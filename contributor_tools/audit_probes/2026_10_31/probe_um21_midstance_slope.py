"""UM21 treadmill walking-surface slope from midstance (read-only probe, AGENTS.md exception).

Question (José): use midstance to get the true ground slope of each UMich 2021
treadmill recording, and decide which slope the motion shared by AB01 i5 and AB01
i10 was recorded on.

Reads one recording at a time from Streaming.mat (h5py, read only) in the UM21-T01
scope order and writes one JSON report to a path that must not exist. Nothing under
converted_datasets/ or source folders is written.

Frames. Markers are in the global (lab) frame (README: "global coordinates", m).
Up = lab +z; this is checked per recording (pelvis markers above heel markers).
Forward = horizontal direction of the median heel->toe vector at midstance in that
recording; its sign is checked against the belt direction (the stance foot moves
backwards with the belt). Forceplates are in the local plate frame (README:
"directions follow the local force plate frame"; x side, y propulsive/braking,
z normal).

Strides. Consecutive same-side heel strikes h0 < h1 (100 Hz frames, 1-based) with
70 <= h1 - h0 <= 200 frames (0.7-2.0 s). Every heel and toe sample from 10 % to
50 % of the stride (and its neighbours, for velocities) must be finite, not
(0,0,0) and have visibility flag != 0.

Midstance frames. Foot flat on the belt means heel and toe move together with the
belt, so their velocities are equal. Primary marker estimates use the frames from
10 % to 50 % of the stride where |v_heel - v_toe| <= 0.05 m/s (central differences),
at least 3 such frames per stride (strides without them are counted and skipped).
The fixed 25-35 % window is also reported (suffix _25_35); in several participants
the foot still rotates in that window (|v_heel - v_toe| 0.1-0.2 m/s), which biases it.

Estimates per stride, in degrees, positive = uphill in the walking direction:
1. foot_pitch (José's method): pitch of the heel->toe vector,
   atan2(dz, d . forward), median over the midstance frames, minus the same
   participant's and leg's level-walking (i0) median, which removes heel/toe marker
   height differences. A vector lying in the belt plane has this pitch equal to the
   slope whatever the toe-out angle.
2. belt_path (no offset needed): direction of travel of the flat foot, which the
   belt carries along its surface. Mean of the heel and toe central-difference
   velocities v; pitch = atan2(-v_z, -(v . forward)); frames with belt speed
   -(v . forward) < 0.4 m/s are not used.
3. plate_force (independent of markers): mean total ground reaction force on the
   body (left + right plates, sign set so the normal component is positive) over
   the whole stride h0..h1 (1000 Hz samples (h0-1)*10 .. (h1-1)*10 - 1), in the
   plate frame. In steady walking the mean GRF points opposite gravity, so its
   tilt from the plate normal is the plate (belt) slope:
   atan2(s * mean F_y, mean F_z). The sign s of plate +y relative to the walking
   direction is taken from the stance pattern: the ipsilateral plate's body-force
   y is lower in early stance (0-15 %, braking) than in late stance (40-55 %,
   propulsion); s = sign(median late - median early) over strides. This holds only
   if the plates carry the whole body weight, so the stride-mean GRF magnitude is
   reported in body weights (ParticipantDetails Bodymass, g = 9.81).

Tolerance (fixed before the AB01 i5/i10 values were looked at; see --blind):
residual r = recording median - labelled slope, over recordings that are not i0
(i0 is zero by construction for foot_pitch) and not AB01 i5/i10. Per method,
tol = max(1.0, ceil_to_0.5(|median r| + 4 * 1.4826 * MAD(r))) degrees. A recording
is flagged when |r| > tol. A method separates 5 from 10 degrees only if tol < 2.5.

--blind withholds every AB01 i5/i10 value from stdout and from the report (used
while the method and the tolerance rule were settled); the final report is made
without --blind and must reproduce the blind-run tolerances (--blind-report).
Development log (all blind): run 1 used only the fixed 25-35 % window; the foot-flat
gate and the plate body-weight check were added after runs 1-2, on the other 48
recordings only. The tolerance rule was not changed between runs.
"""
import os
for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'ARROW_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'
import argparse
import hashlib
import json
import math
from pathlib import Path
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
SCOPE = ROOT / 'docs/quality/audits/um21-t01-tread-release-scope.json'
CENSUS = ROOT / 'docs/quality/audits/um21-t02-clock-census.json'
README = ROOT / 'contributor_tools/conversion_scripts/Umich_2021/R01 Dataset README.pdf'
LABELS = {'d10': -10.0, 'd5': -5.0, 'i0': 0.0, 'i5': 5.0, 'i10': 10.0}
WITHHELD = {('AB01', 'i5'), ('AB01', 'i10')}
STRIDE_FRAMES = (70, 200)
WINDOW = (0.25, 0.35)
SEARCH = (0.10, 0.50)
FLAT_DV_MAX = 0.05
MIN_FLAT_FRAMES = 3
G = 9.81
MIN_BELT_SPEED = 0.4
EARLY, LATE = (0.0, 0.15), (0.40, 0.55)
METHODS = ('foot_pitch', 'belt_path', 'plate_force', 'foot_pitch_25_35', 'belt_path_25_35')


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            h.update(chunk)
    return h.hexdigest()


