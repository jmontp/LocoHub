#!/usr/bin/env python3
"""One plain status label per dataset, taken from docs/maintainers/backlog.json.

The rule (first match wins) uses only backlog facts, never a hand-typed status:
  1. The dataset's R01 task (the local review release) is `review` or `done`
     -> "local review version (not released)".
  2. Any task of the dataset is `working` or `review`, or its backlog entry has
     `rebuild_in_progress: true` (set when José puts a rebuild in scope)
     -> "being rebuilt".
  3. The dataset's pilot or source-readback gate is `partial`
     -> "partly rebuilt locally (not released)".
  4. Otherwise -> "legacy, not yet checked".
If rule 1 matches and a task is also `working`, the page adds a sentence that an
update is being rebuilt. Nothing here is scientific approval.

`python3 contributor_tools/dataset_status.py` writes the status into the catalog
(docs/index.html), the status cards (docs/quality/index.html) and every dataset
page (between STATUS_START / STATUS_END markers). `--check` changes nothing and
exits 1 if any file is out of date. Only docs/ files are read or written.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
BACKLOG = DOCS / "maintainers/backlog.json"
HISTORICAL = ("ca23", "fa16", "fr12", "ha13", "ha23", "mo15", "ta21", "ta22", "ti19", "vz22", "wa23")
LABELS = {
    "review": "local review version (not released)",
    "rebuilding": "being rebuilt",
    "partial": "partly rebuilt locally (not released)",
    "legacy": "legacy, not yet checked",
}
EXPLAIN = {
    "review": "A local review version exists on the maintainer's computer. It is not released and has not been approved scientifically.",
    "rebuilding": "The data is being rebuilt from the original files. Downloads and plots on this page, where present, come from the earlier conversion, which has not been checked.",
    "partial": "Part of the study was rebuilt locally and read back against the original files. Nothing is released. Downloads and plots on this page, where present, come from the earlier conversion, which has not been checked.",
    "legacy": "Downloads and plots on this page, where present, come from an earlier conversion that has not been checked against the original files.",
}
UPDATE_SENTENCE = (" It was built before the 23 November 2026 standard (joint angles as differences of gravity-referenced segment angles, "
                   "centre of pressure in the foot frame); an update to that standard is being rebuilt.")
SIGN_SENTENCE = ' Signs and zero references in files not yet rebuilt may differ from the <a href="{prefix}reference/index.html#signs-and-frames">current standard</a>.'


def load_backlog(path: Path = BACKLOG) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def shown_slugs() -> list[str]:
    """Datasets the site shows (docs/site_datasets.json); hidden dataset pages are left untouched."""
    return list(json.loads((DOCS / "site_datasets.json").read_text(encoding="utf-8"))["shown"])


def backlog_id(slug: str) -> str:
    return "historical" if slug in HISTORICAL else slug


def status_for(data: dict, slug: str) -> tuple[str, bool]:
    """Return (status key, an_update_is_being_rebuilt) for a dataset slug."""
    ds = backlog_id(slug)
    tasks = [t for t in data["tasks"] if t["dataset"] == ds]
    entry = next((d for d in data["datasets"] if d["id"] == ds), None)
    # A rebuild José put in scope stays "being rebuilt" between steps, when no task is momentarily working.
    working = any(t["status"] in ("working", "review") for t in tasks) or bool(entry and entry.get("rebuild_in_progress"))
    if any(t["id"].endswith("-R01") and t["status"] in ("review", "done") for t in tasks):
        return "review", working
    if working:
        return "rebuilding", False
    gates = entry["gate_status"] if entry else {}
    if "partial" in (gates.get("pilot"), gates.get("readback")):
        return "partial", False
    return "legacy", False


def label_text(key: str) -> str:
    return LABELS[key][0].upper() + LABELS[key][1:]


def problems_page(slug: str) -> Path | None:
    path = DOCS / "datasets" / slug / "problems.html"
    return path if path.is_file() else None


def page_block(slug: str, data: dict | None = None) -> str:
    """Status line for a dataset page; the same text the builders embed."""
    data = data or load_backlog()
    key, update = status_for(data, slug)
    text = EXPLAIN[key] + (UPDATE_SENTENCE if update else "")
    link = ' <a href="problems.html">Known problems</a>.' if problems_page(slug) else ""
    return (f'<!-- STATUS_START --><p class="dataset-status" data-status="{key}"><strong>Status: {escape(LABELS[key])}.</strong> '
            f'{escape(text)}{SIGN_SENTENCE.format(prefix="../../")}{link}</p><!-- STATUS_END -->')


BLOCK_RE = re.compile(r"<!-- STATUS_START -->.*?<!-- STATUS_END -->", re.S)


def apply_page(slug: str, html: str, data: dict) -> str:
    """Put the status line right after the page title, replacing an earlier copy."""
    block = page_block(slug, data)
    html = BLOCK_RE.sub("", html)
    head, sep, tail = html.partition("<main")
    if not sep or "</h1>" not in tail:
        raise ValueError(f"{slug}: no dataset heading to attach the status to")
    return head + sep + tail.replace("</h1>", "</h1>" + block, 1)


CATALOG_RE = re.compile(r'<a class="evidence-status"[^>]*? href="((?:\.\./)?)quality/index\.html#status-(\w+)">[^<]*</a>(?:<a class="problems-link"[^>]*>[^<]*</a>)?')
CARD_RE = re.compile(r'(<article class="status-card" id="status-(\w+)"><h3>[^<]*?) <span class="status-label" data-status="\w+">[^<]*</span>')


FUTURE_LINE = {
    "legacy": "not yet checked",
    "rebuilding": "being rebuilt",
    "partial": "partly rebuilt on the maintainer's computer; not released",
    "review": "local review version; not released",
}
FUTURE_RE = re.compile(r"<!-- FUTURE_START -->.*?<!-- FUTURE_END -->", re.S)


def future_block(data: dict) -> str:
    """Closed "Coming later" list: plain text only, because these datasets have no built page."""
    listing = json.loads((DOCS / "site_datasets.json").read_text(encoding="utf-8"))
    later, group = listing.get("later", []), listing.get("later_group")
    items = "".join(f"<li><strong>{escape(d['name'])}</strong>: {escape(FUTURE_LINE[status_for(data, d['slug'])[0]])}.</li>" for d in later)
    total = len(later)
    if group:  # one line for the earlier studies; their status is the backlog's status for the first slug of the group
        status = FUTURE_LINE[status_for(data, group["slugs"][0])[0]]
        items += f"<li><strong>{escape(group['label'])} ({len(group['names'])})</strong>: {escape(status)}. {escape(', '.join(group['names']))}.</li>"
        total += len(group["names"])
    return (f'<!-- FUTURE_START --><details class="future-datasets"><summary>Coming later ({total} datasets)</summary>'
            '<p class="note">These datasets are not on this site yet. Their pages are not published.</p>'
            f"<ul>{items}</ul></details><!-- FUTURE_END -->")


def apply_catalog(html: str, data: dict) -> str:
    def repl(m):
        up, slug = m.group(1), m.group(2)
        key, _ = status_for(data, slug)
        out = f'<a class="evidence-status" data-status="{key}" href="{up}quality/index.html#status-{slug}">{escape(label_text(key))}</a>'
        if problems_page(slug):
            href = f"{slug}/problems.html" if up else f"datasets/{slug}/problems.html"
            out += f'<a class="problems-link" href="{href}">Known problems</a>'
        return out
    html = CATALOG_RE.sub(repl, html)
    return FUTURE_RE.sub(lambda m: future_block(data), html)


def apply_cards(html: str, data: dict) -> str:
    def repl(m):
        key, _ = status_for(data, m.group(2))
        return f'{m.group(1)} <span class="status-label" data-status="{key}">{escape(label_text(key))}</span>'
    return CARD_RE.sub(repl, html)


def targets(data: dict):
    yield DOCS / "index.html", lambda h: apply_catalog(h, data)
    yield DOCS / "datasets/index.html", lambda h: apply_catalog(h, data)
    yield DOCS / "quality/index.html", lambda h: apply_cards(h, data)
    slugs = shown_slugs()
    for slug in slugs:
        page = DOCS / "datasets" / slug / "index.html"
        if page.is_file():
            yield page, (lambda h, s=slug: apply_page(s, h, data))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="Report files that are out of date; write nothing.")
    args = ap.parse_args(argv)
    data = load_backlog()
    stale = []
    for path, fn in targets(data):
        old = path.read_text(encoding="utf-8")
        new = fn(old)
        if new != old:
            stale.append(path.relative_to(ROOT).as_posix())
            if not args.check:
                path.write_text(new, encoding="utf-8")
    for slug in shown_slugs():
        print(f"{slug}: {LABELS[status_for(data, slug)[0]]}")
    print(("out of date: " if args.check else "updated: ") + (", ".join(stale) or "none"))
    return 1 if (args.check and stale) else 0


if __name__ == "__main__":
    sys.exit(main())
