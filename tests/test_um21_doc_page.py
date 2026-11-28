"""UMich 2021 page (package v4): counts match the package, every card, exclusion and limitation shows, nothing internal is visible.

Reads the committed page and the package's small files (manifest, limitations, dataset index, exclusions, evidence lists).
It never opens a table file.
"""
from __future__ import annotations

import csv
import html
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "converted_datasets/reconversion_v2/um21_r01_package_v4"
PAGE = ROOT / "docs/datasets/um21/index.html"
SCOPE = ROOT / "docs/quality/audits/um21-problem-scope.json"
SPEC = ROOT / "contributor_tools/page_specs/um21.json"
pytestmark = pytest.mark.skipif(not (BUNDLE / "manifest.json").exists(), reason="local package absent")


def raw():
    return PAGE.read_text(encoding="utf-8")


def visible_text():
    t = re.sub(r"<(script|style|svg)\b.*?</\1>", " ", raw(), flags=re.S)
    attrs = " ".join(re.findall(r'(?:alt|aria-label)="([^"]*)"', t))
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t) + " " + attrs))


def test_counts_equal_the_package():
    c = json.loads((BUNDLE / "manifest.json").read_text())["counts"]
    assert (c["observations_full"], c["observations_filtered"], c["failed_observations"]) == (7545, 7523, 22)
    text = visible_text()
    assert f"{c['observations_full']:,} strides" in text and f"{c['observations_filtered']:,}" in text
    idx = json.loads((BUNDLE / "dataset_index.json").read_text())["recordings"]
    assert f"{len({r['subject'] for r in idx})} participants" in text and f"{len(idx)} recordings" in text
    assert "60 of 88 legs" in text


def test_every_exclusion_row_is_listed_and_adds_up():
    c = json.loads((BUNDLE / "manifest.json").read_text())["counts"]
    rows = list(csv.DictReader((BUNDLE / "exclusions.csv").open()))
    assert len(rows) == c["exclusions_total"] == 39
    spec = json.loads(SPEC.read_text())
    text = visible_text()
    listed = 0
    for row in spec["exclusion_rows"]:
        n = c
        for k in row["count"]:
            n = n[k]
        listed += n
        assert re.search(re.escape(html.unescape(row["what"])) + r" " + f"{n:,}" + r" ", text), row["what"]
    assert listed == len(rows)


def test_every_limitation_shows():
    lim = json.loads((BUNDLE / "limitations.json").read_text())["limitations"]
    spec = json.loads(SPEC.read_text())
    text = visible_text()
    assert len(lim) == len(spec["limit_plain"]) == 9
    for x in lim:
        assert html.unescape(spec["limit_plain"][x["id"]]) in text, x["id"]


def test_every_card_has_status_scope_and_images():
    scope, spec = json.loads(SCOPE.read_text()), json.loads(SPEC.read_text())
    arts = {m.group(1): m.group(0) for m in re.finditer(r'<article class="fix-card" id="(\w+)">.*?</article>', raw(), re.S)}
    assert set(arts) == {c["key"] for c in scope["cards"]} == set(spec["card_updates"]) and len(arts) == 10
    for c in scope["cards"]:
        art = arts[c["key"]]
        assert html.escape(spec["status_words"][spec["card_updates"][c["key"]]["status"]], quote=True) in art
        assert f"figures/scope-{c['key']}.svg" in art and html.escape(c["total_line"], quote=True) in art
        assert "What we did" in art and "What else this could affect" in art
        for src in re.findall(r'<img src="figures/([^"]+)"', art):
            assert (ROOT / "docs/datasets/um21/figures" / src).exists(), src
    words = {"Also wrong, fixed", "Checked, not affected", "Left out", "Not checked", "Open limit"}
    assert all(k["verdict"] in words for c in scope["cards"] for k in c["knock_on"])


def test_pressure_point_card_equals_the_leg_list():
    legs = list(csv.DictReader((BUNDLE / "evidence/cop_legs.csv").open()))
    held = [x for x in legs if x["status"] != "published"]
    assert (len(legs), len(legs) - len(held), len(held)) == (88, 60, 28)
    card = {c["key"]: c for c in json.loads(SCOPE.read_text())["cards"]}
    rows = {r[0]: r for r in card["cop"]["table"]["rows"]}
    assert sum(int(r[1]) for r in rows.values()) == 88
    assert sum(int(x["strides"]) for x in held) == 2383
    ruled = [x for x in held if x["pending_by_ruling"] == "True"]
    assert len({x["recording"] for x in ruled}) == 5 and sum(int(x["strides"]) for x in ruled) == 829


def test_power_gap_equals_the_package_and_foot_angle_ships():
    lim = {x["id"]: x for x in json.loads((BUNDLE / "limitations.json").read_text())["limitations"]}
    gap = lim["power_from_moment_and_speed"]["gap_source_power_vs_moment_times_speed"]
    text = visible_text()
    for col in ("hip_flexion_power_ipsi_W_kg", "knee_flexion_power_ipsi_W_kg", "ankle_dorsiflexion_power_ipsi_W_kg"):
        assert f"{100 * gap[col]['median_nrms']:.0f}%" in text
    assert "Foot angle" in text and "foot angle and foot angle speed are not released" not in text.lower()


def test_phase_plots_come_from_the_preview():
    page = raw()
    assert page.count('class="phase-signal"') == 13
    assert page.count('<figure class="phase-panel">') >= 13 * 4


def test_no_hashes_paths_or_internal_ids_visible():
    text = visible_text()
    assert not re.search(r"\b[0-9a-f]{32,}\b", text)
    banned = [r"/mnt/", r"converted_datasets", r"\.(json|py|parquet|csv|mat)\b", r"\b[A-Z]{2,4}\d{2}-[A-Z]\d{2}\b", r"\bD-[A-Z0-9]+-", r"\bUM21\b",
              r"\bCORE-\d", r"\bsha\d*\b", r"\bPID\b", r"\bL[125]\b", r"observation_id", r"\bdivisors?\b", r"\bcensus\b", r"\bhooks?\b",
              r"\bgates?\b", r"\blayouts?\b", r"\bmultipliers?\b", r"José", r"Bobby", r"Gregg"]
    for pat in banned:
        assert not re.search(pat, text, flags=0 if "José" in pat or pat.startswith(r"\b[A-Z]") else re.I), pat
    assert "not published yet" in text and "Local review version" in text


def test_held_back_is_stated_plainly_and_unchecked_is_stated():
    text = visible_text()
    for needle in ("Held-back data: five recordings left as they are", "We did not investigate the cause further", "Not checked",
                   "not approved reference ranges"):
        assert needle in text, needle
