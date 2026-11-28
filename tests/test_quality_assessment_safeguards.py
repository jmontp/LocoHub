"""CORE-01 safeguards on small synthetic fixtures.

Every frame here is synthetic: one invented subject ("S01"), constant signals and
values chosen so the expected state is known without running the assessment.
None of these fixtures represents or approves any research dataset.
"""

import json

import numpy as np
import pandas as pd
import pytest

from contributor_tools.common.config_manager import ValidationConfigManager
from contributor_tools.common.data_contract import (
    PHASE_GRID,
    QUALITY_STATES,
    assess_observations,
    inspect_contract,
)


KNEE = "knee_flexion_angle_ipsi_rad"
GRF = "grf_vertical_ipsi_BW"


def cycle(identifier="cycle-1", value=0.5, observation_type="individual_cycle", side="left"):
    return pd.DataFrame({
        "subject": "S01", "source_recording_id": "synthetic/trial-1",
        "observation_id": identifier, "reference_side": side,
        "observation_type": observation_type, "task": "level_walking",
        "task_id": "level_1_m_s", "task_info": json.dumps({"speed_m_s": 1}),
        "phase_ipsi": PHASE_GRID.copy(), KNEE: np.full(150, value),
    })


def recording(times=(10.0, 10.01, 10.02), value=0.5):
    df = cycle(observation_type="continuous_recording").iloc[:len(times)].drop(columns="phase_ipsi")
    df["time_s"] = list(times)
    return df


def profile(**metadata):
    config = ValidationConfigManager()
    config.set_range("level_walking", 0, KNEE, 0, 1)
    config.set_range("level_walking", 100, KNEE, 0, 1)
    for key, value in metadata.items():
        config.set_task_metadata("level_walking", key, value)
    return config


def codes(df):
    return [issue.code for issue in inspect_contract(df).issues]


# Unsupported identities, anatomy, mass, timing and laterality.

@pytest.mark.parametrize("column", ["subject", "source_recording_id", "observation_id"])
@pytest.mark.parametrize("token", ["nan", "None", "<NA>", " NaN ", "null"])
def test_stringified_missing_identity_is_not_a_source_identity(column, token):
    df = cycle()
    df[column] = token
    result = assess_observations(df, profile())
    assert not result["publishable"]
    assert result["coverage"]["eligible_observations"] == 0
    assert "invalid_identity" in codes(df)


def test_numeric_subject_is_not_silently_stringified():
    df = cycle()
    df["subject"] = 1
    assert "invalid_identity" in codes(df)
    assert df["subject"].tolist() == [1] * 150


def test_explicit_none_reference_side_remains_valid_for_ensembles():
    df = cycle(observation_type="ensemble_curve", side="none")
    assert inspect_contract(df).publishable


@pytest.mark.parametrize("side", ["unknown", "Left", "ipsi", "affected"])
def test_cycle_laterality_is_not_inferred(side):
    df = cycle(side=side)
    assert "unreviewed_reference_side" in codes(df)
    assert assess_observations(df, profile())["coverage"]["eligible_observations"] == 0


def test_limb_indexed_cycle_without_side_is_not_assigned_one():
    df = cycle(side="none")
    assert "missing_reference_side" in codes(df)
    assert df["reference_side"].unique().tolist() == ["none"]


def test_body_weight_signal_without_mass_is_assessed_not_rescaled():
    """No mass is supplied or invented; the BW value is checked exactly as given."""
    config = ValidationConfigManager()
    config.set_range("level_walking", 0, GRF, 0, 2)
    df = cycle()
    df[GRF] = 2.5
    result = assess_observations(df, config)
    check = next(s for s in result["observations"][0]["signals"] if s["feature"] == GRF)["checks"][0]
    assert check["value"] == 2.5 and not check["passed"]
    assert "subject_metadata" not in df


def test_ensemble_source_clock_is_not_accepted_as_a_cycle_duration():
    config = profile(observation_types=["ensemble_curve"])
    df = cycle(observation_type="ensemble_curve")
    df["source_start_time_s"] = np.nan
    df["source_end_time_s"] = np.nan
    assert assess_observations(df, config)["counts"]["passed"] == 1
    df["source_start_time_s"] = 0.0
    df["source_end_time_s"] = 1.1  # e.g. an assumed stride duration
    result = assess_observations(df, config)
    assert "ensemble_source_bounds" in codes(df)
    assert result["counts"]["invalid"] == 1 and not result["publishable"]


# States with source, side and time lineage.

