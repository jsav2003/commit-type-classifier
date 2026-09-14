# Estadísticas descriptivas del dataset (F0)

Generado por `python -m ccls f0 stats` desde `data/processed/dataset.jsonl` y `dataset_meta.json`. **No se edita a mano.**

## 1 · De dónde sale cada commit

Población: `git log --no-merges --first-parent <sha>`, historial completo desde el SHA fijado en `config/repos.yaml`. *Etiquetables*: el prefijo es de una de las 4 clases. Muestra estratificada por trimestre UTC de la fecha de commit, con tope de 2000 por repo.

| repo | SHA | commits | etiquetables | tasa | muestreados | trimestres | primer commit | último commit |
|---|---|---:|---:|---:|---:|---:|---|---|
| angular/angular-cli | `31c045639e` | 15632 | 8019 | 51.3% | 2000 | 46 | 2015-05-11 | 2026-09-10 |
| sveltejs/svelte | `6eb720a1b7` | 6033 | 2405 | 39.9% | 2000 | 27 | 2018-10-30 | 2026-09-11 |
| nuxt/nuxt | `87adef3843` | 9275 | 5584 | 60.2% | 2000 | 25 | 2020-07-16 | 2026-09-10 |
| vitejs/vite | `99bd9d1d46` | 9215 | 5691 | 61.8% | 2000 | 26 | 2020-04-20 | 2026-09-10 |
| vitest-dev/vitest | `05982297d0` | 6134 | 4007 | 65.3% | 2000 | 20 | 2021-12-03 | 2026-09-14 |
| **total** | | 46289 | 25706 | 55.5% | **10000** | | | |

## 2 · Distribución de clases

La columna *% refactor en historial* es la proporción entre **todos** los commits etiquetables del repo, antes de muestrear; si se parece a la de la muestra, el muestreo no movió el balance.

| repo | fix | feat | refactor | docs | total | % refactor | % refactor en historial |
|---|---:|---:|---:|---:|---:|---:|---:|
| angular/angular-cli | 923 | 327 | 468 | 282 | 2000 | 23.4% | 23.9% |
| sveltejs/svelte | 1461 | 209 | 1 | 329 | 2000 | 0.1% | 0.1% |
| nuxt/nuxt | 997 | 265 | 102 | 636 | 2000 | 5.1% | 4.9% |
| vitejs/vite | 1067 | 351 | 151 | 431 | 2000 | 7.5% | 7.8% |
| vitest-dev/vitest | 1074 | 414 | 98 | 414 | 2000 | 4.9% | 4.5% |
| **total** | **5522** | **1566** | **820** | **2092** | **10000** | **8.2%** | |

| clase | commits | % del dataset |
|---|---:|---:|
| fix | 5522 | 55.2% |
| feat | 1566 | 15.7% |
| refactor | 820 | 8.2% |
| docs | 2092 | 20.9% |

**`refactor`: 820 ejemplos (8.2%).** DESIGN.md §4.4 proyectaba ~1090 a partir de los commits recientes del piloto; este es el número con muestreo sobre todo el historial. angular/angular-cli aporta 468 (57.1% de todos los `refactor`); sveltejs/svelte, 1.

## 3 · Cobertura temporal (commits muestreados por año)

| repo | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| angular/angular-cli | 15 | 91 | 226 | 228 | 261 | 185 | 172 | 138 | 164 | 167 | 213 | 140 |
| sveltejs/svelte | 0 | 0 | 0 | 2 | 2 | 15 | 25 | 4 | 255 | 977 | 422 | 298 |
| nuxt/nuxt | 0 | 0 | 0 | 0 | 0 | 6 | 250 | 471 | 409 | 327 | 273 | 264 |
| vitejs/vite | 0 | 0 | 0 | 0 | 0 | 215 | 488 | 365 | 277 | 241 | 216 | 198 |
| vitest-dev/vitest | 0 | 0 | 0 | 0 | 0 | 0 | 215 | 443 | 343 | 369 | 332 | 298 |

## 4 · Tamaño de los commits por clase

*Líneas* = agregadas + eliminadas según `--numstat`. El diff se guarda truncado a 16000 caracteres; *% truncado* dice a cuántos les afecta.

| clase | commits | mediana archivos | mediana líneas | p90 líneas | % diff truncado | % toca tests | % solo docs |
|---|---:|---:|---:|---:|---:|---:|---:|
| fix | 5522 | 2 | 24 | 145 | 5.5% | 45.6% | 0.3% |
| feat | 1566 | 5 | 81 | 585 | 24.0% | 48.9% | 0.1% |
| refactor | 820 | 3 | 40 | 440 | 16.8% | 18.4% | 0.1% |
| docs | 2092 | 1 | 7 | 80 | 4.7% | 1.6% | 77.0% |

