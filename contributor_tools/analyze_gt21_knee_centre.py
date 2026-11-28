"""A5: is the Georgia Tech 2021 (GT21) knee (and ankle) joint-centre placement biased?  DRAFT: written in phase 1, not run.

Why: with LocoHub's geometry GT21 people stand with the knee 6.7 degrees flexed on average (A3/A4), the authors' own IK gives
7.2, GT23 and UM21 stand at about 1, and in level walking GT21's knee is about 8 degrees more flexed at mid-stance. LocoHub
places the knee and ankle centres from the authors' scaled OpenSim model (D-GT21-REB-1 = C: knee and ankle centres from the
shank rigid fit, hip centre from the pelvis fit). GT21 has no hip marker and only lateral knee and ankle markers. This script
asks whether a marker-only placement of the knee and ankle centres, independent of the model's joint definitions, changes the
standing and walking numbers.

Inputs (read only; nothing under converted_datasets/ or a source folder is changed)
  * the static-trial export of A3 (gt21_static_export_v1/<AB##>/: CSV markers, static_meta_<AB##>.json);
  * the participant's scaled model (found as in run_gt21_rb_pass.ROOTS) and, if present, generic models (--generic-model);
  * a few SEEDED level-walking recordings per person from the RB01 inventory (markers + gait cycle tables, read one at a time
    with the fail-closed numeric reader) and, per recording, a few seeded strides per leg;
  * the A3 outputs (gt21_static_analysis_v1/per_participant.csv and comparison.json) for the package's own mid-stance walking
    means, the authors' IK standing knee and the GT23/UM21 reference means.

What is computed, per person
  1. Centre offsets (mm). Model centre (as LocoHub places it) minus a marker-only estimate, in the thigh frame (knee) and the
     shank frame (ankle): anterior, distal, rightward components, the 3-D length and the sagittal-plane length. The frames use
     proximal-to-distal = model hip to knee (thigh) or model knee to ankle (shank), anterior = the leg-plane forward direction
     (the pass's own plane) made perpendicular to that long axis. Positive anterior = model centre is in front of the marker
     estimate; positive distal = model centre is lower. Also the model-implied half width: how far medial of the lateral marker
     the model puts its centre, measured in the lab (a width-free check of the width assumption below).
  2. Marker-only estimate: lateral marker shifted medially by half the joint width along a lateral direction made perpendicular
     to the segment's long axis. WIDTHS ARE NOT IN THE DATA: the RB01 subject info holds Subject, Age, Gender, Height, Weight
     only, and no knee or ankle width is recorded. Primary assumption (a typical adult value, NOT sourced from this dataset and
     to be replaced by a cited value before any claim): knee width 0.090 m, ankle (malleoli) width 0.070 m. A sensitivity grid
     (knee, ankle) = (0.07, 0.06), (0.09, 0.07), (0.11, 0.09) m is run and its spread reported. Because the lateral shift
     lies almost perpendicular to the leg plane, it moves sagittal angles very little; the anterior/distal offsets, which come
     from the model definition against the marker positions, are what matter. The lateral direction is the pelvis right
     direction (mid-ASIS/PSIS) orthogonalised to the segment (marker-only; --lateral model_axis uses the model knee axis).
  3. Angles. Thigh, shank, knee and ankle recomputed with the same helpers and per-leg plane as the pass (gt21_rb_pass:
     leg_centres, knee_axis_to_right, plane_forward, segment_angles, joint_angles; the hip centre is the model's in all routes
     because there is no hip marker; the foot angle uses heel and toe, so it does not depend on the centres). Three routes:
     model (the pass), knee_marker (knee centre replaced), both_marker (knee and ankle centres replaced). Static: mean over the
     trial. Walking: mean over seeded strides, 20-35 percent of stride (sheet-A window) between consecutive same-leg heel
     strikes. The walking gap "before" is the package's own mid-stance mean (A3 mid_ columns) minus the GT23/UM21 reference;
     "after" subtracts this script's per-person route change (model minus marker route over the sampled strides), so the sampled
     strides need not match the package's speed or stride set to be comparable.
  4. The scaled model: knee joint location in the parent (femur) and child (tibia) frames, orientation of the parent frame
     (any fixed rotation about the flexion axis is a fixed flexion offset), the flexion axis in the femur frame, and the knee
     translation functions (coupled to flexion?). A model-only curve gives LocoHub's knee angle (thigh line minus shank line,
     hip centre to knee centre to ankle centre) against the model coordinate q over a grid; at q = 0 it shows any neutral
     misalignment of the centre lines, and at the authors' static IK q it shows the LocoHub knee the model implies. The same
     inspection is run on generic models when present, so a scaling effect can be separated from the model definition.

Missing stays missing: a trial or stride with no valid frame has no value and is counted, never filled. Frames the pass would
hold (fit residual or axis checks) are excluded. Thresholds in classify() are this check's own rules for reading the result,
not reference ranges; they are listed in the report for approval. No scientific approval is claimed.

Run: `compute` writes a NEW out-root (CSV and JSON only) through the guarded launcher (spec: build_gt21_knee_centre_specs.py);
`sheet` reads the small CSV and JSON and writes review_sheets/A5-gt21-knee-centre/.
"""
import os
for _k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_k] = '1'
os.environ.setdefault('ARROW_DEFAULT_MEMORY_POOL', 'system')
import argparse
import csv
import json
import math
import random
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

D = 180.0 / math.pi
RECON = ROOT / 'converted_datasets/reconversion_v2'
STATIC_ROOT = RECON / 'gt21_static_export_v1'
A3_ROOT = RECON / 'gt21_static_analysis_v1'
OUT_ROOT = RECON / 'gt21_knee_centre_v1'
INVENTORY = RECON / 'gt21_rb01_inventory_20261123/recording_ledger.jsonl'
SHEET_DIR = ROOT / 'review_sheets/A5-gt21-knee-centre'
GENERIC_MODELS = (ROOT / 'contributor_tools/conversion_scripts/Gait120/rajagopal_original.osim',
                  ROOT / 'contributor_tools/conversion_scripts/Gait120/rajagopal_gait120.osim')
KNEE_WIDTH_M, ANKLE_WIDTH_M = 0.090, 0.070              # ASSUMED typical adult widths; not in the data (see the module note)
WIDTH_GRID_M = ((0.07, 0.06), (0.09, 0.07), (0.11, 0.09))   # (knee, ankle) sensitivity grid
VARIANTS = ('model', 'knee_marker', 'both_marker')
ANGLES = ('thigh', 'shank', 'knee', 'ankle')
OFFSETS = ('knee_ap', 'knee_pd', 'knee_ml', 'knee_3d', 'knee_sag', 'kneeS_ap', 'kneeS_pd',
           'ankle_ap', 'ankle_pd', 'ankle_ml', 'ankle_3d', 'ankle_sag', 'hw_knee_model', 'hw_ankle_model')
