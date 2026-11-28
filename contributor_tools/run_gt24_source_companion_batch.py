"""Explicit serial GT24 all869 source companions; external exclusive slot required."""
import argparse,hashlib,json,os,resource,signal,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'converted_datasets/reconversion_v2';sys.path.insert(0,str(ROOT))


def digest(path,guard=lambda:None):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024**2),b''):guard();h.update(b)
 return h.hexdigest()


def verify(bindings,guard=lambda:None):
 for p,h in bindings.items():
  if digest(p,guard)!=h:raise ValueError('Source companion dependency changed')


def gate(receipt,row):
 if receipt.get('status')!='all_inventoried_source_streams_lossless_readback_checked_unreviewed' or receipt.get('scientific_approval') is not False or receipt.get('canonical_dataset_approval') is not False:raise ValueError('Source-only readback incomplete')
 if any(receipt.get(k)!=row[k] for k in ('phase','subject','recording')):raise ValueError('Phase/subject/source identity differs')
 expected={f['kind'] for f in row['files']};streams=receipt.get('streams',[])
 if len(streams)!=len(expected) or {s['kind'] for s in streams}!=expected:raise ValueError('Missing/duplicate source streams')
 for stream in streams:
  if stream.get('rows',0)<1 or any(stream.get(k) is not True for k in ('literal_csv_bytes_equal','every_numeric_value_and_missing_mask_checked','source_header_and_units_checked')):raise ValueError('Unverified source stream')


def receipt_closure(folder,row):
 """Capture exact readback, plan, producer, source and output artifact identities."""
 folder=Path(folder);path=folder/'source_readback.json';receipt=json.loads(path.read_text());gate(receipt,row)
 plan=folder/'plan.json';producer=folder/'preservation.json'
 if receipt.get('plan_sha256')!=digest(plan) or receipt.get('preservation_sha256')!=digest(producer):raise ValueError('Per-record source receipt changed')
 if receipt.get('source_recording_id')!=row['source_recording_id']:raise ValueError('Source recording ID differs')
 bindings={str(path):digest(path),str(plan):digest(plan),str(producer):digest(producer)}
 files={file['kind']:file for file in row['files']}
 for stream in receipt['streams']:
  source=files[stream['kind']]['path']
  bindings[source]=stream['source_sha256']
  for field in ('compressed','parquet'):
   name=stream[field]
   if Path(name).name!=name:raise ValueError('Output must be a local artifact basename')
   bindings[str(folder/name)]=stream[field+'_sha256']
 verify(bindings)
 return bindings


def cleanup_owned(child):
 try:os.killpg(child.pid,signal.SIGKILL)
 except ProcessLookupError:pass
 child.wait(timeout=10)


def prepare(classification,output):
 classification=Path(classification).resolve();output=Path(output).resolve();scope=json.loads(classification.read_text());rows=scope['records']
 if scope['status']!='all869_source_companions_header_inventory_unreviewed' or len(rows)!=869 or len({(r['phase'],r['subject'],r['recording']) for r in rows})!=869:raise ValueError('Exact869identityscope required')
 if output.exists() or not output.is_relative_to(BASE):raise ValueError('Fresh isolated output required')
 bindings=dict(scope['bindings'])
 for p in [classification,Path(__file__).resolve(),*[ROOT/'contributor_tools'/n for n in ('preserve_gt24_source_companion.py','audit_gt24_source_companion.py','preserve_mblue_planar_estimates.py')]]:
  h=digest(p)
  if str(p) in bindings and bindings[str(p)]!=h:raise ValueError('Do not refresh frozen evidence')
  bindings[str(p)]=h
 verify(bindings);plan={'status':'prepared_not_run','scientific_approval':False,'canonical_dataset_approval':False,'bindings':bindings,'classification':str(classification),'output':str(output),'records':rows,'stage_timeout_seconds':3600,'whole_run_timeout_seconds':30*24*3600,'memory_limit_mib':768,'full_canonical_adoption':False};output.mkdir();p=output/'plan.json';p.write_text(json.dumps(plan,indent=2)+'\n');return {'plan':str(p),'plan_sha256':digest(p),'records':869}


