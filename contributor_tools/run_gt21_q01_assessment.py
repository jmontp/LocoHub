#!/usr/bin/env python3
"""GT21-Q01: assess the GT21-RB07 exports (phase and time tables) with the shared coarse limits.

Same approach and numbers as UMich 2021 (UM21-Q01 v3) and GT2023 (GT23-Q01 v2): structure plus coarse physical limits, blatant
errors only, nothing tuned to a pass rate (D-UM21-Q01-1 = B, applied here as the least-change default; logged in the handoff).
The streaming observation class and the limit tables come unchanged from run_gt23_q01_assessment (bound by hash).

Checks (state per observation: passed | failed | missing | unchecked; never a pass when nothing was assessed)
  L1  hip, knee, ankle angle beyond [-50, 150], [-30, 165], [-80, 50] degrees (phase and time tables).
  L2  change of more than 30 degrees between adjacent 200 Hz samples, evaluated on the TIME table only. A jump is mapped to
      every phase observation of the same recording whose source span contains both samples (as in GT23 v2).
  L4  non-finite samples are counted and reported as missing (state "missing" when any column has a missing sample).
  L5  foot-frame pressure point beyond 0.5 m anterior or 0.3 m vertical / lateral of the foot origin.
  S1  150 samples on the inclusive 0-100 percent grid (phase) or a strictly increasing 200 Hz clock (time), rows = lineage.
  S2  observation id parses; subject, recording and side agree with the columns.   S3  constant metadata, unique identity,
  lineage file, held_signals equal to the all-missing columns.   S4  span inside its continuous recording.   S5  side check on
  cycles: ipsilateral vertical force (body-weight columns x declared body weight) in 0-40 percent above that in 60-100 percent.
  P1  plane glitch beyond 60 degrees: UNCHECKED. It needs per-frame leg-plane geometry that is not in the export; the export
      holds only the bad-fit frames as missing values, which are counted instead (held frames).
  PD  plate dropout: vertical force exactly 0 together with |ankle moment| > 0.3 N*m/kg. A check that is REPORTED and flagged;
      it does not change status (proposed in the ankle-expressivity note, not applied).
status = failed iff L1, L2, L5 or S1-S5 fail. L3 (cycle duration), L4, P1, PD are reported only. Nothing is removed from the
export: failed observations stay in the full variant, filtering belongs to the release step.

Flags (limitations, never removals): early source heel strike / short left stance (22 listed strides, 2 without a toe-off),
left treadmill stance from the belt force, angle samples beyond pi (possible wraps), held frames, plate dropout samples, and the
task_info limits (AB27 right thigh, AB28 pelvis). Specific cases listed with evidence: AB24 ramp_1 recordings and the AB07
levelground cw slow recording named in the ankle-expressivity note.

Units come from the column suffix (an unknown suffix refuses the run). scientific_approval is false.
Run only through contributor_tools.guarded_launcher.
"""
from __future__ import annotations

import os
for _key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_key, "1")
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")
import argparse
import gc
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
from contributor_tools import run_gt23_q01_assessment as q  # noqa: E402  (limit tables, Observation, helpers; bound by hash)

TASK_ID = "GT21-Q01"
RUNNER = "contributor_tools/run_gt21_q01_assessment.py"
BASE = q.BASE
SUBJECTS = ("AB06", "AB07", "AB08", "AB09", "AB10", "AB11", "AB12", "AB13", "AB14", "AB15", "AB16", "AB17", "AB18", "AB19",
            "AB20", "AB21", "AB23", "AB24", "AB25", "AB27", "AB28", "AB30")
PILOT_SUBJECT = "AB24"       # holds the ramp_1 angle wraps; chosen before any result existed
SHORT_STANCE_AUDIT = "docs/quality/audits/gt21-rb07-short-left-stances.json"
RB07_VERIFY = "docs/maintainers/handoffs/GT21-RB07-verify.json"
CONTRACT = "contributor_tools/DATA_CONTRACT.md"
READBACKS = {"AB06": 1, "AB07": 1, "AB08": 1, **{s: 2 for s in ("AB09", "AB10", "AB11", "AB12", "AB13", "AB14", "AB15")},
             **{s: 3 for s in ("AB16", "AB17", "AB18", "AB19", "AB20", "AB21", "AB23")}, "AB24": 4, "AB25": 4,
             "AB27": 5, "AB28": 5, "AB30": 5}
RSS_CAP_MIB = 400.0
ADDRESS_SPACE_MIB = 768
MIN_AVAILABLE_BYTES = 2 * 1024 ** 3
READ_BATCH_ROWS = 2048
TIME_DT = 1.0 / q.TIME_RATE_HZ
DROPOUT_MOMENT_NM_KG = 0.3
DROPOUT_LIST_CAP = 20
MAP_LIST_CAP = 50
CASE_LIST_CAP = 300
PI_DEG = 180.0
# listed cases (task text): recording-id prefixes with evidence
CASES = (
    {"id": "AB24_ramp_1", "subject": "AB24", "recording_prefix": "AB24/ramp/ramp_1_",
     "note": "ankle-expressivity note: almost all whole segments of the AB24 ramp_1 trials have angles of 5.8 to 7.8 rad (likely wraps)"},
    {"id": "AB07_levelground_cw_slow_01_03", "subject": "AB07", "recording_prefix": "AB07/levelground/levelground_cw_slow_01_03",
     "note": "ankle-expressivity note: AB07 levelground_cw_slow_01_03 walk-stand segment 01 has a segment angle of about 2.2 rad"},
)

ID_PHASE_RE = re.compile(r"^(AB\d{2})/(.+)/(left|right)/(\d{4})$")
ID_TIME_RE = re.compile(r"^(AB\d{2})/(.+)/continuous$")
ANGLE_PREFIXES = ("pelvis_sagittal_angle", "thigh_sagittal_angle_", "shank_sagittal_angle_", "foot_sagittal_angle_",
                  "hip_flexion_angle_", "knee_flexion_angle_", "ankle_dorsiflexion_angle_")
CHECKS = ("L1", "L2", "L4", "L5", "S1", "S2", "S3", "S4", "S5", "P1", "PD")
STATUS_CHECKS = ("L1", "L2", "L5", "S1", "S2", "S3", "S4", "S5")
OBS_TYPES = ("individual_cycle", "continuous_recording")

