"""UM21-T05 time-export tests. EVERY fixture here is SYNTHETIC (built by construction); nothing reads UMich data and nothing
here regenerates or validates the scientific dataset. Written without being run (the launcher was busy); run later with
the usual single-worker pytest line before the pilot."""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools import um21_time_export as tx  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


s02t = _load("test_um21_s02_frame_for_t05", ROOT / "tests/test_um21_s02_frame.py")   # reuse its SYNTHETIC trial builder
s02 = s02t.s02
RAD = np.radians


# ------------------------------------------------------------------ names, ids, small rules
def test_column_list_and_phase_names():
    cols = tx.time_columns()
    assert len(cols) == len(set(cols)) == 2 + 2 * 21
    assert cols[:2] == [tx.PELVIS, tx.PELVIS_VEL]
    assert tx.phase_name("thigh_sagittal_angle_left_rad", "left") == "thigh_sagittal_angle_ipsi_rad"
    assert tx.phase_name("hip_flexion_power_right_W_kg", "right") == "hip_flexion_power_ipsi_W_kg"
    assert tx.phase_name(tx.PELVIS, "left") == tx.PELVIS
    with pytest.raises(KeyError):
        tx.phase_name("thigh_sagittal_angle_left_rad", "right")


def test_ids_and_batches():
    assert tx.time_observation_id("AB03/i10", 8123) == "um21:Streaming/AB03/Tread/i10:continuous:frames:1:8123"
    assert tx.parse_id("um21:Streaming/AB03/Tread/i10:left:frames:101:201") == {"recording": "AB03/i10", "side": "left", "a": 101, "b": 201}
    recs = [f"AB{s:02d}/{c}" for s in range(1, 11) for c in ("d10", "d5", "i0", "i5", "i10")][:44]
    b = tx.batches(recs)
    assert [len(x) for x in b] == [5] * 8 + [4]
    assert sorted(sum(b, [])) == sorted(recs)


def test_pelvis_sign_and_exception():
    assert tx.pelvis_sign("AB01/i0") == -1.0 and tx.pelvis_sign("AB04/i0") == 1.0
    assert tx.signed_pelvis(np.array([10.0]), "AB01/i0")[0] == pytest.approx(-RAD(10.0))
    assert tx.signed_pelvis(np.array([10.0]), "AB04/i0")[0] == pytest.approx(RAD(10.0))


def test_velocity_is_gradient_with_neighbour_nan_and_known_slope():
    t = np.arange(10) / 100.0
    assert np.allclose(tx.velocity(2.0 * t), 2.0)           # ends are one-sided and exact for a line
    x = 2.0 * t
    x[4] = np.nan
    v = tx.velocity(x)
    assert np.isnan(v[[3, 4, 5]]).all() and np.isfinite(v[[0, 1, 2, 6, 7, 8, 9]]).all()


def test_power_missing_where_either_factor_missing():
    p = tx.power(np.array([1.0, np.nan, 2.0]), np.array([3.0, 4.0, np.nan]))
    assert p[0] == 3.0 and np.isnan(p[1:]).all()


def test_window_mask_and_holds_from_phase_entries():
    assert tx.window_mask(10, [(2, 4)]).tolist() == [False, True, True, True] + [False] * 6
    entries = [{"observation_id": "um21:Streaming/AB01/Tread/i0:left:frames:10:20",
                "held_signals": {"pelvis_sagittal_angle_rad": "x", "hip_flexion_angle_ipsi_rad": "x", "cop_anterior_ipsi_m": "y",
                             "knee_flexion_moment_ipsi_Nm_kg": "z"}},
               {"observation_id": "um21:Streaming/AB01/Tread/i0:right:frames:30:40", "held_signals": {"pelvis_sagittal_angle_rad": "x"}}]
    h = tx.holds_from_phase_entries(entries)
    assert h[tx.PELVIS] == [(10, 20), (30, 40)]
    assert h["hip_flexion_angle_left_rad"] == [(10, 20)] and h["knee_flexion_moment_left_Nm_kg"] == [(10, 20)]
    assert "cop_anterior_left_m" not in h and len(h) == 3


def test_merge_task_info_keeps_only_constant_keys():
    merged, dropped = tx.merge_task_info(['{"treadmill":true,"speed":1.0,"k":1}', '{"treadmill":true,"speed":1.0,"k":2}'])
    assert merged == {"treadmill": True, "speed": 1.0} and dropped == ["k"]
    assert tx.merge_task_info([]) == ({}, [])


