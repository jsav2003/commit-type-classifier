# F4 · Transfer learning

Generado por `python -m ccls f4 report`. **No se edita a mano.** El diseño de la fase está en `DESIGN.md` §6.3; cómo se leen los números, en §7.3 y §7.4. Cómo se corrió, en `docs/COLAB_F4.md`.

- `f4_codebert`: CodeBERT (`microsoft/codebert-base`) con las últimas capas reentrenadas y la pérdida ponderada por clase.
- `clasico_lr_balanceado`: el clásico de referencia de la F2 (`docs/F2_BASELINES.md`), también reponderado. La comparación es reponderado contra reponderado.
- Semillas: 1, 2, 3, 4, 5. Cada celda es la media entre semillas con su intervalo t al 95%; el clásico es determinista en las particiones por repositorio y temporal, y ahí su intervalo tiene ancho cero y se omite.
- Una celda `—` es una clase sin ejemplos en prueba: la F1 no existe, y no vale 0.
- Dataset: `manifest_sha256` `0177140ce63d03f1fa1aa38f7cde6bdc6ef57f3442b0cc8cf4278e2d7b7249a5`.

## `f4_codebert` contra `clasico_lr_balanceado`, fold por fold

F1 macro. El veredicto compara la media del clásico con el intervalo de `f4_codebert` entre semillas (ver `comparar` en `src/ccls/f4.py`). Ese intervalo solo mide el ruido del entrenamiento, no el de la muestra de prueba, así que "empate" es "la diferencia no pasa ese ruido", no "son iguales".

| partición | fold | n | `f4_codebert` | `clasico_lr_balanceado` | diferencia | veredicto |
|---|---|---:|---:|---:|---:|---|
| aleatoria | aleatoria | 1999 | 72,7% [71,5%, 73,9%] | 74,7% [73,4%, 75,9%] | -2,0 | pierde |
| repositorio | angular/angular-cli | 2000 | 68,1% [65,5%, 70,7%] | 68,9% | -0,7 | empate |
| repositorio | nuxt/nuxt | 2000 | 67,0% [64,7%, 69,3%] | 67,6% | -0,7 | empate |
| repositorio | sveltejs/svelte | 2000 | 57,0% [55,9%, 58,2%] | 56,8% | +0,3 | empate |
| repositorio | vitejs/vite | 2000 | 71,0% [70,3%, 71,8%] | 73,1% | -2,1 | pierde |
| repositorio | vitest-dev/vitest | 2000 | 67,9% [66,4%, 69,4%] | 68,3% | -0,5 | empate |
| temporal | temporal | 2001 | 74,0% [72,5%, 75,4%] | 73,3% | +0,7 | empate |

**En los 6 folds honestos (por repositorio y temporal): 0 gana, 5 empata, 1 pierde.** La aleatoria no cuenta: fuga información entre entrenamiento y prueba (DESIGN.md §5).

## Qué clase gana y cuál pierde

Diferencia de F1, `f4_codebert` menos `clasico_lr_balanceado`, en puntos. `—`: la clase no tiene ejemplos en prueba. La columna de `refactor` lleva su n al lado (§5).

| partición | fold | `fix` | `feat` | `docs` | `refactor` |
|---|---|---:|---:|---:|---:|
| aleatoria | aleatoria | -2,2 | -1,8 | +1,8 | -5,7 (n = 164) |
| repositorio | angular/angular-cli | -1,3 | +1,0 | -1,6 | -1,1 (n = 468) |
| repositorio | nuxt/nuxt | -3,6 | +0,3 | +0,8 | -0,2 (n = 102) |
| repositorio | sveltejs/svelte | -2,0 | +4,2 | -1,8 | +0,7 (n = 1) |
| repositorio | vitejs/vite | -0,7 | -0,9 | +4,5 | -11,1 (n = 151) |
| repositorio | vitest-dev/vitest | -1,5 | +0,8 | +2,9 | -3,9 (n = 98) |
| temporal | temporal | -1,4 | +3,9 | +2,6 | -2,4 (n = 176) |

## Partición aleatoria

80/20 estratificada por clase, con una división distinta por semilla. **Fuga información**: commits del mismo repositorio quedan a los dos lados.

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `f4_codebert` | 77,7% [76,3%, 79,1%] | 72,7% [71,5%, 73,9%] | 82,5% [81,2%, 83,8%] | 61,0% [59,9%, 62,0%] | 94,6% [93,6%, 95,5%] |
| `clasico_lr_balanceado` | 80,0% [78,8%, 81,3%] | 74,7% [73,4%, 75,9%] | 84,7% [83,4%, 85,9%] | 62,7% [60,2%, 65,2%] | 92,7% [91,7%, 93,7%] |

