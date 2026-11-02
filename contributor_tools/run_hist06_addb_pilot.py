#!/usr/bin/env python3
"""HIST-06: guarded pilot of the AddBiomechanics mapping adapter (Falisse, Tan running, Tan walking).

``plan --spec-out PATH``
    Writes a plan-only guarded-launcher job spec and validates it with ``guarded_launcher.validate_spec``.
    Reads no frame data: participants come from the HIST-05 output folder names, their file hashes from
    each conversion.json (frames.parquet, dynamics_model.osim) and from hashing conversion.json itself.
    Launches nothing.

``run ...``
    The job. Start it only through ``python3 -m contributor_tools.guarded_launcher run SPEC.json``; it
    refuses without the launcher's niceness and address-space limit. One participant and one trial at a
    time (bounded columns, the trial's row groups only), through
    contributor_tools/adapters/addbiomechanics_sign_adapter.py: model checks, task rule, rule-B frame, hook,
    then segments and velocities from published channels. Writes only under the new --output-root: per
    participant mapped_frames.parquet (both reference legs), trial_logs.json and sign_applications.json
    (exclusive create), then pilot_summary.json. Exit 0 only when every automated check passes.

Sample: from one random.Random(SEED), one participant per study (sorted folder names), plus the Tan
running s7 hip_calibration trial (the known MAP-TAN-TASK case) when s7 is not drawn. The audited-sign
table must hold the FA16, TA21 and TA22 dataset keys (sign_application refuses a dataset it does not
list); the run step checks that before reading any frame. Truth for the automated sign check: every hook
channel is +1 against the source (model definition, HIST-06 forward-kinematics probe; the pelvis input is
the rule-B pitch by construction). scientific_approval is false.
"""
from __future__ import annotations

import os
for _key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "ARROW_NUM_THREADS"):
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
    name = "contributor_tools.adapters.addbiomechanics_sign_adapter"
    path = ROOT / "contributor_tools/adapters/addbiomechanics_sign_adapter.py"
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


addb = _load_adapter()
sa = addb.sa
PACKAGE_INITS = ("contributor_tools", "contributor_tools.common", "contributor_tools.adapters")

TASK_ID = "HIST-06"
RUNNER = "contributor_tools/run_hist06_addb_pilot.py"
ADAPTER = "contributor_tools/adapters/addbiomechanics_sign_adapter.py"
PROBE = "docs/quality/audits/hist06-addb-mapping-probe.json"
DATA_ROOT = Path("/mnt/s/locomotion_data/addbiomechanics_hist04")
VERSION = "v1"
JOB_ID = f"{TASK_ID}-addb-mapping-pilot-{VERSION}"
SPEC = f"docs/quality/audits/hist06-addb-pilot-spec-{VERSION}.json"
OUTPUT_ROOT = f"converted_datasets/reconversion_v2/hist06_addb_mapping_pilot_{VERSION}"
RECEIPT = f"docs/quality/audits/hist06-addb-launcher-receipt-{VERSION}.json"
SEED = 20261106
REQUIRED_TRIAL = ("ta21", "s7", "hip_calibration")
RSS_CAP_MIB = 300.0
ADDRESS_SPACE_MIB = 768
MIN_AVAILABLE_BYTES = 2 * 1024 ** 3
TRUTH = {"pelvis_tilt": 1, "hip_angle": 1, "knee_angle": 1, "ankle_angle": 1,
         "hip_moment": 1, "knee_moment": 1, "ankle_moment": 1}
LOG_KEYS = ("dataset", "group_id", "leg", "channels", "exceptions_applied", "recording_exceptions")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# ---------------------------------------------------------------- sample and spec (no frame data)
def participants(root=DATA_ROOT):
    return {slug: sorted(p.parent.name for p in (root / slug).glob("*/conversion.json")) for slug in addb.STUDIES}


