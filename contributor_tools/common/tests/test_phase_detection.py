from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from contributor_tools.common import phase_detection


def _make_dummy_stride(time_step: float, stance_start: float, stance_duration: float, total_time: float) -> pd.DataFrame:
    time = np.arange(0.0, total_time, time_step)
    grf = np.zeros_like(time)
    stance_mask = (time >= stance_start) & (time < stance_start + stance_duration)
    grf[stance_mask] = 800.0  # Newtons
    return pd.DataFrame({"time_s": time, "grf": grf})


def test_detect_vertical_grf_events_identifies_transitions():
    time_step = 0.01  # 100 Hz
    total_time = 2.0
    ipsi = _make_dummy_stride(time_step, stance_start=0.2, stance_duration=0.4, total_time=total_time)
    contra = _make_dummy_stride(time_step, stance_start=0.7, stance_duration=0.35, total_time=total_time)

    df = pd.DataFrame({
        "time_s": ipsi["time_s"],
        "grf_ipsi": ipsi["grf"],
        "grf_contra": contra["grf"],
    })

    config = phase_detection.VerticalGRFConfig(
        ipsi_col="grf_ipsi",
        contra_col="grf_contra",
        threshold=100.0,
        min_interval_s=0.2,
        smoothing_window=1,
    )

    events = phase_detection.detect_vertical_grf_events(df, config)

    assert events.sample_rate_hz == pytest.approx(100.0)
    assert events.heel_strikes_ipsi.size == 1
    assert events.heel_strikes_contra.size == 1
    assert events.toe_offs_ipsi.size == 1
    assert events.toe_offs_contra.size == 1

    heel_time_ipsi = df.loc[events.heel_strikes_ipsi[0], "time_s"]
    heel_time_contra = df.loc[events.heel_strikes_contra[0], "time_s"]

    assert pytest.approx(heel_time_ipsi, rel=1e-2) == 0.2
    assert pytest.approx(heel_time_contra, rel=1e-2) == 0.7


def test_min_interval_filters_double_peaks():
    time = np.arange(0.0, 1.0, 0.01)
    grf = np.zeros_like(time)
    grf[20:30] = 600
    grf[25:35] = 600  # overlapping contact, should still count as one
    df = pd.DataFrame({
        "time_s": time,
        "ipsi": grf,
        "contra": grf,
    })
    config = phase_detection.VerticalGRFConfig(
        ipsi_col="ipsi",
        contra_col="contra",
        threshold=100,
        min_interval_s=0.3,
        smoothing_window=1,
    )
    events = phase_detection.detect_vertical_grf_events(df, config)
    assert events.heel_strikes_ipsi.size == 1
    assert events.toe_offs_ipsi.size == 1