PROFILE = {
    "profile_id": "gt21_q01_coarse_limits_v1",
    "decision": "D-UM21-Q01-1 = B (structure plus coarse physical limits, blatant errors only), applied to GT21 as the "
                "least-change default; logged in the handoff",
    "review_status": "draft_limits_unreviewed_scientific_approval_false",
    "population": "able-bodied adults (Georgia Tech 2021, 22 participants: level ground, ramps, stairs, treadmill)",
    "applicability": "every exported observation type (individual_cycle in the phase table, continuous_recording in the time "
                     "table); the limits are physical limits of the body or foot, not task profiles",
    "no_tuning": "L1, L2, L5 are the numbers of UM21-Q01 v3 and GT23-Q01 v2 (asserted equal by the test file); nothing changed "
                 "to reach a pass rate",
    "limits": {
        "L1": {"bounds_deg": {k.rstrip("_"): v for k, v in q.L1_BOUNDS_DEG.items()}},
        "L2": {"threshold_deg": q.L2_JUMP_DEG, "evaluated_on": "time table (5 ms samples); mapped to phase observations"},
        "L5": {"bounds_m": {k.rstrip("_"): v for k, v in q.L5_BOUNDS_M.items()}},
        "P1": {"threshold_deg": 60.0, "state": "unchecked: per-frame leg-plane geometry is not part of the export"},
        "PD": {"vertical_force": 0.0, "abs_ankle_moment_Nm_kg": DROPOUT_MOMENT_NM_KG,
               "reported_only": "flagged and counted; does not change status"},
    },
    "status_rule": "failed iff " + ", ".join(STATUS_CHECKS) + " fail; L3, L4, P1, PD are reported only",
    "unchecked": "velocities, moments, powers, ground reaction forces and the segment-frame pressure point have no limit; "
                 "ankle angle passes are coarse limits only (zero offset is the D-REF-1 segment-angle difference, unreviewed)",
}


class RunError(ValueError):
    pass


def jdump(obj):
    return json.dumps(obj, allow_nan=False, sort_keys=True)


# ---------------------------------------------------------------- limits
def is_angle(col):
    return col.endswith("_rad") and col.startswith(ANGLE_PREFIXES)


def column_limits(col, drop_l2):
    return [l for l in q.column_limits(col) if not (drop_l2 and l[0] == "L2")]


def phase_channel(time_channel, reference_side):
    """Time column (left/right) -> phase column (ipsi/contra) for the observation's reference leg."""
    for word in ("left", "right"):
        if f"_{word}_" in time_channel:
            role = "ipsi" if reference_side == word else "contra"
            return time_channel.replace(f"_{word}_", f"_{role}_")
    return time_channel


# ---------------------------------------------------------------- streaming observation
class Obs(q.Observation):
    """q.Observation plus per-observation extras: angle extremes, held frames, plate dropout, forces, L2 times."""

    def __init__(self, key, kind, columns, limits):
        super().__init__(key, kind, columns, limits)
        self.angle_cols = [c for c in columns if is_angle(c)]
        self.sides = ("left", "right") if kind == "time" else ("ipsi", "contra")
        self.l2_times = {}                         # column -> times (phase axis not used) of the second sample of each jump
        self.ext = {c: [np.inf, -np.inf, 0] for c in self.angle_cols}   # min deg, max deg, samples beyond pi (180 deg)
        self.angle_rows_missing = 0                # rows where at least one angle column is missing
        self.drop = {s: [0, []] for s in self.sides}
        self.drop_finite = {s: 0 for s in self.sides}
        self.bw = {"ipsi": [], "contra": []}

    def _emit(self, st, col, limit, local_idx, values, reasons, axis_slice, offset):
        if limit == "L2":
            self.l2_times.setdefault(col, []).extend(float(axis_slice[i]) for i in local_idx)
        super()._emit(st, col, limit, local_idx, values, reasons, axis_slice, offset)

    def feed(self, data, strings, a, e):
        off = self.rows
        super().feed(data, strings, a, e)
        if self.angle_cols:
            fin_all = np.ones(e - a, dtype=bool)
            for c in self.angle_cols:
                x = data[c][a:e]
                fin = np.isfinite(x)
                fin_all &= fin
                if fin.any():
                    d = np.degrees(x[fin])
                    ex = self.ext[c]
                    ex[0] = min(ex[0], float(d.min()))
                    ex[1] = max(ex[1], float(d.max()))
                    ex[2] += int(np.sum(np.abs(d) > PI_DEG))
            self.angle_rows_missing += int(np.sum(~fin_all))
        for s in self.sides:
            g = data.get(f"grf_vertical_{s}_BW")
            m = data.get(f"ankle_dorsiflexion_moment_{s}_Nm_kg")
            if g is None or m is None:
                continue
            g, m = g[a:e], m[a:e]
            ok = np.isfinite(g[:]) & np.isfinite(m)
            self.drop_finite[s] += int(ok.sum())
            hit = np.flatnonzero(ok & (g == 0.0) & (np.abs(m) > DROPOUT_MOMENT_NM_KG))
            if len(hit):
                self.drop[s][0] += len(hit)
                room = DROPOUT_LIST_CAP - len(self.drop[s][1])
                self.drop[s][1].extend(int(off + h) for h in hit[:max(room, 0)])
        if self.kind == "phase":
            self.bw["ipsi"].append(data["grf_vertical_ipsi_BW"][a:e].copy())
            self.bw["contra"].append(data["grf_vertical_contra_BW"][a:e].copy())


def side_check_state(ipsi_n):
    """S5 state: passed | failed | missing (a non-finite force sample) | unchecked (peak below the 20 N loading threshold)."""
    x = np.asarray(ipsi_n, dtype=float)
    if len(x) != q.N_SAMPLES:
        return "unchecked", None, None
    if not np.isfinite(x).all():
        return "missing", None, None
    if float(np.max(x)) < q.LOAD_N:
        return "unchecked", None, None
    early, late = float(np.mean(x[q.S5_EARLY])), float(np.mean(x[q.S5_LATE]))
    return ("passed" if early > late else "failed"), early, late


def load_short_stance_audit(path):
    """step_id -> record, for the 22 listed strides (20 short stances, 2 without a toe-off)."""
    d = json.loads(Path(path).read_text())
    out = {}
    for subject, rows in d.items():
        if isinstance(rows, list):
            for r in rows:
                out[r["step_id"]] = {"subject": subject, "unavailable": bool(r["stance_unavailable"]),
                                     "stance_samples": r["stance_samples"], "force_at_heel_strike_N": r["force_at_heel_strike_N"]}
    return out


def parse_json(text, default):
    try:
        v = json.loads(text) if text else default
        return v
    except ValueError:
        return None


def state_of(limit, obs, cols, extra_failed=0):
    """State of a limit check over its columns: failed | missing (no finite sample in any) | passed."""
    if extra_failed or any(obs.cols[c].n_failed.get(limit) for c in cols):
        return "failed"
    if not cols:
        return "unchecked"
    if not any(obs.cols[c].n_finite for c in cols):
        return "missing"
    return "passed"


