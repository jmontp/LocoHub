"""GT23-C05: per trial, is the moment error after rescaling lower than the error of the published moments?

Reads only committed audits (no source data): docs/quality/audits/gt23-c04-trial-divisors.json (census, screen)
and, through it, the GT23-C03 rules. Writes docs/quality/audits/gt23-c05-rescale-error.json and the review sheet
review_sheets/D-GT23-C05-1/ (gitignored).

Stages (run one at a time):
  compute  per-trial before/after error table and summary -> audit JSON
  sheets   decision sheet built with contributor_tools/common/review_sheet.py from the audit JSON

Definitions (log errors, so a factor and its inverse count the same; percentages shown are exp(|log|) - 1):
  m      the participant's own README mass (force plates within 1 % in 12 of 12 subjects, GT23-C03).
  d      the unknown divisor the publisher used for this trial. Published per-kg value = N*m / d.
  original error  |ln(d / m)|     (published value / correct own-mass value = m / d)
  rescaled error  |ln(d_hat / d)| after multiplying by d_hat / m (rescaled value / correct = d_hat / d)
For each trial, the plausible divisors d are evaluated one by one ("scenarios"), and rescaling is
  lower      if the rescaled error is lower than the original error in every scenario,
  no change  if the two differ by less than 0.5 % in every scenario (factor ~1: the method picks the own mass, so
             the published value is kept; its error is unknown when another recorded mass is also plausible);
             'own_mass_only' when the own mass is the only plausible divisor (published value already correct
             under the recorded-mass hypothesis),
  worse      if it is never lower and in at least one scenario higher,
  mixed      if it is lower in some scenarios and higher in others (e.g. own mass and another mass plausible).
The 0.5 % tolerance is the C04 'same value' spread (values within 0.5 % count as one mass).

Plausible divisors:
  exact trials (local N*m re-run, GT23-C03/C04): one scenario, d = re-run slope; d_hat = the matched table mass.
  validated gait trials (C04 reliable gait family, >= 10 gait stances, ankle corr >= 0.98, lever estimate L):
    interval = L * exp(+/- k_family), k_family = max(C03 band 0.0488 log, largest |ln(second / lever)| measured
    in that family among the C04 screen trials); if the trial has its own second estimate S, the interval also
    covers S * exp(+/- 0.0488). Scenarios (primary, 'recorded-mass hypothesis'): every README table mass inside
    the interval (all 8 exact divisors are README table values). Check without that hypothesis: 401 log-spaced
    values across the interval ('continuous').
  not validated (non-gait family, curb, < 10 gait stances, ankle corr < 0.98, or no lever estimate): no estimator
    is calibrated for these; the same computation is recorded as indicative only, around L (or the loaded-sample
    estimate when L is missing) with the largest disagreement measured in any family (cutting) as half width.
Rescale methods ('policies'):
  T (primary)  exact divisor where known, else the README table mass nearest the lever estimate.
  E            exact divisor where known, else the lever estimate itself (force-plate estimate used directly).
Combined class (policy T): lower with confidence = lower under the recorded-mass hypothesis AND in the continuous
check (or no recorded mass in the interval and lower in the continuous check); lower if the divisor is a recorded
mass = lower only under the hypothesis.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
import sys

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
C04 = ROOT / 'docs/quality/audits/gt23-c04-trial-divisors.json'
OUT = ROOT / 'docs/quality/audits/gt23-c05-rescale-error.json'
SHEET = ROOT / 'review_sheets/D-GT23-C05-1'
N_GRID = 401

GROUPS = [('level walking', {'normal_walk'}),
          ('other walking', {'dynamic_walk', 'incline_walk', 'meander', 'obstacle_walk', 'side_shuffle', 'turn_and_step',
                             'walk_backward', 'weighted_walk'}),
          ('tire run, cutting', {'tire_run', 'cutting'}),
          ('stairs', {'stairs'}),
          ('curb', {'curb_up', 'curb_down'})]
CLASSES = ['lower_confident', 'lower_if_recorded_mass', 'own_mass_only', 'no_change', 'mixed', 'worse', 'not_validated', 'no_estimate']


def utc():
    return dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pct(x):
    return round(100 * (math.exp(abs(x)) - 1), 2)


def group_of(family):
    for name, fams in GROUPS:
        if family in fams:
            return name
    return 'non-gait'


def scenarios(d_hat, m, divisors):
    return [(d, abs(math.log(d / m)), abs(math.log(d_hat / d))) for d in divisors]


def classify(sc, tol):
    lower = sum(r < o - tol for _, o, r in sc)
    worse = sum(r > o + tol for _, o, r in sc)
    if lower == len(sc):
        return 'lower'
    if lower == 0 and worse == 0:
        return 'no_change'
    if lower == 0:
        return 'worse'
    if worse == 0:
        return 'lower_or_same'
    return 'mixed'


def grid(lo, hi):
    a, b = math.log(lo), math.log(hi)
    return [math.exp(a + (b - a) * i / (N_GRID - 1)) for i in range(N_GRID)]


def summarize(sc):
    return {'original_error_pct': [pct(min(o for _, o, _ in sc)), pct(max(o for _, o, _ in sc))],
            'rescaled_error_pct': [pct(min(r for _, _, r in sc)), pct(max(r for _, _, r in sc))]}


def evaluate(m, d_hat, lo, hi, table, tol):
    plaus = [v for v in table if lo <= v <= hi]
    out = {'divisor_kg': d_hat, 'factor': round(d_hat / m, 4)}
    if plaus:
        sc = scenarios(d_hat, m, plaus)
        out.update(class_recorded_mass=classify(sc, tol), **summarize(sc),
                   scenarios=[{'divisor_kg': d, 'original_pct': pct(o), 'rescaled_pct': pct(r)} for d, o, r in sc])
    else:
        out.update(class_recorded_mass=None)
    scc = scenarios(d_hat, m, grid(lo, hi))
    out['class_continuous'] = classify(scc, tol)
    out['continuous'] = summarize(scc)
    return out


def combine(ev):
    cm, cc = ev['class_recorded_mass'], ev['class_continuous']
    if cm is None:
        return 'lower_confident' if cc == 'lower' else ('mixed' if cc == 'mixed' else cc)
    if cm == 'lower' and cc == 'lower':
        return 'lower_confident'
    if cm in ('lower', 'lower_or_same'):
        return 'lower_if_recorded_mass'
    return cm


def compute():
    c04 = json.loads(C04.read_text())
    rules = c04['rules']
    band = rules['candidate_band_half_width_log']
    tol = rules['same_value_max_spread_log']
    gait = set(rules['reliable_families'])
    min_st = c04['screen']['rules']['min_gait_stances']
    table = sorted(set(c04['readme_masses_kg'].values()))
    owner = defaultdict(list)
    for s, v in c04['readme_masses_kg'].items():
        owner[v].append(s)
    fam = {(t['subject'], t['task']): t['family'] for t in c04['trials']}
    screen = {(r['subject'], r['task']): r for r in c04['screen']['trials']}
    fam_spread, fam_rows = defaultdict(float), defaultdict(list)
    for k, r in screen.items():
        if r.get('second_divisor_kg'):
            x = math.log(r['second_divisor_kg'] / r['census_lever_kg'])
            fam_spread[fam[k]] = max(fam_spread[fam[k]], abs(x))
            fam_rows[fam[k]].append(round(x, 4))
    k_ind = max(fam_spread.values())
    rows = []
    for t in c04['trials']:
        c = t['census']
        key = (t['subject'], t['task'])
        m = c['own_readme_mass_kg']
        L = c['lever_divisor_kg']
        scr = screen.get(key, {})
        S = scr.get('second_divisor_kg')
        stances = t.get('stances_total') or 0
        loaded = (t.get('loaded_sample_estimate') or {}).get('divisor_kg_walking_bias')
        row = {'subject': t['subject'], 'task': t['task'], 'family': t['family'], 'group': group_of(t['family']),
               'own_mass_kg': m, 'c04_census_class': c['cls'], 'c04_screened_class': scr.get('screened_class'),
               'c04_fragile': scr.get('fragile'), 'gait_stances': stances, 'lever_kg': L, 'second_kg': S,
               'loaded_sample_kg': loaded}
        if c['cls'] == 'exact':
            ex = c04['local_nm_rerun'][t['subject']]['exact']
            d, tv = ex['slope_kg'], ex['table_mass_kg']
            sc = scenarios(tv, m, [d])
            cl = classify(sc, tol)
            row.update(tier='exact', rerun_slope_kg=d, plausible_divisors_kg=[d], own_mass_plausible=abs(math.log(d / m)) <= tol,
                       policy_T={'divisor_kg': tv, 'factor': round(tv / m, 4), 'class_recorded_mass': cl,
                                 'class_continuous': cl, **summarize(sc)},
                       policy_E={'divisor_kg': tv, 'factor': round(tv / m, 4), 'class_recorded_mass': cl},
                       )
            row['class'] = 'lower_confident' if cl == 'lower' else ('own_mass_only' if cl == 'no_change' else cl)
            row['narrow_band_class_T'] = row['class']
            rows.append(row)
            continue
        reason = None
        if t['family'] not in gait:
            reason = 'curb family' if t['family'].startswith('curb') else 'non-gait family'
        elif L is None:
            reason = 'fewer than 4 stances (no lever estimate)'
        elif stances < min_st:
            reason = f'fewer than {min_st} gait stances'
        elif c.get('reason_code') == 'ankle corr < 0.98':
            reason = 'ankle corr < 0.98'
        if reason:
            est = L if L is not None else loaded
            row.update(tier='not_validated', reason=reason, **{'class': 'not_validated' if est else 'no_estimate'})
            if est:
                lo, hi = est * math.exp(-k_ind), est * math.exp(k_ind)
                d_t = min(table, key=lambda v: abs(math.log(v / est)))
                ev = evaluate(m, d_t, lo, hi, table, tol)
                ev.pop('scenarios', None)
                row['indicative'] = {'estimate_kg': est, 'estimate_source': 'lever' if L is not None else 'loaded-sample',
                                     'half_width_log': round(k_ind, 4), 'interval_kg': [round(lo, 2), round(hi, 2)],
                                     'own_mass_plausible': lo <= m <= hi, 'class': combine(ev), 'policy_T': ev}
            rows.append(row)
            continue
        k = max(band, fam_spread[t['family']])
        lo, hi = L * math.exp(-k), L * math.exp(k)
        if S:
            lo, hi = min(lo, S * math.exp(-band)), max(hi, S * math.exp(band))
        d_t = min(table, key=lambda v: abs(math.log(v / L)))
        ev_t = evaluate(m, d_t, lo, hi, table, tol)
        ev_e = evaluate(m, L, lo, hi, table, tol)
        ev_e.pop('scenarios', None)
        nlo, nhi = L * math.exp(-band), L * math.exp(band)
        narrow = evaluate(m, d_t, nlo, nhi, table, tol)
        row.update(tier='validated_gait', half_width_log=round(k, 4), interval_kg=[round(lo, 2), round(hi, 2)],
                   plausible_divisors_kg=[v for v in table if lo <= v <= hi],
                   plausible_owners={str(v): owner[v] for v in table if lo <= v <= hi},
                   own_mass_plausible=lo <= m <= hi, policy_T=ev_t, policy_E=ev_e,
                   narrow_band_class_T=combine(narrow))
        row['class'] = combine(ev_t)
        own_only = all(abs(math.log(v / m)) <= tol for v in row['plausible_divisors_kg']) and row['plausible_divisors_kg']
        if row['class'] == 'no_change' and own_only:
            row['class'] = 'own_mass_only'
        row['class_policy_E'] = combine(ev_e)
        rows.append(row)

    def count(sel, key='class'):
        return dict(Counter(r[key] for r in rows if sel(r)))
    by_group = {g: count(lambda r, g=g: r['group'] == g) for g in [x for x, _ in GROUPS] + ['non-gait']}
    by_subject = {s: count(lambda r, s=s: r['subject'] == s) for s in sorted(c04['readme_masses_kg'])}
    val = [r for r in rows if r['tier'] in ('exact', 'validated_gait')]
    lower = [r for r in val if r['class'] == 'lower_confident']
    lower_if = [r for r in val if r['class'] == 'lower_if_recorded_mass']
    mixed = [r for r in val if r['class'] == 'mixed']
    noch = [r for r in val if r['class'] == 'no_change']
    own_only = [r for r in val if r['class'] == 'own_mass_only']

    def rng(r, field):
        return r['policy_T'].get(field) or r['policy_T']['continuous'][field]

    def worst(rs, field):
        vals = [r['policy_T'][field][1] for r in rs if r['policy_T'].get(field)]
        vals_c = [r['policy_T']['continuous'][field][1] for r in rs if r['policy_T'].get('continuous')]
        return {'recorded_mass_max': max(vals) if vals else None, 'continuous_max': max(vals_c) if vals_c else None}
    nv = [r for r in rows if r['tier'] == 'not_validated']
    c04_sets = {'B_well_separated': {(r['subject'], r['task']) for r in rows if r['c04_census_class'] == 'exact' or
                                     (r['c04_screened_class'] == 'unique-estimate' and not r['c04_fragile'])},
                'C_all_matched': {(r['subject'], r['task']) for r in rows if r['c04_census_class'] == 'exact' or
                                  r['c04_screened_class'] == 'unique-estimate'}}
    cross = {k: dict(Counter(r['class'] for r in rows if (r['subject'], r['task']) in v)) for k, v in c04_sets.items()}
    summary = {
        'trials': len(rows),
        'by_class': count(lambda r: True),
        'by_group': by_group,
        'by_subject': by_subject,
        'validated_trials': len(val),
        'policy_E_by_class_validated': count(lambda r: r['tier'] == 'validated_gait', 'class_policy_E'),
        'narrow_band_by_class_validated_T': dict(Counter(r['narrow_band_class_T'] for r in val)),
        'not_validated_indicative': dict(Counter(r['indicative']['class'] for r in nv if r.get('indicative'))),
        'not_validated_reasons': dict(Counter(r['reason'] for r in rows if r['tier'] in ('not_validated',) or r['class'] == 'no_estimate')),
        'lower_confident_error_pct': {'original_min_over_trials': min(rng(r, 'original_error_pct')[0] for r in lower),
                                      'rescaled_worst': worst(lower, 'rescaled_error_pct')},
        'lower_if_recorded_mass_error_pct': {'rescaled_worst': worst(lower_if, 'rescaled_error_pct')},
        'mixed_error_pct': {'original_range': [min(rng(r, 'original_error_pct')[0] for r in mixed),
                                               max(rng(r, 'original_error_pct')[1] for r in mixed)],
                            'rescaled_worst': worst(mixed, 'rescaled_error_pct')},
        'lower_confident_rescaled_worst_median_pct': sorted(r['policy_T']['rescaled_error_pct'][1] for r in lower if r['policy_T'].get('rescaled_error_pct'))[len(lower) // 2],
        'no_change_published_error_pct_max': [min(r['policy_T']['original_error_pct'][1] for r in noch),
                                              max(r['policy_T']['original_error_pct'][1] for r in noch)],
        'own_mass_only_trials': [f"{r['subject']} {r['task']}" for r in own_only],
        'c04_options_cross_tab': cross,
        'lower_confident_trials': [f"{r['subject']} {r['task']}" for r in lower],
        'lower_if_recorded_mass_trials': [f"{r['subject']} {r['task']}" for r in lower_if],
        'mixed_trials': [f"{r['subject']} {r['task']}" for r in mixed],
        'no_change_trials': [f"{r['subject']} {r['task']}" for r in noch],
        'policy_E_worse_trials': [f"{r['subject']} {r['task']}" for r in val if r.get('class_policy_E') == 'worse'],
    }
    audit = {
        'task_id': 'GT23-C05', 'stage': 'rescale error comparison', 'scientific_approval': False, 'rescaling_applied': False,
        'question': ("José (D-GT23-C04-1, conditional): is the rescaled error lower than the original error? If so, rescale "
                     "everything; else get back to me."),
        'probe': {'path': str(HERE.relative_to(ROOT)), 'sha256': sha(HERE)},
        'inputs': {'c04_audit': {'path': str(C04.relative_to(ROOT)), 'sha256': sha(C04)}},
        'data_arrays_read': 0,
        'method': __doc__.split('Definitions', 1)[1].strip(),
        'parameters': {'band_half_width_log': band, 'equal_tolerance_log': tol, 'min_gait_stances': min_st,
                       'table_masses_kg': table, 'family_max_second_vs_lever_log': {k: round(v, 4) for k, v in sorted(fam_spread.items())},
                       'family_second_vs_lever_log_values': dict(sorted(fam_rows.items())),
                       'indicative_half_width_log': round(k_ind, 4), 'grid_points': N_GRID,
                       'lever_on_exact_trials': [{'subject': s, 'exact_kg': e, 'lever_kg': l, 'log_err': round(math.log(l / e), 4)}
                                                 for s, _, e, l, _ in c04['summary']['exact_lever_check']],
                       'second_estimator_calibration': c04['screen']['calibration'],
                       'evidence_for_recorded_mass_hypothesis': ('All 8 exact divisors are README table values (6 with 0.0-0.03 N*m residual; '
                                                                 'AB09 87.57 vs 87.6 and AB13 64.0 near-exact, residual 0.2-0.4 and 3.5-4.7 N*m); a random divisor would fall within 0.005 kg '
                                                                 'of a table value about 0.2 % of the time (GT23-C03 verifier). Not shown '
                                                                 'for non-level trials; AB09 dynamic_walk_1 and weighted_walk_1 read about 5 % '
                                                                 'above the nearest table mass.'),
                       'verifier_numbers_used': {'non_gait_split_half': '4.7 % (AB01 ball_toss_1, C04 verifier)',
                                                 'non_gait_estimator_disagreement': 'up to 7 % (AB02 poses_1, C04 verifier)',
                                                 'tire_run_cutting_second_low': '4.6-15.2 % (C04 verifier round 2)'}},
        'trials': rows,
        'summary': summary,
        'computed_at_utc': utc(),
    }
    OUT.write_text(json.dumps(audit, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({k: summary[k] for k in summary if not k.endswith('_trials')}, indent=1))


# ---------------------------------------------------------------- sheet
INK, MUTED, BLUE, LIGHT, ORANGE, GREY, RED = '#20252B', '#5b6672', '#2a78d6', '#8fbbe9', '#eb6834', '#9aa3ad', '#a8322d'
COLORS = {'lower_confident': BLUE, 'lower_if_recorded_mass': LIGHT, 'own_mass_only': '#1f7a4d', 'no_change': INK, 'mixed': ORANGE, 'worse': RED,
          'not_validated': GREY, 'no_estimate': '#d4d9de'}
LABELS = {'lower_confident': 'lower', 'lower_if_recorded_mass': 'lower if a recorded mass', 'own_mass_only': 'own mass, unchanged',
          'no_change': 'unchanged, error unknown',
          'mixed': 'could rise or fall', 'worse': 'higher', 'not_validated': 'no validated estimate',
          'no_estimate': 'no estimate'}


def style():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 10.5, 'axes.spines.top': False, 'axes.spines.right': False, 'text.color': INK,
                         'axes.labelcolor': INK, 'axes.edgecolor': INK, 'xtick.color': INK, 'ytick.color': INK,
                         'axes.linewidth': 0.6, 'legend.frameon': False, 'legend.fontsize': 10})
    return plt


def save(fig, path, dpi=170):
    import struct
    fig.savefig(path, dpi=dpi)
    with open(path, 'rb') as f:
        width = struct.unpack('>I', f.read(24)[16:20])[0]
    if width / dpi > 4.5 + 1e-6:
        raise ValueError(f'{path} is {width / dpi:.2f} in wide; limit 4.5 in')


def fig_scatter(plt, data, path):
    """Each validated trial: one point per plausible divisor (published error, rescaled error), joined by a line."""
    fig, ax = plt.subplots(figsize=(4.5, 4.6), layout='constrained')
    lim = max(65, 5 + max(pct(math.log(r['policy_T']['divisor_kg'] / r['own_mass_kg'])) for r in data['trials']
                          if r['tier'] in ('exact', 'validated_gait')))
    ax.fill_between([0, lim], [0, lim], [lim, lim], color=RED, alpha=.06, lw=0)
    ax.plot([0, lim], [0, lim], color=MUTED, lw=1, ls='--')
    ax.text(3, lim - 9, 'above the line:\nrescaling adds error', color=RED, fontsize=10)
    order = ['no_change', 'own_mass_only', 'lower_confident', 'lower_if_recorded_mass', 'mixed']
    for cl in order:
        for r in data['trials']:
            if r['class'] != cl or r['tier'] not in ('exact', 'validated_gait'):
                continue
            sc = r['policy_T'].get('scenarios')
            if not sc and r['tier'] != 'exact':   # no recorded mass in the interval: plot its two ends
                dh, m = r['policy_T']['divisor_kg'], r['own_mass_kg']
                sc = [{'original_pct': pct(math.log(d / m)), 'rescaled_pct': pct(math.log(dh / d))} for d in r['interval_kg']]
            if r['tier'] == 'exact':
                sc = [{'original_pct': r['policy_T']['original_error_pct'][0], 'rescaled_pct': r['policy_T']['rescaled_error_pct'][0]}]
            x = [s['original_pct'] for s in sc]
            y = [s['rescaled_pct'] for s in sc]
            ax.plot(x, y, '-', color=COLORS[cl], lw=.8, alpha=.6)
            ax.plot(x, y, 's' if r['tier'] == 'exact' else 'o', color=COLORS[cl], ms=4.5 if r['tier'] == 'exact' else 3.5, alpha=.85)
    ax.set_xlim(-1, lim)
    ax.set_ylim(-1, lim)
    ax.set_xlabel('published moment error (%)')
    ax.set_ylabel('error after rescaling (%)')
    for cl in order:
        ax.plot([], [], 'o', color=COLORS[cl], label=LABELS[cl])
    ax.plot([], [], 's', color=MUTED, label='exact divisor')
    fig.legend(loc='outside lower center', ncol=2, fontsize=10, handletextpad=.3, columnspacing=.8)
    save(fig, path)
    plt.close(fig)


def fig_groups(plt, data, path):
    """Trials per task group by class."""
    groups = [g for g, _ in GROUPS] + ['non-gait']
    fig, ax = plt.subplots(figsize=(4.5, 4.4), layout='constrained')
    for y, g in enumerate(groups):
        left = 0
        for cl in CLASSES:
            n = data['summary']['by_group'][g].get(cl, 0)
            if n:
                ax.barh(y, n, left=left, color=COLORS[cl], height=.7)
            left += n
        ax.text(left + 3, y, str(left), va='center', fontsize=10, color=MUTED)
    ax.set_yticks(range(len(groups)), groups)
    ax.invert_yaxis()
    ax.set_xlabel('GT23 trials')
    ax.set_xlim(0, 230)
    from matplotlib.patches import Patch
    present = [cl for cl in CLASSES if any(data['summary']['by_group'][g].get(cl) for g in groups)]
    fig.legend(handles=[Patch(color=COLORS[c], label=LABELS[c]) for c in present], loc='outside lower center', ncol=2,
               fontsize=10, handletextpad=.4, columnspacing=.8)
    save(fig, path)
    plt.close(fig)


def counts(data):
    s = data['summary']['by_class']
    keys = ['lower_confident', 'lower_if_recorded_mass', 'own_mass_only', 'no_change', 'mixed', 'not_validated', 'no_estimate']
    return {k: s.get(k, 0) for k in keys}


def decision_content(data):
    n = counts(data)
    sm = data['summary']
    total = sm['trials']
    worst_low = sm['lower_confident_error_pct']['rescaled_worst']['recorded_mass_max']
    med_low = sm['lower_confident_rescaled_worst_median_pct']
    worst_if = sm['lower_if_recorded_mass_error_pct']['rescaled_worst']['continuous_max']
    nc_hi = sm['no_change_published_error_pct_max'][1]
    a = n['lower_confident'] + n['own_mass_only']
    b = a + n['lower_if_recorded_mass'] + n['no_change']
    c = total - n['no_estimate']
    options = [
        ('strict', a, f'Rescale only where error falls in every plausible case ({a} trials)',
         f'{total - a} trials (moments and powers)',
         f'{n["lower_confident"]} trials rescaled (remaining error at most {worst_low:.0f} %, median {med_low:.0f} %, if the divisor is a '
         f'recorded mass) and {n["own_mass_only"]} kept whose only plausible divisor is the own mass. Other trials keep kinematics '
         f'and forces; their moments and powers are withheld. Reversible.'),
        ('not_worse', b, f'Also trials that improve only if the divisor is a recorded mass, or stay unchanged ({b} trials)',
         f'{total - b} trials (moments and powers)',
         f'As the previous option plus {n["lower_if_recorded_mass"]} trials whose error falls only if the divisor is a recorded mass '
         f'(else up to {worst_if:.0f} %), and {n["no_change"]} kept as published because the estimate is nearest the own mass, '
         f'though another mass is plausible (published error up to {nc_hi:.0f} %). Reversible.'),
        ('everything', c, f'Rescale every trial with an estimate ({c} trials)', f'{n["no_estimate"]} trials without any estimate',
         f'Also {n["mixed"]} walking trials where error could rise or fall and {n["not_validated"]} trials without a validated '
         f'estimator (non-gait, curb, short or low-correlation trials), so error rises in some trials by an unknown amount. Reversible.'),
    ]
    options.sort(key=lambda o: o[1])   # neutral order: GT23 trials released with kinetics
    return options


def build_sheet():
    from contributor_tools.common.review_sheet import page
    data = json.loads(OUT.read_text())
    sm = data['summary']
    s = sm['by_class']
    total = sm['trials']
    plt = style()
    SHEET.mkdir(parents=True, exist_ok=True)
    for old in SHEET.glob('*.png'):
        old.unlink()
    fig_scatter(plt, data, SHEET / 'fig1_errors.png')
    fig_groups(plt, data, SHEET / 'fig2_groups.png')
    options = decision_content(data)
    keys = 'ABC'
    rec = keys[[o[0] for o in options].index('strict')]
    n = counts(data)
    n_e_worse = len(sm['policy_E_worse_trials'])
    tc = data['parameters']['family_max_second_vs_lever_log']
    tc_pct = pct(max(tc['tire_run'], tc['cutting']))
    chips = [
        ('pass', f'Rescaled error lower in every plausible case: {n["lower_confident"]} trials'),
        ('pass', f'Own mass the only plausible divisor: {n["own_mass_only"]} trials'),
        ('fail', f'Not lower for everything: {n["mixed"]} walking trials could rise or fall'),
        ('fail', f'Rescaling by the raw force-plate estimate would add error in {n_e_worse} trials'),
        ('unchecked', f'{n["not_validated"] + n["no_estimate"]} trials (non-gait, curb, short): no validated estimator'),
        ('unchecked', f'{n["lower_if_recorded_mass"]} trials lower only if the divisor is a recorded mass'),
        ('unchecked', f'{n["no_change"]} trials unchanged by rescaling; their published error is unknown'),
        ('unchecked', f'Tire run and cutting: the two estimators differ by up to {tc_pct:.0f} %'),
    ]
    rows = [(f'{k} · {o[2]}', [o[3], o[4]]) for k, o in zip(keys, options)]
    rows.append(('Defer', ['All GT23 kinetics', 'GT23 moments and powers stay out of any release; kinematics, forces and other datasets unaffected.']))
    why = (f'Rescaling lowers the error in every plausible case only for {n["lower_confident"]} trials. In the others the own mass and '
           f'another mass are both plausible, the gain depends on the divisor being a recorded mass, or no estimator is validated, '
           f'so rescaling everything would raise the error in some trials.')
    decision = {'question': 'Which GT23 trials should carry moments and powers?',
                'columns': ['Left out', 'Consequence'], 'rows': rows,
                'recommendation': f'{rec}. {why} Confidence: medium.', 'footnote': 'Ordered by trials with kinetics.'}
    lc = sm['lower_confident_error_pct']
    details = [
        f'Classes over {total} trials (rescale to the recorded mass nearest the force-plate estimate, exact divisor where known): {s}.',
        f'By task group: {sm["by_group"]}.',
        f'Lower trials: published error at least {lc["original_min_over_trials"]} %; error after rescaling at most '
        f'{lc["rescaled_worst"]["recorded_mass_max"]} % if the divisor is a recorded mass, {lc["rescaled_worst"]["continuous_max"]} % otherwise.',
        f'Could rise or fall: published error {sm["mixed_error_pct"]["original_range"]} %, rescaled up to {sm["mixed_error_pct"]["rescaled_worst"]} %; the own mass and another recorded mass are both plausible.',
        f'Rescaling by the raw force-plate estimate instead: {sm["policy_E_by_class_validated"]} over the validated walking trials.',
        f'Only the C04 band (no family widening): {sm["narrow_band_by_class_validated_T"]}.',
        f'Not validated, indicative only (half width {data["parameters"]["indicative_half_width_log"]} log): {sm["not_validated_indicative"]}.',
        f'Previous decision options (trials by class): {sm["c04_options_cross_tab"]}.',
        f'Evidence: {OUT.relative_to(ROOT)}; builder {HERE.relative_to(ROOT)}. No data arrays read.',
    ]
    page(SHEET / 'index.html', title='GT23 rescale error',
         ask='Choose which GT23 trials carry moments and powers.',
         headline=f'Rescaling lowers moment error with confidence in {n["lower_confident"]} of {total} GT23 trials, not all',
         chips=chips,
         figures=[('fig1_errors.png', 'Is the error lower after rescaling?',
                   'Dots: plausible divisors, joined per trial. Factor errors: 37 % low counts as 59 %.', 'Published against rescaled error per trial'),
                  ('fig2_groups.png', 'Which task groups improve?', 'Grey: no validated estimator.', 'Trials per task group by class')],
         not_shown=['Non-gait exact reference', 'Hip moments separately', 'Why divisors changed'],
         reply='D-GT23-C05-1: A, B, C or defer', details=details, decision=decision)
    backlog = {'id': 'D-GT23-C05-1', 'task_id': 'GT23-C05',
               'question': ('Rescaling GT23 moments to each participant\'s own mass lowers the error in only some trials. Which GT23 '
                            'trials should carry moments and powers? Trials left out keep kinematics and forces; their moments and powers are withheld.'),
               'options': [{'key': k, 'label': o[2], 'consequence': o[4]} for k, o in zip(keys, options)],
               'options_order': 'By GT23 trials released with kinetics: ' + ', '.join(str(o[1]) for o in options) + '.',
               'recommended': rec, 'confidence': 'medium', 'why': why,
               'check': 'Sheet, second figure: the non-gait bar is all grey, so no non-gait trial gets kinetics under A or B.',
               'cost_of_waiting': 'GT23 moments and powers stay out of any release; GT23 kinematics, forces and other datasets are unaffected.',
               'decide_before_recommendation': True, 'status': 'open'}
    (SHEET / 'decision.json').write_text(json.dumps(backlog, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'chips': chips, 'decision': backlog}, indent=1, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('stage', choices=['compute', 'sheets'])
    a = ap.parse_args()
    compute() if a.stage == 'compute' else build_sheet()


if __name__ == '__main__':
    main()
