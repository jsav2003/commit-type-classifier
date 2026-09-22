"""F4 · transfer learning. El reporte `docs/F4_TRANSFER.md`. DESIGN.md §6.3, §7.3 y §7.4.

El modelo y su entrenamiento viven en `profundo.py`; aquí solo se lee lo que dejó
`f4 run` en `resultados/` y se pone al lado del clásico de referencia de la F2.

Reglas del reporte, las mismas de la F2:

- **Contra `clasico_lr_balanceado`**, el clásico de referencia (DESIGN.md §4.4, decidido
  en la F2). Los dos reponderan por clase.
- **F1 por clase**, y `refactor` fold por fold con el n al lado, sin promedio (§5).
- Media e intervalo t al 95% entre semillas, nunca el mejor resultado (§7.3).
- La prueba de etiquetas aleatorias (LEAKAGE.md §7.1) sobre el modelo de esta fase: un
  modelo nuevo es un camino nuevo por el que la etiqueta podría colarse.

Cómo se decide "gana / empata / pierde" en cada fold está en `comparar`, y el reporte lo
dice con su limitación: el intervalo de CodeBERT es solo entre semillas.
"""

from __future__ import annotations

from pathlib import Path

from ccls import experimento, f2

F4_REPORTE_PATH = Path("docs/F4_TRANSFER.md")

MODELO = "f4_codebert"
REFERENCIA = f2.REPONDERADO
PARTICIONES = f2.PARTICIONES

_pct = experimento._pct
_puntos = experimento._puntos
_ic = f2._ic
_resumen_de = f2._resumen_de
_folds = f2._folds


def comparar(nuevo: dict, referencia: dict) -> str:
    """`nuevo` y `referencia` son intervalos de F1 macro de un mismo fold.

    - gana:   la media de la referencia queda por debajo del intervalo del modelo nuevo.
    - pierde: queda por encima.
    - empate: cae dentro.

    Se usa el intervalo del modelo nuevo porque en las particiones por repositorio y
    temporal el clásico es determinista y su intervalo tiene ancho cero. Ese intervalo
    solo mide la variación entre semillas, no la de la muestra de prueba: un "empate"
    quiere decir que la diferencia no supera el ruido del entrenamiento, no que los dos
    modelos sean iguales.
    """
    if nuevo["ic_inf"] is None:
        return "gana" if nuevo["media"] > referencia["media"] else "pierde" if nuevo["media"] < referencia["media"] else "empate"
    if referencia["media"] < nuevo["ic_inf"]:
        return "gana"
    if referencia["media"] > nuevo["ic_sup"]:
        return "pierde"
    return "empate"


