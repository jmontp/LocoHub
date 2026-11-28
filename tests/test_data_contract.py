"""Small independent fixtures for the internal release contract."""

import json

import numpy as np
import pandas as pd
import pytest

from contributor_tools.common.config_manager import ValidationConfigManager
from contributor_tools.common.data_contract import (
    PHASE_GRID,
    assess_observations,
    inspect_contract,
)


SIGNAL = "knee_flexion_angle_ipsi_rad"
OPTIONAL = "grf_vertical_ipsi_BW"


def observation(identifier="cycle-1", value=0.5, observation_type="individual_cycle"):
    return pd.DataFrame({
        "subject": "S01", "source_recording_id": "source/trial-1.mat",
        "observation_id": identifier, "reference_side": "left",
        "observation_type": observation_type, "task": "level_walking",
        "task_id": "level_1_m_s", "task_info": json.dumps({"speed_m_s": 1}),
        "phase_ipsi": PHASE_GRID.copy(), SIGNAL: np.full(150, value),
    })


def profile():
    config = ValidationConfigManager()
    config.set_range("level_walking", 0, SIGNAL, 0, 1)
    config.set_range("level_walking", 100, SIGNAL, 0, 1)
    return config


def test_cycle_identity_and_phase_endpoints_survive_shuffled_rows():
    df = pd.concat([observation("first", 0.25), observation("second", 0.75)], ignore_index=True)
    shuffled = df.sample(frac=1, random_state=5)
    result = assess_observations(shuffled, profile())
    assert result["schema_passed"] and result["publishable"]
    assert result["counts"]["passed"] == 2
    for item in result["observations"]:
        checks = item["signals"][0]["checks"]
        expected = 0.25 if item["identity"]["observation_id"] == "first" else 0.75
        assert [check["value"] for check in checks] == [expected, expected]
        assert checks[-1]["sample_index"] == 149
        assert checks[-1]["sample_phase"] == 100


def test_count_balancing_cannot_hide_malformed_observations():
    first = observation("first").iloc[:149]
    second = observation("second")
    second = pd.concat([second, second.iloc[[-1]]], ignore_index=True)
    result = inspect_contract(pd.concat([first, second], ignore_index=True))
    assert not result.schema_passed
    assert [issue.code for issue in result.issues] == ["invalid_phase_length", "invalid_phase_length"]


@pytest.mark.parametrize("change", ["duplicate", "exclusive_grid", "nan", "nonnumeric"])
def test_invalid_phase_grids_are_rejected(change):
    df = observation()
    if change == "duplicate":
        df.loc[1, "phase_ipsi"] = 0
    elif change == "exclusive_grid":
        df["phase_ipsi"] = np.linspace(0, 100, 150, endpoint=False)
    elif change == "nan":
        df.loc[1, "phase_ipsi"] = np.nan
    else:
        df["phase_ipsi"] = df["phase_ipsi"].astype(str)
    assert not inspect_contract(df).publishable


def test_float32_phase_precision_is_supported():
    df = observation()
    df["phase_ipsi"] = df["phase_ipsi"].astype("float32")
    assert inspect_contract(df).publishable


def test_legacy_missing_ids_remains_unreviewed():
    df = observation().drop(columns=["source_recording_id", "observation_id"])
    df["step"] = 1
    result = assess_observations(df, profile())
    assert not result["publishable"]
    assert result["contract"]["review_status"] == "unreviewed"
    assert result["coverage"]["eligible_observations"] == 0
    assert "observation_id" not in df


def test_inconsistent_task_metadata_and_unknown_reference_are_rejected():
    df = observation()
    df.loc[0, "task_info"] = '{"speed_m_s": 2}'
    assert "inconsistent_metadata" in [issue.code for issue in inspect_contract(df).issues]
    df = observation()
    df["reference_side"] = "unknown"
    assert inspect_contract(df).review_status == "unreviewed"