def rss_mib():
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)


def summary(values):
    import numpy as np
    v = np.asarray([x for x in values if x is not None and math.isfinite(x)], dtype=float)
    if v.size == 0:
        return {'n': 0, 'median': None, 'q25': None, 'q75': None}
    q25, med, q75 = np.percentile(v, [25, 50, 75])
    return {'n': int(v.size), 'median': round(float(med), 3), 'q25': round(float(q25), 3), 'q75': round(float(q75), 3)}


def marker(trial, name):
    import numpy as np
    arr = trial[f'markers/{name}'][...].astype(float)
    xyz = arr[:3]
    ok = np.isfinite(xyz).all(axis=0) & ~np.all(xyz == 0.0, axis=0)
    if arr.shape[0] == 4:
        ok &= arr[3] != 0
    return xyz, ok


def body_mass(handle, subject):
    refs = handle[f'Streaming/{subject}/ParticipantDetails'][...]
    for j in range(refs.shape[1]):
        name = handle[refs[0, j]]
        if name.attrs.get('MATLAB_class') == b'char' and ''.join(chr(int(c)) for c in name[...].reshape(-1)) == 'Bodymass':
            return float(handle[refs[1, j]][...].reshape(-1)[0])
    return None


def recording(handle, subject, condition):
    import numpy as np
    trial = handle[f'Streaming/{subject}/Tread/{condition}']
    events = trial['events']
    hs = {'L': events['LHS'][...].reshape(-1).astype(int), 'R': events['RHS'][...].reshape(-1).astype(int)}
    feet = {s: {m: marker(trial, s + m) for m in ('HEE', 'TOE')} for s in 'LR'}
    pelvis = [marker(trial, n) for n in ('LASI', 'RASI')]
    pelvis_z = np.nanmedian(np.concatenate([xyz[2][ok] for xyz, ok in pelvis]))
    del pelvis
    heel_z = np.nanmedian(np.concatenate([feet[s]['HEE'][0][2][feet[s]['HEE'][1]] for s in 'LR']))
    frames = feet['L']['HEE'][0].shape[1]

    # Stride windows (0-based frame indices): the fixed 25-35 % window and the 10-50 % search range.
    windows = {s: [] for s in 'LR'}
    for s in 'LR':
        ok = feet[s]['HEE'][1] & feet[s]['TOE'][1]
        for h0, h1 in zip(hs[s][:-1], hs[s][1:]):
            d = h1 - h0
            if not STRIDE_FRAMES[0] <= d <= STRIDE_FRAMES[1]:
                continue
            a, b = h0 + round(WINDOW[0] * d) - 1, h0 + round(WINDOW[1] * d) - 1
            sa, sb = h0 + round(SEARCH[0] * d) - 1, h0 + round(SEARCH[1] * d) - 1
            if sa - 1 < 0 or sb + 1 >= frames or not ok[sa - 1:sb + 2].all():
                continue
            windows[s].append((int(h0), int(h1), a, b, sa, sb))

    # Forward axis: median horizontal heel->toe direction in the fixed window, both legs.
    vecs = np.concatenate([(feet[s]['TOE'][0] - feet[s]['HEE'][0])[:, a:b + 1].T
                           for s in 'LR' for _, _, a, b, _, _ in windows[s]])
    fwd = np.median(vecs[:, :2], axis=0)
    fwd = fwd / np.linalg.norm(fwd)

    def pitch_of(heel, toe, i, j):
        dv = toe[:, i:j + 1] - heel[:, i:j + 1]
        return np.degrees(np.arctan2(dv[2], fwd @ dv[:2]))

    def velocities(heel, toe, i, j):
        vh = 50.0 * (heel[:, i + 1:j + 2] - heel[:, i - 1:j])
        vt = 50.0 * (toe[:, i + 1:j + 2] - toe[:, i - 1:j])
        return vh, vt

    def path_of(v):
        back = -(fwd @ v[:2])
        keep = back >= MIN_BELT_SPEED
        return (float(np.median(np.degrees(np.arctan2(-v[2][keep], back[keep])))) if keep.any() else None), float(np.median(back))

    per_leg = {}
    belt_dir_agree = []
    for s in 'LR':
        heel, toe = feet[s]['HEE'][0], feet[s]['TOE'][0]
        out = {'foot_pitch_raw': [], 'belt_path': [], 'foot_pitch_25_35_raw': [], 'belt_path_25_35': [],
               'gated_frames': [], 'strides_without_flat_frames': 0}
        for _, _, a, b, sa, sb in windows[s]:
            out['foot_pitch_25_35_raw'].append(float(np.median(pitch_of(heel, toe, a, b))))
            vh, vt = velocities(heel, toe, a, b)
            path, back = path_of((vh + vt) / 2.0)
            out['belt_path_25_35'].append(path)
            belt_dir_agree.append(back > 0)
            vh, vt = velocities(heel, toe, sa, sb)
            flat = np.linalg.norm(vh - vt, axis=0) <= FLAT_DV_MAX
            if flat.sum() < MIN_FLAT_FRAMES:
                out['strides_without_flat_frames'] += 1
                continue
            out['gated_frames'].append(int(flat.sum()))
            out['foot_pitch_raw'].append(float(np.median(pitch_of(heel, toe, sa, sb)[flat])))
            out['belt_path'].append(path_of(((vh + vt) / 2.0)[:, flat])[0])
        per_leg[s] = out

    # Plates: total body GRF in the plate frame, per stride.
    plates = {s: trial[f'forceplates/{s}Force'][...].astype(float) for s in 'LR'}
    total = plates['L'] + plates['R']
    finite_total = np.isfinite(total).all(axis=0)
    normal_sign = -1.0 if np.nanmedian(total[2]) < 0 else 1.0
    body = normal_sign * total
    early_late = []
    plate = {s: [] for s in 'LR'}
    for s in 'LR':
        ipsi = normal_sign * plates[s][1]
        for h0, h1 in zip(hs[s][:-1], hs[s][1:]):
            d = h1 - h0
            if not STRIDE_FRAMES[0] <= d <= STRIDE_FRAMES[1]:
                continue
            p0, p1 = (h0 - 1) * 10, (h1 - 1) * 10
            if p0 < 0 or p1 > total.shape[1] or not finite_total[p0:p1].all():
                continue
            m = body[:, p0:p1].mean(axis=1)
            plate[s].append((float(m[1]), float(m[2]), float(m[0])))
            e = ipsi[p0 + int(EARLY[0] * d * 10):p0 + int(EARLY[1] * d * 10)]
            late = ipsi[p0 + int(LATE[0] * d * 10):p0 + int(LATE[1] * d * 10)]
            if e.size and late.size and np.isfinite(e).all() and np.isfinite(late).all():
                early_late.append(float(np.median(late) - np.median(e)))
    y_sign = 1.0 if np.median(early_late) > 0 else -1.0
    for s in 'LR':
        per_leg[s]['plate_force'] = [math.degrees(math.atan2(y_sign * y, z)) for y, z, _ in plate[s]]
        per_leg[s]['plate_lateral'] = [math.degrees(math.atan2(x, z)) for _, z, x in plate[s]]
        per_leg[s]['plate_magnitude'] = [math.sqrt(x * x + y * y + z * z) for y, z, x in plate[s]]
    del plates, total, body
    return {'subject': subject, 'condition': condition, 'label_deg': LABELS[condition],
            'checks': {'up_is_lab_z': bool(pelvis_z > heel_z), 'pelvis_minus_heel_z_m': round(float(pelvis_z - heel_z), 3),
                       'forward_xy': [round(float(c), 4) for c in fwd],
                       'stance_foot_moves_backward_fraction': round(float(np.mean(belt_dir_agree)), 3),
                       'plate_normal_sign': normal_sign, 'plate_y_forward_sign': y_sign,
                       'plate_early_late_strides': len(early_late)},
            'body_mass_kg': body_mass(handle, subject),
            'per_leg': per_leg, 'peak_rss_mib_after': rss_mib()}


