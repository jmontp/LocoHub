"""GT24-C01: which mass divided each GT24 trial's per-kg moments, and how heavy is the person in each folder?

Written by GT24-C01 as a bounded pilot. NOT RUN by GT24-C01 (another agent held the numerical
slot). The selection is fixed from metadata only (``plan``); the data step (``pilot``) must be
launched as one job through contributor_tools.guarded_launcher under the AGENTS.md prefix.

Usage:
  plan                       print the seeded selection (reads only the GT24 mass matrix JSON)
  pilot [--out PATH]         read the selected Parsed CSV members, one at a time, from the publisher
                             zips (no extraction) and write the result JSON
                             (default docs/quality/audits/gt24-c01-divisor-probe.json)

Three independent estimators (rules fixed in RULES before any data are read):
  E1 exact identity (no physics, no model): README line 520 defines moment_filt_bio as moment_filt
     minus the exo interaction torque, so for hip_flexion and knee_angle
        exo <joint>_angle_<side>_torque_interaction = s * D * (moment_filt - moment_filt_bio)
     sample by sample, where D is the divisor used for the interaction torque and s aligns the exo
     sign convention. A constant ratio (robust relative spread <= 1e-3, |corr| >= 0.9999) gives D
     exactly and shows the interaction column is in N*m. README line 556 gives a second identity:
        torque_interaction * velocity(rad/s) = s * D * power_exo.
  E2 force-plate weight (mass-free): mean of the two plates' vertical force over whole strides of
     constant-speed level treadmill walking / g = the worn mass (person + exoskeleton). GT23-C02 used
     the same estimator and matched README body masses within 1 % in 12/12 subjects.
  E3 lever arm (C02 method): source ankle moment against the quasi-static force-plate
     ankle moment in N*m about the generic talus point; 1 / slope = implied divisor / lever bias,
     with the bias fixed from GT23-C04 (0.9942; assumed to transfer to GT24). Checks that the net
     moments share the E1 divisor (it separates divisors 8 % apart or more; it cannot separate days).
Caveat: E1 identifies the divisor used for the interaction torque (bio = net - interaction / D_x).
It is the net-moment divisor only if the authors used the same mass for both; E3 tests that, under
the same bias-transfer assumption.
Candidate masses come from the README table (all rows, so cross-subject matches are visible) and,
for Phase3, the Statics.csv model masses at full precision. Parsed-to-native trial mapping uses the
Statics trial name as a prefix; E1 then tests that mapping (an exact match to a 15-digit Statics mass
cannot be chance).

Nothing is converted; nothing under converted_datasets/ or the source folder is written.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
import resource
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

MATRIX = ROOT / 'converted_datasets/reconversion_v2/gt24_source_mass_coverage_v4_20261021/matrix.json'
MATRIX_SHA256 = '688dec9d45ecf103c43a57740c0fbc019ab3e67b47fd37834a726bdd6062b462'
README_SHA256 = 'e896c6b424c45f50f261ade2e40c5f5832065fbcd745c593b7cd72fdeb84026f'
OUT = ROOT / 'docs/quality/audits/gt24-c01-divisor-probe.json'
SEED = 20261031
G = 9.81
RATE_HZ = 200.0

RULES = {
    'fixed_at': 'GT24-C01, before any GT24 data read by this probe',
    'identity_top_quantile': 0.75,          # use samples with |net - bio| (or |power_exo|) at or above this quantile
    'identity_min_samples': 200,
    'identity_exact_max_rel_spread': 1e-3,  # 1.4826 MAD / median of the per-sample ratio
    'identity_exact_min_abs_corr': 0.9999,
    'identity_filtered_min_abs_corr': 0.99, # least-squares divisor reported, class 'proportional_not_exact'
    'mass_match_max_abs_log': 5e-4,         # 0.05 %: README prints 0.01 kg; day-1/day-2 worn masses differ by >= 0.25 %
    'plate_threshold_N': 50.0,              # right-plate heel strike = upward crossing
    'plate_min_strides': 10,
    'plate_unique_margin_log': 0.02,        # nearest candidate must beat the next distinct value by 2 %
    'lever_window': [0.40, 0.90],
    'lever_stance_threshold_N': 50.0,
    'lever_band_half_width_log': 0.0488,    # GT23-C03 tolerance_v2 / GT23-C04 rules (about +/-4.9 %)
    'lever_bias_external': 0.9942,          # GT23-C04 rules.ankle_bias_centre_ratio; assumed to transfer to GT24, not re-fitted
    'level_walk_preference': ['1-2', '1-8', '0-6'],
    'repeat_day_phase12_extra_trials': 6,
}
JOINTS = (('hip_flexion', 'hip'), ('knee_angle', 'knee'))
LEVEL = re.compile(r'^normal_walk_[\d_]+_(0-6|1-2|1-8)_(on|off)$')
REPEAT_DAY_PHASE12 = ('BT06', 'BT07', 'BT13')


def digest_file(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def load_matrix():
    if digest_file(MATRIX) != MATRIX_SHA256:
        raise ValueError('GT24 mass matrix changed; re-plan')
    return json.loads(MATRIX.read_text())


def statics_trial(statics, recording):
    """Statics trial whose name followed by '_' prefixes the Parsed recording; must be unique."""
    hits = [k for k in statics if recording.startswith(k + '_')]
    if len(hits) != 1:
        return None
    return hits[0]


def candidates(meta, phase, subject):
    """All README masses (every row, both phases) plus this folder's Statics masses, labelled."""
    out = []
    for ph, rows in meta['readme']['phase_masses'].items():
        for subj, row in rows.items():
            for field in ('participant_day1_kg', 'model_day1_with_exo_kg', 'participant_day2_kg', 'model_day2_with_exo_kg'):
                if field in row:
                    out.append({'source': 'README', 'phase': ph, 'subject': subj, 'field': field,
                                'own_row': ph == phase and subj == subject, 'kg': float(row[field])})
    if phase == 'Phase3' and subject in meta['phase3_static_models']:
        seen = {}
        for trial, row in meta['phase3_static_models'][subject]['records'].items():
            seen.setdefault(row['source_model_mass_kg_decimal'], []).append(row['source_model_id'])
        for value, ids in sorted(seen.items()):
            out.append({'source': 'Statics', 'phase': phase, 'subject': subject, 'field': 'model ids ' + ','.join(sorted(set(ids), key=int)),
                        'own_row': True, 'kg': float(value)})
    return out


