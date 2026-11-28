#!/usr/bin/env python3
"""Read-only probe for the UM21 fix-scope page blocks (task UM21-R01, follow-up).

Streams the local review bundle's full.parquet once, one stride (150 rows) at a time,
with pyarrow (system memory pool, 4096-row batches, no threads, no read buffer), and
writes ONE small JSON summary: docs/quality/audits/um21-r01-fix-scope-probe.json.
Nothing is written under converted_datasets/. Run alone at nice 19 / ionice idle:

  ARROW_DEFAULT_MEMORY_POOL=system nice -n 19 ionice -c 3 /usr/bin/time -v \
      python3 contributor_tools/probe_um21_fix_scope.py

What it measures (per recording, from the released columns only):
  * identities between columns: thigh = hip + pelvis, shank = thigh - knee
  * whether each stored speed matches the slope of its stored angle
  * hip angle size (mean of each stride's range) to compare AB04 level with the rest
  * ankle moment, ankle power and the power-vs-moment-times-speed correlation for the
    AB07 10 degree incline right-ankle strides that were turned back by 180 degrees
    versus the other strides of the same recording side
"""
from __future__ import annotations

import json
import os

os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")
import resource  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "converted_datasets/reconversion_v2/um21_r01_review_v2"
OUT = ROOT / "docs/quality/audits/um21-r01-fix-scope-probe.json"
SEED_NOTE = "no random sampling: every stride in the full version is read once"

COLS = [
    "observation_id", "reference_side", "source_start_time_s", "source_end_time_s", "ankle_reexpressed",
    "pelvis_sagittal_angle_rad", "hip_flexion_angle_ipsi_rad", "knee_flexion_angle_ipsi_rad",
    "ankle_dorsiflexion_angle_ipsi_rad", "thigh_sagittal_angle_ipsi_rad", "shank_sagittal_angle_ipsi_rad",
    "pelvis_sagittal_velocity_rad_s", "thigh_sagittal_velocity_ipsi_rad_s", "shank_sagittal_velocity_ipsi_rad_s",
    "ankle_dorsiflexion_moment_ipsi_Nm_kg", "ankle_dorsiflexion_power_ipsi_W_kg",
    "quality_status", "failed_limits",
]


def recording_of(obs_id: str) -> str:
    # um21:Streaming/AB04/Tread/i0:right:frames:a:b
    parts = obs_id.split(":")[1].split("/")
    return f"{parts[1]}/{parts[3]}"


def corr(a, b):
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 10:
        return None
    a, b = a[m], b[m]
    if a.std() < 1e-12 or b.std() < 1e-12:
        return None
    return float(np.corrcoef(a, b)[0, 1])


class Acc:
    def __init__(self):
        self.n = 0
        self.id_thigh = 0.0
        self.id_shank = 0.0
        self.vel = {"pelvis": [], "thigh": [], "shank": []}
        self.hip_range = []
        self.hip_mean = []
        self.pelvis_mean = []
        self.pelvis_range = []
        self.moment_range = []
        self.power_range = []


class Ankle:
    def __init__(self):
        self.max_step = {"hip": [], "knee": [], "ankle": []}
        self.failed = {}
        self.moment_range = []
        self.power_range = []
        self.r = []
        self.ankle_range = []


