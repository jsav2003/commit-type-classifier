"""F3 · techo humano: muestreo, ceguera de la hoja y reproducibilidad. DESIGN.md §4.2, §7.5."""

import csv
import json
from collections import Counter
from pathlib import Path

import pytest
import yaml

from ccls import f3
from ccls.label import contiene_fuga

CLASES = ("fix", "feat", "refactor", "docs")
CUOTAS = {"fix": 4, "feat": 3, "refactor": 4, "docs": 3}
HOJA = Path("data/processed/f3_hoja.json")
CLAVE = Path("data/processed/f3_clave.csv")
REGISTROS = Path("data/processed/f3_registros.jsonl")


def _registro(repo: str, i: int, label: str | None) -> dict:
    return {
        "id": f"{repo}@{i:040x}", "repo": repo, "sha": f"{i:040x}", "label": label,
        "message": f"cambio {i} en {repo.split('/')[1]}", "files": [f"src/{i}.py"],
        "lines_added": i, "lines_deleted": i // 2, "diff": "secreto-del-diff", "n_files": 1,
        "auditoria": {"tipo_declarado": label},
    }


def _dataset(n_por_clase_repo: int = 12) -> list[dict]:
    out, i = [], 0
    for repo in ("o/uno", "o/dos", "o/tres"):
        for clase in CLASES:
            for _ in range(n_por_clase_repo):
                out.append(_registro(repo, i, clase))
                i += 1
    return out


def _estrato_a(n: int = 20) -> list[dict]:
    return [_registro("x/ajeno", 10_000 + i, None) for i in range(n)]


def _lote(semilla: int = 7, n_a: int = 20, n_rep: int = 6, ventana: int = 18) -> list[dict]:
    b = f3.muestrear_estrato_b(_dataset(), CUOTAS, semilla)
    return f3.armar_lote(_estrato_a(n_a), [dict(r) for r in b], semilla, n_rep, ventana)


def test_cuotas_iguales_reparte_todo_y_es_determinista():
    c = f3.cuotas_iguales(["d", "a", "c", "b"], 150)
    assert sum(c.values()) == 150
    assert max(c.values()) - min(c.values()) <= 1
    assert f3.cuotas_iguales(["b", "a", "c", "d"], 150) == c


def test_estrato_b_respeta_las_cuotas_por_clase_y_no_repite():
    b = f3.muestrear_estrato_b(_dataset(), CUOTAS, 7)
    assert Counter(r["label"] for r in b) == Counter(CUOTAS)
    assert len({r["id"] for r in b}) == len(b)


def test_estrato_b_reparte_entre_repos_en_vez_de_tomarlo_todo_de_uno():
    b = f3.muestrear_estrato_b(_dataset(), CUOTAS, 7)
    assert len({r["repo"] for r in b if r["label"] == "fix"}) > 1


def test_estrato_b_falla_si_el_dataset_no_alcanza():
    with pytest.raises(RuntimeError):
        f3.muestrear_estrato_b(_dataset(1), {"fix": 50}, 7)


def test_lote_tiene_los_dos_estratos_y_las_repeticiones_al_final():
    lote = _lote()
    originales, repeticiones = lote[:-6], lote[-6:]
    assert len(originales) == 20 + sum(CUOTAS.values())
    assert Counter(r["estrato"] for r in originales) == {"A": 20, "B": 14}
    assert all(r["repeticion_de"] == "" for r in originales)
    assert all(r["repeticion_de"] for r in repeticiones)
    assert Counter(r["estrato"] for r in repeticiones) == {"A": 3, "B": 3}


def test_las_repeticiones_apuntan_a_un_item_ya_visto_de_la_ventana():
    lote = _lote()
    pos = {r["f3_id"]: i for i, r in enumerate(lote)}
    for r in lote[-6:]:
        original = lote[pos[r["repeticion_de"]]]
        assert pos[original["f3_id"]] < 18
        assert original["message"] == r["message"]
        assert original["estrato"] == r["estrato"]


def test_ids_unicos_y_consecutivos():
    lote = _lote()
    assert [r["f3_id"] for r in lote] == [f"f3-{i:04d}" for i in range(1, len(lote) + 1)]


