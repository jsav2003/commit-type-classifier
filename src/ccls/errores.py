"""Análisis de errores. DESIGN.md §7.6, y `ERROR-ANALYSIS.md` como salida.

Revisión de commits mal clasificados, agrupados por causa. Es la parte del proyecto que
demuestra que se miraron los datos y no solo las métricas.

**Qué modelo.** El clásico de referencia (`clasico_lr_balanceado`), en la partición por
repositorio: cada commit lo predice un modelo entrenado sin ver su repo. Es el único con
predicciones por commit reproducibles en segundos; las corridas de CodeBERT y de la red
desde cero guardan métricas y matrices de confusión, no la predicción de cada commit. Los
errores de esos dos modelos no se revisan aquí, y el reporte lo dice.

**Qué muestra.** `POR_REPO` errores por repositorio, tomados por orden de hash
(`particiones.orden`, con un uso propio para que no se parezca a ninguna otra división).
Todos los repos pesan igual aunque angular-cli tenga más commits: la muestra dice qué
tipo de errores hay en cada proyecto, no cuántos hay en total. Los totales salen en el
reporte, calculados sobre todos los errores y no sobre la muestra.

**Qué causas** (DESIGN.md §7.6, más una): `etiqueta_autor`, `mixto`, `mensaje_inutil`,
`error_modelo` y `fuera_de_clases`. La quinta no está en el diseño: la F3 midió que en
los repos sin convención el 31% de los commits no es ninguna de las cuatro clases
(releases, dependencias, CI, tests) y el clasificador no puede decir "ninguna"; sin esta
causa esos errores caerían en `error_modelo` y lo inflarían. Declarada aquí, con fecha.

**Quién categoriza.** La causa de cada error la decide una persona. El archivo de causas
lleva una columna `estado`: `propuesta` es lo que propuso el asistente leyendo el commit;
`confirmada` es lo que una persona revisó y dejó igual o corrigió. El reporte cuenta cada
estado por separado y no presenta una propuesta como revisada.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from pathlib import Path

from ccls import build, experimento, f3, particiones

MODELO = f3.MODELO_F3
SEMILLA_MODELO = f3.SEMILLA_MODELO
SEMILLA_MUESTRA = 1
POR_REPO = 10

MUESTRA_PATH = build.PROCESSED_DIR / "errores_muestra.csv"
META_PATH = build.PROCESSED_DIR / "errores_meta.json"
CAUSAS_PATH = build.PROCESSED_DIR / "errores_causas.csv"
REPORTE_PATH = Path("ERROR-ANALYSIS.md")

MUESTRA_COLS = ("id", "repo", "sha", "verdad", "prediccion", "mensaje", "archivos",
                "n_archivos", "lineas_agregadas", "lineas_borradas")
CAUSAS_COLS = ("id", "causa", "estado", "nota")

CAUSAS = {
    "etiqueta_autor": "La etiqueta que puso el autor es discutible: lo que predijo el modelo se defiende.",
    "mixto": "El commit hace de verdad varias cosas de peso; ninguna etiqueta única es correcta.",
    "mensaje_inutil": "El mensaje no dice qué se hizo (`wip`, `update`, `changes`), así que no hay de dónde aprender.",
    "fuera_de_clases": "No es ninguna de las cuatro clases: release, versión, dependencias, CI, tests o estilo.",
    "error_modelo": "La etiqueta es razonable y el mensaje o los archivos alcanzaban: es un error real del modelo.",
}
ESTADOS = ("propuesta", "confirmada")


# --------------------------------------------------------------------------- #
# la muestra
# --------------------------------------------------------------------------- #

def errores_por_repositorio(registros: list[dict], modelo: str = MODELO,
                            semilla: int = SEMILLA_MODELO) -> list[dict]:
    """Todos los commits mal clasificados, con el modelo entrenado sin su repo."""
    from ccls import modelos

    X = [{k: r[k] for k in experimento.ENTRADAS} for r in registros]
    errores: list[dict] = []
    for fold in particiones.por_repositorio(registros):
        m = modelos.MODELOS[modelo](semilla).fit([X[i] for i in fold.entrenamiento],
                                                  [registros[i]["label"] for i in fold.entrenamiento])
        pred = m.predict([X[i] for i in fold.prueba])
        for i, p in zip(fold.prueba, pred, strict=True):
            if str(p) != registros[i]["label"]:
                errores.append({**registros[i], "prediccion": str(p)})
    return errores


def n_prueba_por_repo(registros: list[dict]) -> dict[str, int]:
    return dict(sorted(Counter(r["repo"] for r in registros).items()))


def muestrear(errores: list[dict], por_repo: int = POR_REPO, semilla: int = SEMILLA_MUESTRA) -> list[dict]:
    grupos: dict[str, list[dict]] = defaultdict(list)
    for e in errores:
        grupos[e["repo"]].append(e)
    out: list[dict] = []
    for repo in sorted(grupos):
        elegidos = sorted(grupos[repo], key=lambda e: particiones.orden("errores", semilla, e["id"]))[:por_repo]
        out += sorted(elegidos, key=lambda e: e["id"])
    return out


def fila_muestra(e: dict) -> dict:
    return {
        "id": e["id"], "repo": e["repo"], "sha": e["sha"], "verdad": e["label"],
        "prediccion": e["prediccion"], "mensaje": e["message"], "archivos": " | ".join(e["files"]),
        "n_archivos": e["n_files"], "lineas_agregadas": e["lines_added"], "lineas_borradas": e["lines_deleted"],
    }


def resumen(errores: list[dict], registros: list[dict]) -> dict:
    """Los totales sobre TODOS los errores, no sobre la muestra."""
    por_par = Counter((e["label"], e["prediccion"]) for e in errores)
    return {
        "modelo": MODELO,
        "particion": "repositorio",
        "n_commits": len(registros),
        "n_errores": len(errores),
        "commits_por_repo": n_prueba_por_repo(registros),
        "errores_por_repo": dict(sorted(Counter(e["repo"] for e in errores).items())),
        "errores_por_par": {f"{v}->{p}": n for (v, p), n in sorted(por_par.items(), key=lambda x: (-x[1], x[0]))},
        "por_repo": POR_REPO,
        "semilla_muestra": SEMILLA_MUESTRA,
    }


def escribir_muestra(muestra: list[dict], meta: dict, path: Path = MUESTRA_PATH, meta_path: Path = META_PATH) -> str:
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=MUESTRA_COLS, lineterminator="\n")
    w.writeheader()
    w.writerows(fila_muestra(e) for e in muestra)
    texto = buf.getvalue()
    path.write_bytes(texto.encode("utf-8"))
    meta_path.write_bytes((json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def leer_muestra(path: Path = MUESTRA_PATH) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# --------------------------------------------------------------------------- #
# las causas
# --------------------------------------------------------------------------- #

def leer_causas(path: Path = CAUSAS_PATH) -> dict[str, dict]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))
    for r in filas:
        if r["causa"] not in CAUSAS:
            raise ValueError(f"{r['id']}: causa desconocida {r['causa']!r} (válidas: {', '.join(CAUSAS)})")
        if r["estado"] not in ESTADOS:
            raise ValueError(f"{r['id']}: estado desconocido {r['estado']!r} (válidos: {', '.join(ESTADOS)})")
    return {r["id"]: r for r in filas}


def escribir_causas(causas: list[dict], path: Path = CAUSAS_PATH) -> None:
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=CAUSAS_COLS, lineterminator="\n")
    w.writeheader()
    w.writerows({k: c[k] for k in CAUSAS_COLS} for c in causas)
    path.write_bytes(buf.getvalue().encode("utf-8"))


def unir(muestra: list[dict], causas: dict[str, dict]) -> list[dict]:
    """La muestra con su causa. Falla si una causa apunta a un commit que no está en la
    muestra: en ese caso la muestra cambió y las causas ya no le corresponden."""
    ids = {m["id"] for m in muestra}
    sueltas = sorted(set(causas) - ids)
    if sueltas:
        raise RuntimeError(f"hay causas de commits que no están en la muestra (¿cambió?): {sueltas[:3]}")
    return [{**m, "causa": causas.get(m["id"], {}).get("causa"),
             "estado": causas.get(m["id"], {}).get("estado"),
             "nota": causas.get(m["id"], {}).get("nota", "")} for m in muestra]


# --------------------------------------------------------------------------- #
# el reporte
# --------------------------------------------------------------------------- #

def _pct(k: int, n: int) -> str:
    return f"{k / n:.1%}".replace(".", ",") if n else "—"


def _celda(texto: str, largo: int = 110) -> str:
    """Una línea, sin barras que rompan la tabla y sin pasar de `largo`."""
    t = " ".join(texto.split()).replace("|", "\\|")
    return t if len(t) <= largo else t[: largo - 1].rstrip() + "…"


def _seccion_alcance(meta: dict) -> list[str]:
    n_c, n_e = meta["n_commits"], meta["n_errores"]
    L = [
        "## Qué se revisó\n",
        f"El modelo es `{meta['modelo']}`, el clásico de referencia, en la partición por "
        "repositorio: cada commit lo predice un modelo entrenado sin ver su repositorio. "
        f"Se equivoca en **{n_e} de {n_c} commits ({_pct(n_e, n_c)})**. De esos se revisaron "
        f"{meta['por_repo']} por repositorio, tomados por orden de hash con una semilla fija "
        "(`src/ccls/errores.py`).\n",
        "**Limitación.** La muestra pesa igual a todos los repos, así que dice qué tipo de "
        "error hay en cada proyecto y no cuántos hay en total: las proporciones de abajo no "
        "son la tasa de cada causa en el dataset. Los errores de CodeBERT y de la red desde "
        "cero no se revisan: sus corridas guardan métricas y matrices de confusión, no la "
        "predicción de cada commit.\n",
        "| repositorio | commits | errores | tasa de error |",
        "|---|---:|---:|---:|",
    ]
    for repo, n in meta["commits_por_repo"].items():
        e = meta["errores_por_repo"].get(repo, 0)
        L.append(f"| {repo} | {n} | {e} | {_pct(e, n)} |")
    L += ["", "Errores por par (verdad → predicción), sobre **todos** los errores:\n",
          "| verdad → predicción | errores | del total |", "|---|---:|---:|"]
    for par, k in list(meta["errores_por_par"].items())[:8]:
        L.append(f"| `{par.replace('->', '` → `')}` | {k} | {_pct(k, n_e)} |")
    L.append("")
    return L


def _seccion_causas_definicion() -> list[str]:
    L = ["## Las causas\n",
         "Son las de DESIGN.md §7.6 más una: `fuera_de_clases`, que el diseño no tenía. La F3 "
         "midió que en los repos sin convención el 31% de los commits no es ninguna de las "
         "cuatro clases y el clasificador no puede decir \"ninguna\"; sin esta causa esos "
         "errores caerían en `error_modelo` y lo inflarían.\n",
         "| causa | qué significa |", "|---|---|"]
    L += [f"| `{c}` | {d} |" for c, d in CAUSAS.items()]
    L.append("")
    return L


def _seccion_estado(filas: list[dict]) -> list[str]:
    n = len(filas)
    por_estado = Counter(f["estado"] for f in filas)
    sin = por_estado.get(None, 0)
    L = ["## Quién decidió cada causa\n"]
    L.append(f"De los {n} errores de la muestra: **{por_estado.get('confirmada', 0)} confirmados** "
             f"por una persona, **{por_estado.get('propuesta', 0)} propuestos** por el asistente "
             f"sin revisar y {sin} sin causa.\n")
    if por_estado.get("confirmada", 0) < n:
        L.append("> **Esto no es todavía un análisis de errores hecho por una persona.** Las "
                 "causas marcadas `propuesta` las puso el asistente leyendo el mensaje y los "
                 "archivos de cada commit; son un punto de partida para revisar, no un "
                 "resultado. Cambiar una causa: editar `data/processed/errores_causas.csv` y "
                 "poner `confirmada` en su estado.\n")
    return L


def _seccion_conteo(filas: list[dict]) -> list[str]:
    n = len(filas)
    L = ["## Cuántos errores hay de cada causa\n",
         "Sobre la muestra (10 por repositorio), no sobre todos los errores.\n",
         "| causa | errores | de la muestra | confirmados |", "|---|---:|---:|---:|"]
    for c in CAUSAS:
        d = [f for f in filas if f["causa"] == c]
        L.append(f"| `{c}` | {len(d)} | {_pct(len(d), n)} | {sum(f['estado'] == 'confirmada' for f in d)} |")
    L += ["", "Por repositorio:\n",
          "| repositorio | " + " | ".join(f"`{c}`" for c in CAUSAS) + " |",
          "|---|" + "---:|" * len(CAUSAS)]
    for repo in sorted({f["repo"] for f in filas}):
        d = [f for f in filas if f["repo"] == repo]
        L.append(f"| {repo} | " + " | ".join(str(sum(f["causa"] == c for f in d)) for c in CAUSAS) + " |")
    L.append("")
    return L


def _seccion_por_causa(filas: list[dict]) -> list[str]:
    L = ["## Los errores, agrupados por causa\n",
         "`verdad` es la etiqueta que puso el autor; `predicción`, lo que dijo el modelo. "
         "Mensaje y archivos recortados a una línea; el commit completo se busca con el sha.\n"]
    for c, d in CAUSAS.items():
        grupo = [f for f in filas if f["causa"] == c]
        if not grupo:
            continue
        L += [f"### `{c}` — {len(grupo)}\n", f"{d}\n",
              "| id | repo | verdad → predicción | mensaje | archivos | estado | nota |",
              "|---|---|---|---|---|---|---|"]
        for f in grupo:
            L.append(f"| {f['sha'][:8]} | {f['repo']} | `{f['verdad']}` → `{f['prediccion']}` | "
                     f"{_celda(f['mensaje'], 90)} | {_celda(f['archivos'], 70)} ({f['n_archivos']}) | "
                     f"{f['estado']} | {_celda(f['nota'], 120)} |")
        L.append("")
    return L


def render(muestra: list[dict], causas: dict[str, dict], meta: dict) -> str:
    filas = unir(muestra, causas)
    L = [
        "# Análisis de errores\n",
        "Generado por `python -m ccls errores report` desde `data/processed/errores_muestra.csv` "
        "y `data/processed/errores_causas.csv`. **No se edita a mano:** las causas se cambian en el "
        "CSV. Diseño en `DESIGN.md` §7.6.\n",
    ]
    L += _seccion_alcance(meta)
    L += _seccion_causas_definicion()
    L += _seccion_estado(filas)
    if all(f["causa"] for f in filas):
        L += _seccion_conteo(filas)
        L += _seccion_por_causa(filas)
    else:
        L.append("Faltan causas: el resto del reporte sale cuando todos los errores tengan una.\n")
    return "\n".join(L)

