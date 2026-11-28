"""Three tiny publisher event files versus literal Parsed clocks; no resampling.

Prepare is metadata-only. Run must be scheduled by the external exclusive worker
coordinator. Neither task labels nor passing clock hypotheses approve cycles.
"""
import argparse,array,bisect,csv,hashlib,json,math,os,resource,signal,struct,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
BASE=ROOT/'converted_datasets/reconversion_v2'
MAX_ROWS=250000


def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024**2),b''):h.update(b)
 return h.hexdigest()


def merge_bindings(*groups):
 result={}
 for group in groups:
  for path,h in group.items():
   path=str(Path(path).resolve())
   if path in result and result[path]!=h:raise ValueError("Conflicting evidence hash: "+path)
   result[path]=h
 return result


def verify(bindings):
 for p,h in bindings.items():
  if digest(p)!=h:raise ValueError('Bound evidence changed: '+p)


def overlap_count(rows):
 import heapq
 active=[];count=0
 for row in sorted(rows,key=lambda r:r['start_s']):
  while active and active[0]<=row['start_s']:heapq.heappop(active)
  count+=len(active);heapq.heappush(active,row['end_s'])
 return count


def validate_selection(members,review):
 selected=review['next_bounded_verification']['selected_records']
 identity=lambda r:(r['subject'],r['recording'],r['source_task'])
 expected={identity(r):r for r in selected}
 if len(members)!=3 or len(expected)!=3 or len({identity(r) for r in members})!=3 or {identity(r) for r in members}!=set(expected) or {r['source_task'] for r in members}!={'ball_toss','cutting','start_stop'}:raise ValueError('Exact three reviewed distinct records/task families required')
 for r in members:
  for key,value in expected[identity(r)]['author_event_member'].items():
   if r['member'].get(key)!=value:raise ValueError('Reviewed ZIP member identity changed')


def interval_rows(matrix):
 """Classification only; row order/invalid values remain in exact field dump."""
 if matrix.ndim!=2 or matrix.shape[1]!=2 or matrix.dtype.kind not in 'biuf':return {'status':'unsupported_event_matrix_schema','rows':[]}
 rows=[]
 for index,values in enumerate(matrix):
  start,end=map(float,values)
  status='valid_interval' if math.isfinite(start) and math.isfinite(end) and end>start else 'invalid_nonfinite_or_nonpositive_duration'
  rows.append({'row_index':index,'status':status,'start_s':start if math.isfinite(start) else None,'end_s':end if math.isfinite(end) else None,'start_float64_hex':struct.pack('>d',start).hex(),'end_float64_hex':struct.pack('>d',end).hex()})
 valid=[r for r in rows if r['status']=='valid_interval']
 diagnostics={'valid_start_order_nondecreasing':all(a['start_s']<=b['start_s'] for a,b in zip(valid,valid[1:])), 'overlap_pairs':overlap_count(valid), 'interpretation':'Diagnostic only; overlapping events may be intentional for optional types. No rows reordered or excluded.'}
 return {'ordering_and_overlap':diagnostics,'status':'empty_author_event_matrix' if not rows else 'author_interval_rows_classified','rows':rows,'valid_rows':sum(r['status']=='valid_interval' for r in rows),'invalid_rows':sum(r['status']!='valid_interval' for r in rows)}


def exact_array(value,budget):
 import numpy as np
 value=np.asarray(value);budget[0]+=value.size
 if budget[0]>100000 or value.nbytes>2*1024**2:raise MemoryError('Decoded MAT field admission exceeded')
 result={'shape':list(value.shape),'dtype':value.dtype.str}
 if value.dtype.names:
  result['fields']={name:exact_array(value[name],budget) for name in value.dtype.names}
 elif value.dtype.kind=='O':result['cells']=[exact_array(cell,budget) for cell in value.flat]
 elif value.dtype.kind in 'biufcUS':result['c_order_bytes_hex']=value.tobytes(order='C').hex()
 else:raise ValueError('Unsupported MAT field representation; original bytes retained')
 return result


