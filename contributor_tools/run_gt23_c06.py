"""GT23-C06 conventions runner: segment and joint angles, speeds, foot-frame pressure point, force frame.

Subcommands
  run      One participant (or named recordings). Reads one recording at a time: step-1 Parquet companions (ground
           force, published joint angles/speeds/moments; hash-bound to the X01 ledger), the marker and Transforms_Euler
           files from the publisher's folder (read-only, hashes checked against the ledger) and the S01 spans. Writes a
           NEW output root: <recording>.parquet (one row per 200 Hz sample), ledger.jsonl (one receipt per recording),
           run_summary.json. Never overwrites.
  spec     Writes the guarded-launcher job spec.
  summary  Adds up participant roots into per-subject, per-leg offsets against the publisher, the pelvis comparison, the
           pressure-point and ankle-moment checks, held columns and speed sign agreement.

Method and conventions: contributor_tools/gt23_conventions.py (docs/reference/index.md, decided 2026-11-23). Python only.
No scientific approval is claimed.
"""
import argparse
import json
import os
from pathlib import Path
import resource
import sys

os.environ.setdefault('ARROW_DEFAULT_MEMORY_POOL', 'system')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
from contributor_tools import gt23_conventions as cv  # noqa: E402
from contributor_tools import gt23_conventions_check as chk  # noqa: E402
from contributor_tools import gt23_segmentation as seg  # noqa: E402
from contributor_tools import gt23_source_reader as rd  # noqa: E402

SOURCE = Path('/mnt/s/locomotion_data/Gtech_2023')
SUBJECTS = ('AB01', 'AB02', 'AB03', 'AB05', 'AB06', 'AB07', 'AB08', 'AB09', 'AB10', 'AB11', 'AB12', 'AB13')
X01_ROOTS = {s: f'converted_datasets/reconversion_v2/gt23_x01_batch_{s}' + ('_r2' if s == 'AB01' else '') for s in SUBJECTS}
S01_ROOTS = {s: f'converted_datasets/reconversion_v2/gt23_s01_batch_{s}' for s in SUBJECTS}
MODEL_FILE = {s: f'{s}-Scaled1.osim' for s in SUBJECTS}
MODEL_FILE['AB01'] = 'AB01-Scaled1_original.osim'
CODE = ('contributor_tools/gt23_conventions.py', 'contributor_tools/gt23_conventions_check.py',
        'contributor_tools/run_gt23_c06.py', 'contributor_tools/gt23_segmentation.py',
        'contributor_tools/gt23_source_reader.py', 'contributor_tools/guarded_launcher.py')
FORWARD_TASKS = ('curb_down', 'curb_up', 'dynamic_walk', 'incline_walk', 'normal_walk', 'obstacle_walk', 'stairs',
                 'start_stop', 'step_ups', 'tire_run', 'weighted_walk')   # D-GT23-C01-1 = C
MARKERS_USED = ('LASI', 'RASI', 'LPSI', 'RPSI', 'LKNE', 'LMKNE', 'RKNE', 'RMKNE', 'LANK', 'LMANK', 'RANK', 'RMANK',
                'LCAL', 'RCAL', 'LMT1', 'LMT5', 'RMT1', 'RMT5')
BODIES = ('pelvis', 'femur_r', 'femur_l', 'tibia_r', 'tibia_l', 'talus_r', 'talus_l', 'calcn_r', 'calcn_l')
WORD = {'L': 'left', 'R': 'right'}
CHUNK = 20000
G = 9.80665
LOAD_BW = 0.2           # fixed in advance: samples with vertical force at least 0.2 body weight for the moment check
SPEED_SIGN_MIN_DEG_S = 10.0   # fixed in advance: sign agreement counted where the published speed exceeds this
MIN_STANCE_S, MAX_STANCE_S = 0.3, 3.0
RAISED_GAP_M = 0.17   # median heel-marker height above the recorded plate surface while loaded; the diagnostic over curb, cutting,
#   step-up, tire-run and stair recordings shows 0.05-0.146 m everywhere except curb_up (0.200-0.229 m): the foot stands on a curb
#   of undocumented height, so the force line does not meet the sole at the recorded plate height. 0.17 sits in that gap.


class RunError(RuntimeError):
    pass


def peak_rss_mib():
    return round(max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) / 1024, 1)


def _atomic_json(path, obj):
    temp = Path(path).with_suffix('.tmp')
    temp.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')
    temp.replace(path)


# ------------------------------------------------------------------------------------------------ readers
def read_companion(path, columns):
    """Columns of a step-1 Parquet companion, one 4096-row batch at a time (no threads, unbuffered)."""
    pf = pq.ParquetFile(str(path), buffer_size=0)
    parts = [b.to_pandas() for b in pf.iter_batches(batch_size=4096, columns=list(columns), use_threads=False)]
    df = pd.concat(parts, ignore_index=True)
    return {c: df[c].to_numpy(np.float64) for c in columns}


def read_markers(path, names):
    """Markers in metres (n, 3) by name; a marker absent from the file is returned as all NaN and listed in ``absent``."""
    first, markers, declared = rd.read_trc_header(path)
    absent = [m for m in names if m not in markers]
    present = [m for m in names if m in markers]
    use, idx = [1], {}
    for m in present:
        i = markers.index(m)
        idx[m] = 2 + 3 * i
        use += [2 + 3 * i, 3 + 3 * i, 4 + 3 * i]
    order = sorted(set(use))
    pos = {c: k for k, c in enumerate(order)}
    parts = []
    for chunk in pd.read_csv(path, sep='\t', skiprows=first, header=None, usecols=order, dtype=np.float64, chunksize=CHUNK):
        arr = chunk.to_numpy(np.float64)
        parts.append(np.stack([arr[:, [pos[idx[m]], pos[idx[m] + 1], pos[idx[m] + 2]]] for m in present], axis=1) / 1000.0)
    block = np.concatenate(parts, axis=0)
    n = len(block)
    out = {m: block[:, k, :].copy() for k, m in enumerate(present)}
    for m in absent:
        out[m] = np.full((n, 3), np.nan)
    return out, absent, n


