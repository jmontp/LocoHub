"""UM21-T04 runner, on SYNTHETIC fixtures only (the synthetic Streaming file of test_um21_sign_adapter and
hand-made observation lists). Expected values are known by construction: which observation ids equal hook
unit ids, frame counts, and the bitwise content of the written rows. The only real files read are the seven
committed T03 launcher receipts (no research data). Nothing is launched."""
import json

import h5py
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from contributor_tools import run_um21_t04_signs as t04
from contributor_tools.common import sign_application as sa
from contributor_tools.guarded_launcher import validate_spec
from tests.test_um21_sign_adapter import world, BUILD, UNITS  # noqa: F401  (fixture)

P = "um21:Streaming/AB02/Tread/i0"


# ---------------------------------------------------------------- ids and reasons
def test_parse_and_reason_known_values():
    p = t04.parse_observation_id(f"{P}:left:frames:100:129")
    assert p == {"subject": "AB02", "condition": "i0", "leg": "left", "a": 100, "b": 129}
    assert "29 frames, below" in t04.unmapped_reason(p)
    assert "269 frames, above" in t04.unmapped_reason({**p, "a": 0, "b": 269})
    assert "not a pair of consecutive" in t04.unmapped_reason({**p, "a": 0, "b": 60})
    for bad in ("um21:Streaming/AB02/Tread/i0:up:frames:1:2", "x", None, f"{P}:left:frames:1:2 "):
        with pytest.raises(ValueError):
            t04.parse_observation_id(bad)


def test_mapping_is_exact_and_accounts_for_every_observation():
    units = {"right": [f"{P}:right:frames:1:61", f"{P}:right:frames:61:121"], "left": [f"{P}:left:frames:5:65"]}
    obs = [(f"{P}:right:frames:61:121", "right"), (f"{P}:left:frames:5:65", "left"),
           (f"{P}:right:frames:200:229", "right"), (f"{P}:left:frames:5:66", "left")]
    rows, extra = t04.map_observations(obs, units, "AB02/i0")
    assert [r["status"] for r in rows] == ["mapped", "mapped", "unmapped", "unmapped"]
    assert [r["unit_index"] for r in rows[:2]] == [1, 0]
    assert extra == {"right": 1, "left": 0}  # one hook unit has no observation
    assert "29 frames" in rows[2]["reason"] and "not a pair" in rows[3]["reason"]
    assert all(r["hook_unit_id"] == r["observation_id"] for r in rows[:2])


def test_mapping_refuses_wrong_recording_side_or_duplicates():
    units = {"right": [f"{P}:right:frames:1:61"], "left": []}
    with pytest.raises(ValueError, match="does not belong"):
        t04.map_observations([("um21:Streaming/AB03/Tread/i0:right:frames:1:61", "right")], units, "AB02/i0")
    with pytest.raises(ValueError, match="disagrees"):
        t04.map_observations([(f"{P}:right:frames:1:61", "left")], units, "AB02/i0")
    with pytest.raises(ValueError, match="duplicate"):
        t04.map_observations([(f"{P}:right:frames:1:61", "right")] * 2, units, "AB02/i0")


def test_selection_and_table_roundtrip(tmp_path):
    rng = np.random.default_rng(3)
    right = {"hip_angle": rng.normal(size=(3, 150)), "pelvis_tilt": rng.normal(size=(3, 150))}
    left = {"hip_angle": rng.normal(size=(2, 150)), "pelvis_tilt": rng.normal(size=(2, 150)),
            "knee_power": rng.normal(size=(2, 150))}  # held on the right
    rows = [{"observation_id": "o1", "leg": "left", "status": "mapped", "unit_index": 1},
            {"observation_id": "o2", "leg": "right", "status": "unmapped", "unit_index": None},
            {"observation_id": "o3", "leg": "right", "status": "mapped", "unit_index": 2}]
    ids, arrays, dropped = t04.select_observation_arrays(rows, {"right": right, "left": left})
    assert ids == ["o1", "o3"] and sorted(arrays) == ["hip_angle", "pelvis_tilt"] and dropped == ["knee_power"]
    assert np.array_equal(arrays["hip_angle"][0], left["hip_angle"][1])
    assert np.array_equal(arrays["hip_angle"][1], right["hip_angle"][2])
    path = tmp_path / "t.parquet"
    t04.write_observation_table(path, ids, arrays, ["left", "right"])
    assert t04.reload_check(path, ids, arrays) == []
    with pytest.raises(FileExistsError):
        t04.write_observation_table(path, ids, arrays, ["left", "right"])  # never overwrites
    t = pq.read_table(path)
    assert t.num_rows == 300 and t.column("sample").to_pylist()[:3] == [0, 1, 2]


