"""Bounded synthetic numerical coverage; coordinator admits single-thread execution.

1537 rows, five small generated CSVs, tracked baseline fixture; no real dataset.
"""
import importlib.util
import json
from pathlib import Path
import pytest
from contributor_tools.prepare_gt24_complete_membership import stat_identity
from contributor_tools.stream_gt24_continuous_record import convert_record
from contributor_tools.audit_gt24_streamed_continuous import audit_record
from contributor_tools.preserve_um21_planar_estimates import exact_value

ADAPTER=Path(__file__).parent/'fixtures/gt24_continuous_stream_adapter.py'


def fixture_record(folder,n=1537,origin=8.,step=.005,perturb=True):
    import numpy as np
    import pandas as pd
    folder.mkdir();subject='SYN';i=np.arange(n);t=i*step;clock=origin+t
    # A sub-tolerance first-interval perturbation makes first interval != median.
    if perturb:clock[1]+=2e-10
    angle={'time':clock};velocity={'time':clock};moment={'time':clock};grf={'time':clock};insole={'time':clock}
    for leg in ('l','r'):
        for joint,scale in [('hip_flexion',1.),('knee_angle',2.),('ankle_angle',3.)]:
            angle[joint+'_'+leg]=scale*t*t
            values=np.full(n,np.nan)
            # Right ankle/knee all missing: fallback and second derivative.
            # Left ankle finite only late: earlier missing chunks MUST NOT fallback.
            if leg=='l' and joint=='ankle_angle':values[1200:]=6*t[1200:]
            if joint=='hip_flexion':values=2*t
            velocity[joint+'_'+leg+'_velocity']=values
            moment[joint+'_'+leg+'_moment']=np.full(n,2.)
        for axis in ('x','y','z'):grf[f'fp_{leg}_force_{axis}']=np.zeros(n)
        for axis in ('x','z'):insole[f'insole_{leg}_cop_{axis}']=np.full(n,.02)
    # No first-chunk contact. Right first event in third chunk determines ALL roles.
    grf['fp_r_force_y'][1100:]=50.;grf['fp_l_force_y'][1300:]=50.
    files={}
    for kind,values in [('angle_filt',angle),('velocity',velocity),('moment_filt',moment),('grf',grf),('insole_sim',insole)]:
        path=folder/f'{subject}_{folder.name}_{kind}.csv'
        pd.DataFrame(values).to_csv(path,index=False,na_rep='nan')
        files[kind]=stat_identity(path)
    return {'subject':subject,'recording':folder.name,'folder':str(folder),'phase':'Synthetic','task':'level_walking','task_id':'synthetic','exo_state':'powered','disposition':'canonical_parsed_candidate_requires_source_audit','files':files}


def load_reference():
    spec=importlib.util.spec_from_file_location('synthetic_complete_record_reference',ADAPTER)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module',params=[(8.,.005,True),(.035,.005,True),(8.,1/256,False)],ids=['integer-origin','fractional-origin','exact-uniform-clock'])
def exported(tmp_path_factory,request):
    import pyarrow.parquet as pq
    root=tmp_path_factory.mktemp('gt24-synthetic-streaming');record=fixture_record(root/'synthetic_on',origin=request.param[0],step=request.param[1],perturb=request.param[2])
    reference=load_reference().process_trial_time(Path(record['folder']),record['subject'],record['phase'])
    old=root/'reference.parquet';reference.to_parquet(old,index=False,row_group_size=512)
    new=root/'streamed.parquet';guards=[]
    result=convert_record(record,ADAPTER,new,lambda:guards.append(True))
    assert guards and result['rows']==1537
    return record,old,new,result


def test_exact_complete_record_values_schema_and_null_masks(exported):
    import itertools
    import pyarrow.parquet as pq
    record,old,new,result=exported
    before,after=pq.ParquetFile(old),pq.ParquetFile(new)
    assert before.schema_arrow.equals(after.schema_arrow,check_metadata=True)
    assert before.metadata.num_rows==after.metadata.num_rows==1537
    for a,b in itertools.zip_longest(before.iter_batches(batch_size=512,use_threads=False),after.iter_batches(batch_size=512,use_threads=False)):
        assert a is not None and b is not None
        for index,name in enumerate(before.schema_arrow.names):
            assert a.column(index).is_null().equals(b.column(index).is_null()),name
            assert exact_value(a.column(index).to_pylist(),b.column(index).to_pylist()),name


def test_analytic_derivatives_at_every_chunk_boundary_and_late_reference(exported):
    import numpy as np
    import pyarrow.parquet as pq
    record,old,new,result=exported
    frame=pq.ParquetFile(new).read(use_threads=False).to_pandas(use_threads=False)
    assert frame.reference_side.eq('right').all()
    assert frame.source_end_time_s.eq(frame.source_time_s.iloc[-1]).all()
    metadata=json.loads(frame.task_info.iloc[0])
    assert metadata['ankle_velocity_fallback']=={'ipsi':True,'contra':False}
    assert frame.ankle_dorsiflexion_velocity_contra_rad_s.iloc[:1200].isna().all()
    assert frame.source_ankle_coordinate_velocity_ipsi_rad_s.isna().all()
    # angle=-3*t^2 deg gives a known constant second derivative -6 deg/s^2.
    rows=[510,511,512,513,1022,1023,1024,1025]
    np.testing.assert_allclose(frame.ankle_dorsiflexion_acceleration_ipsi_rad_s2.iloc[rows],-6*np.pi/180,rtol=0,atol=2e-9)
    np.testing.assert_allclose(frame.knee_flexion_acceleration_ipsi_rad_s2.iloc[rows],-4*np.pi/180,rtol=0,atol=2e-9)
    for column in frame:
        if column.startswith(('thigh_','shank_','foot_')):assert frame[column].isna().all()


def test_rate_is_global_first_interval_not_chunk_median(exported):
    import numpy as np
    import pyarrow.parquet as pq
    record,old,new,result=exported
    frame=pq.ParquetFile(new).read(columns=['source_time_s','sampling_rate_hz'],use_threads=False).to_pandas(use_threads=False)
    clock=frame.source_time_s.to_numpy();expected=1/(clock[1]-clock[0])
    rebased=clock-clock[0];steps=np.diff(rebased)
    if result['facts']['gradient_uniform_step_s'] is None:
        assert expected!=1/np.median(np.diff(clock))
        assert not (steps==steps[0]).all()
    else:
        assert (steps==steps[0]).all()
        assert result['facts']['gradient_uniform_step_s']==steps[0]
    assert frame.sampling_rate_hz.eq(expected).all()
    assert result['facts']['sampling_rate_hz']==expected


def test_independent_streamed_source_readback(exported):
    import pyarrow.parquet as pq
    record,old,new,result=exported
    schema=pq.ParquetFile(old).schema_arrow
    metadata={'weight_kg':70.,'weight_basis':'source_model_including_worn_exo','phase':1,'day':1}
    report=audit_record(record,new,metadata,schema,True,lambda:None)
    assert report['rows']==1537
    assert report['status']=='streamed_continuous_source_checked_unreviewed'
    assert len(report['every_output_field_checked'])==len(schema.names)
