#!/usr/bin/env python3
"""Build docs/quality/fixes.html: one before/after card per verified data finding.

Inputs are read-only and small: committed audit records in docs/quality/audits/,
docs/maintainers/backlog.json and the independent verification handoffs in
docs/maintainers/handoffs/. No research data, source archive or converted dataset
is opened, and no value is measured here. Figures plot curves and numbers that the
audits stored; the only arithmetic is the sign or recipe being compared (for
example hip - pelvis) and division by a mass the audit recorded.

A card is published only when its task is ``done`` in the backlog and its
independent verification file records a ``done`` verdict. Cards whose task is not
yet done are skipped and listed on stderr; nothing else about their status is
inferred.

Rule exception (José's approval, 2026-10-31, relayed by the coordinator): the two
UM21-T02 findings in APPROVED_EXCEPTIONS (belt-clock misalignment, AB01 i5 copy of
i10) are shown although UM21-T02 is not done. Each still requires its own
independently verified evidence, checked on every build (verdicts, the named
verification items and, for the clock census, the reviewed file hash); the card
says the task is not done and cites the approval. No other card may use it. Status labels are written by hand below and must say whether corrected
files exist; at the time of writing none do.

Examples come from a recorded seed (SEED) over a pool stated in each card, never
hand-picked. Figures are one panel each, 4.5 in wide, fonts at least 10 pt.

    python3 contributor_tools/build_fixes_page.py          # write page and figures
    python3 contributor_tools/build_fixes_page.py --check  # fail if they are stale
"""
from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import random
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
AUDITS = ROOT / 'docs/quality/audits'
HANDOFFS = ROOT / 'docs/maintainers/handoffs'
BACKLOG = ROOT / 'docs/maintainers/backlog.json'
PAGE = ROOT / 'docs/quality/fixes.html'
FIG_DIR = ROOT / 'docs/quality/fixes'
SEED = 20261031
AS_OF = '31 October 2026'

INK, MUTED, GREY = '#20252b', '#5b6672', '#b4bcc4'
BEFORE, AFTER = '#c4501a', '#1f6aa5'   # orange = disagreement, blue = agreement
WIDTH_IN = 4.5
ESC = lambda value: html.escape(str(value), quote=True)
SIZES: dict[str, tuple[int, int]] = {}


def load(name):
    return json.loads((AUDITS / name).read_text(encoding='utf-8'))


# ----------------------------------------------------------------- figures

def plt_module():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        'font.size': 10, 'axes.labelsize': 10, 'xtick.labelsize': 10, 'ytick.labelsize': 10,
        'legend.fontsize': 10, 'axes.spines.top': False, 'axes.spines.right': False,
        'text.color': INK, 'axes.labelcolor': INK, 'axes.edgecolor': INK,
        'xtick.color': INK, 'ytick.color': INK, 'legend.frameon': False,
        'axes.linewidth': 0.7, 'svg.hashsalt': 'locohub-fixes', 'svg.fonttype': 'path',
        'figure.facecolor': 'white', 'axes.facecolor': 'white'})
    return plt


def svg_bytes(fig):
    buffer = io.BytesIO()
    fig.savefig(buffer, format='svg', metadata={'Date': None, 'Creator': None})
    return buffer.getvalue()


def line_figure(plt, x, xlabel, ylabel, ylim, background=(), lines=(), height=3.1):
    """One panel: optional grey background curves, then labelled lines."""
    fig, ax = plt.subplots(figsize=(WIDTH_IN, height), layout='constrained')
    ax.axhline(0, color=GREY, lw=0.6, zorder=0)
    for curve in background:
        ax.plot(x, curve, color=GREY, lw=0.6, alpha=0.55, zorder=1)
    for item in lines:
        ax.plot(x, item['y'], color=item['color'], lw=item.get('lw', 1.8), ls=item.get('ls', '-'),
                alpha=item.get('alpha', 1.0), label=item.get('label'), zorder=item.get('z', 3))
    ax.set_xlim(x[0], x[-1])
    ax.set_ylim(*ylim)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    handles, labels = ax.get_legend_handles_labels()
    keep = [(h, l) for h, l in zip(handles, labels) if l and not l.startswith('_')]
    if keep:
        fig.legend(*zip(*keep), loc='outside lower left', ncols=1, handlelength=2.2)
    return fig


def figures_gt24(plt):
    audit = load('gt24-c02-ankle-sign.json')
    pool = [(t, s) for t in audit['trials'] for s in t['sides']
            if 'moment_source_Nm_kg' in s.get('curves', {}) and s['stances_with_finite_moment'] >= 5]
    trial, side = random.Random(SEED).choice(pool)
    c = side['curves']
    x = np.linspace(0, 100, len(c['moment_source_Nm_kg']))
    src, pred = np.array(c['moment_source_Nm_kg']), np.array(c['moment_df_prediction_Nm_kg'])
    lim = (min(src.min(), pred.min(), -pred.max()) - 0.25, max(src.max(), pred.max(), -pred.min()) + 0.25)
    common = dict(x=x, xlabel='Stance (%)', ylabel='Ankle moment (N·m/kg)', ylim=lim)
    published = {'y': src, 'color': INK, 'lw': 2.2, 'label': 'Published ankle moment'}
    before = line_figure(plt, **common, lines=[published, {
        'y': -pred, 'color': BEFORE, 'ls': '--', 'label': 'Force plates, plantarflexor positive (README)'}])
    after = line_figure(plt, **common, lines=[published, {
        'y': pred, 'color': AFTER, 'ls': '--', 'label': 'Force plates, dorsiflexor positive (LocoHub)'}])
    condition = trial['condition']
    example = (f'{trial["subject"]}, {condition}, {"left" if side["side"] == "l" else "right"} leg: '
               f'mean of {side["stances_with_finite_moment"]} stances, one of {len(pool)} legs drawn with seed {SEED}.')
    return before, after, example, len(pool)


