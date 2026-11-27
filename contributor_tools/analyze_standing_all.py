"""A4: standing-pose check for all three datasets (GT21, GT23, UM21).  DRAFT, read-only probes; outputs go to a NEW root.

Subcommands (each bounded: one recording at a time, <300 MiB, run under prlimit/nice/ionice):
  gt23     standing angles from the authors' static_N.trc markers, using gt23_conventions (the geometry of the GT23 package) and
           run_gt23_c06.read_markers.  The package takes thigh and shank from the authors' IK model axes, which do not exist for static
           trials, so standing thigh/shank here use the repo's own marker route (knee centre minus model hip centre, ankle centre minus
           knee centre; the hip centre from a rigid fit of the four pelvis markers to the scaled model).  The package's own marker-vs-model
           difference for level walking (from the C06 ledgers) is read out as a bias and reported as a sensitivity.
  um21     UM21 has NO static trial in the published Streaming.mat.  Proxy only: the standing plateau inside each sit-to-stand recording
           (pelvis height steady within 1 cm, speed below 0.02 m/s, central 60 percent of the longest such run, at least 50 frames),
           run through run_um21_s02_frame's per-leg plane geometry (Harrington hip centres).  Also the authors' Plug-in Gait angles there.
  combine  per-person walking and standing numbers, three-way gaps (as published and with standing as zero), CSV and JSON.
  sheet    review_sheets/A4-standing-all/.
"""
import os
for _k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_k] = '1'
import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
D = 180.0 / math.pi
OUT = ROOT / 'converted_datasets/reconversion_v2/standing_check_v1'
RECON = ROOT / 'converted_datasets/reconversion_v2'
GT23_RAW = Path('/mnt/s/locomotion_data/Gtech_2023/RawData')
UM21_MAT = ROOT / 'contributor_tools/conversion_scripts/Umich_2021/Streaming.mat'
QUANT = ('thigh', 'shank', 'foot', 'pelvis', 'hip', 'knee', 'ankle')
STANDING_PLATEAU_M = 0.01
STANDING_SPEED_M_S = 0.02
STANDING_MIN_FRAMES = 50


def nanmean_of(values):
    v = np.asarray([x for x in values if x is not None and np.isfinite(x)], float)
    return float(v.mean()) if v.size else float('nan')


def write_csv(path, rows):
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, 'x', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


# ------------------------------------------------------------------------------------------------ GT23
def kabsch(local, lab):
    """Rotation R and translation t with lab = R @ local + t (rows are points); proper rotation only."""
    cl, cb = local.mean(0), lab.mean(0)
    h = (local - cl).T @ (lab - cb)
    u, _, vt = np.linalg.svd(h)
    s = np.diag([1, 1, np.sign(np.linalg.det(vt.T @ u.T))])
    r = vt.T @ s @ u.T
    return r, cb - r @ cl


def static_numbers(subject, trc, model_text):
    from contributor_tools import gt23_conventions as cv
    from contributor_tools import run_gt23_c06 as c06
    mk, absent, n = c06.read_markers(trc, c06.MARKERS_USED)
    out = {'frames': n, 'absent': ','.join(absent)}
    asis_mid = (mk['LASI'] + mk['RASI']) / 2
    psis_mid = (mk['LPSI'] + mk['RPSI']) / 2
    pelvis = cv.pelvis_angle(asis_mid, psis_mid)
    out['pelvis'] = float(np.nanmean(pelvis)) * D
    mean_mk = {k: np.nanmean(v, axis=0, keepdims=True) for k, v in mk.items()}
    for S, side in (('L', 'left'), ('R', 'right')):
        s = S.lower()
        fwd = cv.plane_forward(cv.knee_axis_to_right(mk[f'{S}KNE'], mk[f'{S}MKNE'], S))
        knee_mid = (mk[f'{S}KNE'] + mk[f'{S}MKNE']) / 2
        ankle_mid = (mk[f'{S}ANK'] + mk[f'{S}MANK']) / 2
        heel, toe = mk[f'{S}CAL'], (mk[f'{S}MT1'] + mk[f'{S}MT5']) / 2
        # shank and foot per frame (no model needed)
        a = cv.leg_segment_angles(fwd, np.full_like(knee_mid, np.nan), ankle_mid - knee_mid, heel, toe)
        out[f'shank_{side}'] = float(np.nanmean(a['shank'])) * D
        out[f'foot_{side}'] = float(np.nanmean(a['foot'])) * D
        # thigh needs the model hip centre (rigid fit of the pelvis markers to the scaled model)
        thigh = float('nan')
        try:
            geo = cv.model_geometry(model_text, s)
            names = ('LASI', 'RASI', 'LPSI', 'RPSI')
            if all(k in geo['markers'] for k in names) and all(np.isfinite(mean_mk[k]).all() for k in names):
                r, _ = kabsch(np.array([geo['markers'][k] for k in names]), np.array([mean_mk[k][0] for k in names]))
                hip = cv.model_hip_centre({k: mean_mk[k] for k in names}, geo, r[None])
                fwd1 = cv.plane_forward(cv.knee_axis_to_right(mean_mk[f'{S}KNE'], mean_mk[f'{S}MKNE'], S))
                kn = (mean_mk[f'{S}KNE'] + mean_mk[f'{S}MKNE']) / 2
                thigh = float(cv.angle_from_down(cv.sag(kn - hip, fwd1))[0]) * D
        except KeyError as e:
            out['thigh_note'] = f'model lacks {e}'
        out[f'thigh_{side}'] = thigh
    return out


