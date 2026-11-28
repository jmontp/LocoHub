"""Create a NEW queue-compatible native metadata receipt; never rewrite failure.

This does not run MATLAB, signal queues, or authorize scientific publication.
Dependent frozen queues must be retired and explicitly replaced by the controller.
"""
import argparse
import json
from pathlib import Path
from contributor_tools.run_mblue_native_fileinfo import recheck, validate_payload
from contributor_tools.prepare_mblue_orientation_pose_pilot import digest, windows


def reconcile(old_plan_path, old_status_path, native_plan_path, output_root, alive=None):
    alive=alive or (lambda pid:Path(f'/proc/{pid}').exists())
    paths=[Path(p).resolve() for p in (old_plan_path,old_status_path,native_plan_path)]
    old_plan_path,old_status_path,native_plan_path=paths
    output_root=Path(output_root).absolute()
    if output_root.exists() or output_root.is_symlink():raise FileExistsError('New handoff root required')
    old_plan=json.loads(old_plan_path.read_text());old_status=json.loads(old_status_path.read_text());native_plan=json.loads(native_plan_path.read_text())
    if old_status.get('status') not in ('stopped_incomplete','stopped_by_request') or old_status.get('scientific_approval') is not False:
        raise ValueError('Original queue must be terminal, with failure/stop preserved')
    if not isinstance(old_status.get('pid'),int) or alive(old_status['pid']):raise ValueError('Original queue PID must be absent')
    worker=old_status.get('worker_pid')
    if worker is not None and (not isinstance(worker,int) or worker<=0 or alive(worker)):
        raise ValueError('Original worker PID is invalid or still alive')
    prerequisite=Path(old_plan['prerequisite_summary'])
    if json.loads(prerequisite.read_text()).get('status')!=old_plan['prerequisite_status']:
        raise ValueError('Original upstream prerequisites remain incomplete')
    jobs=old_plan['jobs']
    if len(jobs)!=1 or jobs[0]['name']!='mblue_fileinfo_metadata':raise ValueError('Unexpected replaced job scope')
    old_metadata_plan_path=Path(jobs[0]['output'])/'plan.json'
    old_metadata_plan=json.loads(old_metadata_plan_path.read_text())
    if native_plan['sources']!=old_metadata_plan['sources'] or native_plan['rebuild_sha256']!=old_metadata_plan['rebuild_sha256']:
        raise ValueError('Native replacement source scope differs')
    recheck(jobs[0]['code_sha256']);recheck(native_plan['bindings'])
    folder=native_plan_path.parent;receipt_path=folder/'fileinfo_metadata.json';receipt=json.loads(receipt_path.read_text())
    if receipt.get('status')!='fileinfo_metadata_exported_unreviewed' or receipt.get('scientific_approval') is not False:
        raise ValueError('Successful unreviewed native metadata receipt required')
    if receipt['plan_sha256']!=digest(native_plan_path) or receipt['rebuild_sha256']!=native_plan['rebuild_sha256']:
        raise ValueError('Native plan/rebuild binding differs')
    expected_bindings={**native_plan['bindings'],str(native_plan_path):digest(native_plan_path)}
    if receipt['bindings']!=expected_bindings:raise ValueError('Native receipt code/source bindings differ')
    recheck(receipt['bindings']);recheck(receipt['native_evidence'])
    raw=folder/'native_metadata.json';status_path=folder/'native_status.json'
    if set(receipt['native_evidence'])!={str(raw),str(status_path)}:raise ValueError('Native evidence set differs')
    if raw.stat().st_size>1024**2:raise ValueError('Native metadata exceeds admission')
    native_status=json.loads(status_path.read_text(encoding='utf-8-sig'))
    if native_status.get('status')!='completed' or native_status.get('exit_code')!=0 or native_status.get('options')!=windows(folder/'options.json'):
        raise ValueError('Native execution did not complete with expected options')
    if validate_payload(json.loads(raw.read_text()),native_plan['sources'])!=receipt['subjects']:
        raise ValueError('Native selected subjects/tasks differ from raw payload')
    all_paths=[*paths,prerequisite,old_metadata_plan_path,receipt_path,raw,status_path,Path(__file__).resolve()]
    bindings={str(p):digest(p) for p in all_paths};bindings.update(expected_bindings)
    recheck(bindings)
    output_root.mkdir()
    result={'status':'finished_unreviewed','scientific_approval':False,'replacement_kind':'native_metadata_only','superseded_queue_status':old_status,'superseded_queue_status_path':str(old_status_path),'bindings':bindings,'jobs':[{'name':'mblue_fileinfo_native_replacement','exit_code':0,'output':str(folder),'status':receipt['status'],'summary_exists':True,'summary_sha256':digest(receipt_path)}],'metadata_path':str(receipt_path),'controller_requirement':'Only NEW descendant queue plans may consume this receipt. Preserve original failed/stopped queue statuses; retire old descendants and ensure all old PIDs/workers absent before requeueing. No numerical worker started by this reconciliation.'}
    with (output_root/'queue_status.json').open('x') as stream:json.dump(result,stream,indent=2)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('old-plan','old-status','native-plan','output-root'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();print(json.dumps(reconcile(a.old_plan,a.old_status,a.native_plan,a.output_root)))


if __name__=='__main__':main()
