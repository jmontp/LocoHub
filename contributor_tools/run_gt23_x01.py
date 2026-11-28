"""GT23-X01 source preservation and index: one participant (or named recordings) per guarded-launcher job.

Subcommands
  run      Read the named participant's recordings one at a time from the publisher's folders (read-only) and write a
           NEW output root: <root>/<recording>/<channel>.parquet companions, ledger.jsonl (one line per recording),
           events.json, participant.json, run_summary.json. Never overwrites; never writes under the source.
  spec     Write the guarded-launcher job spec (hash-bound code and evidence) for one run or audit job.
  summary  Add up finished participant roots against the acceptance counts (small JSON only).

Pilot: --records AB05/normal_walk_1 (repeatable). Python only; scientific_approval is false everywhere.
"""
import argparse
import json
import os
from pathlib import Path
import resource
import sys

os.environ.setdefault('ARROW_DEFAULT_MEMORY_POOL', 'system')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools import gt23_source_reader as rd  # noqa: E402

SOURCE = Path('/mnt/s/locomotion_data/Gtech_2023')
BASE = ROOT / 'converted_datasets/reconversion_v2'
README = ROOT / 'docs/quality/audits/source_evidence/gt23/publisher-readme.txt'
MASS_CSV = ROOT / 'docs/quality/audits/source_evidence/gt23/publisher-subject-masses.csv'
README_SHA256 = '4a5c8ef0a8d96ed3b81253e7fed2d8516b884fa2aa63e4340c0ab54cf2ac4752'
SUBJECTS = ('AB01', 'AB02', 'AB03', 'AB05', 'AB06', 'AB07', 'AB08', 'AB09', 'AB10', 'AB11', 'AB12', 'AB13')
EXPECTED = {'recordings': 488, 'channel_files': 4880, 'event_files': 787, 'empty_event_files': 9, 'windows': 13119,
            'windows_left': 7721, 'windows_right': 5398, 'with_windows': 398, 'without_windows': 90}
CODE = ('contributor_tools/gt23_source_reader.py', 'contributor_tools/run_gt23_x01.py', 'contributor_tools/guarded_launcher.py')
AUDIT_CODE = ('contributor_tools/audit_gt23_x01.py', 'contributor_tools/guarded_launcher.py')
SOURCE_CAP_NOTE = 'Local RawData/Subject_masses.csv is not the publisher file and is never read.'


class RunError(RuntimeError):
    pass


def peak_rss_mib():
    return round(max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) / 1024, 1)


def _atomic_json(path, obj):
    temp = Path(path).with_suffix('.tmp')
    temp.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')
    temp.replace(path)


