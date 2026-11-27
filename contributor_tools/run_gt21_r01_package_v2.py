#!/usr/bin/env python3
"""GT21-R01 v2 (CORE-FOOT-01, decision D-REF-6 = A): the v1 package plus the per-person foot-flat zero.

A thin adapter on the v1 runner (run_gt21_r01_package.py, imported by file and not edited, so every v1 receipt binding stays
valid) and the shared builder. Reads the same hash-checked GT21-RB07 export and GT21-Q01 v2 inputs as v1 (they still exist),
keeps v1's read-only power check, applies contributor_tools/common/foot_flat.py through Part.transform after it, and re-assesses
L1 (ankle) and L5 (centre of pressure) on the shifted values (contributor_tools/common/foot_flat_adapter.py). Offsets:
docs/quality/audits/foot-flat-offsets.json (bound by hash). Writes NEW roots only (gt21_r01_package_v2 and
gt21_r01_package_pilot_v2_<attempt>); v1 is never touched. scientific_approval is false.

Run only through contributor_tools.guarded_launcher (one worker, nice 19, 768 MiB address space).
"""
from __future__ import annotations

import os
for _key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_key, "1")
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")
import argparse
import dataclasses
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


g = _load("gt21_r01_v1_runner", "contributor_tools/run_gt21_r01_package.py")
rp = g.rp
FF = "contributor_tools/common/foot_flat.py"
FFA = "contributor_tools/common/foot_flat_adapter.py"
OFFSETS = "docs/quality/audits/foot-flat-offsets.json"
ff = _load("foot_flat", FF)
ffa = _load("foot_flat_adapter", FFA)

TASK_ID = "GT21-R01-FF"
RUNNER = "contributor_tools/run_gt21_r01_package_v2.py"
VERSION = "v2"
ATTEMPT = "a5"  # job file names only
BASE, AUDITS = g.BASE, g.AUDITS
FF_BOUND = (RUNNER, FF, FFA, OFFSETS)
CODE_FILES = (RUNNER, g.SHARED, g.JOINT_POWER, g.Q01_RUNNER, FF, FFA)
ANKLE_TEXT = (
    "The ankle angle is the difference of the foot and shank angles measured against gravity (D-REF-1). In this version the foot "
    "and ankle angles carry the per-person foot-flat zero (see the foot-flat limitation); beyond that, the ankle zero has not been "
    "reviewed. The joint-range failures counted below are ankle angles after that shift; they may still reflect an unreviewed offset "
    "and are not evidence of measurement errors. The coarse limits are blatant-error limits written before any data were read, not "
    "approved reference ranges.")


class GT21V2Adapter(ffa.FootFlatMixin, g.GT21Adapter):
    ff_dataset = "GT21"
    ff_vocab = ff.VOCAB_GT21
    ff_l1_decimals = 3
    ff_failure_fields = tuple(g.FAILURE_FIELDS)
    ff_failed_check_ids = {"V.failed": "total", "V.failed_phase": "phase", "V.failed_time": "time"}
    ff_bound_files = FF_BOUND

    def __init__(self, subjects, stage):
        super().__init__(subjects, stage)
        self.release_id = VERSION
        self.ff_init(rp, ff, ROOT)

    def prepare(self):
        super().prepare()
        self.ff_prepare()

    def table_parts(self, table):                       # v1's power check first, then the foot-flat shift
        out = []
        for p in super().table_parts(table):
            first, second = p.transform, self.ff_tf[table]
            out.append(dataclasses.replace(p, transform=(lambda t, a=first, b=second: b(a(t)))))
        return out

    def limitations(self, entries):
        out = super().limitations(entries)
        for x in out:
            if x["id"] == "ankle_zero_offset_unreviewed":
                x["text"] = ANKLE_TEXT
        return out

    def readme_sections(self):
        return [(h, t.replace("this package does not change any value.",
                              "the only change in this version is the foot-flat zero described below."))
                for h, t in super().readme_sections()]


def stage_subjects(stage):
    return list(g.PILOT_SUBJECTS) if stage == "pilot" else list(g.SUBJECTS)


