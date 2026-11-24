"""Georgia Tech 2021 segmentation (GT21-RB03) and the stance force mask (closes the GT21-RB02 zero-fill finding): pure
functions, no file access.

Steps. A source step is the interval between two consecutive heel-strike resets of one leg's source gait table (gcLeft or
gcRight: HeelStrike percentage equal to 0 right after a positive value), the definition of the existing converter and
of the all-source-phases census (83,206 resets, 78,604 steps for the 16 local participants). Both legs are listed. Every
step gets exactly one disposition: ``eligible``, ``held`` (accounted, waiting for a source fact that was not exported) or
``excluded`` with a reason. Nothing is dropped.

Terrain. The label comes only from the source label windows (contiguous runs of one label in the conditions table,
exported by GT21-RB01). A step is labelled only when both its heel strikes lie inside ONE window whose label maps to a task
(the existing converter's rule: both resets inside the window). A step that touches two windows is listed as straddling
with the labels it touches; it is never given the label of either. Ramp incline and stair height come only from the
source scalars and must be finite and positive; nothing is defaulted (no ascent, no 4 inch step, no whole-recording
fallback). Treadmill recordings carry no label table and the speed table was not exported; their steps are ``held``.

Force mask. Wherever event stance is true and the foot owns no plate carrying at least FORCE_MASK_N newtons, the foot's
force (vertical, anterior, lateral) is missing, not 0. FORCE_MASK_N = 20 N was fixed before any result was seen: the
levelground Treadmill_R/Treadmill_L plates carry a median offset of about 13 N (RB02 verifier), and 20 N is 1.5 times
that offset, the same value as the GT23 publisher's stance rule, and well below the pass's own 50 N contact level. It is
an absolute force, not a fraction of body weight (0.03 BW would be only 15 N for the lightest participant).

Force check. Each step's source heel strike is compared with the foot's vertical force rising through the same 20 N
(nearest crossing within a 200 ms search); agreement is within 50 ms. The check is reported with the step and does
not change its disposition: the source events stay the authority.

Authors' segmentation. The authors' STRIDES.m cuts right-leg intervals with segment_gc from gcRight (local minima of the
HeelStrike percentage, plus a partial first and last interval) and classifies ramp and stair intervals by the first and
last label inside them. ``authors_intervals`` reproduces the cutting; ``authors_class`` transcribes the ramp and stair
classification. Levelground and treadmill classes need fields that were not exported (leadingLegStart, leadingLegStop,
turn, treadmill speed) and are not reproduced.

No scientific approval.
"""
import math

import numpy as np

FORCE_MASK_N = 20.0
CROSSING_SEARCH_S = 0.2
AGREE_S = 0.05
EVENT_DROP = 50.0
MIN_GC_SAMPLES = 10
MIN_PEAK_PCT = 50.0
TOL = 1e-9

# label -> (task class). Only labels the existing converter maps are tasks; idle, stand and turn1/turn2 are not.
STEADY = {'levelground': {'walk': 'level_walking'},
          'ramp': {'rampascent': 'incline_walking', 'rampdescent': 'decline_walking'},
          'stair': {'stairascent': 'stair_ascent', 'stairdescent': 'stair_descent'}}
TRANSITION = {'levelground': ('stand-walk', 'walk-stand'),
              'ramp': ('walk-rampascent', 'rampascent-walk', 'walk-rampdescent', 'rampdescent-walk'),
              'stair': ('walk-stairascent', 'stairascent-walk', 'walk-stairdescent', 'stairdescent-walk')}


# ------------------------------------------------------------------------------------------------ source events
def resets(pct):
    """Indices where the percentage is 0 right after a positive value (heel strike); NaN never counts."""
    p = np.asarray(pct, float)
    if p.size < 2:
        return np.zeros(0, int)
    with np.errstate(invalid='ignore'):
        hit = (p[1:] == 0) & (p[:-1] > 0)
    return np.flatnonzero(hit) + 1