WINDOW = (20.0, 35.0)                                   # percent of stride (sheet A)
STRIDE_SECONDS = (0.6, 2.0)                             # this check's own sanity window for one stride
Q_GRID_DEG = (10.0, 0.0, -5.0, -10.0, -20.0, -40.0, -60.0)   # OpenSim knee coordinate (flexion negative)
ASSUMED_PARAMETERS = {'knee_width_m': KNEE_WIDTH_M, 'ankle_width_m': ANKLE_WIDTH_M,
                      'source': 'assumed typical adult values; RB01 subject info records no knee or ankle width'}


# ------------------------------------------------------------------------------------------------ pure geometry
def unit(v):
    from contributor_tools import gt21_rb_pass as rb
    return rb.unit(v)


def lateral_unit(base_right, long_axis, leg):
    """Lateral direction (n, 3) for a leg: the base 'person's right' vector, negated for the left leg, made perpendicular to the
    segment's long axis. NaN where the base is parallel to the axis or not finite."""
    base = np.asarray(base_right, float) * (1.0 if leg == 'right' else -1.0)
    u = unit(long_axis)
    return unit(base - np.sum(base * u, axis=-1, keepdims=True) * u)


def marker_centre(marker, lateral, half_width_m):
    """Marker-only joint centre: the lateral marker moved medially by half the joint width along the lateral direction."""
    return np.asarray(marker, float) - np.asarray(lateral, float) * half_width_m


def segment_frame(prox, dist, fwd_leg):
    """(proximal-to-distal, anterior, rightward) unit axes (n, 3). Anterior = the leg-plane forward direction made perpendicular
    to the long axis; rightward = distal x anterior (for a leg hanging straight down with forward = +x this is +z)."""
    e_pd = unit(np.asarray(dist, float) - np.asarray(prox, float))
    f = np.asarray(fwd_leg, float)
    e_ap = unit(f - np.sum(f * e_pd, axis=-1, keepdims=True) * e_pd)
    return e_pd, e_ap, np.cross(e_pd, e_ap)


def offset_in_frame(model_pt, marker_pt, frame):
    """Model centre minus marker estimate, in millimetres, in a segment frame. Returns dict ap, pd, ml, d3, sag (arrays)."""
    e_pd, e_ap, e_r = frame
    d = (np.asarray(model_pt, float) - np.asarray(marker_pt, float)) * 1000.0
    ap, pdv, ml = np.sum(d * e_ap, axis=-1), np.sum(d * e_pd, axis=-1), np.sum(d * e_r, axis=-1)
    return {'ap': ap, 'pd': pdv, 'ml': ml, 'd3': np.linalg.norm(d, axis=-1), 'sag': np.hypot(ap, pdv)}


def deg_per_mm_ap(thigh_len_m, shank_len_m):
    """Knee-angle change (degrees) for 1 mm of knee-centre displacement along the anterior direction: the thigh and shank lines
    tilt in opposite senses, so the knee angle changes by d * (1/L_thigh + 1/L_shank) (small angles)."""
    return (1.0 / thigh_len_m + 1.0 / shank_len_m) * 1e-3 * D


def classify(static_share, walk_share, marker_static_knee_deg):
    """Reading of the result (this check's own rules, not reference ranges; listed in the report for approval).

    static_share, walk_share: fraction of the model-route mean standing knee / mean walking knee gap that the marker route
    removes. marker_static_knee_deg: mean standing knee on the marker route.
      geometry_biased : both shares >= 0.6 and the marker-route standing knee <= 3 degrees;
      posture_real    : both shares <= 0.25, or the marker-route standing knee is still >= 5 degrees;
      mixed           : anything else."""
    if not (np.isfinite(static_share) and np.isfinite(walk_share) and np.isfinite(marker_static_knee_deg)):
        return 'not_determined'
    if static_share >= 0.6 and walk_share >= 0.6 and marker_static_knee_deg <= 3.0:
        return 'geometry_biased'
    if (static_share <= 0.25 and walk_share <= 0.25) or marker_static_knee_deg >= 5.0:
        return 'posture_real'
    return 'mixed'


def nanmean_of(values):
    v = np.asarray([x for x in values if x is not None and np.isfinite(x)], float)
    return float(v.mean()) if v.size else float('nan')


def masked_mean(x, mask):
    x = np.asarray(x, float)[mask]
    x = x[np.isfinite(x)]
    return float(x.mean()) if x.size else float('nan')


# ------------------------------------------------------------------------------------------------ per-recording routes
def marker_dict(markers):
    """Marker positions in metres (n, 3) for every x/y/z column triple of a source table."""
    from contributor_tools import gt21_rb_pass as rb
    out = {}
    for k in markers:
        if k.endswith('_x'):
            a = rb._marker_array(markers, k[:-2])
            if a is not None:
                out[k[:-2]] = a
    return out


