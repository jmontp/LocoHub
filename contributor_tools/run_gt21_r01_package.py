#!/usr/bin/env python3
"""GT21-R01 (v1): build the local Georgia Tech 2021 review package with the shared streaming builder (package only).

This file is the GT21 adapter and its launcher interface. The package layout and the builder are shared by every dataset:
contributor_tools/common/release_package.py, layout in contributor_tools/DATA_CONTRACT.md ("Release package"). What is
GT21-specific here: the input roots and their hash checks against the launcher receipts, the export exclusions, the
structured assessment (GT21-Q01) in package form, the limitation entries and the power check.

Scope: the 22 participants of the GT21-RB07 export (phase table and time table, one phase file and one time file per variant,
not split per participant, as GT23-R01 under D-GT23-R01-1 = B). full = every exported observation; filtered = full minus the
observations the assessment marked failed (coarse limits GT21-Q01, same numbers as UM21 and GT23); every exclusion is in
exclusions.csv (upstream authors-rule and recording exclusions of the export, assessment failures).

Power rule (D-REF-5): power = published moment x LocoHub joint speed. The GT21 export already follows it (its README says so,
and a probe of AB06 found zero difference), so this adapter does NOT change any value. A read-only part transform checks every
row of every export file against moment x joint speed and the builder check G6 requires zero deviations; if the export did
not follow the rule the build fails and nothing is published.

Inputs (all hash-checked against the clean launcher receipts of the jobs that wrote them):
  GT21-RB07 export roots   gt21_rb07_export_ABxx   (phase.parquet, time.parquet, observations/exclusions/recordings.jsonl)
  GT21-Q01 batch roots     gt21_q01_batch_b1..b6_v2/ABxx (assessment.jsonl, failures.jsonl, assessment.json)

Nothing is repaired, resampled, filled or re-labelled. Run only through contributor_tools.guarded_launcher (one worker, nice 19,
768 MiB address space). scientific_approval is false.
"""
from __future__ import annotations

import os
for _key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_key, "1")
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")  # must precede pyarrow (768 MiB address-space cap)
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
    """Load a shared module by path (importing contributor_tools.common would pull in pandas, scipy and yaml)."""
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


SHARED = "contributor_tools/common/release_package.py"
JOINT_POWER = "contributor_tools/common/joint_power.py"
rp = _load("release_package", SHARED)
jp = _load("joint_power", JOINT_POWER)

TASK_ID = "GT21-R01"
RUNNER = "contributor_tools/run_gt21_r01_package.py"
Q01_RUNNER = "contributor_tools/run_gt21_q01_assessment.py"
VERSION = "v1"
ATTEMPT = "a6"  # job file names only
BASE = "converted_datasets/reconversion_v2"
AUDITS = "docs/quality/audits"
SUBJECTS = ("AB06", "AB07", "AB08", "AB09", "AB10", "AB11", "AB12", "AB13", "AB14", "AB15", "AB16", "AB17", "AB18", "AB19",
            "AB20", "AB21", "AB23", "AB24", "AB25", "AB27", "AB28", "AB30")
PILOT_SUBJECTS = ("AB12", "AB27")  # AB12: left strides without toe-off, 12 short left stances, plate dropout; AB27: held right thigh
BATCHES = {"b1": SUBJECTS[0:4], "b2": SUBJECTS[4:8], "b3": SUBJECTS[8:12], "b4": SUBJECTS[12:16],
           "b5": ("AB23", "AB24", "AB25", "AB27"), "b6": ("AB28", "AB30")}
assert [s for b in BATCHES.values() for s in b] == list(SUBJECTS)
EXPORT_RECEIPT = AUDITS + "/gt21-rb07-export-{}-launcher-receipt.json"
Q01_RECEIPT = AUDITS + "/gt21-q01-batch_{}_v2-launcher-receipt.json"
Q01_SUMMARY = AUDITS + "/gt21-q01-summary.json"
CHAIN_RECEIPTS = (AUDITS + "/gt21-q01-summary-launcher-receipt.json", AUDITS + "/gt21-q01-readback_v3-launcher-receipt.json")
HANDOFFS = tuple(f"docs/maintainers/handoffs/{n}.json" for n in ("GT21-Q01", "GT21-Q01-verify", "GT21-RB07", "GT21-RB07-verify"))
ADDRESS_SPACE_MIB = 768
EXPORT_FILES = ("phase.parquet", "time.parquet", "observations.jsonl", "exclusions.jsonl", "recordings.jsonl", "README.md",
                "run_summary.json")
