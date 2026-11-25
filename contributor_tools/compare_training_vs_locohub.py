"""Compare the ankle training files (es_prepared) with the LocoHub 2021 rebuilds, column by column.

Purpose
  Say how much each signal that the training code reads changes between the file it was trained on and the rebuilt LocoHub
  data. This is a descriptive comparison: the reporting sizes below only decide which differences are counted as "larger
  than a stated size". They are not quality limits, and nothing here approves or rejects either file.

Two comparisons
  gt21  training time file (gtech_2021_time.parquet, 200 Hz, one reference leg per row)
        vs LocoHub GT21 export time.parquet (one continuous 200 Hz observation per recording, left and right columns).
        Current export root per participant: gt21_rb07_export_<ID> if its run_summary.json exists, else
        gt21_rb06_export_<ID>_r2.
  um21  training time file (umich_2021_time.parquet, 200 Hz, right leg)
        vs LocoHub UM21 package v4 phase file (full_phase.parquet; phase only, no time table, no force).
        The training series is read at the source-time positions of every LocoHub stride (see Matching).

Matching (nothing is assumed beyond what is written here; every choice is logged in alignment.csv)
  Participant: the AB<number> token of the subject name (the training files and LocoHub prefix names differently).
  Recording (gt21): a training recording_id is "<subject>|<collection_id>" or "<subject>|<first collection_id>+<k>" for cuts
    that the training code joined. The collection_id (text before "+") matches a LocoHub recording name (the last part of
    source_recording_id, "<subject>/<mode>/<recording>") when the two are equal or one is the other plus "_<more>". The
    pairing is a candidate list; the reported pair is the one that aligns best (below). Unpaired recordings are listed.
  Recording (um21): a training collection_id "Tread_<incline>_<speed>_seg<NN>" belongs to LocoHub source_recording_id
    "um21:Streaming/<subject>/Tread/<incline>". Run, Wtr and Stair collections are not in package v4 and are listed as unpaired.
  Reference leg (gt21): the training file does not keep the reference leg. Both LocoHub legs are tried; the leg whose
    ankle moment fits best is used, and the other leg's misfit is logged. um21: the converter writes reference_leg:right for
    every row, so the right-leg strides are used (option --um21-side).
  Time (gt21): both clocks are 200 Hz but their origins are not assumed equal. The ankle moment of the training recording
    is cross-correlated with the LocoHub moment on a uniform 5 ms grid (FFT), the best three peaks are refined by +-2 samples
    on the RMS difference, and the lowest RMS (with the sign +1 or -1, logged) fixes one time offset per recording. LocoHub
    values are then read at the training time stamps plus that offset (a sample is taken exactly when a LocoHub sample
    lies within 1 microsecond, otherwise linear between neighbours; missing if either neighbour is missing).
  Time (um21): the training time axis restarts at 0 at the first frame of each speed segment (convert_umich_time_to_parquet.m:
    time_s = (frame - segment_start) / 100 for 100 Hz source frames; 1-based frames). Segment start frames are not stored in
    the training file, so each segment's start frame is found by cross-correlating its right ankle moment (100 Hz samples)
    with a frame-domain series rebuilt from the LocoHub right strides (stride observation ids carry the source frames,
    "...:frames:<a>:<b>"). A stride is compared when its whole window lies inside the segment: LocoHub phase sample j
    (0..149) sits at source frame a + j (b - a) / 149, i.e. segment time ((a - start) + j (b - a) / 149) / 100 s.
  Alignment guard: a pairing counts only if the best RMS moment difference is at most --align-rms-tol (default 0.10 Nm/kg)
    over at least max(100, 30 percent of the training moment samples) samples. Others are listed as alignment_failed and
    are not in the statistics. This tolerance only decides whether two recordings are the same recording.

Per column and dataset, per participant, and per participant and task (task = the training file's own label)
  n_positions     compared positions (rows inside the LocoHub span for gt21; strides x 150 for um21)
  n_matched       positions where both values are present
  coverage_his / coverage_lh   fraction of n_positions with a value in the training / LocoHub series
  n_his_only / n_lh_only        positions present in only one series
  bias            mean of (training - LocoHub), in the report unit
  rms             root mean square of that difference
  p95_abs         95th percentile of |difference| (exact per participant and task; dataset level from a histogram of
                  bin width size/200, flagged p95_exact = False; inf if the 95th percentile exceeds 50 x size)
  corr            Pearson correlation of the two series
  frac_exceed     fraction of matched positions with |difference| > reporting size

Column mapping, unit conversion, signs and unmapped columns are written in COLUMN_MAPS and HIS_ROLES below and are copied
into summary.json.

Run only through ``python3 -m contributor_tools.guarded_launcher run SPEC.json`` (spec subcommand below). Streaming: pyarrow
iter_batches(4096, use_threads=False); one participant at a time; stops above --rss-cap-mib (default 290) resident. Writes a new
output directory (docs/quality/audits/training-compare-*): summary.json, comparison.csv, alignment.csv, unmatched.csv.
Unreviewed; no scientific approval is claimed.
"""
import argparse
import csv
import hashlib
import json
import math
import os
import re
import resource
import sys
import time
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
os.environ.setdefault('ARROW_DEFAULT_MEMORY_POOL', 'system')
ROOT = Path(__file__).resolve().parents[1]
import numpy as np  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.compute as pc  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

pa.set_cpu_count(1)
pa.set_io_thread_count(1)

SCHEMA_ID = 'locohub.training_compare/1'
DT = 0.005                                  # both training files and the GT21 time table are 200 Hz
RAD2DEG = 180.0 / math.pi
BATCH_ROWS = 4096
HIST_BINS = 10000
HIST_WIDTH_DIVISOR = 200.0

HIS_DIR_DEFAULT = '/mnt/s/workspace_docs/energy shaping ml/esml_research/LocoHub/es_prepared'
LH_BASE_DEFAULT = 'converted_datasets/reconversion_v2'
UM21_PHASE_DEFAULT = 'converted_datasets/reconversion_v2/um21_r01_package_v4/full_phase.parquet'
UM21_MANIFEST_DEFAULT = 'converted_datasets/reconversion_v2/um21_r01_package_v4/manifest.json'
HIS_FILES = {'gt21': 'gtech_2021_time.parquet', 'um21': 'umich_2021_time.parquet'}
CODE = ('contributor_tools/compare_training_vs_locohub.py',)

