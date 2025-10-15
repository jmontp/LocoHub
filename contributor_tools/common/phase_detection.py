"""Shared utilities for detecting gait events from ground reaction forces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, MutableSequence, Optional, Sequence

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class VerticalGRFConfig:
    """Configuration for vertical ground-reaction-force event detection."""

    ipsi_col: str
    contra_col: str
    time_col: str = "time_s"
    threshold: float = 50.0  # Newtons
    min_interval_s: float = 0.3
    smoothing_window: int = 5
    retain_intermediate: bool = False


@dataclass
class VerticalGRFEvents:
    """Detected heel-strike and toe-off events by sample index."""

    heel_strikes_ipsi: np.ndarray
    heel_strikes_contra: np.ndarray
    toe_offs_ipsi: np.ndarray
    toe_offs_contra: np.ndarray
    sample_rate_hz: Optional[float]
    metadata: Dict[str, float]


def detect_vertical_grf_events(df: pd.DataFrame, config: VerticalGRFConfig) -> VerticalGRFEvents:
    """Detect heel strikes and toe offs from vertical GRF signals.

    Parameters
    ----------
    df:
        DataFrame containing vertical GRF columns and, optionally, a time column.
    config:
        Configuration describing column names and detection parameters.
    """

    required_cols = [config.ipsi_col, config.contra_col]
    for col in required_cols:
        if col not in df.columns:
            raise KeyError(f"Required GRF column '{col}' not found in dataframe")

    time_values = _extract_time(df, config.time_col)
    sample_rate_hz = _estimate_sample_rate(time_values)
    min_interval_samples = _compute_min_interval_samples(config, sample_rate_hz)

    ipsi_contact = _threshold_contact(df[config.ipsi_col].to_numpy(), config)
    contra_contact = _threshold_contact(df[config.contra_col].to_numpy(), config)

    heel_ipsi = _detect_events_from_contact(ipsi_contact, +1, min_interval_samples)
    toe_ipsi = _detect_events_from_contact(ipsi_contact, -1, min_interval_samples)
    heel_contra = _detect_events_from_contact(contra_contact, +1, min_interval_samples)
    toe_contra = _detect_events_from_contact(contra_contact, -1, min_interval_samples)

    metadata: Dict[str, float] = {}
    if sample_rate_hz is not None:
        metadata["sample_rate_hz"] = float(sample_rate_hz)
        metadata["min_interval_samples"] = float(min_interval_samples)

    return VerticalGRFEvents(
        heel_strikes_ipsi=heel_ipsi,
        heel_strikes_contra=heel_contra,
        toe_offs_ipsi=toe_ipsi,
        toe_offs_contra=toe_contra,
        sample_rate_hz=sample_rate_hz,
        metadata=metadata,
    )


def _extract_time(df: pd.DataFrame, time_col: str) -> Optional[np.ndarray]:
    if time_col not in df.columns:
        return None
    return df[time_col].to_numpy(dtype=float, copy=True)


def _estimate_sample_rate(time_values: Optional[np.ndarray]) -> Optional[float]:
    if time_values is None:
        return None
    if len(time_values) < 2:
        return None
    diffs = np.diff(time_values)
    diffs = diffs[diffs > 0]
    if diffs.size == 0:
        return None
    return float(1.0 / np.median(diffs))


def _compute_min_interval_samples(config: VerticalGRFConfig, sample_rate_hz: Optional[float]) -> int:
    if sample_rate_hz is None:
        # Fall back to a conservative default of 50 samples (~0.5 s at 100 Hz)
        return max(1, int(round(config.min_interval_s * 100)))
    return max(1, int(round(config.min_interval_s * sample_rate_hz)))


def _threshold_contact(signal: np.ndarray, config: VerticalGRFConfig) -> np.ndarray:
    if signal.size == 0:
        return signal.astype(bool)
    smoothed = _smooth(signal, config.smoothing_window)
    return smoothed > config.threshold


def _smooth(signal: np.ndarray, window: int) -> np.ndarray:
    if signal.size == 0:
        return signal
    if window <= 1:
        return signal
    window = int(window)
    window = max(1, window)
    kernel = np.ones(window, dtype=float) / window
    padded = np.pad(signal, (window // 2, window - 1 - window // 2), mode="edge")
    smoothed = np.convolve(padded, kernel, mode="valid")
    return smoothed.astype(float, copy=False)


def _detect_events_from_contact(contact: np.ndarray, transition: int, min_interval: int) -> np.ndarray:
    # transition +1 => swing->stance (heel strike); -1 => stance->swing (toe-off)
    contact_int = contact.astype(int, copy=False)
    diffs = np.diff(contact_int)
    idx = np.flatnonzero(diffs == transition) + 1
    if idx.size == 0:
        return idx
    filtered = [int(idx[0])]
    for current in idx[1:]:
        if current - filtered[-1] >= min_interval:
            filtered.append(int(current))
    return np.asarray(filtered, dtype=int)


__all__ = [
    "VerticalGRFConfig",
    "VerticalGRFEvents",
    "detect_vertical_grf_events",
]
