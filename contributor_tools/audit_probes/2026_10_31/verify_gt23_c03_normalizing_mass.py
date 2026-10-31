"""Independent verifier probe for GT23-C03 (GT23 normalizing mass).

Written by the verifying agent; it does not import or reuse the worker's
probe_gt23_c03_normalizing_mass.py. Read-only probe under the AGENTS.md
exception: one subject/trial in memory at a time, nothing written next to the
source, output JSON path given on the command line (scratchpad).

Run:
  OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 MPLBACKEND=Agg \
  nice -n 19 ionice -c 3 python3 verify_gt23_c03_normalizing_mass.py OUT.json

Part A (local MotionFile_EH re-run vs published normal_walk_1):
  - per column, slope of .sto N*m on published, correlation, and the max
    residual for every README / model candidate mass (exactness test);
  - is the .sto physical N*m? slope of .sto ankle on a mass-free force-plate
    lever-arm ankle moment (Virtual_Insoles) -- if the .sto were published x a
    wrong mass, this slope would be (that mass / true divisor), not about 1;
  - which model mass the ID used: mean pelvis_ty residual + mean measured
    vertical GRF, divided by g;
  - whether the .sto IK equals published Joint_Angle.
Part B (lever-arm divisor, mass-free): implied divisor = 1 / slope of the
  published ankle column on the lever-arm N*m estimate, for chosen trials.
"""
from __future__ import annotations

import hashlib
import json
import os
import resource
import sys
import time
import zlib

import numpy as np
import pandas as pd

ROOT = "/mnt/s/locomotion_data/Gtech_2023/RawData"
ZIPDIR = ("converted_datasets/reconversion_v2/swarm_backlog_20261021/"
          "gt23_publisher_source_review_20261021/raw_zip_directory.json")
FS, G = 200.0, 9.81
TALUS = (0.04877, 0.04195)  # subtalar location_in_parent negated; equal in every model used (C02 verify)
README = {"AB01": 78.9, "AB02": 82.2, "AB03": 113.5, "AB05": 71.5, "AB06": 79.1, "AB07": 62.3,
          "AB08": 87.6, "AB09": 84.1, "AB10": 67.5, "AB11": 65.1, "AB12": 64.0, "AB13": 67.6}
MODEL = {"AB01": 78.85, "AB02": 82.179, "AB03": 113.517, "AB05": 71.541, "AB06": 79.111, "AB07": 62.261,
         "AB08": 87.608, "AB09": 84.099, "AB10": 67.524, "AB11": 65.08, "AB12": 64.032, "AB13": 67.574}
STO_SUBJECTS = ["AB01", "AB05", "AB06", "AB08", "AB11"]
LEVER_TRIALS = [("AB01", "normal_walk_1"), ("AB05", "normal_walk_1"), ("AB05", "incline_walk_2"),
                ("AB06", "normal_walk_1"), ("AB08", "normal_walk_1"), ("AB11", "normal_walk_1"),
                ("AB13", "normal_walk_1"), ("AB13", "incline_walk_1")]

reads: list[dict] = []
crc_index: dict[str, tuple[int, int]] = {}


def rss():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def raw(path):
    b = open(path, "rb").read()
    rel = os.path.relpath(path, ROOT)
    pub = crc_index.get(rel)
    reads.append({"path": path, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(),
                  "mtime_ns": os.stat(path).st_mtime_ns,
                  "publisher_crc32_size_match": None if pub is None else (zlib.crc32(b) == pub[0] and len(b) == pub[1])})
    return b


def csv(path, cols=None):
    import io
    return pd.read_csv(io.BytesIO(raw(path)), usecols=cols)


def opensim_table(path, cols):
    import io
    b = raw(path)
    head = b[:4000].decode(errors="replace").splitlines()
    k = next(i for i, l in enumerate(head) if l.strip() == "endheader")
    return pd.read_csv(io.BytesIO(b), sep=r"\s+", skiprows=k + 1, usecols=cols), head[:k + 1]


