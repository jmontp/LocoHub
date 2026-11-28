"""Synthetic fixtures for the CORE-04 sign and offset detector.

Every waveform here is SYNTHETIC: smooth gait-like curves generated in the
LocoHub rule-B convention (segments counterclockwise positive, so pelvis
anterior tilt negative; joint angles and internal moments positive in their
named direction, so knee flexion and knee flexor moment positive), then
corrupted with KNOWN sign flips, offsets,
180-degree branch episodes and missing force plates. Synthetic stance moments
are quasi-static GRF moments plus an unmodelled disturbance standing in for
segment inertia; they test sign recovery and abstention, not inverse dynamics.
No research dataset is read.
"""
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from contributor_tools.common import sign_offset_detector as sod

N = 150
PHASE = np.linspace(0.0, 1.0, N)
STRIDE_S = 1.1
DT = STRIDE_S / (N - 1)
STANCE_END = 0.6


def _bump(phase, centre, width):
    d = (phase - centre + 0.5) % 1.0 - 0.5
    return np.exp(-0.5 * (d / width) ** 2)


# Winter (2009) Table 4.1 (typed here independently of the module): mass fraction,
# COM from the proximal end, radius of gyration about the COM, as fractions.
WINTER = {"thigh": (0.100, 0.433, 0.323), "shank": (0.0465, 0.433, 0.302), "foot": (0.0145, 0.50, 0.475)}


def free_body_hip_moment(P, cop, grf, dt):
    """Internal hip moment per kg on the thigh (counterclockwise = rule-B flexor +) from the
    whole-leg angular momentum balance about a FIXED hip:
    M_hip = sum_i [I_i alpha_i + m_i (c_i - hip) x (a_i - g)] - (CoP - hip) x GRF.
    A different formula from the module's segment-by-segment recursion."""
    cross = lambda a, b: a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]
    g = np.array([0.0, -9.81])
    total = -cross(cop - P["hip"], grf)
    for name, (prox, dist) in (("thigh", ("hip", "knee")), ("shank", ("knee", "ankle")),
                               ("foot", ("heel", "toe"))):
        m, f, rho = WINTER[name]
        v = P[dist] - P[prox]
        length = np.mean(np.hypot(v[..., 0], v[..., 1]), axis=1, keepdims=True)
        c = P[prox] + f * v
        th = np.unwrap(np.arctan2(v[..., 1], v[..., 0]), axis=1)
        alpha = np.gradient(np.gradient(th, dt, axis=1), dt, axis=1)
        acc = np.gradient(np.gradient(c, dt, axis=1), dt, axis=1)
        total = total + m * (rho * length) ** 2 * alpha + m * cross(c - P["hip"], acc - g)
    return total


def synthetic_leg(n_units=24, seed=7, marker_noise_m=0.001, angle_noise_rad=0.005,
                  hip2=0.0, fx_peak=1.5):
    """hip2: amplitude of a 2nd-harmonic hip term (0 = pure cosine hip, which is
    half-cycle antisymmetric); fx_peak: braking/propulsion peak in N/kg."""
    """Rule-B truth for one leg: angles, markers (sagittal), GRF/CoP, moments, power."""
    rng = np.random.default_rng(seed)
    out = {k: np.zeros((n_units, N)) for k in (
        "pelvis_tilt", "hip_angle", "knee_angle", "ankle_angle")}
    for u in range(n_units):
        a = 1 + 0.05 * rng.standard_normal()
        ph = (PHASE + 0.01 * rng.standard_normal()) % 1.0
        out["pelvis_tilt"][u] = -0.17 + 0.03 * a * np.sin(4 * np.pi * ph)
        out["hip_angle"][u] = (0.15 + 0.35 * a * np.cos(2 * np.pi * ph)
                               + hip2 * np.cos(4 * np.pi * ph + 1.0))
        out["knee_angle"][u] = (0.05 + 0.3 * a * _bump(ph, 0.15, 0.06)
                                + 1.05 * a * _bump(ph, 0.72, 0.09))  # flexion positive
        out["ankle_angle"][u] = (0.03 + 0.15 * a * _bump(ph, 0.45, 0.10)
                                 - 0.40 * a * _bump(ph, 0.63, 0.05)
                                 - 0.05 * _bump(ph, 0.10, 0.04))
    out["thigh_angle"] = out["pelvis_tilt"] + out["hip_angle"]
    out["shank_angle"] = out["thigh_angle"] - out["knee_angle"]  # flexion swings the shank back
    out["foot_angle"] = out["shank_angle"] + out["ankle_angle"]

    def vec(t):
        return np.stack([np.sin(t), -np.cos(t)], axis=-1)
    hip = np.zeros((n_units, N, 2))
    hip[..., 1] = 0.92
    knee = hip + 0.45 * vec(out["thigh_angle"])
    ankle = knee + 0.43 * vec(out["shank_angle"])
    f = out["foot_angle"]
    u_f = np.stack([np.cos(f), np.sin(f)], -1)
    n_f = np.stack([-np.sin(f), np.cos(f)], -1)
    p = out["pelvis_tilt"]
    u_p = np.stack([np.cos(p), np.sin(p)], -1)
    n_p = np.stack([-np.sin(p), np.cos(p)], -1)
    pts = {"hip": hip, "knee": knee, "ankle": ankle,
           "heel": ankle - 0.06 * u_f - 0.07 * n_f, "toe": ankle + 0.16 * u_f - 0.07 * n_f,
           "pelvis_rear": hip - 0.12 * u_p + 0.05 * n_p,
           "pelvis_front": hip + 0.12 * u_p + 0.05 * n_p}
    exact = dict(pts)
    pts = {k: v + marker_noise_m * rng.standard_normal(v.shape) for k, v in pts.items()}

    stance = np.broadcast_to(PHASE < STANCE_END, (n_units, N)).copy()
    x = np.clip(PHASE / STANCE_END, 0, 1)
    fy = np.where(stance, 9.81 * (np.sin(np.pi * x) + 0.25 * np.sin(3 * np.pi * x)), 0.0)
    # Braking then propulsion, peak 1.5 N/kg (0.15 BW, within the usual 0.15-0.2 BW).
    fx = np.where(stance, -fx_peak * np.sin(2 * np.pi * x), 0.0)
    grf = np.stack([np.broadcast_to(fx, (n_units, N)), np.broadcast_to(fy, (n_units, N))], -1)
    cop = ankle + np.stack([np.broadcast_to(-0.05 + 0.20 * x, (n_units, N)),
                            np.full((n_units, N), -0.08)], -1)
    disturbance = {"ankle": 0.08, "knee": 0.15}
    for j, pos in (("ankle", ankle), ("knee", knee), ("hip", hip)):
        r = cop - pos
        lever = -(r[..., 0] * grf[..., 1] - r[..., 1] * grf[..., 0])  # counterclockwise on distal segment
        lever = (-1 if j == "knee" else 1) * lever  # rule B: knee flexor positive
        if j == "hip":  # dynamically consistent hip moment (segment inertia and weight included)
            m = free_body_hip_moment(exact, cop, grf, DT)
        else:
            m = np.where(stance, lever, 0.0) + disturbance[j] * np.sin(2 * np.pi * PHASE + 1.3)
        out[f"{j}_moment"] = m + 0.03 * rng.standard_normal((n_units, N))
        omega = np.gradient(out[f"{j}_angle"], axis=1) / DT
        out[f"{j}_power"] = out[f"{j}_moment"] * omega
    for k in ("pelvis_tilt", "hip_angle", "knee_angle", "ankle_angle",
              "thigh_angle", "shank_angle", "foot_angle"):
        out[k] = out[k] + angle_noise_rad * rng.standard_normal((n_units, N))
    return out, pts, {"hip": hip, "knee": knee, "ankle": ankle}, cop, grf, stance


