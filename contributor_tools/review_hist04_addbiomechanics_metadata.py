#!/usr/bin/env python3
"""HIST-04: can LocoHub metadata be rebuilt for Falisse (fa16), Tan running (ta21)
and Tan walking (ta22) from AddBiomechanics B3D headers? Plan-only acquisition.

    python3 contributor_tools/review_hist04_addbiomechanics_metadata.py fetch HEADERS_DIR MEMBER [MEMBER ...]
    python3 contributor_tools/review_hist04_addbiomechanics_metadata.py build HEADERS_DIR

``fetch`` reads only the B3D header of each member from the official
AddBiomechanics Google Drive copy (uncompressed B3D files): bytes 0-7 give the
header length, then one single-range request reads the header protobuf. No frame
bytes are requested. One request pair per member, 2 s apart.

``build`` parses the headers with a minimal protobuf wire decoder (field numbers
from nimblephysics dart/proto/SubjectOnDisk.proto at c405b056), joins them with
the archive central directory recorded by HIST-01, and writes the audit, the
header evidence, plan-only guarded-launcher specs (checked with
guarded_launcher.validate_spec in-process; acquisition script bound by a
placeholder hash, never launched) and the two local review sheets.
"""
import hashlib
import json
import math
import re
import struct
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REL = lambda p: str(Path(p).resolve().relative_to(ROOT)) if str(Path(p).resolve()).startswith(str(ROOT)) else str(p)
ARCHIVE_URL = "http://archive.simtk.org/addbiomechanics/addbiomechanics.zip"
ARCHIVE_ETAG = '"613ecc9321-631d01550d044"'
CD_PATH = ROOT / "converted_datasets/reconversion_v2/swarm_backlog_20261021/adb_official_release_metadata_20261021/central_directory.bin"
CD_SHA256 = "88d494ccf3b1026ded8c37b9fcbf093e5f76adf0f1bda3d2956b19d3f508ce09"
DRIVE_URL = "https://drive.usercontent.google.com/download?id={}&export=download&confirm=t"
AUDIT = ROOT / "docs/quality/audits/hist04-addbiomechanics-metadata.json"
EVIDENCE = ROOT / "docs/quality/audits/source_evidence/hist04"
PLAN_DIR = ROOT / "converted_datasets/reconversion_v2/hist04_addbiomechanics_20261031/plans"
SHEETS = ROOT / "review_sheets"
DEST = Path("/mnt/s/locomotion_data/addbiomechanics_hist04")
ACQUIRE_SCRIPT = "contributor_tools/acquire_addbiomechanics_member.py"
REVIEW_SCRIPT = "contributor_tools/review_hist04_addbiomechanics_metadata.py"
PLACEHOLDER = "0" * 64
RESERVE_MIB = 15 * 1024
MAX_HEADER = 64 * 1024 ** 2
FOLDERS = {"fa16": "Falisse2017_Formatted_No_Arm", "ta21": "Tan2021_Formatted_No_Arm", "ta22": "Tan2022_Formatted_No_Arm"}
# Official AddBiomechanics Drive tree (addbiomechanics.org/redirect/main_dataset_download.html), listed 2026-10-31.
DRIVE_IDS = {
    'test/No_Arm/Falisse2017_Formatted_No_Arm/subject_3/subject_3.b3d': '17OEbu8Iuwt3FtGCUZUly9ghrN2ygV3oQ',
    'test/No_Arm/Tan2021_Formatted_No_Arm/s3/s3.b3d': '14dadURZVKDSaMxl7e1rKeF-Qv4iLsiYP',
    'test/No_Arm/Tan2022_Formatted_No_Arm/10/10.b3d': '17d7oWKixXpYX99ORgZd24SuKR_CnIZa_',
    'train/No_Arm/Falisse2017_Formatted_No_Arm/subject_0/subject_0.b3d': '1oMMcQ8hv5HUplMHHzBuNPrkS10MPDxau',
    'train/No_Arm/Falisse2017_Formatted_No_Arm/subject_1/subject_1.b3d': '1o1hM1S9qm4BNTBUTbGYy2xjAYGSoHSpf',
    'train/No_Arm/Falisse2017_Formatted_No_Arm/subject_10/subject_10.b3d': '1oJPB-k6rA6xohKDf10SZkpG5uW57BhIr',
    'train/No_Arm/Falisse2017_Formatted_No_Arm/subject_2/subject_2.b3d': '1nnSv-UpdWo0ZkfgM01eg0PSPjNuRIT0Q',
    'train/No_Arm/Falisse2017_Formatted_No_Arm/subject_4/subject_4.b3d': '1o83eNV3WNpHpyieNUe-RMr-cZAupCx97',
    'train/No_Arm/Falisse2017_Formatted_No_Arm/subject_5/subject_5.b3d': '1nS-nrVyzvVlVOAZTbu3N3rvC0XjerFnl',
    'train/No_Arm/Falisse2017_Formatted_No_Arm/subject_6/subject_6.b3d': '1nrZpjYtp60IX4K613v-Tv0Th-tCoOpJ6',
    'train/No_Arm/Falisse2017_Formatted_No_Arm/subject_7/subject_7.b3d': '1oPh5WcYk1Ds-XJi6i81lu1PfCwgMIkKd',
    'train/No_Arm/Falisse2017_Formatted_No_Arm/subject_8/subject_8.b3d': '1nkg0k0EX5EyavX-s7Rsp2pyUGGmUDLA7',
    'train/No_Arm/Falisse2017_Formatted_No_Arm/subject_9/subject_9.b3d': '1oEK0s-wJnsGgOfDd-RvMVNRANYhh2Bft',
    'train/No_Arm/Tan2021_Formatted_No_Arm/s1/s1.b3d': '1_1pEoG51sm77uc-HKIIk5unZqybEsftP',
    'train/No_Arm/Tan2021_Formatted_No_Arm/s4/s4.b3d': '1ZSio7BM4v6CS7niD5C6bt07znSJpSSfr',
    'train/No_Arm/Tan2021_Formatted_No_Arm/s5/s5.b3d': '1Zvb7bErDvQ0HucpIq0RYo8KuxsOub1r2',
    'train/No_Arm/Tan2021_Formatted_No_Arm/s6/s6.b3d': '1_uN7zIffMfdEo3XBcPJZ1bKQBhbDKL1H',
    'train/No_Arm/Tan2021_Formatted_No_Arm/s7/s7.b3d': '1ZjrvqjmykCHSiIPlJwaY2d_imGfV8c5a',
    'train/No_Arm/Tan2021_Formatted_No_Arm/s8/s8.b3d': '1Zd1AwNTyKaEDSalbZMICrCJBePSS0lpm',
    'train/No_Arm/Tan2021_Formatted_No_Arm/s9/s9.b3d': '1ZY0TNgCQx_m7Ohmbp0sbex3udvC4Sdpb',
    'train/No_Arm/Tan2022_Formatted_No_Arm/02/02.b3d': '1Y4fkDFRSJQcsr-G2iNizkPLFEEjGQWaX',
    'train/No_Arm/Tan2022_Formatted_No_Arm/04/04.b3d': '1XT-JaZNtdA5YiP0sH6yTGpyRGT4Rcfwh',
    'train/No_Arm/Tan2022_Formatted_No_Arm/05/05.b3d': '1Y8yK_sKW-SkU1NlphpOx5BvPgml4BccM',
    'train/No_Arm/Tan2022_Formatted_No_Arm/06/06.b3d': '1ZBqMueTJSBJHp6HhzIPCN5qSPBVvUuJS',
    'train/No_Arm/Tan2022_Formatted_No_Arm/07/07.b3d': '1XlELseiu52PQA6GcmssQsOzj8U5xxTzM',
    'train/No_Arm/Tan2022_Formatted_No_Arm/08/08.b3d': '1Y3E9P99FBs4piBrAahDRuU1cnM2_m1uY',
    'train/No_Arm/Tan2022_Formatted_No_Arm/09/09.b3d': '1XWjItZiB-pjiwqy92tHURMxwx7RnBd9w',
    'train/No_Arm/Tan2022_Formatted_No_Arm/11/11.b3d': '1Y-2asWzgKTW8y6BugToZuI7nTNfD9TLA',
    'train/No_Arm/Tan2022_Formatted_No_Arm/12/12.b3d': '1YsbVt4qni_11SbsykK3x0UYDX5Ecqyqh',
    'train/No_Arm/Tan2022_Formatted_No_Arm/13/13.b3d': '1Xn1qvVUqiwQUsfqrqWU6R4baMiGY_vYv',
    'train/No_Arm/Tan2022_Formatted_No_Arm/14/14.b3d': '1Xe_acMnSB7emwaeJ555-o2oeVrR1MW4B',
    'train/No_Arm/Tan2022_Formatted_No_Arm/15/15.b3d': '1ZHyYTDfzpNsrhrnKbXJ2ekcwnFbgOXZS',
    'train/No_Arm/Tan2022_Formatted_No_Arm/17/17.b3d': '1XPMZZMYRXGMgtgsEYcQjOobGCEP0uYAJ',
    'train/No_Arm/Tan2022_Formatted_No_Arm/18/18.b3d': '1Yb99JDhjYuEfRRvd-fCe_Xc-efDI9RaR',
    'train/No_Arm/Tan2022_Formatted_No_Arm/19/19.b3d': '1Xpk6N_SDRbYY5ozYhBR6BVOrlhS3lFDj',
    'train/No_Arm/Tan2022_Formatted_No_Arm/20/20.b3d': '1Z45Au3ORd9ej1lmbYI1NRvina07fSw4w',
}
PASS = {0: "kinematics", 1: "dynamics", 2: "lowPassFilter", 3: "accMinimizingFilter"}
TTYPE = {0: "treadmill", 1: "overground", 2: "staticTrial", 3: "other"}
FEAT = {0: "walking", 1: "running", 2: "unevenTerrain", 3: "flatTerrain"}
QUAL = {0: "pilotData", 1: "experimentalData", 2: "internetData"}
MGR = ["notMissingGRF", "measuredGrfZeroWhenAccelerationNonZero", "unmeasuredExternalForceDetected", "torqueDiscrepancy",
       "forceDiscrepancy", "notOverForcePlate", "missingImpact", "missingBlip", "shiftGRF", "interpolatedClippedGRF",
       "manualReview", "footContactDetectedButNoForce", "tooHighMarkerRMS", "hasInputOutliers", "hasNoForcePlateData",
       "velocitiesStillTooHighAfterFiltering", "copOutsideConvexFootError", "zeroForceFrame", "extendedToNearestPeakForce"]


