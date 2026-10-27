"""Synthetic fixtures only; never open the actual UM24K arrays."""
import json
import math
import pytest
from contributor_tools import restore_um24k_ensembles as producer
from contributor_tools import audit_um24k_ensembles as reviewer


def source():
    import numpy as np
    grid=np.arange(101,dtype=float)[:,None]+1000*np.arange(10,dtype=float)[None,:]
    return {'exo':{m:{t:grid.copy()+k for t in producer.TASKS} for k,m in enumerate(producer.EXO)},'emg':{m:{c:{t:{'ensemble':grid.copy()+n,'means':np.arange(10,dtype=float)+123.5} for t in producer.TASKS} for c in ('bare','exo')} for n,m in enumerate(producer.MUSCLES)}}


def test_full_source_schema_and_independent_subject_condition():
    data=producer.validate_source(source())
    for condition in ('bare','exo'):
        for n in (101,150):
            table=producer.observation(data,condition,'RA',7,n)
            checks=reviewer.verify_observation(table,data,condition,'RA',7,n)
            assert checks['source_emg_RF_percent_MVC']['finite_checked']==n
            assert table['source_emg_RF_cycle_mean_percent_MVC'][0].as_py()==130.5
            if condition=='bare':assert checks['source_foot_sensor_force_BW']['assessment']=='unavailable_not_passed'
            with pytest.raises(ValueError,match='identity'):reviewer.verify_observation(table,data,condition,'RA',6,n)


def test_nan_gaps_and_missing_observations_not_dropped():
    data=source();data['exo']['kneeAngle']['LW'][:,0]=math.nan;data['exo']['grf']['LW'][40:42,0]=math.nan;data['exo']['grf']['LW'][0,0]=math.nan
    table=producer.observation(data,'exo','LW',0,150)
    checks=reviewer.verify_observation(table,data,'exo','LW',0,150)
    assert checks['source_knee_flexion_angle_deg']['missing_unassessed']==150
    assert math.isnan(table['source_foot_sensor_force_BW'][0].as_py())
    assert math.isnan(table['source_foot_sensor_force_BW'][60].as_py())


def test_source_signed_zero_and_no_torque_sign_guess():
    data=source();data['exo']['torque']['LL'][0,0]=-0.;data['exo']['torque']['LL'][1,0]=-7.
    table=producer.observation(data,'exo','LL',0,101)
    assert table['source_exo_knee_extension_torque_Nm'][1].as_py()==-7.
    reviewer.verify_observation(table,data,'exo','LL',0,101)
    import pyarrow as pa
    name='source_exo_knee_extension_torque_Nm';values=table[name].to_pylist();values[0]=0.
    bad=table.set_column(table.schema.get_field_index(name),name,pa.array(values))
    with pytest.raises(ValueError,match='bits'):reviewer.verify_observation(bad,data,'exo','LL',0,101)


@pytest.mark.parametrize('kind',['shape','extra','inf'])
def test_partial_or_unknown_source_rejected(kind):
    data=source()
    if kind=='shape':data['exo']['grf']['LL']=data['exo']['grf']['LL'][:100]
    elif kind=='extra':data['exo']['other']=data['exo']['grf']
    else:data['exo']['grf']['LL'][3,1]=math.inf
    with pytest.raises(ValueError):producer.validate_source(data)


def test_corrupted_interpolation_and_invented_time_rejected():
    import pyarrow as pa
    data=source();table=producer.observation(data,'exo','SD',0,150);name='source_knee_flexion_angle_deg';values=table[name].to_pylist();values[73]+=1
    bad=table.set_column(table.schema.get_field_index(name),name,pa.array(values))
    with pytest.raises(ValueError,match='Independent'):reviewer.verify_observation(bad,data,'exo','SD',0,150)
    with pytest.raises(ValueError,match='Unexpected columns'):reviewer.verify_observation(table.append_column('time_s',pa.array([0.]*150)),data,'exo','SD',0,150)
    with pytest.raises(ValueError,match='complete'):reviewer.verify_observation(table.slice(0,149),data,'exo','SD',0,150)


def test_persisted_full_scope_independent_mat_representation(tmp_path):
    from scipy.io import savemat
    import pyarrow.parquet as pq
    data=source();mat=tmp_path/'dataset_S1.mat';savemat(mat,data)
    observations=[{'condition':c,'task':t,'column':i+1} for c in ('bare','exo') for t in producer.TASKS for i in range(10)]
    plan={'output_root':str(tmp_path),'source_root':str(tmp_path),'bindings':{str(mat):producer.digest(mat)},'observations':observations,'source_file_dispositions':{'dataset_S2.mat':'synthetic fixture not included'}}
    p=tmp_path/'plan.json';p.write_text(json.dumps(plan))
    for samples,name in ((101,'source_101.parquet'),(150,'phase_150.parquet')):
        writer=None
        try:
            for item in observations:
                table=producer.observation(data,item['condition'],item['task'],item['column']-1,samples)
                if writer is None:writer=pq.ParquetWriter(tmp_path/name,table.schema)
                writer.write_table(table,row_group_size=samples)
        finally:writer.close()
    report=reviewer.audit_output(p)
    assert report['scope']['ensembles']==120 and report['scientific_approval'] is False
    plan['observations'].pop();p.write_text(json.dumps(plan))
    with pytest.raises(ValueError,match='ledger'):reviewer.audit_output(p)
