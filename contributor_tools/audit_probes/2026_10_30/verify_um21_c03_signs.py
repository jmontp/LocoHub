"""Independent verifier probe for UM21-C03 (UMich 2021 treadmill sagittal signs).

Written from scratch; does not import the worker's builder. Read-only on Streaming.mat
(bounded per-dataset reads, one recording at a time). Writes one JSON to the path given
by --out (scratch, not under converted_datasets/).

Steps:
  fit      marker angles and force-plate lever-arm moments vs source channels on a fresh sample
  episode  AB07/i10 right ankle: alternate Cardan solution identity, run bounds, jump frames
  census   |component 2| > 90 deg in all 500 joint-angle channels; power storage layout in all 300 power channels

Frame: forward = mean horizontal PSIS->ASIS direction, up = +z (markers), angles counterclockwise
about the person's right side (pure right-hand rule with the person facing right).
"""
import os
for k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[k] = '1'
import argparse
import json
import random
import resource
from pathlib import Path

import h5py
import numpy as np

SRC = Path(__file__).resolve().parents[3] / 'contributor_tools/conversion_scripts/Umich_2021/Streaming.mat'
SEED = 20261101
WORKER_SAMPLES = {'AB07/i5', 'AB03/i5', 'AB08/d10', 'AB05/d5', 'AB05/d10', 'AB04/d5', 'AB06/d5', 'AB01/i5'}
SLOPE = {'d10': -10.0, 'd5': -5.0, 'i0': 0.0, 'i5': 5.0, 'i10': 10.0}
G = 9.81


def rss():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def recordings(f):
    return sorted(f'{s}/{c}' for s in f['Streaming'] for c in f[f'Streaming/{s}/Tread'])


def read(t, path, zero_nan=True):
    x = t[path][...].astype(float)
    if zero_nan:
        x[:, (x == 0).all(0)] = np.nan
    return x


def marker(t, name):
    m = t[f'markers/{name}'][...]
    p = m[:3].copy()
    p[:, m[3] != 1] = np.nan
    return p


# ------------------------------------------------------------------ fit

def candidates(target, src, mask):
    out = []
    for c in range(3):
        for s in (1, -1):
            x = s * src[c]
            ok = mask & np.isfinite(x) & np.isfinite(target)
            if ok.sum() < 100 or np.nanstd(x[ok]) == 0:
                continue
            d = target[ok] - x[ok]
            off = np.median(d)
            out.append(dict(component=c + 1, sign=s, offset=round(float(off), 2),
                            median_abs=round(float(np.median(np.abs(d - off))), 3),
                            corr=round(float(np.corrcoef(x[ok], target[ok])[0, 1]), 3)))
    return sorted(out, key=lambda r: r['median_abs'])


def block_mean(x, k=10):
    n = x.shape[1] // k
    return x[:, :n * k].reshape(x.shape[0], n, k).mean(2)


