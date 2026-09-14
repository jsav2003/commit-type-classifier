"""Punto de entrada único: `python -m ccls <subcomando>`. DESIGN.md §7.7."""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

import yaml

from ccls import clone, discover, pilot
from ccls.gitutil import ResultadoComando

CONFIG_PATH = Path("config/repos.yaml")
PILOT_RESULTS_PATH = Path("data/interim/pilot_results.json")
PILOT_REPORT_PATH = Path("docs/PILOTO.md")
PILOT_WORKDIR = Path("data/raw/pilot_costo")


def _cargar_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


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
    candidatos = [c["owner_repo"] for c in cfg.get("piloto_candidatos", [])]
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
    candidatos = [c["owner_repo"] for c in cfg.get("piloto_candidatos", [])]
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
    candidatos = [c["owner_repo"] for c in cfg.get("piloto_candidatos", [])]
    resultados = _cargar_resultados()
    resultados.setdefault("prefijo_clases", {})
    resultados.setdefault("merge_loss", {})
    resultados.setdefault("docs_baseline", {})

    for owner_repo in candidatos:
        repo_path = clone.ruta_local(owner_repo)
        if not repo_path.exists():
            print(f"[SALTADO] {owner_repo}: no está clonado (correr 'pilot clone' primero)")
            continue

        print(f"midiendo {owner_repo} ...")
        m1 = pilot.medir_prefijo_y_clases(repo_path, owner_repo, n=args.n)
        resultados["prefijo_clases"][owner_repo] = _asdict(m1)

        m2 = pilot.medir_merge_loss(repo_path, owner_repo)
        resultados["merge_loss"][owner_repo] = _asdict(m2)

        m3 = pilot.medir_docs_baseline(repo_path, owner_repo, n=args.n)
        resultados["docs_baseline"][owner_repo] = _asdict(m3)

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
    return 0


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

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