Q01_FILES = ("assessment.json", "assessment.jsonl", "failures.jsonl")
FAILURE_FIELDS = ["observation_id", "reference_side", "table", "channel", "limit", "sample_index", "phase_percent", "time_s", "mapped_from",
                  "value", "reason"]
POWER_CHECK_FIELDS = ["table", "power_column", "rows", "rows_power_finite", "rows_new_finite", "rows_deviating"]

EXPECTED_FULL = {"phase_rows": 12247050, "time_rows": 14415683, "phase_observations": 81647, "continuous_recordings": 3146,
                 "observations": 84793, "failed": 1246, "failed_phase": 502, "failed_time": 744, "export_exclusions": 25721,
                 "exclusions_authors_rule_discard": 23393, "exclusions_authors_rule_case_not_found": 2076,
                 "exclusions_recording_not_converted_in_pass": 251, "exclusions_recording_excluded_marker_fit": 1}

JOINTS = ("hip_flexion", "knee_flexion", "ankle_dorsiflexion")
POWER_SPECS = {t: tuple(jp.PowerSpec(f"{j}_power_{sd}_W_kg", f"{j}_moment_{sd}_Nm_kg", ((f"{j}_velocity_{sd}_rad_s", 1),))
                        for sd in sides for j in JOINTS)
               for t, sides in (("phase", ("ipsi", "contra")), ("time", ("left", "right")))}
POWER_COLUMNS = {t: tuple(x.power for x in v) for t, v in POWER_SPECS.items()}
POWER_TOLERANCE = 1e-12  # relative; the export computes the same float64 product, so the expected difference is 0

PREVIEW_COLUMNS = ("pelvis_sagittal_angle_rad", "thigh_sagittal_angle_ipsi_rad", "shank_sagittal_angle_ipsi_rad",
                   "foot_sagittal_angle_ipsi_rad", "hip_flexion_angle_ipsi_rad", "knee_flexion_angle_ipsi_rad",
                   "ankle_dorsiflexion_angle_ipsi_rad", "hip_flexion_moment_ipsi_Nm_kg", "knee_flexion_moment_ipsi_Nm_kg",
                   "ankle_dorsiflexion_moment_ipsi_Nm_kg", "grf_vertical_ipsi_BW", "cop_anterior_ipsi_m")
UNCHECKED_FAMILIES = ("joint velocities", "joint moments", "joint powers (moment times joint speed, not limit-checked)",
                      "ground reaction forces (body weight units)", "foot-frame centre of pressure beyond 0.5 m forward and "
                      "0.3 m up or sideways (only that coarse limit is checked)",
                      "plane glitch of the leg plane (not computable from the export)")

CORRECTED_COP_TEXT = (
    "Centre of pressure (foot frame), as defined by the 24 November 2026 standard (docs/reference/index.md): the centre of "
    "pressure is expressed in the ankle frame, which moves with the foot, within that leg's side-view plane, with the origin "
    "100 mm forward of the ankle joint centre along the foot direction. The Georgia Tech 2021 export carries this definition "
    "as written in its README; this package does not change any value.")