def fit_recording(f, rec):
    subj, cond = rec.split('/')
    t = f[f'Streaming/{subj}/Tread/{cond}']
    asi = (marker(t, 'LASI') + marker(t, 'RASI')) / 2
    psi = (marker(t, 'LPSI') + marker(t, 'RPSI')) / 2
    h = np.nanmean((asi - psi)[:2], 1)
    fwd = np.array([h[0], h[1]]) / np.hypot(*h)

    def sag(p):  # (forward, up)
        return np.vstack([p[0] * fwd[0] + p[1] * fwd[1], p[2]])

    pel = sag(asi - psi)
    pelvis = np.degrees(np.arctan2(pel[1], pel[0]))  # PSIS->ASIS from forward horizontal, CCW +
    lF = block_mean(read(t, 'forceplates/LForce', False))
    rF = block_mean(read(t, 'forceplates/RForce', False))
    n = min(lF.shape[1], asi.shape[1])
    mass = np.mean(-(lF[2, :n] + rF[2, :n])) / G
    # plate fore-aft axis sign: CoP must lie under the foot (heel..toe) during stance; shared by both plates
    def axis_sign(P, F):
        C = block_mean(read(t, f'forceplates/{P}CoP', False))[1, :n] / 1000.0
        hs, ts = sag(marker(t, f'{P}HEE'))[0, :n], sag(marker(t, f'{P}TOE'))[0, :n]
        st = (-F[2, :n] > 0.2 * mass * G) & np.isfinite(hs + ts) & (C != 0)
        res = []
        for s in (1, -1):
            b = np.median(((hs + ts) / 2)[st] - s * C[st])
            res.append((np.mean((s * C[st] + b > np.minimum(hs, ts)[st] - 0.03) & (s * C[st] + b < np.maximum(hs, ts)[st] + 0.03)), s))
        return max(res)[1]
    s_ax = axis_sign('R', rF)
    # plate tilt: sign that brings the mean gravity-frame horizontal force (both plates) closest to zero
    th = np.radians(abs(SLOPE[cond]))
    Fy = s_ax * -(lF[1, :n] + rF[1, :n])
    Fz = -(lF[2, :n] + rF[2, :n])
    resid = {sg: float(np.mean(Fy * np.cos(sg * th) - Fz * np.sin(sg * th)) / (mass * G)) for sg in (1, -1)}
    tilt_sign = min(resid, key=lambda k: abs(resid[k]))
    out = {'recording': rec, 'mass_kg_from_plates': round(float(mass), 1), 'forward_xy': np.round(fwd, 4).tolist(),
           'tilt_sign': tilt_sign, 'plate_axis_sign_R': s_ax, 'mean_horizontal_force_BW_by_tilt_sign': {str(k): round(v, 4) for k, v in resid.items()}, 'legs': {}}
    for side in ('R', 'L'):
        P = side
        hip = marker(t, f'{P}GT')
        knee = (marker(t, f'{P}KNE') + marker(t, f'{P}KNEM')) / 2
        ank = (marker(t, f'{P}ANK') + marker(t, f'{P}ANKM')) / 2
        hee, toe = marker(t, f'{P}HEE'), marker(t, f'{P}TOE')
        th_v, sh_v, ft_v = sag(knee - hip), sag(ank - knee), sag(toe - hee)
        thigh = np.degrees(np.arctan2(th_v[0], -th_v[1]))
        shank = np.degrees(np.arctan2(sh_v[0], -sh_v[1]))
        foot = np.degrees(np.arctan2(ft_v[1], ft_v[0]))
        rhr = {'Pelvis': pelvis, 'Hip': thigh - pelvis, 'Knee': shank - thigh, 'Ankle': foot - shank}
        clin_sign = {'Pelvis': -1, 'Hip': 1, 'Knee': -1, 'Ankle': 1}
        leg = {'angles': {}, 'moments': {}}
        for ch, target in rhr.items():
            src = read(t, f'jointAngles/{P}{ch}Angles')
            m = min(src.shape[1], target.size)
            mask = np.ones(m, bool)
            res = candidates(clin_sign[ch] * target[:m], src[:, :m], mask)
            leg['angles'][ch] = {'best_clinical': res[0], 'second': res[1] if len(res) > 1 else None,
                                 'comp1_opposite': next((r for r in res if r['component'] == 1 and r['sign'] == -1), None)}
        # lever-arm internal moments, RHR (CCW +), in stance on own plate
        F = block_mean(read(t, f'forceplates/{P}Force', False))[:, :n]
        C = block_mean(read(t, f'forceplates/{P}CoP', False))[:, :n] / 1000.0
        grf_plate = -F  # force on the foot, plate frame
        a = tilt_sign * th
        stance = grf_plate[2] > 0.2 * mass * G
        hs, ts = sag(hee)[:, :n], sag(toe)[:, :n]
        best_reg = None
        for s in (1, -1):  # plate fore-aft axis sign and offset registered to the foot during stance
            fa = s * C[1] * np.cos(a)
            mid = (hs[0] + ts[0]) / 2
            ok = stance & np.isfinite(mid) & (C[1] != 0)
            # CoP must progress heel->toe relative to the foot: corr(CoP - mid, time-in-stance) > 0 checked below
            b = np.median(mid[ok] - fa[ok])
            frac_in = np.mean((fa[ok] + b > np.minimum(hs[0], ts[0])[ok] - 0.03) & (fa[ok] + b < np.maximum(hs[0], ts[0])[ok] + 0.03))
            rel = fa[ok] + b - hs[0][ok]
            if best_reg is None or frac_in > best_reg[0]:
                best_reg = (frac_in, s, b)
        frac_in, s_ax, b = best_reg
        cop_f = s_ax * C[1] * np.cos(a) + b
        # CoP height: sole height under the foot at the CoP forward position, ~1.5 cm below the heel/toe markers
        w = np.clip((cop_f - hs[0]) / np.where(ts[0] - hs[0] == 0, np.nan, ts[0] - hs[0]), 0, 1)
        cop_u = hs[1] + w * (ts[1] - hs[1]) - 0.015
        # force in gravity frame: plate y -> along belt (sign s_ax), plate z -> normal
        fy, fz = s_ax * grf_plate[1], grf_plate[2]
        Ff = fy * np.cos(a) - fz * np.sin(a)
        Fu = fy * np.sin(a) + fz * np.cos(a)
        leg['registration'] = {'plate_axis_sign': s_ax, 'cop_within_foot_frac': round(float(frac_in), 3),
                               'stance_frames': int(stance.sum())}
        for jn, jc in (('Hip', hip), ('Knee', knee), ('Ankle', ank)):
            j = sag(jc)[:, :n]
            rf, ru = cop_f - j[0], cop_u - j[1]
            ext = rf * Fu - ru * Ff  # external moment of GRF about the joint, z (CCW +)
            internal = -ext / mass
            src = read(t, f'jointMoments/{P}{jn}Moment')[:, :n]
            ok = stance & np.isfinite(internal) & np.isfinite(src[0])
            res = []
            for c in range(3):
                for sg in (1, -1):
                    x = sg * src[c][ok]
                    if np.std(x) == 0:
                        continue
                    r = np.corrcoef(x, internal[ok])[0, 1]
                    sl = np.polyfit(x, internal[ok], 1)[0]
                    rmsd = np.sqrt(np.mean((internal[ok] - x) ** 2))
                    res.append(dict(component=c + 1, sign=sg, corr=round(float(r), 3), slope=round(float(sl), 3), rms=round(float(rmsd), 3)))
            res.sort(key=lambda r: r['rms'])
            # physiological pattern on source comp 1: mean over late stance (last 40 % of each stance run)
            idx = np.flatnonzero(stance)
            runs = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
            early, late = [], []
            for rr in runs:
                if 40 <= rr.size <= 150:
                    early.append(np.nanmean(src[0][rr[:int(0.15 * rr.size)]]))
                    late.append(np.nanmean(src[0][rr[int(0.6 * rr.size):]]))
            leg['moments'][jn] = {'best_rms': res[0], 'best_corr': max(res, key=lambda r: r['corr']), 'comp1_plus': next(r for r in res if r['component'] == 1 and r['sign'] == 1),
                                  'comp1_minus': next(r for r in res if r['component'] == 1 and r['sign'] == -1),
                                  'source_comp1_mean_first15pct_stance': round(float(np.nanmedian(early)), 3),
                                  'source_comp1_mean_last40pct_stance': round(float(np.nanmedian(late)), 3),
                                  'lever_internal_mean_first15pct': round(float(np.nanmedian([np.nanmean(internal[rr[:int(0.15 * rr.size)]]) for rr in runs if 40 <= rr.size <= 150])), 3),
                                  'lever_internal_mean_last40pct': round(float(np.nanmedian([np.nanmean(internal[rr[int(0.6 * rr.size):]]) for rr in runs if 40 <= rr.size <= 150])), 3),
                                  'stance_runs': len(early)}
        out['legs'][side] = leg
    return out


