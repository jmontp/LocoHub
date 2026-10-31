"""Independent verifier tests for the CORE-04 sign and offset detector.

Written by the CORE-04 verifier, separately from tests/test_sign_offset_detector.py.
Every array here is SYNTHETIC and built in this file; no research dataset is read
and the worker's fixture generator is not imported. Expected signs come from
anatomical statements under rule B (DOC-03): the person faces +x, +y up, +z = the
person's right; segment angles are counterclockwise positive (pelvis anterior tilt
negative); joint angles and internal moments are positive in their named direction
(hip flexion, knee flexion, ankle dorsiflexion; flexor/dorsiflexor moments). They are
checked with numpy's 3D cross product, not with the module's own formulas. (Rule C,
used until 2026-10-31, differed only in the knee: flexion and flexor moment negative.)

Tests marked xfail(strict=True) document defects found in verification
(docs/maintainers/handoffs/CORE-04-verify.json, required fixes). When a fix lands
they XPASS, which fails the run under strict mode: remove the marker then.
"""
import numpy as np
import pytest

from contributor_tools.common import sign_offset_detector as sod

N = 150
PH = np.linspace(0.0, 1.0, N)


# ------------------------------------------------------------------ helpers
def _ccw_z(r2, f2):
    """z component of r x F in 3D with x forward, y up, z = x cross y (person's right)."""
    r3 = np.concatenate([r2, np.zeros(r2.shape[:-1] + (1,))], -1)
    f3 = np.concatenate([f2, np.zeros(f2.shape[:-1] + (1,))], -1)
    return np.cross(r3, f3)[..., 2]


def _gait(n_units=20, seed=101, noise=0.004):
    """Simple rule-B waveforms: hip flexion +, knee flexion +, ankle dorsiflexion +."""
    rng = np.random.default_rng(seed)
    a = 1 + 0.05 * rng.standard_normal((n_units, 1))
    hip = 0.2 + 0.35 * a * np.cos(2 * np.pi * PH)
    knee = (0.1 + 0.55 * a * (1 - np.cos(2 * np.pi * PH)) ** 2 / 4 * (PH > 0.45) * 2
            + 0.05 * np.sin(np.pi * PH))  # flexion positive (rule B)
    ankle = 0.1 * a * np.sin(2 * np.pi * PH) - 0.2 * a * np.exp(-0.5 * ((PH - 0.62) / 0.05) ** 2)
    out = {"hip_angle": hip, "knee_angle": knee, "ankle_angle": ankle}
    return {k: v + noise * rng.standard_normal(v.shape) for k, v in out.items()}


# --------------------------------------------- 1. physics under rule B (pass)
def test_marker_angles_match_anatomical_labels():
    up_hip = np.array([0.0, 0.9])
    # Hip flexed: knee 0.2 m ahead of the hip, pelvis level, so hip angle > 0.
    pts = {"pelvis_rear": up_hip + [-0.12, 0.05], "pelvis_front": up_hip + [0.12, 0.05],
           "hip": up_hip, "knee": up_hip + [0.2, -0.4]}
    assert sod.marker_reference_angles(pts)["hip_angle"] > 0.3
    # Anterior pelvic tilt: ASIS (front) lower than PSIS (rear) -> pelvis tilt < 0.
    pts = {"pelvis_rear": np.array([-0.12, 1.0]), "pelvis_front": np.array([0.12, 0.96])}
    assert sod.marker_reference_angles(pts)["pelvis_tilt"] < 0
    # Knee flexed: thigh vertical, ankle 0.2 m behind the knee -> knee angle > 0 (rule B).
    pts = {"hip": np.array([0.0, 0.9]), "knee": np.array([0.0, 0.45]),
           "ankle": np.array([-0.2, 0.06])}
    assert sod.marker_reference_angles(pts)["knee_angle"] > 0.3
    # Dorsiflexed: shank vertical, toe higher than heel -> ankle angle > 0.
    pts = {"knee": np.array([0.0, 0.5]), "ankle": np.array([0.0, 0.08]),
           "heel": np.array([-0.06, 0.02]), "toe": np.array([0.16, 0.08])}
    assert sod.marker_reference_angles(pts)["ankle_angle"] > 0.2


