"""GT23-E01 export rules (pure functions, no file access).

Turns the verified step outputs into LocoHub observations:

* C06 (angles, speeds, foot-frame pressure point, force in N, held columns), M01 (moments, powers and force in body
  weights after the mass rule) and S01 (strides, spans, dispositions) are the only value sources.
* Gait strides and window-rule spans become 150-sample phase observations (inclusive 0 to 100 percent). Every recording
  also becomes one continuous time observation; the 64 recordings without a defensible cycle are continuous only.
* Window-rule spans have no single leg, so each accepted span is exported once per reference leg (left and right),
  sharing its observation_id.
* Labels come from the authors' file name only where S01 matched an authors' window; every other observation is marked
  unknown. A speed or incline appears only when the authors' file label or the publisher README states it.
* Knee moment is the negative of the source ``knee_angle`` moment (flexion positive, standard); the power product is
  unchanged by that negation. Frontal and transverse columns keep the source sign.

Nothing here reads a file; the runner does the I/O.
"""
import json
import re

import numpy as np

N_PHASE = 150
G = 9.80665
PAPER = 'Georgia Tech 2023 data descriptor, doi 10.1038/s41597-023-02840-6, Table 1 (stair rise 152 mm)'

# (export template, source family, source template, sign, held key template or None)
#  {R} = role or side token in the export name ('ipsi'/'contra' or 'left'/'right'); {w} = 'left'/'right' in the C06
#  names; {s} = 'l'/'r' in the M01 names (the published joint column names).
LEG_SPECS = (
    ('thigh_sagittal_angle_{R}_rad', 'c06', 'thigh_sagittal_angle_{w}_rad', 1.0, 'thigh_sagittal_angle_{w}_rad'),
    ('shank_sagittal_angle_{R}_rad', 'c06', 'shank_sagittal_angle_{w}_rad', 1.0, 'shank_sagittal_angle_{w}_rad'),
    ('foot_sagittal_angle_{R}_rad', 'c06', 'foot_sagittal_angle_{w}_rad', 1.0, 'foot_sagittal_angle_{w}_rad'),
    ('hip_flexion_angle_{R}_rad', 'c06', 'hip_flexion_angle_{w}_rad', 1.0, 'hip_flexion_angle_{w}_rad'),
    ('knee_flexion_angle_{R}_rad', 'c06', 'knee_flexion_angle_{w}_rad', 1.0, 'knee_flexion_angle_{w}_rad'),
    ('ankle_dorsiflexion_angle_{R}_rad', 'c06', 'ankle_dorsiflexion_angle_{w}_rad', 1.0, 'ankle_dorsiflexion_angle_{w}_rad'),
    ('hip_flexion_velocity_{R}_rad_s', 'c06', 'hip_flexion_velocity_{w}_rad_s', 1.0, 'hip_flexion_velocity_{w}_rad_s'),
    ('knee_flexion_velocity_{R}_rad_s', 'c06', 'knee_flexion_velocity_{w}_rad_s', 1.0, 'knee_flexion_velocity_{w}_rad_s'),
    ('ankle_dorsiflexion_velocity_{R}_rad_s', 'c06', 'ankle_dorsiflexion_velocity_{w}_rad_s', 1.0, 'ankle_dorsiflexion_velocity_{w}_rad_s'),
    ('hip_flexion_moment_{R}_Nm_kg', 'm01', 'hip_flexion_{s}_moment_Nm_kg', 1.0, None),
    ('hip_adduction_moment_{R}_Nm_kg', 'm01', 'hip_adduction_{s}_moment_Nm_kg', 1.0, None),
    ('hip_rotation_moment_{R}_Nm_kg', 'm01', 'hip_rotation_{s}_moment_Nm_kg', 1.0, None),
    ('knee_flexion_moment_{R}_Nm_kg', 'm01', 'knee_angle_{s}_moment_Nm_kg', -1.0, None),
    ('ankle_dorsiflexion_moment_{R}_Nm_kg', 'm01', 'ankle_angle_{s}_moment_Nm_kg', 1.0, None),
    ('subtalar_angle_moment_{R}_Nm_kg', 'm01', 'subtalar_angle_{s}_moment_Nm_kg', 1.0, None),
    ('hip_flexion_power_{R}_W_kg', 'm01', 'hip_flexion_power_{s}_W_kg', 1.0, None),
    ('hip_adduction_power_{R}_W_kg', 'm01', 'hip_adduction_power_{s}_W_kg', 1.0, None),
    ('hip_rotation_power_{R}_W_kg', 'm01', 'hip_rotation_power_{s}_W_kg', 1.0, None),
    ('knee_flexion_power_{R}_W_kg', 'm01', 'knee_power_{s}_W_kg', 1.0, None),
    ('ankle_dorsiflexion_power_{R}_W_kg', 'm01', 'ankle_power_{s}_W_kg', 1.0, None),
    ('subtalar_angle_power_{R}_W_kg', 'm01', 'subtalar_power_{s}_W_kg', 1.0, None),
    ('grf_vertical_{R}_N', 'c06', 'grf_lab_y_{w}_N', 1.0, 'grf_lab_y_{w}_N'),
    ('grf_anterior_{R}_N', 'c06', 'grf_anterior_{w}_N', 1.0, 'grf_anterior_{w}_N'),
    ('grf_lateral_{R}_N', 'c06', 'grf_lateral_{w}_N', 1.0, 'grf_lateral_{w}_N'),
    ('grf_lab_x_{R}_N', 'c06', 'grf_lab_x_{w}_N', 1.0, 'grf_lab_x_{w}_N'),
    ('grf_lab_z_{R}_N', 'c06', 'grf_lab_z_{w}_N', 1.0, 'grf_lab_z_{w}_N'),
    ('grf_vertical_{R}_BW', 'm01', 'grf_lab_y_{w}_BW', 1.0, 'grf_lab_y_{w}_N'),
    ('grf_anterior_{R}_BW', 'm01', 'grf_anterior_{w}_BW', 1.0, 'grf_anterior_{w}_N'),
    ('grf_lateral_{R}_BW', 'm01', 'grf_lateral_{w}_BW', 1.0, 'grf_lateral_{w}_N'),
    ('grf_lab_x_{R}_BW', 'm01', 'grf_lab_x_{w}_BW', 1.0, 'grf_lab_x_{w}_N'),
    ('grf_lab_z_{R}_BW', 'm01', 'grf_lab_z_{w}_BW', 1.0, 'grf_lab_z_{w}_N'),
    ('cop_anterior_{R}_m', 'c06', 'cop_anterior_{w}_m', 1.0, 'cop_anterior_{w}_m'),
    ('cop_vertical_{R}_m', 'c06', 'cop_vertical_{w}_m', 1.0, 'cop_vertical_{w}_m'),
    ('cop_lateral_{R}_m', 'c06', 'cop_lateral_{w}_m', 1.0, 'cop_lateral_{w}_m'),
    ('cop_lab_x_{R}_m', 'c06', 'cop_lab_x_{w}_m', 1.0, 'cop_lab_x_{w}_m'),
    ('cop_lab_y_{R}_m', 'c06', 'cop_lab_y_{w}_m', 1.0, 'cop_lab_y_{w}_m'),
    ('cop_lab_z_{R}_m', 'c06', 'cop_lab_z_{w}_m', 1.0, 'cop_lab_z_{w}_m'),
    ('heading_lab_x_{R}', 'c06', 'heading_lab_x_{w}', 1.0, 'heading_lab_x_{w}'),
    ('heading_lab_z_{R}', 'c06', 'heading_lab_z_{w}', 1.0, 'heading_lab_z_{w}'),
)
PELVIS_SPEC = ('pelvis_sagittal_angle_rad', 'c06', 'pelvis_sagittal_angle_rad', 1.0, 'pelvis_sagittal_angle_rad')
SIDE_WORD = {'left': 'l', 'right': 'r'}
OTHER = {'left': 'right', 'right': 'left'}
IDENTITY = ('subject', 'source_recording_id', 'observation_id', 'reference_side', 'observation_type', 'task', 'task_id',
            'task_info', 'subject_metadata')
