"""El análisis de errores (ERROR-ANALYSIS.md).

Lo que se prueba: que la muestra sea determinista y no dependa del orden de entrada, que
pese igual a todos los repos, que una causa que no existe o un estado inventado se rechacen,
y sobre todo que el reporte nunca presente una propuesta como una revisión hecha.
"""

from __future__ import annotations

import random

import pytest

from ccls import errores


def _error(repo: str, i: int) -> dict:
    return {"id": f"{repo}@{i:04d}", "repo": repo, "sha": f"{i:040d}", "label": "fix", "prediccion": "feat",
            "message": f"cambio {i}", "files": ["a.ts", "b.ts"], "n_files": 2, "lines_added": 3, "lines_deleted": 1}


@pytest.fixture
def todos() -> list[dict]:
    return [_error(r, i) for r in ("x/a", "x/b", "x/c") for i in range(40)]


def test_la_muestra_toma_los_mismos_por_repo_y_pesa_igual_a_todos_los_repos(todos):
    muestra = errores.muestrear(todos, por_repo=10)
    assert len(muestra) == 30
    assert {r: sum(e["repo"] == r for e in muestra) for r in ("x/a", "x/b", "x/c")} == {"x/a": 10, "x/b": 10, "x/c": 10}


def test_la_muestra_no_depende_del_orden_de_entrada(todos):
    barajados = todos[:]
    random.Random(7).shuffle(barajados)
    assert [e["id"] for e in errores.muestrear(todos)] == [e["id"] for e in errores.muestrear(barajados)]


def test_la_semilla_cambia_la_muestra(todos):
    assert [e["id"] for e in errores.muestrear(todos, semilla=1)] != [e["id"] for e in errores.muestrear(todos, semilla=2)]


def _muestra(n: int = 4) -> list[dict]:
    return [errores.fila_muestra(_error("x/a", i)) for i in range(n)]


def _meta() -> dict:
    return {"modelo": "clasico_lr_balanceado", "n_commits": 100, "n_errores": 25, "por_repo": 10,
            "commits_por_repo": {"x/a": 100}, "errores_por_repo": {"x/a": 25},
            "errores_por_par": {"fix->feat": 20, "feat->fix": 5}}


def _causas(muestra: list[dict], estado: str = "propuesta", causa: str = "error_modelo") -> dict:
    return {m["id"]: {"id": m["id"], "causa": causa, "estado": estado, "nota": "n"} for m in muestra}


def test_una_causa_que_no_existe_se_rechaza(tmp_path):
    ruta = tmp_path / "causas.csv"
    errores.escribir_causas([{"id": "a", "causa": "inventada", "estado": "propuesta", "nota": ""}], ruta)
    with pytest.raises(ValueError, match="causa desconocida"):
        errores.leer_causas(ruta)


def test_un_estado_que_no_existe_se_rechaza(tmp_path):
    ruta = tmp_path / "causas.csv"
    errores.escribir_causas([{"id": "a", "causa": "mixto", "estado": "aprobada", "nota": ""}], ruta)
    with pytest.raises(ValueError, match="estado desconocido"):
        errores.leer_causas(ruta)


def test_las_causas_de_una_muestra_que_cambio_se_rechazan():
    with pytest.raises(RuntimeError, match="no están en la muestra"):
        errores.unir(_muestra(2), {"otro": {"id": "otro", "causa": "mixto", "estado": "propuesta", "nota": ""}})


def test_una_propuesta_nunca_se_presenta_como_revisada():
    m = _muestra()
    md = errores.render(m, _causas(m, "propuesta"), _meta())
    assert "**0 confirmados** por una persona, **4 propuestos**" in md
    assert "Esto no es todavía un análisis de errores hecho por una persona" in md


def test_con_todo_confirmado_desaparece_el_aviso():
    m = _muestra()
    md = errores.render(m, _causas(m, "confirmada"), _meta())
    assert "**4 confirmados**" in md
    assert "Esto no es todavía" not in md


def test_si_faltan_causas_el_reporte_lo_dice_y_no_inventa_conteos():
    m = _muestra()
    md = errores.render(m, {}, _meta())
    assert "Faltan causas" in md
    assert "## Cuántos errores hay de cada causa" not in md


def test_el_conteo_por_causa_sale_de_las_causas():
    m = _muestra(4)
    causas = _causas(m)
    causas[m[0]["id"]]["causa"] = "mixto"
    md = errores.render(m, causas, _meta())
    seccion = md.split("## Cuántos errores hay de cada causa")[1].split("\n## ")[0]
    assert "| `mixto` | 1 | 25,0% | 0 |" in seccion
    assert "| `error_modelo` | 3 | 75,0% | 0 |" in seccion


def test_una_celda_no_rompe_la_tabla():
    assert "|" not in errores._celda("a | b\nc").replace("\\|", "")
    assert len(errores._celda("x" * 500, 50)) == 50