# Injected source conventions, target = sign * source: a synthetic source with pelvis
# anterior tilt positive, knee flexion negative and knee extensor moment positive.
INJECTED_SIGNS = {"pelvis_tilt": -1, "knee_angle": -1, "knee_moment": -1}
ANKLE_OFFSET = np.deg2rad(5.0)


def injected_source(truth):
    src = {}
    for k in ("pelvis_tilt", "hip_angle", "knee_angle", "ankle_angle",
              "hip_moment", "knee_moment", "ankle_moment"):
        src[k] = INJECTED_SIGNS.get(k, 1) * truth[k]
    src["ankle_angle"] = src["ankle_angle"] + ANKLE_OFFSET  # known offset
    for j in sod.JOINTS:
        src[f"{j}_power"] = -truth[f"{j}_power"]  # stored as -(M x w), like UM21 layout 1
    src["ankle_angle"][[3, 7], 60:81] += np.pi  # known 180-degree branch episodes
    return src


def _injected_report(grouping="coarse"):
    truth, pts, joints, cop, grf, stance = synthetic_leg()
    ref = sod.marker_reference_angles(pts)
    src = injected_source(truth)
    rep = sod.detect_leg("SYNTH-injected", "right", src, reference_angles=ref,
                         joint_positions=joints, cop=cop, grf=grf, dt=DT,
                         task="level_walking", grf_unit="N_per_kg",
                         params={"family_grouping": grouping})
    return rep, src, truth


@pytest.fixture(scope="module")
def full_report():
    return _injected_report("coarse")  # option only; default is "fine"


def test_default_grouping_is_failure_mode():
    assert sod.DEFAULTS["family_grouping"] == "fine"


@pytest.fixture(scope="module")
def fine_report():
    return _injected_report("fine")


EXPECTED_ANGLE_SIGNS = {"pelvis_tilt": -1, "hip_angle": 1, "knee_angle": -1, "ankle_angle": 1}


def test_coarse_families_apply_only_cross_family_angles(full_report):
    # Coarse option: the ankle angle has kinematic + force-plate (plate-timed) evidence and
    # applies. The pure-cosine hip is half-cycle ambiguous, so markers and plate timing count
    # as one family for it; pelvis and knee angles have kinematic evidence only.
    ch = full_report[0]["channels"]
    assert ch["ankle_angle"]["verdict"] == "apply" and ch["ankle_angle"]["sign"] == 1
    for k in ("pelvis_tilt", "hip_angle", "knee_angle"):
        assert ch[k]["verdict"] == "suggest" and ch[k]["sign"] == EXPECTED_ANGLE_SIGNS[k]
    assert "half-cycle ambiguous" in ch["hip_angle"]["reason"]
    assert {k for k, c in ch.items() if c["sign_applied"]} == {"ankle_angle"}


def test_fine_families_apply_two_family_channels(fine_report):
    ch = fine_report[0]["channels"]
    applied = {k: c["sign"] for k, c in ch.items() if c["sign_applied"]}
    assert applied == {"knee_angle": -1, "ankle_angle": 1, "ankle_moment": 1, "ankle_power": -1}
    assert ch["pelvis_tilt"]["verdict"] == "suggest" and ch["pelvis_tilt"]["sign"] == -1
    assert ch["hip_angle"]["verdict"] == "suggest" and ch["hip_angle"]["sign"] == 1


def test_ankle_offset_estimated_and_flagged_not_applied(full_report):
    rep, src, truth = full_report
    off = rep["channels"]["ankle_angle"]["offset"]
    assert off["applied"] is False and off["flag_for_review"] is True
    assert off["ci95"][0] <= ANKLE_OFFSET <= off["ci95"][1]
    assert abs(off["estimate"] - ANKLE_OFFSET) < np.deg2rad(0.5)
    assert rep["channels"]["hip_angle"]["offset"]["flag_for_review"] is False
    corrected, _ = sod.apply_signs(src, rep)
    finite = np.isfinite(corrected["ankle_angle"]) & (np.abs(corrected["ankle_angle"]) < 2)
    resid = (corrected["ankle_angle"] - truth["ankle_angle"])[finite]
    assert abs(np.median(resid) - ANKLE_OFFSET) < 0.01  # offset left in the data


def test_branch_episodes_masked_and_reported(full_report):
    rep, _, _ = full_report
    br = rep["channels"]["ankle_angle"]["branch_screen"]
    assert br["branch_180_frames"] == 2 * 21
    assert [r[0] for r in br["runs_unit_start_stop"]] == [3, 7]
    assert br["runs_unit_start_stop"][0][1:] == [60, 81]
    assert rep["channels"]["knee_angle"]["branch_screen"] is None


def test_ankle_moment_from_force_plates(full_report):
    ch = full_report[0]["channels"]["ankle_moment"]
    assert ch["verdict"] == "suggest" and ch["sign"] == 1 and ch["confidence"] == "medium"
    tests = {e["test"] for e in ch["evidence"] if e["sign"] == 1}
    assert {"lever_arm", "late_stance_plantarflexor"} <= tests
    assert full_report[0]["plate_frame_check"]["cop_progression"]["result"] == "pass"


def test_knee_moment_suggested_only_and_hip_not_applied(full_report):
    ch = full_report[0]["channels"]
    assert ch["knee_moment"]["verdict"] == "suggest" and ch["knee_moment"]["sign"] == -1
    assert ch["knee_moment"]["sign_applied"] is False
    assert ch["hip_moment"]["sign_applied"] is False


def test_ankle_power_applies_from_identity_plus_push_off_timing(fine_report):
    rep = fine_report[0]
    rel = [r for r in rep["relations"] if r["test"] == "power_identity"
           and r["channels"][0] == "ankle_moment"][0]
    assert rel["product"] == -1  # source power stored as -(M x w)
    c = rep["channels"]["ankle_power"]
    assert c["verdict"] == "apply" and c["sign"] == -1
    assert {e["test"] for e in c["evidence"] if e["sign"] == -1} == {
        "power_timing", "derived:power_identity"}


def test_missing_force_plates_abstain():
    truth, *_ = synthetic_leg(seed=11)
    src = {k: truth[k] for k in ("hip_angle", "knee_angle", "ankle_angle",
                                 "hip_moment", "knee_moment", "ankle_moment")}
    rep = sod.detect_leg("SYNTH-no-plates", "left", src, task="level_walking")
    ch = rep["channels"]
    for k in ("hip_moment", "knee_moment", "ankle_moment", "hip_angle", "ankle_angle"):
        assert ch[k]["verdict"] == "abstain", k
        assert ch[k]["sign_applied"] is False
    reasons = {e["reason"] for e in ch["ankle_moment"]["evidence"]}
    assert "no force plate (GRF/CoP) data" in reasons
    # The knee hinge test alone is moderate: suggested, never applied.
    assert ch["knee_angle"]["verdict"] == "suggest" and ch["knee_angle"]["sign"] == 1
    assert ch["knee_angle"]["offset"]["estimate"] is None


