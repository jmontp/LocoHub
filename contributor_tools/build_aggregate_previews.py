#!/usr/bin/env python3
"""Bounded, reproducible descriptive summaries for static dataset pages.

These are local-file previews, not verified releases. Signals are never repaired,
reoriented, interpolated, or zero-filled. Each physical Parquet signal column is
read in one projected pass; SQLite holds observation offsets and spilled moments.
"""

import argparse
from collections import Counter, OrderedDict
import gc
import json
import math
import os
from pathlib import Path
import re
import resource
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

try:
    from .build_data_previews import SOURCES
except ImportError:
    from build_data_previews import SOURCES

ROOT = Path(__file__).resolve().parents[1]
PHASE_POINTS = 150
PHASE_ATOL = 1e-5
PROJECTED_BYTES = 64 * 1024**2
UNITS = ("rad_s2", "deg_s2", "Nm_kg", "rad_s", "deg_s", "m_s2", "W_kg",
         "N_kg", "m_s", "Nm", "rad", "deg", "BW", "Hz", "mm", "cm", "mV",
         "W", "N", "m", "V")
SOURCE_NOTE = (
    "Descriptive summaries of an existing local converted file, not verified against "
    "the linked download. Historical conversion conventions have not been re-checked. "
    "Task-level summaries pool available conditions and recordings."
)
AGGREGATION = {
    "within_subject": "Mean and sample SD (ddof=1) across complete stored phase observations.",
    "all_subjects": "Equal weight per available subject mean at each phase; sample SD (ddof=1) between subject means.",
    "missing": "Nonfinite samples excluded per signal and phase. Missing mean/SD is null; n records finite contributors.",
    "singleton_sd": "null",
    "identity": "Contiguous subject/task/step runs and phase resets; legacy step identifiers are never grouped globally.",
    "phase": "150 strictly increasing points matching linspace(0,100,150) within 1e-5; no sorting or interpolation.",
    "precision_significant_digits": 7,
}


def signal_definitions(schema):
    import pyarrow.types as types
    definitions = []
    for field in schema:
        name = field.name
        if not (types.is_floating(field.type) or types.is_integer(field.type)):
            continue
        if name.startswith(("phase", "time", "source_start", "source_end")):
            continue
        if name in {"height_m", "stair_height_m", "incline_deg", "speed_m_s", "sample_rate_Hz", "sampling_frequency_Hz"}:
            continue
        if name.startswith(("subject_", "task_", "metadata_", "stride_", "cycle_")):
            continue
        unit = next((unit for unit in UNITS if name.endswith("_" + unit)), None)
        if unit is None:
            continue
        core = name[:-(len(unit) + 1)]
        label = core.replace("_ipsi", " (ipsilateral)").replace("_contra", " (contralateral)")
        definitions.append({"column": name, "label": label.replace("_", " ").capitalize(), "unit": unit})
    if len(definitions) > 256:
        raise MemoryError("More than 256 signals exceed the bounded preview schema")
    return definitions


def projected_groups(parquet, columns, limit=PROJECTED_BYTES):
    """Plan groups whose total uncompressed column chunks fit every row group."""
    names = parquet.schema_arrow.names
    maxima = {}
    for name in columns:
        index = names.index(name)
        maxima[name] = max(
            (parquet.metadata.row_group(group).column(index).total_uncompressed_size
             for group in range(parquet.metadata.num_row_groups)), default=0,
        )
        if maxima[name] > limit:
            raise MemoryError(f"Column {name} exceeds the projected row-group limit")
    groups, current, size = [], [], 0
    for name in columns:
        if current and size + maxima[name] > limit:
            groups.append(current)
            current, size = [], 0
        current.append(name)
        size += maxima[name]
    if current:
        groups.append(current)
    return groups


