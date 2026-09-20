# F3 · Techo del anotador (Claude)

Generado por `python -m ccls f3 report`. **No se edita a mano.** El diseño de la fase está en `DESIGN.md` §4.2 y §7.5; cómo se leen los números, en §7.3 y §7.4.

- Dataset: `manifest_sha256` `0177140ce63d03f1fa1aa38f7cde6bdc6ef57f3442b0cc8cf4278e2d7b7249a5`.
- Muestra: `hoja_sha256` `42a4ef08b50f18be24639b47456372746d65b8aba14ed3ad398078ebcc829ab8`, `clave_sha256` `da59ba1afb66f71e214f3fce57144ff553f74d4487cb3b9055eb0df9d5460c1c`.
- Predicciones del modelo: sha256 `816ef7421e4dd8afac17d8fff1deabb942519e1401aec43e64f033c58c3ef141`.
- Semilla del muestreo: 20260920. Cuotas del estrato B: docs 35, feat 35, fix 40, refactor 40.
- Estrato A, repos y SHA fijados: `python-poetry/poetry` @ `be56ff07db`, `rust-lang/rustfmt` @ `2f80bd5ba4`, `spf13/cobra` @ `adbc881390`, `hashicorp/hcl` @ `2f8831b835`.
- 150 ítems en A, 150 en B y 50 repeticiones.

> **Esto no es un techo humano.** Las 350 etiquetas las puso **Claude**, un modelo de lenguaje, en una sola pasada, leyendo únicamente la hoja ciega (mensaje, archivos y líneas; sin la etiqueta declarada, el repo ni las predicciones) y **antes** de calcular ningún número, porque no hubo tiempo de etiquetar a mano. Mide cuánto coincide un lector fuerte con la etiqueta declarada; no dice cuánto coincidiría una persona. La fase sigue pendiente de un anotador humano (`python -m ccls f3 label`).
>
> Criterio fijo: `fix` corrige un comportamiento incorrecto; `feat` añade una capacidad; `refactor` reestructura o renombra sin cambiar el comportamiento; `docs` es solo documentación o changelog; `ninguna` es un release, un bump de versión, CI, dependencias, tests solos o estilo; `mixto` es un cambio que hace varias cosas de peso.
>
> Dos límites: un modelo de lenguaje puede parecerse más a quien escribió la etiqueta declarada que una persona, así que este acuerdo puede sobrestimar el techo; y las 50 repeticiones se etiquetaron en el mismo contexto que las originales, por lo que el acuerdo consigo mismo de la sección 4 no es comparable con el de una persona.

## Cómo hay que leer esto

**Un techo bajo es un resultado, no un fallo.** No se re-muestreó ni se ajustó nada después de ver la cifra (`DESIGN.md` §7.5 y §9).

**Los dos estratos miden cosas distintas y no se mezclan.** B tiene etiqueta declarada y da el techo; A no la tiene y da el caso de uso real. Ninguna tabla los promedia entre sí.

**Cada acuerdo lleva su n y su intervalo.** Con 35-40 ítems por clase el intervalo de Wilson es ancho (±12-15 puntos): una diferencia de pocos puntos entre dos celdas no significa nada, y cuando los intervalos se superponen se dice.

## 1 · El techo (estrato B)

Estrato B: commits del dataset con el prefijo ya quitado, por cuotas de clase. El techo es el acuerdo **anotador ↔ etiqueta declarada** (`DESIGN.md` §7.5). Se da por clase declarada, con el número de ítems al lado y el intervalo de Wilson al 95%. El global reponderado usa las proporciones reales del dataset: `fix` 55,2%, `feat` 15,7%, `refactor` 8,2%, `docs` 20,9%. Su intervalo es normal, `var = Σ wc²·pc(1-pc)/nc`, sin azar.

### Sin `mixto` ni `ninguna`

_Los ítems donde el anotador puso `mixto` o `ninguna` salen del denominador._

