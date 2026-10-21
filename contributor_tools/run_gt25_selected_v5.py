"""Prepare/run v5 three-family + streaming pilots or all 676 identities serially.

No scientific/anatomical approval is implied. Full execution requires actual
successful fresh pilot readbacks; exclusions remain explicitly unresolved.
"""
import argparse
import ast
from collections import Counter
import json
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.run_gt25_selected_batch_v4 import (BASE,FAMILY,classify,identities,selected_identity,guarded as legacy_guarded,regular_receipt)
from contributor_tools.preserve_mblue_planar_estimates import windows_available_mib
from contributor_tools.run_gt25_normalization_pilot_v4 import digest,verify
PROPOSAL=BASE/'gt25_explicit_newton_proposal_v5_20261021'
PILOTS={'walking':('BT05','normal_walk_1_0task_1-8_on'), 'shuffle':('BT04','normal_walk_1_0task_shuffle_on'), 'transfer':('BT03','sit_to_stand_2_0task_tall-noarm_on'), 'streaming':('BT07','sit_to_stand_1_0task_short-arm_on')}
LIMITATIONS=['192 identities excluded/unresolved observation semantics; full native coverage not achieved.', 'Source moment denominator and interaction torque units unresolved; canonical moments/assistance withheld.', 'Segment estimates preserve converter/source transformations; global anatomical orientations unverified.', 'Original inventory binds source paths/stats; source hashes acquired at execution, not historical original-value proof.']


def guarded(command,folder,log,cap,timeout):
    # v4 runtime reserve remains unchanged; add cap-aware v5 admission.
    if windows_available_mib()<max(2816,cap+2048):raise MemoryError('Cap-aware Windows startup reserve unavailable')
    return legacy_guarded(command,folder,log,cap,timeout)


def prepare(out,kind,pilot_plan=None):
    oldpath=BASE/'gt25_ankle_pilot_handoff_v3_20261021/full_batch_replacement_preparation.json'
    inventorypath=BASE/'gt25_full_20261021/inventory.json'
    old=json.loads(oldpath.read_text()); inventory=json.loads(inventorypath.read_text())
    if len(old['records'])!=676 or identities(old['records'])!=identities(inventory):raise ValueError('Full identity membership differs')
    snapshot=PROPOSAL/'isolated_repo';manifestpath=PROPOSAL/'preparation_manifest.json';proposal=json.loads(manifestpath.read_text())
    if proposal['status']!='explicit_newton_v5_prepared_not_run':raise ValueError('v5 proposal required')
    bindings={str(snapshot/k):v for k,v in proposal['snapshot_code'].items()}
    files=[oldpath,inventorypath,manifestpath,Path(__file__),ROOT/'contributor_tools/run_gt25_newton_worker_v5.py',ROOT/'docs/quality/audits/gt25-virtual-imu-segment-review.json']
    # Bind transitive guard, worker/audit and disclosure imports; no source CSV reads.
    files += [ROOT/'contributor_tools'/name for name in ('run_gt25_selected_batch_v4.py','run_gt25_normalization_pilot_v4.py','preserve_mblue_planar_estimates.py','preserve_um21_planar_estimates.py','run_gt25_coverage_pilot.py','clarify_gt25_transfer_segments.py','gt25_projected_row_store.py','um21_planar_field_policy.py','audit_gt25_selected_v5_coverage.py')]
    files += list((ROOT/'contributor_tools/common').rglob('*.py'))
    bindings.update({str(p.resolve()):digest(p) for p in files});verify(bindings)
    tree=ast.parse((snapshot/FAMILY/'convert_gtech_2025_da_to_parquet.py').read_text())
    mapping=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='TASK_MAPPING' for t in n.targets))
    records=[]
    for original in old['records']:
        r=dict(original);r.pop('future_worker_command',None)
        mapped=next((v[0] for pattern,v in mapping.items() if re.search(pattern,r['recording'])),None)
        if mapped!=r['canonical_task']:raise ValueError('Task mapping differs')
        r['route']=classify(r);r['status']='excluded_unresolved_observation_semantics' if r['route'].startswith('excluded') else 'pending'
        r['output']=str(out/'records'/r['subject']/r['recording'])
        if kind=='pilot':
            families=[k for k,v in PILOTS.items() if v==(r['subject'],r['recording'])]
            if not families:continue
            r['family']=families[0]
        records.append(r)
    if kind=='full' and Counter(r['route'] for r in records)!=Counter({'regular_selected_worker':450,'streaming_transfer_worker':34,'excluded_unresolved_observation_semantics':192}):raise ValueError('Full admission counts changed; review required')
    if kind=='pilot':
        if {r['family'] for r in records}!=set(PILOTS):raise ValueError('Pilot family coverage missing')
        records.sort(key=lambda r:list(PILOTS).index(r['family']))
    else:
        if not pilot_plan:raise ValueError('Full preparation needs exact pilot plan')
        pilot_plan=pilot_plan.resolve();p=json.loads(pilot_plan.read_text())
        if p['kind']!='pilot' or p['snapshot']!=str(snapshot):raise ValueError('Wrong pilot snapshot')
        bindings[str(pilot_plan)]=digest(pilot_plan)
    return {'status':'prepared_not_executed','kind':kind,'scientific_approval':False,'bindings':bindings,'proposal':str(PROPOSAL),'snapshot':str(snapshot),'source_root':'/mnt/s/locomotion_data/GaTech_2025_DomainAdaptation/Parsed','pilot_plan':str(pilot_plan) if pilot_plan else None,'records':records,'counts':dict(Counter(r['route'] for r in records)),'limitations':LIMITATIONS,'limits':{'workers':1,'regular_address_space_mib':1536,'streaming_audit_address_space_mib':768,'windows_startup_mib':2816,'regular_windows_startup_mib':3584,'windows_runtime_mib':2048,'linux_startup_mib':3584,'linux_runtime_mib':2048,'stage_timeout_seconds':3660}}


