"""El reporte de la F5 (docs/F5_DESDE_CERO.md).

Lo que se prueba son las reglas que el informe tiene que cumplir aunque los números
cambien: el veredicto sale de los números y se da contra las dos referencias, la aleatoria
no entra en la cuenta de folds honestos, la detección de corridas colapsadas sale de las
matrices de confusión y si falta una partición de §7.1 el reporte lo dice.
"""

from __future__ import annotations

import pytest

from ccls import f5
from test_f2 import FOLDS_REPO, _doc
from test_f4 import _con_montaje, _iv


def test_colapsadas_cuenta_las_corridas_que_predicen_casi_siempre_una_clase():
    todo_fix = [[10, 0, 0, 0], [10, 0, 0, 0], [10, 0, 0, 0], [10, 0, 0, 0]]
    repartida = [[10, 1, 0, 0], [2, 8, 0, 0], [1, 0, 3, 0], [0, 0, 0, 9]]
    doc = {"corridas": [{"confusion": todo_fix}, {"confusion": repartida}, {"confusion": todo_fix}]}
    assert f5.colapsadas(doc) == (2, 3)


def test_colapsadas_respeta_el_umbral():
    # 9 de 10 predicciones en la columna 0: justo el 90%
    doc = {"corridas": [{"confusion": [[9, 1, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]}]}
    assert f5.colapsadas(doc, umbral=0.9) == (1, 1)
    assert f5.colapsadas(doc, umbral=0.95) == (0, 1)


@pytest.fixture
def resultados() -> dict[str, dict[str, dict]]:
    # los tres modelos dan F1 macro 0,7 con intervalo ±0,01: todo fold es empate
    def trio(folds, n_refactor):
        return {m: _con_montaje(_doc(m, folds, n_refactor)) for m in (f5.MODELO, f5.CODEBERT, f5.CLASICO)}
    return {
        "aleatoria": trio(("aleatoria",), (160,)),
        "repositorio": trio(FOLDS_REPO, (468, 0)),
        "temporal": trio(("temporal",), (176,)),
    }


def _seccion(md: str, titulo: str) -> str:
    return md.split(titulo)[1].split("\n## ")[0]


def test_el_veredicto_va_contra_las_dos_referencias(resultados):
    md = f5.render(resultados, [1, 2, 3, 4, 5], "0177140c")
    clasico = _seccion(md, f"`{f5.MODELO}` contra `{f5.CLASICO}`, fold por fold")
    codebert = _seccion(md, f"`{f5.MODELO}` contra `{f5.CODEBERT}`, fold por fold")
    # 2 folds por repositorio + 1 temporal; la aleatoria está en la tabla pero no cuenta
    assert "En los 3 folds honestos" in clasico and "0 gana, 3 empata, 0 pierde" in clasico
    assert "En los 3 folds honestos" in codebert and "0 gana, 3 empata, 0 pierde" in codebert
    assert "| aleatoria | aleatoria |" in clasico
    assert "la media del clásico" in clasico and "la media de CodeBERT" in codebert


def test_el_veredicto_sale_de_los_numeros(resultados):
    resultados["repositorio"][f5.MODELO]["resumen"][0]["f1_macro"] = _iv(0.60)
    md = f5.render(resultados, [1], "0177140c")
    assert "0 gana, 2 empata, 1 pierde" in _seccion(md, f"`{f5.MODELO}` contra `{f5.CLASICO}`, fold por fold")
    assert "0 gana, 2 empata, 1 pierde" in _seccion(md, f"`{f5.MODELO}` contra `{f5.CODEBERT}`, fold por fold")


def test_las_dos_secciones_por_clase_tienen_titulo_distinto(resultados):
    md = f5.render(resultados, [1], "0177140c")
    assert f"## Qué clase gana y cuál pierde, contra `{f5.CLASICO}`" in md
    assert f"## Qué clase gana y cuál pierde, contra `{f5.CODEBERT}`" in md


def test_refactor_lleva_los_tres_modelos_y_su_n(resultados):
    md = f5.render(resultados, [1], "0177140c")
    seccion = _seccion(md, "## `refactor`, fold por fold")
    assert f"`{f5.MODELO}` | `{f5.CODEBERT}` | `{f5.CLASICO}`" in seccion
    assert "| angular/angular-cli | 468 |" in seccion


def test_si_falta_una_particion_barajada_el_reporte_lo_dice(resultados):
    barajadas = {"repositorio": _doc(f5.MODELO, FOLDS_REPO, (468, 0), exactitud=0.45)}
    md = f5.render(resultados, [1], "0177140c", barajadas, tolerancia=0.02)
    assert "2 folds: 2 pasan" in _seccion(md, "## La prueba de etiquetas aleatorias")
    assert "**Falta correr:** aleatoria, temporal." in md
    colapso = _seccion(md, "## Cuántas corridas responden siempre lo mismo")
    assert "| aleatoria | 0 de 2 | sin correr |" in colapso


def test_sin_barajadas_no_hay_seccion_de_fuga_ni_de_colapso(resultados):
    md = f5.render(resultados, [1], "0177140c")
    assert "La prueba de etiquetas aleatorias" not in md
    assert "responden siempre lo mismo" not in md


def test_el_montaje_dice_que_no_es_la_mejor_red_posible(resultados):
    md = f5.render(resultados, [1], "0177140c")
    assert "No es la mejor red desde cero posible" in md
    assert "| `tasa_aprendizaje` | `5e-05` |" in md
