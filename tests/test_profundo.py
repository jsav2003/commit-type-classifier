"""F4: lo que se puede probar sin torch (el texto de entrada, la config, los pesos por
clase, el runner reanudable) y, con torch instalado, el entrenamiento de punta a punta con
una red diminuta. El modelo real (CodeBERT) no se descarga en las pruebas."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from ccls import experimento, profundo
from ccls.modelos import Mayoritaria
from ccls.stats import CLASES
from tests.test_experimento import CFG, _registros


def _reg(**kw) -> dict:
    base = {"message": "corrige el login", "diff": "", "files": ["src/a.ts", "README.md"], "n_files": 2,
            "lines_added": 10, "lines_deleted": 3, "n_binarios": 0, "extensiones": [".ts", ".md"],
            "toca_tests": False, "toca_docs": True}
    return {**base, **kw}


# --- config --------------------------------------------------------------------

def test_la_config_real_carga_y_fija_la_revision():
    cfg = profundo.cargar_config()
    assert len(cfg["revision"]) == 40 and set(cfg["revision"]) <= set("0123456789abcdef")
    assert cfg["pesos_por_clase"] == "balanceados"


def test_config_sin_una_clave_o_con_pesos_distintos_se_rechaza(tmp_path):
    real = yaml.safe_load(profundo.F4_CONFIG_PATH.read_text(encoding="utf-8"))
    sin = {k: v for k, v in real.items() if k != "epocas"}
    (tmp_path / "a.yaml").write_text(yaml.safe_dump(sin), encoding="utf-8")
    with pytest.raises(KeyError, match="epocas"):
        profundo.cargar_config(tmp_path / "a.yaml")
    (tmp_path / "b.yaml").write_text(yaml.safe_dump({**real, "pesos_por_clase": "ninguno"}), encoding="utf-8")
    with pytest.raises(ValueError, match="balanceados"):
        profundo.cargar_config(tmp_path / "b.yaml")


# --- el texto que ve el modelo ------------------------------------------------

def test_el_texto_del_diff_no_entra_jamas():
    """DESIGN.md §6.2 (2026-09-21): el diff no es entrada de la F4. Si `a_texto` lo leyera,
    lo que ponga aquí aparecería en la salida; y un registro SIN la clave tiene que
    funcionar igual, que es la prueba de que ni siquiera se consulta."""
    con = profundo.a_texto(_reg(diff="+ SECRETO_DEL_DIFF"), 25)
    assert "SECRETO_DEL_DIFF" not in " ".join(con)
    r = _reg()
    del r["diff"]
    assert profundo.a_texto(r, 25) == con


def test_mensaje_primero_y_metadatos_con_los_mismos_conteos_que_el_clasico():
    mensaje, meta = profundo.a_texto(_reg(toca_tests=True), 25)
    assert mensaje == "corrige el login"
    assert "files: 2, added: 10, deleted: 3, binary: 0, tests: yes, docs: yes" in meta
    assert meta.endswith("src/a.ts README.md")


def test_las_rutas_se_recortan_y_se_dice_cuantas_faltan():
    r = _reg(files=[f"f{i}.ts" for i in range(30)], n_files=30)
    _, meta = profundo.a_texto(r, 25)
    assert "f24.ts" in meta and "f25.ts" not in meta and meta.endswith("(+5 more)")


# --- pesos por clase -----------------------------------------------------------

def test_pesos_balanceados_igual_que_scikit_learn():
    import numpy
    from sklearn.utils.class_weight import compute_class_weight
    y = [0] * 60 + [1] * 25 + [2] * 5 + [3] * 10
    esperado = compute_class_weight("balanced", classes=numpy.array([0, 1, 2, 3]), y=numpy.array(y))
    assert profundo.pesos_balanceados(y, 4) == pytest.approx(list(esperado))


def test_una_clase_sin_ejemplos_pesa_cero_y_no_reparte_su_peso():
    import numpy
    from sklearn.utils.class_weight import compute_class_weight
    y = [0] * 6 + [1] * 3 + [3] * 1
    p = profundo.pesos_balanceados(y, 4)
    assert p[2] == 0.0
    esperado = compute_class_weight("balanced", classes=numpy.array([0, 1, 3]), y=numpy.array(y))
    assert [p[0], p[1], p[3]] == pytest.approx(list(esperado))


# --- importar no exige torch ---------------------------------------------------

def test_importar_los_modelos_no_importa_torch():
    codigo = "import sys, ccls.modelos, ccls.profundo, ccls.experimento; sys.exit('torch' in sys.modules)"
    assert subprocess.run([sys.executable, "-c", codigo]).returncode == 0


# --- runner reanudable ---------------------------------------------------------

class Contador(Mayoritaria):
    """Cuenta cuántas veces se entrena, para saber qué se saltó el caché."""
    entrenamientos = 0

    def fit(self, X, y):
        Contador.entrenamientos += 1
        return super().fit(X, y)


FAB = {"contador": lambda s: Contador()}
SEMILLAS = [1, 2]


def _correr(cache: Path | None, huella: str = "h1", particion: str = "repositorio"):
    return experimento.correr(_registros(), "contador", particion, SEMILLAS, CFG, fabricas=FAB,
                              cache_dir=cache, huella=huella)


def test_con_cache_el_resultado_es_identico_al_de_sin_cache(tmp_path):
    sin = _correr(None)
    con = _correr(tmp_path)
    assert con == sin
    assert _correr(tmp_path) == sin  # y reusar el caché tampoco lo cambia


def test_relanzar_no_reentrena_lo_que_ya_esta(tmp_path):
    Contador.entrenamientos = 0
    _correr(tmp_path)
    primera = Contador.entrenamientos
    assert primera == len(SEMILLAS) * 3  # 3 folds por repositorio
    _correr(tmp_path)
    assert Contador.entrenamientos == primera


def test_reanuda_donde_se_corto(tmp_path):
    """Una corrida cortada a mitad deja las semillas terminadas; al relanzar solo entrena
    las que faltan y el resultado final es el de una corrida completa."""
    completa = _correr(None)
    Contador.entrenamientos = 0
    experimento.correr(_registros(), "contador", "repositorio", SEMILLAS[:1], CFG, fabricas=FAB,
                       cache_dir=tmp_path, huella="h1")
    hechas = Contador.entrenamientos
    assert hechas == 3
    assert _correr(tmp_path) == completa
    assert Contador.entrenamientos == hechas + 3  # solo la semilla 2


def test_otra_huella_rehace_todo(tmp_path):
    Contador.entrenamientos = 0
    _correr(tmp_path, huella="config-vieja")
    n = Contador.entrenamientos
    _correr(tmp_path, huella="config-nueva")
    assert Contador.entrenamientos == 2 * n


def test_las_barajadas_y_las_de_verdad_no_comparten_cache(tmp_path):
    experimento.correr(_registros(), "contador", "aleatoria", [1], CFG, fabricas=FAB, cache_dir=tmp_path, huella="h")
    Contador.entrenamientos = 0
    experimento.correr(_registros(), "contador", "aleatoria", [1], CFG, fabricas=FAB, cache_dir=tmp_path, huella="h",
                       barajar_etiquetas=True)
    assert Contador.entrenamientos == 1


def test_un_fold_con_barra_en_el_nombre_no_rompe_el_cache(tmp_path):
    _correr(tmp_path)
    assert list(tmp_path.rglob("*org__r0*"))  # `org/r0` -> `org__r0`, sin subcarpetas
    assert not list(tmp_path.rglob("*.tmp"))


# --- de punta a punta con una red diminuta (necesita torch) --------------------

@pytest.fixture
def red_diminuta(tmp_path, monkeypatch):
    """Un RoBERTa de 2 capas y 16 unidades, con un tokenizador entrenado ahí mismo sobre el
    texto de las pruebas: ejercita fit/predict sin bajar nada de internet."""
    pytest.importorskip("torch")
    transformers = pytest.importorskip("transformers")
    from tokenizers import Tokenizer, models, pre_tokenizers, trainers
    from tokenizers.processors import RobertaProcessing

    textos = [f"{p} el módulo files added deleted binary tests docs yes no src a.ts R.md" for p in
              ("corrige", "agrega", "reorganiza", "documenta")] * 20
    tk = Tokenizer(models.WordLevel(unk_token="<unk>"))
    tk.pre_tokenizer = pre_tokenizers.Whitespace()
    tk.train_from_iterator(textos, trainers.WordLevelTrainer(special_tokens=["<pad>", "<s>", "</s>", "<unk>"], vocab_size=200))
    tk.post_processor = RobertaProcessing(("</s>", tk.token_to_id("</s>")), ("<s>", tk.token_to_id("<s>")))
    rapido = transformers.PreTrainedTokenizerFast(tokenizer_object=tk, unk_token="<unk>", pad_token="<pad>",
                                                  bos_token="<s>", eos_token="</s>", cls_token="<s>", sep_token="</s>")
    config = transformers.RobertaConfig(vocab_size=rapido.vocab_size, hidden_size=16, num_hidden_layers=2,
                                        num_attention_heads=2, intermediate_size=32, max_position_embeddings=64,
                                        pad_token_id=rapido.pad_token_id, num_labels=4)
    transformers.RobertaModel(config)  # valida la config
    monkeypatch.setattr(transformers.AutoTokenizer, "from_pretrained", lambda *a, **k: rapido)
    monkeypatch.setattr(transformers.AutoConfig, "from_pretrained", lambda *a, **k: config)
    monkeypatch.setattr(
        transformers.AutoModelForSequenceClassification, "from_pretrained",
        lambda *a, **k: transformers.RobertaForSequenceClassification(config))
    return config


def _cfg(**kw):
    # Una red de 16 unidades con embeddings congelados al azar aprende despacio: con 1 capa
    # entrenable y 30 pasos no sale de una sola clase. 2 capas y 40 épocas bastan.
    return {**profundo.cargar_config(), "max_longitud": 32, "epocas": 40, "tamano_lote": 16, "tasa_aprendizaje": 5e-3,
            "capas_entrenables": 2, **kw}


def _datos():
    palabra = {"fix": "corrige", "feat": "agrega", "refactor": "reorganiza", "docs": "documenta"}
    y = list(CLASES) * 20
    X = [_reg(message=f"{palabra[c]} el módulo", files=["src/a.ts"], extensiones=[".ts"], toca_docs=False) for c in y]
    return X, y


def test_solo_las_ultimas_capas_y_la_cabeza_se_reentrenan(red_diminuta):
    from transformers import RobertaForSequenceClassification
    m = RobertaForSequenceClassification(red_diminuta)
    profundo._congelar(m, 1)
    entrenables = {n for n, p in m.named_parameters() if p.requires_grad}
    assert entrenables and all(n.startswith(("roberta.encoder.layer.1.", "classifier.")) for n in entrenables)
    assert not any(p.requires_grad for p in m.roberta.embeddings.parameters())
    profundo._congelar(m, 0)  # 0 capas: solo la cabeza, no "todas"
    assert {n.split(".")[0] for n, p in m.named_parameters() if p.requires_grad} == {"classifier"}
    nuevo = RobertaForSequenceClassification(red_diminuta)
    profundo._congelar(nuevo, None)  # None: no congela nada, la red entera (F5)
    assert all(p.requires_grad for p in nuevo.parameters())


def test_fit_y_predict_aprenden_la_palabra_que_delata_la_clase(red_diminuta):
    X, y = _datos()
    pred = profundo.ClasificadorProfundo(1, _cfg()).fit(X, y).predict(X)
    assert len(pred) == len(X) and set(pred) <= set(CLASES)
    assert sum(p == c for p, c in zip(pred, y)) / len(y) > 0.9
    assert set(pred) == set(CLASES)  # y no colapsó a una sola clase


def test_misma_semilla_mismas_predicciones(red_diminuta):
    X, y = _datos()
    a = profundo.ClasificadorProfundo(3, _cfg(epocas=2)).fit(X, y).predict(X)
    b = profundo.ClasificadorProfundo(3, _cfg(epocas=2)).fit(X, y).predict(X)
    assert a == b


def test_predict_conserva_el_orden_de_entrada(red_diminuta):
    """predict ordena por largo para gastar menos relleno; la salida tiene que volver al
    orden original, o cada predicción quedaría pegada a otro commit."""
    X, y = _datos()
    m = profundo.ClasificadorProfundo(1, _cfg()).fit(X, y)
    completo = m.predict(X)
    invertido = m.predict(X[::-1])
    assert invertido == completo[::-1]


def test_el_modelo_desde_cero_se_entrena_entero(red_diminuta, monkeypatch):
    import transformers
    llamadas = []
    monkeypatch.setattr(transformers.AutoModelForSequenceClassification, "from_pretrained",
                        lambda *a, **k: llamadas.append("preentrenado"))
    monkeypatch.setattr(transformers.AutoModelForSequenceClassification, "from_config",
                        lambda c: transformers.RobertaForSequenceClassification(c))
    X, y = _datos()
    m = profundo.ClasificadorProfundo(1, _cfg(epocas=1), preentrenado=False).fit(X, y)
    assert llamadas == [] and all(p.requires_grad for p in m.modelo_.parameters())


# --- F5: la red desde cero (DESIGN.md §6.4) -------------------------------------

def test_la_config_de_la_f5_es_la_de_la_f4_salvo_las_capas():
    """config/f5.yaml promete que lo único que cambia son los pesos preentrenados (y, por
    eso, que se entrena la red entera). Si alguien retoca un hiperparámetro de uno solo de
    los dos archivos, la diferencia F4 − F5 dejaría de medir el preentrenamiento."""
    f4 = profundo.cargar_config(profundo.F4_CONFIG_PATH)
    f5 = profundo.cargar_config(profundo.F5_CONFIG_PATH)
    assert f5["capas_entrenables"] is None
    assert {k: v for k, v in f4.items() if k != "capas_entrenables"} == \
           {k: v for k, v in f5.items() if k != "capas_entrenables"}


def test_el_modelo_f5_no_carga_pesos_preentrenados():
    from ccls.modelos import MODELOS
    m = MODELOS["f5_desde_cero"](7)
    assert m.preentrenado is False and m.semilla == 7
    assert m.cfg == profundo.cargar_config(profundo.F5_CONFIG_PATH)
    assert MODELOS["f4_codebert"](7).preentrenado is True


def test_cada_modelo_profundo_tiene_su_config():
    from ccls.modelos import MODELOS
    assert set(profundo.CONFIG_POR_MODELO) == {"f4_codebert", "f5_desde_cero"} <= set(MODELOS)
