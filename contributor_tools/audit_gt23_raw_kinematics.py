"""Independent supplied-CSV kinematics readback; not anatomical approval.

Six angles and six supplied velocities, both physical sides. No differentiation
recipe is assumed. Explicit coordinator-owned serial slot required for execution.
"""
import argparse,csv,hashlib,json,math,os,resource,time
from itertools import zip_longest
from pathlib import Path,PureWindowsPath
ROOT=Path(__file__).resolve().parents[1]
JOINTS=(('hip_flexion','hip_flexion_velocity','hip_flexion',1),('knee_angle','knee_velocity','knee_flexion',-1),('ankle_angle','ankle_velocity','ankle_dorsiflexion',1))
ALIAS='derived_unverified_producer_'

def digest(p,guard=lambda:None):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(262144),b''):guard();h.update(b)
 return h.hexdigest()

def merge(bindings,extra):
 normalized={}
 for p,h in list(bindings.items())+list(extra.items()):
  p=str(Path(p).resolve())
  if p in normalized and normalized[p]!=h:raise ValueError('Conflicting source/code/output hash')
  normalized[p]=h
 bindings.clear()
 for p,h in normalized.items():
  if p in bindings and bindings[p]!=h:raise ValueError('Conflicting source/code/output hash')
  bindings[p]=h

def verify(bindings,guard=lambda:None):
 for p,h in bindings.items():
  if digest(p,guard)!=h:raise ValueError('Bound input changed: '+p)

def source_rows(path,columns,interval=None,guard=lambda:None):
 with Path(path).open(encoding='utf-8-sig',newline='') as f:
  reader=csv.DictReader(f);header=reader.fieldnames or []
  if len(header)!=len(set(header)) or not {'time',*columns}<=set(header):raise ValueError('Required source column missing/duplicate')
  previous=-math.inf
  for i,row in enumerate(reader):
   if i%512==0:guard()
   if None in row or any(v is None for v in row.values()):raise ValueError('Malformed source row')
   t=float(row['time'])
   if not math.isfinite(t) or t<=previous:raise ValueError('Source clock not strictly increasing')
   previous=t
   if interval and not interval[0]<=t<=interval[1]:continue
   values=[float(row[c]) if row[c].strip() else math.nan for c in columns]
   if any(math.isinf(x) for x in values):raise ValueError('Infinite source signal unassessed')
   yield t,values

def interpolate(path,columns,targets,interval=None,guard=lambda:None):
 if not targets or len(targets)>512 or any(not math.isfinite(t) for t in targets) or any(a>b for a,b in zip(targets,targets[1:])):raise ValueError('Bounded ordered target clock required')
 values=[[math.nan]*len(columns) for _ in targets];previous=None;index=0
 for t,current in source_rows(path,columns,interval,guard):
  while index<len(targets) and targets[index]<=t:
   q=targets[index]
   if q==t:values[index]=current[:]
   elif previous is not None:
    pt,pv=previous;fraction=(q-pt)/(t-pt);values[index]=[a+(b-a)*fraction for a,b in zip(pv,current)]
   index+=1
  previous=(t,current)
 return values

def close(a,b):
 if a is None:return math.isnan(b)
 return math.isnan(a) and math.isnan(b) or math.isclose(a,b,rel_tol=1e-8,abs_tol=1e-9)

def phase_clock_gate(folder,guard=lambda:None):
 for angle,velocity in zip_longest(source_rows(folder/'Joint_Angle.csv',[],guard=guard),source_rows(folder/'Joint_Velocities.csv',[],guard=guard)):
  if angle is None or velocity is None or angle[0]!=velocity[0]:raise ValueError('Phase producer uses angle clock for velocity; actual source clocks differ, separate producer fix required')

