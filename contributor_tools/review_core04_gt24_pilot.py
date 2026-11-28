"""CORE-04 GT24 pilot, SHEET step (no data access).

Builds docs/quality/audits/core04-gt24-pilot.json and review_sheets/CORE-04/gt24.html from
the probe file only. The probe step is contributor_tools/probe_core04_gt24.py.
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
from contributor_tools.probe_core04_gt24 import (AUDITS, CHANNELS, COP_REGISTRATION, DOCUMENTATION,  # noqa: E402
                                                 PROBE, SEED, TRUTH, digest)
from contributor_tools.common import sign_offset_detector as sod  # noqa: E402
from contributor_tools.common.documentation_policy import split_documentation  # noqa: E402

SUMMARY = AUDITS / 'core04-gt24-pilot.json'
SHEET = ROOT / 'review_sheets/CORE-04'
LABEL = {'hip_angle': 'hip angle', 'knee_angle': 'knee angle', 'ankle_angle': 'ankle angle',
         'hip_moment': 'hip moment', 'knee_moment': 'knee moment', 'ankle_moment': 'ankle moment',
         'hip_power': 'hip power', 'knee_power': 'knee power', 'ankle_power': 'ankle power'}
SHORT = {'level 1.2 m/s, exo on': 'lvl on', 'level 1.2 m/s, exo off': 'lvl off',
         'incline 5 deg, exo on': 'up5', 'decline 5 deg, exo on': 'dn5'}
BUILDER_HISTORY = [{'probe_file': 'core04-gt24-pilot-probe.json (v1)', 'probe_builder': 'contributor_tools/probe_core04_gt24.py',
                    'sheet_builder': 'contributor_tools/review_core04_gt24_pilot.py',
                    'note': 'Probe and sheet steps are separate files from the start, so sheet edits never change the '
                            'probe hash recorded in the probe output.'},
                   {'probe_file': 'v1 (unchanged; ran with every README statement supplied)',
                    'probe_builder': 'probe_core04_gt24.py after the documentation policy',
                    'note': 'Documentation policy (Jose, 2026-10-30, "fix both readmes based on the evidence"): the adapter '
                            'now passes only statements no verified audit has refuted (refuted_documentation.json); the README '
                            'ankle statement is logged as refuted by GT24-C02. v1 was re-scored from its stored evidence '
                            'under the policy (no data read); the next probe run passes the filtered list itself.'}]
BT12_NOTE = ('BT12 right leg: no strides in either level trial because the publisher NaN-filled that leg (insole and moments '
             '0 % finite in both level trials, 95 % in incline 5; CORE-04 GT24 verifier), as README line 95 describes: '
             '"Due to a failure in one of the loadcells on our instrumented treadmill, there are several trials where the '
             'resulting joint torques are invalid. The invalid data has been NaNd in the dataset."')


def policy_rescore(r, refuted_channels):
    """Recombine one leg's stored primary evidence without refuted documentation (no data read)."""
    out = {}
    for ch in CHANNELS:
        c = r['channels'][ch]
        ev = [sod.Evidence(e['test'], ch, e['strength'], e['sign'], e['reason'], stats=e.get('stats') or {})
              for e in c['evidence'] if not (e['test'] == 'documentation' and ch in refuted_channels)]
        v = sod.combine(ev)
        t = c['truth']
        if v['verdict'] in ('apply', 'suggest'):
            outcome = f"{'applied' if v['verdict'] == 'apply' else 'suggested'}_{'correct' if v['sign'] == t else 'wrong'}"
        else:
            outcome = v['verdict']
        out[ch] = {'verdict': v['verdict'], 'sign': v['sign'], 'truth': t, 'outcome': outcome, 'reason': v['reason']}
    return out


def legs(probe):
    return [r for r in probe['records'] if 'skipped' not in r]


def name(r):
    return f"{r['phase'].replace('Phase1And2', 'P12').replace('Phase3', 'P3')}/{r['subject']} {SHORT[r['condition']]} {r['side'][0].upper()}"


