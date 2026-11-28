"""HIST-06 AddBiomechanics mapping adapter and pilot spec, on SYNTHETIC fixtures only.

The trials here are synthetic HIST-05-style frame tables (dofNN_pos/tau in the H23 DOF order, contact-body
force and CoP in a world frame with +y up, missing_grf_reason). Their motion is the gait-like leg of
tests/test_sign_offset_detector.py (seed 41), built in rule B and stored as the AddBiomechanics model defines
its coordinates (hip flexion, knee flexion and ankle dorsiflexion positive; generalized forces in N*m). The
left leg is the same motion half a cycle later. One trial faces world +x (Tan walking style, pelvis pitch
stored in pelvis_tilt); one faces world -z (Tan running style: the pelvis pitch is stored in pelvis_list and
pelvis_rotation is pi/2). Expected values come from the synthetic truth and hand-computed frame rotations,
not from the adapter. The audited-sign table and backlog used for publication are temporary copies with
synthetic HIST-06 entries; the committed files are not changed. No research data are read; nothing is
launched.
"""
import copy
import json
import math

import numpy as np
import pyarrow as pa
import pytest

from contributor_tools import run_hist06_addb_pilot as pilot
from contributor_tools.adapters import addbiomechanics_sign_adapter as addb
from contributor_tools.common import sign_application as sa
from contributor_tools.guarded_launcher import validate_spec
from tests.test_sign_offset_detector import DT, N, synthetic_leg

BUILD = sa.file_sha256(sa.DETECTOR_PATH)
MASS_KG = 70.0
UNITS = 24
LATERAL_N = 20.0      # outward force on each foot (synthetic)
COP_OUT_M = 0.1       # CoP outward offset of each foot (synthetic)
FLAGGED = slice(3000, 3011)
CHANNELS = ("pelvis_tilt", "hip_angle", "knee_angle", "ankle_angle", "hip_moment", "knee_moment", "ankle_moment")


def _flat(a):
    return a.reshape((a.shape[0] * a.shape[1],) + a.shape[2:])


