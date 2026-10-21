"""Join existing GT24 full runners; source accounting never implies approval.

Prepare only after actual four corrected and two companion pilots. Execution
requires an external exclusive worker slot. Existing plans are never refreshed.
"""
import argparse,hashlib,json,os,resource,signal,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
BASE=ROOT/'converted_datasets/reconversion_v2'
from contributor_tools.run_gt24_full_reconstruction import digest,verify,merge,pilot_gate,headroom


def load(path):return json.loads(Path(path).read_text())
def keys(rows):
 result={(r['phase'],r['subject'],r['recording']) for r in rows}
 if len(result)!=len(rows):raise ValueError('Duplicate source identity')
 return result


def scope_gate(mapped,companions,inventory):
 parsed=[{**r,'phase':p['phase']} for p in inventory['phases'] for r in p['parsed_recordings']]
 native=[{**r,'phase':p['phase']} for p in inventory['phases'] for r in p['dynamic_complete_recordings']]
 if len(parsed)!=2421 or len(native)!=1358:raise ValueError('Original full scope differs')
 if keys(mapped['full_scope']['parsed'])!=keys(parsed) or keys(mapped['full_scope']['native'])!=keys(native):raise ValueError('Mapped plan original identity scope differs')
 only=[r for r in parsed if r['disposition']=='source_only_unmapped_task']
 if len(only)!=869 or len(parsed)-len(only)!=1552 or keys(companions['records'])!=keys(only):raise ValueError('Exact869 companion scope differs')
 return parsed,native


def companion_pilot_gate(receipt,plan):
 from contributor_tools.run_gt24_source_companion_batch import receipt_closure
 if receipt.get('status')!='two_phase_gt24_source_companion_pilots_checked_unreviewed' or receipt.get('scientific_approval') is not False or receipt.get('canonical_dataset_approval') is not False or receipt.get('full869_launched') is not False:raise ValueError('Actual companion pilots required')
 expected=keys([c['record'] for c in plan['cases']]);rows=receipt['records']
 if len(rows)!=2 or keys(rows)!=expected or len({r['phase'] for r in rows})!=2:raise ValueError('Exact two-phase pilot identities required')
 bindings={}
 for row in rows:
  case=next(c for c in plan['cases'] if keys([c['record']])==keys([row]))
  folder=Path(case['plan']).parent
  if digest(case['plan'])!=case['plan_sha256'] or row['report']!=str(folder/'source_readback.json') or row['artifact_hashes']!=receipt_closure(folder,case['record']):raise ValueError('Companion pilot output closure differs')
  merge(bindings,row['artifact_hashes'])
 return bindings


def prepare(mapped_path,companion_path,raw_pilot,companion_pilot,output):
 mapped_path,companion_path,raw_pilot,companion_pilot,output=map(lambda p:Path(p).resolve(),(mapped_path,companion_path,raw_pilot,companion_pilot,output))
 if output.exists() or not output.is_relative_to(BASE):raise ValueError('Fresh isolated coordinator root required')
 mapped,companion=load(mapped_path),load(companion_path);pilot_gate(load(raw_pilot))
 if str(raw_pilot) not in mapped['bindings'] or mapped['bindings'][str(raw_pilot)]!=digest(raw_pilot):raise ValueError('Full mapped plan not bound to actual four pilots')
 pp=companion_pilot.parent/'execution_plan.json';pilotplan=load(pp);receipt=load(companion_pilot)
 if receipt['plan_sha256']!=digest(pp):raise ValueError('Companion execution plan changed')
 bindings={};merge(bindings,mapped['bindings']);merge(bindings,companion['bindings']);merge(bindings,pilotplan['bindings']);merge(bindings,companion_pilot_gate(receipt,pilotplan))
 inventory=load(mapped['inventory']);scope_gate(mapped,companion,inventory)
 for p in [mapped_path,companion_path,raw_pilot,companion_pilot,pp,Path(__file__).resolve(),*[ROOT/'contributor_tools'/n for n in ['preserve_gt24_native_companion.py','audit_gt24_native_companion.py','run_gt24_full_reconstruction.py','run_gt24_source_companion_batch.py']]]:merge(bindings,{str(p):digest(p)})
 verify(bindings)
 for root in (mapped_path.parent,companion_path.parent):
  if (root/'attempt.json').exists():raise ValueError('Full runner already attempted; no implicit retry')
 plan={'status':'prepared_not_run','scientific_approval':False,'canonical_dataset_approval':False,'bindings':bindings,'mapped_plan':str(mapped_path),'companion_plan':str(companion_path),'inventory':mapped['inventory'],'output':str(output),'native_output':str(output/'native'),'disk_policy':'No total fit or compression ratio assumed. Existing per-record worst-case admission and5GiB reserves remain; insufficient disk stops incomplete.','excluded_archive_scope':[{'phase':p['phase'],'static_source_tables':p['static_source_tables'],'excluded_archive_entries':p['excluded_archive_entries']} for p in inventory['phases']]}
 output.mkdir();p=output/'plan.json';p.write_text(json.dumps(plan,indent=2)+'\n');return {'plan':str(p),'plan_sha256':digest(p)}


