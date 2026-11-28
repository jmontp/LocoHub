import importlib.util
from pathlib import Path
import numpy as np
import pytest

p=Path(__file__).resolve().parents[1]/'contributor_tools/audit_probes/2026_10_20/check_mblue_stair_reference.py'
spec=importlib.util.spec_from_file_location('stair_reference',p)
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)


def test_recover_known_resized_clock_window():
    clock=np.arange(1000)*.004
    normalized=clock[200:301]
    assert probe.original_window(normalized,clock)==[200,300]


def test_bad_clock_geometry_is_not_rounded_into_a_match():
    clock=np.arange(1000)*.004
    normalized=clock[200:301].copy()
    normalized[40]+=.001
    with pytest.raises(ValueError,match='resize'):probe.original_window(normalized,clock)


def test_cubic_resize_preserves_constant_clock_origin_and_center():
    result=probe.resized_uniform_clock(10.,.004,308)
    assert result[50]==pytest.approx(10+307*.004/2,abs=1e-12)
    np.testing.assert_allclose(result+result[::-1],20+307*.004,atol=1e-12)


def test_force_events_follow_source_pre_crossing_sample_and_cleaning():
    force=np.zeros(60);force[3:7]=10;force[15:19]=10;force[40:45]=10
    assert probe.source_events(force,3)=={2,39}
