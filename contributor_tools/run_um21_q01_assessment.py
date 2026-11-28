#!/usr/bin/env python3
"""UM21-Q01: assess the T04 v2 treadmill observations with structure checks and coarse physical limits.

Decision D-UM21-Q01-1 = B: structure plus coarse physical limits; blatant errors only. No literature-fitted
ranges, nothing tuned to a pass rate. Two separate layers:

  structural layer   S1 150 contiguous samples, S2 id parses and its side matches reference_side and the
                     observation map, S3 unique ids, L4 non-finite samples reported as missing, L3 stride
                     time (reported, never a filter).
  plausibility layer L1 joint angle beyond a textbook end of range plus 30 deg (hip, knee, ankle),
                     L2 jump of more than 30 deg between adjacent samples (angles and derived segments).

A column with no limit is "unchecked", never pass. A held channel has no column and is
"not_checked_no_column". Only channels T04 published are read. The assessment is read-only on T04 outputs.
scientific_approval is false. Run only through contributor_tools.guarded_launcher.
"""
from __future__ import annotations

import os
for _key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_key, "1")
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")  # must precede pyarrow (768 MiB address-space cap)
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
TASK_ID = "UM21-Q01"
RUNNER = "contributor_tools/run_um21_q01_assessment.py"
VERSION = "v2"  # v2: v1 compared radian columns to degree limits (never fired); v1 roots are INVALID
T04_RECEIPT = "docs/quality/audits/um21-t04-full-{}-launcher-receipt-v2.json"
SUBJECTS = tuple(f"AB{i:02d}" for i in range(1, 11))
C02_REPORT = "converted_datasets/reconversion_v2/um21_c02_pelvis_20261102/pelvis_correspondence_report.json"
C02_REPORT_SHA256 = "66999178c64a493a482677494cb1504b4f2359f2d397307c31d1366c385b9cd1"
PILOT_RECORDINGS = ("AB01/i0", "AB07/i10")  # a clean recording; the recording where the limits must fire (verifier probe)
RSS_CAP_MIB = 300.0
ADDRESS_SPACE_MIB = 768
MIN_AVAILABLE_BYTES = 2 * 1024 ** 3
N_SAMPLES = 150
READ_BATCH_ROWS = 4096
RATE_HZ = 100.0
ID_RE = re.compile(r"^um21:Streaming/(AB\d{2})/Tread/([di]\d+):(right|left):frames:(\d+):(\d+)$")

CHANNELS = ("ankle_angle", "ankle_moment", "ankle_power", "foot_angle", "foot_angle_velocity", "hip_angle",
            "hip_moment", "hip_power", "knee_angle", "knee_moment", "knee_power", "pelvis_tilt",
            "pelvis_tilt_velocity", "shank_angle", "shank_angle_velocity", "thigh_angle",
            "thigh_angle_velocity")

# Units of every published column, as the T04 v2 tables store them. Evidence for each (checked in the job, not
# assumed): sign_offset_detector.py docstring "Angles are radians, moments N*m/kg, power W/kg"; each group's
# derivations.json adapter.unit_conversion = "angles deg -> rad ..."; source_columns "(deg -> rad)"; thigh/shank/foot
# and the velocities are derived from those radian angles (rad, rad/s). The parquet carries no unit metadata.
# The limits stay in DEGREES: radian columns are converted with numpy.degrees before L1 and L2.
COLUMN_UNITS = {c: "rad" for c in ("ankle_angle", "foot_angle", "hip_angle", "knee_angle", "pelvis_tilt",
                                   "shank_angle", "thigh_angle")}
COLUMN_UNITS.update({c: "rad/s" for c in ("foot_angle_velocity", "pelvis_tilt_velocity", "shank_angle_velocity",
                                          "thigh_angle_velocity")})
COLUMN_UNITS.update({c: "N*m/kg" for c in ("ankle_moment", "hip_moment", "knee_moment")})
COLUMN_UNITS.update({c: "W/kg" for c in ("ankle_power", "hip_power", "knee_power")})
UNIT_EVIDENCE_TEXT = "angles deg -> rad"


class UnitError(ValueError):
    """A column's unit is unknown or its evidence is missing: the assessment refuses to run."""