| clase declarada | n | anotador ↔ declarada | modelo ↔ declarada |
|---|---:|---|---|
| `fix` | 38 | 73,7% [58,0%, 85,0%] | 78,9% [63,7%, 88,9%] |
| `feat` | 34 | 85,3% [69,9%, 93,6%] | 67,6% [50,8%, 80,9%] |
| `refactor` | 38 | 78,9% [63,7%, 88,9%] | 63,2% [47,3%, 76,6%] |
| `docs` | 30 | 100,0% [88,6%, 100,0%] | 93,3% [78,7%, 98,2%] |
| **global, sin reponderar** | 140 | 83,6% [76,6%, 88,8%] | 75,0% [67,2%, 81,4%] |
| **global, reponderado** | 140 | **81,4% [73,4%, 89,5%]** | 78,9% [71,0%, 86,8%] |

### Contándolas como desacuerdo

_Todos los ítems entran; `mixto` y `ninguna` cuentan como no coincidir._

| clase declarada | n | anotador ↔ declarada | modelo ↔ declarada |
|---|---:|---|---|
| `fix` | 40 | 70,0% [54,6%, 81,9%] | 80,0% [65,2%, 89,5%] |
| `feat` | 35 | 82,9% [67,3%, 91,9%] | 65,7% [49,2%, 79,2%] |
| `refactor` | 40 | 75,0% [59,8%, 85,8%] | 62,5% [47,0%, 75,8%] |
| `docs` | 35 | 85,7% [70,6%, 93,7%] | 91,4% [77,6%, 97,0%] |
| **global, sin reponderar** | 150 | 78,0% [70,7%, 83,9%] | 74,7% [67,2%, 81,0%] |
| **global, reponderado** | 150 | **75,7% [67,2%, 84,2%]** | 78,7% [71,1%, 86,3%] |

Kappa de Cohen anotador ↔ declarada, sin `mixto` ni `ninguna`: **0,78** (n = 140). Se calcula sobre la muestra por cuotas, no sobre el dataset: las cuotas cambian la prevalencia de cada clase y con ella el acuerdo esperado por azar.

### Qué puso el anotador en cada clase declarada

Conteos. Fila: etiqueta declarada. Columna: lo que puso el anotador.

| declarada \ anotador | `fix` | `feat` | `refactor` | `docs` | `mixto` | `ninguna` |
|---|---:|---:|---:|---:|---:|---:|
| `fix` | 28 | 6 | 2 | 2 | 0 | 2 |
| `feat` | 2 | 29 | 2 | 1 | 0 | 1 |
| `refactor` | 5 | 3 | 30 | 0 | 0 | 2 |
| `docs` | 0 | 0 | 0 | 30 | 1 | 4 |

## 2 · Modelo contra anotador y contra prefijo

Modelo: `clasico_lr_balanceado`, el clásico de referencia de la F2. Cada ítem del estrato B lo predice un modelo entrenado **sin el repo** de ese ítem (el fold de la partición por repositorio); cada ítem del estrato A, uno entrenado con todo el dataset, porque esos repos no están en él. El estrato A no tiene etiqueta declarada, y por eso no hay techo ni reponderación ahí.

### Sin `mixto` ni `ninguna`

| medida | estrato | n | sin reponderar | reponderado al dataset |
|---|---|---:|---|---|
| anotador ↔ declarada (**techo**) | B | 140 | 83,6% [76,6%, 88,8%] | 81,4% [73,4%, 89,5%] |
| modelo ↔ declarada | B | 140 | 75,0% [67,2%, 81,4%] | 78,9% [71,0%, 86,8%] |
| modelo ↔ anotador | B | 140 | 73,6% [65,7%, 80,2%] | 75,0% [66,4%, 83,6%] |
| modelo ↔ anotador | A | 102 | 78,4% [69,5%, 85,3%] | — |

### Contándolas como desacuerdo

| medida | estrato | n | sin reponderar | reponderado al dataset |
|---|---|---:|---|---|
| anotador ↔ declarada (**techo**) | B | 150 | 78,0% [70,7%, 83,9%] | 75,7% [67,2%, 84,2%] |
| modelo ↔ declarada | B | 150 | 74,7% [67,2%, 81,0%] | 78,7% [71,1%, 86,3%] |
| modelo ↔ anotador | B | 150 | 68,7% [60,9%, 75,5%] | 69,7% [60,8%, 78,6%] |
| modelo ↔ anotador | A | 150 | 53,3% [45,4%, 61,1%] | — |

