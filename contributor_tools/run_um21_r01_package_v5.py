#!/usr/bin/env python3
"""UM21-T05 / UM21-R01 v5: the UMich 2021 treadmill review package with a phase table AND a time table.

v5 is v4 plus the continuous time export. It is a thin adapter on top of run_um21_r01_package.py (v4, imported by file, not
edited, so the v4 receipt bindings and every v4 output stay valid) and the shared streaming builder
(contributor_tools/common/release_package.py), which already writes phase + time and the full and filtered variants.

What is unchanged: the phase table (same Q01 v3 parts, same joint-power transform, same exclusions, same phase assessment
statuses). The phase rows of v5 must equal the phase rows of v4 byte for byte in their data columns except the added identity
columns that depend on the lineage hash (lineage_id, assessment_id), which change because the time inputs are part of the
lineage; the readback script checks this.
What is new: the time table (one continuous_recording observation per recording, left/right columns, 100 Hz source clock,
ground force in body weights, centre of pressure), its structured assessment (L2 only, run_um21_t05_assessment.py), its
limitation entries, evidence files and README text. A time observation with an L2 jump is failed in the full variant and left
out of the filtered variant; every such exclusion is a row of exclusions.csv.

Inputs, all hash-checked before the build: the v4 inputs (Q01 v3 root against its clean launcher receipt), the time
assessment root (against its clean launcher receipt) and, through its recorded part hashes, every time part.

``plan``  writes a guarded-launcher spec; ``run`` only through ``python3 -m contributor_tools.guarded_launcher``.
Stages: ``pilot`` (the six pilot recordings, needs the pilot time assessment) and ``full`` (44 recordings; needs a clean pilot
package receipt of the same bound code). scientific_approval is false.
"""
from __future__ import annotations

import os
for _key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_key, "1")
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")
import argparse
import collections
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


v4 = _load("um21_r01_package_v4", "contributor_tools/run_um21_r01_package.py")
rp, jp = v4.rp, v4.jp
tx = _load("um21_time_export_pkg", "contributor_tools/um21_time_export.py")   # numpy only; no S02 import at load time

TASK_ID = "UM21-T05"
RUNNER = "contributor_tools/run_um21_r01_package_v5.py"
T05_ASSESS_RUNNER = "contributor_tools/run_um21_t05_assessment.py"
T05_EXPORT = "contributor_tools/um21_time_export.py"
VERSION = "v5"
ATTEMPT = "a4"
BASE, AUDITS = v4.BASE, v4.AUDITS
TIME_LABEL = "UM21-T05 time export (100 Hz source clock, S02 v7 geometry, plate force and centre of pressure)"
EXPECTED_TIME_OBSERVATIONS = 44


def assess_root(stage):
    return f"{BASE}/um21_t05_assess_{stage}_v2"


def assess_receipt(stage):
    return f"{AUDITS}/um21-t05-assess-{stage}-launcher-receipt-v2.json"


TIME_LIMITATION_TEXT = {
    "time_table_source_rate": (
        "Time table: one continuous observation per recording on the source frame clock, 100 Hz, time_s = (frame - 1) / 100. "
        "Nothing is resampled. The force plates record at 1 kHz; the table carries the plate sample that coincides with each "
        "frame (every tenth sample), without averaging or interpolation, so the nine plate samples between two frames are not "
        "in the table. The phase table is unchanged and is not derived from the time table."),
    "moments_from_source_sign_applied": (
        "Time-table joint moments are the source moments (Nm/kg, internal, named direction positive) read from the same channels "
        "as the phase table, with the audited sign of the phase export; exact zero triples are missing. The readback checks that "
        "the time samples at every stride window reproduce the published phase moments to rounding."),
    "time_pelvis_vicon_single_column": (
        "The pelvis angle in the time table is the Vicon pelvis tilt (audited sign), as in the phase table, in one column for the "
        "whole recording. A stride whose pelvis the phase table holds (marker pelvis disagrees by more than 1 degree, or a marker "
        "gap) has the pelvis, and the hip angle of that leg, missing over the stride's frames in the time table too. Frames "
        "outside every stride window are not checked against the markers."),
    "time_grf_plate_force": (
        "Ground reaction force (new in the time table): the force-plate force of each leg's belt turned into the walking-direction "
        "frame with the plate registration fitted in S02 (axis, sign, belt tilt), negated to be the force on the person, and "
        "divided by body weight (body mass from ParticipantDetails x 9.81). Vertical is up, anterior is the walking direction, "
        "lateral is outward from that leg. A sample whose plate carries less than 20 N is 0 body weights (the foot is off its plate); "
        "a plate sample that is not finite is missing. The source README gives N/kg, but the stride-mean total force equals body "
        "weight in N (UM21-SLOPE), so the plate values are in N. In AB03 and AB10 the plates carry 3 to 9 percent less than body "
        "weight (UM21-SLOPE), most on declines; those forces are published as recorded."),
    "time_grf_held_leg": (
        "Ground force held for a leg: the three force columns are present but missing for the whole recording because the plate "
        "registration of that leg is unknown, the body mass is missing, the plate was loaded at fewer than 95 percent of the leg's "
        "heel strikes, or the recording is one of the held-back recordings (pending by ruling). The reason is in held_signals."),
}
V4_FLAGS_ALSO_ON_TIME = ("power_from_moment_and_speed", "knee_marker_labels_swapped", "cop_estimated_plate_position",
                         "cop_held_leg", "cop_held_pending_ruling", "plane_glitch_hold")
