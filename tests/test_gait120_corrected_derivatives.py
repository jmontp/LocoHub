"""Analytic synthetic raw-clock fixtures; no actual scientific data opened."""
import json
import math
from pathlib import Path
import pytest
from contributor_tools import correct_gait120_unshifted_derivatives as producer
from contributor_tools import audit_gait120_corrected_derivatives as reviewer
from contributor_tools import run_gait120_corrected_full as runner


def fixture():
    import pyarrow as pa
    times=[i/9 for i in range(10)];grid=[i/149 for i in range(150)]
    raw={'time':times,'pelvis_tilt':[t*.1*180/math.pi for t in times]}
    for leg in ('r','l'):
        for joint,rate,sign in [('hip_flexion',.2,1),('knee_angle',.3,-1),('ankle_angle',.4,1)]:raw[joint+'_'+leg]=[t*rate*sign*180/math.pi for t in times]
    values={'subject':['G120_S001']*150,'observation_id':['synthetic:right']*150,'source_start_time_s':[0.]*150,'source_end_time_s':[1.]*150,'subject_metadata':[json.dumps({'weight_kg':80.,'height_m':1.7})]*150,'task_info':['{}']*150,'unrelated':[-0.,None]+[2.]*148,'grf_vertical_ipsi_BW':[float('nan')]*150,'pelvis_sagittal_angle_rad':[t*.1 for t in grid]}
    for side in ('ipsi','contra'):
        for joint,rate in [('hip_flexion',.2),('knee_flexion',.3),('ankle_dorsiflexion',.4)]:values[f'{joint}_angle_{side}_rad']=[t*rate for t in grid]
        for segment,rate in [('thigh',.3),('shank',0.),('foot',.4)]:values[f'{segment}_sagittal_angle_{side}_rad']=[t*rate for t in grid]
    for name in producer.PREVIOUS:values[name]=[999.]*150
    return pa.table(values),raw


def test_corrected_nineteen_derivatives_and_prior_values():
    before,raw=fixture();after=producer.transform_table(before)
    assert after['hip_flexion_velocity_ipsi_rad_s'][0].as_py()==pytest.approx(.2)
    assert after['hip_flexion_acceleration_ipsi_rad_s2'][0].as_py()==pytest.approx(0.)
    assert after['pelvis_sagittal_velocity_rad_s'][0].as_py()==pytest.approx(.1)
    assert after['thigh_sagittal_velocity_ipsi_rad_s'].null_count==150
    assert after['derived_planar_thigh_sagittal_velocity_ipsi_rad_s'][0].as_py()==pytest.approx(.3)
    assert after['derived_previous_discontinuity_policy_hip_flexion_velocity_ipsi_rad_s'][0].as_py()==999.
    checks=reviewer.verify_tables(before,after,raw,{'weight_kg':80.,'height_m':1.7})
    assert len(checks)==25 and all(c['finite_checked']==150 for c in checks.values())


