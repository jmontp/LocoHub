"""Synthetic normalization fixtures; numerical cases are coordinator scheduled."""
import ast
import json
from pathlib import Path
import pytest
from contributor_tools import prepare_gt25_ankle_fix as ankle
from contributor_tools import prepare_gt25_normalization_v4 as tool

ROOT=Path(__file__).resolve().parents[1]
V3=ankle.patch_converter((ROOT/ankle.ADAPTER).read_text())
AUDIT3=ankle.patch_audit((ROOT/'contributor_tools/audit_gt25_streaming_transfer.py').read_text())


def test_only_mass_lookup_and_stride_functions_change():
    funcs=lambda s:{n.name:ast.dump(n) for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)}
    a,b=funcs(V3),funcs(tool.patch_converter(V3))
    assert {k for k in a if a[k]!=b[k]}=={'process_stride','get_subject_mass'}
    assert len(tool.source_aliases())==18
    assert not any('_Nm' in c for c in tool.source_aliases() if 'interaction' in c)


def test_independent_source_mass_and_no_interaction_division():
    source=tool.patch_audit(AUDIT3)
    assert "source_mass_with_exo_kg':float(match[2])" in source
    assert "participant_mass_kg':mass" in source
    assert "resample(exo)*(-1/mass)" not in source
    assert 'source_Nm_per_kg_denominator_unverified' in source
    ast.parse(source)


@pytest.mark.parametrize('side',['l','r'])
@pytest.mark.parametrize('available',[True,False])
def test_participant_bw_source_moments_not_double_divided_and_unknown_assistance(side,available):
    import numpy as np
    import pandas as pd
    def module(source):
        names={'get_subject_mass','process_stride','interpolate_to_phase','compute_velocity_from_angle','compute_acceleration_from_velocity'}
        nodes=[n for n in ast.parse(source).body if (isinstance(n,ast.FunctionDef) and n.name in names) or (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SUBJECT_MASS' for t in n.targets))]
        tree=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),*nodes],type_ignores=[])
        ns={'np':np,'pd':pd,'json':json,'NUM_POINTS':150,'MIN_STRIDE_SAMPLES':100,'MAX_STRIDE_SAMPLES':600}
        exec(compile(ast.fix_missing_locations(tree),'synthetic only','exec'),ns)
        return ns
    new=module(tool.patch_converter(V3)); old=module(V3)
    assert new['get_subject_mass']('BT07')==73.95
    assert old['get_subject_mass']('BT07')==81.23
    t=np.linspace(0,1,101);frames={}
    kinds=['angle_filt','moment_filt','grf','insole_sim']+(['moment_filt_bio','exo'] if available else [])
    for kind in kinds:
        values={'time':t}
        for leg,offset in [('l',1.),('r',2.)]:
            if kind=='angle_filt':
                for joint in ('hip_flexion','knee_angle','ankle_angle'):values[f'{joint}_{leg}']=offset+30*t*t
            elif kind.startswith('moment'):
                for joint in ('hip_flexion','knee_angle','ankle_angle'):values[f'{joint}_{leg}_moment']=np.full(101,offset*2.5)
                values[f'ankle_angle_{leg}_moment'][35]=np.nan
            elif kind=='grf':
                for axis in ('x','y','z'):values[f'fp_{leg}_force_{axis}']=np.full(101,offset*500)
            elif kind=='exo':
                for joint in ('hip_angle','knee_angle'):values[f'{joint}_{leg}_torque_interaction']=np.full(101,offset*7)
            else:
                for axis in ('x','z'):values[f'insole_{leg}_cop_{axis}']=np.full(101,offset/100)
        frames[kind]=pd.DataFrame(values)
    args=dict(data=frames,start_idx=0,end_idx=100,subject_id='BT07',subject_mass=73.95,task='sit_to_stand',task_id='sit_to_stand',task_info={'incline_deg':0.},step_num=0,leg_side=side,model_variant='0task',skip_segment_angles=True,source_recording_id='synthetic')
    after=new['process_stride'](**args);before=old['process_stride'](**{**args,'subject_mass':81.23})
    for role,leg in [('ipsi',side),('contra','r' if side=='l' else 'l')]:
        offset=1 if leg=='l' else 2
        np.testing.assert_allclose(after[f'grf_vertical_{role}_BW'],offset*500/(73.95*9.81))
        np.testing.assert_allclose(after[f'source_grf_global_y_{role}_N'],offset*500)
        np.testing.assert_allclose(after[f'source_hip_flexion_moment_{role}_Nm_kg'],offset*2.5)
        for joint in ('hip_flexion','knee_flexion','ankle_dorsiflexion'):
            for q in ('moment','biological_moment','assistance_moment'):assert after[f'{joint}_{q}_{role}_Nm_kg'].isna().all()
        interaction=after[f'source_hip_angle_torque_interaction_{role}_source_units']
        if available:np.testing.assert_allclose(interaction,offset*7)
        else:assert interaction.isna().all()
    for column in before:
        if column in ('task_info','subject_metadata') or ('_moment_' in column and not column.startswith('source_')) or column.startswith('grf_vertical_'):continue
        pd.testing.assert_series_equal(before[column],after[column],check_exact=True)
    metadata=json.loads(after.subject_metadata.iloc[0])
    assert metadata['weight_kg']==73.95 and metadata['mass_with_worn_exo_kg']==81.23
    assert json.loads(after.task_info.iloc[0])['source_interaction_torque_units'].startswith('unknown;')
    if side=='l':
        ns={};exec(compile(tool.patch_audit(AUDIT3),'independent raw oracle','exec'),ns)
        def read(kind,column,optional=False):return None if kind not in frames and optional else frames[kind][column].to_numpy()
        expected=ns['expected_values'](read,t,73.95,'sit_to_stand')
        assert len(expected)==92
        ns['compare_values'](after,expected)
