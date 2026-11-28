#!/usr/bin/env python3
"""HIST-05: one row per frame from the AddBiomechanics *dynamics* pass (fa16, ta21, ta22).

Per D-HIST-04-1 = A. Reads one B3D with its own protobuf wire decoder (field
numbers from nimblephysics dart/proto/SubjectOnDisk.proto at c405b056; layout
from SubjectOnDisk.cpp: int64 header length, header, then per frame one sensor
record followed by one pass record per trial pass, in that trial's pass order).

- The pass is chosen by its recorded type name ('dynamics') in each trial's
  processing-pass header, never by index. A trial without exactly one dynamics
  pass, or whose pass list differs from the file-wide pass list at any position
  (nimblephysics labels records by the file-wide list), writes no rows and is
  listed with its frame count.
- Every frame of a kept trial is written, including frames whose GRF is flagged;
  the flag is a column.
- Metadata follow the HIST-04 table (docs/quality/audits/hist04-addbiomechanics-metadata.json):
  values the sources do not give stay absent; source timesteps are not rounded;
  proto3 fields absent from the file are not read as their defaults.
- Signals keep source names and units (DOF index, contact-body names, world
  frame). The canonical LocoHub mapping (ipsi/contra, signs, normalization) is a
  later step, so reference_side is 'none' and no _ipsi_/_contra_ column exists.
  Entered and dynamics-model masses are both written; normalization_mass_kg is
  left missing until José sets that convention.
- Falisse subject_1, subject_7 and subject_8 are refused (D-HIST-04-2 = A).

    python3 convert_addbiomechanics_dynamics_frames.py --b3d FILE --member ARCHIVE_PATH --sha256 HEX --out DIR
"""
import argparse
import hashlib
import json
import math
import os
import re
import struct
from collections import Counter
from pathlib import Path

for _k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "ARROW_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

FOLDERS = {"fa16": "Falisse2017_Formatted_No_Arm", "ta21": "Tan2021_Formatted_No_Arm", "ta22": "Tan2022_Formatted_No_Arm"}
DROPPED = frozenset(f"train/No_Arm/Falisse2017_Formatted_No_Arm/subject_{n}/subject_{n}.b3d" for n in (1, 7, 8))
# Matched by (study, subject), ignoring split, case, spacing and leading zeros (D-HIST-04-2 = A).
DROPPED_KEYS = frozenset(("fa16", f"subject_{n}") for n in (1, 7, 8))


def _norm_subject(s):
    s = re.sub(r"\s+", "", s).casefold()
    return re.sub(r"_0+(\d)", r"_\1", s)


def is_dropped(member):
    parts = [p for p in re.split(r"[/\\]+", member.strip()) if p not in ("", ".")]
    folders = {f.casefold(): s for s, f in FOLDERS.items()}
    for i, part in enumerate(parts):
        slug = folders.get(re.sub(r"\s+", "", part).casefold())
        if slug:
            names = [_norm_subject(x) for x in parts[i + 1:]]
            names = [n[:-4] if n.endswith(".b3d") else n for n in names]
            if any((slug, n) in DROPPED_KEYS for n in names):
                return True
    return False
PASS = {0: "kinematics", 1: "dynamics", 2: "lowPassFilter", 3: "accMinimizingFilter"}
QUAL = {0: "pilotData", 1: "experimentalData", 2: "internetData"}
TTYPE = {0: "treadmill", 1: "overground", 2: "staticTrial", 3: "other"}
MGR = ["notMissingGRF", "measuredGrfZeroWhenAccelerationNonZero", "unmeasuredExternalForceDetected", "torqueDiscrepancy",
       "forceDiscrepancy", "notOverForcePlate", "missingImpact", "missingBlip", "shiftGRF", "interpolatedClippedGRF",
       "manualReview", "footContactDetectedButNoForce", "tooHighMarkerRMS", "hasInputOutliers", "hasNoForcePlateData",
       "velocitiesStillTooHighAfterFiltering", "copOutsideConvexFootError", "zeroForceFrame", "extendedToNearestPeakForce"]
