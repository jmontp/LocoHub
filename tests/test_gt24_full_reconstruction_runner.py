"""Pure synthetic scope/admission fixtures; no scientific jobs."""
import copy
from pathlib import Path
import pytest
from contributor_tools import run_gt24_full_reconstruction as r


def pilots():
 return {'status':'four_gt24_raw_audits_source_checked_unreviewed','scientific_approval':False,'full_adoption_allowed':False,'records':[{'case':c,'index':i} for c in ('known','unknown') for i in (0,1)]}


def test_actual_exact_four_pilots_required():
 p=pilots();r.pilot_gate(p)
 for change in ({'status':'four_gt24_raw_audits_partial_unassessed'},{'scientific_approval':True},{'records':p['records'][:3]},{'full_adoption_allowed':True}):
  with pytest.raises(ValueError):r.pilot_gate({**p,**change})


def test_duplicate_pilot_rejected():
 p=pilots();p['records'][-1]=p['records'][0]
 with pytest.raises(ValueError,match='Exact'):r.pilot_gate(p)


def membership():
 jobs=[{'phase':'Phase3','subject':'BT01','parsed_recording':'trial','native_recording':n} for n in ('trial1','trial2')]
 reports=[{**job,'job_index':i,'status':'native_parsed_candidate_rejected','membership_verified':False} for i,job in enumerate(jobs)]
 return {'jobs':jobs},reports


def test_no_match_ambiguity_and_unique_are_distinct():
 m,reports=membership();key=('Phase3','BT01','trial')
 assert r.classify_reports(m,reports)[key]['status']=='no_matching_membership'
 reports[0].update(status='native_parsed_candidate_checked_unreviewed',membership_verified=True)
 assert r.classify_reports(m,reports)[key]['positive_indices']==[0]
 reports[1].update(status='native_parsed_candidate_checked_unreviewed',membership_verified=True)
 assert r.classify_reports(m,reports)[key]['status']=='ambiguous_membership'


def test_missing_candidate_never_resolved_as_unique():
 m,reports=membership()
 with pytest.raises(ValueError,match='All candidate'):r.classify_reports(m,reports[:1])


def test_wrong_identity_or_contradictory_receipt_rejected():
 m,reports=membership();reports[1]['subject']='wrong'
 with pytest.raises(ValueError,match='identity'):r.classify_reports(m,reports)
 m,reports=membership();reports[1]['membership_verified']=True
 with pytest.raises(ValueError,match='contradictory'):r.classify_reports(m,reports)


def test_frozen_binding_never_refreshed():
 old={'source':'original'}
 with pytest.raises(ValueError,match='Conflicting'):r.merge(old,{'source':'changed'})
 assert old=={'source':'original'}


def test_explicit_archetypes_no_default(tmp_path):
 p=tmp_path/'registry.py';p.write_text("TASK_ARCHETYPE_MAP: dict = {'walk': SegmentationArchetype.GAIT, 'stand': SegmentationArchetype.STANDING_ACTION}")
 assert r.archetypes(p)=={'walk':True,'stand':False}
 assert 'unknown' not in r.archetypes(p)


def test_no_run_on_prepare_and_unchanged_hard_limits():
 text=Path(r.__file__).read_text()
 assert '768*1024**2' in text and '3584 if startup else 2048' in text
 assert '2816 if startup else 2048' in text and '5*1024**3' in text
 assert "'full_adoption_allowed':False" in text


def candidate_fixture(tmp_path):
 import json,zipfile
 from contributor_tools.prepare_gt24_complete_membership import stat_identity
 parsed=tmp_path/'parsed.csv';parsed.write_text('time,value\n0,1\n')
 archive=tmp_path/'native.zip'
 with zipfile.ZipFile(archive,'w') as z:z.writestr('trial.csv',parsed.read_bytes())
 with zipfile.ZipFile(archive) as z:
  i=z.getinfo('trial.csv');member={'name':i.filename,'bytes':i.file_size,'compressed_bytes':i.compress_size,'crc32':i.CRC,'header_offset':i.header_offset}
 job={'phase':'Phase3','subject':'BT01','parsed_recording':'trial_on','native_recording':'trial','archive':stat_identity(archive),'tables':[{'kind':'angle_filt','member':member,'parsed':stat_identity(parsed)}]}
 plan=tmp_path/'membership.json';plan.write_text(json.dumps({'bindings':{},'jobs':[job]}))
 report={**{k:job[k] for k in ('phase','subject','parsed_recording','native_recording')},'job_index':0,'plan_sha256':r.digest(plan),'status':'native_parsed_candidate_rejected','membership_verified':False,'scientific_approval':False,'tables':{'angle_filt':{'native':{'full_csv_sha256':r.digest(parsed)},'parsed':{'full_csv_sha256':r.digest(parsed)}}}}
 rp=tmp_path/'report.json';rp.write_text(json.dumps(report));return plan,rp,report


