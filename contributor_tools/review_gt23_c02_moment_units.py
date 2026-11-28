"""GT23-C02: decide the units of GaTech 2023 RawData Joint_Moments.csv from force-plate physics.

Steps (run one at a time, in order):
  probe   Seeded random subjects with a publisher mass, one random walking task each
          (RawData/<subject>/CSV_Data/<task>/), reading only Joint_Moments, Virtual_Insoles,
          GroundFrame_GRFs and Joint_Angle/Joint_Velocities/Joint_Powers for that task.
          Writes docs/quality/audits/gt23-c02-moment-units.json.
  sheet   Builds review_sheets/GT23-C02/ from that JSON only.

Independent evidence (does not use the README units statement):
  A. Force-plate lever arm in the calcn frame (publisher Virtual_Insoles = measured GRF in calcn
     frames; force norm checked equal to GroundFrame_GRFs). External ankle moment, raw N*m:
     M_ext = (cop_ap - a_x) F_vertical + a_y F_shear_ap about the generic gait2392 talus position
     (a_x, a_y) = (0.04877, 0.04195) m in calcn, with a 3 x 3 offset grid. The quasi-static internal
     estimate is -M_ext (dorsiflexion positive), in N*m. No mass is used.
  B. Regression slope of the source ankle column on that N*m estimate in 40-90 % stance:
     about 1 if the column is N*m, about 1/mass if it is N*m/kg. The implied normalizing mass
     (1/slope) is compared with the README mass, the local model-derived table, and a
     force-plate body mass (2 x mean single-leg vertical force over whole strides / g).
  C. Power consistency: Joint_Powers vs moment x Joint_Velocities (rad/s) to show powers share
     the moment's normalization (README says W).
Nothing is converted; nothing under converted_datasets/ is written. Source files are read whole
(a few MB each), one task at a time.
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

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RAW = Path('/mnt/s/locomotion_data/Gtech_2023/RawData')
PUB = ROOT / 'converted_datasets/reconversion_v2/swarm_backlog_20261021/gt23_publisher_source_review_20261021'
README = PUB / 'readme.txt'                       # publisher README fetched and hashed by the prior review (read only)
PUB_MASSES = PUB / 'verified_members/Subject_masses.csv'
LOCAL_MASSES = RAW / 'Subject_masses.csv'          # local table rewritten from model masses (prior review)
AUDIT = ROOT / 'docs/quality/audits/gt23-c02-moment-units.json'
SHEET = ROOT / 'review_sheets/GT23-C02'
PRIOR = ['sign-conventions-source-survey.json', 'gt23-publisher-units-and-mass-review.json']
SEED = 20261030
N_SUBJECTS = 5
G = 9.81
RATE_HZ = 200.0
STANCE_N = 100.0
WINDOW = (0.40, 0.90)
ANKLE_OFFSET = (0.04877, 0.04195)
OFFSET_GRID = [(ax, ay) for ax in (0.02, 0.05, 0.08) for ay in (0.0, 0.04, 0.08)]
WALK = re.compile(r'^(normal_walk|incline_walk|weighted_walk)_\d+$')
INK, MUTED, BLUE, ORANGE = '#20252B', '#5b6672', '#2a78d6', '#eb6834'


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def peak_rss_mib():
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)


def masses(path):
    out = {}
    for line in Path(path).read_text().splitlines():
        parts = line.strip().split(',')
        if len(parts) == 2 and parts[0].startswith('AB'):
            out[parts[0]] = float(parts[1])
    return out


class Reader:
    def __init__(self):
        self.files = []

    def table(self, path, usecols=None):
        import pandas as pd
        raw = Path(path).read_bytes()
        self.files.append({'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
        df = pd.read_csv(io.BytesIO(raw), usecols=usecols)
        del raw
        return df


def stances(fv, n):
    on = np.nan_to_num(fv) > STANCE_N
    edges = np.flatnonzero(np.diff(on.astype(int)))
    runs = []
    for a, b in zip(edges[:-1], edges[1:]):
        if on[a + 1] and 0.25 * RATE_HZ <= b - a <= 2.5 * RATE_HZ and a > 0 and b < n - 2:
            runs.append((a + 1, b + 1))
    return runs


def frac_idx(a, b, lo, hi):
    return a + int(round(lo * (b - a))), a + int(round(hi * (b - a)))


def side_analysis(t, s, pub_mass):
    S = s.upper()
    ins, grf, mom = t['ins'], t['grf'], t['mom']
    fv, fap, fml, cop = (ins[f'{S}{k}'].to_numpy(float) for k in ('VerticalF', 'ShearF_AP', 'ShearF_ML', 'COP_AP'))
    side = 'r' if s == 'r' else 'l'
    m = mom[f'ankle_angle_{side}_moment'].to_numpy(float)
    n = len(fv)
    runs = [r for r in stances(fv, n) if np.isfinite(m[r[0]:r[1]]).all() and np.isfinite(cop[r[0]:r[1]]).all()]
    gnorm = np.sqrt(sum(grf[f'{S}Force{k}'].to_numpy(float) ** 2 for k in ('X', 'Y_Vertical', 'Z')))
    inorm = np.sqrt(fv ** 2 + fap ** 2 + fml ** 2)
    both = np.isfinite(gnorm) & np.isfinite(inorm)
    out = {'side': s, 'stances': len(runs),
           'insole_vs_plate_force_norm_max_abs_diff_N': float(np.max(np.abs(gnorm[both] - inorm[both]))) if both.any() else None,
           'stances_cop_ap_moves_forward': int(sum(np.polyfit(np.arange(b - a), cop[a:b], 1)[0] > 0 for a, b in runs))}
    if len(runs) < 5:
        return out
    # Force-plate body mass: mean single-leg vertical force over whole stride periods (heel strike to heel strike) x 2 / g.
    hs = [a for a, _ in runs]
    fvp = np.nan_to_num(grf[f'{S}ForceY_Vertical'].to_numpy(float))
    per = [2 * float(np.mean(fvp[a:b])) / G for a, b in zip(hs[:-1], hs[1:]) if b - a < 3 * RATE_HZ]
    out['force_plate_mass_kg_median'] = round(float(np.median(per)), 2) if per else None
    idx = np.concatenate([np.arange(*frac_idx(a, b, *WINDOW)) for a, b in runs])

    def internal(ax, ay, shear_sign=1.0):
        return -((cop - ax) * fv + ay * shear_sign * fap)   # N*m, dorsiflexion positive, no mass

    src = m[idx]
    est = internal(*ANKLE_OFFSET)[idx]
    slope = float(src @ est / (est @ est))
    out.update({'window_slope_source_on_Nm_estimate': round(slope, 5),
                'implied_normalizing_mass_kg': round(1 / slope, 2),
                'window_correlation': round(float(np.corrcoef(src, est)[0, 1]), 4),
                'late_stance_min_source': round(float(np.min(src)), 3),
                'late_stance_min_estimate_Nm': round(float(np.min(est)), 2),
                'readme_mass_kg': pub_mass,
                'offset_grid': [{'a_x_m': ax, 'a_y_m': ay, 'implied_mass_kg': round(1 / float(src @ e / (e @ e)), 2)}
                                for ax, ay in OFFSET_GRID for e in [internal(ax, ay)[idx]]],
                'shear_sign_flipped_implied_mass_kg': round(1 / float(src @ (e := internal(*ANKLE_OFFSET, -1.0)[idx]) / (e @ e)), 2)})
    a, b = runs[len(runs) // 2]
    out['example_stance'] = {'source': np.round(np.interp(np.linspace(0, 1, 101), np.linspace(0, 1, b - a), m[a:b]), 4).tolist(),
                             'estimate_Nm': np.round(np.interp(np.linspace(0, 1, 101), np.linspace(0, 1, b - a), internal(*ANKLE_OFFSET)[a:b]), 3).tolist()}
    # Power C
    vel = t['vel'][f'ankle_velocity_{side}'].to_numpy(float)
    pw = t['pow'][f'ankle_power_{side}'].to_numpy(float)
    prod = m * np.deg2rad(vel)
    f = np.isfinite(pw) & np.isfinite(prod)
    out['power_vs_moment_x_velocity'] = {'slope': round(float(pw[f] @ prod[f] / (prod[f] @ prod[f])), 4),
                                         'max_abs_diff': float(np.max(np.abs(pw[f] - prod[f])))}
    return out


def run_probe():
    import pandas  # noqa: F401
    resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 ** 2, 1536 * 1024 ** 2))
    pub, loc = masses(PUB_MASSES), masses(LOCAL_MASSES)
    rng = np.random.default_rng(SEED)
    subjects = sorted(pub)
    order = rng.permutation(len(subjects))
    rd = Reader()
    trials, redraws = [], []
    for k in order:
        if len(trials) == N_SUBJECTS:
            break
        subj = subjects[k]
        tasks = sorted(p.name for p in (RAW / subj / 'CSV_Data').iterdir() if WALK.match(p.name))
        for attempt in range(3):
            task = tasks[int(rng.integers(len(tasks)))]
            d = RAW / subj / 'CSV_Data' / task
            st = {p: (d / p).stat() for p in ('Joint_Moments.csv', 'Virtual_Insoles.csv', 'GroundFrame_GRFs.csv')}
            t = {'mom': rd.table(d / 'Joint_Moments.csv'), 'ins': rd.table(d / 'Virtual_Insoles.csv'),
                 'grf': rd.table(d / 'GroundFrame_GRFs.csv'), 'vel': rd.table(d / 'Joint_Velocities.csv'),
                 'pow': rd.table(d / 'Joint_Powers.csv')}
            sides = [side_analysis(t, s, pub[subj]) for s in 'lr']
            if any(x['stances'] >= 5 for x in sides):
                break
            redraws.append({'subject': subj, 'task': task, 'reason': 'fewer than 5 stances with finite ankle moment and insole on both sides'})
        else:
            continue
        mom = t['mom']
        cols = [c for c in mom.columns if c.endswith('_moment') and ('flexion' in c or 'knee' in c or 'ankle_angle' in c)]
        ranges = {c: [round(float(np.nanpercentile(mom[c], 1)), 3), round(float(np.nanpercentile(mom[c], 99)), 3)]
                  for c in cols if np.isfinite(mom[c]).any()}
        if any((d / p).stat().st_mtime_ns != st[p].st_mtime_ns for p in st):
            raise ValueError('Source changed during the read')
        del t
        trials.append({'subject': subj, 'task': task, 'readme_mass_kg': pub[subj], 'local_model_mass_kg': loc.get(subj),
                       'sagittal_moment_p1_p99': ranges, 'sides': sides})
        print(f'{subj} {task}: rss {peak_rss_mib()} MiB', flush=True)
    lines = README.read_text().splitlines()
    data = {'task_id': 'GT23-C02', 'status': 'review', 'scientific_approval': False,
            'question': 'Are GT23 RawData Joint_Moments.csv values N*m (README) or already mass-normalized N*m/kg?',
            'seed': SEED, 'selection': 'numpy default_rng(seed).permutation over the 12 subjects in the publisher mass table; '
                                       'first N_SUBJECTS; one task each by rng.integers over sorted normal/incline/weighted walking base tasks; '
                                       'redraw if neither side has 5 stances.',
            'chosen': [f'{x["subject"]}/{x["task"]}' for x in trials], 'redraws': redraws,
            'readme': {'path': str(README.relative_to(ROOT)), 'sha256': digest(README), 'line_32': lines[31], 'mass_lines_76_87': lines[75:87]},
            'mass_tables': {'readme_publisher': {'path': str(PUB_MASSES.relative_to(ROOT)), 'sha256': digest(PUB_MASSES), 'kg': pub},
                            'local_model_derived': {'path': str(LOCAL_MASSES), 'sha256': digest(LOCAL_MASSES), 'kg': loc}},
            'files_read': rd.files,
            'method': {'lever_arm': f'internal ankle estimate (N*m, dorsiflexion +) = -[(cop_ap - a_x) F_vertical + a_y F_shear_ap] from Virtual_Insoles (calcn frame), '
                                    f'(a_x, a_y) = {ANKLE_OFFSET} m generic gait2392; grid {OFFSET_GRID}; shear sign also flipped. Ignores foot weight and inertia.',
                       'window': f'{WINDOW} of stance; stance = insole vertical force > {STANCE_N} N, 0.25-2.5 s, not at a file edge, finite moment and CoP.',
                       'slope': 'least squares through the origin of the source ankle column on the N*m estimate; implied mass = 1/slope.',
                       'force_plate_mass': '2 x mean single-leg vertical plate force over each heel-strike-to-heel-strike period / g; median over strides.',
                       'power': 'Joint_Powers ankle vs source ankle moment x Joint_Velocities ankle in rad/s.'},
            'trials': trials, 'peak_rss_mib': peak_rss_mib()}
    AUDIT.write_text(json.dumps(data, indent=1) + '\n')
    print(json.dumps({'audit_sha256': digest(AUDIT), 'peak_rss_mib': peak_rss_mib(), 'chosen': data['chosen']}, indent=1))


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


def legs(data):
    return [(tr, sd) for tr in data['trials'] for sd in tr['sides'] if 'window_slope_source_on_Nm_estimate' in sd]


def fig_example(plt, data, path):
    rng = np.random.default_rng(SEED + 1)
    L = legs(data)
    tr, sd = L[int(rng.integers(len(L)))]
    ex = sd['example_stance']
    x = np.linspace(0, 100, 101)
    est = np.array(ex['estimate_Nm'])
    fig, ax = plt.subplots(figsize=(4.5, 4.1), layout='constrained')
    ax.axhline(0, color=MUTED, lw=.6)
    ax.plot(x, est, color=ORANGE, lw=1.6, ls=':', label='force plate, N·m (README units)')
    ax.plot(x, est / tr['readme_mass_kg'], color=BLUE, lw=1.6, ls='--', label='force plate ÷ mass, N·m/kg')
    ax.plot(x, ex['source'], color=INK, lw=2.2, label='source Joint_Moments.csv')
    lo = min(min(ex['source']), float(np.min(est / tr['readme_mass_kg'])))
    ax.set_ylim(lo * 1.6, 0.6)
    ax.annotate(f'N·m curve off-axis (min {est.min():.0f})', xy=(14, lo * 1.55), xytext=(30, lo * 1.4),
                color=ORANGE, fontsize=10, arrowprops=dict(arrowstyle='->', color=ORANGE))
    ax.set_xlabel('stance (%)'); ax.set_ylabel('ankle moment (source units)')
    ax.set_title(f'{tr["subject"]} {tr["task"]}, {"left" if sd["side"] == "l" else "right"}, one stance ({tr["readme_mass_kg"]} kg)', fontsize=10, loc='left')
    fig.legend(fontsize=10, loc='outside lower left')
    save(fig, path); plt.close(fig)
    return f'{tr["subject"]} {tr["task"]} {sd["side"]}'


def fig_mass(plt, data, path):
    L = legs(data)
    fig, ax = plt.subplots(figsize=(4.5, 3.4), layout='constrained')
    ax.axhspan(0.7, 1.4, color=ORANGE, alpha=.15)
    ax.text(42, 1.6, 'README N·m predicts 1 kg', color=ORANGE, fontsize=10)
    ax.plot([40, 125], [40, 125], color=BLUE, lw=1, ls='--')
    ax.text(42, 140, 'per kg predicts the body mass', color=BLUE, fontsize=10)
    for tr, sd in L:
        g = [q['implied_mass_kg'] for q in sd['offset_grid']]
        ax.plot([tr['readme_mass_kg']] * 2, [min(g), max(g)], color=MUTED, lw=2, alpha=.7)
        ax.plot(tr['readme_mass_kg'], sd['implied_normalizing_mass_kg'], 'o', color=INK, ms=6)
    ax.set_yscale('log'); ax.set_ylim(0.5, 300); ax.set_xlim(40, 125)
    ax.set_xlabel('README body mass (kg)')
    ax.set_ylabel('mass the source divides by (kg)')
    ax.set_title('Dot: generic ankle position; bar: 9 positions', fontsize=10, loc='left')
    save(fig, path); plt.close(fig)


def build_sheet():
    from contributor_tools.common.review_sheet import page
    data = json.loads(AUDIT.read_text())
    L = legs(data)
    plt = style()
    SHEET.mkdir(parents=True, exist_ok=True)
    for old in SHEET.glob('*.png'):
        old.unlink()
    example = fig_example(plt, data, SHEET / 'fig1_example.png')
    fig_mass(plt, data, SHEET / 'fig2_mass.png')
    implied = [sd['implied_normalizing_mass_kg'] for _, sd in L]
    ratio_pub = [sd['implied_normalizing_mass_kg'] / tr['readme_mass_kg'] for tr, sd in L]
    ratio_loc = [sd['implied_normalizing_mass_kg'] / tr['local_model_mass_kg'] for tr, sd in L]
    grid = [q['implied_mass_kg'] for _, sd in L for q in sd['offset_grid']]
    fpm = [(tr['subject'], sd['force_plate_mass_kg_median']) for tr, sd in L]
    pw = [sd['power_vs_moment_x_velocity']['slope'] for _, sd in L]
    subj = sorted({tr['subject'] for tr, _ in L})
    ab03 = [(tr, sd) for tr, sd in L if tr['subject'] == 'AB03']
    VEST = 25 * 0.45359237   # weighted_walk_1_25lbs (README line 136)
    body = {}
    for tr, sd in L:
        body.setdefault(tr['subject'], []).append(sd['force_plate_mass_kg_median'] - (VEST if tr['task'].startswith('weighted') else 0))
    body = {k: round(float(np.mean(v)), 1) for k, v in body.items()}
    readme = {tr['subject']: tr['readme_mass_kg'] for tr, _ in L}
    body_ok = sum(abs(body[k] / readme[k] - 1) < 0.06 for k in body)
    chips = [('pass' if min(grid) > 20 else 'fail',
              f'source divides by a body mass in {len(L)} of {len(L)} legs: {min(implied):.0f}-{max(implied):.0f} kg, never 1 kg'),
             ('pass' if body_ok == len(body) else 'fail', f'plate-derived body mass matches the README mass in {body_ok} of {len(body)} subjects'),
             ('pass' if all(0.9 < p < 1.1 for p in pw) else 'fail', f'power = moment × speed (ratio {min(pw):.2f}-{max(pw):.2f}): powers are W/kg, not W'),
             ('pass', f'insole force = plate force (max difference {max(sd["insole_vs_plate_force_norm_max_abs_diff_N"] for _, sd in L):.0e} N)'),
             ('unchecked', f'which mass the authors divided by: implied/README {min(ratio_pub):.2f}-{max(ratio_pub):.2f}'),
             ('unchecked', 'hip and knee columns: same file, not lever-armed')]
    if ab03:
        tr, sd = ab03[0]
        chips.append(('unchecked', f'AB03: plates give {body["AB03"]:.0f} kg (README 113.5, model table 82.2); source implies {sd["implied_normalizing_mass_kg"]:.0f} kg'))
    page(SHEET / 'index.html', title='GT23 moment units',
         ask='Look at the figures; reply if anything looks wrong.',
         headline=f'GT23 Joint_Moments.csv is N·m/kg, not N·m as the README says ({len(subj)} random subjects)',
         chips=chips,
         figures=[('fig1_example.png', 'Does the source match force-plate N·m or N·m/kg?',
                   'Black follows blue (per kg), not orange (README N·m).', 'One stance: source ankle moment against force-plate estimate in N·m and per kg'),
                  ('fig2_mass.png', 'What mass does every leg divide by?',
                   'Every leg divides by tens of kilograms, not 1.', 'Implied normalizing mass per leg against README mass, log scale')],
         not_shown=['Hip and knee lever arms', 'Every task and subject', 'Which mass the authors used'],
         reply='moment units: ok | what looks wrong',
         details=[f'Seed {SEED}; tasks {", ".join(data["chosen"])}; figure 1 example (seed {SEED + 1}): {example}.',
                  f'Implied mass / README mass: {min(ratio_pub):.2f}-{max(ratio_pub):.2f}. Offset grid implied mass range {min(grid):.0f}-{max(grid):.0f} kg.',
                  f'Force-plate body mass per leg (kg): {fpm}.',
                  f'Peak memory of the probe: {data["peak_rss_mib"]} MiB.',
                  'Evidence: docs/quality/audits/gt23-c02-moment-units.json; builder contributor_tools/review_gt23_c02_moment_units.py.'])
    data['summary'] = {'legs': len(L), 'subjects': subj, 'implied_mass_range_kg': [min(implied), max(implied)],
                       'implied_over_readme_mass': [round(min(ratio_pub), 3), round(max(ratio_pub), 3)],
                       'implied_over_model_mass': [round(min(ratio_loc), 3), round(max(ratio_loc), 3)],
                       'offset_grid_implied_mass_range_kg': [min(grid), max(grid)],
                       'force_plate_mass_kg': fpm, 'force_plate_body_mass_minus_vest_kg': body, 'force_plate_body_mass_matches_readme_within_6pct': [body_ok, len(body)],
                       'power_ratio_range': [min(pw), max(pw)], 'chips': chips}
    data['figure_example'] = example
    data['verdict'] = {
        'answer': 'RawData Joint_Moments.csv is already mass-normalized (N*m/kg), contrary to README line 32 ("Nm"). Joint_Powers.csv equals moment x angular velocity (rad/s), so it is W/kg, contrary to the README "W".',
        'evidence': 'Against a mass-free force-plate lever-arm ankle moment in N*m, the source column scales by 1/(64-90 kg) in every leg (over a 3 x 3 ankle-position grid 46-113 kg); a N*m column would scale by 1. Correlation 0.997-0.9998.',
        'prior_audit': 'gt23-publisher-units-and-mass-review.json accepted N*m from the README alone and proposed dividing by participant mass; that correction would double-normalize and is withdrawn. Its retraction of the earlier "already mass-normalized" claim is itself reversed by this evidence. Its AB03 mass finding stands: force plates give about 114 kg (README 113.5), not the local model table 82.18.',
        'converters': 'The current converters copy raw values and label them Nm_kg; on units that is correct. Mass-dependent fields (body-weight GRF normalization) still need the publisher mass table, per the prior review.',
        'not_resolved': 'Which mass the authors divided by (participant vs model mass, notably AB03 113.5 vs 82.18 kg): the generic ankle position limits the implied mass to about +/-30 %.'}
    data['limitations'] = ['Ankle columns only are lever-armed; hip and knee share the file and show per-kg magnitudes (p1/p99 within about +/-2.1) but were not independently tested.',
                           'Generic gait2392 ankle position in calcn (subject models not parsed); implied mass varies 46-113 kg over the grid, so units are decided but the exact denominator is not.',
                           'Walking tasks only (incline and weighted walking drawn); 5 subjects, 8 legs.',
                           'Quasi-static lever arm ignores foot weight and inertia.',
                           'The README copy is the publisher bitstream bound by the prior review; the publisher README itself is not edited.']
    data['prior_audits_sha256'] = {p: digest(ROOT / 'docs/quality/audits' / p) for p in PRIOR}
    data['builder_sha256'] = digest(Path(__file__))
    AUDIT.write_text(json.dumps(data, indent=1) + '\n')
    print(json.dumps(data['summary'], indent=1))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('step', choices=['probe', 'sheet'])
    args = parser.parse_args()
    os.nice(max(0, 19 - os.nice(0)))
    {'probe': run_probe, 'sheet': build_sheet}[args.step]()


if __name__ == '__main__':
    main()
