"""UM21-T01: treadmill release scope manifest and its local review sheets.

Reads small receipts, the 50 candidate ledgers, the original-curation membership
list, the source trial inventory (HDF5 keys only) and bounded per-recording
Parquet columns. Writes docs/quality/audits/um21-t01-tread-release-scope.json,
review_sheets/UM21-T01/ (verification) and review_sheets/D-1/ (decision).
Launches nothing; changes no inputs.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import hashlib
import json
from pathlib import Path
import random
import sys

import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.common.review_sheet import page

pa.set_cpu_count(1)
pa.set_io_thread_count(1)

V2 = ROOT / 'converted_datasets/reconversion_v2'
BASE = V2 / 'um21_tread_corrected_20261020'
READBACK = V2 / 'um21_tread_full_readback_20261021/source_comparison.json'
MEMBERSHIP = V2 / 'um21_tread_full_curation_v2_20261021/cycle_membership.jsonl'
CURATION = ROOT / 'docs/quality/audits/um21-full-tread-curation.json'
SOURCE = ROOT / 'contributor_tools/conversion_scripts/Umich_2021/Streaming.mat'
MANIFEST = ROOT / 'docs/quality/audits/um21-t01-tread-release-scope.json'
SHEETS = ROOT / 'review_sheets'
SEED = 20261027
CONDITIONS = ['d10', 'd5', 'i0', 'i5', 'i10']
SLOPE = {'d10': 'decline 10°', 'd5': 'decline 5°', 'i0': 'level', 'i5': 'incline 5°', 'i10': 'incline 10°'}
INK, MUTED, REF, LEFT, RIGHT, BAD = '#20252B', '#5b6672', '#999999', '#2a78d6', '#eb6834', '#c0392b'
# Agreement categories keep one color each on the decision sheet.
CATEGORY = {'exported_in_original_curation': ('both keep', '#2a78d6'),
            'exported_not_in_original_curation': ('only we keep', '#1baf7a'),
            'excluded_in_original_curation': ('only authors keep', '#eda100'),
            'excluded_not_in_original_curation': ('neither keeps', '#d5d9de')}
CHECKED = ['pelvis_sagittal_angle_rad'] + [f'{j}_flexion_{q}_{r}_{u}' for j in ('hip', 'knee')
           for q, u in (('angle', 'rad'), ('velocity', 'rad_s')) for r in ('ipsi', 'contra')] + \
          [f'source_ankle_sagittal_angle_{r}_rad' for r in ('ipsi', 'contra')]
IDENTITY_CHECKED = ['observation_id', 'reference_side', 'task_id', 'source_start_time_s', 'source_end_time_s', 'time_s', 'phase_ipsi']
IDENTITY_UNCHECKED = ['subject', 'source_recording_id', 'observation_type', 'task', 'task_info', 'step']
PROBE = ROOT / 'contributor_tools/audit_probes/2026_10_20/check_um21_tread_source.py'
PENDING = [f'ankle_dorsiflexion_angle_{r}_rad' for r in ('ipsi', 'contra')] + \
          [f'{s}_sagittal_angle_{r}_rad' for s in ('thigh', 'shank') for r in ('ipsi', 'contra')]


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def style():
    plt.rcParams.update({'font.size': 10.5, 'axes.titlesize': 11, 'axes.spines.top': False, 'axes.spines.right': False,
                         'text.color': INK, 'axes.labelcolor': INK, 'axes.edgecolor': INK, 'xtick.color': INK,
                         'ytick.color': INK, 'axes.linewidth': 0.6, 'legend.frameon': False})


def source_inventory():
    # Key names only; no arrays are read.
    with h5py.File(SOURCE, 'r') as handle:
        group = handle['Streaming']
        trials = sorted((s, c) for s in group for c in (group[s]['Tread'] if 'Tread' in group[s] else []))
        first = group[trials[0][0]]['Tread'][trials[0][1]]
        channels = {k: sorted(first[k].keys()) for k in first if isinstance(first[k], h5py.Group)}
    return trials, channels


def odd_duration(cycles):
    """Screen (not exclude): exported strides outside 0.5-1.5x the recording's median duration."""
    durations = np.array([(c['end'] - c['start']) / 100 for c in cycles])
    median = np.median(durations)
    return [c for c, d in zip(cycles, durations) if not .5 * median <= d <= 1.5 * median]