# ---------------------------------------------------------------- end to end on the synthetic recording
def test_process_recording_synthetic(world, tmp_path):
    with h5py.File(world["path"], "r") as handle:
        facts, results = t04.um21.convert_recording(handle, "AB02/i0", BUILD)
    r_units, l_units = results[0].unit_ids, results[1].unit_ids
    assert results[0].leg == "right" and UNITS - 1 == len(r_units)
    obs = [(r_units[0], "right"), (r_units[5], "right"), (l_units[3], "left"),
           (f"{P}:right:frames:400:430", "right"),        # 30 frames: no hook unit
           (f"{P}:left:frames:3:70", "left")]              # inside the rule, not a heel-strike pair
    phase = tmp_path / "phase.parquet"
    pq.write_table(pa.table({"observation_id": [o for o, _ in obs for _ in range(150)],
                             "reference_side": [s for _, s in obs for _ in range(150)]}), phase)
    t03 = {"phase": str(phase), "sha256": t04.sha256_file(phase), "job": "synthetic"}
    out = tmp_path / "out"
    with h5py.File(world["path"], "r") as handle:
        summ, groups, logs, fbg, slots, _ = t04.process_recording(handle, "AB02/i0", t03, BUILD, out, sa.BACKLOG_PATH)
    assert (summ["t03_observations"], summ["mapped"], summ["unmapped"]) == (5, 3, 2)
    assert summ["findings"] == [] and all(not v for v in fbg.values())
    assert set(summ["unmapped_reasons"]) == {obs[3][0], obs[4][0]}
    assert "30 frames" in summ["unmapped_reasons"][obs[3][0]] and "not a pair" in summ["unmapped_reasons"][obs[4][0]]
    assert summ["hook_units_without_observation"] == {"right": UNITS - 1 - 2, "left": UNITS - 1 - 1}
    rdir = out / "records" / "AB02_i0"
    tbl = pq.read_table(rdir / "observations_signed.parquet")
    assert tbl.column("observation_id").to_pylist()[::150] == [obs[0][0], obs[1][0], obs[2][0]]
    # written rows are the hook's arrays at the unit, bit for bit; unmapped observations are absent
    want = results[0]
    got = tbl.column("hip_angle").to_numpy().reshape(3, 150)
    assert got[1].tobytes() == want.published["hip_angle"][5].tobytes()
    assert got[2].tobytes() == results[1].published["hip_angle"][3].tobytes()
    held = set(want.application.log["channels"]) - set(want.published)
    assert not held & set(tbl.column_names)  # held channels are never written
    doc = json.loads((rdir / "observation_map.json").read_text())
    assert doc["evidence"]["right"]["hook_units"] == UNITS - 1 and doc["scientific_approval"] is False
    assert (rdir / "groups").is_dir() and len(list((rdir / "groups").iterdir())) == 2


def test_t03_hash_mismatch_is_refused(tmp_path):
    phase = tmp_path / "p.parquet"
    pq.write_table(pa.table({"observation_id": ["a"], "reference_side": ["right"]}), phase)
    with pytest.raises(ValueError, match="sha256 differs"):
        t04.read_t03_observations(str(phase), "0" * 64)


# ---------------------------------------------------------------- proxy
def test_mode_proxy_hands_the_record_to_the_bound_hook_only_in_full_mode():
    class Base:
        marker = 7
        def run_sign_application(self, **kw):
            return kw
    px = t04.ModeProxy(Base(), "docs/quality/audits/x.json")
    assert "pilot_record_path" not in px.run_sign_application(mode="pilot")
    assert px.run_sign_application(mode="full")["pilot_record_path"].endswith("x.json")
    assert px.marker == 7
    with pytest.raises(ValueError, match="--pilot-record"):
        t04.ModeProxy(Base()).run_sign_application(mode="full")


# ---------------------------------------------------------------- receipts and spec (no research data)
def test_t03_records_come_from_the_seven_receipts():
    rec = t04.t03_records()
    assert len(rec) == 44
    assert not any("t03_batch2_" in v["phase"] for v in rec.values())  # the INVALID failed run
    counts = {}
    for v in rec.values():
        counts[v["job"]] = counts.get(v["job"], 0) + 1
    assert counts == {"batch0": 11, "batch1": 11, "v2-batch2": 5, "v2-batch3": 5, "v2-batch4": 4,
                      "v2-batch5": 4, "v2-batch6": 4}
    assert not set(rec) & set(t04.um21.EXCLUDED)


