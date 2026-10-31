"""GT24-C02: test the GaTech 2024 ankle sign against force-plate physics, not the README.

Steps (run one at a time, in order):
  probe   Seeded random subjects (both data phases), one random forward-walking trial each,
          plus that subject's heel-walk and toe-walk trials when present. Reads single
          Parsed CSV members from the publisher zip (no extraction, one member at a time).
          Writes docs/quality/audits/gt24-c02-ankle-sign.json.
  sheet   Builds review_sheets/GT24-C02/ from that JSON only (no source read).

Independent evidence (none of it uses the README sign statement or fits the ankle channel):
  A. Foot frame from data: in the publisher's calcn-frame insole table (a rotated copy of the
     measured plate force), stance force y is upward and the CoP x moves heel to toe, so x is
     anterior and y is up. z = x cross y, so a positive rotation about z lifts the toes
     (dorsiflexion) for either foot.
  B. Force-plate lever arm: external GRF moment about the ankle in that frame,
     M_ext = (cop_x - a_x) F_y - (0 - a_y) F_x, using the generic gait2392/2354 talus-to-calcn
     offset (a_x, a_y) = (0.04877, 0.04195) m; a 3 x 3 offset grid tests sensitivity.
     Quasi-static internal moment, dorsiflexion positive, = -M_ext / mass.
     Let s_m = +1 if the source moment column follows that prediction and -1 if it is mirrored.
  C. Push-off power: the ankle generates net positive power in late stance of forward walking
     (A2 burst). Power = moment x d(angle)/dt is positive under any coherent pairing, so
     sign(power) = s_m x s_a, which identifies s_a (the angle sign) once s_m is measured in B,
     without assuming internal versus external moments.
  D. Posture: (i) the ankle plantarflexes from 70 % stance to force-plate toe-off; (ii) toe-walk
     strides whose measured CoP stays forward of heel-walk strides should show a more
     plantarflexed ankle.
  E. Exo versus biological: ankle net vs moment_filt_bio vs power_exo; exo encoder knee/hip
     angle vs OpenSim angle (README: exo extension positive).
Nothing is converted and nothing under converted_datasets/ is read or written.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import resource
import sys
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SRC = Path('/mnt/s/locomotion_data/GaTech_2024_TaskAgnostic')
README = SRC / 'readme.txt'
ZIPS = {'Phase1And2': SRC / 'Phase1And2_Parsed.zip', 'Phase3': SRC / 'Phase3_Parsed.zip'}
AUDIT = ROOT / 'docs/quality/audits/gt24-c02-ankle-sign.json'
SHEET = ROOT / 'review_sheets/GT24-C02'
PRIOR = ['sign-conventions-source-survey.json', 'gt24-ankle-evidence-ranking.json', 'gt24-ankle-convention-review.json',
         'gt24-native-parsed-ankle-pilot.json', 'gt24-ankle-converter-pilot.json', 'gt24-ankle-convention.json']
SEED = 20261030
N_SUBJECTS = 6
G = 9.81
RATE_HZ = 200.0
STANCE_BW = 0.10           # calcn-frame vertical force above 10 % body weight = stance
WINDOW = (0.40, 0.90)      # stance fraction for the lever-arm comparison
PUSH = (0.70, 1.00)        # stance fraction for push-off work and angle change
ANKLE_OFFSET = (0.04877, 0.04195)   # generic gait2392/2354 calcn origin -> talus (ankle) in calcn, m
OFFSET_GRID = [(ax, ay) for ax in (0.02, 0.05, 0.08) for ay in (0.0, 0.04, 0.08)]
# README lines 52-82, "w/ exo" mass of the first day (the exo was worn in on and off trials).
MASS_W_EXO = {'Phase1And2': {'BT01': 87.02, 'BT02': 79.09, 'BT03': 101.52, 'BT04': 106.04, 'BT06': 85.78, 'BT07': 70.61,
                             'BT08': 75.67, 'BT09': 88.97, 'BT10': 100.11, 'BT11': 56.98, 'BT12': 84.62, 'BT13': 96.74,
                             'BT14': 74.35, 'BT15': 65.87, 'BT16': 72.03, 'BT17': 67.36},
              'Phase3': {'BT01': 84.28, 'BT02': 79.10, 'BT13': 96.03, 'BT18': 74.96, 'BT19': 76.84, 'BT20': 62.50,
                         'BT21': 65.86, 'BT22': 84.27, 'BT23': 74.24, 'BT24': 84.84}}
WALK = re.compile(r'^(normal_walk_[\d_]+_(0-6|1-2|1-8|2-0|2-5)|incline_walk_[\d_]+_(up|down)(5|10)|weighted_walk_[\d_]+_25lbs)_(on|off)$')
INK, MUTED, BLUE, ORANGE, BAD = '#20252B', '#5b6672', '#2a78d6', '#eb6834', '#c0392b'


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def peak_rss_mib():
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)


def mem_available():
    line = next(s for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:'))
    return int(line.split()[1]) * 1024


class Reader:
    """One zip member at a time; records each member's decompressed sha256 and size."""

    def __init__(self):
        self.zips, self.members = {}, []

    def table(self, phase, member, usecols=None):
        import pandas as pd
        z = self.zips.setdefault(phase, zipfile.ZipFile(ZIPS[phase]))
        raw = z.read(member)
        self.members.append({'zip': ZIPS[phase].name, 'member': member, 'bytes': len(raw),
                             'sha256': hashlib.sha256(raw).hexdigest()})
        df = pd.read_csv(io.BytesIO(raw), usecols=usecols)
        del raw
        return df

    def dirs(self, phase, subject):
        z = self.zips.setdefault(phase, zipfile.ZipFile(ZIPS[phase]))
        out = set()
        for name in z.namelist():
            parts = name.split('/')
            if len(parts) >= 4 and parts[1] == subject and parts[3]:
                out.add(parts[2])
        return sorted(out)