def read_euler(path, bodies):
    """Euler angles (n, 3) in file order (radians) for each body; the columns are <body>_Z, <body>_X, <body>_Y in order."""
    cols = {b: [f'{b}_Z', f'{b}_X', f'{b}_Y'] for b in bodies}
    use = [c for b in bodies for c in cols[b]]
    parts = [c for c in pd.read_csv(path, usecols=use, dtype=np.float64, float_precision='round_trip', chunksize=CHUNK)]
    df = pd.concat(parts, ignore_index=True)
    return {b: df[cols[b]].to_numpy(np.float64) for b in bodies}


# ------------------------------------------------------------------------------------------------ small helpers
def _finite_stats(new, pub):
    ok = np.isfinite(new) & np.isfinite(pub)
    if ok.sum() < 3:
        return {'n': int(ok.sum())}
    a, b = new[ok], pub[ok]
    d = a - b
    r = float(np.corrcoef(a, b)[0, 1]) if np.std(a) > 0 and np.std(b) > 0 else None
    return {'n': int(ok.sum()), 'median_offset_deg': float(np.degrees(np.median(d))), 'r': r,
            'resid_sd_deg': float(np.degrees(np.std(d - np.median(d))))}


def stance_runs(force):
    """Index runs [a, b] of own-plate vertical force at or above 20 N, lasting 0.3 to 3 s (fixed rules, no tuning)."""
    f = np.nan_to_num(np.asarray(force, float), nan=0.0) >= cv.STANCE_N
    edges = np.flatnonzero(np.diff(np.concatenate(([0], f.astype(int), [0]))))
    runs = []
    for a, b in zip(edges[::2], edges[1::2]):
        if MIN_STANCE_S <= (b - a) / cv.RATE_HZ <= MAX_STANCE_S:
            runs.append((int(a), int(b) - 1))
    return runs


def _median(x):
    x = [v for v in x if v is not None and np.isfinite(v)]
    return float(np.median(x)) if x else None


def column_reasons(cols, absent, forward_task, n_spans, plate_has_data, raised):
    """For every all-missing output column, the reason (nothing is filled)."""
    asis = {'LASI', 'RASI'} & set(absent)
    pelvis = {'LASI', 'RASI', 'LPSI', 'RPSI'} & set(absent)
    reasons = {}
    for name, v in cols.items():
        if name == 'time_s' or np.isfinite(v).any():
            continue
        side = 'L' if '_left' in name else 'R' if '_right' in name else None
        if name.startswith(('grf_anterior', 'grf_lateral', 'heading_lab')):
            if not forward_task:
                reasons[name] = 'task has no single forward direction (D-GT23-C01-1 = C); lab-axis force columns hold the force'
            elif asis:
                reasons[name] = 'needs missing marker ' + ','.join(sorted(asis))
            elif side and not plate_has_data[side]:
                reasons[name] = 'source plate force is missing for this leg in this recording'
            elif not n_spans:
                reasons[name] = 'plate never loaded above 20 N (no contact to hold a heading for)'
            else:
                reasons[name] = 'plate never loaded above 20 N within the spans'
            continue
        if name.startswith(('grf_lab', 'cop_lab')):
            reasons[name] = ('source plate force is missing for this leg in this recording' if not plate_has_data[side]
                             else 'plate never loaded above 20 N')
            continue
        foot = {f'{side}CAL', f'{side}MT1', f'{side}MT5'} & set(absent) if side else set()
        knee = {f'{side}KNE', f'{side}MKNE'} & set(absent) if side else set()
        if name.startswith('cop_'):
            need = foot | knee | ({f'{side}ANK', f'{side}MANK'} & set(absent))
            if raised.get(side) is not None and raised[side] > RAISED_GAP_M:
                reasons[name] = (f'held: foot stands about {raised[side]:.2f} m above the recorded plate surface (raised surface of '
                                 'undocumented height), so the pressure point on the sole is not defensible')
                continue
            plate_note = '' if plate_has_data[side] else 'source plate force is missing for this leg in this recording'
            reasons[name] = ('needs missing marker ' + ','.join(sorted(need))) if need else (plate_note or 'plate never loaded above 20 N')
            continue
        if name.startswith('pelvis'):
            need = pelvis
        elif name.startswith('hip'):
            need = pelvis | knee      # hip = thigh (leg plane, needs the knee axis) - pelvis
        elif name.startswith(('thigh', 'shank', 'knee')):
            need = knee
        else:  # foot and ankle angle and speed
            need = knee | foot
        reasons[name] = ('needs missing marker ' + ','.join(sorted(need))) if need else 'no finite samples'
    return reasons


