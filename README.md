# Clasificación automática de commits por tipo de cambio

Clasifica commits de Git en `fix / feat / refactor / docs` y compara tres enfoques
(ML clásico, transfer learning, red desde cero) sobre las mismas particiones y las
mismas métricas. El objetivo no es el clasificador — es demostrar, con evidencia,
cuál enfoque funciona mejor y por qué. Ver [`DESIGN.md`](DESIGN.md) para el diseño
completo y [`NO-GOALS.md`](NO-GOALS.md) para los límites.

## Estado

| Fase | Estado |
|---|---|
| Andamiaje del repo | ✅ hecho |
| Piloto (mide 5 supuestos del diseño antes de comprometerse a la F0) | ✅ hecho — ver `docs/PILOTO.md` |
| F0 · Recolección de datos | ✅ **cerrada** el 2026-09-15 con la regla de rescate: 10.000 commits de 5 repos, reproducible byte a byte, pruebas de fuga del prefijo y de correlación en verde (`LEAKAGE.md`). La de etiquetas aleatorias (§7.1) necesita la F1 |
| F1 · Infraestructura de experimentos | ✅ **cerrada** el 2026-09-15: `python -m ccls f1 run` entrena, evalúa y guarda con las tres particiones y cinco semillas. La prueba de etiquetas aleatorias (§7.1) **pasa en 7 de 7 folds** (`docs/F1_ETIQUETAS_ALEATORIAS.md`) |
| F2 · Baselines | ✅ **cerrada** el 2026-09-18: trivial, la regla de `docs` de §6.1 y el clásico (TF-IDF + rasgos, con regresión logística y gradient boosting), en las tres particiones con 5 semillas e intervalos. Tablas en `docs/F2_BASELINES.md` |
| F3 · Techo humano | 🔶 **en curso** (2026-09-20): la muestra de 350 ítems, la herramienta de etiquetado (`python -m ccls f3 label`), las predicciones y el reporte están listos; **hay un techo provisional puesto por un LLM** (`docs/F3_TECHO_LLM.md`, no es un techo humano); el techo humano sigue pendiente de que lo etiquete una persona |
| F4 · Transfer learning | 🔶 **infraestructura lista** (2026-09-21), sin resultados todavía: CodeBERT con las últimas 2 capas reentrenadas (`config/f4.yaml`, fijada antes de entrenar), enchufado al mismo runner, reanudable y probado en CPU. Falta correrlo en una GPU |
| F5-F6 | no empezadas |

## Resultado del piloto (resumen)

10 repos medidos (6 candidatos + 4 de una segunda ola centrada en TS/JS con
`commitlint`, tras ver que ahí rendían los únicos dos candidatos iniciales que
se acercaban al umbral). El umbral de 60% de `DESIGN.md` era un supuesto sin
medir: ningún repo lo alcanzó, así que se bajó a 50% con el dato real en mano
(ver `config/repos.yaml`, comentario en `tasa_prefijo_valido_minima`).

**5 repos admitidos** (`angular/angular-cli`, `sveltejs/svelte`, `nuxt/nuxt`,
`vitejs/vite`, `vitest-dev/vitest`), cada uno tocando el tope de 2.000
commits/repo → **~10.000 commits**. `vuejs/core` queda **fuera**: dio 47,8%,
por debajo del 50%, y estar ya clonado no es razón para bajar el umbral — eso
sería mover el criterio para acomodar el dato. `storybookjs/storybook` se
descartó del piloto por ser demasiado pesado de clonar en el tiempo
disponible, no por no cumplir criterios.

Detalle completo, las 5 tablas y las decisiones de metodología en
[`docs/PILOTO.md`](docs/PILOTO.md).

## El dataset (F0)

10.000 commits, 2.000 por repo, muestreados por trimestre a lo largo de todo el
historial desde un SHA fijado. Detalle en
[`docs/F0_ESTADISTICAS.md`](docs/F0_ESTADISTICAS.md).

| clase | commits | % |
|---|---:|---:|
| fix | 5.522 | 55,2% |
| feat | 1.566 | 15,7% |
| refactor | 820 | 8,2% |
| docs | 2.092 | 20,9% |

- `refactor` es escasa y está concentrada: angular-cli aporta 468 (57%) y svelte 1.
  Se reporta fold por fold, nunca promediada (`DESIGN.md` §5).
- svelte adoptó la convención en 2023: 1.952 de sus 2.000 commits son de 2023-2026
  (`DESIGN.md` §5).
- `.changeset/` se excluye de todas las entradas porque delataba la etiqueta
  (`LEAKAGE.md` §7.2).
