"""Prepare/run all GT25 identities using selected inputs and isolated serial workers.

No publication approval: source-normalized moments/interaction units and virtual
IMU anatomical references remain explicitly unresolved. Frozen v4 is not edited.
"""
import argparse
import ast
import re
from collections import Counter
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
BASE=ROOT/'converted_datasets/reconversion_v2'
from contributor_tools.run_gt25_normalization_pilot_v4 import digest,verify,acceptance
from contributor_tools.preserve_mblue_planar_estimates import headroom,windows_available_mib
from contributor_tools.run_gt25_coverage_pilot import linux_available_mib
FAMILY=Path('contributor_tools/conversion_scripts/GaTech_2025_DomainAdaptation')
KINDS=('angle_filt','moment_filt','grf','velocity','insole_sim','moment_filt_bio','power','power_bio','exo','exo_sim','imu_sim')
LIMITS=['Source fidelity is not anatomical approval.','Canonical moments/assistance withheld; source moment denominator and interaction units unknown.','Virtual IMU segment estimates are independently standing-zeroed local gyro-z estimates, not established global sagittal orientations; separate successor must preserve derived estimates and withhold unsupported canonical fields.','Regular-worker observation filtering still needs an independent event/exclusion and numerical-source audit.','192 excluded/unresolved recording identities remain explicit, never silently omitted.']


def identities(records):
    keys=[(r['subject'],r['recording']) for r in records]
    if len(keys)!=len(set(keys)):raise ValueError('Duplicate recording identity')
    for key in keys:
        if any(Path(x).name!=x or x in ('.','..') for x in key):raise ValueError('Invalid source identity')
    return set(keys)


def classify(record):
    size=sum(x['bytes'] for x in record['source_files'])
    if size!=record['selected_bytes_including_readme']:raise ValueError('Selected source total differs')
    if record['canonical_task'] is None:return 'excluded_unresolved_observation_semantics'
    if size<=64*1024**2 and 256*1024**2+16*size<=1536*1024**2:return 'regular_selected_worker'
    if record['canonical_task']=='sit_to_stand' and record['recording'].startswith('sit_to_stand_'):return 'streaming_transfer_worker'
    raise ValueError('Unadmitted mapped recording; explicit policy required')


def prepare(output):
    oldpath=BASE/'gt25_ankle_pilot_handoff_v3_20261021/full_batch_replacement_preparation.json';old=json.loads(oldpath.read_text())
    inventorypath=BASE/'gt25_full_20261021/inventory.json';inventory=json.loads(inventorypath.read_text())
    if identities(old['records'])!=identities(inventory) or len(inventory)!=676:raise ValueError('Full inventory identity coverage differs')
    bykey={(r['subject'],r['recording']):r for r in inventory}
    pilotpath=BASE/'gt25_normalization_pilot_handoff_v4_20261021/execution_plan.json';pilot=json.loads(pilotpath.read_text())
    proposal=BASE/'gt25_ankle_normalization_proposal_v4_20261021';snapshot=proposal/'isolated_repo'
    tree=ast.parse((snapshot/FAMILY/'convert_gtech_2025_da_to_parquet.py').read_text())
    mapping=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='TASK_MAPPING' for t in n.targets))
    records=[]
    for source in old['records']:
        record=dict(source);record.pop('future_worker_command',None)
        mapped=next((v[0] for pattern,v in mapping.items() if re.search(pattern,record['recording'])),None)
        if mapped!=record['canonical_task']:raise ValueError('Prepared task differs from frozen v4 mapping')
        record['original_inventory_task']=bykey[(record['subject'],record['recording'])]['canonical_task']
        record['mapping_changed_since_original_inventory']=record['original_inventory_task']!=mapped
        record['route']=classify(record);record['status']='excluded_unresolved_observation_semantics' if record['route'].startswith('excluded') else 'pending'
        record['output']=str(output/'records'/record['subject']/record['recording'])
        record['independent_audit_requirement']={'regular_selected_worker':'pending_bounded_raw_source_event_and_all_numeric_feature_readback','streaming_transfer_worker':'required_v4_independent_transfer_readback_then_segment_metadata_preservation','excluded_unresolved_observation_semantics':'not_applicable_conversion; observation_semantics_unresolved'}[record['route']]
        records.append(record)
    bindings=dict(pilot['bindings'])
    for path in [oldpath,inventorypath,pilotpath,Path(__file__),ROOT/'docs/quality/audits/gt25-virtual-imu-segment-review.json',ROOT/'contributor_tools/run_gt25_coverage_pilot.py',ROOT/'contributor_tools/clarify_gt25_transfer_segments.py',ROOT/'contributor_tools/audit_gt25_selected_coverage.py',ROOT/'contributor_tools/run_gt25_normalization_pilot_v4.py']:
        bindings[str(path.resolve())]=digest(path)
    return {'status':'prepared_not_executed','scientific_approval':False,'bindings':bindings,'snapshot':str(snapshot),'proposal':str(proposal),'pilot_plan':str(pilotpath),'source_root':'/mnt/s/locomotion_data/GaTech_2025_DomainAdaptation/Parsed','records':records,'counts':dict(Counter(r['route'] for r in records)),'limitations':LIMITS,'workers':1,'regular_cap_mib':1536,'streaming_cap_mib':768,'source_identity_policy':'Inventory binds selected paths/size/mtime only. Full source hashes acquired by each worker then rechecked; not proof of original inventory-time source values.'}


