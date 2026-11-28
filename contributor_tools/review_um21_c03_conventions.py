"""UM21-C03: sagittal sign-convention fit for UMich 2021 treadmill channels, ankle branch census, review sheets.

Steps (run one at a time, in order):
  probe   Fits every angle, moment and power channel against independent evidence in
          4 random treadmill recordings (seed A) and 4 disjoint ones (seed B):
          marker segment/joint angles for angles; force-plate lever-arm moments for
          moments; lever-arm moment x marker joint speed for powers. Writes
          docs/quality/audits/um21-c03-source-probe.json.
  census  Reads only the jointAngles channels of all 50 treadmill recordings, one
          channel at a time, and lists frames whose middle Cardan component lies
          outside [-90, 90] deg (the alternate branch of the same orientation). Tests
          the alternate-solution identity with rotation matrices. Writes
          docs/quality/audits/um21-c03-episode-census.json.
  sheet   Builds review_sheets/UM21-C03/ and review_sheets/D-UM21-C03-1/ and the summary
          docs/quality/audits/um21-c03-conventions.json from the two files above.

Frame for every target (LocoHub sagittal proposal): x = walking direction, y = up,
z = x cross y = the person's right side, out of the page when the person faces right.
Counterclockwise about +z is positive. Nothing is converted, no dataset is changed,
and the re-expression rule is proposed only. Launches nothing.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
import collections
import hashlib
import itertools
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
AUDITS = ROOT / 'docs/quality/audits'
PROBE = AUDITS / 'um21-c03-source-probe.json'
CENSUS = AUDITS / 'um21-c03-episode-census.json'
SUMMARY = AUDITS / 'um21-c03-conventions.json'
PRIOR = [AUDITS / 'um21-c01-tread-conventions.json', AUDITS / 'um21-c01-source-probe.json']
SHEETS = ROOT / 'review_sheets'
SEED_A, SEED_B = 20261030, 20261031  # B samples only recordings A did not take
N_RANDOM = 4
RATE_HZ = 100.0
G = 9.81
NOMINAL_SLOPE_DEG = {'d10': 10.0, 'd5': 5.0, 'i0': 0.0, 'i5': 5.0, 'i10': 10.0}  # README p.2
STANCE_BW = 0.2       # own-plate vertical force above 20 % body weight counts as stance
JOINTS = ('Hip', 'Knee', 'Ankle')
ANGLE_CHANNELS = ('Pelvis', 'Hip', 'Knee', 'Ankle', 'FootProgress')
# Independent marker target for each source angle channel.
TARGET_OF = {'Pelvis': 'pelvis', 'Hip': 'hip', 'Knee': 'knee', 'Ankle': 'ankle', 'FootProgress': 'foot'}
# Where the two convention options differ: clinical = sign x pure right-hand rule (RHR).
CLINICAL_SIGN = {'pelvis': -1, 'hip': 1, 'knee': -1, 'ankle': 1, 'thigh': 1, 'shank': 1, 'foot': 1,
                 'hip_moment': 1, 'knee_moment': -1, 'ankle_moment': 1, 'power': 1}
INK, MUTED, REF, BLUE, ORANGE, BAD, GREEN = '#20252B', '#5b6672', '#999999', '#2a78d6', '#eb6834', '#c0392b', '#1f7a4d'
SLOPE = {'d10': 'decline 10°', 'd5': 'decline 5°', 'i0': 'level', 'i5': 'incline 5°', 'i10': 'incline 10°'}


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def mem_available():
    line = next(s for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:'))
    return int(line.split()[1]) * 1024


def peak_rss_mib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def guard_start():
    resource.setrlimit(resource.RLIMIT_AS, (1024 ** 3, 1024 ** 3))
    if mem_available() < 2 * 1024 ** 3:
        raise MemoryError('Less than 2 GiB available; not started')
    receipt = json.loads(SOURCE_RECEIPT.read_text())['source']
    st = SOURCE.stat()
    if (st.st_size, st.st_mtime_ns) != (receipt['bytes'], receipt['mtime_ns']):
        raise ValueError('Streaming.mat size/mtime differ from the recorded conversion receipt')
    return receipt, st


def guard_end(before):
    after = SOURCE.stat()
    if (after.st_size, after.st_mtime_ns) != (before.st_size, before.st_mtime_ns):
        raise ValueError('Source changed during the read')
    return after


def source_block(receipt, st):
    return {'path': str(SOURCE.relative_to(ROOT)), 'bytes': st.st_size, 'mtime_ns': st.st_mtime_ns,
            'sha256_recorded': receipt['sha256'],
            'sha256_note': 'Recorded by the treadmill conversion receipt; size and mtime re-checked before and after, bytes not rehashed.'}


# ---------------------------------------------------------------- shared geometry

def rot(axis, deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    if axis == 'x':
        return np.stack([np.stack([np.ones_like(a), 0 * a, 0 * a], -1), np.stack([0 * a, c, -s], -1), np.stack([0 * a, s, c], -1)], -2)
    if axis == 'y':
        return np.stack([np.stack([c, 0 * a, s], -1), np.stack([0 * a, np.ones_like(a), 0 * a], -1), np.stack([-s, 0 * a, c], -1)], -2)
    return np.stack([np.stack([c, -s, 0 * a], -1), np.stack([s, c, 0 * a], -1), np.stack([0 * a, 0 * a, np.ones_like(a)], -1)], -2)


def cardan(triples, order='yxz'):
    """Rotation matrices R = R_order[0](c1) R_order[1](c2) R_order[2](c3) for an (N, 3) array in degrees.
    Vicon describes hip/knee/pelvis as flexion, then adduction, then rotation (YXZ in Plug-in Gait axes)."""
    t = np.asarray(triples, float)
    return rot(order[0], t[:, 0]) @ rot(order[1], t[:, 1]) @ rot(order[2], t[:, 2])


def wrap(deg):
    return (np.asarray(deg) + 180.0) % 360.0 - 180.0


def reexpress(triples):
    """Proposed rule: a triple whose middle component is outside [-90, 90] deg is replaced by the other
    Cardan solution of the same rotation, (c1 + 180, 180 - c2, c3 + 180), each wrapped to [-180, 180)."""
    t = np.array(triples, float)
    alt = np.abs(t[:, 1]) > 90
    t[alt, 0] = wrap(t[alt, 0] + 180)
    t[alt, 1] = wrap(180 - t[alt, 1])
    t[alt, 2] = wrap(t[alt, 2] + 180)
    return t, alt


def geodesic_deg(ra, rb):
    c = (np.einsum('nij,nij->n', ra, rb) - 1) / 2  # trace(ra^T rb)
    return np.degrees(np.arccos(np.clip(c, -1, 1)))


def runs_of(mask):
    idx = np.flatnonzero(mask)
    if not idx.size:
        return []
    parts = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
    return [(int(p[0]), int(p[-1])) for p in parts]  # 0-based inclusive


def strides(hs, length):
    hs = np.asarray(hs).ravel().astype(int)
    return [(int(a), int(b)) for a, b in zip(hs[:-1], hs[1:]) if a >= 1 and b <= length and 50 <= b - a <= 250]


# ---------------------------------------------------------------- probe

def moving_mean(x, k=5):
    return np.convolve(x, np.ones(k) / k, mode='same')


def fit_candidates(target, src, mask, offset=True):
    """Residual of target - sign * src[c] (after the median offset when offset=True) for every component and sign.
    Ranked by the median absolute residual so marker-glitch frames cannot pick the winner; RMS and p95 are reported too."""
    rows = []
    for c in range(src.shape[0]):
        for s in (1, -1):
            x = s * src[c]
            ok = mask & np.isfinite(x) & np.isfinite(target)
            if ok.sum() < 50 or np.nanstd(x[ok]) == 0:
                continue  # too few frames, or a constant (e.g. all-zero) component
            d = target[ok] - x[ok]
            off = float(np.median(d)) if offset else 0.0
            r = np.abs(d - off)
            rows.append({'component': c + 1, 'sign': s, 'offset': round(off, 3), 'median_abs': round(float(np.median(r)), 4),
                         'p95_abs': round(float(np.percentile(r, 95)), 4), 'rms': round(float(np.sqrt(np.mean(r ** 2))), 4),
                         'corr': round(float(np.corrcoef(x[ok], target[ok])[0, 1]), 4),
                         'slope': round(float(np.polyfit(x[ok], target[ok], 1)[0]), 4), 'frames': int(ok.sum())})
    return sorted(rows, key=lambda r: r['median_abs'])


def probe_trial(handle, subject, condition, rng=None):
    trial = handle[f'Streaming/{subject}/Tread/{condition}']
    n = trial['jointAngles']['RPelvisAngles'].shape[1]

    def read(group, name):  # exact (0, 0, 0) triples are zero fill, treated as missing
        x = trial[group][name][...].astype(float)
        x[:, (x == 0).all(0)] = np.nan
        return x

    def marker(name):
        m = trial['markers'][name][...]
        xyz = m[:3].copy()
        xyz[:, m[3] != 1] = np.nan
        return xyz

    asi = (marker('LASI') + marker('RASI')) / 2
    psi = (marker('LPSI') + marker('RPSI')) / 2
    ant = np.nanmean((asi - psi)[:2], 1)
    ant = np.array([ant[0], ant[1], 0.0]) / np.linalg.norm(ant)
    sag = lambda v: (v[0] * ant[0] + v[1] * ant[1], v[2])  # (forward, up) components

    def seg_from_down(v):  # CCW about the right-side axis, 0 = pointing down, distal end forward = +
        fx, up = sag(v)
        return np.degrees(np.arctan2(fx, -up))

    def seg_from_forward(v):  # CCW, 0 = pointing forward horizontally, tip up = +
        fx, up = sag(v)
        return np.degrees(np.arctan2(up, fx))

    pelvis_seg = seg_from_forward(asi - psi)

    # Plates: 10 plate samples per angle frame; block mean to 100 Hz; plate frame tilted with the belt.
    plates = {}
    for s in 'RL':
        f = trial['forceplates'][s + 'Force'][...]
        cop = trial['forceplates'][s + 'CoP'][...]
        if f.shape[1] != 10 * n:
            raise ValueError(f'{subject}/{condition}: plate samples {f.shape[1]} != 10 x {n}')
        plates[s] = (np.nanmean(f.reshape(3, n, 10), 2), np.nanmean(cop.reshape(3, n, 10), 2) / 1000.0)
    total = plates['R'][0] + plates['L'][0]
    mean_total = np.nanmean(total, 1)
    mass = float(np.linalg.norm(mean_total) / G)
    # Belt rise direction in the marker (gravity) frame: heel path z versus y during mid stance.
    hee, toe = marker('RHEE'), marker('RTOE')
    fz_r = -plates['R'][0][2]
    on = np.flatnonzero(np.diff((fz_r > STANCE_BW * mass * G).astype(int)) == 1) + 1
    path = []
    for a in on[:40]:
        b = a + 1
        while b < n and fz_r[b] > STANCE_BW * mass * G:
            b += 1
        s0, s1 = a + int(.3 * (b - a)), a + int(.6 * (b - a))
        for m in (hee, toe):
            ok = np.isfinite(m[1, s0:s1]) & np.isfinite(m[2, s0:s1])
            if ok.sum() > 5:
                path.append(np.degrees(np.arctan(np.polyfit(m[1, s0:s1][ok], m[2, s0:s1][ok], 1)[0])))
    belt_marker_deg = float(np.median(path))
    alpha = np.sign(belt_marker_deg) * NOMINAL_SLOPE_DEG[condition] if NOMINAL_SLOPE_DEG[condition] else 0.0
    rx = rot('x', np.array(alpha))
    lab_mean = rx @ mean_total
    out = {'subject': subject, 'condition': condition, 'frames': n, 'anterior_axis_xy': ant[:2].round(4).tolist(),
           'mass_estimate_kg': round(mass, 2),
           'mass_note': 'Mean |R+L plate force| / g over the recording (steady treadmill walking); estimate, not a measured mass.',
           'belt_slope_from_marker_path_deg': round(belt_marker_deg, 2), 'plate_tilt_used_deg': alpha,
           'mean_plate_force_horizontal_after_tilt_pct_bw': round(float(100 * lab_mean[1] / np.linalg.norm(lab_mean)), 2),
           'sides': {}}

    curves = {}
    for side in 'RL':
        knee_c = (marker(side + 'KNE') + marker(side + 'KNEM')) / 2
        ank_c = (marker(side + 'ANK') + marker(side + 'ANKM')) / 2
        hip_c = marker(side + 'GT')  # lateral proxy for the hip centre
        heel, toe_m = marker(side + 'HEE'), marker(side + 'TOE')
        seg = {'pelvis': pelvis_seg, 'thigh': seg_from_down(knee_c - hip_c), 'shank': seg_from_down(ank_c - knee_c),
               'foot': seg_from_forward(toe_m - heel)}
        rhr = dict(seg)  # pure right-hand-rule targets (counterclockwise about the right-side axis)
        rhr.update(hip=seg['thigh'] - seg['pelvis'], knee=seg['shank'] - seg['thigh'], ankle=seg['foot'] - seg['shank'])
        src = {ch: read('jointAngles', f'{side}{ch}Angles') for ch in ANGLE_CHANNELS}
        res = {'angles': {}, 'recipes': {}, 'moments': {}, 'powers': {}}
        for ch in ANGLE_CHANNELS:
            a = src[ch]
            normal = np.abs(a[1]) <= 90  # alternate-branch frames excluded (see census)
            tgt = TARGET_OF[ch]
            res['angles'][ch] = {'target': tgt, 'alternate_branch_frames_excluded': int((~normal).sum()),
                                 'rhr': fit_candidates(rhr[tgt], a, normal),
                                 'clinical': fit_candidates(CLINICAL_SIGN[tgt] * rhr[tgt], a, normal)}
        # Planar recipes from source component 1 (clinical source signs).
        p1, h1, k1, a1 = (src[c][0] for c in ('Pelvis', 'Hip', 'Knee', 'Ankle'))
        ok_a = np.abs(src['Ankle'][1]) <= 90
        recipes = {'thigh = hip - pelvis': (h1 - p1, 'thigh'), 'thigh = pelvis + hip (current producer)': (p1 + h1, 'thigh'),
                   'shank = hip - pelvis - knee': (h1 - p1 - k1, 'shank'),
                   'foot = hip - pelvis - knee + ankle': (np.where(ok_a, h1 - p1 - k1 + a1, np.nan), 'foot')}
        for name, (x, tgt) in recipes.items():
            res['recipes'][name] = {'target': tgt, 'rhr': fit_candidates(rhr[tgt], x[None], np.ones(n, bool)),
                                    'clinical': fit_candidates(CLINICAL_SIGN[tgt] * rhr[tgt], x[None], np.ones(n, bool))}
        # Lever-arm moments: internal moment = -(r x GRF)_z, r = CoP - joint centre, GRF on foot = -(plate force).
        f, cop = plates[side]
        grf = -(rx @ f)
        cop_lab = rx @ np.vstack([cop[0], cop[1], np.zeros(n)])
        stance = (grf[2] > STANCE_BW * mass * G) & np.isfinite(grf).all(0) & np.isfinite(cop_lab).all(0)
        mid = (heel + toe_m) / 2
        off_ap = np.nanmean(sag(mid)[0][stance] - sag(cop_lab)[0][stance])  # CoP mean over stance at heel-toe midpoint
        low = np.fmin(heel[2], toe_m[2])
        off_up = np.nanmedian(low[stance] - cop_lab[2][stance])  # belt surface at the marker centres
        gx, gz = sag(grf)
        cx0, cz0 = sag(cop_lab)[0] + off_ap, cop_lab[2] + off_up
        centres = {'Hip': hip_c, 'Knee': knee_c, 'Ankle': ank_c}
        base = {}
        for joint, centre in centres.items():
            jx, jz = sag(centre)
            base[joint] = np.where(stance, -((cx0 - jx) * gz - (cz0 - jz) * gx) / mass, np.nan)
        # Moving the CoP by d forward and e up changes every joint's lever moment by -d*gz/m + e*gx/m.
        basis = np.vstack([-gz / mass, gx / mass])
        m_src = {j: read('jointMoments', f'{side}{j}Moment') for j in JOINTS}
        p_src = {j: read('jointPowers', f'{side}{j}Power') for j in JOINTS}
        combos = []
        for signs in itertools.product((1, -1), repeat=3):
            ys, As = [], []
            for sg, joint in zip(signs, JOINTS):
                ok = stance & np.isfinite(m_src[joint][0]) & np.isfinite(base[joint]) & np.isfinite(basis).all(0)
                ys.append(sg * m_src[joint][0][ok] - base[joint][ok])
                As.append(basis[:, ok].T)
            y, A = np.concatenate(ys), np.vstack(As)
            (d, e), *_ = np.linalg.lstsq(A, y, rcond=None)
            combos.append({'rhr_signs_hip_knee_ankle_component1': list(signs), 'cop_forward_shift_m': round(float(d), 4),
                           'cop_up_shift_m': round(float(e), 4), 'rms_Nm_per_kg': round(float(np.sqrt(np.mean((A @ [d, e] - y) ** 2))), 4)})
        combos.sort(key=lambda r: r['rms_Nm_per_kg'])
        d, e = combos[0]['cop_forward_shift_m'], combos[0]['cop_up_shift_m']
        lever = {j: base[j] + d * basis[0] + e * basis[1] for j in JOINTS}
        res['registration'] = {'cop_midpoint_offset_forward_m': round(float(off_ap), 4), 'cop_marker_floor_offset_up_m': round(float(off_up), 4),
                               'stance_frames': int(stance.sum()), 'sign_combinations': combos,
                               'note': 'One CoP shift (forward, up) per plate, fitted jointly to hip, knee and ankle for each of the 8 sign '
                                       'combinations of source component 1; the best combination sets the shift used below.'}
        omega = {j: np.gradient(np.radians(moving_mean(rhr[j.lower()])), 1 / RATE_HZ) for j in JOINTS}
        for joint in JOINTS:
            key = joint.lower() + '_moment'
            res['moments'][joint] = {
                reg: {'rhr': fit_candidates(t, m_src[joint], stance, offset=False),
                      'clinical': fit_candidates(CLINICAL_SIGN[key] * t, m_src[joint], stance, offset=False)}
                for reg, t in (('fitted_registration', lever[joint]), ('midpoint_registration', base[joint]))}
            a_src = src[joint]
            ok = np.abs(a_src[1]) <= 90
            w_src = np.gradient(np.radians(a_src[0]), 1 / RATE_HZ)
            p_ind = lever[joint] * omega[joint]
            p_int = m_src[joint][0] * w_src
            res['powers'][joint] = {
                'zero_or_missing_components': [int(c + 1) for c in range(3) if not np.nanmax(np.abs(np.nan_to_num(p_src[joint][c]))) > 0],
                'vs_lever_moment_x_marker_speed': fit_candidates(p_ind, p_src[joint], stance & ok, offset=False),
                'vs_source_moment_x_source_speed': fit_candidates(p_int, p_src[joint], ok, offset=False),
                'independent_power_p1_p99_stance': np.nanpercentile(p_ind[stance & ok], [1, 99]).round(3).tolist()}
        out['sides'][side] = res
        curves[side] = {**{f'{j.lower()}_src': m_src[j][0] for j in JOINTS}, **{f'{j.lower()}_lever': lever[j] for j in JOINTS},
                        **{f'{j.lower()}_power_src_{c + 1}': p_src[j][c] for j in JOINTS for c in range(3)},
                        **{f'{j.lower()}_power_indep': lever[j] * omega[j] for j in JOINTS}}
    stride = None
    if rng is not None:
        # Random among right strides whose knee and ankle force-plate estimates both exist in >= 40 % of frames
        # (marker dropout removes the estimate; the figure needs both curves).
        choices = [(a, b) for a, b in strides(trial['events']['RHS'][...], n)
                   if all(np.isfinite(curves['R'][f'{j}_lever'][a - 1:b]).mean() >= .4 for j in ('knee', 'ankle'))]
        a, b = rng.choice(choices)
        grid = np.linspace(0, b - a, 101)
        rs = lambda x: [None if not np.isfinite(v) else round(float(v), 4) for v in np.interp(grid, np.arange(b - a + 1), x[a - 1:b])]
        stride = {'trial': f'{subject}/{condition}', 'side': 'right', 'start_frame': a, 'end_frame': b, 'candidates': len(choices),
                  'choice_rule': 'rng(seed A).choice among right strides (50-250 frames) with knee and ankle force-plate estimates in >= 40 % of frames',
                  **{k: rs(v) for k, v in curves['R'].items()}}
    return out, stride


def run_probe():
    import h5py
    receipt, before = guard_start()
    with h5py.File(SOURCE, 'r', rdcc_nbytes=1024 ** 2) as handle:
        group = handle['Streaming']
        trials = sorted((s, c) for s in group for c in group[s]['Tread'])
        rng_a = random.Random(SEED_A)
        sample_a = rng_a.sample(trials, N_RANDOM)
        rest = [t for t in trials if t not in sample_a]
        sample_b = random.Random(SEED_B).sample(rest, N_RANDOM)
        records, stride = [], None
        for label, sample in (('A', sample_a), ('B', sample_b)):
            for i, (s, c) in enumerate(sample):
                if mem_available() < 2 * 1024 ** 3:
                    raise MemoryError('Less than 2 GiB available; stopped at a trial boundary')
                rec, st = probe_trial(handle, s, c, rng=rng_a if (label == 'A' and i == 0) else None)
                rec['sample'] = label
                records.append(rec)
                stride = stride or st
                print(f'{label} {s}/{c} done, peak RSS {peak_rss_mib():.0f} MiB', flush=True)
    after = guard_end(before)
    data = {'task_id': 'UM21-C03', 'scientific_approval': False, 'source': source_block(receipt, after),
            'receipt': {str(SOURCE_RECEIPT.relative_to(ROOT)): digest(SOURCE_RECEIPT)},
            'code_sha256': {str(Path(__file__).relative_to(ROOT)): digest(Path(__file__))},
            'seeds': {'A': SEED_A, 'B': SEED_B, 'rule': 'A = random.Random(A).sample(sorted 50 recordings, 4); B = random.Random(B).sample(the 46 others, 4).'},
            'samples': {'A': [f'{s}/{c}' for s, c in sample_a], 'B': [f'{s}/{c}' for s, c in sample_b]},
            'peak_rss_mib': round(peak_rss_mib(), 1), 'trials': records, 'random_stride': stride}
    PROBE.write_text(json.dumps(data, separators=(',', ':')) + '\n')  # compact: mostly number lists
    print(json.dumps({'samples': data['samples'], 'peak_rss_mib': data['peak_rss_mib'], 'sha256': digest(PROBE)}))


# ---------------------------------------------------------------- census

STEP_SCREENS_DEG = (10, 20, 45, 90)  # reporting screens for frame-to-frame orientation steps; none is adopted


def census_channel(a, hs):
    """One (3, N) joint-angle channel: zero-fill frames, alternate-branch runs, orientation steps and matrix checks.
    Exact (0, 0, 0) triples are treated as missing (they coincide with marker dropout at the AB07/i10 end)."""
    n = a.shape[1]
    t = a.T.astype(float)
    zero = (t == 0).all(1)
    valid = np.isfinite(t).all(1) & ~zero
    fixed, alt = reexpress(np.where(valid[:, None], t, 0.0))
    alt &= valid
    r_raw = cardan(np.where(valid[:, None], t, 0.0))
    step = np.full(n, np.nan)  # orientation change from the previous frame; identical before and after re-expression
    both = valid[1:] & valid[:-1]
    step[1:][both] = geodesic_deg(r_raw[:-1][both], r_raw[1:][both])
    hs = np.asarray(hs).ravel().astype(int)
    pairs = list(zip(hs[:-1], hs[1:]))
    out = {'frames': n, 'zero_triple_frames': int(zero.sum()), 'nonfinite_frames': int((~np.isfinite(t).all(1)).sum()),
           'alternate_frames': int(alt.sum()),
           'step_p99_deg': round(float(np.nanpercentile(step, 99)), 3) if np.isfinite(step).any() else None,
           'step_frames_over_screen': {f'{d}deg': int((step > d).sum()) for d in STEP_SCREENS_DEG},
           'step_over_20deg_frames_1based': (np.flatnonzero(step > 20) + 1).tolist()[:40],
           'strides_touched_by_step_over_screen': {f'{d}deg': sum(bool((step[max(x - 1, 0):min(y, n)] > d).any()) for x, y in pairs)
                                                   for d in STEP_SCREENS_DEG},
           'zero_runs': len(runs_of(zero)),
           'zero_frames_between_first_and_last_heel_strike': int(zero[max(hs.min() - 1, 0):hs.max()].sum()) if hs.size else None}
    if not alt.any():
        return out, fixed
    runs = runs_of(alt)
    inside = np.zeros(n, bool)
    run_rows = []
    for a0, a1 in runs:
        inside[a0:a1 + 1] = True
        edges = []
        for i in (a0, a1 + 1):  # frame i compared with frame i - 1
            if 0 < i < n:
                edges.append({'frame_1based': i + 1, 'matrix_step_deg': None if np.isnan(step[i]) else round(float(step[i]), 2),
                              'raw_jump_deg': np.round(t[i] - t[i - 1], 2).tolist(),
                              'reexpressed_jump_deg': np.round(fixed[i] - fixed[i - 1], 2).tolist(),
                              'previous_frame_zero_fill': bool(zero[i - 1]), 'frame_zero_fill': bool(zero[i]) if i < n else None})
        seg = step[a0 + 1:a1 + 1]
        run_rows.append({'run_1based': [a0 + 1, a1 + 1], 'frames': a1 - a0 + 1, 'edges': edges,
                         'inside_steps_over_screen': {f'{d}deg': int((seg > d).sum()) for d in STEP_SCREENS_DEG},
                         'inside_step_over_20deg_frames_1based': (np.flatnonzero(seg > 20) + a0 + 2).tolist()[:20]})
    normal = valid & ~alt
    in_steps = step[1:][alt[1:] & alt[:-1] & np.isfinite(step[1:])]
    out_steps = step[1:][normal[1:] & normal[:-1] & np.isfinite(step[1:])]
    mirror = t.copy()
    mirror[alt] *= -1  # competing hypothesis: a mirrored sign flip
    offset_only = t.copy()
    offset_only[alt, 0] = wrap(offset_only[alt, 0] + 180)  # competing hypothesis: component 1 shifted by 180 only
    big = step > 20
    out.update({
        'runs': len(runs), 'run_details': run_rows,
        'strides_touched': sum(bool(alt[max(x - 1, 0):min(y, n)].any()) for x, y in pairs),
        'inside_step_p50_p95_deg': np.percentile(in_steps, [50, 95]).round(2).tolist() if in_steps.size else None,
        'outside_step_p50_p95_deg': np.percentile(out_steps, [50, 95]).round(2).tolist() if out_steps.size else None,
        'strides_touched_by_step_over_20deg': sum(bool(big[max(x - 1, 0):min(y, n)].any()) for x, y in pairs),
        'inside_raw_p1_p99_by_component': [np.percentile(t[alt, k], [1, 99]).round(1).tolist() for k in range(3)],
        'inside_reexpressed_p1_p99_by_component': [np.percentile(fixed[alt, k], [1, 99]).round(1).tolist() for k in range(3)],
        'outside_p1_p99_by_component': [np.percentile(t[normal, k], [1, 99]).round(1).tolist() for k in range(3)] if normal.any() else None,
        'max_matrix_difference_raw_vs_reexpressed_all_cardan_orders': max(
            float(np.abs(cardan(t[alt], o) - cardan(fixed[alt], o)).max()) for o in ('xyz', 'xzy', 'yxz', 'yzx', 'zxy', 'zyx')),
        'max_matrix_difference_raw_vs_mirror_hypothesis': float(np.abs(r_raw[alt] - cardan(mirror[alt])).max()),
        'max_matrix_difference_raw_vs_offset_only_hypothesis': float(np.abs(r_raw[alt] - cardan(offset_only[alt])).max())})
    return out, fixed


def stride_curves(x, pairs):
    """101-point nearest-frame resampling per stride; missing frames stay None so glitches are not smoothed away."""
    out = []
    for a, b in pairs:
        seg = x[a - 1:b]
        if len(seg) < 2:
            continue
        idx = np.rint(np.linspace(0, b - a, 101)).astype(int)
        out.append([None if not np.isfinite(v) else round(float(v), 1) for v in seg[idx]])
    return out


def run_census():
    import h5py
    receipt, before = guard_start()
    rows, every, layout, figure = [], [], [], None
    with h5py.File(SOURCE, 'r', rdcc_nbytes=1024 ** 2) as handle:
        group = handle['Streaming']
        trials = sorted((s, c) for s in group for c in group[s]['Tread'])
        for s, c in trials:
            if mem_available() < 2 * 1024 ** 3:
                raise MemoryError('Less than 2 GiB available; stopped at a recording boundary')
            trial = group[s]['Tread'][c]
            hs = {side: trial['events'][f'{side}HS'][...] for side in 'RL'}
            for side in 'RL':
                for ch in ANGLE_CHANNELS:
                    a = trial['jointAngles'][f'{side}{ch}Angles'][...]
                    res, fixed = census_channel(a, hs[side])
                    res = {'recording': f'{s}/{c}', 'side': side, 'channel': ch, **res}
                    every.append({k: res[k] for k in ('recording', 'side', 'channel', 'zero_triple_frames', 'zero_runs', 'zero_frames_between_first_and_last_heel_strike', 'alternate_frames', 'step_p99_deg', 'step_frames_over_screen', 'strides_touched_by_step_over_screen')})
                    if res['alternate_frames'] or res['step_frames_over_screen']['20deg']:
                        rows.append(res)
                    if res['alternate_frames'] and ch == 'Ankle' and (figure is None or res['alternate_frames'] > figure['alternate_frames']):
                        # Figure data: the largest ankle episode, strides wholly outside versus touched.
                        pairs = strides(hs[side], a.shape[1])
                        zero = (a == 0).all(0)
                        alt = (np.abs(a[1]) > 90) & ~zero
                        raw = np.where(zero, np.nan, a[0])
                        fx = np.where(zero, np.nan, fixed[:, 0])
                        inside = [p for p in pairs if alt[p[0] - 1:p[1]].any()]
                        outside = [p for p in pairs if not alt[p[0] - 1:p[1]].any()]
                        figure = {'recording': f'{s}/{c}', 'side': side, 'channel': ch, 'alternate_frames': res['alternate_frames'],
                                  'outside_strides': stride_curves(raw, outside), 'inside_raw': stride_curves(raw, inside),
                                  'inside_reexpressed': stride_curves(fx, inside), 'n_outside': len(outside), 'n_inside': len(inside),
                                  'inside_pairs': inside}
                    del a, fixed
                for joint in JOINTS:  # kinetic layout: which components hold values, and power versus moment x speed
                    mom = trial['jointMoments'][f'{side}{joint}Moment'][...]
                    pw = trial['jointPowers'][f'{side}{joint}Power'][...]
                    ang = trial['jointAngles'][f'{side}{joint}Angles'][...]
                    ok = ~(ang == 0).all(0) & ~(pw == 0).all(0) & (np.abs(ang[1]) <= 90)
                    mw = mom[0] * np.gradient(np.radians(ang[0]), 1 / RATE_HZ)
                    fits = {}
                    for k in range(3):
                        if np.nanstd(pw[k][ok]) > 0:
                            fits[f'c{k + 1}'] = {'corr': round(float(np.corrcoef(pw[k][ok], mw[ok])[0, 1]), 3),
                                                 'slope': round(float(np.polyfit(mw[ok], pw[k][ok], 1)[0]), 3)}
                    layout.append({'recording': f'{s}/{c}', 'side': side, 'joint': joint,
                                   'power_nonzero_components': [k + 1 for k in range(3) if np.any(pw[k] != 0)],
                                   'moment_nonzero_components': [k + 1 for k in range(3) if np.any(mom[k] != 0)],
                                   'power_vs_moment1_x_speed1': fits,
                                   'moment1_p1_p99': np.nanpercentile(mom[0][ok], [1, 99]).round(3).tolist()})
                    del mom, pw, ang
            print(f'{s}/{c} done, peak RSS {peak_rss_mib():.0f} MiB', flush=True)
    after = guard_end(before)
    data = {'task_id': 'UM21-C03', 'scientific_approval': False, 'source': source_block(receipt, after),
            'receipt': {str(SOURCE_RECEIPT.relative_to(ROOT)): digest(SOURCE_RECEIPT)},
            'code_sha256': {str(Path(__file__).relative_to(ROOT)): digest(Path(__file__))},
            'scope': f'{len(trials)} Tread recordings x 2 sides: {len(ANGLE_CHANNELS)} jointAngles channels, plus hip/knee/ankle jointMoments and jointPowers for the kinetic layout; markers and plates not read.',
            'criterion': 'Alternate branch: |component 2| > 90 deg. A Cardan triple with the middle angle outside [-90, 90] '
                         'is the second solution of the same rotation; standard extraction returns the middle angle inside it.',
            'rule_proposed_not_applied': '(c1, c2, c3) -> (wrap(c1 + 180), wrap(180 - c2), wrap(c3 + 180)) for frames meeting the criterion; '
                                         'log recording, side, channel and frame runs. Identity holds for every Cardan order and for per-component sign flips.',
            'channels_flagged': rows, 'all_channels': every, 'kinetic_layout': layout, 'figure_episode': figure, 'peak_rss_mib': round(peak_rss_mib(), 1),
            'channels_scanned': len(trials) * 2 * len(ANGLE_CHANNELS)}
    CENSUS.write_text(json.dumps(data, separators=(',', ':')) + '\n')  # compact: mostly number lists
    print(json.dumps({'flagged': [(r['recording'], r['side'], r['channel'], r['alternate_frames'], r.get('runs'), r['step_frames_over_screen']['20deg'], r['zero_triple_frames']) for r in rows],
                      'peak_rss_mib': data['peak_rss_mib'], 'sha256': digest(CENSUS)}))


# ---------------------------------------------------------------- summary and sheets

VICON = {'url': 'https://vicon-help.atlassian.net/wiki/spaces/Nexus216/pages/11611411', 'retrieved': '2026-10-30',
         'page': 'Vicon Nexus 2.16, Plug-in Gait kinematic variables',
         'quotes': ['Hip: "first flex the hip by the amount of the hip flexion, then adduct by the amount of hip adduction, then rotate the thigh about the (flexed and adducted) long axis of the thigh" (knee and pelvis described the same way: flexion/tilt, then adduction/obliquity, then rotation).',
                    'Ankle: "Foot rotation and foot progression ... are not expressed in terms of goniometric axes, since the ankle angles are not calculated as strict Cardan angles."',
                    'Pelvis: "Absolute angles are measured relative to laboratory axes ... In Plug-in Gait, the laboratory axis closest to the subject\'s direction of progression".'],
         'limitation': 'Nexus 2.16 text; the version used for UM21 is not stated (C01 Q1). The exact ankle sequence is therefore unverified.'}

# Expected sign of each signal under the two convention families and the published UM21 (Vicon) source.
# Frame: x walking direction, y up, z = x cross y = the person's right side (out of the page, person facing right).
SIGN_TABLE = [
    # signal, physical event, pure RHR, clinical (anatomical name), UM21 source as published
    ('Pelvis tilt', 'front tips down', -1, 1, 1),
    ('Thigh angle', 'knee ahead of hip', 1, 1, 1),
    ('Shank angle', 'ankle ahead of knee', 1, 1, 1),
    ('Foot angle', 'toes up', 1, 1, 1),
    ('Hip angle', 'flexion', 1, 1, 1),
    ('Knee angle', 'flexion', -1, 1, 1),
    ('Ankle angle', 'dorsiflexion', 1, 1, 1),
    ('Hip moment (internal)', 'flexor', 1, 1, 1),
    ('Knee moment (internal)', 'flexor', -1, 1, 1),
    ('Ankle moment (internal)', 'dorsiflexor', 1, 1, 1),
    ('Joint power', 'generation', 1, 1, 0),  # 0 = mixed in source (two layouts)
]
OPTIONS = {  # ordered by how many signals differ from the published source sign (fewest first)
    'A': ('Clinical names', [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]),
    'B': ('Segments counterclockwise, joints by name', [-1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]),
    'C': ('Counterclockwise for everything', [r[2] for r in SIGN_TABLE]),
}


def rows_of(probe, getter):
    """Per leg: (sample, recording, side, candidate rows)."""
    return [(t['sample'], f"{t['subject']}/{t['condition']}", side, getter(t['sides'][side])) for t in probe['trials'] for side in 'RL']


def pick(rows, comp, sign):
    return next((r for r in rows if r['component'] == comp and r['sign'] == sign), None)


def channel_summary(probe, getter, conv, comp, sign, legs=None):
    out = {'transform': {'component': comp, 'sign': sign}, 'by_sample': {}}
    for label in ('A', 'B'):
        legs_rows = [(rec, side, g[conv] if isinstance(g, dict) else g) for smp, rec, side, g in rows_of(probe, getter) if smp == label
                     and (legs is None or (rec, side) in legs)]
        won = sum(1 for _, _, rows in legs_rows if rows and rows[0]['component'] == comp and rows[0]['sign'] == sign)
        chosen = [pick(rows, comp, sign) for _, _, rows in legs_rows]
        flipped = [pick(rows, comp, -sign) for _, _, rows in legs_rows]
        chosen = [c for c in chosen if c]
        flipped = [c for c in flipped if c]
        runner = []
        for _, _, rows in legs_rows:
            others = [r for r in rows if not (r['component'] == comp and r['sign'] == sign)]
            if others:
                runner.append(others[0]['median_abs'])
        out['by_sample'][label] = {
            'legs': len(legs_rows), 'legs_where_best': won,
            'median_abs_residual_range': [round(min(c['median_abs'] for c in chosen), 3), round(max(c['median_abs'] for c in chosen), 3)] if chosen else None,
            'opposite_sign_median_abs_range': [round(min(c['median_abs'] for c in flipped), 3), round(max(c['median_abs'] for c in flipped), 3)] if flipped else None,
            'best_other_candidate_median_abs_range': [round(min(runner), 3), round(max(runner), 3)] if runner else None,
            'offset_range': [round(min(c['offset'] for c in chosen), 2), round(max(c['offset'] for c in chosen), 2)] if chosen else None,
            'corr_range': [round(min(c['corr'] for c in chosen), 3), round(max(c['corr'] for c in chosen), 3)] if chosen else None,
            'slope_range': [round(min(c['slope'] for c in chosen), 3), round(max(c['slope'] for c in chosen), 3)] if chosen else None}
    return out


def build_summary(probe, census):
    layout2 = {(x['recording'], x['side']) for x in census['kinetic_layout'] if x['power_nonzero_components'] == [3]}
    layout2_recordings = sorted({r for r, _ in layout2})
    all_legs = {(f"{t['subject']}/{t['condition']}", s) for t in probe['trials'] for s in 'RL'}
    l1, l2 = all_legs - layout2, all_legs & layout2
    table = []
    angle_spec = [('PelvisAngles', 'Pelvis', 'pelvis', 1), ('HipAngles', 'Hip', 'hip', 1), ('KneeAngles', 'Knee', 'knee', 1),
                  ('AnkleAngles', 'Ankle', 'ankle', 1), ('FootProgressAngles', 'FootProgress', 'foot', 1)]
    for name, ch, tgt, comp in angle_spec:
        for conv in ('rhr', 'clinical'):
            best = collections.Counter((r[conv][0]['component'], r[conv][0]['sign']) for _, _, _, r in
                                       rows_of(probe, lambda side, ch=ch: side['angles'][ch])).most_common(1)[0][0]
            table.append({'channel': name, 'evidence': f'marker {tgt} angle', 'convention': conv, 'unit': 'deg -> rad (x pi/180)',
                          **channel_summary(probe, lambda side, ch=ch: side['angles'][ch], conv, *best)})
    for name in ('thigh = hip - pelvis', 'thigh = pelvis + hip (current producer)', 'shank = hip - pelvis - knee', 'foot = hip - pelvis - knee + ankle'):
        for conv in ('rhr', 'clinical'):
            sign = 1 if conv == 'rhr' else CLINICAL_SIGN[name.split()[0]]
            table.append({'channel': f'recipe: {name} (component 1 of each, source signs)', 'evidence': f'marker {name.split()[0]} angle',
                          'convention': conv, 'unit': 'deg -> rad',
                          **channel_summary(probe, lambda side, name=name: side['recipes'][name], conv, 1, sign)})
    for joint in JOINTS:
        for conv in ('rhr', 'clinical'):
            sign = 1 if conv == 'clinical' else CLINICAL_SIGN[joint.lower() + '_moment']
            table.append({'channel': f'{joint}Moment', 'evidence': 'force-plate lever-arm internal moment, one fitted CoP shift per plate',
                          'convention': conv, 'unit': 'N*m/kg as is (slope near 1)',
                          **channel_summary(probe, lambda side, j=joint: side['moments'][j]['fitted_registration'], conv, 1, sign),
                          'midpoint_registration_check': channel_summary(probe, lambda side, j=joint: side['moments'][j]['midpoint_registration'], conv, 1, sign)})
    for joint in JOINTS:
        for layout, legs, comp, sign in (('layout 1 (components 1-3 filled)', l1, 1, -1), ('layout 2 (component 3 only)', l2, 3, 1)):
            for key, ev in (('vs_lever_moment_x_marker_speed', 'force-plate moment x marker joint speed'),
                            ('vs_source_moment_x_source_speed', 'source moment x source joint speed')):
                table.append({'channel': f'{joint}Power, {layout}', 'evidence': ev, 'convention': 'both (power is the same under either option)',
                              'unit': 'W/kg as is', **channel_summary(probe, lambda side, j=joint, k=key: side['powers'][j][k], 'x', comp, sign, legs)})
    combos = collections.Counter(tuple(t['sides'][s]['registration']['sign_combinations'][0]['rhr_signs_hip_knee_ankle_component1'])
                                 for t in probe['trials'] for s in 'RL')
    shifts = [t['sides'][s]['registration']['sign_combinations'][0] for t in probe['trials'] for s in 'RL']
    hip_margin = []
    for t in probe['trials']:
        for s in 'RL':
            cb = {tuple(x['rhr_signs_hip_knee_ankle_component1']): x['rms_Nm_per_kg'] for x in t['sides'][s]['registration']['sign_combinations']}
            hip_margin.append(round(cb[(-1, -1, 1)] - cb[(1, -1, 1)], 3))

    ank = [r for r in census['channels_flagged'] if r['channel'] == 'Ankle' and r['alternate_frames']]
    fig = census['figure_episode']
    ep = next(r for r in ank if r['recording'] == fig['recording'] and r['side'] == fig['side'])
    glitch = ep['step_over_20deg_frames_1based']
    clean_inside = [p for p in fig['inside_pairs'] if not any(p[0] <= g <= p[1] for g in glitch)]
    # A step at frame i compares frames i-1 and i; steps at most 10 frames apart form one cluster (frames i-1..i, 1-based).
    groups = []
    for g in glitch:
        if groups and g - groups[-1][1] <= 10:
            groups[-1][1] = g
        else:
            groups.append([g, g])
    clusters = ', '.join(f'{a}-{b}' if b > a else f'{a}' for a, b in groups)
    other_alt = collections.Counter(r['channel'] for r in census['channels_flagged'] if r['alternate_frames'])
    every = census['all_channels']
    episode = {
        'criterion': census['criterion'], 'rule_proposed_not_applied': census['rule_proposed_not_applied'],
        'joint_angle_channels_scanned': census['channels_scanned'],
        'channels_with_alternate_frames_by_type': dict(other_alt),
        'ankle_channels_with_alternate_frames': [{k: r[k] for k in ('recording', 'side', 'alternate_frames', 'runs', 'strides_touched',
                                                                     'inside_raw_p1_p99_by_component', 'inside_reexpressed_p1_p99_by_component',
                                                                     'outside_p1_p99_by_component', 'max_matrix_difference_raw_vs_reexpressed_all_cardan_orders',
                                                                     'max_matrix_difference_raw_vs_mirror_hypothesis', 'max_matrix_difference_raw_vs_offset_only_hypothesis',
                                                                     'step_frames_over_screen', 'strides_touched_by_step_over_screen')} for r in ank],
        'branch_episode': {'recording': fig['recording'], 'side': fig['side'], 'runs_1based': [x['run_1based'] for x in ep['run_details']],
                           'frames': ep['alternate_frames'], 'strides_touched_all_heel_strike_pairs': ep['strides_touched'],
                           'strides_inside_duration_screened': fig['n_inside'], 'strides_outside_duration_screened': fig['n_outside'],
                           'inside_strides_without_orientation_step_over_20deg': len(clean_inside),
                           'orientation_step_over_20deg_frames_1based': glitch,
                           'orientation_step_clusters_1based': clusters,
                           'inside_step_p50_p95_deg': ep['inside_step_p50_p95_deg'], 'outside_step_p50_p95_deg': ep['outside_step_p50_p95_deg'],
                           'interpretation': f'Inside-run triples re-expressed by the rule span the same 1st-99th percentile ranges as the outside run in all three '
                                             f'components, and orientation changes by {ep["inside_step_p50_p95_deg"][0]} deg per frame (median; 95th percentile '
                                             f'{ep["inside_step_p50_p95_deg"][1]} deg) inside the run against {ep["outside_step_p50_p95_deg"][0]} '
                                             f'({ep["outside_step_p50_p95_deg"][1]}) outside. Frames {clusters} (1-based clusters) contain one-frame orientation '
                                             'changes of 20-171 deg: those are not alternate solutions and the rule cannot fix them. The matrix identity '
                                             '(raw and re-expressed triples give the same rotation) holds for any triple and is a check of the rule, not evidence. '
                                             'The run ends where the recording turns to (0,0,0) zero fill.'},
        'short_ankle_runs': 'AB05/d10 left (5 frames) and AB06/d5 right (8 frames) meet the criterion but re-express to implausible values (middle '
                            'component 15-88 deg) next to orientation jumps; glitches, not branch switches. The rule plus a stride-level orientation-step '
                            'screen removes them; the screen value is reported at 10/20/45/90 deg and none is adopted.',
        'foot_progress': f'FootProgressAngles meet the criterion in {other_alt["FootProgress"]} recording-sides, for nearly whole recordings in '
                         + ', '.join(f'{r["recording"]} {r["side"]}' for r in census['channels_flagged'] if r['channel'] == 'FootProgress' and r['alternate_frames'] > 10000)
                         + '. Vicon says these are not strict Cardan angles; they stay source-only and the rule is not proposed for them.',
        'zero_fill': {'channels_with_exact_zero_triples': sum(1 for x in every if x['zero_triple_frames']),
                      'channels_scanned': len(every), 'zero_frames_total': sum(x['zero_triple_frames'] for x in every),
                      'channels_with_zero_frames_between_first_and_last_heel_strike': sum(1 for x in every if x['zero_frames_between_first_and_last_heel_strike']),
                      'zero_frames_between_first_and_last_heel_strike': sum(x['zero_frames_between_first_and_last_heel_strike'] for x in every),
                      'note': 'Exact (0,0,0) triples coincide with marker dropout at the AB07/i10 end (all foot/shank markers flagged 0). Elsewhere the '
                              'coincidence is not checked. A converter that reads them as 0 deg would invent data.'},
        'peak_rss_mib': census['peak_rss_mib']}
    kinetic = {'power_layout_2_recordings': layout2_recordings, 'power_layout_2_joint_sides': len(layout2) * 3,
               'joint_sides_scanned': len(census['kinetic_layout']),
               'layout_1': 'Power components 1-3 filled; component 1 = -(moment 1 x joint speed 1) (C01 finding).',
               'layout_2': 'Power components 1 and 2 are zero; component 3 = +(moment 1 x joint speed 1), as the paper defines power '
                           '(the Plug-in Gait total-power slot).',
               'moments': 'All three moment components are filled in every recording-side; the moment sign does not change with the power layout '
                          '(lever-arm fits agree in layout-2 recordings AB05/d5, AB05/d10 and AB04/d5).'}
    return {'table': table, 'kinetic_layout': kinetic, 'episode': episode,
            'registration': {'best_sign_combination_counts': {str(list(k)): v for k, v in combos.items()},
                             'fitted_cop_forward_shift_m_range': [min(x['cop_forward_shift_m'] for x in shifts), max(x['cop_forward_shift_m'] for x in shifts)],
                             'fitted_cop_up_shift_m_range': [min(x['cop_up_shift_m'] for x in shifts), max(x['cop_up_shift_m'] for x in shifts)],
                             'hip_sign_margin_rms_Nm_per_kg': hip_margin,
                             'note': 'Fitted from the source moments with 2 parameters shared by 3 joints, separately for every sign combination; '
                                     'not independent of the source for magnitude, but a single shared shift cannot turn one joint sign. '
                                     'One leg (AB06/d5 R) prefers hip negative with a 0.21 m vertical shift, physically implausible; it has 1208 zero-fill frames.'},
            'clean_inside': clean_inside}


def style():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 10.5, 'axes.titlesize': 11, 'axes.spines.top': False, 'axes.spines.right': False,
                         'text.color': INK, 'axes.labelcolor': INK, 'axes.edgecolor': INK, 'xtick.color': INK,
                         'ytick.color': INK, 'axes.linewidth': 0.6, 'legend.frameon': False})
    return plt


def fig_signs(plt, probe, layout2, path):
    """Robust sign preference per leg: (flipped - published) / (flipped + published) median absolute residual
    against counterclockwise-positive evidence. +1: the published sign fits; -1: the flipped sign fits."""
    rows = [('Pelvis tilt', lambda s: s['angles']['Pelvis']['rhr'], 1, None), ('Hip angle', lambda s: s['angles']['Hip']['rhr'], 1, None),
            ('Knee angle', lambda s: s['angles']['Knee']['rhr'], 1, None), ('Ankle angle', lambda s: s['angles']['Ankle']['rhr'], 1, None),
            ('Thigh (hip − pelvis)', lambda s: s['recipes']['thigh = hip - pelvis']['rhr'], 1, None),
            ('Shank (thigh − knee)', lambda s: s['recipes']['shank = hip - pelvis - knee']['rhr'], 1, None),
            ('Foot (shank + ankle)', lambda s: s['recipes']['foot = hip - pelvis - knee + ankle']['rhr'], 1, None),
            ('Hip moment', lambda s: s['moments']['Hip']['fitted_registration']['rhr'], 1, None),
            ('Knee moment', lambda s: s['moments']['Knee']['fitted_registration']['rhr'], 1, None),
            ('Ankle moment', lambda s: s['moments']['Ankle']['fitted_registration']['rhr'], 1, None),
            ('Ankle power, 1st slot', lambda s: s['powers']['Ankle']['vs_lever_moment_x_marker_speed'], 1, False),
            ('Ankle power, 3rd slot', lambda s: s['powers']['Ankle']['vs_lever_moment_x_marker_speed'], 3, True)]
    fig, ax = plt.subplots(figsize=(4.5, 5.4))
    fig.subplots_adjust(left=.40, right=.88, top=.93, bottom=.15)  # fixed canvas: saved without bbox_inches so it stays 4.5 in
    rng = np.random.default_rng(SEED_A)  # vertical jitter only
    ys, labels = [], []
    for i, (label, get, comp, lay2) in enumerate(rows):
        y = len(rows) - i
        vals = []
        for t in probe['trials']:
            for side in 'RL':
                if lay2 is not None and (((f"{t['subject']}/{t['condition']}", side) in layout2) != lay2):
                    continue
                cand = get(t['sides'][side])
                a, b = pick(cand, comp, 1), pick(cand, comp, -1)
                if a and b:
                    vals.append((b['median_abs'] - a['median_abs']) / (b['median_abs'] + a['median_abs']))
        vals = np.array(vals)
        col = BAD if np.median(vals) < 0 else GREEN
        ax.scatter(vals, y + rng.uniform(-.18, .18, len(vals)), s=16, color=col, alpha=.8, lw=0)
        ys.append(y); labels.append(label)
    ax.axvline(0, color=REF, lw=.6)
    ax.set_xlim(-1.05, 1.05); ax.set_ylim(.4, len(rows) + .9)
    ax.set_xticks([-1, 0, 1]); ax.set_xticklabels(['flip\nfits', '0', 'published\nfits'])
    ax.set_yticks(ys); ax.set_yticklabels(labels, fontsize=10)
    ax.tick_params(axis='y', length=0)
    ax.spines['left'].set_visible(False)
    ax.set_xlabel('sign preference, counterclockwise +')
    ax.set_title('One dot per leg (16 legs)', loc='left', fontsize=10, color=MUTED)
    fig.savefig(path, dpi=170); plt.close(fig)


def fig_moment(plt, stride, joint, path):
    src, lev = (np.array([np.nan if v is None else v for v in stride[f'{joint}_{k}']]) for k in ('src', 'lever'))
    phase = np.linspace(0, 100, len(src))
    fig, ax = plt.subplots(figsize=(4.4, 3.0))
    ax.plot(phase, lev, color=INK, lw=2.4, label='force-plate estimate, counterclockwise +')
    ax.plot(phase, src, color=ORANGE, lw=1.6, ls='--', label='source as published')
    ax.axhline(0, color=REF, lw=.5)
    ax.set_xlabel('right gait cycle (%)'); ax.set_ylabel('moment (N·m/kg)')
    ax.set_title(f'{joint.capitalize()}: one random stride', loc='left', fontsize=11)
    ax.legend(loc='upper left', bbox_to_anchor=(0, -.22), fontsize=10)
    fig.savefig(path, dpi=170, bbox_inches='tight'); plt.close(fig)


def fig_episode(plt, figure, clean, which, path):
    outside = np.array([[np.nan if v is None else v for v in c] for c in figure['outside_strides']])
    phase = np.linspace(0, 100, outside.shape[1])
    lo, mid, hi = np.nanpercentile(outside, [5, 50, 95], axis=0)
    curves = figure['inside_raw'] if which == 'raw' else figure['inside_reexpressed']
    pairs = figure['inside_pairs']
    fig, ax = plt.subplots(figsize=(4.4, 3.2))
    ax.fill_between(phase, lo, hi, color=REF, alpha=.35, lw=0, label=f'{figure["n_outside"]} strides outside the episode (5–95 %)')
    ax.plot(phase, mid, color=INK, lw=1.2, label='their median')
    for k, (c, p) in enumerate(zip(curves, pairs)):
        y = np.array([np.nan if v is None else v for v in c])
        bad = p not in clean
        ax.plot(phase, y, color=BAD if which == 'raw' else (ORANGE if bad else BLUE), lw=.7, alpha=.75,
                ls=':' if bad else '-', label=None)
    ax.plot([], [], color=BAD if which == 'raw' else BLUE, lw=1,
            label=f'{len(clean)} strides inside, as published' if which == 'raw' else f'{len(clean)} strides inside, re-expressed')
    ax.plot([], [], color=BAD if which == 'raw' else ORANGE, lw=1, ls=':', label=f'{len(curves) - len(clean)} inside strides with a sudden jump')
    ax.set_ylim(-200, 60) if which == 'raw' else ax.set_ylim(-60, 60)
    ax.axhline(0, color=REF, lw=.5)
    ax.set_xlabel('right gait cycle (%)'); ax.set_ylabel('ankle angle, 1st component (deg)')
    ax.set_title('As published' if which == 'raw' else 'Re-expressed (proposed rule)', loc='left', fontsize=11)
    ax.legend(loc='upper left', bbox_to_anchor=(0, -.22), fontsize=10)
    fig.savefig(path, dpi=170, bbox_inches='tight'); plt.close(fig)


def fig_sign_table(plt, path):
    fig, ax = plt.subplots(figsize=(4.5, 6.4))
    cols = ['source'] + list(OPTIONS)
    x0 = [6.5, 7.6, 8.55, 9.5]
    n = len(SIGN_TABLE)
    for i, (sig, event, rhr, clin, src) in enumerate(SIGN_TABLE):
        y = n - i
        ax.text(0, y + .19, sig, fontsize=10, va='center')
        ax.text(0, y - .21, f'sign of: {event}', fontsize=10, va='center', color=MUTED)
        vals = [src] + [OPTIONS[k][1][i] for k in OPTIONS]
        for j, v in enumerate(vals):
            txt = {1: '+', -1: '−', 0: 'mixed'}[v]
            differs = j > 0 and src != 0 and v != src
            if differs:
                ax.add_patch(plt.Rectangle((x0[j] - .5, y - .42), 1.0, .84, color='#fbe9e7', ec='none'))
            ax.text(x0[j], y, txt, fontsize=12 if v else 10, ha='center', va='center',
                    color=BAD if differs else INK, fontweight='bold' if differs else 'normal')
    for j, c in enumerate(cols):
        ax.text(x0[j], n + .9, c, ha='center', fontsize=10, fontweight='bold')
    ax.set_xlim(-.1, 10.0); ax.set_ylim(.4, n + 1.3); ax.axis('off')
    ax.set_title('Sign of each signal; red = differs from the source', loc='left', fontsize=11)
    fig.savefig(path, dpi=170, bbox_inches='tight'); plt.close(fig)


def build_sheets():
    from contributor_tools.common.review_sheet import page
    plt = style()
    probe, census = json.loads(PROBE.read_text()), json.loads(CENSUS.read_text())
    summ = build_summary(probe, census)
    layout2 = {(x['recording'], x['side']) for x in census['kinetic_layout'] if x['power_nonzero_components'] == [3]}
    for name in ('UM21-C03', 'D-UM21-C03-1'):
        folder = SHEETS / name
        folder.mkdir(parents=True, exist_ok=True)
        for old in folder.glob('*.png'):
            old.unlink()
    fig_signs(plt, probe, layout2, SHEETS / 'UM21-C03/fig1_signs.png')
    stride = probe['random_stride']
    fig_moment(plt, stride, 'knee', SHEETS / 'UM21-C03/fig2a_knee.png')
    fig_moment(plt, stride, 'ankle', SHEETS / 'UM21-C03/fig2b_ankle.png')
    fig_episode(plt, census['figure_episode'], summ['clean_inside'], 'raw', SHEETS / 'UM21-C03/fig3a_raw.png')
    fig_episode(plt, census['figure_episode'], summ['clean_inside'], 'fixed', SHEETS / 'UM21-C03/fig3b_fixed.png')
    fig_sign_table(plt, SHEETS / 'D-UM21-C03-1/fig1_signs.png')

    t = {(r['channel'], r['convention'], r['evidence']): r for r in summ['table']}
    won = lambda key: sum(v['legs_where_best'] for v in t[key]['by_sample'].values())
    legs = lambda key: sum(v['legs'] for v in t[key]['by_sample'].values())
    ang = [('PelvisAngles', 'clinical', 'marker pelvis angle'), ('HipAngles', 'clinical', 'marker hip angle'),
           ('KneeAngles', 'clinical', 'marker knee angle'), ('AnkleAngles', 'clinical', 'marker ankle angle')]
    ang_won, ang_legs = sum(won(k) for k in ang), sum(legs(k) for k in ang)
    mev = 'force-plate lever-arm internal moment, one fitted CoP shift per plate'
    knee_won, ank_won, hip_won = (won((f'{j}Moment', 'clinical', mev)) for j in ('Knee', 'Ankle', 'Hip'))
    ep = summ['episode']['branch_episode']
    zf = summ['episode']['zero_fill']
    kin = summ['kinetic_layout']
    a_rows = summ['episode']['ankle_channels_with_alternate_frames']
    main = next(r for r in a_rows if r['recording'] == ep['recording'] and r['side'] == ep['side'])

    def published_better(joint):  # legs where the published sign of component 1 beats the flipped sign (counterclockwise targets)
        n = 0
        for _, _, _, rows in rows_of(probe, lambda side, j=joint: side['moments'][j]['fitted_registration']['rhr']):
            a, b = pick(rows, 1, 1), pick(rows, 1, -1)
            n += a['median_abs'] < b['median_abs']
        return n
    knee_mirror, ankle_match = 16 - published_better('Knee'), published_better('Ankle')
    steps = ep['inside_step_p50_p95_deg']
    chips = [('pass' if ang_won == ang_legs else 'fail', f'pelvis, hip, knee, ankle angles: 1st component with the published sign fits best in all {ang_legs // 4} legs' if ang_won == ang_legs else f'angle channels: published fit best in {ang_won} of {ang_legs} leg-channels'),
             ('pass' if knee_mirror >= 14 and ankle_match >= 14 else 'fail',
              f'knee moment is flexor-positive, the mirror of the counterclockwise force-plate estimate ({knee_mirror} of 16 legs); ankle matches as published ({ankle_match} of 16)'),
             ('fail', f'power stored two ways: {len(kin["power_layout_2_recordings"])} of 50 recordings use another slot and sign'),
             ('pass', f'broken ankle stretch: re-expressed strides match the leg\'s other strides ({len(summ["clean_inside"])} of {len(census["figure_episode"]["inside_pairs"])})'),
             ('unchecked', f'{len(census["figure_episode"]["inside_pairs"]) - len(summ["clean_inside"])} strides in it with sudden jumps, cause unknown'),
             ('fail', f'(0,0,0) filler inside walking in {zf["channels_with_zero_frames_between_first_and_last_heel_strike"]} of {zf["channels_scanned"]} angle channels'),
             ('unchecked', f'hip moment sign: weak force-plate check (best in {hip_won} of 16 legs)'),
             ('unchecked', 'level walking: none drawn in either sample')]
    pairs = len(census['figure_episode']['inside_pairs'])
    page(SHEETS / 'UM21-C03/index.html', title='Treadmill sign fit',
         ask='Look at 3 figures, then answer one decision.',
         headline='UMich 2021 treadmill signals match clinical signs; pure counterclockwise flips three',
         chips=chips,
         figures=[('fig1_signs.png', 'Which source signs disagree with counterclockwise-positive?',
                   'Red rows need a flip.', 'Sign preference of each source channel against counterclockwise evidence, one dot per leg'),
                  (['fig2a_knee.png', 'fig2b_ankle.png'], 'How does each source moment compare with the force plates?',
                   'Knee is flexor-positive, so mirrored; ankle matches.', 'Knee and ankle moment over one random stride, source versus force-plate estimate'),
                  (['fig3a_raw.png', 'fig3b_fixed.png'], 'Does re-expression restore the broken ankle stretch?',
                   'Grey: same ankle, other strides.', 'Ankle strides inside the episode before and after re-expression against strides outside it')],
         decision={'question': 'How should the broken right-ankle stretch in one recording be released?',
                   'columns': ['Left out', 'Released', 'Needs first'],
                   # Ordered by how many ankle strides from this recording-side are released, fewest first.
                   'rows': [('A · none', ['the whole right ankle', '0 strides', '—']),
                            ('B · outside only', [f'{pairs} inside strides', f'{ep["strides_outside_duration_screened"]} strides', '—']),
                            ('C · re-express', [f'{pairs - len(summ["clean_inside"])} jump strides',
                                                f'{ep["strides_outside_duration_screened"] + len(summ["clean_inside"])} strides', 'rule logged per frame']),
                            ('defer', ['whole right ankle, for now', '0 strides until answered', '—'])],
                   'footnote': 'Source copies stay unchanged.',
                   'recommendation': f'C, medium confidence. Inside the stretch, re-expressed values span the same 1st-99th percentile ranges as the outside strides in all three components, and orientation changes by {steps[1]} degrees per frame at the 95th percentile (outside: {ep["outside_step_p50_p95_deg"][1]}). Strides with sudden jumps stay out. B is the conservative fallback.'},
         not_shown=['Software behind each power layout', 'A strong hip moment check', 'Running, stairs, transitions'],
         reply='ankle stretch: A, B, C or defer  |  what looks wrong',
         details=['Decision D-UM21-C03-2, task UM21-C03.',
                  f'Seeds {SEED_A} (A: {", ".join(probe["samples"]["A"])}) and {SEED_B} (B, disjoint: {", ".join(probe["samples"]["B"])}).',
                  f'Episode {ep["recording"]} {ep["side"]}: runs {ep["runs_1based"]} (1-based frames); jump-frame clusters {ep["orientation_step_clusters_1based"]} (1-based); inside step median/95th percentile {steps} deg.',
                  f'Power layout 2 recordings: {", ".join(kin["power_layout_2_recordings"])}.',
                  f'Peak memory: probe {probe["peak_rss_mib"]} MiB, census {census["peak_rss_mib"]} MiB.',
                  'Evidence: docs/quality/audits/um21-c03-conventions.json; builder contributor_tools/review_um21_c03_conventions.py'])

    page(SHEETS / 'D-UM21-C03-1/index.html', title='Sagittal sign rule',
         ask='Choose the LocoHub sagittal sign rule.',
         headline='Person faces right, counterclockwise positive: three signals disagree with clinical names',
         chips=[('pass', 'UMich angles and moments carry the column A signs'),
                ('pass', 'power sign is the same in A, B and C'),
                ('unchecked', 'other LocoHub datasets under B or C'),
                ('unchecked', 'which rule other datasets\' users expect')],
         figures=[('fig1_signs.png', 'What sign does each signal get under each option?',
                   'Moments are internal: muscles acting on the joint.', 'Table of plus and minus signs per signal for the source and options A, B and C')],
         decision={'question': 'Which sagittal sign rule should LocoHub adopt?',
                   'columns': ['Signs flipped from source', 'Knee flexion', 'Pelvis forward tilt'],
                   # Ordered by how many signals differ from the published source sign, fewest first.
                   'rows': [('A · clinical names', ['none', 'positive', 'positive']),
                            ('B · segments counterclockwise', ['pelvis tilt', 'positive', 'negative']),
                            ('C · counterclockwise for all', ['pelvis tilt, knee angle, knee moment', 'negative', 'negative']),
                            ('defer', ['none yet', 'unchanged', 'unchanged'])],
                   'footnote': 'B and C change every dataset\'s affected columns; all reversible before release.',
                   'recommendation': 'B, low confidence. Segment angles have no anatomical name, so counterclockwise is the natural rule and composes cleanly (thigh = pelvis + hip); joint columns are named flexion and dorsiflexion, and a knee flexion column that is negative in flexion invites misuse. A is the cheapest; C is the purest but breaks the names.'},
         not_shown=['Frontal and transverse signs', 'GRF and CoP axes', 'Datasets other than UMich 2021'],
         reply='sign rule: A, B, C or defer',
         details=['Decision D-UM21-C03-1, task UM21-C03.',
                  'Frame: x walking direction, y up, z = x cross y = the person\'s right side (out of the page). Counterclockwise about +z is positive.',
                  'Power = moment x joint speed is unchanged when both flip, so every option gives generation positive.',
                  'The historical LocoHub reference said "right-hand rule" and also "knee flexion +" and "pelvis anterior tilt +"; under a person facing right those two contradict each other.',
                  'Builder: contributor_tools/review_um21_c03_conventions.py'])

    inputs = {str(Path(x).relative_to(ROOT)): digest(x) for x in PRIOR + [SOURCE_RECEIPT]}
    data = {
        'task_id': 'UM21-C03', 'status': 'review', 'scientific_approval': False,
        'question': 'Find the convention that matches the UMich 2021 treadmill data best and is consistent with the right-hand rule with the person facing right.',
        'scope': 'Streaming/Tread (50 recordings): sagittal angle, moment and power channels. Fits on 8 recordings (two disjoint seeds); joint-angle and kinetic-layout census on all 50.',
        'source': probe['source'], 'inputs_sha256': inputs,
        'outputs_sha256': {str(PROBE.relative_to(ROOT)): digest(PROBE), str(CENSUS.relative_to(ROOT)): digest(CENSUS),
                           str(Path(__file__).relative_to(ROOT)): digest(Path(__file__))},
        'convention_proposal': {
            'frame': 'x = walking direction, y = up (gravity opposite), z = x cross y = the person\'s right side, out of the page when the person faces right. Rotations counterclockwise about +z are positive (right-hand rule). Both legs use the same frame.',
            'derivations': {
                'segment angles': 'Thigh/shank: long axis from straight down, distal end forward = counterclockwise = +. Foot: heel-to-toe from forward horizontal, toes up = +. Pelvis: PSIS-to-ASIS from forward horizontal; anterior tilt lowers the front = clockwise = negative.',
                'joint angles': 'Distal minus proximal segment angle. Hip = thigh - pelvis: flexion +. Knee = shank - thigh: flexion swings the shank back = clockwise = negative. Ankle = foot - shank: dorsiflexion +.',
                'moments': 'Internal (net muscle and tissue) moment on the distal segment, from inverse dynamics; external = minus internal in the quasi-static sense. Counterclockwise on the distal segment is +: hip flexor +, knee extensor + (knee flexor negative), ankle dorsiflexor + (plantarflexor negative).',
                'power': 'Joint power = internal moment x joint angular velocity, both in the same convention; flipping both leaves power unchanged. Generation is positive under every option.'},
            'conflicts_with_clinical_names': ['pelvis anterior tilt (negative under pure RHR)', 'knee flexion angle (negative)', 'knee flexion moment (negative)'],
            'sign_table': [{'signal': s, 'positive_event': e, 'pure_rhr': r, 'clinical': c, 'um21_source': ('mixed' if u == 0 else u)} for s, e, r, c, u in SIGN_TABLE],
            'options': {k: {'label': v[0], 'signs': v[1]} for k, v in OPTIONS.items()},
            'historical_reference_note': 'git 330789e docs/reference/index.md stated "right-hand rule" together with knee flexion + and pelvis anterior tilt +; these cannot all hold with a person facing right.',
            'choice': 'José (decision D-UM21-C03-1). Not picked here.'},
        'vicon_evidence': VICON,
        'method': {
            'seeds': probe['seeds'], 'samples': probe['samples'],
            'angle_targets': 'Marker sagittal angles in the frame above: pelvis PSIS->ASIS midpoints, thigh greater trochanter->knee centre (mid lateral/medial), shank knee->ankle centre (mid malleoli), foot heel->toe; joint angles as segment differences. Forward = mean horizontal PSIS->ASIS direction per recording.',
            'moment_targets': 'Internal moment = -(r x GRF)_z per joint, r = CoP - joint centre, GRF on the foot = -(plate force). Plate data block-averaged to 100 Hz and rotated by the README slope (sign from the heel path in the marker frame; marker frame is gravity-aligned, plates tilt with the belt). Mass = mean |R+L plate force| / g. One CoP shift (forward, up) per plate fitted jointly for hip, knee and ankle under each of the 8 sign combinations; the best combination sets the shift. Stance = own-plate vertical force > 20 % body weight. Ignores segment weight and inertia (worst for the hip); hip centre proxy = greater trochanter.',
            'power_targets': 'Independent: lever-arm moment x marker joint angular velocity (5-frame mean, central difference) in stance. Internal: source moment 1 x d(source angle 1)/dt.',
            'candidates': 'Every component (1-3) x sign (+/-); angles also a median offset. Ranked by median absolute residual (robust to marker glitch frames); RMS, p95, correlation and least-squares slope reported. Alternate-branch and (0,0,0) frames excluded.',
            'conventions': 'Each fit is run against pure-RHR targets and against clinical targets (pelvis, knee angle and knee moment sign-flipped).'},
        'per_channel': summ['table'],
        'registration': summ['registration'],
        'kinetic_layout': summ['kinetic_layout'],
        'ankle_episode_census': summ['episode'],
        'recommended_transforms_if_option_A': {'PelvisAngles': 'component 1 x pi/180', 'HipAngles': 'component 1 x pi/180', 'KneeAngles': 'component 1 x pi/180',
                                               'AnkleAngles': 'component 1 x pi/180 after the re-expression rule (if adopted)', 'HipMoment/KneeMoment/AnkleMoment': 'component 1, N*m/kg as is',
                                               'Power': 'layout 1: -component 1; layout 2: +component 3 (W/kg); remains source-only until reviewed',
                                               'foot segment (candidate, not proposed)': 'FootProgressAngles: -(component 1) - 90 deg tracks marker foot pitch, but whole-recording alternate branches occur'},
        'sign_changes_by_option': {'A': 'none', 'B': 'pelvis tilt x -1 (and every pelvis-based recipe uses + pelvis)', 'C': 'pelvis tilt, knee angle and knee moment x -1'},
        'agent_actions_logged': ['Ranked candidates by median absolute residual after finding marker-label glitches (pelvis marker tilt up to 160 deg) that dominated RMS in AB08/d10 and AB05/d10.',
                                 'Treated exact (0,0,0) triples as missing in fits and census.',
                                 'Kept power, FootProgressAngles and non-sagittal components source-only (no change from C01).'],
        'limitations': ['No scientific approval; the sign rule is a proposal (D-UM21-C03-1).',
                        'Fits cover 8 of 50 recordings (16 legs); none is level walking. The census covers all 50 for joint angles and kinetic layout only.',
                        'Lever-arm moments ignore segment weight and inertia and use a fitted CoP shift; they test sign and approximate scale, not exact values. Hip is weak.',
                        'Marker targets use the greater trochanter, not the hip joint centre, and Plug-in Gait static offsets are unknown; offsets are reported, not interpreted.',
                        'The Plug-in Gait ankle sequence is not documented (Vicon: not strict Cardan). The alternate-solution identity holds for every Cardan order, so the order is not identified by it.',
                        'The cause of the two power layouts and of the ankle episode jump frames is unknown; author question pending.'],
        'peak_rss_mib': {'probe': probe['peak_rss_mib'], 'census': census['peak_rss_mib']},
        'generated_by': 'contributor_tools/review_um21_c03_conventions.py sheet'}
    SUMMARY.write_text(json.dumps(data, indent=1) + '\n')
    print(json.dumps({'summary_sha256': digest(SUMMARY), 'chips': chips}, indent=1))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('step', choices=['probe', 'census', 'sheet'])
    args = parser.parse_args()
    os.nice(max(0, 19 - os.nice(0)))
    {'probe': run_probe, 'census': run_census, 'sheet': build_sheets}[args.step]()


if __name__ == '__main__':
    main()