def closure(plan):
 return _closure(plan,2447)


def _closure(plan,candidate_count):
 from contributor_tools.run_gt24_source_companion_batch import receipt_closure
 mappedplan=load(plan['mapped_plan']);companionplan=load(plan['companion_plan']);inventory=load(plan['inventory']);parsed,native=scope_gate(mappedplan,companionplan,inventory)
 mr=Path(plan['mapped_plan']).parent;cr=Path(plan['companion_plan']).parent;nr=Path(plan['native_output']);mapped=load(mr/'status.json');companions=load(cr/'batch_status.json');nplan=load(nr/'plan.json');ns=load(nr/'native_summary.json')
 if mapped['status']!='all2421_scope_accounted_source_review_incomplete' or mapped['plan_sha256']!=digest(plan['mapped_plan']) or keys(mapped['records'])!=keys(parsed):raise ValueError('Incomplete mapped source accounting')
 if companions['status']!='all869_gt24_source_companions_lossless_readback_checked_unreviewed' or companions['plan_sha256']!=digest(plan['companion_plan']) or keys(companions['records'])!=keys(companionplan['records']):raise ValueError('Incomplete companion scope')
 if ns['status']!='all1358_native_recordings_lossless_source_preserved_unreviewed' or ns['plan_sha256']!=digest(nr/'plan.json') or keys([r['identity'] for r in ns['records']])!=keys(native):raise ValueError('Incomplete native scope')
 if ns['excluded_archive_scope']!=plan['excluded_archive_scope'] or nplan['excluded_archive_scope']!=plan['excluded_archive_scope']:raise ValueError('Original static/nonCSV exclusions lost')
 for result in (mapped,companions,ns):
  if result.get('scientific_approval') is not False:raise ValueError('Unexpected scientific approval')
 bindings={}
 for row in mapped['records']:
  if row['status'] in ('corrected_raw_source_fields_checked_unreviewed','corrected_raw_source_partial_unassessed'):
   from contributor_tools.run_gt24_full_reconstruction import checked_record
   folder=mr/'mapped'/row['phase']/row['subject']/row['recording']
   if Path(row['report'])!=folder/'raw_source.json':raise ValueError('Transplanted mapped report path')
   record=load(folder/'plan.json')['records'][0]
   original=next(r for r in parsed if keys([r])==keys([row]))
   if keys([record])!=keys([row]) or record['files']!=original['files'] or original['disposition']!='canonical_parsed_candidate_requires_source_audit':raise ValueError('Mapped record differs from original source identity')
   actual,hashes=checked_record(folder,record)
   if keys([actual])!=keys([row]):raise ValueError('Readback report identity differs')
   if actual['status']!=row['status'] or hashes!=row['receipt_hashes'] or digest(row['report'])!=row['report_sha256']:raise ValueError('Mapped independent receipt closure differs')
  elif row['status'] not in ('source_only_preservation_pending','blocked_nonunique_source_membership','record_execution_incomplete'):raise ValueError('Unknown mapped disposition')
  merge(bindings,row.get('receipt_hashes',{}))
 candidate_hashes=candidate_receipt_closure(mr/'membership/plan.json',mapped['candidate_reports'],candidate_count)
 merge(bindings,candidate_hashes)
 for row in companions['records']:
  original=next(r for r in companionplan['records'] if keys([r])==keys([row]));actual=receipt_closure(Path(row['report']).parent,original)
  if actual!=row['artifact_hashes']:raise ValueError('Companion closure changed')
  merge(bindings,actual)
 native_hashes=native_receipt_closure(nr,nplan,ns,native)
 if native_hashes!=ns['artifact_hashes']:raise ValueError('Native aggregate closure differs')
 merge(bindings,native_hashes);merge(bindings,nplan['bindings'])
 for p in [mr/'status.json',cr/'batch_status.json',nr/'plan.json',nr/'native_summary.json',Path(mapped['native_residual_summary'])]:merge(bindings,{str(p):digest(p)})
 if digest(mapped['native_residual_summary'])!=mapped['native_residual_summary_sha256']:raise ValueError('Residual source ledger changed')
 verify(bindings);verify(plan['bindings'])
 unresolved=[r for r in mapped['records'] if r['status'] not in ('source_only_preservation_pending','corrected_raw_source_fields_checked_unreviewed')]
 return {'status':'all_original_scope_accounted_with_explicit_scientific_gaps','scientific_approval':False,'canonical_dataset_approval':False,'parsed_records':2421,'mapped_records':1552,'source_companions':869,'native_records':1358,'unresolved_mapped_records':unresolved,'excluded_archive_scope':plan['excluded_archive_scope'],'unresolved_parsed_membership':ns['unresolved_parsed_membership'],'bindings':bindings,'limitations':['Native wholeCSV preservation retains transitions; interval matching does not establish canonical anatomy.','Static/nonCSV source entries remain original archive references, not exported measurements.','Unknown source units, mass denominators, unavailable fields and ambiguous memberships remain unassessed.']}