CLOCKS = ('source_start_time_s', 'source_end_time_s')

HELD_NOT_A_NUMBER_OBS = 'no finite value inside this observation (source values are not a number here)'
HELD_NOT_A_NUMBER_REC = 'source values are not a number over the whole recording'
HELD_PLATE_MOMENT_NOTE = ' (moments and powers of that leg are not a number in the source as well)'
PLATE_MISSING = 'source plate force is missing for this leg in this recording'

README_UNITS_NOTE = ('The publisher README lists joint moments in N*m and powers in W, but the published values are '
                     'already per kilogram; they are labelled Nm_kg and W_kg here and are not divided by mass again.')
AB09_LIMIT = ('AB09 divisor limit: the publisher divided this recording by a mass the audit could not place among the listed '
              'masses (no plausible listed mass inside the force-plate interval); the rescale used the nearest listed mass '
              '(87.6 kg) and may be off by up to about 5 percent.')
AB07_LIMIT = ('AB07 right-foot marker offset limit: the foot-frame pressure point of the right foot lies outside the marker '
              'foot for about 30 percent of loaded normal-walk samples (72 percent between 0.2 and 0.5 of peak load; marker foot '
              'length 0.193 m), and the AB07 foot angle offset is the largest of the twelve participants (ankle offset about -9 '
              'to -13 degrees); the cause is unresolved. Left-foot values of AB07 are affected by a missing LMANK marker as listed '
              'per recording.')
