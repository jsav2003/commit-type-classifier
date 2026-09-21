# Clasificación automática de commits por tipo de cambio

Documento de diseño. Escrito antes del código, a propósito.

---

## 1. Qué es este proyecto

Un sistema que recibe un commit de un repositorio Git y decide qué tipo de cambio es:
**arreglo de bug, funcionalidad nueva, refactorización o documentación**.

El objetivo real no es el clasificador. Es demostrar, con evidencia, cuál de tres
enfoques funciona mejor y por qué:

1. Un modelo clásico de machine learning sobre características calculadas a mano.
2. Un modelo de deep learning preentrenado sobre código, ajustado con transfer
   learning.
3. Una red entrenada desde cero, sin conocimiento previo.

El resultado interesante puede ser que el clásico gane. Si ocurre, se reporta. Ese es
el punto del proyecto.

## 2. Qué NO es

Ver [`NO-GOALS.md`](NO-GOALS.md).

## 3. Por qué este problema

**Los datos son gratis e ilimitados.** GitHub expone millones de commits públicos con
su mensaje y su diff. No hay que salir a recolectar ni etiquetar a mano durante
semanas.

**El dominio se entiende.** Puedes leer un commit y juzgar tú mismo si el modelo se
equivocó. En un problema médico o de sensores, no podrías.

**Tiene una dificultad real y nombrable:** las etiquetas están sucias. Un mensaje que
dice `fix` no siempre arregla un bug, y un commit puede hacer tres cosas a la vez.
Trabajar con etiquetas ruidosas y aun así defender los resultados es el núcleo del
trabajo.

**Permite comparar las tres capas.** Machine learning clásico y deep learning sobre el
mismo problema, con la misma partición y las mismas métricas.

## 4. Los datos

### 4.1 De dónde salen

Repositorios públicos de GitHub, seleccionados con criterios explícitos: proyectos
activos, con historial largo, de varios lenguajes, y que **usen convenciones de commit
verificables**.

Meta: entre 20.000 y 50.000 commits. Más no aporta y complica el manejo.