def test_required_missing_invalid_unchecked_and_failed_are_distinct():
    config = profile()
    frames = [observation(name) for name in ("pass", "missing", "invalid", "failed", "unchecked")]
    frames[1][SIGNAL] = np.nan
    frames[2].loc[1, SIGNAL] = np.inf
    frames[3].loc[149, SIGNAL] = 2.0
    frames[4]["task"] = "stair_ascent"
    result = assess_observations(pd.concat(frames, ignore_index=True), config)
    assert result["counts"] == {"passed": 1, "missing": 1, "invalid": 1, "failed": 1, "unchecked": 1}
    assert result["coverage"]["eligible_observations"] == 1
    assert result["schema_passed"]  # Signal QC is separate from the observation contract.


def test_nan_outside_sampled_phases_still_excludes_required_signal():
    df = observation()
    df.loc[70, SIGNAL] = np.nan
    result = assess_observations(df, profile())
    assert result["counts"]["missing"] == 1
    assert not result["observations"][0]["eligible"]


def test_optional_missing_is_explicit_but_does_not_exclude():
    config = profile()
    config.set_range("level_walking", 0, OPTIONAL, 0, 2)
    config.set_task_metadata("level_walking", "required_features", [SIGNAL])
    config.set_task_metadata("level_walking", "optional_features", [OPTIONAL])
    result = assess_observations(observation(), config)
    assert result["observations"][0]["eligible"]
    states = {item["feature"]: item["status"] for item in result["observations"][0]["signals"]}
    assert states == {SIGNAL: "passed", OPTIONAL: "missing"}
    df = observation()
    df[OPTIONAL] = 9
    assert not assess_observations(df, config)["observations"][0]["eligible"]


def test_legacy_profile_requires_all_configured_signals():
    config = profile()
    config.set_range("level_walking", 0, OPTIONAL, 0, 2)
    assert assess_observations(observation(), config)["counts"]["missing"] == 1


def test_empty_and_unmatched_profiles_never_qualify():
    for config in (None, ValidationConfigManager()):
        result = assess_observations(observation(), config)
        assert result["counts"]["unchecked"] == 1
        assert result["coverage"]["eligible_observations"] == 0
        assert result["coverage"]["assessed_observations"] == 0
        assert result["coverage"]["total_observations"] == 1


def test_ensemble_requires_explicit_profile_approval():
    df = observation(observation_type="ensemble_curve")
    config = profile()
    assert assess_observations(df, config)["counts"]["unchecked"] == 1
    config.set_task_metadata("level_walking", "observation_types", ["ensemble_curve"])
    assert assess_observations(df, config)["counts"]["passed"] == 1


def test_time_observations_use_time_ranges_without_phase_interpolation():
    df = observation(observation_type="continuous_recording").iloc[:3].drop(columns="phase_ipsi")
    df["time_s"] = [0, 0.01, 0.02]
    config = profile()
    assert assess_observations(df, config)["counts"]["unchecked"] == 1
    config.set_task_metadata("level_walking", "time_ranges", {SIGNAL: {"min": 0, "max": 1}})
    result = assess_observations(df.sample(frac=1, random_state=1), config)
    assert result["counts"]["passed"] == 1
    assert result["coverage"]["executed_checks"] == 3
    df.loc[1, "time_s"] = 0
    assert not inspect_contract(df).publishable


def test_invalid_profile_bounds_raise_even_when_signal_is_missing():
    config = profile()
    config.set_range("level_walking", 0, OPTIONAL, 2, 1)
    with pytest.raises(ValueError, match="min/max"):
        assess_observations(observation(), config)


def test_results_are_json_serializable_without_nonfinite_values():
    df = observation()
    df.loc[4, SIGNAL] = np.inf
    result = assess_observations(df, profile())
    json.dumps(result, allow_nan=False)


def test_unknown_task_is_a_contract_error():
    df = observation()
    df["task"] = "invented_task_name"
    assert "unknown_task" in [issue.code for issue in inspect_contract(df).issues]


def test_unavailable_source_clock_is_not_fabricated():
    df = observation(observation_type="transfer")
    df["source_start_time_s"] = np.nan
    df["source_end_time_s"] = np.nan
    assert inspect_contract(df).publishable
    df["source_start_time_s"] = 0.0
    assert not inspect_contract(df).publishable


