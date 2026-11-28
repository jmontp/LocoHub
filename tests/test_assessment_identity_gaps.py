"""CORE-08 identity and profile gaps on small synthetic fixtures.

All frames are synthetic (invented subject "S01", constant 0.5 rad knee angle
inside a 0-1 rad range), so each expected state is known by construction.
Nothing here reads or approves a research dataset.
"""

import json
import warnings

import numpy as np
import pandas as pd
import pytest

from contributor_tools.common import data_contract
from contributor_tools.common.config_manager import ValidationConfigManager
from contributor_tools.common.data_contract import (
    PHASE_GRID,
    assess_observations,
    inspect_contract,
)


KNEE = "knee_flexion_angle_ipsi_rad"
IDENTITY = ["subject", "source_recording_id", "observation_id"]


def cycle(identifier="cycle-1", subject="S01", recording="synthetic/trial-1", task_id="level_1_m_s"):
    return pd.DataFrame({
        "subject": subject, "source_recording_id": recording,
        "observation_id": identifier, "reference_side": "left",
        "observation_type": "individual_cycle", "task": "level_walking",
        "task_id": task_id, "task_info": json.dumps({"speed_m_s": 1}),
        "phase_ipsi": PHASE_GRID.copy(), KNEE: np.full(150, 0.5),
    })


def profile():
    config = ValidationConfigManager()
    config.set_range("level_walking", 0, KNEE, 0, 1)
    config.set_range("level_walking", 100, KNEE, 0, 1)
    return config


def issues(df):
    return inspect_contract(df).issues


@pytest.mark.parametrize("column", IDENTITY)
@pytest.mark.parametrize("token", [
    "<missing>", "<undefined>", "n/a", "N/A", "#N/A", "#n/a", "-nan", "-NaN",
    "​nan", "nan​", "﻿NULL", "ｎａｎ",  # zero-width / full-width
    "Ｎｏｎｅ", "＜NA＞",
])
def test_additional_placeholders_are_not_identities(column, token):
    df = cycle()
    df[column] = token
    result = assess_observations(df, profile())
    assert "invalid_identity" in [issue.code for issue in issues(df)]
    assert not result["publishable"]
    assert result["coverage"]["eligible_observations"] == 0


@pytest.mark.parametrize("column", IDENTITY)
@pytest.mark.parametrize("value", [
    "gt21:AB01/NaN/trial-3", "AB01/<missing>/t1", "rec|N/A|2", "AB01\\-nan\\t1",
    "sub:#N/A", "AB01／ｎａｎ／t1", "AB01/n/a",
])
def test_composite_identity_with_placeholder_part_is_rejected(column, value):
    df = cycle()
    df[column] = value
    assert "invalid_identity" in [issue.code for issue in issues(df)]
    assert assess_observations(df, profile())["coverage"]["eligible_observations"] == 0


@pytest.mark.parametrize("value", [
    "NA", "NA01", "Nancy", "nan_trial", "Banana/1", "AB01/NA/t1", "AB01/nan_x/t1",
    "S_null_2", "NaT-7", "N/A01", "AB01/none/t1",  # "none" can be a real condition label
    "AB01_NaN", "AB01 nan", "AB01/null/NaT",
])
def test_lookalike_identities_still_pass(value):
    df = cycle(identifier=value, subject=value, recording=f"{value}/rec")
    contract = inspect_contract(df)
    assert contract.publishable, [issue.message for issue in contract.issues]
    assert assess_observations(df, profile())["counts"]["passed"] == 1


def test_affected_observation_is_named_and_file_fails_closed():
    df = pd.concat([cycle("o1"), cycle("o2", subject="nan")], ignore_index=True)
    found = issues(df)
    named = [issue.identity for issue in found if issue.code == "invalid_identity"]
    assert named == [{
        "subject": "nan", "source_recording_id": "synthetic/trial-1",
        "observation_id": "o2", "reference_side": "left",
    }]
    assert [issue.identity for issue in found if issue.code == "placeholder_identity_in_file"] == [None]
    result = assess_observations(df, profile())
    by_id = {item["identity"]["observation_id"]: item for item in result["observations"]}
    assert "invalid_identity" in by_id["o2"]["reasons"]
    assert "invalid_identity" not in by_id["o1"]["reasons"]
    assert "placeholder_identity_in_file" in by_id["o1"]["reasons"]
    assert result["coverage"]["eligible_observations"] == 0


