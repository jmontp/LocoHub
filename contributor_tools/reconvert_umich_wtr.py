#!/usr/bin/env python3
"""Preserve every UM21 Wtr cycle as a source-labeled companion table.

Canonical gait labels are deliberately null: protocol speed/acceleration is not
proof of the exact walking/running switch. This is not an approved release.
"""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
import argparse
import json
from pathlib import Path
import resource
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest,ensure_storage_headroom
from contributor_tools.reconvert_umich_running import source_components
from contributor_tools.reconvert_umich_streaming import bounded_array,matlab_text


def windows(events,file):
    import numpy as np
    cuts=bounded_array(events['cutPoints']).T
    labels=[matlab_text(file,r) for r in bounded_array(events['tasks']).flat]
    if cuts.shape!=(len(labels),2) or not np.isfinite(cuts).all() or not np.equal(cuts,np.floor(cuts)).all() or not (cuts[:,1]>cuts[:,0]).all():
        raise ValueError('Invalid source protocol intervals')
    for side,prefix in [('left','L'),('right','R')]:
        hs=bounded_array(events[prefix+'HS']).reshape(-1)
        if not np.isfinite(hs).all() or not np.equal(hs,np.floor(hs)).all() or not (np.diff(hs)>0).all():raise ValueError('Invalid source heel strikes')
        if not np.array_equal(np.diff(hs),bounded_array(events[prefix+'StrideTime']).reshape(-1)):raise ValueError('Stride duration mismatch')
        for a,b in zip(hs[:-1],hs[1:]):
            contained=[i for i,(start,end) in enumerate(cuts) if start<=a and b<=end]
            overlap=[i for i,(start,end) in enumerate(cuts) if start<b and a<end]
            status='one_source_interval' if len(contained)==1 else 'ambiguous_intervals' if len(contained)>1 else 'crosses_interval_boundary' if overlap else 'outside_annotated_protocol'
            yield {'side':side,'start':int(a),'end':int(b),'status':status,'contained_intervals':contained,
                'overlapping_intervals':[{'index':i,'label':labels[i],'start_frame':int(cuts[i,0]),'end_frame':int(cuts[i,1])} for i in overlap]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'contributor_tools/conversion_scripts/Umich_2021/Streaming.mat')
    parser.add_argument('--output-root',type=Path,required=True)
    parser.add_argument('--max-subjects',type=int)
    args=parser.parse_args()
    if args.max_subjects is not None and args.max_subjects<1:parser.error('max-subjects must be positive')
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
    import h5py
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    ensure_storage_headroom(args.output_root);args.output_root.mkdir(parents=True,exist_ok=False)
    code=[Path(__file__),ROOT/'contributor_tools/reconvert_umich_running.py',ROOT/'contributor_tools/reconvert_umich_streaming.py',ROOT/'contributor_tools/reconvert_recording.py']
    for p in code:
        dest=args.output_root/'code'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
    initial=args.source.stat()
    report={'status':'running','source_sha256':digest(args.source),'code_sha256':{str(p.relative_to(ROOT)):digest(p) for p in code},
        'scientific_approval':False,'format':'source_labeled_cycle_companion','records':[],
        'limitations':['Canonical gait task is null pending evidence of walking/running switch frames',
            'Source joint units/components retained; canonical kinetic frames and ankle conventions unresolved',
            'Forceplates, markers and velocity profiles are not included in this companion']}
    def save():
        p=args.output_root/'conversion_summary.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(report,indent=2)+'\n');tmp.replace(p)
    save()
    try:
        with h5py.File(args.source,'r',rdcc_nbytes=1024**2) as f:
            subjects=[s for s in f['Streaming'] if 'Wtr' in f['Streaming'][s]];report['source_subjects']=subjects
            for subject in subjects[:args.max_subjects]:
                if (args.output_root/'STOP_AFTER_CURRENT').exists():report['status']='stopped_by_request';save();return
                available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
                if available<2*1024**3:raise MemoryError('Less than 2 GiB available')
                ensure_storage_headroom(args.output_root)
                if any(digest(ROOT/name)!=sha for name,sha in report['code_sha256'].items()):raise RuntimeError('Code changed during conversion')
                if (args.source.stat().st_size,args.source.stat().st_mtime_ns)!=(initial.st_size,initial.st_mtime_ns):raise RuntimeError('Source changed')
                folder=args.output_root/subject;folder.mkdir();trial=f['Streaming/'+subject+'/Wtr'];writer=None;count=0;counts={};seen=set();mapping=None
                try:
                    with (folder/'cycle_ledger.jsonl').open('x') as ledger:
                        for w in windows(trial['events'],f):
                            a,b=w['start'],w['end'];recording='um21:Streaming/'+subject+'/Wtr';identity=f'{recording}:{w["side"]}:frames:{a}:{b}'
                            if identity in seen:raise ValueError('Duplicate cycle')
                            seen.add(identity)
                            fields,new_mapping=source_components(trial,a,b)
                            if mapping is not None and mapping!=new_mapping:raise ValueError('Source components changed')
                            mapping=new_mapping
                            fields.update(subject=subject,source_recording_id=recording,observation_id=identity,
                                reference_side=w['side'],observation_type='individual_cycle',task=pd.array([None]*150,dtype='string'),
                                task_assignment_status='unverified',source_start_frame=a,source_end_frame=b,
                                source_start_time_s=(a-1)/100,source_end_time_s=(b-1)/100,
                                time_s=np.linspace(0,(b-a)/100,150),phase_ipsi=np.linspace(0,100,150),
                                source_protocol_status=w['status'],source_protocol_intervals=json.dumps(w['overlapping_intervals']))
                            table=pa.Table.from_pandas(pd.DataFrame(fields),preserve_index=False)
                            if writer is None:writer=pq.ParquetWriter(folder/'source_cycles.parquet.partial',table.schema,compression='zstd')
                            writer.write_table(table);count+=1;counts[w['status']]=counts.get(w['status'],0)+1
                            ledger.write(json.dumps({**w,'observation_id':identity})+'\n')
                finally:
                    if writer is not None:writer.close()
                if not count:raise ValueError('No source cycles')
                (folder/'source_cycles.parquet.partial').replace(folder/'source_cycles.parquet')
                (folder/'source_columns.json').write_text(json.dumps(mapping,indent=2)+'\n')
                report['records'].append({'subject':subject,'observations':count,'rows':count*150,'protocol_counts':counts,
                    'outputs':{str(p.relative_to(args.output_root)):digest(p) for p in folder.iterdir()}});save()
            report['status']='all_wtr_source_cycles_preserved_unreviewed' if len(report['records'])==len(subjects) else 'pilot_source_cycles_preserved_unreviewed'
    except Exception as error:report.update(status='failed',reason=str(error));raise
    finally:save()
    print(json.dumps({'status':report['status'],'subjects':len(report['records']),'cycles':sum(r['observations'] for r in report['records'])}))


if __name__=='__main__':main()
