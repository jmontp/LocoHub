"""CORE-FOOT-01 foot-flat zero. All fixtures are SYNTHETIC (random points, random tiny tables); no dataset is read.

The centre-of-pressure sign is proved against each dataset's OWN foot-frame function (GT23 conventions, GT21 pass, UM21 S02
frame): the point is recomputed with the foot angle shifted by -offset and compared with rotate_cop() of the original point.
"""
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pyarrow as pa
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ff = _load("foot_flat_t", "contributor_tools/common/foot_flat.py")
gt23 = _load("gt23_conv_t", "contributor_tools/gt23_conventions.py")
gt21 = _load("gt21_pass_t", "contributor_tools/gt21_rb_pass.py")
um21 = _load("um21_frame_t", "contributor_tools/run_um21_s02_frame.py")


def _stack(ff_out):
    if isinstance(ff_out, dict):
        return np.array(ff_out["anterior"]), np.array(ff_out["vertical"]), np.array(ff_out["lateral"])
    return np.array(ff_out[0]), np.array(ff_out[1]), np.array(ff_out[2])


@pytest.mark.parametrize("name,mod,up,leg", [("gt23", gt23, [0, 1, 0], "R"), ("gt23", gt23, [0, 1, 0], "L"),
                                             ("gt21", gt21, [0, 1, 0], "right"), ("gt21", gt21, [0, 1, 0], "left"),
                                             ("um21", um21, [0, 0, 1], "right"), ("um21", um21, [0, 0, 1], "left")])
@pytest.mark.parametrize("offset_deg", [-11.7, -6.7, 1.2, 8.0])
def test_cop_rotation_matches_each_datasets_own_foot_frame(name, mod, up, leg, offset_deg):
    rng = np.random.default_rng(11)
    n = 40
    up = np.array(up, float)
    horiz = np.array([1.0, 0, 0]) if up[1] == 1 else np.array([1.0, 0, 0])
    fwd = np.tile(horiz, (n, 1)) if name != "um21" else horiz
    ankle = rng.normal(0, 0.3, (n, 3))
    point = ankle + rng.normal(0, 0.15, (n, 3))
    foot = rng.uniform(-0.6, 0.5, n)
    off = math.radians(offset_deg)
    fn = mod.foot_frame_point
    a0, v0, l0 = _stack(fn(point, ankle, fwd, foot, leg))
    a1, v1, l1 = _stack(fn(point, ankle, fwd, foot - off, leg))      # the shifted foot angle, recomputed by the dataset's own code
    ra, rv = ff.rotate_cop(a0, v0, off)
    assert np.max(np.abs(ra - a1)) < 1e-12 and np.max(np.abs(rv - v1)) < 1e-12
    assert np.max(np.abs(l0 - l1)) < 1e-12                                  # lateral does not depend on the foot angle
    # the wrong sign must be visibly wrong (the test can fail)
    wa, wv = ff.rotate_cop(a0, v0, -off)
    assert np.max(np.abs(wa - a1)) > 1e-3


def test_rotation_keeps_distance_to_the_ankle_and_origin():
    a, v = np.array([0.05, -0.1]), np.array([0.02, 0.0])
    ra, rv = ff.rotate_cop(a, v, 0.3)
    assert np.allclose(np.hypot(a + 0.1, v), np.hypot(ra + 0.1, rv))
    assert np.allclose(ff.rotate_cop(a, v, 0.0), (a, v))


def test_person_offsets_and_uncorrected_people():
    rng = np.random.default_rng(1)
    base = rng.normal(0, 0.4, ff.N)
    base[ff.MID] = math.radians(4.0)
    p = ff.person_offsets([("a", "o1", base), ("a", "o2", base + math.radians(2)), ("a", "o3", base - math.radians(2)),
                           ("b", "o4", np.full(ff.N, np.nan))])
    assert abs(p["a"]["offset_deg"] - 4.0) < 1e-9 and p["a"]["n_strides"] == 3
    assert "b" not in p


