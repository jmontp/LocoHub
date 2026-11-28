"""Summary-only native FileInfo source-scope gate; no old queue success required."""
import json
from pathlib import Path
from contributor_tools.run_mblue_native_fileinfo import validate_payload,recheck
from contributor_tools.prepare_mblue_orientation_pose_pilot import digest,windows


def merge_bindings(*groups):
    result={}
    for group in groups:
        for path,sha in group.items():
            if path in result and result[path]!=sha:raise ValueError('Conflicting evidence hash: '+path)
            result[path]=sha
    return result


def source_scope(rebuild,scope,plan):
    if rebuild.get('status')!='all_normalized_blocks_reconstructed_unreviewed' or rebuild.get('planned_blocks')!=335 or len(rebuild.get('records',[]))!=335:raise ValueError('Full335block source rebuild required')
    if scope.get('status')!='complete_mblue_scope_evidence_checked_unreviewed' or scope.get('blocks')!=335 or scope.get('observations_after')!=15061 or scope.get('retained_stair_windows')!=764:raise ValueError('Full final MBLUE scope evidence required')
    blocks=set();subjects={}
    for r in rebuild['records']:
        key=(r['subject'],r['source_path'])
        if key in blocks:raise ValueError('Duplicate source block')
        blocks.add(key);parts=r['source_path'].split('/')
        if len(parts)<2 or parts[0] not in ('bare','exo'):raise ValueError('Unknown source condition/task')
        entry=subjects.setdefault(r['subject'],{'hash':r['subject_info_sha256'],'tasks':set()})
        if entry['hash']!=r['subject_info_sha256']:raise ValueError('Inconsistent FileInfo hash')
        entry['tasks'].add(tuple(parts[:2]))
    if len(subjects)!=10 or len(plan['sources'])!=10 or len({s['subject'] for s in plan['sources']})!=10:raise ValueError('Exactly10 unique FileInfo sources required')
    if {s['subject'] for s in plan['sources']}!=set(subjects):raise ValueError('Subject source scope differs')
    for s in plan['sources']:
        expected=subjects[s['subject']]
        if len(s['tasks'])!=len(set(map(tuple,s['tasks']))) or set(map(tuple,s['tasks']))!=expected['tasks'] or s['sha256']!=expected['hash']:raise ValueError('Source task/hash scope differs')
    return {'blocks':335,'subjects':10,'observations_after':15061,'retained_stair_windows':764}


def check(plan_path,rebuild_path,scope_path,output):
    plan_path=Path(plan_path).resolve();folder=plan_path.parent;rebuild_path=Path(rebuild_path).resolve();scope_path=Path(scope_path).resolve();output=Path(output)
    if output.exists():raise FileExistsError('Preserve prior evidence')
    plan=json.loads(plan_path.read_text());rebuild=json.loads(rebuild_path.read_text());scope=json.loads(scope_path.read_text())
    facts=source_scope(rebuild,scope,plan)
    if digest(rebuild_path)!=plan['rebuild_sha256']:raise ValueError('Rebuild hash differs from native plan')
    if scope['inputs'].get('rebuild')!=str(rebuild_path) or scope['input_sha256'].get('rebuild')!=digest(rebuild_path):raise ValueError('Final scope does not bind exact rebuild')
    if plan['bindings'].get(str(rebuild_path))!=plan['rebuild_sha256']:raise ValueError('Rebuild path absent from native plan bindings')
    bindings=merge_bindings(plan['bindings'],{str(plan_path):digest(plan_path),str(rebuild_path):digest(rebuild_path),str(scope_path):digest(scope_path),str(Path(__file__).resolve()):digest(__file__)})
    for name,path in scope['inputs'].items():
        bindings=merge_bindings(bindings,{path:scope['input_sha256'][name]})
    recheck(bindings)
    for s in plan['sources']:
        p=Path(s['path'])
        if p.stat().st_size>1024**2 or digest(p)!=s['sha256']:raise ValueError('FileInfo source changed or exceeds1MiB')
    receipt_path=folder/'fileinfo_metadata.json';raw=folder/'native_metadata.json';status_path=folder/'native_status.json'
    receipt=json.loads(receipt_path.read_text());status=json.loads(status_path.read_text(encoding='utf-8-sig'))
    if receipt.get('status')!='fileinfo_metadata_exported_unreviewed' or receipt.get('scientific_approval') is not False or receipt.get('plan_sha256')!=digest(plan_path) or receipt.get('rebuild_sha256')!=plan['rebuild_sha256']:raise ValueError('Native metadata receipt incomplete')
    if receipt['bindings']!={**plan['bindings'],str(plan_path):digest(plan_path)}:raise ValueError('Receipt plan binding set differs')
    if status.get('status')!='completed' or status.get('exit_code')!=0 or status.get('options')!=windows(folder/'options.json'):raise ValueError('Native hard-guard completion absent')
    expected={str(raw):digest(raw),str(status_path):digest(status_path)}
    if receipt['native_evidence']!=expected or raw.stat().st_size>1024**2:raise ValueError('Native payload evidence differs')
    if validate_payload(json.loads(raw.read_text()),plan['sources'])!=receipt['subjects']:raise ValueError('Decoded source tasks/strings differ')
    bindings=merge_bindings(bindings,expected,{str(receipt_path):digest(receipt_path)});recheck(bindings)
    result={'status':'native_fileinfo_source_scope_checked_unreviewed','scientific_approval':False,**facts,'metadata_path':str(receipt_path),'bindings':bindings,'queue_history':'Original stopped SciPy queue remains stopped. Its upstream ordering dependency is not a scientific data prerequisite. Completed exact rebuild/source scope verified here.','limitations':['Metadata availability only; no anatomical orientation validation or scientific release approval.']}
    with output.open('x') as f:json.dump(result,f,indent=2)
    return result
