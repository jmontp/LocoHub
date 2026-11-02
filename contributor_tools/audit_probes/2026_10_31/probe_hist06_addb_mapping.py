"""HIST-06: read-only evidence for mapping the HIST-05 AddBiomechanics frames to LocoHub names and signs.

Written by HIST-06. Read-only probe under the AGENTS.md exception: one file at a time, bounded columns
(per row group), writes only its result JSON under docs/quality/audits (exclusive create), nothing under
converted_datasets or source folders. Run alone at nice 19 / ionice idle; peak RSS is recorded.

Sections (each cites what it reads):

1. model: for every participant's dynamics_model.osim (the model the dynamics pass used, written by HIST-05
   from the B3D header), the coordinate list, the coordinate-coupler constraints, the ground_pelvis transform
   axes and the gravity vector, and a rotation-only forward-kinematics sign test: each sagittal and
   frontal/transverse hip coordinate is perturbed by +0.2 rad from the all-zero pose (+0.2 to +0.4 rad for the
   knee, whose range starts at 0) and the rotation of the child body in the ground frame is reported as a
   rotation vector (x forward, y up, z right at the zero pose, where the pelvis frame equals ground).
   Conventions used: OpenSim PhysicalOffsetFrame orientation = body-fixed X-Y-Z Euler angles; a CustomJoint
   SpatialTransform applies rotation1, rotation2, rotation3 as a body-fixed sequence about axes in the
   parent offset frame; a PinJoint rotates about the common z axis of its offset frames. SimmSpline
   functions of coupled rotations are evaluated by linear interpolation between their knots (they are small
   secondary rotations; the sign of the primary rotation does not depend on that approximation).
2. dof_order: per study, one trial (the first row group of a fixed participant) read for the 23 dofNN_pos
   columns: per-column percentiles against two hypotheses for the 23 DOF columns, H23 (model coordinates in
   model order without the two coupled knee_angle_*_beta coordinates) and H_order (the first 23 model
   coordinates). Under H_order dof10 would be knee_angle_r_beta, which the coupler makes equal to dof09.
3. heading: for all 33 participants, per trial, the pelvis anterior axis from dof00-02 (ground_pelvis:
   Rz(tilt) Rx(list) Ry(rotation), body-fixed) projected on the horizontal plane: circular mean yaw and
   resultant length; for Falisse also the mean horizontal COM velocity direction (com_vel_x/z).
4. weight: for all 33 participants, mean summed vertical contact force over frames flagged notMissingGRF,
   divided by g, against the entered mass and the dynamics-model mass (evidence for the normalization-mass
   decision; whole-trial means over steady locomotion approximate body weight).

    nice -n 19 ionice -c 3 python3 contributor_tools/audit_probes/2026_10_31/probe_hist06_addb_mapping.py \
        --root /mnt/s/locomotion_data/addbiomechanics_hist04 --out docs/quality/audits/hist06-addb-mapping-probe.json
"""
from __future__ import annotations

import os
for _k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "ARROW_NUM_THREADS"):
    os.environ.setdefault(_k, "1")
import argparse
import hashlib
import json
import math
import re
import resource
import time
from pathlib import Path

import numpy as np

G = 9.80665  # gravity magnitude in every dynamics_model.osim (<gravity>0 -9.80665 0</gravity>)
H25 = ["pelvis_tilt", "pelvis_list", "pelvis_rotation", "pelvis_tx", "pelvis_ty", "pelvis_tz",
       "hip_flexion_r", "hip_adduction_r", "hip_rotation_r", "knee_angle_r", "knee_angle_r_beta", "ankle_angle_r",
       "subtalar_angle_r", "mtp_angle_r", "hip_flexion_l", "hip_adduction_l", "hip_rotation_l", "knee_angle_l",
       "knee_angle_l_beta", "ankle_angle_l", "subtalar_angle_l", "mtp_angle_l", "lumbar_extension",
       "lumbar_bending", "lumbar_rotation"]