# ------------------------------------------------------------------------------------------------ column mapping
# Report values = scale x raw (+ lh_offset for LocoHub). his = column in the training file. lh = LocoHub column with {R}
# = left/right (GT21 time table) or ipsi (phase table). his_flag = training flag column that must be true for a value to
# count (the training file stores 0.0 where CoP is not measured and VGRF stays finite where force is not measured).
# sign is +1 for every pair: both sides use ankle dorsiflexion positive, foot minus shank, internal moment; a sign
# difference is not assumed away, it shows up in bias/corr and in the alignment log (sign_of_best_fit).


@dataclass(frozen=True)
class ColumnMap:
    name: str
    his: str
    lh: str
    unit: str
    scale: float
    size: float
    lh_offset: float = 0.0
    sign: float = 1.0
    his_flag: str = ''
    note: str = ''


def column_maps(cop_shift_m=0.100):
    return (
        ColumnMap('ankle_angle', 'ankle_dorsiflexion_angle_ipsi_rad', 'ankle_dorsiflexion_angle_{R}_rad', 'deg', RAD2DEG, 2.0),
        ColumnMap('shank_angle', 'shank_sagittal_angle_ipsi_rad', 'shank_sagittal_angle_{R}_rad', 'deg', RAD2DEG, 2.0,
                  note='training UM21 values include its own -2 x pelvis tilt correction; training GT21 values were built on the old pelvis tilt'),
        ColumnMap('foot_angle', 'foot_sagittal_angle_ipsi_rad', 'foot_sagittal_angle_{R}_rad', 'deg', RAD2DEG, 2.0,
                  note='same note as shank_angle; angle zero differs (static pose vs gravity)'),
        ColumnMap('ankle_velocity', 'dtheta_raw', 'ankle_dorsiflexion_velocity_{R}_rad_s', 'deg/s', RAD2DEG, 20.0,
                  note='training value is its own backward difference of the sampled angle; LocoHub value is the source or stride slope; a method difference, not a data error'),
        ColumnMap('ankle_moment', 'ankle_dorsiflexion_moment_ipsi_Nm_kg', 'ankle_dorsiflexion_moment_{R}_Nm_kg', 'Nm/kg', 1.0, 0.05),
        ColumnMap('vertical_force', 'grf_vertical_ipsi_BW', 'grf_vertical_{R}_BW', 'BW', 1.0, 0.05, his_flag='fz_measured',
                  note='training GT21 force is its own sidecar; LocoHub UM21 package has no force (reported as unavailable)'),
        ColumnMap('cop_anterior', 'cop_anterior_ipsi_m', 'cop_anterior_{R}_m', 'm', 1.0, 0.02, lh_offset=float(cop_shift_m), his_flag='cop_ok',
                  note='training: m from the ankle joint centre along the foot axis; LocoHub: origin 100 mm forward of the ankle joint centre; '
                       'LocoHub + shift is compared, so bias also contains any difference between the two ankle-centre definitions'),
    )


HIS_READ_KEYS = ('recording_id', 'subject', 'task', 'time_s')
# Training columns that are not compared, and why (copied to summary.json).
HIS_ROLES = {
    'recording_id': 'key (subject | collection_id, joins marked +k)', 'subject': 'key', 'dataset': 'constant label',
    'task': 'group label (reporting only)', 'task_id': 'label, not read', 'task_info': 'label text, not read',
    'step': 'training step counter, not read', 'time_s': 'time key', 'dt_s': 'constant 0.005, not read',
    'dpsi_raw': 'training backward difference of shank angle; LocoHub GT21 and UM21 have no shank speed column',
    'dphi_raw': 'training backward difference of foot angle; LocoHub has no foot speed column',
    'dtheta_f15': 'training 15 Hz low-pass of dtheta_raw (training-only derived signal)',
    'dpsi_f15': 'training 15 Hz low-pass of dpsi_raw (training-only derived signal)',
    'fz_measured': 'validity flag of vertical_force', 'cop_ok': 'validity flag of cop_anterior',
    'swing': 'training mask', 'wc_weight': 'training weight', 'window_ok': 'training mask', 'loss_mask': 'training mask',
}

# ------------------------------------------------------------------------------------------------ small helpers


def _release_memory():
    """Give freed heap back to the system between participants (peak resident is checked against a cap)."""
    import ctypes
    import gc
    gc.collect()
    try:
        ctypes.CDLL('libc.so.6').malloc_trim(0)
    except (OSError, AttributeError):
        pass


def peak_rss_mib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def check_rss(cap_mib, where):
    p = peak_rss_mib()
    if p > cap_mib:
        raise MemoryError(f'peak resident {p:.0f} MiB above the {cap_mib:.0f} MiB cap at {where}')
    return p


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 22), b''):
            h.update(chunk)
    return h.hexdigest()


def norm_subject(name):
    m = re.search(r'AB\d+', str(name))
    return m.group(0) if m else str(name)


def lh_name(cmap, role):
    return cmap.lh.format(R=role)


def interp_nodes(t, y, tq, tol=1e-6):
    """Values of y(t) at tq. NaN outside [t[0], t[-1]]. A query within tol of a sample takes that sample (even if a neighbour
    is missing); otherwise linear between the two neighbours, NaN if either is missing."""
    t, y, tq = np.asarray(t, float), np.asarray(y, float), np.asarray(tq, float)
    out = np.full(tq.shape, np.nan)
    if len(t) < 2:
        return out
    ok = (tq >= t[0] - tol) & (tq <= t[-1] + tol)
    if not ok.any():
        return out
    q = tq[ok]
    j = np.clip(np.searchsorted(t, q, side='right') - 1, 0, len(t) - 2)
    w = (q - t[j]) / (t[j + 1] - t[j])
    with np.errstate(invalid='ignore'):
        v = y[j] * (1.0 - w) + y[j + 1] * w
    v = np.where(np.abs(q - t[j + 1]) <= tol, y[j + 1], v)
    v = np.where(np.abs(q - t[j]) <= tol, y[j], v)
    out[ok] = v
    return out


def uniform_grid(t, y, t0, dt=DT, max_len=5_000_000):
    """y placed on the grid t0 + k dt (nearest k); NaN where no sample. Later samples overwrite earlier ones."""
    idx = np.rint((np.asarray(t, float) - t0) / dt).astype(np.int64)
    if len(idx) == 0 or idx.min() < 0:
        raise ValueError('time stamps before the grid origin')
    n = int(idx.max()) + 1
    if n > max_len:
        raise ValueError(f'time span of {n} samples is longer than the {max_len} limit')
    arr = np.full(n, np.nan)
    arr[idx] = y
    return arr