def convert_to_degrees(data):
    """data: channel -> array in published units. Returns (data, units) with every radian angle converted to
    degrees. A column without a known unit raises UnitError; nothing is guessed."""
    out, units = {}, {}
    for ch, x in data.items():
        u = COLUMN_UNITS.get(ch)
        if u is None:
            raise UnitError(f"unknown unit for column {ch!r}; refusing to assess")
        if u == "rad":
            out[ch], units[ch] = np.degrees(np.asarray(x, dtype=float)), "deg"
        else:
            out[ch], units[ch] = x, u
    return out, units


def check_unit_evidence(derivation):
    """derivation: a group's derivations.json content. Raises UnitError unless it states the deg -> rad conversion."""
    text = ((derivation or {}).get("adapter") or {}).get("unit_conversion") or ""
    if not text.startswith(UNIT_EVIDENCE_TEXT):
        raise UnitError(f"group derivations do not state '{UNIT_EVIDENCE_TEXT}': {text!r}")
    return text


# L1: draft bounds (D-UM21-Q01-1 = B), textbook end of range widened by 30 degrees.
L1_BOUNDS_DEG = {"hip_angle": (-50.0, 150.0), "knee_angle": (-30.0, 165.0), "ankle_angle": (-80.0, 50.0)}
# L2: any change larger than this between adjacent samples fails.
L2_JUMP_DEG = 30.0
L2_CHANNELS = ("pelvis_tilt", "hip_angle", "knee_angle", "ankle_angle", "thigh_angle", "shank_angle", "foot_angle")
# L3: stride duration limits (repository segmentation limits); structural, reported only.
L3_RANGE_S = (0.4, 2.5)

PROFILE = {
    "profile_id": "um21_q01_coarse_limits_v1",
    "decision": "D-UM21-Q01-1 = B: structure plus coarse physical limits; blatant errors only",
    "review_status": "draft_limits_unreviewed_scientific_approval_false",
    "population": "able-bodied adults (UMich 2021 treadmill walking: level, incline, decline)",
    "units": "limits are in degrees. Published angle columns are radians and are converted with numpy.degrees before L1 and L2 (v1 forgot this). Column units: " + json.dumps(COLUMN_UNITS),
    "applicability": "canonical rule-B columns published by T04 v2 only (hip flexion +, knee flexion +, ankle dorsiflexion +)",
    "no_tuning": "Limits were written before any data were read and are not changed to reach a pass rate.",
    "limits": {
        "L1": {"layer": "plausibility", "what": "angle sample outside bounds", "bounds_deg": L1_BOUNDS_DEG,
               "columns": sorted(L1_BOUNDS_DEG),
               "evidence": "textbook end of range (hip ext ~20-30 / flex ~120; knee flex ~135, ext 0; ankle DF ~20 / PF ~50) "
                           "plus a 30 degree margin chosen here, not from literature. Textbook values: see 'verification'."},
        "L2": {"layer": "plausibility", "what": "absolute change between adjacent samples above threshold",
               "threshold_deg": L2_JUMP_DEG, "columns": list(L2_CHANNELS),
               "evidence": "physical argument only: no walking segment turns 30 degrees between adjacent samples; "
                           "catches 180/360 degree wraps and branch jumps. Chosen, not fitted."},
        "L4": {"layer": "structural", "what": "non-finite sample (the source zero-fill NaN) is reported as missing, "
                                              "with its sample index; missing is never a pass"},
        "L3": {"layer": "structural", "what": "stride time (frames b - a)/100 Hz outside range; reported, never a filter",
               "range_s": L3_RANGE_S},
    },
    "verification": {
        "textbook_values": "Not confirmed against a primary text (AAOS/Norkin & White not read). A web search "
                           "(2026-11-06) returned secondary pages that give hip flexion 120, hip extension 20-30, "
                           "knee flexion 135, ankle dorsiflexion 20, plantarflexion 50 (Enlyte workers' comp explainer; "
                           "a Knowt study set), but other pages give different values (hip flexion 100, knee 150, "
                           "dorsiflexion 30). Treat the textbook values as UNVERIFIED. The sources disagree by up to "
                           "about 30 degrees and our margin is 30, so a few degrees of difference would not change any "
                           "result; larger differences are not ruled out by this check.",
    },
    "channel_coverage": {
        "ankle_angle": "L1 + L2; offset unverified: a pass means only 'not blatantly impossible'",
        "hip_angle": "L1 + L2", "knee_angle": "L1 + L2",
        "pelvis_tilt": "L2 only (no cited range)",
        "thigh_angle": "L2 only; derived planar approximation from the published pelvis (T04); T03 segment columns are never used",
        "shank_angle": "L2 only; same as thigh", "foot_angle": "L2 only; same as thigh",
        "hip_moment": "unchecked (no limit)", "knee_moment": "unchecked (no limit)", "ankle_moment": "unchecked (no limit)",
        "hip_power": "unchecked (no limit); held in some recordings, then no column",
        "knee_power": "unchecked (no limit); held in some recordings, then no column",
        "ankle_power": "unchecked (no limit); held in some recordings, then no column",
        "pelvis_tilt_velocity": "unchecked (no limit)", "thigh_angle_velocity": "unchecked (no limit)",
        "shank_angle_velocity": "unchecked (no limit)", "foot_angle_velocity": "unchecked (no limit)",
    },
}


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


