# Correr la F5 en Google Colab

Guía escrita a mano. Es la de la F4 (`docs/COLAB_F4.md`) con otro comando: `f5 run` en
vez de `f4 run`, y su propio caché en Drive. Lo que allí se explica (por qué no se
reinstala torch, qué hacer si Colab se desconecta) vale igual aquí.

**Costo, estimado y no medido:** la F5 entrena las 12 capas y la F4 solo 2, así que cada
ajuste debería tardar entre 2 y 3 veces lo que tardó en la F4 (2,3 min en una T4): unos 5 a
7 minutos. Son 70 ajustes (35 con etiquetas de verdad y 35 barajadas), o sea **6 a 8 horas
de T4**, repartidas en varias sesiones: el caché en Drive hace que cada sesión retome donde
quedó la anterior. La primera celda de la parte 2 sirve para medir el costo de verdad.

## 1 · Preparar la sesión (cada vez que abras Colab)

Entorno de ejecución → Cambiar tipo de entorno de ejecución → **T4 GPU**. Después:

```python
from google.colab import drive
drive.mount('/content/drive')

!git clone -q https://github.com/jsav2003/commit-type-classifier.git /content/commit-type-classifier
%cd /content/commit-type-classifier
!mkdir -p data/processed
!cp /content/drive/MyDrive/ccls/dataset.jsonl data/processed/
!pip install -q -r requirements.txt transformers==4.57.6
!pip install -q -e .

!sha256sum data/processed/dataset.jsonl
!grep dataset_jsonl_sha256 data/processed/dataset_meta.json
```

Los dos hashes tienen que ser iguales (`797b73e4…`). Los errores de pip sobre `bigframes`,
`datasets`, `diffusers` o `gradio` no importan: son librerías de Colab que el proyecto no
usa.

## 2 · Correr, en este orden

Cada línea en su propia celda. **Siempre con `--cache` apuntando a Drive.**

```python
CACHE = "/content/drive/MyDrive/ccls/f5_corridas"
!python -m ccls f5 run --particion aleatoria --cache {CACHE}
```

Son 5 ajustes: anota cuánto tardó la celda y divídelo entre 5. Con eso se sabe cuánto
cuesta el resto.

```python
!python -m ccls f5 run --particion aleatoria --barajar --cache {CACHE}
```

La prueba de etiquetas aleatorias (LEAKAGE.md §7.1), antes que el resto. **Si da
`exactitud` por encima de `mayoritaria` en más de 2 puntos, para y avisa.** Si la red no
aprende nada ni siquiera con las etiquetas de verdad, la prueba saldrá "no concluyente":
eso no es un fallo, es un resultado posible de la F5.

```python
!python -m ccls f5 run --particion repositorio --cache {CACHE}
!python -m ccls f5 run --particion temporal --cache {CACHE}
```

`repositorio` es la principal y la más larga (25 ajustes, unas 2 a 3 horas).

```python
!python -m ccls f5 run --particion repositorio --barajar --cache {CACHE}
!python -m ccls f5 run --particion temporal --barajar --cache {CACHE}
```

Si Colab se desconecta a mitad: vuelve a la parte 1 y relanza la misma celda. Lo ya hecho
se salta.

## 3 · Traer los resultados

Al final de **cada** sesión, antes de cerrar:

```python
!cp resultados/f5_desde_cero__*.json /content/drive/MyDrive/ccls/
```

De Drive, descarga los `f5_desde_cero__*.json` (o la carpeta `ccls` entera: Drive la baja
como zip, y está bien) y déjalos en `Descargas`.

## Si algo sale raro

- **Sin memoria de GPU (`CUDA out of memory`):** la F5 guarda para el entrenamiento las
  12 capas y la F4 solo 2, así que es posible. **No cambies nada en `config/f5.yaml`**:
  bajar el lote cambia la huella y rompe la regla de que la F5 tiene los hiperparámetros de
  la F4 (hay un test). Para y avisa.
- **Todos los ajustes predicen casi una sola clase:** puede pasar con una red al azar
  entrenada 3 épocas. Es un resultado, no un error de la guía. No se retoca nada.
