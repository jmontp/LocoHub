"""UM21-T02: decision sheets D-UM21-T02-1 (task clock) and D-UM21-T02-2 (AB01 i5/i10 copy).

Reads docs/quality/audits/um21-t02-clock-census.json, the midstance slope probe
report docs/quality/audits/um21-midstance-slope.json (D-UM21-T02-2 slope figure)
and, for the figure records only, one UM21 treadmill recording at a time from Streaming.mat (bounded,
read-only). Writes review_sheets/D-UM21-T02-1/ and review_sheets/D-UM21-T02-2/
(gitignored), each with index.html and decision.json (backlog schema). Launches nothing.

Neutral option order in both sheets: by strides released, fewest first; the
letters follow that order. Recommendations appear only inside the folded section.
Comparison records are drawn with SEED, never hand-picked:
- D-UM21-T02-1: from aligned records that have an a0x2 interval.
- D-UM21-T02-2: from the other AB01 treadmill recordings with an aligned clock.
AB01 i5 is held out of D-UM21-T02-1: its motion is a byte copy of AB01 i10, which
is decided separately in D-UM21-T02-2.
"""
import os
for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'ARROW_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'
import json
from pathlib import Path
import random
import resource
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.audit_um21_tread_pilot import belt_clock_alignment, matlab_text, set_address_space, sha256_file  # noqa: E402
from contributor_tools.common.review_sheet import page  # noqa: E402

CENSUS = ROOT / 'docs/quality/audits/um21-t02-clock-census.json'
SLOPE = ROOT / 'docs/quality/audits/um21-midstance-slope.json'
SLOPE_METHOD = 'belt_path'  # midstance foot path: no level offset; tolerance fixed blind (see the report)
SOURCE = ROOT / 'contributor_tools/conversion_scripts/Umich_2021/Streaming.mat'
SHEETS = ROOT / 'review_sheets'
SEED = 20261031
SUBJECT_RECORD = ('AB01', 'd10')  # the pilot record the review found misaligned
COPY, ORIGINAL = ('AB01', 'i5'), ('AB01', 'i10')
HELD_OUT = {COPY: 'held out pending D-UM21-T02-2; its motion is a copy of AB01 i10'}
WINDOW_LABEL = 'a0x2'
PAD_FRAMES = 600
GROUP_NAMES = [('jointAngles', 'joint angles'), ('jointForces', 'joint forces'), ('jointMoments', 'joint moments'),
               ('jointPowers', 'joint powers'), ('markers', 'markers'), ('forceplates', 'force plates')]
INK, MUTED, LINE, DOT, BAND, ALT = '#20252B', '#5b6672', '#24506F', '#c0392b', '#d5d9de', '#eda100'


def style(plt):
    plt.rcParams.update({'font.size': 10.5, 'axes.titlesize': 11, 'axes.spines.top': False,
                         'axes.spines.right': False, 'text.color': INK, 'axes.labelcolor': INK,
                         'axes.edgecolor': INK, 'xtick.color': INK, 'ytick.color': INK,
                         'legend.frameon': False, 'axes.linewidth': 0.6})


def name(key):
    return f'{key[0]} {key[1]}'


def series(handle, key):
    import numpy as np
    trial = handle[f'Streaming/{key[0]}/Tread/{key[1]}']
    events = trial['events']
    hs = {side: events[k][...].reshape(-1).astype(int) for side, k in (('left', 'LHS'), ('right', 'RHS'))}
    cuts = events['cutPoints'][...].astype(float)
    labels = [matlab_text(handle, r) for r in events['tasks'][...].reshape(-1)]
    cvel = events['VelProf/cvel'][...].reshape(-1).astype(float)
    markers = {n: trial[f'markers/{n}'][...].astype(float) for n in ('LHEE', 'LTOE', 'RHEE', 'RTOE')}
    result = belt_clock_alignment(hs, markers, cvel, cuts, labels, with_series=True)
    a, b = cuts[:, labels.index(WINDOW_LABEL)]
    return {'cvel': cvel, 'window': (int(a), int(b)), 'alignment': result}


