"""Prepare a two-record participant-force correction; execution is explicit/serial.

Historical references prove preservation only, never mass correctness. Requires
fresh source README/Statics and Complete membership before any numerical child.
"""
import argparse
import json
import os
from pathlib import Path
import resource
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
BASE=ROOT/'converted_datasets/reconversion_v2'
from contributor_tools.run_gt24_ankle_converter_pilot import digest,verify,guarded
from contributor_tools.gt24_source_mass import collect_metadata,resolve_mass
from contributor_tools.gt24_mass_field_policy import participant_mass
from contributor_tools.prepare_gt24_complete_membership import checked_report_intervals


def prepare():
    previous_path=BASE/'gt24_streaming_equivalence_v2_20261021/plan.json'
    previous=json.loads(previous_path.read_text())
    matrix_path=BASE/'gt24_source_mass_coverage_v4_20261021/matrix.json'
    matrix=json.loads(matrix_path.read_text());metadata=matrix['source_metadata']
    bindings=dict(previous['bindings']);bindings.update(matrix['code_sha256'])
    records=[]
    for old,index in zip(previous['records'],[88,2105]):
        record=dict(old)
        if len(record['native_name_candidates_only'])!=1:raise ValueError('Pilot requires unique native candidate')
        record['participant_mass']=participant_mass(metadata,record['phase'],record['subject'])
        if record['participant_mass']['value_kg'] is None:raise ValueError('Pilot participant mass unresolved')
        record['model_mass']=resolve_mass(metadata,record['phase'],record['subject'],record['exo_state'],native_trial=record['native_name_candidates_only'][0])
        record.update(mass_evidence_sha256=digest(matrix_path),verified_source_denominator=None,membership_index=index)
        records.append(record)
    for path in [Path(__file__),matrix_path,previous_path,*[ROOT/'contributor_tools'/name for name in ('apply_gt24_participant_normalization.py','gt24_source_mass.py','gt24_mass_field_policy.py')]]:bindings[str(path.resolve())]=digest(path)
    membership=BASE/'gt24_complete_membership_v2_20261021/plan.json'
    bindings[str(membership)]=digest(membership)
    return {'status':'prepared_pending_source_membership_not_executed','scientific_approval':False,'bindings':bindings,'records':records,'mass_matrix':str(matrix_path),'membership_plan':str(membership),'inventory':str(BASE/'gt24_full_continuous_scope_20261021/source_inventory.json'),'memory_limit_mib':768,'scope':'Two full previously exported recordings only; 2421 Parsed and 1358 native records remain in the full coverage ledger','policy':'Participant BW from documented N; source moment denominator and interaction units unknown, canonical moments/assistance withheld; all unrelated fields exact','stage_order':['export','audit']}


def admission(plan):
    verify(plan['bindings'])
    matrix=json.loads(Path(plan['mass_matrix']).read_text())
    fresh=collect_metadata(json.loads(Path(plan['inventory']).read_text()),Path(matrix['source_metadata']['readme']['path']))
    if fresh!=matrix['source_metadata']:raise ValueError('Source mass metadata changed')
    membership_path=Path(plan['membership_plan']);membership=json.loads(membership_path.read_text());verify(membership['bindings'])
    receipts={}
    for record in plan['records']:
        index=record['membership_index'];path=membership_path.parent/'records'/f'{index:06d}.json';report=json.loads(path.read_text());job=membership['jobs'][index]
        if report['status']!='native_parsed_candidate_checked_unreviewed' or report['membership_verified'] is not True or report['plan_sha256']!=digest(membership_path) or report['job_index']!=index:raise ValueError('Successful bound Complete membership required')
        for key,expected in [('phase',record['phase']),('subject',record['subject']),('parsed_recording',record['recording']),('native_recording',record['native_name_candidates_only'][0])]:
            if report[key]!=expected or job[key]!=expected:raise ValueError('Membership source identity mismatch')
        expected_tables={table['kind']:table for table in job['tables']}
        if not expected_tables or set(report['tables'])!=set(expected_tables):raise ValueError('Incomplete source membership tables')
        for kind,table in expected_tables.items():
            if report['tables'][kind]['parsed']['full_csv_sha256']!=digest(table['parsed']['path']):raise ValueError('Membership Parsed source changed')
        if not checked_report_intervals(report):raise ValueError('Empty source membership')
        participant=participant_mass(fresh,record['phase'],record['subject'])
        model=resolve_mass(fresh,record['phase'],record['subject'],record['exo_state'],native_trial=record['native_name_candidates_only'][0])
        if participant!=record['participant_mass'] or model!=record['model_mass'] or record['verified_source_denominator'] is not None:raise ValueError('Unbound or unsupported normalization policy')
        receipts[str(path)]=digest(path)
    return receipts


