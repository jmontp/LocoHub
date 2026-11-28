#!/usr/bin/env python3
"""Independent UM21-T02 audit of one existing UM21 treadmill component pilot record.

Checks one subject/condition of the existing pilot output (phase.parquet,
candidate_ledger.jsonl, source_columns.json) against Streaming.mat and against
the base staging record that the pilot claims to preserve. It imports no
producer module (extend_umich_tread_source, reconvert_umich_*, reconvert_recording)
and implements its own HDF5 reads, event pairing and phase resampling.

What it checks (tolerances are fixed in TOLERANCES before any data is read):
- Events and physical side come from the source heel-strike arrays (LHS -> left,
  RHS -> right), never from row or concatenation order. Every consecutive pair
  appears once in the ledger; written pairs match the parquet observations; ipsi
  and contra columns equal the claimed side's and the other side's source channels.
- Source clock: README (R01 Dataset README.pdf) states joint channels at 100 Hz,
  forceplates at 1000 Hz, heel strikes and stride times in 100 Hz frames. The audit
  checks StrideTime == diff(HS) in frames, forceplate length == 10 x joint length,
  heel strikes inside the joint frames, a factor-of-ten plausibility screen on
  stride duration, and per observation the elapsed frame duration in time_s,
  source_start_time_s and source_end_time_s.
- Phase: exactly 150 contiguous rows per observation, phase_ipsi from 0 to 100
  inclusive in equal steps.
- All added source components (expected 84) and every prior column: values and
  NaN masks against the source; prior columns also bit-for-bit against the base.
- Exclusions: every rejected pair carries the reason an independent task-window
  classification gives it.
- Clock of the task intervals (UM21-T02 review R1): cutPoints index the treadmill
  velocity-profile clock (cvel). The audit estimates belt speed from heel and toe
  markers after each source heel strike (joint clock) and compares it with cvel
  over lags of -1000..1000 frames. It passes only if the best lag is within
  +-50 frames and the lag-0 median error is within 0.02 m/s of the best. A failure
  here fails the audit: the task-window labels and exclusions are then not valid.

Signs: the pilot is a staging output in source signs. D-UM21-C03-1 rule C
(pelvis tilt, knee angle and knee moment x -1) is a downstream release transform;
a pilot column that already carries it fails the value checks. Ankle alternate
Cardan-branch frames (|component 2| > 90 deg) and exact (0, 0, 0) joint-angle
triples inside exported windows are reported as flags (values may be preserved
correctly but still need the logged release rule); they do not fail the audit.

Exit codes: 0 all checks passed; 1 a check failed; 2 usage or input error;
4 stopped by the RSS self-guard. The report is written to <output-dir>/audit_report.json;
the output directory must not exist.
"""
import os

THREAD_ENV = ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
              'ARROW_NUM_THREADS', 'NUMEXPR_NUM_THREADS')
for _key in THREAD_ENV:
    os.environ[_key] = '1'

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
import resource
import sys
import time

SCHEMA = 'locohub.um21_t02_pilot_audit/1'
ADDRESS_SPACE_MIB_MAX = 768
SOURCE_RATE_HZ = 100           # README: joint angles/forces/moments/powers, HS and StrideTime frames.
FORCEPLATE_RATIO = 10          # README: forceplates 1000 Hz.
SAMPLES = 150
STRIDE_SECONDS_SCREEN = (0.7, 2.0)   # walking stride; a x10 clock error lands far outside.
MAX_DATASET_BYTES = 8 * 1024**2      # admission per joint dataset (AB01/d10: 0.39 MiB).
MAX_METADATA_BYTES = 1024**2
TOLERANCES = {
    'source_component_abs': 1e-9,     # source units (deg, N/kg, N*m/kg, W/kg)
    'angle_rad_abs': 1e-9,
    'velocity_rad_s_abs': 1e-7,
    'clock_s_abs': 1e-12,
    'phase_percent_abs': 1e-12,
    'nan_mask': 'exact',
    'prior_columns_vs_base': 'bitwise (float64 bits, strings equal)',
    'resampling': ('linear between source frames at exact rational positions k*(n-1)/149; '
                   'a sample on a source frame takes that frame; otherwise NaN if either neighbour is non-finite'),
    'velocity': ('first-order one-sided at the ends, central inside; NaN if any sample the formula touches, '
                 'including the centre sample, is non-finite (as np.gradient on a near-uniform grid)'),
    'belt_clock_best_lag_frames_abs_max': 50,
    'belt_clock_lag0_excess_error_m_s_max': 0.02,
    'belt_clock_lag_search_frames': [-1000, 1000],
    'belt_clock_min_comparisons': 'max(8, ceil(half the comparisons available at lag 0)) at every lag considered',
    'belt_clock_method': ('per source heel strike h (joint frame, 1-based): mean over frames h+15..h+29 of the mean of '
                          "that side's HEE and TOE central-difference velocities (x 100 Hz, m/s); belt speed = |AP component|, "
                          'AP axis = the axis with the largest median |window velocity|; marker frames h+14..h+30 must be '
                          'finite, not (0,0,0) and not flagged 0; compared with cvel[h+22+lag-1] (0-based) for heel strikes '
                          'inside a transition interval (label a* or d*) +-300 frames; error = median |difference|'),
}
BELT_MARKERS = ('HEE', 'TOE')
BELT_WINDOW = (15, 29)
BELT_CENTRE = 22
BELT_MARGIN = 300
GROUPS = {  # group -> (column kind, unit token, README unit)
    'jointAngles': ('joint_angle', 'deg', 'deg'),
    'jointForces': ('joint_force', 'N_kg', 'N/kg'),
    'jointMoments': ('joint_moment', 'Nm_kg', 'N*m/kg'),
    'jointPowers': ('joint_power', 'W_kg', 'W/kg'),
}
WALK_LABEL_PREFIX = 's'
TRANSITION_LABELS = {'a0x2', 'a0x5', 'd0x2', 'd0x5'}
INCLINES = {'d10': -10, 'd5': -5, 'i0': 0, 'i5': 5, 'i10': 10}
EXCLUDE_OUTSIDE = 'outside or ambiguous task interval'
PRODUCER_MODULE_MARKERS = ('extend_umich_tread_source', 'reconvert_umich', 'reconvert_recording')
OWN_MODULES = {'contributor_tools', 'contributor_tools.audit_um21_tread_pilot', '__main__'}


