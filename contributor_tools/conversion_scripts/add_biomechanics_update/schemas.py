"""Column normalization helpers for AddBiomechanics conversion."""

from __future__ import annotations

from typing import Iterable, List

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = [
    "subject",
    "task",
    "task_id",
    "task_info",
    "step",
    "time_s",
]


OPTIONAL_COLUMNS = [
    "phase_ipsi",
    "phase_contra",
    "subject_metadata",
    "dataset",
]


CANONICAL_ORDER = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

MOMENT_COLUMNS: List[str] = [
    "hip_flexion_moment_contra_Nm",
    "hip_adduction_moment_contra_Nm",
    "hip_rotation_moment_contra_Nm",
    "knee_flexion_moment_contra_Nm",
    "ankle_flexion_moment_contra_Nm",
    "ankle_rotation_moment_contra_Nm",
    "hip_flexion_moment_ipsi_Nm",
    "hip_adduction_moment_ipsi_Nm",
    "hip_rotation_moment_ipsi_Nm",
    "knee_flexion_moment_ipsi_Nm",
    "ankle_flexion_moment_ipsi_Nm",
    "ankle_rotation_moment_ipsi_Nm",
]


def normalize_columns(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    """Return a dataframe with canonical columns and derived features."""

    normalized = df.copy()

    if "dataset" not in normalized.columns:
        normalized["dataset"] = dataset_name

    # Ensure time column exists and is float
    if "time" in normalized.columns and "time_s" not in normalized.columns:
        normalized.rename(columns={"time": "time_s"}, inplace=True)
    normalized["time_s"] = normalized.get("time_s", 0.0).astype(float)

    if "task_raw" not in normalized.columns:
        if "task" in normalized.columns:
            normalized["task_raw"] = normalized["task"]
        elif "trial_id" in normalized.columns:
            normalized["task_raw"] = normalized["trial_id"]
        else:
            normalized["task_raw"] = "unspecified"

    raw_values = normalized["task_raw"].astype(str).fillna("unspecified")

    if "task" not in normalized.columns:
        normalized["task"] = raw_values.str.lower()
    if "task_id" not in normalized.columns:
        normalized["task_id"] = raw_values.str.lower()
    if "task_info" not in normalized.columns:
        normalized["task_info"] = ["variant:raw"] * len(normalized)

    if "step" not in normalized.columns:
        normalized["step"] = -1

    if "subject" in normalized.columns:
        normalized["subject"] = normalized["subject"].astype(str)

    _mass_normalize_moments(normalized)
    _compute_grf_body_weight(normalized)

    return normalized


def _mass_normalize_moments(df: pd.DataFrame) -> None:
    if "subject_mass" not in df.columns:
        return

    mass = df["subject_mass"].astype(float)
    mass = mass.where(mass > 0, np.nan)

    for col in MOMENT_COLUMNS:
        if col not in df.columns:
            continue
        target = col.replace("_Nm", "_Nm_kg")
        df[target] = df[col].astype(float).div(mass)
        df.drop(columns=[col], inplace=True)


def _compute_grf_body_weight(df: pd.DataFrame) -> None:
    if "subject_mass" not in df.columns:
        return

    mass = df["subject_mass"].astype(float)
    denom = mass * 9.80665
    denom = denom.where(denom != 0, np.nan)

    for limb in ("ipsi", "contra"):
        col = f"grf_vertical_{limb}_N"
        if col in df.columns:
            target = f"grf_vertical_{limb}_BW"
            df[target] = df[col].astype(float).div(denom)
