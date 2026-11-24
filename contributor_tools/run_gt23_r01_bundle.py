#!/usr/bin/env python3
"""GT23-R01: build the local Georgia Tech 2023 review package (package only; no documentation page).

This file is the GT23 adapter and its launcher interface. The package layout and the streaming builder are shared by every
dataset: contributor_tools/common/release_package.py, layout in contributor_tools/DATA_CONTRACT.md ("Release package").
What is GT23-specific here: the input roots and their hash checks against the launcher receipts, the export exclusions and
authors' windows, the structured assessment entries (GT23-Q01 v2) in package form, and the limitation entries.

Decision D-GT23-R01-1 = B: strides and movements plus the continuous recordings, as separate files (one phase file and one
time file per variant), not split per participant.

Inputs (all hash-checked against the clean launcher receipts of the chain GT23-PL01):
  GT23-E01 batch roots   gt23_pl_e01_batch_ABxx
  GT23-E02 batch roots   gt23_pl_e02_batch_ABxx  (13 re-exported recordings that REPLACE the same recordings of E01)
  GT23-Q01 v2 roots      gt23_pl_q01v2_batch_ABxx and gt23_pl_q01v2_summary (the single structured assessment)

Nothing is repaired, resampled, filled or re-labelled. Run only through contributor_tools.guarded_launcher (one worker,
nice 19, 768 MiB address space). scientific_approval is false.
"""
from __future__ import annotations

import os
for _key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_key, "1")
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")  # must precede pyarrow (768 MiB address-space cap)
import argparse
import collections
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import importlib.util  # noqa: E402


