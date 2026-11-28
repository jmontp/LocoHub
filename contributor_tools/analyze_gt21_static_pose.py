"""A3: does a standing-pose offset in the Georgia Tech 2021 (GT21) model explain why LocoHub's GT21 knee is more flexed in
level walking than GT23 and UM21?  DRAFT: written in phase 1, not run.

Inputs (read only)
  * the static-trial export of gt21_static_export.m (new root converted_datasets/reconversion_v2/gt21_static_export_v1/<AB##>/):
    static markers, authors' static ik and ik_offset, plus static_meta_<AB##>.json (column names, units);
  * the participant's scaled model and the RB01 weight export, exactly as run_gt21_rb_pass.py reads them;
  * the filtered phase tables of the GT21 package v1, GT23 review v11 and UM21 package v5 (streamed, bounded batches).

What is computed
  (a) the authors' IK hip, knee and ankle angles averaged over each static trial, converted to the LocoHub sign rule
      (knee flexion = minus the OpenSim knee_angle, per common/CLAUDE.md; hip and ankle unchanged); the raw knee column is kept;
  (b) LocoHub's own pelvis, thigh, shank, foot segment angles and hip, knee, ankle joint angles from the static markers by
      calling gt21_rb_pass.process_recording itself (no force plates, no gait events, no moments: those inputs do not exist
      for a static trial and the geometry block does not use them). The geometry is therefore the merged pass's own code.
      If the static trial lacks the thigh or shank marker cluster the pass needs (fewer than three fit markers), the SAME
      call is repeated with the pass's cluster tuples temporarily widened (module attributes THIGH_CLUSTER, SHANK_CLUSTER) to
      every other marker the scaled model puts on that body and the static trial has. Such participants are labelled
      route=widened_cluster_markers; they are not the walking-trial geometry and the sheet says so;
  (c) per-participant mean of each segment/joint angle in 20-35 percent phase of GT21, GT23 and UM21 level walking (the
      sheet-A task rule is imported, not copied), the GT21 minus reference gap, and the gap if each person's standing angle
      were subtracted (GT23 and UM21 left as published: they have no standing data here).

No file under converted_datasets/ or any source folder is changed. Missing stays missing: a trial with no valid frame has no
value and is counted, never filled.

Run (see the report): `compute` writes a NEW out-root (CSV and JSON only; through the guarded launcher or as a read-only probe
under prlimit, nice 19, ionice idle); `sheet` reads the small CSV and writes review_sheets/A3-gt21-standing/.
"""
import os
for _k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_k] = '1'
os.environ.setdefault('ARROW_DEFAULT_MEMORY_POOL', 'system')
import argparse
import contextlib
import csv
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

D = 180.0 / math.pi
RECON = ROOT / 'converted_datasets/reconversion_v2'
STATIC_ROOT = RECON / 'gt21_static_export_v1'
LABELS = RECON / 'gt21_rb01_labels_final_20261124'
SHEET_DIR = ROOT / 'review_sheets/A3-gt21-standing'
FOLDERS = {'GT21': 'gt21_r01_package_v1', 'GT23': 'gt23_r01_review_v11', 'UM21': 'um21_r01_package_v5'}
REFS = ('GT23', 'UM21')
WINDOW = (20.0, 35.0)                      # percent of stride; the mid-stance window of this check
QUANT = ('thigh', 'shank', 'foot', 'pelvis', 'hip', 'knee', 'ankle')
PARQUET_COLUMN = {'thigh': 'thigh_sagittal_angle_ipsi_rad', 'shank': 'shank_sagittal_angle_ipsi_rad',
                  'foot': 'foot_sagittal_angle_ipsi_rad', 'pelvis': 'pelvis_sagittal_angle_rad',
                  'hip': 'hip_flexion_angle_ipsi_rad', 'knee': 'knee_flexion_angle_ipsi_rad',
                  'ankle': 'ankle_dorsiflexion_angle_ipsi_rad'}
PASS_COLUMN = {'thigh': 'thigh_sagittal_angle_{leg}_rad', 'shank': 'shank_sagittal_angle_{leg}_rad',
               'foot': 'foot_sagittal_angle_{leg}_rad', 'pelvis': 'pelvis_sagittal_angle_rad',
               'hip': 'hip_flexion_angle_{leg}_rad', 'knee': 'knee_flexion_angle_{leg}_rad',
               'ankle': 'ankle_dorsiflexion_angle_{leg}_rad'}
