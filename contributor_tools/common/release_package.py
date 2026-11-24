"""One streaming release-package builder for any LocoHub dataset.

The package layout is defined in contributor_tools/DATA_CONTRACT.md ("Release package"). This module writes it, and
nothing in it is specific to one dataset. Everything dataset-specific lives in a small adapter (a ReleaseAdapter subclass):
the input roots and their hash checks, the source exclusions, the structured assessment entries and the limitation entries.

It complements build_dataset_release.py: that builder is in-memory (256 MiB / 500,000-row admission, which is not raised);
this one streams and is meant for exports that do not fit that admission.

How it stays within the memory rules:
  * One table at a time (all phase parts, then all time parts), so only two Parquet writers (full, filtered) are open; an open
    writer keeps about 80 KB of metadata per row group, so row groups are 12,000 rows by default.
  * Source files are read as record batches of at most 3,000 rows with Arrow threads off; each batch is filtered and extended
    by a few string columns, appended to the writers and dropped. Row groups are flushed when 12,000 rows are pending.
  * Only the compact assessment entries (identity, status, counts; no channel lists) and per-observation row counters stay
    resident. Channel states and held columns are folded into counters while assessment.jsonl is written.
  * glibc is told to keep few arenas and to return large blocks to the system, and memory is trimmed after every batch.
  * The caller (a runner under contributor_tools.guarded_launcher) enforces one worker, nice 19 and the address-space cap
    through assert_guarded(); this module never starts a worker.

Nothing is repaired, resampled, filled or re-labelled. The filtered variant drops exactly the observations whose assessment
status is 'failed' and nothing else. scientific_approval is always false here.
"""
from __future__ import annotations

import os
for _key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_key, "1")
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")  # must precede pyarrow under an address-space cap
import collections
import csv
import dataclasses
import gc
import hashlib
import json
from pathlib import Path
import resource
import time
from typing import Any, Iterable, Iterator, Optional

import numpy as np

try:  # few arenas, large blocks via mmap, prompt trimming (address-space cap)
    import ctypes
    _LIBC = ctypes.CDLL("libc.so.6")
    _LIBC.mallopt(-8, 2)            # M_ARENA_MAX
    _LIBC.mallopt(-3, 256 * 1024)   # M_MMAP_THRESHOLD
    _LIBC.mallopt(-1, 256 * 1024)   # M_TRIM_THRESHOLD
except OSError:  # pragma: no cover
    _LIBC = None

PACKAGE_SCHEMA = "locohub.release_package/1"
TABLES = ("phase", "time")
VARIANTS = ("full", "filtered")
FIXED_FILES = ("exclusions.csv", "assessment.jsonl", "limitations.json", "dataset_index.json", "phase_preview.json",
               "test_summary.json", "README.md", "manifest.json", "manifest.sha256")
EXTRA_COLUMNS = ("source_export", "quality_status", "failed_limits", "limitations", "lineage_id", "assessment_id")
NOT_FAILED = "no_failure_found"
FAILED = "failed"
STAGES = ("upstream_not_released", "release_membership", "filtered_variant_only")
EXCLUSION_FIELDS = ["exclusion_id", "observation_id", "subject", "source_recording_id", "reference_side", "stage", "kind",
                    "reason_code", "reason", "decision", "in_full_variant", "in_filtered_variant", "task", "task_id",
                    "start_s", "end_s", "detail"]
ASSESSMENT_REQUIRED = ("observation_id", "reference_side", "table", "observation_type", "subject", "source_recording_id",
                       "task", "task_id", "rows", "status", "failed_limits", "failed_channels", "failed_samples",
                       "limitations", "flight", "attributes", "held_signals", "channel_states")
N = 150
READ_BATCH_ROWS = 3000
DEFAULT_GROUP_ROWS = 12000
RSS_CAP_MIB = 450.0
MIN_AVAILABLE_BYTES = 2 * 1024 ** 3


class PackageError(ValueError):
    pass


# ------------------------------------------------------------------ resource helpers
def trim_memory():
    if _LIBC is not None:
        _LIBC.malloc_trim(0)


def peak_rss_mib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def current_rss_mib():
    with open("/proc/self/statm") as f:
        return int(f.read().split()[1]) * os.sysconf("SC_PAGE_SIZE") / 1024 ** 2


def mem_available():
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    raise RuntimeError("MemAvailable missing")


def assert_guarded(address_space_mib):
    """Refuse to run outside the guarded launcher envelope (niceness 19, address-space cap)."""
    if os.nice(0) < 19:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (niceness 19 expected)")
    soft, _ = resource.getrlimit(resource.RLIMIT_AS)
    if soft == resource.RLIM_INFINITY or soft > address_space_mib * 1024 ** 2:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (address-space limit expected)")
    if mem_available() < MIN_AVAILABLE_BYTES:
        raise MemoryError("less than 2 GiB available; not started")


