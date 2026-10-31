#!/usr/bin/env python3
"""CORE-11-P-UM21: bound-build sign-application pilot on UMich 2021 treadmill recordings.

Two steps:

``plan --spec-out PATH``
    Writes a plan-only guarded-launcher job spec and validates it in-process with
    ``guarded_launcher.validate_spec``. Reads no research data: the recording list comes from the
    committed UM21-T02 clock census, the source sha256 from the UM21-C03 record. Launches nothing.

``run ...``
    The job. Start it only through ``python3 -m contributor_tools.guarded_launcher run SPEC.json``; it
    refuses to start without the launcher's niceness and address-space limit. One recording at a time
    from Streaming.mat (h5py, read-only, 1 MiB chunk cache), through
    contributor_tools/adapters/um21_sign_adapter.py: hook first, then segment angles and velocities from
    the published channels. Writes only under the new --output-root (created here; it must not exist):
    per group the sign-application log and review (exclusive create), the derivation logs, the hook
    outputs and derived arrays (.npz), then reloads them, undoes every sign against the logged input
    hashes and checks each derivation against the log. Ends with pilot_summary.json; exit status 0 only
    when every automated check passes.

Seeded sample (v2 onward): AB04/i0 (the logged pelvis correction, D-UM21-P01-1 = C), then from one
random.Random(SEED): one power layout-2 recording from the bound UM21-C03 layout list (in scope), then
N_RANDOM of the other in-scope recordings. In scope: the 50 census recordings minus the six excluded by
D-UM21-T02-1 = A. The pilot record (docs/quality/audits) is written after the run and its independent
verification, from the receipt and pilot_summary.json, by the ``record`` step (exclusive create).

The job imports the adapter and the hook from their files, so no package __init__ runs; the summary
records any that did, and the pilot then fails.

Audited truth for the sign check (rule B, target = sign x corrected source; UM21-C03 and the CORE-04 UM21
pilot): pelvis -1, hip, knee, ankle angles +1, hip, knee, ankle moments +1; power slot 1 (layout 1) -1,
slot 3 (layout 2) +1. scientific_approval is false.
"""
from __future__ import annotations

import os
for _key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_key, "1")
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import resource
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_adapter():
    """The adapter from its file (it loads the hook from its file): no package __init__ runs in the job, so
    the executed code is the bound files. Reuses an already imported module only if it is the same file."""
    name, path = "contributor_tools.adapters.um21_sign_adapter", ROOT / "contributor_tools/adapters/um21_sign_adapter.py"
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
    if Path(module.__file__).resolve() != path.resolve():
        raise ImportError(f"{name} already imported from {module.__file__}")
    return module


um21 = _load_adapter()
sa = um21.sa
PACKAGE_INITS = ("contributor_tools", "contributor_tools.common", "contributor_tools.adapters")

TASK_ID = "CORE-11-P-UM21"
RUNNER = "contributor_tools/run_core11_um21_pilot.py"
ADAPTER = "contributor_tools/adapters/um21_sign_adapter.py"
CENSUS = "docs/quality/audits/um21-t02-clock-census.json"
C03 = "docs/quality/audits/um21-c03-conventions.json"
SOURCE = "contributor_tools/conversion_scripts/Umich_2021/Streaming.mat"
# v3 (pre-launch review round 2, R3-R5): v1 (no layout-2 recording) and v2 (runner changed since) were never
# committed or launched and were deleted; their paths are not reused and plan refuses while either exists.
VERSION = "v3"
JOB_ID = f"{TASK_ID}-pilot-{VERSION}"
SPEC = f"docs/quality/audits/core11-p-um21-pilot-spec-{VERSION}.json"
OUTPUT_ROOT = f"converted_datasets/reconversion_v2/core11_p_um21_pilot_{VERSION}"
RECEIPT = f"docs/quality/audits/core11-p-um21-launcher-receipt-{VERSION}.json"
RECORD = f"docs/quality/audits/core11-p-um21-pilot-record-{VERSION}.json"
SUPERSEDED = {"docs/quality/audits/core11-p-um21-pilot-spec.json":
              "357721598a2e0bb3687bcbc7d289be7c0b83e5812ea5f4040d9faf68eda0fb3a",
              "docs/quality/audits/core11-p-um21-pilot-spec-v2.json":
              "5b0c5300e999f888c950eedcadb9ddec7fdcda3df482781a578d6a9057d18c24"}