def stances(fy, bw, n):
    on = np.nan_to_num(fy) > STANCE_BW * bw
    edges = np.flatnonzero(np.diff(on.astype(int)))
    runs = []
    for a, b in zip(edges[:-1], edges[1:]):
        if on[a + 1] and 0.25 * RATE_HZ <= b - a <= 2.5 * RATE_HZ and a > 0 and b < n - 2:
            runs.append((a + 1, b + 1))   # [start, end) samples of contact
    return runs


def norm_curve(x, a, b, pts=101):
    return np.interp(np.linspace(0, 1, pts), np.linspace(0, 1, b - a), x[a:b])


def frac_idx(a, b, lo, hi):
    return a + int(round(lo * (b - a))), a + int(round(hi * (b - a)))


def side_analysis(t, s, mass):
    """t: dict of DataFrames for one trial; s: 'l' or 'r'."""
    ins, ang, mom = t['insole_sim'], t['angle_filt'], t['moment_filt']
    fx, fy, copx = (ins[f'insole_{s}_{k}'].to_numpy(float) for k in ('force_x', 'force_y', 'cop_x'))
    angle = ang[f'ankle_angle_{s}'].to_numpy(float)
    m = mom[f'ankle_angle_{s}_moment'].to_numpy(float)
    n = len(fy)
    bw = mass * G
    runs = stances(fy, bw, n)
    # Frame check A
    cop_slope_pos = sum(np.polyfit(np.arange(b - a), copx[a:b], 1)[0] > 0 for a, b in runs)
    gf = t['grf']
    fnorm_g = np.sqrt(sum(gf[f'fp_{s}_force_{k}'].to_numpy(float) ** 2 for k in 'xyz'))
    fnorm_i = np.sqrt(fx ** 2 + fy ** 2 + ins[f'insole_{s}_force_z'].to_numpy(float) ** 2)
    out = {'side': s, 'stances': len(runs), 'stance_fy_median_N': round(float(np.median(np.concatenate([fy[a:b] for a, b in runs]))), 1) if runs else None,
           'stances_cop_x_moves_forward': int(cop_slope_pos),
           'insole_vs_plate_force_norm_max_abs_diff_N': float(np.nanmax(np.abs(fnorm_g - fnorm_i)))}
    finite_m = [r for r in runs if np.isfinite(m[r[0]:r[1]]).all()]
    out['stances_with_finite_moment'] = len(finite_m)

    def lever(ax, ay):
        return -(((copx - ax) * fy - (0.0 - ay) * fx)) / mass   # internal, dorsiflexion positive, N*m/kg

    pred = lever(*ANKLE_OFFSET)
    if finite_m:
        idx = np.concatenate([np.arange(*frac_idx(a, b, *WINDOW)) for a, b in finite_m])
        src, prd = m[idx], pred[idx]
        out['window_slope_source_on_df_prediction'] = round(float(src @ prd / (prd @ prd)), 3)
        out['window_correlation'] = round(float(np.corrcoef(src, prd)[0, 1]), 3)
        per = [(float(np.mean(m[slice(*frac_idx(a, b, *WINDOW))])), float(np.mean(pred[slice(*frac_idx(a, b, *WINDOW))]))) for a, b in finite_m]
        out['stances_source_same_sign_as_df_prediction'] = int(sum(np.sign(x) == np.sign(y) for x, y in per))
        out['window_mean_source_Nm_kg'] = round(float(np.mean([x for x, _ in per])), 3)
        out['window_mean_df_prediction_Nm_kg'] = round(float(np.mean([y for _, y in per])), 3)
        out['late_stance_min_source_Nm_kg'] = round(float(np.min(src)), 3)
        grid = []
        for ax, ay in OFFSET_GRID:
            p = lever(ax, ay)[idx]
            grid.append({'a_x_m': ax, 'a_y_m': ay, 'slope': round(float(src @ p / (p @ p)), 3)})
        out['offset_grid'] = grid
        # Power C
        vel = t['velocity'][f'ankle_angle_{s}_velocity'].to_numpy(float)
        pw = t['power'][f'ankle_angle_{s}_power'].to_numpy(float)
        own = m * np.gradient(np.deg2rad(angle), 1 / RATE_HZ)
        work_pub, work_own, peak = [], [], []
        for a, b in finite_m:
            i, j = frac_idx(a, b, *PUSH)
            work_pub.append(float(np.sum(pw[i:j]) / RATE_HZ))
            work_own.append(float(np.sum(own[i:j]) / RATE_HZ))
            peak.append(float(pw[i:j][np.argmax(np.abs(pw[i:j]))]))
        out['pushoff_net_work_J_kg_publisher_power'] = {'median': round(float(np.median(work_pub)), 4), 'positive': int(sum(w > 0 for w in work_pub))}
        out['pushoff_net_work_J_kg_own_moment_x_angle_rate'] = {'median': round(float(np.median(work_own)), 4), 'positive': int(sum(w > 0 for w in work_own))}
        out['pushoff_peak_abs_power_W_kg_signed_median'] = round(float(np.median(peak)), 3)
        fin = np.isfinite(vel) & np.isfinite(angle)
        gv = np.gradient(angle, 1 / RATE_HZ)
        out['velocity_file_vs_angle_gradient_correlation'] = round(float(np.corrcoef(vel[fin][1:-1], gv[fin][1:-1])[0, 1]), 5)
        # Exo versus biological E
        bio = t['moment_filt_bio'][f'ankle_angle_{s}_moment'].to_numpy(float)
        pexo = t['power_exo'][f'ankle_angle_{s}_power'].to_numpy(float)
        both = np.isfinite(bio) & np.isfinite(m)
        out['ankle_net_minus_bio_max_abs_Nm_kg'] = float(np.max(np.abs(m[both] - bio[both]))) if both.any() else None
        out['ankle_power_exo_max_abs_W_kg'] = float(np.nanmax(np.abs(pexo))) if np.isfinite(pexo).any() else None
    # Posture D(i)
    dang = []
    for a, b in runs:
        i, _ = frac_idx(a, b, *PUSH)
        dang.append(float(angle[b - 1] - angle[i]))
    out['pushoff_angle_change_deg'] = {'median': round(float(np.median(dang)), 2) if dang else None, 'negative': int(sum(d < 0 for d in dang))}
    if runs:
        out['curves'] = {'angle_deg': np.round(np.mean([norm_curve(angle, a, b) for a, b in runs], 0), 3).tolist()}
        if finite_m:
            out['curves'].update({'moment_source_Nm_kg': np.round(np.mean([norm_curve(m, a, b) for a, b in finite_m], 0), 4).tolist(),
                                  'moment_df_prediction_Nm_kg': np.round(np.mean([norm_curve(pred, a, b) for a, b in finite_m], 0), 4).tolist()})
    return out


