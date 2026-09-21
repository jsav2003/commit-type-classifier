"""F4 · transfer learning. DESIGN.md §6.3.

Un encoder preentrenado sobre código (CodeBERT) con una cabeza de clasificación, del que
solo se reentrenan las últimas capas. Cumple la misma interfaz que los modelos de
`modelos.py` (una fábrica que recibe la semilla y devuelve algo con fit/predict), así que
el runner de la F1 lo corre sin saber que es una red.

`torch` y `transformers` se importan dentro de los métodos, no arriba: el resto del
paquete y el CI (que solo instala requirements.txt) no los necesitan. `a_texto` y
`cargar_config` no los tocan y se prueban sin ellos.

El modelo recibe exactamente `experimento.ENTRADAS`, igual que el clásico, y de ahí solo
lee lo mismo que lee el clásico más las rutas de los archivos (config/f4.yaml). **El texto
del diff no entra** (DESIGN.md §6.2, decidido el 2026-09-21): `a_texto` no lee `r["diff"]`
y un test lo comprueba.
"""

from __future__ import annotations

import platform
import random
from pathlib import Path

import yaml

from ccls.stats import CLASES

F4_CONFIG_PATH = Path("config/f4.yaml")

_CLAVES = (
    "modelo_base", "revision", "capas_entrenables", "max_longitud", "epocas", "tamano_lote",
    "tasa_aprendizaje", "decaimiento_pesos", "calentamiento", "pesos_por_clase", "max_archivos_en_texto",
)


def cargar_config(path: Path = F4_CONFIG_PATH) -> dict:
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    faltan = [k for k in _CLAVES if k not in cfg]
    if faltan:
        raise KeyError(f"{path}: faltan {faltan}")
    if cfg["pesos_por_clase"] != "balanceados":
        raise ValueError(f"{path}: pesos_por_clase solo puede ser 'balanceados' (DESIGN.md §4.4)")
    return cfg


def a_texto(r: dict, max_archivos: int) -> tuple[str, str]:
    """(mensaje, metadatos): las dos mitades del par que se le da al tokenizador. El mensaje
    va primero para que, si hay que truncar, se recorte lo de menos valor: los metadatos
    y las rutas van después.

    Toda la información sale de los campos de `experimento.ENTRADAS`, menos `diff`, que no
    se lee. Los conteos son los que el clásico ve como rasgos; las rutas completas son de
    más (el clásico solo ve extensiones) y se declaran en config/f4.yaml.
    """
    archivos = r["files"][:max_archivos]
    resto = len(r["files"]) - len(archivos)
    meta = (
        f"files: {r['n_files']}, added: {r['lines_added']}, deleted: {r['lines_deleted']}, "
        f"binary: {r['n_binarios']}, tests: {'yes' if r['toca_tests'] else 'no'}, "
        f"docs: {'yes' if r['toca_docs'] else 'no'}. "
        + " ".join(archivos)
        + (f" (+{resto} more)" if resto else "")
    )
    return r["message"], meta


def _congelar(modelo, capas_entrenables: int | None) -> None:
    """Deja entrenables solo las últimas `capas_entrenables` capas del encoder y la cabeza
    de clasificación (que no cuelga de `base_model`). `None`: no congela nada, para una red
    que se entrena entera."""
    if capas_entrenables is None:
        return
    base = modelo.base_model
    for p in base.parameters():
        p.requires_grad = False
    capas = base.encoder.layer
    # `capas[-0:]` serían todas: por eso el índice se calcula
    for capa in capas[len(capas) - capas_entrenables:]:
        for p in capa.parameters():
            p.requires_grad = True


def pesos_balanceados(y: list[int], n_clases: int) -> list[float]:
    """n / (k * n_c), la fórmula de class_weight="balanced". Una clase sin ejemplos pesa 0:
    nunca aparece en la pérdida, igual que en scikit-learn, que no la conoce."""
    n = len(y)
    conteo = [y.count(c) for c in range(n_clases)]
    activas = sum(1 for c in conteo if c)
    return [n / (activas * c) if c else 0.0 for c in conteo]


def versiones() -> dict:
    import torch
    import transformers
    return {"torch": torch.__version__, "transformers": transformers.__version__,
            "cuda": torch.version.cuda, "plataforma": platform.platform()}