def _leg_results(P, geo, hw_knee, hw_ankle, lateral_mode, grid):
    from contributor_tools import gt21_rb_pass as rb
    for name in rb.PELVIS_MARKERS + tuple(f'{S}_{m}' for S in 'RL' for m in rb.FOOT_MARKERS):
        if name not in P:
            raise rb.RecordingExcluded(f'missing_markers: {name}')
    asis_mid, psis_mid = (P['L_ASIS'] + P['R_ASIS']) / 2, (P['L_PSIS'] + P['R_PSIS']) / 2
    right_ref = np.cross(rb.pelvis_forward(asis_mid, psis_mid), rb.UP)
    pelvis = rb.pelvis_angle(asis_mid, psis_mid)
    out = {}
    for leg in rb.LEGS:
        s, S = rb.SIDE[leg].lower(), rb.SIDE[leg]
        c = rb.leg_centres(geo[s], geo[s], P, s)
        axis = rb.knee_axis_to_right(c['knee_axis_raw'], right_ref)
        fwd = rb.plane_forward(axis)
        ang = rb.knee_axis_marker_angle(axis, c['knee'], c['hip'], P[f'{S}_Knee_Lat'], leg) if f'{S}_Knee_Lat' in P else None
        held = rb.geometry_hold(list(c['fit_rms_m'].values()), ang) > 0
        base = axis if lateral_mode == 'model_axis' else right_ref
        nan3 = np.full_like(c['knee'], np.nan)
        kl = P.get(f'{S}_Knee_Lat', nan3)
        al = P.get(f'{S}_Ankle_Lat', nan3)
        lat_k = lateral_unit(base, c['knee'] - c['hip'], leg)
        lat_a = lateral_unit(base, c['ankle'] - c['knee'], leg)

        def routes(hk, ha):
            knee_m, ankle_m = marker_centre(kl, lat_k, hk / 2.0), marker_centre(al, lat_a, ha / 2.0)   # widths -> half widths
            return {'model': (c['knee'], c['ankle']), 'knee_marker': (knee_m, c['ankle']), 'both_marker': (knee_m, ankle_m)}, knee_m, ankle_m
        r, knee_m, ankle_m = routes(hw_knee, hw_ankle)
        angles = {}
        for v, (kn, an) in r.items():
            seg = rb.segment_angles(fwd, c['hip'], kn, an, P[f'{S}_Heel'], P[f'{S}_Toe_Tip'])
            ja = rb.joint_angles(pelvis, seg['thigh'], seg['shank'], seg['foot'])
            angles[v] = {'thigh': seg['thigh'] * D, 'shank': seg['shank'] * D, 'knee': ja['knee'] * D, 'ankle': ja['ankle'] * D}
        thigh_f, shank_f = segment_frame(c['hip'], c['knee'], fwd), segment_frame(c['knee'], c['ankle'], fwd)
        ko, kos, ao = offset_in_frame(c['knee'], knee_m, thigh_f), offset_in_frame(c['knee'], knee_m, shank_f), \
            offset_in_frame(c['ankle'], ankle_m, shank_f)
        off = {'knee_ap': ko['ap'], 'knee_pd': ko['pd'], 'knee_ml': ko['ml'], 'knee_3d': ko['d3'], 'knee_sag': ko['sag'],
               'kneeS_ap': kos['ap'], 'kneeS_pd': kos['pd'],
               'ankle_ap': ao['ap'], 'ankle_pd': ao['pd'], 'ankle_ml': ao['ml'], 'ankle_3d': ao['d3'], 'ankle_sag': ao['sag'],
               'hw_knee_model': np.sum((kl - c['knee']) * lat_k, axis=-1) * 1000.0,        # lateral marker beyond the model centre
               'hw_ankle_model': np.sum((al - c['ankle']) * lat_a, axis=-1) * 1000.0,
               'thigh_len_mm': np.linalg.norm(c['knee'] - c['hip'], axis=-1) * 1000.0,
               'shank_len_mm': np.linalg.norm(c['ankle'] - c['knee'], axis=-1) * 1000.0}
        sens = []
        for hk, ha in grid:
            rs, _, _ = routes(hk, ha)
            kn, an = rs['both_marker']
            seg = rb.segment_angles(fwd, c['hip'], kn, an, P[f'{S}_Heel'], P[f'{S}_Toe_Tip'])
            sens.append(rb.joint_angles(pelvis, seg['thigh'], seg['shank'], seg['foot'])['knee'] * D)
        out[leg] = {'angles': angles, 'off': off, 'held': held, 'sens_knee': sens}
    return out


def leg_results(markers, geo, hw_knee=KNEE_WIDTH_M, hw_ankle=ANKLE_WIDTH_M, lateral_mode='pelvis', grid=WIDTH_GRID_M):
    """Per-leg arrays of all routes for one recording table. If the table lacks the pass's thigh or shank cluster (fewer than
    three fit markers), the same call is repeated with the clusters widened (as in A3); the route is returned as text."""
    from contributor_tools import gt21_rb_pass as rb
    from contributor_tools import analyze_gt21_static_pose as a3
    P = marker_dict(markers)
    try:
        return _leg_results(P, geo, hw_knee, hw_ankle, lateral_mode, grid), 'pass_unchanged'
    except rb.RecordingExcluded as first:
        if 'fit markers' not in str(first):
            raise
    thigh, shank = a3.widened_clusters(list(markers), geo)
    with a3.patched_clusters(thigh, shank):
        return _leg_results(P, geo, hw_knee, hw_ankle, lateral_mode, grid), 'widened_cluster_markers'


def summarise_leg(res_leg, idx=None):
    """Means over the leg's valid, not-held frames (all, or those in idx) as a flat dict: ang_<variant>_<q> (degrees),
    off_<name> (mm), len, sensitivity knee angles, and the frame count."""
    n = len(res_leg['held'])
    mask = ~res_leg['held']
    if idx is not None:
        sel = np.zeros(n, bool)
        sel[np.asarray(idx, int)[(np.asarray(idx) >= 0) & (np.asarray(idx) < n)]] = True
        mask = mask & sel
    out = {}
    for v in VARIANTS:
        for q in ANGLES:
            out[f'ang_{v}_{q}'] = masked_mean(res_leg['angles'][v][q], mask)
    for k, arr in res_leg['off'].items():
        out[f'off_{k}'] = masked_mean(arr, mask)
    for i, arr in enumerate(res_leg['sens_knee']):
        out[f'sens_knee_{i}'] = masked_mean(arr, mask)
    out['n_frames'] = int((mask & np.isfinite(res_leg['angles']['model']['knee'])).sum())
    return out


def combine(dicts):
    """Mean of each key over a list of summary dicts (a key with no finite value is NaN)."""
    def numeric(v):
        return isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool)
    keys = sorted({k for d in dicts for k, v in d.items() if numeric(v)})
    return {k: nanmean_of([d.get(k) if numeric(d.get(k)) else None for d in dicts]) for k in keys if k != 'n_frames'} | \
        {'n_frames': int(sum(d.get('n_frames', 0) for d in dicts))}


# ------------------------------------------------------------------------------------------------ walking strides
def stride_windows(heel_strikes, t, lo=WINDOW[0], hi=WINDOW[1], seconds=STRIDE_SECONDS):
    """Index arrays of the lo-hi percent window of each stride between consecutive heel strikes (sample indices on clock t).
    A stride outside the duration window (a missed event, a pause) is skipped."""
    hs = np.sort(np.asarray(heel_strikes, int))
    t = np.asarray(t, float)
    out = []
    for a, b in zip(hs[:-1], hs[1:]):
        if not (seconds[0] <= t[b] - t[a] <= seconds[1]):
            continue
        i0, i1 = int(math.ceil(a + lo / 100.0 * (b - a))), int(math.floor(a + hi / 100.0 * (b - a)))
        if i1 >= i0:
            out.append(np.arange(i0, i1 + 1))
    return out


def sample_items(items, k, rng):
    """k items drawn without replacement with a seeded generator (all of them if fewer), returned in the original order."""
    items = list(items)
    if len(items) <= k:
        return items
    keep = sorted(rng.sample(range(len(items)), k))
    return [items[i] for i in keep]