# ------------------------------------------------------------------------------------------------ one recording
def model_checks(model_text, S, mk, rot, ankle_mid, fwd, fwd_pelvis, cols):
    s, w = S.lower(), WORD[S]
    geo = cv.model_geometry(model_text, s)
    out = {}
    # knee flexion axis: marker axis (lateral/medial knee markers) against the model femur z axis, horizontal parts, signed angle
    # about the vertical (deg); both point to the person's right
    ax_m = cv.plane_forward(cv.knee_axis_to_right(mk[f'{S}KNE'], mk[f'{S}MKNE'], S))
    ax_f = cv.plane_forward(rot[f'femur_{s}'][:, :, 2])
    cosv, sinv = np.sum(ax_m * ax_f, axis=1), np.sum(np.cross(ax_f, ax_m) * cv.UP, axis=1)
    dev = np.degrees(np.arctan2(sinv, cosv))
    out['knee_axis_marker_vs_model_deg'] = ({'n': int(np.isfinite(dev).sum()), 'median': float(np.nanmedian(dev)),
                                              'p95_abs': float(np.nanpercentile(np.abs(dev), 95)), 'max_abs': float(np.nanmax(np.abs(dev)))}
                                             if np.isfinite(dev).any() else {'n': 0})
    via_tib = cv.model_ankle_centre_via_tibia(mk[f'{S}ANK'], mk[f'{S}MANK'], geo, rot[f'tibia_{s}'])
    via_cal = cv.model_talus_origin_via_calcn(mk[f'{S}CAL'], geo, rot[f'calcn_{s}'], rot[f'talus_{s}'])
    d_tib = np.einsum('nji,nj->ni', rot[f'tibia_{s}'], via_tib - ankle_mid)   # model minus marker midpoint, tibia frame
    d_cal = np.einsum('nji,nj->ni', rot[f'tibia_{s}'], via_cal - ankle_mid)

    def med(d):
        return [None if not np.isfinite(d[:, k]).any() else float(np.nanmedian(d[:, k]) * 1000) for k in range(3)]
    apart = np.linalg.norm(via_tib - via_cal, axis=1)
    out['ankle_centre_model_minus_marker_midpoint_mm_tibia_frame'] = {
        'via_tibia_markers': med(d_tib), 'via_calcaneus_marker': med(d_cal),
        'two_model_routes_apart_mm_median': float(np.nanmedian(apart) * 1000) if np.isfinite(apart).any() else None}
    knee_mid = (mk[f'{S}KNE'] + mk[f'{S}MKNE']) / 2
    m_shank = cv.angle_from_down(cv.sag(ankle_mid - knee_mid, fwd))
    m_foot_model = cv.angle_from_forward(cv.sag(rot[f'calcn_{s}'][:, :, 0], fwd))
    out['markers_vs_model_axes'] = {
        'shank': _finite_stats(m_shank, cols[f'shank_sagittal_angle_{w}_rad']),
        'foot_marker_vs_model_calcaneus_x': _finite_stats(cols[f'foot_sagittal_angle_{w}_rad'], m_foot_model)}
    if all(k in geo['markers'] for k in ('LASI', 'RASI', 'LPSI', 'RPSI')):
        hip = cv.model_hip_centre({k: mk[k] for k in ('LASI', 'RASI', 'LPSI', 'RPSI')}, geo, rot['pelvis'])
        m_thigh = cv.angle_from_down(cv.sag(knee_mid - hip, fwd))
        out['markers_vs_model_axes']['thigh'] = _finite_stats(m_thigh, cols[f'thigh_sagittal_angle_{w}_rad'])
    else:
        out['markers_vs_model_axes']['thigh_unavailable'] = 'model has no pelvis markers'
    return out


