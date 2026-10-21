"""Internal observation contract and quality assessment for dataset releases.

An observation is identified by source metadata, never by its position in a file.
This module intentionally has no dependency on a public analysis SDK.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
import json
from typing import Any, Optional

import numpy as np
import pandas as pd

from .config_manager import ValidationConfigManager
from .task_registry import is_valid_task


CONTRACT_VERSION = "2.0"
IDENTITY_COLUMNS = (
    "subject", "source_recording_id", "observation_id", "reference_side"
)
OBSERVATION_TYPES = {
    "individual_cycle", "transfer", "ensemble_curve", "continuous_recording"
}
PHASE_GRID = np.linspace(0.0, 100.0, 150)
QUALITY_STATES = ("passed", "failed", "missing", "unchecked", "invalid")
_METADATA_COLUMNS = (
    "task", "task_id", "task_info", "observation_type",
    "subject_metadata", "source_start_time_s", "source_end_time_s",
)


@dataclass
class ContractIssue:
    code: str
    message: str
    identity: Optional[dict[str, str]] = None
    severity: str = "error"


@dataclass
class ContractResult:
    mode: str
    schema_passed: bool = False
    publishable: bool = False
    review_status: str = "unreviewed"
    observation_count: int = 0
    issues: list[ContractIssue] = field(default_factory=list)
    schema_version: str = CONTRACT_VERSION
    identity_columns: tuple[str, ...] = IDENTITY_COLUMNS

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _identity(key: tuple) -> dict[str, str]:
    return dict(zip(IDENTITY_COLUMNS, (str(value) for value in key)))


def _identity_key(identity: dict[str, str]) -> tuple[str, ...]:
    return tuple(identity[column] for column in IDENTITY_COLUMNS)


def _groups(df: pd.DataFrame):
    return df.groupby(list(IDENTITY_COLUMNS), sort=False, dropna=False)


def _nonempty_strings(values: pd.Series) -> bool:
    return bool(values.map(
        lambda value: isinstance(value, str) and bool(value.strip())
    ).all())


def _json_object(value: Any) -> dict:
    if isinstance(value, str):
        def unique_keys(pairs):
            result = {}
            for key, item in pairs:
                if key in result:
                    raise ValueError(f"Duplicate metadata key: {key}")
                result[key] = item
            return result
        value = json.loads(value, object_pairs_hook=unique_keys)
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    # Reject NaN/Infinity and unserializable values inside metadata too.
    json.dumps(value, allow_nan=False, sort_keys=True)
    return value


def _metadata_token(value: Any) -> str:
    """Compare typed metadata, treating equivalent finite numeric values alike."""
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not np.isfinite(value):
            raise ValueError("Metadata numbers must be finite")
        return "number:" + str(float(value))
    return json.dumps(value, sort_keys=True, allow_nan=False)


def _numeric(values: pd.Series) -> np.ndarray:
    if not pd.api.types.is_numeric_dtype(values.dtype) or pd.api.types.is_bool_dtype(values.dtype):
        raise ValueError("Values must have a numeric dtype")
    return values.to_numpy(dtype=float, na_value=np.nan)


def _mode(df: pd.DataFrame, mode: Optional[str]) -> str:
    if mode is not None:
        if mode not in {"phase", "time", "ensemble"}:
            raise ValueError("mode must be phase, time, or ensemble")
        return mode
    if "phase_ipsi" in df:
        if (
            "observation_type" in df and not df.empty
            and df.observation_type.map(
                lambda value: isinstance(value, str) and value == "ensemble_curve"
            ).all()
        ):
            return "ensemble"
        return "phase"
    return "time"


def inspect_contract(
    df: pd.DataFrame, *, mode: Optional[str] = None
) -> ContractResult:
    """Check explicit source identities, metadata, and each observation's index.

    Legacy rows without source identities remain unreviewed. They are never
    assigned IDs or promoted to publishable data by this function.
    """
    result = ContractResult(mode=_mode(df, mode))
    index_column = "time_s" if result.mode == "time" else "phase_ipsi"
    required = list(IDENTITY_COLUMNS) + [
        "observation_type", "task", "task_id", "task_info", index_column
    ]
    missing = [column for column in required if column not in df]
    if missing:
        result.issues.append(ContractIssue(
            "missing_columns", f"Missing required columns: {', '.join(missing)}"
        ))
        if any(column in missing for column in IDENTITY_COLUMNS):
            result.issues.append(ContractIssue(
                "unreviewed_identity",
                "Source recording and observation identities must come from the source converter; "
                "legacy row positions and step numbers are insufficient.",
            ))
        return result
    if df.empty:
        result.issues.append(ContractIssue("empty_dataset", "The dataset has no observations."))
        return result
    for column in IDENTITY_COLUMNS:
        if not _nonempty_strings(df[column]):
            result.issues.append(ContractIssue(
                "invalid_identity", f"{column} must contain nonempty strings."
            ))
    if result.issues:
        return result
    result.review_status = "identified"
    for key, group in _groups(df):
        identity = _identity(key)
        result.observation_count += 1

        def issue(code: str, message: str) -> None:
            result.issues.append(ContractIssue(code, message, identity))

        side = identity["reference_side"]
        observation_type = group["observation_type"].iloc[0]
        if side == "unknown" and observation_type == "ensemble_curve":
            result.issues.append(ContractIssue(
                "unknown_ensemble_reference_side",
                "The source ensemble does not identify its anatomical reference side.",
                identity, severity="warning",
            ))
        elif side not in {"left", "right", "none"}:
            issue("unreviewed_reference_side", "reference_side must explicitly be left, right, or none.")
            result.review_status = "unreviewed"
        for column in _METADATA_COLUMNS:
            if column not in group:
                continue
            values = group[column]
            if column in {"source_start_time_s", "source_end_time_s"} and values.isna().all():
                # An explicitly unavailable source clock is not fabricated from
                # the normalized phase axis (e.g. source ensemble/transfer data).
                continue
            if column in {"task_info", "subject_metadata"}:
                try:
                    unique = {
                        json.dumps(_json_object(value), sort_keys=True, allow_nan=False)
                        for value in values
                    }
                except (ValueError, TypeError):
                    issue("invalid_metadata", f"{column} must contain finite JSON objects.")
                    continue
            else:
                try:
                    unique = {
                        json.dumps(value, sort_keys=True, allow_nan=False)
                        for value in values.dropna().tolist()
                    }
                except (ValueError, TypeError):
                    issue("invalid_metadata", f"{column} contains unsupported metadata values.")
                    continue
            if len(unique) != 1 or values.isna().any():
                issue("inconsistent_metadata", f"{column} must be present and constant within an observation.")
        for column in ("task", "task_id", "observation_type"):
            if not _nonempty_strings(group[column]):
                issue("invalid_metadata", f"{column} must contain nonempty strings.")
        # No metadata source silently takes precedence over another source.
        try:
            sources = {
                column: _json_object(group[column].iloc[0])
                for column in ("task_info", "subject_metadata") if column in group
            }
            fields = set().union(*(values.keys() for values in sources.values()))
            for name in fields:
                candidates = [
                    _metadata_token(values[name]) for values in sources.values() if name in values
                ]
                if name in group and name not in {"task_info", "subject_metadata"}:
                    candidates.extend(_metadata_token(value) for value in group[name].tolist())
                if len(set(candidates)) > 1:
                    issue("conflicting_metadata", f"{name} conflicts across metadata sources or rows.")
        except (ValueError, TypeError):
            issue("invalid_metadata", "Cannot resolve finite metadata consistently across sources.")
        task = group["task"].iloc[0]
        if not isinstance(task, str) or not is_valid_task(task):
            issue("unknown_task", f"Task is not in the canonical task registry: {task!r}.")
        if not isinstance(observation_type, str) or observation_type not in OBSERVATION_TYPES:
            issue("unknown_observation_type", f"Unsupported observation_type: {observation_type!r}.")
        elif result.mode == "time" and observation_type == "ensemble_curve":
            issue("wrong_observation_mode", "An ensemble curve needs an explicit normalized phase grid.")
        elif result.mode != "time" and observation_type == "continuous_recording":
            issue("wrong_observation_mode", "A continuous recording must use time mode.")
        elif result.mode == "ensemble" and observation_type != "ensemble_curve":
            issue("wrong_observation_mode", "Ensemble mode only accepts ensemble_curve observations.")
        limb_columns = [column for column in group if "_ipsi_" in column or "_contra_" in column]
        if side == "none" and limb_columns and observation_type not in {"ensemble_curve", "transfer"}:
            issue("missing_reference_side", "Limb-indexed cycles require an explicit left or right reference.")
        try:
            index = np.sort(_numeric(group[index_column]))
        except (ValueError, TypeError):
            issue("invalid_index", f"{index_column} must have numeric values.")
            continue
        if not np.isfinite(index).all():
            issue("invalid_index", f"{index_column} contains missing or nonfinite values.")
        elif result.mode == "time":
            if len(index) < 2 or np.any(np.diff(index) <= 0):
                issue("invalid_time_order", "Each time observation needs at least two strictly increasing samples.")
        elif len(index) != 150:
            issue("invalid_phase_length", f"Expected 150 phase samples; found {len(index)}.")
        elif not np.allclose(index, PHASE_GRID, rtol=0, atol=1e-5):
            issue("invalid_phase_grid", "Phase must contain the inclusive 150-sample 0–100 grid without duplicates.")
        start_present = "source_start_time_s" in group
        end_present = "source_end_time_s" in group
        if start_present != end_present:
            issue("incomplete_source_bounds", "Provide both source_start_time_s and source_end_time_s.")
        elif start_present:
            if group["source_start_time_s"].isna().all() and group["source_end_time_s"].isna().all():
                continue
            try:
                start = _numeric(group["source_start_time_s"])
                end = _numeric(group["source_end_time_s"])
                if not (np.isfinite(start).all() and np.isfinite(end).all() and np.all(end > start)):
                    issue("invalid_source_bounds", "Source event bounds must be finite with end greater than start.")
            except (ValueError, TypeError):
                issue("invalid_source_bounds", "Source event bounds must be numeric.")
    result.schema_passed = not any(issue.severity == "error" for issue in result.issues)
    result.publishable = result.schema_passed and result.review_status == "identified"
    return result


def _signal_columns(df: pd.DataFrame) -> set[str]:
    return {
        column for column in df
        if column.startswith(("grf_", "cop_", "emg_"))
        or any(token in column for token in (
            "_angle_", "_velocity_", "_acceleration_", "_moment_", "_power_"
        ))
    }


def _feature_list(value: Any, name: str) -> set[str]:
    if not isinstance(value, (list, tuple)) or any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"{name} must be a list of nonempty feature names")
    return set(value)


def _bounds(value: Any, name: str) -> tuple[float, float]:
    if not isinstance(value, dict):
        raise ValueError(f"Invalid range for {name}")
    low, high = value.get("min"), value.get("max")
    if isinstance(low, bool) or isinstance(high, bool):
        raise ValueError(f"Range bounds for {name} must be finite numbers")
    try:
        low, high = float(low), float(high)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Range bounds for {name} must be finite numbers") from exc
    if not np.isfinite([low, high]).all() or low > high:
        raise ValueError(f"Invalid finite min/max range for {name}")
    return low, high


def _match_applicability(group: pd.DataFrame, rules: Any) -> dict[str, Any]:
    if not isinstance(rules, dict):
        raise ValueError("Profile applicability must be a mapping")
    result: dict[str, Any] = {
        "specified": bool(rules), "matched": True, "values": {}, "reasons": [], "invalid": False
    }
    for name, allowed in rules.items():
        if not isinstance(name, str) or not isinstance(allowed, list) or not allowed:
            raise ValueError("Applicability requires field names mapped to nonempty lists")
        if any(
            item is None or not isinstance(item, (str, int, float, bool))
            for item in allowed
        ):
            raise ValueError(f"Applicability values for {name} must be non-null JSON scalars")
        allowed_tokens = {_metadata_token(item) for item in allowed}
        candidates = []
        try:
            if name in group:
                candidates.extend(group[name].tolist())
            for column in ("task_info", "subject_metadata"):
                if column in group:
                    metadata = _json_object(group[column].iloc[0])
                    if name in metadata:
                        candidates.append(metadata[name])
            def missing(value):
                return value is None or value is pd.NA or (
                    isinstance(value, (float, np.floating)) and np.isnan(value)
                )
            if not candidates or all(missing(value) for value in candidates):
                result["matched"] = False
                result["values"][name] = None
                result["reasons"].append(f"Applicability metadata {name} is missing")
                continue
            if any(missing(value) or not isinstance(value, (str, int, float, bool, np.generic)) for value in candidates):
                raise ValueError("Required applicability metadata must be a consistent scalar")
            tokens = {_metadata_token(value) for value in candidates}
            if len(tokens) != 1:
                raise ValueError("Metadata sources disagree")
            value = candidates[0]
            result["values"][name] = value.item() if isinstance(value, np.generic) else value
            if not tokens <= allowed_tokens:
                result["matched"] = False
                result["reasons"].append(f"Applicability metadata {name} does not match this profile")
        except (ValueError, TypeError):
            result["invalid"] = True
            result["matched"] = False
            result["reasons"].append(f"Applicability metadata {name} is invalid or conflicting")
    return result


def assess_observations(
    df: pd.DataFrame,
    config: Optional[ValidationConfigManager] = None,
    *,
    mode: Optional[str] = None,
    required_features: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Assess observations without deleting rows or imputing missing signals.

    Task metadata may declare ``required_features``, ``optional_features``,
    ``observation_types``, ``applicability``, ``time_ranges``, and ``waveform_ranges``. With older profiles, every
    configured field is required. Ensembles require explicit profile opt-in.
    No profile, unmatched tasks, or zero mandatory checks never produce a
    passing filtered observation.
    """
    contract = inspect_contract(df, mode=mode)
    result: dict[str, Any] = {
        "schema_version": CONTRACT_VERSION,
        "schema_passed": contract.schema_passed,
        "publishable": contract.publishable,
        "contract": contract.to_dict(),
        "observations": [],
        "counts": {state: 0 for state in QUALITY_STATES},
        "coverage": {},
        "limitations": [
            "Range checks do not establish correct coordinate frames, force-plate assignments, "
            "event detection, or source measurement validity.",
            "A passing observation satisfies this profile only; it is not a universal quality certification.",
        ],
    }
    if not all(column in df and _nonempty_strings(df[column]) for column in IDENTITY_COLUMNS):
        result["coverage"] = {
            "total_rows": len(df), "total_observations": 0,
            "assessed_observations": 0, "eligible_observations": 0,
        }
        return result
    issue_map: dict[tuple, list[str]] = {}
    global_issues = [
        issue.code for issue in contract.issues
        if issue.identity is None and issue.severity == "error"
    ]
    for issue in contract.issues:
        if issue.identity and issue.severity == "error":
            issue_map.setdefault(_identity_key(issue.identity), []).append(issue.code)
    observed_signals = _signal_columns(df)
    signal_counts: Counter = Counter()
    executed_checks = 0
    available_profile_tasks = set(config.get_tasks()) if config else set()
    for key, group in _groups(df):
        index_column = "time_s" if contract.mode == "time" else "phase_ipsi"
        if index_column in group:
            group = group.sort_values(index_column, kind="stable")
        identity = _identity(key)
        task = str(group["task"].iloc[0]) if "task" in group else ""
        observation_type = str(group["observation_type"].iloc[0]) if "observation_type" in group else ""
        metadata = config.get_task_metadata(task) if config and task in available_profile_tasks else {}
        phase_ranges = config.get_task_data(task) if config and task in available_profile_tasks else {}
        time_ranges = metadata.get("time_ranges", {})
        waveform_ranges = metadata.get("waveform_ranges", {})
        if not isinstance(time_ranges, dict):
            raise ValueError(f"time_ranges for {task} must be a mapping")
        if not isinstance(waveform_ranges, dict):
            raise ValueError(f"waveform_ranges for {task} must be a mapping")
        for phase, ranges in phase_ranges.items():
            if not np.isfinite(float(phase)) or not 0 <= float(phase) <= 100:
                raise ValueError(f"Invalid profile phase for {task}: {phase}")
            for feature, bounds in ranges.items():
                _bounds(bounds, feature)
        for feature, bounds in time_ranges.items():
            _bounds(bounds, feature)
        for feature, rules in waveform_ranges.items():
            if not isinstance(rules, dict) or not rules or set(rules) - {"min", "max", "max_abs_step"}:
                raise ValueError(f"Invalid waveform rule for {feature}")
            if "min" in rules or "max" in rules:
                _bounds(rules, feature)
            if "max_abs_step" in rules:
                limit = rules["max_abs_step"]
                if isinstance(limit, bool) or not isinstance(limit, (int, float)) or not np.isfinite(limit) or limit <= 0:
                    raise ValueError(f"max_abs_step for {feature} must be positive and finite")
        configured = set(time_ranges) if contract.mode == "time" else {
            feature for ranges in phase_ranges.values() for feature in ranges
        }
        configured |= set(waveform_ranges)
        optional = _feature_list(metadata.get("optional_features", []), "optional_features")
        if required_features is not None:
            required = _feature_list(required_features, "required_features")
        elif "required_features" in metadata:
            required = _feature_list(metadata["required_features"], "required_features")
        else:
            required = configured - optional
        if required & optional:
            raise ValueError(f"Required and optional features overlap for {task}")
        allowed_types = metadata.get("observation_types", ["individual_cycle", "transfer", "continuous_recording"])
        allowed_types = _feature_list(allowed_types, "observation_types")
        applicability = _match_applicability(group, metadata.get("applicability", {}))
        profile_applies = bool(
            task in available_profile_tasks and observation_type in allowed_types and applicability["matched"]
        )
        if task in available_profile_tasks and not applicability["specified"]:
            limitation = (
                "This profile does not declare population/condition applicability for every assessed task; "
                "no healthy-population or exoskeleton-condition match is inferred."
            )
            if limitation not in result["limitations"]:
                result["limitations"].append(limitation)
        issues = global_issues + issue_map.get(_identity_key(identity), [])
        if applicability["invalid"]:
            issues.append("invalid_applicability_metadata")
        signals = []
        for feature in sorted(observed_signals | configured | required | optional):
            item: dict[str, Any] = {
                "feature": feature, "required": feature in required,
                "status": "unchecked", "reason": "No applicable profile range",
                "checks": [], "warnings": [],
                "waveform": {
                    "sample_count": len(group), "finite_samples": 0,
                    "missing_samples": len(group), "infinite_samples": 0,
                    "constant": None, "maximum_absolute_step": None,
                },
            }
            if feature not in group or group[feature].isna().all():
                item.update(status="missing", reason="Signal unavailable")
            else:
                try:
                    values = _numeric(group[feature])
                except (ValueError, TypeError):
                    values = None
                    item.update(status="invalid", reason="Signal must have a numeric dtype")
                if values is not None:
                    finite = np.isfinite(values)
                    finite_values = values[finite]
                    with np.errstate(invalid="ignore", over="ignore"):
                        differences = np.abs(np.diff(np.where(finite, values, np.nan)))
                    available_differences = differences[~np.isnan(differences)]
                    maximum_step = float(available_differences.max()) if available_differences.size else None
                    item["waveform"] = {
                        "sample_count": len(values), "finite_samples": int(finite.sum()),
                        "missing_samples": int(np.isnan(values).sum()),
                        "infinite_samples": int(np.isinf(values).sum()),
                        "constant": bool(np.all(finite_values == finite_values[0])) if finite.all() and len(values) else None,
                        "maximum_absolute_step": maximum_step if maximum_step is None or np.isfinite(maximum_step) else None,
                    }
                    rule = waveform_ranges.get(feature, {})
                    if profile_applies and not issues and "max_abs_step" in rule:
                        jumps = differences > rule["max_abs_step"]
                        if jumps.any():
                            item["warnings"].append({
                                "code": "step_change_limit",
                                "threshold": float(rule["max_abs_step"]),
                                "exceeding_steps": int(jumps.sum()),
                                "message": "Adjacent-sample changes exceed the profile's review threshold.",
                            })
                    if np.isinf(values).any():
                        item.update(status="invalid", reason="Signal contains infinity")
                    elif np.isnan(values).any():
                        item.update(status="missing", reason="Signal is only partially available")
                    elif issues:
                        item.update(status="unchecked", reason="Observation structure is invalid")
                    elif profile_applies:
                        if contract.mode == "time" and feature in time_ranges:
                            low, high = _bounds(time_ranges[feature], feature)
                            outside = (values < low) | (values > high)
                            item["checks"].append({
                                "kind": "all_time_samples", "min": low, "max": high,
                                "sample_count": len(values), "failed_samples": int(outside.sum()),
                                "passed": not bool(outside.any()),
                            })
                            executed_checks += len(values)
                        elif contract.mode != "time":
                            for phase, ranges in sorted(phase_ranges.items()):
                                if feature not in ranges:
                                    continue
                                low, high = _bounds(ranges[feature], feature)
                                index = int(round(float(phase) * 149 / 100))
                                actual = float(values[index])
                                item["checks"].append({
                                    "kind": "phase_sample", "requested_phase": float(phase),
                                    "sample_phase": float(PHASE_GRID[index]), "sample_index": index,
                                    "value": actual, "min": low, "max": high,
                                    "passed": bool(low <= actual <= high),
                                })
                                executed_checks += 1
                        if "min" in rule:
                            low, high = _bounds(rule, feature)
                            outside = (values < low) | (values > high)
                            item["checks"].append({
                                "kind": "whole_waveform_range", "min": low, "max": high,
                                "sample_count": len(values), "failed_samples": int(outside.sum()),
                                "passed": not bool(outside.any()),
                            })
                            executed_checks += len(values)
                        if item["checks"]:
                            passed = all(check["passed"] for check in item["checks"])
                            item.update(
                                status="passed" if passed else "failed",
                                reason="All configured checks passed" if passed else "Outside configured range",
                            )
            signals.append(item)
            signal_counts[item["status"]] += 1
        by_name = {item["feature"]: item for item in signals}
        eligible = (
            not issues and profile_applies and bool(required)
            and all(by_name[name]["status"] == "passed" for name in required)
            and not any(item["status"] in {"failed", "invalid"} for item in signals)
        )
        if issues or any(item["status"] == "invalid" for item in signals):
            status = "invalid"
        elif not profile_applies:
            status = "unchecked"
        elif any(item["status"] == "failed" for item in signals):
            status = "failed"
        elif any(by_name[name]["status"] == "missing" for name in required):
            status = "missing"
        elif eligible:
            status = "passed"
        else:
            status = "unchecked"
        reasons = list(issues)
        reasons.extend(applicability["reasons"])
        if not profile_applies:
            reasons.append("No profile applies to this task and observation type")
        if not required:
            reasons.append("No required signals were configured")
        reasons.extend(
            f"{item['feature']}: {item['reason']}"
            for item in signals
            if item["status"] in {"failed", "invalid"} or (
                item["required"] and item["status"] != "passed"
            )
        )
        result["observations"].append({
            "identity": identity, "observation_type": observation_type,
            "task": task, "task_id": str(group["task_id"].iloc[0]) if "task_id" in group else "",
            "row_count": len(group), "status": status, "eligible": bool(eligible),
            "reasons": reasons, "signals": signals, "profile_applicability": applicability,
        })
        result["counts"][status] += 1
    result["coverage"] = {
        "total_rows": len(df),
        "total_observations": len(result["observations"]),
        "assessed_observations": sum(
            any(signal["checks"] for signal in item["signals"])
            for item in result["observations"]
        ),
        "eligible_observations": sum(item["eligible"] for item in result["observations"]),
        "executed_checks": executed_checks,
        "signal_states": {state: signal_counts[state] for state in QUALITY_STATES},
        "warning_count": sum(
            len(signal["warnings"]) for item in result["observations"] for signal in item["signals"]
        ),
        "constant_signals": sum(
            signal["waveform"]["constant"] is True
            for item in result["observations"] for signal in item["signals"]
        ),
        "participants": len({item["identity"]["subject"] for item in result["observations"]}),
        "observation_types": dict(Counter(item["observation_type"] for item in result["observations"])),
        "tasks": {
            task: {
                "total_observations": sum(item["task"] == task for item in result["observations"]),
                "eligible_observations": sum(
                    item["task"] == task and item["eligible"] for item in result["observations"]
                ),
            }
            for task in sorted({item["task"] for item in result["observations"]})
        },
    }
    return result