## 5 · Señales a vigilar en la F2

No son entradas decididas: se guardan como banderas para medir cuánto aportan por sí solas antes de decidir si se usan (LEAKAGE.md). *Autor bot*: renovate, dependabot o nombre con `[bot]`. *Breaking*: el prefijo llevaba `!` — sale del prefijo, así que es solo auditoría.

| clase | % autor bot | % referencia a issue | % breaking |
|---|---:|---:|---:|
| fix | 1.7% | 21.2% | 0.9% |
| feat | 0.1% | 8.0% | 4.2% |
| refactor | 0.0% | 1.3% | 3.8% |
| docs | 0.0% | 3.9% | 0.0% |

Commits de bot por repo: angular/angular-cli 0, sveltejs/svelte 8, nuxt/nuxt 2, vitejs/vite 62, vitest-dev/vitest 21.

## 6 · Baseline de una línea para `docs`, sobre el dataset final

Regla: "si todos los archivos tocados son .md/.rst/.txt → docs" (DESIGN.md §6.1).

| repo | precisión | recall | F1 |
|---|---:|---:|---:|
| angular/angular-cli | 0.99 | 0.80 | 0.88 |
| sveltejs/svelte | 0.97 | 0.78 | 0.87 |
| nuxt/nuxt | 1.00 | 0.84 | 0.91 |
| vitejs/vite | 0.99 | 0.74 | 0.85 |
| vitest-dev/vitest | 0.99 | 0.67 | 0.80 |
| **todos** | 0.99 | 0.77 | 0.87 |

## 7 · Prefijo de convención y rutas excluidas (LEAKAGE.md §7.2)

| chequeo | registros |
|---|---:|
| `message` con prefijo (detector genérico) — **debe ser 0** | 0 |
| `diff` que repite el mensaje del propio commit con su prefijo — **debe ser 0** | 0 |
| `diff` con algún `tipo:` al inicio de línea (detector genérico; informativo, es código) | 43 |

Mensajes vacíos después de quitar el prefijo: 0.

Rutas excluidas de `diff`, `files`, extensiones y conteo de líneas: `.changeset/`. Afectan a 1496 commits (sveltejs/svelte 1496). Registros del dataset con el diff vacío, por cualquier motivo: 3.

## 8 · Fuga por correlación (LEAKAGE.md §7.3)

Para cada token candidato, la clase donde más se concentra, en el dataset entero y en cada repo donde aparece. Falla si la ganancia es >= 0.5 con al menos 20 registros con el token. Ganancia = (cota inferior de Wilson de P(c|t) − P(c)) / (1 − P(c)).