def process_recording(subject, rec, x01, spans_raw, mass_kg, model_text, source, x01_root):
    task = seg.task_of(rec)
    forward_task = task in FORWARD_TASKS
    folder = Path(source) / 'RawData' / subject
    trc = folder / 'MarkerData' / f'{rec}.trc'
    eul = folder / 'Transforms_Euler' / f'{rec}.csv'
    if rd.sha256_file(trc) != x01['markers']['sha256']:
        raise RunError(f'{rec}: marker file hash differs from the X01 ledger')
    if rd.sha256_file(eul) != x01['euler']['sha256']:
        raise RunError(f'{rec}: Transforms_Euler hash differs from the X01 ledger')
    comp = ROOT / x01_root / rec
    for ch in ('GroundFrame_GRFs', 'Joint_Angle', 'Joint_Velocities', 'Joint_Moments'):
        if rd.sha256_file(comp / f'{ch}.parquet') != x01['channels'][ch]['parquet_sha256']:
            raise RunError(f'{rec}: {ch} companion hash differs from the X01 ledger')
    mk, absent, n = read_markers(trc, MARKERS_USED)
    eu = read_euler(eul, BODIES)
    grf_cols = ['time'] + [f'{s}{c}' for s in 'LR' for c in ('ForceX', 'ForceY_Vertical', 'ForceZ', 'COPX', 'COPY_Vertical', 'COPZ')]
    grf = read_companion(comp / 'GroundFrame_GRFs.parquet', grf_cols)
    if not (len(grf['time']) == n == len(eu['pelvis'])):
        raise RunError(f'{rec}: row counts differ (markers {n}, force {len(grf["time"])}, Euler {len(eu["pelvis"])})')
    dt_dev = float(np.max(np.abs(np.diff(grf['time']) - 1 / cv.RATE_HZ))) if n > 1 else 0.0
    # --- side-view planes (D-REF-4): the pelvis in its own plane; each leg in the plane perpendicular to its knee axis
    fwd = cv.heading(mk['LASI'], mk['RASI'])      # ASIS-line heading, kept only as the walking direction of the force
    asis_mid = (mk['LASI'] + mk['RASI']) / 2
    psis_mid = (mk['LPSI'] + mk['RPSI']) / 2
    rot = {b: cv.euler_yzx(*[eu[b][:, k] for k in range(3)]) for b in BODIES}
    cols = {'time_s': grf['time']}
    pelvis = cv.pelvis_angle(asis_mid, psis_mid)
    fwd_pelvis = cv.pelvis_forward(asis_mid, psis_mid)
    fwd_leg, seg_foot = {}, {}
    for S in 'LR':
        s = S.lower()
        fwd_leg[S] = cv.plane_forward(cv.knee_axis_to_right(mk[f'{S}KNE'], mk[f'{S}MKNE'], S))
        heel, toe = mk[f'{S}CAL'], (mk[f'{S}MT1'] + mk[f'{S}MT5']) / 2
        a = cv.leg_segment_angles(fwd_leg[S], -rot[f'femur_{s}'][:, :, 1], -rot[f'tibia_{s}'][:, :, 1], heel, toe)
        a['pelvis'] = pelvis
        j = cv.joint_angles(a)
        seg_foot[S] = a['foot']
        for k in ('thigh', 'shank', 'foot'):
            cols[f'{k}_sagittal_angle_{WORD[S]}_rad'] = a[k]
        cols[f'hip_flexion_angle_{WORD[S]}_rad'] = j['hip']
        cols[f'knee_flexion_angle_{WORD[S]}_rad'] = j['knee']
        cols[f'ankle_dorsiflexion_angle_{WORD[S]}_rad'] = j['ankle']
        for k, nm in (('hip', 'hip_flexion'), ('knee', 'knee_flexion'), ('ankle', 'ankle_dorsiflexion')):
            cols[f'{nm}_velocity_{WORD[S]}_rad_s'] = cv.central_derivative(j[k])
    cols['pelvis_sagittal_angle_rad'] = pelvis
    # --- composition from the written columns
    comp_err = 0.0
    for S in 'LR':
        w = WORD[S]
        comp_err = max(comp_err, cv.composition_error(cols['pelvis_sagittal_angle_rad'], cols[f'thigh_sagittal_angle_{w}_rad'],
                                                      cols[f'shank_sagittal_angle_{w}_rad'], cols[f'foot_sagittal_angle_{w}_rad'],
                                                      cols[f'hip_flexion_angle_{w}_rad'], cols[f'knee_flexion_angle_{w}_rad'],
                                                      cols[f'ankle_dorsiflexion_angle_{w}_rad']))
    # --- force and pressure point
    force_lab, cop_lab, loaded, ankle_c, heel_p, toe_p = {}, {}, {}, {}, {}, {}
    raised = {}
    for S in 'LR':
        w = WORD[S]
        F = np.stack([grf[f'{S}ForceX'], grf[f'{S}ForceY_Vertical'], grf[f'{S}ForceZ']], axis=1)
        vert = grf[f'{S}ForceY_Vertical']
        load = np.isfinite(vert) & (vert >= cv.STANCE_N)
        loaded[S] = load
        cop = cv.plate_point(grf[f'{S}COPX'], grf[f'{S}COPY_Vertical'], grf[f'{S}COPZ'], vert)   # source plate height, never assumed 0
        force_lab[S], cop_lab[S] = F, cop
        for k, ax in zip('xyz', range(3)):
            cols[f'grf_lab_{k}_{w}_N'] = F[:, ax]
        cols[f'cop_lab_x_{w}_m'] = cop[:, 0]
        cols[f'cop_lab_y_{w}_m'] = cop[:, 1]
        cols[f'cop_lab_z_{w}_m'] = cop[:, 2]
        ankle = (mk[f'{S}ANK'] + mk[f'{S}MANK']) / 2
        heel, toe = mk[f'{S}CAL'], (mk[f'{S}MT1'] + mk[f'{S}MT5']) / 2
        ankle_c[S], heel_p[S], toe_p[S] = ankle, heel, toe
        ff = cv.foot_frame_point(cop, ankle, fwd_leg[S], seg_foot[S], S)
        gap = cv.heel_above_plate(heel[:, 1], cop[:, 1])
        raised[S] = gap
        if gap is not None and gap > RAISED_GAP_M:   # held: the load surface above the plate has no documented height
            ff = {k: np.full(n, np.nan) for k in ff}
        for k in ('anterior', 'vertical', 'lateral'):
            cols[f'cop_{k}_{w}_m'] = ff[k]
    # forward and sideways force: forward-walking tasks only; the heading is held fixed within each of that leg's own
    # strides (or within each window; the whole recording for a task without cycles), from the S01 spans [start, end)
    span_report = []
    contact_fill = {}
    n_spans = 0
    for S in 'LR':
        heading_used = np.full((n, 3), np.nan)
        if forward_task:
            if spans_raw:
                spans = [(a, b - 1) for a, b, side in spans_raw if side in (S, 'both') and b - 1 > a]
            else:
                spans = [(0, n - 1)] if seg.task_class(task) == 'continuous' else []
            n_spans += len(spans)
            heading_used, rep_ = cv.heading_by_span(fwd, spans)
            span_report += rep_
            heading_used, n_runs, n_samples, n_left = cv.fill_heading_by_contact(heading_used, fwd, loaded[S])
            contact_fill[S] = {'contacts_filled': n_runs, 'loaded_samples_filled': n_samples, 'loaded_samples_without_heading': n_left,
                               'loaded_samples': int(loaded[S].sum())}
        a_, l_ = cv.force_forward_sideways(force_lab[S], heading_used, S)
        cols[f'grf_anterior_{WORD[S]}_N'] = a_
        cols[f'grf_lateral_{WORD[S]}_N'] = l_
        cols[f'heading_lab_x_{WORD[S]}'] = heading_used[:, 0]
        cols[f'heading_lab_z_{WORD[S]}'] = heading_used[:, 2]
    spans = list(range(n_spans))
    reasons = column_reasons(cols, absent, forward_task, n_spans, {S: bool(np.isfinite(grf[f'{S}ForceY_Vertical']).any()) for S in 'LR'}, raised)
    # --- checks against independent known values
    second, used = chk.compare(cols, mk, {k: eu[k] for k in ('femur_l', 'femur_r', 'tibia_l', 'tibia_r')}, cop_lab)
    report = {'subject': subject, 'recording': rec, 'task': task, 'forward_task': forward_task, 'rows': n,
              'absent_markers': absent, 'clock_max_dev_s': dt_dev, 'composition_max_abs_err_rad': comp_err,
              'second_implementation': {'max_abs_diff': second, 'samples': used},
              'held_columns': reasons, 'heel_above_plate_median_m': raised, 'span_count': n_spans, 'heading_from_contact_when_no_span': contact_fill,
              'span_heading_dev_deg': {'median_of_span_max': _median([r['max_dev_deg'] for r in span_report]),
                                       'max': max([r['max_dev_deg'] for r in span_report if r['max_dev_deg'] is not None], default=None)}}
    pub_a = read_companion(comp / 'Joint_Angle.parquet', ['hip_flexion_r', 'knee_angle_r', 'ankle_angle_r', 'hip_flexion_l', 'knee_angle_l', 'ankle_angle_l'])
    pub_v = read_companion(comp / 'Joint_Velocities.parquet', ['hip_flexion_velocity_r', 'knee_velocity_r', 'ankle_velocity_r', 'hip_flexion_velocity_l', 'knee_velocity_l', 'ankle_velocity_l'])
    pub_m = read_companion(comp / 'Joint_Moments.parquet', ['ankle_angle_r_moment', 'ankle_angle_l_moment'])
    legs = {}
    for S in 'LR':
        s = S.lower()
        w = WORD[S]
        leg = {}
        for k, pa_name, sign in (('hip', f'hip_flexion_{s}', 1.0), ('knee', f'knee_angle_{s}', -1.0), ('ankle', f'ankle_angle_{s}', 1.0)):
            nm = {'hip': 'hip_flexion', 'knee': 'knee_flexion', 'ankle': 'ankle_dorsiflexion'}[k]
            leg[f'{k}_angle_vs_publisher'] = _finite_stats(cols[f'{nm}_angle_{w}_rad'], np.radians(sign * pub_a[pa_name]))
        for k, pv_name, sign in (('hip', f'hip_flexion_velocity_{s}', 1.0), ('knee', f'knee_velocity_{s}', -1.0), ('ankle', f'ankle_velocity_{s}', 1.0)):
            nm = {'hip': 'hip_flexion', 'knee': 'knee_flexion', 'ankle': 'ankle_dorsiflexion'}[k]
            new = np.degrees(cols[f'{nm}_velocity_{w}_rad_s'])
            pub = sign * pub_v[pv_name]
            ok = np.isfinite(new) & np.isfinite(pub)
            big = ok & (np.abs(pub) > SPEED_SIGN_MIN_DEG_S)
            item = {'n': int(ok.sum()), 'n_above_threshold': int(big.sum())}
            if ok.sum() > 3 and np.std(new[ok]) > 0 and np.std(pub[ok]) > 0:
                item['r'] = float(np.corrcoef(new[ok], pub[ok])[0, 1])
                item['rms_diff_deg_s'] = float(np.sqrt(np.mean((new[ok] - pub[ok]) ** 2)))
                item['rms_published_deg_s'] = float(np.sqrt(np.mean(pub[ok] ** 2)))
            if big.sum():
                item['sign_agreement'] = float(np.mean(np.sign(new[big]) == np.sign(pub[big])))
            leg[f'{k}_speed_vs_publisher'] = item
        # foot flat at mid-stance and pressure point shape over stance runs
        runs = stance_runs(grf[f'{S}ForceY_Vertical'])
        foot = cols[f'foot_sagittal_angle_{w}_rad']
        flat, first, last, vert, lat = [], [], [], [], []
        for a, b in runs:
            lo, hi = a + int(0.4 * (b - a)), a + int(0.6 * (b - a)) + 1
            seg_ = foot[lo:hi]
            if np.isfinite(seg_).any():
                flat.append(float(np.degrees(np.nanmedian(seg_))))
            ant = cols[f'cop_anterior_{w}_m'][a:b + 1]
            if np.isfinite(ant).any():
                good = np.flatnonzero(np.isfinite(ant))
                first.append(float(ant[good[0]]))
                last.append(float(ant[good[-1]]))
                vert.append(float(np.nanmedian(cols[f'cop_vertical_{w}_m'][a:b + 1])))
                lat.append(float(np.nanmedian(cols[f'cop_lateral_{w}_m'][a:b + 1])))
        e_f_, _, _ = cv.foot_axes(fwd_leg[S], seg_foot[S])
        heel_ant = np.sum((heel_p[S] - ankle_c[S]) * e_f_, axis=1) - cv.FOOT_ORIGIN_M
        toe_ant = np.sum((toe_p[S] - ankle_c[S]) * e_f_, axis=1) - cv.FOOT_ORIGIN_M
        ant = cols[f'cop_anterior_{w}_m']
        okc = np.isfinite(ant) & np.isfinite(heel_ant) & np.isfinite(toe_ant)
        leg['cop_outside_foot_share'] = {'n': int(okc.sum()), 'margin_m': 0.05, 'share': (float(np.mean((ant[okc] < heel_ant[okc] - 0.05) | (ant[okc] > toe_ant[okc] + 0.05))) if okc.any() else None)}
        leg['stance_runs'] = len(runs)
        leg['foot_angle_mid_stance_deg_median'] = _median(flat)
        leg['foot_angle_mid_stance_runs'] = len(flat)
        leg['cop_anterior_first_m_median'] = _median(first)
        leg['cop_anterior_last_m_median'] = _median(last)
        leg['cop_vertical_median_m'] = _median(vert)
        leg['cop_lateral_median_m'] = _median(lat)
        # hold-out ankle moment: quasi-static from the foot-frame pressure point against the published moment
        Fa, Fu = cv.foot_frame_force(force_lab[S], fwd_leg[S], seg_foot[S])
        m_calc = cv.ankle_moment_quasi_static(cols[f'cop_anterior_{w}_m'], cols[f'cop_vertical_{w}_m'], Fa, Fu)
        if mass_kg:
            calc = m_calc / mass_kg
            pubm = pub_m[f'ankle_angle_{s}_moment']
            ok = np.isfinite(calc) & np.isfinite(pubm) & (grf[f'{S}ForceY_Vertical'] >= LOAD_BW * mass_kg * G)
            item = {'n': int(ok.sum())}
            if ok.sum() > 10 and np.std(calc[ok]) > 0 and np.std(pubm[ok]) > 0:
                item['r'] = float(np.corrcoef(calc[ok], pubm[ok])[0, 1])
                slope, icpt = np.polyfit(calc[ok], pubm[ok], 1)
                item['slope_published_per_computed'] = float(slope)
                item['intercept_nm_per_kg'] = float(icpt)
                item['median_computed_peak_nm_per_kg'] = float(np.percentile(calc[ok], 5))
                item['median_published_peak_nm_per_kg'] = float(np.percentile(pubm[ok], 5))
            leg['ankle_moment_check'] = item
        # model-based cross-checks (authors' scaled model geometry re-implemented)
        if model_text is not None:
            try:
                leg.update(model_checks(model_text, S, mk, rot, ankle_c[S], fwd_leg[S], fwd_pelvis, cols))
            except KeyError as error:
                leg['model_checks_unavailable'] = f'model lacks {error}'
        legs[S] = leg
    report['legs'] = legs
    # pelvis: marker angle against the authors' model pelvis tilt (x axis of the model pelvis in the same plane)
    model_tilt = cv.angle_from_forward(cv.sag(rot['pelvis'][:, :, 0], fwd_pelvis))
    report['pelvis_vs_model'] = _finite_stats(pelvis, model_tilt)
    mm = cv.model_geometry(model_text, 'r')['markers'] if model_text is not None else {}
    foot_lm = {}
    for S_ in 'LR':
        g = cv.model_geometry(model_text, S_.lower())['markers'] if model_text is not None else {}
        if all(f'{S_}{k}' in g for k in ('CAL', 'MT1', 'MT5')):
            v = (g[f'{S_}MT1'] + g[f'{S_}MT5']) / 2 - g[f'{S_}CAL']
            foot_lm[S_] = float(np.degrees(np.arctan2(v[1], v[0])))   # heel-to-toe line in the model calcaneus x-y plane
    report['foot_model_landmark_angle_deg'] = foot_lm
    if all(k in mm for k in ('LASI', 'RASI', 'LPSI', 'RPSI')):
        v = (mm['LASI'] + mm['RASI']) / 2 - (mm['LPSI'] + mm['RPSI']) / 2
        report['pelvis_model_landmark_angle_deg'] = float(np.degrees(np.arctan2(v[1], v[0])))   # marker pelvis minus model tilt expected here
    report['finite_share'] = {k: round(float(np.isfinite(v).mean()), 6) for k, v in cols.items() if k != 'time_s'}
    return cols, report


