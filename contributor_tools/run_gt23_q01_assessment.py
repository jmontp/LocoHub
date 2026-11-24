#!/usr/bin/env python3
"""GT23-Q01: assess the GT23-E01 export with structure checks and coarse physical limits.

Rule (ported from UM21-Q01, D-UM21-Q01-1 = B, applied here as the least-change default): structure plus coarse
physical limits, blatant errors only; no literature-fitted ranges; nothing tuned to a pass rate. Layers are kept apart.

  structural layer    S1 grid (150 samples, 0 to 100 percent inclusive; time table: increasing, 200 Hz clock),
                      S2 id parses, subject / recording / side agree with the columns and with the lineage file,
                      S3 unique identities, constant metadata inside an observation, transfers come in left+right pairs,
                      S4 spans lie inside their continuous recording, S5 side check on cycles (the ipsilateral leg is
                      loaded in the first 40 percent of the cycle more than in the last 40 percent; reported as a
                      structural side check), L4 non-finite samples reported as missing (sample ranges),
                      L3 cycle duration outside 0.4-2.5 s (reported, never a filter).
  source-fidelity     bound to the E01 run summary hashes and the independent E01 readback report; not redone here.
  plausibility layer  L1 joint angle beyond a textbook end of range plus 30 deg (hip, knee, ankle),
                      L2 jump of more than 30 deg between adjacent samples (all sagittal angles),
                      L5 foot-frame pressure point more than 0.5 m (anterior) or 0.3 m (vertical, lateral) from the
                      foot origin: a blatant limit added to confirm the stairs pressure point (the C06 stairs bug put it
                      0.4 to 0.9 m below the foot).

Units are read from the column suffix and must be known; an unknown suffix refuses to run. Angle limits are in degrees
and radian columns are converted first (the UM21 v1 lesson). A column with no limit is "unchecked", never pass. A held
column (all missing, listed in held_signals) is "not_checked_no_column". Non-finite is missing, never pass.
scientific_approval is false. Run only through contributor_tools.guarded_launcher.
"""
from __future__ import annotations

import os
for _key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_key, "1")
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")
import argparse
import hashlib
import json
from pathlib import Path
import re
import resource
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TASK_ID = "GT23-Q01"
RUNNER = "contributor_tools/run_gt23_q01_assessment.py"
BASE = "converted_datasets/reconversion_v2"
SUBJECTS = ("AB01", "AB02", "AB03", "AB05", "AB06", "AB07", "AB08", "AB09", "AB10", "AB11", "AB12", "AB13")
PILOT_SUBJECTS = ("AB07", "AB12")  # AB07: right-foot offset; AB12: stairs. Chosen before any limit was run.
README = "docs/quality/audits/source_evidence/gt23/publisher-readme.txt"
C06_SUMMARY = f"{BASE}/gt23_c06_summary3/summary.json"
E01_SUMMARY = f"{BASE}/gt23_e01_summary/summary.json"
E01_AUDIT_SUMMARY = f"{BASE}/gt23_e01_audit_summary/audit_summary.json"
RSS_CAP_MIB = 300.0
ADDRESS_SPACE_MIB = 768
MIN_AVAILABLE_BYTES = 2 * 1024 ** 3
N_SAMPLES = 150
READ_BATCH_ROWS = 4096
TIME_RATE_HZ = 200.0
TIME_DT_TOL_S = 1e-6
FAIL_LIST_CAP = 2000          # listed failed samples per (observation, channel, limit); the rest is counted
MISSING_RANGE_CAP = 200       # listed missing sample ranges per channel
UNIT_EVIDENCE_TEXT = "Angles rad, speeds rad/s, moments N*m/kg, powers W/kg"

ID_PHASE_RE = re.compile(r"^(AB\d{2})/([A-Za-z0-9_\-]+)/(left|right|both)/(\d+)$")
ID_TIME_RE = re.compile(r"^(AB\d{2})/([A-Za-z0-9_\-]+)/continuous$")

STR_META = ("subject", "source_recording_id", "observation_id", "reference_side", "observation_type", "task", "task_id",
            "task_info", "subject_metadata", "held_signals")
CONST_STR = tuple(c for c in STR_META if c not in ("observation_id", "reference_side"))
CLOCK_COLS = ("source_start_time_s", "source_end_time_s")
AXIS_COLS = ("phase_ipsi", "time_s")
META_COLS = set(STR_META) | set(CLOCK_COLS) | set(AXIS_COLS)
OBS_TYPES = ("individual_cycle", "transfer", "continuous_recording")


class UnitError(ValueError):
    """A column's unit is unknown or its evidence is missing: the assessment refuses to run."""


class InputError(ValueError):
    """An input differs from its recorded identity: the assessment refuses to run."""


def unit_of(col):
    """Unit of one published signal column, from its suffix. Unknown suffix raises UnitError (nothing is guessed)."""
    if col.startswith("heading_lab_"):
        return "unitless"
    for suffix, unit in (("_rad_s", "rad/s"), ("_rad", "rad"), ("_Nm_kg", "N*m/kg"), ("_W_kg", "W/kg"),
                         ("_BW", "BW"), ("_N", "N"), ("_m", "m")):
        if col.endswith(suffix):
            return unit
    raise UnitError(f"unknown unit for column {col!r}; refusing to assess")


def check_unit_evidence(readme_text):
    """The export README must state the radian / per-kilogram units the suffixes encode."""
    if UNIT_EVIDENCE_TEXT not in (readme_text or ""):
        raise UnitError(f"the export README does not state {UNIT_EVIDENCE_TEXT!r}")
    return UNIT_EVIDENCE_TEXT


# L1: draft bounds, textbook end of range widened by 30 degrees (identical to UM21-Q01; written before any GT23 data).
L1_BOUNDS_DEG = {"hip_flexion_angle_": (-50.0, 150.0), "knee_flexion_angle_": (-30.0, 165.0),
                 "ankle_dorsiflexion_angle_": (-80.0, 50.0)}