def finish_observation(obs, lineage, subject, time_ranges, audit):
    """Entry (assessment.jsonl line) and failure rows of one finished observation."""
    oid, side = obs.key
    kind = obs.kind
    table = "time" if kind == "time" else "phase"
    m = obs.meta
    problems = []
    id_re = ID_TIME_RE if kind == "time" else ID_PHASE_RE
    pm = id_re.match(oid or "")
    otype = m.get("observation_type")
    if pm is None:
        problems.append("S2 id does not parse")
    else:
        if not (pm.group(1) == m.get("subject") == subject):
            problems.append(f"S2 subject differs: id {pm.group(1)!r}, column {m.get('subject')!r}, participant {subject!r}")
        if m.get("source_recording_id") != f"{pm.group(1)}/{pm.group(2)}":
            problems.append("S2 source_recording_id differs from the id")
        if kind == "time":
            if otype != "continuous_recording" or side != "none":
                problems.append("S2 time observation must be continuous_recording with reference_side none")
        else:
            if otype != "individual_cycle":
                problems.append(f"S2 observation_type {otype!r} not allowed in the phase table")
            if side not in ("left", "right") or pm.group(3) != side:
                problems.append(f"S2 reference_side {side!r} differs from the id side {pm.group(3)!r}")
    if obs.meta_problems:
        problems.append(f"S3 values change inside the observation: {sorted(obs.meta_problems)}")
    lin = lineage.get((table, oid, side))
    if lin is None:
        problems.append("S3 observation not in the lineage file")
    else:
        if lin["rows"] != obs.rows:
            problems.append(f"S1 {obs.rows} rows, lineage says {lin['rows']}")
        for c, lk in (("source_start_time_s", "start_s"), ("source_end_time_s", "end_s")):
            if obs.clock.get(c) is None or abs(obs.clock[c] - lin[lk]) > 1e-9:
                problems.append(f"S3 {c} {obs.clock.get(c)} differs from lineage {lin[lk]}")
        for c in ("task", "task_id", "observation_type", "source_recording_id"):
            if lin.get(c) is not None and m.get(c) != lin[c]:
                problems.append(f"S3 {c} {m.get(c)!r} differs from lineage {lin[c]!r}")
    if kind == "phase":
        if obs.rows != q.N_SAMPLES:
            problems.append(f"S1 {obs.rows} rows, expected {q.N_SAMPLES}")
        else:
            ax = np.concatenate(obs.axis)
            if not np.allclose(ax, np.linspace(0.0, 100.0, q.N_SAMPLES), rtol=0, atol=1e-9):
                problems.append("S1 phase is not the 150-sample grid from 0 to 100 percent inclusive")
    else:
        if obs.dt_nonincreasing:
            problems.append(f"S1 time_s not strictly increasing at {obs.dt_nonincreasing} samples")
        if obs.n_dt_bad:
            problems.append(f"S1 {obs.n_dt_bad} sample intervals differ from {1000 * TIME_DT:g} ms (gaps or a different clock)")
        if obs.t_first is not None and abs(obs.clock.get("source_start_time_s", np.nan) - obs.t_first) > 1e-9:
            problems.append("S1 first time_s differs from source_start_time_s")
        if obs.t_last is not None and abs(obs.clock.get("source_end_time_s", np.nan) - obs.t_last) > 1e-9:
            problems.append("S1 last time_s differs from source_end_time_s")
    held = parse_json(m.get("held_signals"), None)
    if not isinstance(held, dict):
        problems.append("S3 held_signals is not a JSON object")
        held = {}
    ti = parse_json(m.get("task_info"), {})
    if not isinstance(ti, dict):
        problems.append("S3 task_info is not JSON")
        ti = {}
    sm = parse_json(m.get("subject_metadata"), {})
    sm = sm if isinstance(sm, dict) else {}
    all_missing = sorted(c for c, s in obs.cols.items() if s.n_finite == 0)
    if sorted(held) != all_missing:
        problems.append("S3 held_signals differ from the all-missing columns: "
                        f"held-only {sorted(set(held) - set(all_missing))[:5]}, missing-only {sorted(set(all_missing) - set(held))[:5]}")
    if kind == "phase" and lin is not None:
        rng = time_ranges.get(m.get("source_recording_id"))
        a, b = obs.clock.get("source_start_time_s"), obs.clock.get("source_end_time_s")
        if rng is None:
            problems.append("S4 no continuous recording for this span")
        elif not (rng[0] - 1e-9 <= a < b <= rng[1] + 1e-9):
            problems.append(f"S4 span {a}..{b} s outside its recording {rng[0]}..{rng[1]} s")
    # S5 side check and flight (cycles)
    s5, early, late, flight = "unchecked", None, None, None
    s5_reason = "time table: not applicable" if kind == "time" else None
    bw_n = sm.get("body_weight_N")
    if kind == "phase" and obs.rows == q.N_SAMPLES:
        if not isinstance(bw_n, (int, float)) or not bw_n > 0:
            s5_reason = "no declared body weight"
        else:
            ip = np.concatenate(obs.bw["ipsi"]) * bw_n
            co = np.concatenate(obs.bw["contra"]) * bw_n
            s5, early, late = side_check_state(ip)
            s5_reason = {"unchecked": "ipsilateral peak below 20 N or no cycle", "missing": "ipsilateral force has missing samples"}.get(s5)
            if s5 == "failed":
                problems.append(f"S5 side check: ipsilateral mean force {early:.0f} N in 0-40 percent is not above {late:.0f} N in 60-100 percent")
            if np.isfinite(ip).all() and np.isfinite(co).all():
                fr, longest = q.flight_stats(ip, co)
                flight = bool(longest >= q.FLIGHT_MIN_SAMPLES)
    cyc_s = l3 = None
    if kind == "phase":
        cyc_s = obs.clock["source_end_time_s"] - obs.clock["source_start_time_s"]
        l3 = bool(not (q.L3_RANGE_S[0] <= cyc_s <= q.L3_RANGE_S[1]))
    # column states in contract words
    fails, ch_states, partial, failed_samples = [], {}, {}, {}
    for c in obs.columns:
        s = obs.cols[c]
        fails.extend(s.fails)
        lims = obs.limits.get(c) or []
        if s.n_finite == 0:
            st = "missing"
        elif s.n_failed:
            st = "failed"
        elif lims:
            st = "passed"
        else:
            st = "unchecked"
        ch_states.setdefault(st, []).append(c)
        if 0 < s.n_finite < s.n_rows:
            partial[c] = {"missing_samples": s.n_rows - s.n_finite, "ranges": s.missing}
        if s.n_failed:
            failed_samples[c] = dict(s.n_failed)
    cols_of = {lim: [c for c in obs.columns if any(l[0] == lim for l in (obs.limits.get(c) or []))] for lim in ("L1", "L2", "L5")}
    checks = {}
    checks["L1"] = state_of("L1", obs, cols_of["L1"])
    checks["L2"] = state_of("L2", obs, cols_of["L2"]) if kind == "time" else "unchecked"   # phase: set by the L2 mapping
    checks["L5"] = state_of("L5", obs, cols_of["L5"])
    n_missing = sum(s.n_rows - s.n_finite for s in obs.cols.values())
    checks["L4"] = "passed" if n_missing == 0 else "missing"
    for tag in ("S1", "S2", "S3", "S4"):
        checks[tag] = "failed" if any(p.startswith(tag + " ") for p in problems) else "passed"
    if kind == "time":
        checks["S4"] = "unchecked"   # a continuous recording is its own span
    checks["S5"] = s5
    checks["P1"] = "unchecked"
    pd_total = sum(v[0] for v in obs.drop.values())
    pd_finite = sum(obs.drop_finite.values())
    checks["PD"] = "failed" if pd_total else ("passed" if pd_finite else "unchecked")
    # flags (limitations)
    flags = []
    for f in (ti.get("flags") or []):
        if f in ("incomplete_stance_force", "authors_rule_extended_to_left_leg"):
            flags.append(f)
    for text in ti.get("limits") or []:
        t = str(text)
        if t.startswith("AB28 pelvis"):
            flags.append("ab28_pelvis_angle_offset")
        elif t.startswith("AB27 right thigh"):
            flags.append("ab27_right_thigh_held_frames")
    beyond_pi = sum(v[2] for v in obs.ext.values())
    if beyond_pi:
        flags.append("angle_samples_beyond_pi")
    if obs.angle_rows_missing:
        flags.append("held_frames_in_angles")
    if pd_total:
        flags.append("plate_dropout_samples")
    audit_hit = audit.get(oid) if kind == "phase" else None
    unavailable_ti = (kind == "phase" and side == "left" and ti.get("treadmill") is True and ti.get("stance_samples") is None)
    if kind == "phase" and side == "left" and ti.get("treadmill") is True:
        flags.append("left_treadmill_stance_from_belt_force")
    if unavailable_ti or (audit_hit and audit_hit["unavailable"]):
        flags.append("left_stance_unavailable_no_toe_off")
    elif audit_hit:
        flags.append("early_source_heel_strike_short_left_stance")
    flags = sorted(set(flags))
    failed_limits = sorted({l for s in obs.cols.values() for l in s.n_failed})
    status_fail = bool(problems) or any(checks[k] == "failed" for k in ("L1", "L2", "L5"))
    entry = {
        "observation_id": oid, "reference_side": side, "table": table, "observation_type": otype, "subject": subject,
        "source_recording_id": m.get("source_recording_id"), "task": m.get("task"), "task_id": m.get("task_id"),
        "rows": obs.rows, "status": "failed" if status_fail else "no_failure_found",
        "failed_limits": failed_limits, "failed_channels": sorted(failed_samples), "failed_samples": failed_samples,
        "limitations": flags, "flight": flight,
        "attributes": {
            "checks": checks, "problems": problems, "cycle_duration_s": cyc_s, "L3_duration_outside_range_reported_only": l3,
            "S5_early_mean_N": early, "S5_late_mean_N": late, "S5_reason": s5_reason,
            "angle_range_deg": {c: [None if not np.isfinite(v[0]) else round(v[0], 3), None if not np.isfinite(v[1]) else round(v[1], 3)]
                                for c, v in obs.ext.items()},
            "angle_samples_beyond_pi": beyond_pi, "angle_rows_missing": obs.angle_rows_missing,
            "missing_samples_total": n_missing, "partially_missing_columns": partial,
            "geometry_held_fraction_ipsi": ti.get("geometry_held_fraction_ipsi"),
            "geometry_held_fraction_contra": ti.get("geometry_held_fraction_contra"),
            "plate_dropout": {s: {"samples": v[0], "first_sample_indices": v[1], "finite_pairs": obs.drop_finite[s]}
                              for s, v in obs.drop.items() if obs.drop_finite[s] or v[0]},
            "task_info_limits": ti.get("limits") or [], "task_info_flags": ti.get("flags") or [],
            "short_stance_audit": audit_hit, "stance_samples": ti.get("stance_samples") if kind == "phase" else None,
            "failed_samples_not_listed": {c: dict(s.n_unlisted) for c, s in obs.cols.items() if s.n_unlisted},
        },
        "held_signals": held,
        "channel_states": {k: sorted(v) for k, v in sorted(ch_states.items())},
    }
    return entry, fails


