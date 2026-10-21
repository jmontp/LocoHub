#!/usr/bin/env python3
"""Build an immutable, identified dataset release with an auditable QC subset."""

from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from typing import Any, Optional

# Keep this contributor command usable without installing an analysis SDK.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Prefer one numeric worker on shared hosts; respect an explicit caller setting.
for _thread_setting in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_thread_setting, "1")

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from contributor_tools.common.config_manager import ValidationConfigManager
from contributor_tools.common.data_contract import (
    CONTRACT_VERSION,
    IDENTITY_COLUMNS,
    _json_object,
    assess_observations,
)


class ReleaseError(ValueError):
    """A release cannot be produced without changing or inventing its evidence."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def _admit_input(
    path: Path, *, memory_budget_mb: int, max_input_rows: int
) -> dict[str, int]:
    if memory_budget_mb < 1 or max_input_rows < 1:
        raise ReleaseError("Memory and row budgets must be positive.")
    with pq.ParquetFile(path) as parquet:
        metadata = parquet.metadata
        rows = metadata.num_rows
        columns = len(parquet.schema_arrow)
        uncompressed = sum(
            metadata.row_group(index).total_byte_size
            for index in range(metadata.num_row_groups)
        )
    # Includes Arrow/Pandas conversion, filtering copies, Python metadata and QC
    # objects. This is deliberately conservative admission, not an OS memory cap.
    estimated_peak = 4 * uncompressed + rows * (columns * 96 + 512)
    budget = memory_budget_mb * 1024 * 1024
    if rows > max_input_rows or estimated_peak > budget:
        raise ReleaseError(
            f"Input rejected before loading: {rows:,} rows, estimated peak "
            f"{estimated_peak / 1024**2:.1f} MiB; limits are {max_input_rows:,} rows "
            f"and {memory_budget_mb} MiB. Build this release on a suitable host "
            "or provide a genuinely smaller source export; this builder is not streaming."
        )
    return {
        "rows": rows, "columns": columns, "parquet_uncompressed_bytes": uncompressed,
        "estimated_peak_bytes": estimated_peak, "memory_budget_bytes": budget,
        "max_input_rows": max_input_rows,
    }


def _read_provenance(path: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    provenance = _json_object(path.read_text(encoding="utf-8"))
    if not isinstance(provenance, dict):
        raise ReleaseError("Provenance must be a JSON object.")
    try:
        json.dumps(provenance, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise ReleaseError("Provenance must contain finite JSON values.") from exc
    for name in ("dataset_id", "release_id"):
        if not isinstance(provenance.get(name), str) or not provenance[name].strip():
            raise ReleaseError(f"Provenance requires a nonempty {name}.")
    for section, keys in {
        "converter": ("name", "revision"),
        "review": ("reviewer", "reviewed_at"),
    }.items():
        if not isinstance(provenance.get(section), dict):
            raise ReleaseError(f"Provenance requires {section} metadata.")
        for key in keys:
            if not isinstance(provenance[section].get(key), str) or not provenance[section][key].strip():
                raise ReleaseError(f"Provenance requires {section}.{key}.")
    try:
        reviewed_at = datetime.fromisoformat(provenance["review"]["reviewed_at"].replace("Z", "+00:00"))
        if reviewed_at.utcoffset() is None:
            raise ValueError("Missing timezone")
    except ValueError as exc:
        raise ReleaseError("review.reviewed_at must be an ISO8601 timestamp with timezone.") from exc
    sources = provenance.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ReleaseError("Provenance requires at least one declared source.")
    verification = []
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get("uri"), str) or not source["uri"].strip():
            raise ReleaseError("Every source requires a nonempty uri.")
        source_hash = source.get("sha256")
        if not isinstance(source_hash, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", source_hash):
            raise ReleaseError("Every source requires an explicit SHA-256 checksum.")
        status = "contributor_declared"
        if "path" in source:
            if not isinstance(source["path"], str) or not source["path"]:
                raise ReleaseError("A local source path must be a nonempty string.")
            local_source = Path(source["path"])
            if not local_source.is_absolute():
                local_source = path.parent / local_source
            if not local_source.is_file() or sha256_file(local_source) != source_hash.lower():
                raise ReleaseError(f"Local source checksum does not match: {source['uri']}")
            status = "verified_local"
        verification.append({"uri": source["uri"], "sha256": source_hash.lower(), "status": status})
    return provenance, verification


def _filtered_rows(df: pd.DataFrame, quality: dict[str, Any]) -> pd.DataFrame:
    accepted = {
        tuple(observation["identity"][column] for column in IDENTITY_COLUMNS)
        for observation in quality["observations"] if observation["eligible"]
    }
    if not accepted:
        return df.iloc[:0].copy()
    index = pd.MultiIndex.from_frame(df[list(IDENTITY_COLUMNS)])
    filtered = df.loc[index.isin(accepted)].copy()
    sample_column = "time_s" if quality["contract"]["mode"] == "time" else "phase_ipsi"
    return filtered.sort_values(list(IDENTITY_COLUMNS) + [sample_column], kind="stable")


def _exclusion_table(quality: dict[str, Any]) -> pa.Table:
    schema = pa.schema(
        [(column, pa.string()) for column in IDENTITY_COLUMNS]
        + [
            ("task", pa.string()), ("task_id", pa.string()),
            ("observation_type", pa.string()), ("status", pa.string()),
            ("row_count", pa.int64()), ("reasons_json", pa.string()),
        ]
    )
    records = []
    for observation in quality["observations"]:
        if observation["eligible"]:
            continue
        records.append({
            **observation["identity"],
            **{column: observation[column] for column in (
                "task", "task_id", "observation_type", "status", "row_count"
            )},
            "reasons_json": json.dumps(observation["reasons"], allow_nan=False),
        })
    return pa.Table.from_pylist(records, schema=schema)


def _publish_directory(stage: Path, destination: Path) -> None:
    """Atomically rename without replacing even a concurrently created empty directory."""
    if sys.platform.startswith("linux"):
        libc = ctypes.CDLL(None, use_errno=True)
        rename = getattr(libc, "renameat2", None)
        if rename is None:
            raise ReleaseError("This host lacks atomic no-overwrite directory publication.")
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        # AT_FDCWD and RENAME_NOREPLACE are Linux API constants.
        if rename(-100, os.fsencode(stage), -100, os.fsencode(destination), 1) != 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error), str(destination))
    elif os.name == "nt":
        # Windows rename already refuses an existing destination.
        os.rename(stage, destination)
    else:
        raise ReleaseError("Atomic no-overwrite release publication is supported on Linux/WSL and Windows.")


def _release_card(manifest: dict, quality: dict, provenance: dict) -> str:
    """Render the already-computed release result without re-reading a dataset."""
    counts = manifest["counts"]
    coverage = quality["coverage"]
    types = ", ".join(
        f"{name}: {count}" for name, count in sorted(coverage["observation_types"].items())
    )
    lines = [
        f"# {manifest['dataset_id']} — {manifest['release_id']}",
        "",
        "This bundle contains the complete identified export and a separate subset "
        "selected by the recorded quality profile.",
        "",
        f"- Participants: {coverage['participants']}",
        f"- Observation types: {types}",
        f"- Full export: {counts['full_observations']} observations, {counts['full_rows']} rows",
        f"- Filtered export: {counts['filtered_observations']} observations, {counts['filtered_rows']} rows",
        f"- Observations with executed range checks: {coverage['assessed_observations']}",
        f"- Informational waveform warnings: {coverage['warning_count']}",
        f"- Constant finite signals (informational): {coverage['constant_signals']}",
        f"- Profile: {manifest['profile']['filename'] or 'None; no observations qualify for the filtered export'}",
        f"- Profile review status: {manifest['profile']['review_status']}",
        "",
        "## Downloads and evidence",
        "",
        "- [Full Parquet export](full.parquet)",
        "- [Filtered Parquet export](filtered.parquet)",
        "- [Exclusion ledger](exclusions.parquet)",
        "- [Quality results and per-signal coverage](quality.json)",
        "- [Manifest and artifact checksums](manifest.json)",
        "- [Source provenance](provenance.json)",
        "",
        "## Task coverage",
        "",
        "| Task | Full observations | Filtered observations |",
        "| --- | ---: | ---: |",
    ]
    lines.extend(
        f"| {task} | {values['total_observations']} | {values['eligible_observations']} |"
        for task, values in coverage["tasks"].items()
    )
    lines.extend([
        "",
        "## Assessment and availability",
        "",
        "Observation states: " + ", ".join(
            f"{state}: {count}" for state, count in counts["observation_statuses"].items()
        ) + ".",
        "",
        "Signal states: " + ", ".join(
            f"{state}: {count}" for state, count in coverage["signal_states"].items()
        ) + ". Missing optional signals are documented in quality results and do not "
        "by themselves exclude observations. Passing applies only to the selected profile.",
        "",
        "## Review and limitations",
        "",
        f"Source review recorded by {manifest['review']['reviewer']} "
        f"at {manifest['review']['reviewed_at']}.",
        f"Converter: {manifest['converter']['name']} ({manifest['converter']['revision']}).",
        "",
    ])
    if "license" in provenance:
        lines.extend([f"Source license declaration: {provenance['license']}.", ""])
    if "citation" in provenance:
        lines.extend([f"Source citation: {provenance['citation']}.", ""])
    lines.extend(f"- {limitation}" for limitation in manifest["limitations"])
    lines.extend(
        f"- Contract warning: {issue['message']}"
        for issue in quality["contract"]["issues"] if issue["severity"] == "warning"
    )
    return "\n".join(lines) + "\n"


def build_release(
    input_path: Path,
    output_dir: Path,
    provenance_path: Path,
    *,
    ranges_path: Optional[Path] = None,
    mode: Optional[str] = None,
    required_features: Optional[list[str]] = None,
    memory_budget_mb: int = 256,
    max_input_rows: int = 500_000,
) -> dict[str, Any]:
    """Build locally; refuse overwrites, invented source IDs and oversized input.

    The full Parquet is copied byte-for-byte. The filtered Parquet retains whole
    eligible observations. An unpublished staging directory is removed on error.
    This function neither uploads data nor changes the source export.
    """
    input_path = Path(input_path).resolve()
    output_dir = Path(output_dir).absolute()
    provenance_path = Path(provenance_path).resolve()
    ranges_path = Path(ranges_path).resolve() if ranges_path is not None else None
    if output_dir.exists() or output_dir.is_symlink():
        raise ReleaseError(f"Release directory already exists and will not be overwritten: {output_dir}")
    if not input_path.is_file() or input_path.suffix.lower() != ".parquet":
        raise ReleaseError("The release input must be an existing Parquet file.")
    admission = _admit_input(
        input_path, memory_budget_mb=memory_budget_mb, max_input_rows=max_input_rows
    )
    for metadata_path in (provenance_path, ranges_path):
        if metadata_path and metadata_path.stat().st_size > min(4 * 1024**2, memory_budget_mb * 1024**2 // 16):
            raise ReleaseError("Provenance/profile metadata exceeds the safe metadata size budget.")
    provenance_hash = sha256_file(provenance_path)
    provenance, source_verification = _read_provenance(provenance_path)
    profile_hash = sha256_file(ranges_path) if ranges_path else None
    config = ValidationConfigManager(ranges_path) if ranges_path else None
    profile_review = config.get_metadata("review_status") if config else None
    if profile_review is not None and (
        not isinstance(profile_review, str) or profile_review not in {"reviewed", "approved"}
    ):
        raise ReleaseError(
            f"Profile review_status={profile_review!r} cannot be published; use a reviewed or approved profile."
        )
    input_hash = sha256_file(input_path)
    # One bounded admitted eager read; use_threads=False avoids a CPU burst.
    table = pq.read_table(input_path, use_threads=False)
    df = table.to_pandas(split_blocks=True)
    del table
    if sha256_file(input_path) != input_hash:
        raise ReleaseError("Input changed while it was being read.")
    quality = assess_observations(df, config, mode=mode, required_features=required_features)
    if not quality["publishable"]:
        details = "; ".join(issue["message"] for issue in quality["contract"]["issues"][:5])
        raise ReleaseError(
            f"Dataset is not publishable ({quality['contract']['review_status']}): {details}"
        )
    quality["profile"] = {
        "sha256": profile_hash, "filename": ranges_path.name if ranges_path else None,
        "required_features_override": required_features,
        "review_status": profile_review or ("legacy_unspecified" if config else "not_applicable"),
        "review": config.get_metadata("review") if config else None,
    }
    quality["source"] = {"input_sha256": input_hash, "provenance_sha256": provenance_hash}
    quality["limitations"].append(
        "Memory admission is a conservative estimate, not a process memory cap; "
        "this release builder loads the admitted dataset into memory."
    )
    if any(source["status"] == "contributor_declared" for source in source_verification):
        quality["limitations"].append(
            "Remote source checksums were declared by the contributor and were not downloaded or independently verified."
        )
    if config and profile_review is None:
        quality["limitations"].append(
            "The legacy profile has no explicit review status; this release records no inferred profile approval."
        )
    filtered = _filtered_rows(df, quality)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive sibling lock prevents two builders from publishing the same ID.
    lock_path = output_dir.parent / f".{output_dir.name}.release.lock"
    try:
        lock_fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ReleaseError(f"Another release build or stale lock exists: {lock_path}") from exc
    os.close(lock_fd)
    stage: Optional[Path] = None
    try:
        if output_dir.exists() or output_dir.is_symlink():
            raise ReleaseError(f"Release directory appeared during build: {output_dir}")
        stage = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.staging-", dir=output_dir.parent))
        shutil.copyfile(input_path, stage / "full.parquet")
        if sha256_file(stage / "full.parquet") != input_hash:
            raise ReleaseError("Input changed during release creation; retry from a stable export.")
        pq.write_table(
            pa.Table.from_pandas(filtered, preserve_index=False),
            stage / "filtered.parquet", row_group_size=16_384, compression="zstd",
        )
        pq.write_table(_exclusion_table(quality), stage / "exclusions.parquet", row_group_size=16_384)
        _write_json(stage / "quality.json", quality)
        shutil.copyfile(provenance_path, stage / "provenance.json")
        if sha256_file(stage / "provenance.json") != provenance_hash:
            raise ReleaseError("Provenance changed during release creation.")
        if ranges_path:
            shutil.copyfile(ranges_path, stage / "profile.yaml")
            if sha256_file(stage / "profile.yaml") != profile_hash:
                raise ReleaseError("Validation profile changed during release creation.")
        manifest = {
            "schema_version": CONTRACT_VERSION,
            "dataset_id": provenance["dataset_id"], "release_id": provenance["release_id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "mode": quality["contract"]["mode"], "contract": quality["contract"],
            "input": {"filename": input_path.name, "sha256": input_hash, **admission},
            "sources": source_verification,
            "converter": provenance["converter"], "review": provenance["review"],
            "profile": quality["profile"],
            "filter_policy": {
                "unit": "whole_observation",
                "required_signals": "All required signals finite and passing all configured checks",
                "optional_signals": "Missing allowed; present failed or invalid signals exclude observation",
                "unmatched_profile": "unchecked; excluded",
                "universal_pass_rate_threshold": None,
            },
            "counts": {
                "full_rows": len(df), "filtered_rows": len(filtered),
                "full_observations": len(quality["observations"]),
                "filtered_observations": quality["coverage"]["eligible_observations"],
                "observation_statuses": quality["counts"],
            },
            "artifacts": {},
            "processing_code": {
                str(path.relative_to(ROOT)): sha256_file(path)
                for path in (
                    Path(__file__).resolve(),
                    ROOT / "contributor_tools/common/data_contract.py",
                    ROOT / "contributor_tools/common/config_manager.py",
                    ROOT / "contributor_tools/common/task_registry.py",
                    ROOT / "contributor_tools/common/feature_constants.py",
                )
            },
            "software": {
                "python": sys.version.split()[0], "numpy": np.__version__,
                "pandas": pd.__version__, "pyarrow": pa.__version__,
            },
            "limitations": quality["limitations"],
        }
        (stage / "README.md").write_text(_release_card(manifest, quality, provenance), encoding="utf-8")
        manifest["artifacts"] = {
            path.name: {"sha256": sha256_file(path), "size_bytes": path.stat().st_size}
            for path in sorted(stage.iterdir())
        }
        _write_json(stage / "manifest.json", manifest)
        (stage / "manifest.sha256").write_text(
            f"{sha256_file(stage / 'manifest.json')}  manifest.json\n", encoding="utf-8"
        )
        # Both directories are on the same filesystem. Readers see either no
        # release or the complete directory. Never merge into an existing one.
        if output_dir.exists() or output_dir.is_symlink():
            raise ReleaseError(f"Release destination already exists: {output_dir}")
        _publish_directory(stage, output_dir)
        stage = None
        return manifest
    finally:
        if stage is not None:
            shutil.rmtree(stage)
        lock_path.unlink(missing_ok=True)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--ranges", type=Path)
    parser.add_argument("--mode", choices=("phase", "time", "ensemble"))
    parser.add_argument("--required-feature", action="append", dest="required_features")
    parser.add_argument("--memory-budget-mb", type=int, default=256)
    parser.add_argument("--max-input-rows", type=int, default=500_000)
    args = parser.parse_args(argv)
    if hasattr(os, "nice"):
        try:
            os.nice(10)
        except OSError:
            pass
    try:
        manifest = build_release(
            args.input, args.output_dir, args.provenance,
            ranges_path=args.ranges, mode=args.mode, required_features=args.required_features,
            memory_budget_mb=args.memory_budget_mb, max_input_rows=args.max_input_rows,
        )
    except (ValueError, OSError, pa.ArrowException) as exc:
        print(f"Release not created: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "release": str(args.output_dir), "dataset_id": manifest["dataset_id"],
        "release_id": manifest["release_id"], "counts": manifest["counts"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