# ---------------------------------------------------------------- pure assessment
def parse_observation_id(oid):
    m = ID_RE.match(oid or "")
    if not m:
        return None
    sub, cond, side, a, b = m.groups()
    return {"subject": sub, "condition": cond, "side": side, "start": int(a), "end": int(b)}


def stride_time_s(parsed):
    return (parsed["end"] - parsed["start"]) / RATE_HZ


def limit_failures(channel, x):
    """[(limit, sample_index, value, reason)] for one 150-sample channel. NaN/inf samples are missing: they
    never fail and never count as evidence of passing. For L2 a pair is used only if both samples are finite."""
    x = np.asarray(x, dtype=float)
    out = []
    finite = np.isfinite(x)
    if channel in L1_BOUNDS_DEG:
        lo, hi = L1_BOUNDS_DEG[channel]
        for i in np.flatnonzero(finite & ((x < lo) | (x > hi))):
            out.append(("L1", int(i), float(x[i]), f"{channel} {x[i]:.1f} deg outside [{lo:g}, {hi:g}] deg"))
    if channel in L2_CHANNELS and len(x) > 1:
        d = np.diff(x)
        ok = finite[1:] & finite[:-1]
        for i in np.flatnonzero(ok & (np.abs(d) > L2_JUMP_DEG)):
            out.append(("L2", int(i) + 1, float(d[i]),
                        f"{channel} changes {d[i]:.1f} deg between samples {int(i)} and {int(i) + 1} (limit {L2_JUMP_DEG:g})"))
    return out


def channel_state(channel, x, failures):
    """State of one channel of one observation. x is None for a channel with no column."""
    if x is None:
        return "not_checked_no_column"
    if not np.isfinite(np.asarray(x, dtype=float)).any():
        return "unchecked_all_missing"
    if channel not in L1_BOUNDS_DEG and channel not in L2_CHANNELS:
        return "unchecked"
    if failures:
        return "fail"
    if channel == "ankle_angle":
        return "pass_offset_unverified"
    if channel in L1_BOUNDS_DEG:
        return "pass"
    return "pass_jump_only"


def assess_observation(oid, side_column, samples, arrays, units=None):
    """One mapped observation. samples: the 150 sample indices as read; arrays: channel -> array or None
    (None = no column). Returns (entry, failures). Structural and plausibility layers are kept separate."""
    for ch in CHANNELS:
        if arrays.get(ch) is not None and (units or {}).get(ch) is None:
            raise UnitError(f"no unit given for column {ch!r}; refusing to assess")
        if (ch in L1_BOUNDS_DEG or ch in L2_CHANNELS) and arrays.get(ch) is not None and units[ch] != "deg":
            raise UnitError(f"{ch} is in {units[ch]!r}; limits are in degrees, convert first")
    parsed = parse_observation_id(oid)
    s_problems = []
    if list(samples) != list(range(N_SAMPLES)):
        s_problems.append("S1 samples are not 0..149 contiguous")
    if parsed is None:
        s_problems.append("S2 id does not parse")
    elif side_column != parsed["side"]:
        s_problems.append(f"S2 reference_side {side_column!r} differs from the id side {parsed['side']!r}")
    st = stride_time_s(parsed) if parsed else None
    missing, chans, fails = {}, {}, []
    for ch in CHANNELS:
        x = arrays.get(ch)
        if x is not None:
            bad = np.flatnonzero(~np.isfinite(np.asarray(x, dtype=float)))
            if len(bad):
                missing[ch] = [int(i) for i in bad]
        f = limit_failures(ch, x) if x is not None else []
        chans[ch] = channel_state(ch, x, f)
        fails.extend({"observation_id": oid, "channel": ch, "limit": lim, "sample_index": i, "value": v, "reason": why}
                     for lim, i, v, why in f)
    entry = {
        "observation_id": oid, "assessed": True,
        "structural": {"state": "fail" if s_problems else "pass", "problems": s_problems,
                       "missing_samples": missing,
                       "stride_time_s": st,
                       "L3_stride_time_outside_range_reported_only": bool(st is not None and not (L3_RANGE_S[0] <= st <= L3_RANGE_S[1]))},
        "plausibility": {"channels": chans, "failed_channels": sorted({f["channel"] for f in fails}),
                         "failed_limits": sorted({f["limit"] for f in fails})},
        "overall": "failed" if (fails or s_problems) else "no_failure_found",
    }
    return entry, fails