TIME_LIMITATION_TITLES = {
    "time_table_source_rate": "Time table at the 100 Hz source clock, plate sampled at the frames",
    "moments_from_source_sign_applied": "Time-table moments: source channel with the audited sign",
    "time_pelvis_vicon_single_column": "Time-table pelvis: one Vicon column, held where the phase pelvis is held",
    "time_grf_plate_force": "Ground force from the plate, in body weights, 0 when the foot is off its plate",
    "time_grf_held_leg": "Ground force held for a leg"}

README_WHAT_NOT = (
    "No contralateral columns in the phase table: each stride carries its own leg only (the time table has left and right "
    "columns). The phase table has no ground reaction force; force is in the time table only. No 1 kHz plate table. Held-back "
    "data (the i10 recordings of AB01, AB02 and AB03, AB04/d10 and AB10/d5) stays pending as it is: centre of pressure and force "
    "are missing there.")
README_TIME = (
    "The time table has one row per 10 ms frame of each treadmill recording (reference_side 'none', observation type "
    "continuous_recording, left and right columns for each leg). Angles, velocities and the foot-frame centre of pressure use the "
    "same S02 v7 geometry as the phase table, frame by frame; velocities are central differences on the 10 ms clock; power is the "
    "moment times the joint speed. A leg plane more than 60 degrees from the walking direction holds that leg's plane-dependent "
    "columns at that frame (rule P1). Time samples at each stride window, resampled to 150 points, reproduce the phase table "
    "(checked by the readback). Only limit L2 (a jump of more than 30 degrees between adjacent samples) is applied to the time "
    "table; a recording with such a jump is failed in the full variant and absent from the filtered variant.")
TIME_EVIDENCE_FIELDS = ["recording", "leg", "force_published", "force_reason", "cop_published", "cop_reason", "glitch_frames"]


def read_jsonl(path):
    with open(path) as f:
        for line in f:
            yield json.loads(line)


def verify_time_assessment(stage):
    """Every output of the time assessment job hashed against its clean receipt; returns (root, hashes)."""
    rel_r = assess_receipt(stage)
    r = json.loads((ROOT / rel_r).read_text())
    if r.get("status") != "completed" or r.get("clean_success") is not True:
        raise ValueError(f"{rel_r} is not a clean completed run")
    root = assess_root(stage)
    if Path(r["spec"]["output_root"]).resolve() != (ROOT / root).resolve():
        raise ValueError("the time assessment receipt is for another output root")
    hashes = {}
    for o in r["outputs"]:
        rel = f"{root}/{o['path']}"
        h = rp.sha256_file(ROOT / rel)
        if h != o["sha256"]:
            raise ValueError(f"{rel} differs from the hash in {rel_r}")
        hashes[rel] = h
    return root, hashes


def time_force_rows(time_entries):
    rows = []
    for e in time_entries:
        held = e["held_signals"]
        for leg in ("left", "right"):
            a = e["attributes"]
            rows.append({"recording": e["source_recording_id"], "leg": leg,
                         "force_published": a["force_published_by_leg"][leg],
                         "force_reason": held.get(f"grf_vertical_{leg}_BW", ""),
                         "cop_published": a["cop_published_by_leg"][leg],
                         "cop_reason": held.get(f"cop_anterior_{leg}_m", ""), "glitch_frames": a["glitch_frames_by_leg"][leg]})
    return sorted(rows, key=lambda r: (r["recording"], r["leg"]))


