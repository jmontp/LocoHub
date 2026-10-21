"""Recover MBLUE stair reference legs from original force-event timestamps.

The normalized source stores both legs on one shared event window. Reconstruct
the original uniform-clock window from imresize's interior sample positions;
require an exact source-clock match and a unique source heel-strike side.
"""
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[name]='1'
import argparse
from collections import Counter
import json
from pathlib import Path
import resource
import sys
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest


def resized_uniform_clock(start, step, count):
    """Evaluate normalized cubic convolution with antialiasing and symmetric edges."""
    import numpy as np
    scale=101/count
    bandwidth=min(1.,scale)
    padding=int(np.ceil(2/bandwidth))+1
    positions=np.arange(-padding,count+padding)
    mirrored=np.pad(np.arange(count),(padding,padding),mode='symmetric')
    centers=(np.arange(101)+.5)/scale-.5
    distance=np.abs((centers[:,None]-positions[None,:])*bandwidth)
    weights=np.where(distance<=1,1.5*distance**3-2.5*distance**2+1,
                     np.where(distance<2,-.5*distance**3+2.5*distance**2-4*distance+2,0.))
    weights/=weights.sum(axis=1)[:,None]
    return weights@(start+mirrored*step)


def original_window(normalized, source_clock):
    import numpy as np
    t=np.asarray(normalized);clock=np.asarray(source_clock)
    if t.shape!=(101,) or len(clock)<2 or not np.isfinite(t).all():
        raise ValueError('Expected finite 101-point normalized clock')
    dt=float(np.median(np.diff(clock)))
    if dt<=0 or not np.allclose(np.diff(clock),dt,rtol=0,atol=1e-8):
        raise ValueError('Original clock must be uniform')
    count=round(float(np.median(np.diff(t[10:-10])))/dt*101)
    if count<2 or count>min(len(clock),10000):raise ValueError('Inferred source window exceeds bounded admission')
    start=t[50]-(count-1)*dt/2;end=t[50]+(count-1)*dt/2
    expected=resized_uniform_clock(start,dt,count)
    if not np.allclose(t,expected,rtol=0,atol=1e-8):
        raise ValueError('Clock does not match antialiased cubic resize')
    indices=[]
    for value in (start,end):
        matches=np.flatnonzero(np.isclose(clock,value,rtol=0,atol=1e-7))
        if len(matches)!=1:raise ValueError('Window endpoint has no unique source sample')
        indices.append(int(matches[0]))
    if indices[1]-indices[0]+1!=count:raise ValueError('Window length differs from source indices')
    return indices


def source_events(force, threshold):
    import numpy as np
    state=np.asarray(force)>threshold
    # MATLAB strfind([0 1]) returns the last sample before threshold crossing.
    candidates=np.flatnonzero(~state[:-1]&state[1:]);clean=[]
    for index in candidates:
        if not clean or index-clean[-1]>20:clean.append(int(index))
    return set(clean)


