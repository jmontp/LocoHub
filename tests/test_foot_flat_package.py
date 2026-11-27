"""CORE-FOOT-01 end to end on a tiny SYNTHETIC package: build 'old', rebuild 'new' with the foot-flat mixin, run the readback.

Everything is made-up numbers (two synthetic participants, one with an offset). Nothing here reads a dataset.
"""
import importlib.util
import json
import math
import os
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from contributor_tools.common import release_package as rp

ROOT = Path(__file__).resolve().parents[1]
N = 150


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ff = _load("foot_flat_pkg_t", "contributor_tools/common/foot_flat.py")
ffa = _load("foot_flat_adapter_pkg_t", "contributor_tools/common/foot_flat_adapter.py")
rb = _load("readback_foot_flat_pkg_t", "contributor_tools/readback_foot_flat.py")

OFFSET = math.radians(-5.0)
OBS = [("S1", "S1/r1", "a", "left"), ("S1", "S1/r1", "b", "left"), ("S2", "S2/r1", "c", "left")]


def _table():
    rng = np.random.default_rng(3)
    cols = {k: [] for k in ("subject", "source_recording_id", "observation_id", "reference_side", "observation_type", "task", "task_id",
                            "task_info", "held_signals", "phase_ipsi", "shank_sagittal_angle_ipsi_rad", "foot_sagittal_angle_ipsi_rad",
                            "ankle_dorsiflexion_angle_ipsi_rad", "cop_anterior_ipsi_m", "cop_vertical_ipsi_m", "cop_lateral_ipsi_m",
                            "knee_flexion_angle_ipsi_rad")}
    for subj, rec, oid, side in OBS:
        shank = rng.normal(0, 0.05, N)
        foot = rng.normal(0, 0.05, N)
        if oid == "a":
            foot[10] = math.radians(48.0) + shank[10]   # ankle = 48 deg: inside L1 until the -5 deg offset makes it 53 deg
        ankle = foot - shank
        for i in range(N):
            for k, v in (("subject", subj), ("source_recording_id", rec), ("observation_id", oid), ("reference_side", side),
                         ("observation_type", "individual_cycle"), ("task", "level_walking"), ("task_id", "w1"), ("task_info", "{}"),
                         ("held_signals", "{}"), ("phase_ipsi", i * 100.0 / (N - 1))):
                cols[k].append(v)
        cols["shank_sagittal_angle_ipsi_rad"] += list(shank)
        cols["foot_sagittal_angle_ipsi_rad"] += list(foot)
        cols["ankle_dorsiflexion_angle_ipsi_rad"] += list(ankle)
        cols["cop_anterior_ipsi_m"] += list(rng.normal(0.0, 0.05, N))
        cols["cop_vertical_ipsi_m"] += list(rng.normal(0.0, 0.02, N))
        cols["cop_lateral_ipsi_m"] += list(rng.normal(0.0, 0.02, N))
        cols["knee_flexion_angle_ipsi_rad"] += list(rng.normal(0.3, 0.1, N))
    return pa.table(cols)


def _entry(subj, rec, oid, side):
    return {"observation_id": oid, "reference_side": side, "table": "phase", "observation_type": "individual_cycle", "subject": subj,
            "source_recording_id": rec, "task": "level_walking", "task_id": "w1", "rows": N, "status": "no_failure_found",
            "failed_limits": [], "failed_channels": [], "failed_samples": {}, "limitations": [], "flight": None, "attributes": {},
            "held_signals": {},
            "channel_states": {"pass": ["cop_anterior_ipsi_m", "cop_vertical_ipsi_m", "cop_lateral_ipsi_m", "knee_flexion_angle_ipsi_rad"],
                               "pass_offset_unverified": ["ankle_dorsiflexion_angle_ipsi_rad"]}}


class OldAdapter(rp.ReleaseAdapter):
    dataset_id = "syn"
    release_id = "v1"
    tables = ("phase",)
    preview_columns = ("foot_sagittal_angle_ipsi_rad",)

    def __init__(self, root):
        self.root = Path(root)
        pq.write_table(_table(), self.root / "src.parquet")

    def table_parts(self, table):
        return [rp.Part(self.root / "src.parquet", "SYN-SRC")]

    def assessment_entries(self):
        for o in OBS:
            yield _entry(*o)

    def evidence_tables(self):
        return {"assessment_failure_samples.csv": (["observation_id", "reference_side", "table", "channel", "limit", "sample_index",
                                                    "phase_percent", "value", "reason"], [])}

    def input_hashes(self):
        return {"src": rp.sha256_file(self.root / "src.parquet")}

    def bound_hashes(self):
        return {"adapter": "0" * 64}

    def lineage_inputs(self):
        return {"assessment": "1" * 64}


