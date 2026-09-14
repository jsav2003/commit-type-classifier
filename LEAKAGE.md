# Fugas de datos (leakage)

Este documento registra las pruebas de fuga que exige `DESIGN.md` §7 y sus resultados.

**Estado al 2026-09-14, con el dataset de la F0 construido:**

| prueba | estado |
|---|---|
| §7.2 · prefijo de convención | ✅ pasa: 0 registros en `message`, 0 en `diff` |
| §7.3 · correlación por clase | ❌ **falla en 4 mediciones de CHANGELOG (angular-cli)**, decisión pendiente; ver abajo |
| §7.1 · etiquetas aleatorias | pendiente: depende de la infraestructura de experimentos (F1) |

Las cifras de la F0 salen de `docs/F0_ESTADISTICAS.md` (§7 y §8), que se genera con
`python -m ccls f0 stats`. Las del "antes" (primera construcción, con `.changeset/`
todavía dentro) se midieron sobre esa construcción antes de reemplazarla, con el mismo
código.

---

## 7.2 · Fuga del prefijo de convención

**Qué se prueba:** que ninguna entrada del dataset contiene el prefijo de Conventional
Commits usado para etiquetar, ni ninguna de sus variantes.

**Dónde:** `tests/test_prefix_leakage.py`. Corre sobre:

1. Fixtures sintéticos con fugas plantadas a propósito: deben **fallar**. Si nunca
   fallan, el test no prueba nada.
2. El dataset real en `data/processed/`: debe **pasar**.

**Patrones cubiertos:** `fix:` `feat:` `refactor:` `docs:`, con y sin scope
(`fix(auth):`), con `!` de breaking change, en cualquier capitalización, al inicio de
cualquier línea (no solo la primera), **detrás de una viñeta** (`* feat:`, `- fix:`,
`+ docs:`), y variantes fuera de la convención estricta: `[FIX]`, `[BUGFIX]`,
`bugfix:`, `FEATURE:`, `chore:`, `chore(deps):`.

### Dos huecos del detector, encontrados antes de extraer

**1. Cuerpos de squash-merge.** GitHub copia al cuerpo del commit la lista de commits
de la rama, con su prefijo: `* feat: add warning…`. El detector original no contemplaba
la viñeta. Medido sobre **todos** los commits etiquetables de cada repo (historial
completo, `--no-merges --first-parent`), después de la limpieza que existía:

| repo | etiquetables | cuerpos con `* tipo:` sin detectar | % |
|---|---:|---:|---:|
| sveltejs/svelte | 2.403 | 696 | 29,0% |
| vitest-dev/vitest | 4.003 | 164 | 4,1% |
| nuxt/nuxt | 5.580 | 77 | 1,4% |
| angular/angular-cli | 8.013 | 33 | 0,4% |
| vitejs/vite | 5.690 | 21 | 0,4% |

**2. Variantes solo al inicio del texto.** Los patrones de variantes (`[FIX]`, `chore:`)
usaban `^` sin `re.MULTILINE`: una variante en la segunda línea pasaba sin detectar.

Para los dos huecos se agregaron fixtures plantados. Con el `label.py` viejo, **8
tests fallaron**; con el arreglo pasan. La limpieza borra el prefijo y conserva la
viñeta y el contenido (`* feat: agrega aviso` → `* agrega aviso`).

### El `diff` tiene su propio chequeo

El detector genérico sobre el `diff` no sirve como prueba. En la primera construcción
marcó **1.521 registros**, 1.485 de ellos de svelte (los `.changeset`, ver abajo).
Quitando los `.changeset`, lo que queda son falsos positivos de código: `docs: false,`
en TS, `refactor: TypeScriptFileRefactor`, los mensajes `fix: '…'` de los diagnósticos
de nuxt, claves de YAML. En el dataset final son **43 registros**, y se reportan como
dato informativo.

El chequeo que sí es prueba (`label.diff_repite_mensaje_propio`): alguna línea del
diff es **el tipo del propio commit + el comienzo de su propio asunto** (25
caracteres, sin el sufijo `(#1234)`), con viñeta y scope opcionales.

- **Sabe fallar con datos reales:** en la primera construcción marcó **1.190 registros**
  de svelte.
- Fixtures plantados: un `.changeset` y una línea `- feat(kit):` fallan; `docs: false,`,
  `refactor: TypeScriptFileRefactor` y un `fix:` con otro asunto no.
- **Límite:** solo ve la etiqueta escrita. Una etiqueta que se filtra por correlación,
  sin que la línea aparezca, la cubre §7.3.

Buscar solo el tipo propio, sin el asunto, habría marcado 11 registros, todos falsos
positivos (diagnósticos de nuxt, `fix: () => void` en svelte).

