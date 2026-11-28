#!/usr/bin/env python3
"""Write the UMich 2021 problem-scope file and draw the figures of its dataset page.

Inputs (small files only; no table file is opened):
  the local review package v4 (manifest, dataset index, limitations, exclusions, evidence/*.csv),
  docs/quality/audits/um21-r01-fix-scope.json (the source counts of the six earlier fix cards).
Outputs:
  docs/quality/audits/um21-problem-scope.json  one card per problem: text, counts, grid, knock-on effects
  docs/datasets/um21/figures/*.svg             scope grids for the new cards, the knee-marker figure, the
                                               pressure-point legs figure, the power-gap figure, two overview figures

    python3 contributor_tools/build_um21_problem_scope.py

Numbers come from the package or from the verified handoffs named next to them in the comments.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "contributor_tools"))
import build_um21_scope_figures as F  # noqa: E402  (shared figure style; importing it runs nothing)

PKG = ROOT / "converted_datasets/reconversion_v2/um21_r01_package_v4"
OLD_SCOPE = ROOT / "docs/quality/audits/um21-r01-fix-scope.json"
OUT = ROOT / "docs/quality/audits/um21-problem-scope.json"
ROWS = [f"AB{i:02d}" for i in range(1, 11)]
COLS = ["d10", "d5", "i0", "i5", "i10"]
COND = {"d10": "10° decline", "d5": "5° decline", "i0": "level", "i5": "5° incline", "i10": "10° incline"}
SIX_LEFT_OUT = {"AB01/d10", "AB01/d5", "AB01/i5", "AB08/i10", "AB09/i10", "AB10/i0"}
# Distances of markers outward from the pelvis midline (m), median per recording and leg, from the independent
# check of 14 legs in 7 recordings (handoff UM21-S02-verify, knee_marker_names.typical_m).
KNEE_MARKER_RANGES = [("Knee marker KNE", 0.006, 0.061), ("Knee marker KNEM", 0.13, 0.20), ("Thigh marker GT", 0.17, 0.21),
                      ("Thigh marker THI", 0.17, 0.20), ("Shank marker TIB", 0.13, 0.20)]


def js(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def pct(a, b):
    return round(100 * a / b, 1)


def rec_code(source_recording_id: str) -> str:
    parts = source_recording_id.split("/")
    return f"{parts[1]}/{parts[3]}"


def grid(cells, caption):
    return {"rows": ROWS, "cols": COLS, "cols_plain": [COND[c] for c in COLS], "cells": cells, "caption": caption}


def hbar(plt, rows, name, xlabel, colors, height=3.3):
    fig, ax = plt.subplots(figsize=(F.WIDTH_IN, height), layout="constrained")
    ys = list(range(len(rows)))[::-1]
    for y, (lab, val), col in zip(ys, rows, colors):
        ax.barh(y, val, color=col, height=.62, zorder=2)
        ax.annotate(f"{val:,}", (val, y), xytext=(4, 0), textcoords="offset points", va="center", fontsize=10)
    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in rows])
    ax.set_xlabel(xlabel)
    ax.set_xlim(0, max(r[1] for r in rows) * 1.28)
    ax.grid(axis="x", color=F.GREY, lw=0.4, alpha=0.6, zorder=0)
    F.save(fig, name)
    plt.close(fig)


def main():
    manifest, index, lim = js(PKG / "manifest.json"), js(PKG / "dataset_index.json"), js(PKG / "limitations.json")
    old = {f["key"]: f for f in js(OLD_SCOPE)["fixes"]}
    L = {x["id"]: x for x in lim["limitations"]}
    counts = manifest["counts"]
    full, filtered = counts["observations_full"], counts["observations_filtered"]
    recs = {rec_code(r["source_recording_id"]): r for r in index["recordings"]}
    assert len(recs) == 44 and not (set(recs) & SIX_LEFT_OUT), "the package must hold the 44 kept recordings"
    all_cells = {f"{r}/{c}": (100.0 if f"{r}/{c}" in recs else None) for r in ROWS for c in COLS}

    # ---- pressure point legs (evidence/cop_legs.csv)
    with (PKG / "evidence/cop_legs.csv").open(newline="", encoding="utf-8") as fh:
        legs = list(csv.DictReader(fh))
    assert len(legs) == 88
    pub = [x for x in legs if x["status"] == "published"]
    held = [x for x in legs if x["status"] != "published"]
    assert (len(pub), len(held)) == (L["cop_estimated_plate_position"]["legs_published"], L["cop_estimated_plate_position"]["legs_held"]) == (60, 28)

    def s(xs):
        return sum(int(x["strides"]) for x in xs)

    ruling = [x for x in held if x["pending_by_ruling"] == "True"]
    rest = [x for x in held if x["pending_by_ruling"] != "True"]
    moment = [x for x in rest if "hold-out" in x["reasons"]]
    toe = [x for x in rest if "toe-off" in x["reasons"]]
    plate = [x for x in rest if x not in moment and x not in toe]
    assert all("plate not loaded" in x["reasons"] for x in plate)
    assert len(ruling) + len(moment) + len(toe) + len(plate) == 28
    strides_held = L["cop_held_leg"]["observations"]
    strides_pub = L["cop_estimated_plate_position"]["observations"]
    assert s(held) == strides_held and s(pub) - strides_pub == 21
    cop_cells = {}
    for key, v in all_cells.items():
        if v is None:
            cop_cells[key] = None
            continue
        rows = [x for x in legs if x["recording"] == key]
        cop_cells[key] = round(100 * s([x for x in rows if x["status"] != "published"]) / s(rows), 1)
    back = L["cop_held_pending_ruling"]
    back_recs = set(back["recordings_named"])
    assert back_recs == {x["recording"] for x in ruling} and back["observations"] == s(ruling) == 829
    assert sum(recs[r]["observations_full"] for r in back_recs) == 829
    back_cells = {k: (None if v is None else (100.0 if k in back_recs else 0.0)) for k, v in all_cells.items()}
    ab01_level_toe = min(float(x["toe_off_within_4cm_fraction"]) for x in legs if x["recording"] == "AB01/i0")
    assert ab01_level_toe == 1.0

    # ---- angle columns (dataset_index finite counts)
    fin = index["finite_values_by_column"]["phase"]["full"]
    ang = [("Pelvis tilt", "pelvis_sagittal_angle_rad"), ("Hip angle", "hip_flexion_angle_ipsi_rad"), ("Knee angle", "knee_flexion_angle_ipsi_rad"),
           ("Ankle angle", "ankle_dorsiflexion_angle_ipsi_rad"), ("Thigh angle", "thigh_sagittal_angle_ipsi_rad"),
           ("Shank angle", "shank_sagittal_angle_ipsi_rad"), ("Foot angle", "foot_sagittal_angle_ipsi_rad")]
    ang_rows = []
    for name, col in ang:
        assert fin[col] % 150 == 0
        have = fin[col] // 150
        ang_rows.append([name, f"{have:,}", f"{full - have:,}"])
    miss = L["angle_columns_missing_in_stride"]

    # ---- power gap (limitations.json)
    gap = L["power_from_moment_and_speed"]["gap_source_power_vs_moment_times_speed"]
    joints = [("Hip", "hip_flexion_power_ipsi_W_kg"), ("Knee", "knee_flexion_power_ipsi_W_kg"), ("Ankle", "ankle_dorsiflexion_power_ipsi_W_kg")]
    pw_rows = [[j, f"{100 * gap[c]['median_nrms']:.0f}%", f"{100 * gap[c]['p90_nrms']:.0f}%", f"{gap[c]['observations_compared']:,} of {gap[c]['observations']:,}"]
               for j, c in joints]
    med = {j: round(100 * gap[c]["median_nrms"]) for j, c in joints}
    p90 = {j: round(100 * gap[c]["p90_nrms"]) for j, c in joints}

    sign_who = js(F.FIG_DIR / "figures.json")["sign_example"]["who"]
    V = {"fixed": "Also wrong, fixed", "ok": "Checked, not affected", "left": "Left out", "nc": "Not checked", "open": "Open limit"}

    def ko(verdict, signal, line, evidence=""):
        return {"signal": signal, "verdict": V[verdict], "line": line, "evidence": evidence}

    cards = []

    def add(key, section, c):
        cards.append(dict(c, key=key, section=section))

    def carry(key):  # source counts of an earlier fix card, measured before that fix
        o = old[key]
        return {"total_line": o["total_line"], "denominator_text": o["denominator_text"], "table": o["table"], "grid": dict(o["grid"], caption=o["grid_caption"])}

    # 1. task timing
    add("clock", "Task timing", {
        "title": "Task timing was off in some recordings", "short": "6 of 50 recordings left out whole",
        "wrong": "The published task intervals (when belt speed or slope changes) were timed on the belt-speed record, not on the motion data. In 4 of 50 treadmill recordings that clock is off by 1.7 to 7 s, and 2 more cannot be checked, so strides near a change can carry the wrong task label.",
        "how": "We lined up the belt-speed record with the belt speed measured from heel and toe markers. 44 recordings agree within half a second.",
        "example": "AB09 at 10° incline: the best shift is 6.85 s, and the belt-speed error drops from 0.67 to 0.07 m/s at that shift, so the recording is left out. AB01 at 5° incline is an exact copy of its 10° incline recording and is also left out.",
        "figures": [{"kind": "published", "src": "um21-clock.svg", "side": "before", "label": "Before and after, per recording",
                     "alt": "Shift of the task timing for each of 50 treadmill recordings. Most sit in a narrow band near zero; four sit 1.7 to 7 seconds away and two cannot be checked.",
                     "caption": "Shift that best lines up the belt-speed record with belt speed from the markers. Crosses at the bottom cannot be checked."}],
        **carry("clock"),
        "knock_on": [
            ko("ok", "Task labels in the 44 recordings we kept", "None of them is off by more than half a second.", "44 of 50 recordings agree within 0.5 s; the six that do not are left out."),
            ko("left", "Task labels in the six left-out recordings", "294 stride-in or stride-out decisions would change if the clock were corrected, so we released none of them.", "294 changed decisions in the four recordings with a measured shift; the other two cannot be evaluated."),
            ko("ok", "Signal values in the kept recordings", "The clock only decides task labels. Nothing in a kept recording was shifted or edited for it.", "The six recordings are removed whole; no interval is shifted or estimated."),
            ko("left", "What each participant still has", "AB01 loses 10° decline, 5° decline and 5° incline; AB08 loses 10° incline; AB09 loses 10° incline; AB10 loses level.", "The package holds 44 recordings and none of these six."),
            ko("nc", "Exact position of each speed or slope change in the kept recordings", "Only checked to within half a second; finer timing is not checked."),
        ]})

    # 2. joint angles against gravity
    add("angle_zero", "Pelvis, segment and joint angles", {
        "title": "Joint angles are measured from markers against gravity",
        "short": f"All {len(recs)} recordings; angle columns missing in {miss['observations']} strides",
        "wrong": "The source's own joint angles carry the zero position of the motion-capture software, and that zero is not published. In three recordings probed before the rebuild, the median difference between the published ankle and the ankle from markers was 0.3 to 6.5° and changed with the leg and the trial, so it is not one constant that could be subtracted.",
        "how": "Thigh, shank and foot angles come from the markers, each in that leg's own side-view plane and measured from gravity (straight down for thigh and shank, forward horizontal for the foot). Hip, knee and ankle angles are differences of these: hip is thigh minus pelvis, knee is thigh minus shank, ankle is foot minus shank. A second implementation recomputed 16 legs and 176 leg-columns of angles and speeds: the largest difference was 0.0 rad and the pattern of missing values was identical.",
        "did": f"All hip, knee, ankle, thigh, shank and foot angles in this version are computed this way, and the foot angle and its speed are now released. Nothing is filled in: where a needed marker is not visible, or the pelvis differs from the pelvis from markers by more than 1°, that stride's angle columns are missing ({miss['observations']} strides in {miss['recordings']} recordings). One stride whose leg plane swung more than 60° from the walking direction has its plane-dependent columns held ({L['plane_glitch_hold']['observations']} stride, already empty).",
        "example": "AB06 at 5° incline: the published ankle sat 4.7° (right leg) and 6.1° (left leg) from the ankle from markers at the median.",
        "figures": [],
        "total_line": f"All {len(recs)} recordings, {full:,} strides in the full version: every angle column is computed from markers.",
        "denominator_text": f"Strides are counted in the full version ({full:,}). The table shows how many strides have a value for each angle column.",
        "table": {"columns": ["Angle column", "Strides with a value", "Strides missing"], "rows": ang_rows, "fold": False},
        "grid": grid(all_cells, "Every recording in this version is affected."),
        "knock_on": [
            ko("ok", "Pelvis tilt", "Kept from the earlier version and compared with the pelvis from markers for every stride.", "A stride that disagrees by more than 1° has its angle columns left missing."),
            ko("fixed", "Thigh, shank and foot angle speeds", "Follow the new angles, with the same derivative method as before.", "Recomputed on 16 legs by a second implementation: no difference."),
            ko("fixed", "Joint power", "Power is now the published moment times these speeds (see the power card)."),
            ko("ok", "Joint moments", "Do not depend on the angles, so they are carried over unchanged.", "Moments are identical to the earlier version in a seeded sample of strides."),
            ko("fixed", "Pressure point", "Built in the same side-view plane and with the same foot angle (see the pressure-point card)."),
            ko("nc", "Where the new zero sits against a standing posture", "No standing recording or reference range was used to check the zero; only coarse limits were applied."),
        ]})

    # 3. knee marker names
    add("knee_markers", "Pelvis, segment and joint angles", {
        "title": "The knee marker names are reversed in the source", "short": f"All {len(recs)} recordings, 88 legs",
        "wrong": "In this source the marker named KNEM lies on the outer (lateral) side of the knee and KNE on the inner (medial) side. That is the reverse of the usual reading of the names. Each leg's side-view plane is built from the knee axis, so the assignment matters.",
        "how": "For every leg we measured how far each marker sits outward from the middle of the pelvis, along the line between the two front hip markers. In 14 legs of 7 recordings, checked independently, KNEM sat 0.117 to 0.141 m further out than KNE and was nearer the thigh markers in every leg. Across all 88 legs the build found the outer marker at least 0.110 m beyond the inner one. The ankle markers are named the usual way, 0.072 to 0.087 m apart.",
        "did": "The side-view plane is built with KNEM as the lateral marker and KNE as the medial marker. Nothing else was changed for it. The reversal is written in the package's list of limitations.",
        "example": "Across the 14 legs checked independently, the typical outward distance was 0.13 to 0.20 m for KNEM and 0.006 to 0.061 m for KNE.",
        "figures": [{"src": "knee-markers.svg", "question": "How far outward from the pelvis midline does each marker sit?",
                     "alt": "Range bars of outward distance from the pelvis midline. Knee marker KNEM is 0.13 to 0.20 metres, like the thigh and shank markers; knee marker KNE is 0.006 to 0.061 metres.",
                     "caption": "Typical outward distance per recording and leg, 14 legs in 7 recordings. A marker on the outer side of the knee sits near the thigh and shank markers."}],
        "total_line": f"All {len(recs)} recordings, 88 legs, {full:,} strides in the full version.",
        "denominator_text": "Legs are counted in the 44 kept recordings (88 legs). The independent check covered 14 of them.",
        "table": {"columns": ["Check", "Legs", "Result"], "rows": [
            ["Independent check: outward distance of KNEM against KNE", "14 (7 recordings)", "KNEM further out in 14 of 14, by 0.117 to 0.141 m"],
            ["Independent check: which knee marker is nearer the thigh markers", "14 (7 recordings)", "KNEM in 14 of 14"],
            ["Build summary: outer minus inner marker", "88 (44 recordings)", "At least 0.110 m, every leg valid"]], "fold": False},
        "grid": grid(all_cells, "Every recording in this version is affected."),
        "knock_on": [
            ko("fixed", "Thigh, shank, knee and foot angles", "Built with the corrected knee side."),
            ko("ok", "Ankle markers", "Named the usual way, so nothing is swapped at the ankle.", "Outer minus inner ankle marker is 0.072 to 0.087 m."),
            ko("nc", "A marker-set description or photograph", "None was seen. The evidence is marker positions only."),
        ]})

    # 4. pelvis backwards
    add("pelvis_backwards", "Pelvis, segment and joint angles", {
        "title": "One recording's pelvis was computed facing backwards", "short": "1 of 44 recordings (AB04 level)",
        "wrong": "In AB04 level walking the motion-capture software computed the pelvis facing backwards, so its stored tilt has the wrong sign.",
        "how": "The published tilt is the mirror image of the tilt computed from the pelvis markers.",
        "example": "AB04 level walking, right leg: the pelvis tilt is multiplied by +1 there and by −1 in the other 43 recordings.",
        "figures": [{"kind": "published", "src": "um21-pelvis-before.svg", "side": "before", "label": "Before: as published",
                     "alt": "Published pelvis tilt is the mirror image of tilt computed from the pelvis markers."},
                    {"kind": "published", "src": "um21-pelvis-after.svg", "side": "after", "label": "After: sign flipped",
                     "alt": "Published pelvis tilt times minus one overlaps the marker tilt.",
                     "caption": "Shown with the source sign (forward tilt positive); LocoHub files store pelvis tilt with the opposite sign."}],
        **carry("pelvis_backwards"),
        "direction": "Hip angle is thigh minus pelvis, so a wrongly signed pelvis would reach it. Thigh, shank and foot angles come from markers and do not use the source's pelvis.",
        "knock_on": [
            ko("ok", "Thigh, shank and foot angles", "Measured from markers, so they do not use the source's pelvis tilt."),
            ko("ok", "Hip angle", "Uses the pelvis, so the pelvis is checked against the pelvis from markers in every stride.", f"A stride that disagrees by more than 1° has its angle columns missing ({miss['observations']} strides in {miss['recordings']} recordings, from this rule or from a hidden marker)."),
            ko("ok", "Pelvis tilt speed", "Unchanged from the earlier version, where it matched the slope of the released tilt in all strides.", "Earlier check: lowest agreement 1.00 in all 7,545 strides."),
            ko("ok", "Hip, knee and ankle moments", "Not affected.", "They do not depend on the angles and are carried over unchanged."),
        ]})

    # 5. sign rule
    add("sign_rule", "Pelvis, segment and joint angles", {
        "title": "Pelvis tilt direction follows one sign rule", "short": "All 44 recordings; pelvis tilt only",
        "wrong": "The source reports forward pelvis tilt as positive. LocoHub's rule (counterclockwise is positive) makes forward tilt negative.",
        "how": "We checked the sign of each angle and moment against marker and force-plate evidence.",
        "example": "AB01 level walking, right leg: pelvis tilt is multiplied by −1; hip, knee and ankle are not changed by the rule.",
        "figures": [{"src": "sign-before.svg", "question": "Before: as the source publishes it (forward tilt is positive)",
                     "alt": "One stride of pelvis tilt as the source publishes it; forward tilt is up."},
                    {"src": "sign-after.svg", "question": "After: LocoHub's rule (forward tilt is negative)",
                     "alt": "The same stride after multiplying by minus one; forward tilt is down.",
                     "caption": f"One stride drawn at random: {sign_who}. The source sign is the released value times −1, since the rule is an exact −1."}],
        **carry("sign_rule"),
        "direction": "Only the pelvis tilt is flipped. Hip, knee and ankle angles are now differences of marker angles and point the way their names say.",
        "knock_on": [
            ko("ok", "Thigh, shank and foot angles", "Measured from markers against gravity, so the rule does not touch them."),
            ko("ok", "Hip, knee and ankle angles", "Each points the way its name says.", "Against markers, the published sign matched in 16 of 16 legs for each of hip, knee and ankle (earlier check)."),
            ko("ok", "Hip, knee and ankle moments", "Not flipped.", "Against force plates the published sign matched in 16 of 16 legs for knee and ankle and 14 of 16 for hip (earlier check)."),
            ko("ok", "Powers", "Power is now moment times joint speed, so its sign follows the moment and the speed, not this rule."),
            ko("nc", "Other datasets' pelvis tilt", "Not part of this page."),
        ]})

    # 6. thigh and shank
    add("thigh_shank", "Pelvis, segment and joint angles", {
        "title": "Thigh and shank angles are now measured, not built from a formula", "short": "All 44 recordings; the earlier formula was off by 2° to 58°",
        "wrong": "Earlier rebuild code added pelvis tilt to the hip angle, but the dataset's authors subtract it, so the thigh angle was off by about twice the pelvis tilt. The older thigh and shank columns are not trusted.",
        "how": "Hip minus pelvis followed the thigh angle computed from the markers within a few degrees; the markers use the bump at the top of the thigh bone, so a small offset was expected.",
        "example": "AB08 at 5° incline, right leg: the earlier rebuild was about 38° off in the example stride.",
        "figures": [{"kind": "published", "src": "um21-thigh-before.svg", "side": "before", "label": "Before: the earlier rebuild",
                     "alt": "Pelvis plus hip runs far above the thigh angle from markers for the whole stride."}],
        **carry("thigh_shank"),
        "direction": "In this version thigh, shank and foot are measured from markers, and hip, knee and ankle are their differences.",
        "knock_on": [
            ko("fixed", "Thigh and shank angles", "Measured from the markers in each leg's own plane.", "Second implementation on 16 legs: largest difference 0.0 rad."),
            ko("fixed", "Foot angle", "Now released, measured from the heel and toe markers.", f"{fin['foot_sagittal_angle_ipsi_rad'] // 150:,} of {full:,} strides have a value."),
            ko("fixed", "Thigh, shank and foot angle speeds", "Follow the new angles."),
            ko("ok", "Hip angle", "Thigh from markers minus the pelvis, which is checked against the pelvis from markers."),
            ko("ok", "Hip, knee and ankle moments", "Not affected: the source calculates them from forces, not from these angles."),
        ]})

    # 7. ankle turned 180 degrees (retired)
    add("ankle_180", "Pelvis, segment and joint angles", {
        "title": "Part of one ankle recording was turned 180°", "short": "22 strides of 1 recording; no longer applies",
        "wrong": "For 5,429 frames of one recording's right ankle (AB07, 10° incline) the software reported the ankle in an equivalent but different form that shifts it by about 180°. The strides inside sat near −160°.",
        "how": "After the turn, the strides fell on the strides outside the stretch: −16.2° to 26.8° against −16.6° to 27.0°.",
        "example": "One stride's tenth sample: −159.6° as published, 20.4° after the turn. Of the 31 strides in the stretch, 20 were turned back, 2 were left out, and 9 were never part of the converted strides.",
        "figures": [{"kind": "published", "src": "um21-ankle-before.svg", "side": "before", "label": "Before: as published",
                     "alt": "Strides inside the stretch sit near minus 160 degrees, far below the strides outside it."}],
        **carry("ankle_180"),
        "knock_on": [
            ko("ok", "Ankle angle in this version", "Computed as foot minus shank from markers, so the source's ankle form does not enter."),
            ko("left", "Two strides with one-sample jumps", "Still left out of both versions.", "They were judged on the source ankle and are not judged again on the ankle from markers."),
            ko("ok", "Hip and knee angles in the same stretch", "The 180° form appeared only in the ankle.", "The form was found in no hip or knee channel (earlier source scan)."),
        ]})

    # 8. joint power
    add("power", "Joint power", {
        "title": "Joint power is recomputed as moment times joint speed",
        "short": f"All {len(recs)} recordings; old gap {med['Hip']}% hip, {med['Knee']}% knee, {med['Ankle']}% ankle",
        "wrong": f"The source's powers do not equal the published moment times the joint speed, and their sign could not be settled from the source alone. Against the moment times our new joint speed, the source's power differed per stride by a median of {med['Hip']}% (hip), {med['Knee']}% (knee) and {med['Ankle']}% (ankle) of the size of the new power; for the larger gaps (90th percentile) {p90['Hip']}%, {p90['Knee']}% and {p90['Ankle']}%.",
        "how": "Per stride, the gap is the square root of the summed squared difference between the source's power and the new power, divided by the square root of the summed squared new power, over the samples where both exist. The median is over strides.",
        "did": "Hip, knee and ankle power are now the published moment times our own joint speed: hip is the thigh speed minus the pelvis speed, knee is the thigh speed minus the shank speed (flexion positive), and ankle is the foot speed minus the shank speed. The source's power values are not carried over. Power is missing wherever the moment or a speed is missing. The 1,407 power entries once held back for an unsettled sign are gone, and 174 entries now record power as missing. After the change the gap is zero.",
        "checked": "A separate readback of every row found power equal to moment times speed to 1e-12 and 29 other columns identical to the earlier version. An independent check of 10 strides drawn with a recorded seed agreed to better than 1e-9 on every row.",
        "example": f"Ankle: the median stride differed by {med['Ankle']}% before, the largest of the three joints; its zero and definition changed in this version.",
        "figures": [{"src": "power-gap.svg", "question": "How far was the source's power from moment times joint speed?",
                     "alt": f"Bars of the typical and large gap between the source's power and moment times speed: hip {med['Hip']} and {p90['Hip']} percent, knee {med['Knee']} and {p90['Knee']} percent, ankle {med['Ankle']} and {p90['Ankle']} percent.",
                     "caption": "Before this version. After it the gap is zero by construction."}],
        "total_line": f"All {len(recs)} recordings, {full:,} strides in the full version: hip, knee and ankle power are recomputed.",
        "denominator_text": "The gap is computed per stride where both the source's power and the new power exist; the table lists how many strides could be compared.",
        "table": {"columns": ["Joint", "Typical gap (median)", "Large gap (90th percentile)", "Strides compared"], "rows": pw_rows, "fold": False},
        "grid": grid(all_cells, "Every recording in this version is affected."),
        "knock_on": [
            ko("ok", "Hip, knee and ankle moments", "Unchanged. They are the input of the power.", "Identical to the earlier version in a seeded sample of strides."),
            ko("fixed", "Power sign", "No sign step is needed any more: the sign follows the moment and the speed."),
            ko("nc", "Power against a range", "Power has no limit, so it was not assessed. It is exact moment times speed, but not checked for plausible size."),
            ko("nc", "Joint work or energy from power", "Not computed or checked here."),
        ]})

    # 9. pressure point
    n_pub, n_held = len(pub), len(held)
    add("cop", "Pressure point", {
        "title": "Pressure point on an estimated plate position, published leg by leg",
        "short": f"{n_pub} of 88 legs published; {n_held} held",
        "wrong": "The source records the pressure point in each force plate's own frame and does not record where the plate sits in the laboratory. A pressure point in the foot's own frame therefore needs an estimated plate position, and that estimate has to be tested before anyone uses it.",
        "how": "The pressure point is expressed in the ankle frame, which turns with the foot, inside that leg's side-view plane; its origin is 100 mm forward of the ankle joint centre along the foot, and sideways is out of the plane. The plate's axis and sign come from the ankle path, its tilt from the belt slope, its forward shift from the hip and knee moments, its height from the rule that the foot rests on the belt, and its sideways shift from the mean foot position.",
        "did": f"A leg publishes the pressure point only if three checks pass: the ankle moment, held out of the fit, is reproduced (correlation at least 0.95); the toe-off end of the pressure point lies within 4 cm of the toe marker in at least 95% of strides (at 0.2 body weight); and the plate is loaded at the leg's heel strikes in at least 95% of them. Each leg is judged on its own, so a passing leg publishes even when the other leg of the recording is held. {n_pub} of 88 legs pass, and {strides_pub:,} strides carry a value. The other {n_held} legs ({strides_held:,} strides) have the three columns present but empty, each with its reason. Published values are labelled 'estimated plate position'.",
        "checked": "A second implementation recomputed 16 legs: the unheld pressure point agreed to 7e-16 m and the verdicts were identical. The pass or hold decision of all 88 legs was recomputed from the per-leg numbers: 60 pass, 28 held. Not independent: the plate axis, sign, tilt and shifts were taken from the build's summary.",
        "example": "AB01 level: both legs publish (held-out ankle moment correlation 0.998, toe-off within 4 cm in 100% of strides). AB07 at 10° decline: the right leg is held (toe-off within 4 cm in 90% of strides) and the left leg publishes alone.",
        "figures": [{"src": "cop-legs.svg", "question": "Which legs publish a pressure point, and why are the others held?",
                     "alt": f"Bars of legs: {n_pub} published; {len(ruling)} held back and left as they are; {len(toe)} failing the toe-off check; {len(plate)} failing the plate-loaded check; {len(moment)} failing the ankle-moment check.",
                     "caption": "One leg of AB04 at 5° incline fails both the toe-off and the plate-loaded check and is counted once, under toe-off."}],
        "total_line": f"{n_held} of 88 legs ({pct(n_held, 88)}%) are held: {strides_held:,} of {full:,} strides ({pct(strides_held, full)}%) have no pressure point. {n_pub} legs publish one for {strides_pub:,} strides.",
        "denominator_text": f"Legs are counted in the 44 kept recordings (88 legs). Of the {s(pub):,} strides in the published legs, {s(pub) - strides_pub} have no loaded plate samples and carry no value, so {strides_pub:,} carry one.",
        "table": {"columns": ["Group of legs", "Legs", "Strides in those legs"], "rows": [
            ["Published", str(n_pub), f"{s(pub):,}"],
            ["Held back and left as they are (see the next card)", str(len(ruling)), f"{s(ruling):,}"],
            ["Toe-off end not within 4 cm of the toe marker in 95% of strides", str(len(toe)), f"{s(toe):,}"],
            ["Plate not loaded at the heel strikes in 95% of strides", str(len(plate)), f"{s(plate):,}"],
            ["Held-out ankle moment not reproduced (correlation 0.924, needs 0.95)", str(len(moment)), f"{s(moment):,}"]], "fold": False},
        "grid": grid(cop_cells, "Share of each recording's strides in held legs; every number is a percent."),
        "knock_on": [
            ko("ok", "Hip, knee and ankle angles", "Not held when the pressure point is held.", f"{miss['observations']} strides have missing angle columns, against {strides_held:,} strides with a held pressure point."),
            ko("ok", "Joint moments and power", "Not held when the pressure point is held.", "The package's note on power says a held pressure point does not hold power."),
            ko("left", "Held legs", f"The three pressure-point columns are present but empty in {strides_held:,} strides, with the reason in each stride's list of empty signals."),
            ko("open", "The plate position is fitted, not measured", "The published pressure point is built on an estimated plate position and has not been compared with a measured foot-frame value."),
            ko("ok", "Heel end of the pressure point", "Reported, but not used to decide a leg.", "The heel marker sits above and behind the sole."),
            ko("nc", "Strides with no loaded plate samples on a published leg", "21 strides have no value, so the pressure point is missing there; missing is never counted as a pass."),
        ]})

    # 10. held-back recordings
    add("held_back", "Pressure point", {
        "title": "Held-back data: five recordings left as they are", "short": f"5 recordings, {back['observations']} strides; pressure point empty",
        "wrong": "In five recordings the pressure point fails its checks in both legs: the 10° incline recordings of AB01, AB02 and AB03 (toe-off within 4 cm in 0 to 21% of strides), the 10° decline recording of AB04 (a 20 cm offset at the heel end that has no explanation), and the 5° decline recording of AB10 (plate loaded at the heel strikes in 94.6% and 94.7% of strides, just under the 95% needed).",
        "how": "The same three checks as on the pressure-point card, applied to each leg.",
        "did": "These five recordings are held back and left as they are. The three pressure-point columns are empty, with the reason in each stride's list of empty signals; their angles, moments and power are published like any other recording's. We did not investigate the cause further.",
        "checked": "The pass or hold decision of all 88 legs was recomputed from the per-leg numbers: 60 pass, 28 held, identical to the build's decision.",
        "example": "AB01 at 10° incline: toe-off within 4 cm in 0% of strides in both legs, while its level recording passes at 100% in both legs.",
        "figures": [],
        "total_line": f"5 of 44 recordings ({pct(5, 44)}%): {back['observations']} of {full:,} strides ({pct(back['observations'], full)}%), 10 of 88 legs.",
        "denominator_text": f"Strides are counted in the full version ({full:,}). All {back['observations']} strides stay in the cleaned version.",
        "table": {"columns": ["Recording", "Strides", "Why the pressure point is held"], "rows": [
            [r.replace("/", ", ").replace("i10", "10° incline").replace("d10", "10° decline").replace("d5", "5° decline"),
             f"{recs[r]['observations_full']:,}",
             {"AB04/d10": "A 20 cm offset at the heel end that has no explanation.",
              "AB10/d5": "Plate loaded at the heel strikes in 94.6% and 94.7% of strides, just under 95%."}.get(r, "Toe-off end within 4 cm of the toe marker in 0 to 21% of strides.")]
            for r in sorted(back_recs)], "fold": False},
        "grid": grid(back_cells, "The five held-back recordings; every number is a percent."),
        "knock_on": [
            ko("ok", "Angles, moments and power in these recordings", "Published as for any other recording."),
            ko("open", "Cause of the toe-off failure in the 10° incline recordings", "Unknown. In the 10° incline recordings checked the toe-off end sat 6 to 11 cm from the toe marker, while the level and 5° incline recordings checked pass in every stride.", "Seen in the check of the build; not investigated further."),
            ko("nc", "Whether the pressure point of these recordings is usable", "Not checked; it is left empty."),
        ]})

    scope = {
        "task_id": "UM21-R01 v3 / CORE-PW01 (package v4)", "scientific_approval": False,
        "builder": "contributor_tools/build_um21_problem_scope.py",
        "package": "converted_datasets/reconversion_v2/um21_r01_package_v4",
        "denominators": {"treadmill_recordings": 50, "kept_recordings": len(recs), "strides_full": full, "strides_cleaned": filtered, "legs": 88,
                         "legs_published": n_pub, "legs_held": n_held},
        "note": "The grids and tables of the six earlier cards (timing, pelvis, sign rule, thigh and shank, ankle) are source counts measured before those fixes, copied from um21-r01-fix-scope.json. The new cards are counted in the v4 package.",
        "cards": cards,
    }
    OUT.write_text(json.dumps(scope, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    # ---- figures
    F.FIG_DIR.mkdir(parents=True, exist_ok=True)
    plt = F.plt_module()
    for c in cards:
        if c["key"] in {"angle_zero", "knee_markers", "power", "cop", "held_back"}:
            F.grid_figure(plt, {"key": c["key"], "grid": c["grid"]})
    fig, ax = plt.subplots(figsize=(F.WIDTH_IN, 3.0), layout="constrained")
    ys = list(range(len(KNEE_MARKER_RANGES)))[::-1]
    for y, (lab, lo, hi) in zip(ys, KNEE_MARKER_RANGES):
        col = F.AFTER if lab.endswith("KNEM") else (F.BEFORE if lab.endswith("KNE") else F.MUTED)
        ax.barh(y, hi - lo, left=lo, color=col, height=.5, zorder=2)
        ax.annotate(f"{lo:g} to {hi:g}", (hi, y), xytext=(4, 0), textcoords="offset points", va="center", fontsize=10)
    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in KNEE_MARKER_RANGES])
    ax.set_xlabel("Distance outward from the pelvis midline (m)")
    ax.set_xlim(0, 0.31)
    ax.grid(axis="x", color=F.GREY, lw=0.4, alpha=0.6, zorder=0)
    F.save(fig, "knee-markers.svg")
    plt.close(fig)
    rows = [("Published", n_pub), ("Held back, left as is", len(ruling)), ("Toe-off check failed", len(toe)),
            ("Plate not loaded at heel strikes", len(plate)), ("Ankle moment not reproduced", len(moment))]
    hbar(plt, rows, "cop-legs.svg", "Legs (of 88)", [F.AFTER, F.BEFORE, F.MUTED, F.MUTED, F.MUTED], height=3.2)
    fig, ax = plt.subplots(figsize=(F.WIDTH_IN, 3.2), layout="constrained")
    ys = list(range(3))[::-1]
    for y, (j, c) in zip(ys, joints):
        a, b = 100 * gap[c]["median_nrms"], 100 * gap[c]["p90_nrms"]
        ax.barh(y + .17, a, height=.32, color=F.BEFORE, zorder=2)
        ax.barh(y - .17, b, height=.32, color=F.MUTED, zorder=2)
        ax.annotate(f"{a:.0f}%", (a, y + .17), xytext=(4, 0), textcoords="offset points", va="center", fontsize=10)
        ax.annotate(f"{b:.0f}%", (b, y - .17), xytext=(4, 0), textcoords="offset points", va="center", fontsize=10)
    ax.set_yticks(ys)
    ax.set_yticklabels([j for j, _ in joints])
    ax.set_xlabel("Gap between source power and moment times speed (%)")
    ax.set_xlim(0, 100 * max(gap[c]["p90_nrms"] for _, c in joints) * 1.25)
    ax.grid(axis="x", color=F.GREY, lw=0.4, alpha=0.6, zorder=0)
    fig.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=F.BEFORE, label="Typical stride (median)"),
                        plt.Rectangle((0, 0), 1, 1, color=F.MUTED, label="Larger gaps (90th percentile)")], loc="outside lower left", ncols=1)
    F.save(fig, "power-gap.svg")
    plt.close(fig)
    byr = counts["exclusions_by_reason"]
    rows = [("Stride too short or too long", byr["upstream_stride_rule"]["t04_2_outside_stride_rule"], F.MUTED),
            ("Sudden ankle jump", byr["upstream_sudden_jump"]["c03_2_sudden_jump"], F.MUTED),
            ("Pressure point too far from foot", byr["assessment_failed"]["L5"], F.BEFORE),
            ("Ankle angle outside possible range", byr["assessment_failed"]["L1"], F.BEFORE)]
    rows.sort(key=lambda r: -r[1])
    hbar(plt, [(a, b) for a, b, _ in rows], "page-left-out.svg", "Strides left out", [c for *_, c in rows], height=2.8)
    short = {"moments_from_v2": "Moments carried over", "power_from_moment_and_speed": "Power recomputed", "knee_marker_labels_swapped": "Knee marker names reversed",
             "cop_estimated_plate_position": "Pressure point, estimated plate", "cop_held_leg": "Pressure point held (leg)",
             "cop_held_pending_ruling": "Held-back recordings", "angle_columns_missing_in_stride": "Angle columns missing",
             "plane_glitch_hold": "Leg-plane glitch held", "plate_position_fitted": "Plate position fitted, not measured"}
    items = sorted(((short[x["id"]], x["observations"]) for x in lim["limitations"]), key=lambda r: -r[1])
    hbar(plt, items, "page-limitations.svg", "Strides touched", [F.MUTED] * len(items), height=3.6)
    print("wrote", OUT.relative_to(ROOT), "and figures to", F.FIG_DIR.relative_to(ROOT), "; cards:", ", ".join(c["key"] for c in cards))


if __name__ == "__main__":
    main()
