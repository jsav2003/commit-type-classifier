# F5 · Red desde cero

Generado por `python -m ccls f5 report`. **No se edita a mano.** El diseño de la fase está en `DESIGN.md` §6.4; cómo se leen los números, en §7.3 y §7.4. Cómo se corrió, en `docs/KAGGLE_F5.md`.

- `f5_desde_cero`: la arquitectura de CodeBERT (`microsoft/codebert-base`) con los pesos al azar, entrenada entera y con la pérdida ponderada por clase.
- `f4_codebert`: la misma arquitectura con los pesos preentrenados y las últimas capas reentrenadas (`docs/F4_TRANSFER.md`). F4 − F5 mide lo que aporta el preentrenamiento.
- `clasico_lr_balanceado`: el clásico de referencia de la F2 (`docs/F2_BASELINES.md`), también reponderado.
- Semillas: 1, 2, 3, 4, 5. Cada celda es la media entre semillas con su intervalo t al 95%; el clásico es determinista en las particiones por repositorio y temporal, y ahí su intervalo tiene ancho cero y se omite.
- Una celda `—` es una clase sin ejemplos en prueba: la F1 no existe, y no vale 0.
- Dataset: `manifest_sha256` `0177140ce63d03f1fa1aa38f7cde6bdc6ef57f3442b0cc8cf4278e2d7b7249a5`.

## `f5_desde_cero` contra `clasico_lr_balanceado`, fold por fold

F1 macro. El veredicto compara la media del clásico con el intervalo de `f5_desde_cero` entre semillas (ver `comparar` en `src/ccls/f4.py`). Ese intervalo solo mide el ruido del entrenamiento, no el de la muestra de prueba, así que "empate" es "la diferencia no pasa ese ruido", no "son iguales".

| partición | fold | n | `f5_desde_cero` | `clasico_lr_balanceado` | diferencia | veredicto |
|---|---|---:|---:|---:|---:|---|
| aleatoria | aleatoria | 1999 | 69,3% [67,7%, 71,0%] | 74,7% [73,4%, 75,9%] | -5,3 | pierde |
| repositorio | angular/angular-cli | 2000 | 60,0% [54,4%, 65,6%] | 68,9% | -8,9 | pierde |
| repositorio | nuxt/nuxt | 2000 | 65,8% [64,9%, 66,8%] | 67,6% | -1,8 | pierde |
| repositorio | sveltejs/svelte | 2000 | 52,7% [52,1%, 53,4%] | 56,8% | -4,1 | pierde |
| repositorio | vitejs/vite | 2000 | 67,6% [65,5%, 69,7%] | 73,1% | -5,5 | pierde |
| repositorio | vitest-dev/vitest | 2000 | 62,7% [60,9%, 64,5%] | 68,3% | -5,7 | pierde |
| temporal | temporal | 2001 | 70,1% [69,3%, 70,9%] | 73,3% | -3,2 | pierde |

**En los 6 folds honestos (por repositorio y temporal): 0 gana, 0 empata, 6 pierde.** La aleatoria no cuenta: fuga información entre entrenamiento y prueba (DESIGN.md §5).

## `f5_desde_cero` contra `f4_codebert`, fold por fold

F1 macro. El veredicto compara la media de CodeBERT con el intervalo de `f5_desde_cero` entre semillas (ver `comparar` en `src/ccls/f4.py`). Ese intervalo solo mide el ruido del entrenamiento, no el de la muestra de prueba, así que "empate" es "la diferencia no pasa ese ruido", no "son iguales".

| partición | fold | n | `f5_desde_cero` | `f4_codebert` | diferencia | veredicto |
|---|---|---:|---:|---:|---:|---|
| aleatoria | aleatoria | 1999 | 69,3% [67,7%, 71,0%] | 72,7% [71,5%, 73,9%] | -3,3 | pierde |
| repositorio | angular/angular-cli | 2000 | 60,0% [54,4%, 65,6%] | 68,1% [65,5%, 70,7%] | -8,1 | pierde |
| repositorio | nuxt/nuxt | 2000 | 65,8% [64,9%, 66,8%] | 67,0% [64,7%, 69,3%] | -1,1 | pierde |
| repositorio | sveltejs/svelte | 2000 | 52,7% [52,1%, 53,4%] | 57,0% [55,9%, 58,2%] | -4,3 | pierde |
| repositorio | vitejs/vite | 2000 | 67,6% [65,5%, 69,7%] | 71,0% [70,3%, 71,8%] | -3,4 | pierde |
| repositorio | vitest-dev/vitest | 2000 | 62,7% [60,9%, 64,5%] | 67,9% [66,4%, 69,4%] | -5,2 | pierde |
| temporal | temporal | 2001 | 70,1% [69,3%, 70,9%] | 74,0% [72,5%, 75,4%] | -3,8 | pierde |

