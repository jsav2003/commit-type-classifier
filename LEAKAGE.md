# Fugas de datos (leakage)

Este documento registra las dos pruebas de fuga que exige `DESIGN.md` §7 y sus
resultados. Mientras no haya código de entrenamiento, queda como esqueleto con las
decisiones de diseño ya tomadas.

## 7.2 · Fuga del prefijo de convención

**Qué se prueba:** que ninguna entrada del dataset (`message`, `diff`) contiene el
prefijo de Conventional Commits usado para etiquetar, ni ninguna de sus variantes.

**Dónde:** `tests/test_prefix_leakage.py`. Corre sobre:

1. Un fixture sintético con fugas plantadas a propósito — debe **fallar**. Si nunca
   falla, el test no prueba nada.
2. El dataset real en `data/processed/` — debe **pasar**.

**Patrones cubiertos:** `fix:` `feat:` `refactor:` `docs:`, con y sin scope
(`fix(auth):`), con `!` de breaking change, en cualquier capitalización, al inicio de
cualquier línea del cuerpo (no solo la primera), y variantes fuera de la convención
estricta: `[FIX]`, `[BUGFIX]`, `bugfix:`, `FEATURE:`, `chore:`.

**Estado:** _pendiente de primera corrida — se llena cuando exista `data/processed/`._

### Decisión abierta: referencias a issues (`Fixes #123`, `Closes #456`)

Es señal legítima del dominio (el autor está diciendo qué arregla el commit) y a la
vez una fuga casi perfecta si el issue tiene un tipo asociado. Posición por defecto:
**se conserva el texto**, pero `build.py` guarda una bandera booleana
`tiene_referencia_issue` en los metadatos, para poder medir en la F2 cuánto aporta esa
señal por sí sola y decidir con el número delante, no a priori.

## 7.1 · Fuga por etiquetas aleatorias

**Qué se prueba:** entrenar todo el montaje (features, modelo, evaluación) con las
etiquetas barajadas al azar. El resultado debe ser el del azar (≈ 1/4 si las clases
están balanceadas, o la tasa de la clase mayoritaria si no). Si da más, hay fuga en
alguna otra parte del pipeline y ningún número posterior es de fiar.

**Cuándo corre:** antes que cualquier experimento real, y se reporta en el `README.md`
del repo, no solo aquí.

**Estado:** _pendiente — depende de la infraestructura de experimentos (F1)._

## Sesgo de selección (no es leakage, pero se registra aquí por relación directa)

El filtro de admisión de repos por tasa de Conventional Commits (`DESIGN.md` §4.1)
introduce un sesgo de selección: el dataset de entrenamiento está hecho enteramente de
proyectos que ya siguen la convención. Por eso los 300 commits del techo humano (F3)
se toman de repos **sin** convención — ver `DESIGN.md` §4.1 y §4.2. No es una fuga
porque no contamina entrenamiento con test, pero si se ignorara al reportar
resultados, daría una imagen más optimista de lo que el clasificador puede hacer en
uso real.