H23 = [c for c in H25 if not c.endswith("_beta")]
H_ORDER = H25[:23]
DOF_ORDER_TRIALS = {"fa16": "subject_4", "ta21": "s1", "ta22": "02"}  # fixed: the first participant listed per study
TEST_COORDS = {  # coordinate -> child body whose rotation is reported
    "pelvis_tilt": "pelvis", "hip_flexion_r": "femur_r", "hip_flexion_l": "femur_l",
    "hip_adduction_r": "femur_r", "hip_adduction_l": "femur_l", "hip_rotation_r": "femur_r",
    "hip_rotation_l": "femur_l", "knee_angle_r": "tibia_r", "knee_angle_l": "tibia_l",
    "ankle_angle_r": "talus_r", "ankle_angle_l": "talus_l", "lumbar_extension": "torso"}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def peak_rss_mib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


# ---------------------------------------------------------------- 1. model
def rot(axis, angle):
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    k = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(angle) * k + (1 - math.cos(angle)) * (k @ k)


def euler_xyz(v):
    return rot((1, 0, 0), v[0]) @ rot((0, 1, 0), v[1]) @ rot((0, 0, 1), v[2])


def rotvec(r):
    """Rotation vector (axis x angle) of a rotation matrix."""
    c = max(-1.0, min(1.0, (np.trace(r) - 1) / 2))
    ang = math.acos(c)
    if ang < 1e-12:
        return np.zeros(3)
    w = np.array([r[2, 1] - r[1, 2], r[0, 2] - r[2, 0], r[1, 0] - r[0, 1]]) / (2 * math.sin(ang))
    return w * ang


def _floats(s):
    return [float(x) for x in s.split()]


def parse_function(block):
    """(kind, callable q -> value) for the function inside one TransformAxis block."""
    m = re.search(r"<LinearFunction[^>]*>\s*<coefficients>([^<]*)</coefficients>", block)
    if m:
        a, b = _floats(m.group(1))
        return "linear", lambda q, a=a, b=b: a * q + b
    m = re.search(r"<Constant[^>]*>\s*<value>([^<]*)</value>", block)
    if m:
        v = float(m.group(1))
        return "constant", lambda q, v=v: v
    m = re.search(r"<SimmSpline[^>]*>\s*<x>([^<]*)</x>\s*<y>([^<]*)</y>", block)
    if m:
        x, y = np.array(_floats(m.group(1))), np.array(_floats(m.group(2)))
        return "simmspline(linear interp)", lambda q, x=x, y=y: float(np.interp(q, x, y))
    return "none", lambda q: 0.0


def parse_model(text):
    joints = {}
    for m in re.finditer(r"<(CustomJoint|PinJoint|WeldJoint)\s+name=\"([^\"]*)\">(.*?)</\1>", text, re.S):
        kind, name, body = m.groups()
        frames = {}
        for f in re.finditer(r"<PhysicalOffsetFrame\s+name=\"([^\"]*)\">(.*?)</PhysicalOffsetFrame>", body, re.S):
            parent = re.search(r"<socket_parent>([^<]*)</socket_parent>", f.group(2)).group(1).split("/")[-1]
            ori = _floats(re.search(r"<orientation>([^<]*)</orientation>", f.group(2)).group(1))
            frames[f.group(1)] = {"body": parent, "orientation": ori}
        p = re.search(r"<socket_parent_frame>([^<]*)</socket_parent_frame>", body).group(1)
        c = re.search(r"<socket_child_frame>([^<]*)</socket_child_frame>", body).group(1)
        coords = re.findall(r"<Coordinate\s+name=\"([^\"]*)\">", body)
        ranges = {n: _floats(r) for n, r in re.findall(
            r"<Coordinate\s+name=\"([^\"]*)\">.*?<range>([^<]*)</range>", body, re.S)}
        axes = []
        for ta in re.finditer(r"<TransformAxis\s+name=\"(rotation[123])\">(.*?)</TransformAxis>", body, re.S):
            co = re.search(r"<coordinates>([^<]*)</coordinates>", ta.group(2))
            ax = _floats(re.search(r"<axis>([^<]*)</axis>", ta.group(2)).group(1))
            fkind, fn = parse_function(ta.group(2))
            axes.append({"name": ta.group(1), "coordinate": co.group(1).strip() if co else None, "axis": ax,
                         "function": fkind, "fn": fn})
        joints[name] = {"kind": kind, "parent_frame": frames.get(p, {"body": p.split("/")[-1], "orientation": [0, 0, 0]}),
                        "child_frame": frames.get(c, {"body": c.split("/")[-1], "orientation": [0, 0, 0]}),
                        "coordinates": coords, "ranges": ranges, "axes": axes}
    return joints