def figures_gt23_units(plt):
    audit = load('gt23-c02-moment-units.json')
    masses = load('gt23-c03-normalizing-mass.json')['subjects']
    own_mass_subjects = {s for s, v in masses.items() if v['readme_consistent']}
    pool = [(t, s) for t in audit['trials'] for s in t['sides']
            if s.get('example_stance') and t['subject'] in own_mass_subjects]
    trial, side = random.Random(SEED).choice(pool)
    src = np.array(side['example_stance']['source'])
    est = np.array(side['example_stance']['estimate_Nm'])
    mass = trial['readme_mass_kg']
    x = np.linspace(0, 100, len(src))
    pad = lambda lo, hi: (lo - 0.08 * (hi - lo), hi + 0.08 * (hi - lo))
    before = line_figure(plt, x, 'Stance (%)', 'Ankle moment (N·m)', pad(min(est.min(), src.min()), max(est.max(), src.max(), 0)), lines=[
        {'y': src, 'color': INK, 'lw': 2.2, 'label': 'Published values, read as N·m (README)'},
        {'y': est, 'color': BEFORE, 'ls': '--', 'label': 'Force plates (N·m)'}])
    after = line_figure(plt, x, 'Stance (%)', 'Ankle moment (N·m/kg)', pad(min(src.min(), (est / mass).min()), max(src.max(), (est / mass).max(), 0)), lines=[
        {'y': src, 'color': INK, 'lw': 2.2, 'label': 'Published values, read as N·m/kg'},
        {'y': est / mass, 'color': AFTER, 'ls': '--', 'label': f'Force plates ÷ {mass:g} kg body mass'}])
    example = (f'{trial["subject"]}, {trial["task"]}, {"left" if side["side"] == "l" else "right"} leg, '
               f'one stance; drawn with seed {SEED} from the {len(pool)} sampled legs of participants whose own mass '
               'was the divisor, so the units question is shown alone.')
    return before, after, example


def figure_gt23_mass(plt):
    subjects = load('gt23-c03-normalizing-mass.json')['subjects']
    names = sorted(subjects)
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 4.4), layout='constrained')
    ys = np.arange(len(names))[::-1]
    for y, name in zip(ys, names):
        row = subjects[name]
        used, own = row['divisor_kg_best'], row['readme_mass_kg']
        wrong = not row['readme_consistent']
        exact = row['divisor_basis'].startswith('local N*m re-run')
        ax.plot([used, own], [y, y], color=GREY, lw=1.4, zorder=1)
        ax.plot(used, y, 's' if exact else '^', color=BEFORE if wrong else MUTED, ms=7, zorder=3)
        ax.plot(own, y, 'o', mfc='white', mec=AFTER, mew=1.8, ms=8, zorder=2)
    ax.set_yticks(ys)
    ax.set_yticklabels(names)
    ax.set_xlabel('Body mass (kg)')
    ax.set_ylim(-0.7, len(names) - 0.3)
    ax.grid(axis='x', color=GREY, lw=0.4, alpha=0.6)
    handles = [
        plt.Line2D([], [], ls='', marker='s', color=BEFORE, ms=7, label='Before: mass the moments were divided by (exact)'),
        plt.Line2D([], [], ls='', marker='^', color=BEFORE, ms=7, label='Before: same, estimated from force plates'),
        plt.Line2D([], [], ls='', marker='o', mfc='white', mec=AFTER, mew=1.8, ms=8, label="After: participant's own mass"),
        plt.Line2D([], [], ls='', marker='s', color=MUTED, ms=7, label='Divisor consistent with own mass (grey)')]
    fig.legend(handles=handles, loc='outside lower left', handletextpad=0.4)
    wrong = [n for n in names if not subjects[n]['readme_consistent']]
    factors = [subjects[n]['scale_factor_published_vs_readme_normalized'] for n in wrong]
    return fig, len(wrong), len(names), min(factors), max(factors)


def figures_um21_branch(plt):
    census = load('um21-c03-episode-census.json')['figure_episode']
    episode = load('um21-c03-conventions.json')['ankle_episode_census']['branch_episode']
    as_array = lambda rows: np.array([[np.nan if v is None else v for v in row] for row in rows], float)
    outside, raw, fixed = as_array(census['outside_strides']), as_array(census['inside_raw']), as_array(census['inside_reexpressed'])
    jumps = episode['orientation_step_over_20deg_frames_1based']
    keep = [i for i, (a, b) in enumerate(census['inside_pairs']) if not any(a <= f <= b for f in jumps)]
    if len(keep) != episode['inside_strides_without_orientation_step_over_20deg']:
        raise ValueError('kept-stride count disagrees with the audit')
    x = np.linspace(0, 100, outside.shape[1])
    label_bg = {'y': outside[0], 'color': GREY, 'lw': 0.8, 'label': f'{census["n_outside"]} strides outside the stretch'}
    before = line_figure(plt, x, 'Stride (%)', 'Ankle angle (deg)', (-215, 45), background=outside, lines=[label_bg] + [
        {'y': raw[i], 'color': BEFORE, 'lw': 0.9, 'alpha': 0.8, 'label': None if i else f'{len(raw)} strides inside, as published'}
        for i in range(len(raw))])
    after = line_figure(plt, x, 'Stride (%)', 'Ankle angle (deg)', (-35, 45), background=outside, lines=[label_bg] + [
        {'y': fixed[i], 'color': AFTER, 'lw': 0.9, 'alpha': 0.8, 'label': None if n else f'{len(keep)} strides inside, re-expressed'}
        for n, i in enumerate(keep)])
    return before, after, len(raw), len(keep), episode['frames']