def test_pelvis_abstains_when_excursion_is_within_marker_noise():
    # Pelvis tilt moves about +/-2 deg; 5 mm marker noise on a 24 cm baseline hides it.
    truth, pts, *_ = synthetic_leg(seed=19, marker_noise_m=0.005)
    rep = sod.detect_leg("SYNTH-noisy-pelvis", "right", {"pelvis_tilt": -truth["pelvis_tilt"]},
                         reference_angles=sod.marker_reference_angles(pts))
    assert rep["channels"]["pelvis_tilt"]["verdict"] == "abstain"


def test_knee_hinge_abstains_outside_walking():
    truth, *_ = synthetic_leg(seed=12)
    ev = sod.knee_hinge_test(truth["knee_angle"], "jump")
    assert ev.sign is None and "not a walking task" in ev.reason


def test_noise_channel_abstains():
    truth, pts, *_ = synthetic_leg(seed=13)
    noise = np.random.default_rng(99).standard_normal((24, N)) * 0.2
    rep = sod.detect_leg("SYNTH-noise", "right", {"hip_angle": noise},
                         reference_angles=sod.marker_reference_angles(pts),
                         task="level_walking")
    assert rep["channels"]["hip_angle"]["verdict"] == "abstain"


def test_template_alone_is_weak_and_never_applied():
    truth, *_ = synthetic_leg(seed=14)
    tmpl = truth["ankle_angle"].mean(axis=0)
    rep = sod.detect_leg("SYNTH-template", "right", {"ankle_angle": -truth["ankle_angle"]},
                         templates={"ankle_angle": (tmpl, "synthetic mean, not literature")})
    ch = rep["channels"]["ankle_angle"]
    assert ch["verdict"] == "abstain" and ch["weak_hint"] == -1
    assert ch["sign_applied"] is False


def test_documentation_disagreeing_with_data_is_conflict():
    # GT24-like: README says plantarflexion positive, data say dorsiflexion positive.
    truth, pts, *_ = synthetic_leg(seed=15)
    rep = sod.detect_leg("SYNTH-doc-conflict", "left", {"ankle_angle": truth["ankle_angle"]},
                         reference_angles=sod.marker_reference_angles(pts),
                         documentation=[("ankle_angle", -1, "synthetic README: PF positive")])
    ch = rep["channels"]["ankle_angle"]
    assert ch["verdict"] == "conflict" and ch["sign_applied"] is False


def test_segment_chain_relations_recover_relative_signs():
    truth, *_ = synthetic_leg(seed=16)
    src = {"thigh_angle": truth["thigh_angle"], "pelvis_tilt": -truth["pelvis_tilt"],
           "hip_angle": truth["hip_angle"]}
    rels = sod.chain_relation("thigh_angle", "pelvis_tilt", "hip_angle", src)
    assert [(r.channels, r.product) for r in rels] == [
        (("thigh_angle", "pelvis_tilt"), -1), (("thigh_angle", "hip_angle"), 1)]


def test_derivation_from_an_applied_anchor_alone_only_suggests():
    E, R = sod.Evidence, sod.Relation
    ev = {"thigh_angle": [], "pelvis_tilt": [], "hip_angle": []}
    verdicts = {"thigh_angle": {"verdict": "apply", "sign": 1, "confidence": "medium"},
                "pelvis_tilt": sod.combine([]), "hip_angle": sod.combine([])}
    rels = [R("segment_chain", ("thigh_angle", "pelvis_tilt"), "strong", -1),
            R("segment_chain", ("thigh_angle", "hip_angle"), "strong", 1)]
    out = sod._propagate(verdicts, ev, rels)
    assert out["pelvis_tilt"]["verdict"] == "suggest" and out["pelvis_tilt"]["sign"] == -1
    assert out["hip_angle"]["verdict"] == "suggest" and out["hip_angle"]["sign"] == 1


def test_lab_frame_projection_independent_of_heading_and_handedness():
    # Person walks along lab -Z with +Y up (GT21-like); lateral axis is lab X.
    truth, pts, *_ = synthetic_leg(seed=17, n_units=6)
    for lateral_sign in (1, -1):  # right- and left-handed lab
        lab = {k: np.stack([lateral_sign * 0.1 * np.ones(v.shape[:-1]), v[..., 1], -v[..., 0]], -1)
               for k, v in pts.items()}
        up = np.array([0.0, 1.0, 0.0])
        fwd = sod.forward_axis(lab["heel"], lab["toe"], up)
        assert np.allclose(fwd, [0, 0, -1], atol=0.02)
        sag = {k: sod.project_sagittal(v, fwd, up) for k, v in lab.items()}
        ref = sod.marker_reference_angles(sag)
        assert np.median(np.abs(ref["knee_angle"] - truth["knee_angle"])) < 0.03


def test_cardan_alternate_branch_identity_and_detection():
    rng = np.random.default_rng(20261030)
    c = np.column_stack([rng.uniform(-30, 30, 200), rng.uniform(-20, 20, 200),
                         rng.uniform(-40, 40, 200)])
    alt = np.column_stack(sod.reexpress_alternate(*c.T))
    assert sod.alternate_branch_frames(*alt.T).all()
    assert not sod.alternate_branch_frames(*c.T).any()
    r1 = Rotation.from_euler("ZXY", c, degrees=True).as_matrix()
    r2 = Rotation.from_euler("ZXY", alt, degrees=True).as_matrix()
    assert np.max(np.abs(r1 - r2)) < 1e-12  # independent check via scipy
    back = np.column_stack(sod.reexpress_alternate(*alt.T))
    assert np.allclose(back, c, atol=1e-9)


def test_degree_units_block_the_reference_test():
    truth, pts, *_ = synthetic_leg(seed=18)
    ev = sod.reference_angle_test("hip_angle", np.rad2deg(truth["hip_angle"]),
                                  sod.marker_reference_angles(pts)["hip_angle"])
    assert ev.sign is None and "units mismatch" in ev.reason
    assert ev.stats["scale_review"] is True


def test_report_is_deterministic(full_report):
    assert _injected_report("coarse")[0] == full_report[0]


# ---- CORE-04 verification round 1 fixes (synthetic) ----
@pytest.mark.parametrize("order", ["contradiction_first", "derivation_first"])
def test_propagation_resolves_contradictions_before_deriving(order):
    E, R = sod.Evidence, sod.Relation
    ev = {"thigh_angle": [E("ref", "thigh_angle", "strong", 1)],
          "hip_angle": [E("ref", "hip_angle", "strong", -1)],
          "shank_angle": []}
    verdicts = {k: sod.combine(v) for k, v in ev.items()}  # suggest (one family each)
    contra = R("segment_chain", ("thigh_angle", "hip_angle"), "strong", 1)
    derive = R("segment_chain", ("shank_angle", "thigh_angle"), "strong", 1)
    rels = [contra, derive] if order == "contradiction_first" else [derive, contra]
    out = sod._propagate(verdicts, ev, rels)
    assert out["thigh_angle"]["verdict"] == "conflict"
    assert out["hip_angle"]["verdict"] == "conflict"
    assert out["shank_angle"]["verdict"] == "abstain"


