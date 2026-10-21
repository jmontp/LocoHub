#!/usr/bin/env python3
"""Export small, real table/plot previews without loading whole datasets.

Run manually when preview sources change. The website build never opens research
files. These local slices are not verified copies of the remote downloads.
"""

import argparse
import gc
import hashlib
import json
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "ga26": "gait120_opensim_phase.parquet",
    "gt21": "gtech_2021_phase_clean.parquet",
    "gt23": "gtech_2023_phase_raw.parquet",
    "gt24": "gtech_2024_phase.parquet",
    "gt25d": "gtech_2025_da_phase_dirty.parquet",
    "mb24": "mblue_ankle_phase.parquet",
    "sp50": "strokepig_phase.parquet",
    "um21": "umich_2021_phase_clean.parquet",
}
SIGNALS = [
    {"column": "hip_flexion_angle_ipsi_rad", "label": "Hip flexion", "unit": "rad"},
    {"column": "knee_flexion_angle_ipsi_rad", "label": "Knee flexion", "unit": "rad"},
    {"column": "ankle_dorsiflexion_angle_ipsi_rad", "label": "Ankle dorsiflexion", "unit": "rad"},
]


def read_preview(path, max_column_bytes=32 * 1024**2):
    import pyarrow.parquet as pq

    with pq.ParquetFile(path) as parquet:
        available = parquet.schema_arrow.names
        columns = [name for name in ["subject", "task", "step", "phase_ipsi"]
                   + [item["column"] for item in SIGNALS] if name in available]
        if "phase_ipsi" not in columns or not parquet.metadata.num_row_groups:
            return {"available": False, "reason": "No phase sample is available for this file."}
        projected = sum(
            parquet.metadata.row_group(0).column(available.index(name)).total_uncompressed_size
            for name in columns
        )
        if projected > max_column_bytes:
            return {"available": False, "reason": "This file needs a separate small preview export."}
        batch = next(parquet.iter_batches(batch_size=150, row_groups=[0],
                                         columns=columns, use_threads=False), None)
        if batch is None:
            return {"available": False, "reason": "No sample rows are available."}
        rows = batch.to_pylist()
        for row in rows:
            for key, value in row.items():
                if isinstance(value, float) and not math.isfinite(value):
                    row[key] = None
        # This is a row slice, not an assertion that a legacy step key is unique.
        phase = [row["phase_ipsi"] for row in rows]
        ordered = all(isinstance(value, (int, float)) for value in phase) and all(
            a < b for a, b in zip(phase, phase[1:])
        )
        signals = [item for item in SIGNALS if item["column"] in columns]
        encoded = json.dumps(rows, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return {
            "available": True, "columns": columns, "signals": signals, "rows": rows,
            "chart_available": ordered,
            "phase_display": "Movement (%)" if ordered and abs(phase[0]) < 1e-6 and abs(phase[-1] - 100) < 1e-6 else "Phase (as stored)",
            "source": {
                "filename": path.name, "file_bytes": path.stat().st_size,
                "file_modified_ns": path.stat().st_mtime_ns,
                "file_rows": parquet.metadata.num_rows, "file_columns": len(available),
                "selection": "First 150 rows of the first row group; selected columns only.",
                "sample_sha256": hashlib.sha256(encoded).hexdigest(),
                "source_sha256": None,
                "note": "Small sample from a local converted file. Not verified against the linked download. The conversion has not been re-checked.",
            },
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "converted_datasets")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/datasets/preview_data.json")
    args = parser.parse_args()
    os.nice(max(0, 19 - os.nice(0)))
    output = {"datasets": {}}
    for slug, filename in SOURCES.items():
        path = args.source_dir / filename
        output["datasets"][slug] = read_preview(path) if path.exists() else {
            "available": False,
            "reason": "No small data preview is available yet. Open the dataset notes for existing plots.",
        }
        gc.collect()
        print(f"{slug}: {'sample ready' if output['datasets'][slug]['available'] else 'no sample'}")
    args.output.write_text(json.dumps(output, separators=(",", ":"), allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