def figures_um21_pelvis(plt):
    audit = load('um21-p01-pelvis-heading.json')
    curves = audit['seeded_picks']['curves']['AB04/i0']
    side = random.Random(SEED).choice(sorted(curves))
    c = curves[side]
    marker, stored = np.array(c['marker_tilt']), np.array(c['stored_tilt'])
    x = np.linspace(0, 100, len(marker))
    lim = (min(marker.min(), stored.min()) - 1.5, max(marker.max(), stored.max()) + 1.5)
    ylabel = 'Pelvis tilt (deg), forward tilt +'
    before = line_figure(plt, x, 'Stride (%)', ylabel, lim, lines=[
        {'y': stored, 'color': INK, 'lw': 2.2, 'label': 'Published pelvis tilt'},
        {'y': marker, 'color': BEFORE, 'ls': '--', 'label': 'Tilt from pelvis markers'}])
    after = line_figure(plt, x, 'Stride (%)', ylabel, lim, lines=[
        {'y': -stored, 'color': INK, 'lw': 2.2, 'label': 'Published pelvis tilt × −1'},
        {'y': marker, 'color': AFTER, 'ls': '--', 'label': 'Tilt from pelvis markers'}])
    frames = c['frames_1based']
    example = (f'{"Right" if side == "R" else "Left"} side, frames {frames[0]}–{frames[1]}: the stride the census drew with seed '
               f'{audit["seeded_picks"]["seed"]}; side drawn with seed {SEED}.')
    rows = [r for r in audit['records'] if r['subject'] == 'AB04' and r['condition'] == 'i0'][0]['sides']
    return before, after, example, rows


def figures_um21_thigh(plt):
    audit = load('um21-c01-source-probe.json')
    stride = audit['random_stride']
    hip, pelvis, marker = (np.array(stride[k]) for k in ('hip', 'pelvis', 'marker_thigh'))
    x = np.linspace(0, 100, len(hip))
    old, new = pelvis + hip, hip - pelvis
    lim = (min(old.min(), new.min(), marker.min()) - 4, max(old.max(), new.max(), marker.max()) + 4)
    ylabel = 'Thigh angle (deg), knee forward +'
    before = line_figure(plt, x, 'Stride (%)', ylabel, lim, lines=[
        {'y': old, 'color': INK, 'lw': 2.2, 'label': 'LocoHub rebuild code (unreleased): pelvis + hip'},
        {'y': marker, 'color': BEFORE, 'ls': '--', 'label': 'Thigh from hip and knee markers'}])
    after = line_figure(plt, x, 'Stride (%)', ylabel, lim, lines=[
        {'y': new, 'color': INK, 'lw': 2.2, 'label': "Authors' recipe: hip − pelvis"},
        {'y': marker, 'color': AFTER, 'ls': '--', 'label': 'Thigh from hip and knee markers'}])
    example = (f'{stride["trial"].replace("/", " ")} {stride["side"]} leg, frames {stride["start_frame"]}–{stride["end_frame"]}: '
               f'the stride the audit drew with seed {audit["seed"]}.')
    return before, after, example, float(np.median(pelvis))


def figure_um21_clock(plt):
    census = load('um21-t02-clock-census.json')
    records = sorted(census['records'], key=lambda r: (r['subject'], r['condition']))
    band = census['audit_rule']['tolerances']['belt_clock_best_lag_frames_abs_max'] / 100   # 100 Hz joint frames
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 3.6), layout='constrained')
    ax.axhspan(-band, band, color=AFTER, alpha=0.12, lw=0, zorder=0)
    floor = -6.2
    missing = []
    for i, r in enumerate(records):
        lag = r['alignment']['best_lag']
        name = f'{r["subject"]} {r["condition"]}'
        if lag is None:
            ax.plot(i, floor, 'x', color=BEFORE, ms=7, mew=1.8, zorder=3)
            missing.append((i, name))
        elif r['alignment']['passed']:
            ax.plot(i, lag / 100, 'o', color=MUTED, ms=4, zorder=2)
        else:
            ax.plot(i, lag / 100, 's', color=BEFORE, ms=6, zorder=3)
            ax.annotate(name, (i, lag / 100), xytext=(5, -4), textcoords='offset points', fontsize=10, color=BEFORE)
    ax.annotate(', '.join(n for _, n in missing), (missing[0][0], floor), xytext=(-8, 0), textcoords='offset points',
                ha='right', va='center', fontsize=10, color=BEFORE)
    ax.set_yticks([-4, -2, 0, 2, 4, 6])
    subjects = sorted({r['subject'] for r in records})
    ax.set_xticks([np.mean([i for i, r in enumerate(records) if r['subject'] == s]) for s in subjects])
    ax.set_xticklabels([s.replace('AB', '') for s in subjects])
    ax.set_xlabel('Participant (AB01–AB10), five recordings each')
    ax.set_ylabel('Task-clock offset (s)')
    ax.set_xlim(-1, len(records))
    ax.set_ylim(floor - 0.6, 8)
    ax.axhline(floor + 0.7, color=GREY, lw=0.6, ls=':')
    handles = [
        plt.Line2D([], [], ls='', marker='s', color=BEFORE, ms=6, label='Fails: offset outside the band (leaves release)'),
        plt.Line2D([], [], ls='', marker='x', color=BEFORE, ms=7, mew=1.8, label='Fails: no belt-speed record to check'),
        plt.Line2D([], [], ls='', marker='o', color=MUTED, ms=4, label='Passes (kept)'),
        plt.Rectangle((0, 0), 1, 1, color=AFTER, alpha=0.12, label=f'Accepted band, ±{band:g} s')]
    fig.legend(handles=handles, loc='outside lower left')
    failed = [r for r in records if not r['alignment']['passed']]
    measured = [abs(r['alignment']['best_lag']) / 100 for r in failed if r['alignment']['best_lag'] is not None]
    passed = [abs(r['alignment']['best_lag']) / 100 for r in records if r['alignment']['passed']]
    return fig, len(records), len(measured), min(measured), max(measured), len(failed) - len(measured), max(passed)


