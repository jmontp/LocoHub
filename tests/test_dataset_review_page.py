"""General dataset review page builder and the backlog-derived status label.

Synthetic fixtures (labelled synthetic) test the gate and the page text. The UMich 2021
test rebuilds the committed page from its local bundle and skips when the bundle is absent.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "contributor_tools"))
import build_dataset_review_page as B  # noqa: E402
import dataset_status as S  # noqa: E402


# ---------- synthetic bundle ----------
def make_root(tmp_path: Path, r01_status: str):
    slug = "syn01"
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "manifest.json").write_text(json.dumps({"counts": {
        "upstream_observations": 12, "full": 10, "filtered": 9,
        "exclusions_by_reason_code": {"t04_2_outside_stride_rule": 2}}}))
    (bundle / "dataset_index.json").write_text(json.dumps({"recordings": [
        {"subject": "S1"}, {"subject": "S1"}, {"subject": "S2"}]}))
    with (bundle / "exclusions.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["reason_code", "reason"])
        w.writeheader()
        w.writerow({"reason_code": "t04_2_outside_stride_rule", "reason": "below 50"})
        w.writerow({"reason_code": "t04_2_outside_stride_rule", "reason": "above 250"})
    with (bundle / "held_signals.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["recording", "column"])
        w.writeheader()
    col = "knee_flexion_angle_ipsi_rad"
    flat = {"n": [3] * 150, "mean": [0.1 * (i % 10) for i in range(150)], "sd": [0.05] * 150}
    (bundle / "phase_preview.json").write_text(json.dumps({"groups": [
        {"task": "level_walking", "condition": "i0", "columns": {col: flat}}]}))
    (tmp_path / "handoff.json").write_text(json.dumps({"task_id": "SYN-R01", "columns": [{"column": col, "status": "checked"}]}))
    fix = {"key": "clock", "card": "Timing", "total_line": "2 of 3 recordings", "denominator_text": "Synthetic.",
           "table": {"columns": ["Recording"], "rows": [["S1/i0"]], "fold": False}, "grid_caption": "Synthetic grid.",
           "direction": "", "knock_on": [{"verdict": "Left out", "signal": "Knee", "line": "Left out.", "evidence": ""}]}
    (tmp_path / "scope.json").write_text(json.dumps({"fixes": [fix]}))
    figs = tmp_path / "docs/datasets" / slug / "figures"
    figs.mkdir(parents=True)
    (figs / "scope-clock.svg").write_text('<svg viewBox="0 0 72 36" xmlns="http://www.w3.org/2000/svg"></svg>')
    (figs / "figures.json").write_text("{}")
    backlog = tmp_path / "backlog.json"
    backlog.write_text(json.dumps({"tasks": [{"id": "SYN-R01", "dataset": slug, "status": r01_status}], "datasets": []}))
    spec = {
        "slug": slug, "display_name": "Synthetic 1", "title": "Synthetic 1 · LocoHub", "css_class": "review-page",
        "r01_task_id": "SYN-R01", "bundle": "bundle", "handoff": "handoff.json", "scope": "scope.json",
        "verified_date": "2026-01-01", "meta_description": "Synthetic.", "heading_note": "Synthetic page.",
        "lead": "{subjects} participants, {recordings} recordings, {full:,} strides, {filtered:,} cleaned.",
        "conditions": {"i0": "level"}, "colors": {"i0": "#009E73"},
        "panels": [{"task": "level_walking", "label": "Level walking", "conditions": ["i0"]}],
        "plain": {col: {"name": "Knee angle", "unit": "radians"}},
        "status_text": {"checked": {"label": "Checked", "note": "Synthetic check."}},
        "scope_questions": {"clock": "Which recordings are shifted?"}, "fixed_note": "Synthetic note.",
        "cards": [{"title": "Timing", "wrong": "w", "how": "h", "did": "d", "example": "e", "figures": [], "single": False, "scope_key": "clock"}],
        "exclusion_rows": [{"what": "Too short or long ({short} short, {long} long)", "count": {"reason": "t04_2_outside_stride_rule"}, "where": "Neither", "why": "Synthetic."}],
        "accounting_note": "{upstream} in, {full} full, {filtered} cleaned.",
        "checked": {"checked": ["One."], "not_checked": ["Two."], "note": "Note."},
        "phase_note": "Phase.", "columns_note": "Columns.", "downloads_text": "Not published.",
    }
    return spec, backlog


def test_refuses_bundle_whose_r01_is_not_done(tmp_path):
    for status in ("working", "review", "blocked"):
        sub = tmp_path / status
        sub.mkdir()
        spec, backlog = make_root(sub, status)
        with pytest.raises(B.BundleNotReady):
            B.build(spec, root=sub, backlog_path=backlog)


def test_review_status_needs_explicit_flag(tmp_path):
    spec, backlog = make_root(tmp_path, "review")
    assert "Synthetic 1" in B.build(spec, root=tmp_path, backlog_path=backlog, allow_review=True)


def test_done_bundle_builds_with_numbers_from_the_bundle(tmp_path):
    spec, backlog = make_root(tmp_path, "done")
    page = B.build(spec, root=tmp_path, backlog_path=backlog)
    assert "2 participants, 3 recordings, 10 strides, 9 cleaned." in page
    assert "Too short or long (1 short, 1 long)" in page and '<td class="num">2</td>' in page
    assert "12 in, 10 full, 9 cleaned." in page
    assert page.count("<svg") == 1 and "scope-clock.svg" in page  # one phase plot; the scope grid is an image
    assert not re.search(r"/mnt/|SYN-R01", re.sub(r"<(script|style)\b.*?</\1>", "", page, flags=re.S))


def test_unexplained_exclusion_reason_is_refused(tmp_path):
    spec, backlog = make_root(tmp_path, "done")
    spec["exclusion_rows"] = []
    with pytest.raises(ValueError):
        B.build(spec, root=tmp_path, backlog_path=backlog)


def test_main_returns_error_and_writes_nothing_when_not_done(tmp_path, monkeypatch):
    spec, backlog = make_root(tmp_path, "working")
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec))
    monkeypatch.setattr(B, "ROOT", tmp_path)
    monkeypatch.setattr(B, "BACKLOG", backlog)
    out = tmp_path / "out.html"
    assert B.main([str(spec_path), "--out", str(out)]) == 1
    assert not out.exists()


# ---------- UMich 2021 reproduces ----------
UM21_BUNDLE = ROOT / "converted_datasets/reconversion_v2/um21_r01_package_v4"


@pytest.mark.skipif(not (UM21_BUNDLE / "manifest.json").exists(), reason="local bundle absent")
def test_um21_page_is_reproduced_from_its_inputs():
    spec = json.loads((ROOT / "contributor_tools/page_specs/um21.json").read_text(encoding="utf-8"))
    built = B.build(spec)
    assert built == (ROOT / "docs/datasets/um21/index.html").read_text(encoding="utf-8")
    c = json.loads((UM21_BUNDLE / "manifest.json").read_text())["counts"]
    assert f"{c['observations_full']:,} strides" in built


# ---------- status label rule ----------
def backlog(tasks, gates=None, ds="x1"):
    return {"tasks": [{"id": i, "dataset": ds, "status": s} for i, s in tasks],
            "datasets": [{"id": ds, "gate_status": gates or {}}]}


def test_status_rule_follows_the_backlog_only():
    assert S.status_for(backlog([("X1-R01", "done")]), "x1") == ("review", False)
    assert S.status_for(backlog([("X1-R01", "review"), ("X1-S02", "working")]), "x1") == ("review", True)
    assert S.status_for(backlog([("X1-R01", "blocked"), ("X1-X01", "working")]), "x1") == ("rebuilding", False)
    assert S.status_for(backlog([("X1-F01", "blocked")], {"readback": "partial"}), "x1") == ("partial", False)
    assert S.status_for(backlog([("X1-F01", "blocked")], {"pilot": "unreviewed"}), "x1") == ("legacy", False)
    assert S.status_for(backlog([]), "x1") == ("legacy", False)


def test_historical_pages_use_the_historical_entry():
    data = {"tasks": [], "datasets": [{"id": "historical", "gate_status": {}}]}
    assert S.status_for(data, "ca23") == ("legacy", False)


def test_committed_pages_carry_the_current_status():
    data = S.load_backlog()
    for path, fn in S.targets(data):
        assert fn(path.read_text(encoding="utf-8")) == path.read_text(encoding="utf-8"), f"run dataset_status.py: {path}"


def test_problems_are_folded_into_the_gt21_and_gt23_pages():
    cat = (ROOT / "docs/index.html").read_text(encoding="utf-8")
    # GT21 folded its problems into the dataset page too: no separate page, no dead link
    assert not (ROOT / "docs/datasets/gt21/problems.html").exists()
    assert "gt21/problems.html" not in cat
    assert "problems.html" not in (ROOT / "docs/datasets/gt21/index.html").read_text(encoding="utf-8")
    # GT23 folded its problems into the dataset page: no separate page, no dead link
    assert not (ROOT / "docs/datasets/gt23/problems.html").exists()
    assert "gt23/problems.html" not in cat
    assert "problems.html" not in (ROOT / "docs/datasets/gt23/index.html").read_text(encoding="utf-8")


# ---------- Georgia Tech 2023 reproduces ----------
GT23_BUNDLE = ROOT / "converted_datasets/reconversion_v2/gt23_r01_review_v11"


@pytest.mark.skipif(not (GT23_BUNDLE / "manifest.json").exists(), reason="local bundle absent")
def test_gt23_page_is_reproduced_from_its_inputs():
    spec = json.loads((ROOT / "contributor_tools/page_specs/gt23.json").read_text(encoding="utf-8"))
    built = B.build(spec)
    assert built == (ROOT / "docs/datasets/gt23/index.html").read_text(encoding="utf-8")