# ------------------------------------------------------------------------------------------------ alignment
def _top_lags(xs, ys, top=3, min_sep=5):
    """Lags k (x index j matches y index j + k) with the largest |cross-correlation|, at least min_sep apart."""
    nx, ny = len(xs), len(ys)
    n = 1
    while n < nx + ny:
        n <<= 1
    if n > (1 << 22):
        raise ValueError('recording too long for the FFT alignment')
    c = np.fft.irfft(np.fft.rfft(ys, n) * np.conj(np.fft.rfft(xs, n)), n)
    lags = np.arange(-(nx - 1), ny)
    vals = np.abs(c[lags % n])
    k = min(len(vals), 400)
    cand = np.argpartition(-vals, k - 1)[:k]
    cand = cand[np.argsort(-vals[cand])]
    chosen = []
    for i in cand:
        if all(abs(int(lags[i]) - c0) >= min_sep for c0 in chosen):
            chosen.append(int(lags[i]))
            if len(chosen) == top:
                break
    return chosen


def score_lag(x, y, lag):
    """(n, rms with sign +1, rms with sign -1) of x[j] vs y[j + lag] over positions where both are finite."""
    j0, j1 = max(0, -lag), min(len(x), len(y) - lag)
    if j1 <= j0:
        return 0, math.inf, math.inf
    a, b = x[j0:j1], y[j0 + lag:j1 + lag]
    m = np.isfinite(a) & np.isfinite(b)
    n = int(m.sum())
    if n == 0:
        return 0, math.inf, math.inf
    a, b = a[m], b[m]
    return n, float(np.sqrt(np.mean((a - b) ** 2))), float(np.sqrt(np.mean((a + b) ** 2)))


def _top_lags_rms(x, y, min_n, top=3, min_sep=5):
    """Lags with the smallest RMS difference (either sign) over the finite overlap, for all lags at once by FFT.
    Sums of squares inside the overlap use masks, so gaps in either series are handled exactly (up to rounding)."""
    nx, ny = len(x), len(y)
    n = 1
    while n < nx + ny:
        n <<= 1
    if n > (1 << 22):
        raise ValueError('recording too long for the FFT alignment')
    mx, my = np.isfinite(x).astype(float), np.isfinite(y).astype(float)
    x0, y0 = np.where(mx > 0, x, 0.0), np.where(my > 0, y, 0.0)

    def xc(a, b):                       # c[lag] = sum_j a[j] b[j + lag]
        return np.fft.irfft(np.fft.rfft(b, n) * np.conj(np.fft.rfft(a, n)), n)
    lags = np.arange(-(nx - 1), ny)
    ix = lags % n
    cnt = np.rint(xc(mx, my)[ix])
    sxx = xc(x0 ** 2, my)[ix]           # sum of x^2 where y also finite
    syy = xc(mx, y0 ** 2)[ix]
    cxy = xc(x0, y0)[ix]
    chosen = []
    for sign in (1.0, -1.0):
        with np.errstate(invalid='ignore', divide='ignore'):
            rms = np.sqrt(np.maximum(sxx + syy - 2.0 * sign * cxy, 0.0) / cnt)
        rms = np.where(cnt >= min_n, rms, np.inf)
        k = min(len(rms), 400)
        cand = np.argpartition(rms, k - 1)[:k]
        cand = cand[np.argsort(rms[cand])]
        got = []
        for i in cand:
            if not np.isfinite(rms[i]):
                break
            if all(abs(int(lags[i]) - c0) >= min_sep for c0 in got):
                got.append(int(lags[i]))
                if len(got) == top:
                    break
        chosen += [g for g in got if g not in chosen]
    return chosen


def best_alignment(x, y, min_n, top=3, refine=2):
    """Best (lag, sign, rms, n) of series x against y, or None. Needs at least min_n samples in the overlap."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    fx, fy = np.isfinite(x), np.isfinite(y)
    if fx.sum() < min_n or fy.sum() < min_n:
        return None
    best = None
    for lag0 in _top_lags_rms(x, y, min_n, top):
        for lag in range(lag0 - refine, lag0 + refine + 1):
            n, rp, rn = score_lag(x, y, lag)
            if n < min_n:
                continue
            for sign, r in ((1, rp), (-1, rn)):
                if best is None or r < best['rms']:
                    best = {'lag': lag, 'sign': sign, 'rms': r, 'n': n}
    return best


# ------------------------------------------------------------------------------------------------ statistics
class AbsHist:
    def __init__(self, size):
        self.width = size / HIST_WIDTH_DIVISOR
        self.counts = np.zeros(HIST_BINS + 1, np.int64)

    def add(self, ad):
        idx = np.minimum((ad / self.width).astype(np.int64), HIST_BINS)
        self.counts += np.bincount(idx, minlength=HIST_BINS + 1)

    def p95(self):
        total = int(self.counts.sum())
        if total == 0:
            return float('nan')
        target = 0.95 * total
        cum = np.cumsum(self.counts)
        i = int(np.searchsorted(cum, target))
        if i >= HIST_BINS:
            return math.inf
        prev = int(cum[i - 1]) if i else 0
        return (i + (target - prev) / int(self.counts[i])) * self.width


class Acc:
    """Running difference statistics of (training x, LocoHub y), exact moments by Chan's merge."""

    def __init__(self, size, keep_abs=False, hist=False):
        self.size = size
        self.n_pos = self.n_his = self.n_lh = self.n = self.n_exceed = 0
        self.mx = self.my = self.md = self.M2x = self.M2y = self.M2d = self.Cxy = 0.0
        self.hist = AbsHist(size) if hist else None
        self.abs_parts = [] if keep_abs else None

    def add(self, x, y):
        x, y = np.asarray(x, float), np.asarray(y, float)
        fx, fy = np.isfinite(x), np.isfinite(y)
        both = fx & fy
        self.n_pos += len(x)
        self.n_his += int(fx.sum())
        self.n_lh += int(fy.sum())
        k = int(both.sum())
        if k == 0:
            return
        xb, yb = x[both], y[both]
        d = xb - yb
        ad = np.abs(d)
        self.n_exceed += int((ad > self.size).sum())
        mx2, my2, md2 = xb.mean(), yb.mean(), d.mean()
        dx, dy, dd = xb - mx2, yb - my2, d - md2
        m2x, m2y, m2d, c2 = float(dx @ dx), float(dy @ dy), float(dd @ dd), float(dx @ dy)
        n1, n = self.n, self.n + k
        ex, ey, ed = mx2 - self.mx, my2 - self.my, md2 - self.md
        w = n1 * k / n
        self.M2x += m2x + ex * ex * w
        self.M2y += m2y + ey * ey * w
        self.M2d += m2d + ed * ed * w
        self.Cxy += c2 + ex * ey * w
        self.mx += ex * k / n
        self.my += ey * k / n
        self.md += ed * k / n
        self.n = n
        if self.hist is not None:
            self.hist.add(ad)
        if self.abs_parts is not None:
            self.abs_parts.append(ad)

    def row(self):
        n = self.n
        nan = float('nan')
        corr = nan
        if n > 1 and self.M2x > 0 and self.M2y > 0:
            corr = self.Cxy / math.sqrt(self.M2x * self.M2y)
        if self.abs_parts is not None:
            p95 = float(np.percentile(np.concatenate(self.abs_parts), 95)) if n else nan
            exact = True
        else:
            p95 = self.hist.p95() if self.hist is not None else nan
            exact = False
        return {'n_positions': self.n_pos, 'n_matched': n,
                'coverage_his': self.n_his / self.n_pos if self.n_pos else nan,
                'coverage_lh': self.n_lh / self.n_pos if self.n_pos else nan,
                'n_his_only': self.n_his - n, 'n_lh_only': self.n_lh - n,
                'bias': self.md if n else nan,
                'rms': math.sqrt(self.M2d / n + self.md ** 2) if n else nan,
                'p95_abs': p95, 'p95_exact': exact, 'corr': corr,
                'frac_exceed': self.n_exceed / n if n else nan,
                'his_mean': self.mx if n else nan, 'lh_mean': self.my if n else nan}