def figure_um21_slope(plt):
    audit = load('um21-midstance-slope.json')
    records = audit['records']
    tol = audit['tolerances']['belt_path']['tol_deg']
    subjects = sorted({r['subject'] for r in records})
    offset = {s: (i - (len(subjects) - 1) / 2) * 0.32 for i, s in enumerate(subjects)}   # fixed spread, not random
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 3.9), layout='constrained')
    line = np.array([-12.5, 12.5])
    ax.fill_between(line, line - tol, line + tol, color=GREY, alpha=0.25, lw=0, zorder=0)
    ax.plot(line, line, color=GREY, lw=0.8, zorder=1)
    for r in records:
        x, y = r['label_deg'] + offset[r['subject']], r['belt_path']['median']
        if r['record'] == 'AB01/i5':
            ax.plot(x, y, 's', color=BEFORE, ms=8, zorder=4)
            ax.annotate('AB01 i5', (x, y), xytext=(-8, 6), textcoords='offset points', ha='right', fontsize=10, color=BEFORE)
        elif r['record'] == 'AB01/i10':
            ax.plot(x, y, 'o', mfc='white', mec=AFTER, mew=1.8, ms=8, zorder=4)
            ax.annotate('AB01 i10', (x, y), xytext=(-8, 6), textcoords='offset points', ha='right', fontsize=10, color=AFTER)
        else:
            ax.plot(x, y, 'o', color=MUTED, ms=4, zorder=2)
    ax.set_xticks([-10, -5, 0, 5, 10])
    ax.set_xlim(-12.5, 12.5)
    ax.set_ylim(-12.5, 12.5)
    ax.set_xlabel('Labelled slope (deg)')
    ax.set_ylabel('Slope measured from foot path (deg)')
    handles = [
        plt.Line2D([], [], ls='', marker='s', color=BEFORE, ms=8, label='AB01 i5: copy of i10 (leaves release)'),
        plt.Line2D([], [], ls='', marker='o', mfc='white', mec=AFTER, mew=1.8, ms=8, label='AB01 i10 (kept; resolution logged)'),
        plt.Line2D([], [], ls='', marker='o', color=MUTED, ms=4, label='Other 48 recordings'),
        plt.Rectangle((0, 0), 1, 1, color=GREY, alpha=0.25, label=f'Measured = label ± {tol:g}°')]
    fig.legend(handles=handles, loc='outside lower left')
    pick = {r['record']: r for r in records}
    others = [r for r in records if r['record'] not in ('AB01/i5', 'AB01/i10')]
    flagged = [r['record'] for r in others if abs(r['belt_path']['median'] - r['label_deg']) > tol]
    return fig, pick['AB01/i5']['belt_path']['median'], pick['AB01/i5']['plate_force']['median'], len(others), flagged


# ------------------------------------------------------------------- cards

def gate(task_id, verify_name, backlog):
    """True only when the task is done and the independent verification says done."""
    tasks = {t['id']: t for t in backlog['tasks']}
    task = tasks.get(task_id)
    path = HANDOFFS / f'{verify_name}-verify.json'
    if task is None or task.get('status') != 'done' or not path.is_file():
        return None
    verify = json.loads(path.read_text(encoding='utf-8'))
    verdict = verify.get('verdict', verify.get('status'))
    if verdict != 'done':
        return None
    return verify.get('last_checked_at_utc', '')[:10]


APPROVAL = 'José approved showing it on 2026-10-31'
APPROVED_EXCEPTIONS = {
    'um21-belt-clock': {'task': 'UM21-T02', 'requires': [
        ('UM21-T02-audit-verify', 'done_for_audit_script', ('round_2', '3. Independent lag spot-check'), 'um21-t02-clock-census.json')]},
    'um21-ab01-copy': {'task': 'UM21-T02', 'requires': [
        ('UM21-SLOPE-verify', 'done', None, None),
        ('UM21-T02-audit-verify', 'done_for_audit_script', ('round_2', '4. Duplicate claim'), None)],
        # The release handling is the coordinator's logged resolution under D-UM21-T02-1 = A
        # (D-UM21-T02-2 withdrawn); it must still be in UM21-T02's handoff.remaining.
        'backlog_remaining': ('Coordinator resolution (2026-10-31): D-UM21-T02-2 withdrawn',
                              'AB01 i10 passes the clock and slope checks and stays')},
}