def test_rows(probe, key='data_only'):
    from contributor_tools.review_core04_um21_pilot import TEST_LABEL
    rows = collections.OrderedDict()
    for r in legs(probe):
        for ch in CHANNELS:
            c = r[key][ch]
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
    from contributor_tools.review_core04_um21_pilot import OUTCOME_COLOR, GREEN, LIGHT, GREY, ORANGE, BAD, MUTED
    L = legs(probe)
    fig, ax = plt.subplots(figsize=(3.6, 7.4))
    for i, ch in enumerate(CHANNELS):
        y = len(CHANNELS) - 1 - i
        for j, r in enumerate(L):
            ax.add_patch(plt.Rectangle((j, y), .9, .9, color=OUTCOME_COLOR[r['channels'][ch]['outcome']], lw=0))
    ax.set_xlim(0, len(L)); ax.set_ylim(0, len(CHANNELS))
    ax.set_yticks([len(CHANNELS) - 1 - i + .45 for i in range(len(CHANNELS))])
    ax.set_yticklabels([LABEL[c] for c in CHANNELS], fontsize=10)
    ax.set_xticks([j + .45 for j in range(0, len(L), 4)])
    ax.set_xticklabels([name(L[j]) for j in range(0, len(L), 4)], rotation=90, fontsize=10)
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in (GREEN, LIGHT, GREY, ORANGE, BAD)]
    ax.legend(handles, ['applied, right sign', 'suggested, right sign', 'abstained',
                        'conflict (README vs data)', 'wrong sign (example; none here)'],
              loc='upper left', bbox_to_anchor=(-.28, -.24), ncol=1, fontsize=10, handlelength=1)
    ax.set_title(f'{len(L)} legs, every 4th labelled', loc='left', fontsize=10, color=MUTED)
    fig.savefig(path, dpi=170, bbox_inches='tight'); plt.close(fig)


def fig_readme(plt, probe, path):
    """Ankle evidence: legs voting dorsiflexion-positive (+1) or plantarflexion-positive (-1) per data test,
    against the README statement."""
    from contributor_tools.review_core04_um21_pilot import GREEN, BAD, GREY, MUTED
    L = legs(probe)
    rows = [('push-off (angle)', 'ankle_angle', 'ankle_pushoff_plantarflexion'),
            ('lever arm (moment)', 'ankle_moment', 'lever_arm'),
            ('late stance (moment)', 'ankle_moment', 'late_stance_plantarflexor')]
    fig, ax = plt.subplots(figsize=(3.0, 3.2))
    for i, (lab, ch, t) in enumerate(rows):
        votes = [next((e['sign'] for e in r['data_only'][ch]['evidence'] if e['test'] == t), None) for r in L]
        pos, neg, none = votes.count(1), votes.count(-1), votes.count(None)
        y = len(rows) - i
        ax.barh(y, pos, color=GREEN, height=.6, lw=0)
        ax.barh(y, -neg, color=BAD, height=.6, lw=0)
        ax.text(2, y, f'{pos} DF+, {neg} PF+', va='center', fontsize=10, color='white')
    ax.barh(0, -len(L), color=GREY, height=.6, lw=0, hatch='//', edgecolor=BAD)
    ax.text(-len(L) + 1, 0, 'README: PF +', va='center', fontsize=10)
    ax.axvline(0, color=MUTED, lw=.6)
    ax.set_yticks([len(rows) - i for i in range(len(rows))] + [0])
    ax.set_yticklabels([r[0] for r in rows] + ['README'], fontsize=10)
    ax.set_xlim(-len(L) - 2, len(L) + 2); ax.set_xticks([-len(L), 0, len(L)])
    ax.set_xticklabels(['PF +', '0', 'DF +'])
    ax.set_xlabel(f'legs voting each ankle sign (of {len(L)})')
    ax.set_title('Data tests, no documentation used', loc='left', fontsize=10, color=MUTED)
    fig.savefig(path, dpi=170, bbox_inches='tight'); plt.close(fig)


