"""Gate and orchestrate existing v5 conversion plus all192 source companions.

No second converter implementation. Preparation requires actual four-family v5
and three-class source-companion pilot receipts. Run only in an externally owned
serial numerical slot; no controller is signaled or resumed by this tool.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
BASE=ROOT/'converted_datasets/reconversion_v2'
_READ_GUARD=None


def digest(path):
 import hashlib
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1024**2),b''):
   h.update(block)
   if _READ_GUARD is not None:_READ_GUARD()
 return h.hexdigest()


def merge_bindings(result,*groups):
 """Add hash claims to a private ledger; reject conflicting canonical paths."""
 for group in groups:
  for path,sha in group.items():
   # Normalize paths so spelling aliases cannot conceal a conflicting identity.
   path=str(Path(path).resolve())
   if path in result and result[path]!=sha:raise ValueError('Conflicting hash for bound path: '+path)
   result[path]=sha
 return result


def verify(bindings):
 for path,sha in bindings.items():
  if digest(path)!=sha:raise ValueError('Bound restoration artifact changed: '+path)


def identity(row):return row['subject'],row['recording']


def unique(rows):
 result={identity(r):r for r in rows}
 if len(result)!=len(rows):raise ValueError('Duplicate recording identity')
 return result


def scope_gate(selected,companions):
 selected=unique(selected);companions=unique(companions)
 counts=Counter(r['route'] for r in selected.values())
 if len(selected)!=676 or counts!=Counter(regular_selected_worker=450,streaming_transfer_worker=34,excluded_unresolved_observation_semantics=192):raise ValueError('Exact676 admission scope required')
 excluded={key for key,row in selected.items() if row['route']=='excluded_unresolved_observation_semantics'}
 if set(companions)!=excluded or any(selected[key]['canonical_task'] is not None for key in excluded):raise ValueError('Source companion scope must equal exactly192 unresolved identities')
 return selected,companions


def companion_receipts(summary_path,expected,status):
 """Reopen every receipt, original source and both persisted companion artifacts."""
 from contributor_tools.run_gt25_source_companion_batch import receipt_gate
 summary_path=Path(summary_path);summary=json.loads(summary_path.read_text());rows=unique(summary['records'])
 if summary.get('status')!=status or summary.get('scientific_approval') is not False or summary.get('canonical_dataset_approval') is not False or set(rows)!=set(expected):raise ValueError('Exact successful source companion scope required')
 batch_plan=summary_path.parent/'plan.json';plan=json.loads(batch_plan.read_text())
 if summary['plan_sha256']!=digest(batch_plan) or set(unique(plan['records']))!=set(expected):raise ValueError('Companion plan identity changed')
 verify(plan['bindings']);planned=unique(plan['records'])
 classification=unique(json.loads(Path(plan['classification']).read_text())['records'])
 bindings=merge_bindings({},{str(summary_path):digest(summary_path),str(batch_plan):digest(batch_plan)},plan['bindings'])
 for key,row in rows.items():
  receipt_path=Path(row['readback'])
  if receipt_path.parent!=Path(planned[key]['output']):raise ValueError('Companion output identity changed')
  receipt=json.loads(receipt_path.read_text());receipt_gate(receipt,*key)
  if digest(receipt_path)!=row['readback_sha256']:raise ValueError('Companion readback changed')
  worker_plan=receipt_path.parent/'plan.json';worker=json.loads(worker_plan.read_text())
  if digest(worker_plan)!=receipt['plan_sha256'] or receipt['bindings']!=worker['bindings']:raise ValueError('Source worker provenance mismatch')
  if worker['record']!=classification[key]:raise ValueError('Source recording admission changed')
  if (worker['record']['subject'],worker['record']['recording'])!=key:raise ValueError('Source worker identity mismatch')
  for name in ['audit_gt25_source_companion.py','preserve_gt25_source_companion.py']:
   tool=ROOT/'contributor_tools'/name
   if receipt['bindings'].get(str(tool))!=digest(tool):raise ValueError('Actual source companion implementation not bound')
  verify(receipt['bindings']);bindings=merge_bindings(bindings,receipt['bindings'])
  preserved=receipt_path.parent/'preservation.json'
  if digest(preserved)!=receipt['preservation_sha256']:raise ValueError('Preservation receipt changed')
  p=json.loads(preserved.read_text())
  if p.get('plan_sha256')!=receipt['plan_sha256'] or p.get('bindings')!=receipt['bindings']:raise ValueError('Preservation plan mismatch')
  streams=p['streams'];kinds=[s['kind'] for s in streams]
  if len(kinds)!=15 or len(set(kinds))!=15 or set(kinds)!={s['kind'] for s in receipt['streams']} or set(kinds)!={s['kind'] for s in worker['record']['files']}:raise ValueError('Companion stream scope incomplete')
  audit_streams={s['kind']:s for s in receipt['streams']};source_files={s['kind']:s for s in worker['record']['files']}
  for stream in streams:
   audited=audit_streams[stream['kind']];source=source_files[stream['kind']]
   if stream['source_path']!=source['path'] or stream['source_bytes']!=source['bytes'] or stream['source_sha256']!=audited['source_sha256'] or stream['rows']!=audited['rows']:raise ValueError('Companion source/readback identity differs')
   for field in ('compressed','parquet'):
    name=stream[field]
    if Path(name).name!=name:raise ValueError('Companion output escapes folder')
    artifact=receipt_path.parent/name
    if digest(artifact)!=stream[field+'_sha256']:raise ValueError('Companion output changed')
    bindings=merge_bindings(bindings,{str(artifact):stream[field+'_sha256']})
   if digest(stream['source_path'])!=stream['source_sha256']:raise ValueError('Companion source changed')
   bindings=merge_bindings(bindings,{stream['source_path']:stream['source_sha256']})
  bindings=merge_bindings(bindings,{str(receipt_path):row['readback_sha256'],str(worker_plan):receipt['plan_sha256'],str(preserved):receipt['preservation_sha256']})
 verify(bindings)
 return bindings


def prerequisites(pilot_plan,companion_summary):
 from contributor_tools import run_gt25_selected_v5 as selected
 from contributor_tools import run_gt25_source_companion_batch as companion
 pilot_plan=Path(pilot_plan).resolve()
 gate=merge_bindings({},selected.prerequisite({'kind':'full','pilot_plan':str(pilot_plan)}))
 # Also require independent full pilot coverage rather than summary counts alone.
 from contributor_tools.audit_gt25_selected_v5_coverage import check
 coverage=check(pilot_plan.parent)
 persisted=json.loads((pilot_plan.parent/'independent_coverage.json').read_text())
 if coverage!=persisted:raise ValueError('Independent v5 pilot coverage differs')
 scope=json.loads(companion.CLASSIFICATION.read_text())['records']
 smallest=[min((r for r in scope if r['source_metadata']['source_task']==family),key=lambda r:r['all_csv_bytes']) for family in ['ball_toss','cutting','start_stop']]
 gate=merge_bindings(gate,companion_receipts(companion_summary,unique(smallest),'three_class_source_companion_pilots_independently_checked'))
 gate=merge_bindings(gate,{str(pilot_plan):digest(pilot_plan)})
 verify(gate);return gate


def prepare(output,pilot_plan,companion_summary):
 from contributor_tools import run_gt25_selected_v5 as selected
 from contributor_tools import run_gt25_source_companion_batch as companion
 output=Path(output).resolve();pilot_plan=Path(pilot_plan).resolve();companion_summary=Path(companion_summary).resolve()
 if output.exists() or not output.is_relative_to(BASE):raise ValueError('Fresh reconversion_v2 output required')
 # No directories/actual full plans until both completed pilot sets pass.
 gate=prerequisites(pilot_plan,companion_summary)
 selected_plan=selected.prepare(output/'selected','full',pilot_plan)
 classification=json.loads(companion.CLASSIFICATION.read_text())['records'];scope_gate(selected_plan['records'],classification)
 output.mkdir(parents=True)
 try:
  (output/'selected').mkdir();(output/'selected/plan.json').write_text(json.dumps(selected_plan,indent=2)+'\n')
  companion.prepare(output/'companions','full',companion_summary)
  companion_plan=json.loads((output/'companions/plan.json').read_text());scope_gate(selected_plan['records'],companion_plan['records'])
  bindings=merge_bindings({},selected_plan['bindings'],companion_plan['bindings'],gate)
  for p in [Path(__file__).resolve(),ROOT/'contributor_tools/audit_gt25_selected_v5_coverage.py',output/'selected/plan.json',output/'companions/plan.json']:bindings=merge_bindings(bindings,{str(p):digest(p)})
  plan={'status':'prepared_actual_pilots_checked_not_run','scientific_approval':False,'canonical_dataset_approval':False,'bindings':bindings,'pilot_plan':str(pilot_plan),'companion_pilot_summary':str(companion_summary),'counts':{'regular':450,'streaming':34,'source_only':192,'total':676},'limitations':selected.LIMITATIONS+['All192 companions retain original source streams; their canonical observation/task semantics remain unresolved.','Parsed source preservation does not restore unprovided native transitions.'],'timeout_s':7*24*3600,'serial_external_slot_required':True}
  verify(bindings);(output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');return plan
 except BaseException as error:
  (output/'preparation_failure.json').write_text(json.dumps({'status':'incomplete_preserved','reason':str(error)}));raise


def final_closure(output):
 from contributor_tools import run_gt25_selected_v5 as selected
 from contributor_tools.audit_gt25_selected_v5_coverage import check
 output=Path(output);plan=json.loads((output/'plan.json').read_text());verify(plan['bindings'])
 if plan.get('scientific_approval') is not False or plan.get('canonical_dataset_approval') is not False:raise ValueError('Unsupported restoration approval')
 coverage=check(output/'selected')
 if coverage!=json.loads((output/'selected/independent_coverage.json').read_text()):raise ValueError('Final independent selected coverage differs')
 sp=json.loads((output/'selected/plan.json').read_text());state=json.loads((output/'selected/batch_status.json').read_text());cp=json.loads((output/'companions/plan.json').read_text())
 selected_rows,companion_rows=scope_gate(state['records'],cp['records']);bindings=companion_receipts(output/'companions/batch_status.json',companion_rows,'all192_source_companions_independently_checked_unreviewed')
 ledger=[]
 for key,r in selected_rows.items():
  if key in companion_rows:
   ledger.append({'subject':key[0],'recording':key[1],'status':'source_preserved_canonical_observations_unresolved','canonical_task':None,'source_companion':companion_rows[key]['output']});continue
  checked=selected.checked_record(r,sp)
  if checked['receipts']!=r['receipts']:raise ValueError('Final selected record receipt changed')
  bindings=merge_bindings(bindings,checked['receipts'])
  for audit_path in checked['receipts']:
   if Path(audit_path).name=='source_comparison.json':
    audit=json.loads(Path(audit_path).read_text())
    if audit.get('scientific_approval') is not False:raise ValueError('Unsupported selected audit approval')
    bindings=merge_bindings(bindings,audit['bindings'])
  ledger.append({'subject':key[0],'recording':key[1],'status':'selected_observations_source_checked_unreviewed','route':r['route'],'rows':checked['rows'],'output':r['output']})
 for p in [output/'selected/batch_status.json',output/'selected/independent_coverage.json']:bindings=merge_bindings(bindings,{str(p):digest(p)})
 bindings=merge_bindings(bindings,plan['bindings'])
 verify(bindings)
 return {'status':'all676_accounted_484_selected_and192_source_companions_checked_unreviewed','scientific_approval':False,'canonical_dataset_approval':False,'scientific_full_scope_complete':False,'records':ledger,'receipts':bindings,'plan_sha256':digest(output/'plan.json'),'limitations':plan['limitations']}


def process(pid):
 try:
  p=Path('/proc')/str(pid);fields=p.joinpath('stat').read_text().rsplit(')',1)[1].split()
  return {'pid':pid,'start':fields[19],'state':fields[0],'ppid':int(fields[1]),'pgid':int(fields[2])}
 except FileNotFoundError:return None


def descendants(parent):
 rows={int(p.name):process(int(p.name)) for p in Path('/proc').iterdir() if p.name.isdigit()};found={parent}
 while True:
  added={pid for pid,r in rows.items() if r and r['ppid'] in found}-found
  if not added:break
  found|=added
 return {pid:rows[pid] for pid in found if pid!=parent and rows.get(pid)}


def cleanup(child,owned):
 def same(identity):
  current=process(identity['pid']);return current and current['start']==identity['start'] and current['state']!='Z'
 parent=owned.get(child.pid)
 if parent and same(parent):
  os.kill(child.pid,signal.SIGSTOP);owned.update(descendants(child.pid))
 for identity in [r for pid,r in owned.items() if pid!=child.pid]+([parent] if parent else []):
  if same(identity):
   try:
    if identity['pgid']==identity['pid']:os.killpg(identity['pid'],signal.SIGKILL)
    else:os.kill(identity['pid'],signal.SIGKILL)
   except ProcessLookupError:pass
 child.wait(timeout=10)
 deadline=time.monotonic()+10
 while any(same(r) for r in owned.values()) and time.monotonic()<deadline:time.sleep(.1)
 if any(same(r) for r in owned.values()):raise RuntimeError('Owned worker cleanup unproved')


def run(output):
 global _READ_GUARD
 output=Path(output).resolve();path=output/'plan.json';plan=json.loads(path.read_text());sha=digest(path);verify(plan['bindings'])
 gate={}
 if (output/'restoration_status.json').exists():raise FileExistsError('Fresh attempt required')
 from contributor_tools.preserve_mblue_planar_estimates import headroom,windows_available_mib
 def resources(startup=False):
  headroom(output);linux=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))//1024
  if windows_available_mib()<(3584 if startup else 2048) or linux<(3584 if startup else 2048):raise MemoryError('Preserve shared host reserves')
 def verified():
  verify(plan['bindings']);verify(gate)
  if digest(path)!=sha:raise ValueError('Restoration plan changed')
 state={'status':'running','scientific_approval':False,'canonical_dataset_approval':False,'plan_sha256':sha,'stages':[]};child=None;owned={};clean=True
 def save():
  temp=output/'restoration_status.tmp';temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(output/'restoration_status.json')
 def terminate(signum,frame):raise RuntimeError('Coordinator termination requested')
 signal.signal(signal.SIGTERM,terminate);signal.signal(signal.SIGINT,terminate)
 env=dict(os.environ);env.pop('PYTHONOPTIMIZE',None)
 for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS','NUMEXPR_NUM_THREADS'):env[key]='1'
 commands=[('selected',[sys.executable,str(ROOT/'contributor_tools/run_gt25_selected_v5.py'),'--output-root',str(output/'selected'),'--run']),('companions',[sys.executable,str(ROOT/'contributor_tools/run_gt25_source_companion_batch.py'),'run','--plan',str(output/'companions/plan.json'),'--plan-sha256',digest(output/'companions/plan.json')])]
 save();started=time.monotonic();last_hash_guard=0
 def hash_guard():
  nonlocal last_hash_guard
  if time.monotonic()-last_hash_guard<15:return
  if (output/'STOP').exists() or (output/'STOP_AFTER_CURRENT').exists():raise RuntimeError('Coordinator stop requested')
  if time.monotonic()-started>plan['timeout_s']:raise TimeoutError('Finite full restoration timeout')
  resources();last_hash_guard=time.monotonic()
 _READ_GUARD=hash_guard
 try:
  resources(True);gate=prerequisites(plan['pilot_plan'],plan['companion_pilot_summary'])
  for name,command in commands:
   verified();resources(True)
   with (output/(name+'.log')).open('x') as log:
    child=subprocess.Popen(['nice','-n','19','ionice','-c','3',*command],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    p=process(child.pid);owned={child.pid:p} if p else {};last=0
    while child.poll() is None:
     owned.update(descendants(child.pid))
     if (output/'STOP').exists() or (output/'STOP_AFTER_CURRENT').exists():raise RuntimeError('Coordinator stop requested')
     if time.monotonic()-started>plan['timeout_s']:raise TimeoutError('Finite full restoration timeout')
     if time.monotonic()-last>15:resources();last=time.monotonic()
     time.sleep(.2)
    if child.returncode:raise RuntimeError('Full restoration stage failed: '+name)
    cleanup(child,owned);child=None;owned={}
   verified();state['stages'].append(name);save()
  report=final_closure(output);verified()
  with (output/'coverage.json').open('x') as f:json.dump(report,f,indent=2)
  state.update(status=report['status'],coverage_sha256=digest(output/'coverage.json'))
 except BaseException as error:state.update(status='stopped_incomplete',reason=str(error))
 finally:
  signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.signal(signal.SIGINT,signal.SIG_IGN)
  if child is not None:
   try:cleanup(child,owned)
   except Exception as error:clean=False;state.update(status='stopped_incomplete_cleanup_unresolved',cleanup_failure=str(error))
  state['owned_workers_cleaned']=clean;save()
  _READ_GUARD=None
 if state['status']!='all676_accounted_484_selected_and192_source_companions_checked_unreviewed':raise RuntimeError(state.get('reason',state['status']))


def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
 q=sub.add_parser('prepare');q.add_argument('--output',type=Path,required=True);q.add_argument('--pilot-plan',type=Path,required=True);q.add_argument('--companion-pilot-summary',type=Path,required=True)
 q=sub.add_parser('run');q.add_argument('--output',type=Path,required=True)
 a=p.parse_args()
 if sys.flags.optimize:raise ValueError('Independent auditors require assertions')
 if a.action=='prepare':prepare(a.output,a.pilot_plan,a.companion_pilot_summary)
 else:run(a.output)
if __name__=='__main__':main()