def test_los_estratos_quedan_mezclados_en_el_orden():
    primeros = [r["estrato"] for r in _lote()[:14]]
    assert set(primeros) == {"A", "B"}


def test_el_lote_no_depende_del_orden_de_entrada_ni_de_la_corrida():
    a = [(r["f3_id"], r["id"]) for r in _lote(semilla=7)]
    assert a == [(r["f3_id"], r["id"]) for r in _lote(semilla=7)]
    assert a != [(r["f3_id"], r["id"]) for r in _lote(semilla=8)]


def test_repeticiones_falla_si_la_ventana_no_tiene_de_un_estrato():
    b = f3.muestrear_estrato_b(_dataset(), CUOTAS, 7)
    with pytest.raises(RuntimeError):
        f3.armar_lote(_estrato_a(20), [dict(r) for r in b], 7, 6, 1)


def _escribir(tmp_path: Path, lote: list[dict]) -> dict:
    return f3.escribir_lote(lote, {"semilla": 7}, [], "0" * 64, tmp_path)


def test_la_hoja_es_ciega(tmp_path):
    _escribir(tmp_path, _lote())
    hoja = json.loads((tmp_path / "f3_hoja.json").read_text(encoding="utf-8"))
    for item in hoja["items"]:
        assert set(item) == {"id", "message", "files", "lines_added", "lines_deleted"}
    crudo = (tmp_path / "f3_hoja.json").read_text(encoding="utf-8")
    for prohibido in ("secreto-del-diff", "o/uno", "x/ajeno", "declarada", "estrato", "tipo_declarado"):
        assert prohibido not in crudo


def test_escribir_lote_es_identico_byte_a_byte(tmp_path):
    m1 = _escribir(tmp_path / "1", _lote())
    m2 = _escribir(tmp_path / "2", _lote())
    for nombre in ("f3_hoja.json", "f3_clave.csv", "f3_registros.jsonl", "f3_meta.json"):
        assert (tmp_path / "1" / nombre).read_bytes() == (tmp_path / "2" / nombre).read_bytes()
    assert m1["hoja_sha256"] == m2["hoja_sha256"] and m1["clave_sha256"] == m2["clave_sha256"]


def test_la_clave_lleva_la_declarada_solo_en_el_estrato_b(tmp_path):
    _escribir(tmp_path, _lote())
    filas = list(csv.DictReader((tmp_path / "f3_clave.csv").open(encoding="utf-8", newline="")))
    assert tuple(filas[0]) == f3.CLAVE_COLS
    assert all(f["declarada"] in CLASES for f in filas if f["estrato"] == "B")
    assert all(f["declarada"] == "" for f in filas if f["estrato"] == "A")


def test_un_mensaje_con_prefijo_no_llega_a_la_hoja(tmp_path):
    lote = _lote()
    lote[0]["message"] = "fix: esto no debió llegar hasta aquí"
    with pytest.raises(RuntimeError, match="prefijo"):
        _escribir(tmp_path, lote)


# --- sobre los datos reales de esta máquina ------------------------------------------------

_reales = pytest.mark.skipif(not HOJA.exists(), reason="no hay muestra F3 en data/processed/ (correr 'f3 build')")


@_reales
def test_hoja_real_sin_prefijo_ni_columnas_delatoras():
    hoja = json.loads(HOJA.read_text(encoding="utf-8"))
    assert len(hoja["items"]) == 350
    for item in hoja["items"]:
        assert set(item) == {"id", "message", "files", "lines_added", "lines_deleted"}
        assert not contiene_fuga(item["message"]), item["id"]


@_reales
def test_muestra_real_tiene_las_cuotas_del_diseno():
    cfg = yaml.safe_load(Path("config/repos.yaml").read_text(encoding="utf-8"))
    m = cfg["f3_muestreo"]
    filas = list(csv.DictReader(CLAVE.open(encoding="utf-8", newline="")))
    originales = [f for f in filas if not f["repeticion_de"]]
    assert len(filas) == len(originales) + m["n_repeticiones"]
    assert sum(f["estrato"] == "A" for f in originales) == m["n_estrato_a"]
    b = Counter(f["declarada"] for f in originales if f["estrato"] == "B")
    assert dict(b) == m["cuotas_estrato_b"]


