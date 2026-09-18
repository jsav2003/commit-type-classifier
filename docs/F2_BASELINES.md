# F2 · Baselines

Generado por `python -m ccls f2 report`. **No se edita a mano.** El diseño de la fase está en `DESIGN.md` §6.1 y §6.2; cómo se leen los números, en §7.3 y §7.4.

- Semillas: 1, 2, 3, 4, 5. Cada celda es la media entre semillas con su intervalo t al 95%, nunca el mejor resultado (§7.3).
- En las particiones por repositorio y temporal la división no depende de la semilla y los modelos son deterministas: el intervalo tiene ancho cero y se omite.
- Una celda `—` es una clase sin ejemplos en prueba: la F1 no existe, y no vale 0.
- Dataset: `manifest_sha256` `0177140ce63d03f1fa1aa38f7cde6bdc6ef57f3442b0cc8cf4278e2d7b7249a5`.

## Qué modelo es cada uno

| modelo | qué es |
|---|---|
| `trivial` | Siempre la clase mayoritaria del entrenamiento. El piso de §6.1. |
| `regla_docs` | El trivial más la regla de una línea de §6.1: si todos los archivos tocados son `.md`/`.rst`/`.txt`, `docs`. |
| `clasico_lr` | §6.2: TF-IDF del mensaje (palabras y bigramas) más los rasgos hechos a mano, con regresión logística. |
| `clasico_lr_balanceado` | El mismo, con `class_weight="balanced"`. La reponderación que §4.4 manda considerar por lo escasa que es `refactor`. |
| `clasico_gb` | Los mismos rasgos con gradient boosting; el TF-IDF entra reducido a 150 componentes con SVD, que es lo que los árboles pueden tragar. |
| `clasico_lr_msg` | Ablación: solo el mensaje. La diferencia con `clasico_lr` es lo que aportan los rasgos hechos a mano. |
| `clasico_lr_issue` | Ablación: `clasico_lr` más `tiene_referencia_issue`, la bandera que quedó fuera de las entradas en la F1. |

## Cómo hay que leer esto

**`docs` casi no requiere modelo.** La regla de una línea de §6.1 ya saca la F1 de `docs` que aparece en la fila `regla_docs`. Cualquier F1 macro alto de los demás modelos hay que mirarlo restando eso: una parte viene de una señal estructural, no de haber aprendido la tarea.

**La partición por repositorio es la principal** (DESIGN.md §5). La aleatoria está para mostrar cuánto se infla el número, no para presumirlo.

**El clásico de referencia es `clasico_lr_balanceado`.** DESIGN.md §4.4 manda considerar la reponderación por lo escasa que es `refactor` y decidirla con el número delante. Está en las tablas: reponderar sube el F1 de `refactor` en 6 de 7 folds y el F1 macro en 6 de 7, y baja la exactitud en 6 de 7. Por §7.4 este proyecto mira el F1 por clase antes que la exactitud — un modelo que nunca predice `refactor` está roto aunque acierte mucho —, así que la reponderación se adopta y `clasico_lr` se sigue reportando al lado, sin ella.

Esas cuentas incluyen el fold `sveltejs/svelte`, que tiene 1 `refactor` en prueba. Ahí la diferencia no significa nada: §5 dice que un F1 sobre un puñado de casos no es una métrica, y por eso también entra a la cuenta en vez de desaparecer sin que se note.

## Partición aleatoria

80/20 estratificada por clase, con una división distinta por semilla. **Fuga información**: commits del mismo repositorio quedan a los dos lados.

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `trivial` | 55,2% | 17,8% | 71,2% | 0,0% | 0,0% |
| `regla_docs` | 71,1% [70,6%, 71,7%] | 41,4% [40,9%, 41,9%] | 79,2% [78,9%, 79,5%] | 0,0% | 86,5% [84,9%, 88,2%] |
| `clasico_lr` | 82,8% [82,0%, 83,5%] | 74,5% [73,1%, 75,8%] | 87,4% [86,7%, 88,1%] | 61,1% [59,2%, 63,0%] | 92,4% [91,7%, 93,2%] |
| `clasico_lr_balanceado` | 80,0% [78,8%, 81,3%] | 74,7% [73,4%, 75,9%] | 84,7% [83,4%, 85,9%] | 62,7% [60,2%, 65,2%] | 92,7% [91,7%, 93,7%] |
| `clasico_gb` | 82,3% [81,4%, 83,2%] | 73,6% [71,6%, 75,6%] | 87,0% [86,5%, 87,5%] | 58,8% [55,3%, 62,3%] | 93,2% [92,2%, 94,2%] |