### Decisión: `.changeset/` fuera de todas las entradas (2026-09-14)

svelte usa *changesets*: casi todos sus commits agregan un `.changeset/xxx.md` con la
línea `fix: …` o `feat: …` **y** el tipo de versión. El tipo de versión delata la clase
aunque se borre la línea. Cruce en la primera construcción:

| etiqueta | `patch` | `minor` | sin bump visible |
|---|---:|---:|---:|
| fix | 1.309 | 3 | 3 |
| feat | 122 | 53 | 0 |
| docs | 5 | 0 | 1 |

**Decisión:** `.changeset/` se saca del `diff`, de `files`, de las extensiones y del
conteo de líneas (`config/repos.yaml` → `f0_extraccion.rutas_excluidas`). svelte **no**
se descarta: es uno de los dos repos fuera de la comunidad Vite/Vue, y quitarlo
empeoraría la diversidad, que es la limitación principal del dataset (README).

- Afecta a 1.496 de los 2.000 commits de svelte. Ninguno queda con el diff vacío.
- `manifest_sha256` no cambia (`0177140c…`): son los mismos commits con las mismas
  etiquetas. `dataset_jsonl_sha256` sí: `ee4b6d65…` → `797b73e4…`.
- `auditoria.n_archivos_excluidos` guarda cuántos archivos se quitaron. Es auditoría,
  nunca entrada del modelo.

### Resultado sobre el dataset final

| chequeo | registros |
|---|---:|
| `message` con prefijo (detector genérico) | **0** |
| `diff` que repite el mensaje del propio commit con su prefijo | **0** |
| `diff` con algún `tipo:` al inicio de línea (informativo: es código) | 43 |
| mensajes vacíos después de quitar el prefijo | 0 |

---

## 7.3 · Fuga por correlación

**Qué se prueba:** que ningún token candidato predice una clase muy por encima de su
frecuencia base. Cubre lo que §7.2 no ve: la etiqueta filtrada sin que la palabra
aparezca, como `patch` ↔ `fix` en los changesets.

**Dónde:** `src/ccls/fuga_correlacion.py` (reutilizable: los candidatos son una lista)
y `tests/test_fuga_correlacion.py`.

**Estadístico.** Para cada token *t*, clase *c* y ámbito (dataset entero y cada repo
por separado):

- *P(t)*: frecuencia base del token.
- *P(t|c)*: frecuencia del token dentro de la clase.
- **ganancia** = (cota inferior de Wilson al 95% de *P(c|t)* − *P(c)*) / (1 − *P(c)*).

Falla si **ganancia ≥ 0,5** en un token presente en **al menos 20 registros** del
ámbito.

**Por qué no se usa el cociente P(t|c) / P(t) directamente.** Es igual a *P(c|t)* /
*P(c)*, así que está acotado por 1 / *P(c)*. Con `fix` en el 55% del dataset, ni una
fuga perfecta pasa de 1,8, y un umbral que la atrapara dispararía por ruido en las
clases chicas. La ganancia normaliza eso (0 = el token no dice nada de la clase, 1 =
siempre que aparece es esa clase). La cota de Wilson evita que un token visto en pocos
registros dispare por azar. Las tablas reportan *P(t)* y *P(t|c)* igual, para leerlas
en los términos originales.

**Tokens candidatos:** ruta `.changeset/`; bump `patch` / `minor` / `major` en el
frontmatter; las palabras `patch`, `minor` y `major` en cualquier entrada; ruta
`CHANGELOG`; encabezado de versión de changelog (`# 1.2.3`); encabezado de tipo
(`### Bug Fixes`, `### Features`…); entrada de changelog con scope (`* **scope:**`); y
"diff vacío", por si la exclusión de rutas dejaba commits sin diff que delataran su
clase.

### Sabe fallar

**Fixtures sintéticos** (6 tests, con la proporción de clases del dataset real):
detecta una fuga en la clase mayoritaria, donde el cociente crudo no llega a 1,82 y
la ganancia supera 0,9; también en una clase minoritaria y en una fuga confinada a un
repo. No dispara con un token repartido como las clases ni con un token visto en 5
registros.

**Con datos reales**, sobre la primera construcción, con `.changeset/` dentro:

