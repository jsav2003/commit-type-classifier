# Resultados

Generado por `python -m ccls results`. **No se edita a mano.** Junta los cuatro enfoques de DESIGN.md §6 en las tres particiones de §5; los números salen de `resultados/*.json` y las secciones de los mismos renderizadores que `docs/F2_BASELINES.md`, `docs/F4_TRANSFER.md` y `docs/F5_DESDE_CERO.md`.

- Semillas: 1, 2, 3, 4, 5. Cada celda es la media entre semillas con su intervalo t al 95%, nunca el mejor resultado (§7.3).
- En las particiones por repositorio y temporal la división no depende de la semilla y los modelos clásicos son deterministas: su intervalo tiene ancho cero y se omite.
- Una celda `—` es una clase sin ejemplos en prueba: la F1 no existe, y no vale 0.
- Dataset: `manifest_sha256` `0177140ce63d03f1fa1aa38f7cde6bdc6ef57f3442b0cc8cf4278e2d7b7249a5`.

## Qué enfoque es cada uno

| modelo | enfoque | detalle | comando |
|---|---|---|---|
| `trivial` | piso | `docs/F2_BASELINES.md` | `f2 run` |
| `regla_docs` | piso | `docs/F2_BASELINES.md` | `f2 run` |
| `clasico_lr` | clásico | `docs/F2_BASELINES.md` | `f2 run` |
| `clasico_lr_balanceado` | clásico, reponderado | `docs/F2_BASELINES.md` | `f2 run` |
| `f4_codebert` | transfer learning | `docs/F4_TRANSFER.md` | `f4 run` |
| `f5_desde_cero` | red desde cero | `docs/F5_DESDE_CERO.md` | `f5 run` |

Las ablaciones del clásico y el gradient boosting no están aquí: viven en `docs/F2_BASELINES.md`.

## La comparación en una tabla

F1 macro, media entre semillas. **Negrita** = la media más alta de la fila. Que un número sea el más alto no lo hace el ganador: los intervalos de las tablas de abajo se superponen en varios folds, y en los reportes de cada fase está el veredicto fold por fold. La partición aleatoria está para mostrar cuánto se infla el número, no como resultado (DESIGN.md §5).

| partición | fold | n | `trivial` | `regla_docs` | `clasico_lr` | `clasico_lr_balanceado` | `f4_codebert` | `f5_desde_cero` |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| aleatoria | aleatoria | 1999 | 17,8% | 41,4% | 74,5% | **74,7%** | 72,7% | 69,3% |
| repositorio | angular/angular-cli | 2000 | 15,8% | 39,2% | 59,2% | **68,9%** | 68,1% | 60,0% |
| repositorio | nuxt/nuxt | 2000 | 16,6% | 43,0% | **72,5%** | 67,6% | 67,0% | 65,8% |
| repositorio | sveltejs/svelte | 2000 | 21,1% | 44,4% | 56,7% | 56,8% | **57,0%** | 52,7% |
| repositorio | vitejs/vite | 2000 | 17,4% | 40,5% | 70,2% | **73,1%** | 71,0% | 67,6% |
| repositorio | vitest-dev/vitest | 2000 | 17,5% | 39,1% | 68,0% | **68,3%** | 67,9% | 62,7% |
| temporal | temporal | 2001 | 18,4% | 42,4% | 71,6% | 73,3% | **74,0%** | 70,1% |

## Partición aleatoria

80/20 estratificada por clase, con una división distinta por semilla. **Fuga información**: commits del mismo repositorio quedan a los dos lados.

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `trivial` | 55,2% | 17,8% | 71,2% | 0,0% | 0,0% |
| `regla_docs` | 71,1% [70,6%, 71,7%] | 41,4% [40,9%, 41,9%] | 79,2% [78,9%, 79,5%] | 0,0% | 86,5% [84,9%, 88,2%] |
| `clasico_lr` | 82,8% [82,0%, 83,5%] | 74,5% [73,1%, 75,8%] | 87,4% [86,7%, 88,1%] | 61,1% [59,2%, 63,0%] | 92,4% [91,7%, 93,2%] |
| `clasico_lr_balanceado` | 80,0% [78,8%, 81,3%] | 74,7% [73,4%, 75,9%] | 84,7% [83,4%, 85,9%] | 62,7% [60,2%, 65,2%] | 92,7% [91,7%, 93,7%] |
| `f4_codebert` | 77,7% [76,3%, 79,1%] | 72,7% [71,5%, 73,9%] | 82,5% [81,2%, 83,8%] | 61,0% [59,9%, 62,0%] | 94,6% [93,6%, 95,5%] |
| `f5_desde_cero` | 74,8% [73,1%, 76,5%] | 69,3% [67,7%, 71,0%] | 79,8% [77,8%, 81,8%] | 54,6% [52,7%, 56,5%] | 93,2% [92,9%, 93,4%] |