def read_mot(path, columns):
    import pandas as pd
    if path.stat().st_size>128*1024**2:raise MemoryError('MOT exceeds source admission')
    with path.open() as stream:
        for skip,line in enumerate(stream,1):
            if skip>100:raise ValueError('MOT header exceeds limit')
            if line.strip()=='endheader':break
        else:raise ValueError('MOT has no endheader')
    return pd.read_csv(path,sep=r'\s+',skiprows=skip,usecols=columns)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-root',type=Path,required=True);a=p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
    import numpy as np
    from scipy.io import loadmat
    inventory_path=ROOT/'converted_datasets/reconversion_v2/mblue_source_inventory_20261021/source_inventory.json'
    inventory=json.loads(inventory_path.read_text());a.output_root.mkdir(parents=True,exist_ok=False)
    report={'status':'checking','scientific_approval':False,'inventory_sha256':digest(inventory_path),
            'probe_sha256':digest(Path(__file__)),'records':[],
            'source_code_sha256':{str(p):digest(p) for p in [
                Path('/mnt/s/workspace/MBLUEAnkleOpenSimProcessing/Utility_TrialParsing/Parsing_Functions/parseNormalizeDataStairs.m'),
                Path('/mnt/s/workspace/MBLUEAnkleOpenSimProcessing/Utility_TrialParsing/Cleaning_Functions/cleanHeelstrikesTreadmillRaw.m'),
                Path('/mnt/c/Program Files/MATLAB/R2023b/toolbox/matlab/images/imresize.m'),
                Path('/mnt/c/Program Files/MATLAB/R2023b/toolbox/matlab/images/+matlab/+images/+internal/+resize/contributions.m')]},
            'limitations':['Source event convention is a force-threshold crossing, not independent physical contact ground truth',
                'Some final descent endpoints are marker-derived in the source parser; endpoint force-reset matches are reported separately',
                'This recovers reference-side evidence; it does not yet change converted outputs']}
    try:
        for source in inventory['sources']:
            path=Path(source['path']);assert digest(path)==source['sha256']
            data=loadmat(path,squeeze_me=False,struct_as_record=True)['dataOut'][0,0]
            subject=path.name.split('_')[0]
            info_path=path.with_name(subject+'_FileInfo.mat');info=loadmat(info_path,simplify_cells=True)['subject_info']
            for condition in ('bare','exo'):
                blocks=[r for r in inventory['blocks'] if r['subject']==subject and r['source_path'].startswith(condition+'/stairs/')]
                windows=[]
                for rec in blocks:
                    block=data
                    for part in rec['source_path'].split('/'):block=block[part][0,0]
                    assert np.array_equal(block['time_l'],block['time_r'])
                    for index in range(block['time_l'].shape[1]):
                        windows.append((rec['source_path'],index,block['time_l'][:,index]))
                filename=info['bare']['stairs']['vicon_filename'] if condition=='bare' else 'exo_'+info['exo']['stairs']['filename_suffix']
                candidates=sorted((Path('/mnt/s/locomotion_data/MBLUE_Ankle_Vicon')/subject).glob('*/'+filename+'_corrected.mot'))
                evidence=[]
                for force_path in candidates:
                    ik_path=force_path.with_name(filename+'_corrected_IK_Results.mot')
                    candidate={'force_path':str(force_path),'ik_path':str(ik_path),'windows':[]}
                    try:
                        force=read_mot(force_path,['time','ground_force1_vy','ground_force2_vy'])
                        clock=read_mot(ik_path,['time']).time.to_numpy()
                        if len(force)%len(clock):raise ValueError('Noninteger original downsampling factor')
                        force=force.iloc[::len(force)//len(clock)]
                        np.testing.assert_allclose(force.time,clock,atol=1e-7,rtol=0)
                        threshold=.03*float(force.ground_force1_vy.max())
                        events={side:source_events(force[col],threshold) for side,col in [('right','ground_force1_vy'),('left','ground_force2_vy')]}
                        for task,index,t in windows:
                            start,end=original_window(t,clock)
                            sides=[side for side,indices in events.items() if start in indices]
                            if len(sides)!=1:raise ValueError('No unique source reference side: '+task+':'+str(index+1))
                            side=sides[0]
                            candidate['windows'].append({'source_path':task,'source_curve_index':index+1,
                                'reference_side':side,'source_event_start_s':float(clock[start]),'source_event_end_s':float(clock[end]),
                                'end_matches_same_side_force_event':end in events[side]})
                        candidate.update(status='all_windows_matched',force_sha256=digest(force_path),ik_sha256=digest(ik_path))
                    except (ValueError,AssertionError,OSError,MemoryError) as error:
                        candidate.update(status='unresolved',reason=str(error))
                    evidence.append(candidate)
                matched=[r for r in evidence if r['status']=='all_windows_matched']
                report['records'].append({'subject':subject,'condition':condition,'normalized_sha256':source['sha256'],
                    'subject_info_sha256':digest(info_path),'expected_windows':len(windows),'candidates':evidence,
                    'status':'unique_source_matched' if len(matched)==1 else 'unresolved'})
        report['status']='all_stair_reference_windows_recovered_unreviewed' if all(r['status']=='unique_source_matched' for r in report['records']) else 'stair_reference_recovery_incomplete'
    except Exception as error:report.update(status='failed',reason=str(error));raise
    finally:(a.output_root/'reference_recovery.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'conditions':len(report['records']),
                      'resolved':sum(r['status']=='unique_source_matched' for r in report['records'])}))
    if report['status']!='all_stair_reference_windows_recovered_unreviewed':raise SystemExit(1)


if __name__=='__main__':main()
