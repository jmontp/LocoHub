#!/usr/bin/env python3
"""Build docs/datasets/gt21/problems.html: the known problems of Georgia Tech 2021, in plain words.

Reads only docs/quality/audits/gt21-problem-scope.json and the figures in docs/datasets/gt21/figures/.
Every number on the page comes from that JSON file. Nothing here is a scientific approval.
Copy the page and its figures to site/html/datasets/gt21/ with --site.

Usage: python3 contributor_tools/build_gt21_problems_page.py [--site]
"""
from __future__ import annotations

import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPE = ROOT / "docs/quality/audits/gt21-problem-scope.json"
OUT = ROOT / "docs/datasets/gt21/problems.html"
FIGS = ROOT / "docs/datasets/gt21/figures"
SITE = ROOT / "site/html/datasets/gt21"
VERDICT_CLASS = {"Also wrong, fixed in a pilot": "v-fixed", "Also wrong, not yet fixed": "v-wrong", "Checked, not affected": "v-ok", "Left out": "v-left", "Not checked": "v-nc"}
STATUS_CLASS = {"fixed_pilot": "s-fixed", "decided": "s-decided", "open": "s-open", "documented": "s-doc"}


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def img_fig(src, label, alt, cap=""):
    svg = (FIGS / src).read_text(encoding="utf-8")
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
    w, h = float(m.group(1)), float(m.group(2))
    c = f"<figcaption>{esc(cap)}</figcaption>" if cap else ""
    return (f'<figure class="fix-figure"><figcaption class="fix-side">{esc(label)}</figcaption>'
            f'<img src="figures/{src}" width="{round(w * 100 / 72)}" height="{round(h * 100 / 72)}" loading="lazy" alt="{esc(alt)}">{c}</figure>')


def status_block(p):
    s = p["status"]
    detail = f' <span class="st-detail">{esc(s["detail"])}</span>' if s["detail"] else ""
    needs = f' <span class="st-needs"><strong>Needs:</strong> {esc(s["needs"].replace("Needs ", "", 1))}</span>' if s["needs"] else ""
    return f'<p class="status-line"><span class="status {STATUS_CLASS[s["key"]]}">{esc(s["label"])}</span>{detail}{needs}</p>'


def scope_block(p):
    t = p["table"]
    head = "".join(f"<th>{esc(c)}</th>" for c in t["columns"])
    body = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in row) + "</tr>" for row in p["table"]["rows"])
    table = (f'<div class="table-scroll" role="region" aria-label="{esc(p["card"])}: numbers" tabindex="0">'
             f'<table class="plain-table scope-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')
    g = img_fig(f"scope-{p['key']}.svg", p["figure_question"], f"Grid of participants by task. {p['grid_caption']}", p["grid_caption"])
    return (f'<div class="scope-block"><h4>How much was affected</h4><p class="scope-total">{esc(p["total_line"])}</p>'
            f'<p class="note">{esc(p["denominator_text"])}</p><div class="fix-figures fix-figures-single">{g}</div>{table}</div>')


def knock_block(p):
    items = []
    for k in p["knock_on"]:
        ev = (f'<span class="ko-evidence"><em>How we know:</em> {esc(k["evidence"])}</span>' if k["evidence"]
              else '<span class="ko-evidence"><em>No evidence yet.</em></span>')
        items.append(f'<li class="ko-item"><span class="verdict {VERDICT_CLASS[k["verdict"]]}">{esc(k["verdict"])}</span> '
                     f'<strong>{esc(k["signal"])}.</strong> {esc(k["line"])} {ev}</li>')
    return (f'<div class="scope-block"><h4>What else this could affect</h4><p class="ko-direction">{esc(p["direction"])}</p>'
            f'<ul class="ko-list">{"".join(items)}</ul></div>')


def card(p, number):
    figs = "".join(img_fig(f["file"], f["question"], f["alt"], f["cap"]) for f in p["extra_figures"])
    single = " fix-figures-single" if len(p["extra_figures"]) == 1 else ""
    fig_html = f'<div class="fix-figures{single}">{figs}</div>' if figs else ""
    return (f'<article class="fix-card" id="{esc(p["key"])}"><h3>{number}. {esc(p["card"])}</h3>{status_block(p)}'
            f'<p><strong>What is wrong.</strong> {esc(p["wrong"])}</p><p><strong>How we know.</strong> {esc(p["how"])}</p>'
            f'{fig_html}<p class="fix-evidence"><strong>Example.</strong> {esc(p["example"])}</p>{scope_block(p)}{knock_block(p)}</article>')