def exception_gate(card_id, backlog):
    """Verification date when José's approved exception holds and its evidence is verified."""
    rule = APPROVED_EXCEPTIONS.get(card_id)
    tasks = {t['id']: t for t in backlog['tasks']}
    if rule is None or rule['task'] not in tasks:
        return None
    if 'backlog_remaining' in rule:
        remaining = tasks[rule['task']].get('handoff', {}).get('remaining', [])
        if not any(all(part in entry for part in rule['backlog_remaining']) for entry in remaining):
            return None
    dates = []
    for verify_name, verdict, item, reviewed_audit in rule['requires']:
        path = HANDOFFS / f'{verify_name}.json'
        if not path.is_file():
            return None
        verify = json.loads(path.read_text(encoding='utf-8'))
        if verify.get('verdict') != verdict:
            return None
        if item:
            round_ = verify.get(item[0], {})
            checks = [c for c in round_.get('checks', []) if c.get('item', '').startswith(item[1])]
            if len(checks) != 1 or not checks[0].get('result', '').startswith('pass'):
                return None
            dates.append(round_.get('last_checked_at_utc', '')[:10])
        else:
            dates.append(verify.get('last_checked_at_utc', '')[:10])
        if reviewed_audit:
            digest = hashlib.sha256((AUDITS / reviewed_audit).read_bytes()).hexdigest()
            reviewed = [v for r in ('round_1', 'round_2', 'round_3') for k, v in verify.get(r, {}).get('reviewed_sha256', {}).items()
                        if k.startswith(f'docs/quality/audits/{reviewed_audit}')]
            if digest not in reviewed:
                return None
    return max(dates)


def figure_html(name, side, alt, caption):
    return (f'<figure class="fix-figure"><figcaption class="fix-side fix-{side.split()[0].strip(":").lower()}">{ESC(side)}</figcaption>'
            f'<img src="fixes/{name}.svg" width="{SIZES[name][0]}" height="{SIZES[name][1]}" loading="lazy" alt="{ESC(alt)}">'
            + (f'<figcaption>{ESC(caption)}</figcaption>' if caption else '') + '</figure>')


def card_html(card, verified_on):
    figures = ''.join(figure_html(*f) for f in card['figures'])
    grid = 'fix-figures' + (' fix-figures-single' if len(card['figures']) == 1 else '')
    links = ' · '.join(f'<a href="{ESC(href)}">{ESC(text)}</a>' for text, href in card['evidence'])
    if card['id'] in APPROVED_EXCEPTIONS:
        verified_text = (f'Evidence independently verified {verified_on}. Task {card["task"]} is not done; '
                         f'{APPROVAL}.')
        rule = ' data-rule="approved-exception"'
    else:
        verified_text = f'Task {card["task"]}, independently verified {verified_on}.'
        rule = ''
    return f'''<article class="fix-card" id="{card['id']}" data-task="{card['task']}"{rule}>
<h2>{ESC(card['title'])}</h2>
<p class="fix-status"><span class="fix-label" data-status="{card['status'][0]}">{ESC(card['status'][1])}</span></p>
<p><strong>Cause.</strong> {card['cause']}</p>
<p><strong>LocoHub.</strong> {card['fix']}</p>
<div class="{grid}">{figures}</div>
<p class="fix-evidence">{ESC(card['example'])} Evidence: {links}. {verified_text}</p>
</article>'''