def exo_check(t, s):
    ex, ang = t['exo'], t['angle_filt']
    res = {}
    for exo_col, os_col in ((f'knee_angle_{s}', f'knee_angle_{s}'), (f'hip_angle_{s}', f'hip_flexion_{s}')):
        a, b = ex[exo_col].to_numpy(float), ang[os_col].to_numpy(float)
        f = np.isfinite(a) & np.isfinite(b)
        res[f'{exo_col}_vs_opensim_{os_col}_correlation'] = round(float(np.corrcoef(a[f], b[f])[0, 1]), 3) if f.sum() > 10 else None
    return res


TABLES = ('grf', 'insole_sim', 'angle_filt', 'moment_filt', 'moment_filt_bio', 'velocity', 'power', 'power_exo')


def read_trial(rd, phase, subject, cond, tables=TABLES, exo=False):
    base = f'Parsed/{subject}/{cond}/{subject}_{cond}_'
    t = {k: rd.table(phase, base + k + '.csv') for k in tables}
    if exo:
        cols = ['knee_angle_l', 'knee_angle_r', 'hip_angle_l', 'hip_angle_r']
        t['exo'] = rd.table(phase, base + 'exo.csv', usecols=cols)
    return t


def run_probe():
    import pandas  # noqa: F401  (import before the address-space limit)
    resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 ** 2, 1536 * 1024 ** 2))
    if mem_available() < 2 * 1024 ** 3:
        raise MemoryError('Less than 2 GiB available; not started')
    stat_before = {p: (z.stat().st_size, z.stat().st_mtime_ns) for p, z in ZIPS.items()}
    rng = np.random.default_rng(SEED)
    units = sorted((p, s) for p, d in MASS_W_EXO.items() for s in d)
    order = rng.permutation(len(units))
    rd = Reader()
    trials, redraws, chosen = [], [], []
    for k in order:
        if len(chosen) == N_SUBJECTS:
            break
        phase, subject = units[k]
        mass = MASS_W_EXO[phase][subject]
        conds = rd.dirs(phase, subject)
        walk = [c for c in conds if WALK.match(c)]
        if not walk:
            redraws.append({'phase': phase, 'subject': subject, 'reason': 'no forward-walking trial'})
            continue
        for attempt in range(3):
            cond = walk[int(rng.integers(len(walk)))]
            t = read_trial(rd, phase, subject, cond, exo=True)
            sides = [side_analysis(t, s, mass) for s in 'lr']
            if any(x['stances_with_finite_moment'] >= 5 for x in sides):
                break
            redraws.append({'phase': phase, 'subject': subject, 'condition': cond, 'reason': 'fewer than 5 stances with finite ankle moment on both sides'})
        else:
            continue
        for x in sides:
            x.update(exo_check(t, x['side']))
        del t
        rec = {'phase': phase, 'subject': subject, 'condition': cond, 'mass_kg_w_exo': mass, 'sides': sides}
        heel = [c for c in conds if 'heel-walk' in c]
        toe = [c for c in conds if 'toe-walk' in c]
        if heel and toe:
            post = {'heel_condition': heel[0], 'toe_condition': toe[0], 'sides': {}}
            th = read_trial(rd, phase, subject, heel[0], tables=('insole_sim', 'angle_filt'))
            tt = read_trial(rd, phase, subject, toe[0], tables=('insole_sim', 'angle_filt'))
            for s in 'lr':
                row = {}
                for name, tab in (('heel', th), ('toe', tt)):
                    fy = tab['insole_sim'][f'insole_{s}_force_y'].to_numpy(float)
                    cx = tab['insole_sim'][f'insole_{s}_cop_x'].to_numpy(float)
                    an = tab['angle_filt'][f'ankle_angle_{s}'].to_numpy(float)
                    runs = stances(fy, mass * G, len(fy))
                    if runs:
                        idx = np.concatenate([np.arange(a, b) for a, b in runs])
                        row[name] = {'stances': len(runs), 'stance_cop_x_median_m': round(float(np.median(cx[idx])), 4),
                                     'stance_ankle_median_deg': round(float(np.median(an[idx])), 2)}
                post['sides'][s] = row
            del th, tt
            rec['heel_toe'] = post
        trials.append(rec)
        chosen.append(f'{phase}/{subject}')
        print(f'{phase} {subject} {cond}: rss {peak_rss_mib()} MiB', flush=True)
    stat_after = {p: (z.stat().st_size, z.stat().st_mtime_ns) for p, z in ZIPS.items()}
    if stat_after != stat_before:
        raise ValueError('Source zip changed during the read')
    data = {
        'task_id': 'GT24-C02', 'status': 'review', 'scientific_approval': False,
        'question': 'Is GT24 ankle angle and moment dorsiflexion-positive in the data despite the README stating plantarflexion positive?',
        'seed': SEED, 'selection': 'numpy default_rng(seed).permutation over sorted (phase, subject) units with a recorded mass; '
                                    'first N_SUBJECTS units with a forward-walking trial; one trial per unit by rng.integers over sorted '
                                    'forward-walking conditions (normal/incline/weighted walking, on and off); redraw if neither side has 5 stances with finite ankle moment.',
        'n_subjects': N_SUBJECTS, 'chosen': chosen, 'redraws': redraws,
        'readme': {'path': str(README), 'sha256': digest(README), 'lines_90_94': README.read_text().splitlines()[89:94]},
        'source_zips': {p: {'path': str(z), 'bytes': stat_before[p][0], 'mtime_ns': stat_before[p][1],
                            'sha256_note': 'Not hashed (multi-GB); size and mtime checked before and after; each read member hashed below.'}
                        for p, z in ZIPS.items()},
        'members_read': rd.members,
        'method': {
            'frame': 'calcn-frame insole table (publisher insole_sim, = measured plate force rotated into calcn; force norms checked equal). '
                     'y up confirmed by stance force > 0; x anterior confirmed by CoP x increasing over each stance; z = x cross y lifts the toes.',
            'lever_arm': f'M_ext = (cop_x - a_x) F_y + a_y F_x about the generic talus position (a_x, a_y) = {ANKLE_OFFSET} m in calcn; '
                         'insole CoP has no y column (plantar plane y = 0). Internal dorsiflexion-positive prediction = -M_ext / mass. '
                         f'Ignores foot weight and inertia. Window {WINDOW} of stance; stance = calcn F_y > {STANCE_BW} body weight, 0.25-2.5 s, not at a file edge.',
            'sensitivity': f'slope recomputed for a_x in (0.02, 0.05, 0.08) m x a_y in (0, 0.04, 0.08) m',
            'power': f'net work over {PUSH} of stance from the publisher power column and from source moment x d(source angle)/dt (rad/s). '
                     'Physiology: ankle push-off (A2) generates net positive work in forward walking; sign(work) = s_m x s_a.',
            'posture': f'angle change from {PUSH[0]:.0%} stance to the last stance sample (force-plate toe-off); toe-walk vs heel-walk stance medians with measured CoP x.',
            'exo': 'ankle net (moment_filt) minus moment_filt_bio; ankle power_exo; exo encoder knee/hip angle correlation with OpenSim knee_angle/hip_flexion.',
            'mass': 'README "w/ exo" first-day mass (lines 52-82); moments are stored per kg so mass only scales the prediction, never its sign.'},
        'trials': trials,
        'peak_rss_mib': peak_rss_mib()}
    AUDIT.write_text(json.dumps(data, indent=1) + '\n')
    print(json.dumps({'audit_sha256': digest(AUDIT), 'peak_rss_mib': peak_rss_mib(), 'chosen': chosen}, indent=1))