LOG_KEYS = ("dataset", "group_id", "leg", "channels", "exceptions_applied", "recording_exceptions")
SEED = 20261102
N_RANDOM = 5
REQUIRED = ("AB04/i0",)  # the logged per-recording pelvis correction must be exercised
RSS_CAP_MIB = 300.0
ADDRESS_SPACE_MIB = 768
MIN_AVAILABLE_BYTES = 2 * 1024 ** 3
TRUTH = {"pelvis_tilt": -1, "hip_angle": 1, "knee_angle": 1, "ankle_angle": 1,
         "hip_moment": 1, "knee_moment": 1, "ankle_moment": 1}
TRUTH_POWER = {1: -1, 3: 1}  # by source slot (UM21-C03 kinetic_layout)
CORRECTION_ID = "UM21-P01-AB04-i0-pelvis"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# ---------------------------------------------------------------- sample and spec (no research data)
def in_scope_recordings(census):
    """Census recordings minus the adapter's exclusions; the census's failed clock checks must be exactly
    the excluded set (a drift between the decision and the census refuses)."""
    records = sorted(f"{r['subject']}/{r['condition']}" for r in census["records"])
    failed = {f"{r['subject']}/{r['condition']}" for r in census["records"] if not r["alignment"]["passed"]}
    if len(records) != 50 or len(set(records)) != 50:
        raise ValueError(f"census lists {len(records)} recordings, expected 50 distinct")
    if failed != set(um21.EXCLUDED):
        raise ValueError(f"census clock failures {sorted(failed)} differ from the adapter exclusions "
                         f"{sorted(um21.EXCLUDED)}")
    return [r for r in records if r not in um21.EXCLUDED]


def layout_2_candidates(census, c03_path=None):
    """In-scope power layout-2 recordings from the bound UM21-C03 record (not hard-coded), minus REQUIRED."""
    layout = um21.power_layout(c03_path or ROOT / C03)
    scope = set(in_scope_recordings(census))
    return sorted(r for r in layout["layout_2"] if r in scope and r not in REQUIRED)


def pilot_sample(census, seed=SEED, n_random=N_RANDOM):
    """REQUIRED, then one layout-2 recording, then n_random others, all drawn from one random.Random(seed)."""
    rng = random.Random(seed)
    layout2 = rng.choice(layout_2_candidates(census))
    pool = [r for r in in_scope_recordings(census) if r not in REQUIRED and r != layout2]
    return list(REQUIRED) + [layout2] + rng.sample(pool, n_random)


def bindings():
    """Bound build (sign_application.bound_build) + adapter, runner, census, C03 record and the source
    file at its recorded sha256 (the launcher hashes it before and after the run)."""
    c03 = json.loads((ROOT / C03).read_text())
    return {**sa.bound_build(), ADAPTER: sha256_file(ROOT / ADAPTER), RUNNER: sha256_file(ROOT / RUNNER),
            CENSUS: sha256_file(ROOT / CENSUS), C03: sha256_file(ROOT / C03),
            SOURCE: c03["source"]["sha256_recorded"]}


def build_spec():
    census = json.loads((ROOT / CENSUS).read_text())
    recordings = pilot_sample(census)
    detector = sa.file_sha256(sa.DETECTOR_PATH)
    return {
        "job_id": JOB_ID,
        "command": ["python3", RUNNER, "run", "--output-root", OUTPUT_ROOT, "--detector-sha256", detector,
                    "--recordings", ",".join(recordings), "--seed", str(SEED)],
        "cwd": str(ROOT),
        "output_root": OUTPUT_ROOT,
        "receipt_path": RECEIPT,
        "bindings": bindings(),
        "timeout_seconds": 3600, "kill_after_seconds": 30, "poll_seconds": 15,
        "startup_memory_mib": {"linux": 3584, "windows": 2816},
        "runtime_memory_mib": {"linux": 2048, "windows": 2048},
        "expected_output_names": ["pilot_summary.json"],
        "address_space_mib": ADDRESS_SPACE_MIB,
    }


