#!/usr/bin/env python3
"""UM21-T04: apply the bound CORE-11 sign-application build to the T03 treadmill observations.

Option (a) of the coordinator ruling: the bound hook runs UNCHANGED on the adapter's strides (consecutive
source heel strikes 50-250 frames apart, one group per recording and leg) and settles one multiplier and
one publication verdict per channel, leg and recording. A T03 observation receives the hook's published
rule-B arrays only if its observation id equals a hook unit id exactly. The bound hook has no function that
applies a settled multiplier to other arrays (undo_sign_application checks every array hash), so an
observation without a hook unit is NOT signed: it is listed with a reason and stays unassessed. Held
channels are never written. Nothing here edits T03 outputs or a bound file.

Steps
``plan --stage a|b``  write and validate a guarded-launcher spec (no research data read).
``run ...``           the job; only through ``python3 -m contributor_tools.guarded_launcher run SPEC.json``.
                      One recording at a time: T03 observation ids (two columns), then the adapter and hook,
                      then segments and velocities derived after the hook (F2), then per-observation
                      selection. New output root only; T03 files are read, hashed against the T03 receipts
                      and never written. ``--mode full`` installs ModeProxy, which hands the committed v4 CORE-11 pilot
                      record (path and sha256 fixed as constants here, bound in the spec) to the bound
                      hook; the unmodified check_pilot_record then gates every group.
One-leg rule (R01): a channel is published for a recording only if both legs published it with the same
multiplier; otherwise it is held for the whole recording and the deciding leg is logged; a multiplier
disagreement holds both and is flagged. Derived segments and velocities follow their inputs.

This file is outside the bound sign-application build. It is bound in the job spec like any other code.
scientific_approval is false everywhere.
"""
from __future__ import annotations

import os
for _key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_key, "1")
# pyarrow's default (jemalloc/mimalloc) pool reserves address space beyond the 768 MiB launcher cap; the system
# pool must be chosen before pyarrow is imported (UM21-T04 pre-launch review B1).
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import re
import resource
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_by_file(name, path):
    """Load a module from its file (no package __init__ runs); reuse an already loaded one only if it is
    the same file."""
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(name, None)
            raise
    if Path(module.__file__).resolve() != Path(path).resolve():
        raise ImportError(f"{name} already imported from {module.__file__}")
    return module


um21 = _load_by_file("contributor_tools.adapters.um21_sign_adapter", ROOT / "contributor_tools/adapters/um21_sign_adapter.py")
sa = um21.sa
pilot = _load_by_file("contributor_tools.run_core11_um21_pilot", ROOT / "contributor_tools/run_core11_um21_pilot.py")
PACKAGE_INITS = ("contributor_tools", "contributor_tools.common", "contributor_tools.adapters")

TASK_ID = "UM21-T04"
RUNNER = "contributor_tools/run_um21_t04_signs.py"
SOURCE = pilot.SOURCE
CENSUS = pilot.CENSUS
C03 = pilot.C03
T03_JOBS = ("batch0", "batch1", "v2-batch2", "v2-batch3", "v2-batch4", "v2-batch5", "v2-batch6")
T03_RECEIPT = "docs/quality/audits/um21-t03-{}-launcher-receipt.json"  # batch2 (INVALID run) is never listed
PILOT_RECORD = "docs/quality/audits/core11-p-um21-pilot-record-v4.json"
PILOT_RECORD_SHA256 = "c459e7a7238105547d0efa10d6a6173af0f0bb5aafc6981023e9cad759788be3"
PILOT_RECEIPT = "docs/quality/audits/core11-p-um21-launcher-receipt-v4.json"
PILOT_RECEIPT_SHA256 = "3b6ff3f4759a9e5e90d77ded35079ab4851f2310e6a579740fcccd6163724505"
SEED = 20261103
N_RANDOM = 5
STAGE_A = ("AB04/i0",)             # the logged pelvis correction (D-UM21-P01-1 = C)
STAGE_B_REQUIRED = ("AB05/i5",)    # J0: 4 observations outside the hook stride rule, in both legs' tables
RSS_CAP_MIB = 300.0
ADDRESS_SPACE_MIB = 768
MIN_AVAILABLE_BYTES = 2 * 1024 ** 3
N_SAMPLES = 150
ID_RE = re.compile(r"^um21:Streaming/(AB\d{2})/Tread/([di]\d+):(right|left):frames:(\d+):(\d+)$")
LEGS = ("right", "left")
READ_BATCH_ROWS = 4096
WRITE_OBSERVATIONS = 20
VERSION = {"a": "v3", "b": "v3", "full": "v1"}  # v3 pilots: the runner changed after the v2 pilots (full mode, one-leg rule)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# ---------------------------------------------------------------- hook mode proxy (no bound file edited)
class ModeProxy:
    """Stands in for the sign_application module inside the adapter: identical except that, in mode 'full',
    the committed pilot record path is handed to the bound hook (the adapter's apply_leg has no such
    argument). Everything else is delegated to the real module."""

    def __init__(self, base, pilot_record_path=None):
        self._base, self._record = base, pilot_record_path

    def run_sign_application(self, **kw):
        if kw.get("mode") == "full":
            if not self._record:
                raise ValueError("mode full needs --pilot-record")
            kw["pilot_record_path"] = self._record
        return self._base.run_sign_application(**kw)

    def __getattr__(self, name):
        return getattr(self._base, name)


