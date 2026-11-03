"""UM21-T03 full treadmill component conversion in bounded batches (standard library only).

Same bound producer (extend_umich_tread_source.py) and accepted audit (audit_um21_tread_pilot.py) as the passing
T02 pilot; no bound file changes. Two subcommands:

scope  Write the 44-record scope file from the corrected baseline and the clock census. D-UM21-T02-1 = A leaves
       the six recordings that fail the clock check (AB01 d10, d5, i5; AB08 i10; AB09 i10; AB10 i0); every other
       baseline record stays, in baseline order, split into fixed batches. Small JSON only; no research arrays.
run    One batch as the single command of one guarded-launcher job: stage the batch's baseline records bit-identical
       into a new base root, run the unchanged producer once, then the audit once per record.

Memory does not grow with records: the producer streams 150-row batches per observation and keeps only a small
summary dict; each audit is its own process. Batches bound the producer's lifetime and give each its own receipt.
Per-record outputs do not depend on which batch holds the record. scientific_approval is false everywhere.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools import run_um21_t02_pilot as pilot  # noqa: E402

BASELINE, READBACK, BASE = pilot.BASELINE, pilot.READBACK, pilot.BASE
CENSUS = ROOT / 'docs/quality/audits/um21-t02-clock-census.json'
BATCH_SIZE = 11
TIMEOUT_PRODUCER_S = 1800
TIMEOUT_AUDIT_S = 400
FILES = pilot.FILES
SCOPE_SCHEMA = 'locohub.um21_t03_scope/1'


class FullError(RuntimeError):
    pass


def digest(path):
    return pilot.digest(path)


def build_scope(baseline=BASELINE, readback_path=READBACK, census_path=CENSUS, batch_size=BATCH_SIZE):
    """Pure bookkeeping from small JSON: kept records in baseline order, dropped records with reasons."""
    summary_path = Path(baseline) / 'conversion_summary.json'
    summary = json.loads(summary_path.read_text())
    readback = json.loads(Path(readback_path).read_text())
    census = json.loads(Path(census_path).read_text())
    if readback.get('status') != 'all_tread_sagittal_exports_checked_unreviewed' \
            or readback.get('summary_sha256') != digest(summary_path) \
            or readback.get('source_sha256') != summary['source']['sha256']:
        raise FullError('verified baseline readback required')
    records = summary['recordings']
    keys = [(r['subject'], r['condition']) for r in records]
    if len(set(keys)) != len(keys):
        raise FullError('duplicate baseline identities')
    drop = {}
    for item in census['misaligned']:
        subject, condition = item['record'].split('/')
        if (subject, condition) not in keys:
            raise FullError(f'census names a record outside the baseline: {item["record"]}')
        detail = next(r['alignment'] for r in census['records'] if (r['subject'], r['condition']) == (subject, condition))
        drop[(subject, condition)] = detail.get('reason') or f'belt-speed clock misaligned by {detail["best_lag"]} frames'
    prior = {(r['subject'], r['condition']): r for r in readback['records']}
    kept = [r for r in records if (r['subject'], r['condition']) not in drop]
    dropped = [{'subject': r['subject'], 'condition': r['condition'], 'reason': drop[(r['subject'], r['condition'])],
                'decision': 'D-UM21-T02-1 = A', 'observations_not_converted': r['observations'],
                'excluded_pairs_in_baseline': prior[(r['subject'], r['condition'])]['excluded_pairs']}
               for r in records if (r['subject'], r['condition']) in drop]
    if len(kept) + len(dropped) != len(records):
        raise FullError('scope does not account for every baseline record')
    totals = census['totals']
    if len(dropped) != totals['misaligned'] or len(kept) != totals['aligned'] \
            or sum(r['observations'] for r in kept) != totals['strides_as_published_aligned_only']:
        raise FullError('scope differs from the clock census totals')
    batches = [[f"{r['subject']}/{r['condition']}" for r in kept[i:i + batch_size]] for i in range(0, len(kept), batch_size)]
    return {'schema': SCOPE_SCHEMA, 'scientific_approval': False,
            'decision': 'D-UM21-T02-1 = A (exclude recordings that fail the clock check)',
            'baseline_summary_sha256': digest(summary_path), 'baseline_readback_sha256': digest(readback_path),
            'census_sha256': digest(census_path), 'source_sha256': summary['source']['sha256'],
            'baseline_recordings': len(records), 'baseline_observations': sum(r['observations'] for r in records),
            'kept_recordings': len(kept), 'kept_observations': sum(r['observations'] for r in kept),
            'dropped': dropped, 'batch_size': batch_size, 'batches': batches,
            'kept': [{'record': f"{r['subject']}/{r['condition']}", 'observations': r['observations'],
                      'excluded_pairs': prior[(r['subject'], r['condition'])]['excluded_pairs']} for r in kept]}


def stage_records(baseline, readback_path, stage, record_ids):
    """New base root with the named records bit-identical to the baseline (hash-checked); summary and readback narrowed."""
    baseline, stage = Path(baseline), Path(stage)
    summary_path = baseline / 'conversion_summary.json'
    summary = json.loads(summary_path.read_text())
    readback = json.loads(Path(readback_path).read_text())
    if readback.get('status') != 'all_tread_sagittal_exports_checked_unreviewed' \
            or readback.get('summary_sha256') != digest(summary_path) \
            or readback.get('source_sha256') != summary['source']['sha256']:
        raise FullError('verified baseline readback required (status, summary hash or source differs)')
    by_key = {(r['subject'], r['condition']): r for r in summary['recordings']}
    prior = {(r['subject'], r['condition']): r for r in readback['records']}
    wanted = [tuple(i.split('/')) for i in record_ids]
    if len(set(wanted)) != len(wanted) or not wanted:
        raise FullError('record list must be non-empty and free of duplicates')
    for key in wanted:
        if key not in by_key or key not in prior:
            raise FullError(f'{key} missing from the baseline summary or readback')
    order = [k for k in by_key if k in set(wanted)]  # baseline order, as the producer would see it
    stage.mkdir(parents=True, exist_ok=False)
    for key in order:
        record, checked = by_key[key], prior[key]
        folder = baseline / key[0] / key[1]
        if Path(record['path']).parts != (key[0], key[1], 'phase.parquet'):
            raise FullError('baseline record path is not <subject>/<condition>/phase.parquet')
        if digest(folder / 'phase.parquet') != record['sha256'] or record['sha256'] != checked['output_sha256']:
            raise FullError(f'baseline phase file differs from its summary or readback hash: {key}')
        if digest(folder / 'candidate_ledger.jsonl') != checked['ledger_sha256']:
            raise FullError(f'baseline ledger differs from its readback hash: {key}')
        target = stage / key[0] / key[1]
        target.mkdir(parents=True)
        for name in FILES:
            shutil.copyfile(folder / name, target / name)
        if digest(target / 'phase.parquet') != record['sha256'] or digest(target / 'candidate_ledger.jsonl') != checked['ledger_sha256']:
            raise FullError(f'staged copy differs from the baseline: {key}')
    origin = {'baseline_summary_sha256': digest(summary_path), 'baseline_readback_sha256': digest(readback_path),
              'selected': [f'{s}/{c}' for s, c in order],
              'note': 'batch input narrowing for the unchanged reviewed producer; not a baseline summary'}
    staged_summary = {**summary, 'recordings': [by_key[k] for k in order], 'available_recordings': len(order),
                      'planned_recordings': len(order), 'staged_from': origin}
    summary_out = stage / 'conversion_summary.json'
    with summary_out.open('x') as stream:
        json.dump(staged_summary, stream, indent=2)
        stream.write('\n')
    readback_out = stage / 'source_comparison.json'
    with readback_out.open('x') as stream:
        json.dump({**readback, 'summary_sha256': digest(summary_out), 'records': [prior[k] for k in order],
                   'staged_from': origin}, stream, indent=2)
        stream.write('\n')
    return {'stage_root': stage, 'summary': summary_out, 'readback': readback_out, 'origin': origin, 'order': order}


def producer_command(output_root, staged, python=sys.executable):
    return [python, str(pilot.PRODUCER), '--base-root', str(staged['stage_root']),
            '--base-readback', str(staged['readback']), '--output-root', str(Path(output_root) / 'components')]


def audit_command(output_root, staged, subject, condition, source, source_sha256, python=sys.executable):
    return [python, str(pilot.AUDIT), '--source', str(source), '--pilot-root', str(Path(output_root) / 'components'),
            '--base-root', str(staged['stage_root']), '--subject', subject, '--condition', condition,
            '--output-dir', str(Path(output_root) / 'audit' / f'{subject}_{condition}'),
            '--expected-source-sha256', source_sha256]


def producer_gate(components_summary, order, scope_by_id):
    """The producer's own summary must show every batch record converted with observations equal to the scope."""
    if components_summary.get('status') != 'all_tread_joint_components_readback_unreviewed':
        raise FullError(f'producer status {components_summary.get("status")}')
    got = {(r['subject'], r['condition']): r for r in components_summary['records']}
    if list(got) != list(order):
        raise FullError('producer records differ from the batch')
    for (subject, condition), r in got.items():
        want = scope_by_id[f'{subject}/{condition}']['observations']
        if r['observations_checked'] != want or not r['existing_columns_exactly_preserved']:
            raise FullError(f'observation count or preservation differs: {subject}/{condition}')
    return got


