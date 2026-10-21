"""Independent bounded comparisons for the seven GT25 source-backed pilot trials.

Run from repo root with one numerical thread, nice 19, ionice 3.
This verifies explicit source transforms, not clinical validity or event semantics.
"""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse
import resource
resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
import hashlib
import json
from pathlib import Path
import re
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
pa.set_cpu_count(1);pa.set_io_thread_count(1)
BASE=Path('converted_datasets/reconversion_v2/gt25_source_pilot_20261020')
SOURCE=Path('/mnt/s/locomotion_data/GaTech_2025_DomainAdaptation')


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024**2),b''):h.update(chunk)
    return h.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root',type=Path,default=BASE)
    args=parser.parse_args()
    base=args.output_root
    mass=float(re.search(r'^BT01:\s*[\d.]+ kg\s*\|\s*([\d.]+) kg',
                         (SOURCE/'readme.txt').read_text(),re.M).group(1))
    results=[]
    for folder in sorted((base/'gt25/Parsed/BT01').iterdir()):
        if not (folder/'phase.parquet').exists():
            raise AssertionError(f'No output for {folder.name}')
        parquet=pq.ParquetFile(folder/'phase.parquet')
        cache={};errors={};checked=0;identities=set()
        def source(kind,columns):
            key=(kind,tuple(columns))
            if key not in cache:
                path=SOURCE/'Parsed/BT01'/folder.name/f'BT01_{folder.name}_{kind}.csv'
                cache[key]=pd.read_csv(path,usecols=columns)
            return cache[key]
        clock=source('angle_filt',['time']).time.to_numpy()
        for batch in parquet.iter_batches(batch_size=150, use_threads=False):
            curve=batch.to_pandas(use_threads=False)
            key=curve.observation_id.iloc[0]
            assert len(curve)==150 and curve.observation_id.nunique()==1 and key not in identities
            identities.add(key)
            a,b=int(curve.source_start_sample.iloc[0]),int(curve.source_end_sample.iloc[0])
            times=clock[a:b+1];target=np.linspace(times[0],times[-1],150)
            assert np.isclose(curve.source_start_time_s.iloc[0],times[0]) and np.isclose(curve.source_end_time_s.iloc[0],times[-1])
            np.testing.assert_allclose(curve.phase_ipsi,np.linspace(0,100,150))
            assert json.loads(curve.subject_metadata.iloc[0])['weight_kg']==mass
            def compare(kind,col,output,scale=1):
                data=source(kind,[col])[col].to_numpy()[a:b+1]
                expected=np.interp(target,times,data)*scale
                actual=curve[output].to_numpy()
                np.testing.assert_allclose(actual,expected,rtol=1e-10,atol=1e-10,equal_nan=True)
                errors[output]=max(errors.get(output,0),float(np.nanmax(abs(actual-expected))))
                return expected
            ref='l' if curve.reference_side.iloc[0]=='left' else 'r'
            for role,leg in [('ipsi',ref),('contra','r' if ref=='l' else 'l')]:
                for joint,src,sign in [('hip_flexion','hip_flexion',1),('knee_flexion','knee_angle',-1)]:
                    expected=compare('angle_filt',f'{src}_{leg}',f'{joint}_angle_{role}_rad',sign*np.pi/180)
                    np.testing.assert_allclose(curve[f'{joint}_velocity_{role}_rad_s'],np.gradient(expected,target),atol=1e-8)
                for joint,src,sign in [('hip_flexion','hip_flexion',1),('knee_flexion','knee_angle',-1),('ankle_dorsiflexion','ankle_angle',1)]:
                    compare('moment_filt',f'{src}_{leg}_moment',f'{joint}_moment_{role}_Nm_kg',sign)
                compare('grf',f'fp_{leg}_force_y',f'grf_vertical_{role}_BW',1/(mass*9.81))
                for axis in ['x','z']:compare('grf',f'fp_{leg}_force_{axis}',f'source_grf_global_{axis}_{role}_N')
                for joint in ['hip','knee']:
                    compare('exo',f'{joint}_angle_{leg}_torque_interaction',f'{joint}_flexion_assistance_moment_{role}_Nm_kg',-1/mass)
                assert curve[f'grf_anterior_{role}_BW'].isna().all()
                assert curve[f'grf_lateral_{role}_BW'].isna().all()
            checked+=1
        results.append({'recording':folder.name,'observations_checked':checked,
                        'manifest_sha256':digest(folder/'conversion_manifest.json'),
                        'output_sha256':digest(folder/'phase.parquet'),'max_error_by_signal':errors})
    report={'scientific_approval':False,'source_mass_kg':mass,'source_readme_sha256':digest(SOURCE/'readme.txt'),
            'scope':'All pilot observations: identity, phase, original frame endpoints, both hip/knee angles and velocities, source joint moments, vertical and raw horizontal forces, hip/knee assistance torques.',
            'limitations':['Ankle sign convention requires reconciliation with source README; matching a source moment sign is not evidence its anatomical name is correct.',
                           'IMU-derived segment orientation, COP interpretation, event definitions and excluded candidates not independently approved.',
                           'Only BT01 selected recordings; full dataset regeneration and checks remain pending.'], 'recordings':results}
    (base/'source_comparison.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'recordings_checked':len(results),'observations_checked':sum(r['observations_checked'] for r in results),'worst_error':max(v for r in results for v in r['max_error_by_signal'].values())}))


if __name__=='__main__':main()