def build(write_figure):
    plt = plt_module()
    backlog = json.loads(BACKLOG.read_text(encoding='utf-8'))
    cards, skipped = [], []

    def add(card, verify_name=None):
        if card['id'] in APPROVED_EXCEPTIONS:
            verified_on = exception_gate(card['id'], backlog)
        else:
            verified_on = gate(card['task'], verify_name or card['task'], backlog)
        if verified_on is None:
            skipped.append(card['task'])
            return
        for name, fig in card.pop('svgs'):
            width, height = fig.get_size_inches() * 100
            SIZES[name] = (round(width), round(height))
            write_figure(name, svg_bytes(fig))
            plt.close(fig)
        cards.append(card_html(card, verified_on))
        outline.append((card['id'], card['short']))

    outline = []
    # Ordered by dataset, then by task id; not by importance.
    b, a, example, legs = figures_gt24(plt)
    add({'id': 'gt24-ankle-sign', 'task': 'GT24-C02', 'short': 'GT24 ankle sign',
         'title': 'Georgia Tech 2024: the ankle sign is the opposite of the README',
         'status': ('documented', 'Documented · values unchanged · no new GT24 release yet'),
         'cause': 'The dataset README says ankle plantarflexion is positive, but the published ankle angles and moments are '
                  f'dorsiflexion-positive: force-plate moments agree in sign and size in {legs} of {legs} sampled legs, and push-off work and '
                  'toe-walking postures agree too.',
         'fix': 'LocoHub keeps the published ankle values, which already match its dorsiflexion-positive columns, and does not '
                'apply the README sign. The hip and knee statements in the README are correct.',
         'svgs': [('gt24-ankle-before', b), ('gt24-ankle-after', a)],
         'figures': [('gt24-ankle-before', 'Before: read as the README says',
                      'The published ankle moment is a mirror image of the force-plate moment taken plantarflexor positive.', ''),
                     ('gt24-ankle-after', 'After: read as LocoHub does',
                      'The published ankle moment overlaps the force-plate moment taken dorsiflexor positive.', '')],
         'example': example,
         'evidence': [('ankle sign audit (JSON)', 'audits/gt24-c02-ankle-sign.json')]})

    b, a, example = figures_gt23_units(plt)
    add({'id': 'gt23-moment-units', 'task': 'GT23-C02', 'short': 'GT23 moment units',
         'title': 'Georgia Tech 2023: joint moments are per kilogram, not N·m',
         'status': ('documented', 'Documented · corrected files not yet released'),
         'cause': 'The README gives joint moments in N·m and powers in W, but the published values are already divided by body mass: '
                  'against force-plate moments in N·m they scale by 1/64 to 1/90 in all 8 sampled legs, never by 1.',
         'fix': 'LocoHub labels these values N·m/kg and W/kg and does not divide by mass a second time. Which mass was used is the next card.',
         'svgs': [('gt23-units-before', b), ('gt23-units-after', a)],
         'figures': [('gt23-units-before', 'Before: read as the README says',
                      'Read as N·m, the published ankle moment is a nearly flat line far smaller than the force-plate moment.', ''),
                     ('gt23-units-after', 'After: read as LocoHub does',
                      'Read as N·m/kg, the published ankle moment overlaps the force-plate moment divided by body mass.', '')],
         'example': example,
         'evidence': [('moment units audit (JSON)', 'audits/gt23-c02-moment-units.json')]})

    fig, n_wrong, n_all, lo, hi = figure_gt23_mass(plt)
    add({'id': 'gt23-normalizing-mass', 'task': 'GT23-C03', 'short': 'GT23 normalizing mass',
         'title': "Georgia Tech 2023: moments divided by another participant's mass",
         'status': ('decided', 'Correction decided · per-trial check planned · not yet released'),
         'cause': f'In {n_wrong} of {n_all} participants the published moments were not divided by the participant’s own body mass; '
                  'in most of them the divisor is exactly another participant’s listed mass, and it can change between trials of one participant. '
                  f'Level-walking moments are {lo:.2f} to {hi:.2f} times their correct per-kilogram value.',
         'fix': 'Each trial will be rescaled to its participant’s own mass after every trial’s divisor has been measured; trials '
                'whose divisor cannot be matched to a recorded mass will not be rescaled by guesswork.',
         'svgs': [('gt23-mass', fig)],
         'figures': [('gt23-mass', 'Before and after, per participant',
                      'For each of 12 participants, the mass their moments were divided by (filled marker) and their own body mass (open circle). '
                      'Nine filled markers sit away from their open circle.',
                      'Level walking. Squares: exact divisor from an N·m re-run that matches the published values; triangles: force-plate estimate. '
                      'Two participants (AB02, AB11) cannot be told apart from their own mass at this precision.')],
         'example': 'All 12 participants shown.',
         'evidence': [('normalizing mass audit (JSON)', 'audits/gt23-c03-normalizing-mass.json')]})

    b, a, n_inside, n_keep, frames = figures_um21_branch(plt)
    add({'id': 'um21-ankle-branch', 'task': 'UM21-C03', 'short': 'UM21 ankle 180° stretch',
         'title': 'UMich 2021: a 180° stretch in one right ankle',
         'status': ('decided', 'Correction decided · not yet released'),
         'cause': f'For {frames:,} frames of one recording’s right ankle (AB07, 10° incline), the published angles are the second, '
                  'equivalent solution of the same ankle orientation, which moves the sagittal angle by about 180°. '
                  'It is a choice of solution, not ankle motion.',
         'fix': f'Those frames will be re-expressed in the standard solution and each one logged; {n_inside - n_keep} of the {n_inside} '
                'strides inside the stretch also contain one-frame jumps that this cannot fix and will be left out. The other ankle channels '
                'and the source copy are unchanged.',
         'svgs': [('um21-ankle-before', b), ('um21-ankle-after', a)],
         'figures': [('um21-ankle-before', 'Before: as published',
                      'Strides inside the stretch sit near minus 160 degrees, far below the strides outside it.', ''),
                     ('um21-ankle-after', 'After: re-expressed',
                      'Re-expressed strides fall on the strides outside the stretch. The vertical scale differs from the Before figure.',
                      'Vertical scale differs from the Before figure.')],
         'example': f'All strides of the right ankle in this recording; {n_keep} of {n_inside} inside strides kept.',
         'evidence': [('episode census (JSON)', 'audits/um21-c03-episode-census.json'),
                      ('convention audit (JSON)', 'audits/um21-c03-conventions.json')]})

    b, a, example, sides = figures_um21_pelvis(plt)
    votes = sides['R']['tilt_votes']
    add({'id': 'um21-reversed-pelvis', 'task': 'UM21-P01', 'short': 'UM21 reversed pelvis',
         'title': 'UMich 2021: one recording’s pelvis computed facing backwards',
         'status': ('decided', 'Correction decided · not yet applied or released'),
         'cause': 'In one of 50 treadmill recordings (AB04, level walking), the motion-capture software computed the pelvis facing '
                  f'backwards (heading about 180°), so the published pelvis tilt has the wrong sign in {votes["flipped_sign"]} of '
                  f'{votes["strides_voting"]} right-side strides, as do obliquity and the thigh and shank angles built on it. '
                  'Hip, knee and ankle angles and moments are unaffected.',
         'fix': 'For that recording only, pelvis tilt will be sign-flipped from the marker evidence and thigh and shank recomputed '
                'from it; the change is logged per recording.',
         'svgs': [('um21-pelvis-before', b), ('um21-pelvis-after', a)],
         'figures': [('um21-pelvis-before', 'Before: as published',
                      'Published pelvis tilt is the mirror image of tilt computed from the pelvis markers.', ''),
                     ('um21-pelvis-after', 'After: sign corrected',
                      'Published pelvis tilt times minus one overlaps the marker tilt.',
                      'Shown with the source sign (forward tilt positive); LocoHub files store pelvis tilt with the opposite sign by rule.')],
         'example': example,
         'evidence': [('pelvis heading census (JSON)', 'audits/um21-p01-pelvis-heading.json')]})

    b, a, example, tilt = figures_um21_thigh(plt)
    add({'id': 'um21-thigh-recipe', 'task': 'UM21-C01', 'short': 'UM21 thigh and shank',
         'title': 'UMich 2021: thigh and shank angles from the wrong pelvis sign',
         'status': ('decided', 'Recipe decided · not yet released'),
         'cause': 'LocoHub’s treadmill rebuild code (not released) adds pelvis tilt to hip flexion using the source’s pelvis sign (forward tilt positive). '
                  'The thigh angle is hip flexion minus that tilt, as in the authors’ own recipe, so the rebuild’s values are off by about '
                  'twice the pelvic tilt. The legacy UMich download used a different recipe and is not shown here.',
         'fix': 'Thigh = hip − pelvis and shank = hip − pelvis − knee, to be released as planar estimates under the standard names. '
                'Under LocoHub’s sign rule, where forward pelvis tilt is negative, this is thigh = pelvis + hip.',
         'svgs': [('um21-thigh-before', b), ('um21-thigh-after', a)],
         'figures': [('um21-thigh-before', 'Before: LocoHub rebuild code (unreleased)',
                      'Pelvis plus hip runs far above the thigh angle from markers for the whole stride.', ''),
                     ('um21-thigh-after', 'After: authors’ recipe',
                      'Hip minus pelvis follows the thigh angle from markers within a few degrees.',
                      'The marker thigh uses the greater trochanter, not the hip centre, so a few degrees of offset is expected.')],
         'example': example + f' Pelvis tilt in this stride: median {tilt:.0f}°.',
         'evidence': [('thigh/shank probe (JSON)', 'audits/um21-c01-source-probe.json'),
                      ('field policy (JSON)', 'audits/um21-c01-tread-conventions.json')]})

    fig, n_rec, n_off, lo, hi, n_missing, aligned_max = figure_um21_clock(plt)
    add({'id': 'um21-belt-clock', 'task': 'UM21-T02', 'short': 'UM21 task-clock offset',
         'title': 'UMich 2021: treadmill task intervals on an offset clock',
         'status': ('decided', 'Correction decided · not yet released'),
         'cause': 'The published task intervals (when belt speed or incline changes) are timed on the belt-speed record, not on the motion data. '
                  f'In {n_off} of {n_rec} treadmill recordings that clock is {lo:.1f} to {hi:.1f} s off the motion data, measured from the '
                  f'heel and toe marker speed, so strides near a change get the wrong task label; {n_missing} recordings have no belt-speed '
                  f'record and cannot be checked. The others agree within {aligned_max:.1f} s.',
         'fix': 'Recordings that fail this check leave the treadmill release; no interval is shifted or estimated. One of them, AB01 i5, '
                'is also a copy of another recording (next card).',
         'svgs': [('um21-clock', fig)],
         'figures': [('um21-clock', 'Before and after, per recording',
                      'Task-clock offset for each of 50 treadmill recordings. Most sit inside a narrow accepted band around zero; four sit '
                      '1.7 to 7 seconds away and two cannot be checked. Those six leave the release.',
                      'Offset that best aligns the belt-speed record with belt speed measured from heel and toe markers. Crosses at the '
                      'bottom have no belt-speed record; their position is not a value.')],
         'example': 'All 50 treadmill recordings shown.',
         'evidence': [('clock census (JSON)', 'audits/um21-t02-clock-census.json')]})

    fig, i5_foot, i5_plate, n_other, flagged = figure_um21_slope(plt)
    if flagged:
        raise ValueError(f'unexplained slope flags: {flagged}')
    add({'id': 'um21-ab01-copy', 'task': 'UM21-T02', 'short': 'UM21 AB01 duplicate',
         'title': 'UMich 2021: the AB01 5° incline recording is a copy of the 10° one',
         'status': ('decided', 'Copy removed from release scope (coordinator resolution under D-UM21-T02-1 = A) · not yet released'),
         'cause': 'The AB01 recording labelled 5° incline contains the same motion, joint and force-plate data, byte for byte, as the AB01 '
                  f'10° recording; only its task timing differs. The walking slope measured from it is {i5_foot:.1f}° from the foot path '
                  f'and {i5_plate:.1f}° from the force plates, not 5°. The other {n_other} recordings match their labels within the foot-path tolerance.',
         'fix': 'The 5° copy fails the clock check, so it leaves the treadmill release under the decision to drop such recordings. '
                'The 10° recording passes the slope and clock checks and stays, with a note that its data also appear under the 5° '
                'label. This handling is the coordinator\u2019s logged resolution; José can still ask to drop the 10° recording too.',
         'svgs': [('um21-slope', fig)],
         'figures': [('um21-slope', 'Before and after, per recording',
                      'Measured walking slope against labelled slope for 50 treadmill recordings. All lie on the diagonal except AB01 i5, '
                      'labelled 5 degrees but measured at 10, on top of AB01 i10.',
                      'Recordings are spread sideways by participant so they do not overlap; the spread is fixed, not data. '
                      'The force plates read low in AB03 and AB10 (a separate shortfall documented in the slope audit), so the figure '
                      'uses the foot-path slope.')],
         'example': 'All 50 treadmill recordings shown.',
         'evidence': [('slope check (JSON)', 'audits/um21-midstance-slope.json'),
                      ('clock census, duplicate list (JSON)', 'audits/um21-t02-clock-census.json'),
                      ('logged resolution (backlog)', '../maintainers/backlog.html#UM21-T02')]})

    if not cards:
        raise SystemExit('No verified cards; refusing to write an empty page.')
    sign_ok = gate('DOC-03', 'DOC-03', backlog)
    context = ''
    if sign_ok:
        context = f'''<section class="fix-context" id="sign-rule" data-task="DOC-03">
<h2>Context: one sign rule for every dataset</h2>
<p>Several cards are about which sign a dataset uses. LocoHub columns follow one written <a href="../reference/index.html#signs-and-frames">sign rule</a>: segment angles are positive counterclockwise with the person facing right, and joint angles and moments are positive in their named direction (hip flexion, knee flexion, ankle dorsiflexion). Pelvis forward tilt is therefore negative in LocoHub files although many sources report it as positive. This is a convention, not an error in any dataset.</p>
<p class="fix-status"><span class="fix-label" data-status="documented">Adopted {AS_OF} · current downloads are legacy and predate it</span></p>
<figure class="fix-figure fix-sign"><img src="../assets/sagittal-signs.svg" width="400" height="600" loading="lazy" alt="Side view of a person facing right with +x forward, +y up and +z out of the page; curved arrows show the positive direction of each segment and joint angle."><figcaption>The sign rule from the file-format reference. Task DOC-03, independently verified {sign_ok}.</figcaption></figure>
</section>'''
        outline.append(('sign-rule', 'Sign rule (context)'))
    return cards, context, outline, skipped


