#!/usr/bin/env python3
"""Build docs/quality/audits/gt21-problem-scope.json for the Georgia Tech 2021 problems page.

Reads only committed audit and handoff JSON files, one small probe file
(gt21-problem-scope-probe.json) and the names of the folders in the stopped rebuild batch. It opens
no recording and no converted data. Every number on docs/datasets/gt21/problems.html comes from the
file this writes. Nothing here is a scientific approval.

Usage: python3 contributor_tools/build_gt21_problem_scope.py
"""
from __future__ import annotations

import json
import os
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUD = ROOT / "docs/quality/audits"
OUT = AUD / "gt21-problem-scope.json"
BATCH = ROOT / "converted_datasets/reconversion_v2/gt21_force_corrected_full_20261021"
SEED = 20261118
MODES = ["levelground", "ramp", "stair", "treadmill"]
MODE_PLAIN = {"levelground": "Level walking", "ramp": "Ramps", "stair": "Stairs", "treadmill": "Treadmill"}
SIX = ["AB12", "AB15", "AB17", "AB19", "AB23", "AB28"]
VERDICTS = ["Also wrong, fixed in a pilot", "Also wrong, not yet fixed", "Checked, not affected", "Left out", "Not checked"]


def load(name):
    return json.loads((AUD / name).read_text(encoding="utf-8"))


def pct(a, b, nd=1):
    return round(100.0 * a / b, nd)


def n(x):
    return f"{x:,}"