def load_inventory(path=INVENTORY, mode='levelground'):
    """{subject: [row]} of the RB01 recording ledger for one mode (streamed line by line)."""
    rows = {}
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            if r.get('mode') == mode:
                rows.setdefault(r['subject'], []).append(r)
    for v in rows.values():
        v.sort(key=lambda r: (r['session'], r['recording']))
    return rows


def walking_summaries(subject, rows, geo, args, rng):
    """Per-stride summary dicts (with 'leg', 'recording') for the seeded recordings and strides of one person."""
    from contributor_tools import gt21_numeric_source as src
    from contributor_tools import gt21_rb_pass as rb
    from contributor_tools import analyze_gt21_static_pose as a3
    out, skipped = [], []
    for row in sample_items(rows, args.recordings_per_person, rng):
        base = a3.MODEL_ROOTS[row['source']] / subject / row['session'] / row['mode']
        name = f"{row['session']}/{row['recording']}"
        try:
            markers = src.read_numeric_table(base / 'markers' / f"{row['recording']}.mat")
            gcs = {}
            for ch, leg in (('gcRight', 'right'), ('gcLeft', 'left')):
                try:
                    gcs[leg] = src.read_numeric_table(base / ch / f"{row['recording']}.mat")
                except Exception:
                    gcs[leg] = None
            res, route = leg_results(markers, geo, args.knee_width_m, args.ankle_width_m, args.lateral)
            t = np.asarray(markers['Header'], float)
            for leg in rb.LEGS:
                if gcs[leg] is None:
                    skipped.append(f'{name}: no gait cycle table for {leg}')
                    continue
                hs, _, _ = rb.event_samples(gcs[leg], t)
                for idx in sample_items(stride_windows(hs, t), args.strides_per_leg, rng):
                    d = summarise_leg(res[leg], idx)
                    d.update(leg=leg, recording=name, route=route)
                    out.append(d)
        except Exception as exc:                                   # one recording is skipped with its reason; the run goes on
            skipped.append(f'{name}: {type(exc).__name__}: {exc}'[:300])
    return out, skipped


# ------------------------------------------------------------------------------------------------ the model
def eval_translations(translations, q):
    tr = np.zeros((len(q), 3))
    from contributor_tools import gt21_rb_pass as rb
    for _, axis, spec in translations:
        tr += rb.eval_function(spec, q)[:, None] * np.asarray(axis, float)[None, :]
    return tr


def model_knee_flexion(inspect, q):
    """LocoHub knee flexion (degrees; thigh line minus shank line, hip centre to knee centre to ankle centre) implied by the model
    alone at knee coordinates q (radians, OpenSim sign), in the femur frame, in the plane perpendicular to the flexion axis.
    Knee centre = the joint point (parent location plus the angle-dependent translation, in the rotated parent frame);
    thigh vector = that point minus the hip centre (hip joint's child location); shank vector = ankle location minus knee
    child location, rotated by the knee rotation. Returns (flexion degrees (n), straight-leg sign check text)."""
    from contributor_tools import gt21_rb_pass as rb
    q = np.atleast_1d(np.asarray(q, float))
    Rpo = rb.euler_xyz_body_fixed(inspect['_parent_orientation'])
    a = Rpo @ inspect['_axis_parent']
    a = a * (1.0 if a[2] >= 0 else -1.0) if a[2] != 0 else a * np.nan          # axis to the person's right (femur +z)
    tr = eval_translations(inspect['_translations'], q)
    joint = np.asarray(inspect['_knee_parent_location'], float) + tr @ Rpo.T
    thigh = joint - np.asarray(inspect['_hip_child_location'], float)
    Rj = rb.rodrigues(inspect['_axis_parent'], q)
    shank = np.einsum('ij,njk,k->ni', Rpo, Rj, np.asarray(inspect['_ankle_in_tibia'], float) - np.asarray(inspect['_knee_child_location'], float))
    thigh = thigh - np.sum(thigh * a, axis=-1, keepdims=True) * a
    shank = shank - np.sum(shank * a, axis=-1, keepdims=True) * a
    flex = np.arctan2(np.sum(np.cross(shank, thigh) * a, axis=-1), np.sum(shank * thigh, axis=-1))
    return flex * D


def inspect_model(text, side, ik_knee_raw_deg=None, q_grid_deg=Q_GRID_DEG):
    """What the model's knee definition is, from the model text alone (metres, degrees, millimetres as named).

    Keys: knee parent location (femur frame), orientation of the parent frame (Euler degrees) and its rotation about the
    flexion axis (fixed flexion offset when non-zero), child location (tibia frame; the pass uses this point as the knee centre),
    hip and ankle locations, the flexion axis in the femur frame and its tilt from lateral, the translation functions (kinds,
    values over the q grid, range) and whether the knee is coupled (any non-constant translation), the model-only LocoHub knee
    curve over the grid and its difference to -q, the neutral (q = 0) value, and the value at the authors' static IK q.
    Keys starting with '_' are internal arrays for model_knee_flexion and are dropped from the JSON."""
    from contributor_tools import gt21_rb_pass as rb
    markers, joints = rb.parse_osim(text)
    s = side
    knee_name = f'knee_{s}' if f'knee_{s}' in joints else f'walker_knee_{s}'      # generic Rajagopal names the joint walker_knee
    knee, hip, ankle = joints[knee_name], joints[f'hip_{s}'], joints[f'ankle_{s}']
    flex = [ax for c, ax in knee['axes'] if c == f'knee_angle_{s}']
    if not flex:
        raise KeyError(f'{knee_name} has no rotation axis for knee_angle_{s}')
    # a generic Rajagopal knee has three rotations driven by knee_angle (the first is flexion, the others small coupled
    # rotations): flexion uses the first and the count is recorded; the model-only curve ignores the coupled rotations
    axis_parent = flex[0] / np.linalg.norm(flex[0])
    Rpo = rb.euler_xyz_body_fixed(knee['parent_orientation'])
    axis_femur = Rpo @ axis_parent
    vee = 0.5 * np.array([Rpo[2, 1] - Rpo[1, 2], Rpo[0, 2] - Rpo[2, 0], Rpo[1, 0] - Rpo[0, 1]])
    about_axis = math.atan2(float(vee @ axis_parent), 0.5 * (np.trace(Rpo) - 1.0)) * D
    q = np.radians(np.asarray(q_grid_deg, float))
    tr = eval_translations(knee['translations'], q) * 1000.0
    kinds = sorted({spec[0] for _, _, spec in knee['translations']})
    finite = np.isfinite(tr).all(axis=1)
    info = {'side': s, 'knee_joint_name': knee_name, 'knee_rotations_driven_by_knee_angle': len(flex), 'knee_parent_location_m': [float(v) for v in knee['parent_location']],
            'knee_parent_orientation_deg': [float(v) * D for v in knee['parent_orientation']],
            'knee_parent_rotation_about_flexion_axis_deg': about_axis,
            'knee_child_location_m': [float(v) for v in knee['child_location']],
            'knee_child_location_norm_mm': float(np.linalg.norm(knee['child_location']) * 1000.0),
            'hip_child_location_m': [float(v) for v in hip['child_location']],
            'ankle_in_tibia_m': [float(v) for v in ankle['parent_location']],
            'knee_axis_in_femur': [float(v) for v in axis_femur],
            'knee_axis_tilt_from_lateral_deg': float(math.acos(min(1.0, abs(float(axis_femur[2])))) * D),
            'translation_function_kinds': kinds, 'knee_coupled': bool([k for k in kinds if k != 'constant']),
            'q_grid_deg': list(q_grid_deg), 'translation_mm_over_q': tr.tolist(),
            'translation_range_mm': [float(np.ptp(tr[finite, k])) if finite.any() else float('nan') for k in range(3)],
            '_parent_orientation': knee['parent_orientation'], '_axis_parent': axis_parent, '_translations': knee['translations'],
            '_knee_parent_location': knee['parent_location'], '_hip_child_location': hip['child_location'],
            '_ankle_in_tibia': ankle['parent_location'], '_knee_child_location': knee['child_location']}
    f = model_knee_flexion(info, q)
    info['model_lh_knee_deg_over_q'] = [float(v) for v in f]
    info['model_lh_knee_minus_negq_deg_over_q'] = [float(v) for v in (f + q * D)]
    i0 = list(q_grid_deg).index(0.0)
    info['neutral_lh_knee_deg'] = float(f[i0])
    ok = np.isfinite(f) & (np.asarray(q_grid_deg) <= 0)
    info['flexion_sign_check_slope'] = float(np.polyfit(-q[ok] * D, f[ok], 1)[0]) if ok.sum() >= 3 else float('nan')   # about +1
    if ik_knee_raw_deg is not None and np.isfinite(ik_knee_raw_deg):
        qi = math.radians(ik_knee_raw_deg)
        fi = float(model_knee_flexion(info, [qi])[0])
        info.update(ik_knee_raw_deg=float(ik_knee_raw_deg), model_lh_knee_at_ik_deg=fi,
                    model_offset_at_ik_deg=fi - (-float(ik_knee_raw_deg)))
    return info


