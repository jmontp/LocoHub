#!/usr/bin/env python3
"""Inventory and serially reconstruct GT25 with isolated, guarded recording workers."""
import argparse
import ast
from collections import Counter
import json
import os
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest,ensure_storage_headroom
from contributor_tools.run_reconversion_batch import run_guarded_worker,available_memory_bytes
CODE=ROOT/'contributor_tools/conversion_scripts/GaTech_2025_DomainAdaptation'


def save(path,value):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)


def inventory(source):
    tree=ast.parse((CODE/'convert_gtech_2025_da_to_parquet.py').read_text())
    mapping=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='TASK_MAPPING' for t in n.targets))
    records=[]
    for subject in sorted(source.glob('BT*')):
        if not subject.is_dir():continue
        for folder in sorted(subject.iterdir()):
            if not folder.is_dir():continue
            match=next((v for pattern,v in mapping.items() if re.search(pattern,folder.name)),None)
            status='unmapped_task' if match is None else 'explicit_task_exclusion' if match[0] is None else 'mapped_task'
            records.append({'subject':subject.name,'recording':folder.name,'mapping_status':status,
                'canonical_task':match[0] if match else None,
                'source_csv_bytes':sum(p.stat().st_size for p in folder.glob('*.csv'))})
    if not records:raise ValueError('No source recordings')
    return records


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,default=Path('/mnt/s/locomotion_data/GaTech_2025_DomainAdaptation/Parsed'))
    parser.add_argument('--output-root',type=Path,required=True);parser.add_argument('--run',action='store_true')
    parser.add_argument('--max-recordings',type=int)
    args=parser.parse_args()
    if args.max_recordings is not None and args.max_recordings<1:parser.error('max-recordings must be positive')
    os.nice(max(0,19-os.nice(0)))
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
    source=args.source_root.resolve();out=args.output_root.resolve();ensure_storage_headroom(out);out.mkdir(parents=True,exist_ok=True)
    plan=inventory(source)
    inventory_path=out/'inventory.json'
    if inventory_path.exists() and json.loads(inventory_path.read_text())!=plan:raise ValueError('Source inventory changed; use a new root')
    save(inventory_path,plan)
    if not args.run:
        print(json.dumps({'recordings':len(plan),'subjects':len({r['subject'] for r in plan}),'mapping_counts':dict(Counter(r['mapping_status'] for r in plan)),'over_64_mib':sum(r['source_csv_bytes']>64*1024**2 for r in plan)}));return
    files=[Path(__file__),ROOT/'contributor_tools/reconvert_recording.py',ROOT/'contributor_tools/run_reconversion_batch.py',*sorted(CODE.glob('*.py')),*sorted((ROOT/'contributor_tools/common').rglob('*.py'))]
    code={str(p):digest(p) for p in files};code_path=out/'batch_code.json'
    if code_path.exists() and json.loads(code_path.read_text())!=code:raise ValueError('Code changed; use a new root')
    save(code_path,code)
    for p in files:
        target=out/'code_snapshot'/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():target.write_bytes(p.read_bytes())
    state={'status':'running','pid':os.getpid(),'total':len(plan),'completed':0,'converted':0,'rows':0,'unresolved':0,'records':[],'scientific_approval':False}
    try:
        for record in plan:
            if (out/'STOP_AFTER_CURRENT').exists():state['status']='stopped_by_request';break
            if args.max_recordings is not None and state['completed']>=args.max_recordings:state['status']='partial_requested_limit';break
            if any(digest(Path(p))!=sha for p,sha in code.items()):raise RuntimeError('Code changed during batch')
            ensure_storage_headroom(out)
            result=dict(record)
            if record['mapping_status']!='mapped_task':
                result['status']='unresolved_task_coverage';state['unresolved']+=1
            elif record['source_csv_bytes']+(source.parent/'readme.txt').stat().st_size>64*1024**2:
                result['status']='deferred_input_admission';state['unresolved']+=1
            else:
                if available_memory_bytes()<int(3.5*1024**3):raise MemoryError('Worker cap plus 2 GiB reserve unavailable')
                log=out/'logs'/record['subject']/(record['recording']+'.log');log.parent.mkdir(parents=True,exist_ok=True)
                command=[sys.executable,str(CODE/'reconvert_recording.py'),'--source-root',str(source),'--subject',record['subject'],'--recording',record['recording'],'--output-root',str(out),'--memory-mib','1536','--max-source-mib','64','--resume']
                state['active_recording']=record;save(out/'batch_status.json',state)
                with log.open('a') as stream:done=run_guarded_worker(command,stdout=stream,timeout=180,output_root=out)
                if done.returncode:raise RuntimeError('Worker failed; see '+str(log))
                manifest_path=out/'gt25/Parsed'/record['subject']/record['recording']/'conversion_manifest.json'
                manifest=json.loads(manifest_path.read_text());result.update(status=manifest['status'],manifest_sha256=digest(manifest_path),rows=manifest.get('rows',0))
                if manifest['status']=='quarantined_schema_failure':raise RuntimeError('Schema failure; see '+str(manifest_path))
                if manifest['status']=='converted_unreviewed':state['converted']+=1;state['rows']+=manifest['rows']
                else:state['unresolved']+=1
            state['records'].append(result);state['completed']+=1;save(out/'batch_status.json',state)
        else:state['status']='complete_with_unresolved_coverage' if state['unresolved'] else 'complete_unreviewed'
    except Exception as error:state.update(status='stopped_incomplete',reason=str(error));raise
    finally:save(out/'batch_status.json',state)
    print(json.dumps({k:v for k,v in state.items() if k not in ('records','active_recording')}))


if __name__=='__main__':main()