def test_lever_arm_sign_matches_cross_product_physics():
    n_units = 12
    x = np.clip(PH / 0.6, 0, 1)
    stance = np.broadcast_to(PH < 0.6, (n_units, N)).copy()
    fy = np.where(stance, 9.81 * np.sin(np.pi * x), 0.0)
    fx = np.where(stance, -1.5 * np.sin(2 * np.pi * x), 0.0)
    grf = np.broadcast_to(np.stack([fx, fy], -1), (n_units, N, 2)).copy()
    ankle = np.zeros((n_units, N, 2)); ankle[..., 1] = 0.08
    cop = ankle + np.stack([np.broadcast_to(-0.06 + 0.22 * x, (n_units, N)),
                            np.full((n_units, N), -0.08)], -1)
    # Static foot: M_internal + (r x F)_z = 0 about the ankle.
    m_true = -_ccw_z(cop - ankle, grf)
    late = stance & (x > 0.7)
    assert np.all(m_true[late] < 0)  # CoP ahead of ankle -> plantarflexor -> negative (rule B)
    rng = np.random.default_rng(5)
    for src_sign in (1, -1):
        src = src_sign * m_true + 0.02 * rng.standard_normal(m_true.shape)
        ev = sod.lever_arm_test("ankle", src, ankle, cop, grf, stance)
        assert ev.sign == src_sign
    # Knee: GRF passing behind the knee -> internal extensor moment on the shank, which is
    # counterclockwise (physics), and negative under rule B (flexor positive).
    knee = ankle + [0.08, 0.40]
    m_knee_ccw = -_ccw_z(cop - knee, grf)
    early = stance & (x > 0.1) & (x < 0.3)
    assert np.all(m_knee_ccw[early] > 0)
    m_knee_b = -m_knee_ccw  # extension counterclockwise; flexion named positive
    assert np.all(m_knee_b[early] < 0)
    for src_sign in (1, -1):
        src = src_sign * m_knee_b + 0.02 * rng.standard_normal(m_knee_b.shape)
        assert sod.lever_arm_test("knee", src, knee, cop, grf, stance).sign == src_sign


def test_power_identity_sign_from_push_off_physics():
    rng = np.random.default_rng(9)
    n_units, dt = 12, 1.1 / (N - 1)
    q = np.broadcast_to(0.1 * np.sin(2 * np.pi * PH) - 0.25 * np.exp(-0.5 * ((PH - 0.6) / 0.05) ** 2),
                        (n_units, N)) + 0.001 * rng.standard_normal((n_units, N))
    m = np.broadcast_to(-1.5 * np.exp(-0.5 * ((PH - 0.5) / 0.08) ** 2), (n_units, N)).copy()
    w = np.gradient(q, axis=1) / dt
    p_true = m * w
    push = (PH > 0.55) & (PH < 0.6)  # plantarflexing (w < 0) with plantarflexor moment (m < 0)
    assert np.all(w[:, push] < 0) and np.all(p_true[:, push] > 0)
    vals = {"ankle_moment": m, "ankle_angle": q, "ankle_power": -p_true}
    assert sod.power_relation("ankle", vals, dt).product == -1
    vals["ankle_power"] = p_true
    assert sod.power_relation("ankle", vals, None).product == 1  # phase data: sign only