L2_JUMP_DEG = 30.0
L2_PREFIXES = ("pelvis_sagittal_angle", "thigh_sagittal_angle_", "shank_sagittal_angle_", "foot_sagittal_angle_",
               "hip_flexion_angle_", "knee_flexion_angle_", "ankle_dorsiflexion_angle_")
L3_RANGE_S = (0.4, 2.5)
# L5: foot-frame pressure point (metres from the foot origin 100 mm ahead of the ankle). Blatant bound only.
L5_BOUNDS_M = {"cop_anterior_": (-0.5, 0.5), "cop_vertical_": (-0.3, 0.3), "cop_lateral_": (-0.3, 0.3)}
S5_EARLY = slice(0, 60)     # phase samples 0..59 = 0 to 40 percent
S5_LATE = slice(90, 150)    # phase samples 90..149 = 60 to 100 percent
LOAD_N = 20.0               # loaded when vertical force is at least this (the C06 pressure-point threshold)
FLIGHT_MIN_SAMPLES = 3

CYCLE_ONLY_NOTE = "S5 and the flight check are computed on individual cycles only"

PROFILE = {
    "profile_id": "gt23_q01_coarse_limits_v1",
    "decision": "D-UM21-Q01-1 = B (structure plus coarse physical limits, blatant errors only), applied to GT23 as the "
                "least-change default; logged in the handoff",
    "review_status": "draft_limits_unreviewed_scientific_approval_false",
    "population": "able-bodied adults (Georgia Tech 2023, 12 participants, many tasks)",
    "units": "limits are in degrees for angles (radian columns are converted with numpy.degrees first) and metres for "
             "the pressure point; units come from the column suffix and an unknown suffix refuses to run",
    "applicability": "every exported observation type (individual_cycle, transfer, continuous_recording); the limits "
                     "are physical limits of the body or foot, not task profiles, so they do not depend on task",
    "no_tuning": "Limits were written before any GT23 data were read and are not changed to reach a pass rate. "
                 "L1, L2, L3 are the UM21-Q01 values; L5 is new and is chosen so the pre-fix stairs error is visible.",
    "limits": {
        "L1": {"layer": "plausibility", "bounds_deg": {k.rstrip("_"): v for k, v in L1_BOUNDS_DEG.items()},
               "evidence": "textbook end of range plus a 30 degree margin chosen here, not from literature (UM21-Q01 text; "
                           "the textbook values were never confirmed against a primary text)"},
        "L2": {"layer": "plausibility", "threshold_deg": L2_JUMP_DEG, "columns": [p.rstrip("_") for p in L2_PREFIXES],
               "evidence": "physical argument only: no body segment turns 30 degrees between adjacent samples "
                           "(phase table: adjacent samples are 1/149 of a cycle apart; time table: 5 ms)"},
        "L5": {"layer": "plausibility", "bounds_m": {k.rstrip("_"): v for k, v in L5_BOUNDS_M.items()},
               "evidence": "a foot is about 0.25 m long and 0.1 m wide; a pressure point more than 0.5 m ahead or "
                           "behind, or 0.3 m above/below or beside the foot origin, is not on the foot. Chosen, not fitted."},
        "L4": {"layer": "structural", "what": "non-finite sample reported as missing (ranges); never a pass"},
        "L3": {"layer": "structural", "range_s": L3_RANGE_S, "what": "cycle duration; reported, never a filter"},
        "S5": {"layer": "structural", "what": "side check on individual cycles: mean ipsilateral vertical force in the first "
                                              "40 percent of the cycle must exceed the mean in the last 40 percent; a "
                                              "swapped side puts the stance at about 50 to 100 percent",
               "applies_when": "all 150 ipsilateral vertical force samples finite and a peak of at least 20 N"},
    },
    "stairs_cop_rule": "The stairs pressure point is held only if more than 1 percent of its finite samples fail L5, or "
                       "the C06 outside-foot share of stairs is higher than that of level walking (normal_walk). "
                       "Written before the stairs data were read.",
    "channel_coverage": {
        "pelvis_sagittal_angle": "L2 only (no cited range)",
        "thigh/shank/foot sagittal angle": "L2 only",
        "hip/knee flexion angle": "L1 + L2", "ankle dorsiflexion angle": "L1 + L2; offset unverified (AB07 about -9 to -13 deg)",
        "cop_anterior/vertical/lateral (foot frame)": "L5 only",
        "joint velocities, moments, powers, forces (N and BW), lab-axis pressure point, heading, subtalar":
            "unchecked (no limit)",
    },
}

LIMITATION_KEYS = ("shuffle_not_steady_walking", "unlabelled_walking_under_functional_task", "run_label_check",
                   "mass_estimated", "ab09_divisor", "ab07_right_foot_offset", "curb_up_cop_held",
                   "window_span_both_legs", "nm_rerun_limit")


# ---------------------------------------------------------------- helpers
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _peak_rss_mib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def _mem_available():
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    return 0


def column_limits(col):
    """[(limit, lo, hi, scale)] for one column. scale 'deg' = convert radians to degrees first; None = as is."""
    out = []
    for prefix, (lo, hi) in L1_BOUNDS_DEG.items():
        if col.startswith(prefix) and col.endswith("_rad"):
            out.append(("L1", lo, hi, "deg"))
    if col.endswith("_rad") and any(col.startswith(p) for p in L2_PREFIXES):
        out.append(("L2", None, L2_JUMP_DEG, "deg"))
    for prefix, (lo, hi) in L5_BOUNDS_M.items():
        if col.startswith(prefix) and col.endswith("_m"):
            out.append(("L5", lo, hi, None))
    return out


