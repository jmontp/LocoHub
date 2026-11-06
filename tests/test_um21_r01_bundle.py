"""UM21-R01 bundle rules. All fixtures here are SYNTHETIC (made-up numbers), not UMich data."""
import os
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

import json
import numpy as np
import pytest

from contributor_tools import run_um21_r01_bundle as r01

N = r01.N


def test_reexpression_of_made_up_wrapped_angle():
    # SYNTHETIC: a true ankle angle of +23 deg stored 180 deg away as -157 deg; another stored unwrapped at -193.3
    raw_rad = np.radians([-157.0, -193.3, 14.0, np.nan])
    new_rad, raw_deg, new_deg = r01.reexpress_ankle_rad(raw_rad)
    assert np.allclose(new_deg[:2], [23.0, -13.3], atol=1e-9)
    assert np.isclose(new_deg[2], -166.0)  # a sample already in the normal branch would move: the caller must only
    assert np.isnan(new_deg[3]) and np.isnan(new_rad[3])  # ... apply it to whole strides inside a ledger run
    assert np.allclose(np.degrees(new_rad[:2]), new_deg[:2])
    back, _, _ = r01.reexpress_ankle_rad(new_rad)  # applying the rule twice returns the original angle (mod 360)
    assert np.allclose(r01.wrap_deg(np.degrees(back[:3]) - raw_deg[:3]), 0.0, atol=1e-9)


def test_wrap_bounds():
    w = r01.wrap_deg([-540.0, -180.0, 0.0, 179.9, 180.0, 360.0])
    assert np.allclose(w, [-180.0, -180.0, 0.0, 179.9, -180.0, 0.0])


def test_classify_stride_by_ledger_runs_and_steps():
    runs0, steps0 = [(1000, 2000), (3000, 3500)], [1100, 3050]
    assert r01.classify_stride(1000, 1099, runs0, steps0) == "inside_clean"
    assert r01.classify_stride(1099, 1200, runs0, steps0) == "inside_jump"
    assert r01.classify_stride(2100, 2400, runs0, steps0) == "outside"
    assert r01.classify_stride(1950, 2100, runs0, steps0) == "partial"
    assert r01.classify_stride(3100, 3200, runs0, steps0) == "inside_clean"
    # a stride ending on the run's first frame (shared heel-strike frame) overlaps by one frame: not a stretch stride
    assert r01.classify_stride(900, 1000, runs0, steps0) == "outside"
    assert r01.classify_stride(2000, 2100, runs0, steps0) == "outside"
    assert r01.classify_stride(901, 1001, runs0, steps0) == "partial"


def test_jump_check_uses_the_q01_limit():
    ok = np.linspace(-10, 20, N)
    assert not r01.has_jump(ok)
    bad = ok.copy()
    bad[60:] += 170.0
    assert r01.has_jump(bad)
    assert not r01.has_jump(np.array([1.0, np.nan, 90.0]))  # a pair with a missing sample is not a jump


def _ex(oid, full, filt, stage):
    return r01.exclusion_row(oid, "AB00/i0", "right", stage, "x", "why", "D-0", full, filt)


def test_exclusion_accounting_full_and_filtered():
    # SYNTHETIC ids: a released, b in full only (failed), c dropped from both, d unmapped
    upstream = ["a", "b", "c", "d"]
    ex = [_ex("b", True, False, "filtered_variant_only"), _ex("c", False, False, "release_membership"),
          _ex("d", False, False, "upstream_not_released")]
    assert r01.account({"a", "b"}, {"a"}, upstream, ex) == []
    # b silently missing from filtered
    assert r01.account({"a", "b"}, {"a"}, upstream, ex[1:])
    # c silently missing from both
    assert r01.account({"a", "b"}, {"a"}, upstream, [ex[0], ex[2]])
    # an excluded id also released in both variants
    assert r01.account({"a", "b"}, {"a", "b"}, upstream, ex)
    # filtered holds something full does not
    assert r01.account({"a"}, {"a", "b"}, upstream, ex)


def test_held_status_text_only_for_held_power():
    assert r01.held_status("hip_power", "hold") == "held: sign unsettled"
    assert r01.held_status("hip_power", "publish") is None
    assert r01.held_status("hip_angle", "hold") is None


