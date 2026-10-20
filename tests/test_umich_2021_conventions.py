"""Regression tests for the UMich 2021 convention corrections."""

from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from contributor_tools.common.validation.validator import Validator
from contributor_tools.common.feature_constants import CANONICAL_COLUMN_GROUPS, TIME_CANONICAL_COLUMNS


TIME_CONVERTER = ROOT / "contributor_tools/conversion_scripts/Umich_2021/convert_umich_time_to_parquet.m"
PHASE_CONVERTER = ROOT / "contributor_tools/conversion_scripts/Umich_2021/convert_umich_phase_to_parquet.m"
DIAGRAM_GENERATOR = ROOT / "contributor_tools/common/plotting/generate_forward_kinematics_reference.py"


def test_forward_kinematics_equations_match_standard_convention():
    source = DIAGRAM_GENERATOR.read_text(encoding="utf-8")

    assert r"\theta_{\mathrm{knee}} = \phi_{\mathrm{thigh}} - \phi_{\mathrm{shank}}" in source
    assert r"\theta_{\mathrm{ankle}} = \phi_{\mathrm{foot}} - \phi_{\mathrm{shank}}" in source
    assert r"\theta_{\mathrm{hip}} = \phi_{\mathrm{thigh}} - \phi_{\mathrm{pelvis}}" in source
    assert "clockwise shank rotation relative to thigh" in source
    foot_block = source[source.index("# Stored \u03c6_foot uses the forward"):source.index("# Center of pressure")]
    assert "start_vec=np.array([1.0, 0.0])" in foot_block
    assert "vertical-down zero" in source
    assert "forward-horizontal zero" in source
    assert "cancel the ankle's anatomical" in source


def test_walking_chain_numerically_satisfies_joint_definitions():
    source = TIME_CONVERTER.read_text(encoding="utf-8")
    assert "right_shank_sag = right_foot_sag - right_ankle_flex;" in source
    assert "right_thigh_sag = right_shank_sag + right_knee_flex;" in source
    assert "right_pelvis_from_chain = right_thigh_sag - right_hip_flex;" in source

    foot, ankle, knee, hip = 0.25, 0.10, 0.55, 0.30
    shank = foot - ankle
    thigh = shank + knee
    pelvis = thigh - hip
    assert np.isclose(knee, thigh - shank)
    assert np.isclose(ankle, foot - shank)
    assert np.isclose(hip, thigh - pelvis)


def test_sts_chain_uses_same_joint_definitions():
    source = PHASE_CONVERTER.read_text(encoding="utf-8")
    assert "foot_ipsi = shank_ipsi + stride_data.ankle_dorsiflexion_angle_ipsi_rad;" in source
    assert "foot_contra = shank_contra + stride_data.ankle_dorsiflexion_angle_contra_rad;" in source

    pelvis, hip, knee, ankle = 0.10, 0.40, 0.30, 0.10
    thigh = pelvis + hip
    shank = thigh - knee
    foot = shank + ankle
    assert np.isclose(hip, thigh - pelvis)
    assert np.isclose(knee, thigh - shank)
    assert np.isclose(ankle, foot - shank)


def test_time_converter_preserves_units_signs_and_axis_mapping():
    source = TIME_CONVERTER.read_text(encoding="utf-8")

    assert "resample_signal(-angles.RKneeAngles" not in source
    assert "right_thigh_sag = right_shank_sag + right_knee_flex;" in source
    assert "left_thigh_sag = left_shank_sag + left_knee_flex;" in source
    assert "Moment(idx, sagittal_plane) ./ body_mass" not in source
    assert "x = 2;" in source
    assert "y = 3;" in source
    assert "z = 1;" in source
    assert "-trial_struct.forceplates.RCoP(force_idx_r, x) ./ 1000" in source
    assert "zero_cop_by_contact(r_cop_anterior, r_cop_lateral, r_cop_vertical" in source
    assert "trial_table = mask_structural_outliers(trial_table);" in source
    assert "r_ankle_anterior" not in source
    assert "sanitize_angle_segment" in source
    for field in ("RPelvisAngles", "LPelvisAngles", "RFootProgressAngles", "LFootProgressAngles"):
        assert field in source[source.index("function [segment_end, is_valid"):]


