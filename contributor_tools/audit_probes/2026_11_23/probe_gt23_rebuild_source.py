"""GT23-REBUILD read-only probes. One recording per invocation; prints JSON to stdout; writes nothing.

Modes (all read only the named recording's files, selected columns):
  markers  SUBJ REC   TRC marker presence and finite coverage (overall and in force-plate stance);
                      pelvis (PSIS->ASIS), shank (knee->ankle) and foot (heel->toe) sagittal angles from markers
  euler    SUBJ REC   Transforms_Euler segment rotations: which Euler convention reproduces IK pelvis (tilt, list, rotation)
  cop      SUBJ REC   global CoP re-expressed in the standard foot frame (origin 100 mm forward of ankle centre); known-value checks
  hs       SUBJ REC   authors' stride starts (Segmentation/*_parsing.mat) vs 20 N rising heel strikes
  moments  SUBJ REC   per-kg Joint_Moments x constant == local inverse_dynamics.sto (N*m)?  implied normalizing mass
Run with: flock /tmp/locohub-probe.lock nice -n 19 ionice -c 3 /usr/bin/time -v python3 this.py MODE SUBJ REC
"""
import itertools
import json
import resource
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation as Rot

ROOT = Path('/mnt/s/locomotion_data/Gtech_2023/RawData')
NEEDED = ['LASI', 'RASI', 'LPSI', 'RPSI', 'LGTR', 'RGTR', 'LKNE', 'LMKNE', 'RKNE', 'RMKNE', 'LANK', 'LMANK',
          'RANK', 'RMANK', 'LCAL', 'RCAL', 'LMT1', 'LMT5', 'RMT1', 'RMT5', 'LTHC', 'RTHC']


def read_trc(path, names_wanted):
    with open(path) as f:
        head = [next(f) for _ in range(8)]
    names = head[3].rstrip('\n').split('\t')
    first = next(i for i, l in enumerate(head) if i > 3 and l[:1].isdigit())
    rate = float(head[2].split('\t')[0])
    markers = [n for n in names[2:] if n]
    cols, found = [0, 1], []
    for m in sorted((x for x in names_wanted if x in markers), key=markers.index):
        if m in markers:
            i = markers.index(m)
            cols += [2 + 3 * i, 3 + 3 * i, 4 + 3 * i]
            found.append(m)
    df = pd.read_csv(path, sep='\t', skiprows=first, header=None, usecols=cols, dtype=np.float64)
    out = {'rate_hz': rate, 'n_markers_in_file': len(markers), 'all_markers': markers, 't': df[1].to_numpy()}
    for k, m in enumerate(found):
        out[m] = df.iloc[:, 2 + 3 * k:5 + 3 * k].to_numpy() / 1000.0
    return out, found


def fwd_dir(rasi, lasi):
    r = rasi - lasi
    f = np.cross(np.array([0.0, 1.0, 0.0]), r)
    f[:, 1] = 0.0
    return f / np.linalg.norm(f, axis=1, keepdims=True)


