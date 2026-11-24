"""UM21-S02 tests. EVERY fixture here is SYNTHETIC (built by construction from chosen angles and points); nothing
reads UMich data and nothing here regenerates or validates the scientific dataset."""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("run_um21_s02_frame", ROOT / "contributor_tools/run_um21_s02_frame.py")
s02 = importlib.util.module_from_spec(spec)
sys.modules["run_um21_s02_frame"] = s02
spec.loader.exec_module(s02)

RAD = np.radians


def sag_points(thigh, shank, foot, pelvis, hip=(0.0, 1.0), thigh_len=0.45, shank_len=0.45):
    """Sagittal (forward, up) points built from chosen segment angles in degrees (synthetic, by construction)."""
    hip = np.array(hip)
    knee = hip + thigh_len * np.array([np.sin(RAD(thigh)), -np.cos(RAD(thigh))])
    ankle = knee + shank_len * np.array([np.sin(RAD(shank)), -np.cos(RAD(shank))])
    heel = ankle + np.array([-0.07, -0.08])
    e = np.array([np.cos(RAD(foot)), np.sin(RAD(foot))])
    heel = ankle - 0.07 * e
    toe = heel + 0.21 * e
    psi = np.array([-0.05, 1.05])
    asi = psi + 0.1 * np.array([np.cos(RAD(pelvis)), np.sin(RAD(pelvis))])
    return {k: v[None, :] for k, v in dict(asi=asi, psi=psi, hip=hip, knee=knee, ankle=ankle, heel=heel, toe=toe).items()}


def test_known_value_segments_and_joints():
    # synthetic: thigh +30, shank -10, foot +20, pelvis -12 deg -> hip 42, knee 40, ankle 30 deg
    seg = s02.segment_angles(sag_points(30, -10, 20, -12))
    assert np.degrees(seg["thigh"][0]) == pytest.approx(30, abs=1e-9)
    assert np.degrees(seg["shank"][0]) == pytest.approx(-10, abs=1e-9)
    assert np.degrees(seg["foot"][0]) == pytest.approx(20, abs=1e-9)
    assert np.degrees(seg["pelvis"][0]) == pytest.approx(-12, abs=1e-9)
    j = s02.joint_angles(seg)
    assert np.degrees([j["hip"][0], j["knee"][0], j["ankle"][0]]) == pytest.approx([42, 40, 30], abs=1e-9)


def test_straight_standing_pose_gives_zero_knee_and_ankle():
    j = s02.joint_angles(s02.segment_angles(sag_points(0, 0, 0, 0)))
    assert j["knee"][0] == pytest.approx(0, abs=1e-12) and j["ankle"][0] == pytest.approx(0, abs=1e-12)


def test_composition_to_1e12():
    rng = np.random.default_rng(7)  # recorded seed
    t, s, f, p = (rng.uniform(-60, 60, 50) for _ in range(4))
    pts = [sag_points(*a) for a in zip(t, s, f, p)]
    seg = {k: np.concatenate([s02.segment_angles(q)[k] for q in pts]) for k in ("pelvis", "thigh", "shank", "foot")}
    j = s02.joint_angles(seg)
    assert np.max(np.abs(seg["thigh"] - seg["pelvis"] - j["hip"])) < 1e-12
    assert np.max(np.abs(seg["thigh"] - j["knee"] - seg["shank"])) < 1e-12
    assert np.max(np.abs(seg["shank"] + j["ankle"] - seg["foot"])) < 1e-12