def pilot_record_path(root=ROOT, expected=None):
    """Absolute path of the committed v4 pilot record, after its sha256 equals the constant. The path is never
    taken from the command line."""
    path = Path(root) / PILOT_RECORD
    want = PILOT_RECORD_SHA256 if expected is None else expected
    if not path.is_file() or sha256_file(path) != want:
        raise ValueError(f"{PILOT_RECORD} is missing or its sha256 differs from the reviewed constant")
    return str(path)


def install_full_mode(record_path):
    """Full mode only: the adapter's hook module is replaced by ModeProxy for this process."""
    um21.sa = ModeProxy(sa, record_path)


# ---------------------------------------------------------------- one-leg rule (pure)
def settle_recording(hook_logs, segment_logs, velocity_logs):
    """The recording-level publication rule from per-leg hook logs.

    hook_logs: leg -> {channel: {"publication", "multiplier"}} (the hook's log channels); segment_logs and
    velocity_logs: leg -> the derivation logs ({"derived": {...}}). Returns (kept, decisions, flags):
    kept = hook channels and derived channels to write, decisions = per channel {"decision", "decided_by",
    "legs", "flag"}, flags = review items. Rule: publish a hook channel only if BOTH legs published it with
    the same multiplier; if either leg held it, hold it for the whole recording and name the deciding leg(s);
    if both published with different multipliers, hold both and flag it. A derived segment is kept only if
    both legs derived it and every input is kept; a derived velocity only if both derived it from a kept
    angle."""
    legs = sorted(hook_logs)
    if legs != ["left", "right"]:
        raise ValueError(f"both legs are required, got {legs}")
    kept, decisions, flags = set(), {}, []
    for ch in sorted(set().union(*[set(hook_logs[l]) for l in legs])):
        info = {l: ({"publication": hook_logs[l][ch]["publication"], "multiplier": hook_logs[l][ch]["multiplier"]}
                    if ch in hook_logs[l] else {"publication": "absent", "multiplier": None}) for l in legs}
        pub = [l for l in legs if info[l]["publication"] == "publish"]
        flag = None
        if len(pub) == 2 and info["left"]["multiplier"] == info["right"]["multiplier"]:
            decision, by = "publish", "both legs published with the same multiplier"
            kept.add(ch)
        elif len(pub) == 2:
            decision, by, flag = "hold", "both legs published with different multipliers", "multiplier_disagreement"
            flags.append({"kind": flag, "channel": ch, "multipliers": {l: info[l]["multiplier"] for l in legs}})
        else:
            held = [l for l in legs if l not in pub]
            decision = "hold"
            by = ("both legs held" if len(held) == 2 else f"{held[0]} leg did not publish (the other published)")
        decisions[ch] = {"decision": decision, "decided_by": by, "legs": info, "flag": flag}
    for seg in list(segment_logs["right"]["derived"]):
        both = all(seg in segment_logs[l]["derived"] for l in legs)
        inputs = set(segment_logs["right"]["derived"][seg]["inputs_sha256"]) if both else set()
        for l in legs:
            if seg in segment_logs[l]["derived"]:
                inputs |= set(segment_logs[l]["derived"][seg]["inputs_sha256"])
        missing = sorted(inputs - kept)
        ok = both and not missing
        if ok:
            kept.add(seg)
        decisions[seg] = {"decision": "derive" if ok else "hold", "legs": {l: seg in segment_logs[l]["derived"] for l in legs},
                          "decided_by": "derived on both legs from kept inputs" if ok else
                          ("not derived on both legs" if not both else f"inputs not kept: {missing}"), "flag": None}
    for vel in sorted(set().union(*[set(velocity_logs[l]["derived"]) for l in legs])):
        both = all(vel in velocity_logs[l]["derived"] for l in legs)
        src = {velocity_logs[l]["derived"][vel]["from"] for l in legs if vel in velocity_logs[l]["derived"]}
        ok = both and len(src) == 1 and src <= kept
        if ok:
            kept.add(vel)
        decisions[vel] = {"decision": "derive" if ok else "hold", "legs": {l: vel in velocity_logs[l]["derived"] for l in legs},
                          "decided_by": "derived on both legs from a kept angle" if ok else
                          f"not derived on both legs or angle {sorted(src)} not kept", "flag": None}
    return kept, decisions, flags


