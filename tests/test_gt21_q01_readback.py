"""GT21-Q01 readback tests on the SYNTHETIC fixture of test_gt21_q01_assessment (known injected values, expected totals written by hand)."""
import argparse
import json
import shutil
from pathlib import Path

from contributor_tools import readback_gt21_q01 as rb
from tests.test_gt21_q01_assessment import SUBJ, world  # noqa: F401  (pytest fixture)

SUMMARY = {"observations": 4, "status": {"failed": 3, "no_failure_found": 1},
           "totals_per_check": {"L1": {"passed": 3, "failed": 1}, "L2": {"failed": 2, "passed": 2}, "L4": {"passed": 3, "missing": 1},
                                "L5": {"passed": 4}, "S1": {"passed": 4}, "S2": {"passed": 4}, "S3": {"passed": 4},
                                "S4": {"passed": 3, "unchecked": 1}, "S5": {"unchecked": 1, "passed": 2, "failed": 1},
                                "P1": {"unchecked": 4}, "PD": {"failed": 1, "passed": 3}}}


def lay_out(world, tmp_path, monkeypatch):
    out = world[2]
    base = tmp_path / "root"
    shutil.copytree(out.parent / "export", base / rb.BASE / f"gt21_rb07_export_{SUBJ}")
    shutil.copytree(out, base / "assess" / SUBJ)
    (base / "summary.json").write_text(json.dumps(SUMMARY))
    rs = base / rb.BASE / f"gt21_rb07_export_{SUBJ}" / "run_summary.json"
    monkeypatch.setattr(rb, "ROOT", base)
    monkeypatch.setattr(rb.os, "nice", lambda n: 19)
    return base, rs


def args(base):
    return argparse.Namespace(subjects=SUBJ, assessment_roots="assess", all_roots="assess", summary="summary.json", output_root="rb")


def test_readback_agrees_with_the_assessment(world, tmp_path, monkeypatch):
    base, _ = lay_out(world, tmp_path, monkeypatch)
    assert rb.run(args(base)) == 0
    rep = json.loads((base / "rb" / "readback.json").read_text())
    assert rep["status"] == "passed" and rep["participants"][SUBJ]["sample_phase"] == 3 and rep["participants"][SUBJ]["mismatches"] == 0


def test_readback_detects_a_tampered_assessment_line(world, tmp_path, monkeypatch):
    base, _ = lay_out(world, tmp_path, monkeypatch)
    p = base / "assess" / SUBJ / "assessment.jsonl"
    lines = [json.loads(x) for x in p.read_text().splitlines()]
    for l in lines:
        if l["observation_id"].endswith("left/0000"):
            l["failed_samples"]["hip_flexion_angle_ipsi_rad"]["L1"] = 7     # truth is 1
    p.write_text("".join(json.dumps(x) + "\n" for x in lines))
    assert rb.run(args(base)) == 1
    rep = json.loads((base / "rb" / "readback.json").read_text())
    assert rep["status"] == "failed" and any("L1" in str(f) for f in rep["failures"])