def dict_schema(schema):
    """The same schema with every string column dictionary-encoded (long repeated strings such as task_info cost 4 bytes per
    row instead of their length while batches wait for a row group). The files are written with store_schema=False, so a
    reader still sees plain string columns."""
    import pyarrow as pa
    return pa.schema([pa.field(f.name, pa.dictionary(pa.int32(), pa.string())) if pa.types.is_string(f.type) else f for f in schema])


def open_part(fh):
    """ParquetFile that decodes string columns as dictionaries."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    plain = pq.ParquetFile(fh, buffer_size=0).schema_arrow
    cols = [f.name for f in plain if pa.types.is_string(f.type)]
    return pq.ParquetFile(fh, buffer_size=0, read_dictionary=cols)


def pin_arrow():
    import pyarrow as pa
    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                return h.hexdigest()
            h.update(b)


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


# ------------------------------------------------------------------ adapter
@dataclasses.dataclass(frozen=True)
class Part:
    """One source table file. `drop_recordings` are source_recording_ids whose rows are skipped (replaced by a later part);
    `expect_recordings`, when set, are the only recordings the part may contain."""
    path: Path
    label: str
    drop_recordings: frozenset = frozenset()
    expect_recordings: Optional[frozenset] = None


class ReleaseAdapter:
    """What a dataset supplies. Everything else is the builder's."""

    dataset_id = "dataset"
    release_id = "v1"
    title = "Dataset review package"
    tables = TABLES
    preview_columns: tuple = ()
    unchecked_families: tuple = ()
    group_rows = DEFAULT_GROUP_ROWS

    def table_parts(self, table: str) -> list:
        raise NotImplementedError

    def assessment_entries(self) -> Iterator[dict]:
        """Yield assessment entries with every key of ASSESSMENT_REQUIRED (the structured assessment, one per observation)."""
        raise NotImplementedError

    def exclusion_rows(self) -> Iterable[dict]:
        """Exclusions outside the assessment (source or export exclusions); keys of EXCLUSION_FIELDS (missing ones are empty)."""
        return []

    def evidence_tables(self) -> dict:
        """{name: (fieldnames, row iterable)} written as CSV under evidence/ (dataset-specific downloadable evidence)."""
        return {}

    def limitations(self, entries: list) -> list:
        """Limitation entries (dicts with id, title, text and counts); see count_flag()."""
        return []

    def readme_sections(self) -> list:
        """[(heading, plain-words text)] appended to the README."""
        return []

    def extra_checks(self, ctx: dict) -> list:
        """[(id, description, expected, observed)] on top of the generic checks. ctx has counts, by_class, part_observations."""
        return []

    def input_hashes(self) -> dict:
        return {}

    def bound_hashes(self) -> dict:
        return {}

    def lineage_inputs(self) -> dict:
        return {}


# ------------------------------------------------------------------ pure rules
def batch_runs(oids, sides):
    """Run-length encode consecutive rows by (observation_id, reference_side): [(key, start, end)], end exclusive."""
    runs = []
    n = len(oids)
    i = 0
    while i < n:
        key = (oids[i], sides[i])
        j = i + 1
        while j < n and oids[j] == key[0] and sides[j] == key[1]:
            j += 1
        runs.append((key, i, j))
        i = j
    return runs


def slim(e):
    """Compact resident form of one assessment entry (no channel lists, no held columns)."""
    missing = [k for k in ASSESSMENT_REQUIRED if k not in e]
    if missing:
        raise PackageError(f"assessment entry lacks {missing}")
    return {"key": (e["observation_id"], e["reference_side"]), "table": e["table"], "type": e["observation_type"],
            "subject": e["subject"], "task": e["task"], "task_id": e["task_id"], "rec": e["source_recording_id"],
            "rows": int(e["rows"]), "overall": e["status"], "causes": list(e["failed_limits"]),
            "failed_channels": list(e["failed_channels"]), "failed_samples": e["failed_samples"],
            "limitations": list(e["limitations"]), "flight": e["flight"], "attributes": dict(e["attributes"])}


def account(full_keys, filtered_keys, failed_keys):
    """full = filtered + failed, exactly: no gap, no overlap, no extra."""
    problems = []
    if filtered_keys - full_keys:
        problems.append(f"{len(filtered_keys - full_keys)} filtered observations are not in full")
    if failed_keys - full_keys:
        problems.append(f"{len(failed_keys - full_keys)} failed observations are not in full")
    if filtered_keys & failed_keys:
        problems.append(f"{len(filtered_keys & failed_keys)} observations are both filtered and failed")
    if (full_keys - filtered_keys) != failed_keys:
        problems.append("full minus filtered does not equal the failed set")
    return problems