# ---------------------------------------------------------------- reading one table
def read_table(path, kind, subject, lineage, time_ranges, sink, audit):
    import pyarrow.parquet as pq
    seen, counts = set(), {"rows": 0, "observations": 0}
    state = {"cur": None}
    with open(path, "rb") as fh:
        pf = pq.ParquetFile(fh, buffer_size=0)
        names = pf.schema_arrow.names
        axis_col = q.AXIS_COLS[1] if kind == "time" else q.AXIS_COLS[0]
        for need in q.STR_META + q.CLOCK_COLS + (axis_col,):
            if need not in names:
                raise q.InputError(f"{path} lacks column {need}")
        columns = [c for c in names if c not in q.META_COLS]
        units = {c: q.unit_of(c) for c in columns}
        limits = {c: column_limits(c, drop_l2=(kind == "phase")) for c in columns}
        for c, lims in limits.items():
            for limit, _, _, scale in lims:
                if scale == "deg" and units[c] != "rad":
                    raise q.UnitError(f"{c} is in {units[c]!r}; limits are in degrees, convert first")
        if kind == "phase":
            for need in ("grf_vertical_ipsi_BW", "grf_vertical_contra_BW"):
                if need not in columns:
                    raise q.InputError(f"{path} lacks column {need}")
        for batch in pf.iter_batches(batch_size=READ_BATCH_ROWS, use_threads=False):
            n = batch.num_rows
            counts["rows"] += n
            enc = {c: batch.column(c).dictionary_encode() for c in q.STR_META}
            idx = {c: enc[c].indices.to_numpy(zero_copy_only=False) for c in q.STR_META}
            data = {c: batch.column(c).to_numpy(zero_copy_only=False).astype(float, copy=False)
                    for c in columns + list(q.CLOCK_COLS) + [axis_col]}
            change = np.flatnonzero((np.diff(idx["observation_id"]) != 0) | (np.diff(idx["reference_side"]) != 0)) + 1
            starts = [0] + [int(x) for x in change]
            ends = [int(x) for x in change] + [n]
            for a, e in zip(starts, ends):
                key = (enc["observation_id"].dictionary[int(idx["observation_id"][a])].as_py(),
                       enc["reference_side"].dictionary[int(idx["reference_side"][a])].as_py())
                strings = {}
                for c in q.CONST_STR:
                    if not np.all(idx[c][a:e] == idx[c][a]):
                        strings[c] = None
                    else:
                        strings[c] = enc[c].dictionary[int(idx[c][a])].as_py()
                cur = state["cur"]
                if cur is None or cur.key != key:
                    if cur is not None:
                        sink(*finish_observation(cur, lineage, subject, time_ranges, audit), cur)
                    if key in seen:
                        state.setdefault("repeated", []).append(key)
                    seen.add(key)
                    counts["observations"] += 1
                    cur = state["cur"] = Obs(key, kind, columns, limits)
                for c, v in list(strings.items()):
                    if v is None:
                        cur.meta_problems.add(c)
                        del strings[c]
                cur.feed(data, strings, a, e)
            del data, enc, idx
        if state["cur"] is not None:
            sink(*finish_observation(state["cur"], lineage, subject, time_ranges, audit), state["cur"])
    return counts, columns, units, sorted(seen), state.get("repeated", [])


