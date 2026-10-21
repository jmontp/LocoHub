"""Explicit serial pilots/full192 source companions; plan-only by default.

External coordinator owns exclusive numerical slot. Full plan preparation
requires completed independent three-class pilot evidence. No canonical approval.
"""
import argparse,collections,hashlib,importlib.util,json,os,signal,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'converted_datasets/reconversion_v2'
CLASSIFICATION=BASE/'swarm_backlog_20261021/gt25_unmapped192_source_classification.json'


def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024**2),b''):h.update(b)
 return h.hexdigest()


def verify(bindings):
 for p,h in bindings.items():
  if digest(p)!=h:raise ValueError('Bound source companion evidence changed')


def receipt_gate(receipt,subject,recording):
 if receipt.get('status')!='all15_source_streams_lossless_readback_checked_unreviewed' or receipt.get('scientific_approval') is not False or receipt.get('canonical_dataset_approval') is not False or receipt.get('subject')!=subject or receipt.get('recording')!=recording:raise ValueError('Independent source receipt invalid')
 streams=receipt.get('streams',[])
 if len(streams)!=15 or len({s['kind'] for s in streams})!=15:raise ValueError('Incomplete15streamscope')
 for stream in streams:
  if stream.get('rows',0)<=0 or any(stream.get(k) is not True for k in ('literal_csv_bytes_equal','every_numeric_value_and_missing_mask_checked','source_header_and_units_checked')):raise ValueError('Source preservation checks incomplete')