def prerequisite(plan):
    pilotpath=Path(plan['pilot_plan']);pilot=json.loads(pilotpath.read_text());summarypath=Path(pilot['attempt_root'])/'handoff_summary.json';summary=json.loads(summarypath.read_text())
    if summary['status']!='corrected_transfer_source_readback_complete_unreviewed' or summary['handoff_sha256']!=digest(pilotpath):raise ValueError('Actual successful v4 pilot required')
    if [s['name'] for s in summary['stages']]!=['conversion','audit']:raise ValueError('Pilot source readback stage missing')
    for stage,done in zip(pilot['stages'],summary['stages']):
        if stage['report']!=done['report'] or digest(done['report'])!=done['report_sha256']:raise ValueError('Pilot receipt changed')
        report=json.loads(Path(done['report']).read_text());acceptance(report,stage['name']);verify(report.get('bindings',{}))
        if stage['name']=='conversion':
            if {r['source_path']:r['source_sha256'] for r in report['sources']}!=pilot['expected_source_hashes']:raise ValueError('Pilot source coverage differs')
            if digest(Path(done['report']).parent/'phase.parquet')!=report['phase_sha256']:raise ValueError('Pilot output changed')
    return {str(summarypath):digest(summarypath),**{s['report']:s['report_sha256'] for s in summary['stages']}}


def selected_identity(record,source_root):
    trial=Path(source_root)/record['subject']/record['recording'];prefix=f"{record['subject']}_{record['recording']}_"
    expected=[trial/(prefix+k+'.csv') for k in KINDS if (trial/(prefix+k+'.csv')).exists()]+[Path(source_root).parent/'readme.txt']
    actual=[x['path'] for x in record['source_files']]
    if len(actual)!=len(set(actual)) or set(actual)!={str(p) for p in expected}:raise ValueError('Selected source membership changed')
    for item in record['source_files']:
        stat=Path(item['path']).stat()
        if (stat.st_size,stat.st_mtime_ns)!=(item['bytes'],item['mtime_ns']):raise ValueError('Source stat identity changed')


