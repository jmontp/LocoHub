"""GT21-RB07 read-only list of left treadmill strides with a rebuilt stance of 5 samples or fewer, or no stance (no sub-20 N
sample), with the left belt vertical force (N) at the heel strike sample and the next samples. One recording at a time.
Usage: audit_gt21_rb07_short_stance.py OUT.json"""
import json
import resource
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools import run_gt21_rb_segment as R  # noqa: E402

SUBJECTS = 'AB06 AB07 AB08 AB09 AB10 AB11 AB12 AB13 AB14 AB15 AB16 AB17 AB18 AB19 AB20 AB21 AB23 AB24 AB25 AB27 AB28 AB30'.split()


def main(out):
    res = {}
    for sj in SUBJECTS:
        root = ROOT / f'converted_datasets/reconversion_v2/gt21_rb07_segment_{sj}'
        steps = [json.loads(x) for x in (root / 'steps.jsonl').read_text().splitlines()]
        sel = [s for s in steps if s['mode'] == 'treadmill' and s['leg'] == 'left' and 'stance_samples' in s
               and (s['stance_samples'] is None or s['stance_samples'] <= 5)]
        if not sel:
            continue
        prow_root, prows = R.load_pass_ledger(sj)
        out_rows = []
        for s in sel:
            pe = prows[(s['mode'], s['recording'])]
            tab = R.read_pass_table(prow_root, pe)
            bw = float(pe['body_weight_N'])
            t, v = tab['time_s'], tab['grf_vertical_left_BW'] * bw
            i0 = int(np.searchsorted(t, s['start_s'] - 1e-9))
            i1 = int(np.searchsorted(t, s['end_s'] + 1e-9, side='right'))
            seg = v[i0:i1]
            out_rows.append({'step_id': s['step_id'], 'stance_samples': s['stance_samples'], 'stance_unavailable': s.get('stance_unavailable'),
                             'force_at_heel_strike_N': float(v[i0]), 'force_next_samples_N': [round(float(x), 1) for x in v[i0 + 1:i0 + 7]],
                             'stride_max_force_N': float(np.nanmax(seg)) if np.isfinite(seg).any() else None,
                             'stride_samples_below_20N': int(np.sum(seg < 20)), 'stride_samples': int(len(seg))})
            del tab
        res[sj] = out_rows
    res['peak_rss_mib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    with open(out, 'x') as f:
        json.dump(res, f, indent=2)
        f.write('\n')


if __name__ == '__main__':
    main(sys.argv[1])