## Partición por repositorio — la principal

Un fold por repo, con ese repo entero en prueba. Es la que responde si esto sirve en un proyecto que el modelo nunca vio.

### Fold `angular/angular-cli` en prueba — n = 2000

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `trivial` | 46,2% | 15,8% | 63,1% | 0,0% | 0,0% |
| `regla_docs` | 57,4% | 39,2% | 68,4% | 0,0% | 88,4% |
| `clasico_lr` | 65,8% | 59,2% | 73,6% | 43,4% | 91,1% |
| `clasico_lr_balanceado` | 70,3% | 68,9% | 76,0% | 52,2% | 91,8% |
| `f4_codebert` | 68,9% [66,7%, 71,1%] | 68,1% [65,5%, 70,7%] | 74,7% [72,7%, 76,6%] | 53,2% [51,6%, 54,9%] | 90,3% [89,5%, 91,1%] |
| `f5_desde_cero` | 63,7% [60,7%, 66,8%] | 60,0% [54,4%, 65,6%] | 72,3% [70,5%, 74,0%] | 42,1% [33,1%, 51,1%] | 86,1% [84,8%, 87,5%] |

### Fold `nuxt/nuxt` en prueba — n = 2000

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `trivial` | 49,9% | 16,6% | 66,5% | 0,0% | 0,0% |
| `regla_docs` | 76,4% | 43,0% | 80,9% | 0,0% | 91,0% |
| `clasico_lr` | 85,4% | 72,5% | 88,2% | 65,8% | 95,3% |
| `clasico_lr_balanceado` | 77,3% | 67,6% | 79,0% | 59,8% | 95,2% |
| `f4_codebert` | 75,5% [72,3%, 78,8%] | 67,0% [64,7%, 69,3%] | 75,4% [70,6%, 80,3%] | 60,0% [59,5%, 60,6%] | 96,0% [95,6%, 96,3%] |
| `f5_desde_cero` | 78,2% [76,3%, 80,1%] | 65,8% [64,9%, 66,8%] | 80,9% [78,3%, 83,5%] | 55,3% [52,8%, 57,8%] | 96,1% [95,7%, 96,6%] |

### Fold `sveltejs/svelte` en prueba — n = 2000

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `trivial` | 73,0% | 21,1% | 84,4% | 0,0% | 0,0% |
| `regla_docs` | 85,5% | 44,4% | 91,0% | 0,0% | 86,7% |
| `clasico_lr` | 87,0% | 56,7% | 92,7% | 45,3% | 88,8% |
| `clasico_lr_balanceado` | 82,0% | 56,8% | 89,6% | 45,8% | 90,3% |
| `f4_codebert` | 80,9% [79,6%, 82,2%] | 57,0% [55,9%, 58,2%] | 87,6% [86,6%, 88,6%] | 50,0% [48,7%, 51,2%] | 88,4% [87,7%, 89,2%] |
| `f5_desde_cero` | 79,6% [78,3%, 81,0%] | 52,7% [52,1%, 53,4%] | 87,1% [85,8%, 88,4%] | 38,8% [34,8%, 42,8%] | 85,0% [83,0%, 87,0%] |

### Fold `vitejs/vite` en prueba — n = 2000

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `trivial` | 53,3% | 17,4% | 69,6% | 0,0% | 0,0% |
| `regla_docs` | 69,1% | 40,5% | 77,5% | 0,0% | 84,6% |
| `clasico_lr` | 81,3% | 70,2% | 86,2% | 52,9% | 93,7% |
| `clasico_lr_balanceado` | 79,1% | 73,1% | 83,3% | 58,2% | 91,6% |
| `f4_codebert` | 77,8% [76,5%, 79,1%] | 71,0% [70,3%, 71,8%] | 82,6% [81,1%, 84,1%] | 57,2% [54,3%, 60,1%] | 96,1% [95,2%, 96,9%] |
| `f5_desde_cero` | 75,4% [72,8%, 77,9%] | 67,6% [65,5%, 69,7%] | 80,3% [77,5%, 83,2%] | 51,3% [47,8%, 54,7%] | 94,0% [93,3%, 94,6%] |

