"""Account for every UM21 walk/run source heel-strike pair and task interval."""
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
import hashlib
import json
from pathlib import Path
import resource
resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
import h5py
import numpy as np
ROOT=Path(__file__).resolve().parents[3]


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def main():
    source=ROOT/'contributor_tools/conversion_scripts/Umich_2021/Streaming.mat'
    out=ROOT/'converted_datasets/reconversion_v2/um21_wtr_coverage_20261021';out.mkdir(exist_ok=False)
    records=[];absent=[]
    with h5py.File(source,'r',rdcc_nbytes=1024**2) as f:
        for subject in f['Streaming']:
            if 'Wtr' not in f['Streaming'][subject]:absent.append(subject);continue
            trial=f['Streaming/'+subject+'/Wtr'];events=trial['events']
            cuts=events['cutPoints'][...].T
            labels=[''.join(chr(int(c)) for c in f[r][...].flat) for r in events['tasks'][...].flat]
            assert len(cuts)==len(labels) and cuts.shape[1]==2
            assert np.isfinite(cuts).all() and np.equal(cuts,np.floor(cuts)).all() and (cuts[:,1]>cuts[:,0]).all()
            pairs=[];counts={};invalid_durations=[]
            for side,prefix in [('left','L'),('right','R')]:
                hs=events[prefix+'HS'][...].reshape(-1)
                durations=events[prefix+'StrideTime'][...].reshape(-1)
                assert np.isfinite(hs).all() and np.equal(hs,np.floor(hs)).all() and (np.diff(hs)>0).all()
                if not np.array_equal(np.diff(hs),durations):invalid_durations.append(side)
                for a,b in zip(hs[:-1],hs[1:]):
                    contained=[i for i,(start,end) in enumerate(cuts) if start<=a and b<=end]
                    overlaps=[i for i,(start,end) in enumerate(cuts) if start<b and a<end]
                    category='one_source_interval' if len(contained)==1 else 'ambiguous_intervals' if len(contained)>1 else 'crosses_interval_boundary' if overlaps else 'outside_annotated_protocol'
                    counts[category]=counts.get(category,0)+1
                    pairs.append({'side':side,'start_frame':int(a),'end_frame':int(b),'status':category,
                        'contained_intervals':contained,'overlapping_intervals':overlaps})
            channels={}
            for group in ['jointAngles','jointForces','jointMoments','jointPowers','forceplates','markers']:
                if group in trial:channels[group]={name:list(ds.shape) for name,ds in trial[group].items()}
            record={'subject':subject,'task_intervals':[{'index':i,'label':label,'start_frame':int(a),'end_frame':int(b)} for i,(label,(a,b)) in enumerate(zip(labels,cuts))],
                'counts':counts,'heel_strike_pairs':pairs,'stride_duration_mismatch_sides':invalid_durations,'channels':channels,
                'velocity_profile_shapes':{k:list(v.shape) for k,v in events['velProf'].items()} if 'velProf' in events else None}
            records.append(record)
    report={'source_sha256':digest(source),'probe_sha256':digest(Path(__file__)),'records':records,'subjects_without_Wtr':absent,
        'scientific_approval':False,'limitations':['Task intervals describe protocol speed/acceleration, not exact walking-to-running gait switch frames',
            'Cycles crossing or outside protocol intervals must not silently disappear or inherit a neighboring label',
            'Velocity profile clocks and measured-versus-commanded semantics have not been verified',
            'Metadata-only audit; no signals reconstructed or scientifically approved']}
    (out/'source_coverage.json').write_text(json.dumps(report,indent=2)+'\n')
    totals={}
    for r in records:
        for k,v in r['counts'].items():totals[k]=totals.get(k,0)+v
    print(json.dumps({'subjects':len(records),'absent':absent,'pair_counts':totals,'duration_mismatch_subjects':[r['subject'] for r in records if r['stride_duration_mismatch_sides']]}))


if __name__=='__main__':main()
