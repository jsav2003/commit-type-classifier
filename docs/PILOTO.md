# Resultados del piloto

Generado por `python -m ccls pilot report`. Reemplaza tres supuestos del diseño por números medidos — ver DESIGN.md §4-6 y la Parte B del plan de arranque. **No se editó a mano.**

## B2.1 / B2.2 · Tasa de prefijo válido y distribución de clases

Muestra: últimos N commits de `git log --no-merges --first-parent` por repo — la misma población que usará la extracción real (C2), no el log crudo. Medir sobre el log crudo diluiría la tasa con commits de merge, que nunca llevan prefijo `tipo:` y no iban a entrar al dataset de todos modos.

| repo | muestreados | tasa prefijo válido | fix | feat | refactor | docs |
|---|---:|---:|---:|---:|---:|---:|
| angular/angular-cli | 1000 | 52.5% | 216 | 38 | 172 | 99 |
| hashicorp/hcl | 357 | 0.3% | 0 | 0 | 0 | 1 |
| python-poetry/poetry | 1000 | 21.1% | 93 | 45 | 14 | 59 |
| rust-lang/rustfmt | 1000 | 13.2% | 57 | 28 | 31 | 16 |
| spf13/cobra | 836 | 4.4% | 23 | 7 | 3 | 4 |
| sveltejs/svelte | 1000 | 57.5% | 475 | 27 | 1 | 72 |

## B2.4 · Commits perdidos por `--no-merges --first-parent`

Sobre el historial completo del repo (no una muestra).

| repo | total | no_merges | first_parent | no_merges+first_parent | % perdido | veredicto |
|---|---:|---:|---:|---:|---:|---|
| angular/angular-cli | 18806 | 18766 | 15637 | 15632 | 16.9% | ok |
| hashicorp/hcl | 1591 | 1361 | 575 | 357 | 77.6% | ok |
| python-poetry/poetry | 3859 | 3728 | 3286 | 3182 | 17.5% | ok |
| rust-lang/rustfmt | 6342 | 4784 | 2790 | 1417 | 77.7% | ok |
| spf13/cobra | 1106 | 992 | 950 | 836 | 24.4% | ok |
| sveltejs/svelte | 11399 | 9852 | 6966 | 6033 | 47.1% | ok |

## B2.5 · Baseline de una línea para la clase `docs`

Regla: "si todos los archivos tocados son .md/.rst/.txt → docs". Evaluada contra la etiqueta declarada.

| repo | evaluados | precisión | recall | F1 |
|---|---:|---:|---:|---:|
| angular/angular-cli | 525 | 0.98 | 0.92 | 0.95 |
| hashicorp/hcl | 1 | 1.00 | 1.00 | 1.00 |
| python-poetry/poetry | 211 | 0.93 | 0.88 | 0.90 |
| rust-lang/rustfmt | 132 | 1.00 | 0.75 | 0.86 |
| spf13/cobra | 37 | 0.67 | 1.00 | 0.80 |
| sveltejs/svelte | 575 | 0.97 | 0.79 | 0.87 |

**F1 promedio 0.90 — alto**: la clase `docs` puede ser casi trivial de acertar por una señal estructural; un F1 macro alto de cualquier modelo puede estar inflado por esta clase sin que haya aprendizaje real sobre las otras tres.

## B2.3 · Coste de clonado (historial completo, sin acotar por fecha)

| estrategia | clon (s) | extracción -p --numstat (s) | disco (MB) | ok |
|---|---:|---:|---:|---|
| completo | 39.8 | 2.9 | 17.2 | True |
| filter_blob_none | 16.4 | 1873.9 | 11.3 | False |

**Estrategia elegida para la F0: `completo`** (tiempo total clon+extracción: completo=42.7s, filter_blob_none=1890.3s).

## Proyección y puerta de decisión

| repo | tasa prefijo | % perdido merge | admitido | commits utilizables estimados |
|---|---:|---:|---|---:|
| angular/angular-cli | 52.5% | 16.9% | NO | 0 |
| hashicorp/hcl | 0.3% | 77.6% | NO | 0 |
| python-poetry/poetry | 21.1% | 17.5% | NO | 0 |
| rust-lang/rustfmt | 13.2% | 77.7% | NO | 0 |
| spf13/cobra | 4.4% | 24.4% | NO | 0 |
| sveltejs/svelte | 57.5% | 47.1% | NO | 0 |

**Total estimado con los 6 candidatos del piloto: 0 commits utilizables** (de 0 repos admitidos de 6 candidatos).

**Ningún candidato del piloto fue admitido.** No hay base para proyectar.

### Distribución de clases agregada (los 6 candidatos del piloto)

| clase | commits | % del total clasificado |
|---|---:|---:|
| fix | 864 | 58.3% |
| feat | 145 | 9.8% |
| refactor | 221 | 14.9% |
| docs | 251 | 16.9% |

Ninguna clase por debajo del 5%. Sin alerta de desbalance severo.

### Veredicto

**Puerta CERRADA por ahora.** Ni el mínimo de 20.000 ni el piso de la regla de rescate (10.000) son alcanzables con este conjunto de candidatos. Hace falta ampliar la búsqueda de repos (más candidatos, o revisar el umbral de tasa de prefijo) antes de comprometerse a la F0.