def run(args):
    out = Path(args.output_root).resolve()
    source = Path(args.source).resolve()
    if not out.is_relative_to(BASE) or out == source or source in out.parents:
        raise RunError('a new output root under converted_datasets/reconversion_v2 (never the source) is required')
    if args.subject not in SUBJECTS:
        raise RunError(f'unknown participant {args.subject}')
    if rd.sha256_file(README) != README_SHA256:
        raise RunError('publisher README hash differs from the bound value')
    wanted = None
    if args.records:
        wanted = []
        for item in args.records:
            subject, rec = item.split('/')
            if subject != args.subject:
                raise RunError(f'record {item} is not for {args.subject}')
            wanted.append(rec)
    out.mkdir(parents=True, exist_ok=False)
    summary = {'status': 'running', 'scientific_approval': False, 'subject': args.subject, 'pilot_records': wanted,
               'note': SOURCE_CAP_NOTE, 'recordings_done': 0}
    target = out / 'run_summary.json'
    _atomic_json(target, summary)
    try:
        subj = rd.Subject(source, args.subject)
        recs = subj.recordings()
        if wanted is not None:
            missing = [r for r in wanted if r not in recs]
            if missing:
                raise RunError(f'named recordings not in the source: {missing}')
            recs = wanted
        readme_masses, csv_masses = rd.load_mass_tables(README, MASS_CSV)
        facts = rd.participant_facts(subj, readme_masses, csv_masses)
        all_recs = subj.recordings()
        orphans = {'marker_files_without_recording': sorted(p.stem for p in (subj.raw / 'MarkerData').glob('*.trc')
                                                             if p.stem not in all_recs),
                   'euler_files_without_recording': sorted(p.stem for p in (subj.raw / 'Transforms_Euler').glob('*.csv')
                                                            if p.stem not in all_recs)}
        facts['orphans'] = orphans
        facts['recordings_in_source'] = len(all_recs)
        events, unassigned = rd.event_ledger(subj, set(recs) if wanted is not None else None)
        facts['unassigned_event_files'] = unassigned
        _atomic_json(out / 'participant.json', facts)
        _atomic_json(out / 'events.json', {'subject': args.subject, 'files': events})
        by_rec = {}
        for item in events:
            by_rec.setdefault(item['recording'], []).append(item)
        failed = 0
        with (out / 'ledger.jsonl').open('x') as ledger:
            for rec in recs:
                files = [{k: e[k] for k in ('file', 'sha256', 'windows_left', 'windows_right') if k in e}
                         for e in by_rec.get(rec, [])]
                try:
                    entry = rd.recording_record(subj, rec, out, files)
                except Exception as error:  # a recording that cannot be read is named, then the batch continues
                    entry = {'subject': args.subject, 'recording': rec, 'status': 'failed',
                             'issues': [f'{type(error).__name__}: {error}'], 'event_files': files}
                    failed += 1
                ledger.write(rd.dumps(entry) + '\n')
                ledger.flush()
                summary['recordings_done'] += 1
                summary['peak_rss_mib'] = peak_rss_mib()
                _atomic_json(target, summary)
        summary['recordings_failed'] = failed
        summary['recordings_with_issues'] = None
        lines = [json.loads(x) for x in (out / 'ledger.jsonl').read_text().splitlines()]
        summary['recordings_with_issues'] = sum(1 for e in lines if e['status'] != 'ok')
        summary['status'] = 'participant_done_unreviewed' if not failed else 'recordings_failed'
    except BaseException as error:
        summary.update(status='runner_error', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        summary['peak_rss_mib'] = peak_rss_mib()
        _atomic_json(target, summary)
    return 0 if summary['status'] == 'participant_done_unreviewed' else 1


def events_all(args):
    """One job: the authors' stride files of all participants, counted with the corrected key rule (small .mat files only)."""
    out = Path(args.output_root).resolve()
    source = Path(args.source).resolve()
    if not out.is_relative_to(BASE) or source in out.parents:
        raise RunError('a new output root under converted_datasets/reconversion_v2 (never the source) is required')
    out.mkdir(parents=True, exist_ok=False)
    totals = {'event_files': 0, 'empty_event_files': 0, 'windows_left': 0, 'windows_right': 0, 'recordings_with_windows': 0}
    problems = []
    for subject in SUBJECTS:
        subj = rd.Subject(source, subject)
        events, unassigned = rd.event_ledger(subj)
        by_rec = {}
        for e in events:
            by_rec.setdefault(e['recording'], []).append(e)
            totals['event_files'] += 1
            n = e.get('windows_left', 0) + e.get('windows_right', 0)
            totals['empty_event_files'] += int(n == 0)
            totals['windows_left'] += e.get('windows_left', 0)
            totals['windows_right'] += e.get('windows_right', 0)
            if e.get('error') or e.get('issues'):
                problems.append(f'{subject}/{e["file"]}: {e.get("error") or e["issues"]}')
        with_windows = sorted(r for r, fs in by_rec.items() if r and sum(f.get('windows_left', 0) + f.get('windows_right', 0) for f in fs))
        totals['recordings_with_windows'] += len(with_windows)
        _atomic_json(out / f'events_{subject}.json', {'subject': subject, 'files': events, 'unassigned_files': unassigned,
                                                       'recordings_with_windows': with_windows,
                                                       'recordings_in_source': len(subj.recordings())})
        if unassigned:
            problems.append(f'{subject}: unassigned event files {unassigned}')
    totals['windows'] = totals['windows_left'] + totals['windows_right']
    want = {'event_files': EXPECTED['event_files'], 'empty_event_files': EXPECTED['empty_event_files'], 'windows': EXPECTED['windows'],
            'windows_left': EXPECTED['windows_left'], 'windows_right': EXPECTED['windows_right'],
            'recordings_with_windows': EXPECTED['with_windows']}
    checks = {k: {'got': totals[k], 'expected': v, 'equal': totals[k] == v} for k, v in want.items()}
    _atomic_json(out / 'events_summary.json', {'schema': 'locohub.gt23_x01_events/1', 'scientific_approval': False, 'totals': totals,
                                               'acceptance_counts': checks, 'all_equal': all(c['equal'] for c in checks.values()),
                                               'problems': problems, 'peak_rss_mib': peak_rss_mib()})
    return 0 if all(c['equal'] for c in checks.values()) and not problems else 1


def make_spec(args):
    from contributor_tools import guarded_launcher as gl
    out_rel = args.output_root
    receipt = args.receipt
    command = ['python3', args.script, 'run' if args.kind == 'run' else 'audit', '--output-root', out_rel,
               '--subject', args.subject]
    code = CODE if args.kind == 'run' else AUDIT_CODE
    bindings = {c: gl.sha256_file(ROOT / c) for c in code}
    if args.kind == 'run':
        bindings[str(README.relative_to(ROOT))] = rd.sha256_file(README)
        bindings[str(MASS_CSV.relative_to(ROOT))] = rd.sha256_file(MASS_CSV)
        for r in args.records or []:
            command += ['--records', r]
    else:
        batch = ROOT / args.batch_root
        command += ['--batch-root', args.batch_root, '--events-root', args.events_root]
        bindings[f'{args.events_root}/events_{args.subject}.json'] = rd.sha256_file(ROOT / args.events_root / f'events_{args.subject}.json')
        for name in ('ledger.jsonl', 'participant.json', 'run_summary.json'):
            bindings[f'{args.batch_root}/{name}'] = rd.sha256_file(batch / name)
        if args.records:
            for r in args.records:
                command += ['--records', r]
    command += ['--source', str(SOURCE)]
    spec = {'job_id': args.job_id, 'command': command, 'cwd': str(ROOT), 'output_root': out_rel, 'receipt_path': receipt,
            'bindings': bindings, 'timeout_seconds': 3600, 'kill_after_seconds': 30, 'poll_seconds': 15,
            'startup_memory_mib': {'linux': 3584, 'windows': 2816}, 'runtime_memory_mib': {'linux': 2048, 'windows': 2048},
            'expected_output_names': ['run_summary.json' if args.kind == 'run' else 'audit_report.json'],
            'address_space_mib': 768}
    with Path(args.spec_out).open('x') as stream:
        json.dump(spec, stream, indent=2)
        stream.write('\n')
    return 0


def summarize(args):
    """Recordings and channel files from the participant ledgers; event files and windows from the events root."""
    tot = {'recordings': 0, 'channel_files': 0, 'recordings_with_issues': 0, 'recordings_failed': 0}
    issues, problems, seen = {}, [], set()
    for root in args.roots:
        for line in (Path(root) / 'ledger.jsonl').read_text().splitlines():
            r = json.loads(line)
            key = (r['subject'], r['recording'])
            if key in seen:
                problems.append(f'duplicate recording {key}')
            seen.add(key)
            tot['recordings'] += 1
            tot['channel_files'] += len(r.get('channels', {}))
            tot['recordings_failed'] += int(r['status'] == 'failed')
            if r['issues']:
                tot['recordings_with_issues'] += 1
                issues[f"{r['subject']}/{r['recording']}"] = r['issues']
    ev = json.loads((Path(args.events_root) / 'events_summary.json').read_text())
    with_windows = set()
    for subject in SUBJECTS:
        part = json.loads((Path(args.events_root) / f'events_{subject}.json').read_text())
        with_windows |= {(subject, r) for r in part['recordings_with_windows']}
    if not with_windows <= seen:
        problems.append(f'event windows assigned to recordings that are not in the ledgers: {sorted(with_windows - seen)[:5]}')
    tot.update({k: ev['totals'][k] for k in ('event_files', 'empty_event_files', 'windows_left', 'windows_right', 'windows')})
    tot['with_windows'] = len(with_windows & seen)
    tot['without_windows'] = tot['recordings'] - tot['with_windows']
    checks = {k: {'got': tot[k], 'expected': v, 'equal': tot[k] == v} for k, v in EXPECTED.items()}
    report = {'schema': 'locohub.gt23_x01_summary/1', 'scientific_approval': False, 'roots': [str(r) for r in args.roots],
              'events_root': str(args.events_root), 'totals': tot, 'acceptance_counts': checks,
              'all_counts_equal': all(c['equal'] for c in checks.values()), 'problems': problems,
              'event_file_problems': ev['problems'],
              'recordings_with_issues_named': issues}
    with Path(args.out).open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    return 0 if report['all_counts_equal'] and not problems else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run')
    r.add_argument('--output-root', type=Path, required=True)
    r.add_argument('--subject', required=True)
    r.add_argument('--records', action='append')
    r.add_argument('--source', type=Path, default=SOURCE)
    s = sub.add_parser('spec')
    s.add_argument('--kind', choices=('run', 'audit'), required=True)
    s.add_argument('--job-id', required=True)
    s.add_argument('--script', required=True)
    s.add_argument('--subject', required=True)
    s.add_argument('--output-root', required=True)
    s.add_argument('--receipt', required=True)
    s.add_argument('--spec-out', required=True)
    s.add_argument('--batch-root')
    s.add_argument('--events-root')
    s.add_argument('--records', action='append')
    e = sub.add_parser('events')
    e.add_argument('--output-root', type=Path, required=True)
    e.add_argument('--source', type=Path, default=SOURCE)
    t = sub.add_parser('summary')
    t.add_argument('--out', type=Path, required=True)
    t.add_argument('--events-root', type=Path, required=True)
    t.add_argument('roots', nargs='+')
    args = p.parse_args(argv)
    return {'run': run, 'spec': make_spec, 'summary': summarize, 'events': events_all}[args.cmd](args)


if __name__ == '__main__':
    sys.exit(main())