IK_NAMES = {'hip': 'hip_flexion_{s}', 'knee': 'knee_angle_{s}', 'ankle': 'ankle_angle_{s}'}
IK_OFFSET_TOLERANCE_DEG = 0.5              # this check's own rule for "ik_offset averages zero over the static trial"
STEADY_SD_DEG = 2.0                        # this check's own rule for "standing is steady" (knee SD over the trial)
AB = re.compile(r'AB\d\d')


# ------------------------------------------------------------------------------------------------ small pure helpers
def trial_stats(x):
    """(mean, sd, n finite) of a series ignoring non-finite values; (nan, nan, 0) when none is finite."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if not x.size:
        return float('nan'), float('nan'), 0
    return float(x.mean()), float(x.std(ddof=1)) if x.size > 1 else 0.0, int(x.size)


def nanmean_of(values):
    v = np.asarray([x for x in values if x is not None and np.isfinite(x)], float)
    return float(v.mean()) if v.size else float('nan')


def read_csv_columns(path):
    """Named float columns of an export CSV (header row of names, %.17g values, NaN as text)."""
    with open(path, newline='') as f:
        header = next(csv.reader(f))
    data = np.loadtxt(path, delimiter=',', skiprows=1, ndmin=2)
    if data.shape[1] != len(header):
        raise ValueError(f'{path}: {data.shape[1]} columns for {len(header)} names')
    return {name: data[:, i].copy() for i, name in enumerate(header)}


def unit_factor(unit, values):
    """(factor to degrees, assumed). A unit text with 'rad' or 'deg' decides; otherwise degrees are assumed and the
    result is flagged (OpenSim IK output is normally degrees; the sheet lists this as not checked)."""
    text = (unit or '').lower()
    if 'rad' in text:
        return D, False
    if 'deg' in text:
        return 1.0, False
    return 1.0, True


def ik_angles(cols, units, side):
    """Authors' IK means over a static trial in degrees for one side ('r' or 'l'), LocoHub sign rule.

    cols: {name: series}, units: {name: unit text}. Returns dict hip, knee, ankle, knee_raw (OpenSim knee_angle), n (frames),
    knee_sd, units_assumed. Knee flexion = minus the OpenSim knee_angle (common/CLAUDE.md sign table); hip and ankle as stored.
    Missing columns give NaN."""
    out, assumed = {}, False
    for key, template in IK_NAMES.items():
        name = template.format(s=side)
        if name not in cols:
            out[key] = float('nan')
            if key == 'knee':
                out.update(knee_raw=float('nan'), knee_sd=float('nan'), n=0)
            continue
        factor, a = unit_factor(units.get(name, ''), cols[name])
        assumed |= a
        mean, sd, n = trial_stats(np.asarray(cols[name], float) * factor)
        if key == 'knee':
            out.update(knee_raw=mean, knee_sd=sd, n=n)
            mean = -mean
        out[key] = mean
    out['units_assumed'] = assumed
    return out


def ik_offset_self_check(offset_cols, units, side):
    """Largest absolute trial mean (degrees) of the authors' ik_offset hip, knee, ankle: by their definition
    ik_offset = ik - mean(static ik), so each mean over the static trial must be about zero."""
    worst = 0.0
    for template in IK_NAMES.values():
        name = template.format(s=side)
        if name not in offset_cols:
            continue
        factor, _ = unit_factor(units.get(name, ''), offset_cols[name])
        mean, _, n = trial_stats(np.asarray(offset_cols[name], float) * factor)
        if n and np.isfinite(mean):
            worst = max(worst, abs(mean))
    return worst


def leg_means_deg(cols):
    """Per-leg trial means (degrees) of the merged pass's columns for one static trial.

    Returns {'right': {quantity: mean}, 'left': {...}, 'n_valid': {leg: frames with a finite knee angle},
    'knee_sd': {leg: sd}}. Pelvis is shared by both legs."""
    out = {'right': {}, 'left': {}, 'n_valid': {}, 'knee_sd': {}}
    for leg in ('right', 'left'):
        for q in QUANT:
            name = PASS_COLUMN[q].format(leg=leg)
            out[leg][q] = trial_stats(np.asarray(cols[name], float) * D)[0] if name in cols else float('nan')
        knee = np.asarray(cols[PASS_COLUMN['knee'].format(leg=leg)], float) * D
        _, sd, n = trial_stats(knee)
        out['n_valid'][leg], out['knee_sd'][leg] = n, sd
    return out


def both_legs(per_leg):
    """Mean of the two legs' values for each quantity (a leg with no value is skipped)."""
    return {q: nanmean_of([per_leg['right'][q], per_leg['left'][q]]) for q in QUANT}


