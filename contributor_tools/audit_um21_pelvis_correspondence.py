"""Bounded same-stride source comparison; never approves 3-D segment anatomy.

Uses explicit StrideDetails physical side/frame identity and Streaming heel strikes.
Author hip-minus-pelvis illustration is kept separate from source correspondence.
"""
import argparse,hashlib,json,math,os,resource,shutil,subprocess,time
from pathlib import Path

def digest(path,guard=lambda:None):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1024**2),b''):guard();h.update(block)
 return h.hexdigest()

def stride_key(values):
 if len(values)!=4:raise ValueError('StrideDetails needs four source fields')
 a,b,d,leg=map(float,values)
 if not all(math.isfinite(x) and x==int(x) for x in (a,b,d,leg)) or a<1 or b<=a or b-a!=d or leg not in (1,2):raise ValueError('Invalid explicit stride identity')
 return ('left' if leg==1 else 'right',int(a),int(b))

def find_stride(details,key):
 found=[];seen=set()
 for i,values in enumerate(details):
  k=stride_key(values)
  if k in seen:raise ValueError('Duplicate physical stride identity')
  seen.add(k)
  if k==key:found.append(i)
 if len(found)!=1:raise ValueError('No unique exact same-side normalized stride')
 return found[0]

def normalize(raw):
 if not 2<=len(raw)<=4096:raise ValueError('Bounded source window required')
 out=[]
 for i in range(150):
  x=i*(len(raw)-1)/149;left=math.floor(x);right=math.ceil(x)
  out.append(float(raw[left]) if left==right else (float(raw[left])*(right-x)+float(raw[right])*(x-left)))
 return out

def compare(normalized,streaming,tolerance=1e-8):
 if len(normalized)!=150 or len(streaming)!=150:raise ValueError('Exactly150 samples required')
 finite=missing=0;mask_mismatch=False;infinite=False;errors=[]
 for a,b in zip(normalized,streaming):
  a=float(a);b=float(b)
  if math.isinf(a) or math.isinf(b):infinite=True
  if math.isnan(a)!=math.isnan(b):mask_mismatch=True
  if math.isnan(a) and math.isnan(b):missing+=1
  if math.isfinite(a) and math.isfinite(b):finite+=1;errors.append(abs(a-b))
 maximum=max(errors,default=None)
 passed=finite==150 and not infinite and not mask_mismatch and maximum<=tolerance
 return {'status':'matched_all150' if passed else 'unassessed_all_missing' if missing==150 else 'mismatch_or_incomplete','finite_pairs':finite,'both_missing':missing,'mask_mismatch':mask_mismatch,'infinity_present':infinite,'maximum_error_deg':maximum}

def compare_components(pelvis,hip,stream_hip,pelvis_candidates):
 result={'hip_components':[compare(a,b) for a,b in zip(hip,stream_hip)],'pelvis_candidates':{}}
 if any(len(x)!=3 for x in (pelvis,hip,stream_hip)):raise ValueError('Three explicit source components required')
 for name,curves in pelvis_candidates.items():
  if curves is None:result['pelvis_candidates'][name]={'status':'unassessed_missing_source_channel'};continue
  if len(curves)!=3:raise ValueError('Three pelvis components required')
  author=[h-p for h,p in zip(hip[0],pelvis[0])]
  minus=[h-p for h,p in zip(stream_hip[0],curves[0])]
  plus=[h+p for h,p in zip(stream_hip[0],curves[0])]
  result['pelvis_candidates'][name]={'components':[compare(a,b) for a,b in zip(pelvis,curves)],'author_minus_vs_stream_minus':compare(author,minus),'author_minus_vs_legacy_stream_plus':compare(author,plus)}
 result['nonzero_normalized_sagittal_pelvis']=any(math.isfinite(float(x)) and abs(float(x))>1e-6 for x in pelvis[0])
 return result

def admit(ds,whole=False):
 if ds.dtype.kind not in 'fiu':raise ValueError('Expected numeric source data')
 if ds.chunks and math.prod(ds.chunks)*ds.dtype.itemsize>16*1024**2:raise ValueError('HDF5 chunk exceeds16MiB')
 if whole and ds.size*ds.dtype.itemsize>256*1024:raise ValueError('Metadata exceeds256KiB')

