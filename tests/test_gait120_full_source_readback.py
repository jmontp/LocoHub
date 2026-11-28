"""Synthetic MOT fixtures; no scientific sources or conversion worker loaded."""
from pathlib import Path
import json
import types
import pytest
from contributor_tools import run_gait120_source_checked_full as m


def test_parser_uses_named_columns_and_preserves_source_sign(tmp_path):
    p=tmp_path/'synthetic.mot';p.write_text('name synthetic\nendheader\ntime ignored knee_angle_r\n0 900 -10\n1 800 -20\n')
    assert m.mot_columns(p,['time','knee_angle_r'])=={'time':[0.,1.],'knee_angle_r':[-10.,-20.]}


def test_duplicate_or_nonmonotonic_clock_rejected(tmp_path):
    p=tmp_path/'synthetic.mot';p.write_text('endheader\ntime hip_flexion_r\n1 0\n1 10\n')
    with pytest.raises(ValueError,match='clock'):m.mot_columns(p,['time'])


def test_partial_record_blocks_resume(tmp_path):
    relative='S001/JointAngle/LevelWalking/Trial01/step01.mot';folder=tmp_path/'recordings'/Path(relative).with_suffix('');folder.mkdir(parents=True)
    with pytest.raises(ValueError,match='Partial'):m.completed({'output_root':str(tmp_path)},relative)


def test_rejects_narrow_inventory():
    with pytest.raises(ValueError,match='Full source'):m.scope({'recordings':['S001/JointAngle/LevelWalking/Trial01/step01.mot'],'subjects':['S001'],'unsupported_source_paths':[]})


def test_independent_all_phase_angles_and_no_force_policy(tmp_path,monkeypatch):
    import numpy as np
    import pyarrow as pa
    import pyarrow.parquet as pq
    relative='S001/JointAngle/LevelWalking/Trial01/step01.mot';source=tmp_path/'raw'/relative;source.parent.mkdir(parents=True)
    cols=['time']+[f'{j}_{l}' for l in ('r','l') for j in ('hip_flexion','knee_angle','ankle_angle')]
    source.write_text('endheader\n'+' '.join(cols)+'\n'+' '.join(map(str,[0,10,-20,30,40,-50,60]))+'\n'+' '.join(map(str,[1,20,-30,40,50,-60,70]))+'\n')
    out=tmp_path/'out';folder=out/'recordings'/Path(relative).with_suffix('');folder.mkdir(parents=True)
    identity='gait120:G120_S001/JointAngle/LevelWalking/Trial01/step01.mot'
    info={'source_force_axes':'original_MOT_axes','exo_state':'no_exo','phase_boundary_method':'source_right_heel_strike_boundaries'}
    values={k:[v]*150 for k,v in {'subject':'G120_S001','task':'level_walking','task_id':'LevelWalking','source_recording_id':identity,'observation_id':identity+':right','reference_side':'right','observation_type':'individual_cycle','source_start_sample':0,'source_end_sample':1,'source_start_time_s':0.,'source_end_time_s':1.,'task_info':json.dumps(info)}.items()}
    values['phase_ipsi']=np.linspace(0,100,150)
    values['phase_ipsi_dot']=[100.]*150
    for side,starts in [('ipsi',[10,-20,30]),('contra',[40,-50,60])]:
        for name,start,sign in zip(['hip_flexion','knee_flexion','ankle_dorsiflexion'],starts,[1,-1,1]):
            end=start-10 if name=='knee_flexion' else start+10
            values[f'{name}_angle_{side}_rad']=np.linspace(start,end,150)*sign*np.pi/180
    values['grf_vertical_ipsi_BW']=[float('nan')]*150;values['hip_flexion_moment_ipsi_Nm_kg']=[float('nan')]*150
    target=folder/'phase.parquet';pq.write_table(pa.table(values),target)
    manifest={'status':'converted_unreviewed','scientific_approval':False,'code':{},'sources':{str(source.resolve()):m.digest(source)},'output_sha256':m.digest(target)};(folder/'conversion_manifest.json').write_text(json.dumps(manifest))
    monkeypatch.setattr(m,'load_original',lambda:types.SimpleNamespace(TASKS={'LevelWalking':'level_walking'}))
    plan={'source_root':str(tmp_path/'raw'),'output_root':str(out),'producer_code':{},'scope_limitations':['synthetic']}
    result=m.independent_readback(plan,relative);assert result['rows']==150
    assert result['feature_counts']['hip_flexion_angle_ipsi_rad']['finite_values_checked']==150
    assert result['anthropometry_assessment'].startswith('unassessed')
    values['hip_flexion_angle_contra_rad']=list(values['hip_flexion_angle_contra_rad']);values['hip_flexion_angle_contra_rad'][75]+=1
    pq.write_table(pa.table(values),target);manifest['output_sha256']=m.digest(target);(folder/'conversion_manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='source value mismatch'):m.independent_readback(plan,relative)


@pytest.mark.parametrize('windows,linux,accepted',[(3072,3584,True),(2816,3584,False),(3071,4000,False),(4000,3583,False)])
def test_cap_aware_startup(windows,linux,accepted):
    values={'windows_available_mib':windows,'linux_available_mib':linux}
    if accepted:m.cap_aware_admission(values)
    else:
        with pytest.raises(MemoryError):m.cap_aware_admission(values)


@pytest.mark.parametrize('value',['inf','-inf'])
def test_infinite_selected_source_measurement_rejected(tmp_path,value):
    p=tmp_path/'synthetic.mot';p.write_text('endheader\ntime hip_flexion_r\n0 '+value+'\n1 10\n')
    with pytest.raises(ValueError,match='Infinite source measurement'):m.mot_columns(p,['time','hip_flexion_r'])