CURB_UP_NOTE = ('curb_up foot-frame pressure point is held: the heel stands 0.20 to 0.23 m above the recorded plate surface '
                '(a curb of undocumented height); force and plate pressure point stay.')
MASS_NOTES = {
    'rescaled_exact': 'Per-kg moments and powers multiplied by {factor:.6f} (mass used {used} kg over own mass {own} kg): the '
                      'publisher divided by another participant\'s listed mass; the mass used is exact (local N*m inverse dynamics).',
    'rescaled_estimated': 'Per-kg moments and powers multiplied by {factor:.6f} (mass used {used} kg over own mass {own} kg): the '
                          'publisher divided by another participant\'s listed mass; the mass used is estimated from the force plates '
                          'and matched to the nearest listed mass.',
    'own_mass_confirmed': 'Kept as published: the published per-kg values are consistent with the participant\'s own mass.',
    'cannot_be_told': 'Kept as published: the mass the publisher divided by cannot be told for this recording.',
}

# ----------------------------------------------------------------------------------------------- labels and tasks
WALK_SPEEDS = {'0-6': 0.6, '1-2': 1.2, '1-8': 1.8, '2-0': 2.0, '2-5': 2.5, 'shuffle': 0.4, 'skip': 1.2}
BACKWARD_SPEEDS = {'0-6': 0.6, '0-8': 0.8, '1-0': 1.0}
DYNAMIC_SPEEDS = {'butt-kicks': 0.8, 'heel-walk': 0.4, 'high-knees': 0.8, 'toe-walk': 0.4}
JUMP_LABELS = ('fb', 'hop', 'vertical', '90-1', '90-2', '180', 'lateral')
FIXED_TASKS = {
    'side_shuffle': ('agility_drill', 'side_shuffle'), 'tire_run': ('agility_drill', 'tire_run'),
    'obstacle_walk': ('free_walk_episode', 'obstacle_walk'), 'meander': ('free_walk_episode', 'meander'),
    'start_stop': ('free_walk_episode', 'start_stop'), 'poses': ('balance_pose', 'poses'),
    'push': ('perturbation', 'push'), 'tug_of_war': ('perturbation', 'tug_of_war'),
    'twister': ('perturbation', 'twister'), 'curb_up': ('step_up', 'curb_up'), 'curb_down': ('step_down', 'curb_down'),
}
TREADMILL_TASKS = ('normal_walk', 'dynamic_walk', 'incline_walk', 'obstacle_walk', 'walk_backward', 'weighted_walk')
CUTTING_LABELS = ('left-fast', 'left-slow', 'right-fast', 'right-slow')


