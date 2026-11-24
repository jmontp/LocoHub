"""Synthetic tests for contributor_tools/run_gt23_q01_assessment.py (all data below are made up)."""
import numpy as np
import pytest

from contributor_tools import run_gt23_q01_assessment as q
from contributor_tools import run_um21_q01_assessment as um


def _cols(**kw):
    return list(kw)


def _obs(kind="phase"):
    cols = ["hip_flexion_angle_ipsi_rad", "knee_flexion_angle_ipsi_rad", "cop_vertical_ipsi_m", "hip_flexion_moment_ipsi_Nm_kg",
            "ankle_dorsiflexion_angle_ipsi_rad"]
    lim = {c: q.column_limits(c) for c in cols}
    return q.Observation(("AB01/x_1/left/0000001", "left"), kind, cols, lim), cols


def _data(n, **over):
    d = {"hip_flexion_angle_ipsi_rad": np.zeros(n), "knee_flexion_angle_ipsi_rad": np.zeros(n),
         "cop_vertical_ipsi_m": np.zeros(n), "hip_flexion_moment_ipsi_Nm_kg": np.ones(n),
         "ankle_dorsiflexion_angle_ipsi_rad": np.zeros(n), "source_start_time_s": np.zeros(n),
         "source_end_time_s": np.ones(n), "phase_ipsi": np.linspace(0, 100, n), "time_s": np.arange(n) * 0.005}
    d.update(over)
    return d


def test_limits_match_um21():
    assert q.L1_BOUNDS_DEG["hip_flexion_angle_"] == um.L1_BOUNDS_DEG["hip_angle"]
    assert q.L1_BOUNDS_DEG["knee_flexion_angle_"] == um.L1_BOUNDS_DEG["knee_angle"]
    assert q.L1_BOUNDS_DEG["ankle_dorsiflexion_angle_"] == um.L1_BOUNDS_DEG["ankle_angle"]
    assert q.L2_JUMP_DEG == um.L2_JUMP_DEG and q.L3_RANGE_S == um.L3_RANGE_S


def test_units_from_suffix_and_refusal():
    assert q.unit_of("hip_flexion_angle_ipsi_rad") == "rad"
    assert q.unit_of("hip_flexion_velocity_left_rad_s") == "rad/s"
    assert q.unit_of("grf_vertical_ipsi_BW") == "BW"
    assert q.unit_of("subtalar_angle_power_ipsi_W_kg") == "W/kg"
    with pytest.raises(q.UnitError):
        q.unit_of("hip_flexion_angle_ipsi_deg")
    with pytest.raises(q.UnitError):
        q.check_unit_evidence("angles in degrees")


def test_l1_uses_degrees_not_radians():
    obs, _ = _obs()
    hip = np.zeros(10); hip[3] = np.radians(160.0); hip[7] = np.radians(100.0)  # 160 deg fails, 100 deg passes
    obs.feed(_data(10, hip_flexion_angle_ipsi_rad=hip), {}, 0, 10)
    f = obs.cols["hip_flexion_angle_ipsi_rad"].fails
    assert [(x["limit"], x["sample_index"]) for x in f if x["limit"] == "L1"] == [("L1", 3)]
    assert abs(f[0]["value"] - 160.0) < 1e-9


def test_l2_jump_and_chunk_independence():
    knee = np.zeros(10); knee[5:] = np.radians(40.0)  # 40 deg step between samples 4 and 5
    one, _ = _obs()
    one.feed(_data(10, knee_flexion_angle_ipsi_rad=knee), {}, 0, 10)
    two, _ = _obs()
    d = _data(10, knee_flexion_angle_ipsi_rad=knee)
    two.feed(d, {}, 0, 5)
    two.feed(d, {}, 5, 10)  # data arrays re-sliced: the pair spans the chunk boundary
    for o in (one, two):
        fl = [x for x in o.cols["knee_flexion_angle_ipsi_rad"].fails if x["limit"] == "L2"]
        assert [x["sample_index"] for x in fl] == [5]
        assert abs(fl[0]["value"] - 40.0) < 1e-9


def test_l2_not_across_missing_and_missing_is_reported():
    knee = np.zeros(10); knee[4] = np.nan; knee[6:] = np.radians(50.0)
    o, _ = _obs()
    o.feed(_data(10, knee_flexion_angle_ipsi_rad=knee), {}, 0, 10)
    s = o.cols["knee_flexion_angle_ipsi_rad"]
    assert [x["sample_index"] for x in s.fails if x["limit"] == "L2"] == [6]
    assert s.missing == [[4, 4]] and s.n_finite == 9


def test_l5_pressure_point_blatant():
    cv = np.full(10, -0.06); cv[2:5] = -0.6  # the old stairs error
    o, _ = _obs()
    o.feed(_data(10, cop_vertical_ipsi_m=cv), {}, 0, 10)
    assert [x["sample_index"] for x in o.cols["cop_vertical_ipsi_m"].fails] == [2, 3, 4]