def write_parquet(path, cols):
    schema = pa.schema([(k, pa.float64()) for k in cols])
    table = pa.Table.from_arrays([pa.array(np.ascontiguousarray(v), type=pa.float64(), from_pandas=False) for v in cols.values()], schema=schema)
    with pq.ParquetWriter(str(path), schema, compression='zstd') as w:
        w.write_table(table, row_group_size=4096)


def load_spans(root):
    out = {}
    p = ROOT / root / 'segments.jsonl'
    for line in p.read_text().splitlines():
        r = json.loads(line)
        if r.get('start_index') is not None and r.get('end_index') is not None:
            out.setdefault(r['recording'], []).append((int(r['start_index']), int(r['end_index']), r['side']))
    return out


def run(args):
    out_root = ROOT / args.output_root
    if out_root.exists() and any(out_root.iterdir()):
        raise RunError(f'{out_root} is not empty; never overwrite')
    out_root.mkdir(parents=True, exist_ok=True)
    subject = args.subject
    x01_root = X01_ROOTS[subject]
    ledger = {}
    for line in (ROOT / x01_root / 'ledger.jsonl').read_text().splitlines():
        e = json.loads(line)
        ledger[e['recording']] = e
    part = json.loads((ROOT / x01_root / 'participant.json').read_text())
    mass = part['mass_kg']['readme']
    model_name = MODEL_FILE[subject]
    model_path = SOURCE / 'RawData' / subject / 'Models' / model_name
    if rd.sha256_file(model_path) != part['models'][model_name]['sha256']:
        raise RunError('model hash differs from the X01 participant file')
    model_text = model_path.read_text()
    spans_by_rec = load_spans(S01_ROOTS[subject])
    wanted = args.records or sorted(ledger)
    receipts = []
    with (out_root / 'ledger.jsonl').open('x') as stream:
        for rec in wanted:
            x01 = ledger[rec]
            cols, rep = process_recording(subject, rec, x01, spans_by_rec.get(rec, []), mass, model_text, args.source, x01_root)
            write_parquet(out_root / f'{rec}.parquet', cols)
            back = pq.ParquetFile(str(out_root / f'{rec}.parquet'), buffer_size=0)
            rep['output'] = {'file': f'{rec}.parquet', 'rows': back.metadata.num_rows, 'columns': back.metadata.num_columns,
                             'sha256': rd.sha256_file(out_root / f'{rec}.parquet'), 'row_groups': back.metadata.num_row_groups}
            rep['model_file'] = model_name
            rep['mass_kg_used_for_check'] = mass
            rep['peak_rss_mib_so_far'] = peak_rss_mib()
            stream.write(json.dumps(rep, sort_keys=True) + '\n')
            stream.flush()
            receipts.append(rep)
            del cols
    bad = [r for r in receipts if r['composition_max_abs_err_rad'] > 1e-12]
    summary = {'subject': subject, 'recordings_done': len(receipts), 'recordings_failed': 0, 'peak_rss_mib': peak_rss_mib(),
               'composition_over_1e-12': [r['recording'] for r in bad], 'scientific_approval': False,
               'status': 'participant_done_unreviewed' if not bad else 'composition_failed'}
    _atomic_json(out_root / 'run_summary.json', summary)
    return 0 if summary['status'] == 'participant_done_unreviewed' else 1