def test_lever_arm_without_frame_check_cannot_apply_alone():
    truth, pts, joints, cop, grf, stance = synthetic_leg(seed=21)
    # No ankle positions -> CoP progression unknown -> ankle lever arm is moderate.
    # Checked under the old single-test rule (min_families=1) so the frame gate is tested.
    rep = sod.detect_leg("SYNTH-no-frame", "right", {"knee_moment": truth["knee_moment"],
                                                     "ankle_moment": truth["ankle_moment"]},
                         joint_positions={"knee": joints["knee"]}, cop=cop, grf=grf, task=None,
                         grf_unit="N_per_kg", params={"min_families": 1})
    assert rep["plate_frame_check"]["cop_progression"]["result"] == "unknown"
    assert rep["channels"]["ankle_moment"]["sign_applied"] is False


def test_marker_points_record_vertical_order_and_refuse_inverted_up():
    truth, pts, *_ = synthetic_leg(seed=22)
    ok = sod.detect_leg("SYNTH-markers", "right", {"hip_angle": truth["hip_angle"]},
                        marker_points=pts)
    assert ok["marker_checks"]["result"] == "pass"
    assert ok["channels"]["hip_angle"]["verdict"] == "suggest"
    assert ok["channels"]["hip_angle"]["sign"] == 1
    flipped = {k: v * np.array([1.0, -1.0]) for k, v in pts.items()}  # up inverted
    bad = sod.detect_leg("SYNTH-markers-flipped", "right", {"hip_angle": truth["hip_angle"]},
                         marker_points=flipped)
    assert bad["marker_checks"]["result"] == "fail"
    assert bad["channels"]["hip_angle"]["verdict"] == "abstain"


def test_degree_input_is_refused_not_fitted():
    truth, pts, *_ = synthetic_leg(seed=23)
    rep = sod.detect_leg("SYNTH-degrees", "right", {"knee_angle": np.rad2deg(truth["knee_angle"])},
                         reference_angles=sod.marker_reference_angles(pts), task="level_walking")
    ch = rep["channels"]["knee_angle"]
    assert ch["verdict"] == "abstain" and ch["evidence"][0]["test"] == "units_check"


def test_deep_flexion_is_not_a_branch():
    # Synthetic squat-like knee: standing near 0, continuous flexion to 125 deg.
    rng = np.random.default_rng(24)
    knee = -np.deg2rad(125) * _bump(PHASE, 0.5, 0.1)
    knee = np.broadcast_to(knee, (10, N)) + 0.003 * rng.standard_normal((10, N))
    _, mask, summary = sod.screen_branch(knee)
    assert not mask.any() and summary["branch_180_frames"] == 0
    assert summary["far_from_median_frames"] > 0


def test_stance_floor_rejects_contact_free_unit():
    rng = np.random.default_rng(25)
    grf_v = np.vstack([np.where(PHASE < STANCE_END, 9.81 * np.sin(np.pi * PHASE / STANCE_END), 0.0),
                       0.03 * np.abs(rng.standard_normal(N))])  # second unit: noise only (N/kg)
    st = sod.stance_from_grf(grf_v, "N_per_kg")
    assert 0.5 < st[0].mean() < 0.65
    assert not st[1].any()
    st_bw = sod.stance_from_grf(grf_v / 9.81, "BW")  # same data in body weights
    assert np.array_equal(st_bw, st)
    with pytest.raises(ValueError):
        sod.stance_from_grf(grf_v, None)


def test_undeclared_grf_unit_leaves_force_plate_tests_abstaining():
    truth, pts, joints, cop, grf, stance = synthetic_leg(seed=26)
    rep = sod.detect_leg("SYNTH-no-unit", "right", {"ankle_moment": truth["ankle_moment"]},
                         joint_positions=joints, cop=cop, grf=grf, task="level_walking")
    ch = rep["channels"]["ankle_moment"]
    assert ch["verdict"] == "abstain"
    assert all("not declared" in e["reason"] for e in ch["evidence"])


# ---- CORE-04 verification round 2 fixes (synthetic) ----
def test_apply_needs_two_families():
    E = sod.Evidence
    one = sod.combine([E("reference_angle:marker", "c", "strong", 1)])
    two = sod.combine([E("reference_angle:marker", "c", "strong", 1),
                       E("lever_arm", "c", "moderate", 1)])
    unknown = sod.combine([E("a", "c", "strong", 1), E("b", "c", "strong", 1)])
    same = sod.combine([E("reference_angle:marker", "c", "strong", 1),
                        E("derived:segment_chain", "c", "strong", 1)])  # both marker geometry
    assert one["verdict"] == "suggest" and same["verdict"] == "suggest"
    assert two["verdict"] == "apply" and two["families"] == ["marker_geometry", "plate_geometry"]
    coarse = sod.combine([E("reference_angle:marker", "c", "strong", 1),
                          E("knee_hinge_asymmetry", "c", "moderate", 1)], grouping="coarse")
    assert coarse["verdict"] == "suggest"  # one kinematic family under the coarse option
    assert unknown["verdict"] == "suggest"  # unclassified tests have no family


def test_cop_progression_check_only_for_forward_heel_strike_walking():
    truth, pts, joints, cop, grf, stance = synthetic_leg(seed=27)
    for task, expected in (("level_walking", "pass"), (None, "unknown"),
                           ("backward_walking", "unknown"), ("run", "unknown")):
        fc = sod.plate_frame_check(cop, joints["ankle"], grf, stance, task=task)
        assert fc["cop_progression"]["result"] == expected, task


def test_vertical_order_uses_foot_not_hip_over_knee():
    # Deep squat posture held for 60 frames: thigh past horizontal (knee above hip),
    # all above the ankle.
    one = {"hip": [0.0, 0.40], "knee": [0.45, 0.45], "ankle": [0.30, 0.08],
           "heel": [0.24, 0.02], "toe": [0.46, 0.02]}
    pts = {k: np.tile(v, (60, 1)) for k, v in one.items()}
    assert sod.vertical_order_fraction(pts) == 1.0
    assert sod.marker_reference_angles(pts).vertical_order["result"] == "pass"
    pelvis_only = {"pelvis_rear": np.array([[-0.12, 1.0]]), "pelvis_front": np.array([[0.12, 0.96]])}
    assert sod.marker_reference_angles(pelvis_only).vertical_order["result"] == "unknown"


def test_unknown_vertical_order_blocks_marker_references_passed_directly():
    rear = np.array([-0.12, 1.0]) + np.zeros((10, N, 2))
    front = np.array([0.12, 0.96]) + np.zeros((10, N, 2))
    front[..., 1] += 0.01 * np.sin(4 * np.pi * PHASE)
    ref = sod.marker_reference_angles({"pelvis_rear": rear, "pelvis_front": front})
    rep = sod.detect_leg("SYNTH-pelvis-only", "right", {"pelvis_tilt": np.array(ref["pelvis_tilt"])},
                         reference_angles=ref)
    assert rep["channels"]["pelvis_tilt"]["verdict"] == "abstain"
    assert rep["marker_checks"]["result"] == "unknown"


