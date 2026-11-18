#!/usr/bin/env python3
"""Build the Georgia Tech 2023 "known problems" page, its scope file and its figures.

Georgia Tech 2023 has not been reconverted or released. Every number here describes the SOURCE
dataset and the committed audit results, measured against the source (denominators are stated on
each card). Nothing on the page claims that a fix was applied to data.

Stages (all run by default, in this order):
  scope    reads the committed audit files (docs/quality/audits/gt23-*.json), the backlog decisions,
           and one read-only listing of the source folders (file names and sizes only, no recording
           is opened); writes docs/quality/audits/gt23-problem-scope.json
  figures  draws docs/datasets/gt23/figures/*.svg from the scope file (matplotlib, 4.5 in wide,
           fonts of at least 10 pt)
  page     writes docs/datasets/gt23/problems.html from the scope file only, and copies the page and
           its figures to site/html/datasets/gt23/

The source listing is a read-only probe: run it alone, serialized with other workers:
  flock /tmp/locohub-probe.lock nice -n 19 ionice -c 3 /usr/bin/time -v python3 \
      contributor_tools/build_gt23_problems_page.py scope

Usage: python3 contributor_tools/build_gt23_problems_page.py [scope|figures|page|all]
"""
from __future__ import annotations

import html
import io
import json
import os
import random
import re
import resource
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDITS = ROOT / "docs/quality/audits"
BACKLOG = ROOT / "docs/maintainers/backlog.json"
SOURCE = Path("/mnt/s/locomotion_data/Gtech_2023")
SCOPE = AUDITS / "gt23-problem-scope.json"
OUT_DIR = ROOT / "docs/datasets/gt23"
FIGS = OUT_DIR / "figures"
OUT = OUT_DIR / "problems.html"
SITE_DIR = ROOT / "site/html/datasets/gt23"
FIXFIGS = ROOT / "docs/quality/fixes"
SEED = 20261118

INK, MUTED, GREY = "#20252b", "#5b6672", "#b4bcc4"
BEFORE, AFTER = "#c4501a", "#1f6aa5"
WIDTH_IN = 4.5

V_WRONG, V_OK, V_LEFT, V_NC = "Also wrong, not fixed", "Checked, not affected", "Left out", "Not checked"
VERDICTS = [V_WRONG, V_OK, V_LEFT, V_NC]
STATUS = {
    "fixed": "Fixed in a checked pilot",
    "decided": "Decided, fix not yet run",
    "open_run": "Open, fix not yet run",
    "open_decide": "Open, needs a decision",
    "documented": "Documented only, kept as published",
}

# Task groups used as the columns of every grid (26 tasks in all).
GROUPS = [
    ("level", "Normal walk, run, skip", ["normal_walk"]),
    ("variants", "Treadmill variants", ["dynamic_walk", "incline_walk", "obstacle_walk", "weighted_walk"]),
    ("backward", "Backward, shuffle", ["walk_backward", "side_shuffle"]),
    ("turn", "Turn, cut, meander", ["cutting", "meander", "turn_and_step"]),
    ("run", "Tire run", ["tire_run"]),
    ("steps", "Stairs, curbs, steps", ["stairs", "curb_down", "curb_up", "step_ups", "start_stop"]),
    ("inplace", "In-place, lifting", ["ball_toss", "jump", "lift_weight", "lunges", "poses", "push", "sit_to_stand",
                                      "squats", "tug_of_war", "twister"]),
]
GROUP_OF = {a: g for g, _, acts in GROUPS for a in acts}
FORWARD_11 = {"curb_down", "curb_up", "dynamic_walk", "incline_walk", "normal_walk", "obstacle_walk", "stairs",
              "start_stop", "step_ups", "tire_run", "weighted_walk"}
RUN_SUFFIX, SKIP_SUFFIX = {"2-0", "2-5"}, {"skip"}
SUBJECTS: list[str] = []


def load(name: str):
    return json.loads((AUDITS / name).read_text(encoding="utf-8"))


def pct(a, n):
    return f"{100 * a / n:.1f}%"


# ======================================================================================================
# scope
# ======================================================================================================
def probe_listing(subjects):
    """Names and sizes only. Maps each event file to its recording; opens no recording."""
    rec_names = {s: sorted(os.listdir(SOURCE / "RawData" / s / "CSV_Data")) for s in subjects}
    out = {s: {r: {"files": 0, "empty": 0, "suffixes": []} for r in rec_names[s]} for s in subjects}
    unmapped, total = [], 0
    for s in subjects:
        for f in sorted(os.scandir(SOURCE / "Segmentation" / s), key=lambda e: e.name):
            if not f.name.endswith("_parsing.mat"):
                continue
            total += 1
            stem = f.name[: -len("_parsing.mat")]
            owner = [r for r in rec_names[s] if stem == r or stem.startswith(r + "_")]
            if not owner:
                unmapped.append(f"{s}/{f.name}")
                continue
            r = max(owner, key=len)
            e = out[s][r]
            e["files"] += 1
            e["suffixes"].append(stem[len(r) + 1:])
            if f.stat().st_size <= 221:
                e["empty"] += 1
    return out, total, unmapped


def cells_from(rec, pred):
    """pred(r) -> 'a' affected, 'u' could not be told, anything else not affected."""
    cells = {}
    for s in SUBJECTS:
        for g, _, _ in GROUPS:
            rs = [r for r in rec if r["subject"] == s and r["group"] == g]
            cells[f"{s}/{g}"] = [sum(pred(r) == "a" for r in rs), len(rs), sum(pred(r) == "u" for r in rs)]
    return cells


def sums(cells):
    return (sum(v[0] for v in cells.values()), sum(v[1] for v in cells.values()), sum(v[2] for v in cells.values()))


def participant_table(cells, unit, first="Participant"):
    rows = []
    for s in SUBJECTS:
        a = n = u = 0
        for g, _, _ in GROUPS:
            v = cells[f"{s}/{g}"]
            a, n, u = a + v[0], n + v[1], u + v[2]
        rows.append([s, f"{n:,}", f"{a:,} ({pct(a, n)})" if n else "none", f"{u:,}"])
    return {"columns": [first, f"{unit.capitalize()} in the source", "Affected", "Could not be told"], "rows": rows, "fold": True}


def task_table(rec, pred, label="Task"):
    acts = sorted({r["family"] for r in rec})
    rows = []
    for a in acts:
        rs = [r for r in rec if r["family"] == a]
        k = sum(pred(r) == "a" for r in rs)
        if k:
            rows.append([a.replace("_", " "), f"{k:,}", f"{len(rs):,}"])
    return {"columns": [label, "Recordings affected", "Recordings of this task"], "rows": rows, "fold": len(rows) > 8}


def K(signal, verdict, line, evidence=""):
    assert verdict in VERDICTS
    return {"signal": signal, "verdict": verdict, "line": line, "evidence": evidence}