def check_runtime(folder,plan,mode):
    path=folder/'runtime_helper.json';r=json.loads(path.read_text());h=r['helper'];snapshot=Path(plan['snapshot'])
    helper=snapshot/'contributor_tools/common/stride_segmentation.py'
    if r['status']!='actual_v5_imports_checked' or r['mode']!=mode or h['path']!=str(helper) or h['sha256']!=plan['bindings'][str(helper)] or h['callables_identity_checked']!=['segment_gait_cycles','segment_sit_stand_transfers']:raise ValueError('Actual helper provenance missing')
    if r['wrapper_sha256']!=plan['bindings'][str(ROOT/'contributor_tools/run_gt25_newton_worker_v5.py')] or r['proposal_sha256']!=plan['bindings'][str(PROPOSAL/'preparation_manifest.json')]:raise ValueError('Wrapper/proposal provenance mismatch')
    if mode=='streaming':
        detector=snapshot/'contributor_tools/gt25_streaming_transfers_newton_v5.py'
        if h['streaming_detector']!={'path':str(detector),'sha256':plan['bindings'][str(detector)]}:raise ValueError('Streaming detector mismatch')
    return {str(path):digest(path)}


def regular_accept(report,converted,pilot=False):
    if report['status']!='regular_raw_source_events_and_92_features_checked_unreviewed' or report['scientific_approval'] is not False or not report['whole_selected_source_clocks_checked'] or report['scientific_blockers']:raise ValueError('Regular independent readback failed')
    n=report['observations_checked']
    if report['rows_checked']!=converted['rows'] or n*150!=converted['rows'] or report['numeric_features_checked']!=(92 if n else 0):raise ValueError('Regular source coverage incomplete')
    if not n and (pilot or not report['no_accepted_observations_independently_checked']):raise ValueError('Pilot cannot demonstrate an empty family')


