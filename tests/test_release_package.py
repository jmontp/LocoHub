"""Release package builder (contributor_tools/common/release_package.py). Every fixture is SYNTHETIC (made-up numbers)."""
import os
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from contributor_tools.common import release_package as rp

N = 150


def _rows(table, obs, label_value):
    """obs: [(recording, observation_id, side)] -> one pa.Table (phase: 150 rows each; time: 6 rows each)."""
    cols = {k: [] for k in ("subject", "source_recording_id", "observation_id", "reference_side", "observation_type", "task",
                            "task_id", "task_info", "held_signals", "idx", "v_ipsi", "h_ipsi")}
    for rec, oid, side in obs:
        n = N if table == "phase" else 6
        for i in range(n):
            cols["subject"].append("S1"); cols["source_recording_id"].append(rec); cols["observation_id"].append(oid)
            cols["reference_side"].append(side)
            cols["observation_type"].append("individual_cycle" if table == "phase" else "continuous_recording")
            cols["task"].append("level_walking"); cols["task_id"].append("w1"); cols["task_info"].append("{}")
            cols["held_signals"].append(json.dumps({"h_ipsi": "held for a stated reason"}))
            cols["idx"].append(i * 100.0 / (N - 1) if table == "phase" else i * 0.005)
            cols["v_ipsi"].append(label_value + i); cols["h_ipsi"].append(float("nan"))
    cols[("phase_ipsi" if table == "phase" else "time_s")] = cols.pop("idx")
    return pa.table(cols)


class TinyAdapter(rp.ReleaseAdapter):
    dataset_id = "tiny"
    release_id = "v1"
    title = "Tiny synthetic package"
    preview_columns = ("v_ipsi",)
    group_rows = 400

    def __init__(self, root):
        self.root = Path(root)
        # SYNTHETIC: recordings S1/r1 (two legs of a, one of b) and S1/r2 (c), r2 is replaced by a second part
        for table in ("phase", "time"):
            if table == "phase":
                first = [("S1/r1", "a", "left"), ("S1/r1", "a", "right"), ("S1/r1", "b", "left"), ("S1/r2", "OLD", "left")]
                second = [("S1/r2", "c", "left")]
            else:
                first = [("S1/r1", "r1/continuous", "none"), ("S1/r2", "OLDT", "none")]
                second = [("S1/r2", "r2/continuous", "none")]
            pq.write_table(_rows(table, first, 1.0), self.root / f"first_{table}.parquet")
            pq.write_table(_rows(table, second, 100.0), self.root / f"second_{table}.parquet")

    def table_parts(self, table):
        return [rp.Part(self.root / f"first_{table}.parquet", "E01", drop_recordings=frozenset({"S1/r2"})),
                rp.Part(self.root / f"second_{table}.parquet", "E02", expect_recordings=frozenset({"S1/r2"}))]

    def assessment_entries(self):
        def entry(oid, side, table, otype, rec, status="no_failure_found", causes=(), limits=()):
            return {"observation_id": oid, "reference_side": side, "table": table, "observation_type": otype, "subject": "S1",
                    "source_recording_id": rec, "task": "level_walking", "task_id": "w1", "rows": N if table == "phase" else 6,
                    "status": status, "failed_limits": list(causes), "failed_channels": ["v_ipsi"] if causes else [],
                    "failed_samples": {"v_ipsi": {"L1": 3}} if causes else {}, "limitations": list(limits), "flight": None,
                    "attributes": {}, "held_signals": {"h_ipsi": "held for a stated reason"},
                    "channel_states": {"pass": ["v_ipsi"], "not_checked_no_column": ["h_ipsi"]}}
        yield entry("a", "left", "phase", "individual_cycle", "S1/r1", limits=["flag_x"])
        yield entry("a", "right", "phase", "individual_cycle", "S1/r1", limits=["flag_x"])
        yield entry("b", "left", "phase", "individual_cycle", "S1/r1", status="failed", causes=["L1"])
        yield entry("c", "left", "phase", "individual_cycle", "S1/r2")
        yield entry("r1/continuous", "none", "time", "continuous_recording", "S1/r1")
        yield entry("r2/continuous", "none", "time", "continuous_recording", "S1/r2")

    def exclusion_rows(self):
        return [{"exclusion_id": "seg1", "subject": "S1", "source_recording_id": "S1/r1", "reference_side": "both",
                 "stage": "upstream_not_released", "kind": "export_exclusion", "reason_code": "too_short",
                 "reason": "segment left out at export: too_short", "in_full_variant": False, "in_filtered_variant": False}]

    def evidence_tables(self):
        return {"windows.csv": (["id", "fate"], [{"id": "w1", "fate": "exported"}])}

    def limitations(self, entries):
        return [{"id": "flag_x", "title": "Flag X", "text": "synthetic limitation", **rp.count_flag(entries, "flag_x")}]

    def readme_sections(self):
        return [("Synthetic note", "This package is built from made-up numbers.")]

    def input_hashes(self):
        return {p.name: rp.sha256_file(p) for p in sorted(self.root.glob("*.parquet"))}

    def bound_hashes(self):
        return {"adapter": "0" * 64}

    def lineage_inputs(self):
        return {"assessment": "1" * 64}

    def extra_checks(self, ctx):
        return [("X1", "second part supplied the replacing observations only", 2, ctx["part_observations"].get("E02"))]


@pytest.fixture()
def package(tmp_path):
    src = tmp_path / "src"; src.mkdir()
    adapter = TinyAdapter(src)
    out = tmp_path / "pkg"
    code, summary = rp.build_package(adapter, out, stage="pilot", log=lambda *_: None)
    return out, code, summary