def build_scope():
    t0 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    global SUBJECTS
    c01, c03 = load("gt23-c01-events-and-frames.json"), load("gt23-c03-normalizing-mass.json")
    c05, scopefile = load("gt23-c05-rescale-error.json"), load("gt23-full-source-scope.json")
    units_rev, oversized = load("gt23-publisher-units-and-mass-review.json"), load("gt23-oversized-transform-container-review.json")
    pilot, sign_ev = load("core04-gt23-pilot.json"), load("gt23-joint-sign-and-segment-evidence.json")
    backlog = json.loads(BACKLOG.read_text(encoding="utf-8"))
    dec = {d["id"]: d for d in backlog["decisions"]}
    for k in ("D-GT23-C01-1", "D-GT23-C05-1"):
        assert dec[k]["status"] == "answered", k
    SUBJECTS = sorted({t["subject"] for t in c05["trials"]})
    probe, n_files, unmapped = probe_listing(SUBJECTS)
    assert not unmapped, unmapped
    totals = c01["totals"]
    assert n_files == totals["parsing_files"] == 787

    # one entry per source recording
    rec = []
    for t in c05["trials"]:
        p = probe[t["subject"]][t["task"]]
        rec.append({"subject": t["subject"], "task": t["task"], "family": t["family"], "group": GROUP_OF[t["family"]],
                    "cls": t["class"], "files": p["files"], "empty": p["empty"],
                    "suffixes": p["suffixes"], "events": p["files"] - p["empty"] > 0})
    N = len(rec)
    assert N == 488 == totals["recordings"]
    assert sum(r["empty"] for r in rec) == totals["empty_parsing_files"] == 9
    n_events = sum(r["events"] for r in rec)
    n_noevents = N - n_events
    assert n_noevents == totals["recordings_without_source_intervals"] == 90, n_noevents
    act = {a["activity"]: a for a in c01["activities"]}
    assert set(act) == set(GROUP_OF) and len(act) == 26
    rng = random.Random(SEED)
    examples = {}
    cards = []

    def add(**card):
        card.setdefault("direction", "")
        card.setdefault("how", "")
        cards.append(card)

    # ---------------- A. mass and units ----------------
    subs = c03["subjects"]
    level_wrong = [s for s in SUBJECTS if not subs[s]["readme_consistent"]]
    exact_other = [s for s in level_wrong if subs[s]["divisor_basis"].startswith("local N")]
    assert len(level_wrong) == 9 and len(exact_other) == 7
    factors = [subs[s]["scale_factor_published_vs_readme_normalized"] for s in level_wrong]
    by = c05["summary"]["by_class"]
    a_conf, a_prob, a_own = by["lower_confident"], by["lower_if_recorded_mass"], by["own_mass_only"]
    a_unk = N - a_conf - a_prob - a_own
    cells = cells_from(rec, lambda r: "a" if r["cls"] == "lower_confident" else ("u" if r["cls"] != "own_mass_only" else "n"))
    a, n, u = sums(cells)
    assert a == a_conf and n == N
    pool = [(r, t) for r, t in zip(rec, c05["trials"]) if r["cls"] == "lower_confident" and t["tier"] == "validated_gait"]
    ex, et = rng.choice(pool)
    examples["mass"] = f"{ex['subject']} {ex['task']}"
    mrows = []
    for s in SUBJECTS:
        x = subs[s]
        exact = x["divisor_basis"].startswith("local N")
        if x["readme_consistent"]:
            used = "own mass" + (" (cannot be told apart from another mass)" if not exact else "")
            how_found = "worked out exactly" if exact else "estimated from force plates"
        else:
            owner = [nm.replace("README ", "") for nm, m in x["nearest_candidate_masses"] if nm.startswith("README") and abs(m - x["divisor_kg_best"]) < 0.2]
            used = f"{x['divisor_kg_best']:.1f}" + (f" ({owner[0]}'s mass)" if owner else "") if exact else f"about {x['divisor_kg_best']:.0f}"
            how_found = "worked out exactly" if exact else "estimated from force plates"
        mrows.append([s, f"{x['readme_mass_kg']}", used, how_found, f"{x['scale_factor_published_vs_readme_normalized']:.2f}"])
    add(key="mass", section="Mass and units", status="documented",
        title="Per-kg moments and powers were divided by another participant's body mass",
        short=f"{a_conf} of {N} recordings shown; {a_unk + a_prob} cannot be told or only probably",
        wrong=f"For {len(level_wrong)} of {len(SUBJECTS)} participants, the authors did not use the person's own body mass to turn moments and powers into per-kg values in level walking. For {len(exact_other)} of them the mass used is exactly another participant's listed body mass, and it can change between recordings of the same person.",
        how="The source gives some recordings in newton-metres as well as per kg. Dividing one by the other gives the mass that was used. Where that was not possible, the mass was estimated from force-plate moments.",
        where=f"Decided by José on 2 November 2026: release every moment and power exactly as published, with no rescaling, and document the mismatch. Nothing has been rescaled or left out. The reason: correcting to the person's own mass clearly lowered the error in only {a_conf} of the {N} recordings.",
        example=f"{ex['subject']}, {ex['task'].replace('_', ' ')}: the person's own mass is {et['own_mass_kg']} kg, but force-plate moments point to about {et['lever_kg']:.0f} kg being used. Published error against the person's own mass is {et['policy_T']['original_error_pct'][0]:.0f} to {et['policy_T']['original_error_pct'][1]:.0f}%. This recording was drawn at random from the {len(pool)} shown recordings with a validated walking estimate.",
        figures=[{"src": "reuse-gt23-mass.svg", "question": "Which mass was used for each participant in level walking?", "alt": "For each of 12 participants, the mass used compared with the person's own mass in level walking; 9 participants have another mass used.", "caption": "Level walking, one row per participant (the same figure as on the fixes page)."}],
        total_line=f"{a_conf} of {N} recordings ({pct(a_conf, N)}) are shown to carry another mass; {a_prob} more ({pct(a_prob, N)}) probably do; {a_own} are confirmed to use the person's own mass; {a_unk} cannot be told. In level walking, {len(level_wrong)} of {len(SUBJECTS)} participants are affected.",
        denominator_text=f"Recordings are the source's {N} recordings from {len(SUBJECTS)} participants. In level walking the affected per-kg values are {min(factors):.2f} to {max(factors):.2f} times the value for the person's own mass. Sample counts were not part of these checks.",
        totals={"units": "recordings", "affected": a_conf, "total": N, "probable": a_prob, "own_confirmed": a_own, "cannot_tell": a_unk, "participants_affected": len(level_wrong), "participants": len(SUBJECTS)},
        grid={"cells": cells, "unit": "recordings", "caption": "Recordings shown to carry another mass. Hatched cells: none shown, but the mass could not be told for most recordings there, so they are not cleared."},
        table={"columns": ["Participant", "Own mass (kg)", "Mass used in level walking (kg)", "How it was found", "Published per-kg value relative to the own-mass value"], "rows": mrows, "fold": True},
        knock_on=[
            K("Hip, knee and ankle moments (per kg)", V_WRONG, f"In the {a_conf} shown recordings they are off by the factors above; kept as published.", "In 8 level-walking recordings, moments recomputed in newton-metres match the published per-kg moments times one constant (correlation 1.0); the constant is another participant's mass in 7 of them."),
            K("Hip, knee and ankle powers (per kg)", V_WRONG, "Power carries the same mass, so it is off by the same factor in the same recordings.", "Published power equals the filtered moment times joint speed (ratio 1.0000, correlation 1.0000 in 12 columns checked by a second person)."),
            K("Joint angles and angle speeds", V_OK, "Mass divides only the moments, so angles do not change with it.", "Moments recomputed without any mass differ from the published ones only by one constant per recording, so the mass enters through that one number."),
            K("Ground forces and pressure point", V_OK, "They are not divided by this mass.", "Body masses from the force plates match the listed masses within 1% in all 12 participants."),
            K("Moments and powers in the other recordings", V_NC, f"{a_unk + a_prob} recordings are not shown to carry another mass: non-walking tasks, curbs, stairs and short recordings have no checked way to find the mass used, and {a_prob} others only probably carry another mass. They are neither confirmed nor cleared."),
        ],
        direction="A wrong mass changes per-kg moments and powers. It does not change angles, forces or the pressure point.")

    add(key="units", section="Mass and units", status="documented",
        title="The README says moments are in N·m and powers in W, but the data are per kg",
        short=f"All {N} recordings; the check covered 5 participants",
        wrong="The publisher's README lists joint moments in N·m and powers in W. The published values were already divided by body mass, so they are in N·m per kg and W per kg.",
        how="A moment rebuilt from the force plates in N·m is 64 to 90 times larger than the published ankle moment, which is a body mass. Joint power equals the published moment times joint speed (ratio 0.96 to 1.00).",
        where="Documented. LocoHub's converters copy the values and label them per kg, and do not divide by mass a second time, so the labels are already right. Nothing was changed in the data.",
        example="AB01, incline walking 2, left leg: read as N·m, the published ankle moment is 1/64 to 1/90 of the force-plate moment, in all 8 sampled legs (98 to 99% too small).",
        figures=[{"src": "reuse-gt23-units-before.svg", "question": "What if we trust the README and read the values as N·m?", "alt": "One stance of ankle moment: read as N·m, the published curve is far smaller than the force-plate moment.", "caption": "Before: read as the README says."},
                 {"src": "reuse-gt23-units-after.svg", "question": "Do the values match once we read them as per kg?", "alt": "The same stance read as per-kg values, matching the force-plate moment divided by a body mass.", "caption": "After: read as LocoHub does."}],
        total_line=f"All {N} recordings (100%) carry the README's wrong unit text. The check measured 5 participants (25 channel files, 8 legs) and found the same result in all.",
        denominator_text="The README applies to every recording. The units check itself sampled 5 of 12 participants; the other 7 are covered by the README text only. Sample counts do not apply.",
        totals={"units": "recordings", "affected": N, "total": N, "participants_checked": 5, "participants": len(SUBJECTS)},
        grid={"cells": cells_from(rec, lambda r: "a"), "unit": "recordings", "caption": "Every recording is covered by the wrong README text (all of them)."},
        table=participant_table(cells_from(rec, lambda r: "a"), "recordings"),
        knock_on=[
            K("Moments (per kg)", V_OK, "LocoHub labels them N·m per kg and does not divide again.", "Both current converters copy the values as per kg."),
            K("Powers (per kg)", V_OK, "Labelled W per kg for the same reason.", "Power equals moment times joint speed, ratio 0.96 to 1.00 in the checked legs."),
            K("Ground forces", V_OK, "The unit text does not touch forces.", "Force-plate body mass matches the README mass in 5 of 5 checked participants."),
            K("The authors' filtered and processed moment and power files", V_NC, "Only 3 recordings were compared with the raw moments and they match; the filtered and power files were not compared."),
        ],
        direction="Wrong unit text would make every moment and power 64 to 90 times too small for anyone who trusts it. Angles and forces are not in these units.")

    ab03_tbl = units_rev["participant_masses"]["comparison"]
    rel = {x["subject"]: abs(float(x["local_model_derived_mass_kg"]) / float(x["publisher_mass_kg"]) - 1) for x in ab03_tbl}
    assert rel["AB03"] > 0.25 and max(v for k, v in rel.items() if k != "AB03") < 0.001
    cells = cells_from(rec, lambda r: "a" if r["subject"] == "AB03" else "n")
    a, n, u = sums(cells)
    add(key="ab03mass", section="Mass and units", status="open_run",
        title="Forces in body weights use the wrong mass for AB03",
        short=f"AB03: {a} of {N} recordings",
        wrong="Both converters take the body mass for body-weight forces from a local table that was rewritten from the body models. For AB03 it says 82.18 kg, but the publisher's table and the force plates say about 113.5 kg. The other participants in the table differ by rounding only (below 0.1%).",
        how="The publisher's mass table and the local table were compared. In the force-plate check, AB03's body mass came out near 114 kg, not 82.",
        where="Open. The supported correction is to use the publisher's table. No data have been converted with it yet.",
        example=f"AB03 forces divided by 82.18 kg instead of 113.5 kg come out {113.5 / 82.18:.2f} times too large in body weights.",
        figures=[],
        total_line=f"{a} of {N} recordings ({pct(a, N)}) from 1 of {len(SUBJECTS)} participants: every AB03 recording would get forces in body weights that are {100 * (113.5 / 82.18 - 1):.0f}% too large.",
        denominator_text=f"Recordings in the source ({N}). Sample counts do not apply: this is a conversion setting, and no AB03 recording was converted with the corrected table.",
        totals={"units": "recordings", "affected": a, "total": N, "participants_affected": 1, "participants": len(SUBJECTS)},
        grid={"cells": cells, "unit": "recordings", "caption": "Recordings whose body-weight forces would use the wrong mass (all of AB03)."},
        table=participant_table(cells, "recordings"),
        knock_on=[
            K("Forces in body weights (up, forward, sideways)", V_WRONG, "AB03's values would be 38% too large. Force in body weights goes down as the mass used goes up.", "Publisher mass table versus the local table, compared participant by participant."),
            K("Moments and powers", V_OK, "The converters read the mass table only for forces; they copy moments as published.", "Converter code was read, not run."),
            K("Pressure point and joint angles", V_OK, "Neither uses a body mass.", "The pressure point calculation uses only positions and the foot frame (code read, not run)."),
            K("The other participants", V_OK, "Rounding only.", "The largest difference between the two tables is below 0.1%."),
        ],
        direction="Mass enters forces in body weights and per-kg moments and powers. Angles and the pressure point do not use it.")

    # ---------------- B. forces and pressure point ----------------
    cells = cells_from(rec, lambda r: "a" if r["events"] else "n")
    a, n, u = sums(cells)
    add(key="forceframe", section="Forces and pressure point", status="open_run",
        title="Horizontal ground force is labelled forward and sideways, but is in lab axes",
        short=f"{a} of {N} recordings that the converters export",
        wrong="The converters write the force plates' horizontal force in lab directions straight into the forward and sideways columns. Lab directions turn with the person, so they are not forward and sideways unless the person walks along one lab axis.",
        how="The paper says the forces are in the lab frame. The converter code copies them without turning them by the person's facing direction.",
        where="Open. A correction tool exists that sets the four forward and sideways force columns to empty and keeps the original values under lab-axis names. It has been tested only on made-up data, not on real data, and has not been run.",
        example="Walking in a straight line can keep one lab axis nearly fixed, so the error can hide there; a turn or a side shuffle shows it at once.",
        figures=[],
        total_line=f"{a} of {N} recordings ({pct(a, N)}) have event windows and would be exported with the wrong labels; the other {N - a} are never exported by either converter.",
        denominator_text=f"Recordings in the source ({N}). Samples were not counted: nothing was converted for this review.",
        totals={"units": "recordings", "affected": a, "total": N, "never_exported": N - a},
        grid={"cells": cells, "unit": "recordings", "caption": "Recordings the converters would export with the wrongly labelled horizontal force."},
        table=participant_table(cells, "recordings"),
        knock_on=[
            K("Forward and sideways force, both legs", V_WRONG, "Lab-axis values are labelled forward and sideways.", "Paper's frame description and the converter code, both read."),
            K("Up-down force", V_OK, "Up is a lab axis and positive means support.", "Force-plate body mass matches the README mass in 5 of 5 checked participants."),
            K("Pressure point", V_OK, "It comes from a different calculation, in the foot's own frame. It has its own card.", "Converter code read, not run."),
            K("Published moments and powers", V_OK, "The authors computed them in the lab frame, so the labelling does not change them.", "A moment rebuilt from the plates in the lab frame matches the published ankle moment (correlation 0.9975 to 0.9998)."),
            K("Forward force after turning it by the facing direction", V_NC, "Braking and push-off looked right in level, incline and decline walking for 3 participants. Stairs and all other tasks were not checked, and nothing has been run on real converted data."),
        ],
        direction="A wrong force direction changes the forward and sideways force and anything computed from it, such as braking and push-off. It does not change up-down force, angles, or the moments the authors published.")

    f15 = [r for r in rec if r["family"] not in FORWARD_11]
    cells = cells_from(rec, lambda r: "a" if r["family"] not in FORWARD_11 else "n")
    a, n, u = sums(cells)
    acts15 = sorted(set(r["family"] for r in f15))
    assert len(acts15) == 15
    ex15 = rng.choice(acts15)
    examples["forward"] = ex15
    add(key="forward", section="Forces and pressure point", status="decided",
        title="Some tasks have no single forward direction",
        short=f"15 of 26 tasks; {a} of {N} recordings",
        wrong="Our rule says forward means the walking direction. In 15 of the 26 tasks the person does not walk forward in one direction: backward walking, side shuffle, squats, sit-to-stand, lifting, jumps, lunges, turns, cutting and meandering.",
        how="The authors' task descriptions were read, and the heading of the pelvis during each window was reviewed; only the 11 forward-walking tasks have a steady heading that matches the direction of travel.",
        where="Decided: José asked us to choose, and we took the smallest change. Forward and sideways force and pressure point are filled only for the 11 forward-walking tasks, from the measured facing direction. The other 15 tasks keep lab-axis values only. Not yet run.",
        example=f"One of the 15, drawn at random: {ex15.replace('_', ' ')}. Its horizontal force stays in lab axes.",
        figures=[],
        total_line=f"15 of 26 tasks ({pct(15, 26)}) and {a} of {N} recordings ({pct(a, N)}) keep lab-axis horizontal force and pressure point only.",
        denominator_text=f"Tasks are the publisher's 26 base tasks; recordings are the source's {N}. Samples were not counted.",
        totals={"units": "recordings", "affected": a, "total": N, "tasks_affected": 15, "tasks": 26},
        grid={"cells": cells, "unit": "recordings", "caption": "Recordings in the 15 tasks with no single forward direction."},
        table=task_table(rec, lambda r: "a" if r["family"] not in FORWARD_11 else "n"),
        knock_on=[
            K("Forward and sideways force in the 15 tasks", V_LEFT, "Not filled; the lab-axis values are kept under lab-axis names.", "The decision, recorded with the options that were weighed."),
            K("Forward and sideways pressure point in the 15 tasks", V_LEFT, "Not filled for the same reason.", "The decision, as above."),
            K("Up-down force and joint angles", V_OK, "Neither needs a forward direction.", "Up-down force is a lab axis; joint angles are joint coordinates, not force data."),
            K("Forward walking: stairs and curbs", V_NC, "The checks of braking, push-off and pressure-point progression gave no answer on stairs, so the facing direction there is not confirmed."),
            K("Forward walking: everything beyond level, incline and decline", V_NC, "Facing direction was measured and checked only in 3 participants on level, incline and decline walking."),
        ],
        direction="This decision changes only the forward and sideways force and pressure point. Up-down force and angles are not touched.")

    cells = cells_from(rec, lambda r: "a" if r["events"] else "n")
    a, n, u = sums(cells)
    add(key="cop", section="Forces and pressure point", status="open_decide",
        title="The pressure point is in the foot's own frame, not the ground frame",
        short=f"{a} of {N} recordings that the converters export",
        wrong="The converters give the centre of pressure (where the force acts on the foot) in a frame attached to the heel bone, which turns with the foot. LocoHub's data reference defines it in the ground frame. The origin is the heel-bone frame origin, not the ankle as a code comment says.",
        how="The calculation was read: the pressure point in the lab is turned into the foot frame using the foot's position and orientation, with no ankle offset.",
        where="Open, needs a decision. The review proposes labelling these values as foot-frame, with correct origin notes, and changing no values. Which frame LocoHub should publish is a convention choice and has not been made.",
        example="A foot that rotates during push-off changes the pressure point's forward and sideways values even if the pressure point does not move on the ground.",
        figures=[],
        total_line=f"{a} of {N} recordings ({pct(a, N)}) have a pressure point in the foot frame; the other {N - a} are never exported.",
        denominator_text=f"Recordings in the source ({N}). Samples were not counted.",
        totals={"units": "recordings", "affected": a, "total": N, "never_exported": N - a},
        grid={"cells": cells, "unit": "recordings", "caption": "Recordings whose pressure point would be in the foot's frame."},
        table=participant_table(cells, "recordings"),
        knock_on=[
            K("Forward, up and sideways pressure point", V_WRONG, "Values are in the foot frame while the reference says ground frame.", "The calculation was read in both converters."),
            K("Published moments", V_OK, "The authors computed them from the plates and joint centres, not from the converters' pressure point.", "A moment rebuilt from plate force and position in the lab frame matches the published ankle moment (correlation 0.9975 to 0.9998)."),
            K("Ground forces", V_OK, "Forces are separate columns and the frame change does not touch them.", "Converter code read, not run."),
            K("Checks that use how the pressure point moves along the foot", V_NC, "Only run in 3 participants on walking and stairs; stairs gave no answer."),
        ],
        direction="A frame error in the pressure point affects anything computed from it, such as moments about the ankle or how the pressure point moves along the foot. It does not change the force itself.")

    # ---------------- C. joint signs and angles ----------------
    cnt = pilot["counts"]
    ok_ch = sum(v.get("applied_correct", 0) + v.get("suggested_correct", 0) for v in pilot["per_channel_outcomes"].values())
    assert ok_ch == cnt["applied_right"] + cnt["suggested_right"] == 141 and cnt["wrong"] == 0 and cnt["leg_channels"] == 180
    n_pilot = len(pilot["leg_assignment_gate"])
    cells = cells_from(rec, lambda r: "a")
    add(key="signs", section="Joint signs and angles", status="decided",
        title="The source's knee sign is opposite to LocoHub's",
        short=f"All {N} recordings; checked in {n_pilot}",
        wrong="The authors' plotting code and paper show hip and knee in the extension-positive direction for the segmented data, and the ankle in the dorsiflexion-positive direction. LocoHub's rule needs flexion positive for hip and knee. The knee therefore needs its sign flipped, in angle, speed and moment; hip and ankle stay as they are.",
        how="The authors' plotting code was read for its sign changes and the paper's description of the plots. The sign detector was then run on 3 participants.",
        where="Decided: José chose the rule that the named direction is positive, and this recipe follows it. It has not been applied to the data. It was reproduced from the data only for walking, inclines, declines and stairs in 3 participants.",
        example=f"AB01, AB06 and AB13 were checked on level, incline, decline and stair walking: the detector gave a sign for {ok_ch} of 180 channel checks and none was wrong; for {cnt['abstained']} it gave no answer.",
        figures=[],
        total_line=f"All {N} recordings (100%) need the knee flip. {n_pilot} recordings ({pct(n_pilot, N)}) were checked on real data: {ok_ch} of 180 channel checks right, 0 wrong, {cnt['abstained']} no answer.",
        denominator_text=f"Recordings in the source ({N}). The checks counted {n_pilot} recordings and 180 channel checks (hip, knee and ankle angle, moment and power). Samples were not counted.",
        totals={"units": "recordings", "affected": N, "total": N, "checked_recordings": n_pilot, "channel_checks": 180, "right": ok_ch, "wrong": 0, "no_answer": cnt["abstained"]},
        grid={"cells": cells, "unit": "recordings", "caption": "Recordings that need the knee sign flip (all of them). Only 20 of them were checked on real data."},
        table=participant_table(cells, "recordings"),
        knock_on=[
            K("Knee angle, knee speed and knee moment", V_WRONG, "The sign is opposite to LocoHub's until the flip is applied.", "Author plotting code and paper, plus 19 of 20 knee-angle and 18 of 20 knee-moment channel checks right in the pilot; the rest gave no answer."),
            K("Hip and ankle angle, speed and moment", V_OK, "They already have the LocoHub sign.", "Pilot: hip angle 20 of 20, ankle angle 20 of 20, ankle moment 20 of 20 and hip moment 17 of 20 checked right; none wrong."),
            K("Powers", V_NC, "Power keeps its sign when moment and speed flip together. The pilot could judge ankle power in 17 of 20, hip power in 10 of 20 and knee power in none of 20."),
            K("Tasks other than walking and stairs", V_NC, "Signs are supported by the source for all tasks but were reproduced from data only for walking, incline, decline and stairs."),
            K("Hip sideways motion, hip rotation and the subtalar joint", V_NC, "No sign rule has been adopted and the plotting evidence does not cover them."),
        ],
        direction="Flipping the knee changes knee angle, speed and moment together. Power keeps its sign. Hip and ankle are not touched.")

    cells = cells_from(rec, lambda r: "a")
    n_arch = sign_ev["publisher_vs_local_segments"]["publisher_archive_entries_examined"]
    assert sign_ev["publisher_vs_local_segments"]["Link_Angle_or_Link_Velocities_members"] == 0
    add(key="segments", section="Joint signs and angles", status="open_decide",
        title="Pelvis, thigh and shank angles are not in the source",
        short=f"All {N} recordings",
        wrong="The publisher gives joint angles (hip, knee, ankle) but no pelvis, thigh or shank angles. The local files that have them were made by our own earlier processing (a fixed turn order with a quarter-turn offset for the pelvis), which is not the publisher's definition.",
        how=f"All {n_arch:,} entries in the publisher's archive were searched and none holds segment angles or segment speeds.",
        where="Open, needs a decision. These angles are not released as standard columns until someone decides whether to compute them from the body model and checks them. Nothing is invented.",
        example="Pelvis tilt for AB02's level walking could be computed from the local transform tables, but its sign and zero point have no source to check against.",
        figures=[],
        total_line=f"All {N} recordings (100%) lack publisher segment angles.",
        denominator_text=f"Recordings in the source ({N}). Seven AB02 windows also have oversized transform tables (see the oversized-table card).",
        totals={"units": "recordings", "affected": N, "total": N},
        grid={"cells": cells, "unit": "recordings", "caption": "Recordings without publisher pelvis, thigh and shank angles (all of them)."},
        table=participant_table(cells, "recordings"),
        knock_on=[
            K("Pelvis, thigh and shank angles and speeds", V_LEFT, "Not released; no checked source definition.", "Search of the publisher archive found no segment angle or speed files."),
            K("Hip, knee and ankle angles", V_OK, "They come straight from the publisher's joint angle files.", "Source file inventory."),
            K("Facing direction used to turn forces", V_OK, "It is measured from pelvis markers, not from these angles.", "The sign-detector pilot measured it from markers on the front and back of the pelvis."),
        ],
        direction="Missing segment angles only remove those columns. Joint angles and forces do not depend on them.")

    cells = cells_from(rec, lambda r: "a")
    add(key="velocity", section="Joint signs and angles", status="documented",
        title="The README and the paper describe joint speed differently",
        short=f"All {N} recordings",
        wrong="The README says joint speed is a one-step backward difference of the angle. The paper says the angles were filtered and differentiated with a centred difference. Both cannot be right.",
        how="The README text, the paper's methods and the authors' code were compared.",
        where="Documented, kept as published. The published speeds are copied unchanged. No recomputation recipe is claimed, and no speed was replaced to match a preferred shape.",
        example="Which difference was used decides how smooth the speed looks near fast changes, such as heel strike.",
        figures=[],
        total_line=f"All {N} recordings (100%) carry joint speeds with an unconfirmed recipe.",
        denominator_text=f"Recordings in the source ({N}). Samples were not counted.",
        totals={"units": "recordings", "affected": N, "total": N},
        grid={"cells": cells, "unit": "recordings", "caption": "Recordings whose joint speed recipe is described two ways (all of them)."},
        table=participant_table(cells, "recordings"),
        knock_on=[
            K("Published joint speeds", V_OK, "Kept exactly as published.", "Values are copied by the converters; none replaced."),
            K("Published powers", V_OK, "Power matches the published moment times the published speed.", "Ratio 0.96 to 1.005 in the 5 participants of the units check."),
            K("Speeds recomputed from angles", V_NC, "A recomputation would need the right recipe, which is not established."),
        ],
        direction="Only joint speed, and anything recomputed from it, depends on the differencing method. Angles and forces do not.")

    # ---------------- D. events and task labels ----------------
    nw = [r for r in rec if r["family"] == "normal_walk"]
    run_f = sum(s in RUN_SUFFIX for r in nw for s in r["suffixes"])
    skip_f = sum(s in SKIP_SUFFIX for r in nw for s in r["suffixes"])
    all_f = sum(r["files"] for r in nw)
    grp = act["normal_walk"]["publisher_groups"]
    assert (run_f, skip_f, all_f) == (grp["run"], grp["calisthenics"], sum(grp.values())) == (22, 11, 77)
    cells = {f"{s}/{g}": [0, 0, 0] for s in SUBJECTS for g, _, _ in GROUPS}
    for s in SUBJECTS:
        sr_ = [r for r in nw if r["subject"] == s]
        cells[f"{s}/level"] = [sum(x in RUN_SUFFIX | SKIP_SUFFIX for r in sr_ for x in r["suffixes"]), sum(r["files"] for r in sr_), 0]
    pick = rng.choice([s for s in SUBJECTS if cells[f"{s}/level"][1]])
    examples["labels"] = pick
    n_lab_subj = len([s for s in SUBJECTS if cells[s + "/level"][1]])
    add(key="labels", section="Events and task labels", status="open_run",
        title="Running and skipping files are labelled as level walking",
        short=f"{run_f + skip_f} of {all_f} normal-walk event files",
        wrong="LocoHub's converter labels every normal-walk file as level walking. The authors group the 2.0 and 2.5 m/s files as running and the skipping files as skipping.",
        how="The authors' grouping code, their plotting script and the paper's Table 1 all call the 2.0 and 2.5 m/s files running.",
        where="Open, fix not yet run. LocoHub will relabel them to follow the authors' grouping. Only labels change; values are unchanged. The mistake is in LocoHub's converter, not in the source.",
        example=f"{pick}: {cells[pick + '/level'][0]} of its {cells[pick + '/level'][1]} normal-walk event files would be relabelled (running at 2.0 and 2.5 m/s, and skipping). {pick} was drawn at random.",
        figures=[{"src": "reuse-gt23-task-label.svg", "question": "How many normal-walk files are really running or skipping?", "alt": "Bar chart of normal-walk files by the authors' group: 44 walking, 22 running, 11 skipping.", "caption": "All 77 files, by the authors' group (the same figure as on the fixes page)."}],
        total_line=f"{run_f + skip_f} of {all_f} event files ({pct(run_f + skip_f, all_f)}) carry the wrong task label: {run_f} running and {skip_f} skipping. They come from {n_lab_subj} of {len(SUBJECTS)} participants; 4 of the running files hold no events.",
        denominator_text=f"The unit is event files (the authors' start and end times, one file per condition and recording): {all_f} normal-walk files in {len(nw)} recordings. Windows and samples were not counted per file.",
        totals={"units": "event files", "affected": run_f + skip_f, "total": all_f, "running": run_f, "skipping": skip_f},
        grid={"cells": cells, "unit": "event files", "caption": "Event files that would be relabelled (the other task columns have no such files)."},
        table=participant_table(cells, "event files"),
        knock_on=[
            K("Grouping of strides by task", V_WRONG, "Running and skipping strides would be pooled with level walking and change its averages.", "Authors' grouping, plotting script and paper Table 1."),
            K("Signal values (angles, forces, moments)", V_OK, "Only the label is wrong; values do not change.", "The problem is in the converter's label step."),
            K("Running files of AB05 and AB10", V_LEFT, "Four running files have no events at all; the README says there are no valid running trials for them.", "Event file sizes inspected; README text."),
            K("Right-leg events in running files", V_NC, "The README says the right plate is missing, yet the running files hold both legs; where the right-leg events came from is not checked."),
            K("Labels of the other 25 tasks", V_NC, "Only the normal-walk labels were audited."),
        ],
        direction="A wrong task label changes how strides are grouped. It does not change any measured value.")

    drop_by = {a_: (act[a_]["phase_converter_interval_use"] or {}).get("dropped_other_leg", 0) for a_ in act}
    kept_by = {a_: (act[a_]["phase_converter_interval_use"] or {}).get("kept", 0) for a_ in act}
    assert sum(drop_by.values()) == totals["phase_dropped"] and sum(kept_by.values()) == totals["phase_kept"]
    total_iv = totals["phase_kept"] + totals["phase_dropped"]
    assert total_iv == totals["intervals_left"] + totals["intervals_right"] == 13119
    cells = cells_from(rec, lambda r: "a" if r["events"] and drop_by[r["family"]] > 0 else "n")
    a, n, u = sums(cells)
    ex2 = rng.choice([x for x in sorted(act) if drop_by[x]])
    examples["secondleg"] = ex2
    add(key="secondleg", section="Events and task labels", status="open_run",
        title="The phase export drops the second leg's steps",
        short=f"{totals['phase_dropped']:,} of {total_iv:,} event windows",
        wrong="For each task the phase converter keeps only the leg with more event windows and drops the other leg's. The dropped windows include running and stairs steps and hop contacts.",
        how="The converter code was read and the kept and dropped counts were recomputed from the authors' event files, task by task.",
        where="Open, fix not yet run. The fix is to export each leg's windows with its own side.",
        example=f"{ex2.replace('_', ' ')}, drawn at random from the tasks that lose windows: {drop_by[ex2]} windows dropped, {kept_by[ex2]} kept.",
        figures=[],
        total_line=f"{totals['phase_dropped']:,} of {total_iv:,} event windows ({pct(totals['phase_dropped'], total_iv)}) never reach the phase export, in {sum(1 for x in drop_by.values() if x)} of 26 tasks, which hold {a} of {N} recordings ({pct(a, N)}). That includes {totals['phase_dropped_cycles']} single-leg gait cycles (running and stairs) and {totals['phase_dropped_hop_contacts']} hop contacts.",
        denominator_text=f"The unit is event windows: {total_iv:,} in all 787 event files of the source ({totals['intervals_left']:,} left, {totals['intervals_right']:,} right). The grid counts recordings that have windows in tasks that lose some; the per-participant split of dropped windows was not read (it needs a guarded job). Samples were not counted.",
        totals={"units": "recordings", "affected": a, "total": N, "windows_dropped": totals["phase_dropped"], "windows_total": total_iv, "gait_cycles_dropped": totals["phase_dropped_cycles"], "hop_contacts_dropped": totals["phase_dropped_hop_contacts"]},
        grid={"cells": cells, "unit": "recordings", "caption": "Recordings with event windows in a task where the phase export drops one leg's windows. How many windows each loses was not counted per participant."},
        table={"columns": ["Task", "Windows kept", "Windows dropped"], "rows": [[x.replace("_", " "), f"{kept_by[x]:,}", f"{drop_by[x]:,}"] for x in sorted(act) if drop_by[x]], "fold": True},
        knock_on=[
            K("Stride counts and averages in the phase export", V_WRONG, "One leg is missing in the affected tasks, so counts are lower and averages use one leg only.", "Kept and dropped windows recomputed from the event files."),
            K("The time-based export", V_OK, "It does not drop legs; it has its own merging problem.", "Converter code read."),
            K("Signal values inside the windows that are kept", V_OK, "Nothing is altered; whole windows are dropped.", "Converter code read."),
            K("Which leg counts as the same side in whole-body windows", V_NC, "Whether the left and right windows are identical for whole-body tasks was not read; if they are, the kept side is arbitrary. This needs a guarded job."),
        ],
        direction="Dropped windows change stride counts and which leg is represented. They do not change the values inside kept windows.")

    cells = cells_from(rec, lambda r: "a" if not r["events"] else "n")
    a, n, u = sums(cells)
    no_ev = [r for r in rec if not r["events"]]
    assert a == 90 and sum(1 for r in no_ev if r["files"] == 0) == 85 == totals["recordings_without_parsing_files"]
    ex3 = rng.choice(sorted({r["family"] for r in no_ev}))
    examples["nowindows"] = ex3
    add(key="nowindows", section="Events and task labels", status="open_decide",
        title="90 recordings have no event windows, so neither converter exports them",
        short=f"{a} of {N} recordings",
        wrong=f"The converters make their windows from the authors' event files. {a} recordings have none: 85 have no event file and 5 (AB01 stair descents) have only empty ones. The README says some AB07 treadmill trials were removed because they had no forward-back force.",
        how="The event file names and sizes were matched to every recording, and the counts agree with the full source listing.",
        where="Open, needs a decision. They could be exported as continuous recordings or left out after a review; neither has been decided.",
        example=f"One of the affected tasks, drawn at random: {ex3.replace('_', ' ')}.",
        figures=[],
        total_line=f"{a} of {N} recordings ({pct(a, N)}) have no event window and are never exported.",
        denominator_text=f"Recordings in the source ({N}). The source files for all of them exist. Samples were not counted.",
        totals={"units": "recordings", "affected": a, "total": N, "no_event_file": 85, "only_empty_files": 5},
        grid={"cells": cells, "unit": "recordings", "caption": "Recordings without an event window."},
        table=task_table(rec, lambda r: "a" if not r["events"] else "n"),
        knock_on=[
            K("All signals in these 90 recordings", V_LEFT, "Never exported by either converter, so no standard column exists for them.", "Converter code read; the full source listing lists their channel files."),
            K("Which tasks a participant did", V_WRONG, "Converted data would look as if these tasks were never recorded.", "Listing of the source recordings against the event files."),
            K("Their source files", V_OK, "All ten channel files exist for every one of them.", "The full source listing agrees with the publisher's archive."),
            K("Quality of the AB07 treadmill trials", V_NC, "The README says they were removed for missing force; they are still in the source and were not examined."),
        ],
        direction="Without a window, a recording is simply missing from the output; nothing already exported changes.")

    cells = cells_from(rec, lambda r: "a" if r["events"] else "n")
    a, n, u = sums(cells)
    assert a == n_events
    win_t = sum((act[x]["time_converter_windows"] or 0) for x in act)
    nonempty_files = totals["parsing_files"] - totals["empty_parsing_files"]
    add(key="merged", section="Events and task labels", status="open_run",
        title="The time export merges all of a file's events into one window",
        short=f"{win_t:,} windows made from {total_iv:,} event windows",
        wrong="The time-based converter makes one window per event file, from the earliest start to the latest end of every field in it. Files that hold several conditions (such as sitting and standing, or forward and backward) become one window that includes the time between them. The reference leg is simply the first start.",
        how="The converter code was read, and its window count was compared with the authors' counts.",
        where="Open, fix not yet run. The fix is one window per source interval, labelled by its field.",
        example=f"The source holds {total_iv:,} event windows in {nonempty_files} non-empty files; the converter writes {win_t:,} windows.",
        figures=[],
        total_line=f"{win_t:,} windows replace {total_iv:,} event windows; {a} of {N} recordings ({pct(a, N)}) are exported this way.",
        denominator_text=f"The unit is windows: {total_iv:,} source windows in {nonempty_files} non-empty event files. How many files hold several conditions was not counted (it needs a guarded job). Samples were not counted.",
        totals={"units": "recordings", "affected": a, "total": N, "windows_written": win_t, "windows_in_source": total_iv, "files": nonempty_files},
        grid={"cells": cells, "unit": "recordings", "caption": "Recordings the time export would merge into one window per file."},
        table=participant_table(cells, "recordings"),
        knock_on=[
            K("Window contents", V_WRONG, "A merged window can include rest between conditions.", "Converter code read: it takes the earliest start and the latest end over every field."),
            K("Reference leg", V_WRONG, "It is the first start, not a measured choice.", "Converter code read."),
            K("Signal values", V_OK, "Only the window edges are affected; values are copied.", "Converter code read."),
            K("How many windows really mix conditions", V_NC, "Not counted: it needs reading the event files one by one, which is a guarded job."),
        ],
        direction="Merged windows change what is inside each window. They do not change signal values.")

    cells = cells_from(rec, lambda r: "u" if r["family"] in ("jump", "sit_to_stand") and r["events"] else "n")
    a, n, u = sums(cells)
    add(key="fallback", section="Events and task labels", status="open_run",
        title="A backup segmentation could replace the source's events",
        short=f"0 known; {u} recordings could be exposed",
        wrong="When an event file lacks left and right fields, the phase converter replaces the source events with its own segmentation using fixed force thresholds (600 and 400 N). Any output made that way is not source-defined.",
        how="The converter code was read, and every sit-to-stand and jump event file was found to have source fields, so the backup should never run.",
        where="Open, fix not yet run. The fix is to remove the backup so the converter stops instead.",
        example="A jump recording whose event file has no left or right field would be cut at a 600 N threshold instead of the authors' pelvis-speed windows.",
        figures=[],
        total_line=f"0 of {N} recordings are known to be affected. {u} recordings in the two tasks that have a backup rule ({pct(u, N)}) could be, and nobody has checked whether it ever ran.",
        denominator_text=f"Recordings in the source ({N}). Old converted files were not opened.",
        totals={"units": "recordings", "affected": 0, "total": N, "could_be_exposed": u},
        grid={"cells": cells, "unit": "recordings", "caption": "Hatched: recordings where the backup rule exists, so it could have been used. None is shown to have been."},
        table=participant_table(cells, "recordings"),
        knock_on=[
            K("Any old output made with the backup", V_NC, "Whether the backup ever ran was not checked; it needs reading old converted files, which is a guarded job."),
            K("Source event windows in these tasks", V_OK, "Every file has source fields, so the source rule applies.", "Field inventory of the authors' event files."),
        ],
        direction="Only the window edges of these two tasks could have been affected; signal values inside are untouched.")

    ol_acts = [x for x in sorted(act) if (act[x]["events"] or {}).get("files_with_one_leg_only", 0)]
    ol_files = sum(act[x]["events"]["files_with_one_leg_only"] for x in ol_acts)
    cells = cells_from(rec, lambda r: "a" if r["events"] and r["family"] in ol_acts else "n")
    a, n, u = sums(cells)
    ex4 = rng.choice(ol_acts)
    examples["oneleg"] = ex4
    add(key="oneleg", section="Events and task labels", status="documented",
        title="Many walking files have events for one leg only",
        short=f"{ol_files} of {nonempty_files} event files",
        wrong="On the treadmill the right plate was missing for many trials. Incline files carry left-leg events only, decline files right-leg only, and several walking tasks have one leg only.",
        how="The authors' event files were counted field by field, and the README notes about the missing plate were read.",
        where="Documented, kept as published. Nothing is invented for the missing leg.",
        example=f"Drawn at random from the {len(ol_acts)} tasks with such files: {ex4.replace('_', ' ')}.",
        figures=[],
        total_line=f"{ol_files} of {nonempty_files} non-empty event files ({pct(ol_files, nonempty_files)}) hold events for one leg only, in {len(ol_acts)} tasks. {a} of {N} recordings ({pct(a, N)}) are in those tasks.",
        denominator_text=f"The unit is event files ({nonempty_files} non-empty, of 787). The grid counts recordings in tasks where at least one file has one leg only, which is more than the recordings that really do. Samples were not counted.",
        totals={"units": "recordings", "affected": a, "total": N, "files_one_leg": ol_files, "files": nonempty_files, "tasks": len(ol_acts)},
        grid={"cells": cells, "unit": "recordings", "caption": "Recordings in tasks where at least one event file has one leg only (an upper bound on the recordings that really do)."},
        table=task_table(rec, lambda r: "a" if r["events"] and r["family"] in ol_acts else "n"),
        knock_on=[
            K("Forces, moments and powers of the missing leg", V_NC, "The paper says inverse dynamics is empty off the plates, but whether the missing leg's columns are empty in the files was not checked; it needs reading channel files."),
            K("Strides of the missing leg", V_LEFT, "No events exist for them, so none can be exported.", "Event file field inventory."),
            K("Left-right comparisons", V_WRONG, "Cannot be made in these tasks.", "Field inventory shows one leg only."),
            K("Joint angles of both legs", V_NC, "Angles come from motion capture, not plates, but this was not checked per file."),
        ],
        direction="A missing plate removes force-based values for that leg. Whether it also removes angles was not checked.")

    wk = [r for r in rec if r["family"] == "weighted_walk"]
    tns = [r for r in rec if r["family"] == "turn_and_step"]
    ab02c = [r for r in rec if r["subject"] == "AB02" and r["family"] in ("curb_down", "curb_up")]
    pred = lambda r: "a" if (r["family"] in ("weighted_walk", "turn_and_step") or (r["subject"] == "AB02" and r["family"] in ("curb_down", "curb_up"))) else "n"  # noqa: E731
    cells = cells_from(rec, pred)
    a, n, u = sums(cells)
    assert a == len(wk) + len(tns) + len(ab02c)
    add(key="disagree", section="Events and task labels", status="documented",
        title="The README and the authors' own code disagree on a few tasks",
        short=f"{a} of {N} recordings in 3 places",
        wrong="Turn-and-step events: the README implies pelvis-speed windows, but the authors' plotting code titles them as cut at toe-off, and left and right counts differ inside files. Weighted walk: the README says 1.0 m/s, the plotting code says 1.25 m/s. AB02's curb files: the file name says one leg but the fields hold the other.",
        how="The README, the plotting script and the event files were compared line by line.",
        where="Documented, kept as published. None of the three is resolved, so nothing was changed.",
        example=f"Weighted walking is {len(wk)} recordings whose speed is either 1.0 or 1.25 m/s depending on the source you trust.",
        figures=[],
        total_line=f"{a} of {N} recordings ({pct(a, N)}): {len(tns)} turn-and-step, {len(wk)} weighted walk and {len(ab02c)} AB02 curb recordings.",
        denominator_text=f"Recordings in the source ({N}). Samples were not counted.",
        totals={"units": "recordings", "affected": a, "total": N, "turn_and_step": len(tns), "weighted_walk": len(wk), "ab02_curb": len(ab02c)},
        grid={"cells": cells, "unit": "recordings", "caption": "Recordings whose description disagrees between the README and the authors' code."},
        table={"columns": ["Disagreement", "Recordings", "What differs"], "rows": [["Turn and step: how events are cut", f"{len(tns)}", "README versus plotting code titles"], ["Weighted walk speed", f"{len(wk)}", "1.0 versus 1.25 m/s"], ["AB02 curb files", f"{len(ab02c)}", "File name versus the leg in the fields"]], "fold": False},
        knock_on=[
            K("Event times in turn and step", V_NC, "Which definition applies is open."),
            K("Speed-based grouping of weighted walking", V_NC, "The true speed is open."),
            K("Left and right in AB02's curb recordings", V_NC, "They may be swapped; unresolved."),
            K("Signal values in these recordings", V_OK, "None were changed; the disagreement is about descriptions and event definitions.", "Nothing in these recordings was edited."),
        ],
        direction="A wrong description changes grouping and labels, not signal values.")

    # ---------------- E. task details and source limits ----------------
    inv = {"stairs", "curb_down", "curb_up", "step_ups"}
    cells = cells_from(rec, lambda r: "a" if r["family"] in inv else "n")
    a, n, u = sums(cells)
    add(key="invented", section="Task details and source limits", status="open_run",
        title="The converter wrote stair, curb and step heights nobody measured",
        short=f"{a} of {N} recordings",
        wrong="The converter writes a stair height of 0.15 m (the paper says 152 mm), calls the pass number a step number, and writes 0.15 m for curbs and 0.20 m for step-ups. The curb and step-up heights are not in any local source.",
        how="The converter's task-detail code was compared with the paper's Table 1. The paper's supplementary protocol table is not available locally.",
        where="Open, fix not yet run. The fix is stair rise 0.152 m citing the paper, a renamed pass number, and no curb or step-up height unless a source gives one.",
        example="Stairs at 0.15 m instead of 0.152 m is 1.3% off; the curb and step-up heights are unchecked.",
        figures=[],
        total_line=f"{a} of {N} recordings ({pct(a, N)}): stairs, curbs and step-ups carry invented or rounded heights.",
        denominator_text=f"Recordings in the source ({N}). Samples do not apply: these are text fields.",
        totals={"units": "recordings", "affected": a, "total": N},
        grid={"cells": cells, "unit": "recordings", "caption": "Recordings with an invented or rounded height in their task details."},
        table=task_table(rec, lambda r: "a" if r["family"] in inv else "n"),
        knock_on=[
            K("Stair height", V_WRONG, "0.15 m instead of 0.152 m, a 1.3% error.", "The paper's Table 1 gives a 152 mm rise; the converter code writes 0.15 m."),
            K("Curb and step-up heights", V_NC, "The true heights are unknown locally."),
            K("Signal values", V_OK, "Only text fields are affected.", "The finding concerns the converter's task-detail fields."),
        ],
        direction="A wrong height affects analyses that use the height. Signals are not affected.")

    cells = {f"{s}/{g}": [0, len([r for r in rec if r["subject"] == s and r["group"] == g]), 0] for s in SUBJECTS for g, _, _ in GROUPS}
    cells["AB02/level"][0] = 1
    ov = oversized["entries"][1]
    assert len(oversized["affected_parsing_entries"]) == 7
    add(key="oversized", section="Task details and source limits", status="open_run",
        title="One recording has transform tables too large for the current limits",
        short="1 of 488 recordings; 7 event files",
        wrong=f"All seven normal-walk event files of AB02 (one recording) point at a body-transform table whose uncompressed size is about {ov['matrix_payload_bytes'] / 2**20:.0f} MiB, above the size limit the current tools accept.",
        how="The container was inspected without loading its arrays: its header and compressed parts were measured.",
        where="Open, needs a guarded job. The original is untouched. Until it is processed, these seven windows stay incomplete, not passing.",
        example="AB02's normal walking at every speed, shuffle and skip falls under this one table.",
        figures=[],
        total_line=f"1 of {N} recordings ({pct(1, N)}), and 7 of 787 event files ({pct(7, 787)}).",
        denominator_text=f"Recordings in the source ({N}) and event files (787). Samples were not counted.",
        totals={"units": "recordings", "affected": 1, "total": N, "files_affected": 7, "files": 787},
        grid={"cells": cells, "unit": "recordings", "caption": "The one recording with an oversized transform table."},
        table=participant_table(cells, "recordings"),
        knock_on=[
            K("Foot-frame pressure point and any angle that needs the transform table", V_NC, "Cannot be produced for these windows until the table is read in a guarded job."),
            K("Angles, forces and moments in the plain channel files for AB02 normal walking", V_NC, "Not examined; they are separate files."),
        ],
        direction="A missing transform table blocks the values that need it. Whether other values are fine was not checked.")

    ch = scopefile["full_raw_scope"]
    cells = cells_from(rec, lambda r: "a")
    add(key="notreconverted", section="Task details and source limits", status="open_run",
        title="Nothing has been reconverted from the full source yet",
        short=f"All {N} recordings, {ch['source_channel_files']:,} channel files",
        wrong=f"The source holds {N} recordings, each with {ch['channel_files_per_recording']} channel files ({ch['source_channel_files']:,} in all, {ch['archive_uncompressed_bytes'] / 1e9:.1f} GB uncompressed). No reviewed conversion of all of them exists, so every number on this page describes the source or the old converter code, not new output.",
        how="The local folders and the publisher archive were listed and matched recording by recording. This is a listing, not a check of any value.",
        where="Open, needs a guarded job. A pilot of the corrected converters on real data comes before any full run.",
        example="The authors' activity-flag file (when each leg is on the plate) is read by neither converter.",
        figures=[],
        total_line=f"All {N} recordings (100%) and {ch['source_channel_files']:,} channel files are still to be reconverted.",
        denominator_text=f"{N} recordings, {ch['source_channel_files']:,} channel files, 787 event files with {total_iv:,} event windows. Sample counts need a read of the channel files.",
        totals={"units": "recordings", "affected": N, "total": N, "channel_files": ch["source_channel_files"], "channel_files_per_recording": ch["channel_files_per_recording"], "event_files": 787},
        grid={"cells": cells, "unit": "recordings", "caption": "Everything is still to be reconverted (all of it)."},
        table=participant_table(cells, "recordings"),
        knock_on=[
            K("Every finding on this page about converted output", V_NC, "None has been seen in real converted data: the fixes have not been run."),
            K("The authors' activity-flag file", V_LEFT, "Neither converter reads it.", "Both converters were read."),
            K("Muscle and body-motion sensor channels", V_NC, "Which converters use them was not checked."),
            K("Quality ranges and plausibility checks", V_NC, "A quality review cannot start before a reviewed conversion exists."),
        ],
        direction="Everything downstream of conversion waits for it. The source itself is untouched.")

    # ---------------- page-level facts ----------------
    source_map = {f"{s}/{g}": [sum(1 for r in rec if r["subject"] == s and r["group"] == g)] * 2 + [0] for s in SUBJECTS for g, _, _ in GROUPS}
    not_checked = [
        {"what": "How many event windows each participant loses or merges", "why": "Needs reading the event files one by one: not checked, needs a guarded job."},
        {"what": "Whether left and right windows are identical in whole-body tasks", "why": "Not checked, needs a guarded job."},
        {"what": "Whether the backup segmentation ever ran", "why": "Needs reading old converted files: not checked, needs a guarded job."},
        {"what": "Whether the missing leg's columns are empty in one-leg files", "why": "Needs reading channel files: not checked, needs a guarded job."},
        {"what": "The mass used in the recordings that cannot be told", "why": f"{a_unk + a_prob} recordings are not shown either way: not checked."},
        {"what": "Joint signs outside walking and stairs, non-sagittal joints and knee and hip power", "why": "Not checked; the pilot could not judge them."},
        {"what": "Facing direction beyond level, incline and decline walking", "why": "Not checked."},
        {"what": "AB02's oversized transform table", "why": "Not checked, needs a guarded job."},
        {"what": "Everything in converted output", "why": "No reviewed conversion exists yet; nothing has been run on real data."},
    ]
    scope = {
        "task_id": "GT23-problems-page",
        "scientific_approval": "none",
        "builder": "contributor_tools/build_gt23_problems_page.py",
        "seed": SEED,
        "examples_drawn": examples,
        "how_examples_were_chosen": "random.Random(seed), drawn in card order from the pool named on each card; the recorded seed reproduces every draw",
        "probe": {
            "kind": "read-only listing of source folders (names and sizes only)",
            "event_files_listed": n_files,
            "recordings_listed": N,
            "empty_event_files": 9,
            "peak_rss_mib_self_reported": round(max(t0, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / 1024, 1),
        },
        "denominators": {"participants": len(SUBJECTS), "recordings": N, "tasks": 26, "channel_files": ch["source_channel_files"],
                         "channel_files_per_recording": ch["channel_files_per_recording"],
                         "event_files": 787, "event_windows": total_iv, "recordings_with_event_windows": n_events,
                         "recordings_without_event_windows": n_noevents, "uncompressed_gb": round(ch["archive_uncompressed_bytes"] / 1e9, 1)},
        "status_words": STATUS,
        "verdict_words": VERDICTS,
        "groups": [{"key": g, "label": lab, "tasks": acts} for g, lab, acts in GROUPS],
        "subjects": SUBJECTS,
        "source_map": {"cells": source_map, "unit": "recordings", "caption": "Recordings the source holds, per participant and task group."},
        "not_checked": not_checked,
        "cards": cards,
    }
    SCOPE.write_text(json.dumps(scope, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", SCOPE.relative_to(ROOT), "cards:", len(cards))


# ======================================================================================================
# figures
# ======================================================================================================
def plt_module():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.size": 10, "axes.labelsize": 10, "xtick.labelsize": 10, "ytick.labelsize": 10,
        "legend.fontsize": 10, "axes.spines.top": False, "axes.spines.right": False,
        "text.color": INK, "axes.labelcolor": INK, "axes.edgecolor": INK,
        "xtick.color": INK, "ytick.color": INK, "legend.frameon": False,
        "axes.linewidth": 0.7, "svg.hashsalt": "locohub-gt23-problems", "svg.fonttype": "path",
        "figure.facecolor": "white", "axes.facecolor": "white"})
    return plt


def save(fig, name):
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", metadata={"Date": None, "Creator": None})
    (FIGS / name).write_bytes(buf.getvalue())


def mix(pct_, base):
    import numpy as np
    t = 0.3 + 0.7 * min(max(pct_, 0.0), 100.0) / 100.0
    b = np.array([int(base[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)
    return tuple((255 * (1 - t) + b * t) / 255)


def grid_figure(plt, scope, cells, unit, name, count_map=False):
    subjects = scope["subjects"]
    groups = scope["groups"]
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 1.7 + 0.24 * len(subjects) + (0.75 if count_map else 1.05)), layout="constrained")
    ax.set_xlim(0, len(groups))
    ax.set_ylim(len(subjects), 0)
    mx = max(v[1] for v in cells.values()) or 1
    for ri, s in enumerate(subjects):
        for ci, g in enumerate(groups):
            a, n, u = cells[f"{s}/{g['key']}"]
            box = dict(xy=(ci + .06, ri + .06), width=.88, height=.88)
            if n == 0:
                ax.add_patch(plt.Rectangle(**box, fill=False, ec=GREY, lw=0.8, ls=(0, (2, 2))))
                continue
            if count_map:
                col = mix(100 * n / mx, AFTER)
                ax.add_patch(plt.Rectangle(**box, fc=col, ec="none"))
                ax.text(ci + .5, ri + .52, str(n), ha="center", va="center", fontsize=10, color="white" if n / mx >= .55 else INK)
                continue
            if a == 0 and u > 0:
                ax.add_patch(plt.Rectangle(**box, fc="#eef0f2", ec=GREY, lw=0.6, hatch="////"))
                continue
            if a == 0:
                ax.add_patch(plt.Rectangle(**box, fc="#dfe3e7", ec="none"))
                continue
            share = 100 * a / n
            ax.add_patch(plt.Rectangle(**box, fc=mix(share, BEFORE), ec="none"))
            ax.text(ci + .5, ri + .52, f"{a}/{n}" if n > 1 else "1", ha="center", va="center", fontsize=10, color="white" if share >= 55 else INK)
    ax.set_xticks([i + .5 for i in range(len(groups))])
    ax.set_xticklabels([g["label"] for g in groups], rotation=90, ha="center")
    ax.xaxis.tick_top()
    ax.set_yticks([i + .5 for i in range(len(subjects))])
    ax.set_yticklabels(subjects)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(length=0)
    if count_map:
        handles = [plt.Rectangle((0, 0), 1, 1, fc=mix(100, AFTER), label=f"Number of {unit} in the source"),
                   plt.Rectangle((0, 0), 1, 1, fill=False, ec=GREY, ls=(0, (2, 2)), label="No such recording")]
    else:
        handles = [plt.Rectangle((0, 0), 1, 1, fc=mix(100, BEFORE), label=f"Affected (affected/all {unit} in the cell)"),
                   plt.Rectangle((0, 0), 1, 1, fc="#dfe3e7", label="None affected"),
                   plt.Rectangle((0, 0), 1, 1, fc="#eef0f2", ec=GREY, hatch="////", label="None shown affected, not cleared"),
                   plt.Rectangle((0, 0), 1, 1, fill=False, ec=GREY, ls=(0, (2, 2)), label="No such recording")]
    fig.legend(handles=handles, loc="outside lower left", ncols=1, handlelength=1.6)
    save(fig, name)
    plt.close(fig)


def bar_figure(plt, scope, name):
    """Event windows kept and dropped by the phase export, per task group."""
    c01 = load("gt23-c01-events-and-frames.json")
    act = {a["activity"]: a for a in c01["activities"]}
    rows = []
    for g in scope["groups"]:
        kept = sum((act[t]["phase_converter_interval_use"] or {}).get("kept", 0) for t in g["tasks"])
        drop = sum((act[t]["phase_converter_interval_use"] or {}).get("dropped_other_leg", 0) for t in g["tasks"])
        rows.append((g["label"], kept, drop))
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 3.4), layout="constrained")
    ys = list(range(len(rows)))[::-1]
    for y, (lab, kept, drop) in zip(ys, rows):
        ax.barh(y, kept, color=MUTED, height=.6, zorder=2)
        ax.barh(y, drop, left=kept, color=BEFORE, height=.6, zorder=2)
        ax.annotate(f"{drop:,} of {kept + drop:,} dropped", (kept + drop, y), xytext=(4, 0), textcoords="offset points", va="center", fontsize=10)
    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in rows])
    ax.set_xlabel("Event windows")
    ax.set_xlim(0, max(r[1] + r[2] for r in rows) * 1.9)
    ax.grid(axis="x", color=GREY, lw=0.4, alpha=0.6, zorder=0)
    fig.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=MUTED, label="Kept by the phase export"),
                        plt.Rectangle((0, 0), 1, 1, color=BEFORE, label="Dropped (the other leg)")], loc="outside lower left", ncols=1)
    save(fig, name)
    plt.close(fig)