class LabelError(ValueError):
    """An authors' label outside the lists above stops the job; there is no default."""


def authors_label(recording, authors_file):
    """The authors' file name without the recording name and the _parsing.mat ending ('' when none remains)."""
    if authors_file is None:
        return None
    head, tail = recording + '_', '_parsing.mat'
    if not (authors_file.startswith(head) and authors_file.endswith(tail)):
        if authors_file == recording + tail:
            return ''
        raise LabelError(f'{authors_file!r} does not belong to recording {recording!r}')
    label = authors_file[len(head):-len(tail)]
    if not recording[-1].isdigit():
        # the AB02 recording folder is 'step_ups' while the authors' files are 'step_ups_1_<leg>': drop the file's own number
        m = re.fullmatch(r'\d+_(.+)', label)
        if m:
            label = m.group(1)
    return label


def stair_pass(recording):
    """('stair_ascent'|'stair_descent', pass number) from the publisher's README list: odd pass up, even pass down."""
    m = re.fullmatch(r'stairs_1_(\d+)', recording)
    if not m:
        raise LabelError(f'stairs recording {recording!r} is not stairs_1_<pass>')
    n = int(m.group(1))
    return ('stair_ascent' if n % 2 == 1 else 'stair_descent'), n


def classify(task, recording, label):
    """(task family, task_id, info) for one observation. ``label`` None means unknown (no authors' window matched)."""
    info = {'source_task': task, 'source_recording': recording}
    if task in TREADMILL_TASKS:
        info['treadmill'] = True
    unknown = label is None
    fam = tid = None
    if task == 'normal_walk':
        if unknown:
            fam, tid = 'functional_task', 'normal_walk_unlabelled'
        elif label in WALK_SPEEDS:
            info['speed_m_s'] = WALK_SPEEDS[label]
            fam, tid = (('run', f'run_{label}') if label in ('2-0', '2-5') else
                        ('agility_drill', 'skip') if label == 'skip' else ('level_walking', f'level_{label}'))
        else:
            raise LabelError(f'normal_walk label {label!r}')
    elif task == 'incline_walk':
        info['speed_m_s'] = 1.2  # publisher README states 1.2 m/s for the whole task
        if unknown:
            fam, tid = 'functional_task', 'incline_walk_unlabelled'
        else:
            m = re.fullmatch(r'(up|down)(5|10)', label)
            if not m:
                raise LabelError(f'incline_walk label {label!r}')
            deg = int(m.group(2))
            if m.group(1) == 'up':
                info['incline_deg'], fam, tid = deg, 'incline_walking', f'incline_{deg}deg'
            else:
                info['incline_deg'], fam, tid = -deg, 'decline_walking', f'decline_{deg}deg'
    elif task == 'stairs':
        fam, n = stair_pass(recording)
        tid = fam
        info['pass_number'] = n
        info['stair_rise_m'] = 0.152
        info['stair_rise_source'] = PAPER
        if not unknown and label not in (('up',) if fam == 'stair_ascent' else ('down',)):
            raise LabelError(f'stairs label {label!r} disagrees with the pass list for {recording}')
    elif task == 'dynamic_walk':
        fam = 'dynamic_walk'
        if unknown:
            tid = 'dynamic_walk_unlabelled'
        elif label in DYNAMIC_SPEEDS:
            tid, info['speed_m_s'] = label, DYNAMIC_SPEEDS[label]
        else:
            raise LabelError(f'dynamic_walk label {label!r}')
    elif task == 'weighted_walk':
        fam = 'weighted_walk'
        info['notes'] = ['speed not set: the README says 1.0 m/s and the authors\' plotting code says 1.25 m/s (unresolved)']
        if unknown:
            tid = 'weighted_unlabelled'
        elif label == '25lbs':
            tid, info['weight_lb'] = 'weighted_25lbs', 25
        else:
            raise LabelError(f'weighted_walk label {label!r}')
    elif task == 'walk_backward':
        fam = 'walk_backward'
        if unknown:
            tid = 'backward_unlabelled'
        elif label in BACKWARD_SPEEDS:
            tid, info['speed_m_s'] = f'backward_{label}', BACKWARD_SPEEDS[label]
        else:
            raise LabelError(f'walk_backward label {label!r}')
    elif task == 'jump':
        if unknown:
            fam, tid = 'functional_task', 'jump_unlabelled'
        elif label in JUMP_LABELS:
            fam, tid = ('hop' if label == 'hop' else 'jump'), f'jump_{label}'
        else:
            raise LabelError(f'jump label {label!r}')
    elif task == 'ball_toss':
        fam, info['object_weight_lb'] = 'load_handling', 15
        if unknown:
            tid = 'ball_toss_unlabelled'
        elif label in ('center', 'left', 'right', 'left-2'):
            tid = f'ball_toss_{label}'
        else:
            raise LabelError(f'ball_toss label {label!r}')
    elif task == 'cutting':
        fam = 'cutting'
        if unknown:
            tid = 'cutting_unlabelled'
        elif label in CUTTING_LABELS:
            tid = f'cutting_{label}'
        else:
            raise LabelError(f'cutting label {label!r}')
    elif task == 'lift_weight':
        fam = 'load_handling'
        if unknown:
            tid = 'lift_unlabelled'
        else:
            m = re.fullmatch(r'(0|25)lbs-(l|r)-(c|l|r)', label)
            if not m:
                raise LabelError(f'lift_weight label {label!r}')
            tid, info['weight_lb'] = f'lift_{label}', int(m.group(1))
    elif task == 'lunges':
        fam = 'lunge'
        if unknown:
            tid = 'lunge_unlabelled'
        elif label == '' or label in ('left', 'right'):
            tid = 'lunge' if label == '' else f'lunge_{label}'
        else:
            raise LabelError(f'lunges label {label!r}')
    elif task == 'sit_to_stand':
        fam = 'sit_to_stand'
        if unknown:
            tid = 'sit_to_stand_unlabelled'
        elif label in ('short-arm', 'short-noarm', 'tall-noarm'):
            tid = f'sit_to_stand_{label}'
        else:
            raise LabelError(f'sit_to_stand label {label!r}')
    elif task == 'squats':
        fam = 'squat'
        if unknown:
            tid = 'squat_unlabelled'
        elif label in ('0lbs', '25lbs'):
            tid, info['weight_lb'] = f'squat_{label}', int(label[:-3])
        else:
            raise LabelError(f'squats label {label!r}')
    elif task == 'step_ups':
        fam = 'step_up'
        if unknown:
            tid = 'step_up_unlabelled'
        elif label in ('left', 'right'):
            tid = f'step_up_{label}'
        else:
            raise LabelError(f'step_ups label {label!r}')
    elif task == 'turn_and_step':
        fam = 'agility_drill'
        info['notes'] = ['the README implies pelvis-speed windows but the authors\' plotting code cuts them at toe-off; unresolved']
        if unknown:
            tid = 'turn_and_step_unlabelled'
        elif label in ('left-turn', 'right-turn'):
            tid = f'turn_and_step_{label}'
        else:
            raise LabelError(f'turn_and_step label {label!r}')
    elif task in FIXED_TASKS:
        fam, tid = FIXED_TASKS[task]
        if task == 'obstacle_walk':
            info['speed_m_s'] = 1.0  # publisher README states 1.0 m/s
        if task in ('curb_up', 'curb_down'):
            info['notes'] = ['no curb height in any source; for AB02 the curb file names say one leg but the fields hold the other']
        if not unknown and task in ('curb_up', 'curb_down') and label not in ('', 'left', 'right'):
            raise LabelError(f'{task} label {label!r}')
        if not unknown and task not in ('curb_up', 'curb_down') and label not in ('',):
            raise LabelError(f'{task} has no label list but got {label!r}')
    else:
        raise LabelError(f'task {task!r} is not in the 26-task list')
    info['authors_label'] = label
    return fam, tid, info


