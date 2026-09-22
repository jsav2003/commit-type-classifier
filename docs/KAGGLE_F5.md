# Correr la F5 en Kaggle

Guía escrita a mano. Alternativa a `docs/COLAB_F5.md`, escrita el 2026-09-22 cuando Colab
cortó la GPU gratuita por límite de uso. Kaggle da unas 30 h de GPU por semana y corre el
notebook **en segundo plano** (hasta 12 h por corrida, con el navegador cerrado). La F5 va
en dos corridas de unas 3-4 h cada una (estimado): etiquetas de verdad y etiquetas
barajadas.

## 1 · Cuenta (una vez)

kaggle.com → crear cuenta → foto (arriba a la derecha) → **Settings → Phone
verification**. Sin verificar no hay GPU ni internet.

## 2 · Subir el dataset (una vez)

`data/processed/dataset.jsonl` (57 MB, no está en git). Cualquiera de estas:

- **https://www.kaggle.com/datasets → + New Dataset**, o
- **+ Create → New Dataset**, o
- desde el notebook: panel derecho → **Input → + Add Input → Upload**.

Título `ccls-dataset`, **Private**, Create.

## 3 · El notebook

**+ Create → New Notebook**. Panel derecho:

- **Accelerator: GPU T4 x2.** No P100: el torch actual ya no la soporta.
- **Internet: On.**
- **Input → + Add Input →** `ccls-dataset`.

Una sola celda:

```python
BARAJAR = False   # 1ª corrida: False  ·  2ª corrida: True

import glob, hashlib, os
!rm -rf /tmp/repo && git clone -q https://github.com/jsav2003/commit-type-classifier.git /tmp/repo
os.chdir('/tmp/repo')
fuente = glob.glob('/kaggle/input/**/dataset.jsonl', recursive=True)[0]
!mkdir -p data/processed && cp "{fuente}" data/processed/
h = hashlib.sha256(open('data/processed/dataset.jsonl', 'rb').read()).hexdigest()
assert h.startswith('797b73e4'), f'dataset distinto: {h}'
!pip install -q -r requirements.txt transformers==4.57.6
!pip install -q -e .
!nvidia-smi --query-gpu=name --format=csv
flag = '--barajar' if BARAJAR else ''
!python -m ccls f5 run --particion todas {flag} --cache /kaggle/working/f5_corridas
!cp resultados/f5_desde_cero__*.json /kaggle/working/
```

El `assert` para la corrida si el dataset subido no es el de la F0.

## 4 · Lanzar

**Save Version → Save & Run All (Commit) → Save.** Se puede cerrar el navegador. El
avance y los logs, en **Versions**.

## 5 · Al terminar

- **Output** de la versión → descargar `f5_desde_cero__*.json` → a `resultados/`.
- 2ª corrida: `BARAJAR = True` y otra vez el paso 4.

## Si algo falla

`CUDA out of memory`, pip o dataset no encontrado: **no tocar `config/f5.yaml`** (bajar el
lote rompe la regla de que la F5 usa los hiperparámetros de la F4, y hay un test). Se para
y se decide.
