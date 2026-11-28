"""Review sheets AT: LocoHub GT23, GT21 and UM21 against each other, and José's training versions against LocoHub.

Reads (never writes) the current LocoHub packages (GT23 review v12, GT21 package v2, UM21 package v6, filtered phase tables) and
the outputs of contributor_tools/compare_training_vs_locohub.py run in time-table mode with --emit-strides
(docs/quality/audits/training-compare-v2-*). Writes review_sheets/AT-locohub-and-training/ (index + one sheet per task).

Per signal panel: LocoHub as a solid mean +- 1 SD band over 0-100 percent phase (ipsi leg, all matching strides, same task rules as
sheet A); the training version as a dashed mean line in the same colour. Training strides: the training file carries no gait phase
(its step counter and swing mask were not used), so every LocoHub stride window of an aligned recording is cut out of the training
time series using the time offset found by the comparison script (the ankle-moment fit); the training value is read at the 150
inclusive phase times of that stride. The training mean is over those strides only (people and recordings the training file holds).
Training minus LocoHub uses the LocoHub time-table series read at the same times, stride by stride, so the same samples sit on both
sides. UM21 vertical force is not in the UM21 phase table: its LocoHub band is the time-table series read at the same stride times
(strides of the training recordings only).

Run (bounded, low priority; one process):
  OMP_NUM_THREADS=1 ARROW_DEFAULT_MEMORY_POOL=system MPLBACKEND=Agg \
  prlimit --as=$((600*1024*1024)) -- nice -n 19 ionice -c 3 python3 contributor_tools/build_review_sheet_locohub_training.py [--render]
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
os.environ.setdefault('ARROW_DEFAULT_MEMORY_POOL', 'system')
import csv
import json
import math
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

pa.set_cpu_count(1)
pa.set_io_thread_count(1)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools import compare_training_vs_locohub as cmp
from contributor_tools import build_review_sheet_cross_dataset as sa
from contributor_tools.common.review_sheet import page

NPH = 150
PHASE = np.linspace(0, 100, NPH)
LANDMARKS = (0, 15, 50, 85)
BATCH = 4096
PKG = ROOT / 'converted_datasets/reconversion_v2'
AUD = ROOT / 'docs/quality/audits'
OUT = ROOT / 'review_sheets/AT-locohub-and-training'
INK = '#20252B'
DATASETS = {'GT23': ('GT23', 'gt23_r01_review_v12', '#2a78d6', 'gt23'),
            'GT21': ('GT21', 'gt21_r01_package_v2', '#eb6834', 'gt21'),
            'UM21': ('UM21', 'um21_r01_package_v6', '#1baf7a', 'um21')}
JOBS = {  # completed time-table runs (pilot outputs are complete runs of the same code; the first gt23 pilot and gt21-a are not used)
    'GT23': ['gt23-pilot3', 'gt23-a', 'gt23-b', 'gt23-c', 'gt23-d', 'gt23-e'],
    'GT21': ['gt21-pilot'] + [f'gt21-{s}' for s in ('AB07', 'AB08', 'AB09', 'AB10', 'AB11', 'AB13', 'AB14', 'AB16', 'AB18', 'AB20', 'AB21', 'AB24', 'AB25', 'AB30')],
    'UM21': ['um21-pilot', 'um21-a', 'um21-b', 'um21-c'],
}
MAPS = {m.name: m for m in cmp.column_maps(0.100)}
D = 180 / np.pi

# (key, title, unit, LocoHub phase column, scale, training column name or None)
SIGNALS = [
    ('pelvis_seg', 'Pelvis angle', 'deg', 'pelvis_sagittal_angle_rad', D, None),
    ('thigh_seg', 'Thigh angle', 'deg', 'thigh_sagittal_angle_ipsi_rad', D, None),
    ('shank_seg', 'Shank angle', 'deg', 'shank_sagittal_angle_ipsi_rad', D, 'shank_angle'),
    ('foot_seg', 'Foot angle', 'deg', 'foot_sagittal_angle_ipsi_rad', D, 'foot_angle'),
    ('hip_angle', 'Hip flexion angle', 'deg', 'hip_flexion_angle_ipsi_rad', D, None),
    ('knee_angle', 'Knee flexion angle', 'deg', 'knee_flexion_angle_ipsi_rad', D, None),
    ('ankle_angle', 'Ankle dorsiflexion angle', 'deg', 'ankle_dorsiflexion_angle_ipsi_rad', D, 'ankle_angle'),
    ('ankle_moment', 'Ankle dorsiflexion moment', 'Nm/kg', 'ankle_dorsiflexion_moment_ipsi_Nm_kg', 1.0, 'ankle_moment'),
    ('grf_v', 'Vertical force', 'BW', 'grf_vertical_ipsi_BW', 1.0, 'vertical_force'),
    ('cop_a', 'Centre of pressure, anterior', 'cm', 'cop_anterior_ipsi_m', 100.0, 'cop_anterior'),
]
SIG = {s[0]: s for s in SIGNALS}
PLOT_SCALE = {s[0]: (100.0 if s[0] == 'cop_a' else 1.0) for s in SIGNALS}   # npz values are already in degrees, Nm/kg, BW; CoP metres -> cm
TRAINED = [s for s in SIGNALS if s[5]]
FIGURES = [
    ('Do the angles match the training version?', ['pelvis_seg', 'thigh_seg', 'shank_seg', 'foot_seg', 'hip_angle', 'knee_angle', 'ankle_angle']),
    ('Do ankle moment, force and centre of pressure match?', ['ankle_moment', 'grf_v', 'cop_a']),
]

# Tasks: the five of sheet A plus sit_to_stand (the only GT23 task in the training file). TYPES: observation types that count.
TASKS = dict(sa.TASKS)
TASKS['sit_to_stand'] = dict(title='Sit to stand', words='sit to stand', match=lambda ds, t, ti: t == 'sit_to_stand')
TYPES = {tid: ('individual_cycle',) for tid in TASKS}
TYPES['sit_to_stand'] = ('transfer',)
TASK_IDS = ['level', 'incline', 'decline', 'stair_ascent', 'stair_descent', 'sit_to_stand']
MATCH_NOTE = dict(sa.MATCH_NOTE)
MATCH_NOTE['sit_to_stand'] = ('Two-leg sit-to-stand transfers of GT23 (transfer windows; ipsi columns are the left leg, so the right-leg training '
                              'recordings read the contra columns of the same window). GT21 and UM21 have no sit-to-stand task.')
MATCH_NOTE['level'] = MATCH_NOTE['level'] + ' Training strides are the LocoHub strides that fall inside an aligned training recording.'

CLASS_WORDS = {'match': 'within size', 'offset': 'constant offset', 'phase': 'phase-dependent', 'scatter': 'scatter only', 'none': 'no data'}


def job_dirs(ds):
    out = []
    for j in JOBS[ds]:
        d = AUD / f'training-compare-v2-{j}'
        s = json.loads((d / 'summary.json').read_text())
        if s['status'] != 'complete':
            raise SystemExit(f'{d} is not complete')
        out.append((d, s))
    return out


# ------------------------------------------------------------------------------------------------ LocoHub pass (as sheet A)
def collect_locohub(ds):
    label, folder, _, _ = DATASETS[ds]
    pf = pq.ParquetFile(PKG / folder / 'filtered_phase.parquet')
    names = set(pf.schema_arrow.names)
    present = {s[0]: s[3] in names for s in SIGNALS}
    sig_cols = [s for s in SIGNALS if present[s[0]]]
    read_cols = ['subject', 'observation_id', 'task', 'task_info', 'observation_type', 'phase_ipsi'] + [s[3] for s in sig_cols]
    nt = len(TASK_IDS)
    acc = {s[0]: np.zeros((nt, 3, NPH)) for s in SIGNALS}
    group_of, counts, subjects = {}, [0] * nt, [set() for _ in range(nt)]
    for batch in pf.iter_batches(BATCH, columns=read_cols, use_threads=False):
        ids = batch.column('observation_id').to_numpy(zero_copy_only=False)
        uniq, first, inv = np.unique(ids, return_index=True, return_inverse=True)
        codes = np.empty(len(uniq), dtype=np.int64)
        for k, (u, f) in enumerate(zip(uniq, first)):
            if u not in group_of:
                gid = -1
                otype = batch.column('observation_type')[int(f)].as_py()
                task = batch.column('task')[int(f)].as_py()
                info = None
                for g, tid in enumerate(TASK_IDS):
                    if otype not in TYPES[tid]:
                        continue
                    if info is None:
                        info = json.loads(batch.column('task_info')[int(f)].as_py() or '{}')
                    if TASKS[tid]['match'](ds, task, info):
                        gid = g
                        break
                if gid >= 0:
                    group_of[u] = gid
                    counts[gid] += 1
                    subjects[gid].add(batch.column('subject')[int(f)].as_py())
                else:
                    group_of[u] = -1
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
                if m.any():
                    p, v = ph[m], vals[m]
                    acc[s[0]][g, 0] += np.bincount(p, minlength=NPH)
                    acc[s[0]][g, 1] += np.bincount(p, weights=v, minlength=NPH)
                    acc[s[0]][g, 2] += np.bincount(p, weights=v * v, minlength=NPH)
    group_of = {k: v for k, v in group_of.items() if v >= 0}
    return dict(present=present, acc=acc, counts=counts, subjects=[len(s) for s in subjects], group_of=group_of,
                lh_time_band={})


# ------------------------------------------------------------------------------------------------ training pass
class PairStat:
    """Training minus LocoHub (same stride, same time) for one dataset, task and column."""

    def __init__(self, size):
        self.acc = cmp.Acc(size, hist=True)
        self.n_strides = 0
        self.n = np.zeros(NPH)
        self.s1 = np.zeros(NPH)

    def add(self, x, y):
        """x, y: (n_strides, 150) in report units."""
        ok = np.isfinite(x) & np.isfinite(y)
        if not ok.any():
            return
        self.acc.add(x[ok], y[ok])
        d = np.where(ok, x - y, 0.0)
        self.n += ok.sum(0)
        self.s1 += d.sum(0)
        self.n_strides += int(ok.any(1).sum())

    def curve(self, min_n=10):
        with np.errstate(invalid='ignore', divide='ignore'):
            return np.where(self.n >= min_n, self.s1 / self.n, np.nan)

    def classify(self, size):
        row = self.acc.row()
        if row['n_matched'] == 0:
            return 'none', row, math.nan, math.nan
        c = self.curve()
        if not np.isfinite(c).any():
            return 'none', row, math.nan, math.nan
        rng = float(np.nanmax(c) - np.nanmin(c))
        off = float(np.nanmean(c))
        if row['rms'] <= size:
            return 'match', row, off, rng
        if rng > size:
            return 'phase', row, off, rng
        if abs(off) > size:
            return 'offset', row, off, rng
        return 'scatter', row, off, rng


def collect_training(ds, lh):
    """Training mean per task and column (LocoHub frame, plotted units), paired stats, and the UM21 force time-table band."""
    nt = len(TASK_IDS)
    tr = {s[0]: np.zeros((nt, 3, NPH)) for s in TRAINED}
    tr_strides = [0] * nt
    tr_people = [set() for _ in range(nt)]
    pair = {}
    seen = set()
    time_band = {}
    for d, summary in job_dirs(ds):
        for f in sorted(d.glob('strides_*.npz')):
            z = np.load(f)
            ids = z['observation_id']
            gids = np.array([lh['group_of'].get(str(o), -1) for o in ids])
            dup = np.array([str(o) in seen for o in ids])
            gids = np.where(dup, -1, gids)
            seen.update(str(o) for o, g in zip(ids, gids) if g >= 0)
            person = f.stem.split('_')[-1]
            for g in np.unique(gids[gids >= 0]):
                sel = gids == g
                tr_strides[g] += int(sel.sum())
                tr_people[g].add(person)
                for s in TRAINED:
                    name = s[5]
                    m = MAPS[name]
                    x = z[name][sel].astype(np.float64) - m.lh_offset
                    y = z['lh_' + name][sel].astype(np.float64) - m.lh_offset
                    ok = np.isfinite(x)
                    tr[s[0]][g, 0] += ok.sum(0)
                    tr[s[0]][g, 1] += np.where(ok, x, 0).sum(0) * PLOT_SCALE[s[0]]
                    tr[s[0]][g, 2] += (np.where(ok, x, 0) ** 2).sum(0) * PLOT_SCALE[s[0]] ** 2
                    pair.setdefault((g, name), PairStat(m.size)).add(z[name][sel].astype(np.float64), z['lh_' + name][sel].astype(np.float64))
                    if ds == 'UM21' and not lh['present'][s[0]]:         # LocoHub band from the time table at the same times
                        okb = np.isfinite(y)
                        a = time_band.setdefault(s[0], np.zeros((nt, 3, NPH)))
                        a[g, 0] += okb.sum(0)
                        a[g, 1] += np.where(okb, y, 0).sum(0) * PLOT_SCALE[s[0]]
                        a[g, 2] += (np.where(okb, y, 0) ** 2).sum(0) * PLOT_SCALE[s[0]] ** 2
    return dict(tr=tr, strides=tr_strides, people=[len(p) for p in tr_people], pair=pair, time_band=time_band)


def curves_of(arr, g):
    n, s1, s2 = arr[g]
    ok = n >= 2
    if not ok.any():
        return None
    mean = np.where(ok, s1 / np.maximum(n, 1), np.nan)
    var = np.where(ok, (s2 - n * mean ** 2) / np.maximum(n - 1, 1), np.nan)
    return mean, np.sqrt(np.maximum(var, 0)), n


# ------------------------------------------------------------------------------------------------ pooled whole-recording statistics
def pooled_dataset_stats(ds):
    """Training minus LocoHub over every time-matched sample of the comparison runs (all tasks the training file holds).
    Mean, RMS and share past the reporting size are pooled exactly from per-person rows; p95 and corr are medians over people."""
    cols = {}
    wrap = {}
    align = {'matched': 0, 'alignment_failed': 0, 'no_candidate': 0}
    reasons = {}
    fails = []
    for d, _ in job_dirs(ds):
        for r in csv.DictReader(open(d / 'comparison.csv')):
            if r['scope'] != 'subject':
                continue
            n = int(r['n_matched'])
            if n == 0:
                continue
            c = cols.setdefault(r['column'], dict(n=0, sb=0.0, sq=0.0, ex=0.0, p95=[], corr=[], people=0))
            c['n'] += n
            c['sb'] += n * float(r['bias'])
            c['sq'] += n * float(r['rms']) ** 2
            c['ex'] += n * float(r['frac_exceed'])
            c['p95'].append(float(r['p95_abs']))
            c['corr'].append(float(r['corr']))
            c['people'] += 1
        wc = d / 'wrap_counts.csv'
        if wc.exists():
            for r in csv.DictReader(open(wc)):
                if r['scope'] == 'subject':
                    w = wrap.setdefault(r['column'], [0, 0])
                    w[0] += int(r['n_matched'])
                    w[1] += int(r['n_wrapped'])
        for r in csv.DictReader(open(d / 'alignment.csv')):
            if r['status'] in align:
                align[r['status']] += 1
            if r['status'] == 'alignment_failed':
                fails.append(f'{r["subject"]} {r["his_recording"]} ({float(r["align_rms_Nm_kg"]):.2f} Nm/kg)')
        for r in csv.DictReader(open(d / 'unmatched.csv')):
            if r['side'] == 'training':
                reasons[r['reason'].split(' (')[0]] = reasons.get(r['reason'].split(' (')[0], 0) + 1
    out = {}
    for name, c in cols.items():
        n = c['n']
        out[name] = dict(n=n, bias=c['sb'] / n, rms=math.sqrt(c['sq'] / n), frac=c['ex'] / n, p95=float(np.nanmedian(c['p95'])),
                         corr=float(np.nanmedian(c['corr'])), people=c['people'])
    return out, {k: (v[1] / v[0] if v[0] else math.nan) for k, v in wrap.items()}, align, reasons, fails


# ------------------------------------------------------------------------------------------------ figures
def style():
    sa.style()


def curves_lh(res, tres, sig, g):
    """LocoHub curves: phase table, or the time-table band for UM21 force."""
    if res['present'][sig]:
        c = sa.curves(res, sig, g)
        return c
    arr = tres['time_band'].get(sig)
    return curves_of(arr, g) if arr is not None else None


def panel(path, results, trained, tid, g, sig):
    key, title, unit, col, scale, tname = SIG[sig]
    fig, ax = plt.subplots(figsize=(4.5, 5.0))
    for row, ds in enumerate(DATASETS):
        label, _, colour, _ = DATASETS[ds]
        res, tres = results[ds], trained[ds]
        c = curves_lh(res, tres, sig, g)
        n_obs = res['counts'][g]
        if c is not None:
            mean, sd, n = c
            ax.fill_between(PHASE, mean - sd, mean + sd, color=colour, alpha=0.18, lw=0)
            ax.plot(PHASE, mean, color=colour, lw=2)
            lh_text = f'{n_obs} strides, {res["subjects"][g]} people' if res['present'][sig] else f'{int(n[0])} strides (time table)'
        else:
            lh_text = 'task not in this dataset' if not n_obs else 'signal not in this dataset'
        if tname is None:
            tr_text = 'training: not in training file'
        else:
            tc = curves_of(tres['tr'][sig], g)
            if tc is None:
                tr_text = 'training: no strides for this task'
            else:
                ax.plot(PHASE, tc[0], color=colour, lw=2, ls=(0, (4, 2.2)))
                tr_text = f'training: {tres["strides"][g]} strides, {tres["people"][g]} people'
        fig.text(0.04, 0.265 - row * 0.085, f'{label} LocoHub: {lh_text}', color=colour, fontsize=10, fontweight='bold', ha='left', va='center')
        fig.text(0.04, 0.265 - row * 0.085 - 0.04, f'   {tr_text}', color=colour, fontsize=10, ha='left', va='center')
    ax.set_title(f'{title} ({unit})', loc='left')
    ax.set_xlim(0, 100)
    ax.set_xlabel('Phase (% of stride)')
    ax.axhline(0, color='#aab2ba', lw=0.5, zorder=0)
    fig.subplots_adjust(left=0.17, right=0.97, top=0.93, bottom=0.35)
    fig.savefig(path, dpi=160)
    plt.close(fig)


# ------------------------------------------------------------------------------------------------ sheet
def fmt_stat(name, st, size, unit_scale=1.0):
    return f'{st["bias"]:+.3g} mean, {st["rms"]:.3g} RMS, {st["p95"]:.3g} p95, r {st["corr"]:.3f}, {100 * st["frac"]:.0f}% past {size:g}'


def dataset_chip(ds, tres, g):
    """pass / fail / unchecked for one dataset on one task, from the stride-paired differences."""
    label = DATASETS[ds][0]
    if tres['strides'][g] == 0:
        return 'unchecked', f'{label} training: no strides for this task in the training file', {}
    classes = {}
    for s in TRAINED:
        ps = tres['pair'].get((g, s[5]))
        if ps is None:
            continue
        cls, row, off, rng = ps.classify(MAPS[s[5]].size)
        classes[s[5]] = (cls, row, off, rng)
    bad = {k: v for k, v in classes.items() if v[0] in ('offset', 'phase')}
    scat = {k: v for k, v in classes.items() if v[0] == 'scatter'}
    short = {'ankle_angle': 'ankle', 'shank_angle': 'shank', 'foot_angle': 'foot', 'ankle_moment': 'moment', 'vertical_force': 'force', 'cop_anterior': 'CoP'}
    unit = {k: MAPS[k].unit for k in MAPS}

    def bit(k, v):
        if v[0] == 'offset':
            return f'{short[k]} offset {v[2]:+.2g} {unit[k]}'
        return f'{short[k]} phase-dependent (mean {v[2]:+.2g}, varies by {v[3]:.2g} {unit[k]})'
    if bad:
        return 'fail', f'{label} training differs from LocoHub: ' + ', '.join(bit(k, v) for k, v in bad.items()), classes
    if scat:
        return 'unchecked', f'{label} training: scatter only past reporting size in ' + ', '.join(short[k] for k in scat) + '; cause not established', classes
    if not classes:
        return 'unchecked', f'{label} training: nothing to compare', classes
    return 'pass', f'{label} training matches LocoHub within reporting size (' + ', '.join(short[k] for k in classes) + ')', classes


def build_task(results, trained, tid, g, pooled):
    task = TASKS[tid]
    out = OUT / tid
    out.mkdir(parents=True, exist_ok=True)
    style()
    for s in SIGNALS:
        panel(out / f'{s[0]}.png', results, trained, tid, g, s[0])
    chips, details, stat_rows, gap_rows = [], [], [], []
    class_by_ds = {}
    for ds in DATASETS:
        state, text, classes = dataset_chip(ds, trained[ds], g)
        chips.append((state, text))
        class_by_ds[ds] = classes
        for s in TRAINED:
            ps = trained[ds]['pair'].get((g, s[5]))
            if ps is None:
                continue
            cls, row, off, rng = ps.classify(MAPS[s[5]].size)
            size = MAPS[s[5]].size
            stat_rows.append([task['title'], DATASETS[ds][0], s[5], MAPS[s[5]].unit, size, trained[ds]['strides'][g], row['n_matched'],
                              f'{row["bias"]:.4g}', f'{row["rms"]:.4g}', f'{row["p95_abs"]:.4g}', f'{row["corr"]:.4f}', f'{100 * row["frac_exceed"]:.1f}' if row['n_matched'] else '',
                              CLASS_WORDS[cls], f'{off:.4g}', f'{rng:.4g}'])
            if row['n_matched']:
                details.append(f'{DATASETS[ds][0]} {s[1].lower()}, training minus LocoHub on {trained[ds]["strides"][g]} paired strides: '
                               f'mean {row["bias"]:+.3g}, RMS {row["rms"]:.3g}, p95 {row["p95_abs"]:.3g}, r {row["corr"]:.3f}, '
                               f'{100 * row["frac_exceed"]:.0f}% past {size:g} {MAPS[s[5]].unit} [{CLASS_WORDS[cls]}; phase-wise mean offset {off:+.3g}, range {rng:.3g}]')
    # LocoHub-only gap table (as sheet A), including UM21 force from its time table
    cs = {}
    for s in SIGNALS:
        for ds in DATASETS:
            c = curves_lh(results[ds], trained[ds], s[0], g)
            if c is not None:
                cs[(s[0], ds)] = c
    names = list(DATASETS)
    gap_lines = []
    for s in SIGNALS:
        parts = []
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if (s[0], a) in cs and (s[0], b) in cs:
                    ma, mb = cs[(s[0], a)][0], cs[(s[0], b)][0]
                    ok = np.isfinite(ma) & np.isfinite(mb)
                    r = float(np.corrcoef(ma[ok], mb[ok])[0, 1]) if ok.sum() > 10 else float('nan')
                    gaps = [float(np.interp(lm, PHASE, ma) - np.interp(lm, PHASE, mb)) for lm in LANDMARKS]
                    parts.append(f'{a}-{b}: ' + '/'.join(f'{x:+.2g}' for x in gaps) + f' (shape r {r:.2f})')
                    gap_rows.append([task['title'], s[1], s[2], f'{a}-{b}', f'{r:.2f}'] + [f'{x:+.3g}' for x in gaps])
        if parts:
            gap_lines.append(f'LocoHub vs LocoHub, {s[1]} ({s[2]}), mean difference at 0/15/50/85%: ' + '; '.join(parts))
    # LocoHub datasets agree chip (sheet A rule on the signals the training file also has, plus force)
    chip_lh = lh_agreement(cs, g)
    chips.append(chip_lh)
    chips.append(('pass' if tid == 'level' else 'unchecked', 'task match: ' + ('same speed' if tid == 'level' else 'transfer windows, GT23 only' if tid == 'sit_to_stand' else 'ramp speed or stair size not matched')))
    # details
    wrapped = ', '.join(f'{DATASETS[ds][0]} ' + '/'.join(f'{100 * pooled[ds][1].get(c, math.nan):.2f}%' for c in ('ankle_angle', 'shank_angle', 'foot_angle'))
                        for ds in DATASETS)
    head = [f'Task: {task["title"]}. {MATCH_NOTE[tid]}',
            'LocoHub strides (people): ' + '; '.join(f'{DATASETS[ds][0]} {results[ds]["counts"][g]} ({results[ds]["subjects"][g]})' for ds in DATASETS)
            + '. Training strides (people): ' + '; '.join(f'{DATASETS[ds][0]} {trained[ds]["strides"][g]} ({trained[ds]["people"][g]})' for ds in DATASETS)
            + '. The training file holds only some people (GT23 11, GT21 15, UM21 10), so the training mean is over fewer strides than the LocoHub band.',
            'Training strides: the training file has no gait phase (its step counter and swing mask were not used). Each LocoHub stride window of an aligned recording '
            'is cut from the training series with the recording time offset from the ankle-moment fit; 150 inclusive phase times per stride.',
            'Chip rule (this sheet only, not a reference range): reporting sizes 2 deg, 0.05 Nm/kg, 0.05 BW, 0.02 m. Training minus LocoHub per paired stride and phase; '
            'within size = RMS at most the size; constant offset = phase-wise mean differs by more than the size but varies by no more than the size; '
            'phase-dependent = phase-wise mean varies by more than the size; scatter only = mean curve inside the size but RMS past it. Failed = offset or phase-dependent; '
            'scatter only or missing = not checked.',
            f'CoP: training is stored 0.100 m forward of the LocoHub origin (comparison script setting); panels and numbers here are in the LocoHub origin, differences are unaffected.',
            f'Share of angle samples that differ by about a half or whole turn (wrapped), ankle/shank/foot, all time-matched samples: {wrapped}.',
            'Mean differences between LocoHub datasets use the first dataset minus the second at 0, 15, 50 and 85% phase (linear interpolation of the mean curves).']
    details = head + details + gap_lines + [
        'Sources: ' + ', '.join(f'{ds} {DATASETS[ds][1]}' for ds in DATASETS) + ' filtered phase tables; training comparison runs docs/quality/audits/training-compare-v2-*; '
        'training files es_prepared/gate/{gtech_2023,gtech_2021,umich_2021}_time.parquet. Builder: contributor_tools/build_review_sheet_locohub_training.py']
    caps = ['Solid: LocoHub mean ± 1 SD. Dashed: training mean.', 'Same colours and lines.']
    figures = [([f'{sg}.png' for sg in sigs], q, c, f'LocoHub bands and dashed training means for {task["words"]}: ' + ', '.join(sigs))
               for (q, sigs), c in zip(FIGURES, caps)]
    not_shown = ['Training pelvis, thigh, hip, knee (not in training file)', 'Other training partitions', 'Differences between people']
    page(out / 'index.html', title=f'LocoHub and training: {task["title"]}', ask='Check the training versions against LocoHub.',
         headline=f'{task["title"]}: GT23, GT21, UM21', chips=chips, figures=figures, not_shown=not_shown,
         reply='ok  |  which signal looks wrong', details=details)
    with (out / 'stats_paired.csv').open('w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['task', 'dataset', 'column', 'unit', 'reporting size', 'training strides', 'paired samples', 'mean (training minus LocoHub)', 'RMS', 'p95 abs', 'corr',
                    '% past size', 'class', 'phase-wise mean offset', 'phase-wise range'])
        w.writerows(stat_rows)
    with (out / 'gaps_locohub_only.csv').open('w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['task', 'signal', 'unit', 'pair (first minus second)', 'shape r'] + [f'mean diff at {lm}%' for lm in LANDMARKS])
        w.writerows(gap_rows)
    return chips, stat_rows


def lh_agreement(cs, g):
    """Sheet A's rule on the LocoHub bands (3 datasets): pass = shape r >= 0.9 and landmark gaps within 1 SD of the wider dataset."""
    names = list(DATASETS)
    worst_state, bits = 'pass', []
    for s in SIGNALS:
        pairs = []
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if (s[0], a) in cs and (s[0], b) in cs:
                    ma, sa_ = cs[(s[0], a)][0], cs[(s[0], a)][1]
                    mb, sb = cs[(s[0], b)][0], cs[(s[0], b)][1]
                    ok = np.isfinite(ma) & np.isfinite(mb)
                    if ok.sum() <= 10:
                        continue
                    r = float(np.corrcoef(ma[ok], mb[ok])[0, 1])
                    ratio = max(abs(float(np.interp(lm, PHASE, ma) - np.interp(lm, PHASE, mb))) /
                                max(float(np.interp(lm, PHASE, sa_)), float(np.interp(lm, PHASE, sb)), 1e-12) for lm in LANDMARKS)
                    flat = bool(max(np.nanmax(ma) - np.nanmin(ma), np.nanmax(mb) - np.nanmin(mb)) < np.nanmedian(np.concatenate([sa_, sb])))
                    pairs.append((r, ratio, flat))
        if len([1 for ds in names if (s[0], ds) in cs]) < 2:
            continue
        if any((not f) and r < 0 for r, _, f in pairs):
            st = 'fail'
        elif all((f or r >= 0.9) and ratio <= 1.0 for r, ratio, f in pairs):
            st = 'pass'
        else:
            st = 'unchecked'
        rank = {'pass': 0, 'unchecked': 1, 'fail': 2}
        if rank[st] > rank[worst_state]:
            worst_state = st
        if st != 'pass':
            bits.append({'pelvis_seg': 'pelvis', 'thigh_seg': 'thigh', 'shank_seg': 'shank', 'foot_seg': 'foot', 'hip_angle': 'hip angle', 'knee_angle': 'knee angle', 'ankle_angle': 'ankle angle', 'ankle_moment': 'ankle moment', 'grf_v': 'force', 'cop_a': 'CoP'}[s[0]])
    text = 'LocoHub datasets overlap on all ten signals' if not bits else 'LocoHub datasets differ (cause not established) in ' + ', '.join(bits)
    if worst_state == 'fail':
        text = 'LocoHub datasets have opposite shape in ' + ', '.join(bits)
    return worst_state, text


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    results, trained, pooled = {}, {}, {}
    for ds in DATASETS:
        results[ds] = collect_locohub(ds)
        trained[ds] = collect_training(ds, results[ds])
        pooled[ds] = pooled_dataset_stats(ds)
    index, sheets = [], []
    for g, tid in enumerate(TASK_IDS):
        chips, _ = build_task(results, trained, tid, g, pooled)
        sheets.append(OUT / tid / 'index.html')
        index.append((tid, chips))
    marks = {'pass': 'pass', 'fail': 'FAILED', 'unchecked': 'not checked'}
    html = ['<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>LocoHub datasets and the training versions</title>'
            '<body style="font:16px/1.5 system-ui;max-width:900px;margin:20px auto;padding:0 16px">'
            '<h1>Do the training versions match LocoHub, and do the datasets match each other?</h1>'
            '<p>Per task: LocoHub bands (solid) and training means (dashed), GT23 blue, GT21 orange, UM21 green. Current packages: GT23 v12, GT21 v2, UM21 v6.</p><ul>']
    for tid, chips in index:
        html.append(f'<li><a href="{tid}/index.html">{TASKS[tid]["title"]}</a><ul>' + ''.join(f'<li>{marks[s]}: {t}</li>' for s, t in chips) + '</ul></li>')
    html.append('</ul><h2>Training minus LocoHub, every time-matched sample</h2><p>All tasks the training file holds, aligned recordings only. '
                'Mean, RMS and share past the reporting size are pooled over people; p95 and correlation are medians over people. '
                'Unit: degrees, Nm/kg, BW, metres (CoP in the training origin, LocoHub + 0.100 m).</p>')
    html.append('<table border="1" cellpadding="4" style="border-collapse:collapse;font-size:14px"><tr><th>Dataset</th><th>Signal</th><th>Samples</th><th>Mean</th><th>RMS</th>'
                '<th>p95</th><th>Corr</th><th>Past size</th><th>Wrapped</th></tr>')
    csv_rows = []
    for ds in DATASETS:
        stats, wrap, align, reasons, fails = pooled[ds]
        for name in ('ankle_angle', 'shank_angle', 'foot_angle', 'ankle_velocity', 'ankle_moment', 'vertical_force', 'cop_anterior'):
            st = stats.get(name)
            if st is None:
                html.append(f'<tr><td>{ds}</td><td>{name}</td><td colspan="7">no matched samples</td></tr>')
                continue
            wr = f'{100 * wrap[name]:.2f}%' if name in wrap else ''
            html.append(f'<tr><td>{ds}</td><td>{name}</td><td>{st["n"]}</td><td>{st["bias"]:+.3g}</td><td>{st["rms"]:.3g}</td><td>{st["p95"]:.3g}</td>'
                        f'<td>{st["corr"]:.3f}</td><td>{100 * st["frac"]:.1f}%</td><td>{wr}</td></tr>')
            csv_rows.append([ds, name, MAPS[name].unit, MAPS[name].size, st['n'], st['people'], f'{st["bias"]:.5g}', f'{st["rms"]:.5g}', f'{st["p95"]:.5g}',
                             f'{st["corr"]:.4f}', f'{100 * st["frac"]:.2f}', f'{100 * wrap[name]:.3f}' if name in wrap else ''])
    html.append('</table><h2>Alignment</h2><ul>')
    for ds in DATASETS:
        stats, wrap, align, reasons, fails = pooled[ds]
        html.append(f'<li>{ds}: {align["matched"]} training recordings aligned, {align["alignment_failed"]} alignment failures'
                    + (f' ({"; ".join(fails)})' if fails else '') + f', {align["no_candidate"]} with no LocoHub candidate or no moment ('
                    + '; '.join(f'{v} {k}' for k, v in reasons.items()) + ')</li>')
    html.append('</ul></body>')
    (OUT / 'index.html').write_text('\n'.join(html), encoding='utf-8')
    with (OUT / 'stats_dataset.csv').open('w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['dataset', 'column', 'unit', 'reporting size', 'samples', 'people', 'mean', 'RMS', 'p95 (median over people)', 'corr (median over people)', '% past size', '% wrapped'])
        w.writerows(csv_rows)
    (OUT / 'summary.json').write_text(json.dumps({tid: [{'state': s, 'text': t} for s, t in chips] for tid, chips in index}, indent=1), encoding='utf-8')
    if '--render' in sys.argv:
        sa.render(sheets + [OUT / 'index.html'])


if __name__ == '__main__':
    main()