class AuditInputError(Exception):
    pass


class RssGuard(Exception):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            h.update(chunk)
    return h.hexdigest()


def peak_rss_mib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def set_address_space(mib):
    if not 0 < mib <= ADDRESS_SPACE_MIB_MAX:
        raise AuditInputError(f'address space must be in (0, {ADDRESS_SPACE_MIB_MAX}] MiB')
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    want = int(mib) * 1024**2
    if hard != resource.RLIM_INFINITY:
        want = min(want, hard)
    resource.setrlimit(resource.RLIMIT_AS, (want, want if hard == resource.RLIM_INFINITY else hard))
    return resource.getrlimit(resource.RLIMIT_AS)


# ---------------------------------------------------------------- resampling
def resample_linear(raw):
    """Own phase resampling: 150 samples from the first to the last frame inclusive."""
    import numpy as np
    raw = np.asarray(raw, dtype=float)
    n = raw.shape[-1]
    if n < 2:
        raise AuditInputError('window needs at least two frames')
    out = np.empty(raw.shape[:-1] + (SAMPLES,))
    span = n - 1
    for k in range(SAMPLES):
        index, remainder = divmod(k * span, SAMPLES - 1)
        if remainder == 0:
            out[..., k] = raw[..., index]
        else:
            frac = remainder / (SAMPLES - 1)
            out[..., k] = raw[..., index] * (1.0 - frac) + raw[..., index + 1] * frac
            # NaN if either neighbour is non-finite (no bridging of missing frames).
            bad = ~(np.isfinite(raw[..., index]) & np.isfinite(raw[..., index + 1]))
            if np.ndim(bad):
                out[..., k][bad] = np.nan
            elif bad:
                out[..., k] = np.nan
    return out


def time_grid(start, end):
    import numpy as np
    return np.array([k * (end - start) / ((SAMPLES - 1) * SOURCE_RATE_HZ) for k in range(SAMPLES)])


def finite_difference(values, times):
    """First-order one-sided at the ends, central inside; NaN if any used sample is NaN."""
    import numpy as np
    d = np.empty(SAMPLES)
    d[0] = (values[1] - values[0]) / (times[1] - times[0])
    d[-1] = (values[-1] - values[-2]) / (times[-1] - times[-2])
    d[1:-1] = (values[2:] - values[:-2]) / (times[2:] - times[:-2])
    d[~np.isfinite(values)] = np.nan
    return d


# ---------------------------------------------------------------- source
def matlab_text(handle, ref):
    data = handle[ref]
    if data.size > 256:
        raise AuditInputError('task label too long')
    return ''.join(chr(int(c)) for c in data[...].reshape(-1))


def small(dataset):
    if dataset.size * dataset.dtype.itemsize > MAX_METADATA_BYTES:
        raise AuditInputError(f'metadata array over admission: {dataset.name}')
    return dataset[...]


def read_source(handle, subject, condition):
    import numpy as np
    path = f'Streaming/{subject}/Tread/{condition}'
    if path not in handle:
        raise AuditInputError(f'source record missing: {path}')
    trial = handle[path]
    events = trial['events']
    hs = {}
    stride = {}
    for side, key, tkey in (('left', 'LHS', 'LStrideTime'), ('right', 'RHS', 'RStrideTime')):
        hs[side] = small(events[key]).astype(float).reshape(-1)
        stride[side] = small(events[tkey]).astype(float).reshape(-1)
    cuts = small(events['cutPoints']).astype(float)
    labels = [matlab_text(handle, r) for r in small(events['tasks']).reshape(-1)]
    channels = {}
    lengths = {}
    for group in GROUPS:
        if group not in trial:
            continue
        for name, ds in trial[group].items():
            if ds.ndim != 2 or not 1 <= ds.shape[0] <= 3:
                raise AuditInputError(f'unexpected source dimensions {ds.name} {ds.shape}')
            if ds.size * ds.dtype.itemsize > MAX_DATASET_BYTES:
                raise AuditInputError(f'source dataset over admission: {ds.name}')
            channels[(group, name)] = np.asarray(ds[...], dtype=float)
            lengths[(group, name)] = ds.shape[1]
    forceplate_lengths = {}
    if 'forceplates' in trial:
        forceplate_lengths = {n: d.shape[-1] for n, d in trial['forceplates'].items()}
    cvel = trial.get('events/VelProf/cvel')
    if cvel is not None and cvel.size * cvel.dtype.itemsize > MAX_DATASET_BYTES:
        raise AuditInputError('cvel over admission')
    markers = {}
    for side in 'LR':
        for name in BELT_MARKERS:
            ds = trial.get(f'markers/{side}{name}')
            if ds is not None:
                if ds.ndim != 2 or ds.shape[0] not in (3, 4) or ds.size * ds.dtype.itemsize > MAX_DATASET_BYTES:
                    raise AuditInputError(f'unexpected marker dimensions {ds.name}')
                markers[side + name] = np.asarray(ds[...], dtype=float)
    return {'hs': hs, 'stride': stride, 'cuts': cuts, 'labels': labels, 'channels': channels,
            'lengths': lengths, 'forceplate_lengths': forceplate_lengths,
            'cvel': np.asarray(cvel[...], dtype=float).reshape(-1) if cvel is not None else None,
            'cvel_length': int(cvel.size) if cvel is not None else None, 'markers': markers}