- `data/processed/manifest.csv` (repo, SHA, etiqueta, fecha) define el dataset y va en
  git; el `.jsonl` con los diffs no. `manifest_sha256`:
  `0177140ce63d03f1fa1aa38f7cde6bdc6ef57f3442b0cc8cf4278e2d7b7249a5`.

## Resultados de los baselines (F2)

Tablas completas, por clase y fold por fold, en
[`docs/F2_BASELINES.md`](docs/F2_BASELINES.md). Lo que hay que saber:

**`docs` casi no requiere modelo.** La regla de una línea de `DESIGN.md` §6.1 — todos
los archivos tocados son `.md`/`.rst`/`.txt` — saca un F1 de `docs` de **0,80 a 0,91**
según el fold, con precisión de ~0,99. Cualquier F1 macro alto hay que leerlo restando
eso: una parte viene de una señal estructural, no de haber aprendido la tarea.

**La partición aleatoria infla el resultado ~18 puntos.** Es el punto 1 de §11:

| modelo | F1 macro, aleatoria | F1 macro, peor fold por repositorio | caída |
|---|---:|---:|---:|
| `trivial` | 17,8% | 15,8% | -2,0 |
| `regla_docs` | 41,4% | 39,1% | -2,3 |
| `clasico_lr` | 74,5% | 56,7% | **-17,8** |
| `clasico_gb` | 73,6% | 54,2% | **-19,4** |

**`refactor` es donde se cae todo.** En la partición principal, el clásico sin
reponderar saca **0,286** de F1 en `refactor` en angular-cli — el fold con 468 ejemplos,
el más favorable. Reponderar (`class_weight="balanced"`) lo sube a **0,554**, a costa de
exactitud. Por §7.4 el proyecto mira el F1 por clase antes que la exactitud, así que el
clásico de referencia es el reponderado; el otro se reporta al lado (`DESIGN.md` §4.4).

**Gradient boosting no le gana a la regresión logística** en ninguna partición, y en
angular-cli pierde por 5 puntos de F1 macro.

**Los rasgos hechos a mano sí aportan.** Solo con el mensaje, el F1 macro en angular-cli
cae de 59,2% a 36,8%. `tiene_referencia_issue` **no** aporta y no entra: mueve menos de
1 punto y el patrón que la calcula exige las palabras `close`/`fix`/`resolve`, que el
TF-IDF ya ve (`DESIGN.md` §6.2).

**La prueba de etiquetas aleatorias se repitió sobre el clásico** y pasa en 7 de 7
folds, ahora con un control que saca entre 14 y 35 puntos sobre el techo del azar
(`LEAKAGE.md` §7.1).

## Limitación principal: diversidad de ecosistema, no tamaño

El dataset está limitado por **diversidad**, no por volumen:

- **Los 5 repos son TypeScript/JavaScript**, y tres de ellos (`vite`, `vitest`,
  `nuxt`) pertenecen a la misma comunidad: comparten mantenedores, herramientas y
  estilo de mensajes.
- **La partición principal es por repositorio** (`DESIGN.md` §5). Con este dataset,
  "un repo que el modelo nunca vio" significa "otro proyecto TS/JS, muy
  probablemente del mismo mundillo". Lo que esa partición mide es generalización
  **dentro de un ecosistema**, no a proyectos nuevos en general, y así se reporta.
- **La escasez de `refactor`** (8,2%, casi todo de `angular-cli`; ver `DESIGN.md`
  §4.4) tampoco es un problema de tamaño: más repos del mismo perfil traerían la misma
  proporción.

**Por qué no se buscaron más repos.** El único perfil que pasó el umbral de
convención es TS/JS con `commitlint`. Una tercera ola de ese perfil podía llevar el
dataset de ~10.000 a ~20.000 commits, pero habría empeorado justo la limitación
real. Y el volumen no cambia la conclusión: 10.000 y 20.000 commits están igual de
lejos de lo que necesitaría la red desde cero (`DESIGN.md` §6.4). Va a perder con
cualquiera de los dos, y ese es su papel en la comparación.

## Limitación declarada: sesgo de selección

El dataset se construye exigiendo una tasa mínima de Conventional Commits por repo
(`config/repos.yaml` → `criterios_admision.tasa_prefijo_valido_minima`). Eso significa
que **el modelo se entrena y evalúa sobre proyectos que ya siguen una convención de
commits** — no sobre el caso de uso donde más falta haría (un repo sin convención). Es
una limitación intencional y documentada, no un descuido: sin una fuente de etiquetas
declarada por el autor no hay forma barata de conseguir 20-50k etiquetas. Por eso los
300 commits del techo humano (F3) se toman de **repos sin convención**, ajenos al
dataset de entrenamiento — ver `DESIGN.md` §4.1.

