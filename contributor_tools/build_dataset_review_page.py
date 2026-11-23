#!/usr/bin/env python3
"""Build a dataset's review page (docs/datasets/<slug>/index.html) from its verified R01 bundle.

One command per landing dataset:

    python3 contributor_tools/build_dataset_review_page.py contributor_tools/page_specs/<slug>.json

The spec (JSON) holds the plain-words text a person wrote for that dataset (fix cards,
left-out rows, checked lists). Every number comes from the bundle: manifest.json,
dataset_index.json, exclusions.csv, held_signals.csv, phase_preview.json, the committed
R01 handoff and the fix-scope JSON. The builder never opens full.parquet or
filtered.parquet. Nothing is published.

Gate: the dataset's R01 task in docs/maintainers/backlog.json must be `done` (a second
agent verified the bundle). The page is refused otherwise. `--allow-review` accepts
`review` and exists only for UMich 2021, whose model page was built before its R01 task
was verified; use `done` for every new dataset.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "contributor_tools"))
import dataset_status  # noqa: E402

BACKLOG = ROOT / "docs/maintainers/backlog.json"
FIGJSON_NAME = "figures.json"
VERDICT_CLASS = {"Also wrong, fixed": "v-fixed", "Checked, not affected": "v-ok", "Left out": "v-left", "Not checked": "v-nc"}


class BundleNotReady(Exception):
    """The dataset's R01 task is not done, so no page may be built from its bundle."""


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def check_gate(spec: dict, backlog_path: Path = BACKLOG, allow_review: bool = False) -> None:
    data = json.loads(Path(backlog_path).read_text(encoding="utf-8"))
    task = next((t for t in data["tasks"] if t["id"] == spec["r01_task_id"]), None)
    if task is None:
        raise BundleNotReady(f"{spec['r01_task_id']} is not in the backlog")
    ok = {"done", "review"} if allow_review else {"done"}
    if task["status"] not in ok:
        raise BundleNotReady(f"{spec['r01_task_id']} is {task['status']}, not done; the bundle has not been verified")


def load_inputs(spec: dict, root: Path = ROOT):
    bundle = root / spec["bundle"]
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    index = json.loads((bundle / "dataset_index.json").read_text(encoding="utf-8"))
    with (bundle / "exclusions.csv").open(newline="", encoding="utf-8") as fh:
        excl = list(csv.DictReader(fh))
    with (bundle / "held_signals.csv").open(newline="", encoding="utf-8") as fh:
        held = list(csv.DictReader(fh))
    preview = json.loads((bundle / "phase_preview.json").read_text(encoding="utf-8"))
    r01 = json.loads((root / spec["handoff"]).read_text(encoding="utf-8"))
    if r01["task_id"] != spec["r01_task_id"]:
        raise ValueError(f"handoff is for {r01['task_id']}, spec expects {spec['r01_task_id']}")
    scope = json.loads((root / spec["scope"]).read_text(encoding="utf-8"))
    return manifest, index, excl, held, preview, r01, scope


def cond_name(spec, rec: str) -> str:
    sub, cond = rec.split("/")
    return f"{sub}, {spec['conditions'][cond]}"


# ---------- phase plots ----------
def pool(groups, column):
    """Pool left and right legs of one condition (weighted mean, pooled sample sd)."""
    n_s = [g["columns"][column]["n"] for g in groups]
    m_s = [g["columns"][column]["mean"] for g in groups]
    s_s = [g["columns"][column]["sd"] for g in groups]
    mean, sd = [], []
    for i in range(150):
        parts = [(n[i], m[i], s[i]) for n, m, s in zip(n_s, m_s, s_s) if n[i] and m[i] is not None]
        N = sum(p[0] for p in parts)
        if N < 2:
            mean.append(None)
            sd.append(None)
            continue
        M = sum(n * m for n, m, _ in parts) / N
        ss = sum((n - 1) * (s or 0.0) ** 2 + n * (m - M) ** 2 for n, m, s in parts)
        mean.append(M)
        sd.append(math.sqrt(ss / (N - 1)))
    return mean, sd


def nice_ticks(lo, hi):
    span = hi - lo or 1.0
    raw = span / 4
    mag = 10 ** math.floor(math.log10(raw))
    step = min((m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw), default=mag)
    start = math.ceil(lo / step) * step
    ticks, t = [], start
    while t <= hi + 1e-9:
        ticks.append(round(t, 10))
        t += step
    return ticks


