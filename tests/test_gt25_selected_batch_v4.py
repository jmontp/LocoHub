import copy
import json
import pytest
from contributor_tools.run_gt25_selected_batch_v4 import classify,identities,prerequisite
from contributor_tools.audit_gt25_selected_coverage import reconcile
from contributor_tools.clarify_gt25_transfer_segments import metadata,apply


def test_selected_bytes_not_all_csv_admission():
    record={'source_files':[{'bytes':63*1024**2}],'selected_bytes_including_readme':63*1024**2,'canonical_task':'level_walking','recording':'normal_walk'}
    assert classify(record)=='regular_selected_worker'
    record['source_files'][0]['bytes']=65*1024**2;record['selected_bytes_including_readme']=65*1024**2
    with pytest.raises(ValueError):classify(record)
    record.update(canonical_task='sit_to_stand',recording='sit_to_stand_test');assert classify(record)=='streaming_transfer_worker'
    record['canonical_task']=None;assert classify(record)=='excluded_unresolved_observation_semantics'


def test_duplicate_or_unsafe_id_rejected():
    with pytest.raises(ValueError):identities([{'subject':'BT01','recording':'x'}]*2)
    with pytest.raises(ValueError):identities([{'subject':'BT01','recording':'../x'}])


def test_coverage_no_omissions_or_pending_success():
    record={'subject':'BT01','recording':'x','route':'regular_selected_worker','source_files':[],'canonical_task':'level_walking','output':'x','status':'converted_unreviewed'}
    plan={'records':[record]};state=copy.deepcopy(plan)
    assert len(reconcile(plan,state))==1
    state['records']=[]
    with pytest.raises(ValueError):reconcile(plan,state)
    state=copy.deepcopy(plan);state['records'][0]['status']='pending'
    with pytest.raises(ValueError):reconcile(plan,state)


def test_actual_pilot_required(tmp_path):
    p=tmp_path/'plan.json';p.write_text(json.dumps({'attempt_root':str(tmp_path/'missing')}))
    with pytest.raises(FileNotFoundError):prerequisite({'pilot_plan':str(p)})


def test_transfer_reference_metadata_exact_scope():
    old=json.dumps({'segment_angle_method':'virtual_IMU_integration_with_converter_initialization','keep':'value'})
    a=json.loads(metadata(old,'sit_to_stand'));b=json.loads(metadata(old,'stand_to_sit'))
    assert a['segment_zero_reference_samples']=='last20' and b['segment_zero_reference_samples']=='first20'
    assert a['keep']=='value' and 'unverified' in a['segment_global_anatomical_orientation']
    with pytest.raises(ValueError):metadata(old,'level_walking')


def test_metadata_successor_preserves_missing_and_numeric_exactly(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    rows=[{'task':'sit_to_stand','task_info':json.dumps({'segment_angle_method':'virtual_IMU_integration_with_converter_initialization'}),'reference_side':'left','observation_type':'transfer','source_recording_id':'gt25:Parsed/BT01/sit_to_stand_x','angle':None,'velocity':float(i)} for i in range(150)]
    old=tmp_path/'old.parquet';new=tmp_path/'new.parquet';pq.write_table(pa.Table.from_pylist(rows),old)
    report=apply(old,new)
    assert report['rows']==150 and report['all_other_fields_masks_metadata_exact'] and not report['anatomical_frame_verified']
    assert pq.ParquetFile(new).read(columns=['angle'],use_threads=False)['angle'].null_count==150
