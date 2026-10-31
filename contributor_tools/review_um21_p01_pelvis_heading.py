"""UM21-P01: decision sheet D-UM21-P01-1 (AB04 i0 pelvis computed facing backwards).

Reads only docs/quality/audits/um21-p01-pelvis-heading.json (the read-only census by
contributor_tools/audit_probes/2026_10_31/probe_um21_pelvis_heading.py). Opens no
source data and launches nothing. Writes review_sheets/D-UM21-P01-1/ (gitignored):
index.html, three one-panel PNGs and decision.json (backlog schema).

Neutral option order: by how many of the recording's pelvis-dependent columns
(pelvis tilt, thigh, shank) are released, fewest first; the letters follow that
order. The recommendation appears only inside the folded section.
Figures use the strides the census drew with its recorded seed (right side, fixed
here before plotting); the contrast recording is the census's seeded pick from the
normal recordings that stay in the release, never hand-picked.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.common.review_sheet import page  # noqa: E402

AUDIT = ROOT / 'docs/quality/audits/um21-p01-pelvis-heading.json'
OUT = ROOT / 'review_sheets' / 'D-UM21-P01-1'
SIDE = 'R'
INK, MUTED, GREY, RED, BLUE = '#20252B', '#5b6672', '#9aa3ad', '#c0392b', '#24506F'


def style(plt):
    plt.rcParams.update({'font.size': 10.5, 'axes.titlesize': 11, 'axes.spines.top': False,
                         'axes.spines.right': False, 'text.color': INK, 'axes.labelcolor': INK,
                         'axes.edgecolor': INK, 'xtick.color': INK, 'ytick.color': INK,
                         'legend.frameon': False, 'axes.linewidth': 0.6})


def name(record):
    return record.replace('/', ' ')


def save(fig, path):
    fig.savefig(path, dpi=160, bbox_inches='tight', pad_inches=0.05)


def fig_census(plt, audit, path):
    rows = audit['records']
    fig, ax = plt.subplots(figsize=(4.5, 3.3))
    for i, r in enumerate(rows):
        h = r['sides'][SIDE]['pelvis_rotation_circular_median_deg']
        bad = r['class'] != 'normal'
        ax.plot(i + 1, abs(h), 'o', ms=6 if bad else 4, color=RED if bad else GREY, zorder=3 if bad else 2)
        if bad:
            ax.annotate(name(r['record']), (i + 1, abs(h)), xytext=(8, -4), textcoords='offset points', color=RED)
    ax.axhline(90, color=INK, lw=0.8, ls='--')
    ax.set_xlim(0, len(rows) + 1)
    ax.set_ylim(-10, 200)
    ax.set_yticks([0, 90, 180])
    ax.set_xlabel('Treadmill recording (scope order)')
    ax.set_ylabel('Stored pelvis heading (deg)')
    save(fig, path)
    plt.close(fig)


def fig_stride(plt, pick, path):
    import numpy as np
    x = np.linspace(0, 100, 101)
    as_array = lambda k: np.array([np.nan if v is None else v for v in pick[k]], float)
    marker, stored = as_array('marker_tilt'), as_array('stored_tilt')
    fig, ax = plt.subplots(figsize=(4.5, 3.1))
    ax.plot(x, marker, color=INK, lw=2.2, label='Markers (independent)')
    ax.plot(x, stored, color=RED, lw=1.6, label='Stored pelvis tilt')
    ax.plot(x, -stored, color=BLUE, lw=1.2, ls='--', label='Stored, sign flipped')
    ax.set_xlabel('Stride (%)')
    ax.set_ylabel('Pelvis tilt, forward + (deg)')
    ax.legend(loc='best', fontsize=10)
    save(fig, path)
    plt.close(fig)


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    style(plt)
    audit = json.loads(AUDIT.read_text())
    if audit['blind_check'] is None or not audit['blind_check']['other_49_records_identical']:
        raise SystemExit('audit lacks a passing blind check')
    reversed_ = audit['summary']['classes']['reversed']
    unresolved = audit['summary']['classes']['unresolved']
    if reversed_ != ['AB04/i0'] or unresolved:
        raise SystemExit(f'sheet text assumes exactly AB04/i0 reversed; got {reversed_} / {unresolved}')
    rec = next(r for r in audit['records'] if r['record'] == 'AB04/i0')
    contrast = audit['seeded_picks']['contrast']
    picks = audit['seeded_picks']['curves']
    seed = audit['seeded_picks']['seed']
    OUT.mkdir(parents=True, exist_ok=True)
    fig_census(plt, audit, OUT / 'census.png')
    fig_stride(plt, picks['AB04/i0'][SIDE], OUT / 'ab04_i0_stride.png')
    fig_stride(plt, picks[contrast][SIDE], OUT / 'contrast_stride.png')

    S = rec['sides']
    j = rec['channel_judgement']
    normal = [r for r in audit['records'] if r['class'] == 'normal']
    pub, voting = audit['summary']['tilt_votes_normal_published_of_voting']
    lo, hi = audit['summary']['rotation_median_range_normal_deg']
    flips = {s: S[s]['tilt_votes']['flipped_sign'] for s in 'RL'}
    votes = {s: S[s]['tilt_votes']['strides_voting'] for s in 'RL'}
    thigh_wrong = sum(j[f'thigh_recipe_{s}']['strides'] - j[f'thigh_recipe_{s}']['published_pelvis_closer'] for s in 'RL')
    thigh_n = sum(j[f'thigh_recipe_{s}']['strides'] for s in 'RL')
    shank = {s: (j[f'shank_recipe_{s}']['strides'] - j[f'shank_recipe_{s}']['published_pelvis_closer'], j[f'shank_recipe_{s}']['strides'])
             for s in 'RL'}
    obl_flip = sum(j[f'pelvis_obliquity_{s}']['strides'] - j[f'pelvis_obliquity_{s}']['agree_strides'] for s in 'RL')
    rot_same = sum(j[f'pelvis_rotation_{s}']['agree_strides'] for s in 'RL')
    n228 = sum(j[f'pelvis_obliquity_{s}']['strides'] for s in 'RL')
    hip_ok = {c: sum(j[f'{c}_{s}']['agree_strides'] for s in 'RL') for c in ('hip_flexion', 'hip_adduction')}
    hip_n = {c: sum(j[f'{c}_{s}']['strides'] for s in 'RL') for c in ('hip_flexion', 'hip_adduction')}
    rot_rel = [audit['expected_signs'][f'hip_rotation_{s}']['reliability'] for s in 'RL']
    stray = [(r['record'], s, r['sides'][s]['tilt_votes']['flipped_sign']) for r in normal for s in 'RL'
             if r['sides'][s]['tilt_votes']['flipped_sign']]
    n_strides = rec['scope_observations']
    err = {k: [S[s]['tilt_error_median_deg'][k] for s in 'RL'] for k in ('published', 'flipped')}
    normal_err = [r['sides'][s]['tilt_error_median_deg']['published'] for r in normal for s in 'RL']

    chips = [
        ('pass', f'{len(normal)} of 50 recordings face forward: heading {lo:+.1f} to {hi:+.1f}°, '
                 f'stored tilt sign matches markers in {pub:,} of {voting:,} strides'),
        ('fail', f'AB04 i0 faces backward: heading 180°, markers match the flipped tilt in '
                 f'{flips["R"]}/{votes["R"]} right and {flips["L"]}/{votes["L"]} left strides'),
        ('fail', f'AB04 i0 thigh from the release recipe is closer with flipped tilt in {thigh_wrong} of {thigh_n} strides'),
        ('pass', f'Matches a lab frame turned 180°: obliquity flipped in {obl_flip}/{n228}, rotation sign kept in {rot_same}/{n228}'),
        ('pass', f'AB04 i0 hip flexion and adduction unaffected ({hip_ok["hip_flexion"]}/{hip_n["hip_flexion"]} '
                 f'and {hip_ok["hip_adduction"]}/{hip_n["hip_adduction"]} strides match markers)'),
        ('unchecked', f'AB04 i0 shank: test too weak at this small tilt ({shank["R"][0]}/{shank["R"][1]} right, '
                      f'{shank["L"][0]}/{shank["L"][1]} left closer with flipped tilt)'),
        ('unchecked', f'Hip rotation: marker estimate agrees in only {min(rot_rel):.0%}–{max(rot_rel):.0%} of normal strides'),
        ('unchecked', f'{sum(x[2] for x in stray)} isolated strides in {len({x[0] for x in stray})} other recordings '
                      'voted flipped; not investigated'),
    ]
    figures = [
        ('census.png', 'Which recordings have the pelvis computed facing backwards?',
         'Dashed: 90° rule.', 'Stored pelvis heading per recording; one at 180 degrees'),
        ('ab04_i0_stride.png', 'Does the stored pelvis tilt in AB04 i0 follow the markers?',
         'Seeded stride, right side.', 'Stored tilt mirrors the marker tilt'),
        ('contrast_stride.png', f'Does a normal recording ({name(contrast)}) look different?',
         f'Seeded random pick ({seed}).', 'Stored tilt lies on the marker tilt'),
    ]
    options = [
        ('A', 'Leave AB04 i0 out', 'none', f'{n_strides} strides leave; nothing changed. Reversible.'),
        ('B', 'Keep AB04 i0; leave its pelvis tilt, thigh and shank missing', 'hip, knee, ankle only',
         f'{n_strides} strides stay; 5 columns missing for this recording. Reversible.'),
        ('C', 'Keep AB04 i0 with pelvis tilt sign-flipped from marker evidence; thigh and shank from it', 'all columns',
         f'{n_strides} strides stay; one logged per-recording sign change. Reversible.'),
    ]
    decision = {'question': 'How should AB04 i0 pelvis-dependent columns be released?',
                'columns': ['Left out', 'Columns released', 'Consequence'],
                'rows': [(f'{k} · {label}', [{'A': f'all {n_strides} strides', 'B': 'pelvis tilt, thigh, shank', 'C': 'nothing'}[k], cols, cons])
                         for k, label, cols, cons in options],
                'footnote': 'Ordered by how much is released. Defer: those columns stay out.',
                'recommendation': 'C, medium confidence. Flipping the sign is the exact re-expression for a lab frame turned '
                                  f'180°, and after flipping the stored tilt sits {err["flipped"][0]:.2f}° from the markers '
                                  f'(other recordings {min(normal_err):.2f}–{max(normal_err):.2f}°). B is the conservative fallback.'}
    details = [
        f'Audit: {AUDIT.relative_to(ROOT)}; probe {audit["probe"]["path"]} sha256 {audit["probe"]["sha256"]}',
        f'Builder: {Path(__file__).relative_to(ROOT)}; seed {seed}; contrast {contrast}; strides '
        f'AB04/i0 R {picks["AB04/i0"][SIDE]["frames_1based"]}, {contrast} R {picks[contrast][SIDE]["frames_1based"]}',
        'Rule fixed before AB04/i0 was examined; blind run (AB04/i0 withheld) reproduced exactly for the other 49 '
        f'(blind report sha256 {audit["blind_check"]["sha256"]}).',
        f'AB04/i0 heading R {S["R"]["pelvis_rotation_circular_median_deg"]}°, L {S["L"]["pelvis_rotation_circular_median_deg"]}°; '
        f'stored tilt median {S["R"]["pelvis_tilt_median_deg"]}° vs marker {S["R"]["marker_tilt_median_deg"]}°; '
        f'median |stored - marker| {err["published"]} vs |-stored - marker| {err["flipped"]} (R, L).',
        f'Stray flipped strides in normal recordings: {stray}.',
        'Not released but affected: AB04/i0 pelvis obliquity (sign) and rotation (+180°); foot progression R median '
        f'{S["R"]["stored_medians_deg"]["foot_progression"]}° and L in the alternate branch for '
        f'{S["L"]["foot_progression_alternate_branch_frames"]} frames.',
        'AB04 i0 is in the release scope (D-UM21-T02-1 = A does not exclude it). No correction was applied anywhere.',
    ]
    page(OUT / 'index.html', title='D-UM21-P01-1 AB04 i0 pelvis heading',
         ask='D-UM21-P01-1: choose how AB04 i0 pelvis-dependent columns are released.',
         headline='1 of 50 treadmill recordings (AB04 i0) has its pelvis computed facing backwards, flipping pelvis tilt.',
         chips=chips, figures=figures,
         not_shown=['Moments and powers.', 'Foot progression (not released).', 'Why Vicon reversed the heading.'],
         reply='D-UM21-P01-1: A, B, C or defer', details=details, decision=decision)
    backlog = {'id': 'D-UM21-P01-1', 'task_id': 'UM21-P01',
               'question': "In one UMich 2021 treadmill recording (AB04, level walking), Vicon computed the pelvis facing "
                           'backwards, so its stored pelvis tilt has the wrong sign, and so do the thigh and shank angles built '
                           'from it. How should that recording\'s pelvis-dependent columns be released?',
               'options': [{'key': k, 'label': label, 'consequence': cons} for k, label, _, cons in options],
               'options_order': 'By how much of the recording is released: nothing; everything except pelvis tilt, thigh '
                                'and shank; everything.',
               'recommended': 'C', 'confidence': 'medium',
               'why': 'A pelvis frame turned 180 degrees about vertical flips tilt and obliquity and shifts rotation by 180 '
                      'degrees exactly; the markers show all three in every stride, and the flipped tilt sits within '
                      f'{err["flipped"][0]:.2f} degrees of the markers, as in the other 49 recordings. Hip angles are unaffected. '
                      'B is the conservative fallback; A also drops hip, knee and ankle data that are unaffected.',
               'check': 'review_sheets/D-UM21-P01-1/index.html, second figure: the red stored tilt is the mirror image of '
                        'the black marker line and the dashed blue line lies on it; in the third figure red lies on black.',
               'cost_of_waiting': 'AB04 i0 pelvis tilt, thigh and shank cannot be released; the other 49 recordings and '
                                  'the AB04 i0 hip, knee and ankle columns are unaffected.',
               'decide_before_recommendation': True, 'status': 'open'}
    (OUT / 'decision.json').write_text(json.dumps(backlog, indent=2) + '\n')
    print(json.dumps({'contrast': contrast, 'seed': seed, 'out': str(OUT.relative_to(ROOT))}))


if __name__ == '__main__':
    main()
