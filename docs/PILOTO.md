# Resultados del piloto

Generado por `python -m ccls pilot report`. Reemplaza tres supuestos del diseño por números medidos — ver DESIGN.md §4-6 y la Parte B del plan de arranque. **No se editó a mano.**

## B2.1 / B2.2 · Tasa de prefijo válido y distribución de clases

Muestra: últimos N commits de `git log --no-merges --first-parent` por repo — la misma población que usará la extracción real (C2), no el log crudo. Medir sobre el log crudo diluiría la tasa con commits de merge, que nunca llevan prefijo `tipo:` y no iban a entrar al dataset de todos modos.

| repo | muestreados | tasa prefijo válido | fix | feat | refactor | docs |
|---|---:|---:|---:|---:|---:|---:|
| angular/angular-cli | 1000 | 52.5% | 216 | 38 | 172 | 99 |
| hashicorp/hcl | 357 | 0.3% | 0 | 0 | 0 | 1 |
| nuxt/nuxt | 1000 | 60.4% | 389 | 78 | 53 | 84 |
| python-poetry/poetry | 1000 | 21.1% | 93 | 45 | 14 | 59 |
| rust-lang/rustfmt | 1000 | 13.2% | 57 | 28 | 31 | 16 |
| spf13/cobra | 836 | 4.4% | 23 | 7 | 3 | 4 |
| sveltejs/svelte | 1000 | 57.5% | 475 | 27 | 1 | 72 |
| vitejs/vite | 1000 | 64.2% | 270 | 118 | 49 | 205 |
| vitest-dev/vitest | 1000 | 69.3% | 374 | 131 | 36 | 152 |
| vuejs/core | 1000 | 47.8% | 442 | 7 | 17 | 12 |

## B2.4 · Commits perdidos por `--no-merges --first-parent`

Sobre el historial completo del repo (no una muestra).

| repo | total | no_merges | first_parent | no_merges+first_parent | % perdido | veredicto |
|---|---:|---:|---:|---:|---:|---|
| angular/angular-cli | 18806 | 18766 | 15637 | 15632 | 16.9% | ok |
| hashicorp/hcl | 1591 | 1361 | 575 | 357 | 77.6% | ok |
| nuxt/nuxt | 15600 | 15163 | 9287 | 9275 | 40.5% | ok |
| python-poetry/poetry | 3859 | 3728 | 3286 | 3182 | 17.5% | ok |
| rust-lang/rustfmt | 6342 | 4784 | 2790 | 1417 | 77.7% | ok |
| spf13/cobra | 1106 | 992 | 950 | 836 | 24.4% | ok |
| sveltejs/svelte | 11399 | 9852 | 6966 | 6033 | 47.1% | ok |
| vitejs/vite | 9677 | 9607 | 9225 | 9215 | 4.8% | ok |
| vitest-dev/vitest | 6142 | 6139 | 6137 | 6134 | 0.1% | ok |
| vuejs/core | 7176 | 7141 | 6455 | 6424 | 10.5% | ok |

## B2.5 · Baseline de una línea para la clase `docs`

Regla: "si todos los archivos tocados son .md/.rst/.txt → docs". Evaluada contra la etiqueta declarada.

| repo | evaluados | precisión | recall | F1 |
|---|---:|---:|---:|---:|
| angular/angular-cli | 525 | 0.98 | 0.92 | 0.95 |
| hashicorp/hcl | 1 | 1.00 | 1.00 | 1.00 |
| nuxt/nuxt | 604 | 1.00 | 0.82 | 0.90 |
| python-poetry/poetry | 211 | 0.93 | 0.88 | 0.90 |
| rust-lang/rustfmt | 132 | 1.00 | 0.75 | 0.86 |
| spf13/cobra | 37 | 0.67 | 1.00 | 0.80 |
| sveltejs/svelte | 575 | 0.97 | 0.79 | 0.87 |
| vitejs/vite | 642 | 1.00 | 0.69 | 0.82 |
| vitest-dev/vitest | 693 | 0.99 | 0.66 | 0.80 |
| vuejs/core | 478 | 0.80 | 0.67 | 0.73 |

**F1 promedio 0.86 — alto**: la clase `docs` puede ser casi trivial de acertar por una señal estructural; un F1 macro alto de cualquier modelo puede estar inflado por esta clase sin que haya aprendizaje real sobre las otras tres.

## B2.3 · Coste de clonado (historial completo, sin acotar por fecha)

| estrategia | clon (s) | extracción -p --numstat (s) | disco (MB) | ok |
|---|---:|---:|---:|---|
| completo | 39.8 | 2.9 | 17.2 | True |
| filter_blob_none | 16.4 | 1873.9 | 11.3 | False |

**Estrategia elegida para la F0: `completo`** (tiempo total clon+extracción: completo=42.7s, filter_blob_none=1890.3s).

## Proyección y puerta de decisión

| repo | tasa prefijo | % perdido merge | admitido | commits utilizables estimados |
|---|---:|---:|---|---:|
| angular/angular-cli | 52.5% | 16.9% | sí | 2000 |
| hashicorp/hcl | 0.3% | 77.6% | NO | 0 |
| nuxt/nuxt | 60.4% | 40.5% | sí | 2000 |
| python-poetry/poetry | 21.1% | 17.5% | NO | 0 |
| rust-lang/rustfmt | 13.2% | 77.7% | NO | 0 |
| spf13/cobra | 4.4% | 24.4% | NO | 0 |
| sveltejs/svelte | 57.5% | 47.1% | sí | 2000 |
| vitejs/vite | 64.2% | 4.8% | sí | 2000 |
| vitest-dev/vitest | 69.3% | 0.1% | sí | 2000 |
| vuejs/core | 47.8% | 10.5% | NO | 0 |

**Total estimado con los 10 candidatos del piloto: 10000 commits utilizables** (de 5 repos admitidos de 10 candidatos).

Faltan **10000 commits** para el mínimo de 20000. Con un promedio de 2000 commits utilizables por repo admitido, hacen falta ~**5 repos adicionales** de perfil similar.

### Distribución de clases agregada (los 10 candidatos del piloto)

| clase | commits | % del total clasificado |
|---|---:|---:|
| fix | 2339 | 60.0% |
| feat | 479 | 12.3% |
| refactor | 376 | 9.6% |
| docs | 704 | 18.1% |

Ninguna clase por debajo del 5%. Sin alerta de desbalance severo.

### Veredicto

**Puerta ABIERTA con la regla de rescate (DESIGN.md §8).** No se alcanza el mínimo de 20.000 con los candidatos del piloto, pero sí una base razonable. Se ajusta la meta a 10.000 commits de menos repositorios, **por escrito en el README**, antes de seguir.