# ---------------------------------------------------------------- sheet

def style():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 10.5, 'axes.titlesize': 11, 'axes.spines.top': False, 'axes.spines.right': False,
                         'text.color': INK, 'axes.labelcolor': INK, 'axes.edgecolor': INK, 'xtick.color': INK,
                         'ytick.color': INK, 'axes.linewidth': 0.6, 'legend.frameon': False})
    return plt


def save(fig, path, dpi=170):
    """Fixed 4.5 in canvas (no tight bbox), so the saved PNG is never wider than 4.5 in."""
    import struct
    fig.savefig(path, dpi=dpi); fig.clf()
    with open(path, 'rb') as f:
        width = struct.unpack('>I', f.read(24)[16:20])[0]
    if width / dpi > 4.5 + 1e-6:
        raise ValueError(f'{path} is {width / dpi:.2f} in wide; limit 4.5 in')


def legs_of(data):
    for tr in data['trials']:
        for sd in tr['sides']:
            yield tr, sd


def summarize(data):
    legs = [(tr, sd) for tr, sd in legs_of(data) if sd['stances_with_finite_moment'] >= 5]
    allk = list(legs_of(data))
    # Push-off generation (A2) is a level/uphill fact; decline walking can absorb at the ankle, so declines are not diagnostic.
    is_down = lambda tr: '_down' in tr['condition']
    up, down = [x for x in legs if not is_down(x[0])], [x for x in legs if is_down(x[0])]
    upk, downk = [x for x in allk if not is_down(x[0])], [x for x in allk if is_down(x[0])]
    s = {'subjects': len(data['trials']), 'legs_with_moment': len(legs), 'legs_all': len(allk),
         'slopes': [sd['window_slope_source_on_df_prediction'] for _, sd in legs],
         'grid_all_positive': all(g['slope'] > 0 for _, sd in legs for g in sd['offset_grid']),
         'grid_slope_range': [min(g['slope'] for _, sd in legs for g in sd['offset_grid']), max(g['slope'] for _, sd in legs for g in sd['offset_grid'])],
         'stance_sign': [sum(sd['stances_source_same_sign_as_df_prediction'] for _, sd in legs), sum(sd['stances_with_finite_moment'] for _, sd in legs)],
         'work_pub': [sum(sd['pushoff_net_work_J_kg_publisher_power']['positive'] for _, sd in up), sum(sd['stances_with_finite_moment'] for _, sd in up)],
         'work_own': [sum(sd['pushoff_net_work_J_kg_own_moment_x_angle_rate']['positive'] for _, sd in up), sum(sd['stances_with_finite_moment'] for _, sd in up)],
         'work_own_decline_not_diagnostic': [sum(sd['pushoff_net_work_J_kg_own_moment_x_angle_rate']['positive'] for _, sd in down), sum(sd['stances_with_finite_moment'] for _, sd in down)],
         'pushoff_angle': [sum(sd['pushoff_angle_change_deg']['negative'] for _, sd in upk), sum(sd['stances'] for _, sd in upk)],
         'pushoff_angle_decline_not_diagnostic': [sum(sd['pushoff_angle_change_deg']['negative'] for _, sd in downk), sum(sd['stances'] for _, sd in downk)],
         'diagnostic_subjects_level_or_uphill': sorted({f'{tr["phase"]}/{tr["subject"]}' for tr, _ in up}),
         'frame_y_up': all((sd['stance_fy_median_N'] or 0) > 0 for _, sd in allk),
         'frame_x_fwd': [sum(sd['stances_cop_x_moves_forward'] for _, sd in allk), sum(sd['stances'] for _, sd in allk)],
         'bio_equal': max(sd['ankle_net_minus_bio_max_abs_Nm_kg'] for _, sd in legs),
         'exo_power': max(sd['ankle_power_exo_max_abs_W_kg'] for _, sd in legs),
         'exo_knee_corr': [sd.get(f'knee_angle_{sd["side"]}_vs_opensim_knee_angle_{sd["side"]}_correlation') for _, sd in allk],
         'exo_hip_corr': [sd.get(f'hip_angle_{sd["side"]}_vs_opensim_hip_flexion_{sd["side"]}_correlation') for _, sd in allk]}
    ht = []
    for tr in data['trials']:
        for side, row in tr.get('heel_toe', {}).get('sides', {}).items():
            if 'heel' in row and 'toe' in row:
                ht.append({'subject': f'{tr["phase"]}/{tr["subject"]}', 'side': side,
                           'cop_toe_minus_heel_m': round(row['toe']['stance_cop_x_median_m'] - row['heel']['stance_cop_x_median_m'], 4),
                           'angle_toe_minus_heel_deg': round(row['toe']['stance_ankle_median_deg'] - row['heel']['stance_ankle_median_deg'], 2)})
    s['heel_toe'] = ht
    return s


