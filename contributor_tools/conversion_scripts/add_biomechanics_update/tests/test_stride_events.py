from __future__ import annotations

import pandas as pd

from contributor_tools.conversion_scripts.add_biomechanics_update.utils import stride_events


def test_detect_events_returns_container_on_empty_df():
    df = pd.DataFrame({
        "time_s": [],
        "grf_vertical_ipsi_N": [],
        "grf_vertical_contra_N": [],
    })
    events = stride_events.detect_events(df)
    assert hasattr(events, "heel_strikes_ipsi")
    assert isinstance(events.heel_strikes_ipsi, list)
    assert events.heel_strikes_ipsi == []
