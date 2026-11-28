"""Tiny synthetic metadata/byte fixtures only, no scientific arrays or jobs."""
import json
from pathlib import Path
from types import SimpleNamespace
import signal
import pytest
from contributor_tools import run_gt25_full_restoration_v5 as tool


def full_scope():
 rows=[]
 for route,count in [('regular_selected_worker',450),('streaming_transfer_worker',34),('excluded_unresolved_observation_semantics',192)]:
  for i in range(count):rows.append({'subject':'synthetic','recording':route+str(i),'route':route,'canonical_task':None if route.startswith('excluded') else 'walking'})
 return rows,[r.copy() for r in rows if r['route'].startswith('excluded')]


def test_exact676_coverage_and_unresolved_semantics():
 rows,companions=full_scope();a,b=tool.scope_gate(rows,companions)
 assert len(a)==676 and len(b)==192


@pytest.mark.parametrize('defect',['missing','duplicate','foreign','canonical'])
def test_no_quiet_scope_shrink_or_guessed_tasks(defect):
 rows,companions=full_scope()
 if defect=='missing':companions.pop()
 elif defect=='duplicate':rows.append(rows[0])
 elif defect=='foreign':companions[0]['recording']='unrelated'
 else:rows[-1]['canonical_task']='walking'
 with pytest.raises(ValueError):tool.scope_gate(rows,companions)


def test_missing_actual_pilots_prevents_any_full_plan_write(tmp_path,monkeypatch):
 monkeypatch.setattr(tool,'BASE',tmp_path)
 def missing(*args):raise ValueError('Actual pilots missing')
 monkeypatch.setattr(tool,'prerequisites',missing)
 out=tmp_path/'full'
 with pytest.raises(ValueError,match='Actual pilots'):tool.prepare(out,tmp_path/'pilot',tmp_path/'companion')
 assert not out.exists()


def write(path,value):path.write_text(json.dumps(value));return tool.digest(path)


def companion_fixture(tmp_path):
 batch=tmp_path/'batch';batch.mkdir();folder=batch/'record';folder.mkdir()
 record={'subject':'synthetic','recording':'source_only','files':[]};streams=[];audited=[]
 bindings={str(tool.ROOT/'contributor_tools'/name):tool.digest(tool.ROOT/'contributor_tools'/name) for name in ['audit_gt25_source_companion.py','preserve_gt25_source_companion.py']}
 for i in range(15):
  source=tmp_path/f'synthetic{i}.csv';source.write_text('time,value\n0,1\n')
  compressed=folder/f'{i}.csv.gz';compressed.write_bytes(b'synthetic compressed bytes')
  parquet=folder/f'{i}.parquet';parquet.write_bytes(b'synthetic parquet bytes')
  kind=str(i);record['files'].append({'kind':kind,'path':str(source),'bytes':source.stat().st_size})
  streams.append({'kind':kind,'source_path':str(source),'source_sha256':tool.digest(source),'source_bytes':source.stat().st_size,'rows':1,'compressed':compressed.name,'compressed_sha256':tool.digest(compressed),'parquet':parquet.name,'parquet_sha256':tool.digest(parquet)})
  audited.append({'kind':kind,'rows':1,'source_sha256':tool.digest(source),'literal_csv_bytes_equal':True,'every_numeric_value_and_missing_mask_checked':True,'source_header_and_units_checked':True})
 classification=tmp_path/'classification.json';write(classification,{'records':[record]});bindings[str(classification)]=tool.digest(classification)
 worker={'record':record,'bindings':bindings};worker_sha=write(folder/'plan.json',worker)
 preserved={'plan_sha256':worker_sha,'bindings':bindings,'streams':streams};preserved_sha=write(folder/'preservation.json',preserved)
 receipt={'status':'all15_source_streams_lossless_readback_checked_unreviewed','scientific_approval':False,'canonical_dataset_approval':False,'subject':'synthetic','recording':'source_only','plan_sha256':worker_sha,'preservation_sha256':preserved_sha,'bindings':bindings,'streams':audited}
 receipt_sha=write(folder/'source_readback.json',receipt)
 row={'subject':'synthetic','recording':'source_only','output':str(folder),'readback':str(folder/'source_readback.json'),'readback_sha256':receipt_sha}
 plan_sha=write(batch/'plan.json',{'records':[row],'bindings':bindings,'classification':str(classification)})
 summary=batch/'batch_status.json';write(summary,{'status':'synthetic_success','scientific_approval':False,'canonical_dataset_approval':False,'records':[row],'plan_sha256':plan_sha})
 return summary,{('synthetic','source_only'):row},folder


