"""UM21-P01: per-recording pelvis heading census, UMich 2021 treadmill (read-only probe, AGENTS.md exception).

Question: in which of the 50 treadmill recordings did Plug-in Gait compute the
pelvis with the walking direction reversed, and which stored channels does that
change? Evidence is the markers, never the pelvis channel itself.

Reads one recording at a time from Streaming.mat (h5py, read only) in the UM21-T01
scope order and writes one JSON report to a path that must not exist. Nothing under
converted_datasets/ or source folders is written. No correction is applied.

Source channels (degrees): R/L PelvisAngles (1 tilt, 2 obliquity, 3 rotation),
R/L HipAngles (1 flexion, 2 adduction, 3 rotation), R/L KneeAngles (1 flexion),
R/L FootProgressAngles (3 = progression angle). Exact (0, 0, 0) triples are zero
fill and alternate-branch triples (|component 2| > 90) are counted and not used.

Marker frame (independent of Plug-in Gait's progression choice). Up = lab +z
(checked: pelvis markers above heel markers). Forward f = mean horizontal
PSIS-midpoint -> ASIS-midpoint direction over the recording (the person's own facing),
right = f x up. Markers with visibility flag != 1 or non-finite are missing.
Marker targets, degrees, per frame:
- pelvis tilt, anterior +: -atan2(up.d, f.d), d = ASIS mid - PSIS mid (the UM21-C03
  clinical pelvis target; C03 found the published sign with offsets within 0.1 deg).
- pelvis obliquity, right side up +, and pelvis yaw, right side forward +: from
  v = (RASI + RPSI)/2 - (LASI + LPSI)/2: atan2(up.v, right.v), atan2(f.v, right.v).
- thigh / shank sagittal (counterclockwise, distal end forward +): greater trochanter ->
  knee centre (mid KNE/KNEM), knee centre -> ankle centre (mid ANK/ANKM).
- hip flexion = thigh + pelvis tilt (thigh - pelvis segment angle).
- hip adduction: thigh frontal angle in the lab (knee medial +) + pelvis obliquity with
  the ipsilateral side up +.
- hip internal rotation: knee axis (pointing right) yaw minus pelvis yaw; negated for the left.
- foot progression, toe-out +: heel -> toe horizontal yaw from f (negated for the left).

Strides: consecutive same-side heel strikes (events RHS/LHS, 1-based frames),
50 <= length <= 250 frames (as UM21-C03). Right channels use right strides, left
channels left strides. A stride votes when >= 30 frames have the stored value and the
marker target.

Votes per stride:
- tilt sign: +1 (published sign) if median |m - p1| < median |m + p1| (no offset),
  else -1. The expected sign is +1, fixed a priori from UM21-C03.
- heading: circular mean of p3 over the stride; 'reversed' when |.| > 90 deg.
- obliquity, rotation, hip 1-3, foot progression: sign of the Pearson correlation of the
  stride's de-meaned stored component and de-meaned marker target. The expected sign is
  the majority over strides of recordings classified 'normal' (data-derived, reported
  with its reliability); a channel is judged only when that reliability >= 0.9.
- thigh / shank recipe (the released planar recipe after D-UM21-C01-1 C and
  D-UM21-C03-1 B): thigh = hip1 - p1, shank = hip1 - p1 - knee1. Vote +1 if the recipe
  with the stored p1 is closer (median absolute, no offset) to the marker segment angle
  than the recipe with -p1, else -1.

Classification rule (fixed in this file before AB04/i0 was looked at beyond the
CORE-04 verifier's finding; the blind run withholds AB04/i0):
per recording-side, H = circular median of stored pelvis rotation (valid frames),
V = fraction of voting strides whose tilt vote is +1.
- normal: both sides |H| < 90, V >= 0.9 and >= 20 voting strides.
- reversed: both sides |H| > 90, V <= 0.1 and >= 20 voting strides.
- unresolved: anything else, or a within-recording heading switch (fraction of strides
  with a reversed heading strictly between 0.05 and 0.95 on either side).
Per other channel in a reversed recording-side: 'flipped' if <= 10 % of strides agree
with the expected sign, 'unchanged' if >= 90 % agree, else 'unresolved'; 'not judged'
when the normal-recording reliability is < 0.9.

--blind withholds every AB04/i0 value from stdout and the report; the final report is
made without --blind and must reproduce the blind run's records and expected signs for
the other 49 recordings (--blind-report).
"""
import os
for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'ARROW_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import resource
import time