def label(member):
    return member.replace("/", "__")


def slug_of(member):
    return next(s for s, f in FOLDERS.items() if f"/{f}/" in member)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ------------------------------------------------------------------ fetch ---

def _range(url, a, b, path):
    head = subprocess.run(["curl", "-sS", "-L", "--max-time", "300", "-r", f"{a}-{b}", "-D", "-", "-o", str(path), url],
                          capture_output=True, text=True, check=True).stdout
    status = [l for l in head.splitlines() if l.startswith("HTTP/")][-1].strip()
    get = lambda k: ([l.split(":", 1)[1].strip() for l in head.splitlines() if l.lower().startswith(k + ":")] or [None])[-1]
    if " 206" not in status:
        raise SystemExit(f"not 206: {status}")
    return status, get("content-range"), get("last-modified"), Path(path).read_bytes()


def fetch(out, members):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for member in members:
        url = DRIVE_URL.format(DRIVE_IDS[member])
        lab = label(member)
        r = {"member": member, "drive_file_id": DRIVE_IDS[member], "url": url,
             "fetched_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        s1, cr1, lm, first = _range(url, 0, 7, out / f"{lab}.len.bin")
        hlen = struct.unpack("<q", first)[0]
        if not 0 < hlen <= MAX_HEADER:
            raise SystemExit(f"{member}: header length {hlen} outside admission")
        time.sleep(1)
        s2, cr2, _, hdr = _range(url, 8, 8 + hlen - 1, out / f"{lab}.hdr.bin")
        if len(hdr) != hlen:
            raise SystemExit(f"{member}: short header read")
        r.update(len_request={"status": s1, "content_range": cr1}, last_modified=lm, header_len=hlen,
                 file_bytes=int(cr1.rsplit("/", 1)[1]), header_request={"status": s2, "content_range": cr2},
                 header_sha256=hashlib.sha256(hdr).hexdigest(), bytes_transferred=8 + hlen)
        (out / f"{lab}.fetch.json").write_text(json.dumps(r, indent=1) + "\n")
        print(member, hlen, r["file_bytes"])
        time.sleep(2)


# ---------------------------------------------------------- B3D header -----

def _varint(b, i):
    r = s = 0
    while True:
        c = b[i]; i += 1; r |= (c & 0x7F) << s; s += 7
        if c < 0x80:
            return r, i


def _fields(b):
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
            raise ValueError(f"wire type {w}")
        yield f, w, v


def _varints(w, v):
    if w == 0:
        return [v]
    out, i = [], 0
    while i < len(v):
        x, i = _varint(v, i)
        out.append(x)
    return out


def _f32(w, v):
    return list(struct.unpack(f"<{len(v) // 4}f", v))


def _f64(w, v):
    return list(struct.unpack(f"<{len(v) // 8}d", v))


def _model(xml):
    t = xml.decode("utf8", "replace")
    bodies = re.findall(r'<Body\s+name="([^"]*)">(.*?)</Body>', t, re.S)
    masses = {b: float(re.search(r"<mass>\s*([-0-9.eE+]+)\s*</mass>", x).group(1)) for b, x in bodies
              if re.search(r"<mass>", x)}
    name = re.search(r'<Model\s+name="([^"]*)"', t)
    return {"bytes": len(xml), "sha256": hashlib.sha256(xml).hexdigest(), "model_name": name.group(1) if name else None,
            "coordinates": re.findall(r'<Coordinate\s+name="([^"]*)"', t), "bodies": [b for b, _ in bodies],
            "body_mass_sum_kg": round(sum(masses.values()), 6)}


def parse_header(raw, file_bytes):
    """SubjectOnDiskHeader. Absent proto3 fields are reported as absent, never as their enum default."""
    h = {"passes": [], "ground_contact_body": [], "trials": [], "marker_name": [], "subject_tag": [],
         "acc_name": [], "gyro_name": [], "emg_name": [], "custom_value_name": []}
    present = set()
    for f, w, v in _fields(raw):
        present.add(f)
        if f == 1: h["num_dofs"] = v
        elif f == 24: h["num_joints"] = v
        elif f == 3: h["raw_sensor_frame_size"] = v
        elif f == 4: h["processing_pass_frame_size"] = v
        elif f == 5:
            p = {"pass_type": "kinematics"}
            for f2, w2, v2 in _fields(v):
                if f2 == 1: p["pass_type"] = PASS.get(v2, v2)
                elif f2 == 2: p["model"] = _model(v2)
            h["passes"].append(p)
        elif f == 6: h["ground_contact_body"].append(v.decode())
        elif f == 7: h["custom_value_name"].append(v.decode())
        elif f == 10: h["version"] = v
        elif f == 11: h["href"] = v.decode("utf8", "replace")
        elif f == 12: h["notes"] = v.decode("utf8", "replace")
        elif f == 13: h["biological_sex"] = v.decode("utf8", "replace")
        elif f == 14: h["height_m"] = _f64(w, v)[0]
        elif f == 15: h["mass_kg"] = _f64(w, v)[0]
        elif f == 16: h["age_years"] = v if v < 2 ** 63 else v - 2 ** 64
        elif f == 17: h["marker_name"].append(v.decode())
        elif f == 18: h["acc_name"].append(v.decode())
        elif f == 19: h["gyro_name"].append(v.decode())
        elif f == 20: h["emg_name"].append(v.decode())
        elif f == 23: h["subject_tag"].append(v.decode("utf8", "replace"))
        elif f == 25: h["data_quality"] = QUAL.get(v, v)
        elif f == 9:
            t = {"trial_tag": [], "pass_types": [], "lowpass": [], "detected_trial_feature": []}
            tp, missing = set(), []
            for f2, w2, v2 in _fields(v):
                tp.add(f2)
                if f2 == 1: t["name"] = v2.decode("utf8", "replace")
                elif f2 == 2: missing += _varints(w2, v2)
                elif f2 == 3: t["length"] = v2
                elif f2 == 4: t["timestep_s"] = _f64(w2, v2)[0]
                elif f2 == 6: t["trial_tag"].append(v2.decode("utf8", "replace"))
                elif f2 == 7: t["num_force_plates"] = v2
                elif f2 == 10: t["original_name"] = v2.decode("utf8", "replace")
                elif f2 == 11: t["split_index"] = v2
                elif f2 == 17: t["trial_type"] = TTYPE.get(v2, v2)
                elif f2 == 18: t["detected_trial_feature"] += [FEAT.get(x, x) for x in _varints(w2, v2)]
                elif f2 == 5:
                    ph = {}
                    for f3, w3, v3 in _fields(v2):
                        if f3 == 1: ph["type"] = PASS.get(v3, v3)
                        elif f3 == 10: ph["cutoff_hz"] = _f32(w3, v3)[0]
                        elif f3 == 11: ph["order"] = v3
                    ph.setdefault("type", "kinematics")
                    t["pass_types"].append(ph["type"])
                    if ph["type"] == "lowPassFilter":
                        t["lowpass"].append([ph.get("cutoff_hz"), ph.get("order")])
            t.setdefault("split_index", 0)  # proto3: absent int32 is 0
            t["fields_absent"] = [n for k, n in ((6, "trial_tag"), (9, "marker_names_guessed"), (12, "original_trial_start_frame"),
                                                 (13, "original_trial_end_frame"), (14, "original_trial_start_time"),
                                                 (15, "original_trial_end_time"), (17, "trial_type"), (18, "detected_trial_feature"))
                                  if k not in tp]
            c = Counter(missing)
            t["missing_grf_reason_counts"] = {MGR[k] if k < len(MGR) else str(k): n for k, n in sorted(c.items())}
            t["frames_with_grf"] = c.get(0, 0)
            t["missing_grf_array_matches_length"] = len(missing) == t.get("length")
            h["trials"].append(t)
    h["top_fields_absent"] = [n for k, n in ((2, "num_trials"), (16, "age_years"), (13, "biological_sex"), (14, "height_m"),
                                             (15, "mass_kg"), (24, "num_joints"), (25, "data_quality")) if k not in present]
    frames = sum(t.get("length", 0) for t in h["trials"])
    data = sum(t.get("length", 0) * (h["raw_sensor_frame_size"] + len(t["pass_types"]) * h["processing_pass_frame_size"])
               for t in h["trials"])
    h["layout_check"] = {"frames": frames, "expected_file_bytes": 8 + len(raw) + data, "file_bytes": file_bytes,
                         "matches": 8 + len(raw) + data == file_bytes}
    h["num_markers"] = len(h.pop("marker_name"))
    h["header_bytes"] = len(raw)
    return h


# ------------------------------------------------- archive central dir -----

def central_directory():
    raw = CD_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != CD_SHA256:
        raise SystemExit("central directory differs from the HIST-01/HIST-03 record")
    out, i = {}, 0
    while i + 46 <= len(raw) and raw[i:i + 4] == b"PK\x01\x02":
        (_, _, _, _, method, _, _, crc, csize, usize, nlen, elen, clen, _, _, _, off) = struct.unpack(
            "<IHHHHHHIIIHHHHHII", raw[i:i + 46])
        name = raw[i + 46:i + 46 + nlen].decode("utf8")
        extra = raw[i + 46 + nlen:i + 46 + nlen + elen]
        j = 0
        while j + 4 <= len(extra):
            hid, hlen = struct.unpack("<HH", extra[j:j + 4])
            body, k = extra[j + 4:j + 4 + hlen], 0
            if hid == 1:
                if usize == 0xFFFFFFFF: usize = struct.unpack("<Q", body[k:k + 8])[0]; k += 8
                if csize == 0xFFFFFFFF: csize = struct.unpack("<Q", body[k:k + 8])[0]; k += 8
                if off == 0xFFFFFFFF: off = struct.unpack("<Q", body[k:k + 8])[0]; k += 8
            j += 4 + hlen
        if name.endswith(".b3d") and "/No_Arm/" in name and any(f"/{f}/" in name for f in FOLDERS.values()):
            out[name] = {"method": method, "crc32": crc, "compressed_bytes": csize, "expanded_bytes": usize,
                         "local_header_offset": off}
        i += 46 + nlen + elen + clen
    return out


# ------------------------------------------------------------- build -------

def read_headers(hdir):
    hdir, res = Path(hdir), {}
    for fj in sorted(hdir.glob("*.fetch.json")):
        r = json.loads(fj.read_text())
        raw = (hdir / f"{label(r['member'])}.hdr.bin").read_bytes()
        if hashlib.sha256(raw).hexdigest() != r["header_sha256"]:
            raise SystemExit(f"{r['member']}: header bytes differ from fetch receipt")
        res[r["member"]] = {"receipt": r, "header": parse_header(raw, r["file_bytes"])}
    return res


PUB = {
    "fa16": {"citation": "Falisse A, Van Rossom S, Jonkers I, De Groote F. EMG-driven optimal estimation of subject-specific Hill model muscle-tendon parameters of the knee joint actuators. IEEE Trans Biomed Eng 64(9):2253-2262, 2017. doi:10.1109/TBME.2016.2630009",
             "read": "KU Leuven accepted manuscript https://lirias.kuleuven.be/retrieve/494460 (PDF sha256 d53f65599f746ffa46207c9804719c92056ab741c818c70438cc08c4899a5446, text extracted with pypdf), section II.A",
             "quotes": ["Eight healthy volunteers (four males and four females, age 29.8 ± 3.9 years, height 176 ± 6.6 cm, and weight 69.6 ± 6.0 kg)",
                        "65 retro-reflective skin-mounted markers ... recorded (100 Hz) ... during six functional motions: gait, squat, stair descent, stair ascent, sit-to-stand-to-sit, and squat jump",
                        "Ground reaction forces (GRF) and EMG data were recorded (1000 Hz) using force plates (AMTI, Watertown, USA)",
                        "11 experimental datasets (seven left and four right legs) were selected"],
             "not_stated": ["walking speed", "treadmill or overground", "incline", "per-participant values"]},
    "ta21": {"citation": "Tan T, Strout ZA, Cheung RTH, Shull PB. Strike index estimation using a convolutional neural network with a single, shoe-mounted inertial sensor. J Biomech 139:111145, 2022. doi:10.1016/j.jbiomech.2022.111145",
             "read": "PubMed abstract via E-utilities efetch PMID 35594817 (XML sha256 03162acde0b84a1b04c852d404fb059d281e74580655a46af8915bf56ea6bf48). Full text not obtained: paper-fetch (Unpaywall, publisher) and SSRN 4021993 failed (institutional access needed).",
             "quotes": ["16 participants were required to land with three strike patterns (rearfoot, midfoot, and forefoot strike) while running on an instrumented treadmill in four conditions i.e., two footwear types and two running speeds"],
             "not_stated": ["speed values", "footwear names", "which trial-name token is which strike pattern", "demographics", "sampling rates"]},
    "ta22": {"citation": "Tan T, Wang D, Shull PB, Halilaj E. IMU and smartphone camera fusion for knee adduction and knee flexion moment estimation during walking. IEEE Trans Ind Inform 19(2):1445-1455, 2023. doi:10.1109/TII.2022.3189648",
             "read": "Abstract via Semantic Scholar API (JSON sha256 ff551c1cef19ea3bae30f67f267adf4b2f8b4a2820622ab31cdb1671668baeb4); author README https://raw.githubusercontent.com/Tian-A-Tan/KAM_and_KFM_Estimation/main/README.md (HIST-03 receipt); secondary description of the same 17-subject dataset: Knowledge transfer-driven estimation of knee moments and ground reaction forces from smartphone videos, PLOS One 2025, doi:10.1371/journal.pone.0335257 (PMC12594377 HTML sha256 c45b30e57477548112becfeb4571fa67e5f0f95823b6f31161a354888055bb0d). Primary full text not obtained (IEEE, institutional access).",
             "quotes": ["Walking data from 17 subjects ... among young healthy nonobese males (TII abstract)",
                        "Ground reaction force (GRF) and center of pressure (CoP) were collected with an instrumented treadmill with two split belts (Bertec Corp.) (README)",
                        "seventeen male subjects (age: 23.2 ± 1.1 years; height: 1.76 ± 0.06 m; mass: 67.3 ± 8.3 kg) (PLOS One 2025, secondary)",
                        "a 2-minute trial of normal walking at a self-selected speed (1.16 ± 0.04 m/s). Nine trials were conducted using combinations of three different foot progression angles (baseline − 15°, baseline, and baseline + 15°) and three different speeds (self-selected −0.2 m/s, self-selected, and self-selected + 0.2 m/s). Similarly, trials involving three different step widths (baseline −0.054 m, baseline, and baseline + 0.070 m) and trunk sway angles (4°, 8°, and 12°) were conducted, each at three different speeds (PLOS One 2025, secondary)",
                        "marker trajectories with a sampling rate of 100 Hz, while ground reaction force data were collected ... at 1000 Hz (PLOS One 2025, secondary)"],
             "not_stated": ["per-participant self-selected speed", "which segment of an AddBiomechanics trial belongs to which speed or modification level", "incline"]},
}


def study_stats(heads, cd):
    st = {}
    for slug, folder in FOLDERS.items():
        members = sorted(m for m in cd if f"/{folder}/" in m)
        read = {m: heads[m]["header"] for m in members if m in heads}
        frames_read = sum(h["layout_check"]["frames"] for h in read.values())
        est, basis = 0, []
        for m in members:
            if m in read:
                est += read[m]["layout_check"]["frames"]
                continue
            hs = list(read.values())
            hb = sum(h["header_bytes"] for h in hs) / len(hs)
            fb = hs[0]["raw_sensor_frame_size"] + 3 * hs[0]["processing_pass_frame_size"]
            est += round((cd[m]["expanded_bytes"] - 8 - hb) / fb)
            basis.append(m)
        subj = [{"subject": m.split("/")[3], "split": m.split("/")[0], **{k: read[m].get(k) for k in
                 ("biological_sex", "age_years", "height_m", "mass_kg")},
                 "kinematics_model_mass_kg": read[m]["passes"][0]["model"]["body_mass_sum_kg"],
                 "dynamics_model_mass_kg": next((p["model"]["body_mass_sum_kg"] for p in read[m]["passes"] if p["pass_type"] == "dynamics"), None)}
                for m in members if m in read]
        for s in subj:
            s["dynamics_to_entered_mass_ratio"] = round(s["dynamics_model_mass_kg"] / s["mass_kg"], 3) if s["dynamics_model_mass_kg"] else None
        trials = [t for h in read.values() for t in h["trials"]]
        st[slug] = {"members": len(members), "headers_read": len(read),
                    "expanded_bytes_total": sum(cd[m]["expanded_bytes"] for m in members),
                    "compressed_bytes_total": sum(cd[m]["compressed_bytes"] for m in members),
                    "largest_expanded_bytes": max(cd[m]["expanded_bytes"] for m in members),
                    "members_over_2e9_bytes": sum(cd[m]["expanded_bytes"] > 2e9 for m in members),
                    "frames_in_headers_read": frames_read, "frames_all_members": est,
                    "frames_basis": "exact for headers read" + (f"; {len(basis)} unread members estimated from expanded bytes with the mean header size and frame size of those read" if basis else ""),
                    "frames_with_grf_in_headers_read": sum(t["frames_with_grf"] for t in trials),
                    "subjects": subj,
                    "original_trial_names": dict(sorted(Counter(t["original_name"] for t in trials).items())),
                    "segments_read": len(trials),
                    "segment_length_max": max(t["length"] for t in trials),
                    "sampling_hz_from_timestep": sorted({round(1 / t["timestep_s"], 3) for t in trials}),
                    "pass_orders": dict(Counter(",".join(t["pass_types"]) for t in trials)),
                    "lowpass_pass_settings": dict(Counter(json.dumps(x) for t in trials for x in t["lowpass"])),
                    "num_force_plates": dict(Counter(str(t.get("num_force_plates")) for t in trials)),
                    "ground_contact_bodies": sorted({",".join(h["ground_contact_body"]) for h in read.values()}),
                    "markers": sorted({h["num_markers"] for h in read.values()}),
                    "dofs": sorted({h["num_dofs"] for h in read.values()}),
                    "subject_tags": sorted({",".join(h["subject_tag"]) for h in read.values()}),
                    "trial_fields_absent_everywhere": sorted(set.intersection(*[set(t["fields_absent"]) for t in trials])),
                    "header_fields_absent": sorted({x for h in read.values() for x in h["top_fields_absent"]}),
                    "layout_matches_file_size": f"{sum(h['layout_check']['matches'] for h in read.values())}/{len(read)}",
                    "drive_size_equals_archive_expanded": f"{sum(heads[m]['receipt']['file_bytes'] == cd[m]['expanded_bytes'] for m in read)}/{len(read)}"}
    return st


def columns(st):
    S = lambda status, source, **kw: {"status": status, "source": source, **kw}
    fa, t1, t2 = st["fa16"], st["ta21"], st["ta22"]
    return [
        {"column": "subject", "contract": "DATA_CONTRACT.md observation contract",
         "fa16": S("from_archive_path", "AddBiomechanics folder name (subject_0..subject_10) and header href", crosswalk_to_paper="missing: no participant code in header or paper"),
         "ta21": S("from_archive_path", "folder name s1, s3-s9 and header href", crosswalk_to_paper="missing; AddBiomechanics has 8 of the 16 participants in the abstract"),
         "ta22": S("from_archive_path", "folder name 02, 04-15, 17-20 and header href (17 folders = 17 subjects in the abstract)", crosswalk_to_paper="missing")},
        {"column": "source_recording_id", "contract": "DATA_CONTRACT.md",
         **{s: S("from_b3d_header", "archive member path + member SHA-256 at acquisition + B3D trial index and trial name") for s in FOLDERS}},
        {"column": "observation_id", "contract": "DATA_CONTRACT.md",
         **{s: S("from_b3d_header", "B3D trial = one AddBiomechanics segment: trial name, original_name and split_index") for s in FOLDERS},
         "note": f"Segments are at most {t1['segment_length_max']} frames (ta21, 10 s at 200 Hz) or 2000 frames at 100 Hz (20 s); AddBiomechanics crops trials by GRF availability and length (FAQ). Whether consecutive segments are contiguous is not recorded."},
        {"column": "reference_side", "contract": "DATA_CONTRACT.md; a limb-indexed continuous recording needs left or right",
         **{s: S("from_b3d_header", "contact bodies calcn_r/calcn_l and model coordinate suffixes _r/_l: both legs, one observation identity per side") for s in FOLDERS},
         "note": "fa16 has a third contact body, pelvis (seat contact). The paper's 'seven left and four right legs' is an EMG selection, not a reference side."},
        {"column": "observation_type", "contract": "DATA_CONTRACT.md",
         **{s: S("from_b3d_header", "continuous_recording: B3D trials are continuous frames with no events") for s in FOLDERS}},
        {"column": "task", "contract": "docs/reference Metadata; task_registry.py",
         "fa16": S("unresolved", "trial names Gait_*, STS_*, StairUp_*", why="8 of 11 subjects match the TBME cohort statistics, but 3 are extra and the files hold only 3 of the paper's 6 motions (gait, sit-to-stand, stair ascent; see falisse_attribution); 'Gait' does not establish terrain; 'STS' would be sit-to-stand-to-sit (both directions in one recording) only if the trials follow the paper's protocol"),
         "ta21": S("from_publication", "run: 'running on an instrumented treadmill' (abstract)"),
         "ta22": S("from_publication_partial", "walking on an instrumented treadmill (README; TII abstract)", why="level_walking versus dynamic_walk (gait modifications) is a LocoHub convention; incline not stated")},
        {"column": "task_id", "contract": "docs/reference Metadata",
         "fa16": S("from_trial_name", "original_name, e.g. Gait_5, STS_2, StairUp_4"),
         "ta21": S("from_trial_name", "original_name {nike|mini}_{SR|SI|baseline}_{24|28}, e.g. nike_SR_24"),
         "ta22": S("from_trial_name", "original_name baseline | fpa | step_width | trunk_sway")},
        {"column": "task_info.treadmill", "contract": "docs/reference example key",
         "fa16": S("missing", "trial_type field absent in every trial; the paper names force plates, no treadmill, and its protocol is not confirmed for these trials"),
         "ta21": S("from_publication", "abstract: instrumented treadmill"),
         "ta22": S("from_publication", "README: instrumented treadmill with two split belts")},
        {"column": "task_info.speed_m_s", "contract": "docs/reference example key",
         "fa16": S("missing", "not stated in the paper"),
         "ta21": S("missing", "abstract: two speeds, values not given; tokens 24/28 have no stated unit", needed="speed values from the J Biomech full text (Elsevier; UM library access) or the authors"),
         "ta22": S("missing", "protocol speeds are relative to each participant's self-selected speed (cohort 1.16 ± 0.04 m/s, secondary source); per-participant values and the speed of each segment are not in the header or trial names", needed="per-trial condition table from the authors; the SimTK stance-window HDF5 fields were not checked for a condition label")},
        {"column": "task_info.incline_deg", "contract": "docs/reference example key",
         **{s: S("missing", "not stated in any source read") for s in FOLDERS}},
        {"column": "task_info.condition (footwear, strike pattern, gait modification level)", "contract": "task_info source task metadata",
         "fa16": S("not_applicable", "no conditions in trial names"),
         "ta21": S("from_trial_name_tokens_only", "footwear token nike/mini and condition token SR/SI/baseline", why="The abstract has two footwear types and three strike patterns (rearfoot, midfoot, forefoot); which token is which is not stated. Store tokens only."),
         "ta22": S("partial", "modification family from trial name", why=f"Each modification is one AddBiomechanics trial split into up to 14 segments, while the protocol has 9 trials per modification (3 levels x 3 speeds): the level and speed of each segment are missing")},
        {"column": "subject_metadata.mass_kg", "contract": "subject_metadata JSON",
         **{s: S("from_b3d_header", "SubjectOnDiskHeader.mass_kg (value entered on AddBiomechanics)") for s in FOLDERS},
         "note": "The dynamics-pass model total mass differs from the entered mass (see mass_check). Which mass normalizes moments and forces is a later conversion convention."},
        {"column": "subject_metadata.height_m", "contract": "subject_metadata JSON", **{s: S("from_b3d_header", "height_m") for s in FOLDERS}},
        {"column": "subject_metadata.sex", "contract": "subject_metadata JSON", **{s: S("from_b3d_header", "biological_sex") for s in FOLDERS}},
        {"column": "subject_metadata.age_years", "contract": "subject_metadata JSON", **{s: S("from_b3d_header", "age_years") for s in FOLDERS}},
        {"column": "subject_metadata.population", "contract": "profile applicability",
         **{s: S("from_b3d_header", "subject_tag 'healthy'") for s in FOLDERS}},
        {"column": "sampling rate", "contract": "provenance; time_s",
         "fa16": S("from_b3d_header", f"per-trial timestep; {fa['sampling_hz_from_timestep'][0]}-{fa['sampling_hz_from_timestep'][-1]} Hz", note="paper states 100 Hz; keep the source timestep, do not round"),
         "ta21": S("from_b3d_header", f"per-trial timestep, slightly different per segment ({t1['sampling_hz_from_timestep'][0]}-{t1['sampling_hz_from_timestep'][-1]} Hz)", note="about 200 Hz; keep the source timestep, do not round"),
         "ta22": S("from_b3d_header", f"per-trial timestep, slightly different per segment ({t2['sampling_hz_from_timestep'][0]}-{t2['sampling_hz_from_timestep'][-1]} Hz)", note="marker rate 100 Hz per the secondary source; keep the source timestep")},
        {"column": "time_s", "contract": "primary time index",
         **{s: S("from_b3d_header", "frame index x trial timestep, segment-local") for s in FOLDERS}},
        {"column": "source_start_time_s / source_end_time_s", "contract": "optional, both or neither",
         **{s: S("missing", "original_trial_start_time/end_time absent in every trial header; both left unknown (allowed)") for s in FOLDERS}},
        {"column": "model", "contract": "conversion provenance",
         **{s: S("from_b3d_header", "OpenSim model text per pass ('optimized_scale_and_markers', 25 coordinates, 14 bodies); the dynamics pass has its own mass-tuned model") for s in FOLDERS}},
        {"column": "force-plate count and GRF availability", "contract": "provenance; quality",
         "fa16": S("from_b3d_header", f"num_force_plates {fa['num_force_plates']}; per-frame missing_GRF_reason"),
         "ta21": S("from_b3d_header", "2 plates; per-frame missing_GRF_reason"),
         "ta22": S("from_b3d_header", "2 plates; per-frame missing_GRF_reason")},
    ]


PAPER_COHORT = {"age_years": (29.8, 3.9), "height_cm": (176, 6.6), "mass_kg": (69.6, 6.0)}


def falisse_subsets(subjects):
    """Score every 4-male/4-female subset against the six cohort statistics the TBME paper reports,
    rounded as the paper rounds them (age and mass to 0.1, height mean to 1 cm, SDs to 0.1)."""
    import itertools
    import statistics as stt
    men = [s for s in subjects if s["biological_sex"] == "male"]
    women = [s for s in subjects if s["biological_sex"] == "female"]
    if len(women) != 4:
        return {"subsets": 0, "scores": {}, "full_matches": []}
    val = {"age_years": lambda s: s["age_years"], "height_cm": lambda s: s["height_m"] * 100, "mass_kg": lambda s: s["mass_kg"]}
    scores, full = Counter(), []
    for m in itertools.combinations(men, 4):
        g = list(m) + women
        n = 0
        for k, (mu, sd) in PAPER_COHORT.items():
            xs = [val[k](s) for s in g]
            n += round(stt.mean(xs), 0 if k == "height_cm" else 1) == mu
            n += round(stt.stdev(xs), 1) == sd
        scores[n] += 1
        if n == 6:
            full.append(sorted(s["subject"] for s in g))
    return {"subsets": sum(scores.values()), "scores": {str(k): scores[k] for k in sorted(scores)}, "full_matches": full}


def output_estimate(st):
    frames = {s: st[s]["frames_all_members"] for s in FOLDERS}
    total = sum(frames.values())
    # Numeric columns per row for one pass: pos, vel, acc, tau (23 DOFs each), per contact body force, CoP, torque (3 each),
    # COM pos/vel/acc, root residual (6), missing-GRF code; float64.
    cols = {s: 4 * 23 + 9 * (3 if s == "fa16" else 2) + 9 + 6 + 1 for s in FOLDERS}
    one = sum(frames[s] * cols[s] * 8 for s in FOLDERS)
    return {"frames": frames, "frames_total": total,
            "rows": {"A_one_row_per_frame_one_pass": total, "B_one_row_per_frame_per_pass": 3 * total,
                     "C_current_adapter_raw_plus_each_pass": 4 * total},
            "numeric_columns_per_pass": cols,
            "uncompressed_numeric_bytes_one_pass": one,
            "basis": "Frames exact for the 15 headers read, estimated for the other 21 members. Every trial read has 3 passes. Bytes are float64 values before Parquet compression for the listed signals; compressed sizes are not measured. Option C stores every frame field as JSON text (the B3D frame data alone is about "
                     + f"{sum(st[s]['expanded_bytes_total'] for s in FOLDERS) / 1e9:.1f} GB in binary)."}


def plan(cd, heads):
    sys.path.insert(0, str(ROOT))
    from contributor_tools.guarded_launcher import validate_spec
    PLAN_DIR.mkdir(parents=True, exist_ok=True)
    order = sorted(cd, key=lambda m: ({"fa16": 0, "ta22": 1, "ta21": 2}[slug_of(m)], cd[m]["expanded_bytes"]))
    out = []
    review_sha = sha256(ROOT / REVIEW_SCRIPT)
    for n, m in enumerate(order, 1):
        slug, subject = slug_of(m), m.split("/")[3]
        exp = {"member": m, "archive_url": ARCHIVE_URL, "archive_etag": ARCHIVE_ETAG, "central_directory_sha256": CD_SHA256,
               **cd[m], "drive_file_id": DRIVE_IDS[m],
               "drive_header_sha256": heads[m]["receipt"]["header_sha256"] if m in heads else None,
               "drive_header_len": heads[m]["receipt"]["header_len"] if m in heads else None,
               "max_download_rate_bytes_per_s": 2 * 1024 ** 2}
        ep = PLAN_DIR / f"{slug}_{subject}_expected.json"
        ep.write_text(json.dumps(exp, indent=1) + "\n")
        exp_mib = math.ceil(cd[m]["expanded_bytes"] / 1024 ** 2)
        root = DEST / slug / subject
        spec = {"job_id": f"hist04-adb-{slug}-{subject}",
                "command": ["python3", ACQUIRE_SCRIPT, "--expected", REL(ep), "--out", str(root),
                            "--receipt-dir", str(DEST / "acquisition_receipts" / f"{slug}_{subject}"), "--run"],
                "output_root": str(root), "receipt_path": str(DEST / "launcher_receipts" / f"{slug}_{subject}.json"),
                "bindings": {ACQUIRE_SCRIPT: PLACEHOLDER, REVIEW_SCRIPT: review_sha, REL(ep): sha256(ep)},
                "timeout_seconds": 3600, "kill_after_seconds": 30, "poll_seconds": 15,
                "startup_memory_mib": {"linux": 3584, "windows": 2816}, "runtime_memory_mib": {"linux": 2048, "windows": 2048},
                "disk_admission": [{"path": str(DEST.parent), "min_free_mib": RESERVE_MIB + 2 * exp_mib}],
                "expected_output_names": [Path(m).name, "acquisition_result.json"], "address_space_mib": 256}
        validate_spec(spec)
        sp = PLAN_DIR / f"{n:02d}_{slug}_{subject}_spec.json"
        sp.write_text(json.dumps(spec, indent=1) + "\n")
        out.append({"order": n, "member": m, "spec": REL(sp), "spec_sha256": sha256(sp), "expected": REL(ep),
                    "expected_sha256": sha256(ep), "transfer_bytes": cd[m]["compressed_bytes"],
                    "transient_b3d_bytes": cd[m]["expanded_bytes"], "validate_spec": "passed in-process; not launched"})
    return out


def build(hdir):
    heads, cd = read_headers(hdir), central_directory()
    if len(cd) != 36:
        raise SystemExit(f"expected 36 No_Arm members, found {len(cd)}")
    if set(cd) != set(DRIVE_IDS):
        raise SystemExit("Drive listing and archive members differ")
    st = study_stats(heads, cd)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    ev = {"note": "HIST-04 B3D header summaries (headers only; no frame bytes). Coordinates and bodies listed once per study.",
          "members": {}}
    for m, d in heads.items():
        h = json.loads(json.dumps(d["header"]))
        for p in h["passes"]:
            p["model"].pop("coordinates"); p["model"].pop("bodies")
        ev["members"][m] = {"receipt": d["receipt"], "header": h}
    ev["model_coordinates"] = {s: heads[next(m for m in heads if slug_of(m) == s)]["header"]["passes"][0]["model"]["coordinates"] for s in FOLDERS}
    ev["model_bodies"] = {s: heads[next(m for m in heads if slug_of(m) == s)]["header"]["passes"][0]["model"]["bodies"] for s in FOLDERS}
    evp = EVIDENCE / "b3d-header-summaries.json"
    evp.write_text(json.dumps(ev, indent=1) + "\n")
    specs = plan(cd, heads)
    est = output_estimate(st)
    fa = st["fa16"]["subjects"]
    mean = lambda xs: sum(xs) / len(xs)
    sd = lambda xs: (sum((x - mean(xs)) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5
    ages = [s["age_years"] for s in fa]
    sub = falisse_subsets(fa)
    match = sub["full_matches"][0] if len(sub["full_matches"]) == 1 else []
    num = lambda x: int(x.split("_")[1])
    extra = sorted((s for s in fa if s["subject"] not in match), key=lambda s: num(s["subject"]))
    match_txt = ", ".join(sorted(match, key=num))
    extra_txt = ", ".join("%s (%d y)" % (s["subject"], s["age_years"]) for s in extra)
    ratios = [x["dynamics_to_entered_mass_ratio"] for x in st["fa16"]["subjects"]]
    audit = {
        "task_id": "HIST-04", "status": "review", "scientific_approval": False,
        "decision_context": "D-HIST-03-1 = C (José): take fa16, ta21, ta22 from AddBiomechanics one participant at a time; make sure the metadata columns can be reconstructed.",
        "builder": REVIEW_SCRIPT,
        "method": [
            "Official AddBiomechanics Drive tree listed (HTML folder pages only) for the six No_Arm folders of the three studies: 36 B3D files, the same 36 members as the archive central directory (sha256 " + CD_SHA256[:8] + "...).",
            f"Headers only: for {len(heads)} members (all 11 fa16, ta21 s3 and s8, ta22 04 and 10) bytes 0-7 and then the header range were requested from the uncompressed Drive copy (single-range 206). Frame bytes were never requested. Total transferred {sum(d['receipt']['bytes_transferred'] for d in heads.values()):,} bytes.",
            "Headers parsed with a minimal protobuf wire decoder against SubjectOnDisk.proto (nimblephysics c405b056); absent proto3 fields are reported as absent, not as enum defaults.",
            "Publications: Falisse 2017 accepted manuscript text (pypdf), Tan 2022 abstract (PubMed E-utilities), Tan 2023 abstract (Semantic Scholar), the Tan README, and one secondary article that describes the Tan 2023 dataset protocol.",
        ],
        "header_layout": {"matches_file_size": {s: st[s]["layout_matches_file_size"] for s in FOLDERS},
                          "drive_bytes_equal_archive_expanded": {s: st[s]["drive_size_equals_archive_expanded"] for s in FOLDERS},
                          "header_bytes_range": [min(d["header"]["header_bytes"] for d in heads.values()), max(d["header"]["header_bytes"] for d in heads.values())],
                          "note": "Tan headers are 8.8-19.9 MB because per-frame quality arrays (missing-GRF reason, marker RMS, residuals) are in the header."},
        "studies": st,
        "publications": PUB,
        "metadata_columns": columns(st),
        "falisse_attribution": {
            "finding": (f"Exactly one of the {sub['subsets']} four-man/four-woman subsets of the 11 AddBiomechanics Falisse subjects reproduces all six cohort statistics the TBME 2017 paper reports: "
                        f"{match_txt}. The folder is very likely the paper's 8 volunteers plus 3 additional men ({extra_txt})."),
            "subset_test": {**sub, "rounding": "age and mass mean and SD to 0.1, height mean to 1 cm and SD to 0.1 cm, as reported",
                            "earlier_error": "The first HIST-04 version read ages outside 29.8 ± 3.9 as a contradiction; a mean ± SD is not a range. Corrected after independent verification (HIST-04-verify.json)."},
            "paper": "8 volunteers (4 male, 4 female), age 29.8 ± 3.9 y, height 176 ± 6.6 cm, mass 69.6 ± 6.0 kg; 11 datasets = 11 legs (7 left, 4 right); six motions: gait, squat, stair descent, stair ascent, sit-to-stand-to-sit, squat jump.",
            "addbiomechanics": f"11 subjects with 11 distinct sex/age/height/mass records ({sum(s['biological_sex'] == 'male' for s in fa)} male, {sum(s['biological_sex'] == 'female' for s in fa)} female), age range {min(ages)}-{max(ages)} y; trials only Gait, STS and StairUp.",
            "unresolved": ["Who the 3 extra men are and which study they come from.",
                           "The trials: the files hold 3 of the paper's 6 motions (gait, sit-to-stand, stair ascent as Gait/STS/StairUp); squat, stair descent and squat jump are absent. Why, and whether these trials follow the paper's protocol, is not stated."],
            "consequence": "Demographics for all 11 come from the headers either way. The paper's citation is likely right for 8 subjects, but its protocol facts (motions, overground plates, 100 Hz, legs) and the task mapping are not applied until the source of the 3 extra subjects and of the trials is confirmed. Falisse is not releasable until then; acquisition is not blocked.",
            "needed": "Yes/no for José (outward-facing): ask the AddBiomechanics team or the KU Leuven authors (a) whether subjects 0, 2, 3, 4, 5, 6, 9 and 10 are the TBME volunteers, (b) who subjects 1, 7 and 8 are, and (c) which protocol the Gait/STS/StairUp trials came from."},
        "mass_check": {
            "finding": "The dynamics pass carries its own mass-tuned model whose total body mass differs from the entered subject mass.",
            "per_subject": {s: [{k: x[k] for k in ("subject", "mass_kg", "kinematics_model_mass_kg", "dynamics_model_mass_kg", "dynamics_to_entered_mass_ratio")} for x in st[s]["subjects"]] for s in FOLDERS},
            "range": {s: [min(x["dynamics_to_entered_mass_ratio"] for x in st[s]["subjects"]), max(x["dynamics_to_entered_mass_ratio"] for x in st[s]["subjects"])] for s in FOLDERS},
            "consequence": f"Moments from the dynamics pass are consistent with the tuned model, not the entered mass (fa16 ratio {min(ratios):.2f}x to {max(ratios):.2f}x; subject_1: 118.0 kg tuned versus 65.5 kg entered). Normalization mass is a conversion convention for José in the canonical-mapping step; both masses are reconstructable from the header. Not checked: whether total model mass is what AddBiomechanics used for each frame's inverse dynamics.",
            "source": "model_osim_text <mass> elements per pass in the B3D header; nimblephysics docs: the dynamics pass 'further solves for the mass distribution' (https://nimblephysics.org/docs/working-with-addbiomechanics-data.html)"},
        "processing_pass": {
            "found": "Every trial read has passes in the order kinematics, lowPassFilter, dynamics (index 0, 1, 2). The lowPassFilter pass records a 30 Hz, order-2 Butterworth. Filter fields in the kinematics and dynamics pass headers hold uninitialized-looking values and are ignored.",
            "legacy": "Legacy LocoHub converters read processingPasses[1], which is the lowPassFilter pass in all 15 headers read (HIST-03 found the same in Tiziana2019 Subject29).",
            "proposal": "Convert the dynamics pass: per the nimblephysics docs it 'takes as input the previous pass outputs ... and then further solves for the mass distribution, fine tunes bone scales, and tunes motion of the skeleton that best matches the experimental force data'. Its values will differ from the legacy files. Pass choice is part of D-HIST-04-1."},
        "row_design": {
            "current_adapter": "convert_addbiomechanics_to_parquet.py writes 1 raw-sensor row + 1 row per pass per frame as JSON payloads (4 rows per frame here).",
            "proposal": "One row per frame from one pass (dynamics), numeric columns, both legs as two reference_side identities of the same rows' recording, flagged frames kept with their missing_GRF_reason (never deleted silently).",
            "lost_in_proposal": ["kinematics and lowPassFilter pass values", "raw marker trajectories and raw per-plate force/CoP/torque readings", "root-frame copies, joint centres, spatial velocity/acceleration histories", "per-frame marker RMS and residual arrays (they stay in the pinned B3D)"],
            "recoverable": "Only by re-fetching: the plan deletes each B3D after conversion, so left-out passes, raw markers and raw plate readings can be recovered only by downloading the member again from the archive while it still serves the same bytes (checked against archive ETag, central-directory CRC32 and the SHA-256 recorded at acquisition) and reconverting. If the archive changes or disappears, they are lost to LocoHub.",
            "estimate": est,
            "question_for_jose": "D-HIST-04-1"},
        "acquisition_plan": {
            "route": "Archive zip member by HTTP range from archive.simtk.org (stable ETag, CRC32 in the central directory); inflate while streaming to one B3D file; the Drive copy is used only as a cross-check of the header hash.",
            "why_not_drive": "Drive publishes no checksum, may throttle (untested) and transfers 1.35x more bytes (uncompressed).",
            "transient_disk": f"One expanded B3D at a time. Largest {max(st[s]['largest_expanded_bytes'] for s in FOLDERS):,} bytes (ta21 s3); {st['ta21']['members_over_2e9_bytes']} of 8 ta21 files exceed 2.0 GB, so the 'under 2 GB' stated in D-HIST-03-1 does not hold: HIST-03 quoted the compressed size (1.64 GB), but the reader needs the expanded file. Peak is 2.22 GB; disk free about 153 GiB. Logged as an agent resource decision; staying under 2 GB would need a streaming frame decoder instead of the nimblephysics reader.",
            "script_requirements": [
                f"New {ACQUIRE_SCRIPT} (not written; specs bind a placeholder hash).",
                "Refuse to start if any *.b3d exists anywhere under the HIST-04 destination (one transient B3D at a time).",
                "HEAD the archive; refuse on an ETag or Content-Length change. Read the 30-byte local header at the bound offset; refuse unless name, method 8 and sizes match the central directory.",
                "Stream the compressed payload with a 1 MiB buffer and a 2 MiB/s ceiling, inflate (raw deflate) straight to <subject>.b3d.partial; compute SHA-256 of the compressed and expanded streams and CRC32 of the expanded stream; refuse on CRC32 or size mismatch.",
                "Check the expanded header: int64 length then header bytes; when a Drive header hash is bound, the header SHA-256 must equal it. Check the layout arithmetic (8 + header + frames x (sensor + passes x pass frame) = file size).",
                "fsync, publish with a no-clobber rename, write acquisition_result.json (hashes, HTTP headers, header summary, status, scientific_approval false). Preserve partial files on failure; stop on a STOP file.",
                "RLIMIT_AS 256 MiB; disk reserve and Windows free memory checked every 15 s.",
                "The B3D is deleted only by the later conversion job after its outputs verify; the next acquisition refuses while it exists."],
            "order": f"fa16 by size (pilot: {specs[0]['member'].split('/')[3]}, smallest), then ta22 by size, then ta21 by size; one job per tool call, each after a fresh admission. The first job is the pilot; a later study starts only after the previous study's first conversion is reviewed.",
            "specs": specs,
            "totals": {s: {"transfer_bytes": st[s]["compressed_bytes_total"], "members": st[s]["members"]} for s in FOLDERS}},
        "forbidden_inventions": [
            "ta21 speed from the tokens 24/28 (unit unstated; 2.4/2.8 m/s would be a guess).",
            "ta21 strike pattern from SR/SI/baseline, or 'minimalist' from 'mini'.",
            "ta22 speed or modification level per segment, or applying the cohort mean self-selected speed to a participant.",
            "fa16 protocol facts (overground, 100 Hz, motions, legs) from the TBME paper while the trials and the 3 extra subjects are unexplained.",
            "Rounding fa16 timesteps (100.1-100.5 Hz) to 100 Hz.",
            "Reading absent trial_type/data_quality fields as their enum defaults (treadmill/pilotData).",
            "Treating consecutive segments as one continuous recording or offsetting time by split_index."],
        "not_checked": [
            "Frame bytes of any file (headers only); 21 of 36 headers not read (their frames are estimated).",
            "Whether the lowPassFilter pass carries joint moments or GRF equal to the dynamics pass.",
            "The Tan 2022 and Tan 2023 full texts (institutional access); the SimTK imukinetics HDF5 for condition labels.",
            "Participant crosswalks to the papers; Falisse source study.",
            "nimblephysics availability in the conversion environment; conversion throughput and compressed output size."],
        "evidence_files": [REL(evp), REL(EVIDENCE / "fetch-receipts.json")],
    }
    receipts = {"note": "HIST-04 fetch receipts (2026-10-31). Header bytes kept under converted_datasets/reconversion_v2/hist04_addbiomechanics_20261031/headers/ (local, gitignored).",
                "drive_listings": "Six No_Arm study folders listed from public folder pages; folder ids in docs/quality/audits/source_evidence/hist03/adb-drive-tree-depth2.json",
                "receipts": [d["receipt"] for d in heads.values()],
                "publications": {"falisse2017_lirias_pdf_sha256": "d53f65599f746ffa46207c9804719c92056ab741c818c70438cc08c4899a5446",
                                 "tan2022_pubmed_efetch_xml_sha256": "03162acde0b84a1b04c852d404fb059d281e74580655a46af8915bf56ea6bf48",
                                 "tan2023_semanticscholar_json_sha256": "ff551c1cef19ea3bae30f67f267adf4b2f8b4a2820622ab31cdb1671668baeb4",
                                 "pmc12594377_html_sha256": "c45b30e57477548112becfeb4571fa67e5f0f95823b6f31161a354888055bb0d",
                                 "nimblephysics_docs_html_sha256": "e1eafd689170292c68b5f32f7e2b319f9eadcf377b88303d100a1a609adb69b3"}}
    (EVIDENCE / "fetch-receipts.json").write_text(json.dumps(receipts, indent=1) + "\n")
    AUDIT.write_text(json.dumps(audit, indent=1, ensure_ascii=False) + "\n")
    sheets(audit)
    print(f"Wrote {REL(AUDIT)}, {REL(evp)}, {len(specs)} specs, review_sheets/HIST-04 and review_sheets/D-HIST-04-1")
    return audit


# ------------------------------------------------------------ sheets ------

STATUS_GROUP = {"from_b3d_header": "B3D header", "from_archive_path": "B3D header", "from_trial_name": "trial name",
                "from_trial_name_tokens_only": "trial name", "from_publication": "publication",
                "from_publication_partial": "partial", "partial": "partial", "missing": "missing",
                "unresolved": "missing", "not_applicable": "not applicable"}
COLORS = {"B3D header": "#2a78d6", "trial name": "#6aa9e9", "publication": "#3a9d6a", "partial": "#e0a030",
          "missing": "#c0392b", "not applicable": "#d5d9de"}


def figures(audit, v, d):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    rows = [c for c in audit["metadata_columns"] if not c["column"].startswith(("source_recording", "observation_type", "time_s", "model", "force-plate", "subject_metadata.height", "subject_metadata.sex", "subject_metadata.age", "subject_metadata.population"))]
    names = {"subject": "subject", "observation_id": "observation id", "reference_side": "side", "task": "task", "task_id": "task id",
             "task_info.treadmill": "treadmill", "task_info.speed_m_s": "speed", "task_info.incline_deg": "incline",
             "subject_metadata.mass_kg": "mass, sex, age, height", "sampling rate": "sampling rate",
             "source_start_time_s / source_end_time_s": "source clock"}
    rows = [c for c in rows if c["column"] in names or c["column"].startswith("task_info.condition")]
    fig, ax = plt.subplots(figsize=(4.5, 4.4))
    for i, c in enumerate(rows):
        for j, s in enumerate(FOLDERS):
            g = STATUS_GROUP[c[s]["status"]]
            ax.add_patch(plt.Rectangle((j, i), 0.94, 0.9, color=COLORS[g]))
    ax.set_xlim(0, 3); ax.set_ylim(len(rows), 0)
    ax.set_xticks([0.47, 1.47, 2.47], ["Falisse", "Tan run", "Tan walk"])
    ax.set_yticks([i + 0.45 for i in range(len(rows))], [names.get(c["column"], "condition") for c in rows])
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    used = [g for g in COLORS if any(STATUS_GROUP[c[s]["status"]] == g for c in rows for s in FOLDERS)]
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=COLORS[g]) for g in used], labels=used, ncol=3, frameon=False,
              loc="lower center", bbox_to_anchor=(0.35, 1.0), fontsize=10, handlelength=1, columnspacing=0.8)
    fig.tight_layout(); fig.savefig(v / "coverage.png", dpi=150); plt.close(fig)
    # Falisse: how many of the paper's six cohort statistics each 4M/4F subset reproduces.
    sub = audit["falisse_attribution"]["subset_test"]
    ks = list(range(7))
    ns = [sub["scores"].get(str(k), 0) for k in ks]
    fig, ax = plt.subplots(figsize=(4.5, 3.3))
    ax.bar(ks, ns, color=["#c9ced4"] * 6 + ["#2a78d6"], width=0.7)
    for k, n in zip(ks, ns):
        if n:
            ax.text(k, n + 0.3, str(n), ha="center")
    ax.set_xticks(ks)
    ax.set_xlabel("reported statistics reproduced (of 6)")
    ax.set_ylabel(f"subsets (of {sub['subsets']})")
    ax.set_ylim(0, max(ns) * 1.25)
    ax.yaxis.get_major_locator().set_params(integer=True)
    fig.tight_layout(); fig.savefig(v / "falisse_subsets.png", dpi=150); plt.close(fig)
    # Decision: rows per design per study.
    est = audit["row_design"]["estimate"]
    fig, ax = plt.subplots(figsize=(4.5, 3.6))
    designs = [("A: 1 row/frame", 1), ("B: 1 row/frame/pass", 3), ("C: current, raw + passes", 4)]
    left = [0, 0, 0]
    for s, col, nm in [("fa16", "#6aa9e9", "Falisse"), ("ta22", "#3a9d6a", "Tan walk"), ("ta21", "#2a78d6", "Tan run")]:
        vals = [est["frames"][s] * k / 1e6 for _, k in designs]
        ax.barh(range(3), vals, left=left, color=col, label=nm, height=0.6)
        left = [a + b for a, b in zip(left, vals)]
    for i, x in enumerate(left):
        ax.text(x + 0.2, i, f"{x:.1f} M", va="center")
    ax.set_yticks(range(3), [n for n, _ in designs]); ax.invert_yaxis()
    ax.set_xlabel("rows, millions"); ax.set_xlim(0, max(left) * 1.25)
    ax.legend(loc="lower center", bbox_to_anchor=(0.4, 1.0), ncol=3, frameon=False, fontsize=10, columnspacing=0.8)
    fig.tight_layout(); fig.savefig(d / "rows.png", dpi=150); plt.close(fig)


