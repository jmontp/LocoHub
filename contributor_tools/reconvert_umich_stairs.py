#!/usr/bin/env python3
"""Read explicitly sided UM21 stair annotations; audit inventory or export a pilot."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
import argparse
import json
from pathlib import Path
import re
import resource
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest,ensure_storage_headroom
from contributor_tools.reconvert_umich_streaming import bounded_array,matlab_text,cycle_frame
from contributor_tools.reconvert_umich_running import source_components


def stair_windows(trial,file,condition):
    import numpy as np
    match=re.fullmatch(r's(\d+)dg_(\d+)',condition)
    if not match:raise ValueError('Unknown stair trial name')
    incline,number=map(int,match.groups());direction='ascent' if number%2 else 'descent'
    events=trial['events'];cuts=bounded_array(events['cutPoints'])
    if cuts.ndim!=2 or cuts.shape[0]!=3:raise ValueError('Unknown stair annotation shape')
    identifier=''.join(chr(int(c)) for c in bounded_array(events['newID']).reshape(-1))
    if identifier!=('i' if direction=='ascent' else 'in')+str(incline):
        raise ValueError('Trial name and source incline/direction disagree')
    source_pairs={}
    for side,key in [('left','LHS'),('right','RHS')]:
        hs=bounded_array(events[key]).reshape(-1)
        if not np.isfinite(hs).all() or not np.equal(hs,np.floor(hs)).all() or not (np.diff(hs)>0).all():
            raise ValueError('Invalid source heel strikes')
        durations=bounded_array(events['LStrideTime' if side=='left' else 'RStrideTime']).reshape(-1)
        if not np.array_equal(np.diff(hs),durations):raise ValueError('Stride duration disagrees with heel strikes')
        source_pairs[side]={(int(a),int(b)) for a,b in zip(hs[:-1],hs[1:])}
    seen=set();windows=[];empty_annotations=[]
    for label_ref,side_ref,bounds_ref in cuts.T:
        label=matlab_text(file,label_ref)
        empty_side=bool(file[side_ref].attrs.get('MATLAB_empty',False))
        empty_bounds=bool(file[bounds_ref].attrs.get('MATLAB_empty',False))
        if empty_side or empty_bounds:
            if not (empty_side and empty_bounds):raise ValueError('Partially empty stair annotation')
            empty_annotations.append({'label':label,'reason':'source_annotation_explicitly_empty'})
            continue
        leg=matlab_text(file,side_ref)
        if leg not in ('L','R'):raise ValueError('Unknown source reference leg')
        side='left' if leg=='L' else 'right';bounds=bounded_array(file[bounds_ref]).reshape(-1)
        if len(bounds)!=2 or not np.isfinite(bounds).all() or not np.equal(bounds,np.floor(bounds)).all():
            raise ValueError('Invalid stair annotation bounds')
        start,end=map(int,bounds);identity=(side,start,end)
        if identity in seen:raise ValueError('Duplicate annotated stair observation')
        if (start,end) not in source_pairs[side]:raise ValueError('Stair annotation disagrees with sided consecutive heel strikes')
        seen.add(identity)
        info={'source_mode':'Stair','source_task_label':label,'stair_incline_deg':incline,
              'stair_direction':direction,'segmentation':'source_sided_cutpoints','source_sample_rate_hz':100}
        if re.fullmatch(r's\d+',label):task='stair_'+direction
        elif re.fullmatch(r'[ab]\d+',label):task='level_walking'
        elif label in ('w2s','s2w'):
            task='transition';info.update(transition_from='level_walking' if label=='w2s' else 'stair_'+direction,
                transition_to='stair_'+direction if label=='w2s' else 'level_walking')
        else:raise ValueError('Unknown source stair task label: '+label)
        windows.append({'side':side,'start':start,'end':end,'label':label,'task':task,'info':info})
    unannotated=[{'side':side,'start':a,'end':b,'reason':'no_source_task_annotation'}
        for side,pairs in source_pairs.items() for a,b in sorted(pairs) if (side,a,b) not in seen]
    return windows,unannotated+empty_annotations


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'contributor_tools/conversion_scripts/Umich_2021/Streaming.mat')
    parser.add_argument('--output-root',type=Path,required=True)
    parser.add_argument('--export-recordings',type=int,default=0,help='Number to export after the full metadata audit; zero audits only')
    args=parser.parse_args()
    if args.export_recordings<0:parser.error('Export count cannot be negative')
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
    import h5py
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    from contributor_tools.common.data_contract import inspect_contract
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    ensure_storage_headroom(args.output_root);args.output_root.mkdir(parents=True,exist_ok=False)
    code=[Path(__file__),ROOT/'contributor_tools/reconvert_umich_streaming.py',ROOT/'contributor_tools/reconvert_umich_running.py',ROOT/'contributor_tools/reconvert_recording.py',ROOT/'contributor_tools/common/data_contract.py']
    for p in code:
        dest=args.output_root/'code'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
    report={'status':'auditing','scientific_approval':False,'source_sha256':digest(args.source),
            'code_sha256':{str(p.relative_to(ROOT)):digest(p) for p in code},'recordings':[],
            'limitations':['Unannotated heel-strike pairs retained in exclusion ledger',
                'Canonical ankle convention and kinetic frames unresolved; source components preserved',
                'Markers not exported; derived segments are not independent measured orientations']}
    def save():
        p=args.output_root/'conversion_summary.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(report,indent=2)+'\n');tmp.replace(p)
    source_stat=args.source.stat()
    save()
    try:
        with h5py.File(args.source,'r',rdcc_nbytes=1024**2) as f:
            plan=[(s,c) for s in f['Streaming'] if 'Stair' in f['Streaming'][s] for c in f['Streaming'][s]['Stair']]
            for subject,condition in plan:
                trial=f[f'Streaming/{subject}/Stair/{condition}'];windows,unannotated=stair_windows(trial,f,condition)
                report['recordings'].append({'subject':subject,'condition':condition,'windows':windows,'unannotated':unannotated})
            report['status']='metadata_audited_unreviewed';save()
            for record in report['recordings'][:args.export_recordings]:
                if (args.output_root/'STOP_AFTER_CURRENT').exists():
                    report['status']='stopped_by_request';save();return
                available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
                if available<2*1024**3:raise MemoryError('Less than 2 GiB available')
                if any(digest(ROOT/name)!=sha for name,sha in report['code_sha256'].items()):
                    raise RuntimeError('Converter code changed during reconstruction')
                current=args.source.stat()
                if (current.st_size,current.st_mtime_ns)!=(source_stat.st_size,source_stat.st_mtime_ns):
                    raise RuntimeError('Source changed during reconstruction')
                ensure_storage_headroom(args.output_root)
                subject,condition=record['subject'],record['condition'];trial=f[f'Streaming/{subject}/Stair/{condition}']
                folder=args.output_root/subject/condition;folder.mkdir(parents=True)
                writer=None;rows=0
                try:
                    for window in record['windows']:
                        frame=cycle_frame(trial,subject,condition,window,mode='Stair')
                        values,mapping=source_components(trial,window['start'],window['end'])
                        frame=pd.concat([frame,pd.DataFrame(values)],axis=1)
                        result=inspect_contract(frame,mode='phase')
                        if not result.schema_passed:raise ValueError(str(result.issues[:3]))
                        table=pa.Table.from_pandas(frame,preserve_index=False)
                        if writer is None:writer=pq.ParquetWriter(folder/'phase.parquet.partial',table.schema,compression='zstd')
                        writer.write_table(table);rows+=len(frame)
                finally:
                    if writer is not None:writer.close()
                if not rows:raise ValueError('No annotated observations')
                (folder/'phase.parquet.partial').replace(folder/'phase.parquet')
                (folder/'source_columns.json').write_text(json.dumps(mapping,indent=2)+'\n')
                record.update(exported_rows=rows,outputs={str(p.relative_to(args.output_root)):digest(p) for p in folder.iterdir()})
                save()
            report['status']=('all_annotated_stair_cycles_exported_unreviewed' if args.export_recordings>=len(plan) else 'metadata_audited_pilot_exported_unreviewed') if args.export_recordings else 'metadata_audited_unreviewed'
    except Exception as error:
        report.update(status='failed',reason=str(error));raise
    finally:save()
    print(json.dumps({'status':report['status'],'recordings':len(report['recordings']),
        'annotated_observations':sum(len(r['windows']) for r in report['recordings']),
        'excluded_annotations_or_pairs':sum(len(r['unannotated']) for r in report['recordings']),
        'exported_rows':sum(r.get('exported_rows',0) for r in report['recordings'])}))


if __name__=='__main__':main()
