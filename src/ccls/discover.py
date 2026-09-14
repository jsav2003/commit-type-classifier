"""Descubrimiento y verificación de repos candidatos vía la API de GitHub (`gh`).

Uso deliberadamente acotado: la API solo sirve para CONSULTAR metadatos (estrellas,
actividad, licencia) — nunca para traer commits o diffs. Eso lo hace `clone.py` +
`gitutil.py` con clonado local. Ver DESIGN.md, decisión 2 del plan de arranque.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass


@dataclass
class MetadatosRepo:
    owner_repo: str
    estrellas: int
    dias_desde_ultimo_push: int
    archivado: bool
    licencia: str | None
    ok: bool
    error: str = ""


def metadatos(owner_repo: str) -> MetadatosRepo:
    """Consulta metadatos de un repo con `gh api`. Requiere `gh auth status` ok."""
    campos = "stargazerCount,pushedAt,isArchived,licenseInfo"
    try:
        proc = subprocess.run(
            ["gh", "repo", "view", owner_repo, "--json", campos],
            capture_output=True, text=True, timeout=30, check=True,
        )
    except subprocess.CalledProcessError as e:
        return MetadatosRepo(owner_repo, 0, -1, False, None, False, e.stderr.strip())
    except FileNotFoundError:
        return MetadatosRepo(owner_repo, 0, -1, False, None, False, "gh no está instalado")

    from datetime import datetime, timezone

    data = json.loads(proc.stdout)
    pushed = datetime.fromisoformat(data["pushedAt"].replace("Z", "+00:00"))
    dias = (datetime.now(timezone.utc) - pushed).days
    licencia = (data.get("licenseInfo") or {}).get("key")

    return MetadatosRepo(
        owner_repo=owner_repo,
        estrellas=data["stargazerCount"],
        dias_desde_ultimo_push=dias,
        archivado=data["isArchived"],
        licencia=licencia,
        ok=True,
    )


def cumple_criterios(m: MetadatosRepo, criterios: dict) -> tuple[bool, list[str]]:
    """Contrasta metadatos contra config/repos.yaml -> criterios_admision.
    Devuelve (cumple, razones_de_rechazo)."""
    razones = []
    if not m.ok:
        return False, [f"metadatos no disponibles: {m.error}"]
    if m.estrellas < criterios.get("estrellas_minimas", 0):
        razones.append(f"estrellas {m.estrellas} < {criterios['estrellas_minimas']}")
    meses_max = criterios.get("actividad_maxima_meses_sin_push")
    if meses_max is not None and m.dias_desde_ultimo_push > meses_max * 30:
        razones.append(f"sin push hace {m.dias_desde_ultimo_push} días")
    if criterios.get("no_archivado") and m.archivado:
        razones.append("repositorio archivado")
    if criterios.get("licencia_permisiva") and not m.licencia:
        razones.append("sin licencia detectada")
    return (len(razones) == 0), razones
