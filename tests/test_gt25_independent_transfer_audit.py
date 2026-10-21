"""Independent audit on synthetic source rows and deliberately corrupted output."""
import sqlite3
import numpy as np
import pandas as pd
import pytest
from contributor_tools import audit_gt25_streaming_transfer as audit
from contributor_tools.common.stride_segmentation import SitStandConfig,segment_sit_stand_transfers


@pytest.mark.parametrize('irregular',[False,True])
def test_sql_run_membership_matches_original_event_oracle(irregular):
    n=1800;t=np.arange(n)*.05
    if irregular:t+=.001*np.sin(np.arange(n)*.1)
    grf=np.full(n,210.);vel=np.zeros(n)
    for i,cross in enumerate([101,223,350,481,620,760,900,1043,1200,1400,1600]):
        grf[cross:]=810. if i%2==0 else 210.
        width=10 if i!=5 else 35;vel[cross-width:cross+width]=70*np.pi/180
    frame=pd.DataFrame({'time_s':t,'l':grf/2,'r':grf/2,'v':vel})
    expected=segment_sit_stand_transfers(frame,SitStandConfig(grf_vertical_ipsi_col='l',grf_vertical_contra_col='r',velocity_cols=('v',)))
    db=sqlite3.connect(':memory:');db.execute('CREATE TABLE raw_event(i INTEGER PRIMARY KEY,t REAL,g REAL,v REAL)')
    db.executemany('INSERT INTO raw_event VALUES(?,?,?,?)',[(i,float(t[i]),float(grf[i]),float(vel[i])) for i in range(n)])
    audit.independent_events(db,n)
    actual=db.execute('SELECT start,end,kind,crossing FROM expected WHERE accepted=1 ORDER BY start').fetchall()
    assert actual==[(s.start_idx,s.end_idx,s.segment_type,s.events['grf_crossing']) for s in expected]


def synthetic_signals():
    times=np.linspace(3,4,151);sources={}
    for kind in ('angle_filt','moment_filt','moment_filt_bio','grf','insole_sim','exo','imu_sim'):
        sources[kind]={c:(np.sin(times+i)+i+1) for i,c in enumerate(audit.columns_for(kind)) if c!='time'}
    def read(kind,column,optional=False):
        if kind not in sources and optional:return None
        return sources[kind][column]
    return times,read


def test_independent_numeric_oracle_matches_original_converter(tmp_path):
    from contributor_tools.run_gt25_streaming_transfer_pilot import load_converter,ROOT,FAMILY
    converter=load_converter(ROOT/FAMILY/'convert_gtech_2025_da_to_parquet.py')
    times,read=synthetic_signals();frames={}
    for kind in ('angle_filt','moment_filt','moment_filt_bio','grf','insole_sim','exo','imu_sim'):
        frames[kind]=pd.DataFrame({'time':times,**{c:read(kind,c) for c in audit.columns_for(kind) if c!='time'}})
    for task in ('sit_to_stand','stand_to_sit'):
        output=converter.process_stride(data={k:v for k,v in frames.items() if k!='imu_sim'},start_idx=0,end_idx=150,subject_id='BT07',subject_mass=81.23,task=task,task_id=task,task_info={},step_num=0,leg_side='l',model_variant='0task',imu_df=frames['imu_sim'],imu_dt=1/150,use_accel_init=True,source_recording_id='synthetic:BT07')
        expected=audit.expected_values(read,times,81.23,task,1/150)
        assert len(audit.compare_values(output,expected))==64
        for column in ['hip_flexion_angle_ipsi_rad','knee_flexion_assistance_moment_ipsi_Nm_kg','foot_sagittal_angle_contra_rad','cop_anterior_ipsi_m']:
            changed=output.copy();changed.loc[40,column]+=.1
            with pytest.raises(AssertionError):audit.compare_values(changed,expected)
        changed=output.copy();changed.loc[40,'grf_anterior_ipsi_BW']=0
        with pytest.raises(ValueError,match='missingness'):audit.compare_values(changed,expected)


def test_raw_csv_projection_ignores_unconsumed_text_and_rejects_clock(tmp_path):
    path=tmp_path/'synthetic.csv';path.write_text('time,x,annotation\n0,3,text\n1,,text\n2,4,text\n')
    db=sqlite3.connect(':memory:');meta=audit.ingest(db,'synthetic',path,['time','x'])
    assert meta['rows']==3
    assert db.execute('SELECT c1 FROM synthetic WHERE i=1').fetchone()[0] is None
    path.write_text('time,x\n1,3\n1,4\n')
    with pytest.raises(ValueError,match='clock'):audit.ingest(db,'bad',path,['time','x'])


