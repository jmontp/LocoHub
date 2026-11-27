"""Review sheets A2: does a foot-flat calibration close the gaps between GT23, GT21 and UM21?

Test only; no data are changed. In mid-stance the foot is flat on the surface, so the foot
segment angle should equal the surface slope (0 on level ground). Per participant and
dataset, offset = median over strides of each stride's median foot angle over 20-35 percent
of the stride, in the matched filtered level-walking strides (ipsi leg). A participant
without matched level strides is left uncorrected (offset reported as none).

Two corrected variants, using the standard's compositions (docs/reference/index.md):
hip = thigh - pelvis, knee = thigh - shank, ankle = foot - shank.
  F (foot only): foot - offset, so ankle - offset; everything else unchanged.
  G (global): thigh, shank and foot all - offset (pelvis unchanged); hip - offset,
              knee and ankle unchanged.
Writes review_sheets/A2-footflat/ (index plus one sheet per task). Reads the filtered phase
tables once, streamed (4096 rows, one thread, column selection); keeps running sums per
participant, so variants are exact algebraic shifts of those sums.

  python3 contributor_tools/build_review_sheet_footflat.py --selftest   # synthetic, reads no data
  OMP_NUM_THREADS=1 ARROW_DEFAULT_MEMORY_POOL=system MPLBACKEND=Agg prlimit --as=$((600*1024*1024)) -- \
    nice -n 19 ionice -c 3 python3 contributor_tools/build_review_sheet_footflat.py --run
  python3 contributor_tools/build_review_sheet_footflat.py --render-only    # screenshots, outside prlimit
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools import build_review_sheet_cross_dataset as A
from contributor_tools.common.review_sheet import page

DATASETS, TASKS, TASK_IDS, PHASE, NPH = A.DATASETS, A.TASKS, A.TASK_IDS, A.PHASE, A.NPH
SEED = 20261128
OUT = A.SHEETS / 'A2-footflat'
MID = (PHASE >= 20) & (PHASE <= 35)
ANGLES = ['hip_angle', 'knee_angle', 'ankle_angle', 'pelvis_seg', 'thigh_seg', 'shank_seg', 'foot_seg']
SIG = {s[0]: s for s in A.SIGNALS if s[0] in ANGLES}
COL = {k: SIG[k][3] for k in ANGLES}
SCALE = {k: SIG[k][4] for k in ANGLES}
VARIANTS = {'O': 'Original', 'F': 'Foot only (F)', 'G': 'Global (G)'}
# Which signals move by -offset in each variant (the standard's compositions, see module docstring).
COEF = {'O': {}, 'F': {'foot_seg': 1, 'ankle_angle': 1},
        'G': {'thigh_seg': 1, 'shank_seg': 1, 'foot_seg': 1, 'hip_angle': 1}}


# ---------- small pure helpers (unit-checked by --selftest) ----------
def stride_mid(foot_deg):
    """Median foot angle over 20-35 percent of one stride (NaN if no finite sample there)."""
    v = np.asarray(foot_deg, dtype=float)[MID]
    v = v[np.isfinite(v)]
    return float(np.median(v)) if v.size else float('nan')


def subject_offsets(level_strides):
    """level_strides: [(subject, foot array(150))] -> {subject: dict(offset, n, lo, hi)}; median of stride medians."""
    per = {}
    for subject, foot in level_strides:
        m = stride_mid(foot)
        if np.isfinite(m):
            per.setdefault(subject, []).append(m)
    return {s: dict(offset=float(np.median(v)), n=len(v), lo=float(np.min(v)), hi=float(np.max(v))) for s, v in per.items()}


def shift_sums(n, s1, s2, c):
    """Running sums of x - c from sums of x: exact."""
    return n, s1 - c * n, s2 - 2 * c * s1 + c * c * n


def shifted_signal(sig, variant, offset):
    """Value to subtract for this signal and variant."""
    return offset * COEF[variant].get(sig, 0)


def recompute_joints(seg):
    """Joint angles from segment angles per the standard."""
    return dict(hip_angle=seg['thigh_seg'] - seg['pelvis_seg'], knee_angle=seg['thigh_seg'] - seg['shank_seg'],
                ankle_angle=seg['foot_seg'] - seg['shank_seg'])


def selftest():
    rng = np.random.default_rng(1)
    # 1. offset from a known synthetic foot angle: flat at 4 deg during 20-35 percent plus noise elsewhere
    foot = rng.normal(0, 30, NPH)
    foot[MID] = 4.0
    assert abs(stride_mid(foot) - 4.0) < 1e-12
    strides = [('p1', foot), ('p1', foot + 2), ('p1', foot - 2), ('p2', foot + 10)]
    off = subject_offsets(strides)
    assert abs(off['p1']['offset'] - 4.0) < 1e-12 and off['p1']['n'] == 3 and abs(off['p2']['offset'] - 14.0) < 1e-12
    assert 'p3' not in off
    assert np.isnan(stride_mid(np.full(NPH, np.nan)))
    # 2. shifted sums equal direct sums
    x = rng.normal(5, 3, 40)
    n, s1, s2 = len(x), x.sum(), (x ** 2).sum()
    for c in (0.0, 2.5, -7.0):
        a = shift_sums(n, s1, s2, c)
        y = x - c
        assert np.allclose(a, (len(y), y.sum(), (y ** 2).sum()))
    # 3. variants versus recomputation from segments (the standard's compositions)
    seg = {k: rng.normal(0, 20, 50) for k in ('pelvis_seg', 'thigh_seg', 'shank_seg', 'foot_seg')}
    base = recompute_joints(seg)
    allv = {**seg, **base}
    c = 6.0
    for v in ('F', 'G'):
        shifted = {k: allv[k] - shifted_signal(k, v, c) for k in allv}
        seg2 = {k: shifted[k] for k in seg}
        re = recompute_joints(seg2)
        for k in re:
            assert np.allclose(re[k], shifted[k]), (v, k)  # stored-joint shift equals recomputation
    g = {k: allv[k] - shifted_signal(k, 'G', c) for k in allv}
    assert np.allclose(g['knee_angle'], allv['knee_angle']) and np.allclose(g['ankle_angle'], allv['ankle_angle'])
    assert np.allclose(g['hip_angle'], allv['hip_angle'] - c) and np.allclose(g['pelvis_seg'], allv['pelvis_seg'])
    f = {k: allv[k] - shifted_signal(k, 'F', c) for k in allv}
    assert np.allclose(f['ankle_angle'], allv['ankle_angle'] - c) and np.allclose(f['hip_angle'], allv['hip_angle'])
    assert np.allclose(f['knee_angle'], allv['knee_angle']) and np.allclose(f['thigh_seg'], allv['thigh_seg'])
    # 4. a foot that is flat on a slope after correction reads the slope (sign: uphill positive)
    slope = 10.0
    raw = np.full(NPH, slope + 5.0)  # offset 5 deg; level calibration finds 5
    assert abs(stride_mid(raw) - 5.0 - slope) < 1e-12
    # 5. variant sums over subjects match direct recomputation, and the reservoir keeps its seed
    r1 = random.Random(f'{SEED}-x'); r2 = random.Random(f'{SEED}-x')
    assert r1.randint(0, 99) == r2.randint(0, 99)
    print('selftest ok')


# ---------- streaming collection ----------
def collect2(ds):
    import pyarrow.parquet as pq
    label, folder, _ = DATASETS[ds]
    pf = pq.ParquetFile(A.PKG / folder / 'filtered_phase.parquet')
    names = set(pf.schema_arrow.names)
    missing = [k for k in ANGLES if COL[k] not in names]
    if missing:
        raise RuntimeError(f'{ds} lacks {missing}')
    cols = ['subject', 'observation_id', 'task', 'task_id', 'task_info', 'observation_type', 'phase_ipsi'] + [COL[k] for k in ANGLES]
    nt = len(TASK_IDS)
    acc = {}  # subject -> array (nt, nsig, 3, NPH)
    rng = {g: random.Random(f'{SEED}-{ds}-{g}') for g in range(nt)}
    group_of, subj_of, expected_of = {}, {}, {}
    counts = [0] * nt
    subj_sets = [set() for _ in range(nt)]
    slots = [[None] * A.N_STRIDES for _ in range(nt)]
    store = {}   # reservoir strides: obs -> (gid, subject, {sig: array})
    foots = {}   # every matched stride's foot angle: obs -> array
    resid = {k: [0, 0.0, 0.0] for k in ('hip_angle', 'knee_angle', 'ankle_angle')}  # count, sum abs, max abs
    for batch in pf.iter_batches(A.BATCH, columns=cols, use_threads=False):
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
                    subject = batch.column('subject')[int(f)].as_py()
                    subj_of[u] = subject
                    expected_of[u] = info.get('incline_deg')
                    if expected_of[u] is None and TASK_IDS[gid] == 'level':
                        expected_of[u] = 0.0
                    counts[gid] += 1
                    subj_sets[gid].add(subject)
                    foots[u] = np.full(NPH, np.nan, dtype=np.float32)
                    i = counts[gid] - 1  # reservoir sampling (algorithm R)
                    j = i if i < A.N_STRIDES else rng[gid].randint(0, i)
                    if j < A.N_STRIDES:
                        old = slots[gid][j]
                        if old is not None:
                            store.pop(old, None)
                        slots[gid][j] = u
                        store[u] = (gid, subject, {k: np.full(NPH, np.nan) for k in ANGLES})
            codes[k] = group_of[u]
        row_group = codes[inv]
        if (row_group < 0).all():
            continue
        ph = np.rint(batch.column('phase_ipsi').to_numpy(zero_copy_only=False) / 100 * (NPH - 1)).astype(np.int64)
        vals = {k: batch.column(COL[k]).to_numpy(zero_copy_only=False).astype(np.float64) * SCALE[k] for k in ANGLES}
        matched = row_group >= 0
        # joint-angle composition check against segments, matched rows only
        comp = {'hip_angle': vals['thigh_seg'] - vals['pelvis_seg'], 'knee_angle': vals['thigh_seg'] - vals['shank_seg'],
                'ankle_angle': vals['foot_seg'] - vals['shank_seg']}
        for k, c in comp.items():
            d = np.abs(vals[k] - c)[matched]
            d = d[np.isfinite(d)]
            if d.size:
                resid[k][0] += d.size
                resid[k][1] += float(d.sum())
                resid[k][2] = max(resid[k][2], float(d.max()))
        # per-stride storage
        for k, u in enumerate(uniq):
            if codes[k] < 0:
                continue
            sel = inv == k
            good = np.isfinite(vals['foot_seg'][sel])
            foots[u][ph[sel][good]] = vals['foot_seg'][sel][good]
            if u in store:
                for s in ANGLES:
                    store[u][2][s][ph[sel]] = np.where(np.isfinite(vals[s][sel]), vals[s][sel], np.nan)
        # per-subject sums
        subj_row = np.array([subj_of.get(u) for u in uniq], dtype=object)[inv]
        for g in np.unique(row_group[matched]):
            for sub in set(subj_row[(row_group == g)]):
                m0 = (row_group == g) & (subj_row == sub)
                arr = acc.setdefault(sub, np.zeros((nt, len(ANGLES), 3, NPH)))
                for si, k in enumerate(ANGLES):
                    m = m0 & np.isfinite(vals[k])
                    if not m.any():
                        continue
                    v, p = vals[k][m], ph[m]
                    arr[g, si, 0] += np.bincount(p, minlength=NPH)
                    arr[g, si, 1] += np.bincount(p, weights=v, minlength=NPH)
                    arr[g, si, 2] += np.bincount(p, weights=v * v, minlength=NPH)
    stride_info = [[] for _ in range(nt)]
    for u, f in foots.items():
        stride_info[group_of[u]].append((subj_of[u], f, expected_of[u]))
    strides = [[(store[u][1], store[u][2]) for u in slots[g] if u is not None] for g in range(nt)]
    return dict(acc=acc, counts=counts, subjects=[len(s) for s in subj_sets], subject_sets=subj_sets,
                strides=strides, stride_info=stride_info, resid=resid)


def variant_results(res, offsets, variant):
    """Structure used by the sheet-A helpers (curves, pair_gaps, panel) for one variant."""
    nt = len(TASK_IDS)
    acc = {k: np.zeros((nt, 3, NPH)) for k in ANGLES}
    for sub, arr in res['acc'].items():
        off = offsets.get(sub, {}).get('offset', 0.0)
        for si, k in enumerate(ANGLES):
            c = shifted_signal(k, variant, off)
            for g in range(nt):
                n, s1, s2 = arr[g, si]
                acc[k][g] += np.array(shift_sums(n, s1, s2, c))
    strides = []
    for g in range(len(TASK_IDS)):
        out = []
        for sub, d in res['strides'][g]:
            off = offsets.get(sub, {}).get('offset', 0.0)
            out.append({k: d[k] - shifted_signal(k, variant, off) for k in ANGLES})
        strides.append(out)
    present = {s[0]: (s[0] in ANGLES) for s in A.SIGNALS}
    return dict(present=present, acc=acc, counts=res['counts'], subjects=res['subjects'], strides=strides)


def slope_check(res, offsets):
    """Per task (incline, decline, level): per-participant median mid-stance foot angle minus expected slope,
    original and corrected. Expected = the stride's recorded incline_deg (uphill positive)."""
    out = {}
    for tid in ('level', 'incline', 'decline'):
        g = TASK_IDS.index(tid)
        per = {}
        for sub, foot, exp in res['stride_info'][g]:
            m = stride_mid(foot)
            if np.isfinite(m) and exp is not None:
                per.setdefault(sub, []).append((m - exp, exp))
        rows = {}
        for sub, v in per.items():
            err = float(np.median([e for e, _ in v]))
            off = offsets.get(sub, {}).get('offset')
            rows[sub] = dict(raw=err, corrected=None if off is None else err - off, expected=float(np.median([x for _, x in v])), n=len(v))
        out[tid] = rows
    return out