def fmt(v):
    s = f"{v:.3g}"
    return "0" if s in ("-0", "0") else s


def panel_svg(title, series, lo, hi, unit, colors):
    W, H, L, R, T, B = 320, 220, 46, 16, 22, 34
    pw, ph = W - L - R, H - T - B

    def X(i):
        return L + pw * i / 149

    def Y(v):
        return T + ph * (1 - (v - lo) / (hi - lo))

    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(title)}: mean with spread over the stride, {esc(unit)}" xmlns="http://www.w3.org/2000/svg">',
           f'<text x="{L}" y="14" font-size="12" font-weight="600" fill="currentColor">{esc(title)}</text>']
    for t in nice_ticks(lo, hi):
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" stroke="currentColor" stroke-opacity=".15"/>')
        out.append(f'<text x="{L - 4}" y="{Y(t) + 4:.1f}" font-size="11" text-anchor="end" fill="currentColor">{fmt(t)}</text>')
    for p in (0, 50, 100):
        x = L + pw * p / 100
        out.append(f'<text x="{x:.1f}" y="{H - 18}" font-size="11" text-anchor="middle" fill="currentColor">{p}</text>')
    out.append(f'<text x="{L + pw / 2:.1f}" y="{H - 4}" font-size="11" text-anchor="middle" fill="currentColor">stride (%)</text>')
    out.append(f'<rect x="{L}" y="{T}" width="{pw}" height="{ph}" fill="none" stroke="currentColor" stroke-opacity=".35"/>')
    for cond, mean, sd in series:
        idx = [i for i in range(150) if mean[i] is not None]
        if len(idx) < 2:
            continue
        up = " ".join(f"{X(i):.1f},{Y(mean[i] + sd[i]):.1f}" for i in idx)
        dn = " ".join(f"{X(i):.1f},{Y(mean[i] - sd[i]):.1f}" for i in reversed(idx))
        line = " ".join(f"{X(i):.1f},{Y(mean[i]):.1f}" for i in idx)
        out.append(f'<polygon points="{up} {dn}" fill="{colors[cond]}" fill-opacity=".18" stroke="none"/>')
        out.append(f'<polyline points="{line}" fill="none" stroke="{colors[cond]}" stroke-width="1.6"/>')
    out.append("</svg>")
    return "".join(out)



def phase_section(spec, preview, columns):
    groups = preview["groups"]
    by = {}
    for g in groups:
        by.setdefault((g["task"], g["condition"]), []).append(g)
    conditions, colors = spec["conditions"], spec["colors"]
    parts = []
    for ci, col in enumerate(columns):
        name, unit = spec["plain"][col]["name"], spec["plain"][col]["unit"]
        pooled = {}
        lo, hi = math.inf, -math.inf
        for panel in spec["panels"]:
            for c in panel["conditions"]:
                if (panel["task"], c) not in by:
                    continue
                m, s = pool(by[(panel["task"], c)], col)
                pooled[(panel["task"], c)] = (m, s)
                for a, b in zip(m, s):
                    if a is not None:
                        lo, hi = min(lo, a - b), max(hi, a + b)
        pad = (hi - lo) * 0.05 or 1
        lo, hi = lo - pad, hi + pad
        panels = []
        for panel in spec["panels"]:
            series = [(c, *pooled[(panel["task"], c)]) for c in panel["conditions"] if (panel["task"], c) in pooled]
            if series:
                panels.append(f'<figure class="phase-panel">{panel_svg(panel["label"], series, lo, hi, unit, colors)}</figure>')
        legend = "".join(f'<span><i style="background:{colors[c]}"></i>{conditions[c]}</span>' for c in colors)
        open_attr = " open" if ci == 0 else ""
        parts.append(
            f'<details class="phase-signal"{open_attr}><summary><strong>{esc(name)}</strong> <span class="phase-unit">{esc(unit)}</span></summary>'
            f'<div class="phase-grid">{"".join(panels)}</div><p class="phase-legend">{legend}</p></details>')
    return "".join(parts)


# ---------- tables ----------
def held_rows(spec, held):
    rows = {}
    for h in held:
        label = cond_name(spec, h["recording"])
        col = h["column"].split("_")[0].capitalize() + " power"
        rows.setdefault(label, []).append(col)
    return rows


