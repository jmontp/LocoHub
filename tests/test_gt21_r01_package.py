"""GT21-R01 adapter rules (the shared builder is tested in test_release_package.py). Fixtures are SYNTHETIC, not Georgia Tech data."""
import os
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

import numpy as np
import pyarrow as pa
import pytest

from contributor_tools import run_gt21_r01_package as r01
from contributor_tools.common import release_package as rp


def xrow(reason, **kw):
    d = {"step_id": "AB99/m/rec/left/0001", "source_recording_id": "AB99/m/rec", "leg": "left", "stage": "RB03 segmentation",
         "mode": "treadmill", "reason": reason, "start_s": 1.0, "end_s": 2.0}
    d.update(kw)
    return d


def test_exclusion_kinds_split_code_and_detail():
    assert r01.exclusion_kind("authors_rule_discard") == ("authors_rule_discard", "authors_rule_discard", "")
    k, c, d = r01.exclusion_kind("authors_rule_discard: more than 2 distinct treadmill speeds inside the step")
    assert (k, c) == ("authors_rule_discard", "authors_rule_discard") and d.startswith("more than 2")
    assert r01.exclusion_kind("fewer than 3 fit markers on femur_r: have ['R_Knee_Lat']")[0] == "recording_excluded_marker_fit"
    with pytest.raises(ValueError):
        r01.exclusion_kind("something new")


def test_export_exclusion_rows_use_known_fields_and_keep_every_row():
    rows = r01.export_exclusion_rows("AB99", [xrow("authors_rule_case_not_found"),
                                              {k: v for k, v in xrow("recording_not_converted_in_pass", leg=None,
                                                                    step_id="AB99/m/x").items() if k not in ("start_s", "end_s")}])
    assert len(rows) == 2 and all(set(r) <= set(rp.EXCLUSION_FIELDS) and r["stage"] == "upstream_not_released" for r in rows)
    assert rows[1]["reference_side"] == "" and rows[1]["start_s"] == ""
    none_id = r01.export_exclusion_rows("AB99", [xrow("fewer than 3 fit markers on femur_r: have ['R_Knee_Lat']", step_id=None, leg=None)])
    assert none_id[0]["exclusion_id"] == "AB99/m/rec#recording"


def line(**kw):
    e = {"observation_id": "AB99/m/rec/left/0001", "reference_side": "left", "table": "phase", "observation_type": "individual_cycle",
         "subject": "AB99", "source_recording_id": "AB99/m/rec", "task": "t", "task_id": "x", "rows": 150,
         "status": "no_failure_found", "failed_limits": [], "failed_channels": [], "failed_samples": {}, "limitations": [],
         "flight": None, "attributes": {}, "held_signals": {}, "channel_states": {}}
    e.update(kw)
    return e


def test_package_entry_checks_keys_and_status():
    assert rp.slim(r01.package_entry(line()))["overall"] == "no_failure_found"
    with pytest.raises(ValueError):
        r01.package_entry({k: v for k, v in line().items() if k != "attributes"})
    with pytest.raises(ValueError):
        r01.package_entry(line(status="maybe"))


def table(power_scale=1.0, nan_power_at=None):
    m = np.array([1.0, 2.0, np.nan, 4.0])
    v = np.array([0.5, -1.0, 3.0, np.nan])
    cols = {"observation_id": ["a"] * 4, "reference_side": ["left"] * 4}
    for j in r01.JOINTS:
        for sd in ("ipsi", "contra"):
            cols[f"{j}_moment_{sd}_Nm_kg"] = m
            cols[f"{j}_velocity_{sd}_rad_s"] = v
            p = m * v * power_scale
            if nan_power_at is not None:
                p = p.copy(); p[nan_power_at] = np.nan
            cols[f"{j}_power_{sd}_W_kg"] = p
    return pa.table(cols)


def test_power_check_counts_zero_for_the_rule_and_flags_deviations_without_changing_data():
    chk = r01.PowerCheck("phase")
    t = table()
    assert chk(t) is t
    assert all(r["rows_deviating"] == 0 and r["rows_new_finite"] == 2 for r in chk.rows())
    bad = r01.PowerCheck("phase")
    bad(table(power_scale=1.1))
    assert all(r["rows_deviating"] == 2 for r in bad.rows())
    missing = r01.PowerCheck("phase")
    missing(table(nan_power_at=0))  # power missing where moment and speed exist: one pattern mismatch per column
    assert all(r["rows_deviating"] == 1 for r in missing.rows())


def test_batches_cover_the_22_participants_once_and_pilot_is_inside():
    assert len(r01.SUBJECTS) == 22 and len(set(r01.SUBJECTS)) == 22
    assert set(r01.PILOT_SUBJECTS) <= set(r01.SUBJECTS)
    assert r01.q01_path("AB27")[1] == "b5" and r01.q01_path("AB30")[1] == "b6"
