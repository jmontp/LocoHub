"""UM21-Q01 v3 assessment tests. Every array here is a SYNTHETIC fixture with an independently known answer."""
import numpy as np
import pytest

from contributor_tools import run_um21_q01_assessment as old
from contributor_tools import run_um21_q01v3_assessment as q

OID = "um21:Streaming/AB01/Tread/i0:right:frames:100:277"
N = 150


def meta(oid=OID, side="right"):
    return {"observation_id": oid, "reference_side": side, "observation_type": "individual_cycle", "subject": "UM21_AB01",
            "source_recording_id": "um21:Streaming/AB01/Tread/i0", "task": "level_walking", "task_id": "s1",
            "phase": list(range(N))}


def clean_arrays():
    t = np.linspace(0, 2 * np.pi, N)
    a = {c: np.zeros(N) for c in q.DATA_COLUMNS}
    a["hip_flexion_angle_ipsi_rad"] = np.radians(20 * np.sin(t))
    a["knee_flexion_angle_ipsi_rad"] = np.radians(30 + 25 * np.sin(t))
    a["ankle_dorsiflexion_angle_ipsi_rad"] = np.radians(8 * np.sin(t))
    a["cop_anterior_ipsi_m"] = np.linspace(-0.05, 0.15, N)
    a["cop_vertical_ipsi_m"] = np.full(N, 0.01)
    a["cop_lateral_ipsi_m"] = np.full(N, 0.02)
    return a


def run(arrays=None, held=None, jumps=None, glitch=False, cop="published", pending=False, m=None):
    return q.assess_observation(m or meta(), arrays or clean_arrays(), held or {}, jumps or {}, glitch, None, cop, pending)


def test_limits_equal_the_earlier_ported_values():
    assert q.L1_BOUNDS_DEG["hip_flexion_angle_ipsi_rad"] == old.L1_BOUNDS_DEG["hip_angle"]
    assert q.L1_BOUNDS_DEG["knee_flexion_angle_ipsi_rad"] == old.L1_BOUNDS_DEG["knee_angle"]
    assert q.L1_BOUNDS_DEG["ankle_dorsiflexion_angle_ipsi_rad"] == old.L1_BOUNDS_DEG["ankle_angle"]
    assert q.L2_JUMP_DEG == old.L2_JUMP_DEG and q.L3_RANGE_S == old.L3_RANGE_S
    assert q.L5_BOUNDS_M == {"cop_anterior_ipsi_m": (-0.5, 0.5), "cop_vertical_ipsi_m": (-0.3, 0.3), "cop_lateral_ipsi_m": (-0.3, 0.3)}


def test_plane_deviation_known_angles():
    fwd = np.array([1.0, 0.0, 0.0])
    ang = np.radians([0.0, 30.0, 60.0, 90.0, 180.0])
    pf = np.stack([np.cos(ang), np.sin(ang), np.zeros(5)], axis=1)
    np.testing.assert_allclose(q.plane_deviation_deg(pf, fwd), [0, 30, 60, 90, 180], atol=1e-6)
    pf[2] = np.nan
    assert np.isnan(q.plane_deviation_deg(pf, fwd)[2])


def test_glitch_mask_is_strictly_above_sixty_degrees_and_ignores_nan():
    m = q.glitch_mask(np.array([0.0, 59.9, 60.0, 60.1, 100.0, np.nan]))
    assert m.tolist() == [False, False, False, True, True, False]


def test_window_uses_one_based_inclusive_frames():
    mask = np.zeros(20, bool)
    mask[4] = True                      # 0-based frame 4 is frame 5
    assert q.window_has_glitch(mask, 5, 8) and q.window_has_glitch(mask, 1, 5)
    assert not q.window_has_glitch(mask, 6, 9) and not q.window_has_glitch(mask, 1, 4)


def test_frame_jump_flags_known_step_and_glitch_exclusion():
    x = np.radians(np.array([0, 1, 2, 40, 41, 42, 43, 44.0]))
    no_glitch = np.zeros(8, bool)
    assert np.flatnonzero(q.frame_jump_flags(x, no_glitch)).tolist() == [3]       # 38 degree step into frame 3
    g = no_glitch.copy()
    g[3] = True                                                                    # the frame after the step is a glitch frame
    assert not q.frame_jump_flags(x, g).any()
    y = x.copy()
    y[3] = np.nan                                                                  # no pair with a missing frame
    assert not q.frame_jump_flags(y, no_glitch).any()
    assert not q.frame_jump_flags(np.radians(np.array([0, 30.0])), np.zeros(2, bool)).any()   # exactly 30 does not fail


def test_stride_jump_pairs_only_inside_the_window():
    flags = np.zeros(30, bool)
    flags[[3, 10, 11, 25]] = True
    # window frames 5..12 (1-based) = 0-based 4..11; pairs (f-1, f) with f in 5..11
    assert q.stride_jump_pairs(flags, 5, 12) == [10, 11]
    assert q.stride_jump_pairs(flags, 4, 5) == [] and q.stride_jump_pairs(flags, 3, 4) == [3]


