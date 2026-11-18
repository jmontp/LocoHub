#!/usr/bin/env python3
"""Read-only probe for the Georgia Tech 2021 problems page (two small questions).

1. How big is the joint-angle zero difference? Read each participant's static-pose joint angles (the
   quantity the authors' script subtracts to make the "relative to static pose" file) and report them
   per joint. The relative file itself is not readable by the restricted reader; one seeded attempt
   per mode records that.
2. Does the same lab sideways axis point the same way for both feet? For three randomly drawn
   treadmill recordings, read the force plate table and report the mean sideways force over stance
   on each plate, plus the average stance curve of one drawn recording.

One source table in memory at a time; writes only docs/quality/audits/gt21-problem-scope-probe.json.
Run alone: flock /tmp/locohub-probe.lock nice -n 19 ionice -c 3 /usr/bin/time -v python3 contributor_tools/probe_gt21_problem_scope.py
"""
from __future__ import annotations

import gc
import json
import random
import resource
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "contributor_tools"))
from gt21_numeric_source import read_numeric_table  # noqa: E402

SRC = ROOT / "contributor_tools/conversion_scripts/Gtech_2021/CAMARGO_ET_AL_J_BIOMECH_DATASET"
OUT = ROOT / "docs/quality/audits/gt21-problem-scope-probe.json"
SEED = 20261118
MODES = ["levelground", "ramp", "stair", "treadmill"]
JOINTS = ["hip_flexion_r", "hip_flexion_l", "knee_angle_r", "knee_angle_l", "ankle_angle_r", "ankle_angle_l", "pelvis_tilt"]


def listing(mode, channel):
    return sorted(p for p in SRC.glob(f"AB*/*/{mode}/{channel}/*.mat"))


def rel(p):
    return str(p.relative_to(SRC))


REJECTED = []


def zero_probe(rng):
    """The relative-to-static-pose joint angle file cannot be read by the restricted reader, so
    read each participant's static-pose angles (the quantity the authors' script subtracts)."""
    tried = []
    for mode in MODES:  # one seeded recording per mode: can the relative file be read at all?
        pick = rng.choice(listing(mode, "ik_offset"))
        try:
            read_numeric_table(pick)
            tried.append({"mode": mode, "recording": rel(pick.parent.parent / "conditions" / pick.name), "admitted": True})
        except ValueError as exc:
            tried.append({"mode": mode, "recording": rel(pick.parent.parent / "conditions" / pick.name), "admitted": False, "why": str(exc)})
    people = []
    for pick in sorted(SRC.glob("AB*/*/static/ik/*.mat")):
        try:
            t = read_numeric_table(pick)
        except ValueError as exc:
            people.append({"participant": pick.parts[len(SRC.parts)], "rejected": str(exc)})
            continue
        row = {"participant": pick.parts[len(SRC.parts)], "samples": int(t["Header"].size), "static_angle_deg_mean": {}, "static_angle_deg_sd": {}}
        for j in JOINTS:
            ok = np.isfinite(t[j])
            row["static_angle_deg_mean"][j] = float(t[j][ok].mean())
            row["static_angle_deg_sd"][j] = float(t[j][ok].std())
        people.append(row)
        del t
        gc.collect()
    return {"relative_file_read_attempts": tried, "static_pose_angles": people}


def stance_probe(rng):
    files = listing("treadmill", "fp")
    picks = rng.sample(files, 12)
    out = []
    for pick in picks:
        if len(out) == 3:
            break
        k = len(out)
        try:
            t = read_numeric_table(pick)
        except ValueError as exc:
            REJECTED.append({"recording": rel(pick.parent.parent / "conditions" / pick.name), "why": str(exc)})
            continue
        t_s = float(np.median(np.diff(t["Header"])))
        row = {"recording": rel(pick.parent.parent / "conditions" / pick.name), "pool": len(files), "plates": {}}
        for plate in ("Treadmill_R", "Treadmill_L"):
            vx, vy = t[f"{plate}_vx"], t[f"{plate}_vy"]
            contact = np.isfinite(vy) & (vy > 100.0)
            idx = np.flatnonzero(contact)
            cuts = np.flatnonzero(np.diff(idx) > 1)
            starts = np.r_[idx[0], idx[cuts + 1]] if idx.size else np.array([], int)
            ends = np.r_[idx[cuts], idx[-1]] if idx.size else np.array([], int)
            curves_x, curves_y = [], []
            for s, e in zip(starts, ends):
                if (e - s) * t_s < 0.3:
                    continue
                grid = np.linspace(s, e, 100)
                curves_x.append(np.interp(grid, np.arange(vx.size), vx))
                curves_y.append(np.interp(grid, np.arange(vy.size), vy))
            p = {"contact_samples": int(contact.sum()), "bouts": len(curves_x),
                 "mean_sideways_force_N_over_contact": float(np.nanmean(vx[contact])),
                 "share_of_contact_with_positive_x": float(np.mean(vx[contact] > 0)),
                 "mean_vertical_force_N_over_contact": float(np.nanmean(vy[contact]))}
            if k == 0 and curves_x:
                p["curve_sideways_N"] = [float(v) for v in np.mean(curves_x, axis=0)]
                p["curve_vertical_N"] = [float(v) for v in np.mean(curves_y, axis=0)]
            row["plates"][plate] = p
        row["sample_period_s"] = t_s
        out.append(row)
        del t
        gc.collect()
    return out


def main():
    rng = random.Random(SEED)
    result = {"seed": SEED, "script": "contributor_tools/probe_gt21_problem_scope.py", "scientific_approval": False,
              "reads": "one source table at a time; nothing written under converted_datasets or source folders",
              "joint_zero": zero_probe(rng), "stance_sideways": stance_probe(rng), "reader_rejections": REJECTED,
              "peak_rss_mib_self_reported": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0}
    OUT.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print("wrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