# ---------------------------------------------------------------- one participant
def load_lineage(root):
    out = {}
    with open(Path(root) / "observations.jsonl") as f:
        for line in f:
            d = json.loads(line)
            k = (d["table"], d["observation_id"], d["reference_side"])
            if k in out:
                raise q.InputError(f"duplicate lineage identity {k}")
            out[k] = d
    return out


def source_fidelity(subject, root, readback_root=None):
    """Identity of the export: the hashes equal the RB07 run summary; the independent RB07 readback passed for the participant."""
    rs = json.loads((Path(root) / "run_summary.json").read_text())
    hashes = {}
    for name in ("phase.parquet", "time.parquet", "observations.jsonl", "exclusions.jsonl", "recordings.jsonl"):
        got = q.sha256_file(Path(root) / name)
        hashes[name] = {"sha256": got, "equals_run_summary": got == rs["sha256"][name]}
        if got != rs["sha256"][name]:
            raise q.InputError(f"{root}/{name} differs from the run summary hash")
    out = {"run_summary": rs, "file_hashes": hashes, "readback": None}
    if readback_root is not None:
        rp = Path(readback_root) / "readback.json"
        rb = json.loads(rp.read_text())
        if rb.get("status") != "passed" or subject not in rb.get("subjects", []) or rb["failures"]["counts"]:
            raise q.InputError(f"the RB07 readback {rp} did not pass for {subject}")
        out["readback"] = {"path": str(rp), "sha256": q.sha256_file(rp), "status": rb["status"], "subjects": rb["subjects"]}
    return out


def new_totals():
    return {"observations": 0, "by_status": {}, "by_kind": {}, "checks": {c: {} for c in CHECKS},
            "limitations": {}, "fail_obs_by_limit": {}, "fail_samples_by_limit_channel": {}, "channel_states": {},
            "structural_by_problem": {}, "missing_by_column": {}, "angle_rows_missing_by_table": {}, "rows_by_table": {},
            "dropout": {"observations": 0, "samples": 0, "by_task": {}}, "beyond_pi": {"observations": 0, "samples": 0},
            "worst": [], "failing": [], "short_stance": [], "recordings_with_angle_failures": []}


def bump(d, *keys):
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = d.get(keys[-1], 0) + 1


def accumulate(tot, e, fails, obs):
    a = e["attributes"]
    tk = f"{e['table']}:{e['task_id']}"
    tot["observations"] += 1
    bump(tot["by_status"], e["status"])
    bump(tot["by_kind"], e["observation_type"])
    for chk, st in a["checks"].items():
        bump(tot["checks"][chk], tk, st)
    for fl in e["limitations"]:
        d = tot["limitations"].setdefault(fl, {"observations": 0, "recordings": set(), "tasks": {}})
        d["observations"] += 1
        d["recordings"].add(e["source_recording_id"])
        bump(d["tasks"], tk)
    for st, cols in e["channel_states"].items():
        for c in cols:
            bump(tot["channel_states"], f"{e['table']}:{c}", st)
    for lim in e["failed_limits"]:
        bump(tot["fail_obs_by_limit"], lim)
    for c, d in e["failed_samples"].items():
        for lim, n in d.items():
            k = f"{e['table']}:{lim}:{c}"
            tot["fail_samples_by_limit_channel"][k] = tot["fail_samples_by_limit_channel"].get(k, 0) + n
    for p in a["problems"]:
        bump(tot["structural_by_problem"], " ".join(p.split(" ")[:4]))
    for c, v in a["partially_missing_columns"].items():
        k = f"{e['table']}:{c}"
        tot["missing_by_column"][k] = tot["missing_by_column"].get(k, 0) + v["missing_samples"]
    t = tot["angle_rows_missing_by_table"]
    t[e["table"]] = t.get(e["table"], 0) + a["angle_rows_missing"]
    tr = tot["rows_by_table"]
    tr[e["table"]] = tr.get(e["table"], 0) + e["rows"]
    pdn = sum(v["samples"] for v in a["plate_dropout"].values())
    if pdn:
        tot["dropout"]["observations"] += 1
        tot["dropout"]["samples"] += pdn
        tot["dropout"]["by_task"][tk] = tot["dropout"]["by_task"].get(tk, 0) + pdn
    if a["angle_samples_beyond_pi"]:
        tot["beyond_pi"]["observations"] += 1
        tot["beyond_pi"]["samples"] += a["angle_samples_beyond_pi"]
    if a["short_stance_audit"] or "left_stance_unavailable_no_toe_off" in e["limitations"]:
        tot["short_stance"].append({"observation_id": e["observation_id"], "status": e["status"],
                                    "flags": [f for f in e["limitations"] if f.startswith(("left_stance", "early_source"))],
                                    "stance_samples": a["stance_samples"], "audit": a["short_stance_audit"]})
    for f in fails:
        tot["worst"].append(f)
    if len(tot["worst"]) > 400:
        tot["worst"] = sorted(tot["worst"], key=lambda f: -abs(f["value"] or 0.0))[:100]
    if e["status"] == "failed":
        tot["failing"].append({"observation_id": e["observation_id"], "reference_side": e["reference_side"], "task_id": e["task_id"],
                               "table": e["table"], "problems": a["problems"],
                               "failed": sorted(f"{l}:{c}" for c, d in e["failed_samples"].items() for l in d)})