def checked_record(record,plan,pilot=False):
    folder=Path(record['output']);stream=record['route']=='streaming_transfer_worker'
    receipts=check_runtime(folder,plan,'streaming' if stream else 'regular')
    auditpath=folder.parent/(record['recording']+'_audit')/'source_comparison.json';audit=json.loads(auditpath.read_text());verify(audit['bindings'])
    audittool=Path(plan['snapshot'])/('contributor_tools/audit_gt25_streaming_transfer_newton_v5.py' if stream else 'contributor_tools/audit_gt25_regular_source_newton_v5.py')
    oracle=Path(plan['snapshot'])/'contributor_tools/audit_gt25_streaming_transfer_newton_v5.py'
    for tool in (audittool,oracle):
        if audit['bindings'].get(str(tool))!=plan['bindings'][str(tool)]:raise ValueError('Actual v5 independent audit implementation missing')
    if audit.get('scientific_approval') is not False:raise ValueError('Audit claims unsupported scientific approval')
    if stream:
        path=folder/'conversion_summary.json';converted=json.loads(path.read_text())
        if converted.get('scientific_approval') is not False:raise ValueError('Conversion claims unsupported scientific approval')
        if converted['status']!='streaming_transfer_converted_unreviewed' or audit['status']!='independent_raw_transfer_events_and_values_checked_unreviewed' or converted['rows']!=audit['rows_checked'] or converted['observations']!=audit['observations_checked'] or audit['numeric_features_checked']!=92:raise ValueError('Stream readback incomplete')
        if pilot and (converted['observations'],converted['rows'])!=(28,4200):raise ValueError('BT07 normal-load regression changed')
        if digest(folder/'phase.parquet')!=converted['phase_sha256']:raise ValueError('Stream output changed')
        expected={s['path'] for s in record['source_files'] if Path(s['path']).name!='readme.txt'}
        if len(converted['sources'])!=len(expected) or {s['source_path'] for s in converted['sources']}!=expected:raise ValueError('Stream source membership differs')
        verify({s['source_path']:s['source_sha256'] for s in converted['sources']})
        streamplan=folder/'plan.json'
        if digest(streamplan)!=converted['plan_sha256']:raise ValueError('Stream plan changed')
        streamconfig=json.loads(streamplan.read_text());verify(streamconfig['bindings'])
        if (streamconfig['subject'],streamconfig['recording'],streamconfig['snapshot'])!=(record['subject'],record['recording'],plan['snapshot']):raise ValueError('Stream identity/snapshot differs')
        if audit['bindings'].get(str(streamplan))!=digest(streamplan) or audit['bindings'].get(str(folder/'phase.parquet'))!=converted['phase_sha256']:raise ValueError('Stream audit did not bind exact outputs')
        for source in converted['sources']:
            if audit['bindings'].get(source['source_path'])!=source['source_sha256']:raise ValueError('Stream audit omitted source identity')
        disclosure=folder/'phase_segment_reference_disclosed.parquet.review.json';d=json.loads(disclosure.read_text())
        if d['status']!='transfer_segment_reference_disclosed_exact_preservation_unreviewed':raise ValueError('Segment disclosure incomplete')
        if d['source']!=str(folder/'phase.parquet') or d['source_sha256']!=converted['phase_sha256'] or d['output']!=str(folder/'phase_segment_reference_disclosed.parquet') or digest(d['output'])!=d['output_sha256'] or d['rows']!=converted['rows'] or not d['all_other_fields_masks_metadata_exact'] or d['anatomical_frame_verified']:raise ValueError('Disclosure preservation hash/semantics mismatch')
        receipts[str(disclosure)]=digest(disclosure);receipts[d['output']]=d['output_sha256']
    else:
        path=folder/'gt25/Parsed'/record['subject']/record['recording']/'conversion_manifest.json'
        converted=regular_receipt(record,path)
        manifest=json.loads(path.read_text())
        for source in manifest['sources']:
            if audit['bindings'].get(source['path'])!=source['sha256']:raise ValueError('Regular audit omitted source identity')
        for output in manifest['outputs']:
            if audit['bindings'].get(str(path.parent/output['name']))!=output['sha256']:raise ValueError('Regular audit omitted exact output')
        regular_accept(audit,converted,pilot)
        if (audit['subject'],audit['recording'])!=(record['subject'],record['recording']):raise ValueError('Wrong source audit identity')
        ledger=auditpath.parent/'event_ledger.json'
        if digest(ledger)!=audit['event_ledger_sha256']:raise ValueError('Event ledger changed')
        receipts[str(ledger)]=digest(ledger)
    if audit['bindings'].get(str(path))!=digest(path):raise ValueError('Audit did not bind actual conversion receipt')
    receipts.update({str(path):digest(path),str(auditpath):digest(auditpath)})
    return {'status':'source_readback_checked_unreviewed','rows':converted['rows'],'receipts':receipts}


def prerequisite(plan):
    if plan['kind']=='pilot':return {}
    path=Path(plan['pilot_plan']);p=json.loads(path.read_text());summarypath=path.parent/'batch_status.json';s=json.loads(summarypath.read_text())
    if s['status']!='four_family_v5_pilot_source_checked_unreviewed' or s['plan_sha256']!=digest(path) or len(s['records'])!=4:raise ValueError('Actual four-family v5 pilot required')
    if [(r['subject'],r['recording']) for r in s['records']]!=list(PILOTS.values()):raise ValueError('Pilot family identity mismatch')
    verify(p['bindings'])
    coveragepath=path.parent/'independent_coverage.json';coverage=json.loads(coveragepath.read_text())
    if coverage['status']!='independent_identity_and_source_receipt_coverage_checked_unreviewed' or coverage['plan_sha256']!=digest(path) or coverage['counts']!={'regular':3,'streaming':1,'unresolved':0}:raise ValueError('Independent pilot coverage missing')
    receipts={str(summarypath):digest(summarypath),str(coveragepath):digest(coveragepath)}
    for r,original in zip(s['records'],p['records']):
        if any(r[k]!=original[k] for k in ('subject','recording','output','route')):raise ValueError('Pilot admission changed')
        checked=checked_record(r,p,True)
        if checked['receipts']!=r['receipts']:raise ValueError('Pilot receipt mismatch')
        receipts.update(checked['receipts'])
    return receipts