def test_specs_validate_and_samples_are_as_reviewed():
    for stage, n in (("a", 1), ("b", 7)):
        spec = t04.build_spec(stage)
        validate_spec(spec)
        recs = spec["command"][spec["command"].index("--recordings") + 1].split(",")
        assert len(recs) == n == len(set(recs))
        assert not set(recs) & set(t04.um21.EXCLUDED) and set(recs) <= set(t04.t03_records())
        assert spec["address_space_mib"] == 768 and "--mode" in spec["command"]
        assert t04.RUNNER in spec["bindings"] and t04.pilot.ADAPTER in spec["bindings"]
        assert all(t04.T03_RECEIPT.format(j) in spec["bindings"] for j in t04.T03_JOBS)
        assert spec["bindings"] == {**spec["bindings"], **sa.bound_build()}
    census = json.loads((t04.ROOT / t04.CENSUS).read_text())
    b = t04.sample_b(census)
    assert t04.build_spec("a")["command"][t04.build_spec("a")["command"].index("--recordings") + 1] == "AB04/i0"
    assert b[0] == "AB05/i5" and "AB04/i0" not in b
    assert b == t04.sample_b(census)  # seeded, reproducible
    assert b[1] in t04.pilot.layout_2_candidates(census)


def test_multi_chunk_table_roundtrip(tmp_path):
    rng = np.random.default_rng(9)
    n = 45  # three row groups of 20, 20, 5 observations
    arrays = {"hip_angle": rng.normal(size=(n, 150)), "knee_moment": rng.normal(size=(n, 150))}
    ids = [f"o{i}" for i in range(n)]
    path = tmp_path / "t.parquet"
    t04.write_observation_table(path, ids, arrays, ["right"] * n)
    assert pq.ParquetFile(path).num_row_groups == 3
    assert t04.reload_check(path, ids, arrays) == []
    bad = {k: a.copy() for k, a in arrays.items()}
    bad["knee_moment"][41, 7] += 1e-12  # one value in the last chunk
    assert any("knee_moment" in f for f in t04.reload_check(path, ids, bad))


def test_mapped_rows_carry_their_leg_multipliers(world, tmp_path):
    with h5py.File(world["path"], "r") as handle:
        _, results = t04.um21.convert_recording(handle, "AB02/i0", BUILD)
    obs = [(results[0].unit_ids[0], "right")]
    phase = tmp_path / "phase.parquet"
    pq.write_table(pa.table({"observation_id": [obs[0][0]] * 150, "reference_side": ["right"] * 150}), phase)
    t03 = {"phase": str(phase), "sha256": t04.sha256_file(phase), "job": "synthetic"}
    with h5py.File(world["path"], "r") as handle:
        t04.process_recording(handle, "AB02/i0", t03, BUILD, tmp_path / "o", sa.BACKLOG_PATH)
    row = json.loads((tmp_path / "o/records/AB02_i0/observation_map.json").read_text())["observations"][0]
    assert row["multiplier_scope"].startswith("per channel per leg")
    assert row["leg_channel_multipliers"]["pelvis_tilt"]["multiplier"] in (-1, 1)
    assert set(row["leg_channel_multipliers"]) == set(results[0].application.log["channels"])


# ---------------------------------------------------------------- address-space probe (synthetic, one record size)
PROBE = r"""
import os, resource, sys
os.environ["ARROW_NUM_THREADS"] = "1"
import numpy as np
sys.path.insert(0, sys.argv[3])
from contributor_tools import run_um21_t04_signs as t04   # sets ARROW_DEFAULT_MEMORY_POOL before pyarrow loads
assert os.environ["ARROW_DEFAULT_MEMORY_POOL"] == "system"
resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 ** 2, 768 * 1024 ** 2))
obs = t04.read_t03_observations(sys.argv[1])
assert len(obs) == 250, len(obs)
rng = np.random.default_rng(1)
arrays = {f"c{i}": rng.normal(size=(250, 150)) for i in range(20)}
ids = [o for o, _ in obs]
t04.write_observation_table(sys.argv[2], ids, arrays, [s for _, s in obs])
assert t04.reload_check(sys.argv[2], ids, arrays) == []
vm = int([l for l in open("/proc/self/status") if l.startswith("VmPeak")][0].split()[1]) / 1024
print(f"RSS_MIB {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.0f} VMPEAK_MIB {vm:.0f}")
"""