def test_unknown_ensemble_reference_is_explicit_warning_not_invented_side():
    df = observation(observation_type="ensemble_curve")
    df["reference_side"] = "unknown"
    result = inspect_contract(df)
    assert result.publishable
    assert result.issues[0].severity == "warning"
    assert df["reference_side"].unique().tolist() == ["unknown"]


def test_waveform_profile_catches_spike_between_sparse_phase_checks():
    df = observation()
    df.loc[75, SIGNAL] = 3.0
    config = profile()
    assert assess_observations(df, config)["counts"]["passed"] == 1
    config.set_task_metadata("level_walking", "waveform_ranges", {
        SIGNAL: {"min": 0, "max": 1}
    })
    result = assess_observations(df, config)
    assert result["counts"]["failed"] == 1
    assert result["coverage"]["executed_checks"] == 152
    checks = result["observations"][0]["signals"][0]["checks"]
    assert checks[-1]["kind"] == "whole_waveform_range"
    assert checks[-1]["failed_samples"] == 1


def test_step_change_warning_uses_only_explicit_profile_threshold():
    df = observation()
    df.loc[75, SIGNAL] = 0.9
    config = profile()
    ordinary = assess_observations(df, config)
    assert ordinary["coverage"]["warning_count"] == 0
    config.set_task_metadata("level_walking", "waveform_ranges", {
        SIGNAL: {"max_abs_step": 0.2}
    })
    result = assess_observations(df, config)
    assert result["counts"]["passed"] == 1  # Review warning is explicitly informational.
    signal = result["observations"][0]["signals"][0]
    assert signal["waveform"]["finite_samples"] == 150
    assert signal["waveform"]["constant"] is False
    assert signal["warnings"][0]["exceeding_steps"] == 2
    assert result["coverage"]["warning_count"] == 1
    constant = assess_observations(observation(), config)
    assert constant["coverage"]["constant_signals"] == 1


def test_step_warning_alone_does_not_create_a_passing_range_assessment():
    config = ValidationConfigManager()
    config.set_task_metadata("level_walking", "waveform_ranges", {
        SIGNAL: {"max_abs_step": 0.2}
    })
    result = assess_observations(observation(), config)
    assert result["counts"]["unchecked"] == 1
    assert result["coverage"]["assessed_observations"] == 0


@pytest.mark.parametrize("population", ["healthy", None])
def test_profile_population_mismatch_or_missing_stays_unchecked(population):
    df = observation()
    if population is not None:
        df["subject_metadata"] = json.dumps({"population": population})
    config = profile()
    config.set_task_metadata("level_walking", "applicability", {"population": ["stroke"]})
    result = assess_observations(df, config)
    assert result["counts"]["unchecked"] == 1
    assert result["coverage"]["executed_checks"] == 0
    assert not result["observations"][0]["profile_applicability"]["matched"]


def test_applicability_matches_typed_metadata_across_sources_without_precedence():
    df = observation()
    df["subject_metadata"] = json.dumps({"population": "stroke"})
    df["task_info"] = json.dumps({"exo_state": "no_exo"})
    config = profile()
    config.set_task_metadata("level_walking", "applicability", {
        "population": ["stroke"], "exo_state": ["no_exo"]
    })
    result = assess_observations(df, config)
    assert result["counts"]["passed"] == 1
    df["task_info"] = json.dumps({"population": "healthy", "exo_state": "no_exo"})
    result = assess_observations(df, config)
    assert not result["schema_passed"] and not result["publishable"]
    assert result["counts"]["invalid"] == 1


def test_duplicate_json_keys_are_rejected():
    df = observation()
    df["subject_metadata"] = '{"population":"stroke","population":"healthy"}'
    assert not inspect_contract(df).publishable


def test_unspecified_profile_applicability_is_disclosed():
    result = assess_observations(observation(), profile())
    assert any("applicability" in limitation for limitation in result["limitations"])