**Decisión tras el piloto (2026-09-14): 5 repos, ~10.000 commits.** La meta de arriba
es la del diseño original y se deja tal como estaba escrita. El piloto dejó 5 repos
admitidos, todos TS/JS, y se decidió no buscar más. La limitación del dataset es la
diversidad de ecosistema, no el tamaño, y una tercera ola del único perfil que pasa el
umbral (TS/JS con `commitlint`) la empeoraría. Lo de "varios lenguajes" tampoco se
cumple, y se declara. El razonamiento completo está en el README ("Limitación
principal") y la lista fijada, en `config/repos.yaml` → `f0_repos`.

**Sesgo de selección, declarado.** Exigir una tasa alta de Conventional Commits para
admitir un repo significa que el dataset entero está hecho de proyectos que ya siguen
esa convención. El uso real de un clasificador de este tipo sería precisamente en
repos que **no** la siguen — si ya la siguieran, no haría falta clasificar nada. Esto
es una limitación del proyecto, no un detalle menor, y se reporta como tal en el
`README.md`.

**Consecuencia para el techo humano (F3):** los 300 commits etiquetados a mano para la
F3 deben salir de repositorios **sin** convención de commits, ajenos al dataset de
entrenamiento. Si salieran del mismo conjunto de repos con convención, el techo humano
mediría el acuerdo dentro del sesgo de selección, no el acuerdo sobre la tarea en
general. Ver también §5 del `docs/PILOTO.md` cuando exista.

### 4.2 De dónde salen las etiquetas

Aquí está la decisión más importante del proyecto.

**Fuente principal — Conventional Commits.** Muchos proyectos serios exigen que el
mensaje empiece con un prefijo: `fix:`, `feat:`, `refactor:`, `docs:`. Eso da una
etiqueta declarada por el propio autor, sin que nadie tenga que etiquetar a mano.

**El problema de esa fuente:** es exactamente la parte del texto que el modelo podría
usar para hacer trampa. Si el mensaje dice `fix: corrige el login` y le entregas el
mensaje completo, el modelo aprende a leer el prefijo y nada más. Obtendría 99% y no
significaría nada.

**La solución, y es obligatoria:** el prefijo se usa para etiquetar, y después **se
elimina del texto de entrada**. El modelo ve `corrige el login` y el diff, nunca la
etiqueta. Esto se verifica con un test automático que busca el prefijo en cualquier
entrada del dataset.

**Conjunto de validación humana.** 300 commits etiquetados a mano por ti, sin mirar el
prefijo, **tomados de repos sin convención de commits** (ver §4.1), para medir dos
cosas: qué tan de acuerdo estás con la etiqueta declarada en proyectos que sí la usan
(comparando contra una muestra equivalente del dataset), y si el modelo se parece más
al humano o al prefijo. Esto establece el **techo realista**: si tú y el autor solo
coinciden el 80% de las veces, ningún modelo debería reportar 95% sin levantar
sospechas.

**Cómo queda resuelta la contradicción entre §4.1 y §7.5: dos estratos.** _(Decidido el
2026-09-20, al abrir la F3, antes de etiquetar nada.)_ §4.1 pide commits de repos sin
convención; §7.5 define el techo como el acuerdo con la etiqueta declarada, que solo
existe donde hay convención. Sobre una misma muestra no se pueden cumplir las dos. La
muestra de 300 tiene dos estratos de 150, mezclados en un solo orden para que quien
etiqueta no sepa cuál mira:

- **A · sin convención.** Commits sin prefijo válido de los cuatro repos que el piloto
  rechazó por tasa baja (`config/repos.yaml` → `f3_repos`: poetry, rustfmt, cobra, hcl).
  Mide el acuerdo humano ↔ modelo en el caso de uso real. No hay etiqueta declarada.
- **B · con convención.** Commits del dataset de la F0, con el prefijo ya quitado, por
  cuotas de clase (40 `fix` / 35 `feat` / 40 `refactor` / 35 `docs`) porque la
  proporción real dejaría ~12 `refactor`. Mide el techo: acuerdo humano ↔ etiqueta
  declarada, reponderado a las proporciones reales del dataset.

Se añaden 50 ítems repetidos, sin avisar, para medir el acuerdo del anotador consigo
mismo. El anotador ve las entradas de §4.3 y nada más (no el texto del diff, que el
modelo de la F2 tampoco ve), con una opción `?` cuyo uso se reporta. La hoja que lee la
herramienta de etiquetado no contiene la etiqueta declarada, ni el repo, ni el SHA.
Limitación declarada: las rutas de archivo delatan el proyecto, así que el estrato no
queda ciego del todo; lo que queda ciego es la etiqueta.

### 4.3 Entradas del modelo

Por cada commit:

- **Mensaje**, sin el prefijo de convención.
- **Diff**: líneas agregadas y eliminadas, truncado a un límite fijo.
- **Metadatos**: número de archivos tocados, líneas agregadas/eliminadas, extensiones
  de los archivos, si toca tests, si toca documentación.

### 4.4 Balance de clases esperado: `refactor` es escasa

_Añadido el 2026-09-14, después del piloto y antes de extraer el dataset._

Proyección con la proporción de cada clase en los últimos 1.000 commits
`--no-merges --first-parent` de cada repo admitido (`docs/PILOTO.md`, B2.2),
escalada al tope de 2.000 commits por repo:

| repo | `refactor` en la muestra del piloto | % | proyectados sobre 2.000 |
|---|---:|---:|---:|
| angular/angular-cli | 172 / 525 | 32,8% | ~655 |
| nuxt/nuxt | 53 / 604 | 8,8% | ~175 |
| vitejs/vite | 49 / 642 | 7,6% | ~153 |
| vitest-dev/vitest | 36 / 693 | 5,2% | ~104 |
| sveltejs/svelte | 1 / 575 | 0,2% | ~3 |
| **total** | **311 / 3.039** | **10,2%** | **~1.090** |

(El 9,6% que aparece en la distribución agregada de `docs/PILOTO.md` incluye los
10 candidatos, admitidos o no; con los 5 admitidos y el tope por repo son ~1.090.)

Lo que la F2 tiene que saber antes de empezar:

1. **`refactor` es la clase minoritaria, con ~1.090 ejemplos esperados.** Desde el
   primer experimento se reporta F1 por clase (§7.4), no solo exactitud ni F1 macro, y
   se considera reponderar (riesgo de §9). Si se repondera, la decisión se documenta
   con el número delante. **Decidido el 2026-09-18, en la F2: se repondera.** Con
   `class_weight="balanced"`, el F1 de `refactor` sube en 6 de los 7 folds —
   +26,8 puntos en angular-cli (0,286 → 0,554), +14,0 en la temporal, +11,3 en vite,
   +8,7 en vitest— y baja solo en nuxt (-4,1). El F1 macro sube en 6 de 7 y la
   exactitud baja en 6 de 7. Por §7.4 este proyecto mira el F1 por clase antes que la
   exactitud, así que el clásico de referencia es `clasico_lr_balanceado`; el no
   reponderado se sigue reportando al lado. (Una de esas 6 mejoras es el fold de
   svelte, con 1 solo `refactor` en prueba, y por §5 ahí la diferencia no significa
   nada: se cuenta y se declara, no se esconde.)
2. **svelte no aporta casi ningún `refactor`.** Su 0,2% refleja la costumbre del
   proyecto al etiquetar, no que no refactorice. En la partición por repositorio, un
   fold con svelte en prueba tiene un F1 de `refactor` indefinido o puro ruido: se
   reporta así, no se promedia a ciegas con los demás.
3. **angular-cli aporta ~60% de todos los `refactor`.** En la partición por
   repositorio, el fold que la deja en prueba entrena con ~435 `refactor`; el que la
   deja en entrenamiento evalúa `refactor` casi solo sobre nuxt, vite y vitest. El F1
   de `refactor` va a depender mucho de dónde cae angular-cli, y por eso se reporta
   por fold.
4. **Es una proyección, no una medición.** La muestra del piloto son commits
   recientes; la extracción real es estratificada por trimestre a lo largo de todo el
   historial, y la proporción puede moverse. Las estadísticas descriptivas de la F0
   reemplazan esta tabla por el número real. **Número real: 820 `refactor` (8,2%);
   angular-cli aporta 468 (57%) y svelte 1** (`docs/F0_ESTADISTICAS.md` §2).

## 5. Las particiones

Aquí se juega la honestidad del proyecto. Tres particiones, de menos a más exigente:

| Partición | Cómo se separa | Qué mide |
|---|---|---|
| **Aleatoria** | Commits al azar | Poco: la referencia optimista que reportan casi todos |
| **Por repositorio** | Repos completos en entrenamiento o en prueba, nunca en ambos | Si funciona en un proyecto que nunca vio |
| **Temporal** | Entrena con commits anteriores a una fecha, evalúa con posteriores | Si funciona con código y convenciones futuras |

**La partición aleatoria fuga información.** Commits del mismo repositorio comparten
estilo de mensaje, autores y nombres de funciones. El modelo memoriza el proyecto, no
aprende la tarea. Se reporta igual, precisamente para mostrar cuánto se infla el
número frente a las otras dos.

**La partición por repositorio es la principal.** Es la que responde a la pregunta
real: ¿sirve esto en un proyecto nuevo?

**La partición temporal exige historial completo por repo.** El tope de commits por
repo (§4.1, ver `config/repos.yaml`) se reparte por muestreo estratificado a lo largo
de todo el historial disponible, no tomando los commits más recientes — de lo
contrario no queda historial "antiguo" con el que entrenar la partición temporal.

**svelte solo cubre 2023-2026.** _(Añadido el 2026-09-14, con el dataset de la F0.)_
svelte adoptó Conventional Commits en 2023: su tasa de prefijo es de 0-7% por año
hasta 2022 y de 52-59% desde 2023. Como el muestreo es proporcional a los commits
etiquetables de cada trimestre, 1.952 de sus 2.000 commits son de 2023 en adelante
(`docs/F0_ESTADISTICAS.md` §3). En la partición temporal, svelte no aporta nada a la
parte antigua: con un corte anterior a 2023, prácticamente todo svelte cae en prueba.
Se dice así en cada tabla de la partición temporal. El criterio de admisión no se
cambió por esto (ver `config/repos.yaml`, cómo se mide `tasa_prefijo_valido_minima`).

**`refactor` se reporta fold por fold, nunca como promedio entre folds.** svelte
aporta 2.000 commits y 1 solo `refactor`; angular-cli aporta 468 de los 820 (57%). En
la partición por repositorio hay folds donde `refactor` prácticamente no existe en
prueba, y un F1 calculado sobre 1 ejemplo no es una métrica: promediarlo con los
demás folds contamina el número. Regla, fijada antes de la F2: en la partición por
repositorio, el F1 de `refactor` va en una fila por fold, con el número de ejemplos de
`refactor` en prueba al lado, y no hay fila de promedio para esa clase. Cualquier
otra clase que quede con muy pocos ejemplos en un fold recibe el mismo trato.

**Cómo quedan implementadas.** _(Fijado el 2026-09-15, en la F1, antes de entrenar
ningún modelo. Código en `src/ccls/particiones.py`, parámetros en
`config/experimentos.yaml`.)_

- **Aleatoria:** 80/20 estratificada por clase. Cada una de las cinco semillas da
  **otra división**, así que el intervalo incluye la varianza de la división y no solo
  la del modelo.
- **Por repositorio:** 5 folds, uno por repo, con ese repo entero en prueba (2.000
  commits cada uno). La división no depende de la semilla. El fold de svelte tiene
  1 solo `refactor` en prueba.
- **Temporal:** un corte **global** el `2025-06-01T00:00:00+00:00` (percentil 80 de
  la fecha de commit), no uno por repo. Con un corte por repo, commits de 2026 de un
  proyecto entrenarían un modelo que se evalúa con commits de 2025 de otro. Quedan
  7.999 commits en entrenamiento y 2.001 en prueba, y **los 5 repos quedan a los dos
  lados** (svelte: 1.483 / 517), porque el corte cae después de su adopción de la
  convención. `refactor`: 644 / 176. La fecha se fija literal, no como cuantil, para
  que el corte no se mueva solo si el dataset cambia.
- El azar de las divisiones y de las etiquetas barajadas sale de sha256, igual que el
  muestreo de la F0: no depende de la versión de Python ni de numpy.
- **Intervalos:** t de Student al 95% sobre las semillas. El resumen agrega semillas
  dentro de cada fold y **nunca folds entre sí**.
- El modelo recibe solo las entradas de §4.3 (`experimento.ENTRADAS`). El runner le
  quita la etiqueta, el repo, el SHA, las fechas y la auditoría antes de entregarle
  los registros.

## 6. Los modelos

### 6.1 Baseline trivial

Predecir siempre la clase más frecuente. Si el 45% de los commits son `fix`, eso da
45%. **Todo modelo debe superarlo o no sirve para nada.** Suena obvio y es el número
que más papers omiten.

**Baseline por clase para `docs`.** Además del baseline trivial global, se mide una
regla de una línea: "si todos los archivos tocados son `.md`/`.rst`/`.txt` → `docs`".
Si esa regla sola obtiene un F1 alto en la clase `docs`, significa que esa clase es
casi trivial de acertar por una señal estructural, y cualquier modelo que reporte un
buen F1 macro puede estar inflado por esa clase sin que haya aprendizaje real sobre
las demás. Se reporta junto al baseline trivial.

### 6.2 Machine learning clásico

Características calculadas a mano:

- Del mensaje: TF-IDF sobre palabras y n-gramas, longitud, presencia de verbos típicos.
- Del diff: líneas agregadas y eliminadas, proporción entre ambas, número de archivos.
- De los archivos: extensiones, si toca tests, si toca `README` o `docs/`.

Modelos: regresión logística y gradient boosting.

**Aquí tú eliges qué mirar.** Esa es la definición del enfoque clásico, y hay que
decirlo así en el informe.

**Qué mira, en concreto.** _(Fijado el 2026-09-18, en la F2. Código en
`src/ccls/modelos.py`, función `rasgos`; resultados en `docs/F2_BASELINES.md`.)_

- **Del mensaje:** TF-IDF de palabras y bigramas (`min_df=2`, `sublinear_tf`), la
  longitud, y una lista de 22 verbos típicos fijada **a priori** con vocabulario
  general de mensajes de commit. No se escogió midiendo sobre el dataset: ajustarla
  después de ver el resultado sería elegir el rasgo con el número delante.
- **Del diff:** líneas agregadas y eliminadas (en logaritmo), la proporción entre
  ambas, número de archivos y de binarios. **El texto del diff no entra en la F2.** No
  es por costo: la prueba de correlación de §7.3 se midió sobre el mensaje y los
  archivos, y meterle el texto del diff al modelo obliga a volver a correrla sobre sus
  tokens antes de creerle a los números. Queda declarado como pendiente, no omitido.
- **De los archivos:** el conjunto de extensiones, si toca tests, si toca
  documentación, y la regla de §6.1 ("todos los archivos son `.md`/`.rst`/`.txt`") como
  rasgo explícito — el conjunto de extensiones sabe decir "hay alguna `.md`", no "todas
  son `.md`".

**El texto del diff no entra en la F4 de entrada.** _(Decidido el 2026-09-21, antes de
empezar la F4.)_ La F4 se mide con las mismas entradas que la F2 (`experimento.ENTRADAS`),
para que la comparación clásico ↔ transfer learning sea limpia: si además cambian las
entradas, una diferencia entre los dos no se sabe de dónde viene. El dato con número
delante es la §5 de `docs/F3_TECHO_LLM.md`: el anotador, viendo lo mismo que el modelo,
pidió ver el diff en el **6,7%** de los ítems, en los dos estratos. Si la F4 se queda
corta, se repite primero la prueba de correlación de §7.3 sobre los tokens del diff y solo
entonces se añade, como ablación declarada y no como cambio de las entradas base.

**`tiene_referencia_issue` no entra.** _(Decidido el 2026-09-18.)_ La bandera se
calculó en la F0 y se dejó fuera de `experimento.ENTRADAS` a propósito, para decidir en
la F2 con el número delante. Medida como ablación (`clasico_lr_issue`), mueve el F1
macro entre -0,67 y +0,99 puntos según el fold, con el signo cambiado entre unos y
otros: no aporta. La razón de fondo es anterior al número y es la que vale: el patrón
que la calcula exige una de las palabras `close`/`fix`/`resolve` pegada a la
referencia, y el TF-IDF del mensaje ya las ve. No es información nueva, es el mensaje
reempaquetado — y construido sobre el nombre de una de las cuatro clases. Se queda en
el dataset como metadato y fuera de las entradas.

### 6.3 Deep learning con transfer learning

Un modelo preentrenado sobre código (familia CodeBERT / CodeT5 o similar), ajustado
con tus datos. Solo se reentrenan las últimas capas.

**Aquí el modelo elige qué mirar.** Ya sabe qué es una función, una variable, una
condición, porque lo aprendió de millones de archivos. Tú solo le enseñas la tarea
específica.

Cabe en una GPU gratuita de Colab. Es la razón por la que el proyecto es viable.

### 6.4 Red desde cero

La misma arquitectura, sin pesos preentrenados. **Probablemente pierda**, y esa es la
demostración empírica de por qué existe el transfer learning. Un resultado negativo,
bien medido, es un resultado.

## 7. Cómo se demuestra que los resultados son reales

Esta sección es el proyecto. Sin ella queda un notebook más.

### 7.1 Prueba de fuga por etiquetas aleatorias

Se entrena todo el montaje con las etiquetas barajadas al azar. **Debe dar el
resultado del azar.** Si da más, hay fuga en alguna parte y el resto de los números no
valen nada. Se corre antes que cualquier experimento y se reporta en el README.

### 7.2 Prueba de fuga del prefijo

Test automático que verifica que ninguna entrada del dataset contiene el prefijo de
convención ni ninguna de sus variantes.

### 7.3 Repeticiones e intervalos de confianza

Cada configuración se entrena con **cinco semillas distintas**. Se reporta media e
intervalo de confianza, nunca el mejor resultado. Una diferencia de dos puntos entre
modelos no significa nada si los intervalos se superponen, y hay que decirlo
explícitamente cuando ocurre.

### 7.4 Métricas por clase, no solo exactitud

Matriz de confusión completa y F1 por clase. Con clases desbalanceadas, la exactitud
esconde que una clase colapsó por completo. Un modelo con 85% de exactitud que nunca
predice `refactor` es un modelo roto.

### 7.5 Techo humano

El conjunto de 300 commits etiquetados a mano fija el techo. Si tu acuerdo con la
etiqueta declarada es del 78%, un modelo que reporta 92% está aprendiendo algo
distinto de la tarea, y hay que investigarlo.

**Qué muestra mide qué.** _(Fijado el 2026-09-20, en la F3.)_ El techo es el acuerdo
humano ↔ etiqueta declarada **del estrato B** (§4.2). El estrato A no tiene etiqueta
declarada y no entra en el techo: sirve para medir cuánto se parece el modelo al humano
fuera de la convención. Los dos estratos no se promedian entre sí en ninguna tabla. Un
techo bajo es un resultado, no un fallo (§9): no se re-muestrea ni se ajusta nada
después de ver la cifra.

**Sin tiempo para etiquetar a mano: anotador LLM provisional.** _(Decidido el 2026-09-20,
después de fijar la muestra y antes de calcular ningún número.)_ Las 350 etiquetas de la
muestra las puso un modelo de lenguaje (Claude), en una sola pasada, leyendo solo la hoja
ciega —sin la etiqueta declarada, el repo ni las predicciones— y con un criterio fijado
por escrito en el reporte. El resultado es `docs/F3_TECHO_LLM.md` y se llama **techo del
anotador LLM**, no techo humano: no dice cuánto coincidiría una persona, y un LLM puede
parecerse más al autor de la etiqueta que una persona, así que tiende a sobrestimarlo.
Las 50 repeticiones se etiquetaron en el mismo contexto que las originales, por lo que su
acuerdo consigo mismo no es comparable con el de una persona. **La F3 no queda cerrada:**
la herramienta humana (`python -m ccls f3 label`) sigue lista y el techo humano sigue
pendiente. Todo resultado que dependa de este número lo cita como anotador LLM.

### 7.6 Análisis de errores

Revisión manual de al menos 50 commits mal clasificados, agrupados por causa:
etiqueta incorrecta del autor, commit genuinamente mixto, mensaje inútil, o error real
del modelo. **Esta sección es la que más comunica competencia**, porque demuestra que
miraste los datos y no solo las métricas.

### 7.7 Reproducibilidad

Un comando reproduce cada tabla del informe. Versiones fijadas, semillas fijadas,
dataset versionado.

## 8. Plan por fases

Presupuesto: 4-5 horas semanales durante 18-20 semanas ≈ 78 horas.

| Fase | Horas | Terminada cuando |
|---|---|---|
| F0 · Recolección de datos | 14 | Dataset de 20-50k commits, limpio, versionado, con estadísticas descriptivas |
| F1 · Infraestructura de experimentos | 10 | Un comando entrena, evalúa y guarda resultados; las tres particiones implementadas |
| F2 · Baselines | 10 | Trivial y clásico funcionando, con intervalos de confianza |
| F3 · Etiquetado humano | 8 | 300 commits etiquetados y calculado el acuerdo con las etiquetas declaradas |
| F4 · Transfer learning | 16 | Modelo preentrenado ajustado, comparado con el clásico en las tres particiones |
| F5 · Red desde cero | 8 | Entrenada y medida, gane o pierda |
| F6 · Análisis de errores e informe | 12 | 50 errores categorizados, todas las tablas reproducibles, README escrito |

### Reglas de rescate

- Si la F0 se complica (límites de la API de GitHub, repos sin convenciones), se
  reduce a 10.000 commits de menos repositorios. Peor dataset, mismo proyecto.
- Si la F4 no cabe en la GPU gratuita, se usa un modelo preentrenado más pequeño o
  solo el mensaje sin diff. Se documenta la limitación.
- La F3 y la F6 no se recortan. Sin el techo humano y sin el análisis de errores, el
  proyecto pierde exactamente lo que lo distingue.

## 9. Riesgos

| Riesgo | Mitigación |
|---|---|
| Fuga por el prefijo de convención | Test automático desde el día uno, antes de entrenar nada |
| Etiquetas demasiado ruidosas para aprender algo | El conjunto humano lo revela en la F3, a las 32 horas, no al final |
| Clases muy desbalanceadas | Reportar F1 por clase y considerar reponderar, documentando la decisión. `refactor` ya se sabe escasa y concentrada en angular-cli (§4.4) |
| Dataset de un solo ecosistema (5 repos TS/JS, 3 de la misma comunidad) | Declarado como limitación principal en el README; la partición por repositorio se reporta como generalización dentro del ecosistema, no a proyectos nuevos en general |
| Etiqueta filtrada por correlación, sin que el prefijo aparezca (los `.changeset` de svelte: `patch` va con `fix` en 1.309 de 1.315 casos) | Prueba de distribución por clase sobre tokens candidatos, medida por separado en commits "solo docs" y "no solo docs" para no confundir la fuga con la señal estructural de §6.1 (LEAKAGE.md §7.3); `.changeset/` excluido de todas las entradas |
| Prefijo filtrado por el cuerpo del mensaje (los squash-merge copian `* feat: ...` de la rama) | Detectado antes de la F0 (29% de los cuerpos de svelte); la limpieza y el test de fuga cubren líneas con viñeta, con fixtures plantados (LEAKAGE.md) |
| Tentación de reportar solo el mejor número | Las cinco semillas y los intervalos están en la infraestructura desde la F1 |
| Límites de la API de GitHub | Recolección por clonado local (`git log`), no por API; la API solo se usa para descubrir repos candidatos |
| Sesgo de selección por exigir convención de commits | Declarado en el README; el techo humano (F3) se mide sobre repos sin convención, ajenos al dataset |
| Merges que ocultan commits etiquetables (`--no-merges --first-parent` puede vaciar un repo sin squash-merge) | Medido en el piloto (`docs/PILOTO.md`); repos por encima del 80% de pérdida se sacan o usan el merge como unidad |
| Ventana temporal sesgada por tomar los commits más recientes | Muestreo estratificado a lo largo del historial completo, nunca `--shallow-since` |

## 10. Qué queda en el repositorio

- El código de recolección, entrenamiento y evaluación.
- El dataset versionado, o el script exacto que lo reconstruye.
- `DESIGN.md` — este documento.
- `RESULTS.md` — las tablas: tres particiones × cuatro enfoques × cinco semillas, con
  intervalos de confianza y matrices de confusión.
- `ERROR-ANALYSIS.md` — los 50 errores revisados, agrupados por causa.
- `LEAKAGE.md` — la prueba de etiquetas aleatorias y la del prefijo, con sus
  resultados.
- `NO-GOALS.md` — los límites.
- Un comando que reproduce todo.

## 11. Qué comunica este repo

A alguien que lo abra sin leerlo entero:

1. Una tabla mostrando que la partición aleatoria infla el resultado frente a la
   partición por repositorio. Eso solo ya demuestra que entiendes el problema de la
   fuga de datos.
2. El techo humano al lado de los números del modelo.
3. La sección de análisis de errores, que prueba que miraste los datos.
4. Intervalos de confianza en cada número.

Cualquiera con experiencia reconoce esas cuatro cosas de inmediato, porque son
exactamente las que faltan en la mayoría de proyectos de machine learning.

## 12. Glosario

- **Commit:** un cambio guardado en el historial de un repositorio, con mensaje y
  diff.
- **Diff:** las líneas exactas que un commit agregó y eliminó.
- **Conventional Commits:** convención donde el mensaje empieza con `fix:`, `feat:`,
  `refactor:`, `docs:`.
- **Fuga de datos (leakage):** cuando el modelo accede a información que no tendría en
  uso real, inflando las métricas.
- **Transfer learning:** partir de un modelo ya entrenado en otra tarea y ajustar solo
  la parte final con tus datos.
- **TF-IDF:** forma de convertir texto en números que pondera las palabras según lo
  distintivas que sean.
- **F1 por clase:** métrica que combina precisión y cobertura, calculada por separado
  para cada categoría.
- **Baseline trivial:** predecir siempre la clase más común. El piso que todo modelo
  debe superar.