ROOT = Path(__file__).resolve().parents[3]
SCOPE = ROOT / 'docs/quality/audits/um21-t01-tread-release-scope.json'
C03 = ROOT / 'docs/quality/audits/um21-c03-conventions.json'
WITHHELD = ('AB04', 'i0')
LEAVES_UNDER_D_UM21_T02_1_A = {('AB01', 'd10'), ('AB01', 'd5'), ('AB08', 'i10'), ('AB09', 'i10'), ('AB10', 'i0'),
                               ('AB01', 'i5')}
STRIDE_FRAMES = (50, 250)
MIN_FRAMES = 30
MIN_STRIDES = 20
HEADING_DEG = 90.0
AGREE = 0.9
SWITCH = (0.05, 0.95)
SEED = 20261101
CORR_CHANNELS = ('pelvis_obliquity', 'pelvis_rotation', 'hip_flexion', 'hip_adduction', 'hip_rotation', 'foot_progression')
RECIPES = ('thigh_recipe', 'shank_recipe')


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            h.update(chunk)
    return h.hexdigest()


def rss_mib():
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)


def wrap(x):
    import numpy as np
    return (np.asarray(x) + 180.0) % 360.0 - 180.0


def circ_mean(x):
    import numpy as np
    r = np.radians(x)
    return float(np.degrees(np.arctan2(np.mean(np.sin(r)), np.mean(np.cos(r)))))


def circ_median(x):
    import numpy as np
    c = circ_mean(x)
    return float(wrap(np.median(wrap(np.asarray(x) - c)) + c))


def curve(x, a, b):
    import numpy as np
    seg = x[a - 1:b]
    idx = np.rint(np.linspace(0, b - a, 101)).astype(int)
    return [None if not np.isfinite(v) else round(float(v), 2) for v in seg[idx]]


