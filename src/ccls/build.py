"""F0 · construcción del dataset (Parte C del plan de arranque). DESIGN.md §4-5.

Por cada repo de config/repos.yaml -> f0_repos:

1. Camina TODO el historial `--no-merges --first-parent` desde el SHA fijado.
2. Etiqueta por Conventional Commits (label.py) y se queda con las 4 clases.
3. Muestreo estratificado por trimestre de la fecha de commit, hasta el tope por
   repo. Nunca "los más recientes": la partición temporal necesita historial
   antiguo (DESIGN.md §5).
4. Trae el diff de los commits elegidos, le quita las rutas excluidas y lo trunca a
   un tope fijo.

Escribe tres archivos en data/processed/:

- dataset.jsonl       el dataset, con diffs. Fuera de git (pesa).
- manifest.csv        repo, sha, etiqueta, fecha: lo que DEFINE el dataset. En git.
- dataset_meta.json   parámetros, SHAs fijados, conteos y checksums. En git.

Nada lleva marca de hora: correr dos veces sobre los mismos clones produce archivos
idénticos, byte a byte.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ccls import clone
from ccls.gitutil import Commit, diffs_de_commits, git_version, log_numstat
from ccls.label import TIPO_A_CLASE, Etiqueta, clasificar, limpiar_texto_completo

PROCESSED_DIR = Path("data/processed")
DATASET_NAME = "dataset.jsonl"
MANIFEST_NAME = "manifest.csv"
META_NAME = "dataset_meta.json"
MANIFEST_COLS = ("repo", "sha", "label", "committer_date")
VERSION_FORMATO = 2

_DOCS_EXTS = {".md", ".rst", ".txt"}
_TEST_RE = re.compile(r"(^|/)(tests?|__tests__|e2e)(/|$)|\.(test|spec)\.[^/]+$", re.IGNORECASE)
# LEAKAGE.md, decisión abierta: el texto se conserva, la bandera permite medir en F2
# cuánto aporta esta señal por sí sola.
_ISSUE_RE = re.compile(
    r"\b(close[sd]?|fix(e[sd])?|resolve[sd]?)\b:?\s+(#\d+|https?://github\.com/\S+/issues/\d+)",
    re.IGNORECASE,
)
_BOT_RE = re.compile(r"\[bot\]|^renovate|^dependabot", re.IGNORECASE)
_CABECERA_DIFF = re.compile(r"^diff --git a/(?P<a>.*) b/(?P<b>.*)$")


def trimestre(fecha_iso: str) -> str:
    """'2021-03-31T23:30:00-05:00' -> '2021Q2'. En UTC, para que el estrato de un
    commit no dependa de la zona horaria de quien lo hizo."""
    dt = datetime.fromisoformat(fecha_iso).astimezone(timezone.utc)
    return f"{dt.year}Q{(dt.month - 1) // 3 + 1}"


def _fecha_utc(fecha_iso: str) -> str:
    return datetime.fromisoformat(fecha_iso).astimezone(timezone.utc).isoformat()


def asignar_por_estrato(tamanos: dict[str, int], tope: int) -> dict[str, int]:
    """Reparte `tope` entre estratos en proporción a su tamaño (método del resto
    mayor, en aritmética entera). Si no hay más que el tope, se toma todo.
    Empates en el resto se deshacen por nombre de estrato: determinista."""
    total = sum(tamanos.values())
    if total <= tope:
        return dict(tamanos)
    asignado: dict[str, int] = {}
    restos: dict[str, int] = {}
    for k, n in tamanos.items():
        asignado[k], restos[k] = divmod(tope * n, total)
    faltan = tope - sum(asignado.values())
    for k in sorted(restos, key=lambda k: (-restos[k], k))[:faltan]:
        asignado[k] += 1
    return asignado


def _orden(semilla: int, sha: str) -> str:
    return hashlib.sha256(f"{semilla}:{sha}".encode("ascii")).hexdigest()


def muestrear(etiquetados: list[tuple[Commit, Etiqueta]], tope: int, semilla: int) -> list[tuple[Commit, Etiqueta]]:
    """Muestreo estratificado por trimestre. Dentro de cada trimestre el orden es
    sha256(semilla:sha): no depende de ningún generador aleatorio."""
    por_trimestre: dict[str, list[tuple[Commit, Etiqueta]]] = defaultdict(list)
    for c, et in etiquetados:
        por_trimestre[trimestre(c.committer_date)].append((c, et))
    cuotas = asignar_por_estrato({k: len(v) for k, v in por_trimestre.items()}, tope)
    elegidos = []
    for k in sorted(por_trimestre):
        grupo = sorted(por_trimestre[k], key=lambda ce: _orden(semilla, ce[0].sha))
        elegidos.extend(grupo[:cuotas[k]])
    return elegidos


def quitar_rutas_del_diff(diff: str, prefijos: tuple[str, ...]) -> str:
    """Quita del diff los bloques de archivos bajo `prefijos`, cabecera incluida. Se
    mira la ruta vieja y la nueva, por si es un rename. Las líneas de contenido
    empiezan con +, - o espacio, así que ninguna se confunde con una cabecera."""
    if not prefijos:
        return diff
    out = []
    saltar = False
    for linea in diff.split("\n"):
        m = _CABECERA_DIFF.match(linea)
        if m:
            saltar = m.group("a").startswith(prefijos) or m.group("b").startswith(prefijos)
        if not saltar:
            out.append(linea)
    return "\n".join(out).strip("\n")


def _es_doc(path: str) -> bool:
    p = path.lower()
    return Path(p).suffix in _DOCS_EXTS or p.startswith("docs/") or "/docs/" in p or Path(p).name.startswith("readme")


def construir_registro(
    owner_repo: str,
    c: Commit,
    et: Etiqueta,
    diff: str,
    diff_max_chars: int,
    rutas_excluidas: tuple[str, ...] = (),
) -> dict:
    asunto = limpiar_texto_completo(et.mensaje_limpio)
    cuerpo = limpiar_texto_completo(c.body)
    files = [f for f in c.files if not f[2].startswith(rutas_excluidas)]
    diff = quitar_rutas_del_diff(diff, rutas_excluidas)
    paths = [p for _, _, p in files]
    return {
        "id": f"{owner_repo}@{c.sha}",
        "repo": owner_repo,
        "sha": c.sha,
        "label": et.clase,
        "committer_date": _fecha_utc(c.committer_date),
        "author_date": _fecha_utc(c.author_date),
        "trimestre": trimestre(c.committer_date),
        # --- entradas del modelo (DESIGN.md §4.3) ---
        "message": f"{asunto}\n\n{cuerpo}" if cuerpo else asunto,
        "diff": diff[:diff_max_chars],
        "files": paths,
        "n_files": len(paths),
        "lines_added": sum(int(a) for a, _, _ in files if a.isdigit()),
        "lines_deleted": sum(int(d) for _, d, _ in files if d.isdigit()),
        "n_binarios": sum(1 for a, _, _ in files if a == "-"),
        "extensiones": sorted({Path(p).suffix.lower() for p in paths if Path(p).suffix}),
        "toca_tests": any(_TEST_RE.search(p) for p in paths),
        "toca_docs": any(_es_doc(p) for p in paths),
        # --- banderas para medir en F2, no entradas por defecto ---
        "diff_chars": len(diff),
        "diff_truncado": len(diff) > diff_max_chars,
        "tiene_referencia_issue": bool(_ISSUE_RE.search(f"{c.subject}\n{c.body}")),
        "es_bot": bool(_BOT_RE.search(c.author_name)),
        # --- sale del prefijo o de lo excluido: solo auditoría, NUNCA entrada del modelo ---
        "auditoria": {
            "tipo_declarado": et.tipo_declarado,
            "scope": et.scope,
            "breaking": et.breaking,
            "n_archivos_excluidos": len(c.files) - len(files),
        },
    }


def extraer_repo(
    owner_repo: str,
    sha: str,
    tope: int,
    semilla: int,
    diff_max_chars: int,
    contexto: int = 3,
    rutas_excluidas: tuple[str, ...] = (),
    base: Path = clone.REPOS_DIR,
) -> tuple[list[dict], dict]:
    repo_path = clone.ruta_local(owner_repo, base)
    if not repo_path.exists():
        raise RuntimeError(f"{owner_repo} no está clonado en {repo_path}")
    commits, r = log_numstat(repo_path, no_merges=True, first_parent=True, rev=sha, timeout=1800)
    if not r.ok:
        raise RuntimeError(f"git log falló en {owner_repo} @ {sha}: {r.stderr[-500:]}")

    etiquetados = []
    sin_prefijo = fuera_de_clases = 0
    for c in commits:
        et = clasificar(c.subject)
        if et.tipo_declarado is None:
            sin_prefijo += 1
        elif et.clase is None:
            fuera_de_clases += 1
        else:
            etiquetados.append((c, et))

    elegidos = muestrear(etiquetados, tope, semilla)
    diffs = diffs_de_commits(repo_path, [c.sha for c, _ in elegidos], contexto=contexto)
    faltan = [c.sha for c, _ in elegidos if c.sha not in diffs]
    if faltan:
        raise RuntimeError(f"{owner_repo}: git no devolvió diff para {len(faltan)} commits, p. ej. {faltan[0]}")

    registros = [
        construir_registro(owner_repo, c, et, diffs[c.sha], diff_max_chars, rutas_excluidas)
        for c, et in elegidos
    ]
    por_clase_historial = Counter(et.clase for _, et in etiquetados)
    resumen = {
        "owner_repo": owner_repo,
        "sha": sha,
        "commits": len(commits),
        "sin_prefijo": sin_prefijo,
        "prefijo_fuera_de_clases": fuera_de_clases,
        "etiquetables": len(etiquetados),
        "etiquetables_por_clase": {k: por_clase_historial.get(k, 0) for k in TIPO_A_CLASE.values()},
        "muestreados": len(registros),
        "trimestres": len({r["trimestre"] for r in registros}),
    }
    return registros, resumen


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def escribir_dataset(registros: list[dict], resumenes: list[dict], parametros: dict, out_dir: Path) -> dict:
    registros = sorted(registros, key=lambda r: (r["repo"], r["committer_date"], r["sha"]))
    out_dir.mkdir(parents=True, exist_ok=True)

    jsonl = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in registros).encode("utf-8")

    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(MANIFEST_COLS)
    for r in registros:
        w.writerow([r[c] for c in MANIFEST_COLS])
    manifest = buf.getvalue().encode("utf-8")

    por_clase = Counter(r["label"] for r in registros)
    meta = {
        "version_formato": VERSION_FORMATO,
        "parametros": parametros,
        "repos": resumenes,
        "n_registros": len(registros),
        "por_clase": {k: por_clase.get(k, 0) for k in TIPO_A_CLASE.values()},
        "manifest_sha256": _sha256(manifest),
        "dataset_jsonl_sha256": _sha256(jsonl),
        "git_version": git_version(),
        "nota_checksums": (
            "manifest_sha256 identifica el dataset: mismos repos, SHAs y etiquetas. "
            "dataset_jsonl_sha256 depende además de cómo esta versión de git genera los diffs."
        ),
    }
    (out_dir / DATASET_NAME).write_bytes(jsonl)
    (out_dir / MANIFEST_NAME).write_bytes(manifest)
    (out_dir / META_NAME).write_bytes((json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return meta


def construir(cfg: dict, base: Path = clone.REPOS_DIR, out_dir: Path = PROCESSED_DIR, log: Callable[[str], None] = print) -> dict:
    ext = cfg["f0_extraccion"]
    parametros = {
        "tope_commits_por_repo": cfg["criterios_admision"]["tope_commits_por_repo"],
        "semilla": ext["semilla"],
        "diff_max_chars": ext["diff_max_chars"],
        "lineas_contexto_diff": ext["lineas_contexto_diff"],
        "rutas_excluidas": list(ext.get("rutas_excluidas", [])),
        "poblacion": "git log --no-merges --first-parent <sha>",
        "estrato": "trimestre UTC de la fecha de commit",
    }
    registros: list[dict] = []
    resumenes: list[dict] = []
    for repo in cfg["f0_repos"]:
        log(f"extrayendo {repo['owner_repo']} @ {repo['sha'][:10]} ...")
        regs, res = extraer_repo(
            repo["owner_repo"], repo["sha"],
            tope=parametros["tope_commits_por_repo"],
            semilla=parametros["semilla"],
            diff_max_chars=parametros["diff_max_chars"],
            contexto=parametros["lineas_contexto_diff"],
            rutas_excluidas=tuple(parametros["rutas_excluidas"]),
            base=base,
        )
        log(f"  {res['commits']} commits, {res['etiquetables']} etiquetables, {res['muestreados']} muestreados en {res['trimestres']} trimestres")
        registros.extend(regs)
        resumenes.append(res)
    return escribir_dataset(registros, resumenes, parametros, out_dir)