def assess_participant(subject, root, out_dir, audit, readback_root=None, base_label=None):
    """Time pass, then phase pass; writes assessment.jsonl, failures.jsonl and assessment.json under out_dir."""
    root = Path(root)
    fid = source_fidelity(subject, root, readback_root)
    lineage = load_lineage(root)
    out_dir.mkdir(parents=True, exist_ok=False)
    tot, started = new_totals(), time.time()
    l2_time = {}           # recording -> {time column -> [second-sample times of jumps]}
    mapped = {"time_l2_jumps": 0, "phase_observations_failed_by_mapping": 0, "phase_observations_failed_samples": 0}
    case_state = {c["id"]: {"id": c["id"], "note": c["note"], "recordings": {}, "phase_observations": 0,
                            "phase_observations_listed": []} for c in CASES if c["subject"] == subject}
    case_hit = lambda rec: next((c for c in CASES if c["subject"] == subject and rec.startswith(c["recording_prefix"])), None)
    with open(out_dir / "assessment.jsonl", "x") as fo, open(out_dir / "failures.jsonl", "x") as ff:
        def write(entry, fails):
            fo.write(jdump(entry) + "\n")
            for f in fails:
                ff.write(jdump(f) + "\n")

        def case_note(entry, obs):
            c = case_hit(entry["source_recording_id"] or "")
            if c is None:
                return
            cs = case_state[c["id"]]
            ar = entry["attributes"]["angle_range_deg"]
            worst = max([max(abs(v[0]), abs(v[1])) for v in ar.values() if v[0] is not None] or [0.0])
            if entry["table"] == "time":
                cs["recordings"][entry["source_recording_id"]] = {
                    "angle_range_deg": ar, "max_abs_angle_deg": worst, "angle_samples_beyond_pi": entry["attributes"]["angle_samples_beyond_pi"],
                    "failed_samples": entry["failed_samples"], "status": entry["status"], "checks": entry["attributes"]["checks"],
                    "rows": entry["rows"]}
            else:
                cs["phase_observations"] += 1
                if entry["failed_limits"] or worst > PI_DEG:
                    if len(cs["phase_observations_listed"]) < CASE_LIST_CAP:
                        cs["phase_observations_listed"].append({"observation_id": entry["observation_id"], "task_id": entry["task_id"],
                                                                "max_abs_angle_deg": worst, "failed_limits": entry["failed_limits"]})

        def time_sink(entry, fails, obs):
            rec = entry["source_recording_id"]
            for col, times in obs.l2_times.items():
                l2_time.setdefault(rec, {}).setdefault(col, []).extend(times)
                mapped["time_l2_jumps"] += len(times)
            if entry["status"] == "failed" and any(l in ("L1", "L2") for l in entry["failed_limits"]):
                if len(tot["recordings_with_angle_failures"]) < 300:
                    tot["recordings_with_angle_failures"].append({
                        "source_recording_id": rec, "failed_samples": entry["failed_samples"],
                        "angle_range_deg": entry["attributes"]["angle_range_deg"],
                        "angle_samples_beyond_pi": entry["attributes"]["angle_samples_beyond_pi"]})
            case_note(entry, obs)
            write(entry, fails)
            accumulate(tot, entry, fails, obs)

        def phase_sink(entry, fails, obs):
            rec = entry["source_recording_id"]
            lin = lineage.get(("phase", entry["observation_id"], entry["reference_side"]))
            start, end = (lin["start_s"], lin["end_s"]) if lin else (None, None)
            per_channel = {}
            if start is not None and rec in l2_time:
                for col, times in l2_time[rec].items():
                    ch = phase_channel(col, entry["reference_side"])
                    for t in times:
                        if start - 1e-9 <= t - TIME_DT and t <= end + 1e-9:
                            per_channel.setdefault(ch, []).append(t)
            has_time = ("time", f"{rec}/continuous", "none") in lineage
            if per_channel:
                for ch, ts in per_channel.items():
                    for t in ts[:MAP_LIST_CAP]:
                        fails.append({"observation_id": entry["observation_id"], "reference_side": entry["reference_side"],
                                      "table": "phase", "channel": ch, "limit": "L2", "sample_index": None,
                                      "mapped_from": {"table": "time", "time_s": t, "previous_time_s": t - TIME_DT},
                                      "value": None, "reason": f"{ch} jumps more than {q.L2_JUMP_DEG:g} degrees between adjacent 200 Hz "
                                                                f"samples at {t:.3f} s (time table, inside this observation's span)"})
                    entry["failed_samples"].setdefault(ch, {})["L2"] = len(ts)
                    if ch in entry["channel_states"].get("passed", []):
                        entry["channel_states"]["passed"].remove(ch)
                        entry["channel_states"].setdefault("failed", []).append(ch)
                    elif ch in entry["channel_states"].get("unchecked", []):
                        entry["channel_states"]["unchecked"].remove(ch)
                        entry["channel_states"].setdefault("failed", []).append(ch)
                    elif ch not in entry["channel_states"].get("failed", []):
                        entry["channel_states"].setdefault("failed", []).append(ch)
                for k in list(entry["channel_states"]):
                    entry["channel_states"][k] = sorted(entry["channel_states"][k])
                    if not entry["channel_states"][k]:
                        del entry["channel_states"][k]
                entry["failed_channels"] = sorted(entry["failed_samples"])
                entry["failed_limits"] = sorted(set(entry["failed_limits"]) | {"L2"})
                entry["attributes"]["checks"]["L2"] = "failed"
                entry["status"] = "failed"
                mapped["phase_observations_failed_by_mapping"] += 1
                mapped["phase_observations_failed_samples"] += sum(len(v) for v in per_channel.values())
            else:
                entry["attributes"]["checks"]["L2"] = "passed" if has_time else "missing"
                if has_time:   # angle columns with no phase-grid limit were tested for jumps on the time table
                    moved = [c for c in entry["channel_states"].get("unchecked", []) if is_angle(c)]
                    if moved:
                        entry["channel_states"]["unchecked"] = [c for c in entry["channel_states"]["unchecked"] if c not in moved]
                        if not entry["channel_states"]["unchecked"]:
                            del entry["channel_states"]["unchecked"]
                        entry["channel_states"]["passed"] = sorted(entry["channel_states"].get("passed", []) + moved)
                        entry["attributes"]["passed_on_time_table_jump_test_only"] = sorted(moved)
            if entry["status"] == "failed" and not entry["attributes"]["problems"] and not any(
                    entry["attributes"]["checks"][k] == "failed" for k in STATUS_CHECKS):
                raise RunError("status failed without a failed check")
            case_note(entry, obs)
            write(entry, fails)
            accumulate(tot, entry, fails, obs)

        counts_t, cols_t, units_t, ids_t, rep_t = read_table(root / "time.parquet", "time", subject, lineage, {}, time_sink, audit)
        tr = {d["source_recording_id"]: (d["start_s"], d["end_s"]) for (tbl, oid, side), d in lineage.items() if tbl == "time"}
        gc.collect()
        counts_p, cols_p, units_p, ids_p, rep_p = read_table(root / "phase.parquet", "phase", subject, lineage, tr, phase_sink, audit)
    got = {("time", i[0], i[1]) for i in ids_t} | {("phase", i[0], i[1]) for i in ids_p}
    rs = fid["run_summary"]
    problems = []
    if got != set(lineage):
        problems.append(f"S3 observations in the tables and in the lineage differ: {len(got ^ set(lineage))}")
    if rep_t or rep_p:
        problems.append(f"S3 identities repeated in separate runs: {(rep_t + rep_p)[:3]}")
    if counts_t["rows"] != rs["time_rows"] or counts_p["rows"] != rs["phase_rows"]:
        problems.append("S1 row counts differ from the run summary")
    if counts_p["observations"] != rs["phase_observations"]:
        problems.append("S3 phase observation count differs from the run summary")
    if counts_t["observations"] != rs["continuous_observations"]:
        problems.append("S3 time observation count differs from the run summary")
    listed_short = {k: v for k, v in audit.items() if v["subject"] == subject}
    found_short = {r["observation_id"] for r in tot["short_stance"]}
    excluded = {}
    with open(root / "exclusions.jsonl") as f:
        for line in f:
            d = json.loads(line)
            if d.get("step_id") in listed_short:
                excluded[d["step_id"]] = d.get("reason")
    unaccounted = sorted(set(listed_short) - found_short - set(excluded))
    for sid in unaccounted:
        problems.append(f"S3 listed short-stance stride {sid} is neither in the phase table nor in the exclusions")
    short_accounting = {"listed_in_audit": len(listed_short), "flagged_in_phase_table": sorted(found_short & set(listed_short)),
                        "excluded_in_export_with_reason": excluded, "unaccounted": unaccounted,
                        "flagged_not_in_audit": sorted(found_short - set(listed_short))}
    for k in tot["limitations"]:
        tot["limitations"][k]["recordings"] = len(tot["limitations"][k]["recordings"])
    assessment = {
        "task_id": TASK_ID, "subject": subject, "scientific_approval": False, "profile": PROFILE,
        "note": "automated assessment, coarse limits; independent readback follows",
        "inputs": {"export_root": base_label or str(root), "file_hashes": fid["file_hashes"], "rb07_readback": fid["readback"],
                   "units_time_table": units_t, "units_phase_table": units_p,
                   "unit_evidence": "units come from the column suffix (observation contract); the export README does not state them"},
        "table_problems": problems,
        "counts": {"time": counts_t, "phase": counts_p, "observations": tot["observations"], "by_kind": tot["by_kind"]},
        "status_counts": tot["by_status"],
        "check_counts_by_table_task": tot["checks"],
        "failed_observations_by_limit": tot["fail_obs_by_limit"],
        "failed_samples_by_limit_and_channel": tot["fail_samples_by_limit_channel"],
        "structural_failures_by_problem": tot["structural_by_problem"],
        "l2_mapping": mapped,
        "worst_examples": sorted(tot["worst"], key=lambda f: -abs(f["value"] or 0.0))[:10],
        "failing_observations_total": len(tot["failing"]),
        "failing_observations": tot["failing"][:300],
        "recordings_with_angle_failures": tot["recordings_with_angle_failures"],
        "cases": case_state,
        "channel_states": tot["channel_states"],
        "held_frames": {"rows_with_a_missing_angle_by_table": tot["angle_rows_missing_by_table"], "rows_by_table": tot["rows_by_table"],
                        "partially_missing_samples_by_column": tot["missing_by_column"]},
        "plate_dropout": tot["dropout"], "angle_samples_beyond_pi": tot["beyond_pi"],
        "short_left_stances": tot["short_stance"], "short_stance_accounting": short_accounting,
        "limitations": tot["limitations"],
        "sidecar_files": {n: {"sha256": q.sha256_file(out_dir / n), "bytes": (out_dir / n).stat().st_size}
                          for n in ("assessment.jsonl", "failures.jsonl")},
        "resources": {"peak_rss_mib": round(q._peak_rss_mib(), 1), "wall_seconds": round(time.time() - started, 1)},
    }
    with open(out_dir / "assessment.json", "x") as f:
        json.dump(assessment, f, indent=1, allow_nan=False, sort_keys=True)
    return assessment


