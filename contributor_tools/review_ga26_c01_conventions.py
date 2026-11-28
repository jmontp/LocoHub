#!/usr/bin/env python3
"""Build the GA26-C01 Gait120 conventions audit from metadata only.

Reads: the paper text extraction, the two lab .osim copies, the committed
anthropometrics spreadsheet, publisher files fetched from figshare (checked
against figshare's published MD5), converter/pipeline source, the committed
source inventory, two .mot headers (no data rows) and directory listings of the
Gait120 source tree. It never reads joint-angle or force sample rows.

    nice -n 19 ionice -c 3 python3 contributor_tools/review_ga26_c01_conventions.py \
        --output docs/quality/audits/ga26-c01-conventions.json
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import re
import statistics as st
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
G120 = ROOT / "contributor_tools/conversion_scripts/Gait120"
PAPER_TEXT = ROOT / "converted_datasets/reconversion_v2/swarm_backlog_20261021/gait120_paper_text.txt"
INVENTORY = ROOT / "converted_datasets/reconversion_v2/gait120_full_batch_20261020/source_inventory.json"
PUBLISHER = ROOT / "converted_datasets/reconversion_v2/ga26_c01_20261031/publisher"
SOURCE = Path("/mnt/s/locomotion_data/Gait120")
FIGSHARE_MD5 = {  # https://api.figshare.com/v2/articles/27677016/files, computed_md5
    "Anthropometric_Data_Participants.xlsx": "e8a02c43464c340e0435246e2c539094",  # file 54257534
    "Subject_Demographics.xlsx": "4a110fc296bb0cc726dd858bc342c009",  # file 53167799
    "Matlab_Codes_for_Processing.zip": "8964047e6686be9083766e4ba0483d23",  # file 53172812
}
TASKS = ("LevelWalking", "StairAscent", "StairDescent", "SlopeAscent",
         "SlopeDescent", "SitToStand", "StandToSit")
PAPER_CYCLES = {"LevelWalking": 1060, "StairAscent": 1187, "StairDescent": 1186,
                "SlopeAscent": 1172, "SlopeDescent": 1150, "SitToStand": 558, "StandToSit": 569}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def find_lines(path: Path, pattern: str) -> list[dict]:
    rx = re.compile(pattern)
    return [{"line": i, "text": line.strip()}
            for i, line in enumerate(path.read_text().splitlines(), 1) if rx.search(line)]


def paper_quote(text: str, needle: str) -> dict:
    flat = re.sub(r"\s+", " ", text.replace("-\n", ""))
    i = flat.find(needle)
    if i < 0:
        raise ValueError(f"paper text lacks: {needle}")
    pages = re.findall(r"PAGE (\d+)", flat[:i])
    return {"pdf_page": int(pages[-1]) if pages else None, "quote": needle}


def knee_joint(model: Path, side: str) -> dict:
    tree = ET.parse(model)
    joint = next(j for j in tree.iter("CustomJoint") if j.get("name") == f"walker_knee_{side}")
    coord = next(c for c in joint.iter("Coordinate") if c.get("name") == f"knee_angle_{side}")
    rot1 = next(t for t in joint.iter("TransformAxis") if t.get("name") == "rotation1")
    return {
        "model_name": tree.getroot().find("Model").get("name"),
        "joint": f"walker_knee_{side}",
        "coordinate_range_rad": [float(v) for v in coord.findtext("range").split()],
        "rotation1_axis": rot1.findtext("axis").split(),
        "joint_xml_sha256": hashlib.sha256(ET.tostring(joint)).hexdigest(),
    }


def mot_header(path: Path) -> dict:
    with path.open("rb") as fh:
        head = fh.read(8192).decode("utf-8", errors="replace").splitlines()
    end = next(i for i, l in enumerate(head) if l.strip().lower() == "endheader")
    labels = head[end + 1].split("\t")
    return {"path": str(path.relative_to(SOURCE)), "size_bytes": path.stat().st_size,
            "header": [l for l in head[:end] if l.strip()], "labels_1_based": {i + 1: n for i, n in enumerate(labels)},
            "scope": "header lines only; no sample rows parsed"}


def sheet_rows(path: Path, name: str | None = None) -> tuple[list, list]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[name] if name else wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    return wb.sheetnames, rows


def masses() -> dict:
    anth = G120 / "Anthropometric_Data_Participants.xlsx"
    demo = PUBLISHER / "Subject_Demographics.xlsx"
    names, yg = sheet_rows(anth, "YG")
    _, og = sheet_rows(anth, "OG")
    _, dem = sheet_rows(demo)
    head, yg = yg[0], yg[1:]
    ids = [r[0] for r in yg]
    dem_by = {r[0]: r for r in dem[1:]}
    mass = {r[0]: r[2] for r in yg}
    mismatch_mass = [k for k in ids if k not in dem_by or abs(dem_by[k][4] - mass[k]) > 1e-9]
    mismatch_height = [k for k in ids if k not in dem_by or abs(dem_by[k][3] * 1000 - [r for r in yg if r[0] == k][0][1]) > 1e-6]
    og_matches = {r[0]: [k for k, d in dem_by.items() if abs(d[4] - r[2]) < 1e-9 and abs(d[3] * 1000 - r[1]) < 1e-6]
                  for r in og[1:]}
    m = list(mass.values())
    ages = [r[1] for r in dem[1:]]
    return {
        "spreadsheet": {"path": rel(anth), "sha256": sha(anth), "md5": md5(anth),
                        "figshare_md5_match": md5(anth) == FIGSHARE_MD5["Anthropometric_Data_Participants.xlsx"],
                        "sheets_in_order": names, "columns": list(head)},
        "demographics": {"path": rel(demo), "sha256": sha(demo), "md5": md5(demo),
                         "figshare_md5_match": md5(demo) == FIGSHARE_MD5["Subject_Demographics.xlsx"],
                         "url": "https://ndownloader.figshare.com/files/53167799",
                         "rows": len(dem) - 1, "sex_values": sorted({r[2] for r in dem[1:]})},
        "YG_sheet": {"rows": len(yg), "unique_ids": len(set(ids)),
                     "ids_exactly_S001_to_S120": ids == [f"S{i:03d}" for i in range(1, 121)],
                     "nonpositive_or_missing_values": [r[0] for r in yg if any(v is None or (isinstance(v, (int, float)) and v <= 0) for v in r[1:])],
                     "mass_kg_mean_sd_min_max": [round(st.mean(m), 3), round(st.stdev(m), 3), min(m), max(m)],
                     "height_mm_mean_sd": [round(st.mean([r[1] for r in yg]), 2), round(st.stdev([r[1] for r in yg]), 2)],
                     "subjects_with_mass_75_kg": [k for k, v in mass.items() if v == 75],
                     "S001_to_S010_mass_kg": {k: mass[k] for k in ids[:10]}},
        "YG_vs_demographics": {"mass_mismatches": mismatch_mass, "height_mismatches": mismatch_height,
                               "statement": "Every YG Bodymass(Kg) and Height(mm) equals the separate publisher Subject_Demographics.xlsx BodyMass (Kg) and Height (m) x 1000 for the same subject ID."},
        "demographics_age_mean_sd": [round(st.mean(ages), 2), round(st.stdev(ages), 2), min(ages), max(ages)],
        "paper_cohort": paper_quote(PAPER_TEXT.read_text(), "height: 173.2 ± 5.6 cm, weight: 74.1 ± 12.5 kg"),
        "OG_sheet": {"rows": [list(r) for r in og[1:]], "matches_any_demographics_row": og_matches,
                     "statement": "Second sheet has two rows labelled S001 and S002 whose values match no participant in Subject_Demographics.xlsx and differ from YG S001/S002. Meaning of YG/OG is not documented in the paper or figshare description. Not used."},
        "converter_sheet_selection": find_lines(G120 / "scale_model.py", r"read_excel"),
        "converter_selection_note": "pd.read_excel without sheet_name reads the first sheet, which is YG; the choice is implicit.",
    }


def inventory_and_listing() -> dict:
    inv = json.loads(INVENTORY.read_text())
    recs = inv["recordings"]
    pat = re.compile(r"^(S\d{3})/JointAngle/(\w+)/(Trial\d{2})/(step\d{2})\.mot$")
    parsed = [pat.match(r).groups() for r in recs]
    by_task = collections.Counter(p[1] for p in parsed)
    trials = collections.defaultdict(set)
    for s, t, tr, stp in parsed:
        trials[(s, t)].add(int(tr[5:]))
    gaps = sorted(f"{s} {t} trials {sorted(v)}" for (s, t), v in trials.items()
                  if sorted(v) != list(range(1, len(v) + 1)))  # a gap or not starting at Trial01
    subjects = sorted({p[0] for p in parsed})
    missing = [f"{s} {t}" for s in subjects for t in TASKS if (s, t) not in trials]
    fewer = {t: sorted(s for s in subjects if (s, t) in trials and len(trials[(s, t)]) < 5) for t in TASKS}
    # Current source listing (names only).
    ja, trc, mot, mot_case, nostatic = set(), set(), set(), collections.Counter(), []
    for i in range(1, 121):
        s = f"S{i:03d}"
        for dp, _, fn in os.walk(SOURCE / s / "JointAngle"):
            ja.update(str(Path(dp, f).relative_to(SOURCE)) for f in fn)
        mc = SOURCE / s / "MotionCapture"
        for t in sorted(os.listdir(mc)):
            if t == "Static":
                if not os.listdir(mc / t / "TRC"):
                    nostatic.append(s)
                continue
            for kind, dst in (("TRC", trc), ("MOT", mot)):
                p = mc / t / kind
                if not p.is_dir():
                    continue
                for tr in os.listdir(p):
                    for f in os.listdir(p / tr):
                        if kind == "MOT":
                            mot_case[re.sub(r"\d", "#", f)] += 1
                        dst.add(f"{s}/{t}/{tr}/{Path(f).stem}".lower())
    ja_key = {f"{r.split('/')[0]}/{r.split('/')[2]}/{r.split('/')[3]}/{Path(r).stem}".lower() for r in recs}
    expected_mot = {k for k in ja_key if int(k[1:4]) >= 11 and k.split("/")[1] in ("levelwalking", "sittostand", "standtosit")}
    return {
        "inventory": {"path": rel(INVENTORY), "sha256": sha(INVENTORY), "records": len(recs),
                      "subjects": len(subjects), "unsupported_source_paths": inv["unsupported_source_paths"],
                      "nonmatching_names": len(recs) - len(parsed)},
        "records_by_task_vs_paper": {t: {"inventory": by_task[t], "paper": PAPER_CYCLES[t]} for t in TASKS},
        "paper_counts": paper_quote(PAPER_TEXT.read_text(), "includes 6,882 movement (or gait) cycles from seven different tasks"),
        "steps_per_trial": {t: dict(collections.Counter(
            collections.Counter((p[0], p[2]) for p in parsed if p[1] == t).values())) for t in TASKS},
        "subject_task_absent": missing,
        "subjects_with_fewer_than_5_trials": {t: v for t, v in fewer.items() if v},
        "trial_numbers_noncontiguous": gaps,
        "paper_removal_statement": paper_quote(PAPER_TEXT.read_text(), "trials with missing motion capture markers and abnormal sEMG signals were manually identified and removed from the dataset"),
        "current_listing": {
            "jointangle_files": len(ja), "jointangle_equals_inventory": ja == set(recs),
            "trc_files": len(trc), "trc_matches_jointangle_case_insensitive": trc == ja_key,
            "force_mot_files": len(mot), "force_mot_name_patterns": dict(mot_case),
            "force_mot_equals_S011_S120_level_walking_and_transfers": mot == expected_mot,
            "force_mot_in_S001_S010": sorted(k for k in mot if int(k[1:4]) <= 10),
            "empty_static_trc_folders": nostatic,
            "scope": "Names only via os.walk/listdir under nice/ionice; no file contents.",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    text = PAPER_TEXT.read_text()
    code_zip = PUBLISHER / "Matlab_Codes_for_Processing.zip"
    with zipfile.ZipFile(code_zip) as zf:
        vis = zf.read(next(n for n in zf.namelist() if n.endswith("dataVisualizer.m"))).decode("utf-8", errors="replace")
    vis_lines = vis.splitlines()
    conv = G120 / "convert_gait120_to_parquet.py"
    pipe = ROOT / "contributor_tools/common/opensim_pipeline.py"
    invd = ROOT / "contributor_tools/common/opensim_inverse_dynamics.py"
    ja_header = mot_header(SOURCE / "S001/JointAngle/LevelWalking/Trial01/step01.mot")
    force_header = mot_header(SOURCE / "S011/MotionCapture/LevelWalking/MOT/Trial01/Step01.mot")
    knee = {
        "question": "Is the stored Gait120 knee_angle_r/_l extension-positive (converter negates it) or flexion-positive (bundled .osim range 0 to 2.09 rad)?",
        "answer_right": "Stored knee_angle_r is extension-positive. The converter's negation gives knee flexion positive, as rule B requires. The bundled .osim is a lab-modified Rajagopal2016 copy, not the authors' model, and says nothing about the stored sign.",
        "answer_left": "Not checked. No source document states the left knee sign; the converter also negates knee_angle_l. Bounded probe written, not run.",
        "evidence": [
            {"claim": "Paper Fig. 4 caption: positive right-limb knee values are extension.",
             **paper_quote(text, "Positive values indicate hip flexion, hip adduction, hip internal rotation, knee extension, and ankle dorsiflexion.")},
            {"claim": "Authors used a modified Rajagopal model with one knee rotational DOF (not the published walker knee).",
             **paper_quote(text, "The analysis used a modified Rajagopal model44, with only one rotational degree of freedom in the knee joint.")},
            {"claim": "Publisher plotting code reads .mot column 11 and negates it before labelling it Knee Flexion.",
             "file": "Matlab_Codes_for_Processing.zip/dataVisualizer.m",
             "sha256": hashlib.sha256(vis.encode()).hexdigest(),
             "lines": {i: vis_lines[i - 1].strip() for i in (34, 103, 104, 112)}},
            {"claim": "In a publisher JointAngle file, column 11 is knee_angle_r and the file states inDegrees=yes; the authors' model kept Rajagopal coordinate names, including knee_angle_r_beta.",
             "header": ja_header},
            {"claim": "The bundled rajagopal_gait120.osim is the lab's copy of Rajagopal2016 written by setup_opensim_model.py with --lock-secondary-knee-dofs and re-saved by OpenSim 4.6 (OpenSimDocument Version 40600 vs 40000): knee_angle_r_beta and knee_angle_l_beta are locked there and unlocked in rajagopal_original.osim. The walker-knee joint XML and the 0 to 2.0944 rad flexion-positive knee range are identical in both files, so the conclusion holds: it is not the authors' model.",
             "beta_coordinates_locked": {"rajagopal_gait120.osim": {"knee_angle_r_beta": True, "knee_angle_l_beta": True}, "rajagopal_original.osim": {"knee_angle_r_beta": False, "knee_angle_l_beta": False}},
             "rajagopal_gait120": {s: knee_joint(G120 / "rajagopal_gait120.osim", s) for s in ("r", "l")},
             "rajagopal_original": {s: knee_joint(G120 / "rajagopal_original.osim", s) for s in ("r", "l")},
             "setup_script_lines": find_lines(G120 / "setup_opensim_model.py", r"rajagopal_original|printToXML|lock-secondary"),
             "lab_notes_line": find_lines(G120 / "CLAUDE.md", r"NOT publicly available")},
            {"claim": "Default converter (publisher angles) negates both knees.",
             "lines": find_lines(conv, r"-knee_(ipsi|contra)_deg")},
        ],
        "second_mode_findings": {
            "scope": "Opt-in --run-ik and --enable-id paths only (lab ID with the flexion-positive Rajagopal copy). The default path runs neither.",
            "knee_angle": {"status": "consistent_with_rule_B",
                           "lines": find_lines(pipe, r"knee_angle_\{|knee_flexion_angle_(ipsi|contra)_rad\"\] = knee")},
            "knee_moment": {"status": "breaks_rule_B_if_used_with_rajagopal",
                            "lines": find_lines(invd, r"knee_flexion_moment_(ipsi|contra)_Nm_kg\"\] = -get_normed"),
                            "reason": "OpenSim ID generalized forces are positive in the coordinate's positive direction (standard OpenSim convention; not re-derived here). With the flexion-positive Rajagopal knee, -knee_angle_*_moment makes knee_flexion_moment positive for an internal extensor moment. Angle and moment in this path use opposite assumptions about the same coordinate.",
                            "data_check": "not checked"},
            "enable_id_path": {"status": "breaks_rule_B",
                               "lines": find_lines(conv, r"^COMPUTE_INVERSE_DYNAMICS = |ik_mot_path=mot_path"),
                               "reason": "Opt-in --enable-id runs ID with ik_mot_path = the publisher's extension-positive JointAngle .mot on the flexion-positive Rajagopal copy, so the knee coordinate is inverted for ID, and extract_sagittal_moments then negates the knee moment as well.",
                               "data_check": "not checked"},
            "default": "Both --run-ik and --enable-id are off by default; the default path computes no moments.",
            "fix_must_be_model_dependent": "The unconditional knee-moment negation is correct only for a flexion-negative knee coordinate (gait2392) and wrong for Rajagopal (flexion-positive). A fix must take the sign from the model's knee coordinate, not change the shared helper unconditionally.",
            "lab_notes": find_lines(G120 / "CLAUDE.md", r"Knee \| Extension \+"),
        },
    }
    loads = {
        "force_availability_paper": paper_quote(text, "The force plate data for the first ten participants (S001 to S010) are not available because the force plate coordinate system was not correctly aligned with the motion capture system during the experiment."),
        "force_tasks_paper": paper_quote(text, "The force plate data are available only for level walking, sit-to-stand, and stand-to-sit tasks."),
        "units_paper": paper_quote(text, "Force data were recorded in newtons, torque data were recorded in newton-meters (Nm), and moment arms were recorded in meters."),
        "global_axes_paper": paper_quote(text, "with the X-axis pointing anteriorly (forward), Y-axis superiorly (upward), and Z-axis laterally (to the right)."),
        "force_header_example": force_header,
        "plate_to_foot_assignment": "not checked: files carry ground_force1_* and ground_force2_* with no body or foot name; no source ExternalLoads setup is published.",
        "converter_force_handling": find_lines(conv, r"source_plate\{plate\}|force_mapping_status|source_cop_frame"),
        "filename_case": "JointAngle files are step##.mot; MotionCapture TRC/MOT files are Step##.*. get_grf_mot_path keeps the JointAngle file name, so pairing works on this case-insensitive drvfs mount and would silently find no force on a case-sensitive file system.",
        "filename_case_lines": find_lines(conv, r"grf_path = Path\(|if grf_path.exists"),
        "mount": "S: drive on /mnt/s is drvfs (Windows, case-insensitive lookups); both step01.mot and Step01.mot resolve.",
    }
    legacy = {
        "finding": "converted_datasets/gait120_phase_clean.parquet stores weight_kg 75.0 for all of S001-S010 (remaining.json finding 'Stored body mass disagrees with source spreadsheet'); spreadsheet masses are 48.2 to 85 kg.",
        "source": "docs/quality/audits/remaining.json",
        "current_converter_fallbacks": find_lines(conv, r"75\.0|= 75\b|1\.70"),
        "current_converter_missing_mass_lines": find_lines(conv, r"Measured mass and height are required|subject_mass_kg = np.nan"),
        "status": "legacy_quarantined: not a release candidate; no current code path assigns 75 kg. Not opened in this task.",
    }
    out = {
        "task_id": "GA26-C01",
        "status": "conventions_documented_unreviewed",
        "scientific_approval": False,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "builder": {"path": rel(Path(__file__)), "sha256": sha(Path(__file__))},
        "resource_class": "read_only; metadata, headers and directory names only; no sample rows; no jobs launched",
        "inputs_sha256": {rel(p): sha(p) for p in [
            G120 / "s41597-025-05391-0.pdf", PAPER_TEXT, G120 / "rajagopal_gait120.osim", G120 / "rajagopal_original.osim",
            G120 / "Anthropometric_Data_Participants.xlsx", G120 / "setup_opensim_model.py", G120 / "scale_model.py",
            conv, pipe, invd, INVENTORY, code_zip, PUBLISHER / "Subject_Demographics.xlsx",
            ROOT / "contributor_tools/probe_ga26_knee_sign.py"]},
        "publisher_md5_checks": {n: {"expected": m, "match": md5((G120 if n.startswith("Anthropometric") else PUBLISHER) / n) == m}
                                 for n, m in FIGSHARE_MD5.items()},
        "knee_sign": knee,
        "masses": masses(),
        "records_and_ids": inventory_and_listing(),
        "loads": loads,
        "legacy_uniform_75kg": legacy,
        "left_knee_probe_plan": {
            "script": "contributor_tools/probe_ga26_knee_sign.py",
            "tests": "tests/test_ga26_knee_sign_probe.py (synthetic, labeled)",
            "inputs": "21 JointAngle .mot files (3 per task, seed 20261031, lowest trial step01), each <= 2 MiB; about 1.5 MB total",
            "rule": "Transfers: seated frame hip_flexion >= +45 deg anchors posture; knee <= -45 deg extension-positive, >= +45 deg flexion-positive. Gait: min <= -40 and max <= +20 deg extension-positive; mirror for flexion. A side gets a sign only if all 21 agree.",
            "command": "python3 contributor_tools/probe_ga26_knee_sign.py --source-root /mnt/s/locomotion_data/Gait120 --inventory converted_datasets/reconversion_v2/gait120_full_batch_20261020/source_inventory.json --output converted_datasets/reconversion_v2/ga26_c01_20261031/knee_sign_probe.json",
            "launch": "Not run. Through the guarded launcher when the numerical slot is free; it also re-checks the right side.",
            "if_left_is_flexion_positive": "Converter negation of knee_angle_l would break rule B; fix is mechanical (do not negate left).",
        },
        "unresolved": [
            "Left knee sign of the stored files (probe written, not run).",
            "Left hip/ankle signs and every non-sagittal coordinate on the left: no source statement; not checked.",
            "Plate-to-foot assignment and the external-load application point/frame: not documented by the source; not checked.",
            "Meaning of the OG sheet (two rows labelled S001/S002 that match no participant).",
            "--run-ik and --enable-id knee moment sign with the Rajagopal copy (code-level findings; not checked on data; both off by default; fix must be model-dependent).",
            "Global segment orientation of the authors' modified model: the model is unpublished; Fig. 4 is right-limb joint angles only.",
        ],
    }
    args.output.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {rel(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
