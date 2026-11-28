"""GT21-RB05 export rules (pure functions, no file access except none).

Turns the merged-pass continuous tables (RB02/RB04), the rule-A step dispositions and the stance force mask (RB03) into
LocoHub observations.

Observations
  * Every rule-A ``eligible`` step of either leg becomes one 150-sample phase observation (inclusive 0 to 100 percent),
    reference leg = the step's leg, ipsi columns = that leg, contra columns = the other leg over the same absolute time
    span (no 50 percent shift assumed). Observation id = the RB03 step id.
  * Every converted recording also becomes one continuous time observation (left and right columns).

Values
  * Angles, speeds, moments and the foot-frame pressure point are the pass values, linearly interpolated in time on the 200 Hz
    pass clock to the 150 phase times (NaN where either neighbouring sample is missing; a phase time that falls on a pass
    sample uses that sample unchanged).
  * Forces in phase observations are NOT interpolated from the 200 Hz table. They are re-derived from the 1 kHz plate source
    at the phase times with the pass's own ownership, sign and body-weight rules (decided before any result was seen: the RB02
    verifier showed that a second linear step from 200 Hz to the phase grid differs from the authors' 1 kHz interpolation by
    up to 0.2 BW at impact; MATLAB equals the 1 kHz interpolation to 2e-14). Plate ownership at a phase time is the pass's
    contact ownership on the time interval [t[a], t[b-1]] of each recorded contact; the sign of the lab Z axis is that of the
    foot's loaded run on the 200 Hz clock (same function as the pass).
  * The RB03 stance force mask (stance true and the foot's owned-plate vertical force under 20 N) makes vertical, anterior and
    lateral force missing, never 0. In phase observations a phase time is masked when either neighbouring pass sample is
    masked (the sample itself when it falls on the pass clock); in the continuous table the layer is applied sample by sample.
  * Power = moment x joint speed, both in the LocoHub convention (D-REF-5), computed row by row in each exported table and
    missing wherever either factor is missing.

Nothing here claims scientific approval.
"""
import json
import re

import numpy as np

N_PHASE = 150
TOL_S = 1e-9
FORCE_MASK_N = 20.0
INCOMPLETE_FRACTION = 0.5          # fixed before results: at least half of a step's stance samples have no force
EDGE_N = 1.0

# (export template, kind, pass column template with {w} = left/right)
LEG_SPECS = (
    ('thigh_sagittal_angle_{R}_rad', 'angle', 'thigh_sagittal_angle_{w}_rad'),
    ('shank_sagittal_angle_{R}_rad', 'angle', 'shank_sagittal_angle_{w}_rad'),
    ('foot_sagittal_angle_{R}_rad', 'angle', 'foot_sagittal_angle_{w}_rad'),
    ('hip_flexion_angle_{R}_rad', 'angle', 'hip_flexion_angle_{w}_rad'),
    ('knee_flexion_angle_{R}_rad', 'angle', 'knee_flexion_angle_{w}_rad'),
    ('ankle_dorsiflexion_angle_{R}_rad', 'angle', 'ankle_dorsiflexion_angle_{w}_rad'),
    ('hip_flexion_velocity_{R}_rad_s', 'velocity', 'hip_flexion_velocity_{w}_rad_s'),
    ('knee_flexion_velocity_{R}_rad_s', 'velocity', 'knee_flexion_velocity_{w}_rad_s'),
    ('ankle_dorsiflexion_velocity_{R}_rad_s', 'velocity', 'ankle_dorsiflexion_velocity_{w}_rad_s'),
    ('hip_flexion_moment_{R}_Nm_kg', 'moment', 'hip_flexion_moment_{w}_Nm_kg'),
    ('knee_flexion_moment_{R}_Nm_kg', 'moment', 'knee_flexion_moment_{w}_Nm_kg'),
    ('ankle_dorsiflexion_moment_{R}_Nm_kg', 'moment', 'ankle_dorsiflexion_moment_{w}_Nm_kg'),
    ('hip_flexion_power_{R}_W_kg', 'power', None),
    ('knee_flexion_power_{R}_W_kg', 'power', None),
    ('ankle_dorsiflexion_power_{R}_W_kg', 'power', None),
    ('grf_vertical_{R}_BW', 'force', 'grf_vertical_{w}_BW'),
    ('grf_anterior_{R}_BW', 'force', 'grf_anterior_{w}_BW'),
    ('grf_lateral_{R}_BW', 'force', 'grf_lateral_{w}_BW'),
    ('cop_anterior_{R}_m', 'cop', 'cop_anterior_{w}_m'),
    ('cop_vertical_{R}_m', 'cop', 'cop_vertical_{w}_m'),
    ('cop_lateral_{R}_m', 'cop', 'cop_lateral_{w}_m'),
)
JOINTS = ('hip_flexion', 'knee_flexion', 'ankle_dorsiflexion')
PELVIS = 'pelvis_sagittal_angle_rad'
IDENTITY = ('subject', 'source_recording_id', 'observation_id', 'reference_side', 'observation_type', 'task', 'task_id',
            'task_info', 'subject_metadata')