def test_second_independent_implementation_with_reversed_heading():
    """Rotation-matrix / complex-number implementation on 3D lab points with the person facing -Y."""
    rng = np.random.default_rng(11)
    f_lab, u_lab = np.array([0.0, -1.0, 0.0]), np.array([0.0, 0.0, 1.0])
    for _ in range(20):
        a = rng.uniform(-50, 50, 4)
        pts = sag_points(*a)
        lab = {k: v[0, 0] * f_lab + v[0, 1] * u_lab for k, v in pts.items()}
        fwd = s02.heading(np.array([lab["asi"]]), np.array([lab["psi"]]))
        assert fwd == pytest.approx(f_lab, abs=1e-9)
        seg = s02.segment_angles({k: s02.sagittal(v[None, :], fwd) for k, v in lab.items()})
        # independent: rotate into the person's frame with an explicit matrix, then use complex arguments
        rot = np.array([f_lab, u_lab])
        loc = {k: rot @ v for k, v in lab.items()}
        c = lambda v: v[0] + 1j * v[1]
        thigh = np.angle(1j * c(loc["knee"] - loc["hip"]) * -1j * 1j) if False else np.angle(complex(-(loc["knee"] - loc["hip"])[1], (loc["knee"] - loc["hip"])[0]))
        shank = np.angle(complex(-(loc["ankle"] - loc["knee"])[1], (loc["ankle"] - loc["knee"])[0]))
        foot = np.angle(c(loc["toe"] - loc["heel"]))
        pel = np.angle(c(loc["asi"] - loc["psi"]))
        assert (seg["thigh"][0], seg["shank"][0], seg["foot"][0], seg["pelvis"][0]) == pytest.approx(
            (thigh, shank, foot, pel), abs=1e-12)
        assert np.degrees((seg["thigh"][0], seg["shank"][0], seg["foot"][0], seg["pelvis"][0])) == pytest.approx(a[[0, 1, 2, 3]], abs=1e-9)


def test_hip_centre_hand_computed():
    # synthetic level pelvis: width 0.25 m, depth 0.10 m; hand values: x = -0.24*0.1-0.0099, y = -0.30*0.25-0.0109,
    # z = 0.33*0.25+0.0073; person faces +x, up +z, right = -y.
    n = 3
    rasi = np.tile([0.05, -0.125, 1.0], (n, 1)); lasi = np.tile([0.05, 0.125, 1.0], (n, 1))
    rpsi = np.tile([-0.05, -0.05, 1.0], (n, 1)); lpsi = np.tile([-0.05, 0.05, 1.0], (n, 1))
    h = s02.hip_centres(rasi, lasi, rpsi, lpsi)
    assert h["pelvic_width_m"] == pytest.approx(0.25) and h["pelvic_depth_m"] == pytest.approx(0.10)
    expect = np.array([0.05 - 0.0339, -0.0898, 1.0 - 0.0859])
    assert h["right"][0] == pytest.approx(expect, abs=1e-9)
    assert h["left"][0] == pytest.approx(expect * [1, -1, 1], abs=1e-9)


def test_velocity_of_constant_rate_angle():
    import contributor_tools.run_um21_t04_signs as t04
    a = np.radians(np.linspace(0, 40, 150))[None, :]
    spacing = np.array([1.0 / 149])  # 1 s stride
    v, _ = s02.sa.derive_angular_velocities({"x": a}, spacing)
    assert v["x_velocity"] == pytest.approx(np.radians(40), rel=1e-9)


# ------------------------------------------------------------------ centre of pressure
@pytest.mark.parametrize("axis", (0, 1))
@pytest.mark.parametrize("sign", (1, -1))
@pytest.mark.parametrize("tilt_deg", (0.0, 10.0, -10.0))
@pytest.mark.parametrize("leg", ("right", "left"))
def test_cop_round_trip(axis, sign, tilt_deg, leg):
    """Synthetic: choose a foot-frame point, build the plate reading that produces it, recover it."""
    rng = np.random.default_rng(3)
    foot = RAD(rng.uniform(-10, 20))
    ankle = np.array([0.31, 0.12, 0.07])           # forward, up, right (person frame)
    target = np.array([0.15, 0.02, -0.08])           # anterior, vertical, lateral (outward)
    e_f, e_p = np.array([np.cos(foot), np.sin(foot)]), np.array([-np.sin(foot), np.cos(foot)])
    out = 1.0 if leg == "right" else -1.0
    p_f_u = ankle[:2] + (s02.FOOT_ORIGIN_M + target[0]) * e_f + target[1] * e_p
    p_r = ankle[2] + out * target[2]
    tilt = RAD(tilt_deg)
    shifts = (0.2, 0.0, 0.05)
    long_b = (p_f_u[0] - shifts[0]) / np.cos(tilt)
    shifts = (shifts[0], p_f_u[1] - long_b * np.sin(tilt), shifts[2])
    right = p_r - shifts[2]
    plate = np.zeros(2)
    if axis == 1:
        plate[1], plate[0] = sign * long_b, sign * right
    else:
        plate[0], plate[1] = sign * long_b, -sign * right
    person = s02.plate_to_person(plate, axis, sign, tilt, shifts)
    got = s02.foot_frame(person, ankle, foot, leg)
    assert got == pytest.approx(target, abs=1e-9)