def markers(subj, rec):
    d, found = read_trc(ROOT / subj / 'MarkerData' / f'{rec}.trc', NEEDED)
    grf = pd.read_csv(ROOT / subj / 'CSV_Data' / rec / 'GroundFrame_GRFs.csv')
    n = len(d['t'])
    res = {'frames': n, 'rate_hz': d['rate_hz'], 'grf_rows': len(grf), 'markers_in_file': d['n_markers_in_file'],
           'missing_requested': [m for m in NEEDED if m not in found]}
    stance = {'R': (grf['RForceY_Vertical'].to_numpy() > 20), 'L': (grf['LForceY_Vertical'].to_numpy() > 20)}
    m = min(n, len(grf))
    cov = {}
    for k in found:
        fin = np.isfinite(d[k][:, 0])
        cov[k] = {'finite': round(float(fin.mean()), 4)}
        for s in 'LR':
            if k.startswith(s) and stance[s][:m].any():
                cov[k]['finite_in_own_stance'] = round(float(fin[:m][stance[s][:m]].mean()), 4)
    res['coverage'] = cov
    res['stance_samples'] = {s: int(stance[s].sum()) for s in 'LR'}
    ok = all(k in d for k in ['LASI', 'RASI', 'LPSI', 'RPSI'])
    if ok:
        asis, psis = (d['LASI'] + d['RASI']) / 2, (d['LPSI'] + d['RPSI']) / 2
        f = fwd_dir(d['RASI'], d['LASI'])
        pel = np.degrees(np.arctan2((asis - psis)[:, 1], np.einsum('ij,ij->i', asis - psis, f)))
        res['pelvis_deg_from_markers'] = {'mean': float(np.nanmean(pel)), 'sd': float(np.nanstd(pel))}
        res['pelvis_deg_percentiles_5_50_95'] = [float(x) for x in np.nanpercentile(pel, [5, 50, 95])]
        mot = ROOT / subj / 'MotionFile_EH' / 'IK_results.mot'
        pel_all = pel
        if mot.exists() and rec == 'normal_walk_1':
            ik = pd.read_csv(mot, sep='\t', skiprows=10, usecols=['time', 'pelvis_tilt', 'knee_angle_r', 'knee_angle_l'])
            k = min(len(ik), n)
            if abs(ik['time'].iloc[1] - ik['time'].iloc[0] - 1 / d['rate_hz']) < 1e-6:
                walk = (stance['L'][:k] | stance['R'][:k])
                walk = np.convolve(walk.astype(float), np.ones(201), 'same') > 0   # within 0.5 s of a stance sample
                ok2 = np.isfinite(pel[:k]) & walk
                a, b = pel[:k][ok2], ik['pelvis_tilt'].to_numpy()[:k][ok2]
                res['pelvis_vs_IK_tilt_walking_frames'] = {'frames': int(ok2.sum()), 'corr': float(np.corrcoef(a, b)[0, 1]),
                    'offset_mean_deg': float((a - b).mean()), 'offset_sd_deg': float((a - b).std()),
                    'sd_markers_deg': float(a.std()), 'sd_IK_deg': float(b.std())}
                res['_ik'] = {c: ik[c].to_numpy()[:k] for c in ('knee_angle_r', 'knee_angle_l')}
    for s, side in (('R', 'right'), ('L', 'left')):
        need = [s + x for x in ('KNE', 'MKNE', 'ANK', 'MANK', 'CAL', 'MT1', 'MT5')]
        if all(x in d for x in need) and ok:
            knee = (d[s + 'KNE'] + d[s + 'MKNE']) / 2
            ank = (d[s + 'ANK'] + d[s + 'MANK']) / 2
            toe = (d[s + 'MT1'] + d[s + 'MT5']) / 2
            shank = np.degrees(np.arctan2(np.einsum('ij,ij->i', ank - knee, f), -(ank - knee)[:, 1]))
            foot = np.degrees(np.arctan2((toe - d[s + 'CAL'])[:, 1], np.einsum('ij,ij->i', toe - d[s + 'CAL'], f)))
            st = stance[s][:min(n, len(grf))]
            mid = np.zeros(len(st), bool)
            idx = np.flatnonzero(st)
            if len(idx):
                # middle third of each contiguous stance
                runs = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
                for r in runs:
                    if len(r) >= 20:
                        a, b = r[len(r) // 3], r[2 * len(r) // 3]
                        mid[a:b] = True
            fm = foot[:len(mid)][mid]
            res[f'{side}_foot_deg_midstance_median'] = None if not np.isfinite(fm).any() else float(np.nanmedian(fm))
            res[f'{side}_shank_deg_percentiles_5_50_95'] = [float(x) for x in np.nanpercentile(shank, [5, 50, 95])]
            if '_ik' in res and s + 'GTR' in d:
                hip = d[s + 'GTR']
                thigh = np.degrees(np.arctan2(np.einsum('ij,ij->i', knee - hip, f), -(knee - hip)[:, 1]))
                kk = min(len(thigh), len(res['_ik']['knee_angle_' + s.lower()]))
                kn = (thigh - shank)[:kk]
                ik_k = -res['_ik']['knee_angle_' + s.lower()][:kk]
                walk = np.convolve(stance[s][:kk].astype(float), np.ones(201), 'same') > 0
                ok3 = np.isfinite(kn) & walk
                if ok3.sum() > 200:
                    res[f'{side}_knee_flexion_markers_vs_minus_IK_knee_angle'] = {
                        'frames': int(ok3.sum()), 'corr': float(np.corrcoef(kn[ok3], ik_k[ok3])[0, 1]),
                        'offset_mean_deg': float((kn[ok3] - ik_k[ok3]).mean()), 'resid_sd_deg': float((kn[ok3] - ik_k[ok3]).std()),
                        'peak_markers_deg': float(np.nanpercentile(kn[ok3], 99)), 'peak_IK_deg': float(np.percentile(ik_k[ok3], 99)),
                        'note': 'thigh from GTR->knee-centre marker line (hip centre not a marker), coarse'}
            res[f'{side}_ankle_centre_finite_in_stance'] = float(np.isfinite(ank[:len(st)][st][:, 0]).mean()) if st.any() else None
    res.pop('_ik', None)
    res['marker_names'] = d['all_markers'] if 'all_markers' in d else None
    return res


def euler(subj, rec):
    e = pd.read_csv(ROOT / subj / 'Transforms_Euler' / f'{rec}.csv')
    ik = pd.read_csv(ROOT / subj / 'MotionFile_EH' / 'IK_results.mot', sep='\t', skiprows=10,
                     usecols=['time', 'pelvis_tilt', 'pelvis_list', 'pelvis_rotation'])
    k = min(len(e), len(ik))
    sel = np.linspace(0, k - 1, 400).astype(int)
    ang = e[['pelvis_Z', 'pelvis_X', 'pelvis_Y']].to_numpy()[sel]
    r_ik = Rot.from_euler('ZXY', np.degrees(0) + ik[['pelvis_tilt', 'pelvis_list', 'pelvis_rotation']].to_numpy()[sel], degrees=True)
    best = []
    for seq in itertools.permutations('XYZ'):
        for intr in (True, False):
            for perm in itertools.permutations(range(3)):
                name = ''.join(seq)
                s = name if intr else name.lower()
                for deg in (False, True):
                    r = Rot.from_euler(s, ang[:, perm], degrees=deg)
                    err = np.degrees((r * r_ik.inv()).magnitude())
                    best.append((float(np.median(err)), float(err.max()), s, perm, deg))
    best.sort()
    return {'rows_euler': len(e), 'rows_ik': len(ik), 'first_col': e.columns[0], 'best_matches': best[:4],
            'time_first_diff': float(e.iloc[1, 0] - e.iloc[0, 0]), 'time_head': [float(x) for x in e.iloc[:3, 0]]}


def moments(subj, rec):
    jm = pd.read_csv(ROOT / subj / 'CSV_Data' / rec / 'Joint_Moments.csv')
    sto = pd.read_csv(ROOT / subj / 'MotionFile_EH' / 'inverse_dynamics.sto', sep='\t', skiprows=6)
    sto.columns = [c.strip() for c in sto.columns]
    k = min(len(jm), len(sto))
    out = {'rows_jm': len(jm), 'rows_sto': len(sto), 'time_aligned_max_abs_s': float(np.abs(jm['time'].to_numpy()[:k] - sto['time'].to_numpy()[:k]).max())}
    for c in ['hip_flexion_r_moment', 'knee_angle_r_moment', 'ankle_angle_r_moment', 'ankle_angle_l_moment', 'knee_angle_l_moment']:
        a, b = jm[c].to_numpy()[:k], sto[c].to_numpy()[:k]
        ok = np.isfinite(a) & np.isfinite(b) & (np.abs(a) > 0.2)
        if ok.sum() > 100:
            ratio = b[ok] / a[ok]
            slope = float((a[ok] @ b[ok]) / (a[ok] @ a[ok]))
            out[c] = {'n': int(ok.sum()), 'slope_Nm_over_perkg': slope, 'ratio_median': float(np.median(ratio)),
                      'corr': float(np.corrcoef(a[ok], b[ok])[0, 1])}
    return out


def hs(subj, rec):
    """Authors' labelled stride starts vs heel strikes found by the README rule (vertical force rising through 20 N)."""
    import glob
    import scipy.io as sio
    grf = pd.read_csv(ROOT / subj / 'CSV_Data' / rec / 'GroundFrame_GRFs.csv')
    t = grf['time'].to_numpy()
    out = {'rate_hz': float(1 / np.median(np.diff(t))), 'files': {}}
    ours = {}
    for s, side in (('L', 'left'), ('R', 'right')):
        f = grf[s + 'ForceY_Vertical'].to_numpy()
        above = np.nan_to_num(f, nan=0.0) > 20
        ours[side] = t[np.flatnonzero(~above[:-1] & above[1:]) + 1]
    for p in sorted(glob.glob(str(ROOT.parent / 'Segmentation' / subj / f'{rec}_*parsing.mat'))):
        m = sio.loadmat(p, simplify_cells=True)
        for side in ('left', 'right'):
            iv = np.atleast_2d(m.get(side, np.empty((0, 2))))
            if iv.size == 0 or ours[side].size == 0:
                out['files'][Path(p).name + ':' + side] = {'author_strides': int(iv.shape[0]) if iv.size else 0, 'our_heel_strikes_in_recording': int(ours[side].size)}
                continue
            st = iv[:, 0]
            nearest = np.abs(ours[side][None, :] - st[:, None]).min(axis=1)
            out['files'][Path(p).name + ':' + side] = {
                'author_strides': int(len(st)), 'median_abs_offset_ms': float(np.median(nearest) * 1000),
                'max_abs_offset_ms': float(nearest.max() * 1000), 'share_within_10ms': float((nearest <= 0.0101).mean()),
                'share_within_50ms': float((nearest <= 0.0501).mean()),
                'our_heel_strikes_in_recording': int(ours[side].size)}
    return out


def cop(subj, rec):
    """CoP in the standard foot frame (origin 100 mm forward of the ankle centre along heel->toe) from markers + global CoP."""
    d, found = read_trc(ROOT / subj / 'MarkerData' / f'{rec}.trc', NEEDED)
    grf = pd.read_csv(ROOT / subj / 'CSV_Data' / rec / 'GroundFrame_GRFs.csv')
    n = min(len(d['t']), len(grf))
    out = {'frames_trc': len(d['t']), 'frames_grf': len(grf), 'time_diff_max_s': float(np.abs(d['t'][:n] - grf['time'].to_numpy()[:n]).max())}
    up = np.array([0.0, 1.0, 0.0])
    for s, side in (('L', 'left'), ('R', 'right')):
        fz = grf[s + 'ForceY_Vertical'].to_numpy()[:n] if (s + 'ForceY_Vertical') in grf else grf[s + 'ForceY_Vertical'].to_numpy()[:n]
        st = fz > 20
        if st.sum() < 40:
            out[side] = 'no stance with force above 20 N'
            continue
        ank = (d[s + 'ANK'] + d[s + 'MANK'])[:n] / 2
        heel = d[s + 'CAL'][:n]
        toe = (d[s + 'MT1'] + d[s + 'MT5'])[:n] / 2
        u = toe - heel
        u /= np.linalg.norm(u, axis=1, keepdims=True)
        uy = up - np.einsum('ij,ij->i', np.broadcast_to(up, u.shape), u)[:, None] * u
        uy /= np.linalg.norm(uy, axis=1, keepdims=True)
        uz = np.cross(u, uy)
        origin = ank + 0.1 * u
        c = grf[[s + 'COPX', s + 'COPY_Vertical', s + 'COPZ']].to_numpy()[:n]
        rel = c - origin
        ant = np.einsum('ij,ij->i', rel, u)
        ver = np.einsum('ij,ij->i', rel, uy)
        lat = np.einsum('ij,ij->i', rel, uz) * (1 if s == 'R' else -1)
        idx = np.flatnonzero(st & np.isfinite(ant))
        runs = [r for r in np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1) if len(r) >= 40]
        k = max(1, min(len(r) for r in runs) // 10) if runs else 0
        out[side] = {'stances': len(runs),
                     'anterior_m_first10pct_median': float(np.median([np.median(ant[r[:k]]) for r in runs])),
                     'anterior_m_last10pct_median': float(np.median([np.median(ant[r[-k:]]) for r in runs])),
                     'vertical_m_median': float(np.median(ver[idx])),
                     'lateral_m_median': float(np.median(lat[idx])), 'lateral_m_iqr': [float(x) for x in np.percentile(lat[idx], [25, 75])],
                     'ankle_height_above_floor_m_median': float(np.median(ank[idx, 1])),
                     'foot_length_m_median': float(np.median(np.linalg.norm((toe - heel)[idx], axis=1)))}
    return out


if __name__ == '__main__':
    mode, subj, rec = sys.argv[1:4]
    res = {'markers': markers, 'euler': euler, 'moments': moments, 'cop': cop, 'hs': hs}[mode](subj, rec)
    res['probe'] = {'mode': mode, 'subject': subj, 'recording': rec,
                    'self_reported_peak_rss_mib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024}
    print(json.dumps(res, indent=1, default=float))
