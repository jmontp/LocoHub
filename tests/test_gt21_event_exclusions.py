"""An omitted opposite-leg cycle must first meet source eligibility rules."""
import importlib.util
from pathlib import Path
import pytest

path = Path(__file__).resolve().parents[1] / 'contributor_tools/audit_probes/2026_10_20/check_gt21_event_coverage.py'
spec = importlib.util.spec_from_file_location('gt21_coverage', path)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

@pytest.mark.parametrize('samples,phase,counts,expected', [
    (5, 99, [100, 100], 'source_cycle_fails_converter_sample_or_phase_rule'),
    (100, 20, [100, 100], 'source_cycle_fails_converter_sample_or_phase_rule'),
    (100, 99, [9, 100], 'insufficient_source_ik_or_id_samples'),
    (100, 99, [100, 9], 'insufficient_source_ik_or_id_samples'),
    (100, 99, [100, 100], 'opposite_reference_leg_not_exported'),
])
def test_opposite_leg_does_not_hide_ineligible_source(samples, phase, counts, expected):
    assert probe.cycle_exclusion([{'exported_sides': {'right'}}], 'left', samples, phase, counts) == expected


def test_missing_and_ambiguous_task_windows():
    window = {'exported_sides': {'right'}}
    assert probe.cycle_exclusion([], 'left', 100, 99, [100, 100]) == 'outside_complete_eligible_task_window'
    assert probe.cycle_exclusion([window, window], 'left', 100, 99, [100, 100]) == 'ambiguous_task_windows'


def test_no_export_is_not_evidence_for_a_leg_policy():
    assert probe.cycle_exclusion([{'exported_sides': set()}], 'left', 100, 99, [100, 100]) == 'requires_further_reconciliation'
