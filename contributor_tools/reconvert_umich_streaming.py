#!/usr/bin/env python3
"""Bounded UM21 treadmill kinematics reconstruction directly from Streaming.mat.

This is an explicitly partial staging export, not a replacement for the full
historical dataset. No inferred transfer pairing, ankle offsets, force directions,
or measured segment orientations are asserted. Each trial is independently saved.
"""
import argparse
import json
import os
from pathlib import Path
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.reconvert_recording import ensure_storage_headroom, digest

RATE_HZ = 100.0  # Streaming joint angles and heel-strike frame indices, source documentation.
INCLINES = {'d10': -10, 'd5': -5, 'i0': 0, 'i5': 5, 'i10': 10}


def matlab_text(file, ref):
    return ''.join(chr(int(c)) for c in file[ref][...].reshape(-1))


def bounded_array(dataset, max_bytes=1024*1024):
    if dataset.size * dataset.dtype.itemsize > max_bytes:
        raise MemoryError(f'Metadata array exceeds admission limit: {dataset.name}')
    return dataset[...]


def windows(events, file, incline):
    """Account for every consecutive source HS pair; never pair by row order."""
    import numpy as np
    cuts = bounded_array(events['cutPoints']).T
    labels = [matlab_text(file, r) for r in bounded_array(events['tasks']).reshape(-1)]
    if len(cuts) != len(labels):
        raise ValueError('Task labels and intervals disagree')
    for side, key in [('right', 'RHS'), ('left', 'LHS')]:
        hs = bounded_array(events[key]).reshape(-1)
        if not np.isfinite(hs).all() or not np.equal(hs, np.floor(hs)).all() or not (np.diff(hs)>0).all():
            raise ValueError(f'Invalid source heel-strike indices: {key}')
        for start, end in zip(hs[:-1], hs[1:]):
            matches = [i for i, (a,b) in enumerate(cuts) if a<=start and end<=b]
            if len(matches)!=1:
                yield {'side':side, 'start':int(start), 'end':int(end), 'excluded':'outside or ambiguous task interval'}
                continue
            label=labels[matches[0]]
            if label.startswith('s'):
                speed=float(label[1:].replace('x','.'))
                task='incline_walking' if incline>0 else 'decline_walking' if incline<0 else 'level_walking'
                info={'incline_deg':incline,'speed_m_s':speed,'surface':'treadmill'}
            elif label in {'a0x2','a0x5','d0x2','d0x5'}:
                task='transition'; info={'incline_deg':incline,'surface':'treadmill','transition_phase':'acceleration' if label[0]=='a' else 'deceleration','acceleration_m_s2':float(label[1:].replace('x','.'))*(1 if label[0]=='a' else -1)}
            else:
                yield {'side':side,'start':int(start),'end':int(end),'excluded':f'unsupported task label: {label}'}
                continue
            yield {'side':side,'start':int(start),'end':int(end),'task':task,'label':label,'info':info}