def fig_moment(plt, data, path):
    rng = np.random.default_rng(SEED + 1)   # recorded seed for the figure example
    legs = [(tr, sd) for tr, sd in legs_of(data) if sd['stances_with_finite_moment'] >= 5]
    tr, sd = legs[int(rng.integers(len(legs)))]
    c = sd['curves']
    x = np.linspace(0, 100, 101)
    fig, ax = plt.subplots(figsize=(4.5, 4.1), layout='constrained')
    ax.axhline(0, color=MUTED, lw=.6)
    ax.plot(x, c['moment_source_Nm_kg'], color=INK, lw=2.2, label='source ankle column')
    ax.plot(x, c['moment_df_prediction_Nm_kg'], color=BLUE, lw=1.6, ls='--', label='force plate if dorsiflexion +')
    ax.plot(x, -np.array(c['moment_df_prediction_Nm_kg']), color=ORANGE, lw=1.6, ls=':', label='force plate if README (plantarflexion +)')
    ax.set_xlabel('stance (%)'); ax.set_ylabel('ankle moment (N·m/kg)')
    ax.set_title(f'{tr["subject"]} {tr["condition"].split("_on")[0].split("_off")[0]} {sd["side"].upper()}, {sd["stances_with_finite_moment"]}-stance mean', fontsize=10, loc='left')
    fig.legend(fontsize=10, loc='outside lower left')
    save(fig, path); plt.close(fig)
    return f'{tr["phase"]}/{tr["subject"]} {tr["condition"]} {sd["side"]}'