# ---------------------------------------------------------------- T03 enumeration (from receipts, never a glob)
def t03_records(root=ROOT):
    """{recording: {"phase": path, "sha256": receipt sha256 of that phase.parquet, "job": name}} from the seven
    valid T03 launcher receipts. Each receipt must be completed and clean. The INVALID batch2 root is not in
    T03_JOBS and nothing is globbed."""
    out = {}
    for job in T03_JOBS:
        path = Path(root) / T03_RECEIPT.format(job)
        r = json.loads(path.read_text())
        if r.get("status") != "completed" or r.get("clean_success") is not True:
            raise ValueError(f"T03 receipt {job} is not a clean completed run")
        base = Path(r["spec"]["output_root"])
        for o in r["outputs"]:
            m = re.fullmatch(r"components/(AB\d{2})/([di]\d+)/phase\.parquet", o["path"])
            if m:
                rec = f"{m.group(1)}/{m.group(2)}"
                if rec in out:
                    raise ValueError(f"{rec} appears in two T03 receipts")
                out[rec] = {"phase": str(base / o["path"]), "sha256": o["sha256"], "job": job}
    if len(out) != 44:
        raise ValueError(f"T03 receipts list {len(out)} records, expected 44")
    return out


def read_t03_observations(phase_path, expected_sha256=None):
    """[(observation_id, reference_side)] in first-seen order, from two columns only. The file is hashed
    against the T03 receipt first."""
    import pyarrow.parquet as pq
    if expected_sha256 is not None and sha256_file(phase_path) != expected_sha256:
        raise ValueError(f"{phase_path}: sha256 differs from the T03 receipt")
    ids, sides = [], []
    with open(phase_path, "rb") as fh:
        pf = pq.ParquetFile(fh, buffer_size=0)
        for batch in pf.iter_batches(batch_size=READ_BATCH_ROWS, columns=["observation_id", "reference_side"],
                                     use_threads=False):
            ids.extend(batch.column(0).to_pylist())
            sides.extend(batch.column(1).to_pylist())
    seen = {}
    for i, s in zip(ids, sides):
        if seen.setdefault(i, s) != s:
            raise ValueError(f"{i}: reference_side changes within an observation")
    return list(seen.items())


# ---------------------------------------------------------------- observation-to-unit mapping (pure)
def parse_observation_id(oid):
    m = ID_RE.fullmatch(oid) if isinstance(oid, str) else None
    if not m:
        raise ValueError(f"observation id {oid!r} is not a UM21 treadmill stride id")
    return {"subject": m.group(1), "condition": m.group(2), "leg": m.group(3), "a": int(m.group(4)),
            "b": int(m.group(5))}


def unmapped_reason(parsed, frames=um21.STRIDE_FRAMES):
    n, (lo, hi) = parsed["b"] - parsed["a"], frames
    if n < lo:
        return f"{n} frames, below the hook stride rule minimum of {lo}"
    if n > hi:
        return f"{n} frames, above the hook stride rule maximum of {hi}"
    return (f"{n} frames, inside the stride rule but not a pair of consecutive source heel strikes (or outside "
            "the recording) for this leg")


