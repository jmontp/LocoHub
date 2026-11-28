import resource
resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
from pathlib import Path
import json,numpy as np,pandas as pd,pyarrow.parquet as pq
base=Path('converted_datasets/reconversion_v2/gt24_backward_fix_pilot_20261020/gt24/Phase3/BT01')
raw=Path('/mnt/s/locomotion_data/GaTech_2024_TaskAgnostic/Phase3_Parsed/Parsed/BT01')
import pyarrow as pa
pa.set_cpu_count(1);pa.set_io_thread_count(1)
results=[]
for folder in sorted(base.iterdir()):
 p=pq.ParquetFile(folder/'phase.parquet');source=raw/folder.name/f'BT01_{folder.name}_angle_filt.csv'
 columns=['time']+[f'{joint}_{side}' for side in ['l','r'] for joint in ['hip_flexion','knee_angle']]
 frame=pd.read_csv(source,usecols=columns)
 worst=0.;checked=0
 for i in range(p.num_row_groups):
  batch=p.read_row_group(i,columns=['observation_id','task','reference_side','source_start_time_s','source_end_time_s']+[f'{joint}_flexion_angle_{side}_rad' for joint in ['hip','knee'] for side in ['ipsi','contra']],use_threads=False).to_pandas(use_threads=False)
  for _,curve in batch.groupby('observation_id',sort=False):
   assert len(curve)==150 and set(curve.task)=={'walk_backward'}
   _,a,b,side=curve.observation_id.iloc[0].rsplit(':',3);a,b=int(a),int(b)
   t=frame.time.iloc[a:b+1].to_numpy();target=np.linspace(t[0],t[-1],150)
   assert np.isclose(curve.source_start_time_s.iloc[0],t[0]) and np.isclose(curve.source_end_time_s.iloc[0],t[-1])
   for role,leg in [('ipsi','l' if side=='left' else 'r'),('contra','r' if side=='left' else 'l')]:
    for joint,source_joint,sign in [('hip','hip_flexion',1),('knee','knee_angle',-1)]:
     expected=np.interp(target,t,frame[f'{source_joint}_{leg}'].iloc[a:b+1])*sign*np.pi/180
     error=float(np.nanmax(abs(expected-curve[f'{joint}_flexion_angle_{role}_rad'].to_numpy())))
     assert error<1e-9,(folder.name,error)
     worst=max(worst,error)
   checked+=1
 results.append({'recording':folder.name,'observations_source_checked':checked,'max_abs_angle_error_rad':worst,'scope':'All hip/knee samples, both legs; original CSV frame endpoints and task name. Other signals not independently checked.'})
out=base.parent.parent.parent/'backward_source_check.json';out.write_text(json.dumps(results,indent=2));print(json.dumps(results))
