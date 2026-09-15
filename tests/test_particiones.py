"""Particiones de la F1 (DESIGN.md §5): invariantes sobre datos sintéticos y, si existe,
sobre el dataset real. Una partición que mezcla un repo o una fecha entre entrenamiento
y prueba invalida todas las tablas sin dar ningún error."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from ccls import particiones

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET = REPO_ROOT / "data" / "processed" / "dataset.jsonl"
CFG = yaml.safe_load((REPO_ROOT / "config" / "experimentos.yaml").read_text(encoding="utf-8"))["particiones"]


def _sinteticos() -> list[dict]:
    regs = []
    for i in range(400):
        repo = f"org/r{i % 4}"
        label = ("fix", "fix", "feat", "docs", "fix", "refactor")[i % 6]
        fecha = f"{2020 + i % 6}-0{1 + i % 9}-15T12:00:00+00:00"
        regs.append({"id": f"{repo}@{i:040d}", "repo": repo, "label": label, "committer_date": fecha})
    return regs


def _cubre_sin_solaparse(fold: particiones.Fold, n: int) -> None:
    ent, pru = set(fold.entrenamiento), set(fold.prueba)
    assert not ent & pru
    assert ent | pru == set(range(n))


def test_aleatoria_estratificada_y_determinista():
    regs = _sinteticos()
    a = particiones.aleatoria(regs, semilla=1, fraccion_prueba=0.2)
    _cubre_sin_solaparse(a, len(regs))
    total = Counter(r["label"] for r in regs)
    en_prueba = Counter(regs[i]["label"] for i in a.prueba)
    assert en_prueba == {c: round(n * 0.2) for c, n in total.items()}
    assert a == particiones.aleatoria(regs, semilla=1, fraccion_prueba=0.2)


def test_aleatoria_otra_semilla_da_otra_division():
    regs = _sinteticos()
    uno = particiones.aleatoria(regs, semilla=1, fraccion_prueba=0.2)
    dos = particiones.aleatoria(regs, semilla=2, fraccion_prueba=0.2)
    assert len(uno.prueba) == len(dos.prueba)
    assert uno.prueba != dos.prueba


def test_aleatoria_no_depende_del_orden_de_carga():
    regs = _sinteticos()
    ids = lambda rs, f: sorted(rs[i]["id"] for i in f.prueba)
    al_reves = list(reversed(regs))
    assert ids(regs, particiones.aleatoria(regs, 3, 0.2)) == ids(al_reves, particiones.aleatoria(al_reves, 3, 0.2))


def test_por_repositorio_un_fold_por_repo_sin_mezclar():
    regs = _sinteticos()
    folds = particiones.por_repositorio(regs)
    assert [f.nombre for f in folds] == ["org/r0", "org/r1", "org/r2", "org/r3"]
    for f in folds:
        _cubre_sin_solaparse(f, len(regs))
        assert {regs[i]["repo"] for i in f.prueba} == {f.nombre}
        assert f.nombre not in {regs[i]["repo"] for i in f.entrenamiento}
    # cada registro cae en prueba exactamente una vez
    assert sorted(i for f in folds for i in f.prueba) == list(range(len(regs)))


def test_temporal_todo_el_entrenamiento_es_anterior_a_la_prueba():
    regs = _sinteticos()
    f = particiones.temporal(regs, "2024-01-01T00:00:00+00:00")
    _cubre_sin_solaparse(f, len(regs))
    ultima_ent = max(datetime.fromisoformat(regs[i]["committer_date"]) for i in f.entrenamiento)
    primera_pru = min(datetime.fromisoformat(regs[i]["committer_date"]) for i in f.prueba)
    assert ultima_ent < datetime.fromisoformat("2024-01-01T00:00:00+00:00") <= primera_pru


def test_temporal_compara_instantes_no_texto():
    # 2024-01-01T02:00-05:00 es 07:00 UTC: va a prueba aunque como texto parezca anterior
    regs = [
        {"id": "a", "repo": "r", "label": "fix", "committer_date": "2023-12-31T23:00:00+00:00"},
        {"id": "b", "repo": "r", "label": "fix", "committer_date": "2024-01-01T02:00:00-05:00"},
    ]
    assert particiones.temporal(regs, "2024-01-01T05:00:00+00:00").prueba == (1,)


def test_fold_vacio_es_error():
    with pytest.raises(ValueError, match="vacío"):
        particiones.temporal(_sinteticos(), "2030-01-01T00:00:00+00:00")


def test_particion_desconocida_es_error():
    with pytest.raises(ValueError, match="desconocida"):
        particiones.generar("por_autor", _sinteticos(), 1, CFG)


@pytest.mark.skipif(not DATASET.exists(), reason="no hay dataset en data/processed/ todavía (F0 sin correr)")
def test_dataset_real_particiones_del_design():
    from ccls.stats import cargar_jsonl

    regs = cargar_jsonl(DATASET)
    repos = {r["repo"] for r in regs}

    (temporal,) = particiones.generar("temporal", regs, 1, CFG)
    _cubre_sin_solaparse(temporal, len(regs))
    # DESIGN.md §5: con el corte global fijado, los 5 repos quedan a los dos lados
    assert {regs[i]["repo"] for i in temporal.entrenamiento} == repos
    assert {regs[i]["repo"] for i in temporal.prueba} == repos

    folds = particiones.generar("repositorio", regs, 1, CFG)
    assert len(folds) == len(repos) == 5
    for f in folds:
        assert {regs[i]["repo"] for i in f.prueba} == {f.nombre}

    (aleatoria,) = particiones.generar("aleatoria", regs, 1, CFG)
    _cubre_sin_solaparse(aleatoria, len(regs))
