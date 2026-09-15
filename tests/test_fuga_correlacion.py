"""Prueba de fuga por correlación — LEAKAGE.md §7.3, módulo ccls.fuga_correlacion.

Igual que la del prefijo: primero se demuestra que SABE fallar con fugas plantadas,
después se exige que el dataset real pase limpio.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from ccls.fuga_correlacion import NO_SOLO_DOCS, SOLO_DOCS, Token, bloques_changelog, medir, sospechosas

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET = REPO_ROOT / "data" / "processed" / "dataset.jsonl"

PATCH = "+'svelte': patch"
CODIGO = ["a.ts"]
DOC = ["docs/guia.md"]


def _reg(label: str, diff: str = "", repo: str = "r/x", files: list[str] = CODIGO) -> dict:
    return {"label": label, "repo": repo, "message": "mensaje", "diff": diff, "files": files}


def _dataset(n_fix=550, n_feat=160, n_refactor=80, n_docs=210, token_en=None, frac=0.9, diff=PATCH):
    """1.000 registros que tocan código, con la proporción de clases del dataset real.
    `token_en` pone `diff` en una fracción `frac` de esa clase."""
    regs = []
    for label, n in (("fix", n_fix), ("feat", n_feat), ("refactor", n_refactor), ("docs", n_docs)):
        con = int(n * frac) if label == token_en else 0
        regs += [_reg(label, diff) for _ in range(con)] + [_reg(label) for _ in range(n - con)]
    return regs


def _commits_solo_docs(n_docs=300, n_fix=5):
    """Commits que solo tocan .md: casi todos docs, como en el dataset real (98,9%)."""
    return [_reg("docs", files=DOC) for _ in range(n_docs)] + [_reg("fix", files=DOC) for _ in range(n_fix)]


def _nombres(ms):
    return {(m.token, m.ambito, m.estrato, m.clase) for m in ms}


def _diff_de(ruta: str, lineas: str) -> str:
    return f"diff --git a/{ruta} b/{ruta}\n--- a/{ruta}\n+++ b/{ruta}\n@@ -1 +1 @@\n{lineas}"


def test_detecta_fuga_en_la_clase_mayoritaria():
    ms = sospechosas(medir(_dataset(token_en="fix")))
    assert ("changeset: bump patch", "todos", NO_SOLO_DOCS, "fix") in _nombres(ms)


def test_el_cociente_crudo_no_habria_bastado():
    """Fuga perfecta en fix (55%): P(t|c)/P(t) no llega a 1,82. Un umbral sobre ese
    cociente no la separa del ruido; la ganancia normalizada sí."""
    m = next(
        m for m in medir(_dataset(token_en="fix", frac=1.0), por_repo=False)
        if m.token == "changeset: bump patch" and m.clase == "fix" and m.estrato == NO_SOLO_DOCS
    )
    assert m.p_token_en_clase / m.p_token < 1.82
    assert m.ganancia > 0.9
    assert m.sospechosa()


def test_detecta_fuga_en_una_clase_minoritaria():
    ms = sospechosas(medir(_dataset(token_en="refactor", diff="+'svelte': minor")))
    assert ("changeset: bump minor", "todos", NO_SOLO_DOCS, "refactor") in _nombres(ms)


def test_detecta_fuga_confinada_a_un_repo():
    regs = _dataset() + [_reg("feat", PATCH, repo="r/chico") for _ in range(25)] + [_reg("fix", repo="r/chico") for _ in range(75)]
    ms = sospechosas(medir(regs))
    assert ("changeset: bump patch", "r/chico", NO_SOLO_DOCS, "feat") in _nombres(ms)


def test_token_repartido_como_las_clases_no_dispara():
    uniforme = Token("uniforme", re.compile(r"algo"), "diff")
    regs = []
    for label, n in (("fix", 550), ("feat", 160), ("refactor", 80), ("docs", 210)):
        regs += [_reg(label, "+algo" if i % 3 == 0 else "") for i in range(n)]
    assert sospechosas(medir(regs, tokens=[uniforme])) == []


def test_pocos_registros_no_disparan():
    regs = _dataset() + [_reg("docs", PATCH) for _ in range(5)]
    assert sospechosas(medir(regs)) == []


# --- Estratos (decisión del 2026-09-15) ---------------------------------------------


def test_changelog_en_commits_solo_docs_no_dispara_con_estratos():
    """El caso de angular-cli: commits que solo tocan CHANGELOG.md, todos docs. Sin
    estratos la prueba falla; dentro de "solo docs" el token no dice nada más que la
    regla estructural, y no falla."""
    changelog = _diff_de("CHANGELOG.md", "+# 1.2.3")
    regs = _dataset() + _commits_solo_docs() + [_reg("docs", changelog, files=["CHANGELOG.md"]) for _ in range(130)]
    sin_estratos = sospechosas(medir(regs, estratificar=False))
    assert ("changelog: ruta", "todos", "sin estratos", "docs") in _nombres(sin_estratos)
    assert sospechosas(medir(regs)) == []


def test_estratos_no_esconden_una_fuga_hacia_docs_en_commits_con_codigo():
    ms = sospechosas(medir(_dataset(token_en="docs")))
    assert ("changeset: bump patch", "todos", NO_SOLO_DOCS, "docs") in _nombres(ms)


def test_dentro_de_solo_docs_se_ve_una_fuga_hacia_otra_clase():
    regs = _dataset() + _commits_solo_docs() + [_reg("feat", PATCH, files=DOC) for _ in range(40)]
    ms = sospechosas(medir(regs))
    assert ("changeset: bump patch", "todos", SOLO_DOCS, "feat") in _nombres(ms)


def test_costo_declarado_no_ve_una_fuga_hacia_docs_dentro_de_solo_docs():
    """Documenta el punto ciego, no lo celebra: con P(docs) ~99% en el estrato, ni un
    token presente en todos los docs y en ningún otro commit alcanza el umbral."""
    regs = _dataset() + [_reg("docs", PATCH, files=DOC) for _ in range(300)] + [_reg("fix", files=DOC) for _ in range(5)]
    assert sospechosas(medir(regs)) == []


# --- Token "changelog: entrada con scope" -------------------------------------------

TIPO_OPCION = "+- **Type:** `boolean`\n+- **Default:** `false`"


def test_bloques_changelog_se_queda_solo_con_los_changelog():
    diff = _diff_de("docs/config/index.md", TIPO_OPCION) + "\n" + _diff_de("packages/x/CHANGELOG.md", "+* **core:** algo")
    bloques = bloques_changelog(diff)
    assert "**core:**" in bloques
    assert "**Type:**" not in bloques


def test_documentacion_de_opciones_no_cuenta_como_entrada_de_changelog():
    """El falso positivo de vitest y vite: un feat que agrega una opción y la documenta."""
    diff = _diff_de("docs/config/index.md", TIPO_OPCION)
    regs = _dataset(token_en="feat", diff=diff)
    assert not any(m.token == "changelog: entrada con scope" for m in sospechosas(medir(regs)))


def test_entrada_con_scope_dentro_de_un_changelog_si_dispara():
    diff = _diff_de("CHANGELOG.md", "+* **core:** agrega algo")
    ms = sospechosas(medir(_dataset(token_en="feat", diff=diff)))
    assert ("changelog: entrada con scope", "todos", NO_SOLO_DOCS, "feat") in _nombres(ms)


@pytest.mark.skipif(not DATASET.exists(), reason="no hay dataset en data/processed/ todavía (F0 sin correr)")
def test_dataset_real_sin_fuga_por_correlacion():
    from ccls.stats import cargar_jsonl

    ms = sospechosas(medir(cargar_jsonl(DATASET)))
    detalle = [
        f"{m.token} [{m.ambito} | {m.estrato}] -> {m.clase}: {m.n_token_clase}/{m.n_token} "
        f"(P(c)={m.p_clase:.1%}, ganancia={m.ganancia:.2f})"
        for m in ms
    ]
    assert not ms, "fuga por correlación:\n" + "\n".join(detalle)