def sheets(audit):
    sys.path.insert(0, str(ROOT / "contributor_tools"))
    from common.review_sheet import page
    v, d = SHEETS / "HIST-04", SHEETS / "D-HIST-04-1"
    v.mkdir(parents=True, exist_ok=True); d.mkdir(parents=True, exist_ok=True)
    figures(audit, v, d)
    st = audit["studies"]
    n_read = sum(s["headers_read"] for s in st.values())
    ok = all(s["layout_matches_file_size"].split("/")[0] == s["layout_matches_file_size"].split("/")[1] for s in st.values())
    page(v / "index.html", title="HIST-04 metadata",
         ask="Look at two figures; no decision here.",
         headline="Identity, side, demographics and rate come from the files; speed, incline and Falisse's trial protocol do not.",
         chips=[("pass" if ok else "fail", f"Header layout matches file size, {n_read} of {n_read} files"),
                ("pass", "Drive and archive copies have equal sizes"),
                ("pass", "8 Falisse subjects reproduce the paper's cohort"),
                ("unchecked", "3 extra Falisse men; 3 of 6 paper motions"),
                ("fail", "Tan running speeds not in any source read"),
                ("fail", "Tan walking speed and level per segment missing"),
                ("fail", "Largest file 2.2 GB on disk, not under 2 GB"),
                ("unchecked", "Tuned model mass differs from entered mass"),
],
         figures=[("coverage.png", "Which metadata can be rebuilt from source, per study?",
                   "Red cells have no source; they stay missing, never filled.", "Source of each metadata column per study"),
                  ("falisse_subsets.png", "Which Falisse subjects could be the paper's eight volunteers?",
                   "Only one subset reproduces all six reported statistics.", "Falisse subsets by statistics matched")],
         not_shown=["Signal values (headers only).", "21 of 36 headers.", "Full texts of both Tan papers."],
         reply="HIST-04 ok",
         details=[f"Audit: {REL(AUDIT)}", f"Builder: {REVIEW_SCRIPT}",
                  "Mass: dynamics-pass model total versus entered mass, Falisse 0.71x to 1.80x (118.0 versus 65.5 kg for one subject).",
                  "Falisse subset test: every 4-man/4-woman subset of the 11, scored against the paper's age, height and mass mean and SD at its rounding."])
    est = audit["row_design"]["estimate"]
    gb = est["uncompressed_numeric_bytes_one_pass"] / 1e9
    decision = {
        "question": "How many rows per AddBiomechanics frame should LocoHub write for these three studies?",
        "columns": ["Left out", "Rows", "Size before compression", "Consequence"],
        "rows": [("A", ["the kinematics and low-pass passes, raw markers and raw plate readings",
                        f"about {est['rows']['A_one_row_per_frame_one_pass'] / 1e6:.1f} million", f"about {gb:.0f} GB",
                        "One row per frame from the dynamics pass; flagged frames kept and labelled; values differ from the old files, which used the low-pass pass. Files are deleted after conversion: left-out data return only by re-downloading while the archive serves the same checked bytes, then reconverting."]),
                 ("B", ["raw markers and raw plate readings",
                        f"about {est['rows']['B_one_row_per_frame_per_pass'] / 1e6:.1f} million", f"about {3 * gb:.0f} GB",
                        "One row per frame per pass with a pass column; users must filter by pass. Reversible."]),
                 ("C", ["nothing",
                        f"about {est['rows']['C_current_adapter_raw_plus_each_pass'] / 1e6:.1f} million", "not estimated (text payloads)",
                        "Current adapter: raw row plus one row per pass, fields stored as text; no converter change. Reversible."]),
                 ("defer", ["all three studies for now", "none", "none", "Acquisition can still run; conversion waits; legacy pages stay."])],
        "footnote": "Ordered by row count. Frames exact for 15 files, estimated for 21; sizes uncompressed.",
        "recommendation": ("A, medium confidence: it matches José's wish for fewer rows, keeps every frame and its force-quality flag, "
                           "and uses AddBiomechanics' final dynamically consistent pass. What is left out can be rebuilt only by re-downloading from the archive while it serves the same hash-checked bytes and reconverting. "
                           "Cost: values will not match the old files, and a later convention is still needed for which mass normalizes moments.")}
    page(d / "index.html", title="D-HIST-04-1 rows per frame",
         ask="Choose A, B, C or defer.",
         headline="Each frame holds raw data and three processed versions; the current converter writes four rows.",
         chips=[("pass", "Every trial read has the same three passes"),
                ("pass", "Old files used the low-pass pass"),
                ("unchecked", "Compressed output size")],
         figures=[("rows.png", "How many rows would each design write?",
                   "Bars stack the three studies.", "Rows per design and study")],
         not_shown=["Signal values.", "Which mass normalizes moments."],
         reply="D-HIST-04-1: A | B | C | defer", decision=decision,
         details=[f"Audit: {REL(AUDIT)} (row_design)", f"Builder: {REVIEW_SCRIPT}"])


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "fetch":
        fetch(sys.argv[2], sys.argv[3:])
    elif len(sys.argv) == 3 and sys.argv[1] == "build":
        build(sys.argv[2])
    else:
        sys.exit(__doc__)
