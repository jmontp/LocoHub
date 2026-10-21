"""Complete source-window/event and metadata gate for one GT21 terrain pilot.

Uses original numeric MAT events and source terrain scalar, plus hash-bound native
condition labels. Does not establish physical contact or force/COP correctness.
"""
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
from contributor_tools.audit_gt21_adoption_ledger import digest, unique, LIMIT, ROOT
from contributor_tools.gt21_adoption_coverage import audit_complete_pairs
from contributor_tools.gt21_terrain_metadata_gate import check_curve_metadata


def terrain_windows(clock, labels, mode):
    if mode not in ('ramp','stair'):raise ValueError('Terrain mode required')
    if not clock or len(clock)!=len(labels) or any(not math.isfinite(t) for t in clock):raise ValueError('Invalid condition clock')
    if any(b<=a for a,b in zip(clock,clock[1:])):raise ValueError('Nonincreasing condition clock')
    targets=[mode+'ascent',mode+'descent']
    targets += ['walk-'+x for x in targets]+[x+'-walk' for x in targets]
    windows=[]
    for target in targets:
        mask=[x==target for x in labels]
        if sum(mask)<50:continue  # Existing MATLAB aggregate label rule.
        start=None
        for i in range(len(mask)+1):
            hit=i<len(mask) and mask[i]
            if hit and start is None:start=i
            if not hit and start is not None:
                end=i-1
                if clock[end]-clock[start]>.05:
                    windows.append({'start_s':clock[start],'end_s':clock[end],'label':target})
                start=None
    return windows


def require_unambiguous_rounding(mode, raw):
    if not isinstance(raw,(int,float)) or isinstance(raw,bool) or not math.isfinite(raw) or raw<=0:
        raise ValueError('Invalid raw terrain scalar')
    scaled=raw*10 if mode=='ramp' else raw*.0254*1000
    if abs((scaled-math.floor(scaled))-.5)<1e-9:
        raise ValueError('Terrain at rounding boundary needs native MATLAB reconciliation')


