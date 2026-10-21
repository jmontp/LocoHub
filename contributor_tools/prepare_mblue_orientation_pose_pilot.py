"""Prepare, never launch, one native OpenSim MBLUE source-window pose pilot."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            value.update(block)
    return value.hexdigest()


def windows(path):
    path = Path(path).resolve()
    if len(path.parts) < 4 or path.parts[:2] != ('/', 'mnt') or len(path.parts[2]) != 1:
        raise ValueError('Native input must be on a mounted Windows drive')
    return path.parts[2].upper() + ':\\' + '\\'.join(path.parts[3:])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lineage', type=Path, required=True)
    parser.add_argument('--subject', required=True)
    parser.add_argument('--source-path', required=True)
    parser.add_argument('--curve-index', type=int, required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    args = parser.parse_args()
    records = json.loads(args.lineage.read_text())['records']
    matches = [r for r in records if r['subject'] == args.subject and r['source_path'] == args.source_path]
    if len(matches) != 1:
        raise ValueError('Exactly one source-matched block required')
    record = matches[0]
    matches = [w for w in record['retained_windows'] if w['observation_id'].endswith(':column:' + str(args.curve_index))]
    if len(matches) != 1:
        raise ValueError('Exactly one retained source window required')
    window = matches[0]
    model = record['model_evidence']['model']; ik = Path(record['ik_path'])
    if ik.stat().st_size > 64*1024**2:
        raise MemoryError('IK file exceeds 64 MiB source admission')
    if digest(ik) != record['ik_sha256'] or digest(model['path']) != model['sha256']:
        raise ValueError('Matched IK/model input changed')
    start, end = window['source_event_start_s'], window['source_event_end_s']
    if not 0 < end-start <= 10:
        raise ValueError('Pilot window must be positive and at most ten seconds')
    out = args.output_root.resolve()
    staging = ROOT/'converted_datasets/reconversion_v2'
    if not out.is_relative_to(staging) or out.exists():
        raise ValueError('New authorized staging root required')
    out.mkdir(parents=True, exist_ok=False)
    code = out/'code'; code.mkdir()
    worker = ROOT/'contributor_tools/native_probes/mblue_orientation_pose_pilot.m'
    shutil.copyfile(worker, code/worker.name)
    original_guard = ROOT/'contributor_tools/run_matlab_recording_guarded.ps1'
    guard = original_guard.read_text()
    before = 'convert_gtech_2021_phase_to_parquet(options)'
    if guard.count(before) != 1:
        raise ValueError('Guard dispatch changed; inspect before adapting')
    guard_path = out/'run_pose_guarded.ps1'
    guard_path.write_text(guard.replace(before, 'mblue_orientation_pose_pilot(options)', 1))
    options = {'output_path': windows(out/'body_axes.csv'), 'model_path': windows(model['path']),
               'ik_path': windows(ik), 'opensim_home': 'C:\\OpenSim 4.4',
               'start_s': start, 'end_s': end, 'max_rows': 2500}
    (out/'options.json').write_text(json.dumps(options, indent=2)+'\n')
    sources = [args.lineage, ik, Path(model['path']), worker, original_guard, Path(__file__),
               ROOT/'contributor_tools/plan_mblue_orientation_lineage.py',
               ROOT/'contributor_tools/audit_mblue_orientation_pose_pilot.py',
               Path('/mnt/s/workspace/MBLUEAnkleOpenSimProcessing/O5_main_OpenSimProcessing.m'),
               Path('/mnt/c/OpenSim 4.4/sdk/Java/org-opensim-modeling.jar')]
    bindings = {str(p.resolve()): digest(p) for p in sources}
    bindings.update({str(p): digest(p) for p in (code/worker.name, guard_path, out/'options.json')})
    plan = {'status':'prepared_not_executed', 'scientific_approval':False,
            'observation_id':window['observation_id'], 'inputs_sha256':bindings,
            'derivation':'Current uniquely recipe-selected placed bare/exo model, native OpenSim4.4 body transforms using full original IK coordinates. This is a reproducible new model-based derivation, not a claim about an unrecorded historical model hash.',
            'axes':{'thigh':'femur local -Y','shank':'tibia local -Y','foot':'calcaneus local +X'},
            'projection':{'up':'ground +Y','forward':'pelvis local +X projected onto ground XZ and normalized per sample',
                          'thigh_shank':'atan2(dot(axis,forward), -dot(axis,up)); vertical-down zero',
                          'foot':'atan2(dot(axis,up), dot(axis,forward)); forward-horizontal zero',
                          'neutral':'No empirical offset; model body axes define geometric reference',
                          'degenerate':'Undefined horizontal heading fails; segment projection norm below1e-8 produces missing angle'},
            'limits':{'native_memory_mib':2048,'timeout_s':300,'max_source_rows':200000,'max_selected_rows':2500},
            'command':['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',windows(guard_path),'-OptionsPath',windows(out/'options.json'),'-CodeDirectory',windows(code),'-MemoryMiB','2048','-TimeoutSeconds','300'],
            'remaining_gates':['Coordinate/projection definition review; these are explicitly derived body axes, not direct measurements',
                'Native pilot must run under serial coordinator after rechecking every bound hash',
                'Independent native body-axis checks and source-coordinate readback',
                'Obtain actual retained normalized clocks before interpolation; this pilot exports original source-time poses only',
                'Full335block/model/FileInfo lineage and immutable output validation before canonical publication']}
    (out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    print(json.dumps({'status':plan['status'],'plan':str(out/'plan.json')}))


if __name__ == '__main__':
    main()