def test_projection_invariant_to_heading_and_reflection():
    rng = np.random.default_rng(20261030)
    sag = {"hip": np.array([0.0, 0.92]), "knee": np.array([0.12, 0.5]),
           "ankle": np.array([0.02, 0.08]), "heel": np.array([-0.05, 0.02]),
           "toe": np.array([0.17, 0.03]), "pelvis_rear": np.array([-0.12, 0.98]),
           "pelvis_front": np.array([0.12, 0.95])}
    lateral = {"hip": 0.09, "knee": 0.11, "ankle": 0.10, "heel": 0.10, "toe": 0.10,
               "pelvis_rear": 0.05, "pelvis_front": 0.12}
    base = sod.marker_reference_angles(sag)
    for _ in range(8):
        psi = rng.uniform(-np.pi, np.pi)
        mirror = rng.choice([1.0, -1.0])
        f = np.array([np.cos(psi), np.sin(psi), 0.0])
        lat = mirror * np.array([-np.sin(psi), np.cos(psi), 0.0])
        lab = {k: v[0] * f + lateral[k] * lat + v[1] * np.array([0, 0, 1.0]) + [3.0, -2.0, 0.01]
               for k, v in sag.items()}
        up = np.array([0, 0, 1.0])
        fwd = sod.forward_axis(lab["heel"], lab["toe"], up)
        proj = {k: sod.project_sagittal(v, fwd, up) for k, v in lab.items()}
        got = sod.marker_reference_angles(proj)
        for k in base:
            assert abs(got[k] - base[k]) < 1e-9, k


# --------------------------------- 2/3. decision rules and statistics (pass)
def _units(signs, seed=3, noise=0.01):
    rng = np.random.default_rng(seed)
    ref = np.broadcast_to(0.3 * np.sin(2 * np.pi * PH), (len(signs), N)).copy()
    vals = np.array(signs)[:, None] * ref + noise * rng.standard_normal(ref.shape)
    return vals, ref


@pytest.mark.parametrize("signs,expected", [
    ([1] * 4, None),              # 4 voting units < 5
    ([1] * 5, 1),                 # exactly 5
    ([1] * 9 + [-1], 1),          # 90 % agreement
    ([-1] * 9 + [1], -1),
    ([1] * 8 + [-1] * 2, None),   # 80 % < 90 %
])
def test_vote_thresholds(signs, expected):
    vals, ref = _units(signs)
    assert sod.reference_angle_test("hip_angle", vals, ref).sign == expected


def test_offset_flag_rule_and_ci_width():
    rng = np.random.default_rng(77)
    n, sigma = 40, 0.03
    ref = np.broadcast_to(0.3 * np.sin(2 * np.pi * PH), (n, N)).copy()
    for true_off, flagged in ((0.06, True), (0.02, False), (-0.06, True)):
        unit_off = true_off + sigma * rng.standard_normal((n, 1))
        ev = sod.reference_angle_test("hip_angle", ref + unit_off, ref)
        o = ev.offset
        assert o["applied"] is False and o["flag_for_review"] is flagged
        assert o["ci95"][0] <= true_off <= o["ci95"][1]
        # Asymptotic width of a 95 % CI for a median: 2 * 1.96 * 1.2533 sigma / sqrt(n).
        expect = 2 * 1.96 * 1.2533 * sigma / np.sqrt(n)
        assert 0.5 * expect < o["ci95"][1] - o["ci95"][0] < 1.6 * expect
    ev2 = sod.reference_angle_test("hip_angle", ref + 0.06, ref)
    assert ev2.offset == sod.reference_angle_test("hip_angle", ref + 0.06, ref).offset


def test_offsets_never_applied_and_only_apply_signs_change_data():
    g = _gait()
    ref = {"hip_angle": g["hip_angle"], "knee_angle": g["knee_angle"]}
    src = {"hip_angle": g["hip_angle"] + 0.1, "knee_angle": -g["knee_angle"] + 0.1,
           "ankle_angle": -g["ankle_angle"]}
    rep = sod.detect_leg("VERIFY-synthetic", "left", src, reference_angles=ref,
                         documentation=[("ankle_angle", -1, "synthetic statement")],
                         templates={"ankle_angle": (g["ankle_angle"].mean(0), "synthetic")},
                         task="level_walking")
    ch = rep["channels"]
    assert ch["hip_angle"]["offset"]["flag_for_review"] is True
    out, _ = sod.apply_signs(src, rep)
    np.testing.assert_array_equal(out["hip_angle"], src["hip_angle"])  # offset kept
    np.testing.assert_array_equal(out["knee_angle"], -src["knee_angle"])
    # Documentation and template agree on the ankle, yet neither may apply a sign.
    assert ch["ankle_angle"]["verdict"] == "abstain" and not ch["ankle_angle"]["sign_applied"]
    np.testing.assert_array_equal(out["ankle_angle"], src["ankle_angle"])