def parse_id(oid, kind):
    """dict with subject, recording, side (id side code) and start for a phase id, or None."""
    if kind == "time":
        m = ID_TIME_RE.match(oid or "")
        return None if not m else {"subject": m.group(1), "recording": m.group(2), "side": "continuous", "start": None}
    m = ID_PHASE_RE.match(oid or "")
    return None if not m else {"subject": m.group(1), "recording": m.group(2), "side": m.group(3), "start": int(m.group(4))}


def runs_of(mask):
    """[start, end] inclusive index ranges of True runs."""
    idx = np.flatnonzero(mask)
    if not len(idx):
        return []
    cuts = np.flatnonzero(np.diff(idx) > 1)
    s = np.concatenate([[idx[0]], idx[cuts + 1]])
    e = np.concatenate([idx[cuts], [idx[-1]]])
    return [[int(a), int(b)] for a, b in zip(s, e)]


def flight_stats(ipsi_n, contra_n):
    """Share of samples with both legs unloaded and the longest such run, for finite 150-sample forces."""
    both = (ipsi_n < LOAD_N) & (contra_n < LOAD_N)
    rr = runs_of(both)
    longest = max((b - a + 1 for a, b in rr), default=0)
    return float(both.mean()), int(longest)


def side_check(ipsi_n):
    """S5 for one cycle. Returns (state, early_mean_N, late_mean_N)."""
    x = np.asarray(ipsi_n, dtype=float)
    if len(x) != N_SAMPLES or not np.isfinite(x).all() or float(np.max(x)) < LOAD_N:
        return "unchecked_no_ipsilateral_force", None, None
    early, late = float(np.mean(x[S5_EARLY])), float(np.mean(x[S5_LATE]))
    return ("pass" if early > late else "fail"), early, late


# ---------------------------------------------------------------- one observation, fed in chunks
class ColState:
    __slots__ = ("n_finite", "n_rows", "missing", "missing_open", "prev", "fails", "n_failed", "n_unlisted", "failed_limits",
                 "max_abs")

    def __init__(self):
        self.n_finite = 0
        self.n_rows = 0
        self.missing = []        # [start, end] ranges (capped)
        self.missing_open = False
        self.prev = None         # last sample (converted) of the previous chunk
        self.fails = []
        self.n_failed = {}
        self.n_unlisted = {}
        self.failed_limits = set()
        self.max_abs = 0.0


class Observation:
    def __init__(self, key, kind, columns, limits):
        self.key, self.kind = key, kind
        self.columns, self.limits = columns, limits
        self.rows = 0
        self.cols = {c: ColState() for c in columns}
        self.meta = {}
        self.meta_problems = set()
        self.clock = {}
        self.axis = []
        self.t_prev = None
        self.dt_bad = []         # [sample_index, dt]
        self.n_dt_bad = 0
        self.dt_nonincreasing = 0
        self.t_first = None
        self.t_last = None
        self.force = {"ipsi": [], "contra": []}

    def _emit(self, st, col, limit, local_idx, values, reasons, axis_slice, offset):
        for li, v, why in zip(local_idx, values, reasons):
            st.n_failed[limit] = st.n_failed.get(limit, 0) + 1
            st.failed_limits.add(limit)
            if sum(1 for f in st.fails if f["limit"] == limit) >= FAIL_LIST_CAP:
                st.n_unlisted[limit] = st.n_unlisted.get(limit, 0) + 1
                continue
            st.fails.append({"observation_id": self.key[0], "reference_side": self.key[1],
                             "table": "time" if self.kind == "time" else "phase", "channel": col, "limit": limit,
                             "sample_index": int(offset + li),
                             ("time_s" if self.kind == "time" else "phase_percent"): float(axis_slice[li]),
                             "value": float(v), "reason": why})

    def feed(self, data, strings, a, e):
        """Rows a..e of a batch. data: column -> float array; strings: column -> decoded value of the run's first row."""
        n = e - a
        off = self.rows
        axis = data["time_s"][a:e] if self.kind == "time" else data["phase_ipsi"][a:e]
        for c, v in strings.items():
            if c in self.meta and self.meta[c] != v:
                self.meta_problems.add(c)
            self.meta.setdefault(c, v)
        for c in CLOCK_COLS:
            x = data[c][a:e]
            if not np.all(x == x[0]):
                self.meta_problems.add(c)
            if c in self.clock and self.clock[c] != float(x[0]):
                self.meta_problems.add(c)
            self.clock.setdefault(c, float(x[0]))
        if self.kind == "time":
            t = axis
            self.t_first = float(t[0]) if self.t_first is None else self.t_first
            tt = np.concatenate([[self.t_prev], t]) if self.t_prev is not None else t
            if len(tt) > 1:
                dt = np.diff(tt)
                base = 0 if self.t_prev is not None else 1
                self.dt_nonincreasing += int(np.sum(~(dt > 0)))
                bad = np.flatnonzero(~(np.abs(dt - 1.0 / TIME_RATE_HZ) <= TIME_DT_TOL_S))
                self.n_dt_bad += len(bad)
                for j in bad[:50 - len(self.dt_bad)]:
                    self.dt_bad.append([int(off + j + base), float(dt[j])])
            self.t_prev = float(t[-1])
            self.t_last = self.t_prev
        else:
            self.axis.append(axis.copy())
        for c in self.columns:
            raw = data[c][a:e]
            st = self.cols[c]
            fin = np.isfinite(raw)
            st.n_rows += n
            st.n_finite += int(fin.sum())
            if fin.any():
                st.max_abs = max(st.max_abs, float(np.max(np.abs(raw[fin]))))
            miss = ~fin
            if miss.any():
                rr = runs_of(miss)
                if st.missing_open and rr and rr[0][0] == 0 and st.missing:
                    st.missing[-1][1] = off + rr[0][1]
                    rr = rr[1:]
                for s, f in rr:
                    if len(st.missing) < MISSING_RANGE_CAP:
                        st.missing.append([off + s, off + f])
            st.missing_open = bool(miss[-1])
            lims = self.limits.get(c)
            if lims:
                x = np.degrees(raw) if lims[0][3] == "deg" else raw
                for limit, lo, hi, _ in lims:
                    if limit in ("L1", "L5"):
                        idx = np.flatnonzero(fin & ((x < lo) | (x > hi)))
                        if len(idx):
                            unit = "deg" if limit == "L1" else "m"
                            self._emit(st, c, limit, idx, x[idx],
                                       [f"{c} {x[i]:.3f} {unit} outside [{lo:g}, {hi:g}] {unit}" for i in idx], axis, off)
                    else:  # L2
                        xe = np.concatenate([[st.prev], x]) if st.prev is not None else x
                        if len(xe) > 1:
                            d = np.diff(xe)
                            ok = np.isfinite(xe[1:]) & np.isfinite(xe[:-1])
                            idx = np.flatnonzero(ok & (np.abs(d) > hi))
                            base = 0 if st.prev is not None else 1
                            if len(idx):
                                self._emit(st, c, "L2", idx + base, d[idx],
                                           [f"{c} changes {d[i]:.1f} deg between adjacent samples (limit {hi:g})" for i in idx],
                                           axis, off)
                        st.prev = float(x[-1])
                if all(l[0] != "L2" for l in lims):
                    st.prev = None
            if self.kind == "phase":
                if c == "grf_vertical_ipsi_N":
                    self.force["ipsi"].append(raw.copy())
                elif c == "grf_vertical_contra_N":
                    self.force["contra"].append(raw.copy())
        self.rows += n


