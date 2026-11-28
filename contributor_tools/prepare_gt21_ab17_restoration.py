"""Isolated v1 extraction/readback and schema admission; never substitute raw ik for ik_offset."""
import argparse,hashlib,json,os,resource,signal,subprocess,sys,time,zipfile,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools import extract_gt21_recovered_archive as extract
from contributor_tools import inspect_gt21_recovered_archive as inspect
BASE=ROOT/'converted_datasets/reconversion_v2'


def inventory(infos):
 records={};other=[]
 for info in infos:
  if info.is_dir():continue
  parts=Path(info.filename).parts
  if len(parts)==5 and parts[-1].endswith('.mat'):
   key=tuple(parts[:3])+(parts[-1],)
   records.setdefault(key,{})[parts[3]]={'member':info.filename,'bytes':info.file_size,'crc32':info.CRC}
  else:other.append({'member':info.filename,'bytes':info.file_size,'crc32':info.CRC})
 return [{'subject':k[0],'date':k[1],'mode':k[2],'recording':k[3],'channels':v} for k,v in sorted(records.items())],other


def persisted_readback(root,infos,guard=lambda:None):
 root=Path(root);expected={i.filename:i for i in infos if not i.is_dir()};seen=set();total=0
 manifest=root/'member_manifest.jsonl';manifest_sha=inspect.digest(manifest)
 with manifest.open() as stream:
  for line in stream:
   guard();row=json.loads(line);name=row['member']
   if name in seen or name not in expected:raise ValueError('Duplicate or unexpected manifest member')
   seen.add(name);info=expected[name];path=root/'files'/name
   if path.is_symlink() or not path.resolve().is_relative_to((root/'files').resolve()):raise ValueError('Unsafe persisted member')
   sha=hashlib.sha256();crc=0;size=0
   with path.open('rb') as f:
    for block in iter(lambda:f.read(1024**2),b''):
     guard();size+=len(block);sha.update(block);crc=zlib.crc32(block,crc)
   if size!=info.file_size or size!=row['bytes'] or crc&0xffffffff!=info.CRC or row['crc32']!=f'{crc&0xffffffff:08x}' or sha.hexdigest()!=row['sha256']:raise ValueError('Persisted bytes differ from ZIP/manifest')
   total+=size
 if seen!=set(expected):raise ValueError('Missing manifest members')
 actual={str(p.relative_to(root/'files')) for p in (root/'files').rglob('*') if p.is_file()}
 if actual!=seen:raise ValueError('Unmanifested persisted files')
 if inspect.digest(manifest)!=manifest_sha:raise ValueError('Manifest changed during readback')
 return {'files':len(seen),'bytes':total,'manifest_sha256':manifest_sha,'status':'all_extracted_bytes_independently_reread_unreviewed','scientific_approval':False}


