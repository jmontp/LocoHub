"""Tiny synthetic ensembles; stdlib-only builder path, no real Parquet reads."""
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('ensemble_preview',ROOT/'contributor_tools/build_ensemble_preview.py')
MODULE=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(MODULE)


def fixture_rows():
    return [{'subject':'S01','source_recording_id':'conditionA','observation_id':'conditionA:'+side,
             'reference_side':side,'task':'level_walking','task_id':'overground_comfortable',
             'observation_type':'ensemble_curve','observation_kind':'ensemble',
             'phase_ipsi':100*i/149,'task_info':json.dumps({'source_grid_samples':101,'export_grid_samples':150}),
             'source_start_time_s':float('nan'),'source_end_time_s':float('nan'),
             'source_ankle_angle_deg':20. if side=='left' else -10.}
            for side in ('left','right') for i in range(150)]


def test_two_legs_are_not_two_subjects_or_strides():
    result=MODULE.preview_from_rows(fixture_rows())
    assert result['subject_count']==1 and result['observation_count']==2
    assert [o['signals']['source_ankle_angle_deg'][0] for o in result['observations']]==[20.,-10.]
    assert not {'cycle_count','stride_count','sd','n'} & result.keys()
    assert all(not {'sd','n'} & o.keys() for o in result['observations'])


def test_missing_source_values_remain_null():
    rows=fixture_rows();rows[17]['source_ankle_angle_deg']=float('nan')
    result=MODULE.preview_from_rows(rows)
    assert result['observations'][0]['signals']['source_ankle_angle_deg'][17] is None
    json.dumps(result,allow_nan=False)


@pytest.mark.parametrize('field,value', [('observation_type','individual_cycle'),('phase_contra',50.),('cycle_duration_s',1.),('time_s',.5)])
def test_reject_mislabeled_or_fabricated_timing(field,value):
    rows=fixture_rows();rows[0][field]=value
    with pytest.raises(ValueError): MODULE.preview_from_rows(rows)


def test_reject_split_identity_and_partial_phase():
    rows=fixture_rows();rows[75]['subject']='S02'
    with pytest.raises(ValueError):MODULE.preview_from_rows(rows)
    with pytest.raises(ValueError):MODULE.preview_from_rows(fixture_rows()[:-1])


def test_metadata_checked_beyond_first_row():
    rows=fixture_rows();rows[149]['task_info']='{}'
    with pytest.raises(ValueError,match='metadata'):MODULE.preview_from_rows(rows)


def test_embedded_json_cannot_close_script():
    rows=fixture_rows()
    for row in rows:row['subject']='</script><script>bad()</script>'
    payload=MODULE.preview_from_rows(rows)
    rendered=MODULE.document(payload,'/* chart fixture */','/* controls fixture */')
    assert '<script>bad()' not in rendered and '\\u003c/script>' in rendered
    assert 'fetch(' not in rendered
