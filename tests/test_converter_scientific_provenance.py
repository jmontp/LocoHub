"""Small executed converter regressions; no source datasets or GPU imports."""

import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest
from scipy.io import savemat


CONVERTERS = Path(__file__).resolve().parents[1] / "contributor_tools" / "conversion_scripts"


def load_converter(relative_path, monkeypatch):
    path = CONVERTERS / relative_path
    monkeypatch.syspath_prepend(str(path.parent))
    spec = importlib.util.spec_from_file_location(f"fixture_{path.parent.name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def um24(monkeypatch):
    return load_converter("UMich_2024_KneeExo/convert_umich_2024_phase_to_parquet.py", monkeypatch)


def ensemble_source(tasks=("LW",)):
    curve = np.linspace(0.0, 30.0, 101)[:, None] * np.ones((1, 10))
    return {
        name: {task: curve.copy() for task in tasks}
        for name in ("kneeAngle", "thighAngle", "shankAngle", "torque", "grf")
    }


def test_ensemble_is_not_a_timed_stride(um24):
    frames = um24.process_task(ensemble_source(), "LW", "level_walking", "level", "assistance:exo_worn")
    result = pd.concat(frames)
    assert result.observation_id.nunique() == 10
    assert set(result.observation_type) == {"ensemble_curve"}
    assert set(result.reference_side) == {"unknown"}
    assert set(result.source_sample_count) == {101}
    assert all(frame.phase_ipsi.iloc[[0, -1]].tolist() == [0.0, 100.0] for frame in frames)
    derivative_columns = result.filter(regex="_velocity_|_acceleration_")
    assert derivative_columns.isna().all().all()
    np.testing.assert_allclose(frames[0].knee_flexion_angle_ipsi_rad.iloc[-1], np.pi / 6)
    np.testing.assert_allclose(frames[0].exo_torque_knee_ipsi_Nm.iloc[-1], -30.0)
    assert json.loads(frames[0].task_info.iloc[0])["timing"] == "unavailable"


def test_ensemble_mat_to_parquet_round_trip(um24, monkeypatch, tmp_path, capsys):
    source = tmp_path / "dataset_S1.mat"
    savemat(source, {"exo": ensemble_source(um24.TASK_MAPPING)})
    monkeypatch.setattr(sys, "argv", ["convert", "--input", str(source), "--output-dir", str(tmp_path)])
    um24.main()
    result = pd.read_parquet(tmp_path / "umich_2024_knee_exo_phase.parquet")
    assert result.observation_id.nunique() == 60
    assert result.groupby("observation_id").size().eq(150).all()
    output = capsys.readouterr().out
    assert "Total ensemble curves: 60" in output
    assert "Total strides:" not in output


@pytest.fixture
def gt24(monkeypatch):
    return load_converter("GaTech_2024_TaskAgnostic/convert_gtech_2024_phase_to_parquet.py", monkeypatch)


def gait_source():
    time = np.linspace(0.0, 1.0, 201)
    angles = {"time": time}
    moments, forces, cop = {}, {}, {}
    for side in ("l", "r"):
        for joint in ("hip_flexion", "knee_angle", "ankle_angle"):
            angles[f"{joint}_{side}"] = 2 * time
            moments[f"{joint}_{side}_moment"] = np.ones_like(time)
        for axis in ("x", "y", "z"):
            forces[f"fp_{side}_force_{axis}"] = np.full_like(time, 100.0)
        for axis in ("x", "z"):
            cop[f"insole_{side}_cop_{axis}"] = np.zeros_like(time)
    return {
        "angle_filt": pd.DataFrame(angles),
        "moment_filt": pd.DataFrame(moments),
        "grf": pd.DataFrame(forces),
        "insole_sim": pd.DataFrame(cop),
    }


def convert_gt24(gt24, recording, step=0, side="l"):
    return gt24.process_stride(
        gait_source(), 0, 200, "BT01", 70.0, "level_walking", "level",
        {}, step, side, 1, "no_exo", source_recording_id=recording,
        skip_segment_angles=True,
    )


def test_gt24_identity_distinguishes_trials_and_survives_counter_changes(gt24):
    first = convert_gt24(gt24, "gt24:Parsed/BT01/trial_A", step=0)
    repeated = convert_gt24(gt24, "gt24:Parsed/BT01/trial_A", step=123)
    other_trial = convert_gt24(gt24, "gt24:Parsed/BT01/trial_B", step=0)
    other_leg = convert_gt24(gt24, "gt24:Parsed/BT01/trial_A", side="r")
    assert first.observation_id.iloc[0] == repeated.observation_id.iloc[0]
    assert len({frame.observation_id.iloc[0] for frame in (first, other_trial, other_leg)}) == 3
    assert first.step.equals(first.observation_id)
    assert first.reference_side.iloc[0] == "left"
    assert first.source_end_time_s.iloc[0] == 1.0
    assert json.loads(first.subject_metadata.iloc[0])["weight_kg"] == 70.0


def test_gt24_derivative_matches_included_endpoint(gt24):
    result = convert_gt24(gt24, "gt24:Parsed/BT01/trial_A")
    np.testing.assert_allclose(result.hip_flexion_angle_ipsi_rad.iloc[-1], np.deg2rad(2.0))
    np.testing.assert_allclose(result.hip_flexion_velocity_ipsi_rad_s, np.deg2rad(2.0), atol=1e-12)
    np.testing.assert_allclose(result.hip_flexion_acceleration_ipsi_rad_s2, 0.0, atol=1e-10)


def test_gt24_unknown_subject_mass_is_unavailable(gt24):
    assert np.isnan(gt24.get_subject_mass("unknown_subject", "Parsed"))


@pytest.fixture
def stroke(monkeypatch):
    return load_converter("StrokePiG/convert_strokepig_to_parquet.py", monkeypatch)


@pytest.mark.parametrize("affected,reference", [("unknown", "l"), ("l", "l"), ("r", "r")])
def test_stroke_clinical_side_is_preserved(stroke, affected, reference):
    metadata = {"mass_kg": 70.0, "affected_side": affected}
    side = stroke.reference_side_for_subject(metadata)
    assert side == reference
    source = gait_source()["angle_filt"]
    source["pelvis_tilt"] = 0.0
    processed = stroke.process_stride(source, 0, 200, side, 70.0, 0)
    result = stroke._build_stride_dataframe(
        processed, None, None, "TVC03", metadata, side,
        processed["stride_duration_s"], 0, "sp50:TVC03/BWA6_ik.mot",
    )
    expected = {"l": "left", "r": "right"}.get(affected, "unknown")
    assert set(result.affected_side) == {expected}
    assert json.loads(result.task_info.iloc[0])["affected_side"] == expected
    assert json.loads(result.subject_metadata.iloc[0])["affected_side"] == expected
    assert result.source_start_sample.iloc[0] == 0
    assert result.source_end_sample.iloc[0] == 199


def test_stroke_missing_channel_remains_missing_and_invalid_time_is_rejected(stroke):
    source = gait_source()["angle_filt"].drop(columns=["hip_flexion_l"])
    result = stroke.process_stride(source, 0, 200, "l", 70.0, 0)
    assert np.isnan(result["hip_flexion_angle_ipsi_rad"]).all()
    source["time"] = 0.0
    assert stroke.process_stride(source, 0, 200, "l", 70.0, 0) is None
