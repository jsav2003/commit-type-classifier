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

### 4.3 Entradas del modelo

Por cada commit:

- **Mensaje**, sin el prefijo de convención.
- **Diff**: líneas agregadas y eliminadas, truncado a un límite fijo.
- **Metadatos**: número de archivos tocados, líneas agregadas/eliminadas, extensiones
  de los archivos, si toca tests, si toca documentación.

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
| Clases muy desbalanceadas | Reportar F1 por clase y considerar reponderar, documentando la decisión |
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