def worker(planpath,index,stage):
    for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[name]='1'
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
    import pyarrow as pa
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    from contributor_tools.apply_gt24_participant_normalization import apply_record,audit_record
    plan=json.loads(planpath.read_text());plan_sha=digest(planpath);receipt=json.loads((planpath.parent/'admission.json').read_text())
    verify(plan['bindings']);verify(receipt['membership_hashes'])
    if receipt['plan_sha256']!=plan_sha:raise ValueError('Admission plan mismatch')
    record=plan['records'][index];folder=planpath.parent/f'record_{index}';folder.mkdir(exist_ok=True);output=folder/'continuous.parquet'
    report=(apply_record if stage=='export' else audit_record)(record,Path(record['reference_output']),output)
    verify(plan['bindings']);verify(receipt['membership_hashes'])
    if digest(planpath)!=plan_sha:raise ValueError('Plan changed')
    report['plan_sha256']=plan_sha
    with (folder/(stage+'.json')).open('x') as handle:json.dump(report,handle,indent=2)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-root',type=Path,required=True);parser.add_argument('--run',action='store_true');parser.add_argument('--worker',choices=['export','audit']);parser.add_argument('--record-index',type=int);args=parser.parse_args()
    folder=args.output_root.resolve();planpath=folder/'plan.json'
    if not folder.is_relative_to(BASE):raise ValueError('Isolated output root required')
    if args.worker:worker(planpath,args.record_index,args.worker);return
    if not args.run:
        plan=prepare();folder.mkdir(parents=True,exist_ok=False);planpath.write_text(json.dumps(plan,indent=2)+'\n');print(plan['status']);return
    plan=json.loads(planpath.read_text());plan_sha=digest(planpath);receipts=admission(plan)
    with (folder/'admission.json').open('x') as handle:json.dump({'plan_sha256':plan_sha,'membership_hashes':receipts,'source_mass_metadata_revalidated':True},handle,indent=2)
    reports=[]
    for index in range(len(plan['records'])):
        for stage in plan['stage_order']:
            verify(plan['bindings']);verify(receipts)
            with (folder/f'{index}_{stage}.log').open('x') as log:guarded([sys.executable,str(Path(__file__).resolve()),'--output-root',str(folder),'--worker',stage,'--record-index',str(index)],folder,log)
        result=json.loads((folder/f'record_{index}/audit.json').read_text())
        if result['status']!='participant_normalization_independent_readback_checked_unreviewed' or result['plan_sha256']!=plan_sha:raise ValueError('Independent readback incomplete')
        if result['output_sha256']!=digest(folder/f'record_{index}/continuous.parquet'):raise ValueError('Audited output changed')
        reports.append(result)
    verify(plan['bindings']);verify(receipts)
    if digest(planpath)!=plan_sha:raise ValueError('Plan changed')
    with (folder/'pilot_summary.json').open('x') as handle:json.dump({'status':'two_phase_participant_force_pilot_checked_unreviewed','scientific_approval':False,'plan_sha256':plan_sha,'membership_hashes':receipts,'records':reports,'canonical_moments_and_assistance_withheld':True},handle,indent=2)

if __name__=='__main__':main()
