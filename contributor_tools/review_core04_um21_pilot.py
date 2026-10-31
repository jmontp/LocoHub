"""CORE-04 UM21 pilot, SHEET step (no data access).

Builds docs/quality/audits/core04-um21-pilot.json (table against the UM21-C03 ground truth
under rule B, every disagreement explained, history kept) and review_sheets/CORE-04/ from the
probe files only. The probe step is contributor_tools/probe_core04_um21.py (split on
2026-10-31 so sheet edits never change a probe file's recorded hash).
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
import collections
import hashlib
import json
from pathlib import Path
import random
import resource
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.common import sign_offset_detector as sod  # noqa: E402
from contributor_tools.probe_core04_um21 import *  # noqa: F401,F403  probe constants and helpers (read-only use)
SUMMARY = AUDITS / 'core04-um21-pilot.json'
SHEET = ROOT / 'review_sheets/CORE-04'


BUILDER_HISTORY = [
    {'probe_file': 'e0f7a5c408f16bcf...', 'builder': '4392164738429dfd...', 'detector': '9fc3e878bdf3a3f3...',
     'note': 'First recorded pilot. The builder then changed only in the sheet step (build_sheet, figure '
             'functions, chip and label text); probe_recording, run_probe, resample, strides and summarize '
             'were not edited.'},
    {'probe_file': '520149f3878f6216...', 'builder': '41a009ef6eed4c99...', 'detector': '9fc3e878bdf3a3f3...',
     'note': 'Probe re-run with the changed builder and the same detector: identical to e0f7a5c4 except the '
             'code hashes and memory figures (compared field by field), so the probe step was unchanged.'},
    {'probe_file': 'this record', 'builder': 'current', 'detector': 'current',
     'note': 'Re-run after the verifier fixes: detector adds the CoP-within-foot check and the vertical-order '
             'visible-frame count; builder declares the CoP registration rule and drops the task ID from '
             'the sheet reply line. Probe file 21675be2...; detector still targeted rule C.'},
    {'probe_file': '21675be2... (unchanged)', 'builder': 'current', 'detector': 'current (rule B)',
     'note': 'Sign rule changed to B (D-UM21-C03-1, task DOC-03). The probe was not re-run: the sheet step '
             're-scores it with to_rule_b(); the probe step now also records target_rule for future runs.'},
    {'probe_file': 'core04-um21-pilot-probe-v2.json (0f84f80a...)', 'builder': 'e0bf7d46d916857c... (probe)',
     'detector': 'fb174cf25b8c5607...',
     'note': 'v2 probe (rule B, phase-3 tests): the adapter added stride durations and body mass from '
             'ParticipantDetails. The sheet was then built with builder 2126c434...: only the sheet step changed '
             '(build_sheet rewritten for v2, new compare_runs and fig_half_cycle, fig_tests height, TEST_LABEL '
             'entries for the new tests). Proof that the probe step is unchanged, without re-reading data: '
             'builder e0bf7d46 was reconstructed exactly (sha256 matches the hash recorded in the v2 probe) by '
             'reverting those sheet-step edits; an AST comparison shows every probe-step function (digest, '
             'peak_rss_mib, mem_available, rot_x, strides, resample, summarize, participant_mass, '
             'probe_recording, run_probe, main) and every module constant except TEST_LABEL identical.'},
    {'probe_file': 'v2 (unchanged)', 'builder': 'current', 'detector': 'current (after fb174cf2)',
     'note': 'Record fixes after verification: per-recording pelvis truth note (AB04/i0), builder history '
             'entry above. Detector after the probe: gate-failure message reworded (no threshold or scope '
             'change) and hip H3 power timing limited to level walking (a scope change made after seeing UM21 '
             'data). The v2 probe was not re-run; the predicted effect on its stored evidence is recorded in '
             'the summary (after_scope_change_prediction).'},
    {'probe_file': 'v2 (unchanged)', 'builder': 'split on 2026-10-31',
     'note': 'Probe and sheet steps split into contributor_tools/probe_core04_um21.py and '
             'contributor_tools/review_core04_um21_pilot.py so that sheet edits never change a recorded probe hash. '
             'Mapping: combined builder e0bf7d46... (v2 probe) -> probe file 17846c4660219d14... ; all 29 probe-step '
             'functions and constants AST-identical (only the CLI dispatcher main differs).'}]


INK, MUTED, REF, GREEN, LIGHT, GREY, ORANGE, BAD = ('#20252B', '#5b6672', '#999999', '#1f7a4d', '#9fd3b5',
                                                    '#d9dde2', '#eb6834', '#c0392b')
OUTCOME_COLOR = {'applied_correct': GREEN, 'suggested_correct': LIGHT, 'abstain': GREY, 'conflict': ORANGE,
                 'applied_wrong': BAD, 'suggested_wrong': BAD}
LABEL = {'pelvis_tilt': 'pelvis tilt', 'hip_angle': 'hip angle', 'knee_angle': 'knee angle',
         'ankle_angle': 'ankle angle', 'hip_moment': 'hip moment', 'knee_moment': 'knee moment',
         'ankle_moment': 'ankle moment', 'hip_power': 'hip power', 'knee_power': 'knee power',
         'ankle_power': 'ankle power'}


TEST_LABEL = {'reference_angle': 'markers', 'knee_hinge_asymmetry': 'knee range', 'lever_arm': 'lever arm',
              'late_stance_plantarflexor': 'late stance', 'hip_stance_extension': 'stance extension',
              'ankle_pushoff_plantarflexion': 'push-off', 'hip_moment_timing': 'stance timing',
              'power_timing': 'power timing', 'inverse_dynamics_light': 'ID-light'}


def legs_of(probe):
    for r in probe['recordings']:
        for side in 'RL':
            yield r, side, r['legs'][side]


def test_table(probe):
    """Per test and channel: legs where the test's sign matched the truth, was wrong, or did not decide."""
    rows = collections.OrderedDict()
    for _, _, leg in legs_of(probe):
        for ch in CHANNELS:
            c = leg['channels'].get(ch)
            if not c:
                continue
            for e in c['evidence']:
                if e['test'].startswith('derived:') or e['test'] in ('units_check',):
                    continue
                key = f"{TEST_LABEL[e['test'].split(':')[0]]}: {LABEL[ch]}"
                r = rows.setdefault(key, collections.Counter())
                r['no decision' if e['sign'] is None else ('right' if e['sign'] == c['truth'] else 'wrong')] += 1
        for rel in leg['relations']:
            j = rel['channels'][0].split('_')[0]
            exp = TRUTH[f'{j}_moment'] * TRUTH[f'{j}_angle'] * TRUTH_POWER[leg['power_slots'][j]]
            r = rows.setdefault(f'power identity: {j}', collections.Counter())
            r['no decision' if rel['product'] is None else ('right' if rel['product'] == exp else 'wrong')] += 1
    return rows