def finish_observation(obs, lineage, subject, time_ranges, held_expected_extra=None):
    """Entry and failures of one finished observation."""
    oid, side = obs.key
    kind = obs.kind
    problems = []
    parsed = parse_id(oid, kind)
    m = obs.meta
    if parsed is None:
        problems.append("S2 id does not parse")
    else:
        if not (parsed["subject"] == m.get("subject") == subject):
            problems.append(f"S2 subject differs: id {parsed['subject']!r}, column {m.get('subject')!r}, participant {subject!r}")
        if m.get("source_recording_id") != f"{parsed['subject']}/{parsed['recording']}":
            problems.append("S2 source_recording_id differs from the id")
        otype = m.get("observation_type")
        if kind == "time":
            if otype != "continuous_recording" or side != "none":
                problems.append("S2 time observation must be continuous_recording with reference_side none")
        elif otype == "individual_cycle":
            if side not in ("left", "right") or parsed["side"] != side:
                problems.append(f"S2 cycle reference_side {side!r} differs from the id side {parsed['side']!r}")
        elif otype == "transfer":
            if side not in ("left", "right") or parsed["side"] != "both":
                problems.append("S2 transfer must have id side 'both' and reference_side left or right")
        else:
            problems.append(f"S2 observation_type {otype!r} not allowed in the phase table")
    if obs.meta_problems:
        problems.append(f"S3 values change inside the observation: {sorted(obs.meta_problems)}")
    lin = lineage.get((("time" if kind == "time" else "phase"), oid, side))
    if lin is None:
        problems.append("S3 observation not in the lineage file")
    else:
        if lin["rows"] != obs.rows:
            problems.append(f"S1 {obs.rows} rows, lineage says {lin['rows']}")
        for c, lk in (("source_start_time_s", "source_start_time_s"), ("source_end_time_s", "source_end_time_s")):
            if obs.clock.get(c) != lin[lk]:
                problems.append(f"S3 {c} {obs.clock.get(c)} differs from lineage {lin[lk]}")
        for c, lk in (("task", "task"), ("task_id", "task_id"), ("observation_type", "observation_type")):
            if m.get(c) != lin[lk]:
                problems.append(f"S3 {c} {m.get(c)!r} differs from lineage {lin[lk]!r}")
        if parsed and parsed["start"] is not None and lin.get("start_index") != parsed["start"]:
            problems.append("S2 id start index differs from lineage start_index")
    if kind == "phase":
        if obs.rows != N_SAMPLES:
            problems.append(f"S1 {obs.rows} rows, expected {N_SAMPLES}")
        else:
            ax = np.concatenate(obs.axis)
            if not np.allclose(ax, np.linspace(0.0, 100.0, N_SAMPLES), rtol=0, atol=1e-9):
                problems.append("S1 phase is not the 150-sample grid from 0 to 100 percent inclusive")
    else:
        if obs.dt_nonincreasing:
            problems.append(f"S1 time_s not strictly increasing at {obs.dt_nonincreasing} samples")
        if obs.n_dt_bad:
            problems.append(f"S1 {obs.n_dt_bad} sample intervals differ from {1000 / TIME_RATE_HZ:g} ms (gaps or a different clock)")
        if obs.t_first is not None and obs.clock.get("source_start_time_s") != obs.t_first:
            problems.append("S1 first time_s differs from source_start_time_s")
        if obs.t_last is not None and abs(obs.clock.get("source_end_time_s", np.nan) - obs.t_last) > 1e-9:
            problems.append("S1 last time_s differs from source_end_time_s")
    try:
        held = json.loads(m.get("held_signals") or "null")
        held = held if isinstance(held, dict) else None
    except ValueError:
        held = None
    if held is None:
        problems.append("S3 held_signals is not a JSON object")
        held = {}
    ti = {}
    try:
        ti = json.loads(m.get("task_info") or "{}")
    except ValueError:
        problems.append("S3 task_info is not JSON")
    all_missing = sorted(c for c, s in obs.cols.items() if s.n_finite == 0)
    if sorted(held) != all_missing:
        problems.append("S3 held_signals differ from the all-missing columns: "
                        f"held-only {sorted(set(held) - set(all_missing))[:5]}, missing-only {sorted(set(all_missing) - set(held))[:5]}")
    if kind == "phase" and parsed and parsed["recording"] is not None and lin is not None:
        rng = time_ranges.get(m.get("source_recording_id"))
        a, b = obs.clock.get("source_start_time_s"), obs.clock.get("source_end_time_s")
        if rng is None:
            problems.append("S4 no continuous recording for this span")
        elif not (rng[0] - 1e-9 <= a < b <= rng[1] + 1e-9):
            problems.append(f"S4 span {a}..{b} s outside its recording {rng[0]}..{rng[1]} s")
    otype = m.get("observation_type")
    # stride time (cycles only), reported
    st_s = None
    l3 = None
    if otype == "individual_cycle":
        st_s = obs.clock["source_end_time_s"] - obs.clock["source_start_time_s"]
        l3 = bool(not (L3_RANGE_S[0] <= st_s <= L3_RANGE_S[1]))
    # S5 side check and flight (cycles with both forces present)
    s5, early, late, flight = "not_applicable", None, None, None
    if otype == "individual_cycle" and obs.rows == N_SAMPLES and obs.force["ipsi"]:
        ip, co = np.concatenate(obs.force["ipsi"]), np.concatenate(obs.force["contra"])
        s5, early, late = side_check(ip)
        if s5 == "fail":
            problems.append(f"S5 side check: ipsilateral mean force {early:.0f} N in 0-40 percent is not above {late:.0f} N in 60-100 percent")
        if np.isfinite(ip).all() and np.isfinite(co).all():
            fr, longest = flight_stats(ip, co)
            flight = {"both_unloaded_share": fr, "longest_run_samples": longest, "flight_cycle": bool(longest >= FLIGHT_MIN_SAMPLES)}
    fails, chans, missing, unlisted = [], {}, {}, {}
    for c in obs.columns:
        s = obs.cols[c]
        fails.extend(s.fails)
        lims = obs.limits.get(c) or []
        if s.n_finite == 0:
            state = "not_checked_no_column" if c in held else "unchecked_all_missing_not_held"
        elif s.n_failed:
            state = "fail"
        elif not lims:
            state = "unchecked"
        elif c.startswith("ankle_dorsiflexion_angle_"):
            state = "pass_offset_unverified"
        elif any(l[0] in ("L1", "L5") for l in lims):
            state = "pass"
        else:
            state = "pass_jump_only"
        chans.setdefault(state, []).append(c)
        if 0 < s.n_finite < s.n_rows:
            missing[c] = {"missing_samples": s.n_rows - s.n_finite, "ranges": s.missing}
        if s.n_unlisted:
            unlisted[c] = s.n_unlisted
    failed_limits = sorted({f["limit"] for f in fails} | {l for s in obs.cols.values() for l in s.n_failed})
    failed_channels = sorted(c for c, s in obs.cols.items() if s.n_failed)
    cop_cols = [c for c in obs.columns if c.startswith(("cop_anterior_", "cop_vertical_", "cop_lateral_"))]
    cop = {"finite_samples": int(sum(obs.cols[c].n_finite for c in cop_cols)),
           "failed_L5_samples": int(sum(obs.cols[c].n_failed.get("L5", 0) for c in cop_cols))}
    limits_text = ti.get("limits") or []
    flags = []
    tid = m.get("task_id")
    if tid == "level_shuffle":
        flags.append("shuffle_not_steady_walking")
    if m.get("task") == "functional_task" and tid in ("normal_walk_unlabelled", "incline_walk_unlabelled") \
            and otype == "individual_cycle":
        flags.append("unlabelled_walking_under_functional_task")
    if m.get("task") == "run" and otype == "individual_cycle":
        flags.append("run_label_check")
    if ti.get("mass_note_key") == "rescaled_estimated":
        flags.append("mass_estimated")
    if any(str(x).startswith("AB09 divisor limit") for x in limits_text):
        flags.append("ab09_divisor")
    if any(str(x).startswith("AB07 right-foot") for x in limits_text):
        flags.append("ab07_right_foot_offset")
    if any(str(x).startswith("curb_up foot-frame") for x in limits_text):
        flags.append("curb_up_cop_held")
    if otype == "transfer":
        flags.append("window_span_both_legs")
    if ti.get("mass_note_key") == "rescaled_exact":
        flags.append("nm_rerun_limit")
    entry = {
        "observation_id": oid, "reference_side": side, "table": "time" if kind == "time" else "phase",
        "observation_type": otype, "task": m.get("task"), "task_id": tid, "source_recording_id": m.get("source_recording_id"),
        "rows": obs.rows, "assessed": True,
        "structural": {"state": "fail" if problems else "pass", "problems": problems,
                       "cycle_duration_s": st_s, "L3_duration_outside_range_reported_only": l3,
                       "S5_side_check": s5, "S5_early_mean_N": early, "S5_late_mean_N": late,
                       "missing_samples": missing},
        "flight": flight, "foot_frame_cop": cop,
        "plausibility": {"channel_states": {k: sorted(v) for k, v in sorted(chans.items())},
                         "failed_channels": failed_channels, "failed_limits": failed_limits,
                         "failed_samples": {c: dict(s.n_failed) for c, s in obs.cols.items() if s.n_failed},
                         "failed_samples_not_listed": unlisted},
        "held_signals": held,
        "limitations": flags,
        "mass_note_key": ti.get("mass_note_key"),
        "overall": "failed" if (problems or fails or any(s.n_failed for s in obs.cols.values())) else "no_failure_found",
    }
    return entry, fails


