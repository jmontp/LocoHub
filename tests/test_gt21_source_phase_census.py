import importlib.util
from pathlib import Path
import sys
import numpy as np

folder = Path(__file__).resolve().parents[1]/'contributor_tools/audit_probes/2026_10_20'
sys.path.insert(0, str(folder))
spec = importlib.util.spec_from_file_location('source_phase_census', folder/'check_gt21_all_source_phases.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_raw_phase_census_counts_all_adjacent_pairs():
    phase = np.array([99., 0., 50., 99., 0., 50., 99., 0.])
    result = probe.inspect_phases(np.arange(len(phase))*.01, phase)
    assert result['resets'] == 3
    assert result['pairs'] == 2
    assert result['cycle_issues'] == []


def test_zero_plateau_is_reported_with_exact_source_interval():
    phase = np.array([99., 0., 0., 50., 99., 0.])
    result = probe.inspect_phases(np.arange(len(phase))*.01, phase)
    assert result['cycle_issues'] == [{'start_s': .01, 'end_s': .05, 'start_index': 1,
                                     'end_index': 5, 'issues': ['extra_zero_phase_samples']}]


def test_bad_samples_outside_complete_pairs_are_not_hidden():
    phase = np.array([np.nan, 101., 0., 50.])
    result = probe.inspect_phases(np.arange(len(phase))*.01, phase)
    assert result['pairs'] == 0
    assert result['nonfinite_samples'] == 1
    assert result['out_of_range_samples'] == 1