def belt_clock_alignment(hs, markers, cvel, cuts, labels, with_series=False):
    """Lag (frames) between the cvel/cutPoints clock and the joint/marker clock.

    hs: {'left': 1-based heel-strike frames, 'right': ...}; markers: {'LHEE': (3|4, N), ...}.
    Returns a dict with best_lag, err_lag0, err_best, comparisons and passed (False when not
    evaluable). with_series adds the per-heel-strike estimates (for review figures only).
    """
    import numpy as np
    out = {'passed': False, 'best_lag': None, 'err_lag0_m_s': None, 'err_best_m_s': None,
           'comparisons_lag0': 0, 'reason': None}
    needed = [s + m for s in 'LR' for m in BELT_MARKERS]
    if cvel is None or any(n not in markers for n in needed):
        out['reason'] = 'not evaluable: cvel or a heel/toe marker is missing'
        return out
    transitions = [(cuts[0, i], cuts[1, i]) for i, label in enumerate(labels) if label[:1] in ('a', 'd')]
    if not transitions:
        out['reason'] = 'not evaluable: no transition interval'
        return out
    velocity, valid = {}, {}
    for name in needed:
        arr = markers[name]
        xyz = arr[:3]
        ok = np.isfinite(xyz).all(axis=0) & ~np.all(xyz == 0.0, axis=0)
        if arr.shape[0] == 4:
            ok &= arr[3] != 0
        v = np.full(xyz.shape, np.nan)
        v[:, 1:-1] = (xyz[:, 2:] - xyz[:, :-2]) * (SOURCE_RATE_HZ / 2.0)
        velocity[name], valid[name] = v, ok
    frames_total = min(v.shape[1] for v in velocity.values())
    times, vectors = [], []
    for side, key in (('L', 'left'), ('R', 'right')):
        for h in np.asarray(hs[key], dtype=int):
            lo, hi = h + BELT_WINDOW[0] - 1, h + BELT_WINDOW[1] - 1  # 0-based velocity indices
            if lo - 1 < 0 or hi + 1 >= frames_total:
                continue
            if not all(valid[side + m][lo - 1:hi + 2].all() for m in BELT_MARKERS):
                continue
            mean = np.mean([velocity[side + m][:, lo:hi + 1].mean(axis=1) for m in BELT_MARKERS], axis=0)
            if any(a - BELT_MARGIN <= h <= b + BELT_MARGIN for a, b in transitions):
                times.append(h + BELT_CENTRE)
                vectors.append(mean)
    if not vectors:
        out['reason'] = 'not evaluable: no heel strike with valid markers near a transition'
        return out
    vectors = np.array(vectors)
    axis = int(np.argmax(np.median(np.abs(vectors), axis=0)))
    speed = np.abs(vectors[:, axis])
    times = np.array(times)
    if with_series:
        out['series'] = {'joint_frame': [int(t) for t in times], 'marker_belt_speed_m_s': [float(v) for v in speed]}

    def error(lag):
        idx = times + lag - 1
        ok = (idx >= 0) & (idx < cvel.size)
        reference = np.full(times.shape, np.nan)
        reference[ok] = cvel[idx[ok]]
        good = np.isfinite(reference) & np.isfinite(speed)
        return (float(np.median(np.abs(reference[good] - speed[good]))) if good.any() else math.inf), int(good.sum())

    err0, n0 = error(0)
    minimum = max(8, math.ceil(n0 / 2))
    out.update(comparisons_lag0=n0, ap_axis_index=axis, min_comparisons=minimum)
    if n0 < 8:
        out['reason'] = f'not evaluable: {n0} comparisons at lag 0'
        return out
    lo_lag, hi_lag = TOLERANCES['belt_clock_lag_search_frames']
    best = (math.inf, 0, 0)
    for lag in range(lo_lag, hi_lag + 1):
        err, n = error(lag)
        if n >= minimum and (err, abs(lag)) < (best[0], abs(best[1])):
            best = (err, lag, n)
    out.update(best_lag=best[1], err_lag0_m_s=err0, err_best_m_s=best[0], comparisons_best=best[2])
    out['passed'] = bool(abs(best[1]) <= TOLERANCES['belt_clock_best_lag_frames_abs_max']
                         and err0 - best[0] <= TOLERANCES['belt_clock_lag0_excess_error_m_s_max'])
    return out


def classify(start, end, cuts, labels, incline):
    """Task-window rule (D-1 option C): exactly one source task interval contains the pair."""
    matches = [i for i in range(cuts.shape[1]) if cuts[0, i] <= start and end <= cuts[1, i]]
    if len(matches) != 1:
        return {'excluded': EXCLUDE_OUTSIDE}
    label = labels[matches[0]]
    if label.startswith(WALK_LABEL_PREFIX):
        speed = float(label[1:].replace('x', '.'))
        task = 'incline_walking' if incline > 0 else 'decline_walking' if incline < 0 else 'level_walking'
        return {'task': task, 'label': label,
                'info': {'incline_deg': incline, 'speed_m_s': speed, 'surface': 'treadmill'}}
    if label in TRANSITION_LABELS:
        sign = 1 if label[0] == 'a' else -1
        return {'task': 'transition', 'label': label,
                'info': {'incline_deg': incline, 'surface': 'treadmill',
                         'transition_phase': 'acceleration' if sign > 0 else 'deceleration',
                         'acceleration_m_s2': sign * float(label[1:].replace('x', '.'))}}
    return {'excluded': f'unsupported task label: {label}'}