def test_reused_negative_membership_rechecks_both_source_hashes(tmp_path):
 import json
 plan,rp,report=candidate_fixture(tmp_path)
 r.verify_membership_sources(plan,0,rp)
 report['tables']['angle_filt']['native']['full_csv_sha256']='0'*64;rp.write_text(json.dumps(report))
 with pytest.raises(ValueError,match='Native receipt bytes'):r.verify_membership_sources(plan,0,rp)


def test_reused_membership_cannot_drop_tables(tmp_path):
 import json
 plan,rp,report=candidate_fixture(tmp_path);report['tables']={};rp.write_text(json.dumps(report))
 with pytest.raises(ValueError,match='table scope'):r.verify_membership_sources(plan,0,rp)


def test_reused_membership_parsed_change_same_size_and_mtime(tmp_path):
 import os
 plan,rp,report=candidate_fixture(tmp_path);source=tmp_path/'parsed.csv';stat=source.stat()
 source.write_text('time,value\n0,2\n');os.utime(source,ns=(stat.st_atime_ns,stat.st_mtime_ns))
 with pytest.raises(ValueError,match='Parsed receipt bytes'):r.verify_membership_sources(plan,0,rp)


def record_fixture(tmp_path):
 import json
 folder=tmp_path/'record_0';folder.mkdir();source=tmp_path/'source.csv';source.write_text('synthetic')
 reference=folder/'baseline_unreviewed.parquet';reference.write_text('synthetic baseline, not Parquet')
 output=folder/'continuous.parquet';output.write_text('synthetic output, not Parquet')
 plan=tmp_path/'plan.json';plan.write_text('{}');(tmp_path/'admission.json').write_text('{}')
 record={'phase':'Phase3','subject':'BT01','recording':'trial','reference_output':str(reference),'files':{'angle_filt':{'path':str(source)}}}
 common={'scientific_approval':False,'plan_sha256':r.digest(plan),'rows':2}
 for name,status in [('baseline','bounded_parsed_continuous_export_unverified'),('export','participant_normalization_export_unverified'),('audit','participant_normalization_independent_readback_checked_unreviewed')]:
  receipt={**common,'status':status,'output_sha256':r.digest(reference if name=='baseline' else output),'reference_sha256':r.digest(reference),'all_unrelated_values_field_metadata_null_masks_exact':True}
  (folder/(name+'.json')).write_text(json.dumps(receipt))
 raw={**common,'status':'corrected_raw_source_partial_unassessed','output_sha256':r.digest(output),'bound_producer_policy':'gt24_participant_mass_missingness_v2','source_sha256':{'angle_filt':r.digest(source)},**{k:record[k] for k in ('phase','subject','recording')}}
 (tmp_path/'raw_source.json').write_text(json.dumps(raw));return record


def test_checked_record_requires_all_actual_preservation_receipts(tmp_path):
 import json
 record=record_fixture(tmp_path);report,hashes=r.checked_record(tmp_path,record)
 assert report['status']=='corrected_raw_source_partial_unassessed'
 assert str(tmp_path/'record_0/continuous.parquet') in hashes
 path=tmp_path/'record_0/audit.json';j=json.loads(path.read_text());j['all_unrelated_values_field_metadata_null_masks_exact']=False;path.write_text(json.dumps(j))
 with pytest.raises(ValueError,match='Exact preservation'):r.checked_record(tmp_path,record)


@pytest.mark.parametrize('change',[{'bound_producer_policy':'v1'},{'subject':'BT02'},{'rows':1},{'source_sha256':{}}])
def test_checked_record_rejects_wrong_policy_identity_rows_or_source_scope(tmp_path,change):
 import json
 record=record_fixture(tmp_path);path=tmp_path/'raw_source.json';j=json.loads(path.read_text());j.update(change);path.write_text(json.dumps(j))
 with pytest.raises(ValueError):r.checked_record(tmp_path,record)


def test_cleanup_kills_descendants_even_after_leader_exit(monkeypatch):
 calls=[]
 class Child:
  pid=123
  def poll(self):return 0
  def wait(self,timeout):calls.append(('wait',timeout))
 monkeypatch.setattr(r.os,'killpg',lambda pid,sig:calls.append(('kill',pid,sig)))
 r.cleanup_owned(Child());assert calls[0]==('kill',123,r.signal.SIGKILL)


def test_signal_handler_turns_interrupt_into_cleanup_path_and_restores(monkeypatch,tmp_path):
 handlers={sig:object() for sig in (r.signal.SIGTERM,r.signal.SIGINT)};original=handlers.copy()
 monkeypatch.setattr(r.signal,'getsignal',handlers.__getitem__)
 monkeypatch.setattr(r.signal,'signal',lambda sig,fn:handlers.__setitem__(sig,fn))
 def interrupted(*args):handlers[r.signal.SIGTERM](r.signal.SIGTERM,None)
 monkeypatch.setattr(r,'_run',interrupted)
 with pytest.raises(RuntimeError,match='interrupted'):r.run(tmp_path/'plan.json','sha')
 assert handlers==original