def test_companion_receipt_closes_actual_sources_outputs_and_missingness(tmp_path):
 summary,expected,folder=companion_fixture(tmp_path)
 bindings=tool.companion_receipts(summary,expected,'synthetic_success')
 assert str(folder/'0.parquet') in bindings and str(tmp_path/'synthetic0.csv') in bindings
 (folder/'0.parquet').write_bytes(b'changed earlier output')
 with pytest.raises(ValueError,match='output changed'):tool.companion_receipts(summary,expected,'synthetic_success')


def test_companion_source_change_rejected(tmp_path):
 summary,expected,folder=companion_fixture(tmp_path)
 (tmp_path/'synthetic14.csv').write_text('changed')
 with pytest.raises(ValueError,match='source changed'):tool.companion_receipts(summary,expected,'synthetic_success')


def test_companion_duplicate_recording_rejected(tmp_path):
 summary,expected,folder=companion_fixture(tmp_path)
 d=json.loads(summary.read_text());d['records']*=2;write(summary,d)
 with pytest.raises(ValueError,match='Duplicate'):tool.companion_receipts(summary,expected,'synthetic_success')


def test_owned_nested_groups_cleaned_before_parent(monkeypatch):
 parent={'pid':10,'pgid':10,'start':'a','state':'S'};stage={'pid':11,'pgid':11,'start':'b','state':'S'};rows={10:parent,11:stage};calls=[]
 monkeypatch.setattr(tool,'process',lambda pid:rows.get(pid));monkeypatch.setattr(tool,'descendants',lambda pid:{11:stage})
 def kill(pid,sig):
  calls.append((pid,sig))
  if sig==signal.SIGKILL:rows.pop(pid,None)
 monkeypatch.setattr(tool.os,'kill',kill);monkeypatch.setattr(tool.os,'killpg',kill)
 tool.cleanup(SimpleNamespace(pid=10,wait=lambda timeout:0),{10:parent})
 assert calls==[(10,signal.SIGSTOP),(11,signal.SIGKILL),(10,signal.SIGKILL)]


def test_reused_pid_never_signaled(monkeypatch):
 old={'pid':10,'pgid':10,'start':'a','state':'S'}
 monkeypatch.setattr(tool,'process',lambda pid:{**old,'start':'reused'})
 def forbidden(*args):pytest.fail('Unrelated process touched')
 monkeypatch.setattr(tool,'descendants',forbidden);monkeypatch.setattr(tool.os,'kill',forbidden);monkeypatch.setattr(tool.os,'killpg',forbidden)
 tool.cleanup(SimpleNamespace(pid=10,wait=lambda timeout:0),{10:old})


def test_binding_merge_rejects_differing_hash_even_path_alias(tmp_path):
 path=tmp_path/'source';path.write_text('synthetic')
 target=tool.merge_bindings({},{str(path):'a'})
 with pytest.raises(ValueError,match='Conflicting hash'):tool.merge_bindings(target,{str(tmp_path/'missing/../source'):'b'})
 assert target=={str(path):'a'}
 assert tool.merge_bindings(target,{str(path):'a'})==target


