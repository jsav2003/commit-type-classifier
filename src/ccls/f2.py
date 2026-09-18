"""F2 · baselines. DESIGN.md §6.1, §6.2, §7.3 y §7.4.

Dos cosas: la lista de experimentos de la fase, declarada, y el renderizador de
`docs/F2_BASELINES.md`. La infraestructura que entrena y mide es la de la F1
(`experimento.py`): la F2 no la toca, solo la usa.

Reglas que el reporte tiene que respetar, fijadas antes de mirar ningún número:

- **F1 por clase desde el primer experimento** (DESIGN.md §7.4). La exactitud sola
  esconde que una clase colapsó.
- **`refactor` va fold por fold, con el n al lado, y no hay fila de promedio**
  (DESIGN.md §5). En la partición por repositorio hay folds con 1 solo ejemplo.
- **La regla de `docs` de §6.1 se reporta al lado de todo lo demás**: si esa regla sola
  acierta casi toda la clase, un F1 macro alto puede venir de ahí.
- Media e intervalo t al 95% entre semillas, nunca el mejor resultado (§7.3).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ccls import experimento
from ccls.stats import CLASES

F2_REPORTE_PATH = Path("docs/F2_BASELINES.md")

# `refactor` nunca se promedia entre folds (DESIGN.md §5): va en su propia sección.
CLASE_POR_FOLD = "refactor"
CLASES_EN_TABLA = tuple(c for c in CLASES if c != CLASE_POR_FOLD)


@dataclass(frozen=True)
class Exp:
    modelo: str
    que_es: str
    # entradas de más que este experimento necesita, fuera de experimento.ENTRADAS
    entradas_extra: tuple[str, ...] = ()
    # las ablaciones no entran a las tablas principales, van en su propia sección
    ablacion: bool = False

    @property
    def entradas(self) -> tuple[str, ...]:
        return experimento.ENTRADAS + self.entradas_extra


EXPERIMENTOS: tuple[Exp, ...] = (
    Exp("trivial",
        "Siempre la clase mayoritaria del entrenamiento. El piso de §6.1."),
    Exp("regla_docs",
        "El trivial más la regla de una línea de §6.1: si todos los archivos tocados "
        "son `.md`/`.rst`/`.txt`, `docs`."),
    Exp("clasico_lr",
        "§6.2: TF-IDF del mensaje (palabras y bigramas) más los rasgos hechos a mano, "
        "con regresión logística."),
    Exp("clasico_lr_balanceado",
        "El mismo, con `class_weight=\"balanced\"`. La reponderación que §4.4 manda "
        "considerar por lo escasa que es `refactor`."),
    Exp("clasico_gb",
        "Los mismos rasgos con gradient boosting; el TF-IDF entra reducido a 150 "
        "componentes con SVD, que es lo que los árboles pueden tragar."),
    Exp("clasico_lr_msg",
        "Ablación: solo el mensaje. La diferencia con `clasico_lr` es lo que aportan "
        "los rasgos hechos a mano.",
        ablacion=True),
    Exp("clasico_lr_issue",
        "Ablación: `clasico_lr` más `tiene_referencia_issue`, la bandera que quedó "
        "fuera de las entradas en la F1.",
        ("tiene_referencia_issue",), ablacion=True),
)

# El modelo cuyo montaje se audita: matrices de confusión y la prueba de §7.1. Es el
# §6.2 tal cual, sin reponderar; `clasico_lr_balanceado` comparte con él todo el
# armado de rasgos, así que auditar uno audita el camino del otro.
PRINCIPAL = "clasico_lr"
REPONDERADO = "clasico_lr_balanceado"
PARTICIONES = ("aleatoria", "repositorio", "temporal")


def por_nombre(nombre: str) -> Exp:
    return next(e for e in EXPERIMENTOS if e.modelo == nombre)


def cargar(modelo: str, particion: str, barajadas: bool = False,
           dir_: Path = experimento.RESULTADOS_DIR) -> dict | None:
    path = dir_ / experimento.nombre_resultado(modelo, particion, barajadas)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


# --------------------------------------------------------------------------- #
# render
# --------------------------------------------------------------------------- #

_pct = experimento._pct
_puntos = experimento._puntos


def _ic(iv: dict | None) -> str:
    """Como `experimento._ic`, pero un intervalo de ancho cero se imprime como un solo
    número. En las particiones por repositorio y temporal la división no depende de la
    semilla, así que un modelo determinista da cinco veces el mismo valor y escribir
    `65,8% [65,8%, 65,8%]` en cada celda solo estorba. El gradient boosting sí depende
    de la semilla y conserva su intervalo: por eso la decisión es celda por celda y no
    por partición."""
    if iv is not None and iv["ic_inf"] is not None and iv["ic_inf"] == iv["ic_sup"]:
        return _pct(iv["media"])
    return experimento._ic(iv)


def _resumen_de(doc: dict, fold: str) -> dict:
    return next(r for r in doc["resumen"] if r["fold"] == fold)


def _folds(doc: dict) -> list[str]:
    return [r["fold"] for r in doc["resumen"]]


def _tabla(resultados: list[tuple[str, dict]]) -> list[str]:
    cabecera = ["modelo", "exactitud", "F1 macro"] + [f"F1 `{c}`" for c in CLASES_EN_TABLA]
    filas = ["| " + " | ".join(cabecera) + " |", "|---" + "|---:" * (len(cabecera) - 1) + "|"]
    for nombre, r in resultados:
        celdas = [f"`{nombre}`", _ic(r["exactitud"]), _ic(r["f1_macro"])]
        celdas += [_ic(r["por_clase"][c]["f1"]) for c in CLASES_EN_TABLA]
        filas.append("| " + " | ".join(celdas) + " |")
    return filas


def _tablas_por_fold(docs: dict[str, dict], nivel: str = "###") -> list[str]:
    primero = next(iter(docs.values()))
    folds = _folds(primero)
    L: list[str] = []
    for fold in folds:
        if len(folds) > 1:
            n = _resumen_de(primero, fold)["n_prueba"]
            L.append(f"{nivel} Fold `{fold}` en prueba — n = {n}\n")
        L += _tabla([(m, _resumen_de(d, fold)) for m, d in docs.items()])
        L.append("")
    return L


def _seccion_particion(titulo: str, nota: str, docs: dict[str, dict]) -> list[str]:
    return [f"## {titulo}\n", nota + "\n"] + _tablas_por_fold(docs)


def _seccion_refactor(por_particion: dict[str, dict[str, dict]]) -> list[str]:
    L = [
        f"## `{CLASE_POR_FOLD}`, fold por fold\n",
        "DESIGN.md §5: `refactor` es el 8,2% del dataset, angular-cli aporta el 57% y "
        "svelte 1 solo ejemplo. Un F1 calculado sobre un puñado de casos no es una "
        "métrica, así que va con el n al lado y **no hay fila de promedio entre "
        "folds**.\n",
    ]
    for particion, docs in por_particion.items():
        primero = next(iter(docs.values()))
        L.append(f"### Partición {particion}\n")
        L.append("| fold | n `refactor` en prueba | " + " | ".join(f"`{m}`" for m in docs) + " |")
        L.append("|---|---:" + "|---:" * len(docs) + "|")
        for fold in _folds(primero):
            n = _resumen_de(primero, fold)["por_clase"][CLASE_POR_FOLD]["n_prueba"]
            celdas = [_ic(_resumen_de(d, fold)["por_clase"][CLASE_POR_FOLD]["f1"]) for d in docs.values()]
            L.append(f"| {fold} | {n} | " + " | ".join(celdas) + " |")
        L.append("")
    return L


def _seccion_inflado(aleatoria: dict[str, dict], repositorio: dict[str, dict]) -> list[str]:
    L = [
        "## Cuánto infla la partición aleatoria\n",
        "Es el punto 1 de DESIGN.md §11. La partición aleatoria reparte commits del "
        "mismo repositorio a los dos lados y el modelo memoriza el proyecto. La "
        "columna del medio es el **peor fold** de la partición por repositorio, no el "
        "promedio: es el que dice qué pasa en el proyecto más distinto de los que "
        "vio.\n",
        "| modelo | F1 macro, aleatoria | F1 macro, por repositorio (peor fold) | caída |",
        "|---|---:|---:|---:|",
    ]
    for m in aleatoria:
        al = _resumen_de(aleatoria[m], "aleatoria")["f1_macro"]["media"]
        peor, fold = min((_resumen_de(repositorio[m], f)["f1_macro"]["media"], f) for f in _folds(repositorio[m]))
        L.append(f"| `{m}` | {_pct(al)} | {_pct(peor)} ({fold}) | {_puntos(peor - al)} |")
    L.append("")
    return L


def _seccion_confusion(doc: dict, modelo: str) -> list[str]:
    """DESIGN.md §7.4: la matriz completa, no solo la exactitud. Se muestra la de la
    primera semilla de cada fold; en la partición por repositorio la división es fija y
    la regresión logística es determinista, así que la matriz no depende de la
    semilla."""
    L = [
        f"## Matrices de confusión — `{modelo}`, partición por repositorio\n",
        "Fila: etiqueta verdadera. Columna: predicción. Primera semilla de cada fold.\n",
    ]
    vistos: set[str] = set()
    for c in doc["corridas"]:
        if c["fold"] in vistos:
            continue
        vistos.add(c["fold"])
        L.append(f"**{c['fold']}**\n")
        L.append("| verdad \\ predicción | " + " | ".join(f"`{x}`" for x in CLASES) + " |")
        L.append("|---" + "|---:" * len(CLASES) + "|")
        for clase, fila in zip(CLASES, c["confusion"], strict=True):
            L.append(f"| `{clase}` | " + " | ".join(str(v) for v in fila) + " |")
        L.append("")
    return L


def _cuenta_reponderacion(resultados: dict[str, dict[str, dict]]) -> dict[str, tuple[int, int]]:
    """Cuántos folds mejora la reponderación y cuántos hay en total, por métrica.

    Se cuenta y no se escribe a mano: si los números cambian, la frase del reporte
    cambia con ellos en vez de quedarse mintiendo.
    """
    cuentas = {"refactor": [0, 0], "f1_macro": [0, 0], "exactitud": [0, 0]}
    for particion in PARTICIONES:
        sin, con = resultados[particion].get(PRINCIPAL), resultados[particion].get(REPONDERADO)
        if sin is None or con is None:
            continue
        for fold in _folds(sin):
            a, b = _resumen_de(sin, fold), _resumen_de(con, fold)
            pares = {
                "refactor": (a["por_clase"][CLASE_POR_FOLD]["f1"], b["por_clase"][CLASE_POR_FOLD]["f1"]),
                "f1_macro": (a["f1_macro"], b["f1_macro"]),
                "exactitud": (a["exactitud"], b["exactitud"]),
            }
            for metrica, (x, y) in pares.items():
                if x is None or y is None:
                    continue
                cuentas[metrica][1] += 1
                if y["media"] > x["media"]:
                    cuentas[metrica][0] += 1
    return {k: (v[0], v[1]) for k, v in cuentas.items()}


def _fold_mas_flaco(resultados: dict[str, dict[str, dict]]) -> tuple[str, int]:
    """El fold con menos ejemplos de `refactor` en prueba, con su n. Se nombra en vez de
    fijar un umbral: elegir ahora un mínimo, viendo ya los resultados, sería mover el
    criterio para acomodar el dato."""
    candidatos = [
        (_resumen_de(doc, fold)["por_clase"][CLASE_POR_FOLD]["n_prueba"], fold)
        for particion in PARTICIONES
        if (doc := resultados[particion].get(PRINCIPAL)) is not None
        for fold in _folds(doc)
    ]
    n, fold = min(candidatos)
    return fold, n


def _parrafo_reponderacion(resultados: dict[str, dict[str, dict]]) -> str:
    c = _cuenta_reponderacion(resultados)
    fold_flaco, n_flaco = _fold_mas_flaco(resultados)
    return (
        f"**El clásico de referencia es `{REPONDERADO}`.** DESIGN.md §4.4 manda "
        "considerar la reponderación por lo escasa que es `refactor` y decidirla con el "
        f"número delante. Está en las tablas: reponderar sube el F1 de `refactor` en "
        f"{c['refactor'][0]} de {c['refactor'][1]} folds y el F1 macro en "
        f"{c['f1_macro'][0]} de {c['f1_macro'][1]}, y baja la exactitud en "
        f"{c['exactitud'][1] - c['exactitud'][0]} de {c['exactitud'][1]}. Por §7.4 este "
        "proyecto mira el F1 por clase antes que la exactitud — un modelo que nunca "
        "predice `refactor` está roto aunque acierte mucho —, así que la reponderación "
        f"se adopta y `{PRINCIPAL}` se sigue reportando al lado, sin ella.\n\n"
        f"Esas cuentas incluyen el fold `{fold_flaco}`, que tiene {n_flaco} "
        "`refactor` en prueba. Ahí la diferencia no significa nada: §5 dice que un F1 "
        "sobre un puñado de casos no es una métrica, y por eso también entra a la "
        "cuenta en vez de desaparecer sin que se note.\n"
    )


def _seccion_fuga(resultados: dict[str, dict[str, dict]], barajadas: dict[str, dict], tolerancia: float) -> list[str]:
    """LEAKAGE.md §7.1 sobre el modelo principal de la F2, no sobre el de humo."""
    L = [
        f"## La prueba de etiquetas aleatorias, sobre `{PRINCIPAL}`\n",
        "`LEAKAGE.md` §7.1 se corrió en la F1 con el modelo de humo, que solo mira el "
        "mensaje. El clásico estrena rasgos —extensiones, la regla de §6.1, los verbos, "
        "los conteos del diff—, y cada rasgo nuevo es un camino nuevo por el que la "
        f"etiqueta podría colarse. Se repite la prueba sobre `{PRINCIPAL}`: con las "
        "etiquetas de entrenamiento barajadas, la exactitud no puede pasar la tasa de "
        f"la clase mayoritaria de prueba por más de {_puntos(tolerancia)} puntos.\n",
        "| partición | fold | techo del azar | exactitud, etiquetas barajadas | exceso | estado |",
        "|---|---|---:|---:|---:|---|",
    ]
    estados = []
    for particion, barajado in barajadas.items():
        for f in experimento.evaluar_fuga_aleatoria(barajado, resultados[particion][PRINCIPAL], tolerancia):
            estados.append(f["estado"])
            L.append(f"| {particion} | {f['fold']} | {_pct(f['techo_azar'])} | "
                     f"{_ic(f['exactitud_barajadas'])} | {_puntos(f['exceso'])} | {f['estado']} |")
    L.append("")
    L.append(f"{len(estados)} folds: {estados.count('pasa')} pasan, {estados.count('falla')} fallan, "
             f"{estados.count('no concluyente')} no concluyentes.\n")
    return L


def render(resultados: dict[str, dict[str, dict]], semillas: list[int], manifest_sha256: str,
           barajadas: dict[str, dict] | None = None, tolerancia: float = 0.02) -> str:
    """`resultados[particion][modelo]` es el JSON que dejó `experimento.guardar`.
    `barajadas[particion]` es el mismo JSON del modelo principal con las etiquetas de
    entrenamiento barajadas (LEAKAGE.md §7.1); si falta, esa sección no se escribe."""
    principales = [e.modelo for e in EXPERIMENTOS if not e.ablacion]
    ablaciones = [e.modelo for e in EXPERIMENTOS if e.ablacion]

    def sel(particion: str, modelos: list[str]) -> dict[str, dict]:
        return {m: resultados[particion][m] for m in modelos if m in resultados.get(particion, {})}

    L = [
        "# F2 · Baselines\n",
        "Generado por `python -m ccls f2 report`. **No se edita a mano.** El diseño de "
        "la fase está en `DESIGN.md` §6.1 y §6.2; cómo se leen los números, en §7.3 y "
        "§7.4.\n",
        f"- Semillas: {', '.join(map(str, semillas))}. Cada celda es la media entre semillas "
        "con su intervalo t al 95%, nunca el mejor resultado (§7.3).",
        "- En las particiones por repositorio y temporal la división no depende de la "
        "semilla y los modelos son deterministas: el intervalo tiene ancho cero y se omite.",
        "- Una celda `—` es una clase sin ejemplos en prueba: la F1 no existe, y no vale 0.",
        f"- Dataset: `manifest_sha256` `{manifest_sha256}`.\n",
        "## Qué modelo es cada uno\n",
        "| modelo | qué es |",
        "|---|---|",
    ]
    L += [f"| `{e.modelo}` | {e.que_es} |" for e in EXPERIMENTOS]
    L += [
        "",
        "## Cómo hay que leer esto\n",
        "**`docs` casi no requiere modelo.** La regla de una línea de §6.1 ya saca la "
        "F1 de `docs` que aparece en la fila `regla_docs`. Cualquier F1 macro alto de "
        "los demás modelos hay que mirarlo restando eso: una parte viene de una señal "
        "estructural, no de haber aprendido la tarea.\n",
        "**La partición por repositorio es la principal** (DESIGN.md §5). La aleatoria "
        "está para mostrar cuánto se infla el número, no para presumirlo.\n",
        _parrafo_reponderacion(resultados),
    ]

    L += _seccion_particion(
        "Partición aleatoria",
        "80/20 estratificada por clase, con una división distinta por semilla. **Fuga "
        "información**: commits del mismo repositorio quedan a los dos lados.",
        sel("aleatoria", principales))
    L += _seccion_particion(
        "Partición por repositorio — la principal",
        "Un fold por repo, con ese repo entero en prueba. Es la que responde si esto "
        "sirve en un proyecto que el modelo nunca vio.",
        sel("repositorio", principales))
    L += _seccion_particion(
        "Partición temporal",
        "Corte global el 2025-06-01: entrena con lo anterior y evalúa con lo "
        "posterior, 7.999 / 2.001.",
        sel("temporal", principales))

    L += _seccion_refactor({p: sel(p, principales) for p in PARTICIONES})
    L += _seccion_inflado(sel("aleatoria", principales), sel("repositorio", principales))

    L += ["## Ablaciones\n", "Qué aporta cada pieza, medido y no afirmado.\n"]
    for particion in ("repositorio", "temporal"):
        L.append(f"### Partición {particion}\n")
        L += _tablas_por_fold(sel(particion, [PRINCIPAL] + ablaciones), nivel="####")

    if barajadas:
        L += _seccion_fuga(resultados, barajadas, tolerancia)
    L += _seccion_confusion(resultados["repositorio"][PRINCIPAL], PRINCIPAL)
    return "\n".join(L)
