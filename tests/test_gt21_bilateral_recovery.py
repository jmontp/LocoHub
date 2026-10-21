"""Recovery preserves complete old observations and rejects altered values."""
import numpy as np
import pandas as pd
import pytest
from contributor_tools.prepare_gt21_bilateral_recovery import verify_preserved, bilateral_source


def cycle(identity, side='right'):
    return pd.DataFrame({'observation_id':[identity]*150,'reference_side':[side]*150,
        'source_start_time_s':np.zeros(150),'source_end_time_s':np.ones(150),
        'angle':np.linspace(0,1,150)})


def test_added_cycles_preserve_all_original_values(tmp_path):
    old=cycle('old');new=cycle('new','left')
    old.to_parquet(tmp_path/'old.parquet',index=False)
    pd.concat([new,old],ignore_index=True).to_parquet(tmp_path/'new.parquet',index=False)
    result=verify_preserved(tmp_path/'old.parquet',tmp_path/'new.parquet')
    assert result['preserved_observations']==1 and result['added_observations']==1
    assert result['added_cycles'][0]['reference_side']=='left'


@pytest.mark.parametrize('fault',['value','missing','duplicate','no_recovery'])
def test_bad_recovery_is_rejected(tmp_path,fault):
    old=cycle('old');new=cycle('new','left');frames=[old.copy(),new]
    if fault=='value':frames[0].loc[70,'angle']+=.1
    elif fault=='missing':frames=[new]
    elif fault=='duplicate':frames=[old,old,new]
    elif fault=='no_recovery':frames=[old]
    old.to_parquet(tmp_path/'old.parquet',index=False)
    pd.concat(frames,ignore_index=True).to_parquet(tmp_path/'new.parquet',index=False)
    with pytest.raises(AssertionError):verify_preserved(tmp_path/'old.parquet',tmp_path/'new.parquet')


def test_patch_preserves_signal_processing_body():
    prefix='function rows = extract_and_process_strides(x)\n'
    selection='gtech_determine_first_heel_strike(x);\nextract_and_process_strides_single_leg(x);\nend\n'
    body='function rows = extract_and_process_strides_single_leg(x)\nrows = x;\nend\n'
    result=bilateral_source(prefix+selection+body)
    assert result.endswith(body)
    assert "for reference = {'right','left'}" in result
    with pytest.raises(ValueError):bilateral_source(prefix+body)