def prepare(output,kind,pilot_summary=None):
 output=Path(output).resolve();scope=json.loads(CLASSIFICATION.read_text());records=scope['records']
 if scope['counts']['records']!=192 or len(records)!=192 or len({(r['subject'],r['recording']) for r in records})!=192:raise ValueError('Exact192identitiesrequired')
 if output.exists() or not output.is_relative_to(BASE):raise ValueError('Fresh local batch root required')
 paths=[Path(__file__).resolve(),ROOT/'contributor_tools/preserve_gt25_source_companion.py',ROOT/'contributor_tools/audit_gt25_source_companion.py',ROOT/'contributor_tools/preserve_mblue_planar_estimates.py',ROOT/'contributor_tools/conversion_scripts/Fukuchi_2018_Walking/run_ensemble_pilot.py',CLASSIFICATION]
 bindings={**scope['bindings'],**{str(p):digest(p) for p in paths}}
 smallest=[min((r for r in records if r['source_metadata']['source_task']==family),key=lambda r:r['all_csv_bytes']) for family in ['ball_toss','cutting','start_stop']]
 if kind=='pilot':selected=smallest
 else:
  if pilot_summary is None:raise ValueError('Actual completed threeclass pilot required before full plan')
  pilot_summary=Path(pilot_summary).resolve();pilot=json.loads(pilot_summary.read_text());expected={(r['subject'],r['recording']) for r in smallest}
  if pilot.get('status')!='three_class_source_companion_pilots_independently_checked' or pilot.get('scientific_approval') is not False or len(pilot.get('records',[]))!=3 or {(r['subject'],r['recording']) for r in pilot['records']}!=expected:raise ValueError('Full plan requires exactpilotcoverage')
  for row in pilot['records']:
   path=Path(row['readback']);receipt=json.loads(path.read_text());receipt_gate(receipt,row['subject'],row['recording'])
   if digest(path)!=row['readback_sha256']:raise ValueError('Pilot source receipt changed')
   verify(receipt['bindings']);bindings[str(path)]=row['readback_sha256']
   preservation=path.parent/'preservation.json'
   if digest(preservation)!=receipt['preservation_sha256']:raise ValueError('Pilot preservation receipt changed')
   prior=json.loads(preservation.read_text());bindings[str(preservation)]=receipt['preservation_sha256']
   for stream in prior['streams']:
    for name,hashkey in [('compressed','compressed_sha256'),('parquet','parquet_sha256')]:
     artifact=path.parent/stream[name]
     if Path(stream[name]).name!=stream[name] or digest(artifact)!=stream[hashkey]:raise ValueError('Pilot output changed')
     bindings[str(artifact)]=stream[hashkey]
    if digest(stream['source_path'])!=stream['source_sha256']:raise ValueError('Pilot original source changed')
    bindings[stream['source_path']]=stream['source_sha256']
  bindings[str(pilot_summary)]=digest(pilot_summary);selected=records
 verify(bindings)
 plan={'status':'prepared_not_run','scientific_approval':False,'canonical_dataset_approval':False,'kind':kind,'bindings':bindings,'classification':str(CLASSIFICATION),'output':str(output),'records':[{'subject':r['subject'],'recording':r['recording'],'source_task':r['source_metadata']['source_task'],'source_bytes':r['all_csv_bytes'],'streams':len(r['files']),'output':str(output/'records'/r['subject']/r['recording'])} for r in selected],'stage_timeout_seconds':3600,'worker_memory_mib':768,'batch_admission_mib':256,'disk_reserve_gib':5,'guard_module':str(paths[-2])}
 output.mkdir(parents=True);(output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');return {'plan':str(output/'plan.json'),'plan_sha256':digest(output/'plan.json'),'records':len(selected)}


def run(plan_path,expected):
 plan_path=Path(plan_path).resolve();out=plan_path.parent
 if digest(plan_path)!=expected or {p.name for p in out.iterdir()}!={'plan.json'}:raise ValueError('Fresh bound batch plan only')
 plan=json.loads(plan_path.read_text());verify(plan['bindings']);spec=importlib.util.spec_from_file_location('companion_guard',plan['guard_module']);guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
 os.nice(max(0,19-os.nice(0)));guard.check_resources(prelaunch=True)
 state={'status':'running','scientific_approval':False,'canonical_dataset_approval':False,'kind':plan['kind'],'plan_sha256':expected,'bindings':plan['bindings'],'records':[],'stages':[]}
 def save():
  p=out/'batch.tmp';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(out/'batch_status.json')
 def stage(cmd,log):
  if (out/'STOP_AFTER_CURRENT').exists():raise RuntimeError('Coordinator stop requested')
  verify(plan['bindings']);guard.check_resources(prelaunch=True);entry={'command':cmd};state['stages'].append(entry)
  env=dict(os.environ)
  for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):env[name]='1'
  env.pop('PYTHONOPTIMIZE',None)
  with log.open('x') as stream:
   child=subprocess.Popen(['nice','-n','19','ionice','-c','3',*cmd],cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True);entry['pid']=child.pid;save();started=last=time.monotonic()
   try:
    while child.poll() is None:
     if (out/'STOP').exists():raise RuntimeError('Coordinator immediate stop requested')
     if time.monotonic()-started>plan['stage_timeout_seconds']:raise subprocess.TimeoutExpired(cmd,plan['stage_timeout_seconds'])
     if time.monotonic()-last>15:guard.check_resources();last=time.monotonic()
     time.sleep(.25)
    if child.returncode:raise subprocess.CalledProcessError(child.returncode,cmd)
   finally:guard.stop_owned_group(child);entry['returncode']=child.returncode;entry['owned_worker_cleaned']=True;save()
 try:
  save()
  for row in plan['records']:
   folder=Path(row['output']);label=row['subject']+'_'+row['recording']
   stage([sys.executable,str(ROOT/'contributor_tools/preserve_gt25_source_companion.py'),'prepare','--classification',plan['classification'],'--subject',row['subject'],'--recording',row['recording'],'--output',str(folder)],out/(label+'_prepare.log'))
   worker_plan=folder/'plan.json';worker_sha=digest(worker_plan)
   stage([sys.executable,str(ROOT/'contributor_tools/preserve_gt25_source_companion.py'),'run','--plan',str(worker_plan),'--plan-sha256',worker_sha],out/(label+'_preserve.log'))
   stage([sys.executable,str(ROOT/'contributor_tools/audit_gt25_source_companion.py'),'--plan',str(worker_plan),'--plan-sha256',worker_sha],out/(label+'_readback.log'))
   receipt_path=folder/'source_readback.json';receipt=json.loads(receipt_path.read_text());receipt_gate(receipt,row['subject'],row['recording'])
   if receipt['plan_sha256']!=worker_sha or digest(worker_plan)!=worker_sha:raise ValueError('Source worker plan changed')
   state['records'].append({**row,'readback':str(receipt_path),'readback_sha256':digest(receipt_path),'stream_count':15});save()
  verify(plan['bindings'])
  if digest(plan_path)!=expected:raise ValueError('Batch plan changed')
  state['status']='three_class_source_companion_pilots_independently_checked' if plan['kind']=='pilot' else 'all192_source_companions_independently_checked_unreviewed'
 except Exception as e:state.update(status='stopped_incomplete',reason=str(e));raise
 finally:save()


def main():
 p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True);q=s.add_parser('prepare');q.add_argument('--output',type=Path,required=True);q.add_argument('--kind',choices=['pilot','full'],required=True);q.add_argument('--pilot-summary',type=Path);q=s.add_parser('run');q.add_argument('--plan',type=Path,required=True);q.add_argument('--plan-sha256',required=True);a=p.parse_args()
 if a.mode=='prepare':print(json.dumps(prepare(a.output,a.kind,a.pilot_summary)))
 else:run(a.plan,a.plan_sha256)
if __name__=='__main__':main()