**En los 6 folds honestos (por repositorio y temporal): 0 gana, 0 empata, 6 pierde.** La aleatoria no cuenta: fuga información entre entrenamiento y prueba (DESIGN.md §5).

## Qué clase gana y cuál pierde, contra `clasico_lr_balanceado`

Diferencia de F1, `f5_desde_cero` menos `clasico_lr_balanceado`, en puntos. `—`: la clase no tiene ejemplos en prueba. La columna de `refactor` lleva su n al lado (§5).

| partición | fold | `fix` | `feat` | `docs` | `refactor` |
|---|---|---:|---:|---:|---:|
| aleatoria | aleatoria | -4,9 | -8,1 | +0,5 | -8,7 (n = 164) |
| repositorio | angular/angular-cli | -3,7 | -10,2 | -5,7 | -15,9 (n = 468) |
| repositorio | nuxt/nuxt | +1,9 | -4,5 | +1,0 | -5,5 (n = 102) |
| repositorio | sveltejs/svelte | -2,5 | -7,0 | -5,3 | -1,4 (n = 1) |
| repositorio | vitejs/vite | -3,0 | -6,9 | +2,4 | -14,5 (n = 151) |
| repositorio | vitest-dev/vitest | -4,7 | -4,4 | +1,6 | -15,2 (n = 98) |
| temporal | temporal | -4,0 | -4,7 | +1,7 | -5,7 (n = 176) |

## Qué clase gana y cuál pierde, contra `f4_codebert`

Diferencia de F1, `f5_desde_cero` menos `f4_codebert`, en puntos. `—`: la clase no tiene ejemplos en prueba. La columna de `refactor` lleva su n al lado (§5).

| partición | fold | `fix` | `feat` | `docs` | `refactor` |
|---|---|---:|---:|---:|---:|
| aleatoria | aleatoria | -2,7 | -6,4 | -1,4 | -2,9 (n = 164) |
| repositorio | angular/angular-cli | -2,4 | -11,2 | -4,2 | -14,8 (n = 468) |
| repositorio | nuxt/nuxt | +5,5 | -4,8 | +0,2 | -5,4 (n = 102) |
| repositorio | sveltejs/svelte | -0,5 | -11,2 | -3,4 | -2,2 (n = 1) |
| repositorio | vitejs/vite | -2,3 | -6,0 | -2,1 | -3,4 (n = 151) |
| repositorio | vitest-dev/vitest | -3,2 | -5,2 | -1,3 | -11,2 (n = 98) |
| temporal | temporal | -2,6 | -8,7 | -0,9 | -3,2 (n = 176) |

## Partición aleatoria

80/20 estratificada por clase, con una división distinta por semilla. **Fuga información**: commits del mismo repositorio quedan a los dos lados.

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `f5_desde_cero` | 74,8% [73,1%, 76,5%] | 69,3% [67,7%, 71,0%] | 79,8% [77,8%, 81,8%] | 54,6% [52,7%, 56,5%] | 93,2% [92,9%, 93,4%] |
| `f4_codebert` | 77,7% [76,3%, 79,1%] | 72,7% [71,5%, 73,9%] | 82,5% [81,2%, 83,8%] | 61,0% [59,9%, 62,0%] | 94,6% [93,6%, 95,5%] |
| `clasico_lr_balanceado` | 80,0% [78,8%, 81,3%] | 74,7% [73,4%, 75,9%] | 84,7% [83,4%, 85,9%] | 62,7% [60,2%, 65,2%] | 92,7% [91,7%, 93,7%] |

## Partición por repositorio — la principal

Un fold por repo, con ese repo entero en prueba.

### Fold `angular/angular-cli` en prueba — n = 2000

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `f5_desde_cero` | 63,7% [60,7%, 66,8%] | 60,0% [54,4%, 65,6%] | 72,3% [70,5%, 74,0%] | 42,1% [33,1%, 51,1%] | 86,1% [84,8%, 87,5%] |
| `f4_codebert` | 68,9% [66,7%, 71,1%] | 68,1% [65,5%, 70,7%] | 74,7% [72,7%, 76,6%] | 53,2% [51,6%, 54,9%] | 90,3% [89,5%, 91,1%] |
| `clasico_lr_balanceado` | 70,3% | 68,9% | 76,0% | 52,2% | 91,8% |

### Fold `nuxt/nuxt` en prueba — n = 2000

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `f5_desde_cero` | 78,2% [76,3%, 80,1%] | 65,8% [64,9%, 66,8%] | 80,9% [78,3%, 83,5%] | 55,3% [52,8%, 57,8%] | 96,1% [95,7%, 96,6%] |
| `f4_codebert` | 75,5% [72,3%, 78,8%] | 67,0% [64,7%, 69,3%] | 75,4% [70,6%, 80,3%] | 60,0% [59,5%, 60,6%] | 96,0% [95,6%, 96,3%] |
| `clasico_lr_balanceado` | 77,3% | 67,6% | 79,0% | 59,8% | 95,2% |

