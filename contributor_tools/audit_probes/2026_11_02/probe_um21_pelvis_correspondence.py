"""UM21-C02: do the Normalized and Streaming pelvis fields describe the same physical stride?

Read-only. Never writes under converted_datasets/ except the one report file named by --out
(only when launched by the guarded launcher). One recording at a time; each recording's
Streaming channels (3 x ~20k frames x 4) and its Normalized stride blocks (about 50 x 3 x 150 x 2)
are held and freed before the next record.

Stride identity. Only explicit Normalized StrideDetails rows are used:
[initial frame, final frame, duration (100 Hz), leg (Left = 1, Right = 2)]. A row is bound to
Streaming only if (side, initial, final) equals consecutive same-side heel strikes (LHS for
Left, RHS for Right) and duration = final - initial. Position in the array (the README says
bilateral strides are concatenated) is never used to assign a side or a time.

Same-grid comparison. The Streaming window raw[a-1 .. b-1] (MATLAB 1-based frames a..b) is
linearly resampled to 150 points. The hip channel of the same side is the positive control:
if it matches exactly, the resampling and frame base are the producer's, and any pelvis
difference is a property of the pelvis fields. The alternative frame base (raw[a .. b])
is also reported for the hip, so the frame base is tested, not assumed.

Hypotheses for the pelvis (all reported, none selected):
  H1 same-side Streaming pelvis (RPelvisAngles for Right strides, LPelvisAngles for Left),
  H2 opposite-side Streaming pelvis,
  H1neg the same-side channel with its sign flipped (diagnostic only).
Components are compared one by one (1 = tilt, 2 = obliquity, 3 = rotation in Plug-in Gait
order) together with the missing-value masks and exact-zero fill.
"""
import argparse
import hashlib
import json
import math
import os
import resource
import sys
import time
from pathlib import Path

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
AUD = ROOT / 'docs/quality/audits'
NORM_REL = 'contributor_tools/conversion_scripts/Umich_2021/Normalized.mat'
STREAM_REL = 'contributor_tools/conversion_scripts/Umich_2021/Streaming.mat'
TOL = 1e-6          # degrees; resampling arithmetic differs only at the 1e-12 level
CAP = 40            # worst strides kept per record
JOBS = [('batch0', 'um21-t03-batch0', 'um21-t03-scope.json', 0), ('batch1', 'um21-t03-batch1', 'um21-t03-scope.json', 1)] + \
       [(f'v2-batch{b}', f'um21-t03-v2-batch{b}', 'um21-t03-scope-v2.json', b) for b in range(2, 7)]


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def rss_mib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def stride_key(row):
    """(side, first, last) from one explicit StrideDetails row, or ValueError."""
    if len(row) != 4:
        raise ValueError('StrideDetails row needs four fields')
    a, b, d, leg = (float(x) for x in row)
    if not all(math.isfinite(x) and x == int(x) for x in (a, b, d, leg)):
        raise ValueError('non-integer StrideDetails field')
    if a < 1 or b <= a or b - a != d or leg not in (1, 2):
        raise ValueError('inconsistent StrideDetails row (need 1 <= a < b, duration = b - a, leg 1 or 2)')
    return ('left' if leg == 1 else 'right', int(a), int(b))


def resample(raw, n=150):
    """Linear resampling of a (3, m) or (m,) window to n points on the inclusive grid."""
    raw = np.asarray(raw, float)
    m = raw.shape[-1]
    if m < 2:
        raise ValueError('window needs two samples')
    x = np.arange(n) * (m - 1) / (n - 1)
    lo = np.floor(x).astype(int)
    hi = np.ceil(x).astype(int)
    w = x - lo
    out = raw[..., lo] * (1 - w) + raw[..., hi] * w
    exact = lo == hi
    out[..., exact] = raw[..., lo[exact]]
    return out