def test_reference_straddling_pi_and_half_turn_offset():
    rng = np.random.default_rng(28)
    seg = np.pi - 0.05 + 0.1 * np.sin(2 * np.pi * PHASE) + 0.003 * rng.standard_normal((20, N))
    w = (seg + np.pi) % (2 * np.pi) - np.pi
    ev = sod.reference_angle_test("thigh_angle", -w, w)
    assert ev.sign == -1 and abs(ev.offset["estimate"]) < 0.01
    true = 0.1 * np.sin(2 * np.pi * PHASE) + 0.003 * rng.standard_normal((20, N))
    rep = sod.detect_leg("SYNTH-half-turn", "right", {"ankle_angle": np.pi - true},
                         reference_angles={"ankle_angle": true}, params={"min_families": 1})
    ch = rep["channels"]["ankle_angle"]
    assert ch["verdict"] == "conflict" and "half-turn" in ch["reason"]


# ---- CORE-04 verification round 3 fixes (synthetic) ----
def test_conflicts_are_sticky_through_propagation():
    # Half-turn conflict on hip set before propagation; a chain derivation must not undo it.
    E, R = sod.Evidence, sod.Relation
    ev = {"thigh_angle": [], "hip_angle": [E("reference_angle:marker", "hip_angle", "strong", 1)]}
    verdicts = {"thigh_angle": {"verdict": "apply", "sign": 1, "confidence": "medium"},
                "hip_angle": {"verdict": "conflict", "sign": None, "confidence": "none",
                              "reason": "half-turn offset"}}
    out = sod._propagate(verdicts, ev, [R("segment_chain", ("thigh_angle", "hip_angle"),
                                           "strong", 1)], min_families=1)
    assert out["hip_angle"]["verdict"] == "conflict"
    assert out["hip_angle"]["reason"] == "half-turn offset"


def test_half_turn_conflict_survives_chain_derivation_in_detect_leg():
    # min_families=1 so thigh and pelvis apply from one test each and the chain derives hip.
    truth, pts, *_ = synthetic_leg(seed=31)
    ref = sod.marker_reference_angles(pts)
    src = {"thigh_angle": truth["thigh_angle"], "pelvis_tilt": truth["pelvis_tilt"],
           "hip_angle": truth["hip_angle"]}
    half = {"thigh_angle": ref["thigh_angle"], "pelvis_tilt": ref["pelvis_tilt"],
            "hip_angle": np.pi + np.asarray(ref["hip_angle"])}  # reference zero half a turn away
    rep = sod.detect_leg("SYNTH-half-turn-chain", "right", src, reference_angles=half,
                         params={"min_families": 1})
    ch = rep["channels"]["hip_angle"]
    assert ch["verdict"] == "conflict" and "half-turn" in ch["reason"]
    # Derivation preconditions held (decided relation, applied anchors), so only the
    # sticky-conflict rule kept hip from being re-derived.
    assert rep["channels"]["thigh_angle"]["verdict"] == "apply"
    rel = [r for r in rep["relations"] if r["channels"] == ["thigh_angle", "hip_angle"]][0]
    assert rel["product"] == 1
    assert not any(e["test"].startswith("derived:") for e in ch["evidence"])


def test_vertical_order_guard_survives_dict_copies():
    rear = np.array([-0.12, 1.0]) + np.zeros((10, N, 2))
    front = np.array([0.12, 0.96]) + np.zeros((10, N, 2))
    front[..., 1] += 0.01 * np.sin(4 * np.pi * PHASE)
    ref = sod.marker_reference_angles({"pelvis_rear": rear, "pelvis_front": front})
    chan = {"pelvis_tilt": np.asarray(ref["pelvis_tilt"]).copy()}
    for copy in (dict(ref), {"pelvis_tilt": ref["pelvis_tilt"]}, {"pelvis_tilt": ref["pelvis_tilt"][:]}):
        rep = sod.detect_leg("SYNTH-copied-guard", "right", chan, reference_angles=copy)
        assert rep["channels"]["pelvis_tilt"]["verdict"] == "abstain"
        assert rep["marker_checks"]["dropped"] == ["pelvis_tilt"]
    # A passing guard is kept through the same copies.
    truth, pts, *_ = synthetic_leg(seed=32)
    good = sod.marker_reference_angles(pts)
    rep = sod.detect_leg("SYNTH-copied-guard-ok", "right", {"hip_angle": truth["hip_angle"]},
                         reference_angles={"hip_angle": good["hip_angle"]})
    assert rep["channels"]["hip_angle"]["sign"] == 1 and rep["marker_checks"] is None


@pytest.mark.parametrize("scale,declared,mass,expected", [
    (1.0, "N_per_kg", None, "pass"),
    (1 / 9.81, "BW", None, "pass"),
    (70.0, "N", None, "pass"),
    (70.0, "N", 70.0, "pass"),
    (1.0, "BW", None, "fail"),        # N/kg data declared BW
    (1.0, "N", None, "fail"),         # N/kg data declared N
    (1 / 9.81, "N_per_kg", None, "fail"),  # BW data declared N/kg
    (70.0, "N_per_kg", None, "fail"),  # N data declared N/kg
    (70.0, "N", 10.0, "fail"),         # declared mass far from the data (peak ~10 BW)
])
def test_grf_unit_plausibility(scale, declared, mass, expected):
    truth, pts, joints, cop, grf, stance = synthetic_leg(seed=33)
    g = grf * scale
    assert sod.grf_unit_check(g[..., 1], declared, mass)["result"] == expected
    rep = sod.detect_leg("SYNTH-grf-unit", "right", {"ankle_moment": truth["ankle_moment"]},
                         joint_positions=joints, cop=cop, grf=g, task="level_walking",
                         grf_unit=declared, body_mass_kg=mass)
    ev = rep["channels"]["ankle_moment"]["evidence"]
    assert rep["grf_unit_check"]["result"] == expected
    if expected == "fail":
        assert all(e["sign"] is None and "implausible" in e["reason"] for e in ev)
        assert rep["plate_frame_check"] is None
    else:
        assert rep["channels"]["ankle_moment"]["verdict"] == "apply"


