"""Etiquetado por Conventional Commits y borrado del prefijo.

Este módulo es la fuente única de verdad sobre "qué es el prefijo de convención".
`tests/test_prefix_leakage.py` importa `LEAK_PATTERNS` de aquí — así el detector de
fugas nunca puede quedar desincronizado del propio etiquetador (si el etiquetador
aprende un patrón nuevo, el test de fuga lo hereda automáticamente).

Ver DESIGN.md §4.2 y LEAKAGE.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Las cuatro clases que el proyecto clasifica (DESIGN.md §1). Todo tipo de
# Conventional Commits que no esté aquí (chore, test, ci, build, style, perf, ...)
# se descarta en vez de reasignarse a una de estas cuatro — ver DESIGN.md §... C3.
TIPO_A_CLASE = {
    "fix": "fix",
    "feat": "feat",
    "refactor": "refactor",
    "docs": "docs",
}

# Prefijo estricto de Conventional Commits: tipo(scope)!: resto
# Ejemplos que matchea: "fix:", "fix(auth):", "fix(auth)!:", "FIX:"
_CC_PREFIX = re.compile(
    r"^(?P<tipo>[A-Za-z]+)(?P<scope>\([^)]*\))?(?P<breaking>!)?:\s*",
)

# Inicio de línea con viñeta opcional. Los squash-merge de GitHub copian al cuerpo
# la lista de commits de la rama ("* feat: ...", "- fix(x): ..."): antes de la F0 se
# midió en el 29% de los cuerpos etiquetados de svelte (LEAKAGE.md).
_VINETA = r"(?P<v>[ \t]*(?:[-*+•][ \t]*)?)"

# El mismo prefijo, en cualquier línea y detrás de una viñeta. Para limpiar.
_CC_PREFIX_LINEA = re.compile(
    rf"^{_VINETA}(?P<tipo>[A-Za-z]+)(\([^)]*\))?!?:[ \t]*",
)

# Variantes fuera de la convención estricta, pero que declaran el mismo tipo de
# cambio y por tanto son fuga si sobreviven en el texto de entrada. Se buscan en
# CUALQUIER línea, no solo la primera (DESIGN.md / LEAKAGE.md §7.2). MULTILINE: sin
# él, `^` solo ancla al inicio del texto y una variante en la segunda línea pasaba.
_VARIANT_PATTERNS = [
    re.compile(rf"^{_VINETA}\[(fix|bugfix|feat|feature|refactor|docs)\]", re.IGNORECASE | re.MULTILINE),
    re.compile(rf"^{_VINETA}(bugfix|feature)\s*:[ \t]*", re.IGNORECASE | re.MULTILINE),
    # descartado, pero igual es fuga si queda
    re.compile(rf"^{_VINETA}chore(\([^)]*\))?!?\s*:[ \t]*", re.IGNORECASE | re.MULTILINE),
]

# Patrones completos usados por el test de fuga: el prefijo estricto en cualquier
# línea del texto (no solo al inicio del string completo) + las variantes.
LEAK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        rf"^{_VINETA}(fix|feat|refactor|docs)(\([^)]*\))?!?:",
        re.IGNORECASE | re.MULTILINE,
    ),
] + _VARIANT_PATTERNS


@dataclass
class Etiqueta:
    clase: str | None  # None => se descarta (tipo fuera de las 4 clases, o sin prefijo)
    tipo_declarado: str | None  # el tipo crudo tal como aparecía, para auditoría
    scope: str | None
    breaking: bool
    mensaje_limpio: str  # subject sin el prefijo


def clasificar(subject: str, body: str = "") -> Etiqueta:
    """Extrae la etiqueta de un subject de Conventional Commits y devuelve el
    mensaje con el prefijo eliminado. No toca el body salvo para el borrado de
    prefijo defensivo (ver `limpiar_texto_completo`).
    """
    m = _CC_PREFIX.match(subject)
    if not m:
        return Etiqueta(None, None, None, False, subject.strip())

    tipo_crudo = m.group("tipo")
    tipo = tipo_crudo.lower()
    scope = m.group("scope")
    breaking = m.group("breaking") is not None
    resto = subject[m.end():].strip()

    clase = TIPO_A_CLASE.get(tipo)
    return Etiqueta(clase, tipo_crudo, scope, breaking, resto)


def limpiar_texto_completo(texto: str) -> str:
    """Borra el prefijo de convención (y sus variantes) de CUALQUIER línea del
    texto, no solo de la primera, también detrás de una viñeta. Se aplica al
    subject ya limpiado por `clasificar` y, por separado, al body completo, porque
    el body puede repetir o citar el prefijo (p. ej. la lista de commits de un
    squash-merge). Borra el prefijo; la viñeta y el resto de la línea se quedan.
    """
    lineas = texto.split("\n")
    limpias = []
    for linea in lineas:
        nueva = linea
        m = _CC_PREFIX_LINEA.match(nueva)
        if m and m.group("tipo").lower() in TIPO_A_CLASE:
            nueva = m.group("v") + nueva[m.end():]
        for pat in _VARIANT_PATTERNS:
            nueva = pat.sub(lambda mm: mm.group("v"), nueva)
        limpias.append(nueva)
    return "\n".join(limpias).strip()


_SUFIJO_PR = re.compile(r"\s*\(#\d+\)\s*$")


def diff_repite_mensaje_propio(diff: str, tipo: str | None, asunto: str, largo: int = 25) -> bool:
    """True si alguna línea del diff es `tipo(scope)!: <inicio del asunto>`, con el
    tipo y el asunto de ESTE commit (p. ej. un .changeset que copia el título del PR).

    Es la prueba del prefijo aplicada al diff. No se usa `contiene_fuga` porque en
    código hay prefijos legítimos que no tienen nada que ver con la etiqueta
    (`docs: false,` en TS, `refactor: TypeScriptFileRefactor`). La fuga por
    correlación, sin la línea escrita, la cubre ccls.fuga_correlacion.
    """
    inicio = _SUFIJO_PR.sub("", asunto).strip().lower()[:largo]
    if not tipo or not inicio:
        return False
    pat = re.compile(
        rf"^[+\- ]?{_VINETA}{re.escape(tipo)}(\([^)]*\))?!?:[ \t]*(?P<resto>.*)$",
        re.IGNORECASE | re.MULTILINE,
    )
    return any(m.group("resto").strip().lower().startswith(inicio) for m in pat.finditer(diff))


def contiene_fuga(texto: str) -> bool:
    """True si `texto` todavía contiene el prefijo de convención en alguna línea.
    Usado por tests/test_prefix_leakage.py contra el dataset real.
    """
    return any(pat.search(texto) for pat in LEAK_PATTERNS)