def candidate_receipt_closure(planpath,rows,expected):
 from contributor_tools.run_gt24_full_reconstruction import verify_membership_sources
 plan=load(planpath)
 if len(plan['jobs'])!=expected or len(rows)!=expected or {r['index'] for r in rows}!=set(range(expected)):raise ValueError('All candidate receipts required')
 result={str(planpath):digest(planpath)}
 for row in rows:
  path=planpath.parent/'records'/f"{row['index']:06d}.json"
  if row['path']!=str(path) or digest(path)!=row['sha256']:raise ValueError('Candidate receipt path/hash differs')
  report=load(path)
  if row['status']!=report['status']:raise ValueError('Candidate disposition differs')
  verify_membership_sources(planpath,row['index'],path)
  result[str(path)]=row['sha256']
 return result


def native_receipt_closure(root,plan,summary,original):
 from contributor_tools.audit_gt24_native_companion import coverage
 if keys(plan['records'])!=keys(original):raise ValueError('Native plan differs from original identities')
 result={};summaryrows={tuple(r['identity'][k] for k in ('phase','subject','recording')):r for r in summary['records']}
 for index,record in enumerate(plan['records']):
  folder=root/'records'/f'{index:06d}';path=folder/'source_readback.json';report=load(path);identity={k:record[k] for k in ('phase','subject','recording','source_recording_id')}
  row=summaryrows[tuple(record[k] for k in ('phase','subject','recording'))]
  if row['report']!=str(path) or row['sha256']!=digest(path) or row['identity']!=identity:raise ValueError('Native summary report identity differs')
  if report['status']!='whole_native_csv_members_independently_byte_checked_unreviewed' or report['scientific_approval'] is not False or report['canonical_dataset_approval'] is not False or report['plan_sha256']!=digest(root/'plan.json') or report['record_index']!=index or report['identity']!=identity:raise ValueError('Native per-record audit differs')
  source=next(r for r in original if keys([r])==keys([record]))
  if record['members']!=source['members']:raise ValueError('Native plan original member scope differs')
  streams=report['streams']
  if len(streams)!=len(record['members']) or {s['member'] for s in streams}!={x['name'] for x in record['members']} or row['streams']!=len(streams):raise ValueError('Native member coverage differs')
  artifacts={}
  for stream in streams:
   if stream['literal_native_bytes_equal'] is not True or Path(stream['compressed']).name!=stream['compressed'] or stream['coverage']!=coverage(record,stream['member'],stream['rows'],stream['source_sha256'],plan['kind_to_native_filename']):raise ValueError('Native original coverage receipt differs')
   artifacts[str(folder/stream['compressed'])]=stream['compressed_sha256']
  if artifacts!=report['artifact_hashes']:raise ValueError('Native per-record output closure differs')
  merge(result,artifacts);merge(result,{str(path):digest(path),str(folder/'preservation.json'):report['preservation_sha256']})
 verify(result);return result


