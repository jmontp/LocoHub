"""Explicit serial GT24 reconstruction, preserving exact full-scope accounting.

Preparation requires four actual independent pilot readbacks. This tool does not
own a shared numerical slot; an external coordinator must hold that slot. No
implicit retries or overwrites. Unmapped/native residual scope is never approved.
"""
import argparse,ast,hashlib,json,os,resource,shutil,signal,subprocess,sys,time,zipfile
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
BASE=ROOT/'converted_datasets/reconversion_v2'


def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
 return h.hexdigest()


def verify(bindings):
 for path,sha in bindings.items():
  if digest(path)!=sha:raise ValueError('Bound full-run prerequisite changed: '+path)


def merge(bindings,extra):
 for path,sha in extra.items():
  if path in bindings and bindings[path]!=sha:raise ValueError('Conflicting frozen binding: '+path)
  bindings[path]=sha


def pilot_gate(receipt):
 if receipt.get('status')!='four_gt24_raw_audits_source_checked_unreviewed' or receipt.get('scientific_approval') is not False or receipt.get('full_adoption_allowed') is not False:raise ValueError('Four actual nonpartial raw pilot readbacks required; partial is not full admission')
 records=receipt.get('records',[])
 if len(records)!=4 or {(r['case'],r['index']) for r in records}!={(c,i) for c in ('known','unknown') for i in (0,1)}:raise ValueError('Exact four-pilot scope required')


def classify_reports(membership,reports):
 if len(reports)!=len(membership['jobs']):raise ValueError('All candidate results required')
 grouped=defaultdict(list)
 for index,(job,report) in enumerate(zip(membership['jobs'],reports)):
  if report.get('job_index')!=index or any(report.get(k)!=job[k] for k in ('phase','subject','parsed_recording','native_recording')):raise ValueError('Candidate identity differs')
  status=report.get('status');matched=report.get('membership_verified')
  if status not in ('native_parsed_candidate_checked_unreviewed','native_parsed_candidate_rejected') or matched is not (status=='native_parsed_candidate_checked_unreviewed'):raise ValueError('Nonterminal/contradictory candidate result')
  key=(job['phase'],job['subject'],job['parsed_recording']);grouped[key]
  if matched:grouped[key].append(index)
 return {key:{'status':'unique_membership' if len(indices)==1 else 'ambiguous_membership' if indices else 'no_matching_membership','positive_indices':indices} for key,indices in grouped.items()}


def verify_membership_sources(planpath,index,reportpath):
 """Revalidate reused positive AND negative receipts against current source bytes."""
 from contributor_tools.prepare_gt24_complete_membership import stat_identity,checked_report_intervals
 plan_sha=digest(planpath);report_sha=digest(reportpath)
 plan=json.loads(Path(planpath).read_text());verify(plan['bindings'])
 report=json.loads(Path(reportpath).read_text());job=plan['jobs'][index]
 if report.get('plan_sha256')!=digest(planpath) or report.get('job_index')!=index:raise ValueError('Membership receipt binding differs')
 classify_reports({'jobs':[job]},[{**report,'job_index':0}])
 if report.get('scientific_approval') is not False or set(report['tables'])!={t['kind'] for t in job['tables']}:raise ValueError('Membership table scope differs')
 if report['membership_verified']:checked_report_intervals(report)
 archive=Path(job['archive']['path']);before=stat_identity(archive)
 if any(before[k]!=job['archive'][k] for k in ('path','bytes','mtime_ns')):raise ValueError('Native archive identity changed')
 with zipfile.ZipFile(archive) as z:
  for table in job['tables']:
   member=table['member'];info=z.getinfo(member['name'])
   if (info.file_size,info.compress_size,info.CRC,info.header_offset)!=(member['bytes'],member['compressed_bytes'],member['crc32'],member['header_offset']):raise ValueError('Native member identity changed')
   parsed=table['parsed'];result=report['tables'][table['kind']]
   if stat_identity(parsed['path'])!=parsed:raise ValueError('Parsed identity changed')
   if digest(parsed['path'])!=result['parsed']['full_csv_sha256']:raise ValueError('Parsed receipt bytes changed')
   h=hashlib.sha256()
   with z.open(info) as stream:
    for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
   if h.hexdigest()!=result['native']['full_csv_sha256']:raise ValueError('Native receipt bytes changed')
   if stat_identity(parsed['path'])!=parsed:raise ValueError('Parsed changed during verification')
 if stat_identity(archive)!=before:raise ValueError('Native changed during verification')
 verify(plan['bindings'])
 if digest(planpath)!=plan_sha or digest(reportpath)!=report_sha:raise ValueError('Membership evidence changed during verification')