def inspect_mat(path):
 from scipy.io import whosmat,loadmat
 schema=whosmat(path);estimated=sum(math.prod(shape)*16 for _,shape,_ in schema)
 if estimated>2*1024**2 or any(math.prod(shape)>100000 for _,shape,_ in schema):raise MemoryError('MAT expanded schema exceeds admission')
 data=loadmat(path,struct_as_record=True,squeeze_me=False,chars_as_strings=False)
 fields={k:v for k,v in data.items() if not k.startswith('__')};budget=[0]
 exact={name:exact_array(value,budget) for name,value in fields.items()}
 legs={name:interval_rows(fields[name]) if name in fields else {'status':'missing_author_leg_field','rows':[]} for name in ('left','right')}
 return {'mat_schema':[{'name':name,'shape':list(shape),'class':kind} for name,shape,kind in schema],'decoded_fields_exact':exact,'legs':legs,'optional_fields_preserved':[k for k in fields if k not in ('left','right')],'optional_type_to_event_membership':'unassessed_preserved_without_assignment','raw_mat_sha256':digest(path)}


def scan_clock(path,check=lambda:None):
 path=Path(path);before=digest(path);clock=array.array('d');literal=hashlib.sha256();numeric=hashlib.sha256();invalid=[];nonfinite=0;nonincreasing=0;rows=0
 with path.open(newline='',encoding='utf-8-sig') as stream:
  reader=csv.reader(stream);header=next(reader)
  if len(header)!=len(set(header)) or header.count('time')!=1:raise ValueError('One explicit source time column required')
  index=header.index('time')
  for row in reader:
   rows+=1
   if rows>MAX_ROWS:raise MemoryError('Bounded source clock row admission exceeded')
   if len(row)!=len(header):raise ValueError('Malformed CSV row width')
   token=row[index];literal.update(struct.pack('>I',len(token.encode()))+token.encode())
   try:t=float(token)
   except ValueError:t=float('nan')
   if not math.isfinite(t):
    nonfinite+=1
    if len(invalid)<16:invalid.append({'row_index':rows-1,'literal_time':token})
   else:
    if clock and t<=clock[-1]:nonincreasing+=1
    clock.append(t);numeric.update(struct.pack('>d',t))
   if rows%512==0:check()
 if digest(path)!=before:raise ValueError('Source changed during clock scan')
 report={'source_sha256':before,'rows':rows,'finite_clock_rows':len(clock),'nonfinite_rows':nonfinite,'nonincreasing_rows':nonincreasing,'invalid_examples':invalid,'literal_time_sha256':literal.hexdigest(),'float64_time_sha256':numeric.hexdigest(),'first_s':clock[0] if clock else None,'last_s':clock[-1] if clock else None,'status':'finite_strictly_increasing_clock' if rows and not nonfinite and not nonincreasing else 'clock_requires_review'}
 return report,clock


def hypotheses(leg,clock_report,clock):
 valid=[r for r in leg['rows'] if r['status']=='valid_interval']
 if not valid or clock_report['status']!='finite_strictly_increasing_clock':return {'status':'unassessed_no_valid_intervals_or_clock','candidates':[],'chosen_offset_s':None}
 first=min(r['start_s'] for r in valid)
 candidates=[('literal_shared_clock',0.),('author_clock_relative_to_source_first',clock[0]),('first_author_event_to_source_first',clock[0]-first)]
 results=[]
 for name,offset in candidates:
  rows=[]
  for r in valid:
   start,end=r['start_s']+offset,r['end_s']+offset;i=bisect.bisect_left(clock,start);j=bisect.bisect_right(clock,end)
   nearest=lambda t:min(abs(clock[k]-t) for k in {max(0,min(len(clock)-1,bisect.bisect_left(clock,t))),max(0,min(len(clock)-1,bisect.bisect_left(clock,t)-1))})
   rows.append({'author_row_index':r['row_index'],'contained_in_record_clock':clock[0]<=start<end<=clock[-1],'source_rows_in_inclusive_interval':j-i,'nearest_start_sample_distance_s':nearest(start),'nearest_end_sample_distance_s':nearest(end)})
  results.append({'name':name,'offset_s':offset,'offset_applied_to_export':False,'all_valid_events_contained':all(r['contained_in_record_clock'] and r['source_rows_in_inclusive_interval']>=2 for r in rows),'events':rows,'interpretation':'First-event anchoring is an unproven fit hypothesis, never automatic evidence of alignment.' if name=='first_author_event_to_source_first' else 'Clock hypothesis only; source provenance must establish reference.'})
 return {'status':'clock_hypotheses_reported_not_selected','candidates':results,'chosen_offset_s':None,'canonical_cycles_approved':False}