MAX_HEADER = 64 * 1024 ** 2
BATCH = 2048


class Refused(RuntimeError):
    """Input or output violates a stated rule; nothing is published."""


def study_of(member):
    hits = [s for s, f in FOLDERS.items() if f"/{f}/" in member]
    if len(hits) != 1 or not member.endswith(".b3d"):
        raise Refused(f"member is not a HIST-05 study B3D: {member}")
    return hits[0]


def check_member(member):
    if member in DROPPED or is_dropped(member):
        raise Refused(f"dropped by D-HIST-04-2: {member}")
    parts = member.split("/")
    if len(parts) != 5 or parts[0] not in ("train", "test") or parts[1] != "No_Arm" or parts[4] != parts[3] + ".b3d":
        raise Refused(f"unexpected member layout: {member}")
    return study_of(member), parts[3]


# ------------------------------------------------------------ wire decoder --

def _varint(b, i):
    r = s = 0
    while True:
        if i >= len(b):
            raise ValueError("truncated varint")
        c = b[i]; i += 1; r |= (c & 0x7F) << s; s += 7
        if c < 0x80:
            return r, i


def fields(b):
    i = 0
    while i < len(b):
        k, i = _varint(b, i)
        f, w = k >> 3, k & 7
        if w == 0:
            v, i = _varint(b, i)
        elif w == 1:
            v = b[i:i + 8]; i += 8
        elif w == 5:
            v = b[i:i + 4]; i += 4
        elif w == 2:
            n, i = _varint(b, i); v = b[i:i + n]; i += n
        else:
            raise ValueError(f"unsupported wire type {w}")
        if i > len(b):
            raise ValueError("truncated field")
        yield f, w, v


def varints(w, v):
    if w == 0:
        return [v]
    out, i = [], 0
    while i < len(v):
        x, i = _varint(v, i)
        out.append(x)
    return out


def f32(w, v):
    return list(struct.unpack(f"<{len(v) // 4}f", v))


def f64(w, v):
    return list(struct.unpack(f"<{len(v) // 8}d", v))


def model_summary(xml):
    t = xml.decode("utf8", "replace")
    bodies = re.findall(r'<Body\s+name="([^"]*)">(.*?)</Body>', t, re.S)
    masses = [float(m.group(1)) for _, x in bodies for m in [re.search(r"<mass>\s*([-0-9.eE+]+)\s*</mass>", x)] if m]
    return {"sha256": hashlib.sha256(xml).hexdigest(), "bytes": len(xml),
            "coordinates": re.findall(r'<Coordinate\s+name="([^"]*)"', t),
            "body_mass_sum_kg": sum(masses) if masses else None}


