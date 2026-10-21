"""Independent bounded CSV readback of GT23 mass, moment and force corrections.

No correction transform is used as the value oracle. This checks the existing
producer's linear interpolation and anatomical routing, not anatomical sign
validity, event detection, or COP transformations. Run in the serial guarded slot.
"""
from itertools import zip_longest
import argparse,csv,hashlib,json,math,os,resource
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MASS=ROOT/'docs/quality/audits/source_evidence/gt23/publisher-subject-masses.csv'
MASS_SHA='ff7f268497c0f2945374894005f68d647e869130e46e90194346752ea6508ab0'
README=ROOT/'docs/quality/audits/source_evidence/gt23/publisher-readme.txt'
README_SHA='4a5c8ef0a8d96ed3b81253e7fed2d8516b884fa2aa63e4340c0ab54cf2ac4752'
JOINTS=[('hip_flexion','hip_flexion',1),('knee_angle','knee_flexion',-1),('ankle_angle','ankle_dorsiflexion',1)]

def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for block in iter(lambda:f.read(1024**2),b''):h.update(block)
 return h.hexdigest()

def verify(bindings):
 for p,h in bindings.items():
  if digest(p)!=h:raise ValueError('Bound input changed: '+p)

def source_rows(path,columns,interval=None):
 """Only one projected row in memory; reject ambiguous clocks, never guess units."""
 with Path(path).open(newline='') as f:
  reader=csv.DictReader(f)
  if 'time' not in (reader.fieldnames or []):raise ValueError('Missing source clock')
  previous=-math.inf
  for row in reader:
   t=float(row['time'])
   if not math.isfinite(t) or t<=previous:raise ValueError('Source clock not strictly increasing')
   previous=t
   if interval and not interval[0]<=t<=interval[1]:continue
   yield t,[float(row[c]) if c in row and row[c].strip() else math.nan for c in columns]

def interpolate(path,columns,targets,interval=None):
 if not targets or len(targets)>512 or any(not math.isfinite(t) for t in targets) or any(a>b for a,b in zip(targets,targets[1:])):raise ValueError('Invalid bounded target clock')
 result=[[math.nan]*len(columns) for _ in targets];index=0;previous=None
 for t,values in source_rows(path,columns,interval):
  while index<len(targets) and targets[index]<=t:
   q=targets[index]
   if q==t:result[index]=values[:]
   elif previous is not None:
    pt,pv=previous;fraction=(q-pt)/(t-pt)
    result[index]=[a+(v-a)*fraction for a,v in zip(pv,values)]
   index+=1
  previous=(t,values)
 return result

def clock_slice(path,interval,offset,count):
 result=[];index=0
 for t,_ in source_rows(path,[],interval):
  if offset<=index<offset+count:result.append(t)
  index+=1
 if len(result)!=count:raise ValueError('Output exceeds native source clock')
 return result,index

def same(actual,expected):
 if actual is None:return math.isnan(expected)
 return (math.isnan(actual) and math.isnan(expected)) or math.isclose(actual,expected,rel_tol=1e-8,abs_tol=1e-9)

def require_headers(path,columns):
 with Path(path).open(newline='') as f:header=next(csv.reader(f))
 if len(header)!=len(set(header)) or not {'time',*columns}<=set(header):raise ValueError('Missing/duplicate required raw source header: '+str(path))


def phase_clock_agreement(folder):
 for angle,moment in zip_longest(source_rows(folder/'Joint_Angle.csv',[]),source_rows(folder/'Joint_Moments.csv',[])):
  if angle is None or moment is None or angle[0]!=moment[0]:raise ValueError('Producer shared kinematic clock differs from moment CSV clock; phase producer clock bug requires separate correction')


