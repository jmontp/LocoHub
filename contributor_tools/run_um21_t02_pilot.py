"""UM21-T02 treadmill component and phase pilot for ONE selected recording (standard library only).

The reviewed producer (extend_umich_tread_source.py) can only take the first N recordings in baseline order,
and changing it would invalidate the bound producer of the 50-recording recipe (restore_um21_tread_components.py).
This runner therefore leaves every bound file byte-identical and narrows the producer's INPUT instead:

1. stage: copy the selected recording's base phase.parquet and candidate_ledger.jsonl from the corrected
   baseline into a new one-record base root (bit-identical, hash-checked against the baseline summary and
   readback), and write a one-record conversion_summary.json and readback that name the same source, probe
   and ledger hashes (the producer requires summary_sha256 to equal the summary's hash);
2. run the unchanged producer on the staged root (one recording, 84 added source components);
3. run the independent audit (audit_um21_tread_pilot.py, accepted hash) on the producer output against the
   staged base root, the source and the expected source sha256.

It is meant to run as the single command of one guarded-launcher job (address space, memory, disk and
timeout guards belong to the launcher). It never signals a process, never retries, and never overwrites.
Source-sign staging only: no sign application (CORE-11) is part of this pilot. scientific_approval is false.
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
BASE = ROOT / 'converted_datasets/reconversion_v2'
BASELINE = BASE / 'um21_tread_corrected_20261020'
READBACK = BASE / 'um21_tread_full_readback_20261021/source_comparison.json'
PRODUCER = ROOT / 'contributor_tools/extend_umich_tread_source.py'
AUDIT = ROOT / 'contributor_tools/audit_um21_tread_pilot.py'
THREAD_ENV = ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'ARROW_NUM_THREADS', 'NUMEXPR_NUM_THREADS')
TIMEOUT_PRODUCER_S = 1500
TIMEOUT_AUDIT_S = 1500
FILES = ('phase.parquet', 'candidate_ledger.jsonl')


class PilotError(RuntimeError):
    pass


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def stage_base(baseline, readback_path, stage, subject, condition):
    """Build a one-record copy of the baseline under ``stage`` (must not exist). Returns the staged paths."""
    baseline, stage = Path(baseline), Path(stage)
    summary_path = baseline / 'conversion_summary.json'
    summary = json.loads(summary_path.read_text())
    readback = json.loads(Path(readback_path).read_text())
    if readback.get('status') != 'all_tread_sagittal_exports_checked_unreviewed' \
            or readback.get('summary_sha256') != digest(summary_path):
        raise PilotError('verified baseline readback required (status or summary hash differs)')
    if readback.get('source_sha256') != summary['source']['sha256']:
        raise PilotError('baseline readback and summary name different sources')
    chosen = [r for r in summary['recordings'] if (r['subject'], r['condition']) == (subject, condition)]
    prior = [r for r in readback['records'] if (r['subject'], r['condition']) == (subject, condition)]
    if len(chosen) != 1 or len(prior) != 1:
        raise PilotError(f'{subject}/{condition} must appear exactly once in the baseline summary and readback')
    record, checked = chosen[0], prior[0]
    folder = baseline / subject / condition
    if Path(record['path']).parts != (subject, condition, 'phase.parquet'):
        raise PilotError('baseline record path is not <subject>/<condition>/phase.parquet')
    if digest(folder / 'phase.parquet') != record['sha256'] or record['sha256'] != checked['output_sha256']:
        raise PilotError('baseline phase file differs from its summary or readback hash')
    if digest(folder / 'candidate_ledger.jsonl') != checked['ledger_sha256']:
        raise PilotError('baseline ledger differs from its readback hash')
    stage.mkdir(parents=True, exist_ok=False)
    target = stage / subject / condition
    target.mkdir(parents=True)
    for name in FILES:
        shutil.copyfile(folder / name, target / name)
    if digest(target / 'phase.parquet') != record['sha256'] or digest(target / 'candidate_ledger.jsonl') != checked['ledger_sha256']:
        raise PilotError('staged copy differs from the baseline')
    origin = {'baseline_summary_sha256': digest(summary_path), 'baseline_readback_sha256': digest(readback_path),
              'selected': f'{subject}/{condition}',
              'note': 'one-record input narrowing for the unchanged reviewed producer; not a baseline summary'}
    staged_summary = {**summary, 'recordings': [record], 'available_recordings': 1, 'planned_recordings': 1,
                      'staged_from': origin}
    summary_out = stage / 'conversion_summary.json'
    with summary_out.open('x') as stream:
        json.dump(staged_summary, stream, indent=2)
        stream.write('\n')
    staged_readback = {**readback, 'summary_sha256': digest(summary_out), 'records': [checked], 'staged_from': origin}
    readback_out = stage / 'source_comparison.json'
    with readback_out.open('x') as stream:
        json.dump(staged_readback, stream, indent=2)
        stream.write('\n')
    return {'stage_root': stage, 'summary': summary_out, 'readback': readback_out, 'origin': origin}


def commands(output_root, staged, subject, condition, source, source_sha256, python=sys.executable):
    """The producer and audit argument lists (pure; nothing runs)."""
    output_root = Path(output_root)
    producer = [python, str(PRODUCER), '--base-root', str(staged['stage_root']),
                '--base-readback', str(staged['readback']), '--output-root', str(output_root / 'components')]
    audit = [python, str(AUDIT), '--source', str(source), '--pilot-root', str(output_root / 'components'),
             '--base-root', str(staged['stage_root']), '--subject', subject, '--condition', condition,
             '--output-dir', str(output_root / 'audit'), '--expected-source-sha256', source_sha256]
    return producer, audit


def run_step(command, log_path, timeout, cwd=ROOT):
    env = {**os.environ, **{key: '1' for key in THREAD_ENV}}
    with Path(log_path).open('x') as log:
        done = subprocess.run(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, env=env, timeout=timeout)
    return done.returncode


def peak_rss_mib():
    """Largest peak RSS of this process's waited-for children, plus itself."""
    kib = max(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return round(kib / 1024, 1)


def run(args):
    output_root = Path(args.output_root).resolve()
    if not output_root.is_relative_to(BASE):
        raise PilotError('isolated output root under converted_datasets/reconversion_v2 required')
    subject, condition = args.record.split('/')
    output_root.mkdir(parents=True, exist_ok=True)  # the launcher requires it absent at launch; this creates it
    if any(output_root.iterdir()):
        raise PilotError('output root must be empty (fresh pilot only)')
    summary = {'status': 'running', 'scientific_approval': False, 'record': args.record, 'steps': {},
               'staging': 'source-sign staging output; no sign application (CORE-11) in this pilot'}
    target = output_root / 'run_summary.json'

    def save():
        temp = target.with_suffix('.tmp')
        temp.write_text(json.dumps(summary, indent=2) + '\n')
        temp.replace(target)
    save()
    try:
        staged = stage_base(BASELINE, READBACK, output_root / 'base_one', subject, condition)
        summary['staged'] = {'summary_sha256': digest(staged['summary']), 'readback_sha256': digest(staged['readback']),
                             **staged['origin']}
        producer, audit = commands(output_root, staged, subject, condition, args.source, args.source_sha256)
        for name, command, timeout in (('producer', producer, TIMEOUT_PRODUCER_S), ('audit', audit, TIMEOUT_AUDIT_S)):
            code = run_step(command, output_root / f'{name}.log', timeout)
            summary['steps'][name] = {'exit_code': code, 'command': command}
            save()
            if code != 0:
                summary['status'] = f'{name}_failed'
                break
        else:
            report = json.loads((output_root / 'audit/audit_report.json').read_text())
            summary['audit_status'] = report.get('status')
            summary['status'] = 'pilot_passed_unreviewed' if report.get('status') == 'pass' else 'audit_not_passed'
    except BaseException as error:  # the summary must say why; nothing is retried
        summary.update(status='runner_error', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        summary['peak_rss_mib_children_max'] = peak_rss_mib()
        save()
    return 0 if summary['status'] == 'pilot_passed_unreviewed' else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)
    go = sub.add_parser('run')
    go.add_argument('--output-root', type=Path, required=True)
    go.add_argument('--record', required=True, help='SUBJECT/CONDITION, e.g. AB04/d10')
    go.add_argument('--source', type=Path, required=True)
    go.add_argument('--source-sha256', required=True)
    args = parser.parse_args(argv)
    return run(args)


if __name__ == '__main__':
    sys.exit(main())