def pilot_sample(found, seed=SEED):
    rng = random.Random(seed)
    picks = {slug: rng.choice(found[slug]) for slug in ("fa16", "ta21", "ta22")}
    extra = [] if picks["ta21"] == REQUIRED_TRIAL[1] else [list(REQUIRED_TRIAL)]
    return picks, extra


def participant_files(slug, subject, root=DATA_ROOT):
    d = root / slug / subject
    conv = json.loads((d / "conversion.json").read_text())
    return {str(d / "conversion.json"): sha256_file(d / "conversion.json"),
            str(d / "frames.parquet"): conv["frames_parquet_sha256"],
            str(d / "dynamics_model.osim"): conv["dynamics_model_sha256"]}


def bindings(picks, extra, root=DATA_ROOT):
    b = {**sa.bound_build(), ADAPTER: sha256_file(ROOT / ADAPTER), RUNNER: sha256_file(ROOT / RUNNER),
         PROBE: sha256_file(ROOT / PROBE)}
    for slug, subject in list(picks.items()) + [(e[0], e[1]) for e in extra]:
        b.update(participant_files(slug, subject, root))
    return b


def build_spec(root=DATA_ROOT):
    picks, extra = pilot_sample(participants(root))
    detector = sa.file_sha256(sa.DETECTOR_PATH)
    sample = ",".join(f"{s}/{p}" for s, p in picks.items())
    cmd = ["python3", RUNNER, "run", "--output-root", OUTPUT_ROOT, "--detector-sha256", detector,
           "--participants", sample, "--seed", str(SEED)]
    if extra:
        cmd += ["--extra-trial", "/".join(extra[0])]
    return {
        "job_id": JOB_ID, "command": cmd, "cwd": str(ROOT), "output_root": OUTPUT_ROOT, "receipt_path": RECEIPT,
        "bindings": bindings(picks, extra, root),
        "timeout_seconds": 3600, "kill_after_seconds": 30, "poll_seconds": 15,
        "startup_memory_mib": {"linux": 3584, "windows": 2816},
        "runtime_memory_mib": {"linux": 2048, "windows": 2048},
        "expected_output_names": ["pilot_summary.json"],
        "address_space_mib": ADDRESS_SPACE_MIB,
    }


def audited_keys_missing(path=sa.AUDITED_PATH):
    table = json.loads(Path(path).read_text())
    return sorted(k for k, _ in addb.STUDIES.values() if k not in (table.get("datasets") or {}))


def plan(spec_out):
    from contributor_tools.guarded_launcher import validate_spec
    spec = build_spec()
    validate_spec(spec)
    path = Path(spec_out)
    with path.open("x", encoding="utf-8") as f:  # never overwrite a spec
        f.write(json.dumps(spec, indent=1) + "\n")
    print(json.dumps({"spec": str(path), "sha256": sha256_file(path), "command": spec["command"][3:],
                      "audited_table_keys_missing": audited_keys_missing()}))


# ---------------------------------------------------------------- the job
def _peak_rss_mib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def _mem_available():
    line = next(s for s in Path("/proc/meminfo").read_text().splitlines() if s.startswith("MemAvailable:"))
    return int(line.split()[1]) * 1024


def row_groups_by_trial(pf):
    md = pf.metadata
    j = pf.schema_arrow.get_field_index("source_trial_index")
    out = {}
    for i in range(md.num_row_groups):
        st = md.row_group(i).column(j).statistics
        if st is None or st.min != st.max:
            raise ValueError(f"row group {i} does not hold a single source_trial_index")
        out.setdefault(int(st.min), []).append(i)
    return out