def make_spec(args):
    from contributor_tools import guarded_launcher as gl
    command = ['python3', 'contributor_tools/run_gt23_c06.py', args.kind, '--output-root', args.output_root]
    bindings = {c: gl.sha256_file(ROOT / c) for c in CODE}
    if args.kind == 'run':
        command += ['--subject', args.subject]
        for r in args.records or []:
            command += ['--records', r]
        command += ['--source', str(SOURCE)]
        for p in (f'{X01_ROOTS[args.subject]}/ledger.jsonl', f'{X01_ROOTS[args.subject]}/participant.json',
                  f'{S01_ROOTS[args.subject]}/segments.jsonl'):
            bindings[p] = rd.sha256_file(ROOT / p)
        names = ['run_summary.json']
    elif args.kind == 'diag':
        command += ['--tasks', args.tasks, '--source', str(SOURCE)]
        for sj in SUBJECTS:
            for p_ in (f'{X01_ROOTS[sj]}/ledger.jsonl', f'{X01_ROOTS[sj]}/participant.json', f'{S01_ROOTS[sj]}/segments.jsonl'):
                bindings[p_] = rd.sha256_file(ROOT / p_)
        names = ['diag.json', 'run_summary.json']
    else:
        command += ['--roots'] + list(args.roots)
        for r in args.roots:
            bindings[f'{r}/run_summary.json'] = rd.sha256_file(ROOT / r / 'run_summary.json')
        names = ['summary.json']
    spec = {'job_id': args.job_id, 'command': command, 'cwd': str(ROOT), 'output_root': args.output_root,
            'receipt_path': args.receipt, 'bindings': bindings, 'timeout_seconds': 3600, 'kill_after_seconds': 30,
            'poll_seconds': 15, 'startup_memory_mib': {'linux': 3584, 'windows': 2816},
            'runtime_memory_mib': {'linux': 2048, 'windows': 2048}, 'expected_output_names': names,
            'address_space_mib': 768}
    with Path(args.spec_out).open('x') as stream:
        json.dump(spec, stream, indent=2)
        stream.write('\n')
    return 0


