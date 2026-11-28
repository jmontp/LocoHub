#!/usr/bin/env python3
"""UM21-R01 v4 (v3 with joint power recomputed, D-REF-5): build the local UMich 2021 treadmill review package with the shared streaming builder.

This file is the UMich 2021 adapter and its launcher interface. The package layout and the builder are shared by every dataset:
contributor_tools/common/release_package.py, layout in contributor_tools/DATA_CONTRACT.md ("Release package"). What is UM21
specific here: the input roots and their hash checks against the launcher receipt, the exclusions inherited from the v2 bundle,
the structured assessment entries (UM21-Q01 v3) and the limitation entries. The legacy builder run_um21_r01_bundle.py (layout
um21_r01_review_v2) is kept as history and is not used.

v4 changes only the three joint power columns (and what the assessment says about them): hip, knee and ankle power are the
published moment times LocoHub's own joint angular velocity (hip = thigh - pelvis speed, knee = thigh - shank speed, ankle =
foot - shank speed, from the package's own segment velocity columns); missing moment or speed gives missing power; source
power values are not carried over. The recomputation is applied through Part.transform with contributor_tools/common/joint_power.py.

Inputs (all hash-checked against the clean launcher receipt of the UM21-Q01 v3 full job before the build):
  UM21-Q01 v3 root   um21_q01v3_full: the composed table parts (one per recording, v2 identity/moments/powers plus S02 v7
                     marker angles, velocities and the foot-frame centre of pressure), the structured assessment
                     (observations.jsonl, failures.jsonl, assessment.json)
  v2 bundle exclusions.csv (the 15 strides outside the stride rule and the 2 sudden-jump strides, judged upstream)

UMich 2021 has no time-indexed export, so the package has a phase table only (tables = phase). Nothing is repaired, resampled,
filled or re-labelled. Run only through contributor_tools.guarded_launcher (one worker, nice 19, 768 MiB address space).
scientific_approval is false.
"""
from __future__ import annotations