def prepare(output):
 output=Path(output).resolve()
 if output.exists() or not output.is_relative_to(BASE):raise ValueError('Fresh local plan root required')
 source=Path('/mnt/s/locomotion_data/gt21_missing_participants_v1/AB17')
 plan=extract.prepare(source/'acquisition_result.json',source/'archive_inspection.json',source/'extracted_v1_independent_20261021')
 with zipfile.ZipFile(plan['archive']) as z:
  inspect.inspect_members(z.infolist(),'AB17',2**63)
  records,other=inventory(z.infolist())
 if len(records)!=133:raise ValueError('Exact reviewed AB17 recording scope required')
 required={'conditions','ik','id','fp','gcLeft','gcRight'}
 selected=[]
 for mode in sorted({r['mode'] for r in records}):
  admitted=[r for r in records if r['mode']==mode and required<=set(r['channels']) and sum(r['channels'][k]['bytes'] for k in required)<32*1024**2]
  if not admitted:raise ValueError('No bounded mode pilot')
  selected.append(min(admitted,key=lambda r:sum(v['bytes'] for v in r['channels'].values())))
 bindings=dict(plan['bindings'])
 for p in [Path(__file__),ROOT/'contributor_tools/gt21_numeric_source.py',ROOT/'contributor_tools/run_gt25_coverage_pilot.py']:
  bindings[str(p.resolve())]=inspect.digest(p)
 result={'status':'prepared_not_extracted','scientific_approval':False,'extraction':plan,'bindings':bindings,'records':records,'other_members':other,'schema_pilot_candidates':selected,'schema_pilot_status':'Not executed; native MATLAB required for unsupported MCOS layouts/conditions labels. No source clock proof inferred.','canonical_blockers':['Publisher v1 lacks ik_offset/static; converter cannot substitute ik without documented processing.','Archive lacks SubjectInfo.mat; independently version-bound participant mass required.','All133 recordings need event/task/force validation; four selected records are feasibility only.'],'cohort':{'expected':22,'current':16,'recovered_unconverted':'AB17','other_missing_count':5},'extraction_worker_cap_mib':256,'extraction_timeout_s':7200,'exclusive_serial_slot_required':True}
 output.mkdir();(output/'plan.json').write_text(json.dumps(result,indent=2)+'\n')
 return result


def worker(path,expected):
 resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,)*2);path=Path(path);plan=json.loads(path.read_text());started=time.monotonic()
 def guard():
  if time.monotonic()-started>7200 or any((path.parent/n).exists() for n in ('STOP','STOP_AFTER_CURRENT')):raise RuntimeError('STOP or deadline')
 guard()
 if inspect.digest(path)!=expected:raise ValueError('Plan changed')
 for p,h in plan['bindings'].items():
  if inspect.digest(p)!=h:raise ValueError('Evidence changed')
 result=extract.extract(plan['extraction'],timeout_seconds=7000)
 with zipfile.ZipFile(plan['extraction']['archive']) as z:receipt=persisted_readback(plan['extraction']['output_root'],z.infolist(),guard)
 guard()
 if inspect.digest(plan['extraction']['archive'])!=plan['extraction']['archive_sha256']:raise ValueError('Archive changed after persisted readback')
 if inspect.digest(path)!=expected:raise ValueError('Plan changed')
 for p,h in plan['bindings'].items():
  if inspect.digest(p)!=h:raise ValueError('Evidence changed')
 receipt.update(plan_sha256=expected,extraction_result=result,schema_pilot_performed=False,canonical_conversion_approved=False)
 with (path.parent/'independent_extraction_receipt.json').open('x') as f:json.dump(receipt,f,indent=2)