CLOCKS = ('source_start_time_s', 'source_end_time_s')
FORCE_KINDS = ('vertical', 'anterior', 'lateral')
OTHER = {'left': 'right', 'right': 'left'}

LIMIT_AB28 = ('AB28 pelvis angle limit: the marker pelvis sagittal angle is about -24 degrees in every mode (other participants -4 to '
              '-18 degrees); consistent within the participant, probably marker placement or posture, not a sign error; not '
              'corrected, not tested further.')
LIMIT_AB27 = ('AB27 right thigh limit: the R_Thigh_Upper marker leaves the rigid thigh in about 22 percent of right-leg frames '
              '(left leg 3 percent); those frames are held (angles, speeds, power and pressure point of that leg missing) and '
              'moments and forces are kept.')
FLAG_LEFT_EXT = 'authors_rule_extended_to_left_leg'
FLAG_INCOMPLETE = 'incomplete_stance_force'
REASON_HOLD = ('bad-fit hold: the segment fit residual is over 20 mm or the knee axis is more than 45 degrees off the lateral '
               'knee marker in every frame of this observation')
REASON_NAN = 'no finite value in this observation (the pass value is missing here)'
REASON_NAN_REC = 'no finite value in the whole recording (the pass value is missing)'
REASON_FORCE_MASK = ('force missing: stance with no plate under the foot carrying at least 20 N (not a measured zero)')
REASON_NO_PLATE = 'no force plate channel in the source recording'
REASON_COP = ('pressure point missing in every sample: the foot carries under 0.2 body weight, the point lies outside the foot-frame '
              'limits, or no plate is owned')
REASON_MOMENT = 'no inverse-dynamics moment in the source for this leg in this observation'
REASON_POWER = 'power missing because the moment or the joint speed is missing here'


# ------------------------------------------------------------------------------------------------ names
def role_columns(roles):
    names = [PELVIS]
    for template, _k, _s in LEG_SPECS:
        for token in roles:
            names.append(template.format(R=token))
    return names


def column_kinds():
    return {template: kind for template, kind, _s in LEG_SPECS}


def kind_of(name):
    if name == PELVIS:
        return 'pelvis'
    for template, kind, _s in LEG_SPECS:
        pre, post = template.split('{R}')
        if name.startswith(pre) and name.endswith(post) and len(name) > len(pre) + len(post):
            return kind
    raise KeyError(name)


def source_columns(token, leg):
    """[(export name, kind, pass column or None, leg)] for one leg."""
    return [(t.format(R=token), kind, None if s is None else s.format(w=leg), leg) for t, kind, s in LEG_SPECS]


def power_inputs(name):
    """(moment export name, velocity export name) for an export power column name."""
    for joint in JOINTS:
        if name.startswith(f'{joint}_power_'):
            tail = name[len(f'{joint}_power_'):]
            return f'{joint}_moment_' + tail.replace('_W_kg', '_Nm_kg'), f'{joint}_velocity_' + tail.replace('_W_kg', '_rad_s')
    raise KeyError(name)


def power_from(moment, velocity):
    """moment x velocity where both are finite, NaN elsewhere (D-REF-5)."""
    m, v = np.asarray(moment, float), np.asarray(velocity, float)
    out = np.full(m.shape, np.nan)
    ok = np.isfinite(m) & np.isfinite(v)
    out[ok] = m[ok] * v[ok]
    return out


# ------------------------------------------------------------------------------------------------ interpolation
def locate(t, tq, tol=TOL_S):
    """Bracket of each query time on clock ``t``: (j, w, exact_index) with exact_index = index of the sample the query falls on
    (within ``tol``) or -1. Queries must lie inside [t[0]-tol, t[-1]+tol]."""
    t, tq = np.asarray(t, float), np.asarray(tq, float)
    if tq.min() < t[0] - tol or tq.max() > t[-1] + tol:
        raise ValueError('query time outside the clock')
    j = np.clip(np.searchsorted(t, tq, side='right') - 1, 0, len(t) - 2)
    w = (tq - t[j]) / (t[j + 1] - t[j])
    exact = np.full(len(tq), -1, int)
    lo = np.abs(tq - t[j]) <= tol
    hi = np.abs(tq - t[j + 1]) <= tol
    exact[hi] = j[hi] + 1
    exact[lo] = j[lo]
    return j, w, exact


