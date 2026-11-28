"""Prepare two real unknown-mass records; actual execution requires Complete membership.

No bulk extraction. The fresh streaming baseline is explicitly unreviewed;
normalization readback does not approve its unrelated anatomical signals.
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
SELECTED=(('Phase3','BT24','normal_walk_1_1_1-2_on',2408),('Phase3','BT13','normal_walk_1_1_0-6_on',1883))


def mass_policy(metadata,record):
    participant=participant_mass(metadata,record['phase'],record['subject'])
    try:
        model=resolve_mass(metadata,record['phase'],record['subject'],record['exo_state'],native_trial=record['native_name_candidates_only'][0])
    except ValueError as exc:
        model={'source_model_mass_kg':None,'mass_basis':'unresolved_source_metadata','model_id':None,'unresolved_reason':str(exc)}
    return participant,model


def prepare(output):
    output=Path(output).resolve()
    if not output.is_relative_to(BASE) or output.exists():raise ValueError('Fresh isolated output required')
    inventory_path=BASE/'gt24_full_continuous_scope_20261021/source_inventory.json';matrix_path=BASE/'gt24_source_mass_coverage_v4_20261021/matrix.json'
    membership_path=BASE/'gt24_complete_membership_v2_20261021/plan.json';previous_path=BASE/'gt24_streaming_equivalence_v2_20261021/plan.json'
    inventory=json.loads(inventory_path.read_text());matrix=json.loads(matrix_path.read_text());membership=json.loads(membership_path.read_text());previous=json.loads(previous_path.read_text())
    lookup={(p['phase'],r['subject'],r['recording']):{**r,'phase':p['phase']} for p in inventory['phases'] for r in p['parsed_recordings']}
    # Existing binding closure pins reviewed adapter imports/common dependencies.
    bindings={p:h for p,h in previous['bindings'].items() if not p.endswith('.parquet')}
    bindings.update(membership['bindings']);bindings.update(matrix['code_sha256'])
    records=[]
    for index,(phase,subject,name,membership_index) in enumerate(SELECTED):
        record=dict(lookup[(phase,subject,name)]);job=membership['jobs'][membership_index]
        if record['task']!='level_walking' or len(record['native_name_candidates_only'])!=1:raise ValueError('Mapped unique candidate required')
        if (job['phase'],job['subject'],job['parsed_recording'],job['native_recording'])!=(phase,subject,name,record['native_name_candidates_only'][0]):raise ValueError('Membership index identity differs')
        participant,model=mass_policy(matrix['source_metadata'],record)
        if participant['value_kg'] is not None:raise ValueError('Representative participant mass is not unresolved')
        if (model['source_model_mass_kg'] is None)!=(index==0):raise ValueError('Representative model availability changed')
        record.update(participant_mass=participant,model_mass=model,mass_evidence_sha256=digest(matrix_path),verified_source_denominator=None,membership_index=membership_index,is_gait=True,reference_output=str(output/f'record_{index}/baseline_unreviewed.parquet'))
        record['model_candidate_not_admitted']=True;records.append(record)
    for p in [Path(__file__),inventory_path,matrix_path,membership_path,previous_path,*[ROOT/'contributor_tools'/n for n in ('apply_gt24_participant_normalization_v2.py','gt24_mass_field_policy.py','gt24_source_mass.py','stream_gt24_continuous_record.py','prepare_gt24_complete_membership.py')]]:bindings[str(p.resolve())]=digest(p)
    verify(bindings)
    plan={'status':'prepared_pending_complete_membership','scientific_approval':False,'records':records,'bindings':bindings,'inventory':str(inventory_path),'mass_matrix':str(matrix_path),'membership_plan':str(membership_path),'corrected_adapter':previous['corrected_adapter'],'output_root':str(output),'stage_order':['baseline','export','audit'],'memory_limit_mib':768,'full_scope':matrix['counts'],'scope':'Two complete representative Parsed records, not full adoption. All2421 Parsed records remain in the bound inventory, including869 source-only tasks.','unresolved':'Baseline unrelated anatomical signals are unreviewed. Model candidate is usable only after exact Complete membership and refreshed source metadata; missing model remains missing. Canonical moments and interaction assistance stay withheld.'}
    output.mkdir(parents=True,exist_ok=False);(output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');return plan


def membership_admission(plan):
    verify(plan['bindings']);matrix=json.loads(Path(plan['mass_matrix']).read_text())
    fresh=collect_metadata(json.loads(Path(plan['inventory']).read_text()),Path(matrix['source_metadata']['readme']['path']))
    if fresh!=matrix['source_metadata']:raise ValueError('Source mass metadata changed')
    mp=Path(plan['membership_plan']);membership=json.loads(mp.read_text());verify(membership['bindings']);receipts={}
    for record in plan['records']:
        index=record['membership_index'];rp=mp.parent/'records'/f'{index:06d}.json'
        if not rp.exists():raise ValueError('Complete membership prerequisite missing: '+str(rp))
        report=json.loads(rp.read_text());job=membership['jobs'][index]
        if report.get('status')!='native_parsed_candidate_checked_unreviewed' or report.get('membership_verified') is not True or report.get('plan_sha256')!=digest(mp) or report.get('job_index')!=index:raise ValueError('Successful exact Complete membership required')
        for key,value in [('phase',record['phase']),('subject',record['subject']),('parsed_recording',record['recording']),('native_recording',record['native_name_candidates_only'][0])]:
            if report.get(key)!=value or job[key]!=value:raise ValueError('Membership identity mismatch')
        tables={t['kind']:t for t in job['tables']}
        if not tables or set(report['tables'])!=set(tables) or not checked_report_intervals(report):raise ValueError('Incomplete membership evidence')
        for kind,table in tables.items():
            path=table['parsed']['path'];h=digest(path)
            if report['tables'][kind]['parsed']['full_csv_sha256']!=h:raise ValueError('Parsed member changed')
            receipts[path]=h
        participant,model=mass_policy(fresh,record)
        if participant!=record['participant_mass'] or model!=record['model_mass'] or record['verified_source_denominator'] is not None:raise ValueError('Normalization evidence differs')
        receipts[str(rp)]=digest(rp)
    return receipts


def worker(planpath,index,stage):
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[key]='1'
    os.environ['MPLBACKEND']='Agg';os.environ['LOCOHUB_HEADLESS']='1'
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
    import pyarrow as pa
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    from contributor_tools.stream_gt24_continuous_record import convert_record
    from contributor_tools.apply_gt24_participant_normalization_v2 import apply_record,audit_record
    plan=json.loads(planpath.read_text());sha=digest(planpath);admission=json.loads((planpath.parent/'admission.json').read_text())
    verify(plan['bindings']);verify(admission['membership_hashes'])
    if admission['plan_sha256']!=sha:raise ValueError('Admission plan mismatch')
    record=plan['records'][index];folder=planpath.parent/f'record_{index}';folder.mkdir(exist_ok=True);reference=Path(record['reference_output']);output=folder/'continuous.parquet'
    if stage=='baseline':
        report=convert_record(record,plan['corrected_adapter'],reference,lambda:None);report['output_sha256']=digest(reference)
    else:
        prior=json.loads((folder/'baseline.json').read_text())
        if prior.get('status')!='bounded_parsed_continuous_export_unverified' or prior['plan_sha256']!=sha or prior['output_sha256']!=digest(reference):raise ValueError('Fresh baseline provenance changed')
        if stage=='export':report=apply_record(record,reference,output)
        else:report=audit_record(record,reference,output)
    verify(plan['bindings']);verify(admission['membership_hashes'])
    if digest(planpath)!=sha:raise ValueError('Plan changed')
    report.update(plan_sha256=sha,scientific_approval=False,unrelated_baseline_signals='preserved but not independently approved by this normalization pilot')
    with (folder/(stage+'.json')).open('x') as f:json.dump(report,f,indent=2)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-root',type=Path,required=True);p.add_argument('--run',action='store_true');p.add_argument('--worker',choices=['baseline','export','audit']);p.add_argument('--record-index',type=int);args=p.parse_args()
    folder=args.output_root.resolve();planpath=folder/'plan.json'
    if not folder.is_relative_to(BASE):raise ValueError('Isolated root required')
    if args.worker:worker(planpath,args.record_index,args.worker);return
    if not args.run:print(json.dumps({'status':prepare(folder)['status'],'plan':str(planpath),'sha256':digest(planpath)}));return
    plan=json.loads(planpath.read_text());sha=digest(planpath)
    if plan['output_root']!=str(folder):raise ValueError('Output root differs')
    receipts=membership_admission(plan)
    with (folder/'admission.json').open('x') as f:json.dump({'plan_sha256':sha,'membership_hashes':receipts,'model_candidates_admitted_only_by_verified_membership':True},f,indent=2)
    reports=[]
    for index in range(len(plan['records'])):
        for stage in plan['stage_order']:
            verify(plan['bindings']);verify(receipts)
            with (folder/f'{index}_{stage}.log').open('x') as log:guarded([sys.executable,str(Path(__file__).resolve()),'--output-root',str(folder),'--worker',stage,'--record-index',str(index)],folder,log)
        report=json.loads((folder/f'record_{index}/audit.json').read_text())
        if report['status']!='participant_normalization_independent_readback_checked_unreviewed' or report['plan_sha256']!=sha or report['output_sha256']!=digest(folder/f'record_{index}/continuous.parquet'):raise ValueError('Incomplete independent normalization readback')
        reports.append(report)
    verify(plan['bindings']);verify(receipts)
    if digest(planpath)!=sha:raise ValueError('Plan changed')
    with (folder/'pilot_summary.json').open('x') as f:json.dump({'status':'unknown_mass_representatives_normalization_checked_unreviewed','scientific_approval':False,'plan_sha256':sha,'membership_hashes':receipts,'records':reports,'full_scope':plan['full_scope'],'unresolved':plan['unresolved']},f,indent=2)

if __name__=='__main__':main()