def test_persisted_independent_readback_and_value_corruption(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    before,raw=fixture();after=producer.transform_table(before);p=tmp_path/'synthetic.parquet';pq.write_table(after,p);read=pq.ParquetFile(p).read(use_threads=False)
    reviewer.verify_tables(before,read,raw,{'weight_kg':80.,'height_m':1.7})
    name='ankle_dorsiflexion_velocity_contra_rad_s';values=read[name].to_pylist();values[75]+=1.;bad=read.set_column(read.schema.get_field_index(name),read.schema.field(name),pa.array(values))
    with pytest.raises(ValueError,match='Independent value'):reviewer.verify_tables(before,bad,raw,{'weight_kg':80.,'height_m':1.7})


def test_unrelated_signed_zero_and_alias_metadata_corruption():
    import pyarrow as pa
    before,raw=fixture();after=producer.transform_table(before);name='unrelated';values=after[name].to_pylist();values[0]=0.;bad=after.set_column(after.schema.get_field_index(name),after.schema.field(name),pa.array(values))
    with pytest.raises(ValueError,match='Unrelated bits'):reviewer.verify_tables(before,bad,raw,{'weight_kg':80.,'height_m':1.7})
    alias=next(iter(producer.PREVIOUS.values()));f=after.schema.field(alias).with_metadata({b'wrong':b'unit'});bad=after.set_column(after.schema.get_field_index(alias),f,after[alias])
    with pytest.raises(ValueError,match='alias metadata'):reviewer.verify_tables(before,bad,raw,{'weight_kg':80.,'height_m':1.7})


def test_partial_source_clock_and_rows_rejected():
    before,raw=fixture()
    with pytest.raises(ValueError,match='Complete'):producer.transform_table(before.slice(0,149))
    short={k:v[:5] for k,v in raw.items()}
    with pytest.raises(ValueError,match='Complete original'):reviewer.expected_from_raw(short,0.,1.)


def test_partial_actual_baseline_rejected(tmp_path,monkeypatch):
    original=tmp_path/'original.json';original.write_text(json.dumps({'output_root':str(tmp_path)}));(tmp_path/'summary.json').write_text(json.dumps({'status':'stopped_incomplete','scientific_approval':False}))
    monkeypatch.setattr(runner,'verify',lambda b:None)
    with pytest.raises(ValueError,match='Completed baseline'):runner.admit({'bindings':{},'original_plan':str(original),'original_plan_sha256':'a'*64},'b'*64)


def test_original_endpoint_duration_controls_derivative():
    import pyarrow as pa
    before,raw=fixture();name='source_end_time_s';before=before.set_column(before.schema.get_field_index(name),before.schema.field(name),pa.array([2.]*150));after=producer.transform_table(before)
    assert after['hip_flexion_velocity_ipsi_rad_s'][0].as_py()==pytest.approx(.1)


def test_correction_cannot_be_applied_twice():
    before,_=fixture()
    with pytest.raises(ValueError):producer.transform_table(producer.transform_table(before))


def test_unshifted_jump_is_retained_in_corrected_derivatives():
    import pyarrow as pa
    before,raw=fixture();grid=[i/149 for i in range(150)];raw={'time':grid,'pelvis_tilt':[t*.1*180/math.pi for t in grid]}
    for leg in ('r','l'):
        for native,rate,sign in [('hip_flexion',.2,1),('knee_angle',.3,-1),('ankle_angle',.4,1)]:raw[native+'_'+leg]=[t*rate*sign*180/math.pi for t in grid]
    hip=[t*.2+(2. if i>=75 else 0.) for i,t in enumerate(grid)];raw['hip_flexion_r']=[v*180/math.pi for v in hip]
    updates={'hip_flexion_angle_ipsi_rad':hip,'thigh_sagittal_angle_ipsi_rad':[h+t*.1 for h,t in zip(hip,grid)],'shank_sagittal_angle_ipsi_rad':[h-t*.2 for h,t in zip(hip,grid)],'foot_sagittal_angle_ipsi_rad':[h+t*.2 for h,t in zip(hip,grid)]}
    for name,values in updates.items():before=before.set_column(before.schema.get_field_index(name),before.schema.field(name),pa.array(values))
    after=producer.transform_table(before)
    assert after['hip_flexion_velocity_ipsi_rad_s'][74].as_py()==pytest.approx(149.2)
    reviewer.verify_tables(before,after,raw,{'weight_kg':80.,'height_m':1.7})


def replace(table,name,values):
    import pyarrow as pa
    return table.set_column(table.schema.get_field_index(name),table.schema.field(name),pa.array(values,type=table.schema.field(name).type))


def test_duration_and_extra_rows_corruption(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    before,raw=fixture();after=producer.transform_table(before)
    bad=replace(before,'source_end_time_s',[2.]*150)
    with pytest.raises(ValueError,match='Complete original'):reviewer.verify_tables(bad,producer.transform_table(bad),raw,{'weight_kg':80.,'height_m':1.7})
    for n in (149,151):
        bad=after.slice(0,n) if n<150 else pa.concat_tables([after,after.slice(0,1)])
        with pytest.raises(ValueError,match='Complete150'):reviewer.verify_tables(before,bad,raw,{})
        path=tmp_path/f'{n}.parquet';pq.write_table(bad,path)
        with pytest.raises(ValueError,match='complete phase'):producer.read_observation(path)


def test_partial_contra_is_missing_not_passing():
    before,raw=fixture();del raw['ankle_angle_l']
    expected,segments=reviewer.expected_from_raw(raw,0.,1.)
    assert all(math.isnan(x) for x in expected['hip_flexion_velocity_contra_rad_s'])
    with pytest.raises(ValueError):reviewer.verify_tables(before,producer.transform_table(before),raw,{'weight_kg':80.,'height_m':1.7})
    for name in before.column_names:
        if name.endswith('_angle_contra_rad'):before=replace(before,name,[math.nan]*150)
    after=producer.transform_table(before)
    checks=reviewer.verify_tables(before,after,raw,{'weight_kg':80.,'height_m':1.7})
    assert checks['hip_flexion_velocity_contra_rad_s']['finite_checked']==0
    assert checks['hip_flexion_velocity_contra_rad_s']['assessment']!='passed'


def test_previous_alias_signed_zero_and_unrelated_force_corruption():
    before,raw=fixture();name='hip_flexion_velocity_ipsi_rad_s';before=replace(before,name,[-0.]+[999.]*149);after=producer.transform_table(before)
    alias=producer.PREVIOUS[name];bad=replace(after,alias,[0.]+[999.]*149)
    with pytest.raises(ValueError,match='Previous derivative not preserved'):reviewer.verify_tables(before,bad,raw,{})
    bad=replace(after,'grf_vertical_ipsi_BW',[0.]+[math.nan]*149)
    with pytest.raises(ValueError,match='Unrelated bits'):reviewer.verify_tables(before,bad,raw,{})


def test_missing_derivative_cannot_pass():
    before,raw=fixture();after=producer.transform_table(before);name='hip_flexion_velocity_ipsi_rad_s'
    with pytest.raises(ValueError):reviewer.verify_tables(before,replace(after,name,[math.nan]*150),raw,{})
    with pytest.raises(ValueError):reviewer.verify_tables(before,after.drop([name]),raw,{})


def test_reader_rejects_decoded_size_before_loading(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    path=tmp_path/'synthetic_large.parquet';pq.write_table(pa.table({'large':['x'*60000]*150}),path,use_dictionary=False,compression='zstd')
    assert path.stat().st_size<8*1024**2
    with pytest.raises(MemoryError,match='Decoded'):producer.read_observation(path)


@pytest.mark.parametrize('mutation',['report_plan','manifest_plan','relative','original_receipt','status','scientific_approval'])
def test_resume_rejects_receipt_plan_and_manifest_identity(tmp_path,mutation):
    folder=tmp_path/'recordings'/'subject'/'walk';folder.mkdir(parents=True)
    plan={'output_root':str(tmp_path)};plan_path=tmp_path/'plan.json';plan_path.write_text(json.dumps(plan));sha=runner.digest(plan_path)
    admitted={'relative':'subject/walk.mot','source':'bound'}
    report={'plan_sha256':sha};manifest={'plan_sha256':sha,'status':'corrected_unshifted_derivatives_export_unreviewed','scientific_approval':False,'relative':'subject/walk.mot','original_receipt':admitted}
    if mutation=='report_plan':report['plan_sha256']='0'*64
    elif mutation=='manifest_plan':manifest['plan_sha256']='0'*64
    else:manifest[mutation]='corrupted'
    (folder/'source_readback.json').write_text(json.dumps(report));(folder/'correction_manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='plan binding|Manifest source identity'):runner.completed(plan,'subject/walk.mot',admitted)
