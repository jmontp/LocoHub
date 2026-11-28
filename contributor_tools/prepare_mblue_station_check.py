"""Prepare a fresh station-API check of an existing immutable MBLUE pose plan.

Preparation never launches native code or reads numerical IK rows. The serial
coordinator must first review the plan and arrange the original pose pilot.
"""
import argparse
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
from contributor_tools.check_mblue_native_stations import COORDINATES,TRANSLATIONS,digest,load_json,recheck
from contributor_tools.prepare_mblue_orientation_pose_pilot import windows
from contributor_tools.audit_mblue_orientation_pose_pilot import linux
ROOT=Path(__file__).resolve().parents[1]


def coordinate_policy(path):
    with Path(path).open('rb') as f:raw=f.read(2*1024**2+1)
    if len(raw)>2*1024**2:raise ValueError('Model XML cap')
    tree=ET.fromstring(raw)
    names=[n.get('name') for n in tree.findall('.//JointSet/objects/*/coordinates/Coordinate')]
    if tuple(names)!=COORDINATES:raise ValueError('Reviewed coordinate set/order differs')
    rotation=set();translation=set()
    for joint in tree.findall('.//JointSet/objects/*'):
        axes=joint.findall('./SpatialTransform/TransformAxis')
        if len(axes)!=6:raise ValueError('Unreviewed joint type')
        for i,a in enumerate(axes):
            (rotation if i<3 else translation).update((a.findtext('coordinates') or '').split())
    if rotation!=set(COORDINATES)-TRANSLATIONS or not TRANSLATIONS<=translation or rotation & TRANSLATIONS:
        raise ValueError('Source model does not support explicit angular/translation policy')
    return [c not in TRANSLATIONS for c in COORDINATES]


def isolated_guard(text):
    changes={'convert_gtech_2021_phase_to_parquet(options)':'mblue_station_pose_check(options)',
             '-lt 1536MB':'-lt 2048MB',
             'Windows available memory fell below 1.5 GiB':'Windows available memory fell below 2 GiB'}
    for before,after in changes.items():
        if text.count(before)!=1:raise ValueError('Guard policy changed: '+before)
        text=text.replace(before,after,1)
    return text


def prepare(pilot_path,output):
    pilot_path=Path(pilot_path).resolve();pilot=load_json(pilot_path);old=pilot_path.parent
    if pilot['status']!='prepared_not_executed' or pilot['scientific_approval'] is not False:raise ValueError('Expected original prepared plan')
    bindings=dict(pilot['inputs_sha256']);bindings[str(pilot_path)]=digest(pilot_path);recheck(bindings)
    original_options=old/'options.json'
    if str(original_options) not in bindings:raise ValueError('Unbound pilot options')
    options=load_json(original_options);model=linux(options['model_path']).resolve();ik=linux(options['ik_path']).resolve()
    if str(model) not in bindings or str(ik) not in bindings:raise ValueError('Unbound model or IK')
    rotational=coordinate_policy(model)
    if options['max_rows']!=2500 or not 0<options['end_s']-options['start_s']<=10:raise ValueError('Pilot limits differ')
    if linux(options['output_path']).resolve()!=old/'body_axes.csv':raise ValueError('Original output differs')
    output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'converted_datasets/reconversion_v2'):raise ValueError('Fresh authorized output required')
    output.mkdir();code=output/'code';code.mkdir()
    worker=ROOT/'contributor_tools/native_probes/mblue_station_pose_check.m';snapshot=code/worker.name;shutil.copyfile(worker,snapshot)
    guard_source=ROOT/'contributor_tools/run_matlab_recording_guarded.ps1'
    guard=output/'run_station_guarded.ps1';guard.write_text(isolated_guard(guard_source.read_text()))
    options.update(output_path=windows(output/'stations.csv'),coordinate_names=list(COORDINATES),rotational=rotational)
    options_path=output/'options.json';options_path.write_text(json.dumps(options,indent=2)+'\n')
    paths=[Path(__file__),ROOT/'contributor_tools/check_mblue_native_stations.py',
           ROOT/'contributor_tools/audit_mblue_orientation_pose_pilot.py',
           ROOT/'contributor_tools/prepare_mblue_orientation_pose_pilot.py',worker,snapshot,guard_source,guard,options_path,
           ROOT/'tests/test_mblue_native_station_check.py']
    for p in paths:bindings[str(p.resolve())]=digest(p)
    recheck(bindings)
    result={'status':'prepared_not_executed','scientific_approval':False,'inputs_sha256':bindings,
      'pilot_plan':str(pilot_path),'pilot_options':str(original_options),'pilot_status':str(old/'native_status.json'),'pilot_output':str(old/'body_axes.csv'),
      'source_ik':str(ik),'start_s':options['start_s'],'end_s':options['end_s'],
      'command':['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',windows(guard),'-OptionsPath',windows(options_path),'-CodeDirectory',windows(code),'-MemoryMiB','2048','-TimeoutSeconds','300'],
      'readback_command':['python3','-m','contributor_tools.check_mblue_native_stations','--plan',str(output/'plan.json')],
      'limits':{'native_memory_mib':2048,'windows_runtime_reserve_mib':2048,'coordinator_startup_windows_available_mib':4352,'native_timeout_s':300,'max_source_rows':200000,'max_selected_rows':2500,'selected_window_s':10},
      'method':'Independent text source reader and explicit XML-checked degree/translation policy; origin plus three unit stations per body via findStationLocationInGround. Compare with original expressVectorInGround output and raw source clock/coordinate values.',
      'remaining_gates':['Coordinator must schedule both native executions exclusively with existing host headroom/disk guards and cleanup; preparation is not a launch wrapper.',
                        'Actual guarded native outputs and original source coordinates remain untested.',
                        'Shared native engine is not an independent model/anatomical validation; canonical orientation stays unavailable.',
                        'Full 335-block/15061-observation lineage and physical reconstruction remain open.']}
    (output/'plan.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pilot-plan',required=True,type=Path);p.add_argument('--output-root',required=True,type=Path);a=p.parse_args()
    prepare(a.pilot_plan,a.output_root);print(a.output_root/'plan.json')