def schema_worker(path,expected):
 resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,)*2)
 from contributor_tools.gt21_numeric_source import read_numeric_table
 path=Path(path);plan=json.loads(path.read_text())
 if inspect.digest(path)!=expected:raise ValueError('Plan changed')
 receipt_path=path.parent/'independent_extraction_receipt.json';receipt=json.loads(receipt_path.read_text());receipt_sha=inspect.digest(receipt_path)
 if receipt['plan_sha256']!=expected or receipt['status']!='all_extracted_bytes_independently_reread_unreviewed':raise ValueError('Independent extraction required')
 for p,h in plan['bindings'].items():
  if inspect.digest(p)!=h:raise ValueError('Bound schema code changed')
 results=[];root=Path(plan['extraction']['output_root'])/'files'
 manifest=root.parent/'member_manifest.jsonl'
 if inspect.digest(manifest)!=receipt['manifest_sha256']:raise ValueError('Extraction manifest changed')
 expected_members={r['member']:r for r in map(json.loads,manifest.read_text().splitlines())}
 for recording in plan['schema_pilot_candidates']:
  row={k:recording[k] for k in ('subject','date','mode','recording')};row['channels']={}
  for kind in ('ik','id','fp','gcLeft','gcRight'):
   if (path.parent/'STOP').exists():raise RuntimeError('STOP')
   member=recording['channels'][kind]['member'];source=root/member;before=inspect.digest(source)
   if before!=expected_members[member]['sha256']:raise ValueError('Extracted source changed since independent readback')
   try:
    columns=read_numeric_table(source,max_source_bytes=32*1024**2)
    info={'status':'supported_numeric_schema_finite_monotonic_header_checked','rows':len(columns['Header']),'columns':list(columns),'source_header_first':float(columns['Header'][0]),'source_header_last':float(columns['Header'][-1]),'clock_units':'unverified'}
   except ValueError as error:info={'status':'native_schema_review_required','reason':str(error)}
   if inspect.digest(source)!=before:raise ValueError('Schema source changed')
   info['sha256']=before;row['channels'][kind]=info
  row['conditions']='Native table/string label review required; not parsed by numeric-only reader';results.append(row)
 for p,h in plan['bindings'].items():
  if inspect.digest(p)!=h:raise ValueError('Bound schema code changed')
 if inspect.digest(manifest)!=receipt['manifest_sha256']:raise ValueError('Member manifest changed')
 for row in results:
  recording=next(r for r in plan['schema_pilot_candidates'] if all(r[k]==row[k] for k in ('subject','date','mode','recording')))
  for kind,info in row['channels'].items():
   if inspect.digest(root/recording['channels'][kind]['member'])!=info['sha256']:raise ValueError('Earlier schema source changed')
 if inspect.digest(path)!=expected or inspect.digest(receipt_path)!=receipt_sha:raise ValueError('Evidence changed')
 with (path.parent/'schema_pilot.json').open('x') as f:json.dump({'status':'v1_numeric_schema_feasibility_reported_unreviewed','scientific_approval':False,'canonical_conversion_approved':False,'plan_sha256':expected,'extraction_receipt_sha256':receipt_sha,'records':results},f,indent=2)


def process_rows():
 rows={}
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   fields=(p/'stat').read_text().rsplit(')',1)[1].split()
   rows[int(p.name)]={'start':fields[19],'parent':int(fields[1]),'state':fields[0]}
  except FileNotFoundError:continue
 return rows


def capture_tree(parent,owned,rows=None):
 rows=process_rows() if rows is None else rows
 # Validate every remembered identity before traversing any ancestry. A reused
 # intermediate PID must never lend its unrelated descendants to this guard.
 def check_existing(snapshot):
  for pid,identity in owned.items():
   if pid in snapshot and snapshot[pid]['start']!=identity['start']:
    raise RuntimeError('Owned PID reused')
 check_existing(rows)
 parent_row=rows.get(parent)
 if parent_row is None:raise RuntimeError('Guard parent identity unavailable')
 found={parent};parents={parent:parent_row['start']}
 while True:
  added={pid for pid,r in rows.items() if r['parent'] in found}-found
  if not added:break
  found.update(added)
  for pid in added:parents[pid]=rows[pid]['start']
 refreshed=process_rows();check_existing(refreshed)
 for pid,start in parents.items():
  if pid not in refreshed or refreshed[pid]['start']!=start or (pid!=parent and refreshed[pid]['parent']!=rows[pid]['parent']):raise RuntimeError('Ancestry changed before capture')
 pending={}
 try:
  for pid in sorted(found-{parent}):
   if pid not in owned:pending[pid]={'start':rows[pid]['start'],'fd':os.pidfd_open(pid)}
  final=process_rows();check_existing(final)
  for pid,start in parents.items():
   if pid not in final or final[pid]['start']!=start or (pid!=parent and final[pid]['parent']!=rows[pid]['parent']):raise RuntimeError('Ancestry changed during capture')
 except BaseException:
  for identity in pending.values():os.close(identity['fd'])
  raise
 owned.update(pending)


def send_owned(identity,sig):
 try:signal.pidfd_send_signal(identity['fd'],sig)
 except ProcessLookupError:pass