@_reales
def test_estrato_a_es_de_repos_ajenos_y_b_es_del_dataset():
    cfg = yaml.safe_load(Path("config/repos.yaml").read_text(encoding="utf-8"))
    f0 = {r["owner_repo"] for r in cfg["f0_repos"]}
    f3r = {r["owner_repo"] for r in cfg["f3_repos"]}
    assert not f0 & f3r
    filas = list(csv.DictReader(CLAVE.open(encoding="utf-8", newline="")))
    assert {f["repo"] for f in filas if f["estrato"] == "A"} <= f3r
    assert {f["repo"] for f in filas if f["estrato"] == "B"} <= f0


@_reales
@pytest.mark.skipif(not REGISTROS.exists(), reason="sin f3_registros.jsonl")
def test_ningun_item_del_estrato_a_tiene_prefijo_de_convencion():
    from ccls.label import clasificar

    for linea in REGISTROS.read_text(encoding="utf-8").splitlines():
        r = json.loads(linea)
        if r["estrato"] == "A":
            assert r["label"] is None
            assert clasificar(r["message"].split("\n")[0]).tipo_declarado is None, r["f3_id"]


# --- etiquetado a mano ---------------------------------------------------------------------

def _hoja(n: int = 5) -> list[dict]:
    return [{"id": f"f3-{i:04d}", "message": f"mensaje {i}", "files": [f"a{i}.py"],
             "lines_added": i, "lines_deleted": 0} for i in range(1, n + 1)]


def _teclas(secuencia: str):
    it = iter(secuencia)
    return lambda: next(it)


def _reloj():
    t = iter(range(0, 10_000, 3))
    return lambda: float(next(t))


def _correr(hoja, path, secuencia):
    salida: list[str] = []
    r = f3.etiquetar(hoja, path, _teclas(secuencia), salida.append, _reloj())
    return r, salida


def test_etiquetar_guarda_cada_respuesta_y_termina(tmp_path):
    ruta = tmp_path / "anot.csv"
    r, _ = _correr(_hoja(3), ruta, "fedq")
    assert r == {"hechas": 3, "total": 3}
    a = f3.leer_anotaciones(ruta)
    assert [x["etiqueta"] for x in a] == ["fix", "feat", "docs"]
    assert [x["id"] for x in a] == ["f3-0001", "f3-0002", "f3-0003"]


def test_etiquetar_se_puede_cortar_y_retomar_sin_duplicar(tmp_path):
    ruta = tmp_path / "anot.csv"
    r1, _ = _correr(_hoja(5), ruta, "frq")
    assert r1["hechas"] == 2
    r2, salida = _correr(_hoja(5), ruta, "dmn")
    assert r2 == {"hechas": 5, "total": 5}
    assert "f3-0003" in salida[0]  # retoma en el tercero
    a = f3.leer_anotaciones(ruta)
    assert [x["id"] for x in a] == [f"f3-{i:04d}" for i in range(1, 6)]
    assert [x["etiqueta"] for x in a] == ["fix", "refactor", "docs", "mixto", "ninguna"]


def test_signo_de_pregunta_marca_necesita_diff_solo_en_ese_item(tmp_path):
    ruta = tmp_path / "anot.csv"
    _correr(_hoja(3), ruta, "?f" "e" "d")
    a = f3.leer_anotaciones(ruta)
    assert [x["necesita_diff"] for x in a] == [True, False, False]


def test_deshacer_borra_la_ultima_respuesta_y_vuelve_a_ese_item(tmp_path):
    ruta = tmp_path / "anot.csv"
    # 1: fix. En el 2 se arrepiente: `u` borra la del 1 y vuelve a él.
    # 1: feat, 2: docs, 3: feat.
    r, salida = _correr(_hoja(3), ruta, "fuedeq")
    assert r == {"hechas": 3, "total": 3}
    a = f3.leer_anotaciones(ruta)
    assert [x["id"] for x in a] == ["f3-0001", "f3-0002", "f3-0003"]
    assert [x["etiqueta"] for x in a] == ["feat", "docs", "feat"]
    assert sum("f3-0001" in s for s in salida) == 2  # se mostró dos veces