def exclusion_table(spec, manifest, excl, held):
    n = manifest["counts"]
    by_code = n["exclusions_by_reason_code"]
    csv_codes = {}
    for e in excl:
        csv_codes[e["reason_code"]] = csv_codes.get(e["reason_code"], 0) + 1
    assert csv_codes == by_code, "exclusions.csv and manifest disagree"
    short = sum(1 for e in excl if e["reason_code"] == "t04_2_outside_stride_rule" and "below" in e["reason"])
    long_ = sum(1 for e in excl if e["reason_code"] == "t04_2_outside_stride_rule" and "above" in e["reason"])
    held_text = "; ".join(f"{k}: {', '.join(sorted(v))}" for k, v in held_rows(spec, held).items())
    vars_ = {"short": short, "long": long_, "held_n": len(held), "held_text": held_text}
    # Every reason code in the bundle must have a row, so no exclusion goes unexplained.
    listed = {r["count"]["reason"] for r in spec["exclusion_rows"] if isinstance(r["count"], dict)}
    missing = set(by_code) - listed
    if missing:
        raise ValueError(f"exclusion reason codes with no row in the spec: {sorted(missing)}")
    rows = []
    for r in spec["exclusion_rows"]:
        c = r["count"]
        count = by_code[c["reason"]] if isinstance(c, dict) else vars_[c] if isinstance(c, str) else c
        rows.append((r["what"].format(**vars_), count, r["where"], r["why"].format(**vars_)))
    head = "<thead><tr><th>What</th><th>Count</th><th>Where it stands</th><th>Why</th></tr></thead>"
    body = "".join(
        f'<tr><td>{esc(a)}</td><td class="num">{b:,}</td><td>{esc(c)}</td><td>{esc(d)}</td></tr>' for a, b, c, d in rows)
    note = '<p class="note">' + esc(spec["accounting_note"].format(upstream=n["upstream_observations"], full=n["full"], filtered=n["filtered"])) + "</p>"
    return f'<div class="table-scroll" role="region" aria-label="What we left out" tabindex="0"><table class="plain-table">{head}<tbody>{body}</tbody></table></div>{note}'


def column_table(spec, r01, held):
    held_cols = {}
    for h in held:
        held_cols.setdefault(h["column"], []).append(cond_name(spec, h["recording"]))
    rows = []
    for c in r01["columns"]:
        name, unit = spec["plain"][c["column"]]["name"], spec["plain"][c["column"]]["unit"]
        label, note = spec["status_text"][c["status"]]["label"], spec["status_text"][c["status"]]["note"]
        if c["column"] in held_cols:
            label = "Not checked; empty in some recordings"
            note = "No check was run. Empty in: " + "; ".join(held_cols[c["column"]]) + " (sign not settled)."
        rows.append(f'<tr><td>{esc(name)}<br><code>{esc(c["column"])}</code></td><td>{esc(unit)}</td>'
                    f'<td><strong>{esc(label)}</strong><br>{esc(note)}</td></tr>')
    return ('<div class="table-scroll" role="region" aria-label="Columns" tabindex="0"><table class="plain-table">'
            '<thead><tr><th>Column</th><th>Unit</th><th>Status</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table></div>')


# ---------- fix cards ----------
def fig(src, side, label, alt, cap=""):
    c = f"<figcaption>{esc(cap)}</figcaption>" if cap else ""
    return (f'<figure class="fix-figure"><figcaption class="fix-side fix-{side}">{esc(label)}</figcaption>'
            f'<img src="../../quality/fixes/{src}" width="450" height="310" loading="lazy" alt="{esc(alt)}">{c}</figure>')


def local_fig(figs_dir: Path, src, label, alt, cap=""):
    svg = (figs_dir / src).read_text(encoding="utf-8")
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
    w, h = float(m.group(1)), float(m.group(2))
    c = f"<figcaption>{esc(cap)}</figcaption>" if cap else ""
    return (f'<figure class="fix-figure"><figcaption class="fix-side">{esc(label)}</figcaption>'
            f'<img src="figures/{src}" width="{round(w * 100 / 72)}" height="{round(h * 100 / 72)}" loading="lazy" alt="{esc(alt)}">{c}</figure>')


