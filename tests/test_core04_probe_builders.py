"""Structure and pure-function checks for the CORE-04 pilot builders (no data is read).

The probe and sheet steps live in separate files so that sheet edits never change the
builder hash recorded inside a probe output."""
import ast
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
PAIRS = [("contributor_tools/probe_core04_um21.py", "contributor_tools/review_core04_um21_pilot.py"),
         ("contributor_tools/probe_core04_gt23.py", "contributor_tools/review_core04_gt23_pilot.py"),
         ("contributor_tools/probe_core04_gt24.py", "contributor_tools/review_core04_gt24_pilot.py"),
         ("contributor_tools/probe_core04_gt21.py", "contributor_tools/review_core04_gt21_pilot.py")]
PROBE_ONLY = {"run_probe", "probe_recording", "condition_record", "condition_legs", "load_trial", "participant_mass", "summarize",
              "read_recording", "process_recording", "ipsi_force", "leg_record"}
SHEET_ONLY = {"build_sheet", "fig_grid", "fig_tests", "fig_heading", "fig_half_cycle", "fig_readme", "to_rule_b"}


def _defs(path):
    return {n.name for n in ast.parse((ROOT / path).read_text()).body
            if isinstance(n, (ast.FunctionDef, ast.ClassDef))}


@pytest.mark.parametrize("probe,review", PAIRS)
def test_probe_and_sheet_steps_are_in_separate_files(probe, review):
    p, r = _defs(probe), _defs(review)
    assert "run_probe" in p and "build_sheet" in r
    assert not (p & SHEET_ONLY), p & SHEET_ONLY
    assert not (r & PROBE_ONLY), r & PROBE_ONLY


def test_stride_axis_angle_flags_reversed_axes_and_skips_missing_markers():
    from contributor_tools.probe_core04_gt23 import stride_axis_angle
    n = 50
    heel = np.zeros((n, 3))
    toe = np.tile([0.2, 0.0, 0.03], (n, 1))  # foot points along +X with a small toe-out
    facing = np.array([1.0, 0.0, 0.0])
    ang = stride_axis_angle(heel, toe, facing)
    assert ang is not None and abs(ang) < 15
    assert abs(stride_axis_angle(heel, toe, -facing)) > 90  # pelvis markers swapped
    assert stride_axis_angle(np.full((n, 3), np.nan), toe, facing) is None


def _gt21_rec(on_mask, n=200):
    """Synthetic treadmill recording for one leg: the named plate carries `on_mask` (labelled synthetic)."""
    f = np.zeros((n, 3))
    f[on_mask, 1] = 700.0
    c = np.zeros((n, 3))
    return {'plates': {'Treadmill_R': (f, c)}}


def test_gt21_stance_capture_rule():
    from contributor_tools.probe_core04_gt21 import ipsi_force
    n = 200
    stance = np.zeros(n, bool); stance[:120] = True
    assert ipsi_force(_gt21_rec(stance), 'right', 'treadmill', 0, n - 1)[2] == 'named plate'
    tail = stance.copy(); tail[180:] = True  # next stance starting before the next source heel strike
    assert ipsi_force(_gt21_rec(tail), 'right', 'treadmill', 0, n - 1)[2] == 'named plate'
    gap = stance.copy(); gap[60:80] = False  # a gap inside stance: not one block
    assert ipsi_force(_gt21_rec(gap), 'right', 'treadmill', 0, n - 1)[2].startswith('stance not captured')
    late = np.zeros(n, bool); late[30:150] = True  # starts after 5 % of the stride
    assert ipsi_force(_gt21_rec(late), 'right', 'treadmill', 0, n - 1)[2].startswith('stance not captured')
    mid = stance.copy(); mid[150:160] = True  # a second block that does not run to the end
    assert ipsi_force(_gt21_rec(mid), 'right', 'treadmill', 0, n - 1)[2].startswith('stance not captured')
    f, c, why = ipsi_force(_gt21_rec(gap), 'right', 'treadmill', 0, n - 1)
    assert np.isnan(f).all() and np.isnan(c).all()  # withheld, not zero-filled


@pytest.mark.parametrize("mode,rise,expected", [
    ("ramp", 0.15, "incline"), ("ramp", -0.15, "decline"), ("ramp", 0.03, None),
    ("stair", 0.40, "stair ascent"), ("stair", -0.40, "stair descent"), ("stair", 0.10, None),
    ("levelground", 0.01, "level overground"), ("levelground", 0.08, None)])
def test_gt21_task_from_pelvis_rise_over_run(mode, rise, expected):
    from contributor_tools.probe_core04_gt21 import classify
    n = 200
    t = np.linspace(0, 1, n)[:, None]
    run = 1.2  # m of progression along lab -Z (labelled synthetic straight path)
    rear = np.hstack([np.zeros((n, 1)), 0.95 + rise * run * t, -run * t])
    front = rear + np.array([0.0, 0.0, -0.15])
    cls, why, slope = classify({'front': front, 'rear': rear}, mode, 0, n - 1)
    assert cls == expected, (cls, why, slope)
    if slope is not None:
        assert abs(slope - rise) < 0.02