def test_clean_observation_has_no_failure_and_unchecked_columns_stay_unchecked():
    e, f = run()
    assert e["status"] == "no_failure_found" and not f and e["failed_limits"] == []
    st = {c: s for s, cols in e["channel_states"].items() for c in cols}
    assert st["hip_flexion_angle_ipsi_rad"] == "pass" and st["cop_anterior_ipsi_m"] == "pass"
    assert st["hip_flexion_moment_ipsi_Nm_kg"] == "unchecked" or st["hip_flexion_moment_ipsi_Nm_kg"] == "unchecked_all_missing"
    assert "moments_powers_from_v2" in e["limitations"] and "cop_estimated_plate_position" in e["limitations"]


def test_l1_fires_in_degrees_not_radians():
    a = clean_arrays()
    a["knee_flexion_angle_ipsi_rad"][10] = np.radians(170.0)       # above 165
    e, f = run(a)
    assert e["status"] == "failed" and e["failed_limits"] == ["L1"] and f[0]["sample_index"] == 10
    assert f[0]["value"] == pytest.approx(170.0)
    a2 = clean_arrays()
    a2["knee_flexion_angle_ipsi_rad"][10] = 2.5                       # 2.5 rad = 143 deg: inside, would fail if read as degrees
    assert run(a2)[0]["status"] == "no_failure_found"


def test_l5_pressure_point_bounds():
    a = clean_arrays()
    a["cop_anterior_ipsi_m"][5] = 0.51
    e, f = run(a)
    assert e["failed_limits"] == ["L5"] and f[0]["channel"] == "cop_anterior_ipsi_m"
    a = clean_arrays()
    a["cop_vertical_ipsi_m"][5] = -0.31
    assert run(a)[0]["failed_limits"] == ["L5"]
    a = clean_arrays()
    a["cop_lateral_ipsi_m"][5] = 0.3                                   # exactly at the bound passes
    assert run(a)[0]["status"] == "no_failure_found"


def test_l2_comes_from_frame_jumps_and_maps_to_the_observation_not_to_the_150_samples():
    a = clean_arrays()
    a["thigh_sagittal_angle_ipsi_rad"] = np.radians(60 * np.sin(np.linspace(0, 2 * np.pi, N)))
    # a 90 degree step between adjacent published samples would be a phase-grid L2 failure; it is NOT used any more
    a["foot_sagittal_angle_ipsi_rad"] = np.radians(np.where(np.arange(N) < 75, 0.0, 90.0))
    assert run(a)[0]["status"] == "no_failure_found"
    e, f = run(a, jumps={"foot_sagittal_angle_ipsi_rad": [120, 121]})
    assert e["status"] == "failed" and e["failed_limits"] == ["L2"]
    assert [x["frame"] for x in f] == [120, 121] and e["failed_samples"]["foot_sagittal_angle_ipsi_rad"] == {"L2": 2}


def test_missing_and_held_columns_are_never_a_pass():
    a = clean_arrays()
    a["hip_flexion_angle_ipsi_rad"][:] = np.nan
    a["hip_flexion_power_ipsi_W_kg"][:] = np.nan
    e, _ = run(a, held={"hip_flexion_power_ipsi_W_kg": "held: sign unsettled"},
               jumps={"hip_flexion_angle_ipsi_rad": [5]})
    st = {c: s for s, cols in e["channel_states"].items() for c in cols}
    assert st["hip_flexion_angle_ipsi_rad"] == "unchecked_all_missing" and st["hip_flexion_power_ipsi_W_kg"] == "unchecked_all_missing"
    assert e["status"] == "no_failure_found"                         # a jump on an all-missing series is not evaluated
    assert "powers_held_sign_unsettled" in e["limitations"] and "angle_columns_missing_in_stride" in e["limitations"]
    assert e["attributes"]["missing_samples"]["hip_flexion_angle_ipsi_rad"]["missing"] == N


def test_plane_hold_sets_leg_columns_missing_keeps_pelvis_and_moments_and_names_them():
    a = clean_arrays()
    a["pelvis_sagittal_angle_rad"][:] = 0.1
    a["hip_flexion_moment_ipsi_Nm_kg"][:] = 0.5
    held = {}
    q.apply_plane_hold(a, held)
    assert set(held) == set(q.LEG_PLANE_COLUMNS)
    assert all(np.isnan(a[c]).all() for c in q.LEG_PLANE_COLUMNS)
    assert np.all(a["pelvis_sagittal_angle_rad"] == 0.1) and np.all(a["hip_flexion_moment_ipsi_Nm_kg"] == 0.5)
    e, _ = run(a, held=held, glitch=True, cop="held")
    assert "plane_glitch_hold" in e["limitations"] and e["status"] == "no_failure_found"
    assert all(v.endswith("(rule P1)") for v in e["held_signals"].values())