def stances(fv):
    m = np.nan_to_num(fv) > 100.0
    d = np.diff(np.r_[0, m.astype(np.int8), 0])
    out = []
    for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)):
        if a > 0 and b < len(fv) and 0.25 <= (b - a) / FS <= 2.5:
            out.append((a, b))
    return out


def lever(subj, task):
    """Mass-free internal ankle estimate (N*m, toes-up +) and 40-90 % stance mask per side."""
    ins = csv(f"{ROOT}/{subj}/CSV_Data/{task}/Virtual_Insoles.csv")
    out = {"time": ins["time"].to_numpy()}
    for s, S in (("l", "L"), ("r", "R")):
        fv, fap, cap = (ins[f"{S}{c}"].to_numpy() for c in ("VerticalF", "ShearF_AP", "COP_AP"))
        st = stances(fv)
        w = np.zeros(len(fv), bool)
        for a, b in st:
            w[a + int(0.4 * (b - a)): a + int(0.9 * (b - a))] = True
        est = -((cap - TALUS[0]) * fv + TALUS[1] * fap)
        out[s] = (est, w & np.isfinite(est), len(st))
    return out


def slope0(y, x):
    ok = np.isfinite(x) & np.isfinite(y)
    return float(np.dot(x[ok], y[ok]) / np.dot(x[ok], x[ok])), float(np.corrcoef(x[ok], y[ok])[0, 1]), int(ok.sum())


def part_a(subj):
    t0 = time.time()
    p = f"{ROOT}/{subj}/MotionFile_EH/inverse_dynamics.sto"
    if not os.path.exists(p):
        return {"subject": subj, "present": False}
    st = os.stat(p)
    cols = ["time", "pelvis_ty_force", "hip_flexion_l_moment", "knee_angle_l_moment", "ankle_angle_l_moment",
            "hip_flexion_r_moment", "knee_angle_r_moment", "ankle_angle_r_moment"]
    sto, header = opensim_table(p, cols)
    task = "normal_walk_1"
    pub = csv(f"{ROOT}/{subj}/CSV_Data/{task}/Joint_Moments.csv", cols[:1] + cols[2:])
    res = {"subject": subj, "present": True, "sto_mtime_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(st.st_mtime)),
           "header": header, "rows_sto": len(sto), "rows_published": len(pub),
           "time_end_sto": float(sto["time"].iloc[-1]), "time_end_published": float(pub["time"].iloc[-1])}
    tp = np.round(pub["time"].to_numpy(), 4)
    ts = np.round(sto["time"].to_numpy(), 4)
    common, ip, isx = np.intersect1d(tp, ts, return_indices=True)
    res["matched_rows"] = int(len(common))
    cands = {f"README {k}": v for k, v in README.items()}
    cands.update({f"model {k}": v for k, v in MODEL.items()})
    colres = {}
    for c in cols[2:]:
        y = sto[c].to_numpy()[isx]
        x = pub[c].to_numpy()[ip]
        ok = np.isfinite(x) & np.isfinite(y)
        if ok.sum() < 1000:
            continue
        k, r, n = slope0(y[ok], x[ok])
        resid = {name: float(np.max(np.abs(y[ok] - m * x[ok]))) for name, m in cands.items()}
        best = sorted(resid.items(), key=lambda kv: kv[1])[:3]
        colres[c] = {"n": n, "slope": round(k, 4), "corr": round(r, 7), "p99_abs_Nm": round(float(np.percentile(np.abs(y[ok]), 99)), 1),
                     "best_candidates_max_abs_residual_Nm": [[nm, round(v, 4)] for nm, v in best],
                     "own_readme_max_abs_residual_Nm": round(resid[f"README {subj}"], 3)}
    res["columns"] = colres
    # physical check: .sto ankle vs mass-free lever arm
    lv = lever(subj, task)
    tl = np.round(lv["time"], 4)
    phys = {}
    for s in ("l", "r"):
        est, w, nst = lv[s]
        if nst < 5:
            continue
        _, il, isx2 = np.intersect1d(tl, ts, return_indices=True)
        y = sto[f"ankle_angle_{s}_moment"].to_numpy()[isx2]
        x = est[il]
        m = w[il] & np.isfinite(y)
        if m.sum() < 1000:
            continue
        k, r, n = slope0(y[m], x[m])
        phys[s] = {"stances": nst, "slope_sto_on_lever_Nm": round(k, 4), "corr": round(r, 4)}
    res["sto_vs_lever_arm"] = phys
    # model mass used by the ID: mean residual + mean measured vertical GRF
    grf = csv(f"{ROOT}/{subj}/CSV_Data/{task}/GroundFrame_GRFs.csv", ["time", "LForceY_Vertical", "RForceY_Vertical"])
    tg = np.round(grf["time"].to_numpy(), 4)
    _, ig, isx3 = np.intersect1d(tg, ts, return_indices=True)
    fy = np.nan_to_num(grf["LForceY_Vertical"].to_numpy()[ig]) + np.nan_to_num(grf["RForceY_Vertical"].to_numpy()[ig])
    fr = sto["pelvis_ty_force"].to_numpy()[isx3]
    res["id_model_mass_from_residual_kg"] = round(float((np.mean(fr) + np.mean(fy)) / G), 2)
    res["right_plate_all_nan"] = bool(np.all(~np.isfinite(grf["RForceY_Vertical"].to_numpy())))
    res["mean_pelvis_ty_residual_N"] = round(float(np.mean(fr)), 1)
    del grf, sto, pub
    # IK in the folder vs published Joint_Angle
    ik, _ = opensim_table(f"{ROOT}/{subj}/MotionFile_EH/IK_results.mot", ["time", "ankle_angle_l", "knee_angle_l", "hip_flexion_l"])
    ja = csv(f"{ROOT}/{subj}/CSV_Data/{task}/Joint_Angle.csv", ["time", "ankle_angle_l", "knee_angle_l", "hip_flexion_l"])
    _, i1, i2 = np.intersect1d(np.round(ik["time"].to_numpy(), 4), np.round(ja["time"].to_numpy(), 4), return_indices=True)
    res["ik_vs_published_angle_max_abs_deg"] = {c: round(float(np.nanmax(np.abs(ik[c].to_numpy()[i1] - ja[c].to_numpy()[i2]))), 6)
                                               for c in ("ankle_angle_l", "knee_angle_l", "hip_flexion_l")}
    res["seconds"] = round(time.time() - t0, 1)
    return res


