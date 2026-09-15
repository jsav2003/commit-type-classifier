"""F1 · un comando entrena, evalúa y guarda. DESIGN.md §7.3, §7.4 y §7.7.

correr() cruza un modelo con una partición y las semillas. Por cada semilla y fold:

1. Reduce cada registro a ENTRADAS. El modelo no recibe la etiqueta, el repo, el SHA,
   las fechas ni la auditoría: no puede leerlos aunque quiera.
2. Si se pide, baraja las etiquetas de entrenamiento (LEAKAGE.md §7.1). Las de prueba
   no se tocan: se evalúa contra la verdad.
3. Entrena, predice y mide (metricas.evaluar).

El resumen agrega las semillas dentro de cada fold y nunca los folds entre sí: es la
regla de DESIGN.md §5 para `refactor` en la partición por repositorio.

Nada lleva marca de hora: la misma corrida en la misma máquina da el mismo JSON.
"""

from __future__ import annotations

import json
import platform
from collections import defaultdict
from pathlib import Path
from typing import Callable

import numpy
import sklearn

from ccls import metricas, particiones
from ccls.modelos import MODELOS
from ccls.stats import CLASES

RESULTADOS_DIR = Path("resultados")
F1_FUGA_PATH = Path("docs/F1_ETIQUETAS_ALEATORIAS.md")

# DESIGN.md §4.3. Las banderas de build.py (tiene_referencia_issue, es_bot,
# diff_truncado...) no entran por defecto: se miden en la F2.
ENTRADAS = (
    "message", "diff", "files", "n_files", "lines_added", "lines_deleted",
    "n_binarios", "extensiones", "toca_tests", "toca_docs",
)


def barajar(etiquetas: list[str], ids: list[str], semilla: int) -> list[str]:
    """Permuta las etiquetas con un orden que depende solo de los ids y la semilla, nunca
    de la etiqueta. Conserva cuántas hay de cada clase."""
    perm = sorted(range(len(ids)), key=lambda i: particiones.orden("barajar", semilla, ids[i]))
    return [etiquetas[j] for j in perm]


def correr(
    registros: list[dict],
    modelo: str,
    particion: str,
    semillas: list[int],
    cfg_particiones: dict,
    barajar_etiquetas: bool = False,
    entradas: tuple[str, ...] | None = ENTRADAS,
    fabricas: dict[str, Callable] = MODELOS,
) -> dict:
    """`entradas=None` pasa los registros completos. Solo lo usan los tests, para
    demostrar que la prueba §7.1 atrapa un modelo que lee la etiqueta."""
    X = registros if entradas is None else [{k: r[k] for k in entradas} for r in registros]
    corridas = []
    for semilla in semillas:
        for fold in particiones.generar(particion, registros, semilla, cfg_particiones):
            y_tr = [registros[i]["label"] for i in fold.entrenamiento]
            if barajar_etiquetas:
                y_tr = barajar(y_tr, [registros[i]["id"] for i in fold.entrenamiento], semilla)
            m = fabricas[modelo](semilla).fit([X[i] for i in fold.entrenamiento], y_tr)
            pred = [str(p) for p in m.predict([X[i] for i in fold.prueba])]
            verdad = [registros[i]["label"] for i in fold.prueba]
            corridas.append({
                "semilla": semilla,
                "fold": fold.nombre,
                "n_entrenamiento": len(fold.entrenamiento),
                **metricas.evaluar(verdad, pred, CLASES),
            })
    return {
        "experimento": {
            "modelo": modelo,
            "particion": particion,
            "etiquetas_barajadas": barajar_etiquetas,
            "semillas": list(semillas),
            "entradas": list(entradas) if entradas is not None else None,
        },
        "resumen": resumir(corridas),
        "corridas": corridas,
    }


def resumir(corridas: list[dict]) -> list[dict]:
    por_fold: dict[str, list[dict]] = defaultdict(list)
    for c in corridas:
        por_fold[c["fold"]].append(c)
    resumen = []
    for fold, cs in por_fold.items():
        resumen.append({
            "fold": fold,
            "n_prueba": cs[0]["n_prueba"],
            "exactitud": metricas.intervalo([c["exactitud"] for c in cs]),
            "f1_macro": metricas.intervalo([c["f1_macro"] for c in cs]),
            "tasa_mayoritaria": metricas.intervalo([c["tasa_mayoritaria"] for c in cs]),
            "por_clase": {
                clase: {
                    "n_prueba": cs[0]["por_clase"][clase]["n_prueba"],
                    "f1": metricas.intervalo([c["por_clase"][clase]["f1"] for c in cs]),
                }
                for clase in CLASES
            },
        })
    return resumen


def _redondear(obj, dec: int = 4):
    if isinstance(obj, float):
        return round(obj, dec)
    if isinstance(obj, dict):
        return {k: _redondear(v, dec) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redondear(v, dec) for v in obj]
    return obj


def nombre_resultado(modelo: str, particion: str, barajadas: bool) -> str:
    return f"{modelo}__{particion}{'__barajadas' if barajadas else ''}.json"