def event_times(header, col, drop=EVENT_DROP):
    """Times where a percentage column falls by more than ``drop`` (the pass's event rule), used for ToeOff."""
    h, x = np.asarray(header, float), np.asarray(col, float)
    if x.size < 2:
        return np.zeros(0)
    with np.errstate(invalid='ignore'):
        return h[np.flatnonzero(np.diff(x) < -drop) + 1]


def phase_issues(phase, start, end):
    """Same checks as the source-phase audit, on the pair of reset indices."""
    issues = []
    interior = phase[start:end]
    if start < 1 or end <= start or end >= len(phase):
        return ['invalid_event_indices']
    if not (phase[start] == 0 and phase[end] == 0 and phase[start - 1] > 0 and phase[end - 1] > 0):
        issues.append('endpoints_not_source_resets')
    if not np.isfinite(phase[start:end + 1]).all():
        issues.append('nonfinite_source_phase')
    if np.any(np.diff(interior) < -1e-8):
        issues.append('source_phase_reversal')
    if np.count_nonzero(interior == 0) != 1:
        issues.append('extra_zero_phase_samples')
    if np.any((interior < 0) | (interior > 100)):
        issues.append('source_phase_outside_0_100')
    return issues


# ------------------------------------------------------------------------------------------------ force mask
def force_missing_mask(stance, vertical_bw, body_weight_n, threshold_n=FORCE_MASK_N):
    """True where stance is true and the foot's vertical force is not at least ``threshold_n`` newtons (a force that is
    already missing counts as not at least the threshold). ``vertical_bw`` is the foot's summed owned-plate force in body
    weights. Returns the mask and a dict of counts by what the force was before."""
    s = np.asarray(stance, bool)
    v = np.asarray(vertical_bw, float)
    with np.errstate(invalid='ignore'):
        enough = v * float(body_weight_n) >= threshold_n
        mask = s & ~enough
        nan_before = s & ~np.isfinite(v)
        zero_before = mask & (v == 0)
        small = mask & np.isfinite(v) & (v != 0)
    stats = {'stance_samples': int(s.sum()), 'masked': int(mask.sum()), 'already_missing': int((mask & nan_before).sum()),
             'was_exactly_zero': int(zero_before.sum()), 'was_small_positive_or_negative': int(small.sum())}
    # stances (runs of true) where the whole stance is masked versus stances with only edge samples masked
    runs = _runs(s)
    full = edge = 0
    for a, b in runs:
        m = int(mask[a:b].sum())
        if m == b - a:
            full += 1
        elif m:
            edge += 1
    stats.update(stances=len(runs), stances_fully_masked=full, stances_with_edge_samples_masked=edge,
                 masked_in_partly_loaded_stances=int(sum(mask[a:b].sum() for a, b in runs if 0 < mask[a:b].sum() < b - a)))
    return mask, stats


def apply_force_mask(columns, leg, mask):
    """Copy of the three force columns of one leg with NaN where the mask is true (the derived layer)."""
    out = {}
    for k in ('grf_vertical', 'grf_anterior', 'grf_lateral'):
        name = f'{k}_{leg}_BW'
        a = np.array(columns[name], float, copy=True)
        a[np.asarray(mask, bool)] = np.nan
        out[name] = a
    return out


def _runs(mask):
    m = np.asarray(mask, bool)
    if not m.size:
        return []
    d = np.diff(np.concatenate(([0], m.astype(np.int8), [0])))
    return list(zip(np.flatnonzero(d == 1).tolist(), np.flatnonzero(d == -1).tolist()))


# ------------------------------------------------------------------------------------------------ label windows
def overlapped_windows(windows, t0, t1):
    return [w for w in windows if w['end_header'] >= t0 - TOL and w['start_header'] <= t1 + TOL]