def sample_at(y, loc):
    """Values of ``y`` at located query times: the sample itself where the query is on the clock, else linear interpolation
    (NaN where either neighbour is not finite)."""
    j, w, exact = loc
    y = np.asarray(y, float)
    out = y[j] + w * (y[j + 1] - y[j])
    on = exact >= 0
    out[on] = y[exact[on]]
    return out


def mask_at(mask, loc):
    """Bool mask at located query times: the sample's own value when on the clock, else true if either neighbour is true."""
    j, _w, exact = loc
    mask = np.asarray(mask, bool)
    out = mask[j] | mask[j + 1]
    on = exact >= 0
    out[on] = mask[exact[on]]
    return out


def zsign_at(zsign, loc):
    """Lab-Z sign at located times: the sample's own on the clock, else the earlier neighbour's, else the later one's."""
    j, _w, exact = loc
    z = np.asarray(zsign, float)
    out = z[j].copy()
    miss = np.isnan(out)
    out[miss] = z[j + 1][miss]
    on = exact >= 0
    out[on] = z[exact[on]]
    return out


def own_at(t, contacts, plate_index, leg, tq, n_plates, tol=TOL_S):
    """(len(tq), P) bool: plate p is owned by ``leg`` at a query time inside [t[a], t[b-1]] of a recorded contact owned by it."""
    own = np.zeros((len(tq), n_plates), bool)
    for c in contacts:
        if c['owner'] != leg:
            continue
        p = plate_index.get(c['plate'])
        if p is None:
            continue
        lo, hi = t[c['a']], t[c['b'] - 1]
        own[(tq >= lo - tol) & (tq <= hi + tol), p] = True
    return own


def own_from_contacts(n, contacts, plate_index, leg, n_plates):
    """(n, P) ownership on the pass clock reconstructed from the ledger's contact records."""
    own = np.zeros((n, n_plates), bool)
    for c in contacts:
        if c['owner'] == leg and c['plate'] in plate_index:
            own[c['a']:c['b'], plate_index[c['plate']]] = True
    return own


# ------------------------------------------------------------------------------------------------ labels and tasks
class LabelError(ValueError):
    """A rule-A label or terrain value outside the lists below stops the recording; there is no default."""


def _need(step, key):
    v = step.get(key)
    if v is None:
        raise LabelError(f'{step.get("step_id")}: {key} is missing')
    return v