### Fold `sveltejs/svelte` en prueba — n = 2000

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `f5_desde_cero` | 79,6% [78,3%, 81,0%] | 52,7% [52,1%, 53,4%] | 87,1% [85,8%, 88,4%] | 38,8% [34,8%, 42,8%] | 85,0% [83,0%, 87,0%] |
| `f4_codebert` | 80,9% [79,6%, 82,2%] | 57,0% [55,9%, 58,2%] | 87,6% [86,6%, 88,6%] | 50,0% [48,7%, 51,2%] | 88,4% [87,7%, 89,2%] |
| `clasico_lr_balanceado` | 82,0% | 56,8% | 89,6% | 45,8% | 90,3% |

### Fold `vitejs/vite` en prueba — n = 2000

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `f5_desde_cero` | 75,4% [72,8%, 77,9%] | 67,6% [65,5%, 69,7%] | 80,3% [77,5%, 83,2%] | 51,3% [47,8%, 54,7%] | 94,0% [93,3%, 94,6%] |
| `f4_codebert` | 77,8% [76,5%, 79,1%] | 71,0% [70,3%, 71,8%] | 82,6% [81,1%, 84,1%] | 57,2% [54,3%, 60,1%] | 96,1% [95,2%, 96,9%] |
| `clasico_lr_balanceado` | 79,1% | 73,1% | 83,3% | 58,2% | 91,6% |

### Fold `vitest-dev/vitest` en prueba — n = 2000

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `f5_desde_cero` | 70,8% [68,9%, 72,6%] | 62,7% [60,9%, 64,5%] | 73,8% [71,0%, 76,6%] | 58,8% [56,5%, 61,1%] | 92,7% [91,9%, 93,5%] |
| `f4_codebert` | 73,5% [71,7%, 75,2%] | 67,9% [66,4%, 69,4%] | 77,0% [75,2%, 78,8%] | 64,0% [62,8%, 65,1%] | 94,0% [93,2%, 94,8%] |
| `clasico_lr_balanceado` | 74,6% | 68,3% | 78,5% | 63,2% | 91,1% |

## Partición temporal

Corte global el 2025-06-01: entrena con lo anterior y evalúa con lo posterior, 7.999 / 2.001.

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `f5_desde_cero` | 76,5% [75,5%, 77,5%] | 70,1% [69,3%, 70,9%] | 81,9% [80,8%, 82,9%] | 51,7% [49,4%, 54,0%] | 94,6% [93,9%, 95,2%] |
| `f4_codebert` | 79,8% [78,2%, 81,4%] | 74,0% [72,5%, 75,4%] | 84,5% [82,9%, 86,0%] | 60,4% [58,0%, 62,8%] | 95,5% [94,8%, 96,1%] |
| `clasico_lr_balanceado` | 80,2% | 73,3% | 85,9% | 56,5% | 92,9% |

## `refactor`, fold por fold

DESIGN.md §5: `refactor` es el 8,2% del dataset, angular-cli aporta el 57% y svelte 1 solo ejemplo. Un F1 calculado sobre un puñado de casos no es una métrica, así que va con el n al lado y **no hay fila de promedio entre folds**.

### Partición aleatoria

| fold | n `refactor` en prueba | `f5_desde_cero` | `f4_codebert` | `clasico_lr_balanceado` |
|---|---:|---:|---:|---:|
| aleatoria | 164 | 49,9% [45,2%, 54,5%] | 52,8% [50,2%, 55,4%] | 58,5% [55,9%, 61,2%] |

### Partición repositorio

| fold | n `refactor` en prueba | `f5_desde_cero` | `f4_codebert` | `clasico_lr_balanceado` |
|---|---:|---:|---:|---:|
| angular/angular-cli | 468 | 39,5% [27,0%, 52,0%] | 54,3% [46,8%, 61,8%] | 55,4% |
| nuxt/nuxt | 102 | 31,1% [27,8%, 34,3%] | 36,4% [32,4%, 40,5%] | 36,6% |
| sveltejs/svelte | 1 | 0,0% | 2,2% [-0,4%, 4,7%] | 1,4% |
| vitejs/vite | 151 | 44,9% [39,5%, 50,4%] | 48,3% [45,3%, 51,3%] | 59,4% |
| vitest-dev/vitest | 98 | 25,4% [18,3%, 32,4%] | 36,6% [33,5%, 39,7%] | 40,5% |

### Partición temporal

| fold | n `refactor` en prueba | `f5_desde_cero` | `f4_codebert` | `clasico_lr_balanceado` |
|---|---:|---:|---:|---:|
| temporal | 176 | 52,3% [51,3%, 53,3%] | 55,5% [53,8%, 57,2%] | 58,0% |

