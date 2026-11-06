"""UMich 2021 page: counts match the local bundle manifest, every exclusion reason shows, nothing internal is visible.

Reads the committed page, and the small bundle manifest and exclusions list (no data tables).
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "converted_datasets/reconversion_v2/um21_r01_review_v2"
PAGE = ROOT / "docs/datasets/um21/index.html"
pytestmark = pytest.mark.skipif(not (BUNDLE / "manifest.json").exists(), reason="local bundle absent")


def visible_text():
    t = PAGE.read_text(encoding="utf-8")
    t = re.sub(r"<(script|style|svg)\b.*?</\1>", " ", t, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))


def test_counts_equal_manifest():
    c = json.loads((BUNDLE / "manifest.json").read_text())["counts"]
    text = visible_text()
    assert f"{c['full']:,} strides" in text and f"{c['filtered']:,}" in text
    assert (c["full"], c["filtered"]) == (7545, 7544)
    idx = json.loads((BUNDLE / "dataset_index.json").read_text())["recordings"]
    assert f"{len({r['subject'] for r in idx})} participants" in text
    assert f"{len(idx)} recordings" in text


def test_every_exclusion_reason_and_count_appears():
    rows = list(csv.DictReader((BUNDLE / "exclusions.csv").open()))
    counts = {}
    for r in rows:
        counts[r["reason_code"]] = counts.get(r["reason_code"], 0) + 1
    text = visible_text()
    expect = {"t04_2_outside_stride_rule": "Too short or too long to check",
              "c03_2_sudden_jump": "Sudden ankle jumps",
              "q01_limit_failed": "beyond the angle limit"}
    assert set(counts) == set(expect)
    for code, phrase in expect.items():
        row = re.search(re.escape(phrase) + r".{0,200}?<?", text)
        assert row, phrase
        assert re.search(re.escape(phrase) + r"[^|]{0,120}? " + str(counts[code]) + r" ", text), (phrase, counts[code])
    for needle in ("never converted", "left empty", "Foot angle", "AB03, 10° incline", "left out earlier"):
        assert needle in text


def test_no_hashes_paths_or_internal_ids_visible():
    text = visible_text()
    assert not re.search(r"\b[0-9a-f]{32,}\b", text)
    for bad in ("/mnt/", "converted_datasets", ".parquet", ".json", "C:\\", "um21:Streaming", "D-UM21", "UM21-", "census", "hook"):
        assert bad not in text, bad
    assert "not published yet" in text


def test_unchecked_is_stated_plainly():
    text = visible_text()
    assert "Not checked" in text and "Moments, powers" in text and "Where the ankle angle is zero" in text


# ---------- fix scope blocks ("How much was affected", "What else this could affect") ----------
SCOPE = ROOT / "docs/quality/audits/um21-r01-fix-scope.json"
AUDITS = ROOT / "docs/quality/audits"


def scope():
    return json.loads(SCOPE.read_text(encoding="utf-8"))


def cards():
    t = PAGE.read_text(encoding="utf-8")
    return re.findall(r'<article class="fix-card">(.*?)</article>', t, flags=re.S)


def test_every_card_has_scope_blocks_and_images():
    cs = cards()
    assert len(cs) == 6 == len(scope()["fixes"])
    for c, f in zip(cs, scope()["fixes"]):
        assert "How much was affected" in c and "What else this could affect" in c
        assert f"figures/scope-{f['key']}.svg" in c
        assert c.count("<img") >= 2  # the scope grid plus at least one before/after or example figure
        assert html_unescape(f["total_line"]) in html_unescape(re.sub(r"<[^>]+>", "", c))


def html_unescape(s):
    import html
    return re.sub(r"\s+", " ", html.unescape(s))


def test_scope_totals_equal_independent_counts():
    s = {f["key"]: f["total_numbers"] for f in scope()["fixes"]}
    idx = json.loads((BUNDLE / "dataset_index.json").read_text())["recordings"]
    converted = sum(r["t04_mapped_observations"] for r in idx)
    unmapped = sum(r["unmapped"] for r in idx)
    assert (converted, unmapped, converted + unmapped) == (7547, 15, 7562)
    ab04 = [r for r in idx if r["recording"] == "AB04/i0"][0]["t04_mapped_observations"]
    assert s["pelvis_backwards"]["strides_affected"] == ab04 and s["pelvis_backwards"]["samples_affected"] == ab04 * 150
    assert s["pelvis_backwards"]["strides_total"] == 7562 and s["pelvis_backwards"]["samples_total"] == 7562 * 150
    assert s["sign_rule"]["strides_affected"] == converted and s["sign_rule"]["strides_sign_flipped"] == converted - ab04
    assert s["thigh_shank"]["strides_affected"] == converted and s["thigh_shank"]["recordings_affected"] == len(idx) == 44
    census = json.loads((AUDITS / "um21-t02-clock-census.json").read_text())["totals"]
    assert s["clock"]["strides_affected"] == census["strides_as_published_all"] - census["strides_as_published_aligned_only"] == 1064
    assert s["clock"]["strides_total"] == 8626 and s["clock"]["recordings_affected"] == 6
    held = list(csv.DictReader((BUNDLE / "held_signals.csv").open()))
    assert s["power"]["channels_held"] == len(held) == 8
    assert s["power"]["stride_joint_values_held"] == sum(int(h["observations"]) for h in held)
    ab07 = [r for r in idx if r["recording"] == "AB07/i10"][0]
    log_rows = sum(1 for _ in (BUNDLE / "ankle_reexpression_log.csv").open()) - 1
    assert s["ankle_180"]["turned_back"] * 150 == log_rows == 3000
    assert s["ankle_180"]["left_out"] == ab07["dropped_c03_2"] == 2
    assert s["ankle_180"]["strides_affected"] == 22 and s["ankle_180"]["recording_strides"] == ab07["t04_mapped_observations"] + ab07["unmapped"]
    for f in scope()["fixes"]:  # percentages follow from the counts
        n = f["total_numbers"]
        if "strides_pct" in n:
            assert abs(n["strides_pct"] - 100 * n["strides_affected"] / n["strides_total"]) < 0.06  # rounded to 1 or 2 decimals


def test_every_knock_on_verdict_has_evidence_or_says_not_checked():
    words = {"Also wrong, fixed", "Checked, not affected", "Left out", "Not checked"}
    items = 0
    for f in scope()["fixes"]:
        for k in f["knock_on"]:
            items += 1
            assert k["verdict"] in words
            assert k["evidence"] or k["verdict"] == "Not checked", k["signal"]
    assert items >= 30
    for c in cards():
        for li in re.findall(r'<li class="ko-item">(.*?)</li>', c, flags=re.S):
            assert "How we know:" in li or ("Not checked" in li and "No evidence yet." in li)
    thigh = [f for f in scope()["fixes"] if f["key"] == "thigh_shank"][0]
    knee = [k for k in thigh["knock_on"] if k["signal"].startswith("Knee angle")][0]
    assert knee["verdict"] == "Checked, not affected" and "does not change the knee" in knee["line"] and "shank is thigh" in knee["line"]


def test_scope_blocks_use_plain_words():
    text = visible_text()
    for bad in ("census", "hook", "layout", "gate", "multiplier", "observation map", "T04", "Q01", "C03", "P01", "decision D-"):
        assert bad not in text, bad
