#!/usr/bin/env python3
"""Reconvert one real recording into an isolated, unreviewed staging directory.

This worker deliberately does not combine recordings or publish releases. Run
separate invocations serially to bound converter memory and resume by recording.
"""

import argparse
import hashlib
import importlib.util
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import resource
import re
import shutil
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
CONVERTERS = ROOT / "contributor_tools" / "conversion_scripts"
THREAD_ENV = (
    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS", "NUMBA_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
    "ARROW_NUM_THREADS",
)
STROKE_RECORDING = re.compile(r"BWA[-_]?\d+_ik\.mot", re.IGNORECASE)
MIN_FREE_DISK_BYTES = 5 * 1024**3


class StorageHeadroomError(RuntimeError):
    pass


def ensure_storage_headroom(path):
    """Check the real mounted volume, never WSL's sparse virtual capacity."""
    path = Path(path).resolve()
    allowed = (ROOT / "converted_datasets" / "reconversion_v2").resolve()
    if not path.is_relative_to(allowed):
        raise StorageHeadroomError("Output must stay inside the authorized reconversion_v2 directory")
    if ("microsoft" in platform.release().lower()
            or os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP")):
        parts = path.parts
        if len(parts) < 3 or parts[1] != "mnt" or not re.fullmatch("[a-z]", parts[2]):
            raise StorageHeadroomError(
                "Native WSL free space does not prove Windows backing-volume capacity; "
                "a verified mounted output volume is required"
            )
    anchor = path
    while not anchor.exists():
        anchor = anchor.parent
    free = shutil.disk_usage(anchor).free
    if free < MIN_FREE_DISK_BYTES:
        raise StorageHeadroomError(
            f"Storage hold: {free / 1024**3:.2f} GiB free at {anchor}; "
            "at least 5 GiB is required before starting a new recording"
        )
    return free


def environment_evidence():
    versions = {"python": sys.version}
    for package in ("numpy", "pandas", "scipy", "pyarrow", "ezc3d", "openpyxl"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return {
        "versions": versions,
        "c3d_reader_importable": importlib.util.find_spec("ezc3d") is not None,
        "opensim_pipeline_requested": False,
    }


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def file_evidence(path):
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": digest(path)}


def resume_matches(existing, sources, code, profile, environment, output):
    return (
        existing.get("sources") == sources
        and existing.get("converter_code") == code
        and existing.get("profile") == profile
        and existing.get("environment") == environment
        and bool(existing.get("outputs"))
        and all((output / item["name"]).is_file()
                and digest(output / item["name"]) == item["sha256"]
                for item in existing["outputs"])
    )


def admit_sources(paths, memory_mib, max_source_mib):
    """Reject unexpectedly large text/C3D inputs before any scientific imports."""
    total = sum(path.stat().st_size for path in paths)
    estimate = 256 * 1024**2 + total * 16
    if total > max_source_mib * 1024**2 or estimate > memory_mib * 1024**2:
        raise MemoryError(
            f"Source size {total / 1024**2:.1f} MiB; conservative working estimate "
            f"{estimate / 1024**2:.1f} MiB exceeds admission limits."
        )
    return total, estimate


def source_paths(args):
    root = args.source_root.resolve()
    subject = root / args.subject
    if args.dataset == "strokepig":
        trial = subject / args.recording
        if not trial.name.endswith("_ik.mot") or not trial.is_file():
            raise ValueError("StrokePiG recording must be an existing *_ik.mot file")
        # Test/rotated reconstructions are not separate source acquisitions.
        if not STROKE_RECORDING.fullmatch(trial.name):
            raise ValueError("Only original BWA<number>_ik.mot acquisitions are admitted")
        files = [trial]
        c3d = trial.with_name(trial.name.removesuffix("_ik.mot") + ".c3d")
        if c3d.exists():
            files.append(c3d)
        files.extend(sorted(subject.glob("*.mp")))
        if (root / "SubjectChar.xlsx").exists():
            files.append(root / "SubjectChar.xlsx")
        converter = CONVERTERS / "StrokePiG" / "convert_strokepig_to_parquet.py"
    else:
        trial = subject / args.recording
        if not trial.is_dir():
            raise ValueError("GT24 recording must be an existing trial directory")
        if args.source not in {"Phase1And2", "Phase3"}:
            raise ValueError("GT24 requires its actual --source Phase1And2 or Phase3")
        prefix = f"{args.subject}_{args.recording}_"
        kinds = (
            "angle_filt", "moment_filt", "grf", "velocity", "insole_sim",
            "moment_filt_bio", "power", "power_bio", "exo", "exo_sim", "imu_sim",
        )
        files = [trial / f"{prefix}{kind}.csv" for kind in kinds]
        files = [path for path in files if path.exists()]
        if (trial / "Virtual_IMUs.csv").exists():
            files.append(trial / "Virtual_IMUs.csv")
        source_readme = root.parent.parent / "readme.txt"
        if source_readme.exists():
            files.append(source_readme)
        converter = CONVERTERS / "GaTech_2024_TaskAgnostic" / "convert_gtech_2024_phase_to_parquet.py"
    if not files:
        raise ValueError("No supported source files found")
    return trial, files, converter


def load_converter(path):
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("recording_converter", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def convert(args):
    started = time.monotonic()
    ensure_storage_headroom(args.output_root)
    for key in THREAD_ENV:
        os.environ[key] = "1"
    os.environ["MPLBACKEND"] = "Agg"
    os.environ["LOCOHUB_HEADLESS"] = "1"
    os.nice(max(0, 19 - os.nice(0)))
    memory_limit = args.memory_mib * 1024**2
    resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
    trial, files, converter_path = source_paths(args)
    source_bytes, estimate = admit_sources(files, args.memory_mib, args.max_source_mib)
    source_evidence = [file_evidence(path) for path in files]
    profile_evidence = file_evidence(args.ranges) if args.ranges else None
    environment = environment_evidence()
    code_paths = sorted(set(
        list(converter_path.parent.glob("*.py"))
        + list((ROOT / "contributor_tools" / "common").rglob("*.py"))
        + [Path(__file__).resolve()]
    ))
    code_evidence = [file_evidence(path) for path in code_paths]
    output = args.output_root / args.dataset / (args.source or "source") / args.subject / trial.stem
    manifest_path = output / "conversion_manifest.json"
    if output.exists():
        if args.resume and manifest_path.exists():
            existing = json.loads(manifest_path.read_text())
            if resume_matches(existing, source_evidence, code_evidence,
                              profile_evidence, environment, output):
                print(json.dumps({"status": "resumed_unchanged", "output": str(output)}), flush=True)
                return
        raise FileExistsError(f"Refusing to overwrite or silently reuse changed output: {output}")
    output.mkdir(parents=True)
    try:
        import pandas as pd
        import pyarrow as pa
        pa.set_cpu_count(1)
        pa.set_io_thread_count(1)
        module = load_converter(converter_path)
        capabilities = {}
        if args.dataset == "strokepig":
            module.RUN_FULL_PIPELINE = False
            metadata_table = None
            metadata_path = args.source_root / "SubjectChar.xlsx"
            if metadata_path.exists():
                metadata_table = module.load_subject_char_xlsx(metadata_path)
            metadata = module.get_subject_metadata(args.subject, args.source_root, metadata_table)
            frames, _ = module.process_trial_file(trial, args.subject, metadata)
            capabilities["c3d_reader_available"] = module.EZC3D_AVAILABLE
            capabilities["opensim_pipeline_run"] = False
        else:
            frames = module.process_trial(trial, args.subject, args.source, "all")
        outputs = []
        report = {"review_status": "unreviewed", "status": "no_accepted_observations"}
        if frames:
            from contributor_tools.common.data_contract import assess_observations
            from contributor_tools.common.config_manager import ValidationConfigManager
            frame = pd.concat(frames, ignore_index=True)
            del frames
            profile = ValidationConfigManager(args.ranges) if args.ranges else None
            report = assess_observations(frame, profile)
            report["review_status"] = "unreviewed"
            report["publishable"] = False
            report["limitations"].append(
                "Recording conversion pilot; segmentation exclusions and scientific conventions "
                "still require review. This is not a published release."
            )
            parquet = output / "phase.parquet"
            frame.to_parquet(parquet, index=False, row_group_size=15000)
            outputs.append({"name": parquet.name, "sha256": digest(parquet), "bytes": parquet.stat().st_size})
            report["rows"] = len(frame)
            report["observations"] = report.get("observations", [])
            report["recording_ids"] = sorted(frame.source_recording_id.unique().tolist())
            report["all_missing_signal_columns"] = [
                name for name in frame.select_dtypes(include="number").columns
                if frame[name].isna().all()
            ]
            del frame
        report_path = output / "quality_unreviewed.json"
        report_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        outputs.append({"name": report_path.name, "sha256": digest(report_path), "bytes": report_path.stat().st_size})
        usage = resource.getrusage(resource.RUSAGE_SELF)
        manifest = {
            "status": ("converted_unreviewed" if report.get("schema_passed")
                       else "quarantined_schema_failure") if report.get("rows", 0)
                      else "no_accepted_observations",
            "review_status": "unreviewed", "dataset": args.dataset,
            "subject": args.subject, "recording": args.recording, "source": args.source,
            "sources": source_evidence, "converter_code": code_evidence,
            "profile": profile_evidence, "environment": environment,
            "outputs": outputs, "capabilities": capabilities,
            "resources": {
                "address_space_limit_mib": args.memory_mib, "numeric_threads": 1, "nice": os.nice(0),
                "source_bytes": source_bytes, "admission_estimate_bytes": estimate,
                "peak_rss_kib": usage.ru_maxrss, "elapsed_seconds": time.monotonic() - started,
                "user_seconds": usage.ru_utime, "system_seconds": usage.ru_stime,
            },
            "rows": report.get("rows", 0), "decision_counts": report.get("counts", {}),
            "schema_passed": report.get("schema_passed", False),
            "limitations": [
                "Only this recording was converted; source acquisition counts are not stride counts.",
                "Existing segmentation filters can exclude candidate windows before output; "
                "a full candidate-exclusion ledger is not yet emitted by these converters.",
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
        print(json.dumps({key: manifest[key] for key in ("status", "rows", "decision_counts", "schema_passed", "resources")}), flush=True)
        print(f"Output: {output}", flush=True)
    except BaseException as exc:
        (output / "failed.json").write_text(json.dumps({"error": repr(exc), "review_status": "unreviewed"}) + "\n")
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=["strokepig", "gt24"], required=True)
    parser.add_argument("--source-root", type=Path, required=True, help="Folder containing subject folders")
    parser.add_argument("--source", choices=["Phase1And2", "Phase3"])
    parser.add_argument("--subject", required=True)
    parser.add_argument("--recording", required=True)
    parser.add_argument("--output-root", type=Path, default=ROOT / "converted_datasets" / "reconversion_v2")
    parser.add_argument("--ranges", type=Path, help="Optional diagnostic ranges; outputs stay unreviewed")
    parser.add_argument("--memory-mib", type=int, default=1536)
    parser.add_argument("--max-source-mib", type=int, default=64)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if not 512 <= args.memory_mib <= 2048:
        parser.error("--memory-mib must be between 512 and 2048")
    for value in (args.subject, args.recording):
        if Path(value).name != value or value in {".", ".."}:
            parser.error("Subject and recording must be single path components")
    try:
        convert(args)
    except StorageHeadroomError as exc:
        print(json.dumps({"status": "blocked_storage", "reason": str(exc)}), flush=True)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
