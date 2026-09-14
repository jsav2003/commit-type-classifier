"""Renderiza docs/PILOTO.md a partir de data/interim/pilot_results.json.

Las cinco tablas que pide la Parte B del plan de arranque (B2.1-B2.5), más la
proyección y el veredicto de la puerta de decisión (B3).
"""

from __future__ import annotations

import math

TOPE_COMMITS_POR_REPO = 2000
META_MINIMA = 20_000
META_MAXIMA = 50_000
UMBRAL_PREFIJO = 0.50  # ver config/repos.yaml: bajado de 0.60 con datos del piloto, no a ciegas
UMBRAL_PERDIDA_MERGE = 0.80
UMBRAL_CLASE_MINORITARIA = 0.05


def _tasa_prefijo(m: dict) -> float:
    n = m["n_muestreados"]
    return m["n_con_prefijo_valido"] / n if n else 0.0


def _pct_perdido_merge(m: dict) -> float:
    if m["total"] == 0:
        return 0.0
    return 1 - (m["no_merges_first_parent"] / m["total"])


def _f1_docs(m: dict) -> tuple[float, float, float]:
    tp, fp, fn = m["tp"], m["fp"], m["fn"]
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f1


def render_piloto_md(resultados: dict) -> str:
    pc = resultados.get("prefijo_clases", {})
    ml = resultados.get("merge_loss", {})
    db = resultados.get("docs_baseline", {})
    cc = resultados.get("costo_clonado", {})

    repos = sorted(pc.keys())
    lineas: list[str] = []
    lineas.append("# Resultados del piloto\n")
    lineas.append(
        "Generado por `python -m ccls pilot report`. Reemplaza tres supuestos del "
        "diseño por números medidos — ver DESIGN.md §4-6 y la Parte B del plan de "
        "arranque. **No se editó a mano.**\n"
    )

    # --- Tabla 1: B2.1 tasa de prefijo + B2.2 distribución de clases -------
    lineas.append("## B2.1 / B2.2 · Tasa de prefijo válido y distribución de clases\n")
    lineas.append(
        "Muestra: últimos N commits de `git log --no-merges --first-parent` por repo — "
        "la misma población que usará la extracción real (C2), no el log crudo. Medir "
        "sobre el log crudo diluiría la tasa con commits de merge, que nunca llevan "
        "prefijo `tipo:` y no iban a entrar al dataset de todos modos.\n"
    )
    lineas.append("| repo | muestreados | tasa prefijo válido | fix | feat | refactor | docs |")
    lineas.append("|---|---:|---:|---:|---:|---:|---:|")
    for r in repos:
        m = pc[r]
        d = m["distribucion"]
        lineas.append(
            f"| {r} | {m['n_muestreados']} | {_tasa_prefijo(m):.1%} | "
            f"{d.get('fix', 0)} | {d.get('feat', 0)} | {d.get('refactor', 0)} | {d.get('docs', 0)} |"
        )
    lineas.append("")

    # --- Tabla 2: B2.4 pérdida por --no-merges --first-parent ---------------
    lineas.append("## B2.4 · Commits perdidos por `--no-merges --first-parent`\n")
    lineas.append("Sobre el historial completo del repo (no una muestra).\n")
    lineas.append("| repo | total | no_merges | first_parent | no_merges+first_parent | % perdido | veredicto |")
    lineas.append("|---|---:|---:|---:|---:|---:|---|")
    repos_excluidos_merge = []
    for r in sorted(ml.keys()):
        m = ml[r]
        pct = _pct_perdido_merge(m)
        veredicto = "SACAR / estrategia propia" if pct > UMBRAL_PERDIDA_MERGE else "ok"
        if pct > UMBRAL_PERDIDA_MERGE:
            repos_excluidos_merge.append(r)
        lineas.append(
            f"| {r} | {m['total']} | {m['no_merges']} | {m['first_parent']} | "
            f"{m['no_merges_first_parent']} | {pct:.1%} | {veredicto} |"
        )
    lineas.append("")

    # --- Tabla 3: B2.5 baseline trivial para 'docs' -------------------------
    lineas.append("## B2.5 · Baseline de una línea para la clase `docs`\n")
    lineas.append("Regla: \"si todos los archivos tocados son .md/.rst/.txt → docs\". Evaluada contra la etiqueta declarada.\n")
    lineas.append("| repo | evaluados | precisión | recall | F1 |")
    lineas.append("|---|---:|---:|---:|---:|")
    for r in sorted(db.keys()):
        m = db[r]
        p, rec, f1 = _f1_docs(m)
        lineas.append(f"| {r} | {m['n_evaluados']} | {p:.2f} | {rec:.2f} | {f1:.2f} |")
    lineas.append("")
    f1s = [_f1_docs(db[r])[2] for r in db if db[r]["n_evaluados"] > 0]
    if f1s:
        f1_prom = sum(f1s) / len(f1s)
        alerta = (
            f"**F1 promedio {f1_prom:.2f} — alto**: la clase `docs` puede ser casi trivial de "
            f"acertar por una señal estructural; un F1 macro alto de cualquier modelo puede "
            f"estar inflado por esta clase sin que haya aprendizaje real sobre las otras tres."
            if f1_prom >= 0.7
            else f"F1 promedio {f1_prom:.2f} — no parece trivialmente resoluble por extensión de archivo sola."
        )
        lineas.append(alerta + "\n")

    # --- Tabla 4: B2.3 coste de clonado -------------------------------------
    lineas.append("## B2.3 · Coste de clonado (historial completo, sin acotar por fecha)\n")
    if cc:
        lineas.append("| estrategia | clon (s) | extracción -p --numstat (s) | disco (MB) | ok |")
        lineas.append("|---|---:|---:|---:|---|")
        for etiqueta in ("completo", "filter_blob_none"):
            if etiqueta not in cc:
                continue
            m = cc[etiqueta]
            ok = m["clone_ok"] and m["extract_ok"]
            lineas.append(f"| {etiqueta} | {m['clone_s']:.1f} | {m['extract_s']:.1f} | {m['disco_mb']:.1f} | {ok} |")
        lineas.append("")
        if "completo" in cc and "filter_blob_none" in cc:
            t_completo = cc["completo"]["clone_s"] + cc["completo"]["extract_s"]
            t_filtrado = cc["filter_blob_none"]["clone_s"] + cc["filter_blob_none"]["extract_s"]
            ganador = "completo" if t_completo <= t_filtrado else "filter_blob_none"
            lineas.append(
                f"**Estrategia elegida para la F0: `{ganador}`** "
                f"(tiempo total clon+extracción: completo={t_completo:.1f}s, "
                f"filter_blob_none={t_filtrado:.1f}s).\n"
            )
    else:
        lineas.append("_sin datos — correr `python -m ccls pilot clone-cost`._\n")

    # --- Proyección y puerta de decisión ------------------------------------
    lineas.append("## Proyección y puerta de decisión\n")
    admitidos = []
    for r in repos:
        tasa = _tasa_prefijo(pc[r])
        perdida = _pct_perdido_merge(ml.get(r, {"total": 0, "no_merges_first_parent": 0})) if r in ml else 1.0
        pasa = tasa >= UMBRAL_PREFIJO and perdida <= UMBRAL_PERDIDA_MERGE
        total_utilizable = ml.get(r, {}).get("no_merges_first_parent", 0)
        usable = min(TOPE_COMMITS_POR_REPO, round(total_utilizable * tasa)) if pasa else 0
        admitidos.append((r, tasa, perdida, pasa, usable))

    lineas.append("| repo | tasa prefijo | % perdido merge | admitido | commits utilizables estimados |")
    lineas.append("|---|---:|---:|---|---:|")
    for r, tasa, perdida, pasa, usable in admitidos:
        lineas.append(f"| {r} | {tasa:.1%} | {perdida:.1%} | {'sí' if pasa else 'NO'} | {usable} |")
    lineas.append("")

    admitidos_ok = [a for a in admitidos if a[3]]
    suma_usable = sum(a[4] for a in admitidos_ok)
    lineas.append(f"**Total estimado con los {len(admitidos)} candidatos del piloto: {suma_usable} commits "
                   f"utilizables** (de {len(admitidos_ok)} repos admitidos de {len(admitidos)} candidatos).\n")

    if suma_usable >= META_MINIMA:
        lineas.append(f"Ya alcanza el mínimo de {META_MINIMA}. **No hacen falta más repos que los del piloto** "
                       f"para llegar a la meta; en la F0 real se puede ampliar la lista igual para tener margen "
                       f"y mejor diversidad, pero la meta en sí no depende de ello.\n")
    elif admitidos_ok:
        promedio_usable = suma_usable / len(admitidos_ok)
        faltante = META_MINIMA - suma_usable
        repos_adicionales = math.ceil(faltante / promedio_usable) if promedio_usable > 0 else float("inf")
        lineas.append(
            f"Faltan **{faltante} commits** para el mínimo de {META_MINIMA}. Con un promedio de "
            f"{promedio_usable:.0f} commits utilizables por repo admitido, hacen falta "
            f"~**{repos_adicionales} repos adicionales** de perfil similar.\n"
        )
    else:
        lineas.append("**Ningún candidato del piloto fue admitido.** No hay base para proyectar.\n")

    # Veredicto de clases minoritarias
    dist_total = {"fix": 0, "feat": 0, "refactor": 0, "docs": 0}
    for r in repos:
        for k, v in pc[r]["distribucion"].items():
            dist_total[k] = dist_total.get(k, 0) + v
    total_clasificados = sum(dist_total.values())
    lineas.append(f"### Distribución de clases agregada (los {len(repos)} candidatos del piloto)\n")
    if total_clasificados:
        lineas.append("| clase | commits | % del total clasificado |")
        lineas.append("|---|---:|---:|")
        clases_minoritarias = []
        for k in ("fix", "feat", "refactor", "docs"):
            pct = dist_total[k] / total_clasificados
            lineas.append(f"| {k} | {dist_total[k]} | {pct:.1%} |")
            if pct < UMBRAL_CLASE_MINORITARIA:
                clases_minoritarias.append(k)
        lineas.append("")
        if clases_minoritarias:
            lineas.append(
                f"⚠️ **{', '.join(clases_minoritarias)} por debajo del {UMBRAL_CLASE_MINORITARIA:.0%}** "
                f"— riesgo #3 de DESIGN.md §9. Antes de la F0 real hay que decidir reponderación o ampliar "
                f"la búsqueda de repos con más peso en esa clase, y documentar la decisión.\n"
            )
        else:
            lineas.append(f"Ninguna clase por debajo del {UMBRAL_CLASE_MINORITARIA:.0%}. Sin alerta de desbalance severo.\n")

    lineas.append("### Veredicto\n")
    veredicto_ok = suma_usable >= META_MINIMA * 0.5  # umbral laxo: ver si la ruta es viable en absoluto
    if suma_usable >= META_MINIMA:
        lineas.append("**Puerta ABIERTA.** La proyección alcanza el mínimo de 20.000 commits utilizables "
                       "con repos de calidad. Se procede a la F0 completa (Parte C) con la meta original.\n")
    elif suma_usable >= 10_000:
        lineas.append("**Puerta ABIERTA con la regla de rescate (DESIGN.md §8).** No se alcanza el mínimo de "
                       "20.000 con los candidatos del piloto, pero sí una base razonable. Se ajusta la meta a "
                       "10.000 commits de menos repositorios, **por escrito en el README**, antes de seguir.\n")
    else:
        lineas.append("**Puerta CERRADA por ahora.** Ni el mínimo de 20.000 ni el piso de la regla de rescate "
                       "(10.000) son alcanzables con este conjunto de candidatos. Hace falta ampliar la búsqueda "
                       "de repos (más candidatos, o revisar el umbral de tasa de prefijo) antes de comprometerse "
                       "a la F0.\n")

    return "\n".join(lineas) + "\n"
