#!/usr/bin/env python3
"""Audit time-indexed LocoHub datasets for sign/physical convention compliance.

This is the third and strictest of three layered validators:
  1. Validator (time mode)   -> schema + time-structure integrity
  2. audit_dataset_units.py   -> loose unit-magnitude sanity + non-finite values
  3. audit_time_conventions.py (this tool) -> tight physical + SIGN conventions

It verifies the *directional* and *cross-signal* conventions a standardized
time-series export must follow, so a converter that silently inverts an axis,
scrambles ipsi/contra, mislabels units, or leaves off-contact CoP unmasked is
caught before the data ships.

Design goals vs. the previous version
-------------------------------------
* Memory-bounded: one streaming pass (pyarrow batches) computes full-coverage
  scalar stats; robust medians/percentiles come from reservoir samples; the few
  relational checks read a capped prefix of rows. The per-task coverage
  aggregation reads only a handful of columns and is the memory high-water mark
  (roughly those columns' size, not the whole file).
* Robust statistics: medians / MAD / percentiles instead of means, so a few
  spikes cannot flip a verdict; systemic-vs-rare classification so a handful of
  out-of-range samples WARNs instead of FAILing the whole dataset.
* Frame-aware CoP: the reference frame (ankle-local vs lab/world) is detected
  from cop_vertical, and the horizontal bound is applied accordingly instead of
  assuming ankle frame universally (which false-FAILs lab-frame datasets).
* New cross-signal checks: sampling-rate consistency, velocity == d(angle)/dt
  sign/scale, segment-angle vs joint-angle chain, degrees-not-radians detection,
  dead (all-NaN) columns, ipsi/contra scale symmetry.

Severity: FAIL (hard convention/physical violation, exit code 1), WARN
(suspicious but possibly legitimate), OK. --strict treats WARN as failure.

Usage:
  python contributor_tools/audit_time_conventions.py converted_datasets/foo_time.parquet
  python contributor_tools/audit_time_conventions.py foo_time.parquet --json report.json --strict
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq


# --------------------------------------------------------------------------- #
# Tunable thresholds (all documented; conservative to keep false positives low)
# --------------------------------------------------------------------------- #
BATCH_ROWS = 131_072            # streaming batch size
RESERVOIR = 120_000             # reservoir sample size for robust medians/pcts
CAP_ROWS = 1_200_000            # prefix rows read for relational checks

LOADED_BW = 0.05                # vertical GRF >= this counts as "limb loaded"
UNLOADED_BW = 0.02              # vertical GRF <  this counts as "clearly unloaded"
GRF_NEG_TOL_BW = 0.10           # vertical GRF this far below 0 is "negative"
GRF_NEG_FRAC_WARN = 0.02        # fraction of negative samples that earns a WARN
GRF_PEAK_LO, GRF_PEAK_HI = 0.6, 3.2   # plausible loaded p95 vertical GRF (BW)

COP_VERT_FLAT_M = 0.02          # |cop_vertical| below this => ankle/local frame
COP_ANKLE_MAX_M = 0.5           # foot-scale horizontal bound in ankle frame
COP_ABSURD_M = 8.0              # horizontal CoP beyond this is impossible (FAIL)
COP_LEAK_FRAC_WARN = 0.05       # finite CoP occurring off-contact => mask leak

UNIT_SYSTEMIC_FRAC = 0.01       # >this fraction beyond a unit ceiling => FAIL
DEG_FRAC_WARN = 0.01            # >this fraction of an angle col beyond 2pi => deg?

DT_REL_TOL = 0.05               # median dt must match 1/declared_rate within 5%
DT_IRREG_FRAC = 0.01            # >this fraction of irregular dt within steps => WARN

VEL_CORR_FAIL = -0.5            # corr(vel, d(angle)/dt) below this => inverted (FAIL)
VEL_CORR_WARN = 0.90            # below this (and >= FAIL) => WARN
VEL_SCALE_LO, VEL_SCALE_HI = 0.5, 2.0  # robust scale ratio outside => unit WARN

CHAIN_CORR_WARN = 0.80          # |corr(knee, thigh-shank)| below this => WARN
SYM_STD_LO, SYM_STD_HI = 0.33, 3.0     # ipsi/contra robust-std ratio band

MIN_N = 200                     # minimum paired samples before a relational check

UNIT_LIMITS = (
    ('_rad_s2', 10_000.0),
    ('_rad_s', 100.0),
    ('_Nm_kg', 20.0),
    ('_rad', 2 * math.pi),
    ('_BW', 10.0),
    ('_m', 5.0),
)

SIDES = ('ipsi', 'contra')
COP_AXES = ('anterior', 'lateral', 'vertical')

# Segment triples for the joint == (minuend - subtrahend) chain check (sagittal).
# The knee is proximal - distal (knee_flexion = thigh - shank), but the ankle is
# distal - proximal (ankle_dorsiflexion = foot - shank): with the shank fixed, a
# positive foot rotation is dorsiflexion; with the foot fixed, a positive shank
# rotation is plantarflexion. Order each triple as (joint, minuend, subtrahend).
CHAIN_TRIPLES = (
    ('knee_flexion_angle', 'thigh_sagittal_angle', 'shank_sagittal_angle'),     # thigh - shank
    ('ankle_dorsiflexion_angle', 'foot_sagittal_angle', 'shank_sagittal_angle'),  # foot - shank
)

# Joints for velocity == d(angle)/dt check.
VEL_JOINTS = ('hip_flexion', 'knee_flexion', 'ankle_dorsiflexion',
              'hip_adduction', 'knee_adduction', 'ankle_adduction')


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
class Report:
    def __init__(self):
        self.findings = []  # (severity, check, message)

    def add(self, severity, check, message):
        self.findings.append((severity, check, message))

    def ok(self, check, message):
        self.add('OK', check, message)

    def warn(self, check, message):
        self.add('WARN', check, message)

    def fail(self, check, message):
        self.add('FAIL', check, message)

    def counts(self):
        c = {'OK': 0, 'WARN': 0, 'FAIL': 0}
        for sev, _, _ in self.findings:
            c[sev] += 1
        return c


# --------------------------------------------------------------------------- #
# Streaming accumulators
# --------------------------------------------------------------------------- #
class Reservoir:
    """Unbiased reservoir sample (Algorithm R) of finite float values."""

    __slots__ = ('buf', 'k', 'n', 'rng')

    def __init__(self, k=RESERVOIR, seed=0):
        self.k = k
        self.buf = np.empty(k, dtype=float)
        self.n = 0
        self.rng = np.random.default_rng(seed)

    def add(self, values):
        v = values[np.isfinite(values)]
        if v.size == 0:
            return
        take = min(self.k - self.n, v.size)
        if take > 0:
            self.buf[self.n:self.n + take] = v[:take]
            self.n += take
            v = v[take:]
        if v.size:
            # replacement phase
            idx = self.rng.integers(0, self.n + np.arange(1, v.size + 1))
            keep = idx < self.k
            self.buf[idx[keep]] = v[keep]
            self.n = self.k

    def values(self):
        return self.buf[:self.n]


@dataclass
class ColStat:
    finite: int = 0
    infinite: int = 0
    total: int = 0
    n_beyond: int = 0        # |x| > unit ceiling
    absmax: float = 0.0
    limit: float = math.inf


@dataclass
class GrfStat:
    finite: int = 0
    total: int = 0
    n_neg: int = 0           # x < -GRF_NEG_TOL_BW
    loaded: Reservoir = field(default_factory=lambda: Reservoir(seed=1))


@dataclass
class CopStat:
    finite: int = 0
    total: int = 0
    absmax: float = 0.0
    n_beyond_ankle: int = 0
    n_absurd: int = 0
    leak: int = 0            # finite while limb clearly unloaded
    vabs: Reservoir = field(default_factory=lambda: Reservoir(seed=2))  # |value| sample


def _unit_limit(name):
    for suf, lim in UNIT_LIMITS:
        if name.endswith(suf):
            return lim
    return None


def _to_np(batch, name):
    arr = pc.cast(batch.column(name), pa.float64(), safe=False)
    return np.asarray(arr.to_numpy(zero_copy_only=False), dtype=float)


# --------------------------------------------------------------------------- #
# Single streaming pass: units, GRF, CoP, time/dt, dead columns
# --------------------------------------------------------------------------- #
def stream_pass(path, names):
    pf = pq.ParquetFile(path)

    unit_cols = [n for n in names if _unit_limit(n) is not None]
    grf_v = {s: f'grf_vertical_{s}_BW' for s in SIDES if f'grf_vertical_{s}_BW' in names}
    cop_cols = {s: [f'cop_{ax}_{s}_m' for ax in COP_AXES if f'cop_{ax}_{s}_m' in names]
                for s in SIDES}
    cop_cols = {s: c for s, c in cop_cols.items() if c}
    has_time = 'time_s' in names
    has_step = 'step' in names
    has_rate = 'sampling_rate_hz' in names

    read_cols = set(unit_cols) | set(grf_v.values())
    for c in cop_cols.values():
        read_cols |= set(c)
    if has_time:
        read_cols.add('time_s')
    if has_step:
        read_cols.add('step')
    if has_rate:
        read_cols.add('sampling_rate_hz')
    read_cols = [n for n in names if n in read_cols]

    ustat = {n: ColStat(limit=_unit_limit(n)) for n in unit_cols}
    gstat = {s: GrfStat() for s in grf_v}
    cstat = {c: CopStat() for cols in cop_cols.values() for c in cols}

    # time / dt accumulators
    dt_res = Reservoir(seed=3)
    n_nonincr = 0     # dt <= 0 within same step (monotonicity violation)
    n_dupe = 0        # dt == 0 within same step (duplicate timestamp)
    n_time_bad = 0    # non-finite or negative time
    prev_time = None
    prev_step = None
    declared_rate = None

    for batch in pf.iter_batches(columns=read_cols, batch_size=BATCH_ROWS, use_threads=False):
        # ---- units + dead columns ----
        for n in unit_cols:
            x = _to_np(batch, n)
            st = ustat[n]
            fin = np.isfinite(x)
            st.total += x.size
            st.finite += int(fin.sum())
            st.infinite += int(np.isinf(x).sum())
            if fin.any():
                xa = np.abs(x[fin])
                st.absmax = max(st.absmax, float(xa.max()))
                st.n_beyond += int((xa > st.limit).sum())

        # ---- GRF vertical ----
        for s, col in grf_v.items():
            v = _to_np(batch, col)
            g = gstat[s]
            fin = np.isfinite(v)
            g.total += v.size
            g.finite += int(fin.sum())
            vf = v[fin]
            g.n_neg += int((vf < -GRF_NEG_TOL_BW).sum())
            g.loaded.add(vf[vf >= LOADED_BW])

        # ---- CoP (frame-aware, leak vs vertical GRF) ----
        for s, cols in cop_cols.items():
            v = _to_np(batch, grf_v[s]) if s in grf_v else None
            unloaded = (v < UNLOADED_BW) if v is not None else None
            for c in cols:
                x = _to_np(batch, c)
                cs = cstat[c]
                fin = np.isfinite(x)
                cs.total += x.size
                cs.finite += int(fin.sum())
                if fin.any():
                    xa = np.abs(x[fin])
                    cs.absmax = max(cs.absmax, float(xa.max()))
                    cs.vabs.add(xa)
                    cs.n_beyond_ankle += int((xa > COP_ANKLE_MAX_M).sum())
                    cs.n_absurd += int((xa > COP_ABSURD_M).sum())
                if unloaded is not None:
                    cs.leak += int((fin & unloaded).sum())

        # ---- time / dt ----
        if has_time:
            t = _to_np(batch, 'time_s')
            n_time_bad += int((~np.isfinite(t)).sum() + np.nansum(t < 0))
            if has_step:
                st = _to_np(batch, 'step')
                # prepend carry from previous batch
                if prev_time is not None:
                    t = np.concatenate(([prev_time], t))
                    st = np.concatenate(([prev_step], st))
                same = st[1:] == st[:-1]
                dt = np.diff(t)
                good = same & np.isfinite(dt)
                dt_res.add(dt[good & (dt > 0)])
                n_nonincr += int((good & (dt <= 0)).sum())
                n_dupe += int((good & (dt == 0)).sum())
                prev_time = t[-1]
                prev_step = st[-1]
        if has_rate and declared_rate is None:
            r = _to_np(batch, 'sampling_rate_hz')
            r = r[np.isfinite(r)]
            if r.size:
                declared_rate = float(np.median(r))

    return {
        'unit_cols': unit_cols, 'ustat': ustat,
        'grf_v': grf_v, 'gstat': gstat,
        'cop_cols': cop_cols, 'cstat': cstat,
        'time': {'has_time': has_time, 'has_step': has_step,
                 'n_time_bad': int(n_time_bad), 'n_nonincr': n_nonincr,
                 'n_dupe': n_dupe, 'dt': dt_res, 'rate': declared_rate},
    }


# --------------------------------------------------------------------------- #
# Interpret streaming results into findings
# --------------------------------------------------------------------------- #
def report_time(res, report):
    t = res['time']
    if not t['has_time']:
        report.warn('time', 'no time_s column; not a time-indexed dataset?')
        return
    if t['n_time_bad']:
        report.fail('time', f"{t['n_time_bad']:,} non-finite/negative time_s values")
    if not t['has_step']:
        report.warn('time', 'no step column; cannot check per-window monotonicity')
        return
    if t['n_nonincr']:
        report.fail('time', f"{t['n_nonincr']:,} within-step samples with non-increasing time "
                            f"({t['n_dupe']:,} exact duplicate timestamps)")
    elif t['n_time_bad'] == 0:
        report.ok('time', 'time_s finite, >=0, strictly increasing within every step')


def report_sampling(res, report):
    t = res['time']
    dt = t['dt'].values()
    if dt.size < MIN_N:
        return
    med = float(np.median(dt))
    if med <= 0:
        return
    # regularity: fraction of within-step dt deviating > DT_REL_TOL from median
    irreg = float((np.abs(dt - med) > DT_REL_TOL * med).mean())
    rate = t['rate']
    if rate:
        exp = 1.0 / rate
        rel = abs(med - exp) / exp
        if rel > DT_REL_TOL:
            report.fail('sampling', f'median dt {med*1e3:.3f} ms disagrees with declared '
                                    f'{rate:g} Hz (expected {exp*1e3:.3f} ms, {rel:.0%} off)')
        elif irreg > DT_IRREG_FRAC:
            report.warn('sampling', f'{irreg:.1%} of within-step steps deviate >5% from median '
                                    f'dt {med*1e3:.3f} ms (irregular sampling)')
        else:
            report.ok('sampling', f'dt {med*1e3:.3f} ms consistent with declared {rate:g} Hz')
    else:
        if irreg > DT_IRREG_FRAC:
            report.warn('sampling', f'{irreg:.1%} of within-step steps deviate >5% from median '
                                    f'dt {med*1e3:.3f} ms (irregular; no declared rate)')
        else:
            report.ok('sampling', f'uniform dt {med*1e3:.3f} ms (~{1/med:.0f} Hz); no declared rate column')


def report_units(res, report):
    flagged = 0
    for n, st in res['ustat'].items():
        if st.infinite:
            report.fail('units', f'{n}: {st.infinite:,} infinite values')
            flagged += 1
        if st.n_beyond:
            frac = st.n_beyond / max(1, st.finite)
            sev = report.fail if frac > UNIT_SYSTEMIC_FRAC else report.warn
            kind = 'systemic' if frac > UNIT_SYSTEMIC_FRAC else 'rare'
            sev('units', f'{n}: {st.n_beyond:,} values ({frac:.2%}, {kind}) beyond '
                         f'+/-{st.limit:g} (max |{st.absmax:.2f}|)')
            flagged += 1
    if flagged == 0:
        report.ok('units', 'all unit-bearing columns within magnitude limits, no infinities')


def report_degrees(res, report):
    # Systemic radians-vs-degrees detection, complementary to the 2pi ceiling.
    for n, st in res['ustat'].items():
        if not n.endswith('_rad'):
            continue
        if st.finite < MIN_N or st.limit != 2 * math.pi:
            continue
        frac = st.n_beyond / st.finite
        if frac > DEG_FRAC_WARN and st.absmax > 6.3:
            report.warn('degrees', f'{n}: {frac:.1%} of samples exceed 2pi (max |{st.absmax:.1f}|) '
                                   f'- values may be in degrees, not radians')


def report_dead(res, report):
    dead = [n for n, st in res['ustat'].items() if st.total and st.finite == 0]
    for n in sorted(dead):
        report.warn('dead-col', f'{n}: present but entirely NaN (dead column)')


def report_grf(res, report):
    for s, g in res['gstat'].items():
        col = res['grf_v'][s]
        if g.finite == 0:
            report.warn('grf', f'{col}: all NaN')
            continue
        loaded = g.loaded.values()
        med = float(np.median(loaded)) if loaded.size else float('nan')
        p95 = float(np.percentile(loaded, 95)) if loaded.size else float('nan')
        frac_neg = g.n_neg / g.finite
        if loaded.size and med < 0:
            report.fail('grf', f'{col}: loaded median {med:.2f} BW is negative (sign inverted?)')
        elif loaded.size and not (GRF_PEAK_LO <= p95 <= GRF_PEAK_HI):
            report.warn('grf', f'{col}: loaded p95 {p95:.2f} BW outside plausible '
                               f'[{GRF_PEAK_LO}, {GRF_PEAK_HI}] (scaling/units?)')
        elif frac_neg > GRF_NEG_FRAC_WARN:
            report.warn('grf', f'{col}: {frac_neg:.1%} of samples < -{GRF_NEG_TOL_BW} BW')
        else:
            report.ok('grf', f'{col}: non-negative, loaded median {med:.2f} BW, p95 {p95:.2f} BW')


def report_cop(res, report):
    for s, cols in res['cop_cols'].items():
        vcol = f'cop_vertical_{s}_m'
        vstat = res['cstat'].get(vcol)
        frame = None
        if vstat is not None and vstat.finite:
            frame = 'ankle-local' if vstat.absmax < COP_VERT_FLAT_M else 'lab/world'
        for c in cols:
            cs = res['cstat'][c]
            if cs.finite == 0:
                continue
            if cs.n_absurd:
                report.fail('cop', f'{c}: {cs.n_absurd:,} samples |CoP| > {COP_ABSURD_M} m '
                                   f'(physically impossible)')
            elif c == vcol:
                pass  # vertical is the frame discriminator; reported below
            elif cs.n_beyond_ankle:
                # The standard mandates an ankle-local CoP frame, so a horizontal
                # CoP beyond foot scale is out-of-bounds regardless of the detected
                # frame. Systemic (>1%) => FAIL, a rare transient => WARN.
                frac = cs.n_beyond_ankle / cs.finite
                sev = report.fail if frac > UNIT_SYSTEMIC_FRAC else report.warn
                sev('cop', f'{c}: {frac:.1%} of samples |CoP| > {COP_ANKLE_MAX_M} m '
                           f'(ankle frame required; max |{cs.absmax:.2f}| m)')
            elif frame == 'ankle-local':
                report.ok('cop', f'{c}: within +/-{COP_ANKLE_MAX_M} m (ankle-local frame)')
            # off-contact mask leak
            if cs.leak:
                frac = cs.leak / max(1, cs.finite)
                if frac > COP_LEAK_FRAC_WARN:
                    report.warn('cop', f'{c}: {frac:.0%} of finite CoP occurs off-contact '
                                       f'(mask leak?)')
        if frame == 'ankle-local':
            report.ok('cop', f'{s}: CoP reference frame is ankle-local '
                             f'(|cop_vertical| max {vstat.absmax:.3f} m)')
        elif frame == 'lab/world':
            report.fail('cop', f'{s}: CoP is not in the mandated ankle-local frame '
                               f'(|cop_vertical| reaches {vstat.absmax:.2f} m; expected ~0)')


# --------------------------------------------------------------------------- #
# Relational checks on a capped prefix of rows (bounded memory)
# --------------------------------------------------------------------------- #
def read_capped(path, cols, max_rows=CAP_ROWS):
    pf = pq.ParquetFile(path)
    frames = []
    n = 0
    for batch in pf.iter_batches(columns=cols, batch_size=BATCH_ROWS, use_threads=False):
        frames.append(batch.to_pandas())
        n += batch.num_rows
        if n >= max_rows:
            break
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=cols)


def _robust_std(x):
    x = x[np.isfinite(x)]
    if x.size < MIN_N:
        return float('nan')
    return float(np.median(np.abs(x - np.median(x))) * 1.4826)


def check_velocity_derivative(path, names, report):
    joints = [j for j in VEL_JOINTS
              if f'{j}_angle_ipsi_rad' in names and f'{j}_velocity_ipsi_rad_s' in names]
    if not joints or 'step' not in names or 'time_s' not in names:
        return
    checked = 0
    for j in joints:
        ac, vc = f'{j}_angle_ipsi_rad', f'{j}_velocity_ipsi_rad_s'
        df = read_capped(path, ['step', 'time_s', ac, vc])
        st = df['step'].to_numpy()
        t = df['time_s'].to_numpy(float)
        a = df[ac].to_numpy(float)
        v = df[vc].to_numpy(float)
        same = st[1:] == st[:-1]
        dt = np.diff(t)
        deriv = np.divide(np.diff(a), dt, out=np.full(dt.shape, np.nan), where=dt > 0)
        vmid = 0.5 * (v[1:] + v[:-1])
        m = same & (dt > 0) & np.isfinite(deriv) & np.isfinite(vmid)
        if m.sum() < MIN_N:
            continue
        checked += 1
        r = float(np.corrcoef(deriv[m], vmid[m])[0, 1])
        ratio = _robust_std(vmid[m]) / (_robust_std(deriv[m]) or float('nan'))
        if r < VEL_CORR_FAIL:
            report.fail('velocity', f'{vc}: corr with d(angle)/dt = {r:.2f} '
                                    f'(sign inverted vs {ac}?)')
        elif r < VEL_CORR_WARN:
            report.warn('velocity', f'{vc}: corr with d(angle)/dt = {r:.2f} '
                                    f'(weak; noisy or mismatched)')
        elif not (VEL_SCALE_LO <= ratio <= VEL_SCALE_HI):
            report.warn('velocity', f'{vc}: scale vs d(angle)/dt = {ratio:.2f}x '
                                    f'(unit mismatch, e.g. deg/s vs rad/s?)')
        else:
            report.ok('velocity', f'{j}: velocity consistent with d(angle)/dt (corr {r:.3f})')
    if checked == 0:
        report.warn('velocity', 'angle/velocity pairs present but too few paired samples to check')


def check_segment_chain(path, names, report):
    for joint, prox, dist in CHAIN_TRIPLES:
        jc = f'{joint}_ipsi_rad'
        pcol, dcol = f'{prox}_ipsi_rad', f'{dist}_ipsi_rad'
        if not all(c in names for c in (jc, pcol, dcol)):
            continue
        df = read_capped(path, [jc, pcol, dcol])
        k = df[jc].to_numpy(float)
        chain = df[pcol].to_numpy(float) - df[dcol].to_numpy(float)
        m = np.isfinite(k) & np.isfinite(chain)
        if m.sum() < MIN_N:
            continue
        r = float(np.corrcoef(k[m], chain[m])[0, 1])
        if r < -CHAIN_CORR_WARN:
            report.warn('chain', f'{joint}: corr with ({prox}-{dist}) = {r:.2f} '
                                 f'(sign convention differs from joint angle?)')
        elif abs(r) < CHAIN_CORR_WARN:
            report.warn('chain', f'{joint}: corr with ({prox}-{dist}) = {r:.2f} '
                                 f'(segment/joint chain inconsistent?)')
        else:
            report.ok('chain', f'{joint} consistent with ({prox}-{dist}) chain (corr {r:.2f})')


def check_ipsi_contra(path, names, report):
    bases = ('knee_flexion_angle', 'hip_flexion_angle', 'ankle_dorsiflexion_angle',
             'grf_vertical', 'knee_flexion_moment')
    suffixes = ('_rad', '_BW', '_Nm_kg', '_rad_s')
    checked = 0
    for base in bases:
        for suf in suffixes:
            ic, cc = f'{base}_ipsi{suf}', f'{base}_contra{suf}'
            if not (ic in names and cc in names):
                continue
            df = read_capped(path, [ic, cc])
            a = df[ic].to_numpy(float)
            b = df[cc].to_numpy(float)
            mask = np.isfinite(a) & np.isfinite(b)
            if mask.sum() < MIN_N:
                break
            checked += 1
            a, b = a[mask], b[mask]
            if np.allclose(a, b):
                report.fail('ipsi/contra', f'{ic} identical to {cc} (routing bug?)')
                break
            r = float(np.corrcoef(a, b)[0, 1])
            sa, sb = _robust_std(a), _robust_std(b)
            ratio = sa / sb if sb else float('nan')
            if r > 0.999:
                report.warn('ipsi/contra', f'{ic} vs {cc} corr={r:.4f} (suspiciously identical)')
            elif np.isfinite(ratio) and not (SYM_STD_LO <= ratio <= SYM_STD_HI):
                report.warn('ipsi/contra', f'{base}: ipsi/contra robust-std ratio {ratio:.2f} '
                                           f'(scale asymmetry)')
            else:
                report.ok('ipsi/contra', f'{base}: ipsi/contra distinct (corr={r:.2f}, '
                                         f'std ratio {ratio:.2f})')
            break
    if checked == 0:
        report.warn('ipsi/contra', 'no ipsi/contra pairs found to compare')


# --------------------------------------------------------------------------- #
# Coverage
# --------------------------------------------------------------------------- #
def coverage_table(path, names):
    """Per-task coverage via a pyarrow group_by (avoids materializing string columns)."""
    if 'task' not in names:
        return []
    has_subject = 'subject' in names
    has_step = 'step' in names
    has_grf = 'grf_vertical_ipsi_BW' in names
    read = ['task'] + [c for c in ('subject', 'step') if c in names]
    if has_grf:
        read.append('grf_vertical_ipsi_BW')

    table = pq.read_table(path, columns=read, use_threads=True)
    aggs = [('task', 'count')]
    if has_subject:
        aggs.append(('subject', 'count_distinct'))
    if has_step:
        aggs.append(('step', 'count_distinct'))
    if has_grf:
        aggs.append(('grf_vertical_ipsi_BW', 'count'))  # non-null count
    grouped = table.group_by('task').aggregate(aggs).to_pydict()

    tasks = [str(t) for t in grouped['task']]
    total = grouped['task_count']
    subj = grouped.get('subject_count_distinct')
    wins = grouped.get('step_count_distinct')
    grf_nonnull = grouped.get('grf_vertical_ipsi_BW_count')

    rows = []
    for i, task in enumerate(tasks):
        rows.append({
            'task': task,
            'subjects': int(subj[i]) if subj is not None else None,
            'windows': int(wins[i]) if wins is not None else None,
            'rows': int(total[i]),
            'grf_coverage': (float(grf_nonnull[i] / total[i])
                             if grf_nonnull is not None and total[i] else None),
        })
    rows.sort(key=lambda r: -r['rows'])
    return rows


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def audit(path: Path):
    names = pq.ParquetFile(path).schema.names
    report = Report()

    res = stream_pass(path, names)
    report_time(res, report)
    report_sampling(res, report)
    report_units(res, report)
    report_degrees(res, report)
    report_dead(res, report)
    report_grf(res, report)
    report_cop(res, report)

    check_velocity_derivative(path, names, report)
    check_segment_chain(path, names, report)
    check_ipsi_contra(path, names, report)

    coverage = coverage_table(path, names)
    return report, coverage


def print_report(path, report, coverage):
    print(f'\n=== Time-series convention audit: {path} ===')
    order = {'FAIL': 0, 'WARN': 1, 'OK': 2}
    icon = {'FAIL': 'X', 'WARN': '!', 'OK': '.'}
    for sev, check, msg in sorted(report.findings, key=lambda f: (order[f[0]], f[1])):
        print(f'  [{icon[sev]}] {sev:4s} {check:12s} {msg}')
    if coverage:
        print('\n  Per-task coverage:')
        print(f'    {"task":22s} {"subj":>4s} {"windows":>8s} {"rows":>12s} {"grf":>6s}')
        for r in coverage:
            cov = f'{r["grf_coverage"]*100:.0f}%' if r['grf_coverage'] is not None else '-'
            print(f'    {r["task"]:22s} {str(r["subjects"]):>4s} {str(r["windows"]):>8s} '
                  f'{r["rows"]:>12,d} {cov:>6s}')
    c = report.counts()
    print(f'\n  Summary: {c["FAIL"]} FAIL, {c["WARN"]} WARN, {c["OK"]} OK')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('datasets', nargs='+', type=Path)
    parser.add_argument('--strict', action='store_true', help='treat WARN as failure')
    parser.add_argument('--json', type=Path, help='write findings + coverage to JSON')
    args = parser.parse_args()

    failed = False
    payload = {}
    for path in args.datasets:
        try:
            report, coverage = audit(path)
        except Exception as exc:  # noqa: BLE001 - surface, do not crash the batch
            print(f'\n=== {path} ===\n  [X] FAIL audit        {type(exc).__name__}: {exc}')
            failed = True
            payload[str(path)] = {'error': f'{type(exc).__name__}: {exc}'}
            continue
        print_report(path, report, coverage)
        c = report.counts()
        failed |= c['FAIL'] > 0 or (args.strict and c['WARN'] > 0)
        payload[str(path)] = {
            'findings': [{'severity': s, 'check': ch, 'message': m} for s, ch, m in report.findings],
            'coverage': coverage,
            'counts': c,
        }

    if args.json:
        args.json.write_text(json.dumps(payload, indent=2), encoding='utf-8')
        print(f'\nWrote {args.json}')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
