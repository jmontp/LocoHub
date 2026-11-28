"""Independent numerical/identity regressions for internal review adapters."""
import json

import numpy as np
import pandas as pd
import pytest

from contributor_tools.common.config_manager import ValidationConfigManager
from contributor_tools.common.dataset_table import DatasetTable, phase_groups, read_review_table
from contributor_tools.common.validation.validator import Validator


SIGNAL = "knee_flexion_angle_ipsi_rad"


def frame():
    return pd.DataFrame({
        "subject": ["A"] * 300, "task": ["level_walking"] * 300,
        "task_id": ["normal"] * 300, "task_info": ["{}"] * 300,
        "step": ["one"] * 150 + ["two"] * 150,
        "phase_ipsi": np.tile(np.linspace(0, 100, 150), 2),
        SIGNAL: np.repeat([0.1, 0.2], 150),
    })


@pytest.fixture
def validator(tmp_path):
    profile = tmp_path / "ranges.yaml"
    profile.write_text(
        f"tasks:\n  level_walking:\n    phases:\n      0:\n        {SIGNAL}:\n          min: 0\n          max: 1\n"
    )
    return Validator(profile)


def test_shuffled_rows_preserve_cycle_values_and_phase():
    source = frame().sample(frac=1, random_state=11)
    data = DatasetTable.from_frame(source)
    values, _ = data.get_cycles(task="level_walking", features=[SIGNAL])
    assert sorted(values[:, 0, 0]) == [0.1, 0.2]
    assert all(np.all(cycle == cycle[0]) for cycle in values)
    # No cache: edits of the table are immediately reflected.
    data.df[SIGNAL] = 7.0
    assert (data.get_cycles(task="level_walking", features=[SIGNAL])[0] == 7).all()


def test_149_plus_151_cannot_pass(validator):
    source = frame()
    source.loc[149, "step"] = "two"
    result = validator.validate_dataset(DatasetTable.from_frame(source))
    assert not result["schema_passed"]
    assert not result["quality_gate_passed"]


def test_repeated_legacy_keys_require_reconversion():
    source = frame()
    source["step"] = "one"
    with pytest.raises(ValueError, match="recording/observation"):
        phase_groups(source)


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_nonfinite_is_never_passing(validator, value):
    source = frame()
    source[SIGNAL] = value
    result = validator.validate_dataset(DatasetTable.from_frame(source))
    assert result["stats"]["total_passing_strides"] == 0
    assert not result["quality_gate_passed"]


def test_nonfinite_between_configured_phases_is_detected(validator):
    source = frame()
    source.loc[77, SIGNAL] = np.inf
    result = validator.validate_dataset(DatasetTable.from_frame(source))
    assert result["stats"]["total_failing_strides"] == 1
    assert result["stats"]["total_passing_strides"] == 1


def test_unconfigured_task_is_visible_and_unassessed(validator):
    source = frame()
    source["task"] = "new_task"
    result = validator.validate_dataset(DatasetTable.from_frame(source))
    assert result["stats"]["total_strides"] == 2
    assert result["stats"]["total_unassessed_strides"] == 2
    assert result["stats"]["total_passing_strides"] == 0
    assert result["unassessed_tasks"] == ["new_task"]


def test_missing_required_signal_does_not_disappear(validator):
    result = validator.validate_dataset(DatasetTable.from_frame(frame().drop(columns=SIGNAL)))
    assert result["tasks"]["level_walking"]["unavailable_variables"] == [SIGNAL]
    assert result["stats"]["total_unassessed_strides"] == 2


def test_default_profile_and_missing_file():
    assert Validator().config_manager.get_tasks()
    with pytest.raises(FileNotFoundError):
        Validator("definitely-not-a-profile.yaml")


@pytest.mark.parametrize("bounds", ["min: 2\n          max: 1", "min: .nan\n          max: 1",
                                    "min: 0", "min: true\n          max: 1"])
