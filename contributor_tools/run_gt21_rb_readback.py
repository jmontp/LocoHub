"""GT21 merged pass readback (GT21-RB02/RB04): checks the 22 batch outputs against the RB01 inventory and re-derives a seeded
sample from the SOURCE with a separate scalar code path (no import of gt21_rb_pass).

Reads one recording file at a time. Checks:
 1. disposition: every inventory recording of every participant has exactly one ledger line (converted or excluded with a reason);
    converted lines have their Parquet and no other Parquet exists.
 2. frozen code: every batch's run_summary code hashes equal the files now.
 3. stored data: rows equal the ledger sample count; time strictly increasing and finite; no inf; hip = thigh - pelvis,
    knee = thigh - shank, ankle = foot - shank to 1e-12 where finite; every held frame is missing in that leg's angles, speeds
    and CoP; CoP within the foot-frame limits and under no less than 0.2 BW; CoP and GRF anterior/lateral never finite where
    the ledger says the plate is absent.
 4. independent re-derivation (seeded, 3 recordings per participant, 25 frames each): pelvis angle from the raw markers with
    scalar loops, and the plate vertical force against the raw force plates (treadmill: the named plate exactly; overground: the
    two feet together never exceed the sum of all plates).
Writes a NEW root with readback.json and run_summary.json. No scientific approval is claimed.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import resource
import sys

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('ARROW_DEFAULT_MEMORY_POOL', 'system')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
from contributor_tools import gt21_numeric_source as src  # noqa: E402
from contributor_tools import run_gt21_rb_pass as run  # noqa: E402

BATCH = 'converted_datasets/reconversion_v2/gt21_rb_pass_batch_{s}_20261124'
SEED = 20261126
PER_PARTICIPANT = 3
FRAMES = 25


def sha256_file(path):
    return run.sha256_file(path)


def batch_dir(s):
    return ROOT / BATCH.format(s=s)


def batch_ledger_path(s):
    d = batch_dir(s)
    return d / 'ledger.jsonl'


def check_dispositions(inv, subjects):
    out = {}
    for s in subjects:
        want = {(m, r) for (sj, m, r) in inv if sj == s}
        got, dup, rows = {}, [], []
        for line in batch_ledger_path(s).read_text().splitlines():
            e = json.loads(line)
            key = (e['mode'], e['recording'])
            if key in got:
                dup.append(key)
            got[key] = e
            rows.append(e)
        files = {p.relative_to(batch_dir(s)).as_posix() for p in batch_dir(s).rglob('*.parquet')}
        listed = {e['parquet'] for e in rows if e['status'] == 'converted'}
        out[s] = dict(inventory=len(want), ledger=len(got), converted=sum(e['status'] == 'converted' for e in rows),
                      excluded=[(k, e['reason']) for k, e in got.items() if e['status'] != 'converted'],
                      missing_from_ledger=sorted(want - set(got)), extra_in_ledger=sorted(set(got) - want),
                      duplicates=dup, parquet_not_listed=sorted(files - listed), listed_not_on_disk=sorted(listed - files),
                      ok=(want == set(got) and not dup and files == listed))
    return out


def check_code_hashes(subjects):
    now = {c: sha256_file(ROOT / c) for c in run.CODE}
    bad = {}
    for s in subjects:
        summary = json.loads((batch_dir(s) / 'run_summary.json').read_text())
        diff = {c: h for c, h in summary['code_sha256'].items() if now.get(c) != h}
        if diff:
            bad[s] = diff
    return now, bad


def check_stored(path, entry):
    t = pq.read_table(path)
    n = t.num_rows
    cols = {c: t.column(c).to_numpy(zero_copy_only=False) for c in t.column_names}
    res = {'rows_equal_ledger': n == entry['n_samples']}
    time = cols['time_s']
    res['time_ok'] = bool(np.isfinite(time).all() and (np.diff(time) > 0).all())
    res['no_inf'] = all(not np.isinf(v).any() for v in cols.values() if v.dtype.kind == 'f')
    comp = 0.0
    held_leak = 0
    cop_bad = 0
    for leg in ('right', 'left'):
        th, sh, ft = (cols[f'{k}_sagittal_angle_{leg}_rad'] for k in ('thigh', 'shank', 'foot'))
        pel = cols['pelvis_sagittal_angle_rad']
        for a, b in ((cols[f'hip_flexion_angle_{leg}_rad'], th - pel), (cols[f'knee_flexion_angle_{leg}_rad'], th - sh),
                     (cols[f'ankle_dorsiflexion_angle_{leg}_rad'], ft - sh)):
            d = np.abs(a - b)
            d = d[np.isfinite(d)]
            comp = max(comp, float(d.max()) if d.size else 0.0)
        held = cols[f'geometry_hold_{leg}'] > 0
        names = [f'{k}_sagittal_angle_{leg}_rad' for k in ('thigh', 'shank', 'foot')] + \
                [f'{k}_{q}_{leg}_{u}' for k in ('hip_flexion', 'knee_flexion', 'ankle_dorsiflexion')
                 for q, u in (('angle', 'rad'), ('velocity', 'rad_s'))] + [f'cop_{k}_{leg}_m' for k in ('anterior', 'vertical', 'lateral')]
        held_leak += int(sum(np.isfinite(cols[c][held]).sum() for c in names))
        a, l, v = cols[f'cop_anterior_{leg}_m'], cols[f'cop_lateral_{leg}_m'], cols[f'grf_vertical_{leg}_BW']
        fin = np.isfinite(a)
        cop_bad += int(((np.abs(a[fin]) > 0.5) | (np.abs(l[fin]) > 0.10) | ~(v[fin] >= 0.2)).sum())
    res.update(composition_max_abs_error_rad=comp, held_frames_with_values=held_leak, cop_limit_violations=cop_bad)
    if entry['plates'].get('unavailable_reason'):
        res['plate_absent_but_force_present'] = int(sum(np.isfinite(cols[f'grf_vertical_{leg}_BW']).sum() for leg in ('right', 'left')))
    res['ok'] = (res['rows_equal_ledger'] and res['time_ok'] and res['no_inf'] and comp <= 1e-12 and held_leak == 0 and cop_bad == 0
                 and not res.get('plate_absent_but_force_present'))
    return res, cols


def independent(entry, cols, rng, roots=None):
    """Re-derive pelvis angle and plate vertical force from the source at seeded frames with scalar code."""
    roots = roots or run.ROOTS
    base = roots[entry['source']] / entry['subject'] / entry['session'] / entry['mode']
    rec = entry['recording']
    mk = src.read_numeric_table(base / 'markers' / f'{rec}.mat')
    fp = src.read_numeric_table(base / 'fp' / f'{rec}.mat')
    weight = entry['weight_kg']
    n = len(mk['Header'])
    idx = sorted(rng.sample(range(n), min(FRAMES, n)))
    worst_pelvis = 0.0
    for i in idx:
        v = lambda name: [mk[f'{name}_{a}'][i] / 1000.0 for a in 'xyz']
        la, ra, lp, rp = v('L_ASIS'), v('R_ASIS'), v('L_PSIS'), v('R_PSIS')
        d = [((la[k] + ra[k]) - (lp[k] + rp[k])) / 2.0 for k in range(3)]
        if not all(math.isfinite(x) for x in d):
            continue
        horiz = math.hypot(d[0], d[2])
        want = math.atan2(d[1], horiz)
        worst_pelvis = max(worst_pelvis, abs(want - cols['pelvis_sagittal_angle_rad'][i]))
    ft = fp['Header']
    names = sorted({c[:-3] for c in fp if c.endswith('_vy')})
    bw = weight * 9.81
    worst_force, exceed = 0.0, 0
    for i in idx:
        t = mk['Header'][i]
        j = int(np.searchsorted(ft, t, side='right')) - 1
        if j < 0 or j >= len(ft) - 1:
            continue
        w = (t - ft[j]) / (ft[j + 1] - ft[j]) if ft[j] != t else 0.0
        plate = {p: fp[f'{p}_vy'][j] + w * (fp[f'{p}_vy'][j + 1] - fp[f'{p}_vy'][j]) for p in names}
        if entry['mode'] == 'treadmill':
            for leg, p in (('right', 'Treadmill_R'), ('left', 'Treadmill_L')):
                got = cols[f'grf_vertical_{leg}_BW'][i] * bw
                if math.isfinite(plate[p]) and math.isfinite(got):
                    worst_force = max(worst_force, abs(got - plate[p]))
        else:
            tot = sum(cols[f'grf_vertical_{leg}_BW'][i] * bw for leg in ('right', 'left') if math.isfinite(cols[f'grf_vertical_{leg}_BW'][i]))
            allp = sum(max(v_, 0.0) for v_ in plate.values() if math.isfinite(v_))
            if tot > allp + 1e-6:
                exceed += 1
    return {'frames': len(idx), 'pelvis_angle_max_abs_diff_rad': worst_pelvis,
            'treadmill_vertical_force_max_abs_diff_N': worst_force if entry['mode'] == 'treadmill' else None,
            'overground_feet_exceed_all_plates_frames': exceed if entry['mode'] != 'treadmill' else None,
            'ok': worst_pelvis < 1e-9 and worst_force < 1e-6 and exceed == 0}


def supplement(out, only):
    results = []
    rng = random.Random(SEED + 1)
    for rec in only:
        s, mode, name = rec.split('/')
        entry = next(json.loads(l) for l in batch_ledger_path(s).read_text().splitlines()
                     if json.loads(l)['recording'] == name and json.loads(l)['mode'] == mode)
        res, cols = check_stored(batch_dir(s) / entry['parquet'], entry)
        info = json.loads((ROOT / run.LABELS / s / f'subject_info_{s}.json').read_text())
        try:
            ind = independent(dict(entry, weight_kg=float(info['values']['Weight'])), cols, rng)
        except Exception as exc:
            ind = {'ok': False, 'error': f'{type(exc).__name__}: {exc}'[:300]}
        results.append({'recording': rec, 'stored': res, 'independent': ind})
    report = {'status': 'readback_supplement_unreviewed', 'scientific_approval': False, 'seed': SEED + 1, 'results': results,
              'ok': all(r['stored']['ok'] and r['independent']['ok'] for r in results)}
    with open(out / 'readback.json', 'x') as f:
        json.dump(report, f, indent=1, sort_keys=True, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
        f.write('\n')
    with open(out / 'run_summary.json', 'x') as f:
        json.dump({'status': report['status'], 'ok': report['ok'], 'peak_rss_mib': run.peak_rss_mib(), 'scientific_approval': False}, f)
        f.write('\n')
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out-root', required=True)
    p.add_argument('--only', action='append', help='SUBJECT/MODE/RECORDING: stored and independent checks for these only '
                   '(a supplement run in a fresh process; no disposition or code-hash checks)')
    args = p.parse_args(argv)
    out = Path(args.out_root)
    if out.exists() and any(out.iterdir()):
        raise SystemExit('output root must be new')
    out.mkdir(parents=True, exist_ok=True)
    inv = run.load_inventory()
    if args.only:
        return supplement(out, args.only)
    subjects = sorted({s for s, _, _ in inv})
    disp = check_dispositions(inv, subjects)
    code_now, code_bad = check_code_hashes(subjects)
    rng = random.Random(SEED)
    stored_failures, indep, totals = [], [], {'recordings': 0, 'held_frames': 0, 'frames': 0}
    seeded = {}
    for s in subjects:
        entries = [json.loads(l) for l in batch_ledger_path(s).read_text().splitlines()]
        conv = [e for e in entries if e['status'] == 'converted']
        seeded[s] = {e['recording'] for e in rng.sample(conv, min(PER_PARTICIPANT, len(conv)))}
        for e in conv:
            res, cols = check_stored(batch_dir(s) / e['parquet'], e)
            totals['recordings'] += 1
            totals['frames'] += e['n_samples']
            totals['held_frames'] += sum(e['fit'][leg]['geometry_hold']['held_frames'] for leg in ('right', 'left'))
            if not res['ok']:
                stored_failures.append({'recording': f"{s}/{e['mode']}/{e['recording']}", **res})
            if e['recording'] in seeded[s]:
                info = json.loads((ROOT / run.LABELS / s / f'subject_info_{s}.json').read_text())
                e = dict(e, weight_kg=float(info['values']['Weight']))
                try:
                    r = independent(e, cols, rng)
                except Exception as exc:
                    r = {'ok': False, 'error': f'{type(exc).__name__}: {exc}'[:300]}
                indep.append({'recording': f"{s}/{e['mode']}/{e['recording']}", **r})
            del cols
    report = {'status': 'readback_done_unreviewed', 'scientific_approval': False, 'seed': SEED,
              'dispositions': disp, 'disposition_ok': all(d['ok'] for d in disp.values()),
              'inventory_total': len(inv), 'ledger_total': sum(d['ledger'] for d in disp.values()),
              'converted_total': sum(d['converted'] for d in disp.values()),
              'excluded_total': sum(len(d['excluded']) for d in disp.values()),
              'code_sha256_now': code_now, 'batches_with_other_code': code_bad,
              'stored_checks': {**totals, 'failed_recordings': stored_failures},
              'independent_rederivation': {'recordings': len(indep), 'failed': [r for r in indep if not r['ok']], 'all': indep}}
    report['ok'] = bool(report['disposition_ok'] and not code_bad and not stored_failures and all(r['ok'] for r in indep))
    with open(out / 'readback.json', 'x') as f:
        json.dump(report, f, indent=1, sort_keys=True, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
        f.write('\n')
    with open(out / 'run_summary.json', 'x') as f:
        json.dump({'status': 'readback_done_unreviewed', 'ok': report['ok'], 'peak_rss_mib': run.peak_rss_mib(),
                   'scientific_approval': False}, f, indent=1)
        f.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
