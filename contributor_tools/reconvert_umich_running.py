#!/usr/bin/env python3
"""Reconstruct all UM21 Run trials with bounded source-component preservation.

Original 100 Hz joint channels retain their own components/units; this does not
claim canonical kinetic frames or resolve the ankle offset convention.
"""
import argparse
import json
import os
from pathlib import Path
import resource
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import ensure_storage_headroom,digest
from contributor_tools.reconvert_umich_streaming import bounded_array,cycle_frame
GROUPS={'jointAngles':('joint_angle','deg'),'jointForces':('joint_force','N_kg'),
        'jointMoments':('joint_moment','Nm_kg'),'jointPowers':('joint_power','W_kg')}


def running_windows(events,condition):
    import numpy as np
    import re
    if not re.fullmatch(r's\d+x\d+',condition):raise ValueError('Unknown running speed label')
    maximum=float(condition[1:].replace('x','.'))
    for side,key,duration_key in [('left','LHS','LStrideTime'),('right','RHS','RStrideTime')]:
        hs=bounded_array(events[key]).reshape(-1)
        durations=bounded_array(events[duration_key]).reshape(-1)
        if not np.isfinite(hs).all() or not np.equal(hs,np.floor(hs)).all() or not (np.diff(hs)>0).all():raise ValueError('Invalid source heel strikes')
        if not np.array_equal(np.diff(hs),durations):raise ValueError('Source stride durations disagree with heel-strike intervals')
        for start,end in zip(hs[:-1],hs[1:]):
            yield {'side':side,'start':int(start),'end':int(end),'task':'run','label':condition,
                'info':{'source_mode':'Run','surface':'level_ground','protocol_max_speed_m_s':maximum,
                        'segmentation':'source_heel_strike_frames','source_sample_rate_hz':100}}


def source_components(trial,start,end):
    import numpy as np
    fields={};mapping={}
    if start<1 or end<=start or end-start+1>4096:raise ValueError('Invalid or oversized source interval')
    target=np.linspace(start-1,end-1,150)
    clock=np.arange(start-1,end)
    for group,(kind,unit) in GROUPS.items():
        if group not in trial:continue
        for name,ds in trial[group].items():
            if ds.ndim!=2 or not 1<=ds.shape[0]<=3 or ds.shape[1]<end:raise ValueError(f'Unexpected source dimensions: {ds.name}')
            for component in range(ds.shape[0]):
                column=f'source_{kind}_{name.lower()}_component_{component}_{unit}'
                fields[column]=np.interp(target,clock,ds[component,start-1:end])
                mapping[column]={'group':group,'variable':name,'matlab_component_1based':component+1,'unit':unit,
                    'canonical_frame_verified':False}
    return fields,mapping


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'contributor_tools/conversion_scripts/Umich_2021/Streaming.mat')
    parser.add_argument('--output-root',type=Path,required=True)
    args=parser.parse_args()
    for key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
    os.nice(max(0,19-os.nice(0)))
    import h5py
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    from contributor_tools.common.data_contract import inspect_contract
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    ensure_storage_headroom(args.output_root);args.output_root.mkdir(parents=True,exist_ok=False)
    code=[Path(__file__),ROOT/'contributor_tools/reconvert_umich_streaming.py',ROOT/'contributor_tools/reconvert_recording.py',ROOT/'contributor_tools/common/data_contract.py']
    for path in code:
        dest=args.output_root/'code'/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(path.read_bytes())
    source_stat=args.source.stat()
    report={'status':'running','scientific_approval':False,'source_sha256':digest(args.source),
        'code_sha256':{str(p.relative_to(ROOT)):digest(p) for p in code},'recordings':[],
        'readme_sha256':digest(ROOT/'contributor_tools/conversion_scripts/Umich_2021/R01 Dataset README.pdf'),
        'limitations':['Canonical kinetic signs/frames and ankle offset not verified',
            'Forceplates and markers are not included; source joint channels retain documented source units/components',
            'Source event validity needs independent biomechanical review; non-running tasks remain separate']}
    def save():
        report['peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        p=args.output_root/'conversion_summary.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(report,indent=2)+'\n');tmp.replace(p)
    save()
    try:
        with h5py.File(args.source,'r',rdcc_nbytes=1024**2) as f:
            plan=[(s,c) for s in f['Streaming'] if 'Run' in f['Streaming'][s] for c in f['Streaming'][s]['Run']]
            report['available_recordings']=len(plan)
            for subject,condition in plan:
                if (args.output_root/'STOP_AFTER_CURRENT').exists():report['status']='stopped_by_request';break
                ensure_storage_headroom(args.output_root)
                available=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
                if available<2*1024**3:raise MemoryError('Less than 2 GiB available')
                trial=f[f'Streaming/{subject}/Run/{condition}'];folder=args.output_root/subject/condition;folder.mkdir(parents=True)
                writer=None;count=0;keys=set();column_map=None
                try:
                    with (folder/'candidate_ledger.jsonl').open('w') as ledger:
                        for window in running_windows(trial['events'],condition):
                            frame=cycle_frame(trial,subject,condition,window,mode='Run')
                            values,mapping=source_components(trial,window['start'],window['end'])
                            if column_map is not None and mapping!=column_map:raise ValueError('Source schema changed within trial')
                            column_map=mapping;frame=pd.concat([frame,pd.DataFrame(values)],axis=1)
                            checked=inspect_contract(frame,mode='phase')
                            if not checked.schema_passed:raise ValueError(str(checked.issues[:3]))
                            identity=frame.observation_id.iloc[0]
                            if identity in keys:raise ValueError('Repeated observation ID')
                            keys.add(identity)
                            table=pa.Table.from_pandas(frame,preserve_index=False)
                            if writer is None:writer=pq.ParquetWriter(folder/'phase.parquet.partial',table.schema,compression='zstd')
                            writer.write_table(table);count+=1
                            ledger.write(json.dumps({**window,'observation_id':identity,'status':'written_unreviewed'})+'\n')
                finally:
                    if writer is not None:writer.close()
                if not count:raise ValueError('No source cycles produced')
                (folder/'phase.parquet.partial').replace(folder/'phase.parquet')
                (folder/'source_columns.json').write_text(json.dumps(column_map,indent=2)+'\n')
                entry={'subject':subject,'condition':condition,'observations':count,'rows':150*count,
                    'source_component_columns':len(column_map),'outputs':{str(p.relative_to(args.output_root)):digest(p) for p in folder.iterdir() if p.is_file()}}
                report['recordings'].append(entry);save();print(json.dumps(entry),flush=True);time.sleep(2)
            else:report['status']='complete_running_source_channels_unreviewed'
        if (args.source.stat().st_size,args.source.stat().st_mtime_ns)!=(source_stat.st_size,source_stat.st_mtime_ns):raise ValueError('Source changed during conversion')
        if any(digest(ROOT/p)!=value for p,value in report['code_sha256'].items()):raise ValueError('Code changed during conversion')
    except Exception as error:
        report.update(status='stopped_error',reason=str(error));save();raise
    save()


if __name__=='__main__':main()