def test_deshacer_sin_nada_no_rompe(tmp_path):
    ruta = tmp_path / "anot.csv"
    r, salida = _correr(_hoja(2), ruta, "ufeq")
    assert r["hechas"] == 2
    assert any("nada que deshacer" in s for s in salida)


def test_etiquetar_mide_segundos_por_item(tmp_path):
    ruta = tmp_path / "anot.csv"
    _correr(_hoja(2), ruta, "fe")
    assert all(x["segundos"] > 0 for x in f3.leer_anotaciones(ruta))


def test_una_hoja_distinta_de_la_de_las_anotaciones_se_rechaza(tmp_path):
    ruta = tmp_path / "anot.csv"
    _correr(_hoja(3), ruta, "feq")
    otra = _hoja(3)
    otra[0]["id"] = "f3-9999"
    with pytest.raises(RuntimeError, match="no corresponde"):
        _correr(otra, ruta, "q")


def test_la_pantalla_solo_muestra_lo_de_la_hoja(tmp_path):
    ruta = tmp_path / "anot.csv"
    _, salida = _correr(_hoja(1), ruta, "f")
    pantalla = salida[0]
    assert "mensaje 1" in pantalla and "a1.py" in pantalla
    for prohibido in ("declarada", "estrato", "repo", "sha"):
        assert prohibido not in pantalla.lower()


def test_etiquetado_no_abre_la_clave():
    import inspect

    fuente = inspect.getsource(f3.etiquetar) + inspect.getsource(f3.cargar_hoja) + inspect.getsource(f3.leer_tecla)
    assert "F3_CLAVE_PATH" not in fuente and "f3_clave" not in fuente and "F3_REGISTROS_PATH" not in fuente


# --- acuerdos y reporte, con anotaciones sintéticas ------------------------------------------

import random

from ccls import metricas

PESOS = f3.pesos_del_dataset({"fix": 5522, "feat": 1566, "refactor": 820, "docs": 2092})


def _filas(humano=lambda d, i: d, modelo=lambda d, i: d, cuotas=None, n_a=150, n_rep=50):
    """Una muestra sintética con la forma de la real: B por cuotas, A sin declarada, y
    repeticiones al final. `humano(declarada, i)` decide qué pone la persona."""
    cuotas = cuotas or {"fix": 40, "feat": 35, "refactor": 40, "docs": 35}
    filas = []
    for c, n in cuotas.items():
        for _ in range(n):
            filas.append({"estrato": "B", "declarada": c, "repo": "o/uno"})
    for _ in range(n_a):
        filas.append({"estrato": "A", "declarada": None, "repo": "x/ajeno"})
    for i, f in enumerate(filas, start=1):
        f["id"] = f"f3-{i:04d}"
        f["repeticion_de"] = None
        f["humana"] = humano(f["declarada"], i)
        f["modelo"] = modelo(f["declarada"], i)
        f["necesita_diff"] = i % 10 == 0
        f["segundos"] = 20.0 + i % 7
    for j, f in enumerate(filas[:n_rep]):
        copia = dict(f)
        copia["id"] = f"f3-{len(filas) + j + 1:04d}"
        copia["repeticion_de"] = f["id"]
        filas.append(copia)
    return filas


def _meta_f3():
    return {"hoja_sha256": "h" * 64, "clave_sha256": "c" * 64,
            "parametros": {"semilla": 7, "cuotas_estrato_b": {"fix": 40, "feat": 35, "refactor": 40, "docs": 35}},
            "repos_estrato_a": [{"owner_repo": "x/ajeno", "sha": "a" * 40}]}


def _meta_f0():
    return {"manifest_sha256": "m" * 64, "por_clase": {"fix": 5522, "feat": 1566, "refactor": 820, "docs": 2092}}


def test_pesos_del_dataset_suman_uno():
    assert sum(PESOS.values()) == pytest.approx(1.0)
    assert PESOS["fix"] == pytest.approx(0.5522)