@pytest.fixture(scope="module")
def truth():
    t, pts, joints, cop, grf, stance = synthetic_leg(n_units=UNITS, seed=41)
    right = {k: _flat(t[k]) for k in ("pelvis_tilt", "hip_angle", "knee_angle", "ankle_angle",
                                      "hip_moment", "knee_moment", "ankle_moment")}
    right["grf"] = _flat(grf) * MASS_KG
    right["cop"] = _flat(cop)
    left = {k: np.roll(v, N // 2, axis=0) for k, v in right.items()}
    left["pelvis_tilt"] = right["pelvis_tilt"]  # one pelvis
    return {"right": right, "left": left}


def synthetic_table(truth, facing, slug="ta22", subject="02", original="baseline", grf_scale=1.0, flags=None,
                    edit=None):
    """HIST-05-style frames for one trial. facing: '+x' or '-z' (world facing and treadmill direction).
    grf_scale multiplies the recorded force; flags replaces the per-frame missing_grf_reason array; edit(cols)
    may change recorded columns in place (e.g. a source NaN or an exact zero)."""
    n = UNITS * N
    folder = addb.STUDIES[slug][1]
    rid = f"train/No_Arm/{folder}/{subject}/{subject}.b3d#trial0"
    x = np.array([1.0, 0, 0]) if facing == "+x" else np.array([0, 0, -1.0])
    zr = np.cross(x, [0.0, 1.0, 0.0])  # person's right
    cols = {f"dof{i:02d}_{q}": np.zeros(n) for i in range(23) for q in ("pos", "tau")}
    p = truth["right"]["pelvis_tilt"]
    if facing == "+x":
        cols["dof00_pos"] = p.copy()                    # tilt = pitch when facing +x
    else:
        cols["dof01_pos"] = p.copy()                    # list = pitch when rotation = pi/2 (facing -z)
        cols["dof02_pos"] = np.full(n, math.pi / 2)     # pelvis_tilt column stays 0: it holds no pitch here
    for side, s in (("right", "r"), ("left", "l")):
        tr = truth[side]
        for j, coord in (("hip", "hip_flexion"), ("knee", "knee_angle"), ("ankle", "ankle_angle")):
            k = addb.DOF[f"{coord}_{s}"]
            cols[f"dof{k:02d}_pos"] = tr[f"{j}_angle"].copy()
            cols[f"dof{k:02d}_tau"] = tr[f"{j}_moment"] * MASS_KG
        cols[f"dof{addb.DOF['hip_adduction_' + s]:02d}_pos"] = np.full(n, 0.05)
        cols[f"dof{addb.DOF['hip_rotation_' + s]:02d}_pos"] = np.full(n, -0.03)
        out = zr if side == "right" else -zr
        f = grf_scale * tr["grf"][:, :1] * x + grf_scale * tr["grf"][:, 1:2] * np.array([0, 1.0, 0]) + LATERAL_N * out * (tr["grf"][:, 1:2] > 0)
        c = tr["cop"][:, :1] * x + tr["cop"][:, 1:2] * np.array([0, 1.0, 0]) + COP_OUT_M * out
        c = np.where(f[:, 1:2] > 0, c, 0.0)  # as the source: undefined CoP stored as an exact (0, 0, 0)
        body = f"calcn_{s}"
        for i, a in enumerate("xyz"):
            cols[f"{body}_force_{a}"] = f[:, i]
            cols[f"{body}_cop_{a}"] = c[:, i]
    if flags is None:
        flags = np.array(["notMissingGRF"] * n, dtype=object)
        flags[FLAGGED] = "footContactDetectedButNoForce"
    if edit is not None:
        edit(cols)
    cols.update({
        "com_vel_x": np.zeros(n), "com_vel_z": np.zeros(n), "missing_grf_reason": flags.tolist(),
        "time_s": np.arange(n) * DT, "source_frame_index": np.arange(n), "source_timestep_s": np.full(n, DT),
        "source_trial_index": np.zeros(n, dtype=np.int64), "source_recording_id": [rid] * n,
        "observation_id": [f"{original}_segment_0"] * n, "source_original_trial_name": [original] * n,
        "subject": [subject] * n, "task_info": [json.dumps({"source_original_trial_name": original})] * n,
        "subject_metadata": [json.dumps({"mass_kg": MASS_KG})] * n,
        "entered_mass_kg": np.full(n, MASS_KG), "dynamics_model_mass_kg": np.full(n, 64.0)})
    return pa.table(cols)


def _tables(tmp_path, entries=True):
    """Temporary audited-sign table (FA16/TA21/TA22 keys, + entries citing HIST-06) and backlog (HIST-06
    done and citing them). The committed files are read, never written."""
    table = json.loads(sa.AUDITED_PATH.read_text())
    backlog = json.loads(sa.BACKLOG_PATH.read_text())
    ids = []
    for slug, (key, _) in addb.STUDIES.items():
        ds = {"recording_id_pattern": addb.recording_pattern(slug), "entries": []}
        if entries:
            for ch in CHANNELS:
                ids.append(f"{key}-{ch}")
                ds["entries"].append({"id": f"{key}-{ch}", "channel": ch, "sign": 1, "audit_tasks": ["HIST-06"],
                                      "evidence_basis": "synthetic test entry", "citation": "synthetic"})
        table["datasets"][key] = ds
    task = next(t for t in backlog["tasks"] if t["id"] == "HIST-06")
    task["status"] = "done"
    task.setdefault("handoff", {}).setdefault("checks", []).append("synthetic citations: " + ", ".join(ids))
    a, b = tmp_path / "audited_signs.json", tmp_path / "backlog.json"
    a.write_text(json.dumps(table))
    b.write_text(json.dumps(backlog))
    return a, b


@pytest.fixture(scope="module")
def mapped(truth, tmp_path_factory):
    tmp = tmp_path_factory.mktemp("hist06")
    audited, backlog = _tables(tmp)
    out = {}
    for facing in ("+x", "-z"):
        slug, subject, original = ("ta22", "02", "baseline") if facing == "+x" else ("ta21", "s1", "nike_SR_24")
        trial = addb.trial_from_table(slug, synthetic_table(truth, facing, slug, subject, original))
        res = addb.apply_trial(trial, BUILD, backlog_path=backlog, audited_path=audited)
        cols, info = addb.trial_rows(trial, res, {"task": None})
        out[facing] = {"trial": trial, "result": res, "cols": {k: np.asarray(v) for k, v in cols.items()},
                       "info": info}
    return out


def _ref(cols, side):
    m = cols["reference_side"] == side
    return {k: v[m] for k, v in cols.items()}


# ---------------------------------------------------------------- DOF order and model checks
def test_dof_index_is_model_order_without_coupled_beta():
    # values typed from the HIST-06 probe (dof_order section), not from the adapter's list
    expected = {"pelvis_tilt": 0, "hip_flexion_r": 6, "knee_angle_r": 9, "ankle_angle_r": 10, "mtp_angle_r": 12,
                "hip_flexion_l": 13, "knee_angle_l": 16, "ankle_angle_l": 17, "lumbar_rotation": 22}
    assert {k: addb.DOF[k] for k in expected} == expected
    assert len(addb.DOF) == 23 and "knee_angle_r_beta" not in addb.DOF


def _osim(coupler=True, gravity="0 -9.8066499999999994 0", pelvis_axis="0 0 1"):
    coords = "".join(f'<Coordinate name="{c}"><range>-1 1</range></Coordinate>' for c in addb.H25)
    cpl = "".join(f'<CoordinateCouplerConstraint name="pf_{s}"><isEnforced>true</isEnforced>'
                  f'<coupled_coordinates_function><LinearFunction name="f"><coefficients> 1 0</coefficients>'
                  f'</LinearFunction></coupled_coordinates_function><independent_coordinate_names>knee_angle_{s}'
                  f'</independent_coordinate_names><dependent_coordinate_name>knee_angle_{s}_beta'
                  f'</dependent_coordinate_name></CoordinateCouplerConstraint>' for s in "rl") if coupler else ""
    axes = [("rotation1", "pelvis_tilt", pelvis_axis), ("rotation2", "pelvis_list", "1 0 0"),
            ("rotation3", "pelvis_rotation", "0 1 0")]
    ta = "".join(f'<TransformAxis name="{n}"><coordinates>{c}</coordinates><axis>{a}</axis><LinearFunction '
                 f'name="function"><coefficients> 1 0</coefficients></LinearFunction></TransformAxis>' for n, c, a in axes)
    gp = (f'<CustomJoint name="ground_pelvis"><PhysicalOffsetFrame name="g"><orientation>0 0 0</orientation>'
          f'</PhysicalOffsetFrame><PhysicalOffsetFrame name="p"><orientation>0 0 0</orientation></PhysicalOffsetFrame>'
          f'<SpatialTransform>{ta}</SpatialTransform></CustomJoint>')
    return f"<OpenSimDocument><Model><gravity>{gravity}</gravity>{gp}{coords}{cpl}</Model></OpenSimDocument>".encode()


def _columns(n_dofs=23):
    cols = [f"dof{i:02d}_pos" for i in range(n_dofs)]
    return cols + [f"calcn_{s}_{q}_{a}" for s in "rl" for q in ("force", "cop") for a in "xyz"]


def _conv(osim):
    import hashlib
    return {"dynamics_model_sha256": hashlib.sha256(osim).hexdigest(), "model_coordinates": list(addb.H25)}


def test_model_check_accepts_the_synthetic_model():
    osim = _osim()
    facts = addb.check_model(osim, _conv(osim), _columns())
    assert "H23" in facts["dof_rule"]


@pytest.mark.parametrize("osim, n_dofs, match", [
    (_osim(coupler=False), 23, "coupler"),
    (_osim(gravity="0 0 -9.81"), 23, "gravity"),
    (_osim(pelvis_axis="1 0 0"), 23, "rotation1"),
    (_osim(), 25, "DOF position columns"),
])
def test_model_check_refuses_what_the_mapping_does_not_rest_on(osim, n_dofs, match):
    with pytest.raises(addb.ModelMismatchError, match=match):
        addb.check_model(osim, _conv(osim), _columns(n_dofs))


def test_model_check_refuses_a_model_that_is_not_the_recorded_one():
    osim = _osim()
    with pytest.raises(addb.ModelMismatchError, match="sha256"):
        addb.check_model(osim + b" ", _conv(osim), _columns())


# ---------------------------------------------------------------- MAP-TAN-TASK and task labels
@pytest.mark.parametrize("slug, name, match", [
    ("ta21", "nike_SR_24", True), ("ta21", "mini_baseline_28", True), ("ta21", "hip_calibration", False),
    ("ta21", "nike_SR_26", False), ("ta21", "Nike_SR_24", False), ("ta21", "nike_SR_24 ", False),
    ("ta22", "baseline", True), ("ta22", "trunk_sway", True), ("ta22", "baseline_2", False), ("ta22", "static", False),
    ("fa16", "Gait_7", True), ("fa16", "STS_2", True), ("fa16", "StairUp_3", True), ("fa16", "Squat_1", False),
])
def test_protocol_pattern(slug, name, match):
    assert addb.protocol_match(slug, name) is match


@pytest.mark.parametrize("answer", [None, "A", "B", "C", "defer"])
def test_hip_calibration_never_gets_a_task(answer):
    task, rule = addb.task_label("ta21", "hip_calibration", answer)
    assert task is None and "MAP-TAN-TASK" in rule


@pytest.mark.parametrize("slug, name, answer, expected", [
    ("ta21", "nike_SR_24", None, "run"),
    ("ta22", "baseline", None, None), ("ta22", "baseline", "A", "level_walking"),
    ("ta22", "fpa", "A", None), ("ta22", "fpa", "B", "level_walking"),
    ("fa16", "STS_2", "B", None), ("fa16", "STS_2", "C", "sit_to_stand"),
    ("fa16", "Gait_7", "A", "level_walking"), ("fa16", "StairUp_2", "A", "stair_ascent"),
])
def test_task_labels_only_from_the_decision(slug, name, answer, expected):
    assert addb.task_label(slug, name, answer)[0] == expected


def test_decision_answers_ignore_open_and_deferred():
    backlog = {"decisions": [{"id": addb.TASK_DECISION, "answer": "B"}]}
    assert addb.decision_answers(backlog)["task"] == "B"
    assert addb.decision_answers({"decisions": [{"id": addb.TASK_DECISION, "answer": "defer"}]})["task"] is None
    assert addb.decision_answers({"decisions": []})["task"] is None
    assert "mass" not in addb.decision_answers(backlog)  # normalization mass is not a decision (standing rule)


def test_non_protocol_trial_rows_carry_no_task(truth, tmp_path):
    audited, backlog = _tables(tmp_path)
    trial = addb.trial_from_table("ta21", synthetic_table(truth, "-z", "ta21", "s7", "hip_calibration"))
    res = addb.apply_trial(trial, BUILD, backlog_path=backlog, audited_path=audited)
    cols, info = addb.trial_rows(trial, res, {"task": "C"})
    assert set(cols["task"]) == {None} and info["in_task_table"] is False
    assert set(cols["task_id"]) == {"hip_calibration"} and set(cols["source_original_trial_name"]) == {"hip_calibration"}
    assert all(not json.loads(t)["in_task_table"] for t in set(cols["task_info"]))
    # no forward locomotion: anterior and lateral force stay empty, vertical force stays
    assert np.isnan(np.asarray(cols["grf_anterior_ipsi_N"], float)).all()
    assert np.isfinite(np.asarray(cols["grf_vertical_ipsi_N"], float)).any()


def test_dropped_falisse_subjects_are_refused():
    with pytest.raises(addb.OutOfScopeError, match="D-HIST-04-2"):
        addb.check_recording("fa16", "train/No_Arm/Falisse2017_Formatted_No_Arm/subject_7/subject_7.b3d#trial0")


# ---------------------------------------------------------------- geometry
@pytest.mark.parametrize("tilt, lst, rot, pitch", [
    (0.2, 0.0, 0.0, 0.2),             # facing +x: pitch = tilt
    (0.0, 0.2, math.pi / 2, 0.2),     # facing -z: pitch = list
    (-0.2, 0.0, math.pi, 0.2),        # facing -x: Rz(t) (-1, 0, 0) = (-cos t, -sin t, 0)
    (0.3, 0.0, math.pi / 2, 0.0),     # facing -z: tilt is obliquity, no pitch
])
def test_pelvis_pitch_is_heading_independent(tilt, lst, rot, pitch):
    assert addb.pelvis_pitch(np.array([tilt]), np.array([lst]), np.array([rot]))[0] == pytest.approx(pitch, abs=1e-12)


def test_frame_basis_hand_computed():
    x, y, z = addb.frame_basis([-1.0, 0.0, 0.0])  # walking toward world -x
    f = np.array([-100.0, 700.0, 30.0])
    assert (f @ x, f[1], f @ z) == pytest.approx((100.0, 700.0, -30.0))  # z' = (0, 0, -1)
    # walking toward world -z: the person turned +90 deg about +y, so their right (world +z at zero yaw)
    # becomes Ry(90 deg) (0, 0, 1) = (1, 0, 0)
    x, y, z = addb.frame_basis([0.0, 0.0, -1.0])
    assert z == pytest.approx([1.0, 0.0, 0.0])


# ---------------------------------------------------------------- end to end (hook, frame, rows)
@pytest.mark.parametrize("facing", ["+x", "-z"])
def test_walking_direction_from_treadmill_cop(mapped, facing):
    wd = mapped[facing]["result"]["frame"]["walking"]
    want = [1.0, 0.0, 0.0] if facing == "+x" else [0.0, 0.0, -1.0]
    assert wd["ok"] and np.allclose(wd["direction"], want, atol=1e-6)


@pytest.mark.parametrize("facing", ["+x", "-z"])
def test_published_sagittal_columns_equal_the_source(mapped, truth, facing):
    m = mapped[facing]
    for side in ("right", "left"):
        for k in CHANNELS:
            assert m["result"]["legs"][side]["application"].log["channels"][k]["publication"] == "publish", k
    r = _ref(m["cols"], "right")
    tr, tl = truth["right"], truth["left"]
    assert np.array_equal(r["hip_flexion_angle_ipsi_rad"], tr["hip_angle"])
    assert np.array_equal(r["knee_flexion_angle_contra_rad"], tl["knee_angle"])
    assert np.array_equal(r["ankle_dorsiflexion_moment_ipsi_Nm"], tr["ankle_moment"] * MASS_KG)
    assert np.allclose(r["pelvis_sagittal_angle_rad"], tr["pelvis_tilt"], atol=1e-12)
    # per kg of the recorded 70 kg: back to the synthetic per-kg truth (stored as truth x 70 N*m)
    assert np.allclose(r["hip_flexion_moment_ipsi_Nm_kg"], tr["hip_moment"], rtol=0, atol=1e-12)


@pytest.mark.parametrize("facing", ["+x", "-z"])
def test_force_and_cop_in_the_rule_b_frame(mapped, truth, facing):
    cols = mapped[facing]["cols"]
    for ref, other in (("right", "left"), ("left", "right")):
        r = _ref(cols, ref)
        g = truth[ref]["grf"]
        assert np.allclose(r["grf_anterior_ipsi_N"], g[:, 0], atol=1e-9)  # every frame, flagged or not
        assert np.allclose(r["grf_vertical_ipsi_N"], g[:, 1], atol=1e-9)
        loaded = g[:, 1] > 0
        assert np.allclose(r["grf_lateral_ipsi_N"][loaded], LATERAL_N, atol=1e-9)  # outward, both legs
        assert np.allclose(r["grf_lateral_ipsi_N"][~loaded], 0.0, atol=1e-12)
        assert np.allclose(r["cop_lateral_ipsi_m"][loaded], COP_OUT_M, atol=1e-12)
        assert np.allclose(r["cop_anterior_ipsi_m"][loaded], truth[ref]["cop"][loaded, 0], atol=1e-12)
        assert np.isnan(r["cop_anterior_ipsi_m"][~loaded]).all()  # (0, 0, 0) placeholder is not a CoP


def test_flagged_frames_keep_recorded_force_and_carry_the_flag(mapped, truth):
    r = _ref(mapped["+x"]["cols"], "right")
    g = truth["right"]["grf"]
    assert np.allclose(r["grf_vertical_ipsi_N"][FLAGGED], g[FLAGGED, 1], atol=1e-9)
    loaded = g[FLAGGED, 1] > 0
    assert loaded.any() and np.isfinite(r["cop_vertical_ipsi_m"][FLAGGED][loaded]).all()  # flag blanks no CoP
    assert set(r["missing_grf_reason"][FLAGGED]) == {"footContactDetectedButNoForce"}  # source label, unchanged
    assert mapped["+x"]["result"]["log"]["grf_frames_flagged_kept"] == FLAGGED.stop - FLAGGED.start


def _stride_count(result, side):
    leg = result["log"]["legs"][side]
    return len(leg["stride_frames"]) if leg["unit"] == "stride" else 0


def test_flagged_burst_does_not_break_strides(mapped):
    # independent count from the fixture layout: 24 strides of 150 samples; a heel strike needs 5 unloaded
    # frames before it, so the right foot's first contact (frame 1) does not count: 23 strikes, 22 strides;
    # the left foot (half a cycle later) has 24 strikes, 23 strides. The 11 flagged frames change nothing.
    res = mapped["+x"]["result"]
    assert _stride_count(res, "right") == 22 and _stride_count(res, "left") == 23


def test_unloaded_cop_placeholder_is_empty_and_independent_of_the_flag(truth, tmp_path):
    """Source stores CoP (0, 0, 0) wherever the foot is unloaded (HIST-06-verify F3). Those frames must come out
    empty whatever their flag; a loaded frame keeps its recorded CoP even when flagged."""
    n = UNITS * N
    fy = truth["right"]["grf"][:, 1]
    flags = np.array(["footContactDetectedButNoForce"] * n, dtype=object)  # every frame flagged
    flags[: n // 2] = "notMissingGRF"                                       # first half clean
    audited, backlog = _tables(tmp_path)
    trial = addb.trial_from_table("ta22", synthetic_table(truth, "+x", flags=flags))
    for a in "xyz":  # fixture check: the placeholder really is an exact zero triple
        assert (np.asarray(trial.data[f"calcn_r_cop_{a}"])[fy <= 0] == 0.0).all()
    res = addb.apply_trial(trial, BUILD, backlog_path=backlog, audited_path=audited)
    cols, _ = addb.trial_rows(trial, res, {"task": None})
    r = _ref({k: np.asarray(v) for k, v in cols.items()}, "right")
    for c in ("cop_anterior_ipsi_m", "cop_vertical_ipsi_m", "cop_lateral_ipsi_m"):
        assert np.isnan(r[c].astype(float)[fy <= 0]).all()
        assert np.isfinite(r[c].astype(float)[fy > 0]).all()           # clean and flagged halves alike
    assert np.allclose(r["grf_vertical_ipsi_N"].astype(float), fy, atol=1e-9)  # force untouched (zeros stay)
    assert (r["grf_vertical_ipsi_N"].astype(float)[fy <= 0] == 0.0).all()


REAL_PATTERN_SCALE = 90.0 / 70.0   # recorded force as for a 90 kg runner: stance peaks above 700 N
BLIP_STANCE = slice(1501, 1590)    # unit 10 right loaded stance: frames 1501-1589 (phase 0 and >= 0.6 unloaded)
ZERO_FRAME = 1820                  # inside unit 12 right stance
NAN_FRAME = 2500                   # inside the right stride that starts at frame 2401


@pytest.fixture(scope="module")
def real_pattern(truth, tmp_path_factory):
    """Frame-level flags as AddBiomechanics writes them (HIST-06-verify F1): footContactDetectedButNoForce on
    every frame where a foot is unloaded (flight-like), a whole right stance marked missingBlip although its
    recorded force exceeds 700 N, one stance frame with an exact recorded zero (flagged), one source NaN."""
    n = UNITS * N
    fy_r, fy_l = truth["right"]["grf"][:, 1], truth["left"]["grf"][:, 1]
    flags = np.array(["notMissingGRF"] * n, dtype=object)
    flags[(fy_r <= 0) | (fy_l <= 0)] = "footContactDetectedButNoForce"
    flags[BLIP_STANCE] = "missingBlip"
    flags[ZERO_FRAME] = "footContactDetectedButNoForce"

    def edit(cols):
        for a in "xyz":
            cols[f"calcn_r_force_{a}"] = cols[f"calcn_r_force_{a}"].copy()
            cols[f"calcn_r_force_{a}"][ZERO_FRAME] = 0.0
            cols[f"calcn_r_cop_{a}"] = cols[f"calcn_r_cop_{a}"].copy()
            cols[f"calcn_r_cop_{a}"][ZERO_FRAME] = 0.0  # the source's placeholder with a zero force
        cols["calcn_r_force_y"][NAN_FRAME] = np.nan
    tmp = tmp_path_factory.mktemp("hist06_real")
    audited, backlog = _tables(tmp)
    trial = addb.trial_from_table("ta21", synthetic_table(truth, "-z", "ta21", "s3", "nike_SR_24",
                                                          grf_scale=REAL_PATTERN_SCALE, flags=flags, edit=edit))
    res = addb.apply_trial(trial, BUILD, backlog_path=backlog, audited_path=audited)
    cols, _ = addb.trial_rows(trial, res, {"task": None})
    return {"trial": trial, "result": res, "cols": {k: np.asarray(v) for k, v in cols.items()}, "flags": flags}


def test_real_marking_pattern_keeps_force_and_finds_strides(real_pattern, truth):
    m = real_pattern
    g = truth["right"]["grf"][:, 1] * REAL_PATTERN_SCALE
    assert g[BLIP_STANCE].max() > 700.0                                    # fixture: a loaded stance
    assert (m["flags"] != "notMissingGRF").mean() > 0.5                    # most frames flagged, as in F1
    r = _ref(m["cols"], "right")
    assert np.allclose(r["grf_vertical_ipsi_N"][BLIP_STANCE], g[BLIP_STANCE], atol=1e-9)
    assert set(r["missing_grf_reason"][BLIP_STANCE]) == {"missingBlip"}
    assert r["grf_vertical_ipsi_N"][ZERO_FRAME] == 0.0                     # recorded zero kept, not blanked
    assert r["missing_grf_reason"][ZERO_FRAME] == "footContactDetectedButNoForce"
    assert np.isnan(r["grf_vertical_ipsi_N"][NAN_FRAME])                   # source NaN stays empty
    assert np.isnan(r["cop_anterior_ipsi_m"][ZERO_FRAME]) and np.isnan(r["cop_vertical_ipsi_m"][NAN_FRAME])
    assert np.isfinite(r["cop_vertical_ipsi_m"][BLIP_STANCE]).all()       # flagged loaded stance keeps CoP
    assert np.isfinite(np.delete(r["grf_vertical_ipsi_N"], NAN_FRAME)).all()
    # strides from the recorded force: right loses only the stride holding the source NaN (22 - 1); left 23
    assert _stride_count(m["result"], "right") == 21 and _stride_count(m["result"], "left") == 23
    for side in ("right", "left"):
        assert m["result"]["legs"][side]["application"].report["task"] == "run"  # stride units carry the task


def test_block_fallback_without_strides(truth, tmp_path):
    """No heel strike (recorded force below the 50 N threshold everywhere): fixed 100-frame blocks, no task."""
    audited, backlog = _tables(tmp_path)
    trial = addb.trial_from_table("ta22", synthetic_table(truth, "+x", grf_scale=0.05))
    assert (truth["right"]["grf"][:, 1] * 0.05).max() < addb.HS_THRESHOLD_N  # fixture: no strike possible
    res = addb.apply_trial(trial, BUILD, backlog_path=backlog, audited_path=audited)
    for side in ("right", "left"):
        leg = res["log"]["legs"][side]
        assert leg["unit"] == "block" and leg["units"] == (UNITS * N) // 100 and leg["stride_frames"] == []
        assert res["legs"][side]["application"].report["task"] is None


def test_reference_legs_swap_roles(mapped):
    cols = mapped["+x"]["cols"]
    r, l = _ref(cols, "right"), _ref(cols, "left")
    assert np.array_equal(r["hip_flexion_angle_ipsi_rad"], l["hip_flexion_angle_contra_rad"])
    assert np.array_equal(r["grf_vertical_contra_N"], l["grf_vertical_ipsi_N"], equal_nan=True)
    assert len(cols["time_s"]) == 2 * UNITS * N


def test_segments_and_velocities_from_published_channels(mapped, truth):
    r = _ref(mapped["+x"]["cols"], "right")
    thigh = r["pelvis_sagittal_angle_rad"] + r["hip_flexion_angle_ipsi_rad"]
    shank = thigh - r["knee_flexion_angle_ipsi_rad"]
    foot = shank + r["ankle_dorsiflexion_angle_ipsi_rad"]
    assert np.allclose(r["thigh_sagittal_angle_ipsi_rad"], thigh, atol=1e-12)
    assert np.allclose(r["foot_sagittal_angle_ipsi_rad"], foot, atol=1e-12)
    assert np.allclose(r["knee_flexion_velocity_ipsi_rad_s"], np.gradient(truth["right"]["knee_angle"], DT))


def test_hip_adduction_keeps_source_sign(mapped):
    r = _ref(mapped["+x"]["cols"], "left")
    assert np.allclose(r["hip_adduction_angle_ipsi_rad"], 0.05) and np.allclose(r["hip_rotation_angle_contra_rad"], -0.03)


def test_without_audited_entries_everything_sagittal_is_held(truth, tmp_path):
    audited, backlog = _tables(tmp_path, entries=False)
    trial = addb.trial_from_table("ta22", synthetic_table(truth, "+x"))
    res = addb.apply_trial(trial, BUILD, backlog_path=backlog, audited_path=audited)
    for side in ("right", "left"):
        ch = res["legs"][side]["application"].log["channels"]
        assert all(c["publication"] == "hold" and c["hold_reason"] for c in ch.values())
    cols, _ = addb.trial_rows(trial, res, {"task": None})
    assert np.isnan(np.asarray(cols["knee_flexion_angle_ipsi_rad"], float)).all()
    assert np.isnan(np.asarray(cols["thigh_sagittal_angle_ipsi_rad"], float)).all()


def test_dataset_missing_from_the_committed_table_is_refused(truth):
    table = json.loads(sa.AUDITED_PATH.read_text())
    if "TA22" in table["datasets"]:
        pytest.skip("the committed table already lists TA22")
    trial = addb.trial_from_table("ta22", synthetic_table(truth, "+x"))
    with pytest.raises(ValueError, match="not in the audited-sign table"):
        addb.apply_trial(trial, BUILD)


def _with_masses(trial, entered, fitted=64.0):
    """Copy of a synthetic trial whose recorded (entered) and fitted (dynamics-model) mass columns are replaced."""
    data = dict(trial.data)
    n = len(trial.flags)
    data["entered_mass_kg"] = np.asarray(entered, float) if np.ndim(entered) else np.full(n, float(entered))
    data["dynamics_model_mass_kg"] = np.full(n, float(fitted))
    return addb.Trial(**{**trial.__dict__, "data": data})


def test_per_kg_and_body_weight_use_the_recorded_mass(mapped, truth):
    """Synthetic truth is per kg; the source stores it x 70 kg (N*m, N). Dividing by the recorded 70 kg must
    give the truth back; the fitted 64 kg in the same rows must not be used."""
    m = mapped["+x"]
    cols, info = addb.trial_rows(m["trial"], m["result"], {"task": None})
    r = _ref({k: np.asarray(v) for k, v in cols.items()}, "right")
    clean = np.ones(UNITS * N, bool)
    clean[FLAGGED] = False
    assert np.allclose(r["knee_flexion_moment_ipsi_Nm_kg"].astype(float), truth["right"]["knee_moment"], atol=1e-12)
    assert np.allclose(r["ankle_dorsiflexion_moment_contra_Nm_kg"].astype(float), truth["left"]["ankle_moment"], atol=1e-12)
    g_per_kg = truth["right"]["grf"][:, 1] / MASS_KG
    assert np.allclose(r["grf_vertical_ipsi_BW"].astype(float)[clean], g_per_kg[clean] / 9.80665, atol=1e-12)
    assert info["normalization_mass_kg"] == MASS_KG
    assert set(r["normalization_mass_kg"].astype(float)) == {MASS_KG}
    assert all("recorded participant mass" in b for b in set(r["normalization_mass_basis"]))
    fitted = truth["right"]["knee_moment"] * MASS_KG / 64.0
    assert not np.allclose(r["knee_flexion_moment_ipsi_Nm_kg"].astype(float), fitted)


def test_the_divisor_follows_the_recorded_column(mapped, truth):
    m = mapped["+x"]
    trial = _with_masses(m["trial"], 82.5, fitted=70.0)  # fitted equal to the storing mass: must still not be used
    cols, _ = addb.trial_rows(trial, m["result"], {"task": None})
    r = _ref({k: np.asarray(v) for k, v in cols.items()}, "right")
    assert np.allclose(r["hip_flexion_moment_ipsi_Nm_kg"].astype(float),
                       truth["right"]["hip_moment"] * 70.0 / 82.5, atol=1e-12)


@pytest.mark.parametrize("entered", [math.nan, 0.0, -5.0])
def test_missing_recorded_mass_leaves_per_kg_empty(mapped, entered):
    m = mapped["+x"]
    cols, info = addb.trial_rows(_with_masses(m["trial"], entered), m["result"], {"task": None})
    assert np.isnan(np.asarray(cols["knee_flexion_moment_ipsi_Nm_kg"], float)).all()
    assert np.isnan(np.asarray(cols["grf_vertical_ipsi_BW"], float)).all()
    assert np.isfinite(np.asarray(cols["knee_flexion_moment_ipsi_Nm"], float)).any()  # N*m unaffected
    assert info["normalization_mass_kg"] is None
    assert all("missing or not positive" in b for b in set(cols["normalization_mass_basis"]))


def test_recorded_mass_must_be_constant_within_a_trial(mapped):
    m = mapped["+x"]
    n = UNITS * N
    entered = np.full(n, MASS_KG)
    entered[-1] = 71.0
    with pytest.raises(ValueError, match="not constant"):
        addb.trial_rows(_with_masses(m["trial"], entered), m["result"], {"task": None})


def test_inputs_are_not_modified_and_undo_restores_them(mapped):
    for side, leg in mapped["+x"]["result"]["legs"].items():
        app = leg["application"]
        restored = sa.undo_sign_application(app.channels, copy.deepcopy(app.log))
        for k, a in restored.items():
            assert sa.array_sha256(a) == sa.array_sha256(leg["inputs"]["channels"][k])


def test_rows_fit_the_declared_schema(mapped):
    m = mapped["+x"]
    cols, _ = addb.trial_rows(m["trial"], m["result"], {"task": None})
    t = pa.table(cols, schema=addb.arrow_schema())
    assert t.num_rows == 2 * UNITS * N


# ---------------------------------------------------------------- pilot sample and spec
def test_pilot_sample_is_seeded_and_adds_the_known_case():
    found = {"fa16": ["subject_0", "subject_2"], "ta21": ["s1", "s3", "s7"], "ta22": ["02", "04"]}
    a, b = pilot.pilot_sample(found), pilot.pilot_sample(found)
    assert a == b
    picks, extra = a
    assert (extra == []) == (picks["ta21"] == "s7")
    if extra:
        assert extra == [["ta21", "s7", "hip_calibration"]]


def test_spec_validates_on_a_synthetic_root(tmp_path, monkeypatch):
    for slug, subj in (("fa16", "subject_0"), ("ta21", "s1"), ("ta21", "s7"), ("ta22", "02")):
        d = tmp_path / slug / subj
        d.mkdir(parents=True)
        (d / "conversion.json").write_text(json.dumps({"frames_parquet_sha256": "a" * 64,
                                                       "dynamics_model_sha256": "b" * 64}))
    spec = pilot.build_spec(root=tmp_path)
    validate_spec(spec)
    assert spec["command"][:3] == ["python3", pilot.RUNNER, "run"]
    assert spec["address_space_mib"] == 768
