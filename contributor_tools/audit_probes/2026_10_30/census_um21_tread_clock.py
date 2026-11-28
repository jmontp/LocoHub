"""UM21-T02 review follow-up: task-interval clock and motion-duplicate census.

Bounded, read-only probe (AGENTS.md probe exception). Reads one UM21 treadmill
recording at a time from Streaming.mat, in the UM21-T01 scope order, and writes one
JSON report to a path that must not exist. Nothing under converted_datasets/ or
source folders is written.

Per recording:
- Belt-clock alignment with the reviewed audit's own rule
  (contributor_tools/audit_um21_tread_pilot.belt_clock_alignment): best lag between
  the cvel/cutPoints clock and the joint/marker clock, lag-0 error, best error, pass.
- Task-window decisions for every consecutive heel-strike pair with the source
  cutPoints as published, and with the cutPoints moved into joint frames by the
  measured lag (cut - lag). Counts of written strides and of changed decisions.
- sha256 of every dataset in jointAngles, jointForces, jointMoments, jointPowers,
  markers and forceplates (raw bytes, one dataset at a time) and of the event
  arrays (heel strikes, stride times, cutPoints, decoded task labels, newID), to
  find data repeated across recordings.
- Which input is missing when the alignment check cannot be evaluated: no cvel,
  or a missing heel/toe marker (the audit reports one combined reason).
"""
import os
for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'ARROW_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'
import argparse
import hashlib
import json
from pathlib import Path
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from contributor_tools.audit_um21_tread_pilot import (  # noqa: E402  reviewed audit rule, reused on purpose
    INCLINES, TOLERANCES, belt_clock_alignment, classify, matlab_text, set_address_space, sha256_file)

SCOPE = ROOT / 'docs/quality/audits/um21-t01-tread-release-scope.json'
GROUPS = ('jointAngles', 'jointForces', 'jointMoments', 'jointPowers', 'markers', 'forceplates')


def recording(handle, subject, condition):
    import numpy as np
    trial = handle[f'Streaming/{subject}/Tread/{condition}']
    events = trial['events']
    hs = {side: events[key][...].reshape(-1).astype(int) for side, key in (('left', 'LHS'), ('right', 'RHS'))}
    cuts = events['cutPoints'][...].astype(float)
    labels = [matlab_text(handle, r) for r in events['tasks'][...].reshape(-1)]
    cvel = events['VelProf/cvel'][...].reshape(-1).astype(float) if 'VelProf/cvel' in events else None
    markers = {n: trial[f'markers/{n}'][...].astype(float) for n in ('LHEE', 'LTOE', 'RHEE', 'RTOE')
               if f'markers/{n}' in trial}
    alignment = belt_clock_alignment(hs, markers, cvel, cuts, labels)
    missing = [m for m in ('no cvel' if cvel is None else None,
                           'missing heel/toe marker' if len(markers) < 4 else None) if m]
    alignment['not_evaluable_detail'] = missing if alignment['best_lag'] is None else []
    del markers
    hashes = {}
    for group in GROUPS:
        if group not in trial:
            continue
        for name in sorted(trial[group]):
            hashes[f'{group}/{name}'] = hashlib.sha256(np.ascontiguousarray(trial[group][name][...]).tobytes()).hexdigest()
    for name in ('LHS', 'RHS', 'LStrideTime', 'RStrideTime', 'cutPoints', 'newID'):
        if name in events:
            hashes[f'events/{name}'] = hashlib.sha256(np.ascontiguousarray(events[name][...]).tobytes()).hexdigest()
    hashes['events/tasks'] = hashlib.sha256('|'.join(labels).encode()).hexdigest()
    frames = trial['jointAngles/RHipAngles'].shape[1]
    incline = INCLINES[condition]
    lag = alignment['best_lag'] or 0
    shifted = cuts - lag
    pairs = [(s, int(a), int(b)) for s in ('left', 'right') for a, b in zip(hs[s][:-1], hs[s][1:])]
    as_published = {p: classify(p[1], p[2], cuts, labels, incline) for p in pairs}
    realigned = {p: classify(p[1], p[2], shifted, labels, incline) for p in pairs}
    def key(c):
        return c.get('label') or c.get('excluded')
    changed = sum(key(as_published[p]) != key(realigned[p]) for p in pairs)
    transition_written = sum(c.get('task') == 'transition' for c in as_published.values())
    transition_kept = sum(c.get('task') == 'transition' and key(c) == key(realigned[p]) for p, c in as_published.items())
    return {'subject': subject, 'condition': condition, 'joint_frames': int(frames),
            'cvel_samples': None if cvel is None else int(cvel.size), 'cut_points_max': float(cuts.max()),
            'alignment': alignment, 'pairs': len(pairs),
            'written_as_published': sum('excluded' not in c for c in as_published.values()),
            'written_realigned': sum('excluded' not in c for c in realigned.values()),
            'decisions_changed_by_realignment': changed,
            'transition_written_as_published': transition_written,
            'transition_unchanged_by_realignment': transition_kept,
            'events_sha256': hashlib.sha256(np.concatenate([hs['left'], [-1], hs['right']]).tobytes()).hexdigest(),
            'cut_points_sha256': hashlib.sha256(cuts.tobytes()).hexdigest(),
            'dataset_sha256': hashes,
            'group_sha256': {g: hashlib.sha256(''.join(f'{k}={v};' for k, v in hashes.items()
                                                        if k.startswith(g + '/')).encode()).hexdigest()
                             for g in GROUPS + ('events',)}}


