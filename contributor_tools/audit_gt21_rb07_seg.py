"""GT21-RB07 before/after audit of the RB03 roots (read-only; bounded reads, one recording at a time).
before = gt21_rb_segment_batch_<ID>_20261126 (RB06), after = gt21_rb07_segment_<ID>. Only left treadmill toe-off, stance fields,
the left force mask and the ledger's left mask/stance notes may change. Reports left vs right treadmill stance fractions and the
left strides still unavailable per participant."""
import json
import resource
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / 'converted_datasets/reconversion_v2'
SUBJECTS = 'AB06 AB07 AB08 AB09 AB10 AB11 AB12 AB13 AB14 AB15 AB16 AB17 AB18 AB19 AB20 AB21 AB23 AB24 AB25 AB27 AB28 AB30'.split()
OLD, NEW = 'gt21_rb_segment_batch_{}_20261126', 'gt21_rb07_segment_{}'
STEP_ALLOWED = {'stance_samples', 'force_missing_stance_samples', 'stance_unavailable', 'toe_off_s', 'toe_off_rule'}
LEDGER_ALLOWED = {'stance_unavailable', 'left_toe_off_rebuilt', 'left_toe_off_copied_from_right', 'peak_rss_mib_after'}


def jl(p):
    return [json.loads(x) for x in Path(p).read_text().splitlines()]


def med(x):
    x = [v for v in x if v is not None and np.isfinite(v)]
    return float(np.median(x)) if x else None


def main(out, subjects):
    res = {'per_subject': {}}
    for sj in subjects or SUBJECTS:
        o, n = B / OLD.format(sj), B / NEW.format(sj)
        so, sn = {s['step_id']: s for s in jl(o / 'steps.jsonl')}, {s['step_id']: s for s in jl(n / 'steps.jsonl')}
        c = Counter()
        c['same_step_ids'] = so.keys() == sn.keys()
        fl, fr, tmin = [], [], []
        for sid, a in so.items():
            b = sn[sid]
            tl = a['mode'] == 'treadmill' and a['leg'] == 'left'
            if tl:
                c['left_tm_steps'] += 1
                diff = {k for k in set(a) | set(b) if a.get(k) != b.get(k)}
                c['left_tm_unexpected_field_change'] += bool(diff - STEP_ALLOWED)
                if b.get('stance_samples') is None:
                    c['left_tm_unavailable_after'] += 1
                    c['left_tm_unavailable_reasons:' + str(b.get('stance_unavailable'))] += 1
                else:
                    c['left_tm_stance_available_after'] += 1
                    fl.append(b['stance_samples'] / b['gc_samples'])
                    tmin.append(b['stance_samples'])
                    c['left_tm_stance_le_5_samples'] += b['stance_samples'] <= 5
                    c['left_tm_masked_after'] += b['force_missing_stance_samples'] or 0
                    c['left_tm_incomplete_flag_after'] += (b['force_missing_stance_samples'] or 0) / b['stance_samples'] >= 0.5
            else:
                c['other_steps'] += 1
                c['other_steps_changed'] += a != b
                if a['mode'] == 'treadmill' and a.get('stance_samples') is not None:
                    fr.append(a['stance_samples'] / a['gc_samples'])
        lo = {(r['mode'], r['recording']): r for r in jl(o / 'ledger.jsonl')}
        ln = {(r['mode'], r['recording']): r for r in jl(n / 'ledger.jsonl')}
        c['same_ledger_keys'] = lo.keys() == ln.keys()
        for k, ra in lo.items():
            rb = ln[k]
            if k[0] != 'treadmill':
                c['non_tm_ledger_changed'] += {x: y for x, y in ra.items() if x != 'peak_rss_mib_after'} != \
                    {x: y for x, y in rb.items() if x != 'peak_rss_mib_after'}
            else:
                ra2, rb2 = json.loads(json.dumps(ra)), json.loads(json.dumps(rb))
                for r in (ra2, rb2):
                    for x in LEDGER_ALLOWED:
                        r.pop(x, None)
                    if 'force_mask' in r:
                        r['force_mask'].pop('left', None)
                c['tm_ledger_changed_beyond_left'] += ra2 != rb2
                if rb.get('left_toe_off_rebuilt'):
                    c['left_rebuilt'] += rb['left_toe_off_rebuilt']['rebuilt']
                    c['left_unavailable_strides'] += rb['left_toe_off_rebuilt']['unavailable']
            if 'force_mask_layer' in ra:
                ta, tb = pq.read_table(o / ra['force_mask_layer']), pq.read_table(n / rb['force_mask_layer'])
                c['layers'] += 1
                c['time_clock_changed'] += not ta.column('time_s').equals(tb.column('time_s'))
                c['right_mask_changed'] += not ta.column('force_missing_right').equals(tb.column('force_missing_right'))
                if k[0] != 'treadmill':
                    c['non_tm_layers_changed'] += not ta.equals(tb)
                else:
                    c['left_mask_true_samples_before'] += int(np.sum(ta.column('force_missing_left').to_numpy()))
                    c['left_mask_true_samples_after'] += int(np.sum(tb.column('force_missing_left').to_numpy()))
        d = dict(c)
        d['left_treadmill_stance_fraction_median'] = med(fl)
        d['right_treadmill_stance_fraction_median'] = med(fr)
        d['left_stance_samples_min'] = int(min(tmin)) if tmin else None
        res['per_subject'][sj] = d
        print(sj, d, file=sys.stderr, flush=True)
    res['peak_rss_mib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    Path(out).write_text(json.dumps(res, indent=2, sort_keys=True, default=bool) + '\n')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