def prepare(output):
 output=Path(output).resolve()
 if output.exists() or not output.is_relative_to(BASE):raise ValueError('Fresh isolated root required')
 receipt_path=BASE/'gt25_author_event_members_v4_20261021/retrieval.json';receipt=json.loads(receipt_path.read_text())
 if receipt['status']!='three_exact_publisher_members_retrieved_unparsed' or receipt['numerical_parsing_performed'] is not False or len(receipt['members'])!=3:raise ValueError('Exact untouched acquisition required')
 classification=BASE/'swarm_backlog_20261021/gt25_unmapped192_source_classification.json';scope=json.loads(classification.read_text());lookup={(r['subject'],r['recording']):r for r in scope['records']}
 bindings=merge_bindings({str(receipt_path):digest(receipt_path),str(classification):digest(classification),str(Path(__file__).resolve()):digest(__file__)},scope['bindings'])
 review=ROOT/'docs/quality/audits/gt25-author-event-source-review.json'
 bindings=merge_bindings(bindings,{str(review):receipt['source_review_sha256'],str(BASE/'gt25_author_code_followup_20261021/segmented_inventory.json'):receipt['original_inventory_sha256'],str(receipt_path.parent/'retrieve.py'):receipt['retrieval_tool_sha256']})
 verify(bindings)
 validate_selection(receipt['members'],json.loads(review.read_text()))
 acquisition=receipt_path.parent
 for name in ('retrieve.py','current_bitstream_metadata.json','after_bitstream_metadata.json'):bindings=merge_bindings(bindings,{str(acquisition/name):digest(acquisition/name)})
 original=BASE/'gt25_author_code_followup_20261021'
 for name in ('segmented_inventory.json','segmented_central_directory.bin','readme.txt','bitstreams.json','author_event_membership.json'):bindings=merge_bindings(bindings,{str(original/name):digest(original/name)})
 for name in ('run_gt25_coverage_pilot.py','reconvert_recording.py'):bindings=merge_bindings(bindings,{str(ROOT/'contributor_tools'/name):digest(ROOT/'contributor_tools'/name)})
 records=[]
 for member in receipt['members']:
  path=Path(member['output'])
  if path.stat().st_size!=member['bytes'] or digest(path)!=member['sha256']:raise ValueError('Acquired member changed')
  bindings=merge_bindings(bindings,{str(path):member['sha256']});record=lookup[member['subject'],member['recording']]
  files=[f for f in record['files'] if f['kind'] in ('angle','activity_flag','grf')]
  if {f['kind'] for f in files}!={'angle','activity_flag','grf'} or len(files)!=3 or sum(f['bytes'] for f in files)>64*1024**2:raise ValueError('Three clock sources within64MiB required')
  for f in files:
   stat=Path(f['path']).stat()
   if (stat.st_size,stat.st_mtime_ns)!=(f['bytes'],f['mtime_ns']):raise ValueError('Source stat differs from reviewed inventory')
  records.append({'subject':member['subject'],'recording':member['recording'],'source_task':member['source_task'],'member':member,'clock_files':files})
 verify(bindings);output.mkdir(parents=True)
 plan={'status':'three_author_event_clock_pilots_prepared_not_run','scientific_approval':False,'records':records,'bindings':bindings,'memory_cap_mib':768,'timeout_s':180,'max_clock_rows':MAX_ROWS,'source_clock_hash_policy':'Sourcefile stat pinned at preparation; sourcebytes hashes acquired and rechecked during worker, not historical original-value proof.','external_exclusive_slot_required':True,'limitations':['No phase normalization, event splitting, canonical task reassignment or source data modification.','All hypotheses retained; no offset automatically selected.','Left/right and optional types preserved, clinical/anatomical reference and optionaltype membership unassessed.']}
 (output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');return plan


def worker(path,expected):
 resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));path=Path(path).resolve();plan=json.loads(path.read_text())
 if digest(path)!=expected:raise ValueError('Plan changed')
 verify(plan['bindings']);results=[]
 def check():
  if any((path.parent/name).exists() for name in ('STOP','STOP_AFTER_CURRENT')):raise RuntimeError('Coordinator stop')
 for record in plan['records']:
  check();mat=inspect_mat(record['member']['output']);clocks={};comparisons={}
  for f in record['clock_files']:
   stat=Path(f['path']).stat()
   if (stat.st_size,stat.st_mtime_ns)!=(f['bytes'],f['mtime_ns']):raise ValueError('Source changed before readback')
   report,clock=scan_clock(f['path'],check);clocks[f['kind']]=report;comparisons[f['kind']]={leg:hypotheses(info,report,clock) for leg,info in mat['legs'].items()}
  results.append({'subject':record['subject'],'recording':record['recording'],'source_task':record['source_task'],'mat':mat,'clocks':clocks,'stream_clock_literals_identical':len({x['literal_time_sha256'] for x in clocks.values()})==1,'stream_numeric_clocks_identical':len({x['float64_time_sha256'] for x in clocks.values()})==1,'comparisons':comparisons,'canonical_cycles_approved':False})
 verify(plan['bindings'])
 for r,record in zip(results,plan['records']):
  for f in record['clock_files']:
   if digest(f['path'])!=r['clocks'][f['kind']]['source_sha256']:raise ValueError('Earlier source clock changed')
 if digest(path)!=expected:raise ValueError('Plan changed')
 result={'status':'author_event_schema_and_clock_hypotheses_reported_unreviewed','scientific_approval':False,'canonical_cycles_approved':False,'plan_sha256':expected,'records':results,'limitations':plan['limitations']}
 with (path.parent/'event_clock_review.json').open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False)