def _table(subjects, rng, n_per=150, with_null=False):
    subj = np.repeat(subjects, n_per)
    n = len(subj)
    shank = rng.normal(0, 0.3, n)
    foot = rng.normal(0, 0.3, n)
    cols = {"subject": subj, "observation_id": np.repeat([f"o{i}" for i in range(len(subjects))], n_per),
            "phase_ipsi": np.tile(np.linspace(0, 100, n_per), len(subjects)),
            "shank_sagittal_angle_ipsi_rad": shank, "foot_sagittal_angle_ipsi_rad": foot,
            "foot_sagittal_angle_contra_rad": foot + 0.1,
            "ankle_dorsiflexion_angle_ipsi_rad": foot - shank, "ankle_dorsiflexion_angle_contra_rad": foot + 0.1 - shank,
            "knee_flexion_angle_ipsi_rad": rng.normal(0, 0.3, n),
            "cop_anterior_ipsi_m": rng.normal(0, 0.05, n), "cop_vertical_ipsi_m": rng.normal(0, 0.02, n),
            "cop_lateral_ipsi_m": rng.normal(0, 0.02, n), "cop_lab_x_ipsi_m": rng.normal(0, 1, n),
            "grf_vertical_ipsi_BW": rng.uniform(0, 1.2, n)}
    cols["cop_anterior_contra_m"] = cols["cop_anterior_ipsi_m"].copy()
    cols["cop_vertical_contra_m"] = cols["cop_vertical_ipsi_m"].copy()
    cols["cop_anterior_ipsi_m"][::7] = np.nan
    cols["cop_vertical_ipsi_m"][::7] = np.nan
    t = pa.table({k: (pa.array(v) if v.dtype.kind == "f" else pa.array(v.tolist())) for k, v in cols.items()})
    if with_null:
        i = t.schema.get_field_index("foot_sagittal_angle_ipsi_rad")
        vals = cols["foot_sagittal_angle_ipsi_rad"]
        t = t.set_column(i, t.schema.field(i), pa.array(vals, mask=np.arange(n) % 11 == 0))
    return t, cols


def test_transform_changes_only_foot_ankle_cop_and_keeps_the_composition():
    rng = np.random.default_rng(5)
    t, c = _table(["S1", "S2"], rng, with_null=True)
    off = {"S1": math.radians(-6.7)}                       # S2 is uncorrected
    tf = ff.FootFlat(off)
    out = tf(t)
    assert out.schema.equals(t.schema)
    changed = set(ff.changed_columns(t.schema.names))
    assert changed == {"foot_sagittal_angle_ipsi_rad", "foot_sagittal_angle_contra_rad", "ankle_dorsiflexion_angle_ipsi_rad",
                       "ankle_dorsiflexion_angle_contra_rad", "cop_anterior_ipsi_m", "cop_vertical_ipsi_m",
                       "cop_anterior_contra_m", "cop_vertical_contra_m"}
    for name in t.schema.names:
        old, new = t.column(name), out.column(name)
        if name not in changed:
            assert old.equals(new), name                   # everything else identical (bit for bit)
    s1 = np.array(t.column("subject").to_pylist()) == "S1"
    for name in ("foot_sagittal_angle_contra_rad", "ankle_dorsiflexion_angle_ipsi_rad", "ankle_dorsiflexion_angle_contra_rad"):
        d = np.array(t.column(name).to_numpy(zero_copy_only=False)) - np.array(out.column(name).to_numpy(zero_copy_only=False))
        assert np.max(np.abs(d[s1] - off["S1"])) < 1e-15 and np.all(d[~s1] == 0.0)
    # null kept as null, value shifted elsewhere
    f_old, f_new = t.column("foot_sagittal_angle_ipsi_rad"), out.column("foot_sagittal_angle_ipsi_rad")
    assert f_old.null_count == f_new.null_count > 0
    # ankle = foot - shank keeps holding after the shift (within rounding)
    foot = np.array(out.column("foot_sagittal_angle_contra_rad").to_numpy(zero_copy_only=False))
    ank = np.array(out.column("ankle_dorsiflexion_angle_contra_rad").to_numpy(zero_copy_only=False))
    sh = np.array(out.column("shank_sagittal_angle_ipsi_rad").to_numpy(zero_copy_only=False))
    assert np.max(np.abs(ank - (foot - sh))) < 1e-12
    # CoP: NaN pattern kept, distance to the ankle kept, lateral untouched
    a0 = np.array(t.column("cop_anterior_ipsi_m").to_numpy(zero_copy_only=False))
    a1 = np.array(out.column("cop_anterior_ipsi_m").to_numpy(zero_copy_only=False))
    v0 = np.array(t.column("cop_vertical_ipsi_m").to_numpy(zero_copy_only=False))
    v1 = np.array(out.column("cop_vertical_ipsi_m").to_numpy(zero_copy_only=False))
    assert np.array_equal(np.isnan(a0), np.isnan(a1)) and np.array_equal(np.isnan(v0), np.isnan(v1))
    ok = np.isfinite(a0) & s1
    assert np.allclose(np.hypot(a0 + 0.1, v0)[ok], np.hypot(a1 + 0.1, v1)[ok], atol=1e-12)
    assert np.array_equal(a0[~s1 | ~np.isfinite(a0)], a1[~s1 | ~np.isfinite(a0)], equal_nan=True)
    assert tf.summary()["rows_shifted"] == int(s1.sum())