# ---------------------------------------------------------------- reading one table
def read_table(path, kind, subject, lineage, time_ranges, sink):
    """Stream one table in small batches. sink(entry, fails) receives each finished observation."""
    import pyarrow.parquet as pq
    seen, counts = set(), {"rows": 0, "observations": 0}
    state = {"cur": None}
    with open(path, "rb") as fh:
        pf = pq.ParquetFile(fh, buffer_size=0)
        names = pf.schema_arrow.names
        for need in STR_META + CLOCK_COLS + ((AXIS_COLS[1],) if kind == "time" else (AXIS_COLS[0],)):
            if need not in names:
                raise InputError(f"{path} lacks column {need}")
        columns = [c for c in names if c not in META_COLS]
        units = {c: unit_of(c) for c in columns}
        limits = {c: column_limits(c) for c in columns}
        for c, lims in limits.items():
            for limit, _, _, scale in lims:
                if scale == "deg" and units[c] != "rad":
                    raise UnitError(f"{c} is in {units[c]!r}; limits are in degrees, convert first")
        for batch in pf.iter_batches(batch_size=READ_BATCH_ROWS, use_threads=False):
            n = batch.num_rows
            counts["rows"] += n
            enc = {c: batch.column(c).dictionary_encode() for c in STR_META}
            idx = {c: enc[c].indices.to_numpy(zero_copy_only=False) for c in STR_META}
            data = {c: batch.column(c).to_numpy(zero_copy_only=False).astype(float, copy=False)
                    for c in columns + list(CLOCK_COLS) + [AXIS_COLS[1] if kind == "time" else AXIS_COLS[0]]}
            change = np.flatnonzero((np.diff(idx["observation_id"]) != 0) | (np.diff(idx["reference_side"]) != 0)) + 1
            starts = [0] + [int(x) for x in change]
            ends = [int(x) for x in change] + [n]
            for a, e in zip(starts, ends):
                key = (enc["observation_id"].dictionary[int(idx["observation_id"][a])].as_py(),
                       enc["reference_side"].dictionary[int(idx["reference_side"][a])].as_py())
                strings = {}
                for c in CONST_STR:
                    if not np.all(idx[c][a:e] == idx[c][a]):
                        strings[c] = None  # changes inside the run: flagged below
                        state.setdefault("bad_run", set()).add((key, c))
                    else:
                        strings[c] = enc[c].dictionary[int(idx[c][a])].as_py()
                cur = state["cur"]
                if cur is None or cur.key != key:
                    if cur is not None:
                        sink(*finish_observation(cur, lineage, subject, time_ranges))
                    if key in seen:
                        state.setdefault("repeated", []).append(key)
                    seen.add(key)
                    counts["observations"] += 1
                    cur = state["cur"] = Observation(key, kind, columns, limits)
                for c, v in list(strings.items()):
                    if v is None:
                        cur.meta_problems.add(c)
                        del strings[c]
                cur.feed(data, strings, a, e)
        if state["cur"] is not None:
            sink(*finish_observation(state["cur"], lineage, subject, time_ranges))
    return counts, columns, units, sorted(seen), state.get("repeated", [])