# ---------------------------------------------------------------- T04 enumeration (from receipts, never a glob)
def t04_records(root=ROOT):
    """{recording: {"table","map","table_sha256","map_sha256","root","subject"}} from the ten v2 launcher receipts.
    Each receipt must be completed and clean; 44 records; no root may hold INVALID_DO_NOT_USE.txt."""
    out = {}
    for sub in SUBJECTS:
        r = json.loads((Path(root) / T04_RECEIPT.format(sub)).read_text())
        if r.get("status") != "completed" or r.get("clean_success") is not True:
            raise ValueError(f"T04 receipt {sub} is not a clean completed run")
        base = Path(r["spec"]["output_root"])
        if (base / "INVALID_DO_NOT_USE.txt").exists():
            raise ValueError(f"{base} is marked INVALID")
        files = {o["path"]: o["sha256"] for o in r["outputs"]}
        for p, h in files.items():
            m = re.fullmatch(r"records/(AB\d{2})_([di]\d+)/observations_signed\.parquet", p)
            if not m:
                continue
            rec = f"{m.group(1)}/{m.group(2)}"
            mp = f"records/{m.group(1)}_{m.group(2)}/observation_map.json"
            if rec in out or mp not in files:
                raise ValueError(f"{rec}: duplicate or missing map in receipts")
            out[rec] = {"subject": sub, "root": str(base), "files": files, "table": str(base / p), "table_sha256": h,
                        "map": str(base / mp), "map_sha256": files[mp]}
    if len(out) != 44:
        raise ValueError(f"T04 receipts list {len(out)} records, expected 44")
    return out


def read_table(path, expected_sha256):
    """The T04 observation table for one recording: ids, sides, samples and the float channels, read in small
    batches. The file is hashed against the T04 receipt first."""
    if sha256_file(path) != expected_sha256:
        raise ValueError(f"{path} differs from its T04 receipt hash")
    import pyarrow.parquet as pq
    with open(path, "rb") as fh:
        pf = pq.ParquetFile(fh, buffer_size=0)
        names = pf.schema_arrow.names
        cols = [c for c in names if c in CHANNELS]
        unknown = [c for c in names if c not in CHANNELS and c not in ("observation_id", "reference_side", "sample")]
        ids, sides, samples, data = [], [], [], {c: [] for c in cols}
        for b in pf.iter_batches(batch_size=READ_BATCH_ROWS, use_threads=False):
            ids.extend(b.column("observation_id").to_pylist())
            sides.extend(b.column("reference_side").to_pylist())
            samples.append(b.column("sample").to_numpy(zero_copy_only=False))
            for c in cols:
                data[c].append(b.column(c).to_numpy(zero_copy_only=False).astype(float))
    return ids, sides, np.concatenate(samples), {c: np.concatenate(v) for c, v in data.items()}, unknown


def group_observations(ids):
    """[(id, start, stop)] for consecutive runs of the same id; ids reappearing later are reported."""
    runs, repeated, seen = [], [], set()
    i = 0
    while i < len(ids):
        j = i
        while j < len(ids) and ids[j] == ids[i]:
            j += 1
        if ids[i] in seen:
            repeated.append(ids[i])
        seen.add(ids[i])
        runs.append((ids[i], i, j))
        i = j
    return runs, repeated


