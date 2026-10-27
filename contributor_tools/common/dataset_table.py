"""Internal table adapter for conversion review tools, not an analysis SDK.

New releases use the explicit data contract. Legacy files can be inspected only
when their stored keys identify complete cycles; source provenance is never
inferred from row order.
"""
from pathlib import Path
import os
import re

import numpy as np
import pandas as pd

from .feature_constants import CANONICAL_COLUMN_GROUPS, LEGACY_GRF_ALIASES


def read_review_table(path, columns=None):
    """Admit only small review tables; large releases need bounded tooling.

    Four times Parquet's uncompressed size is a conservative admission estimate,
    not a promise about pandas memory. Avoids accidentally loading GB-sized files.
    """
    path = Path(path)
    budget = int(os.environ.get("LOCOHUB_REVIEW_MEMORY_MB", "256")) * 1024**2
    if budget <= 0:
        raise ValueError("LOCOHUB_REVIEW_MEMORY_MB must be positive")
    if path.suffix.lower() in {".csv", ".txt"}:
        estimate = path.stat().st_size * 12
    else:
        import pyarrow.parquet as pq
        with pq.ParquetFile(path) as parquet:
            estimate = sum(
                parquet.metadata.row_group(i).total_byte_size
                for i in range(parquet.metadata.num_row_groups)
            ) * 4 + parquet.metadata.num_rows * (len(parquet.schema_arrow) * 96 + 512)
    if estimate > budget:
        raise MemoryError(
            f"Review load estimated at {estimate / 1024**2:.0f} MiB exceeds "
            f"{budget / 1024**2:.0f} MiB budget. Use a small source-derived pilot "
            "or bounded audit tools; this command will not load the file."
        )
    if path.suffix.lower() in {".csv", ".txt"}:
        return pd.read_csv(path, usecols=columns)
    return pd.read_parquet(path, columns=columns)


def phase_groups(df, phase_col="phase_ipsi", subject_col="subject", task_col="task"):
    """Return positional indices for complete observations, sorted by phase.

    Reject ambiguous legacy identities rather than silently splitting or mixing
    recordings. The original dataframe index need not be unique.
    """
    if df.empty:
        raise ValueError("No observations to assess")
    if phase_col not in df:
        raise ValueError(f"Missing phase column: {phase_col}")
    if {"source_recording_id", "observation_id"}.issubset(df.columns):
        keys = [subject_col, "source_recording_id", "observation_id"]
        if "reference_side" in df:
            keys.append("reference_side")
    else:
        keys = [subject_col, task_col]
        keys += [c for c in ("task_id", "step") if c in df]
        if "step" not in keys:
            raise ValueError("Missing observation identity: observation_id or legacy step")
    missing = [c for c in keys if c not in df]
    if missing:
        raise ValueError(f"Missing observation identity columns: {missing}")
    if df[keys].isna().any().any():
        raise ValueError("Observation identity contains missing values")
    groups = []
    for key, positions in df.groupby(keys, sort=False, dropna=False).indices.items():
        group = df.iloc[positions]
        if len(group) != 150:
            raise ValueError(
                f"Observation {key!r} has {len(group)} rows, expected 150. "
                "Repeated legacy keys require reconversion with recording/observation IDs."
            )
        for column in (subject_col, task_col, "task_id", "observation_type"):
            if column in group and group[column].nunique(dropna=False) != 1:
                raise ValueError(f"Observation {key!r} mixes {column}")
        phase = pd.to_numeric(group[phase_col], errors="coerce").to_numpy(float)
        order = np.argsort(phase, kind="stable")
        if not np.allclose(phase[order], np.linspace(0, 100, 150), atol=1e-5, rtol=0):
            raise ValueError(f"Observation {key!r} does not have the inclusive 150-point 0–100 phase grid")
        groups.append((key, np.asarray(positions)[order]))
    return groups


class DatasetTable:
    """Minimal mutable table view for legacy reviewer/plotter integration.

    No cached arrays: editing a review table cannot leave stale extraction data.
    """
    POINTS_PER_CYCLE = 150

    def __init__(self, data_path, subject_col="subject", task_col="task",
                 phase_col="phase_ipsi", file_type="auto"):
        self.data_path = Path(data_path)
        self.subject_col, self.task_col, self.phase_col = subject_col, task_col, phase_col
        frame = read_review_table(self.data_path)
        self.df = frame.rename(columns={
            old: new for old, new in LEGACY_GRF_ALIASES.items()
            if old in frame and new not in frame
        })

    @classmethod
    def from_frame(cls, frame, data_path="in_memory", phase_col="phase_ipsi"):
        instance = cls.__new__(cls)
        instance.data_path = Path(data_path)
        instance.subject_col, instance.task_col = "subject", "task"
        instance.phase_col = phase_col
        instance.df = frame
        return instance

    @property
    def features(self):
        canonical = {name for group in CANONICAL_COLUMN_GROUPS.values() for name in group}
        return [
            c for c in self.df.columns if c in canonical or
            re.search(r"_(?:rad(?:_s2?)?|Nm(?:_kg)?|BW|N|m|W(?:_kg)?|mV|uV|mvc|peak)$", c)
        ]

    def get_tasks(self):
        return sorted(self.df[self.task_col].dropna().unique().tolist())

    def get_subjects(self):
        return sorted(self.df[self.subject_col].dropna().unique().tolist())

    def get_cycles(self, subject=None, task=None, features=None):
        frame = self.df
        if subject is not None:
            frame = frame[frame[self.subject_col] == subject]
        if task is not None:
            frame = frame[frame[self.task_col] == task]
        selected = self.features if features is None else list(features)
        missing = sorted(set(selected) - set(frame.columns))
        if missing:
            raise ValueError(f"Requested signals are unavailable: {missing}")
        if frame.empty:
            return None, selected
        groups = phase_groups(frame, self.phase_col, self.subject_col, self.task_col)
        return np.stack([frame.iloc[pos][selected].to_numpy(float) for _, pos in groups]), selected
