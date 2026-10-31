"""Independent verifier probe for GT23-C02 (GT23 joint-moment units).

Written by the verifying agent; it does not import or reuse the worker's
review_gt23_c02_moment_units.py. Read-only on /mnt/s/locomotion_data/Gtech_2023:
one subject/task's CSV files at a time (only needed columns kept), plus the
subject OpenSim model files (small XML). Output is one JSON file.

Run:
  OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 MPLBACKEND=Agg \
  nice -n 19 ionice -c 3 python3 verify_gt23_c02_moment_units.py OUT.json

Per leg:
  A. Fixed-lever slope: source ankle column on a mass-free N*m internal estimate
     about the talus point from the subject's own model (subtalar
     location_in_parent); implied mass = 1/slope.
  B. Free-lever fit (new): source = b1*(cop_x*Fy) + b2*Fx + b3*Fy, which is the
     same quasi-static moment with unknown talus point; 1/b1 = implied mass and
     the talus point is recovered as a check of the fit's plausibility.
  C. Plate-derived body mass from full-stride mean vertical force.
  D. Powers vs moment x velocity (rad/s) for hip, knee and ankle.
  E. ProcessedData moment vs RawData moment on matched time stamps.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import resource
import sys
import time
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

ROOT = "/mnt/s/locomotion_data/Gtech_2023"
SEED = 20261103
N_RANDOM = 4
FS = 200.0
G = 9.81
VEST_KG = 25 * 0.45359237
WORKER_SUBJECTS = {"AB01", "AB02", "AB03", "AB08", "AB10"}
README_MASS = {"AB01": 78.9, "AB02": 82.2, "AB03": 113.5, "AB05": 71.5, "AB06": 79.1, "AB07": 62.3,
               "AB08": 87.6, "AB09": 84.1, "AB10": 67.5, "AB11": 65.1, "AB12": 64.0, "AB13": 67.6}
TASKS = ("incline_walk_1", "incline_walk_2", "normal_walk_1", "weighted_walk_1")
TARGETED = [("AB03", "normal_walk_1"), ("AB03", "incline_walk_1")]  # not random: the AB03 mass question
WORKER_FILE = (f"{ROOT}/RawData/AB02/CSV_Data/incline_walk_2/Joint_Moments.csv",
               "429ad9072b7ae5d3b52468a4205b5b48f97b02327f463233bf3265f01cafa4ce")
PRIOR_FILES = [(f"{ROOT}/RawData/AB01/CSV_Data/ball_toss_1/Joint_Moments.csv", "27c936b0962fed29d2da7b651264c43169042eb0e36a764686752cba26b77033"),
               (f"{ROOT}/RawData/AB01/CSV_Data/stairs_1_10/Joint_Moments.csv", "3ff45b0433cd6df23754d8cbd2e7e151e1fa5df60fd5423cb7d8e19e407582fb")]

reads: list[dict] = []


def rss_mib() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def read(path: str, cols=None) -> pd.DataFrame:
    st0 = os.stat(path)
    raw = open(path, "rb").read()
    reads.append({"path": path, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "mtime_ns": st0.st_mtime_ns})
    df = pd.read_csv(io.BytesIO(raw), usecols=cols)
    del raw
    return df


def model_info(path: str) -> dict:
    raw = open(path, "rb").read()
    reads.append({"path": path, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    root = ET.fromstring(raw)
    total = 0.0
    sub = {}
    for body in root.iter("Body"):
        m = body.find("mass")
        if m is not None:
            total += float(m.text)
        for j in body.iter("CustomJoint"):
            if j.get("name", "").startswith("subtalar_"):
                loc = [float(v) for v in j.find("location_in_parent").text.split()]
                ori = [float(v) for v in j.find("orientation_in_parent").text.split()]
                sub[j.get("name")[-1]] = {"location_in_parent": loc, "orientation_in_parent": ori}
    return {"model_mass_kg": round(total, 3), "subtalar": sub}


def runs(mask):
    d = np.diff(np.r_[0, mask.astype(np.int8), 0])
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)))


def stances(fv):
    out = []
    for a, b in runs(np.nan_to_num(fv) > 100.0):
        if a == 0 or b >= len(fv) or not (0.25 <= (b - a) / FS <= 2.5):
            continue
        out.append((a, b))
    return out


def analyse(subj: str, task: str) -> dict:
    d = f"{ROOT}/RawData/{subj}/CSV_Data/{task}"
    statics = pd.read_csv(f"{ROOT}/RawData/{subj}/Models/Statics.csv")
    srow = statics[statics["trial"] == task]
    static = int(srow["static"].iloc[0]) if len(srow) else None
    mpath = f"{ROOT}/RawData/{subj}/Models/{subj}-Scaled{static}.osim"
    minfo = model_info(mpath) if static is not None and os.path.exists(mpath) else {}
    ins = read(f"{d}/Virtual_Insoles.csv")
    grf = read(f"{d}/GroundFrame_GRFs.csv", cols=["time", "RForceY_Vertical", "LForceY_Vertical"])
    mom = read(f"{d}/Joint_Moments.csv", cols=["time", "hip_flexion_r_moment", "hip_flexion_l_moment", "knee_angle_r_moment",
                                                 "knee_angle_l_moment", "ankle_angle_r_moment", "ankle_angle_l_moment"])
    pw = read(f"{d}/Joint_Powers.csv", cols=["time", "hip_flexion_power_r", "hip_flexion_power_l", "knee_power_r", "knee_power_l",
                                               "ankle_power_r", "ankle_power_l"])
    vel = read(f"{d}/Joint_Velocities.csv", cols=["time", "hip_flexion_velocity_r", "hip_flexion_velocity_l", "knee_velocity_r",
                                                    "knee_velocity_l", "ankle_velocity_r", "ankle_velocity_l"])
    n = len(ins)
    tr = {"subject": subj, "task": task, "readme_mass_kg": README_MASS[subj], "static": static, "model_file": os.path.basename(mpath),
          "model": minfo, "rows": {"ins": n, "grf": len(grf), "mom": len(mom), "pw": len(pw), "vel": len(vel)},
          "time_equal": bool(all(len(x) == n and np.allclose(x["time"].to_numpy(), ins["time"].to_numpy()) for x in (grf, mom, pw, vel)))}
    weighted = task.startswith("weighted")
    tr["sides"] = []
    for s, S in (("l", "L"), ("r", "R")):
        fv, fap, cap = ins[f"{S}VerticalF"].to_numpy(), ins[f"{S}ShearF_AP"].to_numpy(), ins[f"{S}COP_AP"].to_numpy()
        msrc = mom[f"ankle_angle_{s}_moment"].to_numpy()
        st = stances(fv)
        leg = {"side": s, "stances": len(st)}
        if len(st) < 5 or not np.isfinite(msrc).any():
            leg["note"] = "fewer than 5 stances or no finite ankle moment"
            tr["sides"].append(leg)
            continue
        win = np.zeros(n, bool)
        wide = np.zeros(n, bool)
        fwd = 0
        for a, b in st:
            L = b - a
            win[a + int(0.4 * L): a + int(0.9 * L)] = True
            wide[a + int(0.2 * L): a + int(0.9 * L)] = True
            fwd += int(cap[a + int(0.85 * L)] > cap[a + int(0.15 * L)])
        ok = win & np.isfinite(msrc) & np.isfinite(cap) & np.isfinite(fap)
        okw = wide & np.isfinite(msrc) & np.isfinite(cap) & np.isfinite(fap)
        leg["stances_cop_forward"] = fwd
        sub = minfo.get("subtalar", {}).get(s)
        ax, ay = (-sub["location_in_parent"][0], -sub["location_in_parent"][1]) if sub else (0.04877, 0.04195)
        leg["talus_point_in_calcn_m"] = [round(ax, 5), round(ay, 5)]
        est_nm = -((cap - ax) * fv + ay * fap)  # internal, toes-up positive, N*m
        k = float(np.dot(est_nm[ok], msrc[ok]) / np.dot(est_nm[ok], est_nm[ok]))
        leg["fixed_lever"] = {"slope": round(k, 5), "implied_mass_kg": round(1.0 / k, 2), "corr": round(float(np.corrcoef(est_nm[ok], msrc[ok])[0, 1]), 4),
                              "late_min_source": round(float(np.nanmin(msrc[ok])), 3), "late_min_est_Nm": round(float(np.nanmin(est_nm[ok])), 1)}
        X = np.c_[-cap[okw] * fv[okw], -fap[okw], fv[okw]]
        b, *_ = np.linalg.lstsq(X, msrc[okw], rcond=None)
        pred = X @ b
        leg["free_lever"] = {"implied_mass_kg": round(1.0 / b[0], 2), "talus_x_m": round(b[2] / b[0], 4), "talus_y_m": round(b[1] / b[0], 4),
                             "r2": round(1 - float(np.sum((msrc[okw] - pred) ** 2) / np.sum((msrc[okw] - msrc[okw].mean()) ** 2)), 4)}
        # plate mass: full stride mean of this leg's vertical force (heel strike to heel strike)
        gv = grf[f"{S}ForceY_Vertical"].to_numpy()
        hs = [a for a, _ in st]
        means = [np.nanmean(gv[hs[i]:hs[i + 1]]) for i in range(len(hs) - 1) if (hs[i + 1] - hs[i]) / FS < 2.5]
        pm = 2 * float(np.median(means)) / G
        leg["plate_mass_kg"] = round(pm, 2)
        leg["plate_mass_minus_vest_kg"] = round(pm - (VEST_KG if weighted else 0.0), 2)
        leg["insole_vs_plate_vertical_max_abs_diff_N"] = None
        # powers
        pr = {}
        for j_m, j_p, j_v in (("hip_flexion", "hip_flexion_power", "hip_flexion_velocity"), ("knee_angle", "knee_power", "knee_velocity"),
                              ("ankle_angle", "ankle_power", "ankle_velocity")):
            m_ = mom[f"{j_m}_{s}_moment"].to_numpy()
            p_ = pw[f"{j_p}_{s}"].to_numpy()
            prod = m_ * np.radians(vel[f"{j_v}_{s}"].to_numpy())
            o = np.isfinite(p_) & np.isfinite(prod)
            pr[j_m] = {"slope_power_on_moment_x_rad_s": round(float(np.dot(prod[o], p_[o]) / np.dot(prod[o], prod[o])), 4),
                       "corr": round(float(np.corrcoef(prod[o], p_[o])[0, 1]), 4)}
            pr[j_m]["moment_p1_p99"] = [round(float(np.nanpercentile(m_, 1)), 3), round(float(np.nanpercentile(m_, 99)), 3)]
        leg["power_vs_moment_velocity"] = pr
        tr["sides"].append(leg)
    del ins, grf, pw, vel
    # ProcessedData vs RawData moment (first matching sub-task folder)
    pdir = f"{ROOT}/ProcessedData/{subj}"
    subs = sorted(x for x in os.listdir(pdir) if x.startswith(task.rsplit("_", 1)[0] + "_")) if os.path.isdir(pdir) else []
    if subs:
        sd = subs[0]
        pm_ = read(f"{pdir}/{sd}/{subj}_{sd}_moment.csv", cols=["time", "ankle_angle_l_moment", "knee_angle_l_moment", "hip_flexion_l_moment"])
        idx = np.searchsorted(mom["time"].to_numpy(), pm_["time"].to_numpy())
        idx = np.clip(idx, 0, len(mom) - 1)
        tmatch = np.abs(mom["time"].to_numpy()[idx] - pm_["time"].to_numpy()) < 1e-6
        cmp = {"processed_folder": sd, "rows": len(pm_), "time_matched": int(tmatch.sum())}
        for c in ("ankle_angle_l_moment", "knee_angle_l_moment", "hip_flexion_l_moment"):
            a_ = pm_[c].to_numpy()[tmatch]
            r_ = mom[c].to_numpy()[idx[tmatch]]
            o = np.isfinite(a_) & np.isfinite(r_)
            cmp[c] = {"finite": int(o.sum()), "max_abs_diff": float(np.max(np.abs(a_[o] - r_[o]))) if o.any() else None}
        tr["processed_vs_raw"] = cmp
        del pm_
    del mom
    return tr


def main(out_path: str) -> None:
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    pool = sorted(s for s in README_MASS if s not in WORKER_SUBJECTS)
    order = [pool[i] for i in rng.permutation(len(pool))]
    out = {"seed": SEED, "pool": pool, "draw_order": order, "trials": [], "redraws": []}
    picked = 0
    for subj in order:
        if picked >= N_RANDOM:
            break
        avail = [t for t in TASKS if os.path.isdir(f"{ROOT}/RawData/{subj}/CSV_Data/{t}")]
        task = avail[int(rng.integers(len(avail)))]
        tr = analyse(subj, task)
        tr["selection"] = "random"
        if not any("fixed_lever" in s for s in tr["sides"]):
            out["redraws"].append(f"{subj}/{task}: no leg with 5 stances")
            continue
        out["trials"].append(tr)
        picked += 1
        print(subj, task, f"rss {rss_mib():.1f} MiB {time.time() - t0:.1f} s", flush=True)
    for subj, task in TARGETED:
        tr = analyse(subj, task)
        tr["selection"] = "targeted (AB03 mass question)"
        out["trials"].append(tr)
        print(subj, task, f"rss {rss_mib():.1f} MiB {time.time() - t0:.1f} s", flush=True)
    # every model in AB03's folder
    out["ab03_models"] = {f: model_info(f"{ROOT}/RawData/AB03/Models/{f}") for f in sorted(os.listdir(f"{ROOT}/RawData/AB03/Models")) if f.endswith(".osim")}
    # source unchanged
    chk = []
    for p, want in [WORKER_FILE] + PRIOR_FILES:
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        chk.append({"path": p, "sha256": h, "expected": want, "match": h == want})
    after = []
    for r in reads:
        if "mtime_ns" in r:
            after.append(os.stat(r["path"]).st_mtime_ns == r["mtime_ns"])
    out["source_unchanged"] = {"rehash": chk, "mtime_unchanged_after_read": [int(sum(after)), len(after)]}
    out["files_read"] = reads
    out["elapsed_s"] = round(time.time() - t0, 1)
    out["peak_rss_mib"] = round(rss_mib(), 1)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=1)
    print("peak rss", out["peak_rss_mib"])


if __name__ == "__main__":
    main(sys.argv[1])