def test_reversed_heading_gives_positive_anterior():
    # synthetic CoP 0.15 m ahead of the foot origin; the person faces -X in the lab (as AB04/i0 does)
    f_lab = np.array([-1.0, 0.0, 0.0])
    fwd = s02.heading(np.array([[-0.05, 0, 1.0]]), np.array([[0.05, 0, 1.0]]))
    assert fwd == pytest.approx(f_lab)
    ankle_lab = np.array([0.0, 0.0, 0.1])
    cop_lab = ankle_lab + (0.1 + 0.15) * f_lab
    a, c = s02.sagittal(ankle_lab, fwd), s02.sagittal(cop_lab, fwd)
    got = s02.foot_frame(np.array([c[0], c[1], 0.0]), np.array([a[0], a[1], 0.0]), 0.0, "right")
    assert got[0] == pytest.approx(0.15)


def test_force_follows_plate_conventions():
    # plate force on the plate is (0, f_long, -700): the ground pushes the person up, and braking if f_long > 0 on a
    # positive-sign axis 1 -> ground force forward = -f_long
    g = s02.force_to_person(np.array([0.0, 50.0, -700.0]), 1, 1, 0.0)
    assert g == pytest.approx([-50.0, 700.0, 0.0])
    g = s02.force_to_person(np.array([0.0, 50.0, -700.0]), 1, -1, 0.0)
    assert g[0] == pytest.approx(50.0)


def test_unloaded_samples_are_missing_never_zero():
    force = np.zeros((3, 6)); cop = np.zeros((3, 6))
    force[2, 2:5] = [-10.0, -300.0, -500.0]          # one sample below 20 N
    cop[0, 2:5], cop[1, 2:5] = [5.0, 6.0, 7.0], [100.0, 110.0, 120.0]
    f, c, loaded = s02.mask_unloaded(force, cop)
    assert loaded.tolist() == [False, False, False, True, True, False]
    assert np.isnan(c[:, ~loaded]).all() and np.isnan(f[:, ~loaded]).all()
    assert c[1, 3] == pytest.approx(0.110)            # mm -> m


def test_plate_interpolation_needs_both_neighbours():
    v = np.array([np.nan, 1.0, 2.0, 3.0, np.nan])
    got = s02.plate_at(v, np.array([1.0, 1.5, 2.0, 3.5]))
    assert np.isnan(got[3]) and got[1] == pytest.approx(1.5) and got[0] == pytest.approx(1.0) and got[2] == pytest.approx(2.0)
    assert np.isnan(s02.plate_at(v, np.array([0.0]))[0])


def test_shift_fit_recovers_known_shift():
    rng = np.random.default_rng(5)
    n = 400
    fy = rng.uniform(4, 10, n); fx = rng.uniform(-1.5, 1.5, n)
    cop_true = np.stack([rng.uniform(0, .2, n), np.full(n, 0.02)])
    hip = np.stack([rng.uniform(-.1, .1, n), np.full(n, 0.95)]); knee = np.stack([rng.uniform(-.1, .1, n), np.full(n, 0.5)])
    m_h = s02.joint_moment_from_force(cop_true, [fx, fy], hip, "hip")
    m_k = s02.joint_moment_from_force(cop_true, [fx, fy], knee, "knee")
    d, _, _ = s02.fit_shifts(cop_true - np.array([[0.25], [0.03]]), [fx, fy], hip, knee, m_h, m_k)
    assert d == pytest.approx([0.25, 0.03], abs=1e-9)


def test_choose_plate_axis_and_flip():
    t = np.arange(2000)
    ankle = 0.3 * np.sin(t / 150.0)
    rng = np.random.default_rng(1)
    for axis, sign in ((1, 1), (0, -1)):
        cop = np.zeros((2, t.size)); cop[axis] = sign * ankle * 1.2; cop[1 - axis] = rng.normal(0, 0.003, t.size)
        got, _ = s02.choose_plate_axis(cop, ankle, [(0, 2000)])
        assert got == (axis, sign)


# ------------------------------------------------------------------ whole recording on a synthetic trial
class A:
    def __init__(self, a):
        self.a, self.shape, self.ndim = np.asarray(a), np.asarray(a).shape, np.asarray(a).ndim

    def __getitem__(self, k):
        return self.a