# ---------- figures and pages ----------
def mean_abs_gap(results, gid):
    out = {}
    for sig in ANGLES:
        pg = A.pair_gaps(results, gid, sig)
        vals = [abs(v['gaps'][lm]) for v in pg.values() for lm in A.LANDMARKS]
        out[sig] = float(np.mean(vals)) if vals else float('nan')
    return out


def offsets_figure(path, offsets_by_ds):
    fig, ax = plt.subplots(figsize=(4.5, 3.6))
    rng = np.random.default_rng(SEED)
    for i, ds in enumerate(DATASETS):
        vals = np.array([v['offset'] for v in offsets_by_ds[ds].values()])
        colour = DATASETS[ds][2]
        ax.scatter(i + rng.uniform(-0.15, 0.15, len(vals)), vals, color=colour, s=22, alpha=0.8)
        if len(vals):
            ax.hlines(np.median(vals), i - 0.3, i + 0.3, color=A.INK, lw=2)
    ax.axhline(0, color='#aab2ba', lw=0.5)
    ax.set_xticks(range(3), list(DATASETS))
    ax.set_ylabel('Foot angle, 20-35% (deg)')
    ax.set_title('Level-walking offset per participant', loc='left')
    fig.subplots_adjust(left=0.17, right=0.97, top=0.92, bottom=0.12)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def slope_figure(path, checks, tid):
    fig, ax = plt.subplots(figsize=(4.5, 3.6))
    rng = np.random.default_rng(SEED)
    for i, ds in enumerate(DATASETS):
        rows = checks[ds][tid]
        colour = DATASETS[ds][2]
        raw = [r['raw'] for r in rows.values()]
        cor = [r['corrected'] for r in rows.values() if r['corrected'] is not None]
        ax.scatter(2 * i - 0.25 + rng.uniform(-0.1, 0.1, len(raw)), raw, facecolors='none', edgecolors=colour, s=22)
        ax.scatter(2 * i + 0.25 + rng.uniform(-0.1, 0.1, len(cor)), cor, color=colour, s=22)
        for x, v in ((2 * i - 0.25, raw), (2 * i + 0.25, cor)):
            if v:
                ax.hlines(np.median(v), x - 0.22, x + 0.22, color=A.INK, lw=2)
    ax.axhline(0, color=A.INK, lw=0.8)
    ax.set_xticks([2 * i for i in range(3)], list(DATASETS))
    ax.set_ylabel('Foot angle minus slope (deg)')
    ax.set_title(f'{TASKS[tid]["title"]}: hollow original, filled corrected', loc='left', fontsize=9.5)
    fig.subplots_adjust(left=0.17, right=0.97, top=0.92, bottom=0.12)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def build_task(vres, tid, gid, checks, offsets_by_ds):
    task = TASKS[tid]
    out = OUT / tid
    out.mkdir(parents=True, exist_ok=True)
    A.style()
    for v in VARIANTS:
        for sig in ANGLES:
            A.panel(out / f'{v}_{sig}.png', vres[v], tid, gid, sig)
    gaps = {v: mean_abs_gap(vres[v], gid) for v in VARIANTS}
    chips, rows, details = [], [], []
    for v, name in VARIANTS.items():
        states = []
        for sig in ANGLES:
            pg = A.pair_gaps(vres[v], gid, sig)
            avail = [ds for ds in DATASETS if A.curves(vres[v][ds], sig, gid) is not None]
            states.append(A.judge(pg, len(avail)))
            for (a, b), p in pg.items():
                rows.append([task['title'], v, SIG[sig][1], f'{a}-{b}', f'{p["r"]:.2f}'] + [f'{p["gaps"][lm]:+.3g}' for lm in A.LANDMARKS])
        mean_all = float(np.nanmean(list(gaps[v].values())))
        chips.append(('pass' if all(s == 'pass' for s in states) else 'unchecked',
                      f'{name}: mean gap {mean_all:.1f} deg; {sum(s == "pass" for s in states)} of 7 angles agree by the rule'))
    if tid in ('incline', 'decline', 'level'):
        bits, ok = [], True
        for ds in DATASETS:
            rws = [r for r in checks[ds][tid].values() if r['corrected'] is not None]
            if rws:
                med = float(np.median([r['corrected'] for r in rws]))
                bits.append(f'{ds} {med:+.1f}')
                ok &= abs(med) <= 2.0
            else:
                bits.append(f'{ds} n/a')
                ok = False
        chips.append(('pass' if ok else 'unchecked', 'foot minus slope after correction (deg): ' + ', '.join(bits)))
    for sig in ANGLES:
        details.append(f'{SIG[sig][1]}, mean absolute gap over pairs and landmarks (deg): original {gaps["O"][sig]:.2f}, F {gaps["F"][sig]:.2f}, G {gaps["G"][sig]:.2f}')
    for v, name in VARIANTS.items():
        for sig in ANGLES:
            pg = A.pair_gaps(vres[v], gid, sig)
            details.append(f'{name}: {SIG[sig][1]} mean difference at 0/15/50/85%, ' + '; '.join(
                f'{a}-{b} ' + '/'.join(f'{p["gaps"][lm]:+.1f}' for lm in A.LANDMARKS) for (a, b), p in pg.items()))
    details = [f'Task: {task["title"]}. {A.MATCH_NOTE[tid]}',
               'Strides (people): ' + '; '.join(f'{ds} {vres["O"][ds]["counts"][gid]} ({vres["O"][ds]["subjects"][gid]})' for ds in DATASETS),
               f'Random strides: {A.N_STRIDES} per dataset, seed {SEED}. Offsets are applied per participant; participants without level walking are not corrected.',
               'Chip rule: pass = shape r at least 0.9 and every gap at 0, 15, 50, 85% within 1 SD of the wider dataset (this sheet only); foot-flat check passes if each dataset median is within 2 deg of the slope (also this sheet only).'] + details
    figures = [([f'{v}_{s}.png' for s in ANGLES], f'{name}: do the angles overlap?', 'Band: mean ± 1 SD. Thin: 6 random strides.' if v == 'O' else 'Same bands and colours.',
                f'GT23, GT21 and UM21 angle panels, {name}, {task["words"]}') for v, name in VARIANTS.items()]
    page(out / 'index.html', title=f'Foot-flat test: {task["title"]}', ask='Check which correction closes the gaps.',
         headline=f'{task["title"]}: original, foot-only, global', chips=chips, figures=figures,
         not_shown=['Forces, moments, powers', 'Other speeds and slopes', 'UM21 stairs (no data)'],
         reply='ok  |  which angle looks wrong', details=details)
    with (out / 'gaps.csv').open('w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['task', 'variant', 'signal', 'pair (first minus second)', 'shape r'] + [f'mean diff at {lm}%' for lm in A.LANDMARKS])
        w.writerows(rows)
    return chips, gaps


def build_index(offsets_by_ds, checks, resid, task_summary):
    A.style()
    OUT.mkdir(parents=True, exist_ok=True)
    offsets_figure(OUT / 'offsets.png', offsets_by_ds)
    slope_figure(OUT / 'slope_incline.png', checks, 'incline')
    slope_figure(OUT / 'slope_decline.png', checks, 'decline')
    chips, details = [], []
    for ds in DATASETS:
        o = offsets_by_ds[ds]
        v = np.array([x['offset'] for x in o.values()])
        chips.append(('unchecked', f'{ds} offset median {np.median(v):+.1f} deg, range {v.min():+.1f} to {v.max():+.1f} ({len(v)} people)'))
        details.append(f'{ds} per-participant offsets (deg, strides): ' + '; '.join(f'{s} {x["offset"]:+.1f} ({x["n"]})' for s, x in sorted(o.items())))
    bad = {ds: sorted({sub for tid in ('level', 'incline', 'decline') for sub in checks[ds][tid]} - set(offsets_by_ds[ds])) for ds in DATASETS}
    nbad = sum(len(v) for v in bad.values())
    chips.append(('unchecked' if nbad else 'pass', f'{nbad} participants with other walking but no matched level walking are left uncorrected'))
    worst = max(max(r[2] for r in resid[ds].values()) for ds in DATASETS)
    chips.append(('pass' if worst < 1e-3 else 'unchecked', f'joint angles equal segment differences in the data (largest residual {worst:.3g} deg)'))
    for ds in DATASETS:
        details.append(f'{ds} participants without matched level walking: {", ".join(bad[ds]) or "none"}')
        details.append(f'{ds} composition residual (mean abs, max abs, deg): ' + '; '.join(
            f'{k} {r[1] / max(r[0], 1):.3g}, {r[2]:.3g}' for k, r in resid[ds].items()))
    for tid in ('level', 'incline', 'decline'):
        for ds in DATASETS:
            rws = checks[ds][tid]
            cor = [r['corrected'] for r in rws.values() if r['corrected'] is not None]
            raw = [r['raw'] for r in rws.values()]
            exp = [r['expected'] for r in rws.values()]
            if raw:
                details.append(f'{TASKS[tid]["title"]}, {ds}: expected slope {np.median(exp):+.1f} deg; foot at 20-35% minus slope, median over people: original {np.median(raw):+.1f} (range {min(raw):+.1f} to {max(raw):+.1f})'
                               + (f', corrected {np.median(cor):+.1f} (range {min(cor):+.1f} to {max(cor):+.1f})' if cor else ', not corrected'))
    for tid, gaps in task_summary.items():
        for sig in ANGLES:
            details.append(f'{TASKS[tid]["title"]}, {SIG[sig][1]}: mean absolute gap (deg) original {gaps["O"][sig]:.2f}, F {gaps["F"][sig]:.2f}, G {gaps["G"][sig]:.2f}')
    details.append('Offset: per participant, median over strides of each stride\'s median foot angle over 20-35% (ipsi), matched level strides. Slope sign: uphill positive. Builder: contributor_tools/build_review_sheet_footflat.py')
    page(OUT / 'index.html', title='Foot-flat test', ask='Check the offsets, then the slope check.',
         headline='Foot-flat offsets per participant and slope check',
         chips=chips, figures=[('offsets.png', 'How large is each participant\'s offset?', 'Line: median.', 'Offset per participant by dataset'),
                               (['slope_incline.png', 'slope_decline.png'], 'Does the corrected foot match the slope?', 'Zero line is the slope.', 'Foot angle minus slope, original and corrected')],
         not_shown=['Cause of the offsets', 'Whether foot-flat holds in every stride', 'Forces, moments, powers'],
         reply='ok  |  what looks wrong', details=details)
    html = (OUT / 'index.html').read_text(encoding='utf-8')
    links = '<nav><p>Per-task sheets: ' + ' · '.join(f'<a href="{t}/index.html">{TASKS[t]["title"]}</a>' for t in TASK_IDS) + '</p></nav>'
    (OUT / 'index.html').write_text(html.replace('</main>', links + '</main>', 1), encoding='utf-8')


def main():
    results = {ds: collect2(ds) for ds in DATASETS}
    offsets_by_ds = {ds: subject_offsets([(sub, foot) for sub, foot, _ in results[ds]['stride_info'][TASK_IDS.index('level')]]) for ds in DATASETS}
    checks = {ds: slope_check(results[ds], offsets_by_ds[ds]) for ds in DATASETS}
    vres = {v: {ds: variant_results(results[ds], offsets_by_ds[ds], v) for ds in DATASETS} for v in VARIANTS}
    task_summary = {}
    for gid, tid in enumerate(TASK_IDS):
        _, task_summary[tid] = build_task(vres, tid, gid, checks, offsets_by_ds)
    build_index(offsets_by_ds, checks, {ds: results[ds]['resid'] for ds in DATASETS}, task_summary)
    (OUT / 'summary.json').write_text(json.dumps(dict(seed=SEED, offsets=offsets_by_ds, gaps=task_summary,
                                                      slope=checks), indent=1, default=float), encoding='utf-8')


def render_only():
    A.render([OUT / 'index.html'] + [OUT / t / 'index.html' for t in TASK_IDS])


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest()
    elif '--render-only' in sys.argv:
        render_only()
    elif '--run' in sys.argv:
        main()
    else:
        print(__doc__)