def persisted_full_fixture(tmp_path,monkeypatch):
 """676 identities; real coverage/companion receipt closure, synthetic audit hook.

 The selected numerical/runtime checker is substituted: this tests orchestration,
 not GT25 scientific calculations. All metadata and source/output bytes persist.
 """
 from contributor_tools import run_gt25_selected_v5 as selected
 from contributor_tools.audit_gt25_selected_v5_coverage import check
 out=tmp_path/'full';sp=out/'selected';cp=out/'companions';sp.mkdir(parents=True);cp.mkdir()
 rows,unresolved=full_scope();inventory=tmp_path/'gt25_full_20261021/inventory.json';inventory.parent.mkdir();write(inventory,rows)
 raw=tmp_path/'raw';raw.write_text('synthetic raw source')
 selected_rows=[]
 for r in rows:
  row={**r,'output':str(sp/'records'/r['recording'])}
  if r['route'].startswith('excluded'):row['status']='excluded_unresolved_observation_semantics'
  else:
   folder=Path(row['output']);folder.mkdir(parents=True)
   audit={'scientific_approval':False,'rows_checked':150,'observations_checked':1,'numeric_features_checked':92,'bindings':{str(raw):tool.digest(raw)},'whole_selected_source_clocks_checked':True,'scientific_blockers':[],'no_accepted_observations_independently_checked':False,'status':'regular_raw_source_events_and_92_features_checked_unreviewed' if r['route']=='regular_selected_worker' else 'independent_raw_transfer_events_and_values_checked_unreviewed'}
   auditpath=folder/'source_comparison.json';sha=write(auditpath,audit)
   row.update(status='source_readback_checked_unreviewed',rows=150,receipts={str(auditpath):sha})
  selected_rows.append(row)
 selected_plan={'kind':'full','records':selected_rows,'bindings':{str(inventory):tool.digest(inventory)},'limitations':['synthetic test only']}
 plan_sha=write(sp/'plan.json',selected_plan)
 state={'status':'all_676_accounted_484_source_checked_192_unresolved','scientific_approval':False,'plan_sha256':plan_sha,'records':selected_rows}
 write(sp/'batch_status.json',state);write(sp/'independent_coverage.json',check(sp))
 # Source-companion byte checks remain real, sharing tiny synthetic bytes.
 modelroot=tmp_path/'model';modelroot.mkdir();model,_,model_folder=companion_fixture(modelroot)
 worker=json.loads((model_folder/'plan.json').read_text());preserved=json.loads((model_folder/'preservation.json').read_text());receipt=json.loads((model_folder/'source_readback.json').read_text())
 records=[];classification_records=[]
 for r in unresolved:
  record={**worker['record'],'subject':r['subject'],'recording':r['recording']};classification_records.append(record)
 classification=tmp_path/'all_classification.json';write(classification,{'records':classification_records})
 bindings={p:h for p,h in worker['bindings'].items() if not p.endswith('classification.json')};bindings[str(classification)]=tool.digest(classification)
 for record in classification_records:
  folder=cp/'records'/record['recording'];folder.mkdir(parents=True)
  for stream in preserved['streams']:
   for key in ('compressed','parquet'):(folder/stream[key]).symlink_to(model_folder/stream[key])
  worker_sha=write(folder/'plan.json',{'record':record,'bindings':bindings})
  p={**preserved,'bindings':bindings,'plan_sha256':worker_sha};p_sha=write(folder/'preservation.json',p)
  report={**receipt,'subject':record['subject'],'recording':record['recording'],'bindings':bindings,'plan_sha256':worker_sha,'preservation_sha256':p_sha};sha=write(folder/'source_readback.json',report)
  records.append({'subject':record['subject'],'recording':record['recording'],'output':str(folder),'readback':str(folder/'source_readback.json'),'readback_sha256':sha})
 cp_sha=write(cp/'plan.json',{'records':records,'classification':str(classification),'bindings':bindings})
 write(cp/'batch_status.json',{'status':'all192_source_companions_independently_checked_unreviewed','scientific_approval':False,'canonical_dataset_approval':False,'plan_sha256':cp_sha,'records':records})
 write(out/'plan.json',{'scientific_approval':False,'canonical_dataset_approval':False,'bindings':{},'limitations':['synthetic test only']})
 calls=[]
 def checked(row,plan):
  calls.append(tool.identity(row));return {'receipts':row['receipts'],'rows':row['rows']}
 monkeypatch.setattr(selected,'checked_record',checked)
 return out,calls


@pytest.fixture(scope='module')
def full_fixture(tmp_path_factory):
 # One bounded set of temporary metadata files, reused by mutation tests.
 with pytest.MonkeyPatch.context() as monkeypatch:
  out,calls=persisted_full_fixture(tmp_path_factory.mktemp('gt25_full'),monkeypatch)
  yield out,calls


def test_persisted_full_closure_all676_no_skips(full_fixture):
 out,calls=full_fixture;calls.clear();report=tool.final_closure(out)
 assert len(report['records'])==676 and len(calls)==484 and len(set(calls))==484
 assert sum(r['status']=='source_preserved_canonical_observations_unresolved' for r in report['records'])==192
 assert report['scientific_approval'] is False and report['scientific_full_scope_complete'] is False