def synthetic_trial(drop_marker=None):
    """12 s synthetic recording at 100 Hz, person facing -Y, sinusoidal segment angles, plate axis 1 sign +1,
    quasi-static moments consistent with the centre-of-pressure model. Returns (trial, v2, truth)."""
    n, T, mass = 1200, 1.0, 70.0
    t = (np.arange(n)) / 100.0
    F, U, R = np.array([0, -1.0, 0]), np.array([0, 0, 1.0]), np.array([-1.0, 0, 0])
    lab = lambda pf, pu, pr: pf[:, None] * F + pu[:, None] * U + pr[:, None] * R
    z, o = np.zeros(n), np.ones(n)
    psi_f, psi_u = z - 0.05, o * 1.05
    th_p = RAD(-10.0)
    asi_f, asi_u = psi_f + 0.1 * np.cos(th_p), psi_u + 0.1 * np.sin(th_p)
    mk = {"RPSI": lab(psi_f, psi_u, z + 0.05), "LPSI": lab(psi_f, psi_u, z - 0.05),
          "RASI": lab(asi_f, asi_u, z + 0.125), "LASI": lab(asi_f, asi_u, z - 0.125)}
    hjc = s02.hip_centres(mk["RASI"], mk["LASI"], mk["RPSI"], mk["LPSI"])
    truth = {}
    plate = {}
    for side, leg, out, off in (("R", "right", 1.0, 0.0), ("L", "left", -1.0, 0.5)):
        ph = ((t - off) / T) % 1.0
        sphase = 2 * np.pi * ph
        th_t, th_s, th_f = RAD(5 + 25 * np.cos(sphase)), RAD(-10 + 10 * np.cos(sphase)), RAD(5 * np.sin(sphase + 1))
        hip = hjc["right" if side == "R" else "left"]
        knee = hip + 0.45 * (np.sin(th_t)[:, None] * F - np.cos(th_t)[:, None] * U)
        ank = knee + 0.45 * (np.sin(th_s)[:, None] * F - np.cos(th_s)[:, None] * U)
        e_f = np.cos(th_f)[:, None] * F + np.sin(th_f)[:, None] * U
        heel = ank - 0.07 * e_f
        toe = heel + 0.21 * e_f
        mk.update({side + "KNE": knee + 0.05 * out * R, side + "KNEM": knee - 0.05 * out * R,
                   side + "ANK": ank + 0.035 * out * R, side + "ANKM": ank - 0.035 * out * R,
                   side + "HEE": heel, side + "TOE": toe, side + "GT": hip + 0.02 * out * R})
        # plate (person frame truth): loaded for the first 60 percent of the cycle
        tp = np.arange(10 * n) / 1000.0
        php = ((tp - off) / T) % 1.0
        s = php / 0.6
        loaded = s < 1.0
        fy = np.where(loaded, 10.0 * np.sin(np.pi * np.clip(s, 0, 1)), 0.0)              # N/kg
        fx = 0.15 * fy * np.cos(2 * np.pi * np.clip(s, 0, 1))
        ank_f = np.interp(tp, t, ank @ F); ank_u = np.interp(tp, t, ank @ U); ank_r = np.interp(tp, t, ank @ R)
        foot_p = np.interp(tp, t, th_f)
        ant = -0.17 + 0.21 * np.clip(s, 0, 1)
        cop_f = ank_f + (0.1 + ant) * np.cos(foot_p)
        cop_u = np.full_like(tp, 0.02)
        cop_r = ank_r + 0.01
        SF, SR = 0.25, 0.0
        rng = np.random.default_rng(2 if side == "R" else 4)
        p0 = (cop_r - SR) + rng.normal(0, 0.002, tp.size)     # axis 1, sign +1: right = p0, long = p1
        p1 = cop_f - SF
        force = np.zeros((3, tp.size)); cop = np.zeros((3, tp.size))
        force[1], force[2] = -fx * mass, -fy * mass
        cop[0], cop[1] = np.where(loaded, p0, 0) * 1000, np.where(loaded, p1, 0) * 1000
        force[:, ~loaded] = 0
        plate[side] = (force, cop)
        # frame-rate quasi-static moments (Nm/kg) from the true centre of pressure
        idx = np.arange(0, 10 * n, 10)
        cop_fr = np.stack([cop_f[idx], cop_u[idx]]); frc_fr = np.stack([fx[idx], fy[idx]])
        sg = lambda p: np.stack([p @ F, p @ U])
        mom = {"hip": s02.joint_moment_from_force(cop_fr, frc_fr, sg(hip), "hip"),
               "knee": s02.joint_moment_from_force(cop_fr, frc_fr, sg(knee), "knee"),
               "ankle": s02.joint_moment_from_force(cop_fr, frc_fr, sg(ank), "ankle")}
        truth[leg] = dict(th_t=th_t, th_s=th_s, th_f=th_f, mom=mom, cop_f=cop_f, tp=tp, ank=ank, t=t, loaded=loaded)
    if drop_marker:
        mk[drop_marker][300:420, :] = np.nan
    vis = lambda x: np.vstack([x.T, np.where(np.isfinite(x).all(axis=1), 1.0, 0.0)[None, :]])
    markers = {k: A(np.where(np.isfinite(vis(v)), vis(v), 0.0)) for k, v in mk.items()}
    trial = {"markers": markers,
             "forceplates": {"RForce": A(plate["R"][0]), "RCoP": A(plate["R"][1]), "LForce": A(plate["L"][0]),
                             "LCoP": A(plate["L"][1])},
             "events": {"RHS": A(np.arange(1, 1200, 100)), "LHS": A(np.arange(51, 1200, 100))}}
    v2 = {}
    for leg, side, a0 in (("right", "R", 101), ("left", "L", 51 + 100)):
        pairs = [(a0 + 100 * k, a0 + 100 * (k + 1)) for k in range(8)]
        for j, name in enumerate(("hip", "knee", "ankle")):
            truth[leg][name + "_grid"] = s02.um21.resample(truth[leg]["mom"][name], pairs)
        for k, (a, b) in enumerate(pairs):
            oid = f"um21:Streaming/AB99/Tread/i0:{leg}:frames:{a}:{b}"
            row = {s02.V2_COLUMNS[c]: np.zeros(150) for c in ("hip_angle", "knee_angle", "ankle_angle", "thigh_angle", "shank_angle")}
            row[s02.V2_COLUMNS["pelvis_tilt"]] = np.full(150, th_p)
            for name in ("hip", "knee", "ankle"):
                row[s02.V2_COLUMNS[name + "_moment"]] = truth[leg][name + "_grid"][k]
            v2[oid] = row
        truth[leg]["pairs"] = pairs
    return trial, v2, truth, mass