def assess_recording(rec, info, no_twin):
    ids, sides, samples, data, unknown = read_table(info["table"], info["table_sha256"])
    if sha256_file(info["map"]) != info["map_sha256"]:
        raise ValueError(f"{info['map']} differs from its T04 receipt hash")
    omap = json.loads(Path(info["map"]).read_text())
    unit_evidence = {}
    for leg in ("left", "right"):  # unit evidence from each group's derivations (hash-checked against the T04 receipt)
        rel = f"records/{rec.replace('/', '_')}/groups/{rec.replace('/', '_')}_{leg}/derivations.json"
        dp = Path(info["root"]) / rel
        if info["files"].get(rel) is None or sha256_file(dp) != info["files"][rel]:
            raise UnitError(f"{rel} is missing from the T04 receipt or differs from it")
        unit_evidence[leg] = check_unit_evidence(json.loads(dp.read_text()))
    data, units = convert_to_degrees(data)
    decisions = omap["recording_rule"]["decisions"]
    held = {ch: d["decided_by"] for ch, d in decisions.items() if d["decision"] == "hold"}
    mapped_ids = {o["observation_id"] for o in omap["observations"] if o["status"] == "mapped"}
    unmapped = [{"observation_id": o["observation_id"], "recording": rec, "status": o["status"], "reason": o["reason"],
                 "assessment": "unassessed: no published values; already left out by T04 (D-UM21-T04-2 = A)"}
                for o in omap["observations"] if o["status"] != "mapped"]
    runs, repeated = group_observations(ids)
    entries, fails, rec_problems = [], [], []
    if repeated:
        rec_problems.append(f"S3 ids appear in more than one run: {sorted(set(repeated))[:5]}")
    if {r[0] for r in runs} != mapped_ids:
        rec_problems.append("S2 table ids differ from the mapped ids in the observation map")
    if unknown:
        rec_problems.append(f"table has columns outside the T04 channel list: {unknown}")
    for oid, a, b in runs:
        arrays = {c: (data[c][a:b] if c in data else None) for c in CHANNELS}
        entry, f = assess_observation(oid, sides[a], samples[a:b], arrays, units)
        entry["recording"] = rec
        if (b - a) != N_SAMPLES:
            entry["structural"]["state"] = "fail"
            entry["structural"]["problems"].append(f"S1 {b - a} rows, expected {N_SAMPLES}")
            entry["overall"] = "failed"
        entry["channels_without_column"] = sorted(c for c in CHANNELS if c not in data)
        entries.append(entry), fails.extend(f)
    summary = {"recording": rec, "t04_root": info["root"], "table_sha256": info["table_sha256"],
               "map_sha256": info["map_sha256"], "observations_in_table": len(runs),
               "observations_unmapped": len(unmapped), "columns_present": sorted(data), "units_after_conversion": units,
               "unit_evidence": unit_evidence,
               "channels_held_no_column": held, "record_problems": rec_problems,
               "observations_without_normalized_twin_record_level": no_twin}
    return entries, fails, unmapped, summary


def no_twin_counts():
    p = ROOT / C02_REPORT
    if sha256_file(p) != C02_REPORT_SHA256:
        raise ValueError("the C02 pelvis report differs from its reviewed hash")
    d = json.loads(p.read_text())
    return {r["record"]: r["t03_written_total"] - r["t03_written_with_normalized_twin"] for r in d["records"]}


# ---------------------------------------------------------------- spec
def stage_recordings(stage):
    return list(PILOT_RECORDINGS) if stage == "pilot" else sorted(t04_records())


def stage_paths(stage):
    return {"job_id": f"{TASK_ID}-{stage}-{VERSION}",
            "spec": f"docs/quality/audits/um21-q01-{stage}-spec-{VERSION}.json",
            "output_root": f"converted_datasets/reconversion_v2/um21_q01_{stage}_{VERSION}",
            "receipt": f"docs/quality/audits/um21-q01-{stage}-launcher-receipt-{VERSION}.json"}


