"""UM21-Q01 assessment tests. All arrays here are SYNTHETIC fixtures with known values."""
import numpy as np
import pytest

from contributor_tools import run_um21_q01_assessment as q

OID = "um21:Streaming/AB01/Tread/i0:right:frames:100:277"


def smooth():
    t = np.linspace(0, 2 * np.pi, 150)
    return {"hip_angle": 20 * np.sin(t), "knee_angle": 30 + 25 * np.sin(t), "ankle_angle": 8 * np.sin(t),
            "pelvis_tilt": 5 + np.sin(t), "thigh_angle": 15 * np.sin(t), "shank_angle": 10 * np.sin(t),
            "foot_angle": 5 * np.sin(t), "hip_moment": np.sin(t)}


def arrays(**over):
    a = {c: None for c in q.CHANNELS}
    a.update(smooth())
    a.update(over)
    return a


def run(a, side="right", samples=None):
    units = {c: "deg" for c in q.CHANNELS}  # SYNTHETIC arrays here are already in degrees
    return q.assess_observation(OID, side, list(range(150)) if samples is None else samples, a, units)


def test_clean_synthetic_has_no_failures_but_unchecked_columns_stay_unchecked():
    e, f = run(arrays())
    assert f == [] and e["overall"] == "no_failure_found"
    ch = e["plausibility"]["channels"]
    assert ch["hip_angle"] == "pass" and ch["pelvis_tilt"] == "pass_jump_only"
    assert ch["ankle_angle"] == "pass_offset_unverified"
    assert ch["hip_moment"] == "unchecked"  # has data but no limit: never pass
    assert ch["hip_power"] == "not_checked_no_column"  # held: no column


def test_180_degree_jump_fails_L2_with_sample_index():
    x = smooth()["knee_angle"].copy()
    x[75:] += 180.0
    e, f = run(arrays(knee_angle=x))
    l2 = [r for r in f if r["limit"] == "L2" and r["channel"] == "knee_angle"]
    assert [r["sample_index"] for r in l2] == [75]
    assert e["overall"] == "failed" and e["plausibility"]["channels"]["knee_angle"] == "fail"


def test_out_of_range_angle_fails_L1_at_exact_samples():
    x = np.zeros(150)
    x[[10, 11]] = [151.0, 150.0]  # 150 is on the bound: passes; 151 fails
    x[11] = 150.0
    e, f = run(arrays(hip_angle=x * 1.0))
    l1 = [r for r in f if r["limit"] == "L1"]
    assert [r["sample_index"] for r in l1] == [10]
    assert q.limit_failures("knee_angle", np.full(150, -31.0))[0][0] == "L1"
    assert q.limit_failures("ankle_angle", np.full(150, 51.0))[0][0] == "L1"
    assert q.limit_failures("ankle_angle", np.full(150, -80.0)) == []


def test_jump_of_exactly_30_passes_and_just_over_fails():
    x = np.zeros(150)
    x[50:] = 30.0
    assert q.limit_failures("pelvis_tilt", x) == []
    x[50:] = 30.5
    assert [r[1] for r in q.limit_failures("pelvis_tilt", x)] == [50]


def test_nan_is_missing_not_failure_and_not_a_jump():
    x = smooth()["hip_angle"].copy()
    x[40:45] = np.nan
    e, f = run(arrays(hip_angle=x))
    assert f == [] and e["structural"]["missing_samples"]["hip_angle"] == [40, 41, 42, 43, 44]
    assert q.channel_state("hip_angle", np.full(150, np.nan), []) == "unchecked_all_missing"


def test_unlimited_channels_are_never_limit_checked():
    assert q.limit_failures("hip_moment", np.full(150, 1e6)) == []
    assert q.channel_state("hip_moment", np.full(150, 1e6), []) == "unchecked"
    assert q.channel_state("knee_power", None, []) == "not_checked_no_column"


def test_structural_problems_separate_from_plausibility():
    e, _ = run(arrays(), side="left")
    assert e["structural"]["state"] == "fail" and e["plausibility"]["failed_channels"] == []
    e, _ = run(arrays(), samples=list(range(149)) + [150])
    assert e["structural"]["state"] == "fail"


def test_stride_time_from_id_and_reported_only():
    assert q.stride_time_s(q.parse_observation_id(OID)) == pytest.approx(1.77)
    e, _ = q.assess_observation("um21:Streaming/AB01/Tread/i0:right:frames:100:400", "right", list(range(150)), arrays(), {c: "deg" for c in q.CHANNELS})
    assert e["structural"]["L3_stride_time_outside_range_reported_only"] is True
    assert e["overall"] == "no_failure_found"  # L3 never filters


def test_group_observations_reports_repeats():
    runs, rep = q.group_observations(["a", "a", "b", "a"])
    assert runs == [("a", 0, 2), ("b", 2, 3), ("a", 3, 4)] and rep == ["a"]


# ---- units (v2): published angles are RADIANS. All arrays below are SYNTHETIC with known values.
def rad_data(**over):
    d = {c: np.radians(v) for c, v in smooth().items() if c in q.COLUMN_UNITS and q.COLUMN_UNITS[c] == "rad"}
    d["hip_moment"] = smooth()["hip_moment"]
    d.update(over)
    return d


def run_published(d):
    conv, units = q.convert_to_degrees(d)
    return q.assess_observation(OID, "right", list(range(150)), {**{c: None for c in q.CHANNELS}, **conv}, units)


def test_radian_published_clean_stride_passes_after_conversion():
    e, f = run_published(rad_data())
    assert f == [] and e["plausibility"]["channels"]["hip_angle"] == "pass"


def test_radian_valued_out_of_range_ankle_fails_L1_in_degrees():
    x = np.zeros(150)
    x[30] = -4.65  # radians, about -266 degrees (the AB07/i10 kind of value); raw it would look in-range
    e, f = run_published(rad_data(ankle_angle=x))
    assert [r["limit"] for r in f if r["channel"] == "ankle_angle"][:1] == ["L1"]
    assert f[0]["value"] == pytest.approx(-266.4, abs=0.1)


def test_radian_valued_jump_fails_L2():
    x = np.zeros(150)
    x[60:] = 2.37  # radians, about 135.8 degrees between adjacent samples
    e, f = run_published(rad_data(foot_angle=x))
    l2 = [r for r in f if r["limit"] == "L2"]
    assert [r["sample_index"] for r in l2] == [60] and l2[0]["value"] == pytest.approx(135.8, abs=0.1)
    x[60:] = 0.5  # 28.6 degrees: passes
    assert run_published(rad_data(foot_angle=x))[1] == []


def test_unknown_unit_is_refused():
    with pytest.raises(q.UnitError):
        q.convert_to_degrees({"mystery_angle": np.zeros(150)})
    with pytest.raises(q.UnitError):  # a limited angle passed unconverted (radians) is refused
        q.assess_observation(OID, "right", list(range(150)), arrays(), {c: "rad" for c in q.CHANNELS})
    with pytest.raises(q.UnitError):  # no unit given
        q.assess_observation(OID, "right", list(range(150)), arrays())


def test_unit_evidence_must_state_the_conversion():
    q.check_unit_evidence({"adapter": {"unit_conversion": "angles deg -> rad (x pi/180, numpy.radians); moments..."}})
    with pytest.raises(q.UnitError):
        q.check_unit_evidence({"adapter": {}})
    with pytest.raises(q.UnitError):
        q.check_unit_evidence({"adapter": {"unit_conversion": "angles as stored"}})