def scope_block(spec, figs_dir, fix):
    t = fix["table"]
    head = "".join(f"<th>{esc(c)}</th>" for c in t["columns"])
    body = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in row) + "</tr>" for row in t["rows"])
    table = (f'<div class="table-scroll" role="region" aria-label="{esc(fix["card"])}: affected recordings" tabindex="0">'
             f'<table class="plain-table scope-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')
    if t["fold"]:
        table = f'<details class="scope-fold"><summary>Show all {len(t["rows"])} rows</summary>{table}</details>'
    q = spec["scope_questions"][fix["key"]]
    g = local_fig(figs_dir, f"scope-{fix['key']}.svg", q, f"Grid of participants by task. {fix['grid_caption']}", fix["grid_caption"])
    return (f'<div class="scope-block"><h4>How much was affected</h4><p class="scope-total">{esc(fix["total_line"])}</p>'
            f'<p class="note">{esc(fix["denominator_text"])}</p>'
            f'<div class="fix-figures fix-figures-single">{g}</div>{table}</div>')


def knock_block(fix):
    items = []
    for k in fix["knock_on"]:
        ev = f'<span class="ko-evidence"><em>How we know:</em> {esc(k["evidence"])}</span>' if k["evidence"] else '<span class="ko-evidence"><em>No evidence yet.</em></span>'
        items.append(f'<li class="ko-item"><span class="verdict {VERDICT_CLASS[k["verdict"]]}">{esc(k["verdict"])}</span> '
                     f'<strong>{esc(k["signal"])}.</strong> {esc(k["line"])} {ev}</li>')
    d = f'<p class="ko-direction">{esc(fix["direction"])}</p>' if fix.get("direction") else ""
    return f'<div class="scope-block"><h4>What else this could affect</h4>{d}<ul class="ko-list">{"".join(items)}</ul></div>'


def card_figures(c, figs_dir, figinfo):
    q, parts = "", []
    for f in c["figures"]:
        if "question" in f:
            q = f'<p class="fig-question">{esc(f["question"])}</p>'
            continue
        cap = f.get("caption", "").format(fi=figinfo)
        if f["kind"] == "published":
            parts.append(fig(f["src"], f["side"], f["label"], f["alt"], cap))
        else:
            parts.append(local_fig(figs_dir, f["src"], f["label"], f["alt"], cap))
    figures = "".join(parts)
    return q + (f'<div class="fix-figures{" fix-figures-single" if c["single"] else ""}">{figures}</div>' if figures else "")


def fix_cards(spec, scope, figs_dir, figinfo):
    S = {f["key"]: f for f in scope["fixes"]}
    out = []
    for c in spec["cards"]:
        fx = S[c["scope_key"]]
        out.append(f'<article class="fix-card"><h3>{esc(c["title"])}</h3>'
                   f'<p><strong>What was wrong.</strong> {esc(c["wrong"])}</p><p><strong>How we know.</strong> {esc(c["how"])}</p>'
                   f'<p><strong>What we did.</strong> {esc(c["did"])}</p>{card_figures(c, figs_dir, figinfo)}'
                   f'<p class="fix-evidence"><strong>Example.</strong> {esc(c["example"])}</p>'
                   f'{scope_block(spec, figs_dir, fx)}{knock_block(fx)}</article>')
    return "".join(out)




