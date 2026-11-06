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