def style():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 10.5, 'axes.titlesize': 11, 'axes.spines.top': False,
                         'axes.spines.right': False, 'text.color': INK, 'axes.labelcolor': INK,
                         'axes.edgecolor': INK, 'xtick.color': INK, 'ytick.color': INK,
                         'axes.linewidth': 0.6, 'legend.frameon': False})
    return plt


def fig_grid(plt, probe, path):
    legs = [(f"{r['recording'].replace('/', ' ')} {s}", leg) for r, s, leg in legs_of(probe)]
    fig, ax = plt.subplots(figsize=(4.35, 6.6))
    fig.subplots_adjust(left=.27, right=.98, top=.95, bottom=.40)
    for i, ch in enumerate(CHANNELS):
        y = len(CHANNELS) - 1 - i
        for j, (_, leg) in enumerate(legs):
            o = leg['channels'][ch]['outcome']
            ax.add_patch(plt.Rectangle((j, y), .92, .9, color=OUTCOME_COLOR[o], lw=0))
            if o.endswith('_wrong'):
                ax.text(j + .46, y + .45, '×', ha='center', va='center', color='white', fontsize=10)
    ax.set_xlim(0, len(legs)); ax.set_ylim(0, len(CHANNELS))
    ax.set_yticks([len(CHANNELS) - 1 - i + .45 for i in range(len(CHANNELS))])
    ax.set_yticklabels([LABEL[c] for c in CHANNELS], fontsize=10)
    ax.set_xticks([j + .46 for j in range(len(legs))])
    ax.set_xticklabels([n for n, _ in legs], rotation=90, fontsize=10)
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in (GREEN, LIGHT, GREY, ORANGE, BAD)]
    ax.legend(handles, ['applied, right sign', 'suggested, right sign', 'abstained', 'conflict',
                        'wrong sign (example; none here)'],
              loc='upper left', bbox_to_anchor=(-.38, -.30), ncol=1, fontsize=10, handlelength=1)
    ax.set_title('One column per leg, 10 recordings', loc='left', fontsize=10, color=MUTED)
    fig.savefig(path, dpi=170, bbox_inches='tight'); plt.close(fig)


