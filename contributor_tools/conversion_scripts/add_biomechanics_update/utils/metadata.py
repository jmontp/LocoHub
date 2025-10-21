"""Metadata helpers for AddBiomechanics conversion."""

from __future__ import annotations

import numpy as np
import pandas as pd


def attach_subject_metadata(df: pd.DataFrame, dataset_name: str) -> None:
    """Populate subject metadata columns in-place."""

    if "dataset" not in df.columns:
        df["dataset"] = dataset_name

    if "subject_metadata" not in df.columns:
        df["subject_metadata"] = None

    if "subject_mass" in df.columns:
        metadata = df["subject_mass"].apply(_mass_to_metadata)
        df["subject_metadata"] = metadata.fillna(df["subject_metadata"])


def _mass_to_metadata(value) -> str | None:
    try:
        mass = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(mass) or mass <= 0:
        return None
    return f"mass_kg:{mass:.3f}"