def public(info):
    return {k: v for k, v in info.items() if not k.startswith('_')}


def compare_models(scaled, generic):
    """Differences scaled minus generic in the knee definition (millimetres and degrees)."""
    return {'knee_parent_location_diff_mm': [float((a - b) * 1000.0) for a, b in zip(scaled['knee_parent_location_m'], generic['knee_parent_location_m'])],
            'knee_child_location_norm_diff_mm': scaled['knee_child_location_norm_mm'] - generic['knee_child_location_norm_mm'],
            'neutral_lh_knee_diff_deg': scaled['neutral_lh_knee_deg'] - generic['neutral_lh_knee_deg'],
            'axis_tilt_diff_deg': scaled['knee_axis_tilt_from_lateral_deg'] - generic['knee_axis_tilt_from_lateral_deg'],
            'translation_range_diff_mm': [a - b for a, b in zip(scaled['translation_range_mm'], generic['translation_range_mm'])]}


# ------------------------------------------------------------------------------------------------ per person
def read_a3(a3_root):
    """({subject: row}, reference means) from the A3 outputs; empty when absent (the sheet then shows not checked)."""
    p, c = Path(a3_root) / 'per_participant.csv', Path(a3_root) / 'comparison.json'
    rows, ref = {}, {}
    if p.is_file():
        with open(p, newline='') as f:
            for r in csv.DictReader(f):
                row = {}
                for k, v in r.items():
                    try:
                        row[k] = float(v)
                    except (TypeError, ValueError):
                        row[k] = v
                rows[r['subject']] = row
    if c.is_file():
        ref = json.loads(c.read_text()).get('reference_means_deg', {}).get('mean_of_both', {})
    return rows, ref


def load_model_text(subject):
    from contributor_tools import analyze_gt21_static_pose as a3
    root = a3.find_model_root(subject)
    return (root / subject / 'osimxml' / f'{subject}.osim').read_text()


def static_summaries(static_root, subject, geo, args):
    """Per-trial summary dicts (both legs combined) for the participant's static trials, plus the excluded list."""
    from contributor_tools import analyze_gt21_static_pose as a3
    trials, excluded = [], []
    rows, _ = a3.static_trials(static_root, subject)
    for tr in rows:
        try:
            if not tr['markers']['read_ok']:
                raise ValueError('static markers table unreadable')
            markers, _ = a3.table_data(static_root, subject, tr['markers'])
            res, route = leg_results(markers, geo, args.knee_width_m, args.ankle_width_m, args.lateral)
            d = combine([summarise_leg(res[leg]) for leg in res])
            d['route'] = route
            trials.append(d)
        except Exception as exc:
            excluded.append(f"{tr['session']}/{tr['recording']}: {type(exc).__name__}: {exc}"[:300])
    return trials, excluded