def test_threshold_ambiguity_refuses_adoption():
    db=sqlite3.connect(':memory:');db.execute('CREATE TABLE raw_event(i INTEGER PRIMARY KEY,t REAL,g REAL,v REAL)')
    db.executemany('INSERT INTO raw_event VALUES(?,?,?,?)',[(i,i*.05,400.,0.) for i in range(20)])
    with pytest.raises(ValueError,match='ambiguous'):audit.independent_events(db,20)


def test_end_to_end_persisted_synthetic_audit(tmp_path,monkeypatch):
    import json
    import pyarrow as pa
    import pyarrow.parquet as pq
    from contributor_tools.run_gt25_streaming_transfer_pilot import load_converter,ROOT,FAMILY
    from contributor_tools import preserve_mblue_planar_estimates as guards
    checked_storage_paths=[]
    def check_storage(path):
        # Keep the real filesystem prerequisite even while isolating machine
        # capacity thresholds from this small synthetic regression fixture.
        import shutil
        shutil.disk_usage(path)
        checked_storage_paths.append(path)
    monkeypatch.setattr(guards,'headroom',check_storage)
    monkeypatch.setattr(guards,'windows_available_mib',lambda:99999)
    converter=load_converter(ROOT/FAMILY/'convert_gtech_2025_da_to_parquet.py')
    pilot=tmp_path/'pilot';pilot.mkdir();recording='sit_to_stand_1_0task_short-arm_on';subject='BT07'
    n=800;t=np.arange(n)*.05;grf=np.full(n,210.);velocity=np.zeros(n)
    for i,cross in enumerate([101,223,350,481,620,730]):
        grf[cross:]=810. if i%2==0 else 210.;velocity[cross-10:cross+10]=70
    frames={};sources=[];planned=[]
    for kind in ('angle_filt','moment_filt','grf','velocity','insole_sim','moment_filt_bio','exo','imu_sim'):
        cols=audit.columns_for(kind);frame=pd.DataFrame({'time':t,**{c:np.sin(t+i)+i+1 for i,c in enumerate(cols[1:])}})
        if kind=='grf':frame['fp_l_force_y']=grf/2;frame['fp_r_force_y']=grf/2
        if kind=='velocity':
            for c in cols[1:]:frame[c]=velocity
        frames[kind]=frame;path=tmp_path/(kind+'.csv');frame.to_csv(path,index=False)
        sources.append({'source_path':str(path),'source_sha256':audit.digest(path)});planned.append({'path':str(path),'kind':kind})
    f=pd.DataFrame({'time_s':t,'l':grf/2,'r':grf/2,'v':velocity*np.pi/180})
    events=segment_sit_stand_transfers(f,SitStandConfig(grf_vertical_ipsi_col='l',grf_vertical_contra_col='r',velocity_cols=('v',)))
    writer=None
    for number,event in enumerate(events):
        output=converter.process_stride(data={k:v for k,v in frames.items() if k!='imu_sim'},start_idx=event.start_idx,end_idx=event.end_idx,subject_id=subject,subject_mass=81.23,task=event.segment_type,task_id=event.segment_type,task_info={'incline_deg':0.0},step_num=number,leg_side='l',model_variant='0task',imu_df=frames['imu_sim'],imu_dt=.05,use_accel_init=True,source_recording_id=f'gt25:Parsed/{subject}/{recording}')
        table=pa.Table.from_pandas(output,preserve_index=False)
        if writer is None:writer=pq.ParquetWriter(pilot/'phase.parquet',table.schema)
        writer.write_table(table,row_group_size=150)
    writer.close()
    readme=tmp_path/'readme.txt';readme.write_text('BT07: 73.95 kg | 81.23 kg\n')
    plan={'subject':subject,'recording':recording,'sources':planned,'bindings':{str(readme):audit.digest(readme)}}
    (pilot/'plan.json').write_text(json.dumps(plan))
    (pilot/'conversion_summary.json').write_text(json.dumps({'status':'streaming_transfer_converted_unreviewed','plan_sha256':audit.digest(pilot/'plan.json'),'phase_sha256':audit.digest(pilot/'phase.parquet'),'rows':len(events)*150,'observations':len(events),'sources':sources}))
    result=audit.audit(pilot,tmp_path/'audit')
    assert result['observations_checked']==len(events)>0
    assert result['numeric_features_checked']==64
    assert result['scientific_approval'] is False
    assert checked_storage_paths and all(path==tmp_path for path in checked_storage_paths)