class UM21AdapterV5(v4.UM21Adapter):
    tables = ("phase", "time")
    title = "UMich 2021 treadmill review package"

    def __init__(self, recordings, stage):
        super().__init__(recordings, stage)
        self.release_id = VERSION
        self.time_assessment, self._time_hashes, self._time_entries = {}, {}, []

    def prepare(self):
        super().prepare()
        root, hashes = verify_time_assessment(self.stage)
        self._time_hashes = hashes
        self._inputs.update(hashes)
        self._bound.update({k: rp.sha256_file(ROOT / k) for k in (RUNNER, T05_ASSESS_RUNNER, T05_EXPORT, assess_receipt(self.stage))})
        self.time_assessment = json.loads((ROOT / root / "time_assessment.json").read_text())
        ta = self.time_assessment
        if sorted(ta["parts"]) != sorted(self.recordings):
            raise ValueError("the time assessment covers other recordings than this package")
        for rec, p in ta["parts"].items():
            if rp.sha256_file(ROOT / p["path"]) != p["sha256"]:
                raise ValueError(f"{p['path']} differs from the hash recorded by the time assessment")
        self._time_entries = [e for e in read_jsonl(ROOT / root / "time_observations.jsonl") if self._selected(e["source_recording_id"])]
        print("time assessment verified against its receipt and part hashes", flush=True)

    def lineage_inputs(self):
        return {k: v for k, v in self._inputs.items()
                if k.endswith(("observations.jsonl", "failures.jsonl", "assessment.json"))}   # includes the time_* files

    def table_parts(self, table):
        if table == "phase":
            return super().table_parts("phase")
        return [rp.Part(ROOT / self.time_assessment["parts"][r]["path"], TIME_LABEL) for r in self.recordings]

    def assessment_entries(self):
        yield from super().assessment_entries()
        for e in self._time_entries:
            yield e

    def evidence_tables(self):
        ev = dict(super().evidence_tables())
        ev["time_force_and_cop_legs.csv"] = (TIME_EVIDENCE_FIELDS, time_force_rows(self._time_entries))
        ev["time_l2_jumps.csv"] = (["recording", "observation_id", "channel", "frame", "time_s", "value_deg", "reason"],
                                   [{"recording": x["recording"], "observation_id": x["observation_id"], "channel": x["channel"],
                                     "frame": x["frame"], "time_s": x["time_s"], "value_deg": x["value"], "reason": x["reason"]}
                                    for x in read_jsonl(ROOT / assess_root(self.stage) / "time_failures.jsonl")
                                    if self._selected(x["observation_id"].rsplit(":", 4)[0])])
        return ev

    def limitations(self, entries):
        phase = [e for e in entries if e["table"] == "phase"]
        timed = [e for e in entries if e["table"] == "time"]
        out = v4.UM21Adapter.limitations(self, phase)
        for x in out:
            if x["id"] in V4_FLAGS_ALSO_ON_TIME:
                x["time_observations"] = rp.count_flag(timed, x["id"])["observations"]
        for flag, text in TIME_LIMITATION_TEXT.items():
            out.append({"id": flag, "title": TIME_LIMITATION_TITLES[flag], "text": text, **rp.count_flag(timed, flag)})
        return out

    def readme_sections(self):
        secs = [s for s in super().readme_sections() if s[0] != "What is not in this package"]
        return secs + [("Time table", README_TIME), ("What is not in this package", README_WHAT_NOT)]

    def extra_checks(self, ctx):
        counts, entries = ctx["counts"], ctx["entries"]
        a, ta = self.assessment, self.time_assessment
        sel = set(self.recordings)
        phase = [e for e in entries if e["table"] == "phase"]
        timed = [e for e in entries if e["table"] == "time"]
        n_pub, n_held, _n_legs = v4.published_leg_count(phase)
        a_pub = sum(1 for l in a["cop_legs"]["published"] if l["recording"] in sel)
        a_held = sum(1 for l in a["cop_legs"]["held"] if l["recording"] in sel)
        failed_phase = [e for e in phase if e["overall"] == rp.FAILED]
        failed_time = [e for e in timed if e["overall"] == rp.FAILED]
        by_kind = ctx["by_kind"]
        upstream = by_kind.get("upstream_stride_rule", 0) + by_kind.get("upstream_sudden_jump", 0)
        t_assess = {r: v for r, v in ta["per_record"].items() if r in sel}
        checks = [
            ("U1", "phase observations equal the observations of the Q01 v3 job",
             sum(v["observations"] for r, v in a["per_record"].items() if r in sel), counts["full"]["phase_observations"]),
            ("U2", "failed phase observations equal the failures recorded by the Q01 v3 job",
             sum(v["failed"] for r, v in a["per_record"].items() if r in sel), len(failed_phase)),
            ("U3", "legs with a published centre of pressure and legs held equal the Q01 v3 verdicts", [a_pub, a_held], [n_pub, n_held]),
            ("U4", "the package has a phase table and a time table", ["phase", "time"], counts["tables"]),
            ("U5", "every phase observation has exactly 150 rows", counts["full"]["phase_observations"] * 150, counts["full"]["phase_rows"]),
            ("U7", "finite power rows in the written full phase table equal the rows where moment and joint speed were both finite",
             {c: v["rows_new_finite"] for c, v in sorted(self.stats.summary().items())},
             {c: ctx["readback"][("full", "phase")]["finite"][c] for c in sorted(v4.POWER_COLUMNS)}),
            ("U8", "time observations and rows equal the time assessment (one per recording)",
             [len(t_assess), sum(v["rows"] for v in t_assess.values())], [counts["full"]["time_observations"], counts["full"]["time_rows"]]),
            ("U9", "failed time observations equal the time assessment",
             sorted(r for r, v in t_assess.items() if v["status"] == "failed"), sorted(e["rec"].split("Streaming/")[1].replace("/Tread/", "/") for e in failed_time)),
            ("U10", "the time observation ids equal the ids named by the time assessment",
             sorted(p["observation_id"] for r, p in ta["parts"].items() if r in sel), sorted(e["key"][0] for e in timed)),
            ("U11", "no phase assessment status was changed by the time assessment (phase failure causes equal the Q01 v3 causes; in a pilot subset every cause is one of them)",
             sorted(a["failed_by_limit_observations"]) if self.stage == "full" else sorted(a["failed_by_limit_observations"])[:0] + sorted({c for e in failed_phase for c in e["causes"]} & set(a["failed_by_limit_observations"])),
             sorted({c for e in failed_phase for c in e["causes"]})),
        ]
        if self.stage == "full":
            seen = {"observations": counts["full"]["phase_observations"], "phase_rows": counts["full"]["phase_rows"],
                    "recordings": len({e["rec"] for e in phase}), "upstream_stride_rule_exclusions": by_kind.get("upstream_stride_rule", 0),
                    "sudden_jump_exclusions": by_kind.get("upstream_sudden_jump", 0),
                    "upstream_total_observations": counts["full"]["phase_observations"] + upstream,
                    "cop_legs_published": n_pub, "cop_legs_held": n_held}
            checks += [("V." + k, f"{k} equals the verified chain total", v, seen[k]) for k, v in v4.EXPECTED_FULL.items()]
            checks.append(("V.time_observations", "time observations equal the 44 recordings", EXPECTED_TIME_OBSERVATIONS,
                           counts["full"]["time_observations"]))
        return checks