def match(value, cands, tol):
    if value is None or not math.isfinite(value) or value <= 0:
        return []
    hits = [dict(c, abs_log=round(abs(math.log(value / c['kg'])), 6)) for c in cands if abs(math.log(value / c['kg'])) <= tol]
    return sorted(hits, key=lambda c: c['abs_log'])


def plan():
    m = load_matrix()
    meta = m['source_metadata']
    if meta['readme']['sha256'] != README_SHA256:
        raise ValueError('README binding changed')
    rng = np.random.default_rng(SEED)
    units = {}
    for r in m['parsed_recordings']:
        units.setdefault((r['phase'], r['subject']), []).append(r)
    selection = []
    for (phase, subject) in sorted(units):
        recs = sorted(units[(phase, subject)], key=lambda r: r['recording'])
        chosen = set()
        statics = meta['phase3_static_models'].get(subject, {}).get('records', {}) if phase == 'Phase3' else {}
        # Stage A: one level-walk trial per exo state present, preferring 1.2 m/s.
        for state in sorted({r['exo_state'] for r in recs}):
            for speed in RULES['level_walk_preference']:
                pool = [r['recording'] for r in recs if r['exo_state'] == state and LEVEL.match(r['recording'])
                        and LEVEL.match(r['recording']).group(1) == speed]
                if pool:
                    pick = pool[int(rng.integers(len(pool)))]
                    chosen.add(pick)
                    selection.append({'phase': phase, 'subject': subject, 'recording': pick, 'stage': 'A_level_walk',
                                      'exo_state': state, 'estimators': ['E1', 'E2', 'E3']})
                    break
        # Stage B (Phase3): one trial for every Statics mass value not already covered.
        if statics:
            covered = {statics[statics_trial(statics, c)]['source_model_mass_kg_decimal'] for c in chosen if statics_trial(statics, c)}
            groups = {}
            for r in recs:
                key = statics_trial(statics, r['recording'])
                if key is not None:
                    groups.setdefault(statics[key]['source_model_mass_kg_decimal'], []).append(r['recording'])
            for value in sorted(groups):
                if value in covered:
                    continue
                pool = sorted(groups[value])
                pick = pool[int(rng.integers(len(pool)))]
                chosen.add(pick)
                selection.append({'phase': phase, 'subject': subject, 'recording': pick, 'stage': 'B_statics_mass_group',
                                  'statics_mass_kg': value, 'estimators': ['E1']})
        # Stage C (Phase1And2 repeat-day subjects): extra random trials, any task, to see both day divisors.
        if phase == 'Phase1And2' and subject in REPEAT_DAY_PHASE12:
            pool = [r['recording'] for r in recs if r['recording'] not in chosen]
            for i in rng.permutation(len(pool))[:RULES['repeat_day_phase12_extra_trials']]:
                selection.append({'phase': phase, 'subject': subject, 'recording': pool[int(i)], 'stage': 'C_repeat_day',
                                  'estimators': ['E1']})
    for s in selection:
        if s['phase'] == 'Phase3':
            st = meta['phase3_static_models'].get(s['subject'], {}).get('records', {})
            key = statics_trial(st, s['recording'])
            s['statics_trial'] = key
            s['statics_mass_kg'] = st[key]['source_model_mass_kg_decimal'] if key else None
    return {'seed': SEED, 'matrix_sha256': MATRIX_SHA256, 'rules': RULES, 'units': len(units), 'trials': len(selection),
            'by_stage': {k: sum(s['stage'] == k for s in selection) for k in ('A_level_walk', 'B_statics_mass_group', 'C_repeat_day')},
            'selection': selection}