LIMITATION_TEXT = {
    "held_frames_in_angles": ("Held frames: in these observations some frames have no angle (the marker fit was bad or a marker "
                              "was missing), so angles, speeds, power and the pressure point of that leg are missing there. "
                              "Nothing is filled. The share of held frames is in task_info (geometry_held_fraction)."),
    "plate_dropout_samples": ("Plate dropout flag: in these observations some samples have a vertical force of 0 while the "
                              "ankle moment is above 0.3 N*m/kg, which looks like a force plate that dropped out. The samples "
                              "are flagged only; they are not removed and the observation is not failed for it."),
    "early_source_heel_strike_short_left_stance": ("Early source heel strikes: in 18 left treadmill strides the source heel "
                                                   "strike falls while the left foot is still unloading from the previous "
                                                   "step, so the stance is only 2 to 5 samples long. They are kept and flagged; "
                                                   "the heel-strike timing is a source question that is not resolved. Two more "
                                                   "listed short stances were left out by the authors' rule and are in "
                                                   "exclusions.csv."),
    "left_stance_unavailable_no_toe_off": ("Two left treadmill strides have no toe-off: the left belt force never falls below "
                                           "20 N after the heel strike inside the stride, so their stance fields are empty "
                                           "(unavailable). Nothing was invented."),
    "left_treadmill_stance_from_belt_force": ("Left treadmill toe-off was rebuilt: the source copies the right foot's toe-off "
                                              "into the left foot in all treadmill recordings, so the left toe-off here is the "
                                              "first sample after the left heel strike where the left belt vertical force is "
                                              "below 20 N. The same rule applied to the right foot reproduces the source toe-off "
                                              "with a median difference of 0 ms, a 95th percentile of 15 ms and a worst case of "
                                              "195 ms (20,447 strides). Only the left stance fields changed; values of all "
                                              "columns are unchanged."),
    "incomplete_stance_force": ("Stance force is masked: where no plate carries 20 N under the foot during stance, force, "
                                "moments, power and the pressure point are missing rather than zero. This is a measurement "
                                "limit of the source; at least half of the stance samples are missing in these observations."),
    "authors_rule_extended_to_left_leg": ("Left-leg strides use the authors' stride rule, which they published for the right "
                                          "leg only; the same rule was applied to the left leg and flagged."),
    "ab27_right_thigh_held_frames": ("AB27 right thigh: the thigh marker leaves the rigid thigh in about 22 percent of right-leg "
                                     "frames, so those frames are held (angles, speeds, power and pressure point of that leg are "
                                     "missing); moments and forces are kept."),
    "ab28_pelvis_angle_offset": ("AB28 pelvis angle: the marker pelvis sagittal angle is about -24 degrees in every mode, while "
                                 "other participants show -4 to -18 degrees. It is consistent within the participant (probably "
                                 "marker placement or posture, not a sign error) and was not corrected."),
}
LIMITATION_TITLES = {
    "held_frames_in_angles": "Held frames (angles missing)", "plate_dropout_samples": "Force plate dropout flags",
    "early_source_heel_strike_short_left_stance": "Early source heel strikes (short left stances)",
    "left_stance_unavailable_no_toe_off": "Left strides with no toe-off",
    "left_treadmill_stance_from_belt_force": "Left treadmill toe-off rebuilt from belt force",
    "incomplete_stance_force": "Stance force masked (missing, not zero)",
    "authors_rule_extended_to_left_leg": "Authors' stride rule applied to the left leg",
    "ab27_right_thigh_held_frames": "AB27 right thigh held frames", "ab28_pelvis_angle_offset": "AB28 pelvis angle offset"}
STATIC_LIMITATIONS = (
    ("p1_unchecked", "Plane glitch (P1) not checked",
     "Whether a leg plane jumps away from the walking direction (rule P1) could not be checked, because the export has no "
     "per-frame plane. Every observation is therefore 'not checked' for P1; this is never a pass."),
    ("ankle_zero_offset_unreviewed", "Ankle failures may reflect an unreviewed zero offset",
     "The ankle angle is the difference of the foot and shank angles measured against gravity (D-REF-1), and its zero offset has "
     "not been reviewed. Most of the 186 joint-range failures are ankle angles; they may reflect that offset and are not "
     "evidence of measurement errors. The coarse limits are blatant-error limits written before any data were read, not "
     "approved reference ranges."),
    ("source_is_authors_2024_copy", "Source files are the authors' 2024 copy",
     "The source files of all 22 participants come from the authors' 2024 copy, which carries no publisher checksums. A "
     "file-by-file comparison with the checksummed 2021 publisher archive exists for AB17 only (1,464 of 1,466 files identical; "
     "2 ramp joint-moment files differ). For the other 21 participants the source bytes are not checked against the 2021 release."),
    ("power_from_moment_and_speed", "Power is moment times joint speed",
     "Hip, knee and ankle power are the published moment times LocoHub's own joint angular velocity (D-REF-5, 24 November "
     "2026). The export already followed this rule; the build checked every row and found no deviation. Power is missing wherever "
     "the moment or the speed is missing."),
    ("authors_rule_exclusions", "Strides and recordings left out by the export",
     "The export leaves out strides under the authors' rule, steps whose case was not found, steps of recordings that were not "
     "converted, and one recording with too few fitted markers. Every one is a row in exclusions.csv."))


