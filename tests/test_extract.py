"""Verifica el parseo de `git log --numstat` (gitutil.log_numstat) contra un repo
git real y diminuto, creado al vuelo. Esto se corre ANTES de apuntar el pipeline a
repos reales grandes — si el parser tiene un bug, es mucho más barato descubrirlo
aquí que a mitad de un clonado de 40.000 commits.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ccls.gitutil import log_numstat, rev_counts


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True)


@pytest.fixture
def repo_juguete(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", "-b", "main", cwd=repo)
    _git("config", "user.email", "test@example.com", cwd=repo)
    _git("config", "user.name", "Test", cwd=repo)

    (repo / "a.py").write_text("print('hola')\n")
    _git("add", "a.py", cwd=repo)
    _git("commit", "-q", "-m", "feat(core): primer commit", cwd=repo)

    (repo / "a.py").write_text("print('hola')\nprint('mundo')\n")
    (repo / "b.md").write_text("# doc\n")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "fix: corrige el saludo\n\nfixes #12", cwd=repo)

    # commit con cuerpo multilínea
    (repo / "c.py").write_text("x = 1\n")
    _git("add", "-A", cwd=repo)
    _git(
        "commit", "-q", "-m",
        "refactor(core)!: reordena módulos\n\nBREAKING CHANGE: cambia la API pública\nsegunda línea del cuerpo",
        cwd=repo,
    )

    return repo


def test_log_numstat_parsea_los_tres_commits(repo_juguete: Path):
    commits, resultado = log_numstat(repo_juguete, no_merges=True, first_parent=True)
    assert resultado.ok, resultado.stderr
    assert len(commits) == 3

    # git log los devuelve del más nuevo al más viejo
    c_refactor, c_fix, c_feat = commits

    assert c_feat.subject == "feat(core): primer commit"
    assert [f[2] for f in c_feat.files] == ["a.py"]

    assert c_fix.subject == "fix: corrige el saludo"
    assert c_fix.body == "fixes #12"
    assert {f[2] for f in c_fix.files} == {"a.py", "b.md"}

    assert c_refactor.subject == "refactor(core)!: reordena módulos"
    assert "BREAKING CHANGE" in c_refactor.body
    assert "segunda línea del cuerpo" in c_refactor.body
    assert [f[2] for f in c_refactor.files] == ["c.py"]


def test_rev_counts_sobre_repo_lineal_sin_merges(repo_juguete: Path):
    counts = rev_counts(repo_juguete)
    assert counts["total"] == 3
    assert counts["no_merges"] == 3  # no hay merges, nada que perder
    assert counts["first_parent"] == 3
    assert counts["no_merges_first_parent"] == 3


@pytest.fixture
def repo_con_merge(tmp_path: Path) -> Path:
    """Simula el caso que preocupa a B2.4: una rama con dos commits etiquetados
    fusionada con un merge commit (no squash). --no-merges descarta el merge en sí,
    pero --first-parent NO debería tirar los commits de la rama fusionada si se
    camina con `git log --first-parent` desde la rama que los contiene via merge:
    de hecho, --first-parent SÍ los excluye porque solo seguirá el primer padre
    del merge (la rama main), que es exactamente el comportamiento que el piloto
    necesita cuantificar.
    """
    repo = tmp_path / "repo_merge"
    repo.mkdir()
    _git("init", "-q", "-b", "main", cwd=repo)
    _git("config", "user.email", "test@example.com", cwd=repo)
    _git("config", "user.name", "Test", cwd=repo)

    (repo / "a.py").write_text("1\n")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "feat: base", cwd=repo)

    _git("checkout", "-q", "-b", "rama", cwd=repo)
    (repo / "b.py").write_text("2\n")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "fix: en la rama 1", cwd=repo)
    (repo / "c.py").write_text("3\n")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "feat: en la rama 2", cwd=repo)

    _git("checkout", "-q", "main", cwd=repo)
    (repo / "d.py").write_text("4\n")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "docs: en main mientras tanto", cwd=repo)

    _git("merge", "-q", "--no-ff", "rama", "-m", "Merge branch 'rama'", cwd=repo)

    return repo


def test_first_parent_excluye_commits_de_rama_fusionada(repo_con_merge: Path):
    counts = rev_counts(repo_con_merge)
    assert counts["total"] == 5  # base, fix, feat, docs, merge
    assert counts["no_merges"] == 4  # se descarta solo el commit de merge
    assert counts["first_parent"] == 3  # base, docs, merge: NO ve fix/feat de la rama
    assert counts["no_merges_first_parent"] == 2  # base, docs: pierde fix Y feat

    # Esto es exactamente el riesgo de B2.4: 2 de 5 commits reales (40%) desaparecen
    # con la combinación por defecto porque vivían en una rama fusionada sin squash.
    commits, resultado = log_numstat(repo_con_merge, no_merges=True, first_parent=True)
    assert resultado.ok, resultado.stderr
    subjects = {c.subject for c in commits}
    assert subjects == {"feat: base", "docs: en main mientras tanto"}
    assert "fix: en la rama 1" not in subjects
    assert "feat: en la rama 2" not in subjects
