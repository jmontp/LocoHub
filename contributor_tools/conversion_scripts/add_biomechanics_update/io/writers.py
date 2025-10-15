"""Output writers for AddBiomechanics conversion."""

from __future__ import annotations

import atexit
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .. import config


_TIME_WRITERS: Dict[Path, pq.ParquetWriter] = {}
_PHASE_WRITERS: Dict[Path, pq.ParquetWriter] = {}


def write_time_chunk(df: pd.DataFrame, events, output_root: Path, dataset_name: str) -> None:
    """Append a time-indexed chunk to the dataset export."""

    if df.empty:
        return

    paths = config.dataset_output_paths(output_root, dataset_name)
    step_values = _assign_steps(len(df), events.heel_strikes_ipsi)
    df_out = df.copy()
    df_out["step"] = step_values

    table = pa.Table.from_pandas(df_out, preserve_index=False)
    _write_table(Path(paths["time"]), table, cache=_TIME_WRITERS)


def write_phase_chunk(df: pd.DataFrame, events, output_root: Path, dataset_name: str) -> None:
    """Append a phase-indexed chunk to the dataset export."""

    stride_frames = _phase_dataframe_from_events(df, events)
    if not stride_frames:
        return

    paths = config.dataset_output_paths(output_root, dataset_name)
    phase_df = pd.concat(stride_frames, ignore_index=True)
    table = pa.Table.from_pandas(phase_df, preserve_index=False)
    _write_table(Path(paths["phase"]), table, cache=_PHASE_WRITERS)


def _assign_steps(length: int, heel_indices: list[int]) -> np.ndarray:
    if length == 0:
        return np.array([], dtype=int)

    if not heel_indices:
        return np.zeros(length, dtype=int)

    valid_indices = sorted(i for i in heel_indices if 0 <= i < length)
    if not valid_indices:
        return np.zeros(length, dtype=int)

    step = np.zeros(length, dtype=int)
    for stride_idx, start in enumerate(valid_indices):
        end = valid_indices[stride_idx + 1] if stride_idx + 1 < len(valid_indices) else length
        end = max(end, start + 1)
        step[start:end] = stride_idx
        if stride_idx == 0 and start > 0:
            step[:start] = 0
    if len(valid_indices) == 1:
        step[valid_indices[0]:] = 0
    return step


def _phase_dataframe_from_events(df: pd.DataFrame, events) -> list[pd.DataFrame]:
    heel_indices = sorted(i for i in events.heel_strikes_ipsi if 0 <= i < len(df))
    if len(heel_indices) < 2:
        return []

    numeric_cols = df.select_dtypes(include=[np.number, "bool"]).columns.tolist()
    for drop_col in ("step", "phase_ipsi", "phase_contra"):
        if drop_col in numeric_cols:
            numeric_cols.remove(drop_col)

    category_cols = [col for col in df.columns if col not in numeric_cols]

    frames: list[pd.DataFrame] = []
    for stride_idx in range(len(heel_indices) - 1):
        start, end = heel_indices[stride_idx], heel_indices[stride_idx + 1]
        if end - start < 2:
            continue

        stride_df = df.iloc[start:end].reset_index(drop=True)
        phase_original = np.linspace(0.0, 100.0, len(stride_df))
        phase_target = np.linspace(0.0, 100.0, 150)

        data = {"phase_ipsi": phase_target, "step": np.full_like(phase_target, stride_idx, dtype=int)}

        for col in numeric_cols:
            values = stride_df[col].to_numpy(dtype=float, copy=True)
            valid = np.isfinite(values)
            if valid.sum() < 2:
                fill_value = values[valid][0] if valid.any() else np.nan
                data[col] = np.full_like(phase_target, fill_value, dtype=float)
                continue
            data[col] = np.interp(phase_target, phase_original[valid], values[valid])

        for col in category_cols:
            value = stride_df[col].iloc[0]
            data[col] = np.repeat(value, len(phase_target))

        frames.append(pd.DataFrame(data))

    return frames


def _write_table(path: Path, table: pa.Table, *, cache: Dict[Path, pq.ParquetWriter]) -> None:
    writer = cache.get(path)
    if writer is None:
        path.parent.mkdir(parents=True, exist_ok=True)
        writer = pq.ParquetWriter(str(path), table.schema)
        cache[path] = writer
    writer.write_table(table)


def _close_writers() -> None:  # pragma: no cover - exercised at process exit
    for writer in list(_TIME_WRITERS.values()):
        writer.close()
    for writer in list(_PHASE_WRITERS.values()):
        writer.close()
    _TIME_WRITERS.clear()
    _PHASE_WRITERS.clear()


atexit.register(_close_writers)