def test_registration_from_summary_lateral_none_becomes_zero_like_s02():
    leg = {"plate": {"axis": 1, "sign": -1, "tilt_used_deg": 5.0, "fit": {"forward_m": 0.1, "up_m": 0.02, "lateral_m": None},
                     "plate_assignment": {"same_plate_loaded_within_5_frames_fraction": 0.98}},
           "cop_gate": {"verdict": "pass", "reasons": []}}
    r = tx.registration_from_summary(leg)
    assert r["shift"] == (0.1, 0.02, 0.0) and r["axis"] == 1 and r["sign"] == -1 and r["tilt_deg"] == 5.0
    assert tx.force_hold_reason(r, 70.0, "AB01/i0") is None and tx.cop_hold_reason(r, "AB01/i0") is None
    assert tx.registration_from_summary(None)["shift"] is None


def test_hold_reasons():
    ok = {"axis": 1, "sign": 1, "tilt_deg": 0.0, "shift": (0, 0, 0), "cop_verdict": "pass", "assignment_same_plate": 0.99}
    assert tx.force_hold_reason(ok, 70.0, "AB01/i10") == tx.REASON_FORCE_PENDING
    assert tx.force_hold_reason(ok, None, "AB01/i0") == tx.REASON_FORCE_NO_MASS
    assert tx.force_hold_reason({**ok, "assignment_same_plate": 0.9}, 70.0, "AB01/i0") == tx.REASON_FORCE_ASSIGN
    assert tx.force_hold_reason({**ok, "axis": None}, 70.0, "AB01/i0") == tx.REASON_FORCE_NO_REG
    assert tx.cop_hold_reason(ok, "AB10/d5").startswith(tx.REASON_COP_PREFIX)
    assert tx.cop_hold_reason({**ok, "cop_verdict": "held", "cop_reasons": ["r = 0.2"]}, "AB01/i0").endswith("r = 0.2")


# ------------------------------------------------------------------ force: BW, zero off the plate, missing when not finite
def test_grf_bw_known_values_zero_off_plate_and_nonfinite_missing():
    mass = 80.0
    bw = mass * 9.81
    # plate (N): x side-to-side, y long axis, z ground-normal (negative while loaded). axis 1, sign +1, no tilt.
    f = np.array([[0.0, 10.0, 0.0, np.nan],        # f0 (side)
                  [0.0, -100.0, 0.0, 0.0],         # f1 (long axis; ground force on person forward = -sign*f1 = +100 N)
                  [0.0, -bw, -5.0, 0.0]])          # f2; sample 2 carries only 5 N (below 20 N): foot off the plate
    out, loaded = tx.grf_bw(f, {"axis": 1, "sign": 1, "tilt_deg": 0.0}, mass, "right", s02)
    assert loaded.tolist() == [False, True, False, False]
    assert np.allclose(out[:, 1], [1.0, 100.0 / bw, -10.0 / bw])     # vertical, anterior, lateral (right leg: +right = -sign*f0)
    assert np.allclose(out[:, 0], 0.0) and np.allclose(out[:, 2], 0.0)   # finite and unloaded: 0 BW, not missing
    assert np.isnan(out[:, 3]).all()                                    # not finite: missing, never 0
    left, _ = tx.grf_bw(f, {"axis": 1, "sign": 1, "tilt_deg": 0.0}, mass, "left", s02)
    assert left[2, 1] == pytest.approx(+10.0 / bw)                       # outward is mirrored for the left leg


def test_grf_bw_belt_tilt_rotates_into_gravity_frame():
    bw = 70.0 * 9.81
    f = np.array([[0.0], [0.0], [-bw]])
    tilt = 10.0
    out, _ = tx.grf_bw(f, {"axis": 1, "sign": 1, "tilt_deg": tilt}, 70.0, "right", s02)
    # the plate normal is tilted by 10 degrees: the force on the person has the same magnitude, split into up and forward
    assert np.hypot(out[0, 0], out[1, 0]) == pytest.approx(1.0)
    assert out[0, 0] == pytest.approx(np.cos(RAD(tilt)))
    assert abs(out[1, 0]) == pytest.approx(np.sin(RAD(tilt)))


# ------------------------------------------------------------------ L2 and the time assessment entry
def test_l2_jumps_between_finite_samples_only():
    x = np.zeros(10)
    x[5:] = RAD(40.0)
    assert tx.l2_jumps(x) == [5]
    x[5] = np.nan                                       # a held (NaN) sample: no jump is counted across it
    assert tx.l2_jumps(x) == []
    assert tx.l2_jumps(np.array([0.0])) == []


