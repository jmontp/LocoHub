"""CORE-04 GT21 pilot, SHEET step (no data access).

Builds docs/quality/audits/core04-gt21-pilot.json and review_sheets/CORE-04/gt21.html from the probe
file only. The probe step is contributor_tools/probe_core04_gt21.py (separate files from the start, so
sheet edits never change the probe hash recorded in the probe output).
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import collections
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.probe_core04_gt21 import (AUDITS, COP_REGISTRATION, JOINT_CHANNELS, PROBE,  # noqa: E402
                                                 SAGITTAL_HEADING_DEG, SEED, TRUTH, digest)

SUMMARY = AUDITS / 'core04-gt21-pilot.json'
SHEET = ROOT / 'review_sheets/CORE-04'
CHANNELS = JOINT_CHANNELS
LABEL = {'hip_angle': 'hip angle', 'knee_angle': 'knee angle', 'ankle_angle': 'ankle angle',
         'hip_moment': 'hip moment', 'knee_moment': 'knee moment', 'ankle_moment': 'ankle moment',
         'hip_power': 'hip power', 'knee_power': 'knee power', 'ankle_power': 'ankle power'}
SHORT = {'level treadmill': 'tm', 'level overground': 'lvl', 'incline': 'up', 'decline': 'dn',
         'stair ascent': 'st-up', 'stair descent': 'st-dn'}
# Rejections explained after the probe ran, from a bounded read of the two Header columns by the
# independent verifier (CORE-04 verify, pilot_gt21 check 6). The probe's whole-recording rejection
# stands; only the explanation on the sheet changes. Unlisted rejections stay "cause not checked".
REJECTION_EXPLAINED = {
    'AB24/12_02_2018/ramp/ramp_6_l_01_02.mat': {
        'chip': 'its plate file starts 1 ms after the kinematics; dropping one sample would recover it',
        'detail': ('ik runs at 200 Hz from 53.935 s; fp runs at 1000 Hz on the exact ms grid but starts at 53.936 s, so '
                   'only the first kinematic sample (1 of 3975) has no plate sample. Dropping that one sample would '
                   'recover the recording; the probe rejected the whole recording (conservative).'),
        'source': 'CORE-04 verifier, GT21 pilot check 6 (bounded read of the ik and fp Header columns)'}}
BUILDER_HISTORY = [{'probe_file': 'core04-gt21-pilot-probe.json (v1)', 'probe_builder': 'contributor_tools/probe_core04_gt21.py',
                    'sheet_builder': 'contributor_tools/review_core04_gt21_pilot.py',
                    'note': 'Probe and sheet steps are separate files from the start. Before the recorded run: a one-subject '
                            'pilot of the same code (written outside the repository) found the stance-capture rule too strict '
                            '(the stride ends at the next heel strike, and on stairs plate contact starts before the source '
                            'heel strike), and the first full run stopped at the 280 MiB cap because importing the detector '
                            'through the package loaded pandas; both fixed, the one-subject pilot re-run (peak 195 MiB, no '
                            'wrong sign), then a full run (peak 221 MiB). That run showed the leg gate counting strides with '
                            'withheld force as "knee peak in swing"; the detector gate was fixed (units without stance '
                            'information do not vote; synthetic test) and the full run repeated with the same probe file '
                            'and seed. Repeat vs first full run: identical verdicts in all 648 leg-channels; gate pass -> '
                            'unknown in 5 legs (AB09 up L, AB18 lvl L, AB18 up L, AB24 up L, AB24 st-up R). The first '
                            'full run is not kept in the repository.'},
                   {'probe_file': 'core04-gt21-pilot-probe.json (v1, unchanged)', 'sheet_builder': 'edited 2026-10-31 (CORE-11)',
                    'note': 'Sheet step only, no data read: the rejected-recording chip now states the verified cause (plate '
                            'file starts 1 ms after the kinematics; dropping one sample would recover it) and figure 3 bars '
                            'are neutral instead of the wrong-sign red. Counts, verdicts and the probe file are unchanged.'}]


def legs(probe):
    return [r for r in probe['records'] if 'skipped' not in r]


def name(r):
    return f"{r['subject']} {SHORT[r['condition']]} {r['side'][0].upper()}"


def test_rows(probe):
    from contributor_tools.review_core04_um21_pilot import TEST_LABEL
    rows = collections.OrderedDict()
    for r in legs(probe):
        for ch in CHANNELS:
            c = r['channels'][ch]
            for e in c['evidence']:
                if e['test'].startswith('derived:') or e['test'] in ('units_check', 'documentation'):
                    continue
                k = f"{TEST_LABEL[e['test'].split(':')[0]]}: {LABEL[ch]}"
                rows.setdefault(k, collections.Counter())['no decision' if e['sign'] is None else
                                                          ('right' if e['sign'] == c['truth'] else 'wrong')] += 1
        for rel in r['relations']:
            j = rel['channels'][0].split('_')[0]
            exp = TRUTH[f'{j}_moment'] * TRUTH[f'{j}_angle'] * TRUTH[f'{j}_power']
            rows.setdefault(f'power identity: {j}', collections.Counter())['no decision' if rel['product'] is None else
                                                                          ('right' if rel['product'] == exp else 'wrong')] += 1
    return rows


def fig_grid(plt, probe, path):
    from contributor_tools.review_core04_um21_pilot import OUTCOME_COLOR, GREEN, LIGHT, GREY, BAD, MUTED
    L = legs(probe)
    fig, ax = plt.subplots(figsize=(4.0, 4.4))
    for i, ch in enumerate(CHANNELS):
        y = len(CHANNELS) - 1 - i
        for j, r in enumerate(L):
            ax.add_patch(plt.Rectangle((j, y), .9, .9, color=OUTCOME_COLOR[r['channels'][ch]['outcome']], lw=0))
    ax.set_xlim(0, len(L)); ax.set_ylim(0, len(CHANNELS))
    ax.set_yticks([len(CHANNELS) - 1 - i + .45 for i in range(len(CHANNELS))])
    ax.set_yticklabels([LABEL[c] for c in CHANNELS], fontsize=10)
    step = 12
    ax.set_xticks([j + .45 for j in range(0, len(L), step)])
    ax.set_xticklabels([name(L[j]) for j in range(0, len(L), step)], rotation=90, fontsize=10)
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in (GREEN, LIGHT, GREY, BAD)]
    ax.legend(handles, ['applied, right sign', 'suggested, right sign', 'abstained', 'wrong sign (none here)'],
              loc='upper left', bbox_to_anchor=(-.32, -.30), ncol=2, fontsize=10, handlelength=1)
    ax.set_title(f'{len(L)} legs, every {step}th labelled', loc='left', fontsize=10, color=MUTED)
    fig.savefig(path, dpi=170, bbox_inches='tight'); plt.close(fig)


def fig_heading(plt, probe, path):
    """Per-recording model heading (circular median of ik pelvis_rotation) against the sagittal band."""
    from contributor_tools.review_core04_um21_pilot import GREEN, MUTED
    h = np.array([r['model_heading_deg']['circular_median'] for r in probe['recordings'] if 'model_heading_deg' in r])
    fig, ax = plt.subplots(figsize=(4.4, 2.8))
    ax.axvspan(-SAGITTAL_HEADING_DEG, SAGITTAL_HEADING_DEG, color=GREEN, alpha=.25, lw=0)
    ax.text(0, 0.96, 'sagittal\n(|heading| < 20)', ha='center', va='top', fontsize=10, color=MUTED,
            transform=ax.get_xaxis_transform())
    # Neutral bars: red marks a wrong sign elsewhere on this sheet, and a heading outside the band is
    # not a wrong sign (verifier note, CORE-04 GT21 check 7).
    ax.hist(h, bins=np.arange(-180, 185, 10), color=MUTED, lw=0)
    ax.set_xlim(-180, 180); ax.set_xticks([-180, -90, 0, 90, 180])
    ax.set_xlabel('model heading per recording (deg)'); ax.set_ylabel('recordings')
    ax.set_title(f'{len(h)} recordings; pelvis tilt is sagittal only in the band', loc='left', fontsize=10, color=MUTED)
    fig.savefig(path, dpi=170, bbox_inches='tight'); plt.close(fig)


def rejected_chip(rejected):
    if not rejected:
        return 'every seeded recording passed the reader checks'
    why = [REJECTION_EXPLAINED.get(r['recording'], {}).get('chip', 'cause not checked') for r in rejected]
    if len(rejected) == 1:
        return f'1 recording left out: {why[0]}'
    return f'{len(rejected)} recordings left out: ' + '; '.join(why)


def build_sheet():
    from contributor_tools.common.review_sheet import page
    from contributor_tools.review_core04_um21_pilot import style, fig_tests
    probe = json.loads(PROBE.read_text())
    plt = style()
    SHEET.mkdir(parents=True, exist_ok=True)
    for old in SHEET.glob('gt21_*.png'):
        old.unlink()
    rows = test_rows(probe)
    fig_grid(plt, probe, SHEET / 'gt21_fig1_grid.png')
    fig_tests(plt, rows, SHEET / 'gt21_fig2_tests.png')
    fig_heading(plt, probe, SHEET / 'gt21_fig3_heading.png')

    L = legs(probe)
    skipped = [r for r in probe['records'] if 'skipped' in r]
    per = {ch: collections.Counter(r['channels'][ch]['outcome'] for r in L) for ch in CHANNELS}
    tot = collections.Counter()
    for v in per.values():
        tot.update(v)
    counts = {'applied_right': tot['applied_correct'], 'applied_wrong': tot['applied_wrong'],
              'suggested_right': tot['suggested_correct'], 'suggested_wrong': tot['suggested_wrong'],
              'conflict': tot['conflict'], 'abstained': tot['abstain'], 'leg_channels': len(L) * len(CHANNELS)}
    by_cond = {c: dict(collections.Counter(r['channels'][ch]['outcome'] for r in L if r['condition'] == c for ch in CHANNELS))
               for c in SHORT}
    wrong = counts['applied_wrong'] + counts['suggested_wrong']
    wrong_votes = sum(v.get('wrong', 0) for v in rows.values())
    wrong_vote_detail = [{'leg': name(r), 'channel': ch, 'test': e['test'], 'sign': e['sign'], 'agree': e['agree'],
                          'reason': e['reason'], 'verdict': r['channels'][ch]['verdict'], 'final_sign': r['channels'][ch]['sign']}
                         for r in L for ch in CHANNELS for e in r['channels'][ch]['evidence']
                         if e['sign'] is not None and e['sign'] != r['channels'][ch]['truth']
                         and not e['test'].startswith('derived:') and e['test'] not in ('units_check',)]
    hc = collections.defaultdict(collections.Counter)
    for r in L:
        for ch in CHANNELS:
            for e in r['channels'][ch]['evidence']:
                h = (e['stats'] or {}).get('half_cycle', {})
                if 'result' in h:
                    hc[f"{ch} / {e['test'].split(':')[0]}"][h['result']] += 1
    hc_tot = collections.Counter()
    for v in hc.values():
        hc_tot.update(v)
    fixed_timing = sum(1 for r in L for ch in CHANNELS if 'fixed_timing_shape' in (r['channels'][ch]['families'] or []))
    gate = collections.Counter((r['condition'], str((r['leg_assignment_check'] or {}).get('result'))) for r in L)
    gate_tot = collections.Counter(str((r['leg_assignment_check'] or {}).get('result')) for r in L)
    unit = collections.Counter(r['grf_unit_check'].get('result') for r in L)
    marker = collections.Counter(str((r['marker_checks'] or {}).get('result', 'not run')) for r in L)
    frame = collections.Counter((k, v['result']) for r in L for k, v in (r['plate_frame_check'] or {}).items()
                                if isinstance(v, dict))
    force = collections.Counter()
    for r in L:
        force.update(r['force_status_strides'])
    strides = sum(r['strides'] for r in L)
    captured = force['named plate'] + force['nearest-foot plates']
    recs = [r for r in probe['recordings'] if 'model_heading_deg' in r]
    sagittal = sum(r['pelvis_sagittal'] for r in recs)
    rejected = [r for r in probe['recordings'] if 'rejected' in r]
    where = lambda ch, o: [name(r) for r in L if r['channels'][ch]['outcome'] == o]
    n_subj = len(probe['subjects'])

    chips = [('pass' if not wrong else 'fail', f'no wrong sign applied or suggested in {len(L) * len(CHANNELS)} leg-channels'),
             ('pass' if not wrong_votes else 'unchecked', f'{wrong_votes} single-test votes for a wrong sign (all outvoted; see details)'
              if wrong_votes else 'no single test voted for a wrong sign'),
             ('fail' if gate_tot.get('fail', 0) else ('unchecked' if gate_tot.get('unknown', 0) + gate_tot.get('None', 0) else 'pass'),
              f'leg gate: {gate_tot.get("pass", 0)} pass, {gate_tot.get("fail", 0)} fail, '
              f'{gate_tot.get("unknown", 0) + gate_tot.get("None", 0)} not decided (stairs, ramps)'),
             ('unchecked', f'pelvis unchecked: model heading sagittal in {sagittal} of {len(recs)} recordings'),
             ('unchecked', f'half-cycle check ambiguous in {hc_tot.get("ambiguous", 0)} test votes; '
                           f'{hc_tot.get("half", 0)} half-cycle'),
             ('unchecked', f'plate captured the stance in {captured} of {strides} strides; the rest give no force tests'),
             ('unchecked', 'body mass unit unresolved: signs only'),
             ('unchecked' if rejected else 'pass', rejected_chip(rejected))]
    page(SHEET / 'gt21.html', title='GT21 detector pilot',
         ask='Look at 3 figures; reply if anything looks wrong.',
         headline=f'GaTech 2021, {n_subj} people, level, ramps, stairs: '
                  f'{"no wrong sign" if not wrong else f"{wrong} wrong signs"}; pelvis unchecked',
         chips=chips,
         figures=[('gt21_fig1_grid.png', 'Does every detected sign match the known GT21 sign?',
                   'Red would mark a wrong sign.', 'Grid of channels by legs coloured by verdict'),
                  ('gt21_fig2_tests.png', 'Did any single test vote for the wrong sign?',
                   'Red marks a wrong vote.', 'Bars per test: legs with right sign, wrong sign or no decision'),
                  ('gt21_fig3_heading.png', 'Is the model pelvis tilt sagittal in these recordings?',
                   'Outside the band, tilt is not sagittal.', 'Histogram of per-recording model heading with the sagittal band')],
         not_shown=['Pelvis and segment angles', 'Moment magnitudes (mass unit unresolved)',
                    'Offsets (model-zero angles used)'],
         reply='GT21 pilot: ok  |  what looks wrong',
         details=[f'Seed {SEED}; subjects {", ".join(probe["subjects"])} (of {len(probe["eligible_subjects"])} local with all four modes).',
                  'Conditions per subject and leg: treadmill level, overground level, ramp incline and decline, stair ascent and descent; '
                  'task per stride from the mode and the pelvis rise over run (no source labels: the conditions tables are not admitted by the reader).',
                  'Ground truth (rule B, target = sign x source, OpenSim gait2392 per GT21-C01): hip +1, knee angle -1, ankle +1; '
                  'moments hip +1, knee -1, ankle +1; powers +1.',
                  f'Pelvis: model heading (circular median of ik pelvis_rotation) within {SAGITTAL_HEADING_DEG:.0f} deg of 0 in '
                  f'{sagittal} of {len(recs)} recordings, so ik pelvis_tilt is not sagittal and was not tested (GT21-C01).',
                  'Angles: ik (model zero); ik_offset is not admitted by the reader. Same sign, different offset.',
                  f'Forces: {dict(force)}.',
                  f'Gates: leg assignment {dict(gate_tot)}; GRF unit {dict(unit)}; marker vertical order {dict(marker)}; plate frame {dict(frame)}.',
                  f'Half-cycle: {dict(hc_tot)}; {fixed_timing} leg-channels used the merged fixed-timing family.',
                  f'Leg-conditions left out for too few strides: {len(skipped)}. Rejected recordings (the next seeded one was read): '
                  f'{"; ".join(r["recording"] + " - " + r["rejected"] for r in rejected) or "none"}.',
                  *[f'{r["recording"]}: {REJECTION_EXPLAINED[r["recording"]]["detail"]} '
                    f'Source: {REJECTION_EXPLAINED[r["recording"]]["source"]}.'
                    for r in rejected if r['recording'] in REJECTION_EXPLAINED],
                  f'Peak memory {probe["resources"]["peak_rss_mib"]} MiB (cap 300). Nothing applied to any dataset.',
                  'Evidence: docs/quality/audits/core04-gt21-pilot.json; builders contributor_tools/probe_core04_gt21.py and review_core04_gt21_pilot.py'])

    data = {'task_id': 'CORE-04', 'pilot': 'GT21', 'run': 'v1', 'status': 'review', 'scientific_approval': False,
            'applies_to_dataset': 'nothing',
            'question': 'Does the detector reproduce the GT21 signs across treadmill, overground, ramps and stairs without a wrong sign, and does it leave the non-sagittal model pelvis unchecked?',
            'target_rule': 'B (D-UM21-C03-1 = B)', 'seed': probe['seed'], 'selection': probe['selection'],
            'subjects': probe['subjects'], 'classes': probe['classes'],
            'inputs_sha256': {str(PROBE.relative_to(ROOT)): digest(PROBE)},
            'code_sha256': {**probe['code_sha256'], f'{Path(__file__).relative_to(ROOT)} (sheet)': digest(Path(__file__))},
            'builder_history': BUILDER_HISTORY,
            'ground_truth': {'source': 'docs/quality/audits/gt21-c01-conventions.json (model rotation axes, knee range '
                                       '-120..10 deg, joint_moments positive along the coordinate) mapped to rule B',
                             'signs': {k: v for k, v in TRUTH.items() if k != 'pelvis_tilt'},
                             'pelvis': f'not tested: model heading sagittal in {sagittal} of {len(recs)} recordings'},
            'adapter': {'channels': 'ik (deg -> rad, model zero), id (N*m, not mass-normalized), jp (W)',
                        'units': 'source heel strike to heel strike per leg (gcRight/gcLeft), 0.6-2.5 s, resampled to 150',
                        'geometry': COP_REGISTRATION, 'parameters': probe['adapter_parameters'],
                        'mass': probe['mass_source'], 'forward_axis': 'per-stride pelvis facing'},
            'counts': counts, 'per_channel_outcomes': {ch: dict(v) for ch, v in per.items()},
            'per_condition_outcomes': by_cond,
            'per_test': {k: dict(v) for k, v in rows.items()}, 'wrong_single_test_votes': wrong_vote_detail,
            'half_cycle': {'by_test': {k: dict(v) for k, v in hc.items()}, 'total': dict(hc_tot),
                           'fixed_timing_family_leg_channels': fixed_timing},
            'gates': {'leg_assignment': {f'{k} / {v}': n for (k, v), n in gate.items()}, 'grf_unit': dict(unit),
                      'marker_vertical_order': dict(marker), 'plate_frame': {f'{k} / {v}': n for (k, v), n in frame.items()}},
            'force_capture_strides': dict(force), 'strides': strides,
            'pelvis_heading': {'recordings': len(recs), 'sagittal': sagittal,
                               'per_recording': [{'recording': r['recording'], **r['model_heading_deg']} for r in recs]},
            'rejected_recordings': rejected, 'skipped': skipped,
            'stride_tallies': probe['stride_tallies'],
            'explanations': {},
            'per_leg': [{'leg': name(r), 'strides': r['strides'], 'sources': r['sources'],
                         'force_status_strides': r['force_status_strides'], 'slope': r['slope_median_q05_q95'],
                         **{ch: {'verdict': [r['channels'][ch]['verdict'], r['channels'][ch]['sign']],
                                 'truth': r['channels'][ch]['truth'], 'families': r['channels'][ch]['families'],
                                 'tests': {e['test']: [e['sign'], e['agree']] for e in r['channels'][ch]['evidence']}}
                            for ch in CHANNELS}} for r in L],
            'resources': probe['resources'], 'files_read': len(probe['files_read']),
            'limitations': [f'{n_subj} subjects, {len(L)} legs; seeded recordings per mode, not every recording.',
                            'Task per stride is geometric (pelvis rise over run), not the source label; transition strides excluded.',
                            'Hip point is the Thigh_Upper marker (no trochanter marker); the vertical-order guard decides its use.',
                            'Model heading about 90 deg: pelvis tilt not tested.',
                            'Body mass unit unresolved (GT21-S01); used only by the GRF-unit check and ID-light; signs only.',
                            'No detector threshold was changed for this pilot; the GRF-unit check now ignores units whose GRF the adapter withheld (bug found by this pilot, synthetic test added).'],
            'generated_by': 'contributor_tools/review_core04_gt21_pilot.py'}
    data['explanations'] = explain(data, where, L)
    SUMMARY.write_text(json.dumps(data, indent=1) + '\n')
    print(json.dumps({'chips': chips, 'counts': counts, 'summary_sha256': digest(SUMMARY)}, indent=1))


def explain(data, where, L):
    """Every disagreement (wrong verdict or wrong single-test vote) and every class of non-applied verdict,
    grouped by channel, condition, verdict and the detector's reason, with the undecided tests' reasons."""
    groups = collections.defaultdict(lambda: {'legs': [], 'undecided_tests': collections.Counter()})
    for r in L:
        for ch in CHANNELS:
            c = r['channels'][ch]
            if c['verdict'] == 'apply':
                continue
            g = groups[(ch, r['condition'], c['verdict'], c['reason'])]
            g['legs'].append(name(r))
            for e in c['evidence']:
                if e['sign'] is None and not e['test'].startswith('derived:'):
                    g['undecided_tests'][f"{e['test']}: {e['reason']}"] += 1
    half_legs = [r for r in L if any((e['stats'] or {}).get('half_cycle', {}).get('result') == 'half'
                                     for e in r['channels']['hip_moment']['evidence'])]
    half_hip_applied = sum(r['channels']['hip_moment']['verdict'] == 'apply' for r in half_legs)
    non_applied = [{'channel': ch, 'condition': cond, 'verdict': v, 'reason': why, 'legs': len(g['legs']),
                    'undecided_tests': dict(g['undecided_tests'].most_common(4))}
                   for (ch, cond, v, why), g in sorted(groups.items())]
    return {
        'wrong_signs': 'none: no wrong verdict' + ('' if not data['wrong_single_test_votes'] else
                                                  '; single-test wrong votes are listed in wrong_single_test_votes'),
        'wrong_single_test_votes': ('none' if not data['wrong_single_test_votes'] else
                                    'listed with their reasons in wrong_single_test_votes'),
        'pelvis': ('Model heading about +-90 deg (subjects walk along lab Z; GT21-C01), so ik pelvis_tilt is mostly '
                   'obliquity and the pelvis was not tested. One recording had a circular-median heading inside the band '
                   'with a wide spread (a turning path); its strides were a minority of the leg, so the pelvis stayed '
                   'unchecked there as well.'),
        'knee_power': 'Knee power has no timing test; the power identity needs the knee angle and knee moment applied, and '
                      'the knee moment has only the knee lever arm (one family), so the identity has no anchor.',
        'knee_moment': 'Only the knee lever arm (plate geometry) tests the knee moment: suggest at most.',
        'hip_and_ankle_power': 'Power timing covers level walking (hip H3) and level/incline walking (ankle); elsewhere '
                               'only the power identity can vote, which is one family.',
        'stairs': 'Stair descent is outside the plate-timed tests and the leg gate; stair angles then rest on markers '
                  'alone (one family). The knee range test needs walking.',
        'half_cycle': {'ambiguous': 'Where the half-cycle check is ambiguous, the marker and plate-timing tests merge into one '
                                    '"fixed timing shape" family (suggest at most).',
                       'half': 'All "half" results are the hip lever arm (a weak test): its per-stride correlation with the '
                               'source hip moment is low (median |r| 0.13-0.63) and slightly higher at a half-cycle lag, so '
                               'it abstained, as designed. Likely causes: the hip point is a thigh marker, not the joint '
                               'centre, and the lever arm ignores the swing-phase inertial moment. No wrong sign followed; '
                               f'the hip moment was still applied from the other families in {half_hip_applied} of those {len(half_legs)} legs.'},
        'leg_gate_not_decided': 'Stair descent is outside the gate (12 legs). On ramps and stair ascent the knee peak fell '
                                'in swing in 74-89 % of strides, below the 90 % needed to pass (large early-stance knee '
                                'flexion); nothing failed. One overground leg had too few strides with captured stance.',
        'plate_frame_unknown': 'CoP progression and braking/propulsion are defined for forward heel-strike walking, so they '
                               'are unknown on stairs (24 legs each); the remaining unknowns had too few or mixed votes.',
        'rejected_recordings': [{**r, 'explanation': REJECTION_EXPLAINED.get(r['recording'], {}).get('detail', 'cause not checked'),
                                 'explanation_source': REJECTION_EXPLAINED.get(r['recording'], {}).get('source')}
                                for r in data['rejected_recordings']],
        'non_applied_by_reason': non_applied}


def main():
    os.nice(max(0, 19 - os.nice(0)))
    build_sheet()


if __name__ == '__main__':
    main()
