"""Small synthetic ZIP/CSV fixtures; no arrays, source archives or native jobs."""
import copy,gzip,hashlib,zipfile
import pytest
from contributor_tools import preserve_gt24_native_companion as writer
from contributor_tools import audit_gt24_native_companion as audit


def fixture(tmp_path,matched=True):
 data=b'time,value\r\n0,-0\r\n1,NaN\r\n1,\r\n0.5,Inf\r\n';extra=b'time,signal\n9,1\n8,2\n'
 archive=tmp_path/'synthetic.zip'
 with zipfile.ZipFile(archive,'w') as z:z.writestr('Phase/BT01/trial/Joint_Angles_Filt.csv',data);z.writestr('Phase/BT01/trial/Extra.csv',extra)
 with zipfile.ZipFile(archive) as z:members=[{'name':i.filename,'bytes':i.file_size,'compressed_bytes':i.compress_size,'crc32':i.CRC,'header_offset':i.header_offset} for i in z.infolist()]
 stat=archive.stat();cov={'status':'native_not_read_no_candidate','native_rows':None,'unmatched_native_rows':None}
 if matched:cov={'status':'native_projected_source_scanned','native_rows':4,'verified_unique_parsed_intervals':[[1,2]],'unmatched_native_intervals':[[0,0],[3,3]],'unmatched_native_rows':2,'source_tables':{'angle_filt':{'rows':4,'full_csv_sha256':hashlib.sha256(data).hexdigest()}}}
 record={'phase':'synthetic','subject':'synthetic','recording':'trial','source_recording_id':'synthetic:trial','members':members,'archive':{'path':str(archive.resolve()),'bytes':stat.st_size,'mtime_ns':stat.st_mtime_ns},'coverage':cov}
 folder=tmp_path/'output';streams=writer.preserve_record(record,folder)
 return record,folder,{'streams':streams},data


def test_entire_native_bytes_and_boundary_context_preserved(tmp_path):
 record,folder,producer,data=fixture(tmp_path)
 result,bindings=audit.audit_record(record,folder,producer,{'angle_filt':'Joint_Angles_Filt.csv'})
 assert gzip.decompress((folder/producer['streams'][0]['compressed']).read_bytes())==data
 assert result[0]['coverage']['residual_intervals']==[[0,0],[3,3]]
 assert result[0]['coverage']['matched_rows']==2
 assert result[0]['clock_diagnostics']['duplicates']==1 and result[0]['clock_diagnostics']['decreases']==1
 assert result[1]['rows']==2 and result[1]['coverage']['residual_rows']==2
 assert len(bindings)==2


def test_ambiguous_or_unread_native_is_fully_preserved_not_skipped(tmp_path):
 record,folder,producer,data=fixture(tmp_path,False)
 result,_=audit.audit_record(record,folder,producer,{'angle_filt':'Joint_Angles_Filt.csv'})
 assert result[0]['coverage']['residual_intervals']==[[0,3]]
 assert result[0]['coverage']['matched_rows']==0


@pytest.mark.parametrize('defect',['hash','range','residual_count','overlap'])
def test_membership_cannot_hide_rows_without_exact_source_evidence(tmp_path,defect):
 record,folder,producer,data=fixture(tmp_path);cov=record['coverage']
 if defect=='hash':cov['source_tables']['angle_filt']['full_csv_sha256']='0'*64
 elif defect=='range':cov['verified_unique_parsed_intervals']=[[1,8]]
 elif defect=='residual_count':cov['unmatched_native_rows']=1
 else:cov['verified_unique_parsed_intervals']=[[1,2],[2,3]]
 with pytest.raises(ValueError):audit.audit_record(record,folder,producer,{'angle_filt':'Joint_Angles_Filt.csv'})


def test_missing_original_stream_fails_full_record_accounting(tmp_path):
 record,folder,producer,data=fixture(tmp_path);producer['streams'].pop()
 with pytest.raises(ValueError,match='member scope'):audit.audit_record(record,folder,producer,{})


def test_numeric_equivalent_changed_literal_bytes_fail(tmp_path):
 record,folder,producer,data=fixture(tmp_path);stream=producer['streams'][0];path=folder/stream['compressed'];path.write_bytes(gzip.compress(data.replace(b'-0',b'0')));stream['compressed_sha256']=writer.digest(path)
 with pytest.raises(ValueError,match='literal bytes'):audit.audit_record(record,folder,producer,{})


def test_later_output_mutation_detected(tmp_path):
 record,folder,producer,data=fixture(tmp_path);_,bindings=audit.audit_record(record,folder,producer,{'angle_filt':'Joint_Angles_Filt.csv'})
 (folder/producer['streams'][0]['compressed']).write_bytes(b'changed')
 with pytest.raises(ValueError):audit.verify(bindings)


def test_no_clock_column_does_not_invent_timing(tmp_path):
 path=tmp_path/'synthetic.gz';path.write_bytes(gzip.compress(b'label,value\nabc,1\n'))
 rows,info=audit.clock_rows(path)
 assert rows==1 and info['time_column_present'] is False


def test_bad_csv_remains_output_but_readback_not_approved(tmp_path):
 path=tmp_path/'synthetic.gz';path.write_bytes(gzip.compress(b'time,value\n0,1,2\n'))
 with pytest.raises(ValueError,match='row width'):audit.clock_rows(path)
 assert path.exists()


def test_disk_admission_does_not_assume_compression(tmp_path):
 record,folder,producer,data=fixture(tmp_path)
 assert writer.reserve_bytes([record])>sum(m['bytes'] for m in record['members'])