def check_rows(rows,folder,mode,mass,offset=0,coverage=None):
 if coverage is None:coverage={}
 first=rows[0];side=first['reference_side'];start=first['source_start_time_s'];end=first['source_end_time_s']
 if side not in ('left','right') or not math.isfinite(start) or not start<end:raise ValueError('Invalid source interval/side')
 for r in rows:
  if any(r[k]!=first[k] for k in ('observation_id','source_recording_id','subject','reference_side','source_start_time_s','source_end_time_s')):raise ValueError('Mixed observation identity')
 if mode=='phase':
  if len(rows)!=150 or offset:raise ValueError('Phase observation must contain150samples')
  targets=[start+(end-start)*i/149 for i in range(150)];total=150
  if any(not same(r['phase_ipsi'],100*i/149) for i,r in enumerate(rows)):raise ValueError('Phase grid mismatch')
 else:
  targets,total=clock_slice(folder/'Joint_Angle.csv',(start,end),offset,len(rows))
  origin=clock_slice(folder/'Joint_Angle.csv',(start,end),0,1)[0][0]
  if any(not same(r['time_s'],t-origin) for r,t in zip(rows,targets)):raise ValueError('Native time clock mismatch')
 moment_interval=(start,end) if mode=='phase' else None
 finite=0
 for role,leg in [('ipsi',side[0]),('contra','r' if side=='left' else 'l')]:
  require_headers(folder/'Joint_Moments.csv',[f'{raw}_{leg}_moment' for raw,_,_ in JOINTS])
  require_headers(folder/'GroundFrame_GRFs.csv',[leg.upper()+'Force'+a for a in ('X','Y_Vertical','Z')])
  source=interpolate(folder/'Joint_Moments.csv',[f'{raw}_{leg}_moment' for raw,_,_ in JOINTS],targets,moment_interval)
  force=interpolate(folder/'GroundFrame_GRFs.csv',[leg.upper()+'Force'+a for a in ('X','Y_Vertical','Z')],targets,(start,end))
  for i,row in enumerate(rows):
   for j,(raw,canonical,sign) in enumerate(JOINTS):
    expected=source[i][j]
    if not same(row[f'source_{raw}_moment_{role}_Nm'],expected) or not same(row[f'{canonical}_moment_{role}_Nm_kg'],sign*expected/mass):raise ValueError('Raw moment / participant mass mismatch')
    finite+=int(math.isfinite(expected))
    for feature in (f'source_{raw}_moment_{role}_Nm',f'{canonical}_moment_{role}_Nm_kg'):
     counts=coverage.setdefault(feature,{'finite':0,'missing':0});counts['finite' if math.isfinite(expected) else 'missing']+=1
   for j,name in enumerate((f'source_grf_global_x_{role}_BW',f'grf_vertical_{role}_BW',f'source_grf_global_z_{role}_BW')):
    if not same(row[name],force[i][j]/(mass*9.81)):raise ValueError('Raw Newton force / participant BW mismatch')
    finite+=int(math.isfinite(force[i][j]))
    counts=coverage.setdefault(name,{'finite':0,'missing':0});counts['finite' if math.isfinite(force[i][j]) else 'missing']+=1
   if row[f'grf_anterior_{role}_BW'] is not None or row[f'grf_lateral_{role}_BW'] is not None:raise ValueError('Unsupported anatomical horizontal force present')
 return finite,total

