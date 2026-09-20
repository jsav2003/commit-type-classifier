"""Métricas por clase e intervalos de confianza. DESIGN.md §7.3 y §7.4.

La F1 de una clase sin ejemplos en prueba es None, no 0: no existe. En la partición
por repositorio pasa con `refactor` cuando svelte queda en prueba (DESIGN.md §5).
"""

from __future__ import annotations

import math
import statistics

from scipy.stats import t as t_student


def evaluar(verdad: list[str], prediccion: list[str], clases: tuple[str, ...]) -> dict:
    idx = {c: i for i, c in enumerate(clases)}
    k = len(clases)
    confusion = [[0] * k for _ in range(k)]  # fila: verdad, columna: predicción
    for v, p in zip(verdad, prediccion, strict=True):
        confusion[idx[v]][idx[p]] += 1

    n = len(verdad)
    por_clase = {}
    for c, i in idx.items():
        soporte = sum(confusion[i])
        predichos = sum(fila[i] for fila in confusion)
        tp = confusion[i][i]
        por_clase[c] = {
            "n_prueba": soporte,
            "n_predichos": predichos,
            "precision": tp / predichos if predichos else None,
            "cobertura": tp / soporte if soporte else None,
            "f1": 2 * tp / (soporte + predichos) if soporte else None,
        }
    f1s = [m["f1"] for m in por_clase.values() if m["f1"] is not None]
    return {
        "n_prueba": n,
        "exactitud": sum(confusion[i][i] for i in range(k)) / n,
        # macro sobre las clases presentes en prueba
        "f1_macro": statistics.fmean(f1s),
        # techo del azar: ningún predictor que ignora la entrada lo pasa en esperanza
        "tasa_mayoritaria": max(map(sum, confusion)) / n,
        "por_clase": por_clase,
        "confusion": confusion,
    }


def intervalo(valores: list[float | None], nivel: float = 0.95) -> dict | None:
    """Media e intervalo t de Student sobre las semillas. None si algún valor no existe;
    sin intervalo si hay una sola semilla."""
    if any(v is None for v in valores):
        return None
    n = len(valores)
    media = statistics.fmean(valores)
    if n < 2:
        return {"n": n, "media": media, "ic_inf": None, "ic_sup": None}
    h = t_student.ppf((1 + nivel) / 2, n - 1) * statistics.stdev(valores) / math.sqrt(n)
    return {"n": n, "media": media, "ic_inf": media - h, "ic_sup": media + h}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de Wilson para una proporción k/n. Sin ejemplos no hay intervalo:
    (0, 1), que es "no sé nada", no (0, 0)."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    centro = p + z**2 / (2 * n)
    margen = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n * n))
    denom = 1 + z**2 / n
    return (centro - margen) / denom, (centro + margen) / denom


def kappa_cohen(a: list[str], b: list[str], clases: tuple[str, ...]) -> float | None:
    """Kappa de Cohen entre dos anotaciones de los mismos ítems. None si no está
    definido: sin ítems, o cuando el acuerdo esperado por azar es 1 (los dos dicen
    siempre la misma clase y no hay nada que corregir)."""
    n = len(a)
    if n == 0:
        return None
    observado = sum(x == y for x, y in zip(a, b, strict=True)) / n
    esperado = sum((a.count(c) / n) * (b.count(c) / n) for c in clases)
    if esperado >= 1:
        return None
    return (observado - esperado) / (1 - esperado)
