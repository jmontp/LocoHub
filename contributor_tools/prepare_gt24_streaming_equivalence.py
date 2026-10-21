"""Prepare isolated two-phase streaming equivalence; --run is explicit serial work.

Uses existing complete pilot recordings, never reduced prefixes. Each numerical
stage is a separate768MiB guarded child. No full-data adoption is implied.
"""
import argparse
import itertools
import json
import os
from pathlib import Path
import resource
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.run_gt24_ankle_converter_pilot import digest,verify,guarded
from contributor_tools.preserve_um21_planar_estimates import exact_value


def build_plan(inventory_path,previous_plan):
    inventory=json.loads(inventory_path.read_text());previous=json.loads(previous_plan.read_text())
    summary_path=previous_plan.parent/'pilot_summary.json';summary=json.loads(summary_path.read_text())
    if summary['status']!='two_phase_continuous_streaming_pilot_checked_unreviewed' or summary['plan_sha256']!=digest(previous_plan):raise ValueError('Successful source-checked continuous pilot required')
    by_key={(phase['phase'],record['subject'],record['recording']):{**record,'phase':phase['phase']} for phase in inventory['phases'] for record in phase['parsed_recordings']}
    bindings=dict(previous['bindings']);records=[]
    for index,old in enumerate(previous['records']):
        record=by_key[(old['phase'],old['subject'],old['condition'])]
        if record['task']!='level_walking':raise ValueError('Pilot reference-rule evidence must be reviewed for non-gait task')
        reference=previous_plan.parent/f'record_{index}/corrected.parquet'
        bindings[str(reference)]=summary['records'][index]['corrected_sha256']
        record.update(reference_output=str(reference),phase_pilot_output=old['phase_pilot_output'],is_gait=True)
        records.append(record)
    bindings.update(inventory['code_sha256'])
    for path in [inventory_path,previous_plan,summary_path,Path(__file__),*[ROOT/'contributor_tools'/name for name in ('stream_gt24_continuous_record.py','audit_gt24_streamed_continuous.py','gt24_continuous_stream_windows.py','match_gt24_complete_intervals.py','prepare_gt24_complete_membership.py')]]:bindings[str(path.resolve())]=digest(path)
    verify(bindings)
    return {'status':'prepared_not_executed','scientific_approval':False,'bindings':bindings,'records':records,'corrected_adapter':previous['corrected_adapter'],'memory_limit_mib':768,'stage_order':['export','audit','equivalence'],'limitation':'Two complete previously checked recordings only; full Parsed scope and native Complete intervals remain separate'}


def worker(planpath,index,stage):
    for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[name]='1'
    os.environ['MPLBACKEND']='Agg';os.environ['LOCOHUB_HEADLESS']='1'
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    from contributor_tools.stream_gt24_continuous_record import convert_record
    from contributor_tools.audit_gt24_streamed_continuous import audit_record
    plan=json.loads(planpath.read_text());plan_sha=digest(planpath);verify(plan['bindings'])
    record=plan['records'][index];out=planpath.parent/f'record_{index}';out.mkdir(exist_ok=True);output=out/'continuous.parquet'
    # Outer guarded parent continuously enforces memory/disk/host reserves.
    guard=lambda:None
    if stage=='export':report=convert_record(record,plan['corrected_adapter'],output,guard)
    elif stage=='audit':
        phase=pq.ParquetFile(record['phase_pilot_output']);first=next(phase.iter_batches(batch_size=1,columns=['subject_metadata'],use_threads=False))
        metadata=json.loads(first.column(0).to_pylist()[0]);reference=pq.ParquetFile(record['reference_output'])
        report=audit_record(record,output,metadata,reference.schema_arrow,record['is_gait'],guard)
    else:
        old=pq.ParquetFile(record['reference_output']);new=pq.ParquetFile(output)
        if old.metadata.num_rows!=new.metadata.num_rows or not old.schema_arrow.equals(new.schema_arrow,check_metadata=True):raise ValueError('Streaming pilot changed reference schema/counts')
        rows=0
        for before,after in itertools.zip_longest(old.iter_batches(batch_size=512,use_threads=False),new.iter_batches(batch_size=512,use_threads=False)):
            if before is None or after is None or before.num_rows!=after.num_rows:raise ValueError('Unequal complete readback coverage')
            for name in old.schema_arrow.names:
                a=before.column(before.schema.get_field_index(name));b=after.column(after.schema.get_field_index(name))
                if not a.is_null().equals(b.is_null()) or not exact_value(a.to_pylist(),b.to_pylist()):raise ValueError('Streaming changed exact persisted field: '+name)
            rows+=before.num_rows
        report={'status':'complete_record_streaming_exact_equivalence_checked_unreviewed','rows':rows,'all_fields_metadata_masks_exact':True,'source_checked_reference_sha256':digest(record['reference_output']),'streamed_output_sha256':digest(output),'scientific_approval':False}
    verify(plan['bindings'])
    if digest(planpath)!=plan_sha:raise ValueError('Plan changed during worker')
    report['plan_sha256']=plan_sha
    with (out/(stage+'.json')).open('x') as f:json.dump(report,f,indent=2);f.write('\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__);base=ROOT/'converted_datasets/reconversion_v2'
    parser.add_argument('--output-root',type=Path,required=True);parser.add_argument('--run',action='store_true');parser.add_argument('--worker',choices=['export','audit','equivalence']);parser.add_argument('--record-index',type=int)
    args=parser.parse_args();out=args.output_root.resolve();planpath=out/'plan.json'
    if not out.is_relative_to(base):raise ValueError('Isolated scientific output required')
    if args.worker:worker(planpath,args.record_index,args.worker);return
    if not args.run:
        plan=build_plan(base/'gt24_full_continuous_scope_20261021/source_inventory.json',base/'gt24_continuous_pilot_v2_20261021/plan.json')
        out.mkdir(parents=True,exist_ok=False);planpath.write_text(json.dumps(plan,indent=2)+'\n')
        print(json.dumps({'status':plan['status'],'plan':str(planpath)}));return
    plan=json.loads(planpath.read_text());plan_sha=digest(planpath);verify(plan['bindings']);reports=[]
    for index in range(len(plan['records'])):
        for stage in plan['stage_order']:
            verify(plan['bindings'])
            with (out/f'{index}_{stage}.log').open('x') as log:guarded([sys.executable,str(Path(__file__).resolve()),'--output-root',str(out),'--worker',stage,'--record-index',str(index)],out,log)
        reports.append({stage:json.loads((out/f'record_{index}'/(stage+'.json')).read_text()) for stage in plan['stage_order']})
    verify(plan['bindings'])
    if digest(planpath)!=plan_sha:raise ValueError('Plan changed during serial run')
    result={'status':'two_phase_complete_record_streaming_equivalence_checked_unreviewed','scientific_approval':False,'plan_sha256':plan_sha,'records':reports}
    with (out/'pilot_summary.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'status':result['status']}))

if __name__=='__main__':main()