def run(path,expected):
 from contributor_tools.run_gt25_coverage_pilot import guarded_stage
 from contributor_tools.reconvert_recording import ensure_storage_headroom
 path=Path(path).resolve()
 if digest(path)!=expected:raise ValueError('Bound plan required')
 if (path.parent/'attempt.json').exists():raise FileExistsError('Existing attempt preserved')
 plan=json.loads(path.read_text());verify(plan['bindings'])
 if plan['memory_cap_mib']!=768 or plan['timeout_s']!=180 or plan['max_clock_rows']!=MAX_ROWS or plan['external_exclusive_slot_required'] is not True:raise ValueError('Fixed admission limits required')
 def stop(*args):raise RuntimeError('Coordinator interruption')
 previous={s:signal.signal(s,stop) for s in (signal.SIGINT,signal.SIGTERM)}
 last=0
 def storage(root):
  nonlocal last
  if any((path.parent/name).exists() for name in ('STOP','STOP_AFTER_CURRENT')):raise RuntimeError('Coordinator stop')
  if time.monotonic()-last>15:ensure_storage_headroom(root);last=time.monotonic()
 env=os.environ
 env.pop('PYTHONOPTIMIZE',None)
 for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):env[key]='1'
 try:
  with (path.parent/'attempt.json').open('x') as stream:json.dump({'status':'started','plan_sha256':expected,'scientific_approval':False},stream)
  with (path.parent/'worker.log').open('x') as log:result=guarded_stage(['nice','-n','19',sys.executable,str(Path(__file__).resolve()),'worker','--plan',str(path),'--plan-sha256',expected],stdout=log,output_root=path.parent,storage_check=storage,timeout=plan['timeout_s'])
  if result.returncode:raise RuntimeError('Event clock worker failed; preserve evidence')
  report=json.loads((path.parent/'event_clock_review.json').read_text())
  verify(plan['bindings'])
  if digest(path)!=expected:raise ValueError('Plan changed after worker')
  identities=lambda rows:[(r['subject'],r['recording'],r['source_task']) for r in rows]
  if identities(report['records'])!=identities(plan['records']):raise ValueError('Pilot identity mismatch')
  if report['status']!='author_event_schema_and_clock_hypotheses_reported_unreviewed' or report['plan_sha256']!=expected or report['scientific_approval'] is not False or report['canonical_cycles_approved'] is not False or len(report['records'])!=3:raise ValueError('Pilot receipt incomplete')
 finally:
  for sig,handler in previous.items():signal.signal(sig,handler)


def main():
 p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='action',required=True);q=s.add_parser('prepare');q.add_argument('--output',type=Path,required=True)
 for mode in ('run','worker'):
  q=s.add_parser(mode);q.add_argument('--plan',type=Path,required=True);q.add_argument('--plan-sha256',required=True)
 a=p.parse_args()
 if sys.flags.optimize:raise ValueError('Review tools require assertions enabled')
 if a.action=='prepare':prepare(a.output)
 elif a.action=='run':run(a.plan,a.plan_sha256)
 else:worker(a.plan,a.plan_sha256)
if __name__=='__main__':main()
