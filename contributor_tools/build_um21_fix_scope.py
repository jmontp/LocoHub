#!/usr/bin/env python3
"""Build docs/quality/audits/um21-r01-fix-scope.json (task UM21-R01, follow-up).

For each "What we fixed" card on the UMich 2021 page this records
  1. how much was affected (participants x tasks, strides, samples), and
  2. what else the broken signal could affect, with one verdict per downstream signal.

Reads only small files: the bundle's dataset_index.json and held_signals.csv, the
committed clock census, pelvis-heading audit, 180-degree census and conventions audit,
the committed handoffs, and the probe output docs/quality/audits/um21-r01-fix-scope-probe.json
(written by contributor_tools/probe_um21_fix_scope.py). It never opens a parquet file.
The page builder reads the JSON this script writes; the page has no hand-typed numbers.

Usage: python3 contributor_tools/build_um21_fix_scope.py
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "converted_datasets/reconversion_v2/um21_r01_review_v2"
AUDITS = ROOT / "docs/quality/audits"
HANDOFFS = ROOT / "docs/maintainers/handoffs"
OUT = AUDITS / "um21-r01-fix-scope.json"

SAMPLES = 150
CONDITION = {"d10": "10° decline", "d5": "5° decline", "i0": "level", "i5": "5° incline", "i10": "10° incline"}
COND_ORDER = ["d10", "d5", "i0", "i5", "i10"]
FIXED, OK, LEFT, NC = "Also wrong, fixed", "Checked, not affected", "Left out", "Not checked"
VERDICTS = (FIXED, OK, LEFT, NC)


def n(x):
    return f"{x:,}"


def pct(a, b, digits=1):
    return round(100.0 * a / b, digits)


def name(rec):
    s, c = rec.split("/")
    return f"{s}, {CONDITION[c]}"


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def ko(signal, verdict, line, evidence="", ref=""):
    assert verdict in VERDICTS
    assert verdict == NC or evidence, signal
    return {"signal": signal, "verdict": verdict, "line": line, "evidence": evidence, "ref": ref}


def grid(cells):
    """cells: {rec: pct or None}. All 50 treadmill recordings are keyed; missing means no such recording."""
    return {"rows": [f"AB{i:02d}" for i in range(1, 11)], "cols": COND_ORDER,
            "cols_plain": [CONDITION[c] for c in COND_ORDER], "cells": cells}


def main():
    index = load(BUNDLE / "dataset_index.json")
    recs = {r["recording"]: r for r in index["recordings"]}
    assert len(recs) == 44
    manifest = load(BUNDLE / "manifest.json")
    probe = load(AUDITS / "um21-r01-fix-scope-probe.json")
    pr = probe["per_recording"]
    census = load(AUDITS / "um21-t02-clock-census.json")
    p01 = load(AUDITS / "um21-p01-pelvis-heading.json")
    c03 = load(AUDITS / "um21-c03-episode-census.json")
    q01 = load(HANDOFFS / "UM21-Q01.json")
    with (BUNDLE / "held_signals.csv").open(newline="", encoding="utf-8") as fh:
        held = list(csv.DictReader(fh))

    mapped = {k: v["t04_mapped_observations"] for k, v in recs.items()}
    total_strides = manifest["counts"]["upstream_observations"]  # 7,562
    converted = sum(mapped.values())                             # 7,547
    unmapped = sum(v["unmapped"] for v in recs.values())         # 15
    assert total_strides == converted + unmapped == 7562
    full, filt = manifest["counts"]["full"], manifest["counts"]["filtered"]
    total_samples = total_strides * SAMPLES
    all50 = [f"AB{i:02d}/{c}" for i in range(1, 11) for c in COND_ORDER]
    assert len(all50) == 50
    per_rec_total = {k: mapped[k] + recs[k]["unmapped"] for k in recs}
    assert sum(per_rec_total.values()) == total_strides

    out = {
        "task_id": "UM21-R01",
        "part": "fix scope and knock-on analysis for the UMich 2021 page",
        "scientific_approval": False,
        "builder": "contributor_tools/build_um21_fix_scope.py",
        "probe": "docs/quality/audits/um21-r01-fix-scope-probe.json (contributor_tools/probe_um21_fix_scope.py)",
        "denominators": {
            "treadmill_recordings": 50, "kept_recordings": len(recs),
            "strides_in_converted_set": total_strides, "strides_converted": converted,
            "strides_too_short_or_long_to_convert": unmapped,
            "strides_full_version": full, "strides_cleaned_version": filt,
            "samples_per_stride": SAMPLES, "samples_in_converted_set": total_samples,
            "note": "Percentages use the 7,562 strides of the converted set (7,547 converted plus 15 too short or long to convert) unless a row says otherwise. The clock fix happened before strides existed and uses the 8,626 strides the task windows would have produced in all 50 recordings.",
        },
        "verdict_words": list(VERDICTS),
        "fixes": [],
    }

    # ---------------------------------------------------------------- 1 clock
    mis = {m["record"]: m for m in census["misaligned"]}
    rec_by = {f"{r['subject']}/{r['condition']}": r for r in census["records"]}
    six = list(mis)
    assert len(six) == 6
    all_strides = census["totals"]["strides_as_published_all"]
    kept_strides = census["totals"]["strides_as_published_aligned_only"]
    six_strides = sum(rec_by[k]["written_as_published"] for k in six)
    assert six_strides == all_strides - kept_strides == 1064
    changed = sum(m["decisions_changed"] for m in mis.values())
    hz = 100.0
    rows = []
    for k in six:
        r, m = rec_by[k], mis[k]
        minutes = r["joint_frames"] / hz / 60
        if m["best_lag"] is None:
            status = "Cannot be checked: no belt-speed record"
            shift = None
        else:
            shift = abs(m["best_lag"]) / hz
            status = f"Clock off by {shift:.2f} s"
        if k == "AB01/i5":
            status += "; also an exact copy of AB01 10° incline"
        rows.append({"recording": name(k), "recording_code": k, "strides": r["written_as_published"],
                     "strides_pct": pct(r["written_as_published"], all_strides),
                     "labels_that_would_change": m["decisions_changed"] if m["best_lag"] is not None else None,
                     "shift_s": shift, "minutes": round(minutes, 1), "status": status})
    six_min = round(sum(r["minutes"] for r in rows), 1)
    total_min = round(sum(r["joint_frames"] for r in census["records"]) / hz / 60, 1)
    shifts = sorted(r["shift_s"] for r in rows if r["shift_s"])
    left_by_subject = {}
    for k in six:
        left_by_subject.setdefault(k.split("/")[0], []).append(CONDITION[k.split("/")[1]])
    lost = "; ".join(f"{s} loses {', '.join(v[:-1]) + ' and ' + v[-1] if len(v) > 1 else v[0]}" for s, v in sorted(left_by_subject.items()))
    out["fixes"].append({
        "key": "clock", "card": "Task timing was off in some recordings",
        "total_line": (f"6 of 50 treadmill recordings (12.0%): 1,064 of {n(all_strides)} strides the task windows would have produced (12.3%), "
                       f"about {six_min:g} of {total_min:g} minutes of walking. Four recordings are off by {shifts[0]:.1f} to {shifts[-1]:.1f} s, two cannot be checked."),
        "total_numbers": {"recordings_affected": 6, "recordings_total": 50, "strides_affected": six_strides, "strides_total": all_strides,
                          "strides_pct": pct(six_strides, all_strides), "minutes_affected": six_min, "minutes_total": total_min,
                          "labels_that_would_change": changed},
        "denominator_text": "Strides are counted as the task windows would have produced them before anything was left out (8,626 in all 50 recordings). Samples do not apply: these strides were never converted.",
        "table": {"columns": ["Participant and task", "Strides (of 8,626)", "Task labels that would change", "Why", "Minutes"],
                  "rows": [[r["recording"], f"{n(r['strides'])} ({r['strides_pct']}%)",
                            "unknown" if r["labels_that_would_change"] is None else n(r["labels_that_would_change"]), r["status"], f"{r['minutes']:g}"] for r in rows],
                  "fold": False},
        "grid": grid({k: (100.0 if k in mis else 0.0) for k in all50}),
        "grid_caption": "Share of the recording that carries the wrong task timing (100 means the whole recording).",
        "direction": None,
        "knock_on": [
            ko("Task labels in the 44 recordings we kept", OK,
               "None of them is off by more than half a second.",
               f"44 of 50 recordings agree within 0.5 s (50 samples at 100 per second); the six that do not are left out.",
               "UM21-T02 clock census"),
            ko("Task labels in the six left-out recordings", LEFT,
               f"{changed} stride-in or stride-out decisions would change if the clock were corrected, so we released none of them.",
               f"{changed} changed decisions in the four recordings with a measured shift; the other two cannot be evaluated.",
               "um21-t02-clock-census.json totals/misaligned"),
            ko("Signal values (angles, moments, powers) in the kept recordings", OK,
               "The clock only decides task labels. Nothing in a kept recording was shifted or edited for it.",
               "The six recordings are removed whole; no interval is shifted or estimated.", "UM21-R01 original_vs_fixed"),
            ko("What each participant still has", LEFT, f"{lost}.",
               "Participants lose these conditions from the review version.", "dataset_index.json"),
            ko("Exact position of each speed or slope change in the kept recordings", NC,
               "Only checked to within half a second; finer timing is not checked."),
        ],
    })

    # ---------------------------------------------------------------- 2 AB04 level pelvis
    ab04 = "AB04/i0"
    a_n = mapped[ab04]
    rec04 = [r for r in p01["records"] if r["record"] == ab04][0]
    normal = p01["summary"]["classes"]["normal"]
    pub, vote = p01["summary"]["tilt_votes_normal_published_of_voting"]
    thigh_flip = sum(s["recipes"]["thigh_recipe"]["strides"] - s["recipes"]["thigh_recipe"]["published_pelvis_closer"] for s in rec04["sides"].values())
    thigh_all = sum(s["recipes"]["thigh_recipe"]["strides"] for s in rec04["sides"].values())
    shank_closer_flip = sum(s["recipes"]["shank_recipe"]["strides"] - s["recipes"]["shank_recipe"]["published_pelvis_closer"] for s in rec04["sides"].values())
    shank_err = [s["recipes"]["shank_recipe"] for s in rec04["sides"].values()]
    hip_ok = sum(v["agree_strides"] for k, v in rec04["channel_judgement"].items() if k.startswith("hip_flexion"))
    hip_all = sum(v["strides"] for k, v in rec04["channel_judgement"].items() if k.startswith("hip_flexion"))
    obl = sum(v["strides"] - v["agree_strides"] for k, v in rec04["channel_judgement"].items() if k.startswith("pelvis_obliquity"))
    head_other = max(abs(r["sides"]["R"]["pelvis_rotation_circular_median_deg"]) for r in p01["records"] if r["subject"] == "AB04" and r["record"] != ab04)
    p = pr
    ab04_others = [k for k in p if k.startswith("AB04/") and k != ab04]
    out["fixes"].append({
        "key": "pelvis_backwards", "card": "One recording's pelvis was computed facing backwards",
        "total_line": (f"AB04 level walking only: {a_n} of {n(total_strides)} strides ({pct(a_n, total_strides)}%), "
                       f"{n(a_n * SAMPLES)} of {n(total_samples)} samples ({pct(a_n, total_strides)}%). That is 1 of 44 recordings; all {a_n} strides in it are affected (100%)."),
        "total_numbers": {"recordings_affected": 1, "recordings_total": len(recs), "strides_affected": a_n, "strides_total": total_strides,
                          "strides_pct": pct(a_n, total_strides), "samples_affected": a_n * SAMPLES, "samples_total": total_samples},
        "denominator_text": "Strides are counted in the converted set of 7,562; samples are 150 per stride.",
        "table": {"columns": ["Participant and task", "Strides affected (of strides in the recording)", "Samples"],
                  "rows": [[name(ab04), f"{a_n} of {per_rec_total[ab04]} (100%)", f"{n(a_n * SAMPLES)} of {n(per_rec_total[ab04] * SAMPLES)}"]], "fold": False},
        "grid": grid({k: (100.0 if k == ab04 else 0.0) for k in all50 if k in recs}),
        "grid_caption": "Share of each recording's strides with a backwards pelvis.",
        "direction": "The pelvis feeds the thigh angle, and the thigh feeds the shank. The hip, knee and ankle angles are measured between neighbouring body segments, so they do not depend on which way the pelvis frame faces.",
        "knock_on": [
            ko("Thigh angle", FIXED, "Rebuilt from the flipped pelvis tilt (thigh = hip + pelvis tilt).",
               f"With the flipped tilt the thigh is closer to the marker thigh in {thigh_flip} of {thigh_all} strides checked against markers ({thigh_all // 2} per leg).", "UM21-P01 recipes"),
            ko("Shank angle", FIXED, "Rebuilt from the corrected thigh and the knee. The marker check cannot tell the two signs apart here.",
               f"Shank = thigh − knee holds to rounding in all {n(full)} released strides; against markers the two signs miss by "
               f"{shank_err[0]['median_err_published']:.1f}° and {shank_err[0]['median_err_flipped']:.1f}° (right leg), because this participant's tilt is small (about 2°).",
               "UM21-P01 recipes; probe identity"),
            ko("Pelvis tilt speed", OK, "It follows the published tilt, so it follows the fix.",
               f"The stored speed matches the slope of the released tilt in all {n(full)} strides (lowest agreement {min(v['speed_vs_angle_slope_corr_min']['pelvis'] for v in pr.values()):.2f}).",
               "probe speed_vs_angle"),
            ko("Hip angle", OK, "Not affected: it is measured relative to the thigh and pelvis segments, not to the lab frame.",
               f"It matches the marker hip in {hip_ok} of {hip_all} strides checked ({hip_all // 2} per leg), and its mean ({p[ab04]['hip_mean_deg_mean']:.1f}°) sits between AB04's 5° decline ({p['AB04/d5']['hip_mean_deg_mean']:.1f}°) and 5° incline ({p['AB04/i5']['hip_mean_deg_mean']:.1f}°) recordings.",
               "UM21-P01 channel_judgement; probe"),
            ko("Knee and ankle angles", OK, "Not affected: both are measured between neighbouring segments.",
               "An independent check against force-plate and marker evidence kept their published sign for this recording.", "UM21-P01-verify check 2"),
            ko("Hip, knee and ankle moments and powers", OK, "Not affected: they are expressed in each body segment's own frame.",
               f"The same independent check applied the ordinary moment and power signs here; the ankle moment size ({p[ab04]['ankle_moment_range_mean']:.2f}) lies within AB04's other recordings ({min(p[k]['ankle_moment_range_mean'] for k in ab04_others):.2f} to {max(p[k]['ankle_moment_range_mean'] for k in ab04_others):.2f} N·m/kg).",
               "UM21-P01-verify check 2; probe"),
            ko("Pelvis side tilt and twist", LEFT, "Also backwards in the source (side tilt flipped, twist turned by 180°); we do not release these.",
               f"Side tilt is flipped in {obl} of {hip_all} strides checked ({hip_all // 2} per leg).", "UM21-P01"),
            ko("Foot direction angle", LEFT, "About 180° off in this recording in the source; we do not release it.",
               f"The source value sits near {rec04['sides']['R']['stored_medians_deg']['foot_progression']:.0f}° where the markers give about {rec04['sides']['R']['marker_medians_deg']['foot_progression']:.0f}°.", "UM21-P01 stored_medians_deg"),
            ko("Any other recording being backwards", OK, "No other treadmill recording is.",
               f"Headings of the other 49 recordings lie within ±4.75°, and {n(pub)} of {n(vote)} strides carry the published tilt sign; AB04's other four recordings are within {head_other:.1f}°.",
               "UM21-P01 summary"),
            ko("Five strides at the end of a trial, where the person turns around", NC,
               "In 3 recordings the sign vote is uninformative there; a separate stride check has not been done."),
        ],
    })

    # ---------------------------------------------------------------- 3 sign rule
    flipped_rec = [k for k in recs if k != ab04]
    flipped_strides = sum(mapped[k] for k in flipped_rec)
    out["fixes"].append({
        "key": "sign_rule", "card": "Pelvis tilt direction follows one sign rule",
        "total_line": (f"All 44 recordings, 100%: {n(converted)} of {n(total_strides)} strides ({pct(converted, total_strides)}%; the other {unmapped} were too short or long to convert), "
                       f"{n(converted * SAMPLES)} of {n(total_samples)} samples. In 43 recordings the sign is flipped; in AB04 level it is flipped twice (once for the backwards pelvis, once for the rule), so it ends up as published."),
        "total_numbers": {"recordings_affected": len(recs), "recordings_total": len(recs), "strides_affected": converted, "strides_total": total_strides,
                          "strides_pct": pct(converted, total_strides), "samples_affected": converted * SAMPLES, "samples_total": total_samples,
                          "recordings_sign_flipped": len(flipped_rec), "strides_sign_flipped": flipped_strides},
        "denominator_text": "Strides are counted in the converted set of 7,562; the 15 too short or long to convert never reached this step.",
        "table": {"columns": ["Group", "Recordings", "Strides", "Samples", "What happens to pelvis tilt"],
                  "rows": [["All except AB04 level", str(len(flipped_rec)), f"{n(flipped_strides)} (100% of them)", n(flipped_strides * SAMPLES), "Sign flipped (source forward = +, LocoHub forward = −)"],
                           ["AB04 level walking", "1", f"{a_n} (100%)", n(a_n * SAMPLES), "Flipped twice: ends as published"]], "fold": False},
        "grid": grid({k: 100.0 for k in recs}),
        "grid_caption": "Share of each recording's strides that go through the pelvis sign step (100 everywhere).",
        "direction": "Only the pelvis is flipped. The thigh and shank are built from the pelvis, so they follow it. The hip, knee and ankle angles are published signed in the direction of their name and are not touched.",
        "knock_on": [
            ko("Thigh and shank angles", OK, "They are built after the sign step, so they already use the flipped tilt.",
               f"Thigh = hip + pelvis tilt and shank = thigh − knee hold to rounding in all {n(full)} released strides (largest difference {max(max(v['max_abs_thigh_minus_hip_plus_pelvis_rad'], v['max_abs_shank_minus_thigh_minus_knee_rad']) for v in pr.values()):g} rad).",
               "probe identity; UM21-T04-verify"),
            ko("Pelvis tilt speed", OK, "It was flipped along with the angle.",
               f"The stored speed matches the slope of the released tilt in all {n(full)} strides.", "probe speed_vs_angle"),
            ko("Hip, knee and ankle angles", OK, "Not flipped; each already points the way its name says.",
               "Against markers, the published sign matched in 16 of 16 legs checked for each of hip, knee and ankle.", "UM21-C03 per_channel_best_transform"),
            ko("Hip, knee and ankle moments", OK, "Not flipped.",
               "Against force plates the published sign matched in 16 of 16 legs for the knee and ankle moments and 14 of 16 for the hip moment (the weakest of the three).", "UM21-C03 per_channel_best_transform"),
            ko("Powers", OK, "Their sign is set separately (see the power card).",
               "Power signs come from the moment-times-speed check, not from the pelvis rule.", "UM21-Q01 t04_v2_power_summary"),
            ko("Foot angle", LEFT, "Would follow the same sign rule, but it is not released.",
               "Foot angle carries the unchecked ankle zero point.", "UM21-R01 columns_not_released"),
            ko("Other datasets' pelvis tilt", NC, "Not part of this page; each dataset has its own sign step."),
        ],
    })

    # ---------------------------------------------------------------- 4 thigh/shank
    rows = []
    errs = {}
    for k in sorted(recs, key=lambda r: (r.split("/")[0], COND_ORDER.index(r.split("/")[1]))):
        if k == ab04:
            rows.append([name(k), f"{mapped[k]} of {per_rec_total[k]} (100%)", "not computed: the old build used the backwards pelvis"])
            continue
        e = 2 * abs(pr[k]["pelvis_mean_deg_mean"])
        errs[k] = e
        rows.append([name(k), f"{mapped[k]} of {per_rec_total[k]} (100%)", f"about {e:.0f}°"])
    lo, hi = min(errs.values()), max(errs.values())
    knee_in = all(v["max_abs_shank_minus_thigh_minus_knee_rad"] < 1e-9 for v in pr.values())
    assert knee_in
    out["fixes"].append({
        "key": "thigh_shank", "card": "Thigh and shank angles are rebuilt",
        "total_line": (f"All 44 recordings, 100%: every one of the {n(converted)} converted strides ({pct(converted, total_strides)}% of {n(total_strides)}; the other {unmapped} were never converted), "
                       f"{n(converted * SAMPLES)} samples each for thigh and shank. The earlier rebuild was off by about {lo:.0f}° to {hi:.0f}° on average, depending on how far the participant tilts the pelvis."),
        "total_numbers": {"recordings_affected": len(recs), "recordings_total": len(recs), "strides_affected": converted, "strides_total": total_strides,
                          "strides_pct": pct(converted, total_strides), "samples_affected": converted * SAMPLES, "samples_total": total_samples,
                          "error_deg_min": round(lo, 1), "error_deg_max": round(hi, 1)},
        "denominator_text": "The earlier thigh and shank columns were never released. The error is twice the recording's average pelvis tilt.",
        "table": {"columns": ["Participant and task", "Strides affected", "Earlier rebuild off by (average over the stride)"], "rows": rows, "fold": True},
        "grid": grid({k: 100.0 for k in recs}),
        "grid_caption": "Share of each recording's strides whose earlier thigh and shank were wrong (100 everywhere).",
        "direction": ("Which way the dependence runs: thigh = hip + pelvis tilt, shank = thigh − knee, foot = shank + ankle. "
                      "Pelvis, hip, knee and ankle are published by the source; thigh, shank and foot are worked out from them. "
                      "So a wrong pelvis or hip gives a wrong thigh and shank, and a wrong knee gives a wrong shank only. A wrong thigh never changes the hip or knee."),
        "knock_on": [
            ko("Knee angle (your example)", OK,
               "A bad thigh does not change the knee angle. The knee is published by the source, not worked out from the thigh. The dependence runs the other way: the shank is thigh − knee.",
               f"Shank = thigh − knee holds to rounding in all {n(full)} released strides, so the knee is an input, not an output; the published knee sign matched markers in 16 of 16 legs.",
               "probe identity; UM21-C03 per_channel_best_transform"),
            ko("Hip angle", OK, "Not affected: it is published by the source. The old build misused it by adding the pelvis instead of subtracting it.",
               "Hip minus pelvis follows the thigh from markers in 10 of 10 legs in the first check and in 10 of 10 legs in an independent repeat on other recordings.", "UM21-C01, UM21-C01-verify"),
            ko("Shank angle", FIXED, "Rebuilt from the corrected thigh and the knee.",
               f"Shank = thigh − knee to rounding in all {n(full)} released strides.", "probe identity"),
            ko("Thigh and shank speeds", OK, "They are the slope of the rebuilt angles, so they follow the fix.",
               f"Stored speed matches the slope of the released angle in all {n(full)} strides (lowest agreement {min(min(v['speed_vs_angle_slope_corr_min']['thigh'], v['speed_vs_angle_slope_corr_min']['shank']) for v in pr.values()):.2f}).",
               "probe speed_vs_angle"),
            ko("Foot angle (shank + ankle)", LEFT, "Would also have been wrong; not released.", "Foot angle carries the unchecked ankle zero point.", "UM21-R01 columns_not_released"),
            ko("Hip, knee and ankle moments and powers", OK, "Not affected: the source calculates them itself; our thigh and shank are not an input.",
               "Moment and power columns are copied from the source (power after a sign step), not rebuilt from our segment angles.", "UM21-R01 columns"),
            ko("Thigh and shank on the other leg", LEFT, "The earlier tables carried the other leg too; each stride now carries its own leg only.",
               "Earlier opposite-leg columns pre-date the sign step and are not trusted.", "UM21-R01 open_items_resolved"),
            ko("How far side-view thigh and shank are from the true 3D angles", NC, "They are side-view estimates; the difference to 3D angles is not checked."),
        ],
    })

    # ---------------------------------------------------------------- 5 ankle 180
    ab = "AB07/i10"
    t = probe["ab07_i10_right_ankle"]
    turned, others = t["turned_back_strides"]["n"], t["other_strides_same_side"]["n"]
    dropped = recs[ab]["dropped_c03_2"]
    right_total = turned + others + dropped
    affected = turned + dropped
    census_stretch = 31
    never = census_stretch - affected
    alts = [(x["recording"], x["side"], x["alternate_frames"]) for x in c03["all_channels"] if x["channel"] == "Ankle" and x["alternate_frames"] > 0]
    big = max(alts, key=lambda a: a[2])
    small = [a for a in alts if a != big]
    out["fixes"].append({
        "key": "ankle_180", "card": "Part of one ankle recording was turned 180°",
        "total_line": (f"AB07, 10° incline, right ankle only: {affected} of {n(total_strides)} strides ({pct(affected, total_strides, 2)}%), {n(affected * SAMPLES)} of {n(total_samples)} samples; "
                       f"that is {affected} of the {right_total} right-leg strides of that recording ({pct(affected, right_total)}%) and {affected} of its {per_rec_total[ab]} strides ({pct(affected, per_rec_total[ab])}%). "
                       f"{turned} were turned back ({n(turned * SAMPLES)} samples logged), {dropped} were left out."),
        "total_numbers": {"recordings_affected": 1, "recordings_total": len(recs), "strides_affected": affected, "strides_total": total_strides,
                          "strides_pct": pct(affected, total_strides, 2), "samples_affected": affected * SAMPLES, "samples_total": total_samples,
                          "turned_back": turned, "left_out": dropped, "never_converted": never, "stretch_strides": census_stretch,
                          "right_leg_strides_in_recording": right_total, "recording_strides": per_rec_total[ab]},
        "denominator_text": "Strides are counted in the converted set of 7,562. The source stretch holds 31 strides, but 9 of them were never converted and are not counted.",
        "table": {"columns": ["Participant and task", "Turned back", "Left out (one-sample jumps)", "Never converted", "Of right-leg strides", "Samples turned back"],
                  "rows": [[name(ab) + ", right ankle", str(turned), str(dropped), str(never), f"{affected} of {right_total} ({pct(affected, right_total)}%)", n(turned * SAMPLES)]], "fold": False},
        "grid": grid({k: (pct(affected, per_rec_total[ab]) if k == ab else 0.0) for k in all50 if k in recs}),
        "grid_caption": "Share of each recording's strides (both legs) turned back or left out for this fix.",
        "direction": "Only the right ankle angle was in the other form. Thigh and shank do not use the ankle (shank = thigh − knee), so the dependence would only reach the foot angle (shank + ankle), which is not released.",
        "knock_on": [
            ko("Ankle speed", LEFT, "The turn would have broken it, but ankle speed is not a released column.", "The released speeds are pelvis, thigh and shank only.", "UM21-R01 columns"),
            ko("Ankle power in the turned-back strides", OK, "It is consistent with the turned-back angle.",
               f"Power follows moment times speed (worked out from the turned-back angle) with agreement {t['turned_back_strides']['power_vs_moment_times_speed_corr_median']:.3f} (lowest {t['turned_back_strides']['corr_min']:.3f}) against {t['other_strides_same_side']['power_vs_moment_times_speed_corr_median']:.3f} (lowest {t['other_strides_same_side']['corr_min']:.3f}) in the other right-leg strides. Their power range is smaller ({t['turned_back_strides']['power_range_mean']:.1f} against {t['other_strides_same_side']['power_range_mean']:.1f} W/kg); why was not checked.",
               "probe ab07_i10_right_ankle"),
            ko("Ankle moment in the turned-back strides", OK, "Not affected.",
               f"Moment range {t['turned_back_strides']['moment_range_mean']:.2f} against {t['other_strides_same_side']['moment_range_mean']:.2f} N·m/kg in the other right-leg strides; no jumps.", "probe ab07_i10_right_ankle"),
            ko("Hip and knee angles in the same stretch", OK, "Not affected: the 180° form appears only in the ankle.",
               f"The 180° form was found in no hip or knee channel; the largest sample-to-sample step in the released right-leg strides is {t['turned_back_strides']['max_step_deg_per_sample_largest']['knee']:.1f}° (knee) against {t['other_strides_same_side']['max_step_deg_per_sample_largest']['knee']:.1f}° elsewhere.",
               "UM21-C03 episode census; probe"),
            ko("Sudden knee jumps seen at the edges of the stretch", NC, "The source scan saw knee jumps over 90° in 3 strides at these edges; whether they are the 2 strides left out or the 9 never converted was not matched."),
            ko("Thigh and shank angles", OK, "Not affected: they do not use the ankle.",
               f"Shank = thigh − knee holds to rounding in all {n(full)} released strides.", "probe identity"),
            ko("Foot angle (shank + ankle)", LEFT, "Would be 180° off here; not released.", "Foot angle carries the unchecked ankle zero point.", "UM21-R01 columns_not_released"),
            ko("The same problem in other recordings", OK, "It happens once.",
               f"All 500 joint-angle channels were scanned: only {big[0]} {('right' if big[1] == 'R' else 'left')} ankle has a long stretch ({n(big[2])} frames).", "UM21-C03 episode census"),
            ko("Two short ankle glitches elsewhere", NC,
               "Left as published, in " + " and ".join(f"{name(a[0])} {('right' if a[1] == 'R' else 'left')} ankle ({a[2]} frames)" for a in small) + "; whether they fall inside released strides was not checked here."),
        ],
    })

    # ---------------------------------------------------------------- 6 power
    rule = {}
    for line in q01["t04_v2_power_summary"]["per_record"]:
        rec, rest = line.split(": ", 1)
        for m in re.finditer(r"(ankle|hip|knee) (hook|physics|copied|HELD) r=([+-]\d\.\d\d)/([+-]\d\.\d\d)", rest):
            rule[(rec, m.group(1))] = (m.group(2), float(m.group(3)), float(m.group(4)))
    assert len(rule) == 132
    counts = {}
    for v in rule.values():
        counts[v[0]] = counts.get(v[0], 0) + 1
    assert counts == {"hook": 24, "physics": 96, "copied": 4, "HELD": 8}, counts
    pairs_total = sum(recs[r]["full"] for r, _ in rule)
    by_rule_pairs = {}
    for (r, j), v in rule.items():
        by_rule_pairs[v[0]] = by_rule_pairs.get(v[0], 0) + recs[r]["full"]
    layout2 = sorted({r for (r, j), v in rule.items() if j == "ankle" and v[1] > 0} | {r for r in ("AB03/i10",)})
    flipped = sum(1 for v in rule.values() if v[0] != "HELD" and v[1] < 0)
    kept = sum(1 for v in rule.values() if v[0] != "HELD" and v[1] > 0)
    jn = {"hip": "hip power", "knee": "knee power", "ankle": "ankle power"}
    rows = []
    cell = {}
    for (r, j), v in sorted(rule.items(), key=lambda kv: (kv[0][0].split("/")[0], COND_ORDER.index(kv[0][0].split("/")[1]), kv[0][1])):
        if v[0] in ("HELD", "copied"):
            rows.append([name(r), jn[j], "Left empty" if v[0] == "HELD" else "Sign copied from the other leg",
                         f"{v[1]:+.2f} / {v[2]:+.2f}", f"{recs[r]['full']} of {per_rec_total[r]}"])
            cell[r] = cell.get(r, 0) + 1
    assert len(rows) == 12
    held_pairs, copied_pairs, phys_pairs = by_rule_pairs["HELD"], by_rule_pairs["copied"], by_rule_pairs["physics"]
    # held_signals.csv must agree with the handoff
    assert {(h["recording"], h["column"].split("_")[0]) for h in held} == {(r, j) for (r, j), v in rule.items() if v[0] == "HELD"}
    cells = {k: round(100.0 * cell.get(k, 0) / 3, 1) for k in all50 if k in recs}
    pw_total = pairs_total
    out["fixes"].append({
        "key": "power", "card": "Power sign was unsettled",
        "total_line": (f"12 of 132 power channels (9.1%; 44 recordings × hip, knee, ankle) were not set by a clear rule: 8 left empty and 4 copied. "
                       f"In stride terms: {n(held_pairs)} of {n(pw_total)} stride-joint values left empty ({pct(held_pairs, pw_total)}%, {n(held_pairs * SAMPLES)} samples) and "
                       f"{n(copied_pairs)} copied ({pct(copied_pairs, pw_total)}%). {n(phys_pairs)} stride-joint values ({pct(phys_pairs, pw_total)}%, {n(phys_pairs * SAMPLES)} samples, 96 channels) use a sign set by the moment-times-speed check."),
        "total_numbers": {"channels_total": 132, "channels_copied": 4, "channels_held": 8, "channels_physics": 96, "channels_source_layout_rule": 24,
                          "channels_sign_flipped": flipped, "channels_sign_kept": kept,
                          "stride_joint_values_total": pw_total, "stride_joint_values_held": held_pairs, "stride_joint_values_copied": copied_pairs,
                          "stride_joint_values_physics": phys_pairs, "samples_held": held_pairs * SAMPLES, "samples_physics": phys_pairs * SAMPLES,
                          "recordings_with_second_storage": len(layout2)},
        "denominator_text": f"A stride-joint value is one stride's hip, knee or ankle power ({n(full)} released strides × 3 joints = {n(pw_total)}). Of the 124 channels with a sign set, {flipped} were multiplied by −1 and {kept} kept as published. Power is stored in two ways; the {len(layout2)} recordings stored the second way keep their sign: {'; '.join(name(r) for r in layout2)}.",
        "table": {"columns": ["Participant and task", "Joint", "What happened", "Agreement, left / right leg", "Strides (of the recording)"], "rows": rows, "fold": True},
        "grid": grid(cells),
        "grid_caption": "Share of each recording's three power channels (hip, knee, ankle) that are empty or copied.",
        "direction": "Power relates to the joint moment times the joint speed. We use the published moment and the speed from the published angle to set the power sign; the moment and angle are inputs, the power is the output. Nothing else is computed from power.",
        "knock_on": [
            ko("Hip, knee and ankle moments", OK, "Not changed by the power sign. They are the reference the power sign is checked against.",
               "Their own sign matched force plates in 16 of 16 legs for knee and ankle and 14 of 16 for hip.", "UM21-C03 per_channel_best_transform"),
            ko("Joint angles and angle speeds", OK, "Not changed by the power sign.", f"Stored speeds match the slope of the released angles in all {n(full)} strides.", "probe speed_vs_angle"),
            ko("Hip power in 6 recordings, plus knee and ankle power in AB03 10° incline", LEFT, "Left empty (present but missing) because the check stayed below 0.9 on at least one leg.",
               f"{n(held_pairs)} stride-joint values; agreement below 0.9 on at least one leg.", "UM21-Q01 t04_v2_power_summary"),
            ko("The moment or speed in those held recordings", NC,
               "Low agreement could come from the power, the moment or the joint speed. Which one is off was not checked, and moments and speeds have no range check."),
            ko("Joint work or energy computed from power by a user", NC, "Not computed or checked here."),
        ],
    })

    # ---------------------------------------------------------------- consistency
    for f in out["fixes"]:
        for k in f["knock_on"]:
            assert k["verdict"] in VERDICTS and (k["verdict"] == NC or k["evidence"])
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