def test_side_check_and_flight():
    force = np.zeros(150); force[:80] = 600.0  # stance first: pass
    assert q.side_check(force)[0] == "pass"
    assert q.side_check(np.roll(force, 75))[0] == "fail"  # opposite leg stance: swapped side
    assert q.side_check(np.full(150, np.nan))[0] == "unchecked_no_ipsilateral_force"
    ip = np.zeros(150); ip[:60] = 500.0
    co = np.zeros(150); co[75:] = 500.0
    share, longest = q.flight_stats(ip, co)
    assert longest == 15 and abs(share - 0.1) < 1e-12


def test_parse_ids():
    assert q.parse_id("AB05/ball_toss_1/both/0002710", "phase")["start"] == 2710
    assert q.parse_id("AB01/ball_toss_1/continuous", "time")["side"] == "continuous"
    assert q.parse_id("AB01/ball_toss_1/continuous", "phase") is None


def test_held_state_and_overall():
    o, cols = _obs()
    o.rows = 0
    nan = np.full(150, np.nan)
    hip = np.zeros(150); hip[10] = np.radians(170.0)
    o.feed(_data(150, hip_flexion_angle_ipsi_rad=hip, hip_flexion_moment_ipsi_Nm_kg=nan),
           {"subject": "AB01", "source_recording_id": "AB01/x_1", "observation_type": "individual_cycle", "task": "level_walking",
            "task_id": "level_1-2", "task_info": "{}", "subject_metadata": "{}",
            "held_signals": '{"hip_flexion_moment_ipsi_Nm_kg": "why"}'}, 0, 150)
    lin = {("phase", "AB01/x_1/left/0000001", "left"): {"rows": 150, "source_start_time_s": 0.0, "source_end_time_s": 1.0,
                                                           "task": "level_walking", "task_id": "level_1-2",
                                                           "observation_type": "individual_cycle", "start_index": 1}}
    e, fails = q.finish_observation(o, lin, "AB01", {"AB01/x_1": (0.0, 5.0)})
    st = e["plausibility"]["channel_states"]
    assert st["not_checked_no_column"] == ["hip_flexion_moment_ipsi_Nm_kg"]
    assert "hip_flexion_angle_ipsi_rad" in st["fail"]
    assert e["overall"] == "failed" and e["structural"]["state"] == "pass"
    assert any(f["limit"] == "L1" and f["sample_index"] == 10 for f in fails)


def test_read_table_streams_across_batches(tmp_path, monkeypatch):
    pa = pytest.importorskip("pyarrow")
    import pyarrow.parquet as pq
    monkeypatch.setattr(q, "READ_BATCH_ROWS", 100)  # observations of 150 rows straddle batches
    rows, lineage = [], {}
    for k, (side, bad) in enumerate((("left", False), ("right", True), ("left", False))):
        oid = f"AB01/x_1/left/{k:07d}"
        oid = f"AB01/x_1/{side}/{k:07d}"
        hip = np.zeros(150)
        if bad:
            hip[40] = np.radians(200.0)
        info = '{"mass_note_key":"cannot_be_told","limits":[]}'
        for i in range(150):
            rows.append({"subject": "AB01", "source_recording_id": "AB01/x_1", "observation_id": oid, "reference_side": side,
                         "observation_type": "individual_cycle", "task": "level_walking", "task_id": "level_1-2",
                         "task_info": info, "subject_metadata": "{}", "held_signals": "{}", "phase_ipsi": i * 100.0 / 149,
                         "source_start_time_s": 1.0, "source_end_time_s": 2.0, "hip_flexion_angle_ipsi_rad": hip[i]})
        lineage[("phase", oid, side)] = {"rows": 150, "source_start_time_s": 1.0, "source_end_time_s": 2.0,
                                          "task": "level_walking", "task_id": "level_1-2",
                                          "observation_type": "individual_cycle", "start_index": k}
    cols = {c: [r[c] for r in rows] for c in rows[0]}
    pq.write_table(pa.table(cols), tmp_path / "phase.parquet", row_group_size=70)
    got = []
    counts, _, units, ids, rep = q.read_table(tmp_path / "phase.parquet", "phase", "AB01", lineage,
                                              {"AB01/x_1": (0.0, 5.0)}, lambda e, f: got.append((e, f)))
    assert counts == {"rows": 450, "observations": 3} and rep == [] and units["hip_flexion_angle_ipsi_rad"] == "rad"
    assert [e["overall"] for e, _ in got] == ["no_failure_found", "failed", "no_failure_found"]
    assert [(f["limit"], f["sample_index"]) for f in got[1][1]] == [("L1", 40), ("L2", 40), ("L2", 41)]
