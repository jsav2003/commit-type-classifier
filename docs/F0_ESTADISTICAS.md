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

Para cada token candidato, la clase donde más se concentra, en el dataset entero y en cada repo donde aparece. Todo se mide por separado en los estratos *solo docs* y *no solo docs* (la regla estructural de DESIGN.md §6.1): un token cuenta como fuga solo si dice algo más que esa regla. Falla si la ganancia es >= 0.5 con al menos 20 registros con el token. Ganancia = (cota inferior de Wilson de P(c|t) − P(c)) / (1 − P(c)), con P(c) dentro del estrato.

| token | ámbito | estrato | con token | P(t) | clase | P(t\|c) | P(c) | P(c\|t) | ganancia | falla |
|---|---|---|---:|---:|---|---:|---:|---:|---:|---|
| changeset: ruta | todos | solo docs | 0 | 0.0% | fix | 0.0% | 0.9% | 0.0% | 0.00 | no |
| changeset: bump patch | todos | solo docs | 0 | 0.0% | fix | 0.0% | 0.9% | 0.0% | 0.00 | no |
| changeset: bump minor | todos | solo docs | 0 | 0.0% | fix | 0.0% | 0.9% | 0.0% | 0.00 | no |
| changeset: bump major | todos | solo docs | 0 | 0.0% | fix | 0.0% | 0.9% | 0.0% | 0.00 | no |
| palabra patch | todos | solo docs | 9 | 0.6% | refactor | 0.0% | 0.1% | 0.0% | -0.00 | no |
| palabra minor | todos | solo docs | 27 | 1.7% | fix | 13.3% | 0.9% | 7.4% | 0.01 | no |
| palabra major | todos | solo docs | 44 | 2.7% | refactor | 0.0% | 0.1% | 0.0% | -0.00 | no |
| changelog: ruta | todos | solo docs | 136 | 8.4% | refactor | 0.0% | 0.1% | 0.0% | -0.00 | no |
| changelog: encabezado de versión | todos | solo docs | 123 | 7.6% | refactor | 0.0% | 0.1% | 0.0% | -0.00 | no |
| changelog: encabezado de tipo | todos | solo docs | 6 | 0.4% | refactor | 0.0% | 0.1% | 0.0% | -0.00 | no |
| changelog: entrada con scope | todos | solo docs | 2 | 0.1% | refactor | 0.0% | 0.1% | 0.0% | -0.00 | no |
| diff vacío | todos | solo docs | 0 | 0.0% | fix | 0.0% | 0.9% | 0.0% | 0.00 | no |
| changeset: ruta | todos | no solo docs | 0 | 0.0% | fix | 0.0% | 65.8% | 0.0% | 0.00 | no |
| changeset: bump patch | todos | no solo docs | 0 | 0.0% | fix | 0.0% | 65.8% | 0.0% | 0.00 | no |
| changeset: bump minor | todos | no solo docs | 0 | 0.0% | fix | 0.0% | 65.8% | 0.0% | 0.00 | no |
| changeset: bump major | todos | no solo docs | 0 | 0.0% | fix | 0.0% | 65.8% | 0.0% | 0.00 | no |
| palabra patch | todos | no solo docs | 75 | 0.9% | refactor | 1.8% | 9.8% | 20.0% | 0.03 | no |
| palabra minor | todos | no solo docs | 60 | 0.7% | docs | 2.7% | 5.8% | 21.7% | 0.08 | no |
| palabra major | todos | no solo docs | 180 | 2.2% | docs | 5.6% | 5.8% | 15.0% | 0.05 | no |
| changelog: ruta | todos | no solo docs | 10 | 0.1% | docs | 1.0% | 5.8% | 50.0% | 0.19 | no |
| changelog: encabezado de versión | todos | no solo docs | 1 | 0.0% | feat | 0.1% | 18.7% | 100.0% | 0.02 | no |
| changelog: encabezado de tipo | todos | no solo docs | 5 | 0.1% | docs | 0.6% | 5.8% | 60.0% | 0.18 | no |
| changelog: entrada con scope | todos | no solo docs | 1 | 0.0% | docs | 0.2% | 5.8% | 100.0% | 0.16 | no |
| diff vacío | todos | no solo docs | 3 | 0.0% | docs | 0.4% | 5.8% | 66.7% | 0.16 | no |
| palabra patch | angular/angular-cli | solo docs | 6 | 2.6% | feat | 0.0% | 0.0% | 0.0% | 0.00 | no |
| palabra minor | angular/angular-cli | solo docs | 7 | 3.1% | feat | 0.0% | 0.0% | 0.0% | 0.00 | no |
| palabra major | angular/angular-cli | solo docs | 11 | 4.8% | feat | 0.0% | 0.0% | 0.0% | 0.00 | no |
| changelog: ruta | angular/angular-cli | solo docs | 126 | 55.5% | feat | 0.0% | 0.0% | 0.0% | -0.00 | no |
| changelog: encabezado de versión | angular/angular-cli | solo docs | 123 | 54.2% | feat | 0.0% | 0.0% | 0.0% | 0.00 | no |
| changelog: encabezado de tipo | angular/angular-cli | solo docs | 5 | 2.2% | feat | 0.0% | 0.0% | 0.0% | -0.00 | no |
| palabra patch | angular/angular-cli | no solo docs | 17 | 1.0% | refactor | 1.9% | 26.3% | 52.9% | 0.06 | no |
| palabra minor | angular/angular-cli | no solo docs | 17 | 1.0% | refactor | 2.4% | 26.3% | 64.7% | 0.20 | no |
| palabra major | angular/angular-cli | no solo docs | 43 | 2.4% | refactor | 4.3% | 26.3% | 46.5% | 0.08 | no |
| changelog: ruta | angular/angular-cli | no solo docs | 1 | 0.1% | feat | 0.3% | 18.4% | 100.0% | 0.03 | no |
| changelog: encabezado de versión | angular/angular-cli | no solo docs | 1 | 0.1% | feat | 0.3% | 18.4% | 100.0% | 0.03 | no |
| palabra patch | nuxt/nuxt | solo docs | 2 | 0.4% | refactor | 0.0% | 0.0% | 0.0% | 0.00 | no |
| palabra minor | nuxt/nuxt | solo docs | 6 | 1.1% | refactor | 0.0% | 0.0% | 0.0% | 0.00 | no |
| palabra major | nuxt/nuxt | solo docs | 8 | 1.5% | refactor | 0.0% | 0.0% | 0.0% | 0.00 | no |
| palabra patch | nuxt/nuxt | no solo docs | 12 | 0.8% | refactor | 1.0% | 7.0% | 8.3% | -0.06 | no |
| palabra minor | nuxt/nuxt | no solo docs | 4 | 0.3% | docs | 1.0% | 7.0% | 25.0% | -0.03 | no |
| palabra major | nuxt/nuxt | no solo docs | 18 | 1.2% | docs | 5.8% | 7.0% | 33.3% | 0.10 | no |
| changelog: ruta | nuxt/nuxt | no solo docs | 2 | 0.1% | refactor | 2.0% | 7.0% | 100.0% | 0.29 | no |
| changelog: encabezado de tipo | nuxt/nuxt | no solo docs | 1 | 0.1% | feat | 0.4% | 18.0% | 100.0% | 0.03 | no |
| diff vacío | nuxt/nuxt | no solo docs | 1 | 0.1% | refactor | 1.0% | 7.0% | 100.0% | 0.15 | no |
| palabra minor | sveltejs/svelte | solo docs | 2 | 0.8% | feat | 0.0% | 0.0% | 0.0% | 0.00 | no |
| palabra major | sveltejs/svelte | solo docs | 3 | 1.1% | feat | 0.0% | 0.0% | 0.0% | 0.00 | no |
| changelog: ruta | sveltejs/svelte | solo docs | 1 | 0.4% | feat | 0.0% | 0.0% | 0.0% | 0.00 | no |
| palabra patch | sveltejs/svelte | no solo docs | 3 | 0.2% | refactor | 0.0% | 0.1% | 0.0% | -0.00 | no |
| palabra minor | sveltejs/svelte | no solo docs | 22 | 1.3% | feat | 5.3% | 12.0% | 50.0% | 0.21 | no |
| palabra major | sveltejs/svelte | no solo docs | 13 | 0.7% | docs | 6.9% | 4.1% | 38.5% | 0.14 | no |
| changelog: ruta | sveltejs/svelte | no solo docs | 2 | 0.1% | docs | 2.8% | 4.1% | 100.0% | 0.31 | no |
| changelog: encabezado de tipo | sveltejs/svelte | no solo docs | 1 | 0.1% | docs | 1.4% | 4.1% | 100.0% | 0.17 | no |
| palabra patch | vitejs/vite | solo docs | 1 | 0.3% | feat | 0.0% | 0.0% | 0.0% | 0.00 | no |
| palabra minor | vitejs/vite | solo docs | 4 | 1.2% | feat | 0.0% | 0.0% | 0.0% | 0.00 | no |
| palabra major | vitejs/vite | solo docs | 16 | 5.0% | feat | 0.0% | 0.0% | 0.0% | 0.00 | no |
| changelog: ruta | vitejs/vite | solo docs | 9 | 2.8% | feat | 0.0% | 0.0% | 0.0% | 0.00 | no |
| changelog: encabezado de tipo | vitejs/vite | solo docs | 1 | 0.3% | feat | 0.0% | 0.0% | 0.0% | 0.00 | no |
| changelog: entrada con scope | vitejs/vite | solo docs | 2 | 0.6% | feat | 0.0% | 0.0% | 0.0% | 0.00 | no |
| palabra patch | vitejs/vite | no solo docs | 25 | 1.5% | docs | 2.7% | 6.7% | 12.0% | -0.03 | no |
| palabra minor | vitejs/vite | no solo docs | 8 | 0.5% | docs | 3.5% | 6.7% | 50.0% | 0.16 | no |
| palabra major | vitejs/vite | no solo docs | 70 | 4.2% | fix | 5.1% | 63.4% | 77.1% | 0.07 | no |
| changelog: ruta | vitejs/vite | no solo docs | 5 | 0.3% | docs | 2.7% | 6.7% | 60.0% | 0.18 | no |
| changelog: encabezado de tipo | vitejs/vite | no solo docs | 2 | 0.1% | docs | 1.8% | 6.7% | 100.0% | 0.29 | no |
| changelog: entrada con scope | vitejs/vite | no solo docs | 1 | 0.1% | docs | 0.9% | 6.7% | 100.0% | 0.15 | no |
| palabra minor | vitest-dev/vitest | solo docs | 8 | 2.8% | fix | 66.7% | 1.1% | 25.0% | 0.06 | no |
| palabra major | vitest-dev/vitest | solo docs | 6 | 2.1% | refactor | 0.0% | 0.0% | 0.0% | 0.00 | no |
| palabra patch | vitest-dev/vitest | no solo docs | 18 | 1.0% | refactor | 1.0% | 5.7% | 5.6% | -0.05 | no |
| palabra minor | vitest-dev/vitest | no solo docs | 9 | 0.5% | docs | 2.9% | 8.0% | 44.4% | 0.12 | no |
| palabra major | vitest-dev/vitest | no solo docs | 36 | 2.1% | docs | 2.9% | 8.0% | 11.1% | -0.04 | no |
| changelog: encabezado de tipo | vitest-dev/vitest | no solo docs | 1 | 0.1% | refactor | 1.0% | 5.7% | 100.0% | 0.16 | no |
| diff vacío | vitest-dev/vitest | no solo docs | 2 | 0.1% | docs | 1.5% | 8.0% | 100.0% | 0.29 | no |

Tokens que fallan: **0**.

## 9 · Versionado

- `manifest_sha256`: `0177140ce63d03f1fa1aa38f7cde6bdc6ef57f3442b0cc8cf4278e2d7b7249a5`
- `dataset_jsonl_sha256`: `797b73e4182caeed0643eb5ac88bbba05cc9de233a15f116cb6144f6c0d569ff` (git version 2.51.0.windows.1)
- semilla 20260914, tope 2000 por repo, diff truncado a 16000 caracteres con 3 líneas de contexto