ROW_FIELDS = ['dataset', 'scope', 'subject', 'task', 'column', 'unit', 'reporting_size', 'n_positions', 'n_matched',
              'coverage_his', 'coverage_lh', 'n_his_only', 'n_lh_only', 'bias', 'rms', 'p95_abs', 'p95_exact', 'corr',
              'frac_exceed', 'his_mean', 'lh_mean']
ALIGN_FIELDS = ['dataset', 'subject', 'his_recording', 'lh_recording', 'status', 'leg', 'sign_of_best_fit', 'lag_samples',
                'time_offset_s', 'segment_start_frame', 'align_rms_Nm_kg', 'other_leg_rms_Nm_kg', 'align_overlap_n',
                'his_rows', 'rows_compared', 'strides', 'note']
UNMATCHED_FIELDS = ['dataset', 'subject', 'side', 'recording', 'rows', 'reason']


class Collector:
    def __init__(self, dataset, maps, out_dir):
        self.dataset, self.maps = dataset, {m.name: m for m in maps}
        self.overall = {n: Acc(m.size, hist=True) for n, m in self.maps.items()}
        self.subj, self.cell = {}, {}
        self.rows, self.align, self.unmatched = [], [], []
        self.unavailable = {}
        self.out = out_dir

    def add_pairs(self, subject, task, pairs):
        for name, (x, y) in pairs.items():
            m = self.maps[name]
            self.overall[name].add(x, y)
            self.subj.setdefault((subject, name), Acc(m.size, keep_abs=True)).add(x, y)
            self.cell.setdefault((subject, task, name), Acc(m.size, keep_abs=True)).add(x, y)

    def _row(self, scope, subject, task, name, acc):
        m = self.maps[name]
        return {'dataset': self.dataset, 'scope': scope, 'subject': subject, 'task': task, 'column': name, 'unit': m.unit,
                'reporting_size': m.size, **acc.row()}

    def flush_subject(self, subject):
        for key in [k for k in self.subj if k[0] == subject]:
            self.rows.append(self._row('subject', subject, '', key[1], self.subj.pop(key)))
        for key in [k for k in self.cell if k[0] == subject]:
            self.rows.append(self._row('subject_task', subject, key[1], key[2], self.cell.pop(key)))

    def overall_rows(self):
        return [self._row('dataset', '', '', n, a) for n, a in self.overall.items()]


# ------------------------------------------------------------------------------------------------ streaming input
def batch_arrays(batch):
    out = {}
    for name, col in zip(batch.schema.names, batch.columns):
        t = col.type
        if pa.types.is_string(t) or pa.types.is_large_string(t) or pa.types.is_dictionary(t):
            out[name] = np.array(col.to_pylist(), dtype=object)
        elif pa.types.is_boolean(t):
            out[name] = pc.fill_null(col, False).to_numpy(zero_copy_only=False).astype(bool)
        else:
            out[name] = col.to_numpy(zero_copy_only=False).astype(np.float64)
    return out


def row_groups_with(pf, col, wanted):
    """Row groups whose min/max of `col` may contain a wanted value (all groups if statistics are missing)."""
    names = pf.schema_arrow.names
    wanted = sorted(wanted)
    try:
        j = names.index(col)
    except ValueError:
        return list(range(pf.metadata.num_row_groups))
    keep = []
    for g in range(pf.metadata.num_row_groups):
        st = pf.metadata.row_group(g).column(j).statistics
        if st is None or not st.has_min_max:
            keep.append(g)
        else:
            try:
                if any(st.min <= w <= st.max for w in wanted):
                    keep.append(g)
            except TypeError:
                keep.append(g)
    return keep


def read_batches(path, columns, subject_col=None, raw_subjects=None, batch_rows=BATCH_ROWS):
    """Dict-of-arrays batches of `columns` (rows of the wanted subjects only), streamed with iter_batches."""
    pf = pq.ParquetFile(str(path))
    missing = [c for c in columns if c not in pf.schema_arrow.names]
    if missing:
        raise KeyError(f'{path}: columns missing {missing}')
    cols = list(columns)
    if subject_col and subject_col not in cols:
        cols.append(subject_col)
    groups = row_groups_with(pf, subject_col, raw_subjects) if subject_col and raw_subjects else None
    for batch in pf.iter_batches(batch_size=batch_rows, row_groups=groups, columns=cols, use_threads=False):
        arrs = batch_arrays(batch)
        if subject_col and raw_subjects is not None:
            m = np.isin(arrs[subject_col], list(raw_subjects))
            if not m.any():
                continue
            arrs = {k: v[m] for k, v in arrs.items()}
        yield arrs


def iter_runs(batches, key):
    """(key value, concatenated arrays) for each run of equal `key`; error if a key value comes back later."""
    seen, cur, parts = set(), None, None
    for b in batches:
        k = b[key]
        n = len(k)
        if n == 0:
            continue
        cut = (np.flatnonzero(k[1:] != k[:-1]) + 1).tolist()
        for s, e in zip([0] + cut, cut + [n]):
            kk = k[s]
            if cur is None or kk != cur:
                if cur is not None:
                    seen.add(cur)
                    yield cur, {c: np.concatenate(v) for c, v in parts.items()}
                if kk in seen:
                    raise ValueError(f'{key} {kk!r} comes back after other rows: the file is not grouped by it')
                cur, parts = kk, {c: [] for c in b}
            for c, v in b.items():
                parts[c].append(v[s:e])
    if cur is not None:
        yield cur, {c: np.concatenate(v) for c, v in parts.items()}


