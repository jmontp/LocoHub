#!/usr/bin/env python3
"""UM21-R01 v6 (CORE-FOOT-01, decision D-REF-6 = A): the v5 package (phase and time tables) plus the per-person foot-flat zero.

A thin adapter on the v5 runner (run_um21_r01_package_v5.py, itself on v4; both imported by file and not edited, so their receipt
bindings stay valid) and the shared builder. Reads the same hash-checked Q01 v3 parts and time-export parts as v5 (they still
exist), keeps v4's power transform, applies contributor_tools/common/foot_flat.py through Part.transform after it, and re-assesses
L1 (ankle) and L5 (centre of pressure) of the phase table on the shifted values (foot_flat_adapter.py); the time table carries only
the L2 assessment, which a constant shift cannot change (checked). The UM21 plate-placement gate stays as built: held centre-of-pressure
legs stay missing. Offsets: docs/quality/audits/foot-flat-offsets.json (bound by hash). Writes NEW roots only (um21_r01_package_v6
and um21_r01_package_pilot_v6_<attempt>); v5 is never touched. scientific_approval is false.

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


v5 = _load("um21_r01_package_v5_runner", "contributor_tools/run_um21_r01_package_v5.py")
v4, rp = v5.v4, v5.rp
FF = "contributor_tools/common/foot_flat.py"
FFA = "contributor_tools/common/foot_flat_adapter.py"
OFFSETS = "docs/quality/audits/foot-flat-offsets.json"
ff = _load("foot_flat", FF)
ffa = _load("foot_flat_adapter", FFA)

TASK_ID = "UM21-R01-FF"
RUNNER = "contributor_tools/run_um21_r01_package_v6.py"
VERSION = "v6"
ATTEMPT = "a5"  # job file names only
BASE, AUDITS = v5.BASE, v5.AUDITS
FF_BOUND = (RUNNER, FF, FFA, OFFSETS)


class UM21AdapterV6(ffa.FootFlatMixin, v5.UM21AdapterV5):
    ff_dataset = "UM21"
    ff_vocab = ff.VOCAB_UM21
    ff_limits = {"phase": ("L1", "L5"), "time": ()}        # the time table carries the L2 assessment only
    ff_l1_decimals = 1                                      # the UM21 assessment words L1 values with one decimal
    ff_failure_fields = ("observation_id", "reference_side", "table", "channel", "limit", "sample_index", "frame", "value", "reason")
    ff_failed_check_ids = {"U2": "phase"}
    ff_bound_files = FF_BOUND

    def __init__(self, recordings, stage):
        super().__init__(recordings, stage)
        self.release_id = VERSION
        self.ff_init(rp, ff, ROOT)

    def prepare(self):
        super().prepare()
        self.ff_prepare()

    def table_parts(self, table):                       # v5's parts (power transform on phase), then the foot-flat shift
        out = []
        for p in super().table_parts(table):
            first, second = p.transform, self.ff_tf[table]
            out.append(dataclasses.replace(p, transform=(second if first is None else (lambda t, a=first, b=second: b(a(t))))))
        return out


def stage_paths(stage):
    return {"job_id": f"{TASK_ID}-package-{stage}-{VERSION}-{ATTEMPT}",
            "spec": f"{AUDITS}/um21-r01-package-{stage}-spec-{VERSION}-{ATTEMPT}.json",
            "output_root": f"{BASE}/um21_r01_package_{stage}_{VERSION}_{ATTEMPT}" if stage == "pilot" else f"{BASE}/um21_r01_package_{VERSION}",
            "receipt": f"{AUDITS}/um21-r01-package-{stage}-launcher-receipt-{VERSION}-{ATTEMPT}.json"}


def build_spec(stage, pilot_receipt=None):
    p = stage_paths(stage)
    cmd = ["python3", RUNNER, "run", "--output-root", p["output_root"], "--stage", stage,
           "--recordings", ",".join(v4.stage_recordings(stage))]
    b = {**v5.bound_files(stage), **{k: rp.sha256_file(ROOT / k) for k in FF_BOUND}}
    if stage == "full":
        cmd += ["--pilot-receipt", pilot_receipt]
        b[pilot_receipt] = rp.sha256_file(ROOT / pilot_receipt)
    return {"job_id": p["job_id"], "command": cmd, "cwd": str(ROOT), "output_root": p["output_root"],
            "receipt_path": p["receipt"], "bindings": b, "timeout_seconds": 3600, "kill_after_seconds": 30, "poll_seconds": 15,
            "startup_memory_mib": {"linux": 3584, "windows": 2816}, "runtime_memory_mib": {"linux": 2048, "windows": 2048},
            "disk_admission": [{"path": p["output_root"], "min_free_mib": 8 * 1024 if stage == "full" else 3 * 1024}],
            "expected_output_names": ["manifest.json"], "address_space_mib": v4.ADDRESS_SPACE_MIB}


def plan(stage, pilot_receipt=None):
    from contributor_tools.guarded_launcher import validate_spec
    spec = build_spec(stage, pilot_receipt)
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
    if cmd[cmd.index("--stage") + 1] != "pilot" or cmd[1] != RUNNER:
        raise SystemExit("refused: the receipt is not a v6 pilot run")
    for f in (*FF_BOUND, v5.RUNNER, v4.RUNNER, v4.SHARED, v4.Q01_RUNNER, v4.JOINT_POWER, v5.T05_ASSESS_RUNNER, v5.T05_EXPORT):
        if r["spec"]["bindings"].get(f) != rp.sha256_file(ROOT / f):
            raise SystemExit(f"refused: the pilot ran different code than the current {f}")


def run(args):
    rp.assert_guarded(v4.ADDRESS_SPACE_MIB)
    recordings = args.recordings.split(",")
    if recordings != v4.stage_recordings(args.stage):
        raise SystemExit("refused: --recordings are not the pilot sample or the 44 recordings of the Q01 v3 job")
    if args.stage == "full":
        if not args.pilot_receipt:
            raise SystemExit("refused: a full run needs --pilot-receipt")
        check_pilot(args.pilot_receipt)
    rp.pin_arrow()
    started = time.time()
    adapter = UM21AdapterV6(recordings, args.stage)
    adapter.prepare()
    code, _ = rp.build_package(adapter, (ROOT / args.output_root).resolve(), stage=args.stage, started=started)
    return code


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="step", required=True)
    pp = sub.add_parser("plan")
    pp.add_argument("--stage", choices=("pilot", "full"), required=True)
    pp.add_argument("--pilot-receipt")
    pr = sub.add_parser("run")
    pr.add_argument("--output-root", required=True)
    pr.add_argument("--stage", choices=("pilot", "full"), required=True)
    pr.add_argument("--recordings", required=True)
    pr.add_argument("--pilot-receipt")
    args = p.parse_args(argv)
    if args.step == "plan":
        if args.stage == "full" and not args.pilot_receipt:
            raise SystemExit("a full plan needs --pilot-receipt")
        return plan(args.stage, args.pilot_receipt) or 0
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