# ------------------------------------------------------------------ episode

def R(axis, deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    o, z = np.ones_like(a), np.zeros_like(a)
    if axis == 'x':
        m = [[o, z, z], [z, c, -s], [z, s, c]]
    elif axis == 'y':
        m = [[c, z, s], [z, o, z], [-s, z, c]]
    else:
        m = [[c, -s, z], [s, c, z], [z, z, o]]
    return np.moveaxis(np.array(m), [0, 1], [-2, -1])


def mat(tr, order):
    return R(order[0], tr[0]) @ R(order[1], tr[1]) @ R(order[2], tr[2])


def angle_between(A, B):
    c = (np.einsum('nij,nij->n', A, B) - 1) / 2
    return np.degrees(np.arccos(np.clip(c, -1, 1)))


def wrap(x):
    return (x + 180) % 360 - 180


def episode(f):
    t = f['Streaming/AB07/Tread/i10']
    a = t['jointAngles/RAnkleAngles'][...].astype(float)
    zero = (a == 0).all(0)
    alt = (np.abs(a[1]) > 90) & ~zero
    idx = np.flatnonzero(alt)
    runs = [[int(r[0]), int(r[-1])] for r in np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)] if idx.size else []
    re = a.copy()
    re[0, alt] = wrap(a[0, alt] + 180)
    re[1, alt] = wrap(180 - a[1, alt])
    re[2, alt] = wrap(a[2, alt] + 180)
    orders = ['xyz', 'xzy', 'yxz', 'yzx', 'zxy', 'zyx']
    ident = {o: float(np.max(np.abs(mat(a[:, alt], o) - mat(re[:, alt], o)))) for o in orders}
    mirror = re.copy()
    mirror[:, alt] = -a[:, alt]
    mirr = {o: float(np.max(np.abs(mat(a[:, alt], o) - mat(np.array([a[0, alt] + 180, a[1, alt], a[2, alt]]), o)))) for o in orders}
    inside, outside = re[:, alt], re[:, ~alt & ~zero]
    pct = lambda x: [[round(float(v), 1) for v in np.percentile(row, [1, 99])] for row in x]
    # frame-to-frame orientation change of the raw triples (order-invariant? no: report yxz and xyz)
    jumps = {}
    for o in ('yxz', 'xyz', 'zyx'):
        M = mat(a, o)
        step = angle_between(M[:-1], M[1:])
        valid = ~zero[:-1] & ~zero[1:]
        lo, hi = (runs[0][0] - 5, runs[-1][1] + 5) if runs else (0, 0)
        big = [int(i + 1) for i in np.flatnonzero((step > 20) & valid) if lo <= i + 1 <= hi]
        jumps[o] = {'frames_step_over_20deg_in_episode_window_0based_landing_frame': big,
                    'max_step_inside_excluding_jumps': round(float(np.percentile(step[lo:hi][valid[lo:hi]], 95)), 2)}
    # steps in component space of the re-expressed series at run boundaries
    bstep = []
    for r0, r1 in runs:
        for i in (r0, r1 + 1):
            if 0 < i < a.shape[1]:
                bstep.append({'frame': i, 'raw_step_deg': np.round(a[:, i] - a[:, i - 1], 1).tolist(),
                              'reexpressed_step_deg': np.round(wrap(re[:, i] - re[:, i - 1]), 1).tolist()})
    hs = np.asarray(t['events/RHS'][...]).ravel().astype(int)  # 1-based frames
    strides_in = [(int(x), int(y)) for x, y in zip(hs[:-1], hs[1:]) if alt[x - 1:y - 1].any()]
    return {'channel': 'AB07/i10 RAnkleAngles', 'frames': int(a.shape[1]), 'alt_frames': int(alt.sum()),
            'runs_0based_inclusive': runs, 'zero_fill_frames': int(zero.sum()),
            'identity_max_abs_matrix_diff_by_order': ident, 'c1_plus_180_only_max_diff_by_order': mirr,
            'inside_reexpressed_p1_p99': pct(inside), 'outside_p1_p99': pct(outside), 'inside_raw_p1_p99': pct(a[:, alt]),
            'jumps': jumps, 'run_boundary_steps': bstep, 'strides_touching_alt_frames': len(strides_in),
            'heel_strikes': int(hs.size)}