def plan(spec_out):
    from contributor_tools.guarded_launcher import validate_spec
    for old in SUPERSEDED:
        if (ROOT / old).exists():
            raise SystemExit(f"refused: superseded spec {old} still exists; delete it so it cannot be launched")
    spec = build_spec()
    validate_spec(spec)
    path = Path(spec_out)
    with path.open("x", encoding="utf-8") as f:  # never overwrite a spec
        f.write(json.dumps(spec, indent=1) + "\n")
    print(json.dumps({"spec": str(path), "sha256": sha256_file(path),
                      "recordings": spec["command"][spec["command"].index("--recordings") + 1]}))


# ---------------------------------------------------------------- pilot checks (one group)
def expected_sign(channel, power_slots):
    if channel.endswith("_power"):
        return TRUTH_POWER.get(power_slots.get(channel.split("_")[0]))
    return TRUTH.get(channel)


def check_group(result):
    """Automated pilot checks for one LegResult. Returns {check: [findings]}; empty lists pass.
    'not_checked' lists published channels without an audited truth (reported, not a failure)."""
    log = result.application.log
    ch = log["channels"]
    slots = result.adapter_log["power_slots"]
    f = {"wrong_published_sign": [], "unexplained_hold": [], "unexplained_review": [],
         "segment_not_from_published": [], "velocity_not_from_published": [], "correction": [],
         "forbidden_hook_input": [], "not_checked": []}
    for k, c in ch.items():
        if c["publication"] == "publish":
            want = expected_sign(k, slots)
            if want is None:
                f["not_checked"].append(f"{k}: no audited truth")
            elif c["sign_vs_corrected_source"] != want:
                f["wrong_published_sign"].append(f"{k}: published {c['sign_vs_corrected_source']:+d}, truth {want:+d}")
        elif not (c.get("hold_reason") or "").strip():
            f["unexplained_hold"].append(k)
    for item in result.application.review:
        if item["kind"] in ("guard_refused", "conflict") and not (item.get("reason") or "").strip():
            f["unexplained_review"].append(f"{item['kind']} {item['channel']}")
    f["forbidden_hook_input"] = [k for k in ch if k in sa.SEGMENT_CHANNELS or k.endswith(sa.VELOCITY_SUFFIX)]
    available = {k: c["output_sha256"] for k, c in ch.items() if c["publication"] == "publish"}
    for seg, d in result.segment_log["derived"].items():
        for name, h in d["inputs_sha256"].items():
            if available.get(name) != h:
                f["segment_not_from_published"].append(f"{seg}: input {name}")
        if sa.array_sha256(result.segments[seg]) != d["output_sha256"]:
            f["segment_not_from_published"].append(f"{seg}: output hash")
        available[seg] = d["output_sha256"]
    for vel, d in result.velocity_log["derived"].items():
        if available.get(d["from"]) != d["input_sha256"]:
            f["velocity_not_from_published"].append(vel)
    applied = log["corrections_applied"]
    if result.recording == "AB04/i0":
        p = ch.get("pelvis_tilt", {})
        ok = (len(applied) == 1 and applied[0]["id"] == CORRECTION_ID and applied[0]["channel"] == "pelvis_tilt"
              and applied[0]["decision"] == {"id": "D-UM21-P01-1", "answer": "C"}
              and p.get("publication") == "publish" and p.get("multiplier") == 1)
        if not ok:
            f["correction"].append("AB04/i0 pelvis correction not applied and logged as recorded")
        if not set(sa.SEGMENT_CHANNELS) <= set(result.segments):
            f["correction"].append("AB04/i0 thigh, shank and foot not all derived from the corrected tilt")
    elif applied:
        f["correction"].append(f"unexpected correction in {result.recording}: {applied}")
    return f