def cycle_frame(trial, subject, condition, window):
    import numpy as np
    import pandas as pd
    start,end=window['start'],window['end']
    if start<1 or end<=start or end-start+1>4096:
        raise ValueError('Source frame interval is invalid or exceeds 4096-sample admission limit')
    duration=(end-start)/RATE_HZ
    times=np.linspace(0,duration,150)
    recording=f'um21:Streaming/{subject}/Tread/{condition}'
    identity=f'{recording}:{window["side"]}:frames:{start}:{end}'
    fields={'subject':f'UM21_{subject}','source_recording_id':recording,'observation_id':identity,
            'reference_side':window['side'],'observation_type':'individual_cycle','task':window['task'],
            'task_id':window['label'],'task_info':json.dumps(window['info'],sort_keys=True),
            'source_start_time_s':(start-1)/RATE_HZ,'source_end_time_s':(end-1)/RATE_HZ,
            'phase_ipsi':np.linspace(0,100,150),'time_s':times,'step':identity}
    def read(name,plane=0):
        ds=trial.get('jointAngles/'+name)
        if ds is None: return np.full(150,np.nan)
        if ds.ndim!=2 or ds.shape[0]!=3 or ds.shape[1]<end:
            raise ValueError(f'Unexpected source dimensions: {name}')
        raw=ds[plane,start-1:end]
        # np.interp retains gaps adjacent to NaN; never bridge missing measurements.
        return np.interp(np.linspace(0,len(raw)-1,150),np.arange(len(raw)),raw)*np.pi/180
    pelvis=read('RPelvisAngles');fields['pelvis_sagittal_angle_rad']=pelvis
    for role,leg in [('ipsi','R' if window['side']=='right' else 'L'),('contra','L' if window['side']=='right' else 'R')]:
        hip=read(leg+'HipAngles');knee=read(leg+'KneeAngles')
        fields[f'hip_flexion_angle_{role}_rad']=hip
        fields[f'knee_flexion_angle_{role}_rad']=knee
        fields[f'thigh_sagittal_angle_{role}_rad']=pelvis+hip
        fields[f'shank_sagittal_angle_{role}_rad']=pelvis+hip-knee
        # Preserve the original ankle channel, without a waveform-selected 90-degree correction.
        fields[f'source_ankle_sagittal_angle_{role}_rad']=read(leg+'AnkleAngles')
        fields[f'ankle_dorsiflexion_angle_{role}_rad']=np.full(150,np.nan)
        for joint in ['hip_flexion','knee_flexion']:
            fields[f'{joint}_velocity_{role}_rad_s']=np.gradient(fields[f'{joint}_angle_{role}_rad'],times)
    return pd.DataFrame(fields)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'contributor_tools/conversion_scripts/Umich_2021/Streaming.mat')
    parser.add_argument('--output-root',type=Path,required=True)
    parser.add_argument('--max-recordings',type=int)
    parser.add_argument('--delay-seconds',type=float,default=2)
    args=parser.parse_args()
    if args.delay_seconds<0 or (args.max_recordings is not None and args.max_recordings<1):parser.error('Invalid limit/delay')
    for key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:
        os.environ[key]='1'
    os.nice(max(0,19-os.nice(0)))
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
    ensure_storage_headroom(args.output_root)
    args.output_root.mkdir(parents=True,exist_ok=False)
    import h5py
    import pyarrow as pa
    import pyarrow.parquet as pq
    from contributor_tools.common.data_contract import inspect_contract
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    (args.output_root/'converter_snapshot.py').write_text(Path(__file__).read_text())
    source_stat=args.source.stat()
    source={'path':str(args.source.resolve()),'bytes':source_stat.st_size,'mtime_ns':source_stat.st_mtime_ns,'sha256':digest(args.source)}
    evidence={'review_status':'unreviewed','scope':'UM21 Streaming/Tread sagittal hip/knee kinematics only; partial staging export',
              'source':source,'code_sha256':digest(Path(__file__)),
              'dependency_sha256':{str(p.relative_to(ROOT)):digest(p) for p in [ROOT/'contributor_tools/common/data_contract.py',ROOT/'contributor_tools/reconvert_recording.py']},
              'versions':{'h5py':h5py.__version__,'pyarrow':pa.__version__}, 'sample_rate_hz':RATE_HZ,
              'limitations':['No full scientific approval','Ankle canonical values withheld pending offset convention review; unmodified source channel retained',
                             'Thigh/shank are joint-chain derived, not independent segment measurements',
                             'Moments, forces, COP and nonsagittal signals not converted in this staging pass',
                             'Run, Wtr, Stair and Sts/Normalized transfers not converted in this staging pass; no guessed transfer duration or bilateral pairing'],
              'recordings':[],'status':'running'}
    summary=args.output_root/'conversion_summary.json'
    def save():
        evidence['peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        temp=summary.with_suffix('.tmp');temp.write_text(json.dumps(evidence,indent=2)+'\n');temp.replace(summary)
    save()
    try:
        with h5py.File(args.source,'r',rdcc_nbytes=1024*1024) as source_file:
            plan=[(subject,condition) for subject in source_file['Streaming'] if 'Tread' in source_file[f'Streaming/{subject}'] for condition in source_file[f'Streaming/{subject}/Tread'] if condition in INCLINES]
            evidence['available_recordings']=len(plan)
            if args.max_recordings:plan=plan[:args.max_recordings]
            evidence['planned_recordings']=len(plan)
            for subject,condition in plan:
                if (args.output_root/'STOP_AFTER_CURRENT').exists():evidence['status']='stopped_by_request';break
                ensure_storage_headroom(args.output_root)
                available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
                if available<2*1024**3:raise MemoryError('Less than 2 GiB available; stopped at recording boundary')
                trial=source_file[f'Streaming/{subject}/Tread/{condition}']
                out=args.output_root/subject/condition;out.mkdir(parents=True)
                entry={'subject':subject,'condition':condition,'observations':0,'rows':0,'excluded':0}
                writer=None;identities=set()
                try:
                    with (out/'candidate_ledger.jsonl').open('w') as ledger:
                        for window in windows(trial['events'],source_file,INCLINES[condition]):
                            if 'excluded' in window:entry['excluded']+=1;ledger.write(json.dumps(window)+'\n');continue
                            df=cycle_frame(trial,subject,condition,window)
                            result=inspect_contract(df,mode='phase')
                            if not result.schema_passed:raise ValueError(str(result.to_dict()))
                            key=df.observation_id.iloc[0]
                            if key in identities:raise ValueError('Duplicate observation identity')
                            identities.add(key)
                            table=pa.Table.from_pandas(df,preserve_index=False)
                            if writer is None:writer=pq.ParquetWriter(out/'phase.parquet.partial',table.schema,compression='zstd')
                            writer.write_table(table)
                            entry['observations']+=1;entry['rows']+=150
                            ledger.write(json.dumps({**window,'observation_id':key,'status':'written_unreviewed'})+'\n')
                finally:
                    if writer is not None:writer.close()
                if not entry['observations']:raise ValueError('No observations produced')
                output=out/'phase.parquet';output.with_suffix('.parquet.partial').replace(output)
                entry.update({'path':str(output.relative_to(args.output_root)),'sha256':digest(output),'bytes':output.stat().st_size,'schema_passed':True})
                evidence['recordings'].append(entry);save();print(json.dumps(entry),flush=True)
                time.sleep(args.delay_seconds)
            else:evidence['status']='complete_partial_scope'
        if (args.source.stat().st_size,args.source.stat().st_mtime_ns)!=(source_stat.st_size,source_stat.st_mtime_ns):raise ValueError('Source file changed during conversion')
    except Exception as exc:
        evidence['status']='stopped_error';evidence['error']=str(exc);save();raise
    save()


if __name__=='__main__':main()