def test_column_list_is_stable_and_names_follow_reference():
    names = [v[0] for v in r01.COLUMNS.values()]
    assert len(names) == len(set(names)) == 15
    assert all("contra" not in n for n in names)
    assert not any("foot" in n for n in names) and "foot_angle" in r01.NOT_RELEASED
    assert {"hip_flexion_power_ipsi_W_kg", "knee_flexion_power_ipsi_W_kg", "ankle_dorsiflexion_power_ipsi_W_kg"} <= set(names)
    assert r01.COLUMNS["ankle_angle"][2] == "offset_unverified"


def _meta(oid, side="right"):
    return {"subject": "UM21_AB00", "source_recording_id": "um21:Streaming/AB00/Tread/i0", "observation_id": oid,
            "reference_side": side, "observation_type": "individual_cycle", "task": "level_walking", "task_id": "t",
            "task_info": "{}", "source_start_time_s": 1.0, "source_end_time_s": 2.0}


def test_synthetic_bundle_tables_held_columns_and_variants(tmp_path):
    import pyarrow.parquet as pq
    schema = r01.make_schema()
    n = 3 * N
    out = {name: np.linspace(0, 1, n) for name, _u, _s in r01.COLUMNS.values()}
    for ch in r01.POWER_CHANNELS:  # held power: all missing
        out[r01.COLUMNS[ch][0]] = np.full(n, np.nan)
    held = sorted(r01.COLUMNS[c][0] for c in r01.POWER_CHANNELS)
    rows = [{"oid": f"o{i}", "a": i * N, "b": (i + 1) * N, "meta": _meta(f"o{i}"), "overall": ov, "failed_limits": fl,
             "failed_channels": [], "reexpressed": False, "held": held, "kept": kept, "recording": "AB00/i0"}
            for i, (ov, fl, kept) in enumerate([("no_failure_found", [], True), ("failed", ["L1"], True),
                                                ("no_failure_found", [], False)])]
    ctx = {"lineage_id": "L", "assessment_id": "A"}
    full, nf = r01.to_table(rows, out, schema, ctx, False)
    filt, nfi = r01.to_table(rows, out, schema, ctx, True)
    assert (nf, nfi) == (2, 1)  # the dropped observation is in neither; the failed one only in full
    assert full.schema.names == filt.schema.names
    for name in held:
        assert np.isnan(full.column(name).to_numpy()).all()
    assert set(full.column("held_signals").to_pylist()) == {json.dumps({c: "held: sign unsettled" for c in held})}
    pq.write_table(full, tmp_path / "f.parquet", row_group_size=r01.ROW_GROUP_ROWS)
    pq.write_table(filt, tmp_path / "g.parquet", row_group_size=r01.ROW_GROUP_ROWS)
    a, b = r01.readback(tmp_path / "f.parquet"), r01.readback(tmp_path / "g.parquet", preview=True)
    assert (a["observations"], b["observations"], a["bad_grid_events"], b["bad_grid_events"]) == (2, 1, 0, 0)
    assert a["finite_values_in_held_columns"] == 0 and a["finite_values_by_column"]["hip_flexion_power_ipsi_W_kg"] == 0
    assert a["finite_values_by_column"]["hip_flexion_angle_ipsi_rad"] == 2 * N
    prev = r01.preview_json(b["preview_groups"], {"x": 1})
    g = prev["groups"][0]
    assert g["observations"] == 1 and g["columns"]["hip_flexion_power_ipsi_W_kg"]["n"] == [0] * N
    assert g["columns"]["hip_flexion_angle_ipsi_rad"]["n"] == [1] * N


def test_committed_ledger_gives_29_clean_and_2_jump_strides():
    # Real committed ledger (small JSON, no scientific arrays): the C03 census says 31 inside strides, 29 without jumps.
    c03 = r01.load_c03()
    kinds = [r01.classify_stride(a, b, c03["runs0"], c03["step0"]) for a, b in c03["inside_pairs"]]
    assert kinds.count("inside_clean") == 29 and kinds.count("inside_jump") == 2 and "partial" not in kinds
    assert c03["census_counts"]["inside_without_step_over_20deg"] == 29
