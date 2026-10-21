"""Prepare bounded native FileInfo string export; never launch MATLAB."""
import argparse
import json
from pathlib import Path
import shutil
from contributor_tools.prepare_mblue_orientation_pose_pilot import digest,windows,ROOT


def prepare(source_plan,rebuild,out):
    source_plan=Path(source_plan).resolve();rebuild=Path(rebuild).resolve();out=Path(out).resolve()
    original=json.loads(source_plan.read_text())
    if original['status']!='prepared_metadata_export_not_executed' or digest(rebuild)!=original['rebuild_sha256']:
        raise ValueError('Original rebuilt metadata lineage changed')
    if not 1<=len(original['sources'])<=10 or len({s['subject'] for s in original['sources']})!=len(original['sources']):raise ValueError('Subject scope invalid')
    sources=[]
    for source in original['sources']:
        p=Path(source['path'])
        if p.stat().st_size>1024**2 or digest(p)!=source['sha256']:raise ValueError('FileInfo source admission/hash differs')
        fields=[]
        for condition,task in source['tasks']:
            if condition not in ('bare','exo'):raise ValueError('Unknown source condition')
            fields.append({'condition':condition,'task':task,'key':'vicon_filename' if condition=='bare' else 'filename_suffix'})
        sources.append({'subject':source['subject'],'path':windows(p),'fields':fields})
    if out.exists() or not out.is_relative_to(ROOT/'converted_datasets/reconversion_v2'):raise ValueError('Fresh staging root required')
    worker=ROOT/'contributor_tools/native_probes/mblue_fileinfo_metadata.m'
    original_guard=ROOT/'contributor_tools/run_matlab_recording_guarded.ps1'
    guard=original_guard.read_text();dispatch='convert_gtech_2021_phase_to_parquet(options)'
    if guard.count(dispatch)!=1 or guard.count('1536MB')!=1:raise ValueError('Guard template changed')
    out.mkdir(parents=True);(out/'code').mkdir();shutil.copyfile(worker,out/'code'/worker.name)
    (out/'run_native_guarded.ps1').write_text(guard.replace(dispatch,'mblue_fileinfo_metadata(options)').replace('1536MB','2048MB').replace('below 1.5 GiB','below 2 GiB'))
    options={'output_path':windows(out/'native_metadata.json'),'sources':sources}
    (out/'options.json').write_text(json.dumps(options,indent=2)+'\n')
    paths=[source_plan,rebuild,worker,original_guard,Path(__file__).resolve(),ROOT/'contributor_tools/run_mblue_native_fileinfo.py',ROOT/'contributor_tools/export_mblue_fileinfo_metadata.py',ROOT/'contributor_tools/prepare_mblue_orientation_pose_pilot.py',out/'code'/worker.name,out/'run_native_guarded.ps1',out/'options.json']
    bindings={str(p):digest(p) for p in paths};bindings.update({s['path']:s['sha256'] for s in original['sources']})
    plan={'status':'prepared_native_metadata_not_executed','scientific_approval':False,'sources':original['sources'],'rebuild_sha256':original['rebuild_sha256'],'bindings':bindings,
        'limits':{'subjects':10,'source_bytes_each':1024**2,'native_memory_mib':1024,'windows_startup_mib':3072,'windows_runtime_mib':2048,'native_timeout_s':120,'wrapper_timeout_s':180},
        'command':['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',windows(out/'run_native_guarded.ps1'),'-OptionsPath',windows(out/'options.json'),'-CodeDirectory',windows(out/'code'),'-MemoryMiB','1024','-TimeoutSeconds','120'],
        'reason':'SciPy MatlabOpaque MCOS strings require native MATLAB string decoding; source identity and task selection unchanged.'}
    (out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');return plan


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-plan',type=Path,required=True);p.add_argument('--rebuild',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True)
    a=p.parse_args();print(json.dumps({'status':prepare(a.source_plan,a.rebuild,a.output_root)['status']}))
if __name__=='__main__':main()