# ---------------------------------------------------------------- one participant
def root_for(subject):
    return f"{BASE}/gt23_e01_batch_{subject}"


def load_lineage(root):
    out = {}
    with open(Path(root) / "observations.jsonl") as f:
        for line in f:
            d = json.loads(line)
            k = (d["table"], d["observation_id"], d["reference_side"])
            if k in out:
                raise InputError(f"duplicate lineage identity {k}")
            out[k] = d
    return out


def source_fidelity(subject, root):
    """Identity of the export, bound to the E01 run summary and the independent E01 readback."""
    rs = json.loads((Path(root) / "run_summary.json").read_text())
    hashes = {}
    for name in ("phase.parquet", "time.parquet", "observations.jsonl", "exclusions.jsonl", "authors_windows.jsonl",
                 "recordings.jsonl"):
        got = sha256_file(Path(root) / name)
        hashes[name] = {"sha256": got, "equals_e01_run_summary": got == rs["sha256"][name]}
        if got != rs["sha256"][name]:
            raise InputError(f"{root}/{name} differs from the E01 run summary hash")
    audit_path = ROOT / BASE / f"gt23_e01_audit_{subject}" / "audit_report.json"
    audit = json.loads(audit_path.read_text())
    failed = sorted(k for k, v in audit["checks"].items() if not v.get("passed"))
    if audit.get("status") not in (None, "pass") and failed:
        raise InputError(f"E01 readback of {subject} has failed checks: {failed[:3]}")
    readme = (Path(root) / "README.md").read_text()
    return {"e01_run_summary": rs, "file_hashes": hashes,
            "e01_readback": {"path": str(audit_path.relative_to(ROOT)), "sha256": sha256_file(audit_path),
                             "status": audit.get("status"), "checks": len(audit["checks"]), "failed_checks": failed},
            "unit_evidence": check_unit_evidence(readme)}


def new_totals():
    return {"observations": 0, "overall": {}, "by_kind": {}, "limitations": {}, "channel_states": {},
            "fail_obs_by_limit": {}, "fail_samples_by_limit": {}, "fail_samples_by_limit_channel": {},
            "fail_obs_by_task_limit": {}, "structural_fail_by_problem": {}, "cycles_by_side": {}, "s5": {},
            "flight": {}, "cop_by_task": {}, "held_by_column": {}, "worst": [], "failing": []}