def labels_of(handle, key):
    return [matlab_text(handle, r) for r in handle[f'Streaming/{key[0]}/Tread/{key[1]}/events/tasks'][...].reshape(-1)]


def save(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches='tight', pad_inches=0.05)


def overlay(path, data, title, extra_cvel=None):
    """Marker belt speed (dots) over the source belt command; extra_cvel = (label, cvel) adds a second command."""
    import numpy as np
    import matplotlib.pyplot as plt
    a, b = data['window']
    lo, hi = a - PAD_FRAMES, b + PAD_FRAMES
    fig, ax = plt.subplots(figsize=(4.5, 3.9))
    ax.axvspan(a / 100, b / 100, color=BAND, lw=0,
               label=f'source {WINDOW_LABEL} interval' if extra_cvel is None else f'{title} {WINDOW_LABEL} interval')
    idx = np.arange(max(lo, 1), min(hi, data['cvel'].size)) - 1
    ax.plot((idx + 1) / 100, data['cvel'][idx], color=LINE, lw=1.6,
            label='source belt command (cvel)' if extra_cvel is None else f'{title} belt command')
    if extra_cvel is not None:
        label, cvel = extra_cvel
        idx2 = np.arange(max(lo, 1), min(hi, cvel.size)) - 1
        ax.plot((idx2 + 1) / 100, cvel[idx2], color=ALT, lw=1.6, ls='--', label=f'{label} belt command')
    s = data['alignment']['series']
    frames, speed = np.array(s['joint_frame']), np.array(s['marker_belt_speed_m_s'])
    keep = (frames >= lo) & (frames <= hi)
    ax.plot(frames[keep] / 100, speed[keep], 'o', ms=3.5, color=DOT, label='belt speed from foot markers')
    ax.set_xlabel('time on the motion clock (s)')
    ax.set_ylabel('belt speed (m/s)')
    if extra_cvel is None:
        ax.set_title(title, loc='left')
    ax.legend(loc='upper left', bbox_to_anchor=(-0.02, -0.22), fontsize=10)
    save(fig, path)
    plt.close(fig)


def lag_plot(path, census):
    import matplotlib.pyplot as plt
    records = census['records']
    fig, ax = plt.subplots(figsize=(4.5, 3.4))
    ax.axhspan(-50, 50, color=BAND, lw=0, label='±50-frame tolerance')
    unevaluable = []
    for i, r in enumerate(records):
        lag = r['alignment']['best_lag']
        key = (r['subject'], r['condition'])
        if lag is None:
            ax.plot(i, 0, 'x', color=MUTED, ms=7, mew=1.6)
            unevaluable.append((i, key, r['alignment'].get('not_evaluable_detail') or ['not evaluable']))
        elif r['alignment']['passed']:
            ax.plot(i, lag, 'o', color=LINE, ms=3.5)
        else:
            ax.plot(i, lag, 'o', color=DOT, ms=5)
            note = ' (held out)' if key in HELD_OUT else ''
            ax.annotate(name(key) + note, (i, lag), xytext=(6, 0), textcoords='offset points', va='center',
                        fontsize=10, color=DOT)
    # Labels for unevaluable records sit below the band with leader lines, clear of the dots.
    for n, (i, key, detail) in enumerate(unevaluable):
        ax.annotate(f'{name(key)}: {", ".join(detail)}', (i, 0), xytext=(i, -220 - 110 * n), textcoords='data',
                    ha='right', fontsize=10, color=MUTED,
                    arrowprops={'arrowstyle': '-', 'color': MUTED, 'lw': 0.8, 'shrinkB': 5})
    ax.set_xlabel('recording (AB01 d10 … AB10 i5)')
    ax.set_ylabel('belt-clock offset (frames, 100 Hz)')
    ax.set_xticks([])
    ax.set_ylim(-520, 760)
    ax.legend(loc='center right', bbox_to_anchor=(1.0, 0.62), fontsize=10)
    save(fig, path)
    plt.close(fig)


