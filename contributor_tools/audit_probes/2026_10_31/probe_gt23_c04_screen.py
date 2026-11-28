"""GT23-C04 round 2: screen the 61 matched trials, and build the review sheets.

Stages (run one at a time):
  screen   Bounded read of only the 61 trials the census matched (exact + unique-estimate): Joint_Moments.csv and
           Virtual_Insoles.csv. Applies two screens fixed in SCREEN_RULES before any read, and writes a 'screen'
           block into docs/quality/audits/gt23-c04-trial-divisors.json. Census classes are kept; the screen adds a
           screened class. Read-only probe exception: one trial in memory at a time, nice 19 / ionice idle
           (caller), single-threaded, peak RSS recorded (< 300 MiB), nothing written under converted_datasets/ or
           the source folder.
  sheets   Reads only the audit JSON and builds review_sheets/GT23-C04/ (verification) and
           review_sheets/D-GT23-C04-1/ (decision) with contributor_tools/common/review_sheet.py.

Second estimator (written for this screen; it does not use the census lever code, the OpenSim models or the
joint angles): in each calcn frame the published ankle moment times the divisor D equals the quasi-static
moment of the insole force about a fixed talus point (px, py) that is fitted with D:
    -cop * Fv = D * M_pub - px * Fv + py * F_ap        (least squares, all samples with Fv > 100 N, each side
                                                        its own talus point, one D per trial)
The ankle-axis tilt is a constant factor, absorbed by a bias calibrated on the 8 exact trials.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
import datetime as dt
import importlib.util
import json
from pathlib import Path
import resource
import sys
import time

import numpy as np

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
_spec = importlib.util.spec_from_file_location('c03', HERE.parent / 'probe_gt23_c03_normalizing_mass.py')
c03 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c03)

AUDIT = ROOT / 'docs/quality/audits/gt23-c04-trial-divisors.json'
C03_AUDIT = ROOT / 'docs/quality/audits/gt23-c03-normalizing-mass.json'
RAW = c03.RAW
RSS_LIMIT_MIB = 300
LOADED_N = 100.0

# Fixed before the screen read (2026-10-31, after the verifier's round 1, before any of these 61 trials were re-read):
SCREEN_RULES = {
    'min_gait_stances': 10,
    'min_gait_stances_why': ('Per-stance ankle implied mass in the census (220 trial sides with >= 4 stances) has a robust log sd of '
                             '0.020 (median), 0.033 (75th pct) and 0.047 (90th pct). Requiring the pooled estimate\'s sampling error '
                             '(sd / sqrt(n)) to be no larger than the C03 calibration robust sd (0.0152 log) for a 90th-percentile trial '
                             'gives n >= (0.047 / 0.0152)^2 = 9.7, so 10 gait stances (both legs). Matched trials have 4 or >= 11 '
                             'stances, so any threshold from 5 to 11 gives the same split.'),
    'second_estimator': 'fitted-talus least squares (module docstring); bias = median(D / exact divisor) over the 8 exact trials',
    'agreement': ('the second estimate (divided by its bias) lies within the C03 band (0.0488 log) of the matched divisor AND the matched '
                  'mass value is the README table value nearest to it (values within 0.5 % count as one)'),
    'fail_action': 'unique-estimate trials failing either screen are re-classed ambiguous (not rescalable); exact trials are not screened',
    'post_hoc': True,
    'post_hoc_note': 'Added after the census and after the verifier showed that short-trial matches depend on the estimator.',
}


def utc():
    return dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def fitted_talus(reader, subj, task):
    d = RAW / subj / 'CSV_Data' / task
    mom, ins = reader.table(d / 'Joint_Moments.csv'), reader.table(d / 'Virtual_Insoles.csv')
    if len(mom) != len(ins) or float(np.max(np.abs(mom.time.to_numpy() - ins.time.to_numpy()))) > 1e-6:
        return {'error': 'time bases differ'}
    ys, cols, n_side = [], [], {}
    sides = [s for s in 'rl']
    for k, s in enumerate(sides):
        S = s.upper()
        M = mom[f'ankle_angle_{s}_moment'].to_numpy(float)
        fv, fap, cop = (ins[f'{S}{x}'].to_numpy(float) for x in ('VerticalF', 'ShearF_AP', 'COP_AP'))
        f = np.isfinite(M) & np.isfinite(fv) & np.isfinite(fap) & np.isfinite(cop) & (np.nan_to_num(fv) > LOADED_N)
        n_side[s] = int(f.sum())
        if f.sum() < 200:
            continue
        X = np.zeros((int(f.sum()), 1 + 2 * len(sides)))
        X[:, 0] = M[f]
        X[:, 1 + 2 * k] = -fv[f]
        X[:, 2 + 2 * k] = fap[f]
        ys.append(-cop[f] * fv[f]); cols.append(X)
    if not ys:
        return {'error': 'no loaded samples', 'samples_per_side': n_side}
    X, y = np.vstack(cols), np.concatenate(ys)
    keep = np.any(X[:, 1:] != 0, axis=0)
    X = np.column_stack([X[:, 0], X[:, 1:][:, keep]])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    return {'D_kg_raw': round(float(beta[0]), 3), 'samples_per_side': n_side,
            'talus_xy_m': [round(float(v), 4) for v in beta[1:]],
            'r2': round(1 - float(resid @ resid) / float((y - y.mean()) @ (y - y.mean())), 4)}


def group_nearest(readme, x):
    """Nearest README mass value to x, with values within 0.5 % merged into one group."""
    vals = sorted(set(readme.values()))
    near = min(vals, key=lambda v: abs(np.log(v / x)))
    return sorted(v for v in vals if abs(np.log(v / near)) <= np.log(1.005))


def stage_screen():
    import pandas  # noqa: F401
    resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 ** 2, 1536 * 1024 ** 2))
    t0 = time.monotonic()
    rules_fixed = utc()
    data = json.loads(AUDIT.read_text())
    if data.get('stage') != 'census':
        raise ValueError('census audit required')
    band = data['rules']['candidate_band_half_width_log']
    readme = data['readme_masses_kg']
    fragile = {(f[0], f[1]) for f in data['sensitivity']['fragile_unique_estimates']}
    matched = [t for t in data['trials'] if t['census']['rescalable']]
    zipdir = {e['name']: e for e in json.loads(c03.ZIP_DIR.read_text())}
    reader = c03.Reader(zipdir)
    rows = []
    for t in matched:
        st = {p: (RAW / t['subject'] / 'CSV_Data' / t['task'] / p).stat().st_mtime_ns for p in ('Joint_Moments.csv', 'Virtual_Insoles.csv')}
        e = fitted_talus(reader, t['subject'], t['task'])
        if any((RAW / t['subject'] / 'CSV_Data' / t['task'] / p).stat().st_mtime_ns != v for p, v in st.items()):
            raise ValueError('source changed during read')
        rows.append({'subject': t['subject'], 'task': t['task'], 'census_class': t['census']['cls'],
                     'divisor_kg': t['census']['divisor_kg'], 'own_mass_kg': t['census']['own_readme_mass_kg'],
                     'census_lever_kg': t['census']['lever_divisor_kg'], 'gait_stances': t.get('stances_total'),
                     'fragile': (t['subject'], t['task']) in fragile, 'second_estimator': e})
        print(f"{t['subject']} {t['task']}: D={e.get('D_kg_raw')} r2={e.get('r2')} rss={c03.peak_rss_mib()}", flush=True)
        if c03.peak_rss_mib() > RSS_LIMIT_MIB:
            raise MemoryError('peak RSS above limit')
    cal = [r for r in rows if r['census_class'] == 'exact' and r['second_estimator'].get('D_kg_raw')]
    q = np.log([r['second_estimator']['D_kg_raw'] / r['divisor_kg'] for r in cal])
    bias = float(np.exp(np.median(q)))
    cal_sd = 1.4826 * float(np.median(np.abs(q - np.median(q))))
    counts = {'exact': 0, 'unique_kept': 0, 'unique_to_ambiguous': 0}
    for r in rows:
        D = r['second_estimator'].get('D_kg_raw')
        e2 = D / bias if D and D > 0 else None
        r['second_divisor_kg'] = round(e2, 2) if e2 else None
        r['second_log_err_vs_divisor'] = round(float(np.log(e2 / r['divisor_kg'])), 4) if e2 else None
        r['second_nearest_value_kg'] = group_nearest(readme, e2) if e2 else None
        if r['census_class'] == 'exact':
            r['screened_class'] = 'exact'; counts['exact'] += 1
            continue
        fails = []
        if (r['gait_stances'] or 0) < SCREEN_RULES['min_gait_stances']:
            fails.append(f"{r['gait_stances']} gait stances < {SCREEN_RULES['min_gait_stances']}")
        if not e2:
            fails.append('second estimator failed')
        else:
            if abs(np.log(e2 / r['divisor_kg'])) > band:
                fails.append(f'second estimate {e2:.1f} kg outside the band of {r["divisor_kg"]}')
            if not any(abs(np.log(v / r['divisor_kg'])) < 1e-9 for v in r['second_nearest_value_kg']):
                fails.append(f'second estimate {e2:.1f} kg is nearest to {r["second_nearest_value_kg"]}, not {r["divisor_kg"]}')
        r['screen_fails'] = fails
        r['screened_class'] = 'unique-estimate' if not fails else 'ambiguous'
        counts['unique_kept' if not fails else 'unique_to_ambiguous'] += 1
    kept = [r for r in rows if r['screened_class'] in ('exact', 'unique-estimate')]
    data['screen'] = {
        'rules': SCREEN_RULES, 'rules_fixed_at_utc': rules_fixed,
        'probe': {'path': str(HERE.relative_to(ROOT)), 'sha256': c03.digest(HERE)},
        'calibration': {'n_exact': len(cal), 'bias': round(bias, 4), 'robust_sd_log': round(cal_sd, 4),
                        'per_trial_ratio': {r['subject']: round(r['second_estimator']['D_kg_raw'] / r['divisor_kg'], 4) for r in cal},
                        'worst_abs_log': round(float(np.max(np.abs(q - np.log(bias)))), 4)},
        'trials': rows, 'counts': counts,
        'option_counts_after_screen': {'A_none': 0,
                                       'B_well_separated': sum(1 for r in kept if not r['fragile']),
                                       'C_all_matched': len(kept)},
        'option_counts_before_screen': {'A_none': 0, 'B_well_separated': data['sensitivity']['rescalable_excluding_fragile'],
                                        'C_all_matched': data['sensitivity']['rescalable_strict']},
        'rescale_table_after_screen': [[r['subject'], r['task'], r['screened_class'], r['divisor_kg'],
                                        round(r['divisor_kg'] / r['own_mass_kg'], 4), r['fragile']] for r in kept],
        'factor_range_after_screen': [min(r['divisor_kg'] / r['own_mass_kg'] for r in kept), max(r['divisor_kg'] / r['own_mass_kg'] for r in kept)],
        'files_read': {'count': len(reader.files), 'bytes': int(sum(f['bytes'] for f in reader.files)),
                       'publisher_crc32_mismatch': [f['path'] for f in reader.files if f['publisher_crc32_match'] is False]},
        'runtime_seconds': round(time.monotonic() - t0, 1), 'peak_rss_mib': c03.peak_rss_mib(), 'finished_at_utc': utc()}
    data['screen']['factor_range_after_screen'] = [round(v, 4) for v in data['screen']['factor_range_after_screen']]
    AUDIT.write_text(json.dumps(data, indent=1) + '\n')
    print(json.dumps({k: v for k, v in data['screen'].items() if k not in ('trials', 'rules', 'rescale_table_after_screen')}, indent=1))


# ---------------------------------------------------------------- sheets

INK, MUTED, BLUE, ORANGE, GREY, RED = '#20252B', '#5b6672', '#2a78d6', '#eb6834', '#9aa3ad', '#a8322d'
SHEET_V = ROOT / 'review_sheets/GT23-C04'
SHEET_D = ROOT / 'review_sheets/D-GT23-C04-1'


def fig_coverage(plt, data, path):
    """Per subject: trials with an established divisor (after the screen) vs not, split by reason."""
    scr = {(r['subject'], r['task']): r['screened_class'] for r in data['screen']['trials']}
    subs = sorted(data['readme_masses_kg'])
    cats = [('established', BLUE), ('ambiguous or no match', ORANGE), ('not estimable', GREY)]
    fig, ax = plt.subplots(figsize=(4.5, 4.6), layout='constrained')
    for y, s in enumerate(subs):
        ts = [t for t in data['trials'] if t['subject'] == s]
        n = {'established': 0, 'ambiguous or no match': 0, 'not estimable': 0}
        for t in ts:
            c = scr.get((s, t['task']), t['census']['cls'])
            n['established' if c in ('exact', 'unique-estimate') else 'not estimable' if c == 'unreliable' else 'ambiguous or no match'] += 1
        left = 0
        for k, col in cats:
            ax.barh(y, n[k], left=left, color=col, height=.7)
            left += n[k]
    ax.set_yticks(range(len(subs)), subs)
    ax.invert_yaxis()
    ax.set_xlabel('GT23 trials')
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=col, label=k) for k, col in cats], loc='outside lower center', ncol=2, fontsize=10,
               handletextpad=.4, columnspacing=.8)
    c03.save(fig, path); plt.close(fig)


def fig_screen(plt, data, path):
    """Second estimator / matched divisor against gait stances, with the band; failing trials marked."""
    band = data['rules']['candidate_band_half_width_log']
    rows = [r for r in data['screen']['trials'] if r['second_divisor_kg']]
    fig, ax = plt.subplots(figsize=(4.5, 4.2), layout='constrained')
    ax.axhspan(100 * (np.exp(-band) - 1), 100 * (np.exp(band) - 1), color=BLUE, alpha=.12, lw=0)
    ax.axvline(data['screen']['rules']['min_gait_stances'], color=MUTED, ls='--', lw=1)
    for r in rows:
        y = 100 * (r['second_divisor_kg'] / r['divisor_kg'] - 1)
        if r['census_class'] == 'exact':
            ax.plot(r['gait_stances'], y, 's', color=INK, ms=5)
        elif r['screened_class'] == 'unique-estimate' and r['fragile']:
            ax.plot(r['gait_stances'], y, 'o', mfc='white', mec=BLUE, mew=1.5, ms=6)
        elif r['screened_class'] == 'unique-estimate':
            ax.plot(r['gait_stances'], y, 'o', color=BLUE, ms=5)
        else:
            ax.plot(r['gait_stances'], y, 'x', color=RED, ms=7, mew=1.6)
    ax.set_xscale('log')
    ax.set_xticks([4, 10, 30, 100, 300], ['4', '10', '30', '100', '300'])
    ax.minorticks_off()
    ax.set_xlabel('gait stances in the trial (log scale)')
    ax.set_ylabel('second estimate vs matched mass (%)')
    ax.plot([], [], 's', color=INK, label='exact')
    ax.plot([], [], 'o', color=BLUE, label='kept')
    ax.plot([], [], 'o', mfc='white', mec=BLUE, mew=1.5, label='kept, other mass near edge')
    ax.plot([], [], 'x', color=RED, mew=1.6, label='dropped')
    fig.legend(loc='outside lower center', ncol=2, fontsize=10, handletextpad=.3, columnspacing=.8)
    c03.save(fig, path); plt.close(fig)


def fig_power(plt, data, path):
    """Ankle power / (moment x velocity) per trial; a made-up mis-scaled trial for contrast."""
    r = [v['median_ratio_top_quartile'] for t in data['trials'] for k, v in t['power_check'].get('columns', {}).items() if k.startswith('ankle')]
    fig, ax = plt.subplots(figsize=(4.5, 3.4), layout='constrained')
    band = data['rules']['candidate_band_half_width_log']
    ax.axvspan(np.exp(-band), np.exp(band), color=BLUE, alpha=.12, lw=0)
    ax.hist(r, bins=np.linspace(0.55, 1.15, 61), color=BLUE)
    made_up = 71.5 / 113.5   # AB05 incline if powers had used the own mass while moments used 113.5 kg
    ax.axvline(made_up, color=RED, ls='--', lw=1.4)
    ax.text(made_up + .01, ax.get_ylim()[1] * .8, 'made-up example:\npowers divided by\nanother mass', color=RED, fontsize=10)
    ax.set_xlabel('ankle power / (moment × velocity)')
    ax.set_ylabel('trial legs')
    c03.save(fig, path); plt.close(fig)


def run_cut(data):
    """Matched tire-run and cutting trials: second estimate vs matched mass (unexplained disagreement)."""
    rows = [r for r in data['screen']['trials'] if r['task'].startswith(('tire_run', 'cutting'))]
    low = [r for r in rows if r['screened_class'] == 'ambiguous']
    kept = [r for r in rows if r['screened_class'] != 'ambiguous']
    pct = [100 * (r['second_divisor_kg'] / r['divisor_kg'] - 1) for r in low]
    return {'n': len(rows), 'n_low': len(low), 'lo': min(pct), 'hi': max(pct), 'all_low': all(p < 0 for p in pct),
            'kept': [f"{r['subject']} {r['task'].replace('_1', '').replace('_', '-')}" for r in kept],
            'kept_fragile': all(r['fragile'] for r in kept)}


def decision_content(data):
    rc = run_cut(data)
    if not (rc['all_low'] and rc['kept_fragile']):
        raise ValueError('tire-run/cutting text assumes all dropped read low and all kept are only in the largest option')
    sc = data['screen']['option_counts_after_screen']
    total = len(data['trials'])
    nb, nc = sc['B_well_separated'], sc['C_all_matched']
    pre = data['screen']['option_counts_before_screen']
    options = [
        (0, 'Withhold kinetics for every GT23 trial', f'All {total} trials',
         'Returns to the withhold option for GT23. Kinematics and forces released; no GT23 moments or powers. Nothing estimated. Reversible.'),
        (nb, f'Rescale the {nb} well-separated matches', f'{total - nb} trials (kinetics only)',
         f'Moments and powers rescaled to own mass for {nb} trials (exact or matched by two estimators, at least 10 stances, '
         f'no other recorded mass near the band edge). Other trials keep kinematics and forces; their moments and powers are withheld. Reversible.'),
        (nc, f'Rescale all {nc} matches', f'{total - nc} trials (kinetics only)',
         f'As the previous option plus {nc - nb} matches with another recorded mass just outside the 5 % band, so a few factors may be '
         f'off by 5-10 %. These include {" and ".join(rc["kept"])}, the only tire-run and cutting matches kept; in the other '
         f'{rc["n_low"]} the second estimator reads {-rc["hi"]:.1f}-{-rc["lo"]:.1f} % low. '
         f'Other trials keep kinematics and forces; their moments and powers are withheld. Reversible.'),
    ]
    options.sort(key=lambda o: o[0])   # neutral order: GT23 trials released with kinetics (0, B, C)
    return options, nb, nc, pre


def build_sheets():
    from contributor_tools.common.review_sheet import page
    data = json.loads(AUDIT.read_text())
    if 'screen' not in data:
        raise ValueError('run the screen first')
    plt = c03.style()
    for d in (SHEET_V, SHEET_D):
        d.mkdir(parents=True, exist_ok=True)
        for old in d.glob('*.png'):
            old.unlink()
    fig_coverage(plt, data, SHEET_V / 'fig1_coverage.png')
    fig_screen(plt, data, SHEET_V / 'fig2_screen.png')
    fig_power(plt, data, SHEET_V / 'fig3_power.png')
    fig_coverage(plt, data, SHEET_D / 'fig1_coverage.png')
    fig_screen(plt, data, SHEET_D / 'fig2_screen.png')
    s, scr = data['summary'], data['screen']
    total = len(data['trials'])
    options, nb, nc, pre = decision_content(data)
    exact = s['by_class']['exact']
    dropped = scr['counts']['unique_to_ambiguous']
    lo, hi = scr['factor_range_after_screen']
    pw = s['power_check']
    shifting = ['AB05', 'AB07', 'AB01', 'AB06', 'AB10', 'AB13']
    rc = run_cut(data)
    tc_chip = (f'Tire run and cutting: second estimate {-rc["hi"]:.1f}-{-rc["lo"]:.1f} % low in {rc["n_low"]} of {rc["n"]} matches, '
               f'cause unknown; {len(rc["kept"])} kept')
    chips_v = [
        ('pass', f'Independent re-check: {total} of {total} trial classes reproduced'),
        ('pass', f'Exact divisors in {exact} level-walk trials; force plates agree in {exact} of {exact}'),
        ('pass', f'Powers carry each trial\'s moment divisor: ankle {pw["shares_moment_divisor"]} of {pw["tested"]}; knee explained by 6 Hz moment filtering'),
        ('fail', f'Divisor established for only {nc} of {total} trials ({dropped} matches dropped by the screen)'),
        ('fail', f'Divisor changes between trials of one subject in {len(shifting)} subjects'),
        ('unchecked', f'{s["unreliable_reasons"]["non-gait family"]} non-gait trials: no calibrated estimator'),
        ('unchecked', tc_chip),
        ('unchecked', 'Origin of the N·m re-run files'),
    ]
    details_v = [
        f'Census: {total} trials; classes before the screen {s["by_class"]}. Unreliable reasons {s["unreliable_reasons"]}.',
        f'Screen (post hoc, rules fixed before the read): at least {scr["rules"]["min_gait_stances"]} gait stances and agreement of a fitted-talus estimator '
        f'(bias {scr["calibration"]["bias"]}, robust sd {scr["calibration"]["robust_sd_log"]} log on {scr["calibration"]["n_exact"]} exact trials). '
        f'Unique matches kept {scr["counts"]["unique_kept"]}, re-classed ambiguous {dropped}.',
        f'Counts by option: before the screen B {pre["B_well_separated"]} / C {pre["C_all_matched"]}; after B {nb} / C {nc}. Factors after the screen {lo}-{hi}.',
        'Power check: median ankle power / (moment x velocity) within 5 % of 1. Published power = 6 Hz low-pass moment x velocity (verifier, ratio 1.0000 in 12 columns); the filter is linear, so the rescale factor applies to hip, knee and ankle powers.',
        'Figure 3 contrast: the dashed line is a made-up trial whose powers used AB05\'s own mass while its moments used 113.5 kg.',
        f'Evidence: {AUDIT.relative_to(ROOT)}; builder {HERE.relative_to(ROOT)}; census probe probe_gt23_c04_trial_divisors.py. '
        f'Peak memory census {data["peak_rss_mib"]} MiB, screen {scr["peak_rss_mib"]} MiB.',
        'Not checked: AB09 dynamic_walk_1 and weighted_walk_1 read about 5 % above the nearest recorded mass (87.6 kg); left as no match.',
        f'Tire-run and cutting matches kept: {", ".join(rc["kept"])} (both only in the largest option).']
    page(SHEET_V / 'index.html', title='GT23 trial divisors',
         ask='Check that the per-trial divisor table can be trusted.',
         headline=f'Divisor established for {nc} of {total} GT23 trials',
         chips=chips_v,
         figures=[('fig1_coverage.png', 'How many trials per subject have an established divisor?', 'Grey: no calibrated estimate.', 'Trials per subject by divisor status'),
                  ('fig2_screen.png', 'Does a second estimator agree with each match?', 'Crosses dropped: under 10 stances, or nearer another mass. Open circles: another mass near the band edge.', 'Second estimate against matched mass by stance count'),
                  ('fig3_power.png', 'Do powers use the same divisor as moments?', 'Dashed line: made-up mis-scaled trial.', 'Ankle power ratio histogram')],
         not_shown=['Hip moments', 'Why the divisors shifted', 'Non-gait trials with another estimator'],
         reply='looks right, or what is wrong', details=details_v)
    keys = 'ABC'
    rows = [(f'{k} · {o[1]}', [o[2], o[3]]) for k, o in zip(keys, options)]
    rows.append(('Defer', ['All GT23 kinetics', 'GT23 moments and powers stay out of any release; kinematics, forces and other datasets unaffected.']))
    why = (f'The {nb} trials are exact or matched by two independent estimators with enough stances and no recorded mass at the band edge; '
           f'the other {nc - nb} matches could be a neighbouring mass, which would make their factor wrong by 5-10 %.')
    decision = {'question': 'Which GT23 trials should carry moments and powers rescaled to the participant\'s own mass?',
                'columns': ['Left out', 'Consequence'], 'rows': rows,
                'recommendation': f'B. {why} Confidence: medium.',
                'footnote': 'Ordered by trials with kinetics.'}
    chips_d = [
        ('pass', f'Exact divisors in {exact} level-walk trials'),
        ('fail', f'Divisor established for only {nc} of {total} trials'),
        ('unchecked', f'{s["unreliable_reasons"]["non-gait family"]} non-gait trials have no calibrated estimator'),
        ('unchecked', tc_chip),
    ]
    details_d = [f'After the screen: B {nb}, C {nc} of {total} (before: {pre["B_well_separated"]} / {pre["C_all_matched"]}). Rescale factors {lo}-{hi}.',
                 'Trials not rescaled keep kinematics and forces; only their moments and powers are withheld.',
                 'Options ordered by trials released with kinetics (0, B, C); the builder sorts on that count.',
                 f'Evidence: {AUDIT.relative_to(ROOT)}; builder {HERE.relative_to(ROOT)}.']
    page(SHEET_D / 'index.html', title='GT23 rescale scope',
         ask='Choose which GT23 trials get rescaled moments and powers.',
         headline=f'Divisor established for {nc} of {total} GT23 trials',
         chips=chips_d,
         figures=[('fig1_coverage.png', 'How many trials per subject have an established divisor?', 'Grey: no calibrated estimate.', 'Trials per subject by divisor status'),
                  ('fig2_screen.png', 'Does a second estimator agree with each match?', 'Crosses dropped: under 10 stances, or nearer another mass. Open circles only in the largest option.', 'Second estimate against matched mass by stance count')],
         not_shown=['Which trials are near the band edge', 'Non-gait trials with another estimator', 'Why the divisors shifted'],
         reply='D-GT23-C04-1: A, B, C or defer', details=details_d, decision=decision)
    backlog = {'id': 'D-GT23-C04-1', 'task_id': 'GT23-C04',
               'question': ('Only some GT23 trials have a clearly identified divisor. Which GT23 trials should carry moments and powers rescaled to '
                            'the participant\'s own mass? Trials not rescaled keep kinematics and forces; their moments and powers are withheld.'),
               'options': [{'key': k, 'label': o[1], 'consequence': o[3]} for k, o in zip(keys, options)],
               'options_order': f'By GT23 trials released with kinetics: 0, {nb}, {nc}.',
               'recommended': 'B', 'confidence': 'medium', 'why': why,
               'check': ("Sheet, first figure: AB11's bar has no blue part, so none of its trials would get rescaled kinetics under B or C."),
               'cost_of_waiting': 'GT23 moments and powers stay out of any release; GT23 kinematics, forces and other datasets are unaffected.',
               'decide_before_recommendation': True, 'status': 'open'}
    (SHEET_D / 'decision.json').write_text(json.dumps(backlog, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'chips_v': chips_v, 'decision': backlog}, indent=1, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('stage', choices=['screen', 'sheets'])
    a = ap.parse_args()
    os.nice(max(0, 19 - os.nice(0)))
    stage_screen() if a.stage == 'screen' else build_sheets()


if __name__ == '__main__':
    main()