def test_read_and_write_paths_fit_the_launcher_address_space(tmp_path):
    """One synthetic record the size of a T03 phase table (250 observations x 150 rows, 114 columns), read and
    the signed table written and reloaded in a child limited to 768 MiB address space (RLIMIT_AS)."""
    import subprocess
    import sys
    rng = np.random.default_rng(0)
    n = 250 * 150
    cols = {"observation_id": [f"{P}:right:frames:{i}:{i + 60}" for i in range(250) for _ in range(150)],
            "reference_side": ["right"] * n}
    cols.update({f"x{i}": rng.normal(size=n) for i in range(112)})
    phase = tmp_path / "phase.parquet"
    pq.write_table(pa.table(cols), phase)
    r = subprocess.run(["nice", "-n", "19", sys.executable, "-c", PROBE, str(phase), str(tmp_path / "o.parquet"),
                        str(t04.ROOT)], capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-800:]
    rss = int(r.stdout.split("RSS_MIB")[1].split()[0])
    assert rss < 300, r.stdout


# ---------------------------------------------------------------- one-leg rule (R01)
def _hl(**kw):
    """leg log channels: name -> (publication, multiplier)"""
    return {k: {"publication": v[0], "multiplier": v[1]} for k, v in kw.items()}


def _dlog(**kw):
    return {"derived": kw}


def test_one_leg_rule_known_cases():
    pub1, held = ("publish", 1), ("hold", 1)
    right = _hl(hip_angle=pub1, pelvis_tilt=("publish", -1), hip_power=pub1, knee_power=held, ankle_power=("publish", -1),
                knee_angle=pub1)
    left = _hl(hip_angle=pub1, pelvis_tilt=("publish", 1), hip_power=held, knee_power=held, ankle_power=("publish", -1),
               knee_angle=pub1)
    seg = {"thigh_angle": {"inputs_sha256": {"pelvis_tilt": "x", "hip_angle": "y"}},
           "shank_angle": {"inputs_sha256": {"thigh_angle": "x", "knee_angle": "y"}}}
    vel = {"hip_angle_velocity": {"from": "hip_angle"}, "thigh_angle_velocity": {"from": "thigh_angle"}}
    kept, dec, flags = t04.settle_recording({"right": right, "left": left}, {"right": _dlog(**seg), "left": _dlog(**seg)},
                                            {"right": _dlog(**vel), "left": _dlog(**vel)})
    assert {"hip_angle", "knee_angle", "ankle_power"} <= kept
    assert not kept & {"hip_power", "knee_power", "pelvis_tilt"}
    assert dec["hip_power"]["decision"] == "hold" and "left leg did not publish" in dec["hip_power"]["decided_by"]
    assert dec["knee_power"]["decided_by"] == "both legs held"
    # pelvis multipliers differ (-1 vs +1): both held and flagged
    assert dec["pelvis_tilt"]["flag"] == "multiplier_disagreement"
    assert flags == [{"kind": "multiplier_disagreement", "channel": "pelvis_tilt", "multipliers": {"left": 1, "right": -1}}]
    # derived follow their inputs: thigh needs pelvis (not kept); shank needs thigh (not kept)
    assert "thigh_angle" not in kept and "shank_angle" not in kept and "thigh_angle_velocity" not in kept
    assert "hip_angle_velocity" in kept and dec["hip_angle_velocity"]["decision"] == "derive"
    assert "pelvis_tilt" in dec["thigh_angle"]["decided_by"]


def test_one_leg_rule_all_agree_and_missing_leg_channel():
    same = _hl(hip_angle=("publish", 1), pelvis_tilt=("publish", -1))
    seg = {"thigh_angle": {"inputs_sha256": {"pelvis_tilt": "x", "hip_angle": "y"}}}
    vel = {"thigh_angle_velocity": {"from": "thigh_angle"}}
    kept, dec, flags = t04.settle_recording({"right": same, "left": dict(same)}, {"right": _dlog(**seg), "left": _dlog(**seg)},
                                            {"right": _dlog(**vel), "left": _dlog(**vel)})
    assert kept == {"hip_angle", "pelvis_tilt", "thigh_angle", "thigh_angle_velocity"} and flags == []
    one_missing = {"hip_angle": same["hip_angle"]}
    kept, dec, _ = t04.settle_recording({"right": same, "left": one_missing}, {"right": _dlog(**seg), "left": _dlog()},
                                        {"right": _dlog(**vel), "left": _dlog()})
    assert kept == {"hip_angle"} and dec["pelvis_tilt"]["legs"]["left"]["publication"] == "absent"
    assert dec["thigh_angle"]["decided_by"] == "not derived on both legs"
    with pytest.raises(ValueError, match="both legs"):
        t04.settle_recording({"right": same}, {"right": _dlog()}, {"right": _dlog()})


