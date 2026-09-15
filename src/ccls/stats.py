"""Estadísticas descriptivas del dataset de la F0 -> docs/F0_ESTADISTICAS.md.

Se genera desde data/processed/dataset.jsonl y dataset_meta.json; no se edita a mano.
Cumple el "con estadísticas descriptivas" de la F0 (DESIGN.md §8) y reemplaza la
proyección de clases de DESIGN.md §4.4 por el número real.
"""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from ccls.fuga_correlacion import MIN_SOPORTE, UMBRAL_GANANCIA, medir, solo_docs, sospechosas, tabla_md
from ccls.label import contiene_fuga, diff_repite_mensaje_propio

CLASES = ("fix", "feat", "refactor", "docs")
REFACTOR_PROYECTADO = 1090  # DESIGN.md §4.4


def cargar_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(linea) for linea in f if linea.strip()]


def _pct(a: int, b: int) -> str:
    return f"{a / b:.1%}" if b else "—"


def _p90(valores: list[int]) -> float:
    return statistics.quantiles(valores, n=10)[-1] if len(valores) >= 2 else float(valores[0] if valores else 0)


def render(registros: list[dict], meta: dict) -> str:
    por_repo: dict[str, list[dict]] = defaultdict(list)
    por_clase: dict[str, list[dict]] = defaultdict(list)
    for r in registros:
        por_repo[r["repo"]].append(r)
        por_clase[r["label"]].append(r)
    resumenes = meta["repos"]
    params = meta["parametros"]
    n = len(registros)
    L: list[str] = []

    L.append("# Estadísticas descriptivas del dataset (F0)\n")
    L.append(
        "Generado por `python -m ccls f0 stats` desde `data/processed/dataset.jsonl` y "
        "`dataset_meta.json`. **No se edita a mano.**\n"
    )

    # --- 1. Origen ---------------------------------------------------------------
    L.append("## 1 · De dónde sale cada commit\n")
    L.append(
        f"Población: `{params['poblacion']}`, historial completo desde el SHA fijado en "
        "`config/repos.yaml`. *Etiquetables*: el prefijo es de una de las 4 clases. Muestra "
        f"estratificada por {params['estrato']}, con tope de {params['tope_commits_por_repo']} por repo.\n"
    )
    L.append("| repo | SHA | commits | etiquetables | tasa | muestreados | trimestres | primer commit | último commit |")
    L.append("|---|---|---:|---:|---:|---:|---:|---|---|")
    for res in resumenes:
        fechas = sorted(r["committer_date"] for r in por_repo[res["owner_repo"]])
        L.append(
            f"| {res['owner_repo']} | `{res['sha'][:10]}` | {res['commits']} | {res['etiquetables']} | "
            f"{_pct(res['etiquetables'], res['commits'])} | {res['muestreados']} | {res['trimestres']} | "
            f"{fechas[0][:10] if fechas else '—'} | {fechas[-1][:10] if fechas else '—'} |"
        )
    tot_c = sum(r["commits"] for r in resumenes)
    tot_e = sum(r["etiquetables"] for r in resumenes)
    L.append(f"| **total** | | {tot_c} | {tot_e} | {_pct(tot_e, tot_c)} | **{n}** | | | |")
    L.append("")

    # --- 2. Clases ---------------------------------------------------------------
    L.append("## 2 · Distribución de clases\n")
    L.append(
        "La columna *% refactor en historial* es la proporción entre **todos** los commits "
        "etiquetables del repo, antes de muestrear; si se parece a la de la muestra, el "
        "muestreo no movió el balance.\n"
    )
    L.append("| repo | fix | feat | refactor | docs | total | % refactor | % refactor en historial |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for res in resumenes:
        cnt = Counter(r["label"] for r in por_repo[res["owner_repo"]])
        hist = res["etiquetables_por_clase"]
        L.append(
            f"| {res['owner_repo']} | " + " | ".join(str(cnt.get(k, 0)) for k in CLASES)
            + f" | {sum(cnt.values())} | {_pct(cnt.get('refactor', 0), sum(cnt.values()))} | "
            f"{_pct(hist['refactor'], res['etiquetables'])} |"
        )
    tot = Counter(r["label"] for r in registros)
    L.append(
        "| **total** | " + " | ".join(f"**{tot.get(k, 0)}**" for k in CLASES)
        + f" | **{n}** | **{_pct(tot.get('refactor', 0), n)}** | |"
    )
    L.append("")
    L.append("| clase | commits | % del dataset |")
    L.append("|---|---:|---:|")
    for k in CLASES:
        L.append(f"| {k} | {tot.get(k, 0)} | {_pct(tot.get(k, 0), n)} |")
    L.append("")

    n_ref = tot.get("refactor", 0)
    ref_por_repo = sorted(
        ((sum(1 for r in por_repo[res["owner_repo"]] if r["label"] == "refactor"), res["owner_repo"]) for res in resumenes),
        reverse=True,
    )
    if n_ref:
        mayor, menor = ref_por_repo[0], ref_por_repo[-1]
        L.append(
            f"**`refactor`: {n_ref} ejemplos ({_pct(n_ref, n)}).** DESIGN.md §4.4 proyectaba "
            f"~{REFACTOR_PROYECTADO} a partir de los commits recientes del piloto; este es el número "
            f"con muestreo sobre todo el historial. {mayor[1]} aporta {mayor[0]} "
            f"({_pct(mayor[0], n_ref)} de todos los `refactor`); {menor[1]}, {menor[0]}.\n"
        )

    # --- 3. Cobertura temporal ---------------------------------------------------
    L.append("## 3 · Cobertura temporal (commits muestreados por año)\n")
    anios = sorted({r["committer_date"][:4] for r in registros})
    L.append("| repo | " + " | ".join(anios) + " |")
    L.append("|---|" + "---:|" * len(anios))
    for res in resumenes:
        cnt = Counter(r["committer_date"][:4] for r in por_repo[res["owner_repo"]])
        L.append(f"| {res['owner_repo']} | " + " | ".join(str(cnt.get(a, 0)) for a in anios) + " |")
    L.append("")

    # --- 4. Tamaño ---------------------------------------------------------------
    L.append("## 4 · Tamaño de los commits por clase\n")
    L.append(
        f"*Líneas* = agregadas + eliminadas según `--numstat`. El diff se guarda truncado a "
        f"{params['diff_max_chars']} caracteres; *% truncado* dice a cuántos les afecta.\n"
    )
    L.append("| clase | commits | mediana archivos | mediana líneas | p90 líneas | % diff truncado | % toca tests | % solo docs |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for k in CLASES:
        rs = por_clase.get(k, [])
        if not rs:
            continue
        lineas = [r["lines_added"] + r["lines_deleted"] for r in rs]
        L.append(
            f"| {k} | {len(rs)} | {statistics.median(r['n_files'] for r in rs):.0f} | "
            f"{statistics.median(lineas):.0f} | {_p90(lineas):.0f} | "
            f"{_pct(sum(r['diff_truncado'] for r in rs), len(rs))} | "
            f"{_pct(sum(r['toca_tests'] for r in rs), len(rs))} | "
            f"{_pct(sum(solo_docs(r['files']) for r in rs), len(rs))} |"
        )
    L.append("")

    # --- 5. Señales a vigilar en F2 ---------------------------------------------
    L.append("## 5 · Señales a vigilar en la F2\n")
    L.append(
        "No son entradas decididas: se guardan como banderas para medir cuánto aportan por sí "
        "solas antes de decidir si se usan (LEAKAGE.md). *Autor bot*: renovate, dependabot o "
        "nombre con `[bot]`. *Breaking*: el prefijo llevaba `!` — sale del prefijo, así que es "
        "solo auditoría.\n"
    )
    L.append("| clase | % autor bot | % referencia a issue | % breaking |")
    L.append("|---|---:|---:|---:|")
    for k in CLASES:
        rs = por_clase.get(k, [])
        if not rs:
            continue
        L.append(
            f"| {k} | {_pct(sum(r['es_bot'] for r in rs), len(rs))} | "
            f"{_pct(sum(r['tiene_referencia_issue'] for r in rs), len(rs))} | "
            f"{_pct(sum(r['auditoria']['breaking'] for r in rs), len(rs))} |"
        )
    L.append("")
    bots_repo = {res["owner_repo"]: sum(r["es_bot"] for r in por_repo[res["owner_repo"]]) for res in resumenes}
    L.append("Commits de bot por repo: " + ", ".join(f"{k} {v}" for k, v in bots_repo.items()) + ".\n")

    # --- 6. Baseline docs --------------------------------------------------------
    L.append("## 6 · Baseline de una línea para `docs`, sobre el dataset final\n")
    L.append("Regla: \"si todos los archivos tocados son .md/.rst/.txt → docs\" (DESIGN.md §6.1).\n")
    L.append("| repo | precisión | recall | F1 |")
    L.append("|---|---:|---:|---:|")
    grupos = [(res["owner_repo"], por_repo[res["owner_repo"]]) for res in resumenes] + [("**todos**", registros)]
    for nombre, rs in grupos:
        tp = sum(1 for r in rs if solo_docs(r["files"]) and r["label"] == "docs")
        fp = sum(1 for r in rs if solo_docs(r["files"]) and r["label"] != "docs")
        fn = sum(1 for r in rs if not solo_docs(r["files"]) and r["label"] == "docs")
        p = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * p * rc / (p + rc) if p + rc else 0.0
        L.append(f"| {nombre} | {p:.2f} | {rc:.2f} | {f1:.2f} |")
    L.append("")

    # --- 7. Fuga del prefijo ----------------------------------------------------
    L.append("## 7 · Prefijo de convención y rutas excluidas (LEAKAGE.md §7.2)\n")
    fuga_msg = sum(1 for r in registros if contiene_fuga(r["message"]))
    fuga_diff = sum(
        1 for r in registros
        if diff_repite_mensaje_propio(r["diff"], r["auditoria"]["tipo_declarado"], r["message"].split("\n")[0])
    )
    generico_diff = sum(1 for r in registros if contiene_fuga(r["diff"]))
    vacios = sum(1 for r in registros if not r["message"].strip())
    L.append("| chequeo | registros |")
    L.append("|---|---:|")
    L.append(f"| `message` con prefijo (detector genérico) — **debe ser 0** | {fuga_msg} |")
    L.append(f"| `diff` que repite el mensaje del propio commit con su prefijo — **debe ser 0** | {fuga_diff} |")
    L.append(f"| `diff` con algún `tipo:` al inicio de línea (detector genérico; informativo, es código) | {generico_diff} |")
    L.append("")
    L.append(f"Mensajes vacíos después de quitar el prefijo: {vacios}.\n")
    rutas = params.get("rutas_excluidas", [])
    if rutas:
        excl = Counter(r["repo"] for r in registros if r["auditoria"]["n_archivos_excluidos"])
        diff_vacio = sum(1 for r in registros if not r["diff"].strip())
        L.append(
            f"Rutas excluidas de `diff`, `files`, extensiones y conteo de líneas: "
            f"{', '.join(f'`{p}`' for p in rutas)}. Afectan a {sum(excl.values())} commits "
            f"({', '.join(f'{k} {v}' for k, v in sorted(excl.items()))}). Registros del dataset con el diff "
            f"vacío, por cualquier motivo: {diff_vacio}.\n"
        )

    # --- 8. Fuga por correlación -------------------------------------------------
    L.append("## 8 · Fuga por correlación (LEAKAGE.md §7.3)\n")
    mediciones = medir(registros)
    L.append(
        f"Para cada token candidato, la clase donde más se concentra, en el dataset entero y en cada repo "
        f"donde aparece. Todo se mide por separado en los estratos *solo docs* y *no solo docs* (la regla "
        f"estructural de DESIGN.md §6.1): un token cuenta como fuga solo si dice algo más que esa regla. "
        f"Falla si la ganancia es >= {UMBRAL_GANANCIA} con al menos {MIN_SOPORTE} registros con el token. "
        f"Ganancia = (cota inferior de Wilson de P(c|t) − P(c)) / (1 − P(c)), con P(c) dentro del estrato.\n"
    )
    L.extend(tabla_md(mediciones))
    L.append("")
    L.append(f"Tokens que fallan: **{len(sospechosas(mediciones))}**.\n")

    # --- 9. Versionado -----------------------------------------------------------
    L.append("## 9 · Versionado\n")
    L.append(f"- `manifest_sha256`: `{meta['manifest_sha256']}`")
    L.append(f"- `dataset_jsonl_sha256`: `{meta['dataset_jsonl_sha256']}` ({meta['git_version']})")
    L.append(f"- semilla {params['semilla']}, tope {params['tope_commits_por_repo']} por repo, "
             f"diff truncado a {params['diff_max_chars']} caracteres con {params['lineas_contexto_diff']} líneas de contexto")
    L.append("")
    return "\n".join(L) + "\n"