# ---------------------------------------------------------------- estimators (pure; tested on synthetic data)

def _top(mask_values, q):
    a = np.abs(mask_values)
    fin = np.isfinite(a)
    if fin.sum() == 0:
        return fin
    return fin & (a >= np.quantile(a[fin], q)) & (a > 1e-9)


def ratio_estimate(numer, denom, q=None):
    """Per-sample ratio numer/denom on the largest |denom| samples; returns divisor, sign, spread, corr."""
    q = RULES['identity_top_quantile'] if q is None else q
    numer, denom = np.asarray(numer, float), np.asarray(denom, float)
    both = np.isfinite(numer) & np.isfinite(denom)
    sel = both & _top(np.where(both, denom, np.nan), q)
    n = int(sel.sum())
    out = {'n_used': n, 'n_finite': int(both.sum())}
    if n < RULES['identity_min_samples']:
        out['class'] = 'too_few_samples'
        return out
    r = numer[sel] / denom[sel]
    med = float(np.median(r))
    spread = float(1.4826 * np.median(np.abs(r - med)) / abs(med)) if med else math.inf
    corr = float(np.corrcoef(numer[both], denom[both])[0, 1]) if np.std(denom[both]) > 0 and np.std(numer[both]) > 0 else math.nan
    ls = float(numer[both] @ denom[both] / (denom[both] @ denom[both]))
    out.update(ratio_median=med, divisor_kg=abs(med), sign=int(np.sign(med)), rel_spread=spread, corr=corr, ls_ratio=ls)
    if spread <= RULES['identity_exact_max_rel_spread'] and abs(corr) >= RULES['identity_exact_min_abs_corr']:
        out['class'] = 'exact'
    elif abs(corr) >= RULES['identity_filtered_min_abs_corr']:
        out['class'] = 'proportional_not_exact'
        out['divisor_kg'] = abs(ls)
        out['sign'] = int(np.sign(ls))
    else:
        out['class'] = 'no_identity'
    return out


def plate_mass(fy_l, fy_r):
    """Worn mass from mean total vertical plate force between the first and last right heel strike."""
    fy_l, fy_r = np.asarray(fy_l, float), np.asarray(fy_r, float)
    tot = fy_l + fy_r
    on = np.nan_to_num(fy_r) > RULES['plate_threshold_N']
    hs = np.flatnonzero(~on[:-1] & on[1:]) + 1
    out = {'strides': int(max(len(hs) - 1, 0))}
    if len(hs) - 1 < RULES['plate_min_strides']:
        out['class'] = 'too_few_strides'
        return out
    seg = tot[hs[0]:hs[-1]]
    if not np.isfinite(seg).all():
        out['class'] = 'nonfinite_force'
        return out
    per = [float(np.mean(tot[a:b]) / G) for a, b in zip(hs[:-1], hs[1:])]
    out.update({'class': 'estimated', 'mass_kg': float(np.mean(seg) / G),
                'per_stride_rel_sd': float(np.std(per) / np.mean(per)), 'samples': int(len(seg))})
    return out


