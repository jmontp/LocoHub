"""GT21-C01: force, COP and joint reference conventions, evidence report and review sheets.

Reads small publisher text sources (README, processing scripts, subject models),
the current GT21 adapter source, prior audit receipts, and a seeded random sample
of source recordings (two per mode). Source tables are read one at a time with
the restricted numeric MAT reader (64 MiB file cap, MemAvailable checked first).
Writes docs/quality/audits/gt21-c01-conventions.json, review_sheets/GT21-C01/
and review_sheets/D-GT21-C01-1/. Launches nothing; changes no inputs.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import sys
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.common.review_sheet import page
from contributor_tools.gt21_numeric_source import read_numeric_table

SEED = 20261027
MODES = ('treadmill', 'levelground', 'ramp', 'stair')
PER_MODE = 2
CONTACT_N = 100.0  # publisher Osim.correlateForcePlates contact threshold (N)
MIN_FREE_KIB = 1024 * 1024  # refuse a source read below 1 GiB MemAvailable
GT = ROOT / 'contributor_tools/conversion_scripts/Gtech_2021'
SRC = GT / 'CAMARGO_ET_AL_J_BIOMECH_DATASET'
SCRIPTS = SRC / 'scripts (1)'
REPORT = ROOT / 'docs/quality/audits/gt21-c01-conventions.json'
SHEETS = ROOT / 'review_sheets'
INK, MUTED = '#20252B', '#5b6672'
HEADING = {'faces lab -Z': '#2a78d6', 'faces lab +Z': '#1baf7a', 'walks along lab ±X': '#eb6834',
           'no pelvis markers': '#d5d9de'}

PUBLISHER_SOURCES = {
    'readme': SRC / 'README.txt',
    'run_osim': SCRIPTS / 'RUN_OSIM.m',
    'ramp_id': SCRIPTS / 'lib/RampID.m',
    'transform_forceplates': SCRIPTS / 'lib/TransformForceplates.m',
    'correlate_force_plates': SCRIPTS / 'MoCapTools/+Osim/correlateForcePlates.m',
    'create_external_loads': SCRIPTS / 'MoCapTools/+Osim/createExternalLoads.m',
    'c3d_to_mot': SCRIPTS / 'MoCapTools/+Vicon/C3DtoMOT.m',
    'c3d_to_trc': SCRIPTS / 'MoCapTools/+Vicon/C3DtoTRC.m',
    'vicon_transform': SCRIPTS / 'MoCapTools/+Vicon/transform.m',
}
ADAPTER_SOURCES = [GT / 'convert_gtech_2021_phase_to_parquet.m'] + [
    GT / 'utilities' / name for name in ('gtech_compute_grf_cop_stride.m', 'gtech_forward_source_z_sign.m',
                                         'gtech_select_force_plate.m')]
PRIOR_AUDITS = [ROOT / 'docs/quality/audits' / name for name in (
    'gt21-force-geometry.json', 'gt21-measured-force-direction.json', 'gt21-completed-force-readback.json',
    'gt21-all-source-phases.json', 'gt21-participant-source-coverage.json', 'gt21-ab17-recovery.json',
    'queue-recovery-expanded-49-summary.json', 'gt21-plate-assignment-fix.json', 'gt21-force-fix.json',
    'gt21-ab17-native-metadata-reuse.json')]

# Source-processing statements; each line reference was read from the hashed file.
SOURCE_STATEMENTS = [
    ('c3d_to_mot', '3-4', 'Force-plate tables are declared to be in the OpenSim frame with Y up.'),
    ('c3d_to_mot', '98-100', 'F in N; M divided by 1000 to N m; COP P divided by 1000 to m.'),
    ('c3d_to_mot', '74, 83-85', 'COP uses zero top-cover thickness; plate origin Y is negated "for some reason" (publisher comment).'),
    ('c3d_to_mot', '24, 44-45, 58-78, 98', 'Only the local Fz/Mx/My used for COP are low-pass filtered (FilterFreq default 15 Hz, filtfilt); local COP is set to the plate origin (0) when local Fz > -10 N or nonfinite; exported F and M are the unfiltered btk global wrenches.'),
    ('c3d_to_mot', '127', 'All force, COP and moment triples pass through Vicon.transform(...,"OsimXYZ").'),
    ('vicon_transform', '19-21', 'Row-vector rotation: OpenSim (X, Y, Z) = Vicon (X, Z, -Y).'),
    ('c3d_to_trc', '19', 'Markers pass through the same OsimXYZ transform; TRC markers remain in mm.'),
    ('correlate_force_plates', '47, 53, 60-65', 'Markers divided by 1000 and compared with plate COP; contact is _vy > 100 N.'),
    ('create_external_loads', '38-41, 91-96', 'Plate _v and _p are applied to calcn_r/calcn_l, both expressed in ground; no torque identifier, so plate moments are not used by inverse dynamics.'),
    ('run_osim', '39-47', 'ID uses correlateForcePlates side assignment (RampID for ramps) and filters ID output.'),
    ('run_osim', '63-69', 'ik_offset = ik minus the mean static-trial IK, per coordinate.'),
    ('ramp_id', '16-20, 33-37', 'Ramp ID assumes the third plate may carry either foot and splits trials at idle midpoints.'),
    ('readme', '28, 36-37, 47-48', 'fp is ground reaction force of all plates at 1000 Hz; static and ik_offset (angles relative to the static pose) added 4/28/2024; no units or axis statement for fp.'),
]


def digest(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def rel(path):
    return str(Path(path).relative_to(ROOT))


def mem_available_kib():
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'):
            return int(line.split()[1])
    raise RuntimeError('MemAvailable not reported')


def load(path):
    free = mem_available_kib()
    if free < MIN_FREE_KIB:
        raise MemoryError(f'MemAvailable {free} KiB below admission')
    return read_numeric_table(path)


def style():
    plt.rcParams.update({'font.size': 10.5, 'axes.titlesize': 11, 'axes.spines.top': False,
                         'axes.spines.right': False, 'text.color': INK, 'axes.labelcolor': INK,
                         'axes.edgecolor': INK, 'xtick.color': INK, 'ytick.color': INK,
                         'axes.linewidth': 0.6, 'legend.frameon': False})


def model_axes():
    """Sagittal/pelvis joint axes from every local subject model (XML text only)."""
    names = ('ground_pelvis', 'hip_r', 'hip_l', 'knee_r', 'knee_l', 'ankle_r', 'ankle_l', 'back')
    models, signatures = {}, set()
    for path in sorted(SRC.glob('AB*/osimxml/*.osim')):
        root = ET.parse(path).getroot()
        gravity = root.findtext('.//gravity').split()
        joints = {}
        for joint in root.iter('CustomJoint'):
            if joint.get('name') in names:
                spatial = joint.find('SpatialTransform')
                joints[joint.get('name')] = [((axis.findtext('coordinates') or '').strip(),
                                              [round(float(v), 6) for v in axis.findtext('axis').split()])
                                             for axis in spatial if axis.get('name').startswith('rotation')]
        ranges = {c.get('name'): [round(float(v), 4) for v in c.findtext('range').split()]
                  for c in root.iter('Coordinate') if c.get('name') in ('knee_angle_r', 'knee_angle_l')}
        offsets = sorted({f.findtext('orientation').strip() for f in root.iter('PhysicalOffsetFrame')
                          if f.get('name') in ('ground_offset', 'pelvis_offset')})
        signature = json.dumps([[float(v) for v in gravity], joints, ranges, offsets], sort_keys=True)
        signatures.add(signature)
        models[rel(path)] = digest(path)
    example = json.loads(next(iter(signatures)))
    return {'models_sha256': models, 'identical_axis_definitions': len(signatures) == 1,
            'gravity': example[0], 'rotation_axes': example[1], 'knee_ranges_rad': example[2],
            'ground_and_pelvis_offset_orientations': example[3]}


def inventory():
    found = {mode: [] for mode in MODES}
    for subject in sorted(p for p in SRC.glob('AB*') if p.is_dir()):
        for date in sorted(p for p in subject.iterdir() if p.is_dir() and p.name != 'osimxml'):
            for mode in MODES:
                fp_dir = date / mode / 'fp'
                if not fp_dir.is_dir():
                    continue
                for path in sorted(fp_dir.glob('*.mat')):
                    if all((date / mode / channel / path.name).is_file() for channel in ('markers', 'gcRight', 'ik')):
                        found[mode].append((subject.name, date.name, mode, path.name))
    return found


def pelvis_vectors(markers):
    fwd = np.stack([(markers[f'L_ASIS_{a}'] + markers[f'R_ASIS_{a}'] - markers[f'L_PSIS_{a}'] - markers[f'R_PSIS_{a}']) / 2
                    for a in 'xyz'], 1)
    lr = np.stack([markers[f'R_ASIS_{a}'] - markers[f'L_ASIS_{a}'] for a in 'xyz'], 1)
    with np.errstate(invalid='ignore', divide='ignore'):
        return fwd / np.linalg.norm(fwd, axis=1, keepdims=True), lr / np.linalg.norm(lr, axis=1, keepdims=True)


def heading_class(fwd):
    x, z = fwd[:, 0], fwd[:, 2]
    labels = np.full(len(fwd), 'no pelvis markers', dtype=object)
    finite = np.isfinite(x) & np.isfinite(z)
    labels[finite & (np.abs(z) > np.abs(x)) & (z < 0)] = 'faces lab -Z'
    labels[finite & (np.abs(z) > np.abs(x)) & (z > 0)] = 'faces lab +Z'
    labels[finite & (np.abs(x) >= np.abs(z))] = 'walks along lab ±X'
    return labels


def quantiles(values, q=(5, 50, 95), digits=4):
    values = np.asarray(values, float)
    values = values[np.isfinite(values)]
    return [round(float(v), digits) for v in np.percentile(values, q)] if values.size else None




def rotation(axis, degrees):
    """Stack of right-handed rotation matrices about a coordinate axis."""
    v = np.radians(degrees)
    c, s, o, z = np.cos(v), np.sin(v), np.ones_like(v), np.zeros_like(v)
    rows = {'x': [[o, z, z], [z, c, -s], [z, s, c]], 'y': [[c, z, s], [z, o, z], [-s, z, c]],
            'z': [[c, -s, z], [s, c, z], [z, z, o]]}[axis]
    return np.moveaxis(np.array(rows), [0, 1], [-2, -1])


def model_pelvis(tilt, list_, rot):
    # ground_pelvis: rotation1 pelvis_tilt about Z, rotation2 pelvis_list about X, rotation3 pelvis_rotation about Y.
    # Tested here as successive (intrinsic) rotations: R = Rz(tilt) Rx(list) Ry(rotation).
    return rotation('z', tilt) @ rotation('x', list_) @ rotation('y', rot)


def decompose_zxy(R):
    """Inverse of model_pelvis: (tilt, list, rotation) in degrees."""
    return (np.degrees(np.arctan2(-R[:, 0, 1], R[:, 1, 1])), np.degrees(np.arcsin(np.clip(R[:, 2, 1], -1, 1))),
            np.degrees(np.arctan2(-R[:, 2, 0], R[:, 2, 2])))


def sagittal_heading_first(R):
    """Pelvis forward/backward tilt after removing heading: R = Ry(h) Rz(theta) Rx(phi); anterior tilt = -theta."""
    return -np.degrees(np.arcsin(np.clip(R[:, 1, 0], -1, 1)))


def marker_pelvis(markers):
    """Pelvis frame from markers: x = mean ASIS - mean PSIS, z = R_ASIS - L_ASIS orthogonalized, y = z cross x."""
    x, z = pelvis_vectors(markers)
    with np.errstate(invalid='ignore'):
        z = z - np.sum(z * x, 1, keepdims=True) * x
        z = z / np.linalg.norm(z, axis=1, keepdims=True)
    return np.stack([x, np.cross(z, x), z], 2)


def recording_facts(key):
    subject, date, mode, name = key
    base = SRC / subject / date / mode
    markers = load(base / 'markers' / name)
    clock = markers['Header']
    fwd, lr = pelvis_vectors(markers)
    feet = {side: np.stack([(markers[f'{side}_Heel_{a}'] + markers[f'{side}_Toe_Tip_{a}']) / 2000 for a in 'xyz'], 1)
            for side in 'LR'}
    up = np.array([0.0, 1.0, 0.0])
    handed = np.einsum('ij,ij->i', np.cross(fwd, up), lr)
    labels = heading_class(fwd)
    del markers
    fp = load(base / 'fp' / name)
    plates, cop_near, cop_camera = [], [], []
    fp_clock = fp['Header']
    for column in [c for c in fp if c.endswith('_vy')]:
        prefix = column[:-3]
        vy = fp[column]
        on_markers = np.interp(clock, fp_clock, vy, left=np.nan, right=np.nan) > CONTACT_N
        cop = np.stack([np.interp(clock, fp_clock, fp[f'{prefix}_p{a}'], left=np.nan, right=np.nan) for a in 'xyz'], 1)
        # Made-up contrast: the same COP read back in the unrotated camera axes (Vicon X, Y, Z = X, -Z, Y).
        camera = np.stack([cop[:, 0], -cop[:, 2], cop[:, 1]], 1)
        distance = {side: np.linalg.norm(cop - feet[side], axis=1) for side in 'LR'}
        camera_distance = np.minimum(*(np.linalg.norm(camera - feet[side], axis=1) for side in 'LR'))
        usable = on_markers & np.isfinite(distance['L']) & np.isfinite(distance['R'])
        near = np.minimum(distance['L'], distance['R'])[usable]
        far = np.maximum(distance['L'], distance['R'])[usable]
        cop_near.append(near)
        cop_camera.append(camera_distance[usable])
        contact_fp = vy > CONTACT_N
        moment = np.linalg.norm(np.stack([fp[f'{prefix}_moment_{a}'] for a in 'xyz'], 1)[contact_fp], axis=1)
        plates.append({
            'plate': prefix, 'contact_samples_fp_clock': int(contact_fp.sum()),
            'samples_below_minus_100N': int((vy < -CONTACT_N).sum()),
            'contact_samples_marker_clock': int(on_markers.sum()),
            'cop_y_m_quantiles_05_50_95': quantiles(fp[f'{prefix}_py'][contact_fp]),
            'cop_to_nearer_foot_m_quantiles': quantiles(near),
            'cop_to_other_foot_m_quantiles': quantiles(far),
            'cop_in_camera_axes_to_nearer_foot_m_quantiles': quantiles(camera_distance[usable]),
            'left_foot_nearer_fraction': round(float(np.mean(distance['L'][usable] < distance['R'][usable])), 4) if usable.any() else None,
            'heading_during_contact': {k: int(np.sum(labels[on_markers] == k)) for k in HEADING},
            'moment_magnitude_Nm_quantiles': quantiles(moment, digits=1),
        })
    del fp
    z_dominant = np.isin(labels, ['faces lab -Z', 'faces lab +Z'])
    deviation = np.degrees(np.arctan2(np.abs(fwd[:, 0]), np.abs(fwd[:, 2])))[z_dominant]
    return {
        'recording': f'{subject}/{date}/{mode}/{name}',
        'sha256': {channel: digest(base / channel / name) for channel in ('fp', 'markers')},
        'marker_samples': int(len(clock)),
        'right_handed_fraction': round(float(np.mean(handed[np.isfinite(handed)] > 0)), 4),
        'heading_all_samples': {k: int(np.sum(labels == k)) for k in HEADING},
        'z_dominant_heading_deviation_deg_quantiles_50_95_100': quantiles(deviation, (50, 95, 100), 2),
        'plates': plates,
    }, np.concatenate(cop_near), np.concatenate(cop_camera)


def stride_means(signals, phase, reference):
    """Right heel-strike strides (120-600 samples at 200 Hz), each centred. Returns stride-mean curves,
    stride count and the median within-stride correlation of each signal with the reference."""
    starts = np.where(np.diff(phase) < -50)[0] + 1
    curves = {k: [] for k in signals}
    within = {k: [] for k in signals}
    for a, b in zip(starts[:-1], starts[1:]):
        if not 120 <= b - a <= 600 or not all(np.isfinite(v[a:b]).all() for v in signals.values()):
            continue
        for k, v in signals.items():
            s = np.interp(np.linspace(0, 1, 101), np.linspace(0, 1, b - a), v[a:b])
            curves[k].append(s - s.mean())
        for k in signals:
            within[k].append(np.corrcoef(curves[k][-1], curves[reference][-1])[0, 1])
    count = len(curves[reference])
    if not count:
        return None, 0, {}
    return ({k: np.mean(v, 0) for k, v in curves.items()}, count,
            {k: round(float(np.nanmedian(v)), 3) for k, v in within.items() if k != reference})


def pelvis_check(key):
    """Does a marker pelvis frame, decomposed in the model's Z-X-Y order, reproduce the source IK pelvis angles?

    One constant rotation between the marker frame and the model pelvis frame is fitted (orthogonal
    Procrustes, 3 parameters); it cannot create time-varying agreement or choose a sign.
    """
    subject, date, mode, name = key
    base = SRC / subject / date / mode
    markers = load(base / 'markers' / name)
    clock = markers['Header']
    marker_frame = marker_pelvis(markers)
    del markers
    ik = load(base / 'ik' / name)
    source = {c: np.interp(clock, ik['Header'], ik[f'pelvis_{c}']) for c in ('tilt', 'list', 'rotation')}
    del ik
    source_frame = model_pelvis(source['tilt'], source['list'], source['rotation'])
    good = np.isfinite(marker_frame).all((1, 2))
    u, _, vt = np.linalg.svd(np.einsum('nji,njk->ik', marker_frame[good], source_frame[good]))
    offset = u @ vt
    fitted = marker_frame @ offset
    tilt, list_, rot = decompose_zxy(fitted)
    out = {'recording': f'{subject}/{date}/{mode}/{name}', 'samples': int(good.sum()),
           'marker_to_model_offset_deg': round(float(np.degrees(np.arccos(np.clip((np.trace(offset) - 1) / 2, -1, 1)))), 2),
           'pelvis_rotation_deg_quantiles_05_50_95': quantiles(source['rotation'], digits=1),
           'zxy_agreement': {}}
    for label, mine in (('tilt', tilt), ('list', list_), ('rotation', rot)):
        diff = np.degrees(np.angle(np.exp(1j * np.radians(mine - source[label]))))[good]
        entry = {'rms_deg': round(float(np.sqrt(np.mean((diff - np.median(diff)) ** 2))), 2)}
        if label != 'rotation':
            entry['r'] = round(float(np.corrcoef(mine[good], source[label][good])[0, 1]), 3)
        out['zxy_agreement'][label] = entry
    anatomical_source = sagittal_heading_first(source_frame)
    anatomical_marker = sagittal_heading_first(fitted)
    out['heading_removed_sagittal_tilt'] = {
        'source_vs_marker_r': round(float(np.corrcoef(anatomical_source[good], anatomical_marker[good])[0, 1]), 3),
        'source_vs_marker_rms_deg': round(float(np.std((anatomical_source - anatomical_marker)[good])), 2),
        'pelvis_tilt_vs_marker_r': round(float(np.corrcoef(source['tilt'][good], anatomical_marker[good])[0, 1]), 3)}
    gait = load(base / 'gcRight' / name)
    phase = np.interp(clock, gait['Header'], gait['HeelStrike'], left=np.nan, right=np.nan)
    del gait
    signals = {'marker tilt': anatomical_marker, 'pelvis_tilt': source['tilt'], '-pelvis_list': -source['list'],
               'heading-removed source tilt': anatomical_source}
    mean, strides, within = stride_means(signals, phase, 'marker tilt')
    out['stride_level'] = {'strides': strides}
    if strides:
        out['stride_level'].update({
            'stride_mean_r_with_marker_tilt': {k: round(float(np.corrcoef(mean[k], mean['marker tilt'])[0, 1]), 3)
                                               for k in signals if k != 'marker tilt'},
            'median_within_stride_r_with_marker_tilt': within,
            'stride_mean_peak_to_peak_deg': {k: round(float(np.ptp(v)), 2) for k, v in mean.items()},
            'heading_removed_vs_minus_list_sample_r': round(float(np.corrcoef(anatomical_source[good], -source['list'][good])[0, 1]), 3)})
    out['sha256'] = {c: digest(base / c / name) for c in ('markers', 'ik', 'gcRight')}
    return out, mean


def draw(found):
    rng = random.Random(SEED)
    picks, failures = {}, []
    for mode in MODES:
        order = rng.sample(found[mode], len(found[mode]))
        picks[mode] = []
        for key in order:
            if len(picks[mode]) == PER_MODE:
                break
            try:
                facts = recording_facts(key)
            except (ValueError, MemoryError) as error:
                failures.append({'recording': '/'.join(key), 'reason': str(error)})
                continue
            picks[mode].append((key, facts))
    return picks, failures


SHORT_MODE = {'treadmill': 'treadmill', 'levelground': 'level', 'ramp': 'ramp', 'stair': 'stair'}


def fig_heading(records, out):
    pooled = {}
    for record in records:
        mode = record['recording'].split('/')[2]
        for plate in record['plates']:
            label = f"{SHORT_MODE[mode]} {plate['plate'].replace('Treadmill_', 'belt ')}"
            counts = pooled.setdefault(label, {k: 0 for k in HEADING})
            for k, v in plate['heading_during_contact'].items():
                counts[k] += v
    rows = [(k, v) for k, v in pooled.items() if sum(v.values())]
    height = 0.32 * len(rows) + 1.9
    fig, ax = plt.subplots(figsize=(4.5, height))
    for i, (label, counts) in enumerate(rows):
        total = sum(counts.values())
        left = 0.0
        for name, color in HEADING.items():
            ax.barh(i, counts[name] / total, left=left, color=color, height=0.72)
            left += counts[name] / total
    ax.set_yticks(range(len(rows)), [r[0] for r in rows])
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.set_xlabel('share of contact samples')
    fig.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=c) for c in HEADING.values()], labels=list(HEADING),
               loc='lower center', ncol=2, fontsize=10)
    fig.tight_layout(rect=(0, 0.75 / height, 1, 1))
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return rows


def fig_cop(near, camera, out):
    fig, ax = plt.subplots(figsize=(4.5, 3.3))
    bins = np.linspace(0, 3, 61)
    ax.hist(np.clip(camera, 0, 3), bins=bins, color='#c9ced4', label='camera axes (made up)')
    ax.hist(near, bins=bins, color='#2a78d6', alpha=0.85, label='as published')
    ax.set_xlabel('COP to nearer foot (m)')
    ax.set_ylabel('contact samples')
    ax.legend(fontsize=10)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_pelvis(mean, label, out):
    fig, ax = plt.subplots(figsize=(4.5, 3.9))
    x = np.linspace(0, 100, 101)
    ax.plot(x, mean['marker tilt'], color=INK, lw=2.4, label='markers: tilt (forward +)')
    ax.plot(x, mean['pelvis_tilt'], color='#2a78d6', lw=2.0, label='pelvis_tilt (used now)')
    ax.plot(x, mean['heading-removed source tilt'], color='#eb6834', lw=2.0, ls='--', label='source tilt, heading removed')
    ax.set_title(label, fontsize=11)
    ax.set_xlabel('right-leg stride (%)')
    ax.set_ylabel('stride mean, centred (deg)')
    ax.legend(fontsize=10, loc='upper center', bbox_to_anchor=(0.5, -0.22), ncol=1)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_axes_panels(folder):
    """Made-up top views, one per PNG; axis relations come from the source transform and markers."""
    cases = [('faces -Z', HEADING['faces lab -Z'], (0, 1), 'outward'),
             ('faces +Z', HEADING['faces lab +Z'], (0, -1), 'inward'),
             ('faces +X', HEADING['walks along lab ±X'], (1, 0), 'forward'),
             ('faces -X', HEADING['walks along lab ±X'], (-1, 0), 'backward')]
    names = []
    for index, (title, color, (dx, dy), meaning) in enumerate(cases, 1):
        fig, ax = plt.subplots(figsize=(3.0, 3.3))
        ax.set_xlim(0, 6)
        ax.set_ylim(0, 6.6)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.add_patch(FancyArrowPatch((0.3, 6.1), (1.5, 6.1), arrowstyle='-|>', mutation_scale=12, color=MUTED))
        ax.add_patch(FancyArrowPatch((0.3, 6.1), (0.3, 4.9), arrowstyle='-|>', mutation_scale=12, color=MUTED))
        ax.text(1.6, 6.1, '+X', va='center', fontsize=10, color=MUTED)
        ax.text(0.45, 4.75, '+Z', va='top', fontsize=10, color=MUTED)
        cx, cy = 3.2, 3.2
        ax.add_patch(FancyArrowPatch((cx - 1.0 * dx, cy - 1.0 * dy), (cx + 1.2 * dx, cy + 1.2 * dy),
                                     arrowstyle='-|>', mutation_scale=18, color=color, lw=2.6))
        # Subject's right side: walking direction turned clockwise on the page (Y points out of the page).
        rx, ry = dy, -dx
        fx, fy = cx + 0.8 * rx, cy + 0.8 * ry
        ax.plot(fx, fy, 'o', ms=15, color=INK, mfc='white', mew=1.6)
        ax.text(fx, fy, 'R', ha='center', va='center', fontsize=10, fontweight='bold')
        ax.add_patch(FancyArrowPatch((fx + 0.25, fy), (fx + 1.3, fy), arrowstyle='-|>', mutation_scale=13,
                                     color='#c0392b', lw=2.0))
        ax.text(4.1, 5.6, title, ha='center', fontsize=11.5, color=color, fontweight='bold')
        ax.text(3.0, 0.3, f'red +X at right foot\n= {meaning}', ha='center', fontsize=10.5)
        name = f'fig1{"abcd"[index - 1]}_axes.png'
        fig.savefig(folder / name, dpi=150, bbox_inches='tight')
        plt.close(fig)
        names.append(name)
    return names


def channel_policy(axes):
    lab = 'publisher lab/ground frame: +Y up (model gravity -Y), +X and +Z horizontal, right-handed'
    return {
        'grf_vertical_{ipsi,contra}_BW': {
            'source': 'selected plate _vy / (mass * 9.81)', 'frame': lab,
            'sign': 'positive upward support on the body; publisher contact rule is _vy > 100 N and ID applies _v to calcn',
            'status': 'verified_lab_axis',
            'note': 'Gravity-aligned on ramps, not surface-normal. Exported force is the unfiltered btk global wrench. BW normalization inherits the unresolved SubjectInfo.Weight unit.'},
        'grf_anterior_{ipsi,contra}_BW': {
            'source': 'selected plate _vz times per-cycle pelvis-marker sign along lab Z',
            'sign': 'positive toward the measured walking direction along lab Z',
            'status': 'verified_lab_axis_with_measured_sign',
            'missing_when': 'pelvis markers missing, heading not Z-dominant, or sign changes within the cycle',
            'note': 'Lab Z component only; heading deviation within Z-dominant cycles is reported per recording, not rotated out.'},
        'grf_lateral_{ipsi,contra}_BW': {
            'source': 'selected plate _vx, unsigned by heading or leg', 'sign': 'lab +X',
            'status': 'anatomical_projection_unsupported',
            'note': "Lab +X is the right foot's outward side when facing -Z, inward when facing +Z, and forward or backward on X-direction plates. Pending D-GT21-C01-1."},
        'cop_anterior_{ipsi,contra}_m': {
            'source': '(plate _pz - lateral ankle marker z / 1000) times the anterior sign', 'origin': 'lateral ankle marker, not a joint centre',
            'status': 'verified_lab_axis_with_measured_sign',
            'missing_when': 'vertical force < 0.2 BW or anterior sign missing',
            'note': 'Source COP comes from 15 Hz (default) filtered local Fz/Mx/My and is set to the local plate origin, not NaN, when local Fz > -10 N; the adapter 0.2 BW mask removes those samples.'},
        'cop_lateral_{ipsi,contra}_m': {
            'source': 'plate _px - lateral ankle marker x / 1000', 'sign': 'lab +X', 'origin': 'lateral ankle marker',
            'status': 'anatomical_projection_unsupported', 'note': 'Same heading/leg ambiguity as grf_lateral. Pending D-GT21-C01-1.'},
        'cop_vertical_{ipsi,contra}_m': {
            'source': 'plate _py - lateral ankle marker y / 1000', 'sign': 'lab +Y (up)', 'origin': 'lateral ankle marker',
            'status': 'verified_lab_axis', 'note': 'Source _py is the plate surface height in the lab (0 on floor and treadmill, step/ramp heights elsewhere).'},
        'plate_moment_xyz': {
            'source': 'plate _moment_x/y/z', 'status': 'unresolved_not_exported',
            'note': 'Magnitudes of hundreds of N m on contact indicate a moment about a plate or lab point, not a free moment at the COP. Reference point and sign are not stated; publisher ID does not use them.'},
        'plate_assignment': {
            'treadmill': 'named Treadmill_R/Treadmill_L plates (publisher TransformForceplates uses heel geometry for all modes)',
            'overground': 'unique plate with > 2/3 COP-nearer heel/toe midpoint during > 100 N contact, else missing',
            'status': 'rule_follows_publisher_geometry_not_independent_contact_labels',
            'note': 'Levelground files include a virtual Combined plate (publisher combineForcePlates: vertical-force-weighted COP); not separated from its components.'},
        'joint_angles': {
            'source': 'ik_offset (= ik minus mean static IK; publisher RUN_OSIM.m 63-69), degrees', 'axes': axes['rotation_axes'],
            'sign': 'hip_flexion +flexion (about segment +Z); knee_angle +extension (range -120..10 deg), negated to flexion-positive by the adapter; ankle_angle +dorsiflexion about the oblique talocrural axis (about 12 deg from Z)',
            'status': 'model_axes_verified_zero_reference_open',
            'note': 'Zero is the static standing pose, not the model zero. Version-1 archives (AB17) lack ik_offset and static. Open question queued after the two current decisions.'},
        'joint_moments': {
            'source': 'OpenSim ID generalized forces divided by mass', 'sign': 'positive along the coordinate; knee negated by the adapter',
            'status': 'model_axes_verified', 'note': 'Publisher ID applied plate force at the COP in ground, no plate torque; filtered after ID.'},
        'pelvis_tilt_list_rotation': {
            'source': 'ik pelvis_tilt, pelvis_list, pelvis_rotation (degrees)',
            'composition': 'R_pelvis_in_ground = Rz(pelvis_tilt) Rx(pelvis_list) Ry(pelvis_rotation): model axes (0,0,1), (1,0,0), (0,1,0) applied as successive rotations; reproduced from markers in every sampled mode (see pelvis_check).',
            'status': 'verified_source_definition',
            'note': 'Subjects walk along lab Z, so pelvis_rotation is near +90 or -90 deg. pelvis_tilt is then a rotation about lab Z (mostly frontal obliquity) and pelvis_list carries forward/backward tilt with a sign that flips with walking direction.'},
        'pelvis_and_segment_sagittal_angles': {
            'source': 'adapter: pelvis_sagittal = pelvis_tilt; thigh = pelvis + hip_flexion; shank = thigh - knee flexion; foot = shank + ankle; trunk = pelvis + lumbar_extension',
            'status': 'unresolved_source_only',
            'note': 'pelvis_tilt is mostly obliquity, so the current mapping is wrong and all five segment angles are unsupported. No source-derived forward tilt (heading-removed IK tilt, equivalently -pelvis_list on -Z-facing treadmill) reproduces marker tilt at the stride level on treadmill; overground evidence is partial. Keep source pelvis_tilt/list/rotation under source names only. Pending D-GT21-C01-2.'},
    }


def main():
    style()
    started = datetime.now(timezone.utc).isoformat()
    for name in ('GT21-C01', 'D-GT21-C01-1'):
        (SHEETS / name).mkdir(parents=True, exist_ok=True)
    axes = model_axes()
    found = inventory()
    picks, failures = draw(found)
    records, near, camera = [], [], []
    for mode in MODES:
        for _, (facts, n, c) in picks[mode]:
            records.append(facts)
            near.append(n)
            camera.append(c)
    near, camera = np.concatenate(near), np.concatenate(camera)
    pelvis = [pelvis_check(key) for mode in MODES for key, _ in picks[mode]]
    pelvis_summary = [p for p, _ in pelvis]
    # Figure examples: one seeded random treadmill and one seeded random overground recording, stride means.
    example_rng = random.Random(SEED)
    examples = [example_rng.choice([i for i, (p, m) in enumerate(pelvis) if m is not None and ('/treadmill/' in p['recording']) == tread])
                for tread in (True, False)]

    contact_heading = {k: 0 for k in HEADING}
    plates_with_x = []
    for record in records:
        for plate in record['plates']:
            for k, v in plate['heading_during_contact'].items():
                contact_heading[k] += v
            if plate['heading_during_contact']['walks along lab ±X'] > 0.1 * max(plate['contact_samples_marker_clock'], 1):
                plates_with_x.append(f"{record['recording']}:{plate['plate']}")
    total_contact = sum(contact_heading.values())
    no_negative = all(p['samples_below_minus_100N'] == 0 for r in records for p in r['plates'])
    handed = min(r['right_handed_fraction'] for r in records)
    near_median, camera_median = float(np.median(near)), float(np.median(camera))
    rotation_rms = max(p['zxy_agreement']['rotation']['rms_deg'] for p in pelvis_summary)
    tilt_list_rms = max(max(p['zxy_agreement'][c]['rms_deg'] for c in ('tilt', 'list')) for p in pelvis_summary)
    current_r = [p['heading_removed_sagittal_tilt']['pelvis_tilt_vs_marker_r'] for p in pelvis_summary]
    removed_r = [p['heading_removed_sagittal_tilt']['source_vs_marker_r'] for p in pelvis_summary]
    both_directions = [r['recording'] for r in records if r['recording'].split('/')[2] in ('ramp', 'stair')
                       and min(r['heading_all_samples']['faces lab -Z'], r['heading_all_samples']['faces lab +Z']) > 0]

    rows = fig_heading(records, SHEETS / 'GT21-C01/fig1_heading.png')
    fig_cop(near, camera, SHEETS / 'GT21-C01/fig2_cop.png')
    pelvis_pngs = []
    for tag, index in zip(('a', 'b'), examples):
        recording = pelvis_summary[index]['recording'].split('/')
        fig_pelvis(pelvis[index][1], f'{SHORT_MODE[recording[2]]} {recording[0]}, {pelvis_summary[index]["stride_level"]["strides"]} strides',
                   SHEETS / f'GT21-C01/fig3{tag}_pelvis.png')
        pelvis_pngs.append(f'fig3{tag}_pelvis.png')
    stride_r = {mode: [p['stride_level']['stride_mean_r_with_marker_tilt']['heading-removed source tilt']
                       for p in pelvis_summary if p['recording'].split('/')[2] == mode] for mode in MODES}
    panels = fig_axes_panels(SHEETS / 'D-GT21-C01-1')

    report = {
        'task_id': 'GT21-C01', 'status': 'conventions_documented_unreviewed', 'scientific_approval': False,
        'generated_at_utc': started,
        'builder': {'path': rel(__file__), 'sha256': digest(__file__)},
        'resource_class': 'read_only; one thread; restricted MAT reader (64 MiB per file); MemAvailable >= 1 GiB before each read; no MATLAB/OpenSim',
        'inputs_sha256': {
            'publisher': {rel(p): digest(p) for p in PUBLISHER_SOURCES.values()},
            'adapter': {rel(p): digest(p) for p in ADAPTER_SOURCES},
            'prior_audits': {rel(p): digest(p) for p in PRIOR_AUDITS},
            'reader': {rel(ROOT / 'contributor_tools/gt21_numeric_source.py'): digest(ROOT / 'contributor_tools/gt21_numeric_source.py')},
        },
        'source_processing_statements': [{'file': rel(PUBLISHER_SOURCES[k]), 'lines': lines, 'statement': text}
                                         for k, lines, text in SOURCE_STATEMENTS],
        'source_processing_caveat': 'The toolbox converters (C3DtoMOT, C3DtoTRC, transform) are shipped with the data, but no producer log ties them to the published fp/markers files. Their stated frame is corroborated below by the data, not proven as the producer. The btk wrench force-sign convention is not stated in the scripts; force-on-body is supported by the publisher contact rule, the ID load application and the absence of samples below -100 N.',
        'model': axes,
        'random_sample': {'seed': SEED, 'per_mode': PER_MODE,
                          'inventory_counts': {m: len(v) for m, v in found.items()},
                          'drawn': [r['recording'] for r in records], 'reader_rejections': failures},
        'recordings': records,
        'pooled': {'contact_heading_samples': contact_heading,
                   'plates_with_over_10pct_x_direction_contact': plates_with_x,
                   'ramp_stair_recordings_with_both_z_directions': both_directions,
                   'no_plate_below_minus_100N': no_negative,
                   'min_right_handed_fraction': handed,
                   'cop_to_nearer_foot_median_m': round(near_median, 4),
                   'cop_in_camera_axes_to_nearer_foot_median_m': round(camera_median, 4)},
        'pelvis_check': {
            'recordings': pelvis_summary,
            'figure_examples': {'seed': SEED, 'recordings': [pelvis_summary[i]['recording'] for i in examples],
                                'kind': 'right-stride means (120-600 samples), each stride centred'},
            'heading_removed_stride_mean_r_by_mode': stride_r,
            'method': 'Marker pelvis frame (x = mean ASIS - mean PSIS, z = R_ASIS - L_ASIS orthogonalized). One constant marker-to-model rotation fitted per recording (orthogonal Procrustes against R = Rz(tilt) Rx(list) Ry(rotation) built from source IK), then decomposed in the same Z-X-Y order. Angle differences are wrapped and median-centred. Heading-removed tilt: R = Ry(h) Rz(theta) Rx(phi), forward tilt = -theta, for both source IK and markers.',
            'independent_prompt': 'Verifier (seed 58213) reported the same Z-X-Y reproduction on two treadmill recordings without the constant offset; re-derived here on this sample with the offset, across all four modes.',
            'interpretation': 'The source pelvis coordinates are successive Z-X-Y rotations of the model pelvis (reproduced within a few degrees in all modes). Because subjects face lab Z, pelvis_tilt is mostly frontal obliquity, so the adapter pelvis_sagittal_angle = pelvis_tilt is wrong. No source-derived forward tilt is validated at the stride level: on treadmill the heading-removed source tilt is nearly identical to -pelvis_list (sample r about 0.99) and neither reproduces the stride-mean marker tilt (r 0.07 and -0.25); overground stride-mean r is 0.30-0.81 from 8-13 strides of mixed ascent/descent per recording, with stride-mean amplitudes of 2-5 deg. Sample-level agreement is not sufficient. Pelvis and the four inherited segment angles stay source-only/unresolved; the treadmill disagreement is unexplained (marker noise, soft tissue or IK weighting not separated).'},
        'channel_policy': channel_policy(axes),
        'prior_audits_revalidated': {
            'gt21-force-geometry.json': 'AB06 treadmill: forward -Z, left-to-right +X agrees with this sample; anterior sign matched source_negative on all 228 legs because that recording faces -Z.',
            'gt21-measured-force-direction.json': 'Coordinate statement (anterior signed lab Z, lateral lab +X, vertical +Y, COP origin lateral ankle marker) matches the adapter source. Lateral is a lab axis, not anatomical.',
            'gt21-plate-assignment-fix.json': 'Assignment rule matches gtech_select_force_plate.m; Combined plate handling not covered.',
            'gt21-completed-force-readback.json': 'AB06 only; readback checks decoding and declared lab mapping, not anatomical frames.',
        },
        'unresolved': [
            'Anatomical sideways (lateral) force and COP sign (D-GT21-C01-1).',
            'Pelvis and segment sagittal angles: current pelvis_tilt mapping is wrong; no source-derived tilt validates at stride level on treadmill (D-GT21-C01-2). Unexplained treadmill marker/IK disagreement.',
            'Joint-angle zero reference: static-pose offset (ik_offset) versus model zero (ik); queued after the two current decisions.',
            'Anterior force/COP use lab Z only; Z-dominant cycles allow up to 45 deg heading.',
            'Plate moment reference point and sign; Combined virtual plate composition.',
            'COP reference: lateral ankle marker offset from the ankle joint centre is not quantified.',
            'Mass unit for BW normalization (SubjectInfo.Weight) is resolved elsewhere (GT21-A02/S01).',
        ],
    }
    REPORT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    share = lambda k: 100 * contact_heading[k] / total_contact
    chips = [('pass' if no_negative else 'fail', 'vertical force is upward support on every sampled plate'),
             ('pass' if handed > 0.95 else 'fail', 'lab X, Y up, Z is right-handed with the markers'),
             ('pass' if near_median < 0.2 < camera_median else 'fail', f'COP sits {near_median:.2f} m from a foot, in meters'),
             ('pass' if axes['identical_axis_definitions'] else 'fail', f'joint axes identical in all {len(axes["models_sha256"])} subject models'),
             ('fail' if plates_with_x else 'pass', f'lab X is the walking direction on {len(plates_with_x)} sampled plates'),
             ('pass' if rotation_rms < 3 and tilt_list_rms < 4 else 'fail', f'markers reproduce source pelvis angles within {tilt_list_rms:.1f}°'),
             ('fail' if max(np.abs(current_r)) < 0.5 else 'unchecked', 'current pelvis column does not follow marker tilt'),
             ('unchecked', 'why no source tilt matches markers on treadmill strides')]
    page(SHEETS / 'GT21-C01/index.html', title='Georgia Tech 2021 conventions check',
         ask='Look at 3 figures. Reply ok, or say what looks wrong.',
         headline='Georgia Tech 2021 forces and COP use a Y-up lab frame; sideways and pelvis columns are wrong',
         chips=chips,
         figures=[('fig1_heading.png', 'On which plates is lab X the walking direction?',
                   'Orange: the sideways column holds fore-aft force.',
                   'Stacked bars of walking heading during contact for each sampled plate'),
                  ('fig2_cop.png', 'Is the source COP in meters in the marker frame?',
                   'Grey: same COP in unrotated camera axes.',
                   'Histograms of COP distance to the nearer foot, as published and in camera axes'),
                  (pelvis_pngs, 'Does any source pelvis angle follow the marker tilt over a stride?',
                   'Stride means: random treadmill and overground recording.',
                   'Stride-mean marker forward tilt, source pelvis_tilt and heading-removed source tilt, treadmill and overground')],
         not_shown=['Joint moments', 'Unsampled participants', 'Plate moment reference point'],
         reply='ok  |  what looks wrong',
         details=[f'GT21-C01. Random sample seed {SEED}, {PER_MODE} recordings per mode: ' + ', '.join(r['recording'] for r in records),
                  'Contact samples by heading: ' + ', '.join(f'{k} {share(k):.1f}%' for k in HEADING),
                  f'Pelvis: rotation within {rotation_rms:.1f}° RMS; heading-removed source tilt vs marker tilt, stride-mean r by mode: '
                  + '; '.join(f'{m} ' + ', '.join(f'{v:.2f}' for v in rs) for m, rs in stride_r.items()),
                  f'Reader rejections: {len(failures)}',
                  'Report: docs/quality/audits/gt21-c01-conventions.json',
                  'Builder: contributor_tools/review_gt21_c01_conventions.py'])

    page(SHEETS / 'D-GT21-C01-1/index.html', title='Sideways force decision',
         ask='Choose how sideways force and COP are published for Georgia Tech 2021.',
         headline='The sideways columns hold lab +X, whose meaning changes with walking direction',
         chips=[('pass', 'lab X, Y up, Z frame confirmed from source scripts and markers'),
                ('pass' if both_directions else 'fail', 'both walking directions occur on ramp and stair plates')],
         figures=[(panels, 'What does lab +X mean for the right foot?',
                   'Made-up layouts; axis relations from the source.',
                   'Top views of four walking directions with the meaning of lab +X at the right foot')],
         decision={'question': 'How are sideways force and COP published?',
                   'columns': ['Left out', 'What changes', 'Adapter work', 'Reversible'],
                   # Neutral order: most sideways values published first; ties by less adapter work.
                   'rows': [('A · right +', ['X-direction and unclear cycles', 'lab X signed by measured heading', 'sign rule', 'yes']),
                            ('B · outward +', ['X-direction and unclear cycles', 'as A, left leg mirrored', 'sign rule and mirror', 'yes']),
                            ('C · lab axis', ['all sideways values', 'lab +X kept under a lab-axis name', 'rename columns', 'yes']),
                            ('defer', ['nothing yet', 'pilots run; sideways not releasable', '—', '—'])],
                   'footnote': 'Every option keeps measured lab values.',
                   'recommendation': 'C, medium confidence: the data spec does not yet define a sideways sign, so filling it for one dataset would set a cross-dataset convention by default. A or B can follow once the spec defines lateral.'},
         not_shown=["Other datasets' sideways conventions"],
         reply='D-GT21-C01-1: A, B, C or defer',
         details=['D-GT21-C01-1 (task GT21-C01). Report: docs/quality/audits/gt21-c01-conventions.json (channel_policy)',
                  'Builder: contributor_tools/review_gt21_c01_conventions.py'])

    print(json.dumps({'drawn': report['random_sample']['drawn'], 'rejections': failures, 'pooled': report['pooled'],
                      'pelvis': pelvis_summary, 'rows': len(rows)}, indent=1))


if __name__ == '__main__':
    main()
