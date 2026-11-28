#!/usr/bin/env python3
"""GA26-C01 bounded probe: sign of the stored Gait120 knee_angle_r/_l columns.

Question: in the publisher JointAngle .mot files, is knee_angle_{r,l} positive
for knee extension (paper Fig. 4 caption, right limb only) or for flexion
(the unmodified Rajagopal 2016 coordinate)? The left side has no paper evidence.

Rules are fixed here before any data are read, and do not use the converter:
- Transfers. The seated frame is the first sample of SitToStand and the last
  sample of StandToSit (paper p. 5: start/end frames from pelvis and shoulder
  markers on a 490 mm stool). The hip is the anchor: hip_flexion_<side> must be
  >= +45 deg at the seated frame (seated hip flexion), otherwise the file is
  'anchor_failed'. Then knee_angle_<side> <= -45 deg means extension-positive,
  >= +45 deg flexion-positive, anything between is indeterminate.
- Locomotion (five gait tasks). Swing knee flexion is large in every task.
  min <= -40 and max <= +20 deg: extension-positive; max >= +40 and
  min >= -20 deg: flexion-positive; otherwise indeterminate.
- A side's verdict is a sign only when every sampled file gives that sign.
  Any disagreement, indeterminate file or anchor failure leaves it unresolved.

Bounds: at most 21 files (3 per task), each at most 2 MiB, read once, one
thread, no pandas, no writes except the output JSON. Subjects are drawn with a
recorded seed from the committed source inventory, not hand-picked. Run only
through the reviewed guarded launcher when the numerical slot is free.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

TASKS = ("LevelWalking", "StairAscent", "StairDescent", "SlopeAscent",
         "SlopeDescent", "SitToStand", "StandToSit")
TRANSFERS = {"SitToStand": "first", "StandToSit": "last"}
MAX_FILES = 21
MAX_BYTES = 2 * 1024 * 1024
SEED = 20261031
SIDES = ("r", "l")


def parse_mot(text: str) -> dict[str, list[float]]:
    """Parse an OpenSim .mot text (header, 'endheader', labels, rows)."""
    lines = text.splitlines()
    try:
        end = next(i for i, line in enumerate(lines) if line.strip().lower() == "endheader")
    except StopIteration as exc:
        raise ValueError("no endheader line") from exc
    labels = lines[end + 1].split()
    cols: dict[str, list[float]] = {name: [] for name in labels}
    for line in lines[end + 2:]:
        if not line.strip():
            continue
        values = line.split()
        if len(values) != len(labels):
            raise ValueError("row width differs from label count")
        for name, value in zip(labels, values):
            cols[name].append(float(value))
    if not cols.get("time"):
        raise ValueError("no data rows")
    if "indegrees=yes" not in text[: text.lower().find("endheader")].lower().replace(" ", ""):
        raise ValueError("header does not state inDegrees=yes")
    return cols


def classify(task: str, cols: dict[str, list[float]], side: str) -> dict:
    knee = cols[f"knee_angle_{side}"]
    out = {"knee_min_deg": min(knee), "knee_max_deg": max(knee)}
    if task in TRANSFERS:
        idx = 0 if TRANSFERS[task] == "first" else -1
        hip = cols[f"hip_flexion_{side}"][idx]
        k = knee[idx]
        out.update(seated_hip_flexion_deg=hip, seated_knee_angle_deg=k)
        if hip < 45.0:
            out["call"] = "anchor_failed"
        elif k <= -45.0:
            out["call"] = "extension_positive"
        elif k >= 45.0:
            out["call"] = "flexion_positive"
        else:
            out["call"] = "indeterminate"
        return out
    lo, hi = out["knee_min_deg"], out["knee_max_deg"]
    if lo <= -40.0 and hi <= 20.0:
        out["call"] = "extension_positive"
    elif hi >= 40.0 and lo >= -20.0:
        out["call"] = "flexion_positive"
    else:
        out["call"] = "indeterminate"
    return out


def verdict(calls: list[str]) -> str:
    if calls and all(c == "extension_positive" for c in calls):
        return "extension_positive"
    if calls and all(c == "flexion_positive" for c in calls):
        return "flexion_positive"
    return "unresolved"


def select(recordings: list[str], per_task: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    chosen = []
    for task in TASKS:
        by_subject: dict[str, str] = {}
        for rel in sorted(recordings):
            parts = rel.split("/")
            if parts[2] == task and parts[4] == "step01.mot":
                by_subject.setdefault(parts[0], rel)  # lowest trial with a step01
        subjects = sorted(by_subject)
        for subject in rng.sample(subjects, min(per_task, len(subjects))):
            chosen.append(by_subject[subject])
    if len(chosen) > MAX_FILES:
        raise ValueError("selection exceeds the file cap")
    return chosen


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source-root", type=Path, required=True)
    ap.add_argument("--inventory", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--per-task", type=int, default=3)
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite existing output")
    recordings = json.loads(args.inventory.read_text())["recordings"]
    files = select(recordings, args.per_task, args.seed)
    rows = []
    for rel in files:
        path = args.source_root / rel
        size = path.stat().st_size
        if size > MAX_BYTES:
            raise SystemExit(f"file over cap: {rel} ({size} bytes)")
        raw = path.read_bytes()
        cols = parse_mot(raw.decode("utf-8", errors="strict"))
        task = rel.split("/")[2]
        rows.append({"recording": rel, "sha256": hashlib.sha256(raw).hexdigest(), "task": task,
                     "n_rows": len(cols["time"]),
                     **{side: classify(task, cols, side) for side in SIDES}})
    result = {
        "probe": "GA26-C01 knee sign", "seed": args.seed, "per_task": args.per_task,
        "inventory_sha256": hashlib.sha256(args.inventory.read_bytes()).hexdigest(),
        "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "files": rows,
        "verdict": {side: verdict([r[side]["call"] for r in rows]) for side in SIDES},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result["verdict"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
