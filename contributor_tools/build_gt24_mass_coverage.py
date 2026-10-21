"""Full metadata-only GT24 admission matrix and independent source mass evidence."""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import types
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.gt24_source_mass import collect_metadata,resolve_mass
from contributor_tools.gt24_mass_field_policy import participant_mass


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def existing_policy(path):
    tree=ast.parse(path.read_text());names={'SUBJECT_MASS_PHASE12','SUBJECT_MASS_PHASE3','PHASE1_SUBJECTS','PHASE2_SUBJECTS','PHASE3_SUBJECTS'};functions={'get_collection_phase','get_exo_state','is_day2_trial','get_subject_mass'}
    selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in n.targets)]
    namespace={'np':types.SimpleNamespace(nan=float('nan'))}
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(path)+' [metadata only]','exec'),namespace)
    return namespace


def explicit_state(name):
    states=[state for state,tokens in [('no_exo',('_noexo','_bare')),('powered',('_on','_hilo')),('worn_unpowered',('_off',))] if any(token in name for token in tokens)]
    if len(states)!=1:raise ValueError('Explicit state ambiguous or absent')
    return states[0]


def build(inventory_path,adapter,readme_path):
    inventory=json.loads(inventory_path.read_text());metadata=collect_metadata(inventory,readme_path);policy=existing_policy(adapter);rows=[];native=[]
    for phase in inventory['phases']:
        for source in phase['dynamic_complete_recordings']:
            item={'phase':phase['phase'],'subject':source['subject'],'native_trial':source['recording'],'mass_binding_status':'requires_parsed_state_and_membership' if phase['phase']=='Phase1And2' else 'native_static_model_listed_requires_cross_document_check'}
            if phase['phase']=='Phase3':
                table=metadata['phase3_static_models'].get(source['subject'],{}).get('records',{})
                if source['recording'] not in table:raise ValueError('Native Phase3 trial lacks model mapping')
                item['model']=table[source['recording']]
                try:resolve_mass(metadata,phase['phase'],source['subject'],'powered',native_trial=source['recording'])
                except ValueError as exc:item.update(mass_binding_status='source_metadata_conflict',blocker=str(exc))
            native.append(item)
        for record in phase['parsed_recordings']:
            state=explicit_state(record['recording']);collection=policy['get_collection_phase'](record['subject'],phase['phase']);day2=policy['is_day2_trial'](record['recording']);old=policy['get_subject_mass'](record['subject'],phase['phase'],state,day2)
            item={'phase':phase['phase'],'subject':record['subject'],'recording':record['recording'],'folder':record['folder'],'task_disposition':record['disposition'],'canonical_task':record.get('task'),'exo_state':state,'existing_mass_kg':old,'existing_assumed_day':2 if day2 else 1,'source_membership_verified':False,'source_file_kinds':sorted(record['files']),'source_file_bytes':sum(f['bytes'] for f in record['files'].values()),'clock_continuity':'unassessed_no_signal_reads','mass_candidates':[],'blockers':[]}
            candidates=record['native_name_candidates_only'] if phase['phase']=='Phase3' else [None]
            for trial in candidates:
                try:resolved=resolve_mass(metadata,phase['phase'],record['subject'],state,native_trial=trial)
                except ValueError as exc:item['blockers'].append(str(exc));continue
                item['mass_candidates'].append({'native_trial':trial,**resolved})
            item['participant_mass']=participant_mass(metadata,phase['phase'],record['subject'])
            item['source_joint_moment_denominator']='unverified; source Nm/kg values retained, canonical participant-normalized moments withheld'
            masses={x['source_model_mass_kg_decimal'] for x in item['mass_candidates']}
            item['mass_status']='source_candidate_mass_requires_membership' if len(masses)==1 and not item['blockers'] else 'source_mass_unresolved'
            item['existing_mass_differs_from_all_candidates']=bool(masses) and all(old!=float(value) for value in masses)
            if len(masses)>1:item['blockers'].append('Native candidates have different exact model masses')
            if record['disposition']!='canonical_parsed_candidate_requires_source_audit':item['blockers'].append('Source-only task requires explicit task policy; must remain in coverage')
            item['blockers']+=['Full-record source membership pending','Clock continuity and supplied channel values unassessed','Source model mass correction and independent readback required']
            rows.append(item)
    grouped=[]
    for phase,subject in sorted({(r['phase'],r['subject']) for r in rows}):
        records=[r for r in rows if (r['phase'],r['subject'])==(phase,subject)]
        grouped.append({'phase':phase,'subject':subject,'records':len(records),'task_dispositions':dict(Counter(r['task_disposition'] for r in records)),'mass_statuses':dict(Counter(r['mass_status'] for r in records)),'existing_mass_differs':sum(r['existing_mass_differs_from_all_candidates'] for r in records),'states':dict(Counter(r['exo_state'] for r in records)),'channel_availability':dict(Counter(kind for r in records for kind in r['source_file_kinds']))})
    return {'status':'complete_gt24_mass_admission_matrix_unreviewed','scientific_approval':False,'admitted_records':0,'inventory_sha256':digest(inventory_path),'adapter_sha256':digest(adapter),'code_sha256':{str(Path(__file__).resolve()):digest(__file__),str(ROOT/'contributor_tools/gt24_source_mass.py'):digest(ROOT/'contributor_tools/gt24_source_mass.py'),str(ROOT/'contributor_tools/gt24_mass_field_policy.py'):digest(ROOT/'contributor_tools/gt24_mass_field_policy.py')},'source_metadata':metadata,'parsed_recordings':rows,'native_recordings':native,'by_phase_subject':grouped,'counts':{'parsed_records':len(rows),'native_dynamic_records':len(native),'existing_mass_differs':sum(r['existing_mass_differs_from_all_candidates'] for r in rows),'mass_unresolved':sum(r['mass_status']=='source_mass_unresolved' for r in rows),'task_dispositions':dict(Counter(r['task_disposition'] for r in rows)),'participant_mass_bound':sum(r['participant_mass']['value_kg'] is not None for r in rows),'participant_mass_unresolved':sum(r['participant_mass']['value_kg'] is None for r in rows)},'channel_policy':{'grf_vertical_ipsi_BW_and_contra':'Canonical body weights require documented participant-without-exoskeleton mass: raw force/(participant mass*9.81). Preserve model-normalized force only in separate explicit derived source-model-weight aliases','hip_and_knee_assistance_moment_Nm_kg':'Canonical assistance withheld: actual torque_interaction column units absent from README. Preserve raw values in units_unknown aliases; do not borrow estimated/measured/desired torque units','joint_moment_and_biological_moment_Nm_kg':'Preserve raw source-normalized values in source aliases. Canonical participant-normalized values require independently verified source denominator chain: sign*source_value*source_denominator/participant_mass; otherwise withheld. Never divide already normalized values again','raw_source_grf_N_and_angles_velocities':'Mass-independent; preserve exactly','ankle_assistance':'Known absent only no-exo; otherwise missing','calendar_day':'Unknown unless separately sourced; static model ID is not day number','source_model_mass_vs_participant_mass':'Keep separate; worn-system mass includes exoskeleton. No implicit conversion to participant-only normalization'},'source_read_scope':'README text and10 tiny Statics metadata CSVs only; no time-series CSVs or Parquet loaded'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);base=ROOT/'converted_datasets/reconversion_v2'
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    inventory=base/'gt24_full_continuous_scope_20261021/source_inventory.json'
    adapter=base/'gt24_continuous_correction_proposal_20261021/isolated_repo/contributor_tools/conversion_scripts/GaTech_2024_TaskAgnostic/convert_gtech_2024_phase_to_parquet.py'
    result=build(inventory,adapter,Path('/mnt/s/locomotion_data/GaTech_2024_TaskAgnostic/readme.txt'))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result['counts']))

if __name__=='__main__':main()