## Partición por repositorio — la principal

Un fold por repo, con ese repo entero en prueba.

### Fold `angular/angular-cli` en prueba — n = 2000

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `f4_codebert` | 68,9% [66,7%, 71,1%] | 68,1% [65,5%, 70,7%] | 74,7% [72,7%, 76,6%] | 53,2% [51,6%, 54,9%] | 90,3% [89,5%, 91,1%] |
| `clasico_lr_balanceado` | 70,3% | 68,9% | 76,0% | 52,2% | 91,8% |

### Fold `nuxt/nuxt` en prueba — n = 2000

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `f4_codebert` | 75,5% [72,3%, 78,8%] | 67,0% [64,7%, 69,3%] | 75,4% [70,6%, 80,3%] | 60,0% [59,5%, 60,6%] | 96,0% [95,6%, 96,3%] |
| `clasico_lr_balanceado` | 77,3% | 67,6% | 79,0% | 59,8% | 95,2% |

### Fold `sveltejs/svelte` en prueba — n = 2000

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `f4_codebert` | 80,9% [79,6%, 82,2%] | 57,0% [55,9%, 58,2%] | 87,6% [86,6%, 88,6%] | 50,0% [48,7%, 51,2%] | 88,4% [87,7%, 89,2%] |
| `clasico_lr_balanceado` | 82,0% | 56,8% | 89,6% | 45,8% | 90,3% |

### Fold `vitejs/vite` en prueba — n = 2000

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `f4_codebert` | 77,8% [76,5%, 79,1%] | 71,0% [70,3%, 71,8%] | 82,6% [81,1%, 84,1%] | 57,2% [54,3%, 60,1%] | 96,1% [95,2%, 96,9%] |
| `clasico_lr_balanceado` | 79,1% | 73,1% | 83,3% | 58,2% | 91,6% |

### Fold `vitest-dev/vitest` en prueba — n = 2000

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `f4_codebert` | 73,5% [71,7%, 75,2%] | 67,9% [66,4%, 69,4%] | 77,0% [75,2%, 78,8%] | 64,0% [62,8%, 65,1%] | 94,0% [93,2%, 94,8%] |
| `clasico_lr_balanceado` | 74,6% | 68,3% | 78,5% | 63,2% | 91,1% |

## Partición temporal

Corte global el 2025-06-01: entrena con lo anterior y evalúa con lo posterior, 7.999 / 2.001.

| modelo | exactitud | F1 macro | F1 `fix` | F1 `feat` | F1 `docs` |
|---|---:|---:|---:|---:|---:|
| `f4_codebert` | 79,8% [78,2%, 81,4%] | 74,0% [72,5%, 75,4%] | 84,5% [82,9%, 86,0%] | 60,4% [58,0%, 62,8%] | 95,5% [94,8%, 96,1%] |
| `clasico_lr_balanceado` | 80,2% | 73,3% | 85,9% | 56,5% | 92,9% |

## `refactor`, fold por fold

DESIGN.md §5: `refactor` es el 8,2% del dataset, angular-cli aporta el 57% y svelte 1 solo ejemplo. Un F1 calculado sobre un puñado de casos no es una métrica, así que va con el n al lado y **no hay fila de promedio entre folds**.

### Partición aleatoria

| fold | n `refactor` en prueba | `f4_codebert` | `clasico_lr_balanceado` |
|---|---:|---:|---:|
| aleatoria | 164 | 52,8% [50,2%, 55,4%] | 58,5% [55,9%, 61,2%] |

### Partición repositorio

| fold | n `refactor` en prueba | `f4_codebert` | `clasico_lr_balanceado` |
|---|---:|---:|---:|
| angular/angular-cli | 468 | 54,3% [46,8%, 61,8%] | 55,4% |
| nuxt/nuxt | 102 | 36,4% [32,4%, 40,5%] | 36,6% |
| sveltejs/svelte | 1 | 2,2% [-0,4%, 4,7%] | 1,4% |
| vitejs/vite | 151 | 48,3% [45,3%, 51,3%] | 59,4% |
| vitest-dev/vitest | 98 | 36,6% [33,5%, 39,7%] | 40,5% |

