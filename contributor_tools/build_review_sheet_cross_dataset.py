"""Review sheets A: do GT23, GT21 and UM21 follow the same standard?

Overlays the filtered phase tables of the three local review packages
(GT23 review v11, GT21 package v1, UM21 package v5) for matched tasks, one panel
per signal: mean and 1 SD band over 0-100 percent phase (ipsi leg) plus a few
seeded random strides. Writes review_sheets/A-<task>/ (one sheet per task) and
review_sheets/A-cross-dataset/ (index, numbers). Reads only; changes no inputs.

Memory: each file is streamed with pyarrow iter_batches (4096 rows, one thread,
column selection). Per task and signal it keeps running count, sum and sum of
squares per phase index, plus a reservoir of random strides per task chosen
with the recorded SEED. Run (bounded, low priority):
  OMP_NUM_THREADS=1 ARROW_DEFAULT_MEMORY_POOL=system MPLBACKEND=Agg \
  prlimit --as=$((600*1024*1024)) -- nice -n 19 ionice -c 3 \
  python3 contributor_tools/build_review_sheet_cross_dataset.py [--render]
Add --v2 to read the packages rebuilt with the per-person foot-flat zero (GT23 v12, GT21 v2, UM21 v6) and write
review_sheets/A-<task>-v2/ and review_sheets/A-cross-dataset-v2/, leaving the first sheets in place.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
os.environ.setdefault('ARROW_DEFAULT_MEMORY_POOL', 'system')
import csv
import json
from pathlib import Path
import random
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.common.review_sheet import page

SEED = 20261127
N_STRIDES = 6
BATCH = 4096
NPH = 150
PHASE = np.linspace(0, 100, NPH)
LANDMARKS = (0, 15, 50, 85)
STANCE = (15, 50)
PKG = ROOT / 'converted_datasets/reconversion_v2'
SHEETS = ROOT / 'review_sheets'
DATASETS = {  # key: (label, folder, colour)
    'GT23': ('GT23', 'gt23_r01_review_v11', '#2a78d6'),
    'GT21': ('GT21', 'gt21_r01_package_v1', '#eb6834'),
    'UM21': ('UM21', 'um21_r01_package_v5', '#1baf7a'),
}
V2 = '--v2' in sys.argv  # packages after the foot-flat zero; sheets get a -v2 suffix
if V2:
    DATASETS = {'GT23': ('GT23', 'gt23_r01_review_v12', '#2a78d6'),
                'GT21': ('GT21', 'gt21_r01_package_v2', '#eb6834'),
                'UM21': ('UM21', 'um21_r01_package_v6', '#1baf7a')}
SUFFIX = '-v2' if V2 else ''
INK = '#20252B'

# (key, title, unit, column, scale). Angle radians shown in degrees; CoP metres in cm.
D = 180 / np.pi
SIGNALS = [
    ('hip_angle', 'Hip flexion angle', 'deg', 'hip_flexion_angle_ipsi_rad', D, 'joint angles'),
    ('knee_angle', 'Knee flexion angle', 'deg', 'knee_flexion_angle_ipsi_rad', D, 'joint angles'),
    ('ankle_angle', 'Ankle dorsiflexion angle', 'deg', 'ankle_dorsiflexion_angle_ipsi_rad', D, 'joint angles'),
    ('pelvis_seg', 'Pelvis angle', 'deg', 'pelvis_sagittal_angle_rad', D, 'segment angles'),
    ('thigh_seg', 'Thigh angle', 'deg', 'thigh_sagittal_angle_ipsi_rad', D, 'segment angles'),
    ('shank_seg', 'Shank angle', 'deg', 'shank_sagittal_angle_ipsi_rad', D, 'segment angles'),
    ('foot_seg', 'Foot angle', 'deg', 'foot_sagittal_angle_ipsi_rad', D, 'segment angles'),
    ('hip_moment', 'Hip flexion moment', 'Nm/kg', 'hip_flexion_moment_ipsi_Nm_kg', 1.0, 'moments'),
    ('knee_moment', 'Knee flexion moment', 'Nm/kg', 'knee_flexion_moment_ipsi_Nm_kg', 1.0, 'moments'),
    ('ankle_moment', 'Ankle dorsiflexion moment', 'Nm/kg', 'ankle_dorsiflexion_moment_ipsi_Nm_kg', 1.0, 'moments'),
    ('hip_power', 'Hip power', 'W/kg', 'hip_flexion_power_ipsi_W_kg', 1.0, 'powers'),
    ('knee_power', 'Knee power', 'W/kg', 'knee_flexion_power_ipsi_W_kg', 1.0, 'powers'),
    ('ankle_power', 'Ankle power', 'W/kg', 'ankle_dorsiflexion_power_ipsi_W_kg', 1.0, 'powers'),
    ('grf_v', 'Vertical force', 'BW', 'grf_vertical_ipsi_BW', 1.0, 'forces'),
    ('grf_a', 'Anterior force', 'BW', 'grf_anterior_ipsi_BW', 1.0, 'forces'),
    ('grf_l', 'Lateral force', 'BW', 'grf_lateral_ipsi_BW', 1.0, 'forces'),
    ('cop_a', 'Centre of pressure, anterior', 'cm', 'cop_anterior_ipsi_m', 100.0, 'centre of pressure'),
]
FIGURES = [  # per sheet: three figures, one PNG per signal
    ('Do joint and segment angles overlap?', ['hip_angle', 'knee_angle', 'ankle_angle', 'pelvis_seg', 'thigh_seg', 'shank_seg', 'foot_seg']),
    ('Do moments and powers overlap?', ['hip_moment', 'knee_moment', 'ankle_moment', 'hip_power', 'knee_power', 'ankle_power']),
    ('Do forces and centre of pressure overlap?', ['grf_v', 'grf_a', 'grf_l', 'cop_a']),
]

# Task matching. Each returns True when an observation belongs to the task for that dataset.
# Level: treadmill/level walking at 1.2 m/s (+-0.05). Incline/decline: 10 deg (+-1.0 deg); UM21 uses its 1.2 m/s
# runs (its 0.8 and 1.0 m/s runs are left out); GT21 ramp speed is not recorded. Stairs: any stair cycle.
TASKS = {
    'level': dict(title='Level walking', words='level walking at 1.2 m/s', match=lambda ds, t, ti: (
        t == 'level_walking' and ti.get('speed_m_s') is not None and abs(ti['speed_m_s'] - 1.2) <= 0.051
        and (ds != 'UM21' or ti.get('incline_deg') == 0))),
    'incline': dict(title='Incline walking about 10 degrees', words='incline walking, about 10 degrees', match=lambda ds, t, ti: (
        t == 'incline_walking' and ti.get('incline_deg') is not None and abs(ti['incline_deg'] - 10) <= 1.0
        and (ds != 'UM21' or ti.get('speed_m_s') == 1.2))),
    'decline': dict(title='Decline walking about 10 degrees', words='decline walking, about 10 degrees', match=lambda ds, t, ti: (
        t == 'decline_walking' and ti.get('incline_deg') is not None and abs(ti['incline_deg'] + 10) <= 1.0
        and (ds != 'UM21' or ti.get('speed_m_s') == 1.2))),
    'stair_ascent': dict(title='Stair ascent', words='stair ascent', match=lambda ds, t, ti: t == 'stair_ascent'),
    'stair_descent': dict(title='Stair descent', words='stair descent', match=lambda ds, t, ti: t == 'stair_descent'),
}
TASK_IDS = list(TASKS)
MATCH_NOTE = {
    'level': 'Speeds matched: GT23 1.2 (level_1-2); GT21 treadmill 1.15, 1.2, 1.25; UM21 1.2 at 0 deg (its 0.8 and 1.0 runs left out).',
    'incline': 'Slopes matched: GT23 10 deg at 1.2 m/s; GT21 9.2 and 11.0 deg (speed not recorded for ramps); UM21 10 deg at 1.2 m/s.',
    'decline': 'Slopes matched: GT23 -10 deg at 1.2 m/s; GT21 -9.2 and -11.0 deg (speed not recorded for ramps); UM21 -10 deg at 1.2 m/s.',
    'stair_ascent': 'Stair cycles of any participant; UM21 has no stair task. Stair dimensions are not compared.',
    'stair_descent': 'Stair cycles of any participant; UM21 has no stair task. Stair dimensions are not compared.',
}


def collect(ds):
    """One pass over a filtered phase table. Returns per-task sums and reservoir strides."""
    label, folder, _ = DATASETS[ds]
    pf = pq.ParquetFile(PKG / folder / 'filtered_phase.parquet')
    names = set(pf.schema_arrow.names)
    present = {s[0]: s[3] in names for s in SIGNALS}
    sig_cols = [s for s in SIGNALS if present[s[0]]]
    read_cols = ['subject', 'observation_id', 'task', 'task_id', 'task_info', 'observation_type', 'phase_ipsi'] + [s[3] for s in sig_cols]
    nt = len(TASK_IDS)
    acc = {s[0]: np.zeros((nt, 3, NPH)) for s in sig_cols}  # count, sum, sum of squares
    rng = {g: random.Random(f'{SEED}-{ds}-{g}') for g in range(nt)}
    seen_obs, group_of = 0, {}
    counts = [0] * nt
    subjects = [set() for _ in range(nt)]
    slots = [[None] * N_STRIDES for _ in range(nt)]  # observation id per slot
    store = {}  # observation id -> (task index, {signal: array(150)})
    for batch in pf.iter_batches(BATCH, columns=read_cols, use_threads=False):
        ids = batch.column('observation_id').to_numpy(zero_copy_only=False)
        uniq, first, inv = np.unique(ids, return_index=True, return_inverse=True)
        codes = np.empty(len(uniq), dtype=np.int64)
        for k, (u, f) in enumerate(zip(uniq, first)):
            if u not in group_of:
                gid = -1
                if batch.column('observation_type')[int(f)].as_py() == 'individual_cycle':
                    task = batch.column('task')[int(f)].as_py()
                    info = json.loads(batch.column('task_info')[int(f)].as_py() or '{}')
                    for g, tid in enumerate(TASK_IDS):
                        if TASKS[tid]['match'](ds, task, info):
                            gid = g
                            break
                group_of[u] = gid
                if gid >= 0:
                    counts[gid] += 1
                    subjects[gid].add(batch.column('subject')[int(f)].as_py())
                    i = counts[gid] - 1  # reservoir sampling (algorithm R)
                    j = i if i < N_STRIDES else rng[gid].randint(0, i)
                    if j < N_STRIDES:
                        old = slots[gid][j]
                        if old is not None:
                            store.pop(old, None)
                        slots[gid][j] = u
                        store[u] = (gid, {s[0]: np.full(NPH, np.nan) for s in sig_cols})
            codes[k] = group_of[u]
        row_group = codes[inv]
        if (row_group < 0).all():
            continue
        ph = np.rint(batch.column('phase_ipsi').to_numpy(zero_copy_only=False) / 100 * (NPH - 1)).astype(np.int64)
        for s in sig_cols:
            vals = batch.column(s[3]).to_numpy(zero_copy_only=False).astype(np.float64) * s[4]
            good = np.isfinite(vals)
            for g in np.unique(row_group[row_group >= 0]):
                m = (row_group == g) & good
                if not m.any():
                    continue
                v = vals[m]
                p = ph[m]
                acc[s[0]][g, 0] += np.bincount(p, minlength=NPH)
                acc[s[0]][g, 1] += np.bincount(p, weights=v, minlength=NPH)
                acc[s[0]][g, 2] += np.bincount(p, weights=v * v, minlength=NPH)
            if store:
                for k, u in enumerate(uniq):
                    if u in store:
                        m = (inv == k) & good
                        store[u][1][s[0]][ph[m]] = vals[m]
    strides = [[store[u][1] for u in slots[g] if u is not None] for g in range(nt)]
    return dict(present=present, acc=acc, counts=counts, subjects=[len(s) for s in subjects], strides=strides)


def curves(res, sig, gid):
    """Mean, SD and finite-stride count per phase index, or None if no finite data."""
    if not res['present'].get(sig):
        return None
    n, s1, s2 = res['acc'][sig][gid]
    ok = n >= 2
    if not ok.any():
        return None
    mean = np.where(ok, s1 / np.maximum(n, 1), np.nan)
    var = np.where(ok, (s2 - n * mean ** 2) / np.maximum(n - 1, 1), np.nan)
    return mean, np.sqrt(np.maximum(var, 0)), n


def style():
    plt.rcParams.update({'font.size': 10, 'axes.titlesize': 10.5, 'axes.spines.top': False, 'axes.spines.right': False,
                         'text.color': INK, 'axes.labelcolor': INK, 'axes.edgecolor': INK, 'xtick.color': INK,
                         'ytick.color': INK, 'axes.linewidth': 0.6, 'legend.frameon': False})


def status(res, sig, gid):
    if not res['present'].get(sig):
        return 'not in this dataset'
    if curves(res, sig, gid) is None:
        return 'no finite values for this task'
    return None


def panel(path, results, tid, gid, sig):
    key, title, unit, col, scale, fam = next(s for s in SIGNALS if s[0] == sig)
    fig, ax = plt.subplots(figsize=(4.5, 3.9))
    for row, ds in enumerate(DATASETS):
        label, _, colour = DATASETS[ds]
        res = results[ds]
        c = curves(res, sig, gid)
        n_obs = res['counts'][gid]
        if c is None:
            msg = status(res, sig, gid) if n_obs else 'task not in this dataset'
            if not n_obs and not res['present'].get(sig):
                msg = 'task not in this dataset'
            text = f'{label}: {msg}'
        else:
            mean, sd, n = c
            ax.fill_between(PHASE, mean - sd, mean + sd, color=colour, alpha=0.18, lw=0)
            for stride in res['strides'][gid]:
                ax.plot(PHASE, stride[sig], color=colour, lw=0.5, alpha=0.45)
            ax.plot(PHASE, mean, color=colour, lw=2)
            text = f'{label}: {n_obs} strides, {res["subjects"][gid]} people'
        fig.text(0.04, 0.115 - row * 0.045, text, color=colour, fontsize=10, fontweight='bold', ha='left', va='center')
    ax.set_title(f'{title} ({unit})', loc='left')
    ax.set_xlim(0, 100)
    ax.set_xlabel('Phase (% of stride)')
    ax.axhline(0, color='#aab2ba', lw=0.5, zorder=0)
    fig.subplots_adjust(left=0.17, right=0.97, top=0.92, bottom=0.30)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def pair_gaps(results, gid, sig):
    """Mean differences between datasets at landmarks, shape correlation, spread ratio."""
    cs = {ds: curves(results[ds], sig, gid) for ds in DATASETS}
    cs = {ds: c for ds, c in cs.items() if c is not None}
    out = {}
    names = list(DATASETS)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if a in cs and b in cs:
                ma, sa = cs[a][0], cs[a][1]
                mb, sb = cs[b][0], cs[b][1]
                ok = np.isfinite(ma) & np.isfinite(mb)
                r = float(np.corrcoef(ma[ok], mb[ok])[0, 1]) if ok.sum() > 10 else float('nan')
                gaps, ratios = {}, {}
                for lm in LANDMARKS:
                    d = float(np.interp(lm, PHASE, ma) - np.interp(lm, PHASE, mb))
                    spread = max(float(np.interp(lm, PHASE, sa)), float(np.interp(lm, PHASE, sb)))
                    gaps[lm] = d
                    ratios[lm] = abs(d) / spread if spread > 0 else float('inf')
                amp = max(np.nanmax(ma) - np.nanmin(ma), np.nanmax(mb) - np.nanmin(mb))
                flat = bool(amp < np.nanmedian(np.concatenate([sa, sb])))  # curve barely moves: shape is not informative
                out[(a, b)] = dict(r=r, gaps=gaps, ratio=ratios, flat=flat)
    return out


def judge(pg, n_avail):
    """pass: shape r >= 0.9 and every landmark gap within 1 SD of the wider dataset; fail: opposite shape (r < 0);
    unchecked otherwise or when fewer than two datasets have the signal. These cut-offs are this sheet's own rule."""
    if n_avail < 2 or not pg:
        return 'unchecked'
    shape = [v for v in pg.values() if not v['flat']]
    if any(v['r'] < 0 for v in shape):
        return 'fail'
    if all((v['flat'] or v['r'] >= 0.9) and max(v['ratio'].values()) <= 1.0 for v in pg.values()):
        return 'pass'
    return 'unchecked'


