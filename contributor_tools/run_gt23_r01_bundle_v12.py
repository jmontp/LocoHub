#!/usr/bin/env python3
"""GT23-R01 v12 (CORE-FOOT-01, decision D-REF-6 = A): the v11 package plus the per-person foot-flat zero.

A thin adapter on the v11 runner (run_gt23_r01_bundle.py, imported by file and not edited, so every v11 receipt binding stays
valid) and the shared builder. The E01/E02 table files that v11 was built from were deleted on 2026-11-25 (disk cleanup approved
by Jose; notes and receipts kept), so the tables here are read from the v11 package itself (full_phase / full_time, hash-checked
against its manifest); its power values are already the D-REF-5 values, so the power transform is NOT applied again. The small
evidence files (E01/E02 jsonl, Q01 v2 assessment) are the same hash-checked inputs as v11. foot_flat.py is applied through
Part.transform, and L1 (ankle) and L5 (centre of pressure) are re-assessed on the shifted values (foot_flat_adapter.py).
Offsets: docs/quality/audits/foot-flat-offsets.json (bound by hash). Writes NEW roots only (gt23_r01_review_v12 and
gt23_r01_review_pilot_v12); v11 is never touched. scientific_approval is false.

Run only through contributor_tools.guarded_launcher (one worker, nice 19, 768 MiB address space).
"""
from __future__ import annotations

import os
for _key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_key, "1")
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")
import argparse
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


g = _load("gt23_r01_v11_runner", "contributor_tools/run_gt23_r01_bundle.py")
rp = g.rp
FF = "contributor_tools/common/foot_flat.py"
FFA = "contributor_tools/common/foot_flat_adapter.py"
OFFSETS = "docs/quality/audits/foot-flat-offsets.json"
ff = _load("foot_flat", FF)
ffa = _load("foot_flat_adapter", FFA)

TASK_ID = "GT23-R01-FF"
RUNNER = "contributor_tools/run_gt23_r01_bundle_v12.py"
VERSION = "v12"
ATTEMPT = "a8"  # job file names only (a1, a2 stopped at input checks; a3 ran but its G6 check compares with full-dataset statistics: E01/E02 tables and Q01 observations.jsonl are deleted)
BASE, AUDITS = g.BASE, g.AUDITS
PILOT_SUBJECTS = ("AB03", "AB07")  # AB03: side_shuffle_1 plate failures, E02 step_ups; AB07: the one participant without an offset
FF_BOUND = (RUNNER, FF, FFA, OFFSETS)
CODE_FILES = (RUNNER, g.SHARED, g.JOINT_POWER, FF, FFA)


V11_ROOT = f"{BASE}/gt23_r01_review_v11"
_orig_input_files = g.input_files


def _input_files_without_deleted_tables(subject):
    # deleted on 2026-11-25: the E01/E02 table files and the Q01 observations.jsonl (their content lives in the v11 package)
    return {k: v for k, v in _orig_input_files(subject).items()
            if not k.endswith(("/phase.parquet", "/time.parquet", "/observations.jsonl"))}


g.input_files = _input_files_without_deleted_tables   # the E01/E02 table files no longer exist; their small companions do


class SubjectsOnly(frozenset):
    """drop_recordings that skips every recording whose participant is not in `keep` (the pilot reads the one v11 file)."""

    def __new__(cls, keep):
        obj = super().__new__(cls)
        obj.keep = frozenset(keep)
        return obj

    def __contains__(self, rec):
        return rec.split("/")[0] not in self.keep


class FrozenGap:
    """The v11 power-gap statistics (computed when v11 was built from the source power values), read back from v11."""

    def __init__(self, summary):
        self._s = summary

    def summary(self):
        return self._s


class GT23V11Package(g.GT23Adapter):
    """The v11 adapter, reading the v11 package where the inputs it was built from no longer exist."""

    def _v11_files(self):
        m = json.loads((ROOT / V11_ROOT / "manifest.json").read_text())
        return m["files"]

    def prepare(self):
        files = self._v11_files()
        self._v11_hashes = {f"{V11_ROOT}/manifest.json": rp.sha256_file(ROOT / V11_ROOT / "manifest.json")}
        for name in ("full_phase.parquet", "full_time.parquet", "assessment.jsonl"):
            h = rp.sha256_file(ROOT / V11_ROOT / name)
            if h != files[name]["sha256"]:
                raise ValueError(f"{V11_ROOT}/{name} differs from the hash in its manifest")
            self._v11_hashes[f"{V11_ROOT}/{name}"] = h
        lim = json.loads((ROOT / V11_ROOT / "limitations.json").read_text())
        gap = next(x for x in lim["limitations"] if x["id"] == "power_from_moment_and_speed")["gap_source_power_vs_moment_times_velocity"]
        self.stats = FrozenGap({k: v for k, v in gap.items() if k != "definition"})
        super().prepare()

    def input_hashes(self):
        return {**super().input_hashes(), **self._v11_hashes}

    def table_parts(self, table):
        drop = SubjectsOnly(self.subjects) if list(self.subjects) != list(g.SUBJECTS) else frozenset()
        return [rp.Part(ROOT / V11_ROOT / f"full_{table}.parquet", "GT23-V11-PACKAGE", drop_recordings=drop,
                        transform=self._transform(table))]

    def _transform(self, table):                       # no power transform: v11 already carries the D-REF-5 power values
        return lambda t: t

    def assessment_entries(self):
        """The v11 package's own assessment entries (package form, power flags and held columns already applied): the Q01 v2
        observations.jsonl they came from was deleted on 2026-11-25. The v11 assessment.jsonl is hash-checked in prepare()."""
        with open(ROOT / V11_ROOT / "assessment.jsonl") as f:
            for line in f:
                e = json.loads(line)
                if e["subject"] in self.subjects:
                    e.pop("in_full_variant", None)
                    e.pop("in_filtered_variant", None)
                    yield e

    def _scan(self):
        for table in ("phase", "time"):
            maps = [g.jp.scan_presence(p.path, g.POWER_SPECS[table], skip_recordings=p.drop_recordings) for p in self.table_parts(table)]
            self.presence[table] = g.jp.merge_presence(maps)
            print(f"power presence scanned for {len(self.presence[table])} {table} observations", flush=True)


