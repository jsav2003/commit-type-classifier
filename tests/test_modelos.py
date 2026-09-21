"""Los baselines de la F2 (DESIGN.md §6.1 y §6.2).

La regla de `docs` tiene que ser exactamente la de §6.1 — la misma que estratifica la
prueba de correlación y la que midió el piloto — y el clásico tiene que ver solo lo que
el runner le entrega (experimento.ENTRADAS), nunca la etiqueta ni el repo.
"""

from __future__ import annotations

import pytest

from ccls import experimento
from ccls.modelos import MODELOS, ReglaDocs, rasgos


def _reg(files: list[str], **extra) -> dict:
    r = {
        "message": "corrige el borde", "diff": "", "files": files, "n_files": len(files),
        "lines_added": 3, "lines_deleted": 1, "n_binarios": 0,
        "extensiones": sorted({f.rsplit(".", 1)[-1] and "." + f.rsplit(".", 1)[-1] for f in files if "." in f}),
        "toca_tests": False, "toca_docs": any(f.endswith(".md") for f in files),
        # fuera de ENTRADAS: solo clasico_lr_issue la recibe (f2.EXPERIMENTOS)
        "tiene_referencia_issue": False,
    }
    r.update(extra)
    return r


# --- regla de docs, DESIGN.md §6.1 ---------------------------------------------

def test_regla_docs_predice_docs_solo_si_todos_los_archivos_son_documentacion():
    m = ReglaDocs().fit([], ["fix", "fix", "docs"])
    assert m.clase_ == "fix"
    assert m.predict([_reg(["README.md"])]) == ["docs"]
    assert m.predict([_reg(["a.md", "b.rst", "c.txt"])]) == ["docs"]
    # un solo archivo de código basta para que la regla no dispare
    assert m.predict([_reg(["README.md", "src/a.ts"])]) == ["fix"]
    assert m.predict([_reg(["src/a.ts"])]) == ["fix"]


def test_regla_docs_sin_archivos_no_dispara():
    """Un commit sin archivos (todos excluidos por rutas_excluidas) no es `docs` por
    vacuidad: `all([])` es True y ahí estaría el error."""
    m = ReglaDocs().fit([], ["fix"])
    assert m.predict([_reg([])]) == ["fix"]


def test_regla_docs_es_la_misma_regla_de_la_prueba_de_correlacion():
    from ccls.fuga_correlacion import solo_docs
    m = ReglaDocs().fit([], ["fix"])
    for files in (["a.md"], ["a.md", "b.ts"], [], ["docs/guia.rst"], ["a.MD"]):
        assert (m.predict([_reg(files)]) == ["docs"]) is solo_docs(files)


# --- clásico, DESIGN.md §6.2 ----------------------------------------------------

def test_rasgos_no_inventa_campos_fuera_de_las_entradas():
    """Si un rasgo leyera la etiqueta, el repo o la fecha, esto lo atrapa: el registro
    que recibe el clásico es el que el runner arma con experimento.ENTRADAS."""
    r = {k: v for k, v in _reg(["src/a.ts"]).items() if k in experimento.ENTRADAS}
    assert set(r) == set(experimento.ENTRADAS)  # el registro de prueba es el real, completo
    rasgos([r])  # no debe lanzar KeyError


def test_rasgos_proporcion_con_commit_sin_lineas():
    """Un commit solo de binarios tiene 0 agregadas y 0 eliminadas: la proporción no
    puede ser una división por cero."""
    f = rasgos([_reg(["logo.png"], lines_added=0, lines_deleted=0, n_binarios=1)])[0]
    assert f["proporcion_agregadas"] == 0.5


def test_rasgos_marca_la_regla_de_docs():
    assert rasgos([_reg(["README.md"])])[0]["solo_docs"] == 1.0
    assert "solo_docs" not in rasgos([_reg(["src/a.ts"])])[0]


# El profundo baja ~500 MB y necesita torch: tiene sus propios tests en test_profundo.py
@pytest.mark.parametrize("nombre", sorted(set(MODELOS) - {"f4_codebert"}))
def test_todo_modelo_entrena_y_predice_las_clases_declaradas(nombre):
    from ccls.stats import CLASES
    X = [_reg(["src/a.ts"]) for _ in range(40)] + [_reg(["R.md"]) for _ in range(40)]
    y = (["fix", "feat", "refactor", "fix"] * 10) + (["docs"] * 40)
    pred = MODELOS[nombre](1).fit(X, y).predict(X)
    assert len(pred) == len(X)
    assert set(map(str, pred)) <= set(CLASES)
