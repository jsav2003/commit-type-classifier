"""Prueba de fuga por correlación — LEAKAGE.md §7.3.

La prueba del prefijo (§7.2) busca la etiqueta escrita. Esta busca la etiqueta
filtrada por correlación: un token que no dice "fix" pero que, cuando aparece, casi
siempre es fix. El caso real que la motivó: los .changeset de svelte traían "patch"
o "minor", y "patch" iba con fix en 1.309 de 1.315 commits, aunque la línea `fix:`
no apareciera.

Para cada token candidato t, cada clase c, cada estrato y cada ámbito (el dataset
entero y cada repo por separado):

    P(t)       frecuencia base del token
    P(t|c)     frecuencia del token dentro de la clase
    ganancia   (cota inferior de Wilson de P(c|t) − P(c)) / (1 − P(c))

La prueba falla si ganancia >= UMBRAL_GANANCIA en un token presente en al menos
MIN_SOPORTE registros del ámbito.

Por qué no se usa directamente el cociente P(t|c) / P(t): es igual a P(c|t) / P(c),
así que está acotado por 1 / P(c). Con fix en el 55% del dataset, ni una fuga
perfecta pasa de 1,8, y un umbral lo bastante bajo para atraparla dispararía por
ruido en las clases chicas. La ganancia normaliza eso: 0 = el token no dice nada de
la clase, 1 = siempre que aparece es esa clase. La cota inferior de Wilson (95%)
evita que un token visto en pocos registros dispare por azar.

Estratos (decisión del 2026-09-15, LEAKAGE.md §7.3). Todo se mide por separado dentro
de "solo docs" y "no solo docs", la regla estructural de DESIGN.md §6.1, que ya es
señal legítima y declarada. Un token solo cuenta como fuga si dice algo MÁS que esa
regla. Costo, declarado: dentro de "solo docs" la base de docs es ~99%, así que una
fuga hacia docs en commits que ya solo tocan .md no se puede ver. Hacia las otras
clases sí.

Los candidatos se eligen a mano: tokens sospechosos de describir el tipo del cambio.
No se prueba cualquier token, porque hay señal legítima de la tarea que también
predice clases (".md" predice docs, DESIGN.md §6.1).
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

CLASES = ("fix", "feat", "refactor", "docs")
UMBRAL_GANANCIA = 0.5
MIN_SOPORTE = 20
_Z = 1.96
DOCS_EXTS = {".md", ".rst", ".txt"}
SOLO_DOCS = "solo docs"
NO_SOLO_DOCS = "no solo docs"
SIN_ESTRATOS = "sin estratos"


def solo_docs(files: list[str]) -> bool:
    """La regla de una línea de DESIGN.md §6.1, la misma que midió el piloto (B2.5)."""
    return bool(files) and all(Path(p).suffix.lower() in DOCS_EXTS for p in files)


@dataclass(frozen=True)
class Token:
    nombre: str
    patron: re.Pattern[str]
    campo: str  # "message", "diff", "diff_changelog", "files" o "todo"


def _token(nombre: str, regex: str, campo: str = "diff", flags: int = re.MULTILINE) -> Token:
    return Token(nombre, re.compile(regex, flags), campo)


# Frontmatter de un changeset, dentro del diff: "+'svelte': patch"
_BUMP = r"^[+\- ][ \t]*['\"]?[@\w./-]+['\"]?[ \t]*:[ \t]*{}[ \t]*$"
_CHANGELOG = r"(^|/)changelog(\.md)?$"
_CHANGELOG_RE = re.compile(_CHANGELOG, re.IGNORECASE)
_CABECERA_DIFF = re.compile(r"^diff --git a/(?P<a>.*) b/(?P<b>.*)$")

TOKENS_CANDIDATOS: list[Token] = [
    _token("changeset: ruta", r"(^|/)\.changeset/", campo="files"),
    _token("changeset: bump patch", _BUMP.format("patch")),
    _token("changeset: bump minor", _BUMP.format("minor")),
    _token("changeset: bump major", _BUMP.format("major")),
    _token("palabra patch", r"\bpatch\b", campo="todo", flags=re.IGNORECASE),
    _token("palabra minor", r"\bminor\b", campo="todo", flags=re.IGNORECASE),
    _token("palabra major", r"\bmajor\b", campo="todo", flags=re.IGNORECASE),
    _token("changelog: ruta", _CHANGELOG, campo="files", flags=re.IGNORECASE | re.MULTILINE),
    _token("changelog: encabezado de versión", r"^\+#{1,3} \[?v?\d+\.\d+\.\d+"),
    _token(
        "changelog: encabezado de tipo",
        r"^\+#{2,4}[ \t]*(bug fixes|features|performance improvements|breaking changes|code refactoring|reverts)[ \t]*$",
        flags=re.IGNORECASE | re.MULTILINE,
    ),
    # Solo dentro de archivos CHANGELOG: en cualquier parte del diff atrapaba la
    # documentación de opciones ("- **Type:** `boolean`" en docs/config/*.md), que
    # acompaña a los feat de vitest y vite y es señal de la tarea (LEAKAGE.md §7.3).
    _token("changelog: entrada con scope", r"^\+[ \t]*[*-] \*\*[^*\n]+:\*\*", campo="diff_changelog"),
    # Efecto secundario de config/repos.yaml -> rutas_excluidas: un commit que solo
    # tocaba .changeset/ queda con el diff vacío, y eso también podría delatar la clase.
    _token("diff vacío", r"\A\s*\Z", flags=0),
]


def bloques_changelog(diff: str) -> str:
    """Las partes del diff que pertenecen a archivos CHANGELOG, cabecera incluida."""
    out = []
    dentro = False
    for linea in diff.split("\n"):
        m = _CABECERA_DIFF.match(linea)
        if m:
            dentro = bool(_CHANGELOG_RE.search(m.group("a")) or _CHANGELOG_RE.search(m.group("b")))
        if dentro:
            out.append(linea)
    return "\n".join(out)


def _texto(r: dict, campo: str) -> str:
    if campo == "files":
        return "\n".join(r["files"])
    if campo == "todo":
        return "\n".join([r["message"], r["diff"], *r["files"]])
    if campo == "diff_changelog":
        return bloques_changelog(r["diff"])
    return r[campo]


def _wilson_inferior(k: int, n: int) -> float:
    if n == 0:
        return 0.0
    p = k / n
    centro = p + _Z**2 / (2 * n)
    margen = _Z * math.sqrt(p * (1 - p) / n + _Z**2 / (4 * n * n))
    return (centro - margen) / (1 + _Z**2 / n)


@dataclass
class Medicion:
    token: str
    ambito: str
    estrato: str
    clase: str
    n: int  # registros en el ámbito y estrato
    n_clase: int
    n_token: int  # registros del ámbito y estrato con el token
    n_token_clase: int  # registros de la clase con el token

    @property
    def p_token(self) -> float:
        return self.n_token / self.n if self.n else 0.0

    @property
    def p_token_en_clase(self) -> float:
        return self.n_token_clase / self.n_clase if self.n_clase else 0.0

    @property
    def p_clase(self) -> float:
        return self.n_clase / self.n if self.n else 0.0

    @property
    def p_clase_dado_token(self) -> float:
        return self.n_token_clase / self.n_token if self.n_token else 0.0

    @property
    def ganancia(self) -> float:
        if not self.n_token or self.p_clase >= 1:
            return 0.0
        return (_wilson_inferior(self.n_token_clase, self.n_token) - self.p_clase) / (1 - self.p_clase)

    def sospechosa(self, umbral: float = UMBRAL_GANANCIA, min_soporte: int = MIN_SOPORTE) -> bool:
        return self.n_token >= min_soporte and self.ganancia >= umbral


def medir(
    registros: list[dict],
    tokens: list[Token] = TOKENS_CANDIDATOS,
    por_repo: bool = True,
    estratificar: bool = True,
) -> list[Medicion]:
    ambitos: dict[str, list[int]] = {"todos": list(range(len(registros)))}
    if por_repo:
        grupos: dict[str, list[int]] = defaultdict(list)
        for i, r in enumerate(registros):
            grupos[r["repo"]].append(i)
        ambitos.update(sorted(grupos.items()))

    if estratificar:
        es_solo_docs = [solo_docs(r["files"]) for r in registros]
        estratos = {SOLO_DOCS: lambda i: es_solo_docs[i], NO_SOLO_DOCS: lambda i: not es_solo_docs[i]}
    else:
        estratos = {SIN_ESTRATOS: lambda i: True}

    presencia = {tok.nombre: [bool(tok.patron.search(_texto(r, tok.campo))) for r in registros] for tok in tokens}

    mediciones = []
    for ambito, todos_idxs in ambitos.items():
        for estrato, pertenece in estratos.items():
            idxs = [i for i in todos_idxs if pertenece(i)]
            por_clase = Counter(registros[i]["label"] for i in idxs)
            for tok in tokens:
                con_token = [i for i in idxs if presencia[tok.nombre][i]]
                cnt = Counter(registros[i]["label"] for i in con_token)
                for c in CLASES:
                    mediciones.append(
                        Medicion(tok.nombre, ambito, estrato, c, len(idxs), por_clase.get(c, 0), len(con_token), cnt.get(c, 0))
                    )
    return mediciones


def sospechosas(mediciones: list[Medicion], umbral: float = UMBRAL_GANANCIA, min_soporte: int = MIN_SOPORTE) -> list[Medicion]:
    return [m for m in mediciones if m.sospechosa(umbral, min_soporte)]


def tabla_md(mediciones: list[Medicion]) -> list[str]:
    """Una fila por (token, ámbito, estrato): la clase con más ganancia. Filas de un
    repo solo si el token aparece en ese repo y estrato."""
    mejor: dict[tuple[str, str, str], Medicion] = {}
    for m in mediciones:
        clave = (m.token, m.ambito, m.estrato)
        if clave not in mejor or m.ganancia > mejor[clave].ganancia:
            mejor[clave] = m
    filas = [
        "| token | ámbito | estrato | con token | P(t) | clase | P(t\\|c) | P(c) | P(c\\|t) | ganancia | falla |",
        "|---|---|---|---:|---:|---|---:|---:|---:|---:|---|",
    ]
    for (token, ambito, estrato), m in mejor.items():
        if ambito != "todos" and m.n_token == 0:
            continue
        filas.append(
            f"| {token} | {ambito} | {estrato} | {m.n_token} | {m.p_token:.1%} | {m.clase} | {m.p_token_en_clase:.1%} | "
            f"{m.p_clase:.1%} | {m.p_clase_dado_token:.1%} | {m.ganancia:.2f} | {'**SÍ**' if m.sospechosa() else 'no'} |"
        )
    return filas