def run(path):
    plan=json.loads(path.read_text());sha=digest(path);verify(plan['bindings']);gate=prerequisite(plan);out=path.parent
    status=out/'batch_status.json'
    if status.exists():raise FileExistsError('Fresh attempt required')
    state={'status':'running','plan_sha256':sha,'scientific_approval':False,'records':[dict(r) for r in plan['records']],'pilot_receipts':gate,'limitations':plan['limitations']}
    def save():
        tmp=out/'batch_status.tmp';tmp.write_text(json.dumps(state,indent=2)+'\n');tmp.replace(status)
    def verify_all():
        verify(plan['bindings']);verify(gate)
        if digest(path)!=sha:raise ValueError('Plan changed')
    save()
    try:
        for r in state['records']:
            verify_all()
            if (out/'STOP_AFTER_CURRENT').exists():state['status']='stopped_incomplete';break
            selected_identity(r,plan['source_root'])
            if r['route'].startswith('excluded'):continue
            folder=Path(r['output']);folder.parent.mkdir(parents=True,exist_ok=True);stream=r['route']=='streaming_transfer_worker'
            cmd=[sys.executable,str(ROOT/'contributor_tools/run_gt25_newton_worker_v5.py'),'--proposal',plan['proposal'],'--mode','streaming' if stream else 'regular','--source-root',plan['source_root'],'--subject',r['subject'],'--recording',r['recording'],'--output-root',str(folder)]
            if not stream:cmd+=['--memory-mib','1536','--max-source-mib','64']
            guarded(cmd,out,folder.parent/(r['recording']+'.log'),768 if stream else 1536,3660)
            audit=folder.parent/(r['recording']+'_audit');snapshot=Path(plan['snapshot'])
            tool=snapshot/('contributor_tools/audit_gt25_streaming_transfer_newton_v5.py' if stream else 'contributor_tools/audit_gt25_regular_source_newton_v5.py')
            cmd=[sys.executable,'-c','import runpy,sys; p=sys.argv.pop(1); runpy.run_path(p,run_name="__main__")',str(tool)]
            cmd+=['--pilot',str(folder)] if stream else ['--manifest',str(folder/'gt25/Parsed'/r['subject']/r['recording']/'conversion_manifest.json'),'--snapshot',plan['snapshot']]
            guarded(cmd+['--output-root',str(audit),'--run'],out,folder.parent/(r['recording']+'_audit.log'),768,3660)
            if stream:
                guarded([sys.executable,str(ROOT/'contributor_tools/clarify_gt25_transfer_segments.py'),'--source',str(folder/'phase.parquet'),'--output',str(folder/'phase_segment_reference_disclosed.parquet')],out,folder.parent/(r['recording']+'_metadata.log'),768,180)
            r.update(checked_record(r,plan,plan['kind']=='pilot'));selected_identity(r,plan['source_root']);verify_all();save()
        else:state['status']='four_family_v5_pilot_source_checked_unreviewed' if plan['kind']=='pilot' else 'all_676_accounted_484_source_checked_192_unresolved'
        verify_all()
        if identities(state['records'])!=identities(plan['records']):raise ValueError('Final coverage differs')
        state['counts']=dict(Counter(r['status'] for r in state['records']))
    except BaseException as exc:state.update(status='failed_incomplete',reason=str(exc));raise
    finally:save()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-root',type=Path,required=True);p.add_argument('--kind',choices=['pilot','full'],default='pilot');p.add_argument('--pilot-plan',type=Path);p.add_argument('--run',action='store_true');a=p.parse_args();out=a.output_root.resolve()
    if not out.is_relative_to(BASE):raise ValueError('Isolated staging required')
    if a.run:
        run(out/'plan.json')
        from contributor_tools.audit_gt25_selected_v5_coverage import check
        report=check(out)
        with (out/'independent_coverage.json').open('x') as f:json.dump(report,f,indent=2)
        return
    plan=prepare(out,a.kind,a.pilot_plan);out.mkdir(parents=True,exist_ok=False);(out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(plan['counts']))
if __name__=='__main__':main()