def parse_header(raw):
    """SubjectOnDiskHeader with presence tracking. Returns a dict; absent fields are absent keys."""
    h = {"passes": [], "ground_contact_body": [], "trials": [], "subject_tag": [], "num_markers": 0}
    present = set()
    for f, w, v in fields(raw):
        present.add(f)
        if f == 1: h["num_dofs"] = v
        elif f == 3: h["raw_sensor_frame_size"] = v
        elif f == 4: h["processing_pass_frame_size"] = v
        elif f == 5:
            p, xml = {"pass_type": "kinematics"}, b""
            for f2, w2, v2 in fields(v):
                if f2 == 1: p["pass_type"] = PASS.get(v2, str(v2))
                elif f2 == 2: xml = v2
            p["model"] = model_summary(xml)
            p["model_xml"] = xml
            h["passes"].append(p)
        elif f == 6: h["ground_contact_body"].append(v.decode())
        elif f == 10: h["version"] = v
        elif f == 11: h["href"] = v.decode("utf8", "replace")
        elif f == 12: h["notes"] = v.decode("utf8", "replace")
        elif f == 13: h["biological_sex"] = v.decode("utf8", "replace")
        elif f == 14: h["height_m"] = f64(w, v)[0]
        elif f == 15: h["mass_kg"] = f64(w, v)[0]
        elif f == 16: h["age_years"] = v if v < 2 ** 63 else v - 2 ** 64
        elif f == 17: h["num_markers"] += 1
        elif f == 23: h["subject_tag"].append(v.decode("utf8", "replace"))
        elif f == 25: h["data_quality"] = QUAL.get(v, str(v))
        elif f == 9:
            t = {"passes": [], "missing_grf": [], "split_index": 0}
            tp = set()
            for f2, w2, v2 in fields(v):
                tp.add(f2)
                if f2 == 1: t["name"] = v2.decode("utf8", "replace")
                elif f2 == 2: t["missing_grf"] += varints(w2, v2)
                elif f2 == 3: t["length"] = v2
                elif f2 == 4: t["timestep_s"] = f64(w2, v2)[0]
                elif f2 == 7: t["num_force_plates"] = v2
                elif f2 == 10: t["original_name"] = v2.decode("utf8", "replace")
                elif f2 == 11: t["split_index"] = v2
                elif f2 == 17: t["trial_type"] = TTYPE.get(v2, str(v2))
                elif f2 == 5:
                    ph = {"type": "kinematics", "marker_rms": [], "linear_residual": [], "angular_residual": []}
                    for f3, w3, v3 in fields(v2):
                        if f3 == 1: ph["type"] = PASS.get(v3, str(v3))
                        elif f3 == 5: ph["marker_rms"] += f32(w3, v3)
                        elif f3 == 7: ph["linear_residual"] += f32(w3, v3)
                        elif f3 == 8: ph["angular_residual"] += f32(w3, v3)
                    t["passes"].append(ph)
            t["fields_present"] = sorted(tp)
            h["trials"].append(t)
    h["fields_present"] = sorted(present)
    for key in ("num_dofs", "raw_sensor_frame_size", "processing_pass_frame_size"):
        if key not in h:
            raise Refused(f"header lacks {key}")
    return h


def read_header(path):
    with Path(path).open("rb") as stream:
        first = stream.read(8)
        if len(first) != 8:
            raise Refused("file shorter than the header length field")
        n = struct.unpack("<q", first)[0]
        if not 0 < n <= MAX_HEADER:
            raise Refused(f"header length {n} outside admission")
        raw = stream.read(n)
    if len(raw) != n:
        raise Refused("truncated header")
    return raw


def layout(h, header_bytes):
    """Byte offset of each trial's first frame and total expected file size."""
    starts, pos = [], 8 + header_bytes
    for t in h["trials"]:
        starts.append(pos)
        pos += t["length"] * (h["raw_sensor_frame_size"] + len(t["passes"]) * h["processing_pass_frame_size"])
    return starts, pos


def decode_pass_frame(buf, n_dofs, n_bodies):
    """SubjectOnDiskProcessingPassFrame -> named float lists with checked lengths."""
    want = {1: ("pos", n_dofs), 2: ("vel", n_dofs), 3: ("acc", n_dofs), 4: ("tau", n_dofs),
            6: ("cop", 3 * n_bodies), 7: ("contact_torque", 3 * n_bodies), 8: ("contact_force", 3 * n_bodies),
            9: ("com_pos", 3), 10: ("com_vel", 3), 11: ("com_acc", 3), 12: ("root_residual", 6)}
    out = {}
    for f, w, v in fields(buf):
        if f in want:
            out.setdefault(want[f][0], []).extend(f64(w, v))
    for f, (name, n) in want.items():
        got = out.get(name)
        if got is None:
            out[name] = [math.nan] * n  # absent in this frame: missing, never zero
        elif len(got) != n:
            raise Refused(f"pass frame field {name} has {len(got)} values, expected {n}")
    return out


# ------------------------------------------------------------- metadata ---