def label_of_step(windows, t0, t1):
    """(status, label, overlapped labels). status: inside_one_window, straddles, partly_outside_one_window, outside."""
    ov = overlapped_windows(windows, t0, t1)
    labels = [w['label'] for w in ov]
    if not ov:
        return 'outside', None, labels
    if len(ov) >= 2:
        return 'straddles', None, labels
    w = ov[0]
    if w['start_header'] <= t0 + TOL and w['end_header'] >= t1 - TOL:
        return 'inside_one_window', w['label'], labels
    return 'partly_outside_one_window', None, labels


def positive_number(value):
    """A finite positive scalar from a JSON value, else None (a list, null or text is not a value)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    v = float(value)
    return v if math.isfinite(v) and v > 0 else None


def classify_step(mode, meta, t0, t1, header, pct, a, b, table_span, converted=True):
    """One disposition for one step. ``meta``: dict from the RB01 label row (label_windows, label_present,
    ramp_incline_top_level, stair_height_top_level, trial_start, trial_end, read_ok). ``a``, ``b``: reset indices into
    ``pct``/``header``. ``table_span``: (first, last) time of the continuous table, or None.
    Returns a dict with disposition, reason, label, step_class, direction, incline_deg, stair_height_m, labels."""
    out = {'disposition': 'excluded', 'reason': None, 'label': None, 'step_class': None, 'direction': None,
           'incline_deg': None, 'stair_height_m': None, 'labels_overlapped': [], 'window_status': None}
    seg = pct[a:b + 1]
    issues = phase_issues(pct, a, b)
    if issues:
        out['reason'] = 'source_phase_issue: ' + ','.join(issues)
        return out
    if len(seg) < MIN_GC_SAMPLES:
        out['reason'] = f'fewer_than_{MIN_GC_SAMPLES}_source_gait_samples'
        return out
    if not np.nanmax(seg) >= MIN_PEAK_PCT:
        out['reason'] = f'source_gait_percentage_never_reaches_{MIN_PEAK_PCT:g}'
        return out
    if not meta or not meta.get('read_ok'):
        out['reason'] = 'label_export_unreadable'
        return out
    if mode == 'treadmill':
        ts, te = meta.get('trial_start'), meta.get('trial_end')
        if not isinstance(ts, (int, float)) or not isinstance(te, (int, float)):
            out['reason'] = 'no_trial_window'
        elif t0 < ts - TOL or t1 > te + TOL:
            out['reason'] = 'outside_trial_window'
        else:
            out.update(disposition='held', reason='treadmill_speed_table_not_exported_so_steady_speed_unassessed',
                       window_status='inside_trial_window')
        return out
    if not meta.get('label_present'):
        out['reason'] = 'no_label_table'
        return out
    status, label, overlapped = label_of_step(meta.get('label_windows') or [], t0, t1)
    out.update(window_status=status, labels_overlapped=overlapped)
    if status != 'inside_one_window':
        out['reason'] = {'straddles': 'straddles_label_windows', 'outside': 'outside_every_label_window',
                         'partly_outside_one_window': 'not_fully_inside_one_label_window'}[status]
        return out
    steady, trans = STEADY[mode], TRANSITION[mode]
    if label in steady:
        out['step_class'] = 'steady'
    elif label in trans:
        out['step_class'] = 'transition'
    else:
        out['reason'] = f'label_not_mapped_to_a_task: {label}'
        return out
    out['label'] = label
    if mode == 'ramp':
        inc = positive_number(meta.get('ramp_incline_top_level'))
        if inc is None:
            out.update(reason='source_incline_missing_or_not_positive', step_class=None)
            return out
        down = 'rampdescent' in label
        out.update(direction='descent' if down else 'ascent', incline_deg=-inc if down else inc)
    elif mode == 'stair':
        h = positive_number(meta.get('stair_height_top_level'))
        if h is None:
            out.update(reason='source_stair_height_missing_or_not_positive', step_class=None)
            return out
        out.update(direction='descent' if 'stairdescent' in label else 'ascent', stair_height_m=round(h * 0.0254, 3))
    else:
        out['direction'] = None
    if table_span is None:
        out['reason'] = 'recording_not_converted_in_pass'
        return out
    if t0 < table_span[0] - TOL or t1 > table_span[1] + TOL:
        out['reason'] = 'step_outside_continuous_table'
        return out
    out['disposition'] = 'eligible'
    return out


# ------------------------------------------------------------------------------------------------ force check
def rising_crossings(t, f, threshold_n):
    f = np.asarray(f, float)
    ok = np.isfinite(f[:-1]) & np.isfinite(f[1:])
    with np.errstate(invalid='ignore'):
        hit = ok & (f[:-1] < threshold_n) & (f[1:] >= threshold_n)
    return np.asarray(t, float)[np.flatnonzero(hit) + 1]


def force_check(t, vertical_n, hs_time, t0, t1, threshold_n=FORCE_MASK_N):
    """Compare a source heel strike with the foot's vertical force rising through the threshold."""
    t = np.asarray(t, float)
    v = np.asarray(vertical_n, float)
    inside = (t >= t0 - TOL) & (t <= t1 + TOL)
    with np.errstate(invalid='ignore'):
        loaded = bool(np.any(v[inside] >= threshold_n))
    cr = rising_crossings(t, v, threshold_n)
    res = {'force_in_step_reaches_threshold': loaded, 'offset_ms': None}
    near = cr[np.abs(cr - hs_time) <= CROSSING_SEARCH_S + TOL]
    if near.size:
        k = int(np.argmin(np.abs(near - hs_time)))
        off = float((near[k] - hs_time) * 1000.0)
        res['offset_ms'] = off
        res['status'] = 'agrees_within_50_ms' if abs(off) <= AGREE_S * 1000 + 1e-6 else 'nearest_crossing_beyond_50_ms'
    elif not loaded:
        res['status'] = 'foot_never_reaches_threshold_in_step'
    else:
        res['status'] = 'no_crossing_within_200_ms'
    return res


