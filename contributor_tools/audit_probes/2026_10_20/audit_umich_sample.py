# Archived read-only investigation probe, 2026-10-20.
# Run from repository root with OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
# and nice -n 19 ionice -c 3. Local source paths and file versions are required.
# Results are scoped samples, not release approval.
import resource,json
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
import numpy as np,pyarrow.parquet as pq,h5py
from pathlib import Path
out=[]
for p in Path('converted_datasets').glob('umich*.parquet'):
 f=pq.ParquetFile(p);cols=['subject','task','step','time_s','hip_flexion_angle_ipsi_rad','hip_flexion_velocity_ipsi_rad_s','knee_flexion_angle_ipsi_rad','thigh_sagittal_angle_ipsi_rad','shank_sagittal_angle_ipsi_rad','foot_sagittal_angle_ipsi_rad','ankle_dorsiflexion_angle_ipsi_rad','pelvis_sagittal_angle_rad']
 d=next(f.iter_batches(batch_size=150,columns=cols,use_threads=False)).to_pydict();a={k:np.array(v) for k,v in d.items()};record={'file':str(p),'rows':[0,149],'subject':d['subject'][0],'task':d['task'][0],'step':d['step'][0]}
 for name,res in [('knee',a['knee_flexion_angle_ipsi_rad']-(a['thigh_sagittal_angle_ipsi_rad']-a['shank_sagittal_angle_ipsi_rad'])),('hip',a['hip_flexion_angle_ipsi_rad']-(a['thigh_sagittal_angle_ipsi_rad']-a['pelvis_sagittal_angle_rad'])),('ankle',a['ankle_dorsiflexion_angle_ipsi_rad']-(a['foot_sagittal_angle_ipsi_rad']-a['shank_sagittal_angle_ipsi_rad']))]:record[name+'_chain_max_abs_residual']=float(np.nanmax(np.abs(res)))
 v=np.gradient(a['hip_flexion_angle_ipsi_rad'],a['time_s']);record['hip_velocity_interior_max_error']=float(np.max(np.abs(v[1:-1]-a['hip_flexion_velocity_ipsi_rad_s'][1:-1])));record['first_values']={k:v[0] for k,v in d.items()};out.append(record)
print(json.dumps(out,indent=2))
with h5py.File('contributor_tools/conversion_scripts/Umich_2021/Streaming.mat') as f:
 t=f['Streaming/AB01/Tread/d10'];print('events',[(k,v.shape) for k,v in t['events'].items()]);print('angles',[(k,v.shape) for k,v in t['jointAngles'].items()][:2]);print('RHS',t['events/RHS'][:,:5]);print('RStrideTime',t['events/RStrideTime'][:,:5]);print('cutPoints',t['events/cutPoints'][:,:3])