def test_build_time_entry_status_states_and_failure_rows():
    n = 200
    t = np.arange(n) / 100.0
    cols = {c: np.zeros(n) for c in tx.time_columns()}
    cols["knee_flexion_angle_left_rad"][100:] = RAD(45.0)    # a 45 degree step: L2 failure
    held = {"cop_anterior_right_m": "held"}
    cols["cop_anterior_right_m"] = np.full(n, np.nan)
    meta = {"observation_id": tx.time_observation_id("AB01/i0", n), "subject": "UM21_AB01", "source_recording_id": "um21:Streaming/AB01/Tread/i0",
            "task": "level_walking", "task_id": "level"}
    e, fails = tx.build_time_entry(meta, t, cols, held, ["time_table_source_rate"])
    assert e["status"] == "failed" and e["failed_limits"] == ["L2"] and e["table"] == "time" and e["reference_side"] == "none"
    assert e["failed_channels"] == ["knee_flexion_angle_left_rad"] and e["failed_samples"] == {"knee_flexion_angle_left_rad": {"L2": 1}}
    assert fails[0]["sample_index"] == 100 and fails[0]["time_s"] == pytest.approx(1.0) and fails[0]["value"] == pytest.approx(45.0)
    states = {c: s for s, cs in e["channel_states"].items() for c in cs}
    assert states["cop_anterior_right_m"] == "unchecked_all_missing"       # missing is never a pass
    assert states["grf_vertical_left_BW"] == "unchecked"                   # no limit applies to force on the time table
    assert states["thigh_sagittal_angle_left_rad"] == "pass_jump_only"
    for key in ("observation_id", "reference_side", "table", "observation_type", "subject", "source_recording_id", "task", "task_id",
                "rows", "status", "failed_limits", "failed_channels", "failed_samples", "limitations", "flight", "attributes",
                "held_signals", "channel_states"):
        assert key in e                                                   # what the shared builder requires
    ok, none = tx.build_time_entry(meta, t, {c: np.zeros(n) for c in tx.time_columns()}, {}, [])
    assert ok["status"] == "no_failure_found" and not none


# ------------------------------------------------------------------ readback rules on known values
def test_resample_window_reproduces_a_ramp_exactly_and_nan_propagates():
    x = np.arange(1000, dtype=float) * 0.01              # frame f (1-based) has value (f - 1) * 0.01
    y = tx.resample_window(x, 101, 201)
    assert y[0] == pytest.approx(1.00) and y[-1] == pytest.approx(2.00) and np.allclose(np.diff(y), 1.0 / 149)
    x[150] = np.nan
    assert np.isnan(tx.resample_window(x, 101, 201)).any()


def test_compare_series_tolerances():
    ph = np.linspace(0.0, 1.0, 150)
    assert tx.compare_series("angle", ph, ph + 5e-10)["pass"]
    assert not tx.compare_series("angle", ph, ph + 5e-9)["pass"]
    assert tx.compare_series("pelvis_hip", ph, ph + 5e-7)["pass"]
    assert tx.compare_series("moment", ph, ph + 2e-9)["pass"] is False
    t = ph.copy(); t[10] = np.nan                         # finiteness differences are counted, not gated
    c = tx.compare_series("angle", ph, t)
    assert c["pass"] and c["only_phase_finite"] == 1
    v = np.sin(np.linspace(0, 6, 150))
    assert tx.compare_series("velocity", v, v * 1.01)["pass"] and not tx.compare_series("velocity", v, v * 1.2)["pass"]
    c = tx.compare_series("cop", ph, ph + 0.0005)
    assert c["pass"] is None and c["n_both"] == 150
    assert tx.leg_cop_verdict(c["abs_values_pooled"], 150, 0, 0)["pass"]
    assert not tx.leg_cop_verdict(np.full(150, 0.01), 150, 0, 0)["pass"]
    assert not tx.leg_cop_verdict(np.full(100, 0.0001), 100, 10, 10)["pass"]      # 17 percent of samples finite in only one table


# ------------------------------------------------------------------ whole recording on a synthetic trial
class A:
    def __init__(self, a):
        self.a, self.shape, self.ndim = np.asarray(a), np.asarray(a).shape, np.asarray(a).ndim

    def __getitem__(self, k):
        return self.a


def trial_with_vicon(trial, n=1200):
    """The S02 synthetic trial plus synthetic Vicon pelvis tilt (raw +10 degrees = published -10 deg, the marker pelvis tilt)
    and constant synthetic moments."""
    z = np.zeros((3, n))
    pel = z.copy(); pel[0] = 10.0
    mom = {f"{s}{j}Moment": A(np.vstack([np.full(n, 0.5), np.zeros(n), np.zeros(n)])) for s in "RL" for j in ("Hip", "Knee", "Ankle")}
    trial = dict(trial)
    trial["jointAngles"] = {"RPelvisAngles": A(pel), "LPelvisAngles": A(pel)}
    trial["jointMoments"] = mom
    return trial