def checked_record(folder,record):
 """Require actual producer, preservation AND raw-source receipts, not exit codes."""
 folder=Path(folder);rp=folder/'plan.json';sha=digest(rp);out=folder/'record_0/continuous.parquet';reference=Path(record['reference_output'])
 output_sha=digest(out);reference_sha=digest(reference);receipts={str(out):output_sha,str(reference):reference_sha,str(rp):sha,str(folder/'admission.json'):digest(folder/'admission.json')}
 for name,status in [('baseline','bounded_parsed_continuous_export_unverified'),('export','participant_normalization_export_unverified'),('audit','participant_normalization_independent_readback_checked_unreviewed')]:
  path=folder/'record_0'/(name+'.json');receipt=json.loads(path.read_text());receipts[str(path)]=digest(path)
  expected=reference_sha if name=='baseline' else output_sha
  if receipt.get('status')!=status or receipt.get('scientific_approval') is not False or receipt.get('plan_sha256')!=sha or receipt.get('output_sha256')!=expected:raise ValueError('Producer/preservation receipt differs: '+name)
  if name=='audit':
   if receipt.get('all_unrelated_values_field_metadata_null_masks_exact') is not True or receipt.get('reference_sha256')!=reference_sha:raise ValueError('Exact preservation not proved')
   rows=receipt['rows']
 report=json.loads((folder/'raw_source.json').read_text());receipts[str(folder/'raw_source.json')]=digest(folder/'raw_source.json')
 if report.get('status') not in ('corrected_raw_source_fields_checked_unreviewed','corrected_raw_source_partial_unassessed') or report.get('scientific_approval') is not False or report.get('plan_sha256')!=sha or report.get('output_sha256')!=output_sha:raise ValueError('Raw receipt provenance differs')
 if report.get('bound_producer_policy')!='gt24_participant_mass_missingness_v2' or any(report.get(k)!=record[k] for k in ('phase','subject','recording')):raise ValueError('Raw producer/record identity differs')
 if rows<=0 or report.get('rows')!=rows:raise ValueError('Readback row coverage differs')
 for name in ('baseline','export'):
  if json.loads((folder/'record_0'/(name+'.json')).read_text()).get('rows')!=rows:raise ValueError('Producer row coverage differs')
 expected_sources=set(record['files']) & {'angle_filt','velocity','moment_filt','moment_filt_bio','grf','insole_sim','exo'}
 if set(report['source_sha256'])!=expected_sources:raise ValueError('Raw source scope differs')
 for kind,source_sha in report['source_sha256'].items():
  if digest(record['files'][kind]['path'])!=source_sha:raise ValueError('Raw source changed after readback')
 return report,receipts


def cleanup_owned(child):
 # A leader can exit before its descendants. The new session remains ours.
 try:os.killpg(child.pid,signal.SIGKILL)
 except ProcessLookupError:pass
 child.wait(timeout=10)