def test_layout_and_counts(package):
    out, code, summary = package
    assert code == 0 and summary["all_pass"], [c for c in summary["checks"] if not c["pass"]]
    names = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    assert names == sorted(["full_phase.parquet", "full_time.parquet", "filtered_phase.parquet", "filtered_time.parquet",
                            "exclusions.csv", "assessment.jsonl", "limitations.json", "dataset_index.json", "phase_preview.json",
                            "test_summary.json", "README.md", "manifest.json", "manifest.sha256", "evidence/windows.csv"])
    # full: a(2 legs), b, c = 4 phase observations, 2 continuous; the replaced OLD / OLDT rows are gone
    assert pq.ParquetFile(out / "full_phase.parquet").metadata.num_rows == 4 * N
    assert pq.ParquetFile(out / "filtered_phase.parquet").metadata.num_rows == 3 * N      # b failed
    assert pq.ParquetFile(out / "full_time.parquet").metadata.num_rows == 12
    assert pq.ParquetFile(out / "filtered_time.parquet").metadata.num_rows == 12
    t = pq.read_table(out / "full_phase.parquet")
    assert pq.ParquetFile(out / "full_phase.parquet").schema_arrow.field("task_info").type == pa.string()   # readers see plain strings
    assert set(t.column("observation_id").to_pylist()) == {"a", "b", "c"}
    assert set(t.column("source_export").to_pylist()) == {"E01", "E02"}
    c_rows = t.filter(pa.array([x == "c" for x in t.column("observation_id").to_pylist()]))
    assert c_rows.column("v_ipsi").to_pylist()[0] == 100.0           # the replacing part's values, not the old ones
    f = pq.read_table(out / "filtered_phase.parquet")
    assert "b" not in set(f.column("observation_id").to_pylist()) and set(f.column("quality_status").to_pylist()) == {"no_failure_found"}
    assert set(t.column("quality_status").to_pylist()) == {"no_failure_found", "failed"}


def test_exclusions_assessment_and_limitations(package):
    out, _, _ = package
    rows = list(csv.DictReader(open(out / "exclusions.csv")))
    assert [r["exclusion_id"] for r in rows] == ["seg1", "b|left"]
    assert rows[1]["stage"] == "filtered_variant_only" and rows[1]["kind"] == "assessment_failed" and rows[1]["reason_code"] == "L1"
    assert set(rows[0]) == set(rp.EXCLUSION_FIELDS)
    lines = [json.loads(l) for l in open(out / "assessment.jsonl")]
    assert len(lines) == 6 and {l["in_filtered_variant"] for l in lines if l["observation_id"] == "b"} == {False}
    lim = json.load(open(out / "limitations.json"))["limitations"][0]
    assert lim["id"] == "flag_x" and lim["observations"] == 2 and lim["in_filtered_variant"] == 2


def test_manifest_hashes_and_binding(package):
    out, _, _ = package
    man = json.load(open(out / "manifest.json"))
    for rel, info in man["files"].items():
        assert hashlib.sha256((out / rel).read_bytes()).hexdigest() == info["sha256"]
        assert (out / rel).stat().st_size == info["bytes"]
    assert set(man["files"]) == {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()} - {"manifest.json", "manifest.sha256"}
    assert open(out / "manifest.sha256").read().split()[0] == hashlib.sha256((out / "manifest.json").read_bytes()).hexdigest()
    idx, prev, ts, lim = (json.load(open(out / n)) for n in ("dataset_index.json", "phase_preview.json", "test_summary.json", "limitations.json"))
    assert idx["binding"] == prev["binding"] == ts["binding"] == man["binding"] == lim["binding"]
    assert man["binding"]["full_phase.parquet"] == man["files"]["full_phase.parquet"]["sha256"]
    assert man["binding"]["counts"]["observations_full"] == 6 and man["binding"]["counts"]["observations_filtered"] == 5
    assert man["scientific_approval"] is False and man["local_only"] is True
    assert "made-up numbers" in open(out / "README.md").read()


def test_preview_from_written_filtered_phase(package):
    out, _, _ = package
    prev = json.load(open(out / "phase_preview.json"))
    g = prev["groups"][0]["columns"]["v_ipsi"]
    # filtered phase observations: a(left,right) = 1..150 and c = 100..249 -> mean at phase 0 is (1+1+100)/3
    assert g["mean"][0] == pytest.approx(102 / 3, abs=1e-6) and g["n_max"] == 3


def test_refuses_to_overwrite_and_rejects_bad_input(tmp_path):
    src = tmp_path / "src"; src.mkdir()
    adapter = TinyAdapter(src)
    out = tmp_path / "pkg"
    out.mkdir()
    with pytest.raises(FileExistsError):
        rp.build_package(adapter, out, stage="pilot", log=lambda *_: None)

    class Dropping(TinyAdapter):                       # an observation with no assessment entry must stop the build
        def assessment_entries(self):
            return (e for e in super().assessment_entries() if e["observation_id"] != "a" or e["reference_side"] != "right")
    with pytest.raises(rp.PackageError):
        rp.build_package(Dropping(src), tmp_path / "pkg2", stage="pilot", log=lambda *_: None)

    class BadStage(TinyAdapter):
        def exclusion_rows(self):
            return [{"exclusion_id": "x", "stage": "somewhere", "kind": "k", "reason_code": "r"}]
    with pytest.raises(rp.PackageError):
        rp.build_package(BadStage(src), tmp_path / "pkg3", stage="pilot", log=lambda *_: None)


def test_account_rules():
    full = {("a", "l"), ("b", "l"), ("c", "l")}
    assert rp.account(full, {("a", "l"), ("b", "l")}, {("c", "l")}) == []
    assert rp.account(full, {("a", "l"), ("b", "l")}, set())
    assert rp.account(full, full, {("c", "l")})