def registrations(summary, **over):
    regs = {leg: tx.registration_from_summary(summary["legs"][leg]) for leg in ("right", "left")}
    for leg in regs:
        regs[leg].update({"cop_verdict": "pass", "assignment_same_plate": 1.0})   # the synthetic gate verdicts are not the point here
    for leg, d in over.items():
        regs[leg].update(d)
    return regs


@pytest.fixture(scope="module")
def synthetic_world():
    trial, v2, truth, mass = s02t.synthetic_trial()
    ids, sides, arrays, unheld, summary, ledger = s02.process_recording(trial, "AB99/i0", v2, mass, 0.0)
    return trial_with_vicon(trial), truth, mass, ids, arrays, unheld, summary


def test_whole_recording_clock_columns_and_known_angles(synthetic_world):
    trial, truth, mass, ids, arrays, unheld, summary = synthetic_world
    res = tx.process_time_recording(trial, "AB99/i0", registrations(summary), {}, mass, s02)
    c = res["columns"]
    assert len(res["time_s"]) == 1200 and np.allclose(np.diff(res["time_s"]), 0.01) and res["time_s"][0] == 0.0
    assert list(c) == tx.time_columns()
    assert np.nanmax(np.abs(c[tx.PELVIS] - RAD(-10.0))) < 1e-12                    # raw +10 deg, audited sign -1
    for leg in ("right", "left"):
        th, sh, ft = (c[f"{k}_sagittal_angle_{leg}_rad"] for k in ("thigh", "shank", "foot"))
        assert np.nanmax(np.abs(th - truth[leg]["th_t"])) < 5e-4 and np.nanmax(np.abs(ft - truth[leg]["th_f"])) < 5e-4
        hip, knee, ankle = (c[f"{k}_angle_{leg}_rad"] for k in ("hip_flexion", "knee_flexion", "ankle_dorsiflexion"))
        assert np.nanmax(np.abs(th - c[tx.PELVIS] - hip)) < 1e-12                  # composition is exact in the table
        assert np.nanmax(np.abs(th - sh - knee)) < 1e-12 and np.nanmax(np.abs(sh + ankle - ft)) < 1e-12
        # power = moment x joint speed, exactly
        assert np.allclose(c[f"knee_flexion_power_{leg}_W_kg"], c[f"knee_flexion_moment_{leg}_Nm_kg"] * (
            c[f"thigh_sagittal_velocity_{leg}_rad_s"] - c[f"shank_sagittal_velocity_{leg}_rad_s"]), atol=1e-12)
    assert res["held"] == {}


def test_whole_recording_force_and_cop_follow_the_plate(synthetic_world):
    trial, truth, mass, ids, arrays, unheld, summary = synthetic_world
    res = tx.process_time_recording(trial, "AB99/i0", registrations(summary), {}, mass, s02)
    c = res["columns"]
    for side, leg in (("R", "right"), ("L", "left")):
        fz = trial["forceplates"][side + "Force"][...][2][::10][:1200]
        loaded = -fz > 20.0
        v = c[f"grf_vertical_{leg}_BW"]
        assert np.allclose(v[loaded], -fz[loaded] / (mass * 9.81)) and np.all(v[~loaded] == 0.0)   # real force; 0 off the plate
        assert np.allclose(c[f"grf_lateral_{leg}_BW"], 0.0)
        cop = c[f"cop_anterior_{leg}_m"]
        assert np.isfinite(cop[loaded]).mean() > 0.95 and np.isnan(cop[~loaded]).all()             # unloaded: missing, never 0


