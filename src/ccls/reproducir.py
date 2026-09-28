"""`python -m ccls reproducir`: el pipeline entero en orden, con un solo comando.
DESIGN.md §7.7 y §10.

Encadena los mismos subcomandos que están en `docs/ESTADO.md`, en el orden en que dependen unos
de otros, y para en el primero que falle. Los pasos se agrupan por lo que cuestan:

- `datos`: reconstruye el dataset y la muestra de la F3. Clona los repos (red, y GB en
  `data/raw/`); el dataset sale byte a byte igual (`manifest_sha256`).
- `cpu`: entrena y mide los baselines y las pruebas de fuga. Minutos, sin GPU.
- `gpu`: la F4 y la F5. Necesitan `requirements-f4.txt` y una GPU (horas en una T4); son
  reanudables, así que un corte no pierde lo hecho.
- `reportes`: escribe `docs/*.md` y `RESULTS.md` desde `resultados/`. Segundos, sin torch.

Por defecto corre `cpu` y `reportes`, que necesitan el dataset ya construido. `--datos`
agrega el primer grupo y `--gpu` el tercero. Sin `--gpu`, los reportes usan los
`resultados/f4_*` y `resultados/f5_*` que ya están en el repo.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DATASET = Path("data/processed/dataset.jsonl")

GRUPOS = ("datos", "cpu", "gpu", "reportes")


@dataclass(frozen=True)
class Paso:
    grupo: str
    argv: tuple[str, ...]
    para_que: str

    @property
    def comando(self) -> str:
        return "python -m ccls " + " ".join(self.argv)


PASOS: tuple[Paso, ...] = (
    Paso("datos", ("f0", "build"), "reconstruye el dataset (clona los repos)"),
    Paso("datos", ("f3", "build"), "muestra ciega de la F3"),
    Paso("datos", ("f3", "predecir"), "predicciones del clásico sobre la muestra de la F3"),
    Paso("cpu", ("f0", "stats"), "docs/F0_ESTADISTICAS.md"),
    Paso("cpu", ("f1", "fuga-aleatoria"), "LEAKAGE.md §7.1 con el modelo de humo -> docs/F1_ETIQUETAS_ALEATORIAS.md"),
    Paso("cpu", ("f2", "run"), "los baselines en las tres particiones, cinco semillas"),
    Paso("cpu", ("f1", "run", "--modelo", "clasico_lr", "--barajar"), "§7.1 sobre el clásico"),
    Paso("cpu", ("errores", "muestra"), "los errores del clásico y la muestra de 50 a revisar"),
    Paso("cpu", ("f3", "report", "--anotaciones", "data/processed/f3_anotaciones_llm.csv",
                 "--anotador", "Claude", "--salida", "docs/F3_TECHO_LLM.md"),
         "techo provisional del anotador LLM"),
    Paso("gpu", ("f4", "run"), "CodeBERT, tres particiones (reanudable)"),
    Paso("gpu", ("f4", "run", "--barajar"), "§7.1 sobre CodeBERT (reanudable)"),
    Paso("gpu", ("f5", "run"), "la red desde cero, tres particiones (reanudable)"),
    Paso("gpu", ("f5", "run", "--barajar"), "§7.1 sobre la red desde cero (reanudable)"),
    Paso("reportes", ("f2", "report"), "docs/F2_BASELINES.md"),
    Paso("reportes", ("f4", "report"), "docs/F4_TRANSFER.md"),
    Paso("reportes", ("f5", "report"), "docs/F5_DESDE_CERO.md"),
    Paso("reportes", ("errores", "report"), "ERROR-ANALYSIS.md (las causas están en data/processed/errores_causas.csv)"),
    Paso("reportes", ("results",), "RESULTS.md"),
)


def plan(datos: bool = False, gpu: bool = False) -> list[Paso]:
    grupos = {"cpu", "reportes"} | ({"datos"} if datos else set()) | ({"gpu"} if gpu else set())
    return [p for p in PASOS if p.grupo in grupos]


def falta_el_dataset(datos: bool, dataset: Path = DATASET) -> bool:
    """Sin `--datos`, los pasos de cpu y de reportes leen un dataset que tiene que existir."""
    return not datos and not dataset.exists()


def correr(pasos: list[Paso], main, imprimir=print) -> int:
    """`main(argv) -> int` es `ccls.cli.main`. Devuelve 0 si todo salió bien y, si no, el
    código del primer paso que falló; los que venían después no se corren."""
    for i, p in enumerate(pasos, 1):
        imprimir(f"\n[{i}/{len(pasos)}] {p.comando}\n    {p.para_que}")
        codigo = main(list(p.argv))
        if codigo:
            imprimir(f"\nfalló el paso {i} ({p.comando}) con código {codigo}; no se sigue")
            return codigo
    imprimir(f"\nlisto: {len(pasos)} pasos")
    return 0