def test_moderate_dissent_blocks_strong_and_weak_dissent_does_not():
    E = sod.Evidence
    assert sod.combine([E("a", "c", "strong", 1), E("b", "c", "moderate", -1)])["verdict"] == "conflict"
    assert sod.combine([E("a", "c", "strong", 1), E("b", "c", "strong", -1)])["verdict"] == "conflict"
    # Round 3 rule (coordinator): no sign from a single test; apply needs agreeing tests
    # from >= 2 evidence families. One strong test (any weak dissent) is suggest only.
    v = sod.combine([E("reference_angle:marker", "c", "strong", 1), E("template", "c", "weak", -1)])
    assert v["verdict"] == "suggest" and v["sign"] == 1
    v = sod.combine([E("reference_angle:marker", "c", "strong", 1),
                     E("knee_hinge_asymmetry", "c", "moderate", 1), E("template", "c", "weak", -1)])
    assert v["verdict"] == "apply" and v["confidence"] == "medium"
    assert sod.combine([E("b", "c", "moderate", 1)])["verdict"] == "suggest"
    assert sod.combine([E("d", "c", "documentation", 1), E("t", "c", "weak", 1)])["verdict"] == "abstain"


def test_360_wrapped_storage_does_not_create_offset():
    g = _gait(seed=4)
    src = {"ankle_angle": np.mod(g["ankle_angle"], 2 * np.pi)}
    rep = sod.detect_leg("VERIFY-wrap", "right", src, reference_angles={"ankle_angle": g["ankle_angle"]})
    c = rep["channels"]["ankle_angle"]
    assert c["sign"] == 1 and abs(c["offset"]["estimate"]) < 0.01
    assert c["offset"]["flag_for_review"] is False


# --------------------------------------------- documented defects (xfail)
def test_lever_arm_alone_must_not_apply_in_mirrored_plate_frame():
    n_units = 12
    x = np.clip(PH / 0.6, 0, 1)
    stance = np.broadcast_to(PH < 0.6, (n_units, N)).copy()
    fy = np.where(stance, 9.81 * np.sin(np.pi * x), 0.0)
    fx = np.where(stance, -1.5 * np.sin(2 * np.pi * x), 0.0)
    grf = np.broadcast_to(np.stack([fx, fy], -1), (n_units, N, 2)).copy()
    ankle = np.zeros((n_units, N, 2)); ankle[..., 1] = 0.08
    cop = ankle + np.stack([np.broadcast_to(-0.06 + 0.22 * x, (n_units, N)),
                            np.full((n_units, N), -0.08)], -1)
    m_true = -_ccw_z(cop - ankle, grf) + 0.02 * np.random.default_rng(6).standard_normal((n_units, N))
    flip = np.array([-1.0, 1.0])  # plate frame forward axis reversed relative to the markers
    rep = sod.detect_leg("VERIFY-mirrored-plate", "right", {"ankle_moment": m_true},
                         joint_positions={"ankle": ankle * flip}, cop=cop * flip, grf=grf * flip,
                         task=None)
    c = rep["channels"]["ankle_moment"]
    assert not (c["verdict"] == "apply" and c["sign"] == -1)


def test_no_derivation_from_conflicted_channel():
    g = _gait(seed=8)
    pelvis = 0.03 * np.sin(4 * np.pi * PH) + np.zeros_like(g["hip_angle"]) - 0.1
    thigh = pelvis + g["hip_angle"]
    shank = thigh - g["knee_angle"]  # rule B: knee flexion swings the shank back
    src = {"pelvis_tilt": pelvis, "hip_angle": g["hip_angle"], "thigh_angle": thigh,
           "shank_angle": shank, "knee_angle": g["knee_angle"]}
    # A faulty reference makes hip apply with the wrong sign; the chain then contradicts
    # thigh and hip. Shank must not inherit a sign from the conflicted thigh.
    ref = {"thigh_angle": thigh, "hip_angle": -g["hip_angle"], "pelvis_tilt": pelvis}
    rep = sod.detect_leg("VERIFY-propagation", "right", src, reference_angles=ref)
    ch = rep["channels"]
    assert ch["thigh_angle"]["verdict"] == "conflict"
    assert ch["shank_angle"]["verdict"] != "apply"