def build_figures():
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    FIGS.mkdir(parents=True, exist_ok=True)
    plt = plt_module()
    sm = scope["source_map"]
    grid_figure(plt, scope, sm["cells"], sm["unit"], "scope-map.svg", count_map=True)
    for c in scope["cards"]:
        g = c["grid"]
        grid_figure(plt, scope, g["cells"], g["unit"], f"scope-{c['key']}.svg")
    bar_figure(plt, scope, "bars-secondleg.svg")
    for src, dst in (("gt23-mass.svg", "reuse-gt23-mass.svg"), ("gt23-units-before.svg", "reuse-gt23-units-before.svg"),
                     ("gt23-units-after.svg", "reuse-gt23-units-after.svg"), ("gt23-task-label.svg", "reuse-gt23-task-label.svg")):
        shutil.copyfile(FIXFIGS / src, FIGS / dst)
    print("figures written to", FIGS.relative_to(ROOT))


# ======================================================================================================
# page (reads only the scope file and the figure files)
# ======================================================================================================
def esc(s) -> str:
    return html.escape(str(s), quote=True)


VERDICT_CLASS = {V_WRONG: "v-wrong", V_OK: "v-ok", V_LEFT: "v-left", V_NC: "v-nc"}
STATUS_CLASS = {"fixed": "s-fixed", "decided": "s-decided", "open_run": "s-open", "open_decide": "s-open", "documented": "s-doc"}
GRID_QUESTION = {
    "mass": "Which recordings carry another participant's mass?", "units": "Which recordings are covered by the wrong README units?",
    "ab03mass": "Which recordings get the wrong mass for forces in body weights?", "forceframe": "Which recordings get wrongly labelled horizontal force?",
    "forward": "Which recordings are in tasks with no single forward direction?", "cop": "Which recordings get a pressure point in the foot's frame?",
    "signs": "Which recordings need the knee sign flip?", "segments": "Which recordings lack pelvis, thigh and shank angles?",
    "velocity": "Which recordings have a joint speed with an unconfirmed recipe?", "labels": "Which event files carry the wrong task label?",
    "secondleg": "Which recordings lose the second leg's windows?", "nowindows": "Which recordings have no event window?",
    "merged": "Which recordings are merged into one window per file?", "fallback": "Which recordings could have used the backup segmentation?",
    "oneleg": "Which recordings are in tasks with one-leg event files?", "disagree": "Which recordings have a disputed description?",
    "invented": "Which recordings carry invented heights?", "oversized": "Which recording has the oversized table?",
    "notreconverted": "Which recordings are still to be reconverted?"}