import os
for _key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_key, "1")
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")  # must precede pyarrow (768 MiB address-space cap)
import argparse
import csv
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_shared():
    """Load the shared builder by path (importing contributor_tools.common would pull in pandas, scipy and yaml)."""
    path = ROOT / "contributor_tools" / "common" / "release_package.py"
    spec = importlib.util.spec_from_file_location("release_package", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["release_package"] = mod
    spec.loader.exec_module(mod)
    return mod


JOINT_POWER = "contributor_tools/common/joint_power.py"
rp = _load_shared()


def _load_power():
    path = ROOT / JOINT_POWER
    spec = importlib.util.spec_from_file_location("joint_power", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["joint_power"] = mod
    spec.loader.exec_module(mod)
    return mod


jp = _load_power()

TASK_ID = "UM21-R01"
RUNNER = "contributor_tools/run_um21_r01_package.py"
SHARED = "contributor_tools/common/release_package.py"
Q01_RUNNER = "contributor_tools/run_um21_q01v3_assessment.py"
VERSION = "v4"
ATTEMPT = "a1"  # job file names only; a1 stopped before reading data (receipt root comparison); a2 not clean (a foreign worker started during the run) and text edited after
BASE = "converted_datasets/reconversion_v2"
AUDITS = "docs/quality/audits"
Q01_ROOT = f"{BASE}/um21_q01v3_full"
Q01_RECEIPT = f"{AUDITS}/um21-q01v3-full-launcher-receipt.json"
S02_RECEIPT = f"{AUDITS}/um21-s02-full-launcher-receipt-v7.json"
V2_EXCLUSIONS = f"{BASE}/um21_r01_review_v2/exclusions.csv"
HANDOFFS = ("docs/maintainers/handoffs/UM21-STD-plan.json", "docs/maintainers/handoffs/UM21-S02-verify.json")
PILOT_RECORDINGS = ("AB01/i0", "AB03/i10", "AB04/i0", "AB07/d10", "AB08/i0", "AB10/d5")
ADDRESS_SPACE_MIB = 768
SOURCE_LABEL = "UM21-Q01v3 (v2 identity, moments, powers + S02 v7 angles and centre of pressure)"

EXPECTED_FULL = {"observations": 7545, "phase_rows": 1131750, "recordings": 44, "upstream_stride_rule_exclusions": 15,
                 "sudden_jump_exclusions": 2, "upstream_total_observations": 7562, "cop_legs_published": 60,
                 "cop_legs_held": 28}

POWER_SPECS = (
    jp.PowerSpec("hip_flexion_power_ipsi_W_kg", "hip_flexion_moment_ipsi_Nm_kg",
                 (("thigh_sagittal_velocity_ipsi_rad_s", 1), ("pelvis_sagittal_velocity_rad_s", -1))),
    jp.PowerSpec("knee_flexion_power_ipsi_W_kg", "knee_flexion_moment_ipsi_Nm_kg",
                 (("thigh_sagittal_velocity_ipsi_rad_s", 1), ("shank_sagittal_velocity_ipsi_rad_s", -1))),
    jp.PowerSpec("ankle_dorsiflexion_power_ipsi_W_kg", "ankle_dorsiflexion_moment_ipsi_Nm_kg",
                 (("foot_sagittal_velocity_ipsi_rad_s", 1), ("shank_sagittal_velocity_ipsi_rad_s", -1))))
POWER_COLUMNS = tuple(x.power for x in POWER_SPECS)
POWER_MISSING_REASON = "power missing: the moment or the joint speed is missing in this observation"
GAP_FIELDS = ["power_column", "observations", "observations_compared", "median_nrms", "p90_nrms", "pooled_nrms", "rows_both_finite",
              "rows_source_finite", "rows_new_finite", "rows_source_only_finite", "rows_new_only_finite",
              "observations_source_finite_new_all_missing", "observations_source_all_missing_new_finite"]

PREVIEW_COLUMNS = ("pelvis_sagittal_angle_rad", "thigh_sagittal_angle_ipsi_rad", "shank_sagittal_angle_ipsi_rad",
                   "foot_sagittal_angle_ipsi_rad", "hip_flexion_angle_ipsi_rad", "knee_flexion_angle_ipsi_rad",
                   "ankle_dorsiflexion_angle_ipsi_rad", "hip_flexion_moment_ipsi_Nm_kg", "knee_flexion_moment_ipsi_Nm_kg",
                   "ankle_dorsiflexion_moment_ipsi_Nm_kg", "cop_anterior_ipsi_m", "cop_vertical_ipsi_m", "cop_lateral_ipsi_m")
UNCHECKED_FAMILIES = ("joint velocities", "joint moments", "joint powers (recomputed as moment times speed, not limit-checked)",
                      "range of pelvis, thigh, shank and foot angles (jump check only)")
COP_FIELDS = ["recording", "leg", "status", "strides", "reasons", "holdout_ankle_moment_r", "toe_off_within_4cm_fraction",
              "plate_assignment_same_plate_fraction", "loaded_fraction", "pending_by_ruling", "label"]
GLITCH_FIELDS = ["recording", "leg", "frames_over_60_deg", "finite_plane_frames", "max_plane_deviation_deg", "strides_held"]
FAILURE_FIELDS = ["observation_id", "reference_side", "table", "channel", "limit", "sample_index", "frame", "value", "reason"]

CORRECTED_COP_TEXT = (
    "Centre of pressure (foot frame), as defined by the 24 November 2026 standard (docs/reference/index.md): the centre of "
    "pressure is expressed in the ankle frame, which moves with the foot, within that leg's side-view plane. The foot direction "
    "is the leg-plane forward direction rotated by the foot angle (foot = shank + ankle). The origin is 100 mm forward of the "
    "ankle joint centre along that foot direction; forward is along it, up is perpendicular to it within the plane, and sideways "
    "is perpendicular to the leg plane, outward from that leg. The UMich 2021 source does not record the force-plate "
    "position in the laboratory, so the plate position is estimated from the data (axis and sign from the ankle "
    "path, belt tilt from the condition slope, forward shift fitted to the hip and knee moments, up shift from the foot-on-belt "
    "rule, sideways shift from the mean foot position). The column is therefore labelled 'estimated plate position'; it is not "
    "a measured foot-frame pressure point. A leg publishes it only if the held-out ankle moment is reproduced (r >= 0.95), the "
    "toe-off end of the pressure point lies within 4 cm of the toe marker in at least 95 percent of strides (checked at 0.2 body "
    "weight), and the plate is loaded at the leg's heel strikes in at least 95 percent of them. Each leg is judged and published on "
    "its own (D-UM21-S02-1 = A, D-UM21-S02-2 = A). Every other leg has the three columns present but missing, with the reason in "
    "held_signals.")

LIMITATION_TEXT = {
    "moments_from_v2": ("Moments are carried from the earlier v2 bundle unchanged. They were not recomputed from the new "
                        "marker angles (moments do not depend on the angles)."),
    "power_from_moment_and_speed": ("Hip, knee and ankle power are the published moment times LocoHub's own joint angular "
                                    "velocity (hip = thigh minus pelvis speed, knee = thigh minus shank speed, ankle = foot minus "
                                    "shank speed; knee moment is the flexor moment, knee speed is flexion-positive), as decided on "
                                    "24 November 2026 (D-REF-5). The v2 source power values are not carried over. Power is missing "
                                    "wherever the moment or a speed is missing; held centre of pressure does not hold power."),
    "knee_marker_labels_swapped": ("Knee marker names: in this source the marker named KNEM lies on the lateral side of the knee "
                                   "and KNE on the medial side (checked on every leg of every recording; lateral minus medial "
                                   "distance from the pelvis midline at least 0.110 m). This is the reverse of the usual reading of the "
                                   "names; the per-leg side-view plane is built with that assignment. Evidence is marker positions "
                                   "only; no photograph or marker-set document was seen."),
    "cop_estimated_plate_position": ("The published centre of pressure is built on an estimated plate position (fitted from the "
                                     "data, not measured). It passed the gate for its leg but is not an independently measured "
                                     "foot-frame pressure point."),
    "cop_held_leg": ("Centre of pressure held: the three foot-frame columns are present but missing for this leg because it did not "
                     "pass the gate (reason in held_signals)."),
    "cop_held_pending_ruling": ("Held-back data stays pending as it is (ruling): the i10 recordings of AB01, AB02 and AB03, "
                                "AB04/d10 and AB10/d5 are not investigated further; their centre of pressure stays held."),
    "angle_columns_missing_in_stride": ("Some angle columns are missing for this stride because a marker is not visible in its "
                                        "window, or the pelvis disagrees with the marker pelvis by more than 1 degree; nothing "
                                        "is filled."),
    "plane_glitch_hold": (f"Plane-glitch hold (rule P1): a frame in this stride's window has a leg plane more than 60 degrees "
                          "from the walking direction, so the leg's plane-dependent columns are held."),
}
LIMITATION_TITLES = {
    "moments_from_v2": "Moments carried from the v2 bundle", "power_from_moment_and_speed": "Power recomputed as moment times joint speed", "knee_marker_labels_swapped": "Knee marker names reversed in the source",
    "cop_estimated_plate_position": "Centre of pressure on an estimated plate position",
    "cop_held_leg": "Centre of pressure held (leg did not pass the gate)",
    "cop_held_pending_ruling": "Held-back recordings left pending",
    "angle_columns_missing_in_stride": "Angle columns missing for a stride", "plane_glitch_hold": "Plane-glitch hold (rule P1)"}


def _obsolete(reason):
    return reason.startswith("held: sign unsettled")


# ------------------------------------------------------------------ small helpers
def read_jsonl(path):
    with open(path) as f:
        for line in f:
            yield json.loads(line)


def verify_inputs():
    """Hash every output of the Q01 v3 full job and compare it with the clean launcher receipt. Returns {path: sha256}."""
    r = json.loads((ROOT / Q01_RECEIPT).read_text())
    if r.get("status") != "completed" or r.get("clean_success") is not True:
        raise ValueError(f"{Q01_RECEIPT} is not a clean completed run")
    if Path(r["spec"]["output_root"]).resolve() != (ROOT / Q01_ROOT).resolve():
        raise ValueError("the receipt is for another output root")
    hashes = {}
    for o in r["outputs"]:
        rel = f"{Q01_ROOT}/{o['path']}"
        h = rp.sha256_file(ROOT / rel)
        if h != o["sha256"]:
            raise ValueError(f"{rel} differs from the hash in {Q01_RECEIPT}")
        hashes[rel] = h
    return hashes


def bound_files():
    b = [RUNNER, SHARED, JOINT_POWER, Q01_RUNNER, Q01_RECEIPT, S02_RECEIPT, V2_EXCLUSIONS, *HANDOFFS]
    return {k: rp.sha256_file(ROOT / k) for k in b}


def recording_id(short):
    sub, cond = short.split("/")
    return f"um21:Streaming/{sub}/Tread/{cond}"


# ------------------------------------------------------------------ pure rules (tested with synthetic data)
def inherited_exclusion_rows(v2_rows):
    """Exclusion rows from the v2 bundle's exclusions.csv. The assessment-based row of v2 (q01_limit_failed) is dropped: the v3
    assessment is the only source of filtered_variant_only rows."""
    out = []
    for x in v2_rows:
        if x["stage"] == "filtered_variant_only":
            continue
        if x["reason_code"] == "t04_2_outside_stride_rule":
            kind, extra = "upstream_stride_rule", ""
        elif x["reason_code"] == "c03_2_sudden_jump":
            kind = "upstream_sudden_jump"
            extra = ("; judged on the earlier Vicon ankle angle in the v2 bundle and not re-evaluated on the marker angles "
                     "(the marker-angle table covers the v2 observation set)")
        else:
            raise ValueError(f"unknown v2 exclusion reason {x['reason_code']!r}")
        sub = x["recording"].split("/")[0]
        out.append({"exclusion_id": x["observation_id"], "observation_id": x["observation_id"], "subject": f"UM21_{sub}",
                    "source_recording_id": recording_id(x["recording"]), "reference_side": x["reference_side"],
                    "stage": x["stage"], "kind": kind, "reason_code": x["reason_code"], "reason": x["reason"] + extra,
                    "decision": x["decision"], "in_full_variant": False, "in_filtered_variant": False, "task": "",
                    "task_id": "", "start_s": "", "end_s": "", "detail": "frames are in the observation id"})
    return out


def cop_leg_rows(assessment):
    rows = []
    for status, legs in (("published", assessment["cop_legs"]["published"]), ("held", assessment["cop_legs"]["held"])):
        for l in legs:
            m = l["cop_metrics"]
            rows.append({"recording": l["recording"], "leg": l["leg"], "status": status, "strides": l["strides"],
                         "reasons": "; ".join(l.get("cop_reasons", [])), "holdout_ankle_moment_r": m["holdout_r"],
                         "toe_off_within_4cm_fraction": m["toe_within_4cm_fraction"],
                         "plate_assignment_same_plate_fraction": m["plate_assignment_same_plate_fraction"],
                         "loaded_fraction": m["loaded_fraction"],
                         "pending_by_ruling": l["recording"] in assessment["cop_legs"]["pending_by_ruling_recordings"],
                         "label": assessment["cop_legs"]["label"] if status == "published" else ""})
    return sorted(rows, key=lambda r: (r["recording"], r["leg"]))


def glitch_leg_rows(assessment):
    held = {}
    for s in assessment["plane_glitch_rule"]["strides_held"]:
        held[(s["recording"], s["leg"])] = held.get((s["recording"], s["leg"]), 0) + 1
    return [{"recording": l["recording"], "leg": l["leg"], "frames_over_60_deg": l["frames_over_60_deg"],
             "finite_plane_frames": l["finite_plane_frames"], "max_plane_deviation_deg": l["max_plane_deviation_deg"],
             "strides_held": held.get((l["recording"], l["leg"]), 0)} for l in assessment["plane_glitch_rule"]["legs"]]


def published_leg_count(entries):
    """(legs with at least one stride whose centre of pressure is published, legs with every stride held) from entries."""
    pub, held, seen = set(), set(), set()
    for e in entries:
        k = (e["rec"], e["key"][1])
        seen.add(k)
        st = e["attributes"].get("cop_status")
        if st == "published":
            pub.add(k)
        elif st == "held":
            held.add(k)
    return len(pub), len(held - pub), len(seen)


# ------------------------------------------------------------------ the adapter
class UM21Adapter(rp.ReleaseAdapter):
    dataset_id = "um21"
    title = "UMich 2021 treadmill review package"
    tables = ("phase",)
    preview_columns = PREVIEW_COLUMNS
    unchecked_families = UNCHECKED_FAMILIES

    def __init__(self, recordings, stage):
        self.recordings, self.stage = list(recordings), stage
        self.release_id = VERSION
        self._inputs, self._bound = {}, {}
        self.assessment, self._v2_rows = {}, []
        self.stats, self.presence = jp.GapStats(), {}

    def prepare(self):
        self._inputs = verify_inputs()
        self._bound = bound_files()
        self._inputs[V2_EXCLUSIONS] = self._bound[V2_EXCLUSIONS]
        self.assessment = json.loads((ROOT / Q01_ROOT / "assessment.json").read_text())
        with open(ROOT / V2_EXCLUSIONS, newline="") as f:
            self._v2_rows = list(csv.DictReader(f))
        have = set(self.assessment["per_record"])
        if not set(self.recordings) <= have:
            raise ValueError("a requested recording is not in the Q01 v3 job")
        print("inputs verified against the Q01 v3 receipt", flush=True)
        self.presence = jp.merge_presence([jp.scan_presence(p.path, POWER_SPECS) for p in self.table_parts("phase")])
        print(f"power presence scanned for {len(self.presence)} observations", flush=True)

    def input_hashes(self):
        return self._inputs

    def bound_hashes(self):
        return self._bound

    def lineage_inputs(self):
        return {k: v for k, v in self._inputs.items() if k.endswith(("observations.jsonl", "failures.jsonl", "assessment.json"))}

    def table_parts(self, table):
        return [rp.Part(ROOT / Q01_ROOT / "parts" / f"{r.replace('/', '_')}.parquet", SOURCE_LABEL, transform=self._transform)
                for r in self.recordings]

    def _transform(self, t):
        t = jp.recompute(t, POWER_SPECS, self.stats)
        return jp.rewrite_held_column(t, POWER_COLUMNS, self.presence, POWER_MISSING_REASON, json.dumps, _obsolete)

    def _selected(self, oid_recording):
        return oid_recording in {recording_id(r) for r in self.recordings}   # small set (at most 44)

    def assessment_entries(self):
        for e in read_jsonl(ROOT / Q01_ROOT / "observations.jsonl"):
            if self._selected(e["source_recording_id"]):
                yield self._power_entry(e)

    def _power_entry(self, e):
        pres = self.presence[(e["observation_id"], e["reference_side"])]
        e = dict(e)
        e["held_signals"] = jp.adjust_held(e["held_signals"], pres, POWER_COLUMNS, POWER_MISSING_REASON, _obsolete)
        e["channel_states"] = jp.adjust_states(e["channel_states"], pres, POWER_COLUMNS, "unchecked", "unchecked_all_missing")
        lims = [x for x in e["limitations"] if x not in ("moments_powers_from_v2", "powers_held_sign_unsettled")]
        e["limitations"] = ["moments_from_v2", "power_from_moment_and_speed"] + lims
        return e

    def exclusion_rows(self):
        return [x for x in inherited_exclusion_rows(self._v2_rows) if self._selected(x["source_recording_id"])]

    def evidence_tables(self):
        def failures():
            for x in read_jsonl(ROOT / Q01_ROOT / "failures.jsonl"):
                rec = x["observation_id"].rsplit(":", 4)[0]
                if self._selected(rec):
                    yield {k: x.get(k, "") for k in FAILURE_FIELDS}
        sel = set(self.recordings)
        return {"cop_legs.csv": (COP_FIELDS, [r for r in cop_leg_rows(self.assessment) if r["recording"] in sel]),
                "plane_glitch_legs.csv": (GLITCH_FIELDS, [r for r in glitch_leg_rows(self.assessment) if r["recording"] in sel]),
                "assessment_failure_samples.csv": (FAILURE_FIELDS, failures()),
                "power_recompute_gap.csv": (GAP_FIELDS, [{"power_column": c, **v} for c, v in self.stats.summary().items()])}

    def limitations(self, entries):
        out = []
        n_pub, n_held, n_legs = published_leg_count(entries)
        for flag, text in LIMITATION_TEXT.items():
            x = {"id": flag, "title": LIMITATION_TITLES[flag], "text": text, **rp.count_flag(entries, flag)}
            if flag in ("cop_estimated_plate_position", "cop_held_leg"):
                x["legs_published"], x["legs_held"], x["legs_total"] = n_pub, n_held, n_legs
            if flag == "cop_held_pending_ruling":
                x["recordings_named"] = sorted(self.assessment["cop_legs"]["pending_by_ruling_recordings"])
            if flag == "power_from_moment_and_speed":
                x["gap_source_power_vs_moment_times_speed"] = {
                    "definition": "per observation sqrt(sum (source - new)^2 / sum new^2) over rows where both are finite; median "
                                  "over observations; after the change the gap is zero by construction (checked to 1e-12 by the readback)",
                    **self.stats.summary()}
            out.append(x)
        out.append({"id": "plate_position_fitted", "title": "Plate position fitted, not measured", "text": CORRECTED_COP_TEXT,
                    "observations": len(entries), "gate": self.assessment["cop_legs"]["rule"]})
        return out

    def readme_sections(self):
        return [("Foot-frame centre of pressure", CORRECTED_COP_TEXT),
                ("Where the data come from",
                 "UMich 2021 treadmill recordings (Streaming.mat). Identity, task labels, source clocks and joint moments "
                 "come from the earlier v2 review bundle unchanged. Joint powers are recomputed here as the moment times the "
                 "joint angular velocity (D-REF-5, 24 November 2026); the v2 power values are not carried over. Segment and joint angles, velocities and the foot-frame "
                 "centre of pressure come from the verified S02 v7 conversion (angles measured from markers in each leg's own "
                 "side-view plane; joint angles are differences of segment angles). The structured assessment is UM21-Q01 v3 "
                 "(coarse limits written before any data were read; draft, not approved reference ranges; D-UM21-Q01-1 = B). "
                 "The previous ankle zero-offset caveat no longer applies, because the ankle angle is now foot minus shank "
                 "from markers; the Vicon-based ankle re-expression of AB07/i10 was retired."),
                ("What is not in this package",
                 "No time-indexed table (the export is phase-normalised strides only), no ground reaction force, and no contralateral "
                 "columns: each stride carries its own leg only. Held-back data (the i10 recordings of AB01, AB02 and AB03, "
                 "AB04/d10 and AB10/d5) stays pending as it is.")]

    def extra_checks(self, ctx):
        counts, entries = ctx["counts"], ctx["entries"]
        a = self.assessment
        sel = set(self.recordings)
        a_failed = sum(v["failed"] for r, v in a["per_record"].items() if r in sel)
        a_obs = sum(v["observations"] for r, v in a["per_record"].items() if r in sel)
        n_pub, n_held, n_legs = published_leg_count(entries)
        a_pub = sum(1 for l in a["cop_legs"]["published"] if l["recording"] in sel)
        a_held = sum(1 for l in a["cop_legs"]["held"] if l["recording"] in sel)
        upstream = ctx["by_kind"].get("upstream_stride_rule", 0) + ctx["by_kind"].get("upstream_sudden_jump", 0)
        checks = [
            ("U1", "observations in the package equal the observations of the Q01 v3 job", a_obs, counts["observations_full"]),
            ("U2", "failed observations equal the failures recorded by the Q01 v3 job", a_failed, counts["failed_observations"]),
            ("U3", "legs with a published centre of pressure and legs held equal the Q01 v3 verdicts", [a_pub, a_held], [n_pub, n_held]),
            ("U4", "no time table in the package (UMich 2021 has no time-indexed export)", ["phase"], counts["tables"]),
            ("U5", "every observation has exactly 150 rows (phase table)", counts["observations_full"] * 150, counts["full"]["phase_rows"]),
            ("U7", "finite power rows in the written full table equal the rows where moment and joint speed were both finite",
             {c: v["rows_new_finite"] for c, v in sorted(self.stats.summary().items())},
             {c: ctx["readback"][("full", "phase")]["finite"][c] for c in sorted(POWER_COLUMNS)}),
        ]
        if self.stage == "full":
            checks.append(("U6", "the causes of the assessment failures equal the causes recorded by the Q01 v3 job",
                           sorted(a["failed_by_limit_observations"]), sorted(counts["assessment_failures_by_cause"])))
            seen = {"observations": counts["observations_full"], "phase_rows": counts["full"]["phase_rows"],
                    "recordings": len({e["rec"] for e in entries}),
                    "upstream_stride_rule_exclusions": ctx["by_kind"].get("upstream_stride_rule", 0),
                    "sudden_jump_exclusions": ctx["by_kind"].get("upstream_sudden_jump", 0),
                    "upstream_total_observations": counts["observations_full"] + upstream,
                    "cop_legs_published": n_pub, "cop_legs_held": n_held}
            checks += [("V." + k, f"{k} equals the verified chain total", v, seen[k]) for k, v in EXPECTED_FULL.items()]
        return checks


# ------------------------------------------------------------------ job
def stage_recordings(stage):
    if stage == "pilot":
        return list(PILOT_RECORDINGS)
    return sorted(json.loads((ROOT / Q01_ROOT / "assessment.json").read_text())["per_record"])


def stage_paths(stage):
    return {"job_id": f"{TASK_ID}-{stage}-{VERSION}-{ATTEMPT}", "spec": f"{AUDITS}/um21-r01-package-{stage}-spec-{VERSION}-{ATTEMPT}.json",
            "output_root": f"{BASE}/um21_r01_package_{stage}_{VERSION}_{ATTEMPT}" if stage == "pilot" else f"{BASE}/um21_r01_package_{VERSION}",
            "receipt": f"{AUDITS}/um21-r01-package-{stage}-launcher-receipt-{VERSION}-{ATTEMPT}.json"}


def build_spec(stage, pilot_receipt=None):
    p = stage_paths(stage)
    cmd = ["python3", RUNNER, "run", "--output-root", p["output_root"], "--stage", stage,
           "--recordings", ",".join(stage_recordings(stage))]
    b = bound_files()
    if stage == "full":
        cmd += ["--pilot-receipt", pilot_receipt]
        b[pilot_receipt] = rp.sha256_file(ROOT / pilot_receipt)
    return {"job_id": p["job_id"], "command": cmd, "cwd": str(ROOT), "output_root": p["output_root"],
            "receipt_path": p["receipt"], "bindings": b, "timeout_seconds": 3600, "kill_after_seconds": 30, "poll_seconds": 15,
            "startup_memory_mib": {"linux": 3584, "windows": 2816}, "runtime_memory_mib": {"linux": 2048, "windows": 2048},
            "disk_admission": [{"path": p["output_root"], "min_free_mib": 6 * 1024 if stage == "full" else 2 * 1024}],
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
    """A full run needs a clean pilot receipt of the same bound runner and shared builder on the pilot recordings."""
    r = json.loads((ROOT / rel).read_text())
    if r.get("status") != "completed" or r.get("clean_success") is not True:
        raise SystemExit("refused: the pilot receipt is not a clean completed run")
    cmd = r["spec"]["command"]
    if "--stage" not in cmd or cmd[cmd.index("--stage") + 1] != "pilot":
        raise SystemExit("refused: the receipt is not a pilot run")
    for f in (RUNNER, SHARED, Q01_RUNNER, JOINT_POWER):
        if r["spec"]["bindings"].get(f) != rp.sha256_file(ROOT / f):
            raise SystemExit(f"refused: the pilot ran different code than the current {f}")


def run(args):
    rp.assert_guarded(ADDRESS_SPACE_MIB)
    recordings = args.recordings.split(",")
    if recordings != stage_recordings(args.stage):
        raise SystemExit("refused: --recordings are not the pilot sample or the 44 recordings of the Q01 v3 job")
    if args.stage == "full":
        if not args.pilot_receipt:
            raise SystemExit("refused: a full run needs --pilot-receipt")
        check_pilot(args.pilot_receipt)
    rp.pin_arrow()
    started = time.time()
    adapter = UM21Adapter(recordings, args.stage)
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
        return plan(args.stage, args.pilot_receipt)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
