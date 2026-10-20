#!/usr/bin/env python3
"""Batch runner for Gait120 full OpenSim conversion (per-subject subprocess).

Why this exists:
- Long-lived OpenSim Python sessions can segfault after many Scale/IK/ID runs.
- Running each subject in a fresh subprocess is slower but much more robust.
- Produces one parquet per subject, then merges them into a single parquet.

Example:
  python contributor_tools/conversion_scripts/Gait120/run_full_opensim_conversion.py \
    --input /mnt/s/locomotion_data/Gait120 \
    --output converted_datasets/gait120_opensim_phase.parquet \
    --parts-dir /tmp/gait120_opensim_parts \
    --pipeline-cache-root /tmp/gait120_opensim_cache \
    --opensim-rotate
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple


def _discover_subjects(input_root: Path) -> List[str]:
    subjects = sorted([p.name for p in input_root.iterdir() if p.is_dir() and p.name.startswith("S")])
    return subjects


def _iter_subjects(input_root: Path, subjects: Optional[Sequence[str]]) -> List[str]:
    discovered = _discover_subjects(input_root)
    if subjects:
        desired = [s.strip() for s in subjects if s.strip()]
        missing = sorted(set(desired) - set(discovered))
        if missing:
            raise FileNotFoundError(f"Subjects not found under {input_root}: {missing[:10]}")
        return desired
    return discovered


def _convert_one_subject(
    *,
    repo_root: Path,
    input_root: Path,
    subject: str,
    parts_dir: Path,
    pipeline_cache_root: Path,
    opensim_rotate: bool,
    model_choice: str,
    id_correction: str,
    log_dir: Path,
) -> Tuple[int, Path, Path]:
    """Run convert_gait120_to_parquet.py for a single subject as a subprocess."""
    script = repo_root / "contributor_tools" / "conversion_scripts" / "Gait120" / "convert_gait120_to_parquet.py"
    if not script.exists():
        raise FileNotFoundError(f"Missing conversion script: {script}")

    parts_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    pipeline_cache_root.mkdir(parents=True, exist_ok=True)

    out_name = f"gait120_{subject.lower()}_opensim_phase.parquet"
    out_path = parts_dir / out_name
    cache_dir = pipeline_cache_root / subject
    log_path = log_dir / f"{subject}.log"

    python_cmd_parts = [
        f"python {script.as_posix()}",
        f"--input {input_root.as_posix()}",
        f"--subjects {subject}",
        "--run-ik",
        "--opensim-rotate" if opensim_rotate else "",
        f"--opensim-model {model_choice}",
        f"--opensim-id-correction {id_correction}",
        f"--output {out_path.name}",
        f"--output-dir {parts_dir.as_posix()}",
        f"--pipeline-cache {cache_dir.as_posix()}",
    ]
    python_cmd = " ".join(p for p in python_cmd_parts if p).strip()

    bash_cmd = (
        "set -euo pipefail; "
        "source ~/miniconda3/etc/profile.d/conda.sh; "
        "conda activate opensim; "
        f"PYTHONUNBUFFERED=1 {python_cmd} "
        f"> {log_path.as_posix()} 2>&1"
    )

    cmd = ["bash", "-lc", bash_cmd]

    proc = subprocess.run(cmd, cwd=str(repo_root))
    return proc.returncode, out_path, log_path


def _merge_parquets_streaming(part_files: Sequence[Path], output_path: Path) -> None:
    """Merge parquet files without loading everything into memory."""
    try:
        import pyarrow as pa  # type: ignore
        import pyarrow.parquet as pq  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("pyarrow is required to merge parquet files") from exc

    if not part_files:
        raise ValueError("No part parquet files provided.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    writer: Optional[pq.ParquetWriter] = None
    try:
        for part in part_files:
            pf = pq.ParquetFile(part)
            for batch in pf.iter_batches():
                table = pa.Table.from_batches([batch])
                if writer is None:
                    writer = pq.ParquetWriter(str(output_path), table.schema, compression="snappy")
                writer.write_table(table)
    finally:
        if writer is not None:
            writer.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full Gait120 OpenSim conversion (per-subject subprocess)")
    parser.add_argument("--input", type=str, default="/mnt/s/locomotion_data/Gait120", help="Gait120 root folder")
    parser.add_argument("--output", type=str, required=True, help="Final merged parquet output path")
    parser.add_argument("--parts-dir", type=str, default="/tmp/gait120_opensim_parts", help="Directory for per-subject parquet parts")
    parser.add_argument("--pipeline-cache-root", type=str, default="/tmp/gait120_opensim_cache", help="Root cache dir (scaled models, IK, ID)")
    parser.add_argument("--logs-dir", type=str, default="/tmp/gait120_opensim_logs", help="Directory for per-subject logs")
    parser.add_argument("--subjects", nargs="+", default=None, help="Optional subject subset (e.g., S001 S002)")
    parser.add_argument("--opensim-rotate", action="store_true", help="Rotate TRC/GRF +90° about Y for OpenSim (+X forward)")
    parser.add_argument("--opensim-model", type=str, default="original", choices=["original", "gait120"], help="OpenSim model variant")
    parser.add_argument(
        "--opensim-id-correction",
        type=str,
        default="none",
        choices=["none", "inertia_subtraction"],
        help="ID post-processing mode (default: none)",
    )
    parser.add_argument("--max-retries", type=int, default=2, help="Retries per subject on failure")
    parser.add_argument("--resume", action="store_true", help="Skip subjects with an existing part parquet")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    input_root = Path(args.input)
    if not input_root.exists():
        print(f"❌ Input path not found: {input_root}")
        return 1

    parts_dir = Path(args.parts_dir)
    pipeline_cache_root = Path(args.pipeline_cache_root)
    logs_dir = Path(args.logs_dir)
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = (Path.cwd() / output_path).resolve()

    subjects = _iter_subjects(input_root, args.subjects)
    print(f"Subjects: {len(subjects)}")
    print(f"Parts dir: {parts_dir}")
    print(f"Logs dir: {logs_dir}")
    print(f"Cache root: {pipeline_cache_root}")
    print(f"Final output: {output_path}")

    failed: List[str] = []
    produced: List[Path] = []

    for idx, subject in enumerate(subjects, start=1):
        part_path = parts_dir / f"gait120_{subject.lower()}_opensim_phase.parquet"
        if args.resume and part_path.exists():
            print(f"[{idx}/{len(subjects)}] {subject}: skip (exists)")
            produced.append(part_path)
            continue

        attempt = 0
        rc = 1
        log_path = logs_dir / f"{subject}.log"
        while attempt <= int(args.max_retries):
            attempt += 1
            print(f"[{idx}/{len(subjects)}] {subject}: convert (attempt {attempt})")
            rc, part_path, log_path = _convert_one_subject(
                repo_root=repo_root,
                input_root=input_root,
                subject=subject,
                parts_dir=parts_dir,
                pipeline_cache_root=pipeline_cache_root,
                opensim_rotate=bool(args.opensim_rotate),
                model_choice=str(args.opensim_model),
                id_correction=str(args.opensim_id_correction),
                log_dir=logs_dir,
            )
            if rc == 0 and part_path.exists():
                break
            if attempt <= int(args.max_retries):
                print(f"  ⚠️ Failed (rc={rc}). Retrying. Log: {log_path}")

        if rc != 0 or not part_path.exists():
            print(f"  ❌ Failed (rc={rc}). Log: {log_path}")
            failed.append(subject)
            continue
        produced.append(part_path)

    if failed:
        print(f"⚠️ Failed subjects ({len(failed)}): {failed[:10]}")

    if not produced:
        print("❌ No parquet parts produced; nothing to merge.")
        return 1

    print(f"Merging {len(produced)} parquet part(s) -> {output_path}")
    produced_sorted = sorted(set(produced), key=lambda p: p.name)
    _merge_parquets_streaming(produced_sorted, output_path)

    print("✅ Merge complete")
    if failed:
        print("⚠️ Merge completed with failures; rerun with --resume after investigating logs.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