def glance(scope):
    rows = []
    for i, p in enumerate(scope["problems"], 1):
        s = p["status"]
        rows.append(f'<tr><td>{i}</td><td><a href="#{esc(p["key"])}">{esc(p["card"])}</a></td>'
                    f'<td><span class="status {STATUS_CLASS[s["key"]]}">{esc(s["label"])}</span></td><td>{esc(p["total_line"].split(". ")[0].rstrip("."))}.</td></tr>')
    return ('<div class="table-scroll" role="region" aria-label="All problems at a glance" tabindex="0"><table class="plain-table glance-table">'
            '<thead><tr><th>#</th><th>Problem</th><th>Where it stands</th><th>How much</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table></div>')


def not_checked(scope):
    out = []
    for i, p in enumerate(scope["problems"], 1):
        items = [k for k in p["knock_on"] if k["verdict"] == "Not checked"]
        if items:
            out.append(f'<li><strong>{i}. {esc(p["card"])}</strong><ul>' + "".join(f'<li>{esc(k["signal"])}</li>' for k in items) + '</ul></li>')
    return '<ul class="nc-list">' + "".join(out) + '</ul>'


CSS = """
.gt21 section { padding-top: .3rem; }
.gt21 h2 { margin-top: 2rem; }
.gt21 .lead { max-width: 72ch; }
.gt21 .plain-table { width: 100%; border-collapse: collapse; font-size: .88rem; }
.gt21 .plain-table th, .gt21 .plain-table td { text-align: left; vertical-align: top; padding: .45rem .6rem; border-bottom: 1px solid var(--line); }
.gt21 .table-scroll { overflow-x: auto; }
.gt21 .plain-table { min-width: 34rem; }
.gt21 .glance-table { min-width: 44rem; }
.gt21 .note { color: var(--muted); font-size: .82rem; max-width: 72ch; }
.gt21 .fix-card h3 { margin: 0 0 .35rem; font-size: 1.1rem; }
.gt21 .status-line { max-width: 76ch; margin: .2rem 0 .5rem; }
.gt21 .status { display: inline-block; font-size: .8rem; font-weight: 600; padding: .05rem .5rem; border-radius: 3px; border: 1px solid currentColor; white-space: nowrap; margin-right: .4rem; }
.gt21 .s-fixed { color: #1b7a43; } .gt21 .s-decided { color: #1f6aa5; } .gt21 .s-open { color: #a3361a; } .gt21 .s-doc { color: #5b6672; }
.gt21 .st-detail, .gt21 .st-needs { font-size: .9rem; }
.gt21 .st-needs { display: block; margin-top: .2rem; }
.gt21 .scope-block { border-top: 1px solid var(--line); margin-top: .9rem; padding-top: .4rem; }
.gt21 .scope-block h4 { margin: .2rem 0 .4rem; font-size: 1rem; }
.gt21 .scope-total { max-width: 72ch; font-weight: 600; margin: .2rem 0; }
.gt21 .scope-table { min-width: 31rem; }
.gt21 .ko-list { list-style: none; margin: .3rem 0; padding: 0; max-width: 80ch; }
.gt21 .ko-item { padding: .5rem 0; border-bottom: 1px solid var(--line); font-size: .92rem; }
.gt21 .ko-evidence { display: block; color: var(--muted); font-size: .85rem; margin-top: .15rem; }
.gt21 .ko-direction { max-width: 72ch; font-size: .92rem; }
.gt21 .verdict { display: inline-block; font-size: .78rem; font-weight: 600; padding: .05rem .45rem; border-radius: 3px; border: 1px solid currentColor; margin-right: .3rem; white-space: nowrap; }
.gt21 .v-ok { color: #1f6aa5; } .gt21 .v-fixed { color: #1b7a43; } .gt21 .v-left { color: #8a5a00; } .gt21 .v-nc { color: #a3361a; } .gt21 .v-wrong { color: #8c2f8c; }
@media (prefers-color-scheme: dark) { .gt21 .v-ok, .gt21 .s-decided { color: #6db3e8; } .gt21 .v-fixed, .gt21 .s-fixed { color: #5cc98a; } .gt21 .v-left { color: #e0a93b; } .gt21 .v-nc, .gt21 .s-open { color: #f08a6e; } .gt21 .v-wrong { color: #d79ad7; } .gt21 .s-doc { color: #a9b4bf; } }
@media (max-width: 40rem) { .gt21 .plain-table th, .gt21 .plain-table td { padding: .35rem .4rem; font-size: .8rem; } .gt21 .fix-card p { max-width: 100%; } }
.gt21 .nc-list { max-width: 80ch; font-size: .92rem; }
.gt21 .nc-list ul { margin: .1rem 0 .5rem; }
.gt21 .local-box { border: 1px solid var(--warn-line); background: var(--warn); padding: .8rem 1rem; max-width: 72ch; border-radius: 3px; }
"""


