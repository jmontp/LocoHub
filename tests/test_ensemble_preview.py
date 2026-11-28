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


@pytest.mark.parametrize('column,label,unit', [
    ('hip_flexion_angle_ipsi_rad','Hip flexion','rad'),
    ('ankle_dorsiflexion_moment_ipsi_Nm_kg','Ankle dorsiflexion moment','Nm_kg'),
    ('source_LKneeAngleZ_deg','Left knee angle · Z','deg'),
    ('source_RGRFY_N_kg','Right ground force · Y','N_kg')])
def test_human_labels_keep_exact_columns_and_storage_units(column,label,unit):
    signal=MODULE.signal_definition(column)
    assert signal['column']==column and signal['label']==label and signal['unit']==unit
    assert signal['source_component']==column.startswith('source_')


def test_source_labels_do_not_invent_anatomical_axes():
    signal=MODULE.signal_definition('source_LAnkleMomentX_Nm_kg')
    assert signal['reference_side']=='left' and signal['source_axis']=='X'
    assert signal['label']=='Left ankle moment · X'
    assert 'dorsiflexion' not in signal['label']


def test_display_metadata_does_not_change_scientific_values():
    rows=fixture_rows();rows[0]['source_ankle_angle_deg']=12.345
    output=MODULE.preview_from_rows(rows)
    assert output['observations'][0]['signals']['source_ankle_angle_deg'][0]==12.345
    assert output['observation_count']==2 and output['subject_count']==1