def test_whole_recording_synthetic():
    trial, v2, truth, mass = synthetic_trial()
    ids, sides, arrays, unheld, summary, ledger = s02.process_recording(trial, "AB99/i0", v2, mass, 0.0)
    assert len(ids) == 16
    assert s02.composition_error(arrays) < 1e-12
    # known angles at the grid times (synthetic, built by construction)
    for leg in ("right", "left"):
        tr = truth[leg]
        rows = [i for i, o in enumerate(ids) if f":{leg}:" in o]
        for r, (a, b) in zip(rows, tr["pairs"]):
            tg = (a - 1) / 100.0 + np.arange(150) * ((b - a) / 100.0) / 149
            for col, key in (("thigh_angle", "th_t"), ("shank_angle", "th_s"), ("foot_angle", "th_f")):
                assert np.max(np.abs(arrays[col][r] - np.interp(tg, tr["t"], tr[key]))) < 5e-4
            hip_expect = np.interp(tg, tr["t"], tr["th_t"]) - RAD(-10.0)
            assert np.max(np.abs(arrays["hip_angle"][r] - hip_expect)) < 5e-4
    # the fitted registration recovers the forward and up shifts of the synthetic plate (0.25 m, 0.02 m)
    for leg in ("right", "left"):
        fit = summary["legs"][leg]["plate"]["fit"]
        assert fit["forward_m"] == pytest.approx(0.25, abs=3e-3)
        assert fit["up_m"] == pytest.approx(0.02, abs=1.5e-2)
        assert summary["legs"][leg]["plate"]["axis"] == 1 and summary["legs"][leg]["plate"]["sign"] == 1
        assert summary["legs"][leg]["plate"]["ankle_holdout"]["r"] > 0.99
    # unloaded samples carry no centre of pressure; loaded ones match the foot-frame truth
    for leg in ("right", "left"):
        tr = truth[leg]
        rows = [i for i, o in enumerate(ids) if f":{leg}:" in o]
        for r, (a, b) in zip(rows, tr["pairs"]):
            c = unheld["cop_anterior"][r]
            tg = (a - 1) / 100.0 + np.arange(150) * ((b - a) / 100.0) / 149
            ldd = np.interp(tg, tr["tp"], tr["loaded"].astype(float)) > 0.999
            assert np.isfinite(c[ldd]).sum() > 20 and np.isnan(c[tg - (a - 1) / 100.0 > 0.62]).all()