def test_existing_scientific_artifact_never_overwritten(tmp_path):
 record,folder,producer,data=fixture(tmp_path)
 with pytest.raises(FileExistsError):writer.preserve_record(record,folder)


def test_prepare_refuses_incomplete_membership_before_source_io(tmp_path,monkeypatch):
 import json
 monkeypatch.setattr(writer,'BASE',tmp_path)
 plan=tmp_path/'membership.json';plan.write_text(json.dumps({'jobs':[{}]}))
 summary=tmp_path/'coverage.json';summary.write_text(json.dumps({'status':'all_planned_candidate_checks_aggregated_unreviewed','scientific_approval':False}))
 with pytest.raises(ValueError,match='2447'):writer.prepare(plan,summary,tmp_path/'out')
 assert not (tmp_path/'out').exists()


def test_ambiguous_membership_with_zero_unique_intervals_remains_all_residual(tmp_path):
 record,folder,producer,data=fixture(tmp_path)
 record['coverage'].update(verified_unique_parsed_intervals=[],unmatched_native_intervals=[[0,3]],unmatched_native_rows=4)
 results,_=audit.audit_record(record,folder,producer,{'angle_filt':'Joint_Angles_Filt.csv'})
 assert results[0]['coverage']['matched_rows']==0 and results[0]['coverage']['residual_rows']==4


def test_full_plan_low_space_remains_reviewable_but_record_admission_enforced(tmp_path,monkeypatch):
 import json
 from types import SimpleNamespace
 from contributor_tools import prepare_gt24_complete_membership as membership
 monkeypatch.setattr(writer,'BASE',tmp_path)
 members=[{'name':'synthetic.csv','bytes':1024**3,'compressed_bytes':10,'crc32':0,'header_offset':0}]
 records=[{'subject':'synthetic','recording':str(i),'members':members} for i in range(1358)]
 inventory=tmp_path/'inventory.json';inventory.write_text(json.dumps({'phases':[{'phase':'synthetic','archive':{'path':'not_read.zip'},'dynamic_complete_recordings':records,'static_source_tables':[],'excluded_archive_entries':[]}]}))
 plan=tmp_path/'membership.json';plan.write_text(json.dumps({'jobs':[{}]*2447,'bindings':{},'inventory':str(inventory)}))
 summary={'status':'all_planned_candidate_checks_aggregated_unreviewed','scientific_approval':False,'candidate_report_hashes':{},'native_recordings':[{'phase':'synthetic','subject':'synthetic','recording':str(i),'status':'native_not_read_no_candidate','native_rows':None,'unmatched_native_rows':None} for i in range(1358)],'unresolved_parsed_membership':[]}
 sp=tmp_path/'summary.json';sp.write_text(json.dumps(summary))
 # Only completion proof is mocked; this exercises real full-scope plan construction.
 monkeypatch.setattr(membership,'summarize',lambda path:summary)
 monkeypatch.setattr(writer.shutil,'disk_usage',lambda path:SimpleNamespace(free=21*1024**3))
 output=tmp_path/'output';writer.prepare(plan,sp,output)
 actual=json.loads((output/'plan.json').read_text())
 assert len(actual['records'])==1358
 assert actual['disk_admission']['full_scope_fits_worst_case_at_preparation'] is False
 assert {p.name for p in output.iterdir()}=={'plan.json'}
 writer.admit_record_disk(actual['records'][0],output)
 monkeypatch.setattr(writer.shutil,'disk_usage',lambda path:SimpleNamespace(free=5*1024**3))
 with pytest.raises(MemoryError,match='Per-record'):writer.admit_record_disk(actual['records'][0],output)
 assert {p.name for p in output.iterdir()}=={'plan.json'}


def test_actual_membership_summarizer_schema_consumed_without_translation(tmp_path):
 import io,json
 from contributor_tools import prepare_gt24_complete_membership as membership
 from contributor_tools.match_gt24_complete_intervals import ProjectedCSV,compare_membership
 native=b'time,value\n0,10\n1,11\n2,12\n3,13\n';parsed=b'time,value\n1,11\n2,12\n'
 result=compare_membership(ProjectedCSV(io.BytesIO(native),['time','value']),ProjectedCSV(io.BytesIO(parsed),['time','value']))
 inventory=tmp_path/'inventory.json';inventory.write_text(json.dumps({'phases':[{'phase':'synthetic','dynamic_complete_recordings':[{'subject':'subject','recording':'native'}]}]}))
 job={'phase':'synthetic','subject':'subject','native_recording':'native','parsed_recording':'subset'}
 plan=tmp_path/'plan.json';plan.write_text(json.dumps({'bindings':{},'inventory':str(inventory),'jobs':[job],'unresolved_source_membership':[]}))
 reports=tmp_path/'records';reports.mkdir();(reports/'000000.json').write_text(json.dumps({**job,'plan_sha256':writer.digest(plan),'job_index':0,'status':'native_parsed_candidate_checked_unreviewed','membership_verified':True,'tables':{'angle_filt':result},'matched_intervals':result['matched_native_intervals']}))
 summary=membership.summarize(plan);row=summary['native_recordings'][0]
 assert row['verified_unique_parsed_intervals']==[[1,2]] and row['unmatched_native_intervals']==[[0,0],[3,3]]
 mapped=audit.coverage({'coverage':row},'Joint_Angles_Filt.csv',4,hashlib.sha256(native).hexdigest(),membership.TABLES)
 assert mapped['matched_rows']==2 and mapped['residual_rows']==2