def run(args):
    output_root = Path(args.output_root).resolve()
    if not output_root.is_relative_to(BASE):
        raise FullError('isolated output root under converted_datasets/reconversion_v2 required')
    scope_path = Path(args.scope)
    if digest(scope_path) != args.scope_sha256:
        raise FullError('scope file hash differs from --scope-sha256')
    scope = json.loads(scope_path.read_text())
    if scope.get('schema') != SCOPE_SCHEMA or not 0 <= args.batch < len(scope['batches']):
        raise FullError('unknown scope schema or batch index')
    ids = scope['batches'][args.batch]
    by_id = {r['record']: r for r in scope['kept']}
    output_root.mkdir(parents=True, exist_ok=True)  # the launcher requires it absent; this creates it
    if any(output_root.iterdir()):
        raise FullError('output root must be empty (fresh batch only)')
    summary = {'status': 'running', 'scientific_approval': False, 'batch': args.batch, 'batches_total': len(scope['batches']),
               'scope_sha256': args.scope_sha256, 'records': ids, 'steps': {}, 'audits': {},
               'staging': 'source-sign staging output; no sign application (CORE-11)'}
    target = output_root / 'run_summary.json'

    def save():
        temp = target.with_suffix('.tmp')
        temp.write_text(json.dumps(summary, indent=2) + '\n')
        temp.replace(target)
    save()
    try:
        staged = stage_records(BASELINE, READBACK, output_root / 'base_batch', ids)
        summary['staged'] = {'summary_sha256': digest(staged['summary']), 'readback_sha256': digest(staged['readback']),
                             **staged['origin']}
        code = pilot.run_step(producer_command(output_root, staged), output_root / 'producer.log', TIMEOUT_PRODUCER_S)
        summary['steps']['producer'] = {'exit_code': code}
        save()
        if code != 0:
            summary['status'] = 'producer_failed'
        else:
            made = json.loads((output_root / 'components/conversion_summary.json').read_text())
            producer_gate(made, staged['order'], by_id)
            summary['producer_records'] = [{'record': f'{r["subject"]}/{r["condition"]}', 'observations': r['observations_checked'],
                                            'source_columns': r['source_columns'], 'maximum_error': r['maximum_error'],
                                            'output_sha256': r['output_sha256'], 'ledger_sha256': r['ledger_sha256']}
                                           for r in made['records']]
            (output_root / 'audit').mkdir()
            for subject, condition in staged['order']:
                name = f'{subject}/{condition}'
                code = pilot.run_step(audit_command(output_root, staged, subject, condition, args.source, args.source_sha256),
                                      output_root / 'audit' / f'{subject}_{condition}.log', TIMEOUT_AUDIT_S)
                report = json.loads((output_root / 'audit' / f'{subject}_{condition}/audit_report.json').read_text()) \
                    if (output_root / 'audit' / f'{subject}_{condition}/audit_report.json').exists() else {}
                checks = report.get('checks', {})
                summary['audits'][name] = {'exit_code': code, 'status': report.get('status'),
                                           'checks_total': len(checks), 'checks_failed': sorted(k for k, v in checks.items() if not v.get('passed'))}
                save()
            ok = all(a['exit_code'] == 0 and a['status'] == 'pass' for a in summary['audits'].values())
            summary['status'] = 'batch_passed_unreviewed' if ok else 'audit_not_passed'
    except BaseException as error:
        summary.update(status='runner_error', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        summary['peak_rss_mib_children_max'] = pilot.peak_rss_mib()
        save()
    return 0 if summary['status'] == 'batch_passed_unreviewed' else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('scope')
    s.add_argument('--out', type=Path, required=True)
    go = sub.add_parser('run')
    go.add_argument('--output-root', type=Path, required=True)
    go.add_argument('--scope', type=Path, required=True)
    go.add_argument('--scope-sha256', required=True)
    go.add_argument('--batch', type=int, required=True)
    go.add_argument('--source', type=Path, required=True)
    go.add_argument('--source-sha256', required=True)
    args = parser.parse_args(argv)
    if args.cmd == 'scope':
        with args.out.open('x') as stream:
            json.dump(build_scope(), stream, indent=2)
            stream.write('\n')
        return 0
    return run(args)


if __name__ == '__main__':
    sys.exit(main())