def test_marker_gap_holds_columns_not_fills():
    trial, v2, truth, mass = synthetic_trial(drop_marker="RKNE")
    ids, sides, arrays, unheld, summary, ledger = s02.process_recording(trial, "AB99/i0", v2, mass, 0.0)
    gap = [i for i, o in enumerate(ids) if ":right:" in o and (301 <= int(o.split(":")[-2]) + 0 <= 420 or int(o.split(":")[-2]) < 420 < int(o.split(":")[-1]))]
    assert gap
    for i in gap:
        assert np.isnan(arrays["thigh_angle"][i]).all() and np.isnan(arrays["hip_angle"][i]).all()
        assert np.isfinite(arrays["foot_angle"][i]).all()
    # the other leg is untouched by the right knee gap
    assert np.isfinite(arrays["knee_angle"][[i for i, o in enumerate(ids) if ":left:" in o]]).all()


def test_pelvis_disagreement_holds_pelvis_and_hip():
    trial, v2, truth, mass = synthetic_trial()
    oid = next(iter(v2))
    v2[oid][s02.V2_COLUMNS["pelvis_tilt"]] = v2[oid][s02.V2_COLUMNS["pelvis_tilt"]] + RAD(2.0)
    ids, sides, arrays, unheld, summary, ledger = s02.process_recording(trial, "AB99/i0", v2, mass, 0.0)
    i = ids.index(oid)
    assert np.isnan(arrays["pelvis_tilt"][i]).all() and np.isnan(arrays["hip_angle"][i]).all()
    assert np.isfinite(arrays["knee_angle"][i]).all()


# ------------------------------------------------------------------ re-implemented independent method (synthetic)
FWD_Y = np.array([0.0, 1.0, 0.0])


def lab_bn(b, n):
    b, n = np.asarray(b, float), np.asarray(n, float)
    return b[:, None] * FWD_Y + n[:, None] * s02.UP


def test_pig_ankle_centre_geometry():
    ank, knee, tib = np.array([[0, 0, 0.1]]), np.array([[0, 0, 0.5]]), np.array([[-0.02, 0, 0.3]])
    off = 0.0457
    j = s02.pig_ankle_centre(knee, ank, tib, off)[0]
    assert np.linalg.norm(j - ank[0]) == pytest.approx(off, abs=1e-12)
    assert (j - knee[0]) @ (j - ank[0]) == pytest.approx(0, abs=1e-12)   # right angle at J
    assert j[1] == pytest.approx(0, abs=1e-12) and j[0] > 0                # in the plane, opposite the TIB marker
    j2 = s02.pig_ankle_centre(knee, ank, tib, off, toward_tib=True)[0]
    assert j2[0] < 0


def make_stance_series(offset, sigma=1.0, n=400, h_j=0.09, pig_back=0.016):
    """Synthetic: static foot on a level belt, loaded; the plate reading is built so the own-moment offset is known."""
    rng = np.random.default_rng(9)
    t = np.arange(n)
    ph = (t % 100) / 100.0
    stance = ph < 0.6
    s = ph / 0.6
    fn = np.where(stance, 700.0 * np.sin(np.pi * np.clip(s, 0, 1)), 0.0)
    fap = np.where(stance, -100.0 * np.sin(2 * np.pi * np.clip(s, 0, 1)), 0.0)   # braking first, then propulsion
    tau = rng.uniform(-0.2, 0.2, n)                                              # Nm/kg, arbitrary
    mass = 70.0
    a_b, a_n = np.zeros(n), np.full(n, 0.09)
    j_b = a_b - pig_back
    with np.errstate(divide="ignore", invalid="ignore"):
        db_id = (-tau * mass - h_j * 1.0 * fap) / fn
    cop_marker = j_b + db_id                       # centre of pressure along the belt in marker coordinates
    cop_ap = sigma * (cop_marker + offset)         # plate reading so that sigma * cop - offset = marker value
    seg = dict(ankle=lab_bn(a_b, a_n), midpoint=lab_bn(a_b, a_n), pig=lab_bn(j_b, a_n),
               heel=lab_bn(a_b - 0.08, np.full(n, 0.03)), toe=lab_bn(a_b + 0.13, np.full(n, 0.03)),
               met1=lab_bn(a_b + 0.1, np.full(n, 0.02)), met5=lab_bn(a_b + 0.08, np.full(n, 0.02)),
               pig_medial_root=np.ones(n, bool), cop_ap=cop_ap, f_ap=fap, f_n=fn, vgrf_bw=fn / (mass * 9.81), tau=tau)
    return seg, mass