def _run(path,expected):
 path=Path(path).resolve();out=path.parent
 if digest(path)!=expected or {p.name for p in out.iterdir()}!={'plan.json'}:raise ValueError('Fresh bound plan required')
 plan=json.loads(path.read_text());verify(plan['bindings']);started=time.monotonic()
 from contributor_tools.preserve_mblue_planar_estimates import headroom,windows_available_mib
 state={'status':'running','plan_sha256':expected,'scientific_approval':False,'canonical_dataset_approval':False,'records':[]}
 def save():
  p=out/'status.tmp';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(out/'batch_status.json')
 def resources(startup):
  headroom(out)
  if windows_available_mib()<(2816 if startup else 2048):raise MemoryError('Windows source worker reserve insufficient')
 def stage(command,label):
  if (out/'STOP').exists() or (out/'STOP_AFTER_CURRENT').exists():raise RuntimeError('Coordinator stop')
  if time.monotonic()-started>plan['whole_run_timeout_seconds']:raise TimeoutError('Full source batch timeout')
  verify(plan['bindings'])
  if digest(path)!=expected:raise ValueError('Batch plan changed between stages')
  resources(True);env=dict(os.environ);env.pop('PYTHONOPTIMIZE',None)
  for n in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):env[n]='1'
  with (out/(label+'.log')).open('x') as log:
   def cap():resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
   child=subprocess.Popen(['nice','-n','19','ionice','-c','3',*command],cwd=ROOT,env=env,start_new_session=True,stdout=log,stderr=subprocess.STDOUT,preexec_fn=cap);begin=last=time.monotonic()
   try:
    state['worker_pid']=child.pid;save()
    while child.poll() is None:
     if (out/'STOP').exists():raise RuntimeError('Immediate coordinator stop')
     if time.monotonic()-begin>plan['stage_timeout_seconds']:raise TimeoutError('Per-stage source worker timeout')
     if time.monotonic()-last>15:resources(False);last=time.monotonic()
     time.sleep(.25)
    if child.returncode:raise RuntimeError('Source preservation failed; inspect preserved log')
   finally:
    cleanup_owned(child);state.pop('worker_pid',None);save()
 try:
  save()
  for index,row in enumerate(plan['records']):
   folder=out/'records'/row['phase']/row['subject']/row['recording'];writer=str(ROOT/'contributor_tools/preserve_gt24_source_companion.py')
   stage([sys.executable,writer,'prepare','--classification',plan['classification'],'--phase',row['phase'],'--subject',row['subject'],'--recording',row['recording'],'--output',str(folder)],f'{index:04d}_prepare')
   p=folder/'plan.json';h=digest(p)
   stage([sys.executable,writer,'run','--plan',str(p),'--plan-sha256',h],f'{index:04d}_preserve')
   stage([sys.executable,str(ROOT/'contributor_tools/audit_gt24_source_companion.py'),'--plan',str(p),'--plan-sha256',h],f'{index:04d}_audit')
   report=folder/'source_readback.json';result=json.loads(report.read_text());gate(result,row)
   if result['plan_sha256']!=h or digest(p)!=h or result['preservation_sha256']!=digest(folder/'preservation.json'):raise ValueError('Per-record source receipt changed')
   state['records'].append({k:row[k] for k in ('phase','subject','recording')}|{'report':str(report),'report_sha256':digest(report),'streams':len(row['files']),'artifact_hashes':receipt_closure(folder,row)});save()
  verify(plan['bindings'])
  if digest(path)!=expected or len(state['records'])!=869 or {(r['phase'],r['subject'],r['recording']) for r in state['records']}!={(r['phase'],r['subject'],r['recording']) for r in plan['records']}:raise ValueError('Full source scope changed')
  last_check=[0.]
  def closure_guard():
   if time.monotonic()-last_check[0]>15:
    resources(False);last_check[0]=time.monotonic()
   if (out/'STOP').exists() or time.monotonic()-started>plan['whole_run_timeout_seconds']:raise RuntimeError('Final closure interrupted')
  for row in state['records']:
   verify(row['artifact_hashes'],closure_guard)
  verify(plan['bindings'],closure_guard)
  if digest(path)!=expected:raise ValueError('Plan changed during final closure')
  state['status']='all869_gt24_source_companions_lossless_readback_checked_unreviewed'
 except BaseException as error:state.update(status='stopped_incomplete',reason=str(error));raise
 finally:save()

def run(path,expected):
 def interrupted(signum,frame):raise RuntimeError('Coordinator interrupted: '+str(signum))
 previous={sig:signal.getsignal(sig) for sig in (signal.SIGTERM,signal.SIGINT)}
 try:
  for sig in previous:signal.signal(sig,interrupted)
  return _run(path,expected)
 finally:
  for sig,handler in previous.items():signal.signal(sig,handler)


if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True);q=s.add_parser('prepare');q.add_argument('--classification',type=Path,required=True);q.add_argument('--output',type=Path,required=True);q=s.add_parser('run');q.add_argument('--plan',type=Path,required=True);q.add_argument('--plan-sha256',required=True);a=p.parse_args()
 if a.mode=='prepare':print(json.dumps(prepare(a.classification,a.output)))
 else:run(a.plan,a.plan_sha256)