# ---------------------------------------------------------------- run / spec / summary
def export_root(subject):
    return f"{BASE}/gt21_rb07_export_{subject}"


def readback_root(subject):
    return f"{BASE}/gt21_rb07_readback_c{READBACKS[subject]}"


def run(args):
    if os.nice(0) < 19:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (niceness 19 expected)")
    soft, _ = resource.getrlimit(resource.RLIMIT_AS)
    if soft == resource.RLIM_INFINITY or soft > ADDRESS_SPACE_MIB * 1024 ** 2:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (address-space limit expected)")
    subjects = tuple(args.subjects.split(","))
    if args.stage == "pilot" and subjects != (PILOT_SUBJECT,):
        raise SystemExit("refused: the pilot is exactly " + PILOT_SUBJECT)
    if args.stage == "full" and (not 1 <= len(subjects) <= 4 or any(s not in SUBJECTS for s in subjects)):
        raise SystemExit("refused: a full batch is one to four listed participants")
    audit = load_short_stance_audit(ROOT / SHORT_STANCE_AUDIT)
    out = (ROOT / args.output_root).resolve()
    out.mkdir(parents=True, exist_ok=False)
    rc = 0
    for s in subjects:
        if q._mem_available() < MIN_AVAILABLE_BYTES:
            raise MemoryError("less than 2 GiB available; stopped at a participant boundary")
        a = assess_participant(s, ROOT / export_root(s), out / s, audit, ROOT / readback_root(s), export_root(s))
        gc.collect()
        print(json.dumps({"subject": s, "observations": a["counts"]["observations"], "status": a["status_counts"],
                          "failed_observations_by_limit": a["failed_observations_by_limit"], "l2_mapping": a["l2_mapping"],
                          "table_problems": a["table_problems"], "peak_rss_mib": a["resources"]["peak_rss_mib"],
                          "wall_seconds": a["resources"]["wall_seconds"]}), flush=True)
        if a["table_problems"]:
            rc = 1
        if q._peak_rss_mib() > RSS_CAP_MIB:
            raise MemoryError(f"peak RSS {q._peak_rss_mib():.0f} MiB above {RSS_CAP_MIB}; stopped")
    return rc


def build_spec(job, stage, subjects, version=""):
    from contributor_tools.guarded_launcher import validate_spec
    audit_dir = "docs/quality/audits"
    out_root = f"{BASE}/gt21_q01_{job}{version}"
    b = {RUNNER: q.sha256_file(ROOT / RUNNER), q.RUNNER: q.sha256_file(ROOT / q.RUNNER),
         "contributor_tools/guarded_launcher.py": q.sha256_file(ROOT / "contributor_tools/guarded_launcher.py"),
         CONTRACT: q.sha256_file(ROOT / CONTRACT), SHORT_STANCE_AUDIT: q.sha256_file(ROOT / SHORT_STANCE_AUDIT),
         RB07_VERIFY: q.sha256_file(ROOT / RB07_VERIFY)}
    for s in subjects:
        for n in ("run_summary.json", "observations.jsonl"):
            b[f"{export_root(s)}/{n}"] = q.sha256_file(ROOT / export_root(s) / n)
        b[f"{readback_root(s)}/readback.json"] = q.sha256_file(ROOT / readback_root(s) / "readback.json")
    spec = {"job_id": f"gt21-q01-{job}{version}",
            "command": ["python3", RUNNER, "run", "--output-root", out_root, "--stage", stage, "--subjects", ",".join(subjects)],
            "cwd": str(ROOT), "output_root": out_root, "receipt_path": f"{audit_dir}/gt21-q01-{job}{version}-launcher-receipt.json",
            "bindings": b, "timeout_seconds": 3600, "kill_after_seconds": 30, "poll_seconds": 15,
            "startup_memory_mib": {"linux": 3584, "windows": 2816}, "runtime_memory_mib": {"linux": 2048, "windows": 2048},
            "expected_output_names": ["assessment.json"], "address_space_mib": ADDRESS_SPACE_MIB}
    validate_spec(spec)
    return spec, ROOT / audit_dir / f"gt21-q01-{job}{version}-spec.json"


