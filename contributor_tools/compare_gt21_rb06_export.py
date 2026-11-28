"""GT21-RB06: compare RB05 export roots before (r1) and after the left-treadmill stance fix, per participant, streamed.
Strict: every non-treadmill row and every column except the left leg's force columns of treadmill observations is bit equal.
Reports exactly which columns differ, how many observations, and the incomplete_stance_force counts."""
import json, resource, sys
from collections import Counter
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq
ROOT = Path(__file__).resolve().parents[1]
B = ROOT / 'converted_datasets/reconversion_v2'
FORCE = ('grf_vertical', 'grf_anterior', 'grf_lateral')


def jl(p):
    return [json.loads(x) for x in Path(p).read_text().splitlines()]


def left_force_cols(names, ref_side, kind):
    """Force columns that belong to the left foot of one row."""
    out = set()
    for n in names:
        if not n.startswith(FORCE):
            continue
        if kind == 'time':
            if '_left_' in n:
                out.add(n)
        elif ('_ipsi_' in n) == (ref_side == 'left'):
            out.add(n)
    return out


def eq(a, b):
    if a.dtype.kind == 'f':
        return np.array_equal(a, b, equal_nan=True)
    return np.array_equal(a, b)


def compare_parquet(old, new, kind, obs_info, res):
    po, pn = pq.ParquetFile(str(old)), pq.ParquetFile(str(new))
    assert po.metadata.num_rows == pn.metadata.num_rows and po.schema_arrow.equals(pn.schema_arrow)
    names = po.schema_arrow.names
    for bo, bn in zip(po.iter_batches(batch_size=3000), pn.iter_batches(batch_size=3000)):
        to, tn = bo.to_pydict(), bn.to_pydict()
        oid = np.array(to['observation_id'])
        for o in sorted(set(oid)):
            m = oid == o
            mode, ref = obs_info[o]
            allowed = left_force_cols(names, ref, kind) if mode == 'treadmill' else set()
            for c in names:
                a, b = np.array(to[c], dtype=object if po.schema_arrow.field(c).type == 'string' or c == 'task_info' else float)[m], \
                    np.array(tn[c], dtype=object if po.schema_arrow.field(c).type == 'string' or c == 'task_info' else float)[m]
                if c == 'task_info':
                    for x, y in zip(a, b):
                        if x != y:
                            dx, dy = json.loads(x), json.loads(y)
                            res['task_info_keys_changed'].update(k for k in set(dx) | set(dy) if dx.get(k) != dy.get(k))
                            res['task_info_rows_changed'] += 1
                    continue
                if not eq(a, b):
                    res[f'{kind}_cols_changed'][c] += 1
                    if c not in allowed:
                        res[f'{kind}_UNEXPECTED'][f'{mode}:{ref}:{c}'] += 1
                    else:
                        res['left_force_obs_changed'] += 0


def main(out):
    tot = {'subjects': {}}
    for sj in 'AB06 AB07 AB08 AB09 AB10 AB11 AB12 AB13 AB14 AB15 AB16 AB17 AB18 AB19 AB20 AB21 AB23 AB24 AB25 AB27 AB28 AB30'.split():
        o, n = B / f'gt21_rb05_export_{sj}_r1', B / f'gt21_rb06_export_{sj}_r2'
        oo, on = {r['observation_id']: r for r in jl(o / 'observations.jsonl')}, {r['observation_id']: r for r in jl(n / 'observations.jsonl')}
        res = {'obs_old': len(oo), 'obs_new': len(on), 'same_obs_ids': oo.keys() == on.keys(),
               'exclusions_equal': jl(o / 'exclusions.jsonl') == jl(n / 'exclusions.jsonl'),
               'task_info_keys_changed': Counter(), 'task_info_rows_changed': 0, 'phase_cols_changed': Counter(), 'phase_UNEXPECTED': Counter(),
               'time_cols_changed': Counter(), 'time_UNEXPECTED': Counter(), 'left_force_obs_changed': 0}
        c = Counter()
        for k, a in oo.items():
            b = on[k]
            tl = a['mode'] == 'treadmill' and a['reference_side'] == 'left'
            diff = {x for x in set(a) | set(b) if a.get(x) != b.get(x)}
            if diff:
                c[('treadmill_left_ref' if tl else a['mode'] + '_' + a['reference_side']) + ':' + ','.join(sorted(diff))] += 1
            c['flag_before'] += 'incomplete_stance_force' in a.get('flags', []) and a['mode'] == 'treadmill' and a['reference_side'] == 'left'
            c['flag_after'] += 'incomplete_stance_force' in b.get('flags', []) and b['mode'] == 'treadmill' and b['reference_side'] == 'left'
            c['flag_before_all'] += 'incomplete_stance_force' in a.get('flags', [])
            c['flag_after_all'] += 'incomplete_stance_force' in b.get('flags', [])
        res['obs_record_diffs'] = dict(c)
        info = {k: (a['mode'], a['reference_side']) for k, a in oo.items()}
        compare_parquet(o / 'phase.parquet', n / 'phase.parquet', 'phase', info, res)
        compare_parquet(o / 'time.parquet', n / 'time.parquet', 'time', {k: (a['mode'], 'left') for k, a in oo.items()} if False else info, res)
        for k in ('task_info_keys_changed', 'phase_cols_changed', 'phase_UNEXPECTED', 'time_cols_changed', 'time_UNEXPECTED'):
            res[k] = dict(res[k]) if not isinstance(res[k], set) else sorted(res[k])
        tot['subjects'][sj] = res
        print(sj, 'unexpected', res['phase_UNEXPECTED'], res['time_UNEXPECTED'], res['obs_record_diffs'], file=sys.stderr, flush=True)
    tot['peak_rss_mib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    Path(out).write_text(json.dumps(tot, indent=1, sort_keys=True, default=list) + '\n')


if __name__ == '__main__':
    main(sys.argv[1])