def _load_shared():
    """Load the shared builder by path. Importing it as contributor_tools.common.release_package would run
    contributor_tools/common/__init__.py, which pulls in pandas, scipy and yaml (about 86 MiB the build cannot spare under the
    768 MiB address-space cap)."""
    path = ROOT / "contributor_tools" / "common" / "release_package.py"
    spec = importlib.util.spec_from_file_location("release_package", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["release_package"] = mod
    spec.loader.exec_module(mod)
    return mod


rp = _load_shared()

TASK_ID = "GT23-R01"
RUNNER = "contributor_tools/run_gt23_r01_bundle.py"
SHARED = "contributor_tools/common/release_package.py"
VERSION = "v10"  # v1-v9 were earlier pilots or failed full builds (memory); roots are not the frozen code
BASE = "converted_datasets/reconversion_v2"
SUBJECTS = ("AB01", "AB02", "AB03", "AB05", "AB06", "AB07", "AB08", "AB09", "AB10", "AB11", "AB12", "AB13")
PILOT_SUBJECTS = ("AB03", "AB13")  # AB03: side_shuffle_1 failures and E02 step_ups; AB13: E02 dynamic_walk_1 and a held right leg
AUDITS = "docs/quality/audits"
E01_RECEIPT = AUDITS + "/gt23-pl-e01-batch-{}-launcher-receipt.json"
E02_RECEIPT = AUDITS + "/gt23-pl-e02-batch-{}-launcher-receipt.json"
Q01_RECEIPT = AUDITS + "/gt23-pl-q01v2-batch_{}-launcher-receipt.json"
CHAIN_SUMMARIES = (AUDITS + "/gt23-pl-e01-summary-launcher-receipt.json",
                   AUDITS + "/gt23-pl-e02-summary-launcher-receipt.json",
                   AUDITS + "/gt23-pl-q01v2-summary-launcher-receipt.json")
Q01_SUMMARY = BASE + "/gt23_pl_q01v2_summary/assessment_summary.json"
HANDOFFS = tuple(f"docs/maintainers/handoffs/{n}.json" for n in
                 ("GT23-M01", "GT23-M01-verify", "GT23-S01", "GT23-S01-verify", "GT23-X01", "GT23-X01-verify",
                  "GT23-PL01", "GT23-PL01-verify"))
ADDRESS_SPACE_MIB = 768
FAILURE_FIELDS = ["observation_id", "reference_side", "table", "channel", "limit", "sample_index", "phase_percent", "time_s",
                  "value", "reason"]
WINDOW_FIELDS = ["subject", "source_recording_id", "file", "row", "key", "side", "segment_index", "start_s", "end_s", "status",
                 "fate", "reason", "observation_ids"]

EXPECTED_FULL = {"phase_rows": 2862750, "time_rows": 6397787, "phase_observations": 19085, "continuous_recordings": 488,
                 "observations": 19573, "failed": 125, "export_exclusions": 1415, "authors_windows_not_exported": 3741,
                 "authors_windows_exported": 9378, "estimated_mass_recordings": 45, "exact_mass_recordings": 7,
                 "recordings_replaced_by_e02": 13}

PREVIEW_COLUMNS = ("pelvis_sagittal_angle_rad", "thigh_sagittal_angle_ipsi_rad", "shank_sagittal_angle_ipsi_rad",
                   "foot_sagittal_angle_ipsi_rad", "hip_flexion_angle_ipsi_rad", "knee_flexion_angle_ipsi_rad",
                   "ankle_dorsiflexion_angle_ipsi_rad", "hip_flexion_moment_ipsi_Nm_kg", "knee_flexion_moment_ipsi_Nm_kg",
                   "ankle_dorsiflexion_moment_ipsi_Nm_kg", "grf_vertical_ipsi_BW", "cop_anterior_ipsi_m")

CORRECTED_COP_TEXT = (
    "Centre of pressure (foot frame), as defined by the 24 November 2026 standard (docs/reference/index.md): the centre of "
    "pressure is expressed in the ankle frame, which moves with the foot, within that leg's side-view plane. The foot direction "
    "is the leg-plane forward direction rotated by the foot angle (foot = shank + ankle). The origin is 100 mm forward of the "
    "ankle joint centre along that foot direction; forward is along it, up is perpendicular to it within the plane, and sideways "
    "is perpendicular to the leg plane, outward from that leg. Toe-out therefore appears as a sideways offset. "
    "This replaces the wording 'forward along heel to toe' in the READMEs of the E01 and E02 batch folders; those batch READMEs "
    "are kept unchanged as evidence and are superseded on this line only. The data were built under the 24 November rule.")

LIMITATION_TEXT = {
    "step_up_cop_held": ("Step-up foot-frame pressure point is held (all missing): the foot stands on a step of about 0.5 m of "
                         "undocumented height on the plate, and the recorded plate height is the plate surface. Force and plate "
                         "pressure point stay."),
    "curb_up_cop_held": ("curb_up foot-frame pressure point is held (all missing): the heel stands 0.20 to 0.23 m above the "
                         "recorded plate surface (a curb of undocumented height). Force and plate pressure point stay."),
    "ab07_right_foot_offset": ("AB07 right-foot marker offset: the foot-frame pressure point of the right foot lies outside the "
                               "marker foot for about 30 percent of loaded normal-walk samples (marker foot length 0.193 m) and the "
                               "AB07 ankle offset is the largest of the twelve participants (about -9 to -13 degrees); the cause "
                               "is unresolved. Left-foot values of AB07 are affected by a missing LMANK marker as listed per "
                               "recording."),
    "mass_estimated": ("Per-kg moments and powers were multiplied by (mass used / own mass) for recordings where the publisher "
                       "divided by another participant's listed mass; the mass used is estimated from the force plates and matched "
                       "to the nearest listed mass (45 recordings)."),
    "ab09_divisor": ("AB09 divisor: the publisher divided these recordings by a mass the audit could not place among the listed "
                     "masses (no plausible listed mass inside the force-plate interval); the rescale used the nearest listed mass "
                     "(87.6 kg) and may be off by up to about 5 percent."),
    "nm_rerun_limit": ("N*m re-run limit: moments and powers of these recordings were rescaled with an exact mass found by a "
                       "local N*m inverse-dynamics re-run; that re-run exists for 7 recordings only. Every other recording is "
                       "estimated, kept as published, or cannot be told."),
    "window_span_both_legs": ("Window-rule spans (transfers) have no single leg: each accepted span is exported for the left and "
                              "the right reference leg with the same observation_id, so the 'transfer' observations come in "
                              "pairs. Contralateral columns cover the same absolute time span; no 50 percent shift is assumed."),
    "shuffle_not_steady_walking": "Shuffle cycles (task_id level_shuffle) are filed under task level_walking but are not steady walking.",
    "unlabelled_walking_under_functional_task": ("Walking cycles of the unlabelled recordings normal_walk_1 and incline_walk_* "
                                                 "sit under task functional_task, because the source gives no speed or incline "
                                                 "label for them; some cycles show a flight phase (both feet unloaded)."),
    "run_label_check": ("Cycles with task run (2.0 and 2.5 m/s) are labelled run, while the publisher README describes these "
                        "recordings as walking; some of these cycles show a flight phase (both feet unloaded)."),
}
UNCHECKED_FAMILIES = ("joint velocities", "joint moments", "joint powers", "ground reaction forces (N and body weight)",
                      "lab-axis pressure point", "heading", "subtalar angle, moment and power",
                      "hip adduction/rotation moments and powers")


# ------------------------------------------------------------------ small helpers
def read_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f]