def accumulate(tot, e, fails):
    tot["observations"] += 1
    tot["overall"][e["overall"]] = tot["overall"].get(e["overall"], 0) + 1
    kind = e["observation_type"]
    tot["by_kind"][kind] = tot["by_kind"].get(kind, 0) + 1
    for fl in e["limitations"]:
        d = tot["limitations"].setdefault(fl, {"observations": 0, "recordings": [], "tasks": {}})
        d["observations"] += 1
        if e["source_recording_id"] not in d["recordings"]:
            d["recordings"].append(e["source_recording_id"])
        d["tasks"][e["task_id"]] = d["tasks"].get(e["task_id"], 0) + 1
    for state, chs in e["plausibility"]["channel_states"].items():
        for ch in chs:
            tot["channel_states"].setdefault(ch, {}).setdefault(state, 0)
            tot["channel_states"][ch][state] += 1
            if state == "not_checked_no_column":
                tot["held_by_column"][ch] = tot["held_by_column"].get(ch, 0) + 1
    for lim in e["plausibility"]["failed_limits"]:
        tot["fail_obs_by_limit"][lim] = tot["fail_obs_by_limit"].get(lim, 0) + 1
        t = tot["fail_obs_by_task_limit"].setdefault(e["task_id"], {})
        t[lim] = t.get(lim, 0) + 1
    for ch, d in e["plausibility"]["failed_samples"].items():
        for lim, n in d.items():
            tot["fail_samples_by_limit"][lim] = tot["fail_samples_by_limit"].get(lim, 0) + n
            k = f"{lim}:{ch}"
            tot["fail_samples_by_limit_channel"][k] = tot["fail_samples_by_limit_channel"].get(k, 0) + n
    for p in e["structural"]["problems"]:
        k = p.split(" ")[0] + " " + " ".join(p.split(" ")[1:4])
        tot["structural_fail_by_problem"][k] = tot["structural_fail_by_problem"].get(k, 0) + 1
    if kind == "individual_cycle":
        sd = tot["cycles_by_side"].setdefault(e["reference_side"], 0)
        tot["cycles_by_side"][e["reference_side"]] = sd + 1
        s5 = e["structural"]["S5_side_check"]
        d = tot["s5"].setdefault(e["task_id"], {})
        d[s5] = d.get(s5, 0) + 1
        if e["flight"] is not None:
            f = tot["flight"].setdefault(e["task_id"], {"cycles_with_both_forces": 0, "flight_cycles": 0, "shares": []})
            f["cycles_with_both_forces"] += 1
            f["flight_cycles"] += int(e["flight"]["flight_cycle"])
            f["shares"].append(round(e["flight"]["both_unloaded_share"], 4))
    c = tot["cop_by_task"].setdefault(e["task"], {"observations": 0, "finite_samples": 0, "failed_L5_samples": 0,
                                                    "observations_with_finite_cop": 0})
    c["observations"] += 1
    c["finite_samples"] += e["foot_frame_cop"]["finite_samples"]
    c["failed_L5_samples"] += e["foot_frame_cop"]["failed_L5_samples"]
    c["observations_with_finite_cop"] += int(e["foot_frame_cop"]["finite_samples"] > 0)
    for f in fails:
        tot["worst"].append(f)
    if len(tot["worst"]) > 400:
        tot["worst"] = sorted(tot["worst"], key=lambda f: -abs(f["value"]))[:100]
    if e["overall"] == "failed":
        tot["failing"].append({"observation_id": e["observation_id"], "reference_side": e["reference_side"],
                               "task_id": e["task_id"], "table": e["table"], "problems": e["structural"]["problems"],
                               "failed": sorted(f"{l}:{c}" for c in e["plausibility"]["failed_channels"]
                                                for l in e["plausibility"]["failed_samples"].get(c, {}))})


def assess_participant(subject, out_dir):
    """Time pass, then phase pass; writes observations.jsonl, failures.jsonl and assessment.json under out_dir."""
    root = ROOT / root_for(subject)
    fid = source_fidelity(subject, root)
    lineage = load_lineage(root)
    out_dir.mkdir(parents=True, exist_ok=False)
    tot, started = new_totals(), time.time()
    with open(out_dir / "observations.jsonl", "x") as fo, open(out_dir / "failures.jsonl", "x") as ff:
        def sink_factory(kind):
            def sink(entry, fails):
                fo.write(json.dumps(entry, allow_nan=False) + "\n")
                for f in fails:
                    ff.write(json.dumps(f, allow_nan=False) + "\n")
                accumulate(tot, entry, fails)
            return sink
        # time pass first: recording clocks for S4
        tr = {}

        def time_sink(entry, fails):
            sink_factory("time")(entry, fails)
        counts_t, cols_t, units_t, ids_t, rep_t = read_table(root / "time.parquet", "time", subject, lineage, {}, time_sink)
        # recording clock ranges from the lineage (equal to time_s first/last, which S1 checks per recording)
        for (tbl, oid, side), d in lineage.items():
            if tbl == "time":
                tr[d["source_recording_id"]] = (d["source_start_time_s"], d["source_end_time_s"])
        counts_p, cols_p, units_p, ids_p, rep_p = read_table(root / "phase.parquet", "phase", subject, lineage, tr, sink_factory("phase"))
    seen_ids = set(ids_t) | set(ids_p)
    lin_ids = set(lineage)
    got = set(("time", i[0], i[1]) for i in ids_t) | set(("phase", i[0], i[1]) for i in ids_p)
    rs = fid["e01_run_summary"]
    problems = []
    if got != lin_ids:
        problems.append(f"S3 observations in the tables and in the lineage differ: {len(got ^ lin_ids)}")
    if rep_t or rep_p:
        problems.append(f"S3 identities repeated in separate runs: {(rep_t + rep_p)[:3]}")
    if counts_t["rows"] != rs["time_rows"] or counts_p["rows"] != rs["phase_rows"]:
        problems.append("S1 row counts differ from the E01 run summary")
    for k, v in rs["observations"].items():
        if tot["by_kind"].get(k) != v:
            problems.append(f"S3 observation count of {k}: {tot['by_kind'].get(k)} != E01 {v}")
    # transfer pairing
    pairs = {}
    for (tbl, oid, side) in lineage:
        if tbl == "phase" and lineage[(tbl, oid, side)]["observation_type"] == "transfer":
            pairs.setdefault(oid, set()).add(side)
    unpaired = sorted(o for o, s in pairs.items() if s != {"left", "right"})
    if unpaired:
        problems.append(f"S3 transfers without both legs: {unpaired[:3]}")
    assessment = {
        "task_id": TASK_ID, "subject": subject, "scientific_approval": False,
        "note": "automated assessment, coarse limits (D-UM21-Q01-1 = B applied to GT23); independent review follows",
        "profile": PROFILE,
        "inputs": {"export_root": root_for(subject), "source_fidelity": fid["file_hashes"],
                   "e01_readback": fid["e01_readback"], "unit_evidence": fid["unit_evidence"],
                   "units_time_table": units_t, "units_phase_table": units_p},
        "table_problems": problems,
        "counts": {"time": counts_t, "phase": counts_p, "observations": tot["observations"], "by_kind": tot["by_kind"]},
        "overall_counts": tot["overall"],
        "failed_observations_by_limit": tot["fail_obs_by_limit"],
        "failed_observations_by_task_and_limit": tot["fail_obs_by_task_limit"],
        "failed_samples_by_limit": tot["fail_samples_by_limit"],
        "failed_samples_by_limit_and_channel": tot["fail_samples_by_limit_channel"],
        "structural_failures_by_problem": tot["structural_fail_by_problem"],
        "worst_examples": sorted(tot["worst"], key=lambda f: -abs(f["value"]))[:10],
        "failing_observations": tot["failing"][:500],
        "failing_observations_total": len(tot["failing"]),
        "channel_states": tot["channel_states"],
        "held_columns_not_checked_no_column": tot["held_by_column"],
        "cycles_by_reference_side": tot["cycles_by_side"],
        "side_check_s5_by_task": tot["s5"],
        "flight_by_task": {k: {"cycles_with_both_forces": v["cycles_with_both_forces"], "flight_cycles": v["flight_cycles"],
                               "both_unloaded_shares": v["shares"]} for k, v in tot["flight"].items()},
        "foot_frame_cop_by_task": tot["cop_by_task"],
        "limitations": tot["limitations"],
        "sidecar_files": {n: {"sha256": sha256_file(out_dir / n), "bytes": (out_dir / n).stat().st_size}
                          for n in ("observations.jsonl", "failures.jsonl")},
        "sidecar_reading": "observations.jsonl: one entry per assessed observation (structural, plausibility and "
                           "limitations; overall = failed | no_failure_found, never 'passed'). failures.jsonl: one row "
                           "per failed sample (observation_id, reference_side, channel, limit, sample_index, clock, value, "
                           "reason; at most 2000 listed per observation, channel and limit, the rest counted).",
        "resources": {"peak_rss_mib": round(_peak_rss_mib(), 1), "wall_seconds": round(time.time() - started, 1)},
    }
    with open(out_dir / "assessment.json", "x") as f:
        json.dump(assessment, f, indent=1, allow_nan=False)
    return assessment