def build(results, tid, gid):
    task = TASKS[tid]
    out = SHEETS / f'A-{tid}{SUFFIX}'
    out.mkdir(parents=True, exist_ok=True)
    style()
    for sig in [s[0] for s in SIGNALS]:
        panel(out / f'{sig}.png', results, tid, gid, sig)
    chips, details, table_rows = [], [], []
    fam_info = {}
    for s in SIGNALS:
        sig, title, unit = s[0], s[1], s[2]
        pg = pair_gaps(results, gid, sig)
        avail = [ds for ds in DATASETS if curves(results[ds], sig, gid) is not None]
        state = judge(pg, len(avail))
        worst = max((max(abs(v['gaps'][lm]) for lm in STANCE) for v in pg.values()), default=None)
        fam = fam_info.setdefault(s[5], dict(states=[], bits=[], missing=set()))
        fam['states'].append(state)
        short = title.split(' ')[0].lower() if s[5] in ('joint angles', 'segment angles', 'moments', 'powers') else title.lower()
        fam['bits'].append(f'{short} {worst:.2g} {unit}' if worst is not None else f'{short} n/a')
        for ds in DATASETS:
            if ds not in avail:
                fam['missing'].add(ds)
        for (a, b), v in pg.items():
            table_rows.append([TASKS[tid]['title'], title, unit, f'{a}-{b}', f'{v["r"]:.2f}'] +
                              [f'{v["gaps"][lm]:+.3g}' for lm in LANDMARKS] + [f'{max(v["ratio"].values()):.2f}'])
        line = f'{title} ({unit}), mean difference at 0/15/50/85% ' + '; '.join(
            f'{a}-{b}: ' + '/'.join(f'{v["gaps"][lm]:+.2g}' for lm in LANDMARKS) + f' (shape r {v["r"]:.2f})' for (a, b), v in pg.items())
        if len(avail) < 3:
            line += '; missing: ' + ', '.join(f'{ds} ({status(results[ds], sig, gid) if results[ds]["counts"][gid] else "task not in this dataset"})' for ds in DATASETS if ds not in avail)
        line += f' [{state}]'
        details.append(line)
    rank = {'pass': 0, 'unchecked': 1, 'fail': 2}
    for name, fam in fam_info.items():
        state = max(fam['states'], key=lambda x: rank[x])
        miss = f'; {", ".join(sorted(fam["missing"]))} lacks some' if fam['missing'] else ''
        verb = {'pass': 'agree', 'fail': 'opposite shape', 'unchecked': 'differ, cause not established'}[state]
        chips.append((state, f'{name} {verb}: largest gap at 15 and 50% {", ".join(fam["bits"])}{miss}'))
    n_oc = [results[ds]['counts'][gid] for ds in DATASETS]
    chips = chips[:6] + [chips[6]] if len(chips) >= 7 else chips
    # chips are in signal order: joint, segment, moments, powers, forces, centre of pressure
    chips.append(('pass' if tid == 'level' else 'unchecked',
                  'task match: ' + ('same speed' if tid == 'level' else 'ramp speed or stair size not matched')))
    caps = ['Band: mean ± 1 SD of strides. Thin lines: 6 seeded random strides.', 'Same bands and colours.', 'Same bands and colours.']
    not_shown = ['Other speeds and slopes', 'UM21 force (not in its phase table)', 'Differences between people']
    figures = []
    for (question, sigs), cap in zip(FIGURES, caps):
        figures.append(([f'{sg}.png' for sg in sigs], question, cap, f'Overlay of GT23 (blue), GT21 (orange) and UM21 (green) for {task["words"]}: ' + ', '.join(sigs)))
    details = [f'Task: {task["title"]}. {MATCH_NOTE[tid]}',
               'Strides per dataset (people): ' + '; '.join(f'{ds} {results[ds]["counts"][gid]} ({results[ds]["subjects"][gid]})' for ds in DATASETS)
               + '. Strides pooled across people, so people with more strides weigh more.',
               f'Random strides: reservoir sample of {N_STRIDES} per dataset, seed {SEED}.',
               'Chip rule (this sheet only, not a reference range): pass = mean curves correlate at 0.9 or more for every pair and every gap at 0, 15, 50, 85% is within 1 SD of the wider dataset; failed = opposite shape (r below 0); the shape test is skipped when a curve moves less than its own SD; otherwise not checked.',
               'Mean differences use the first dataset minus the second, in the unit shown, at 0, 15, 50 and 85% phase (linear interpolation of the mean curves).'] + details + [
        'Sources: ' + ', '.join(f'{ds} {DATASETS[ds][1]}' for ds in DATASETS) + ', filtered phase tables. Builder: contributor_tools/build_review_sheet_cross_dataset.py']
    page(out / 'index.html', title=f'Cross-dataset check: {task["title"]}',
         ask='Check whether the three datasets overlap.', headline=f'{task["title"]}: GT23, GT21 and UM21',
         chips=chips, figures=figures, not_shown=not_shown, reply='ok  |  which signal looks wrong', details=details)
    with (out / 'gaps.csv').open('w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['task', 'signal', 'unit', 'pair (first minus second)', 'shape r'] + [f'mean diff at {lm}%' for lm in LANDMARKS] + ['max gap / wider SD'])
        w.writerows(table_rows)
    return chips, table_rows


def render(paths):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/google-chrome') if Path('/usr/bin/google-chrome').exists() else p.chromium.launch()
        for path in paths:
            for name, width in (('wide', 1280), ('phone', 390)):
                pg = browser.new_page(viewport={'width': width, 'height': 900})
                pg.goto(path.resolve().as_uri())
                pg.screenshot(path=str(path.parent / f'render_{name}.png'), full_page=True)
                pg.close()
        browser.close()


def main():
    results = {ds: collect(ds) for ds in DATASETS}
    index_rows, sheets = [], []
    for gid, tid in enumerate(TASK_IDS):
        chips, _ = build(results, tid, gid)
        sheets.append(SHEETS / f'A-{tid}{SUFFIX}' / 'index.html')
        index_rows.append((tid, chips))
    idx = SHEETS / f'A-cross-dataset{SUFFIX}'
    idx.mkdir(parents=True, exist_ok=True)
    marks = {'pass': 'pass', 'fail': 'FAILED', 'unchecked': 'not checked'}
    html = ['<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>Do the three datasets follow the same standard?</title>'
            '<body style="font:16px/1.5 system-ui;max-width:860px;margin:20px auto;padding:0 16px">'
            '<h1>Do the three datasets follow the same standard?</h1><ul>']
    for tid, chips in index_rows:
        html.append(f'<li><a href="../A-{tid}{SUFFIX}/index.html">{TASKS[tid]["title"]}</a><ul>' +
                    ''.join(f'<li>{marks[s]}: {t}</li>' for s, t in chips) + '</ul></li>')
    html.append('</ul></body>')
    (idx / 'index.html').write_text('\n'.join(html), encoding='utf-8')
    summary = {tid: [{'state': s, 'text': t} for s, t in chips] for tid, chips in index_rows}
    summary['seed'] = SEED
    (idx / 'summary.json').write_text(json.dumps(summary, indent=1), encoding='utf-8')
    if '--render' in sys.argv:
        render(sheets + [idx / 'index.html'])


if __name__ == '__main__':
    main()
