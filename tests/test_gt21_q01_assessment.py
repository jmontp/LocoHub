"""GT21-Q01 assessment tests. SYNTHETIC fixtures (made-up export with known injected values); no scientific dataset is read.

Known values: one 800-sample time recording at 200 Hz from t=10 s with a 60 degree jump of the left knee between samples
100 and 101 (t=10.5 -> 10.505), three zero-vertical-force samples with ankle moment 0.5, and three phase cycles:
A (10.4-11.4 s, contains the jump) has a hip angle of 200 degrees and a foot angle of 4 rad; B (11.5-12.5 s) is clean;
C (12.6-13.6 s, right leg) is loaded late (side check fails)."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from contributor_tools import run_gt21_q01_assessment as g
from contributor_tools import run_gt23_q01_assessment as q
from contributor_tools import run_um21_q01v3_assessment as um

PHASE_COLS = ["pelvis_sagittal_angle_rad"] + [f"{s}_sagittal_angle_{r}_rad" for s in ("thigh", "shank", "foot") for r in ("ipsi", "contra")] \
    + [f"{j}_angle_{r}_rad" for j in ("hip_flexion", "knee_flexion", "ankle_dorsiflexion") for r in ("ipsi", "contra")] \
    + [f"{j}_velocity_{r}_rad_s" for j in ("hip_flexion", "knee_flexion", "ankle_dorsiflexion") for r in ("ipsi", "contra")] \
    + [f"{j}_moment_{r}_Nm_kg" for j in ("hip_flexion", "knee_flexion", "ankle_dorsiflexion") for r in ("ipsi", "contra")] \
    + [f"grf_{d}_{r}_BW" for d in ("vertical", "anterior", "lateral") for r in ("ipsi", "contra")] \
    + [f"cop_{d}_{r}_m" for d in ("anterior", "vertical", "lateral") for r in ("ipsi", "contra")]
TIME_COLS = [c.replace("_ipsi_", "_left_").replace("_contra_", "_right_") for c in PHASE_COLS]
SUBJ = "AB99"
REC = f"{SUBJ}/levelground/lg_1"
META = json.dumps({"body_weight_N": 700.0, "body_mass_kg": 71.4})


def table(kind, n, ids, cols, start, end, axis, overrides, held=None, task=("level_walking", "level"), ref="left"):
    d = {"subject": [SUBJ] * n, "source_recording_id": [REC] * n, "observation_id": [ids] * n,
         "reference_side": [ref] * n, "observation_type": ["continuous_recording" if kind == "time" else "individual_cycle"] * n,
         "task": [task[0]] * n, "task_id": [task[1]] * n, "task_info": [json.dumps({"flags": [], "limits": [], "treadmill": False,
                                                                                     "stance_samples": 5})] * n,
         "subject_metadata": [META] * n, ("time_s" if kind == "time" else "phase_ipsi"): list(axis),
         "source_start_time_s": [start] * n, "source_end_time_s": [end] * n, "held_signals": [json.dumps(held or {})] * n}
    for c in cols:
        d[c] = np.zeros(n)
    for c, v in overrides.items():
        d[c] = np.asarray(v, dtype=float)
    return d


def concat(parts):
    return {k: np.concatenate([np.asarray(p[k]) for p in parts]) if not isinstance(parts[0][k], list)
            else sum((p[k] for p in parts), []) for k in parts[0]}


def write(path, parts):
    d = concat(parts)
    pq.write_table(pa.table({k: (pa.array(v) if isinstance(v, list) else pa.array(np.asarray(v))) for k, v in d.items()}), path,
                   row_group_size=97)


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    root = tmp_path_factory.mktemp("gt21q01") / "export"
    root.mkdir()
    t = 10.0 + np.arange(800) / 200.0
    knee = np.zeros(800)
    knee[101:] = np.radians(60.0)
    gv = np.full(800, 1.0)
    gv[200:203] = 0.0
    mom = np.zeros(800)
    mom[200:203] = 0.5
    tparts = [table("time", 800, f"{REC}/continuous", TIME_COLS, t[0], t[-1], t,
                    {"knee_flexion_angle_left_rad": knee, "grf_vertical_left_BW": gv, "ankle_dorsiflexion_moment_left_Nm_kg": mom},
                    ref="none", task=("continuous_recording", "levelground_recording"))]
    write(root / "time.parquet", tparts)
    ph = np.linspace(0, 100, 150)
    early = np.where(np.arange(150) < 60, 1.0, 0.0)
    late = early[::-1]
    hip = np.zeros(150)
    hip[10] = np.radians(200.0)
    foot = np.zeros(150)
    foot[20] = 4.0
    a = table("phase", 150, f"{SUBJ}/levelground/lg_1/left/0000", PHASE_COLS, 10.4, 11.4, ph,
              {"hip_flexion_angle_ipsi_rad": hip, "foot_sagittal_angle_ipsi_rad": foot, "grf_vertical_ipsi_BW": early})
    a["source_recording_id"] = [REC] * 150
    b = table("phase", 150, f"{SUBJ}/levelground/lg_1/left/0001", PHASE_COLS, 11.5, 12.5, ph,
              {"grf_vertical_ipsi_BW": early, "cop_anterior_contra_m": np.full(150, np.nan)},
              held={"cop_anterior_contra_m": "no force"})
    c = table("phase", 150, f"{SUBJ}/levelground/lg_1/right/0002", PHASE_COLS, 12.6, 13.6, ph,
              {"grf_vertical_ipsi_BW": late}, ref="right")
    write(root / "phase.parquet", [a, b, c])
    lin = [{"table": "time", "observation_id": f"{REC}/continuous", "reference_side": "none", "rows": 800, "start_s": t[0], "end_s": t[-1],
            "observation_type": "continuous_recording", "source_recording_id": REC, "subject": SUBJ, "held_signals": []}]
    for oid, side, s, e in ((f"{SUBJ}/levelground/lg_1/left/0000", "left", 10.4, 11.4), (f"{SUBJ}/levelground/lg_1/left/0001", "left", 11.5, 12.5),
                            (f"{SUBJ}/levelground/lg_1/right/0002", "right", 12.6, 13.6)):
        lin.append({"table": "phase", "observation_id": oid, "reference_side": side, "rows": 150, "start_s": s, "end_s": e,
                    "observation_type": "individual_cycle", "source_recording_id": REC, "subject": SUBJ,
                    "task": "level_walking", "task_id": "level", "held_signals": []})
    (root / "observations.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lin))
    for n in ("exclusions.jsonl", "recordings.jsonl"):
        (root / n).write_text("")
    rs = {"time_rows": 800, "phase_rows": 450, "phase_observations": 3, "continuous_observations": 1,
          "sha256": {n: hashlib.sha256((root / n).read_bytes()).hexdigest()
                     for n in ("phase.parquet", "time.parquet", "observations.jsonl", "exclusions.jsonl", "recordings.jsonl")}}
    (root / "run_summary.json").write_text(json.dumps(rs))
    audit = {f"{SUBJ}/levelground/lg_1/left/0001": {"subject": SUBJ, "unavailable": False, "stance_samples": 3, "force_at_heel_strike_N": 100.0},
             f"{SUBJ}/levelground/lg_1/right/0002": {"subject": SUBJ, "unavailable": True, "stance_samples": None, "force_at_heel_strike_N": 200.0}}
    out = root.parent / "out"
    a = g.assess_participant(SUBJ, root, out, audit)
    rows = {(d["table"], d["observation_id"]): d for d in map(json.loads, (out / "assessment.jsonl").read_text().splitlines())}
    return a, rows, out


def test_limits_equal_the_other_datasets():
    assert q.L1_BOUNDS_DEG == {"hip_flexion_angle_": (-50.0, 150.0), "knee_flexion_angle_": (-30.0, 165.0), "ankle_dorsiflexion_angle_": (-80.0, 50.0)}
    assert (q.L2_JUMP_DEG, q.L5_BOUNDS_M) == (30.0, {"cop_anterior_": (-0.5, 0.5), "cop_vertical_": (-0.3, 0.3), "cop_lateral_": (-0.3, 0.3)})
    assert tuple(um.L1_BOUNDS_DEG.values()) == tuple(q.L1_BOUNDS_DEG.values())
    assert um.L2_JUMP_DEG == q.L2_JUMP_DEG and um.PLANE_GLITCH_DEG == 60.0


def test_problem_free_fixture(world):
    a, rows, _ = world
    assert a["table_problems"] == []
    assert a["counts"]["observations"] == 4


def test_time_jump_is_found_and_mapped_to_the_span_that_contains_it(world):
    _, rows, _ = world
    tm = rows[("time", f"{REC}/continuous")]
    assert tm["attributes"]["checks"]["L2"] == "failed" and tm["failed_samples"]["knee_flexion_angle_left_rad"]["L2"] == 1
    pa_ = rows[("phase", f"{SUBJ}/levelground/lg_1/left/0000")]
    assert pa_["attributes"]["checks"]["L2"] == "failed"
    assert pa_["failed_samples"]["knee_flexion_angle_ipsi_rad"] == {"L2": 1}
    pb = rows[("phase", f"{SUBJ}/levelground/lg_1/left/0001")]
    assert pb["attributes"]["checks"]["L2"] == "passed"
    assert "L2" not in pb["failed_limits"]


def test_l1_and_wrap_flag_on_phase_a(world):
    _, rows, _ = world
    e = rows[("phase", f"{SUBJ}/levelground/lg_1/left/0000")]
    assert e["failed_samples"]["hip_flexion_angle_ipsi_rad"] == {"L1": 1}
    assert e["status"] == "failed" and e["attributes"]["checks"]["L1"] == "failed"
    assert e["attributes"]["angle_samples_beyond_pi"] == 2     # 200 degrees and 4 rad (229 degrees)
    assert "angle_samples_beyond_pi" in e["limitations"]
    assert e["attributes"]["angle_range_deg"]["foot_sagittal_angle_ipsi_rad"][1] == pytest.approx(229.183, abs=1e-3)


def test_clean_cycle_is_not_called_pass_but_no_failure_found(world):
    _, rows, _ = world
    e = rows[("phase", f"{SUBJ}/levelground/lg_1/left/0001")]
    assert e["status"] == "no_failure_found"
    assert e["attributes"]["checks"]["P1"] == "unchecked"
    assert e["attributes"]["checks"]["L4"] == "missing"       # the held cop column is missing, not a pass
    assert "cop_anterior_contra_m" in e["channel_states"]["missing"]
    assert e["held_signals"] == {"cop_anterior_contra_m": "no force"}
    assert "ankle_dorsiflexion_moment_ipsi_Nm_kg" in e["channel_states"]["unchecked"]
    assert e["attributes"]["checks"]["S5"] == "passed"


def test_plate_dropout_counts_three_samples_and_does_not_change_status(world):
    _, rows, _ = world
    tm = rows[("time", f"{REC}/continuous")]
    assert tm["attributes"]["checks"]["PD"] == "failed"
    assert tm["attributes"]["plate_dropout"]["left"]["samples"] == 3
    assert tm["attributes"]["plate_dropout"]["left"]["first_sample_indices"] == [200, 201, 202]
    assert "plate_dropout_samples" in tm["limitations"]
    assert tm["failed_limits"] == ["L2"]                    # status comes from L2 only
    assert rows[("phase", f"{SUBJ}/levelground/lg_1/left/0001")]["attributes"]["checks"]["PD"] == "passed"   # finite pairs, no dropout


def test_side_check_uses_body_weight_and_fails_a_late_loaded_cycle(world):
    _, rows, _ = world
    c = rows[("phase", f"{SUBJ}/levelground/lg_1/right/0002")]
    assert c["attributes"]["checks"]["S5"] == "failed" and c["status"] == "failed"
    assert c["attributes"]["S5_late_mean_N"] == pytest.approx(700.0) and c["attributes"]["S5_early_mean_N"] == pytest.approx(0.0)


def test_short_stance_flags_are_kept_not_dropped(world):
    a, rows, _ = world
    b = rows[("phase", f"{SUBJ}/levelground/lg_1/left/0001")]
    c = rows[("phase", f"{SUBJ}/levelground/lg_1/right/0002")]
    assert "early_source_heel_strike_short_left_stance" in b["limitations"]
    assert "left_stance_unavailable_no_toe_off" in c["limitations"]
    assert len(a["short_left_stances"]) == 2 and a["table_problems"] == []
    assert a["short_stance_accounting"]["unaccounted"] == [] and len(a["short_stance_accounting"]["flagged_in_phase_table"]) == 2


def test_held_frames_are_counted(world):
    a, rows, _ = world
    assert a["held_frames"]["rows_by_table"] == {"time": 800, "phase": 450}
    assert a["held_frames"]["rows_with_a_missing_angle_by_table"] == {"time": 0, "phase": 0}


def test_unknown_unit_suffix_refuses():
    with pytest.raises(q.UnitError):
        q.unit_of("hip_flexion_angle_ipsi_deg")


def test_phase_channel_roles():
    assert g.phase_channel("knee_flexion_angle_left_rad", "left") == "knee_flexion_angle_ipsi_rad"
    assert g.phase_channel("knee_flexion_angle_left_rad", "right") == "knee_flexion_angle_contra_rad"
    assert g.phase_channel("pelvis_sagittal_angle_rad", "left") == "pelvis_sagittal_angle_rad"


def test_wrong_grid_fails_s1():
    cols = PHASE_COLS
    key = ("AB99/levelground/lg_1/left/0009", "left")
    obs = g.Obs(key, "phase", cols, {c: g.column_limits(c, True) for c in cols})
    n = 149
    data = {c: np.zeros(n) for c in cols}
    data.update({"phase_ipsi": np.linspace(0, 100, n), "source_start_time_s": np.full(n, 1.0), "source_end_time_s": np.full(n, 2.0)})
    strings = {"subject": SUBJ, "source_recording_id": REC, "observation_type": "individual_cycle", "task": "x", "task_id": "y",
               "task_info": "{}", "subject_metadata": META, "held_signals": "{}"}
    obs.feed(data, strings, 0, n)
    entry, _ = g.finish_observation(obs, {}, SUBJ, {}, {})
    assert entry["attributes"]["checks"]["S1"] == "failed" and entry["status"] == "failed"
    assert entry["attributes"]["checks"]["S5"] == "unchecked"


def test_listed_stride_excluded_in_export_is_accounted_not_a_problem(world, tmp_path):
    import shutil
    root = tmp_path / "export"
    shutil.copytree(Path(world[2]).parent / "export", root)
    sid = f"{SUBJ}/treadmill/t_1/left/0101"
    (root / "exclusions.jsonl").write_text(json.dumps({"step_id": sid, "reason": "authors_rule_discard: test"}) + "\n")
    rs = json.loads((root / "run_summary.json").read_text())
    rs["sha256"]["exclusions.jsonl"] = hashlib.sha256((root / "exclusions.jsonl").read_bytes()).hexdigest()
    (root / "run_summary.json").write_text(json.dumps(rs))
    audit = {sid: {"subject": SUBJ, "unavailable": False, "stance_samples": 3, "force_at_heel_strike_N": 1.0}}
    a = g.assess_participant(SUBJ, root, tmp_path / "o", audit)
    acc = a["short_stance_accounting"]
    assert a["table_problems"] == [] and acc["excluded_in_export_with_reason"] == {sid: "authors_rule_discard: test"}
    audit2 = {sid.replace("0101", "0999"): audit[sid]}
    b = g.assess_participant(SUBJ, root, tmp_path / "o2", audit2)
    assert b["short_stance_accounting"]["unaccounted"] and b["table_problems"]
