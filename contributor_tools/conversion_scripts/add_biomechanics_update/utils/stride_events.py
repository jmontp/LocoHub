"""Stride event detection utilities leveraging shared vertical GRF logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import pandas as pd

from contributor_tools.common import phase_detection


@dataclass
class StrideEvents:
    """Container for heel-strike and toe-off events in a dataframe chunk."""

    heel_strikes_ipsi: List[int]
    heel_strikes_contra: List[int]
    toe_offs_ipsi: List[int]
    toe_offs_contra: List[int]
    sample_rate_hz: Optional[float]


def detect_events(
    df: pd.DataFrame,
    *,
    ipsi_col: str = "grf_vertical_ipsi_N",
    contra_col: str = "grf_vertical_contra_N",
) -> StrideEvents:
    """Detect stride events using vertical GRF signals.

    Parameters
    ----------
    df:
        Normalized dataframe chunk.
    ipsi_col / contra_col:
        Column names containing ipsilateral and contralateral vertical GRFs in
        Newtons.
    """

    config = phase_detection.VerticalGRFConfig(
        ipsi_col=ipsi_col,
        contra_col=contra_col,
    )
    try:
        events = phase_detection.detect_vertical_grf_events(df, config)
    except KeyError:
        return StrideEvents([], [], [], [], None)
    return StrideEvents(
        heel_strikes_ipsi=events.heel_strikes_ipsi.tolist(),
        heel_strikes_contra=events.heel_strikes_contra.tolist(),
        toe_offs_ipsi=events.toe_offs_ipsi.tolist(),
        toe_offs_contra=events.toe_offs_contra.tolist(),
        sample_rate_hz=events.sample_rate_hz,
    )
