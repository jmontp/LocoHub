"""Metadata-only exact GT24 scope and serial reconstruction prerequisites.

This planner reads existing JSON/source text only. It never launches a worker or
labels source availability as scientific validation.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'converted_datasets/reconversion_v2'


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def unique(rows,keys):
    result={}
    for row in rows:
        key=tuple(row[k] for k in keys)
        if key in result:raise ValueError('Duplicate source identity: '+str(key))
        result[key]=row
    return result


def classify(inventory,matrix,membership):
    parsed=unique([{**r,'phase':phase['phase']} for phase in inventory['phases'] for r in phase['parsed_recordings']],('phase','subject','recording'))
    native=unique([{**r,'phase':phase['phase']} for phase in inventory['phases'] for r in phase['dynamic_complete_recordings']],('phase','subject','recording'))
    masses=unique(matrix['parsed_recordings'],('phase','subject','recording'))
    if set(parsed)!=set(masses):raise ValueError('Mass matrix does not exactly cover Parsed identities')
    jobs=defaultdict(list);seen=set()
    for index,job in enumerate(membership['jobs']):
        key=(job['phase'],job['subject'],job['parsed_recording']);nkey=(job['phase'],job['subject'],job['native_recording'])
        if key not in parsed or nkey not in native:raise ValueError('Membership job references unknown source')
        if (key,nkey) in seen:raise ValueError('Duplicate candidate membership job')
        seen.add((key,nkey));jobs[key].append(index)
    rows=[]
    required={'angle_filt','moment_filt','grf','velocity','insole_sim'}
    for key,record in parsed.items():
        mass=masses[key];available=set(record['files']);mapped=record['disposition']=='canonical_parsed_candidate_requires_source_audit'
        if record['disposition'] not in ('canonical_parsed_candidate_requires_source_audit','source_only_unmapped_task'):raise ValueError('Unknown task disposition')
        if mass['task_disposition']!=record['disposition']:raise ValueError('Mass task scope differs')
        rows.append({'phase':key[0],'subject':key[1],'recording':key[2],'disposition':record['disposition'],'source_files':{kind:value['path'] for kind,value in record['files'].items()},'source_bytes':sum(value['bytes'] for value in record['files'].values()),'missing_required_streams':sorted(required-available),'participant_mass':mass['participant_mass'],'source_model_mass_status':mass['mass_status'],'candidate_membership_jobs':jobs[key],'membership_status':'pending_actual_all_candidate_results' if jobs[key] else 'no_candidate_requires_source_lineage_resolution','clock_status':'unassessed_requires_actual_source_scan','next_action':'bounded_corrected_continuous_then_independent_corrected_source_readback' if mapped else 'lossless_source_companion_all_streams_without_canonical_task','canonical_moments':'withheld_unverified_source_denominator','canonical_assistance':'withheld_unverified_interaction_units','ready_for_scientific_adoption':False})
    return {'parsed':rows,'native':[{'phase':k[0],'subject':k[1],'recording':k[2],'disposition':'complete_source_only_until_exact_parsed_interval_union_and_residual_clock_accounting'} for k in native],'counts':{'parsed':len(parsed),'native':len(native),'task_dispositions':dict(Counter(r['disposition'] for r in rows)),'missing_required_streams':sum(bool(r['missing_required_streams']) for r in rows),'without_candidate_membership':sum(not r['candidate_membership_jobs'] for r in rows),'participant_mass_unresolved':sum(r['participant_mass']['value_kg'] is None for r in rows)}}


def prepare(output):
    paths={'inventory':BASE/'gt24_full_continuous_scope_20261021/source_inventory.json','matrix':BASE/'gt24_source_mass_coverage_v4_20261021/matrix.json','membership':BASE/'gt24_complete_membership_v2_20261021/plan.json'}
    data={key:json.loads(path.read_text()) for key,path in paths.items()};result=classify(data['inventory'],data['matrix'],data['membership'])
    if result['counts']['parsed']!=2421 or result['counts']['native']!=1358 or result['counts']['task_dispositions']!={'source_only_unmapped_task':869,'canonical_parsed_candidate_requires_source_audit':1552}:raise ValueError('Reviewed full scope changed')
    checks=[]
    for name,bindings in [('membership',data['membership']['bindings']),('mass_matrix',data['matrix']['code_sha256'])]:
        for path,expected in bindings.items():
            actual=digest(path) if Path(path).is_file() else None
            checks.append({'plan':name,'path':path,'expected_sha256':expected,'actual_sha256':actual,'matches':actual==expected})
    result.update(status='full_scope_accounted_not_execution_ready',scientific_approval=False,bindings={str(p):digest(p) for p in [*paths.values(),Path(__file__).resolve()]},original_binding_checks=checks,serial_dependencies=[{'stage':'pilot_gate','required':'Actual known-mass two-phase AND unknown-participant/model-mass pilot readbacks, exact bound outputs; fixture success is insufficient'},{'stage':'membership_all_candidates','required':'All2447 candidate jobs with immutable receipts; reject ambiguous membership; account every no-candidate Parsed identity'},{'stage':'corrected_raw_auditor','required':'NEW independent source audit of corrected participant/missing-mass fields. Existing audit_gt24_streamed_continuous expects superseded model BW and canonical moments/assistance; cannot accept corrected output.'},{'stage':'per_record','required':'Source scan/clock continuity; bounded baseline; v2 normalization; independent original CSV readback; source/order/clock/missingness and every output field. Missing signals are unassessed, not pass.'},{'stage':'unmapped_source_companions','required':'All869 identities and every supplied stream preserved with literal byte and numeric readback; no fabricated canonical tasks or cycles.'},{'stage':'native_residual_accounting','required':'All1358 Complete identities and10static groups remain distinct; uniquely matched Parsed intervals do not cover native transitions automatically.'}],policy_blockers=['Source-normalized moment denominator remains unverified: retain source aliases, withhold canonical participant moments.','Interaction-torque units unknown: retain units_unknown source aliases; do not borrow other torque-column units.','Nonuniform source clocks require interval-specific derivative policy; current exporter refuses gaps.','Existing source auditor shares stream scan/reference logic with exporter; independent whole-record side/clock checks needed before anatomical approval.'])
    output=Path(output)
    with output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    return result['counts']

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();print(json.dumps(prepare(args.output)))