def main() -> None:
    pf = pq.ParquetFile(BUNDLE / "full.parquet", buffer_size=0)
    per = {}
    stretch = {True: Ankle(), False: Ankle()}
    seen = set()
    cur_id, buf = None, []

    def flush():
        nonlocal cur_id, buf
        if cur_id is None:
            return
        assert cur_id not in seen
        seen.add(cur_id)
        d = {c: np.array([r[i] for r in buf], dtype=float if c not in ("observation_id", "reference_side", "ankle_reexpressed", "quality_status", "failed_limits") else object)
             for i, c in enumerate(COLS)}
        assert len(buf) == 150, (cur_id, len(buf))
        rec = recording_of(cur_id)
        a = per.setdefault(rec, Acc())
        a.n += 1
        dur = float(d["source_end_time_s"][0] - d["source_start_time_s"][0])
        dt = dur / 149.0
        pel, hip, knee = d["pelvis_sagittal_angle_rad"], d["hip_flexion_angle_ipsi_rad"], d["knee_flexion_angle_ipsi_rad"]
        th, sh = d["thigh_sagittal_angle_ipsi_rad"], d["shank_sagittal_angle_ipsi_rad"]
        a.id_thigh = max(a.id_thigh, float(np.nanmax(np.abs(th - (hip + pel)))) if np.isfinite(th).any() else 0.0)
        a.id_shank = max(a.id_shank, float(np.nanmax(np.abs(sh - (th - knee)))) if np.isfinite(sh).any() else 0.0)
        for name, ang, vel in (("pelvis", pel, d["pelvis_sagittal_velocity_rad_s"]),
                               ("thigh", th, d["thigh_sagittal_velocity_ipsi_rad_s"]),
                               ("shank", sh, d["shank_sagittal_velocity_ipsi_rad_s"])):
            r = corr(np.gradient(ang, dt), vel)
            if r is not None:
                a.vel[name].append(r)
        if np.isfinite(hip).all():
            a.hip_range.append(float(hip.max() - hip.min()))
            a.hip_mean.append(float(hip.mean()))
        if np.isfinite(pel).all():
            a.pelvis_mean.append(float(pel.mean()))
            a.pelvis_range.append(float(pel.max() - pel.min()))
        mom, pw, ank = d["ankle_dorsiflexion_moment_ipsi_Nm_kg"], d["ankle_dorsiflexion_power_ipsi_W_kg"], d["ankle_dorsiflexion_angle_ipsi_rad"]
        if np.isfinite(mom).all():
            a.moment_range.append(float(mom.max() - mom.min()))
        if np.isfinite(pw).all():
            a.power_range.append(float(pw.max() - pw.min()))
        if rec == "AB07/i10" and d["reference_side"][0] == "right" and np.isfinite(ank).all():
            s = stretch[bool(d["ankle_reexpressed"][0])]
            if np.isfinite(mom).all():
                s.moment_range.append(float(mom.max() - mom.min()))
            if np.isfinite(pw).all():
                s.power_range.append(float(pw.max() - pw.min()))
                r = corr(pw, mom * np.gradient(ank, dt))
                if r is not None:
                    s.r.append(r)
            s.ankle_range.append(float(ank.max() - ank.min()))
            for nm, arr in (("hip", hip), ("knee", knee), ("ankle", ank)):
                s.max_step[nm].append(float(np.degrees(np.abs(np.diff(arr)).max())))
            key = str(d["quality_status"][0]) + "|" + str(d["failed_limits"][0])
            s.failed[key] = s.failed.get(key, 0) + 1
        cur_id, buf = None, []

    for batch in pf.iter_batches(batch_size=4096, columns=COLS, use_threads=False):
        cols = [batch.column(i).to_pylist() for i in range(len(COLS))]
        for row in zip(*cols):
            if row[0] != cur_id:
                flush()
                cur_id = row[0]
            buf.append(row)
    flush()

    def med(x):
        return None if not x else round(float(np.median(x)), 6)

    def mean(x):
        return None if not x else round(float(np.mean(x)), 6)

    recs = {}
    for rec in sorted(per):
        a = per[rec]
        recs[rec] = {
            "strides": a.n,
            "max_abs_thigh_minus_hip_plus_pelvis_rad": a.id_thigh,
            "max_abs_shank_minus_thigh_minus_knee_rad": a.id_shank,
            "speed_vs_angle_slope_corr_min": {k: (None if not v else round(float(np.min(v)), 4)) for k, v in a.vel.items()},
            "speed_vs_angle_slope_corr_median": {k: med(v) for k, v in a.vel.items()},
            "hip_range_deg_mean": None if not a.hip_range else round(float(np.degrees(np.mean(a.hip_range))), 2),
            "hip_mean_deg_mean": None if not a.hip_mean else round(float(np.degrees(np.mean(a.hip_mean))), 2),
            "pelvis_mean_deg_mean": None if not a.pelvis_mean else round(float(np.degrees(np.mean(a.pelvis_mean))), 2),
            "pelvis_range_deg_mean": None if not a.pelvis_range else round(float(np.degrees(np.mean(a.pelvis_range))), 2),
            "ankle_moment_range_mean": mean(a.moment_range),
            "ankle_power_range_mean": mean(a.power_range),
        }
    rss_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    out = {
        "task_id": "UM21-R01",
        "part": "fix-scope knock-on probe (read-only)",
        "source": "full.parquet of the local UM21 review bundle, streamed one stride at a time",
        "strides_read": len(seen),
        "sampling": SEED_NOTE,
        "script": "contributor_tools/probe_um21_fix_scope.py",
        "peak_rss_mib_self_reported": round(rss_mib, 1),
        "per_recording": recs,
        "ab07_i10_right_ankle": {
            "turned_back_strides": {"n": len(stretch[True].r), "ankle_range_deg_mean": None if not stretch[True].ankle_range else round(float(np.degrees(np.mean(stretch[True].ankle_range))), 2),
                                    "moment_range_mean": mean(stretch[True].moment_range), "power_range_mean": mean(stretch[True].power_range),
                                    "max_step_deg_per_sample_largest": {k: (None if not v else round(max(v), 2)) for k, v in stretch[True].max_step.items()}, "quality": stretch[True].failed,
                                    "power_vs_moment_times_speed_corr_median": med(stretch[True].r), "corr_min": None if not stretch[True].r else round(float(np.min(stretch[True].r)), 4)},
            "other_strides_same_side": {"n": len(stretch[False].r), "ankle_range_deg_mean": None if not stretch[False].ankle_range else round(float(np.degrees(np.mean(stretch[False].ankle_range))), 2),
                                        "moment_range_mean": mean(stretch[False].moment_range), "power_range_mean": mean(stretch[False].power_range),
                                        "max_step_deg_per_sample_largest": {k: (None if not v else round(max(v), 2)) for k, v in stretch[False].max_step.items()}, "quality": stretch[False].failed,
                                        "power_vs_moment_times_speed_corr_median": med(stretch[False].r), "corr_min": None if not stretch[False].r else round(float(np.min(stretch[False].r)), 4)},
        },
    }
    OUT.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}; strides {len(seen)}; peak rss {rss_mib:.1f} MiB")


if __name__ == "__main__":
    main()
