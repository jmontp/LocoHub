"""Synthetic tests (hand-computed values) for contributor_tools/common/joint_power.py. No real data."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pyarrow as pa

_p = Path(__file__).resolve().parents[1] / "contributor_tools" / "common" / "joint_power.py"
_s = importlib.util.spec_from_file_location("joint_power", _p)
jp = importlib.util.module_from_spec(_s)
import sys
sys.modules["joint_power"] = jp
_s.loader.exec_module(jp)

SPEC = jp.PowerSpec("p", "m", (("a", 1), ("b", -1)))


def table(held=None):
    n = 4
    cols = {"observation_id": ["o1", "o1", "o2", "o2"], "reference_side": ["left"] * n, "source_recording_id": ["r"] * n,
            "m": [2.0, np.nan, 3.0, -1.0], "a": [1.0, 5.0, np.nan, 0.5], "b": [0.5, 1.0, 1.0, 1.5], "p": [9.0, 9.0, 9.0, 9.0]}
    if held is not None:
        cols["held_signals"] = held
    return pa.table(cols)


def test_power_is_moment_times_signed_velocity_and_missing_when_an_input_is_missing():
    t = jp.recompute(table(), [SPEC])
    p = t.column("p").to_numpy()
    assert p[0] == 2.0 * (1.0 - 0.5)          # 1.0
    assert np.isnan(p[1]) and np.isnan(p[2])  # moment missing; velocity missing
    assert p[3] == -1.0 * (0.5 - 1.5)         # 1.0 (generation: negative moment, negative velocity)


def test_gap_stats_uses_only_rows_where_both_are_finite():
    st = jp.GapStats()
    jp.recompute(table(), [SPEC], st)
    s = st.summary()["p"]
    assert s["rows_both_finite"] == 2 and s["rows_source_finite"] == 4 and s["rows_new_finite"] == 2
    # observation o1: d = 9-1 = 8, new = 1 -> 8 ; observation o2: d = 8, new = 1 -> 8
    assert s["median_nrms"] == 8.0


def test_presence_and_held_rewrite():
    held = ['{"p": "held: sign unsettled"}'] * 2 + ['{}'] * 2
    t = table(held)
    pres = {("o1", "left"): {"p": True}, ("o2", "left"): {"p": False}}
    out = jp.rewrite_held_column(t, ["p"], pres, "missing", json.dumps, lambda r: r.startswith("held: sign"))
    texts = out.column("held_signals").to_pylist()
    assert texts[:2] == ["{}", "{}"]
    assert json.loads(texts[2]) == {"p": "missing"}
    assert jp.adjust_states({"unchecked": ["p", "q"]}, {"p": False}, ["p"], "unchecked", "gone") == {"unchecked": ["q"], "gone": ["p"]}