def main():
    cross = load("gt21-s01-cohort-crosswalk.json")
    mirror = load("gt21-s02-2024-copy.json")
    conv = load("gt21-c01-conventions.json")
    phases = load("gt21-all-source-phases.json")
    terrain = load("gt21-events-and-terrain.json")
    readback = load("gt21-completed-force-readback.json")
    preserve = load("gt21-force-fix-preservation.json")
    elig = load("gt21-event-eligibility.json")
    geom = load("gt21-force-geometry.json")
    force_fix = load("gt21-force-fix.json")
    plate_fix = load("gt21-plate-assignment-fix.json")
    direction = load("gt21-measured-force-direction.json")
    core04 = load("core04-gt21-pilot.json")
    terrain_fix = load("gt21-terrain-fix.json")
    cover = load("gt21-event-coverage.json")
    probe = load("gt21-problem-scope-probe.json")
    status = json.loads((BATCH / "batch_status.json").read_text(encoding="utf-8"))

    # ---- who and how many (source dataset denominators) ----
    local = {p["subject"]: p["local_source"]["recordings_by_mode_conditions_files"] for p in cross["participants"] if (p.get("local_source") or {}).get("recordings_by_mode_conditions_files")}
    assert len(local) == 16 and sum(sum(v.values()) for v in local.values()) == 2301
    mode_tot = {m: sum(v[m] for v in local.values()) for m in MODES}
    six_rec = {s: mirror["participants"][s]["structure"]["recordings_by_mode_conditions_files"] for s in SIX}
    six_total = sum(sum(v.values()) for v in six_rec.values())
    assert six_total == 846
    six_mode = {m: sum(v[m] for v in six_rec.values()) for m in MODES}
    all_total = 2301 + six_total
    weights = {p["subject"]: float(p["metadata"]["Weight_literal"]) for p in cross["participants"]}
    assert len(weights) == 22
    steps_total = phases["counts"]["pairs"]
    samples_total = phases["counts"]["samples"]

    # the stopped rebuild batch: folder names only
    done_dirs = {}
    for sub in sorted(os.listdir(BATCH)):
        sd = BATCH / sub
        if sd.is_dir() and sub.startswith("AB"):
            for date in os.listdir(sd):
                for m in os.listdir(sd / date):
                    done_dirs[(sub, m)] = len(os.listdir(sd / date / m))
    batch_people = sorted({k[0] for k in done_dirs})
    assert batch_people == ["AB06"], batch_people
    assert status["completed"] == 102 and status["total"] == 2301 and status["observations"] == 1299
    stair_dirs = done_dirs[("AB06", "stair")]  # one finished, one is the recording that failed
    batch_done = {"levelground": done_dirs[("AB06", "levelground")], "ramp": done_dirs[("AB06", "ramp")],
                  "treadmill": done_dirs[("AB06", "treadmill")], "stair": stair_dirs - 1}
    assert sum(batch_done.values()) == 102

    den = {
        "publisher_participants": 22, "local_participants": 16, "missing_participants": 6,
        "local_recordings": 2301, "local_recordings_by_task": mode_tot,
        "acquired_recordings_of_six": six_total, "acquired_by_task": six_mode, "recordings_local_plus_acquired": all_total,
        "source_steps_local": steps_total, "source_samples_local_gait_tables": samples_total,
        "rebuilt_recordings": 102, "rebuilt_steps": 1299, "rebuilt_participants": ["AB06"], "rebuilt_by_task": batch_done,
        "note": ("Scope is measured against the source dataset: 22 participants in the original study, of which 16 are here "
                 "(2,301 recordings) and six are not converted (846 recordings in the authors' 2024 copy). A step is one heel strike "
                 "to the next heel strike of one leg; the 16 local participants have 78,604 of them in the source gait tables "
                 "(21,363,858 samples). Only 102 recordings (1,299 steps), all from AB06, have been rebuilt, so measured counts "
                 "below come from small checked sets and say so. Sample counts are given only where an audit has them."),
    }

    def rows16():
        return sorted(local) + ["SIX"]

    def make_grid(kind, rows, fn, note=""):
        cells = {}
        for r in rows:
            for m in MODES:
                cells[f"{r}/{m}"] = fn(r, m)
        return {"kind": kind, "rows": rows, "cols": MODES, "cols_plain": [MODE_PLAIN[m] for m in MODES], "cells": cells, "note": note}

    def six_row(r):
        return "pending" if r == "SIX" else None

    def table_by_task(label_a, fn):
        return [[MODE_PLAIN[m], n(mode_tot[m])] + fn(m) for m in MODES]

    probs = []

    # ================= A: six missing participants =================
    rows22 = sorted(weights)
    six_tab = []
    for s in SIX:
        st = mirror["participants"][s]["structure"]
        r = six_rec[s]
        six_tab.append([s, n(sum(r.values())), f"{r['levelground']} / {r['ramp']} / {r['stair']} / {r['treadmill']}", n(st["files"]), f"{st['bytes'] / 1e9:.2f} GB", "Downloaded and checked, not unpacked or converted"])
    probs.append({
        "key": "missing_participants", "card": "Six of the 22 participants are not in the local data",
        "status": {"key": "decided", "label": "Decided by José, fix not yet run",
                   "detail": "José chose the authors' 2024 copy as the source for the six. All six are downloaded and checked against the folder listing. None is unpacked or converted yet.",
                   "needs": ""},
        "wrong": "The original study has 22 participants. The local source folder holds 16 of them (2,301 recordings). AB12, AB15, AB17, AB19, AB23 and AB28 were never converted. For AB17, the one participant whose 2021 published archive we opened, that archive has no static-pose files and no joint angles relative to the static pose, which our conversion code reads.",
        "how": "The publisher lists 22 archives, rechecked on 31 October 2026 with unchanged size and checksum. The local folder holds 16 participants and no extra ones. The other five 2021 archives were not opened.",
        "example": "AB17, compared with its 2021 archive: 1,464 of 1,466 files are identical in size and checksum, 136 exist only in the 2024 copy (133 relative joint-angle files and 3 static-pose files), and 2 ramp joint-moment files differ.",
        "total_line": f"6 of 22 participants ({pct(6, 22)}%); {n(six_total)} of {n(all_total)} recordings ({pct(six_total, all_total)}%), counting the 2,301 local recordings plus the {n(six_total)} in the 2024 copy.",
        "total_numbers": {"participants_missing": 6, "participants_total": 22, "recordings_missing": six_total, "recordings_total": all_total},
        "denominator_text": "Recordings are counted from the file listings of the 2024 copy (one recording per conditions file). Samples are not known: the six have not been opened.",
        "table": {"columns": ["Participant", "Recordings", "Level / ramp / stair / treadmill", "Files", "Size", "Where it stands"], "rows": six_tab, "fold": False},
        "grid": make_grid("affected", rows22, lambda r, m: 100.0 if r in SIX else 0.0),
        "grid_caption": "Shaded rows are the six participants that are not converted yet.",
        "figure_question": "Which participants are missing, and for which tasks?",
        "direction": "Direction: missing people change who the data describes. They do not change the values of the 16 people we have.",
        "knock_on": [
            {"signal": "The 16 participants already here", "verdict": "Checked, not affected",
             "line": "The six were downloaded into a separate folder; the local source folder was not written.",
             "evidence": "Local folder still holds exactly 16 participants and 2,301 recordings; no unexpected participant.", "ref": "gt21-s01-cohort-crosswalk counts"},
            {"signal": "Any result that pools the whole cohort", "verdict": "Left out",
             "line": "Until the six are converted, pooled results describe 16 of 22 people.",
             "evidence": f"{n(six_total)} recordings ({pct(six_total, all_total)}%) are not in the converted set.", "ref": "gt21-s02-2024-copy participants"},
            {"signal": "Joint-angle zero used for the six", "verdict": "Not checked",
             "line": "Their folders list the same relative joint-angle files as the 16, but no file of the six has been read.",
             "evidence": "", "ref": ""},
            {"signal": "Body mass of the six", "verdict": "Not checked",
             "line": "The subject sheet has a Weight number for all 22, but its unit is unresolved (see the body-mass card).",
             "evidence": "", "ref": ""},
        ],
        "extra_figures": [],
    })

    # ================= B: which version of the files =================
    ramp_all = mode_tot["ramp"] + six_mode["ramp"]
    probs.append({
        "key": "file_version", "card": "The local files are the authors' 2024 copy, not the checksummed 2021 release",
        "status": {"key": "decided", "label": "Decided by José, fix not yet run",
                   "detail": "José chose the 2024 copy. The file-by-file comparison with the 2021 release has run for AB17 only.", "needs": ""},
        "wrong": "The 16 local participants, and the six now downloaded, come from the authors' 2024 copy. Only the 2021 release has publisher checksums. The listings show that every ramp joint-moment file was rewritten in September 2021, after the first release, and that relative joint-angle files were added in April 2024.",
        "how": "We compared AB17's 2021 archive with the 2024 copy by size and checksum. Modification times in the listings are labels, not proof, and the 2024 folder is a live working copy.",
        "example": "AB17 ramp recording 1 (right leg): the joint-moment file is 322,984 bytes in 2021 and 324,295 bytes in 2024. Ramp recording 6 (right leg, trial 4): 284,406 against 299,554 bytes. What changed inside is not decoded.",
        "total_line": f"2 of 61 AB17 ramp joint-moment files ({pct(2, 61)}%) differ between 2021 and 2024. The other {n(ramp_all - 61)} ramp recordings of the 22 participants have not been compared.",
        "total_numbers": {"files_differ": 2, "ramp_files_compared": 61, "ramp_recordings_all_22": ramp_all, "ramp_not_compared": ramp_all - 61, "identical_files_ab17": 1464, "files_only_in_2024": 136},
        "denominator_text": "Counted over AB17's 1,602 files in the 2024 copy against 1,466 files in its 2021 archive. Percentages for the other participants are unknown, not zero. Samples are not counted.",
        "table": {"columns": ["Group of AB17 files", "Files", "Result"], "rows": [
            ["Same size and checksum in 2021 and 2024", "1,464", "Identical"],
            ["Only in the 2024 copy", "136", "133 relative joint-angle files, 3 static-pose files"],
            ["Ramp joint-moment files that differ", "2", "Rewritten after the 2021 release"],
            ["Ramp joint-moment files that match", "59", "Identical, although dated September 2021"]], "fold": False},
        "grid": make_grid("affected", rows22, lambda r, m: ({"levelground": 0.0, "ramp": pct(2, 61), "stair": 0.0, "treadmill": 0.0}[m] if r == "AB17" else "nc")),
        "grid_caption": "Only AB17 was compared. Every other cell is not checked, which is different from not affected.",
        "figure_question": "Which participants have had their files compared with the 2021 release?",
        "direction": "Direction: a changed file only affects the quantity stored in it. Ramp joint moments are the exposed quantity; angles, forces and marker files were identical in AB17.",
        "knock_on": [
            {"signal": "Ramp joint moments and powers", "verdict": "Not checked",
             "line": "Two AB17 files changed; whether the change matters is unknown for AB17 and for every other participant.",
             "evidence": "", "ref": ""},
            {"signal": "Joint angles, forces and markers of AB17", "verdict": "Checked, not affected",
             "line": "Every shared file except the two ramp moment files has the same size and checksum as in 2021.",
             "evidence": "1,464 of 1,466 shared files identical; 0 differ in content at the same size.", "ref": "GT21-S02 crc_comparison"},
            {"signal": "Level, stair and treadmill moments of AB17", "verdict": "Checked, not affected",
             "line": "Same size and checksum as in 2021.", "evidence": "All level, stair and treadmill joint-moment files of AB17 match.", "ref": "GT21-S02 crc_comparison"},
            {"signal": "The other 15 local participants", "verdict": "Not checked",
             "line": "No 2021 archive is held for them, so no comparison is possible without another download.", "evidence": "", "ref": ""},
        ],
        "extra_figures": [],
    })

    # ================= C: plate assignment and sign =================
    pres_rec = preserve["recordings"]  # 36
    pres_lvl = preserve["by_mode"]["levelground"]
    pres_tm = preserve["by_mode"]["treadmill"]
    changed_vals = pres_lvl["changes"]["changed"] + pres_tm["changes"]["changed"]
    m2f, f2m = pres_lvl["changes"]["missing_to_finite"], pres_tm["changes"]["finite_to_missing"]
    legs = geom["converted_force_comparison"]["leg_comparisons"]
    rng = random.Random(SEED)
    draw = rng.sample(range(len(legs)), 24)
    force_draw = []
    for i in sorted(draw):
        c = legs[i]
        force_draw.append({"index": i, "leg": c["anatomical_leg"], "error_sign_a": c["anterior"]["max_abs_errors_BW"]["source_positive"],
                           "error_sign_b": c["anterior"]["max_abs_errors_BW"]["source_negative"]})
    ex = force_draw[0]
    probs.append({
        "key": "plate_and_sign", "card": "Force plates and force signs were picked from force and ankle-moment waveforms",
        "status": {"key": "fixed_pilot", "label": "Fixed in a checked pilot",
                   "detail": "New rules ran in small trial runs (a pilot) and agree with the source. The full rebuild has not adopted them.", "needs": ""},
        "wrong": "For overground walking the old conversion code decided which plate belonged to which foot with early-stance and late-swing force thresholds, and it chose the sign of forward force and centre of pressure by whichever matched the ankle moment curve. That can put one foot's force on the other foot or flip a sign without the data saying so.",
        "how": "The code review found both rules. Plate positions and pelvis markers can answer the same questions without the moment curve. Treadmill plates are named by side, and the one treadmill pilot recording shows one sign matching the measured plate data to rounding error.",
        "did": "",
        "example": f"One of 24 legs drawn at random from the 228 legs of the treadmill pilot recording (seed {SEED}): a {ex['leg']} leg where assuming forward force is positive is off by up to {ex['error_sign_a']:.2f} body weights and assuming it is negative is off by only {ex['error_sign_b']:.0e}.",
        "total_line": (f"In the {pres_rec} recordings compared before and after (30 overground, 6 treadmill, all AB06; {n(preserve['rows'])} rows) the new rules changed {n(changed_vals)} force values. "
                       f"None of the other columns changed."),
        "total_numbers": {"recordings_compared": pres_rec, "rows": preserve["rows"], "values_changed": changed_vals, "overground_missing_to_measured": m2f, "treadmill_measured_to_missing": f2m,
                          "treadmill_cycles_in_pilot": force_fix["cycles"], "pilot_rows": force_fix["rows"]},
        "denominator_text": (f"Of the 2,301 local recordings, {pres_rec} have been compared before and after, all from AB06, so 1.6% of recordings. Percentages are not extrapolated. The old rule applied to every recording with force plates. "
                             "Overground values changed from missing to measured; treadmill values changed from measured to missing, mostly because centre of pressure is now left missing when the foot carries under 0.2 body weight."),
        "table": {"columns": ["Task", "Recordings compared", "Rows", "Force values changed", "Missing to measured", "Measured to missing"], "rows": [
            ["Level walking (AB06)", "30", n(pres_lvl["rows"]), n(pres_lvl["changes"]["changed"]), n(pres_lvl["changes"]["missing_to_finite"]), "0"],
            ["Treadmill (AB06)", "6", n(pres_tm["rows"]), n(pres_tm["changes"]["changed"]), "0", n(pres_tm["changes"]["finite_to_missing"])],
            ["Ramps and stairs", "1 and 1 (pilot only)", "300 and 150", "not measured", "not measured", "not measured"]], "fold": False},
        "grid": make_grid("checked", rows16(), lambda r, m: six_row(r) or ({"levelground": 100.0, "ramp": pct(1, 63), "stair": pct(1, 42), "treadmill": pct(6, 8)}[m] if r == "AB06" else 0.0)),
        "grid_caption": "Share of each group's recordings that the new rules were compared on. Zero means not looked at.",
        "figure_question": "Which participants and tasks have been compared before and after?",
        "direction": "Direction: a wrong plate or sign changes force and centre of pressure. Angles and the authors' joint moments are separate source columns.",
        "knock_on": [
            {"signal": "Forces and centre of pressure of the 36 compared recordings", "verdict": "Also wrong, fixed in a pilot",
             "line": "Every changed value is a force or centre-of-pressure value.",
             "evidence": f"{n(changed_vals)} force values changed; centre of pressure agrees with the measured plate position to {force_fix['max_contact_cop_error_m']:.0e} m at contact.", "ref": "gt21-force-fix-preservation; gt21-force-fix"},
            {"signal": "Joint angles, moments, powers and timing in those recordings", "verdict": "Checked, not affected",
             "line": "They are copied from the authors' files, not computed from our force columns.",
             "evidence": f"All non-force columns identical in {pres_rec} recordings ({n(preserve['rows'])} rows) before and after.", "ref": "gt21-force-fix-preservation non_force_columns_identical"},
            {"signal": "Ramp and stair forces", "verdict": "Not checked",
             "line": "Only 2 ramp steps and 1 stair step were rebuilt with the new rules.", "evidence": "", "ref": ""},
            {"signal": "Treadmill and overground recordings other than the 36", "verdict": "Not checked",
             "line": "Needs the full rebuild, which is a guarded job (a supervised run with memory limits).", "evidence": "", "ref": ""},
            {"signal": "The plate rule itself", "verdict": "Not checked",
             "line": "The rule follows the publisher's geometry; no independent contact label exists to test it.", "evidence": "", "ref": ""},
        ],
        "extra_figures": [{"file": "force-sign.svg", "question": "Which forward-force sign matches the measured plate data?",
                           "alt": "For 24 randomly drawn legs, the error of assuming forward force is positive is about 0.1 body weight, while assuming negative is off by about one part in a trillion.",
                           "cap": f"24 legs drawn at random (seed {SEED}) from the 228 legs of one treadmill pilot recording. Each dot is one leg; lower is a better match."}],
        "figure_data": {"force_sign_draw": force_draw, "seed": SEED, "pool": len(legs)},
    })

    # ================= D: sideways direction =================
    st = probe["stance_sideways"]
    rt = [r["plates"]["Treadmill_R"]["mean_sideways_force_N_over_contact"] for r in st]
    lf = [r["plates"]["Treadmill_L"]["mean_sideways_force_N_over_contact"] for r in st]
    hd = conv["pooled"]["contact_heading_samples"]
    hd_tot = sum(hd.values())
    who = lambda rec: rec.split("/")[0] + ", treadmill trial " + str(int(rec.split("/")[-1].split("_")[1]))
    curve0 = st[0]["plates"]
    probs.append({
        "key": "sideways", "card": "Sideways force and centre of pressure point opposite ways for the two feet",
        "status": {"key": "decided", "label": "Decided by José, fix not yet run",
                   "detail": "José chose option B: positive outward for each leg, so the left leg is mirrored. The conversion code has not been changed or run for this.", "needs": ""},
        "wrong": "The sideways columns were exported on the lab's fixed X axis. That axis points to the person's right when they face the lab's negative Z direction. So it points outward for the right foot and inward for the left foot, and it flips when they walk the other way. The name 'lateral' therefore does not describe the numbers.",
        "how": f"We read the force plate table of three treadmill recordings drawn at random (seed {probe['seed']}), one at a time. On the right plate the mean sideways force over stance is {rt[0]:.1f}, {rt[1]:.1f} and {rt[2]:.1f} N; on the left plate it is {lf[0]:+.1f}, {lf[1]:+.1f} and {lf[2]:+.1f} N. Same axis, opposite signs.",
        "example": f"{who(st[0]['recording'])}: {curve0['Treadmill_R']['bouts']} right-foot and {curve0['Treadmill_L']['bouts']} left-foot stance phases averaged. The right foot pushes toward negative X, the left toward positive X.",
        "total_line": "All 2,301 local recordings (100%), in the two sideways force columns and the two sideways centre-of-pressure columns, wherever a plate gives a value.",
        "total_numbers": {"recordings_affected": 2301, "recordings_total": 2301, "walking_samples_faced_negative_z": hd["faces lab -Z"], "walking_samples_faced_positive_z": hd["faces lab +Z"], "walking_samples_along_x": hd["walks along lab ±X"], "walking_samples_total": hd_tot,
                          "treadmill_mean_right_N": rt, "treadmill_mean_left_N": lf},
        "denominator_text": (f"Recordings: 2,301 local ones; the {n(six_total)} not yet converted would be affected the same way. Steps and samples are not counted because the fix is not run. "
                             f"In 8 recordings checked for walking direction, {n(hd['faces lab -Z'])} of {n(hd_tot)} on-plate samples ({pct(hd['faces lab -Z'], hd_tot)}%) face -Z, {n(hd['faces lab +Z'])} ({pct(hd['faces lab +Z'], hd_tot)}%) face +Z and {hd['walks along lab ±X']} ({pct(hd['walks along lab ±X'], hd_tot)}%) walk along X."),
        "table": {"columns": ["Treadmill recording (drawn at random)", "Right plate mean (N)", "Left plate mean (N)"], "rows": [[who(r["recording"]), f"{r['plates']['Treadmill_R']['mean_sideways_force_N_over_contact']:.1f}", f"{r['plates']['Treadmill_L']['mean_sideways_force_N_over_contact']:+.1f}"] for r in st], "fold": False},
        "grid": make_grid("affected", rows16(), lambda r, m: six_row(r) or 100.0),
        "grid_caption": "Every recording carries the sideways columns, so every cell is affected.",
        "figure_question": "Which recordings carry the sideways columns?",
        "direction": "Direction: the sign fix changes only sideways force and sideways centre of pressure. It does not reach vertical or forward values or any angle.",
        "knock_on": [
            {"signal": "Sideways centre of pressure", "verdict": "Also wrong, not yet fixed",
             "line": "It is measured on the same X axis as the sideways force, so it has the same left-right flip.", "evidence": "Both columns are declared lab +X in the conventions review.", "ref": "gt21-c01-conventions channel_policy"},
            {"signal": "Vertical force and centre-of-pressure height", "verdict": "Checked, not affected",
             "line": "They sit on the lab's up axis, which is checked.", "evidence": "Gravity points down the lab Y axis; right-handed in 100% of 8 sampled recordings.", "ref": "gt21-c01-conventions"},
            {"signal": "Forward force and centre of pressure", "verdict": "Checked, not affected",
             "line": "Their sign comes from the measured pelvis direction of each step, not from the sideways rule.", "evidence": "Forward sign measured per step on the lab Z axis; missing if the direction is unclear.", "ref": "gt21-measured-force-direction"},
            {"signal": "Angles, joint moments and powers", "verdict": "Checked, not affected",
             "line": "Changing a force or position sign left every other column exactly as it was in the pilot runs.", "evidence": "Non-force columns identical in 2 pilot recordings (114 treadmill and 2 ramp steps).", "ref": "gt21-measured-force-direction"},
            {"signal": "Walking along the X axis", "verdict": "Not checked",
             "line": f"{hd['walks along lab ±X']} of {n(hd_tot)} on-plate samples in 8 recordings walk along X, where 'sideways' would be forward or backward. Beyond those 8 recordings it is not measured.", "evidence": "", "ref": ""},
        ],
        "extra_figures": [{"file": "sideways.svg", "question": "Does 'sideways' point the same way for both feet?",
                           "alt": "Average sideways force over stance for the right and left treadmill plates of one recording. The right foot pushes toward negative X, the left toward positive X.",
                           "cap": f"{who(st[0]['recording'])}, one of three recordings drawn at random (seed {probe['seed']}). Lines are averages over stance phases."}],
        "figure_data": {"probe_curve": {"right": curve0["Treadmill_R"]["curve_sideways_N"], "left": curve0["Treadmill_L"]["curve_sideways_N"], "who": who(st[0]["recording"]), "seed": probe["seed"]}},
    })

    # ================= E: pelvis tilt =================
    pc = conv["pelvis_check"]["recordings"]
    pelvis_rows = []
    for r in pc:
        sid, mode = r["recording"].split("/")[0], r["recording"].split("/")[2]
        s = r["stride_level"]
        pelvis_rows.append({"who": f"{sid} {MODE_PLAIN[mode].lower()}", "strides": s["strides"], "published_tilt": s["stride_mean_r_with_marker_tilt"]["pelvis_tilt"],
                            "minus_list": s["stride_mean_r_with_marker_tilt"]["-pelvis_list"], "heading_removed": s["stride_mean_r_with_marker_tilt"]["heading-removed source tilt"],
                            "marker_offset_deg": r["marker_to_model_offset_deg"]})
    offs = [r["marker_offset_deg"] for r in pelvis_rows]
    ph = core04["pelvis_heading"]
    probs.append({
        "key": "pelvis", "card": "Pelvis tilt, and the angles built on it, do not match the markers",
        "status": {"key": "decided", "label": "Decided by José, fix not yet run",
                   "detail": "José chose option C: take tilt from the pelvis markers directly. The conversion code has not been changed or run for this.", "needs": ""},
        "wrong": "The old conversion code exported the authors' model 'pelvis tilt' as forward-back tilt. The authors' model turns the pelvis about 90 degrees in heading, so that column is not forward-back tilt. After removing the heading, no tilt we can derive from the authors' data follows the marker tilt over treadmill strides, and overground it follows only partly. Thigh, shank, foot and trunk angles were built on that tilt.",
        "how": f"We compared each candidate with the tilt of the four pelvis markers over the strides of 8 recordings drawn at random (seed 20261027). Stride-average agreement on the two treadmill recordings is {pelvis_rows[0]['heading_removed']:.2f} and {pelvis_rows[1]['heading_removed']:.2f} (1 would be identical). In a separate set of {ph['recordings']} recordings, only {ph['sagittal']} had the model's heading in the forward-back frame.",
        "example": f"{pelvis_rows[0]['who']}, {pelvis_rows[0]['strides']} strides: the published pelvis tilt agrees with the marker tilt at {pelvis_rows[0]['published_tilt']:.2f}. The marker-based tilt sits about {offs[0]:.0f} degrees from the model's zero.",
        "total_line": "The pelvis tilt column and four angle columns built on it (thigh, shank, foot, trunk) in all 2,301 local recordings (100%).",
        "total_numbers": {"recordings_affected": 2301, "recordings_total": 2301, "columns_affected": 5, "heading_sample_recordings": ph["recordings"], "heading_sagittal": ph["sagittal"], "tilt_sample_recordings": len(pc), "marker_offset_range_deg": [min(offs), max(offs)]},
        "denominator_text": f"Recordings: 2,301 local ones. Evidence comes from {len(pc)} recordings (7 participants) for agreement and {ph['recordings']} recordings (6 participants) for heading. Strides and samples are not counted for the whole set.",
        "table": {"columns": ["Recording (drawn at random)", "Strides", "Published pelvis tilt", "Heading removed", "Marker tilt offset"], "rows": [[r["who"], str(r["strides"]), f"{r['published_tilt']:.2f}", f"{r['heading_removed']:.2f}", f"{r['marker_offset_deg']:.1f}°"] for r in pelvis_rows], "fold": False},
        "grid": make_grid("affected", rows16(), lambda r, m: six_row(r) or 100.0),
        "grid_caption": "Every recording has the pelvis tilt column, so every cell is affected.",
        "figure_question": "Which recordings carry the pelvis tilt column?",
        "direction": "Direction: pelvis tilt feeds the thigh, shank, foot and trunk angles. Hip, knee and ankle angles are separate joint angles.",
        "knock_on": [
            {"signal": "Thigh, shank, foot and trunk angles (side view)", "verdict": "Also wrong, not yet fixed",
             "line": "They inherit the pelvis tilt, so they carry the same error.", "evidence": "The conversion builds them from the pelvis tilt; the marker route would mix marker and model zeros.", "ref": "GT21-C01 summary"},
            {"signal": "Hip, knee and ankle angles", "verdict": "Checked, not affected",
             "line": "They are the model's own joint angles, not built on the pelvis tilt column.",
             "evidence": "0 wrong signs among 648 leg channels tested (521 right, 127 left undecided).", "ref": "core04-gt21-pilot counts"},
            {"signal": "Joint moments and powers", "verdict": "Not checked",
             "line": "They are the authors' own values and do not use our pelvis column, so no change is expected, but no run has shown it.", "evidence": "", "ref": ""},
            {"signal": "Why the treadmill markers and the model disagree", "verdict": "Not checked",
             "line": "Marker noise, soft tissue and model weighting are candidates. It needs a guarded job (a supervised run with memory limits).", "evidence": "", "ref": ""},
            {"signal": "The six participants not yet converted", "verdict": "Not checked", "line": "Their files have not been read.", "evidence": "", "ref": ""},
        ],
        "extra_figures": [{"file": "pelvis.svg", "question": "Does any source tilt follow the marker tilt, stride by stride?",
                           "alt": "Stride-average agreement with marker tilt for three candidate tilts in 8 recordings. None is close to 1 on both treadmill recordings.",
                           "cap": "8 recordings drawn at random (seed 20261027). Each bar is the stride-average correlation with the pelvis-marker tilt; 1 would be identical."}],
        "figure_data": {"pelvis": pelvis_rows},
    })

    # ================= F: joint angle zero =================
    tried = probe["joint_zero"]["relative_file_read_attempts"]
    pose = probe["joint_zero"]["static_pose_angles"]
    unread = len(tried) + len(pose)
    assert all(not t["admitted"] for t in tried) and all("rejected" in p for p in pose)
    probs.append({
        "key": "joint_zero", "card": "Joint-angle zero is now defined by the segment angles",
        "status": {"key": "decided", "label": "Decided by José, fix not yet run", "detail": "José decided on 23 November 2026: joint angles are differences of segment angles, and segment angles are measured against gravity, so there is no separate joint zero (no static pose, no model zero). The conversion code has not been changed or run for this.", "needs": "Needs segment angles (thigh, shank, foot and pelvis) for every recording. Pelvis-marker tilt is available (the earlier pelvis decision); whether thigh, shank and foot angles can be built from the markers and the ankle centre found: not checked. A guarded job is needed to measure how far the old zeros differ from the new one."},
        "wrong": "Joint angles come in two versions. One is zero at the model's own zero. The other is the trial angle minus the average of the participant's static standing trial (added by the authors in April 2024). The conversion code reads the relative version, our sign tests used the model zero, and the 2021 archive of AB17 has no relative version. José has now decided the zero (see the status above); the size of the difference between the old files and the new rule is not measured.",
        "how": "The README dates the relative files to 28 April 2024, and the authors' script subtracts the column average of the first static trial it finds, without wrapping angles. We then tried to measure the difference with our safe file reader: it refused all 20 files we tried (16 static-pose files and one relative file for each of the four tasks).",
        "example": "No measured example exists: the size of the difference has not been measured, so the figure is a made-up illustration, labelled as one.",
        "total_line": "Every joint angle in all 2,301 local recordings (100%) is affected by the new zero rule. The size of the difference is not measured.",
        "total_numbers": {"recordings_affected": 2301, "recordings_total": 2301, "files_tried": unread, "files_read": 0, "static_files_tried": len(pose), "relative_files_tried": len(tried)},
        "denominator_text": "Recordings: 2,301 local ones. Participants: all 16 local and the six not yet converted. Samples are not counted. 'Affected' means the choice applies, not that the values are wrong.",
        "table": {"columns": ["What we tried", "Files", "Read"], "rows": [["Static-pose joint-angle files (one per local participant)", str(len(pose)), "0"], ["Relative joint-angle files (one per task, drawn at random)", str(len(tried)), "0"]], "fold": False},
        "grid": make_grid("affected", rows16(), lambda r, m: six_row(r) or 100.0),
        "grid_caption": "The choice applies to every recording; the size of the difference is not measured.",
        "figure_question": "Which recordings does the zero choice apply to?",
        "direction": "Direction: the zero shifts every sample of the joint angles. Moments and powers come from separate files.",
        "knock_on": [
            {"signal": "Hip, knee and ankle angles", "verdict": "Not checked", "line": "Every sample shifts by a constant that is not measured here.", "evidence": "", "ref": ""},
            {"signal": "Signs of hip, knee and ankle angles", "verdict": "Checked, not affected",
             "line": "A constant shift does not flip a sign; our sign test found none wrong.", "evidence": "0 wrong signs in 648 leg channels tested (305 applied, 216 suggested, 127 left undecided), using the model zero.", "ref": "core04-gt21-pilot counts"},
            {"signal": "Reference ranges for the angles", "verdict": "Not checked", "line": "Ranges depend on the zero. The zero is now decided, so ranges can be set only after the angles are recomputed.", "evidence": "", "ref": ""},
            {"signal": "Joint moments and powers", "verdict": "Checked, not affected",
             "line": "The authors' script only writes a new angle file; moments are read from their own files.", "evidence": "The authors' script writes the relative angle file only and leaves the moment files alone.", "ref": "gt21-ab17-local-processing-recipe static_recipe"},
            {"signal": "Thigh, shank, foot and trunk angles", "verdict": "Not checked", "line": "They are tied to the pelvis problem (see its card).", "evidence": "", "ref": ""},
        ],
        "extra_figures": [{"file": "zero.svg", "question": "What would a different zero do to a joint angle?",
                           "alt": "Made-up illustration: the same knee-angle curve drawn twice, one shifted up by a constant.",
                           "cap": "Made-up illustration. The real shift has not been measured."}],
    })

    # ================= G: body mass unit =================
    wmin, wmax = min(weights.values()), max(weights.values())
    probs.append({
        "key": "mass_unit", "card": "The unit of participant weight is not stated",
        "status": {"key": "open", "label": "Open", "detail": "", "needs": "Needs source evidence first (the authors' scripts or paper). If none turns up, a decision will be needed."},
        "wrong": "Forces are divided by body weight and moments and powers by body mass, using the Weight number in the subject sheet. No file we hold states its unit. The numbers look like kilograms, but that is not proof, and the model's mass is not an acceptable stand-in.",
        "how": f"The README gives no unit for the subject sheet; the authors' inverse-kinematics tool does not use it; a download of the 2021 scripts archive was refused. The local scripts divide forces and moments by it, which supports kilograms but does not prove it. The 22 values run from {wmin:.2f} to {wmax:.2f}.",
        "example": f"AB17 has the Weight number 61.23; AB25 has {weights['AB25']:.2f}. Neither number carries a unit.",
        "total_line": "Every force, moment and power column that is divided by body weight or mass, in all 2,301 local recordings (100%), and all 22 participants have a number.",
        "total_numbers": {"recordings_affected": 2301, "recordings_total": 2301, "participants_with_number": 22, "weight_min": wmin, "weight_max": wmax},
        "denominator_text": "Recordings: 2,301 local ones. Participants: 22 of 22 have a number; the unit is the open question. Samples are not counted.",
        "table": {"columns": ["Participants", "Weight number present", "Unit stated"], "rows": [["22 of 22", "Yes", "No"]], "fold": False},
        "grid": make_grid("affected", rows16(), lambda r, m: six_row(r) or 100.0),
        "grid_caption": "Every normalised force, moment and power depends on the number.",
        "figure_question": "Which recordings use the weight number?",
        "direction": "Direction: the weight unit scales forces, moments and powers. It does not touch angles or positions.",
        "knock_on": [
            {"signal": "Forces in body weights", "verdict": "Not checked", "line": "They scale directly with the unit; a wrong unit would scale every value.", "evidence": "", "ref": ""},
            {"signal": "Joint moments and powers per kilogram", "verdict": "Not checked", "line": "Same scaling; no check against another source has been run.", "evidence": "", "ref": ""},
            {"signal": "Centre-of-pressure positions in metres", "verdict": "Checked, not affected", "line": "They come from plate and marker positions, not from weight.", "evidence": "Computed from plate position minus ankle marker position, in metres.", "ref": "gt21-c01-conventions channel_policy"},
            {"signal": "Joint angles", "verdict": "Checked, not affected", "line": "Angles do not use mass.", "evidence": "Angles are read from the authors' joint angle files.", "ref": "gt21-c01-conventions channel_policy"},
        ],
        "extra_figures": [{"file": "mass.svg", "question": "What do the Weight numbers look like?",
                           "alt": "Dot plot of the 22 participant Weight numbers, from about 52 to 96, with no unit.",
                           "cap": "One dot per participant. Hollow dots are the six participants not yet converted."}],
        "figure_data": {"weights": weights, "six": SIX},
    })

    # ================= H: opposite-leg steps =================
    sp = elig["source_pair_counts"]
    sp_total = sum(sp.values())
    probs.append({
        "key": "opposite_leg", "card": "Many steps of the other leg were not exported",
        "status": {"key": "open", "label": "Open", "detail": "A fix that processes both legs is written; its two trial runs are prepared but have not run.", "needs": "Needs a guarded job (a supervised run with memory limits)."},
        "wrong": "The old conversion code exported one reference leg's steps for each stretch of walking and left out the matching steps of the other leg, even when the source has them. Opposite-leg steps overlap in time, so they are not independent trials.",
        "how": f"We compared every source step in {elig['recordings_checked']} completed recordings with what was exported.",
        "example": f"Of {n(sp_total)} source steps, {n(sp['exported'])} were exported, {n(sp['opposite_reference_leg_not_exported'])} were not exported although their leg's step qualifies, and {n(sp['outside_complete_eligible_task_window'])} fell outside a complete task window.",
        "total_line": f"{n(sp['opposite_reference_leg_not_exported'])} of {n(sp_total)} source steps ({pct(sp['opposite_reference_leg_not_exported'], sp_total)}%) in {elig['recordings_checked']} recordings qualify but were not exported. Another {n(sp['outside_complete_eligible_task_window'])} ({pct(sp['outside_complete_eligible_task_window'], sp_total)}%) lie outside a task window.",
        "total_numbers": {"steps_total": sp_total, "steps_exported": sp["exported"], "steps_recoverable_not_exported": sp["opposite_reference_leg_not_exported"], "steps_outside_window": sp["outside_complete_eligible_task_window"], "recordings": elig["recordings_checked"]},
        "denominator_text": f"Counted over {elig['recordings_checked']} of the 2,301 local recordings (30 overground, 6 treadmill, all AB06). The local source gait tables hold {n(steps_total)} steps in all; how many qualify across them is not measured. Samples are not counted.",
        "table": {"columns": ["Steps in the 36 recordings", "Count", "Share"], "rows": [
            ["Exported", n(sp["exported"]), f"{pct(sp['exported'], sp_total)}%"],
            ["Qualify but not exported (other leg)", n(sp["opposite_reference_leg_not_exported"]), f"{pct(sp['opposite_reference_leg_not_exported'], sp_total)}%"],
            ["Outside a complete task window", n(sp["outside_complete_eligible_task_window"]), f"{pct(sp['outside_complete_eligible_task_window'], sp_total)}%"]], "fold": False},
        "grid": make_grid("checked", rows16(), lambda r, m: six_row(r) or ({"levelground": 100.0, "treadmill": pct(6, 8), "ramp": 0.0, "stair": 0.0}[m] if r == "AB06" else 0.0)),
        "grid_caption": "Share of each group's recordings that the step count covers. Zero means not looked at.",
        "figure_question": "Which participants and tasks have been counted?",
        "direction": "Direction: missing steps lower the number of strides per person and task. They do not change values inside the strides that were exported.",
        "knock_on": [
            {"signal": "Number of strides per participant and task", "verdict": "Also wrong, not yet fixed", "line": "Counts are lower than the source supports.", "evidence": f"{n(sp['opposite_reference_leg_not_exported'])} qualifying steps missing in {elig['recordings_checked']} recordings.", "ref": "gt21-event-eligibility"},
            {"signal": "Treating strides as independent trials", "verdict": "Not checked", "line": "Left and right steps overlap in time; the overlap is documented but its effect on any statistic is not tested.", "evidence": "", "ref": ""},
            {"signal": "Force and centre of pressure of the recovered steps", "verdict": "Not checked", "line": "They would need the force checks to run again.", "evidence": "", "ref": ""},
            {"signal": "Steps already exported", "verdict": "Not checked", "line": "A hardened check that every old step stays identical exists with 16 synthetic tests but has not been run on the real recordings.", "evidence": "", "ref": ""},
            {"signal": "Ramps and stairs", "verdict": "Not checked", "line": "The step count covers overground and treadmill recordings only.", "evidence": "", "ref": ""},
        ],
        "extra_figures": [{"file": "steps.svg", "question": "Which source steps reach the data?",
                           "alt": "One bar of 2,270 source steps split into exported, qualifying but not exported, and outside a task window.",
                           "cap": "Source steps in 36 AB06 recordings (30 overground, 6 treadmill)."}],
        "figure_data": {"steps": sp},
    })

    # ================= I: terrain defaults =================
    ramp_src, stair_src = terrain["source_terrain_by_mode"]["ramp"], terrain["source_terrain_by_mode"]["stair"]
    assert terrain["missing_or_invalid_terrain_values"] == 0 and ramp_src == mode_tot["ramp"] and stair_src == mode_tot["stair"]
    probs.append({
        "key": "terrain_defaults", "card": "Ramp and stair labels could be filled with defaults",
        "status": {"key": "open", "label": "Open", "detail": "A fix that removes the defaults is written and passed 6 small tests. It has not been run in MATLAB and the full rebuild does not use it.", "needs": "Needs a guarded job (a supervised run with memory limits)."},
        "wrong": "If the source lacks a ramp direction the old conversion code still assumes ascent, if it lacks a stair height it uses four inches, and if no labelled step survives it falls back to the whole recording. These would be invented labels.",
        "how": f"We read the terrain label of every local ramp and stair recording. None is missing or invalid. In the {terrain['completed_recordings']} completed recordings, {terrain['terrain_cycles_checked']} ramp and stair steps show no default.",
        "example": f"Of {n(ramp_src)} ramp recordings and {n(stair_src)} stair recordings, 0 lack a label, an incline or a stair height.",
        "total_line": f"0 of {n(ramp_src + stair_src)} local ramp and stair recordings (0%) lack a source label. The risk is latent, so what is exposed is {n(ramp_src + stair_src)} recordings.",
        "total_numbers": {"recordings_affected": 0, "ramp_recordings": ramp_src, "stair_recordings": stair_src, "terrain_steps_checked_in_outputs": terrain["terrain_cycles_checked"], "completed_recordings_checked": terrain["completed_recordings"], "steps_checked": terrain["cycles_checked"], "steps_with_phase_issues": terrain["cycles_with_source_phase_issues"]},
        "denominator_text": "Source labels were checked in all 1,680 local ramp and stair recordings; output checks cover 39 steps of the completed recordings only (all AB06). The six participants not yet converted are not checked.",
        "table": {"columns": ["Task", "Recordings", "Label or size missing"], "rows": [["Ramps", n(ramp_src), "0"], ["Stairs", n(stair_src), "0"]], "fold": False},
        "grid": make_grid("affected", sorted(local) + ["SIX"], lambda r, m: six_row(r) or (0.0 if m in ("ramp", "stair") else None)),
        "grid_caption": "No local ramp or stair recording lacks a label. Level walking and treadmill have no terrain label to check.",
        "figure_question": "Do ramp and stair recordings carry a label and a size?",
        "direction": "Direction: a wrong terrain label changes which strides are grouped together, not the values inside a stride.",
        "knock_on": [
            {"signal": "Which strides are grouped as ramp up, ramp down, stairs", "verdict": "Checked, not affected", "line": "No default was used in the checked outputs.", "evidence": f"{terrain['terrain_cycles_checked']} terrain steps checked; current output fallback observed: no.", "ref": "gt21-events-and-terrain"},
            {"signal": "Step timing from the source gait tables", "verdict": "Checked, not affected", "line": "Every source gait table was read.", "evidence": f"{n(phases['counts']['tables_read'])} tables, {n(phases['counts']['samples'])} samples, 0 non-finite, 0 out of range, 0 of {n(phases['counts']['pairs'])} steps with issues.", "ref": "gt21-all-source-phases"},
            {"signal": "Whether the stair or ramp size is true", "verdict": "Not checked", "line": "Sizes are the authors' annotations, not measured geometry.", "evidence": "", "ref": ""},
            {"signal": "Stair outputs", "verdict": "Not checked", "line": "The rebuild failed on a stair recording, so no stair output has been reviewed.", "evidence": "", "ref": ""},
        ],
        "extra_figures": [{"file": "terrain.svg", "question": "How many ramp and stair recordings lack a label or size?",
                           "alt": "Two bars, 1,015 ramp and 665 stair recordings, each with every recording labelled and none missing.",
                           "cap": "All local ramp and stair recordings."}],
        "figure_data": {"ramp": ramp_src, "stair": stair_src},
    })

    # ================= J: rebuild stopped =================
    rebuilt_total = 102
    probs.append({
        "key": "rebuild_stopped", "card": "Only 102 of 2,301 recordings have been rebuilt, and a stair recording failed",
        "status": {"key": "open", "label": "Open", "detail": "The rebuild stopped when its worker failed on a stair recording.", "needs": "Needs a guarded job to find out why (a supervised run with memory limits)."},
        "wrong": "The full rebuild stopped after 102 recordings (1,299 steps), all from AB06. The native worker failed on a stair recording (AB06, stair 1 left, trial 2). No other participant has been rebuilt, and only one stair recording finished. Two restart attempts also ended with an error.",
        "how": f"The batch status reports 102 of 2,301 completed and 1,299 steps; the output folder holds only AB06: {batch_done['levelground']} level, {batch_done['ramp']} ramp, {batch_done['treadmill']} treadmill and {batch_done['stair']} stair recording.",
        "example": "AB06 level walking, ramps and treadmill are all rebuilt. AB06 stairs: 1 of 42 finished, 1 failed, 40 not tried.",
        "total_line": f"{n(2301 - rebuilt_total)} of 2,301 local recordings ({pct(2301 - rebuilt_total, 2301)}%) are not rebuilt; 15 of 16 local participants have none. Stairs: {n(mode_tot['stair'] - 1)} of {n(mode_tot['stair'])} ({pct(mode_tot['stair'] - 1, mode_tot['stair'])}%) not rebuilt.",
        "total_numbers": {"recordings_rebuilt": 102, "recordings_total": 2301, "steps_rebuilt": 1299, "participants_rebuilt": 1, "participants_total_local": 16, "stair_rebuilt": 1, "stair_total": mode_tot["stair"]},
        "denominator_text": f"Recordings: 2,301 local ones (the {n(six_total)} not yet converted would add more). Steps: 1,299 rebuilt steps; the source holds {n(steps_total)}. Samples are not counted.",
        "table": {"columns": ["Task (AB06)", "Recordings in AB06", "Rebuilt"], "rows": [[MODE_PLAIN[m], str(local["AB06"][m]), str(batch_done[m])] for m in MODES], "fold": False},
        "grid": make_grid("checked", rows16(), lambda r, m: six_row(r) or (pct(batch_done[m], local["AB06"][m]) if r == "AB06" else 0.0)),
        "grid_caption": "Share of each group's recordings that are rebuilt. Zero means not rebuilt.",
        "figure_question": "Which recordings have been rebuilt?",
        "direction": "Direction: every other fix on this page can only be adopted after a rebuild. Source data are not affected.",
        "knock_on": [
            {"signal": "Source timing in all 2,301 recordings", "verdict": "Checked, not affected", "line": "The source gait tables were read, not the rebuilt data.", "evidence": f"{n(phases['counts']['tables_read'])} tables, 0 steps with issues.", "ref": "gt21-all-source-phases"},
            {"signal": "Force values of the 51 completed recordings", "verdict": "Checked, not affected", "line": "They match the original force and marker tables.", "evidence": f"{readback['recordings']} recordings, {n(readback['observations'])} steps; largest difference {readback['maximum_absolute_error']:.0e}.", "ref": "gt21-completed-force-readback"},
            {"signal": "The other 51 completed recordings", "verdict": "Not checked", "line": "Readback has not covered them.", "evidence": "", "ref": ""},
            {"signal": "Quality ranges and filtered version", "verdict": "Not checked", "line": "They need the full rebuild.", "evidence": "", "ref": ""},
            {"signal": "Why the stair recording failed", "verdict": "Not checked", "line": "The cause has not been found.", "evidence": "", "ref": ""},
        ],
        "extra_figures": [],
    })

    # ================= K: legs with no plate =================
    ps = {m: readback["by_mode"][m]["plate_selection"] for m in ("levelground", "treadmill", "ramp")}
    legs_m = {m: ps[m]["assigned"] + ps[m]["no_supported_plate"] for m in ps}
    none_tot = sum(ps[m]["no_supported_plate"] for m in ps)
    legs_tot = sum(legs_m.values())
    sc = core04["force_capture_strides"]
    sc_tot = core04["strides"]
    probs.append({
        "key": "no_plate", "card": "Some legs have no usable force plate",
        "status": {"key": "documented", "label": "Documented only, kept as published",
                   "detail": "Force and centre of pressure are left missing when no plate can be matched to a leg. We never guess.", "needs": ""},
        "wrong": "On the overground walkway a foot does not always land on one plate, and sometimes two feet land on one. Those legs have no force or centre of pressure. This is a limit of the source, not an error we corrected.",
        "how": f"We read back the force of {readback['recordings']} completed recordings and counted the legs that matched a plate by position. Separately, a seeded sample of {n(sc_tot)} strides from 6 participants was classified.",
        "example": f"Of {n(sc_tot)} sampled strides, {n(sc['named plate'])} used a named plate, {n(sc['nearest-foot plates'])} a plate matched by nearest foot, {n(sc['no plate contact'])} had no plate contact, {n(sc['stance not captured as one block (start <= 5%, 45-80% of stride)'])} had stance that was not captured as one block, and {sc['a plate carried both feet in this stride']} had one plate carrying both feet.",
        "total_line": f"{n(none_tot)} of {n(legs_tot)} leg-steps ({pct(none_tot, legs_tot)}%) in the 51 completed recordings have no supported plate: overground {ps['levelground']['no_supported_plate']} of {legs_m['levelground']} ({pct(ps['levelground']['no_supported_plate'], legs_m['levelground'])}%), ramps {ps['ramp']['no_supported_plate']} of {legs_m['ramp']} ({pct(ps['ramp']['no_supported_plate'], legs_m['ramp'])}%), treadmill 0 of {n(legs_m['treadmill'])}.",
        "total_numbers": {"leg_steps_total": legs_tot, "leg_steps_no_plate": none_tot, "overground_no_plate": ps["levelground"]["no_supported_plate"], "overground_leg_steps": legs_m["levelground"], "ramp_no_plate": ps["ramp"]["no_supported_plate"], "ramp_leg_steps": legs_m["ramp"], "treadmill_leg_steps": legs_m["treadmill"],
                          "sample_strides": sc_tot, "sample_no_contact": sc["no plate contact"], "sample_split": sc["stance not captured as one block (start <= 5%, 45-80% of stride)"], "sample_both_feet": sc["a plate carried both feet in this stride"], "sample_named": sc["named plate"], "sample_nearest": sc["nearest-foot plates"]},
        "denominator_text": "A leg-step is one leg's step in one recording (both legs of each step are counted). Counts come from AB06's 51 completed recordings, which is 2.2% of the 2,301, plus a separate seeded sample of 3,389 strides from 6 participants. Stairs are not covered because no stair output was reviewed.",
        "table": {"columns": ["Task (completed recordings)", "Leg-steps", "No supported plate", "Share"], "rows": [
            ["Level walking", n(legs_m["levelground"]), str(ps["levelground"]["no_supported_plate"]), f"{pct(ps['levelground']['no_supported_plate'], legs_m['levelground'])}%"],
            ["Ramps", n(legs_m["ramp"]), str(ps["ramp"]["no_supported_plate"]), f"{pct(ps['ramp']['no_supported_plate'], legs_m['ramp'])}%"],
            ["Treadmill", n(legs_m["treadmill"]), "0", "0%"]], "fold": False},
        "grid": make_grid("affected", rows16(), lambda r, m: six_row(r) or ({"levelground": pct(ps["levelground"]["no_supported_plate"], legs_m["levelground"]), "ramp": pct(ps["ramp"]["no_supported_plate"], legs_m["ramp"]), "treadmill": 0.0, "stair": "nc"}[m] if r == "AB06" else "nc")),
        "grid_caption": "Share of each group's leg-steps with no plate. Only AB06 was read back; every other cell is not checked.",
        "figure_question": "How many leg-steps get a force plate?",
        "direction": "Direction: a leg with no plate has no force or centre of pressure. Its joint angles, moments and powers are separate source columns.",
        "knock_on": [
            {"signal": "Force and centre of pressure of those legs", "verdict": "Left out", "line": "They are missing, not estimated.", "evidence": f"{n(none_tot)} of {n(legs_tot)} leg-steps in the completed recordings.", "ref": "gt21-completed-force-readback by_mode"},
            {"signal": "Joint angles, moments and powers of those legs", "verdict": "Checked, not affected", "line": "They are copied from the authors' files.", "evidence": "Non-force columns identical in 36 recordings when the force rules changed.", "ref": "gt21-force-fix-preservation"},
            {"signal": "Whether the matched plate is the right plate", "verdict": "Not checked", "line": "The match uses marker distance, not an independent contact label.", "evidence": "", "ref": ""},
            {"signal": "Any participant except AB06", "verdict": "Not checked", "line": "No other participant has been read back.", "evidence": "", "ref": ""},
        ],
        "extra_figures": [{"file": "plates.svg", "question": "How many leg-steps get a force plate?",
                           "alt": "Stacked bars of leg-steps with and without a supported plate: overground 74 and 200, treadmill 1,870 and 0, ramp 43 and 35.",
                           "cap": "Leg-steps in the 51 completed AB06 recordings."}],
        "figure_data": {"plates": {m: ps[m] for m in ps}},
    })

    # ================= L1: forward force direction =================
    q95 = [r["z_dominant_heading_deviation_deg_quantiles_50_95_100"][1] for r in conv["recordings"]]
    q100 = [r["z_dominant_heading_deviation_deg_quantiles_50_95_100"][2] for r in conv["recordings"]]
    drawn = [r["recording"] for r in conv["recordings"]]
    cells_l1 = {}
    for rec in drawn:
        s, _, mode = rec.split("/")[0], None, rec.split("/")[2]
        cells_l1[(s, mode)] = cells_l1.get((s, mode), 0) + 1
    probs.append({
        "key": "forward_direction", "card": "Forward force and centre of pressure use one fixed lab direction",
        "status": {"key": "documented", "label": "Documented only, kept as published",
                   "detail": "Forward values are measured on the lab Z axis only. They are kept with this limit stated.", "needs": ""},
        "wrong": "Forward force and forward centre of pressure use the lab Z axis, signed by the measured pelvis direction of each step. A step is kept while the walking path stays within 45 degrees of Z. On curved overground paths the forward value is therefore under-reported. Steps where the direction is unclear are left missing.",
        "how": f"We measured the path direction in 8 recordings drawn at random (seed 20261027). The 95th percentile of the deviation from Z is {min(q95):.1f} to {max(q95):.1f} degrees, lowest on the treadmill and highest overground.",
        "example": f"AB16 level walking: half of the samples deviate by {conv['recordings'][2]['z_dominant_heading_deviation_deg_quantiles_50_95_100'][0]:.1f} degrees or less, 95% by {q95[2]:.1f} degrees or less, and the worst by {q100[2]:.1f}.",
        "total_line": "Forward force and forward centre of pressure in all 2,301 local recordings (100%) carry this limit; how much is lost per recording is measured in 8 only.",
        "total_numbers": {"recordings_with_limit": 2301, "recordings_total": 2301, "recordings_measured": 8, "deviation_p95_min": min(q95), "deviation_p95_max": max(q95), "walking_along_x_samples": hd["walks along lab ±X"], "walking_samples_total": hd_tot},
        "denominator_text": "Recordings: 2,301 local ones; angles measured in 8. Samples: 76,909 on-plate samples in those 8 recordings.",
        "table": {"columns": ["Recording (drawn at random)", "Deviation from Z, 95% of samples (degrees)", "Worst (degrees)"], "rows": [[f"{r['recording'].split('/')[0]} {MODE_PLAIN[r['recording'].split('/')[2]].lower()}", f"{r['z_dominant_heading_deviation_deg_quantiles_50_95_100'][1]:.1f}", f"{r['z_dominant_heading_deviation_deg_quantiles_50_95_100'][2]:.1f}"] for r in conv["recordings"]], "fold": False},
        "grid": make_grid("checked", rows16(), lambda r, m: six_row(r) or (pct(cells_l1.get((r, m), 0), local[r][m]) if r in local else 0.0)),
        "grid_caption": "Share of each group's recordings that were measured. Zero means not looked at.",
        "figure_question": "Which recordings have had their walking direction measured?",
        "direction": "Direction: the path direction affects forward and sideways force and centre of pressure. Vertical values are not affected.",
        "knock_on": [
            {"signal": "Sideways force and centre of pressure", "verdict": "Not checked", "line": "A curved path also tilts the sideways axis; no check has measured it.", "evidence": "", "ref": ""},
            {"signal": "Vertical force and centre-of-pressure height", "verdict": "Checked, not affected", "line": "They do not depend on path direction.", "evidence": "Vertical uses the lab up axis in all 8 recordings.", "ref": "gt21-c01-conventions"},
            {"signal": "Forces on ramps", "verdict": "Not checked", "line": "Ramp forces are along the lab's up axis, not the ramp surface. How much that matters is not measured.", "evidence": "", "ref": ""},
            {"signal": "Joint angles, moments and powers", "verdict": "Not checked", "line": "They do not use this direction; no run has compared them.", "evidence": "", "ref": ""},
        ],
        "extra_figures": [{"file": "heading.svg", "question": "Which way is the person facing when a foot is on a plate?",
                           "alt": "Bars of on-plate samples in 8 recordings: 72,143 facing negative Z, 4,486 facing positive Z, 280 walking along X.",
                           "cap": "On-plate samples in 8 recordings drawn at random (seed 20261027)."}],
        "figure_data": {"heading": hd},
    })

    # ================= L2: centre of pressure origin =================
    probs.append({
        "key": "cop_origin", "card": "Centre of pressure is measured from the outer ankle marker, not from the decided origin",
        "status": {"key": "decided", "label": "Decided by José, fix not yet run",
                   "detail": "José decided on 23 November 2026: the centre of pressure moves with the foot, with its origin 100 mm forward of the ankle joint centre along the foot's heel-to-toe direction. The conversion code has not been changed or run for this.",
                   "needs": "Needs the ankle joint centre and the foot's direction for every sample, from markers. Whether the markers give them: not checked. The current offset from the outer ankle marker is not measured."},
        "wrong": "Centre of pressure is stored relative to the outer ankle marker, not the ankle joint centre. The distance between the two is not measured. The authors' own centre of pressure is also filtered at 15 Hz by default, and is set to the plate origin when the plate sees almost no load; our code leaves those samples missing.",
        "how": f"The authors' scripts were read line by line. In 8 sampled recordings the centre of pressure lies a median of {conv['pooled']['cop_to_nearer_foot_median_m'] * 100:.1f} cm from the nearer foot, so it lands near the foot.",
        "example": f"A median distance of {conv['pooled']['cop_to_nearer_foot_median_m'] * 100:.1f} cm to the nearer foot says the values land near the right foot. It does not say how far they sit from the ankle joint.",
        "total_line": "All centre-of-pressure columns in all 2,301 local recordings (100%) are relative to the ankle marker, not to the decided origin (100 mm forward of the ankle joint centre in the foot's frame). The offset to the joint is not measured.",
        "total_numbers": {"recordings_affected": 2301, "recordings_total": 2301, "median_cop_to_foot_cm": round(conv["pooled"]["cop_to_nearer_foot_median_m"] * 100, 1), "sampled_recordings": 8},
        "denominator_text": "Recordings: 2,301 local ones. Samples are not counted. 'Affected' means the stated origin applies.",
        "table": {"columns": ["Check", "Result"], "rows": [["Median distance from centre of pressure to the nearer foot, 8 recordings", f"{conv['pooled']['cop_to_nearer_foot_median_m'] * 100:.1f} cm"], ["Distance to the ankle joint centre", "Not measured"]], "fold": False},
        "grid": make_grid("affected", rows16(), lambda r, m: six_row(r) or 100.0),
        "grid_caption": "Every centre-of-pressure column is relative to the ankle marker.",
        "figure_question": "Which recordings carry centre of pressure relative to the ankle marker?",
        "direction": "Direction: the origin offsets all centre-of-pressure positions by a roughly constant amount. Forces and angles are unaffected.",
        "knock_on": [
            {"signal": "Centre-of-pressure positions", "verdict": "Not checked", "line": "Every value is shifted by the unmeasured ankle-marker offset.", "evidence": "", "ref": ""},
            {"signal": "Forces and joint angles", "verdict": "Checked, not affected", "line": "They do not use the centre of pressure.", "evidence": "Forces come from plate force columns and angles from joint angle files.", "ref": "gt21-c01-conventions channel_policy"},
            {"signal": "Anything computed from centre of pressure, such as moment arms", "verdict": "Not checked", "line": "No such quantity is exported or tested.", "evidence": "", "ref": ""},
        ],
        "extra_figures": [],
    })

    checked_fine = [
        f"All {n(phases['counts']['tables_read'])} source gait-phase tables of the 16 local participants were read: {n(phases['counts']['samples'])} samples, 0 non-finite or out of range, and 0 of {n(phases['counts']['pairs'])} steps with a timing problem.",
        f"All {n(terrain['source_terrain_recordings'])} local ramp and stair recordings carry a terrain label and a positive incline or stair height.",
        f"Force values of {readback['recordings']} completed recordings ({n(readback['observations'])} steps) match the original force and marker tables; the largest difference is {readback['maximum_absolute_error']:.0e}.",
        "The sign test on 648 leg channels (6 participants, seeded) found 0 wrong signs; 127 channels were left undecided and are not counted as passed.",
        "Vertical force and centre-of-pressure height use the lab's up axis; the lab frame was right-handed in all 8 sampled recordings.",
    ]
    other_limits = [
        "Plate moments are not exported: their reference point and sign are not stated, and values of hundreds of newton-metres on contact show they are not free moments.",
        "Overground files include a virtual 'Combined' plate (a force-weighted merge of the real plates) that we do not separate from its parts.",
        "Static-pose file choice in the authors' script depends on file ordering, so the intended calibration for a participant is unknown.",
        "The 2024 source folder is a live working copy: one file in AB28 is dated October 2026, so each download re-lists the folder first.",
        "No producer log ties the shipped force-conversion tools to the published force files; the frame is corroborated by data, not proven by the producer.",
    ]
    out = {
        "task_id": "GT21-problems-page", "part": "problem scope and knock-on analysis for the Georgia Tech 2021 page",
        "scientific_approval": False, "builder": "contributor_tools/build_gt21_problem_scope.py",
        "probe": "docs/quality/audits/gt21-problem-scope-probe.json (contributor_tools/probe_gt21_problem_scope.py)",
        "seed": SEED, "denominators": den, "verdict_words": VERDICTS,
        "status_words": ["Fixed in a checked pilot", "Decided by José, fix not yet run", "Open", "Documented only, kept as published"],
        "problems": probs, "checked_fine": checked_fine, "other_limits": other_limits,
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", OUT.relative_to(ROOT), len(probs), "problems")


if __name__ == "__main__":
    main()