def test_cop_leg_held_is_a_limitation_and_pending_ruling_is_flagged():
    a = clean_arrays()
    for c in q.COP_COLUMNS:
        a[c][:] = np.nan
    held = {c: q.COP_REASON_PREFIX + "toe-off end within 4 cm in 0 percent of strides (needs 95)" for c in q.COP_COLUMNS}
    e, _ = run(a, held=held, cop="held", pending=True)
    assert {"cop_held_leg", "cop_held_pending_ruling"} <= set(e["limitations"])
    assert "cop_estimated_plate_position" not in e["limitations"] and e["attributes"]["cop_status"] == "held"
    e2, _ = run(a, held=held, cop="held", pending=False)
    assert "cop_held_pending_ruling" not in e2["limitations"]


def test_structural_problems_fail_and_are_named():
    e, _ = run(m=meta(side="left"))
    assert e["status"] == "failed" and e["failed_limits"] == ["structural"]
    bad = meta()
    bad["phase"] = list(range(149)) + [150]
    assert run(m=bad)[0]["failed_limits"] == ["structural"]
    assert run(m=meta(oid="not an id"))[0]["failed_limits"] == ["structural"]


def test_unknown_unit_suffix_refuses():
    a = clean_arrays()
    a["mystery_column"] = np.zeros(N)
    with pytest.raises(q.UnitError):
        run(a)
    with pytest.raises(q.UnitError):
        q.unit_of("something_deg")
    assert q.unit_of("hip_flexion_angle_ipsi_rad") == "rad" and q.unit_of("cop_anterior_ipsi_m") == "m"


def test_stride_time_is_reported_not_filtered():
    e, _ = run(m=meta(oid="um21:Streaming/AB01/Tread/i0:right:frames:100:400"))
    assert e["attributes"]["stride_time_s"] == 3.0 and e["attributes"]["L3_stride_time_outside_range_reported_only"] is True
    assert e["status"] == "no_failure_found"


def test_leg_cop_verdicts_read_the_summary_shape():
    rec = {"legs": {"right": {"strides": 3, "cop_gate": {"verdict": "pass", "reasons": []},
                              "plate": {"ankle_holdout": {"r": 0.99}, "endpoint_check_0p2bw": {"fraction_within_4cm_toe": 1.0},
                                        "plate_assignment": {"same_plate_loaded_within_5_frames_fraction": 0.98}, "loaded_fraction": 0.7}},
                    "left": {"strides": 3, "cop_gate": {"verdict": "held", "reasons": ["toe-off end within 4 cm in 0 percent of strides (needs 95)"]},
                             "plate": {}}}}
    out = {leg: (v, why, met) for leg, v, why, met in q.leg_cop_verdicts(rec)}
    assert out["right"][0] == "pass" and out["right"][2]["holdout_r"] == 0.99
    assert out["left"][0] == "held" and "toe-off" in out["left"][1][0] and out["left"][2]["holdout_r"] is None


def test_component_and_part_roundtrip_with_synthetic_files(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    oid2 = "um21:Streaming/AB01/Tread/i0:right:frames:277:454"
    ids = [OID] * N + [oid2] * N
    cols = {"observation_id": ids, "reference_side": ["right"] * (2 * N), "sample": list(range(N)) * 2}
    for c in q.S02_TO_PUBLISHED:
        cols[c] = [float(i) for i in range(2 * N)]
    path = tmp_path / "s02.parquet"
    pq.write_table(pa.table(cols), str(path))
    got = q.read_component(path, q.sha256_file(path))
    assert list(got) == [OID, oid2] and got[oid2]["hip_angle"][0] == float(N)
    with pytest.raises(ValueError):
        q.read_component(path, "0" * 64)
    cols["sample"] = list(range(N - 1)) + [200] + list(range(N))
    pq.write_table(pa.table(cols), str(tmp_path / "bad.parquet"))
    with pytest.raises(ValueError):
        q.read_component(tmp_path / "bad.parquet", q.sha256_file(tmp_path / "bad.parquet"))
    a = clean_arrays()
    meta_v2 = {**{k: "x" for k in q.IDENTITY_STR}, "held_signals": "{}"}
    p2 = tmp_path / "part.parquet"
    q.write_part(p2, [(meta_v2, (1.0, 2.0), np.linspace(0, 100, N), a, {"cop_anterior_ipsi_m": "r"})])
    t = pq.read_table(p2)
    assert t.num_rows == N and t.schema.equals(q.part_schema())
    assert t.column("held_signals")[0].as_py() == '{"cop_anterior_ipsi_m": "r"}'
    assert t.column("source_end_time_s")[7].as_py() == 2.0