def _agg(values):
    v = [x for x in values if x is not None and np.isfinite(x)]
    if not v:
        return None
    return {'n': len(v), 'median': float(np.median(v)), 'min': float(np.min(v)), 'max': float(np.max(v))}


def summarize(args):
    led = []
    for root in args.roots:
        led += [json.loads(x) for x in (ROOT / root / 'ledger.jsonl').read_text().splitlines()]
    out = {'recordings': len(led), 'composition_max_abs_err_rad': max(r['composition_max_abs_err_rad'] for r in led),
           'second_implementation_max_abs_diff': {
               'angles_rad': max(r['second_implementation']['max_abs_diff']['angles_rad'] for r in led),
               'cop_m': max(r['second_implementation']['max_abs_diff']['cop_m'] for r in led)},
           'per_subject_leg': {}, 'pelvis_vs_model': {}, 'held_columns': {}, 'speed_sign_by_task': {}}
    by = {}
    for r in led:
        for S, leg in r['legs'].items():
            by.setdefault((r['subject'], S), []).append((r, leg))
    for (subj, S), items in sorted(by.items()):
        d = {}
        for k in ('hip', 'knee', 'ankle'):
            ss = [leg[f'{k}_angle_vs_publisher'] for _, leg in items]
            d[k] = {'offset_deg': _agg([s.get('median_offset_deg') for s in ss]), 'r': _agg([s.get('r') for s in ss]),
                    'offset_deg_walking_tasks': _agg([leg[f'{k}_angle_vs_publisher'].get('median_offset_deg') for r, leg in items
                                                      if r['task'] in ('normal_walk', 'dynamic_walk', 'incline_walk', 'weighted_walk', 'obstacle_walk')])}
        d['foot_flat_mid_stance_deg_all_stances'] = _agg([leg['foot_angle_mid_stance_deg_median'] for _, leg in items])
        d['foot_flat_mid_stance_deg_normal_walk'] = _agg([leg['foot_angle_mid_stance_deg_median'] for r, leg in items if r['task'] == 'normal_walk'])
        d['cop_outside_foot_share'] = _agg([leg.get('cop_outside_foot_share', {}).get('share') for _, leg in items])
        d['ankle_moment_r'] = _agg([leg.get('ankle_moment_check', {}).get('r') for _, leg in items])
        d['ankle_moment_slope'] = _agg([leg.get('ankle_moment_check', {}).get('slope_published_per_computed') for _, leg in items])
        d['cop_anterior_first_m'] = _agg([leg['cop_anterior_first_m_median'] for r, leg in items if r['task'] == 'normal_walk'])
        d['cop_anterior_last_m'] = _agg([leg['cop_anterior_last_m_median'] for r, leg in items if r['task'] == 'normal_walk'])
        d['cop_vertical_m'] = _agg([leg['cop_vertical_median_m'] for r, leg in items if r['task'] == 'normal_walk'])
        d['cop_lateral_m'] = _agg([leg['cop_lateral_median_m'] for r, leg in items if r['task'] == 'normal_walk'])
        d['ankle_centre_model_minus_markers_mm_tibia_frame'] = [
            _agg([(leg.get('ankle_centre_model_minus_marker_midpoint_mm_tibia_frame') or {}).get('via_tibia_markers', [None] * 3)[k] for _, leg in items])
            for k in range(3)]
        d['markers_vs_model_foot_offset_deg'] = _agg([(leg.get('markers_vs_model_axes') or {}).get('foot_marker_vs_model_calcaneus_x', {}).get('median_offset_deg') for _, leg in items])
        d['foot_model_landmark_angle_deg'] = _agg([r.get('foot_model_landmark_angle_deg', {}).get(S) for r, _ in items])
        d['contact_heading_loaded_share'] = _agg([(r.get('heading_from_contact_when_no_span', {}).get(S) or {}).get('loaded_samples_filled', 0) /
                                                  max(1, (r.get('heading_from_contact_when_no_span', {}).get(S) or {}).get('loaded_samples', 1)) for r, _ in items if r['forward_task']])
        d['markers_vs_model_thigh_offset_deg'] = _agg([(leg.get('markers_vs_model_axes') or {}).get('thigh', {}).get('median_offset_deg') for _, leg in items])
        d['markers_vs_model_shank_offset_deg'] = _agg([(leg.get('markers_vs_model_axes') or {}).get('shank', {}).get('median_offset_deg') for _, leg in items])
        out['per_subject_leg'][f'{subj}/{S}'] = d
    for subj in sorted({r['subject'] for r in led}):
        rs = [r for r in led if r['subject'] == subj]
        out['pelvis_vs_model'][subj] = {'r': _agg([r['pelvis_vs_model'].get('r') for r in rs]),
                                        'model_landmark_angle_deg': _agg([r.get('pelvis_model_landmark_angle_deg') for r in rs]),
                                        'resid_sd_deg': _agg([r['pelvis_vs_model'].get('resid_sd_deg') for r in rs]),
                                        'offset_deg': _agg([r['pelvis_vs_model'].get('median_offset_deg') for r in rs])}
    for r in led:
        for col, why in r['held_columns'].items():
            out['held_columns'].setdefault(why, {}).setdefault(r['task'], 0)
            out['held_columns'][why][r['task']] += 1
    tasks = sorted({r['task'] for r in led})
    out['cop_outside_foot_share_by_task'] = {t_: _agg([leg.get('cop_outside_foot_share', {}).get('share') for r in led if r['task'] == t_ for leg in r['legs'].values()]) for t_ in tasks}
    out['ankle_moment_slope_by_task'] = {t_: _agg([leg.get('ankle_moment_check', {}).get('slope_published_per_computed') for r in led if r['task'] == t_ for leg in r['legs'].values()]) for t_ in tasks}
    for t in tasks:
        row = {}
        for k in ('hip', 'knee', 'ankle'):
            vals = [leg[f'{k}_speed_vs_publisher'].get('sign_agreement') for r in led if r['task'] == t for leg in r['legs'].values()]
            row[k] = _agg(vals)
        out['speed_sign_by_task'][t] = row
    (ROOT / args.output_root).mkdir(parents=True, exist_ok=False)
    _atomic_json(ROOT / args.output_root / 'summary.json', out)
    return 0