def check_record(folder):
    import numpy as np
    import pyarrow as pa
    import pyarrow.parquet as pq
    from scipy.io import loadmat
    from contributor_tools.gt21_numeric_source import read_numeric_table
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    folder=Path(folder);mp=folder/'conversion_manifest.json';mh=digest(mp);manifest=json.loads(mp.read_text())
    if manifest['status']!='converted_unreviewed':raise ValueError('Completed conversion required')
    rec=manifest['recording'];mode=rec['mode']
    if mode not in ('ramp','stair'):raise ValueError('Terrain mode required')
    rid=f"gt21:{rec['subject']}/{rec['date']}/{mode}/{rec['recording']}";used=[]
    def source(channel):
        item=unique(manifest['sources'],lambda x:Path(x['path']).parent.name==channel)
        p=Path(item['path'])
        if list(p.parts[-5:])!=[rec['subject'],rec['date'],mode,channel,rec['recording']]:raise ValueError('Source identity mismatch')
        if p.stat().st_size>LIMIT:raise MemoryError('64 MiB source admission exceeded')
        if digest(p)!=item['sha256']:raise ValueError('Source hash changed')
        used.append((p,item['sha256']));return p
    condition_source=source('conditions');field='rampIncline' if mode=='ramp' else 'stairHeight'
    value=loadmat(condition_source,variable_names=[field]).get(field)
    if value is None or value.size!=1 or np.iscomplexobj(value):raise ValueError('Missing/nonreal scalar terrain')
    raw=float(value.item());require_unambiguous_rounding(mode,raw)
    item=unique(manifest['compressed_source_tables'],lambda x:x['name'].startswith('source_conditions_'))
    if Path(item['name']).name!=item['name']:raise ValueError('Unsafe condition export name')
    cp=folder/item['name'];expected=unique(manifest['outputs'],lambda x:x['name']==item['name'])['sha256']
    if digest(cp)!=expected:raise ValueError('Condition export changed')
    used.append((cp,expected))
    with gzip.open(cp,'rb') as stream:payload=stream.read(LIMIT+1)
    if len(payload)>LIMIT:raise MemoryError('Condition CSV admission exceeded')
    if hashlib.sha256(payload).hexdigest()!=item['uncompressed_sha256']:raise ValueError('Condition content hash mismatch')
    reader=csv.DictReader(io.StringIO(payload.decode('utf-8-sig')))
    if not reader.fieldnames or len(set(reader.fieldnames))!=len(reader.fieldnames) or not {'Header','Label'}<=set(reader.fieldnames):raise ValueError('Missing condition columns')
    clock=[];labels=[]
    for row in reader:
        if len(clock)>=2_000_000:raise MemoryError('Condition row admission exceeded')
        clock.append(float(row['Header']));labels.append(row['Label'])
    del reader,payload
    windows=terrain_windows(clock,labels,mode)
    if not windows:raise ValueError('No supported source terrain windows')
    clocks={}
    for channel in ('ik_offset','id'):
        table=read_numeric_table(source(channel));clocks[channel]=table['Header'].copy();del table
    pairs=[];by_identity={}
    for side in ('left','right'):
        table=read_numeric_table(source('gc'+side.capitalize()));t=table['Header'];phase=table['HeelStrike']
        if not np.isfinite(phase).all() or np.any((phase<0)|(phase>100)):raise ValueError('Invalid source phase')
        resets=np.flatnonzero((phase==0)&np.r_[False,phase[:-1]>0])
        for a,b in zip(resets[:-1],resets[1:]):
            start,end=float(t[a]),float(t[b]);matching=[w for w in windows if w['start_s']<=start and end<=w['end_s']]
            row={'side':side,'start_s':start,'end_s':end,'matching_windows':len(matching),
                'source_cycle_samples':int(b-a+1),'maximum_source_phase':float(np.max(phase[a:b+1])),
                'source_ik_samples':int(np.searchsorted(clocks['ik_offset'],end,'right')-np.searchsorted(clocks['ik_offset'],start)),
                'source_id_samples':int(np.searchsorted(clocks['id'],end,'right')-np.searchsorted(clocks['id'],start)),
                'observation_id':f'{rid}:samples:{int(a)+1}:{int(b)+1}:{side}'}
            pairs.append(row);by_identity[row['observation_id']]=row
        del table,t,phase
    p=folder/'phase.parquet';expected=unique(manifest['outputs'],lambda x:x['name']=='phase.parquet')['sha256']
    if digest(p)!=expected:raise ValueError('Output hash mismatch')
    used.append((p,expected));actual=[];metadata_checks=[]
    cols=['observation_id','source_recording_id','reference_side','source_start_time_s','source_end_time_s','task','task_id','task_info']
    for batch in pq.ParquetFile(p).iter_batches(batch_size=150,columns=cols,use_threads=False):
        rows=batch.to_pylist()
        if len(rows)!=150:raise ValueError('Incomplete cycle')
        identity=rows[0]['observation_id']
        if identity not in by_identity:raise ValueError('Output identity not a raw event pair')
        pair=by_identity[identity]
        for row in rows:
            if row['observation_id']!=identity or row['source_recording_id']!=rid or row['reference_side']!=pair['side']:raise ValueError('Mixed output identity')
            for col,key in [('source_start_time_s','start_s'),('source_end_time_s','end_s')]:
                if not isinstance(row[col],(int,float)) or not math.isfinite(row[col]) or abs(row[col]-pair[key])>1e-9:raise ValueError('Output clock differs from source event')
        lo=int(np.searchsorted(clock,pair['start_s']));hi=int(np.searchsorted(clock,pair['end_s'],'right'))
        selected=labels[lo:hi]
        # Whole-window coverage requires a complete contiguous source region,
        # not merely one label found somewhere between event timestamps.
        matching=[w for w in windows if w['start_s']<=pair['start_s'] and pair['end_s']<=w['end_s']]
        if len(matching)!=1 or not selected or set(selected)!={matching[0]['label']}:raise ValueError('Cycle not covered by one source label window')
        result=check_curve_metadata(rows,mode=mode,source_labels=selected,raw_terrain=raw)
        metadata_checks.append({'observation_id':identity,'source_label':result['source_label']})
        actual.append({k:pair[k] for k in ('side','start_s','end_s')})
    report={'status':'checking','scientific_approval':False,'force_cop_checked':False,'recording':rec,
        'source_windows':windows,'source_pairs':pairs,'metadata_checks':metadata_checks,'raw_terrain':{'field':field,'value':raw},
        'manifest_sha256':mh,'limitations':['Mixed condition labels decoded by native MATLAB, hash-bound here','Source event annotations are not physical contact ground truth','Frozen aggregate label-count rule retained; no new eligibility policy adopted','Near-half rounding boundaries rejected pending native reconciliation'],
        'code_sha256':{str(x.relative_to(ROOT)):digest(x) for x in [Path(__file__).resolve(),ROOT/'contributor_tools/gt21_terrain_metadata_gate.py',ROOT/'contributor_tools/gt21_adoption_coverage.py',ROOT/'contributor_tools/audit_gt21_adoption_ledger.py',ROOT/'contributor_tools/gt21_numeric_source.py']}}
    try:
        report['coverage']=audit_complete_pairs(pairs,actual);report['status']='complete_eligible_pairs_checked_unreviewed'
    except ValueError as error:report.update(status='incomplete_or_ambiguous_eligible_pairs',reason=str(error))
    if digest(mp)!=mh or any(digest(p)!=h for p,h in used):raise ValueError('Evidence changed during audit')
    report['evidence']=[{'path':str(p),'sha256':h} for p,h in used]
    return report