def archetypes(path):
 tree=ast.parse(Path(path).read_text())
 for node in tree.body:
  if isinstance(node,ast.AnnAssign) and isinstance(node.target,ast.Name) and node.target.id=='TASK_ARCHETYPE_MAP':
   if not isinstance(node.value,ast.Dict):raise ValueError('Unexpected archetype declaration')
   return {ast.literal_eval(k):v.attr=='GAIT' for k,v in zip(node.value.keys,node.value.values) if isinstance(v,ast.Attribute)}
 raise ValueError('Bound task archetypes absent')


def prepare(pilot_path,output):
 output=Path(output).resolve();pilot_path=Path(pilot_path).resolve()
 if output.exists() or not output.is_relative_to(BASE):raise ValueError('Fresh isolated full output required')
 pilot=json.loads(pilot_path.read_text());pilot_gate(pilot)
 bindings={str(pilot_path):digest(pilot_path)}
 for row in pilot['records']:
  rp=Path(row['report'])
  if digest(rp)!=row['report_sha256']:raise ValueError('Pilot raw receipt changed')
  report=json.loads(rp.read_text());ap=rp.parent/'plan.json';auditplan=json.loads(ap.read_text())
  if report.get('status')!='corrected_raw_source_fields_checked_unreviewed' or report.get('entirely_unassessed_features') or report.get('plan_sha256')!=digest(ap):raise ValueError('Partial or unbound pilot evidence')
  merge(bindings,auditplan['bindings']);merge(bindings,{str(rp):digest(rp),str(ap):digest(ap)})
 source=BASE/'gt24_complete_membership_v2_20261021/plan.json';membership=json.loads(source.read_text());merge(bindings,membership['bindings']);bindings[str(source)]=digest(source)
 inventory=Path(membership['inventory']);matrix=BASE/'gt24_source_mass_coverage_v4_20261021/matrix.json';unknown=BASE/'gt24_unknown_mass_pilot_20261021/plan.json';template=json.loads(unknown.read_text());merge(bindings,template['bindings'])
 from contributor_tools.audit_gt24_corrected_raw_source import unit_evidence
 mass_metadata=json.loads(matrix.read_text())
 unit_evidence(Path(mass_metadata['source_metadata']['readme']['path']).read_text())
 from contributor_tools.plan_gt24_full_reconstruction import classify
 scope=classify(json.loads(inventory.read_text()),json.loads(matrix.read_text()),membership)
 if scope['counts']['parsed']!=2421 or scope['counts']['native']!=1358 or len(membership['jobs'])!=2447 or scope['counts']['task_dispositions'].get('source_only_unmapped_task')!=869:raise ValueError('Full source scope changed')
 adapter=Path(template['corrected_adapter']);registry=adapter.parents[2]/'common/stride_segmentation.py';tasks=archetypes(registry)
 for p in [Path(__file__).resolve(),inventory,matrix,unknown,registry,*[ROOT/'contributor_tools'/n for n in ('audit_gt24_corrected_raw_source.py','plan_gt24_full_reconstruction.py','prepare_gt24_unknown_mass_pilot.py','apply_gt24_participant_normalization_v2.py')]]:merge(bindings,{str(p):digest(p)})
 verify(bindings)
 plan={'status':'prepared_not_run','scientific_approval':False,'bindings':bindings,'membership_original':str(source),'inventory':str(inventory),'mass_matrix':str(matrix),'corrected_adapter':str(adapter),'task_archetypes':tasks,'output_root':str(output),'full_scope':scope,'policy':'Unknown participant/model values remain absent; no verified source moment denominator; all unverified canonical moments/interaction torques withheld.','stage_timeout_seconds':3600,'whole_run_timeout_seconds':30*24*3600}
 output.mkdir();(output/'membership').mkdir();shutil.copyfile(source,output/'membership/plan.json');(output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
 return {'plan':str(output/'plan.json'),'plan_sha256':digest(output/'plan.json'),'membership_jobs':2447,'mapped_recordings':1552,'source_only_recordings':869}


def record_admission(plan,membership,job_index,source_record,root):
 from contributor_tools.gt24_source_mass import collect_metadata,resolve_mass
 from contributor_tools.gt24_mass_field_policy import participant_mass
 from contributor_tools.prepare_gt24_complete_membership import checked_report_intervals
 matrix=json.loads(Path(plan['mass_matrix']).read_text());inventory=json.loads(Path(plan['inventory']).read_text())
 fresh=collect_metadata(inventory,Path(matrix['source_metadata']['readme']['path']))
 if fresh!=matrix['source_metadata']:raise ValueError('Current mass metadata differs')
 job=membership['jobs'][job_index];path=root/'membership/records'/f'{job_index:06d}.json';report=json.loads(path.read_text())
 if not checked_report_intervals(report):raise ValueError('Empty membership intervals')
 if report['plan_sha256']!=digest(root/'membership/plan.json'):raise ValueError('Membership plan mismatch')
 if set(report['tables'])!={t['kind'] for t in job['tables']}:raise ValueError('Missing matched source tables')
 hashes={str(path):digest(path)}
 for table in job['tables']:
  p=table['parsed']['path'];h=digest(p)
  if report['tables'][table['kind']]['parsed']['full_csv_sha256']!=h:raise ValueError('Matched Parsed source changed')
  hashes[p]=h
 record=dict(source_record);mass=participant_mass(fresh,record['phase'],record['subject'])
 try:model=resolve_mass(fresh,record['phase'],record['subject'],record['exo_state'],native_trial=job['native_recording'])
 except ValueError as error:model={'source_model_mass_kg':None,'mass_basis':'unresolved_source_metadata','model_id':None,'unresolved_reason':str(error)}
 if record['task'] not in plan['task_archetypes']:raise ValueError('No explicit bound task archetype; do not default to gait')
 record.update(participant_mass=mass,model_mass=model,mass_evidence_sha256=digest(plan['mass_matrix']),verified_source_denominator=None,membership_index=job_index,native_name_candidates_only=[job['native_recording']],is_gait=plan['task_archetypes'][record['task']])
 return record,hashes


def worker(planpath,stage):
 resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
 import pyarrow as pa
 pa.set_cpu_count(1);pa.set_io_thread_count(1)
 if stage!='raw':
  from contributor_tools.prepare_gt24_unknown_mass_pilot import worker as original_worker
  original_worker(planpath,0,stage);return
 from contributor_tools.audit_gt24_corrected_raw_source import audit
 original_sha=digest(planpath)
 p=json.loads(planpath.read_text());ad=json.loads((planpath.parent/'admission.json').read_text());verify(p['bindings']);verify(ad['membership_hashes'])
 if ad['plan_sha256']!=digest(planpath):raise ValueError('Actual record admission changed')
 last_check=[0.]
 def guard():
  if time.monotonic()-last_check[0]>=15:headroom(planpath.parent,False);last_check[0]=time.monotonic()
 result=audit(p['records'][0],planpath.parent/'record_0/continuous.parquet',guard);verify(p['bindings']);verify(ad['membership_hashes'])
 if digest(planpath)!=original_sha:raise ValueError('Record plan changed during raw audit')
 result['plan_sha256']=original_sha
 with (planpath.parent/'raw_source.json').open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False)