# ---------------------------------------------------------------- report helpers
class Checks:
    def __init__(self):
        self.items = {}

    def record(self, check_id, passed, detail=None, example=None):
        item = self.items.setdefault(check_id, {'passed': True, 'evaluated': 0, 'failures': 0, 'examples': []})
        item['evaluated'] += 1
        if detail is not None:
            item['detail'] = detail
        if not passed:
            item['passed'] = False
            item['failures'] += 1
            if example is not None and len(item['examples']) < 5:
                item['examples'].append(example)

    def all_passed(self):
        return bool(self.items) and all(i['passed'] for i in self.items.values())


def chunks_of(parquet_path, columns=None):
    """Yield consecutive 150-row pyarrow tables, independent of row-group layout."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    buffer = None
    for batch in pq.ParquetFile(parquet_path).iter_batches(batch_size=SAMPLES, columns=columns,
                                                          use_threads=False):
        table = pa.Table.from_batches([batch])
        buffer = table if buffer is None else pa.concat_tables([buffer, table])
        while buffer.num_rows >= SAMPLES:
            yield buffer.slice(0, SAMPLES)
            buffer = buffer.slice(SAMPLES)
    if buffer is not None and buffer.num_rows:
        raise AuditInputError(f'{parquet_path}: {buffer.num_rows} trailing rows; not a multiple of 150')


def column(table, name):
    import numpy as np
    return np.asarray(table.column(name).to_numpy(zero_copy_only=False))


def compare_values(checks, check_id, actual, expected, tol, where):
    import numpy as np
    actual = np.asarray(actual, dtype=float)
    a_nan, e_nan = ~np.isfinite(actual), ~np.isfinite(expected)
    mask_ok = bool(np.array_equal(a_nan, e_nan))
    both = ~a_nan & ~e_nan
    err = float(np.max(np.abs(actual[both] - expected[both]))) if both.any() else 0.0
    ok = mask_ok and err <= tol
    checks.record(check_id, ok, example=None if ok else {**where, 'max_abs_error': err, 'mask_equal': mask_ok})
    return err, int(both.sum())


# ---------------------------------------------------------------- main audit
def audit(args, report, checks):
    import numpy as np
    import h5py
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)
    report['versions'] = {'python': sys.version.split()[0], 'numpy': np.__version__,
                          'h5py': h5py.__version__, 'pyarrow': pa.__version__}
    subject, condition = args.subject, args.condition
    if condition not in INCLINES:
        raise AuditInputError(f'unknown treadmill condition {condition}')
    incline = INCLINES[condition]
    pilot = args.pilot_root / subject / condition
    base = args.base_root / subject / condition
    files = {
        'pilot_phase': pilot / 'phase.parquet', 'pilot_ledger': pilot / 'candidate_ledger.jsonl',
        'pilot_source_columns': pilot / 'source_columns.json',
        'pilot_summary': args.pilot_root / 'conversion_summary.json',
        'base_phase': base / 'phase.parquet', 'base_ledger': base / 'candidate_ledger.jsonl',
        'base_summary': args.base_root / 'conversion_summary.json',
    }
    for key, path in files.items():
        if not path.is_file():
            raise AuditInputError(f'missing input {key}: {path}')
    hashes = {key: sha256_file(path) for key, path in files.items()}
    report['inputs'] = {key: {'path': str(path), 'bytes': path.stat().st_size, 'sha256': hashes[key]}
                        for key, path in files.items()}
    source_stat = args.source.stat()
    report['inputs']['source'] = {'path': str(args.source), 'bytes': source_stat.st_size,
                                  'mtime_ns': source_stat.st_mtime_ns}
    if args.skip_source_hash:
        report['inputs']['source']['sha256'] = None
        report['inputs']['source']['sha256_status'] = 'skipped_by_flag (bounded probe); launcher binds it'
    else:
        actual = sha256_file(args.source)
        report['inputs']['source']['sha256'] = actual
        checks.record('source_sha256_matches_expected', actual == args.expected_source_sha256,
                      example={'actual': actual, 'expected': args.expected_source_sha256})

    # ---- receipts agree with the files they describe
    summary = json.loads(files['pilot_summary'].read_text())
    base_summary = json.loads(files['base_summary'].read_text())
    record = [r for r in summary.get('records', []) if (r.get('subject'), r.get('condition')) == (subject, condition)]
    base_record = [r for r in base_summary.get('recordings', [])
                   if (r.get('subject'), r.get('condition')) == (subject, condition)]
    if len(record) != 1 or len(base_record) != 1:
        raise AuditInputError('pilot or base summary has no single record for this subject/condition')
    record, base_record = record[0], base_record[0]
    receipt = {
        'pilot_phase_sha256': record.get('output_sha256') == hashes['pilot_phase'],
        'pilot_ledger_sha256': record.get('ledger_sha256') == hashes['pilot_ledger'],
        'pilot_source_columns_sha256': record.get('source_columns_sha256') == hashes['pilot_source_columns'],
        'base_phase_sha256_in_pilot_summary': record.get('base_output_sha256') == hashes['base_phase'],
        'base_phase_sha256_in_base_summary': base_record.get('sha256') == hashes['base_phase'],
        'ledger_identical_to_base': hashes['pilot_ledger'] == hashes['base_ledger'],
        'pilot_and_base_name_same_source_sha256':
            summary.get('source_sha256') == base_summary.get('source', {}).get('sha256'),
        'pilot_summary_base_summary_sha256': summary.get('base_summary_sha256') == hashes['base_summary'],
    }
    if not args.skip_source_hash:
        receipt['pilot_summary_source_sha256_equals_source'] = \
            summary.get('source_sha256') == report['inputs']['source']['sha256']
    for name, ok in receipt.items():
        checks.record('receipt_' + name, ok)
    snapshot = {}
    for original, expected in (summary.get('code_sha256') or {}).items():
        rel = Path(original).name
        candidates = list((args.pilot_root / 'code').rglob(rel))
        actual = sha256_file(candidates[0]) if len(candidates) == 1 else None
        snapshot[rel] = {'expected': expected, 'snapshot_sha256': actual}
        checks.record('receipt_code_snapshot_matches_summary', actual == expected, example={rel: snapshot[rel]})
    report['code_snapshot'] = snapshot

    # ---- source
    with h5py.File(args.source, 'r', rdcc_nbytes=1024**2) as handle:
        src = read_source(handle, subject, condition)
    channels = src['channels']
    lengths = set(src['lengths'].values())
    frames = next(iter(lengths)) if len(lengths) == 1 else None
    checks.record('clock_joint_channels_share_frame_count', frames is not None,
                  example={'lengths': sorted(lengths)})
    clock = {'joint_frames': frames, 'readme_rate_hz': SOURCE_RATE_HZ,
             'forceplate_lengths': sorted(set(src['forceplate_lengths'].values())),
             'cvel_length': src['cvel_length'], 'cut_points_max': float(np.max(src['cuts'])) if src['cuts'].size else None}
    for side in ('left', 'right'):
        hs, stride = src['hs'][side], src['stride'][side]
        valid = (np.isfinite(hs).all() and np.array_equal(hs, np.floor(hs)) and (np.diff(hs) > 0).all())
        checks.record('events_heel_strikes_integer_increasing', bool(valid), example={'side': side})
        checks.record('clock_stride_time_equals_hs_difference_frames',
                      stride.shape == np.diff(hs).shape and bool(np.array_equal(np.diff(hs), stride)),
                      example={'side': side})
        if frames is not None:
            checks.record('clock_heel_strikes_inside_joint_frames',
                          bool(hs.min() >= 1 and hs.max() <= frames), example={'side': side})
    if src['forceplate_lengths'] and frames is not None:
        checks.record('clock_forceplate_frames_equal_10x_joint_frames',
                      set(src['forceplate_lengths'].values()) == {FORCEPLATE_RATIO * frames},
                      example=clock)
    report['clock'] = clock
    flags = []
    if frames is not None and clock['cut_points_max'] is not None and clock['cut_points_max'] > frames:
        flags.append({'flag': 'cut_points_exceed_joint_frames',
                      'detail': f"max cutPoint {clock['cut_points_max']:.0f} > joint frames {frames}; "
                                f"cvel has {src['cvel_length']} samples. Whether the two clocks agree is tested by "
                                'clock_cut_points_aligned_with_joint_frames.'})
    cuts, labels = src['cuts'], src['labels']
    alignment = belt_clock_alignment(src['hs'], src['markers'], src['cvel'], cuts, labels)
    report['belt_clock_alignment'] = alignment
    checks.record('clock_cut_points_aligned_with_joint_frames', alignment['passed'],
                  detail='cutPoints/cvel clock vs joint/marker clock; see belt_clock_alignment', example=alignment)
    checks.record('events_cut_points_shape', cuts.ndim == 2 and cuts.shape == (2, len(labels)),
                  example={'shape': list(cuts.shape), 'labels': len(labels)})

    # ---- independent event pairs and their classification
    expected_pairs = {}
    for side in ('left', 'right'):
        hs = src['hs'][side].astype(int)
        for a, b in zip(hs[:-1], hs[1:]):
            expected_pairs[(side, int(a), int(b))] = classify(int(a), int(b), cuts, labels, incline)
    frame_pairs = {}
    for side, a, b in expected_pairs:
        frame_pairs.setdefault((a, b), []).append(side)
    ledger = [json.loads(line) for line in files['pilot_ledger'].read_text().splitlines() if line.strip()]
    keys = [(x.get('side'), x.get('start'), x.get('end')) for x in ledger]
    checks.record('ledger_pairs_unique', len(keys) == len(set(keys)))
    checks.record('ledger_accounts_for_every_source_pair', set(keys) == set(expected_pairs),
                  example={'missing': [list(k) for k in sorted(set(expected_pairs) - set(keys))][:5],
                           'extra': [list(map(str, k)) for k in sorted(set(keys) - set(expected_pairs), key=str)][:5]})
    written = {}
    reasons = {}
    for entry in ledger:
        key = (entry.get('side'), entry.get('start'), entry.get('end'))
        expect = expected_pairs.get(key)
        if expect is None:
            continue
        if 'excluded' in entry:
            reason = entry['excluded']
            reasons[reason] = reasons.get(reason, 0) + 1
            checks.record('exclusion_has_explicit_reason', isinstance(reason, str) and bool(reason.strip()),
                          example={'pair': list(key)})
            checks.record('exclusion_reason_matches_independent_rule', expect.get('excluded') == reason,
                          example={'pair': list(key), 'ledger': reason, 'independent': expect})
            checks.record('exclusion_entry_has_no_observation', 'observation_id' not in entry,
                          example={'pair': list(key)})
        else:
            ok = ('excluded' not in expect and entry.get('task') == expect['task']
                  and entry.get('label') == expect['label'] and entry.get('info') == expect['info']
                  and entry.get('status') == 'written_unreviewed')
            checks.record('written_entry_matches_independent_rule', ok,
                          example={'pair': list(key), 'ledger': {k: entry.get(k) for k in ('task', 'label', 'info')},
                                   'independent': expect})
            written[entry.get('observation_id')] = (key, expect)
    checks.record('ledger_observation_ids_unique', len(written) == sum('excluded' not in e for e in ledger))

    # ---- source component mapping
    mapping = json.loads(files['pilot_source_columns'].read_text())
    source_triplets = {(g, n, c) for (g, n), arr in channels.items() for c in range(arr.shape[0])}
    mapped = {}
    for col, info in mapping.items():
        g, n, c1, unit = info.get('group'), info.get('variable'), info.get('matlab_component_1based'), info.get('unit')
        ok = (g in GROUPS and isinstance(c1, int) and unit == GROUPS[g][1]
              and info.get('canonical_frame_verified') is False
              and col == f'source_{GROUPS[g][0]}_{str(n).lower()}_component_{c1 - 1}_{unit}')
        checks.record('component_mapping_consistent', ok, example={'column': col, 'mapping': info})
        if ok:
            mapped[col] = (g, n, c1 - 1)
    checks.record('component_mapping_covers_every_source_component',
                  set(mapped.values()) == source_triplets and len(mapped) == len(mapping),
                  example={'unmapped_source': sorted(map(str, source_triplets - set(mapped.values())))[:5]})
    checks.record('component_count_as_expected', len(source_triplets) == args.expected_component_count
                  and len(mapping) == args.expected_component_count,
                  example={'source': len(source_triplets), 'mapping': len(mapping),
                           'expected': args.expected_component_count})

    # ---- schemas
    pilot_schema = pq.read_schema(files['pilot_phase'])
    base_schema = pq.read_schema(files['base_phase'])
    prior = list(base_schema.names)
    added = [n for n in pilot_schema.names if n not in prior]
    checks.record('schema_prior_columns_present_same_type',
                  all(n in pilot_schema.names and pilot_schema.field(n).type == base_schema.field(n).type for n in prior))
    checks.record('schema_added_columns_equal_mapping', set(added) == set(mapping),
                  example={'added_not_mapped': sorted(set(added) - set(mapping))[:5],
                           'mapped_not_added': sorted(set(mapping) - set(added))[:5]})

    # ---- per observation
    seen = set()
    errors = {'source_components': 0.0, 'prior_angles_rad': 0.0, 'prior_velocities_rad_s': 0.0}
    finite_counts = {'source_components': 0, 'prior_angles_rad': 0, 'prior_velocities_rad_s': 0}
    stats = {'observations': 0, 'by_side': {'left': 0, 'right': 0}, 'by_task': {},
             'side_discriminating_observations': 0, 'frame_pairs_shared_by_both_sides': 0,
             'durations_s': []}
    zero_triples = {}
    ankle_alternate = {}
    pi180 = math.pi / 180
    string_cols = [n for n in prior if pa.types.is_string(base_schema.field(n).type)
                   or pa.types.is_large_string(base_schema.field(n).type)]
    for pilot_chunk, base_chunk in zip_strict(chunks_of(files['pilot_phase']), chunks_of(files['base_phase'])):
        if peak_rss_mib() > args.max_rss_mib:
            raise RssGuard(f'peak RSS {peak_rss_mib():.1f} MiB above guard {args.max_rss_mib} MiB')
        ids = pilot_chunk.column('observation_id').to_pylist()
        oid = ids[0]
        checks.record('phase_150_contiguous_rows_per_observation', len(set(ids)) == 1 and oid not in seen,
                      example={'observation_id': oid})
        seen.add(oid)
        stats['observations'] += 1
        # prior columns preserved bit for bit
        for name in prior:
            if name in string_cols:
                same = pilot_chunk.column(name).to_pylist() == base_chunk.column(name).to_pylist()
            else:
                a = np.ascontiguousarray(column(pilot_chunk, name), dtype=np.float64)
                b = np.ascontiguousarray(column(base_chunk, name), dtype=np.float64)
                same = bool(np.array_equal(a.view(np.uint64), b.view(np.uint64)))
            checks.record('prior_column_bitwise_equal_to_base', same, example={'observation_id': oid, 'column': name})
        if oid not in written:
            checks.record('observation_is_written_ledger_pair', False, example={'observation_id': oid})
            continue
        (side, start, end), expect = written[oid]
        checks.record('observation_is_written_ledger_pair', True)
        stats['by_side'][side] += 1
        stats['by_task'][expect['task']] = stats['by_task'].get(expect['task'], 0) + 1
        stats['durations_s'].append((end - start) / SOURCE_RATE_HZ)
        if len(frame_pairs[(start, end)]) > 1:
            stats['frame_pairs_shared_by_both_sides'] += 1
        recording = f'um21:Streaming/{subject}/Tread/{condition}'
        identity = {'subject': f'UM21_{subject}', 'source_recording_id': recording,
                    'observation_id': f'{recording}:{side}:frames:{start}:{end}', 'reference_side': side,
                    'observation_type': 'individual_cycle', 'task': expect['task'], 'task_id': expect['label'],
                    'step': f'{recording}:{side}:frames:{start}:{end}'}
        for name, value in identity.items():
            checks.record('identity_' + name, pilot_chunk.column(name).to_pylist() == [value] * SAMPLES,
                          example={'observation_id': oid, 'expected': value})
        infos = set(pilot_chunk.column('task_info').to_pylist())
        checks.record('identity_task_info', len(infos) == 1 and json.loads(next(iter(infos))) == expect['info'],
                      example={'observation_id': oid})
        # clock and phase
        phase = column(pilot_chunk, 'phase_ipsi')
        k = np.arange(SAMPLES)
        checks.record('phase_inclusive_0_to_100', bool(phase[0] == 0.0 and phase[-1] == 100.0 and
                      np.max(np.abs(phase - 100.0 * k / (SAMPLES - 1))) <= TOLERANCES['phase_percent_abs']),
                      example={'observation_id': oid})
        times = time_grid(start, end)
        t = column(pilot_chunk, 'time_s')
        checks.record('clock_time_s_elapsed_frames_at_100hz', bool(t[0] == 0.0 and
                      np.max(np.abs(t - times)) <= TOLERANCES['clock_s_abs']), example={'observation_id': oid})
        s0, s1 = column(pilot_chunk, 'source_start_time_s'), column(pilot_chunk, 'source_end_time_s')
        checks.record('clock_source_start_end_time_s', bool(
            np.all(np.abs(s0 - (start - 1) / SOURCE_RATE_HZ) <= TOLERANCES['clock_s_abs']) and
            np.all(np.abs(s1 - (end - 1) / SOURCE_RATE_HZ) <= TOLERANCES['clock_s_abs']) and
            np.all(np.abs((s1 - s0) - t[-1]) <= 10 * TOLERANCES['clock_s_abs'])), example={'observation_id': oid})
        # source windows (frames are 1-based and inclusive)
        window = {key: arr[:, start - 1:end] for key, arr in channels.items()}
        for col, (g, n, c) in mapped.items():
            err, cnt = compare_values(checks, 'source_component_values_and_mask', column(pilot_chunk, col),
                                      resample_linear(window[(g, n)][c]), TOLERANCES['source_component_abs'],
                                      {'observation_id': oid, 'column': col})
            errors['source_components'] = max(errors['source_components'], err)
            finite_counts['source_components'] += cnt
        # prior columns against the documented base recipe (source signs, rule C not applied)
        ang = lambda name: resample_linear(window[('jointAngles', name)][0]) * pi180  # noqa: E731
        pelvis = ang('RPelvisAngles')
        expected_prior = {'pelvis_sagittal_angle_rad': pelvis}
        legs = {'ipsi': 'R' if side == 'right' else 'L', 'contra': 'L' if side == 'right' else 'R'}
        for role, leg in legs.items():
            hip, knee, ankle = ang(leg + 'HipAngles'), ang(leg + 'KneeAngles'), ang(leg + 'AnkleAngles')
            expected_prior.update({
                f'hip_flexion_angle_{role}_rad': hip, f'knee_flexion_angle_{role}_rad': knee,
                f'thigh_sagittal_angle_{role}_rad': pelvis + hip,
                f'shank_sagittal_angle_{role}_rad': pelvis + hip - knee,
                f'source_ankle_sagittal_angle_{role}_rad': ankle,
                f'ankle_dorsiflexion_angle_{role}_rad': np.full(SAMPLES, np.nan)})
            for joint, values in (('hip_flexion', hip), ('knee_flexion', knee)):
                vel = finite_difference(values, times)
                err, cnt = compare_values(checks, 'prior_velocity_values_and_mask',
                                          column(pilot_chunk, f'{joint}_velocity_{role}_rad_s'), vel,
                                          TOLERANCES['velocity_rad_s_abs'], {'observation_id': oid, 'role': role})
                errors['prior_velocities_rad_s'] = max(errors['prior_velocities_rad_s'], err)
                finite_counts['prior_velocities_rad_s'] += cnt
        for name, values in expected_prior.items():
            err, cnt = compare_values(checks, 'prior_angle_values_and_mask', column(pilot_chunk, name), values,
                                      TOLERANCES['angle_rad_abs'], {'observation_id': oid, 'column': name})
            errors['prior_angles_rad'] = max(errors['prior_angles_rad'], err)
            finite_counts['prior_angles_rad'] += cnt
        # The ipsi/contra value checks above only discriminate the physical side when the
        # two legs' source hip windows differ; count the observations where they do.
        own, opposite = ang(legs['ipsi'] + 'HipAngles'), ang(legs['contra'] + 'HipAngles')
        both = np.isfinite(own) & np.isfinite(opposite)
        if both.any() and np.max(np.abs(own[both] - opposite[both])) > 1e-6:
            stats['side_discriminating_observations'] += 1
        # flags: zero-filled triples and ankle alternate branch inside the window
        for (g, n), arr in window.items():
            if g != 'jointAngles' or arr.shape[0] != 3:
                continue
            zeros = int(np.sum(np.all(arr == 0.0, axis=0)))
            if zeros:
                zero_triples.setdefault(n, {'frames': 0, 'observations': 0})
                zero_triples[n]['frames'] += zeros
                zero_triples[n]['observations'] += 1
            if n.endswith('AnkleAngles'):
                alt = int(np.sum(np.abs(arr[1]) > 90.0))
                if alt:
                    ankle_alternate.setdefault(n, {'frames': 0, 'observations': 0})
                    ankle_alternate[n]['frames'] += alt
                    ankle_alternate[n]['observations'] += 1
    checks.record('every_written_pair_has_an_observation', seen >= set(written),
                  example={'missing': sorted(set(written) - seen)[:5]})
    checks.record('observation_count_matches_pilot_summary',
                  record.get('observations_checked') == stats['observations'] == len(written),
                  example={'summary': record.get('observations_checked'), 'parquet': stats['observations'],
                           'ledger_written': len(written)})
    checks.record('side_discriminating_data_present', stats['side_discriminating_observations'] == stats['observations'],
                  example={'discriminating': stats['side_discriminating_observations'],
                           'observations': stats['observations']})
    durations = stats.pop('durations_s')
    median = float(np.median(durations)) if durations else None
    checks.record('clock_stride_duration_screen', median is not None and
                  STRIDE_SECONDS_SCREEN[0] <= median <= STRIDE_SECONDS_SCREEN[1],
                  detail=f'median exported stride {median} s within {STRIDE_SECONDS_SCREEN} s')
    stats['stride_seconds'] = {'median': median, 'min': min(durations) if durations else None,
                               'max': max(durations) if durations else None}
    stats['excluded_pairs'] = sum(reasons.values())
    stats['source_pairs'] = len(expected_pairs)
    stats['exclusion_reasons'] = reasons
    stats['source_component_columns'] = len(mapped)
    report['counts'] = stats
    report['max_abs_error'] = errors
    report['finite_values_checked'] = finite_counts
    if zero_triples:
        flags.append({'flag': 'exact_zero_joint_angle_triples_in_exported_windows', 'detail': zero_triples})
    if ankle_alternate:
        flags.append({'flag': 'ankle_alternate_branch_frames_in_exported_windows', 'detail': ankle_alternate})
    report['flags'] = flags


def zip_strict(a, b):
    sentinel = object()
    a, b = iter(a), iter(b)
    while True:
        x, y = next(a, sentinel), next(b, sentinel)
        if x is sentinel and y is sentinel:
            return
        if x is sentinel or y is sentinel:
            raise AuditInputError('pilot and base phase files have different row counts')
        yield x, y


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--source', type=Path, required=True, help='Streaming.mat (HDF5)')
    parser.add_argument('--pilot-root', type=Path, required=True)
    parser.add_argument('--base-root', type=Path, required=True)
    parser.add_argument('--subject', required=True)
    parser.add_argument('--condition', required=True)
    parser.add_argument('--output-dir', type=Path, required=True, help='new directory; must not exist')
    hash_group = parser.add_mutually_exclusive_group(required=True)
    hash_group.add_argument('--expected-source-sha256')
    hash_group.add_argument('--skip-source-hash', action='store_true',
                            help='bounded probe only: record size/mtime, not the full-file sha256')
    parser.add_argument('--expected-component-count', type=int, default=84)
    parser.add_argument('--address-space-mib', type=int, default=ADDRESS_SPACE_MIB_MAX)
    parser.add_argument('--max-rss-mib', type=float, default=300.0, help='self-guard; stop above this peak RSS')
    return parser.parse_args(argv)


def main(argv=None):
    started = time.time()
    try:
        args = parse_args(argv)
        limit = set_address_space(args.address_space_mib)
    except AuditInputError as error:
        print(f'audit_um21_tread_pilot: {error}', file=sys.stderr)
        return 2
    if args.expected_source_sha256 is not None and not re.fullmatch('[0-9a-f]{64}', args.expected_source_sha256):
        print('audit_um21_tread_pilot: expected sha256 must be 64 lowercase hex', file=sys.stderr)
        return 2
    try:
        args.output_dir.mkdir(parents=False, exist_ok=False)
    except OSError as error:
        print(f'audit_um21_tread_pilot: output directory not created: {error}', file=sys.stderr)
        return 2
    try:
        os.nice(max(0, 19 - os.nice(0)))
    except OSError:
        pass
    script = Path(__file__).resolve()
    report = {'schema': SCHEMA, 'task_id': 'UM21-T02', 'status': 'running', 'scientific_approval': False,
              'subject': args.subject, 'condition': args.condition, 'argv': sys.argv[1:] if argv is None else argv,
              'audit_script': {'path': str(script), 'sha256': sha256_file(script)},
              'tolerances_stated_in_advance': TOLERANCES,
              'expectations': {
                  'side': 'LHS pairs -> left, RHS pairs -> right; ipsi = that leg, contra = the other leg',
                  'frames': 'source frames are 1-based; window = frames start..end inclusive',
                  'clock': 'source_start_time_s = (start-1)/100, source_end_time_s = (end-1)/100, '
                           'time_s[k] = k*(end-start)/(149*100)',
                  'prior_recipe': 'pelvis = RPelvisAngles c1; hip/knee/ankle = leg c1; thigh = pelvis + hip; '
                                  'shank = pelvis + hip - knee; deg x pi/180; ankle_dorsiflexion all NaN; '
                                  'velocities = finite difference over time_s (source signs; D-UM21-C03-1 rule C '
                                  'not applied in this staging output)',
                  'components': 'every component of jointAngles/Forces/Moments/Powers, source units, resampled',
                  'exclusions': 'task-window rule: exactly one cutPoints interval [a, b] with a <= start and end <= b',
              },
              'resources': {'rlimit_as_bytes': list(limit), 'thread_env': {k: os.environ.get(k) for k in THREAD_ENV}}}
    checks = Checks()
    code = 0
    try:
        audit(args, report, checks)
        code = 0 if checks.all_passed() else 1
        report['status'] = 'pass' if code == 0 else 'fail'
    except RssGuard as error:
        report.update(status='stopped_rss_guard', error=str(error))
        code = 4
    except (AuditInputError, OSError, KeyError, ValueError) as error:
        report.update(status='input_error', error=f'{type(error).__name__}: {error}')
        code = 2
    except Exception as error:  # still write the report; never exit 0
        report.update(status='error', error=f'{type(error).__name__}: {error}')
        code = 2
    loaded = sorted(m for m in sys.modules if m not in OWN_MODULES and (
        any(marker in m for marker in PRODUCER_MODULE_MARKERS) or m.startswith('contributor_tools.')))
    checks.record('no_producer_module_loaded', not loaded, example={'modules': loaded})
    if loaded and code == 0:
        code, report['status'] = 1, 'fail'
    report['checks'] = checks.items
    report['binding_complete'] = report.get('inputs', {}).get('source', {}).get('sha256') is not None
    report['resources'].update({'peak_rss_mib': round(peak_rss_mib(), 1), 'wall_seconds': round(time.time() - started, 2),
                                'max_rss_guard_mib': args.max_rss_mib})
    target = args.output_dir / 'audit_report.json'
    try:  # serialise before opening: a non-finite value must not leave an empty report behind
        text = json.dumps(report, indent=2, allow_nan=False, default=str) + '\n'
    except (TypeError, ValueError) as error:
        print(f'audit_um21_tread_pilot: report not serialisable ({error}); nothing written', file=sys.stderr)
        return 2
    with open(target, 'x') as stream:
        stream.write(text)
    print(json.dumps({'status': report['status'], 'report': str(target),
                      'failed_checks': [k for k, v in checks.items.items() if not v['passed']],
                      'flags': [f['flag'] for f in report.get('flags', [])],
                      'peak_rss_mib': report['resources']['peak_rss_mib']}))
    return code


if __name__ == '__main__':
    sys.exit(main())