def flat_row(subject, static, walk, a3row, ref, inspect_row):
    """One per-participant CSV row from the static trial summaries, the walking stride summaries and the A3 row."""
    row = {'subject': subject, 'n_static_trials': len(static), 'static_routes': ';'.join(sorted({t['route'] for t in static})),
           'n_walk_strides': len(walk), 'walk_recordings': ';'.join(sorted({w['recording'] for w in walk}))}
    for label, items in (('static', static), ('walk', walk)):
        agg = combine(items) if items else {}
        for v in VARIANTS:
            for q in ANGLES:
                row[f'{label}_{v}_{q}'] = agg.get(f'ang_{v}_{q}', float('nan'))
        for k in OFFSETS:
            row[f'{label}_off_{k}'] = agg.get(f'off_{k}', float('nan'))
        for q in ANGLES:
            row[f'{label}_delta_{q}'] = row[f'{label}_model_{q}'] - row[f'{label}_both_marker_{q}']
        row[f'{label}_delta_knee_only_knee'] = row[f'{label}_model_knee'] - row[f'{label}_knee_marker_knee']
        sens = [agg.get(f'sens_knee_{i}', float('nan')) for i in range(len(WIDTH_GRID_M))]
        row[f'{label}_width_sensitivity_knee_deg'] = (max(sens) - min(sens)) if all(np.isfinite(sens)) else float('nan')
        tl, sl = agg.get('off_thigh_len_mm'), agg.get('off_shank_len_mm')
        row[f'{label}_thigh_len_mm'], row[f'{label}_shank_len_mm'] = tl if tl is not None else float('nan'), sl if sl is not None else float('nan')
        row[f'{label}_knee_deg_per_10mm_ap'] = (10.0 * deg_per_mm_ap(tl / 1000.0, sl / 1000.0)) if tl and sl and np.isfinite(tl) and np.isfinite(sl) else float('nan')
    # the package's own mid-stance walking means and the references (A3), so the gap before and after can be formed
    for q in ('thigh', 'shank', 'knee', 'ankle'):
        mid = a3row.get(f'mid_{q}', float('nan')) if a3row else float('nan')
        r = ref.get(q, float('nan'))
        row[f'a3_mid_{q}'] = mid
        row[f'gap_before_{q}'] = mid - r
        row[f'gap_after_{q}'] = mid - r - row[f'walk_delta_{q}']
    row['gap_after_knee_only'] = row['gap_before_knee'] - row['walk_delta_knee_only_knee']
    row['a3_lh_knee_static'] = a3row.get('lh_knee', float('nan')) if a3row else float('nan')
    row['a3_ik_knee_static'] = a3row.get('ik_knee', float('nan')) if a3row else float('nan')
    row['static_model_minus_a3_knee'] = row['static_model_knee'] - row['a3_lh_knee_static']
    for k in ('knee_child_location_norm_mm', 'knee_axis_tilt_from_lateral_deg', 'knee_parent_rotation_about_flexion_axis_deg',
              'neutral_lh_knee_deg', 'flexion_sign_check_slope', 'model_offset_at_ik_deg'):
        row[f'model_{k}'] = inspect_row.get(k, float('nan')) if inspect_row else float('nan')
    row['model_knee_coupled'] = bool(inspect_row['knee_coupled']) if inspect_row else ''
    row['model_translation_range_mm'] = ';'.join(f'{v:.2f}' for v in inspect_row['translation_range_mm']) if inspect_row else ''
    return row


def column_stats(rows, name):
    x = np.asarray([r[name] for r in rows], float)
    x = x[np.isfinite(x)]
    if not x.size:
        return {'n': 0}
    return {'n': int(x.size), 'mean': float(x.mean()), 'sd': float(x.std(ddof=1)) if x.size > 1 else 0.0,
            'min': float(x.min()), 'max': float(x.max())}


def summary_json(rows, ref, models, generic):
    from contributor_tools import analyze_gt21_static_pose as a3
    out = {'assumed_parameters': ASSUMED_PARAMETERS, 'window_percent': list(WINDOW), 'reference_means_deg': ref,
           'people': len(rows), 'offsets_mm': {}, 'static': {}, 'walking': {}, 'models': {}}
    for label in ('static', 'walk'):
        for k in OFFSETS:
            out['offsets_mm'][f'{label}_{k}'] = column_stats(rows, f'{label}_off_{k}')
    for q in ANGLES:
        out['static'][q] = {'model': column_stats(rows, f'static_model_{q}'), 'knee_marker': column_stats(rows, f'static_knee_marker_{q}'),
                            'both_marker': column_stats(rows, f'static_both_marker_{q}'), 'delta': column_stats(rows, f'static_delta_{q}')}
    sk = out['static']['knee']
    static_share = sk['delta']['mean'] / sk['model']['mean'] if sk['model'].get('n') and sk['model']['mean'] else float('nan')
    out['static_share_removed_knee'] = static_share
    out['static_corr_model_vs_marker_knee'] = a3.pearson([r['static_model_knee'] for r in rows if np.isfinite(r['static_model_knee']) and np.isfinite(r['static_both_marker_knee'])],
                                                         [r['static_both_marker_knee'] for r in rows if np.isfinite(r['static_model_knee']) and np.isfinite(r['static_both_marker_knee'])])
    for q in ('knee', 'thigh', 'shank', 'ankle'):
        if q in ref:
            out['walking'][q] = a3.compare([r[f'walk_delta_{q}'] for r in rows], [r[f'a3_mid_{q}'] for r in rows], ref[q])
    if 'knee' in out['walking']:
        out['walking_knee_only_route'] = a3.compare([r['walk_delta_knee_only_knee'] for r in rows], [r['a3_mid_knee'] for r in rows], ref['knee'])
    walk_share = out['walking']['knee']['share_of_gap_from_standing'] if 'knee' in out['walking'] else float('nan')
    out['walking_share_removed_knee'] = walk_share
    marker_static_knee = sk['both_marker'].get('mean', float('nan')) if sk['both_marker'].get('n') else float('nan')
    out['verdict'] = classify(static_share, walk_share, marker_static_knee)
    out['verdict_rules'] = ("geometry_biased: both shares >= 0.6 and marker-route standing knee <= 3 deg; posture_real: both shares <= 0.25 "
                            "or marker-route standing knee >= 5 deg; else mixed (own rules, for approval; not reference ranges)")
    ap = out['offsets_mm'].get('static_knee_ap', {})
    dpm = column_stats(rows, 'static_knee_deg_per_10mm_ap')
    if ap.get('n') and dpm.get('n') and sk['model'].get('n'):
        out['knee_ap_offset_needed_to_explain_standing_mm'] = sk['model']['mean'] / (dpm['mean'] / 10.0)
        out['knee_ap_offset_consistency_mean_over_sd'] = abs(ap['mean']) / ap['sd'] if ap['sd'] else float('nan')
    out['models'] = {'scaled': {k: column_stats(rows, f'model_{k}') for k in ('knee_child_location_norm_mm', 'knee_axis_tilt_from_lateral_deg',
                                                                              'knee_parent_rotation_about_flexion_axis_deg', 'neutral_lh_knee_deg',
                                                                              'flexion_sign_check_slope', 'model_offset_at_ik_deg')},
                     'knee_coupled_people': int(sum(1 for r in rows if r.get('model_knee_coupled') is True)),
                     'generic': generic}
    return out