def test_force_and_cop_axis_transforms_numerically_match_converter():
    raw_force = np.array([100.0, 200.0, -700.0])  # ML-left, AP, vertical-down
    body_weight = 700.0
    anterior = raw_force[1] / body_weight
    vertical = -raw_force[2] / body_weight
    lateral = -raw_force[0] / body_weight
    assert np.allclose([anterior, vertical, lateral], [2 / 7, 1.0, -1 / 7])

    raw_cop_mm = np.array([[50.0, -100.0, 0.0], [20.0, -350.0, 0.0]])
    mapped_cop_m = raw_cop_mm[:, [1, 2, 0]] / 1000
    mapped_cop_m[:, 0] *= -1
    mapped_cop_m[:, 2] *= -1
    contact_relative = mapped_cop_m - mapped_cop_m[0]
    assert np.allclose(contact_relative[0], [0.0, 0.0, 0.0])
    assert np.allclose(contact_relative[1], [0.25, 0.0, 0.03])


def test_phase_converter_assigns_one_unique_id_per_150_row_cycle():
    source = PHASE_CONVERTER.read_text(encoding="utf-8")

    assert "subject_cycles = height(subject_table) / 150;" in source
    assert "subject_table.step = repelem((next_step:next_step + subject_cycles - 1)', 150);" in source
    mixed_path_cycle_counts = [4, 3, 2, 5]
    total_cycles = sum(mixed_path_cycle_counts)
    identifiers = np.repeat(np.arange(1, total_cycles + 1), 150)
    assert len(np.unique(identifiers)) == total_cycles
    assert all(np.count_nonzero(identifiers == cycle) == 150 for cycle in range(1, total_cycles + 1))


def test_time_validator_detects_cross_batch_time_regression(tmp_path):
    dataset = tmp_path / "cross_batch_time.parquet"
    pd.DataFrame(
        {
            "subject": ["UM21_AB01"] * 5,
            "task": ["level_walking"] * 5,
            "task_id": ["level_1ms"] * 5,
            "task_info": ["speed_m_s:1.0"] * 5,
            "step": [1] * 5,
            "time_s": [0.0, 0.005, 0.010, 0.010, 0.015],
        }
    ).to_parquet(dataset, index=False)

    result = Validator(time_batch_size=3, time_column_chunk_size=1).validate(str(dataset))

    assert result["schema_passed"] is False
    assert "time_s_not_strictly_increasing" in result["violations"]["level_walking"]


def test_umich_converters_write_and_merge_bounded_shards():
    time_source = TIME_CONVERTER.read_text(encoding="utf-8")
    phase_source = PHASE_CONVERTER.read_text(encoding="utf-8")

    for source in (time_source, phase_source):
        assert "merge_parquet_shards" in source
        assert "--row-group-size 65536" in source
        assert "UMICH_STREAMING_SUBJECT_DIR" in source
    assert "total_data = [total_data; subject_rows]" not in time_source
    assert "total_data = append_stride_data(total_data, stride_table);" not in phase_source


def test_validator_dispatches_time_only_dataset_without_phase_column(tmp_path):
    dataset = tmp_path / "minimal_time.parquet"
    pd.DataFrame(
        {
            "subject": ["UM21_AB01"] * 3,
            "task": ["level_walking"] * 3,
            "task_id": ["level_1ms"] * 3,
            "task_info": ["speed_m_s:1.0"] * 3,
            "step": [1] * 3,
            "time_s": [0.0, 0.005, 0.010],
        }
    ).to_parquet(dataset, index=False)

    result = Validator().validate(str(dataset))

    assert result["mode"] == "time"
    assert result["schema_passed"] is True
    assert result["phase_valid"] is True


def test_time_validator_rejects_non_increasing_segment_time(tmp_path):
    dataset = tmp_path / "bad_time.csv"
    pd.DataFrame(
        {
            "subject": ["UM21_AB01"] * 3,
            "task": ["level_walking"] * 3,
            "task_id": ["level_1ms"] * 3,
            "task_info": ["speed_m_s:1.0"] * 3,
            "step": [1] * 3,
            "time_s": [0.0, 0.005, 0.005],
        }
    ).to_csv(dataset, index=False)

    result = Validator().validate(str(dataset))

    assert result["mode"] == "time"
    assert result["schema_passed"] is False
    assert "time_s_not_strictly_increasing" in result["violations"]["level_walking"]