def plate_verdict(mass, cands):
    if mass is None:
        return None
    values = sorted({round(c['kg'], 2) for c in cands})
    logs = sorted((abs(math.log(mass / v)), v) for v in values)
    best, nxt = logs[0], next((x for x in logs[1:] if abs(x[1] - logs[0][1]) > 0.011), None)
    unique = nxt is not None and nxt[0] - best[0] >= RULES['plate_unique_margin_log']
    return {'nearest_kg': best[1], 'nearest_abs_log': round(best[0], 4), 'next_kg': nxt[1] if nxt else None,
            'unique': bool(unique), 'nearest_labels': [f"{c['source']} {c['phase']} {c['subject']} {c['field']}" for c in cands if round(c['kg'], 2) == best[1]]}


def lever_divisor(fx, fy, copx, src, offset=(0.04877, 0.04195)):
    """Implied divisor = 1 / slope(source Nm/kg on quasi-static internal dorsiflexion moment in N*m)."""
    fx, fy, copx, src = (np.asarray(a, float) for a in (fx, fy, copx, src))
    on = np.nan_to_num(fy) > RULES['lever_stance_threshold_N']
    edges = np.flatnonzero(np.diff(on.astype(int)))
    idx = []
    stances = 0
    for a, b in zip(edges[:-1], edges[1:]):
        if on[a + 1] and 0.25 * RATE_HZ <= b - a <= 2.5 * RATE_HZ and a > 0 and b < len(fy) - 2:
            s0, s1 = a + 1, b + 1
            if np.isfinite(src[s0:s1]).all():
                lo, hi = RULES['lever_window']
                idx.append(np.arange(s0 + int(round(lo * (s1 - s0))), s0 + int(round(hi * (s1 - s0)))))
                stances += 1
    if stances < 4:
        return {'stances': stances, 'class': 'too_few_stances'}
    i = np.concatenate(idx)
    pred = -((copx[i] - offset[0]) * fy[i] + offset[1] * fx[i])
    k = float(src[i] @ pred / (pred @ pred))
    return {'stances': stances, 'class': 'estimated', 'implied_divisor_kg_uncorrected': 1.0 / k if k > 0 else None,
            'corr': float(np.corrcoef(src[i], pred)[0, 1])}


# ---------------------------------------------------------------- data step

def run_trial(rd, meta, item):
    phase, subject, rec = item['phase'], item['subject'], item['recording']
    base = f'Parsed/{subject}/{rec}/{subject}_{rec}_'
    cands = candidates(meta, phase, subject)
    tol = RULES['mass_match_max_abs_log']
    out = dict(item, identity={}, power_identity={})
    exo = rd.table(phase, base + 'exo.csv')
    net = rd.table(phase, base + 'moment_filt.csv')
    bio = rd.table(phase, base + 'moment_filt_bio.csv')
    pex = rd.table(phase, base + 'power_exo.csv')
    vel = rd.table(phase, base + 'velocity.csv')
    for side in ('l', 'r'):
        for coord, exo_joint in JOINTS:
            key = f'{coord}_{side}'
            col_x = f'{exo_joint}_angle_{side}_torque_interaction'
            col_m = f'{coord}_{side}_moment'
            if col_x not in exo or col_m not in net or col_m not in bio:
                out['identity'][key] = {'class': 'column_absent'}
                continue
            x = exo[col_x].to_numpy(float)
            res = ratio_estimate(x, net[col_m].to_numpy(float) - bio[col_m].to_numpy(float))
            res['matches'] = match(res.get('divisor_kg'), cands, tol) if res.get('class') == 'exact' else []
            out['identity'][key] = res
            col_p, col_v = f'{coord}_{side}_power', f'{coord}_{side}_velocity'
            if col_p in pex and col_v in vel:
                pr = ratio_estimate(x * np.deg2rad(vel[col_v].to_numpy(float)), pex[col_p].to_numpy(float))
                pr['matches'] = match(pr.get('divisor_kg'), cands, tol) if pr.get('class') == 'exact' else []
                out['power_identity'][key] = pr
            else:
                out['power_identity'][key] = {'class': 'column_absent'}
    del exo, pex, vel
    exact = [v['divisor_kg'] for v in out['identity'].values() if v.get('class') == 'exact']
    out['identity_divisor_kg'] = float(np.median(exact)) if exact else None
    out['identity_divisor_spread_rel'] = float((max(exact) - min(exact)) / np.median(exact)) if exact else None
    out['identity_matches'] = match(out['identity_divisor_kg'], cands, tol)
    if 'E2' in item['estimators']:
        grf = rd.table(phase, base + 'grf.csv', usecols=['fp_l_force_y', 'fp_r_force_y'])
        pm = plate_mass(grf['fp_l_force_y'], grf['fp_r_force_y'])
        pm['verdict'] = plate_verdict(pm.get('mass_kg'), cands)
        out['plate'] = pm
        del grf
    if 'E3' in item['estimators']:
        ins = rd.table(phase, base + 'insole_sim.csv')
        out['lever'] = {}
        for side in ('l', 'r'):
            lv = lever_divisor(ins[f'insole_{side}_force_x'], ins[f'insole_{side}_force_y'], ins[f'insole_{side}_cop_x'],
                               net[f'ankle_angle_{side}_moment'])
            if lv.get('implied_divisor_kg_uncorrected') and out['identity_divisor_kg']:
                lv['log_ratio_to_identity'] = math.log(lv['implied_divisor_kg_uncorrected'] / out['identity_divisor_kg'])
            out['lever'][side] = lv
        del ins
    return out