def headroom(folder,startup):
 from contributor_tools.preserve_mblue_planar_estimates import headroom as common,windows_available_mib
 common(folder)
 linux=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))//1024
 if linux<(3584 if startup else 2048) or windows_available_mib()<(2816 if startup else 2048):raise MemoryError('Full worker memory headroom insufficient')
 if shutil.disk_usage(folder).free<5*1024**3:raise MemoryError('Preserve5GiB disk reserve')


def _run(planpath,expected):
 root=planpath.parent;plan=json.loads(planpath.read_text())
 if digest(planpath)!=expected or plan['output_root']!=str(root):raise ValueError('Plan/path differs')
 verify(plan['bindings'])
 with (root/'attempt.json').open('x') as stream:json.dump({'plan_sha256':expected},stream)
 state={'status':'running','scientific_approval':False,'full_adoption_allowed':False,'plan_sha256':expected,'candidate_reports':[],'records':[]};started=time.monotonic()
 def save():
  temp=root/'status.tmp';temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(root/'status.json')
 def stop():
  if (root/'STOP').exists() or (root/'STOP_AFTER_CURRENT').exists():raise RuntimeError('Coordinator stop requested')
  if time.monotonic()-started>plan['whole_run_timeout_seconds']:raise TimeoutError('Finite full-run30day timeout')
 def stage(cmd,label,timeout=3600):
  stop();verify(plan['bindings'])
  if digest(planpath)!=expected or digest(root/'membership/plan.json')!=digest(plan['membership_original']):raise ValueError('Execution plan changed')
  headroom(root,True)
  env=dict(os.environ);env.pop('PYTHONOPTIMIZE',None)
  for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):env[key]='1'
  with (root/(label+'.log')).open('x') as log:
   def cap():resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
   child=subprocess.Popen(['nice','-n','19','ionice','-c','3',*cmd],env=env,cwd=ROOT,start_new_session=True,stdout=log,stderr=subprocess.STDOUT,preexec_fn=cap);last=begin=time.monotonic()
   try:
    while child.poll() is None:
     if (root/'STOP').exists():raise RuntimeError('Immediate coordinator stop')
     if time.monotonic()-begin>timeout:raise TimeoutError('Stage timeout')
     if time.monotonic()-last>15:headroom(root,False);last=time.monotonic()
     time.sleep(.25)
    return child.returncode
   finally:
    cleanup_owned(child)
 membership_path=root/'membership/plan.json';membership=json.loads(membership_path.read_text())
 try:
  save()
  for index in range(len(membership['jobs'])):
   path=root/'membership/records'/f'{index:06d}.json'
   # Reuse only actual immutable original receipts with matching full plan.
   old=Path(plan['membership_original']).parent/'records'/path.name
   if old.exists():
    report=json.loads(old.read_text())
    if report.get('plan_sha256')!=digest(membership_path) or report.get('job_index')!=index:raise ValueError('Existing candidate receipt differs')
    path.parent.mkdir(exist_ok=True);shutil.copyfile(old,path)
    if stage([sys.executable,str(Path(__file__).resolve()),'verify-membership','--plan',str(membership_path),'--index',str(index),'--report',str(path)],f'membership_reuse_{index:06d}',1860):raise ValueError('Reused membership source bytes no longer verified')
   elif stage([sys.executable,str(ROOT/'contributor_tools/prepare_gt24_complete_membership.py'),'--output-root',str(membership_path.parent),'--record-index',str(index)],f'membership_{index:06d}',1860):raise RuntimeError('Membership worker incomplete; preserve failure')
   report=json.loads(path.read_text());state['candidate_reports'].append({'index':index,'path':str(path),'sha256':digest(path),'status':report['status']});save()
  reports=[json.loads(Path(row['path']).read_text()) for row in state['candidate_reports']];resolved=classify_reports(membership,reports)
  if stage([sys.executable,str(ROOT/'contributor_tools/prepare_gt24_complete_membership.py'),'--output-root',str(membership_path.parent),'--summarize'],'membership_summary'):raise RuntimeError('Native residual accounting incomplete')
  inventory=json.loads(Path(plan['inventory']).read_text());matrix=json.loads(Path(plan['mass_matrix']).read_text());mass_lookup={(r['phase'],r['subject'],r['recording']):r for r in matrix['parsed_recordings']}
  for phase in inventory['phases']:
   for source in phase['parsed_recordings']:
    stop();key=(phase['phase'],source['subject'],source['recording']);entry={'phase':key[0],'subject':key[1],'recording':key[2],'scientific_approval':False}
    if source['disposition']=='source_only_unmapped_task':entry.update(status='source_only_preservation_pending',reason='No canonical task invented; all supplied streams retained in source inventory')
    elif resolved.get(key,{}).get('status')!='unique_membership':entry.update(status='blocked_nonunique_source_membership',membership=resolved.get(key))
    else:
     folder=root/'mapped'/key[0]/key[1]/key[2];folder.mkdir(parents=True,exist_ok=False)
     record,hashes=record_admission(plan,membership,resolved[key]['positive_indices'][0],{**source,'phase':key[0],'exo_state':mass_lookup[key]['exo_state']},root)
     record['reference_output']=str(folder/'record_0/baseline_unreviewed.parquet')
     rp=folder/'plan.json';rp.write_text(json.dumps({'records':[record],'bindings':plan['bindings'],'corrected_adapter':plan['corrected_adapter']},indent=2)+'\n');(folder/'admission.json').write_text(json.dumps({'plan_sha256':digest(rp),'membership_hashes':hashes})+'\n')
     failed=None
     for action in ('baseline','export','audit','raw'):
      if stage([sys.executable,str(Path(__file__).resolve()),'worker','--plan',str(rp),'--stage',action],f"mapped_{len(state['records']):04d}_{action}"):failed=action;break
     if failed:entry.update(status='record_execution_incomplete',failed_stage=failed,artifact=str(folder))
     else:
      report,receipt_hashes=checked_record(folder,record)
      entry['receipt_hashes']=receipt_hashes
      entry.update(status=report['status'],report=str(folder/'raw_source.json'),report_sha256=digest(folder/'raw_source.json'),rows=report['rows'])
    state['records'].append(entry);save()
  if len(state['records'])!=2421:raise ValueError('Incomplete Parsed record accounting')
  verify(plan['bindings'])
  verify({r['path']:r['sha256'] for r in state['candidate_reports']})
  for entry in state['records']:verify(entry.get('receipt_hashes',{}))
  if digest(membership_path)!=digest(plan['membership_original']):raise ValueError('Copied membership plan changed')
  if digest(planpath)!=expected:raise ValueError('Full plan changed during execution')
  state.update(status='all2421_scope_accounted_source_review_incomplete',native_residual_summary=str(root/'membership/coverage_summary.json'),native_residual_summary_sha256=digest(root/'membership/coverage_summary.json'),unmapped_source_preservation_pending=869)
 except BaseException as error:state.update(status='stopped_incomplete',reason=str(error));raise
 finally:save()