def build_spec(stage):
    p = stage_paths(stage)
    b = {RUNNER: sha256_file(ROOT / RUNNER), C02_REPORT: C02_REPORT_SHA256}
    for sub in SUBJECTS:
        b[T04_RECEIPT.format(sub)] = sha256_file(ROOT / T04_RECEIPT.format(sub))
    return {"job_id": p["job_id"],
            "command": ["python3", RUNNER, "run", "--output-root", p["output_root"], "--stage", stage,
                        "--recordings", ",".join(stage_recordings(stage))],
            "cwd": str(ROOT), "output_root": p["output_root"], "receipt_path": p["receipt"], "bindings": b,
            "timeout_seconds": 3600, "kill_after_seconds": 30, "poll_seconds": 15,
            "startup_memory_mib": {"linux": 3584, "windows": 2816},
            "runtime_memory_mib": {"linux": 2048, "windows": 2048},
            "expected_output_names": ["assessment.json"], "address_space_mib": ADDRESS_SPACE_MIB}


def plan(stage):
    from contributor_tools.guarded_launcher import validate_spec
    spec = build_spec(stage)
    validate_spec(spec)
    path = ROOT / stage_paths(stage)["spec"]
    with path.open("x", encoding="utf-8") as f:
        f.write(json.dumps(spec, indent=1) + "\n")
    print(json.dumps({"spec": str(path), "sha256": sha256_file(path)}))