def list_subjects(path, col='subject'):
    pf = pq.ParquetFile(str(path))
    out = set()
    for batch in pf.iter_batches(batch_size=BATCH_ROWS, columns=[col], use_threads=False):
        out.update(pc.unique(batch.column(0)).to_pylist())
    return out


# ------------------------------------------------------------------------------------------------ training side
def his_columns(maps):
    cols = list(HIS_READ_KEYS)
    for m in maps:
        for c in (m.his, m.his_flag):
            if c and c not in cols:
                cols.append(c)
    return cols


def prepare_his(rec, maps):
    """One training recording: time, task labels and masked report-unit series per mapped column."""
    t = rec['time_s']
    if len(t) > 1 and np.any(np.diff(t) < 0):
        raise ValueError('training time_s decreases inside a recording')
    out = {}
    for m in maps:
        v = rec[m.his].astype(float)
        if m.his_flag:
            flag = rec[m.his_flag]
            ok = flag.astype(bool) if flag.dtype == bool else flag > 0.5
            v = np.where(ok, v, np.nan)
        out[m.name] = v * m.scale
    names, code = np.unique(np.asarray(rec['task'], dtype=object).astype(str), return_inverse=True)
    return {'t': t, 'task_names': names, 'task_code': code.astype(np.int16), 'vals': out}


def modal_task(h):
    return str(h['task_names'][np.argmax(np.bincount(h['task_code']))]) if len(h['task_code']) else ''


def his_recordings(path, maps, raw_subjects, rss_cap):
    out = {}
    for rid, rec in iter_runs(read_batches(path, his_columns(maps), 'subject', raw_subjects), 'recording_id'):
        out[str(rid)] = prepare_his(rec, maps)
        check_rss(rss_cap, f'training recording {rid}')
    return out


# ------------------------------------------------------------------------------------------------ GT21
def name_match(cid, name):
    base = str(cid).split('+')[0]
    dup = re.match(r'^([A-Za-z]+)_(\1_.*)$', base, re.IGNORECASE)   # training ids repeat the mode: "treadmill_treadmill_01_01_..."
    if dup:
        base = dup.group(2)
    base, name = base.lower(), str(name).lower()           # some participants have "Treadmill_01_01" in LocoHub, "treadmill_Treadmill_.." in training
    return base == name or base.startswith(name + '_') or name.startswith(base + '_')


def gt21_root(base, subject):
    """Current export root of a participant: RB07 if finished, else the r2 export. (root, label) or (None, reason)."""
    base = Path(base)
    r7 = base / f'gt21_rb07_export_{subject}'
    r2 = base / f'gt21_rb06_export_{subject}_r2'
    if (r7 / 'run_summary.json').exists() and (r7 / 'time.parquet').exists():
        return r7, 'rb07'
    if (r2 / 'run_summary.json').exists() and (r2 / 'time.parquet').exists():
        return r2, 'rb06_r2'
    return None, 'no finished export root'


def gt21_lh_columns(maps):
    cols = ['source_recording_id', 'time_s']
    for m in maps:
        for leg in ('left', 'right'):
            cols.append(lh_name(m, leg))
    return cols


def fit_gt21(h, lrec, maps, cfg):
    """Best leg/offset of one training recording against one LocoHub recording, or a failure record."""
    mom = next(m for m in maps if m.name == 'ankle_moment')
    tL = lrec['time_s']
    hx = h['vals']['ankle_moment']
    t0h = float(h['t'][0])
    gx = uniform_grid(h['t'], hx, t0h)
    min_n = max(cfg.min_overlap_n, int(cfg.min_overlap_frac * int(np.isfinite(hx).sum())))
    nL = int(round((tL[-1] - tL[0]) / DT)) + 1
    gridL = tL[0] + np.arange(nL) * DT
    fits = {}
    for leg in ('left', 'right'):
        yL = interp_nodes(tL, lrec[lh_name(mom, leg)] * mom.scale, gridL)
        fit = best_alignment(gx, yL, min_n)
        if fit is not None:
            fits[leg] = fit
    if not fits:
        return None
    leg = min(fits, key=lambda k: fits[k]['rms'])
    other = [fits[k]['rms'] for k in fits if k != leg]
    fit = dict(fits[leg], leg=leg, other_rms=other[0] if other else math.nan)
    fit['offset'] = float(tL[0] + fit['lag'] * DT - t0h)
    return fit


def gt21_pairs(h, lrec, fit, maps):
    """(task labels inside the span, {column: (training, LocoHub)} in report units) for a fitted recording."""
    tq = h['t'] + fit['offset']
    tL = lrec['time_s']
    inside = (tq >= tL[0] - 1e-6) & (tq <= tL[-1] + 1e-6)
    pairs = {}
    for m in maps:
        if lh_name(m, fit['leg']) in lrec:
            y = interp_nodes(tL, lrec[lh_name(m, fit['leg'])] * m.scale + m.lh_offset, tq)
        else:
            y = np.full(len(tq), np.nan)          # column absent in LocoHub: counted as no LocoHub coverage
        pairs[m.name] = (h['vals'][m.name][inside], y[inside])
    return h['task_code'][inside], pairs


