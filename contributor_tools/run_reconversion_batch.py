#!/usr/bin/env python3
"""Serial, resumable recording conversion with a memory-headroom guard.

Plans and results are manifests, never a concatenated in-memory dataset.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import signal
import sys
import time

try:
    from .reconvert_recording import ROOT, STROKE_RECORDING, StorageHeadroomError, ensure_storage_headroom, MAX_WORKER_MEMORY_MIB, MEMORY_RESERVE_BYTES, MemoryHeadroomError, memory_snapshot
except ImportError:
    from reconvert_recording import ROOT, STROKE_RECORDING, StorageHeadroomError, ensure_storage_headroom, MAX_WORKER_MEMORY_MIB, MEMORY_RESERVE_BYTES, MemoryHeadroomError, memory_snapshot


def available_memory_bytes():
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("Cannot establish available memory; refusing to launch a worker")


def run_guarded_worker(command, *, stdout, timeout, output_root):
    """Monitor only this isolated worker process group; never kill unrelated jobs."""
    process = subprocess.Popen(command, stdout=stdout, stderr=subprocess.STDOUT, start_new_session=True)
    started = time.monotonic()
    try:
        while process.poll() is None:
            if available_memory_bytes() < 1536 * 1024**2:
                raise MemoryHeadroomError('Available memory fell below 1.5 GiB during conversion')
            ensure_storage_headroom(output_root)
            if time.monotonic() - started > timeout:
                raise subprocess.TimeoutExpired(command, timeout)
            time.sleep(.5)
        return subprocess.CompletedProcess(command, process.returncode)
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()


def inventory(dataset, source_root, subjects=None):
    prefix = "TVC" if dataset == "strokepig" else "BT"
    folders = sorted(path for path in source_root.iterdir() if path.is_dir() and path.name.startswith(prefix))
    if subjects:
        folders = [path for path in folders if path.name in subjects]
    records, excluded, missing = [], [], []
    for subject in folders:
        if dataset == "strokepig":
            candidates = sorted(subject.glob("*_ik.mot"))
            accepted = [path for path in candidates if STROKE_RECORDING.fullmatch(path.name)]
            excluded.extend(str(path.relative_to(source_root)) for path in candidates if path not in accepted)
        else:
            accepted = sorted(path for path in subject.iterdir() if path.is_dir())
        if not accepted:
            missing.append(subject.name)
        records.extend({"subject": subject.name, "recording": path.name} for path in accepted)
    return {
        "source_subject_count": len(folders), "recording_count": len(records),
        "subjects_with_recordings": sorted({item["subject"] for item in records}),
        "subjects_without_supported_recordings": missing,
        "excluded_derived_recordings": excluded, "recordings": records,
    }


def worker_command(args, record):
    command = [
        sys.executable, str(ROOT / "contributor_tools" / "reconvert_recording.py"),
        "--dataset", args.dataset, "--source-root", str(args.source_root),
        "--subject", record["subject"], "--recording", record["recording"],
        "--output-root", str(args.output_root), "--memory-mib", str(args.memory_mib),
        "--max-source-mib", str(args.max_source_mib), "--resume",
    ]
    if args.source:
        command += ["--source", args.source]
    if args.ranges:
        command += ["--ranges", str(args.ranges)]
    return command


def manifest_path(args, record):
    return (args.output_root / args.dataset / (args.source or "source") /
            record["subject"] / Path(record["recording"]).stem / "conversion_manifest.json")


def summarize(results, plan):
    summary = {
        "review_status": "unreviewed", "planned_recordings": len(plan["recordings"]),
        "completed_recordings": len(results), "status_counts": {},
        "rows": 0, "schema_valid_rows": 0, "observations": 0, "peak_worker_rss_kib": 0,
        "source_subject_count": plan["source_subject_count"],
        "subjects_with_recordings": plan["subjects_with_recordings"],
        "subjects_without_supported_recordings": plan["subjects_without_supported_recordings"],
        "excluded_derived_recordings": plan["excluded_derived_recordings"],
        "decision_counts": {},
    }
    for result in results:
        status = result["status"]
        summary["status_counts"][status] = summary["status_counts"].get(status, 0) + 1
        summary["rows"] += result.get("rows", 0)
        if result.get("schema_passed"):
            summary["schema_valid_rows"] += result.get("rows", 0)
        summary["peak_worker_rss_kib"] = max(summary["peak_worker_rss_kib"], result.get("peak_rss_kib", 0))
        for state, count in result.get("decision_counts", {}).items():
            summary["decision_counts"][state] = summary["decision_counts"].get(state, 0) + count
            summary["observations"] += count
    return summary


def write_summary(output_root, results, plan, batch_status):
    summary = summarize(results, plan)
    summary["batch_status"] = batch_status
    summary["remaining_recordings"] = len(plan["recordings"]) - len(results)
    summary_path = output_root / "batch_summary.json"
    temporary = summary_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(summary, indent=2) + "\n")
    temporary.replace(summary_path)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=["strokepig", "gt24"], required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--source", choices=["Phase1And2", "Phase3"])
    parser.add_argument("--subjects", nargs="+")
    parser.add_argument("--output-root", type=Path, required=True, help="New batch folder inside reconversion_v2")
    parser.add_argument("--ranges", type=Path)
    parser.add_argument("--memory-mib", type=int, default=1536)
    parser.add_argument("--max-source-mib", type=int, default=64)
    parser.add_argument("--max-recordings", type=int)
    parser.add_argument("--delay-seconds", type=float, default=2)
    parser.add_argument("--worker-timeout-seconds", type=int, default=180)
    parser.add_argument("--max-consecutive-failures", type=int, default=3)
    parser.add_argument("--run", action="store_true", help="Without this flag only record the source inventory")
    args = parser.parse_args()
    if not 512 <= args.memory_mib <= MAX_WORKER_MEMORY_MIB:
        parser.error("Batch workers must have 512–10240 MiB address-space limits")
    if not 1 <= args.max_source_mib <= 512:
        parser.error("--max-source-mib must be between 1 and 512")
    if args.memory_mib * 1024**2 > .8 * memory_snapshot()["MemTotal"]:
        parser.error("Worker memory limit exceeds 80% of total RAM")
    if args.delay_seconds < 0 or args.worker_timeout_seconds <= 0:
        parser.error("Delay must be nonnegative and timeout positive")
    if args.max_recordings is not None and args.max_recordings <= 0:
        parser.error("--max-recordings must be positive")
    if args.max_consecutive_failures <= 0:
        parser.error("--max-consecutive-failures must be positive")
    os.nice(max(0, 19 - os.nice(0)))
    args.source_root = args.source_root.resolve()
    args.output_root = args.output_root.resolve()
    if not args.output_root.is_relative_to(ROOT / "converted_datasets" / "reconversion_v2"):
        parser.error("Batch outputs must remain inside converted_datasets/reconversion_v2")
    if args.run:
        try:
            ensure_storage_headroom(args.output_root)
        except StorageHeadroomError as exc:
            print(json.dumps({"batch_status": "blocked_storage", "reason": str(exc)}), flush=True)
            return 3
    args.output_root.mkdir(parents=True, exist_ok=True)
    plan = inventory(args.dataset, args.source_root, args.subjects)
    if args.max_recordings is not None:
        plan["recordings"] = plan["recordings"][:args.max_recordings]
    plan["dataset"] = args.dataset
    plan["source_root"] = str(args.source_root)
    plan["source"] = args.source
    plan_path = args.output_root / "source_inventory.json"
    if plan_path.exists() and json.loads(plan_path.read_text()) != plan:
        raise ValueError("The source plan changed; choose a new batch directory")
    plan_path.write_text(json.dumps(plan, indent=2) + "\n")
    print(json.dumps({key: value for key, value in plan.items() if key != "recordings"}), flush=True)
    if not args.run:
        return
    logs = args.output_root / "logs"
    logs.mkdir(exist_ok=True)
    results = []
    consecutive_failures = 0
    batch_status = "running"
    stop_file = args.output_root / "STOP_AFTER_CURRENT"
    journal = args.output_root / "recording_results.jsonl"
    for index, record in enumerate(plan["recordings"], 1):
        if stop_file.exists():
            batch_status = "stopped_by_request"
            break
        try:
            ensure_storage_headroom(args.output_root)
        except StorageHeadroomError as exc:
            batch_status = "stopped_storage"
            print(str(exc), flush=True)
            break
        while available_memory_bytes() < args.memory_mib * 1024**2 + MEMORY_RESERVE_BYTES:
            if stop_file.exists():
                break
            print(f"Paused: waiting for {args.memory_mib / 1024 + 2:.1f} GiB available memory (worker cap + reserve).", flush=True)
            write_summary(args.output_root, results, plan, "waiting_for_memory")
            time.sleep(10)
        if stop_file.exists():
            batch_status = "stopped_by_request"
            break
        record_key = f"{record['subject']}__{Path(record['recording']).stem}"
        result = {**record, "started_at": datetime.now(timezone.utc).isoformat()}
        log_path = logs / f"{record_key}.log"
        with log_path.open("a") as log:
            try:
                completed = run_guarded_worker(
                    worker_command(args, record), stdout=log,
                    timeout=args.worker_timeout_seconds, output_root=args.output_root,
                )
                result["returncode"] = completed.returncode
                result["status"] = "worker_failed"
                path = manifest_path(args, record)
                if completed.returncode == 0 and path.exists():
                    manifest = json.loads(path.read_text())
                    result.update({key: manifest[key] for key in ("status", "rows", "decision_counts", "schema_passed")})
                    result["peak_rss_kib"] = manifest["resources"]["peak_rss_kib"]
                    result["worker_elapsed_seconds"] = manifest["resources"]["elapsed_seconds"]
                    result["manifest"] = str(path.relative_to(args.output_root))
            except MemoryHeadroomError as exc:
                result["status"] = "worker_memory_stop"
                result["reason"] = str(exc)
                batch_status = "stopped_memory"
            except StorageHeadroomError as exc:
                result["status"] = "worker_storage_stop"
                result["reason"] = str(exc)
                batch_status = "stopped_storage"
            except subprocess.TimeoutExpired:
                result["status"] = "worker_timed_out"
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        results.append(result)
        with journal.open("a") as stream:
            stream.write(json.dumps(result) + "\n")
        if result["status"] in {"worker_failed", "worker_timed_out", "quarantined_schema_failure"}:
            consecutive_failures += 1
        else:
            consecutive_failures = 0
        if consecutive_failures >= args.max_consecutive_failures:
            batch_status = "stopped_incomplete"
        write_summary(args.output_root, results, plan, batch_status)
        print(f"{index}/{len(plan['recordings'])} {record_key}: {result['status']}", flush=True)
        if batch_status in {"stopped_memory", "stopped_storage"}:
            break
        if batch_status == "stopped_incomplete":
            print(f"Stopped after {consecutive_failures} consecutive failures.", flush=True)
            break
        if index < len(plan["recordings"]):
            time.sleep(args.delay_seconds)
    if batch_status == "running":
        batch_status = "completed_with_failures" if any(
            item["status"] in {"worker_failed", "worker_timed_out", "quarantined_schema_failure"}
            for item in results
        ) else "completed"
    print(json.dumps(write_summary(args.output_root, results, plan, batch_status)), flush=True)
    return 0 if batch_status == "completed" else 2


if __name__ == "__main__":
    sys.exit(main())