### Fold `vitest-dev/vitest` en prueba — n = 2000

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `trivial` | 53,7% | 17,5% | 69,9% | 0,0% | 0,0% |
| `regla_docs` | 67,4% | 39,1% | 76,7% | 0,0% | 79,7% |
| `clasico_lr` | 79,8% | 68,0% | 84,9% | 64,5% | 90,7% |
| `clasico_lr_balanceado` | 74,6% | 68,3% | 78,5% | 63,2% | 91,1% |
| `f4_codebert` | 73,5% [71,7%, 75,2%] | 67,9% [66,4%, 69,4%] | 77,0% [75,2%, 78,8%] | 64,0% [62,8%, 65,1%] | 94,0% [93,2%, 94,8%] |
| `f5_desde_cero` | 70,8% [68,9%, 72,6%] | 62,7% [60,9%, 64,5%] | 73,8% [71,0%, 76,6%] | 58,8% [56,5%, 61,1%] | 92,7% [91,9%, 93,5%] |

## Partición temporal

Corte global el 2025-06-01: entrena con lo anterior y evalúa con lo posterior, 7.999 / 2.001.

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `trivial` | 58,4% | 18,4% | 73,8% | 0,0% | 0,0% |
| `regla_docs` | 74,5% | 42,4% | 82,0% | 0,0% | 87,5% |
| `clasico_lr` | 83,4% | 71,6% | 88,8% | 60,0% | 93,7% |
| `clasico_lr_balanceado` | 80,2% | 73,3% | 85,9% | 56,5% | 92,9% |
| `f4_codebert` | 79,8% [78,2%, 81,4%] | 74,0% [72,5%, 75,4%] | 84,5% [82,9%, 86,0%] | 60,4% [58,0%, 62,8%] | 95,5% [94,8%, 96,1%] |
| `f5_desde_cero` | 76,5% [75,5%, 77,5%] | 70,1% [69,3%, 70,9%] | 81,9% [80,8%, 82,9%] | 51,7% [49,4%, 54,0%] | 94,6% [93,9%, 95,2%] |

## `refactor`, fold por fold

DESIGN.md §5: `refactor` es el 8,2% del dataset, angular-cli aporta el 57% y svelte 1 solo ejemplo. Un F1 calculado sobre un puñado de casos no es una métrica, así que va con el n al lado y **no hay fila de promedio entre folds**.

### Partición aleatoria

| fold | n `refactor` en prueba | `trivial` | `regla_docs` | `clasico_lr` | `clasico_lr_balanceado` | `f4_codebert` | `f5_desde_cero` |
|---|---:|---:|---:|---:|---:|---:|---:|
| aleatoria | 164 | 0,0% | 0,0% | 56,8% [53,6%, 60,1%] | 58,5% [55,9%, 61,2%] | 52,8% [50,2%, 55,4%] | 49,9% [45,2%, 54,5%] |

### Partición repositorio

| fold | n `refactor` en prueba | `trivial` | `regla_docs` | `clasico_lr` | `clasico_lr_balanceado` | `f4_codebert` | `f5_desde_cero` |
|---|---:|---:|---:|---:|---:|---:|---:|
| angular/angular-cli | 468 | 0,0% | 0,0% | 28,6% | 55,4% | 54,3% [46,8%, 61,8%] | 39,5% [27,0%, 52,0%] |
| nuxt/nuxt | 102 | 0,0% | 0,0% | 40,7% | 36,6% | 36,4% [32,4%, 40,5%] | 31,1% [27,8%, 34,3%] |
| sveltejs/svelte | 1 | 0,0% | 0,0% | 0,0% | 1,4% | 2,2% [-0,4%, 4,7%] | 0,0% |
| vitejs/vite | 151 | 0,0% | 0,0% | 48,1% | 59,4% | 48,3% [45,3%, 51,3%] | 44,9% [39,5%, 50,4%] |
| vitest-dev/vitest | 98 | 0,0% | 0,0% | 31,8% | 40,5% | 36,6% [33,5%, 39,7%] | 25,4% [18,3%, 32,4%] |

### Partición temporal

| fold | n `refactor` en prueba | `trivial` | `regla_docs` | `clasico_lr` | `clasico_lr_balanceado` | `f4_codebert` | `f5_desde_cero` |
|---|---:|---:|---:|---:|---:|---:|---:|
| temporal | 176 | 0,0% | 0,0% | 44,0% | 58,0% | 55,5% [53,8%, 57,2%] | 52,3% [51,3%, 53,3%] |

## Cuánto infla la partición aleatoria

Es el punto 1 de DESIGN.md §11. La partición aleatoria reparte commits del mismo repositorio a los dos lados y el modelo memoriza el proyecto. La columna del medio es el **peor fold** de la partición por repositorio, no el promedio: es el que dice qué pasa en el proyecto más distinto de los que vio.