def duplicates(records):
    """Recordings that share any byte-identical dataset, and per-group coverage for each such pair."""
    name_of = lambda r: f"{r['subject']}/{r['condition']}"  # noqa: E731
    groups = {}
    for g in GROUPS + ('events',):
        seen = {}
        for r in records:
            seen.setdefault(r['group_sha256'][g], []).append(name_of(r))
        groups[f'{g}_whole_group'] = [v for v in seen.values() if len(v) > 1]
    owners = {}
    for r in records:
        for name, digest in r['dataset_sha256'].items():
            if not name.startswith('events/'):  # small event arrays can coincide by chance; compared below
                owners.setdefault((name, digest), []).append(name_of(r))
    pairs = sorted({tuple(sorted(v[i:i + 2])) for v in owners.values() if len(v) > 1 for i in range(len(v) - 1)})
    groups['recording_pairs_sharing_any_signal_dataset'] = [list(p) for p in pairs]
    by_name = {name_of(r): r['dataset_sha256'] for r in records}
    coverage = {}
    for a, b in pairs:
        per_group = {}
        for name in sorted(set(by_name[a]) | set(by_name[b])):
            g, short = name.split('/', 1)
            item = per_group.setdefault(g, {'identical': 0, 'of': 0, 'differs': []})
            item['of'] += 1
            if by_name[a].get(name) == by_name[b].get(name):
                item['identical'] += 1
            else:
                item['differs'].append(short)
        coverage[f'{a} = {b}'] = per_group
    groups['pair_coverage'] = coverage
    return groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'contributor_tools/conversion_scripts/Umich_2021/Streaming.mat')
    parser.add_argument('--output', type=Path, required=True, help='new JSON file')
    parser.add_argument('--max-rss-mib', type=float, default=300.0)
    args = parser.parse_args()
    set_address_space(768)
    os.nice(max(0, 19 - os.nice(0)))
    import h5py
    started = time.time()
    scope = json.loads(SCOPE.read_text())
    plan = [(r['subject'], r['condition'], r['observations'], r['excluded_pairs']) for r in scope['records']]
    stat = args.source.stat()
    records = []
    with h5py.File(args.source, 'r', rdcc_nbytes=1024**2) as handle:
        for subject, condition, observations, excluded in plan:
            r = recording(handle, subject, condition)
            r['t01_observations'], r['t01_excluded_pairs'] = observations, excluded
            r['matches_t01_counts'] = (r['written_as_published'] == observations
                                       and r['pairs'] - r['written_as_published'] == excluded)
            r['peak_rss_mib_after'] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
            records.append(r)
            print(json.dumps({'record': f'{subject}/{condition}', 'lag': r['alignment']['best_lag'],
                              'pass': r['alignment']['passed'], 'rss': r['peak_rss_mib_after']}), flush=True)
            if r['peak_rss_mib_after'] > args.max_rss_mib:
                raise SystemExit(f'peak RSS above {args.max_rss_mib} MiB; stopped')
    if (args.source.stat().st_size, args.source.stat().st_mtime_ns) != (stat.st_size, stat.st_mtime_ns):
        raise SystemExit('source changed during the census')
    aligned = [r for r in records if r['alignment']['passed']]
    misaligned = [r for r in records if not r['alignment']['passed']]
    totals = {
        'recordings': len(records), 'aligned': len(aligned), 'misaligned': len(misaligned),
        'strides_as_published_all': sum(r['written_as_published'] for r in records),
        'strides_as_published_aligned_only': sum(r['written_as_published'] for r in aligned),
        'strides_misaligned_realigned_aligned_as_published':
            sum(r['written_as_published'] for r in aligned) + sum(r['written_realigned'] for r in misaligned),
        'decisions_changed_in_misaligned_by_realignment': sum(r['decisions_changed_by_realignment'] for r in misaligned),
        'pairs_in_misaligned': sum(r['pairs'] for r in misaligned),
        'all_counts_match_t01': all(r['matches_t01_counts'] for r in records)}
    report = {
        'task_id': 'UM21-T02', 'part': 'task-interval clock and motion-duplicate census (review R1 follow-up)',
        'status': 'census_complete_unreviewed', 'scientific_approval': False,
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'probe': {'path': str(Path(__file__).relative_to(ROOT)), 'sha256': sha256_file(Path(__file__))},
        'audit_rule': {'path': 'contributor_tools/audit_um21_tread_pilot.py',
                       'sha256': sha256_file(ROOT / 'contributor_tools/audit_um21_tread_pilot.py'),
                       'tolerances': {k: v for k, v in TOLERANCES.items() if k.startswith('belt_clock')}},
        'inputs': {'scope': {'path': str(SCOPE.relative_to(ROOT)), 'sha256': sha256_file(SCOPE)},
                   'source': {'path': str(args.source), 'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns,
                              'sha256_recorded': scope['source']['streaming_sha256_recorded'],
                              'sha256_note': 'Recorded by earlier receipts; size and mtime re-checked before and after, bytes not rehashed.'}},
        'realignment_rule_for_counts': 'cutPoints moved into joint frames as cut - best_lag (cvel index = joint frame + lag); counts only, nothing is converted.',
        'totals': totals,
        'misaligned': [{'record': f"{r['subject']}/{r['condition']}", 'best_lag': r['alignment']['best_lag'],
                        'err_lag0_m_s': r['alignment']['err_lag0_m_s'], 'err_best_m_s': r['alignment']['err_best_m_s'],
                        'reason': r['alignment']['reason'], 'not_evaluable_detail': r['alignment']['not_evaluable_detail'], 'decisions_changed': r['decisions_changed_by_realignment'],
                        'pairs': r['pairs']} for r in misaligned],
        'duplicates': duplicates(records),
        'records': [{k: v for k, v in r.items() if k != 'dataset_sha256'} for r in records],
        'dataset_sha256_by_record': {f"{r['subject']}/{r['condition']}": r['dataset_sha256'] for r in records},
        'resources': {'peak_rss_mib': round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
                      'wall_seconds': round(time.time() - started, 1), 'rlimit_as_bytes': list(resource.getrlimit(resource.RLIMIT_AS))},
        'limitations': ['Belt speed from heel/toe markers is an estimate; aligned controls show +10 to +17 frame lags, '
                        'absorbed by the +-50 frame tolerance but not calibrated.',
                        'Duplicate detection is exact-byte only; near-copies are not detected.',
                        'Counts under re-alignment use one global lag per recording; drift within a recording is not tested.']}
    text = json.dumps(report, indent=1, allow_nan=False) + '\n'
    with open(args.output, 'x') as stream:
        stream.write(text)
    print(json.dumps({'totals': totals, 'peak_rss_mib': report['resources']['peak_rss_mib']}))


if __name__ == '__main__':
    main()
