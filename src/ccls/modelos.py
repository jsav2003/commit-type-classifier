"""Modelos que la infraestructura de la F1 sabe entrenar.

Un modelo es una fábrica: recibe la semilla y devuelve un objeto con fit(X, y) y
predict(X). X es una lista de registros ya reducidos a experimento.ENTRADAS. Los
modelos del enfoque profundo viven en profundo.py y se registran aquí con import perezoso.

- trivial:      siempre la clase más frecuente del entrenamiento (DESIGN.md §6.1).
- regla_docs:   la regla de una línea de DESIGN.md §6.1 sobre el baseline trivial (F2).
- clasico_lr:   mensaje (TF-IDF) + los rasgos hechos a mano, regresión logística (§6.2).
- clasico_lr_balanceado: el mismo, con class_weight="balanced" (la reponderación de §4.4).
- clasico_lr_msg: solo el mensaje. La ablación que mide cuánto aportan los rasgos.
- clasico_gb:   los mismos rasgos, gradient boosting (§6.2).
- humo:         TF-IDF del mensaje + regresión logística, con los valores por defecto.
                Existe para la prueba de etiquetas aleatorias (LEAKAGE.md §7.1). Sus
                números NO son resultados de la F2.

El clásico ve solo lo que el runner le entrega (experimento.ENTRADAS): el mensaje ya
limpio del prefijo, el diff, los archivos y los metadatos de DESIGN.md §4.3.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from sklearn.decomposition import TruncatedSVD
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, make_pipeline
from sklearn.preprocessing import FunctionTransformer, MaxAbsScaler

from ccls.fuga_correlacion import solo_docs


class Mayoritaria:
    def fit(self, X: list[dict], y: list[str]) -> "Mayoritaria":
        conteo = Counter(y)
        self.clase_ = min(conteo, key=lambda c: (-conteo[c], c))  # empate: el nombre menor
        return self

    def predict(self, X: list[dict]) -> list[str]:
        return [self.clase_] * len(X)


class ReglaDocs(Mayoritaria):
    """DESIGN.md §6.1, el baseline por clase para `docs`: si todos los archivos tocados
    son .md/.rst/.txt, `docs`; si no, la clase mayoritaria del entrenamiento.

    La regla es `fuga_correlacion.solo_docs`, la misma que estratifica la prueba de
    correlación (LEAKAGE.md §7.3) y la que midió el piloto (B2.5): una sola definición.

    El respaldo es el baseline trivial, así que este modelo es "el trivial más la
    regla" y el F1 de `docs` que reporta es el de la regla sola — cierto mientras la
    clase mayoritaria no sea `docs`, que en este dataset es `fix` (55%).
    """

    def predict(self, X: list[dict]) -> list[str]:
        return ["docs" if solo_docs(r["files"]) else self.clase_ for r in X]


def _mensajes(X: list[dict]) -> list[str]:
    return [r["message"] for r in X]


def trivial(semilla: int) -> Mayoritaria:
    return Mayoritaria()


def regla_docs(semilla: int) -> ReglaDocs:
    return ReglaDocs()


def humo(semilla: int):
    # max_iter no es un ajuste: con el valor por defecto (100) lbfgs no converge.
    return make_pipeline(
        FunctionTransformer(_mensajes),
        TfidfVectorizer(),
        LogisticRegression(max_iter=1000, random_state=semilla),
    )

# --------------------------------------------------------------------------- #
# F2 · machine learning clásico (DESIGN.md §6.2)
# --------------------------------------------------------------------------- #

# §6.2 dice "aquí tú eliges qué mirar", y esta lista es esa elección. Se fijó a priori,
# con vocabulario general de mensajes de commit en inglés, y NO se escogió midiendo
# sobre el dataset: ajustarla después de ver el resultado sería elegir el rasgo con el
# número delante. El TF-IDF ya ve estas palabras; la bandera solo las hace explícitas.
VERBOS = (
    "fix", "add", "remove", "update", "rename", "move", "extract", "simplify",
    "clean", "refactor", "improve", "revert", "bump", "document", "support",
    "prevent", "avoid", "handle", "introduce", "drop", "split", "deprecate",
)
_VERBO_RE = {v: re.compile(rf"{v}(s|es|ed|ing|d)?", re.IGNORECASE) for v in VERBOS}


def rasgos(X: list[dict]) -> list[dict]:
    """Los rasgos hechos a mano de DESIGN.md §6.2, uno por commit.

    Dispersos a propósito: lo que vale 0 no se escribe, y DictVectorizer solo conoce
    las claves que vio en el entrenamiento. Una extensión que solo existe en el repo de
    prueba se ignora, que es lo correcto en la partición por repositorio.

    Del diff entran conteos, no texto. El texto del diff no se mira en la F2: la prueba
    de correlación de LEAKAGE.md §7.3 se midió sobre el mensaje, y meter el diff al
    modelo exige volver a correrla sobre sus tokens antes de creerle a los números.
    """
    out = []
    for r in X:
        agregadas, eliminadas = r["lines_added"], r["lines_deleted"]
        total = agregadas + eliminadas
        f = {
            # del diff: conteos y la proporción entre agregadas y eliminadas
            "log_agregadas": math.log1p(agregadas),
            "log_eliminadas": math.log1p(eliminadas),
            # 0,5 es el valor neutro para un commit sin líneas (solo binarios)
            "proporcion_agregadas": agregadas / total if total else 0.5,
            "log_archivos": math.log1p(r["n_files"]),
            # del mensaje: la longitud
            "log_largo_mensaje": math.log1p(len(r["message"])),
        }
        if r["n_binarios"]:
            f["log_binarios"] = math.log1p(r["n_binarios"])
        # de los archivos
        if r["toca_tests"]:
            f["toca_tests"] = 1.0
        if r["toca_docs"]:
            f["toca_docs"] = 1.0
        if solo_docs(r["files"]):
            # la regla de §6.1 como rasgo: el conjunto de extensiones no sabe decir
            # "todas son .md", solo "hay alguna .md"
            f["solo_docs"] = 1.0
        for ext in r["extensiones"]:
            f[f"ext={ext}"] = 1.0
        for verbo, patron in _VERBO_RE.items():
            if patron.search(r["message"]):
                f[f"verbo={verbo}"] = 1.0
        out.append(f)
    return out


def _a_denso(X):
    return X.toarray() if hasattr(X, "toarray") else X


class SVDAcotada(TruncatedSVD):
    """TruncatedSVD que baja n_components si el vocabulario es más chico. Con el dataset
    completo nunca actúa (el vocabulario son decenas de miles de columnas); existe para
    que el clásico se pueda correr sobre un subconjunto pequeño sin reventar."""

    def fit_transform(self, X, y=None):
        self.n_components = min(self.n_components, X.shape[1] - 1)
        return super().fit_transform(X, y)


def _tfidf():
    # min_df=2 quita los hapax (identificadores y SHA que solo salen una vez); no es un
    # ajuste buscado, es la defensa contra memorizar un commit concreto.
    return make_pipeline(
        FunctionTransformer(_mensajes),
        TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, strip_accents="unicode"),
    )


def rasgos_con_issue(X: list[dict]) -> list[dict]:
    """rasgos() más la bandera `tiene_referencia_issue`, que build.py calcula pero que
    NO está en experimento.ENTRADAS. Solo la usa clasico_lr_issue, y el runner tiene que
    pasarle esa entrada de más (ver f2.EXPERIMENTOS)."""
    marcados = rasgos(X)
    for f, r in zip(marcados, X, strict=True):
        if r["tiene_referencia_issue"]:
            f["tiene_referencia_issue"] = 1.0
    return marcados


def _rasgos_vectorizados(fn=rasgos):
    # MaxAbsScaler y no StandardScaler: centrar destruiría la dispersión.
    return make_pipeline(FunctionTransformer(fn), DictVectorizer(), MaxAbsScaler())


def _mensaje_y_rasgos(fn=rasgos) -> FeatureUnion:
    return FeatureUnion([("mensaje", _tfidf()), ("rasgos", _rasgos_vectorizados(fn))])


def _lr(semilla: int, class_weight=None) -> LogisticRegression:
    # max_iter no es un ajuste: con el valor por defecto lbfgs no converge.
    return LogisticRegression(max_iter=2000, random_state=semilla, class_weight=class_weight)


def clasico_lr(semilla: int):
    return make_pipeline(_mensaje_y_rasgos(), _lr(semilla))


def clasico_lr_balanceado(semilla: int):
    """La reponderación que DESIGN.md §4.4 manda considerar por lo escasa que es
    `refactor`. Se reporta al lado del no reponderado: la decisión va con el número
    delante, no antes."""
    return make_pipeline(_mensaje_y_rasgos(), _lr(semilla, class_weight="balanced"))


def clasico_lr_msg(semilla: int):
    """Ablación: solo el mensaje. La diferencia con clasico_lr es lo que aportan los
    rasgos hechos a mano."""
    return make_pipeline(_tfidf(), _lr(semilla))


def clasico_lr_issue(semilla: int):
    """Ablación de la decisión que quedó abierta en la F1: `tiene_referencia_issue` no
    entró a experimento.ENTRADAS, y la F2 decide con el número delante si entra."""
    return make_pipeline(_mensaje_y_rasgos(rasgos_con_issue), _lr(semilla))


def clasico_gb(semilla: int):
    """Gradient boosting sobre los mismos rasgos. Los árboles no tragan una matriz
    dispersa de cientos de miles de columnas, así que el TF-IDF entra reducido a 150
    componentes con SVD; los rasgos hechos a mano entran enteros."""
    return make_pipeline(
        FeatureUnion([
            ("mensaje", make_pipeline(_tfidf(), SVDAcotada(n_components=150, random_state=semilla))),
            ("rasgos", _rasgos_vectorizados()),
        ]),
        FunctionTransformer(_a_denso),
        HistGradientBoostingClassifier(random_state=semilla),
    )


# --------------------------------------------------------------------------- #
# F4 · transfer learning (DESIGN.md §6.3)
# --------------------------------------------------------------------------- #

def f4_codebert(semilla: int):
    """CodeBERT con las últimas capas reentrenadas (config/f4.yaml). El import es
    perezoso: importar `modelos` no debe exigir torch."""
    from ccls import profundo
    return profundo.ClasificadorProfundo(semilla, profundo.cargar_config())


MODELOS = {
    "trivial": trivial,
    "regla_docs": regla_docs,
    "clasico_lr": clasico_lr,
    "clasico_lr_balanceado": clasico_lr_balanceado,
    "clasico_lr_msg": clasico_lr_msg,
    "clasico_lr_issue": clasico_lr_issue,
    "clasico_gb": clasico_gb,
    "humo": humo,
    "f4_codebert": f4_codebert,
}