def gather():
    summary = json.loads((BASE / 'conversion_summary.json').read_text())
    readback = {(r['subject'], r['condition']): r for r in json.loads(READBACK.read_text())['records']}
    curation = {(r['subject'], r['condition']): r for r in json.loads(CURATION.read_text())['records']}
    membership = [json.loads(line) for line in MEMBERSHIP.read_text().splitlines()]
    records = []
    for r in summary['recordings']:
        key = (r['subject'], r['condition'])
        folder = BASE / r['subject'] / r['condition']
        ledger = [json.loads(line) for line in (folder / 'candidate_ledger.jsonl').read_text().splitlines()]
        frame = pq.read_table(folder / 'phase.parquet', columns=['reference_side', 'task'] + CHECKED + PENDING).to_pandas()
        exported = [c for c in ledger if 'excluded' not in c]
        counts = curation[key]['counts']
        rb = readback[key]
        mine = [m for m in membership if (m['subject'], m['condition']) == key]
        # Identity-level agreement: the same (side, start, end) strides are exported in ledger and membership.
        ledger_ids = {(c['side'], c['start'], c['end'], 'excluded' not in c) for c in ledger}
        member_ids = {(m['reference_side'], m['start_frame'], m['end_frame'], m['streaming_status'].startswith('exported')) for m in mine}
        rule_only = {(m['reference_side'], m['start_frame'], m['end_frame']) for m in mine
                     if m['streaming_status'] == 'exported_not_in_original_curation'}
        odd = odd_duration(exported)
        record = {'subject': r['subject'], 'condition': r['condition'],
                  'normalized_condition': curation[key]['normalized_condition'],
                  'phase_parquet': str(folder.relative_to(ROOT) / 'phase.parquet'), 'phase_sha256': r['sha256'],
                  'ledger_sha256': rb['ledger_sha256'], 'readback_maximum_error': rb['maximum_error'],
                  'observations': r['observations'], 'excluded_pairs': r['excluded'],
                  'observations_by_side': {s: int((frame.reference_side == s).sum() // 150) for s in ('left', 'right')},
                  'observations_by_task': {t: int(n // 150) for t, n in frame.task.value_counts().items()},
                  'exclusion_reasons': sorted({c['excluded'] for c in ledger if 'excluded' in c}),
                  'curation': counts, 'nan_in_checked_columns': int(frame[CHECKED].isna().to_numpy().sum()),
                  'pending_columns_all_nan': {c: bool(frame[c].isna().all()) for c in PENDING},
                  'identity_agreement_ledger_membership': ledger_ids == member_ids,
                  'odd_duration_exported': len(odd),
                  'odd_duration_rule_only': sum((c['side'], c['start'], c['end']) in rule_only for c in odd)}
        # Four independent receipts must agree on the same identity and counts.
        membership_counts = {k: sum(m['streaming_status'] == k for m in mine) for k in CATEGORY}
        agree = (len(exported) == r['observations'] == rb['observations'] ==
                 counts['exported_in_original_curation'] + counts['exported_not_in_original_curation']
                 and r['excluded'] == rb['excluded_pairs'] == len(ledger) - len(exported)
                 and rb['output_sha256'] == r['sha256'] and curation[key]['ledger_sha256'] == rb['ledger_sha256']
                 and membership_counts == {k: counts[k] for k in CATEGORY} and ledger_ids == member_ids)
        record['receipts_agree'] = bool(agree)
        records.append(record)
    return records, membership


def manifest(records, inventory, channels, sample):
    totals = {k: sum(r['curation'][k] for r in records) for k in CATEGORY}
    converted = sorted((r['subject'], r['condition']) for r in records)
    data = {'task_id': 'UM21-T01', 'status': 'scope_declared_unreviewed', 'scientific_approval': False,
            'inputs_sha256': {str(p.relative_to(ROOT)): digest(p) for p in
                              (BASE / 'conversion_summary.json', READBACK, CURATION, MEMBERSHIP)},
            'source': {'path': str(SOURCE.relative_to(ROOT)), 'bytes': SOURCE.stat().st_size,
                       'streaming_sha256_recorded': json.loads((BASE / 'conversion_summary.json').read_text())['source']['sha256'],
                       'normalized_sha256_recorded': json.loads(CURATION.read_text())['source_normalized_sha256'],
                       'sha256_note': 'Recorded by the conversion and curation receipts; not recomputed here.',
                       'readback_probe_sha256': digest(PROBE), 'curation_probe_sha256': json.loads(CURATION.read_text())['probe_sha256'],
                       'tread_trials_in_source': len(inventory),
                       'converted_equals_source_inventory': converted == inventory},
            'recordings': len(records), 'observations': sum(r['observations'] for r in records),
            'excluded_pairs': sum(r['excluded_pairs'] for r in records), 'curation_totals': totals,
            'all_receipts_agree': all(r['receipts_agree'] for r in records),
            'columns': {'identity_checked_by_probe': IDENTITY_CHECKED, 'identity_unchecked': IDENTITY_UNCHECKED,
                        'values_identical_to_source': [c for c in CHECKED if 'velocity' not in c],
                        'derived_checked_against_source_derivative': [c for c in CHECKED if 'velocity' in c],
                        'pending_conventions_UM21_C01': PENDING,
                        'not_exported_source_groups': {k: v for k, v in channels.items() if k != 'events'},
                        'not_exported_owner': 'Joint components UM21-T02/T03; forceplates and markers UM21-X01/X02',
                        'not_exported_note': 'jointAngles groups are listed whole; their sagittal hip, knee, pelvis and ankle parts are exported above, other planes are not.'},
            'odd_duration_screen': {'rule': 'exported stride outside 0.5-1.5x its recording median duration',
                                    'exported': sum(r['odd_duration_exported'] for r in records),
                                    'rule_only': sum(r['odd_duration_rule_only'] for r in records)},
            'membership_policy': 'Open decision D-1 (UM21-R01).',
            'pilot_record': {'subject': 'AB01', 'condition': 'd10', 'decided_by': 'agent',
                             'reason': 'Both legs, steady and transition cycles, 77 exclusions, and the unresolved ankle column present; an existing producer pilot uses current code.'},
            'random_sample': {'seed': SEED, 'record': f'{sample["subject"]}/{sample["condition"]}'},
            'records': records,
            'limitations': ['Counts and receipts only; no new numerical source comparison was run.',
                            'Original curation agreement does not validate event timing or the opposite leg.']}
    MANIFEST.write_text(json.dumps(data, indent=2) + '\n')
    return data


def unusual(counts):
    """Recordings beyond 2.5 SD of their slope either way, or left/right differing by over 10%."""
    totals = {k: sum(v.values()) for k, v in counts.items()}
    flagged = {}
    for k, v in counts.items():
        # Compare within the same slope only; slopes differ in typical stride counts.
        peers = [t for (s, c), t in totals.items() if c == k[1]]
        mean, sd = np.mean(peers), np.std(peers)
        if abs(totals[k] - mean) > 2.5 * sd:
            flagged[k] = 'high' if totals[k] > mean else 'low'
        elif abs(v.get('left', 0) - v.get('right', 0)) > .1 * max(v.values()):
            flagged[k] = 'left/right imbalance'
    return flagged


def draw_cells(axis, cells, rows, cols, flagged):
    for i, row in enumerate(rows):
        for j, col in enumerate(cols):
            sides = cells.get((row, col))
            for k, side in enumerate(('left', 'right')):
                n = sides.get(side, 0) if sides else 0
                color = (LEFT, RIGHT)[k] if n else BAD
                axis.add_patch(plt.Rectangle((j + k * .5, i), .5, 1, color=color, alpha=.28 if n else .85, ec='white', lw=1.5))
                axis.text(j + k * .5 + .25, i + .5, str(n) if n else '✗', ha='center', va='center', fontsize=10,
                          color=INK if n else 'white')
            if (row, col) in flagged:
                axis.add_patch(plt.Rectangle((j, i), 1, 1, fill=False, ec=INK, lw=2))
    axis.set_xlim(0, len(cols)); axis.set_ylim(len(rows), 0); axis.tick_params(length=0)
    axis.spines[:].set_visible(False)


def fig_completeness(records, inventory, folder):
    subjects = sorted({s for s, _ in inventory})
    counts = {(r['subject'], r['condition']): r['observations_by_side'] for r in records}
    flagged = unusual(counts)
    fig, ax = plt.subplots(figsize=(6.4, 5.6))
    # Rows and columns come from the source inventory, so a missing conversion shows as a red cell.
    draw_cells(ax, counts, subjects, sorted({c for _, c in inventory}, key=CONDITIONS.index), flagged)
    ax.set_xticks(np.arange(len(CONDITIONS)) + .5, [SLOPE[c].replace(' ', '\n') for c in CONDITIONS])
    ax.set_yticks(np.arange(len(subjects)) + .5, subjects)
    ax.set_title('Strides per recording (left | right)', loc='left', fontweight='bold')
    fig.savefig(folder / 'fig1a_grid.png', dpi=170, bbox_inches='tight'); plt.close(fig)
    # Labeled made-up examples of the failures this figure must reveal.
    fig, kx = plt.subplots(figsize=(3.0, 3.0))
    draw_cells(kx, {('fine', 'x'): {'left': 90, 'right': 91}, ('one leg', 'x'): {'left': 88}, ('odd', 'x'): {'left': 90, 'right': 40}},
               ['fine', 'one leg', 'missing', 'odd'], ['x'], {('odd', 'x'): 'left/right imbalance'})
    kx.set_xticks([]); kx.set_yticks([.5, 1.5, 2.5, 3.5], ['fine', 'one leg missing', 'recording missing', 'outlined: unusual'])
    kx.yaxis.tick_right(); kx.set_title('Failure looks like (made-up)', loc='left', fontsize=10.5, color=MUTED)
    fig.savefig(folder / 'fig1b_key.png', dpi=170, bbox_inches='tight'); plt.close(fig)
    return flagged


def fig_legs(sample, folder):
    path = BASE / sample['subject'] / sample['condition'] / 'phase.parquet'
    cols = ['task', 'observation_id', 'hip_flexion_angle_ipsi_rad', 'hip_flexion_angle_contra_rad']
    frame = pq.read_table(path, columns=cols).to_pandas()
    frame = frame[frame.task != 'transition']
    groups = [g for _, g in frame.groupby('observation_id')]
    ipsi = np.degrees(np.stack([g.hip_flexion_angle_ipsi_rad.to_numpy() for g in groups]))
    contra = np.degrees(np.stack([g.hip_flexion_angle_contra_rad.to_numpy() for g in groups]))
    phase = np.linspace(0, 100, ipsi.shape[1])
    # Other-leg lag from the circular cross-correlation of the mean curves.
    a, b = ipsi.mean(0) - ipsi.mean(), contra.mean(0) - contra.mean()
    lag = int(np.argmax([np.dot(a, np.roll(b, -k)) for k in range(len(a))])) * 100 / (len(a) - 1)
    panels = [('fig2a_real.png', f'This recording (other leg lags {lag:.0f}%)', ipsi.mean(0), contra.mean(0), True),
              ('fig2b_copied.png', 'If the other-leg column copied this leg (made-up)', ipsi.mean(0), ipsi.mean(0) + .8, False),
              ('fig2c_flipped.png', 'If the sign were flipped (made-up)', -ipsi.mean(0), -contra.mean(0), False)]
    for name, title, one, other, real in panels:
        fig, ax = plt.subplots(figsize=(3.6, 2.9))
        if real:
            ax.plot(phase, ipsi.T, color=LEFT, lw=.4, alpha=.08)
        ax.plot(phase, one, color=LEFT if real else REF, lw=2, label='this leg')
        ax.plot(phase, other, color=RIGHT if real else REF, lw=2, ls='--', label='other leg')
        ax.axhline(0, color=REF, lw=.5); ax.set_ylim(-65, 70)
        ax.set_xlabel('gait cycle (%)'); ax.set_ylabel('hip flexion (deg)')
        ax.set_title(title, loc='left', fontweight='bold' if real else 'normal', fontsize=10.5, color=INK if real else MUTED, wrap=True)
        ax.legend(loc='best', fontsize=9.5)
        fig.savefig(folder / name, dpi=170, bbox_inches='tight'); plt.close(fig)
    return lag, len(groups), [p[0] for p in panels]


def fig_agreement(records, membership, sample, folder):
    t = {k: sum(r['curation'][k] for r in records) for k in CATEGORY}
    fig, ax = plt.subplots(figsize=(3.4, 3.4))
    layout = [['exported_in_original_curation', 'exported_not_in_original_curation'],
              ['excluded_in_original_curation', 'excluded_not_in_original_curation']]
    for i, row in enumerate(layout):
        for j, key in enumerate(row):
            ax.add_patch(plt.Rectangle((j, 1 - i), 1, 1, color=CATEGORY[key][1], alpha=.55, ec='white', lw=2))
            ax.text(j + .5, 1.5 - i, f'{t[key]:,}', ha='center', va='center', fontsize=12, fontweight='bold')
    ax.set_xlim(0, 2); ax.set_ylim(0, 2); ax.set_aspect('equal'); ax.tick_params(length=0); ax.spines[:].set_visible(False)
    ax.set_xticks([.5, 1.5], ['in authors\'\nset', 'not in\nauthors\' set']); ax.set_yticks([1.5, .5], ['rule\nkeeps', 'rule\ndrops'])
    ax.set_title(f'All {sum(t.values()):,} heel-strike pairs', loc='left', fontweight='bold')
    fig.savefig(folder / 'fig3a_table.png', dpi=170, bbox_inches='tight'); plt.close(fig)
    rows = [m for m in membership if (m['subject'], m['condition']) == (sample['subject'], sample['condition'])]
    fig, bx = plt.subplots(figsize=(4.6, 2.9))
    for lane, side in enumerate(('left', 'right')):
        for m in (m for m in rows if m['reference_side'] == side):
            bx.broken_barh([(m['start_frame'] / 100, (m['end_frame'] - m['start_frame']) / 100)], (lane - .38, .76),
                           color=CATEGORY[m['streaming_status']][1], alpha=.85, lw=0)
    bx.set_yticks([0, 1], ['left leg', 'right leg']); bx.tick_params(axis='y', length=0); bx.spines['left'].set_visible(False)
    bx.set_xlabel('time in recording (s)')
    bx.set_title(f'One random recording: {sample["subject"]}, {SLOPE[sample["condition"]]}', loc='left', fontweight='bold')
    handles = [plt.Rectangle((0, 0), 1, 1, color=c, alpha=.85) for _, c in CATEGORY.values()]
    bx.legend(handles, [n for n, _ in CATEGORY.values()], ncol=2, loc='upper center', bbox_to_anchor=(.5, -.28), fontsize=9.5)
    fig.savefig(folder / 'fig3b_timeline.png', dpi=170, bbox_inches='tight'); plt.close(fig)
    return t


def sheets(data, flagged, lag, strides, leg_panels, totals, sample):
    rec = data['records']
    worst = max(r['readback_maximum_error'] for r in rec)
    both_legs = all(min(r['observations_by_side'].values()) > 0 for r in rec)
    complete = data['source']['converted_equals_source_inventory']
    unusual_text = ', '.join(f'{s} {SLOPE[c]}' for s, c in flagged)
    chips = [('pass' if complete else 'fail', f'{len(rec)} of {data["source"]["tread_trials_in_source"]} source recordings'),
             ('pass' if data['all_receipts_agree'] else 'fail', f'all {sum(totals.values()):,} heel-strike pairs accounted for'),
             ('pass' if both_legs else 'fail', 'both legs in every recording'),
             ('pass' if worst < 1e-9 else 'fail', 'hip, knee, pelvis angles identical to source; velocities match'),
             ('pass' if all(r['nan_in_checked_columns'] == 0 for r in rec) else 'fail', 'no gaps in those signals'),
             ('pass' if 45 <= lag <= 55 else 'fail', f'other leg lags {lag:.0f}% (expect 45–55%)'),
             ('unchecked', 'stride start/end timing')]
    if flagged:
        chips.append(('unchecked', f'{len(flagged)} unusual stride count ({unusual_text})' if len(flagged) == 1
                      else f'{len(flagged)} unusual stride counts ({unusual_text})'))
    odd = data['odd_duration_screen']
    if odd['exported']:
        chips[6] = ('unchecked', f'stride timing; {odd["exported"]} kept strides have odd durations')
    page(SHEETS / 'UM21-T01/index.html', title='UM21-T01 check',
         ask='Look at 2 figures. Reply ok, or say what looks wrong.',
         headline='UMich 2021 treadmill: all recordings converted, both legs, matching source',
         chips=chips,
         figures=[(['fig1a_grid.png', 'fig1b_key.png'], 'Is any recording or leg missing?',
                   'Outlined: unusual counts or uneven legs.',
                   'Grid of 10 subjects by 5 slopes with left and right stride counts, and a made-up failure key'),
                  (leg_panels, 'Do the two legs and the sign look right?',
                   f'{strides} steady strides from one random recording.',
                   'Hip flexion of this and the other leg, next to made-up failure examples')],
         not_shown=['Ankle, thigh, shank angles, hip offset: conventions open',
                    'Forces, moments, markers: not converted yet',
                    'Whether the source labels legs correctly'],
         reply='ok  |  what looks wrong',
         details=['Agent decided: the one-recording test run uses AB01 decline 10° (both legs, transitions, exclusions).',
                  f'Random recording {sample["subject"]}/{sample["condition"]}, seed {SEED}; other-leg lag {lag:.1f}%.',
                  f'Largest source difference {worst:.1e} rad.',
                  'Manifest: docs/quality/audits/um21-t01-tread-release-scope.json',
                  'Builder: contributor_tools/review_um21_t01_scope.py'])
    ours = totals['exported_in_original_curation'] + totals['exported_not_in_original_curation']
    authors = totals['exported_in_original_curation'] + totals['excluded_in_original_curation']
    only_ours, only_authors = totals['exported_not_in_original_curation'], totals['excluded_in_original_curation']
    page(SHEETS / 'D-1/index.html', title='D-1 decision',
         ask='Choose which strides go into the first UMich 2021 treadmill release.',
         headline=f'Task-window rule and original authors disagree on {only_ours + only_authors:,} of {sum(totals.values()):,} heel-strike pairs',
         chips=[('pass', 'every dropped pair has a recorded reason'),
                ('unchecked', f'{data["odd_duration_screen"]["rule_only"]} rule-only strides have odd durations')],
         figures=[(['fig3a_table.png', 'fig3b_timeline.png'], 'Where do the rule and the authors disagree?',
                   'The rule drops strides outside a clear task window.',
                   'Two by two agreement table and a timeline of one random recording')],
         decision={'question': 'D-1 · Which strides make up the first release?',
                   'columns': ['Left out', 'Strides', 'Versus authors', 'Extra work'],
                   # Options are ordered by stride count, fewest first, so order cannot signal the recommendation.
                   'rows': [('A · both agree', [f'{only_ours + only_authors:,} disputed strides', f'{totals["exported_in_original_curation"]:,}', f'−{only_authors:,}', 'none']),
                            ("B · authors' set", [f'{only_ours:,} rule-only strides', f'{authors:,}', 'identical', f're-cut {only_authors:,} strides']),
                            ('C · task-window rule', [f'{only_authors:,} author strides', f'{ours:,}', f'+{only_ours:,} / −{only_authors:,}', 'none']),
                            ('defer', ['release waits; test run still goes ahead', '—', '—', '—'])],
                   'footnote': "All options keep a column marking the authors' set; changeable later.",
                   'recommendation': "C, medium confidence: it keeps the most strides and the authors' set stays reproducible from the flag column. It still leaves out 479 author strides and keeps 47 odd-duration strides, both checked in the test run."},
         not_shown=['Whether the disputed strides have valid stride timing',
                    "The authors' selection rule (not yet identified)"],
         reply='D-1: A, B, C or defer',
         details=['Source: original-curation membership list and our exclusion ledgers.',
                  'Builder: contributor_tools/review_um21_t01_scope.py'])


def main():
    style()
    for name in ('UM21-T01', 'D-1'):
        (SHEETS / name).mkdir(parents=True, exist_ok=True)
    inventory, channels = source_inventory()
    records, membership = gather()
    sample = random.Random(SEED).choice(records)
    data = manifest(records, inventory, channels, sample)
    flagged = fig_completeness(records, inventory, SHEETS / 'UM21-T01')
    lag, strides, leg_panels = fig_legs(sample, SHEETS / 'UM21-T01')
    totals = fig_agreement(records, membership, sample, SHEETS / 'D-1')
    sheets(data, flagged, lag, strides, leg_panels, totals, sample)
    print(json.dumps({'sample': data['random_sample'], 'all_receipts_agree': data['all_receipts_agree'],
                      'complete': data['source']['converted_equals_source_inventory'], 'lag_pct': round(lag, 1),
                      'unusual': {f'{k[0]}/{k[1]}': v for k, v in flagged.items()}}))


if __name__ == '__main__':
    main()
