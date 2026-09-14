"""Construcción del dataset de la F0 (build.py) sobre un repo git diminuto, creado al
vuelo con fechas controladas. Igual que test_extract.py: si el muestreo o la
limpieza tienen un bug, se ve aquí y no a mitad de 10.000 commits reales.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from ccls.build import asignar_por_estrato, escribir_dataset, extraer_repo, trimestre
from ccls.label import contiene_fuga

OWNER_REPO = "local/juguete"


def test_asignacion_proporcional_suma_el_tope():
    cuotas = asignar_por_estrato({"2020Q1": 10, "2020Q2": 30, "2020Q3": 60}, tope=10)
    assert cuotas == {"2020Q1": 1, "2020Q2": 3, "2020Q3": 6}


def test_asignacion_reparte_restos_de_forma_determinista():
    cuotas = asignar_por_estrato({"b": 1, "a": 1, "c": 1}, tope=2)
    assert sum(cuotas.values()) == 2
    assert cuotas == {"a": 1, "b": 1, "c": 0}  # empate de restos: gana el nombre menor


def test_asignacion_nunca_pide_mas_de_lo_que_hay():
    tamanos = {"x": 1, "y": 7, "z": 500}
    cuotas = asignar_por_estrato(tamanos, tope=300)
    assert sum(cuotas.values()) == 300
    assert all(cuotas[k] <= tamanos[k] for k in tamanos)


def test_asignacion_toma_todo_si_no_llega_al_tope():
    assert asignar_por_estrato({"a": 3, "b": 4}, tope=100) == {"a": 3, "b": 4}


def test_trimestre_se_calcula_en_utc():
    # 23:30 del 31 de marzo en UTC-5 ya es 1 de abril en UTC
    assert trimestre("2021-03-31T23:30:00-05:00") == "2021Q2"
    assert trimestre("2021-01-01T00:00:00+00:00") == "2021Q1"


def _commit(repo: Path, mensaje: str, fecha: str, archivo: str, contenido: str) -> None:
    ruta = repo / archivo
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(contenido, encoding="utf-8")
    env = {**os.environ, "GIT_AUTHOR_DATE": fecha, "GIT_COMMITTER_DATE": fecha}
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", mensaje], cwd=repo, check=True, capture_output=True, env=env)


@pytest.fixture
def base_juguete(tmp_path: Path) -> Path:
    """Directorio base con un repo en la ruta que espera clone.ruta_local."""
    repo = tmp_path / "local__juguete.git"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)

    _commit(repo, "feat(core): primer commit", "2020-02-01T10:00:00+00:00", "a.ts", "export const a = 1\n")
    _commit(repo, "chore: configura el linter", "2020-02-15T10:00:00+00:00", "eslint.json", "{}\n")
    _commit(repo, "sin convención", "2020-05-01T10:00:00+00:00", "b.ts", "export const b = 2\n")
    _commit(
        repo,
        "fix(parser): corrige el caso vacío (#12)\n\n* fix: primer intento\n\n* chore: formato\n\nFixes #11",
        "2020-05-20T10:00:00+00:00", "a.ts", "export const a = 1\nexport const vacio = ''\n",
    )
    _commit(repo, "docs: explica el parser", "2021-08-01T10:00:00+00:00", "docs/parser.md", "# Parser\n")
    _commit(repo, "refactor!: renombra el módulo", "2021-11-01T10:00:00+00:00", "src/test/b.spec.ts", "it('b')\n" * 50)
    return tmp_path


def _sha_head(base: Path) -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=base / "local__juguete.git", capture_output=True, text=True, check=True)
    return r.stdout.strip()


def _extraer(base: Path, **kw):
    params = {"tope": 100, "semilla": 1, "diff_max_chars": 16000, "contexto": 3}
    params.update(kw)
    return extraer_repo(OWNER_REPO, _sha_head(base), base=base, **params)


def test_extraer_repo_etiqueta_limpia_y_trae_diff(base_juguete: Path):
    registros, resumen = _extraer(base_juguete)

    assert resumen["commits"] == 6
    assert resumen["sin_prefijo"] == 1
    assert resumen["prefijo_fuera_de_clases"] == 1  # chore
    assert resumen["etiquetables"] == 4
    assert sorted(r["label"] for r in registros) == ["docs", "feat", "fix", "refactor"]

    fix = next(r for r in registros if r["label"] == "fix")
    assert fix["message"].startswith("corrige el caso vacío (#12)")
    assert "* primer intento" in fix["message"]  # la viñeta del squash queda, el prefijo no
    assert fix["diff"].startswith("diff --git a/a.ts b/a.ts")
    assert fix["tiene_referencia_issue"]
    assert fix["auditoria"] == {"tipo_declarado": "fix", "scope": "(parser)", "breaking": False, "n_archivos_excluidos": 0}

    refactor = next(r for r in registros if r["label"] == "refactor")
    assert refactor["toca_tests"]
    assert refactor["auditoria"]["breaking"]
    assert refactor["lines_added"] == 50

    docs = next(r for r in registros if r["label"] == "docs")
    assert docs["toca_docs"] and not docs["toca_tests"]

    for r in registros:
        assert not contiene_fuga(r["message"]), r["message"]


def test_extraer_repo_trunca_el_diff(base_juguete: Path):
    registros, _ = _extraer(base_juguete, diff_max_chars=40)
    refactor = next(r for r in registros if r["label"] == "refactor")
    assert refactor["diff_truncado"]
    assert len(refactor["diff"]) == 40
    assert refactor["diff_chars"] > 40


def test_extraer_repo_respeta_el_sha_fijado(base_juguete: Path):
    sha_fijado = _sha_head(base_juguete)
    _commit(base_juguete / "local__juguete.git", "feat: llega después del SHA fijado", "2022-01-01T10:00:00+00:00", "c.ts", "c\n")
    registros, resumen = extraer_repo(OWNER_REPO, sha_fijado, tope=100, semilla=1, diff_max_chars=16000, base=base_juguete)
    assert resumen["commits"] == 6
    assert all("después" not in r["message"] for r in registros)


def test_muestreo_estratificado_y_determinista(base_juguete: Path):
    # 4 etiquetables en 4 trimestres distintos (2020Q1, 2020Q2, 2021Q3, 2021Q4): tope 2
    a, _ = _extraer(base_juguete, tope=2)
    b, _ = _extraer(base_juguete, tope=2)
    assert len(a) == 2
    assert [r["sha"] for r in a] == [r["sha"] for r in b]


def test_escribir_dataset_es_identico_byte_a_byte(base_juguete: Path, tmp_path: Path):
    registros, resumen = _extraer(base_juguete)
    params = {"semilla": 1}
    m1 = escribir_dataset(list(registros), [resumen], params, tmp_path / "uno")
    m2 = escribir_dataset(list(reversed(registros)), [resumen], params, tmp_path / "dos")
    assert m1["manifest_sha256"] == m2["manifest_sha256"]
    for nombre in ("dataset.jsonl", "manifest.csv", "dataset_meta.json"):
        assert (tmp_path / "uno" / nombre).read_bytes() == (tmp_path / "dos" / nombre).read_bytes()
    cabecera = (tmp_path / "uno" / "manifest.csv").read_text(encoding="utf-8").splitlines()[0]
    assert cabecera == "repo,sha,label,committer_date"


def test_extraer_repo_excluye_changeset_de_todas_las_entradas(base_juguete: Path):
    repo = base_juguete / "local__juguete.git"
    (repo / ".changeset").mkdir()
    (repo / ".changeset" / "wet-games-fly.md").write_text(
        "---\n'juguete': patch\n---\n\nfix: corrige el export\n", encoding="utf-8"
    )
    _commit(repo, "fix: corrige el export", "2022-03-01T10:00:00+00:00", "a.ts", "export const a = 2\n")

    registros, _ = _extraer(base_juguete, rutas_excluidas=(".changeset/",))
    r = next(r for r in registros if r["message"] == "corrige el export")
    assert r["files"] == ["a.ts"]
    assert r["n_files"] == 1
    assert r["extensiones"] == [".ts"]
    assert (r["lines_added"], r["lines_deleted"]) == (1, 2)
    assert r["diff"].startswith("diff --git a/a.ts b/a.ts")
    assert ".changeset" not in r["diff"] and "patch" not in r["diff"]
    assert r["auditoria"]["n_archivos_excluidos"] == 1

    # sin la exclusión, el changeset sí estaba: el test no pasa por accidente
    sin, _ = _extraer(base_juguete)
    assert ".changeset/wet-games-fly.md" in next(r for r in sin if r["message"] == "corrige el export")["files"]
