"""GT21-RB06 before/after audit of the left-leg treadmill stance fix (read-only; bounded reads, one recording at a time).
Compares the RB03 roots *_20261125 (before) with *_20261126 (after) for every participant: steps, ledgers, force-mask layers."""
import hashlib, json, resource, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq
ROOT = Path(__file__).resolve().parents[1]
B = ROOT / 'converted_datasets/reconversion_v2'
SUBJECTS = 'AB06 AB07 AB08 AB09 AB10 AB11 AB12 AB13 AB14 AB15 AB16 AB17 AB18 AB19 AB20 AB21 AB23 AB24 AB25 AB27 AB28 AB30'.split()
OLD, NEW = 'gt21_rb_segment_batch_{}_20261125', 'gt21_rb_segment_batch_{}_20261126'


def jl(p):
    return [json.loads(x) for x in Path(p).read_text().splitlines()]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def flag(s):
    a, m = s.get('stance_samples'), s.get('force_missing_stance_samples')
    return bool(a) and m / a >= 0.5


def main(out):
    res = {'per_subject': {}}
    tot = Counter()
    for sj in SUBJECTS:
        o, n = B / OLD.format(sj), B / NEW.format(sj)
        so, sn = {s['step_id']: s for s in jl(o / 'steps.jsonl')}, {s['step_id']: s for s in jl(n / 'steps.jsonl')}
        assert so.keys() == sn.keys()
        lo, ln = {(r['mode'], r['recording']): r for r in jl(o / 'ledger.jsonl')}, {(r['mode'], r['recording']): r for r in jl(n / 'ledger.jsonl')}
        assert lo.keys() == ln.keys()
        c = Counter(); frac = defaultdict(list)
        for sid, a in so.items():
            b = sn[sid]
            tm_left = a['mode'] == 'treadmill' and a['leg'] == 'left'
            if tm_left and 'stance_samples' in a:
                c['left_tm_steps'] += 1
                c['stance_samples_before'] += a.get('stance_samples') or 0
                c['masked_before'] += a.get('force_missing_stance_samples') or 0
                c['flag_before'] += flag(a); c['flag_after'] += flag(b)
                c['stance_none_after'] += (b.get('stance_samples') is None and 'stance_unavailable' in b)
                frac['left_before'].append(a['stance_samples'] / a['gc_samples'] if a.get('stance_samples') is not None else np.nan)
                allowed = {'force_check', 'force_missing_stance_samples', 'stance_samples', 'stance_unavailable'}
                diff = {k for k in set(a) | set(b) if a.get(k) != b.get(k)}
                c['left_tm_other_field_changed'] += bool(diff - allowed)
                fa, fb = dict(a['force_check']), dict(b['force_check'])
                fa.pop('toe_off_offset_ms', None); fb.pop('toe_off_offset_ms', None)
                c['left_tm_force_check_other_changed'] += fa != fb
            else:
                c['other_steps'] += 1
                if a['mode'] == 'treadmill':
                    c['right_tm_steps'] += 1
                    frac['right'].append(a['stance_samples'] / a['gc_samples'] if a.get('stance_samples') is not None else np.nan)
                c['other_steps_changed'] += a != b
        # ledgers and layers
        for k, ra in lo.items():
            rb = ln[k]
            ia, ib = dict(ra), dict(rb)
            ib.pop('stance_unavailable', None)
            if k[0] != 'treadmill':
                c['non_tm_ledger_changed'] += {x: y for x, y in ra.items() if x != 'peak_rss_mib_after'} != {x: y for x, y in rb.items() if x != 'peak_rss_mib_after'}
            else:
                ra2, rb2 = json.loads(json.dumps(ra)), json.loads(json.dumps(rb))
                ra2['force_mask'].pop('left', None) if 'force_mask' in ra2 else None
                rb2['force_mask'].pop('left', None) if 'force_mask' in rb2 else None
                for r in (ra2, rb2):
                    r.pop('stance_unavailable', None); r.pop('peak_rss_mib_after', None)
                c['tm_ledger_changed_beyond_left_mask'] += ra2 != rb2
            if 'force_mask_layer' in ra:
                pa_, pb_ = o / ra['force_mask_layer'], n / rb['force_mask_layer']
                if k[0] != 'treadmill':
                    c['non_tm_layers'] += 1
                    same = sha(pa_) == sha(pb_)
                    if not same:
                        same = pq.read_table(pa_).equals(pq.read_table(pb_))
                    c['non_tm_layers_changed'] += not same
                else:
                    ta, tb = pq.read_table(pa_), pq.read_table(pb_)
                    c['tm_layers'] += 1
                    c['tm_right_layer_changed'] += not ta.column('force_missing_right').equals(tb.column('force_missing_right'))
                    c['tm_time_changed'] += not ta.column('time_s').equals(tb.column('time_s'))
                    c['tm_left_masked_before'] += int(np.sum(ta.column('force_missing_left').to_numpy(zero_copy_only=False)))
                    c['tm_left_masked_after'] += int(np.sum(tb.column('force_missing_left').to_numpy(zero_copy_only=False)))
        res['per_subject'][sj] = {**c, 'left_stance_fraction_before_median': float(np.nanmedian(frac['left_before'])) if frac['left_before'] else None,
                                  'right_stance_fraction_median': float(np.nanmedian(frac['right'])) if frac['right'] else None}
        tot.update({k: v for k, v in c.items()})
        print(sj, dict(c), file=sys.stderr, flush=True)
    res['totals'] = dict(tot)
    res['peak_rss_mib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    Path(out).write_text(json.dumps(res, indent=1, sort_keys=True, default=float) + '\n')


if __name__ == '__main__':
    main(sys.argv[1])