# ------------------------------------------------------------------ job
def stage_paths(stage):
    return {"job_id": f"{TASK_ID}-package-{stage}-{VERSION}-{ATTEMPT}",
            "spec": f"{AUDITS}/um21-r01-package-{stage}-spec-{VERSION}-{ATTEMPT}.json",
            "output_root": f"{BASE}/um21_r01_package_{stage}_{VERSION}_{ATTEMPT}" if stage == "pilot" else f"{BASE}/um21_r01_package_{VERSION}",
            "receipt": f"{AUDITS}/um21-r01-package-{stage}-launcher-receipt-{VERSION}-{ATTEMPT}.json"}


def bound_files(stage):
    b = dict(v4.bound_files())
    for k in (RUNNER, T05_ASSESS_RUNNER, T05_EXPORT, assess_receipt(stage)):
        b[k] = rp.sha256_file(ROOT / k)
    return b


def build_spec(stage, pilot_receipt=None):
    p = stage_paths(stage)
    cmd = ["python3", RUNNER, "run", "--output-root", p["output_root"], "--stage", stage,
           "--recordings", ",".join(v4.stage_recordings(stage))]
    b = bound_files(stage)
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
    if cmd[cmd.index("--stage") + 1] != "pilot":
        raise SystemExit("refused: the receipt is not a pilot run")
    for f in (RUNNER, v4.RUNNER, v4.SHARED, v4.Q01_RUNNER, v4.JOINT_POWER, T05_ASSESS_RUNNER, T05_EXPORT):
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
    adapter = UM21AdapterV5(recordings, args.stage)
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
