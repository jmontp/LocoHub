"""README-specific scalar/static checks and coordinator-scheduled small fixtures."""
import ast
import importlib.util
import json
import math
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('gt25_ankle_prepare',ROOT/'contributor_tools/prepare_gt25_ankle_fix.py')
TOOL=importlib.util.module_from_spec(spec);spec.loader.exec_module(TOOL)
SOURCE=(ROOT/TOOL.ADAPTER).read_text()


@pytest.mark.parametrize('side',['ipsi','contra'])
def test_positive_source_plantarflexion_is_negative_dorsiflexion(side):
    tree=ast.parse(TOOL.patch_converter(SOURCE));name=f'ankle_{side}_rad'
    node=next(n for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
    actual=eval(compile(ast.Expression(node.value),'synthetic','eval'),{'resample':lambda x:x,f'ankle_{side}_deg':30.,'deg2rad':math.pi/180})
    assert actual==pytest.approx(-math.pi/6)


def test_only_stride_changes_assistance_and_imu_functions_unchanged():
    before=ast.parse(SOURCE);after=ast.parse(TOOL.patch_converter(SOURCE))
    funcs=lambda t:{n.name:ast.dump(n) for n in t.body if isinstance(n,ast.FunctionDef)}
    a,b=funcs(before),funcs(after)
    assert {k for k in a if a[k]!=b[k]}=={'process_stride'}
    assignment=lambda tree:[ast.dump(n) for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id.startswith('ankle_assist') for t in n.targets)]
    assert assignment(before)==assignment(after)
    assert len(TOOL.aliases())==10


def test_audit_has_own_readme_binding_and_source_alias_reads():
    source=TOOL.patch_audit((ROOT/'contributor_tools/audit_gt25_streaming_transfer.py').read_text())
    assert "('ankle_dorsiflexion','ankle_angle',-1)" in source
    assert TOOL.README_SHA in source
    assert "raw_angle=resample(read('angle_filt',f'ankle_angle_{side}'))*np.pi/180" in source
    assert 'converter.process_stride' not in source


@pytest.mark.parametrize('biological',[True,False])
@pytest.mark.parametrize('side',['l','r'])
def test_numerical_coupling_source_readback_and_exact_other_fields(side,biological):
    import numpy as np
    import pandas as pd
    def module(source):
        names={'process_stride','interpolate_to_phase','compute_velocity_from_angle','compute_acceleration_from_velocity'}
        nodes=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name in names]
        tree=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),*nodes],type_ignores=[])
        ns={'np':np,'pd':pd,'json':json,'NUM_POINTS':150,'MIN_STRIDE_SAMPLES':100,'MAX_STRIDE_SAMPLES':600}
        exec(compile(ast.fix_missing_locations(tree),'isolated synthetic functions','exec'),ns)
        return ns
    original=module(SOURCE);corrected=module(TOOL.patch_converter(SOURCE))
    t=np.linspace(0,1,101);frames={}
    for kind in ['angle_filt','moment_filt','grf','insole_sim']+(['moment_filt_bio'] if biological else []):
        values={'time':t}
        for leg,offset in [('l',1.),('r',3.)]:
            if kind=='angle_filt':
                for joint in ['hip_flexion','knee_angle','ankle_angle']:values[f'{joint}_{leg}']=offset+30*t*t
                values[f'ankle_angle_{leg}'][35]=np.nan
            elif kind.startswith('moment'):
                for joint in ['hip_flexion','knee_angle','ankle_angle']:values[f'{joint}_{leg}_moment']=np.full(101,offset)
            elif kind=='grf':
                for axis in ['x','y','z']:values[f'fp_{leg}_force_{axis}']=np.full(101,offset*100)
            else:
                for axis in ['x','z']:values[f'insole_{leg}_cop_{axis}']=np.full(101,offset/100)
        frames[kind]=pd.DataFrame(values)
    args=dict(data=frames,start_idx=0,end_idx=100,subject_id='BT07',subject_mass=81.23,task='sit_to_stand',task_id='sit_to_stand',task_info={'incline_deg':0.},step_num=0,leg_side=side,model_variant='0task',skip_segment_angles=True,source_recording_id='synthetic')
    before=original['process_stride'](**args);after=corrected['process_stride'](**args)
    changed={f'ankle_dorsiflexion_{quantity}_{role}_{unit}' for role in ['ipsi','contra'] for quantity,unit in [('angle','rad'),('velocity','rad_s'),('acceleration','rad_s2'),('moment','Nm_kg'),('biological_moment','Nm_kg')]}
    for column in before:
        if column=='task_info':
            old=json.loads(before[column][0]);new=json.loads(after[column][0])
            for key,value in TOOL.METADATA.items():assert new.pop(key)==value
            assert old==new
        elif column in changed:np.testing.assert_allclose(after[column],-before[column],rtol=0,atol=0,equal_nan=True)
        else:pd.testing.assert_series_equal(before[column],after[column],check_exact=True)
    for role in ['ipsi','contra']:
        np.testing.assert_allclose(after[f'ankle_dorsiflexion_velocity_{role}_rad_s']*after[f'ankle_dorsiflexion_moment_{role}_Nm_kg'],before[f'ankle_dorsiflexion_velocity_{role}_rad_s']*before[f'ankle_dorsiflexion_moment_{role}_Nm_kg'],rtol=0,atol=0,equal_nan=True)
        assert after[f'ankle_dorsiflexion_assistance_moment_{role}_Nm_kg'].isna().all()
    # Independent audit uses l-reference transfer convention. Test it against
    # source values only for that declared reference, not by swapping columns.
    if side=='l':
        namespace={};exec(compile(TOOL.patch_audit((ROOT/'contributor_tools/audit_gt25_streaming_transfer.py').read_text()),'independent audit','exec'),namespace)
        def read(kind,column,optional=False):return None if kind not in frames and optional else frames[kind][column].to_numpy()
        expected=namespace['expected_values'](read,t,81.23,'sit_to_stand')
        namespace['compare_values'](after,expected)