class NewAdapter(ffa.FootFlatMixin, OldAdapter):
    ff_dataset = "SYN"
    ff_vocab = ff.VOCAB_GT23
    ff_limits = {"phase": ("L1", "L5")}
    ff_failed_check_ids = {}
    ff_bound_files = ()

    def __init__(self, root, offsets_root):
        super().__init__(root)
        self.release_id = "v2"
        self.ff_init(rp, ff, offsets_root)

    def table_parts(self, table):
        import dataclasses
        return [dataclasses.replace(p, transform=self.ff_tf[table]) for p in super().table_parts(table)]

    def prepare(self):
        self.ff_prepare()


@pytest.fixture()
def packages(tmp_path):
    (tmp_path / "docs/quality/audits").mkdir(parents=True)
    (tmp_path / "docs/quality/audits/foot-flat-offsets.json").write_text(json.dumps(
        {"datasets": {"SYN": {"people": {"S1": {"offset_rad": OFFSET}}, "persons_without_offset": ["S2"]}}}))
    src = tmp_path / "src"; src.mkdir()
    base = tmp_path / "pk"; base.mkdir()
    code, s_old = rp.build_package(OldAdapter(src), base / "old", stage="pilot", log=lambda *_: None)
    assert code == 0, [c for c in s_old["checks"] if not c["pass"]]
    new = NewAdapter(src, tmp_path)
    new.prepare()
    code, s_new = rp.build_package(new, base / "new", stage="pilot", log=lambda *_: None)
    return tmp_path, base, code, s_new, new


def test_rebuild_flips_exactly_the_shifted_observation_and_accounts_for_it(packages):
    tmp, base, code, summary, new = packages
    assert code == 0 and summary["all_pass"], [c for c in summary["checks"] if not c["pass"]]
    assert {k: v for k, v in new.ff_flips.items()} .keys() == {("a", "left", "phase")}
    flip = new.ff_flips[("a", "left", "phase")]
    assert flip["status_before"] == "no_failure_found" and flip["status_after"] == "failed" and flip["causes_after"] == "L1"
    import csv
    ex = list(csv.DictReader(open(base / "new/exclusions.csv")))
    assert [r["exclusion_id"] for r in ex] == ["a|left"] and ex[0]["reason_code"] == "L1"
    assert pq.ParquetFile(base / "new/filtered_phase.parquet").metadata.num_rows == 2 * N
    assert pq.ParquetFile(base / "old/filtered_phase.parquet").metadata.num_rows == 3 * N


def test_independent_readback_passes_and_catches_a_wrong_shift(packages, monkeypatch):
    tmp, base, code, summary, new = packages
    monkeypatch.setattr(rb, "ROOT", tmp)
    monkeypatch.setattr(rb, "BASE", "pk")
    monkeypatch.setitem(rb.LIMITS_BY_TABLE, "SYN", {"phase": True, "time": False})
    args = SimpleNamespace(dataset="SYN", old_package="old", new_package="new", tables="phase", subset=False, skip_manifest=False,
                           output_root="out_ok")
    assert rb.run(args) == 0
    res = json.loads((tmp / "out_ok/readback.json").read_text())
    assert res["all_pass"] and {c["id"] for c in res["checks"]} >= {"R1", "R2.phase", "R3.phase", "R4.phase", "R5.phase", "R6.phase", "R7.phase", "R8.phase", "R9b"}
    # tamper with the offsets the readback reads: it must now fail R4 and R6
    p = tmp / "docs/quality/audits/foot-flat-offsets.json"
    d = json.loads(p.read_text())
    d["datasets"]["SYN"]["people"]["S1"]["offset_rad"] = OFFSET * 2
    p.write_text(json.dumps(d))
    args.output_root = "out_bad"
    assert rb.run(args) == 1
    bad = json.loads((tmp / "out_bad/readback.json").read_text())
    failed = {c["id"] for c in bad["checks"] if not c["pass"]}
    assert {"R4.phase", "R6.phase"} <= failed
