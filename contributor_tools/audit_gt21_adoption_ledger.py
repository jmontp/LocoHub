"""Independent eligible-pair ledger for ONE bounded GT21 adoption recording.

Supports levelground/treadmill pilots. Numeric clocks/events come from original
MAT files; task windows use hash-bound native condition exports because the
restricted numeric reader cannot decode mixed label tables. No force/COP claim.
"""
import os
for _key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[_key]='1'
import argparse
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from contributor_tools.gt21_adoption_coverage import audit_complete_pairs
LIMIT=64*1024**2


def digest(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024**2),b''):result.update(block)
    return result.hexdigest()


def unique(items, predicate):
    found=[x for x in items if predicate(x)]
    if len(found)!=1:raise ValueError('Missing or ambiguous manifest evidence')
    return found[0]


def source_windows(clock, values, mode):
    """Mirror declared frozen admission rules, not the proposed per-region rule."""
    if mode not in ('levelground','treadmill'):raise ValueError('Unsupported source-window mode')
    if not clock or len(clock)!=len(values) or any(not math.isfinite(t) for t in clock):
        raise ValueError('Missing/nonfinite condition clock')
    if any(b<=a for a,b in zip(clock,clock[1:])):raise ValueError('Nonincreasing condition clock')
    targets=[i/20 for i in range(10,41)] if mode=='treadmill' else ['walk','turnccw','turncw','stand-walk','walk-stand']
    if mode=='treadmill' and any(not math.isfinite(v) for v in values):raise ValueError('Nonfinite speed evidence')
    windows=[]
    for target in targets:
        if mode=='treadmill':
            # Boundary equality can be sensitive to MATLAB colon rounding or
            # CSV precision: demand native clarification rather than guessing.
            if any(abs(abs(v-target)-.025)<1e-12 for v in values):
                raise ValueError('Speed exactly at tolerance boundary requires native reconciliation')
            mask=[abs(v-target)<=.025 for v in values]
        else:mask=[v==target for v in values]
        if mode=='levelground' and sum(mask)<50:continue
        start=None
        for i in range(len(mask)+1):
            hit=i<len(mask) and mask[i]
            if hit and start is None:start=i
            if not hit and start is not None:
                end=i-1
                # MATLAB treadmill uses 5000 samples, without duration test.
                admitted=end-start+1>=5000 if mode=='treadmill' else clock[end]-clock[start]>.05
                if admitted:windows.append({'start_s':clock[start],'end_s':clock[end],'label':target})
                start=None
    return windows


