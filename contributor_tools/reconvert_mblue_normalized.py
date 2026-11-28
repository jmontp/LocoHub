#!/usr/bin/env python3
"""Rebuild all inventoried MBLUE normalized blocks with bounded per-block writes.

This preserves corrected normalized-source coverage; external Vicon COP files and
scientific coordinate conventions still need separate reconciliation.
"""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse
import importlib.util
import json
from pathlib import Path
import resource
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest,ensure_storage_headroom
CODE=ROOT/'contributor_tools/conversion_scripts/MBLUEAnkle/convert_mblue_ankle_to_parquet.py'


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-root',type=Path,required=True)
    parser.add_argument('--inventory',type=Path,default=ROOT/'converted_datasets/reconversion_v2/mblue_source_inventory_20261021/source_inventory.json')
    args=parser.parse_args();resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
    import numpy as np
    import pyarrow as pa
    import pyarrow.parquet as pq
    from scipy.io import loadmat
    from contributor_tools.common.data_contract import inspect_contract
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    inventory=json.loads(args.inventory.read_text());ensure_storage_headroom(args.output_root);args.output_root.mkdir(parents=True,exist_ok=False)
    spec=importlib.util.spec_from_file_location('mblue_rebuild',CODE);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    files=[Path(__file__),CODE,ROOT/'contributor_tools/reconvert_recording.py',ROOT/'contributor_tools/common/data_contract.py',ROOT/'contributor_tools/common/task_registry.py']
    code={str(p):digest(p) for p in files}
    for p in files:
        dest=args.output_root/'code'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
    summary={'status':'running','pid':os.getpid(),'scientific_approval':False,'inventory_sha256':digest(args.inventory),'code_sha256':code,'planned_blocks':len(inventory['blocks']),'records':[],
        'limitations':['Reconstructs available normalized blocks; raw Vicon COP sources are not included',
            'Task segmentation, ankle/segment and force coordinate conventions remain unverified',
            'Available source fields not represented by the adapter require separate preservation']}
    def save():
        p=args.output_root/'conversion_summary.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(summary,indent=2)+'\n');tmp.replace(p)
    save()
    try:
        for source_info in inventory['sources']:
            source=Path(source_info['path']);subject=source.name.split('_')[0]
            if digest(source)!=source_info['sha256']:raise RuntimeError('Source changed since inventory')
            if source.stat().st_size>64*1024**2:raise MemoryError('Normalized source exceeds admission')
            data=loadmat(source,squeeze_me=False,struct_as_record=True)['dataOut'][0,0]
            info_path=source.with_name(subject+'_FileInfo.mat');info=loadmat(info_path,simplify_cells=True)['subject_info'];mass=float(info['mass'])
            if mass!=module.SUBJECT_INFO[subject]['mass']:raise ValueError('Subject mass mismatch')
            for record in [r for r in inventory['blocks'] if r['subject']==subject]:
                if (args.output_root/'STOP_AFTER_CURRENT').exists():summary['status']='stopped_by_request';save();return
                available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
                if available<2*1024**3:raise MemoryError('Less than 2 GiB Linux memory available')
                import shutil
                if shutil.disk_usage('/mnt/c').free<1024**3:raise OSError('Windows host drive below 1 GiB free')
                ensure_storage_headroom(args.output_root)
                if any(digest(Path(p))!=sha for p,sha in code.items()):raise RuntimeError('Code changed during reconstruction')
                parts=record['source_path'].split('/');condition=parts[0];path='/'.join(parts[1:]);block=data
                for part in parts:block=block[part][0,0]
                bilateral=parts[1] in ('STS','crouch')
                key=parts[2] if parts[1]=='stairs' else parts[-1]
                task,task_id,speed=module.TASK_MAPPING[key]
                if parts[1]=='stairs':task_id+='_'+parts[-1]
                common=dict(task_data=block,subject_id=subject,subject_mass=mass,task=task,task_id=task_id,condition=condition,task_key=parts[1],source_task_path=path)
                frames,_=module.process_bilateral_task(**common) if bilateral else module.process_gait_task(**common,speed_m_s=speed)
                expected=record['sides']['l']['cycles'] if bilateral else sum(v['cycles'] for v in record['sides'].values())
                if len(frames)!=expected:raise ValueError('Source/output cycle count mismatch: '+record['source_path'])
                folder=args.output_root/subject/record['source_path'];folder.mkdir(parents=True)
                writer=None;identities=set()
                try:
                    for frame in frames:
                        checked=inspect_contract(frame,mode='phase')
                        if not checked.schema_passed:raise ValueError(str(checked.issues[:3]))
                        identity=frame.observation_id.iloc[0]
                        if identity in identities:raise ValueError('Repeated source identity')
                        identities.add(identity);table=pa.Table.from_pandas(frame,preserve_index=False)
                        if writer is None:writer=pq.ParquetWriter(folder/'phase.parquet.partial',table.schema,compression='zstd')
                        writer.write_table(table)
                finally:
                    if writer is not None:writer.close()
                outputs={}
                if writer is not None:
                    target=folder/'phase.parquet';(folder/'phase.parquet.partial').replace(target);outputs[str(target.relative_to(args.output_root))]=digest(target)
                summary['records'].append({'subject':subject,'source_path':record['source_path'],'observations':len(frames),'rows':len(frames)*150,'source_sha256':source_info['sha256'],'subject_info_sha256':digest(info_path),'outputs':outputs,'status':'converted_unreviewed' if frames else 'empty_source_block'})
                del frames;save()
            del data
        summary['status']='all_normalized_blocks_reconstructed_unreviewed'
    except Exception as error:summary.update(status='failed',reason=str(error));raise
    finally:save()
    print(json.dumps({'status':summary['status'],'blocks':len(summary['records']),'observations':sum(r['observations'] for r in summary['records'])}))


if __name__=='__main__':main()