# ----------------------------------------------------------------------------------------------- spec helpers
def role_columns(roles):
    """Export column names for the given {role token: side word} mapping, in a fixed order."""
    names = [PELVIS_SPEC[0]]
    for template, *_ in LEG_SPECS:
        for token in roles:
            names.append(template.format(R=token))
    return names


def column_sources(token, side):
    """[(export name, family, source name, sign, held key or None)] for one leg (token = role or side word)."""
    s, out = SIDE_WORD[side], []
    for template, family, src, sign, hold in LEG_SPECS:
        out.append((template.format(R=token), family, src.format(w=side, s=s), sign, None if hold is None else hold.format(w=side)))
    return out


def phase_samples(values, a, b, n=N_PHASE):
    """n samples of ``values`` between integer sample indices a and b (inclusive ends) by linear interpolation in the
    sample index. Exact integer positions use the sample itself; any non-finite neighbour gives NaN (never filled)."""
    if not (0 <= a < b < len(values)):
        raise ValueError(f'span {a}..{b} outside 0..{len(values) - 1}')
    steps = np.arange(n, dtype=np.int64) * (b - a)
    lo = a + steps // (n - 1)
    rem = steps % (n - 1)
    hi = np.minimum(lo + 1, b)
    w = rem / float(n - 1)
    x_lo, x_hi = values[lo], values[hi]
    out = np.where(rem == 0, x_lo, x_lo * (1.0 - w) + x_hi * w)
    return out


