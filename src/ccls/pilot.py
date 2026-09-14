"""Mediciones del piloto (Parte B del plan de arranque). Reemplaza tres supuestos
del diseño por números medidos, antes de comprometerse a las 14 horas de la F0.

Ver docs/PILOTO.md para los resultados y DESIGN.md §4-6 para las decisiones que
dependen de estos números.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from ccls.gitutil import Commit, ResultadoComando, clone_bare, dir_size_bytes, log_numstat, log_patch_to_devnull, rev_counts
from ccls.label import TIPO_A_CLASE, clasificar

DOCS_EXTS = {".md", ".rst", ".txt"}


@dataclass
class MedicionPrefijoClases:
    owner_repo: str
    n_muestreados: int
    n_con_prefijo_valido: int  # tipo mapea a una de las 4 clases
    n_con_prefijo_descartado: int  # tipo de Conventional Commits pero fuera de las 4 (chore, test, ...)
    n_sin_prefijo: int
    distribucion: dict[str, int] = field(default_factory=dict)  # clase -> conteo

    @property
    def tasa_prefijo_valido(self) -> float:
        return self.n_con_prefijo_valido / self.n_muestreados if self.n_muestreados else 0.0


def medir_prefijo_y_clases(repo_path: Path, owner_repo: str, n: int = 1000) -> MedicionPrefijoClases:
    """B2.1 y B2.2. Sobre el historial 'tal cual aparece' (sin --no-merges ni
    --first-parent): lo que un `git log` normal mostraría, que es la referencia
    más directa de 'los últimos N commits' del repo.
    """
    commits, resultado = log_numstat(repo_path, no_merges=False, first_parent=False, limit=n)
    if not resultado.ok:
        raise RuntimeError(f"git log falló en {owner_repo}: {resultado.stderr}")

    dist = {c: 0 for c in TIPO_A_CLASE.values()}
    n_validos = 0
    n_descartados = 0
    n_sin_prefijo = 0
    for c in commits:
        et = clasificar(c.subject)
        if et.tipo_declarado is None:
            n_sin_prefijo += 1
        elif et.clase is not None:
            n_validos += 1
            dist[et.clase] += 1
        else:
            n_descartados += 1

    return MedicionPrefijoClases(
        owner_repo=owner_repo,
        n_muestreados=len(commits),
        n_con_prefijo_valido=n_validos,
        n_con_prefijo_descartado=n_descartados,
        n_sin_prefijo=n_sin_prefijo,
        distribucion=dist,
    )


@dataclass
class MedicionMergeLoss:
    owner_repo: str
    total: int
    no_merges: int
    first_parent: int
    no_merges_first_parent: int

    @property
    def pct_perdido(self) -> float:
        if self.total == 0:
            return 0.0
        return 1 - (self.no_merges_first_parent / self.total)


def medir_merge_loss(repo_path: Path, owner_repo: str) -> MedicionMergeLoss:
    """B2.4. Cuántos commits sobreviven a --no-merges --first-parent, sobre el
    historial COMPLETO (no una muestra: la pérdida se concentra donde hubo
    ramas largas, que puede no estar en los últimos 1000 commits)."""
    counts = rev_counts(repo_path)
    return MedicionMergeLoss(
        owner_repo=owner_repo,
        total=counts["total"],
        no_merges=counts["no_merges"],
        first_parent=counts["first_parent"],
        no_merges_first_parent=counts["no_merges_first_parent"],
    )


@dataclass
class MedicionDocsBaseline:
    owner_repo: str
    n_evaluados: int
    tp: int
    fp: int
    fn: int

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


def _es_prediccion_docs(files: list[tuple[str, str, str]]) -> bool:
    if not files:
        return False
    for _, _, path in files:
        ext = Path(path).suffix.lower()
        if ext not in DOCS_EXTS:
            return False
    return True


def medir_docs_baseline(repo_path: Path, owner_repo: str, n: int = 1000) -> MedicionDocsBaseline:
    """B2.5. F1 de la regla 'todos los archivos son .md/.rst/.txt => docs',
    evaluada contra la etiqueta declarada por Conventional Commits (de los
    commits que SÍ tienen prefijo válido en las 4 clases)."""
    commits, resultado = log_numstat(repo_path, no_merges=False, first_parent=False, limit=n)
    if not resultado.ok:
        raise RuntimeError(f"git log falló en {owner_repo}: {resultado.stderr}")

    tp = fp = fn = 0
    evaluados = 0
    for c in commits:
        et = clasificar(c.subject)
        if et.clase is None:
            continue
        evaluados += 1
        pred_docs = _es_prediccion_docs(c.files)
        real_docs = et.clase == "docs"
        if pred_docs and real_docs:
            tp += 1
        elif pred_docs and not real_docs:
            fp += 1
        elif not pred_docs and real_docs:
            fn += 1

    return MedicionDocsBaseline(owner_repo=owner_repo, n_evaluados=evaluados, tp=tp, fp=fp, fn=fn)


@dataclass
class MedicionCostoClonado:
    owner_repo: str
    filter_blob_none: bool
    clone_ok: bool
    clone_s: float
    clone_stderr: str
    extract_ok: bool
    extract_s: float
    extract_stderr: str
    disco_mb: float


def medir_costo_clonado(owner_repo: str, workdir: Path, filter_blob_none: bool, timeout_clone: int = 1800, timeout_extract: int = 1800) -> MedicionCostoClonado:
    """B2.3. Clona con la estrategia dada y luego recorre el historial completo
    con -p --numstat descartando la salida, para medir el coste real de
    extracción de diffs (no solo metadatos)."""
    dest = workdir / (owner_repo.replace("/", "__") + ("__filtered" if filter_blob_none else "__full") + ".git")
    url = f"https://github.com/{owner_repo}.git"

    r_clone = clone_bare(url, dest, filter_blob_none=filter_blob_none, timeout=timeout_clone)
    if not r_clone.ok:
        return MedicionCostoClonado(owner_repo, filter_blob_none, False, r_clone.elapsed_s, r_clone.stderr, False, 0.0, "", 0.0)

    r_extract = log_patch_to_devnull(dest, no_merges=True, first_parent=True, timeout=timeout_extract)
    disco_mb = dir_size_bytes(dest) / (1024 * 1024)

    return MedicionCostoClonado(
        owner_repo=owner_repo,
        filter_blob_none=filter_blob_none,
        clone_ok=r_clone.ok,
        clone_s=r_clone.elapsed_s,
        clone_stderr=r_clone.stderr[-500:],
        extract_ok=r_extract.ok,
        extract_s=r_extract.elapsed_s,
        extract_stderr=r_extract.stderr[-500:],
        disco_mb=disco_mb,
    )
