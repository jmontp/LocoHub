#!/usr/bin/env python3
"""Explicitly scheduled single GT25 snapshot pilot; defaults to planning only.

Reuses the existing BT01 source audit unchanged. No anatomical approval is inferred.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FAMILY = Path('contributor_tools/conversion_scripts/GaTech_2025_DomainAdaptation')
SOURCE = Path('/mnt/s/locomotion_data/GaTech_2025_DomainAdaptation/Parsed')
AUDIT = ROOT/'contributor_tools/audit_probes/2026_10_20/check_gt25_source.py'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024**2), b''):
            h.update(chunk)
    return h.hexdigest()


def verify_snapshot(prepared):
    prepared = Path(prepared).resolve()
    allowed = (ROOT/'converted_datasets/reconversion_v2').resolve()
    if not prepared.is_relative_to(allowed):
        raise ValueError('Snapshot must be under authorized reconversion directory')
    plan = json.loads((prepared/'preparation_manifest.json').read_text())
    if plan['status'] != 'prepared_unreviewed_not_run':
        raise ValueError('Unrecognized snapshot preparation status')
    snapshot = prepared/'isolated_repo'
    for name, sha in plan['snapshot_code'].items():
        path = (snapshot/name).resolve()
        if not path.is_relative_to(snapshot) or digest(path) != sha:
            raise ValueError('Snapshot changed: '+name)
    actual = {str(p.relative_to(snapshot)) for p in (snapshot/'contributor_tools').rglob('*.py')}
    if actual != set(plan['snapshot_code']):
        raise ValueError('Snapshot Python dependency set changed')
    if digest(SOURCE.parent/'readme.txt') != plan['readme']['sha256']:
        raise ValueError('Source README no longer matches reviewed snapshot evidence')
    return snapshot, plan


def evidence(paths):
    return [{'path': str(p), 'bytes': p.stat().st_size, 'sha256': digest(p)} for p in paths]


def validate_pilot_kind(kind, recording, selected_bytes, all_csv_bytes, baseline):
    if selected_bytes > 64*1024**2:
        raise ValueError('Selected sources exceed unchanged 64 MiB admission')
    if kind == 'shuffle':
        if not (recording.startswith('normal_walk_') and '_shuffle_' in recording):
            raise ValueError('Shuffle pilot requires source shuffle recording')
    elif kind == 'recovered_admission':
        if not recording.startswith('sit_to_stand_') or all_csv_bytes <= 64*1024**2:
            raise ValueError('Recovered admission pilot must prove original all-CSV rejection')
    elif kind == 'unchanged':
        if baseline is None or '_shuffle_' in recording:
            raise ValueError('Unchanged pilot requires an ordinary recording baseline')
    else:
        raise ValueError('Unknown pilot kind')


def verify_manifest(path, expected_sources=None):
    data = json.loads(path.read_text())
    if data['status'] != 'converted_unreviewed' or not data.get('schema_passed') or data.get('rows', 0) <= 0:
        raise ValueError('Worker did not produce a nonempty schema-checked recording')
    if expected_sources is not None and data['sources'] != expected_sources:
        raise ValueError('Worker consumed a different source inventory')
    for item in data['sources'] + data['converter_code']:
        if digest(Path(item['path'])) != item['sha256']:
            raise ValueError('Recorded source/code hash changed')
    for item in data['outputs']:
        p = path.parent/item['name']
        if p.parent != path.parent or digest(p) != item['sha256']:
            raise ValueError('Recorded output changed')
    return data


def review_output(manifest, kind, baseline):
    # Called only as a separately bounded, guarded worker after conversion.
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (768*1024**2, 768*1024**2))
    import pyarrow.parquet as pq
    import pandas as pd
    data = verify_manifest(manifest)
    other = None
    if kind == 'unchanged':
        before = verify_manifest(baseline)
        if before['sources'] != data['sources'] or before['rows'] != data['rows']:
            raise ValueError('Baseline lineage/count differs')
        other = iter(pq.ParquetFile(baseline.parent/'phase.parquet').iter_batches(batch_size=150, use_threads=False))
    count = 0
    for batch in pq.ParquetFile(manifest.parent/'phase.parquet').iter_batches(batch_size=150, use_threads=False):
        frame = batch.to_pandas(use_threads=False)
        if len(frame) != 150 or frame.observation_id.nunique() != 1:
            raise ValueError('Incomplete or mixed observation')
        if kind == 'shuffle':
            if not frame.task.eq('level_walking').all():
                raise ValueError('Shuffle task mapping incorrect')
            for value in frame.task_info:
                info = json.loads(value)
                if info.get('speed_m_s') != .4 or info.get('source_variant') != 'shuffle':
                    raise ValueError('Shuffle source metadata incorrect')
        if other is not None:
            pd.testing.assert_frame_equal(frame, next(other).to_pandas(use_threads=False), check_exact=True)
        count += len(frame)
    if count != data['rows'] or (other is not None and next(other, None) is not None):
        raise ValueError('Output/baseline row count mismatch')
    print(json.dumps({'checked_rows': count, 'kind': kind, 'scientific_approval': False}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', type=Path)
    parser.add_argument('--recording')
    parser.add_argument('--kind', choices=['shuffle', 'recovered_admission', 'unchanged'])
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--review-manifest', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    for name in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'ARROW_NUM_THREADS']:
        os.environ[name] = '1'
    os.nice(max(0, 19-os.nice(0)))
    if args.review_manifest:
        review_output(args.review_manifest, args.kind, args.baseline)
        return
    if not args.prepared or not args.recording or not args.kind:
        parser.error('prepared, recording and kind are required')
    if Path(args.recording).name != args.recording or args.recording in {'.', '..'}:
        parser.error('Recording must be a single path component')
    snapshot, preparation = verify_snapshot(args.prepared)
    # Load the adapter without calling its main; this imports only stdlib worker code.
    spec = importlib.util.spec_from_file_location('gt25_pilot_adapter', snapshot/FAMILY/'reconvert_recording.py')
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    from types import SimpleNamespace
    trial, paths, _ = adapter.source_paths(SimpleNamespace(source_root=SOURCE, subject='BT01', recording=args.recording))
    sources = evidence(paths)
    validate_pilot_kind(args.kind, args.recording, sum(p['bytes'] for p in sources),
                        sum(p.stat().st_size for p in trial.glob('*.csv')), args.baseline)
    out = snapshot/'converted_datasets/reconversion_v2'/('pilot_'+args.kind+'_'+args.recording)
    if out.exists():
        raise FileExistsError('Pilot exists; inspect it rather than silently resume')
    plan = {'status': 'planned_not_run', 'sources': sources, 'snapshot_manifest_sha256': digest(args.prepared/'preparation_manifest.json'),
            'audit_sha256': digest(AUDIT), 'runner_sha256': digest(Path(__file__)), 'output': str(out),
            'scientific_approval': False, 'kind': args.kind}
    if not args.run:
        print(json.dumps(plan, indent=2))
        return
    # The existing guard monitors Linux memory/storage. Require Windows startup reserve too.
    result = subprocess.run(['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe', '-NoProfile', '-NonInteractive',
        '-Command', '[math]::Floor((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1024) | ConvertTo-Json -Compress'],
        capture_output=True, text=True, timeout=30, check=True)
    if int(json.loads(result.stdout)) < 3584:
        raise MemoryError('Need 1.5 GiB worker cap plus 2 GiB host reserve')
    from contributor_tools.run_reconversion_batch import run_guarded_worker
    from contributor_tools.reconvert_recording import ensure_storage_headroom
    ensure_storage_headroom(out)
    out.mkdir(parents=True)
    summary = dict(plan, status='running')
    try:
        commands = [[sys.executable, str(snapshot/FAMILY/'reconvert_recording.py'), '--source-root', str(SOURCE),
                     '--subject', 'BT01', '--recording', args.recording, '--output-root', str(out),
                     '--memory-mib', '1536', '--max-source-mib', '64']]
        manifest = out/'gt25/Parsed/BT01'/args.recording/'conversion_manifest.json'
        review = [sys.executable, str(Path(__file__).resolve()), '--review-manifest', str(manifest), '--kind', args.kind]
        if args.baseline:
            review += ['--baseline', str(args.baseline.resolve())]
        commands += [review, [sys.executable, str(AUDIT), '--output-root', str(out)]]
        for index, command in enumerate(commands):
            verify_snapshot(args.prepared)
            if digest(args.prepared/'preparation_manifest.json') != plan['snapshot_manifest_sha256']:
                raise ValueError('Preparation manifest changed during pilot')
            if evidence(paths) != sources or digest(AUDIT) != plan['audit_sha256']:
                raise ValueError('Source or audit changed during pilot')
            with (out/f'worker_{index}.log').open('x') as log:
                done = run_guarded_worker(command, stdout=log, timeout=180, output_root=out)
            if done.returncode:
                raise RuntimeError('Pilot stage failed: '+str(index))
        verify_manifest(manifest, sources)
        audit = json.loads((out/'source_comparison.json').read_text())
        if len(audit['recordings']) != 1 or audit['recordings'][0]['recording'] != args.recording or audit['recordings'][0]['observations_checked'] <= 0:
            raise ValueError('Source audit did not cover requested recording')
        verify_snapshot(args.prepared)
        summary.update(status='pilot_checks_passed_unreviewed', source_audit_sha256=digest(out/'source_comparison.json'),
                       conversion_manifest_sha256=digest(manifest), limitations=audit['limitations'])
    except Exception as error:
        summary.update(status='failed', reason=str(error))
        raise
    finally:
        (out/'pilot_summary.json').write_text(json.dumps(summary, indent=2)+'\n')


if __name__ == '__main__':
    main()