def test_reassess_matches_a_direct_recount_and_l2_is_unchanged(tmp_path):
    import pyarrow.parquet as pq
    rng = np.random.default_rng(9)
    n = 150
    ank = np.radians(rng.uniform(-70, 40, n))
    ank[10] = np.radians(48.0)              # inside the limit at zero, outside once the offset (-5 deg) is subtracted: 53 > 50
    anterior = np.zeros(n)
    vertical = np.zeros(n)
    t = pa.table({"observation_id": ["o1"] * n, "reference_side": ["left"] * n, "subject": ["S1"] * n,
                  "source_recording_id": ["S1/r"] * n, "phase_ipsi": np.linspace(0, 100, n),
                  "foot_sagittal_angle_ipsi_rad": ank + 0.2, "ankle_dorsiflexion_angle_ipsi_rad": ank,
                  "cop_anterior_ipsi_m": anterior, "cop_vertical_ipsi_m": vertical})
    path = tmp_path / "phase.parquet"
    pq.write_table(t, path)
    rp = _load("rp_t", "contributor_tools/common/release_package.py")
    part = rp.Part(path, "synthetic")
    off = math.radians(-5.0)
    key = ("o1", "left")
    r = ff.Reassess({"S1": off}, {key: ["ankle_dorsiflexion_angle_ipsi_rad", "cop_anterior_ipsi_m"]}, {key: {}}, "phase")
    r.scan_part(part, rp)
    direct0 = int(np.sum((np.degrees(ank) < -80) | (np.degrees(ank) > 50)))
    direct1 = int(np.sum((np.degrees(ank - off) < -80) | (np.degrees(ank - off) > 50)))
    assert direct1 == direct0 + 1
    ch = r.changes()
    assert ch == {key: {"ankle_dorsiflexion_angle_ipsi_rad": direct1}}
    assert r.l2_flips == 0 and r.l2_pairs > 0
    assert r.mismatches() == []
    assert len(r.listed[(key, "ankle_dorsiflexion_angle_ipsi_rad")]) == direct1
    r.finish()                                    # frozen results survive the release of the per-observation bookkeeping
    assert r.changes() == ch and r.mismatches() == [] and not r.rows and not r.checked
    assert r.old_count(key, "ankle_dorsiflexion_angle_ipsi_rad") == direct0
    assert len(r.listed[(key, "ankle_dorsiflexion_angle_ipsi_rad")]) == direct1
    entry = {"failed_samples": {}, "failed_channels": [], "failed_limits": [], "status": "no_failure_found",
             "channel_states": {"pass_offset_unverified": ["ankle_dorsiflexion_angle_ipsi_rad"], "pass": ["cop_anterior_ipsi_m"]},
             "attributes": {"checks": {"L1": "passed", "L5": "passed"}}}
    e = ff.apply_changes(entry, ch[key], ff.VOCAB_GT23)
    assert e["status"] == "failed" and e["failed_limits"] == ["L1"] and e["failed_channels"] == ["ankle_dorsiflexion_angle_ipsi_rad"]
    assert e["channel_states"]["fail"] == ["ankle_dorsiflexion_angle_ipsi_rad"] and e["attributes"]["checks"]["L1"] == "failed"
    # and back: a failure that the shift removes returns to the dataset's own pass state; other causes keep it failed
    back = ff.apply_changes(e, {"ankle_dorsiflexion_angle_ipsi_rad": 0}, ff.VOCAB_GT23)
    assert back["status"] == "no_failure_found" and back["channel_states"]["pass_offset_unverified"] == ["ankle_dorsiflexion_angle_ipsi_rad"]
    assert ff.checked_columns(entry, ff.VOCAB_GT23, ("L1", "L5")) == ["ankle_dorsiflexion_angle_ipsi_rad", "cop_anterior_ipsi_m"]
    assert ff.checked_columns(entry, ff.VOCAB_GT23, ("L5",)) == ["cop_anterior_ipsi_m"]
    e2 = dict(e, failed_limits=["L1", "L2"], failed_samples={"x": {"L2": 3}, "ankle_dorsiflexion_angle_ipsi_rad": {"L1": 1}})
    e3 = ff.apply_changes(e2, {"ankle_dorsiflexion_angle_ipsi_rad": 0}, ff.VOCAB_GT23)
    assert e3["status"] == "failed" and e3["failed_limits"] == ["L2"]


