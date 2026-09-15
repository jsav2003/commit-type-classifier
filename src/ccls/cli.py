"""Punto de entrada único: `python -m ccls <subcomando>`. DESIGN.md §7.7."""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

import yaml

from ccls import clone, discover, pilot
from ccls.gitutil import ResultadoComando, head_sha

CONFIG_PATH = Path("config/repos.yaml")
PILOT_RESULTS_PATH = Path("data/interim/pilot_results.json")
PILOT_REPORT_PATH = Path("docs/PILOTO.md")
PILOT_WORKDIR = Path("data/raw/pilot_costo")


def _cargar_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _todos_los_candidatos(cfg: dict) -> list[str]:
    """Junta piloto_candidatos (ola 1) y cualquier piloto_candidatos_olaN
    posterior (ola 2, ola 3, ...) en una sola lista, en orden."""
    candidatos = [c["owner_repo"] for c in cfg.get("piloto_candidatos", [])]
    for clave in sorted(k for k in cfg if k.startswith("piloto_candidatos_ola")):
        candidatos += [c["owner_repo"] for c in cfg[clave]]
    return candidatos


def _guardar_resultados(resultados: dict) -> None:
    PILOT_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PILOT_RESULTS_PATH.open("w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)


def _cargar_resultados() -> dict:
    if not PILOT_RESULTS_PATH.exists():
        return {}
    with PILOT_RESULTS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _asdict(obj):
    return dataclasses.asdict(obj) if dataclasses.is_dataclass(obj) else obj


# --------------------------------------------------------------------------- #
# discover-check
# --------------------------------------------------------------------------- #

def cmd_discover_check(args: argparse.Namespace) -> int:
    cfg = _cargar_config()
    criterios = cfg.get("criterios_admision", {})
    candidatos = _todos_los_candidatos(cfg)
    print(f"{'repo':32} {'ok':4} {'estrellas':10} {'dias_sin_push':14} {'archivado':10} {'licencia':10}")
    for owner_repo in candidatos:
        m = discover.metadatos(owner_repo)
        cumple, razones = discover.cumple_criterios(m, criterios)
        estado = "SI" if cumple else "no"
        print(f"{owner_repo:32} {estado:4} {m.estrellas:<10} {m.dias_desde_ultimo_push:<14} {str(m.archivado):10} {str(m.licencia):10}")
        if not cumple:
            print(f"    -> {'; '.join(razones)}")
    return 0


# --------------------------------------------------------------------------- #
# pilot clone
# --------------------------------------------------------------------------- #

def cmd_pilot_clone(args: argparse.Namespace) -> int:
    cfg = _cargar_config()
    candidatos = _todos_los_candidatos(cfg)
    for owner_repo in candidatos:
        dest, resultado = clone.asegurar_clonado(owner_repo, timeout=args.timeout)
        if resultado is None:
            print(f"[ya clonado] {owner_repo} -> {dest}")
        elif resultado.ok:
            print(f"[ok {resultado.elapsed_s:6.1f}s] {owner_repo} -> {dest}")
        else:
            print(f"[FALLÓ] {owner_repo}: {resultado.stderr[-300:]}")
    return 0


# --------------------------------------------------------------------------- #
# pilot measure  (B2.1, B2.2, B2.4, B2.5)
# --------------------------------------------------------------------------- #

def cmd_pilot_measure(args: argparse.Namespace) -> int:
    cfg = _cargar_config()
    candidatos = _todos_los_candidatos(cfg)
    resultados = _cargar_resultados()
    resultados.setdefault("prefijo_clases", {})
    resultados.setdefault("merge_loss", {})
    resultados.setdefault("docs_baseline", {})
    resultados.setdefault("meta", {})

    import datetime

    for owner_repo in candidatos:
        repo_path = clone.ruta_local(owner_repo)
        if not repo_path.exists():
            print(f"[SALTADO] {owner_repo}: no está clonado (correr 'pilot clone' primero)")
            continue

        try:
            sha = head_sha(repo_path)
            resultados["meta"][owner_repo] = {
                "head_sha": sha,
                "medido_en": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            print(f"midiendo {owner_repo} (HEAD {sha}) ...")
            m1 = pilot.medir_prefijo_y_clases(repo_path, owner_repo, n=args.n)
            resultados["prefijo_clases"][owner_repo] = _asdict(m1)

            m2 = pilot.medir_merge_loss(repo_path, owner_repo)
            resultados["merge_loss"][owner_repo] = _asdict(m2)

            m3 = pilot.medir_docs_baseline(repo_path, owner_repo, n=args.n)
            resultados["docs_baseline"][owner_repo] = _asdict(m3)
        except RuntimeError as e:
            # Un repo roto (clon incompleto, HEAD inconsistente) no debe tirar
            # abajo la medición de los demás candidatos de la lista.
            print(f"[FALLÓ] {owner_repo}: {e}")
            resultados["meta"][owner_repo] = {"error": str(e)}
            continue

        print(
            f"  prefijo válido: {m1.tasa_prefijo_valido:.1%} | "
            f"pérdida merge: {m2.pct_perdido:.1%} | "
            f"F1 baseline docs: {m3.f1:.2f}"
        )

    _guardar_resultados(resultados)
    print(f"guardado en {PILOT_RESULTS_PATH}")
    return 0


# --------------------------------------------------------------------------- #
# pilot clone-cost (B2.3)
# --------------------------------------------------------------------------- #

def cmd_pilot_clone_cost(args: argparse.Namespace) -> int:
    cfg = _cargar_config()
    owner_repo = args.repo or cfg.get("piloto_repo_costo_clonado")
    resultados = _cargar_resultados()
    resultados.setdefault("costo_clonado", {})

    for filtro in (False, True):
        etiqueta = "filter_blob_none" if filtro else "completo"
        print(f"midiendo costo de clonado ({etiqueta}) para {owner_repo} ...")
        m = pilot.medir_costo_clonado(owner_repo, PILOT_WORKDIR, filter_blob_none=filtro, timeout_clone=args.timeout, timeout_extract=args.timeout)
        resultados["costo_clonado"][etiqueta] = _asdict(m)
        print(f"  clone: {m.clone_s:.1f}s ok={m.clone_ok} | extract: {m.extract_s:.1f}s ok={m.extract_ok} | disco: {m.disco_mb:.1f} MB")

    _guardar_resultados(resultados)
    print(f"guardado en {PILOT_RESULTS_PATH}")
    return 0


# --------------------------------------------------------------------------- #
# pilot report -> docs/PILOTO.md
# --------------------------------------------------------------------------- #

def cmd_pilot_report(args: argparse.Namespace) -> int:
    from ccls import report as report_mod
    resultados = _cargar_resultados()
    if not resultados:
        print("no hay resultados en", PILOT_RESULTS_PATH)
        return 1
    texto = report_mod.render_piloto_md(resultados)
    PILOT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    PILOT_REPORT_PATH.write_text(texto, encoding="utf-8")
    print(f"escrito {PILOT_REPORT_PATH}")

    # Copia versionada de los resultados crudos (data/interim/ está en .gitignore,
    # pero el JSON detrás del piloto sí debe quedar en git: es pequeño y es la
    # evidencia de la puerta de decisión — DESIGN.md §7.7, reproducibilidad).
    snapshot_path = PILOT_REPORT_PATH.parent / "pilot_results.json"
    snapshot_path.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"escrito {snapshot_path}")
    return 0


# --------------------------------------------------------------------------- #
# f0 build / f0 stats  (Parte C)
# --------------------------------------------------------------------------- #

F0_STATS_PATH = Path("docs/F0_ESTADISTICAS.md")


def cmd_f0_build(args: argparse.Namespace) -> int:
    from ccls import build
    meta = build.construir(_cargar_config())
    print(f"{meta['n_registros']} registros -> {build.PROCESSED_DIR}  {meta['por_clase']}")
    print(f"manifest_sha256 {meta['manifest_sha256']}")
    return 0


def cmd_f0_stats(args: argparse.Namespace) -> int:
    from ccls import build, stats
    dataset = build.PROCESSED_DIR / build.DATASET_NAME
    if not dataset.exists():
        print(f"no existe {dataset} (correr 'f0 build' primero)")
        return 1
    meta = json.loads((build.PROCESSED_DIR / build.META_NAME).read_text(encoding="utf-8"))
    F0_STATS_PATH.write_text(stats.render(stats.cargar_jsonl(dataset), meta), encoding="utf-8")
    print(f"escrito {F0_STATS_PATH}")
    return 0


# --------------------------------------------------------------------------- #
# f1 run / f1 fuga-aleatoria
# --------------------------------------------------------------------------- #

EXPERIMENTOS_CONFIG_PATH = Path("config/experimentos.yaml")


def _cargar_f1() -> tuple[dict, list[dict], str] | None:
    from ccls import build, stats
    dataset = build.PROCESSED_DIR / build.DATASET_NAME
    if not dataset.exists():
        print(f"no existe {dataset} (correr 'f0 build' primero)")
        return None
    with EXPERIMENTOS_CONFIG_PATH.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    meta = json.loads((build.PROCESSED_DIR / build.META_NAME).read_text(encoding="utf-8"))
    return cfg, stats.cargar_jsonl(dataset), meta["manifest_sha256"]


def _pct(x: float) -> str:
    return f"{x:6.1%}"


def cmd_f1_run(args: argparse.Namespace) -> int:
    from ccls import experimento, particiones
    cargado = _cargar_f1()
    if cargado is None:
        return 1
    cfg, registros, manifest_sha256 = cargado
    tipos = particiones.TIPOS if args.particion == "todas" else (args.particion,)
    for tipo in tipos:
        res = experimento.correr(registros, args.modelo, tipo, cfg["semillas"], cfg["particiones"], barajar_etiquetas=args.barajar)
        path = experimento.guardar(res, manifest_sha256)
        print(f"{tipo} -> {path}")
        for r in res["resumen"]:
            print(f"  {r['fold']:24} n={r['n_prueba']:5}  exactitud {_pct(r['exactitud']['media'])}  "
                  f"F1 macro {_pct(r['f1_macro']['media'])}  mayoritaria {_pct(r['tasa_mayoritaria']['media'])}")
    return 0


def cmd_f1_fuga_aleatoria(args: argparse.Namespace) -> int:
    from ccls import experimento, particiones
    cargado = _cargar_f1()
    if cargado is None:
        return 1
    cfg, registros, manifest_sha256 = cargado
    prueba = cfg["fuga_etiquetas_aleatorias"]
    filas_por_particion = {}
    for tipo in particiones.TIPOS:
        corridas = {}
        for barajadas in (True, False):
            print(f"{tipo}, etiquetas {'barajadas' if barajadas else 'de verdad'} ...")
            corridas[barajadas] = experimento.correr(
                registros, prueba["modelo"], tipo, cfg["semillas"], cfg["particiones"], barajar_etiquetas=barajadas
            )
            print(f"  -> {experimento.guardar(corridas[barajadas], manifest_sha256)}")
        filas_por_particion[tipo] = experimento.evaluar_fuga_aleatoria(corridas[True], corridas[False], prueba["tolerancia"])
        for f in filas_por_particion[tipo]:
            print(f"  {f['fold']:24} techo {_pct(f['techo_azar'])}  barajadas {_pct(f['exactitud_barajadas']['media'])}  "
                  f"control {_pct(f['exactitud_control']['media'])}  {f['estado']}")
    experimento.F1_FUGA_PATH.write_text(
        experimento.render_fuga_aleatoria(filas_por_particion, prueba["modelo"], cfg["semillas"], prueba["tolerancia"], manifest_sha256),
        encoding="utf-8",
    )
    print(f"escrito {experimento.F1_FUGA_PATH}")
    estados = [f["estado"] for filas in filas_por_particion.values() for f in filas]
    return 0 if all(e == "pasa" for e in estados) else 1


# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ccls")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("discover-check", help="verifica metadatos de los candidatos del piloto contra criterios_admision")
    p.set_defaults(func=cmd_discover_check)

    pilot_parser = sub.add_parser("pilot", help="mediciones de la Parte B (piloto)")
    pilot_sub = pilot_parser.add_subparsers(dest="pilot_comando", required=True)

    p = pilot_sub.add_parser("clone", help="clona (bare, completo) los repos candidatos del piloto")
    p.add_argument("--timeout", type=int, default=1800)
    p.set_defaults(func=cmd_pilot_clone)

    p = pilot_sub.add_parser("measure", help="B2.1/B2.2/B2.4/B2.5 sobre los repos ya clonados")
    p.add_argument("-n", type=int, default=1000, help="tamaño de muestra por repo")
    p.set_defaults(func=cmd_pilot_measure)

    p = pilot_sub.add_parser("clone-cost", help="B2.3: filter:blob:none vs clon completo, historial entero")
    p.add_argument("--repo", default=None, help="por defecto, piloto_repo_costo_clonado de config/repos.yaml")
    p.add_argument("--timeout", type=int, default=1800)
    p.set_defaults(func=cmd_pilot_clone_cost)

    p = pilot_sub.add_parser("report", help="renderiza docs/PILOTO.md desde los resultados guardados")
    p.set_defaults(func=cmd_pilot_report)

    f0_parser = sub.add_parser("f0", help="construcción del dataset (Parte C)")
    f0_sub = f0_parser.add_subparsers(dest="f0_comando", required=True)

    p = f0_sub.add_parser("build", help="extrae, etiqueta y muestrea los f0_repos -> data/processed/")
    p.set_defaults(func=cmd_f0_build)

    p = f0_sub.add_parser("stats", help="escribe docs/F0_ESTADISTICAS.md desde data/processed/")
    p.set_defaults(func=cmd_f0_stats)

    f1_parser = sub.add_parser("f1", help="infraestructura de experimentos")
    f1_sub = f1_parser.add_subparsers(dest="f1_comando", required=True)

    p = f1_sub.add_parser("run", help="entrena y evalúa un modelo con las semillas de config/experimentos.yaml -> resultados/")
    p.add_argument("--modelo", required=True, choices=("trivial", "humo"))
    p.add_argument("--particion", default="todas", choices=("todas", "aleatoria", "repositorio", "temporal"))
    p.add_argument("--barajar", action="store_true", help="baraja las etiquetas de entrenamiento (LEAKAGE.md §7.1)")
    p.set_defaults(func=cmd_f1_run)

    p = f1_sub.add_parser("fuga-aleatoria", help="LEAKAGE.md §7.1 en las tres particiones -> docs/F1_ETIQUETAS_ALEATORIAS.md")
    p.set_defaults(func=cmd_f1_fuga_aleatoria)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