def test_malformed_profile_rejected(tmp_path, bounds):
    profile = tmp_path / "invalid.yaml"
    profile.write_text(f"tasks:\n  x:\n    phases:\n      0:\n        {SIGNAL}:\n          {bounds}\n")
    with pytest.raises(ValueError):
        ValidationConfigManager(profile)


def test_memory_admission_precedes_pandas_read(tmp_path, monkeypatch):
    path = tmp_path / "tiny.parquet"
    frame().to_parquet(path, index=False)
    monkeypatch.setenv("LOCOHUB_REVIEW_MEMORY_MB", "0")
    monkeypatch.setattr(pd, "read_parquet", lambda *a, **k: pytest.fail("Must not load"))
    with pytest.raises(ValueError, match="positive"):
        read_review_table(path)


def test_velocity_check_uses_actual_phase_spacing():
    from contributor_tools.common.validation.report_generator import ValidationReportGenerator
    source = frame().iloc[:150].copy()
    source[SIGNAL] = np.linspace(0, 1, 150)
    source["phase_ipsi_dot"] = 100.0
    velocity = "knee_flexion_velocity_ipsi_rad_s"
    source[velocity] = 1.0
    # Skip renderer initialization; exercise the numerical check without writing reports.
    renderer = ValidationReportGenerator.__new__(ValidationReportGenerator)
    renderer._log_memory = lambda *args: None
    result = renderer.validate_velocity_consistency(source)[velocity]
    assert result["status"] == "pass"
    assert result["mean_error"] < 1e-12


def test_cli_counts_unassessed_as_unassessed(validator):
    from contributor_tools.quick_validation_check import _compute_task_statistics
    source = frame()
    source[SIGNAL] = np.nan
    table = DatasetTable.from_frame(source)
    result = validator.validate_dataset(table)
    details = _compute_task_statistics(table.data_path, validator, result, table)
    assert details["level_walking"]["passing_strides"] == 0
    assert details["level_walking"]["unassessed_strides"] == 2


def identified_frame():
    source = frame()
    source["source_recording_id"] = "fixture_recording"
    source["observation_id"] = source["step"]
    source["reference_side"] = "left"
    source["observation_type"] = "individual_cycle"
    return source


def test_cleaner_cli_and_release_engine_share_decisions(validator, tmp_path):
    from contributor_tools.common.data_contract import assess_observations
    from contributor_tools.create_clean_dataset import DatasetCleaner
    source = identified_frame()
    source.loc[source.observation_id == "two", SIGNAL] = 5.0
    source = source.sample(frac=1, random_state=31)
    input_path = tmp_path / "source.parquet"
    output_path = tmp_path / "filtered.parquet"
    source.to_parquet(input_path, index=False)
    assessment = assess_observations(source, validator.config_manager)
    review = validator.validate(str(input_path))
    assert review["assessment"] == assessment
    stats = DatasetCleaner(validator).clean_dataset(str(input_path), str(output_path))
    assert stats["clean_strides"] == assessment["counts"]["passed"] == 1
    selected = pd.read_parquet(output_path)
    assert len(selected) == 150
    assert set(selected.observation_id) == {"one"}
    assert pd.read_parquet(input_path).equals(source.reset_index(drop=True))
    report = json.loads(output_path.with_suffix(".parquet.quality.json").read_text())
    assert report["counts"] == assessment["counts"]
    with pytest.raises(FileExistsError):
        DatasetCleaner(validator).clean_dataset(str(input_path), str(output_path))


def test_cleaner_rejects_legacy_before_writing(validator, tmp_path):
    from contributor_tools.create_clean_dataset import DatasetCleaner
    source = tmp_path / "legacy.parquet"
    target = tmp_path / "filtered.parquet"
    frame().to_parquet(source, index=False)
    with pytest.raises(ValueError, match="release contract"):
        DatasetCleaner(validator).clean_dataset(str(source), str(target))
    assert not target.exists()