def part_b(subj, task):
    lv = lever(subj, task)
    pub = csv(f"{ROOT}/{subj}/CSV_Data/{task}/Joint_Moments.csv", ["time", "ankle_angle_l_moment", "ankle_angle_r_moment"])
    out = {"subject": subj, "task": task, "readme_kg": README[subj], "sides": {}}
    for s in ("l", "r"):
        est, w, nst = lv[s]
        y = pub[f"ankle_angle_{s}_moment"].to_numpy()
        m = w & np.isfinite(y)
        if nst < 5 or m.sum() < 500:
            continue
        k, r, n = slope0(y[m], est[m])
        out["sides"][s] = {"stances": nst, "implied_divisor_kg": round(1 / k, 2), "corr": round(r, 4)}
    return out


def main(out_path):
    t0 = time.time()
    for e in json.load(open(ZIPDIR)):
        if e["name"] and not e["name"].endswith("/"):
            crc_index[e["name"]] = (e["crc32"], e["uncompressed_size"])
    out = {"part_a": [], "part_b": []}
    for s in STO_SUBJECTS:
        out["part_a"].append(part_a(s))
        print("A", s, f"rss {rss():.1f}", flush=True)
    for s, t in LEVER_TRIALS:
        out["part_b"].append(part_b(s, t))
        print("B", s, t, f"rss {rss():.1f}", flush=True)
    out["mtime_unchanged"] = [sum(os.stat(r["path"]).st_mtime_ns == r["mtime_ns"] for r in reads), len(reads)]
    out["files_read"] = reads
    out["elapsed_s"] = round(time.time() - t0, 1)
    out["peak_rss_mib"] = round(rss(), 1)
    json.dump(out, open(out_path, "w"), indent=1)
    print("peak", out["peak_rss_mib"])


if __name__ == "__main__":
    main(sys.argv[1])