def rec_path(subject, kind):
    return {"e01": f"{BASE}/gt23_pl_e01_batch_{subject}", "e02": f"{BASE}/gt23_pl_e02_batch_{subject}",
            "q01": f"{BASE}/gt23_pl_q01v2_batch_{subject}/{subject}"}[kind]


def receipt_outputs(rel):
    """{relative output path: sha256} of a clean completed launcher receipt."""
    r = json.loads((ROOT / rel).read_text())
    if r.get("status") != "completed" or r.get("clean_success") is not True:
        raise ValueError(f"{rel} is not a clean completed run")
    return {o["path"]: o["sha256"] for o in r["outputs"]}


def input_files(subject):
    """{relative path: (receipt path, output name)} for every input file the adapter reads."""
    out = {}
    for kind, receipt in (("e01", E01_RECEIPT), ("e02", E02_RECEIPT)):
        names = ["phase.parquet", "time.parquet", "authors_windows.jsonl", "exclusions.jsonl", "recordings.jsonl"]
        if kind == "e02":
            names.append("e02_summary.json")
        for n in names:
            out[f"{rec_path(subject, kind)}/{n}"] = (receipt.format(subject), n)
    for n in ("assessment.json", "observations.jsonl", "failures.jsonl"):
        out[f"{rec_path(subject, 'q01')}/{n}"] = (Q01_RECEIPT.format(subject), f"{subject}/{n}")
    return out


def verify_inputs(subject):
    """Hash every input file and compare it with the receipt of the job that wrote it. Returns {path: sha256}."""
    files = input_files(subject)
    receipts = {}
    for rel, (rcpt, name) in files.items():
        receipts.setdefault(rcpt, receipt_outputs(rcpt))
    hashes = {}
    for rel, (rcpt, name) in sorted(files.items()):
        h = rp.sha256_file(ROOT / rel)
        want = receipts[rcpt].get(name)
        if want is None or h != want:
            raise ValueError(f"{rel} differs from the hash in {rcpt} ({name})")
        hashes[rel] = h
    return hashes


def bound_files():
    b = [RUNNER, SHARED, Q01_SUMMARY, *CHAIN_SUMMARIES, *HANDOFFS]
    for s in SUBJECTS:
        b += [E01_RECEIPT.format(s), E02_RECEIPT.format(s), Q01_RECEIPT.format(s)]
    return {k: rp.sha256_file(ROOT / k) for k in b}


# ------------------------------------------------------------------ pure rules (tested with synthetic data)
def failure_causes(entry):
    """Why the assessment marked an observation failed: the failed limits plus a failed structural side check."""
    causes = list(entry["plausibility"]["failed_limits"])
    if entry["structural"]["state"] == "fail":
        causes.append("S5_side_check" if entry["structural"].get("S5_side_check") == "fail" else "structural")
    return sorted(set(causes))