## Partición por repositorio — la principal

Un fold por repo, con ese repo entero en prueba. Es la que responde si esto sirve en un proyecto que el modelo nunca vio.

### Fold `angular/angular-cli` en prueba — n = 2000

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `trivial` | 46,2% | 15,8% | 63,1% | 0,0% | 0,0% |
| `regla_docs` | 57,4% | 39,2% | 68,4% | 0,0% | 88,4% |
| `clasico_lr` | 65,8% | 59,2% | 73,6% | 43,4% | 91,1% |
| `clasico_lr_balanceado` | 70,3% | 68,9% | 76,0% | 52,2% | 91,8% |
| `clasico_gb` | 63,3% [62,8%, 63,8%] | 54,2% [53,4%, 55,0%] | 72,0% [71,7%, 72,4%] | 38,6% [37,0%, 40,2%] | 90,7% [90,0%, 91,4%] |

### Fold `nuxt/nuxt` en prueba — n = 2000

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `trivial` | 49,9% | 16,6% | 66,5% | 0,0% | 0,0% |
| `regla_docs` | 76,4% | 43,0% | 80,9% | 0,0% | 91,0% |
| `clasico_lr` | 85,4% | 72,5% | 88,2% | 65,8% | 95,3% |
| `clasico_lr_balanceado` | 77,3% | 67,6% | 79,0% | 59,8% | 95,2% |
| `clasico_gb` | 84,1% [83,7%, 84,6%] | 70,1% [69,1%, 71,2%] | 86,9% [86,7%, 87,2%] | 60,4% [59,5%, 61,4%] | 95,6% [95,2%, 95,9%] |

### Fold `sveltejs/svelte` en prueba — n = 2000

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `trivial` | 73,0% | 21,1% | 84,4% | 0,0% | 0,0% |
| `regla_docs` | 85,5% | 44,4% | 91,0% | 0,0% | 86,7% |
| `clasico_lr` | 87,0% | 56,7% | 92,7% | 45,3% | 88,8% |
| `clasico_lr_balanceado` | 82,0% | 56,8% | 89,6% | 45,8% | 90,3% |
| `clasico_gb` | 86,3% [85,9%, 86,7%] | 57,6% [56,9%, 58,3%] | 92,1% [91,7%, 92,4%] | 46,1% [44,0%, 48,2%] | 87,6% [87,2%, 87,9%] |

### Fold `vitejs/vite` en prueba — n = 2000

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `trivial` | 53,3% | 17,4% | 69,6% | 0,0% | 0,0% |
| `regla_docs` | 69,1% | 40,5% | 77,5% | 0,0% | 84,6% |
| `clasico_lr` | 81,3% | 70,2% | 86,2% | 52,9% | 93,7% |
| `clasico_lr_balanceado` | 79,1% | 73,1% | 83,3% | 58,2% | 91,6% |
| `clasico_gb` | 79,3% [79,1%, 79,5%] | 65,7% [65,3%, 66,1%] | 84,7% [84,5%, 84,9%] | 47,2% [45,5%, 48,9%] | 94,3% [94,0%, 94,7%] |

### Fold `vitest-dev/vitest` en prueba — n = 2000

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `trivial` | 53,7% | 17,5% | 69,9% | 0,0% | 0,0% |
| `regla_docs` | 67,4% | 39,1% | 76,7% | 0,0% | 79,7% |
| `clasico_lr` | 79,8% | 68,0% | 84,9% | 64,5% | 90,7% |
| `clasico_lr_balanceado` | 74,6% | 68,3% | 78,5% | 63,2% | 91,1% |
| `clasico_gb` | 78,6% [78,1%, 79,0%] | 67,2% [66,4%, 68,0%] | 84,2% [83,9%, 84,5%] | 61,3% [60,1%, 62,5%] | 91,1% [90,5%, 91,7%] |

## Partición temporal

Corte global el 2025-06-01: entrena con lo anterior y evalúa con lo posterior, 7.999 / 2.001.

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `trivial` | 58,4% | 18,4% | 73,8% | 0,0% | 0,0% |
| `regla_docs` | 74,5% | 42,4% | 82,0% | 0,0% | 87,5% |
| `clasico_lr` | 83,4% | 71,6% | 88,8% | 60,0% | 93,7% |
| `clasico_lr_balanceado` | 80,2% | 73,3% | 85,9% | 56,5% | 92,9% |
| `clasico_gb` | 82,8% [82,4%, 83,2%] | 70,8% [70,0%, 71,5%] | 88,3% [88,1%, 88,6%] | 58,1% [56,9%, 59,3%] | 94,3% [93,9%, 94,8%] |

