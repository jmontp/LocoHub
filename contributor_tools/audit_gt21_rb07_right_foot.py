"""GT21-RB07 read-only check: the left-treadmill toe-off rule (first sample after the heel strike where the foot's own belt
vertical force is below 20 N) applied to the RIGHT foot, whose source toe-off is a real measurement, compared with the source
right toe-off. Reads one recording at a time (two gait tables, five pass-table columns). Writes one JSON, no data root.
No threshold tuning. Usage: audit_gt21_rb07_right_foot.py OUT.json [SUBJECT ...]"""
import json
import resource
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools import gt21_numeric_source as src  # noqa: E402
from contributor_tools import gt21_rb_segment as sg  # noqa: E402
from contributor_tools import run_gt21_rb_segment as R  # noqa: E402

DT_MS = 5.0


def summarize(err_ms):
    a = np.asarray(err_ms, float)
    if not a.size:
        return {'strides': 0}
    ab = np.abs(a)
    return {'strides': int(a.size), 'median_error_ms': float(np.median(a)), 'median_abs_error_ms': float(np.median(ab)),
            'p95_abs_error_ms': float(np.percentile(ab, 95)), 'worst_abs_error_ms': float(ab.max()),
            'worst_error_ms': float(a[int(np.argmax(ab))]), 'median_abs_error_samples': float(np.median(ab) / DT_MS),
            'worst_abs_error_samples': float(ab.max() / DT_MS), 'exact_match_strides': int((ab < 1e-6).sum())}


def main(out, subjects):
    inv = R.load_inventory()
    subjects = subjects or sorted({s for (s, m, r) in inv})
    result = {'rule': sg.LEFT_TOE_OFF_RULE, 'threshold_N': sg.FORCE_MASK_N, 'per_participant': {}}
    allerr = []
    for subj in subjects:
        root, rows = R.load_pass_ledger(subj)
        err, no_to, no_rule, n = [], 0, 0, 0
        for (s, m, r), row in sorted(inv.items()):
            if s != subj or m != 'treadmill':
                continue
            pe = rows.get((m, r))
            tab = R.read_pass_table(root, pe)
            if tab is None:
                continue
            bw = float(pe['body_weight_N'])
            g = src.read_numeric_table(R.ROOTS[row['source']] / s / row['session'] / m / 'gcRight' / f'{r}.mat')
            h, pct = np.asarray(g['Header'], float), np.asarray(g['HeelStrike'], float)
            toe, rs = sg.event_times(h, g['ToeOff']), sg.resets(pct)
            t, v = tab['time_s'], tab['grf_vertical_right_BW'] * bw
            for k in range(len(rs) - 1):
                t0, t1 = float(h[rs[k]]), float(h[rs[k + 1]])
                to = toe[(toe > t0) & (toe < t1)]
                if not to.size:
                    no_to += 1
                    continue
                n += 1
                i = sg.toe_off_from_force(t, v, t0, t1)
                if i is None:
                    no_rule += 1
                    continue
                err.append((t[i] - to[0]) * 1000.0)
        result['per_participant'][subj] = {**summarize(err), 'strides_with_source_toe_off': n,
                                          'rule_found_no_sample': no_rule, 'strides_without_source_toe_off_skipped': no_to}
        allerr += err
    result['all'] = summarize(allerr)
    result['peak_rss_mib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    with open(out, 'x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