def _seccion_veredicto(resultados: dict[str, dict[str, dict]]) -> list[str]:
    L = [
        f"## `{MODELO}` contra `{REFERENCIA}`, fold por fold\n",
        "F1 macro. El veredicto compara la media del clásico con el intervalo de "
        f"`{MODELO}` entre semillas (ver `comparar` en `src/ccls/f4.py`). Ese intervalo "
        "solo mide el ruido del entrenamiento, no el de la muestra de prueba, así que "
        "\"empate\" es \"la diferencia no pasa ese ruido\", no \"son iguales\".\n",
        f"| partición | fold | n | `{MODELO}` | `{REFERENCIA}` | diferencia | veredicto |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    cuenta: dict[str, int] = {}
    for particion in PARTICIONES:
        nuevo, ref = resultados[particion][MODELO], resultados[particion][REFERENCIA]
        for fold in _folds(nuevo):
            a, b = _resumen_de(nuevo, fold), _resumen_de(ref, fold)
            v = comparar(a["f1_macro"], b["f1_macro"])
            if particion != "aleatoria":
                cuenta[v] = cuenta.get(v, 0) + 1
            L.append(f"| {particion} | {fold} | {a['n_prueba']} | {_ic(a['f1_macro'])} | {_ic(b['f1_macro'])} | "
                     f"{_puntos(a['f1_macro']['media'] - b['f1_macro']['media'])} | {v} |")
    total = sum(cuenta.values())
    L.append("")
    L.append(f"**En los {total} folds honestos (por repositorio y temporal): "
             f"{cuenta.get('gana', 0)} gana, {cuenta.get('empate', 0)} empata, "
             f"{cuenta.get('pierde', 0)} pierde.** La aleatoria no cuenta: fuga información "
             "entre entrenamiento y prueba (DESIGN.md §5).\n")
    return L


def _seccion_por_clase(resultados: dict[str, dict[str, dict]]) -> list[str]:
    """Diferencia de F1 por clase, fold por fold. Es donde se ve qué compra el
    preentrenamiento: el macro puede quedar igual ganando en una clase y perdiendo en otra."""
    clases = f2.CLASES_EN_TABLA + (f2.CLASE_POR_FOLD,)
    L = [
        "## Qué clase gana y cuál pierde\n",
        f"Diferencia de F1, `{MODELO}` menos `{REFERENCIA}`, en puntos. `—`: la clase no "
        "tiene ejemplos en prueba. La columna de `refactor` lleva su n al lado (§5).\n",
        "| partición | fold | " + " | ".join(f"`{c}`" for c in clases) + " |",
        "|---|---" + "|---:" * len(clases) + "|",
    ]
    for particion in PARTICIONES:
        nuevo, ref = resultados[particion][MODELO], resultados[particion][REFERENCIA]
        for fold in _folds(nuevo):
            a, b = _resumen_de(nuevo, fold)["por_clase"], _resumen_de(ref, fold)["por_clase"]
            celdas = []
            for c in clases:
                if a[c]["f1"] is None or b[c]["f1"] is None:
                    celdas.append("—")
                    continue
                d = _puntos(a[c]["f1"]["media"] - b[c]["f1"]["media"])
                celdas.append(f"{d} (n = {a[c]['n_prueba']})" if c == f2.CLASE_POR_FOLD else d)
            L.append(f"| {particion} | {fold} | " + " | ".join(celdas) + " |")
    L.append("")
    return L


def _seccion_fuga(resultados: dict[str, dict[str, dict]], barajadas: dict[str, dict], tolerancia: float) -> list[str]:
    L = [
        f"## La prueba de etiquetas aleatorias, sobre `{MODELO}`\n",
        "`LEAKAGE.md` §7.1: con las etiquetas de entrenamiento barajadas, la exactitud no "
        f"puede pasar la tasa de la clase mayoritaria de prueba por más de {_puntos(tolerancia)} "
        "puntos. CodeBERT ve las rutas completas de los archivos, que el clásico no ve: es "
        "un camino nuevo por el que la etiqueta podría colarse.\n",
        "| partición | fold | techo del azar | exactitud, etiquetas barajadas | exceso | estado |",
        "|---|---|---:|---:|---:|---|",
    ]
    estados = []
    for particion in PARTICIONES:
        if particion not in barajadas:
            continue
        for f in experimento.evaluar_fuga_aleatoria(barajadas[particion], resultados[particion][MODELO], tolerancia):
            estados.append(f["estado"])
            L.append(f"| {particion} | {f['fold']} | {_pct(f['techo_azar'])} | "
                     f"{_ic(f['exactitud_barajadas'])} | {_puntos(f['exceso'])} | {f['estado']} |")
    faltan = [p for p in PARTICIONES if p not in barajadas]
    L.append("")
    L.append(f"{len(estados)} folds: {estados.count('pasa')} pasan, {estados.count('falla')} fallan, "
             f"{estados.count('no concluyente')} no concluyentes."
             + (f" **Falta correr:** {', '.join(faltan)}." if faltan else "") + "\n")
    L.append("Con etiquetas barajadas la exactitud varía mucho de una semilla a otra y el "
             "intervalo sale ancho; algunos intervalos llegan a tocar el techo. El criterio "
             "de §7.1 se fijó sobre la media, no sobre el extremo del intervalo, y no se "
             "cambia ahora.\n")
    return L


def _seccion_confusion(doc: dict) -> list[str]:
    L = [
        f"## Matrices de confusión — `{MODELO}`, partición por repositorio\n",
        "Fila: etiqueta verdadera. Columna: predicción. **Semilla 1 de cada fold**: a "
        "diferencia del clásico, aquí la semilla cambia el modelo y la matriz de otra "
        "semilla sería algo distinta.\n",
    ]
    return L + f2._seccion_confusion(doc, MODELO)[2:]


def _seccion_montaje(doc: dict) -> list[str]:
    h = doc["experimento"]["hiperparametros"]
    v = doc["versiones"]
    L = [
        "## Montaje\n",
        "Hiperparámetros de `config/f4.yaml`, fijados el 2026-09-21 **antes** de entrenar y "
        "sin retocar después: no hay conjunto de validación y ninguno se eligió mirando una "
        "partición de prueba. Sin afinar puede quedar por debajo de lo que CodeBERT da de "
        "verdad; afinarlo contra estos mismos folds sería elegir con el número delante.\n",
        "| parámetro | valor |",
        "|---|---|",
    ]
    L += [f"| `{k}` | `{val}` |" for k, val in h.items()]
    L += [
        "",
        "El texto del diff **no entra** (DESIGN.md §6.2): el modelo ve el mensaje, los "
        "conteos del diff y las rutas de los archivos, lo mismo que el clásico más las "
        "rutas completas.\n",
        "Versiones con que se corrió: " + ", ".join(f"{k} {val}" for k, val in v.items()) + ".\n",
        "En GPU los ajustes no son bit a bit reproducibles aunque se fije la semilla; para "
        "eso están las cinco semillas.\n",
    ]
    return L


def render(resultados: dict[str, dict[str, dict]], semillas: list[int], manifest_sha256: str,
           barajadas: dict[str, dict] | None = None, tolerancia: float = 0.02) -> str:
    """`resultados[particion][modelo]` tiene al menos `MODELO` y `REFERENCIA`.
    `barajadas[particion]` es `MODELO` con las etiquetas barajadas; si falta una
    partición, la sección de §7.1 lo dice en vez de callarlo."""
    def sel(particion: str) -> dict[str, dict]:
        return {m: resultados[particion][m] for m in (MODELO, REFERENCIA)}

    L = [
        "# F4 · Transfer learning\n",
        "Generado por `python -m ccls f4 report`. **No se edita a mano.** El diseño de la "
        "fase está en `DESIGN.md` §6.3; cómo se leen los números, en §7.3 y §7.4. Cómo se "
        "corrió, en `docs/COLAB_F4.md`.\n",
        f"- `{MODELO}`: CodeBERT (`microsoft/codebert-base`) con las últimas capas "
        "reentrenadas y la pérdida ponderada por clase.",
        f"- `{REFERENCIA}`: el clásico de referencia de la F2 (`docs/F2_BASELINES.md`), "
        "también reponderado. La comparación es reponderado contra reponderado.",
        f"- Semillas: {', '.join(map(str, semillas))}. Cada celda es la media entre semillas "
        "con su intervalo t al 95%; el clásico es determinista en las particiones por "
        "repositorio y temporal, y ahí su intervalo tiene ancho cero y se omite.",
        "- Una celda `—` es una clase sin ejemplos en prueba: la F1 no existe, y no vale 0.",
        f"- Dataset: `manifest_sha256` `{manifest_sha256}`.\n",
    ]
    L += _seccion_veredicto(resultados)
    L += _seccion_por_clase(resultados)
    L += f2._seccion_particion(
        "Partición aleatoria",
        "80/20 estratificada por clase, con una división distinta por semilla. **Fuga "
        "información**: commits del mismo repositorio quedan a los dos lados.",
        sel("aleatoria"))
    L += f2._seccion_particion(
        "Partición por repositorio — la principal",
        "Un fold por repo, con ese repo entero en prueba.",
        sel("repositorio"))
    L += f2._seccion_particion(
        "Partición temporal",
        "Corte global el 2025-06-01: entrena con lo anterior y evalúa con lo "
        "posterior, 7.999 / 2.001.",
        sel("temporal"))
    L += f2._seccion_refactor({p: sel(p) for p in PARTICIONES})
    L += f2._seccion_inflado(sel("aleatoria"), sel("repositorio"))
    if barajadas:
        L += _seccion_fuga(resultados, barajadas, tolerancia)
    L += _seccion_confusion(resultados["repositorio"][MODELO])
    L += _seccion_montaje(resultados["repositorio"][MODELO])
    return "\n".join(L)