def run(args):
    if os.nice(0) < 19:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (niceness 19 expected)")
    soft, _ = resource.getrlimit(resource.RLIMIT_AS)
    if soft == resource.RLIM_INFINITY or soft > ADDRESS_SPACE_MIB * 1024 ** 2:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (address-space limit expected)")
    recordings = args.recordings.split(",")
    if recordings != stage_recordings(args.stage):
        raise SystemExit("refused: --recordings are not the pilot sample or the 44 T04 records")
    if _mem_available() < MIN_AVAILABLE_BYTES:
        raise MemoryError("less than 2 GiB available; not started")
    records = t04_records()
    no_twin = no_twin_counts()
    out = (ROOT / args.output_root).resolve()
    out.mkdir(parents=True, exist_ok=False)
    started = time.time()
    fail_by_limit, fail_obs_by_limit, fail_by_channel, worst = {}, {}, {}, []
    failing_strides, fail_by_rec = [], {}
    states, overall, totals = {}, {}, {"observations": 0, "unmapped": 0}
    summaries, unmapped_all, rec_problems = [], [], {}
    with open(out / "observations.jsonl", "x") as fo, open(out / "failures.jsonl", "x") as ff:
        for rec in recordings:
            if _mem_available() < MIN_AVAILABLE_BYTES:
                raise MemoryError("less than 2 GiB available; stopped at a recording boundary")
            entries, fails, unmapped, summ = assess_recording(rec, records[rec], no_twin.get(rec))
            for e in entries:
                e["normalized_crosscheck"] = ("record-level count only: this record has "
                                              f"{no_twin.get(rec)} observations without a normalized twin; "
                                              "which ones is not recorded in the C02 report" if no_twin.get(rec) else "all twinned")
                fo.write(json.dumps(e) + "\n")
                overall[e["overall"]] = overall.get(e["overall"], 0) + 1
                for ch, s in e["plausibility"]["channels"].items():
                    states.setdefault(ch, {}).setdefault(s, 0)
                    states[ch][s] += 1
                for lim in e["plausibility"]["failed_limits"]:
                    fail_obs_by_limit[lim] = fail_obs_by_limit.get(lim, 0) + 1
                    d = fail_by_rec.setdefault(rec, {})
                    d[lim] = d.get(lim, 0) + 1
                if e["overall"] == "failed":
                    mine = [f for f in fails if f["observation_id"] == e["observation_id"]]
                    failing_strides.append({"observation_id": e["observation_id"], "recording": rec,
                                            "structural_problems": e["structural"]["problems"],
                                            "failed": sorted({f"{f['limit']}:{f['channel']}" for f in mine}),
                                            "worst_value_deg": max((abs(f["value"]) for f in mine), default=None)})
            for f in fails:
                ff.write(json.dumps(f) + "\n")
                fail_by_limit[f["limit"]] = fail_by_limit.get(f["limit"], 0) + 1
                k = f"{f['limit']}:{f['channel']}"
                fail_by_channel[k] = fail_by_channel.get(k, 0) + 1
                worst.append(f)
            if len(worst) > 200:  # keep only the largest values (by size of the value) to bound memory
                worst = sorted(worst, key=lambda f: -abs(f["value"]))[:50]
            totals["observations"] += len(entries)
            totals["unmapped"] += len(unmapped)
            unmapped_all.extend(unmapped)
            summ["peak_rss_mib_after_record"] = round(_peak_rss_mib(), 1)
            summaries.append(summ)
            if summ["record_problems"]:
                rec_problems[rec] = summ["record_problems"]
            print(f"{rec} done, {len(entries)} observations, {len(fails)} failed samples, peak RSS {_peak_rss_mib():.0f} MiB",
                  flush=True)
            if _peak_rss_mib() > RSS_CAP_MIB:
                raise MemoryError(f"peak RSS {_peak_rss_mib():.0f} MiB above {RSS_CAP_MIB}; stopped")
    worst = sorted(worst, key=lambda f: -abs(f["value"]))[:10]
    held = [{"recording": s["recording"], "channel": ch, "reason": why}
            for s in summaries for ch, why in s["channels_held_no_column"].items()]
    full = args.stage == "full"
    expected_ok = (not full) or (totals["observations"] == 7547 and totals["unmapped"] == 15)
    assessment = {
        "task_id": TASK_ID, "stage": args.stage, "scientific_approval": False,
        "note": "automated assessment, coarse limits (D-UM21-Q01-1 = B); independent review follows",
        "profile": PROFILE,
        "unit_handling": "published angle columns are radians (evidence per recording in per_record.unit_evidence); "
                         "converted to degrees before L1 and L2; unknown unit raises UnitError; failure values are degrees",
        "inputs": {"t04_receipts": [T04_RECEIPT.format(s) for s in SUBJECTS],
                   "c02_report": C02_REPORT, "c02_report_sha256": C02_REPORT_SHA256,
                   "records": {r: {k: records[r][k] for k in ("root", "table_sha256", "map_sha256")}
                               for r in recordings}},
        "sidecar_files": {n: {"sha256": sha256_file(out / n), "bytes": (out / n).stat().st_size}
                          for n in ("observations.jsonl", "failures.jsonl")},
        "sidecar_reading": "observations.jsonl: one entry per assessed observation (structural and plausibility "
                           "layers separate; overall = failed | no_failure_found, never 'passed' because columns "
                           "stay unchecked). failures.jsonl: one row per failed sample (observation_id, channel, "
                           "limit, sample_index, value, reason).",
        "totals": {**totals, "expected_for_full": {"observations": 7547, "unmapped": 15}, "matches_expected": expected_ok},
        "overall_counts": overall,
        "strides_failed_by_limit": fail_obs_by_limit,
        "strides_failed_by_recording_and_limit": fail_by_rec,
        "failing_strides": failing_strides,
        "failed_samples_by_limit": fail_by_limit,
        "failed_samples_by_limit_and_channel": fail_by_channel,
        "worst_examples": worst,
        "channel_states": states,
        "unmapped_observations": unmapped_all,
        "held_channels_no_column": held,
        "held_channels_note": "A held channel has no column: not_checked_no_column, never a pass.",
        "observations_without_normalized_twin": {
            "total_record_level": sum(no_twin.get(s["recording"]) or 0 for s in summaries),
            "per_record": {s["recording"]: no_twin.get(s["recording"]) for s in summaries}},
        "record_problems": rec_problems,
        "per_record": summaries,
        "resources": {"peak_rss_mib": round(_peak_rss_mib(), 1), "rss_cap_mib": RSS_CAP_MIB,
                      "rlimit_as_bytes": list(resource.getrlimit(resource.RLIMIT_AS)), "nice": os.nice(0),
                      "wall_seconds": round(time.time() - started, 1)},
    }
    with open(out / "assessment.json", "x") as f:
        json.dump(assessment, f, indent=1, allow_nan=False)
    print(json.dumps({"totals": totals, "overall": overall, "failed_strides_by_limit": fail_obs_by_limit,
                      "peak_rss_mib": assessment["resources"]["peak_rss_mib"]}))
    return 0 if (expected_ok and not rec_problems) else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="step", required=True)
    pp = sub.add_parser("plan")
    pp.add_argument("--stage", choices=("pilot", "full"), required=True)
    pr = sub.add_parser("run")
    pr.add_argument("--output-root", required=True)
    pr.add_argument("--stage", choices=("pilot", "full"), required=True)
    pr.add_argument("--recordings", required=True)
    args = p.parse_args(argv)
    if args.step == "plan":
        plan(args.stage)
        return 0
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