def page_html(cards, context, outline):
    nav = ''.join(f'<li><a href="#{i}">{ESC(t)}</a></li>' for i, t in outline)
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Data problems LocoHub found in source datasets and earlier conversions, shown before and after correction.">
  <meta name="color-scheme" content="light dark">
  <title>Broken vs fixed data · LocoHub</title>
  <link rel="stylesheet" href="../stylesheets/site.css">
  <link rel="stylesheet" href="../stylesheets/fixes.css">
  <script src="../javascripts/extra.js" defer></script>
</head>
<!-- Generated by contributor_tools/build_fixes_page.py from committed audit records. Edit the builder, not this file. -->
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header">
    <div class="header-inner">
      <a class="wordmark" href="../index.html" aria-label="LocoHub home">LocoHub</a>
      <nav class="primary-nav" aria-label="Main navigation"><a href="../index.html">Data</a>
<a href="../tutorials/index.html">Tutorials</a>
<a href="../reference/index.html">File format</a>
<a href="index.html" aria-current="page">Testing &amp; data quality</a></nav>
      <form class="header-search" role="search" aria-label="Site search" action="../search/index.html"><label class="visually-hidden" for="header-query">Search documentation</label><input id="header-query" type="search" name="q" placeholder="Search docs" required><button type="submit">Search</button></form>
      <a class="repository-link" href="https://github.com/jmontp/LocoHub">GitHub</a>
    </div>
  </header>
  <div class="page-layout">
    <main id="main" class="page-content" tabindex="-1">
      <div class="page-kicker"><a href="../index.html">LocoHub</a><span aria-hidden="true">/</span><a href="index.html">Testing &amp; data quality</a><span aria-hidden="true">/</span>Broken vs fixed data</div>