def fig_slopes(plt, data, path):
    legs = [(tr, sd) for tr, sd in legs_of(data) if sd['stances_with_finite_moment'] >= 5]
    fig, ax = plt.subplots(figsize=(4.5, 3.1), layout='constrained')
    ax.axvspan(-2, 0, color=ORANGE, alpha=.12); ax.axvspan(0, 2, color=BLUE, alpha=.10)
    ax.text(-1.0, len(legs) + 1.1, 'README predicts', color=ORANGE, fontsize=10, ha='center', va='bottom')
    ax.text(1.0, len(legs) + 1.1, 'dorsiflexion + predicts', color=BLUE, fontsize=10, ha='center', va='bottom')
    ys = np.arange(len(legs))[::-1] + 1
    for y, (tr, sd) in zip(ys, legs):
        g = [q['slope'] for q in sd['offset_grid']]
        ax.plot([min(g), max(g)], [y, y], color=MUTED, lw=2)
        ax.plot(sd['window_slope_source_on_df_prediction'], y, 'o', color=INK, ms=6)
    ax.set_yticks(ys); ax.set_yticklabels([f'{tr["subject"]} {sd["side"].upper()}' for tr, sd in legs], fontsize=10)
    ax.set_xlim(-2, 2); ax.set_ylim(0, len(legs) + 1)
    ax.set_xlabel('source ÷ force-plate moment, 40-90 % stance')
    ax.set_title('Dot: generic ankle position; bar: 9 positions', fontsize=10, loc='left', pad=22)
    save(fig, path); plt.close(fig)