## 3 · Fuera de la convención (estrato A)

Commits **sin prefijo** de cuatro repos que el dataset nunca vio. No hay etiqueta declarada: solo se puede medir cuánto se parece el modelo al anotador. La caída de B a A es la medición directa del sesgo de selección de `DESIGN.md` §4.1, que hasta aquí solo estaba declarado.

### Modelo ↔ anotador, por estrato

Sin reponderar en los dos, para que los estratos sean comparables. **No se promedian entre sí.**

| variante | n en B | B | n en A | A | diferencia A − B | intervalos |
|---|---:|---|---:|---|---:|---|
| sin `mixto` ni `ninguna` | 140 | 73,6% [65,7%, 80,2%] | 102 | 78,4% [69,5%, 85,3%] | +4,9 | se superponen: la diferencia no es concluyente |
| contándolas como desacuerdo | 150 | 68,7% [60,9%, 75,5%] | 150 | 53,3% [45,4%, 61,1%] | -15,3 | se superponen: la diferencia no es concluyente |

### Por repo (variante sin `mixto` ni `ninguna`)

| repo | ítems | con clase del anotador | modelo ↔ anotador |
|---|---:|---:|---|
| `hashicorp/hcl` | 38 | 20 | 75,0% [53,1%, 88,8%] |
| `python-poetry/poetry` | 38 | 26 | 73,1% [53,9%, 86,3%] |
| `rust-lang/rustfmt` | 37 | 28 | 78,6% [60,5%, 89,8%] |
| `spf13/cobra` | 37 | 28 | 85,7% [68,5%, 94,3%] |

### Qué puso el anotador y qué predijo el modelo en A

| | `fix` | `feat` | `refactor` | `docs` | `mixto` | `ninguna` |
|---|---:|---:|---:|---:|---:|---:|
| anotador | 37 | 22 | 14 | 29 | 1 | 47 |
| modelo | 57 | 17 | 22 | 54 | — | — |

## 4 · El ruido del propio anotador

Ítems que se mostraron dos veces, la segunda al final y sin avisar. El acuerdo de uno consigo mismo es la cota de ruido del techo: ningún acuerdo con una etiqueta declarada debería pedirse más alto que el que el anotador logra con sus propias respuestas. Cuenta `mixto` y `ninguna` como etiquetas.

| estrato | pares | acuerdo consigo mismo | kappa |
|---|---:|---|---:|
| A | 25 | 100,0% [86,7%, 100,0%] | 1,00 |
| B | 25 | 100,0% [86,7%, 100,0%] | 1,00 |

## 5 · Cuántas veces no alcanzó la evidencia

El anotador ve lo mismo que el modelo: mensaje, archivos y líneas, **no** el texto del diff. `?` marca los ítems donde habría querido verlo. Es el dato que dice si el texto del diff, declarado como pendiente en `DESIGN.md` §6.2, hace falta de verdad en la F4.

| estrato | n | `?` (habría querido el diff) | `mixto` | `ninguna` |
|---|---:|---|---|---|
| A | 150 | 6,7% [3,7%, 11,8%] | 0,7% [0,1%, 3,7%] | 31,3% [24,5%, 39,1%] |
| B | 150 | 6,7% [3,7%, 11,8%] | 0,7% [0,1%, 3,7%] | 6,0% [3,2%, 11,0%] |

## 6 · Contra los números de la F2

Exactitud de `clasico_lr_balanceado` en la partición por repositorio de la F2 (2.000 commits por fold, con la proporción real de clases). Un fold por fila y sin promedio, como en `docs/F2_BASELINES.md`. Se compara con la fila **reponderado** de la sección 2, no con la de sin reponderar: la muestra humana está por cuotas de clase y su exactitud cruda no es comparable.

| fold | n prueba | exactitud | F1 macro |
|---|---:|---|---|
| `angular/angular-cli` | 2000 | 70,3% | 68,9% |
| `nuxt/nuxt` | 2000 | 77,3% | 67,6% |
| `sveltejs/svelte` | 2000 | 82,0% | 56,8% |
| `vitejs/vite` | 2000 | 79,1% | 73,1% |
| `vitest-dev/vitest` | 2000 | 74,6% | 68,3% |