def test_process_recording_applies_the_rule_to_written_columns(world, tmp_path):
    """On the real hook output of the synthetic recording: written columns are exactly the kept ones."""
    with h5py.File(world["path"], "r") as handle:
        _, results = t04.um21.convert_recording(handle, "AB02/i0", BUILD)
    obs = [(results[0].unit_ids[0], "right")]
    phase = tmp_path / "phase.parquet"
    pq.write_table(pa.table({"observation_id": [obs[0][0]] * 150, "reference_side": ["right"] * 150}), phase)
    t03 = {"phase": str(phase), "sha256": t04.sha256_file(phase), "job": "synthetic"}
    with h5py.File(world["path"], "r") as handle:
        summ, *_ = t04.process_recording(handle, "AB02/i0", t03, BUILD, tmp_path / "o", sa.BACKLOG_PATH)
    doc = json.loads((tmp_path / "o/records/AB02_i0/observation_map.json").read_text())
    kept = {k for k, d in doc["recording_rule"]["decisions"].items() if d["decision"] in ("publish", "derive")}
    assert set(summ["written_columns"]) == kept and kept
    assert set(summ["channels_held_by_rule"]).isdisjoint(summ["written_columns"])


# ---------------------------------------------------------------- full-mode gate, against the REAL bound hook
def test_full_mode_gate_with_the_real_hook(world, monkeypatch, tmp_path):
    rec_path = t04.pilot_record_path()
    assert rec_path.endswith(t04.PILOT_RECORD)
    monkeypatch.setattr(t04.um21, "sa", t04.ModeProxy(sa, rec_path))
    with h5py.File(world["path"], "r") as handle:
        _, res = t04.um21.convert_recording(handle, "AB02/i0", BUILD, mode="full")
    facts = res[0].application.log["pilot"]
    assert res[0].application.log["mode"] == "full" and facts["pilot_task"] == "CORE-11-P-UM21"
    # refusals come from the unmodified hook: no record, a record outside the audits folder
    for bad in (None, str(tmp_path / "missing.json")):
        monkeypatch.setattr(t04.um21, "sa", t04.ModeProxy(sa, bad))
        with h5py.File(world["path"], "r") as handle:
            with pytest.raises((sa.PilotGateError, ValueError)):
                t04.um21.convert_recording(handle, "AB02/i0", BUILD, mode="full")
    copy = tmp_path / "record.json"
    copy.write_bytes((t04.ROOT / t04.PILOT_RECORD).read_bytes())
    monkeypatch.setattr(t04.um21, "sa", t04.ModeProxy(sa, str(copy)))
    with h5py.File(world["path"], "r") as handle:
        with pytest.raises(sa.PilotGateError, match="audits"):
            t04.um21.convert_recording(handle, "AB02/i0", BUILD, mode="full")


def test_pilot_record_constant_is_enforced(tmp_path):
    with pytest.raises(ValueError, match="differs from the reviewed constant"):
        t04.pilot_record_path(expected="0" * 64)
    assert t04.sha256_file(t04.ROOT / t04.PILOT_RECORD) == t04.PILOT_RECORD_SHA256
    assert t04.sha256_file(t04.ROOT / t04.PILOT_RECEIPT) == t04.PILOT_RECEIPT_SHA256


def test_full_specs_one_subject_per_batch_bind_the_gate():
    batches = t04.subject_batches()
    assert sum(len(v) for v in batches.values()) == 44 and len(batches) == 10
    assert not set(sum(batches.values(), [])) & set(t04.um21.EXCLUDED)
    for subject, recs in batches.items():
        spec = t04.build_spec("full", subject)
        validate_spec(spec)
        assert spec["command"][spec["command"].index("--recordings") + 1].split(",") == recs
        assert spec["command"][-2:] == ["--subject", subject] and "full" in spec["command"]
        assert spec["bindings"][t04.PILOT_RECORD] == t04.PILOT_RECORD_SHA256
        assert spec["bindings"][t04.PILOT_RECEIPT] == t04.PILOT_RECEIPT_SHA256
        assert all(t04.T03_RECEIPT.format(j) in spec["bindings"] for j in t04.T03_JOBS)
        assert spec["address_space_mib"] == 768
    assert len({t04.build_spec("full", s)["output_root"] for s in batches}) == 10
    with pytest.raises(ValueError, match="unknown subject"):
        t04.build_spec("full", "AB99")
