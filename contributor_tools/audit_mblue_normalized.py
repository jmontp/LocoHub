#!/usr/bin/env python3
"""Independently read back completed MBLUE blocks, optionally following a worker."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse
import json
from pathlib import Path
import resource
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('batch',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--watch-pid',type=int);args=parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
    import numpy as np
    import pyarrow.parquet as pq
    from scipy.io import loadmat
    from scipy.interpolate import interp1d
    args.output.mkdir(parents=True,exist_ok=False)
    state={'status':'checking','pid':os.getpid(),'records':[],'observations':0,'finite_values_checked':0,'scientific_approval':False,'probe_sha256':digest(Path(__file__)),
        'limitations':['Checks source identities, clocks, joint angles/velocities/moments and vertical forces',
            'Arithmetic agreement is not approval of anatomical signs, force coordinates, event definitions or unexported source channels']}
    def save():
        p=args.output/'source_comparison.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(state,indent=2)+'\n');tmp.replace(p)
    save();loaded_subject=None;data=None
    try:
        while True:
            summary=json.loads((args.batch/'conversion_summary.json').read_text())
            for record in summary['records'][len(state['records']):]:
                subject=record['subject'];source=Path('/mnt/s/workspace/MBLUEAnkleOpenSimProcessing/Subject_Data')/(subject+'_NormalizedStrides.mat')
                if subject!=loaded_subject:
                    if digest(source)!=record['source_sha256']:raise ValueError('Source hash changed')
                    data=None;data=loadmat(source,squeeze_me=False,struct_as_record=True)['dataOut'][0,0];loaded_subject=subject
                    info_path=source.with_name(subject+'_FileInfo.mat');assert digest(info_path)==record['subject_info_sha256']
                    mass=float(loadmat(info_path,simplify_cells=True)['subject_info']['mass'])
                block=data
                for part in record['source_path'].split('/'):block=block[part][0,0]
                bilateral='/STS/' in record['source_path'] or record['source_path'].endswith('/crouch')
                expected_keys=set()
                for side in (['l'] if bilateral else ['l','r']):
                    values=block['hip_flexion_'+side];n=values.shape[1] if values.ndim==2 else 1 if values.size else 0
                    expected_keys.update((side,i) for i in range(n))
                seen=set();finite=0;max_error=0.
                for path,sha in record['outputs'].items():
                    file=args.batch/path;assert digest(file)==sha
                    for batch in pq.ParquetFile(file).iter_batches(batch_size=150,use_threads=False):
                        frame=batch.to_pandas(use_threads=False);assert len(frame)==150 and frame.observation_id.nunique()==1
                        side={'left':'l','right':'r'}[frame.reference_side.iloc[0]];index=int(frame.source_curve_index.iloc[0])-1
                        assert (side,index) in expected_keys and (side,index) not in seen;seen.add((side,index))
                        recording=f'mblue:{subject}_NormalizedStrides.mat:dataOut/'+record['source_path']
                        assert frame.source_recording_id.eq(recording).all() and frame.observation_id.eq(f'{recording}:{side}:column:{index+1}').all()
                        clocks=block['time_'+side];clock=clocks[:,index] if clocks.ndim==2 else clocks;target=np.linspace(clock[0],clock[-1],150)
                        np.testing.assert_allclose(frame.time_s,target-clock[0],atol=1e-10)
                        np.testing.assert_allclose(frame.source_start_time_s,clock[0]);np.testing.assert_allclose(frame.source_end_time_s,clock[-1])
                        assert all(json.loads(v)['weight_kg']==mass for v in frame.subject_metadata)
                        def expected(field,leg,scale):
                            if field not in block.dtype.names:return np.full(150,np.nan)
                            values=block[field];times=block['time_'+leg]
                            if values.ndim==1:values=values[:,None]
                            if times.ndim==1:times=times[:,None]
                            cols=[index] if bilateral or leg==side else range(times.shape[1])
                            predictions=[]
                            for col in cols:
                                raw=np.where(np.isfinite(values[:,col]),values[:,col]*scale,np.nan)
                                predictions.append(interp1d(times[:,col],raw,bounds_error=False,fill_value=np.nan)(target))
                            if len(predictions)==1:return predictions[0]
                            result=np.full(150,np.nan)
                            for j in range(150):
                                present=[v[j] for v in predictions if np.isfinite(v[j])]
                                if present and np.allclose(present,present[0],rtol=1e-7,atol=1e-10):result[j]=present[0]
                            return result
                        def compare(column,values,tolerance=1e-8):
                            nonlocal finite,max_error
                            actual=frame[column].to_numpy()
                            try:np.testing.assert_allclose(actual,values,atol=tolerance,rtol=tolerance,equal_nan=True)
                            except AssertionError as error:raise AssertionError(f'{subject}/{record["source_path"]} {side}:{index+1} {column}: {error}') from error
                            valid=np.isfinite(values);finite+=int(valid.sum())
                            if valid.any():max_error=max(max_error,float(np.max(abs(actual[valid]-values[valid]))))
                        for role,leg in [('ipsi',side),('contra','r' if side=='l' else 'l')]:
                            for canonical,raw,sign in [('hip_flexion','hip_flexion',1),('knee_flexion','knee_angle',-1),('ankle_dorsiflexion','ankle_angle',1)]:
                                angles=expected(raw+'_'+leg,leg,sign*np.pi/180)
                                compare(f'{canonical}_angle_{role}_rad',angles)
                                velocity=np.gradient(angles, (target[-1]-target[0])/149);velocity[~np.isfinite(angles)]=np.nan
                                compare(f'{canonical}_velocity_{role}_rad_s',velocity,1e-7)
                                compare(f'{canonical}_moment_{role}_Nm_kg',expected(raw+'_'+leg+'_moment',leg,sign/mass))
                            compare(f'grf_vertical_{role}_BW',expected('ForceN_'+leg,leg,1/(mass*9.81)))
                assert seen==expected_keys,'Missing source cycles'
                entry={'subject':subject,'source_path':record['source_path'],'observations':len(seen),'finite_values_checked':finite,'maximum_error':max_error}
                state['records'].append(entry);state['observations']+=len(seen);state['finite_values_checked']+=finite;save();print(json.dumps(entry),flush=True)
            alive=False
            if args.watch_pid:
                try:alive=b'reconvert_mblue_normalized.py' in Path(f'/proc/{args.watch_pid}/cmdline').read_bytes()
                except FileNotFoundError:pass
            if not alive:
                state['status']='all_normalized_blocks_source_checked_unreviewed' if len(state['records'])==summary['planned_blocks'] and summary['status']=='all_normalized_blocks_reconstructed_unreviewed' else 'checked_completed_subset_unreviewed';break
            state['status']='waiting_for_completed_blocks';save();time.sleep(5)
    except Exception as error:
        state.update(status='failed',reason=str(error))
        if args.watch_pid:(args.batch/'STOP_AFTER_CURRENT').touch()
        raise
    finally:save()


if __name__=='__main__':main()
