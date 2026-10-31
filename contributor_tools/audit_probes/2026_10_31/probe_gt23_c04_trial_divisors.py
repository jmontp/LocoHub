"""GT23-C04: per-trial census of the mass each GT23 trial's moments were divided by, and the rescale table.

José answered D-GT23-C03-1 = B (rescale each trial to its participant's own mass). This probe only
builds the per-trial rescale table; no data are rescaled or written anywhere except the audit JSON.

Read-only probe (AGENTS.md exception): one trial (recording) in memory at a time, nothing written under
converted_datasets/ or the source folder, single-threaded, nice 19 / ionice idle (set by the caller),
peak RSS recorded and required below 300 MiB.

Usage:
  pilot   --subjects AB05,AB12 --out <scratch json>    bounded pilot (same code as the census)
  census  [--out docs/quality/audits/gt23-c04-trial-divisors.json]   every subject, every trial

Methods (reused unchanged from GT23-C03, imported from its probe, not re-implemented):
  * exact divisor: RawData/<subj>/MotionFile_EH/inverse_dynamics.sto (local N*m re-run, provenance unknown)
    equals the matching published trial times a constant (every ankle/knee column corr >= 0.9999).
  * force-plate lever-arm estimate (mass-free): calcn-frame insole GRF/CoP, joint centres from the
    trial's own scaled model (Statics.csv), quasi-static ankle moment in 40-90 % of gait stances;
    implied mass = 1 / slope(published on estimate); divisor = implied / ankle bias.
Tolerances are read from the GT23-C03 audit (tolerance_v2; sha256 recorded) and fixed in RULES below
before any trial data are read. Nothing is tuned in this task.

Added here (not used for classification): a loaded-sample variant of the same estimator for trials with
no gait stances (all samples with insole vertical force > 100 N), and a power check
(published power vs published moment x published joint velocity) to test whether powers share the moment divisor.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import sys
import time

import numpy as np

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
_spec = importlib.util.spec_from_file_location('c03', HERE.parent / 'probe_gt23_c03_normalizing_mass.py')
c03 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c03)

RAW = c03.RAW
C03_AUDIT = ROOT / 'docs/quality/audits/gt23-c03-normalizing-mass.json'
AUDIT = ROOT / 'docs/quality/audits/gt23-c04-trial-divisors.json'
RSS_LIMIT_MIB = 300
LOCOMOTION = set(c03.FAMILIES)                       # the 14 families the C03 lever method was run on
UNRELIABLE_FAMILIES = {'curb_up', 'curb_down'}       # C03: ankle corr < 0.98 in 6 of 9 curb trials
POWER_COLS = {'ankle': ('ankle_power_{s}', 'ankle_angle_{s}_moment', 'ankle_velocity_{s}'),
              'knee': ('knee_power_{s}', 'knee_angle_{s}_moment', 'knee_velocity_{s}')}


def rules(c03_audit):
    t2 = c03_audit['tolerance_v2']
    return {
        'source': 'GT23-C03 audit tolerance_v2 (fixed there; not recomputed here)',
        'exact_rerun_min_corr': c03.EXACT_CORR,
        'exact_table_match_max_abs_log': 0.001,
        'ankle_bias_centre_ratio': t2['ankle_bias']['centre_ratio'],
        'candidate_band_half_width_log': t2['ankle_bias']['half_width_log'],
        'candidate_band_note': 'about +/-5 %; calibrated on 5 level-walk trials, out of sample worst 4.9 % (3 of 3), so the margin is thin',
        'min_gait_stances': c03.MIN_STANCES,
        'reliable_min_ankle_corr': 0.98,
        'reliable_families': sorted(LOCOMOTION - UNRELIABLE_FAMILIES),
        'unreliable_families': sorted(UNRELIABLE_FAMILIES),
        'same_value_max_spread_log': float(np.log(1.005)),
        'knee': 'recorded only (knee-ankle disagreement spans -0.31 to +0.15 log in C03 reliable trials, so it is not a gate)',
        'power_check': 'ratio of published power to published moment x published joint velocity (deg/s -> rad/s): median of P / (M w) over finite '
                       'samples with |M w| at or above its 75th percentile (slope and corr also recorded). Shares the moment divisor when '
                       '|log median ratio| <= the candidate band half width in every tested ANKLE column (a different divisor would scale every '
                       'column of the trial equally; knee ratios are recorded only, because pilot 2 showed published knee power below M w by '
                       '3-17 % in trials whose ankle ratio is 1.00, cause not identified); this detects a different table mass more than '
                       'about 5 % away (e.g. own vs another subject), not small differences. Revised after pilot 1 (2 subjects): the first rule '
                       '(|log slope| <= 0.02 and corr >= 0.98) failed on filtering differences between the published velocity and power '
                       '(knee slopes 0.84-0.99, corr 0.93-0.99). Not a gate for the moment class.',
        'classes': {
            'exact': 'the trial matched by a local N*m re-run whose ankle/knee columns all correlate >= 0.9999 with the published moments; '
                     'divisor = the README table mass within 0.1 % of the re-run slope',
            'unique-estimate': 'reliable lever estimate; every README mass inside the band lies within 0.5 % of the others (one mass value); '
                               'divisor = the nearest such table mass',
            'ambiguous': 'reliable lever estimate; table masses more than 0.5 % apart lie inside the band',
            'no-match': 'reliable lever estimate; no README table mass inside the band',
            'unreliable': 'family outside the reliable locomotion families (non-gait task or curb), fewer than 4 gait stances, '
                          'ankle corr < 0.98, unequal time bases, or no model in Statics.csv',
        },
        'rescale': 'rescale_factor = divisor / own README mass, only for exact and unique-estimate; '
                   'per-kg own-mass value = published x rescale_factor (moments and, if the power check passes, powers)',
    }


class CachedReader(c03.Reader):
    """Same hashing/CRC reader as C03, with a per-trial cache so each file is read once."""

    def __init__(self, zipdir):
        super().__init__(zipdir)
        self.cache = {}

    def table(self, path, **kw):
        key = str(path)
        if key not in self.cache:
            self.cache[key] = super().table(path, **kw)
        return self.cache[key]

    def clear(self):
        self.cache.clear()


def utc():
    return dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def loaded_estimate(reader, inv, subj, task, bias):
    """Loaded-sample variant (all samples with insole vertical force > 100 N), ankle only. Informational."""
    d = RAW / subj / 'CSV_Data' / task
    mname, _ = c03.model_for(inv, subj, task)
    if mname is None:
        return None
    model = inv[subj]['models'][mname]
    mom, ins, ang = (reader.table(d / p) for p in ('Joint_Moments.csv', 'Virtual_Insoles.csv', 'Joint_Angle.csv'))
    if not (len(mom) == len(ins) == len(ang)):
        return None
    src_all, est_all = [], []
    for s in 'rl':
        S = s.upper()
        fv, fap, cop = (ins[f'{S}{k}'].to_numpy(float) for k in ('VerticalF', 'ShearF_AP', 'COP_AP'))
        qa, qs = ang[f'ankle_angle_{s}'].to_numpy(float), ang[f'subtalar_angle_{s}'].to_numpy(float)
        src = mom[f'ankle_angle_{s}_moment'].to_numpy(float)
        i = np.flatnonzero(np.isfinite(fv) & np.isfinite(fap) & np.isfinite(cop) & np.isfinite(qa) & np.isfinite(qs)
                           & np.isfinite(src) & (np.nan_to_num(fv) > c03.STANCE_N))
        if i.size < 200:
            continue
        p, n = c03.joint_frames(model[s], qa[i], qs[i])['ankle']
        src_all.append(src[i]); est_all.append(c03.estimate(p, n, cop[i], fv[i], fap[i], c03.COP_Y))
    if not src_all:
        return None
    src, est = np.concatenate(src_all), np.concatenate(est_all)
    sl, r = c03.fit(src, est)
    return {'samples': int(src.size), 'corr': round(r, 4),
            'divisor_kg_walking_bias': round(1 / sl / bias, 2) if sl > 0 else None}


def power_check(reader, subj, task, band):
    d = RAW / subj / 'CSV_Data' / task
    if not (d / 'Joint_Powers.csv').exists() or not (d / 'Joint_Velocities.csv').exists():
        return {'present': False}
    mom, vel = reader.table(d / 'Joint_Moments.csv'), reader.table(d / 'Joint_Velocities.csv')
    pw = reader.table(d / 'Joint_Powers.csv')
    if not (len(pw) == len(mom) == len(vel)) or float(np.max(np.abs(pw.time.to_numpy() - vel.time.to_numpy()))) > 1e-6:
        return {'present': True, 'aligned': False}
    out = {'present': True, 'aligned': True, 'columns': {}}
    for j, (pc, mc, ac) in POWER_COLS.items():
        for s in 'rl':
            P, M = pw[pc.format(s=s)].to_numpy(float), mom[mc.format(s=s)].to_numpy(float)
            w = np.deg2rad(vel[ac.format(s=s)].to_numpy(float))
            f = np.isfinite(P) & np.isfinite(M) & np.isfinite(w)
            if f.sum() < 400:
                continue
            x = M[f] * w[f]
            if not np.any(x):
                continue
            sl = float(P[f] @ x / (x @ x))
            big = np.abs(x) >= np.percentile(np.abs(x), 75)
            med = float(np.median(P[f][big] / x[big]))
            out['columns'][f'{j}_{s}'] = {'n': int(f.sum()), 'median_ratio_top_quartile': round(med, 4), 'slope': round(sl, 4),
                                          'corr': round(float(np.corrcoef(P[f], x)[0, 1]), 4)}
    ank = [v for k, v in out['columns'].items() if k.startswith('ankle')]
    out['shares_moment_divisor'] = all(v['median_ratio_top_quartile'] > 0 and abs(np.log(v['median_ratio_top_quartile'])) <= band
                                       for v in ank) if ank else None
    kn = [v['median_ratio_top_quartile'] for k, v in out['columns'].items() if k.startswith('knee')]
    out['knee_ratio_range'] = [min(kn), max(kn)] if kn else None
    return out


def classify(rec, R, readme, exact):
    own = readme[rec['subject']]
    task = rec['task']
    out = {'own_readme_mass_kg': own}
    lev = rec['ankle']['implied_mass_kg'] / R['ankle_bias_centre_ratio'] if rec.get('usable') and rec.get('ankle', {}).get('implied_mass_kg') else None
    out['lever_divisor_kg'] = round(lev, 2) if lev else None
    if exact and exact.get('trial') == task:
        out.update(cls='exact', divisor_kg=exact['table_mass_kg'], divisor_source=f"local N*m re-run slope {exact['slope_kg']} = README {exact['table_subject']} table mass")
        out['candidates'] = [[exact['table_subject'], exact['table_mass_kg']]]
        if lev:
            out['lever_log_err_vs_exact'] = round(float(np.log(lev / exact['table_mass_kg'])), 4)
            out['lever_agrees_with_exact'] = bool(abs(np.log(lev / exact['table_mass_kg'])) <= R['candidate_band_half_width_log'])
    else:
        reason = code = None
        if rec['family'] not in LOCOMOTION:
            code, reason = 'non-gait family', 'non-gait task family; lever method not calibrated for it'
        elif rec['family'] in UNRELIABLE_FAMILIES:
            code, reason = 'curb family', 'curb family (C03: unreliable lever estimate)'
        elif not rec.get('usable'):
            code, reason = 'not usable', rec.get('reason', 'not usable')
        elif not rec['ankle']['implied_mass_kg'] or rec['ankle']['corr'] < R['reliable_min_ankle_corr']:
            code, reason = 'ankle corr < 0.98', f"ankle corr {rec['ankle']['corr']} < {R['reliable_min_ankle_corr']}"
        cands = sorted(([k, v] for k, v in readme.items() if lev and abs(np.log(v / lev)) <= R['candidate_band_half_width_log']),
                       key=lambda kv: abs(np.log(kv[1] / lev))) if lev else []
        out['candidates'] = cands
        if lev:
            outside = [v for v in readme.values() if abs(np.log(v / lev)) > R['candidate_band_half_width_log']]
            out['nearest_excluded_log_margin'] = round(min(abs(np.log(v / lev)) for v in outside) - R['candidate_band_half_width_log'], 4)
        if reason:
            out.update(cls='unreliable', reason=reason, reason_code=code)
        elif not cands:
            out.update(cls='no-match')
        else:
            vals = [v for _, v in cands]
            if np.log(max(vals) / min(vals)) <= R['same_value_max_spread_log']:
                out.update(cls='unique-estimate', divisor_kg=cands[0][1], divisor_source=f'force-plate lever estimate {round(lev, 2)} kg; nearest table mass {cands[0][0]}')
            else:
                out.update(cls='ambiguous')
        if cands:
            vals = [v for _, v in cands]
            out['candidate_factor_range'] = [round(min(vals) / own, 4), round(max(vals) / own, 4)]
            out['own_mass_is_candidate'] = any(k == rec['subject'] for k, _ in cands)
            if exact:
                out['subject_rerun_divisor_is_candidate'] = any(abs(np.log(v / exact['table_mass_kg'])) < 1e-9 for _, v in cands)
    out['rescalable'] = out['cls'] in ('exact', 'unique-estimate')
    out['rescale_factor'] = round(out['divisor_kg'] / own, 4) if out['rescalable'] else None
    return out


def exact_info(e, readme):
    div = c03.exact_divisor(e) if e.get('present') else None
    if div is None:
        return None
    subj, m = min(readme.items(), key=lambda kv: abs(np.log(kv[1] / div)))
    if abs(np.log(m / div)) > 0.001:
        return {'trial': e.get('trial'), 'slope_kg': div, 'table_subject': None, 'table_mass_kg': None, 'unmatched': True}
    return {'trial': e['trial'], 'slope_kg': div, 'table_subject': subj, 'table_mass_kg': m}


def run(subjects, out_path, stage):
    import pandas  # noqa: F401
    resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 ** 2, 1536 * 1024 ** 2))
    t0 = time.monotonic()
    c03a = json.loads(C03_AUDIT.read_text())
    R = rules(c03a)
    data = {'task_id': 'GT23-C04', 'stage': stage, 'scientific_approval': False, 'rescaling_applied': False,
            'question': 'Which mass was each GT23 trial divided by, and what factor rescales it to the participant\'s own mass (D-GT23-C03-1 = B)?',
            'probe': {'path': str(HERE.relative_to(ROOT)), 'sha256': c03.digest(HERE),
                      'c03_probe_sha256': c03.digest(HERE.parent / 'probe_gt23_c03_normalizing_mass.py')},
            'c03_audit': {'path': str(C03_AUDIT.relative_to(ROOT)), 'sha256': c03.digest(C03_AUDIT)},
            'rules': R, 'rules_fixed_at_utc': utc(), 'subjects': subjects}
    readme = c03.masses(c03.PUB_MASSES)
    data['readme_masses_kg'] = readme
    zipdir = {e['name']: e for e in json.loads(c03.ZIP_DIR.read_text())}
    reader = CachedReader(zipdir)
    inv = c03.inventory(reader)
    data['inventory_files_read'] = len(reader.files)
    trials, reruns = [], {}
    for subj in subjects:
        e = c03.eh_check(reader, subj)
        reader.clear()
        reruns[subj] = {k: v for k, v in e.items()}
        ex = exact_info(e, readme)
        reruns[subj]['exact'] = ex
        for task in sorted(p.name for p in (RAW / subj / 'CSV_Data').iterdir() if p.is_dir()):
            ts = time.monotonic()
            nfiles = len(reader.files)
            try:
                r = c03.analyse_trial(reader, inv, readme, subj, task, 'census')
            except (KeyError, ValueError, FileNotFoundError) as err:
                r = {'subject': subj, 'task': task, 'usable': False, 'reason': f'{type(err).__name__}: {err}'}
            r.setdefault('family', c03.family(task))
            for side in r.get('sides', []):
                side.pop('first_stance_ankle_centre_calcn_m', None); side.pop('first_stance_knee_centre_calcn_m', None)
            try:
                r['loaded_sample_estimate'] = loaded_estimate(reader, inv, subj, task, R['ankle_bias_centre_ratio'])
            except (KeyError, ValueError, FileNotFoundError) as err:
                r['loaded_sample_estimate'] = {'error': f'{type(err).__name__}: {err}'}
            try:
                r['power_check'] = power_check(reader, subj, task, R['candidate_band_half_width_log'])
            except (KeyError, ValueError, FileNotFoundError) as err:
                r['power_check'] = {'error': f'{type(err).__name__}: {err}'}
            if r.get('knee', {}).get('implied_mass_kg'):
                r['knee']['divisor_kg_knee_bias'] = round(r['knee']['implied_mass_kg'] / c03a['tolerance_v2']['knee_bias']['centre_ratio'], 2)
            r['census'] = classify(r, R, readme, ex if ex and not ex.get('unmatched') else None)
            r['files'] = [{'name': Path(f['path']).name, 'sha256': f['sha256'], 'publisher_crc32_match': f['publisher_crc32_match']}
                          for f in reader.files[nfiles:]]
            r['seconds'] = round(time.monotonic() - ts, 2)
            reader.clear()
            trials.append(r)
            c = r['census']
            print(f"{subj} {task}: {c['cls']} lev={c.get('lever_divisor_kg')} div={c.get('divisor_kg')} f={c.get('rescale_factor')} "
                  f"pw={r['power_check'].get('shares_moment_divisor')} {r['seconds']}s rss={c03.peak_rss_mib()}", flush=True)
            if c03.peak_rss_mib() > RSS_LIMIT_MIB:
                raise MemoryError('peak RSS above limit')
    data['local_nm_rerun'] = reruns
    data['trials'] = trials
    data['summary'] = summarize(trials, subjects)
    files = reader.files
    data['files_read'] = {'count': len(files), 'bytes': int(sum(f['bytes'] for f in files)),
                          'publisher_crc32_mismatch': [f['path'] for f in files if f['publisher_crc32_match'] is False],
                          'not_in_publisher_archive': sorted({f['path'] for f in files if f['publisher_crc32_match'] is None}),
                          'manifest_sha256': hashlib.sha256('\n'.join(sorted(f"{f['path']} {f['sha256']}" for f in files)).encode()).hexdigest()}
    data['runtime_seconds'] = round(time.monotonic() - t0, 1)
    data['peak_rss_mib'] = c03.peak_rss_mib()
    data['finished_at_utc'] = utc()
    Path(out_path).write_text(json.dumps(data, indent=1) + '\n')
    print(json.dumps({'summary': data['summary'], 'runtime_seconds': data['runtime_seconds'], 'peak_rss_mib': data['peak_rss_mib']}, indent=1))


def summarize(trials, subjects):
    classes = ['exact', 'unique-estimate', 'ambiguous', 'no-match', 'unreliable']
    s = {'trials': len(trials), 'by_class': {c: sum(t['census']['cls'] == c for t in trials) for c in classes}}
    s['rescalable'] = sum(t['census']['rescalable'] for t in trials)
    s['by_subject'] = {subj: {c: sum(t['census']['cls'] == c for t in trials if t['subject'] == subj) for c in classes} for subj in subjects}
    fam = {}
    for t in trials:
        fam.setdefault(t['family'], {c: 0 for c in classes})[t['census']['cls']] += 1
    s['by_family'] = fam
    s['unreliable_reasons'] = {}
    for t in trials:
        if t['census']['cls'] == 'unreliable':
            k = t['census']['reason_code']
            s['unreliable_reasons'][k] = s['unreliable_reasons'].get(k, 0) + 1
    s['ambiguous_trials'] = [[t['subject'], t['task'], t['census']['lever_divisor_kg'], [v for _, v in t['census']['candidates']]]
                             for t in trials if t['census']['cls'] == 'ambiguous']
    amb = [t['census'] for t in trials if t['census']['cls'] == 'ambiguous']
    s['ambiguous_own_mass_is_candidate'] = sum(c['own_mass_is_candidate'] for c in amb)
    s['ambiguous_factor_range_widest'] = max((c['candidate_factor_range'][1] / c['candidate_factor_range'][0] for c in amb), default=None)
    s['exact_lever_check'] = [[t['subject'], t['task'], t['census']['divisor_kg'], t['census']['lever_divisor_kg'], t['census'].get('lever_agrees_with_exact')]
                              for t in trials if t['census']['cls'] == 'exact']
    s['unique_margin_min_log'] = min((t['census']['nearest_excluded_log_margin'] for t in trials if t['census']['cls'] == 'unique-estimate'), default=None)
    s['no_match_trials'] = [[t['subject'], t['task'], t['census']['lever_divisor_kg']] for t in trials if t['census']['cls'] == 'no-match']
    s['rescale_table'] = [[t['subject'], t['task'], t['census']['cls'], t['census']['divisor_kg'], t['census']['rescale_factor']]
                          for t in trials if t['census']['rescalable']]
    pc = [t['power_check'].get('shares_moment_divisor') for t in trials if t['power_check'].get('present')]
    s['power_check'] = {'tested': sum(x is not None for x in pc), 'shares_moment_divisor': sum(bool(x) for x in pc),
                        'fails': [[t['subject'], t['task']] for t in trials
                                  if t['power_check'].get('present') and t['power_check'].get('shares_moment_divisor') is False],
                        'knee_ratio_overall_range': [min((t['power_check']['knee_ratio_range'][0] for t in trials if t['power_check'].get('knee_ratio_range')), default=None),
                                                     max((t['power_check']['knee_ratio_range'][1] for t in trials if t['power_check'].get('knee_ratio_range')), default=None)]}
    return s


def sensitivity():
    """Reads only the census audit (no data reads). Added after the census: how many unique-estimate trials would
    become ambiguous if the band were one calibration robust sd (C03 ankle_bias robust_sd_log) wider. Classes in
    the census are not changed; this block only flags fragile matches."""
    data = json.loads(AUDIT.read_text())
    if data.get('stage') != 'census':
        raise ValueError('run the census first')
    c03a = json.loads(C03_AUDIT.read_text())
    sd = c03a['tolerance_v2']['ankle_bias']['robust_sd_log']
    fragile = [[t['subject'], t['task'], t['census']['lever_divisor_kg'], t['census']['divisor_kg'], t['census']['nearest_excluded_log_margin']]
               for t in data['trials'] if t['census']['cls'] == 'unique-estimate' and t['census']['nearest_excluded_log_margin'] < sd]
    keys = {(f[0], f[1]) for f in fragile}
    robust = [r for r in data['summary']['rescale_table'] if (r[0], r[1]) not in keys]
    data['sensitivity'] = {
        'added_after_census': True, 'rule': f'unique-estimate is fragile when another README mass lies within one calibration robust sd ({sd} log) outside the band',
        'fragile_unique_estimates': fragile, 'n_fragile': len(fragile),
        'rescalable_strict': len(data['summary']['rescale_table']), 'rescalable_excluding_fragile': len(robust),
        'rescale_table_excluding_fragile': robust, 'computed_at_utc': utc()}
    AUDIT.write_text(json.dumps(data, indent=1) + '\n')
    print(json.dumps({k: v for k, v in data['sensitivity'].items() if k != 'rescale_table_excluding_fragile'}, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('stage', choices=['pilot', 'census', 'sensitivity'])
    ap.add_argument('--subjects', default=None)
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    os.nice(max(0, 19 - os.nice(0)))
    if a.stage == 'sensitivity':
        return sensitivity()
    all_subj = sorted(c03.masses(c03.PUB_MASSES))
    subjects = a.subjects.split(',') if a.subjects else all_subj
    if a.stage == 'pilot' and (not a.out or len(subjects) > 2):
        raise SystemExit('pilot needs --out (scratch) and at most 2 subjects')
    run(subjects, a.out or AUDIT, a.stage)


if __name__ == '__main__':
    main()