@pytest.mark.parametrize('defect',['identity','route','output','scientific'])
def test_persisted_full_closure_rejects_selected_admission_mutation(full_fixture,defect):
 out,_=full_fixture;path=out/'selected/batch_status.json';original=path.read_text();d=json.loads(original)
 if defect=='identity':d['records'][0]['recording']='swapped'
 elif defect=='route':d['records'][0]['route']='streaming_transfer_worker'
 elif defect=='output':d['records'][0]['output']='wrong-output'
 else:d['scientific_approval']=True
 try:
  write(path,d)
  with pytest.raises(ValueError):tool.final_closure(out)
 finally:path.write_text(original)


def test_persisted_full_closure_rejects_companion_scientific_claim(full_fixture):
 out,_=full_fixture;path=out/'companions/batch_status.json';original=path.read_text();d=json.loads(original);d['canonical_dataset_approval']=True
 try:
  write(path,d)
  with pytest.raises(ValueError,match='successful'):tool.final_closure(out)
 finally:path.write_text(original)


def test_final_closure_conflict_between_record_audits(full_fixture,monkeypatch):
 from contributor_tools import run_gt25_selected_v5 as selected
 out,_=full_fixture;shared=out/'shared_synthetic_receipt';shared.write_text('first version')
 original=selected.checked_record;calls=0
 def changing_receipt(row,plan):
  nonlocal calls
  calls+=1
  if calls==2:shared.write_text('second version')
  # Synthetic readback hook models two completed record audits observing a
  # shared dependency at different times; actual persisted bytes change.
  row['receipts'][str(shared)]=tool.digest(shared)
  return original(row,plan)
 monkeypatch.setattr(selected,'checked_record',changing_receipt)
 try:
  with pytest.raises(ValueError,match='Conflicting hash'):tool.final_closure(out)
  assert calls==2
 finally:shared.unlink()


def test_persisted_selected_audit_scientific_claim_rejected(full_fixture):
 out,_=full_fixture;statepath=out/'selected/batch_status.json';original=statepath.read_text();state=json.loads(original)
 auditpath=Path(next(iter(state['records'][0]['receipts'])));audit_original=auditpath.read_text();audit=json.loads(audit_original);audit['scientific_approval']=True
 try:
  state['records'][0]['receipts'][str(auditpath)]=write(auditpath,audit);write(statepath,state)
  with pytest.raises(ValueError,match='audit approval'):tool.final_closure(out)
 finally:statepath.write_text(original);auditpath.write_text(audit_original)


@pytest.mark.parametrize('sig',[signal.SIGINT,signal.SIGTERM])
def test_signal_during_success_cleanup_retried_in_outer_finally(tmp_path,monkeypatch,sig):
 from contributor_tools import preserve_mblue_planar_estimates as memory
 out=tmp_path/'run';out.mkdir();(out/'companions').mkdir();write(out/'companions/plan.json',{})
 write(out/'plan.json',{'bindings':{},'pilot_plan':'unused','companion_pilot_summary':'unused','timeout_s':60})
 monkeypatch.setattr(tool,'prerequisites',lambda *a:{})
 monkeypatch.setattr(memory,'headroom',lambda p:None);monkeypatch.setattr(memory,'windows_available_mib',lambda:100000)
 handlers={};monkeypatch.setattr(tool.signal,'signal',lambda signum,handler:handlers.update({signum:handler}))
 child=SimpleNamespace(pid=10,returncode=0,poll=lambda:0)
 monkeypatch.setattr(tool.subprocess,'Popen',lambda *a,**k:child)
 monkeypatch.setattr(tool,'process',lambda pid:{'pid':pid,'start':'test','state':'S','pgid':pid})
 calls=[]
 def cleanup(child,owned):
  calls.append('cleanup')
  if len(calls)==1:handlers[sig](sig,None)
  assert handlers[signal.SIGINT]==signal.SIG_IGN and handlers[signal.SIGTERM]==signal.SIG_IGN
 monkeypatch.setattr(tool,'cleanup',cleanup)
 with pytest.raises(RuntimeError,match='termination'):tool.run(out)
 state=json.loads((out/'restoration_status.json').read_text())
 assert calls==['cleanup','cleanup'] and state['owned_workers_cleaned'] is True and state['status']=='stopped_incomplete'