def slope_plot(path, slope):
    """Midstance slope estimate per recording against its label; AB01 i5/i10 marked; band = blind tolerance."""
    import matplotlib.pyplot as plt
    tol = slope['tolerances'][SLOPE_METHOD]['tol_deg']
    subjects = sorted({r['subject'] for r in slope['records']})
    fig, ax = plt.subplots(figsize=(4.5, 3.9))
    labels = sorted({r['label_deg'] for r in slope['records']})
    for k, lab in enumerate(labels):
        ax.fill_between([lab - 1.2, lab + 1.2], lab - tol, lab + tol, color=BAND, lw=0,
                        label=f'label ± {tol:g}° (tolerance)' if k == 0 else None)
        ax.plot([lab - 1.2, lab + 1.2], [lab, lab], color=MUTED, lw=0.8)
    for r in slope['records']:
        key = (r['subject'], r['condition'])
        x = r['label_deg'] + (subjects.index(r['subject']) - (len(subjects) - 1) / 2) * 0.22
        y = r[SLOPE_METHOD]['median']
        if key in (COPY, ORIGINAL):
            ax.plot(x, y, 'o', ms=7, color=DOT, zorder=3, label='AB01 i5 and i10 (same motion)' if key == COPY else None)
            ax.annotate(name(key), (x, y), xytext=(-8, 10), textcoords='offset points', ha='right', fontsize=10, color=DOT)
        else:
            ax.plot(x, y, 'o', ms=3.5, color=LINE, zorder=2, label='other recordings' if key == ('AB02', 'd10') else None)
    ax.set_xticks(labels, [f'{v:+g}' if v else '0' for v in labels])
    ax.set_yticks(labels)
    ax.set_xlabel('labelled slope (deg)')
    ax.set_ylabel('midstance slope (deg)')
    ax.set_ylim(-13.5, 14.5)
    ax.legend(loc='upper left', bbox_to_anchor=(-0.02, -0.2), fontsize=10)
    save(fig, path)
    plt.close(fig)


def identical_plot(path, coverage_pairs):
    """coverage_pairs: [(label, color, {group: (identical, of)})] -> horizontal bars of % identical."""
    import numpy as np
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(4.5, 3.6))
    y = np.arange(len(GROUP_NAMES))
    height = 0.38
    for k, (label, color, cov) in enumerate(coverage_pairs):
        values = [100.0 * cov[g][0] / cov[g][1] for g, _ in GROUP_NAMES]
        bars = ax.barh(y + (k - 0.5) * height, values, height=height, color=color, label=label)
        for bar, (g, _) in zip(bars, GROUP_NAMES):
            if cov[g][0] == 0:  # a 0 % bar has no width: mark it so the contrast is visible
                ax.plot(0, bar.get_y() + bar.get_height() / 2, marker='s', ms=7, color=color, clip_on=False)
            ax.text(max(bar.get_width(), 2.5) + 2, bar.get_y() + bar.get_height() / 2, f'{cov[g][0]}/{cov[g][1]}',
                    va='center', fontsize=10, color=INK)
    ax.set_yticks(y, [n for _, n in GROUP_NAMES])
    ax.invert_yaxis()
    ax.set_xlim(0, 125)
    ax.set_xticks([0, 50, 100])
    ax.set_xlabel('datasets byte-identical (%)')
    ax.legend(loc='upper left', bbox_to_anchor=(-0.02, -0.2), fontsize=10)
    save(fig, path)
    plt.close(fig)


def pair_coverage(census, a, b):
    hashes = census['dataset_sha256_by_record']
    ha, hb = hashes[f'{a[0]}/{a[1]}'], hashes[f'{b[0]}/{b[1]}']
    out = {}
    for g, _ in GROUP_NAMES:
        names = [n for n in ha if n.split('/')[0] == g]
        out[g] = (sum(ha[n] == hb.get(n) for n in names), len(names))
    return out