class CycleIndexer:
    """Find complete contiguous observations across arbitrary batch boundaries."""

    def __init__(self, accept, observe=None):
        import numpy as np
        self.expected = np.linspace(0, 100, PHASE_POINTS)
        self.accept = accept
        self.observe = observe
        self.key = None
        self.phase = []
        self.length = 0
        self.start = 0
        self.offset = 0
        self.previous = None
        self.invalid_identity = False
        self.counts = Counter()
        self.task_counts = {}

    def _finish(self):
        import numpy as np
        if not self.length:
            return
        task = str(self.key[1]) if self.key and self.key[1] is not None else "(missing)"
        if task not in self.task_counts and len(self.task_counts) >= 4096:
            raise MemoryError("More than 4096 task labels exceed the bounded preview schema")
        stats = self.task_counts.setdefault(task, Counter())
        if self.observe and self.key and all(isinstance(value, str) and value.strip() for value in self.key[:2]):
            self.observe(str(self.key[1]), str(self.key[0]))
        if self.invalid_identity:
            reason = "invalid_identity"
        elif self.length != PHASE_POINTS:
            reason = "incomplete_or_oversized"
        else:
            phase = np.asarray(self.phase, dtype=float)
            reason = None if (np.isfinite(phase).all() and (np.diff(phase) > 0).all()
                              and np.allclose(phase, self.expected, atol=PHASE_ATOL, rtol=0)) else "malformed_phase"
        if reason:
            self.counts[reason + "_observations"] += 1
            self.counts[reason + "_rows"] += self.length
            stats[reason + "_observations"] += 1
            stats[reason + "_rows"] += self.length
        else:
            self.accept(self.start, self.start + self.length, str(self.key[0]), str(self.key[1]))
            self.counts["complete_observations"] += 1
            self.counts["complete_rows"] += self.length
            stats["complete_observations"] += 1
            stats["complete_rows"] += self.length

    def feed(self, keys, phases):
        for key, value in zip(keys, phases):
            phase = float(value) if value is not None else float("nan")
            reset = (math.isfinite(phase) and abs(phase) <= PHASE_ATOL
                     and self.previous is not None and math.isfinite(self.previous)
                     and self.previous > PHASE_ATOL)
            if self.length and (key != self.key or reset):
                self._finish()
                self.length = 0
                self.phase = []
            if not self.length:
                self.start = self.offset
                self.key = key
                self.invalid_identity = any(
                    value is None or (isinstance(value, str) and not value.strip())
                    or (isinstance(value, float) and not math.isfinite(value))
                    for value in key[:3]
                )
            self.length += 1
            if self.length <= PHASE_POINTS:
                self.phase.append(phase)
            self.previous = phase
            self.offset += 1

    def finish(self):
        self._finish()
        self.length = 0
        self.counts["source_rows"] = self.offset
        return dict(self.counts), {key: dict(value) for key, value in self.task_counts.items()}


class Moments:
    def __init__(self, shape):
        import numpy as np
        self.n = np.zeros(shape, dtype="uint64")
        self.mean = np.zeros(shape, dtype="float64")
        self.m2 = np.zeros(shape, dtype="float64")

    def update(self, values):
        import numpy as np
        finite = np.isfinite(values)
        self.n[finite] += 1
        delta = values[finite] - self.mean[finite]
        self.mean[finite] += delta / self.n[finite]
        self.m2[finite] += delta * (values[finite] - self.mean[finite])

    def arrays(self):
        import numpy as np
        mean = np.where(self.n > 0, self.mean, np.nan)
        sd = np.full(self.n.shape, np.nan, dtype=float)
        valid = self.n > 1
        sd[valid] = np.sqrt(np.maximum(self.m2[valid], 0) / (self.n[valid] - 1))
        return mean, sd, self.n


class MomentStore:
    def __init__(self, connection, columns, cache_size=32):
        self.connection, self.columns = connection, columns
        self.cache_size = cache_size
        self.cache = OrderedDict()

    def _save(self, key, moments):
        task, subject = key
        for i, column in enumerate(self.columns):
            if moments.n[i].any():
                self.connection.execute(
                    "INSERT OR REPLACE INTO stats VALUES (?,?,?,?,?,?)",
                    (task, subject, column, moments.n[i].tobytes(),
                     moments.mean[i].tobytes(), moments.m2[i].tobytes()),
                )

    def update(self, task, subject, values):
        import numpy as np
        key = (task, subject)
        moments = self.cache.pop(key, None)
        if moments is None:
            moments = Moments((len(self.columns), PHASE_POINTS))
            placeholders = ",".join("?" for _ in self.columns)
            for column, n, mean, m2 in self.connection.execute(
                f"SELECT feature,n,mean,m2 FROM stats WHERE task=? AND subject=? AND feature IN ({placeholders})",
                (task, subject, *self.columns),
            ):
                i = self.columns.index(column)
                moments.n[i] = np.frombuffer(n, dtype="uint64")
                moments.mean[i] = np.frombuffer(mean, dtype="float64")
                moments.m2[i] = np.frombuffer(m2, dtype="float64")
        moments.update(values.T)
        self.cache[key] = moments
        if len(self.cache) > self.cache_size:
            old_key, old_moments = self.cache.popitem(last=False)
            self._save(old_key, old_moments)

    def flush(self):
        for key, moments in self.cache.items():
            self._save(key, moments)
        self.cache.clear()
        self.connection.commit()