class GT23V12Adapter(ffa.FootFlatMixin, GT23V11Package):
    ff_dataset = "GT23"
    ff_vocab = ff.VOCAB_GT23
    ff_l1_decimals = 3
    ff_failure_fields = tuple(g.FAILURE_FIELDS)
    ff_failed_check_ids = {"G5.failed": "total"}
    ff_bound_files = FF_BOUND

    def __init__(self, subjects, stage):
        super().__init__(subjects, stage)
        self.release_id = VERSION
        self.ff_init(rp, ff, ROOT)

    def prepare(self):
        super().prepare()
        self.ff_prepare()

    def _transform(self, table):                       # the base class adds nothing (v11 already carries the power values)
        return self.ff_tf[table]

    def extra_checks(self, ctx):
        checks = super().extra_checks(ctx)
        if self.stage != "full":     # G6 compares with the power statistics of all 12 participants (read back from v11); a pilot is a subset
            checks = [c for c in checks if c[0] != "G6"]
        return checks

    def readme_sections(self):
        out = [("How v12 was built",
                "v12 is v11 with the foot-flat zero applied. The E01/E02 table files v11 was built from were deleted on 25 November "
                "2026 to free disk, so the tables were read from the v11 package (full tables, hash-checked against its manifest). "
                "Every value outside the foot angle, ankle angle and foot-frame pressure point is the v11 value.")]
        for h, t in super().readme_sections():
            out.append((h, t.replace("Ankle angle zero offset is unverified.",
                                     "The ankle angle carries the foot-flat zero described below; its zero is otherwise unreviewed.")))
        return out


def stage_subjects(stage):
    return list(PILOT_SUBJECTS) if stage == "pilot" else list(g.SUBJECTS)


def stage_paths(stage):
    return {"job_id": f"{TASK_ID}-{stage}-{VERSION}-{ATTEMPT}", "spec": f"{AUDITS}/gt23-r01-{stage}-spec-{VERSION}-{ATTEMPT}.json",
            "output_root": f"{BASE}/gt23_r01_review_pilot_{VERSION}" if stage == "pilot" else f"{BASE}/gt23_r01_review_{VERSION}",
            "receipt": f"{AUDITS}/gt23-r01-{stage}-launcher-receipt-{VERSION}-{ATTEMPT}.json"}


def build_spec(stage, pilot_receipt=None):
    p = stage_paths(stage)
    cmd = ["python3", RUNNER, "run", "--output-root", p["output_root"], "--stage", stage, "--subjects", ",".join(stage_subjects(stage))]
    bindings = {**g.bound_files(), **{k: rp.sha256_file(ROOT / k) for k in FF_BOUND}}
    if stage == "full":
        cmd += ["--pilot-receipt", pilot_receipt]
        bindings[pilot_receipt] = rp.sha256_file(ROOT / pilot_receipt)
    return {"job_id": p["job_id"], "command": cmd, "cwd": str(ROOT), "output_root": p["output_root"], "receipt_path": p["receipt"],
            "bindings": bindings, "timeout_seconds": 3600, "kill_after_seconds": 30, "poll_seconds": 15,
            "startup_memory_mib": {"linux": 3584, "windows": 2816}, "runtime_memory_mib": {"linux": 2048, "windows": 2048},
            "disk_admission": [{"path": p["output_root"], "min_free_mib": 25 * 1024 if stage == "full" else 8 * 1024}],
            "expected_output_names": ["manifest.json"], "address_space_mib": g.ADDRESS_SPACE_MIB}


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
    if "--stage" not in cmd or cmd[cmd.index("--stage") + 1] != "pilot" or cmd[1] != RUNNER:
        raise SystemExit("refused: the receipt is not a v12 pilot run")
    for f in (*CODE_FILES, OFFSETS):
        if r["spec"]["bindings"].get(f) != rp.sha256_file(ROOT / f):
            raise SystemExit(f"refused: the pilot ran different code than the current {f}")


def run(args):
    rp.assert_guarded(g.ADDRESS_SPACE_MIB)
    subjects = args.subjects.split(",")
    if subjects != stage_subjects(args.stage):
        raise SystemExit("refused: --subjects are not the pilot pair or the 12 participants")
    if args.stage == "full":
        if not args.pilot_receipt:
            raise SystemExit("refused: a full run needs --pilot-receipt")
        check_pilot(args.pilot_receipt)
    rp.pin_arrow()
    started = time.time()
    adapter = GT23V12Adapter(subjects, args.stage)
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
    pr.add_argument("--subjects", required=True)
    pr.add_argument("--pilot-receipt")
    args = p.parse_args(argv)
    if args.step == "plan":
        if args.stage == "full" and not args.pilot_receipt:
            raise SystemExit("a full plan needs --pilot-receipt")
        return plan(args.stage, args.pilot_receipt)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