def task_fields(slug, original):
    """task, task_info per the HIST-04 table. Unknown values are listed as unavailable, never filled."""
    info = {"source_original_trial_name": original}
    if slug == "fa16":
        return None, {**info, "task_status": "unresolved: trials hold 3 of the TBME 2017 paper's 6 motions; protocol not confirmed",
                      "unavailable": ["speed_m_s", "incline_deg", "treadmill"]}
    if slug == "ta21":
        m = re.fullmatch(r"(nike|mini)_(SR|SI|baseline)_(24|28)", original)
        tokens = {"footwear_token": m.group(1), "condition_token": m.group(2), "speed_token": m.group(3)} if m else {}
        return "run", {**info, **tokens, "treadmill": True,
                       "token_meaning": "not stated in the sources read",
                       "unavailable": ["speed_m_s", "incline_deg"]}
    mod = original if original in ("baseline", "fpa", "step_width", "trunk_sway") else None
    return None, {**info, **({"modification_token": mod} if mod else {}), "treadmill": True,
                  "task_status": "walking; level_walking versus dynamic_walk is a pending LocoHub convention",
                  "unavailable": ["speed_m_s", "incline_deg", "modification_level"]}


def subject_metadata(h):
    meta = {k: h[k] for k in ("mass_kg", "height_m", "biological_sex", "age_years") if k in h}
    if h["subject_tag"]:
        meta["subject_tags"] = list(h["subject_tag"])
    masses = {p["pass_type"]: p["model"]["body_mass_sum_kg"] for p in h["passes"]}
    for k in ("kinematics", "dynamics"):
        if masses.get(k) is not None:
            meta[f"{k}_model_mass_kg"] = masses[k]
    meta["source"] = "B3D SubjectOnDiskHeader (values entered on AddBiomechanics) and per-pass model body masses"
    return meta


# ------------------------------------------------------------- convert ----