| token | ámbito | con token | P(t) | clase | P(t\|c) | P(c) | P(c\|t) | ganancia | falla |
|---|---|---:|---:|---|---:|---:|---:|---:|---|
| changeset: ruta | todos | 0 | 0.0% | fix | 0.0% | 55.2% | 0.0% | 0.00 | no |
| changeset: bump patch | todos | 0 | 0.0% | fix | 0.0% | 55.2% | 0.0% | 0.00 | no |
| changeset: bump minor | todos | 0 | 0.0% | fix | 0.0% | 55.2% | 0.0% | 0.00 | no |
| changeset: bump major | todos | 0 | 0.0% | fix | 0.0% | 55.2% | 0.0% | 0.00 | no |
| palabra patch | todos | 84 | 0.8% | refactor | 1.8% | 8.2% | 17.9% | 0.03 | no |
| palabra minor | todos | 87 | 0.9% | docs | 1.8% | 20.9% | 43.7% | 0.16 | no |
| palabra major | todos | 224 | 2.2% | docs | 3.4% | 20.9% | 31.7% | 0.06 | no |
| changelog: ruta | todos | 146 | 1.5% | docs | 6.7% | 20.9% | 96.6% | 0.90 | **SÍ** |
| changelog: encabezado de versión | todos | 124 | 1.2% | docs | 5.9% | 20.9% | 99.2% | 0.94 | **SÍ** |
| changelog: encabezado de tipo | todos | 11 | 0.1% | docs | 0.4% | 20.9% | 81.8% | 0.40 | no |
| changelog: entrada con scope | todos | 252 | 2.5% | feat | 9.1% | 15.7% | 56.3% | 0.41 | no |
| diff vacío | todos | 3 | 0.0% | docs | 0.1% | 20.9% | 66.7% | -0.00 | no |
| palabra patch | angular/angular-cli | 23 | 1.1% | refactor | 1.9% | 23.4% | 39.1% | -0.02 | no |
| palabra minor | angular/angular-cli | 24 | 1.2% | refactor | 2.4% | 23.4% | 45.8% | 0.06 | no |
| palabra major | angular/angular-cli | 54 | 2.7% | refactor | 4.3% | 23.4% | 37.0% | 0.03 | no |
| changelog: ruta | angular/angular-cli | 127 | 6.3% | docs | 44.7% | 14.1% | 99.2% | 0.95 | **SÍ** |
| changelog: encabezado de versión | angular/angular-cli | 124 | 6.2% | docs | 43.6% | 14.1% | 99.2% | 0.95 | **SÍ** |
| changelog: encabezado de tipo | angular/angular-cli | 5 | 0.2% | docs | 1.8% | 14.1% | 100.0% | 0.49 | no |
| changelog: entrada con scope | angular/angular-cli | 4 | 0.2% | feat | 0.3% | 16.4% | 25.0% | -0.14 | no |
| palabra patch | nuxt/nuxt | 14 | 0.7% | refactor | 1.0% | 5.1% | 7.1% | -0.04 | no |
| palabra minor | nuxt/nuxt | 10 | 0.5% | docs | 1.1% | 31.8% | 70.0% | 0.12 | no |
| palabra major | nuxt/nuxt | 26 | 1.3% | docs | 2.2% | 31.8% | 53.8% | 0.05 | no |
| changelog: ruta | nuxt/nuxt | 2 | 0.1% | refactor | 2.0% | 5.1% | 100.0% | 0.31 | no |
| changelog: encabezado de tipo | nuxt/nuxt | 1 | 0.1% | feat | 0.4% | 13.2% | 100.0% | 0.09 | no |
| changelog: entrada con scope | nuxt/nuxt | 14 | 0.7% | docs | 1.9% | 31.8% | 85.7% | 0.41 | no |
| diff vacío | nuxt/nuxt | 1 | 0.1% | refactor | 1.0% | 5.1% | 100.0% | 0.16 | no |
| palabra patch | sveltejs/svelte | 3 | 0.1% | refactor | 0.0% | 0.1% | 0.0% | -0.00 | no |
| palabra minor | sveltejs/svelte | 24 | 1.2% | feat | 5.3% | 10.4% | 45.8% | 0.19 | no |
| palabra major | sveltejs/svelte | 16 | 0.8% | docs | 2.4% | 16.4% | 50.0% | 0.14 | no |
| changelog: ruta | sveltejs/svelte | 3 | 0.1% | docs | 0.9% | 16.4% | 100.0% | 0.33 | no |
| changelog: encabezado de tipo | sveltejs/svelte | 1 | 0.1% | docs | 0.3% | 16.4% | 100.0% | 0.05 | no |
| palabra patch | vitejs/vite | 26 | 1.3% | refactor | 2.6% | 7.5% | 15.4% | -0.02 | no |
| palabra minor | vitejs/vite | 12 | 0.6% | docs | 1.9% | 21.6% | 66.7% | 0.22 | no |
| palabra major | vitejs/vite | 86 | 4.3% | docs | 6.0% | 21.6% | 30.2% | -0.00 | no |
| changelog: ruta | vitejs/vite | 14 | 0.7% | docs | 2.8% | 21.6% | 85.7% | 0.49 | no |
| changelog: encabezado de tipo | vitejs/vite | 3 | 0.1% | docs | 0.7% | 21.6% | 100.0% | 0.28 | no |
| changelog: entrada con scope | vitejs/vite | 67 | 3.4% | feat | 10.0% | 17.5% | 52.2% | 0.28 | no |
| palabra patch | vitest-dev/vitest | 18 | 0.9% | refactor | 1.0% | 4.9% | 5.6% | -0.04 | no |
| palabra minor | vitest-dev/vitest | 17 | 0.9% | docs | 2.4% | 20.7% | 58.8% | 0.19 | no |
| palabra major | vitest-dev/vitest | 42 | 2.1% | refactor | 0.0% | 4.9% | 0.0% | -0.05 | no |
| changelog: encabezado de tipo | vitest-dev/vitest | 1 | 0.1% | refactor | 1.0% | 4.9% | 100.0% | 0.17 | no |
| changelog: entrada con scope | vitest-dev/vitest | 167 | 8.3% | feat | 25.4% | 20.7% | 62.9% | 0.44 | no |
| diff vacío | vitest-dev/vitest | 2 | 0.1% | docs | 0.5% | 20.7% | 100.0% | 0.17 | no |

Tokens que fallan: **4**.

## 9 · Versionado

- `manifest_sha256`: `0177140ce63d03f1fa1aa38f7cde6bdc6ef57f3442b0cc8cf4278e2d7b7249a5`
- `dataset_jsonl_sha256`: `797b73e4182caeed0643eb5ac88bbba05cc9de233a15f116cb6144f6c0d569ff` (git version 2.51.0.windows.1)
- semilla 20260914, tope 2000 por repo, diff truncado a 16000 caracteres con 3 líneas de contexto

