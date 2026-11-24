"""UM21-R01 v3 adapter rules (the shared builder is tested in test_release_package.py). Fixtures are SYNTHETIC, not UMich data."""
import os
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

import pytest

from contributor_tools import run_um21_r01_package as r01
from contributor_tools.common import release_package as rp


def v2row(code, stage="upstream_not_released", rec="AB03/i10", side="right"):
    return {"observation_id": f"um21:Streaming/{rec}:{side}:frames:1:2".replace("/", "/Tread/", 1) if False else
            f"um21:Streaming/{rec.split('/')[0]}/Tread/{rec.split('/')[1]}:{side}:frames:2367:2413",
            "recording": rec, "reference_side": side, "stage": stage, "reason_code": code, "reason": "r", "decision": "D",
            "in_full_variant": "False", "in_filtered_variant": "False"}


def test_inherited_exclusions_keep_stride_rule_and_jump_rows_and_drop_the_old_assessment_row():
    rows = r01.inherited_exclusion_rows([v2row("t04_2_outside_stride_rule"),
                                         v2row("c03_2_sudden_jump", stage="release_membership", rec="AB07/i10"),
                                         v2row("q01_limit_failed", stage="filtered_variant_only", rec="AB08/i0", side="left")])
    assert [r["kind"] for r in rows] == ["upstream_stride_rule", "upstream_sudden_jump"]
    assert rows[0]["source_recording_id"] == "um21:Streaming/AB03/Tread/i10" and rows[0]["subject"] == "UM21_AB03"
    assert "not re-evaluated" in rows[1]["reason"] and rows[1]["stage"] == "release_membership"
    assert all(set(r) <= set(rp.EXCLUSION_FIELDS) and r["in_full_variant"] is False and r["in_filtered_variant"] is False for r in rows)
    with pytest.raises(ValueError):
        r01.inherited_exclusion_rows([v2row("something_new")])


def entry(rec, side, cop):
    return rp.slim({"observation_id": f"{rec}:{side}:frames:1:2", "reference_side": side, "table": "phase",
                    "observation_type": "individual_cycle", "subject": "UM21_AB01", "source_recording_id": rec, "task": "t",
                    "task_id": "x", "rows": 150, "status": "no_failure_found", "failed_limits": [], "failed_channels": [],
                    "failed_samples": {}, "limitations": [], "flight": None, "attributes": {"cop_status": cop},
                    "held_signals": {}, "channel_states": {}})


def test_published_leg_count_uses_legs_not_strides():
    es = [entry("r1", "right", "published"), entry("r1", "right", "no_loaded_samples"), entry("r1", "left", "held"),
          entry("r1", "left", "held"), entry("r2", "right", "held")]
    assert r01.published_leg_count(es) == (1, 2, 3)


def test_cop_leg_rows_and_glitch_rows_from_an_assessment_shape():
    m = {"holdout_r": 0.99, "toe_within_4cm_fraction": 1.0, "plate_assignment_same_plate_fraction": 0.98, "loaded_fraction": 0.7}
    a = {"cop_legs": {"published": [{"recording": "AB01/i0", "leg": "right", "strides": 3, "cop_metrics": m}],
                      "held": [{"recording": "AB01/i10", "leg": "left", "strides": 2, "cop_reasons": ["toe-off 0 percent"], "cop_metrics": m}],
                      "pending_by_ruling_recordings": ["AB01/i10"], "label": "estimated plate position"},
         "plane_glitch_rule": {"legs": [{"recording": "AB08/i0", "leg": "left", "frames_over_60_deg": 36, "finite_plane_frames": 100,
                                         "max_plane_deviation_deg": 102.9}],
                               "strides_held": [{"recording": "AB08/i0", "leg": "left"}]}}
    rows = r01.cop_leg_rows(a)
    assert [(r["recording"], r["status"], r["pending_by_ruling"], r["label"]) for r in rows] == [
        ("AB01/i0", "published", False, "estimated plate position"), ("AB01/i10", "held", True, "")]
    assert set(rows[0]) == set(r01.COP_FIELDS)
    g = r01.glitch_leg_rows(a)
    assert g[0]["strides_held"] == 1 and set(g[0]) == set(r01.GLITCH_FIELDS)


def test_limitation_texts_exist_for_every_flag_the_assessment_can_emit():
    from contributor_tools import run_um21_q01v3_assessment as q
    emitted = {"moments_powers_from_v2", "knee_marker_labels_swapped", "cop_estimated_plate_position", "cop_held_leg",
               "cop_held_pending_ruling", "powers_held_sign_unsettled", "angle_columns_missing_in_stride", "plane_glitch_hold"}
    assert emitted == set(r01.LIMITATION_TEXT) == set(r01.LIMITATION_TITLES)
    assert q.PENDING_BY_RULING == {"AB01/i10", "AB02/i10", "AB03/i10", "AB04/d10", "AB10/d5"}


def test_stage_paths_and_spec_never_reuse_an_existing_root():
    assert r01.stage_paths("pilot")["output_root"] != r01.stage_paths("full")["output_root"]
    assert r01.recording_id("AB07/i10") == "um21:Streaming/AB07/Tread/i10"
