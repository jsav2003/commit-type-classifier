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
| F0 · Recolección de datos | **dataset construido** (10.000 commits, reproducible byte a byte); **sin cerrar**: la prueba de fuga por correlación falla en los CHANGELOG de angular-cli, decisión pendiente (`LEAKAGE.md` §7.3) |
| F1-F6 | no empezadas |

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
```

## Pruebas de fuga

Ver `LEAKAGE.md`. Dos pruebas corren hoy, y las dos incluyen fixtures con fugas
plantadas a propósito para demostrar que **sí saben fallar**:

- `tests/test_prefix_leakage.py`: ningún `message` contiene el prefijo de Conventional
  Commits (`fix:`, `feat:`, también detrás de una viñeta) y ningún `diff` repite el
  mensaje del propio commit con su prefijo.
- `tests/test_fuga_correlacion.py`: ningún token candidato (`patch`, `minor`, rutas
  `.changeset/`, patrones de CHANGELOG…) predice una clase muy por encima de su
  frecuencia base, en el dataset entero ni dentro de un repo.

## Estructura

```
DESIGN.md                 documento de diseño completo
NO-GOALS.md               qué NO es este proyecto
LEAKAGE.md                las pruebas de fuga (§7.1 aleatoria, §7.2 prefijo, §7.3 correlación) y sus cifras
config/repos.yaml         criterios de admisión, candidatos del piloto, repos y parámetros de la F0
src/ccls/                 paquete: gitutil, label, clone, discover, pilot, report, build, stats, fuga_correlacion, cli
tests/                    pytest — pruebas de fuga, parser de git log, construcción del dataset
docs/PILOTO.md            resultados del piloto (Parte B), generado, no escrito a mano
docs/F0_ESTADISTICAS.md   estadísticas descriptivas del dataset, generado, no escrito a mano
data/processed/           manifest.csv y dataset_meta.json en git; dataset.jsonl fuera
```
