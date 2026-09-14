"""Operaciones de git de bajo nivel, compartidas por clone.py, extract.py y pilot.py.

Todo pasa por clones `--bare` locales: sin working tree, más rápido y más barato en
disco. Ver DESIGN.md — decisión 2 (clonado local en vez de API de GitHub).
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

# Separadores de control que no aparecen en mensajes de commit normales.
_REC_SEP = "\x1e"  # separa un commit del siguiente
_FIELD_SEP = "\x1f"  # separa campos dentro del header de un commit

_LOG_FORMAT = f"{_REC_SEP}%H{_FIELD_SEP}%aI{_FIELD_SEP}%an{_FIELD_SEP}%s{_FIELD_SEP}%b{_REC_SEP}END"


@dataclass
class ResultadoComando:
    ok: bool
    stdout: str
    stderr: str
    elapsed_s: float
    returncode: int


def _run(cmd: list[str], cwd: Path | None = None, timeout: int | None = None) -> ResultadoComando:
    inicio = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        elapsed = time.monotonic() - inicio
        return ResultadoComando(proc.returncode == 0, proc.stdout, proc.stderr, elapsed, proc.returncode)
    except subprocess.TimeoutExpired as e:
        elapsed = time.monotonic() - inicio
        return ResultadoComando(False, e.stdout or "", (e.stderr or "") + "\n[timeout]", elapsed, -1)


def clone_bare(url: str, dest: Path, filter_blob_none: bool = False, timeout: int = 1800) -> ResultadoComando:
    """Clona un repo en modo --bare (sin working tree). Devuelve tiempo transcurrido
    para que el piloto (B2.3) pueda comparar estrategias.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "clone", "--bare"]
    if filter_blob_none:
        cmd += ["--filter=blob:none"]
    cmd += [url, str(dest)]
    return _run(cmd, timeout=timeout)


def rev_counts(repo_path: Path) -> dict[str, int]:
    """Cuenta commits bajo distintas combinaciones de banderas — insumo directo de
    la medición B2.4 (pérdida por --no-merges --first-parent).
    """
    variantes = {
        "total": [],
        "no_merges": ["--no-merges"],
        "first_parent": ["--first-parent"],
        "no_merges_first_parent": ["--no-merges", "--first-parent"],
    }
    out = {}
    for nombre, flags in variantes.items():
        r = _run(["git", "rev-list", "--count", "HEAD", *flags], cwd=repo_path)
        out[nombre] = int(r.stdout.strip()) if r.ok and r.stdout.strip().isdigit() else -1
    return out


@dataclass
class Commit:
    sha: str
    author_date: str
    author_name: str
    subject: str
    body: str
    files: list[tuple[str, str, str]] = field(default_factory=list)  # (add, del, path)


def _parse_log_numstat(raw: str) -> list[Commit]:
    commits: list[Commit] = []
    # raw empieza con _REC_SEP porque el formato lo antepone a cada commit.
    bloques = raw.split(_REC_SEP)
    i = 0
    while i < len(bloques):
        bloque = bloques[i]
        i += 1
        if not bloque:
            continue
        # bloque = "%H\x1f%aI\x1f%an\x1f%s\x1f%b" y el siguiente elemento de la
        # lista, tras el próximo _REC_SEP, empieza con "END\n<numstat...>"
        campos = bloque.split(_FIELD_SEP)
        if len(campos) < 5:
            continue
        sha, author_date, author_name, subject, body = campos[0], campos[1], campos[2], campos[3], campos[4]
        # El siguiente elemento trae "END\n" seguido del bloque numstat de ESTE commit.
        numstat_txt = ""
        if i < len(bloques):
            siguiente = bloques[i]
            if siguiente.startswith("END"):
                numstat_txt = siguiente[len("END"):].lstrip("\n")
        files = []
        for linea in numstat_txt.splitlines():
            linea = linea.strip()
            if not linea:
                continue
            partes = linea.split("\t")
            if len(partes) == 3:
                files.append((partes[0], partes[1], partes[2]))
        commits.append(Commit(sha, author_date, author_name, subject.strip(), body.strip(), files))
    return commits


def log_numstat(
    repo_path: Path,
    no_merges: bool = True,
    first_parent: bool = True,
    limit: int | None = None,
    timeout: int = 600,
) -> tuple[list[Commit], ResultadoComando]:
    """git log con --numstat (sin -p, sin contenido de diff) — barato: no requiere
    bajar blobs completos, solo los necesarios para contar líneas +/-.
    """
    cmd = ["git", "log", f"--format={_LOG_FORMAT}", "--numstat"]
    if no_merges:
        cmd.append("--no-merges")
    if first_parent:
        cmd.append("--first-parent")
    if limit:
        cmd += ["-n", str(limit)]
    r = _run(cmd, cwd=repo_path, timeout=timeout)
    if not r.ok:
        return [], r
    return _parse_log_numstat(r.stdout), r


def log_patch_to_devnull(repo_path: Path, no_merges: bool = True, first_parent: bool = True, timeout: int = 1800) -> ResultadoComando:
    """Recorre TODO el historial con -p --numstat, descartando la salida.
    Simula el coste real de extracción de diffs (B2.3): con --filter=blob:none
    esto fuerza a bajar cada blob bajo demanda.
    """
    cmd = ["git", "log", "--numstat", "-p", "--no-color", "-U3"]
    if no_merges:
        cmd.append("--no-merges")
    if first_parent:
        cmd.append("--first-parent")
    # Redirigir a NUL directamente en el proceso, más rápido que traer la salida
    # completa a Python solo para descartarla.
    inicio = time.monotonic()
    try:
        with open("NUL" if _is_windows() else "/dev/null", "w") as devnull:
            proc = subprocess.run(cmd, cwd=str(repo_path), stdout=devnull, stderr=subprocess.PIPE, text=True, timeout=timeout)
        elapsed = time.monotonic() - inicio
        return ResultadoComando(proc.returncode == 0, "", proc.stderr or "", elapsed, proc.returncode)
    except subprocess.TimeoutExpired as e:
        elapsed = time.monotonic() - inicio
        return ResultadoComando(False, "", (e.stderr or "") + "\n[timeout]", elapsed, -1)


def _is_windows() -> bool:
    import platform
    return platform.system() == "Windows"


def head_sha(repo_path: Path) -> str | None:
    r = _run(["git", "rev-parse", "HEAD"], cwd=repo_path)
    return r.stdout.strip() if r.ok else None


def dir_size_bytes(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total