def guarded(command,folder,log,cap,timeout):
    if windows_available_mib()<2816 or linux_available_mib()<max(3584,cap+2048):raise MemoryError('Startup reserves unavailable')
    headroom(folder);env=dict(os.environ)
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS','NUMEXPR_NUM_THREADS'):env[key]='1'
    with log.open('x') as handle:
        p=subprocess.Popen(['nice','-n','19','ionice','-c','3',*command],cwd=ROOT,env=env,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
        start=time.monotonic();last=0
        try:
            while p.poll() is None:
                now=time.monotonic()
                if now-start>timeout:raise TimeoutError('Finite stage timeout')
                if linux_available_mib()<2048:raise MemoryError('Linux reserve')
                if now-last>=15:
                    headroom(folder)
                    if windows_available_mib()<2048:raise MemoryError('Windows reserve')
                    last=now
                time.sleep(.5)
            if p.returncode:raise RuntimeError('Worker failed: '+str(log))
        finally:
            if p.poll() is None:
                os.killpg(p.pid,signal.SIGTERM)
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()


def regular_receipt(record,path):
    result=json.loads(path.read_text())
    if any(result[k]!=record[k] for k in ('subject','recording')) or result['dataset']!='gt25' or result['source']!='Parsed':raise ValueError('Manifest identity differs')
    if result['status'] not in ('converted_unreviewed','no_accepted_observations'):raise ValueError('Nonterminal or quarantined conversion')
    expected={x['path'] for x in record['source_files']}
    if len(result['sources'])!=len(expected) or {s['path'] for s in result['sources']}!=expected:raise ValueError('Manifest omitted selected source')
    verify({s['path']:s['sha256'] for s in result['sources']})
    for item in result['outputs']:
        if Path(item['name']).name!=item['name'] or digest(path.parent/item['name'])!=item['sha256']:raise ValueError('Persisted output differs')
    rows=result['rows']
    if rows%150 or (result['status']=='converted_unreviewed' and (rows<=0 or not result['schema_passed'])):raise ValueError('Incomplete phase rows/schema')
    return {'status':result['status'],'rows':rows,'manifest':str(path),'manifest_sha256':digest(path),'independent_source_readback':'pending','scientific_approval':False}


def run(planpath):
    plan=json.loads(planpath.read_text());plan_sha=digest(planpath);verify(plan['bindings']);gate=prerequisite(plan);out=planpath.parent
    state={'status':'running','scientific_approval':False,'plan_sha256':plan_sha,'pilot_receipts':gate,'records':[dict(r) for r in plan['records']],'limitations':plan['limitations']}
    statuspath=out/'batch_status.json'
    if statuspath.exists():raise FileExistsError('Preserve previous attempt; resume needs separate reviewed handoff')
    def save():
        tmp=out/'batch_status.tmp';tmp.write_text(json.dumps(state,indent=2)+'\n');tmp.replace(statuspath)
    save()
    try:
        for record in state['records']:
            if (out/'STOP_AFTER_CURRENT').exists():state['status']='stopped_incomplete';break
            verify(plan['bindings']);verify(gate)
            if digest(planpath)!=plan_sha:raise ValueError('Plan changed')
            selected_identity(record,plan['source_root'])
            if record['route'].startswith('excluded'):continue
            folder=Path(record['output']);folder.parent.mkdir(parents=True,exist_ok=True)
            if record['route']=='regular_selected_worker':
                command=[sys.executable,str(Path(plan['snapshot'])/FAMILY/'reconvert_recording.py'),'--source-root',plan['source_root'],'--subject',record['subject'],'--recording',record['recording'],'--output-root',str(folder),'--memory-mib','1536','--max-source-mib','64']
                guarded(command,out,folder.parent/(record['recording']+'.log'),1536,180)
                record.update(regular_receipt(record,folder/'gt25/Parsed'/record['subject']/record['recording']/'conversion_manifest.json'))
            else:
                command=[sys.executable,str(ROOT/'contributor_tools/run_gt25_streaming_transfer_pilot.py'),'--prepared',plan['proposal'],'--source-root',plan['source_root'],'--subject',record['subject'],'--recording',record['recording'],'--output-root',str(folder),'--run']
                guarded(command,out,folder.parent/(record['recording']+'.log'),768,3660)
                audit=folder.parent/(record['recording']+'_audit')
                guarded([sys.executable,'-c','import runpy,sys; p=sys.argv.pop(1); runpy.run_path(p,run_name="__main__")',str(Path(plan['snapshot'])/'contributor_tools/audit_gt25_streaming_transfer_normalization_v4.py'),'--pilot',str(folder),'--output-root',str(audit),'--run'],out,folder.parent/(record['recording']+'_audit.log'),768,3660)
                converted=json.loads((folder/'conversion_summary.json').read_text());checked=json.loads((audit/'source_comparison.json').read_text())
                if converted['status']!='streaming_transfer_converted_unreviewed' or checked['status']!='independent_raw_transfer_events_and_values_checked_unreviewed' or converted['rows']!=checked['rows_checked'] or converted['observations']!=checked['observations_checked'] or checked['numeric_features_checked']!=92:raise ValueError('Transfer source readback incomplete')
                if digest(folder/'phase.parquet')!=converted['phase_sha256']:raise ValueError('Transfer output hash differs')
                expected={x['path'] for x in record['source_files'] if Path(x['path']).name!='readme.txt'}
                if len(converted['sources'])!=len(expected) or {s['source_path'] for s in converted['sources']}!=expected:raise ValueError('Transfer source membership incomplete')
                verify({s['source_path']:s['source_sha256'] for s in converted['sources']});verify(checked['bindings'])
                record.update(status='transfer_source_readback_unreviewed',rows=converted['rows'],manifest=str(folder/'conversion_summary.json'),manifest_sha256=digest(folder/'conversion_summary.json'),audit=str(audit/'source_comparison.json'),audit_sha256=digest(audit/'source_comparison.json'))
                guarded([sys.executable,str(ROOT/'contributor_tools/clarify_gt25_transfer_segments.py'),'--source',str(folder/'phase.parquet'),'--output',str(folder/'phase_segment_reference_disclosed.parquet')],out,folder.parent/(record['recording']+'_segment_metadata.log'),768,180)
                disclosure=folder/'phase_segment_reference_disclosed.parquet.review.json'
                record.update(segment_disclosure=str(disclosure),segment_disclosure_sha256=digest(disclosure))
            selected_identity(record,plan['source_root']);verify(plan['bindings']);verify(gate);save()
        else:state['status']='conversions_accounted_pending_regular_source_audit'
        verify(plan['bindings']);verify(gate)
        if digest(planpath)!=plan_sha:raise ValueError('Plan changed at final accounting')
        state['regular_independent_audit_backlog']=[{'subject':r['subject'],'recording':r['recording'],'manifest':r.get('manifest'),'manifest_sha256':r.get('manifest_sha256'),'status':'pending','acceptance':['Independent complete source event and exclusion enumeration, not output-selected windows only','All92 canonical/source numeric fields and missing masks against original selectedCSV','Every observation identity, phase150coverage, physical leg, mass/units, preserved source aliases','Separate segment reference semantics; no anatomical approval inferred']} for r in state['records'] if r['route']=='regular_selected_worker']
    except BaseException as exc:state.update(status='failed_incomplete',reason=str(exc));raise
    finally:save()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-root',type=Path,required=True);p.add_argument('--run',action='store_true');a=p.parse_args();out=a.output_root.resolve()
    if not out.is_relative_to(BASE):raise ValueError('Isolated output required')
    if a.run:
        run(out/'plan.json')
        from contributor_tools.audit_gt25_selected_coverage import check
        report=check(out)
        with (out/'independent_coverage.json').open('x') as handle:json.dump(report,handle,indent=2)
        return
    plan=prepare(out);out.mkdir(parents=True,exist_ok=False);(out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(plan['counts']))

if __name__=='__main__':main()
