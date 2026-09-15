"""F1 · las tres particiones de DESIGN.md §5.

Una partición es una lista de folds. Cada fold dice qué posiciones de la lista de
registros van a entrenamiento y cuáles a prueba.

- aleatoria:   un fold por semilla, estratificado por clase.
- repositorio: un fold por repo, con ese repo entero en prueba. No depende de la semilla.
- temporal:    un fold, corte global por fecha de commit. No depende de la semilla.

Igual que el muestreo de la F0 (build.py), el azar sale de sha256 y no de un generador
aleatorio: la misma semilla da la misma división en cualquier versión de Python o numpy.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

TIPOS = ("aleatoria", "repositorio", "temporal")


@dataclass(frozen=True)
class Fold:
    nombre: str
    entrenamiento: tuple[int, ...]
    prueba: tuple[int, ...]


def orden(uso: str, semilla: int, id_: str) -> str:
    """Clave de orden pseudoaleatoria. `uso` separa los usos entre sí: dividir y barajar
    con la misma semilla no deben producir el mismo orden."""
    return hashlib.sha256(f"{uso}:{semilla}:{id_}".encode("utf-8")).hexdigest()


def _fold(nombre: str, n: int, prueba: set[int]) -> Fold:
    fold = Fold(nombre, tuple(i for i in range(n) if i not in prueba), tuple(sorted(prueba)))
    if not fold.entrenamiento or not fold.prueba:
        raise ValueError(f"fold {nombre!r} vacío: {len(fold.entrenamiento)} en entrenamiento, {len(fold.prueba)} en prueba")
    return fold


def aleatoria(registros: list[dict], semilla: int, fraccion_prueba: float) -> Fold:
    por_clase: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(registros):
        por_clase[r["label"]].append(i)
    prueba: set[int] = set()
    for clase in sorted(por_clase):
        idx = sorted(por_clase[clase], key=lambda i: orden("aleatoria", semilla, registros[i]["id"]))
        prueba.update(idx[: round(len(idx) * fraccion_prueba)])
    return _fold("aleatoria", len(registros), prueba)


def por_repositorio(registros: list[dict]) -> list[Fold]:
    return [
        _fold(repo, len(registros), {i for i, r in enumerate(registros) if r["repo"] == repo})
        for repo in sorted({r["repo"] for r in registros})
    ]


def temporal(registros: list[dict], corte: str) -> Fold:
    """Entrenamiento: committer_date < corte. Prueba: committer_date >= corte."""
    t = datetime.fromisoformat(corte)
    prueba = {i for i, r in enumerate(registros) if datetime.fromisoformat(r["committer_date"]) >= t}
    return _fold("temporal", len(registros), prueba)


def generar(tipo: str, registros: list[dict], semilla: int, cfg: dict) -> list[Fold]:
    """`cfg` es la sección `particiones` de config/experimentos.yaml."""
    if tipo == "aleatoria":
        return [aleatoria(registros, semilla, cfg["aleatoria"]["fraccion_prueba"])]
    if tipo == "repositorio":
        return por_repositorio(registros)
    if tipo == "temporal":
        return [temporal(registros, cfg["temporal"]["corte"])]
    raise ValueError(f"partición desconocida: {tipo!r} (válidas: {', '.join(TIPOS)})")