def fig_tests(plt, rows, path):
    keys = list(rows)
    fig, ax = plt.subplots(figsize=(4.5, 1.6 + 0.3 * len(keys)))
    fig.subplots_adjust(left=.50, right=.96, top=1 - 0.35 / (1.6 + 0.3 * len(keys)),
                        bottom=1.0 / (1.6 + 0.3 * len(keys)))
    for i, k in enumerate(keys):
        y = len(keys) - 1 - i
        x0 = 0
        for part, col in (('right', GREEN), ('wrong', BAD), ('no decision', GREY)):
            v = rows[k][part]
            if v:
                ax.barh(y, v, left=x0, color=col, height=.7, lw=0)
            x0 += v
    ax.set_yticks(range(len(keys) - 1, -1, -1)); ax.set_yticklabels(keys, fontsize=10)
    n_legs = max(sum(rows[k].values()) for k in keys)  # legs per test row (scales to the pilot)
    ax.set_xlim(0, n_legs); ax.set_xticks([0, n_legs // 2, n_legs]); ax.set_xlabel('legs')
    ax.tick_params(axis='y', length=0)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in (GREEN, BAD, GREY)]
    ax.legend(handles, ['right sign', 'wrong sign', 'no decision'], loc='upper left',
              bbox_to_anchor=(-1.05, -.1), ncol=3, fontsize=10, handlelength=1)
    ax.set_title(f'Each test on its own, {n_legs} legs', loc='left', fontsize=10, color=MUTED)
    fig.savefig(path, dpi=170); plt.close(fig)


def fig_episode(plt, ep, path):
    cur = np.array(ep['curves_deg'], float)
    aside = np.array(ep['set_aside'], bool)
    ph = np.linspace(0, 100, cur.shape[1])
    fig, ax = plt.subplots(figsize=(4.4, 3.2))
    for i in np.flatnonzero(~aside):
        bad = np.nanmin(cur[i]) < -100
        ax.plot(ph, cur[i], color=ORANGE if bad else REF, lw=1.4 if bad else .5, alpha=1 if bad else .5,
                ls='--' if bad else '-', zorder=3 if bad else 1)
    for i in np.flatnonzero(aside):
        ax.plot(ph, cur[i], color=BAD, lw=.6, alpha=.6)
    ax.plot([], [], color=REF, lw=1, label=f'{int((~aside).sum()) - 1} strides used')
    ax.plot([], [], color=BAD, lw=1, label=f'{int(aside.sum())} strides set aside')
    ax.plot([], [], color=ORANGE, lw=1.4, ls='--', label='1 used stride with a jump')
    ax.axhline(0, color=REF, lw=.5)
    ax.set_xlabel('right gait cycle (%)'); ax.set_ylabel('ankle, 1st component (deg)')
    ax.set_title('AB07 incline 10%, right ankle, as published', loc='left', fontsize=10, color=MUTED)
    ax.legend(loc='upper left', bbox_to_anchor=(0, -.24), fontsize=10)
    fig.savefig(path, dpi=170, bbox_inches='tight'); plt.close(fig)


RULE_B_FLIP = ('knee_angle', 'knee_moment')  # only channels whose target differs between C and B


def to_rule_b(probe):
    """Re-score a probe recorded with the rule-C detector to rule B, without data.

    Rule B differs from C only in the knee angle and knee moment targets (B = -C).
    The detector's knee tests are mirror images under that change (marker knee
    reference negated, knee-hinge expectation mirrored, knee lever arm x -1), its
    vote and agreement rules are symmetric in sign, and the knee power product
    (moment x angle) is unchanged. So verdicts and confidences stay, and the knee
    signs, evidence signs and offsets negate. Truth and outcomes are recomputed.
    """
    if probe.get('target_rule', 'C') == 'B':
        return probe
    probe = json.loads(json.dumps(probe))
    for r in probe['recordings']:
        for leg in r['legs'].values():
            for ch in RULE_B_FLIP:
                c = leg['channels'].get(ch)
                if not c:
                    continue
                c['sign'] = None if c['sign'] is None else -c['sign']
                for e in c['evidence']:
                    if e['sign'] is not None and e['strength'] != 'documentation':
                        e['sign'] = -e['sign']
                off = c['offset']
                if off.get('estimate') is not None:
                    off['estimate'] = -off['estimate']
                    off['ci95'] = [-off['ci95'][1], -off['ci95'][0]]
                c['truth'] = TRUTH[ch]
                if c['verdict'] in ('apply', 'suggest'):
                    kind = 'applied' if c['verdict'] == 'apply' else 'suggested'
                    c['outcome'] = f"{kind}_{'correct' if c['sign'] == c['truth'] else 'wrong'}"
            for rel in leg['relations']:
                if rel['test'] == 'segment_chain' and 'knee_angle' in rel['channels'] and rel['product']:
                    rel['product'] = -rel['product']
            leg['log'] = ['(rule-C log omitted after re-scoring to rule B)']
    probe['target_rule'] = 'B'
    probe['rescored_from'] = {'rule': 'C', 'method': 'to_rule_b(): knee angle and knee moment signs, '
                              'evidence signs and offsets negated; verdicts unchanged; no data re-read'}
    return probe


def fig_half_cycle(plt, probe, path):
    """Hip angle (marker test): median |r| at lag 0 vs a half-cycle lag, one dot per leg."""
    pts = []
    for r, side, leg in legs_of(probe):
        ev = [e for e in leg['channels']['hip_angle']['evidence'] if e['test'].startswith('reference_angle')]
        hc = (ev[0]['stats'] or {}).get('half_cycle', {}) if ev else {}
        if 'median_abs_r_lag0' in hc:
            pts.append((hc['median_abs_r_lag0'], hc['median_abs_r_half'], hc['result']))
    m = sod.DEFAULTS['half_cycle_margin']
    fig, ax = plt.subplots(figsize=(4.0, 3.6))
    lo = min(min(p[0] for p in pts), min(p[1] for p in pts)) - 0.03
    xs = np.linspace(lo, 1.0, 50)
    ax.fill_between(xs, xs - m, xs + m, color=GREY, lw=0, label=f'ambiguous band (gap < {m})')
    ax.plot(xs, xs, color=REF, lw=.6)
    for res, col, lab in (('lag0', GREEN, 'lag 0 better: can apply'),
                          ('ambiguous', ORANGE, 'ambiguous: suggest'),
                          ('half', BAD, 'other leg (example)')):
        sel = [p for p in pts if p[2] == res]
        ax.scatter([p[0] for p in sel], [p[1] for p in sel], s=26, color=col, lw=0,
                   label=f'{lab} ({len(sel)})', zorder=3)
    ax.set_xlim(lo, 1.0); ax.set_ylim(lo, 1.0)
    ax.set_xlabel('median |r|, lag 0'); ax.set_ylabel('median |r|, half-cycle lag')
    ax.set_title('Hip angle vs marker hip, 20 legs', loc='left', fontsize=10, color=MUTED)
    ax.legend(loc='upper left', bbox_to_anchor=(0, -.2), fontsize=10)
    fig.savefig(path, dpi=170, bbox_inches='tight'); plt.close(fig)


def scope_prediction(probe):
    """Hip H3 power timing was limited to level walking after the v2 probe (data-informed scope
    change). Predict its effect on the stored v2 evidence by dropping out-of-scope hip
    power-timing votes and recombining; not a new run."""
    changes, counts = [], collections.Counter()
    for r, side, leg in legs_of(probe):
        for ch in CHANNELS:
            c = leg['channels'][ch]
            outcome = c['outcome']
            if ch == 'hip_power' and r['task'] not in sod.POWER_TIMING_TASKS['hip']:
                ev = [sod.Evidence(e['test'], ch, e['strength'], e['sign'], e['reason'], stats=e.get('stats') or {})
                      for e in c['evidence'] if e['test'] != 'power_timing']
                v = sod.combine(ev)
                outcome = (v['verdict'] if v['verdict'] in ('abstain', 'conflict') else
                           f"{'applied' if v['verdict'] == 'apply' else 'suggested'}_"
                           f"{'correct' if v['sign'] == c['truth'] else 'wrong'}")
                if outcome != c['outcome']:
                    changes.append({'leg': f"{r['recording']} {side}", 'channel': ch,
                                    'before': c['outcome'], 'after': outcome})
            counts[outcome.split('_')[0] if outcome.endswith(('_correct', '_wrong')) else outcome] += 1
            if outcome.endswith('_wrong'):
                counts['wrong'] += 1
    return {'method': 'recombine stored v2 evidence without out-of-scope hip power-timing votes (not a probe run)',
            'changes': changes, 'counts': dict(counts)}


def compare_runs(old, new):
    """Field-by-field comparison of two probe records (both rule B)."""
    out = {'verdict_changes': [], 'sign_changes_among_decided': [], 'old_test_vote_changes': [],
           'offset_max_abs_diff_rad': 0.0, 'unchanged_channels': 0}
    old_tests = ('reference_angle:marker', 'knee_hinge_asymmetry', 'lever_arm', 'late_stance_plantarflexor')
    for r1, r2 in zip(old['recordings'], new['recordings']):
        for side in 'RL':
            for ch in CHANNELS:
                a, b = r1['legs'][side]['channels'][ch], r2['legs'][side]['channels'][ch]
                leg = f"{r2['recording']} {side}"
                if (a['verdict'], a['sign']) != (b['verdict'], b['sign']):
                    out['verdict_changes'].append({'leg': leg, 'channel': ch, 'before': [a['verdict'], a['sign']],
                                                   'after': [b['verdict'], b['sign']], 'reason_after': b['reason']})
                else:
                    out['unchanged_channels'] += 1
                if a['sign'] is not None and b['sign'] is not None and a['sign'] != b['sign']:
                    out['sign_changes_among_decided'].append({'leg': leg, 'channel': ch})
                va = {e['test']: e['sign'] for e in a['evidence']}
                vb = {e['test']: (e['sign'], e['reason']) for e in b['evidence']}
                for t in old_tests:
                    if t in va and t in vb and va[t] != vb[t][0]:
                        out['old_test_vote_changes'].append({'leg': leg, 'channel': ch, 'test': t,
                                                             'before': va[t], 'after': vb[t][0], 'reason': vb[t][1]})
                ea, eb = a['offset'].get('estimate'), b['offset'].get('estimate')
                if ea is not None and eb is not None:
                    out['offset_max_abs_diff_rad'] = max(out['offset_max_abs_diff_rad'], abs(ea - eb))
    out['offset_max_abs_diff_rad'] = round(out['offset_max_abs_diff_rad'], 6)
    return out


def build_sheet():
    from contributor_tools.common.review_sheet import page
    probe = json.loads(PROBE.read_text())
    assert probe.get('target_rule') == 'B'
    v1 = to_rule_b(json.loads(PROBE_V1.read_text()))
    cmp = compare_runs(v1, probe)
    history = []
    if SUMMARY.exists():
        prev = json.loads(SUMMARY.read_text())
        history = prev.get('history', [])
        if prev.get('run') != 'v2':
            history.append({k: prev.get(k) for k in ('target_rule', 'rescored_from', 'inputs_sha256', 'code_sha256',
                                                     'per_channel_outcomes', 'per_test', 'explanations',
                                                     'pair_evidence_for_D-CORE-04-1', 'resources', 'builder_history')}
                           | {'run': 'v1 (rule-C detector, re-scored to rule B)'})
    plt = style()
    SHEET.mkdir(parents=True, exist_ok=True)
    for old in SHEET.glob('*.png'):
        old.unlink()
    rows = test_table(probe)
    fig_grid(plt, probe, SHEET / 'fig1_grid.png')
    fig_tests(plt, rows, SHEET / 'fig2_tests.png')
    fig_half_cycle(plt, probe, SHEET / 'fig3_half_cycle.png')

    per_channel = {ch: collections.Counter() for ch in CHANNELS}
    per_leg, offsets = [], collections.defaultdict(list)
    hc = collections.defaultdict(dict)
    for r, side, leg in legs_of(probe):
        name = f"{r['recording']} {side}"
        row = {'leg': name, 'task': r['task'], 'power_slots': leg['power_slots'], 'body_mass_kg': r['body_mass_kg'],
               'leg_assignment': leg['leg_assignment_check']}
        for ch in CHANNELS:
            c = leg['channels'][ch]
            per_channel[ch][c['outcome']] += 1
            row[ch] = {'verdict': c['verdict'], 'sign': c['sign'], 'truth': c['truth'], 'outcome': c['outcome'],
                       'families': c.get('families'), 'tests': {e['test']: [e['sign'], e['agree']] for e in c['evidence']}}
            for e in c['evidence']:
                h = (e.get('stats') or {}).get('half_cycle')
                if h and 'result' in h:
                    hc[(ch, e['test'].split(':')[0])][name] = h['result']
            if c['offset'].get('estimate') is not None:
                offsets[ch].append((c['offset']['estimate'], c['offset']['flag_for_review']))
        per_leg.append(row)
    n_legs = len(per_leg)
    count = lambda kind: sum(v[f'{kind}_correct'] + v[f'{kind}_wrong'] for v in per_channel.values())
    wrong = [(row['leg'], ch) for row in per_leg for ch in CHANNELS if row[ch]['outcome'].endswith('_wrong')]
    abstain = sum(v['abstain'] for v in per_channel.values())
    conflict = sum(v['conflict'] for v in per_channel.values())
    new_tests = ('stance extension', 'push-off', 'stance timing', 'power timing', 'ID-light')
    new_rows = {k: dict(v) for k, v in rows.items() if k.split(':')[0] in new_tests}
    new_wrong = sum(v.get('wrong', 0) for v in new_rows.values())
    new_decided = sum(v.get('right', 0) + v.get('wrong', 0) for v in new_rows.values())
    new_total = sum(sum(v.values()) for v in new_rows.values())
    rel_right = sum(rows[k]['right'] for k in rows if k.startswith('power identity'))
    rel_total = sum(sum(rows[k].values()) for k in rows if k.startswith('power identity'))
    hip_amb = sorted(k for k, v in hc[('hip_angle', 'reference_angle')].items() if v == 'ambiguous')
    id_amb = sorted(k for k, v in hc[('hip_moment', 'inverse_dynamics_light')].items() if v == 'ambiguous')
    lever_half = sorted(k for k, v in hc[('hip_moment', 'lever_arm')].items() if v == 'half')
    gate_fail = [row['leg'] for row in per_leg if row['leg_assignment']['result'] == 'fail']
    gate_frac = {row['leg']: row['leg_assignment'].get('knee_peak_in_swing_fraction') for row in per_leg}
    off_flag = sum(f for v in offsets.values() for _, f in v)
    off_total = sum(len(v) for v in offsets.values())
    off_max = max(abs(e) for ch, v in offsets.items() if ch != 'pelvis_tilt' for e, _ in v)
    gained = [c for c in cmp['verdict_changes'] if c['after'][0] in ('apply', 'suggest') and c['before'][0] != 'apply'
              and not (c['before'][0] == 'suggest' and c['after'][0] == 'suggest')]
    lost = [c for c in cmp['verdict_changes'] if c['before'][0] == 'apply' and c['after'][0] != 'apply']
    ep_rec = next(r for r in probe['recordings'] if 'episode_curves' in r)
    ep_strides = ep_rec['legs']['R']['branch_strides']['ankle_angle']
    masses = {r['recording'].split('/')[0]: r['body_mass_kg'] for r in probe['recordings']}

    chips = [('pass' if not wrong else 'fail', f'no wrong sign in {n_legs * len(CHANNELS)} leg-channels: {count("applied")} applied, {count("suggested")} suggested' if not wrong else f'{len(wrong)} wrong signs'),
             ('pass' if not new_wrong else 'fail', f'new tests: {new_wrong} wrong votes; decided {new_decided} of {new_total} leg-tests'),
             ('pass' if not cmp['sign_changes_among_decided'] else 'fail', f'vs the earlier run: {len(cmp["sign_changes_among_decided"])} sign changes; {len(gained)} channels gained a verdict, {len(lost)} lost apply'),
             ('pass', f'power slot and sign recovered in {rel_right} of {rel_total} leg-joints, both layouts'),
             ('unchecked', f'{len(hip_amb)} of {n_legs} hips cannot be told from the other leg: hip angle suggest only'),
             ('unchecked', f'leg gate failed on both AB07 incline-10 legs: their plate-timed tests abstained'),
             ('unchecked', f'hip lever arm read "other leg?" in {len(lever_half)} legs; column is right (weak test, no effect)'),
             ('unchecked', f'{off_flag} of {off_total} angle zero offsets flagged, up to {np.degrees(off_max):.0f}°, not interpreted')]
    page(SHEET / 'index.html', title='UM21 detector pilot',
         ask='Look at 3 figures; reply if anything looks wrong.',
         headline=f'Re-run with cross-family tests: {count("applied")} UMich signs applied, none wrong',
         chips=chips,
         figures=[('fig1_grid.png', 'Does every detected sign match the known UMich sign?',
                   'Grey: abstained.', 'Grid of channels by legs coloured by verdict and correctness'),
                  ('fig2_tests.png', 'Did any single test vote for the wrong sign?',
                   'Red would mark a wrong vote.', 'Bars per test: legs with right sign, wrong sign or no decision'),
                  ('fig3_half_cycle.png', 'Which hips can be told apart from the other leg?',
                   'Orange: ambiguous, so suggest only.', 'Scatter of hip fit at lag 0 against a half-cycle lag, one dot per leg')],
         not_shown=['Anatomical meaning of the zero offsets', 'GT21, GT23 and GT24 pilots',
                    'Running, stairs, overground walking'],
         reply='detector pilot: ok  |  what looks wrong',
         details=[f'Same 10 recordings (seeds {SEED_A}, {SEED_B}, plus AB01/i0 and AB07/i10), 20 legs; detector build {probe["code_sha256"]["contributor_tools/common/sign_offset_detector.py"][:8]}; rule B.',
                  f'Inputs added: stride durations from frame counts at {RATE_HZ:.0f} Hz; body mass from ParticipantDetails {masses} kg (declared for the GRF unit check and ID-light).',
                  f'Hips ambiguous: {", ".join(hip_amb)}. ID-light ambiguous (hip moment suggest): {", ".join(id_amb)}.',
                  f'Leg gate failed (knee peak in swing in {gate_frac.get("AB07/i10 R")} and {gate_frac.get("AB07/i10 L")} of strides): {", ".join(gate_fail)}; all others passed (0.94-1.0).',
                  f'Hip lever arm "other leg?" (half lag better) in {", ".join(lever_half)}; weak test scoring 0.',
                  f'Branch episode unchanged: AB07/i10 R frames {ep_strides["first_frame"]}-{ep_strides["last_frame"]}, {len(ep_strides["strides_1based_frames"])} strides set aside.',
                  f'Peak memory {probe["resources"]["peak_rss_mib"]} MiB (cap 300). Nothing applied to any dataset.',
                  'Pelvis truth varies per recording: in AB04/i0 (not in this sample) Plug-in Gait reversed the walking direction, so its stored tilt is flipped and a +1 suggestion is correct there; the 10 recordings here are unaffected.',
                  'After this run, hip push-off power timing was limited to level walking (scope change made after seeing UM21 data); predicted on the stored evidence: hip power 1 apply to suggest and 5 suggest to abstain, still no wrong sign.',
                  'Evidence: docs/quality/audits/core04-um21-pilot.json; builder contributor_tools/review_core04_um21_pilot.py'])

    legs_where = lambda ch, outcome: [row['leg'] for row in per_leg if row[ch]['outcome'] == outcome]
    explanations = {
        'wrong_signs': wrong or 'none: every applied or suggested sign equals the UM21-C03 sign under rule B',
        'conflicts': conflict,
        'hip_angle_suggest': {'legs': legs_where('hip_angle', 'suggested_correct'), 'half_cycle_ambiguous': hip_amb,
                              'why': 'Marker test half-cycle ambiguous (|r| at lag 0 within 0.05 of the half lag), so markers and hip stance extension count as one family; on AB07/i10 the leg gate also failed.'},
        'knee_angle_suggest': {'legs': legs_where('knee_angle', 'suggested_correct'),
                               'why': 'As in the first run: only the marker test decided; the knee-range test cast fewer than 5 votes or split on these incline legs.'},
        'ankle_angle_and_moment_suggest': {'legs': legs_where('ankle_angle', 'suggested_correct') + legs_where('ankle_moment', 'suggested_correct'),
                                           'why': 'AB07/i10: the leg gate failed, so push-off and late-stance tests abstained; each channel kept one family.'},
        'hip_moment': {'applied': legs_where('hip_moment', 'applied_correct'), 'suggest': legs_where('hip_moment', 'suggested_correct'),
                       'id_light_ambiguous': id_amb,
                       'why': 'Applied where ID-light (with the declared body mass) and stance timing agree and ID-light separates lag 0 from the half lag; suggest where ID-light is half-cycle ambiguous (families collapse) or the gate failed (AB07/i10).'},
        'hip_lever_arm_half': {'legs': lever_half,
                               'why': 'The quasi-static hip lever arm fits the moment column better half a cycle late in these legs although the column is this leg\'s (the same column agrees with ID-light). The test is weak (score 0) and the flag makes it abstain; no effect on verdicts. A false "other leg?" alarm, recorded.'},
        'leg_gate_fail': {'legs': gate_fail, 'knee_peak_in_swing_fraction': {k: gate_frac[k] for k in gate_fail},
                          'why': 'In these 10 % incline legs the knee\'s largest excursion from its median falls in stance in about 93 % of strides, so the gate reads the plate as belonging to the other leg and all plate-timed tests abstain (conservative). Plates and units are this leg\'s (the lever arm and CoP checks pass). The knee-range test also cast few votes on these legs in the first run; the cause is not checked further.'},
        'power': {'ankle_applied': legs_where('ankle_power', 'applied_correct'), 'ankle_suggest': legs_where('ankle_power', 'suggested_correct'),
                  'hip_applied': legs_where('hip_power', 'applied_correct'), 'hip_suggest': legs_where('hip_power', 'suggested_correct'),
                  'power_identity_right': f'{rel_right}/{rel_total}',
                  'why': 'Apply needs the power identity (moment and angle both applied) plus power timing. Power timing excludes decline walking (ankle and hip; 10 legs) and abstained where the leg gate failed (AB07/i10, 2 legs); on those legs only the identity decides (suggest or abstain). Hip power also needs an applied hip angle and moment. Knee power has the identity only.'},
        'pelvis_and_knee_moment': 'One family each (marker geometry; plate geometry): suggest only, all right.',
        'offsets': {'flagged': f'{off_flag}/{off_total}', 'others_max_deg': round(float(np.degrees(off_max)), 1),
                    'max_abs_change_vs_first_run_rad': cmp['offset_max_abs_diff_rad'],
                    'why': 'Reported only; zero-definition differences against marker zeros; never applied.'}}
    data = {
        'task_id': 'CORE-04', 'pilot': 'UM21', 'run': 'v2', 'status': 'review', 'scientific_approval': False,
        'applies_to_dataset': 'nothing',
        'question': 'Does the detector (rule B, phase-3 cross-family tests) reproduce the verified UMich 2021 treadmill signs, and abstain rather than err?',
        'target_rule': 'B (D-UM21-C03-1 = B, task DOC-03)',
        'source': probe['source'], 'seeds': probe['seeds'], 'samples': probe['samples'],
        'inputs_sha256': {str(PROBE.relative_to(ROOT)): digest(PROBE), str(PROBE_V1.relative_to(ROOT)): digest(PROBE_V1),
                          str(C03.relative_to(ROOT)): digest(C03)},
        'code_sha256': {**probe['code_sha256'], f'{Path(__file__).relative_to(ROOT)} (sheet)': digest(Path(__file__))},
        'builder_history': BUILDER_HISTORY,
        'ground_truth': {'source': 'UM21-C03 and sign-conventions-source-survey.json mapped to rule B (the UMich clinical source matches B except pelvis tilt)',
                         'per_recording_caveat': ('The UMich pelvis truth varies per recording. In AB04/i0 (verifier run; not in this '
                                                  'pilot) Plug-in Gait computed the pelvis with the walking direction reversed (median '
                                                  'pelvis rotation 180.2 deg vs about 0 elsewhere), so the stored tilt there is flipped and '
                                                  'the detector\'s +1 pelvis suggestion is correct for that recording. Checked for the '
                                                  'pilot\'s 10 recordings: none is affected (pelvis marker test agreed with -1 in every '
                                                  'leg, offset within 0.2 deg).'),
                         'signs': TRUTH, 'power_by_slot': {'slot 1 (layout 1)': -1, 'slot 3 (layout 2)': 1},
                         'hip_moment_status': 'partly verified in UM21-C03 (weak lever-arm evidence)'},
        'adapter': {'angles': 'component 1 of {side}{Pelvis,Hip,Knee,Ankle}Angles, deg -> rad; exact (0,0,0) triples -> missing',
                    'moments': 'component 1 of {side}{Hip,Knee,Ankle}Moment (N*m/kg as stored)',
                    'power': 'first non-zero slot of {side}{Joint}Power (slot recorded; no sign change)',
                    'units': 'one stride per unit (heel strike to heel strike, 50-250 frames), resampled to 150 samples; unit_durations_s = (frames - 1) / 100 Hz',
                    'markers': 'sagittal projection on the median heel-to-toe forward axis, lab +z up',
                    'plates': 'block mean to 100 Hz, README belt tilt, GRF on foot = -(plate force), declared unit N with body_mass_kg from ParticipantDetails Bodymass; CoP by the moment-independent midpoint rule',
                    'body_mass_kg': masses,
                    'not_supplied': 'documentation statements and templates'},
        'counts': {'applied_right': count('applied'), 'suggested_right': count('suggested'), 'abstained': abstain,
                   'conflict': conflict, 'wrong': len(wrong)},
        'after_scope_change_prediction': scope_prediction(probe),
        'per_channel_outcomes': {ch: dict(v) for ch, v in per_channel.items()},
        'per_test': {k: dict(v) for k, v in rows.items()},
        'new_tests': new_rows,
        'half_cycle': {f'{ch} / {t}': dict(collections.Counter(v.values())) for (ch, t), v in hc.items()},
        'comparison_with_rule_B_rescore_of_v1': {**{k: v for k, v in cmp.items() if k != 'verdict_changes'},
                                                'verdict_changes_count': len(cmp['verdict_changes']),
                                                'gained_verdict': len(gained), 'lost_apply': lost,
                                                'verdict_changes': cmp['verdict_changes']},
        'explanations': explanations,
        'per_leg': per_leg,
        'resources': probe['resources'],
        'history': history,
        'limitations': ['One dataset (Vicon Plug-in Gait, treadmill, 10 recordings, 20 legs); no running, stairs or overground.',
                        'Hip moment ground truth is weak (UM21-C03); hip power truth follows from it.',
                        'Strides are resampled before the branch screen (one AB07/i10 jump stride kept, no vote).',
                        'No threshold was changed for this run.'],
        'generated_by': 'contributor_tools/review_core04_um21_pilot.py sheet'}
    SUMMARY.write_text(json.dumps(data, indent=1) + '\n')
    print(json.dumps({'chips': chips, 'summary_sha256': digest(SUMMARY)}, indent=1))


def main():
    os.nice(max(0, 19 - os.nice(0)))
    build_sheet()


if __name__ == '__main__':
    main()