# ------------------------------------------------------------------ small helpers
def read_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f]


def export_path(subject):
    return f"{BASE}/gt21_rb07_export_{subject}"


def q01_path(subject):
    b = next(k for k, v in BATCHES.items() if subject in v)
    return f"{BASE}/gt21_q01_batch_{b}_v2/{subject}", b


def receipt_outputs(rel):
    """{output path: sha256} of a clean completed launcher receipt."""
    r = json.loads((ROOT / rel).read_text())
    if r.get("status") != "completed" or r.get("clean_success") is not True:
        raise ValueError(f"{rel} is not a clean completed run")
    return {o["path"]: o["sha256"] for o in r["outputs"]}


def input_files(subject):
    """{relative path: (receipt path, output name)} for every input file the adapter reads."""
    out = {f"{export_path(subject)}/{n}": (EXPORT_RECEIPT.format(subject), n) for n in EXPORT_FILES}
    qp, b = q01_path(subject)
    out.update({f"{qp}/{n}": (Q01_RECEIPT.format(b), f"{subject}/{n}") for n in Q01_FILES})
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
    b = [RUNNER, SHARED, JOINT_POWER, Q01_RUNNER, Q01_SUMMARY, *CHAIN_RECEIPTS, *HANDOFFS]
    for s in SUBJECTS:
        b.append(EXPORT_RECEIPT.format(s))
    for k in BATCHES:
        b.append(Q01_RECEIPT.format(k))
    return {k: rp.sha256_file(ROOT / k) for k in b}


# ------------------------------------------------------------------ pure rules (tested with synthetic data)
def exclusion_kind(reason):
    """(kind, reason code, detail) of one export exclusion reason."""
    code, _, rest = reason.partition(":")
    code = code.strip()
    if code in ("authors_rule_discard", "authors_rule_case_not_found", "recording_not_converted_in_pass"):
        return code, code, rest.strip()
    if code.startswith("fewer than 3 fit markers"):
        return "recording_excluded_marker_fit", "recording_excluded_marker_fit", reason
    raise ValueError(f"unknown export exclusion reason: {reason!r}")


def export_exclusion_rows(subject, rows):
    out = []
    for x in rows:
        kind, code, detail = exclusion_kind(x["reason"])
        out.append({"exclusion_id": x["step_id"] or f"{x['source_recording_id']}#recording", "observation_id": "", "subject": subject,
                    "source_recording_id": x["source_recording_id"], "reference_side": x["leg"] or "",
                    "stage": "upstream_not_released", "kind": kind, "reason_code": code,
                    "reason": f"left out at export ({x['stage']}): {x['reason']}", "decision": "",
                    "in_full_variant": False, "in_filtered_variant": False, "task": x["mode"], "task_id": "",
                    "start_s": x.get("start_s", ""), "end_s": x.get("end_s", ""), "detail": detail})
    return out


def package_entry(e):
    """A GT21-Q01 assessment line in the package's assessment format (it already is; this checks and copies)."""
    missing = [k for k in rp.ASSESSMENT_REQUIRED if k not in e]
    if missing:
        raise ValueError(f"{e.get('observation_id')}: assessment line lacks {missing}")
    if e["status"] not in (rp.FAILED, rp.NOT_FAILED):
        raise ValueError(f"{e['observation_id']}: unknown status {e['status']!r}")
    return {k: e[k] for k in rp.ASSESSMENT_REQUIRED}