def processes():
 rows={}
 for path in Path('/proc').iterdir():
  if not path.name.isdigit():continue
  try:
   stat=(path/'stat').read_text().rsplit(')',1)[1].split();rows[int(path.name)]={'start':stat[19],'ppid':int(stat[1]),'pgid':int(stat[2]),'state':stat[0]}
  except FileNotFoundError:continue
 return rows


def descendants(pid,rows):
 owned={pid};prior=None
 while prior!=owned:
  prior=set(owned);owned.update(p for p,r in rows.items() if r['ppid'] in owned)
 return {p:rows[p] for p in owned if p in rows}


def cleanup(child,owned):
 handlers={s:signal.signal(s,signal.SIG_IGN) for s in (signal.SIGINT,signal.SIGTERM)}
 try:
  current=processes()
  if child.pid in owned and current.get(child.pid,{}).get('start')==owned[child.pid]['start']:
   try:os.kill(child.pid,signal.SIGSTOP)
   except ProcessLookupError:pass
   capture_owned(child,owned,processes())
  for pid,row in sorted(owned.items(),key=lambda pair:pair[0]==child.pid):
   current=processes().get(pid,{})
   if current.get('start')!=row['start'] or current.get('state')=='Z':continue
   try:os.killpg(pid,signal.SIGKILL) if current.get('pgid')==pid else os.kill(pid,signal.SIGKILL)
   except ProcessLookupError:pass
  child.wait(timeout=15)
  deadline=time.monotonic()+15
  while True:
   current=processes();alive=[p for p,r in owned.items() if current.get(p,{}).get('start')==r['start'] and current[p]['state']!='Z']
   if not alive:break
   if time.monotonic()>deadline:raise RuntimeError('Owned workers still alive; external controller must remain held')
   time.sleep(.1)
 finally:
  for sig,handler in handlers.items():signal.signal(sig,handler)


def capture_owned(child,owned,rows):
 """Never adopt descendants of a reused parent PID or overwrite old identity."""
 parent=owned.get(child.pid)
 if not parent or rows.get(child.pid,{}).get('start')!=parent['start']:return
 for pid,row in descendants(child.pid,rows).items():
  if pid not in owned or owned[pid]['start']==row['start']:owned[pid]=row


def runtime_gate(root,started,begin=None,timeout=None,check_headroom=False):
 now=time.monotonic()
 if (root/'STOP').exists() or (root/'STOP_AFTER_CURRENT').exists():raise RuntimeError('Coordinator stop requested')
 if now-started>90*24*3600:raise TimeoutError('Whole90day deadline expired')
 if begin is not None and now-begin>timeout:raise TimeoutError('Stage deadline expired')
 if check_headroom:headroom(root,False)


def closure_worker(path,sha):
 """Long source/archive rereads belong to a monitored bounded subprocess."""
 path=Path(path).resolve()
 if digest(path)!=sha:raise ValueError('Coordinator plan changed')
 plan=load(path);verify(plan['bindings']);result=closure(plan)
 if digest(path)!=sha:raise ValueError('Coordinator plan changed during closure')
 result['coordinator_plan_sha256']=sha
 with (path.parent/'summary.json').open('x') as stream:json.dump(result,stream,indent=2)


