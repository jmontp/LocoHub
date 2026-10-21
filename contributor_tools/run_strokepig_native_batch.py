"""Serial native StrokePiG source exports with an exact readback after each file."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.reconvert_recording import digest, ensure_storage_headroom
from contributor_tools.run_reconversion_batch import available_memory_bytes, run_guarded_worker

CONVERTER = ROOT / 'contributor_tools/reconvert_strokepig_native.py'
CHECKER = ROOT / 'contributor_tools/audit_probes/2026_10_20/check_strokepig_native_readback.py'


def save(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temp.replace(path)


def verify_existing(folder, source, converter_hash):
    metadata = json.loads((folder / 'source_metadata.json').read_text())
    if metadata['source_sha256'] != digest(source):
        raise ValueError('Source changed; choose a new output root')
    if metadata['converter_sha256'] != converter_hash:
        raise ValueError('Converter changed; choose a new output root')
    if metadata['output_sha256'] != digest(folder / 'source_time.parquet'):
        raise ValueError('Output changed; refusing resume')
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--census', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--max-recordings', type=int)
    args = parser.parse_args()
    if args.max_recordings is not None and args.max_recordings < 1:
        parser.error('max-recordings must be positive')
    os.nice(max(0, 19 - os.nice(0)))
    for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[key] = '1'
    source_root = args.source_root.resolve()
    output = args.output_root.resolve()
    ensure_storage_headroom(output)
    output.mkdir(parents=True, exist_ok=True)
    lock = (output / 'batch.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    census = json.loads(args.census.read_text())
    if census['status'] != 'source_census_complete_unreviewed':
        raise ValueError('Source census incomplete')
    records = census['records']
    if any(r['status'] != 'inventoried' for r in records):
        raise ValueError('Source census has unresolved input failures')
    names = [r['source_recording'] for r in records]
    if not names or len(set(names)) != len(names):
        raise ValueError('Empty or ambiguous source inventory')
    for name in names:
        if not (source_root / name).resolve().is_relative_to(source_root):
            raise ValueError('Source outside root')
    files = [Path(__file__), CONVERTER, CHECKER,
             ROOT / 'contributor_tools/reconvert_recording.py',
             ROOT / 'contributor_tools/run_reconversion_batch.py']
    code = {str(p): digest(p) for p in files}
    plan = {'census_sha256': digest(args.census), 'source_root': str(source_root),
            'source_recordings': names, 'code_sha256': code}
    plan_path = output / 'batch_plan.json'
    if plan_path.exists() and json.loads(plan_path.read_text()) != plan:
        raise ValueError('Batch inputs changed; use a new output root')
    save(plan_path, plan)
    for p in files:
        copy = output / 'code' / p.relative_to(ROOT)
        copy.parent.mkdir(parents=True, exist_ok=True)
        if not copy.exists():
            copy.write_bytes(p.read_bytes())
    if not args.run:
        print(json.dumps({'planned_recordings': len(records), 'status': 'planned_only'}))
        return
    state = {'status': 'running', 'pid': os.getpid(), 'planned_recordings': len(records),
             'records': [], 'scientific_approval': False}
    status_path = output / 'batch_status.json'
    save(status_path, state)
    try:
        for record in records:
            if (output / 'STOP_AFTER_CURRENT').exists():
                state['status'] = 'stopped_by_request'
                break
            if args.max_recordings and len(state['records']) >= args.max_recordings:
                state['status'] = 'partial_requested_limit'
                break
            ensure_storage_headroom(output)
            if shutil.disk_usage('/mnt/c').free < 1024**3:
                raise OSError('Windows backing drive below 1 GiB free')
            if available_memory_bytes() < 3 * 1024**3:
                raise MemoryError('Worker cap plus reserve unavailable')
            if digest(args.census) != plan['census_sha256'] or any(digest(Path(p)) != h for p, h in code.items()):
                raise RuntimeError('Reviewed code or census changed')
            relative = Path(record['source_recording'])
            source = source_root / relative
            if digest(source) != record['sha256']:
                raise ValueError('Source changed since census')
            # Retain the complete filename, including suffix, to avoid stem collisions.
            folder = output / 'recordings' / relative
            state['active_recording'] = relative.as_posix()
            save(status_path, state)
            log = output / 'logs' / (relative.as_posix() + '.log')
            log.parent.mkdir(parents=True, exist_ok=True)
            with log.open('a') as stream:
                if folder.exists():
                    verify_existing(folder, source, code[str(CONVERTER)])
                else:
                    command = [sys.executable, str(CONVERTER), '--source-root', str(source_root),
                               '--recording', relative.as_posix(), '--output-root', str(folder)]
                    result = run_guarded_worker(command, stdout=stream, timeout=120, output_root=output)
                    if result.returncode:
                        raise RuntimeError('Export failed; see ' + str(log))
                command = [sys.executable, str(CHECKER), '--source-root', str(source_root), '--output-root', str(folder)]
                result = run_guarded_worker(command, stdout=stream, timeout=120, output_root=output)
                if result.returncode:
                    raise RuntimeError('Readback failed; see ' + str(log))
            metadata = verify_existing(folder, source, code[str(CONVERTER)])
            comparison = json.loads((folder / 'source_comparison.json').read_text())
            if comparison['status'] != 'exact_source_companion_readback':
                raise ValueError('Readback did not establish exact preservation')
            if any(digest(Path(p)) != h for p, h in code.items()):
                raise RuntimeError('Code changed during export or readback')
            state['records'].append({'source_recording': relative.as_posix(), 'rows': metadata['rows'],
                'components_checked': comparison['components_and_residuals_checked'],
                'output_sha256': metadata['output_sha256'], 'readback_sha256': digest(folder / 'source_comparison.json')})
            save(status_path, state)
        else:
            state['status'] = 'all_native_companions_readback_unreviewed'
    except Exception as error:
        state.update(status='stopped_incomplete', reason=str(error))
        raise
    finally:
        state.pop('active_recording', None)
        save(status_path, state)
    print(json.dumps({'status': state['status'], 'recordings': len(state['records'])}))


if __name__ == '__main__':
    main()
