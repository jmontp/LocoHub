"""GT23-R01 adapter rules (the shared builder is tested in test_release_package.py). Fixtures are SYNTHETIC, not Georgia Tech data."""
import os
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

import pytest

from contributor_tools import run_gt23_r01_bundle as r01
from contributor_tools.common import release_package as rp


def raw(oid, side, overall="no_failure_found", limits=(), table="phase", rec="AB99/x_1", flight=None, failed=(), structural="pass",
        held=None):
    return {"observation_id": oid, "reference_side": side, "table": table, "observation_type": "individual_cycle", "task": "t",
            "task_id": "t1", "source_recording_id": rec, "rows": 150, "overall": overall, "limitations": list(limits),
            "mass_note_key": "cannot_be_told", "flight": ({"flight_cycle": flight} if flight is not None else None),
            "held_signals": held or {}, "structural": {"state": structural, "S5_side_check": "fail" if structural == "fail" else "pass"},
            "plausibility": {"failed_limits": list(failed), "failed_channels": ["c"] if failed else [], "failed_samples": {"c": {"L5": 3}} if failed else {},
                             "channel_states": {"pass": ["a"]}}}


def test_failure_causes_limits_and_side_check():
    assert r01.failure_causes(raw("o", "left", "failed", failed=["L5", "L1"])) == ["L1", "L5"]
    assert r01.failure_causes(raw("o", "left", "failed", structural="fail")) == ["S5_side_check"]


def test_package_entry_has_every_required_key_and_keeps_status_words():
    e = r01.package_entry(raw("AB99/x_1/L/1", "left", "failed", failed=["L5"], rec="AB99/x_1", flight=True,
                              held={"cop_anterior_ipsi_m": "held"}))
    assert all(k in e for k in rp.ASSESSMENT_REQUIRED)
    assert e["status"] == "failed" and e["failed_limits"] == ["L5"] and e["subject"] == "AB99" and e["flight"] is True
    assert e["attributes"]["foot_cop_held"] is True
    ok = r01.package_entry(raw("o", "right"))
    assert ok["failed_limits"] == [] and ok["flight"] is None and ok["attributes"]["foot_cop_held"] is False
    assert rp.slim(ok)["key"] == ("o", "right")


def test_count_flag_by_type_flight_and_filtered():
    es = [rp.slim(r01.package_entry(x)) for x in (
        raw("o1", "left", limits=["run_label_check"], flight=True), raw("o2", "left", limits=["run_label_check"], flight=False),
        raw("o3", "right", "failed", limits=["run_label_check"], flight=True, failed=["L5"]), raw("o4", "right"))]
    c = rp.count_flag(es, "run_label_check")
    assert (c["observations"], c["cycles_with_flight"], c["in_filtered_variant"], c["failed_in_assessment"]) == (3, 2, 2, 1)
    assert rp.count_flag(es, "ab09_divisor")["observations"] == 0


def test_export_and_window_exclusion_rows():
    ex1 = [{"recording": "r1", "segment_id": "S/r1/both/1", "side": "both", "stage": "S01", "reason": "shorter_than_0.25_s", "start_s": 1, "end_s": 1.1, "task": "t"},
           {"recording": "r2", "segment_id": "S/r2/both/9", "side": "both", "stage": "S01", "reason": "old", "start_s": 2, "end_s": 2.1, "task": "t"}]
    ex2 = [{"recording": "r2", "segment_id": "S/r2/both/9", "side": "both", "stage": "S01", "reason": "old", "start_s": 2, "end_s": 2.1, "task": "t"}]
    rows = r01.export_exclusion_rows("S", ex1, ex2, {"r2"})
    assert [r["exclusion_id"] for r in rows] == ["S/r1/both/1", "S/r2/both/9"]          # the E01 r2 row is replaced, not doubled
    wins = [{"fate": "exported", "file": "f", "row": 0, "reason": None, "recording": "r1", "side": "L", "task": "t", "start": 0, "end": 1},
            {"fate": "not_exported", "file": "f", "row": 1, "reason": "nearest_record_excluded: shorter_than_0.25_s", "recording": "r1", "side": "R",
             "task": "t", "start": 1, "end": 2}]
    w = r01.window_exclusion_rows("S", wins)
    assert len(w) == 1 and w[0]["reason_code"] == "nearest_record_excluded" and w[0]["detail"] == "shorter_than_0.25_s"
    assert w[0]["reference_side"] == "right" and w[0]["stage"] == "upstream_not_released"
    assert all(set(r) <= set(rp.EXCLUSION_FIELDS) for r in rows + w)


def test_assessment_failure_rows_are_filtered_only_exclusions():
    es = [rp.slim(r01.package_entry(raw("S/r1/L/5", "left", "failed", failed=["L5"], rec="S/r1")))]
    r = rp.assessment_failure_rows(es)[0]
    assert r["stage"] == "filtered_variant_only" and r["in_full_variant"] is True and r["in_filtered_variant"] is False
    assert r["reason_code"] == "L5" and r["observation_id"] == "S/r1/L/5"


def test_cop_wording_states_the_24_november_frame():
    t = r01.CORRECTED_COP_TEXT
    assert "side-view plane" in t and "100 mm forward of the ankle joint centre" in t and "Toe-out" in t
    assert "forward along heel to toe" in t and "superseded" in t     # names the old wording it replaces


def test_pilot_and_full_subjects():
    assert r01.stage_subjects("pilot") == ["AB03", "AB13"] and len(r01.stage_subjects("full")) == 12