def test_time_samples_at_stride_windows_reproduce_the_phase_values(synthetic_world):
    trial, truth, mass, ids, arrays, unheld, summary = synthetic_world
    c = tx.process_time_recording(trial, "AB99/i0", registrations(summary), {}, mass, s02)["columns"]
    cop_abs, nfin, nph, ntm = [], 0, 0, 0
    for i, oid in enumerate(ids):
        p = tx.parse_id(oid)
        leg, a, b = p["side"], p["a"], p["b"]
        for tmpl, key, kind in (("thigh_sagittal_angle_{w}_rad", "thigh_angle", "angle"), ("shank_sagittal_angle_{w}_rad", "shank_angle", "angle"),
                                ("foot_sagittal_angle_{w}_rad", "foot_angle", "angle"), ("knee_flexion_angle_{w}_rad", "knee_angle", "angle"),
                                ("ankle_dorsiflexion_angle_{w}_rad", "ankle_angle", "angle"), ("hip_flexion_angle_{w}_rad", "hip_angle", "pelvis_hip"),
                                ("thigh_sagittal_velocity_{w}_rad_s", "thigh_angle_velocity", "velocity"),
                                ("foot_sagittal_velocity_{w}_rad_s", "foot_angle_velocity", "velocity")):
            r = tx.compare_series(kind, arrays[key][i], tx.resample_window(c[tmpl.format(w=leg)], a, b))
            assert r["pass"], (oid, key, r)
        cmp = tx.compare_series("cop", unheld["cop_anterior"][i], tx.resample_window(c[f"cop_anterior_{leg}_m"], a, b))
        if cmp["n_both"]:
            cop_abs.append(cmp["abs_values_pooled"])
        nfin, nph, ntm = nfin + cmp["n_both"], nph + cmp["only_phase_finite"], ntm + cmp["only_time_finite"]
    assert tx.leg_cop_verdict(np.concatenate(cop_abs), nfin, nph, ntm)["pass"]


def test_held_legs_and_pending_recordings_keep_columns_missing_with_reasons(synthetic_world):
    trial, truth, mass, ids, arrays, unheld, summary = synthetic_world
    regs = registrations(summary, left={"cop_verdict": "held", "cop_reasons": ["r = 0.2"], "assignment_same_plate": 0.5})
    res = tx.process_time_recording(trial, "AB99/i0", regs, {}, mass, s02)
    for col in tx.leg_columns("left", tx.COPS):
        assert not np.isfinite(res["columns"][col]).any() and res["held"][col].startswith(tx.REASON_COP_PREFIX)
    for col in tx.leg_columns("left", tx.GRFS):
        assert not np.isfinite(res["columns"][col]).any() and res["held"][col] == tx.REASON_FORCE_ASSIGN
    assert np.isfinite(res["columns"]["cop_anterior_right_m"]).any() and "cop_anterior_right_m" not in res["held"]
    pend = tx.process_time_recording(trial, "AB01/i10", registrations(summary), {}, mass, s02)
    for leg in ("left", "right"):
        assert all(not np.isfinite(pend["columns"][c]).any() for c in tx.leg_columns(leg, tx.COPS + tx.GRFS))
        assert pend["held"][f"grf_vertical_{leg}_BW"] == tx.REASON_FORCE_PENDING
    assert np.isfinite(pend["columns"]["thigh_sagittal_angle_right_rad"]).any()          # angles stay published


def test_holds_from_the_phase_table_are_applied_to_pelvis_hip_and_moments(synthetic_world):
    trial, truth, mass, ids, arrays, unheld, summary = synthetic_world
    holds = {tx.PELVIS: [(100, 150)], "knee_flexion_moment_right_Nm_kg": [(200, 250)]}
    c = tx.process_time_recording(trial, "AB99/i0", registrations(summary), holds, mass, s02)["columns"]
    assert np.isnan(c[tx.PELVIS][99:150]).all() and np.isfinite(c[tx.PELVIS][98]) and np.isfinite(c[tx.PELVIS][150])
    assert np.isnan(c["hip_flexion_angle_right_rad"][99:150]).all()                       # hip = thigh - pelvis follows the pelvis hold
    assert np.isnan(c["knee_flexion_moment_right_Nm_kg"][199:250]).all() and np.isfinite(c["knee_flexion_moment_left_Nm_kg"][199:250]).all()
    assert np.isnan(c["knee_flexion_power_right_W_kg"][199:250]).all()


def test_marker_gap_leaves_dependent_columns_missing_at_those_frames_only():
    trial, v2, truth, mass = s02t.synthetic_trial(drop_marker="RKNE")
    ids, sides, arrays, unheld, summary, ledger = s02.process_recording(trial, "AB99/i0", v2, mass, 0.0)
    c = tx.process_time_recording(trial_with_vicon(trial), "AB99/i0", registrations(summary), {}, mass, s02)["columns"]
    th = c["thigh_sagittal_angle_right_rad"]
    assert np.isnan(th[300:420]).all() and np.isfinite(th[:299]).all() and np.isfinite(th[421:]).all()
    assert np.isfinite(c["thigh_sagittal_angle_left_rad"]).all()                          # the other leg is untouched
    assert np.isfinite(c[tx.PELVIS]).all()                                                # pelvis does not use the knee marker
