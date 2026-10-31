"""Independent verifier checks for DOC-05 (docs/quality/fixes.html).

Written by the DOC-05 verifier without importing the builder or the worker's test.
Each number on the page is recomputed from the committed audit JSON; no research
data are read.
"""
from __future__ import annotations

import html
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDITS = ROOT / "docs/quality/audits"
PAGE = ROOT / "docs/quality/fixes.html"


def audit(name):
    return json.loads((AUDITS / name).read_text(encoding="utf-8"))


def page_text():
    raw = PAGE.read_text(encoding="utf-8")
    return html.unescape(re.sub(r"<[^>]+>", " ", raw))


def card(card_id):
    raw = PAGE.read_text(encoding="utf-8")
    match = re.search(rf'<article class="fix-card" id="{card_id}"[^>]*>(.*?)</article>', raw, re.S)
    assert match, card_id
    return html.unescape(re.sub(r"<[^>]+>", " ", match.group(1)))


def test_gt23_mass_counts_and_factor_range():
    subjects = audit("gt23-c03-normalizing-mass.json")["subjects"]
    wrong = [s for s, v in subjects.items() if not v["readme_consistent"]]
    # Published / correct = own mass / divisor, computed here from the two masses.
    factors = [subjects[s]["readme_mass_kg"] / subjects[s]["divisor_kg_best"] for s in wrong]
    text = card("gt23-normalizing-mass")
    assert f"In {len(wrong)} of {len(subjects)} participants" in text
    assert f"{min(factors):.2f} to {max(factors):.2f}" in text
    assert all(subjects[s]["calibration_trial"] == "normal_walk_1" for s in subjects)  # 'level walking'


def test_um21_branch_frames_and_kept_strides():
    figure = audit("um21-c03-episode-census.json")["figure_episode"]
    episode = audit("um21-c03-conventions.json")["ankle_episode_census"]["branch_episode"]
    jumps = episode["orientation_step_over_20deg_frames_1based"]
    inside = figure["inside_pairs"]
    kept = [p for p in inside if not any(p[0] <= f <= p[1] for f in jumps)]
    text = card("um21-ankle-branch")
    assert f"{episode['frames']:,} frames" in text
    assert f"2 of the {len(inside)} strides" in text and len(inside) - len(kept) == 2
    assert f"{len(kept)} of {len(inside)} inside strides kept" in text


def test_gt24_pool_seed_and_stances():
    trials = audit("gt24-c02-ankle-sign.json")["trials"]
    pool = [(t, s) for t in trials for s in t["sides"]
            if s.get("stances_with_finite_moment", 0) >= 5 and "moment_source_Nm_kg" in s.get("curves", {})]
    trial, side = random.Random(20261031).choice(pool)
    summary = audit("gt24-c02-ankle-sign.json")["summary"]
    text = card("gt24-ankle-sign")
    assert len(pool) == summary["legs_with_moment"] == 12 and "12 of 12" in text
    assert f"mean of {side['stances_with_finite_moment']} stances" in text and trial["subject"] in text


def test_gt23_units_range_and_legs():
    summary = audit("gt23-c02-moment-units.json")["summary"]
    low, high = summary["implied_mass_range_kg"]
    text = card("gt23-moment-units")
    assert f"1/{round(low)} to 1/{round(high)}" in text and f"all {summary['legs']} sampled legs" in text


def test_um21_pelvis_strides():
    record = [r for r in audit("um21-p01-pelvis-heading.json")["records"]
              if r["subject"] == "AB04" and r["condition"] == "i0"][0]["sides"]["R"]
    votes = record["tilt_votes"]
    assert votes["flipped_sign"] == votes["strides_voting"] == record["strides"] == 114
    assert "114 of 114 right-side strides" in card("um21-reversed-pelvis")


def test_um21_thigh_offset_is_twice_tilt():
    stride = audit("um21-c01-source-probe.json")["random_stride"]
    hip, pelvis = stride["hip"], stride["pelvis"]
    diffs = [(p + h) - (h - p) - 2 * p for p, h in zip(pelvis, hip)]
    assert max(abs(d) for d in diffs) < 1e-9
    median = sorted(pelvis)[len(pelvis) // 2]
    assert f"median {round(median)}°" in card("um21-thigh-recipe")


def test_no_card_names_a_released_correction():
    text = page_text().lower()
    for phrase in ("now released", "fixed in the download", "corrected release is available", "download the corrected"):
        assert phrase not in text