CSS_TEMPLATE = """
.review-page section { padding-top: .3rem; }
.review-page h2 { margin-top: 2rem; }
.review-page .lead { max-width: 72ch; }
.review-page .plain-table { width: 100%; border-collapse: collapse; font-size: .88rem; }
.review-page .plain-table th, .review-page .plain-table td { text-align: left; vertical-align: top; padding: .45rem .6rem; border-bottom: 1px solid var(--line); }
.review-page .plain-table td.num { text-align: right; white-space: nowrap; }
.review-page .plain-table code { font-size: .74rem; color: var(--muted); word-break: break-all; }
.review-page .table-scroll { overflow-x: auto; }
.review-page .plain-table { min-width: 34rem; }
.review-page .note { color: var(--muted); font-size: .82rem; max-width: 72ch; }
.review-page .checks { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr)); gap: 1rem 1.5rem; }
.review-page .checks ul { margin: .3rem 0; padding-left: 1.2rem; }
.review-page .checks h3 { margin: .2rem 0; font-size: 1rem; }
.review-page .phase-signal { border-top: 1px solid var(--line); padding: .5rem 0; }
.review-page .phase-signal summary { cursor: pointer; font-size: .95rem; padding: .25rem 0; }
.review-page .phase-unit { color: var(--muted); font-size: .82rem; font-weight: 400; margin-left: .5rem; }
.review-page .phase-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 17rem), 1fr)); gap: .8rem 1.2rem; margin: .6rem 0; }
.review-page .phase-panel { margin: 0; min-width: 0; }
.review-page .phase-panel svg { display: block; width: 100%; height: auto; background: var(--page); color: var(--ink); }
.review-page .phase-legend { display: flex; flex-wrap: wrap; gap: .3rem 1rem; font-size: .8rem; color: var(--muted); margin: .2rem 0 .6rem; }
.review-page .phase-legend i { display: inline-block; width: .8rem; height: .25rem; margin-right: .35rem; vertical-align: middle; }
.review-page .fix-card h3 { margin: 0 0 .35rem; font-size: 1.1rem; }
.review-page .scope-block { border-top: 1px solid var(--line); margin-top: .9rem; padding-top: .4rem; }
.review-page .scope-block h4 { margin: .2rem 0 .4rem; font-size: 1rem; }
.review-page .scope-total { max-width: 72ch; font-weight: 600; margin: .2rem 0; }
.review-page .scope-table { min-width: 31rem; }
.review-page .scope-fold > summary { cursor: pointer; font-size: .9rem; padding: .3rem 0; }
.review-page .fig-question { font-weight: 600; margin: .8rem 0 .2rem; max-width: 72ch; }
.review-page .ko-list { list-style: none; margin: .3rem 0; padding: 0; max-width: 80ch; }
.review-page .ko-item { padding: .5rem 0; border-bottom: 1px solid var(--line); font-size: .92rem; }
.review-page .ko-evidence { display: block; color: var(--muted); font-size: .85rem; margin-top: .15rem; }
.review-page .ko-direction { max-width: 72ch; font-size: .92rem; background: var(--soft, transparent); }
.review-page .verdict { display: inline-block; font-size: .78rem; font-weight: 600; padding: .05rem .45rem; border-radius: 3px; border: 1px solid currentColor; margin-right: .3rem; white-space: nowrap; }
.review-page .v-ok { color: #1f6aa5; } .review-page .v-fixed { color: #1b7a43; } .review-page .v-left { color: #8a5a00; } .review-page .v-nc { color: #a3361a; }
@media (prefers-color-scheme: dark) { .review-page .v-ok { color: #6db3e8; } .review-page .v-fixed { color: #5cc98a; } .review-page .v-left { color: #e0a93b; } .review-page .v-nc { color: #f08a6e; } }
@media (max-width: 40rem) { .review-page .scope-table th, .review-page .scope-table td { padding: .35rem .4rem; font-size: .8rem; } }
.review-page .local-box { border: 1px solid var(--warn-line); background: var(--warn); padding: .8rem 1rem; max-width: 72ch; border-radius: 3px; }
"""

def build(spec: dict, root: Path = ROOT, backlog_path: Path = BACKLOG, allow_review: bool = False) -> str:
    check_gate(spec, backlog_path, allow_review)
    manifest, index, excl, held, preview, r01, scope = load_inputs(spec, root)
    figs_dir = root / "docs/datasets" / spec["slug"] / "figures"
    figinfo = json.loads((figs_dir / FIGJSON_NAME).read_text(encoding="utf-8"))
    n = manifest["counts"]
    recordings = len(index["recordings"])
    subjects = len({r["subject"] for r in index["recordings"]})
    columns = [c["column"] for c in r01["columns"]]
    name, cls = spec["display_name"], spec["css_class"]
    css = CSS_TEMPLATE.replace(".review-page", "." + cls)
    lead = spec["lead"].format(subjects=subjects, recordings=recordings, full=n["full"], filtered=n["filtered"])
    ck = spec["checked"]
    li = lambda items: "".join(f"\n        <li>{esc(i)}</li>" for i in items)
    status_block = dataset_status.page_block(spec["slug"], json.loads(Path(backlog_path).read_text(encoding="utf-8")))
    h1_id = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{esc(spec['meta_description'])}">
  <meta name="color-scheme" content="light dark">
  <title>{esc(spec['title'])}</title>
  <link rel="stylesheet" href="../../stylesheets/site.css">
  <link rel="stylesheet" href="../../stylesheets/dataset-pages.css">
  <link rel="stylesheet" href="../../stylesheets/visual-styles.css">
  <link rel="stylesheet" href="../../stylesheets/fixes.css">
  <script src="../../javascripts/visual-styles.js"></script>
  <script src="../../javascripts/extra.js" defer></script>
  <style>{css}</style>