def test_inverted_up_vector_is_detected():
    sag = {"hip": np.array([0.0, 0.92]), "knee": np.array([0.12, 0.5]),
           "ankle": np.array([0.02, 0.08]), "heel": np.array([-0.05, 0.02]),
           "toe": np.array([0.17, 0.03])}
    lab = {k: np.array([v[0], 0.1, v[1]]) for k, v in sag.items()}
    wrong_up = np.array([0, 0, -1.0])
    try:
        fwd = sod.forward_axis(lab["heel"], lab["toe"], wrong_up)
        proj = {k: sod.project_sagittal(v, fwd, wrong_up) for k, v in lab.items()}
        got = sod.marker_reference_angles(proj)
    except ValueError:
        return
    base = sod.marker_reference_angles(sag)
    assert np.sign(got["knee_angle"]) == np.sign(base["knee_angle"])


# ------------------------------------- round 2 documented defects (xfail)
def _plate(cop_path, fx_sign=1.0, n_units=12, seed=21):
    x = np.clip(PH / 0.6, 0, 1)
    stance = PH < 0.6
    fy = np.where(stance, 9.81 * (np.sin(np.pi * x) + 0.02), 0.0)
    fx = np.where(stance, -fx_sign * 1.5 * np.sin(2 * np.pi * x), 0.0)
    grf = np.broadcast_to(np.stack([fx, fy], -1), (n_units, N, 2)).copy()
    ankle = np.zeros((n_units, N, 2)); ankle[..., 1] = 0.08
    cop = ankle + np.stack([np.broadcast_to(cop_path(x), (n_units, N)),
                            np.full((n_units, N), -0.08)], -1)
    m = -_ccw_z(cop - ankle, grf) + 0.02 * np.random.default_rng(seed).standard_normal((n_units, N))
    return m, ankle, cop, grf


@pytest.mark.parametrize("label,cop_path,fx_sign,task", [
    ("backward walking", lambda x: 0.16 - 0.22 * x, -1.0, "backward_walking"),
    ("toe walking, atypical population", lambda x: 0.13 - 0.04 * np.sin(np.pi * x / 1.2), 1.0, None),
])
def test_mirrored_plate_frame_not_applied_when_cop_moves_toe_to_heel(label, cop_path, fx_sign, task):
    m, ankle, cop, grf = _plate(cop_path, fx_sign)
    flip = np.array([-1.0, 1.0])
    rep = sod.detect_leg("VERIFY-r2-" + label, "right", {"ankle_moment": m},
                         joint_positions={"ankle": ankle * flip}, cop=cop * flip, grf=grf * flip,
                         task=task)
    c = rep["channels"]["ankle_moment"]
    assert not (c["verdict"] == "apply" and c["sign"] == -1)  # truth: target = +1 * source


def test_every_contradicting_relation_is_honoured():
    rng = np.random.default_rng(31)
    pel = -0.1 + 0.03 * np.sin(4 * np.pi * PH) + 0.002 * rng.standard_normal((20, N))
    hip = 0.2 + 0.35 * np.cos(2 * np.pi * PH) + 0.004 * rng.standard_normal((20, N))
    thigh = pel + hip
    # Faulty pelvis and hip references: both chain pairs contradict the applied signs.
    rep = sod.detect_leg("VERIFY-r2-two-contradictions", "right",
                         {"pelvis_tilt": pel, "hip_angle": hip, "thigh_angle": thigh},
                         reference_angles={"pelvis_tilt": -pel, "hip_angle": -hip,
                                           "thigh_angle": thigh})
    assert all(c["verdict"] != "apply" for c in rep["channels"].values())