def compute(args):
    from contributor_tools import analyze_gt21_static_pose as a3
    from contributor_tools import gt21_rb_pass as rb
    out = Path(args.out_root)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f'{out} is not empty; outputs go to a new root')
    out.mkdir(parents=True, exist_ok=True)
    static_root = Path(args.static_root)
    subjects = sorted(p.name for p in static_root.iterdir() if p.is_dir() and a3.AB.fullmatch(p.name))
    if args.subject:
        subjects = [s for s in subjects if s in args.subject]
    a3rows, ref = read_a3(args.a3_root)
    inventory = load_inventory()
    generic = {}
    for g in (args.generic_model or [str(p) for p in GENERIC_MODELS]):
        gp = Path(g)
        if gp.is_file():
            try:
                generic[gp.name] = {}
                for s in 'rl':
                    gi = public(inspect_model(gp.read_text(), s))
                    # comparable only if the model-only knee curve follows -q with slope about +1 (same sign and axis convention as
                    # the GT21 scaled models); the generic Rajagopal knee (flexion positive about a rotated x axis, splines for q 0 to
                    # 120 degrees, three coupled rotations) is not, and its neutral value must then be disregarded
                    gi['comparable'] = bool(np.isfinite(gi['flexion_sign_check_slope']) and abs(gi['flexion_sign_check_slope'] - 1.0) < 0.1)
                    generic[gp.name][s] = gi
            except Exception as exc:
                generic[gp.name] = {'error': f'{type(exc).__name__}: {exc}'[:300]}
    rows, per_model, skipped, excluded = [], {}, {}, {}
    for subject in subjects:
        text = load_model_text(subject)
        geo = {s: rb.model_geometry(text, s) for s in 'rl'}
        ik_raw = a3rows.get(subject, {}).get('ik_knee_raw', float('nan'))
        info = {s: inspect_model(text, s, ik_raw) for s in 'rl'}
        inspect_row = {k: nanmean_of([info[s].get(k) for s in 'rl']) for k in
                       ('knee_child_location_norm_mm', 'knee_axis_tilt_from_lateral_deg', 'knee_parent_rotation_about_flexion_axis_deg',
                        'neutral_lh_knee_deg', 'flexion_sign_check_slope', 'model_offset_at_ik_deg')}
        inspect_row['knee_coupled'] = any(info[s]['knee_coupled'] for s in 'rl')
        inspect_row['translation_range_mm'] = [nanmean_of([info[s]['translation_range_mm'][k] for s in 'rl']) for k in range(3)]
        per_model[subject] = {s: public(info[s]) for s in 'rl'}
        if generic:
            per_model[subject]['vs_generic'] = {g: {s: compare_models(info[s], v[s]) for s in 'rl'} for g, v in generic.items() if 'error' not in v and all(v[s]['comparable'] for s in 'rl')}
        static, excluded[subject] = static_summaries(static_root, subject, geo, args)
        rng = random.Random(args.seed * 1000 + int(subject[2:]))
        walk, skipped[subject] = walking_summaries(subject, inventory.get(subject, []), geo, args, rng)
        rows.append(flat_row(subject, static, walk, a3rows.get(subject), ref, inspect_row))
    with open(out / 'per_participant.csv', 'x', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ['subject'])
        w.writeheader()
        w.writerows(rows)
    summary = summary_json(rows, ref, per_model, generic)
    summary['seed'] = args.seed
    summary['sampling'] = {'recordings_per_person': args.recordings_per_person, 'strides_per_leg': args.strides_per_leg,
                           'lateral_direction': args.lateral}
    summary['a3_inputs_found'] = bool(a3rows) and bool(ref)
    with open(out / 'comparison.json', 'x') as f:
        json.dump(summary, f, indent=2, allow_nan=True)
        f.write('\n')
    with open(out / 'model_inspection.json', 'x') as f:
        json.dump(per_model, f, indent=2, allow_nan=True)
        f.write('\n')
    import resource
    run = {'status': 'run_done_unreviewed', 'scientific_approval': False, 'participants': len(rows),
           'excluded_static_trials': {k: v for k, v in excluded.items() if v}, 'skipped_walking': {k: v for k, v in skipped.items() if v},
           'peak_rss_mib': round(max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                                     resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) / 1024, 1)}
    with open(out / 'run_summary.json', 'x') as f:
        json.dump(run, f, indent=2)
        f.write('\n')
    return 0