def benign_hold(channel, c, log, slots):
    """(ok, why) for one held group, from structured log fields only (never the reason text). A hold is benign
    when it comes from a per-recording exception or a not-released channel, or when the detector did not
    report a conflict and its sign is empty or equals the audited truth (powers by their slot). A detector
    that opposes the truth or reports a conflict is a disagreement: it is how the AB04/i0 reversal was found."""
    if any(x.get("channel") == channel for x in log.get("exceptions_applied") or []):
        return True, "per-recording exception"
    if any(channel in (x.get("not_released") or {}) for x in log.get("recording_exceptions") or []):
        return True, "not released for this recording"
    if c.get("verdict") == "conflict":
        return False, "detector reports a conflict"
    want, sign = expected_sign(channel, slots), c.get("detector_sign")
    if sign is None:
        return True, f"detector gave no sign (verdict {c.get('verdict')})"
    if want is not None and sign == want:
        return True, f"detector sign {sign:+d} equals the audited truth (verdict {c.get('verdict')})"
    return False, f"detector {c.get('verdict')} {sign:+d} against the audited truth {want}"


def explain_cross_group(items, logs, slots_by_group):
    """Mark each cross_group_review item explained or unexplained (an unexplained item fails the pilot).

    logs: the groups' sign-application logs (LOG_KEYS); slots_by_group: group_id -> power slots. Signs that
    differ between groups are explained only for a power channel whose published groups use different source
    slots, each published with its slot's audited truth. A channel held in some groups and published in others
    is explained only when every published group has the audited truth and every held group is a benign hold
    (benign_hold, structured fields only). Anything else is unexplained."""
    by_key = {f"{lg['group_id']} {lg['leg']}": lg for lg in logs}
    out = []
    for it in items:
        ch = it["channel"]
        rows = {k: lg["channels"][ch] for k, lg in by_key.items() if ch in lg["channels"]}
        pub = {k: c for k, c in rows.items() if c["publication"] == "publish"}
        held = {k: c for k, c in rows.items() if c["publication"] == "hold"}
        slots_of = {k: slots_by_group[by_key[k]["group_id"]] for k in rows}
        truth_ok = all(c["sign_vs_corrected_source"] == expected_sign(ch, slots_of[k]) for k, c in pub.items())
        explanations, unexplained = [], []
        if not truth_ok:
            unexplained.append("a published group does not have the audited sign")
        if len({c["sign_vs_corrected_source"] for c in pub.values()}) > 1:
            slots = {slots_of[k].get(ch.split("_")[0]) for k in pub}
            if ch.endswith("_power") and len(slots) > 1 and truth_ok:
                explanations.append(f"power slots differ ({sorted(slots)}); each published group has its slot's "
                                    "audited sign")
            else:
                unexplained.append("published signs differ without a power-slot difference matching the truth")
        for k, c in held.items():
            ok, why = benign_hold(ch, c, by_key[k], slots_of[k])
            (explanations if ok else unexplained).append(f"held in {k}: {why}")
        out.append({**it, "explained": not unexplained and bool(explanations), "explanations": explanations,
                    "unexplained": unexplained or ([] if explanations else ["no explanation found"])})
    return out