def test_humano_perfecto_da_acuerdo_total_y_kappa_uno():
    B = [f for f in _filas() if f["estrato"] == "B" and not f["repeticion_de"]]
    por_clase = f3.acuerdo_por_clase(B, "humana", "declarada", True)
    p, lo, hi = f3.reponderado(por_clase, PESOS)
    assert p == pytest.approx(1.0) and hi == pytest.approx(1.0)
    assert f3.acuerdo(B, "humana", "declarada", True) == (150, 150)
    assert metricas.kappa_cohen([f["declarada"] for f in B], [f["humana"] for f in B], f3.ETIQUETAS) == 1.0


def test_humano_al_azar_cae_a_la_tasa_base_y_kappa_a_cero():
    rng = random.Random(3)
    filas = _filas(humano=lambda d, i: rng.choice(f3.ETIQUETAS),
                   cuotas={"fix": 400, "feat": 350, "refactor": 400, "docs": 350})
    B = [f for f in filas if f["estrato"] == "B"]
    k, n = f3.acuerdo(B, "humana", "declarada", True)
    assert k / n == pytest.approx(0.25, abs=0.04)
    kappa = metricas.kappa_cohen([f["declarada"] for f in B], [f["humana"] for f in B], f3.ETIQUETAS)
    assert abs(kappa) < 0.06


def test_mixto_y_ninguna_salen_del_denominador_o_cuentan_como_desacuerdo():
    filas = _filas(humano=lambda d, i: "mixto" if d == "fix" and i % 2 == 0 else (d or "fix"))
    B = [f for f in filas if f["estrato"] == "B" and not f["repeticion_de"]]
    mixtos = sum(f["humana"] == "mixto" for f in B)
    assert mixtos > 0
    assert f3.acuerdo(B, "humana", "declarada", True) == (150 - mixtos, 150 - mixtos)
    assert f3.acuerdo(B, "humana", "declarada", False) == (150 - mixtos, 150)


def test_ambas_columnas_de_una_variante_usan_los_mismos_items():
    filas = _filas(humano=lambda d, i: "ninguna" if i % 3 == 0 else (d or "fix"), modelo=lambda d, i: "fix")
    B = [f for f in filas if f["estrato"] == "B" and not f["repeticion_de"]]
    h = f3.acuerdo_por_clase(B, "humana", "declarada", True)
    m = f3.acuerdo_por_clase(B, "modelo", "declarada", True)
    assert {c: n for c, (_, n) in h.items()} == {c: n for c, (_, n) in m.items()}


def test_reponderado_constante_y_sin_clase():
    por_clase = {c: (8, 10) for c in f3.ETIQUETAS}
    p, lo, hi = f3.reponderado(por_clase, PESOS)
    assert p == pytest.approx(0.8) and lo < 0.8 < hi
    assert f3.reponderado({**por_clase, "refactor": (0, 0)}, PESOS) is None


def test_reponderado_pesa_las_clases():
    por_clase = {"fix": (10, 10), "feat": (0, 10), "refactor": (0, 10), "docs": (0, 10)}
    assert f3.reponderado(por_clase, PESOS)[0] == pytest.approx(PESOS["fix"])


def test_unir_falla_si_falta_una_anotacion_o_una_prediccion():
    clave = [{"id": "f3-0001", "estrato": "B", "repo": "o/uno", "sha": "s", "declarada": "fix", "repeticion_de": ""}]
    anot = [{"id": "f3-0001", "etiqueta": "fix", "necesita_diff": False, "segundos": 3.0}]
    with pytest.raises(RuntimeError, match="anotaciones"):
        f3.unir(clave, [], {"f3-0001": "fix"})
    with pytest.raises(RuntimeError, match="predicciones"):
        f3.unir(clave, anot, {})
    fila = f3.unir(clave, anot, {"f3-0001": "docs"})[0]
    assert (fila["humana"], fila["modelo"], fila["declarada"], fila["repeticion_de"]) == ("fix", "docs", "fix", None)


