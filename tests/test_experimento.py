"""Infraestructura de la F1: métricas, intervalos, el runner y la prueba de etiquetas
aleatorias (LEAKAGE.md §7.1). Igual que las otras pruebas de fuga, esta tiene que saber
fallar: un modelo que lee la etiqueta se atrapa en cuanto el runner se la deja ver."""

from __future__ import annotations

import json
from collections import Counter

import pytest

from ccls import experimento, metricas
from ccls.modelos import Mayoritaria
from ccls.stats import CLASES

CFG = {"aleatoria": {"fraccion_prueba": 0.25}, "temporal": {"corte": "2023-01-01T00:00:00+00:00"}}
PALABRA = {"fix": "corrige", "feat": "agrega", "refactor": "reorganiza", "docs": "documenta"}


def _registros(n: int = 400) -> list[dict]:
    """Proporción de clases parecida al dataset real (fix mayoritaria). El mensaje trae
    una palabra que delata la clase: el control tiene que aprender algo."""
    regs = []
    for i in range(n):
        label = ("fix", "fix", "fix", "feat", "docs", "refactor", "fix", "docs")[i % 8]
        repo = f"org/r{i % 3}"
        regs.append({
            "id": f"{repo}@{i:040d}", "repo": repo, "sha": f"{i:040d}", "label": label,
            "committer_date": f"{2020 + i % 5}-06-01T00:00:00+00:00",
            "message": f"{PALABRA[label]} el módulo {i % 17}", "diff": "", "files": ["a.ts"], "n_files": 1,
            "lines_added": 1, "lines_deleted": 0, "n_binarios": 0, "extensiones": [".ts"],
            "toca_tests": False, "toca_docs": label == "docs",
            "auditoria": {"tipo_declarado": label},
        })
    return regs


class Tramposo(Mayoritaria):
    """Predice la etiqueta si el registro la trae. Sin ella, la clase mayoritaria."""

    def predict(self, X):
        return [r.get("label", self.clase_) for r in X]


FABRICAS = {"tramposo": lambda s: Tramposo(), "trivial": lambda s: Mayoritaria()}


# --- métricas ------------------------------------------------------------------

def test_evaluar_confusion_y_f1_por_clase():
    verdad = ["fix", "fix", "fix", "feat", "docs"]
    pred = ["fix", "fix", "feat", "feat", "fix"]
    m = metricas.evaluar(verdad, pred, CLASES)
    assert m["confusion"][0] == [2, 1, 0, 0]  # fila fix
    assert m["exactitud"] == pytest.approx(3 / 5)
    assert m["tasa_mayoritaria"] == pytest.approx(3 / 5)
    assert m["por_clase"]["fix"]["f1"] == pytest.approx(2 * 2 / (3 + 3))
    assert m["por_clase"]["docs"]["f1"] == 0.0  # tiene ejemplos y ninguno acertado
    # sin ejemplos en prueba la F1 no existe, y no entra en la macro
    assert m["por_clase"]["refactor"] == {"n_prueba": 0, "n_predichos": 0, "precision": None, "cobertura": None, "f1": None}
    assert m["f1_macro"] == pytest.approx((4 / 6 + 2 / 3 + 0.0) / 3)


def test_intervalo_t_student():
    iv = metricas.intervalo([0.80, 0.82, 0.84, 0.86, 0.88])
    assert iv["media"] == pytest.approx(0.84)
    # t(0.975, 4) = 2.7764; s = 0.0316
    assert iv["ic_sup"] - iv["media"] == pytest.approx(2.7764 * 0.0316228 / 5 ** 0.5, rel=1e-3)
    assert metricas.intervalo([0.5])["ic_inf"] is None
    assert metricas.intervalo([0.5, None]) is None


# --- runner --------------------------------------------------------------------

