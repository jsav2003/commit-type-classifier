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
| Piloto (mide 5 supuestos del diseño antes de comprometerse a la F0) | en curso |
| F0 · Recolección de datos | pendiente del resultado del piloto |
| F1-F6 | no empezadas |

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
```

## Prueba de fuga del prefijo

`tests/test_prefix_leakage.py` verifica que ningún texto de entrada al modelo
contiene el prefijo de Conventional Commits usado para etiquetar (`fix:`, `feat:`,
etc.) ni sus variantes. El test incluye un fixture con fugas plantadas a propósito
para demostrar que **sí sabe fallar** cuando corresponde — ver `LEAKAGE.md`.

## Estructura

```
DESIGN.md              documento de diseño completo
NO-GOALS.md             qué NO es este proyecto
LEAKAGE.md              las dos pruebas de fuga (§7.1 aleatoria, §7.2 prefijo) y su estado
config/repos.yaml       criterios de selección de repos + candidatos del piloto
src/ccls/               paquete: gitutil, label, clone, discover, pilot, report, cli
tests/                  pytest — incluye el test de fuga y el parser de git log
docs/PILOTO.md          resultados del piloto (Parte B), generado, no escrito a mano
data/                   crudo/intermedio/procesado — ignorado por git salvo el manifiesto
```
