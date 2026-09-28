"""`RESULTS.md`: los cuatro enfoques en las tres particiones, en un solo documento.
DESIGN.md §10 y §7.7.

No calcula nada nuevo. Lee lo que dejaron `f1 run`, `f2 run`, `f4 run` y `f5 run` en
`resultados/` y lo junta, para que quien abra el repo vea la comparación completa sin
saltar entre `F2_BASELINES.md`, `F4_TRANSFER.md` y `F5_DESDE_CERO.md`. Las reglas de
lectura son las de esos reportes (media e intervalo entre semillas, `refactor` fold por
fold, la aleatoria no cuenta como resultado honesto) y las secciones vienen de los mismos
renderizadores, así que un cambio de formato allí se ve aquí.

Los enfoques (DESIGN.md §6):

1. Pisos: el trivial y la regla de `docs`.
2. Clásico: TF-IDF y rasgos con regresión logística, con y sin reponderar.
3. Transfer learning: CodeBERT con las últimas capas reentrenadas.
4. Red desde cero: la misma arquitectura con pesos al azar.
"""

from __future__ import annotations

from pathlib import Path

from ccls import experimento, f2, f4, f5

RESULTS_PATH = Path("RESULTS.md")

PARTICIONES = f2.PARTICIONES

# (modelo, enfoque, de dónde sale, comando que lo produce)
MODELOS: tuple[tuple[str, str, str, str], ...] = (
    ("trivial", "piso", "docs/F2_BASELINES.md", "f2 run"),
    ("regla_docs", "piso", "docs/F2_BASELINES.md", "f2 run"),
    ("clasico_lr", "clásico", "docs/F2_BASELINES.md", "f2 run"),
    (f2.REPONDERADO, "clásico, reponderado", "docs/F2_BASELINES.md", "f2 run"),
    (f4.MODELO, "transfer learning", "docs/F4_TRANSFER.md", "f4 run"),
    (f5.MODELO, "red desde cero", "docs/F5_DESDE_CERO.md", "f5 run"),
)
NOMBRES = tuple(m for m, *_ in MODELOS)

# Los modelos a los que se les corrió la prueba de etiquetas aleatorias (LEAKAGE.md §7.1)
# y el comando que la corre. El control de cada uno son sus propios resultados reales.
CON_FUGA: tuple[tuple[str, str], ...] = (
    ("clasico_lr", "f1 run --modelo clasico_lr --barajar"),
    (f4.MODELO, "f4 run --barajar"),
    (f5.MODELO, "f5 run --barajar"),
)

# Los que llevan matriz de confusión: los tres enfoques con modelo de verdad.
CON_MATRIZ = (f2.REPONDERADO, f4.MODELO, f5.MODELO)


def cargar_todo() -> tuple[dict[str, dict[str, dict]], dict[str, dict[str, dict]], list[str]]:
    """(resultados[particion][modelo], barajadas[modelo][particion], lo que falta)."""
    resultados: dict[str, dict[str, dict]] = {p: {} for p in PARTICIONES}
    faltan: list[str] = []
    for p in PARTICIONES:
        for modelo, _, _, comando in MODELOS:
            doc = f2.cargar(modelo, p)
            if doc is None:
                faltan.append(f"{modelo} · {p} ('{comando}')")
            else:
                resultados[p][modelo] = doc
    barajadas: dict[str, dict[str, dict]] = {}
    for modelo, _ in CON_FUGA:
        docs = {p: d for p in PARTICIONES if (d := f2.cargar(modelo, p, barajadas=True)) is not None}
        if docs:
            barajadas[modelo] = docs
    return resultados, barajadas, faltan


def _seccion_resumen(resultados: dict[str, dict[str, dict]]) -> list[str]:
    """F1 macro fold por fold, todos los enfoques en una tabla. El más alto de cada fila va
    en negrita solo como ayuda de lectura: con intervalos que se superponen, no es una
    victoria (el detalle con intervalos y el veredicto están en los reportes de cada fase)."""
    L = [
        "## La comparación en una tabla\n",
        "F1 macro, media entre semillas. **Negrita** = la media más alta de la fila. "
        "Que un número sea el más alto no lo hace el ganador: los intervalos de las tablas "
        "de abajo se superponen en varios folds, y en los reportes de cada fase está el "
        "veredicto fold por fold. La partición aleatoria está para mostrar cuánto se "
        "infla el número, no como resultado (DESIGN.md §5).\n",
        "| partición | fold | n | " + " | ".join(f"`{m}`" for m in NOMBRES) + " |",
        "|---|---|---:|" + "---:|" * len(NOMBRES),
    ]
    for particion in PARTICIONES:
        primero = resultados[particion][NOMBRES[0]]
        for fold in f2._folds(primero):
            medias = [f2._resumen_de(resultados[particion][m], fold)["f1_macro"]["media"] for m in NOMBRES]
            mejor = max(medias)
            celdas = [f"**{f2._pct(x)}**" if x == mejor else f2._pct(x) for x in medias]
            n = f2._resumen_de(primero, fold)["n_prueba"]
            L.append(f"| {particion} | {fold} | {n} | " + " | ".join(celdas) + " |")
    L.append("")
    return L