def run(path,sha):
 path=Path(path).resolve();root=path.parent;plan=load(path)
 if digest(path)!=sha or plan['output']!=str(root):raise ValueError('Bound coordinator plan required')
 state={'status':'running','scientific_approval':False,'stages':[]};started=time.monotonic()
 def stop(*args):raise RuntimeError('Coordinator interrupted')
 previous={s:signal.signal(s,stop) for s in (signal.SIGINT,signal.SIGTERM)}
 def save():
  p=root/'status.tmp';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(root/'status.json')
 def worker(label,args,timeout):
  runtime_gate(root,started)
  if digest(path)!=sha:raise ValueError('Coordinator plan changed')
  headroom(root,True);env=dict(os.environ);env.pop('PYTHONOPTIMIZE',None)
  for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):env[k]='1'
  with (root/(label+'.log')).open('x') as log:
   def cap():resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
   child=subprocess.Popen(['nice','-n','19','ionice','-c','3',sys.executable,*map(str,args)],cwd=ROOT,env=env,start_new_session=True,preexec_fn=cap,stdout=log,stderr=subprocess.STDOUT)
   rows=processes();owned={child.pid:rows[child.pid]} if child.pid in rows else {};capture_owned(child,owned,rows);begin=last=time.monotonic()
   try:
    while child.poll() is None:
     capture_owned(child,owned,processes())
     now=time.monotonic();runtime_gate(root,started,begin,timeout,now-last>15)
     if now-last>15:last=now
     time.sleep(.1)
    runtime_gate(root,started,begin,timeout)
    if child.returncode:raise RuntimeError(label+' failed; preserve attempt')
   finally:cleanup(child,owned)
 def stage(label,args,timeout):
  # Even dependency hashes can include large sources: never scan them in the
  # supervising coordinator while its periodic guard is suspended.
  worker(label+'_bindings',[Path(__file__).resolve(),'verify-bindings','--plan',path,'--plan-sha256',sha],3600)
  worker(label,args,timeout)
  state['stages'].append(label);save()

 try:
  with (root/'attempt.json').open('x') as stream:json.dump({'plan_sha256':sha},stream)
  save()
  for label,tool,key in [('mapped','run_gt24_full_reconstruction.py','mapped_plan'),('companions','run_gt24_source_companion_batch.py','companion_plan')]:
   p=Path(plan[key]);stage(label,[ROOT/'contributor_tools'/tool,'run','--plan',p,'--plan-sha256',digest(p)],30*24*3600+60)
  mp=Path(plan['mapped_plan']).parent/'membership/plan.json';native=Path(plan['native_output'])
  stage('native_prepare',[ROOT/'contributor_tools/preserve_gt24_native_companion.py','prepare','--membership-plan',mp,'--coverage-summary',mp.parent/'coverage_summary.json','--output',native],3600)
  np=native/'plan.json';nh=digest(np)
  if len(load(np)['records'])!=1358:raise ValueError('Native plan scope')
  for index in range(1358):
   stage(f'native_{index:04d}_preserve',[ROOT/'contributor_tools/preserve_gt24_native_companion.py','run','--plan',np,'--plan-sha256',nh,'--record-index',index],3660)
   stage(f'native_{index:04d}_audit',[ROOT/'contributor_tools/audit_gt24_native_companion.py','--plan',np,'--plan-sha256',nh,'--record-index',index],3660)
  stage('native_summary',[ROOT/'contributor_tools/audit_gt24_native_companion.py','--plan',np,'--plan-sha256',nh,'--summarize'],24*3600+60)
  stage('final_closure',[Path(__file__).resolve(),'final-closure','--plan',path,'--plan-sha256',sha],7*24*3600)
  runtime_gate(root,started,check_headroom=True)
  result=load(root/'summary.json')
  if digest(path)!=sha or result.get('coordinator_plan_sha256')!=sha or result.get('scientific_approval') is not False or result.get('canonical_dataset_approval') is not False or result.get('status')!='all_original_scope_accounted_with_explicit_scientific_gaps':raise ValueError('Final closure receipt does not bind this unapproved scope')
  state.update(status=result['status'],summary_sha256=digest(root/'summary.json'))
 except BaseException as error:state.update(status='stopped_incomplete',reason=str(error));raise
 finally:
  save()
  for sig,handler in previous.items():signal.signal(sig,handler)


def main():
 p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True);q=s.add_parser('prepare')
 for name in ('mapped-plan','companion-plan','raw-pilot','companion-pilot','output'):q.add_argument('--'+name,type=Path,required=True)
 for mode in ('run','verify-bindings','final-closure'):
  q=s.add_parser(mode);q.add_argument('--plan',type=Path,required=True);q.add_argument('--plan-sha256',required=True)
 a=p.parse_args()
 if a.mode=='prepare':print(json.dumps(prepare(a.mapped_plan,a.companion_plan,a.raw_pilot,a.companion_pilot,a.output)))
 elif a.mode=='run':run(a.plan,a.plan_sha256)
 else:
  if sys.flags.optimize:raise ValueError('Independent source auditors require assertions')
  resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
  if digest(a.plan)!=a.plan_sha256:raise ValueError('Bound coordinator plan required')
  if a.mode=='verify-bindings':verify(load(a.plan)['bindings'])
  else:closure_worker(a.plan,a.plan_sha256)
if __name__=='__main__':main()