def classify(step):
    """(task, task_id, info) for one eligible step from the authors' label and the authors' terrain fields (port of the existing
    converter's map_levelground_label, map_ramp_label, map_stair_label; treadmill is level walking on the treadmill)."""
    mode, label = step['mode'], step.get('label')
    info = {'surface': {'levelground': 'overground', 'ramp': 'overground', 'stair': 'stairs', 'treadmill': 'treadmill'}[mode],
            'authors_label': label, 'authors_class': step.get('authors_class'), 'source_mode': mode}
    if mode == 'levelground':
        table = {'walk': ('level_walking', 'level', None, None), 'turnccw': ('transition', 'turn_left', 'level_walking', 'level_walking'),
                 'turncw': ('transition', 'turn_right', 'level_walking', 'level_walking'),
                 'stand-walk': ('transition', 'stand_to_walk', 'stand', 'level_walking'),
                 'walk-stand': ('transition', 'walk_to_stand', 'level_walking', 'stand')}
        if label not in table:
            raise LabelError(f'{step["step_id"]}: levelground label {label!r}')
        task, tid, a, b = table[label]
        if task == 'transition':
            info.update(gait_transition=True, transition_from=a, transition_to=b)
        if label == 'turnccw':
            info['turn_direction'] = 'left'
        if label == 'turncw':
            info['turn_direction'] = 'right'
        m = re.search(r'_(fast|normal|slow)_', step['recording'])
        if m:
            info['recording_speed_word'] = m.group(1)
            info['recording_speed_note'] = 'a word from the authors\' recording name, not a measured speed'
        return task, tid, info
    if mode == 'ramp':
        signed = float(_need(step, 'incline_deg'))     # the authors' value as RB03 carries it: positive up, negative down
        direction = _need(step, 'direction')
        if direction not in ('ascent', 'descent'):
            raise LabelError(f'{step["step_id"]}: ramp direction {direction!r}')
        if not (np.isfinite(signed) and signed != 0 and (signed > 0) == (direction == 'ascent')):
            raise LabelError(f'{step["step_id"]}: incline {signed} disagrees with direction {direction}')
        angle = abs(signed)
        info['incline_deg'] = signed
        steady = {'rampascent': ('incline_walking', f'incline_{angle:.1f}deg'),
                  'rampdescent': ('decline_walking', f'decline_{angle:.1f}deg')}
        trans = {'walk-rampascent': ('walk_to_ramp_ascent', 'level_walking', 'incline_walking'),
                 'rampascent-walk': ('ramp_ascent_to_walk', 'incline_walking', 'level_walking'),
                 'walk-rampdescent': ('walk_to_ramp_descent', 'level_walking', 'decline_walking'),
                 'rampdescent-walk': ('ramp_descent_to_walk', 'decline_walking', 'level_walking')}
        want = 'ascent' if 'ascent' in str(label) else 'descent'
        if direction != want:
            raise LabelError(f'{step["step_id"]}: direction {direction} disagrees with label {label}')
        if label in steady:
            return steady[label][0], steady[label][1], info
        if label in trans:
            tid, a, b = trans[label]
            info.update(gait_transition=True, transition_from=a, transition_to=b)
            return 'transition', tid, info
        raise LabelError(f'{step["step_id"]}: ramp label {label!r}')
    if mode == 'stair':
        h = float(_need(step, 'stair_height_m'))
        if not (np.isfinite(h) and h > 0):
            raise LabelError(f'{step["step_id"]}: stair height {h}')
        direction = _need(step, 'direction')
        info['step_height_m'] = h
        want = 'ascent' if 'ascent' in str(label) else 'descent'
        if direction != want:
            raise LabelError(f'{step["step_id"]}: direction {direction} disagrees with label {label}')
        steady = {'stairascent': ('stair_ascent', 'stair_ascent'), 'stairdescent': ('stair_descent', 'stair_descent')}
        trans = {'walk-stairascent': ('walk_to_stair_ascent', 'level_walking', 'stair_ascent'),
                 'stairascent-walk': ('stair_ascent_to_walk', 'stair_ascent', 'level_walking'),
                 'walk-stairdescent': ('walk_to_stair_descent', 'level_walking', 'stair_descent'),
                 'stairdescent-walk': ('stair_descent_to_walk', 'stair_descent', 'level_walking')}
        if label in steady:
            return steady[label][0], steady[label][1], info
        if label in trans:
            tid, a, b = trans[label]
            info.update(gait_transition=True, transition_from=a, transition_to=b)
            return 'transition', tid, info
        raise LabelError(f'{step["step_id"]}: stair label {label!r}')
    if mode == 'treadmill':
        speeds = step.get('speed_values_m_s')
        if not speeds:
            raise LabelError(f'{step["step_id"]}: no treadmill speed values')
        vals = sorted(float(s) for s in speeds)
        info['treadmill'] = True
        info['speed_values_m_s'] = vals
        if len(vals) == 1:
            info['speed_m_s'] = vals[0]
        else:
            info['speed_note'] = 'the authors\' speed table changes inside this step (two values); no single speed is stated'
        return 'level_walking', 'level', info
    raise LabelError(f'mode {mode!r}')


def stance_flags(step):
    """('incomplete_stance_force' or None, fraction of stance samples without force or None)."""
    s, m = step.get('stance_samples'), step.get('force_missing_stance_samples')
    if not s:
        return None, None
    frac = m / s
    return (FLAG_INCOMPLETE if frac >= INCOMPLETE_FRACTION else None), frac


def step_limits(subject):
    out = []
    if subject == 'AB28':
        out.append(LIMIT_AB28)
    if subject == 'AB27':
        out.append(LIMIT_AB27)
    return out


def subject_meta(info, weight_kg, bw_n):
    v = info['values']
    return {'body_mass_kg': weight_kg, 'body_mass_source': 'SubjectInfo Weight, unit kg (RB01 export)', 'body_weight_N': bw_n,
            'body_weight_rule': 'weight_kg x 9.81', 'age_years': v.get('Age'), 'sex_source_letter': v.get('Gender'),
            'height_m': v.get('Height')}


# ------------------------------------------------------------------------------------------------ held columns
def held_reason(name, kind, leg, finite_in_obs, finite_in_rec, hold_all, mask_all, plate_channels):
    """Reason text for a column with no finite value in the observation, or None when it holds data."""
    if finite_in_obs:
        return None
    if kind == 'pelvis':
        return REASON_NAN if finite_in_rec else REASON_NAN_REC
    if kind in ('angle', 'velocity'):
        return REASON_HOLD if hold_all else (REASON_NAN if finite_in_rec else REASON_NAN_REC)
    if kind == 'moment':
        return REASON_MOMENT if finite_in_rec else REASON_NAN_REC
    if kind == 'power':
        return (REASON_HOLD + '; ' if hold_all else '') + REASON_POWER
    if kind == 'force':
        if not plate_channels:
            return REASON_NO_PLATE
        return REASON_FORCE_MASK if mask_all else (REASON_NAN if finite_in_rec else REASON_NAN_REC)
    if kind == 'cop':
        if hold_all:
            return REASON_HOLD
        return REASON_COP
    raise KeyError(kind)


def dumps(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))