def run(planpath,expected):
 def interrupted(signum,frame):raise RuntimeError('Coordinator interrupted: '+str(signum))
 previous={sig:signal.getsignal(sig) for sig in (signal.SIGTERM,signal.SIGINT)}
 try:
  for sig in previous:signal.signal(sig,interrupted)
  return _run(planpath,expected)
 finally:
  for sig,handler in previous.items():signal.signal(sig,handler)


def main():
 p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True);q=s.add_parser('prepare');q.add_argument('--pilot-receipt',type=Path,required=True);q.add_argument('--output',type=Path,required=True);q=s.add_parser('run');q.add_argument('--plan',type=Path,required=True);q.add_argument('--plan-sha256',required=True);q=s.add_parser('worker');q.add_argument('--plan',type=Path,required=True);q.add_argument('--stage',choices=['baseline','export','audit','raw'],required=True);q=s.add_parser('verify-membership');q.add_argument('--plan',type=Path,required=True);q.add_argument('--index',type=int,required=True);q.add_argument('--report',type=Path,required=True);a=p.parse_args()
 if a.mode=='prepare':print(json.dumps(prepare(a.pilot_receipt,a.output)))
 elif a.mode=='run':run(a.plan.resolve(),a.plan_sha256)
 elif a.mode=='verify-membership':verify_membership_sources(a.plan,a.index,a.report)
 else:worker(a.plan,a.stage)
if __name__=='__main__':main()
