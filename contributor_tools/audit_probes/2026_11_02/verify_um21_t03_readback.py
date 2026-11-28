"""UM21-T03 verifier part 2: independent full readback of the converted treadmill phase files.

Does not import the producer or audit code. Outputs are enumerated from the seven launcher
receipts (output_root) and the scope files, never by glob. One record at a time; source arrays
for one record (about 12 MiB) are held and freed before the next record.

Frame base: ledger frames are source heel-strike values (MATLAB 1-based); time = (frame-1)/100 s; array index = frame-1.
Per record: 150 rows per observation with phase 0..100 inclusive; ledger/side/clock/ID agreement;
source heel-strike events vs ledger pairs; no observation for an excluded pair; exact component
column set (84); values of a seeded random sample of observations vs source frames.
"""
import argparse, gc, hashlib, json, os, random, resource, sys, time
from pathlib import Path

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1'); os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
AUD = ROOT / 'docs/quality/audits'
JOBS = [('batch0', 'um21-t03-batch0', 'um21-t03-scope.json', 0), ('batch1', 'um21-t03-batch1', 'um21-t03-scope.json', 1)] + \
       [(f'v2-batch{b}', f'um21-t03-v2-batch{b}', 'um21-t03-scope-v2.json', b) for b in range(2, 7)]
GROUPS = [('jointAngles', 'joint_angle', 'deg'), ('jointForces', 'joint_force', 'N_kg'),
          ('jointMoments', 'joint_moment', 'Nm_kg'), ('jointPowers', 'joint_power', 'W_kg')]


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def rss_mib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def plan(only):
    out = []
    for name, stem, scope_name, batch in JOBS:
        rec = json.loads((AUD / f'{stem}-launcher-receipt.json').read_text())
        scope = json.loads((AUD / scope_name).read_text())
        kept = {k['record']: k for k in scope['kept']}
        for r in scope['batches'][batch]:
            if only and r not in only:
                continue
            out.append({'job': name, 'record': r, 'root': Path(rec['spec']['output_root']), 'scope': kept[r],
                        'bindings': rec['spec']['bindings']})
    return out


