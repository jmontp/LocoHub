"""Full-cycle same-physical-side ankle comparison; missing matches are unassessed.

The published positive-dorsiflexion degree convention supports rad=deg*pi/180.
Source validity is a separate question: matching curated data is not scientific approval.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import time


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024**2),b''):h.update(b)
    return h.hexdigest()


def physical_key(reference_side, role, start, end):
    if reference_side not in ('left','right') or role not in ('ipsi','contra'):
        raise ValueError('Unknown side/role')
    if not all(math.isfinite(v) and int(v)==v for v in (start,end)) or start<1 or end<=start:
        raise ValueError('Invalid source frame identity')
    side=reference_side if role=='ipsi' else ('right' if reference_side=='left' else 'left')
    return side,int(start),int(end)


def compare(values_rad, key, curated, read_curve):
    if len(values_rad)!=150:raise ValueError('Expected150 output samples')
    if key not in curated:
        return {'status':'unassessed_no_same_side_frame_counterpart','physical_side':key[0]}
    expected=read_curve(curated[key])
    if len(expected)!=150:raise ValueError('Expected150 curated samples')
    errors=[];mask_mismatch=False;invalid=False
    for a,b in zip(values_rad,expected):
        b=float(b)*math.pi/180
        if a is None:a=math.nan
        a=float(a)
        if math.isnan(a)!=math.isnan(b):mask_mismatch=True
        if math.isinf(a) or math.isinf(b):invalid=True
        if math.isfinite(a) and math.isfinite(b):errors.append(abs(a-b))
    maximum=max(errors,default=None)
    passed=not mask_mismatch and not invalid and maximum is not None and maximum<=1e-9
    return {'status':'matched_all150' if passed else 'mismatch','physical_side':key[0], 'finite_pairs':len(errors),'max_abs_error_rad':maximum,'missingness_mismatch':mask_mismatch,'nonfinite_infinity':invalid,'curated_task':curated[key]['task']}


def admit_dataset(ds):
    if ds.size*ds.dtype.itemsize>16*1024**2:raise ValueError('Source block admission exceeded')
    if ds.chunks and math.prod(ds.chunks)*ds.dtype.itemsize>16*1024**2:raise ValueError('Source chunk admission exceeded')


def audit(plan_path):
    import h5py
    import pyarrow.parquet as pq
    from contributor_tools.preserve_mblue_planar_estimates import headroom,windows_available_mib
    plan_path=Path(plan_path);plan=json.loads(plan_path.read_text());root=Path(plan['output_root'])
    if root.exists():raise FileExistsError('Fresh audit output required')
    if windows_available_mib()<2816:raise RuntimeError('Windows startup headroom below2816MiB')
    headroom(root.parent)
    bindings={**plan['bindings'],str(plan_path.resolve()):digest(plan_path)}
    def verify():
        for p,h in bindings.items():
            if digest(p)!=h:raise ValueError('Input/code changed: '+p)
    verify();root.mkdir();start=time.monotonic();last=0
    def guard():
        nonlocal last
        now=time.monotonic()
        if now-start>1800 or (root/'STOP').exists():raise RuntimeError('Timeout or STOP')
        if now-last>15:
            headroom(root)
            if windows_available_mib()<2048:raise RuntimeError('Windows runtime headroom below2048MiB')
            last=now
    counts=Counter();seen=set();record_counts=[]
    with h5py.File(plan['normalized'], 'r', rdcc_nbytes=1024**2) as source, (root/'comparisons.jsonl').open('x') as out:
        for record in plan['records']:
            guard();subject=record['subject'];condition=record['condition'];curated={}
            for task,block in source[f'Normalized/{subject}/Walk'].items():
                if condition not in block or not isinstance(block[condition],h5py.Group):continue
                block=block[condition];details=block['events/StrideDetails'];angles=block['jointAngles/AnkleAngles']
                admit_dataset(details);admit_dataset(angles)
                if details.ndim!=2 or details.shape[0]!=4 or details.shape[1]>10000:raise ValueError('Unexpected StrideDetails schema')
                n=details.shape[1]
                if angles.shape not in ((n,3,150),(3,150)) or (angles.ndim==2 and n!=1):raise ValueError('Unexpected ankle schema')
                for i in range(n):
                    a,b,d,leg=map(float,details[:,i])
                    if leg not in (1,2) or b-a!=d:raise ValueError('Invalid curated identity')
                    key=physical_key('left' if leg==1 else 'right','ipsi',a,b)
                    if key in curated:raise ValueError('Duplicate same-side curated frame identity')
                    curated[key]={'task':task,'path':angles.name,'index':i,'ndim':angles.ndim}
            def curve(ref):
                ds=source[ref['path']]
                return ds[ref['index'],0,:] if ref['ndim']==3 else ds[0,:]
            columns=['observation_id','reference_side','source_start_time_s','source_end_time_s','source_ankle_sagittal_angle_ipsi_rad','source_ankle_sagittal_angle_contra_rad']
            parquet=pq.ParquetFile(record['parquet']);observations=0
            if parquet.metadata.num_rows!=record['expected_observations']*150:raise ValueError('Output scope differs')
            for batch in parquet.iter_batches(batch_size=150,columns=columns,use_threads=False):
                guard();data=batch.to_pydict()
                if batch.num_rows!=150:raise ValueError('Incomplete observation')
                for c in columns[:4]:
                    if len(set(data[c]))!=1:raise ValueError('Mixed observation identity')
                identity=data['observation_id'][0];side=data['reference_side'][0]
                if identity in seen:raise ValueError('Duplicate observation')
                seen.add(identity);a=data['source_start_time_s'][0]*100+1;b=data['source_end_time_s'][0]*100+1
                if abs(a-round(a))>1e-7 or abs(b-round(b))>1e-7:raise ValueError('Noninteger source frames')
                a,b=round(a),round(b)
                if identity!=f'um21:Streaming/{subject}/Tread/{condition}:{side}:frames:{a}:{b}':raise ValueError('Recording identity differs')
                for role in ('ipsi','contra'):
                    key=physical_key(side,role,a,b)
                    result=compare(data[f'source_ankle_sagittal_angle_{role}_rad'],key,curated,curve)
                    out.write(json.dumps({'observation_id':identity,'role':role,'start_frame':a,'end_frame':b,**result},allow_nan=False)+'\n');counts[result['status']]+=1
                observations+=1
            record_counts.append({'subject':subject,'condition':condition,'observations':observations,'curated_cycles':len(curated)})
    verify()
    result={'status':'full_cycle_source_comparison_complete_unreviewed','scientific_approval':False,'counts':dict(counts),'records':record_counts,'bindings':bindings,'comparison_sha256':digest(root/'comparisons.jsonl'),'limitations':['No same-side exact-window curated counterpart is unassessed, not rejected.','Curated agreement is source fidelity, not independent anatomical validation.','No guessed offset or waveform-selected sign. Missing marker validity is not established here.']}
    with (root/'audit_summary.json').open('x') as f:json.dump(result,f,indent=2)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plan',required=True,type=Path);parser.add_argument('--run',action='store_true');args=parser.parse_args()
    if not args.run:print(json.dumps({'status':'not_executed','plan':str(args.plan)}));return
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,)*2);os.nice(19)
    print(json.dumps(audit(args.plan)))


if __name__=='__main__':main()