## `refactor`, fold por fold

DESIGN.md §5: `refactor` es el 8,2% del dataset, angular-cli aporta el 57% y svelte 1 solo ejemplo. Un F1 calculado sobre un puñado de casos no es una métrica, así que va con el n al lado y **no hay fila de promedio entre folds**.

### Partición aleatoria

| fold | n `refactor` en prueba | `trivial` | `regla_docs` | `clasico_lr` | `clasico_lr_balanceado` | `clasico_gb` |
|---|---:|---:|---:|---:|---:|---:|
| aleatoria | 164 | 0,0% | 0,0% | 56,8% [53,6%, 60,1%] | 58,5% [55,9%, 61,2%] | 55,4% [50,8%, 60,0%] |

### Partición repositorio

| fold | n `refactor` en prueba | `trivial` | `regla_docs` | `clasico_lr` | `clasico_lr_balanceado` | `clasico_gb` |
|---|---:|---:|---:|---:|---:|---:|
| angular/angular-cli | 468 | 0,0% | 0,0% | 28,6% | 55,4% | 15,5% [13,6%, 17,3%] |
| nuxt/nuxt | 102 | 0,0% | 0,0% | 40,7% | 36,6% | 37,5% [34,8%, 40,4%] |
| sveltejs/svelte | 1 | 0,0% | 0,0% | 0,0% | 1,4% | 4,7% [4,1%, 5,3%] |
| vitejs/vite | 151 | 0,0% | 0,0% | 48,1% | 59,4% | 36,6% [34,1%, 39,1%] |
| vitest-dev/vitest | 98 | 0,0% | 0,0% | 31,8% | 40,5% | 32,2% [29,7%, 34,6%] |

### Partición temporal

| fold | n `refactor` en prueba | `trivial` | `regla_docs` | `clasico_lr` | `clasico_lr_balanceado` | `clasico_gb` |
|---|---:|---:|---:|---:|---:|---:|
| temporal | 176 | 0,0% | 0,0% | 44,0% | 58,0% | 42,3% [40,0%, 44,6%] |

## Cuánto infla la partición aleatoria

Es el punto 1 de DESIGN.md §11. La partición aleatoria reparte commits del mismo repositorio a los dos lados y el modelo memoriza el proyecto. La columna del medio es el **peor fold** de la partición por repositorio, no el promedio: es el que dice qué pasa en el proyecto más distinto de los que vio.

| modelo | F1 macro, aleatoria | F1 macro, por repositorio (peor fold) | caída |
|---|---:|---:|---:|
| `trivial` | 17,8% | 15,8% (angular/angular-cli) | -2,0 |
| `regla_docs` | 41,4% | 39,1% (vitest-dev/vitest) | -2,3 |
| `clasico_lr` | 74,5% | 56,7% (sveltejs/svelte) | -17,8 |
| `clasico_lr_balanceado` | 74,7% | 56,8% (sveltejs/svelte) | -17,9 |
| `clasico_gb` | 73,6% | 54,2% (angular/angular-cli) | -19,4 |

## Ablaciones

Qué aporta cada pieza, medido y no afirmado.

### Partición repositorio

#### Fold `angular/angular-cli` en prueba — n = 2000

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `clasico_lr` | 65,8% | 59,2% | 73,6% | 43,4% | 91,1% |
| `clasico_lr_msg` | 51,8% | 36,8% | 66,0% | 32,8% | 43,1% |
| `clasico_lr_issue` | 66,2% | 59,9% | 74,1% | 43,8% | 91,2% |

#### Fold `nuxt/nuxt` en prueba — n = 2000

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `clasico_lr` | 85,4% | 72,5% | 88,2% | 65,8% | 95,3% |
| `clasico_lr_msg` | 72,0% | 57,3% | 79,1% | 50,7% | 74,6% |
| `clasico_lr_issue` | 85,0% | 71,8% | 88,0% | 65,6% | 95,3% |

#### Fold `sveltejs/svelte` en prueba — n = 2000

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `clasico_lr` | 87,0% | 56,7% | 92,7% | 45,3% | 88,8% |
| `clasico_lr_msg` | 79,9% | 44,2% | 88,9% | 14,9% | 67,5% |
| `clasico_lr_issue` | 87,0% | 56,5% | 92,8% | 44,4% | 88,8% |

#### Fold `vitejs/vite` en prueba — n = 2000

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `clasico_lr` | 81,3% | 70,2% | 86,2% | 52,9% | 93,7% |
| `clasico_lr_msg` | 69,8% | 53,2% | 78,9% | 37,3% | 70,3% |
| `clasico_lr_issue` | 81,2% | 70,0% | 86,1% | 52,3% | 93,7% |