class ClasificadorProfundo:
    def __init__(self, semilla: int, cfg: dict, preentrenado: bool = True):
        self.semilla = semilla
        self.cfg = cfg
        self.preentrenado = preentrenado

    # ---- utilidades --------------------------------------------------------

    def _fijar_semillas(self) -> None:
        import numpy
        import torch
        random.seed(self.semilla)
        numpy.random.seed(self.semilla)
        torch.manual_seed(self.semilla)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(self.semilla)

    def _codificar(self, X: list[dict]) -> list[dict]:
        pares = [a_texto(r, self.cfg["max_archivos_en_texto"]) for r in X]
        enc = self.tok_([a for a, _ in pares], [b for _, b in pares], truncation=True,
                        max_length=self.cfg["max_longitud"])
        return [{"input_ids": enc["input_ids"][i], "attention_mask": enc["attention_mask"][i]}
                for i in range(len(X))]

    def _lote(self, items: list[dict]):
        return {k: v.to(self.dispositivo_) for k, v in self.tok_.pad(items, return_tensors="pt").items()}

    # ---- fit / predict -----------------------------------------------------

    def fit(self, X: list[dict], y: list[str]) -> "ClasificadorProfundo":
        import torch
        from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

        cfg = self.cfg
        self._fijar_semillas()
        self.clases_ = list(CLASES)
        y_idx = [self.clases_.index(c) for c in y]
        self.dispositivo_ = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tok_ = AutoTokenizer.from_pretrained(cfg["modelo_base"], revision=cfg["revision"])
        if self.preentrenado:
            modelo = AutoModelForSequenceClassification.from_pretrained(
                cfg["modelo_base"], revision=cfg["revision"], num_labels=len(self.clases_))
            _congelar(modelo, cfg["capas_entrenables"])
        else:  # la misma arquitectura sin pesos preentrenados, entrenada entera (DESIGN.md §6.4)
            modelo = AutoModelForSequenceClassification.from_config(
                AutoConfig.from_pretrained(cfg["modelo_base"], revision=cfg["revision"], num_labels=len(self.clases_)))
        modelo.to(self.dispositivo_)

        items = self._codificar(X)
        pesos = torch.tensor(pesos_balanceados(y_idx, len(self.clases_)), dtype=torch.float, device=self.dispositivo_)
        perdida = torch.nn.CrossEntropyLoss(weight=pesos)
        entrenables = [p for p in modelo.parameters() if p.requires_grad]
        opt = torch.optim.AdamW(entrenables, lr=cfg["tasa_aprendizaje"], weight_decay=cfg["decaimiento_pesos"])
        por_epoca = -(-len(items) // cfg["tamano_lote"])
        total = por_epoca * cfg["epocas"]
        sched = get_linear_schedule_with_warmup(opt, int(cfg["calentamiento"] * total), total)
        cuda = self.dispositivo_.type == "cuda"
        escalador = torch.amp.GradScaler("cuda", enabled=cuda)
        azar = torch.Generator().manual_seed(self.semilla)

        modelo.train()
        for _ in range(cfg["epocas"]):
            orden = torch.randperm(len(items), generator=azar).tolist()
            for i in range(0, len(orden), cfg["tamano_lote"]):
                idx = orden[i:i + cfg["tamano_lote"]]
                lote = self._lote([items[j] for j in idx])
                objetivo = torch.tensor([y_idx[j] for j in idx], device=self.dispositivo_)
                with torch.autocast(device_type=self.dispositivo_.type, dtype=torch.float16, enabled=cuda):
                    logits = modelo(**lote).logits
                # la pérdida en float32: con fp16 los pesos por clase pierden precisión
                p = perdida(logits.float(), objetivo)
                opt.zero_grad(set_to_none=True)
                escalador.scale(p).backward()
                escalador.step(opt)
                escalador.update()
                sched.step()
        self.modelo_ = modelo
        return self

    def predict(self, X: list[dict]) -> list[str]:
        import torch
        items = self._codificar(X)
        orden = sorted(range(len(items)), key=lambda i: len(items[i]["input_ids"]))  # menos relleno
        pred = [""] * len(items)
        self.modelo_.eval()
        cuda = self.dispositivo_.type == "cuda"
        with torch.no_grad():
            for i in range(0, len(orden), self.cfg["tamano_lote"] * 2):
                idx = orden[i:i + self.cfg["tamano_lote"] * 2]
                with torch.autocast(device_type=self.dispositivo_.type, dtype=torch.float16, enabled=cuda):
                    logits = self.modelo_(**self._lote([items[j] for j in idx])).logits
                for j, k in zip(idx, logits.argmax(-1).tolist(), strict=True):
                    pred[j] = self.clases_[k]
        return pred