class PowerCheck:
    """Part transform that changes nothing and counts rows where an export power column differs from moment x joint speed."""

    def __init__(self, table):
        self.specs = POWER_SPECS[table]
        self.table = table
        self.acc = {s.power: [0, 0, 0, 0] for s in self.specs}  # rows, power finite, new finite, deviating

    def __call__(self, t):
        import numpy as np
        for s in self.specs:
            src = jp._col(t, s.power)
            new, _ = jp.power_from(jp._col(t, s.moment), jp.joint_velocity(t, s))
            fs, fn = np.isfinite(src), np.isfinite(new)
            both = fs & fn
            dev = int((fs != fn).sum()) + int((np.abs(src[both] - new[both]) > POWER_TOLERANCE * np.maximum(1.0, np.abs(new[both]))).sum())
            a = self.acc[s.power]
            a[0] += t.num_rows; a[1] += int(fs.sum()); a[2] += int(fn.sum()); a[3] += dev
        return t

    def rows(self):
        return [{"table": self.table, "power_column": c, "rows": a[0], "rows_power_finite": a[1], "rows_new_finite": a[2],
                 "rows_deviating": a[3]} for c, a in self.acc.items()]


# ------------------------------------------------------------------ the adapter
class GT21Adapter(rp.ReleaseAdapter):
    dataset_id = "gt21"
    title = "Georgia Tech 2021 review package"
    tables = ("phase", "time")
    preview_columns = PREVIEW_COLUMNS
    unchecked_families = UNCHECKED_FAMILIES
    group_rows = 40000  # larger row groups: 12.2 M + 14.4 M rows at 12,000 per group made the open writers' footers too large for the memory cap
    resident_attribute_keys = ()  # attributes (column ranges, missing-sample ranges) go to assessment.jsonl only; not kept in memory

    def __init__(self, subjects, stage):
        self.subjects, self.stage = list(subjects), stage
        self.release_id = VERSION
        self._inputs, self._bound = {}, {}
        self.summaries, self._excl, self.recordings = {}, [], []
        self.checkers = {t: PowerCheck(t) for t in self.tables}

    def prepare(self):
        """Hash and check every input against its receipt, then load the small evidence files."""
        for s in self.subjects:
            self._inputs.update(verify_inputs(s))
            print(f"{s}: inputs verified against receipts", flush=True)
        self._bound = bound_files()
        for s in self.subjects:
            self.summaries[s] = json.loads((ROOT / export_path(s) / "run_summary.json").read_text())
            self._excl += export_exclusion_rows(s, read_jsonl(ROOT / export_path(s) / "exclusions.jsonl"))
            self.recordings += read_jsonl(ROOT / export_path(s) / "recordings.jsonl")

    def input_hashes(self):
        return self._inputs

    def bound_hashes(self):
        return self._bound

    def lineage_inputs(self):
        h = {k: v for k, v in self._inputs.items() if "/gt21_q01_batch_" in k}
        h[Q01_SUMMARY] = self._bound[Q01_SUMMARY]
        return h

    def table_parts(self, table):
        return [rp.Part(ROOT / export_path(s) / f"{table}.parquet", "GT21-RB07", transform=self.checkers[table])
                for s in self.subjects]

    def assessment_entries(self):
        for s in self.subjects:
            with open(ROOT / q01_path(s)[0] / "assessment.jsonl") as f:
                for line in f:
                    yield package_entry(json.loads(line))

    def exclusion_rows(self):
        return self._excl

    def evidence_tables(self):
        def failures():
            for s in self.subjects:
                with open(ROOT / q01_path(s)[0] / "failures.jsonl") as f:
                    for line in f:
                        r = json.loads(line)
                        if set(r) - set(FAILURE_FIELDS):
                            raise ValueError(f"{s}: unexpected failure fields {sorted(set(r) - set(FAILURE_FIELDS))}")
                        row = {k: ("" if r.get(k) is None else r[k]) for k in FAILURE_FIELDS}
                        if isinstance(row["mapped_from"], dict):
                            row["mapped_from"] = json.dumps(row["mapped_from"], sort_keys=True)
                        yield row
        power = [r for t in self.tables for r in self.checkers[t].rows()]
        return {"assessment_failure_samples.csv": (FAILURE_FIELDS, failures()),
                "power_rule_check.csv": (POWER_CHECK_FIELDS, power)}

    def limitations(self, entries):
        out = []
        for flag in LIMITATION_TEXT:
            out.append({"id": flag, "title": LIMITATION_TITLES[flag], "text": LIMITATION_TEXT[flag], **rp.count_flag(entries, flag)})
        n = len(entries)
        n_fail = sum(1 for e in entries if e["overall"] == rp.FAILED)
        for lid, title, text in STATIC_LIMITATIONS:
            x = {"id": lid, "title": title, "text": text, "observations": n, "in_filtered_variant": n - n_fail}
            if lid == "p1_unchecked":
                x["observations_not_checked"] = n
            if lid == "ankle_zero_offset_unreviewed":
                x["failed_observations_by_cause"] = dict(self._causes(entries))
            if lid == "source_is_authors_2024_copy":
                x["participants"] = len(self.subjects)
                x["participants_compared_with_2021_archive"] = ["AB17"]
            if lid == "power_from_moment_and_speed":
                x["check"] = [r for t in self.tables for r in self.checkers[t].rows()]
            if lid == "authors_rule_exclusions":
                x["export_exclusion_rows"] = len(self._excl)
            out.append(x)
        return out

    @staticmethod
    def _causes(entries):
        import collections
        c = collections.Counter()
        for e in entries:
            if e["overall"] == rp.FAILED:
                for x in e["causes"]:
                    c[x] += 1
        return c

    def readme_sections(self):
        return [("Foot-frame centre of pressure", CORRECTED_COP_TEXT),
                ("Where the data come from",
                 "Georgia Tech 2021 export GT21-RB07 for 22 participants (strides and movements as the phase table, continuous "
                 "recordings as the time table; separate files, not split per participant), and the single structured assessment "
                 "GT21-Q01 (coarse physical limits written before any GT21 data were read, the same numbers as UMich 2021 and "
                 "Georgia Tech 2023; draft, not approved reference ranges). The source files are the authors' 2024 copy. Joint "
                 "angles are differences of segment angles measured against gravity (D-REF-1); their zero offset is unreviewed. "
                 "The left treadmill toe-off was rebuilt from the left belt force (see the limitations)."),
                ("What is not in this package",
                 "Plane glitch (P1) is not checked. Velocities, moments, powers and forces have no limit and are listed as not "
                 "checked. Strides left out by the authors' rule and recordings left out by the export are in exclusions.csv, not "
                 "in either variant.")]

    def extra_checks(self, ctx):
        counts, entries = ctx["counts"], ctx["entries"]
        sums = {k: sum(self.summaries[s][k] for s in self.subjects)
                for k in ("phase_rows", "time_rows", "phase_observations", "continuous_observations", "exclusions")}
        deviating = {r["power_column"]: r["rows_deviating"] for t in self.tables for r in self.checkers[t].rows()}
        checks = [
            ("G1", "observations in the package equal the export run summaries (phase + continuous)",
             sums["phase_observations"] + sums["continuous_observations"], counts["observations_full"]),
            ("G2", "phase and time rows in the full tables equal the export run summaries",
             [sums["phase_rows"], sums["time_rows"]], [counts["full"]["phase_rows"], counts["full"]["time_rows"]]),
            ("G3", "export exclusion rows equal the export run summaries",
             sums["exclusions"], ctx["by_kind"].get("authors_rule_discard", 0) + ctx["by_kind"].get("authors_rule_case_not_found", 0)
             + ctx["by_kind"].get("recording_not_converted_in_pass", 0) + ctx["by_kind"].get("recording_excluded_marker_fit", 0)),
            ("G4", "no export power value deviates from moment x joint speed (D-REF-5), every row of every export file",
             {c: 0 for c in deviating}, deviating),
            ("G5", "every assessed observation has a recording in recordings.jsonl of its participant (exported)",
             [], sorted({e["rec"] for e in entries} - {r["source_recording_id"] for r in self.recordings if r["status"] == "exported"})),
            ("G6", "finite power rows in the written full tables equal the rows where moment and joint speed were both finite",
             {c: sum(a[2] for a in [self.checkers[t].acc[c]]) for t in self.tables for c in POWER_COLUMNS[t]},
             {c: ctx["readback"][("full", t)]["finite"][c] for t in self.tables for c in POWER_COLUMNS[t]}),
        ]
        if self.stage == "full":
            by_table = counts["assessment_failures_by_table"]
            seen = {"phase_rows": counts["full"]["phase_rows"], "time_rows": counts["full"]["time_rows"],
                    "phase_observations": counts["full"]["phase_observations"],
                    "continuous_recordings": counts["full"]["time_observations"], "observations": counts["observations_full"],
                    "failed": counts["failed_observations"], "failed_phase": by_table.get("phase", 0),
                    "failed_time": by_table.get("time", 0), "export_exclusions": sums["exclusions"],
                    **{f"exclusions_{k}": ctx["by_kind"].get(k, 0) for k in
                       ("authors_rule_discard", "authors_rule_case_not_found", "recording_not_converted_in_pass",
                        "recording_excluded_marker_fit")}}
            checks += [("V." + k, f"{k} equals the verified chain total", v, seen[k]) for k, v in EXPECTED_FULL.items()]
        return checks