def initialize_database(path):
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=OFF")
    connection.execute("PRAGMA cache_size=-8192")
    connection.execute("PRAGMA max_page_count=65536")  # 256 MiB at default 4 KiB pages.
    connection.execute("CREATE TABLE cycles (start INTEGER PRIMARY KEY, stop INTEGER, subject TEXT, task TEXT)")
    connection.execute("CREATE TABLE source_groups (task TEXT, subject TEXT, PRIMARY KEY(task,subject))")
    connection.execute("CREATE TABLE stats (task TEXT, subject TEXT, feature TEXT, n BLOB, mean BLOB, m2 BLOB, PRIMARY KEY(task,subject,feature))")
    return connection


def index_cycles(parquet, connection, batch_rows):
    names = parquet.schema_arrow.names
    required = ["subject", "task", "step", "phase_ipsi"]
    if any(name not in names for name in required):
        raise ValueError("Source requires subject, task, step, and phase_ipsi columns")
    keys = ["subject", "task", "step"] + [
        name for name in ("task_id", "source_recording_id", "observation_id", "reference_side")
        if name in names
    ]
    groups = projected_groups(parquet, keys + ["phase_ipsi"])
    if len(groups) != 1:
        raise MemoryError("Observation metadata exceeds the projected row-group limit")
    indexer = CycleIndexer(
        lambda *row: connection.execute("INSERT INTO cycles VALUES (?,?,?,?)", row),
        lambda *row: connection.execute("INSERT OR IGNORE INTO source_groups VALUES (?,?)", row),
    )
    for batch in parquet.iter_batches(batch_size=batch_rows, columns=groups[0], use_threads=False):
        values = {name: batch.column(name).to_pylist() for name in groups[0]}
        indexer.feed(zip(*(values[name] for name in keys)), values["phase_ipsi"])
    result = indexer.finish()
    connection.commit()
    return result


def accumulate_group(parquet, connection, columns, batch_rows):
    import numpy as np
    cursor = connection.execute("SELECT start,stop,subject,task FROM cycles ORDER BY start")
    cycle = next(cursor, None)
    store = MomentStore(connection, columns)
    offset = 0
    pending = np.empty((PHASE_POINTS, len(columns)), dtype=float)
    for batch in parquet.iter_batches(batch_size=batch_rows, columns=columns, use_threads=False):
        end = offset + batch.num_rows
        if cycle is not None and cycle[0] < end:
            values = np.column_stack([
                batch.column(name).to_numpy(zero_copy_only=False).astype(float, copy=False)
                for name in columns
            ])
            while cycle is not None and cycle[0] < end:
                start, stop, subject, task = cycle
                left, right = max(start, offset), min(stop, end)
                pending[left - start:right - start] = values[left - offset:right - offset]
                if stop > end:
                    break
                store.update(task, subject, pending)
                cycle = next(cursor, None)
        offset = end
    if cycle is not None:
        raise ValueError("Signal scan ended before indexed observations")
    store.flush()


def json_array(values, integer=False):
    if integer:
        return [int(value) for value in values]
    return [float(format(float(value), ".7g")) if math.isfinite(float(value)) else None for value in values]


def signal_json(moments):
    mean, sd, count = moments.arrays()
    return {"mean": json_array(mean), "sd": json_array(sd), "n": json_array(count, integer=True)}


def task_filename(task):
    readable = re.sub(r"[^a-zA-Z0-9_-]+", "_", task).strip("_") or "task"
    # Avoid collisions between labels whose punctuation normalizes identically.
    import hashlib
    return readable + "_" + hashlib.sha256(task.encode()).hexdigest()[:8] + ".json"


def write_json(path, payload):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as stream:
        json.dump(payload, stream, separators=(",", ":"), allow_nan=False)
        stream.write("\n")
    temporary.replace(path)


def write_subject(task_path, subject, payload):
    """Subject links resolve relative to the containing task JSON."""
    relative = Path(task_path.stem + "_subjects") / task_filename(subject)
    destination = task_path.parent / relative
    destination.parent.mkdir(exist_ok=True)
    write_json(destination, payload)
    return {"observations": payload["observations"], "url": relative.as_posix()}, destination.stat().st_size