def gt23_bias():
    """Marker-minus-published median offsets (degrees) in level walking (normal_walk_1) from the C06 ledgers, per subject."""
    bias = {}
    for led in sorted(RECON.glob('gt23_c06_batch3_AB*/ledger.jsonl')):
        for line in led.read_text().splitlines():
            r = json.loads(line)
            if r.get('recording') != 'normal_walk_1':
                continue
            vals = {k: [] for k in ('thigh', 'shank')}
            for S in 'LR':
                m = r['legs'][S].get('markers_vs_model_axes', {})
                for k in vals:
                    if k in m and 'median_offset_deg' in m[k]:
                        vals[k].append(m[k]['median_offset_deg'])
            bias[r['subject']] = {k: nanmean_of(v) for k, v in vals.items()}
    return bias


def cmd_gt23(args):
    from contributor_tools import run_gt23_c06 as c06
    OUT.mkdir(parents=True, exist_ok=True)
    rows, per_subject = [], []
    bias = gt23_bias()
    subjects = args.subject or list(c06.SUBJECTS)
    for subject in subjects:
        folder = GT23_RAW / subject
        statics = {}
        for line in (folder / 'Models/Statics.csv').read_text().splitlines()[1:]:
            name, val = line.split(',')[:2]
            statics[name] = val
        used = statics.get('normal_walk_1')
        files = sorted((folder / 'MarkerData').glob('static_*.trc'), key=lambda p: int(re.search(r'(\d+)', p.stem).group(1)))
        model_text = (folder / 'Models' / c06.MODEL_FILE[subject]).read_text()
        trials = []
        for p in files:
            k = re.search(r'(\d+)', p.stem).group(1)
            rec = {'subject': subject, 'recording': p.stem, 'static_index_of_normal_walk': used,
                   'is_walking_static': k == used, 'status': 'ok'}
            try:
                rec.update(static_numbers(subject, p, model_text))
            except Exception as exc:
                rec.update(status='excluded', reason=f'{type(exc).__name__}: {exc}'[:200])
            trials.append(rec)
            rows.append(rec)
        use = [t for t in trials if t['status'] == 'ok' and t['is_walking_static']] or [t for t in trials if t['status'] == 'ok']
        row = {'subject': subject, 'n_static_files': len(files), 'static_index_for_walking': used,
               'trials_used': ';'.join(t['recording'] for t in use), 'used_walking_static': any(t['is_walking_static'] for t in use)}
        for q in ('thigh', 'shank', 'foot'):
            row[q] = nanmean_of([nanmean_of([t.get(f'{q}_left'), t.get(f'{q}_right')]) for t in use])
        row['pelvis'] = nanmean_of([t.get('pelvis') for t in use])
        row['hip'], row['knee'], row['ankle'] = row['thigh'] - row['pelvis'], row['thigh'] - row['shank'], row['foot'] - row['shank']
        b = bias.get(subject, {})
        row['bias_thigh'], row['bias_shank'] = b.get('thigh', float('nan')), b.get('shank', float('nan'))
        row['thigh_adj'], row['shank_adj'] = row['thigh'] - row['bias_thigh'], row['shank'] - row['bias_shank']
        row['knee_adj'], row['ankle_adj'] = row['thigh_adj'] - row['shank_adj'], row['foot'] - row['shank_adj']
        row['hip_adj'] = row['thigh_adj'] - row['pelvis']
        # spread over all static files of the person (steadiness between statics)
        for q in ('thigh', 'shank', 'foot'):
            v = [nanmean_of([t.get(f'{q}_left'), t.get(f'{q}_right')]) for t in trials if t['status'] == 'ok']
            row[f'{q}_range_over_statics'] = float(np.nanmax(v) - np.nanmin(v)) if len(v) and np.isfinite(v).any() else float('nan')
        per_subject.append(row)
    tag = args.tag
    write_csv(OUT / f'gt23_static_trials{tag}.csv', rows)
    write_csv(OUT / f'gt23_standing_per_participant{tag}.csv', per_subject)
    import resource
    print('peak MiB', resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
    return 0


# ------------------------------------------------------------------------------------------------ UM21
def plateau(z):
    """Frame indices of the central 60 percent of the longest steady plateau at the top of z; empty if none."""
    z = np.asarray(z, float)
    ok = np.isfinite(z)
    if ok.sum() < STANDING_MIN_FRAMES:
        return np.array([], int)
    top = np.nanpercentile(z[ok], 90)
    speed = np.abs(np.gradient(np.where(ok, z, np.nanmedian(z)), 0.01))
    m = ok & (np.abs(z - top) <= STANDING_PLATEAU_M) & (speed < STANDING_SPEED_M_S)
    best, start = (0, 0), None
    for i, v in enumerate(list(m) + [False]):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start > best[1] - best[0]:
                best = (start, i)
            start = None
    a, b = best
    if b - a < STANDING_MIN_FRAMES:
        return np.array([], int)
    n = b - a
    return np.arange(a + int(0.2 * n), b - int(0.2 * n))


def um21_trial(t):
    from contributor_tools import run_um21_s02_frame as s
    n = t['markers']['LASI'].shape[1]
    mk, cov = s.read_markers(t, n)
    asi, psi = (mk['LASI'] + mk['RASI']) / 2, (mk['LPSI'] + mk['RPSI']) / 2
    z = np.nanmean(np.stack([mk[k][:, 2] for k in ('LASI', 'RASI', 'LPSI', 'RPSI')]), axis=0)
    idx = plateau(z)
    rec = {'frames': n, 'standing_frames': int(idx.size)}
    if not idx.size:
        return rec
    sel = {k: v[idx] for k, v in mk.items()}
    hj = s.hip_centres(sel['RASI'], sel['LASI'], sel['RPSI'], sel['LPSI'])
    pelvis = s.pelvis_angle_own_plane(asi[idx], psi[idx])
    rec['pelvis'] = float(np.nanmean(pelvis)) * D
    for S, side in (('L', 'left'), ('R', 'right')):
        fwd = s.plane_forward(s.knee_axis_to_right(sel[S + s.KNEE_LATERAL_MARKER], sel[S + s.KNEE_MEDIAL_MARKER], S))
        hip = hj['left' if S == 'L' else 'right']
        knee = (sel[f'{S}KNE'] + sel[f'{S}KNEM']) / 2
        ank = (sel[f'{S}ANK'] + sel[f'{S}ANKM']) / 2
        a = s.leg_segment_angles(fwd, knee - hip, ank - knee, sel[f'{S}HEE'], sel[f'{S}TOE'])
        for q in ('thigh', 'shank', 'foot'):
            rec[f'{q}_{side}'] = float(np.nanmean(a[q])) * D
    ja = t['jointAngles']
    for name, key in (('pig_knee', 'KneeAngles'), ('pig_hip', 'HipAngles'), ('pig_ankle', 'AnkleAngles'), ('pig_pelvis', 'PelvisAngles')):
        for S, side in (('L', 'left'), ('R', 'right')):
            if f'{S}{key}' in ja:
                rec[f'{name}_{side}'] = float(np.nanmean(ja[f'{S}{key}'][0][idx]))
    return rec


def cmd_um21(args):
    import h5py
    OUT.mkdir(parents=True, exist_ok=True)
    rows, per = [], []
    with h5py.File(UM21_MAT, 'r') as f:
        subjects = args.subject or sorted(f['Streaming'].keys())
        for subject in subjects:
            sts = f['Streaming'][subject]['Sts']
            trials = []
            for tn in sorted(sts.keys()):
                rec = {'subject': subject, 'recording': tn, 'status': 'ok'}
                try:
                    rec.update(um21_trial(sts[tn]))
                except Exception as exc:
                    rec.update(status='excluded', reason=f'{type(exc).__name__}: {exc}'[:200])
                trials.append(rec)
                rows.append(rec)
            use = [t for t in trials if t['status'] == 'ok' and t.get('standing_frames', 0) >= STANDING_MIN_FRAMES * 0.6]
            row = {'subject': subject, 'n_sts_recordings': len(trials), 'n_with_standing_plateau': len(use)}
            for q in ('thigh', 'shank', 'foot'):
                row[q] = nanmean_of([nanmean_of([t.get(f'{q}_left'), t.get(f'{q}_right')]) for t in use])
            row['pelvis'] = nanmean_of([t.get('pelvis') for t in use])
            row['hip'], row['knee'], row['ankle'] = row['thigh'] - row['pelvis'], row['thigh'] - row['shank'], row['foot'] - row['shank']
            for q in ('pig_knee', 'pig_hip', 'pig_ankle', 'pig_pelvis'):
                row[q] = nanmean_of([nanmean_of([t.get(f'{q}_left'), t.get(f'{q}_right')]) for t in use])
            for q in ('thigh', 'shank', 'foot'):
                v = [nanmean_of([t.get(f'{q}_left'), t.get(f'{q}_right')]) for t in use]
                row[f'{q}_range_over_recordings'] = float(np.nanmax(v) - np.nanmin(v)) if len(v) and np.isfinite(v).any() else float('nan')
            per.append(row)
    write_csv(OUT / f'um21_sts_trials{args.tag}.csv', rows)
    write_csv(OUT / f'um21_sts_standing_per_participant{args.tag}.csv', per)
    import resource
    print('peak MiB', resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
    return 0


# ------------------------------------------------------------------------------------------------ combine
def read_rows(path):
    with open(path, newline='') as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k, v in r.items():
            if k != 'subject':
                try:
                    r[k] = float(v)
                except ValueError:
                    pass
    return rows


def stats(x):
    x = np.asarray([v for v in x if np.isfinite(v)], float)
    if not x.size:
        return {'n': 0, 'mean': float('nan'), 'sd': float('nan'), 'min': float('nan'), 'max': float('nan')}
    return {'n': int(x.size), 'mean': float(x.mean()), 'sd': float(x.std(ddof=1)) if x.size > 1 else 0.0,
            'min': float(x.min()), 'max': float(x.max())}


def load_people():
    """{dataset: {subject: {'walk': {q: deg}, 'stand': {q: deg}, 'stand_adj': {...}}}}"""
    people = {'GT21': {}, 'GT23': {}, 'UM21': {}}
    for r in read_rows(RECON / 'gt21_static_analysis_v1/per_participant.csv'):
        people['GT21'][r['subject']] = {'walk': {q: r[f'mid_{q}'] for q in QUANT}, 'stand': {q: r[f'lh_{q}'] for q in QUANT}}
    walk23 = json.loads((OUT / 'walking_means_GT23.json').read_text())['means']
    st23 = {r['subject']: r for r in read_rows(OUT / 'gt23_standing_per_participant.csv')}
    for s, m in walk23.items():
        r = st23.get(s)
        people['GT23'][s] = {'walk': {q: m.get(q, float('nan')) for q in QUANT},
                             'stand': {q: (r[q] if r else float('nan')) for q in QUANT},
                             'stand_adj': {q: (r[f'{q}_adj'] if r and f'{q}_adj' in r else (r[q] if r else float('nan'))) for q in QUANT}}
    walk21 = json.loads((OUT / 'walking_means_UM21.json').read_text())['means']
    st21 = {r['subject']: r for r in read_rows(OUT / 'um21_sts_standing_per_participant.csv')}
    for s, m in walk21.items():
        key = s.replace('UM21_', '')
        r = st21.get(key)
        people['UM21'][key] = {'walk': {q: m.get(q, float('nan')) for q in QUANT},
                               'stand': {q: (r[q] if r else float('nan')) for q in QUANT}}
    return people


def summarise(people, standing_for, variant='stand'):
    """Walking means per dataset: as published (all people), as published (people with standing), and with standing as zero."""
    out = {}
    for ds, ppl in people.items():
        entry = {'people_walking': len(ppl)}
        for q in QUANT:
            walk_all = [p['walk'][q] for p in ppl.values()]
            both = [(p['walk'][q], (p.get(variant) or p['stand'])[q]) for p in ppl.values()
                    if np.isfinite(p['walk'][q]) and np.isfinite((p.get(variant) or p['stand'])[q])]
            w = np.array([b[0] for b in both])
            st = np.array([b[1] for b in both])
            e = {'published_all': stats(walk_all), 'standing': stats(st)}
            if standing_for.get(ds):
                e['published_same_people'] = stats(w)
                e['standing_zero'] = stats(w - st)
            entry[q] = e
        out[ds] = entry
    return out


def three_way(summary, standing_set):
    """Mean-per-dataset table and pairwise gaps (GT21 minus x, GT23 minus UM21) and the spread (max minus min) of the three means.
    Datasets in standing_set use the standing-zero mean over people with standing data; the others stay as published (all people)."""
    table = {}
    for q in QUANT:
        mean = {ds: (summary[ds][q]['standing_zero']['mean'] if ds in standing_set else summary[ds][q]['published_all']['mean'])
                for ds in summary}
        v = [x for x in mean.values() if np.isfinite(x)]
        table[q] = {'mean': mean, 'GT21_minus_GT23': mean['GT21'] - mean['GT23'], 'GT21_minus_UM21': mean['GT21'] - mean['UM21'],
                    'GT23_minus_UM21': mean['GT23'] - mean['UM21'], 'spread_max_minus_min': float(max(v) - min(v)) if v else float('nan')}
    return table


def cmd_combine(args):
    people = load_people()
    result = {'window_percent': [20, 35], 'task': 'level walking 1.2 m/s, filtered phase tables (GT21 v1, GT23 v11, UM21 v5)',
              'people_walking': {ds: len(p) for ds, p in people.items()}, 'variants': {}}
    sets = {'as_published': (set(), 'stand'),
            'GT21_only (A3)': ({'GT21'}, 'stand'),
            'GT21+GT23 (marker standing)': ({'GT21', 'GT23'}, 'stand'),
            'GT21+GT23 (bias-adjusted standing)': ({'GT21', 'GT23'}, 'stand_adj'),
            'all three (UM21 sit-to-stand proxy)': ({'GT21', 'GT23', 'UM21'}, 'stand'),
            'all three (bias-adjusted GT23)': ({'GT21', 'GT23', 'UM21'}, 'stand_adj')}
    for name, (sset, variant) in sets.items():
        # GT21 has no stand_adj; the helper falls back to 'stand'
        summ = summarise(people, {d: d in sset for d in people}, variant)
        result['variants'][name] = {'datasets_zeroed': sorted(sset), 'summary': summ, 'three_way': three_way(summ, sset)}
    # same-people comparison: for GT23 and UM21 compare their own people only
    result['standing_by_dataset'] = {ds: {q: stats([p['stand'][q] for p in people[ds].values()]) for q in QUANT} for ds in people}
    # person-level table
    rows = []
    for ds, ppl in people.items():
        for s, p in ppl.items():
            row = {'dataset': ds, 'subject': s}
            for q in QUANT:
                row[f'walk_{q}'] = p['walk'][q]
                row[f'stand_{q}'] = p['stand'][q]
                row[f'zeroed_{q}'] = p['walk'][q] - p['stand'][q]
            rows.append(row)
    write_csv(OUT / 'per_person_all_datasets.csv', rows)
    with open(OUT / 'comparison.json', 'x') as f:
        json.dump(result, f, indent=2, allow_nan=True)
        f.write('\n')
    for name, v in result['variants'].items():
        tw = v['three_way']
        print(name, {q: round(tw[q]['spread_max_minus_min'], 1) for q in ('thigh', 'shank', 'foot', 'knee', 'ankle', 'hip', 'pelvis')})
    return 0


# ------------------------------------------------------------------------------------------------ the review sheet
def cmd_sheet(args):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from contributor_tools.common.review_sheet import page
    comp = json.loads((OUT / 'comparison.json').read_text())
    people = load_people()
    out = Path(args.sheet_dir)
    out.mkdir(parents=True, exist_ok=True)
    INK, COL = '#20252B', {'GT21': '#eb6834', 'GT23': '#2a78d6', 'UM21': '#3a9d5d'}
    plt.rcParams.update({'font.size': 10, 'axes.titlesize': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                         'text.color': INK, 'axes.labelcolor': INK, 'axes.edgecolor': INK, 'legend.frameon': False})
    # figure 1: standing knee per person; a straight standing leg would read zero
    fig, ax = plt.subplots(figsize=(4.5, 3.6))
    rng = np.random.default_rng(20261127)   # recorded seed for the horizontal jitter only
    for i, ds in enumerate(('GT21', 'GT23', 'UM21')):
        v = np.array([p['stand']['knee'] for p in people[ds].values() if np.isfinite(p['stand']['knee'])])
        ax.scatter(i + rng.uniform(-0.15, 0.15, v.size), v, color=COL[ds], s=22, zorder=3)
        ax.hlines(v.mean(), i - 0.3, i + 0.3, color=INK, lw=1.5)
    ax.axhline(0, color='#7a8591', ls='--', lw=1)
    ax.set_xticks(range(3))
    ax.set_xticklabels(['GT21\nstatic', 'GT23\nstatic', 'UM21\nsit-stand pause'])
    ax.set_ylabel('Standing knee flexion (degrees)')
    fig.text(0.97, 0.01, 'dashed: zero; bar: mean', ha='right', fontsize=10, color='#5b6672')
    fig.subplots_adjust(left=0.17, right=0.97, top=0.97, bottom=0.2)
    fig.savefig(out / 'standing_knee.png', dpi=160)
    plt.close(fig)
    # figure 2: how far apart are the three dataset means in walking, before and after
    qs = ('thigh', 'shank', 'foot', 'knee', 'ankle')
    before = comp['variants']['as_published']['three_way']
    after = comp['variants']['all three (UM21 sit-to-stand proxy)']['three_way']
    fig, ax = plt.subplots(figsize=(4.5, 3.6))
    xs = np.arange(len(qs))
    ax.bar(xs - 0.2, [before[q]['spread_max_minus_min'] for q in qs], 0.38, color='#c9a227', label='as converted')
    ax.bar(xs + 0.2, [after[q]['spread_max_minus_min'] for q in qs], 0.38, color='#2a78d6', label='standing as zero')
    ax.set_xticks(xs)
    ax.set_xticklabels(['Thigh', 'Shank', 'Foot', 'Knee', 'Ankle'])
    ax.set_ylabel('Largest gap between datasets (degrees)')
    ax.legend(loc='upper left', fontsize=10)
    fig.subplots_adjust(left=0.17, right=0.97, top=0.97, bottom=0.12)
    fig.savefig(out / 'gap_all_three.png', dpi=160)
    plt.close(fig)
    # figure 3: does subtracting standing shrink person-to-person spread (it would if standing explained individual offsets)
    summ = comp['variants']['all three (UM21 sit-to-stand proxy)']['summary']
    fig, ax = plt.subplots(figsize=(4.5, 3.6))
    xs = np.arange(3)
    ax.bar(xs - 0.2, [summ[d]['knee']['published_same_people']['sd'] for d in ('GT21', 'GT23', 'UM21')], 0.38, color='#c9a227', label='as converted')
    ax.bar(xs + 0.2, [summ[d]['knee']['standing_zero']['sd'] for d in ('GT21', 'GT23', 'UM21')], 0.38, color='#2a78d6', label='standing as zero')
    ax.set_xticks(xs)
    ax.set_xticklabels(['GT21', 'GT23', 'UM21'])
    ax.set_ylabel('Spread of walking knee across people (SD, degrees)')
    ax.legend(loc='upper left', fontsize=10)
    fig.subplots_adjust(left=0.17, right=0.97, top=0.97, bottom=0.12)
    fig.savefig(out / 'person_spread.png', dpi=160)
    plt.close(fig)
    sd = comp['standing_by_dataset']
    chips = [('pass', 'GT23: static trials for 12 of 12 people'),
             ('fail', 'UM21: no static trial; only a sit-to-stand pause proxy'),
             ('pass', 'GT21: static trials for 22 of 22 people'),
             ('unchecked', 'GT23 thigh and shank: marker route, not the authors\' model axes'),
             ('unchecked', 'GT23 AB03: no thigh (model lacks pelvis markers)'),
             ('unchecked', 'GT23 AB02, AB03, AB09: walking static file missing'),
             ('unchecked', 'UM21 AB03: no steady standing pause found'),
             ('unchecked', 'UM21 proxy is not a calibration pose')]
    k = comp['variants']['all three (UM21 sit-to-stand proxy)']['three_way']['knee']['spread_max_minus_min']
    k0 = comp['variants']['as_published']['three_way']['knee']['spread_max_minus_min']
    headline = f'Standing as zero narrows the knee gap between the three datasets from {k0:.1f} to {k:.1f} degrees, mostly by moving GT21.'
    d = [f"Standing mean (min to max, people) thigh/shank/foot/knee/ankle - {ds}: " + '; '.join(
        f"{q} {sd[ds][q]['mean']:.1f} ({sd[ds][q]['min']:.1f} to {sd[ds][q]['max']:.1f}, n={sd[ds][q]['n']})" for q in ('thigh', 'shank', 'foot', 'knee', 'ankle')) for ds in ('GT21', 'GT23', 'UM21')]
    for name, v in comp['variants'].items():
        tw = v['three_way']
        d.append(f"{name}: dataset means GT21/GT23/UM21 knee " + '/'.join(f"{tw['knee']['mean'][x]:.1f}" for x in ('GT21', 'GT23', 'UM21')) +
                 '; largest gap ' + ', '.join(f"{q} {tw[q]['spread_max_minus_min']:.1f}" for q in qs))
    d += ['Walking: level 1.2 m/s, 20-35 percent of stride, filtered phase tables GT21 v1, GT23 v11, UM21 v5 (people with strides: GT21 22, GT23 11, UM21 9). Standing is subtracted per person; only people with both are in the after numbers.',
          'Hip and pelvis are not zeroed in the rule; knee = thigh minus shank and ankle = foot minus shank after zeroing.',
          'GT23 bias-adjusted variant removes the package\'s own marker-minus-model offset for level walking (C06 ledgers, normal_walk_1).',
          f'Source: {OUT}. Builder: contributor_tools/analyze_standing_all.py']
    page(out / 'index.html', title='Standing pose across GT21, GT23, UM21', ask='Does standing as zero make the three datasets agree?',
         headline=headline, chips=chips,
         figures=[(['standing_knee.png'], 'Do people stand with a straight knee?', 'One dot per person.', 'Standing knee angle per person in three datasets'),
                  (['gap_all_three.png'], 'Do the dataset means come together?', 'Bars: largest gap between the three.', 'Largest between-dataset gap before and after'),
                  (['person_spread.png'], 'Does it also tighten people within a dataset?', 'Bars: spread across people.', 'Person spread before and after')],
         not_shown=['Tasks other than level walking', 'GT23 authors\' static IK', 'Whether Plug-in Gait zeroed UM21'],
         reply='ok  |  what looks wrong', details=d)
    if args.render:
        from contributor_tools.build_review_sheet_cross_dataset import render
        render([out / 'index.html'])
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest='cmd', required=True)
    for name in ('gt23', 'um21'):
        c = sub.add_parser(name)
        c.add_argument('--subject', action='append')
        c.add_argument('--tag', default='')
    sub.add_parser('combine')
    sh = sub.add_parser('sheet')
    sh.add_argument('--sheet-dir', default=str(ROOT / 'review_sheets/A4-standing-all'))
    sh.add_argument('--render', action='store_true')
    args = p.parse_args(argv)
    return {'gt23': cmd_gt23, 'um21': cmd_um21, 'combine': cmd_combine, 'sheet': cmd_sheet}[args.cmd](args)


if __name__ == '__main__':
    raise SystemExit(main())