def check_rows(rows,folder,mode,offset=0,coverage=None,aliases=False,guard=lambda:None):
 if mode not in ('time','phase') or not rows or len(rows)>512:raise ValueError('Invalid bounded mode/rows')
 coverage={} if coverage is None else coverage;first=rows[0];start,end=first['source_start_time_s'],first['source_end_time_s'];side=first['reference_side']
 if side not in ('left','right') or not all(math.isfinite(x) for x in (start,end)) or start>=end:raise ValueError('Invalid physical side/source interval')
 for row in rows:
  if any(row[k]!=first[k] for k in ('subject','source_recording_id','observation_id','reference_side','source_start_time_s','source_end_time_s')):raise ValueError('Mixed source identity')
 if mode=='phase':
  if len(rows)!=150 or offset:raise ValueError('Exactly150inclusive phase rows required')
  targets=[start+(end-start)*i/149 for i in range(150)];total=150
  if any(not close(r['phase_ipsi'],100*i/149) for i,r in enumerate(rows)):raise ValueError('Phase grid differs')
 else:
  targets=[];total=0;origin=None
  for t,_ in source_rows(folder/'Joint_Angle.csv',[],(start,end),guard):
   if origin is None:origin=t
   if offset<=total<offset+len(rows):targets.append(t)
   total+=1
  if len(targets)!=len(rows) or any(not close(r['time_s'],t-origin) for r,t in zip(rows,targets)):raise ValueError('Actual native timestamp identity differs')
 for family,filename,index,units in [('angle','Joint_Angle.csv',0,'rad'),('velocity','Joint_Velocities.csv',1,'rad_s')]:
  columns=[f'{joint[index]}_{leg}' for leg in ('l','r') for joint in JOINTS]
  expected=interpolate(folder/filename,columns,targets,(start,end) if mode=='phase' else None,guard)
  for role,leg in [('ipsi',side[0]),('contra','r' if side=='left' else 'l')]:
   base=0 if leg=='l' else 3
   for j,(_,_,canonical,sign) in enumerate(JOINTS):
    feature=f'{canonical}_{family}_{role}_{units}';name=ALIAS+feature if aliases else feature;counts=coverage.setdefault(name,{'finite':0,'missing':0})
    for row,raw in zip(rows,expected):
     if name not in row or not close(row[name],sign*raw[base+j]*math.pi/180):raise ValueError('Supplied source value/side/sign/unit mismatch: '+name)
     if aliases and row.get(feature,'absent') is not None:raise ValueError('Withheld canonical column is not null')
     counts['finite' if math.isfinite(raw[base+j]) else 'missing']+=1
 return total

def verify_window_support(original,prepared,guard=lambda:None):
 index=0 if original.name=='Joint_Angle.csv' else 1
 columns=[f'{j[index]}_{leg}' for leg in ('l','r') for j in JOINTS]
 actual=iter(source_rows(prepared,columns,guard=guard));wanted=next(actual,None);matched=0;started=False;ended=False
 for t,values in source_rows(original,columns,guard=guard):
  if wanted is None:
   ended=True;continue
  if t==wanted[0]:
   if ended or any(not (a==b or math.isnan(a) and math.isnan(b)) for a,b in zip(values,wanted[1])):raise ValueError('Prepared source values differ from original')
   matched+=1;started=True;wanted=next(actual,None)
  elif started and wanted is not None:raise ValueError('Prepared source clock skips original interior rows')
  elif t>wanted[0]:raise ValueError('Prepared source clock absent from original')
 if wanted is not None or matched<2:raise ValueError('Prepared source support incomplete')
 return matched


def windows_local(value):
 p=PureWindowsPath(value)
 if p.drive.upper() not in ('S:','C:') or '..' in p.parts:raise ValueError('Unsupported source root')
 return Path('/mnt')/p.drive[0].lower()/Path(*p.parts[1:])

def sources(manifest,evidence,options,evidence_sha,mode):
 if mode not in ('time','phase') or ('prepared_input_manifest' in manifest)!=(mode=='time'):raise ValueError('Actual producing mode/source schema differs')
 selected={};extra={};required={'Joint_Angle.csv','Joint_Velocities.csv'}
 if mode=='time':
  if manifest['prepared_input_manifest']!=evidence_sha or manifest['prepared_input_sha256'].get('source_window_manifest.json')!=evidence_sha or evidence['subject']!=options['subject'] or evidence['parsing']!=options['recording']:raise ValueError('Prepared source identity differs')
  for name in required:
   row=evidence['csv_files'][name];source=Path(row['source']);relative=f"RawData/{evidence['subject']}/CSV_Data/{evidence['recording']}/{name}"
   if source.parts[-5:]!=Path(relative).parts or manifest['prepared_input_sha256'].get(relative)!=row['window_sha256']:raise ValueError('Prepared/raw kinematic source mapping differs')
   selected[str(source)]=row['source_sha256'];extra[str(windows_local(options['data_root'])/relative)]=row['window_sha256']
 else:
  if evidence['output_sha256']!=manifest['output_sha256'] or evidence.get('scientific_approval') is not False:raise ValueError('Native source receipt output differs')
  parsing=windows_local(options['data_root'])/'Segmentation'/options['subject']/options['recording']
  extra[str(parsing)]=evidence['source_sha256'][str(parsing)]
  candidates={}
  for source_path,source_sha in evidence['source_sha256'].items():
   if Path(source_path).name in required:merge(candidates,{source_path:source_sha})
  actual_prefix=(windows_local(options['data_root'])/'RawData'/options['subject']/'CSV_Data').resolve()
  originals={p:h for p,h in candidates.items() if not Path(p).is_relative_to(actual_prefix)}
  selected=originals if originals else candidates
  if originals:
   # Only the exact producer input root may be removed from original candidates.
   # Extra third-party roots remain ambiguous and fail the exactpair check below.
   for p,h in candidates.items():
    if Path(p).is_relative_to(actual_prefix):merge(extra,{p:h})
 if len(selected)!=2 or len({str(Path(p).parent) for p in selected})!=1:raise ValueError('Exact raw kinematic pair required')
 folder=Path(next(iter(selected))).parent
 if folder.parent.name!='CSV_Data' or folder.parent.parent.name!=options['subject']:raise ValueError('Source participant differs')
 return selected,extra


