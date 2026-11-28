"""Georgia Tech 2023 segmentation rules (GT23 only), pure functions with no file access.

Rules follow the publisher's README "SEGMENTATION DETAILS" (docs/quality/audits/source_evidence/gt23/publisher-readme.txt):

* gait rule: a stride starts when the vertical plate force rises through 20 N and ends at that leg's next rising
  crossing. The start time is the first sample at or above 20 N (probe: 0 ms offset against the authors' strides on
  AB05 and AB12 normal walking). Both legs, each from its own plate.
* window rule: a window starts when the speed of the mean of the pelvis (or, for lifts, trunk) markers rises through
  0.5 m/s and ends when it falls back through it; gaps and spans shorter than the debounce time are handled by named
  parameters. The authors say they then verified windows by hand; that step cannot be reproduced and is not claimed.
* continuous rule: tasks with no defensible cycle are exported as continuous recordings.

Nothing is dropped silently: every contact, interval and span becomes one record with a status and, when excluded, a
reason. The parameters below are fixed in advance from the README and a stated physical range; they are not tuned to
the agreement with the authors' windows.
"""
import re

import numpy as np

STANCE_N = 20.0
GAIT_MIN_S = 0.3   # shortest accepted stride; shorter intervals are listed with a reason, not dropped
GAIT_MAX_S = 5.0   # longest accepted stride; a longer interval spans a pause or a missed contact
SPEED_THRESHOLD_M_S = 0.5
SPEED_HALF_SPAN_SAMPLES = 5   # central difference over 10 samples (50 ms at 200 Hz)
DEBOUNCE_S = 0.25             # sub-threshold gaps shorter than this are bridged; spans shorter than this are excluded
MATCH_TOLERANCE_MS = {'gait': 50.0, 'window': 250.0}
RATE_HZ = 200.0

GAIT_TASKS = ('normal_walk', 'dynamic_walk', 'incline_walk', 'weighted_walk', 'walk_backward', 'stairs',
              'obstacle_walk', 'side_shuffle')
WINDOW_PELVIS_TASKS = ('ball_toss', 'curb_down', 'curb_up', 'cutting', 'jump', 'lunges', 'sit_to_stand', 'squats',
                       'step_ups', 'tire_run', 'turn_and_step')
WINDOW_TRUNK_TASKS = ('lift_weight',)
CONTINUOUS_TASKS = ('meander', 'poses', 'push', 'start_stop', 'tug_of_war', 'twister')
PELVIS_MARKERS = ('LASI', 'RASI', 'LPSI', 'RPSI')
TRUNK_MARKERS = ('C7', 'STRN')

RULES = {
    'gait': 'gait_force_rise_20N_first_sample_at_or_above_each_leg',
    'window_pelvis': 'window_speed_cross_0.5_m_per_s_pelvis_markers',
    'window_trunk': 'window_speed_cross_0.5_m_per_s_trunk_markers',
    'continuous': 'continuous_recording_no_defensible_cycle',
}


class UnknownTask(ValueError):
    """An unlisted task stops the job; there is no default to gait."""


def task_of(recording):
    for task in GAIT_TASKS + WINDOW_PELVIS_TASKS + WINDOW_TRUNK_TASKS + CONTINUOUS_TASKS:
        if re.fullmatch(re.escape(task) + r'(_\d+)*', recording):
            return task
    raise UnknownTask(f'recording {recording!r} does not belong to any of the 26 listed tasks')


def task_class(task):
    if task in GAIT_TASKS:
        return 'gait'
    if task in WINDOW_PELVIS_TASKS:
        return 'window_pelvis'
    if task in WINDOW_TRUNK_TASKS:
        return 'window_trunk'
    if task in CONTINUOUS_TASKS:
        return 'continuous'
    raise UnknownTask(f'task {task!r} is not listed')


def rising_crossings(force, threshold=STANCE_N):
    """Indices i with finite force[i-1] < threshold <= force[i] (first sample at or above the threshold)."""
    f = np.asarray(force, float)
    ok = np.isfinite(f[:-1]) & np.isfinite(f[1:])
    with np.errstate(invalid='ignore'):
        hit = ok & (f[:-1] < threshold) & (f[1:] >= threshold)
    return np.flatnonzero(hit) + 1


def plate_state(force):
    f = np.asarray(force, float)
    finite = np.isfinite(f)
    if not finite.any():
        return 'plate_missing_all_samples_not_a_number'
    if not (f[finite] >= STANCE_N).any():
        return 'plate_never_reaches_threshold'
    return 'plate_present'