def body_rotations(joints, q):
    """Ground orientation of every body for coordinate values q (missing = 0)."""
    child_of = {j["child_frame"]["body"]: n for n, j in joints.items()}
    out = {"ground": np.eye(3)}

    def get(body):
        if body in out:
            return out[body]
        j = joints[child_of[body]]
        rp = get(j["parent_frame"]["body"]) @ euler_xyz(j["parent_frame"]["orientation"])
        if j["kind"] == "PinJoint":
            rj = rot((0, 0, 1), q.get(j["coordinates"][0], 0.0))
        elif j["kind"] == "WeldJoint":
            rj = np.eye(3)
        else:
            rj = np.eye(3)
            for a in j["axes"]:
                val = a["fn"](q.get(a["coordinate"], 0.0)) if a["coordinate"] else a["fn"](0.0)
                rj = rj @ rot(a["axis"], val)
        out[body] = rp @ rj @ euler_xyz(j["child_frame"]["orientation"]).T
        return out[body]
    for b in list(child_of):
        get(b)
    return out


def model_section(osim_path):
    text = Path(osim_path).read_text(errors="replace")
    joints = parse_model(text)
    coords = re.findall(r"<Coordinate\s+name=\"([^\"]*)\"", text)
    couplers = []
    for m in re.finditer(r"<CoordinateCouplerConstraint\s+name=\"([^\"]*)\">(.*?)</CoordinateCouplerConstraint>", text, re.S):
        b = m.group(2)
        lf = re.search(r"<coupled_coordinates_function>.*?<coefficients>([^<]*)</coefficients>", b, re.S)
        couplers.append({"name": m.group(1),
                         "independent": re.search(r"<independent_coordinate_names>([^<]*)<", b).group(1).strip(),
                         "dependent": re.search(r"<dependent_coordinate_name>([^<]*)<", b).group(1).strip(),
                         "linear_coefficients": _floats(lf.group(1)) if lf else None,
                         "enforced": (re.search(r"<isEnforced>([^<]*)<", b) or re.search(r"<isDisabled>([^<]*)<", b)).group(0)})
    zero = body_rotations(joints, {})
    signs = {}
    for c, body in TEST_COORDS.items():
        base = 0.2 if c.startswith("knee") else 0.0
        r0 = body_rotations(joints, {c: base})[body]
        r1 = body_rotations(joints, {c: base + 0.2})[body]
        w = rotvec(r1 @ r0.T)  # rotation in the ground frame
        signs[c] = {"body": body, "q_from": base, "q_to": base + 0.2,
                    "ground_rotation_vector_rad": [round(float(x), 4) for x in w]}
    gp = joints.get("ground_pelvis", {})
    return {
        "sha256": sha256_file(osim_path), "coordinates": coords, "coordinates_equal_H25": coords == H25,
        "couplers": couplers,
        "ground_pelvis_axes": [{k: a[k] for k in ("name", "coordinate", "axis", "function")} for a in gp.get("axes", [])],
        "ground_pelvis_offset_orientations": [gp.get("parent_frame", {}).get("orientation"),
                                              gp.get("child_frame", {}).get("orientation")],
        "gravity": re.search(r"<gravity>([^<]*)</gravity>", text).group(1).strip(),
        "pelvis_axes_at_zero_pose": [round(float(x), 6) for x in zero["pelvis"].ravel()],
        "fk_sign_test": signs,
        "coordinate_ranges": {n: r for j in joints.values() for n, r in j["ranges"].items()},
    }


# ---------------------------------------------------------------- 2-4. data (bounded reads)
def row_groups_by_trial(pf):
    md = pf.metadata
    j = pf.schema_arrow.get_field_index("source_trial_index")
    out = {}
    for i in range(md.num_row_groups):
        st = md.row_group(i).column(j).statistics
        if st is None or st.min != st.max:
            raise ValueError(f"row group {i} has no single source_trial_index")
        out.setdefault(int(st.min), []).append(i)
    return out