def recording(handle, subject, condition):
    import numpy as np
    trial = handle[f'Streaming/{subject}/Tread/{condition}']

    def angles(name):
        x = trial['jointAngles'][name][...].astype(float)
        zero = (x == 0).all(0)
        alt = np.abs(x[1]) > 90
        x[:, zero | alt] = np.nan
        return x, int(zero.sum()), int((alt & ~zero).sum())

    def marker(name):
        m = trial['markers'][name][...]
        xyz = m[:3].astype(float)
        xyz[:, (m[3] != 1) | ~np.isfinite(xyz).all(0)] = np.nan
        return xyz

    lasi, rasi, lpsi, rpsi = (marker(n) for n in ('LASI', 'RASI', 'LPSI', 'RPSI'))
    asi, psi = (lasi + rasi) / 2, (lpsi + rpsi) / 2
    d = asi - psi
    ant = np.nanmean(d[:2], 1)
    f = np.array([ant[0], ant[1], 0.0]) / np.linalg.norm(ant)
    up = np.array([0.0, 0.0, 1.0])
    right = np.cross(f, up)
    def proj(vec, axis):
        return np.einsum('i,in->n', axis, vec)

    tilt_m = -np.degrees(np.arctan2(proj(d, up), proj(d, f)))
    v = (rasi + rpsi) / 2 - (lasi + lpsi) / 2
    obl_m = np.degrees(np.arctan2(proj(v, up), proj(v, right)))
    yaw_p = np.degrees(np.arctan2(proj(v, f), proj(v, right)))
    heel_z = np.nanmedian(np.concatenate([marker(s + 'HEE')[2] for s in 'LR']))
    pelvis_z = np.nanmedian(asi[2])
    del lasi, rasi, lpsi, rpsi, asi, psi, d, v

    out = {'subject': subject, 'condition': condition,
           'checks': {'up_is_lab_z': bool(pelvis_z > heel_z), 'pelvis_minus_heel_z_m': round(float(pelvis_z - heel_z), 3),
                      'anatomical_forward_xy': [round(float(c), 4) for c in f[:2]]},
           'sides': {}}
    rng_curves = {}
    for s in 'RL':
        sign = 1.0 if s == 'R' else -1.0
        p, p_zero, p_alt = angles(f'{s}PelvisAngles')
        hip, h_zero, h_alt = angles(f'{s}HipAngles')
        knee, _, _ = angles(f'{s}KneeAngles')
        fpa, fp_zero, fp_alt = angles(f'{s}FootProgressAngles')
        gt = marker(s + 'GT')
        knee_c = (marker(s + 'KNE') + marker(s + 'KNEM')) / 2
        ank_c = (marker(s + 'ANK') + marker(s + 'ANKM')) / 2
        t = knee_c - gt
        sh = ank_c - knee_c
        thigh_m = np.degrees(np.arctan2(proj(t, f), -proj(t, up)))
        shank_m = np.degrees(np.arctan2(proj(sh, f), -proj(sh, up)))
        hipflex_m = thigh_m + tilt_m
        hipadd_m = np.degrees(np.arctan2(-sign * proj(t, right), -proj(t, up))) + sign * obl_m
        kaxis = sign * (marker(s + 'KNE') - marker(s + 'KNEM'))
        hiprot_m = sign * (np.degrees(np.arctan2(proj(kaxis, f), proj(kaxis, right))) - yaw_p)
        foot = marker(s + 'TOE') - marker(s + 'HEE')
        fp_m = sign * np.degrees(np.arctan2(proj(foot, right), proj(foot, f)))
        del gt, knee_c, ank_c, t, sh, kaxis, foot

        rot_center = circ_mean(p[2][np.isfinite(p[2])]) if np.isfinite(p[2]).any() else 0.0
        rot_unwrapped = wrap(p[2] - rot_center) + rot_center  # continuous around the recording's heading
        pairs = {'pelvis_obliquity': (p[1], obl_m), 'pelvis_rotation': (rot_unwrapped, yaw_p),
                 'hip_flexion': (hip[0], hipflex_m), 'hip_adduction': (hip[1], hipadd_m), 'hip_rotation': (hip[2], hiprot_m),
                 'foot_progression': (fpa[2], fp_m)}
        recipe_pairs = {'thigh_recipe': (hip[0], thigh_m), 'shank_recipe': (hip[0] - knee[0], shank_m)}

        hs = trial['events'][s + 'HS'][...].reshape(-1).astype(int)
        n = p.shape[1]
        strides = [(int(a), int(b)) for a, b in zip(hs[:-1], hs[1:])
                   if a >= 1 and b <= n and STRIDE_FRAMES[0] <= b - a <= STRIDE_FRAMES[1]]
        tilt_votes, heading_rev, stride_rows = [], [], []
        corr = {c: [] for c in CORR_CHANNELS}
        recipe = {c: [] for c in RECIPES}
        for a, b in strides:
            sl = slice(a - 1, b)
            row = {'frames_1based': [a, b]}
            pv, mv = p[0][sl], tilt_m[sl]
            ok = np.isfinite(pv) & np.isfinite(mv)
            if ok.sum() >= MIN_FRAMES:
                e_pub = float(np.median(np.abs(mv[ok] - pv[ok])))
                e_flip = float(np.median(np.abs(mv[ok] + pv[ok])))
                vote = 1 if e_pub < e_flip else -1
                tilt_votes.append(vote)
                row.update(tilt_vote=vote, tilt_err_pub=round(e_pub, 2), tilt_err_flip=round(e_flip, 2))
            r3 = p[2][sl]
            if np.isfinite(r3).sum() >= MIN_FRAMES:
                hd = circ_mean(r3[np.isfinite(r3)])
                heading_rev.append(abs(hd) > HEADING_DEG)
                row['heading_deg'] = round(hd, 2)
            for c, (src, tgt) in pairs.items():
                x, y = src[sl], tgt[sl]
                ok = np.isfinite(x) & np.isfinite(y)
                if ok.sum() >= MIN_FRAMES and np.std(x[ok]) > 0 and np.std(y[ok]) > 0:
                    corr[c].append(float(np.corrcoef(x[ok], y[ok])[0, 1]))
            for c, (base, tgt) in recipe_pairs.items():
                x, pp, y = base[sl], p[0][sl], tgt[sl]
                ok = np.isfinite(x) & np.isfinite(pp) & np.isfinite(y)
                if ok.sum() >= MIN_FRAMES:
                    e_pub = float(np.median(np.abs(y[ok] - (x[ok] - pp[ok]))))
                    e_flip = float(np.median(np.abs(y[ok] - (x[ok] + pp[ok]))))
                    recipe[c].append((1 if e_pub < e_flip else -1, e_pub, e_flip))
            stride_rows.append(row)
        valid_rot = p[2][np.isfinite(p[2])]
        side = {
            'strides': len(strides), 'pelvis_zero_fill_frames': p_zero, 'pelvis_alternate_branch_frames': p_alt,
            'hip_zero_fill_frames': h_zero, 'hip_alternate_branch_frames': h_alt,
            'foot_progression_zero_fill_frames': fp_zero, 'foot_progression_alternate_branch_frames': fp_alt,
            'pelvis_rotation_circular_median_deg': round(circ_median(valid_rot), 2) if valid_rot.size else None,
            'pelvis_tilt_median_deg': round(float(np.nanmedian(p[0])), 2),
            'pelvis_obliquity_median_deg': round(float(np.nanmedian(p[1])), 2),
            'marker_tilt_median_deg': round(float(np.nanmedian(tilt_m)), 2),
            'tilt_votes': {'strides_voting': len(tilt_votes), 'published_sign': tilt_votes.count(1),
                           'flipped_sign': tilt_votes.count(-1)},
            'tilt_error_median_deg': {
                'published': round(float(np.median([r['tilt_err_pub'] for r in stride_rows if 'tilt_vote' in r])), 3) if tilt_votes else None,
                'flipped': round(float(np.median([r['tilt_err_flip'] for r in stride_rows if 'tilt_vote' in r])), 3) if tilt_votes else None},
            'heading_reversed_strides': int(sum(heading_rev)), 'heading_strides': len(heading_rev),
            'correlation': {c: {'strides': len(v), 'positive': int(sum(x > 0 for x in v)),
                                'median_r': round(float(np.median(v)), 3) if v else None} for c, v in corr.items()},
            'recipes': {c: {'strides': len(v), 'published_pelvis_closer': int(sum(x[0] == 1 for x in v)),
                            'median_err_published': round(float(np.median([x[1] for x in v])), 2) if v else None,
                            'median_err_flipped': round(float(np.median([x[2] for x in v])), 2) if v else None}
                        for c, v in recipe.items()},
            'stored_medians_deg': {'hip_flexion': round(float(np.nanmedian(hip[0])), 2),
                                   'hip_adduction': round(float(np.nanmedian(hip[1])), 2),
                                   'hip_rotation': round(float(np.nanmedian(hip[2])), 2),
                                   'foot_progression': round(float(np.nanmedian(fpa[2])), 2)},
            'marker_medians_deg': {'foot_progression': round(float(np.nanmedian(fp_m)), 2)}}
        out['sides'][s] = side
        # Curves for one stride per side are kept for every recording; the sheet picks by seed.
        voting = [r['frames_1based'] for r in stride_rows if 'tilt_vote' in r]
        rng_curves[s] = {'strides_voting_1based': voting,
                         'series': {'marker_tilt': tilt_m, 'stored_tilt': p[0], 'marker_thigh': thigh_m,
                                    'recipe_thigh': hip[0] - p[0]}}
    out['peak_rss_mib_after'] = rss_mib()
    return out, rng_curves


