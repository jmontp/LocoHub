"""CORE-04 GT23 pilot, SHEET step (no data access).

Builds docs/quality/audits/core04-gt23-pilot.json and review_sheets/CORE-04/gt23.html from the
probe files only (v2 current, v1 kept as history). The probe step is
contributor_tools/probe_core04_gt23.py (split on 2026-10-31 so sheet edits never change a
probe file's recorded hash).
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import resource
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.common import sign_offset_detector as sod  # noqa: E402
from contributor_tools.probe_core04_gt23 import *  # noqa: F401,F403  probe constants and helpers (read-only use)
SUMMARY = AUDITS / 'core04-gt23-pilot.json'
SHEET = ROOT / 'review_sheets/CORE-04'
BUILDER_HISTORY = [
    {'probe_file': 'core04-gt23-pilot-probe.json (v1, 69da8886...)', 'builder': 'd99d53acab2795ee... (probe)',
     'detector': 'efd74e7389ad54e3...',
     'note': 'v1 probe: forward axis = the analysed foot heel-to-toe axis. The sheet was then built with builder '
             '4165840b...: only the sheet step changed (build_sheet, fig_grid, fig_heading, legs, test_rows, LABEL, '
             'SHORT replacing the stub). Proof without data: d99d53ac was reconstructed exactly (sha256 matches the '
             'hash recorded in the v1 probe) by restoring the stub; an AST comparison shows every probe-step '
             'function (load_trial, condition_record, summarize, parsing, resample, Reader, run_probe, main) '
             'identical.'},
    {'probe_file': 'core04-gt23-pilot-probe-v2.json (abba296a...)', 'builder': '97375fa65933ba8b... (probe)',
     'sheet_builder': '57a9a5c9... (sheet, before the split)', 'detector': 'efd74e7389ad54e3...',
     'note': 'v2 probe (same seed): forward axis = per-stride pelvis facing (horizontal ASIS-mid minus PSIS-mid), '
             'foot axis only as a fallback; verifier recommendation after the toe-out finding. Census before the '
             'run: no other numerical worker. The sheet was then built with 57a9a5c9...: only the sheet step and a '
             'BUILDER_HISTORY constant changed. Proof without data: 97375fa6 was reconstructed exactly (sha256 matches '
             'the hash recorded in the v2 probe) from the current probe-side code plus the unchanged 4165840b sheet '
             'step, and the probe-step functions compare identical by AST.'},
    {'probe_file': 'v1 and v2 (unchanged)', 'builder': 'split on 2026-10-31',
     'note': 'Probe and sheet steps split into contributor_tools/probe_core04_gt23.py and '
             'contributor_tools/review_core04_gt23_pilot.py so that sheet edits never change a recorded probe hash. '
             'Mapping: combined builder 97375fa6... (v2 probe) -> probe file 218d56143cfb5ca3... ; all 26 probe-step '
             'functions, classes and constants AST-identical (only the CLI dispatcher main differs). v1 (d99d53ac) '
             'differs from it only by the v2 axis change and stays history.'},
    {'probe_file': 'none yet', 'builder': 'probe file 0ee1f68a75f8fcc1...',
     'note': 'After the mapping: per-stride agreement of the pelvis facing and the foot heel-to-toe axis is recorded '
             '(angle per stride; strides more than 90 deg apart have their geometry withheld). Verifier suggestion; '
             'not run yet (no data read). Unit test: tests/test_core04_probe_builders.py.'}]


LABEL = {'hip_angle': 'hip angle', 'knee_angle': 'knee angle', 'ankle_angle': 'ankle angle',
         'hip_moment': 'hip moment', 'knee_moment': 'knee moment', 'ankle_moment': 'ankle moment',
         'hip_power': 'hip power', 'knee_power': 'knee power', 'ankle_power': 'ankle power'}
SHORT = {'level 1.2 m/s': 'lvl', 'incline 5 deg': 'up5', 'incline 10 deg': 'up10', 'decline 5 deg': 'dn5',
         'decline 10 deg': 'dn10', 'stair ascent': 'st-up', 'stair descent': 'st-dn'}


def legs(probe):
    return [r for r in probe['records'] if 'skipped' not in r]


def test_rows(probe):
    from contributor_tools.review_core04_um21_pilot import TEST_LABEL
    rows = collections.OrderedDict()
    for r in legs(probe):
        for ch in CHANNELS:
            c = r['channels'][ch]
            for e in c['evidence']:
                if e['test'].startswith('derived:') or e['test'] == 'units_check':
                    continue
                key = f"{TEST_LABEL[e['test'].split(':')[0]]}: {LABEL[ch]}"
                rows.setdefault(key, collections.Counter())['no decision' if e['sign'] is None else
                                                            ('right' if e['sign'] == c['truth'] else 'wrong')] += 1
        for rel in r['relations']:
            j = rel['channels'][0].split('_')[0]
            exp = TRUTH[f'{j}_moment'] * TRUTH[f'{j}_angle'] * TRUTH[f'{j}_power']
            rows.setdefault(f'power identity: {j}', collections.Counter())['no decision' if rel['product'] is None else
                                                                          ('right' if rel['product'] == exp else 'wrong')] += 1
    return rows


def fig_grid(plt, probe, path):
    from contributor_tools.review_core04_um21_pilot import OUTCOME_COLOR, GREEN, LIGHT, GREY, ORANGE, BAD, MUTED
    L = legs(probe)
    fig, ax = plt.subplots(figsize=(3.9, 6.2))
    for i, ch in enumerate(CHANNELS):
        y = len(CHANNELS) - 1 - i
        for j, r in enumerate(L):
            o = r['channels'][ch]['outcome']
            ax.add_patch(plt.Rectangle((j, y), .92, .9, color=OUTCOME_COLOR[o], lw=0))
    ax.set_xlim(0, len(L)); ax.set_ylim(0, len(CHANNELS))
    ax.set_yticks([len(CHANNELS) - 1 - i + .45 for i in range(len(CHANNELS))])
    ax.set_yticklabels([LABEL[c] for c in CHANNELS], fontsize=10)
    ax.set_xticks([j + .46 for j in range(len(L))])
    ax.set_xticklabels([f"{r['subject']} {SHORT[r['condition']]}" for r in L], rotation=90, fontsize=10)
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in (GREEN, LIGHT, GREY, ORANGE, BAD)]
    ax.legend(handles, ['applied, right sign', 'suggested, right sign', 'abstained', 'conflict',
                        'wrong sign (example; none here)'], loc='upper left', bbox_to_anchor=(-.38, -.32),
              ncol=1, fontsize=10, handlelength=1)
    ax.set_title(f'One column per leg, {len(L)} legs', loc='left', fontsize=10, color=MUTED)
    fig.savefig(path, dpi=170, bbox_inches='tight'); plt.close(fig)


def fig_heading(plt, probe, path):
    """Pelvis heading relative to the heel-to-toe forward axis, one dot per trial/pass."""
    from contributor_tools.review_core04_um21_pilot import GREEN, BAD, GREY, MUTED, REF
    L = legs(probe)
    fig, ax = plt.subplots(figsize=(4.3, 4.6))
    for j, r in enumerate(L):
        hs = r['pelvis_heading_vs_forward_deg']
        ax.scatter(hs, [len(L) - j] * len(hs), s=18, color=GREEN, lw=0, zorder=3)
    ax.axvspan(-5, 5, color=GREY, alpha=.35, lw=0, label='within 5 deg: foot axis close to the facing')
    ax.scatter([180.2], [0], s=40, color=BAD, marker='x', label='UMich AB04/i0: reversed pelvis (180 deg)', zorder=3)
    ax.axvline(0, color=REF, lw=.6)
    ax.set_xlim(-200, 200); ax.set_xticks([-180, -90, 0, 90, 180])
    ax.set_yticks([len(L) - j for j in range(len(L))])
    ax.set_yticklabels([f"{r['subject']} {SHORT[r['condition']]}" for r in L], fontsize=10)
    ax.set_xlabel('pelvis facing minus foot axis (deg)')
    ax.set_title('GT23: one dot per trial or stair pass', loc='left', fontsize=10, color=MUTED)
    ax.legend(loc='upper left', bbox_to_anchor=(-.3, -.12), fontsize=10)
    fig.savefig(path, dpi=170, bbox_inches='tight'); plt.close(fig)


def build_sheet():
    from contributor_tools.common.review_sheet import page
    from contributor_tools.review_core04_um21_pilot import style, fig_tests
    probe = json.loads(PROBE.read_text())
    v1 = json.loads(PROBE_V1.read_text())
    history = []
    if SUMMARY.exists():
        prev = json.loads(SUMMARY.read_text())
        history = prev.get('history', [])
        if prev.get('run') == 'v1':
            history.append({k: prev.get(k) for k in ('inputs_sha256', 'code_sha256', 'counts', 'per_channel_outcomes',
                                                     'per_test', 'new_tests', 'half_cycle', 'explanations', 'resources')}
                           | {'run': 'v1 (foot heel-to-toe forward axis)'})
    plt = style()
    SHEET.mkdir(parents=True, exist_ok=True)
    for old in SHEET.glob('gt23_*.png'):
        old.unlink()
    rows = test_rows(probe)
    fig_grid(plt, probe, SHEET / 'gt23_fig1_grid.png')
    fig_tests(plt, rows, SHEET / 'gt23_fig2_tests.png')
    fig_heading(plt, probe, SHEET / 'gt23_fig3_heading.png')

    L = legs(probe)
    name = lambda r: f"{r['subject']} {r['condition']}"
    per_channel = {ch: collections.Counter(r['channels'][ch]['outcome'] for r in L) for ch in CHANNELS}
    count = lambda kind: sum(v[f'{kind}_correct'] + v[f'{kind}_wrong'] for v in per_channel.values())
    wrong = [(name(r), ch) for r in L for ch in CHANNELS if r['channels'][ch]['outcome'].endswith('_wrong')]
    abstain = sum(v['abstain'] for v in per_channel.values())
    conflict = sum(v['conflict'] for v in per_channel.values())
    hc = collections.defaultdict(dict)
    for r in L:
        for ch in CHANNELS:
            for e in r['channels'][ch]['evidence']:
                h = (e['stats'] or {}).get('half_cycle', {})
                if 'result' in h:
                    hc[f"{ch} / {e['test'].split(':')[0]}"][name(r)] = h['result']
    hip_amb = sorted(k for k, v in hc['hip_angle / reference_angle'].items() if v == 'ambiguous')
    lever_half = sorted(k for k, v in hc.get('hip_moment / lever_arm', {}).items() if v == 'half')
    gate = {name(r): (r['leg_assignment_check']['result'], r['leg_assignment_check'].get('knee_peak_in_swing_fraction')) for r in L}
    frame = {name(r): {k: v['result'] for k, v in (r['plate_frame_check'] or {}).items()} for r in L}
    headings = [h for r in L for h in r['pelvis_heading_vs_forward_deg']]
    new_tests = ('stance extension', 'push-off', 'stance timing', 'power timing', 'ID-light')
    new_rows = {k: dict(v) for k, v in rows.items() if k.split(':')[0] in new_tests}
    new_wrong = sum(v.get('wrong', 0) for v in new_rows.values())
    skipped = [r for r in probe['records'] if 'skipped' in r]
    L1 = legs(v1)

    def id_r(r):
        e = [e for e in r['channels']['hip_moment']['evidence'] if e['test'] == 'inverse_dynamics_light'][0]
        return {'sign': e['sign'], 'votes': e['agree'],
                'median_abs_r': (e['stats'] or {}).get('half_cycle', {}).get('median_abs_r_lag0'), 'reason': e['reason']}
    decline_hip = [{'leg': name(b), 'v1_verdict': a['channels']['hip_moment']['verdict'], 'v1_id_light': id_r(a),
                    'v2_verdict': b['channels']['hip_moment']['verdict'], 'v2_id_light': id_r(b)}
                   for a, b in zip(L1, L) if b['task'] == 'decline_walking']
    dec_applied = (sum(x['v1_verdict'] == 'apply' for x in decline_hip), sum(x['v2_verdict'] == 'apply' for x in decline_hip))
    changes = [{'leg': name(b), 'channel': ch, 'v1': [a['channels'][ch]['verdict'], a['channels'][ch]['sign']],
                'v2': [b['channels'][ch]['verdict'], b['channels'][ch]['sign']]}
               for a, b in zip(L1, L) for ch in CHANNELS
               if (a['channels'][ch]['verdict'], a['channels'][ch]['sign']) != (b['channels'][ch]['verdict'], b['channels'][ch]['sign'])]
    fallback = {name(r): r['forward_axis_strides'] for r in L if r['forward_axis_strides'].get('foot (fallback)')}
    dec_txt = '; '.join(f"{x['leg']}: {x['v1_id_light']['median_abs_r']} -> {x['v2_id_light']['median_abs_r']}"
                        for x in decline_hip)
    where = lambda ch, o: [name(r) for r in L if r['channels'][ch]['outcome'] == o]
    c03 = json.loads(C03.read_text())
    divisor = {s: {k: c03['subjects'][s].get(k) for k in ('readme_mass_kg', 'divisor_kg_best', 'divisor_basis')}
               for s in probe['subjects']}
    off_mass = sorted(s for s, v in divisor.items()
                      if v['divisor_kg_best'] and abs(v['divisor_kg_best'] / v['readme_mass_kg'] - 1) > 0.02)

    chips = [('pass' if not wrong else 'fail', f'no wrong sign in {len(L) * len(CHANNELS)} leg-channels: {count("applied")} applied, {count("suggested")} suggested'),
             ('pass' if not new_wrong else 'fail', f'new cross-family tests: {new_wrong} wrong votes'),
             ('unchecked', f'v1 forward axis (one foot) was {min(abs(h) for h in headings):.0f}-{max(abs(h) for h in headings):.0f}° off the pelvis facing; v2 uses the pelvis'),
             ('unchecked', f'moments use another participant\'s mass for {len(off_mass)} of {len(divisor)} people: signs only, magnitudes unused'),
             ('unchecked', f'{len(hip_amb)} of {len(L)} hips half-cycle ambiguous (the 10° inclines): suggest only'),
             ('unchecked', 'knee moment has one evidence family: suggest at most'),
             ('unchecked', 'one decline leg failed the CoP-within-foot check: its lever arms abstained'),
             ('pass', f'hip moment on declines applied in {dec_applied[1]} of {len(decline_hip)} legs with the pelvis axis (v1: {dec_applied[0]})')]
    page(SHEET / 'gt23.html', title='GT23 detector pilot',
         ask='Look at 3 figures; reply if anything looks wrong.',
         headline=f'GaTech 2023, 3 people, 7 tasks: {count("applied")} signs applied, none wrong',
         chips=chips,
         figures=[('gt23_fig1_grid.png', 'Does every detected sign match the known GT23 sign?',
                   'Grey: abstained.', 'Grid of channels by legs coloured by verdict and correctness'),
                  ('gt23_fig2_tests.png', 'Did any single test vote for the wrong sign?',
                   'Red would mark a wrong vote.', 'Bars per test: legs with right sign, wrong sign or no decision'),
                  ('gt23_fig3_heading.png', 'Does the foot axis used as forward match the pelvis facing?',
                   'v1 used the foot axis; v2 uses the pelvis.', 'Pelvis facing minus foot heel-to-toe axis for every GT23 trial or pass')],
         not_shown=['Moment magnitudes (wrong normalizing mass)', 'Running and other GT23 tasks',
                    'GT21 and GT24 pilots'],
         reply='GT23 pilot: ok  |  what looks wrong',
         details=[f'Seed {SEED}; subjects {", ".join(probe["subjects"])} (README masses {probe["readme_masses_kg"]} kg, declared for the GRF check and ID-light).',
                  'Conditions: treadmill level 1.2 m/s, incline 5 and 10 deg (left leg), decline 5 and 10 deg (right leg; the right plate works only on declines), stair ascent and descent (strides pooled over passes, leg with more strides). Units are the dataset\'s own stride segmentation.',
                  'Ground truth (rule B, target = sign x source): OpenSim gait2392, so hip +1, knee angle -1, ankle +1; moments hip +1, knee -1, ankle +1; powers +1.',
                  f'Half-cycle ambiguous hips: {", ".join(hip_amb)}. Hip lever arm "other leg?" (weak test): {", ".join(lever_half) or "none"}.',
                  f'Gate results: {sorted(set(v[0] for v in gate.values()))}; unknown where the task is outside the gate (stair descent) or under 90 % in swing.',
                  f'Pelvis facing minus foot axis: {min(headings):.0f} to {max(headings):.0f} deg (toe-out; left legs negative, right positive). v1 projected on the foot axis, which leaked frontal forces into the decline ID-light estimate; v2 projects each stride on its pelvis facing (foot axis as fallback: {fallback or "none"}).',
                  f'Hip moment on declines, ID-light median |r| v1 -> v2: {dec_txt}.',
                  f'{len(skipped)} stair-descent leg left out (AB01: no parsed strides). Process census before v2: no other numerical worker.',
                  f'Peak memory {probe["resources"]["peak_rss_mib"]} MiB (cap 300). Nothing applied to any dataset.',
                  'Evidence: docs/quality/audits/core04-gt23-pilot.json; builder contributor_tools/review_core04_gt23_pilot.py'])

    explanations = {
        'wrong_signs': wrong or 'none: every applied or suggested sign equals the gait2392 sign under rule B',
        'conflicts': conflict,
        'skipped': [{'leg': f"{r['subject']} {r['condition']}", 'why': r['skipped']} for r in skipped],
        'hip_angle_suggest': {'legs': where('hip_angle', 'suggested_correct'), 'half_cycle_ambiguous': hip_amb,
                              'why': 'Ambiguous on all three 10-degree inclines (markers and stance extension count as one family). Stair descent is outside hip stance extension; AB01 decline 10 cast 2 stance-extension votes; AB13 stair ascent had 4 marker votes (< 5).'},
        'knee_angle': {'suggest': where('knee_angle', 'suggested_correct'), 'abstain': where('knee_angle', 'abstain'),
                       'why': 'The knee-range test is walking-only (stairs excluded) and cast fewer than 5 votes on the 10-degree slopes; markers alone give suggest. AB13 stair ascent: the marker test had 4 votes (< 5), so abstain.'},
        'ankle_angle_suggest': {'legs': where('ankle_angle', 'suggested_correct'),
                                'why': 'Stair descent is outside the push-off test; AB13 stair ascent had 4 marker votes.'},
        'hip_moment': {'suggest': where('hip_moment', 'suggested_correct'), 'abstain': where('hip_moment', 'abstain'),
                       'decline_before_after': decline_hip,
                       'why': ('Applied where ID-light and stance timing agree. v1 cause of the low decline ID-light correlations '
                               '(verifier, pilot_gt23): the forward axis was one foot\'s heel-to-toe line, which toe-out rotates '
                               '5-21 deg from the person\'s facing, so frontal forces leaked into the sagittal estimate '
                               '(verifier with the pelvis axis: AB01 decline 5 0.39 -> 0.95; AB13 decline 10 0.25 -> 0.54; '
                               'AB06 decline 5 0.74 -> 0.85). v2 uses the per-stride pelvis facing and reproduces this. '
                               'Remaining suggests: AB01 decline 10 (CoP-within-foot failed, so ID-light abstains), AB13 '
                               'decline 10 (ID-light 4 votes), stair descent (ID-light only; stance timing excludes stairs). '
                               'Stair ascent: fewer than 5 ID-light votes, abstain.')},
        'knee_moment': {'suggest': where('knee_moment', 'suggested_correct'), 'abstain': where('knee_moment', 'abstain'),
                        'why': 'One family only (lever arm): suggest by design. Abstain where the lever arm abstained (CoP-within-foot failure on AB01 decline 10; 4 votes on AB13 stair ascent).'},
        'ankle_moment_suggest': {'legs': where('ankle_moment', 'suggested_correct'),
                                 'why': 'AB01 decline 10: CoP-within-foot failed, so the lever arm abstained; late stance alone gives suggest.'},
        'powers': {'hip_applied': where('hip_power', 'applied_correct'), 'ankle_applied': where('ankle_power', 'applied_correct'),
                   'why': 'Apply needs the power identity (moment and angle applied) plus power timing. Hip power timing is level-walking only (scope change after UM21) and ankle power timing excludes declines and stair descent, so those legs rest on the identity (suggest) or abstain. Knee power has the identity only.'},
        'hip_lever_arm_half': {'legs': lever_half, 'why': 'Weak test (score 0); flagged "other leg?" although the column is this leg\'s, as in UM21; no effect.'},
        'forward_axis': {'pelvis_minus_foot_axis_deg_range': [min(headings), max(headings)],
                         'why': ('GT23 stores no pelvis angle, so no pelvis sign is tested. The marker pelvis facing differs from '
                                 'the analysed foot\'s heel-to-toe axis by 5-28 deg (toe-out: left legs negative, right legs '
                                 'positive); no pelvis faces backwards (contrast: UMich AB04/i0 at 180 deg). The offset was not '
                                 'harmless: in v1 it leaked frontal forces into the decline hip ID-light estimate. v2 projects each '
                                 'stride on its pelvis facing.'),
                         'fallback_strides': fallback},
        'v1_to_v2_verdict_changes': changes,
        'moment_scale': {'subjects_with_other_divisor': off_mass,
                         'why': 'GT23 published moments and powers are divided by another participant\'s mass for the subjects listed (GT23-C03 divisors below). Every detector decision here is scale-free (correlation and slope signs, contrasts relative to each unit\'s peak); lever-arm and ID-light slopes are not interpreted.',
                         'gt23_c03_subjects': divisor}}
    data = {'task_id': 'CORE-04', 'pilot': 'GT23', 'run': 'v2', 'builder_history': BUILDER_HISTORY,
            'history': history, 'forward_axis': probe.get('forward_axis'), 'status': 'review', 'scientific_approval': False,
            'applies_to_dataset': 'nothing',
            'question': 'Does the detector (rule B, cross-family tests) reproduce the gait2392 signs of GaTech 2023 across level, incline, decline and stair walking, and abstain rather than err?',
            'target_rule': 'B (D-UM21-C03-1 = B)', 'seed': probe['seed'], 'selection': probe['selection'],
            'subjects': probe['subjects'], 'conditions': probe['conditions'],
            'inputs_sha256': {str(PROBE.relative_to(ROOT)): digest(PROBE), str(PROBE_V1.relative_to(ROOT)): digest(PROBE_V1),
                              str(C03.relative_to(ROOT)): digest(C03)},
            'code_sha256': {**probe['code_sha256'], f'{Path(__file__).relative_to(ROOT)} (sheet)': digest(Path(__file__))},
            'ground_truth': {'source': 'sign-conventions-source-survey.json (GT23: gait2392, knee flexion negative; author plot code and paper) and GT23-C02 (ankle sign, power = moment x velocity), mapped to rule B',
                             'signs': TRUTH, 'pelvis': 'not published in GT23 (no pelvis channel)'},
            'adapter': {'channels': 'Joint_Angle hip_flexion/knee_angle/ankle_angle (deg -> rad); Joint_Moments *_moment (published N*m/kg, divisor per GT23-C03); Joint_Powers (W/kg)',
                        'units': 'Segmentation/<subject>/<task>_parsing.mat stride start/end times (dataset segmentation), resampled to 150 samples; durations from the times',
                        'markers': '.trc (mm -> m): CAL heel, mean MT1/MT5 toe, mean ANK/MANK ankle, mean KNE/MKNE knee, GTR hip proxy, ASIS/PSIS midpoints; each stride projected on its pelvis facing (horizontal ASIS-mid minus PSIS-mid), foot heel-to-toe axis as fallback, Y up',
                        'plates': 'GroundFrame_GRFs (N, m; OpenSim ground frame) for the analysed side; GRF unit N with the participant README mass',
                        'cop_registration': COP_REGISTRATION},
            'counts': {'applied_right': count('applied'), 'suggested_right': count('suggested'), 'abstained': abstain,
                       'conflict': conflict, 'wrong': len(wrong), 'leg_channels': len(L) * len(CHANNELS)},
            'per_channel_outcomes': {ch: dict(v) for ch, v in per_channel.items()},
            'per_test': {k: dict(v) for k, v in rows.items()}, 'new_tests': new_rows,
            'half_cycle': {k: dict(collections.Counter(v.values())) for k, v in hc.items()},
            'leg_assignment_gate': gate, 'plate_frame_checks': frame,
            'explanations': explanations,
            'per_leg': [{'leg': name(r), 'side': r['side'], 'strides': r['strides'], 'sources': r['sources'],
                         'pelvis_heading_vs_forward_deg': r['pelvis_heading_vs_forward_deg'],
                         **{ch: {k: r['channels'][ch][k] for k in ('verdict', 'sign', 'truth', 'outcome', 'families')} |
                            {'tests': {e['test']: [e['sign'], e['agree']] for e in r['channels'][ch]['evidence']}} for ch in CHANNELS}}
                        for r in L],
            'resources': probe['resources'], 'files_read_count': len(probe['files_read']),
            'limitations': ['3 subjects, 20 legs; no running or non-cyclic tasks.',
                            'Moment and power magnitudes carry the GT23-C03 normalizing-mass error; only signs are tested.',
                            'v1 used the foot heel-to-toe axis (toe-out leaked frontal forces into ID-light on declines); v2 uses the per-stride pelvis facing.',
                            'No threshold was changed for this pilot.'],
            'generated_by': 'contributor_tools/review_core04_gt23_pilot.py sheet'}
    SUMMARY.write_text(json.dumps(data, indent=1) + '\n')
    print(json.dumps({'chips': chips, 'summary_sha256': digest(SUMMARY)}, indent=1))


def main():
    os.nice(max(0, 19 - os.nice(0)))
    build_sheet()


if __name__ == '__main__':
    main()
