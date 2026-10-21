#!/usr/bin/env python3
"""Bounded source readback of completed GT21 native records, optionally live.

Uses independently extracted source masses. A failed live check requests a stop
at the next recording boundary; it never terminates native MATLAB mid-write.
"""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import resource
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest,ensure_storage_headroom


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(path)


def check_record(folder,masses,mass_evidence):
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    from contributor_tools.common.data_contract import inspect_contract
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    manifest_path=folder/'conversion_manifest.json';manifest=json.loads(manifest_path.read_text())
    assert manifest['status']=='converted_unreviewed'
    for item in manifest['sources']+manifest['code']:
        assert digest(Path(item['path']))==item['sha256'],f"Source/code changed: {item['path']}"
    for item in manifest['outputs']:
        assert digest(folder/item['name'])==item['sha256'],f"Output changed: {item['name']}"
    mass_source=next(item for item in manifest['sources'] if Path(item['path']).name=='SubjectInfo.mat')
    assert mass_source['sha256']==mass_evidence['source_sha256']
    for item in manifest['compressed_source_tables']:
        h=hashlib.sha256()
        with gzip.open(folder/item['name'],'rb') as stream:
            for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
        assert h.hexdigest()==item['uncompressed_sha256']
    angle_columns=[f'{joint}_{leg}' for joint in ['hip_flexion','knee_angle','ankle_angle'] for leg in ['l','r']]
    moments_columns=[name+'_moment' for name in angle_columns]
    angles=pd.read_csv(folder/'source_ik_offset_data.csv.gz',usecols=['Header',*angle_columns])
    moments=pd.read_csv(folder/'source_id_data.csv.gz',usecols=['Header',*moments_columns])
    events={side:pd.read_csv(folder/f'source_gc{side.capitalize()}_data.csv.gz',usecols=['Header','HeelStrike']) for side in ['left','right']}
    for table in [angles,moments,*events.values()]:
        assert np.isfinite(table.Header).all() and np.all(np.diff(table.Header)>0),'Source clock not strictly increasing'
    event_pairs={}
    for side,table in events.items():
        hs=table.loc[table.HeelStrike.eq(0) & table.HeelStrike.shift().gt(0),'Header'].to_numpy()
        event_pairs[side]=list(zip(hs[:-1],hs[1:]))
    record=manifest['recording'];mass=masses[record['subject']]
    recording_id=f"gt21:{record['subject']}/{record['date']}/{record['mode']}/{record['recording']}"
    conditions=None
    if record['mode']=='levelground':
        candidates=list(folder.glob('source_conditions_*.csv.gz'));assert len(candidates)==1
        conditions=pd.read_csv(candidates[0])
    errors={};seen=set();observed={side:set() for side in events};rows=0;finite_values=0
    for batch in pq.ParquetFile(folder/'phase.parquet').iter_batches(batch_size=150,use_threads=False):
        curve=batch.to_pandas(use_threads=False)
        assert len(curve)==150 and curve.observation_id.nunique()==1
        assert inspect_contract(curve,mode='phase').schema_passed
        identity=curve.observation_id.iloc[0];assert identity not in seen;seen.add(identity)
        assert curve.source_recording_id.eq(recording_id).all()
        side=curve.reference_side.iloc[0]
        start=float(curve.source_start_time_s.iloc[0]);end=float(curve.source_end_time_s.iloc[0])
        if conditions is not None:
            info=json.loads(curve.task_info.iloc[0])
            assert 'speed_m_s' not in info,'Cohort mean is not a measured trial speed'
            category=next((v for v in ['slow','fast','normal'] if v in record['recording']),'unknown')
            assert info['speed_category']==category and info['speed_source']=='filename'
            if 'Label' in conditions:
                labels=conditions.loc[conditions.Header.between(start,end),'Label']
                assert len(labels)>0 and labels.nunique()==1,'Output crosses source task labels'
                expected_task={'walk':('level_walking','level'),'turnccw':('transition','turn_left'),
                    'turncw':('transition','turn_right'),'stand-walk':('transition','stand_to_walk'),
                    'walk-stand':('transition','walk_to_stand')}[labels.iloc[0]]
                assert curve.task.eq(expected_task[0]).all() and curve.task_id.eq(expected_task[1]).all()
        pairs=event_pairs[side]
        matches=[i for i,(a,b) in enumerate(pairs) if abs(a-start)<1e-9 and abs(b-end)<1e-9]
        assert len(matches)==1,'Output is not bounded by consecutive original heel strikes'
        assert matches[0] not in observed[side];observed[side].add(matches[0])
        np.testing.assert_allclose([json.loads(v)['weight_kg'] for v in curve.subject_metadata],mass,rtol=0,atol=1e-12)
        target=np.linspace(start,end,150)
        if 'phase_ipsi_dot' in curve:np.testing.assert_allclose(curve.phase_ipsi_dot,100/(end-start),rtol=1e-10,atol=1e-10)
        for role,leg in [('ipsi',side[0]),('contra','r' if side=='left' else 'l')]:
            for canonical,source,sign in [('hip_flexion','hip_flexion',1),('knee_flexion','knee_angle',-1),('ankle_dorsiflexion','ankle_angle',1)]:
                for kind,table,src,scale,unit in [('angle',angles,f'{source}_{leg}',sign*np.pi/180,'rad'),('moment',moments,f'{source}_{leg}_moment',sign/mass,'Nm_kg')]:
                    expected=np.interp(target,table.Header,table[src],left=np.nan,right=np.nan)*scale
                    col=f'{canonical}_{kind}_{role}_{unit}'
                    actual=curve[col].to_numpy();np.testing.assert_allclose(actual,expected,atol=1e-8,rtol=1e-8,equal_nan=True)
                    finite=np.isfinite(expected);finite_values+=int(finite.sum())
                    if finite.any():errors[col]=max(errors.get(col,0),float(np.max(abs(actual[finite]-expected[finite]))))
                    if kind=='angle':
                        col=f'{canonical}_velocity_{role}_rad_s';expected_v=np.gradient(expected,target)
                        actual=curve[col].to_numpy();np.testing.assert_allclose(actual,expected_v,atol=1e-7,rtol=1e-7,equal_nan=True)
                        finite=np.isfinite(expected_v);finite_values+=int(finite.sum())
                        if finite.any():errors[col]=max(errors.get(col,0),float(np.max(abs(actual[finite]-expected_v[finite]))))
        rows+=len(curve)
    omitted={side:[{'start_s':float(a),'end_s':float(b)} for i,(a,b) in enumerate(pairs) if i not in observed[side]] for side,pairs in event_pairs.items()}
    return {'status':'source_checked_unreviewed','record':record,'observations':len(seen),'rows':rows,
        'source_mass_kg':mass,'finite_values_checked':finite_values,'max_errors':errors,
        'unexported_source_event_pairs':omitted,'manifest_sha256':digest(manifest_path),
        'output_sha256':digest(folder/'phase.parquet'),'scientific_approval':False,
        'limitations':['Unexported event-pair reasons require separate reconciliation',
            'Force/COP and physical frame/sign conventions not verified by this arithmetic check']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch-root',type=Path,required=True)
    parser.add_argument('--output-root',type=Path,required=True)
    parser.add_argument('--mass-evidence',type=Path,default=ROOT/'converted_datasets/reconversion_v2/gt21_subject_mass_review_20261021')
    parser.add_argument('--watch-pid',type=int)
    args=parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
    import pandas as pd
    root=args.batch_root.resolve();out=args.output_root.resolve();ensure_storage_headroom(out);out.mkdir(parents=True,exist_ok=False)
    mass_evidence=json.loads((args.mass_evidence/'source_comparison.json').read_text())
    assert mass_evidence['native_exact_mass_readback']
    assert digest(args.mass_evidence/'subject_masses.csv')==mass_evidence['csv_sha256']
    table=pd.read_csv(args.mass_evidence/'subject_masses.csv');masses=dict(zip(table.Subject,table.Weight))
    plan=json.loads((root/'inventory.json').read_text())['recordings']
    state={'status':'checking','pid':os.getpid(),'planned_recordings':len(plan),'checked_recordings':0,
        'observations':0,'rows':0,'finite_values_checked':0,'unexported_event_pairs':0,
        'mass_evidence_sha256':digest(args.mass_evidence/'source_comparison.json'),'probe_sha256':digest(Path(__file__)),
        'scientific_approval':False,'records':[]}
    save(out/'audit_status.json',state)
    try:
        cursor=0
        while True:
            batch_state=json.loads((root/'batch_status.json').read_text())
            while cursor<int(batch_state.get('completed',0)):
                record=plan[cursor];folder=root/record['subject']/record['date']/record['mode']/Path(record['recording']).stem
                result=check_record(folder,masses,mass_evidence)
                target=out/'records'/folder.relative_to(root)/'source_comparison.json';save(target,result)
                cursor+=1;state['checked_recordings']=cursor
                for key in ['observations','rows','finite_values_checked']:state[key]+=result[key]
                state['unexported_event_pairs']+=sum(len(v) for v in result['unexported_source_event_pairs'].values())
                state['records'].append({'path':str(target.relative_to(out)),'sha256':digest(target)})
                save(out/'audit_status.json',state)
                print(json.dumps({'checked':cursor,'recording':record,'observations':result['observations']}),flush=True)
            alive=False
            if args.watch_pid:
                try:command=Path(f'/proc/{args.watch_pid}/cmdline').read_bytes();alive=b'run_gt21_native_batch.py' in command and str(root).encode() in command
                except FileNotFoundError:pass
            if not alive:
                state['status']='all_recordings_source_checked_unreviewed' if cursor==len(plan) and batch_state.get('status')=='complete_unreviewed' else 'checked_completed_subset_unreviewed'
                break
            state['status']='waiting_for_completed_recordings';save(out/'audit_status.json',state);time.sleep(10)
    except Exception as error:
        state.update(status='failed',reason=str(error))
        if args.watch_pid:(root/'STOP_AFTER_CURRENT').touch()
        raise
    finally:save(out/'audit_status.json',state)


if __name__=='__main__':main()