CSS = """
.gt23p section { padding-top: .3rem; }
.gt23p h2 { margin-top: 2rem; }
.gt23p .sec-h { margin: 1.8rem 0 .2rem; font-size: 1.25rem; border-bottom: 2px solid var(--line); padding-bottom: .2rem; }
.gt23p .lead { max-width: 72ch; }
.gt23p .plain-table { width: 100%; border-collapse: collapse; font-size: .88rem; }
.gt23p .plain-table th, .gt23p .plain-table td { text-align: left; vertical-align: top; padding: .45rem .6rem; border-bottom: 1px solid var(--line); }
.gt23p .table-scroll { overflow-x: auto; }
.gt23p .plain-table { min-width: 34rem; }
.gt23p .note { color: var(--muted); font-size: .82rem; max-width: 72ch; }
.gt23p .fix-card h3 { margin: 0 0 .35rem; font-size: 1.1rem; }
.gt23p .scope-block { border-top: 1px solid var(--line); margin-top: .9rem; padding-top: .4rem; }
.gt23p .scope-block h4 { margin: .2rem 0 .4rem; font-size: 1rem; }
.gt23p .scope-total { max-width: 72ch; font-weight: 600; margin: .2rem 0; }
.gt23p .scope-table { min-width: 31rem; }
.gt23p .scope-fold > summary { cursor: pointer; font-size: .9rem; padding: .3rem 0; }
.gt23p .fig-question { font-weight: 600; margin: .8rem 0 .2rem; max-width: 72ch; }
.gt23p .ko-list { list-style: none; margin: .3rem 0; padding: 0; max-width: 80ch; }
.gt23p .ko-item { padding: .5rem 0; border-bottom: 1px solid var(--line); font-size: .92rem; }
.gt23p .ko-evidence { display: block; color: var(--muted); font-size: .85rem; margin-top: .15rem; }
.gt23p .ko-direction { max-width: 72ch; font-size: .92rem; }
.gt23p .verdict, .gt23p .status-pill { display: inline-block; font-size: .78rem; font-weight: 600; padding: .05rem .45rem; border-radius: 3px; border: 1px solid currentColor; margin-right: .3rem; }
.gt23p .verdict { white-space: nowrap; }
.gt23p .v-ok { color: #1f6aa5; } .gt23p .v-wrong { color: #a3361a; } .gt23p .v-left { color: #8a5a00; } .gt23p .v-nc { color: #6b4a9a; }
.gt23p .s-fixed { color: #1b7a43; } .gt23p .s-decided { color: #1f6aa5; } .gt23p .s-open { color: #a3361a; } .gt23p .s-doc { color: #8a5a00; }
@media (prefers-color-scheme: dark) { .gt23p .v-ok { color: #6db3e8; } .gt23p .v-wrong { color: #f08a6e; } .gt23p .v-left { color: #e0a93b; } .gt23p .v-nc { color: #b99be0; }
  .gt23p .s-fixed { color: #5cc98a; } .gt23p .s-decided { color: #6db3e8; } .gt23p .s-open { color: #f08a6e; } .gt23p .s-doc { color: #e0a93b; } }
@media (max-width: 40rem) { .gt23p .scope-table th, .gt23p .scope-table td, .gt23p .plain-table th, .gt23p .plain-table td { padding: .35rem .4rem; font-size: .8rem; } .gt23p .plain-table { min-width: 28rem; } }
.gt23p .status-line { margin: .2rem 0 .6rem; }
.gt23p .status-key { max-width: 72ch; padding-left: 1.1rem; font-size: .92rem; }
.gt23p .status-key li { margin: .3rem 0; }
.gt23p .fix-figure img { max-width: 100%; }
"""