def audit(plan,guard):
 if plan.get('expected_record_count')!=4 or len(plan['records'])!=4 or any(sum(r['reference_side']==side for r in plan['records'])!=2 for side in ('left','right')):raise ValueError('Exact four-stride bilateral pilot scope required')
 import h5py
 rows=[];identities=set()
 with h5py.File(plan['normalized'],'r',rdcc_nbytes=1024**2) as norm,h5py.File(plan['streaming'],'r',rdcc_nbytes=1024**2) as stream:
  for record in plan['records']:
   guard();side=record['reference_side'];a=record['start_frame'];b=record['end_frame'];key=(side,a,b)
   ident=f'um21:Streaming/{record["subject"]}/Tread/{record["condition"]}:{side}:frames:{a}:{b}'
   if record['observation_id']!=ident or ident in identities:raise ValueError('Wrong or duplicate recording identity')
   identities.add(ident)
   if side not in ('left','right') or not 1<=a<b or b-a+1>4096:raise ValueError('Invalid frame window')
   condition={'d5':'in5','d10':'in10'}.get(record['condition'],record['condition'])
   nb=norm[f'Normalized/{record["subject"]}/Walk/{record["original_normalized_task"]}/{condition}']
   sb=stream[f'Streaming/{record["subject"]}/Tread/{record["condition"]}']
   details=nb['events/StrideDetails'];admit(details,True)
   if details.ndim!=2 or details.shape[0]!=4:raise ValueError('StrideDetails source schema differs')
   index=find_stride(details[...].T,key);n=details.shape[1]
   events=sb['events/'+('LHS' if side=='left' else 'RHS')];admit(events,True)
   hs=list(map(float,events[...].reshape(-1)))
   if not all(math.isfinite(x) and x==int(x) for x in hs) or any(y<=x for x,y in zip(hs,hs[1:])):raise ValueError('Invalid source heel-strike sequence')
   if sum(x==a and y==b for x,y in zip(hs,hs[1:]))!=1:raise ValueError('Not exact consecutive same-side source heel strikes')
   def normalized(name):
    ds=nb['jointAngles/'+name];admit(ds)
    if ds.shape==(n,3,150):return ds[index,:,:].tolist()
    if n==1 and ds.shape==(3,150):return ds[...].tolist()
    raise ValueError('Normalized component/stride dimensions differ')
   def streaming(name,optional=False):
    if 'jointAngles/'+name not in sb:
     if optional:return None
     raise ValueError('Missing same-side hip channel')
    ds=sb['jointAngles/'+name];admit(ds)
    if ds.ndim!=2 or ds.shape[0]!=3 or ds.shape[1]<b:raise ValueError('Streaming channel dimensions differ')
    return [normalize(ds[c,a-1:b]) for c in range(3)]
   pelvis=normalized('PelvisAngles');hip=normalized('HipAngles')
   result=compare_components(pelvis,hip,streaming(('L' if side=='left' else 'R')+'HipAngles'),{name:streaming(name,True) for name in ('RPelvisAngles','LPelvisAngles')})
   rows.append({'observation_id':ident,'physical_side':side,'normalized_block':nb.name,'streaming_block':sb.name,'normalized_stride_index_zero_based':index,'start_frame_one_based':a,'end_frame_inclusive_one_based':b,**result})
 side_nonzero={side:any(r['physical_side']==side and r['nonzero_normalized_sagittal_pelvis'] for r in rows) for side in ('left','right')}
 return {'status':'same_stride_component_comparison_reported_unreviewed' if all(side_nonzero.values()) else 'partial_unassessed_missing_bilateral_nonzero_pelvis','scientific_approval':False,'canonical_3d_approval':False,'streaming_author_recipe_approved':False,'nonzero_pelvis_by_side':side_nonzero,'records':rows,'limitations':['Component matching is reported for both named pelvis candidates; no waveform-selected sign/channel is adopted.','Author normalized hip-minus-pelvis is a planar illustration, not3D anatomy or a shank/foot definition.','All source windows and missing channels remain explicit; comparison mismatch is not repaired.','No original producer aliases or queued artifacts modified.']}

def bound_inputs(plan):
 canonical={}
 for path,h in plan['bindings'].items():
  key=str(Path(path).resolve())
  if key in canonical and canonical[key]!=h:raise ValueError('Conflicting canonical binding')
  if not isinstance(h,str) or len(h)!=64 or any(c not in '0123456789abcdef' for c in h):raise ValueError('Invalid SHA256 binding')
  canonical[key]=h
 required={str(Path(plan[k]).resolve()) for k in ('normalized','streaming')}|{str(Path(__file__).resolve())}
 if not required<=set(canonical):raise ValueError('Missing mandatory source/auditor binding')
 return canonical

def run(plan_path,expected,supervised):
 if not supervised:raise RuntimeError('Exclusive external numerical supervisor required')
 if digest(plan_path)!=expected:raise ValueError('Plan hash changed')
 plan=json.loads(plan_path.read_text());plan['bindings']=bound_inputs(plan);output=Path(plan['output'])
 if output.exists():raise FileExistsError('Fresh comparison output required')
 started=time.monotonic();last=0
 def guard(startup=False):
  nonlocal last
  now=time.monotonic()
  if now-started>1800 or (output.parent/'STOP').exists():raise RuntimeError('Timeout or STOP')
  if now-last<15 and not startup:return
  linux=int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))/1024
  ps='/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'
  r=subprocess.run([ps,'-NoProfile','-NonInteractive','-Command','[long](Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory'],capture_output=True,text=True,check=True,timeout=15)
  if linux<(3584 if startup else 2048) or int(r.stdout.strip())/1024<(2816 if startup else 2048):raise MemoryError('Headroom below unchanged guard')
  if shutil.disk_usage(output.parent).free<5*1024**3:raise RuntimeError('Disk reserve5GiB')
  if digest(plan_path)!=expected:raise ValueError('Plan mutated')
  last=now
 def verify():
  for path,h in plan['bindings'].items():
   if digest(path,guard)!=h:raise ValueError('Source/code binding changed: '+path)
 guard(True);verify();result=audit(plan,guard);verify()
 result.update(plan_sha256=expected,bindings=plan['bindings'])
 if digest(plan_path)!=expected:raise ValueError('Plan changed before output publication')
 with output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--plan-sha256',required=True);p.add_argument('--run',action='store_true');p.add_argument('--supervised-exclusive-slot',action='store_true');a=p.parse_args()
 if not a.run:print(json.dumps({'status':'not_executed','plan':str(a.plan)}));return
 for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
 os.nice(max(0,19-os.getpriority(os.PRIO_PROCESS,0)));subprocess.run(['ionice','-c','3','-p',str(os.getpid())],check=True,timeout=10)
 resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
 print(json.dumps(run(a.plan,a.plan_sha256,a.supervised_exclusive_slot)['status']))
if __name__=='__main__':main()