def compare_gt21_subject(his_path, lh_path, subject, cfg, col, maps, root_label=''):
    raw = {s for s in list_subjects(his_path) if norm_subject(s) == subject}
    if not raw:
        col.unmatched.append({'dataset': 'gt21', 'subject': subject, 'side': 'training', 'recording': '', 'rows': 0,
                              'reason': 'participant not in the training file'})
        return
    hs = his_recordings(his_path, maps, raw, cfg.rss_cap_mib)
    cands = {rid: [] for rid in hs}
    best = {}
    lh_cols = gt21_lh_columns(maps)
    pf_cols = set(pq.ParquetFile(str(lh_path)).schema_arrow.names)
    lh_cols = [c for c in lh_cols if c in pf_cols]
    for m in maps:
        if lh_name(m, 'left') not in pf_cols:
            col.unavailable[m.name] = 'column absent from the LocoHub time table'
    for key, lrec in iter_runs(read_batches(lh_path, lh_cols), 'source_recording_id'):
        name = str(key).split('/')[-1]
        matched = [rid for rid in hs if name_match(rid.split('|', 1)[-1], name)]
        if not matched:
            col.unmatched.append({'dataset': 'gt21', 'subject': subject, 'side': 'locohub', 'recording': str(key),
                                  'rows': len(lrec['time_s']), 'reason': 'no training recording with this name'})
            continue
        for rid in matched:
            cands[rid].append(str(key))
            h = hs[rid]
            if not np.isfinite(h['vals']['ankle_moment']).any():
                continue
            fit = fit_gt21(h, lrec, maps, cfg)
            if fit is None:
                continue
            if rid in best and best[rid]['fit']['rms'] <= fit['rms']:
                continue
            task, pairs = gt21_pairs(h, lrec, fit, maps)
            best[rid] = {'fit': fit, 'lh': str(key), 'task': task, 'pairs': pairs}
        check_rss(cfg.rss_cap_mib, f'locohub recording {key}')
    for rid, h in hs.items():
        base = {'dataset': 'gt21', 'subject': subject, 'his_recording': rid, 'his_rows': len(h['t'])}
        b = best.get(rid)
        if b is None:
            why = ('no finite ankle moment in the training recording' if not np.isfinite(h['vals']['ankle_moment']).any()
                   else 'no LocoHub recording with this name' if not cands[rid]
                   else 'alignment impossible: too little overlapping moment')
            col.align.append({**base, 'status': 'no_candidate', 'note': why})
            col.unmatched.append({'dataset': 'gt21', 'subject': subject, 'side': 'training', 'recording': rid,
                                  'rows': len(h['t']), 'reason': why})
            continue
        fit = b['fit']
        ok = fit['rms'] <= cfg.align_rms_tol
        col.align.append({**base, 'lh_recording': b['lh'], 'status': 'matched' if ok else 'alignment_failed',
                          'leg': fit['leg'], 'sign_of_best_fit': 'same' if fit['sign'] > 0 else 'flipped',
                          'lag_samples': fit['lag'], 'time_offset_s': fit['offset'], 'align_rms_Nm_kg': fit['rms'],
                          'other_leg_rms_Nm_kg': fit['other_rms'], 'align_overlap_n': fit['n'],
                          'rows_compared': len(b['task']), 'note': f'candidates {len(cands[rid])}; locohub root {root_label}'})
        if not ok:
            col.unmatched.append({'dataset': 'gt21', 'subject': subject, 'side': 'training', 'recording': rid,
                                  'rows': len(h['t']), 'reason': f'alignment failed (best moment RMS {fit["rms"]:.3f} Nm/kg)'})
            continue
        for code in np.unique(b['task']):
            sel = b['task'] == code
            col.add_pairs(subject, str(h['task_names'][code]), {k: (x[sel], y[sel]) for k, (x, y) in b['pairs'].items()})
    col.flush_subject(subject)


# ------------------------------------------------------------------------------------------------ UM21
OBS_RE = re.compile(r'^(?P<rec>.+):(?P<side>left|right):frames:(?P<a>\d+):(?P<b>\d+)$')
REC_RE = re.compile(r'Streaming/(?P<sub>[^/]+)/Tread/(?P<inc>[^/:]+)$')
CID_RE = re.compile(r'^Tread_(?P<inc>d10|d5|i0|i10|i5)(_|$)')


def parse_observation(oid):
    m = OBS_RE.match(str(oid))
    if not m:
        raise ValueError(f'observation id without source frames: {oid!r}')
    return m.group('side'), int(m.group('a')), int(m.group('b'))


def frames_series(strides, n_phase=150):
    """Frame-domain series (index = 1-based source frame - 1) rebuilt from strides [(a, b, values at the phase grid)]."""
    n = max(b for _, b, _ in strides)
    out = np.full(n, np.nan)
    grid = np.arange(n_phase, dtype=float)
    for a, b, v in strides:
        f = np.arange(a, b + 1)
        new = interp_nodes(grid, v, (f - a) / (b - a) * (n_phase - 1))
        cur = out[f - 1]
        out[f - 1] = np.where(np.isfinite(new), new, cur)
    return out


def um21_stride_times(a, b, start, n_phase=150):
    """Training-file time (s) of the phase samples of a stride on source frames a..b, segment starting at frame `start`."""
    return ((a - start) + np.arange(n_phase) * (b - a) / (n_phase - 1)) / 100.0


def um21_lh_columns(maps, available):
    cols = ['source_recording_id', 'observation_id', 'reference_side']
    for m in maps:
        c = lh_name(m, 'ipsi')
        if c in available:
            cols.append(c)
    return cols


