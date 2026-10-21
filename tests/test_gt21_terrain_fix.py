from pathlib import Path
import pandas as pd
import pytest
from contributor_tools.prepare_gt21_terrain_fix import terrain_source, verify_identical

SOURCE = Path(__file__).resolve().parents[1]/'contributor_tools/conversion_scripts/Gtech_2021/convert_gtech_2021_phase_to_parquet.m'


def test_patch_removes_invented_terrain_and_preserves_signal_processing():
    original = SOURCE.read_text()
    patched = terrain_source(original)
    assert 'Unknown direction, assume ascent by default' not in patched
    assert 'stair_height_m = 0.102' not in patched
    for name in ('process_ramp', 'process_stair'):
        start = patched.index('function [rows, trial_count] = '+name+'(')
        end = patched.index('\nfunction ', start+1)
        body = patched[start:end]
        assert 'fallback:true' not in body
        assert 'require_terrain_inputs(trial_data,' in body
    # Every function after trial loading, including interpolation, joint signals,
    # force/COP and identities, must be unchanged by this metadata correction.
    anchor = 'function trial_data = load_trial_data('
    assert original[original.index(anchor):] == patched[patched.index(anchor):patched.index('\nfunction require_terrain_inputs(')]


def test_patch_refuses_unreviewed_source_shape():
    with pytest.raises(ValueError):
        terrain_source(SOURCE.read_text().replace('        processed = false;', '        processed = [];'))


@pytest.mark.parametrize('change', ['signal', 'metadata', 'missing_row'])
def test_preservation_check_rejects_any_changed_output(tmp_path, change):
    original = pd.DataFrame({'observation_id': ['source-cycle']*150, 'task': ['incline_walking']*150,
                             'signal': [i*.01 for i in range(150)]})
    corrected = original.copy()
    if change == 'signal': corrected.loc[4, 'signal'] += .1
    if change == 'metadata': corrected.loc[0, 'task'] = 'decline_walking'
    if change == 'missing_row': corrected = corrected.iloc[:-1]
    a, b = tmp_path/'original.parquet', tmp_path/'corrected.parquet'
    original.to_parquet(a); corrected.to_parquet(b)
    with pytest.raises(AssertionError): verify_identical(a, b)


def test_preservation_check_accepts_exact_values_including_missing(tmp_path):
    frame = pd.DataFrame({'signal': [float('nan'), 1., 2.]})
    a, b = tmp_path/'a.parquet', tmp_path/'b.parquet'
    frame.to_parquet(a); frame.to_parquet(b)
    assert verify_identical(a, b) == 3