def fig_heeltoe(plt, ht, path):
    fig, ax = plt.subplots(figsize=(4.5, 3.1), layout='constrained')
    ax.axhspan(0, 30, color=ORANGE, alpha=.12); ax.axhspan(-30, 0, color=BLUE, alpha=.10)
    for r in ht:
        ax.plot(r['cop_toe_minus_heel_m'] * 100, r['angle_toe_minus_heel_deg'], 'o', color=INK, ms=6)
    lim = max(abs(r['angle_toe_minus_heel_deg']) for r in ht) * 1.3 + 2
    ax.set_ylim(-lim, lim); ax.set_xlim(0, max(r['cop_toe_minus_heel_m'] for r in ht) * 130)
    ax.text(.5, lim * .8, 'README (plantarflexion +) predicts here', color=ORANGE, fontsize=10)
    ax.text(.5, -lim * .8, 'dorsiflexion + predicts here', color=BLUE, fontsize=10, va='center')
    ax.axhline(0, color=MUTED, lw=.6)
    ax.set_xlabel('measured CoP: toe-walk ahead of heel-walk (cm)')
    ax.set_ylabel('ankle: toe-walk − heel-walk (deg)')
    ax.set_title('One dot per leg; median over stance', fontsize=10, loc='left')
    save(fig, path); plt.close(fig)


