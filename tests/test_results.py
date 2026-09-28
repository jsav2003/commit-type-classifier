"""RESULTS.md: los cuatro enfoques juntos.

No calcula nada nuevo; lo que se prueba son las reglas que el documento tiene que cumplir
aunque los números cambien: todos los enfoques en la tabla, el más alto marcado sin llamarlo
ganador, la prueba de fuga contada por modelo y partición, y el aviso de que no hay techo
humano.
"""

from __future__ import annotations

import pytest

from ccls import results
from test_f2 import FOLDS_REPO, _doc
from test_f4 import _iv


@pytest.fixture
def resultados() -> dict[str, dict[str, dict]]:
    def todos(folds, n_refactor):
        return {m: _doc(m, folds, n_refactor) for m in results.NOMBRES}
    return {
        "aleatoria": todos(("aleatoria",), (160,)),
        "repositorio": todos(FOLDS_REPO, (468, 0)),
        "temporal": todos(("temporal",), (176,)),
    }


def _seccion(md: str, titulo: str) -> str:
    return md.split(titulo)[1].split("\n## ")[0]


def test_la_tabla_resumen_lleva_los_cuatro_enfoques(resultados):
    md = results.render(resultados, {}, [1, 2, 3, 4, 5], "0177140c")
    cabecera = next(l for l in _seccion(md, "## La comparación en una tabla").split("\n") if l.startswith("| partición"))
    for modelo in ("trivial", "regla_docs", "clasico_lr", "clasico_lr_balanceado", "f4_codebert", "f5_desde_cero"):
        assert f"`{modelo}`" in cabecera


def test_solo_la_media_mas_alta_va_en_negrita_y_no_se_llama_ganador(resultados):
    resultados["repositorio"]["f4_codebert"]["resumen"][0]["f1_macro"] = _iv(0.80)
    md = results.render(resultados, {}, [1], "0177140c")
    seccion = _seccion(md, "## La comparación en una tabla")
    fila = next(l for l in seccion.split("\n") if l.startswith(f"| repositorio | {FOLDS_REPO[0]} |"))
    assert fila.count("**") == 2 and "**80,0%**" in fila
    assert "no lo hace el ganador" in seccion


def test_la_prueba_de_fuga_se_cuenta_por_modelo_y_particion(resultados):
    barajadas = {
        "clasico_lr": {"repositorio": _doc("clasico_lr", FOLDS_REPO, (468, 0), exactitud=0.4)},
    }
    md = results.render(resultados, barajadas, [1], "0177140c")
    seccion = _seccion(md, "## La prueba de etiquetas aleatorias, en los tres modelos")
    assert "| `clasico_lr` | repositorio | 2 | 2 | 0 | 0 |" in seccion
    # lo que no se corrió se dice, no se calla
    assert "| `f4_codebert` | aleatoria | — | — | — | sin correr |" in seccion


def test_sin_barajadas_no_hay_seccion_de_fuga(resultados):
    md = results.render(resultados, {}, [1], "0177140c")
    assert "La prueba de etiquetas aleatorias" not in md


def test_el_techo_humano_se_declara_pendiente(resultados):
    md = results.render(resultados, {}, [1], "0177140c")
    assert "Hoy no hay techo humano" in _seccion(md, "## El techo humano")


def test_matrices_de_los_tres_enfoques_con_modelo(resultados):
    md = results.render(resultados, {}, [1], "0177140c")
    for modelo in results.CON_MATRIZ:
        assert f"## Matrices de confusión — `{modelo}`, partición por repositorio" in md


def test_cargar_todo_dice_que_falta(tmp_path, monkeypatch):
    monkeypatch.setattr("ccls.f2.cargar.__defaults__", (False, tmp_path))
    _, _, faltan = results.cargar_todo()
    assert len(faltan) == len(results.NOMBRES) * 3
    assert "trivial · aleatoria ('f2 run')" in faltan