def classify(rec):
    reasons = []
    sides = rec['sides']
    cls = []
    for s in 'RL':
        x = sides[s]
        h = x['pelvis_rotation_circular_median_deg']
        tv = x['tilt_votes']
        vfrac = tv['published_sign'] / tv['strides_voting'] if tv['strides_voting'] else None
        frac_rev = x['heading_reversed_strides'] / x['heading_strides'] if x['heading_strides'] else None
        if frac_rev is not None and SWITCH[0] < frac_rev < SWITCH[1]:
            reasons.append(f'{s}: heading switches within the recording ({frac_rev:.2f} of strides reversed)')
            cls.append('unresolved')
            continue
        if h is None or vfrac is None or tv['strides_voting'] < MIN_STRIDES:
            reasons.append(f'{s}: too few voting strides or no rotation')
            cls.append('unresolved')
        elif abs(h) < HEADING_DEG and vfrac >= AGREE:
            cls.append('normal')
        elif abs(h) > HEADING_DEG and vfrac <= 1 - AGREE:
            cls.append('reversed')
        else:
            reasons.append(f'{s}: heading {h} with published-sign fraction {vfrac:.3f}')
            cls.append('unresolved')
    if cls[0] == cls[1] and cls[0] != 'unresolved':
        return cls[0], reasons
    return 'unresolved', reasons or ['sides disagree']


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--source', type=Path, default=ROOT / 'contributor_tools/conversion_scripts/Umich_2021/Streaming.mat')
    parser.add_argument('--output', type=Path, required=True, help='new JSON file')
    parser.add_argument('--blind', action='store_true', help='withhold AB04/i0 values')
    parser.add_argument('--blind-report', type=Path, help='blind-run report the final run must reproduce')
    parser.add_argument('--max-rss-mib', type=float, default=300.0)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('output exists; refusing to overwrite')
    want = 768 * 1024**2
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (want if hard == resource.RLIM_INFINITY else min(want, hard), hard))
    os.nice(max(0, 19 - os.nice(0)))
    import numpy as np
    import h5py
    started = time.time()
    scope = json.loads(SCOPE.read_text())
    plan = [(r['subject'], r['condition']) for r in scope['records']]
    strides_in_scope = {(r['subject'], r['condition']): r['observations'] for r in scope['records']}
    stat = args.source.stat()
    rows, curves = [], {}
    with h5py.File(args.source, 'r', rdcc_nbytes=1024**2) as handle:
        for subject, condition in plan:
            rec, cv = recording(handle, subject, condition)
            if rec['peak_rss_mib_after'] > args.max_rss_mib:
                raise SystemExit(f'peak RSS above {args.max_rss_mib} MiB; stopped')
            rec['class'], rec['class_reasons'] = classify(rec)
            rec['record'] = f'{subject}/{condition}'
            rec['release_status'] = ('leaves under D-UM21-T02-1 = A' if (subject, condition) in LEAVES_UNDER_D_UM21_T02_1_A
                                     else 'in the treadmill release scope')
            rec['scope_observations'] = strides_in_scope[(subject, condition)]
            rows.append(rec)
            curves[rec['record']] = cv
    if (args.source.stat().st_size, args.source.stat().st_mtime_ns) != (stat.st_size, stat.st_mtime_ns):
        raise SystemExit('source changed during the probe')

    # Expected correlation signs from 'normal' recordings (AB04/i0 never contributes in a blind run).
    hidden = '/'.join(WITHHELD) if args.blind else None
    visible = [r for r in rows if r['record'] != hidden]
    expected = {}
    for c in CORR_CHANNELS:
        for s in 'RL':
            pos = tot = 0
            for r in visible:
                if r['class'] != 'normal':
                    continue
                x = r['sides'][s]['correlation'][c]
                pos += x['positive']
                tot += x['strides']
            sgn = 1 if pos >= tot - pos else -1
            expected[f'{c}_{s}'] = {'sign': sgn, 'strides': tot,
                                    'reliability': round((pos if sgn == 1 else tot - pos) / tot, 4) if tot else None}
    for c in RECIPES:
        for s in 'RL':
            pub = tot = 0
            for r in visible:
                if r['class'] != 'normal':
                    continue
                x = r['sides'][s]['recipes'][c]
                pub += x['published_pelvis_closer']
                tot += x['strides']
            expected[f'{c}_{s}'] = {'sign': 1, 'strides': tot, 'reliability': round(pub / tot, 4) if tot else None,
                                    'note': 'expected a priori: the recipe uses the stored pelvis tilt'}

    def judge(r):
        out = {}
        for s in 'RL':
            x = r['sides'][s]
            for c in CORR_CHANNELS:
                e = expected[f'{c}_{s}']
                k = x['correlation'][c]
                agree = (k['positive'] if e['sign'] == 1 else k['strides'] - k['positive'])
                frac = agree / k['strides'] if k['strides'] else None
                if e['reliability'] is None or e['reliability'] < AGREE:
                    verdict = 'not judged (marker target unreliable in normal recordings)'
                elif frac is None:
                    verdict = 'unresolved'
                else:
                    verdict = 'flipped' if frac <= 1 - AGREE else 'unchanged' if frac >= AGREE else 'unresolved'
                out[f'{c}_{s}'] = {'agree_strides': agree, 'strides': k['strides'], 'verdict': verdict}
            for c in RECIPES:
                e = expected[f'{c}_{s}']
                k = x['recipes'][c]
                frac = k['published_pelvis_closer'] / k['strides'] if k['strides'] else None
                if e['reliability'] is None or e['reliability'] < AGREE:
                    verdict = 'not judged (marker target unreliable in normal recordings)'
                elif frac is None:
                    verdict = 'unresolved'
                else:
                    verdict = 'wrong pelvis sign' if frac <= 1 - AGREE else 'right pelvis sign' if frac >= AGREE else 'unresolved'
                out[f'{c}_{s}'] = {'published_pelvis_closer': k['published_pelvis_closer'], 'strides': k['strides'], 'verdict': verdict}
        return out

    for r in rows:
        r['channel_judgement'] = judge(r)

    # Seeded stride picks for the sheet: every reversed recording, and one normal contrast recording
    # drawn from normal recordings that stay in the release scope.
    rng = random.Random(SEED)
    normal_in_scope = sorted(r['record'] for r in visible if r['class'] == 'normal'
                             and r['release_status'] == 'in the treadmill release scope')
    contrast = rng.choice(normal_in_scope) if normal_in_scope else None
    picks = {}
    for rec in sorted([r['record'] for r in visible if r['class'] != 'normal']) + ([contrast] if contrast else []):
        if args.blind and rec == '/'.join(WITHHELD):
            continue
        picks[rec] = {}
        for s in 'RL':
            cv = curves[rec][s]
            if not cv['strides_voting_1based']:
                continue
            a, b = rng.choice(cv['strides_voting_1based'])
            picks[rec][s] = {'frames_1based': [a, b], **{k: curve(v, a, b) for k, v in cv['series'].items()}}
    del curves

    summary = {
        'classes': {k: sorted(r['record'] for r in visible if r['class'] == k) for k in ('normal', 'reversed', 'unresolved')},
        'rotation_median_range_normal_deg': [min(min(r['sides'][s]['pelvis_rotation_circular_median_deg'] for s in 'RL')
                                                 for r in visible if r['class'] == 'normal'),
                                             max(max(r['sides'][s]['pelvis_rotation_circular_median_deg'] for s in 'RL')
                                                 for r in visible if r['class'] == 'normal')],
        'tilt_votes_normal_published_of_voting': [sum(r['sides'][s]['tilt_votes']['published_sign'] for r in visible
                                                      if r['class'] == 'normal' for s in 'RL'),
                                                  sum(r['sides'][s]['tilt_votes']['strides_voting'] for r in visible
                                                      if r['class'] == 'normal' for s in 'RL')]}
    if args.blind:
        for r in rows:
            if (r['subject'], r['condition']) == WITHHELD:
                for key in list(r):
                    if key not in ('record', 'subject', 'condition', 'release_status'):
                        r[key] = 'withheld (blind run)'

    blind_check = None
    if args.blind_report:
        blind = json.loads(args.blind_report.read_text())
        if blind['probe']['sha256'] != sha256_file(Path(__file__)):
            raise SystemExit('blind run used different probe code')
        b_rows = {r['record']: r for r in blind['records']}
        strip = lambda r: {k: v for k, v in r.items() if k != 'peak_rss_mib_after'}
        same = all(strip(r) == strip(b_rows[r['record']]) for r in rows if r['record'] != '/'.join(WITHHELD))
        blind_check = {'path_name': args.blind_report.name, 'sha256': sha256_file(args.blind_report),
                       'generated_utc': blind['generated_utc'], 'probe_sha256': blind['probe']['sha256'],
                       'other_49_records_identical': same, 'expected_signs_identical': blind['expected_signs'] == expected,
                       'contrast_identical': blind['seeded_picks']['contrast'] == contrast}
        if not (same and blind_check['expected_signs_identical']):
            raise SystemExit('final run differs from the blind run outside AB04/i0')

    report = {
        'task_id': 'UM21-P01', 'status': 'probe_complete_unreviewed', 'scientific_approval': False,
        'corrections_applied': False, 'blind_run': bool(args.blind),
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'probe': {'path': str(Path(__file__).resolve().relative_to(ROOT)), 'sha256': sha256_file(Path(__file__))},
        'inputs': {'scope': {'path': str(SCOPE.relative_to(ROOT)), 'sha256': sha256_file(SCOPE)},
                   'c03_conventions': {'path': str(C03.relative_to(ROOT)), 'sha256': sha256_file(C03)},
                   'source': {'path': str(args.source.resolve().relative_to(ROOT)), 'bytes': stat.st_size,
                              'mtime_ns': stat.st_mtime_ns,
                              'sha256_recorded': scope['source']['streaming_sha256_recorded'],
                              'sha256_note': 'Recorded by earlier receipts; size and mtime re-checked before and after, bytes not rehashed.'}},
        'rule': {'heading_deg': HEADING_DEG, 'agreement': AGREE, 'min_strides': MIN_STRIDES, 'min_frames_per_stride': MIN_FRAMES,
                 'switch_fraction': list(SWITCH), 'stride_frames': list(STRIDE_FRAMES),
                 'text': 'normal: both sides |H| < 90, V >= 0.9, >= 20 voting strides; reversed: both sides |H| > 90, V <= 0.1, '
                         '>= 20 voting strides; else unresolved (also any within-recording heading switch). '
                         'H = circular median stored pelvis rotation; V = fraction of strides whose marker tilt vote is the published sign.'},
        'expected_signs': expected,
        'seeded_picks': {'seed': SEED, 'contrast': contrast, 'contrast_pool': normal_in_scope, 'curves': picks,
                         'rule': 'random.Random(seed): contrast = choice(sorted normal in-scope records); then one stride per side '
                                 'for each non-normal record (sorted) and the contrast, in that order.'},
        'summary': summary,
        'records': rows, 'blind_check': blind_check,
        'resources': {'peak_rss_mib': rss_mib(), 'wall_seconds': round(time.time() - started, 1),
                      'rlimit_as_bytes': list(resource.getrlimit(resource.RLIMIT_AS)), 'nice': os.nice(0)}}
    nan_paths = []

    def clean(x, path=''):  # non-finite numbers become null and are listed, never silently dropped
        if isinstance(x, float) and not math.isfinite(x):
            nan_paths.append(path)
            return None
        if isinstance(x, dict):
            return {k: clean(v, f'{path}/{k}') for k, v in x.items()}
        if isinstance(x, list):
            return [clean(v, f'{path}/{i}') for i, v in enumerate(x)]
        return x
    report = clean(report)
    report['non_finite_values_nulled'] = [p for p in nan_paths if '/curves/' not in p][:200]
    report['non_finite_curve_samples_nulled'] = sum('/curves/' in p for p in nan_paths)
    text = json.dumps(report, indent=1, allow_nan=False) + '\n'
    with open(args.output, 'x') as stream:
        stream.write(text)
    print(json.dumps({'summary': summary, 'expected': expected, 'contrast': contrast,
                      'peak_rss_mib': report['resources']['peak_rss_mib'], 'wall_s': report['resources']['wall_seconds']}, indent=1))


if __name__ == '__main__':
    main()
