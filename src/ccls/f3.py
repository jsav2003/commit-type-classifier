"""F3 · techo humano. DESIGN.md §4.2 y §7.5.

La muestra humana tiene dos estratos, mezclados en un solo orden para que quien
etiqueta no sepa cuál mira:

- A · commits SIN prefijo válido de los repos de config/repos.yaml -> f3_repos.
  No hay etiqueta declarada. Mide el acuerdo humano <-> modelo fuera de la convención.
- B · commits del dataset de la F0, con el prefijo ya quitado, por cuotas de clase.
  Mide el techo: acuerdo humano <-> etiqueta declarada.

Más `n_repeticiones` ítems repetidos al final, sin avisar, para medir el acuerdo del
anotador consigo mismo.

Escribe en data/processed/:

- f3_hoja.json          lo ÚNICO que lee la herramienta de etiquetado: id, mensaje,
                        archivos y líneas. Sin etiqueta declarada, repo ni SHA. En git.
- f3_clave.csv          id -> estrato, repo, SHA, etiqueta declarada. En git. La
                        herramienta de etiquetado no lo abre.
- f3_registros.jsonl    los registros completos, con diffs, para que el modelo prediga.
                        Fuera de git, como dataset.jsonl.
- f3_meta.json          parámetros, conteos y checksums. En git.

Nada lleva marca de hora: correr dos veces sobre los mismos clones y el mismo dataset
produce hoja y clave idénticas, byte a byte. El azar sale de sha256, como en la F0.
"""

from __future__ import annotations

import csv
import io
import json
import os
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable

from ccls import build, clone, metricas
from ccls.gitutil import Commit, diffs_de_commits, git_version, log_numstat
from ccls.label import Etiqueta, clasificar, contiene_fuga

F3_HOJA_PATH = build.PROCESSED_DIR / "f3_hoja.json"
F3_CLAVE_PATH = build.PROCESSED_DIR / "f3_clave.csv"
F3_REGISTROS_PATH = build.PROCESSED_DIR / "f3_registros.jsonl"
F3_META_PATH = build.PROCESSED_DIR / "f3_meta.json"
F3_ANOTACIONES_PATH = build.PROCESSED_DIR / "f3_anotaciones.csv"

VERSION_FORMATO = 1
CLAVE_COLS = ("id", "estrato", "repo", "sha", "declarada", "repeticion_de")
# Lo que la herramienta de etiquetado puede leer de cada ítem. Todo lo demás (repo,
# SHA, etiqueta declarada, fechas, auditoría) vive en la clave o en los registros.
CAMPOS_HOJA = ("id", "message", "files", "lines_added", "lines_deleted")


def cuotas_iguales(claves: list[str], n: int) -> dict[str, int]:
    """Reparte `n` en partes iguales entre `claves`; el resto, de a uno, por orden de
    nombre. Determinista. Se reparte por igual y no en proporción al tamaño para que
    los repos chicos (cobra, hcl) no desaparezcan de la muestra."""
    base, resto = divmod(n, len(claves))
    return {k: base + (1 if i < resto else 0) for i, k in enumerate(sorted(claves))}


def muestrear_estrato_a(
    sin_prefijo_por_repo: dict[str, list[tuple[Commit, Etiqueta]]], n: int, semilla: int
) -> dict[str, list[tuple[Commit, Etiqueta]]]:
    """`n` commits sin prefijo, repartidos por igual entre repos y, dentro de cada uno,
    estratificados por trimestre con el mismo `build.muestrear` de la F0."""
    cuotas = cuotas_iguales(list(sin_prefijo_por_repo), n)
    out = {}
    for repo, cuota in cuotas.items():
        disponibles = sin_prefijo_por_repo[repo]
        if len(disponibles) < cuota:
            raise RuntimeError(f"{repo}: {len(disponibles)} commits sin prefijo, la cuota pide {cuota}")
        out[repo] = build.muestrear(disponibles, cuota, semilla)
    return out


def muestrear_estrato_b(registros: list[dict], cuotas: dict[str, int], semilla: int) -> list[dict]:
    """Por cada clase declarada, `cuotas[clase]` registros del dataset. Dentro de la
    clase, repartidos entre repos en proporción a su tamaño (`asignar_por_estrato`,
    para que angular-cli no se lleve todo) y, dentro del repo, por sha256."""
    elegidos: list[dict] = []
    for clase in sorted(cuotas):
        por_repo: dict[str, list[dict]] = defaultdict(list)
        for r in registros:
            if r["label"] == clase:
                por_repo[r["repo"]].append(r)
        if sum(map(len, por_repo.values())) < cuotas[clase]:
            raise RuntimeError(f"el dataset tiene menos de {cuotas[clase]} registros de `{clase}`")
        reparto = build.asignar_por_estrato({k: len(v) for k, v in por_repo.items()}, cuotas[clase])
        for repo in sorted(por_repo):
            grupo = sorted(por_repo[repo], key=lambda r: build._orden(semilla, r["id"]))
            elegidos.extend(grupo[: reparto[repo]])
    return elegidos