def tolerance(residuals):
    import numpy as np
    r = np.asarray(residuals, dtype=float)
    med = float(np.median(r))
    spread = 1.4826 * float(np.median(np.abs(r - med)))
    raw = abs(med) + 4.0 * spread
    return {'n': int(r.size), 'median_residual_deg': round(med, 3), 'robust_sd_deg': round(spread, 3),
            'tol_deg': max(1.0, math.ceil(raw * 2.0) / 2.0),
            'separates_5_from_10': max(1.0, math.ceil(raw * 2.0) / 2.0) < 2.5}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--source', type=Path, default=ROOT / 'contributor_tools/conversion_scripts/Umich_2021/Streaming.mat')
    parser.add_argument('--output', type=Path, required=True, help='new JSON file')
    parser.add_argument('--blind', action='store_true', help='withhold AB01 i5/i10 values')
    parser.add_argument('--blind-report', type=Path, help='blind-run report whose tolerances the final run must equal')
    parser.add_argument('--max-rss-mib', type=float, default=300.0)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('output exists; refusing to overwrite')
    want = 768 * 1024**2
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (want if hard == resource.RLIM_INFINITY else min(want, hard), hard))
    os.nice(max(0, 19 - os.nice(0)))
    import numpy as np
    import h5py
    started = time.time()
    scope = json.loads(SCOPE.read_text())
    plan = [(r['subject'], r['condition']) for r in scope['records']]
    stat = args.source.stat()
    raw = []
    with h5py.File(args.source, 'r', rdcc_nbytes=1024**2) as handle:
        for subject, condition in plan:
            r = recording(handle, subject, condition)
            raw.append(r)
            if r['peak_rss_mib_after'] > args.max_rss_mib:
                raise SystemExit(f'peak RSS above {args.max_rss_mib} MiB; stopped')
    if (args.source.stat().st_size, args.source.stat().st_mtime_ns) != (stat.st_size, stat.st_mtime_ns):
        raise SystemExit('source changed during the probe')

    # Level-walking offsets per participant and leg.
    offsets = {}
    for r in raw:
        if r['condition'] == 'i0':
            for s in 'LR':
                for key in ('foot_pitch_raw', 'foot_pitch_25_35_raw'):
                    offsets[(r['subject'], s, key)] = float(np.median(r['per_leg'][s][key]))
    rows = []
    for r in raw:
        legs = {}
        pooled = {m: [] for m in METHODS}
        for s in 'LR':
            leg = r['per_leg'][s]
            off = {k: offsets[(r['subject'], s, k)] for k in ('foot_pitch_raw', 'foot_pitch_25_35_raw')}
            vals = {'foot_pitch': [p - off['foot_pitch_raw'] for p in leg['foot_pitch_raw']],
                    'foot_pitch_25_35': [p - off['foot_pitch_25_35_raw'] for p in leg['foot_pitch_25_35_raw']],
                    'belt_path': leg['belt_path'], 'belt_path_25_35': leg['belt_path_25_35'],
                    'plate_force': leg['plate_force']}
            legs['left' if s == 'L' else 'right'] = {
                **{m: summary(vals[m]) for m in METHODS},
                'foot_pitch_raw': summary(leg['foot_pitch_raw']),
                'level_offset_deg': {k: round(v, 3) for k, v in off.items()},
                'flat_frames_per_stride': summary(leg['gated_frames']),
                'strides_without_flat_frames': leg['strides_without_flat_frames'],
                'plate_lateral_tilt': summary(leg['plate_lateral']),
                'plate_grf_magnitude_raw_units': summary(leg['plate_magnitude']),
                'plate_grf_magnitude_body_weights': summary([f / (r['body_mass_kg'] * G) for f in leg['plate_magnitude']]
                                                            if r['body_mass_kg'] else [])}
            for m in METHODS:
                pooled[m] += [v for v in vals[m] if v is not None]
        rows.append({'record': f"{r['subject']}/{r['condition']}", 'subject': r['subject'], 'condition': r['condition'],
                     'label_deg': r['label_deg'], 'body_mass_kg': r['body_mass_kg'], **{m: summary(pooled[m]) for m in METHODS},
                     'per_leg': legs, 'checks': r['checks'], 'peak_rss_mib_after': r['peak_rss_mib_after']})

    tolerances = {}
    for m in METHODS:
        reference = [row[m]['median'] - row['label_deg'] for row in rows
                     if row['condition'] != 'i0' and (row['subject'], row['condition']) not in WITHHELD
                     and row[m]['median'] is not None]
        tolerances[m] = tolerance(reference)
    for row in rows:
        row['residual_deg'] = {m: None if row[m]['median'] is None else round(row[m]['median'] - row['label_deg'], 3)
                               for m in METHODS}
        row['flagged'] = {m: (row['residual_deg'][m] is not None and abs(row['residual_deg'][m]) > tolerances[m]['tol_deg'])
                          for m in METHODS}
        row['nearest_label_deg'] = {m: None if row[m]['median'] is None else
                                    min(LABELS.values(), key=lambda lab: abs(lab - row[m]['median'])) for m in METHODS}

    blind_check = None
    if args.blind_report:
        blind = json.loads(args.blind_report.read_text())
        blind_check = {'path': str(args.blind_report.resolve().relative_to(ROOT)), 'sha256': sha256_file(args.blind_report),
                       'generated_utc': blind['generated_utc'], 'probe_sha256': blind['probe']['sha256'],
                       'blind_tolerances': blind['tolerances'], 'tolerances_equal': blind['tolerances'] == tolerances}
        if blind['probe']['sha256'] != sha256_file(Path(__file__)):
            raise SystemExit('blind run used different probe code')
        if not blind_check['tolerances_equal']:
            raise SystemExit('final tolerances differ from the blind run')
    if args.blind:
        for row in rows:
            if (row['subject'], row['condition']) in WITHHELD:
                for key in list(row):
                    if key not in ('record', 'subject', 'condition', 'label_deg'):
                        row[key] = 'withheld (blind run)'

    def flags(m):
        return [row['record'] for row in rows if isinstance(row.get('flagged'), dict) and row['flagged'][m]]
    report = {
        'task_id': 'UM21-SLOPE', 'part': 'walking-surface slope from midstance, all 50 treadmill recordings',
        'status': 'probe_complete_unreviewed', 'scientific_approval': False, 'blind_run': bool(args.blind),
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'probe': {'path': str(Path(__file__).resolve().relative_to(ROOT)), 'sha256': sha256_file(Path(__file__))},
        'inputs': {'scope': {'path': str(SCOPE.relative_to(ROOT)), 'sha256': sha256_file(SCOPE)},
                   'census': {'path': str(CENSUS.relative_to(ROOT)), 'sha256': sha256_file(CENSUS)},
                   'readme_pdf': {'path': str(README.relative_to(ROOT)), 'sha256': sha256_file(README)},
                   'source': {'path': str(args.source.resolve().relative_to(ROOT)), 'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns,
                              'sha256_recorded': scope['source']['streaming_sha256_recorded'],
                              'sha256_note': 'Recorded by earlier receipts; size and mtime re-checked before and after, bytes not rehashed.'}},
        'method': {'frames': 'markers lab frame, up = +z (checked per recording), forward = median midstance heel->toe horizontal direction; plates in the local plate frame',
                   'stride_frames': list(STRIDE_FRAMES), 'midstance_window_fraction': list(WINDOW),
                   'min_belt_speed_m_s': MIN_BELT_SPEED, 'plate_early_late_fraction': [list(EARLY), list(LATE)],
                   'sign': 'positive = uphill in the walking direction',
                   'midstance_frames': 'frames in 10-50 % of the stride with |v_heel - v_toe| <= 0.05 m/s (foot flat on the belt), >= 3 per stride; _25_35 variants use the fixed 25-35 % window',
                   'search_window_fraction': list(SEARCH), 'flat_dv_max_m_s': FLAT_DV_MAX, 'min_flat_frames': MIN_FLAT_FRAMES,
                   'foot_pitch': 'heel->toe pitch at midstance minus the same participant and leg level-walking (i0) median',
                   'belt_path': 'pitch of the flat foot path (mean heel/toe velocity) at midstance; no offset',
                   'plate_units_note': 'stride-mean |GRF| equals body mass x g, so forceplate force is in N, not the README N/kg',
                   'plate_force': 'tilt of the stride-mean total GRF from the plate normal; plate +y sign from braking/propulsion order'},
        'tolerance_rule': 'Per method: residual r = recording median - label over recordings that are not i0 and not AB01 i5/i10; '
                          'tol = max(1.0, ceil_to_0.5(|median r| + 4 * 1.4826 * MAD(r))) deg; flag when |r| > tol. '
                          'Fixed in code and computed in a blind run before the AB01 i5/i10 values were looked at.',
        'tolerances': tolerances, 'blind_check': blind_check,
        'flags': {m: flags(m) for m in METHODS},
        'records': rows,
        'resources': {'peak_rss_mib': rss_mib(), 'wall_seconds': round(time.time() - started, 1),
                      'rlimit_as_bytes': list(resource.getrlimit(resource.RLIMIT_AS)), 'nice': os.nice(0)}}
    text = json.dumps(report, indent=1, allow_nan=False) + '\n'
    with open(args.output, 'x') as stream:
        stream.write(text)
    print(json.dumps({'tolerances': tolerances, 'flags': report['flags'], 'peak_rss_mib': report['resources']['peak_rss_mib'],
                      'wall_s': report['resources']['wall_seconds']}, indent=1))


if __name__ == '__main__':
    main()