def compare_um21_subject(his_path, lh_path, subject, cfg, col, maps):
    raw = {s for s in list_subjects(his_path) if norm_subject(s) == subject}
    if not raw:
        col.unmatched.append({'dataset': 'um21', 'subject': subject, 'side': 'training', 'recording': '', 'rows': 0,
                              'reason': 'participant not in the training file'})
        return
    hs = his_recordings(his_path, maps, raw, cfg.rss_cap_mib)
    by_inc, used = {}, set()
    for rid in hs:
        cid = rid.split('|', 1)[-1]
        m = CID_RE.match(cid)
        if not m:
            col.align.append({'dataset': 'um21', 'subject': subject, 'his_recording': rid, 'his_rows': len(hs[rid]['t']),
                              'status': 'no_candidate', 'note': 'not a treadmill collection; not in package v4 (Run, Wtr, Stair)'})
            col.unmatched.append({'dataset': 'um21', 'subject': subject, 'side': 'training', 'recording': rid,
                                  'rows': len(hs[rid]['t']), 'reason': 'not a treadmill collection (not in package v4)'})
            continue
        by_inc.setdefault(m.group('inc'), []).append(rid)
    pf_cols = set(pq.ParquetFile(str(lh_path)).schema_arrow.names)
    cols = um21_lh_columns(maps, pf_cols)
    for m in maps:
        if lh_name(m, 'ipsi') not in pf_cols:
            col.unavailable[m.name] = 'column absent from the LocoHub phase table'
    batches = read_batches(lh_path, cols + ['subject'], 'subject', {s for s in list_subjects(lh_path) if norm_subject(s) == subject})
    mom = next(m for m in maps if m.name == 'ankle_moment')
    for key, lrec in iter_runs(batches, 'source_recording_id'):
        rm = REC_RE.search(str(key))
        if not rm:
            col.unmatched.append({'dataset': 'um21', 'subject': subject, 'side': 'locohub', 'recording': str(key),
                                  'rows': len(lrec['observation_id']), 'reason': 'not a treadmill recording id'})
            continue
        inc = rm.group('inc')
        mask = lrec['reference_side'] == cfg.um21_side
        lrec = {k: v[mask] for k, v in lrec.items()}
        obs = lrec['observation_id']
        cut = (np.flatnonzero(obs[1:] != obs[:-1]) + 1).tolist()
        strides = []
        for s, e in zip([0] + cut, cut + [len(obs)]):
            if e - s != 150:
                raise ValueError(f'{obs[s]}: {e - s} rows, expected 150')
            _, a, b = parse_observation(obs[s])
            strides.append({'a': a, 'b': b, 'vals': {m.name: (lrec[lh_name(m, 'ipsi')][s:e] * m.scale + m.lh_offset
                                                              if lh_name(m, 'ipsi') in lrec else np.full(150, np.nan))
                                                     for m in maps}})
        segs = by_inc.get(inc, [])
        if not segs:
            col.unmatched.append({'dataset': 'um21', 'subject': subject, 'side': 'locohub', 'recording': str(key),
                                  'rows': 150 * len(strides), 'reason': 'no training segment for this incline'})
            continue
        used.add(inc)
        moment_strides = [(s['a'], s['b'], s['vals']['ankle_moment']) for s in strides]
        series = frames_series(moment_strides)
        covered = np.zeros(len(strides), bool)
        for rid in segs:
            h = hs[rid]
            base = {'dataset': 'um21', 'subject': subject, 'his_recording': rid, 'lh_recording': str(key), 'his_rows': len(h['t']),
                    'leg': cfg.um21_side}
            hx = h['vals']['ankle_moment']
            g = uniform_grid(h['t'], hx, 0.0)[::2]
            min_n = max(cfg.min_overlap_n, int(cfg.min_overlap_frac * int(np.isfinite(g).sum())))
            fit = best_alignment(g, series, min_n)
            if fit is None:
                col.align.append({**base, 'status': 'no_candidate', 'note': 'too little overlapping moment to align'})
                col.unmatched.append({'dataset': 'um21', 'subject': subject, 'side': 'training', 'recording': rid,
                                      'rows': len(h['t']), 'reason': 'too little overlapping moment to align'})
                continue
            start = fit['lag'] + 1
            ok = fit['rms'] <= cfg.align_rms_tol
            row = {**base, 'status': 'matched' if ok else 'alignment_failed', 'sign_of_best_fit': 'same' if fit['sign'] > 0 else 'flipped',
                   'lag_samples': fit['lag'], 'segment_start_frame': start, 'align_rms_Nm_kg': fit['rms'], 'align_overlap_n': fit['n']}
            if not ok:
                col.align.append({**row, 'note': 'best moment RMS above the alignment tolerance'})
                col.unmatched.append({'dataset': 'um21', 'subject': subject, 'side': 'training', 'recording': rid, 'rows': len(h['t']),
                                      'reason': f'alignment failed (best moment RMS {fit["rms"]:.3f} Nm/kg)'})
                continue
            t_end = float(h['t'][-1])
            xs = {m.name: [] for m in maps}
            ys = {m.name: [] for m in maps}
            n_in = 0
            for i, s in enumerate(strides):
                tq = um21_stride_times(s['a'], s['b'], start)
                if tq[0] < -1e-9 or tq[-1] > t_end + 1e-9 or covered[i]:
                    continue
                covered[i] = True
                n_in += 1
                for m in maps:
                    if m.name in s['vals']:
                        xs[m.name].append(interp_nodes(h['t'], h['vals'][m.name], tq))
                        ys[m.name].append(s['vals'][m.name])
            col.align.append({**row, 'strides': n_in, 'rows_compared': 150 * n_in, 'note': ''})
            if n_in:
                col.add_pairs(subject, modal_task(h), {k: (np.concatenate(xs[k]), np.concatenate(ys[k])) for k in xs if xs[k]})
        left = int((~covered).sum())
        if left:
            col.align.append({'dataset': 'um21', 'subject': subject, 'lh_recording': str(key), 'status': 'strides_not_in_a_matched_segment',
                              'leg': cfg.um21_side, 'strides': left, 'rows_compared': 0, 'note': 'LocoHub strides with no matched training segment'})
        check_rss(cfg.rss_cap_mib, f'locohub recording {key}')
    for inc, rids in by_inc.items():
        if inc not in used:
            for rid in rids:
                col.unmatched.append({'dataset': 'um21', 'subject': subject, 'side': 'training', 'recording': rid, 'rows': len(hs[rid]['t']),
                                      'reason': 'incline recording not in package v4'})
    col.flush_subject(subject)


# ------------------------------------------------------------------------------------------------ run and spec
@dataclass
class Cfg:
    align_rms_tol: float = 0.10
    min_overlap_frac: float = 0.30
    min_overlap_n: int = 100
    rss_cap_mib: float = 290.0
    um21_side: str = 'right'


def resolve_inputs(args):
    his = Path(args.his_file) if args.his_file else Path(args.his_dir) / args.partition / HIS_FILES[args.dataset]
    if args.dataset == 'um21':
        lh = {None: (ROOT / args.um21_phase, 'um21_r01_package_v4')}
        return his, lh
    subjects = args.subject or []
    return his, {s: gt21_root(ROOT / args.lh_base, s) for s in subjects}


