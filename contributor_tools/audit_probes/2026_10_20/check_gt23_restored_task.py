"""Verify original ball-toss annotations and bilateral angles after task restoration."""
import resource
resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from scipy.io import loadmat
import pyarrow as pa
pa.set_cpu_count(1);pa.set_io_thread_count(1)
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from contributor_tools.common.data_contract import inspect_contract
from contributor_tools.reconvert_recording import digest


def main():
    base=ROOT/'converted_datasets/reconversion_v2/gt23_all_tasks_phase_pilot_20261020'
    source=Path('/mnt/s/locomotion_data/Gtech_2023')
    parsing=source/'Segmentation/AB01/ball_toss_1_center_parsing.mat'
    angle=source/'RawData/AB01/CSV_Data/ball_toss_1/Joint_Angle.csv'
    annotations=loadmat(parsing)
    np.testing.assert_array_equal(annotations['left'],annotations['right'])
    expected={tuple(map(float,pair)) for pair in annotations['left']}
    raw=pd.read_csv(angle);frame=pd.read_parquet(base/'phase.parquet')
    assert inspect_contract(frame,mode='phase').schema_passed
    assert frame.task.eq('load_handling').all() and frame.task_id.eq('ball_toss').all()
    assert frame.source_recording_id.eq('gt23:AB01/ball_toss_1').all()
    checked=set();errors={}
    for _,curve in frame.groupby('observation_id',sort=False):
        assert len(curve)==150
        a,b=float(curve.source_start_time_s.iloc[0]),float(curve.source_end_time_s.iloc[0])
        assert (a,b) not in checked;checked.add((a,b))
        selected=raw[(raw.time>=a)&(raw.time<=b)]
        target=np.linspace(a,b,150)
        ref=curve.reference_side.iloc[0][0]
        for role,side in [('ipsi',ref),('contra','r' if ref=='l' else 'l')]:
            for original,canonical,sign in [('hip_flexion','hip_flexion',1),('knee_angle','knee_flexion',-1),('ankle_angle','ankle_dorsiflexion',1)]:
                values=np.interp(target,selected.time,selected[f'{original}_{side}']*sign*np.pi/180,left=np.nan,right=np.nan)
                col=f'{canonical}_angle_{role}_rad'
                np.testing.assert_allclose(curve[col],values,atol=1e-9,rtol=1e-9,equal_nan=True)
                errors[col]=max(errors.get(col,0),float(np.nanmax(abs(curve[col]-values))))
    assert checked==expected
    manifest=json.loads((base/'conversion_manifest.json').read_text())
    assert manifest['output_sha256']==digest(base/'phase.parquet')
    for path,value in manifest['code_sha256'].items():
        assert digest(base/'code'/path)==value and digest(ROOT/path)==value
    sources=[parsing,*sorted((angle.parent).glob('*.csv')),source/'RawData/AB01/Transforms/ball_toss_1.mat',source/'RawData/Subject_masses.csv']
    report={'observations':len(checked),'rows':len(frame),'schema_passed':True,'max_angle_errors_rad':errors,
        'source_sha256':{str(p):digest(p) for p in sources},'probe_sha256':digest(Path(__file__)),
        'output_sha256':digest(base/'phase.parquet'),'scientific_approval':False,
        'limitations':['One restored task window checked natively','Physical events, frame/sign conventions and remaining restored tasks need verification']}
    (base/'source_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['observations','rows','schema_passed','max_angle_errors_rad']}))


if __name__=='__main__':main()