</head>
<body class="dataset-detail">
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header">
    <div class="header-inner">
      <a class="wordmark" href="../../index.html" aria-label="LocoHub home">LocoHub</a>
      <nav class="primary-nav" aria-label="Main navigation"><a href="../../index.html" aria-current="page">Data</a>
<a href="../../tutorials/index.html">Tutorials</a>
<a href="../../reference/index.html">File format</a>
<a href="../../quality/index.html">Testing &amp; data quality</a></nav>
      <form class="header-search" role="search" aria-label="Site search" action="../../search/index.html"><label class="visually-hidden" for="header-query">Search documentation</label><input id="header-query" type="search" name="q" placeholder="Search docs" required><button type="submit">Search</button></form>
      <a class="repository-link" href="https://github.com/jmontp/LocoHub">GitHub</a>
    </div>
  </header>
  <div class="page-layout wide-page">
    <main id="main" class="page-content {cls}" tabindex="-1">
      <div class="page-kicker"><a href="../../index.html">LocoHub</a><span aria-hidden="true">/</span>{esc(name)}</div>
      <header class="dataset-heading"><h1 id="{h1_id}">{esc(name)}</h1>{status_block}
<p class="dataset-note">{esc(spec['heading_note'])}</p></header>
      <nav class="dataset-section-nav" aria-label="Sections"><a href="#what-this-is">What this is</a><a href="#fixed">What we fixed</a><a href="#left-out">What we left out</a><a href="#checked">What we checked</a><a href="#phase-plots">Phase plots</a><a href="#columns">Columns</a><a href="#downloads">Downloads</a></nav>

      <section id="what-this-is" aria-labelledby="what-h"><h2 id="what-h">What this is</h2>
      <p class="lead">{lead}</p></section>

      <section id="fixed" aria-labelledby="fixed-h"><h2 id="fixed-h">What we fixed (original vs fixed)</h2>
      <p class="note">{esc(spec['fixed_note'])}</p>
      {fix_cards(spec, scope, figs_dir, figinfo)}</section>

      <section id="left-out" aria-labelledby="left-h"><h2 id="left-h">What we left out and why</h2>
      {exclusion_table(spec, manifest, excl, held)}</section>

      <section id="checked" aria-labelledby="checked-h"><h2 id="checked-h">What we checked and what we did not</h2>
      <div class="checks"><div><h3>Checked</h3><ul>{li(ck['checked'])}</ul></div>
      <div><h3>Not checked</h3><ul>{li(ck['not_checked'])}</ul></div></div>
      <p class="note">{esc(ck['note'])}</p></section>

      <section id="phase-plots" aria-labelledby="phase-h"><h2 id="phase-h">Phase plots</h2>
      <p class="note">{esc(spec['phase_note'])}</p>
      {phase_section(spec, preview, columns)}</section>

      <section id="columns" aria-labelledby="columns-h"><h2 id="columns-h">Columns</h2>
      {column_table(spec, r01, held)}
      <p class="note">{spec['columns_note']}</p></section>

      <section id="downloads" aria-labelledby="downloads-h"><h2 id="downloads-h">Downloads</h2>
      <div class="local-box"><p>{spec['downloads_text']}</p></div>
      <p class="note">Page built from the local review version checked on {esc(spec['verified_date'])}.</p></section>
    </main>
  </div>
  <footer class="site-footer"><p>LocoHub</p><nav aria-label="Additional links"><a href="../../contributing/index.html">Contribute data</a><a href="../../maintainers/index.html">Maintainers</a><a href="../../reference/index.html#release-evidence">Download notes</a><a href="https://github.com/jmontp/LocoHub/issues">Report an issue</a></nav></footer>
</body>
</html>
"""
    return page


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", type=Path, help="page spec JSON, for example contributor_tools/page_specs/um21.json")
    ap.add_argument("--allow-review", action="store_true", help="accept an R01 task in review (UMich 2021 only)")
    ap.add_argument("--out", type=Path, default=None, help="output file (default docs/datasets/<slug>/index.html)")
    args = ap.parse_args(argv)
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    try:
        page = build(spec, allow_review=args.allow_review)
    except BundleNotReady as error:
        print(f"refused: {error}", file=sys.stderr)
        return 1
    out = args.out or ROOT / "docs/datasets" / spec["slug"] / "index.html"
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
