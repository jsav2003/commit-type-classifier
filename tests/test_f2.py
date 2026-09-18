"""El reporte de la F2 (docs/F2_BASELINES.md).

Lo que se prueba no es que el markdown quede bonito, sino las tres reglas que el
informe tiene que cumplir aunque los números cambien:

- `refactor` va fold por fold, con el n al lado, y sin fila de promedio (DESIGN.md §5).
- Una clase sin ejemplos en prueba sale como `—`, no como 0 (§7.4).
- Cada experimento recibe exactamente las entradas que declara, ni una más.
"""

from __future__ import annotations

import pytest

from ccls import experimento, f2

FOLDS_REPO = ("angular/angular-cli", "sveltejs/svelte")


def _intervalo(media: float | None) -> dict | None:
    return None if media is None else {"n": 5, "media": media, "ic_inf": media - 0.01, "ic_sup": media + 0.01}


def _resumen_fold(fold: str, n_refactor: int, exactitud: float = 0.8) -> dict:
    return {
        "fold": fold,
        "n_prueba": 2000,
        "exactitud": _intervalo(exactitud),
        "f1_macro": _intervalo(0.7),
        "tasa_mayoritaria": _intervalo(0.5),
        "por_clase": {
            "fix": {"n_prueba": 1000, "f1": _intervalo(0.85)},
            "feat": {"n_prueba": 300, "f1": _intervalo(0.6)},
            # sin ejemplos en prueba: la F1 no existe
            "refactor": {"n_prueba": n_refactor, "f1": _intervalo(0.4 if n_refactor else None)},
            "docs": {"n_prueba": 400, "f1": _intervalo(0.88)},
        },
    }


def _doc(modelo: str, folds: tuple[str, ...], n_refactor: tuple[int, ...], exactitud: float = 0.8) -> dict:
    return {
        "experimento": {"modelo": modelo, "particion": "x", "etiquetas_barajadas": False,
                        "semillas": [1, 2, 3, 4, 5], "entradas": list(experimento.ENTRADAS)},
        "resumen": [_resumen_fold(f, n, exactitud) for f, n in zip(folds, n_refactor, strict=True)],
        "corridas": [
            {"semilla": s, "fold": f, "confusion": [[10, 1, 0, 0], [2, 8, 0, 0], [1, 0, 3, 0], [0, 0, 0, 9]]}
            for f in folds for s in (1, 2)
        ],
    }


@pytest.fixture
def resultados() -> dict[str, dict[str, dict]]:
    modelos = [e.modelo for e in f2.EXPERIMENTOS]
    return {
        "aleatoria": {m: _doc(m, ("aleatoria",), (160,)) for m in modelos},
        # svelte aporta 1 solo refactor (DESIGN.md §5); aquí, 0: la F1 no existe
        "repositorio": {m: _doc(m, FOLDS_REPO, (468, 0)) for m in modelos},
        "temporal": {m: _doc(m, ("temporal",), (176,)) for m in modelos},
    }


def test_refactor_va_por_fold_con_el_n_y_sin_promedio(resultados):
    md = f2.render(resultados, [1, 2, 3, 4, 5], "0177140c")
    seccion = md.split("## `refactor`, fold por fold")[1].split("\n## ")[0]
    assert "| angular/angular-cli | 468 |" in seccion
    assert "| sveltejs/svelte | 0 |" in seccion
    # la palabra "promedio" solo puede aparecer en la advertencia, nunca como fila
    assert "no hay fila de promedio" in seccion
    assert not any(l.lower().startswith("| promedio") or l.lower().startswith("| media") for l in seccion.split("\n"))


def test_clase_sin_ejemplos_sale_como_raya_y_no_como_cero(resultados):
    md = f2.render(resultados, [1], "0177140c")
    seccion = md.split("## `refactor`, fold por fold")[1].split("\n## ")[0]
    fila_svelte = next(l for l in seccion.split("\n") if l.startswith("| sveltejs/svelte |"))
    assert "—" in fila_svelte
    assert "0,0%" not in fila_svelte


def test_refactor_no_aparece_en_las_tablas_por_particion(resultados):
    """Si `refactor` se colara en la tabla general volvería a promediarse entre folds."""
    md = f2.render(resultados, [1], "0177140c")
    cabeceras = [l for l in md.split("\n") if l.startswith("| modelo |")]
    assert cabeceras
    assert all("refactor" not in c for c in cabeceras)


def test_el_reporte_nombra_la_regla_de_docs_como_forma_de_leerlo(resultados):
    md = f2.render(resultados, [1], "0177140c")
    assert "regla_docs" in md.split("## Cómo hay que leer esto")[1].split("\n## ")[0]


def test_cada_experimento_declara_sus_entradas(resultados):
    for e in f2.EXPERIMENTOS:
        assert e.entradas[: len(experimento.ENTRADAS)] == experimento.ENTRADAS
        if e.modelo == "clasico_lr_issue":
            assert e.entradas_extra == ("tiene_referencia_issue",)
        else:
            # ningún otro modelo puede pedir entradas fuera de DESIGN.md §4.3
            assert e.entradas_extra == ()


def test_los_modelos_del_plan_existen_de_verdad():
    from ccls.modelos import MODELOS
    assert {e.modelo for e in f2.EXPERIMENTOS} <= set(MODELOS)
    assert f2.PRINCIPAL in MODELOS


# --- §7.1 sobre el modelo de la F2 ----------------------------------------------

def _barajadas(exactitud: float) -> dict[str, dict]:
    """El mismo montaje con las etiquetas barajadas. El techo del azar de los
    _resumen_fold es 0,5 (tasa_mayoritaria)."""
    return {
        "aleatoria": _doc(f2.PRINCIPAL, ("aleatoria",), (160,), exactitud),
        "repositorio": _doc(f2.PRINCIPAL, FOLDS_REPO, (468, 0), exactitud),
        "temporal": _doc(f2.PRINCIPAL, ("temporal",), (176,), exactitud),
    }


def test_etiquetas_barajadas_pasan_si_no_superan_el_techo_del_azar(resultados):
    md = f2.render(resultados, [1], "0177140c", _barajadas(0.51), tolerancia=0.02)
    seccion = md.split("## La prueba de etiquetas aleatorias")[1].split("\n## ")[0]
    assert "4 folds: 4 pasan, 0 fallan" in seccion


def test_etiquetas_barajadas_fallan_si_el_montaje_aprende_del_ruido(resultados):
    """Si el clásico sacara señal con las etiquetas barajadas, el reporte tiene que
    decir `falla`, no esconderlo."""
    md = f2.render(resultados, [1], "0177140c", _barajadas(0.70), tolerancia=0.02)
    seccion = md.split("## La prueba de etiquetas aleatorias")[1].split("\n## ")[0]
    assert "0 pasan, 4 fallan" in seccion


def test_sin_resultados_barajados_la_seccion_no_se_inventa(resultados):
    assert "La prueba de etiquetas aleatorias" not in f2.render(resultados, [1], "0177140c")


def test_un_intervalo_de_ancho_cero_se_imprime_como_un_solo_numero():
    """En las particiones con división fija y modelo determinista, las cinco semillas
    dan lo mismo. La celda no debe repetir el número tres veces."""
    assert f2._ic({"n": 5, "media": 0.658, "ic_inf": 0.658, "ic_sup": 0.658}) == "65,8%"
    # si el modelo sí depende de la semilla, el intervalo se conserva
    assert "[" in f2._ic({"n": 5, "media": 0.633, "ic_inf": 0.628, "ic_sup": 0.638})
    assert f2._ic(None) == "—"