def armar_lote(a: list[dict], b: list[dict], semilla: int, n_repeticiones: int, ventana: int) -> list[dict]:
    """Une los dos estratos en un solo orden barajado por sha256 y añade al final las
    repeticiones. Cada ítem sale con su `f3_id` y su `estrato`; las repeticiones llevan
    además `repeticion_de`. Las repeticiones salen de los primeros `ventana` puestos,
    mitad de cada estrato, para que pase tiempo entre las dos vistas."""
    for r in a:
        r["estrato"] = "A"
    for r in b:
        r["estrato"] = "B"
    orden = sorted(a + b, key=lambda r: build._orden(semilla, "orden:" + r["id"]))
    for i, r in enumerate(orden, start=1):
        r["f3_id"] = f"f3-{i:04d}"
        r["repeticion_de"] = ""

    candidatos = orden[:ventana]
    mitad = n_repeticiones // 2
    repetidos: list[dict] = []
    for estrato, cuota in (("A", n_repeticiones - mitad), ("B", mitad)):
        pool = sorted((r for r in candidatos if r["estrato"] == estrato),
                      key=lambda r: build._orden(semilla, "rep:" + r["f3_id"]))
        if len(pool) < cuota:
            raise RuntimeError(f"solo {len(pool)} ítems del estrato {estrato} en los primeros {ventana}")
        repetidos.extend(pool[:cuota])
    repetidos.sort(key=lambda r: build._orden(semilla, "reporden:" + r["f3_id"]))

    lote = list(orden)
    for j, r in enumerate(repetidos, start=len(orden) + 1):
        copia = dict(r)
        copia["f3_id"] = f"f3-{j:04d}"
        copia["repeticion_de"] = r["f3_id"]
        lote.append(copia)
    return lote


def _item_hoja(r: dict) -> dict:
    item = {"id": r["f3_id"], **{k: r[k] for k in CAMPOS_HOJA if k != "id"}}
    if contiene_fuga(item["message"]):
        raise RuntimeError(f"{r['f3_id']}: el mensaje todavía contiene un prefijo de convención")
    return item