def package_entry(e):
    """A GT23-Q01 v2 observation entry in the package's assessment format."""
    fl = e.get("flight")
    held = e.get("held_signals") or {}
    return {"observation_id": e["observation_id"], "reference_side": e["reference_side"], "table": e["table"],
            "observation_type": e["observation_type"], "subject": e["source_recording_id"].split("/")[0],
            "source_recording_id": e["source_recording_id"], "task": e["task"], "task_id": e["task_id"], "rows": int(e["rows"]),
            "status": e["overall"], "failed_limits": failure_causes(e) if e["overall"] == rp.FAILED else [],
            "failed_channels": list(e["plausibility"]["failed_channels"]),
            "failed_samples": {c: dict(v) for c, v in e["plausibility"].get("failed_samples", {}).items()},
            "limitations": list(e["limitations"]), "flight": (None if not fl else bool(fl.get("flight_cycle"))),
            "attributes": {"mass_note_key": e["mass_note_key"],
                           "foot_cop_held": any(c.startswith(("cop_anterior_", "cop_vertical_", "cop_lateral_")) for c in held),
                           "structural_state": e["structural"]["state"]},
            "held_signals": dict(held), "channel_states": {k: list(v) for k, v in e["plausibility"]["channel_states"].items()}}


def export_exclusion_rows(subject, e01_excl, e02_excl, superseded):
    """Export exclusions of one participant. E01 rows of replaced recordings are replaced by the E02 rows."""
    rows = []
    for x in [r for r in e01_excl if r["recording"] not in superseded] + list(e02_excl):
        rows.append({"exclusion_id": x["segment_id"], "observation_id": "", "subject": subject,
                     "source_recording_id": f"{subject}/{x['recording']}", "reference_side": x["side"],
                     "stage": "upstream_not_released", "kind": "export_exclusion", "reason_code": x["reason"],
                     "reason": f"segment left out at export ({x['stage']}): {x['reason']}", "decision": "",
                     "in_full_variant": False, "in_filtered_variant": False, "task": x["task"], "task_id": "",
                     "start_s": x["start_s"], "end_s": x["end_s"], "detail": ""})
    return rows


def window_exclusion_rows(subject, windows):
    rows = []
    for w in windows:
        if w["fate"] == "exported":
            continue
        code, _, rest = (w["reason"] or "").partition(":")
        rows.append({"exclusion_id": f"{w['file']}#{w['row']}", "observation_id": "", "subject": subject,
                     "source_recording_id": f"{subject}/{w['recording']}",
                     "reference_side": {"L": "left", "R": "right"}.get(w["side"], w["side"]),
                     "stage": "upstream_not_released", "kind": "authors_window_not_exported", "reason_code": code.strip(),
                     "reason": f"authors' window not exported: {w['reason']}", "decision": "", "in_full_variant": False,
                     "in_filtered_variant": False, "task": w["task"], "task_id": "", "start_s": w["start"], "end_s": w["end"],
                     "detail": rest.strip()})
    return rows


