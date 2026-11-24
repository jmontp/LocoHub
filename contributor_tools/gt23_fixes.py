"""GT23-E02 fix rules (pure functions, no file access).

Two blatant-error fixes on the C06 columns before the E01 export rules run. Nothing is refit or tuned.

1. Angle wraps. C06 writes every segment angle wrapped to (-180, 180] degrees. When a segment (the right foot in a heel kick)
   sits near +-180 degrees it crosses that branch cut, and the joint angle (a difference of segment angles) jumps by 360 degrees
   although the motion is continuous. Fix at the source of the wrap: every segment angle is unwrapped along each run of
   consecutive finite samples of the continuous recording (a step of more than 180 degrees between neighbours is a branch
   crossing, never a movement), then the joint angles are differenced again from the unwrapped segments and the speeds are derived
   again. The first sample of a run keeps the branch that puts its joint angle inside (-180, 180], and the run follows
   continuously from it. Only whole multiples of 360 degrees are added to any sample; a check refuses anything else.
   A NaN gap is never bridged: each finite run is handled alone and no sample is invented.

2. Step-up pressure point. In every step_ups recording the foot stands on a step of about 0.5 m that sits on the plate, and the
   recorded COPY_Vertical is the plate surface, so the foot-frame pressure point has no defensible height over the sole. It is
   held exactly as curb_up is held (all three foot-frame columns NaN with a stated reason); force, plate pressure point and angles
   stay. The rule is the task (a step-up onto a raised platform of undocumented height); the measured heel height above the plate
   surface on loaded samples is recorded per recording as evidence, not as a threshold.
"""
import numpy as np

TWO_PI = 2.0 * np.pi
RATE_HZ = 200.0
SPEED_KEEP_TOL = 1e-9          # rad/s: float rounding of a shifted angle; below it the published speed is kept bit for bit
MULTIPLE_TOL = 1e-9            # rad: a change must be a whole multiple of 2 pi within this
SIDES = ('left', 'right')
JOINTS = (('hip', 'hip_flexion'), ('knee', 'knee_flexion'), ('ankle', 'ankle_dorsiflexion'))
STEP_UP_TASK = 'step_ups'
RAISED_GAP_M = 0.17            # C06 constant used by the curb_up hold; here only a reference line for the evidence share
COP_KEYS = ('anterior', 'vertical', 'lateral')

STEP_UP_REASON = ('held: the foot stands on a step of about 0.5 m (undocumented height) that sits on the plate, and the recorded '
                  'plate height is the plate surface, so the pressure point on the sole is not defensible')
STEP_UP_NOTE = ('step_up foot-frame pressure point is held: the foot stands on a step of about 0.5 m (undocumented height) on the '
                'plate and the recorded plate height is the plate surface; force and plate pressure point stay.')


def wrap(a):
    return (np.asarray(a, float) + np.pi) % TWO_PI - np.pi


def central_derivative(x, dt=1.0 / RATE_HZ):
    """Same definition as the C06 speed: difference of the neighbours, wrapped to (-pi, pi], over 2 dt."""
    x = np.asarray(x, float)
    out = np.full(x.shape, np.nan)
    if len(x) > 2:
        out[1:-1] = wrap(x[2:] - x[:-2]) / (2.0 * dt)
    return out


def finite_runs(x):
    """[(start, stop)] half-open index ranges of consecutive finite samples."""
    ok = np.isfinite(x)
    if not ok.any():
        return []
    d = np.diff(np.concatenate([[0], ok.view(np.int8), [0]]))
    return list(zip(np.flatnonzero(d == 1).tolist(), np.flatnonzero(d == -1).tolist()))


def _turns(median):
    return int(np.round(median / TWO_PI))


def unwrap_segments(pelvis, thigh, shank, foot):
    """New (pelvis, thigh, shank, foot) angle arrays in radians. Inputs are not modified."""
    p, t, s, f = (np.array(a, float, copy=True) for a in (pelvis, thigh, shank, foot))
    for a in (p, t, s, f):
        for lo, hi in finite_runs(a):
            a[lo:hi] = np.unwrap(a[lo:hi])      # period 2 pi; the first sample of a run is untouched
    # distal segments, in order: the first sample of a run keeps the branch of its (already placed) parent, i.e. the joint
    # angle there is put inside (-180, 180]; the run then follows continuously from that sample
    for child, parent, sign in ((t, p, 1.0), (s, t, -1.0), (f, s, 1.0)):
        for lo, hi in finite_runs(child):
            both = np.flatnonzero(np.isfinite(parent[lo:hi]))
            if not len(both):
                continue
            j0 = lo + both[0]
            joint0 = (child[j0] - parent[j0]) if sign > 0 else (parent[j0] - child[j0])
            k = int(np.ceil((joint0 - np.pi) / TWO_PI))     # smallest k with joint0 - 2 pi k <= pi
            if k:
                child[lo:hi] -= sign * TWO_PI * k
    return p, t, s, f