## CI

`.github/workflows/ci.yml` existe y corre `pytest` en cada push, pero **todavía no ha
ejecutado ni una vez**: la cuenta de GitHub está bloqueada por facturación (el mismo
problema que tiene parado el CI de `durable-kv`). Mientras tanto, la verificación es
local: `pytest -q` desde la raíz del repo, con el venv activado.

## Reproducir

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\pip install -r requirements-f4.txt   # solo para la F4/F5 (torch, transformers)
.\.venv\Scripts\pip install -e .
.\.venv\Scripts\pytest -q
```

Comandos del pipeline (`python -m ccls <subcomando>`, ver `src/ccls/cli.py`):

```powershell
python -m ccls discover-check          # verifica metadatos de los candidatos del piloto
python -m ccls pilot clone             # clona (bare, completo) los repos del piloto
python -m ccls pilot measure           # B2.1/B2.2/B2.4/B2.5
python -m ccls pilot clone-cost        # B2.3
python -m ccls pilot report            # escribe docs/PILOTO.md
python -m ccls f0 build                # extrae los f0_repos -> data/processed/
python -m ccls f0 stats                # escribe docs/F0_ESTADISTICAS.md
python -m ccls f1 run --modelo humo    # tres particiones x 5 semillas -> resultados/*.json
python -m ccls f1 fuga-aleatoria       # LEAKAGE.md §7.1 -> docs/F1_ETIQUETAS_ALEATORIAS.md
python -m ccls f2 run                  # los baselines de la F2 -> resultados/*.json
python -m ccls f1 run --modelo clasico_lr --barajar   # §7.1 sobre el clásico
python -m ccls f2 report               # escribe docs/F2_BASELINES.md
python -m ccls f4 run                  # F4: necesita requirements-f4.txt y GPU; reanudable (data/interim/f4_corridas)
```

Las particiones (DESIGN.md §5) y las semillas están en `config/experimentos.yaml`:
aleatoria 80/20 estratificada, con otra división por semilla; por repositorio, un
fold por repo; temporal, con corte global el 2025-06-01.

## Pruebas de fuga

Ver `LEAKAGE.md`. Tres pruebas corren hoy, y todas incluyen fixtures con fugas
plantadas a propósito para demostrar que **sí saben fallar**:

- `tests/test_prefix_leakage.py`: ningún `message` contiene el prefijo de Conventional
  Commits (`fix:`, `feat:`, también detrás de una viñeta) y ningún `diff` repite el
  mensaje del propio commit con su prefijo.
- `tests/test_fuga_correlacion.py`: ningún token candidato (`patch`, `minor`, rutas
  `.changeset/`, patrones de CHANGELOG…) predice una clase muy por encima de su
  frecuencia base, en el dataset entero ni dentro de un repo. Se mide por separado en
  commits "solo docs" y "no solo docs": un token solo cuenta como fuga si dice algo más
  que la regla estructural de `DESIGN.md` §6.1.
- `tests/test_experimento.py` (§7.1): con las etiquetas de entrenamiento barajadas, la
  exactitud no pasa la tasa de la clase mayoritaria en ningún fold. Un modelo que lee
  la etiqueta falla la prueba en cuanto el runner se la deja ver. **Sobre el dataset
  real pasa en 7 de 7 folds**: entre 0,9 y 3,7 puntos por debajo del techo del azar.

## Estructura

```
DESIGN.md                 documento de diseño completo
NO-GOALS.md               qué NO es este proyecto
LEAKAGE.md                las pruebas de fuga (§7.1 aleatoria, §7.2 prefijo, §7.3 correlación) y sus cifras
config/repos.yaml         criterios de admisión, candidatos del piloto, repos y parámetros de la F0
config/experimentos.yaml  semillas, particiones y criterio de la prueba de etiquetas aleatorias (F1)
src/ccls/                 paquete: gitutil, label, clone, discover, pilot, report, build, stats, fuga_correlacion,
                          particiones, metricas, modelos, experimento, f2, cli
tests/                    pytest — pruebas de fuga, parser de git log, construcción del dataset, particiones, runner
docs/PILOTO.md            resultados del piloto (Parte B), generado, no escrito a mano
docs/F0_ESTADISTICAS.md   estadísticas descriptivas del dataset, generado, no escrito a mano
docs/F1_ETIQUETAS_ALEATORIAS.md  prueba §7.1, generado, no escrito a mano
docs/F2_BASELINES.md      tablas de los baselines de la F2, generado, no escrito a mano
resultados/               un JSON por modelo × partición (corridas, resumen, versiones, manifest_sha256)
data/processed/           manifest.csv y dataset_meta.json en git; dataset.jsonl fuera
```