def compare(a, b):
    """Per-component comparison of two (3, 150) arrays: error, finite pairs and mask agreement."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    if a.shape != (3, 150) or b.shape != (3, 150):
        raise ValueError('need (3, 150) arrays on the same grid')
    comps = []
    for c in range(3):
        na, nb = np.isnan(a[c]), np.isnan(b[c])
        both = ~na & ~nb
        err = np.abs(a[c][both] - b[c][both])
        comps.append({
            'finite_pairs': int(both.sum()),
            'mask_mismatch': int((na != nb).sum()),
            'both_missing': int((na & nb).sum()),
            'max_abs_error_deg': float(err.max()) if err.size else None,
            'infinite': bool(np.isinf(a[c]).any() or np.isinf(b[c]).any()),
        })
    return comps


def matches(comps, tol=TOL):
    return all(c['finite_pairs'] == 150 and c['mask_mismatch'] == 0 and not c['infinite']
               and c['max_abs_error_deg'] is not None and c['max_abs_error_deg'] <= tol for c in comps)


def all_zero(x):
    x = np.asarray(x, float)
    return bool(np.all(x == 0))


def summarize(per_stride, key):
    """Counts for one hypothesis over strides; per_stride items hold lists of 3 component dicts."""
    n = len(per_stride)
    out = {'strides': n, 'matched_all_components': sum(matches(s[key]) for s in per_stride)}
    for c in range(3):
        errs = [s[key][c]['max_abs_error_deg'] for s in per_stride if s[key][c]['max_abs_error_deg'] is not None]
        out[f'component{c + 1}'] = {
            'matched': sum(s[key][c]['finite_pairs'] == 150 and s[key][c]['mask_mismatch'] == 0 and
                           s[key][c]['max_abs_error_deg'] <= TOL for s in per_stride),
            'mask_mismatch_strides': sum(s[key][c]['mask_mismatch'] > 0 for s in per_stride),
            'median_max_error_deg': float(np.median(errs)) if errs else None,
            'worst_max_error_deg': float(max(errs)) if errs else None,
        }
    return out


def bind_task(sb_events, sb_ang, nb, record_ids, ledger, n_stream_frames):
    """All strides of one Normalized block against one Streaming recording."""
    det = np.asarray(nb['events/StrideDetails'][...])
    det = det.reshape(4, -1).T      # (strides, 4); a one-stride block is stored squeezed
    n = det.shape[0]
    hs = {'left': [int(x) for x in np.asarray(sb_events['LHS']).reshape(-1)],
          'right': [int(x) for x in np.asarray(sb_events['RHS']).reshape(-1)]}
    pairs = {s: set(zip(v, v[1:])) for s, v in hs.items()}
    dims = {k: nb['jointAngles/' + k].shape for k in ('PelvisAngles', 'HipAngles')}
    expect = (n, 3, 150) if n > 1 else (3, 150)
    if any(d != expect for d in dims.values()):
        raise ValueError(f'Normalized block dimensions differ: {dims}, strides {n}')
    npel = np.asarray(nb['jointAngles/PelvisAngles'][...]).reshape(n, 3, 150)
    nhip = np.asarray(nb['jointAngles/HipAngles'][...]).reshape(n, 3, 150)
    rows, unbound, seen = [], [], set()
    for j in range(n):
        try:
            key = stride_key(det[j])
        except ValueError as exc:
            unbound.append({'index': j, 'reason': str(exc), 'row': [float(x) for x in det[j]]})
            continue
        if key in seen:
            unbound.append({'index': j, 'reason': 'duplicate (side, first, last) identity', 'key': list(key)})
            continue
        seen.add(key)
        side, a, b = key
        if (a, b) not in pairs[side]:
            unbound.append({'index': j, 'reason': 'not consecutive same-side Streaming heel strikes', 'key': list(key)})
            continue
        if b > n_stream_frames:
            unbound.append({'index': j, 'reason': 'window beyond Streaming channel length', 'key': list(key)})
            continue
        own, other = ('L', 'R') if side == 'left' else ('R', 'L')
        s_hip = resample(sb_ang[own + 'HipAngles'][:, a - 1:b])
        s_hip_alt = resample(sb_ang[own + 'HipAngles'][:, a:b + 1]) if b + 1 <= n_stream_frames else None
        s_p1 = resample(sb_ang[own + 'PelvisAngles'][:, a - 1:b]) if own + 'PelvisAngles' in sb_ang else None
        s_p2 = resample(sb_ang[other + 'PelvisAngles'][:, a - 1:b]) if other + 'PelvisAngles' in sb_ang else None
        p = npel[j]
        row = {
            'index': j, 'side': side, 'first': a, 'last': b,
            'in_t03_release': ledger.get((side, a, b)),
            'hip_control_base1': compare(nhip[j], s_hip),
            'hip_control_base0': compare(nhip[j], s_hip_alt) if s_hip_alt is not None else None,
            'H1_same_side': compare(p, s_p1) if s_p1 is not None else None,
            'H2_opposite_side': compare(p, s_p2) if s_p2 is not None else None,
            'H1neg_same_side_sign_flipped': compare(p, -s_p1) if s_p1 is not None else None,
            'normalized_pelvis_all_zero': all_zero(p),
            'normalized_pelvis_any_nan': bool(np.isnan(p).any()),
            'stream_same_side_pelvis_all_zero': all_zero(s_p1) if s_p1 is not None else None,
            'normalized_sagittal_pelvis_nonzero': bool(np.nanmax(np.abs(p[0])) > 1e-6) if not np.isnan(p[0]).all() else False,
        }
        rows.append(row)
    return n, rows, unbound


def probe_record(sub, cond, nfile, sfile, ledger):
    """One recording. Returns a compact report (aggregates plus the worst strides)."""
    ncond = {'d5': 'in5', 'd10': 'in10'}.get(cond, cond)
    sb = sfile[f'Streaming/{sub}/Tread/{cond}']
    ang = {}
    for name in ('RPelvisAngles', 'LPelvisAngles', 'RHipAngles', 'LHipAngles'):
        ds = sb['jointAngles/' + name]
        if ds.ndim != 2 or ds.shape[0] != 3:
            raise ValueError(f'Streaming {name} shape {ds.shape}')
        ang[name] = np.asarray(ds[...], float)
    nframes = {v.shape[1] for v in ang.values()}
    if len(nframes) != 1:
        raise ValueError('Streaming channels differ in length')
    nframes = nframes.pop()
    walk = nfile[f'Normalized/{sub}/Walk']
    tasks = {}
    allrows, allunbound, n_total = [], [], 0
    for task in walk:
        if ncond not in walk[task]:
            continue
        nb = walk[task][ncond]
        n, rows, unbound = bind_task(sb['events'], ang, nb, None, ledger, nframes)
        for r in rows:
            r['task'] = task
        for u in unbound:
            u['task'] = task
        tasks[task] = {'normalized_strides': n, 'bound': len(rows), 'unbound': len(unbound)}
        n_total += n
        allrows += rows
        allunbound += unbound
    left = sum(r['side'] == 'left' for r in allrows)
    summary = {'strides_bound': len(allrows), 'left': left, 'right': len(allrows) - left}
    out = {
        'record': f'{sub}/{cond}', 'normalized_condition': ncond, 'streaming_frames': nframes,
        'tasks': tasks, 'normalized_strides': n_total, 'unbound': allunbound, 'summary': summary,
        'sides': {}, 'hip_control_base1': summarize(allrows, 'hip_control_base1') if allrows else None,
    }
    alt = [r for r in allrows if r['hip_control_base0'] is not None]
    out['hip_control_base0'] = summarize(alt, 'hip_control_base0') if alt else None
    for side in ('left', 'right'):
        sr = [r for r in allrows if r['side'] == side]
        out['sides'][side] = {
            'strides': len(sr),
            'normalized_pelvis_all_zero': sum(r['normalized_pelvis_all_zero'] for r in sr),
            'normalized_pelvis_any_nan': sum(r['normalized_pelvis_any_nan'] for r in sr),
            'stream_same_side_pelvis_all_zero': sum(bool(r['stream_same_side_pelvis_all_zero']) for r in sr),
            'normalized_sagittal_pelvis_nonzero': sum(r['normalized_sagittal_pelvis_nonzero'] for r in sr),
            'hip_control_base1': summarize(sr, 'hip_control_base1') if sr else None,
        }
        for h in ('H1_same_side', 'H2_opposite_side', 'H1neg_same_side_sign_flipped'):
            ok = [r for r in sr if r[h] is not None]
            out['sides'][side][h] = summarize(ok, h) if ok else None
    # T03 release overlap: strides in the T03 written ledger that have a normalized twin
    inrel = [r for r in allrows if r['in_t03_release'] is not None]
    out['t03_written_with_normalized_twin'] = len(inrel)
    out['t03_written_total'] = sum(1 for v in ledger.values() if v is not None)
    out['t03_labels_vs_normalized_task'] = {
        'agree': sum(r['in_t03_release']['label'] == r['task'] for r in inrel),
        'differ': [{'key': [r['side'], r['first'], r['last']], 'task': r['task'], 'ledger_label': r['in_t03_release']['label']}
                   for r in inrel if r['in_t03_release']['label'] != r['task']][:10]}
    out['t03_pelvis_H1_matched_in_release'] = sum(matches(r['H1_same_side']) for r in inrel if r['H1_same_side'])
    # worst same-side pelvis strides (never hidden behind the aggregate)
    def worst(r):
        h = r['H1_same_side']
        return -1 if h is None else max((c['max_abs_error_deg'] or 0) for c in h)
    out['worst_H1_strides'] = [{'side': r['side'], 'first': r['first'], 'last': r['last'], 'task': r['task'],
                                'max_error_deg': worst(r), 'normalized_pelvis_all_zero': r['normalized_pelvis_all_zero']}
                               for r in sorted(allrows, key=worst, reverse=True)[:CAP] if worst(r) > TOL]
    return out


def load_ledger(path):
    """(side, start, end) -> {'label', 'observation_id'} for written observations; None for exclusions."""
    out = {}
    for line in Path(path).read_text().splitlines():
        d = json.loads(line)
        key = (d['side'], int(d['start']), int(d['end']))
        out[key] = ({'label': d.get('label'), 'observation_id': d['observation_id']}
                    if d.get('status') == 'written_unreviewed' else None)
    return out


def plan(only):
    """Records and ledger paths enumerated from the seven receipts and the scope files only (no glob)."""
    out = []
    for name, stem, scope_name, batch in JOBS:
        rec = json.loads((AUD / f'{stem}-launcher-receipt.json').read_text())
        scope = json.loads((AUD / scope_name).read_text())
        for r in scope['batches'][batch]:
            if only and r not in only:
                continue
            sub, cond = r.split('/')
            led = Path(rec['spec']['output_root']) / 'base_batch' / sub / cond / 'candidate_ledger.jsonl'
            out.append({'job': name, 'record': r, 'ledger': led})
    return out


def run(args):
    import h5py
    if not args.no_nice:
        os.nice(19)
    t0 = time.time()
    src_n, src_s = ROOT / NORM_REL, ROOT / STREAM_REL
    stat0 = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in (src_n, src_s)}
    if args.normalized_sha256 and sha(src_n) != args.normalized_sha256:
        raise SystemExit('Normalized.mat hash differs')
    if args.source_sha256 and sha(src_s) != args.source_sha256:
        raise SystemExit('Streaming.mat hash differs')
    only = set(args.record or [])
    items = plan(only)
    if only and len(items) != len(only):
        raise SystemExit('requested record not in the 44-record scope')
    records = []
    with h5py.File(src_n, 'r', rdcc_nbytes=1 << 20) as nfile, h5py.File(src_s, 'r', rdcc_nbytes=1 << 20) as sfile:
        for it in items:
            sub, cond = it['record'].split('/')
            records.append(probe_record(sub, cond, nfile, sfile, load_ledger(it['ledger'])))
            print(it['record'], 'done', round(rss_mib(), 1), 'MiB peak', flush=True)
    stat1 = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in (src_n, src_s)}
    if stat0 != stat1:
        raise SystemExit('source file changed during the probe')
    report = {
        'task_id': 'UM21-C02', 'scientific_approval': False, 'probe': Path(__file__).name,
        'probe_sha256': sha(__file__), 'tolerance_deg': TOL, 'records': records,
        'sources': {'Normalized.mat': {'sha256_bound': args.normalized_sha256, 'size_mtime_ns': stat0['Normalized.mat']},
                    'Streaming.mat': {'sha256_bound': args.source_sha256, 'size_mtime_ns': stat0['Streaming.mat']}},
        'peak_rss_mib': round(rss_mib(), 1), 'wall_seconds': round(time.time() - t0, 1),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x') as f:
        json.dump(report, f, indent=1, allow_nan=False)
    print('wrote', out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', required=True)
    p.add_argument('--record', action='append', help='SUBJECT/COND; repeatable. Default: all 44 scope records')
    p.add_argument('--source-sha256')
    p.add_argument('--normalized-sha256')
    p.add_argument('--no-nice', action='store_true')
    run(p.parse_args())


if __name__ == '__main__':
    main()