| modelo | F1 macro, aleatoria | F1 macro, por repositorio (peor fold) | caída |
|---|---:|---:|---:|
| `trivial` | 17,8% | 15,8% (angular/angular-cli) | -2,0 |
| `regla_docs` | 41,4% | 39,1% (vitest-dev/vitest) | -2,3 |
| `clasico_lr` | 74,5% | 56,7% (sveltejs/svelte) | -17,8 |
| `clasico_lr_balanceado` | 74,7% | 56,8% (sveltejs/svelte) | -17,9 |
| `f4_codebert` | 72,7% | 57,0% (sveltejs/svelte) | -15,7 |
| `f5_desde_cero` | 69,3% | 52,7% (sveltejs/svelte) | -16,6 |

## La prueba de etiquetas aleatorias, en los tres modelos

`LEAKAGE.md` §7.1: con las etiquetas de entrenamiento barajadas, la exactitud no puede pasar la tasa de la clase mayoritaria de prueba por más de +2,0 puntos. Cada modelo nuevo es un camino nuevo por el que la etiqueta podría colarse, así que se corre para cada uno. El detalle por fold está en `docs/F2_BASELINES.md`, `docs/F4_TRANSFER.md` y `docs/F5_DESDE_CERO.md`.

| modelo | partición | folds | pasan | fallan | no concluyentes |
|---|---|---:|---:|---:|---:|
| `clasico_lr` | aleatoria | 1 | 1 | 0 | 0 |
| `clasico_lr` | repositorio | 5 | 5 | 0 | 0 |
| `clasico_lr` | temporal | 1 | 1 | 0 | 0 |
| `f4_codebert` | aleatoria | 1 | 1 | 0 | 0 |
| `f4_codebert` | repositorio | 5 | 5 | 0 | 0 |
| `f4_codebert` | temporal | 1 | 1 | 0 | 0 |
| `f5_desde_cero` | aleatoria | 1 | 1 | 0 | 0 |
| `f5_desde_cero` | repositorio | 5 | 5 | 0 | 0 |
| `f5_desde_cero` | temporal | 1 | 1 | 0 | 0 |

## Matrices de confusión — `clasico_lr_balanceado`, partición por repositorio

Fila: etiqueta verdadera. Columna: predicción. Primera semilla de cada fold.

**angular/angular-cli**

| verdad \ predicción | `fix` | `feat` | `refactor` | `docs` |
|---|---:|---:|---:|---:|
| `fix` | 775 | 90 | 54 | 4 |
| `feat` | 123 | 170 | 31 | 3 |
| `refactor` | 190 | 62 | 213 | 3 |
| `docs` | 29 | 2 | 3 | 248 |

**nuxt/nuxt**

| verdad \ predicción | `fix` | `feat` | `refactor` | `docs` |
|---|---:|---:|---:|---:|
| `fix` | 688 | 159 | 138 | 12 |
| `feat` | 34 | 199 | 24 | 8 |
| `refactor` | 10 | 27 | 61 | 4 |
| `docs` | 13 | 16 | 8 | 599 |

**sveltejs/svelte**

| verdad \ predicción | `fix` | `feat` | `refactor` | `docs` |
|---|---:|---:|---:|---:|
| `fix` | 1256 | 103 | 85 | 17 |
| `feat` | 62 | 96 | 47 | 4 |
| `refactor` | 0 | 0 | 1 | 0 |
| `docs` | 24 | 11 | 6 | 288 |

**vitejs/vite**

| verdad \ predicción | `fix` | `feat` | `refactor` | `docs` |
|---|---:|---:|---:|---:|
| `fix` | 882 | 80 | 69 | 36 |
| `feat` | 128 | 187 | 19 | 17 |
| `refactor` | 28 | 18 | 101 | 4 |
| `docs` | 12 | 7 | 0 | 412 |

**vitest-dev/vitest**

| verdad \ predicción | `fix` | `feat` | `refactor` | `docs` |
|---|---:|---:|---:|---:|
| `fix` | 758 | 204 | 94 | 18 |
| `feat` | 67 | 306 | 35 | 6 |
| `refactor` | 20 | 17 | 60 | 1 |
| `docs` | 11 | 27 | 9 | 367 |

## Matrices de confusión — `f4_codebert`, partición por repositorio

Fila: etiqueta verdadera. Columna: predicción. Primera semilla de cada fold.

**angular/angular-cli**