def test_angle_range_attribute_shift():
    attrs = {"angle_range_deg": {"foot_sagittal_angle_ipsi_rad": [-10.0, 30.0], "knee_flexion_angle_ipsi_rad": [0.0, 60.0]}}
    out = ff.shift_angle_range_attribute(attrs, -5.0)
    assert out["angle_range_deg"]["foot_sagittal_angle_ipsi_rad"] == [-5.0, 35.0]
    assert out["angle_range_deg"]["knee_flexion_angle_ipsi_rad"] == [0.0, 60.0]
    out = ff.shift_angle_range_attribute({"angle_range_deg": {"foot_sagittal_angle_left_rad": [None, None], "ankle_dorsiflexion_angle_left_rad": [1.0, None]}}, 2.0)
    assert out["angle_range_deg"]["foot_sagittal_angle_left_rad"] == [None, None]
    assert out["angle_range_deg"]["ankle_dorsiflexion_angle_left_rad"] == [-1.0, None]


def test_readback_lockstep_and_bit_equal_helpers():
    rb = _load("readback_ff_t", "contributor_tools/readback_foot_flat.py")
    rb.STEP = 7
    t1 = pa.table({"observation_id": [f"o{i // 5}" for i in range(23)], "x": [float(i) for i in range(23)]})
    t2 = pa.table({"observation_id": [f"o{i // 5}" for i in range(23)], "x": [float(i) for i in range(23)]})
    pieces_a = (t1.slice(i, 4) for i in range(0, 23, 4))     # different batch sizes on the two sides
    pieces_b = (t2.slice(i, 9) for i in range(0, 23, 9))
    n = 0
    for a, b in rb.lockstep(pieces_a, pieces_b):
        assert a.num_rows == b.num_rows and a.equals(b)
        n += a.num_rows
    assert n == 23
    with pytest.raises(ValueError):
        list(rb.lockstep(iter([t1]), iter([t2.slice(0, 20)])))
    nan_a = pa.chunked_array([[1.0, float("nan"), 3.0]])
    assert rb.bit_equal(nan_a, nan_a) and not rb.bit_equal(nan_a, pa.chunked_array([[1.0, float("nan"), 3.5]]))