# ------------------------------------------------------------------ the adapter
class GT23Adapter(rp.ReleaseAdapter):
    dataset_id = "gt23"
    title = "Georgia Tech 2023 review package"
    tables = ("phase", "time")
    preview_columns = PREVIEW_COLUMNS
    unchecked_families = UNCHECKED_FAMILIES

    def __init__(self, subjects, stage):
        self.subjects, self.stage = list(subjects), stage
        self.release_id = VERSION
        self._inputs, self._bound = {}, {}
        self.sup, self.windows, self.recordings, self.replaced = {}, [], [], {}
        self._excl, self._window_rows, self.problems = [], [], []

    def prepare(self):
        """Hash and check every input against its receipt, then load the small evidence files."""
        for s in self.subjects:
            self._inputs.update(verify_inputs(s))
            print(f"{s}: inputs verified against receipts", flush=True)
        self._bound = bound_files()
        for s in self.subjects:
            e02, e01 = rec_path(s, "e02"), rec_path(s, "e01")
            summary = json.loads((ROOT / e02 / "e02_summary.json").read_text())
            sup = set(summary["superseded_e01_recordings"])
            self.sup[s], self.replaced[s] = sup, sorted(sup)
            aw1, aw2 = read_jsonl(ROOT / e01 / "authors_windows.jsonl"), read_jsonl(ROOT / e02 / "authors_windows.jsonl")
            ex1, ex2 = read_jsonl(ROOT / e01 / "exclusions.jsonl"), read_jsonl(ROOT / e02 / "exclusions.jsonl")
            canon = lambda rows: sorted(json.dumps(r, sort_keys=True) for r in rows)  # noqa: E731
            if canon([r for r in aw1 if r["recording"] in sup]) != canon(aw2):
                self.problems.append(f"{s}: E02 authors windows differ from the E01 windows of the replaced recordings")
            if canon([r for r in ex1 if r["recording"] in sup]) != canon(ex2):
                self.problems.append(f"{s}: E02 export exclusions differ from the E01 exclusions of the replaced recordings")
            rec1, rec2 = read_jsonl(ROOT / e01 / "recordings.jsonl"), read_jsonl(ROOT / e02 / "recordings.jsonl")
            if {r["recording"] for r in rec2} != sup:
                self.problems.append(f"{s}: E02 recordings differ from its superseded list")
            self.recordings += [{**r, "subject": s} for r in [r for r in rec1 if r["recording"] not in sup] + rec2]
            windows = [w for w in aw1 if w["recording"] not in sup] + aw2
            self.windows += [{**w, "subject": s} for w in windows]
            self._excl += export_exclusion_rows(s, ex1, ex2, sup) + window_exclusion_rows(s, windows)
            for w in windows:
                self._window_rows.append({"subject": s, "source_recording_id": f"{s}/{w['recording']}", "file": w["file"],
                                          "row": w["row"], "key": w["key"], "side": w["side"], "segment_index": w["segment_index"],
                                          "start_s": w["start"], "end_s": w["end"], "status": w["status"], "fate": w["fate"],
                                          "reason": w["reason"] or "", "observation_ids": ";".join(w["observations"])})

    def input_hashes(self):
        return self._inputs

    def bound_hashes(self):
        return self._bound

    def lineage_inputs(self):
        h = {k: v for k, v in self._inputs.items() if "/gt23_pl_q01v2_batch_" in k}
        h[Q01_SUMMARY] = rp.sha256_file(ROOT / Q01_SUMMARY)
        return h

    def table_parts(self, table):
        parts = []
        for s in self.subjects:
            full = frozenset(f"{s}/{n}" for n in self.sup[s])
            parts.append(rp.Part(ROOT / rec_path(s, "e01") / f"{table}.parquet", "GT23-E01", drop_recordings=full))
            parts.append(rp.Part(ROOT / rec_path(s, "e02") / f"{table}.parquet", "GT23-E02", expect_recordings=full))
        return parts

    def assessment_entries(self):
        for s in self.subjects:
            with open(ROOT / rec_path(s, "q01") / "observations.jsonl") as f:
                for line in f:
                    yield package_entry(json.loads(line))

    def exclusion_rows(self):
        return self._excl

    def evidence_tables(self):
        def failures():
            for s in self.subjects:
                with open(ROOT / rec_path(s, "q01") / "failures.jsonl") as f:
                    for line in f:
                        r = json.loads(line)
                        if set(r) - set(FAILURE_FIELDS):
                            raise ValueError(f"{s}: unexpected failure fields {sorted(set(r) - set(FAILURE_FIELDS))}")
                        yield {k: r.get(k, "") for k in FAILURE_FIELDS}
        return {"authors_windows.csv": (WINDOW_FIELDS, self._window_rows),
                "assessment_failure_samples.csv": (FAILURE_FIELDS, failures())}

    def limitations(self, entries):
        lim = {flag: rp.count_flag(entries, flag) for flag in LIMITATION_TEXT}
        ab03 = [e for e in entries if e["rec"] == "AB03/side_shuffle_1"]
        ab03_failed = [e for e in ab03 if e["overall"] == rp.FAILED]
        samples = collections.Counter()
        for e in ab03_failed:
            for c, v in e["failed_samples"].items():
                samples[c] += sum(v.values())
        n_est = sum(1 for r in self.recordings if r["mass_note_key"] == "rescaled_estimated")
        n_exact = sum(1 for r in self.recordings if r["mass_note_key"] == "rescaled_exact")
        out = [{"id": "ab03_side_shuffle_1_foot_cop", "title": "AB03 side_shuffle_1 foot-frame pressure point",
                "text": ("The plate pressure point of AB03 side_shuffle_1 lies about 0.5 m sideways of the marker foot at high load "
                         "(0.53 to 0.65 m left foot, 0.27 to 0.69 m right foot): a plate/marker mismatch, not toe-out; the source "
                         "geometry is not labelled. The values are present in the full variant with the assessment failure "
                         "recorded, and the failing observations are left out of the filtered variant. They are not set to missing."),
                "observations_in_recording": len(ab03), "failed_observations": len(ab03_failed),
                "failed_observations_by_type": dict(collections.Counter(e["type"] for e in ab03_failed)),
                "failed_samples_by_channel": dict(samples),
                "observations_with_foot_frame_cop_held": sum(1 for e in ab03 if e["attributes"].get("foot_cop_held")),
                "in_filtered_variant": len(ab03) - len(ab03_failed)}]
        titles = [("step_up_cop_held", "Step-up foot-frame pressure point held"), ("curb_up_cop_held", "curb_up foot-frame pressure point held"),
                  ("ab07_right_foot_offset", "AB07 right-foot marker offset"), ("mass_estimated", "Estimated mass factors"),
                  ("ab09_divisor", "AB09 divisor"), ("nm_rerun_limit", "N*m re-run limit"),
                  ("window_span_both_legs", "Window spans exported for both legs"),
                  ("shuffle_not_steady_walking", "Shuffle cycles filed as level_walking"),
                  ("unlabelled_walking_under_functional_task", "Walking cycles filed as functional_task"),
                  ("run_label_check", "Cycles labelled run (2.0 and 2.5 m/s)")]
        for flag, title in titles:
            x = {"id": flag, "title": title, "text": LIMITATION_TEXT[flag], **lim[flag]}
            if flag == "mass_estimated":
                x["recordings_from_recordings_jsonl"] = n_est
            if flag == "nm_rerun_limit":
                x["recordings_from_recordings_jsonl"] = n_exact
            if flag == "window_span_both_legs":
                x["spans"] = lim[flag]["observations"] // 2
            out.append(x)
        return out

    def readme_sections(self):
        return [("Foot-frame centre of pressure (corrected note)", CORRECTED_COP_TEXT),
                ("Where the data come from",
                 "Georgia Tech 2023 export (GT23-E01) with the 13 recordings re-exported in GT23-E02 substituted, and the single "
                 "structured assessment GT23-Q01 v2 (profile gt23_q01_coarse_limits_v2: coarse physical limits written before any "
                 "GT23 data were read; draft, not approved reference ranges). Decision D-GT23-R01-1 = B: strides, movements and "
                 "continuous recordings in separate files, not split per participant. Ankle angle zero offset is unverified.")]

    def extra_checks(self, ctx):
        counts, entries = ctx["counts"], ctx["entries"]
        keys = {e["key"] for e in entries}
        missing = [f"{w['subject']}: {w['file']}#{w['row']} names {o}" for w in self.windows if w["fate"] == "exported"
                   for o in w["observations"] if tuple(o.partition("|")[::2]) not in keys]
        replaced_ids = {f"{s}/{n}" for s, names in self.replaced.items() for n in names}
        e02_expected = sum(1 for e in entries if e["rec"] in replaced_ids)
        n_windows = len(self.windows)
        n_exported = sum(1 for w in self.windows if w["fate"] == "exported")
        checks = [
            ("G1", "every exported authors window names only released observations", [], missing),
            ("G2", "authors windows: total = exported + not exported; the not-exported ones are all in exclusions.csv",
             n_windows - n_exported, ctx["by_kind"].get("authors_window_not_exported", 0)),
            ("G3", "E02 supplied exactly the observations of the recordings it replaced, and no E01 row of those recordings was kept",
             e02_expected, ctx["part_observations"].get("GT23-E02", 0)),
            ("G4", "E01 and E02 agree on authors windows, export exclusions and recording lists for the replaced recordings",
             [], self.problems),
        ]
        if self.stage == "full":
            full = counts["full"]
            seen = {"phase_rows": full["phase_rows"], "time_rows": full["time_rows"], "phase_observations": full["phase_observations"],
                    "continuous_recordings": full["time_observations"], "observations": counts["observations_full"],
                    "failed": counts["failed_observations"], "export_exclusions": ctx["by_kind"].get("export_exclusion", 0),
                    "authors_windows_not_exported": ctx["by_kind"].get("authors_window_not_exported", 0),
                    "authors_windows_exported": n_exported,
                    "estimated_mass_recordings": sum(1 for r in self.recordings if r["mass_note_key"] == "rescaled_estimated"),
                    "exact_mass_recordings": sum(1 for r in self.recordings if r["mass_note_key"] == "rescaled_exact"),
                    "recordings_replaced_by_e02": len(replaced_ids)}
            checks += [("G5." + k, f"{k} equals the verified chain total", v, seen[k]) for k, v in EXPECTED_FULL.items()]
        return checks