def prepare(report_path,manifest_path,output):
 report_path=Path(report_path).resolve();manifest_path=Path(manifest_path).resolve();output=Path(output).resolve()
 report=json.loads(report_path.read_text());manifest=json.loads(manifest_path.read_text());bindings=report['verified_input_sha256']
 if report.get('status')!='force_cop_and_publisher_normalization_corrected_unreviewed' or report.get('scientific_approval') is not False:raise ValueError('Completed normalization required')
 if bindings.get(str(manifest_path))!=digest(manifest_path):raise ValueError('Native source manifest not bound by correction chain')
 sources=manifest['sources'];required={'Joint_Angle.csv','Joint_Moments.csv','GroundFrame_GRFs.csv'};selected={p:h for p,h in sources.items() if Path(p).name in required}
 if len(selected)!=3 or len({str(Path(p).parent) for p in selected})!=1:raise ValueError('One exact raw recording required')
 parquet=report_path.parent/'corrected.parquet'
 if digest(parquet)!=report['output_sha256']:raise ValueError('Corrected output changed')
 mode=report['actual_producing_converter']['mode']
 if mode not in ('time','phase'):raise ValueError('Actual producing mode unknown')
 if not output.is_relative_to(ROOT/'converted_datasets/reconversion_v2') or output.exists():raise ValueError('Fresh local audit root required')
 extra={**selected,str(report_path):digest(report_path),str(manifest_path):digest(manifest_path),str(parquet):report['output_sha256'],str(MASS):MASS_SHA,str(README):README_SHA,str(Path(__file__).resolve()):digest(__file__)}
 for path,value in extra.items():
  if path in bindings and bindings[path]!=value:raise ValueError('Conflicting source binding')
 bound={**bindings,**extra}
 verify(bound);output.mkdir(parents=True)
 plan={'status':'prepared_not_run','scientific_approval':False,'bindings':bound,'parquet':str(parquet),'source_folder':str(Path(next(iter(selected))).parent),'mode':mode,'expected_rows':report['rows_checked']}
 (output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');return {'plan':str(output/'plan.json'),'plan_sha256':digest(output/'plan.json')}

def run(plan_path,expected):
 for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[key]='1'
 resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
 plan_path=Path(plan_path)
 if digest(plan_path)!=expected:raise ValueError('Plan changed')
 p=json.loads(plan_path.read_text());verify(p['bindings'])
 target=plan_path.parent/'raw_source_readback.json'
 if target.exists() or plan_path.with_name('attempt.json').exists():raise FileExistsError('Existing audit preserved')
 with plan_path.with_name('attempt.json').open('x') as f:json.dump({'status':'started_unreviewed','plan_sha256':expected,'scientific_approval':False},f)
 import pyarrow.parquet as pq
 masses={r['Subject']:float(r['Mass']) for r in csv.DictReader(MASS.read_text().splitlines())};folder=Path(p['source_folder']);subject=folder.parent.parent.name;recording=folder.name
 if subject not in masses or not math.isfinite(masses[subject]) or masses[subject]<=0:raise ValueError('Unknown publisher participant mass')
 if p['mode']=='phase':phase_clock_agreement(folder)
 coverage={}
 seen=set();current=None;offset=0;expected_total=0;count=0;finite=0;pending=[]
 def consume(rows,offset):
  for row in rows:
   if row['subject']!='GT23_'+subject or row['source_recording_id']!=f'gt23:{subject}/{recording}':raise ValueError('Wrong source recording/participant')
   if json.loads(row['subject_metadata'])['weight_kg']!=masses[subject]:raise ValueError('Publisher mass metadata differs')
  return check_rows(rows,folder,p['mode'],masses[subject],offset,coverage)
 for batch in pq.ParquetFile(p['parquet']).iter_batches(batch_size=150 if p['mode']=='phase' else 512,use_threads=False):
  if batch.nbytes>8*1024**2:raise MemoryError('Batch admission exceeded')
  for row in batch.to_pylist():
   identity=row['observation_id']
   if current is not None and identity!=current:
    if pending:
     n,total=consume(pending,offset);finite+=n;offset+=len(pending);pending=[];expected_total=total
    if offset!=expected_total:raise ValueError('Incomplete observation coverage')
    seen.add(current);offset=0
   if identity in seen:raise ValueError('Repeated observation identity')
   current=identity;pending.append(row);count+=1
   if len(pending)==(150 if p['mode']=='phase' else 512):
    n,total=consume(pending,offset);finite+=n;offset+=len(pending);expected_total=total;pending=[]
 if pending:n,total=consume(pending,offset);finite+=n;offset+=len(pending);expected_total=total
 if current is None or offset!=expected_total or count!=p['expected_rows'] or finite==0:raise ValueError('Incomplete source coverage')
 verify(p['bindings'])
 if digest(plan_path)!=expected:raise ValueError('Plan changed during audit')
 unassessed=[name for name,counts in coverage.items() if counts['finite']==0]
 report={'status':'publisher_normalization_raw_source_partial_unassessed' if unassessed else 'publisher_normalization_raw_source_checked_unreviewed','feature_coverage':coverage,'entirely_unassessed_features':unassessed,'scientific_approval':False,'rows_checked':count,'observations_checked':len(seen)+1,'finite_values_checked':finite,'participant':subject,'publisher_mass_kg':masses[subject],'bindings':p['bindings'],'plan_sha256':expected,'limitations':['Raw source values, physical-side routing and existing interpolation checked; source parsing event validity not independently approved.','Anatomical joint moment signs and COP transforms remain outside this audit; missing signals are unassessed.']}
 with target.open('x') as f:json.dump(report,f,indent=2)

def main():
 ap=argparse.ArgumentParser(description=__doc__);s=ap.add_subparsers(dest='mode',required=True);a=s.add_parser('prepare');a.add_argument('--report',type=Path,required=True);a.add_argument('--native-source-manifest',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a=s.add_parser('run');a.add_argument('--plan',type=Path,required=True);a.add_argument('--plan-sha256',required=True);x=ap.parse_args()
 if x.mode=='prepare':print(json.dumps(prepare(x.report,x.native_source_manifest,x.output)))
 else:run(x.plan,x.plan_sha256)
if __name__=='__main__':main()
