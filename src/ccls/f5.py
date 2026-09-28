"""F5 · red desde cero. El reporte `docs/F5_DESDE_CERO.md`. DESIGN.md §6.4, §7.3 y §7.4.

Lo que se entrena y se guarda vive en `profundo.py` y `f4 run`/`f5 run`; aquí solo se lee
lo que quedó en `resultados/` y se pone al lado de las dos referencias:

- `clasico_lr_balanceado`, el clásico de referencia de la F2 (DESIGN.md §4.4).
- `f4_codebert`, la misma arquitectura con los pesos preentrenados. La diferencia F4 − F5
  es lo que aportan esos pesos con el mismo presupuesto de entrenamiento (§6.4).

Las reglas son las de la F4 (`comparar` y las secciones se reusan de `f4.py`): F1 por
clase, `refactor` fold por fold, media e intervalo entre semillas y la prueba de etiquetas
aleatorias de `LEAKAGE.md` §7.1. La F5 no busca ganar: DESIGN.md §6.4 dice que
probablemente pierda y que un resultado negativo bien medido es un resultado.
"""

from __future__ import annotations

from pathlib import Path

from ccls import f2, f4

F5_REPORTE_PATH = Path("docs/F5_DESDE_CERO.md")

MODELO = "f5_desde_cero"
CLASICO = f2.REPONDERADO
CODEBERT = f4.MODELO
PARTICIONES = f2.PARTICIONES

# Una corrida "colapsa" si al menos esta parte de sus predicciones cae en una sola clase.
UMBRAL_COLAPSO = 0.9

_pct = f2._pct
_puntos = f2._puntos
_resumen_de = f2._resumen_de
_folds = f2._folds


def colapsadas(doc: dict, umbral: float = UMBRAL_COLAPSO) -> tuple[int, int]:
    """(corridas cuyas predicciones caen casi todas en una clase, corridas totales).

    Una red que no aprendió suele responder siempre lo mismo. Esto lo mide directo desde
    las matrices de confusión, sin depender de que la exactitud lo delate."""
    n = 0
    for c in doc["corridas"]:
        por_columna = [sum(fila[j] for fila in c["confusion"]) for j in range(len(c["confusion"]))]
        total = sum(por_columna)
        if total and max(por_columna) / total >= umbral:
            n += 1
    return n, len(doc["corridas"])


def _seccion_colapso(resultados: dict[str, dict[str, dict]], barajadas: dict[str, dict]) -> list[str]:
    L = [
        "## Cuántas corridas responden siempre lo mismo\n",
        f"Una corrida (una semilla en un fold) cuenta como colapsada si al menos el "
        f"{UMBRAL_COLAPSO:.0%} de sus predicciones cae en una sola clase. El umbral es una "
        "elección de este reporte para describir, no un criterio de la prueba de fuga.\n",
        "| partición | corridas, etiquetas reales | corridas, etiquetas barajadas |",
        "|---|---:|---:|",
    ]
    for particion in PARTICIONES:
        real = colapsadas(resultados[particion][MODELO])
        bar = colapsadas(barajadas[particion]) if particion in barajadas else None
        L.append(f"| {particion} | {real[0]} de {real[1]} | "
                 + (f"{bar[0]} de {bar[1]}" if bar else "sin correr") + " |")
    L.append("")
    return L


def _seccion_montaje(doc: dict) -> list[str]:
    h = doc["experimento"]["hiperparametros"]
    v = doc["versiones"]
    L = [
        "## Montaje\n",
        "`config/f5.yaml` es `config/f4.yaml` con una sola diferencia: la red se entrena "
        "entera (`capas_entrenables: null`), porque congelar capas con pesos al azar sería "
        "dejar ruido fijo en medio de la red. Fijada el 2026-09-22 **antes** de entrenar. "
        "El tokenizador es el de CodeBERT: la F5 hereda su vocabulario, no sus pesos.\n",
        "**No es la mejor red desde cero posible.** Una red al azar suele pedir más épocas y "
        "otra tasa de aprendizaje, pero buscarlas obligaría a elegir mirando los folds de "
        "prueba (no hay conjunto de validación) y a cambiar dos cosas a la vez. Con este "
        "presupuesto la comparación es limpia; con otro, el resultado de la F5 podría ser "
        "mejor. DESIGN.md §6.4.\n",
        "| parámetro | valor |",
        "|---|---|",
    ]
    L += [f"| `{k}` | `{val}` |" for k, val in h.items()]
    L += [
        "",
        "Versiones con que se corrió: " + ", ".join(f"{k} {val}" for k, val in v.items()) + ".\n",
        "En GPU los ajustes no son bit a bit reproducibles aunque se fije la semilla; para "
        "eso están las cinco semillas.\n",
    ]
    return L