def test_inverted_up_with_pelvis_only_markers_is_not_applied():
    rear = np.array([-0.12, 1.0]) + np.zeros((10, N, 2))
    front = np.array([0.12, 0.96]) + np.zeros((10, N, 2))
    front[..., 1] += 0.01 * np.sin(4 * np.pi * PH)
    truth = sod.marker_reference_angles({"pelvis_rear": rear, "pelvis_front": front})["pelvis_tilt"]
    inverted = {"pelvis_rear": rear * [1, -1.0], "pelvis_front": front * [1, -1.0]}
    rep = sod.detect_leg("VERIFY-r2-pelvis-only", "right", {"pelvis_tilt": truth},
                         marker_points=inverted)
    c = rep["channels"]["pelvis_tilt"]
    assert not (c["verdict"] == "apply" and c["sign"] == -1)


def test_source_equal_to_reference_near_pi_gives_plus_one():
    rng = np.random.default_rng(41)
    seg = np.pi - 0.05 + 0.1 * np.sin(2 * np.pi * PH) + 0.003 * rng.standard_normal((20, N))
    w = (seg + np.pi) % (2 * np.pi) - np.pi
    rep = sod.detect_leg("VERIFY-r2-near-pi", "right", {"thigh_angle": w},
                         reference_angles={"thigh_angle": w})
    c = rep["channels"]["thigh_angle"]
    assert c["verdict"] != "apply" or c["sign"] == 1


def test_no_apply_with_half_turn_offset():
    rng = np.random.default_rng(43)
    true = 0.1 * np.sin(2 * np.pi * PH) + 0.003 * rng.standard_normal((20, N))
    src = true.copy()
    src[:12] = np.pi - true[:12]
    rep = sod.detect_leg("VERIFY-r2-branch-majority", "right", {"ankle_angle": src},
                         reference_angles={"ankle_angle": true})
    c = rep["channels"]["ankle_angle"]
    assert c["verdict"] != "apply"


# ------------------------------------- phase 3 (rule B, D-CORE-04-1 = C) documented defect
def _planar_leg(n_units=20, seed=51):
    """Synthetic rule-B leg: hip (with a 2nd harmonic), knee flexion in swing, markers."""
    rng = np.random.default_rng(seed)
    a = 1 + 0.05 * rng.standard_normal((n_units, 1))
    pelvis = -0.17 + 0.0 * PH + np.zeros((n_units, 1))
    hip = 0.15 + 0.35 * a * np.cos(2 * np.pi * PH) + 0.05 * np.sin(4 * np.pi * PH)
    knee = 0.1 + 1.0 * a * np.exp(-0.5 * ((PH - 0.72) / 0.09) ** 2)  # flexion positive
    thigh = pelvis + hip
    shank = thigh - knee
    down = lambda t: np.stack([np.sin(t), -np.cos(t)], -1)
    hip_pt = np.zeros((n_units, N, 2)); hip_pt[..., 1] = 0.92
    knee_pt = hip_pt + 0.45 * down(thigh)
    ankle_pt = knee_pt + 0.43 * down(shank)
    u_p = np.stack([np.cos(pelvis), np.sin(pelvis)], -1)
    pts = {"pelvis_rear": hip_pt - 0.12 * u_p + [0, 0.05], "pelvis_front": hip_pt + 0.12 * u_p + [0, 0.05],
           "hip": hip_pt, "knee": knee_pt, "ankle": ankle_pt}
    stance = np.broadcast_to(PH < 0.6, (n_units, N)).copy()
    return hip + 0.004 * rng.standard_normal(hip.shape), knee, pts, stance


def test_hip_column_from_other_leg_is_not_applied():
    hip, knee, pts, stance = _planar_leg()
    other_leg = np.roll(hip, N // 2, axis=1)  # the source column belongs to the other leg
    rep = sod.detect_leg("VERIFY-p3-leg-swapped-hip", "right",
                         {"hip_angle": other_leg, "knee_angle": knee},
                         marker_points=pts, stance=stance, task="level_walking")
    c = rep["channels"]["hip_angle"]
    assert c["verdict"] != "apply"