def map_observations(observations, unit_ids_by_leg, recording):
    """Exact-id mapping. Returns (rows, hook_units_without_observation). A row is mapped only when the
    observation id is one of that leg's hook unit ids; otherwise it is unmapped with a reason. The side in the
    id, the T03 reference_side and the recording must agree or the id is refused."""
    subject, condition = recording.split("/")
    lookup = {leg: {u: i for i, u in enumerate(units)} for leg, units in unit_ids_by_leg.items()}
    rows, used = [], {leg: set() for leg in unit_ids_by_leg}
    seen = set()
    for oid, side in observations:
        if oid in seen:
            raise ValueError(f"duplicate observation id {oid}")
        seen.add(oid)
        p = parse_observation_id(oid)
        if (p["subject"], p["condition"]) != (subject, condition):
            raise ValueError(f"{oid} does not belong to {recording}")
        if side is not None and str(side).strip().lower()[:1] != p["leg"][0]:
            raise ValueError(f"{oid}: reference_side {side!r} disagrees with the id")
        i = lookup[p["leg"]].get(oid)
        if i is None:
            rows.append({"observation_id": oid, "leg": p["leg"], "status": "unmapped", "unit_index": None,
                         "hook_unit_id": None, "reason": unmapped_reason(p),
                         "assessment_state": "unassessed (no sign-applied values)"})
        else:
            used[p["leg"]].add(i)
            rows.append({"observation_id": oid, "leg": p["leg"], "status": "mapped", "unit_index": i,
                         "hook_unit_id": oid, "reason": None, "assessment_state": "signs applied by the hook"})
    extra = {leg: len(units) - len(used[leg]) for leg, units in unit_ids_by_leg.items()}
    return rows, extra


def select_observation_arrays(rows, per_leg_arrays):
    """{channel: (n_mapped, 150)} for the mapped rows in row order, plus the observation ids. per_leg_arrays:
    leg -> {channel: (units, 150)}. A channel absent from a leg (held) is absent from the result when it is
    absent from any leg that has a mapped observation (no half-written column)."""
    mapped = [r for r in rows if r["status"] == "mapped"]
    legs = sorted({r["leg"] for r in mapped})
    channels = None
    for leg in legs:
        ks = set(per_leg_arrays[leg])
        channels = ks if channels is None else channels & ks
    out = {k: np.stack([per_leg_arrays[r["leg"]][k][r["unit_index"]] for r in mapped]) for k in sorted(channels or [])}
    return [r["observation_id"] for r in mapped], out, sorted(set().union(*[set(per_leg_arrays[l]) for l in legs]) - set(channels or [])) if legs else []