def dof_order_section(path, ranges):
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(path)
    rg = row_groups_by_trial(pf)
    first = min(rg)
    cols = [f"dof{i:02d}_pos" for i in range(23)]
    t = pf.read_row_groups(rg[first], columns=cols + ["source_original_trial_name"])
    x = {c: t.column(c).to_numpy() for c in cols}
    res = {"file": str(path), "trial_index": first, "trial": t.column("source_original_trial_name")[0].as_py(),
           "frames": t.num_rows, "columns": {}}
    for i, c in enumerate(cols):
        p = np.nanpercentile(x[c], [0, 1, 50, 99, 100])
        row = {"p0_p1_p50_p99_p100": [round(float(v), 4) for v in p]}
        for hyp, names in (("H23", H23), ("H_order", H_ORDER)):
            name = names[i]
            r = ranges.get(name)
            if r and not name.startswith("pelvis_t"):
                inside = float(np.mean((x[c] >= r[0] - 1e-6) & (x[c] <= r[1] + 1e-6)))
                row[hyp] = {"coordinate": name, "range": r, "fraction_inside": round(inside, 4)}
            else:
                row[hyp] = {"coordinate": name, "range": r}
        res["columns"][c] = row
    res["max_abs_dof10_minus_dof09"] = float(np.nanmax(np.abs(x["dof10_pos"] - x["dof09_pos"])))
    res["max_abs_dof17_minus_dof16"] = float(np.nanmax(np.abs(x["dof17_pos"] - x["dof16_pos"])))
    # left/right structure under H23: right block dof06-12, left block dof13-19
    pairs = {}
    for r_i, l_i, name in ((6, 13, "hip_flexion"), (9, 16, "knee_angle"), (10, 17, "ankle_angle")):
        a, b = x[f"dof{r_i:02d}_pos"], x[f"dof{l_i:02d}_pos"]
        pairs[name] = {"right_p1_p99": [round(float(v), 3) for v in np.nanpercentile(a, [1, 99])],
                       "left_p1_p99": [round(float(v), 3) for v in np.nanpercentile(b, [1, 99])]}
    res["left_right_under_H23"] = pairs
    return res


def pelvis_yaw(tilt, lst, rot_):
    """Yaw of the pelvis anterior axis about +y (0 = facing ground +x), ground_pelvis = Rz Rx Ry body-fixed."""
    ct, st, cl, sl, cr, sr = np.cos(tilt), np.sin(tilt), np.cos(lst), np.sin(lst), np.cos(rot_), np.sin(rot_)
    # first column of Rz(t) Rx(l) Ry(r)
    rz =np.stack([np.stack([ct, -st, 0 * ct], -1), np.stack([st, ct, 0 * ct], -1),
                   np.stack([0 * ct, 0 * ct, 0 * ct + 1], -1)], -2)
    rx = np.stack([np.stack([0 * cl + 1, 0 * cl, 0 * cl], -1), np.stack([0 * cl, cl, -sl], -1),
                   np.stack([0 * cl, sl, cl], -1)], -2)
    ry = np.stack([np.stack([cr, 0 * cr, sr], -1), np.stack([0 * cr, 0 * cr + 1, 0 * cr], -1),
                   np.stack([-sr, 0 * cr, cr], -1)], -2)
    a =(rz @ rx @ ry)[..., :, 0]
    return np.arctan2(-a[..., 2], a[..., 0]), a[..., 1]