def export_tasks(connection, output, definitions, source, task_counts):
    import numpy as np
    by_column = {item["column"]: item for item in definitions}
    tasks = []
    for (task,) in connection.execute("SELECT DISTINCT task FROM source_groups ORDER BY task"):
        columns = [row[0] for row in connection.execute("SELECT DISTINCT feature FROM stats WHERE task=? ORDER BY feature", (task,))]
        subjects = list(connection.execute(
            "SELECT s.subject,COALESCE(c.n,0) FROM source_groups s LEFT JOIN "
            "(SELECT subject,COUNT(*) n FROM cycles WHERE task=? GROUP BY subject) c "
            "ON s.subject=c.subject WHERE s.task=? ORDER BY s.subject LIMIT 10001", (task, task),
        ))
        if len(subjects) > 10000:
            raise MemoryError("More than 10000 subjects exceed the bounded task preview")
        signals = [by_column[column] for column in columns]
        across = {column: Moments((PHASE_POINTS,)) for column in columns}
        filename = task_filename(task)
        temporary = output / (filename + ".tmp")
        subject_bytes = []
        with temporary.open("w") as stream:
            stream.write('{"phase":' + json.dumps(json_array(np.linspace(0, 100, PHASE_POINTS))))
            stream.write(',"subjects":{')
            for ordinal, (subject, observations) in enumerate(subjects):
                subject_signals = {}
                for column, n, mean, m2 in connection.execute(
                    "SELECT feature,n,mean,m2 FROM stats WHERE task=? AND subject=? ORDER BY feature",
                    (task, subject),
                ):
                    moments = Moments((PHASE_POINTS,))
                    moments.n = np.frombuffer(n, dtype="uint64")
                    moments.mean = np.frombuffer(mean, dtype="float64")
                    moments.m2 = np.frombuffer(m2, dtype="float64")
                    subject_signals[column] = signal_json(moments)
                    across[column].update(np.where(moments.n > 0, moments.mean, np.nan))
                if ordinal:
                    stream.write(",")
                reference, size = write_subject(
                    output / filename, subject,
                    {"observations": observations, "signals": subject_signals},
                )
                subject_bytes.append(size)
                stream.write(json.dumps(subject) + ":" + json.dumps(reference, separators=(",", ":")))
                if stream.tell() > 64 * 1024**2:
                    raise MemoryError("Task JSON exceeds the 64 MiB static-preview limit")
            stream.write('},"all":' + json.dumps(
                {"subjects": sum(count > 0 for _, count in subjects),
                 "signals": {column: signal_json(across[column]) for column in columns}},
                separators=(",", ":"), allow_nan=False,
            ))
            stream.write(',"source":' + json.dumps(source, separators=(",", ":")))
            stream.write(',"aggregation":' + json.dumps(AGGREGATION, separators=(",", ":")))
            stream.write(',"excluded_counts":' + json.dumps(task_counts.get(task, {})))
            stream.write("}\n")
        temporary.replace(output / filename)
        tasks.append({
            "id": task, "label": task.replace("_", " ").capitalize(),
            "url": f"{output.name}/{filename}", "subjects": [row[0] for row in subjects],
            "signals": signals, "observations": sum(row[1] for row in subjects),
            "available": bool(signals),
            "file_bytes": (output / filename).stat().st_size,
            "subject_file_bytes": sum(subject_bytes),
            "max_subject_file_bytes": max(subject_bytes, default=0),
        })
    return tasks


def split_existing_exports(output):
    """Repackage existing summaries without reading or recomputing source data."""
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for slug, dataset in manifest["datasets"].items():
        for task in dataset["tasks"]:
            task_path = output / task["url"]
            if not task_path.resolve().is_relative_to(output.resolve()):
                raise ValueError("Task URL escapes the aggregate output directory")
            with task_path.open() as stream:
                payload = json.load(stream)
            subject_bytes = []
            for subject, values in payload["subjects"].items():
                if "signals" in values:
                    reference, size = write_subject(task_path, subject, values)
                    payload["subjects"][subject] = reference
                else:
                    subject_path = task_path.parent / values["url"]
                    if not subject_path.resolve().is_relative_to(output.resolve()):
                        raise ValueError("Subject URL escapes the aggregate output directory")
                    size = subject_path.stat().st_size
                subject_bytes.append(size)
            write_json(task_path, payload)
            task["file_bytes"] = task_path.stat().st_size
            task["subject_file_bytes"] = sum(subject_bytes)
            task["max_subject_file_bytes"] = max(subject_bytes, default=0)
            del payload
            gc.collect()
        if dataset.get("source"):
            write_json(output / slug / "index.json", dataset)
        print(f"{slug}: subject files ready", flush=True)
    manifest["version"] = 2
    write_json(manifest_path, manifest)
    return manifest