## Cuánto infla la partición aleatoria

Es el punto 1 de DESIGN.md §11. La partición aleatoria reparte commits del mismo repositorio a los dos lados y el modelo memoriza el proyecto. La columna del medio es el **peor fold** de la partición por repositorio, no el promedio: es el que dice qué pasa en el proyecto más distinto de los que vio.

| modelo | F1 macro, aleatoria | F1 macro, por repositorio (peor fold) | caída |
|---|---:|---:|---:|
| `f5_desde_cero` | 69,3% | 52,7% (sveltejs/svelte) | -16,6 |
| `f4_codebert` | 72,7% | 57,0% (sveltejs/svelte) | -15,7 |
| `clasico_lr_balanceado` | 74,7% | 56,8% (sveltejs/svelte) | -17,9 |

## La prueba de etiquetas aleatorias, sobre `f5_desde_cero`

`LEAKAGE.md` §7.1: con las etiquetas de entrenamiento barajadas, la exactitud no puede pasar la tasa de la clase mayoritaria de prueba por más de +2,0 puntos. La red parte de pesos al azar y ve las rutas completas de los archivos: es un camino por el que la etiqueta podría colarse, y se prueba igual.

| partición | fold | techo del azar | exactitud, etiquetas barajadas | exceso | estado |
|---|---|---:|---:|---:|---|
| aleatoria | aleatoria | 55,2% | 31,7% [5,1%, 58,4%] | -23,5 | pasa |
| repositorio | angular/angular-cli | 46,2% | 21,0% [3,4%, 38,5%] | -25,2 | pasa |
| repositorio | nuxt/nuxt | 49,9% | 46,2% [36,2%, 56,3%] | -3,6 | pasa |
| repositorio | sveltejs/svelte | 73,0% | 38,7% [-0,2%, 77,6%] | -34,4 | pasa |
| repositorio | vitejs/vite | 53,3% | 39,8% [16,8%, 62,9%] | -13,5 | pasa |
| repositorio | vitest-dev/vitest | 53,7% | 30,7% [3,5%, 58,0%] | -23,0 | pasa |
| temporal | temporal | 58,4% | 43,3% [17,6%, 69,0%] | -15,1 | pasa |

7 folds: 7 pasan, 0 fallan, 0 no concluyentes.

Con etiquetas barajadas la exactitud varía mucho de una semilla a otra y el intervalo sale ancho; algunos intervalos llegan a tocar el techo. El criterio de §7.1 se fijó sobre la media, no sobre el extremo del intervalo, y no se cambia ahora.

## Cuántas corridas responden siempre lo mismo

Una corrida (una semilla en un fold) cuenta como colapsada si al menos el 90% de sus predicciones cae en una sola clase. El umbral es una elección de este reporte para describir, no un criterio de la prueba de fuga.

| partición | corridas, etiquetas reales | corridas, etiquetas barajadas |
|---|---:|---:|
| aleatoria | 0 de 5 | 4 de 5 |
| repositorio | 0 de 25 | 24 de 25 |
| temporal | 0 de 5 | 5 de 5 |

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

## Montaje

`config/f5.yaml` es `config/f4.yaml` con una sola diferencia: la red se entrena entera (`capas_entrenables: null`), porque congelar capas con pesos al azar sería dejar ruido fijo en medio de la red. Fijada el 2026-09-22 **antes** de entrenar. El tokenizador es el de CodeBERT: la F5 hereda su vocabulario, no sus pesos.

**No es la mejor red desde cero posible.** Una red al azar suele pedir más épocas y otra tasa de aprendizaje, pero buscarlas obligaría a elegir mirando los folds de prueba (no hay conjunto de validación) y a cambiar dos cosas a la vez. Con este presupuesto la comparación es limpia; con otro, el resultado de la F5 podría ser mejor. DESIGN.md §6.4.

| parámetro | valor |
|---|---|
| `modelo_base` | `microsoft/codebert-base` |
| `revision` | `3b0952feddeffad0063f274080e3c23d75e7eb39` |
| `capas_entrenables` | `None` |
| `max_longitud` | `256` |
| `epocas` | `3` |
| `tamano_lote` | `32` |
| `tasa_aprendizaje` | `5e-05` |
| `decaimiento_pesos` | `0.01` |
| `calentamiento` | `0.1` |
| `pesos_por_clase` | `balanceados` |
| `max_archivos_en_texto` | `25` |

Versiones con que se corrió: python 3.12.13, numpy 2.2.1, scikit-learn 1.6.1, torch 2.10.0+cu128, transformers 4.57.6, cuda 12.8, plataforma Linux-6.12.90+-x86_64-with-glibc2.35.

En GPU los ajustes no son bit a bit reproducibles aunque se fije la semilla; para eso están las cinco semillas.