def clock_sheet(census, handle, plt):
    out = SHEETS / 'D-UM21-T02-1'
    out.mkdir(parents=True, exist_ok=True)
    records = {(r['subject'], r['condition']): r for r in census['records']}
    candidates = sorted(k for k, r in records.items() if r['alignment']['passed'] and k not in HELD_OUT
                        and WINDOW_LABEL in labels_of(handle, k))
    control = random.Random(SEED).choice(candidates)
    overlay(out / 'ab01_d10_overlay.png', series(handle, SUBJECT_RECORD), name(SUBJECT_RECORD))
    overlay(out / 'control_overlay.png', series(handle, control), name(control))
    lag_plot(out / 'lags.png', census)

    scope = [r for k, r in records.items() if k not in HELD_OUT]
    aligned = [r for r in scope if r['alignment']['passed']]
    bad = [r for r in scope if not r['alignment']['passed']]
    measured = [r for r in bad if r['alignment']['best_lag'] is not None]
    unmeasured = [r for r in bad if r['alignment']['best_lag'] is None]
    all_published = sum(r['written_as_published'] for r in scope)
    released_a = sum(r['written_as_published'] for r in aligned)
    released_b = released_a + sum(r['written_realigned'] for r in measured)
    left_a = all_published - released_a
    left_b = sum(r['written_as_published'] for r in unmeasured)
    changed = sum(r['decisions_changed_by_realignment'] for r in measured)
    pairs_measured = sum(r['pairs'] for r in measured)
    names = lambda rs: ', '.join(name((r['subject'], r['condition'])) for r in rs)  # noqa: E731
    held = 'AB01 i5 is held out of every option pending its own decision; its motion is a copy of AB01 i10.'
    original_n = records[ORIGINAL]['written_as_published']  # AB01 i10 is aligned and counted in every option
    def if_dropped(n):
        return (f'If D-UM21-T02-2 is A, AB01 i10 also leaves and this count is {n - original_n:,} '
                f'({original_n} fewer).')
    options = [  # (strides released, label, left out, changes, backlog consequence)
        (released_a, 'Exclude recordings that fail the clock check',
         f'{len(bad)} recordings, {left_a:,} strides', 'No labels change',
         f'{len(bad)} recordings ({names(bad)}) leave the treadmill release: {left_a:,} strides; nothing is estimated. '
         f'{held} {if_dropped(released_a)} Reversible.'),
        (released_b, 'Re-align the measured recordings by their offset',
         f'{len(unmeasured)} recordings without a belt command (cvel), {left_b:,} strides',
         f'{changed} of {pairs_measured} task decisions move in {len(measured)} recordings',
         f'Task intervals of {names(measured)} are shifted by the marker-measured offset ({changed} of {pairs_measured} '
         f'decisions change); {names(unmeasured)} are left out ({left_b} strides). Adds a derived step that needs its '
         f'own review. {held} {if_dropped(released_b)} Reversible.'),
        (all_published, 'Keep the source task intervals as published', 'Nothing',
         f'{changed} of {pairs_measured} task decisions in {len(measured)} recordings stay off the motion',
         f'No change; {changed} of {pairs_measured} stride decisions in {names(measured)} stay mislabelled, and '
         f'{names(unmeasured)} stay unchecked. {held} {if_dropped(all_published)} Reversible.'),
    ]
    options.sort(key=lambda o: o[0])  # neutral order: strides released, fewest first
    assert options[0][1].startswith('Exclude'), 'recommendation text names A = exclude'
    keys = 'ABC'
    rows = [(f'{k} · {o[1]}', [o[2], f'{o[0]:,} ({o[0] - original_n:,} if D-UM21-T02-2 is A)', o[3]])
            for k, o in zip(keys, options)]
    rows.append(('Defer', ['—', '—', 'Treadmill pilot and release stay blocked']))
    why = ('The offsets are large and clearly measured (1.7–7 s), while the other recordings line up within 0.2 s. '
           'Excluding invents nothing; re-aligning would add a new estimate (median error 0.05–0.07 m/s) that '
           'needs its own review.')
    recommendation = f'A. {why} Confidence: medium. Pick the pilot from the aligned recordings.'
    decision = {'question': 'How should treadmill strides get task labels when the belt clock is off the motion?',
                'columns': ['Left out', 'Strides released', 'Changes'], 'rows': rows,
                'recommendation': recommendation,
                'footnote': 'Ordered by strides released. AB01 i5 held out (D-UM21-T02-2).'}
    lags = sorted(r['alignment']['best_lag'] for r in census['records'] if r['alignment']['passed'])
    measured_all = [r for r in census['records'] if not r['alignment']['passed'] and r['alignment']['best_lag'] is not None]
    unmeasured_detail = '; '.join(f"{name((r['subject'], r['condition']))}: {', '.join(r['alignment']['not_evaluable_detail'])}"
                                  for r in unmeasured)
    chips = [
        ('pass', f"{len(lags)} of {len(census['records'])} recordings line up ({lags[0]:+d} to {lags[-1]:+d} frames)"),
        ('fail', f"{len(measured_all)} recordings 1.7–7 s off: {names(measured_all)}"),
        ('unchecked', f'No clock evidence ({unmeasured_detail})'),
        ('pass', 'Stride counts match the release scope in all 50'),
        ('unchecked', 'Marker belt-speed estimate has its own small lag, not calibrated'),
    ]
    figures = [
        ('ab01_d10_overlay.png', 'Do AB01 d10 task intervals line up with the motion?',
         'Dots: belt speed from foot markers. Line: belt command.', 'AB01 d10 marker belt speed rises before the belt command'),
        ('control_overlay.png', f'Does a well-aligned recording ({name(control)}) look different?',
         f'Seeded random pick ({SEED}).', 'Marker belt speed follows the belt command'),
        ('lags.png', 'Which recordings are off?', 'Band: ±50-frame tolerance.', 'Offset per recording'),
    ]
    details = [f'Census: {CENSUS.relative_to(ROOT)} sha256 {sha256_file(CENSUS)}',
               f"Audit rule: contributor_tools/audit_um21_tread_pilot.py sha256 {census['audit_rule']['sha256']}",
               f'Builder: {Path(__file__).relative_to(ROOT)}; seed {SEED}; comparison record {control[0]}/{control[1]}',
               'Offsets: ' + '; '.join(f"{r['subject']}/{r['condition']} {r['alignment']['best_lag']:+d} frames, "
                                      f"lag-0 error {r['alignment']['err_lag0_m_s']:.3f} vs best {r['alignment']['err_best_m_s']:.3f} m/s"
                                      for r in measured_all),
               'Counts exclude AB01 i5 (held out). Re-alignment moves cutPoints into motion frames as cut − offset; nothing was converted.']
    page(out / 'index.html', title='D-UM21-T02-1 treadmill task clock',
         ask='D-UM21-T02-1: choose how treadmill strides get task labels.',
         headline='Task intervals run on the belt clock; 4 of 50 recordings are 1.7–7 s off the motion.',
         chips=chips, figures=figures,
         not_shown=['Drift within a recording.', 'Re-aligned label accuracy.', 'Signal values (unaffected).'],
         reply='D-UM21-T02-1: A, B, C or defer', details=details, decision=decision)
    backlog = {'id': 'D-UM21-T02-1', 'task_id': 'UM21-T02',
               'question': 'The UMich 2021 treadmill task intervals run on the belt-speed clock, which is 1.7 to 7 seconds '
                           'off the motion data in some recordings. How should treadmill strides get task labels?',
               'options': [{'key': k, 'label': o[1], 'consequence': o[4]} for k, o in zip(keys, options)],
               'options_order': 'By strides released in the 50-recording treadmill scope without AB01 i5: '
                                + ', '.join(f'{o[0]:,}' for o in options)
                                + f' (each {original_n} lower if D-UM21-T02-2 is A; the order is the same).',
               'recommended': 'A', 'confidence': 'medium', 'why': why,
               'check': 'review_sheets/D-UM21-T02-1/index.html, first figure: in AB01 d10 the red marker dots reach 1.2 m/s '
                        'well before the blue belt-command line does; in the second figure they sit on the line.',
               'cost_of_waiting': 'The UMich 2021 treadmill pilot and the 50-recording treadmill release stay blocked; '
                                  'other datasets are unaffected.',
               'decide_before_recommendation': True, 'status': 'open'}
    (out / 'decision.json').write_text(json.dumps(backlog, indent=2) + '\n')
    return {'control': control, 'options': [(o[1], o[0]) for o in options]}