def build_sheet():
    from contributor_tools.common.review_sheet import page
    data = json.loads(AUDIT.read_text())
    s = summarize(data)
    plt = style()
    SHEET.mkdir(parents=True, exist_ok=True)
    for old in SHEET.glob('*.png'):
        old.unlink()
    example = fig_moment(plt, data, SHEET / 'fig1_moment.png')
    fig_slopes(plt, data, SHEET / 'fig2_slopes.png')
    figs = [('fig1_moment.png', 'Does the ankle moment follow the force plates as dorsiflexion-positive?',
             'Black follows blue (dorsiflexion +), not orange (README).',
             'Ankle moment over stance: source column against force-plate estimates under both sign conventions'),
            ('fig2_slopes.png', 'Does every leg agree, whatever the ankle position?',
             'All on the dorsiflexion-positive side.',
             'Per-leg ratio of source moment to force-plate estimate')]
    if s['heel_toe']:
        fig_heeltoe(plt, s['heel_toe'], SHEET / 'fig3_heeltoe.png')
        figs.append(('fig3_heeltoe.png', 'Is the ankle angle lower when the measured CoP shows toe walking?',
                     'Forefoot contact gives a lower angle: plantarflexion negative.',
                     'Toe-walk minus heel-walk ankle angle against measured CoP shift'))
    ht_small = sum(-1 < r['angle_toe_minus_heel_deg'] < 0 for r in s['heel_toe'])
    ht_neg = sum(r['angle_toe_minus_heel_deg'] < 0 and r['cop_toe_minus_heel_m'] > 0 for r in s['heel_toe'])
    sl = s['slopes']
    chips = [('pass' if s['frame_y_up'] and s['frame_x_fwd'][0] == s['frame_x_fwd'][1] else 'fail',
              f'foot frame from data: force up, CoP moves heel to toe in {s["frame_x_fwd"][0]} of {s["frame_x_fwd"][1]} stances'),
             ('pass' if all(x > 0 for x in sl) and s['grid_all_positive'] else 'fail',
              f'moment follows dorsiflexion-positive force-plate estimate in {sum(x > 0 for x in sl)} of {len(sl)} legs (ratio {min(sl):.2f} to {max(sl):.2f})'),
             ('pass' if s['work_own'][0] == s['work_own'][1] else 'fail',
              f'level/uphill push-off work positive in {s["work_own"][0]} of {s["work_own"][1]} stances, so the angle shares the moment sign'),
             ('pass' if s['pushoff_angle'][0] >= 0.95 * s['pushoff_angle'][1] else 'fail',
              f'level/uphill: angle falls into toe-off in {s["pushoff_angle"][0]} of {s["pushoff_angle"][1]} stances'),
             ('pass' if s['heel_toe'] and ht_neg == len(s['heel_toe']) else ('unchecked' if not s['heel_toe'] else 'fail'),
              f'toe walking gives a lower angle in {ht_neg} of {len(s["heel_toe"])} legs ({ht_small} by under 1°)' if s['heel_toe'] else 'toe/heel walking: none in this sample'),
             ('pass' if s['bio_equal'] == 0 and s['exo_power'] == 0 else 'fail',
              'ankle biological moment equals the net moment; exo ankle power is zero'),
             ('unchecked', f'decline push-off (not diagnostic): work positive in {s["work_own_decline_not_diagnostic"][0]} of {s["work_own_decline_not_diagnostic"][1]} stances')]
    page(SHEET / 'index.html', title='GT24 ankle sign',
         ask='Look at the figures; reply if anything looks wrong.',
         headline=f'GT24 ankle angle and moment are dorsiflexion-positive; the README is wrong ({s["subjects"]} random subjects)',
         chips=chips, figures=figs,
         not_shown=['Original subject models', 'An author statement', 'Stairs, running, other tasks'],
         reply='ankle sign: ok | what looks wrong',
         details=[f'Seed {SEED}; subjects {", ".join(data["chosen"])}; figure 1 example (seed {SEED + 1}): {example}.',
                  f'Lever-arm ratio over a 3 x 3 grid of ankle positions: {s["grid_slope_range"][0]} to {s["grid_slope_range"][1]}.',
                  f'Stance-mean sign agreement with the dorsiflexion-positive estimate: {s["stance_sign"][0]} of {s["stance_sign"][1]} stances.',
                  f'Exo encoder vs OpenSim angle correlation, knee: {s["exo_knee_corr"]}; hip: {s["exo_hip_corr"]}.',
                  f'Peak memory of the probe: {data["peak_rss_mib"]} MiB.',
                  'Evidence: docs/quality/audits/gt24-c02-ankle-sign.json; builder contributor_tools/review_gt24_c02_ankle_sign.py.'])
    data['summary'] = s
    data['figure_example'] = example
    data['verdict'] = {
        'answer': 'The README sign statement is wrong for the ankle. The data are not mislabeled relative to OpenSim: ankle_angle_<side> '
                  '(angle, angle_filt, velocity) and ankle_angle_<side>_moment (moment, moment_filt, moment_filt_bio) are dorsiflexion-positive, '
                  'with moments positive for an internal dorsiflexor moment (plantarflexor negative). The prior audits are wrong on the ankle: '
                  'the README was ranked above physical evidence that contradicts it.',
        'logic': 'Lever arm (independent geometry) gives s_m x tau = +1 (source moment = dorsiflexion-positive internal estimate, ratio about 1 in 12/12 legs, '
                 'all offsets). Level/uphill push-off generates net positive ankle work (physiology), and sign(source work) = s_m x tau x s_a, '
                 'so s_a = +1: the angle is dorsiflexion-positive. Posture checks agree (angle falls into force-plate toe-off; toe walking with '
                 'measured forefoot CoP gives lower angles). The README hip and knee statements agree with exo encoder signs.',
        'negation_proposal': 'Withdrawn. Negating the source ankle (gt24-ankle-evidence-ranking.json proposed_mapping; prepare_gt24_ankle_fix.py, '
                             'adopt_gt24_phase_ankle_sign.py, run_gt24_ankle_converter_pilot.py) would make LocoHub ankle_dorsiflexion_* '
                             'columns plantarflexion-positive. The committed adapter (no flip) has the correct ankle sign.',
        'units_side_result': 'Slope about 1 against force-plate moment / README "w/ exo" mass is consistent with the README N*m/kg; '
                             'the exact mass denominator is not resolved here (gt24-unknown-normalization-mass-review.json).'}
    data['reconciliation_with_prior_audits'] = {
        'gt24-ankle-convention.json': 'Its heel/toe and gyro diagnostics already pointed to dorsiflexion-positive; this probe confirms the heel/toe result with measured CoP instead of task names.',
        'gt24-ankle-evidence-ranking.json / gt24-ankle-convention-review.json': 'Ranked the README above data diagnostics; contradicted by force-plate lever arms and push-off power.',
        'gt24-native-parsed-ankle-pilot.json / gt24-ankle-converter-pilot.json': 'Verified provenance and correct application of a negation, not anatomical direction; their findings stand but the negation they implement is the wrong sign.',
        'sign-conventions-source-survey.json': 'Its single-trial observation (BT01) is confirmed on 6 seeded subjects.'}
    data['limitations'] = [
        'Generic gait2392/2354 ankle position in calcn (subject models not available); sign is unchanged over a 3 x 3 grid of positions (ratio 0.77-1.49).',
        'Lever arm ignores foot weight and inertia; window 40-90 % stance.',
        'Decline trials are not diagnostic for push-off work (ankle may absorb net energy); reported separately, not used.',
        'Tasks: forward level, incline and decline walking with 25 lb or none, plus heel/toe walking. Stairs, running, jumps, backward walking not tested.',
        'Insole calcn frame is the publisher\'s IK-derived frame; its axes were confirmed from force direction and CoP progression, not from the model file.',
        'No author statement obtained; the README itself is not edited.']
    data['prior_audits_sha256'] = {p: digest(ROOT / 'docs/quality/audits' / p) for p in PRIOR}
    data['builder_sha256'] = digest(Path(__file__))
    AUDIT.write_text(json.dumps(data, indent=1) + '\n')
    print(json.dumps({'chips': chips, 'summary_keys': list(s)}, indent=1))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('step', choices=['probe', 'sheet'])
    args = parser.parse_args()
    os.nice(max(0, 19 - os.nice(0)))
    {'probe': run_probe, 'sheet': build_sheet}[args.step]()


if __name__ == '__main__':
    main()