def gait_segments(time, force, side, min_s=GAIT_MIN_S, max_s=GAIT_MAX_S):
    """One record per interval between consecutive rising crossings, plus the final contact. Never drops one."""
    t = np.asarray(time, float)
    f = np.asarray(force, float)
    cross = rising_crossings(f)
    out = []
    for k, a in enumerate(cross):
        rec = {'side': side, 'start_index': int(a), 'start_s': float(t[a])}
        if k + 1 == len(cross):
            rec.update(end_index=None, end_s=None, duration_s=None, status='excluded',
                       reason='last_contact_has_no_following_contact')
        else:
            b = cross[k + 1]
            dur = float(t[b] - t[a])
            rec.update(end_index=int(b), end_s=float(t[b]), duration_s=dur, status='accepted', reason=None)
            if not np.isfinite(f[a:b + 1]).all():
                rec.update(status='excluded', reason='force_not_a_number_inside_stride')
            elif dur < min_s:
                rec.update(status='excluded', reason=f'shorter_than_{min_s:g}_s')
            elif dur > max_s:
                rec.update(status='excluded', reason=f'longer_than_{max_s:g}_s')
        out.append(rec)
    return out


def marker_speed(time, positions_mm, half=SPEED_HALF_SPAN_SAMPLES):
    """Speed (m/s) of the mean of the given markers by a central difference; not a number where any input is missing.

    ``positions_mm``: array (n_samples, n_markers, 3).
    """
    t = np.asarray(time, float)
    p = np.asarray(positions_mm, float)
    n = len(t)
    speed = np.full(n, np.nan)
    if n <= 2 * half:
        return speed
    dt = t[2 * half:] - t[:n - 2 * half]
    mean = p.mean(axis=1)  # a missing marker makes the mean not a number: nothing is filled in
    with np.errstate(invalid='ignore', divide='ignore'):
        v = (mean[2 * half:] - mean[:n - 2 * half]) / dt[:, None] * 1e-3
        speed[half:n - half] = np.sqrt((v ** 2).sum(axis=1))
    return speed


def window_segments(time, speed, threshold=SPEED_THRESHOLD_M_S, debounce_s=DEBOUNCE_S):
    """Spans where the speed is at or above the threshold, as records; none dropped without a reason."""
    t = np.asarray(time, float)
    s = np.asarray(speed, float)
    above = np.zeros(len(s), bool)
    finite = np.isfinite(s)
    above[finite] = s[finite] >= threshold
    edges = np.diff(np.concatenate(([0], above.astype(np.int8), [0])))
    starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1) - 1  # inclusive last sample at or above
    spans = list(zip(starts.tolist(), ends.tolist()))
    # bridge short dips, but only dips whose samples are all measured (a missing sample is not evidence of a dip)
    merged = []
    for a, b in spans:
        if merged:
            pa, pb = merged[-1]
            gap = slice(pb + 1, a)
            if t[a] - t[pb] < debounce_s and finite[gap].all():
                merged[-1] = (pa, b)
                continue
        merged.append((a, b))
    out = []
    n = len(t)
    for a, b in merged:
        rec = {'side': 'both', 'start_index': int(a), 'start_s': float(t[a]), 'end_index': int(b), 'end_s': float(t[b]),
               'duration_s': float(t[b] - t[a]), 'status': 'accepted', 'reason': None,
               'peak_speed_m_s': float(np.nanmax(s[a:b + 1]))}
        before_missing = a > 0 and not finite[a - 1]
        after_missing = b < n - 1 and not finite[b + 1]
        if a == 0 or b == n - 1:
            rec.update(status='excluded', reason='span_open_at_recording_edge')
        elif before_missing or after_missing:
            rec.update(status='excluded', reason='span_boundary_next_to_missing_marker')
        elif rec['duration_s'] < debounce_s:
            rec.update(status='excluded', reason=f'shorter_than_{debounce_s:g}_s')
        out.append(rec)
    return out


def match_authors(ours, authors, tolerance_ms, same_side=True):
    """Match each authors' window to the nearest of our records by start time.

    ``ours``: segment records (accepted and excluded). ``authors``: dicts with side, start, end.
    Returns one result dict per authors' window, in order. An authors' window may share our record with another one
    (several authors' files can list the same span). A match needs an accepted record starting within the tolerance.
    """
    results = []
    for a in authors:
        pool = [o for o in ours if (not same_side or o['side'] in (a['side'], 'both'))]
        res = {'status': 'missed', 'reason': None, 'segment_index': None, 'start_offset_ms': None, 'end_offset_ms': None,
               'nearest_start_offset_ms': None}
        if not pool:
            res['reason'] = 'no_record_for_this_leg'
            results.append(res)
            continue
        offs = np.array([(o['start_s'] - a['start']) * 1000.0 for o in pool])
        order = np.argsort(np.abs(offs), kind='stable')
        accepted = [i for i in order if pool[i]['status'] == 'accepted']
        nearest = order[0]
        res['nearest_start_offset_ms'] = float(offs[nearest])
        if accepted and abs(offs[accepted[0]]) <= tolerance_ms:
            o = pool[accepted[0]]
            res.update(status='matched', segment_index=ours.index(o), start_offset_ms=float(offs[accepted[0]]),
                       end_offset_ms=None if o['end_s'] is None else float((o['end_s'] - a['end']) * 1000.0))
        elif abs(offs[nearest]) <= tolerance_ms:
            res['reason'] = 'nearest_record_excluded: ' + str(pool[nearest]['reason'])
            res['segment_index'] = ours.index(pool[nearest])
        else:
            res['reason'] = 'no_record_starts_within_tolerance'
        results.append(res)
    return results