def copy_sheet(census, handle, plt):
    import numpy as np
    out = SHEETS / 'D-UM21-T02-2'
    out.mkdir(parents=True, exist_ok=True)
    records = {(r['subject'], r['condition']): r for r in census['records']}
    others = sorted(k for k, r in records.items() if k[0] == COPY[0] and k not in (COPY, ORIGINAL)
                    and r['alignment']['passed'])
    contrast = random.Random(SEED).choice(others)
    contrast_text = ('the only other aligned AB01 recording' if len(others) == 1
                     else f'seeded pick ({SEED}) of the other aligned AB01 recordings')
    pair_key = ' = '.join(sorted(f'{k[0]}/{k[1]}' for k in (COPY, ORIGINAL)))
    coverage = census['duplicates']['pair_coverage'][pair_key]
    sharing = census['duplicates']['recording_pairs_sharing_any_signal_dataset']

    slope = json.loads(SLOPE.read_text())
    if slope.get('blind_run') or not (slope.get('blind_check') or {}).get('tolerances_equal'):
        raise SystemExit('slope report must be the unblinded run that reproduced the blind tolerances')
    slope_plot(out / 'slope.png', slope)
    by_record = {(r['subject'], r['condition']): r for r in slope['records']}
    shared = {m: by_record[ORIGINAL][m]['median'] for m in ('foot_pitch', 'belt_path', 'plate_force')}
    assert all(by_record[COPY][m]['median'] == v for m, v in shared.items()), 'copied pair must give equal slopes'
    lo, hi = min(shared.values()), max(shared.values())
    tol = slope['tolerances'][SLOPE_METHOD]['tol_deg']
    others_flagged = [r['record'].replace('/', ' ') for r in slope['records']
                      if r['flagged'][SLOPE_METHOD] and (r['subject'], r['condition']) not in (COPY, ORIGINAL)]
    identical_plot(out / 'identical.png', [
        (f'{name(COPY)} vs {name(ORIGINAL)}', DOT, pair_coverage(census, COPY, ORIGINAL)),
        (f'{name(contrast)} vs {name(ORIGINAL)}', LINE, pair_coverage(census, contrast, ORIGINAL)),
    ])
    shared_series = series(handle, ORIGINAL)  # markers and heel strikes are identical in both recordings
    copy_cvel = handle[f'Streaming/{COPY[0]}/Tread/{COPY[1]}/events/VelProf/cvel'][...].reshape(-1).astype(float)
    overlay(out / 'clock_owner.png', shared_series, name(ORIGINAL), extra_cvel=(name(COPY), copy_cvel))

    n_copy = records[COPY]['written_as_published']
    n_orig = records[ORIGINAL]['written_as_published']
    lag_copy, lag_orig = records[COPY]['alignment']['best_lag'], records[ORIGINAL]['alignment']['best_lag']
    signal_total = sum(v['of'] for g, v in coverage.items() if g != 'events')
    signal_same = sum(v['identical'] for g, v in coverage.items() if g != 'events')
    options = [  # (strides released from the two, label, left out, effect, backlog consequence)
        (0, f'Drop both {name(COPY)} and {name(ORIGINAL)}', f'{n_copy + n_orig} strides (both)',
         'Neither recording is released',
         f'Neither recording is released ({n_copy} + {n_orig} strides left out). Reversible.'),
        (n_orig, f'Drop {name(COPY)} only', f'{n_copy} strides ({name(COPY)})',
         f'Motion released once, as {name(ORIGINAL)}; {COPY[0]} has no 5° incline recording',
         f'{name(COPY)} is left out ({n_copy} strides); the motion is released once as {name(ORIGINAL)} '
         f'({n_orig} strides). {COPY[0]} then has no 5-degree incline recording, and assigning the motion to '
         f'{name(ORIGINAL)} rests on the measured slope ({lo:.1f}-{hi:.1f} degrees by three methods) and the marker '
         f'belt-speed fit ({lag_orig:+d} vs {lag_copy:+d} frames). Reversible.'),
        (n_orig + n_copy, 'Keep both as published', 'Nothing',
         f'Same strides released twice; {name(COPY)} labels follow D-UM21-T02-1',
         f'Both are released; the same motion appears twice, once labelled as a 5-degree incline whose task clock is '
         f'{abs(lag_copy) / 100:.1f} s off it ({name(COPY)} then falls under D-UM21-T02-1). Reversible before release.'),
    ]
    options.sort(key=lambda o: o[0])  # neutral order: strides released from the two recordings, fewest first
    assert options[1][1].startswith('Drop ' + name(COPY)), 'recommendation text names B = drop the copy only'
    keys = 'ABC'
    rows = [(f'{k} · {o[1]}', [o[2], f'{o[0]:,}', o[3]]) for k, o in zip(keys, options)]
    rows.append(('Defer', ['—', '—', f'Both stay out of the release ({n_copy + n_orig} strides)']))
    why = (f'Every signal and the heel strikes of {name(COPY)} equal {name(ORIGINAL)} byte for byte. The shared motion '
           f'was walked on a {lo:.1f}-{hi:.1f} degree slope (midstance foot path, heel-toe pitch and plate force), '
           f"and only {name(ORIGINAL)}'s task clock fits it ({lag_orig:+d} vs {lag_copy:+d} frames), so the motion "
           f'belongs to {name(ORIGINAL)}. Releasing both publishes the same strides twice; dropping both discards '
           'data whose labels check out.')
    recommendation = (f'B. {why} Confidence: medium; an author reply could show where the original '
                      f'{name(COPY)} data went.')
    decision = {'question': f'{name(COPY)} is a copy of {name(ORIGINAL)}. Which should be released?',
                'columns': ['Left out', f'Strides released (of {n_copy + n_orig})', 'Effect'], 'rows': rows,
                'recommendation': recommendation, 'footnote': 'Ordered by strides released.'}
    chips = [
        ('pass', f'{signal_same} of {signal_total} signal datasets byte-identical: angles, kinetics, markers, force plates'),
        ('pass', 'Heel strikes and stride times identical; task intervals differ'),
        ('pass', f'Only this pair, of all 50 recordings, shares any dataset' if len(sharing) == 1
         else f'{len(sharing)} recording pairs share datasets'),
        ('fail', f"Shared motion measured at {lo:.1f}-{hi:.1f}° slope: fits {name(ORIGINAL)}'s 10° label, not {name(COPY)}'s 5°"),
        ('pass', f'Midstance slope matches the label in the other 48 recordings (±{tol:g}°)' if not others_flagged
         else f"Other recordings off their label: {', '.join(others_flagged)}"),
        ('fail', f"{name(COPY)} task clock is {abs(lag_copy) / 100:.1f} s off the motion; {name(ORIGINAL)}'s fits"),
        ('unchecked', 'Why the copy exists (authors not asked)'),
    ]
    figures = [
        ('identical.png', f'Do {name(COPY)} and {name(ORIGINAL)} hold the same data?', f'Blue: {contrast_text}.',
         'All datasets identical for the copied pair, none for the contrast pair'),
        ('slope.png', 'Which slope was the shared motion walked on?', 'Band: tolerance fixed before viewing AB01.',
         'The AB01 i5 and i10 dots both sit at 10 degrees; every other recording sits on its label'),
        ('clock_owner.png', 'Whose task clock fits the shared motion?', 'Dots: belt speed from foot markers.',
         'Marker belt speed follows the i10 command, not the i5 one'),
    ]
    details = [f'Census: {CENSUS.relative_to(ROOT)} sha256 {sha256_file(CENSUS)}',
               f'Builder: {Path(__file__).relative_to(ROOT)}; seed {SEED}; contrast record {contrast[0]}/{contrast[1]}',
               'Per-group identity: ' + '; '.join(f"{g} {v['identical']}/{v['of']}" + (f" (differs: {', '.join(v['differs'])})" if v['differs'] else '')
                                                for g, v in sorted(coverage.items())),
               'Decoded task labels are identical; cutPoints and newID differ.',
               f"Slope: {SLOPE.relative_to(ROOT)} sha256 {sha256_file(SLOPE)}; probe {slope['probe']['path']} "
               f"sha256 {slope['probe']['sha256']}",
               'Shared AB01 i5/i10 motion, median [IQR] deg: ' + '; '.join(
                   f"{m} {by_record[ORIGINAL][m]['median']:.2f} [{by_record[ORIGINAL][m]['q25']:.2f}, {by_record[ORIGINAL][m]['q75']:.2f}]"
                   for m in ('belt_path', 'foot_pitch', 'plate_force')),
               'Tolerances (blind, from the other non-level recordings): ' + '; '.join(
                   f"{m} {t['tol_deg']:g}" for m, t in slope['tolerances'].items() if m in ('belt_path', 'foot_pitch', 'plate_force')),
               'Plate slope is not valid in AB03 and AB10 (3-9 % of body weight off the plates); markers agree with labels there.']
    page(out / 'index.html', title='D-UM21-T02-2 AB01 copied recording',
         ask='D-UM21-T02-2: choose which of the two copied recordings to release.',
         headline=f'{name(COPY)} is a byte-for-byte copy of {name(ORIGINAL)} except its task intervals.',
         chips=chips, figures=figures,
         not_shown=[f'Whether original {name(COPY)} data exists elsewhere.', 'Other near-copies (exact bytes only).'],
         reply='D-UM21-T02-2: A, B, C or defer', details=details, decision=decision)
    backlog = {'id': 'D-UM21-T02-2', 'task_id': 'UM21-T02',
               'question': "In the UMich 2021 treadmill data, participant AB01's 5-degree incline recording is a "
                           "byte-for-byte copy of the same participant's 10-degree incline recording, except for its "
                           'task intervals. Which of the two should be released?',
               'options': [{'key': k, 'label': o[1], 'consequence': o[4]} for k, o in zip(keys, options)],
               'options_order': 'By strides released from the two recordings: '
                                + ', '.join(f'{o[0]:,}' for o in options) + '.',
               'recommended': 'B', 'confidence': 'medium', 'why': why,
               'check': 'review_sheets/D-UM21-T02-2/index.html, second figure: the red AB01 i5 dot sits at 10 on the '
                        'vertical axis, while every other dot above the 5-degree label sits near 5.',
               'cost_of_waiting': f'{name(COPY)} and {name(ORIGINAL)} stay out of the treadmill release '
                                  f'({n_copy + n_orig} strides); nothing else waits.',
               'decide_before_recommendation': True, 'status': 'open'}
    (out / 'decision.json').write_text(json.dumps(backlog, indent=2) + '\n')
    return {'contrast': contrast, 'options': [(o[1], o[0]) for o in options]}


def main():
    set_address_space(768)
    import h5py
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    style(plt)
    census = json.loads(CENSUS.read_text())
    with h5py.File(SOURCE, 'r', rdcc_nbytes=1024**2) as handle:
        first = clock_sheet(census, handle, plt)
        second = copy_sheet(census, handle, plt)
    print(json.dumps({'D-UM21-T02-1': first, 'D-UM21-T02-2': second,
                      'peak_rss_mib': round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)}))


if __name__ == '__main__':
    main()
