# Correr la F4 en Google Colab

Guía escrita a mano (los demás `docs/F*_*.md` son generados). Es la parte de la F4 que no
se puede hacer en esta máquina: no tiene GPU. En CPU CodeBERT tarda ~1 s por ejemplo; una
corrida completa serían días.

**Costo, estimado y no medido en GPU:** 35 ajustes por modelo (1 aleatoria + 5 folds por
repositorio + 1 temporal, cada uno con 5 semillas), unas 4 a 7 horas de T4 en total. La
primera corrida (paso 5) sirve para medirlo de verdad antes de comprometerse.

## 0 · Antes de salir de esta máquina

Tu rama local va por delante de `origin/main` y Colab clona de ahí. Sube los commits:

```powershell
git push
```

Si el repo es privado, Colab necesita un token: usa
`git clone https://<usuario>:<token>@github.com/jsav2003/commit-type-classifier.git`.
Si prefieres no subirlo, comprime la carpeta sin `.venv`, `data/raw` ni `data/interim` y
súbela a Drive.

El dataset **no está en git** (`data/processed/*.jsonl`): sube
`data/processed/dataset.jsonl` (57 MB) a Google Drive, por ejemplo a
`MyDrive/ccls/dataset.jsonl`.

## 1 · Abrir Colab con GPU

Entorno de ejecución → Cambiar tipo de entorno → **GPU (T4)**. Comprueba:

```python
!nvidia-smi | head -12
```

## 2 · Montar Drive y clonar

```python
from google.colab import drive
drive.mount('/content/drive')
```

```python
!git clone https://github.com/jsav2003/commit-type-classifier.git
%cd commit-type-classifier
!mkdir -p data/processed
!cp /content/drive/MyDrive/ccls/dataset.jsonl data/processed/
```

## 3 · Instalar

**No reinstales torch**: Colab ya trae uno con CUDA y `requirements-f4.txt` fija el de
esta máquina (CPU). Instala solo lo demás:

```python
!pip install -q -r requirements.txt transformers==4.57.6
!pip install -q -e .
```

Si pip cambia numpy y Colab lo pide, reinicia el entorno de ejecución y vuelve a este paso.

## 4 · Comprobar que es el mismo dataset

```python
!sha256sum data/processed/dataset.jsonl
!grep dataset_jsonl_sha256 data/processed/dataset_meta.json
```

Los dos hashes tienen que ser iguales (`797b73e4…`). Si no lo son, el archivo subido no es
el de la F0 y ningún número de la F4 sería comparable con la F2.

## 5 · Primera corrida: la partición aleatoria, para medir el costo

```python
CACHE = "/content/drive/MyDrive/ccls/f4_corridas"
!python -m ccls f4 run --particion aleatoria --cache {CACHE}
```

**Siempre con `--cache` apuntando a Drive.** Cada (semilla, fold) se guarda al terminar; si
Colab se desconecta, vuelves a lanzar el mismo comando y retoma donde quedó. Sin eso, se
pierde todo lo hecho en la sesión.

Anota cuánto tardó cada ajuste (son 5 en esta partición): con eso sabes cuánto van a
costar las otras dos.

## 6 · La prueba de etiquetas aleatorias, antes que nada

`DESIGN.md` §7.1 pide correrla antes que cualquier experimento: con las etiquetas
barajadas el resultado tiene que ser el del azar. Si da más, hay fuga y ningún otro número
vale.

```python
!python -m ccls f4 run --particion aleatoria --barajar --cache {CACHE}
```

Se lee igual que en `LEAKAGE.md` §7.1: con etiquetas barajadas, la exactitud no puede pasar
la tasa de la clase mayoritaria de prueba. **No sigas con el paso 7 si esto falla.**

## 7 · El resto

```python
!python -m ccls f4 run --particion repositorio --cache {CACHE}
!python -m ccls f4 run --particion temporal --cache {CACHE}
```

`repositorio` es la partición principal y la más cara (25 ajustes).

## 8 · Traer los resultados

Los JSON quedan en `resultados/f4_codebert__<partición>.json` dentro de la sesión, que se
borra. Cópialos a Drive antes de cerrar:

```python
!cp resultados/f4_codebert__*.json /content/drive/MyDrive/ccls/
```

y de ahí a la carpeta `resultados/` de este repo. Cada JSON lleva las versiones de
`torch` y `transformers`, los hiperparámetros y el `manifest_sha256`.

## Si algo sale raro

- **Sin memoria de GPU:** baja `tamano_lote` en `config/f4.yaml`, **pero eso cambia la
  huella y rehace todo lo guardado**, y hay que reportarlo como otra configuración
  (`config/f4.yaml`, cabecera).
- **Dos corridas dan números distintos con la misma semilla:** en GPU las operaciones no
  son bit a bit deterministas. En la CPU de esta máquina sí lo son (hay un test). Es una
  diferencia esperable y hay que decirlo al reportar; para eso están las cinco semillas.
- **`f4 run` dice que no existe el dataset:** el paso 2 no copió el archivo o quedó en otra
  ruta; tiene que estar en `data/processed/dataset.jsonl`.