def guardar(resultado: dict, manifest_sha256: str, out_dir: Path = RESULTADOS_DIR) -> Path:
    exp = resultado["experimento"]
    doc = {
        **resultado,
        "dataset": {"manifest_sha256": manifest_sha256},
        "versiones": {"python": platform.python_version(), "numpy": numpy.__version__, "scikit-learn": sklearn.__version__},
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / nombre_resultado(exp["modelo"], exp["particion"], exp["etiquetas_barajadas"])
    path.write_bytes((json.dumps(_redondear(doc), ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return path


# --------------------------------------------------------------------------- #
# LEAKAGE.md §7.1 · etiquetas aleatorias
# --------------------------------------------------------------------------- #

def evaluar_fuga_aleatoria(barajado: dict, control: dict, tolerancia: float) -> list[dict]:
    """Una fila por fold.

    Un predictor que no mira la etiqueta tiene exactitud esperada sum_c q_c * p_c, que
    no pasa de max_c p_c: la tasa de la clase mayoritaria de prueba es el techo del azar.

    - falla:          con etiquetas barajadas, la exactitud media pasa ese techo por
                      más de `tolerancia`.
    - no concluyente: no falla, pero el mismo montaje con las etiquetas de verdad
                      tampoco pasa el techo por más de `tolerancia`. Un montaje que no
                      aprende nada pasaría la prueba sin demostrar nada.
    - pasa:           lo demás.
    """
    control_por_fold = {r["fold"]: r for r in control["resumen"]}
    filas = []
    for r in barajado["resumen"]:
        techo = r["tasa_mayoritaria"]["media"]
        exceso = r["exactitud"]["media"] - techo
        exceso_control = control_por_fold[r["fold"]]["exactitud"]["media"] - techo
        if exceso > tolerancia:
            estado = "falla"
        elif exceso_control <= tolerancia:
            estado = "no concluyente"
        else:
            estado = "pasa"
        filas.append({
            "fold": r["fold"],
            "n_prueba": r["n_prueba"],
            "techo_azar": techo,
            "exactitud_barajadas": r["exactitud"],
            "f1_macro_barajadas": r["f1_macro"],
            "exactitud_control": control_por_fold[r["fold"]]["exactitud"],
            "exceso": exceso,
            "estado": estado,
        })
    return filas


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x:.1%}".replace(".", ",")


def _puntos(x: float) -> str:
    return f"{x * 100:+.1f}".replace(".", ",")


def _ic(iv: dict | None) -> str:
    if iv is None:
        return "—"
    if iv["ic_inf"] is None:
        return _pct(iv["media"])
    return f"{_pct(iv['media'])} [{_pct(iv['ic_inf'])}, {_pct(iv['ic_sup'])}]"


def render_fuga_aleatoria(filas_por_particion: dict[str, list[dict]], modelo: str, semillas: list[int], tolerancia: float, manifest_sha256: str) -> str:
    L = [
        "# Prueba de fuga por etiquetas aleatorias (F1)\n",
        "Generado por `python -m ccls f1 fuga-aleatoria`. **No se edita a mano.** "
        "Criterio y lectura en `LEAKAGE.md` §7.1.\n",
        f"- Modelo: `{modelo}` (`src/ccls/modelos.py`). Solo verifica el montaje: sus números con "
        "etiquetas de verdad **no son resultados de la F2**.",
        f"- Semillas: {', '.join(map(str, semillas))}. Media e intervalo t al 95% entre semillas.",
        f"- Tolerancia: {_puntos(tolerancia)} puntos sobre el techo del azar (tasa de la clase mayoritaria en prueba).",
        "- En las particiones por repositorio y temporal la división es fija y la regresión logística es "
        "determinista: el control da lo mismo con cada semilla y su intervalo tiene ancho cero.",
        f"- Dataset: `manifest_sha256` `{manifest_sha256}`.\n",
    ]
    for particion, filas in filas_por_particion.items():
        L.append(f"## Partición {particion}\n")
        L.append("| fold | n prueba | techo del azar | exactitud, etiquetas barajadas | F1 macro, barajadas | exactitud, control | exceso (puntos) | estado |")
        L.append("|---|---:|---:|---:|---:|---:|---:|---|")
        for f in filas:
            L.append(
                f"| {f['fold']} | {f['n_prueba']} | {_pct(f['techo_azar'])} | {_ic(f['exactitud_barajadas'])} | "
                f"{_ic(f['f1_macro_barajadas'])} | {_ic(f['exactitud_control'])} | {_puntos(f['exceso'])} | {f['estado']} |"
            )
        L.append("")
    estados = [f["estado"] for filas in filas_por_particion.values() for f in filas]
    L.append("## Resultado\n")
    L.append(
        f"{len(estados)} folds: {estados.count('pasa')} pasan, {estados.count('falla')} fallan, "
        f"{estados.count('no concluyente')} no concluyentes.\n"
    )
    return "\n".join(L)
