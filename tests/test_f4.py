"""El reporte de la F4 (docs/F4_TRANSFER.md).

Como en la F2, lo que se prueba son las reglas que el informe tiene que cumplir aunque
los números cambien: el veredicto por fold sale de los números y no de una frase escrita
a mano, la aleatoria no entra en la cuenta de folds honestos, y si falta una partición de
§7.1 el reporte lo dice.
"""

from __future__ import annotations

import pytest

from ccls import f4
from test_f2 import FOLDS_REPO, _doc


def _iv(media: float, ancho: float = 0.01) -> dict:
    return {"n": 5, "media": media, "ic_inf": media - ancho, "ic_sup": media + ancho}


@pytest.mark.parametrize("ref, esperado", [(0.68, "gana"), (0.70, "empate"), (0.72, "pierde")])
def test_comparar_usa_el_intervalo_del_modelo_nuevo(ref, esperado):
    assert f4.comparar(_iv(0.70), _iv(ref, 0.0)) == esperado


def test_comparar_sin_intervalo_compara_medias():
    sin = {"n": 1, "media": 0.70, "ic_inf": None, "ic_sup": None}
    assert f4.comparar(sin, _iv(0.69, 0.0)) == "gana"
    assert f4.comparar(sin, _iv(0.70, 0.0)) == "empate"


def _con_montaje(doc: dict) -> dict:
    doc["experimento"]["hiperparametros"] = {"tasa_aprendizaje": 5e-5, "epocas": 3}
    doc["versiones"] = {"python": "3.13", "torch": "2.11.0"}
    return doc


@pytest.fixture
def resultados() -> dict[str, dict[str, dict]]:
    # el clásico acierta menos en exactitud (0,6) pero da el mismo F1 macro (0,7) que
    # los _doc de test_f2: con intervalos de ±0,01, todo fold es empate
    def par(folds, n_refactor):
        return {f4.MODELO: _con_montaje(_doc(f4.MODELO, folds, n_refactor)),
                f4.REFERENCIA: _doc(f4.REFERENCIA, folds, n_refactor, exactitud=0.6)}
    return {
        "aleatoria": par(("aleatoria",), (160,)),
        "repositorio": par(FOLDS_REPO, (468, 0)),
        "temporal": par(("temporal",), (176,)),
    }


def _seccion(md: str, titulo: str) -> str:
    return md.split(titulo)[1].split("\n## ")[0]


def test_la_cuenta_de_folds_honestos_no_incluye_la_aleatoria(resultados):
    md = f4.render(resultados, [1, 2, 3, 4, 5], "0177140c")
    seccion = _seccion(md, "contra `clasico_lr_balanceado`, fold por fold")
    # 2 folds por repositorio + 1 temporal; la aleatoria está en la tabla pero no cuenta
    assert "En los 3 folds honestos" in seccion
    assert "0 gana, 3 empata, 0 pierde" in seccion
    assert "| aleatoria | aleatoria |" in seccion


def test_el_veredicto_sale_de_los_numeros(resultados):
    fold = resultados["repositorio"][f4.MODELO]["resumen"][0]
    fold["f1_macro"] = _iv(0.60)
    md = f4.render(resultados, [1], "0177140c")
    assert "0 gana, 2 empata, 1 pierde" in _seccion(md, "fold por fold\n")


def test_refactor_va_por_fold_y_la_clase_vacia_sale_como_raya(resultados):
    md = f4.render(resultados, [1], "0177140c")
    fila = next(l for l in _seccion(md, "## Qué clase gana y cuál pierde").split("\n")
                if l.startswith("| repositorio | sveltejs/svelte |"))
    assert fila.endswith("| — |")
    assert "(n = 468)" in md


def test_si_falta_una_particion_barajada_el_reporte_lo_dice(resultados):
    barajadas = {"repositorio": _doc(f4.MODELO, FOLDS_REPO, (468, 0), exactitud=0.45)}
    md = f4.render(resultados, [1], "0177140c", barajadas, tolerancia=0.02)
    seccion = _seccion(md, "## La prueba de etiquetas aleatorias")
    assert "2 folds: 2 pasan" in seccion
    assert "**Falta correr:** aleatoria, temporal." in seccion


def test_el_montaje_escribe_la_tasa_de_aprendizaje_sin_redondear(resultados):
    md = f4.render(resultados, [1], "0177140c")
    assert "| `tasa_aprendizaje` | `5e-05` |" in md