def prepare(report_path,manifest_path,evidence_path,evidence_sha,output):
 report_path,manifest_path,evidence_path,output=map(lambda p:Path(p).resolve(),(report_path,manifest_path,evidence_path,output));report=json.loads(report_path.read_text());manifest=json.loads(manifest_path.read_text());options_path=manifest_path.with_name('options.json');bindings={};merge(bindings,report['verified_input_sha256'])
 if report['status']!='force_cop_and_publisher_normalization_corrected_unreviewed' or report.get('scientific_approval') is not False:raise ValueError('Actual corrected native report required')
 if bindings.get(str(manifest_path))!=digest(manifest_path) or bindings.get(str(options_path))!=digest(options_path) or digest(evidence_path)!=evidence_sha:raise ValueError('Actual native/source receipt not bound')
 mode=report['actual_producing_converter']['mode'];selected,extra=sources(manifest,json.loads(evidence_path.read_text()),json.loads(options_path.read_text()),evidence_sha,mode)
 actual_folder=windows_local(json.loads(options_path.read_text())['data_root'])/'RawData'/json.loads(options_path.read_text())['subject']/'CSV_Data'/Path(next(iter(selected))).parent.name
 pairs=[];evidence=json.loads(evidence_path.read_text())
 for original,source_sha in selected.items():
  prepared=actual_folder/Path(original).name;relative='/'.join(prepared.parts[-5:]);prepared_sha=manifest.get('prepared_input_sha256',{}).get(relative) or evidence.get('source_sha256',{}).get(str(prepared))
  if str(prepared)==original:prepared_sha=prepared_sha or source_sha
  if not prepared_sha:raise ValueError('Actual producer cropped source has no bound receipt hash')
  merge(extra,{str(prepared):prepared_sha});pairs.append({'original':original,'prepared':str(prepared)})
 parquet=report_path.parent/'corrected.parquet'
 if digest(parquet)!=report['output_sha256'] or type(report['rows_checked']) is not int or report['rows_checked']<=0:raise ValueError('Corrected output hash/count differs')
 if output.exists() or not output.is_relative_to(ROOT/'converted_datasets/reconversion_v2'):raise ValueError('Fresh isolated audit root required')
 merge(bindings,selected);merge(bindings,extra)
 for path in [report_path,manifest_path,options_path,evidence_path,parquet,Path(__file__).resolve(),ROOT/'contributor_tools/preserve_mblue_planar_estimates.py']:merge(bindings,{str(path):digest(path)})
 verify(bindings);output.mkdir(parents=True);p=output/'plan.json';p.write_text(json.dumps({'status':'prepared_not_run','scientific_approval':False,'anatomical_approval':False,'bindings':bindings,'parquet':str(parquet),'source_folder':str(actual_folder),'source_pairs':pairs,'mode':mode,'expected_rows':report['rows_checked'],'timeout_seconds':1800,'requires_external_exclusive_supervisor':True},indent=2)+'\n')
 return {'plan':str(p),'plan_sha256':digest(p)}


def runtime_guard(folder,seconds):
 import sys
 sys.path.insert(0,str(ROOT))
 from contributor_tools.preserve_mblue_planar_estimates import headroom,windows_available_mib
 started=time.monotonic();last=[None]
 def guard():
  now=time.monotonic()
  if now-started>seconds or (folder/'STOP').exists():raise RuntimeError('Finite audit timeout/coordinator STOP')
  if last[0] is None or now-last[0]>15:
   headroom(folder)
   linux=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))//1024
   if linux<(3584 if last[0] is None else 2048) or windows_available_mib()<(2816 if last[0] is None else 2048):raise MemoryError('Kinematics audit headroom refused')
   last[0]=now
 guard();return guard


