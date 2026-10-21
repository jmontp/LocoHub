"""Bounded real-source check of MBLUE AB01 bare walking temporal alignment."""
import resource
resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
from scipy.io import loadmat
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest, ensure_storage_headroom
source=Path('/mnt/s/workspace/MBLUEAnkleOpenSimProcessing/Subject_Data/AB01_NormalizedStrides.mat')
code=ROOT/'contributor_tools/conversion_scripts/MBLUEAnkle/convert_mblue_ankle_to_parquet.py'
spec=importlib.util.spec_from_file_location('mblue_checked',code);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
out=ROOT/'converted_datasets/reconversion_v2/mblue_overlap_pilot_20261020'
ensure_storage_headroom(out);out.mkdir(exist_ok=False)
data=loadmat(source,squeeze_me=False,struct_as_record=True)['dataOut'][0,0]['bare'][0,0]['level_1x0'][0,0]
frames,_=module.process_gait_task(data,'AB01',module.SUBJECT_INFO['AB01']['mass'],'level_walking','level_1x0',1.,'bare',task_key='level_1x0')
errors=[];position=0
for side,other in [('l','r'),('r','l')]:
 for index in range(data[f'time_{side}'].shape[1]):
  frame=frames[position];position+=1
  clock=data[f'time_{side}'][:,index];target=np.linspace(clock[0],clock[-1],150)
  # Independently check points lying strictly inside one opposite-leg source cycle.
  for row,t in enumerate(target):
   candidates=[j for j in range(data[f'time_{other}'].shape[1]) if data[f'time_{other}'][0,j]<t<data[f'time_{other}'][-1,j]]
   if len(candidates)!=1:continue
   j=candidates[0];times=data[f'time_{other}'][:,j]
   for joint,key,sign in [('hip_flexion','hip_flexion',1),('knee_flexion','knee_angle',-1),('ankle_dorsiflexion','ankle_angle',1)]:
    raw=data[f'{key}_{other}'][:,j]
    expected=np.interp(t,times,raw)*sign*np.pi/180
    actual=frame[f'{joint}_angle_contra_rad'].iloc[row]
    np.testing.assert_allclose(actual,expected,atol=1e-12,rtol=1e-10,equal_nan=True)
    if np.isfinite(expected):errors.append(abs(actual-expected))
  if 'pelvis_tilt' not in data.dtype.names:assert frame.pelvis_sagittal_angle_rad.isna().all()
import pandas as pd
import pyarrow as pa
pa.set_cpu_count(1);pa.set_io_thread_count(1)
path=out/'phase_unreviewed.parquet';pd.concat(frames,ignore_index=True).to_parquet(path,index=False)
report={'scientific_approval':False,'scope':'AB01 bare level walking at 1 m/s, both reference legs; opposite hip/knee/ankle samples with unique source time overlap.',
 'observations':len(frames),'compared_values':len(errors),'max_abs_error_rad':max(errors),
 'source_sha256':digest(source),'converter_sha256':digest(code),'output_sha256':digest(path),
 'limitations':['Legacy identities/metadata not yet migrated; not a publishable artifact.','Other conditions, signals, force/COP mappings and task coverage remain unverified.']}
(out/'source_comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