def test_time_validator_rejects_nonfinite_and_extreme_biomechanics(tmp_path):
    dataset = tmp_path / "corrupt_time.parquet"
    pd.DataFrame(
        {
            "subject": ["UM21_AB01"] * 3,
            "task": ["level_walking"] * 3,
            "task_id": ["level_1ms"] * 3,
            "task_info": ["speed_m_s:1.0"] * 3,
            "step": [1] * 3,
            "time_s": [0.0, 0.005, 0.010],
            "knee_flexion_angle_ipsi_rad": [0.1, np.inf, 0.2],
            "knee_flexion_velocity_ipsi_rad_s": [0.0, 999_999.0, -999_999.0],
        }
    ).to_parquet(dataset, index=False)

    result = Validator().validate(str(dataset))

    task_violations = result["violations"]["level_walking"]
    assert result["schema_passed"] is False
    assert "knee_flexion_angle_ipsi_rad_infinite" in task_violations
    assert any(name.startswith("knee_flexion_velocity_ipsi_rad_s_outside_structural_limit") for name in task_violations)


def test_time_validator_uses_configured_structural_limits(tmp_path):
    ranges = tmp_path / "ranges.yaml"
    ranges.write_text(
        "version: '2.0'\n"
        "time_structural_abs_limits:\n"
        "  joint_angles: 0.5\n"
        "tasks: {}\n",
        encoding="utf-8",
    )
    dataset = tmp_path / "configured_limit_time.csv"
    pd.DataFrame(
        {
            "subject": ["UM21_AB01"],
            "task": ["level_walking"],
            "task_id": ["level_1ms"],
            "task_info": ["speed_m_s:1.0"],
            "step": [1],
            "time_s": [0.0],
            "knee_flexion_angle_ipsi_rad": [0.75],
        }
    ).to_csv(dataset, index=False)

    result = Validator(config_path=ranges).validate(str(dataset))

    assert result["schema_passed"] is False
    assert "knee_flexion_angle_ipsi_rad_outside_structural_limit_0.5" in result["violations"]["level_walking"]


def test_time_validator_allows_nan_placeholders_for_optional_signals(tmp_path):
    dataset = tmp_path / "optional_nan_time.parquet"
    pd.DataFrame(
        {
            "subject": ["UM21_AB01"] * 3,
            "task": ["stair_ascent"] * 3,
            "task_id": ["stairs_20deg"] * 3,
            "task_info": ["incline_deg:20"] * 3,
            "step": [1] * 3,
            "time_s": [0.0, 0.005, 0.010],
            "knee_flexion_moment_ipsi_Nm_kg": [np.nan] * 3,
            "grf_vertical_ipsi_BW": [np.nan] * 3,
        }
    ).to_parquet(dataset, index=False)

    result = Validator().validate(str(dataset))

    assert result["schema_passed"] is True
    assert result["violations"] == {}


def test_full_canonical_multiplane_fields_are_scanned(tmp_path):
    assert "hip_adduction_angle_ipsi_rad" in CANONICAL_COLUMN_GROUPS["joint_angles"]
    assert "hip_rotation_velocity_ipsi_rad_s" in CANONICAL_COLUMN_GROUPS["joint_velocities"]
    assert "hip_adduction_angle_ipsi_rad" in TIME_CANONICAL_COLUMNS

    dataset = tmp_path / "corrupt_multiplane_time.parquet"
    pd.DataFrame(
        {
            "subject": ["UM21_AB01"] * 2,
            "task": ["level_walking"] * 2,
            "task_id": ["level_1ms"] * 2,
            "task_info": ["speed_m_s:1.0"] * 2,
            "step": [1] * 2,
            "time_s": [0.0, 0.005],
            "hip_adduction_angle_ipsi_rad": [0.1, -np.inf],
            "hip_rotation_velocity_ipsi_rad_s": [0.0, 999_999.0],
        }
    ).to_parquet(dataset, index=False)

    result = Validator().validate(str(dataset))
    task_violations = result["violations"]["level_walking"]

    assert result["schema_passed"] is False
    assert "hip_adduction_angle_ipsi_rad_infinite" in task_violations
    assert any(
        name.startswith("hip_rotation_velocity_ipsi_rad_s_outside_structural_limit")
        for name in task_violations
    )