def test_moment_registration_recovers_known_offset():
    ref = dict(pig_ankle_height_m=0.09, ankle_height_m=0.09, sole_line_pitch_rad=np.arctan2(0.0, 0.21))
    for offset, sigma in ((0.31, 1.0), (-0.42, 1.0)):
        seg, mass = make_stance_series(offset, sigma)
        sg, _ = s02.esml_plate_sign([seg], FWD_Y, 0.0) if False else (1.0, 0)
        reg = s02.moment_registration([seg], FWD_Y, 0.0, mass, ref, sg)
        assert reg["offset_m"] == pytest.approx(offset, abs=1e-9)
        assert reg["force_sign"] == 1.0 and reg["residual_iqr_m"] < 1e-9 and reg["donor"]
        assert reg["pig_minus_midpoint_b_m"] == pytest.approx(-0.016, abs=1e-12)


def _donor_meta(own, donor_ok=lambda s: True, extra=()):
    meta = {s: {"recordings": {"Tread_i10": {"walk_direction": 1.0, "plate_sign": 1.0,
                                              "moment_diagnostic": {"offset_m": o, "donor": donor_ok(s)}}}}
            for s, o in own.items()}
    for s in extra:
        meta[s] = {"recordings": {"Tread_i10": {"walk_direction": 1.0, "plate_sign": 1.0}}}
    return meta


def test_leave_subject_out_donor_median():
    own = {"S1": 0.10, "S2": 0.20, "S3": 0.30, "S4": 0.40, "S5": 0.50, "S6": 0.60}
    meta = _donor_meta(own, extra=("S7",))
    s02.leave_subject_out_offsets(meta)
    r1 = meta["S1"]["recordings"]["Tread_i10"]          # donors S2..S6: median 0.40 (S1's own value never enters)
    assert r1["status"] == "registered" and r1["registration_offset_m"] == pytest.approx(0.40)
    assert "S1" not in r1["registration_donors"]
    r7 = meta["S7"]["recordings"]["Tread_i10"]          # donors S1..S6: median of 0.10..0.60 = 0.35
    assert r7["registration_offset_m"] == pytest.approx(0.35)
    meta = _donor_meta(own, donor_ok=lambda s: s != "S2", extra=("S7",))   # S2 fails the IQR gate: 5 donors left
    s02.leave_subject_out_offsets(meta)
    assert meta["S7"]["recordings"]["Tread_i10"]["registration_offset_m"] == pytest.approx(0.40)
    assert meta["S1"]["recordings"]["Tread_i10"]["status"] == "excluded"    # only 4 other donors


def test_sole_reference_belt_height_and_pig_offset():
    n_flat, n_push = 250, 100
    t = np.arange(n_flat + n_push)
    w = -2.0                                           # rad/s push-off rotation about C
    cb, cn = 0.05, 0.02
    theta = np.where(t >= n_flat, w * (t - n_flat) / 100.0, 0.0)
    body = {"heel": (-0.08, 0.03), "toe": (0.13, 0.03), "met1": (0.1, 0.02), "met5": (0.08, 0.02), "mid": (0.0, 0.09)}
    def point(name):
        db, dn = body[name][0] - cb, body[name][1] - cn
        return (cb + db * np.cos(theta) - dn * np.sin(theta), cn + db * np.sin(theta) + dn * np.cos(theta))
    pos = {k: point(k) for k in body}
    mid = lab_bn(*pos["mid"])
    pig = lab_bn(pos["mid"][0] - 0.016, pos["mid"][1])
    seg = dict(ankle=mid, midpoint=mid, pig=pig, pig_medial_root=np.ones(t.size, bool),
               heel=lab_bn(*pos["heel"]), toe=lab_bn(*pos["toe"]), met1=lab_bn(*pos["met1"]), met5=lab_bn(*pos["met5"]),
               vgrf_bw=np.full(t.size, 0.9))
    ref = s02.sole_reference({"Tread_i0_s1_seg01": seg}, FWD_Y)
    assert ref["belt_height_m"] == pytest.approx(cn - s02.ROCKER_ABOVE_BELT_M, abs=2e-3)
    assert ref["ankle_height_m"] == pytest.approx(0.09 - (cn - s02.ROCKER_ABOVE_BELT_M), abs=2e-3)
    assert ref["pig_minus_midpoint_foot_axis_m"] == pytest.approx(-0.016, abs=1e-3)
    assert ref["sole_line_pitch_rad"] == pytest.approx(0.0, abs=1e-9)


