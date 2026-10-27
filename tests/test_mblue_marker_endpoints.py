import importlib.util
from pathlib import Path
import numpy as np
import pytest

p=Path(__file__).resolve().parents[1]/'contributor_tools/audit_probes/2026_10_20/check_mblue_marker_endpoints.py'
spec=importlib.util.spec_from_file_location('marker_endpoints',p)
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)


def test_five_point_quadratic_derivative_including_edges():
    clock=np.arange(100)*.004
    np.testing.assert_allclose(probe.five_point_slope(clock,3*clock**2+2*clock+7),6*clock+2,atol=1e-11)


def test_nonuniform_marker_clock_is_rejected():
    clock=np.arange(100)*.004;clock[40]+=.001
    with pytest.raises(ValueError,match='Uniform'):probe.five_point_slope(clock,np.zeros(100))


def test_no_midswing_peak_is_not_invented():
    clock=np.arange(100)*.004
    with pytest.raises(ValueError,match='midswing'):probe.endpoint_from_markers(clock,np.zeros(100),np.zeros(100),5)