def summarize(results):
    """Net moments share the E1 divisor when the lever ratio is inside the band around the EXTERNAL GT23 bias.

    implied = D_net / b, so log(implied / D_x) = log(D_net / D_x) - log(b). The bias b is fixed from GT23-C04
    (assumed to transfer to GT24); the pilot median is reported only, never used to classify (that would be circular).
    E1 measures the interaction-torque divisor D_x; D_net = D_x only if the authors used one mass for both.
    """
    logs = [lv['log_ratio_to_identity'] for t in results for lv in t.get('lever', {}).values() if 'log_ratio_to_identity' in lv]
    centre = -math.log(RULES['lever_bias_external'])
    for t in results:
        for lv in t.get('lever', {}).values():
            if 'log_ratio_to_identity' in lv:
                lv['shares_identity_divisor_if_bias_transfers'] = abs(lv['log_ratio_to_identity'] - centre) <= RULES['lever_band_half_width_log']
    bias = float(np.median(logs)) if logs else None
    units = {}
    for t in results:
        u = units.setdefault(f"{t['phase']}/{t['subject']}", {'identity_divisors_kg': [], 'plate_kg': [], 'matches': []})
        if t['identity_divisor_kg']:
            u['identity_divisors_kg'].append(round(t['identity_divisor_kg'], 6))
            u['matches'].append([f"{c['source']} {c['phase']} {c['subject']} {c['field']}" for c in t['identity_matches']])
        if t.get('plate', {}).get('mass_kg'):
            u['plate_kg'].append(round(t['plate']['mass_kg'], 2))
    return {'lever_pilot_median_log_reported_only': bias, 'lever_external_centre_log': centre, 'units': units,
            'trials_identity_exact': sum(t['identity_divisor_kg'] is not None for t in results), 'trials': len(results)}


def pilot(out_path):
    import zipfile
    from contributor_tools.review_gt24_c02_ankle_sign import Reader, ZIPS, peak_rss_mib, mem_available
    resource.setrlimit(resource.RLIMIT_AS, (int(1.5 * 2 ** 30), int(1.5 * 2 ** 30)))
    p = plan()
    meta = load_matrix()['source_metadata']
    before = {k: (v.stat().st_size, v.stat().st_mtime_ns) for k, v in ZIPS.items()}
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    t0 = time.time()
    rd = Reader()
    results = []
    for item in p['selection']:
        if mem_available() < 2 ** 30:
            raise MemoryError('Less than 1 GiB available; stopping without partial success')
        results.append(run_trial(rd, meta, item))
    for z in rd.zips.values():
        z.close()
    after = {k: (v.stat().st_size, v.stat().st_mtime_ns) for k, v in ZIPS.items()}
    if before != after:
        raise RuntimeError('Source zip changed during the read')
    doc = {'task_id': 'GT24-C01', 'stage': 'pilot', 'scientific_approval': False, 'probe_sha256': digest_file(__file__),
           'plan': p, 'started_at_utc': started, 'runtime_seconds': round(time.time() - t0, 1), 'peak_rss_mib': peak_rss_mib(),
           'zips_unchanged': True, 'members_read': rd.members, 'results': results, 'summary': summarize(results)}
    Path(out_path).write_text(json.dumps(doc, indent=1, default=float) + '\n')
    print(json.dumps(doc['summary'], indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('step', choices=['plan', 'pilot'])
    ap.add_argument('--out', default=str(OUT))
    a = ap.parse_args()
    if a.step == 'plan':
        print(json.dumps(plan(), indent=1))
    else:
        pilot(a.out)


if __name__ == '__main__':
    main()