def test_pelvis_small_difference_flagged_not_held():
    trial, v2, truth, mass = synthetic_trial()
    oid = next(iter(v2))
    v2[oid][s02.V2_COLUMNS["pelvis_tilt"]] = v2[oid][s02.V2_COLUMNS["pelvis_tilt"]] + RAD(0.5)
    ids, sides, arrays, unheld, summary, ledger = s02.process_recording(trial, "AB99/i0", v2, mass, 0.0)
    assert np.isfinite(arrays["pelvis_tilt"][ids.index(oid)]).all()
    assert summary["legs"]["right"]["pelvis_check"]["flagged_above_0.2_deg_kept"] >= 1


def test_endpoint_report_uses_first_stance_run():
    # synthetic: stance from sample 2 to 90, then loaded again from 140 (next stride). heel marker at -0.17, toe 0.04
    ant = np.full((1, 150), np.nan)
    ant[0, 2:91] = np.linspace(-0.16, 0.05, 89)
    ant[0, 140:] = -0.16
    heel, toe = np.full((1, 150), -0.17), np.full((1, 150), 0.04)
    r = s02.endpoint_report(ant, heel, toe, None, 0.03, "test")
    assert r["strides_checked"] == 1 and r["fraction_within_tolerance_heel"] == 1.0 and r["fraction_within_tolerance_toe"] == 1.0
    assert r["first_loaded_minus_heel_m"]["median"] == pytest.approx(0.01) and r["last_loaded_minus_toe_m"]["median"] == pytest.approx(0.01)


# ------------------------------------------------------------------ publication gate (D-UM21-S02-1 = A); synthetic inputs
def _reg(r=0.97, toe4=0.97, heel4=0.0, assign=1.0, lat=0.9):
    return {"ankle_holdout": {"r": r}, "endpoint_check_0p2bw": {"fraction_within_4cm_toe": toe4, "fraction_within_4cm_heel": heel4},
            "plate_assignment": {"same_plate_loaded_within_5_frames_fraction": assign}, "lateral_corr_plate_vs_markers": lat}


def test_gate_passes_when_both_checks_pass_and_heel_is_not_a_gate():
    assert s02.cop_gate_reasons(_reg(r=0.95, toe4=0.95, heel4=0.0), "AB01/i0") == []   # exactly at both limits


@pytest.mark.parametrize("kw,text", [({"r": 0.949}, "hold-out ankle"), ({"toe4": 0.94}, "toe-off end"),
                                      ({"toe4": None}, "not checkable"), ({"assign": 0.5}, "plate not loaded")])
def test_gate_holds_each_failure(kw, text):
    reasons = s02.cop_gate_reasons(_reg(**kw), "AB01/i0")
    assert reasons and any(text in r for r in reasons)


def test_gate_holds_named_recording_until_explained():
    reasons = s02.cop_gate_reasons(_reg(), "AB04/d10")
    assert len(reasons) == 1 and "20 cm" in reasons[0]


def test_gate_missing_checks_are_not_a_pass():
    assert s02.cop_gate_reasons({}, "AB01/i0")


def test_quantiles_store_p95():
    q = s02._quantiles(np.arange(101.0) * -1)
    assert q["p95"] == pytest.approx(-5.0) and q["p95_abs"] == pytest.approx(95.0)


def test_full_stage_lists_44_recordings():
    assert len(s02.stage_recordings("full")) == 44