class WindowMeans:
    """Running per-subject mean of each named series over rows whose phase lies in [lo, hi] (inclusive); values in degrees."""

    def __init__(self, lo=WINDOW[0], hi=WINDOW[1]):
        self.lo, self.hi, self.sum, self.n = lo, hi, {}, {}

    def add(self, subjects, phase, values):
        subjects, phase = np.asarray(subjects, object), np.asarray(phase, float)
        inside = (phase >= self.lo) & (phase <= self.hi)
        for s in np.unique(subjects[inside]):
            rows = inside & (subjects == s)
            for name, v in values.items():
                v = np.asarray(v, float)
                ok = rows & np.isfinite(v)
                key = (str(s), name)
                self.sum[key] = self.sum.get(key, 0.0) + float(v[ok].sum())
                self.n[key] = self.n.get(key, 0) + int(ok.sum())

    def means(self):
        out = {}
        for (s, name), total in self.sum.items():
            n = self.n[(s, name)]
            out.setdefault(s, {})[name] = total / n if n else float('nan')
        return out


def subject_key(label):
    """'AB06' from any subject label that contains it; None otherwise."""
    m = AB.search(str(label))
    return m.group(0) if m else None


def rank(x):
    """Ranks 1..n (average ranks for ties)."""
    x = np.asarray(x, float)
    order = np.argsort(x, kind='mergesort')
    r = np.empty(len(x))
    r[order] = np.arange(1, len(x) + 1)
    for v in np.unique(x):
        m = x == v
        if m.sum() > 1:
            r[m] = r[m].mean()
    return r