def columns(n_dofs, bodies):
    cols = [f"dof{i:02d}_{q}" for q in ("pos", "vel", "acc", "tau") for i in range(n_dofs)]
    for b in bodies:
        cols += [f"{b}_{q}_{a}" for q in ("force", "cop", "torque") for a in "xyz"]
    cols += [f"com_{q}_{a}" for q in ("pos", "vel", "acc") for a in "xyz"] + [f"root_residual_{i}" for i in range(6)]
    return cols


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def convert(b3d, member, source_sha256, out_dir, guard=lambda: None):
    """Write <out_dir>/frames.parquet, dynamics_model.osim and conversion.json (all exclusive). Returns the summary."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1); pa.set_io_thread_count(1)
    slug, subject = check_member(member)
    b3d, out_dir = Path(b3d), Path(out_dir)
    if not re.fullmatch(r"[0-9a-f]{64}", source_sha256 or ""):
        raise Refused("source SHA-256 required")
    targets = [out_dir / n for n in ("frames.parquet", "frames.parquet.partial", "dynamics_model.osim", "conversion.json")]
    if any(p.exists() for p in targets):
        raise Refused("conversion outputs already exist; earlier outputs are preserved")
    raw = read_header(b3d)
    h = parse_header(raw)
    starts, expected = layout(h, len(raw))
    size = b3d.stat().st_size
    if size != expected:
        raise Refused(f"layout arithmetic {expected} differs from file size {size}")
    dyn_models = [p for p in h["passes"] if p["pass_type"] == "dynamics"]
    if len(dyn_models) != 1:
        raise Refused(f"subject has {len(dyn_models)} global dynamics passes; exactly one required")
    bodies, n = h["ground_contact_body"], h["num_dofs"]
    global_types = [p["pass_type"] for p in h["passes"]]
    sig = columns(n, bodies)
    meta = subject_metadata(h)
    meta_json = json.dumps(meta, sort_keys=True)
    entered = h.get("mass_kg", math.nan)
    fitted = dyn_models[0]["model"]["body_mass_sum_kg"]
    fitted = math.nan if fitted is None else fitted
    str_cols = ["dataset", "subject", "source_member", "source_b3d_sha256", "source_recording_id", "observation_id",
                "reference_side", "observation_type", "task", "task_id", "task_info", "subject_metadata",
                "source_trial_name", "source_original_trial_name", "source_pass_type", "missing_grf_reason",
                "normalization_mass_status"]
    int_cols = ["source_trial_index", "source_split_index", "source_frame_index", "source_pass_index_in_trial"]
    flt_cols = ["time_s", "source_timestep_s", "entered_mass_kg", "dynamics_model_mass_kg", "normalization_mass_kg",
                "dynamics_marker_rms", "dynamics_linear_residual", "dynamics_angular_residual"] + sig
    schema = pa.schema([(c, pa.string()) for c in str_cols] + [(c, pa.int64()) for c in int_cols] +
                       [(c, pa.float64()) for c in flt_cols])
    out_dir.mkdir(parents=True, exist_ok=True)
    partial = out_dir / "frames.parquet.partial"
    trials, rows_total = [], 0
    sensor, pass_size = h["raw_sensor_frame_size"], h["processing_pass_frame_size"]
    with b3d.open("rb") as stream, pq.ParquetWriter(partial, schema, compression="zstd") as writer:
        for ti, t in enumerate(h["trials"]):
            guard()
            types = [p["type"] for p in t["passes"]]
            name, original = t.get("name"), t.get("original_name")
            rec = {"trial_index": ti, "name": name, "original_name": original, "frames": t["length"], "pass_order": types}
            if types != global_types[:len(types)]:
                # nimblephysics labels each pass record by the file-wide pass list (FramePass::readFromProto);
                # a trial whose own list differs at any position could be read differently, so it is excluded.
                rec.update(status="excluded", reason=f"trial pass order {types} differs from the file-wide pass list {global_types}", rows=0)
                trials.append(rec)
                continue
            if types.count("dynamics") != 1 or not name or original is None or "timestep_s" not in t:
                rec.update(status="excluded", reason="no single dynamics pass, or name/original_name/timestep absent", rows=0)
                trials.append(rec)
                continue
            k = types.index("dynamics")
            step = t["timestep_s"]
            if not (math.isfinite(step) and step > 0):
                rec.update(status="excluded", reason="nonpositive or nonfinite timestep", rows=0)
                trials.append(rec)
                continue
            dpass = t["passes"][k]
            per_frame = {q: (dpass[q] if len(dpass[q]) == t["length"] else None)
                         for q in ("marker_rms", "linear_residual", "angular_residual")}
            mgr = t["missing_grf"] if len(t["missing_grf"]) == t["length"] else None
            task, info = task_fields(slug, original)
            info["source_split_index"] = t["split_index"]
            info_json = json.dumps(info, sort_keys=True)
            record = sensor + len(types) * pass_size
            rid = f"{member}#trial{ti}"
            for start in range(0, t["length"], BATCH):
                guard()
                count = min(BATCH, t["length"] - start)
                stream.seek(starts[ti] + start * record)
                block = stream.read(count * record)
                if len(block) != count * record:
                    raise Refused("short read inside the data section")
                cols = {c: [] for c in schema.names}
                for j in range(count):
                    i = start + j
                    off = j * record + sensor + k * pass_size
                    fr = decode_pass_frame(block[off:off + pass_size], n, len(bodies))
                    vals = fr["pos"] + fr["vel"] + fr["acc"] + fr["tau"]
                    for b in range(len(bodies)):
                        vals += fr["contact_force"][3 * b:3 * b + 3] + fr["cop"][3 * b:3 * b + 3] + fr["contact_torque"][3 * b:3 * b + 3]
                    vals += fr["com_pos"] + fr["com_vel"] + fr["com_acc"] + fr["root_residual"]
                    for c, v in zip(sig, vals):
                        cols[c].append(v)
                    code = mgr[i] if mgr is not None else None
                    row = {"dataset": slug, "subject": subject, "source_member": member, "source_b3d_sha256": source_sha256,
                           "source_recording_id": rid, "observation_id": name, "reference_side": "none",
                           "observation_type": "continuous_recording", "task": task, "task_id": original,
                           "task_info": info_json, "subject_metadata": meta_json, "source_trial_name": name,
                           "source_original_trial_name": original, "source_pass_type": "dynamics",
                           "missing_grf_reason": (MGR[code] if code is not None and code < len(MGR) else (str(code) if code is not None else None)),
                           "normalization_mass_status": "convention_pending: entered versus dynamics-model mass",
                           "source_trial_index": ti, "source_split_index": t["split_index"], "source_frame_index": i,
                           "source_pass_index_in_trial": k, "time_s": i * step, "source_timestep_s": step,
                           "entered_mass_kg": entered, "dynamics_model_mass_kg": fitted, "normalization_mass_kg": math.nan,
                           "dynamics_marker_rms": per_frame["marker_rms"][i] if per_frame["marker_rms"] else math.nan,
                           "dynamics_linear_residual": per_frame["linear_residual"][i] if per_frame["linear_residual"] else math.nan,
                           "dynamics_angular_residual": per_frame["angular_residual"][i] if per_frame["angular_residual"] else math.nan}
                    for c, v in row.items():
                        cols[c].append(v)
                writer.write_table(pa.table(cols, schema=schema))
                rows_total += count
            rec.update(status="written", rows=t["length"], dynamics_pass_index_in_trial=k,
                       frames_with_grf=(sum(1 for x in mgr if x == 0) if mgr is not None else None))
            trials.append(rec)
    frames_total = sum(t["length"] for t in h["trials"])
    if rows_total != sum(r["rows"] for r in trials) or frames_total != sum(r["frames"] for r in trials):
        raise Refused("frame accounting differs")
    readback = pq.ParquetFile(partial).metadata.num_rows
    if readback != rows_total:
        raise Refused(f"parquet readback has {readback} rows, wrote {rows_total}")
    os.link(partial, out_dir / "frames.parquet")
    partial.unlink()
    with (out_dir / "dynamics_model.osim").open("xb") as s:
        s.write(dyn_models[0]["model_xml"])
    summary = {"status": "converted_unreviewed", "scientific_approval": False, "member": member, "dataset": slug,
               "subject": subject, "source_b3d_sha256": source_sha256, "source_bytes": size,
               "header_sha256": hashlib.sha256(raw).hexdigest(), "rows": rows_total, "frames_in_file": frames_total,
               "frames_excluded": frames_total - rows_total, "trials": trials,
               "frames_parquet_sha256": sha256_file(out_dir / "frames.parquet"),
               "dynamics_model_sha256": dyn_models[0]["model"]["sha256"],
               "dof_names": "not mapped: columns are DOF indices; header model coordinates (in model order) recorded for the later mapping step",
               "model_coordinates": dyn_models[0]["model"]["coordinates"], "contact_bodies": bodies,
               "dynamics_fields_not_written": ["ground_contact_wrench (5)", "root_frame_* copies (12 kept as root_residual; 14, 17-24 not written)",
                                               "root_frame_joint_centers (15)", "world_frame_joint_centers (16)"],
               "not_written_by_design": "raw sensor record (markers, raw plate readings) and the kinematics/lowPassFilter passes (D-HIST-04-1 = A)",
               "subject_metadata": meta, "header_fields_present": h["fields_present"],
               "trial_fields_present_union": sorted({f for t in h["trials"] for f in t["fields_present"]}),
               "converter_sha256": sha256_file(__file__)}
    with (out_dir / "conversion.json").open("x") as s:
        s.write(json.dumps(summary, indent=1) + "\n")
    return summary


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--b3d", type=Path, required=True)
    p.add_argument("--member", required=True)
    p.add_argument("--sha256", required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    if sha256_file(a.b3d) != a.sha256:
        raise SystemExit("B3D SHA-256 differs from --sha256")
    s = convert(a.b3d, a.member, a.sha256, a.out)
    print(json.dumps({k: s[k] for k in ("status", "rows", "frames_excluded")}))


if __name__ == "__main__":
    main()