### Partición temporal

| fold | n `refactor` en prueba | `f4_codebert` | `clasico_lr_balanceado` |
|---|---:|---:|---:|
| temporal | 176 | 55,5% [53,8%, 57,2%] | 58,0% |

## Cuánto infla la partición aleatoria

Es el punto 1 de DESIGN.md §11. La partición aleatoria reparte commits del mismo repositorio a los dos lados y el modelo memoriza el proyecto. La columna del medio es el **peor fold** de la partición por repositorio, no el promedio: es el que dice qué pasa en el proyecto más distinto de los que vio.

| modelo | F1 macro, aleatoria | F1 macro, por repositorio (peor fold) | caída |
|---|---:|---:|---:|
| `f4_codebert` | 72,7% | 57,0% (sveltejs/svelte) | -15,7 |
| `clasico_lr_balanceado` | 74,7% | 56,8% (sveltejs/svelte) | -17,9 |

## La prueba de etiquetas aleatorias, sobre `f4_codebert`

`LEAKAGE.md` §7.1: con las etiquetas de entrenamiento barajadas, la exactitud no puede pasar la tasa de la clase mayoritaria de prueba por más de +2,0 puntos. CodeBERT ve las rutas completas de los archivos, que el clásico no ve: es un camino nuevo por el que la etiqueta podría colarse.

| partición | fold | techo del azar | exactitud, etiquetas barajadas | exceso | estado |
|---|---|---:|---:|---:|---|
| aleatoria | aleatoria | 55,2% | 35,4% [13,2%, 57,6%] | -19,9 | pasa |
| repositorio | angular/angular-cli | 46,2% | 35,0% [21,7%, 48,4%] | -11,1 | pasa |
| repositorio | nuxt/nuxt | 49,9% | 43,9% [32,6%, 55,1%] | -6,0 | pasa |
| repositorio | sveltejs/svelte | 73,0% | 34,5% [5,7%, 63,3%] | -38,6 | pasa |
| repositorio | vitejs/vite | 53,3% | 46,3% [34,0%, 58,6%] | -7,0 | pasa |
| repositorio | vitest-dev/vitest | 53,7% | 41,4% [18,2%, 64,6%] | -12,3 | pasa |
| temporal | temporal | 58,4% | 39,9% [23,7%, 56,1%] | -18,5 | pasa |

7 folds: 7 pasan, 0 fallan, 0 no concluyentes.

Con etiquetas barajadas la exactitud varía mucho de una semilla a otra y el intervalo sale ancho; algunos intervalos llegan a tocar el techo. El criterio de §7.1 se fijó sobre la media, no sobre el extremo del intervalo, y no se cambia ahora.

## Matrices de confusión — `f4_codebert`, partición por repositorio

Fila: etiqueta verdadera. Columna: predicción. **Semilla 1 de cada fold**: a diferencia del clásico, aquí la semilla cambia el modelo y la matriz de otra semilla sería algo distinta.

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

## Montaje

Hiperparámetros de `config/f4.yaml`, fijados el 2026-09-21 **antes** de entrenar y sin retocar después: no hay conjunto de validación y ninguno se eligió mirando una partición de prueba. Sin afinar puede quedar por debajo de lo que CodeBERT da de verdad; afinarlo contra estos mismos folds sería elegir con el número delante.

| parámetro | valor |
|---|---|
| `modelo_base` | `microsoft/codebert-base` |
| `revision` | `3b0952feddeffad0063f274080e3c23d75e7eb39` |
| `capas_entrenables` | `2` |
| `max_longitud` | `256` |
| `epocas` | `3` |
| `tamano_lote` | `32` |
| `tasa_aprendizaje` | `5e-05` |
| `decaimiento_pesos` | `0.01` |
| `calentamiento` | `0.1` |
| `pesos_por_clase` | `balanceados` |
| `max_archivos_en_texto` | `25` |

El texto del diff **no entra** (DESIGN.md §6.2): el modelo ve el mensaje, los conteos del diff y las rutas de los archivos, lo mismo que el clásico más las rutas completas.

Versiones con que se corrió: python 3.13.15, numpy 2.2.1, scikit-learn 1.6.1, torch 2.11.0+cu128, transformers 4.57.6, cuda 12.8, plataforma Linux-6.6.122+-x86_64-with-glibc2.39.

En GPU los ajustes no son bit a bit reproducibles aunque se fije la semilla; para eso están las cinco semillas.