# ------------------------------------------------------------------ job
def stage_subjects(stage):
    return list(PILOT_SUBJECTS) if stage == "pilot" else list(SUBJECTS)


def stage_paths(stage):
    return {"job_id": f"{TASK_ID}-{stage}-{VERSION}",
            "spec": f"{AUDITS}/gt23-r01-{stage}-spec-{VERSION}.json",
            "output_root": f"{BASE}/gt23_r01_review_{stage}_{VERSION}" if stage == "pilot" else f"{BASE}/gt23_r01_review_{VERSION}",
            "receipt": f"{AUDITS}/gt23-r01-{stage}-launcher-receipt-{VERSION}.json"}


def build_spec(stage, pilot_receipt=None):
    p = stage_paths(stage)
    cmd = ["python3", RUNNER, "run", "--output-root", p["output_root"], "--stage", stage,
           "--subjects", ",".join(stage_subjects(stage))]
    bindings = bound_files()
    if stage == "full":
        cmd += ["--pilot-receipt", pilot_receipt]
        bindings[pilot_receipt] = rp.sha256_file(ROOT / pilot_receipt)
    return {"job_id": p["job_id"], "command": cmd, "cwd": str(ROOT), "output_root": p["output_root"],
            "receipt_path": p["receipt"], "bindings": bindings,
            "timeout_seconds": 3600, "kill_after_seconds": 30, "poll_seconds": 15,
            "startup_memory_mib": {"linux": 3584, "windows": 2816},
            "runtime_memory_mib": {"linux": 2048, "windows": 2048},
            "disk_admission": [{"path": p["output_root"], "min_free_mib": 25 * 1024 if stage == "full" else 8 * 1024}],
            "expected_output_names": ["manifest.json"], "address_space_mib": ADDRESS_SPACE_MIB}


