"""Synthetic numerical fixtures: coordinator executes only in an available slot."""
import ast
import json
from pathlib import Path
import pytest
from contributor_tools.prepare_gt24_continuous_correction import patch,TIME,ROOT


def fixture(state='powered',bad_clock=False):
    import numpy as np
    import pandas as pd
    clock=np.array([10.,10.1,10.3,10.5]);data={}
    angle={'time':clock};velocity={'time':clock};moment={'time':clock};grf={'time':clock};insole={'time':clock}
    for side in ('l','r'):
        for name,slope in [('hip_flexion',1.),('knee_angle',3.),('ankle_angle',2.)]:
            angle[name+'_'+side]=slope*(clock-clock[0]);velocity[name+'_'+side+'_velocity']=np.full(4,np.nan);moment[name+'_'+side+'_moment']=np.full(4,2.)
        for axis in ('x','y','z'):grf[f'fp_{side}_force_{axis}']=np.full(4,10.)
        for axis in ('x','z'):insole[f'insole_{side}_cop_{axis}']=np.full(4,.02)
    for name,values in [('angle_filt',angle),('velocity',velocity),('moment_filt',moment),('grf',grf),('insole_sim',insole)]:data[name]=pd.DataFrame(values)
    if bad_clock:data['moment_filt'].loc[1,'time']+=.01
    tree=ast.parse(patch((ROOT/TIME).read_text()));needed={'_gradient_over_time','_series_or_nan','process_trial_time'}
    module=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in needed],type_ignores=[])
    namespace={'np':np,'pd':pd,'json':json,'Path':Path,'Optional':__import__('typing').Optional,'map_task_name':lambda _:('level_walking','synthetic',{}),'get_collection_phase':lambda *_:1,'get_exo_state':lambda *_:state,'is_day2_trial':lambda _:False,'get_subject_mass':lambda *_:70.,'load_trial_data':lambda *_:data,'_determine_reference_leg':lambda *_:'l'}
    exec(compile(module,'<synthetic continuous fixture>','exec'),namespace)
    return namespace['process_trial_time'],clock


@pytest.mark.parametrize('state',['powered','worn_unpowered','no_exo'])
def test_source_clock_fallback_sign_missing_assistance_and_force_frames(state):
    import numpy as np
    fn,clock=fixture(state);out=fn(Path('/synthetic/trial'),'SYN','Synthetic')
    np.testing.assert_array_equal(out.source_time_s,clock)
    np.testing.assert_array_equal(out.time_s,clock-clock[0])
    np.testing.assert_allclose(out.ankle_dorsiflexion_velocity_ipsi_rad_s,-2*np.pi/180,atol=1e-12)
    np.testing.assert_allclose(out.knee_flexion_velocity_ipsi_rad_s,-3*np.pi/180,atol=1e-12)
    assert out.source_ankle_coordinate_velocity_ipsi_rad_s.isna().all()
    for name in ['ankle_dorsiflexion_assistance_moment_ipsi_Nm_kg','hip_flexion_assistance_moment_ipsi_Nm_kg']:
        assert out[name].eq(0).all() if state=='no_exo' else out[name].isna().all()
    assert out.grf_anterior_ipsi_BW.isna().all() and out.cop_vertical_ipsi_m.isna().all()
    assert out.source_grf_global_x_ipsi_N.eq(10).all()
    assert json.loads(out.task_info.iloc[0])['ankle_velocity_fallback']=={'ipsi':True,'contra':True}


def test_misaligned_source_clock_rejected_before_export():
    fn,_=fixture(bad_clock=True)
    with pytest.raises(ValueError,match='does not align'):fn(Path('/synthetic/trial'),'SYN','Synthetic')
