"""Clonado de repos candidatos a data/raw/repos/. DESIGN.md — decisión 2."""

from __future__ import annotations

from pathlib import Path

from ccls.gitutil import clone_bare

REPOS_DIR = Path("data/raw/repos")


def slug(owner_repo: str) -> str:
    return owner_repo.replace("/", "__") + ".git"


def ruta_local(owner_repo: str, base: Path = REPOS_DIR) -> Path:
    return base / slug(owner_repo)


def asegurar_clonado(owner_repo: str, base: Path = REPOS_DIR, filter_blob_none: bool = False, timeout: int = 1800):
    """Clona si no existe ya. Reanudable: no repite un clonado ya hecho."""
    dest = ruta_local(owner_repo, base)
    if dest.exists() and any(dest.iterdir()):
        return dest, None
    url = f"https://github.com/{owner_repo}.git"
    resultado = clone_bare(url, dest, filter_blob_none=filter_blob_none, timeout=timeout)
    return dest, resultado