def test_barajar_conserva_las_clases_y_no_depende_de_la_etiqueta():
    regs = _registros()
    y = [r["label"] for r in regs]
    ids = [r["id"] for r in regs]
    b = experimento.barajar(y, ids, semilla=1)
    assert Counter(b) == Counter(y)
    assert b != y
    assert b == experimento.barajar(y, ids, semilla=1)
    assert b != experimento.barajar(y, ids, semilla=2)
    # la permutación sale de los ids: con otras etiquetas, las mismas posiciones se mueven igual
    otras = [f"x{i}" for i in range(len(y))]
    perm = experimento.barajar(otras, ids, semilla=1)
    assert b == [y[int(p[1:])] for p in perm]


def test_el_modelo_solo_recibe_las_entradas():
    vistos = []

    class Espia(Mayoritaria):
        def fit(self, X, y):
            vistos.extend(X)
            return super().fit(X, y)

    experimento.correr(_registros(), "espia", "aleatoria", [1], CFG, fabricas={"espia": lambda s: Espia()})
    assert vistos and all(set(r) == set(experimento.ENTRADAS) for r in vistos)


def test_resumen_agrega_semillas_dentro_del_fold_nunca_entre_folds():
    res = experimento.correr(_registros(), "trivial", "repositorio", [1, 2, 3], CFG, fabricas=FABRICAS)
    assert len(res["corridas"]) == 3 * 3
    assert [r["fold"] for r in res["resumen"]] == ["org/r0", "org/r1", "org/r2"]
    for r in res["resumen"]:
        assert r["exactitud"]["n"] == 3


def test_guardar_es_determinista(tmp_path):
    res = experimento.correr(_registros(), "trivial", "temporal", [1, 2], CFG, fabricas=FABRICAS)
    p1 = experimento.guardar(res, "abc", tmp_path / "uno")
    p2 = experimento.guardar(res, "abc", tmp_path / "dos")
    assert p1.name == "trivial__temporal.json"
    assert p1.read_bytes() == p2.read_bytes()
    doc = json.loads(p1.read_text(encoding="utf-8"))
    assert doc["dataset"]["manifest_sha256"] == "abc"
    assert "scikit-learn" in doc["versiones"]


# --- §7.1 · etiquetas aleatorias -------------------------------------------------

def _prueba_71(modelo: str, particion: str, entradas=experimento.ENTRADAS, fabricas=None):
    regs = _registros()
    kw = {"entradas": entradas, "fabricas": fabricas or FABRICAS}
    barajado = experimento.correr(regs, modelo, particion, [1, 2, 3], CFG, barajar_etiquetas=True, **kw)
    control = experimento.correr(regs, modelo, particion, [1, 2, 3], CFG, **kw)
    return experimento.evaluar_fuga_aleatoria(barajado, control, tolerancia=0.02)


@pytest.mark.parametrize("particion", ["aleatoria", "repositorio", "temporal"])
def test_71_falla_si_el_modelo_ve_la_etiqueta(particion):
    filas = _prueba_71("tramposo", particion, entradas=None)
    assert filas and all(f["estado"] == "falla" for f in filas)


@pytest.mark.parametrize("particion", ["aleatoria", "repositorio", "temporal"])
def test_71_el_mismo_tramposo_no_puede_hacer_trampa_con_las_entradas(particion):
    # con ENTRADAS la etiqueta no llega: predice la mayoritaria, y el control tampoco aprende
    filas = _prueba_71("tramposo", particion)
    assert all(f["estado"] == "no concluyente" for f in filas)


def test_71_pasa_con_el_modelo_de_humo():
    filas = _prueba_71("humo", "aleatoria", fabricas=experimento.MODELOS)
    assert [f["estado"] for f in filas] == ["pasa"]
    assert filas[0]["exactitud_control"]["media"] > 0.9  # la palabra delata la clase


def test_71_render_resume_los_estados():
    filas = _prueba_71("tramposo", "temporal", entradas=None)
    md = experimento.render_fuga_aleatoria({"temporal": filas}, "tramposo", [1, 2, 3], 0.02, "abc")
    assert "0 pasan, 1 fallan, 0 no concluyentes" in md