#### Fold `vitest-dev/vitest` en prueba — n = 2000

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `clasico_lr` | 79,8% | 68,0% | 84,9% | 64,5% | 90,7% |
| `clasico_lr_msg` | 71,5% | 56,2% | 79,7% | 45,3% | 75,0% |
| `clasico_lr_issue` | 79,4% | 67,8% | 84,6% | 64,1% | 90,8% |

### Partición temporal

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `clasico_lr` | 83,4% | 71,6% | 88,8% | 60,0% | 93,7% |
| `clasico_lr_msg` | 76,7% | 61,3% | 84,5% | 49,8% | 79,0% |
| `clasico_lr_issue` | 83,7% | 72,6% | 89,0% | 60,5% | 93,7% |

## La prueba de etiquetas aleatorias, sobre `clasico_lr`

`LEAKAGE.md` §7.1 se corrió en la F1 con el modelo de humo, que solo mira el mensaje. El clásico estrena rasgos —extensiones, la regla de §6.1, los verbos, los conteos del diff—, y cada rasgo nuevo es un camino nuevo por el que la etiqueta podría colarse. Se repite la prueba sobre `clasico_lr`: con las etiquetas de entrenamiento barajadas, la exactitud no puede pasar la tasa de la clase mayoritaria de prueba por más de +2,0 puntos.

| partición | fold | techo del azar | exactitud, etiquetas barajadas | exceso | estado |
|---|---|---:|---:|---:|---|
| aleatoria | aleatoria | 55,2% | 54,0% [53,7%, 54,2%] | -1,3 | pasa |
| repositorio | angular/angular-cli | 46,2% | 45,0% [43,7%, 46,2%] | -1,2 | pasa |
| repositorio | nuxt/nuxt | 49,9% | 49,3% [48,7%, 49,9%] | -0,6 | pasa |
| repositorio | sveltejs/svelte | 73,0% | 60,1% [35,1%, 85,1%] | -13,0 | pasa |
| repositorio | vitejs/vite | 53,3% | 52,0% [51,4%, 52,7%] | -1,3 | pasa |
| repositorio | vitest-dev/vitest | 53,7% | 52,5% [51,7%, 53,3%] | -1,2 | pasa |
| temporal | temporal | 58,4% | 56,8% [55,8%, 57,8%] | -1,6 | pasa |

7 folds: 7 pasan, 0 fallan, 0 no concluyentes.

## Matrices de confusión — `clasico_lr`, partición por repositorio

Fila: etiqueta verdadera. Columna: predicción. Primera semilla de cada fold.

**angular/angular-cli**

| verdad \ predicción | `fix` | `feat` | `refactor` | `docs` |
|---|---:|---:|---:|---:|
| `fix` | 881 | 31 | 7 | 4 |
| `feat` | 203 | 109 | 11 | 4 |
| `refactor` | 349 | 35 | 81 | 3 |
| `docs` | 37 | 0 | 0 | 245 |

**nuxt/nuxt**

| verdad \ predicción | `fix` | `feat` | `refactor` | `docs` |
|---|---:|---:|---:|---:|
| `fix` | 895 | 64 | 27 | 11 |
| `feat` | 74 | 179 | 6 | 6 |
| `refactor` | 40 | 23 | 35 | 4 |
| `docs` | 23 | 13 | 2 | 598 |

**sveltejs/svelte**

| verdad \ predicción | `fix` | `feat` | `refactor` | `docs` |
|---|---:|---:|---:|---:|
| `fix` | 1384 | 37 | 23 | 17 |
| `feat` | 105 | 74 | 23 | 7 |
| `refactor` | 1 | 0 | 0 | 0 |
| `docs` | 35 | 7 | 5 | 282 |

**vitejs/vite**

| verdad \ predicción | `fix` | `feat` | `refactor` | `docs` |
|---|---:|---:|---:|---:|
| `fix` | 1022 | 26 | 7 | 12 |
| `feat` | 188 | 144 | 3 | 16 |
| `refactor` | 79 | 16 | 51 | 5 |
| `docs` | 15 | 7 | 0 | 409 |

**vitest-dev/vitest**

| verdad \ predicción | `fix` | `feat` | `refactor` | `docs` |
|---|---:|---:|---:|---:|
| `fix` | 948 | 78 | 30 | 18 |
| `feat` | 140 | 253 | 14 | 7 |
| `refactor` | 52 | 16 | 28 | 2 |
| `docs` | 19 | 23 | 6 | 366 |