def fig_img(src, label, alt, cap=""):
    svg = (FIGS / src).read_text(encoding="utf-8")
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
    w, h = float(m.group(1)), float(m.group(2))
    c = f"<figcaption>{esc(cap)}</figcaption>" if cap else ""
    return (f'<figure class="fix-figure"><figcaption class="fix-side">{esc(label)}</figcaption>'
            f'<img src="figures/{src}" width="{round(w * 100 / 72)}" height="{round(h * 100 / 72)}" loading="lazy" alt="{esc(alt)}">{c}</figure>')


def table_html(t, label):
    head = "".join(f"<th>{esc(c)}</th>" for c in t["columns"])
    body = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in row) + "</tr>" for row in t["rows"])
    tb = (f'<div class="table-scroll" role="region" aria-label="{esc(label)}" tabindex="0">'
          f'<table class="plain-table scope-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')
    if t["fold"]:
        tb = f'<details class="scope-fold"><summary>Show all {len(t["rows"])} rows</summary>{tb}</details>'
    return tb


def card_html(c):
    figs = "".join(f'<p class="fig-question">{esc(f["question"])}</p><div class="fix-figures fix-figures-single">{fig_img(f["src"], f["question"], f["alt"], f["caption"])}</div>' for f in c["figures"])
    g = c["grid"]
    q = GRID_QUESTION[c["key"]]
    grid = fig_img(f"scope-{c['key']}.svg", q, f"Grid of participants by task group. {g['caption']}", g["caption"])
    bars = ""
    if c["key"] == "secondleg":
        bq = "How many event windows does each kind of task lose?"
        bars = (f'<p class="fig-question">{bq}</p><div class="fix-figures fix-figures-single">'
                + fig_img("bars-secondleg.svg", bq, "Bars of event windows kept and dropped per task group.", "Windows kept and dropped by the phase export.") + "</div>")
    scope = (f'<div class="scope-block"><h4>How much was affected</h4><p class="scope-total">{esc(c["total_line"])}</p>'
             f'<p class="note">{esc(c["denominator_text"])}</p><div class="fix-figures fix-figures-single">{grid}</div>'
             f'{table_html(c["table"], c["title"] + ": affected")}</div>')
    items = []
    for k in c["knock_on"]:
        ev = f'<span class="ko-evidence"><em>How we know:</em> {esc(k["evidence"])}</span>' if k["evidence"] else ""
        items.append(f'<li class="ko-item"><span class="verdict {VERDICT_CLASS[k["verdict"]]}">{esc(k["verdict"])}</span> <strong>{esc(k["signal"])}.</strong> {esc(k["line"])} {ev}</li>')
    d = f'<p class="ko-direction">{esc(c["direction"])}</p>' if c["direction"] else ""
    knock = f'<div class="scope-block"><h4>What else this could affect</h4>{d}<ul class="ko-list">{"".join(items)}</ul></div>'
    how = f'<p><strong>How we know.</strong> {esc(c["how"])}</p>' if c["how"] else ""
    return (f'<article class="fix-card" id="{c["key"]}"><h3>{esc(c["title"])}</h3>'
            f'<p class="status-line"><span class="status-pill {STATUS_CLASS[c["status"]]}">{esc(STATUS[c["status"]])}</span></p>'
            f'<p><strong>What is wrong.</strong> {esc(c["wrong"])}</p>{how}'
            f'<p><strong>Where it stands.</strong> {esc(c["where"])}</p>{figs}{bars}'
            f'<p class="fix-evidence"><strong>Example.</strong> {esc(c["example"])}</p>{scope}{knock}</article>')