def audit_batches(batches,folder,mode,expected_rows,guard=lambda:None,aliases=False):
 folder=Path(folder);subject=folder.parent.parent.name;recording=folder.name
 if mode=='phase':phase_clock_gate(folder,guard)
 coverage={};seen=set();current=None;pending=[];offset=0;total=0;count=0;invariant=None
 def consume(rows,offset):
  for row in rows:
   if row['subject']!='GT23_'+subject or row['source_recording_id']!=f'gt23:{subject}/{recording}':raise ValueError('Wrong original participant/recording')
  return check_rows(rows,folder,mode,offset,coverage,aliases,guard)
 for rows in batches:
  guard()
  for row in rows:
   identity=row['observation_id']
   if current is not None and identity!=current:
    if pending:total=consume(pending,offset);offset+=len(pending);pending=[]
    if offset!=total:raise ValueError('Incomplete observation source rows')
    seen.add(current);offset=0
   if identity in seen:raise ValueError('Repeated observation identity')
   actual_identity=tuple(row[k] for k in ('subject','source_recording_id','observation_id','reference_side','source_start_time_s','source_end_time_s'))
   if identity!=current:invariant=actual_identity
   elif actual_identity!=invariant:raise ValueError('Observation metadata changed across chunks')
   current=identity;pending.append(row);count+=1
   if len(pending)==(150 if mode=='phase' else 512):total=consume(pending,offset);offset+=len(pending);pending=[]
 if pending:total=consume(pending,offset);offset+=len(pending)
 if current is None or offset!=total or count!=expected_rows or len(coverage)!=12:raise ValueError('Complete12feature source scope required')
 unassessed=[name for name,c in coverage.items() if c['finite']==0]
 return {'status':'supplied_raw_kinematics_partial_unassessed' if unassessed else 'supplied_raw_kinematics_producer_recipe_checked_unreviewed','scientific_approval':False,'anatomical_approval':False,'producer_transformation_checked':True,'rows_checked':count,'observations_checked':len(seen)+1,'feature_coverage':coverage,'entirely_unassessed_features':unassessed,'physical_source_participant':subject,'source_recording':recording,'limitations':['Checks supplied source values/physical side/clock and explicit producer +hip,-knee,+ankle degree conversion; not anatomical coordinate approval.','Supplied velocity differentiation/filtering recipe remains unresolved; no velocity recomputation performed.','Parsing interval/event validity outside scope. Phase velocity angle-clock assumption must agree with actual own CSV clock.','Bounded repeatedCSVscans suitable for finite pilots; fullbatch indexing requires separate reviewed optimization.']}


def run(path,expected,supervised=False):
 if not supervised:raise ValueError('External exclusive supervisor confirmation required')
 for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[k]='1'
 resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
 path=Path(path).resolve()
 if digest(path)!=expected:raise ValueError('Plan changed')
 plan=json.loads(path.read_text());guard=runtime_guard(path.parent,plan['timeout_seconds']);verify(plan['bindings'],guard);target=path.parent/'raw_kinematics_readback.json'
 if target.exists() or path.with_name('attempt.json').exists():raise FileExistsError('Existing audit preserved')
 with path.with_name('attempt.json').open('x') as f:json.dump({'plan_sha256':expected,'scientific_approval':False},f)
 import pyarrow as pa,pyarrow.parquet as pq
 pa.set_cpu_count(1);pa.set_io_thread_count(1)
 def batches():
  for batch in pq.ParquetFile(plan['parquet']).iter_batches(batch_size=150 if plan['mode']=='phase' else 512,use_threads=False):
   if batch.nbytes>8*1024**2:raise MemoryError('Audit batch exceeds8MiB')
   yield batch.to_pylist()
 for pair in plan['source_pairs']:
  verify_window_support(Path(pair['original']),Path(pair['prepared']),guard)
 report=audit_batches(batches(),Path(plan['source_folder']),plan['mode'],plan['expected_rows'],guard)
 verify(plan['bindings'],guard);guard()
 if digest(path,guard)!=expected:raise ValueError('Plan changed during audit')
 report.update(plan_sha256=expected,bindings=plan['bindings'],output_sha256=digest(plan['parquet'],guard))
 with target.open('x') as f:json.dump(report,f,indent=2,allow_nan=False)


def main():
 p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True);q=s.add_parser('prepare')
 for name in ('report','native-source-manifest','source-evidence','output'):q.add_argument('--'+name,type=Path,required=True)
 q.add_argument('--source-evidence-sha256',required=True);q=s.add_parser('run');q.add_argument('--plan',type=Path,required=True);q.add_argument('--plan-sha256',required=True);q.add_argument('--supervised-exclusive-slot',action='store_true');a=p.parse_args()
 if a.mode=='prepare':print(json.dumps(prepare(a.report,a.native_source_manifest,a.source_evidence,a.source_evidence_sha256,a.output)))
 else:run(a.plan,a.plan_sha256,a.supervised_exclusive_slot)
if __name__=='__main__':main()