def test_placeholder_check_runs_on_unique_values_only(monkeypatch):
    calls = []
    original = data_contract._placeholder_text

    def counted(value):
        calls.append(value)
        return original(value)

    monkeypatch.setattr(data_contract, "_placeholder_text", counted)
    df = pd.concat([cycle("o1"), cycle("o2")], ignore_index=True)  # 300 rows
    assert inspect_contract(df).publishable
    # Identity columns: 1 + 1 + 2 unique values; task_id: once per observation.
    assert len(calls) == 6


@pytest.mark.parametrize("task_id", ["nan", "NaN", "<missing>", "N/A"])
def test_stringified_missing_task_id_is_invalid(task_id):
    df = cycle(task_id=task_id)
    assert "invalid_metadata" in [issue.code for issue in issues(df)]
    assert assess_observations(df, profile())["counts"]["invalid"] == 1


def test_lookalike_task_id_stays_valid():
    assert inspect_contract(cycle(task_id="NA_speed")).publishable


@pytest.mark.parametrize("status", ["reviewed", "approved"])
def test_reviewed_profile_must_declare_applicability(status):
    config = profile()
    config.set_metadata("review_status", status)
    assert data_contract.profile_applicability_gaps(config) == ["level_walking"]
    config.set_task_metadata("level_walking", "applicability", {})
    assert data_contract.profile_applicability_gaps(config) == ["level_walking"]
    config.set_task_metadata("level_walking", "applicability", {"population": ["healthy"]})
    assert data_contract.profile_applicability_gaps(config) == []


@pytest.mark.parametrize("status", [None, "draft"])
def test_unreviewed_profiles_are_not_reported_as_reviewed(status):
    """Draft and unlabelled profiles are handled by the release gate's own labels."""
    config = profile()
    if status:
        config.set_metadata("review_status", status)
    assert data_contract.profile_applicability_gaps(config) == []
    assert data_contract.profile_applicability_gaps(None) == []


@pytest.mark.parametrize("categories", [1, 2])
@pytest.mark.parametrize("column", IDENTITY + ["reference_side"])
def test_categorical_identities_are_assessed_like_strings(column, categories):
    plain = pd.concat([cycle("o1"), cycle("o2")], ignore_index=True)
    if categories == 1:
        plain = plain[plain["observation_id"] == "o1"].reset_index(drop=True)
    categorical = plain.copy()
    categorical[column] = categorical[column].astype("category")
    assert categorical[column].cat.categories.size == (categories if column == "observation_id" else 1)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        expected = assess_observations(plain, profile())
        actual = assess_observations(categorical, profile())
    assert actual["publishable"] and actual["counts"] == expected["counts"]
    assert [item["identity"] for item in actual["observations"]] == [
        item["identity"] for item in expected["observations"]
    ]


def test_categorical_placeholder_and_missing_identities_still_fail():
    df = cycle(subject="nan")
    df["subject"] = df["subject"].astype("category")
    assert "invalid_identity" in [issue.code for issue in issues(df)]
    df = cycle()
    df["subject"] = pd.Categorical([None] * 150, categories=["S01"])
    assert "invalid_identity" in [issue.code for issue in issues(df)]


def test_file_level_count_is_distinct_observations_not_issues():
    df = pd.concat([cycle("o1"), cycle("<missing>", subject="nan")], ignore_index=True)
    found = issues(df)
    assert len([issue for issue in found if issue.code == "invalid_identity"]) == 2  # two columns
    [summary] = [issue for issue in found if issue.code == "placeholder_identity_in_file"]
    assert summary.message.startswith("1 observation(s)")


@pytest.mark.parametrize("value", ["#NA", "1.#QNAN", "AB01/#NA/t1", "AB01/1.#QNAN", "AB01/ /t1", "AB01|\u3000|t1"])
def test_spreadsheet_nan_spellings_and_blank_parts_are_rejected(value):
    df = cycle(recording=value)
    assert "invalid_identity" in [issue.code for issue in issues(df)]


@pytest.mark.parametrize("value", [
    "https://example.invalid/raw.zip", "C:\\data\\trial.mat", "/data/S01/trial.mat",
    "\\\\server\\share\\t1", "AB01//t1", "S01 / trial 1",
])
def test_real_path_shapes_with_empty_parts_still_pass(value):
    assert inspect_contract(cycle(recording=value)).publishable
