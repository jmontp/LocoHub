"""Verify corrected repeat-recording selection and transfer direction labels."""
import resource
resource.setrlimit(resource.RLIMIT_AS, (768*1024**2, 768*1024**2))
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pyarrow as pa
from scipy.io import loadmat
pa.set_cpu_count(1); pa.set_io_thread_count(1)
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from contributor_tools.reconvert_recording import digest
from contributor_tools.common.data_contract import inspect_contract


def main():
    base = ROOT/'converted_datasets/reconversion_v2/gt23_native_transfer_pilot_20261020'
    source = Path('/mnt/s/locomotion_data/Gtech_2023')
    parsing = source/'Segmentation/AB03/sit_to_stand_1_2_short-arm_parsing.mat'
    annotations = loadmat(parsing)
    raw = pd.read_csv(source/'RawData/AB03/CSV_Data/sit_to_stand_1_2/Joint_Angle.csv')
    frame = pd.read_parquet(base/'phase.parquet')
    assert inspect_contract(frame, mode='phase').schema_passed
    assert set(frame.source_recording_id) == {'gt23:AB03/sit_to_stand_1_2'}
    expected = {(condition, float(a), float(b)) for condition in ['sitting', 'standing']
                for a, b in annotations['left_'+condition]}
    checked = set(); errors = {}; tasks = {}
    for _, curve in frame.groupby('observation_id', sort=False):
        assert len(curve) == 150 and curve.observation_type.eq('transfer').all()
        info = json.loads(curve.task_info.iloc[0]); condition = info['source_condition']
        task = 'stand_to_sit' if condition == 'sitting' else 'sit_to_stand'
        assert curve.task.eq(task).all()
        assert info['segmentation'] == 'source_named_transfer_interval'
        assert info['armrests'] is True
        a, b = float(curve.source_start_time_s.iloc[0]), float(curve.source_end_time_s.iloc[0])
        key = (condition, a, b); assert key not in checked; checked.add(key)
        tasks[task] = tasks.get(task, 0)+1
        selected = raw[(raw.time >= a) & (raw.time <= b)]
        target = np.linspace(a, b, 150)
        ref = curve.reference_side.iloc[0][0]
        for role, leg in [('ipsi', ref), ('contra', 'r' if ref == 'l' else 'l')]:
            for name, canonical, sign in [('hip_flexion','hip_flexion',1), ('knee_angle','knee_flexion',-1), ('ankle_angle','ankle_dorsiflexion',1)]:
                values = np.interp(target, selected.time, selected[f'{name}_{leg}']*sign*np.pi/180, left=np.nan, right=np.nan)
                col = f'{canonical}_angle_{role}_rad'
                np.testing.assert_allclose(curve[col], values, atol=1e-9, rtol=1e-9, equal_nan=True)
                errors[col] = max(errors.get(col,0),float(np.nanmax(abs(curve[col]-values))))
    assert checked == expected
    evidence = json.loads((base/'input_evidence.json').read_text())
    assert all(digest(Path(path)) == value for path,value in evidence['sources'].items())
    assert all(digest(ROOT/path) == value and digest(base/'code'/path) == value for path,value in evidence['code'].items())
    report = {'rows':len(frame), 'observations':len(checked), 'tasks':tasks,
              'max_angle_errors_rad':errors, 'schema_passed':True,
              'output_sha256':digest(base/'phase.parquet'), 'probe_sha256':digest(Path(__file__)),
              'limitations':['One native transfer recording only', 'Boundary precision and full scientific validation remain open']}
    (base/'source_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    manifest = {'status':'converted_unreviewed', **evidence, **report, 'scientific_approval':False}
    (base/'conversion_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