def assessment_failure_rows(entries):
    """Exclusion rows for observations the assessment marked failed (in full, left out of filtered)."""
    rows = []
    for q in entries:
        if q["overall"] != FAILED:
            continue
        n_samples = sum(sum(v.values()) for v in q["failed_samples"].values())
        rows.append({"exclusion_id": f"{q['key'][0]}|{q['key'][1]}", "observation_id": q["key"][0], "subject": q["subject"],
                     "source_recording_id": q["rec"], "reference_side": q["key"][1], "stage": "filtered_variant_only",
                     "kind": "assessment_failed", "reason_code": "+".join(q["causes"]),
                     "reason": "failed assessment (" + ", ".join(q["causes"]) + ")" +
                               (f" on {', '.join(sorted(q['failed_channels']))}" if q["failed_channels"] else "") +
                               (f"; {n_samples} samples outside limits" if n_samples else ""),
                     "decision": "structured assessment", "in_full_variant": True, "in_filtered_variant": False,
                     "task": q["task"], "task_id": q["task_id"], "start_s": "", "end_s": "",
                     "detail": json.dumps(q["failed_samples"], sort_keys=True)})
    return rows


def count_flag(entries, flag):
    """Counts for one per-observation limitation flag."""
    sel = [q for q in entries if flag in q["limitations"]]
    return {"observations": len(sel),
            "by_type": dict(collections.Counter(q["type"] for q in sel)),
            "recordings": len({q["rec"] for q in sel}),
            "participants": sorted({q["subject"] for q in sel}),
            "in_filtered_variant": sum(1 for q in sel if q["overall"] != FAILED),
            "failed_in_assessment": sum(1 for q in sel if q["overall"] == FAILED),
            "cycles_with_flight": sum(1 for q in sel if q["flight"] is True),
            "cycles_checked_for_flight": sum(1 for q in sel if q["flight"] is not None)}


class Sink:
    """Parquet writer that buffers record batches and writes a row group whenever group_rows rows are pending."""

    def __init__(self, path, schema, group_rows):
        import pyarrow.parquet as pq
        self.w = pq.ParquetWriter(str(path), schema, compression="zstd", store_schema=False)
        self.group_rows, self.buf, self.n, self.rows, self.groups = group_rows, [], 0, 0, 0

    def add(self, table):
        import pyarrow as pa
        if table.num_rows == 0:
            return
        self.buf.append(table)
        self.n += table.num_rows
        while self.n >= self.group_rows:
            t = pa.concat_tables(self.buf)
            self._write(t.slice(0, self.group_rows))
            rest = t.slice(self.group_rows)
            self.buf, self.n = ([rest] if rest.num_rows else []), rest.num_rows

    def _write(self, t):
        self.w.write_table(t, row_group_size=max(t.num_rows, 1))
        self.rows += t.num_rows
        self.groups += 1

    def close(self):
        import pyarrow as pa
        if self.buf:
            self._write(pa.concat_tables(self.buf))
            self.buf, self.n = [], 0
        self.w.close()


