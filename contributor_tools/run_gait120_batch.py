#!/usr/bin/env python3
"""Inventory or reconstruct Gait120 one source file per guarded process.

Default is inventory only. --run creates immutable, unreviewed outputs; matching
source/code/output hashes permit resume. Failures stop without deleting evidence.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'ARROW_NUM_THREADS'):
    os.environ[name] = '1'

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.reconvert_recording import digest, ensure_storage_headroom
from contributor_tools.run_reconversion_batch import run_guarded_worker, available_memory_bytes

CODE = ROOT / 'contributor_tools/conversion_scripts/Gait120'
TASKS = {'LevelWalking': 'level_walking', 'SitToStand': 'sit_to_stand',
         'StandToSit': 'stand_to_sit', 'StairAscent': 'stair_ascent',
         'StairDescent': 'stair_descent', 'SlopeAscent': 'incline_walking',
         'SlopeDescent': 'decline_walking'}


def inventory(root):
    records = []
    unsupported = []
    for subject in sorted(root.glob('S*')):
        if not subject.is_dir():
            continue
        for source in sorted(p for p in (subject / 'JointAngle').rglob('*') if p.is_file() and p.suffix.lower() == '.mot'):
            relative = source.relative_to(root)
            if len(relative.parts) != 5 or relative.parts[2] not in TASKS:
                unsupported.append(str(relative))
            else:
                records.append(str(relative))
    return {'recordings': records, 'unsupported_source_paths': unsupported,
            'subjects': sorted({Path(p).parts[0] for p in records})}


def source_files(root, relative):
    subject, _, task, trial, name = Path(relative).parts
    source = root / relative
    sheet = root / 'Anthropometric_Data_Participants.xlsx'
    if not sheet.exists():
        sheet = CODE / sheet.name
    paths = [source, sheet]
    for kind, extension in [('MOT', '.mot'), ('TRC', '.trc')]:
        path = root / subject / 'MotionCapture' / task / kind / trial / Path(name).with_suffix(extension)
        if path.exists():
            paths.append(path)
    if sum(p.stat().st_size for p in paths) > 64 * 1024**2:
        raise MemoryError('Recording exceeds 64 MiB source admission')
    return paths


def hashes(paths):
    return {str(p.resolve()): digest(p) for p in paths}


def resume_matches(folder, sources, code):
    path = folder / 'conversion_manifest.json'
    if not path.exists():
        return False
    manifest = json.loads(path.read_text())
    return (manifest.get('status') == 'converted_unreviewed'
            and manifest.get('sources') == sources and manifest.get('code') == code
            and (folder / 'phase.parquet').is_file()
            and manifest.get('output_sha256') == digest(folder / 'phase.parquet'))


def worker(args):
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024**2, 1024 * 1024**2))
    sys.path.insert(0, str(CODE))
    from contributor_tools.conversion_scripts.Gait120 import convert_gait120_to_parquet as converter
    from contributor_tools.common.data_contract import inspect_contract
    import pandas as pd
    relative = Path(args.worker)
    source = args.source_root / relative
    folder = args.output_root / 'recordings' / relative.with_suffix('')
    code = json.loads((args.output_root / 'code_hashes.json').read_text())
    if hashes(map(Path, code)) != code:
        raise ValueError('Converter code changed since inventory')
    sources = hashes(source_files(args.source_root, relative))
    if folder.exists():
        if resume_matches(folder, sources, code):
            return
        raise ValueError(f'Existing output has different/incomplete evidence: {folder}')
    ensure_storage_headroom(folder)
    folder.mkdir(parents=True)
    subject, _, task, _, _ = relative.parts
    anthropometry = converter.get_subject_anthropometrics(subject, args.source_root)
    frame = converter.process_step_file(source, f'G120_{subject}', TASKS[task], task, 0,
        subject_mass_kg=anthropometry['mass_kg'], subject_height_m=anthropometry['height_m'])
    if frame is None or len(frame) != 150 or not inspect_contract(frame, mode='phase').schema_passed:
        raise ValueError('Empty or structurally invalid conversion')
    output = folder / 'phase.parquet'
    frame.to_parquet(output, index=False)
    pd.testing.assert_frame_equal(frame.reset_index(drop=True), pd.read_parquet(output))
    if hashes(map(Path, sources)) != sources or hashes(map(Path, code)) != code:
        raise ValueError('Source or code changed during conversion')
    manifest = {'status': 'converted_unreviewed', 'sources': sources, 'code': code,
                'output_sha256': digest(output), 'rows': len(frame),
                'observation_id': frame.observation_id.iloc[0], 'schema_passed': True,
                'scientific_approval': False,
                'limitations': ['Anatomical force/COP mapping unresolved',
                                'Default precomputed kinematics only; experimental ID excluded',
                                'Non-sagittal source signals not yet standardized']}
    (folder / 'conversion_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=Path('/mnt/s/locomotion_data/Gait120'))
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--worker', help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.source_root = args.source_root.resolve()
    args.output_root = args.output_root.resolve()
    if args.worker:
        relative = Path(args.worker)
        if relative.is_absolute() or '..' in relative.parts or len(relative.parts) != 5:
            parser.error('Worker recording must be a relative inventory path')
        worker(args)
        return
    ensure_storage_headroom(args.output_root)
    args.output_root.mkdir(parents=True, exist_ok=True)
    plan = inventory(args.source_root)
    code_paths = sorted(CODE.glob('*.py')) + sorted((ROOT / 'contributor_tools/common').rglob('*.py'))
    code_paths += [Path(__file__), ROOT / 'contributor_tools/reconvert_recording.py', ROOT / 'contributor_tools/run_reconversion_batch.py']
    code = hashes(code_paths)
    for name, value in [('source_inventory.json', plan), ('code_hashes.json', code)]:
        path = args.output_root / name
        if path.exists() and json.loads(path.read_text()) != value:
            raise ValueError(f'{name} changed; choose a new output directory')
        path.write_text(json.dumps(value, indent=2) + '\n')
    for path in code_paths:
        target = args.output_root / 'code' / path.resolve().relative_to(ROOT)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    print(json.dumps({'subjects': len(plan['subjects']), 'recordings': len(plan['recordings']),
                      'unsupported': len(plan['unsupported_source_paths'])}), flush=True)
    if not args.run:
        return
    state = {'status': 'running', 'completed': 0, 'total': len(plan['recordings']), 'pid': os.getpid()}
    def save():
        path = args.output_root / 'batch_status.tmp'
        path.write_text(json.dumps(state, indent=2) + '\n')
        path.replace(args.output_root / 'batch_status.json')
    try:
        for relative in plan['recordings']:
            if (args.output_root / 'STOP_AFTER_CURRENT').exists():
                state['status'] = 'stopped_by_request'
                break
            ensure_storage_headroom(args.output_root)
            if available_memory_bytes() < 3 * 1024**3:
                raise MemoryError('Need 1 GiB worker capacity plus 2 GiB reserve')
            state['recording'] = relative
            save()
            command = [sys.executable, str(Path(__file__).resolve()), '--source-root', str(args.source_root),
                       '--output-root', str(args.output_root), '--worker', relative]
            with (args.output_root / 'worker.log').open('a') as log:
                log.write('\n' + relative + '\n'); log.flush()
                result = run_guarded_worker(command, stdout=log, timeout=120, output_root=args.output_root)
            if result.returncode:
                raise RuntimeError(f'Worker failed for {relative}: {result.returncode}')
            state['completed'] += 1
            save()
            time.sleep(.2)
        else:
            state['status'] = 'complete_unreviewed' if not plan['unsupported_source_paths'] else 'incomplete_unsupported_sources'
    except Exception as error:
        state['status'] = 'stopped_incomplete'
        state['reason'] = str(error)
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