def cleanup_owned(child,owned):
 # This dedicated guard is a subreaper; escaped sessions reparent here.
 if child.pid in owned:send_owned(owned[child.pid],signal.SIGSTOP)
 capture_tree(os.getpid(),owned)
 for identity in owned.values():send_owned(identity,signal.SIGKILL)
 child.wait(timeout=10)
 deadline=time.monotonic()+10
 while time.monotonic()<deadline:
  capture_tree(os.getpid(),owned)
  for identity in owned.values():send_owned(identity,signal.SIGKILL)
  try:
   while os.waitpid(-1,os.WNOHANG)[0]:pass
  except ChildProcessError:return
  time.sleep(.05)
 raise RuntimeError('Owned child cleanup not proven')


def supervised(command,log,storage,timeout):
 import ctypes
 from contributor_tools.run_gt25_coverage_pilot import windows_available_mib,linux_available_mib
 libc=ctypes.CDLL(None,use_errno=True)
 if libc.prctl(36,1,0,0,0)!=0:raise OSError('Cannot establish child subreaper')
 if windows_available_mib()<3584 or linux_available_mib()<3584:raise MemoryError('Startup reserve')
 storage();child=None;owned={}
 def interrupted(*args):raise RuntimeError('Interrupted')
 previous={sig:signal.signal(sig,interrupted) for sig in (signal.SIGINT,signal.SIGTERM)}
 try:
  blocked=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
  try:
   child=subprocess.Popen(['ionice','-c3',*command],stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=lambda:signal.pthread_sigmask(signal.SIG_SETMASK,blocked))
   capture_tree(os.getpid(),owned)
   if child.pid not in owned:raise RuntimeError('Cannot establish child ownership')
  finally:signal.pthread_sigmask(signal.SIG_SETMASK,blocked)
  started=time.monotonic();last=0
  while child.poll() is None:
   capture_tree(os.getpid(),owned)
   if time.monotonic()-started>timeout:raise TimeoutError('Worker deadline')
   if time.monotonic()-last>15:
    storage()
    if windows_available_mib()<2048 or linux_available_mib()<2048:raise MemoryError('Runtime reserve')
    last=time.monotonic()
   time.sleep(.1)
  if child.returncode:raise RuntimeError('Worker failed; preserve artifacts')
 finally:
  for sig in previous:signal.signal(sig,signal.SIG_IGN)
  try:
   if child is not None:cleanup_owned(child,owned)
  finally:
   for identity in owned.values():os.close(identity['fd'])
   for sig,handler in previous.items():signal.signal(sig,handler)


def run(path,expected,schema=False):
 path=Path(path);plan=json.loads(path.read_text())
 if inspect.digest(path)!=expected:raise ValueError('Plan changed')
 def storage():
  if any((path.parent/n).exists() for n in ('STOP','STOP_AFTER_CURRENT')):raise RuntimeError('STOP')
  import shutil
  if shutil.disk_usage(Path(plan['extraction']['archive']).parent).free<inspect.RESERVE:raise MemoryError('Preserve15GiB reserve')
 for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
 with (path.parent/('schema_worker.log' if schema else 'worker.log')).open('x') as log:
  supervised(['nice','-n','19',sys.executable,__file__,'schema-worker' if schema else 'worker','--plan',str(path),'--plan-sha256',expected],log,storage,180 if schema else 7200)


def main():
 p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True);q=s.add_parser('prepare');q.add_argument('--output',type=Path,required=True)
 for mode in ('run','worker','schema-worker','run-schema'):
  q=s.add_parser(mode);q.add_argument('--plan',type=Path,required=True);q.add_argument('--plan-sha256',required=True)
 a=p.parse_args()
 if a.mode=='prepare':prepare(a.output)
 elif a.mode=='worker':worker(a.plan,a.plan_sha256)
 elif a.mode=='schema-worker':schema_worker(a.plan,a.plan_sha256)
 elif a.mode=='run-schema':run(a.plan,a.plan_sha256,schema=True)
 else:run(a.plan,a.plan_sha256)
if __name__=='__main__':main()