def escribir_lote(lote: list[dict], parametros: dict, resumenes: list[dict], manifest_sha256: str,
                  out_dir: Path = build.PROCESSED_DIR) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)

    hoja = (json.dumps({"version_formato": VERSION_FORMATO, "items": [_item_hoja(r) for r in lote]},
                       ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8")

    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(CLAVE_COLS)
    for r in lote:
        w.writerow([r["f3_id"], r["estrato"], r["repo"], r["sha"], r["label"] or "", r["repeticion_de"]])
    clave = buf.getvalue().encode("utf-8")

    registros = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in lote).encode("utf-8")

    originales = [r for r in lote if not r["repeticion_de"]]
    meta = {
        "version_formato": VERSION_FORMATO,
        "parametros": parametros,
        "repos_estrato_a": resumenes,
        "n_items": len(lote),
        "n_originales": len(originales),
        "n_repeticiones": len(lote) - len(originales),
        "estrato_a": len([r for r in originales if r["estrato"] == "A"]),
        "estrato_b_por_clase": dict(sorted(Counter(r["label"] for r in originales if r["estrato"] == "B").items())),
        "estrato_a_por_repo": dict(sorted(Counter(r["repo"] for r in originales if r["estrato"] == "A").items())),
        "manifest_sha256": manifest_sha256,
        "hoja_sha256": build._sha256(hoja),
        "clave_sha256": build._sha256(clave),
        "registros_jsonl_sha256": build._sha256(registros),
        "git_version": git_version(),
        "nota_checksums": (
            "hoja_sha256 y clave_sha256 identifican la muestra: mismos commits, mismo orden. "
            "registros_jsonl_sha256 depende además de cómo esta versión de git genera los diffs."
        ),
    }
    (out_dir / F3_HOJA_PATH.name).write_bytes(hoja)
    (out_dir / F3_CLAVE_PATH.name).write_bytes(clave)
    (out_dir / F3_REGISTROS_PATH.name).write_bytes(registros)
    (out_dir / F3_META_PATH.name).write_bytes(
        (json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return meta


def extraer_sin_prefijo(owner_repo: str, sha: str, base: Path = clone.REPOS_DIR) -> list[tuple[Commit, Etiqueta]]:
    """Los commits de `--no-merges --first-parent` desde `sha` que NO llevan prefijo de
    convención. Se excluye cualquier `palabra:` inicial (`clasificar` da tipo_declarado),
    no solo los cuatro tipos: un `chore:` también es un repo con convención."""
    repo_path = clone.ruta_local(owner_repo, base)
    if not repo_path.exists():
        raise RuntimeError(f"{owner_repo} no está clonado en {repo_path}")
    commits, r = log_numstat(repo_path, no_merges=True, first_parent=True, rev=sha, timeout=1800)
    if not r.ok:
        raise RuntimeError(f"git log falló en {owner_repo} @ {sha}: {r.stderr[-500:]}")
    out = []
    for c in commits:
        et = clasificar(c.subject)
        if et.tipo_declarado is None:
            out.append((c, et))
    return out


def construir(cfg: dict, registros_f0: list[dict], manifest_sha256: str, base: Path = clone.REPOS_DIR,
              out_dir: Path = build.PROCESSED_DIR, log: Callable[[str], None] = print) -> dict:
    m = cfg["f3_muestreo"]
    ext = cfg["f0_extraccion"]
    semilla = m["semilla"]
    rutas = tuple(ext.get("rutas_excluidas", []))
    f0 = {r["owner_repo"] for r in cfg["f0_repos"]}
    ajenos = [r["owner_repo"] for r in cfg["f3_repos"] if r["owner_repo"] in f0]
    if ajenos:
        raise RuntimeError(f"f3_repos no puede incluir repos del dataset de entrenamiento: {ajenos}")

    sin_prefijo: dict[str, list[tuple[Commit, Etiqueta]]] = {}
    resumenes = []
    for repo in cfg["f3_repos"]:
        log(f"leyendo {repo['owner_repo']} @ {repo['sha'][:10]} ...")
        sp = extraer_sin_prefijo(repo["owner_repo"], repo["sha"], base)
        sin_prefijo[repo["owner_repo"]] = sp
        resumenes.append({"owner_repo": repo["owner_repo"], "sha": repo["sha"], "sin_prefijo": len(sp)})
        log(f"  {len(sp)} commits sin prefijo")

    elegidos_a = muestrear_estrato_a(sin_prefijo, m["n_estrato_a"], semilla)
    a: list[dict] = []
    for repo in cfg["f3_repos"]:
        owner_repo = repo["owner_repo"]
        pares = elegidos_a[owner_repo]
        diffs = diffs_de_commits(clone.ruta_local(owner_repo, base), [c.sha for c, _ in pares],
                                 contexto=ext["lineas_contexto_diff"])
        faltan = [c.sha for c, _ in pares if c.sha not in diffs]
        if faltan:
            raise RuntimeError(f"{owner_repo}: git no devolvió diff para {len(faltan)} commits, p. ej. {faltan[0]}")
        for c, et in pares:
            a.append(build.construir_registro(owner_repo, c, et, diffs[c.sha], ext["diff_max_chars"], rutas))
        for res in resumenes:
            if res["owner_repo"] == owner_repo:
                res["muestreados"] = len(pares)

    b = muestrear_estrato_b(registros_f0, m["cuotas_estrato_b"], semilla)
    lote = armar_lote(a, [dict(r) for r in b], semilla, m["n_repeticiones"], m["ventana_repeticiones"])
    parametros = {
        "semilla": semilla,
        "n_estrato_a": m["n_estrato_a"],
        "cuotas_estrato_b": m["cuotas_estrato_b"],
        "n_repeticiones": m["n_repeticiones"],
        "ventana_repeticiones": m["ventana_repeticiones"],
        "diff_max_chars": ext["diff_max_chars"],
        "rutas_excluidas": list(rutas),
        "estrato_a": "git log --no-merges --first-parent <sha>, solo commits sin prefijo de convención",
    }
    return escribir_lote(lote, parametros, resumenes, manifest_sha256, out_dir)


# --------------------------------------------------------------------------- #
# Etiquetado a mano
# --------------------------------------------------------------------------- #

ETIQUETAS = ("fix", "feat", "refactor", "docs")
# `mixto`: el commit hace más de una cosa. `ninguna`: no es ninguna de las cuatro
# (una actualización de dependencias, un cambio de CI). El reporte da el acuerdo
# contándolas y sin contarlas (DESIGN.md §7.5).
ETIQUETAS_HUMANAS = ETIQUETAS + ("mixto", "ninguna")
TECLAS = {"f": "fix", "e": "feat", "r": "refactor", "d": "docs", "m": "mixto", "n": "ninguna"}
ANOTACIONES_COLS = ("id", "etiqueta", "necesita_diff", "segundos")
MAX_ARCHIVOS_A_LA_VISTA = 25


def cargar_hoja(path: Path = F3_HOJA_PATH) -> list[dict]:
    """La ÚNICA entrada de datos de la herramienta de etiquetado. No hay ninguna otra
    ruta en este bloque: la clave (etiqueta declarada, repo, SHA) no se abre desde aquí."""
    return json.loads(path.read_text(encoding="utf-8"))["items"]


def leer_anotaciones(path: Path = F3_ANOTACIONES_PATH) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))
    for r in filas:
        r["necesita_diff"] = r["necesita_diff"] == "1"
        r["segundos"] = float(r["segundos"])
    return filas


def escribir_anotaciones(anotaciones: list[dict], path: Path = F3_ANOTACIONES_PATH) -> None:
    """Reescribe el archivo entero en cada respuesta, por un temporal: si el proceso se
    corta a la mitad, queda la versión anterior completa y no una a medias."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(ANOTACIONES_COLS)
    for a in anotaciones:
        w.writerow([a["id"], a["etiqueta"], int(a["necesita_diff"]), f"{a['segundos']:.1f}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(buf.getvalue().encode("utf-8"))
    os.replace(tmp, path)


def _pantalla(item: dict, puesto: int, total: int, necesita_diff: bool) -> str:
    files = item["files"]
    vistos = files[:MAX_ARCHIVOS_A_LA_VISTA]
    resto = len(files) - len(vistos)
    L = [
        "",
        f"[ {puesto}/{total} ]  {item['id']}",
        "",
        "mensaje:",
        *("  " + linea for linea in item["message"].strip().split("\n")),
        "",
        f"archivos ({len(files)}):",
        *("  " + f for f in vistos),
        *([f"  ... y {resto} más"] if resto else []),
        "",
        f"+{item['lines_added']} / -{item['lines_deleted']}",
        "",
        "[f]ix  f[e]at  [r]efactor  [d]ocs   [m]ixto  [n]inguna",
        "[?] necesitaría el diff" + ("  (marcado)" if necesita_diff else "")
        + "   [u]ndo  [q]uit (ya está guardado)",
    ]
    return "\n".join(L)


def leer_tecla() -> str:
    """Una tecla sin Enter. Ctrl-C se trata como salir: cada respuesta ya está en disco."""
    try:
        import msvcrt
        return msvcrt.getwch().lower()
    except ImportError:
        pass
    import sys
    if not sys.stdin.isatty():
        return (sys.stdin.readline() or "q").strip()[:1].lower() or "q"
    import termios
    import tty
    fd = sys.stdin.fileno()
    viejo = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1).lower()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, viejo)


def etiquetar(
    hoja: list[dict],
    anotaciones_path: Path = F3_ANOTACIONES_PATH,
    tecla: Callable[[], str] = leer_tecla,
    imprimir: Callable[[str], None] = print,
    reloj: Callable[[], float] = time.monotonic,
) -> dict:
    """Bucle de etiquetado, reanudable: retoma en el primer ítem de la hoja que no tiene
    anotación. Cada respuesta se escribe a disco al instante. `?` marca que el ítem
    habría necesitado el texto del diff (no lo muestra: el modelo de la F2 tampoco lo
    ve) y sigue pidiendo la etiqueta. `u` borra la última respuesta y vuelve a ese
    ítem; `q` sale."""
    ids = [it["id"] for it in hoja]
    hechas = leer_anotaciones(anotaciones_path)
    if [a["id"] for a in hechas] != ids[: len(hechas)]:
        raise RuntimeError(
            f"{anotaciones_path} no corresponde a esta hoja: sus ids no son un prefijo de los de la hoja. "
            "Si cambió la muestra (f3 build), las anotaciones viejas ya no valen."
        )
    while len(hechas) < len(hoja):
        item = hoja[len(hechas)]
        necesita_diff = False
        inicio = reloj()
        while True:
            imprimir(_pantalla(item, len(hechas) + 1, len(hoja), necesita_diff))
            k = tecla()
            if k in TECLAS:
                hechas.append({"id": item["id"], "etiqueta": TECLAS[k], "necesita_diff": necesita_diff,
                               "segundos": reloj() - inicio})
                escribir_anotaciones(hechas, anotaciones_path)
                break
            if k == "?":
                necesita_diff = not necesita_diff
            elif k == "u":
                if hechas:
                    hechas.pop()
                    escribir_anotaciones(hechas, anotaciones_path)
                    item = hoja[len(hechas)]
                    necesita_diff = False
                    inicio = reloj()
                else:
                    imprimir("(no hay nada que deshacer)")
            elif k in ("q", "\x03", "\x1b"):
                imprimir(f"\nguardado: {len(hechas)}/{len(hoja)} ítems.")
                return {"hechas": len(hechas), "total": len(hoja)}
    imprimir(f"\nlisto: {len(hechas)}/{len(hoja)} ítems.")
    return {"hechas": len(hechas), "total": len(hoja)}


# --------------------------------------------------------------------------- #
# Predicciones del modelo sobre la muestra
# --------------------------------------------------------------------------- #

F3_PREDICCIONES_PATH = build.PROCESSED_DIR / "f3_predicciones.csv"
F3_REPORTE_PATH = Path("docs/F3_TECHO_HUMANO.md")
PREDICCIONES_COLS = ("id", "prediccion", "entrenado_sin")
# El clásico de referencia de la F2 (DESIGN.md §4.4). Una sola semilla: con la división
# fija y el modelo determinista, las cinco darían lo mismo.
MODELO_F3 = "clasico_lr_balanceado"
SEMILLA_MODELO = 1


def predecir(registros_f0: list[dict], lote: list[dict], modelo: str = MODELO_F3,
             semilla: int = SEMILLA_MODELO) -> list[dict]:
    """Qué dice el modelo de cada ítem de la muestra, sin haber visto ese repo.

    Un ítem del estrato B es de un repo del dataset: el modelo se entrena con los otros
    repos (el mismo fold que la partición por repositorio de la F2). Un ítem del
    estrato A es de un repo que el dataset nunca tuvo: el modelo se entrena con todo.
    Recibe solo `experimento.ENTRADAS`, igual que en la F2."""
    from ccls import experimento, modelos

    def entradas(rs: list[dict]) -> list[dict]:
        return [{k: r[k] for k in experimento.ENTRADAS} for r in rs]

    grupos: dict[str, list[dict]] = defaultdict(list)
    for r in lote:
        grupos[r["repo"] if r["estrato"] == "B" else ""].append(r)
    out: list[dict] = []
    for excluido in sorted(grupos):
        train = [r for r in registros_f0 if r["repo"] != excluido] if excluido else registros_f0
        m = modelos.MODELOS[modelo](semilla).fit(entradas(train), [r["label"] for r in train])
        for r, p in zip(grupos[excluido], m.predict(entradas(grupos[excluido])), strict=True):
            out.append({"id": r["f3_id"], "prediccion": str(p), "entrenado_sin": excluido or "(nada: repo ajeno)"})
    return sorted(out, key=lambda x: x["id"])


def escribir_predicciones(preds: list[dict], path: Path = F3_PREDICCIONES_PATH) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(PREDICCIONES_COLS)
    for p in preds:
        w.writerow([p[c] for c in PREDICCIONES_COLS])
    data = buf.getvalue().encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return build._sha256(data)


def leer_predicciones(path: Path = F3_PREDICCIONES_PATH) -> dict[str, str]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return {r["id"]: r["prediccion"] for r in csv.DictReader(f)}


def leer_clave(path: Path = F3_CLAVE_PATH) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# --------------------------------------------------------------------------- #
# Acuerdos
# --------------------------------------------------------------------------- #

def unir(clave: list[dict], anotaciones: list[dict], predicciones: dict[str, str]) -> list[dict]:
    """Una fila por ítem de la clave: estrato, declarada, lo que puso el humano y lo que
    dijo el modelo. Falla si falta alguna anotación o predicción: un techo calculado
    sobre una parte de la muestra no es el techo."""
    humanas = {a["id"]: a for a in anotaciones}
    faltan = [c["id"] for c in clave if c["id"] not in humanas]
    if faltan:
        raise RuntimeError(f"faltan {len(faltan)} anotaciones, p. ej. {faltan[0]}")
    sin_pred = [c["id"] for c in clave if c["id"] not in predicciones]
    if sin_pred:
        raise RuntimeError(f"faltan {len(sin_pred)} predicciones, p. ej. {sin_pred[0]} (correr 'f3 predecir')")
    return [
        {
            "id": c["id"], "estrato": c["estrato"], "repo": c["repo"], "declarada": c["declarada"] or None,
            "repeticion_de": c["repeticion_de"] or None,
            "humana": humanas[c["id"]]["etiqueta"], "necesita_diff": humanas[c["id"]]["necesita_diff"],
            "segundos": humanas[c["id"]]["segundos"], "modelo": predicciones[c["id"]],
        }
        for c in clave
    ]


def _valen(filas: list[dict], solo_clases: bool) -> list[dict]:
    """Los ítems sobre los que se calcula una variante. `solo_clases`: el humano tiene
    que haber puesto una de las cuatro clases; `mixto` y `ninguna` salen del
    denominador. Si no, cuentan como desacuerdo. Todas las filas de una variante usan
    los mismos ítems, para que sean comparables entre sí."""
    return [f for f in filas if f["humana"] in ETIQUETAS] if solo_clases else filas


def acuerdo(filas: list[dict], a: str, b: str, solo_clases: bool) -> tuple[int, int]:
    """(k, n): en cuántos ítems coinciden las columnas `a` y `b`."""
    vs = _valen(filas, solo_clases)
    return sum(f[a] == f[b] for f in vs), len(vs)


def acuerdo_por_clase(filas: list[dict], a: str, b: str, solo_clases: bool) -> dict[str, tuple[int, int]]:
    """(k, n) para cada clase declarada: `filas` son del estrato B."""
    vs = _valen(filas, solo_clases)
    return {c: (sum(f[a] == f[b] for f in vs if f["declarada"] == c), sum(f["declarada"] == c for f in vs))
            for c in ETIQUETAS}


def reponderado(por_clase: dict[str, tuple[int, int]], pesos: dict[str, float]) -> tuple[float, float, float] | None:
    """Acuerdo global a las proporciones reales del dataset: p = sum(w_c * p_c). Las
    clases son muestras independientes, así que var = sum(w_c^2 * p_c (1-p_c) / n_c) y
    el intervalo es normal al 95%: cerrado, sin RNG. None si alguna clase no tiene ítems."""
    if any(n == 0 for _, n in por_clase.values()):
        return None
    p = sum(pesos[c] * k / n for c, (k, n) in por_clase.items())
    var = sum(pesos[c] ** 2 * (k / n) * (1 - k / n) / n for c, (k, n) in por_clase.items())
    h = 1.96 * var**0.5
    return p, max(0.0, p - h), min(1.0, p + h)


def pesos_del_dataset(por_clase: dict[str, int]) -> dict[str, float]:
    total = sum(por_clase[c] for c in ETIQUETAS)
    return {c: por_clase[c] / total for c in ETIQUETAS}


# --------------------------------------------------------------------------- #
# Reporte
# --------------------------------------------------------------------------- #

def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x:.1%}".replace(".", ",")


def _puntos(x: float) -> str:
    return f"{x * 100:+.1f}".replace(".", ",")


def _num(x: float | None) -> str:
    return "—" if x is None else f"{x:.2f}".replace(".", ",")


def _celda(k: int, n: int) -> str:
    """Acuerdo con su intervalo de Wilson. Sin ítems no hay acuerdo: `—`, nunca 0."""
    if n == 0:
        return "—"
    lo, hi = metricas.wilson(k, n)
    return f"{_pct(k / n)} [{_pct(lo)}, {_pct(hi)}]"


def _celda_rep(por_clase: dict[str, tuple[int, int]], pesos: dict[str, float]) -> str:
    r = reponderado(por_clase, pesos)
    return "—" if r is None else f"{_pct(r[0])} [{_pct(r[1])}, {_pct(r[2])}]"


def _sumar(por_clase: dict[str, tuple[int, int]]) -> tuple[int, int]:
    return sum(k for k, _ in por_clase.values()), sum(n for _, n in por_clase.values())


def _se_superponen(a: tuple[int, int], b: tuple[int, int]) -> bool | None:
    if a[1] == 0 or b[1] == 0:
        return None
    (l1, h1), (l2, h2) = metricas.wilson(*a), metricas.wilson(*b)
    return not (h1 < l2 or h2 < l1)


VARIANTES = (
    (True, "sin `mixto` ni `ninguna`", "los ítems donde el humano puso `mixto` o `ninguna` salen del denominador"),
    (False, "contándolas como desacuerdo", "todos los ítems entran; `mixto` y `ninguna` cuentan como no coincidir"),
)


def _seccion_techo(B: list[dict], pesos: dict[str, float]) -> list[str]:
    L = ["## 1 · El techo (estrato B)", "",
         "Estrato B: commits del dataset con el prefijo ya quitado, por cuotas de clase. El techo es "
         "el acuerdo **humano ↔ etiqueta declarada** (`DESIGN.md` §7.5). Se da por clase declarada, "
         "con el número de ítems al lado y el intervalo de Wilson al 95%. El global reponderado usa "
         "las proporciones reales del dataset: " + ", ".join(f"`{c}` {_pct(pesos[c])}" for c in ETIQUETAS)
         + ". Su intervalo es normal, `var = Σ wc²·pc(1-pc)/nc`, sin azar.", ""]
    for solo, nombre, nota in VARIANTES:
        h = acuerdo_por_clase(B, "humana", "declarada", solo)
        m = acuerdo_por_clase(B, "modelo", "declarada", solo)
        L += [f"### {nombre[0].upper() + nombre[1:]}", "", f"_{nota[0].upper() + nota[1:]}._", "",
              "| clase declarada | n | humano ↔ declarada | modelo ↔ declarada |", "|---|---:|---|---|"]
        for c in ETIQUETAS:
            L.append(f"| `{c}` | {h[c][1]} | {_celda(*h[c])} | {_celda(*m[c])} |")
        hs, ms = _sumar(h), _sumar(m)
        L.append(f"| **global, sin reponderar** | {hs[1]} | {_celda(*hs)} | {_celda(*ms)} |")
        L.append(f"| **global, reponderado** | {hs[1]} | **{_celda_rep(h, pesos)}** | {_celda_rep(m, pesos)} |")
        L.append("")
    vs = _valen(B, True)
    kappa = metricas.kappa_cohen([f["declarada"] for f in vs], [f["humana"] for f in vs], ETIQUETAS)
    L += [f"Kappa de Cohen humano ↔ declarada, sin `mixto` ni `ninguna`: **{_num(kappa)}** (n = {len(vs)}). "
          "Se calcula sobre la muestra por cuotas, no sobre el dataset: las cuotas cambian la "
          "prevalencia de cada clase y con ella el acuerdo esperado por azar.", "",
          "### Qué puso el humano en cada clase declarada", "",
          "Conteos. Fila: etiqueta declarada. Columna: lo que puso el humano.", "",
          "| declarada \\ humano | " + " | ".join(f"`{c}`" for c in ETIQUETAS_HUMANAS) + " |",
          "|---" + "|---:" * len(ETIQUETAS_HUMANAS) + "|"]
    for c in ETIQUETAS:
        cnt = Counter(f["humana"] for f in B if f["declarada"] == c)
        L.append(f"| `{c}` | " + " | ".join(str(cnt.get(e, 0)) for e in ETIQUETAS_HUMANAS) + " |")
    return L + [""]


def _seccion_modelo(A: list[dict], B: list[dict], pesos: dict[str, float]) -> list[str]:
    L = ["## 2 · Modelo contra humano y contra prefijo", "",
         f"Modelo: `{MODELO_F3}`, el clásico de referencia de la F2. Cada ítem del estrato B lo predice un "
         "modelo entrenado **sin el repo** de ese ítem (el fold de la partición por repositorio); cada ítem "
         "del estrato A, uno entrenado con todo el dataset, porque esos repos no están en él. "
         "El estrato A no tiene etiqueta declarada, y por eso no hay techo ni reponderación ahí.", ""]
    for solo, nombre, _ in VARIANTES:
        h = acuerdo_por_clase(B, "humana", "declarada", solo)
        m = acuerdo_por_clase(B, "modelo", "declarada", solo)
        mh = acuerdo_por_clase(B, "modelo", "humana", solo)
        ma = acuerdo(A, "modelo", "humana", solo)
        L += [f"### {nombre[0].upper() + nombre[1:]}", "",
              "| medida | estrato | n | sin reponderar | reponderado al dataset |", "|---|---|---:|---|---|",
              f"| humano ↔ declarada (**techo**) | B | {_sumar(h)[1]} | {_celda(*_sumar(h))} | {_celda_rep(h, pesos)} |",
              f"| modelo ↔ declarada | B | {_sumar(m)[1]} | {_celda(*_sumar(m))} | {_celda_rep(m, pesos)} |",
              f"| modelo ↔ humano | B | {_sumar(mh)[1]} | {_celda(*_sumar(mh))} | {_celda_rep(mh, pesos)} |",
              f"| modelo ↔ humano | A | {ma[1]} | {_celda(*ma)} | — |", ""]
        r_h, r_m = reponderado(h, pesos), reponderado(m, pesos)
        if solo and r_h is not None and r_m is not None and r_m[0] > r_h[0]:
            L += [f"> **El modelo coincide más con la etiqueta declarada ({_pct(r_m[0])}) que el humano "
                  f"({_pct(r_h[0])}).** Por `DESIGN.md` §7.5 eso no es una buena noticia: sugiere que aprende "
                  "algo distinto de la tarea (la costumbre de cada proyecto al etiquetar) y hay que "
                  "investigarlo antes de creerle a los demás números.", ""]
    return L


def _seccion_fuera(A: list[dict], B: list[dict]) -> list[str]:
    L = ["## 3 · Fuera de la convención (estrato A)", "",
         "Commits **sin prefijo** de cuatro repos que el dataset nunca vio. No hay etiqueta declarada: "
         "solo se puede medir cuánto se parece el modelo al humano. La caída de B a A es la medición "
         "directa del sesgo de selección de `DESIGN.md` §4.1, que hasta aquí solo estaba declarado.", "",
         "### Modelo ↔ humano, por estrato", "",
         "Sin reponderar en los dos, para que los estratos sean comparables. **No se promedian entre sí.**", "",
         "| variante | n en B | B | n en A | A | diferencia A − B | intervalos |", "|---|---:|---|---:|---|---:|---|"]
    for solo, nombre, _ in VARIANTES:
        b, a = acuerdo(B, "modelo", "humana", solo), acuerdo(A, "modelo", "humana", solo)
        sup = _se_superponen(a, b)
        dif = "—" if a[1] == 0 or b[1] == 0 else _puntos(a[0] / a[1] - b[0] / b[1])
        veredicto = "—" if sup is None else ("se superponen: la diferencia no es concluyente" if sup else "no se superponen")
        L.append(f"| {nombre} | {b[1]} | {_celda(*b)} | {a[1]} | {_celda(*a)} | {dif} | {veredicto} |")
    L += ["", "### Por repo (variante sin `mixto` ni `ninguna`)", "",
          "| repo | ítems | con clase del humano | modelo ↔ humano |", "|---|---:|---:|---|"]
    for repo in sorted({f["repo"] for f in A}):
        fs = [f for f in A if f["repo"] == repo]
        k, n = acuerdo(fs, "modelo", "humana", True)
        L.append(f"| `{repo}` | {len(fs)} | {n} | {_celda(k, n)} |")
    L += ["", "### Qué puso el humano y qué predijo el modelo en A", "",
          "| | " + " | ".join(f"`{e}`" for e in ETIQUETAS_HUMANAS) + " |", "|---" + "|---:" * len(ETIQUETAS_HUMANAS) + "|"]
    ch, cm = Counter(f["humana"] for f in A), Counter(f["modelo"] for f in A)
    L.append("| humano | " + " | ".join(str(ch.get(e, 0)) for e in ETIQUETAS_HUMANAS) + " |")
    L.append("| modelo | " + " | ".join(str(cm.get(e, 0)) if e in ETIQUETAS else "—" for e in ETIQUETAS_HUMANAS) + " |")
    return L + [""]


def _seccion_ruido(filas: list[dict]) -> list[str]:
    humana = {f["id"]: f["humana"] for f in filas}
    L = ["## 4 · El ruido del propio anotador", "",
         "Ítems que se mostraron dos veces, la segunda al final y sin avisar. El acuerdo de uno consigo "
         "mismo es la cota de ruido del techo: ningún acuerdo con una etiqueta declarada debería "
         "pedirse más alto que el que el humano logra con sus propias respuestas. Cuenta `mixto` y "
         "`ninguna` como etiquetas.", "",
         "| estrato | pares | acuerdo consigo mismo | kappa |", "|---|---:|---|---:|"]
    for estrato in ("A", "B"):
        pares = [(humana[f["repeticion_de"]], f["humana"]) for f in filas
                 if f["repeticion_de"] and f["estrato"] == estrato]
        k = sum(a == b for a, b in pares)
        kappa = metricas.kappa_cohen([a for a, _ in pares], [b for _, b in pares], ETIQUETAS_HUMANAS)
        L.append(f"| {estrato} | {len(pares)} | {_celda(k, len(pares))} | {_num(kappa)} |")
    return L + [""]


def _seccion_evidencia(A: list[dict], B: list[dict]) -> list[str]:
    L = ["## 5 · Cuántas veces no alcanzó la evidencia", "",
         "El humano ve lo mismo que el modelo: mensaje, archivos y líneas, **no** el texto del diff. "
         "`?` marca los ítems donde habría querido verlo. Es el dato que dice si el texto del diff, "
         "declarado como pendiente en `DESIGN.md` §6.2, hace falta de verdad en la F4.", "",
         "| estrato | n | `?` (habría querido el diff) | `mixto` | `ninguna` |", "|---|---:|---|---|---|"]
    for nombre, fs in (("A", A), ("B", B)):
        n = len(fs)
        L.append(f"| {nombre} | {n} | {_celda(sum(f['necesita_diff'] for f in fs), n)} | "
                 f"{_celda(sum(f['humana'] == 'mixto' for f in fs), n)} | "
                 f"{_celda(sum(f['humana'] == 'ninguna' for f in fs), n)} |")
    return L + [""]


def _seccion_coste(filas: list[dict]) -> list[str]:
    seg = sorted(f["segundos"] for f in filas)
    mediana = statistics.median(seg)
    p90 = seg[int(0.9 * (len(seg) - 1))]
    return ["## 6 · Coste", "",
            f"{len(seg)} ítems etiquetados (repeticiones incluidas). Mediana **{mediana:.0f} s** por ítem, "
            f"percentil 90 {p90:.0f} s. La suma es {sum(seg) / 3600:.1f} h e incluye las pausas que hubo "
            "con un ítem en pantalla: la mediana es la cifra fiable. Presupuesto de la fase: 8 h.", ""]


def _seccion_f2(doc: dict | None) -> list[str]:
    if doc is None:
        return []
    L = ["## 7 · Contra los números de la F2", "",
         f"Exactitud de `{MODELO_F3}` en la partición por repositorio de la F2 (2.000 commits por fold, "
         "con la proporción real de clases). Un fold por fila y sin promedio, como en `docs/F2_BASELINES.md`. "
         "Se compara con la fila **reponderado** de la sección 2, no con la de sin reponderar: la muestra "
         "humana está por cuotas de clase y su exactitud cruda no es comparable.", "",
         "| fold | n prueba | exactitud | F1 macro |", "|---|---:|---|---|"]
    for r in doc["resumen"]:
        L.append(f"| `{r['fold']}` | {r['n_prueba']} | {_pct(r['exactitud']['media'])} | {_pct(r['f1_macro']['media'])} |")
    return L + [""]


def render(filas: list[dict], meta_f3: dict, meta_f0: dict, f2_repositorio: dict | None = None,
           predicciones_sha256: str | None = None) -> str:
    originales = [f for f in filas if not f["repeticion_de"]]
    A = [f for f in originales if f["estrato"] == "A"]
    B = [f for f in originales if f["estrato"] == "B"]
    pesos = pesos_del_dataset(meta_f0["por_clase"])
    L = ["# F3 · Techo humano", "",
         "Generado por `python -m ccls f3 report`. **No se edita a mano.** El diseño de la fase está en "
         "`DESIGN.md` §4.2 y §7.5; cómo se leen los números, en §7.3 y §7.4.", "",
         f"- Dataset: `manifest_sha256` `{meta_f0['manifest_sha256']}`.",
         f"- Muestra: `hoja_sha256` `{meta_f3['hoja_sha256']}`, `clave_sha256` `{meta_f3['clave_sha256']}`.",
         *([f"- Predicciones del modelo: sha256 `{predicciones_sha256}`."] if predicciones_sha256 else []),
         f"- Semilla del muestreo: {meta_f3['parametros']['semilla']}. Cuotas del estrato B: "
         + ", ".join(f"{c} {n}" for c, n in meta_f3["parametros"]["cuotas_estrato_b"].items()) + ".",
         "- Estrato A, repos y SHA fijados: "
         + ", ".join(f"`{r['owner_repo']}` @ `{r['sha'][:10]}`" for r in meta_f3["repos_estrato_a"]) + ".",
         f"- {len(A)} ítems en A, {len(B)} en B y {len(filas) - len(originales)} repeticiones.", "",
         "## Cómo hay que leer esto", "",
         "**Un techo bajo es un resultado, no un fallo.** No se re-muestreó ni se ajustó nada después de ver la "
         "cifra (`DESIGN.md` §7.5 y §9).", "",
         "**Los dos estratos miden cosas distintas y no se mezclan.** B tiene etiqueta declarada y da el techo; "
         "A no la tiene y da el caso de uso real. Ninguna tabla los promedia entre sí.", "",
         "**Cada acuerdo lleva su n y su intervalo.** Con 35-40 ítems por clase el intervalo de Wilson es ancho "
         "(±12-15 puntos): una diferencia de pocos puntos entre dos celdas no significa nada, y cuando los "
         "intervalos se superponen se dice.", ""]
    L += _seccion_techo(B, pesos) + _seccion_modelo(A, B, pesos) + _seccion_fuera(A, B)
    L += _seccion_ruido(filas) + _seccion_evidencia(A, B) + _seccion_coste(filas) + _seccion_f2(f2_repositorio)
    return "\n".join(L).rstrip("\n") + "\n"