def test_each_state_reports_source_side_and_time_lineage():
    frames = [cycle(name) for name in ("pass", "missing", "invalid", "failed", "unchecked")]
    frames[1][KNEE] = np.nan
    frames[2].loc[3, KNEE] = np.inf
    frames[3].loc[0, KNEE] = 2.0
    frames[4]["task"] = "stair_ascent"
    for offset, frame in enumerate(frames):
        frame["reference_side"] = "right" if offset % 2 else "left"
        frame["source_start_time_s"] = 10.0 + offset
        frame["source_end_time_s"] = 11.2 + offset
    result = assess_observations(pd.concat(frames, ignore_index=True), profile())
    by_id = {item["identity"]["observation_id"]: item for item in result["observations"]}
    assert {name: item["status"] for name, item in by_id.items()} == {
        "pass": "passed", "missing": "missing", "invalid": "invalid",
        "failed": "failed", "unchecked": "unchecked",
    }
    for offset, name in enumerate(("pass", "missing", "invalid", "failed", "unchecked")):
        item = by_id[name]
        assert item["identity"]["source_recording_id"] == "synthetic/trial-1"
        assert item["identity"]["reference_side"] == ("right" if offset % 2 else "left")
        assert item["time_lineage"] == {
            "index_column": "phase_ipsi", "index_first": 0.0, "index_last": 100.0,
            "source_start_time_s": 10.0 + offset, "source_end_time_s": 11.2 + offset,
        }
    json.dumps(result, allow_nan=False)


def test_unavailable_clock_lineage_stays_unavailable():
    item = assess_observations(cycle(), profile())["observations"][0]
    assert item["time_lineage"]["source_start_time_s"] is None
    assert item["time_lineage"]["source_end_time_s"] is None


def test_time_observation_lineage_reports_recorded_clock():
    config = profile(time_ranges={KNEE: {"min": 0, "max": 1}})
    item = assess_observations(recording().sample(frac=1, random_state=3), config)["observations"][0]
    assert item["status"] == "passed"
    assert item["time_lineage"]["index_first"] == 10.0
    assert item["time_lineage"]["index_last"] == 10.02


def test_every_observation_is_accounted_for_once():
    frames = [cycle("a"), cycle("b", value=2.0), cycle("a", side="right"), cycle("c").iloc[:149]]
    result = assess_observations(pd.concat(frames, ignore_index=True), profile())
    assert result["coverage"]["total_observations"] == 4
    assert sum(result["counts"].values()) == 4
    assert set(result["counts"]) == set(QUALITY_STATES)
    excluded = [item for item in result["observations"] if not item["eligible"]]
    assert len(excluded) == 4 - result["coverage"]["eligible_observations"] == 2
    assert all(item["reasons"] for item in excluded)


# Phase grid and real clocks.

@pytest.mark.parametrize("rows", [149, 151])
def test_ensemble_also_needs_exactly_150_inclusive_samples(rows):
    df = cycle(observation_type="ensemble_curve")
    df = df.iloc[:rows] if rows < 150 else pd.concat([df, df.iloc[[-1]]], ignore_index=True)
    assert "invalid_phase_length" in codes(df)


@pytest.mark.parametrize("times", [(0.0, 0.0, 0.02), (0.0, np.nan, 0.02), (0.0,)])
def test_invalid_real_clocks_are_not_repaired(times):
    df = recording(times)
    assert not inspect_contract(df).publishable
    assert df["time_s"].tolist()[:1] == [0.0]


# Explicit profile applicability.

@pytest.mark.parametrize("field,allowed,actual", [
    ("population", ["stroke"], "healthy"),
    ("protocol", ["treadmill"], "overground"),
    ("reference_side", ["right"], None),  # The cycle's own side is "left".
    ("sign_rule", ["B"], None),  # Ranges assume rule B signs; undeclared stays unchecked.
])
def test_applicability_mismatch_or_absence_stays_unchecked(field, allowed, actual):
    df = cycle()
    if actual is not None:
        df["subject_metadata"] = json.dumps({field: actual})
    result = assess_observations(df, profile(applicability={field: allowed}))
    assert result["counts"]["unchecked"] == 1
    assert result["coverage"]["executed_checks"] == 0


def test_unit_suffix_mismatch_is_never_converted():
    df = cycle().rename(columns={KNEE: "knee_flexion_angle_ipsi_deg"})
    df["knee_flexion_angle_ipsi_deg"] = 30.0
    item = assess_observations(df, profile())["observations"][0]
    states = {signal["feature"]: signal["status"] for signal in item["signals"]}
    assert states == {KNEE: "missing", "knee_flexion_angle_ipsi_deg": "unchecked"}
    assert not item["eligible"]


@pytest.mark.parametrize("observation_type", ["transfer", "ensemble_curve"])
def test_observation_type_outside_profile_stays_unchecked(observation_type):
    config = profile(observation_types=["individual_cycle"])
    result = assess_observations(cycle(observation_type=observation_type), config)
    assert result["counts"]["unchecked"] == 1


def test_signal_without_rule_is_unchecked_and_cannot_qualify():
    config = profile(required_features=[KNEE, GRF])
    df = cycle()
    df[GRF] = 1.0
    item = assess_observations(df, config)["observations"][0]
    grf = next(signal for signal in item["signals"] if signal["feature"] == GRF)
    assert grf["status"] == "unchecked" and not grf["checks"]
    assert item["status"] == "unchecked" and not item["eligible"]
