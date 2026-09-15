"""Modelos que la infraestructura de la F1 sabe entrenar.

Un modelo es una fábrica: recibe la semilla y devuelve un objeto con fit(X, y) y
predict(X). X es una lista de registros ya reducidos a experimento.ENTRADAS. Los
modelos de verdad llegan en la F2 y la F4.

- trivial: siempre la clase más frecuente del entrenamiento (DESIGN.md §6.1).
- humo:    TF-IDF del mensaje + regresión logística, con los valores por defecto. Existe
           para la prueba de etiquetas aleatorias (LEAKAGE.md §7.1). Sus números NO son
           resultados de la F2.
"""

from __future__ import annotations

from collections import Counter

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer


class Mayoritaria:
    def fit(self, X: list[dict], y: list[str]) -> "Mayoritaria":
        conteo = Counter(y)
        self.clase_ = min(conteo, key=lambda c: (-conteo[c], c))  # empate: el nombre menor
        return self

    def predict(self, X: list[dict]) -> list[str]:
        return [self.clase_] * len(X)


def _mensajes(X: list[dict]) -> list[str]:
    return [r["message"] for r in X]


def trivial(semilla: int) -> Mayoritaria:
    return Mayoritaria()


def humo(semilla: int):
    # max_iter no es un ajuste: con el valor por defecto (100) lbfgs no converge.
    return make_pipeline(
        FunctionTransformer(_mensajes),
        TfidfVectorizer(),
        LogisticRegression(max_iter=1000, random_state=semilla),
    )


MODELOS = {"trivial": trivial, "humo": humo}
