"""Independent verifier probe for GT24-C02 (GT24 ankle sign).

Written by the verifying agent; it does not import or reuse the worker's
review_gt24_c02_ankle_sign.py. Read-only: members of the publisher Parsed zips
are read one at a time into memory (nothing extracted, nothing written next to
the source). Output is one JSON file given on the command line.

Run (single worker, low priority):
  OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 MPLBACKEND=Agg \
  nice -n 19 ionice -c 3 python3 verify_gt24_c02_ankle_sign.py OUT.json

Tests per leg (all on a fresh seed, subjects disjoint from the worker's draw):
  1. Frame: insole (calcn) stance force up; CoP moves heel to toe.
  2. Lever arm: source ankle moment vs an internal dorsiflexion-positive
     estimate from calcn-frame force and CoP about a generic talus point.
  3. Foot-pitch chain (new, kinematic, moment-free): the calcn pitch relative to
     the lab, from the same force vector seen in the lab and calcn frames, is
     regressed on hip_flexion, knee_angle and ankle_angle. A dorsiflexion-positive
     ankle (rotation about the same +z as hip flexion and knee extension) gives an
     ankle coefficient near +1; plantarflexion-positive gives near -1.
  4. Push-off work (70-100 % stance) on level/uphill/weighted walking.
  5. Angle change from 70 % stance to toe-off.
  6. Toe walk vs heel walk stance medians with measured CoP.
  7. Exo encoders vs OpenSim hip/knee.
  8. Plate-derived body mass vs README mass (force units and direction).
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
import zipfile

import numpy as np
import pandas as pd

ROOT = "/mnt/s/locomotion_data/GaTech_2024_TaskAgnostic"
SEED = 20261103
N_SUBJECTS = 5
FS = 200.0
G = 9.81
WORKER_PEOPLE = {"BT10", "BT02", "BT07", "BT24", "BT20", "BT11"}  # worker's seed-20261030 draw
TALUS = (0.04877, 0.04195)  # generic gait2392 talus origin in calcn (m)
GRID_X = (0.0, 0.05, 0.10)
GRID_Y = (0.0, 0.04, 0.08)
VEST_KG = 25 * 0.45359237

# README "w/ exo" first-day masses (readme.txt SUBJECT MASS section).
MASS = {
    "Phase1And2": {"BT01": 87.02, "BT02": 79.09, "BT03": 101.52, "BT04": 106.04, "BT06": 85.78,
                   "BT07": 70.61, "BT08": 75.67, "BT09": 88.97, "BT10": 100.11, "BT11": 56.98,
                   "BT12": 84.62, "BT13": 96.74, "BT14": 74.35, "BT15": 65.87, "BT16": 72.03,
                   "BT17": 67.36},
    "Phase3": {"BT01": 84.28, "BT02": 79.10, "BT13": 96.03, "BT18": 74.96, "BT19": 76.84,
               "BT20": 62.50, "BT21": 65.86, "BT22": 84.27, "BT23": 74.24, "BT24": 84.84},
}
WALK = re.compile(r"^(normal_walk|incline_walk|weighted_walk)_\d+(_\d+)?_(0-6|1-2|1-8|2-0|2-5|up5|up10|25lbs)_(on|off)$")

# Files hashed by earlier audits, re-hashed here to show the source is unchanged.
PILOT_PREFIX = ("Phase1And2", "BT01_normal_walk_1_0-6_on_angle_filt.csv", 56138,
                "eabfbfe2db517229284e6b5f2c3c62342e1d5ea1b297b8eb440632b1848d5c6b")

reads: list[dict] = []


def rss_mib() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def read(z: zipfile.ZipFile, zipname: str, member: str, cols=None) -> pd.DataFrame:
    raw = z.read(member)
    reads.append({"zip": zipname, "member": member, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    df = pd.read_csv(io.BytesIO(raw), usecols=cols)
    del raw
    return df


def runs(mask: np.ndarray) -> list[tuple[int, int]]:
    d = np.diff(np.r_[0, mask.astype(np.int8), 0])
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)))  # [start, stop)


def stances(fy: np.ndarray, bw: float) -> list[tuple[int, int]]:
    out = []
    for a, b in runs(np.nan_to_num(fy) > 0.05 * bw):
        if a == 0 or b >= len(fy):
            continue
        if not (0.25 <= (b - a) / FS <= 2.5):
            continue
        out.append((a, b))
    return out


def lever_pred(cx, fx, fy, mass, ax, ay):
    m_ext = (cx - ax) * fy + ay * fx  # (r x F)_z, r = (cop_x - ax, -ay)
    return -m_ext / mass  # internal moment on the foot, +z (toes up) positive


def slope0(y, x):
    ok = np.isfinite(x) & np.isfinite(y)
    return float(np.dot(x[ok], y[ok]) / np.dot(x[ok], x[ok])), float(np.corrcoef(x[ok], y[ok])[0, 1]), int(ok.sum())


def member(names, subj, cond, kind):
    m = f"Parsed/{subj}/{cond}/{subj}_{cond}_{kind}.csv"
    return m if m in names else None


def leg_main(side, ins, grf, ang, mom, bio, pw, bw, mass, diagnostic):
    s = side
    fx, fy, cx = ins[f"insole_{s}_force_x"].to_numpy(), ins[f"insole_{s}_force_y"].to_numpy(), ins[f"insole_{s}_cop_x"].to_numpy()
    fz = ins[f"insole_{s}_force_z"].to_numpy()
    lx, ly, lz = (grf[f"fp_{s}_force_{c}"].to_numpy() for c in "xyz")
    a_deg = ang[f"ankle_angle_{s}"].to_numpy()
    hip = ang[f"hip_flexion_{s}"].to_numpy()
    knee = ang[f"knee_angle_{s}"].to_numpy()
    m_src = mom[f"ankle_angle_{s}_moment"].to_numpy()
    st = stances(fy, bw)
    res = {"side": s, "stances": len(st)}
    if len(st) < 3:
        return res
    norm_diff = np.nanmax(np.abs(np.sqrt(fx**2 + fy**2 + fz**2) - np.sqrt(lx**2 + ly**2 + lz**2)))
    res["insole_vs_plate_force_norm_max_abs_diff_N"] = float(norm_diff)
    res["stance_fy_median_N"] = float(np.median([np.median(fy[a:b]) for a, b in st]))
    fwd = 0
    for a, b in st:
        n = b - a
        i1, i2 = a + int(0.15 * n), a + int(0.85 * n)
        fwd += int(cx[i2] > cx[i1])
    res["stances_cop_moves_forward"] = fwd
    # lever arm
    pred = lever_pred(cx, fx, fy, mass, *TALUS)
    win = np.zeros(len(fy), bool)
    same = 0
    finite_st = 0
    for a, b in st:
        n = b - a
        w = slice(a + int(0.4 * n), a + int(0.9 * n))
        if np.all(np.isfinite(m_src[w])):
            win[w] = True
            finite_st += 1
            same += int(np.sign(np.mean(m_src[w])) == np.sign(np.mean(pred[w])))
    res["stances_finite_moment"] = finite_st
    if finite_st >= 3:
        k, r, n = slope0(m_src[win], pred[win])
        res["lever_slope_source_on_df_internal_pred"] = round(k, 3)
        res["lever_corr"] = round(r, 4)
        res["stances_same_sign"] = same
        grid = []
        for ax in GRID_X:
            for ay in GRID_Y:
                grid.append(round(slope0(m_src[win], lever_pred(cx, fx, fy, mass, ax, ay)[win])[0], 3))
        res["lever_grid_slopes"] = grid
        # alternative: lab-frame shear sign flipped / CoP-only (ay = 0) variants
        res["late_stance_source_min_Nm_kg"] = round(float(np.nanmin(m_src[win])), 3)
        bdiff = np.nanmax(np.abs(m_src[win] - bio[f"ankle_angle_{s}_moment"].to_numpy()[win]))
        res["ankle_net_minus_bio_max_abs"] = float(bdiff)
    # foot pitch chain
    good = np.zeros(len(fy), bool)
    mid = np.zeros(len(fy), bool)
    for a, b in st:
        n = b - a
        seg = np.arange(a, b)
        good[seg[fy[seg] > 0.2 * bw]] = True
        mid[a + int(0.3 * n): a + int(0.6 * n)] = True
    sel_s = mid & good
    # Shear correlation was tried first and is unreliable (foot pitch and slope
    # leak vertical force into calcn x); kept only as a record.
    res["lab_x_vs_calcn_x_shear_corr_unused"] = round(float(np.corrcoef(fx[sel_s], lx[sel_s])[0, 1]), 3)
    # Lab forward from treadmill CoP: the stance foot is carried backward by the
    # belt (about speed x stance time, larger than the 0.1-0.2 m heel-to-toe
    # CoP travel), so lab CoP x decreases over stance if lab +x is forward.
    lcx, lcz = grf[f"fp_{s}_cop_x"].to_numpy(), grf[f"fp_{s}_cop_z"].to_numpy()
    dlx = [lcx[a + int(0.85 * (b - a))] - lcx[a + int(0.15 * (b - a))] for a, b in st]
    dlz = [lcz[a + int(0.85 * (b - a))] - lcz[a + int(0.15 * (b - a))] for a, b in st]
    # The lab CoP travels along z, not x (first run showed |dz| ~ 0.3-0.5 m,
    # |dx| < 0.03 m), so the lab fore-aft axis is +/- z; pick the axis with the
    # larger travel and its sign.
    use_z = abs(np.median(dlz)) > abs(np.median(dlx))
    lab_ap = lz if use_z else lx
    sgn = -float(np.sign(np.median(dlz if use_z else dlx)))
    res["lab_cop_stance_travel_median_m"] = {"x": round(float(np.median(dlx)), 3), "z": round(float(np.median(dlz)), 3)}
    res["lab_fore_aft_axis"] = ("+z" if sgn > 0 else "-z") if use_z else ("+x" if sgn > 0 else "-x")
    theta = np.degrees(np.arctan2(fx, fy) - np.arctan2(sgn * lab_ap, ly))
    theta = (theta + 180.0) % 360.0 - 180.0
    ok = good & np.isfinite(theta) & np.isfinite(a_deg) & np.isfinite(hip) & np.isfinite(knee)
    X = np.c_[np.ones(ok.sum()), hip[ok], knee[ok], a_deg[ok]]
    coef, *_ = np.linalg.lstsq(X, theta[ok], rcond=None)
    res["pitch_free_regression"] = {"hip": round(float(coef[1]), 3), "knee": round(float(coef[2]), 3), "ankle": round(float(coef[3]), 3)}
    resid = theta[ok] - hip[ok] - knee[ok]
    for sa, key in ((1.0, "df_positive"), (-1.0, "pf_positive")):
        r_ = resid - sa * a_deg[ok]
        res.setdefault("pitch_chain_residual_sd_deg", {})[key] = round(float(np.std(r_ - r_.mean())), 2)
    kk = np.polyfit(a_deg[ok], resid, 1)[0]
    res["pitch_minus_hip_knee_slope_on_ankle"] = round(float(kk), 3)
    res["pitch_range_deg"] = [round(float(np.percentile(theta[ok], 2)), 1), round(float(np.percentile(theta[ok], 98)), 1)]
    # power / posture
    a_rad = np.radians(a_deg)
    own_p = m_src * np.gradient(a_rad, 1.0 / FS)
    pub_p = pw[f"ankle_angle_{s}_power"].to_numpy()
    wp, wo, dang = [], [], []
    for a, b in st:
        n = b - a
        w = slice(a + int(0.7 * n), b)
        if np.all(np.isfinite(pub_p[w])) and np.all(np.isfinite(own_p[w])):
            wp.append(float(np.sum(pub_p[w]) / FS))
            wo.append(float(np.sum(own_p[w]) / FS))
        dang.append(float(a_deg[b - 1] - a_deg[a + int(0.7 * n)]))
    res["diagnostic_for_work"] = diagnostic
    res["pushoff_work_pub_J_kg"] = {"median": round(float(np.median(wp)), 4) if wp else None, "positive": int(np.sum(np.array(wp) > 0)), "n": len(wp)}
    res["pushoff_work_own_J_kg"] = {"median": round(float(np.median(wo)), 4) if wo else None, "positive": int(np.sum(np.array(wo) > 0)), "n": len(wo)}
    res["angle_change_70pct_to_toeoff_deg"] = {"median": round(float(np.median(dang)), 2), "negative": int(np.sum(np.array(dang) < 0)), "n": len(dang)}
    return res


def main(out_path: str) -> None:
    t0 = time.time()
    zips = {ph: zipfile.ZipFile(f"{ROOT}/{ph}_Parsed.zip") for ph in ("Phase1And2", "Phase3")}
    zstat0 = {ph: [os.stat(z.filename).st_size, os.stat(z.filename).st_mtime_ns] for ph, z in zips.items()}
    names = {ph: set(z.namelist()) for ph, z in zips.items()}
    conds = {}
    for ph, ns in names.items():
        for n in ns:
            p = n.split("/")
            if len(p) == 4 and p[0] == "Parsed" and p[3]:
                conds.setdefault((ph, p[1]), set()).add(p[2])
    pool = sorted(k for k in conds if k[1] not in WORKER_PEOPLE and k != ("Phase1And2", "BT01") and k[1] in MASS[k[0]])
    rng = np.random.default_rng(SEED)
    order = [pool[i] for i in rng.permutation(len(pool))]
    out = {"seed": SEED, "pool": ["/".join(k) for k in pool], "draw_order": ["/".join(k) for k in order], "trials": [], "heel_toe": [], "redraws": []}
    for ph, subj in order:
        if len(out["trials"]) >= N_SUBJECTS:
            break
        z = zips[ph]
        cands = sorted(c for c in conds[(ph, subj)] if WALK.match(c))
        if not cands:
            out["redraws"].append(f"{ph}/{subj}: no walking condition")
            continue
        cond = cands[int(rng.integers(len(cands)))]
        need = {k: member(names[ph], subj, cond, k) for k in ("insole_sim", "grf", "angle_filt", "moment_filt", "moment_filt_bio", "power", "exo")}
        if any(v is None for v in need.values()):
            out["redraws"].append(f"{ph}/{subj}/{cond}: missing {[k for k, v in need.items() if v is None]}")
            continue
        mass = MASS[ph][subj]
        ins = read(z, ph, need["insole_sim"])
        grf = read(z, ph, need["grf"])
        ang = read(z, ph, need["angle_filt"])
        mom = read(z, ph, need["moment_filt"])
        bio = read(z, ph, need["moment_filt_bio"])
        pw = read(z, ph, need["power"])
        exo = read(z, ph, need["exo"], cols=["time", "hip_angle_l", "knee_angle_l", "hip_angle_r", "knee_angle_r"])
        lens = {k: len(v) for k, v in dict(ins=ins, grf=grf, ang=ang, mom=mom, bio=bio, pw=pw, exo=exo).items()}
        same_time = all(np.allclose(ins["time"].to_numpy(), d["time"].to_numpy()) for d in (grf, ang, mom, pw) if len(d) == len(ins))
        weighted = "25lbs" in cond
        load_kg = mass + (VEST_KG if weighted else 0.0)
        bw = load_kg * G
        diagnostic = not ("down" in cond)
        tr = {"phase": ph, "subject": subj, "condition": cond, "readme_mass_w_exo_kg": mass, "added_load_kg": round(load_kg - mass, 2),
              "row_counts": lens, "time_columns_equal": bool(same_time)}
        ftot = grf["fp_l_force_y"].to_numpy() + grf["fp_r_force_y"].to_numpy()
        tr["plate_mean_vertical_over_g_kg"] = round(float(np.nanmean(ftot) / G), 2)
        tr["plate_mass_over_expected"] = round(float(np.nanmean(ftot) / G / load_kg), 3)
        tr["sides"] = [leg_main(s, ins, grf, ang, mom, bio, pw, bw, mass, diagnostic) for s in ("l", "r")]
        ex = {}
        for s in ("l", "r"):
            te = exo["time"].to_numpy()
            for j_exo, j_os in (("knee_angle", "knee_angle"), ("hip_angle", "hip_flexion")):
                e = np.interp(ang["time"].to_numpy(), te, exo[f"{j_exo}_{s}"].to_numpy())
                o = ang[f"{j_os}_{s}"].to_numpy()
                ok = np.isfinite(e) & np.isfinite(o)
                ex[f"{j_exo}_{s}_corr_with_{j_os}"] = round(float(np.corrcoef(e[ok], o[ok])[0, 1]), 3)
        tr["exo_encoder_corr"] = ex
        out["trials"].append(tr)
        del ins, grf, ang, mom, bio, pw, exo
        # heel / toe walking for the same subject
        ht = {}
        for kind in ("heel-walk", "toe-walk"):
            cs = sorted(c for c in conds[(ph, subj)] if kind in c)
            if not cs:
                continue
            c = cs[0]
            m1, m2 = member(names[ph], subj, c, "insole_sim"), member(names[ph], subj, c, "angle_filt")
            if not (m1 and m2):
                continue
            i2 = read(z, ph, m1)
            a2 = read(z, ph, m2, cols=["time", "ankle_angle_l", "ankle_angle_r"])
            ht[kind] = {"condition": c}
            for s in ("l", "r"):
                fy = i2[f"insole_{s}_force_y"].to_numpy()
                stc = stances(fy, mass * G)
                idx = np.concatenate([np.arange(a, b) for a, b in stc]) if stc else np.array([], int)
                ht[kind][s] = {"stances": len(stc),
                               "cop_x_median_m": float(np.median(i2[f"insole_{s}_cop_x"].to_numpy()[idx])) if len(idx) else None,
                               "ankle_median_deg": float(np.median(a2[f"ankle_angle_{s}"].to_numpy()[idx])) if len(idx) else None}
            del i2, a2
        if "heel-walk" in ht and "toe-walk" in ht:
            for s in ("l", "r"):
                h, t = ht["heel-walk"][s], ht["toe-walk"][s]
                if h["stances"] >= 3 and t["stances"] >= 3:
                    out["heel_toe"].append({"subject": f"{ph}/{subj}", "side": s, "cop_toe_minus_heel_m": round(t["cop_x_median_m"] - h["cop_x_median_m"], 4),
                                            "ankle_toe_minus_heel_deg": round(t["ankle_median_deg"] - h["ankle_median_deg"], 2),
                                            "stances_heel_toe": [h["stances"], t["stances"]]})
        print(f"{ph}/{subj} {cond} done, rss {rss_mib():.1f} MiB, {time.time() - t0:.1f} s", flush=True)
    # source-unchanged checks
    chk = {}
    ph, base, nbytes, want = PILOT_PREFIX
    cand = [n for n in names[ph] if n.endswith("/" + base)]
    if len(cand) == 1:
        with zips[ph].open(cand[0]) as f:
            pre = f.read(nbytes)
        chk["pilot_prefix"] = {"member": cand[0], "bytes": nbytes, "sha256": hashlib.sha256(pre).hexdigest(), "expected": want,
                               "match": hashlib.sha256(pre).hexdigest() == want}
    else:
        chk["pilot_prefix"] = {"member_candidates": cand}
    wa = json.load(open("docs/quality/audits/gt24-c02-ankle-sign.json"))
    wm = [m for m in wa["members_read"] if m["member"].endswith("BT02_normal_walk_1_1_2-0_on_grf.csv")][0]
    raw = zips["Phase3"].read(wm["member"])
    chk["worker_member_rehash"] = {"member": wm["member"], "sha256": hashlib.sha256(raw).hexdigest(), "expected": wm["sha256"],
                                   "match": hashlib.sha256(raw).hexdigest() == wm["sha256"]}
    del raw
    zstat1 = {ph: [os.stat(z.filename).st_size, os.stat(z.filename).st_mtime_ns] for ph, z in zips.items()}
    chk["zip_size_mtime_before"] = zstat0
    chk["zip_size_mtime_after"] = zstat1
    chk["zip_matches_worker_record"] = {ph: zstat0[ph] == [wa["source_zips"][ph]["bytes"], wa["source_zips"][ph]["mtime_ns"]] for ph in zstat0}
    rb = open(f"{ROOT}/readme.txt", "rb").read()
    chk["readme_sha256"] = hashlib.sha256(rb).hexdigest()
    chk["readme_matches_prior"] = chk["readme_sha256"] == "e896c6b424c45f50f261ade2e40c5f5832065fbcd745c593b7cd72fdeb84026f"
    out["source_unchanged"] = chk
    out["members_read"] = reads
    out["elapsed_s"] = round(time.time() - t0, 1)
    out["peak_rss_mib"] = round(rss_mib(), 1)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=1)
    print("peak rss", out["peak_rss_mib"])


if __name__ == "__main__":
    main(sys.argv[1])