def build() -> str:
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    d = scope["denominators"]
    cards = "".join(card(p, i) for i, p in enumerate(scope["problems"], 1))
    fine = "".join(f"<li>{esc(x)}</li>" for x in scope["checked_fine"])
    limits = "".join(f"<li>{esc(x)}</li>" for x in scope["other_limits"])
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Georgia Tech 2021 walking data: the problems we know about, how much each affects, and what else each could affect.">
  <meta name="color-scheme" content="light dark">
  <title>Georgia Tech 2021, known problems · LocoHub</title>
  <link rel="stylesheet" href="../../stylesheets/site.css">
  <link rel="stylesheet" href="../../stylesheets/dataset-pages.css">
  <link rel="stylesheet" href="../../stylesheets/visual-styles.css">
  <link rel="stylesheet" href="../../stylesheets/fixes.css">
  <script src="../../javascripts/visual-styles.js"></script>
  <script src="../../javascripts/extra.js" defer></script>
  <style>{CSS}</style>
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
    <main id="main" class="page-content gt21" tabindex="-1">
      <div class="page-kicker"><a href="../../index.html">LocoHub</a><span aria-hidden="true">/</span><a href="index.html">Georgia Tech 2021</a><span aria-hidden="true">/</span>Known problems</div>
      <header class="dataset-heading"><h1 id="gt21-problems">Georgia Tech 2021: known problems</h1>
<p class="dataset-note">Not released. The local rebuild stopped at {d['rebuilt_recordings']} of {d['local_recordings']:,} recordings. Nothing on this page has been approved scientifically.</p></header>
      <nav class="dataset-section-nav" aria-label="Sections"><a href="#what-this-is">What this is</a><a href="#glance">At a glance</a><a href="#problems">The problems</a><a href="#fine">Checked and fine</a><a href="#limits">Other limits</a><a href="#not-checked">Not checked</a></nav>

      <section id="what-this-is" aria-labelledby="what-h"><h2 id="what-h">What this is</h2>
      <p class="lead">Walking on level ground, ramps, stairs and a treadmill from the Georgia Tech 2021 study: {d['publisher_participants']} participants in the original study, of which {d['local_participants']} are here ({d['local_recordings']:,} recordings) and {d['missing_participants']} are not converted yet ({d['acquired_recordings_of_six']} recordings downloaded). This page lists every problem we know about. It is not a list of fixes: only {d['rebuilt_recordings']} recordings ({d['rebuilt_steps']:,} steps, all from AB06) have been rebuilt, so each card says where its problem stands.</p>
      <p class="note">{esc(d['note'])}</p>
      <p class="note">Each card says what is wrong, how we know, how much it affects, and what else it could affect. Four statuses are used: <strong>fixed in a checked pilot</strong> (a pilot is a small trial run on a few recordings; the full rebuild does not use it yet), <strong>decided by José, fix not yet run</strong>, <strong>open</strong>, and <strong>documented only, kept as published</strong>. A figure may show a sample; its caption says how it was drawn and the seed is recorded. Anything that needs more than a small read is marked not checked and needs a guarded job, which is a supervised run with memory limits.</p></section>

      <section id="glance" aria-labelledby="glance-h"><h2 id="glance-h">All problems at a glance</h2>
      {glance(scope)}</section>

      <section id="problems" aria-labelledby="problems-h"><h2 id="problems-h">The problems</h2>
      {cards}</section>

      <section id="fine" aria-labelledby="fine-h"><h2 id="fine-h">What we checked and found no problem</h2>
      <ul class="nc-list">{fine}</ul>
      <p class="note">A check that passed is not approval. It says only that this one thing was not found wrong.</p></section>

      <section id="limits" aria-labelledby="limits-h"><h2 id="limits-h">Other limits we know about</h2>
      <ul class="nc-list">{limits}</ul></section>

      <section id="not-checked" aria-labelledby="nc-h"><h2 id="nc-h">Everything marked not checked</h2>
      <p class="note">Each item below needs a guarded job, a new decision or source evidence before it can be checked.</p>
      {not_checked(scope)}
      <div class="local-box"><p><strong>Local review page, not published.</strong> The rebuilt files and the checks behind this page exist only on the maintainer's computer.</p></div></section>
    </main>
  </div>
  <footer class="site-footer"><p>LocoHub</p><nav aria-label="Additional links"><a href="../../contributing/index.html">Contribute data</a><a href="../../maintainers/index.html">Maintainers</a><a href="../../reference/index.html#release-evidence">Download notes</a><a href="https://github.com/jmontp/LocoHub/issues">Report an issue</a></nav></footer>
</body>
</html>
"""
    return page


def main() -> None:
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    if "--site" in sys.argv:
        (SITE / "figures").mkdir(parents=True, exist_ok=True)
        shutil.copy2(OUT, SITE / "problems.html")
        for f in FIGS.glob("*.svg"):
            shutil.copy2(f, SITE / "figures" / f.name)
        print("copied to", SITE.relative_to(ROOT))


if __name__ == "__main__":
    main()