def summarize(roots, out_json):
    """Counts per check x table:task x participant, from the participant assessment.json files (read-only on inputs)."""
    ass = {}
    for r in roots:
        for p in sorted((ROOT / r).glob("AB*/assessment.json")):
            s = p.parent.name
            a = json.loads(p.read_text())
            if a["table_problems"]:
                raise q.InputError(f"{s}: table problems {a['table_problems'][:2]}")
            if s in ass:
                raise q.InputError(f"{s} assessed twice")
            ass[s] = a
    subjects = tuple(sorted(ass))
    if subjects != tuple(sorted(SUBJECTS)):
        raise q.InputError(f"participants {subjects} differ from the 22 expected")
    res = {"task_id": TASK_ID, "scientific_approval": False, "subjects": list(subjects), "profile": PROFILE,
           "observations": 0, "status": {}, "by_kind": {}, "counts_per_check_task_participant": {c: {} for c in CHECKS},
           "totals_per_check": {c: {} for c in CHECKS}, "failed_observations_by_limit": {}, "failed_samples_by_limit_and_channel": {},
           "by_participant": {}, "limitations": {}, "channel_states": {}, "held_frames": {"rows_with_a_missing_angle_by_table": {},
                                                                                         "rows_by_table": {}, "partially_missing_samples_by_column": {}},
           "plate_dropout": {"observations": 0, "samples": 0, "by_participant": {}}, "angle_samples_beyond_pi": {"observations": 0, "samples": 0, "by_participant": {}},
           "short_left_stances": [], "cases": {}, "recordings_with_angle_failures": [], "worst_examples": [], "l2_mapping": {}}
    for s, a in ass.items():
        res["observations"] += a["counts"]["observations"]
        for k, v in a["status_counts"].items():
            res["status"][k] = res["status"].get(k, 0) + v
        for k, v in a["counts"]["by_kind"].items():
            res["by_kind"][k] = res["by_kind"].get(k, 0) + v
        for chk, tasks in a["check_counts_by_table_task"].items():
            for tk, sts in tasks.items():
                res["counts_per_check_task_participant"][chk].setdefault(tk, {})[s] = sts
                for st, n in sts.items():
                    res["totals_per_check"][chk][st] = res["totals_per_check"][chk].get(st, 0) + n
        for k, v in a["failed_observations_by_limit"].items():
            res["failed_observations_by_limit"][k] = res["failed_observations_by_limit"].get(k, 0) + v
        for k, v in a["failed_samples_by_limit_and_channel"].items():
            res["failed_samples_by_limit_and_channel"][k] = res["failed_samples_by_limit_and_channel"].get(k, 0) + v
        res["by_participant"][s] = {"status": a["status_counts"], "failed_observations_by_limit": a["failed_observations_by_limit"],
                                    "structural_failures_by_problem": a["structural_failures_by_problem"],
                                    "l2_mapping": a["l2_mapping"], "peak_rss_mib": a["resources"]["peak_rss_mib"],
                                    "wall_seconds": a["resources"]["wall_seconds"],
                                    "export_hashes": {n: v["sha256"] for n, v in a["inputs"]["file_hashes"].items()},
                                    "assessment_jsonl_sha256": a["sidecar_files"]["assessment.jsonl"]["sha256"]}
        for fl, v in a["limitations"].items():
            d = res["limitations"].setdefault(fl, {"observations": 0, "recordings": 0, "by_participant": {}})
            d["observations"] += v["observations"]
            d["recordings"] += v["recordings"]
            d["by_participant"][s] = v["observations"]
        for ch, st in a["channel_states"].items():
            d = res["channel_states"].setdefault(ch, {})
            for k, n in st.items():
                d[k] = d.get(k, 0) + n
        for part in ("rows_with_a_missing_angle_by_table", "rows_by_table", "partially_missing_samples_by_column"):
            for k, n in a["held_frames"][part].items():
                res["held_frames"][part][k] = res["held_frames"][part].get(k, 0) + n
        res["plate_dropout"]["observations"] += a["plate_dropout"]["observations"]
        res["plate_dropout"]["samples"] += a["plate_dropout"]["samples"]
        res["plate_dropout"]["by_participant"][s] = {"observations": a["plate_dropout"]["observations"],
                                                      "samples": a["plate_dropout"]["samples"], "by_task": a["plate_dropout"]["by_task"]}
        res["angle_samples_beyond_pi"]["observations"] += a["angle_samples_beyond_pi"]["observations"]
        res["angle_samples_beyond_pi"]["samples"] += a["angle_samples_beyond_pi"]["samples"]
        res["angle_samples_beyond_pi"]["by_participant"][s] = a["angle_samples_beyond_pi"]
        res["short_left_stances"] += a["short_left_stances"]
        res["cases"].update(a["cases"])
        res["recordings_with_angle_failures"] += [{**r, "participant": s} for r in a["recordings_with_angle_failures"]]
        res["worst_examples"] += a["worst_examples"]
        res["l2_mapping"][s] = a["l2_mapping"]
    res["worst_examples"] = sorted(res["worst_examples"], key=lambda f: -abs(f["value"] or 0.0))[:10]
    res["recordings_with_angle_failures_total"] = len(res["recordings_with_angle_failures"])
    res["recordings_with_angle_failures"] = sorted(res["recordings_with_angle_failures"],
                                                    key=lambda r: -r["angle_samples_beyond_pi"])[:100]
    audit = load_short_stance_audit(ROOT / SHORT_STANCE_AUDIT)
    acc = {s: a["short_stance_accounting"] for s, a in ass.items()}
    flagged = {i for v in acc.values() for i in v["flagged_in_phase_table"]}
    excl = {i: r for v in acc.values() for i, r in v["excluded_in_export_with_reason"].items()}
    res["short_stance_cross_check"] = {
        "listed_in_audit": len(audit), "flagged_in_phase_table": len(flagged), "excluded_in_export": excl,
        "unaccounted": sorted(set(audit) - flagged - set(excl)),
        "flagged_not_in_audit": sorted(i for v in acc.values() for i in v["flagged_not_in_audit"])}
    out = Path(out_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "x") as f:
        f.write(json.dumps(res, indent=2, ensure_ascii=False, allow_nan=False, sort_keys=True) + "\n")
    print(json.dumps({"observations": res["observations"], "status": res["status"], "checks": res["totals_per_check"]}))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="step", required=True)
    pr = sub.add_parser("run")
    pr.add_argument("--output-root", required=True)
    pr.add_argument("--stage", choices=("pilot", "full"), required=True)
    pr.add_argument("--subjects", required=True)
    ps = sub.add_parser("spec")
    ps.add_argument("--job", required=True, help="pilot or batch_<name>")
    ps.add_argument("--subjects", default=None)
    ps.add_argument("--version", default="")
    pm = sub.add_parser("summary")
    pm.add_argument("--roots", required=True, help="comma-separated batch roots (relative), each holding ABxx/assessment.json")
    pm.add_argument("--out", required=True)
    args = p.parse_args(argv)
    if args.step == "run":
        return run(args)
    if args.step == "summary":
        return summarize(tuple(args.roots.split(",")), args.out)
    if args.job == "pilot":
        spec, path = build_spec("pilot", "pilot", (PILOT_SUBJECT,), args.version)
    else:
        spec, path = build_spec(args.job, "full", tuple(args.subjects.split(",")), args.version)
    with path.open("x") as f:
        json.dump(spec, f, indent=2)
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