# ---------------------------------------------------------------- pilot record (after the launched run)
def build_record(receipt_path, summary_path, repo_root=ROOT, spec_path=None):
    """The pilot record for check_pilot_record: dataset, outcome, pilot_task, launcher_receipt {path, sha256}
    and bindings identical to the receipt's spec bindings. outcome is 'passed' only when the receipt is a
    clean completed run of this job with every binding matching before and after, its output hashes include
    this pilot_summary.json, and the summary's automated outcome passed. Independent verification and the
    backlog citations remain separate requirements of the full-run gate. The receipt must have run the
    reviewed spec file (spec_path, default SPEC): its spec_sha256 equals that file's sha256 and its spec
    bindings equal the file's bindings."""
    repo_root = Path(repo_root).resolve()
    receipt_path = Path(receipt_path).resolve()
    rdata = receipt_path.read_bytes()
    r = json.loads(rdata)
    sdata = Path(summary_path).read_bytes()
    summary = json.loads(sdata)
    spec = r.get("spec") or {}
    bindings = spec.get("bindings") or {}
    problems = []
    if r.get("status") != "completed" or r.get("clean_success") is not True:
        problems.append("receipt is not a clean completed run")
    spec_path = Path(spec_path or repo_root / SPEC)
    try:
        spec_bytes = spec_path.read_bytes()
    except OSError as exc:
        spec_bytes = None
        problems.append(f"reviewed spec unreadable: {type(exc).__name__}")
    if spec_bytes is not None:
        if r.get("spec_sha256") != hashlib.sha256(spec_bytes).hexdigest():
            problems.append("receipt spec_sha256 is not the reviewed spec file's sha256")
        if json.loads(spec_bytes).get("bindings") != bindings:
            problems.append("receipt spec bindings differ from the reviewed spec file's bindings")
    if spec.get("job_id") != JOB_ID:
        problems.append(f"receipt job_id {spec.get('job_id')!r} is not {JOB_ID!r}")
    if Path(str(spec.get("cwd"))).resolve() != repo_root:
        problems.append("receipt cwd is not this repository")
    if not receipt_path.is_relative_to(repo_root):
        problems.append("receipt is outside this repository")
    for when in ("bindings_before", "bindings_after"):
        b = r.get(when) or {}
        if set(b) != set(bindings) or not all(v.get("matches") for v in b.values()):
            problems.append(f"{when}: not every binding matched")
    if any(bindings.get(k) != v for k, v in summary.get("bound_build", {}).items()) or not summary.get("bound_build"):
        problems.append("the summary's bound build is not bound by the receipt")
    sha_summary = hashlib.sha256(sdata).hexdigest()
    if not any(o.get("path") == "pilot_summary.json" and o.get("sha256") == sha_summary for o in r.get("outputs") or []):
        problems.append("pilot_summary.json is not among the receipt's hashed outputs")
    if summary.get("automated_outcome") != "passed":
        problems.append(f"automated outcome {summary.get('automated_outcome')!r}")
    return {"dataset": um21.DATASET, "outcome": "failed" if problems else "passed", "pilot_task": TASK_ID,
            "launcher_receipt": {"path": str(receipt_path.relative_to(repo_root)) if receipt_path.is_relative_to(repo_root)
                                 else str(receipt_path), "sha256": hashlib.sha256(rdata).hexdigest()},
            "bindings": dict(bindings), "job_id": spec.get("job_id"), "scientific_approval": False,
            "spec": {"path": str(spec_path.relative_to(repo_root)) if spec_path.resolve().is_relative_to(repo_root)
                     else str(spec_path), "sha256": r.get("spec_sha256")},
            "pilot_summary_sha256": sha_summary, "recordings": summary.get("recordings"),
            "problems": problems,
            "note": "The full-run gate also needs this record and the receipt committed, the pilot task done after "
                    "independent verification, and its backlog record citing this path, its sha256 and the "
                    "receipt sha256."}


def write_record(receipt_path, summary_path, out, repo_root=ROOT, spec_path=None):
    record = build_record(receipt_path, summary_path, repo_root, spec_path)
    digest = sa.write_json_exclusive(out, record)  # never overwrites
    return record, digest


# ---------------------------------------------------------------- the job
def _peak_rss_mib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def _mem_available():
    line = next(s for s in Path("/proc/meminfo").read_text().splitlines() if s.startswith("MemAvailable:"))
    return int(line.split()[1]) * 1024


def _save_npz_exclusive(path, arrays):
    with open(path, "xb") as fh:
        np.savez(fh, **arrays)
    return sha256_file(path)