def check_record(folder):
    import numpy as np
    import pyarrow as pa
    import pyarrow.parquet as pq
    from contributor_tools.gt21_numeric_source import read_numeric_table
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    folder=Path(folder);manifest_path=folder/'conversion_manifest.json'
    manifest_hash=digest(manifest_path);manifest=json.loads(manifest_path.read_text())
    if manifest['status']!='converted_unreviewed':raise ValueError('Recording not completed')
    rec=manifest['recording'];mode=rec['mode']
    if mode not in ('levelground','treadmill'):raise ValueError('Terrain eligibility ledger not implemented')
    recording_id=f"gt21:{rec['subject']}/{rec['date']}/{mode}/{rec['recording']}"
    used=[]
    def source(channel):
        item=unique(manifest['sources'],lambda x:Path(x['path']).parent.name==channel and Path(x['path']).name==rec['recording'])
        path=Path(item['path'])
        if path.stat().st_size>LIMIT:raise MemoryError('Source exceeds 64 MiB admission')
        if digest(path)!=item['sha256']:raise ValueError('Original source changed')
        # Prevent a hash-valid but wrong recording's channel from being bound.
        if list(path.parts[-5:])!=[rec['subject'],rec['date'],mode,channel,rec['recording']]:
            raise ValueError('Source path does not match recording identity')
        used.append((path,item['sha256']))
        return path
    source('conditions')
    condition_item=unique(manifest['compressed_source_tables'],lambda x:x['name'].startswith('source_conditions_'))
    name=condition_item['name']
    if Path(name).name!=name:raise ValueError('Unsafe condition export path')
    path=folder/name
    output_item=unique(manifest['outputs'],lambda x:x['name']==name)
    if digest(path)!=output_item['sha256']:raise ValueError('Native condition export changed')
    used.append((path,output_item['sha256']))
    with gzip.open(path,'rb') as stream:raw=stream.read(LIMIT+1)
    if len(raw)>LIMIT:raise MemoryError('Condition export exceeds 64 MiB admission')
    if hashlib.sha256(raw).hexdigest()!=condition_item['uncompressed_sha256']:
        raise ValueError('Native condition content changed')
    field='Speed' if mode=='treadmill' else 'Label'
    rows=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    if not rows.fieldnames or len(set(rows.fieldnames))!=len(rows.fieldnames) or not {'Header',field}<=set(rows.fieldnames):
        raise ValueError('Missing or duplicate task-window columns')
    clock=[];values=[]
    for row in rows:
        if len(clock)>=2_000_000:raise MemoryError('Condition row admission exceeded')
        clock.append(float(row['Header']));values.append(float(row[field]) if mode=='treadmill' else row[field])
    del raw,rows
    windows=source_windows(clock,values,mode);del clock,values
    if not windows:raise ValueError('No supported source windows; cannot certify missing evidence')
    clocks={}
    for channel in ('ik_offset','id'):
        table=read_numeric_table(source(channel));clocks[channel]=table['Header'].copy();del table
    pairs=[];identity_map={}
    for side in ('left','right'):
        table=read_numeric_table(source('gc'+side.capitalize()))
        t=table['Header'];phase=table['HeelStrike']
        if not np.isfinite(phase).all() or np.any((phase<0)|(phase>100)):
            raise ValueError('Invalid source phase samples')
        reset=np.flatnonzero((phase==0)&np.r_[False,phase[:-1]>0])
        for ai,bi in zip(reset[:-1],reset[1:]):
            start,end=float(t[ai]),float(t[bi])
            matching=[w for w in windows if w['start_s']<=start and end<=w['end_s']]
            row={'side':side,'start_s':start,'end_s':end,'matching_windows':len(matching),
                'source_cycle_samples':int(bi-ai+1),'maximum_source_phase':float(np.max(phase[ai:bi+1])),
                'source_ik_samples':int(np.searchsorted(clocks['ik_offset'],end,side='right')-np.searchsorted(clocks['ik_offset'],start)),
                'source_id_samples':int(np.searchsorted(clocks['id'],end,side='right')-np.searchsorted(clocks['id'],start)),
                'matching_window_labels':[w['label'] for w in matching]}
            identity=f'{recording_id}:samples:{int(ai)+1}:{int(bi)+1}:{side}'
            row['observation_id']=identity;pairs.append(row);identity_map[identity]=row
        del table,t,phase
    path=folder/'phase.parquet';item=unique(manifest['outputs'],lambda x:x['name']=='phase.parquet')
    if digest(path)!=item['sha256']:raise ValueError('Output changed')
    used.append((path,item['sha256']))
    columns=['observation_id','source_recording_id','reference_side','source_start_time_s','source_end_time_s']
    actual=[]
    for batch in pq.ParquetFile(path).iter_batches(batch_size=150,columns=columns,use_threads=False):
        data=batch.to_pydict()
        if batch.num_rows!=150 or any(len(set(v))!=1 for v in data.values()):
            raise ValueError('Mixed or incomplete observation identity')
        identity=data['observation_id'][0]
        if data['source_recording_id'][0]!=recording_id or identity not in identity_map:
            raise ValueError('Output identity is not an original adjacent event pair')
        expected=identity_map[identity]
        if any(not isinstance(data[c][0],(int,float)) or not math.isfinite(data[c][0]) for c in ('source_start_time_s','source_end_time_s')):
            raise ValueError('Nonfinite output timing')
        if data['reference_side'][0]!=expected['side'] or any(abs(data[c][0]-expected[k])>1e-9 for c,k in [('source_start_time_s','start_s'),('source_end_time_s','end_s')]):
            raise ValueError('Output identity disagrees with source timing/side')
        actual.append({k:expected[k] for k in ('side','start_s','end_s')})
    report={'status':'checking','recording':rec,'source_pairs':pairs,'source_windows':windows,
        'manifest_sha256':manifest_hash,'scientific_approval':False,'force_cop_checked':False,
        'policy':'Frozen MATLAB global 50-label count / >0.05s region; treadmill 5000 samples within speed tolerance; 10 GC/IK/ID samples and phase max>=50',
        'code_sha256':{str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__).resolve(),ROOT/'contributor_tools/gt21_adoption_coverage.py',ROOT/'contributor_tools/gt21_numeric_source.py']},
        'limitations':['Only levelground/treadmill eligibility supported',
            'Condition labels use hash-bound native CSV, not independent opaque MAT decoding',
            'Source annotation agreement does not verify physical heel contact or anatomical conventions',
            'Per-contiguous-region 50-sample policy is not adopted; frozen aggregate rule retained']}
    try:
        report['coverage']=audit_complete_pairs(pairs,actual)
        report['status']='complete_eligible_pairs_checked_unreviewed'
    except ValueError as error:
        report.update(status='incomplete_or_ambiguous_eligible_pairs',reason=str(error))
    if digest(manifest_path)!=manifest_hash or any(digest(p)!=h for p,h in used):raise ValueError('Evidence changed during audit')
    report['evidence']=[{'path':str(p),'sha256':h} for p,h in used]
    return report


def main():
    import resource
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
    os.nice(max(0,19-os.nice(0)))
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path);parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    if args.report.exists():raise FileExistsError(args.report)
    report=check_record(args.folder)
    with args.report.open('x') as stream:json.dump(report,stream,indent=2);stream.write('\n')
    if report['status']!='complete_eligible_pairs_checked_unreviewed':raise SystemExit(1)


if __name__=='__main__':main()
