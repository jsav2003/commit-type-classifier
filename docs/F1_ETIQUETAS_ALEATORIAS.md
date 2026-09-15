# Prueba de fuga por etiquetas aleatorias (F1)

Generado por `python -m ccls f1 fuga-aleatoria`. **No se edita a mano.** Criterio y lectura en `LEAKAGE.md` §7.1.

- Modelo: `humo` (`src/ccls/modelos.py`). Solo verifica el montaje: sus números con etiquetas de verdad **no son resultados de la F2**.
- Semillas: 1, 2, 3, 4, 5. Media e intervalo t al 95% entre semillas.
- Tolerancia: +2,0 puntos sobre el techo del azar (tasa de la clase mayoritaria en prueba).
- En las particiones por repositorio y temporal la división es fija y la regresión logística es determinista: el control da lo mismo con cada semilla y su intervalo tiene ancho cero.
- Dataset: `manifest_sha256` `0177140ce63d03f1fa1aa38f7cde6bdc6ef57f3442b0cc8cf4278e2d7b7249a5`.

## Partición aleatoria

| fold | n prueba | techo del azar | exactitud, etiquetas barajadas | F1 macro, barajadas | exactitud, control | exceso (puntos) | estado |
|---|---:|---:|---:|---:|---:|---:|---|
| aleatoria | 1999 | 55,2% | 53,7% [53,4%, 54,0%] | 19,1% [18,4%, 19,7%] | 75,4% [74,9%, 76,0%] | -1,5 | pasa |

## Partición repositorio

| fold | n prueba | techo del azar | exactitud, etiquetas barajadas | F1 macro, barajadas | exactitud, control | exceso (puntos) | estado |
|---|---:|---:|---:|---:|---:|---:|---|
| angular/angular-cli | 2000 | 46,2% | 44,2% [42,9%, 45,6%] | 16,7% [15,9%, 17,4%] | 54,5% [54,5%, 54,5%] | -1,9 | pasa |
| nuxt/nuxt | 2000 | 49,9% | 48,9% [48,5%, 49,4%] | 17,5% [17,1%, 17,9%] | 71,5% [71,5%, 71,5%] | -0,9 | pasa |
| sveltejs/svelte | 2000 | 73,0% | 69,3% [67,8%, 70,9%] | 22,8% [21,3%, 24,4%] | 78,6% [78,6%, 78,6%] | -3,7 | pasa |
| vitejs/vite | 2000 | 53,3% | 52,2% [51,8%, 52,6%] | 18,9% [17,9%, 19,9%] | 70,9% [70,9%, 70,9%] | -1,1 | pasa |
| vitest-dev/vitest | 2000 | 53,7% | 52,6% [52,0%, 53,1%] | 18,8% [18,5%, 19,1%] | 71,2% [71,2%, 71,2%] | -1,1 | pasa |

## Partición temporal

| fold | n prueba | techo del azar | exactitud, etiquetas barajadas | F1 macro, barajadas | exactitud, control | exceso (puntos) | estado |
|---|---:|---:|---:|---:|---:|---:|---|
| temporal | 2001 | 58,4% | 56,8% [55,8%, 57,9%] | 20,0% [18,9%, 21,2%] | 76,6% [76,6%, 76,6%] | -1,6 | pasa |

## Resultado

7 folds: 7 pasan, 0 fallan, 0 no concluyentes.