def check_trial(trial, result, cols, task_info):
    """Automated checks for one trial. Returns {check: [findings]}; empty lists pass."""
    f = {"wrong_published_sign": [], "unexplained_hold": [], "undo": [], "segment_not_from_published": [],
         "map_tan_task": [], "rows": [], "dof_guard": [], "not_checked": []}
    for side, leg in result["legs"].items():
        app = leg["application"]
        for k, c in app.log["channels"].items():
            if c["publication"] == "publish":
                if c["sign_vs_corrected_source"] != TRUTH.get(k):
                    f["wrong_published_sign"].append(f"{side} {k}: published {c['sign_vs_corrected_source']:+d}")
            elif not (c.get("hold_reason") or "").strip():
                f["unexplained_hold"].append(f"{side} {k}")
        try:
            restored = sa.undo_sign_application(app.channels, app.log)
            bad = [k for k, a in restored.items() if sa.array_sha256(a) != sa.array_sha256(leg["inputs"]["channels"][k])]
            f["undo"] += [f"{side} {k}" for k in bad]
        except sa.UndoError as exc:
            f["undo"].append(f"{side}: {exc}")
        avail = {k: sa.array_sha256(a) for k, a in leg["continuous"].items()}
        if not result["pelvis_published"]:
            avail.pop("pelvis_tilt", None)
        for seg, d in result["log"]["segments"][side]["derived"].items():  # chain order: thigh, shank, foot
            for name, h in d["inputs_sha256"].items():
                if avail.get(name) != h:
                    f["segment_not_from_published"].append(f"{side} {seg}: {name}")
            avail[seg] = d["output_sha256"]
    n = len(trial.flags)
    if not addb.protocol_match(trial.slug, trial.original_name):
        if task_info["task"] is not None or task_info["in_task_table"]:
            f["map_tan_task"].append(f"{trial.original_name}: labelled {task_info['task']!r}")
        if set(cols["task_id"]) != {trial.original_name}:
            f["map_tan_task"].append(f"{trial.original_name}: source name not kept")
    if len(cols["time_s"]) != 2 * n or sorted(set(cols["reference_side"])) != ["left", "right"]:
        f["rows"].append(f"{len(cols['time_s'])} rows for {n} frames")
    for side in addb.SIDES:
        s = addb.SIDES[side]
        knee = addb._col(trial, f"knee_angle_{s}", "pos")
        ankle = addb._col(trial, f"ankle_angle_{s}", "pos")
        if np.mean(knee >= -0.05) < 0.99 or np.mean((ankle >= -0.8) & (ankle <= 0.65)) < 0.99:
            f["dof_guard"].append(f"{side}: knee or ankle column outside the expected model range")
    return f