# ------------------------------------------------------------------------------------------------ the review sheet
def read_rows(path):
    with open(path, newline='') as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k, v in r.items():
            if k not in ('subject', 'static_routes', 'walk_recordings', 'model_translation_range_mm'):
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
    out = Path(args.sheet_dir)
    out.mkdir(parents=True, exist_ok=True)
    INK, ORANGE, BLUE = '#20252B', '#eb6834', '#2a78d6'
    plt.rcParams.update({'font.size': 10, 'axes.titlesize': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                         'text.color': INK, 'axes.labelcolor': INK, 'axes.edgecolor': INK, 'legend.frameon': False})

    def fin(*cols):
        return [r for r in rows if all(np.isfinite(r[c]) for c in cols)]

    # 1. where the model's knee centre sits against the marker-only estimate (thigh frame)
    fig, ax = plt.subplots(figsize=(4.5, 3.8))
    for label, color, name in (('standing', ORANGE, 'static'), ('walking', BLUE, 'walk')):
        pts = fin(f'{name}_off_knee_ap', f'{name}_off_knee_pd')
        ax.scatter([r[f'{name}_off_knee_ap'] for r in pts], [r[f'{name}_off_knee_pd'] for r in pts], color=color, s=22, label=label, zorder=3)
    ax.axhline(0, color='#aab2ba', lw=0.8)
    ax.axvline(0, color='#aab2ba', lw=0.8)
    ax.set_xlabel('Model centre in front of marker estimate (mm)')
    ax.set_ylabel('Model centre below it (mm)')
    ax.legend(loc='best', fontsize=10)
    fig.text(0.97, 0.01, 'crossing: model equals marker estimate', ha='right', fontsize=10, color='#5b6672')
    fig.subplots_adjust(left=0.17, right=0.97, top=0.97, bottom=0.2)
    fig.savefig(out / 'knee_centre_offset.png', dpi=160)
    plt.close(fig)
    # 2. standing knee, model route against marker route
    fig, ax = plt.subplots(figsize=(4.5, 3.8))
    pts = fin('static_model_knee', 'static_both_marker_knee')
    x, y = [r['static_model_knee'] for r in pts], [r['static_both_marker_knee'] for r in pts]
    ax.scatter(x, y, color=ORANGE, s=22, zorder=3)
    if pts:
        lo, hi = min(min(x), min(y), 0) - 1, max(max(x), max(y), 1) + 1
        ax.plot([lo, hi], [lo, hi], ls='--', color='#7a8591', lw=1)
        ax.set_xlim(lo, hi)
        ax.set_ylim(lo, hi)
    ax.axhline(1.0, color=BLUE, lw=1)
    ax.text(0.03, 0.9, 'blue: GT23 and UM21 stand at about 1 degree', transform=ax.transAxes, fontsize=10, color=BLUE)
    ax.set_xlabel('Standing knee, model centres (degrees)')
    ax.set_ylabel('Standing knee, marker centres (degrees)')
    fig.text(0.97, 0.01, 'dashed: the route makes no difference', ha='right', fontsize=10, color='#5b6672')
    fig.subplots_adjust(left=0.17, right=0.97, top=0.97, bottom=0.2)
    fig.savefig(out / 'standing_routes.png', dpi=160)
    plt.close(fig)
    # 3. walking gap before and after
    fig, ax = plt.subplots(figsize=(4.5, 3.8))
    qs = ('knee', 'thigh', 'shank')
    xs = np.arange(len(qs))

    def bar(prefix, offset, color, label):
        m = [np.nanmean([r[f'{prefix}_{q}'] for r in rows]) for q in qs]
        s = [np.nanstd([r[f'{prefix}_{q}'] for r in rows], ddof=1) for q in qs]
        ax.bar(xs + offset, m, 0.38, yerr=s, color=color, capsize=3, label=label)
    bar('gap_before', -0.2, ORANGE, 'as converted')
    bar('gap_after', 0.2, BLUE, 'marker centres')
    ax.axhline(0, color=INK, lw=0.6)
    ax.set_xticks(xs)
    ax.set_xticklabels(['Knee', 'Thigh', 'Shank'])
    ax.set_ylabel('GT21 minus GT23/UM21 (degrees)')
    ax.legend(loc='best', fontsize=10)
    fig.subplots_adjust(left=0.17, right=0.97, top=0.97, bottom=0.12)
    fig.savefig(out / 'walking_gap.png', dpi=160)
    plt.close(fig)

    sk, wk = comp['static']['knee'], comp['walking'].get('knee', {})
    stand_model, stand_delta = sk['model'].get('mean', float('nan')), sk['delta'].get('mean', float('nan'))
    headline = (f'Marker-based knee centres move standing knee {stand_delta:.1f} of {stand_model:.1f} degrees and the walking gap '
                f'{wk.get("mean_gap", float("nan")) - wk.get("mean_corrected_gap", float("nan")):.1f} of {wk.get("mean_gap", float("nan")):.1f}.')
    n = len(rows)
    sens = [r['static_width_sensitivity_knee_deg'] for r in rows if np.isfinite(r['static_width_sensitivity_knee_deg'])]
    chips = [
        ('pass' if n == 22 else 'unchecked', f'{n} of 22 people analysed'),
        ('pass' if all(abs(r['static_model_minus_a3_knee']) <= 0.5 for r in fin('static_model_minus_a3_knee')) and fin('static_model_minus_a3_knee')
         else 'unchecked', 'standing knee on model centres matches sheet A3 within 0.5 degrees'),
        ('unchecked', 'joint widths assumed, not measured'),
        ('pass' if sens and max(sens) <= 0.5 else 'unchecked', f'width choice moves knee at most {max(sens) if sens else float("nan"):.1f} degrees'),
        ('unchecked', 'lateral direction from pelvis, not a measured axis' if comp['sampling']['lateral_direction'] == 'pelvis' else 'lateral direction from model axis'),
        ('pass' if all(r['n_walk_strides'] >= 4 for r in rows) else 'unchecked', 'at least 4 walking strides per person'),
        ('pass' if comp['models']['knee_coupled_people'] in (0, n) else 'unchecked',
         f'knee translation coupled to flexion in {comp["models"]["knee_coupled_people"]} of {n} models'),
        ('pass' if any('error' not in v and all(v[s]['comparable'] for s in 'rl') for v in comp['models']['generic'].values()) else 'unchecked',
         'generic model compared' if any('error' not in v and all(v[s]['comparable'] for s in 'rl') for v in comp['models']['generic'].values()) else 'generic model not comparable'),
    ]
    details = [
        f'Reading (own rule, not a reference range): {comp["verdict"]}. {comp["verdict_rules"]}',
        f'Assumed widths (not in the data): knee {comp["assumed_parameters"]["knee_width_m"]*1000:.0f} mm, ankle {comp["assumed_parameters"]["ankle_width_m"]*1000:.0f} mm; sensitivity grid in the module note.',
        'Offsets are model centre minus marker estimate: anterior and distal positive, in the thigh frame (knee) and shank frame (ankle). Ankle offsets and the knee offset in the shank frame are in per_participant.csv.',
        'Walking: seeded recordings and strides, 20-35 percent of stride; "as converted" is the package mid-stance mean from sheet A3 minus the mean of the GT23 and UM21 person means; "marker centres" subtracts the route change measured on the sampled strides.',
        'Model inspection (knee joint location, fixed rotation, coupled translations, generic comparison) is in model_inspection.json and comparison.json.',
    ] + [f'{r["subject"]}: standing knee {r["static_model_knee"]:.1f} model, {r["static_both_marker_knee"]:.1f} marker; knee offset anterior {r["static_off_knee_ap"]:.1f}, '
         f'distal {r["static_off_knee_pd"]:.1f} mm; walking route change {r["walk_delta_knee"]:.1f} degrees over {int(r["n_walk_strides"])} strides' for r in rows] + \
        [f'Source: {src}. Builder: contributor_tools/analyze_gt21_knee_centre.py']
    page(out / 'index.html', title='GT21 knee centre placement', ask='Is the GT21 knee centre biased?', headline=headline, chips=chips,
         figures=[(['knee_centre_offset.png'], 'Where does the model put the knee centre?', 'One dot per person.',
                   'Model knee centre against the marker estimate, forward and downward offset, one dot per person'),
                  (['standing_routes.png'], 'Does the standing knee change with marker centres?', 'Dots: people; line: no change.',
                   'Standing knee on marker centres against model centres, one dot per person'),
                  (['walking_gap.png'], 'Does the walking gap shrink?', 'Bars: mean over people.',
                   'Mean walking gap for knee, thigh and shank, as converted and with marker centres')],
         not_shown=['Hip centre placement', 'Measured joint widths', 'Tasks other than level walking'],
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
    c.add_argument('--a3-root', default=str(A3_ROOT))
    c.add_argument('--subject', action='append', help='limit to these participants (pilot)')
    c.add_argument('--seed', type=int, default=20261127)
    c.add_argument('--recordings-per-person', type=int, default=2)
    c.add_argument('--strides-per-leg', type=int, default=4)
    c.add_argument('--knee-width-m', type=float, default=KNEE_WIDTH_M)
    c.add_argument('--ankle-width-m', type=float, default=ANKLE_WIDTH_M)
    c.add_argument('--lateral', choices=('pelvis', 'model_axis'), default='pelvis')
    c.add_argument('--generic-model', action='append', help='generic .osim to inspect (default: the two Gait120 Rajagopal files if present)')
    s = sub.add_parser('sheet')
    s.add_argument('--out-root', required=True)
    s.add_argument('--sheet-dir', default=str(SHEET_DIR))
    s.add_argument('--render', action='store_true')
    args = p.parse_args(argv)
    return {'compute': compute, 'sheet': sheet}[args.cmd](args)


if __name__ == '__main__':
    raise SystemExit(main())