# ------------------------------------------------------------------ job
def stage_subjects(stage):
    return list(PILOT_SUBJECTS) if stage == "pilot" else list(SUBJECTS)


def stage_paths(stage):
    return {"job_id": f"{TASK_ID}-{stage}-{VERSION}-{ATTEMPT}", "spec": f"{AUDITS}/gt21-r01-{stage}-spec-{VERSION}-{ATTEMPT}.json",
            "output_root": f"{BASE}/gt21_r01_package_pilot_{VERSION}_{ATTEMPT}" if stage == "pilot" else f"{BASE}/gt21_r01_package_{VERSION}",
            "receipt": f"{AUDITS}/gt21-r01-{stage}-launcher-receipt-{VERSION}-{ATTEMPT}.json"}


def build_spec(stage, pilot_receipt=None, full_free_mib=15 * 1024 + 1024):
    p = stage_paths(stage)
    cmd = ["python3", RUNNER, "run", "--output-root", p["output_root"], "--stage", stage,
           "--subjects", ",".join(stage_subjects(stage))]
    b = bound_files()
    if stage == "full":
        cmd += ["--pilot-receipt", pilot_receipt]
        b[pilot_receipt] = rp.sha256_file(ROOT / pilot_receipt)
    return {"job_id": p["job_id"], "command": cmd, "cwd": str(ROOT), "output_root": p["output_root"],
            "receipt_path": p["receipt"], "bindings": b, "timeout_seconds": 3600, "kill_after_seconds": 30, "poll_seconds": 15,
            "startup_memory_mib": {"linux": 3584, "windows": 2816}, "runtime_memory_mib": {"linux": 2048, "windows": 2048},
            "disk_admission": [{"path": p["output_root"], "min_free_mib": full_free_mib if stage == "full" else 4 * 1024}],
            "expected_output_names": ["manifest.json"], "address_space_mib": ADDRESS_SPACE_MIB}


def plan(stage, pilot_receipt=None, full_free_mib=15 * 1024 + 1024):
    from contributor_tools.guarded_launcher import validate_spec
    spec = build_spec(stage, pilot_receipt, full_free_mib)
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
    for f in (RUNNER, SHARED, JOINT_POWER, Q01_RUNNER):
        if r["spec"]["bindings"].get(f) != rp.sha256_file(ROOT / f):
            raise SystemExit(f"refused: the pilot ran different code than the current {f}")


def run(args):
    rp.assert_guarded(ADDRESS_SPACE_MIB)
    subjects = args.subjects.split(",")
    if subjects != stage_subjects(args.stage):
        raise SystemExit("refused: --subjects are not the pilot pair or the 22 participants")
    if args.stage == "full":
        if not args.pilot_receipt:
            raise SystemExit("refused: a full run needs --pilot-receipt")
        check_pilot(args.pilot_receipt)
    rp.pin_arrow()
    started = time.time()
    adapter = GT21Adapter(subjects, args.stage)
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
