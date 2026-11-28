import importlib.util
from pathlib import Path
import numpy as np
import pytest

path=Path(__file__).resolve().parents[1]/'contributor_tools/audit_probes/2026_10_20/check_gt21_events_and_terrain.py'
spec=importlib.util.spec_from_file_location('gt21_event_terrain',path)
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)


def test_monotone_source_cycle_has_two_real_resets():
    assert probe.phase_issues(np.array([99.,0.,30.,60.,99.,0.]),1,5)==[]


@pytest.mark.parametrize('index,value,issue',[
    (3,20.,'source_phase_reversal'),
    (2,0.,'extra_zero_phase_samples'),
    (3,np.nan,'nonfinite_source_phase'),
    (4,101.,'source_phase_outside_0_100'),
    (0,np.nan,'endpoints_not_source_resets'),
    (5,10.,'endpoints_not_source_resets'),
])
def test_source_event_problems_are_reported(index,value,issue):
    phase=np.array([99.,0.,30.,60.,99.,0.]);phase[index]=value
    assert issue in probe.phase_issues(phase,1,5)


def test_terrain_transitions_are_not_assumed_steady_ascent():
    assert probe.terrain_task('rampdescent')=='decline_walking'
    assert probe.terrain_task('stairdescent')=='stair_descent'
    assert probe.terrain_task('walk-rampascent')=='transition'
    with pytest.raises(ValueError):probe.terrain_task('unknown')


@pytest.mark.parametrize('metadata,records,expected', [
    ([{'present_and_positive': False}], [{'phase_issues': []}], 'source_terrain_metadata_incomplete'),
    ([{'present_and_positive': True}], [{'phase_issues': ['source_phase_reversal']}], 'source_phase_issues_found'),
    ([{'present_and_positive': True}], [], 'no_completed_outputs_checked'),
    ([{'present_and_positive': True}], [{'phase_issues': []}], 'source_events_and_terrain_checked_unreviewed'),
])
def test_findings_and_empty_output_reviews_are_not_reported_as_success(metadata, records, expected):
    assert probe.review_status({'terrain_metadata': metadata, 'completed_records': records}) == expected