def build_page(scope) -> str:
    d = scope["denominators"]
    cards = scope["cards"]
    sections = []
    for c in cards:
        if c["section"] not in sections:
            sections.append(c["section"])
    summary_rows = "".join(
        f'<tr><td><a href="#{c["key"]}">{esc(c["title"])}</a></td><td>{esc(STATUS[c["status"]])}</td><td>{esc(c["short"])}</td></tr>' for c in cards)
    body_cards = "".join(f'<h3 class="sec-h">{esc(s)}</h3>' + "".join(card_html(c) for c in cards if c["section"] == s) for s in sections)
    nc = "".join(f'<li>{esc(x["what"])}. {esc(x["why"])}</li>' for x in scope["not_checked"])
    status_key = "".join(f'<li><span class="status-pill {STATUS_CLASS[k]}">{esc(v)}</span> {esc(t)}</li>' for (k, v), t in zip(
        scope["status_words"].items(),
        ["A fix was run on real data and independently checked. None of these problems is in this state yet.",
         "A person decided what to do. The fix has not been run on data.",
         "A fix is known and has not been run; no decision is needed.",
         "A choice about conventions or scope is still needed.",
         "No fix is planned. The published values are kept and the problem is written down."]))
    smap = scope["source_map"]
    mapfig = fig_img("scope-map.svg", "What does the source hold, per participant and task?", "Grid of participants by task group, with the number of recordings in each cell.", smap["caption"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Georgia Tech 2023: the known problems, how much data each touches and what else it could affect.">
  <meta name="color-scheme" content="light dark">
  <title>Georgia Tech 2023: known problems · LocoHub</title>
  <link rel="stylesheet" href="../../stylesheets/site.css">
  <link rel="stylesheet" href="../../stylesheets/dataset-pages.css">
  <link rel="stylesheet" href="../../stylesheets/visual-styles.css">
  <link rel="stylesheet" href="../../stylesheets/fixes.css">
  <script src="../../javascripts/visual-styles.js"></script>
  <script src="../../javascripts/extra.js" defer></script>
  <style>{CSS}</style>
</head>
<body class="dataset-detail">
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header">
    <div class="header-inner">
      <a class="wordmark" href="../../index.html" aria-label="LocoHub home">LocoHub</a>
      <nav class="primary-nav" aria-label="Main navigation"><a href="../../index.html" aria-current="page">Data</a>
<a href="../../tutorials/index.html">Tutorials</a>
<a href="../../reference/index.html">File format</a>
<a href="../../quality/index.html">Testing &amp; data quality</a></nav>
      <form class="header-search" role="search" aria-label="Site search" action="../../search/index.html"><label class="visually-hidden" for="header-query">Search documentation</label><input id="header-query" type="search" name="q" placeholder="Search docs" required><button type="submit">Search</button></form>
      <a class="repository-link" href="https://github.com/jmontp/LocoHub">GitHub</a>
    </div>
  </header>
  <div class="page-layout wide-page">
    <main id="main" class="page-content gt23p" tabindex="-1">
      <div class="page-kicker"><a href="../../index.html">LocoHub</a><span aria-hidden="true">/</span><a href="index.html">Georgia Tech 2023</a><span aria-hidden="true">/</span>Known problems</div>
      <header class="dataset-heading"><h1 id="gt23-problems">Georgia Tech 2023: known problems</h1>
<p class="dataset-note">Not reconverted and not released. Nothing on this page has been approved scientifically, and no fix on it has been applied to data.</p></header>
      <nav class="dataset-section-nav" aria-label="Sections"><a href="#what-this-is">What this is</a><a href="#at-a-glance">At a glance</a><a href="#problems">The problems</a><a href="#not-checked">What we did not check</a></nav>

      <section id="what-this-is" aria-labelledby="what-h"><h2 id="what-h">What this is</h2>
      <p class="lead">Georgia Tech 2023 has {d['participants']} participants and {d['recordings']} recordings of {d['tasks']} tasks, each with {d['channel_files_per_recording']} channel files ({d['channel_files']:,} in all, {d['uncompressed_gb']} GB). The authors also supplied {d['event_files']} event files that list {d['event_windows']:,} start and end times; {d['recordings_with_event_windows']} recordings have event windows and {d['recordings_without_event_windows']} have none. This page lists every problem we know, how much of the source each one touches, and what else it could affect.</p>
      <p class="note">Unlike the pages of datasets that were reconverted, this page says where each problem stands instead of what we did. Counts are measured against the source, and each card states what it counts. Example recordings are drawn at random with a recorded seed, not hand-picked.</p>
      <div class="fix-figures fix-figures-single">{mapfig}</div>
      <h3>Where a problem can stand</h3>
      <ul class="status-key">{status_key}</ul></section>

      <section id="at-a-glance" aria-labelledby="glance-h"><h2 id="glance-h">At a glance</h2>
      <div class="table-scroll" role="region" aria-label="All problems" tabindex="0"><table class="plain-table"><thead><tr><th>Problem</th><th>Where it stands</th><th>How much</th></tr></thead><tbody>{summary_rows}</tbody></table></div></section>

      <section id="problems" aria-labelledby="problems-h"><h2 id="problems-h">The problems</h2>
      <p class="note">One card per problem. Each card says what is wrong, where it stands, how much of the source it touches, and what else it could affect. A verdict is given only where there is evidence; otherwise it says not checked.</p>
      {body_cards}</section>

      <section id="not-checked" aria-labelledby="nc-h"><h2 id="nc-h">What we did not check</h2>
      <ul>{nc}</ul>
      <p class="note">Numbers about reading source files come from file names and sizes only; no recording was opened for this page.</p></section>
    </main>
  </div>
  <footer class="site-footer"><p>LocoHub</p><nav aria-label="Additional links"><a href="../../contributing/index.html">Contribute data</a><a href="../../maintainers/index.html">Maintainers</a><a href="../../reference/index.html#release-evidence">Download notes</a><a href="https://github.com/jmontp/LocoHub/issues">Report an issue</a></nav></footer>
</body>
</html>
"""


def write_page():
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    OUT.write_text(build_page(scope), encoding="utf-8")
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "figures").mkdir(exist_ok=True)
    shutil.copyfile(OUT, SITE_DIR / "problems.html")
    for f in FIGS.glob("*.svg"):
        shutil.copyfile(f, SITE_DIR / "figures" / f.name)
    print("wrote", OUT.relative_to(ROOT), "and copied to", SITE_DIR.relative_to(ROOT))


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage in ("scope", "all"):
        build_scope()
    if stage in ("figures", "all"):
        build_figures()
    if stage in ("page", "all"):
        write_page()


if __name__ == "__main__":
    main()
