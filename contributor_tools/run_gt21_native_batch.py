#!/usr/bin/env python3
"""Inventory or serially regenerate GT21 using guarded, isolated MATLAB workers.

Outputs remain unreviewed staging data. Resume requires matching source, code and
output hashes. Failure stops the batch without overwriting partial artifacts.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest, ensure_storage_headroom
CODE=ROOT/'contributor_tools/conversion_scripts/Gtech_2021'
GUARD=ROOT/'contributor_tools/run_matlab_recording_guarded.ps1'
MODES=('levelground','treadmill','ramp','stair')
CHANNELS=('conditions','ik_offset','id','gcLeft','gcRight','fp','markers')


def windows_path(path):
    path=Path(path).resolve()
    if not str(path).startswith('/mnt/s/'):
        raise ValueError('Native source/code/output paths must be on S')
    return 'S:'+str(path).removeprefix('/mnt/s').replace('/','\\')


def inventory(root):
    records=[]
    for subject in sorted(root.glob('AB*')):
        if not subject.is_dir():continue
        for date in sorted(subject.iterdir()):
            if not date.is_dir():continue
            for mode in MODES:
                for source in sorted((date/mode/'conditions').glob('*.mat')):
                    records.append({'subject':subject.name,'date':date.name,'mode':mode,'recording':source.name})
    return records


def evidence(paths):
    return [{'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':digest(p)} for p in paths]


def source_files(root,record):
    mode=root/record['subject']/record['date']/record['mode']
    paths=[root/'SubjectInfo.mat']
    paths += [mode/channel/record['recording'] for channel in CHANNELS if (mode/channel/record['recording']).is_file()]
    for channel in ('conditions','ik_offset','id','gcLeft','gcRight'):
        if not (mode/channel/record['recording']).is_file():
            raise ValueError(f'Missing required {channel}: {record}')
    total=sum(p.stat().st_size for p in paths)
    if total>64*1024**2:
        raise MemoryError(f'Native recording admission exceeded: {total/1024**2:.1f} MiB > 64 MiB')
    return paths


def resume_matches(manifest,sources,code,folder):
    return (manifest.get('status')=='converted_unreviewed'
            and manifest.get('sources')==sources and manifest.get('code')==code
            and bool(manifest.get('outputs'))
            and all((folder/item['name']).is_file() and digest(folder/item['name'])==item['sha256'] for item in manifest['outputs']))


def structural_check(path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from contributor_tools.common.data_contract import inspect_contract
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    identities=set();rows=0
    for batch in pq.ParquetFile(path).iter_batches(batch_size=150,use_threads=False):
        frame=batch.to_pandas(use_threads=False)
        result=inspect_contract(frame,mode='phase')
        if not result.schema_passed or len(frame)!=150 or frame.observation_id.nunique()!=1:
            raise ValueError(f'Output structural failure: {result.issues[:3]}')
        identity=frame.observation_id.iloc[0]
        if identity in identities:raise ValueError(f'Duplicate source observation: {identity}')
        identities.add(identity);rows+=len(frame)
    if not rows:raise ValueError('No observations in output')
    return {'rows':rows,'observations':len(identities),'schema_passed':True,'scientific_approval':False}


def compress_source_tables(folder):
    """Losslessly compress native comparison tables; verify before removing CSV."""
    import gzip
    import hashlib
    import shutil
    compressed=[]
    for source in sorted(folder.glob('source_*.csv')):
        original_hash=digest(source)
        target=source.with_suffix('.csv.gz')
        with source.open('rb') as reader, gzip.open(target,'xb',compresslevel=3) as writer:
            shutil.copyfileobj(reader,writer,length=1024*1024)
        restored=hashlib.sha256()
        with gzip.open(target,'rb') as reader:
            for block in iter(lambda:reader.read(1024*1024),b''):restored.update(block)
        if restored.hexdigest()!=original_hash:
            raise ValueError(f'Compressed source-table verification failed: {source}')
        compressed.append({'name':target.name,'uncompressed_sha256':original_hash})
        source.unlink()
    return compressed


def save(path,value):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(path)


def run_record(root,record,output,code):
    sources=evidence(source_files(root,record))
    folder=output/record['subject']/record['date']/record['mode']/Path(record['recording']).stem
    manifest_path=folder/'conversion_manifest.json'
    if manifest_path.exists():
        previous=json.loads(manifest_path.read_text())
        if resume_matches(previous,sources,code,folder):return previous
        raise ValueError(f'Existing output differs from requested source/code: {folder}')
    folder.mkdir(parents=True,exist_ok=False)
    options=dict(data_root=windows_path(root),output_path=windows_path(folder/'phase.parquet'),**record)
    save(folder/'options.json',options)
    save(folder/'input_manifest.json',{'sources':sources,'code':code})
    command=['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',windows_path(GUARD),'-OptionsPath',windows_path(folder/'options.json'),'-CodeDirectory',windows_path(CODE),'-MemoryMiB','2048','-TimeoutSeconds','300']
    # PowerShell owns a kill-on-close Windows job and its native timeout. Never
    # terminate this wrapper alone, which could leave an unobserved native child.
    with (folder/'launcher.log').open('w') as log:
        completed=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
    if completed.returncode:raise RuntimeError(f'Native worker failed; retained evidence at {folder}')
    status=json.loads((folder/'native_status.json').read_text(encoding='utf-8-sig'))
    if status.get('status')!='completed' or status.get('exit_code')!=0:
        raise RuntimeError(f'Native status does not confirm completion: {folder}')
    checks=structural_check(folder/'phase.parquet')
    compressed=compress_source_tables(folder)
    manifest={'status':'converted_unreviewed','recording':record,'sources':sources,'code':code,'checks':checks,'native_status':status,'compressed_source_tables':compressed,
              'outputs':[{'name':p.name,'sha256':digest(p)} for p in sorted(folder.iterdir()) if p.is_file() and p!=manifest_path]}
    save(manifest_path,manifest)
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,default=CODE/'CAMARGO_ET_AL_J_BIOMECH_DATASET')
    parser.add_argument('--output-root',type=Path,required=True)
    parser.add_argument('--run',action='store_true')
    parser.add_argument('--max-recordings',type=int)
    args=parser.parse_args()
    if args.max_recordings is not None and args.max_recordings<1:parser.error('max-recordings must be positive')
    root=args.source_root.resolve();out=args.output_root.resolve()
    ensure_storage_headroom(out)
    records=inventory(root)
    if not records:raise ValueError('No source recordings found')
    out.mkdir(parents=True,exist_ok=True)
    save(out/'inventory.json',{'recordings':records,'subjects':sorted({r['subject'] for r in records}),'scientific_approval':False})
    if not args.run:
        print(json.dumps({'recordings':len(records),'subjects':len({r['subject'] for r in records}),'status':'inventory_only'}));return
    for key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
    os.nice(max(0,19-os.nice(0)))
    import resource
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
    files=[Path(__file__),GUARD,CODE/'convert_gtech_2021_phase_to_parquet.m',*sorted((CODE/'utilities').glob('*.m')),*sorted((CODE.parent/'matlab_common').glob('*.m')),*sorted((ROOT/'contributor_tools/common').rglob('*.py')),ROOT/'contributor_tools/reconvert_recording.py']
    code=evidence(files)
    code_manifest=out/'batch_code.json'
    if code_manifest.exists():
        if json.loads(code_manifest.read_text())!=code:
            raise ValueError('Batch code changed; use a new output root')
    else:
        save(code_manifest,code)
        import shutil
        for path in files:
            target=out/'code_snapshot'/path.relative_to(ROOT)
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    state={'status':'running','pid':os.getpid(),'total':len(records),'completed':0,'observations':0,'scientific_approval':False}
    try:
        for record in records:
            if (out/'STOP_AFTER_CURRENT').exists():state['status']='stopped_by_request';break
            if args.max_recordings is not None and state['completed']>=args.max_recordings:state['status']='partial_requested_limit';break
            ensure_storage_headroom(out)
            # Refuse mixed-code batches if code changes during a long run.
            if evidence(files)!=code:raise RuntimeError('Converter/guard code changed during batch')
            state['active_recording']=record;save(out/'batch_status.json',state)
            manifest=run_record(root,record,out,code)
            state['completed']+=1;state['observations']+=manifest['checks']['observations']
            save(out/'batch_status.json',state)
            print(json.dumps({'completed':state['completed'],'total':len(records),'recording':record}),flush=True)
            time.sleep(2)
        else:state['status']='complete_unreviewed'
    except Exception as error:
        state['status']='stopped_incomplete';state['reason']=str(error);raise
    finally:save(out/'batch_status.json',state)


if __name__=='__main__':main()