def check_record(item, handle, seed, nsample, res):
    import pyarrow.parquet as pq
    r = item['record']; sub, cond = r.split('/')
    fails = []
    def fail(msg): fails.append(msg)
    folder = item['root'] / 'components' / sub / cond
    rec_id = f'um21:Streaming/{sub}/Tread/{cond}'
    # ledger from the source ledger bound by the job
    led_path = folder / 'candidate_ledger.jsonl'
    bound = [v for k, v in item['bindings'].items() if k.endswith(f'/{sub}/{cond}/candidate_ledger.jsonl')]
    if len(bound) != 1 or sha(led_path) != bound[0]:
        fail('ledger hash differs from bound baseline ledger')
    ledger = [json.loads(l) for l in led_path.read_text().splitlines() if l.strip()]
    written = [l for l in ledger if 'observation_id' in l]
    excluded = [l for l in ledger if 'excluded' in l]
    if len(written) + len(excluded) != len(ledger) or len(written) != item['scope']['observations'] or len(excluded) != item['scope']['excluded_pairs']:
        fail(f'ledger counts written {len(written)} excluded {len(excluded)} vs scope {item["scope"]}')
    if any(l['observation_id'] != f'{rec_id}:{l["side"]}:frames:{l["start"]}:{l["end"]}' for l in written):
        fail('ledger observation id not built from side/start/end')
    wkeys = {(l['side'], l['start'], l['end']) for l in written}
    xkeys = {(l['side'], l['start'], l['end']) for l in excluded}
    if wkeys & xkeys or len(wkeys) != len(written) or len(xkeys) != len(excluded):
        fail('ledger written/excluded pairs overlap or repeat')
    # source events vs ledger pairs (every consecutive heel-strike pair of each side accounted once)
    trial = handle[f'Streaming/{sub}/Tread/{cond}']
    ev = trial['events']
    offset = None
    for side, key in (('left', 'LHS'), ('right', 'RHS')):
        hs = np.asarray(ev[key]).reshape(-1)
        pairs = {(int(a), int(b)) for a, b in zip(hs[:-1], hs[1:])}
        mine = {(l['start'], l['end']) for l in ledger if l['side'] == side}
        if len(mine) != len([l for l in ledger if l['side'] == side]):
            fail(f'{side} ledger repeats a pair')
        found = [o for o in (0, 1) if {(a - o, b - o) for a, b in pairs} == mine]
        if not found:
            fail(f'{side} ledger pairs are not the consecutive source heel strikes')
        else:
            offset = found[0] if offset is None or offset == found[0] else -1
    if offset == -1:
        fail('inconsistent heel-strike frame offset between sides')
    res['hs_offset_frames'] = offset
    # expected components from source structure
    arrays, expected_cols, mapping = {}, [], {}
    nframes = None
    for g, kind, unit in GROUPS:
        for name in sorted(trial[g].keys()):
            ds = trial[g][name]
            if ds.shape[0] != 3:
                fail(f'{g}/{name} shape {ds.shape}')
            nframes = ds.shape[1] if nframes is None else nframes
            if ds.shape[1] != nframes: fail('frame count differs between variables')
            arrays[(g, name)] = np.asarray(ds[:, :])
            for c in range(ds.shape[0]):
                col = f'source_{kind}_{name.lower()}_component_{c}_{unit}'
                expected_cols.append(col); mapping[col] = (g, name, c)
    if len(expected_cols) != 84: fail(f'{len(expected_cols)} source components')
    sc = json.loads((folder / 'source_columns.json').read_text())
    if {k: (v['group'], v['variable'], v['matlab_component_1based'] - 1) for k, v in sc.items()} != mapping:
        fail('source_columns.json mapping differs from source structure')
    pf = pq.ParquetFile(folder / 'phase.parquet')
    names = pf.schema_arrow.names
    if sorted(c for c in names if c.startswith('source_joint_')) != sorted(expected_cols):
        fail('source component columns differ from source structure')
    n_obs = pf.metadata.num_rows // 150
    if pf.metadata.num_rows != 150 * len(written):
        fail(f'rows {pf.metadata.num_rows} != 150 x {len(written)}')
    rng = random.Random(f'{seed}:{r}')
    sample = set(rng.sample(range(len(written)), min(nsample, len(written))))
    grid = np.linspace(0., 100., 150)
    ids, compared, max_err, bad_vals, finite_cmp, nan_cmp = [], 0, 0., 0, 0, 0
    reading = ['subject', 'source_recording_id', 'observation_id', 'reference_side', 'observation_type', 'phase_ipsi',
               'source_start_time_s', 'source_end_time_s'] + expected_cols
    idx = 0
    for batch in pf.iter_batches(batch_size=150, columns=reading, use_threads=False):
        d = batch.to_pydict() if False else None
        t = batch
        if t.num_rows != 150:
            fail(f'batch {idx} has {t.num_rows} rows'); idx += 1; continue
        oid = t.column('observation_id').to_pylist()
        if len(set(oid)) != 1:
            fail(f'batch {idx} spans observation ids'); idx += 1; continue
        oid = oid[0]; ids.append(oid)
        ph = t.column('phase_ipsi').to_numpy()
        if ph[0] != 0. or ph[-1] != 100. or not np.allclose(ph, grid, rtol=0, atol=1e-9) or not (np.diff(ph) > 0).all():
            fail(f'{oid}: phase grid')
        led = written[idx] if idx < len(written) else None
        if led is None or oid != led['observation_id']:
            fail(f'obs {idx} id/order differs from ledger'); idx += 1; continue
        side = led['side']
        s0 = t.column('source_start_time_s').to_numpy(); s1 = t.column('source_end_time_s').to_numpy()
        if not (np.all(s0 == s0[0]) and np.all(s1 == s1[0]) and abs(s0[0] - (led['start'] - 1) / 100) < 1e-9 and abs(s1[0] - (led['end'] - 1) / 100) < 1e-9):
            fail(f'{oid}: event times differ from ledger')
        if set(t.column('reference_side').to_pylist()) != {side} or set(t.column('source_recording_id').to_pylist()) != {rec_id} \
                or set(t.column('subject').to_pylist()) != {f'UM21_{sub}'} or set(t.column('observation_type').to_pylist()) != {'individual_cycle'}:
            fail(f'{oid}: side/recording/subject/type')
        if idx in sample:
            a, b = led['start'] - 1, led['end'] - 1  # ledger frames are MATLAB 1-based heel-strike frames
            if not (0 <= a < b < nframes): fail(f'{oid}: frames outside source')
            else:
                clock = np.arange(a, b + 1, dtype=float); target = np.linspace(a, b, 150)
                for col in expected_cols:
                    g, name, c = mapping[col]
                    exp = np.interp(target, clock, arrays[(g, name)][c, a:b + 1])
                    act = t.column(col).to_numpy(zero_copy_only=False)
                    if np.isnan(exp).tolist() != np.isnan(act).tolist():
                        bad_vals += 1; fail(f'{oid}: {col} missing-value mask differs'); continue
                    ok = np.isfinite(exp)
                    nan_cmp += int((~ok).sum()); finite_cmp += int(ok.sum())
                    if ok.any():
                        e = float(np.max(np.abs(act[ok] - exp[ok]))); max_err = max(max_err, e)
                        if not np.allclose(act[ok], exp[ok], rtol=1e-10, atol=1e-9):
                            bad_vals += 1; fail(f'{oid}: {col} values differ (max {e:.3g})')
                    compared += 1
        idx += 1
    if ids != [l['observation_id'] for l in written] or len(set(ids)) != len(ids):
        fail('observation id set/order differs from ledger written entries')
    if set(ids) & {f'{rec_id}:{s}:frames:{a}:{b}' for s, a, b in xkeys}:
        fail('an observation exists for an excluded pair')
    res.update(record=r, job=item['job'], observations=len(ids), rows=pf.metadata.num_rows, excluded_pairs=len(excluded),
               ledger_entries=len(ledger), sampled_observations=len(sample), sampled_components_compared=compared,
               finite_values_compared=finite_cmp, missing_values_compared=nan_cmp, max_abs_error=max_err,
               failures=fails, status='pass' if not fails else 'fail', rss_mib_so_far=round(rss_mib(), 1))
    del arrays; gc.collect()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--seed', type=int, default=20261102)
    ap.add_argument('--sample', type=int, default=40)
    ap.add_argument('--records', nargs='*')
    ap.add_argument('--no-nice', action='store_true')
    ap.add_argument('--source', default='contributor_tools/conversion_scripts/Umich_2021/Streaming.mat')
    ap.add_argument('--source-sha256', default='df8b3e31d2fe6869b95b4776a8f77639da476685b4c0ccb86c985bee3f01b531')
    a = ap.parse_args()
    if not a.no_nice:
        os.nice(max(0, 19 - os.nice(0)))
    import h5py
    t0 = time.time()
    src = ROOT / a.source
    src_ok = sha(src) == a.source_sha256 if not a.records else None
    a.out.parent.mkdir(parents=True, exist_ok=True)
    items = plan(set(a.records) if a.records else None)
    report = {'schema': 'um21_t03_readback/1', 'seed': a.seed, 'sample_per_record': a.sample, 'source_sha256_checked': src_ok,
              'records': [], 'scientific_approval': False}
    with h5py.File(src, 'r', rdcc_nbytes=1024**2) as h:
        for it in items:
            res = {}
            try:
                check_record(it, h, a.seed, a.sample, res)
            except Exception as e:  # report, never hide
                res.update(record=it['record'], status='error', failures=[repr(e)])
            report['records'].append(res)
            print(res['record'], res['status'], res.get('observations'), res.get('rss_mib_so_far'), flush=True)
            a.out.write_text(json.dumps({**report, 'partial': True}, indent=1) + '\n')
    rs = report['records']
    report.update(partial=False, wall_seconds=round(time.time() - t0, 1), peak_rss_mib=round(rss_mib(), 1),
        totals={'records': len(rs), 'passed': sum(r['status'] == 'pass' for r in rs), 'observations': sum(r.get('observations', 0) for r in rs),
                'sampled_observations': sum(r.get('sampled_observations', 0) for r in rs),
                'sampled_components_compared': sum(r.get('sampled_components_compared', 0) for r in rs),
                'finite_values_compared': sum(r.get('finite_values_compared', 0) for r in rs),
                'missing_values_compared': sum(r.get('missing_values_compared', 0) for r in rs),
                'max_abs_error': max([r.get('max_abs_error', 0) for r in rs] or [0]),
                'excluded_pairs_confirmed_absent': sum(r.get('excluded_pairs', 0) for r in rs)},
        status='pass' if rs and all(r['status'] == 'pass' for r in rs) else 'fail')
    a.out.write_text(json.dumps(report, indent=1) + '\n')
    print(report['status'], report['totals'], report['peak_rss_mib'])
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    sys.exit(main())
