"""Prueba de fuga por correlación — LEAKAGE.md §7.3, módulo ccls.fuga_correlacion.

Igual que la del prefijo: primero se demuestra que SABE fallar con fugas plantadas,
después se exige que el dataset real pase limpio.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from ccls.fuga_correlacion import Token, medir, sospechosas

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET = REPO_ROOT / "data" / "processed" / "dataset.jsonl"

PATCH = "+'svelte': patch"


def _reg(label: str, diff: str = "", repo: str = "r/x") -> dict:
    return {"label": label, "repo": repo, "message": "mensaje", "diff": diff, "files": ["a.ts"]}


def _dataset(n_fix=550, n_feat=160, n_refactor=80, n_docs=210, token_en=None, frac=0.9, diff=PATCH):
    """1.000 registros con la proporción de clases del dataset real. `token_en` pone
    `diff` en una fracción `frac` de esa clase."""
    regs = []
    for label, n in (("fix", n_fix), ("feat", n_feat), ("refactor", n_refactor), ("docs", n_docs)):
        con = int(n * frac) if label == token_en else 0
        regs += [_reg(label, diff) for _ in range(con)] + [_reg(label) for _ in range(n - con)]
    return regs


def _nombres(ms):
    return {(m.token, m.ambito, m.clase) for m in ms}


def test_detecta_fuga_en_la_clase_mayoritaria():
    ms = sospechosas(medir(_dataset(token_en="fix")))
    assert ("changeset: bump patch", "todos", "fix") in _nombres(ms)


def test_el_cociente_crudo_no_habria_bastado():
    """Fuga perfecta en fix (55%): P(t|c)/P(t) no llega a 1,82. Un umbral sobre ese
    cociente no la separa del ruido; la ganancia normalizada sí."""
    m = next(
        m for m in medir(_dataset(token_en="fix", frac=1.0), por_repo=False)
        if m.token == "changeset: bump patch" and m.clase == "fix"
    )
    assert m.p_token_en_clase / m.p_token < 1.82
    assert m.ganancia > 0.9
    assert m.sospechosa()


def test_detecta_fuga_en_una_clase_minoritaria():
    ms = sospechosas(medir(_dataset(token_en="refactor", diff="+'svelte': minor")))
    assert ("changeset: bump minor", "todos", "refactor") in _nombres(ms)


def test_detecta_fuga_confinada_a_un_repo():
    regs = _dataset() + [_reg("feat", PATCH, repo="r/chico") for _ in range(25)] + [_reg("fix", repo="r/chico") for _ in range(75)]
    ms = sospechosas(medir(regs))
    assert ("changeset: bump patch", "r/chico", "feat") in _nombres(ms)


def test_token_repartido_como_las_clases_no_dispara():
    uniforme = Token("uniforme", re.compile(r"algo"), "diff")
    regs = []
    for label, n in (("fix", 550), ("feat", 160), ("refactor", 80), ("docs", 210)):
        regs += [_reg(label, "+algo" if i % 3 == 0 else "") for i in range(n)]
    assert sospechosas(medir(regs, tokens=[uniforme])) == []


def test_pocos_registros_no_disparan():
    regs = _dataset() + [_reg("docs", PATCH) for _ in range(5)]
    assert sospechosas(medir(regs)) == []


@pytest.mark.skipif(not DATASET.exists(), reason="no hay dataset en data/processed/ todavía (F0 sin correr)")
def test_dataset_real_sin_fuga_por_correlacion():
    from ccls.stats import cargar_jsonl

    ms = sospechosas(medir(cargar_jsonl(DATASET)))
    detalle = [
        f"{m.token} [{m.ambito}] -> {m.clase}: {m.n_token_clase}/{m.n_token} (P(c)={m.p_clase:.1%}, ganancia={m.ganancia:.2f})"
        for m in ms
    ]
    assert not ms, "fuga por correlación:\n" + "\n".join(detalle)
