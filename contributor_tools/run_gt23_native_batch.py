#!/usr/bin/env python3
"""Serial, resumable GT23 time/phase reconstruction with bounded native workers.

Inventory by default. Results stay unreviewed; empty annotations and admission
failures are explicit unresolved records, never successful conversions.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest,ensure_storage_headroom
from contributor_tools.prepare_gt23_recording import KINDS,resolve_recording
CODE=ROOT/'contributor_tools/conversion_scripts/Gtech_2023'
GUARD=ROOT/'contributor_tools/run_gt23_recording_guarded.ps1'
LIMIT=64*1024**2


def save(path,value):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(path)


def windows(path):
    path=Path(path).resolve()
    if not str(path).startswith('/mnt/s/'):raise ValueError('Native paths must be on S')
    return 'S:'+str(path).removeprefix('/mnt/s').replace('/','\\')


def hashes(paths):
    return {str(p.resolve()):digest(p) for p in sorted(paths)}


def code_files():
    return [Path(__file__),GUARD,ROOT/'contributor_tools/run_matlab_recording_guarded.ps1',
        ROOT/'contributor_tools/prepare_gt23_recording.py',ROOT/'contributor_tools/reconvert_recording.py',
        *CODE.rglob('*.m'),*(CODE.parent/'matlab_common').glob('*.m'),
        *(ROOT/'contributor_tools/common').rglob('*.py')]


def inventory(root):
    import numpy as np
    from scipy.io import loadmat
    records=[]
    for path in sorted((root/'Segmentation').glob('AB*/*_parsing.mat')):
        if path.stat().st_size>4*1024**2:raise MemoryError('Parsing input exceeds 4 MiB')
        parsed=loadmat(path)
        intervals=[v for k,v in parsed.items() if not k.startswith('_') and isinstance(v,np.ndarray)
            and v.ndim==2 and v.shape[1]==2 and np.issubdtype(v.dtype,np.number) and v.size]
        if any(not np.isfinite(v).all() or not (v[:,1]>v[:,0]).all() for v in intervals):
            raise ValueError(f'Invalid source intervals: {path}')
        records.append({'subject':path.parent.name,'parsing':path.name,
            'recording':resolve_recording(root/'RawData'/path.parent.name/'CSV_Data',path.name),
            'has_intervals':bool(intervals),'parsing_sha256':digest(path)})
    return records


def sources(root,record):
    raw=root/'RawData'/record['subject']
    return [root/'Segmentation'/record['subject']/record['parsing'],root/'RawData/Subject_masses.csv',
        raw/'Transforms'/(record['recording']+'.mat'),
        *(raw/'CSV_Data'/record['recording']/(kind+'.csv') for kind in KINDS)]


def native(options,folder,mode):
    folder.mkdir(parents=True,exist_ok=True)
    save(folder/'options.json',options)
    command=['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-NonInteractive',
        '-ExecutionPolicy','Bypass','-File',windows(GUARD),'-OptionsPath',windows(folder/'options.json'),
        '-CodeDirectory',windows(CODE),'-MemoryMiB','2048','-TimeoutSeconds','300','-Mode',mode]
    # Guard owns the native process job and timeout; never kill only its wrapper.
    with (folder/'launcher.log').open('w') as log:
        result=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
    if result.returncode:raise RuntimeError(f'Native {mode} failed: {folder}')
    output=Path(options['output_path'].replace('S:', '/mnt/s').replace('\\','/'))
    status=json.loads((output.parent/'native_status.json').read_text(encoding='utf-8-sig'))
    if status.get('status')!='completed' or status.get('exit_code')!=0:raise RuntimeError('Native worker did not complete')
    if not output.is_file():raise RuntimeError(f'Native worker produced no output: {output}')
    return status


def structural(path,mode):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from contributor_tools.common.data_contract import inspect_contract
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    rows=0;identities=set();previous_time=None;previous_row=None
    for batch in pq.ParquetFile(path).iter_batches(batch_size=150 if mode=='phase' else 4096,use_threads=False):
        frame=batch.to_pandas(use_threads=False)
        checked=frame
        if mode=='time' and len(frame)==1 and previous_row is not None:
            import pandas as pd
            checked=pd.concat([previous_row,frame],ignore_index=True)
        result=inspect_contract(checked,mode=mode)
        if not result.schema_passed:raise ValueError(f'Structural failure: {result.issues[:3]}')
        if mode=='phase':
            if len(frame)!=150 or frame.observation_id.nunique()!=1:raise ValueError('Invalid phase observation')
            identity=frame.observation_id.iloc[0]
            if identity in identities:raise ValueError('Repeated observation identity')
            identities.add(identity)
        else:
            if previous_time is not None and frame.time_s.iloc[0]<=previous_time:raise ValueError('Time decreased across batches')
            previous_time=frame.time_s.iloc[-1]
            previous_row=frame.tail(1)
            identities.update(frame.observation_id)
        rows+=len(frame)
    if not rows:raise ValueError('Empty output')
    if mode=='time' and len(identities)!=1:raise ValueError('Expected one continuous source window')
    return {'rows':rows,'observations':len(identities),'schema_passed':True}


def resume_matches(manifest,source_hashes,code,folder):
    if manifest.get('status')=='converted_unreviewed' and not {'time/time.parquet','phase/phase.parquet'}.issubset(manifest.get('outputs',{})):
        return False
    return (manifest.get('status') in {'converted_unreviewed','no_source_intervals','deferred_input_admission'}
        and manifest.get('sources')==source_hashes and manifest.get('code')==code
        and bool(manifest.get('outputs'))
        and all((folder/name).is_file() and digest(folder/name)==value for name,value in manifest['outputs'].items()))


def run_record(root,record,out,code):
    paths=sources(root,record);source_hashes=hashes(paths)
    folder=out/record['subject']/Path(record['parsing']).stem
    manifest_path=folder/'conversion_manifest.json'
    if manifest_path.exists():
        previous=json.loads(manifest_path.read_text())
        if resume_matches(previous,source_hashes,code,folder):return previous
        raise ValueError(f'Existing artifact source/code/output mismatch: {folder}')
    folder.mkdir(parents=True,exist_ok=False)
    save(folder/'input_evidence.json',{'record':record,'sources':source_hashes,'code':code})
    manifest={'record':record,'sources':source_hashes,'code':code,'scientific_approval':False}
    prepared=None;view=root
    if not record['has_intervals']:
        manifest.update(status='no_source_intervals',reason='Original parsing has no nonempty Nx2 intervals; raw coverage unresolved')
    elif paths[2].stat().st_size>LIMIT:
        manifest.update(status='deferred_input_admission',reason='Original transform MAT exceeds 64 MiB preparation admission')
    else:
        if sum(p.stat().st_size for p in paths)>LIMIT:
            prepared=folder/'prepared_input'
            command=[sys.executable,str(ROOT/'contributor_tools/prepare_gt23_recording.py'),
                '--source-root',str(root),'--subject',record['subject'],'--parsing',record['parsing'],'--output-root',str(prepared)]
            with (folder/'preparation.log').open('w') as log:
                subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
            view=prepared
            preparation=json.loads((prepared/'source_window_manifest.json').read_text())
            # Bind every source used by preparation to the prelaunch source hashes.
            observed=dict(preparation['other_source_sha256'])
            observed.update({v['source']:v['source_sha256'] for v in preparation['csv_files'].values()})
            if observed!=source_hashes:raise ValueError('Prepared inputs differ from admitted source hashes')
            transform=prepared/'RawData'/record['subject']/'Transforms'/(record['recording']+'.mat')
            native({'source_path':windows(paths[2]),'output_path':windows(transform),
                'start_s':preparation['start_s'],'end_s':preparation['end_s']},folder/'transform_preparation','prepare-transforms')
            verification=json.loads(Path(str(transform)+'.verification.json').read_text())
            if not verification['exact_native_readback']:raise ValueError('Transform preparation readback failed')
            evidence=folder/'transform_preparation'
            for name in ['native_status.json','matlab.log']:
                shutil.copy2(transform.parent/name,evidence/name)
            save(evidence/'verification.json',verification)
            save(folder/'prepared_input_evidence.json',{'preparation':preparation,
                'prepared_hashes':hashes(sources(prepared,record))})
        if sum(p.stat().st_size for p in sources(view,record))>LIMIT:
            manifest.update(status='deferred_input_admission',reason='Prepared source window still exceeds 64 MiB native admission')
        else:
            checks={}
            for mode in ['time','phase']:
                destination=folder/mode/(mode+'.parquet')
                native({'data_root':windows(view),'subject':record['subject'],'recording':record['parsing'],
                    'output_path':windows(destination)},destination.parent,mode)
                checks[mode]=structural(destination,mode)
            manifest.update(status='converted_unreviewed',checks=checks)
    if hashes(paths)!=source_hashes:raise ValueError('Original source changed during conversion')
    if hashes(code_files())!=code:raise ValueError('Code changed during conversion')
    # Only discard this run's reproducible input excerpts, after their hashes and
    # native exact-readback evidence are saved. Original sources are untouched.
    if prepared is not None:shutil.rmtree(prepared)
    outputs=[p for p in folder.rglob('*') if p.is_file() and not any(x in {'temp','preferences'} for x in p.relative_to(folder).parts)]
    manifest['outputs']={str(p.relative_to(folder)):digest(p) for p in outputs}
    save(manifest_path,manifest)
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,default=Path('/mnt/s/locomotion_data/Gtech_2023'))
    parser.add_argument('--output-root',type=Path,required=True)
    parser.add_argument('--run',action='store_true')
    parser.add_argument('--max-recordings',type=int)
    args=parser.parse_args()
    if args.max_recordings is not None and args.max_recordings<1:parser.error('max-recordings must be positive')
    for key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
    import resource
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
    os.nice(max(0,19-os.nice(0)))
    root=args.source_root.resolve();out=args.output_root.resolve();ensure_storage_headroom(out)
    records=inventory(root)
    if not records:raise ValueError('No source parsing files')
    out.mkdir(parents=True,exist_ok=True)
    save(out/'inventory.json',{'records':records,'scientific_approval':False})
    if not args.run:
        print(json.dumps({'windows':len(records),'empty_annotations':sum(not r['has_intervals'] for r in records)}));return
    import fcntl
    lock=(out/'batch.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    files=code_files();code=hashes(files);code_path=out/'batch_code.json'
    if code_path.exists() and json.loads(code_path.read_text())!=code:raise ValueError('Batch code changed; use a new output root')
    save(code_path,code)
    for path in files:
        dest=out/'code_snapshot'/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():shutil.copy2(path,dest)
        elif digest(dest)!=code[str(path.resolve())]:raise ValueError('Code snapshot changed')
    state={'status':'running','pid':os.getpid(),'total':len(records),'processed':0,'converted':0,'unresolved':0,'scientific_approval':False}
    try:
        for record in records:
            if (out/'STOP_AFTER_CURRENT').exists():state['status']='stopped_by_request';break
            if args.max_recordings and state['processed']>=args.max_recordings:state['status']='partial_requested_limit';break
            ensure_storage_headroom(out)
            if hashes(files)!=code:raise RuntimeError('Code changed during batch')
            state['active_record']=record;save(out/'batch_status.json',state)
            result=run_record(root,record,out,code)
            state['processed']+=1
            state['converted' if result['status']=='converted_unreviewed' else 'unresolved']+=1
            save(out/'batch_status.json',state)
            print(json.dumps({'processed':state['processed'],'total':len(records),'record':record,'status':result['status']}),flush=True)
            time.sleep(2)
        else:state['status']='complete_with_unresolved_inputs' if state['unresolved'] else 'complete_unreviewed'
    except Exception as error:
        state.update(status='stopped_incomplete',reason=str(error));raise
    finally:save(out/'batch_status.json',state)


if __name__=='__main__':main()
