"""Georgia Tech 2023 dataset page: counts equal the local package, every card and limitation shows, nothing internal is visible.

Reads the committed page and the package's small files (manifest, limitations, dataset index, exclusion list). It never opens a
table file.
"""
from __future__ import annotations

import csv
import html
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "converted_datasets/reconversion_v2/gt23_r01_review_v11"
PAGE = ROOT / "docs/datasets/gt23/index.html"
SCOPE = ROOT / "docs/quality/audits/gt23-problem-scope.json"
SPEC = ROOT / "contributor_tools/page_specs/gt23.json"
pytestmark = pytest.mark.skipif(not (BUNDLE / "manifest.json").exists(), reason="local package absent")


def raw():
    return PAGE.read_text(encoding="utf-8")


def visible_text():
    t = re.sub(r"<(script|style|svg)\b.*?</\1>", " ", raw(), flags=re.S)
    attrs = " ".join(re.findall(r'(?:alt|aria-label)="([^"]*)"', t))
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t) + " " + attrs))


def counts():
    return json.loads((BUNDLE / "manifest.json").read_text())["counts"]


def test_counts_equal_the_package():
    c = counts()
    text = visible_text()
    assert (c["observations_full"], c["observations_filtered"], c["failed_observations"]) == (19573, 19448, 125)
    assert f"{c['observations_full']:,} observations" in text and f"{c['observations_filtered']:,}" in text
    full = c["full"]["observations_by_type"]
    assert (full["individual_cycle"], full["transfer"], full["continuous_recording"]) == (8831, 10254, 488)
    for n in (full["individual_cycle"], full["transfer"], full["transfer"] // 2):
        assert f"{n:,}" in text
    idx = json.loads((BUNDLE / "dataset_index.json").read_text())["recordings"]
    assert f"{len({r['subject'] for r in idx})} participants" in text and f"{len(idx)} recordings" in text


def test_every_exclusion_count_is_listed_and_adds_up():
    c = counts()
    rows = list(csv.DictReader((BUNDLE / "exclusions.csv").open()))
    assert len(rows) == c["exclusions_total"] == 5281
    by = {}
    for r in rows:
        by[(r["kind"], r["reason_code"])] = by.get((r["kind"], r["reason_code"]), 0) + 1
    text = visible_text()
    spec = json.loads(SPEC.read_text())
    listed = 0
    for row in spec["exclusion_rows"]:
        n = c
        for k in row["count"]:
            n = n[k]
        listed += n
        assert re.search(re.escape(html.unescape(row["what"])) + r" " + f"{n:,}" + r" ", text), row["what"]
    assert listed == len(rows)
    for kind, reasons in c["exclusions_by_reason"].items():
        if kind == "assessment_failed":
            continue
        for reason, n in reasons.items():
            assert by[(kind, reason)] == n


def test_every_limitation_and_its_counts_show():
    lim = json.loads((BUNDLE / "limitations.json").read_text())["limitations"]
    assert len(lim) == 13
    spec = json.loads(SPEC.read_text())
    text = visible_text()
    for x in lim:
        plain = html.unescape(spec["limit_plain"][x["id"]])
        assert plain in text, x["id"]
        obs = x.get("observations", x.get("observations_in_recording"))
        tail = text.split(plain, 1)[1][:80]
        assert re.match(rf"\s*{obs:,}\b", tail), (x["id"], obs, tail)
    assert "not checked" in text.lower() and "joint speeds" in text


def test_every_problem_card_has_a_status_and_the_source_counts():
    scope = json.loads(SCOPE.read_text())
    spec = json.loads(SPEC.read_text())
    arts = {m.group(1): m.group(0) for m in re.finditer(r'<article class="fix-card" id="(\w+)">.*?</article>', raw(), re.S)}
    assert set(arts) == {c["key"] for c in scope["cards"]} and len(arts) == 19
    fixed = 0
    for c in scope["cards"]:
        art = arts[c["key"]]
        u = spec["card_updates"][c["key"]]
        assert u["status"] in spec["status_words"]
        assert html.escape(spec["status_words"][u["status"]], quote=True) in art
        assert f"figures/scope-{c['key']}.svg" in art and "<img " in art
        assert html.escape(c["total_line"], quote=True) in art
        assert "What we did" in art and "What else this could affect" in art
        fixed += u["status"] == "fixed"
        for src in re.findall(r'<img src="figures/([^"]+)"', art):
            assert (ROOT / "docs/datasets/gt23/figures" / src).exists(), src
        t = c["totals"]
        assert sum(v[0] for v in c["grid"]["cells"].values()) == t["affected"]
        assert sum(v[1] for v in c["grid"]["cells"].values()) == t["total"]
    assert fixed == sum(1 for u in spec["card_updates"].values() if u["status"] == "fixed") and fixed >= 12


def test_headline_card_numbers_equal_the_checked_handoffs():
    """The numbers the cards state, against independent sources: the package files and the verified handoffs."""
    text = visible_text()
    hand = ROOT / "docs/maintainers/handoffs"
    m01 = json.loads((hand / "GT23-M01.json").read_text())["counts"]
    assert (m01["rescaled"], m01["rescaled_exact"], m01["rescaled_estimated"], m01["kept"], m01["ab03_recordings"]) == (52, 7, 45, 436, 40)
    for n in (52, 436, 434):
        assert f"{n}" in text
    assert "113.5 kg" in text and "0.152 m" in text
    q = json.loads((hand / "GT23-PL01.json").read_text())["steps_2_to_4"]["q01_v2"]
    assert (q["before_old_v1"]["failed"], q["after"]["failed"]) == (815, 125)
    s01 = json.loads((hand / "GT23-S01.json").read_text())["counts"]
    assert (s01["authors_windows"], s01["without_windows_gait"], s01["without_windows_window"], s01["without_windows_continuous"]) == (13119, 23, 3, 64)
    assert "9,378 of the authors" in text and "3,741" in text
    for verdict in re.findall(r'class="verdict (v-[a-z]+)"', raw()):
        assert verdict in {"v-fixed", "v-ok", "v-left", "v-nc"}


def test_phase_plots_come_from_the_preview_and_figures_exist():
    page = raw()
    assert page.count('class="phase-signal"') == 12
    assert page.count('<figure class="phase-panel">') >= 12 * 5
    for name in ("page-failures", "page-left-out", "page-limitations"):
        assert f"figures/{name}.svg" in page and (ROOT / f"docs/datasets/gt23/figures/{name}.svg").exists()


def test_no_hashes_paths_or_internal_ids_visible():
    text = visible_text()
    assert not re.search(r"\b[0-9a-f]{32,}\b", text)
    banned = [r"/mnt/", r"converted_datasets", r"\.(json|py|parquet|csv|mat|sto|osim)\b", r"\b[A-Z]{2,4}\d{2}-[A-Z]\d{2}\b", r"\bD-[A-Z0-9]+-",
              r"\bGT23\b", r"\bCORE-\d", r"\bsha\d*\b", r"\bPID\b", r"\bL[125]\b", r"\bS5\b", r"observation_id", r"\bdivisors?\b",
              r"\bcensus\b", r"\bhooks?\b", r"\bgates?\b", r"\blayouts?\b", r"\bmultipliers?\b", r"José", r"Bobby", r"Gregg"]
    for pat in banned:
        assert not re.search(pat, text, flags=0 if pat.startswith(r"\b[A-Z]") or "José" in pat else re.I), pat
    assert "not published yet" in text and "Local review version" in text


def test_status_and_links():
    page = raw()
    assert 'data-status="review"' in page and "local review version (not released)" in page
    assert "problems.html" not in page
    assert not (ROOT / "docs/datasets/gt23/problems.html").exists()


def test_unchecked_is_stated_plainly():
    text = visible_text()
    for needle in ("Not checked", "Where the ankle angle is zero has not been checked", "not approved reference ranges",
                   "A missing or unassessed signal is not evidence of passing"):
        assert needle in text, needle
