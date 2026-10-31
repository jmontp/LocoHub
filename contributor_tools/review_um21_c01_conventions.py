"""UM21-C01: treadmill sign/unit/frame evidence probe and its local review sheets.

`probe` reads a few channels from a handful of Streaming.mat treadmill trials,
one trial at a time (markers, joint angles, sagittal moments/powers, one
force plate), and writes docs/quality/audits/um21-c01-source-probe.json.
`sheet` builds review_sheets/UM21-C01/ (verification plus decision D-UM21-C01-2)
and review_sheets/D-UM21-C01-1/ (thigh/shank recipe decision) from that file.

Marker-derived angles are an independent geometric check of signs and recipes,
not a replacement for model output. Nothing is converted, no offset is applied,
and no input file is changed. Launches nothing.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
import hashlib
import json
from pathlib import Path
import random
import resource
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SOURCE = ROOT / 'contributor_tools/conversion_scripts/Umich_2021/Streaming.mat'
SOURCE_RECEIPT = ROOT / 'converted_datasets/reconversion_v2/um21_tread_corrected_20261020/conversion_summary.json'
PROBE = ROOT / 'docs/quality/audits/um21-c01-source-probe.json'
SHEETS = ROOT / 'review_sheets'
SEED = 20261028
N_RANDOM = 4
LEAD = ('AB02', 'i5')          # coordinator lead: hip flexion never in extension
ANOMALY = [('AB07', 'i10'), ('AB08', 'i0')]  # known ankle anomalies (ankle source review)
SCREENS_DEG = (45, 60, 90)  # reporting screens only; the full treadmill ankle scan maximum is +37.2 deg
RATE_HZ = 100.0
PLATE_RATE_HZ = 1000.0
INK, MUTED, REF, BLUE, ORANGE, BAD = '#20252B', '#5b6672', '#999999', '#2a78d6', '#eb6834', '#c0392b'
SLOPE = {'d10': 'decline 10°', 'd5': 'decline 5°', 'i0': 'level', 'i5': 'incline 5°', 'i10': 'incline 10°'}


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def mem_available():
    line = next(s for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:'))
    return int(line.split()[1]) * 1024


# ---------------------------------------------------------------- probe

def corr(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    return float(np.corrcoef(a[ok], b[ok])[0, 1])


def stats(diff):
    return {'mean_deg': float(np.nanmean(diff)), 'median_deg': float(np.nanmedian(diff)), 'sd_deg': float(np.nanstd(diff)),
            'abs_p95_deg': float(np.nanpercentile(np.abs(diff), 95)), 'finite_frames': int(np.isfinite(diff).sum())}


def right_strides(rhs, length):
    """Consecutive right heel-strike pairs, 0.8-1.6 s, fully inside the record (frames are 1-based)."""
    return [(int(a), int(b)) for a, b in zip(rhs[:-1], rhs[1:]) if 80 <= b - a <= 160 and a >= 1 and b <= length]


def probe_trial(handle, subject, condition, keep_stride=None):
    trial = handle[f'Streaming/{subject}/Tread/{condition}']
    def marker(name):  # frames where the camera flag e is not 1 become NaN
        m = trial['markers'][name][...]
        xyz = m[:3, :].copy()
        xyz[:, m[3] != 1] = np.nan
        return xyz
    angle = lambda n: trial['jointAngles'][n][...]
    asi = (marker('LASI') + marker('RASI')) / 2
    psi = (marker('LPSI') + marker('RPSI')) / 2
    d = asi - psi
    # Anterior = mean horizontal PSIS->ASIS direction; global Z is vertical (checked below).
    ant = np.nanmean(d[:2], 1)
    ant /= np.linalg.norm(ant)
    tilt_markers = np.degrees(np.arctan2(psi[2] - asi[2], d[0] * ant[0] + d[1] * ant[1]))  # + when PSIS higher

    def sagittal(v):  # forward-positive angle of a proximal->distal vector from straight down
        return np.degrees(np.arctan2(v[0] * ant[0] + v[1] * ant[1], -v[2]))

    rp, lp = angle('RPelvisAngles'), angle('LPelvisAngles')
    out = {'subject': subject, 'condition': condition, 'frames': int(rp.shape[1]),
           'pelvis_marker_height_m': float(np.nanmean(asi[2])), 'anterior_axis_xy': ant.round(4).tolist(),
           'pelvis_component1_minus_marker_tilt': stats(rp[0] - tilt_markers),
           'pelvis_component1_vs_marker_tilt_corr': corr(rp[0], tilt_markers),
           'pelvis_component1_mean_deg': float(np.nanmean(rp[0])),
           'right_minus_left_pelvis_max_abs_deg': [float(np.nanmax(np.abs(rp[k] - lp[k]))) for k in range(3)],
           'sides': {}}
    curves = {}
    for side in 'RL':
        knee_c = (marker(side + 'KNE') + marker(side + 'KNEM')) / 2
        ankle_c = (marker(side + 'ANK') + marker(side + 'ANKM')) / 2
        thigh_m, shank_m = sagittal(knee_c - marker(side + 'GT')), sagittal(ankle_c - knee_c)
        hip, knee = angle(side + 'HipAngles')[0], angle(side + 'KneeAngles')[0]
        pelvis = rp[0]
        recipes = {'author_hip_minus_pelvis': (hip - pelvis, hip - pelvis - knee),
                   'producer_pelvis_plus_hip': (pelvis + hip, pelvis + hip - knee)}
        s = {'hip_component1_p1_p99_deg': np.nanpercentile(hip, [1, 99]).round(2).tolist(),
             'marker_thigh_p1_p99_deg': np.nanpercentile(thigh_m, [1, 99]).round(2).tolist(),
             'ankle_component1_p1_p99_deg': np.nanpercentile(angle(side + 'AnkleAngles')[0], [1, 99]).round(2).tolist()}
        for name, (thigh, shank) in recipes.items():
            s[name] = {'thigh_minus_marker': stats(thigh - thigh_m), 'shank_minus_marker': stats(shank - shank_m)}
        # Sagittal kinetics: moment sign over stance and power versus moment x joint velocity.
        for joint in ('Hip', 'Knee', 'Ankle'):
            m = trial['jointMoments'][f'{side}{joint}Moment'][0]
            p = trial['jointPowers'][f'{side}{joint}Power'][...]
            w = np.gradient(np.radians(angle(f'{side}{joint}Angles')[0]), 1 / RATE_HZ)
            slope = np.polyfit(m * w, p[0], 1)[0]
            s[f'{joint.lower()}_moment_component1_p1_p99'] = np.nanpercentile(m, [1, 99]).round(3).tolist()
            s[f'{joint.lower()}_power_component1_vs_moment_x_velocity'] = {'corr': corr(p[0], m * w), 'slope': float(slope)}
            s[f'{joint.lower()}_power_abs_p99_by_component'] = [float(np.nanpercentile(np.abs(c), 99)) for c in p]
        out['sides'][side] = s
        curves[side] = (thigh_m, shank_m, hip, knee, pelvis)
    plate = trial['forceplates']['RForce'][...]
    cop = trial['forceplates']['RCoP'][...]
    out['right_plate'] = {'samples': int(plate.shape[1]), 'samples_per_angle_frame': plate.shape[1] / rp.shape[1],
                          'force_p1_p99_by_component': [np.nanpercentile(c, [1, 99]).round(2).tolist() for c in plate],
                          'cop_p1_p99_by_component': [np.nanpercentile(c, [1, 99]).round(4).tolist() for c in cop]}
    stride = None
    if keep_stride is not None:
        rhs = trial['events']['RHS'][...].ravel()
        choices = right_strides(rhs, rp.shape[1])
        start, end = keep_stride.choice(choices)
        thigh_m, shank_m, hip, knee, pelvis = (c[start - 1:end] for c in curves['R'])
        grid = np.linspace(0, end - start, 101)
        rs = lambda x: np.interp(grid, np.arange(end - start + 1), x).round(3).tolist()
        stride = {'side': 'right', 'start_frame': start, 'end_frame': end, 'candidates': len(choices),
                  'marker_thigh': rs(thigh_m), 'marker_shank': rs(shank_m), 'hip': rs(hip), 'knee': rs(knee), 'pelvis': rs(pelvis)}
    return out, stride


def probe_ankle(handle, subject, condition):
    trial = handle[f'Streaming/{subject}/Tread/{condition}']
    out = {'subject': subject, 'condition': condition, 'sides': {}}
    for side in 'RL':
        a = trial['jointAngles'][f'{side}AnkleAngles'][...]
        bad = np.flatnonzero(np.abs(a[0]) > 60)  # display screen only, not a validation bound
        runs = np.split(bad, np.flatnonzero(np.diff(bad) > 1) + 1) if bad.size else []
        normal = np.ones(a.shape[1], bool)
        normal[bad] = False
        out['sides'][side] = {
            'frames': int(a.shape[1]), 'frames_abs_component1_over_60deg': int(bad.size),
            'runs_1based': [[int(r[0]) + 1, int(r[-1]) + 1] for r in runs],
            'component1_p1_p99_outside_runs': np.nanpercentile(a[0][normal], [1, 99]).round(2).tolist(),
            'components_2_3_p1_p99_inside_runs': [np.nanpercentile(a[k][bad], [1, 99]).round(1).tolist() for k in (1, 2)] if bad.size else None,
            # Every 5th frame (20 Hz) for the figure; extreme values inside runs are in the ankle source review.
            'component1_every5': a[0][::5].round(2).tolist()}
        # The frame boundary depends on the screen, so report several screens and the same-side
        # heel-strike strides each one touches. No screen is adopted as a validation bound.
        hs = trial['events'][f'{side}HS'][...].ravel().astype(int)
        sweep = {}
        for screen in SCREENS_DEG:
            flagged = np.flatnonzero(np.abs(a[0]) > screen) + 1  # 1-based frames
            parts = np.split(flagged, np.flatnonzero(np.diff(flagged) > 1) + 1) if flagged.size else []
            touched = [[int(x), int(y)] for x, y in zip(hs[:-1], hs[1:])
                       if flagged.size and ((flagged >= x) & (flagged <= y)).any()]
            sweep[f'{screen}deg'] = {'frames': int(flagged.size), 'runs_1based': [[int(r[0]), int(r[-1])] for r in parts],
                                     'strides_touched': touched}
        out['sides'][side]['screen_sweep'] = sweep
        out['sides'][side]['strides_touched_identical_across_screens'] = len(
            {json.dumps(v['strides_touched']) for v in sweep.values()}) == 1
    return out


def run_probe():
    import h5py
    resource.setrlimit(resource.RLIMIT_AS, (1024 ** 3, 1024 ** 3))
    if mem_available() < 2 * 1024 ** 3:
        raise MemoryError('Less than 2 GiB available; probe not started')
    receipt = json.loads(SOURCE_RECEIPT.read_text())['source']
    before = SOURCE.stat()
    if (before.st_size, before.st_mtime_ns) != (receipt['bytes'], receipt['mtime_ns']):
        raise ValueError('Streaming.mat size/mtime differ from the recorded conversion receipt')
    with h5py.File(SOURCE, 'r', rdcc_nbytes=1024 ** 2) as handle:
        group = handle['Streaming']
        trials = sorted((s, c) for s in group for c in group[s]['Tread'])
        rng = random.Random(SEED)
        sample = rng.sample(trials, N_RANDOM)
        records, stride = [], None
        for i, (s, c) in enumerate(sample + [LEAD]):
            if mem_available() < 2 * 1024 ** 3:
                raise MemoryError('Less than 2 GiB available; stopped at a trial boundary')
            rec, st = probe_trial(handle, s, c, keep_stride=rng if i == 0 else None)
            rec['role'] = 'random' if i < N_RANDOM else 'coordinator_lead'
            records.append(rec)
            stride = stride or st
        ankle = [probe_ankle(handle, s, c) for s, c in ANOMALY]
    after = SOURCE.stat()
    if (after.st_size, after.st_mtime_ns) != (before.st_size, before.st_mtime_ns):
        raise ValueError('Source changed during probe')
    data = {'task_id': 'UM21-C01', 'scientific_approval': False,
            'source': {'path': str(SOURCE.relative_to(ROOT)), 'bytes': after.st_size, 'mtime_ns': after.st_mtime_ns,
                       'sha256_recorded': receipt['sha256'],
                       'sha256_note': 'Recorded by the treadmill conversion receipt; size and mtime re-checked, bytes not rehashed.'},
            'receipt': {str(SOURCE_RECEIPT.relative_to(ROOT)): digest(SOURCE_RECEIPT)},
            'code_sha256': {str(Path(__file__).relative_to(ROOT)): digest(Path(__file__))},
            'seed': SEED, 'random_trials': [f'{s}/{c}' for s, c in sample], 'lead_trial': '/'.join(LEAD),
            'method': {'marker_pelvis_tilt': 'atan2(PSIS mid height - ASIS mid height, horizontal PSIS->ASIS distance); + when PSIS higher (Vicon pelvic tilt definition).',
                       'marker_thigh': 'greater trochanter -> mid lateral/medial knee, sagittal angle from straight down, forward positive.',
                       'marker_shank': 'mid knee -> mid lateral/medial malleolus, same sign.',
                       'limits': 'Trochanter is not the hip joint center, so a few degrees of constant offset is expected. Marker geometry tests sign and recipe, not model calibration.',
                       'power_check': 'Least-squares slope and correlation of source power component 1 on moment component 1 x d(angle component 1)/dt, all frames.'},
            'trials': records, 'random_stride': {'trial': '/'.join(sample[0]), **stride}, 'ankle_anomalies': ankle}
    PROBE.write_text(json.dumps(data, indent=1) + '\n')
    print(json.dumps({'random_trials': data['random_trials'], 'stride': [stride['start_frame'], stride['end_frame']],
                      'probe_sha256': digest(PROBE)}))


# ---------------------------------------------------------------- sheets

def style():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 10.5, 'axes.titlesize': 11, 'axes.spines.top': False, 'axes.spines.right': False,
                         'text.color': INK, 'axes.labelcolor': INK, 'axes.edgecolor': INK, 'xtick.color': INK,
                         'ytick.color': INK, 'axes.linewidth': 0.6, 'legend.frameon': False})
    return plt


STATUS = {'standard': ('standard column', '#1f7a4d', '#e5f3eb'), 'derived': ('derived estimate', '#7a5a00', '#fff4d6'),
          'source': ('source only', '#5b6672', '#eceff2'), 'call': ('waits on your answer', '#24506F', '#e3edf6'),
          'remove': ('dropped', '#a8322d', '#fbe9e7'), 'bad': ('made-up error', '#a8322d', '#fbe9e7')}
# One panel per image: (file, panel title, rows of (source field, transform, our column, status)).
MAPPING = [
    ('fig1a_standard.png', 'Standard columns', [
        ('PelvisAngles · tilt', '× π/180', 'pelvis_sagittal_angle_rad', 'standard'),
        ('HipAngles · flexion', '× π/180', 'hip_flexion_angle_*_rad', 'standard'),
        ('KneeAngles · flexion', '× π/180', 'knee_flexion_angle_*_rad', 'standard'),
        ('hip, knee angle', 'd/dt per stride', 'hip/knee_flexion_velocity_*', 'derived')]),
    ('fig1b_waiting.png', 'Waiting on your answers', [
        ('Hip − Pelvis', '× π/180', 'thigh_sagittal_angle_*_rad', 'call'),
        ('Hip − Pelvis − Knee', '× π/180', 'shank_sagittal_angle_*_rad', 'call'),
        ('AnkleAngles · flexion', '× π/180', 'ankle_dorsiflexion_angle_*_rad', 'call'),
        ('Hip/Knee/Ankle moment · flexion', 'unchanged', '*_flexion_moment_*_Nm_kg', 'call'),
        ('Pelvis + Hip (current)', 'any answer', 'thigh/shank current values', 'remove')]),
    ('fig1c_source.png', 'Kept only as source copies', [
        ('AnkleAngles · flexion', 'exact copy', 'source_ankle_sagittal_angle_*', 'source'),
        ('Joint powers, joint forces', 'exact copy', 'source components', 'source'),
        ('2nd and 3rd components', 'exact copy', 'source components', 'source'),
        ('Foot progression angles', 'exact copy', 'source components', 'source'),
        ('Force plates', 'not exported yet', 'source components', 'source')]),
    ('fig1d_failure.png', 'Failure looks like (made-up)', [
        ('HipAngles · 2nd (adduction)', '× π/180', 'hip_flexion_angle_*_rad', 'bad'),
        ('KneeAngles · flexion', '× −π/180', 'knee_flexion_angle_*_rad', 'bad')]),
]


def fig_mapping_panel(plt, title, rows, path):
    """Two text lines per row so the panel stays 4.5 in wide with 10 pt text."""
    fig, ax = plt.subplots(figsize=(4.5, .62 * len(rows) + .55))
    n = len(rows)
    for i, (src, how, col, status) in enumerate(rows):
        y = n - i
        label, ink, fill = STATUS[status]
        ax.add_patch(plt.Rectangle((0, y - .46), 10, .9, color=fill, ec='none'))
        ax.add_patch(plt.Rectangle((0, y - .46), .12, .9, color=ink, ec='none'))
        ax.text(.3, y + .2, f'{src}  ({how})', va='center', fontsize=10, color=INK)
        ax.text(.3, y - .2, '→ ' + col, va='center', fontsize=10, family='monospace', color=INK)
    ax.set_title(title, loc='left', fontsize=11, fontweight='bold',
                 color=STATUS['bad'][1] if rows[0][3] == 'bad' else INK)
    ax.set_xlim(0, 10); ax.set_ylim(.5, n + .5); ax.axis('off')
    fig.savefig(path, dpi=170, bbox_inches='tight'); plt.close(fig)


def fig_ankle(plt, anomaly, path):
    side_r, side_l = anomaly['sides']['R'], anomaly['sides']['L']
    t = np.arange(len(side_r['component1_every5'])) * 5 / RATE_HZ
    fig, ax = plt.subplots(figsize=(4.5, 3.3))
    ax.plot(t, side_l['component1_every5'], color=BLUE, lw=.5, label='left')
    ax.plot(t, side_r['component1_every5'], color=ORANGE, lw=.5, label='right')
    a, b = side_r['runs_1based'][0]
    ax.axvspan((a - 1) / RATE_HZ, (b - 1) / RATE_HZ, color=BAD, alpha=.08, lw=0)
    ax.text((a - 1) / RATE_HZ - 3, -260, f'right jumps\nat {(a - 1) / RATE_HZ:.0f} s', fontsize=10, color=BAD, ha='right')
    ax.axhline(0, color=REF, lw=.5)
    ax.set_xlabel('time in recording (s)'); ax.set_ylabel('source ankle flexion (deg)')
    ax.set_ylim(-320, 75)
    ax.set_title(f'{anomaly["subject"]}, {SLOPE[anomaly["condition"]]}, unmodified', loc='left', fontsize=11)
    ax.legend(loc='lower left', ncol=2, fontsize=10)
    fig.savefig(path, dpi=170, bbox_inches='tight'); plt.close(fig)


def fig_recipe(plt, stride, part, path):
    pelvis, hip, knee = (np.array(stride[k]) for k in ('pelvis', 'hip', 'knee'))
    phase = np.linspace(0, 100, len(hip))
    if part == 'thigh':
        marker, author, producer = np.array(stride['marker_thigh']), hip - pelvis, pelvis + hip
        labels = ('hip − pelvis', 'pelvis + hip')
    else:
        marker, author, producer = np.array(stride['marker_shank']), hip - pelvis - knee, pelvis + hip - knee
        labels = ('hip − pelvis − knee', 'pelvis + hip − knee')
    fig, ax = plt.subplots(figsize=(4.4, 3.2))
    ax.plot(phase, marker, color=INK, lw=2.4, label='from markers')
    ax.plot(phase, author, color=BLUE, lw=1.6, label=labels[0])
    ax.plot(phase, producer, color=ORANGE, lw=1.6, ls='--', label=labels[1])
    ax.axhline(0, color=REF, lw=.5)
    ax.set_xlabel('right gait cycle (%)'); ax.set_ylabel(f'{part} angle, forward + (deg)')
    ax.set_title(f'{part.capitalize()}: one random stride', loc='left', fontsize=11)
    ax.legend(loc='upper left', bbox_to_anchor=(0, -.2), ncol=1, fontsize=10)
    fig.savefig(path, dpi=170, bbox_inches='tight'); plt.close(fig)


def build_sheets():
    from contributor_tools.common.review_sheet import page
    plt = style()
    data = json.loads(PROBE.read_text())
    trials = data['trials']
    random_trials = [t for t in trials if t['role'] == 'random']
    sides = [s for t in random_trials for s in t['sides'].values()]
    # Medians: a few glitch frames per recording should not hide or fake agreement. Bounds are sample ranges.
    pelvis_err = max(abs(t['pelvis_component1_minus_marker_tilt']['median_deg']) for t in random_trials)
    author = [s['author_hip_minus_pelvis'] for s in sides]
    producer = [s['producer_pelvis_plus_hip'] for s in sides]
    a_meds = [a[k]['median_deg'] for a in author for k in ('thigh_minus_marker', 'shank_minus_marker')]
    p_thigh = min(abs(p['thigh_minus_marker']['median_deg']) for p in producer)
    closer = sum(abs(a['thigh_minus_marker']['median_deg']) < abs(p['thigh_minus_marker']['median_deg'])
                 and abs(a['shank_minus_marker']['median_deg']) < abs(p['shank_minus_marker']['median_deg'])
                 for a, p in zip(author, producer))
    slopes = [s[f'{j}_power_component1_vs_moment_x_velocity']['slope'] for s in sides for j in ('hip', 'knee', 'ankle')]
    ankle_stance = max(s['ankle_moment_component1_p1_p99'][0] for s in sides)
    force_min = min(t['right_plate']['force_p1_p99_by_component'][2][0] for t in random_trials)
    cop_span = max(abs(v) for t in random_trials for c in t['right_plate']['cop_p1_p99_by_component'][:2] for v in c)
    run = data['ankle_anomalies'][0]['sides']['R']['runs_1based'][0]
    ab08 = data['ankle_anomalies'][1]['sides']['L']['screen_sweep']
    lead = next(t for t in trials if t['role'] == 'coordinator_lead')

    for name in ('UM21-C01', 'D-UM21-C01-1'):
        folder = SHEETS / name
        folder.mkdir(parents=True, exist_ok=True)
        for old in folder.glob('*.png'):
            old.unlink()  # remove figures from earlier layouts so the folder matches the page
    for name, title, rows in MAPPING:
        fig_mapping_panel(plt, title, rows, SHEETS / 'UM21-C01' / name)
    fig_ankle(plt, data['ankle_anomalies'][0], SHEETS / 'UM21-C01/fig2_ankle.png')
    fig_recipe(plt, data['random_stride'], 'thigh', SHEETS / 'D-UM21-C01-1/fig1_thigh.png')
    fig_recipe(plt, data['random_stride'], 'shank', SHEETS / 'D-UM21-C01-1/fig2_shank.png')

    chips = [('pass' if pelvis_err < 1 else 'fail', f'pelvis tilt matches pelvis markers (median within {max(pelvis_err, .1):.1f}°)'),
             ('pass', 'hip and knee flexion positive: Vicon and authors agree'),
             ('pass' if ankle_stance < -1 else 'fail', 'ankle stance moment negative, as "internal, dorsiflexion positive" predicts'),
             ('fail' if max(slopes) < 0 else 'pass', 'source power sign is opposite to moment × joint speed'),
             ('fail' if force_min < -100 or cop_span > 5 else 'pass', 'force plates hold newtons and millimetres, not the README\'s N/kg and metres'),
             ('unchecked', 'ankle zero: no calibration files'),
             ('unchecked', f'right ankle jumps in one recording ({(run[0] - 1) / RATE_HZ:.0f}–{(run[1] - 1) / RATE_HZ:.0f} s), cause unknown'),
             ('unchecked', 'side-to-side and twist signs')]
    n_trials = len(random_trials)
    page(SHEETS / 'UM21-C01/index.html', title='Treadmill conventions check',
         ask='Look at 2 figures, then answer one decision.',
         headline='UMich 2021 treadmill: which fields become standard columns',
         chips=chips,
         figures=[([m[0] for m in MAPPING], 'Does each column take the right source field and sign?',
                   'Last panel: what a wrong mapping looks like.',
                   'Source fields mapped to our columns by release status, and two made-up wrong mappings'),
                  ('fig2_ankle.png', 'Is a source ankle channel broken in one recording?',
                   'Kept unchanged; never shifted.',
                   'Left and right source ankle angle over a whole recording; the right jumps late in the recording')],
         decision={'question': 'Release ankle angle and flexion moments as standard columns?',
                   'columns': ['Left out', 'Standard columns', 'Needs first'],
                   # Ordered by how much becomes standard, fewest first.
                   'rows': [('A · neither yet', ['ankle angle and moments', 'none', 'author reply']),
                            ('B · moments only', ['ankle angle', 'hip, knee, ankle flexion moments', 'our moment sign rule written down']),
                            ('C · both', ['broken ankle stretches', 'ankle angle and the three moments', 'our moment sign rule written down']),
                            ('defer', ['both, for now', 'release waits on these columns', '—'])],
                   'footnote': 'Source copies stay in every option; all reversible.',
                   'recommendation': 'C, medium confidence. Authors state dorsiflexion and flexion positive and internal moments; Vicon puts flexion first; ankle stance moments agree in every sampled leg. Moments ship only after our internal-moment rule is written into the reference. Broken ankle stretches stay missing.'},
         not_shown=['Ankle zero offsets per participant', 'Which pelvis side the authors\' normalized file used', 'Running, stairs, transitions'],
         reply='ankle and moments: A, B, C or defer  |  what looks wrong',
         details=['Decision D-UM21-C01-2, task UM21-C01.',
                  f'Random trials (seed {data["seed"]}): {", ".join(data["random_trials"])}. An independent verifier repeated the checks on 5 other recordings (seed 4242).',
                  f'Coordinator lead {data["lead_trial"]}: hip flexion p1-p99 {lead["sides"]["R"]["hip_component1_p1_p99_deg"]} deg with pelvis tilt mean {lead["pelvis_component1_mean_deg"]:.1f} deg; hip is measured from the tilted pelvis, so it rarely reaches extension.',
                  f'Power slope on moment x joint speed: {min(slopes):.2f} to {max(slopes):.2f} here; -0.71 to -1.02 across both samples.',
                  f'Ankle jump: AB07 incline 10 right, frames {run[0]}-{run[1]}. AB08 level left: '
                  + '; '.join(f'{k} screen {v["frames"]} frames {v["runs_1based"]}' for k, v in ab08.items())
                  + '. Frame boundary depends on the screen; no screen is adopted.',
                  'Evidence: docs/quality/audits/um21-c01-tread-conventions.json and um21-c01-source-probe.json',
                  'Builder: contributor_tools/review_um21_c01_conventions.py'])

    page(SHEETS / 'D-UM21-C01-1/index.html', title='Thigh and shank decision',
         ask='Choose how thigh and shank angles are released.',
         headline='Current thigh and shank columns add the pelvis angle; the authors subtract it',
         chips=[('pass' if closer == len(author) else 'fail', f'hip − pelvis closer to the markers in {closer} of {len(author)} legs ({n_trials} random recordings)'),
                ('pass' if max(map(abs, a_meds)) < 10 else 'fail', f'median gap {min(a_meds):+.0f}° to {max(a_meds):+.0f}° in these legs'),
                ('fail' if p_thigh > 5 else 'pass', f'pelvis + hip off by {p_thigh:.0f}° or more'),
                ('unchecked', 'full 3D segment angles')],
         figures=[(['fig1_thigh.png', 'fig2_shank.png'], 'Which recipe follows the leg markers?',
                   'Black is independent: trochanter, knee, ankle markers.',
                   'Thigh and shank angle over one random stride from markers and from two recipes')],
         decision={'question': 'How should thigh and shank angles ship?',
                   'columns': ['Left out', 'Columns', 'Needs first'],
                   # Ordered by how strongly the estimate is presented, weakest first.
                   'rows': [('A · leave out', ['thigh and shank', 'none', 'full 3D model, later']),
                            ('B · labeled estimate', ['standard names', 'planar estimate columns', 'formula stated with the columns']),
                            ('C · standard names', ['nothing', 'thigh and shank angle columns', 'our segment sign rule written down']),
                            ('defer', ['thigh and shank, for now', 'release waits on these columns', '—'])],
                   'footnote': 'Every option drops the current pelvis-plus-hip values; all reversible.',
                   'recommendation': 'B, medium confidence. The authors publish hip minus pelvis as their thigh estimate and markers agree within about 8 degrees across both samples, but it is a planar sum of 3D angles and the shank step is ours.'},
         not_shown=['Full 3D segment orientation', 'Running, stairs, transitions'],
         reply='thigh and shank: A, B, C or defer',
         details=['Decision D-UM21-C01-1, task UM21-C01.',
                  f'Random stride: {data["random_stride"]["trial"]} right, frames {data["random_stride"]["start_frame"]}-{data["random_stride"]["end_frame"]} (seed {data["seed"]}).',
                  f'Author-recipe median gaps {min(a_meds):+.1f} to {max(a_meds):+.1f} deg here; the independent verifier found -7.7 to +5.0 deg (thigh) on 5 other recordings. Producer recipe at least {p_thigh:.1f} deg here. The trochanter is not the hip centre.',
                  'Author recipe: publisher exampleUseScript.m lines 34-36 (thigh = hip - pelvis).',
                  'Builder: contributor_tools/review_um21_c01_conventions.py'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', choices=['probe', 'sheet'])
    args = parser.parse_args()
    os.nice(max(0, 19 - os.nice(0)))
    run_probe() if args.step == 'probe' else build_sheets()


if __name__ == '__main__':
    main()