# ---------------------------------------------------------------- summary (reads the participant assessments)
def summarize(roots, out_root, subjects=SUBJECTS):
    ass = {}
    for s in subjects:
        p = ROOT / roots.format(s) / s / "assessment.json"
        ass[s] = json.loads(p.read_text())
        if ass[s]["table_problems"]:
            raise InputError(f"{s}: table problems {ass[s]['table_problems'][:2]}")
    tot = {"observations": 0, "overall": {}, "by_kind": {}, "fail_obs_by_limit": {}, "fail_samples_by_limit": {}}
    by_part = {}
    for s, a in ass.items():
        tot["observations"] += a["counts"]["observations"]
        for k, v in a["overall_counts"].items():
            tot["overall"][k] = tot["overall"].get(k, 0) + v
        for k, v in a["counts"]["by_kind"].items():
            tot["by_kind"][k] = tot["by_kind"].get(k, 0) + v
        for k, v in a["failed_observations_by_limit"].items():
            tot["fail_obs_by_limit"][k] = tot["fail_obs_by_limit"].get(k, 0) + v
        for k, v in a["failed_samples_by_limit"].items():
            tot["fail_samples_by_limit"][k] = tot["fail_samples_by_limit"].get(k, 0) + v
        by_part[s] = {"overall": a["overall_counts"], "failed_observations_by_limit": a["failed_observations_by_limit"],
                      "failed_samples_by_limit": a["failed_samples_by_limit"],
                      "structural_failures_by_problem": a["structural_failures_by_problem"],
                      "cycles_by_reference_side": a["cycles_by_reference_side"], "peak_rss_mib": a["resources"]["peak_rss_mib"]}
    return ass, tot, by_part


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="step", required=True)
    pr = sub.add_parser("run")
    pr.add_argument("--output-root", required=True)
    pr.add_argument("--stage", choices=("pilot", "full"), required=True)
    pr.add_argument("--subjects", required=True)
    args = p.parse_args(argv)
    return run(args)


def run(args):
    if os.nice(0) < 19:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (niceness 19 expected)")
    soft, _ = resource.getrlimit(resource.RLIMIT_AS)
    if soft == resource.RLIM_INFINITY or soft > ADDRESS_SPACE_MIB * 1024 ** 2:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (address-space limit expected)")
    subjects = tuple(args.subjects.split(","))
    if args.stage == "pilot" and subjects != PILOT_SUBJECTS:
        raise SystemExit("refused: the pilot is exactly " + ",".join(PILOT_SUBJECTS))
    if args.stage == "full" and (len(subjects) != 1 or subjects[0] not in SUBJECTS):
        raise SystemExit("refused: a full batch is exactly one participant")
    out = (ROOT / args.output_root).resolve()
    out.mkdir(parents=True, exist_ok=False)
    rc = 0
    for s in subjects:
        if _mem_available() < MIN_AVAILABLE_BYTES:
            raise MemoryError("less than 2 GiB available; stopped at a participant boundary")
        a = assess_participant(s, out / s)
        print(json.dumps({"subject": s, "observations": a["counts"]["observations"], "overall": a["overall_counts"],
                          "failed_observations_by_limit": a["failed_observations_by_limit"],
                          "table_problems": a["table_problems"], "peak_rss_mib": a["resources"]["peak_rss_mib"]}), flush=True)
        if a["table_problems"]:
            rc = 1
        if _peak_rss_mib() > RSS_CAP_MIB:
            raise MemoryError(f"peak RSS {_peak_rss_mib():.0f} MiB above {RSS_CAP_MIB}; stopped")
    return rc


if __name__ == "__main__":
    sys.exit(main())
