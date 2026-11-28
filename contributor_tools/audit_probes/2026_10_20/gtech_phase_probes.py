# Archived read-only investigation probe, 2026-10-20.
# Run from repository root with OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
# and nice -n 19 ionice -c 3. Local source paths and file versions are required.
# Results are scoped samples, not release approval.
"""Read-only first600-row probes of every GT21 clean rowgroup; no full scan."""
import resource
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
import pyarrow.parquet as pq,numpy as np,json
from pathlib import Path
f=pq.ParquetFile('converted_datasets/gtech_2021_phase_clean.parquet');out=[];collisions=[]
for rg in range(f.num_row_groups):
 cols=['subject','task','task_id','task_info','step','phase_ipsi','phase_ipsi_dot','hip_flexion_angle_ipsi_rad','hip_flexion_velocity_ipsi_rad_s']
 names=f.schema_arrow.names
 assert sum(f.metadata.row_group(rg).column(names.index(c)).total_uncompressed_size for c in cols)<64*1024**2
 b=next(f.iter_batches(batch_size=600,columns=cols,row_groups=[rg],use_threads=False)).to_pydict()
 phase=np.array(b['phase_ipsi']);starts=np.where(phase==0)[0];seen={}
 for s in starts:
  if s+150>len(phase):continue
  a=np.array(b['hip_flexion_angle_ipsi_rad'][s:s+150]);v=np.array(b['hip_flexion_velocity_ipsi_rad_s'][s:s+150]);r=b['phase_ipsi_dot'][s];e=np.gradient(a)*149*r/100;mask=abs(e)>1e-5
  key=tuple(b[k][s] for k in ['subject','task','task_id','task_info','step'])
  out.append({'rg':rg,'subject':b['subject'][s],'task':b['task'][s],'step':b['step'][s],'ratio':float(np.median(v[mask]/e[mask]))})
  if key in seen and a[0]!=seen[key]:collisions.append({'rg':rg,'key':key,'first_angle':seen[key],'other_angle':float(a[0])})
  seen[key]=float(a[0])
Path('/tmp/gtech-21-derivative-samples.json').write_text(json.dumps(out,indent=2))
Path('/tmp/gtech-21-collision-samples.json').write_text(json.dumps(collisions,indent=2))
print(json.dumps({'curves':len(out),'duplicate_metadata_keys':len(collisions),'ratios':[min(r['ratio'] for r in out),max(r['ratio'] for r in out)]}))