def test_render_pone_la_n_al_lado_y_no_promedia_los_estratos():
    texto = f3.render(_filas(), _meta_f3(), _meta_f0())
    assert texto.startswith("# F3 · Techo humano")
    assert "**No se edita a mano.**" in texto
    assert "`hoja_sha256` `" + "h" * 64 in texto
    # las filas globales solo existen en la sección del techo (2 variantes x 2 filas)
    assert texto.count("| **global,") == 4
    assert "A+B" not in texto and "A y B" not in texto
    # cada fila por clase declarada lleva su n
    assert "| `refactor` | 40 |" in texto and "| `feat` | 35 |" in texto


def test_render_una_clase_sin_items_sale_con_raya_y_no_con_cero():
    filas = _filas(cuotas={"fix": 40, "feat": 35, "refactor": 0, "docs": 35})
    texto = f3.render(filas, _meta_f3(), _meta_f0())
    assert "| `refactor` | 0 | — | — |" in texto
    global_rep = [l for l in texto.splitlines() if l.startswith("| **global, reponderado**")]
    assert global_rep and all("| — |" in l for l in global_rep)


def test_render_avisa_si_el_modelo_supera_al_humano():
    # el humano falla en la mitad de los ítems de B; el modelo es perfecto
    ruidoso = _filas(humano=lambda d, i: d if (d is None or i % 2) else ("docs" if d != "docs" else "fix"))
    assert "El modelo coincide más con la etiqueta declarada" in f3.render(ruidoso, _meta_f3(), _meta_f0())
    assert "El modelo coincide más" not in f3.render(_filas(), _meta_f3(), _meta_f0())


def test_render_ruido_del_anotador_con_pares_identicos():
    texto = f3.render(_filas(), _meta_f3(), _meta_f0())
    fila_b = next(l for l in texto.splitlines() if l.startswith("| B | ") and "%" in l and "[" in l and "pares" not in l)
    assert "100,0%" in fila_b


def test_render_es_determinista_y_lleva_saltos_de_linea_lf():
    a = f3.render(_filas(), _meta_f3(), _meta_f0())
    assert a == f3.render(_filas(), _meta_f3(), _meta_f0())
    assert "\r" not in a


def test_render_sin_doc_de_f2_omite_esa_seccion_y_con_doc_una_fila_por_fold():
    assert "Contra los números de la F2" not in f3.render(_filas(), _meta_f3(), _meta_f0())
    doc = {"resumen": [{"fold": "a/b", "n_prueba": 2000, "exactitud": {"media": 0.8}, "f1_macro": {"media": 0.6}},
                       {"fold": "c/d", "n_prueba": 2000, "exactitud": {"media": 0.7}, "f1_macro": {"media": 0.5}}]}
    texto = f3.render(_filas(), _meta_f3(), _meta_f0(), doc)
    assert "| `a/b` | 2000 | 80,0% | 60,0% |" in texto and "| `c/d` | 2000 | 70,0% | 50,0% |" in texto
    filas_tabla = [l for l in texto.splitlines() if l.startswith("| ")]
    assert not any("promedio" in l.lower() or "media" in l.lower().split("|")[1] for l in filas_tabla)


def test_predecir_devuelve_una_prediccion_por_item_entrenada_sin_ese_repo():
    dataset = []
    for repo in ("o/uno", "o/dos"):
        for i in range(12):
            for c in f3.ETIQUETAS:
                r = _registro(repo, len(dataset), c)
                r.update({"lines_added": 1, "lines_deleted": 1, "n_binarios": 0, "extensiones": [".py"],
                          "toca_tests": False, "toca_docs": False, "message": f"{c} cosa {i}", "diff": ""})
                dataset.append(r)
    b = f3.muestrear_estrato_b(dataset, {"fix": 2, "feat": 2, "refactor": 2, "docs": 2}, 1)
    lote = f3.armar_lote([], [dict(r) for r in b], 1, 0, 1)
    preds = f3.predecir(dataset, lote)
    assert {p["id"] for p in preds} == {r["f3_id"] for r in lote}
    assert all(p["entrenado_sin"] in ("o/uno", "o/dos") for p in preds)