def _write_group(out, result):
    """Write one group's outputs (exclusive), reload them, undo and re-check. Returns (manifest, findings)."""
    gdir = out / "groups" / result.group_id.replace("/", "_").replace(":", "_")
    gdir.mkdir(parents=True, exist_ok=False)
    app = result.application
    files = {"sign_application.json": sa.write_json_exclusive(gdir / "sign_application.json", app.log),
             "sign_review.json": sa.write_json_exclusive(gdir / "sign_review.json", app.review),
             "derivations.json": sa.write_json_exclusive(gdir / "derivations.json", sa._finite({
                 "segment_angles": result.segment_log, "velocities": result.velocity_log,
                 "adapter": result.adapter_log})),
             # hook outputs under logical detector names: held channels stay in the source convention
             "hook_outputs.npz": _save_npz_exclusive(gdir / "hook_outputs.npz", app.channels),
             "derived.npz": _save_npz_exclusive(gdir / "derived.npz", {**result.segments, **result.velocities})}
    findings = []
    with np.load(gdir / "hook_outputs.npz", allow_pickle=False) as z:
        loaded = {k: z[k] for k in z.files}
    restored = sa.undo_sign_application(loaded, gdir / "sign_application.json",
                                        expected_log_sha256=files["sign_application.json"])
    for k, a in restored.items():
        if sa.array_sha256(a) != result.adapter_log["inputs_sha256"][k]:
            findings.append(f"undo of {k} does not reproduce the adapter input")
    with np.load(gdir / "derived.npz", allow_pickle=False) as z:
        derived = {k: sa.array_sha256(z[k]) for k in z.files}
    logged = {**{k: d["output_sha256"] for k, d in result.segment_log["derived"].items()},
              **{k: d["output_sha256"] for k, d in result.velocity_log["derived"].items()}}
    if derived != logged:
        findings.append("written derived arrays differ from the derivation logs")
    return {"dir": str(gdir.relative_to(out)), "sha256": files}, findings


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
    if recordings != pilot_sample(census, seed=args.seed):
        raise SystemExit("refused: --recordings is not the seeded pilot sample")
    for r in recordings:
        um21.check_recording(r)  # refuses an excluded id before any data access
    if _mem_available() < MIN_AVAILABLE_BYTES:
        raise MemoryError("less than 2 GiB available; not started")
    c03 = json.loads((ROOT / C03).read_text())["source"]
    source = ROOT / SOURCE
    st = source.stat()
    if (st.st_size, st.st_mtime_ns) != (c03["bytes"], c03["mtime_ns"]):
        raise ValueError("Streaming.mat size/mtime differ from the UM21-C03 record")
    out = (ROOT / args.output_root).resolve()
    out.mkdir(parents=True, exist_ok=False)
    started = time.time()
    (out / "inputs").mkdir()
    backlog_bytes = sa.BACKLOG_PATH.read_bytes()  # one snapshot: every group sees the same backlog
    snapshot = out / "inputs" / "backlog_snapshot.json"
    with open(snapshot, "xb") as fh:
        fh.write(backlog_bytes)
    import h5py
    groups, logs, failures, facts_all = [], [], {}, {}
    with h5py.File(source, "r", rdcc_nbytes=1024 ** 2) as handle:
        for rec in recordings:
            if _mem_available() < MIN_AVAILABLE_BYTES:
                raise MemoryError("less than 2 GiB available; stopped at a recording boundary")
            facts, results = um21.convert_recording(handle, rec, args.detector_sha256, backlog_path=snapshot)
            facts_all[rec] = facts
            for res in results:
                manifest, written = _write_group(out, res)
                found = check_group(res)
                found["written_outputs"] = written
                log = res.application.log
                groups.append({"group_id": res.group_id, "units": len(res.unit_ids), **manifest,
                               "counts": log["counts"], "power_slots": res.adapter_log["power_slots"],
                               "published": res.adapter_log["published"], "held": res.adapter_log["held"],
                               "derived": res.adapter_log["derived_segments"] + res.adapter_log["derived_velocities"],
                               "corrections_applied": log["corrections_applied"],
                               "findings": found})
                failures[res.group_id] = {k: v for k, v in found.items() if v and k != "not_checked"}
                logs.append({k: log[k] for k in LOG_KEYS})
            del results
            print(f"{rec} done, peak RSS {_peak_rss_mib():.0f} MiB", flush=True)
            if _peak_rss_mib() > RSS_CAP_MIB:
                raise MemoryError(f"peak RSS {_peak_rss_mib():.0f} MiB above {RSS_CAP_MIB}; stopped")
    after = source.stat()
    source_unchanged = (after.st_size, after.st_mtime_ns) == (st.st_size, st.st_mtime_ns)
    slots_by_group = {g["group_id"]: g["power_slots"] for g in groups}
    cross = explain_cross_group(sa.cross_group_review(logs), logs, slots_by_group)
    unexplained = [c for c in cross if not c["explained"]]
    inits = [m for m in PACKAGE_INITS if m in sys.modules]  # unbound package code that ran in the job
    failed = {g: v for g, v in failures.items() if v}
    passed = not failed and source_unchanged and not unexplained and not inits
    summary = {
        "task_id": TASK_ID, "dataset": um21.DATASET, "scientific_approval": False, "mode": "pilot",
        "automated_outcome": "passed" if passed else "failed",
        "note": "automated checks only; the pilot record is written after independent verification",
        "detector_sha256": args.detector_sha256, "bound_build": sa.bound_build(),
        "code_sha256": {ADAPTER: sha256_file(ROOT / ADAPTER), RUNNER: sha256_file(ROOT / RUNNER)},
        "seed": args.seed, "recordings": recordings, "required": list(REQUIRED),
        "exclusions": {"decision": um21.EXCLUSION_DECISION, "excluded": um21.EXCLUDED},
        "backlog_snapshot_sha256": hashlib.sha256(backlog_bytes).hexdigest(),
        "source": {"path": SOURCE, "bytes": st.st_size, "mtime_ns": st.st_mtime_ns,
                   "sha256_recorded": c03["sha256_recorded"], "unchanged_after_run": source_unchanged},
        "truth": {"channels": TRUTH, "power_by_slot": {str(k): v for k, v in TRUTH_POWER.items()},
                  "basis": "UM21-C03 per-channel audit and the CORE-04 UM21 pilot (rule B, target = sign x "
                           "corrected source)"},
        "checks": ["no published sign contradicts the audited truth", "every hold, conflict and guard "
                   "refusal carries a logged reason", "segments derived from published channels, velocities "
                   "from published or derived angles (hash-linked)", "AB04/i0 correction applied and logged; "
                   "no other recording corrected", "no segment angle or velocity passed to the hook",
                   "undo of every written hook output reproduces the adapter input hash", "written derived "
                   "arrays match the derivation logs", "source size and mtime unchanged",
                   "power slot of every joint equals the UM21-C03 layout record (else the recording fails)",
                   "every cross-group review item explained (power slots differ; or held where the detector did not "
                   "oppose the truth nor report a conflict, or by a per-recording exception, with every published "
                   "sign matching the truth)", "no package __init__ ran in the job"],
        "failures": failed, "cross_group_review": cross, "unexplained_cross_group_items": len(unexplained),
        "package_inits_imported": inits, "recording_facts": facts_all, "groups": groups,
        "resources": {"peak_rss_mib": round(_peak_rss_mib(), 1), "rss_cap_mib": RSS_CAP_MIB,
                      "rlimit_as_bytes": list(resource.getrlimit(resource.RLIMIT_AS)), "nice": os.nice(0),
                      "wall_seconds": round(time.time() - started, 1)},
    }
    sa.write_json_exclusive(out / "pilot_summary.json", sa._finite(summary))
    print(json.dumps({"automated_outcome": summary["automated_outcome"], "groups": len(groups),
                      "peak_rss_mib": summary["resources"]["peak_rss_mib"]}))
    return 0 if passed else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="step", required=True)
    pp = sub.add_parser("plan", help="write and validate the plan-only job spec (no data read)")
    pp.add_argument("--spec-out", default=str(ROOT / SPEC))
    pc = sub.add_parser("record", help="after the launched run: write the pilot record (exclusive)")
    pc.add_argument("--receipt", default=str(ROOT / RECEIPT))
    pc.add_argument("--summary", default=str(ROOT / OUTPUT_ROOT / "pilot_summary.json"))
    pc.add_argument("--out", default=str(ROOT / RECORD))
    pc.add_argument("--spec", default=str(ROOT / SPEC))
    pr = sub.add_parser("run", help="the job; only through contributor_tools.guarded_launcher")
    pr.add_argument("--output-root", required=True)
    pr.add_argument("--detector-sha256", required=True)
    pr.add_argument("--recordings", required=True)
    pr.add_argument("--seed", type=int, required=True)
    args = p.parse_args(argv)
    if args.step == "plan":
        plan(args.spec_out)
        return 0
    if args.step == "record":
        record, digest = write_record(args.receipt, args.summary, args.out, spec_path=args.spec)
        print(json.dumps({"record": args.out, "sha256": digest, "outcome": record["outcome"],
                          "problems": record["problems"]}))
        return 0 if record["outcome"] == "passed" else 1
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