<h1>Broken vs fixed data</h1>
<p class="fix-intro">Each card shows one problem LocoHub found in a source dataset or in LocoHub’s own unreleased rebuild code. The <em>Before</em> figure shows the data as published, or as LocoHub’s unreleased build computed it; the <em>After</em> figure shows what LocoHub will release. Both are drawn against the same independent check, such as force plates or markers.</p>
<p class="catalog-note"><strong>Most corrections are not in downloadable files yet.</strong> Each card states its status. A card means the finding was reproduced by a second, independent reviewer; it is not scientific approval of the dataset.</p>
{''.join(cards)}
{context}
<p class="audit-limitation fix-footnote">Status as of {AS_OF}. Figures are drawn only from values stored in the linked audit records; no data were re-read to make this page. Findings still under review are not shown. <a href="index.html">Back to testing &amp; data quality</a>.</p>
    </main>
    <aside class="page-outline" aria-label="On this page"><p>On this page</p><ol>{nav}</ol></aside>
  </div>
  <footer class="site-footer"><p>LocoHub</p><nav aria-label="Additional links"><a href="../contributing/index.html">Contribute data</a><a href="../maintainers/index.html">Maintainers</a><a href="../reference/index.html#release-evidence">Download notes</a><a href="https://github.com/jmontp/LocoHub/issues">Report an issue</a></nav></footer>
</body>
</html>
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--check', action='store_true', help='Fail if the page or a figure differs from a fresh build.')
    args = parser.parse_args()
    produced = {}
    cards, context, outline, skipped = build(lambda name, data: produced.__setitem__(FIG_DIR / f'{name}.svg', data))
    produced[PAGE] = page_html(cards, context, outline).encode('utf-8')
    for task in skipped:
        print(f'skipped {task}: task not done or verification not done', file=sys.stderr)
    if args.check:
        stale = [p for p, data in produced.items() if not p.is_file() or p.read_bytes() != data]
        if stale:
            raise SystemExit('Stale: ' + ', '.join(str(p.relative_to(ROOT)) for p in stale))
        print(f'Current: {len(cards)} cards, {len(produced) - 1} figures.')
        return
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    for path, data in produced.items():
        path.write_bytes(data)
    print(f'Wrote {PAGE.relative_to(ROOT)} with {len(cards)} cards and {len(produced) - 1} figures.')


if __name__ == '__main__':
    main()