def write_observation_table(path, obs_ids, arrays, sides):
    """Long table: observation_id, reference_side, sample (0..149), one float64 column per published or
    derived channel. Written in chunks of WRITE_OBSERVATIONS observations (one row group each) to bound
    memory and address space. Exclusive create."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    n = len(obs_ids)
    names = list(arrays)
    schema = pa.schema([("observation_id", pa.string()), ("reference_side", pa.string()),
                        ("sample", pa.int32())] + [(k, pa.float64()) for k in names])
    with open(path, "xb") as fh:
        with pq.ParquetWriter(fh, schema, compression="snappy", use_dictionary=False) as w:
            for i in range(0, n, WRITE_OBSERVATIONS):
                j = min(i + WRITE_OBSERVATIONS, n)
                cols = {"observation_id": np.repeat(np.array(obs_ids[i:j], dtype=object), N_SAMPLES).tolist(),
                        "reference_side": np.repeat(np.array(sides[i:j], dtype=object), N_SAMPLES).tolist(),
                        "sample": np.tile(np.arange(N_SAMPLES, dtype=np.int32), j - i)}
                for k in names:
                    cols[k] = np.ascontiguousarray(arrays[k][i:j], dtype=np.float64).reshape(-1)
                w.write_table(pa.table(cols, schema=schema))
    return sha256_file(path)


def reload_check(path, obs_ids, arrays):
    """Findings from re-reading the written table in batches and comparing every column bitwise."""
    import pyarrow.parquet as pq
    findings, row = [], 0
    n = len(obs_ids)
    with open(path, "rb") as fh:
        pf = pq.ParquetFile(fh, buffer_size=0)
        for batch in pf.iter_batches(batch_size=WRITE_OBSERVATIONS * N_SAMPLES, use_threads=False):
            m = batch.num_rows // N_SAMPLES
            i = row // N_SAMPLES
            if batch.column("observation_id").to_pylist()[::N_SAMPLES] != list(obs_ids[i:i + m]):
                findings.append(f"observation ids differ after reload (rows from {row})")
            for k, a in arrays.items():
                got = batch.column(k).to_numpy(zero_copy_only=False).reshape(m, N_SAMPLES)
                if got.tobytes() != np.ascontiguousarray(a[i:i + m], dtype=np.float64).tobytes():
                    findings.append(f"column {k} differs after reload (observations from {i})")
            row += batch.num_rows
    if row != n * N_SAMPLES:
        findings.append(f"reloaded {row} rows, expected {n * N_SAMPLES}")
    return findings


# ---------------------------------------------------------------- one recording
def leg_arrays(result):
    """Published hook outputs plus derived segments and velocities for one LegResult, by logical name."""
    return {**result.published, **result.segments, **result.velocities}


def process_recording(handle, rec, t03, detector_sha256, out, backlog_path, mode="pilot", pilot_record=None):
    """One recording: hook (per leg), pilot-style group checks and writes, then exact observation mapping and
    selection. Returns (record_summary, group_summaries, logs, findings_by_group, slots_by_group)."""
    observations = read_t03_observations(t03["phase"], t03["sha256"])
    facts, results = um21.convert_recording(handle, rec, detector_sha256, backlog_path=backlog_path, mode=mode)
    rdir = out / "records" / rec.replace("/", "_")
    rdir.mkdir(parents=True, exist_ok=False)
    groups, logs, found_by_group, slots = [], [], {}, {}
    per_leg = {}
    for res in results:
        manifest, written = pilot._write_group(rdir, res)
        found = pilot.check_group(res)
        found["written_outputs"] = written
        log = res.application.log
        groups.append({"group_id": res.group_id, "units": len(res.unit_ids), **manifest, "counts": log["counts"],
                       "power_slots": res.adapter_log["power_slots"], "published": res.adapter_log["published"],
                       "held": res.adapter_log["held"], "corrections_applied": log["corrections_applied"],
                       "pilot_facts": log["pilot"], "findings": found})
        found_by_group[res.group_id] = {k: v for k, v in found.items() if v and k != "not_checked"}
        logs.append({k: log[k] for k in pilot.LOG_KEYS})
        slots[res.group_id] = res.adapter_log["power_slots"]
        per_leg[res.leg] = (res, leg_arrays(res))
    kept, decisions, rule_flags = settle_recording(
        {leg: per_leg[leg][0].application.log["channels"] for leg in per_leg},
        {leg: per_leg[leg][0].segment_log for leg in per_leg}, {leg: per_leg[leg][0].velocity_log for leg in per_leg})
    per_leg = {leg: (res, {k: a for k, a in arrs.items() if k in kept}) for leg, (res, arrs) in per_leg.items()}
    rows, extra = map_observations(observations, {leg: per_leg[leg][0].unit_ids for leg in per_leg}, rec)
    sides = dict(observations)
    obs_ids, arrays, dropped = select_observation_arrays(rows, {leg: v[1] for leg, v in per_leg.items()})
    table_sha = None
    table_findings = []
    if obs_ids:
        table_sha = write_observation_table(rdir / "observations_signed.parquet", obs_ids, arrays,
                                            [sides[o] for o in obs_ids])
        table_findings = reload_check(rdir / "observations_signed.parquet", obs_ids, arrays)
    mapped = sum(r["status"] == "mapped" for r in rows)
    mult = {leg: {k: {"multiplier": c["multiplier"], "publication": c["publication"]}
                  for k, c in per_leg[leg][0].application.log["channels"].items()} for leg in per_leg}
    for r in rows:  # the multiplier is one per channel and leg; each row carries its leg's table
        if r["status"] == "mapped":
            r["leg_channel_multipliers"] = mult[r["leg"]]
            r["multiplier_scope"] = "per channel per leg per recording (hook-settled), not per stride"
    evidence = {leg: {"hook_units": len(per_leg[leg][0].unit_ids),
                      "unit_ids_sha256": hashlib.sha256("\n".join(per_leg[leg][0].unit_ids).encode()).hexdigest(),
                      "log": f"groups/{per_leg[leg][0].group_id.replace('/', '_').replace(':', '_')}/sign_application.json",
                      "multipliers": {k: {"multiplier": c["multiplier"], "publication": c["publication"]}
                                      for k, c in per_leg[leg][0].application.log["channels"].items()},
                      "evidence_rule": "one multiplier per channel for the whole leg, settled by the hook from all "
                                       "of this leg's units; each mapped observation is one of those units"}
                for leg in per_leg}
    map_doc = {"recording": rec, "scientific_approval": False, "mode": mode, "t03_phase_sha256": t03["sha256"],
               "t03_job": t03["job"], "observations": rows, "hook_units_without_observation": extra,
               "recording_rule": {"text": "publish only if both legs published with the same multiplier; else hold for the whole recording",
                                  "decisions": decisions, "flags": rule_flags},
               "channels_not_written_for_all_legs": dropped, "evidence": evidence,
               "rule": "Exact observation id = hook unit id. Unmapped observations receive no signed values "
                       "and stay unassessed (coordinator ruling, option a)."}
    map_sha = sa.write_json_exclusive(rdir / "observation_map.json", sa._finite(map_doc))
    findings = list(table_findings)
    if mapped + sum(r["status"] == "unmapped" for r in rows) != len(observations):
        findings.append("mapped + unmapped differs from the T03 observation count")
    if len(obs_ids) != mapped:
        findings.append("written observations differ from mapped observations")
    summary = {"recording": rec, "t03_observations": len(observations), "mapped": mapped,
               "unmapped": len(observations) - mapped,
               "unmapped_reasons": {r["observation_id"]: r["reason"] for r in rows if r["status"] == "unmapped"},
               "hook_units": {leg: len(per_leg[leg][0].unit_ids) for leg in per_leg},
               "hook_units_without_observation": extra, "written_columns": sorted(arrays),
               "observation_table_sha256": table_sha, "observation_map_sha256": map_sha,
               "rule_flags": rule_flags, "channels_held_by_rule": sorted(k for k, d in decisions.items() if d["decision"] == "hold"),
               "findings": findings}
    return summary, groups, logs, found_by_group, slots, facts


# ---------------------------------------------------------------- spec
def sample_b(census, seed=SEED, n_random=N_RANDOM):
    """STAGE_B_REQUIRED, one power layout-2 recording, then n_random others from one random.Random(seed).
    AB04/i0 (stage a) is not repeated."""
    rng = random.Random(seed)
    scope = [r for r in pilot.in_scope_recordings(census) if r not in STAGE_A and r not in STAGE_B_REQUIRED]
    layout2 = rng.choice(sorted(r for r in pilot.layout_2_candidates(census) if r in scope))
    pool = [r for r in scope if r != layout2]
    return list(STAGE_B_REQUIRED) + [layout2] + rng.sample(pool, n_random)


def bindings(root=ROOT):
    b = {**pilot.bindings(), RUNNER: sha256_file(root / RUNNER)}
    for job in T03_JOBS:
        b[T03_RECEIPT.format(job)] = sha256_file(root / T03_RECEIPT.format(job))
    return b


def subject_batches():
    """One batch per subject, from the seven T03 receipts only: {subject: [recordings]} (sorted)."""
    out = {}
    for rec in sorted(t03_records()):
        out.setdefault(rec.split("/")[0], []).append(rec)
    return out


def stage_paths(stage, subject=None):
    if stage in ("a", "b"):
        v, tag = VERSION[stage], f"pilot-{stage}"
    else:
        v, tag = VERSION["full"], f"full-{subject}"
    return {"job_id": f"{TASK_ID}-{tag}-{v}",
            "spec": f"docs/quality/audits/um21-t04-{tag}-spec-{v}.json",
            "output_root": f"converted_datasets/reconversion_v2/um21_t04_{tag.replace('-', '_')}_{v}",
            "receipt": f"docs/quality/audits/um21-t04-{tag}-launcher-receipt-{v}.json"}


def stage_recordings(stage, subject=None):
    if stage == "a":
        return list(STAGE_A)
    if stage == "b":
        return sample_b(json.loads((ROOT / CENSUS).read_text()))
    batches = subject_batches()
    if subject not in batches:
        raise ValueError(f"unknown subject {subject!r}; T03 subjects: {sorted(batches)}")
    return batches[subject]


def build_spec(stage, subject=None):
    recordings = stage_recordings(stage, subject)
    p = stage_paths(stage, subject)
    full = stage == "full"
    detector = sa.file_sha256(sa.DETECTOR_PATH)
    b = bindings()
    if full:  # the committed v4 pilot record and its receipt gate the run: bind both
        b[PILOT_RECORD] = PILOT_RECORD_SHA256
        b[PILOT_RECEIPT] = PILOT_RECEIPT_SHA256
        if sha256_file(ROOT / PILOT_RECORD) != PILOT_RECORD_SHA256 or sha256_file(ROOT / PILOT_RECEIPT) != PILOT_RECEIPT_SHA256:
            raise ValueError("the v4 pilot record or receipt differs from the reviewed constants")
    cmd = ["python3", RUNNER, "run", "--output-root", p["output_root"], "--detector-sha256", detector,
           "--recordings", ",".join(recordings), "--stage", stage, "--mode", "full" if full else "pilot"]
    if full:
        cmd += ["--subject", subject]
    return {
        "job_id": p["job_id"], "command": cmd,
        "cwd": str(ROOT), "output_root": p["output_root"], "receipt_path": p["receipt"],
        "bindings": b,
        "timeout_seconds": 3600, "kill_after_seconds": 30, "poll_seconds": 15,
        "startup_memory_mib": {"linux": 3584, "windows": 2816},
        "runtime_memory_mib": {"linux": 2048, "windows": 2048},
        "expected_output_names": ["t04_summary.json"],
        "address_space_mib": ADDRESS_SPACE_MIB,
    }


def plan(stage, spec_out=None, subject=None):
    from contributor_tools.guarded_launcher import validate_spec
    spec = build_spec(stage, subject)
    validate_spec(spec)
    path = Path(spec_out or ROOT / stage_paths(stage, subject)["spec"])
    with path.open("x", encoding="utf-8") as f:  # never overwrite a spec
        f.write(json.dumps(spec, indent=1) + "\n")
    print(json.dumps({"spec": str(path), "sha256": sha256_file(path),
                      "recordings": spec["command"][spec["command"].index("--recordings") + 1]}))


# ---------------------------------------------------------------- the job
def _peak_rss_mib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def run(args):
    if os.nice(0) < 19:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (niceness 19 expected)")
    soft, _ = resource.getrlimit(resource.RLIMIT_AS)
    if soft == resource.RLIM_INFINITY or soft > ADDRESS_SPACE_MIB * 1024 ** 2:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (address-space limit expected)")
    if not sa.SHA256_RE.fullmatch(args.detector_sha256 or ""):
        raise SystemExit("refused: --detector-sha256 must be a full lowercase sha256")
    census = json.loads((ROOT / CENSUS).read_text())
    recordings = args.recordings.split(",")
    if (args.mode == "full") != (args.stage == "full"):
        raise SystemExit("refused: --mode full goes with --stage full only")
    if recordings != stage_recordings(args.stage, args.subject):
        raise SystemExit("refused: --recordings are not the reviewed sample or the subject's T03 records")
    if args.mode == "full":
        install_full_mode(pilot_record_path())
    for r in recordings:
        um21.check_recording(r)
    if pilot._mem_available() < MIN_AVAILABLE_BYTES:
        raise MemoryError("less than 2 GiB available; not started")
    records = t03_records()
    c03 = json.loads((ROOT / C03).read_text())["source"]
    source = ROOT / SOURCE
    st = source.stat()
    if (st.st_size, st.st_mtime_ns) != (c03["bytes"], c03["mtime_ns"]):
        raise ValueError("Streaming.mat size/mtime differ from the UM21-C03 record")
    out = (ROOT / args.output_root).resolve()
    out.mkdir(parents=True, exist_ok=False)
    started = time.time()
    (out / "inputs").mkdir()
    backlog_bytes = sa.BACKLOG_PATH.read_bytes()
    snapshot = out / "inputs" / "backlog_snapshot.json"
    with open(snapshot, "xb") as fh:
        fh.write(backlog_bytes)
    import h5py
    summaries, groups_all, logs, failures, slots_all, facts_all = [], [], [], {}, {}, {}
    with h5py.File(source, "r", rdcc_nbytes=1024 ** 2) as handle:
        for rec in recordings:
            if pilot._mem_available() < MIN_AVAILABLE_BYTES:
                raise MemoryError("less than 2 GiB available; stopped at a recording boundary")
            summ, groups, lg, fbg, slots, facts = process_recording(handle, rec, records[rec], args.detector_sha256,
                                                                    out, snapshot, mode=args.mode)
            summaries.append(summ), groups_all.extend(groups), logs.extend(lg)
            failures.update(fbg), slots_all.update(slots)
            facts_all[rec] = facts
            print(f"{rec} done, mapped {summ['mapped']}/{summ['t03_observations']}, peak RSS {_peak_rss_mib():.0f} MiB",
                  flush=True)
            if _peak_rss_mib() > RSS_CAP_MIB:
                raise MemoryError(f"peak RSS {_peak_rss_mib():.0f} MiB above {RSS_CAP_MIB}; stopped")
    after = source.stat()
    source_unchanged = (after.st_size, after.st_mtime_ns) == (st.st_size, st.st_mtime_ns)
    cross = pilot.explain_cross_group(sa.cross_group_review(logs), logs, slots_all)
    unexplained = [c for c in cross if not c["explained"]]
    inits = [m for m in PACKAGE_INITS if m in sys.modules]
    rec_findings = {s["recording"]: s["findings"] for s in summaries if s["findings"]}
    failed = {g: v for g, v in failures.items() if v}
    gate_missing = [g["group_id"] for g in groups_all if args.mode == "full" and not g["pilot_facts"]]
    passed = not failed and not rec_findings and source_unchanged and not unexplained and not inits and not gate_missing
    summary = {
        "task_id": TASK_ID, "stage": args.stage, "mode": args.mode, "scientific_approval": False,
        "automated_outcome": "passed" if passed else "failed",
        "note": "automated checks only; independent review follows",
        "detector_sha256": args.detector_sha256, "bound_build": sa.bound_build(),
        "code_sha256": {pilot.ADAPTER: sha256_file(ROOT / pilot.ADAPTER), pilot.RUNNER: sha256_file(ROOT / pilot.RUNNER),
                        RUNNER: sha256_file(ROOT / RUNNER)},
        "recordings": recordings, "backlog_snapshot_sha256": hashlib.sha256(backlog_bytes).hexdigest(),
        "mapping_rule": "exact observation id = hook unit id; unmapped observations unsigned and unassessed",
        "totals": {"t03_observations": sum(s["t03_observations"] for s in summaries),
                   "mapped": sum(s["mapped"] for s in summaries), "unmapped": sum(s["unmapped"] for s in summaries)},
        "pilot_gate": ({"record": PILOT_RECORD, "record_sha256": PILOT_RECORD_SHA256, "receipt": PILOT_RECEIPT,
                        "receipt_sha256": PILOT_RECEIPT_SHA256, "groups_without_hook_pilot_facts": gate_missing}
                       if args.mode == "full" else None),
        "rule_flags": {s["recording"]: s["rule_flags"] for s in summaries if s["rule_flags"]},
        "records": summaries, "group_failures": failed, "record_findings": rec_findings,
        "cross_group_review": cross, "unexplained_cross_group_items": len(unexplained),
        "package_inits_imported": inits, "source_unchanged_after_run": source_unchanged,
        "recording_facts": facts_all, "groups": groups_all,
        "resources": {"peak_rss_mib": round(_peak_rss_mib(), 1), "rss_cap_mib": RSS_CAP_MIB,
                      "rlimit_as_bytes": list(resource.getrlimit(resource.RLIMIT_AS)), "nice": os.nice(0),
                      "wall_seconds": round(time.time() - started, 1)},
    }
    sa.write_json_exclusive(out / "t04_summary.json", sa._finite(summary))
    print(json.dumps({"automated_outcome": summary["automated_outcome"], "totals": summary["totals"],
                      "peak_rss_mib": summary["resources"]["peak_rss_mib"]}))
    return 0 if passed else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="step", required=True)
    pp = sub.add_parser("plan", help="write and validate the plan-only job spec (no data read)")
    pp.add_argument("--stage", choices=("a", "b", "full"), required=True)
    pp.add_argument("--subject")
    pp.add_argument("--spec-out")
    pr = sub.add_parser("run", help="the job; only through contributor_tools.guarded_launcher")
    pr.add_argument("--output-root", required=True)
    pr.add_argument("--detector-sha256", required=True)
    pr.add_argument("--recordings", required=True)
    pr.add_argument("--stage", choices=("a", "b", "full"), required=True)
    pr.add_argument("--subject")
    pr.add_argument("--mode", choices=("pilot", "full"), default="pilot")
    args = p.parse_args(argv)
    if args.step == "plan":
        plan(args.stage, args.spec_out, args.subject)
        return 0
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
