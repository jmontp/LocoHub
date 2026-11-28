"""Independent verifier probe for GT23-C04 (per-trial divisor census).

Written by the verifying agent; it does not import the worker's C03/C04 probes.
The worker's audit JSON is read only as the sampling frame (trial list, class)
and for comparison. Read-only probe under the AGENTS.md exception: one trial in
memory at a time; output JSON path on the command line (scratchpad).

Run:
  OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 MPLBACKEND=Agg \
  nice -n 19 ionice -c 3 python3 verify_gt23_c04_trial_divisors.py OUT.json

Estimators (mass-free, from Virtual_Insoles in the calcn frame; implied divisor
= 1 / slope of the published ankle column on the N*m estimate):
  e1  gait: fixed generic talus point, 40-90 % of each 0.25-2.5 s stance
  e2  free: talus point fitted with the mass, all loaded samples (> 100 N)
  e3  fixed talus point, all loaded samples
Calibration: e1/e2/e3 on the 8 exact trials (divisor known from the C03 re-runs).
Split-half: e2 on the first and second half of the loaded samples (precision).
Knee power: published power vs moment x velocity, raw and with the moment
low-passed (5th-order Butterworth 6 Hz, zero lag, as the README describes
moment_filt), plus ProcessedData moment_filt x velocity.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import resource
import sys
import time

import numpy as np
import pandas as pd

ROOT = "/mnt/s/locomotion_data/Gtech_2023"
AUDIT = "docs/quality/audits/gt23-c04-trial-divisors.json"
SEED = 20261104
FS = 200.0
TALUS = (0.04877, 0.04195)
EXACT = {("AB01", "normal_walk_1"): 78.9, ("AB05", "normal_walk_1"): 78.9, ("AB06", "normal_walk_1"): 71.5,
         ("AB08", "normal_walk_1"): 62.3, ("AB09", "normal_walk_1"): 87.6, ("AB10", "normal_walk_1"): 84.1,
         ("AB12", "normal_walk_1"): 65.1, ("AB13", "normal_walk_1"): 64.0}
PLAN = {"unique-estimate": 6, "ambiguous": 5, "no-match": 2,
        ("unreliable", "non-gait family"): 6, ("unreliable", "not usable"): 1,
        ("unreliable", "curb family"): 1, ("unreliable", "ankle corr < 0.98"): 1}
KNEE_TRIALS = [("AB05", "side_shuffle_1", "side_shuffle_1"), ("AB01", "incline_walk_2", None),
               ("AB05", "meander_1", "meander_1")]
reads = []


def rss():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def csv(path, cols=None):
    b = open(path, "rb").read()
    reads.append({"path": path, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(), "mtime_ns": os.stat(path).st_mtime_ns})
    return pd.read_csv(io.BytesIO(b), usecols=cols)


def stances(fv):
    m = np.nan_to_num(fv) > 100.0
    d = np.diff(np.r_[0, m.astype(np.int8), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1))
            if a > 0 and b < len(fv) and 0.25 <= (b - a) / FS <= 2.5]


def estimators(subj, task):
    d = f"{ROOT}/RawData/{subj}/CSV_Data/{task}"
    ins = csv(f"{d}/Virtual_Insoles.csv")
    mom = csv(f"{d}/Joint_Moments.csv", ["time", "ankle_angle_l_moment", "ankle_angle_r_moment"])
    if len(mom) != len(ins) or not np.allclose(mom["time"].to_numpy(), ins["time"].to_numpy()):
        return {"error": "time bases differ"}
    Y1, X1, Y2, X2, Y3, X3 = [], [], [], [], [], []
    nst = 0
    for s, S in (("l", "L"), ("r", "R")):
        fv, fap, cap = (ins[f"{S}{c}"].to_numpy() for c in ("VerticalF", "ShearF_AP", "COP_AP"))
        y = mom[f"ankle_angle_{s}_moment"].to_numpy()
        ok = np.isfinite(fv) & np.isfinite(fap) & np.isfinite(cap) & np.isfinite(y)
        est = -((cap - TALUS[0]) * fv + TALUS[1] * fap)
        st = stances(fv)
        nst += len(st)
        w = np.zeros(len(fv), bool)
        for a, b in st:
            w[a + int(0.4 * (b - a)): a + int(0.9 * (b - a))] = True
        g = w & ok
        Y1.append(y[g]); X1.append(est[g])
        ld = ok & (np.nan_to_num(fv) > 100.0)
        Y3.append(y[ld]); X3.append(est[ld])
        Y2.append(y[ld]); X2.append(np.c_[-cap[ld] * fv[ld], -fap[ld], fv[ld]])
    out = {"stances": nst}
    y1, x1 = np.concatenate(Y1), np.concatenate(X1)
    if len(y1) > 200:
        k = np.dot(x1, y1) / np.dot(x1, x1)
        out["e1"] = {"divisor_kg": round(1 / k, 2), "corr": round(float(np.corrcoef(x1, y1)[0, 1]), 4), "n": int(len(y1))}
    y3, x3 = np.concatenate(Y3), np.concatenate(X3)
    if len(y3) > 200:
        k = np.dot(x3, y3) / np.dot(x3, x3)
        out["e3"] = {"divisor_kg": round(1 / k, 2), "corr": round(float(np.corrcoef(x3, y3)[0, 1]), 4), "n": int(len(y3))}
        y2, x2 = np.concatenate(Y2), np.vstack(X2)
        b, *_ = np.linalg.lstsq(x2, y2, rcond=None)
        pred = x2 @ b
        r2 = 1 - np.sum((y2 - pred) ** 2) / np.sum((y2 - y2.mean()) ** 2)
        half = len(y2) // 2
        hb = [np.linalg.lstsq(x2[sl], y2[sl], rcond=None)[0] for sl in (slice(0, half), slice(half, None))]
        out["e2"] = {"divisor_kg": round(1 / b[0], 2), "talus_x_m": round(b[2] / b[0], 4), "talus_y_m": round(b[1] / b[0], 4),
                     "r2": round(float(r2), 4), "n": int(len(y2)),
                     "split_half_divisor_kg": [round(1 / hb[0][0], 2), round(1 / hb[1][0], 2)]}
    return out


def butter_lp(x, fc=6.0, order=5):
    from scipy.signal import butter, filtfilt
    bb, aa = butter(order, fc / (FS / 2))
    y = x.copy()
    ok = np.isfinite(x)
    if ok.sum() > 50:
        # filter contiguous finite runs only
        d = np.diff(np.r_[0, ok.astype(np.int8), 0])
        for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)):
            if b - a > 3 * (order + 1) * 3:
                y[a:b] = filtfilt(bb, aa, x[a:b])
    return y


def ratio(p, q):
    ok = np.isfinite(p) & np.isfinite(q)
    p, q = p[ok], q[ok]
    top = np.abs(q) >= np.percentile(np.abs(q), 75)
    return {"median_ratio_top_quartile": round(float(np.median(p[top] / q[top])), 4),
            "slope": round(float(np.dot(q, p) / np.dot(q, q)), 4), "corr": round(float(np.corrcoef(q, p)[0, 1]), 5)}


def knee(subj, task, proc):
    d = f"{ROOT}/RawData/{subj}/CSV_Data/{task}"
    pw = csv(f"{d}/Joint_Powers.csv", ["time", "knee_power_l", "knee_power_r", "ankle_power_l", "ankle_power_r"])
    mo = csv(f"{d}/Joint_Moments.csv", ["time", "knee_angle_l_moment", "knee_angle_r_moment", "ankle_angle_l_moment", "ankle_angle_r_moment"])
    ve = csv(f"{d}/Joint_Velocities.csv", ["time", "knee_velocity_l", "knee_velocity_r", "ankle_velocity_l", "ankle_velocity_r"])
    out = {"subject": subj, "task": task, "raw": {}}
    for j, mj in (("knee", "knee_angle"), ("ankle", "ankle_angle")):
        for s in ("l", "r"):
            p = pw[f"{j}_power_{s}"].to_numpy()
            m = mo[f"{mj}_{s}_moment"].to_numpy()
            w = np.radians(ve[f"{j}_velocity_{s}"].to_numpy())
            if np.isfinite(p).sum() < 1000 or np.isfinite(m).sum() < 1000:
                continue
            out["raw"][f"{j}_{s}"] = {"P_vs_M_w": ratio(p, m * w), "P_vs_lp6(M)_w": ratio(p, butter_lp(m) * w),
                                      "P_vs_M_lp6(w)": ratio(p, m * butter_lp(w))}
    del pw, mo, ve
    if proc:
        pd_ = f"{ROOT}/ProcessedData/{subj}/{proc}/{subj}_{proc}"
        pp = csv(f"{pd_}_power.csv", ["time", "knee_power_l", "knee_power_r", "ankle_power_l", "ankle_power_r"])
        mf = csv(f"{pd_}_moment_filt.csv", ["time", "knee_angle_l_moment", "knee_angle_r_moment", "ankle_angle_l_moment", "ankle_angle_r_moment"])
        mr = csv(f"{pd_}_moment.csv", ["time", "knee_angle_l_moment", "knee_angle_r_moment", "ankle_angle_l_moment", "ankle_angle_r_moment"])
        vv = csv(f"{pd_}_velocity.csv")
        out["processed"] = {"velocity_columns": [c for c in vv.columns if "knee" in c or "ankle" in c][:6]}
        for j, mj in (("knee", "knee_angle"), ("ankle", "ankle_angle")):
            for s in ("l", "r"):
                vc = [c for c in vv.columns if c.startswith(f"{j}_velocity_{s}") or c == f"{mj}_{s}_velocity"]
                if not vc:
                    continue
                p = pp[f"{j}_power_{s}"].to_numpy()
                w = np.radians(vv[vc[0]].to_numpy())
                if np.isfinite(p).sum() < 500:
                    continue
                out["processed"][f"{j}_{s}"] = {"P_vs_Mraw_w": ratio(p, mr[f"{mj}_{s}_moment"].to_numpy() * w),
                                                "P_vs_Mfilt_w": ratio(p, mf[f"{mj}_{s}_moment"].to_numpy() * w)}
    return out


def main(out_path):
    t0 = time.time()
    a = json.load(open(AUDIT))
    trials = [(t["subject"], t["task"], t["census"]["cls"], t["census"].get("reason_code"), t["census"].get("lever_divisor_kg"),
               [tuple(c) for c in t["census"].get("candidates") or []], t["census"].get("divisor_kg")) for t in a["trials"]]
    rng = np.random.default_rng(SEED)
    sample = []
    for key, n in PLAN.items():
        pool = [t for t in trials if (t[2] == key if isinstance(key, str) else (t[2] == key[0] and t[3] == key[1]))]
        idx = sorted(rng.choice(len(pool), size=min(n, len(pool)), replace=False))
        sample += [pool[i] for i in idx]
    out = {"seed": SEED, "plan": {str(k): v for k, v in PLAN.items()}, "calibration": [], "sample": [], "knee": []}
    for (s, t), m in EXACT.items():
        r = estimators(s, t)
        r.update({"subject": s, "task": t, "exact_divisor_kg": m})
        out["calibration"].append(r)
        print("cal", s, t, f"{rss():.1f}", flush=True)
    for s, t, cls, reason, wdiv, cands, div in sample:
        r = estimators(s, t)
        r.update({"subject": s, "task": t, "worker_class": cls, "worker_reason": reason, "worker_lever_divisor_kg": wdiv,
                  "worker_candidates": cands, "worker_divisor_kg": div})
        out["sample"].append(r)
        print("smp", s, t, cls, f"{rss():.1f}", flush=True)
    for s, t, p in KNEE_TRIALS:
        out["knee"].append(knee(s, t, p))
        print("knee", s, t, f"{rss():.1f}", flush=True)
    out["mtime_unchanged"] = [sum(os.stat(r["path"]).st_mtime_ns == r["mtime_ns"] for r in reads), len(reads)]
    out["files_read"] = reads
    out["elapsed_s"] = round(time.time() - t0, 1)
    out["peak_rss_mib"] = round(rss(), 1)
    json.dump(out, open(out_path, "w"), indent=1)
    print("peak", out["peak_rss_mib"], "elapsed", out["elapsed_s"])


if __name__ == "__main__":
    main(sys.argv[1])
