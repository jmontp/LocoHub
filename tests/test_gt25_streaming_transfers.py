"""Synthetic whole-trial oracle comparisons; no scientific GT25 data."""
from dataclasses import replace
import numpy as np
import pandas as pd
import pytest
from contributor_tools import gt25_projected_row_store as spool
from contributor_tools import gt25_streaming_transfers as streamed
from contributor_tools.common.stride_segmentation import SitStandConfig,segment_sit_stand_transfers


def fixture(tmp_path, irregular=False):
    n=1800;t=np.arange(n)*.05
    if irregular:t+=.001*np.sin(np.arange(n)*.1)
    grf=np.full(n,200.);v=np.zeros(n)
    crossings=[101,223,350,481,620,760,900,1043,1200,1400,1600]
    for i,cross in enumerate(crossings):
        grf[cross:]=800. if i%2==0 else 200.
        width=10 if i!=5 else 35
        v[cross-width:cross+width]=70
    data={'angle_filt':pd.DataFrame({'time':t}),
          'grf':pd.DataFrame({'time':t,'fp_l_force_y':grf/2,'fp_r_force_y':grf/2}),
          'velocity':pd.DataFrame({'time':t,**{f'{joint}_{side}_velocity':v for joint in ('hip_flexion','knee_angle') for side in ('l','r')}})}
    stores={}
    for kind,df in data.items():
        csv=tmp_path/(kind+'.csv');df.to_csv(csv,index=False)
        spool.build(csv,tmp_path/kind,list(df),chunk_rows=17);stores[kind]=spool.Store(tmp_path/kind)
    frame=pd.DataFrame({'time_s':t,'grf_vertical_ipsi_N':grf/2,'grf_vertical_contra_N':grf/2,
        **{f'{joint}_velocity_{role}_rad_s':v*np.pi/180 for joint in ('hip_flexion','knee_flexion') for role in ('ipsi','contra')}})
    config=SitStandConfig(grf_vertical_ipsi_col='grf_vertical_ipsi_N',grf_vertical_contra_col='grf_vertical_contra_N',
        velocity_cols=tuple(c for c in frame if 'velocity' in c))
    return stores,frame,config


@pytest.mark.parametrize('chunk,irregular',[(1,False),(17,False),(63,True),(4096,False)])
def test_whole_trial_boundaries_equal_original(tmp_path,chunk,irregular):
    stores,frame,config=fixture(tmp_path,irregular)
    original=segment_sit_stand_transfers(frame,config)
    streamed.segment(stores,tmp_path/'events.sqlite',config,chunk_rows=chunk)
    result=list(streamed.accepted(tmp_path/'events.sqlite'))
    assert len(original)>4
    assert [(s.start_idx,s.end_idx,s.segment_type,s.events['grf_crossing']) for s in original]==[(s['start_idx'],s['end_idx'],s['segment_type'],s['crossing']) for s in result]
    np.testing.assert_allclose([s.duration_s for s in original],[s['duration_s'] for s in result],rtol=0,atol=1e-12)


@pytest.mark.parametrize('kind',['sit_to_stand','stand_to_sit'])
def test_interval_output_and_imu_initialization_equal_full_source(tmp_path,kind):
    from pathlib import Path
    from contributor_tools import run_gt25_streaming_transfer_pilot as adapter
    converter=adapter.load_converter(Path(adapter.ROOT)/adapter.FAMILY/'convert_gtech_2025_da_to_parquet.py')
    n=180;t=np.arange(n)*.005;stores={};frames={}
    for source_kind in adapter.KINDS:
        cols=spool.projection(source_kind,transfer=True)
        frame=pd.DataFrame({'time':t,**{col:np.sin(t*3+index)+index+1 for index,col in enumerate(cols[1:])}})
        frames[source_kind]=frame
        source=tmp_path/(source_kind+'.csv');frame.to_csv(source,index=False)
        spool.build(source,tmp_path/source_kind,cols,chunk_rows=17);stores[source_kind]=spool.Store(tmp_path/source_kind)
    recording='sit_to_stand_1_baseline_short-arm_on';start,end=23,153
    boundary={'start_idx':start,'end_idx':end,'segment_type':kind}
    expected=converter.process_stride(data={k:v for k,v in frames.items() if k!='imu_sim'},start_idx=start,end_idx=end,
        subject_id='BT01',subject_mass=95.33,task=kind,task_id=kind,task_info={'incline_deg':0.},step_num=0,leg_side='l',model_variant='baseline',
        imu_df=frames['imu_sim'],imu_dt=np.mean(np.diff(t)),use_accel_init=True,source_recording_id=f'gt25:Parsed/BT01/{recording}')
    actual=next(adapter.convert_windows(stores,[boundary],converter,'BT01',recording))
    pd.testing.assert_frame_equal(actual,expected,check_exact=False,rtol=1e-10,atol=1e-8)
    assert actual.source_start_sample.iloc[0]==23
    assert actual.step.iloc[0]==actual.observation_id.iloc[0]


@pytest.mark.parametrize('edge',['initial_unknown','short_trial','nan_velocity','bw_units','iqr_disabled','all_nan_grf'])
def test_edge_semantics_against_original(tmp_path,edge):
    stores,frame,config=fixture(tmp_path)
    if edge=='initial_unknown':frame.loc[:80,['grf_vertical_ipsi_N','grf_vertical_contra_N']]=250.
    if edge=='short_trial':frame=frame.iloc[:5].copy()
    if edge=='nan_velocity':frame.loc[98:105,config.velocity_cols[0]]=np.nan
    if edge=='bw_units':frame[['grf_vertical_ipsi_N','grf_vertical_contra_N']]/=1000
    if edge=='iqr_disabled':config=replace(config,use_iqr_filtering=False)
    if edge=='all_nan_grf':frame[['grf_vertical_ipsi_N','grf_vertical_contra_N']]=np.nan
    altered={
        'angle_filt':pd.DataFrame({'time':frame.time_s}),
        'grf':pd.DataFrame({'time':frame.time_s,'fp_l_force_y':frame.grf_vertical_ipsi_N,'fp_r_force_y':frame.grf_vertical_contra_N}),
        'velocity':pd.DataFrame({'time':frame.time_s,**{f'{joint}_{side}_velocity':frame[f'{out}_velocity_{role}_rad_s']*180/np.pi for joint,out in [('hip_flexion','hip_flexion'),('knee_angle','knee_flexion')] for side,role in [('l','ipsi'),('r','contra')]}})}
    stores={}
    for key,df in altered.items():
        p=tmp_path/(key+'edge.csv');df.to_csv(p,index=False)
        spool.build(p,tmp_path/(key+'edge'),list(df));stores[key]=spool.Store(tmp_path/(key+'edge'))
    expected=segment_sit_stand_transfers(frame,config)
    streamed.segment(stores,tmp_path/'edge.sqlite',config,chunk_rows=13)
    actual=list(streamed.accepted(tmp_path/'edge.sqlite'))
    assert [(s.start_idx,s.end_idx,s.segment_type) for s in expected]==[(s['start_idx'],s['end_idx'],s['segment_type']) for s in actual]


def test_missing_velocity_is_not_invented_zero(tmp_path):
    stores,frame,config=fixture(tmp_path)
    stores['velocity'].columns.remove('hip_flexion_l_velocity')
    with pytest.raises(ValueError):streamed.segment(stores,tmp_path/'missing.sqlite',config)