def run_participant(out, slug, subject, detector, answers, backlog_snapshot, only_trial=None):
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)
    d = DATA_ROOT / slug / subject
    conv = json.loads((d / "conversion.json").read_text())
    pf = pq.ParquetFile(d / "frames.parquet")
    names = pf.schema_arrow.names
    model = addb.check_model((d / "dynamics_model.osim").read_bytes(), conv, names)
    cols = addb.required_columns(names)
    groups = row_groups_by_trial(pf)
    if only_trial is not None:  # select by the conversion record's trial names, not by reading frames
        keep = {t["trial_index"] for t in conv["trials"] if t["original_name"] == only_trial and t["status"] == "written"}
        if not keep:
            raise ValueError(f"{slug}/{subject} has no written trial named {only_trial!r}")
        groups = {ti: g for ti, g in groups.items() if ti in keep}
    pdir = out / (f"{slug}_{subject}" + ("" if only_trial is None else f"_{only_trial}"))
    pdir.mkdir(parents=True, exist_ok=False)
    writer = pq.ParquetWriter(pdir / "mapped_frames.parquet.partial", addb.arrow_schema(), compression="zstd")
    trial_logs, sign_logs, findings, cross = [], [], {}, []
    rows = 0
    try:
        for ti in sorted(groups):
            t = pf.read_row_groups(groups[ti], columns=cols)
            trial = addb.trial_from_table(slug, t)
            del t
            if only_trial is not None and trial.original_name != only_trial:
                continue
            result = addb.apply_trial(trial, detector, backlog_path=backlog_snapshot)
            table_cols, task_info = addb.trial_rows(trial, result, answers)
            writer.write_table(pa.table(table_cols, schema=addb.arrow_schema()))
            rows += len(table_cols["time_s"])
            found = check_trial(trial, result, table_cols, task_info)
            findings[trial.recording] = {k: v for k, v in found.items() if v}
            trial_logs.append({**result["log"], **task_info, "findings": found})
            for side, leg in result["legs"].items():
                lg = leg["application"].log
                sign_logs.append(lg)
                cross.append({k: lg[k] for k in LOG_KEYS})
            del result, table_cols, trial
            if _peak_rss_mib() > RSS_CAP_MIB:
                raise MemoryError(f"peak RSS {_peak_rss_mib():.0f} MiB above {RSS_CAP_MIB}; stopped")
            if _mem_available() < MIN_AVAILABLE_BYTES:
                raise MemoryError("less than 2 GiB available; stopped at a trial boundary")
    finally:
        writer.close()
    os.link(pdir / "mapped_frames.parquet.partial", pdir / "mapped_frames.parquet")
    (pdir / "mapped_frames.parquet.partial").unlink()
    if pq.ParquetFile(pdir / "mapped_frames.parquet").metadata.num_rows != rows:
        raise RuntimeError("mapped_frames.parquet readback differs")
    hashes = {"mapped_frames.parquet": sha256_file(pdir / "mapped_frames.parquet"),
              "trial_logs.json": sa.write_json_exclusive(pdir / "trial_logs.json", sa._finite(trial_logs)),
              "sign_applications.json": sa.write_json_exclusive(pdir / "sign_applications.json", sign_logs)}
    source_ok = sha256_file(d / "frames.parquet") == conv["frames_parquet_sha256"]
    return {"participant": f"{slug}/{subject}", "only_trial": only_trial, "model": model, "rows": rows,
            "trials": len(trial_logs), "outputs": hashes, "source_unchanged": source_ok,
            "trials_with_findings": {k: v for k, v in findings.items() if v},
            "walking_direction_ok": sum(bool(t["walking_direction"]["ok"]) for t in trial_logs),
            "pelvis_published_trials": sum(bool(t["pelvis_published"]) for t in trial_logs),
            "published_counts": _counts(sign_logs)}, cross


def _counts(logs):
    out = {}
    for lg in logs:
        for k, c in lg["channels"].items():
            row = out.setdefault(k, {"publish": 0, "hold": 0, "verdicts": {}})
            row[c["publication"]] += 1
            row["verdicts"][c["verdict"]] = row["verdicts"].get(c["verdict"], 0) + 1
    return out