def plan(stage, pilot_receipt=None):
    from contributor_tools.guarded_launcher import validate_spec
    spec = build_spec(stage, pilot_receipt)
    validate_spec(spec)
    path = ROOT / stage_paths(stage)["spec"]
    with path.open("x", encoding="utf-8") as f:
        f.write(json.dumps(spec, indent=1) + "\n")
    print(json.dumps({"spec": str(path), "sha256": rp.sha256_file(path)}))


def check_pilot(rel):
    """A full run needs a clean pilot receipt of the same bound runner and shared builder on the pilot participants."""
    r = json.loads((ROOT / rel).read_text())
    if r.get("status") != "completed" or r.get("clean_success") is not True:
        raise SystemExit("refused: the pilot receipt is not a clean completed run")
    cmd = r["spec"]["command"]
    if "--stage" not in cmd or cmd[cmd.index("--stage") + 1] != "pilot":
        raise SystemExit("refused: the receipt is not a pilot run")
    for f in (RUNNER, SHARED):
        if r["spec"]["bindings"].get(f) != rp.sha256_file(ROOT / f):
            raise SystemExit(f"refused: the pilot ran different code than the current {f}")


def run(args):
    rp.assert_guarded(ADDRESS_SPACE_MIB)
    subjects = args.subjects.split(",")
    if subjects != stage_subjects(args.stage):
        raise SystemExit("refused: --subjects are not the pilot pair or the 12 participants")
    if args.stage == "full":
        if not args.pilot_receipt:
            raise SystemExit("refused: a full run needs --pilot-receipt")
        check_pilot(args.pilot_receipt)
    rp.pin_arrow()
    started = time.time()
    adapter = GT23Adapter(subjects, args.stage)
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