# ------------------------------------------------------------------ census

def census(f):
    recs = recordings(f)
    flagged, zero_inside, scanned = [], 0, 0
    layout = {}
    for rec in recs:
        s, c = rec.split('/')
        t = f[f'Streaming/{s}/Tread/{c}']
        for side in 'LR':
            for ch in ('Pelvis', 'Hip', 'Knee', 'Ankle', 'FootProgress'):
                a = t[f'jointAngles/{side}{ch}Angles'][...]
                zero = (a == 0).all(0)
                n_alt = int(((np.abs(a[1]) > 90) & ~zero).sum())
                scanned += 1
                if n_alt:
                    flagged.append({'recording': rec, 'side': side, 'channel': ch, 'alt_frames': n_alt})
            for j in ('Hip', 'Knee', 'Ankle'):
                p = t[f'jointPowers/{side}{j}Power'][...]
                z12 = bool((p[0] == 0).all() and (p[1] == 0).all())
                layout.setdefault(rec, []).append('2' if z12 else '1')
    lay = {r: sorted(set(v)) for r, v in layout.items()}
    l2 = sorted(r for r, v in lay.items() if v == ['2'])
    mixed = sorted(r for r, v in lay.items() if len(v) > 1)
    by_type = {}
    for x in flagged:
        by_type[x['channel']] = by_type.get(x['channel'], 0) + 1
    return {'angle_channels_scanned': scanned, 'flagged_by_type': by_type,
            'flagged_non_footprogress': [x for x in flagged if x['channel'] != 'FootProgress'],
            'power_layout2_recordings': l2, 'power_layout1_count': sum(v == ['1'] for v in lay.values()),
            'power_mixed_recordings': mixed}