def held_reason(column, held_key, rec_held, finite_in_obs, finite_in_rec, plate_missing_leg, family):
    """Reason text for a column that is entirely missing in this observation, or None when it holds data."""
    if finite_in_obs:
        return None
    if held_key is not None and held_key in rec_held:
        return rec_held[held_key]
    if family == 'm01' and column.startswith(('hip_', 'knee_', 'ankle_', 'subtalar_')) and plate_missing_leg:
        return PLATE_MISSING + HELD_PLATE_MOMENT_NOTE
    return HELD_NOT_A_NUMBER_REC if not finite_in_rec else HELD_NOT_A_NUMBER_OBS


def mass_key(entry):
    """one of rescaled_exact, rescaled_estimated, own_mass_confirmed, cannot_be_told from an M01 ledger entry."""
    if entry['action'] == 'rescale':
        if entry['how_known'] not in ('exact', 'estimated'):
            raise ValueError(f"unknown rescale class {entry['how_known']!r}")
        return f"rescaled_{entry['how_known']}"
    if entry['note_key'] not in ('own_mass_confirmed', 'cannot_be_told'):
        raise ValueError(f"unknown kept class {entry['note_key']!r}")
    return entry['note_key']


def mass_note(entry):
    key = mass_key(entry)
    return key, MASS_NOTES[key].format(factor=entry.get('factor') or 0.0, used=entry.get('mass_used_kg'), own=entry.get('own_mass_kg'))


def ab09_divisor_limit(entry):
    prov = entry.get('audit_provenance') or {}
    return (entry['action'] == 'rescale' and entry['how_known'] == 'estimated' and entry['subject'] == 'AB09'
            and prov.get('plausible_divisors_kg') == [])


def recording_limits(subject, entry, task):
    limits = []
    if ab09_divisor_limit(entry):
        limits.append(AB09_LIMIT)
    if subject == 'AB07':
        limits.append(AB07_LIMIT)
    if task == 'curb_up':
        limits.append(CURB_UP_NOTE)
    return limits


def observation_sides(side_code):
    """S01 side code -> list of reference sides. A window-rule span has no single leg: both legs, same identity."""
    return {'L': ['left'], 'R': ['right'], 'both': ['left', 'right']}[side_code]


def obs_type(task_class):
    return 'individual_cycle' if task_class == 'gait' else 'transfer'


def subject_meta(mass_kg):
    return {'body_mass_kg': mass_kg, 'body_mass_source': 'publisher README table (AB03 113.5 kg)',
            'body_weight_mass_kg': mass_kg}


def dumps(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))
