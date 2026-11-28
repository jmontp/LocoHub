"""Dynamically admit completed restored treadmill/stair baselines for preservation.

Preparation binds tools and future producer plans only; numerical output evidence
is acquired inside a separately guarded serial slot after actual source checks.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'converted_datasets/reconversion_v2'
MAPPING={f'{segment}_sagittal_angle_{side}_rad':f'derived_planar_{segment}_sagittal_angle_{side}_rad' for segment in ('shank','thigh') for side in ('contra','ipsi')}


def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def verify(bindings):
    for path,sha in bindings.items():
        if digest(path)!=sha:raise ValueError('Changed bound evidence: '+path)


def prepare(kind,out):
    oldpath=BASE/'um21_tread_stair_planar_serial_queue_20261021/plan.json';old=json.loads(oldpath.read_text());bindings={}
    for j in old['jobs']:bindings.update(j['code_sha256'])
    verify(bindings)
    upstream=BASE/('um21_tread_components_restored_20261021' if kind=='tread_components' else 'um21_stairs_restored_v2_20261021')/'plan.json';prior=json.loads(upstream.read_text());verify(prior['bindings'])
    bindings.update(prior['bindings'])
    for path in (oldpath,upstream,Path(__file__)):
        bindings[str(path.resolve())]=digest(path)
    baseline=prior['output_root'];scope=out/'scope.json';preserved=out/'preserved'
    common=['--baseline',baseline,'--scope-report',str(scope),'--output-root',str(preserved)]
    commands=[[sys.executable,str(ROOT/'contributor_tools/build_um21_planar_scope.py'),'--baseline',baseline,'--producer',kind,'--output',str(scope)], [sys.executable,str(ROOT/'contributor_tools/preserve_um21_planar_estimates.py'),*common], [sys.executable,str(ROOT/'contributor_tools/preserve_um21_planar_estimates.py'),*common,'--run']]
    return {'status':'prepared_waiting_actual_source_receipts','scientific_approval':False,'kind':kind,'upstream_plan':str(upstream),'upstream_completion':str(upstream.parent/'completion.json'),'baseline':baseline,'scope_path':str(scope),'preserved_root':str(preserved),'bindings':bindings,'commands':commands,'expected_records':50 if kind=='tread_components' else 403,'expected_observations':8626 if kind=='tread_components' else 2700,'field_mapping':MAPPING,'limits':{'address_space_mib':768,'workers':1,'stage_timeout_seconds':21600,'windows_startup_mib':2816,'windows_runtime_mib':2048,'linux_startup_mib':3584,'linux_runtime_mib':2048},'limitations':['Exact preservation under derived_planar aliases is not approval of 3D orientations or ankle conventions.','Four thigh/shank angle canonical fields become missing; all original source components/identities/sidecars and unrelated values remain unchanged.','Actual full restored baseline and independently checked source coverage are mandatory; missing future receipts are never treated as passing.']}


def upstream_gate(receipt,upstream,plan):
    expected='all50_tread_components_8626_observations_source_checked_unreviewed' if plan['kind']=='tread_components' else 'all_stairs_source_scope_checked_unreviewed'
    if receipt['status']!=expected or receipt['scientific_approval'] is not False or receipt['plan_sha256']!=plan['bindings'][plan['upstream_plan']] or receipt['bindings']!=upstream['bindings'] or receipt['source_sha256']!=upstream['source']['sha256'] or (receipt['recordings'],receipt['observations'])!=(plan['expected_records'],plan['expected_observations']):raise ValueError('Actual complete source restoration/readback required')
    if plan['kind']=='tread_components' and receipt['excluded_preserved']!=3674:raise ValueError('Tread exclusions not preserved')
    if str(Path(plan['baseline'])/'conversion_summary.json') not in receipt['artifacts']:raise ValueError('Baseline summary not bound')
    if plan['kind']=='stairs' and str(Path(plan['baseline'])/'source_comparison.json') not in receipt['artifacts']:raise ValueError('Independent stair source readback not bound')


def preservation_gate(scope,report,plan):
    if scope['status']!='complete_um21_planar_scope_checked_unreviewed' or scope['producer']!=plan['kind'] or scope['baseline_root']!=plan['baseline'] or scope['expected_records']!=plan['expected_records'] or scope['expected_observations']!=plan['expected_observations']:raise ValueError('Full dynamic scope incomplete')
    if report['status']!='um21_planar_estimates_preserved_canonical_orientations_withheld_unreviewed' or report['scientific_approval'] is not False or report['producer']!=plan['kind'] or report['scope']!='complete_bound_baseline' or report['field_mapping']!=plan['field_mapping'] or report['observations']!=plan['expected_observations']:raise ValueError('Preservation proof incomplete')
    expected={r['phase_path']:r for r in scope['records']};actual={r['phase_path']:r for r in report['records']}
    if len(expected)!=plan['expected_records'] or len(actual)!=len(report['records']) or actual.keys()!=expected.keys():raise ValueError('Preserved shard coverage differs')
    for path,r in actual.items():
        prior=expected[path]
        if not path or r['observations']!=prior['observations'] or r['rows']!=150*prior['observations'] or not all(r.get(k) is True for k in ('persisted_exact_preservation','unrelated_metadata_preserved','source_null_masks_preserved')):raise ValueError('Missing persisted exact preservation')
        if r['outputs'].keys()!=prior['outputs'].keys():raise ValueError('Source sidecar coverage changed')
        for relative,output in r['outputs'].items():
            if output['source_sha256']!=prior['outputs'][relative] or (relative!=path and output['sha256']!=output['source_sha256']):raise ValueError('Unrelated sidecar/source lineage changed')


def run(planpath):
    plan=json.loads(planpath.read_text());sha=digest(planpath);verify(plan['bindings']);out=planpath.parent
    if any((out/name).exists() for name in ('scope.json','preserved','completion.json','admission.json')):raise FileExistsError('Fresh preservation attempt required')
    upstream=json.loads(Path(plan['upstream_plan']).read_text());receiptpath=Path(plan['upstream_completion']);receipt=json.loads(receiptpath.read_text());upstream_gate(receipt,upstream,plan)
    verify(receipt['bindings']);verify(receipt['artifacts']);dynamic={str(receiptpath):digest(receiptpath),**receipt['artifacts']}
    (out/'admission.json').write_text(json.dumps({'status':'actual_complete_source_receipts_admitted','scientific_approval':False,'bindings':dynamic},indent=2)+'\n')
    for index,command in enumerate(plan['commands']):
        verify(plan['bindings']);verify(dynamic)
        if digest(planpath)!=sha:raise ValueError('Static plan changed')
        with (out/f'{index}.log').open('x') as log:subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=21600)
        if index==0:
            scope=json.loads(Path(plan['scope_path']).read_text())
            if (scope['expected_records'],scope['expected_observations'])!=(plan['expected_records'],plan['expected_observations']):raise ValueError('Scope counts differ')
    reportpath=Path(plan['preserved_root'])/'planar_preservation_summary.json';report=json.loads(reportpath.read_text());scope=json.loads(Path(plan['scope_path']).read_text());preservation_gate(scope,report,plan);verify(report['bindings']);verify(dynamic);verify(plan['bindings'])
    artifacts={str(p):digest(p) for p in (Path(plan['scope_path']),Path(plan['preserved_root'])/'plan.json',reportpath,out/'admission.json')}
    for record in report['records']:
        for relative,item in record['outputs'].items():
            path=(Path(plan['preserved_root'])/relative).resolve()
            if not path.is_relative_to(Path(plan['preserved_root'])) or digest(path)!=item['sha256']:raise ValueError('Persisted preservation output changed')
            artifacts[str(path)]=item['sha256']
    result={'status':f'full_{plan["kind"]}_planar_preservation_source_gated_unreviewed','scientific_approval':False,'plan_sha256':sha,'records':plan['expected_records'],'observations':plan['expected_observations'],'field_mapping':MAPPING,'bindings':plan['bindings'],'source_receipts':dynamic,'artifacts':artifacts,'limitations':plan['limitations']}
    with (out/'completion.json').open('x') as f:json.dump(result,f,indent=2)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--kind',choices=['tread_components','stairs'],required=True);p.add_argument('--output-root',type=Path,required=True);p.add_argument('--run',action='store_true');a=p.parse_args();out=a.output_root.resolve()
    if not out.is_relative_to(BASE):raise ValueError('Isolated staging required')
    if a.run:run(out/'plan.json');return
    plan=prepare(a.kind,out);out.mkdir(parents=True,exist_ok=False);(out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps({'records':plan['expected_records'],'observations':plan['expected_observations']}))
if __name__=='__main__':main()