| verdad \ predicción | `fix` | `feat` | `refactor` | `docs` |
|---|---:|---:|---:|---:|
| `fix` | 728 | 116 | 72 | 7 |
| `feat` | 84 | 191 | 52 | 0 |
| `refactor` | 151 | 58 | 255 | 4 |
| `docs` | 20 | 11 | 11 | 240 |

**nuxt/nuxt**

| verdad \ predicción | `fix` | `feat` | `refactor` | `docs` |
|---|---:|---:|---:|---:|
| `fix` | 657 | 152 | 181 | 7 |
| `feat` | 27 | 192 | 33 | 13 |
| `refactor` | 11 | 12 | 76 | 3 |
| `docs` | 8 | 14 | 3 | 611 |

**sveltejs/svelte**

| verdad \ predicción | `fix` | `feat` | `refactor` | `docs` |
|---|---:|---:|---:|---:|
| `fix` | 1177 | 221 | 34 | 29 |
| `feat` | 37 | 149 | 8 | 15 |
| `refactor` | 0 | 0 | 1 | 0 |
| `docs` | 10 | 18 | 3 | 298 |

**vitejs/vite**

| verdad \ predicción | `fix` | `feat` | `refactor` | `docs` |
|---|---:|---:|---:|---:|
| `fix` | 864 | 119 | 70 | 14 |
| `feat` | 101 | 203 | 40 | 7 |
| `refactor` | 32 | 31 | 87 | 1 |
| `docs` | 11 | 4 | 0 | 416 |

**vitest-dev/vitest**

| verdad \ predicción | `fix` | `feat` | `refactor` | `docs` |
|---|---:|---:|---:|---:|
| `fix` | 736 | 212 | 115 | 11 |
| `feat` | 48 | 308 | 55 | 3 |
| `refactor` | 13 | 18 | 65 | 2 |
| `docs` | 7 | 23 | 4 | 380 |

## Matrices de confusión — `f5_desde_cero`, partición por repositorio

Fila: etiqueta verdadera. Columna: predicción. Primera semilla de cada fold.

**angular/angular-cli**

| verdad \ predicción | `fix` | `feat` | `refactor` | `docs` |
|---|---:|---:|---:|---:|
| `fix` | 780 | 63 | 60 | 20 |
| `feat` | 184 | 104 | 34 | 5 |
| `refactor` | 280 | 75 | 110 | 3 |
| `docs` | 28 | 9 | 2 | 243 |

**nuxt/nuxt**

| verdad \ predicción | `fix` | `feat` | `refactor` | `docs` |
|---|---:|---:|---:|---:|
| `fix` | 734 | 136 | 119 | 8 |
| `feat` | 48 | 181 | 26 | 10 |
| `refactor` | 18 | 33 | 49 | 2 |
| `docs` | 15 | 15 | 1 | 605 |

**sveltejs/svelte**

| verdad \ predicción | `fix` | `feat` | `refactor` | `docs` |
|---|---:|---:|---:|---:|
| `fix` | 1202 | 154 | 43 | 62 |
| `feat` | 83 | 100 | 8 | 18 |
| `refactor` | 1 | 0 | 0 | 0 |
| `docs` | 17 | 24 | 2 | 286 |

**vitejs/vite**

| verdad \ predicción | `fix` | `feat` | `refactor` | `docs` |
|---|---:|---:|---:|---:|
| `fix` | 820 | 166 | 48 | 33 |
| `feat` | 144 | 176 | 20 | 11 |
| `refactor` | 36 | 51 | 62 | 2 |
| `docs` | 11 | 2 | 0 | 418 |

**vitest-dev/vitest**

| verdad \ predicción | `fix` | `feat` | `refactor` | `docs` |
|---|---:|---:|---:|---:|
| `fix` | 695 | 292 | 71 | 16 |
| `feat` | 64 | 317 | 22 | 11 |
| `refactor` | 23 | 48 | 24 | 3 |
| `docs` | 10 | 21 | 1 | 382 |

## El techo humano

DESIGN.md §11 pide poner el techo humano al lado de los números del modelo. **Hoy no hay techo humano:** la F3 está hecha de forma provisional con un anotador LLM (`docs/F3_TECHO_LLM.md`), y ese número no es comparable con el de una persona. Cuando alguien etiquete la muestra a mano (`python -m ccls f3 label`), el techo humano irá en `docs/F3_TECHO_HUMANO.md` y aquí se enlaza.

## Cómo se reproduce cada tabla

`python -m ccls reproducir` corre el pipeline en orden y regenera todos los reportes; `--plan` solo lo muestra. Las tablas de este documento salen de `resultados/*.json` con `python -m ccls results`. Los comandos que produjeron cada modelo están en la tabla de arriba y en `README.md`.