def run(args):
    if os.nice(0) < 19:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (niceness 19 expected)")
    soft, _ = resource.getrlimit(resource.RLIMIT_AS)
    if soft == resource.RLIM_INFINITY or soft > ADDRESS_SPACE_MIB * 1024 ** 2:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (address-space limit expected)")
    if not sa.SHA256_RE.fullmatch(args.detector_sha256 or ""):
        raise SystemExit("refused: --detector-sha256 must be a full lowercase sha256")
    picks, extra = pilot_sample(participants(), seed=args.seed)
    if args.participants != ",".join(f"{s}/{p}" for s, p in picks.items()):
        raise SystemExit("refused: --participants is not the seeded pilot sample")
    if (args.extra_trial or None) != ("/".join(extra[0]) if extra else None):
        raise SystemExit("refused: --extra-trial differs from the plan")
    missing = audited_keys_missing()
    if missing:
        raise SystemExit(f"refused before reading frames: the audited-sign table lacks dataset keys {missing}")
    if _mem_available() < MIN_AVAILABLE_BYTES:
        raise MemoryError("less than 2 GiB available; not started")
    out = (ROOT / args.output_root).resolve()
    out.mkdir(parents=True, exist_ok=False)
    started = time.time()
    (out / "inputs").mkdir()
    backlog_bytes = sa.BACKLOG_PATH.read_bytes()
    snapshot = out / "inputs" / "backlog_snapshot.json"
    with open(snapshot, "xb") as fh:
        fh.write(backlog_bytes)
    answers = addb.decision_answers(json.loads(backlog_bytes))
    parts, cross = [], []
    jobs = [(s, p, None) for s, p in picks.items()] + [(e[0], e[1], e[2]) for e in extra]
    for slug, subject, only in jobs:
        rec, c = run_participant(out, slug, subject, args.detector_sha256, answers, snapshot, only)
        parts.append(rec)
        cross += c
        print(f"{slug}/{subject}{'' if only is None else ' ' + only} done, peak RSS {_peak_rss_mib():.0f} MiB", flush=True)
    cross_items = sa.cross_group_review(cross)
    inits = [m for m in PACKAGE_INITS if m in sys.modules]
    failed = {p["participant"] + ("" if p["only_trial"] is None else f" {p['only_trial']}"): p["trials_with_findings"]
              for p in parts if p["trials_with_findings"]}
    hard = {k: {r: {c: v for c, v in f.items() if c != "not_checked"} for r, f in t.items()} for k, t in failed.items()}
    hard = {k: {r: f for r, f in t.items() if f} for k, t in hard.items()}
    hard = {k: t for k, t in hard.items() if t}
    passed = not hard and all(p["source_unchanged"] for p in parts) and not inits
    summary = {
        "task_id": TASK_ID, "scientific_approval": False, "mode": "pilot",
        "automated_outcome": "passed" if passed else "failed",
        "detector_sha256": args.detector_sha256, "bound_build": sa.bound_build(),
        "code_sha256": {ADAPTER: sha256_file(ROOT / ADAPTER), RUNNER: sha256_file(ROOT / RUNNER)},
        "seed": args.seed, "participants": picks, "extra_trial": extra,
        "decisions": {k: v for k, v in answers.items() if k.endswith("_record")},
        "backlog_snapshot_sha256": hashlib.sha256(backlog_bytes).hexdigest(),
        "truth": {"channels": TRUTH, "basis": "model definition (HIST-06 forward-kinematics probe); pelvis pitch "
                                              "rule-B by construction"},
        "checks": ["no published sign differs from the model-definition truth", "every hold carries a reason",
                   "undo of every hook output reproduces the adapter input", "segments derived from published "
                   "channels only (hash-linked)", "MAP-TAN-TASK: no non-protocol trial labelled or in a task table; "
                   "source name kept", "two rows (right and left reference) per source frame",
                   "knee and ankle DOF columns inside the model range (H23 guard)", "source frames.parquet sha256 "
                   "unchanged", "no package __init__ ran in the job"],
        "failures": hard, "not_checked_items": failed, "cross_group_review": cross_items,
        "package_inits_imported": inits, "participant_results": parts,
        "resources": {"peak_rss_mib": round(_peak_rss_mib(), 1), "rss_cap_mib": RSS_CAP_MIB,
                      "rlimit_as_bytes": list(resource.getrlimit(resource.RLIMIT_AS)), "nice": os.nice(0),
                      "wall_seconds": round(time.time() - started, 1)},
    }
    sa.write_json_exclusive(out / "pilot_summary.json", sa._finite(summary))
    print(json.dumps({"automated_outcome": summary["automated_outcome"], "participants": len(parts),
                      "peak_rss_mib": summary["resources"]["peak_rss_mib"]}))
    return 0 if passed else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="step", required=True)
    pp = sub.add_parser("plan", help="write and validate the plan-only job spec (no frame data read)")
    pp.add_argument("--spec-out", default=str(ROOT / SPEC))
    pr = sub.add_parser("run", help="the job; only through contributor_tools.guarded_launcher")
    pr.add_argument("--output-root", required=True)
    pr.add_argument("--detector-sha256", required=True)
    pr.add_argument("--participants", required=True)
    pr.add_argument("--seed", type=int, required=True)
    pr.add_argument("--extra-trial", default=None)
    args = p.parse_args(argv)
    if args.step == "plan":
        plan(args.spec_out)
        return 0
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