# ------------------------------------------------------------------ streaming
def stream_part(part, table_name, q, ctx, sinks, state):
    """Append one source part to the full and filtered sinks of a table; fills state (rows per key, contiguity, schema)."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    fh = open(part.path, "rb")
    try:
        pf = open_part(fh)
        schema = pf.schema_arrow
        if state["schema"].get(table_name) is None:
            state["schema"][table_name] = schema
        elif not schema.equals(state["schema"][table_name]):
            raise PackageError(f"{part.path}: schema differs from the first {table_name} part")
        prev_key = state["prev_key"].get((table_name, str(part.path)))
        for batch in pf.iter_batches(batch_size=READ_BATCH_ROWS, use_threads=False):
            trim_memory()
            oids = batch.column("observation_id").to_pylist()
            sides = batch.column("reference_side").to_pylist()
            recs = batch.column("source_recording_id").to_pylist()
            n = len(oids)
            keep = np.ones(n, dtype=bool)
            quality, causes, lims = [], [], []
            for key, a, b in batch_runs(oids, sides):
                rec = recs[a]
                if rec in part.drop_recordings:
                    keep[a:b] = False
                    quality.extend([None] * (b - a)); causes.extend([None] * (b - a)); lims.extend([None] * (b - a))
                    continue
                if part.expect_recordings is not None and rec not in part.expect_recordings:
                    raise PackageError(f"{part.path}: {rec} is not among the recordings this part may contain")
                if key not in q or q[key]["table"] != table_name or q[key]["rec"] != rec:
                    raise PackageError(f"{part.path}: {key} has no matching assessment entry")
                if key != prev_key:
                    if key in state["closed"]:
                        raise PackageError(f"{part.path}: {key} appears in more than one run")
                    if prev_key is not None:
                        state["closed"].add(prev_key)
                    prev_key = key
                state["rows"][key] = state["rows"].get(key, 0) + (b - a)
                state["export"][key] = part.label
                e = q[key]
                quality.extend([FAILED if e["overall"] == FAILED else NOT_FAILED] * (b - a))
                causes.extend([json.dumps(e["causes"])] * (b - a))
                lims.extend([json.dumps(e["limitations"])] * (b - a))
            state["prev_key"][(table_name, str(part.path))] = prev_key
            if not keep.any():
                continue
            t = pa.Table.from_batches([batch]).filter(pa.array(keep))
            ql = [x for x, k in zip(quality, keep) if k]
            cl = [x for x, k in zip(causes, keep) if k]
            ll = [x for x, k in zip(lims, keep) if k]
            m = len(ql)
            for name, vals in (("source_export", [part.label] * m), ("quality_status", ql), ("failed_limits", cl),
                               ("limitations", ll), ("lineage_id", [ctx["lineage_id"]] * m),
                               ("assessment_id", [ctx["assessment_id"]] * m)):
                t = t.append_column(name, pa.array(vals, type=pa.string()).dictionary_encode())
            sinks[("full", table_name)].add(t)
            sinks[("filtered", table_name)].add(t.filter(pa.array([x != FAILED for x in ql])))
    finally:
        fh.close()


def readback(path, table_name, expect, preview_columns=(), preview=False):
    """Stream one written file: rows, per-observation rows, grid or time-order checks, finite counts per numeric column,
    finite values in held columns, identity columns, optional preview sums."""
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    idx_name = "phase_ipsi" if table_name == "phase" else "time_s"
    obs, closed, state = {}, set(), {}
    prev_key = None
    bad = collections.Counter()
    finite = {}
    held_finite = 0
    ids = {"lineage_id": set(), "assessment_id": set(), "source_export": set(), "quality_status": set()}
    groups = {}
    rows = 0
    with open(path, "rb") as fh:
        pf = open_part(fh)
        names = pf.schema_arrow.names
        numeric = [f.name for f in pf.schema_arrow if pa.types.is_floating(f.type)]
        n_groups = pf.metadata.num_row_groups
        max_rg = max((pf.metadata.row_group(i).num_rows for i in range(n_groups)), default=0)
        for b in pf.iter_batches(batch_size=READ_BATCH_ROWS, use_threads=False):
            oids, sides = b.column("observation_id").to_pylist(), b.column("reference_side").to_pylist()
            idx = b.column(idx_name).to_numpy(zero_copy_only=False)
            rows += len(oids)
            for name in ids:
                ids[name].update(pc.unique(b.column(name)).to_pylist())
            for key, a, e in batch_runs(oids, sides):
                if key != prev_key:
                    if key in closed:
                        bad["non_contiguous"] += 1
                    if prev_key is not None:
                        closed.add(prev_key)
                    prev_key = key
                seg = idx[a:e]
                obs[key] = obs.get(key, 0) + (e - a)
                if table_name == "phase":
                    start = state.get(key, 0)
                    pidx = np.rint(seg * (N - 1) / 100.0).astype(int)
                    if not np.array_equal(pidx, np.arange(start, start + (e - a))) or \
                            np.max(np.abs(seg - pidx * 100.0 / (N - 1))) > 1e-9:
                        bad["phase_grid"] += 1
                    state[key] = start + (e - a)
                else:
                    last = state.get(key, -np.inf)
                    if not (np.all(np.isfinite(seg)) and np.all(np.diff(seg) > 0) and seg[0] > last):
                        bad["time_order"] += 1
                    state[key] = float(seg[-1])
            for c in numeric:
                x = b.column(c).to_numpy(zero_copy_only=False)
                finite[c] = finite.get(c, 0) + int(np.isfinite(x).sum())
            hs = np.array(b.column("held_signals").to_pylist(), dtype=object)
            for text in set(hs.tolist()):
                if text and text not in ("{}", "[]", "null"):
                    held = json.loads(text)
                    mask = hs == text
                    for name in (held if isinstance(held, list) else list(held)):
                        if name in b.schema.names:
                            held_finite += int(np.isfinite(b.column(name).to_numpy(zero_copy_only=False)[mask]).sum())
            if preview:
                gk = list(zip(b.column("task").to_pylist(), b.column("task_id").to_pylist(), b.column("observation_type").to_pylist()))
                pidx_all = np.rint(idx * (N - 1) / 100.0).astype(int)
                for g in set(gk):
                    sel = np.array([k == g for k in gk])
                    acc = groups.setdefault(g, {"obs": set(), **{c: [np.zeros(N), np.zeros(N), np.zeros(N)] for c in preview_columns}})
                    acc["obs"].update({k for k, s in zip(zip(oids, sides), sel) if s})
                    for c in preview_columns:
                        x = b.column(c).to_numpy(zero_copy_only=False)[sel]
                        ok = np.isfinite(x)
                        np.add.at(acc[c][0], pidx_all[sel][ok], 1.0)
                        np.add.at(acc[c][1], pidx_all[sel][ok], x[ok])
                        np.add.at(acc[c][2], pidx_all[sel][ok], x[ok] ** 2)
    pf = None
    gc.collect()
    trim_memory()
    if table_name == "phase":
        bad["short_observation"] += sum(1 for v in obs.values() if v != N)
    else:
        bad["short_observation"] += sum(1 for v in obs.values() if v < 2)
    bad["unexpected_identity_values"] += int(ids["lineage_id"] != {expect["lineage_id"]}) + int(ids["assessment_id"] != {expect["assessment_id"]})
    return {"rows": rows, "observations": len(obs), "obs_rows": obs, "problems": {k: v for k, v in bad.items() if v},
            "finite": finite, "columns": names, "row_groups": n_groups, "max_row_group_rows": max_rg,
            "finite_in_held_columns": held_finite, "quality_values": sorted(ids["quality_status"]),
            "source_exports": sorted(ids["source_export"]), "preview_groups": groups}


def preview_json(groups, columns, binding):
    out = []
    for g in sorted(groups):
        acc = groups[g]
        entry = {"task": g[0], "task_id": g[1], "observation_type": g[2], "observations": len(acc["obs"]), "columns": {}}
        for c in columns:
            n, s1, s2 = acc[c]
            with np.errstate(invalid="ignore", divide="ignore"):
                mean = np.where(n > 0, s1 / np.maximum(n, 1), np.nan)
                var = np.where(n > 1, (s2 - n * mean ** 2) / np.maximum(n - 1, 1), np.nan)
            sd = np.sqrt(np.maximum(var, 0.0))
            entry["columns"][c] = {"n_min": int(n.min()), "n_max": int(n.max()),
                                   "mean": [None if not np.isfinite(v) else round(float(v), 6) for v in mean],
                                   "sd": [None if not np.isfinite(v) else round(float(v), 6) for v in sd]}
        out.append(entry)
    return {"description": "Mean and sample standard deviation per phase sample (150 points, 0 to 100 percent inclusive) of the "
                           "FILTERED phase file, by task, task_id and observation type, over the listed columns of every "
                           "reference leg. Computed from the written filtered_phase.parquet; no smoothing. n_min and n_max "
                           "are the fewest and most finite values at any phase sample.",
            "binding": binding, "groups": out}


def write_csv(path, rows, fields):
    with open(path, "x", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, restval="", extrasaction="raise")
        w.writeheader()
        w.writerows(rows)


def write_json(path, obj):
    with open(path, "x") as f:
        json.dump(obj, f, indent=1, allow_nan=False)


# ------------------------------------------------------------------ the builder
def build_package(adapter, out_dir, *, stage, started=None, rss_cap_mib=RSS_CAP_MIB, log=print):
    """Write one release package to a new directory. Returns (exit code, test_summary dict)."""
    import pyarrow as pa
    started = started or time.time()
    pin_arrow()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=False)
    input_hashes, bound = adapter.input_hashes(), adapter.bound_hashes()
    assessment_files = adapter.lineage_inputs()
    ctx = {"lineage_id": sha256_bytes(json.dumps({**input_hashes, **bound}, sort_keys=True).encode()),
           "assessment_id": sha256_bytes(json.dumps(assessment_files, sort_keys=True).encode())}
    tables = tuple(adapter.tables)
    # 1. assessment: stream into assessment.jsonl, keep only the compact entries
    q, agg = {}, {"states": collections.Counter(), "held": collections.Counter()}
    with open(out / "assessment.jsonl", "x") as af:
        for raw in adapter.assessment_entries():
            e = slim(raw)
            if e["key"] in q:
                raise PackageError(f"duplicate assessment entry {e['key']}")
            q[e["key"]] = e
            for st, cols in raw["channel_states"].items():
                for c in cols:
                    agg["states"][(raw["table"], c, st)] += 1
            for c, reason in raw["held_signals"].items():
                agg["held"][(raw["table"], c, reason)] += 1
            af.write(json.dumps({**raw, "in_full_variant": True, "in_filtered_variant": raw["status"] != FAILED}, sort_keys=True) + "\n")
    state = {"schema": {}, "prev_key": {}, "closed": set(), "rows": {}, "export": {}}
    problems = []
    part_obs = collections.Counter()
    # 2. tables, one at a time
    for table_name in tables:
        parts = adapter.table_parts(table_name)
        with open(parts[0].path, "rb") as fh:
            base = open_part(fh).schema_arrow
        schema = pa.schema(list(base) + [pa.field(n, pa.dictionary(pa.int32(), pa.string())) for n in EXTRA_COLUMNS])
        sinks = {(v, table_name): Sink(out / f"{v}_{table_name}.parquet", schema, adapter.group_rows) for v in VARIANTS}
        try:
            for part in parts:
                if mem_available() < MIN_AVAILABLE_BYTES:
                    raise MemoryError("less than 2 GiB available; stopped at a part boundary")
                t0 = time.time()
                stream_part(part, table_name, q, ctx, sinks, state)
                trim_memory()
                log(f"{table_name} {part.label} {Path(part.path).parent.name}: peak RSS {peak_rss_mib():.0f} MiB, "
                    f"current RSS {current_rss_mib():.0f} MiB, {time.time() - t0:.0f} s")
                if peak_rss_mib() > rss_cap_mib:
                    raise MemoryError(f"peak RSS {peak_rss_mib():.0f} MiB above {rss_cap_mib}; stopped")
        finally:
            for s in sinks.values():
                s.close()
            sinks = None
            gc.collect()
            trim_memory()  # the closed writers' row-group metadata is returned before the next table and the readback
    for key, e in q.items():
        if e["table"] in tables and state["rows"].get(key) != e["rows"]:
            problems.append(f"{key}: {state['rows'].get(key)} rows written, the assessment entry says {e['rows']}")
    for key, label in state["export"].items():
        part_obs[label] += 1
    entries = list(q.values())
    failed_entries = [e for e in entries if e["overall"] == FAILED]
    failed_keys = {e["key"] for e in failed_entries}
    # 3. exclusions and evidence
    excl = list(adapter.exclusion_rows()) + assessment_failure_rows(entries)
    for r in excl:
        if r.get("stage") not in STAGES:
            raise PackageError(f"exclusion stage {r.get('stage')!r} is not one of {STAGES}")
    write_csv(out / "exclusions.csv", excl, EXCLUSION_FIELDS)
    evidence = {}
    if adapter.evidence_tables():
        (out / "evidence").mkdir()
        for name, (fields, rows) in adapter.evidence_tables().items():
            write_csv(out / "evidence" / name, rows, list(fields))
            evidence[name] = True
    # 4. hashes and readback of the written tables
    files = {f"{v}_{t}": f"{v}_{t}.parquet" for v in VARIANTS for t in tables}
    hashes = {name: sha256_file(out / name) for name in files.values()}
    rb = {}
    for (v, t) in ((v, t) for v in VARIANTS for t in tables):
        rb[(v, t)] = readback(out / files[f"{v}_{t}"], t, ctx, adapter.preview_columns,
                              preview=(v == "filtered" and t == "phase"))
    full_keys = set().union(*[set(rb[("full", t)]["obs_rows"]) for t in tables])
    filt_keys = set().union(*[set(rb[("filtered", t)]["obs_rows"]) for t in tables])
    acc_problems = account(full_keys, filt_keys, failed_keys)
    by_stage = collections.Counter(r["stage"] for r in excl)
    by_kind = collections.Counter(r["kind"] for r in excl)
    by_reason = {k: dict(collections.Counter(r["reason_code"] for r in excl if r["kind"] == k)) for k in by_kind}
    entry_counts = lambda es: dict(collections.Counter(e["type"] for e in es))  # noqa: E731
    counts = {
        "tables": list(tables), "observations_full": len(full_keys), "observations_filtered": len(filt_keys),
        "failed_observations": len(failed_keys),
        "full": {**{f"{t}_rows": rb[("full", t)]["rows"] for t in tables},
                 **{f"{t}_observations": len(rb[("full", t)]["obs_rows"]) for t in tables},
                 "observations_by_type": entry_counts(entries)},
        "filtered": {**{f"{t}_rows": rb[("filtered", t)]["rows"] for t in tables},
                     **{f"{t}_observations": len(rb[("filtered", t)]["obs_rows"]) for t in tables},
                     "observations_by_type": entry_counts([e for e in entries if e["overall"] != FAILED])},
        "exclusions_total": len(excl), "exclusions_by_stage": dict(by_stage), "exclusions_by_kind": dict(by_kind),
        "exclusions_by_reason": by_reason,
        "assessment_failures_by_cause": dict(collections.Counter(c for e in failed_entries for c in e["causes"])),
        "assessment_failures_by_table": dict(collections.Counter(e["table"] for e in failed_entries)),
        "observations_by_part_label": dict(part_obs),
    }
    binding = {**hashes, "exclusions_sha256": sha256_file(out / "exclusions.csv"),
               "assessment_sha256": sha256_file(out / "assessment.jsonl"),
               "counts": {"observations_full": counts["observations_full"], "observations_filtered": counts["observations_filtered"],
                          "failed_observations": counts["failed_observations"],
                          **{f"full_{t}_rows": counts["full"][f"{t}_rows"] for t in tables},
                          **{f"filtered_{t}_rows": counts["filtered"][f"{t}_rows"] for t in tables},
                          "exclusions_total": counts["exclusions_total"]},
               "lineage_id": ctx["lineage_id"], "assessment_id": ctx["assessment_id"]}
    # 5. checks
    fe = lambda v, t: rb[(v, t)]  # noqa: E731
    failed_rows = {t: sum(e["rows"] for e in failed_entries if e["table"] == t) for t in tables}
    q_rows = {t: sum(e["rows"] for e in entries if e["table"] == t) for t in tables}
    ctx_checks = {"counts": counts, "by_kind": dict(by_kind), "part_observations": dict(part_obs), "entries": entries,
                  "problems": problems}
    checks = [
        ("T1", "every phase observation has exactly 150 rows on the inclusive 0-100 grid, every time observation is sorted with "
               "at least 2 finite timestamps, and rows are contiguous, in every table file", {},
         {f"{v}_{t}": fe(v, t)["problems"] for v in VARIANTS for t in tables if fe(v, t)["problems"]}),
        ("T2", "full and filtered write the same column list for each table",
         [fe("full", t)["columns"] for t in tables], [fe("filtered", t)["columns"] for t in tables]),
        ("T3", "the observations in the full files are exactly the assessed observations, with the assessed row counts",
         {"missing_or_extra": 0, **{f"rows_{t}": q_rows[t] for t in tables}},
         {"missing_or_extra": len(full_keys ^ set(q)) + sum(1 for t in tables for k, v in fe("full", t)["obs_rows"].items() if q[k]["rows"] != v),
          **{f"rows_{t}": fe("full", t)["rows"] for t in tables}}),
        ("T4", "full = filtered + failed: no gap, no overlap, no extra", [], acc_problems),
        ("T5", "filtered rows = full rows minus the rows of the failed observations, for each table",
         {t: fe("full", t)["rows"] - failed_rows[t] for t in tables}, {t: fe("filtered", t)["rows"] for t in tables}),
        ("T6", "every failed observation is listed in exclusions.csv (stage filtered_variant_only) and nothing else differs",
         sorted(f"{k[0]}|{k[1]}" for k in failed_keys),
         sorted(r["exclusion_id"] for r in excl if r["kind"] == "assessment_failed")),
        ("T7", "held columns hold no finite value where an observation names them held (both variants)", 0,
         sum(fe(v, t)["finite_in_held_columns"] for v in VARIANTS for t in tables)),
        ("T8", "quality_status is no_failure_found throughout the filtered files and failed appears in the full files only when the assessment failed an observation",
         {"filtered": [NOT_FAILED], "full_has_failed": bool(failed_keys)},
         {"filtered": sorted(set().union(*[set(fe("filtered", t)["quality_values"]) for t in tables])),
          "full_has_failed": FAILED in set().union(*[set(fe("full", t)["quality_values"]) for t in tables])}),
        ("T9", "no other problems were recorded while reading", [], problems),
        ("T10", "the files carry one lineage_id and one assessment_id on every row", 0,
         sum(fe(v, t)["problems"].get("unexpected_identity_values", 0) for v in VARIANTS for t in tables)),
        ("T11", "assessment.jsonl lists every observation once", len(q), sum(1 for _ in open(out / "assessment.jsonl"))),
        ("T12", "every exclusion row names a known stage and the stage counts add up to the total", counts["exclusions_total"], sum(by_stage.values())),
    ]
    checks += list(adapter.extra_checks(ctx_checks))
    test_rows = [{"id": i, "check": d, "expected": ex, "observed": ob, "pass": ex == ob} for i, d, ex, ob in checks]
    test_summary = {"scientific_approval": False, "stage": stage, "binding": binding, "checks": test_rows,
                    "all_pass": all(t["pass"] for t in test_rows),
                    "note": "Computed by the package builder from the written files. A separate readback script re-checks the "
                            "package independently."}
    # 6. limitations, index, preview
    limitations = adapter.limitations(entries)
    states = collections.defaultdict(collections.Counter)
    for (t, c, st), n in agg["states"].items():
        states[(t, c)][st] += n
    held_cols = collections.defaultdict(lambda: {"observations": 0, "reasons": {}})
    for (t, c, reason), n in agg["held"].items():
        held_cols[(t, c)]["observations"] += n
        held_cols[(t, c)]["reasons"][reason] = n
    signal_states = {f"{t}:{c}": dict(v) for (t, c), v in sorted(states.items())}
    held_summary = {f"{t}:{c}": v for (t, c), v in sorted(held_cols.items())}
    unchecked_cols = sorted(k for k, v in signal_states.items() if set(v) <= {"unchecked", "not_checked_no_column"})
    by_rec = collections.defaultdict(list)
    for e in entries:
        by_rec[e["rec"]].append(e)
    recs_index = [{"source_recording_id": rec, "subject": es[0]["subject"], "task": es[0]["task"],
                   "source_export": sorted({state["export"].get(e["key"]) for e in es} - {None}),
                   "observations_full": len(es), "observations_filtered": sum(1 for e in es if e["overall"] != FAILED),
                   "individual_cycles": sum(1 for e in es if e["type"] == "individual_cycle"),
                   "transfers": sum(1 for e in es if e["type"] == "transfer"),
                   "continuous": sum(1 for e in es if e["type"] == "continuous_recording")} for rec, es in sorted(by_rec.items())]
    index = {"release": f"{adapter.dataset_id}-{adapter.release_id}", "scientific_approval": False, "stage": stage,
             "binding": binding,
             "files": {f"{v}_{t}": {"file": files[f"{v}_{t}"], "rows": fe(v, t)["rows"], "observations": len(fe(v, t)["obs_rows"]),
                                    "row_groups": fe(v, t)["row_groups"]} for v in VARIANTS for t in tables},
             "counts": counts, "recordings": recs_index,
             "finite_values_by_column": {t: {v: fe(v, t)["finite"] for v in VARIANTS} for t in tables},
             "signal_states_by_table_and_column": signal_states, "held_columns": held_summary,
             "unchecked_columns": unchecked_cols, "extra_columns": list(EXTRA_COLUMNS)}
    pcols = [c for c in adapter.preview_columns if c in rb[("filtered", "phase")]["columns"]] if "phase" in tables else []
    preview = preview_json(rb[("filtered", "phase")]["preview_groups"], pcols, binding) if "phase" in tables else \
        {"description": "no phase table", "binding": binding, "groups": []}
    write_json(out / "limitations.json", {"schema": PACKAGE_SCHEMA, "binding": binding, "limitations": limitations,
                                         "unchecked_signal_families": list(adapter.unchecked_families),
                                         "unchecked_columns_by_assessment": unchecked_cols})
    write_json(out / "dataset_index.json", index)
    write_json(out / "phase_preview.json", preview)
    write_json(out / "test_summary.json", test_summary)
    with open(out / "README.md", "x") as f:
        f.write(readme_text(adapter, counts, limitations, stage, tables, bool(evidence)))
    manifest = {"schema": PACKAGE_SCHEMA, "dataset_id": adapter.dataset_id, "release_id": adapter.release_id, "stage": stage,
                "scientific_approval": False, "local_only": True, "no_upload_no_publish": True, "tables": list(tables),
                "binding": binding, "counts": counts, "limitations_file": "limitations.json",
                "inputs_sha256": input_hashes, "bound_files_sha256": bound, "extra_columns": list(EXTRA_COLUMNS), "files": {},
                "resources": {"peak_rss_mib": round(peak_rss_mib(), 1), "rlimit_as_bytes": list(resource.getrlimit(resource.RLIMIT_AS)),
                              "nice": os.nice(0), "wall_seconds": round(time.time() - started, 1),
                              "row_groups": {f"{v}_{t}": fe(v, t)["row_groups"] for v in VARIANTS for t in tables},
                              "max_row_group_rows": {f"{v}_{t}": fe(v, t)["max_row_group_rows"] for v in VARIANTS for t in tables}}}
    for p in sorted(out.rglob("*")):
        rel = p.relative_to(out).as_posix()
        if p.is_file() and rel not in ("manifest.json", "manifest.sha256"):
            manifest["files"][rel] = {"sha256": sha256_file(p), "bytes": p.stat().st_size}
    write_json(out / "manifest.json", manifest)
    with open(out / "manifest.sha256", "x") as f:
        f.write(f"{sha256_file(out / 'manifest.json')}  manifest.json\n")
    for p in out.rglob("*"):
        try:
            os.chmod(p, 0o444 if p.is_file() else 0o555)
        except OSError:
            pass
    log(json.dumps({"counts": {k: counts[k] for k in ("observations_full", "observations_filtered", "failed_observations", "exclusions_total")},
                    "full": counts["full"], "filtered": counts["filtered"], "tests_pass": test_summary["all_pass"],
                    "failed_checks": [t["id"] for t in test_rows if not t["pass"]], "peak_rss_mib": manifest["resources"]["peak_rss_mib"]}))
    return (0 if test_summary["all_pass"] else 1), test_summary


def readme_text(adapter, counts, limitations, stage, tables, has_evidence):
    lines = []
    for x in limitations:
        n = x.get("observations", x.get("observations_in_recording"))
        lines.append(f"- {x['title']}: {n} observations" + (f" in {x['recordings']} recordings" if "recordings" in x else ""))
    t0 = tables[0]
    sections = "".join(f"## {h}\n\n{t}\n\n" for h, t in adapter.readme_sections())
    return (f"# {adapter.title} (local, not published)\n\n"
            "Review copy only; no scientific approval.\n\n"
            "What is in this folder:\n\n"
            + "".join(f"- `full_{t}.parquet` and `filtered_{t}.parquet`: the {t} table (one row per sample).\n" for t in tables) +
            "- The full files hold every exported observation. `quality_status` and `failed_limits` on every row record the "
            "structured assessment. The filtered files leave out the observations the assessment marked failed, and nothing else.\n"
            "- `exclusions.csv`: every observation, segment or window left out of either variant, with its id, stage and reason.\n"
            "- `assessment.jsonl`: the assessment of every observation, with failed limits, held columns and limitations.\n"
            "- `limitations.json`: each known limitation with counts.\n"
            + ("- `evidence/`: dataset-specific files that back the exclusions and the assessment.\n" if has_evidence else "") +
            "- `manifest.json`, `manifest.sha256`: sha256 of every file, counts and sources. `dataset_index.json`, `phase_preview.json` "
            "and `test_summary.json` carry the same hashes and counts.\n\n"
            f"Counts (stage {stage}): {counts['observations_full']} observations in full, {counts['observations_filtered']} in filtered, "
            f"{counts['failed_observations']} failed by the assessment; {counts['full'].get(t0 + '_rows')} {t0} rows in full; "
            f"{counts['exclusions_total']} exclusion rows.\n\n"
            + sections +
            "## Limitations (details with counts in limitations.json)\n\n" + "\n".join(lines) + "\n\n"
            "Nothing is resampled, filled or re-labelled. Signals without a limit are listed as not checked in limitations.json "
            "and dataset_index.json; a missing or unchecked signal is never evidence of passing. The limits used are listed in the "
            "manifest and are not approved reference ranges.\n")