def _seccion_fuga(resultados: dict[str, dict[str, dict]], barajadas: dict[str, dict[str, dict]],
                  tolerancia: float) -> list[str]:
    L = [
        "## La prueba de etiquetas aleatorias, en los tres modelos\n",
        "`LEAKAGE.md` §7.1: con las etiquetas de entrenamiento barajadas, la exactitud no "
        f"puede pasar la tasa de la clase mayoritaria de prueba por más de {f2._puntos(tolerancia)} "
        "puntos. Cada modelo nuevo es un camino nuevo por el que la etiqueta podría "
        "colarse, así que se corre para cada uno. El detalle por fold está en "
        "`docs/F2_BASELINES.md`, `docs/F4_TRANSFER.md` y `docs/F5_DESDE_CERO.md`.\n",
        "| modelo | partición | folds | pasan | fallan | no concluyentes |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for modelo, _ in CON_FUGA:
        for particion in PARTICIONES:
            if particion not in barajadas.get(modelo, {}):
                L.append(f"| `{modelo}` | {particion} | — | — | — | sin correr |")
                continue
            filas = experimento.evaluar_fuga_aleatoria(
                barajadas[modelo][particion], resultados[particion][modelo], tolerancia)
            estados = [f["estado"] for f in filas]
            L.append(f"| `{modelo}` | {particion} | {len(filas)} | {estados.count('pasa')} | "
                     f"{estados.count('falla')} | {estados.count('no concluyente')} |")
    L.append("")
    return L


def _seccion_techo() -> list[str]:
    return [
        "## El techo humano\n",
        "DESIGN.md §11 pide poner el techo humano al lado de los números del modelo. **Hoy "
        "no hay techo humano:** la F3 está hecha de forma provisional con un anotador LLM "
        "(`docs/F3_TECHO_LLM.md`), y ese número no es comparable con el de una persona. "
        "Cuando alguien etiquete la muestra a mano (`python -m ccls f3 label`), el techo "
        "humano irá en `docs/F3_TECHO_HUMANO.md` y aquí se enlaza.\n",
    ]


def _seccion_reproducir() -> list[str]:
    return [
        "## Cómo se reproduce cada tabla\n",
        "`python -m ccls reproducir` corre el pipeline en orden y regenera todos los "
        "reportes; `--plan` solo lo muestra. Las tablas de este documento salen de "
        "`resultados/*.json` con `python -m ccls results`. Los comandos que produjeron cada "
        "modelo están en la tabla de arriba y en `docs/ESTADO.md`.\n",
    ]


def render(resultados: dict[str, dict[str, dict]], barajadas: dict[str, dict[str, dict]],
           semillas: list[int], manifest_sha256: str, tolerancia: float = 0.02) -> str:
    def sel(particion: str) -> dict[str, dict]:
        return {m: resultados[particion][m] for m in NOMBRES}

    L = [
        "# Resultados\n",
        "Generado por `python -m ccls results`. **No se edita a mano.** Junta los cuatro "
        "enfoques de DESIGN.md §6 en las tres particiones de §5; los números salen de "
        "`resultados/*.json` y las secciones de los mismos renderizadores que "
        "`docs/F2_BASELINES.md`, `docs/F4_TRANSFER.md` y `docs/F5_DESDE_CERO.md`.\n",
        f"- Semillas: {', '.join(map(str, semillas))}. Cada celda es la media entre semillas "
        "con su intervalo t al 95%, nunca el mejor resultado (§7.3).",
        "- En las particiones por repositorio y temporal la división no depende de la "
        "semilla y los modelos clásicos son deterministas: su intervalo tiene ancho cero y "
        "se omite.",
        "- Una celda `—` es una clase sin ejemplos en prueba: la F1 no existe, y no vale 0.",
        f"- Dataset: `manifest_sha256` `{manifest_sha256}`.\n",
        "## Qué enfoque es cada uno\n",
        "| modelo | enfoque | detalle | comando |",
        "|---|---|---|---|",
    ]
    L += [f"| `{m}` | {e} | `{doc}` | `{cmd}` |" for m, e, doc, cmd in MODELOS]
    L += [
        "",
        "Las ablaciones del clásico y el gradient boosting no están aquí: viven en "
        "`docs/F2_BASELINES.md`.\n",
    ]
    L += _seccion_resumen(resultados)
    L += f2._seccion_particion(
        "Partición aleatoria",
        "80/20 estratificada por clase, con una división distinta por semilla. **Fuga "
        "información**: commits del mismo repositorio quedan a los dos lados.",
        sel("aleatoria"))
    L += f2._seccion_particion(
        "Partición por repositorio — la principal",
        "Un fold por repo, con ese repo entero en prueba. Es la que responde si esto "
        "sirve en un proyecto que el modelo nunca vio.",
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
    for modelo in CON_MATRIZ:
        L += f2._seccion_confusion(resultados["repositorio"][modelo], modelo)
    L += _seccion_techo()
    L += _seccion_reproducir()
    return "\n".join(L)