def render(resultados: dict[str, dict[str, dict]], semillas: list[int], manifest_sha256: str,
           barajadas: dict[str, dict] | None = None, tolerancia: float = 0.02) -> str:
    """`resultados[particion]` tiene `MODELO`, `CLASICO` y `CODEBERT`. `barajadas[particion]`
    es `MODELO` con las etiquetas barajadas; si falta una partición, la sección de §7.1 lo
    dice en vez de callarlo."""
    barajadas = barajadas or {}

    def sel(particion: str) -> dict[str, dict]:
        return {m: resultados[particion][m] for m in (MODELO, CODEBERT, CLASICO)}

    L = [
        "# F5 · Red desde cero\n",
        "Generado por `python -m ccls f5 report`. **No se edita a mano.** El diseño de la "
        "fase está en `DESIGN.md` §6.4; cómo se leen los números, en §7.3 y §7.4. Cómo se "
        "corrió, en `docs/KAGGLE_F5.md`.\n",
        f"- `{MODELO}`: la arquitectura de CodeBERT (`microsoft/codebert-base`) con los pesos "
        "al azar, entrenada entera y con la pérdida ponderada por clase.",
        f"- `{CODEBERT}`: la misma arquitectura con los pesos preentrenados y las últimas "
        "capas reentrenadas (`docs/F4_TRANSFER.md`). F4 − F5 mide lo que aporta el "
        "preentrenamiento.",
        f"- `{CLASICO}`: el clásico de referencia de la F2 (`docs/F2_BASELINES.md`), también "
        "reponderado.",
        f"- Semillas: {', '.join(map(str, semillas))}. Cada celda es la media entre semillas "
        "con su intervalo t al 95%; el clásico es determinista en las particiones por "
        "repositorio y temporal, y ahí su intervalo tiene ancho cero y se omite.",
        "- Una celda `—` es una clase sin ejemplos en prueba: la F1 no existe, y no vale 0.",
        f"- Dataset: `manifest_sha256` `{manifest_sha256}`.\n",
    ]
    L += f4._seccion_veredicto(resultados, MODELO, CLASICO)
    L += f4._seccion_veredicto(resultados, MODELO, CODEBERT, de_ref="de CodeBERT")
    L += f4._seccion_por_clase(resultados, MODELO, CLASICO,
                               titulo=f"Qué clase gana y cuál pierde, contra `{CLASICO}`")
    L += f4._seccion_por_clase(resultados, MODELO, CODEBERT,
                               titulo=f"Qué clase gana y cuál pierde, contra `{CODEBERT}`")
    L += f2._seccion_particion(
        "Partición aleatoria",
        "80/20 estratificada por clase, con una división distinta por semilla. **Fuga "
        "información**: commits del mismo repositorio quedan a los dos lados.",
        sel("aleatoria"))
    L += f2._seccion_particion(
        "Partición por repositorio — la principal",
        "Un fold por repo, con ese repo entero en prueba.",
        sel("repositorio"))
    L += f2._seccion_particion(
        "Partición temporal",
        "Corte global el 2025-06-01: entrena con lo anterior y evalúa con lo "
        "posterior, 7.999 / 2.001.",
        sel("temporal"))
    L += f2._seccion_refactor({p: sel(p) for p in PARTICIONES})
    L += f2._seccion_inflado(sel("aleatoria"), sel("repositorio"))
    if barajadas:
        L += f4._seccion_fuga(
            resultados, barajadas, tolerancia, modelo=MODELO,
            nota="La red parte de pesos al azar y ve las rutas completas de los archivos: es "
                 "un camino por el que la etiqueta podría colarse, y se prueba igual.")
        L += _seccion_colapso(resultados, barajadas)
    L += f2._seccion_confusion(resultados["repositorio"][MODELO], MODELO)
    L += _seccion_montaje(resultados["repositorio"][MODELO])
    return "\n".join(L)