def stage_paths(stage):
    return {"job_id": f"{TASK_ID}-{stage}-{VERSION}-{ATTEMPT}", "spec": f"{AUDITS}/gt21-r01-{stage}-spec-{VERSION}-{ATTEMPT}.json",
            "output_root": f"{BASE}/gt21_r01_package_pilot_{VERSION}_{ATTEMPT}" if stage == "pilot" else f"{BASE}/gt21_r01_package_{VERSION}",
            "receipt": f"{AUDITS}/gt21-r01-{stage}-launcher-receipt-{VERSION}-{ATTEMPT}.json"}


def build_spec(stage, pilot_receipt=None, full_free_mib=15 * 1024 + 1024):
    p = stage_paths(stage)
    cmd = ["python3", RUNNER, "run", "--output-root", p["output_root"], "--stage", stage, "--subjects", ",".join(stage_subjects(stage))]
    b = {**g.bound_files(), **{k: rp.sha256_file(ROOT / k) for k in FF_BOUND}}
    if stage == "full":
        cmd += ["--pilot-receipt", pilot_receipt]
        b[pilot_receipt] = rp.sha256_file(ROOT / pilot_receipt)
    return {"job_id": p["job_id"], "command": cmd, "cwd": str(ROOT), "output_root": p["output_root"],
            "receipt_path": p["receipt"], "bindings": b, "timeout_seconds": 3600, "kill_after_seconds": 30, "poll_seconds": 15,
            "startup_memory_mib": {"linux": 3584, "windows": 2816}, "runtime_memory_mib": {"linux": 2048, "windows": 2048},
            "disk_admission": [{"path": p["output_root"], "min_free_mib": full_free_mib if stage == "full" else 4 * 1024}],
            "expected_output_names": ["manifest.json"], "address_space_mib": g.ADDRESS_SPACE_MIB}


def plan(stage, pilot_receipt=None, full_free_mib=15 * 1024 + 1024):
    from contributor_tools.guarded_launcher import validate_spec
    spec = build_spec(stage, pilot_receipt, full_free_mib)
    validate_spec(spec)
    path = ROOT / stage_paths(stage)["spec"]
    with path.open("x", encoding="utf-8") as f:
        f.write(json.dumps(spec, indent=1) + "\n")
    print(json.dumps({"spec": str(path), "sha256": rp.sha256_file(path)}))


def check_pilot(rel):
    r = json.loads((ROOT / rel).read_text())
    if r.get("status") != "completed" or r.get("clean_success") is not True:
        raise SystemExit("refused: the pilot receipt is not a clean completed run")
    cmd = r["spec"]["command"]
    if "--stage" not in cmd or cmd[cmd.index("--stage") + 1] != "pilot" or cmd[1] != RUNNER:
        raise SystemExit("refused: the receipt is not a v2 pilot run")
    for f in (*CODE_FILES, OFFSETS):
        if r["spec"]["bindings"].get(f) != rp.sha256_file(ROOT / f):
            raise SystemExit(f"refused: the pilot ran different code than the current {f}")


def run(args):
    rp.assert_guarded(g.ADDRESS_SPACE_MIB)
    subjects = args.subjects.split(",")
    if subjects != stage_subjects(args.stage):
        raise SystemExit("refused: --subjects are not the pilot pair or the 22 participants")
    if args.stage == "full":
        if not args.pilot_receipt:
            raise SystemExit("refused: a full run needs --pilot-receipt")
        check_pilot(args.pilot_receipt)
    rp.pin_arrow()
    started = time.time()
    adapter = GT21V2Adapter(subjects, args.stage)
    adapter.prepare()
    code, _ = rp.build_package(adapter, (ROOT / args.output_root).resolve(), stage=args.stage, started=started)
    return code


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="step", required=True)
    pp = sub.add_parser("plan")
    pp.add_argument("--stage", choices=("pilot", "full"), required=True)
    pp.add_argument("--pilot-receipt")
    pp.add_argument("--full-free-mib", type=int, default=15 * 1024 + 1024)
    pr = sub.add_parser("run")
    pr.add_argument("--output-root", required=True)
    pr.add_argument("--stage", choices=("pilot", "full"), required=True)
    pr.add_argument("--subjects", required=True)
    pr.add_argument("--pilot-receipt")
    args = p.parse_args(argv)
    if args.step == "plan":
        if args.stage == "full" and not args.pilot_receipt:
            raise SystemExit("a full plan needs --pilot-receipt")
        return plan(args.stage, args.pilot_receipt, args.full_free_mib)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