| token | ámbito | con token | P(t) | clase | P(t\|c) | P(c) | P(c\|t) | ganancia |
|---|---|---:|---:|---|---:|---:|---:|---:|
| changeset: bump patch | todos | 1.440 | 14,4% | fix | 23,8% | 55,2% | 91,1% | 0,77 |
| changeset: bump minor | todos | 56 | 0,6% | feat | 3,4% | 15,7% | 94,6% | 0,83 |
| changeset: ruta | todos | 1.496 | 15,0% | fix | 23,8% | 55,2% | 87,9% | 0,69 |
| palabra patch | todos | 1.521 | 15,2% | fix | 24,4% | 55,2% | 88,6% | 0,71 |
| changeset: bump patch | svelte | 1.440 | 72,0% | fix | 89,8% | 73,0% | 91,1% | 0,61 |
| changeset: bump minor | svelte | 56 | 2,8% | feat | 25,4% | 10,4% | 94,6% | 0,84 |
| palabra minor | svelte | 77 | 3,9% | feat | 29,2% | 10,4% | 79,2% | 0,65 |

### Resultado sobre el dataset final

- Tokens de changeset: **0 registros** con el token.
- `palabra patch`: 84 registros, ganancia 0,03. `palabra minor`: 87 registros, 0,16.
  `palabra major`: 224 registros, 0,06. Sin changesets, las palabras no dicen nada.
- `diff vacío`: 3 registros (nuxt 1, vitest 2), sin soporte ni señal.
- **Fallan 4 mediciones, todas de CHANGELOG.** La tabla completa está en
  `docs/F0_ESTADISTICAS.md` §8.

| token | ámbito | con token | P(t) | clase | P(t\|c) | P(c) | P(c\|t) | ganancia |
|---|---|---:|---:|---|---:|---:|---:|---:|
| changelog: ruta | todos | 146 | 1,5% | docs | 6,7% | 20,9% | 96,6% | 0,90 |
| changelog: encabezado de versión | todos | 124 | 1,2% | docs | 5,9% | 20,9% | 99,2% | 0,94 |
| changelog: ruta | angular-cli | 127 | 6,3% | docs | 44,7% | 14,1% | 99,2% | 0,95 |
| changelog: encabezado de versión | angular-cli | 124 | 6,2% | docs | 43,6% | 14,1% | 99,2% | 0,95 |

`changelog: encabezado de tipo` (11 registros) y `changelog: entrada con scope`
(ganancia 0,41 hacia `feat`) no fallan.

### CHANGELOG de angular-cli: falla, **decisión pendiente**

Qué son esos registros:

- 146 registros tocan un `CHANGELOG`: 141 `docs`, 3 `feat` y 2 `refactor`. 127 son de
  angular-cli.
- **122 son el mismo commit repetido por versión:** `docs: release notes for the vX
  release`. 133 tocan un solo archivo y 136 tocan solo `.md`.

La medición que importa para decidir es si el token dice algo más que la regla
estructural legítima de `DESIGN.md` §6.1 ("todos los archivos son `.md`/`.rst`/`.txt`
→ `docs`"), que ya se sabe que deja la clase casi trivial:

| condición | P(docs) |
|---|---:|
| solo toca `.md`/`.rst`/`.txt` | 1.610 / 1.628 (98,9%) |
| solo `.md` **y** toca CHANGELOG | 136 / 136 |
| solo `.md` **sin** CHANGELOG | 1.474 / 1.492 (98,8%) |
| **no** solo `.md` y toca CHANGELOG | 5 / 10 |

A diferencia del changeset, que anota el tipo de *otro* cambio (el de código), aquí el
CHANGELOG *es* el cambio. Condicionado a la señal estructural, el token no agrega
información. Pero la regla de la prueba es la que es, y falla: **la F0 no se cierra
hasta decidir**. Opciones:

- **(a) Condicionar la prueba a la señal estructural declarada:** medir la ganancia de
  cada token dentro de los estratos "solo docs / no solo docs". Es genérica, sin lista
  de excepciones. Costo: no puede ver una fuga hacia `docs` dentro de commits que ya
  son solo `.md`, aunque ahí la clase ya está decidida por la estructura.
- **(b) Excepción explícita por token**, con la tabla de arriba como justificación
  escrita en el test. Es simple, pero abre una puerta de excepciones en una prueba de
  fuga.
- **(c) Excluir CHANGELOG como `.changeset/`.** No se recomienda: 133 commits quedarían
  con el diff vacío y todos `docs`, y la fuga pasaría a "diff vacío".

---

### Decisión abierta: referencias a issues (`Fixes #123`, `Closes #456`)

Es señal legítima del dominio (el autor está diciendo qué arregla el commit) y a la
vez una fuga casi perfecta si el issue tiene un tipo asociado. Posición por defecto:
**se conserva el texto**, pero `build.py` guarda una bandera booleana
`tiene_referencia_issue` en los metadatos, para poder medir en la F2 cuánto aporta esa
señal por sí sola y decidir con el número delante, no a priori. En la F0 aparece en el
21,2% de los `fix`, 8,0% de los `feat`, 3,9% de los `docs` y 1,3% de los `refactor`
(`docs/F0_ESTADISTICAS.md` §5).

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