def power_sign(f, recs):
    out = {}
    for rec in recs:
        s, c = rec.split('/')
        t = f[f'Streaming/{s}/Tread/{c}']
        for j in ('Ankle', 'Knee'):
            m = read(t, f'jointMoments/R{j}Moment')
            a = read(t, f'jointAngles/R{j}Angles')
            p = read(t, f'jointPowers/R{j}Power', zero_nan=False)
            w = np.gradient(np.radians(a[0])) * 100.0
            mp = m[0] * w
            ok = np.isfinite(mp)
            out[f'{rec} R{j}'] = {f'corr_comp{k + 1}': (round(float(np.corrcoef(mp[ok], p[k][ok])[0, 1]), 3) if np.std(p[k][ok]) > 0 else 'all zero/constant')
                                  for k in range(3)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('step', choices=['fit', 'episode', 'census'])
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 ** 2, 1536 * 1024 ** 2))
    st = SRC.stat()
    with h5py.File(SRC, 'r') as f:
        if args.step == 'fit':
            recs = recordings(f)
            pool = [r for r in recs if r not in WORKER_SAMPLES]
            rng = random.Random(SEED)
            sample = rng.sample(pool, 3)
            if not any(r.endswith('/i0') for r in sample):
                sample.append(rng.choice([r for r in pool if r.endswith('/i0') and r not in sample]))
            res = {'seed': SEED, 'rule': 'pool = 50 recordings minus the worker 8; random.Random(SEED).sample(pool, 3); '
                   'if no i0 drawn, the same rng .choice() of a remaining i0 recording', 'sample': sample,
                   'recordings': [fit_recording(f, r) for r in sample]}
        elif args.step == 'episode':
            res = episode(f)
        else:
            res = census(f)
            res['power_sign'] = power_sign(f, ['AB02/i0', 'AB05/i0'])
    after = SRC.stat()
    res['source_unchanged'] = (st.st_size, st.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
    res['peak_rss_mib'] = round(rss(), 1)
    Path(args.out).write_text(json.dumps(res, indent=1))
    print(json.dumps(res)[:200], res['peak_rss_mib'])


if __name__ == '__main__':
    main()
