"""Prueba de fuga del prefijo — DESIGN.md §7.2, LEAKAGE.md.

Este test se escribe ANTES que el código de extracción (riesgo #1 de DESIGN.md §9:
"test automático desde el día uno, antes de entrenar nada"). Dos cosas se verifican:

1. Que el test SÍ falla sobre un fixture con fugas plantadas a propósito — un test
   de fuga que nunca ha fallado no prueba nada.
2. Que el dataset real (cuando exista) pasa limpio.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ccls.label import clasificar, contiene_fuga, diff_repite_mensaje_propio, limpiar_texto_completo

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = REPO_ROOT / "data" / "processed"


# ---------------------------------------------------------------------------
# 1. El test debe SABER fallar: fixtures con fuga plantada.
# ---------------------------------------------------------------------------

FUGAS_PLANTADAS = [
    "fix: corrige el login",
    "feat(auth): agrega login con Google",
    "refactor!: cambia la firma de la API pública",
    "DOCS: actualiza el README",
    "algo normal\n\nfix: esto se coló en el cuerpo",
    "[FIX] arregla el crash al iniciar",
    "bugfix: corrige el null pointer",
    "chore: bump de dependencias",  # variante fuera de las 4 clases, pero igual es fuga
    "chore(deps): actualiza dependencias",
    # Cuerpo de un squash-merge de GitHub: copia la lista de commits de la rama, con
    # viñeta. Medido antes de la F0: 29% de los cuerpos etiquetados de svelte.
    "agrega aviso al fallar play()\n\n* feat: agrega aviso\n\n* chore: formato",
    "- fix(parser): corrige el caso vacío",
    "+ docs: aclara el ejemplo",
    # Variantes en una línea intermedia, no al inicio del texto.
    "texto normal\n[FIX] variante en una línea intermedia",
    "texto normal\n  chore: variante en una línea intermedia",
]


@pytest.mark.parametrize("texto", FUGAS_PLANTADAS)
def test_contiene_fuga_detecta_prefijos_plantados(texto):
    assert contiene_fuga(texto), f"el detector de fuga no vio: {texto!r}"


TEXTOS_LIMPIOS = [
    "corrige el login",
    "agrega login con Google",
    "cambia la firma de la API pública",
    "actualiza el README",
    "algo normal\n\nesto no debería sonar a prefijo",
    "arregla el crash al iniciar",
    "* agrega aviso\n\n* formato",
    "- fixes the parser when the input is empty",
    "Note: esto no es un prefijo de convención",
    "see docs/fix.md for details",
]


@pytest.mark.parametrize("texto", TEXTOS_LIMPIOS)
def test_contiene_fuga_no_da_falsos_positivos(texto):
    assert not contiene_fuga(texto), f"falso positivo sobre: {texto!r}"


def test_clasificar_extrae_tipo_y_limpia_subject():
    et = clasificar("fix(auth): corrige el login")
    assert et.clase == "fix"
    assert et.tipo_declarado == "fix"
    assert et.scope == "(auth)"
    assert et.mensaje_limpio == "corrige el login"
    assert not contiene_fuga(et.mensaje_limpio)


def test_clasificar_tipos_fuera_de_las_4_clases_se_descartan():
    for tipo in ["chore", "test", "ci", "build", "style", "perf"]:
        et = clasificar(f"{tipo}: algo")
        assert et.clase is None, f"{tipo} no debería mapear a ninguna de las 4 clases"


def test_clasificar_sin_prefijo_devuelve_clase_none():
    et = clasificar("arregla el bug sin seguir convención")
    assert et.clase is None
    assert et.mensaje_limpio == "arregla el bug sin seguir convención"


def test_limpiar_texto_completo_borra_prefijo_en_cualquier_linea():
    sucio = "mensaje normal\nfix: esto no debería estar\notra línea normal"
    limpio = limpiar_texto_completo(sucio)
    assert not contiene_fuga(limpio)
    assert "esto no debería estar" in limpio  # se borra el prefijo, no la línea


def test_limpiar_texto_completo_borra_prefijo_en_lineas_con_vineta():
    sucio = "resumen\n\n* feat: agrega aviso\n\n* chore(deps): formato\n- fix(parser)!: caso vacío"
    limpio = limpiar_texto_completo(sucio)
    assert not contiene_fuga(limpio)
    # se borra el prefijo; la viñeta y el contenido se quedan
    assert limpio == "resumen\n\n* agrega aviso\n\n* formato\n- caso vacío"


# El diff tiene su propia versión de la prueba: el detector genérico dispara sobre
# código legítimo (`docs: false,`). Se busca el tipo Y el asunto del propio commit.
DIFF_CHANGESET = (
    "diff --git a/.changeset/wet-games-fly.md b/.changeset/wet-games-fly.md\n"
    "+---\n+'svelte': patch\n+---\n+\n+fix: adjust mount and createRoot types\n"
)


def test_diff_repite_mensaje_propio_detecta_changeset_plantado():
    assert diff_repite_mensaje_propio(DIFF_CHANGESET, "fix", "adjust mount and createRoot types (#10421)")


def test_diff_repite_mensaje_propio_detecta_con_scope_y_vineta():
    assert diff_repite_mensaje_propio("+- feat(kit): add the thing\n", "feat", "add the thing")


@pytest.mark.parametrize("diff", [
    "+      fix: 'Remove `experimental.headNext` from your `nuxt.config`',",
    "+      docs: false,",
    "+    refactor: TypeScriptFileRefactor) {",
    "+fix: adjust something else entirely",
])
def test_diff_repite_mensaje_propio_ignora_prefijos_de_codigo(diff):
    assert not diff_repite_mensaje_propio(diff, "fix", "adjust mount and createRoot types")


# ---------------------------------------------------------------------------
# 2. El dataset real, cuando exista, debe pasar limpio.
# ---------------------------------------------------------------------------

def _iter_dataset_jsonl():
    if not DATASET_DIR.exists():
        return
    for path in DATASET_DIR.glob("*.jsonl"):
        with path.open("r", encoding="utf-8") as f:
            for lineno, linea in enumerate(f, start=1):
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    yield path, lineno, json.loads(linea)
                except json.JSONDecodeError as e:
                    pytest.fail(f"{path}:{lineno} no es JSON válido: {e}")


@pytest.mark.skipif(
    not DATASET_DIR.exists() or not any(DATASET_DIR.glob("*.jsonl")),
    reason="no hay dataset en data/processed/ todavía (F0 sin correr)",
)
def test_dataset_real_no_contiene_prefijo():
    fallos = []
    for path, lineno, registro in _iter_dataset_jsonl():
        mensaje = registro["message"]
        if contiene_fuga(mensaje):
            fallos.append(f"{path}:{lineno} campo 'message' contiene el prefijo")
        tipo = registro["auditoria"]["tipo_declarado"]
        if diff_repite_mensaje_propio(registro["diff"], tipo, mensaje.split("\n")[0]):
            fallos.append(f"{path}:{lineno} campo 'diff' repite el mensaje del commit con su prefijo")
    assert not fallos, "fuga de prefijo encontrada:\n" + "\n".join(fallos[:20])
