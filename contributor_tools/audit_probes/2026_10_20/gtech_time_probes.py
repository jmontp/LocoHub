# Archived read-only investigation probe, 2026-10-20.
# Run from repository root with OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
# and nice -n 19 ionice -c 3. Local source paths and file versions are required.
# Results are scoped samples, not release approval.
import resource
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
import pyarrow.parquet as pq,json,numpy as np
from pathlib import Path
out=[]
def bounds(v):
 a=np.array(v,dtype=float);a=a[np.isfinite(a)];return [float(min(a)),float(max(a))] if len(a) else None
for name in ['gtech_2021_time','gtech_2023_time','gtech_2024_time','gtech_2024_time_bt24']:
 f=pq.ParquetFile('converted_datasets/'+name+'.parquet');names=f.schema_arrow.names
 cols=[n for n in ['time_s','reference_leg','subject','task','collection_id','hip_flexion_angle_ipsi_rad','hip_flexion_moment_ipsi_Nm_kg','grf_vertical_ipsi_BW'] if n in names]
 for rg in sorted(set([0,f.num_row_groups-1])):
  size=sum(f.metadata.row_group(rg).column(names.index(c)).total_uncompressed_size for c in cols)
  if size>64*1024**2:out.append({'file':name,'rg':rg,'skipped_projected_bytes':size});continue
  b=next(f.iter_batches(batch_size=300,columns=cols,row_groups=[rg],use_threads=False)).to_pydict();dt=np.diff(b['time_s'])
  out.append({'file':name,'rg':rg,'rows':len(b['time_s']),'first_subject':b['subject'][0],'first_task':b['task'][0],'time_diffs_range':bounds(dt),'negative_time_steps':int(sum(dt<0)),'reference_leg_values':list(set(b.get('reference_leg',[]))),'signal_ranges':{k:bounds(v) for k,v in b.items() if k not in ['time_s','reference_leg','subject','task','collection_id']}})
Path('/tmp/gtech-time-probes.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