def heading_and_weight_section(path, slug):
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(path)
    names = pf.schema_arrow.names
    rg = row_groups_by_trial(pf)
    fy_cols = [c for c in names if c.endswith("_force_y")]
    cols = ["dof00_pos", "dof01_pos", "dof02_pos", "com_vel_x", "com_vel_z", "missing_grf_reason",
            "source_original_trial_name", "entered_mass_kg", "dynamics_model_mass_kg"] + fy_cols
    trials, fsum, nclean = [], 0.0, 0
    entered = model = None
    for ti in sorted(rg):
        t = pf.read_row_groups(rg[ti], columns=cols)
        yaw, up = pelvis_yaw(t.column("dof00_pos").to_numpy(), t.column("dof01_pos").to_numpy(),
                             t.column("dof02_pos").to_numpy())
        z = np.exp(1j * yaw)
        mean = complex(np.mean(z))
        rec = {"trial_index": ti, "name": t.column("source_original_trial_name")[0].as_py(), "frames": t.num_rows,
               "yaw_mean_deg": round(math.degrees(math.atan2(mean.imag, mean.real)), 2),
               "yaw_resultant": round(abs(mean), 4),
               "yaw_p1_p99_deg": [round(float(v), 1) for v in np.degrees(np.percentile(
                   np.angle(z / (mean / abs(mean) if abs(mean) else 1)), [1, 99]))]}
        if slug == "fa16":
            vx, vz = t.column("com_vel_x").to_numpy(), t.column("com_vel_z").to_numpy()
            speed = np.hypot(vx, vz)
            v = np.array([np.mean(vx), np.mean(vz)])
            rec["com_mean_horizontal_speed_m_s"] = round(float(np.hypot(*v)), 3)
            rec["com_travel_yaw_deg"] = round(math.degrees(math.atan2(-v[1], v[0])), 2) if np.hypot(*v) > 0.2 else None
            rec["com_median_speed_m_s"] = round(float(np.median(speed)), 3)
        flags = np.array(t.column("missing_grf_reason").to_pylist(), dtype=object)
        clean = flags == "notMissingGRF"
        total = sum(t.column(c).to_numpy() for c in fy_cols)
        rec["frames_notMissingGRF"] = int(clean.sum())
        if clean.any():
            rec["mean_vertical_force_N_clean"] = round(float(np.mean(total[clean])), 2)
            fsum += float(np.sum(total[clean]))
            nclean += int(clean.sum())
        entered = float(t.column("entered_mass_kg")[0].as_py())
        model = float(t.column("dynamics_model_mass_kg")[0].as_py())
        trials.append(rec)
        del t
    w = fsum / nclean / G if nclean else None
    return {"file": str(path), "trials": trials, "contact_force_y_columns": fy_cols,
            "weight": {"frames_notMissingGRF": nclean, "mean_force_over_g_kg": None if w is None else round(w, 3),
                       "entered_mass_kg": entered, "dynamics_model_mass_kg": round(model, 3),
                       "ratio_to_entered": None if w is None else round(w / entered, 4),
                       "ratio_to_model": None if w is None else round(w / model, 4)}}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--sections", default="model,dof_order,heading")
    a = ap.parse_args(argv)
    if os.nice(0) < 19:
        raise SystemExit("run at nice 19 (AGENTS.md read-only probe exception)")
    started = time.time()
    sections = a.sections.split(",")
    parts = sorted(p.parent for p in a.root.glob("*/*/frames.parquet"))
    out = {"task": "HIST-06", "probe": "contributor_tools/audit_probes/2026_10_31/probe_hist06_addb_mapping.py",
           "probe_sha256": sha256_file(__file__), "root": str(a.root), "participants": len(parts),
           "scientific_approval": False}
    if "model" in sections:
        models = {}
        for p in parts:
            models[f"{p.parent.name}/{p.name}"] = model_section(p / "dynamics_model.osim")
        first = next(iter(models.values()))
        same = {k: all(m[k] == first[k] for m in models.values())
                for k in ("coordinates", "couplers", "ground_pelvis_axes", "ground_pelvis_offset_orientations", "gravity")}
        sign_table = {c: sorted({tuple(np.sign(np.round(m["fk_sign_test"][c]["ground_rotation_vector_rad"], 3)).astype(int).tolist())
                                 for m in models.values()}) for c in TEST_COORDS}
        out["model"] = {"identical_across_participants": same,
                        "fk_sign_patterns_across_participants": {c: [list(s) for s in v] for c, v in sign_table.items()},
                        "example": {"participant": next(iter(models)), **first},
                        "per_participant_fk": {k: m["fk_sign_test"] for k, m in models.items()},
                        "per_participant_sha256": {k: m["sha256"] for k, m in models.items()}}
        ranges = first["coordinate_ranges"]
    else:
        ranges = model_section(parts[0] / "dynamics_model.osim")["coordinate_ranges"]
    if "dof_order" in sections:
        out["dof_order"] = {s: dof_order_section(a.root / s / subj / "frames.parquet", ranges)
                            for s, subj in DOF_ORDER_TRIALS.items()}
    if "heading" in sections:
        out["heading_weight"] = {}
        for p in parts:
            out["heading_weight"][f"{p.parent.name}/{p.name}"] = heading_and_weight_section(p / "frames.parquet", p.parent.name)
            print(f"{p.parent.name}/{p.name} peak RSS {peak_rss_mib():.0f} MiB", flush=True)
    out["resources"] = {"peak_rss_mib": round(peak_rss_mib(), 1), "wall_s": round(time.time() - started, 1),
                        "nice": os.nice(0)}
    with open(a.out, "x") as f:
        f.write(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"out": str(a.out), "peak_rss_mib": out["resources"]["peak_rss_mib"]}))


if __name__ == "__main__":
    main()