def build_sheet():
    from contributor_tools.common.review_sheet import page
    from contributor_tools.review_core04_um21_pilot import style, fig_tests
    probe = json.loads(PROBE.read_text())
    plt = style()
    SHEET.mkdir(parents=True, exist_ok=True)
    for old in SHEET.glob('gt24_*.png'):
        old.unlink()
    rows = test_rows(probe)
    fig_grid(plt, probe, SHEET / 'gt24_fig1_grid.png')
    fig_tests(plt, rows, SHEET / 'gt24_fig2_tests.png')
    fig_readme(plt, probe, SHEET / 'gt24_fig3_readme.png')

    L = legs(probe)
    skipped = [r for r in probe['records'] if 'skipped' in r]

    def tally(key):
        per = {ch: collections.Counter(r[key][ch]['outcome'] for r in L) for ch in CHANNELS}
        tot = collections.Counter()
        for v in per.values():
            tot.update(v)
        counts = {'applied_right': tot['applied_correct'], 'applied_wrong': tot['applied_wrong'],
                  'suggested_right': tot['suggested_correct'], 'suggested_wrong': tot['suggested_wrong'],
                  'conflict': tot['conflict'], 'abstained': tot['abstain'], 'leg_channels': len(L) * len(CHANNELS)}
        return per, counts
    kept_docs, refuted_docs = split_documentation('GT24', DOCUMENTATION)
    refuted_channels = {e['channel'] for e in refuted_docs if e['action'] == 'withheld'}
    for r in L:
        r['policy'] = policy_rescore(r, refuted_channels)
    per_p, cnt_p = tally('channels')
    per_d, cnt_d = tally('data_only')
    per_pol, cnt_pol = tally('policy')
    policy_vs_data_only = sum((r['policy'][ch]['verdict'], r['policy'][ch]['sign']) ==
                              (r['data_only'][ch]['verdict'], r['data_only'][ch]['sign']) for r in L for ch in CHANNELS)
    wrong = sum(c['applied_wrong'] + c['suggested_wrong'] for c in (cnt_p, cnt_d, cnt_pol))
    readme_applied = [name(r) for r in L for ch in ('ankle_angle', 'ankle_moment')
                      if r['channels'][ch]['sign_applied' if 'sign_applied' in r['channels'][ch] else 'verdict'] == 'apply'
                      and r['channels'][ch]['sign'] == -1]
    hc = collections.defaultdict(collections.Counter)
    for r in L:
        for ch in CHANNELS:
            for e in r['data_only'][ch]['evidence']:
                h = (e['stats'] or {}).get('half_cycle', {})
                if 'result' in h:
                    hc[f"{ch} / {e['test'].split(':')[0]}"][h['result']] += 1
    gate = collections.Counter((r['task'], r['leg_assignment_check']['result']) for r in L)
    frame = collections.Counter((k, v['result']) for r in L for k, v in (r['plate_frame_check'] or {}).items())
    new_tests = ('stance extension', 'push-off', 'stance timing', 'power timing', 'ID-light')
    new_rows = {k: dict(v) for k, v in rows.items() if k.split(':')[0] in new_tests}
    new_wrong = sum(v.get('wrong', 0) for v in new_rows.values())
    where = lambda key, ch, o: [name(r) for r in L if r[key][ch]['outcome'] == o]

    chips = [('pass' if not wrong else 'fail', f'no wrong sign in {len(L) * len(CHANNELS)} leg-channels, in every scoring'),
             ('pass' if not readme_applied else 'fail', f'README ankle sign never applied: a conflict in all {cnt_p["conflict"] // 2} legs when supplied'),
             ('pass', f'README ankle statement now withheld as refuted: ankle moment applied in {per_pol["ankle_moment"]["applied_correct"]} of {len(L)} legs'),
             ('pass' if not new_wrong else 'fail', f'new cross-family tests: {new_wrong} wrong votes'),
             ('unchecked', 'no markers in the parsed data: hip, knee and powers reach suggest at most'),
             ('unchecked', 'knee moment and hip lever arm abstain: no knee or hip positions'),
             ('unchecked', 'moment normalizing mass unresolved: signs only'),
             ('unchecked', f'{len(skipped)} leg-conditions left out: 3 without exo-off trials, 2 NaN-filled by the publisher')]
    page(SHEET / 'gt24.html', title='GT24 detector pilot',
         ask='Look at 3 figures; reply if anything looks wrong.',
         headline=f'GaTech 2024, 6 people, exo on and off: no wrong sign; refuted README ankle sign withheld',
         chips=chips,
         figures=[('gt24_fig1_grid.png', 'Does every detected sign match the known GT24 sign?',
                   'Orange: README disagrees with data.', 'Grid of channels by legs coloured by verdict, with the README supplied'),
                  ('gt24_fig2_tests.png', 'Did any single test vote for the wrong sign?',
                   'Red would mark a wrong vote.', 'Bars per test: legs with right sign, wrong sign or no decision (data only)'),
                  ('gt24_fig3_readme.png', 'Does the README ankle sign agree with the data?',
                   'Every data test says dorsiflexion positive.', 'Counts of legs voting each ankle sign per data test against the README statement')],
         not_shown=['Moment magnitudes (normalizing mass unresolved)', 'Stairs, running and other GT24 tasks',
                    'GT21 pilot'],
         reply='GT24 pilot: ok  |  what looks wrong',
         details=[f'Seed {SEED}; subjects {", ".join(probe["subjects"])}; exo-off level walking for {", ".join(probe["subjects_with_exo_off"])}.',
                  'Conditions: treadmill level 1.2 m/s exo on, level 1.2 m/s exo off, incline 5 deg and decline 5 deg exo on; both legs; strides heel strike to heel strike from the insole vertical force.',
                  'Ground truth (rule B, target = sign x source): hip +1, knee angle -1, ankle +1 (data dorsiflexion positive); moments hip +1, knee -1, ankle +1; powers +1.',
                  'README lines 90-91 supplied as documentation in the run (ankle plantarflexion positive, so -1 for the ankle angle and moment): every ankle verdict became a conflict. Policy since then (Jose, 2026-10-30, "fix both readmes based on the evidence"): statements refuted by a verified audit are withheld and logged; the README ankle statement is refuted by GT24-C02. Re-scored from stored evidence, the result equals the data-only run.',
                  BT12_NOTE,
                  'Geometry: no markers in the Parsed zips; ankle lever arm in each calcn frame (insole_sim CoP and force, generic talus position). Lab force file not used (walking direction +-z varies by trial).',
                  f'Gate: {dict(gate)}. Plate frame checks: {dict(frame)}.',
                  f'Peak memory {probe["resources"]["peak_rss_mib"]} MiB (cap 300). Nothing applied to any dataset.',
                  'Evidence: docs/quality/audits/core04-gt24-pilot.json; builders contributor_tools/probe_core04_gt24.py and review_core04_gt24_pilot.py'])

    explanations = {
        'wrong_signs': 'none, in the primary run (with README documentation) and in the data-only run',
        'readme_conflict': {'legs': len(L), 'channels': ['ankle_angle', 'ankle_moment'],
                            'why': 'README lines 90-91 state ankle plantarflexion positive (-1 under rule B). The push-off test (ankle angle), the calcn-frame lever arm and the late-stance test (ankle moment) all vote dorsiflexion positive (+1) in every leg, so the detector reports a conflict and applies nothing. Without the documentation the ankle moment applies +1 (two families) and the ankle angle is suggest +1 (push-off only). GT24-C02 reached the same conclusion independently.'},
        'hip_angle_suggest': {'why': 'Only hip stance extension (plate timing) is available; no marker reference, so one family.'},
        'knee_angle': {'suggest': where('channels', 'knee_angle', 'suggested_correct'), 'abstain': where('channels', 'knee_angle', 'abstain'),
                       'why': 'Only the knee-range test (joint anatomy) is available; it cast too few votes on 2 incline legs (abstain).'},
        'hip_moment_suggest': {'why': 'Only stance timing; the hip lever arm and ID-light need hip, knee, heel and toe positions, which the Parsed data do not have.'},
        'knee_moment_abstain': {'why': 'The knee lever arm needs a knee position; no other knee-moment test exists.'},
        'powers': {'hip_suggest': where('channels', 'hip_power', 'suggested_correct'), 'ankle_suggest': where('channels', 'ankle_power', 'suggested_correct'),
                   'why': 'Power timing votes on level walking (hip) and level/incline walking (ankle); declines are outside it. The power identity needs the moment and angle applied, which no joint has here (the ankle moment applies only without documentation, and the ankle angle is suggest), so powers are suggest at most. Knee power has the identity only.'},
        'skipped': [{'leg': f"{r['phase']}/{r['subject']} {r['condition']} {r.get('side', '')}".strip(), 'why': r['skipped'],
                     'cause': (BT12_NOTE if r['subject'] == 'BT12' else 'no exo-off level trial for this subject')}
                    for r in skipped],
        'documentation_policy': {'instruction': 'Jose, 2026-10-30: "we should just fix both readmes based on the evidence" (a verified audit overrides a publisher README); recorded verbatim in docs/maintainers/backlog.json in the handoff checks of GT24-C02 and GT23-C02',
                                 'implementation': 'contributor_tools/common/documentation_policy.py + refuted_documentation.json; a statement is withheld only if its exact citation_id, its channel and its sign match an entry whose task has status done in backlog.json (the single authoritative record; verify files not parsed); every matching entry evaluated; integer signs required; otherwise kept and logged; policy implementation, not a new scientific decision',
                                 'refuted_log': refuted_docs, 'passed': kept_docs,
                                 'rescore': f'stored primary evidence recombined without the refuted statements: equals the data-only run in {policy_vs_data_only} of {len(L) * len(CHANNELS)} leg-channels'},
        'frame_checks': {'counts': {f'{k} / {v}': n for (k, v), n in frame.items()},
                         'why': 'CoP progression is checked against the generic ankle in the calcn frame (passes in every leg). CoP-within-foot needs heel and toe markers (unknown), so the ankle lever arm stays moderate. The braking/propulsion check reads force_x in the foot frame, which pitches with the foot; it is unknown or fails (anterior force then dropped), which does not change the lever-arm sign here.'},
        'gate': {'counts': {f'{k} / {v}': n for (k, v), n in gate.items()}}}
    data = {'task_id': 'CORE-04', 'pilot': 'GT24', 'run': 'v1', 'status': 'review', 'scientific_approval': False,
            'applies_to_dataset': 'nothing',
            'question': 'Does the detector reproduce the GT24 signs (ankle dorsiflexion positive in the data), report the README ankle statement as a conflict, and never apply it?',
            'target_rule': 'B (D-UM21-C03-1 = B)', 'seed': probe['seed'], 'selection': probe['selection'],
            'subjects': probe['subjects'], 'subjects_with_exo_off': probe['subjects_with_exo_off'], 'conditions': probe['conditions'],
            'inputs_sha256': {str(PROBE.relative_to(ROOT)): digest(PROBE)},
            'code_sha256': {**probe['code_sha256'], f'{Path(__file__).relative_to(ROOT)} (sheet)': digest(Path(__file__))},
            'builder_history': BUILDER_HISTORY,
            'ground_truth': {'source': 'docs/quality/audits/gt24-c02-ankle-sign.json (done) and the sign survey, mapped to rule B',
                             'signs': TRUTH, 'readme_statement': probe['readme']['lines_90_91'],
                             'pelvis': 'no pelvis channel or markers in the Parsed zips'},
            'adapter': {'channels': 'angle_filt (deg -> rad), moment_filt (net ID, N*m/kg; normalizing mass unresolved), power (W/kg)',
                        'units': 'heel strike to heel strike per leg from insole_sim vertical force > 10 % body weight, 0.4-2.5 s, resampled to 150',
                        'geometry': COP_REGISTRATION, 'mass': 'README w/ exo (exo on) or w/o exo (exo off), first day',
                        'documentation': probe['documentation_supplied'],
                        'forward_axis': 'not needed: no markers; ankle geometry in the calcn frame'},
            'counts_primary_with_readme': cnt_p, 'counts_data_only': cnt_d,
            'counts_policy_rescore': cnt_pol, 'policy_rescore_equals_data_only': f'{policy_vs_data_only}/{len(L) * len(CHANNELS)}',
            'per_channel_outcomes_policy': {ch: dict(v) for ch, v in per_pol.items()},
            'per_channel_outcomes_primary': {ch: dict(v) for ch, v in per_p.items()},
            'per_channel_outcomes_data_only': {ch: dict(v) for ch, v in per_d.items()},
            'readme_sign_applied_anywhere': readme_applied,
            'per_test_data_only': {k: dict(v) for k, v in rows.items()}, 'new_tests': new_rows,
            'half_cycle': {k: dict(v) for k, v in hc.items()},
            'explanations': explanations,
            'per_leg': [{'leg': name(r), 'exo': r['exo'], 'strides': r['strides'], 'body_mass_kg': r['body_mass_kg'],
                         'source_condition': r['source_condition'],
                         **{ch: {'primary': [r['channels'][ch]['verdict'], r['channels'][ch]['sign']],
                                 'data_only': [r['data_only'][ch]['verdict'], r['data_only'][ch]['sign']],
                                 'truth': r['channels'][ch]['truth'],
                                 'tests': {e['test']: [e['sign'], e['agree']] for e in r['channels'][ch]['evidence']}}
                            for ch in CHANNELS}} for r in L],
            'resources': probe['resources'], 'members_read': len(probe['members_read']),
            'limitations': ['6 subjects, 40 legs, treadmill level/incline/decline walking only.',
                            'No markers in the Parsed zips: no marker references, no knee/hip positions, no ID-light; hip, knee and powers cannot reach apply.',
                            'Moment normalizing mass unresolved (gt24-unknown-normalization-mass-review.json); only signs tested.',
                            'Ankle lever arm uses a generic talus position in calcn.',
                            'No threshold was changed for this pilot.'],
            'generated_by': 'contributor_tools/review_core04_gt24_pilot.py'}
    SUMMARY.write_text(json.dumps(data, indent=1) + '\n')
    print(json.dumps({'chips': chips, 'summary_sha256': digest(SUMMARY)}, indent=1))


def main():
    os.nice(max(0, 19 - os.nice(0)))
    build_sheet()


if __name__ == '__main__':
    main()