# ------------------------------------------------------------------------------------------------ authors' cutting
def authors_intervals(header, pct):
    """Right-leg (or any leg) intervals as segment_gc's gc2intervals cuts them: findpeaks(-gc) minima (a flat minimum
    reports its first sample), plus the sample before the first positive value and the last positive sample.
    Returns a list of dicts {kind, start_s, end_s, start_index, end_index}."""
    h, g = np.asarray(header, float), np.asarray(pct, float)
    n = len(g)
    if n < 3:
        return []
    neg = -g
    with np.errstate(invalid='ignore'):
        peaks = np.flatnonzero((neg[1:-1] > neg[:-2]) & (neg[1:-1] >= neg[2:])) + 1
        pos = np.flatnonzero(g > 0)
    if not pos.size:
        return []
    first, last = int(pos[0]) - 1, int(pos[-1])
    idx = ([first] if first >= 0 else []) + [int(p) for p in peaks] + [last]
    out = []
    for k in range(len(idx) - 1):
        kind = 'interior'
        if k == 0 and first >= 0:
            kind = 'partial_first'
        if k == len(idx) - 2:
            kind = 'partial_last' if kind == 'interior' else 'partial_first_and_last'
        out.append({'kind': kind, 'start_index': idx[k], 'end_index': idx[k + 1],
                    'start_s': float(h[idx[k]]), 'end_s': float(h[idx[k + 1]])})
    return out


def _all(seq, label):
    return bool(seq) and all(x == label for x in seq)