def pearson(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 3 or x.std() == 0 or y.std() == 0:
        return float('nan')
    return float(np.corrcoef(x, y)[0, 1])


def compare(stand, mid, ref):
    """Standing offset against the walking gap, across participants, for one quantity.

    stand, mid: equal-length arrays (degrees; one entry per participant): standing mean and mid-stance walking mean in GT21.
    ref: the reference walking mean (scalar, degrees). gap = mid - ref. corrected = mid - stand - ref (standing taken as zero).
    Returns means, SDs, Pearson and Spearman r of gap against stand, OLS slope of gap on stand (1.0 would mean one degree of
    gap per degree of standing offset), and the share of the mean gap that the mean standing offset accounts for."""
    stand, mid = np.asarray(stand, float), np.asarray(mid, float)
    ok = np.isfinite(stand) & np.isfinite(mid)
    stand, mid = stand[ok], mid[ok]
    gap = mid - ref
    corrected = mid - stand - ref
    slope = float(np.polyfit(stand, gap, 1)[0]) if len(stand) >= 3 and stand.std() > 0 else float('nan')
    mean_gap = float(gap.mean()) if len(gap) else float('nan')
    return {'n': int(len(gap)), 'mean_standing': float(stand.mean()) if len(stand) else float('nan'),
            'mean_gap': mean_gap, 'sd_gap': float(gap.std(ddof=1)) if len(gap) > 1 else float('nan'),
            'mean_corrected_gap': float(corrected.mean()) if len(gap) else float('nan'),
            'sd_corrected_gap': float(corrected.std(ddof=1)) if len(gap) > 1 else float('nan'),
            'pearson_r': pearson(stand, gap), 'spearman_r': pearson(rank(stand), rank(gap)) if len(stand) >= 3 else float('nan'),
            'slope_gap_on_standing': slope,
            'share_of_gap_from_standing': float(stand.mean() / mean_gap) if len(gap) and mean_gap not in (0.0,) else float('nan')}


# ------------------------------------------------------------------------------------------------ LocoHub static geometry
def widened_clusters(marker_names, geo):
    """(thigh tuple, shank tuple) of marker names without the side prefix: the pass's own cluster plus every marker the scaled
    model places on a femur or tibia that the static trial also has."""
    from contributor_tools import gt21_rb_pass as rb
    have = set(marker_names)
    thigh, shank = set(rb.THIGH_CLUSTER), set(rb.SHANK_CLUSTER)
    for s, S in (('r', 'R'), ('l', 'L')):
        for name, (body, _) in geo[s]['markers'].items():
            if name.startswith(S + '_') and f'{name}_x' in have:
                if body == f'femur_{s}':
                    thigh.add(name[2:])
                elif body == f'tibia_{s}':
                    shank.add(name[2:])
    return tuple(sorted(thigh)), tuple(sorted(shank))


@contextlib.contextmanager
def patched_clusters(thigh, shank):
    from contributor_tools import gt21_rb_pass as rb
    old = rb.THIGH_CLUSTER, rb.SHANK_CLUSTER
    rb.THIGH_CLUSTER, rb.SHANK_CLUSTER = thigh, shank
    try:
        yield
    finally:
        rb.THIGH_CLUSTER, rb.SHANK_CLUSTER = old


def locohub_static(markers, geo, weight_kg):
    """The merged pass's geometry on one static marker table. Returns (result dict, route text).

    result: leg_means_deg(...) plus 'held_fraction' per leg. Raises rb.RecordingExcluded if even the widened route fails."""
    from contributor_tools import gt21_rb_pass as rb
    try:
        cols, ledger = rb.process_recording(markers, None, None, None, None, geo, weight_kg, 'levelground')
        route = 'pass_unchanged'
    except rb.RecordingExcluded as first:
        if 'fit markers' not in str(first):
            raise
        thigh, shank = widened_clusters(list(markers), geo)
        with patched_clusters(thigh, shank):
            cols, ledger = rb.process_recording(markers, None, None, None, None, geo, weight_kg, 'levelground')
        route = 'widened_cluster_markers'
    res = leg_means_deg(cols)
    res['held_fraction'] = {leg: ledger['fit'][leg]['geometry_hold']['held_frames'] / max(1, ledger['n_samples'])
                            for leg in ('right', 'left')}
    res['n_samples'] = ledger['n_samples']
    return res, route


# Same two source roots as run_gt21_rb_pass.ROOTS (a test compares them). Not imported: that module pulls in scipy.io and
# pyarrow at import, which this probe does not need before the walking tables are streamed (300 MiB budget).
MODEL_ROOTS = {'local_2024_copy_bundle': ROOT / 'contributor_tools/conversion_scripts/Gtech_2021/CAMARGO_ET_AL_J_BIOMECH_DATASET',
               'extracted_2024_copy_zip': Path('/mnt/s/locomotion_data/gt21_author_mirror_2024_extracted')}


def find_model_root(subject):
    for root in MODEL_ROOTS.values():
        if (root / subject / 'osimxml' / f'{subject}.osim').is_file():
            return root
    raise FileNotFoundError(f'no scaled model for {subject}')


def load_geometry_and_weight(subject):
    from contributor_tools import gt21_rb_pass as rb
    root = find_model_root(subject)
    text = (root / subject / 'osimxml' / f'{subject}.osim').read_text()
    geo = {s: rb.model_geometry(text, s) for s in 'rl'}
    info_path = LABELS / subject / f'subject_info_{subject}.json'
    try:
        weight = rb.weight_kg_from_subject_info(json.loads(info_path.read_text()))
    except Exception:                      # the weight never enters angles; NaN, not an invented mass
        weight = float('nan')
    return geo, weight


# ------------------------------------------------------------------------------------------------ static trials
def static_trials(static_root, subject):
    """One row per static markers table of the participant, with its ik and ik_offset partner when present."""
    meta = json.loads((Path(static_root) / subject / f'static_meta_{subject}.json').read_text())
    tables = meta.get('tables') or []
    if isinstance(tables, dict):
        tables = [tables]
    by = {(t['session'], t['recording'], t['channel']): t for t in tables}
    rows = []
    for (session, rec, channel), t in sorted(by.items()):
        if channel == 'markers':
            rows.append({'session': session, 'recording': rec, 'markers': t,
                         'ik': by.get((session, rec, 'ik')), 'ik_offset': by.get((session, rec, 'ik_offset'))})
    return rows, meta


def table_data(static_root, subject, entry):
    cols = read_csv_columns(Path(static_root) / subject / entry['csv'])
    units = dict(zip(entry.get('columns') or [], entry.get('units') or []))
    return cols, units


def analyse_subject(static_root, subject):
    """Per-trial dict list for one participant (never raises for one bad trial: the reason is listed)."""
    rows, meta = static_trials(static_root, subject)
    out = []
    geo = weight = None
    for tr in rows:
        rec = {'subject': subject, 'session': tr['session'], 'recording': tr['recording'], 'status': 'ok', 'reason': ''}
        try:
            if tr['ik'] and tr['ik']['read_ok']:
                cols, units = table_data(static_root, subject, tr['ik'])
                for s, leg in (('r', 'right'), ('l', 'left')):
                    for k, v in ik_angles(cols, units, s).items():
                        rec[f'ik_{leg}_{k}'] = v
            else:
                rec['ik_missing'] = True
            if tr['ik_offset'] and tr['ik_offset']['read_ok'] and tr['ik'] and tr['ik']['read_ok']:
                cols, units = table_data(static_root, subject, tr['ik_offset'])
                rec['ik_offset_max_abs_mean_deg'] = max(ik_offset_self_check(cols, units, s) for s in 'rl')
            if not tr['markers']['read_ok']:
                raise ValueError('static markers table unreadable: ' + tr['markers'].get('error', ''))
            if geo is None:
                geo, weight = load_geometry_and_weight(subject)
            markers, _ = table_data(static_root, subject, tr['markers'])
            res, route = locohub_static(markers, geo, weight)
            rec['route'] = route
            rec['n_samples'] = res['n_samples']
            for leg in ('right', 'left'):
                rec[f'n_valid_{leg}'] = res['n_valid'][leg]
                rec[f'knee_sd_{leg}'] = res['knee_sd'][leg]
                rec[f'held_fraction_{leg}'] = res['held_fraction'][leg]
                for q in QUANT:
                    rec[f'lh_{leg}_{q}'] = res[leg][q]
        except Exception as exc:           # a participant's trial is excluded with its reason; the run goes on
            rec.update(status='excluded', reason=f'{type(exc).__name__}: {exc}'[:300])
        out.append(rec)
    if not rows:
        out.append({'subject': subject, 'status': 'no_static_table', 'reason': json.dumps(meta.get('tables'))[:200]})
    return out


def participant_row(subject, trials):
    """Mean over the participant's valid static trials (unweighted mean of trial means), both legs."""
    ok = [t for t in trials if t.get('status') == 'ok' and 'route' in t]
    row = {'subject': subject, 'n_static_trials_ok': len(ok), 'n_static_trials': len(trials),
           'routes': ';'.join(sorted({t['route'] for t in ok}))}
    for q in QUANT:
        row[f'lh_{q}'] = nanmean_of([nanmean_of([t[f'lh_right_{q}'], t[f'lh_left_{q}']]) for t in ok])
    for key in ('hip', 'knee', 'ankle', 'knee_raw'):
        row[f'ik_{key}'] = nanmean_of([nanmean_of([t.get(f'ik_right_{key}'), t.get(f'ik_left_{key}')]) for t in ok])
    row['ik_units_assumed'] = any(t.get('ik_right_units_assumed') or t.get('ik_left_units_assumed') for t in ok)
    row['ik_offset_max_abs_mean_deg'] = max([t['ik_offset_max_abs_mean_deg'] for t in ok if 'ik_offset_max_abs_mean_deg' in t],
                                            default=float('nan'))
    row['knee_sd_in_trial'] = nanmean_of([nanmean_of([t['knee_sd_right'], t['knee_sd_left']]) for t in ok])
    for q in QUANT:  # authors' IK vs LocoHub for the three joints
        if q in ('hip', 'knee', 'ankle'):
            row[f'lh_minus_ik_{q}'] = row[f'lh_{q}'] - row[f'ik_{q}']
    return row


# ------------------------------------------------------------------------------------------------ walking means
def stream_window_means(ds, batch_rows=4096):
    """{subject: {quantity: mean degrees}} and {subject: stride count} for one dataset's level walking, 20-35 percent phase."""
    import pyarrow.parquet as pq
    from contributor_tools.build_review_sheet_cross_dataset import TASKS
    match = TASKS['level']['match']
    pf = pq.ParquetFile(RECON / FOLDERS[ds] / 'filtered_phase.parquet')
    names = set(pf.schema_arrow.names)
    have = [q for q in QUANT if PARQUET_COLUMN[q] in names]
    read = ['subject', 'observation_id', 'task', 'task_info', 'observation_type', 'phase_ipsi'] + [PARQUET_COLUMN[q] for q in have]
    wm, group, strides = WindowMeans(), {}, {}
    for b in pf.iter_batches(batch_rows, columns=read, use_threads=False):
        ids = b.column('observation_id').to_numpy(zero_copy_only=False)
        uniq, first, inv = np.unique(ids, return_index=True, return_inverse=True)
        keep_u = np.zeros(len(uniq), bool)
        for k, (u, f) in enumerate(zip(uniq, first)):
            if u not in group:
                ok = b.column('observation_type')[int(f)].as_py() == 'individual_cycle'
                if ok:
                    info = json.loads(b.column('task_info')[int(f)].as_py() or '{}')
                    ok = bool(match(ds, b.column('task')[int(f)].as_py(), info))
                group[u] = ok
                if ok:
                    s = b.column('subject')[int(f)].as_py()
                    strides[s] = strides.get(s, 0) + 1
            keep_u[k] = group[u]
        keep = keep_u[inv]
        if not keep.any():
            continue
        subj = b.column('subject').to_numpy(zero_copy_only=False)[keep]
        phase = b.column('phase_ipsi').to_numpy(zero_copy_only=False)[keep].astype(float)
        vals = {q: b.column(PARQUET_COLUMN[q]).to_numpy(zero_copy_only=False)[keep].astype(float) * D for q in have}
        wm.add(subj, phase, vals)
    return wm.means(), strides


def compute(args):
    out = Path(args.out_root)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f'{out} is not empty; outputs go to a new root')
    out.mkdir(parents=True, exist_ok=True)
    static_root = Path(args.static_root)
    subjects = sorted(p.name for p in static_root.iterdir() if p.is_dir() and AB.fullmatch(p.name))
    if args.subject:
        subjects = [s for s in subjects if s in args.subject]
    trials, rows = [], []
    for s in subjects:
        t = analyse_subject(static_root, s)
        trials += t
        rows.append(participant_row(s, t))
    walking = {}
    for ds in FOLDERS:
        means, strides = stream_window_means(ds)
        walking[ds] = {'means': means, 'strides': strides}
    gt21 = {subject_key(s): m for s, m in walking['GT21']['means'].items() if subject_key(s)}
    ref = {ds: {q: nanmean_of([m.get(q) for m in walking[ds]['means'].values()]) for q in QUANT} for ds in REFS}
    ref['mean_of_both'] = {q: nanmean_of([ref[d][q] for d in REFS]) for q in QUANT}
    for row in rows:
        mid = gt21.get(row['subject'], {})
        for q in QUANT:
            row[f'mid_{q}'] = mid.get(q, float('nan'))
        row['mid_strides'] = next((n for s, n in walking['GT21']['strides'].items() if subject_key(s) == row['subject']), 0)
    comparison = {'window_percent': list(WINDOW), 'reference_means_deg': ref,
                  'reference_people': {d: len(walking[d]['means']) for d in REFS},
                  'gt21_people_walking': len(gt21), 'gt21_people_static': len(rows),
                  'gt21_people_in_both': sum(1 for r in rows if np.isfinite(r['mid_knee']) and np.isfinite(r['lh_knee'])),
                  'by_reference': {}, 'rule_notes': {'ik_offset_tolerance_deg': IK_OFFSET_TOLERANCE_DEG,
                                                     'steady_sd_deg': STEADY_SD_DEG}}
    for rname, rvals in ref.items():
        comparison['by_reference'][rname] = {
            q: compare([r[f'lh_{q}'] for r in rows], [r[f'mid_{q}'] for r in rows], rvals[q]) for q in QUANT}
    # the same comparison with the authors' IK standing angles (hip, knee, ankle only)
    comparison['by_reference_ik_standing'] = {
        rname: {q: compare([r[f'ik_{q}'] for r in rows], [r[f'mid_{q}'] for r in rows], rvals[q]) for q in ('hip', 'knee', 'ankle')}
        for rname, rvals in ref.items()}
    with open(out / 'static_trials.csv', 'x', newline='') as f:
        keys = sorted({k for t in trials for k in t}, key=lambda k: (k not in ('subject', 'session', 'recording', 'status', 'reason'), k))
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(trials)
    with open(out / 'per_participant.csv', 'x', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ['subject'])
        w.writeheader()
        w.writerows(rows)
    with open(out / 'comparison.json', 'x') as f:
        json.dump(comparison, f, indent=2, allow_nan=True)
        f.write('\n')
    import resource
    summary = {'status': 'run_done_unreviewed', 'scientific_approval': False, 'participants': len(rows),
               'trials': len(trials), 'excluded_trials': [f"{t['subject']}/{t.get('session')}/{t.get('recording')}: {t['reason']}"
                                                         for t in trials if t.get('status') != 'ok'],
               'peak_rss_mib': round(max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                                         resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) / 1024, 1)}
    with open(out / 'run_summary.json', 'x') as f:
        json.dump(summary, f, indent=2)
        f.write('\n')
    return 0


