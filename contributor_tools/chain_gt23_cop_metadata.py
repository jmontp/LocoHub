"""Prepare and execute a receipt-bound COP overlay on completed force corrections.

Preparation reads hashes/JSON only. The run command is one externally guarded
worker; it never launches itself or edits the original correction tools.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FORCE_PATH=ROOT/'contributor_tools/correct_gt23_global_force_frame.py'
COP_PATH=ROOT/'contributor_tools/annotate_gt23_cop_frame.py'
PINNED={str(FORCE_PATH):'5070fbf5a7960a977834065c69d22d822c28cfe0788f78b772f48099db0315bc',
        str(COP_PATH):'c464769ffe4a88f8c35e6979ec3de02dd88382ce93b61b60d84e1c3ab0077e41'}


def digest(path):
    import hashlib
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def verify(bindings):
    for path,expected in bindings.items():
        if digest(path)!=expected:raise ValueError('Changed bound evidence: '+path)


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def completed_chain(report_path,native_lineage,force_module,required_bindings):
    """No scientific array reads; every supplied receipt must already exist."""
    report_path=Path(report_path).resolve();native_lineage=Path(native_lineage).resolve()
    report=json.loads(report_path.read_text())
    if report.get('status')!='global_force_labels_corrected_source_preserved_unreviewed' or report.get('scientific_approval') is not False:
        raise ValueError('Force correction is not completed and unreviewed')
    bindings=report['input_sha256']
    for path,h in required_bindings.items():
        if bindings.get(path)!=h:raise ValueError('Unreviewed producing force tool')
    if bindings.get(str(native_lineage))!=digest(native_lineage):raise ValueError('Native lineage not bound by force report')
    verify(bindings)
    lineage=json.loads(native_lineage.read_text())
    for path,h in lineage['evidence_sha256'].items():
        if bindings.get(path)!=h:raise ValueError('Native evidence absent from completed force report')
    for key in ['run_manifest','run_driver']:
        if lineage[key] not in lineage['evidence_sha256']:raise ValueError('Unbound native producer evidence')
    producer=force_module.validate_lineage(lineage,json.loads(Path(lineage['run_manifest']).read_text()),Path(lineage['run_driver']).read_text())
    if report.get('actual_producing_converter')!=producer:raise ValueError('Actual producer differs')
    if bindings.get(str(ROOT/producer['path']))!=producer['sha256']:raise ValueError('Producer code is not bound')
    originals=[p for p,h in bindings.items() if p.endswith('.parquet') and h==lineage['input_sha256']]
    if len(originals)!=1:raise ValueError('Original native Parquet is not uniquely bound')
    target=report_path.parent/'corrected.parquet'
    if digest(target)!=report['output_sha256']:raise ValueError('Completed force output changed')
    if report.get('aliases')!=force_module.ALIASES or report.get('frame')!=force_module.FRAME_INFO:
        raise ValueError('Unexpected completed force mapping')
    return {'input':str(target),'original_input':originals[0],'producer':producer,
            'bindings':{**bindings,str(report_path):digest(report_path),str(target):digest(target)},
            'force_report':str(report_path),'native_lineage':str(native_lineage)}


def validate_force_table(table,force_module):
    import pyarrow as pa
    if not set(force_module.ALIASES.values())<=set(table.column_names):raise ValueError('Force source aliases missing')
    for name,alias in force_module.ALIASES.items():
        if name not in table.column_names or table[name].null_count!=table.num_rows:
            raise ValueError('Unsupported anatomical horizontal force remains')
        f=table.schema.field(alias)
        if f.type!=table.schema.field(name).type or not pa.types.is_floating(f.type) or (f.metadata or {}).get(b'coordinate_frame')!=b'global':
            raise ValueError('Incorrect force alias schema')
    for raw in table['task_info'].to_pylist():
        if json.loads(raw).get('gt23_force_frame')!=force_module.FRAME_INFO:
            raise ValueError('Expected force provenance missing')


def prepare(report_path,lineage_path,plan_path,output):
    verify(PINNED);force=load('gt23_chain_force',FORCE_PATH)
    chain=completed_chain(report_path,lineage_path,force,{str(FORCE_PATH):PINNED[str(FORCE_PATH)]})
    output=Path(output).resolve();plan_path=Path(plan_path).resolve()
    local=ROOT/'converted_datasets/reconversion_v2'
    if not output.is_relative_to(local) or not plan_path.is_relative_to(local):raise ValueError('Plan/output outside local review root')
    if output.exists() or plan_path.exists():raise FileExistsError('Fresh plan and output required')
    bindings={**chain['bindings'],**PINNED,str(Path(__file__).resolve()):digest(__file__)}
    guard=ROOT/'contributor_tools/conversion_scripts/Fukuchi_2018_Walking/run_ensemble_pilot.py'
    bindings[str(guard)]=digest(guard)
    for relative in ['docs/quality/audits/gt23-cop-and-joint-coordinate-review.json',
                     'converted_datasets/reconversion_v2/swarm_backlog_20261021/gt23_ab01_model_coordinates.json']:
        path=ROOT/relative;bindings[str(path)]=digest(path)
    plan={**chain,'status':'prepared_not_run','scientific_approval':False,'output':str(output),'bindings':bindings,
          'guard':{'module':str(guard),'function':'guarded_stage','timeout_seconds':120,'worker_address_space_mib':768,'resource_poll_seconds':15},
          'execution':'Coordinator serial slot only; invoke the printed run command through the pinned guarded_stage. The worker never launches itself.',
          'acceptance':'Combined receipt status force_and_cop_metadata_corrections_source_preserved_unreviewed; all numerical bits/null masks, force aliases and force metadata unchanged.'}
    verify(bindings);plan_path.parent.mkdir(parents=True,exist_ok=True)
    with plan_path.open('x') as stream:json.dump(plan,stream,indent=2);stream.write('\n')
    command=['ionice','-c','3','python3',str(Path(__file__).resolve()),'run','--plan',str(plan_path),'--plan-sha256',digest(plan_path)]
    return {'plan':str(plan_path),'plan_sha256':digest(plan_path),'guarded_worker_command':command}


def run(plan_path,expected):
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[key]='1'
    import resource
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
    if digest(plan_path)!=expected:raise ValueError('Plan hash mismatch')
    plan=json.loads(Path(plan_path).read_text());verify(plan['bindings']);verify(PINNED)
    force=load('gt23_chain_force',FORCE_PATH);cop=load('gt23_chain_cop',COP_PATH)
    chain=completed_chain(plan['force_report'],plan['native_lineage'],force,{str(FORCE_PATH):PINNED[str(FORCE_PATH)]})
    if chain['input']!=plan['input'] or chain['producer']!=plan['producer']:raise ValueError('Chain differs from prepared plan')
    for path,h in chain['bindings'].items():
        if plan['bindings'].get(path)!=h:raise ValueError('Prepared chain binding differs')
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    for batch in pq.ParquetFile(plan['input']).iter_batches(batch_size=512,use_threads=False):
        if batch.nbytes>8*1024**2:raise MemoryError('Force batch exceeds admission')
        validate_force_table(pa.Table.from_batches([batch]),force)
    output=Path(plan['output']).resolve()
    if not output.is_relative_to(ROOT/'converted_datasets/reconversion_v2'):raise ValueError('Unauthorized output')
    output.mkdir(parents=True,exist_ok=False);target=output/'corrected.parquet'
    rows=cop.annotate_parquet(plan['input'],target)
    verify(plan['bindings'])
    if digest(plan_path)!=expected:raise ValueError('Plan changed during execution')
    report={'status':'force_and_cop_metadata_corrections_source_preserved_unreviewed','scientific_approval':False,
            'rows_checked':rows,'plan_sha256':expected,'verified_input_sha256':plan['bindings'],
            'force_report':plan['force_report'],'original_native_input':chain['original_input'],
            'intermediate_force_output':chain['input'],'actual_producing_converter':chain['producer'],
            'output_sha256':digest(target),'numerical_changes_in_this_stage':False,
            'scope':'Completed global-force correction retained; added only COP provenance. Anatomical joint signs, exact model/export correspondence and ankle-origin offsets remain unapproved.'}
    (output/'combined_correction_readback.json').write_text(json.dumps(report,indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='mode',required=True)
    prep=sub.add_parser('prepare')
    for name in ['force-report','native-lineage','plan','output']:prep.add_argument('--'+name,type=Path,required=True)
    execute=sub.add_parser('run');execute.add_argument('--plan',type=Path,required=True);execute.add_argument('--plan-sha256',required=True)
    args=parser.parse_args()
    if args.mode=='prepare':print(json.dumps(prepare(args.force_report,args.native_lineage,args.plan,args.output),indent=2))
    else:run(args.plan,args.plan_sha256)


if __name__=='__main__':main()