def authors_class(mode, seq, trans_asc, trans_desc):
    """STRIDES.m ramp and stair classification from the ordered labels inside a stride. Returns a class name, 'discard',
    'case_not_found' (the authors' script stops with an error there), or 'not_reproduced' for other modes."""
    if mode not in ('ramp', 'stair') or not seq:
        return 'not_reproduced' if mode not in ('ramp', 'stair') else 'case_not_found'
    f, l = seq[0], seq[-1]
    anyidle = 'idle' in seq
    A = list(trans_asc or [])
    D = list(trans_desc or [])

    def at(x, i):
        return x[i] if len(x) > i else None
    if mode == 'ramp':
        rules = [
            (_all(seq, 'idle'), 'discard'), (f == 'idle', 'discard'),
            (f == 'rampascent-walk' and l == 'walk-rampdescent' and anyidle, 'discard'),
            (f == 'walk-rampascent' and at(A, 0) == 'l', 'rampascent'),
            (f == 'walk-rampascent' and at(A, 0) == 'r', 'walk-rampascent'),
            (_all(seq, 'rampascent'), 'rampascent'), (l == 'rampascent-walk', 'rampascent-walk'),
            (l == 'idle' and f == 'rampascent-walk', 'discard'),
            (f == 'walk-rampdescent' and at(D, 0) == 'l', 'rampdescent'),
            (f == 'walk-rampdescent' and at(D, 0) == 'r', 'walk-rampdescent'),
            (_all(seq, 'rampdescent'), 'rampdescent'), (l == 'rampdescent-walk', 'rampdescent-walk'),
            (l == 'idle' and f == 'rampdescent-walk', 'discard'),
            (f == 'rampdescent-walk' and l == 'walk-rampascent' and at(A, 0) == 'r', 'discard'),
            (f == 'rampascent-walk' and l == 'rampdescent' and 'walk-rampdescent' in seq, 'discard')]
    else:
        rules = [
            (_all(seq, 'idle'), 'discard'),
            (f == 'idle' and l == 'walk-stairascent' and at(A, 0) == 'l', 'walk-stairascent'),
            (f == 'walk-stairascent' and l == 'stairascent' and at(A, 0) == 'l', 'stairascent'),
            (f == 'stairascent' and l == 'stairascent-walk' and at(A, 1) == 'r', 'stairascent-walk'),
            (f == 'stairascent-walk' and l == 'idle' and at(A, 1) == 'r', 'discard'),
            (f == 'idle' and l == 'walk-stairdescent' and at(D, 0) == 'l', 'stairdescent-walk'),
            (f == 'walk-stairdescent' and l == 'stairdescent' and at(D, 0) == 'l', 'stairdescent'),
            (f == 'stairdescent' and l == 'stairdescent-walk' and at(D, 1) == 'r', 'stairdescent-walk'),
            (f == 'stairdescent-walk' and l == 'idle' and at(D, 1) == 'r', 'discard'),
            (f == 'stairascent-walk' and at(D, 1) == 'l', 'discard'),
            (f == 'walk-stairascent' and l == 'stairascent' and at(A, 0) == 'r', 'stairascent'),
            (_all(seq, 'stairascent'), 'stairascent'),
            (f == 'stairascent' and l == 'stairascent-walk' and at(A, 0) == 'r', 'stairascent-walk'),
            (f == 'stairascent-walk' and l == 'idle' and at(A, 1) == 'l', 'discard'),
            (f == 'idle' and l == 'walk-stairdescent' and at(D, 0) == 'r', 'discard'),
            (f == 'walk-stairdescent' and l == 'stairdescent' and at(D, 0) == 'r', 'stairdescent'),
            (_all(seq, 'stairdescent'), 'stairdescent'),
            (f == 'stairdescent' and l == 'stairdescent-walk' and at(D, 1) == 'l', 'stairdescent-walk'),
            (f == 'stairdescent-walk' and l == 'idle' and at(D, 1) == 'l', 'discard'),
            (f == 'idle' and l == 'walk-stairascent' and at(A, 0) == 'r', 'discard'),
            (f == 'stairascent-walk' and l == 'walk-stairdescent' and anyidle and at(A, 1) == 'l', 'discard'),
            (f == 'stairascent-walk' and l == 'walk-stairdescent' and at(A, 1) == 'r', 'discard')]
    for cond, name in rules:
        if cond:
            return name
    return 'case_not_found'