# ------------------------------------------------------------------------------------------------ the review sheet
def read_rows(path):
    with open(path, newline='') as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k, v in r.items():
            if k not in ('subject', 'routes'):
                try:
                    r[k] = float(v)
                except ValueError:
                    r[k] = {'True': True, 'False': False}.get(v, v)
    return rows


def sheet(args):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from contributor_tools.common.review_sheet import page
    src = Path(args.out_root)
    rows = read_rows(src / 'per_participant.csv')
    comp = json.loads((src / 'comparison.json').read_text())
    cmp_ = comp['by_reference']['mean_of_both']
    out = Path(args.sheet_dir)
    out.mkdir(parents=True, exist_ok=True)
    INK, ORANGE, BLUE = '#20252B', '#eb6834', '#2a78d6'
    plt.rcParams.update({'font.size': 10, 'axes.titlesize': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                         'text.color': INK, 'axes.labelcolor': INK, 'axes.edgecolor': INK, 'legend.frameon': False})

    def scatter(q, label, name):
        pts = [(r[f'lh_{q}'], r[f'mid_{q}'] - comp['reference_means_deg']['mean_of_both'][q]) for r in rows
               if np.isfinite(r[f'lh_{q}']) and np.isfinite(r[f'mid_{q}'])]
        fig, ax = plt.subplots(figsize=(4.5, 3.8))
        if pts:
            x, y = np.array(pts).T
            ax.scatter(x, y, color=ORANGE, s=22, zorder=3)
            lo, hi = min(x.min(), y.min(), 0) - 1, max(x.max(), y.max(), 0) + 1
            ax.plot([lo, hi], [lo, hi], ls='--', color='#7a8591', lw=1)
            ax.set_xlim(lo, hi)
            ax.set_ylim(lo, hi)
            c = cmp_[q]
            ax.text(0.03, 0.97, f'r = {c["pearson_r"]:.2f}, {c["n"]} people\nslope {c["slope_gap_on_standing"]:.2f}', transform=ax.transAxes,
                    va='top', fontsize=10)
        ax.axhline(0, color='#aab2ba', lw=0.5)
        ax.axvline(0, color='#aab2ba', lw=0.5)
        ax.set_xlabel(f'{label} standing (degrees)')
        ax.set_ylabel(f'{label} walking gap (degrees)')
        fig.text(0.97, 0.01, 'dashed: standing offset explains the whole gap', ha='right', fontsize=10, color='#5b6672')
        fig.subplots_adjust(left=0.16, right=0.97, top=0.97, bottom=0.2)
        fig.savefig(out / name, dpi=160)
        plt.close(fig)

    scatter('knee', 'Knee flexion', 'knee_scatter.png')
    scatter('thigh', 'Thigh', 'thigh_scatter.png')
    scatter('shank', 'Shank', 'shank_scatter.png')
    fig, ax = plt.subplots(figsize=(4.5, 3.8))
    qs = ('knee', 'thigh', 'shank')
    xs = np.arange(len(qs))
    ax.bar(xs - 0.2, [cmp_[q]['mean_gap'] for q in qs], 0.38, yerr=[cmp_[q]['sd_gap'] for q in qs], color=ORANGE, capsize=3,
           label='as converted')
    ax.bar(xs + 0.2, [cmp_[q]['mean_corrected_gap'] for q in qs], 0.38, yerr=[cmp_[q]['sd_corrected_gap'] for q in qs], color=BLUE,
           capsize=3, label='standing as zero')
    ax.axhline(0, color=INK, lw=0.6)
    ax.set_xticks(xs)
    ax.set_xticklabels(['Knee', 'Thigh', 'Shank'])
    ax.set_ylabel('GT21 minus GT23/UM21 (degrees)')
    ax.legend(loc='best', fontsize=10)
    fig.subplots_adjust(left=0.17, right=0.97, top=0.97, bottom=0.12)
    fig.savefig(out / 'gap_before_after.png', dpi=160)
    plt.close(fig)

    n_static = len(rows)
    ok = [r for r in rows if r['n_static_trials_ok'] > 0]
    routes = {r['routes'] for r in ok}
    knee = cmp_['knee']
    chips = [
        ('pass' if n_static == 22 else 'unchecked', f'static trials found for {n_static} of 22 people'),
        ('pass' if ok and routes == {'pass_unchanged'} else ('unchecked' if ok else 'fail'),
         f'LocoHub geometry ran on {len(ok)} of {n_static}; route ' + ', '.join(sorted(routes))),
        ('pass' if ok and all(r['knee_sd_in_trial'] <= STEADY_SD_DEG for r in ok) else 'unchecked',
         f'standing steady: knee SD at most {STEADY_SD_DEG:g} degrees in the trial'),
        ('pass' if ok and all(r['ik_offset_max_abs_mean_deg'] <= IK_OFFSET_TOLERANCE_DEG for r in ok) else 'unchecked',
         "authors' offset angles average zero over standing"),
        ('unchecked', "authors' knee sign taken from the converter rule; unit " + ('assumed degrees' if any(r['ik_units_assumed'] for r in ok) else 'as stored')),
        ('unchecked', 'GT23 and UM21 have no standing data here'),
        ('pass' if comp['gt21_people_in_both'] == n_static else 'unchecked',
         f'{comp["gt21_people_in_both"]} people have both standing and walking'),
    ]
    headline = (f'Standing knee averages {knee["mean_standing"]:.1f} degrees; the walking knee gap is {knee["mean_gap"]:.1f} degrees; '
                f'standing as zero leaves {knee["mean_corrected_gap"]:.1f}.')
    details = [
        'Walking: level walking at 1.2 m/s (sheet A rule), 20-35 percent of stride, mean over each person\'s strides (people with more strides weigh more); both legs pooled. Reference = mean of the GT23 and UM21 person means.',
        'Standing: LocoHub segment and joint angles from the static markers by the merged pass (route per person below); mean over the trial and both legs, then over static trials.',
        f'Own rules (not reference ranges): standing steady = knee SD at most {STEADY_SD_DEG:g} degrees; authors\' offset angles average zero = within {IK_OFFSET_TOLERANCE_DEG:g} degrees.',
        'Slope is gap on standing offset across people; 1.0 means one degree of gap per degree of standing offset. Spearman r and the comparison with each reference alone are in comparison.json.',
        'Standing angles from the authors\' IK (hip, knee, ankle) are in per_participant.csv (ik_ columns) with the difference to LocoHub (lh_minus_ik_ columns).',
    ] + [f'{r["subject"]}: standing knee {r["lh_knee"]:.1f}, thigh {r["lh_thigh"]:.1f}, shank {r["lh_shank"]:.1f}; walking knee {r["mid_knee"]:.1f}; route {r["routes"]}; '
         f'authors\' IK knee {r["ik_knee"]:.1f}' for r in rows] + [f'Source: {src}. Builder: contributor_tools/analyze_gt21_static_pose.py']
    page(out / 'index.html', title='GT21 standing pose and the knee gap', ask='Does the standing pose explain the GT21 knee gap?',
         headline=headline, chips=chips,
         figures=[(['knee_scatter.png'], 'Do people who stand more flexed also walk more flexed?',
                   'Each dot is one person.', 'Scatter of standing knee against the walking knee gap, one dot per GT21 person'),
                  (['thigh_scatter.png', 'shank_scatter.png'], 'Do thigh and shank tell the same story?', 'Same layout.',
                   'Scatter of standing thigh and shank angle against their walking gaps'),
                  (['gap_before_after.png'], 'What is left if standing is zero?', 'Bars: mean; whiskers: spread across people.',
                   'Mean walking gap before and after subtracting each person\'s standing angle, for knee, thigh and shank')],
         not_shown=['Standing poses of GT23 and UM21', 'Tasks other than level walking', 'Why a standing offset would exist'],
         reply='ok  |  what looks wrong', details=details)
    if args.render:
        from contributor_tools.build_review_sheet_cross_dataset import render
        render([out / 'index.html'])
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('compute')
    c.add_argument('--out-root', required=True)
    c.add_argument('--static-root', default=str(STATIC_ROOT))
    c.add_argument('--subject', action='append', help='limit to these participants (pilot)')
    s = sub.add_parser('sheet')
    s.add_argument('--out-root', required=True)
    s.add_argument('--sheet-dir', default=str(SHEET_DIR))
    s.add_argument('--render', action='store_true')
    args = p.parse_args(argv)
    return {'compute': compute, 'sheet': sheet}[args.cmd](args)


if __name__ == '__main__':
    raise SystemExit(main())