def test_grf_unit_check_ignores_units_whose_grf_was_withheld():
    # GT21 pilot: an adapter withholds GRF (all NaN) for strides whose stance a plate did not
    # capture. Those units must not vote a -inf peak that turns a plausible unit into "fail".
    truth, pts, joints, cop, grf, stance = synthetic_leg(seed=33)
    g = (grf * 70.0)[..., 1].copy()
    full = sod.grf_unit_check(g, "N", 70.0)
    g[: g.shape[0] * 2 // 3] = np.nan  # two thirds of the units withheld
    part = sod.grf_unit_check(g, "N", 70.0)
    assert full["result"] == part["result"] == "pass"
    assert part["units_with_grf"] == g.shape[0] - g.shape[0] * 2 // 3
    assert np.isfinite(part["median_unit_peak"])


def test_vertical_order_ignores_frames_with_missing_markers():
    truth, pts, *_ = synthetic_leg(seed=34)
    gappy = {k: v.copy() for k, v in pts.items()}
    gappy["knee"][:, :60] = np.nan  # 40 % marker dropout must not read as an inverted up vector
    assert sod.vertical_order_fraction(gappy) == 1.0
    none = {k: np.full_like(v, np.nan) for k, v in pts.items()}
    assert sod.vertical_order_fraction(none) is None



# ---- CORE-04 UM21 pilot verification fixes (synthetic) ----
def test_vertical_order_needs_enough_visible_frames_to_pass_but_one_to_fail():
    truth, pts, *_ = synthetic_leg(seed=35, n_units=1)
    few = {k: v[:, :20] for k, v in pts.items()}  # 20 visible frames < 50 required
    chk = sod.vertical_order_check(few)
    assert chk["result"] == "unknown" and chk["visible_frames"] == 20 and chk["fraction"] == 1.0
    assert sod.vertical_order_check(pts)["result"] == "pass"  # 150 frames
    inverted = {k: v[:, :1] * np.array([1.0, -1.0]) for k, v in pts.items()}
    assert sod.vertical_order_check(inverted)["result"] == "fail"
    with pytest.raises(ValueError):
        sod.marker_reference_angles(inverted)
    rep = sod.detect_leg("SYNTH-few-frames", "right", {"hip_angle": truth["hip_angle"][:, :20]},
                         marker_points=few)
    assert rep["marker_checks"]["visible_frames"] == 20
    assert rep["marker_checks"]["result"] == "unknown"


def test_cop_registration_shift_is_caught_by_the_foot_span_check():
    # A constant 11 cm backward CoP registration error (as in the verifier's
    # heel-at-contact rule on AB04/d10) leaves progression intact but moves every lever arm.
    truth, pts, joints, cop, grf, stance = synthetic_leg(seed=36)
    good = sod.detect_leg("SYNTH-cop-ok", "right", {"ankle_moment": truth["ankle_moment"]},
                          marker_points=pts, cop=cop, grf=grf, task="level_walking",
                          grf_unit="N_per_kg", cop_registration="synthetic: exact")
    assert good["plate_frame_check"]["cop_within_foot"]["result"] == "pass"
    assert good["cop_registration"] == "synthetic: exact"
    lever = [e for e in good["channels"]["ankle_moment"]["evidence"] if e["test"] == "lever_arm"][0]
    assert lever["strength"] == "strong" and lever["sign"] == 1
    shifted = cop - np.array([0.11, 0.0])
    bad = sod.detect_leg("SYNTH-cop-shifted", "right", {"ankle_moment": truth["ankle_moment"]},
                         marker_points=pts, cop=shifted, grf=grf, task="level_walking",
                         grf_unit="N_per_kg")
    assert bad["plate_frame_check"]["cop_progression"]["result"] == "pass"
    assert bad["plate_frame_check"]["cop_within_foot"]["result"] == "fail"
    lever = [e for e in bad["channels"]["ankle_moment"]["evidence"] if e["test"] == "lever_arm"][0]
    assert lever["sign"] is None and "registration" in lever["reason"]
    assert bad["channels"]["ankle_moment"]["sign_applied"] is False
    assert bad["cop_registration"] == "undeclared"


def test_lever_arm_is_not_strong_without_foot_markers():
    truth, pts, joints, cop, grf, stance = synthetic_leg(seed=37)
    rep = sod.detect_leg("SYNTH-no-feet", "right", {"ankle_moment": truth["ankle_moment"]},
                         joint_positions=joints, cop=cop, grf=grf, task="level_walking",
                         grf_unit="N_per_kg")
    assert rep["plate_frame_check"]["cop_within_foot"]["result"] == "unknown"
    lever = [e for e in rep["channels"]["ankle_moment"]["evidence"] if e["test"] == "lever_arm"][0]
    assert lever["strength"] == "moderate"



# ---- CORE-04 phase 3: cross-family tests (synthetic) ----
ALL = ("pelvis_tilt", "hip_angle", "knee_angle", "ankle_angle", "hip_moment", "knee_moment",
       "ankle_moment", "hip_power", "knee_power", "ankle_power")
INJECTED_TRUTH = {k: INJECTED_SIGNS.get(k, -1 if k.endswith("_power") else 1) for k in ALL}
DUR = np.full(24, STRIDE_S)


def _full(src, pts, cop, grf, task="level_walking", **kw):
    return sod.detect_leg("SYNTH-full", "right", src, marker_points=pts, cop=cop, grf=grf,
                          task=task, grf_unit="N_per_kg", unit_durations_s=kw.pop("dur", DUR),
                          dt=DT, **kw)


def _no_wrong_apply(rep, truth=INJECTED_TRUTH):
    for k, c in rep["channels"].items():
        if c["sign_applied"]:
            assert c["sign"] == truth[k], (k, c["sign"], c["reason"])


def test_cross_family_apply_with_markers_plates_and_durations():
    truth, pts, joints, cop, grf, stance = synthetic_leg(seed=41)
    rep = _full(injected_source(truth), pts, cop, grf)
    ch = rep["channels"]
    applied = {k: c["sign"] for k, c in ch.items() if c["sign_applied"]}
    assert applied == {"knee_angle": -1, "ankle_angle": 1, "hip_moment": 1,
                       "ankle_moment": 1, "ankle_power": -1}
    assert set(ch["hip_moment"]["families"]) == {"plate_geometry", "plate_timing"}
    # Pure-cosine hip: half-cycle ambiguous, so the hip angle is suggest only; hip power then
    # has no applied anchors and the smooth gait has no H3 burst: it abstains.
    assert ch["hip_angle"]["verdict"] == "suggest" and ch["hip_angle"]["sign"] == 1
    assert ch["hip_power"]["verdict"] == "abstain"
    assert ch["pelvis_tilt"]["verdict"] == "suggest"  # no second family for the pelvis
    assert rep["leg_assignment_check"]["result"] == "pass"


@pytest.mark.parametrize("s", [1, -1])
def test_plate_timed_tests_recover_both_orientations(s):
    truth, pts, joints, cop, grf, stance = synthetic_leg(seed=42)
    gate = sod.leg_assignment_check(truth["knee_angle"], stance, "level_walking")
    assert gate["result"] == "pass"
    assert sod.hip_stance_extension_test(s * truth["hip_angle"], stance, "level_walking", gate).sign == s
    assert sod.ankle_pushoff_test(s * truth["ankle_angle"], stance, "level_walking", gate).sign == s
    assert sod.hip_moment_timing_test(s * truth["hip_moment"], stance, "level_walking", gate).sign == s
    assert sod.power_timing_test("ankle", s * truth["ankle_power"], stance, "level_walking",
                                 gate).sign == s


def test_hip_power_timing_on_a_labelled_h3_pattern():
    # Labelled synthetic pattern (not a gait model): a positive hip power burst centred on
    # toe-off (H3) plus an earlier absorption (H2).
    stance = np.broadcast_to(PHASE < STANCE_END, (10, N)).copy()
    h3 = 0.8 * _bump(PHASE, 0.62, 0.04) - 0.5 * _bump(PHASE, 0.42, 0.05)
    pw = np.broadcast_to(h3, (10, N)) + 0.01 * np.random.default_rng(43).standard_normal((10, N))
    for s in (1, -1):
        assert sod.power_timing_test("hip", s * pw, stance, "level_walking").sign == s
    assert sod.power_timing_test("hip", 0.01 * pw, stance, "level_walking").sign == 1  # scale-free
    assert sod.power_timing_test("hip", pw, stance, "decline_walking").sign is None
    assert sod.power_timing_test("hip", pw, stance, "incline_walking").sign is None


@pytest.mark.parametrize("task", [None, "jump", "backward_walking", "stair_descent"])
def test_cross_family_tests_abstain_outside_their_assumptions(task):
    truth, pts, joints, cop, grf, stance = synthetic_leg(seed=44)
    for ev in (sod.hip_stance_extension_test(truth["hip_angle"], stance, task),
               sod.ankle_pushoff_test(truth["ankle_angle"], stance, task),
               sod.hip_moment_timing_test(truth["hip_moment"], stance, task),
               sod.power_timing_test("ankle", truth["ankle_power"], stance, task),
               sod.power_timing_test("hip", truth["hip_power"], stance, task)):
        assert ev.sign is None and "assumptions" in ev.reason, ev.test
    assert sod.leg_assignment_check(truth["knee_angle"], stance, task)["result"] == "unknown"
    assert sod.hip_stance_extension_test(truth["hip_angle"], None, "level_walking").sign is None


def test_leg_gate_ignores_units_without_stance_information():
    # GT21 pilot: units whose GRF the adapter withheld have an all-False stance row. They must
    # not vote "knee peak in swing"; otherwise they outvote contralateral-plate units.
    truth, pts, joints, cop, grf, stance = synthetic_leg(seed=45)
    n = stance.shape[0]
    wrong_leg = np.roll(stance, stance.shape[1] // 2, axis=1)  # other leg's plate timing
    mixed = np.zeros_like(stance)
    k = n // 3
    mixed[:k] = wrong_leg[:k]  # one third of units carry the other leg's stance, the rest none
    gate = sod.leg_assignment_check(truth["knee_angle"], mixed, "level_walking")
    assert gate["units_without_stance"] == n - k
    assert gate["result"] != "pass"
    if k >= sod.DEFAULTS["min_units"]:
        assert gate["result"] == "fail"


def test_contralateral_plate_is_caught_by_the_leg_gate():
    # Plate data of the other leg: stance, GRF and CoP shifted by half a stride.
    truth, pts, joints, cop, grf, stance = synthetic_leg(seed=45)
    shift = lambda a: np.roll(a, N // 2, axis=1)
    rep = _full(injected_source(truth), pts, shift(cop), shift(grf))
    assert rep["leg_assignment_check"]["result"] == "fail"
    timed = {"hip_stance_extension", "ankle_pushoff_plantarflexion", "hip_moment_timing",
             "power_timing", "late_stance_plantarflexor"}
    for c in rep["channels"].values():
        for e in c["evidence"]:
            if e["test"] in timed:
                assert e["sign"] is None and "other leg" in e["reason"]
    _no_wrong_apply(rep)
    assert not rep["channels"]["hip_moment"]["sign_applied"]


def test_backward_walking_labelled_level_never_applies_a_wrong_sign():
    # A backward walker (kinematics time-reversed within stance and swing) whose task is
    # mislabelled as level walking: the plate-timed hip test votes the wrong way.
    truth, pts, joints, cop, grf, stance = synthetic_leg(seed=46)
    idx = np.rint(((STANCE_END - PHASE) % 1.0) * (N - 1)).astype(int)
    hip_b = truth["hip_angle"][:, idx]
    pts_b = {k: v[:, idx] for k, v in pts.items()}
    rep = sod.detect_leg("SYNTH-backward", "right", {"hip_angle": hip_b, "knee_angle": truth["knee_angle"][:, idx]},
                         marker_points=pts_b, grf=grf, task="level_walking", grf_unit="N_per_kg")
    hip = rep["channels"]["hip_angle"]
    assert {e["test"]: e["sign"] for e in hip["evidence"]} == {
        "reference_angle:marker": 1, "hip_stance_extension": -1}
    assert hip["verdict"] == "conflict" and not hip["sign_applied"]
    alone = sod.detect_leg("SYNTH-backward-no-markers", "right",
                           {"hip_angle": hip_b, "knee_angle": truth["knee_angle"][:, idx]},
                           grf=grf, task="level_walking", grf_unit="N_per_kg")
    c = alone["channels"]["hip_angle"]
    assert c["verdict"] == "suggest" and c["sign"] == -1 and not c["sign_applied"]  # wrong, not applied


def test_mirrored_sagittal_markers_and_plates_give_conflicts_not_wrong_applies():
    # Adapter bug: forward axis reversed for markers, CoP and GRF alike.
    truth, pts, joints, cop, grf, stance = synthetic_leg(seed=47)
    mir = np.array([-1.0, 1.0])
    rep = _full(injected_source(truth), {k: v * mir for k, v in pts.items()}, cop * mir, grf * mir)
    _no_wrong_apply(rep)
    ch = rep["channels"]
    for k in ("hip_angle", "knee_angle", "ankle_angle"):
        assert ch[k]["verdict"] == "conflict", (k, ch[k]["reason"])
    assert rep["plate_frame_check"]["cop_progression"]["result"] == "fail"
    id_ev = [e for e in ch["hip_moment"]["evidence"] if e["test"] == "inverse_dynamics_light"][0]
    assert id_ev["sign"] is None and "frame" in id_ev["reason"]


def _winter_points(theta, n_units=4, hip=(0.0, 0.9)):
    """Rigid straight leg at angle theta from straight down, foot perpendicular to it."""
    d = np.stack([np.sin(theta), -np.cos(theta)], -1)
    u = np.stack([np.cos(theta), np.sin(theta)], -1)
    h = np.broadcast_to(np.array(hip), d.shape)
    knee = h + 0.45 * d
    ankle = knee + 0.43 * d
    pts = {"hip": h, "knee": knee, "ankle": ankle, "heel": ankle - 0.05 * u + 0.07 * d,
           "toe": ankle + 0.15 * u + 0.07 * d}
    return {k: np.broadcast_to(v, (n_units,) + v.shape).copy() for k, v in pts.items()}


def _composite(pts):
    """Mass, COM and inertia per kg of each Winter segment (independent of the module)."""
    out = []
    for name, (prox, dist) in (("thigh", ("hip", "knee")), ("shank", ("knee", "ankle")),
                               ("foot", ("heel", "toe"))):
        m, f, rho = WINTER[name]
        v = pts[dist] - pts[prox]
        length = np.hypot(v[..., 0], v[..., 1]).mean()
        out.append((m, pts[prox] + f * v, m * (rho * length) ** 2))
    return out


def test_inverse_dynamics_light_matches_a_rigid_pendulum():
    # Swing only (no GRF): a rigid leg pendulum about a fixed hip. Analytic:
    # M_hip = I_hip * theta'' + g * sum m_i (c_i - hip)_x, I_hip = sum (I_i + m_i |c_i - hip|^2).
    t = np.linspace(0.0, 1.0, N)
    theta = 0.4 * np.sin(2 * np.pi * t)
    pts = _winter_points(theta)
    I_hip = sum(I + m * np.sum((c - pts["hip"]) ** 2, -1)[0, 0] for m, c, I in _composite(pts))
    alpha = -0.4 * (2 * np.pi) ** 2 * np.sin(2 * np.pi * t)
    grav = sum(9.81 * m * (c - pts["hip"])[0, :, 0] for m, c, I in _composite(pts))
    analytic = I_hip * alpha + grav
    est = sod.inverse_dynamics_light(pts, np.full((4, N, 2), np.nan), np.zeros((4, N, 2)),
                                     np.ones(4))
    # Whole unit, ends included (periodic padding removes filter edge transients).
    assert np.max(np.abs(est[0] - analytic)) < 0.02 * np.max(np.abs(analytic))
    # Overground: the hip translating at constant speed must not change the moment.
    moving = {k: v + np.stack([1.3 * t, 0 * t], -1) for k, v in pts.items()}
    est2 = sod.inverse_dynamics_light(moving, np.full((4, N, 2), np.nan), np.zeros((4, N, 2)),
                                      np.ones(4))
    assert np.max(np.abs(est2 - est)) < 1e-6


def test_inverse_dynamics_light_matches_statics():
    # Held posture with a constant GRF: M_hip = g sum m_i (c_i - hip)_x - (CoP - hip) x F.
    pts = _winter_points(np.full(N, 0.25))
    F = np.broadcast_to(np.array([1.2, 9.0]), (4, N, 2)).copy()
    cop = pts["ankle"] + np.array([0.10, -0.08])
    r = cop - pts["hip"]
    analytic = (sum(9.81 * m * (c - pts["hip"])[..., 0] for m, c, I in _composite(pts))
                - (r[..., 0] * F[..., 1] - r[..., 1] * F[..., 0]))
    est = sod.inverse_dynamics_light(pts, cop, F, np.ones(4))
    assert np.allclose(est, analytic, atol=1e-6)


def test_inverse_dynamics_light_abstains_without_time_or_mass():
    truth, pts, joints, cop, grf, stance = synthetic_leg(seed=48)
    src = {"hip_moment": truth["hip_moment"]}
    no_dur = _full(src, pts, cop, grf, dur=None)
    ev = [e for e in no_dur["channels"]["hip_moment"]["evidence"] if e["test"] == "inverse_dynamics_light"][0]
    assert ev["sign"] is None and "durations" in ev["reason"]
    newtons = sod.detect_leg("SYNTH-N", "right", src, marker_points=pts, cop=cop, grf=grf * 70.0,
                             task="level_walking", grf_unit="N", unit_durations_s=DUR)
    ev = [e for e in newtons["channels"]["hip_moment"]["evidence"] if e["test"] == "inverse_dynamics_light"][0]
    assert ev["sign"] is None and "mass" in ev["reason"]



# ---- CORE-04 phase 3, verifier fix: a column taken from the other leg ----
def test_asymmetric_hip_applies_and_its_other_leg_column_does_not():
    # With a 2nd harmonic the hip is not antisymmetric over half a cycle, so lag 0 and a
    # half-cycle lag can be told apart.
    truth, pts, joints, cop, grf, stance = synthetic_leg(seed=51, hip2=0.12)
    rep = _full(injected_source(truth), pts, cop, grf)
    hip = rep["channels"]["hip_angle"]
    ref = [e for e in hip["evidence"] if e["test"] == "reference_angle:marker"][0]
    assert ref["stats"]["half_cycle"]["result"] == "lag0"
    assert hip["verdict"] == "apply" and hip["sign"] == 1
    src = injected_source(truth)
    src["hip_angle"] = np.roll(src["hip_angle"], N // 2, axis=1)
    rep = _full(src, pts, cop, grf)
    hip = rep["channels"]["hip_angle"]
    ref = [e for e in hip["evidence"] if e["test"] == "reference_angle:marker"][0]
    assert ref["stats"]["half_cycle"]["result"] == "half" and ref["sign"] is None
    assert not hip["sign_applied"]


@pytest.mark.parametrize("hip2", [0.0, 0.12])
@pytest.mark.parametrize("channel", ["hip_angle", "knee_angle", "ankle_angle", "hip_moment",
                                     "ankle_moment", "ankle_power", "hip_power"])
def test_column_from_the_other_leg_never_applies_a_wrong_sign(channel, hip2):
    truth, pts, joints, cop, grf, stance = synthetic_leg(seed=52, hip2=hip2)
    src = injected_source(truth)
    src[channel] = np.roll(src[channel], N // 2, axis=1)
    rep = _full(src, pts, cop, grf)
    c = rep["channels"][channel]
    assert not (c["sign_applied"] and c["sign"] != INJECTED_TRUTH[channel]), c["reason"]
    _no_wrong_apply(rep)


def test_hip_moment_timing_on_a_labelled_physiological_pattern():
    # Labelled synthetic pattern shaped like normative walking (internal extensor early,
    # flexor late, small in swing); not produced by the planar fixture, whose fixed hip
    # gives a non-physiological late-stance moment at 0.2 BW propulsion.
    stance = np.broadcast_to(PHASE < STANCE_END, (12, N)).copy()
    hm = (-0.7 * _bump(PHASE, 0.08, 0.06) + 0.7 * _bump(PHASE, 0.50, 0.08)
          - 0.15 * _bump(PHASE, 0.95, 0.04))
    m = np.broadcast_to(hm, (12, N)) + 0.02 * np.random.default_rng(53).standard_normal((12, N))
    for s in (1, -1):
        assert sod.hip_moment_timing_test(s * m, stance, "level_walking").sign == s
    assert sod.hip_moment_timing_test(m, stance, "stair_ascent").sign is None


def test_hip_moment_timing_and_id_light_disagreement_is_a_conflict():
    # At 0.30 BW propulsion the planar fixture's late-stance hip moment turns extensor, so
    # the timing test votes against inverse dynamics: the verdict must be a conflict.
    truth, pts, joints, cop, grf, stance = synthetic_leg(seed=54, fx_peak=2.94)
    rep = _full({"hip_moment": truth["hip_moment"], "knee_angle": truth["knee_angle"]},
                pts, cop, grf)
    c = rep["channels"]["hip_moment"]
    votes = {e["test"]: e["sign"] for e in c["evidence"]}
    assert votes["inverse_dynamics_light"] == 1 and votes["hip_moment_timing"] == -1
    assert c["verdict"] == "conflict" and not c["sign_applied"]



def test_hip_power_timing_abstains_on_an_incline_pattern():
    # Labelled synthetic incline pattern (not a gait model): on a steep incline the hip
    # keeps generating with an extensor moment through late stance, so power around toe-off
    # can be negative for a correctly stored column. Level-walking reading would vote wrong;
    # the test must abstain for incline walking (scope change logged after UM21 data).
    stance = np.broadcast_to(PHASE < STANCE_END, (10, N)).copy()
    incline = 1.0 * _bump(PHASE, 0.20, 0.08) - 0.6 * _bump(PHASE, 0.62, 0.05)
    pw = np.broadcast_to(incline, (10, N)) + 0.01 * np.random.default_rng(55).standard_normal((10, N))
    assert sod.power_timing_test("hip", pw, stance, "level_walking").sign == -1  # would be wrong
    ev = sod.power_timing_test("hip", pw, stance, "incline_walking")
    assert ev.sign is None and "assumptions" in ev.reason
    # The ankle push-off test keeps incline walking in scope.
    assert "incline_walking" in sod.POWER_TIMING_TASKS["ankle"]


def test_gate_failure_message_names_both_causes():
    assert "other leg" in sod.GATE_FAIL and "steep incline" in sod.GATE_FAIL