def write_csv(path, fields, rows):
    with open(path, 'x', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow(r)


def mapping_report(maps, his_schema, lh_names_by_role):
    mapped_his = {c for m in maps for c in (m.his, m.his_flag) if c}
    return {
        'columns': [{'name': m.name, 'training_column': m.his, 'locohub_column': m.lh, 'unit': m.unit, 'scale_from_raw': m.scale,
                     'locohub_offset_in_unit': m.lh_offset, 'sign': m.sign, 'training_validity_flag': m.his_flag,
                     'reporting_size': m.size, 'note': m.note} for m in maps],
        'training_unmapped': [{'column': c, 'role': HIS_ROLES.get(c, 'not described')} for c in his_schema if c not in mapped_his],
        'locohub_unmapped': {role: sorted(n for n in names if n not in {lh_name(m, role) for m in maps}) for role, names in lh_names_by_role.items()},
        'reporting_sizes_note': 'sizes decide which differences are counted in frac_exceed; they are reporting sizes, not quality limits',
    }


def run(args):
    out = Path(args.out_dir)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f'{out} is not empty; outputs go to a new directory')
    out.mkdir(parents=True, exist_ok=True)
    cfg = Cfg(args.align_rms_tol, 0.30, 100, args.rss_cap_mib, args.um21_side)
    maps = column_maps(args.cop_shift_m)
    his, lh = resolve_inputs(args)
    started = time.time()
    his_names = pq.ParquetFile(str(his)).schema_arrow.names
    his_subjects = sorted({norm_subject(s) for s in list_subjects(his)})
    col = Collector(args.dataset, maps, out)
    subjects = args.subject or (his_subjects if args.dataset == 'um21' else [])
    status, error, per_subject, lh_names = 'complete', None, {}, {}
    try:
        for s in subjects:
            t0 = time.time()
            if args.dataset == 'gt21':
                root, label = lh[s] if s in lh else gt21_root(ROOT / args.lh_base, s)
                if root is None:
                    col.unmatched.append({'dataset': 'gt21', 'subject': s, 'side': 'locohub', 'recording': '', 'rows': 0, 'reason': label})
                    continue
                path = root / 'time.parquet'
                lh_names.setdefault('left', pq.ParquetFile(str(path)).schema_arrow.names)
                compare_gt21_subject(his, path, s, cfg, col, maps, f'{label}: {root.name}')
                per_subject[s] = {'locohub_root': str(root.relative_to(ROOT)), 'label': label}
            else:
                path = lh[None][0]
                lh_names.setdefault('ipsi', pq.ParquetFile(str(path)).schema_arrow.names)
                compare_um21_subject(his, path, s, cfg, col, maps)
                per_subject[s] = {'locohub_file': str(path.relative_to(ROOT))}
            _release_memory()
            per_subject[s].update(seconds=round(time.time() - t0, 1), peak_rss_mib=round(peak_rss_mib(), 1))
            print(f'{args.dataset} {s} done peak_rss_mib={peak_rss_mib():.1f}', file=sys.stderr, flush=True)
    except Exception as exc:  # noqa: BLE001 - recorded, then re-raised after the partial outputs are written
        status, error = 'incomplete', f'{type(exc).__name__}: {exc}'[:500]
        raise
    finally:
        write_csv(out / 'comparison.csv', ROW_FIELDS, col.overall_rows() + col.rows)
        write_csv(out / 'alignment.csv', ALIGN_FIELDS, col.align)
        write_csv(out / 'unmatched.csv', UNMATCHED_FIELDS, col.unmatched)
        summary = {
            'schema': SCHEMA_ID, 'status': status, 'error': error, 'scientific_approval': False, 'dataset': args.dataset,
            'partition': args.partition, 'training_file': str(his), 'training_file_bytes': his.stat().st_size,
            'locohub_inputs': {str(k): [str(v[0]), v[1]] for k, v in lh.items()},
            'training_subjects': his_subjects, 'subjects_run': subjects, 'per_subject': per_subject,
            'unavailable_in_locohub': col.unavailable,
            'mapping': mapping_report(maps, his_names, lh_names),
            'settings': {'align_rms_tol_Nm_kg': cfg.align_rms_tol, 'min_overlap_fraction': cfg.min_overlap_frac,
                         'min_overlap_n': cfg.min_overlap_n, 'cop_origin_shift_m': args.cop_shift_m, 'um21_side': cfg.um21_side,
                         'hist_bin_width_rule': f'reporting size / {HIST_WIDTH_DIVISOR:g}, {HIST_BINS} bins'},
            'counts': {'alignment_rows_by_status': _count(r['status'] for r in col.align),
                       'unmatched_by_reason': _count(r['reason'] for r in col.unmatched)},
            'peak_rss_mib': round(peak_rss_mib(), 1), 'seconds': round(time.time() - started, 1),
            'code_sha256': {c: sha256_file(ROOT / c) for c in CODE}}
        (out / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True, default=str) + '\n')
    return 0


def _count(items):
    out = {}
    for i in items:
        out[i] = out.get(i, 0) + 1
    return out


def make_spec(args):
    sys.path.insert(0, str(ROOT))
    from contributor_tools import guarded_launcher as gl
    his, lh = resolve_inputs(args)
    bindings = {c: gl.sha256_file(ROOT / c) for c in CODE + ('contributor_tools/guarded_launcher.py',)}
    bindings[str(his)] = gl.sha256_file(his)
    if args.dataset == 'um21':
        for rel in (args.um21_phase, UM21_MANIFEST_DEFAULT):
            bindings[rel] = gl.sha256_file(ROOT / rel)
    else:
        for s, (root, label) in lh.items():
            if root is None:
                raise SystemExit(f'{s}: {label}')
            for n in ('time.parquet', 'run_summary.json'):
                bindings[str((root / n).relative_to(ROOT))] = gl.sha256_file(root / n)
    command = ['python3', 'contributor_tools/compare_training_vs_locohub.py', 'run', '--dataset', args.dataset,
               '--partition', args.partition, '--out-dir', args.out_dir, '--his-file', str(his),
               '--cop-shift-m', str(args.cop_shift_m), '--align-rms-tol', str(args.align_rms_tol)]
    for s in args.subject or []:
        command += ['--subject', s]
    spec = {'job_id': args.job_id, 'command': command, 'cwd': str(ROOT), 'output_root': args.out_dir, 'receipt_path': args.receipt,
            'bindings': bindings, 'timeout_seconds': 3600, 'kill_after_seconds': 30, 'poll_seconds': 15,
            'startup_memory_mib': {'linux': 3584, 'windows': 2816}, 'runtime_memory_mib': {'linux': 2048, 'windows': 2048},
            'expected_output_names': ['summary.json', 'comparison.csv'], 'address_space_mib': 768,
            'disk_admission': [{'path': str(ROOT / 'docs'), 'min_free_mib': 5120}]}
    with open(args.spec_out, 'x') as f:
        json.dump(spec, f, indent=2)
        f.write('\n')
    return 0


def build_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    for name in ('run', 'spec'):
        s = sub.add_parser(name)
        s.add_argument('--dataset', choices=('gt21', 'um21'), required=True)
        s.add_argument('--partition', default='gate', help='es_prepared partition (CoP of um21 depends on it)')
        s.add_argument('--his-dir', default=HIS_DIR_DEFAULT)
        s.add_argument('--his-file', default=None, help='override the training parquet path')
        s.add_argument('--lh-base', default=LH_BASE_DEFAULT)
        s.add_argument('--um21-phase', default=UM21_PHASE_DEFAULT)
        s.add_argument('--um21-side', choices=('left', 'right'), default='right')
        s.add_argument('--subject', action='append', help='AB number; repeatable. um21 default: all training participants')
        s.add_argument('--cop-shift-m', type=float, default=0.100)
        s.add_argument('--align-rms-tol', type=float, default=0.10)
        s.add_argument('--out-dir', required=True)
        if name == 'run':
            s.add_argument('--rss-cap-mib', type=float, default=290.0)
        else:
            s.add_argument('--job-id', required=True)
            s.add_argument('--receipt', required=True)
            s.add_argument('--spec-out', required=True)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.dataset == 'gt21' and not args.subject:
        raise SystemExit('gt21 needs at least one --subject (one participant at a time; list them explicitly)')
    return {'run': run, 'spec': make_spec}[args.cmd](args)


if __name__ == '__main__':
    raise SystemExit(main())
