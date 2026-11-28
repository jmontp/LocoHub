"""Bounded real-source check of MBLUE paired clocks, transfers and crouch."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import resource
resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pyarrow as pa
from scipy.io import loadmat
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest,ensure_storage_headroom
from contributor_tools.common.data_contract import inspect_contract
pa.set_cpu_count(1);pa.set_io_thread_count(1)
source=Path('/mnt/s/workspace/MBLUEAnkleOpenSimProcessing/Subject_Data/AB01_NormalizedStrides.mat')
code=ROOT/'contributor_tools/conversion_scripts/MBLUEAnkle/convert_mblue_ankle_to_parquet.py'
spec=importlib.util.spec_from_file_location('mblue_checked',code);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
out=ROOT/'converted_datasets/reconversion_v2/mblue_transfer_clock_pilot_v2_20261021';ensure_storage_headroom(out);out.mkdir(exist_ok=False)
(out/'converter_snapshot.py').write_bytes(code.read_bytes())
data=loadmat(source,squeeze_me=False,struct_as_record=True)['dataOut'][0,0]
results=[];allframes=[];seen=set()
for condition in ['bare','exo']:
    for path in [('STS','sit_stand'),('STS','stand_sit'),('crouch',)]:
        task_data=data[condition][0,0]
        for part in path:task_data=task_data[part][0,0]
        task,task_id,_=module.TASK_MAPPING[path[-1]]
        frames,_=module.process_bilateral_task(task_data,'AB01',module.SUBJECT_INFO['AB01']['mass'],task,task_id,condition,task_key=path[0],source_task_path='/'.join(path))
        assert len(frames)==task_data['time_l'].shape[1];maximum=0.;values=0
        for index,frame in enumerate(frames):
            assert inspect_contract(frame,mode='phase').schema_passed
            assert frame.source_curve_index.eq(index+1).all()
            identity=frame.observation_id.iloc[0];assert identity not in seen;seen.add(identity)
            left=task_data['time_l'][:,index];right=task_data['time_r'][:,index]
            np.testing.assert_array_equal(left,right)
            target=np.linspace(left[0],left[-1],150)
            np.testing.assert_allclose(frame.time_s,target-left[0],atol=1e-10)
            np.testing.assert_allclose(frame.source_start_time_s,left[0]);np.testing.assert_allclose(frame.source_end_time_s,left[-1])
            np.testing.assert_allclose(frame.phase_ipsi_dot,100/(left[-1]-left[0]))
            for role,side in [('ipsi','l'),('contra','r')]:
                for canonical,raw,sign in [('hip_flexion','hip_flexion',1),('knee_flexion','knee_angle',-1),('ankle_dorsiflexion','ankle_angle',1)]:
                    expected=np.interp(target,left,task_data[raw+'_'+side][:,index])*sign*np.pi/180
                    actual=frame[f'{canonical}_angle_{role}_rad'].to_numpy()
                    np.testing.assert_allclose(actual,expected,atol=1e-10,rtol=1e-10,equal_nan=True)
                    np.testing.assert_allclose(frame[f'{canonical}_velocity_{role}_rad_s'],np.gradient(expected,target),atol=1e-9,rtol=1e-9,equal_nan=True)
                    finite=np.isfinite(expected);values+=int(finite.sum())
                    if finite.any():maximum=max(maximum,float(np.max(abs(actual[finite]-expected[finite]))))
            allframes.append(frame)
        results.append({'condition':condition,'source_path':'/'.join(path),'observations':len(frames),'angle_values_checked':values,'max_angle_error_rad':maximum})
output=out/'phase_unreviewed.parquet';pd.concat(allframes,ignore_index=True).to_parquet(output,index=False)
report={'scientific_approval':False,'records':results,'source_sha256':digest(source),'converter_sha256':digest(code),'probe_sha256':digest(Path(__file__)),'output_sha256':digest(output),
    'limitations':['AB01 only; full subject/task reconstruction remains pending','Force/COP mapping, source convention interpretation and full-channel coverage remain unverified']}
(out/'source_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'observations':len(seen),'angle_values_checked':sum(r['angle_values_checked'] for r in results),'max_angle_error_rad':max(r['max_angle_error_rad'] for r in results)}))