def aggregate_file(path, output, *, batch_rows=4096):
    import pyarrow.parquet as pq
    started = time.monotonic()
    initial = path.stat()
    output.mkdir(parents=True, exist_ok=True)
    source = {
        "filename": path.name, "file_bytes": initial.st_size,
        "file_modified_ns": initial.st_mtime_ns, "source_sha256": None, "note": SOURCE_NOTE,
    }
    with tempfile.TemporaryDirectory(prefix=".aggregate-", dir=output.parent) as temporary:
        connection = initialize_database(Path(temporary) / "moments.sqlite")
        try:
            with pq.ParquetFile(path, pre_buffer=False, buffer_size=65536) as parquet:
                definitions = signal_definitions(parquet.schema_arrow)
                source.update(file_rows=parquet.metadata.num_rows, file_columns=len(parquet.schema_arrow))
                groups = projected_groups(parquet, [item["column"] for item in definitions])
                counts, task_counts = index_cycles(parquet, connection, batch_rows)
                print(f"{path.name}: indexed {counts.get('complete_observations', 0)} complete observations; {len(groups)} signal groups", flush=True)
                for index, group in enumerate(groups, 1):
                    accumulate_group(parquet, connection, group, batch_rows)
                    gc.collect()
                    print(f"{path.name}: signal group {index}/{len(groups)} complete", flush=True)
            final = path.stat()
            if (initial.st_size, initial.st_mtime_ns) != (final.st_size, final.st_mtime_ns):
                raise ValueError("Source changed during aggregation")
            tasks = export_tasks(connection, output, definitions, source, task_counts)
            return {
                "available": any(task["available"] for task in tasks), "source": source, "phase_points": PHASE_POINTS,
                "aggregation": AGGREGATION, "tasks": tasks, "excluded_counts": counts,
                "task_counts": task_counts,
                "resources": {"elapsed_seconds": time.monotonic() - started,
                              "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                              "batch_rows": batch_rows, "projected_group_max_bytes": PROJECTED_BYTES,
                              "sqlite_bytes": (Path(temporary) / "moments.sqlite").stat().st_size},
            }
        finally:
            connection.close()


def available_memory():
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("Cannot establish available memory")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "converted_datasets")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/datasets/aggregate_previews")
    parser.add_argument("--datasets", nargs="+", choices=list(SOURCES), default=list(SOURCES))
    parser.add_argument("--worker", choices=list(SOURCES))
    parser.add_argument("--split-existing", action="store_true", help="Split embedded subject summaries without reading Parquet")
    parser.add_argument("--batch-rows", type=int, default=4096)
    args = parser.parse_args()
    os.nice(max(0, 19 - os.nice(0)))
    for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "ARROW_NUM_THREADS"):
        os.environ[variable] = "1"
    if not 1 <= args.batch_rows <= 8192:
        parser.error("Batch rows must be between 1 and 8192")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.split_existing:
        while available_memory() < 2 * 1024**3:
            print("Waiting for 2 GiB available memory before splitting summaries.", flush=True)
            time.sleep(10)
        resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
        split_existing_exports(args.output_dir)
        return
    if args.worker:
        resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
        import pyarrow as pa
        pa.set_cpu_count(1)
        pa.set_io_thread_count(1)
        result = aggregate_file(args.source_dir / SOURCES[args.worker], args.output_dir / args.worker, batch_rows=args.batch_rows)
        (args.output_dir / args.worker / "index.json").write_text(json.dumps(result, separators=(",", ":"), allow_nan=False) + "\n")
        return
    manifest = {"version": 2, "aggregation": AGGREGATION, "datasets": {}}
    for slug in args.datasets:
        path = args.source_dir / SOURCES[slug]
        if not path.exists():
            manifest["datasets"][slug] = {"available": False, "reason": "The configured local source file is unavailable.", "tasks": []}
        else:
            while available_memory() < 2 * 1024**3:
                print("Waiting for 2 GiB available memory before next dataset worker.", flush=True)
                time.sleep(10)
            if shutil.disk_usage(args.output_dir).free < 512 * 1024**2:
                raise RuntimeError("Less than 512 MiB free for bounded preview export")
            command = [sys.executable, str(Path(__file__).resolve()), "--worker", slug,
                       "--source-dir", str(args.source_dir), "--output-dir", str(args.output_dir),
                       "--batch-rows", str(args.batch_rows)]
            subprocess.run(command, check=True)
            manifest["datasets"][slug] = json.loads((args.output_dir / slug / "index.json").read_text())
        temporary = args.output_dir / "manifest.json.tmp"
        temporary.write_text(json.dumps(manifest, separators=(",", ":"), allow_nan=False) + "\n")
        temporary.replace(args.output_dir / "manifest.json")
        print(f"{slug}: export ready", flush=True)


if __name__ == "__main__":
    main()
