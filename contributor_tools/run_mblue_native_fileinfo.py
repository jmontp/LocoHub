"""Validate or explicitly run one prepared, hard-capped native metadata export."""
import argparse
import json
from pathlib import Path
import subprocess
from contributor_tools.prepare_mblue_orientation_pose_pilot import digest,windows
from contributor_tools.export_mblue_fileinfo_metadata import select_fields


def recheck(bindings):
    for path,sha in bindings.items():
        if digest(path)!=sha:raise ValueError('Bound input changed: '+path)


def validate_payload(payload,sources):
    if set(payload)!={'subjects'} or set(payload['subjects'])!={s['subject'] for s in sources}:raise ValueError('Native subject scope differs')
    result={}
    for source in sources:
        subject=source['subject'];info=payload['subjects'][subject];tasks=[tuple(t) for t in source['tasks']]
        conditions={c for c,_ in tasks}
        if set(info)!={'subject','date',*conditions}:raise ValueError('Native metadata fields differ')
        for condition in conditions:
            expected={task for c,task in tasks if c==condition}
            if set(info[condition])!=expected:raise ValueError('Native task scope differs')
            key='vicon_filename' if condition=='bare' else 'filename_suffix'
            if any(set(info[condition][task])!={key} for task in expected):raise ValueError('Native task fields differ')
        selected=select_fields(subject,info,tasks)
        selected.update(source_fileinfo_path=source['path'],source_fileinfo_sha256=source['sha256'])
        result[subject]=selected
    return result


def execute(plan_path):
    plan_path=Path(plan_path).resolve();out=plan_path.parent;plan=json.loads(plan_path.read_text())
    if plan['status']!='prepared_native_metadata_not_executed':raise ValueError('Native preparation required')
    if any((out/n).exists() for n in ('native_attempt.json','native_status.json','native_metadata.json','fileinfo_metadata.json')):raise FileExistsError('Existing native attempt preserved')
    bindings=dict(plan['bindings']);bindings[str(plan_path)]=digest(plan_path);recheck(bindings)
    if str(Path(__file__).resolve()) not in bindings:raise ValueError('Runner must be frozen by plan')
    (out/'native_attempt.json').write_text(json.dumps({'status':'started','plan_sha256':bindings[str(plan_path)]})+'\n')
    with (out/'guard.log').open('x') as stream:
        subprocess.run(plan['command'],stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=180)
    recheck(bindings)
    status_path=out/'native_status.json';status=json.loads(status_path.read_text(encoding='utf-8-sig'))
    if status.get('status')!='completed' or status.get('exit_code')!=0 or status.get('options')!=windows(out/'options.json'):
        raise ValueError('Native metadata execution did not complete with bound options')
    raw=out/'native_metadata.json'
    if raw.stat().st_size>1024**2:raise ValueError('Native metadata output exceeds1MiB')
    evidence={str(raw):digest(raw),str(status_path):digest(status_path)}
    subjects=validate_payload(json.loads(raw.read_text()),plan['sources'])
    recheck(bindings);recheck(evidence)
    result={'status':'fileinfo_metadata_exported_unreviewed','scientific_approval':False,'subjects':subjects,
        'plan_sha256':bindings[str(plan_path)],'rebuild_sha256':plan['rebuild_sha256'],'exporter_sha256':digest(__file__),
        'bindings':bindings,'native_evidence':evidence,'source_string_decode':'Native MATLAB char(string) scalar decoding; no numerical arrays exported'}
    with (out/'fileinfo_metadata.json').open('x') as stream:json.dump(result,stream,indent=2)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--run',action='store_true');a=p.parse_args()
    if not a.run:
        plan=json.loads(a.plan.read_text());recheck(plan['bindings']);print(json.dumps({'status':plan['status'],'subjects':len(plan['sources']),'executed':False}));return
    result=execute(a.plan);print(json.dumps({'status':result['status'],'subjects':len(result['subjects'])}))
if __name__=='__main__':main()