def check_whole_turns(old, new):
    """Indices where new differs from old; raises when any difference is not a whole multiple of 2 pi."""
    both = np.isfinite(old) & np.isfinite(new)
    if not np.array_equal(np.isfinite(old), np.isfinite(new)):
        raise ValueError('finite pattern changed')
    idx = np.flatnonzero(both & (new != old))
    if len(idx):
        d = (new[idx] - old[idx]) / TWO_PI
        if np.max(np.abs(d - np.round(d))) * TWO_PI > MULTIPLE_TOL:
            raise ValueError('a change is not a whole multiple of 360 degrees')
    return idx


def fix_angles(cols):
    """cols: dict of C06 column arrays (not modified). Returns (new dict of the changed columns only, report).

    report: {column: {'indices': int array, 'old': float array, 'new': float array}} for every column that changed, angles in
    radians with whole turns of 2 pi, speeds in rad/s (expected none). Columns absent from ``cols`` are skipped."""
    pel = cols['pelvis_sagittal_angle_rad']
    new, report = {}, {}
    pel_new = None
    for side in SIDES:
        names = {k: f'{k}_sagittal_angle_{side}_rad' for k in ('thigh', 'shank', 'foot')}
        if not all(n in cols for n in names.values()):
            continue
        p2, t2, s2, f2 = unwrap_segments(pel, cols[names['thigh']], cols[names['shank']], cols[names['foot']])
        if pel_new is None:
            pel_new = p2
        elif not np.array_equal(pel_new, p2, equal_nan=True):
            raise ValueError('the pelvis unwrap depends on the leg')
        seg = {'pelvis': p2, 'thigh': t2, 'shank': s2, 'foot': f2}
        joint = {'hip': t2 - p2, 'knee': t2 - s2, 'ankle': f2 - s2}
        out = {names['thigh']: t2, names['shank']: s2, names['foot']: f2, 'pelvis_sagittal_angle_rad': p2}
        for j, word in JOINTS:
            out[f'{word}_angle_{side}_rad'] = joint[j]
        for name, arr in out.items():
            arr = np.where(np.abs(arr - cols[name]) <= MULTIPLE_TOL, cols[name], arr)    # rounding of a recomputed difference: keep the published bits
            out[name] = arr
            idx = check_whole_turns(cols[name], arr)
            if len(idx):
                new[name] = arr
                report[name] = {'indices': idx, 'old': cols[name][idx], 'new': arr[idx]}
        for j, word in JOINTS:
            vname = f'{word}_velocity_{side}_rad_s'
            if vname not in cols:
                continue
            v = central_derivative(out[f'{word}_angle_{side}_rad'])
            old = cols[vname]
            same = (np.isnan(v) & np.isnan(old)) | (np.abs(v - old) <= SPEED_KEEP_TOL)
            idx = np.flatnonzero(~same)
            if len(idx):
                keep = np.array(old, float, copy=True)
                keep[idx] = v[idx]
                new[vname] = keep
                report[vname] = {'indices': idx, 'old': old[idx], 'new': v[idx]}
    return new, report


def l2_failures(x, limit_rad=np.radians(30.0)):
    """Indices i where |x[i] - x[i-1]| exceeds the limit with both finite (the Q01 L2 rule on a time table)."""
    x = np.asarray(x, float)
    if len(x) < 2:
        return np.zeros(0, int)
    d = np.diff(x)
    ok = np.isfinite(x[1:]) & np.isfinite(x[:-1])
    return np.flatnonzero(ok & (np.abs(d) > limit_rad)) + 1


def classify_jumps(old, new, limit_rad=np.radians(30.0)):
    """Classify each published L2 failure of one column: 'wrap' when it is gone after the unwrap (the wrapped step is under the
    limit), 'remains' when the unwrapped column still jumps there (not a wrap). Returns (wrap_idx, remains_idx)."""
    before = l2_failures(old, limit_rad)
    after = set(l2_failures(new, limit_rad).tolist())
    wrap_idx = np.array([i for i in before if i not in after], int)
    remains = np.array([i for i in before if i in after], int)
    return wrap_idx, remains


def step_up_hold(task_of_recording):
    """The rule: every recording of the step_ups task."""
    return task_of_recording == STEP_UP_TASK


def hold_step_up_cop(cols, held_columns):
    """New columns (NaN) and held reasons for the six foot-frame pressure-point columns. Inputs are not modified."""
    new, held = {}, dict(held_columns)
    for side in SIDES:
        for k in COP_KEYS:
            name = f'cop_{k}_{side}_m'
            if name in cols:
                new[name] = np.full(cols[name].shape, np.nan)
                held.setdefault(name, STEP_UP_REASON)
    return new, held


def heel_gap_evidence(heel_y, plate_y, vertical_force_n, stance_n=20.0):
    """Heel marker height above the recorded plate surface over loaded samples: n, median, 95th percentile, share above the
    C06 reference line (RAISED_GAP_M). Evidence only; the hold rule does not use it."""
    ok = np.isfinite(heel_y) & np.isfinite(plate_y) & np.isfinite(vertical_force_n) & (vertical_force_n >= stance_n)
    if not ok.any():
        return {'loaded_samples': 0, 'median_m': None, 'p95_m': None, 'share_above_reference_line': None}
    gap = heel_y[ok] - plate_y[ok]
    return {'loaded_samples': int(ok.sum()), 'median_m': float(np.median(gap)), 'p95_m': float(np.percentile(gap, 95)),
            'share_above_reference_line': float(np.mean(gap > RAISED_GAP_M))}
