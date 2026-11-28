"""Bounded census of original GT21 gait-phase tables, including unexported cycles."""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
from collections import Counter
import json
from pathlib import Path
import resource
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from contributor_tools.gt21_numeric_source import read_numeric_table
from contributor_tools.reconvert_recording import digest
from check_gt21_events_and_terrain import phase_issues


def inspect_phases(clock, phase):
    import numpy as np
    if clock.shape != phase.shape:
        raise ValueError('Phase and clock lengths differ')
    resets = np.flatnonzero((phase[1:] == 0) & (phase[:-1] > 0)) + 1
    issues = []
    for start, end in zip(resets[:-1], resets[1:]):
        found = phase_issues(phase, int(start), int(end))
        if found:
            issues.append({'start_s': float(clock[start]), 'end_s': float(clock[end]),
                           'start_index': int(start), 'end_index': int(end), 'issues': found})
    return {'samples': len(clock), 'resets': len(resets), 'pairs': max(0, len(resets)-1),
            'nonfinite_samples': int(np.count_nonzero(~np.isfinite(phase))),
            'out_of_range_samples': int(np.count_nonzero((phase < 0) | (phase > 100))),
            'cycle_issues': issues}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (768*1024**2, 768*1024**2))
    os.nice(max(0, 19-os.nice(0)))
    source = ROOT/'contributor_tools/conversion_scripts/Gtech_2021/CAMARGO_ET_AL_J_BIOMECH_DATASET'
    records = json.loads(args.inventory.read_text())['recordings']
    args.output_root.mkdir(parents=True, exist_ok=False)
    counts = Counter()
    status = {'status': 'running', 'pid': os.getpid(), 'scientific_approval': False,
              'expected_tables': 2*len(records), 'inventory_sha256': digest(args.inventory),
              'code_sha256': {str(p.relative_to(ROOT)): digest(p) for p in
                 [Path(__file__), Path(__file__).with_name('check_gt21_events_and_terrain.py'),
                  ROOT/'contributor_tools/gt21_numeric_source.py']},
              'limitations': ['Checks source phase annotations, not physical heel contact timing',
                  'Source findings do not prove affected cycles are exported',
                  'No event pair can be inferred before the first or after the last observed reset']}
    def save():
        status['counts'] = dict(counts)
        status['peak_rss_kib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        temp = args.output_root/'status.tmp'
        temp.write_text(json.dumps(status, indent=2)+'\n')
        temp.replace(args.output_root/'status.json')
    save()
    try:
        with (args.output_root/'tables.jsonl').open('x') as ledger:
            for record in records:
                for side in ('left', 'right'):
                    path = source/record['subject']/record['date']/record['mode']/('gc'+side.capitalize())/record['recording']
                    result = {'recording': record, 'side': side, 'source_path': str(path)}
                    try:
                        before = digest(path)
                        table = read_numeric_table(path)
                        result.update(inspect_phases(table['Header'], table['HeelStrike']))
                        assert digest(path) == before, 'Source changed while reading'
                        result['source_sha256'] = before
                        counts['tables_read'] += 1
                        for key in ('samples', 'resets', 'pairs', 'nonfinite_samples', 'out_of_range_samples'):
                            counts[key] += result[key]
                        counts['pairs_with_issues'] += len(result['cycle_issues'])
                        counts['tables_without_pairs'] += int(result['pairs'] == 0)
                        counts['tables_with_findings'] += int(bool(result['cycle_issues'] or result['nonfinite_samples'] or result['out_of_range_samples']))
                    except (ValueError, KeyError, OSError, AssertionError, MemoryError) as error:
                        counts['unreadable_tables'] += 1
                        result['error'] = str(error)
                    ledger.write(json.dumps(result, allow_nan=False)+'\n')
                    ledger.flush()
                    counts['tables_attempted'] += 1
                save()
        status['status'] = ('source_phase_census_incomplete' if counts['unreadable_tables'] else
                            'source_phase_findings_require_review' if counts['tables_with_findings'] else
                            'source_phase_census_checked_unreviewed')
        status['ledger_sha256'] = digest(args.output_root/'tables.jsonl')
    except Exception as error:
        status.update(status='failed', reason=str(error))
        raise
    finally:
        save()
    print(json.dumps(status))
    if status['status'] != 'source_phase_census_checked_unreviewed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
