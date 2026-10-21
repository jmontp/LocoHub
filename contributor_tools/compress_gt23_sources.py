"""Low-priority transparent NTFS compression, verifying every source byte hash.

Run only while bulk converters are stopped. No source files are deleted or
rewritten by Python; compact applies filesystem compression in place.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.reconvert_recording import ensure_storage_headroom
SOURCE = Path('/mnt/s/locomotion_data/Gtech_2023/RawData')


def fingerprint(path):
    before = path.stat()
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError('Source changed while hashing: ' + str(path))
    return {'sha256': h.hexdigest(), 'bytes': after.st_size, 'mtime_ns': after.st_mtime_ns}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--target-free-gib', type=float, default=24)
    parser.add_argument('--max-files', type=int)
    parser.add_argument('--recording', help='One relative CSV path for a bounded pilot')
    args = parser.parse_args()
    if args.target_free_gib <= 0 or (args.max_files is not None and args.max_files < 1):
        parser.error('Targets and limits must be positive')
    os.nice(max(0, 19 - os.nice(0)))
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024**2, 256 * 1024**2))
    ensure_storage_headroom(args.output_root)
    args.output_root.mkdir(parents=True, exist_ok=False)
    if args.recording:
        candidate = SOURCE / args.recording
        if not candidate.resolve().is_relative_to(SOURCE.resolve()) or candidate.suffix != '.csv':
            raise ValueError('Pilot must be a CSV within the source root')
        files = [candidate]
    else:
        files = sorted((p for p in SOURCE.rglob('*.csv') if p.is_file()),
                       key=lambda p: (-p.stat().st_size, str(p)))
    plan = [{'path': str(p), 'bytes': p.stat().st_size, 'mtime_ns': p.stat().st_mtime_ns} for p in files]
    (args.output_root / 'inventory.json').write_text(json.dumps(plan, indent=2) + '\n')
    code_hash = fingerprint(Path(__file__))['sha256']
    shutil.copyfile(__file__, args.output_root / 'compressor_snapshot.py')
    state = {'status': 'running', 'pid': os.getpid(), 'target_free_gib': args.target_free_gib,
             'source_root': str(SOURCE), 'files_verified': 0, 'logical_bytes_verified': 0,
             'initial_free_bytes': shutil.disk_usage('/mnt/s').free, 'code_sha256': code_hash,
             'scope': 'single_file_pilot' if args.recording else 'inventoried_source_csvs'}
    def save():
        state['current_free_bytes'] = shutil.disk_usage('/mnt/s').free
        p = args.output_root / 'status.json'
        tmp = p.with_suffix('.tmp')
        tmp.write_text(json.dumps(state, indent=2) + '\n')
        tmp.replace(p)
    save()
    try:
        with (args.output_root / 'verified_files.jsonl').open('x') as journal:
            for item in plan:
                if (args.output_root / 'STOP_AFTER_CURRENT').exists():
                    state['status'] = 'stopped_by_request'
                    break
                if shutil.disk_usage('/mnt/s').free >= args.target_free_gib * 1024**3:
                    state['status'] = 'target_headroom_reached'
                    break
                if args.max_files and state['files_verified'] >= args.max_files:
                    state['status'] = 'partial_requested_limit'
                    break
                available = int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:'))) * 1024
                if available < 2 * 1024**3 or shutil.disk_usage('/mnt/c').free < 1024**3:
                    raise RuntimeError('Memory or host-drive reserve unavailable')
                if fingerprint(Path(__file__))['sha256'] != code_hash:
                    raise RuntimeError('Compressor code changed')
                path = Path(item['path'])
                if item['bytes'] > 256 * 1024**2:
                    raise MemoryError('File exceeds the 256 MiB compression admission limit')
                if not path.resolve().is_relative_to(SOURCE.resolve()) or path.suffix != '.csv':
                    raise ValueError('Path outside the source CSV inventory')
                before = fingerprint(path)
                if (before['bytes'], before['mtime_ns']) != (item['bytes'], item['mtime_ns']):
                    raise ValueError('Source changed since inventory')
                # Save the pre-compression hash even if Windows or verification fails.
                state['active_file'] = {'path': str(path), 'before': before}
                save()
                windows_path = 'S:' + str(path).removeprefix('/mnt/s').replace('/', '\\')
                if any(c in windows_path for c in '&|<>^%!"()\r\n') or ' ' in windows_path:
                    raise ValueError('Unexpected shell characters in inventoried filename')
                command = ['/mnt/c/Windows/System32/cmd.exe', '/c', 'start', '/low', '/wait', '/b',
                           'compact.exe', '/c', '/q', windows_path]
                # Do not terminate cmd alone on a timeout: it owns a native child.
                # One file is the stop boundary; the next iteration checks reserves.
                done = subprocess.run(command, capture_output=True, text=True, stdin=subprocess.DEVNULL)
                after = fingerprint(path)
                result = {'path': str(path), 'before': before, 'after': after,
                          'returncode': done.returncode, 'compact_output': done.stdout + done.stderr}
                journal.write(json.dumps(result) + '\n')
                journal.flush()
                if done.returncode or before != after:
                    raise RuntimeError('Compression or source-integrity check failed: ' + str(path))
                state['files_verified'] += 1
                state['logical_bytes_verified'] += before['bytes']
                state.pop('active_file', None)
                save()
            else:
                state['status'] = 'all_inventoried_csvs_verified'
    except Exception as error:
        state.update(status='failed', reason=str(error))
        raise
    finally:
        save()
    print(json.dumps(state))


if __name__ == '__main__':
    main()