def diag(args):
    """Diagnostic over the named tasks of every participant (one recording resident at a time): outside-foot share,
    pressure-point height facts and ankle-moment ratio per recording and leg. Writes one JSON, no data arrays."""
    out_root = ROOT / args.output_root
    out_root.mkdir(parents=True, exist_ok=False)
    tasks = set(args.tasks.split(','))
    rows = []
    for subject in SUBJECTS:
        x01_root = X01_ROOTS[subject]
        ledger = {}
        for line in (ROOT / x01_root / 'ledger.jsonl').read_text().splitlines():
            e = json.loads(line)
            ledger[e['recording']] = e
        part = json.loads((ROOT / x01_root / 'participant.json').read_text())
        model_text = (SOURCE / 'RawData' / subject / 'Models' / MODEL_FILE[subject]).read_text()
        spans_by_rec = load_spans(S01_ROOTS[subject])
        for rec in sorted(ledger):
            if seg.task_of(rec) not in tasks:
                continue
            cols, rep = process_recording(subject, rec, ledger[rec], spans_by_rec.get(rec, []), part['mass_kg']['readme'], model_text, args.source, x01_root)
            mk, _, _ = read_markers(Path(args.source) / 'RawData' / subject / 'MarkerData' / f'{rec}.trc', ('LCAL', 'RCAL'))
            for S in 'LR':
                w = WORD[S]
                y = cols[f'cop_lab_y_{w}_m']
                ok = np.isfinite(y) & np.isfinite(mk[f'{S}CAL'][:, 1])
                if not ok.any():
                    continue
                leg = rep['legs'][S]
                rows.append({'subject': subject, 'recording': rec, 'task': rep['task'], 'leg': S, 'loaded_samples': int(ok.sum()),
                             'outside_share': leg['cop_outside_foot_share']['share'], 'vertical_median_m': leg['cop_vertical_median_m'],
                             'plate_height_median_m': float(np.median(y[ok])),
                             'heel_minus_plate_median_m': float(np.median(mk[f'{S}CAL'][ok, 1] - y[ok])),
                             'heel_height_range_in_load_m': float(np.ptp(mk[f'{S}CAL'][ok, 1])),
                             'ankle_moment_slope': leg.get('ankle_moment_check', {}).get('slope_published_per_computed'),
                             'ankle_moment_r': leg.get('ankle_moment_check', {}).get('r')})
            del cols
    _atomic_json(out_root / 'diag.json', {'tasks': sorted(tasks), 'rows': rows})
    _atomic_json(out_root / 'run_summary.json', {'status': 'diag_done_unreviewed', 'rows': len(rows), 'peak_rss_mib': peak_rss_mib(), 'scientific_approval': False})
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('run')
    s.add_argument('--output-root', required=True)
    s.add_argument('--subject', required=True, choices=SUBJECTS)
    s.add_argument('--records', action='append')
    s.add_argument('--source', default=str(SOURCE))
    s = sub.add_parser('spec')
    s.add_argument('--kind', choices=('run', 'summary', 'diag'), required=True)
    s.add_argument('--tasks')
    s.add_argument('--job-id', required=True)
    s.add_argument('--output-root', required=True)
    s.add_argument('--receipt', required=True)
    s.add_argument('--spec-out', required=True)
    s.add_argument('--subject', choices=SUBJECTS)
    s.add_argument('--records', action='append')
    s.add_argument('--roots', nargs='*')
    s = sub.add_parser('diag')
    s.add_argument('--output-root', required=True)
    s.add_argument('--tasks', required=True)
    s.add_argument('--source', default=str(SOURCE))
    s = sub.add_parser('summary')
    s.add_argument('--output-root', required=True)
    s.add_argument('--roots', nargs='+', required=True)
    args = p.parse_args(argv)
    return {'run': run, 'spec': make_spec, 'summary': summarize, 'diag': diag}[args.cmd](args)


if __name__ == '__main__':
    raise SystemExit(main())
