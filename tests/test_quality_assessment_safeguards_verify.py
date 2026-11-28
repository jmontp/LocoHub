"""Independent verifier probes for CORE-01 (quality assessment safeguards).

Written by the CORE-01 verifier without importing or reusing the worker's test
helpers. All frames are synthetic and invented here: subject "P7", hip angle
held at constants whose pass/fail state is known by construction (profile range
-0.2..0.8 rad). No research data is read and nothing here approves a dataset.
"""

import json

import numpy as np
import pandas as pd
import pytest

from contributor_tools.common.config_manager import ValidationConfigManager
from contributor_tools.common.data_contract import assess_observations, inspect_contract


HIP = "hip_flexion_angle_ipsi_rad"
GRID = np.linspace(0.0, 100.0, 150)  # independently written inclusive grid


def phase_obs(obs="o1", *, subject="P7", recording="rec/A", side="right",
              otype="individual_cycle", hip=0.3, n=150, extra=None):
    frame = pd.DataFrame({
        "subject": [subject] * n, "source_recording_id": [recording] * n,
        "observation_id": [obs] * n, "reference_side": [side] * n,
        "observation_type": [otype] * n, "task": ["level_walking"] * n,
        "task_id": ["lw_fixture"] * n,
        "task_info": [json.dumps({"speed_m_s": 1.2})] * n,
        "phase_ipsi": np.linspace(0.0, 100.0, n), HIP: [hip] * n,
    })
    for column, value in (extra or {}).items():
        frame[column] = value
    return frame


def time_obs(times, *, obs="t1", hip=0.3, extra=None):
    n = len(times)
    frame = pd.DataFrame({
        "subject": ["P7"] * n, "source_recording_id": ["rec/T"] * n,
        "observation_id": [obs] * n, "reference_side": ["left"] * n,
        "observation_type": ["continuous_recording"] * n, "task": ["level_walking"] * n,
        "task_id": ["lw_fixture"] * n, "task_info": [json.dumps({"speed_m_s": 1.2})] * n,
        "time_s": list(times), HIP: [hip] * n,
    })
    for column, value in (extra or {}).items():
        frame[column] = value
    return frame


def phase_profile(**task_metadata):
    config = ValidationConfigManager()
    for phase in (0, 50, 100):
        config.set_range("level_walking", phase, HIP, -0.2, 0.8)
    for key, value in task_metadata.items():
        config.set_task_metadata("level_walking", key, value)
    return config


def time_profile(**task_metadata):
    config = ValidationConfigManager()
    config.set_task_metadata("level_walking", "time_ranges", {HIP: {"min": -0.2, "max": 0.8}})
    for key, value in task_metadata.items():
        config.set_task_metadata("level_walking", key, value)
    return config


def issue_codes(frame, **kwargs):
    return {issue.code for issue in inspect_contract(frame, **kwargs).issues}


# --- Baselines: the fixtures pass when nothing is wrong ---------------------

def test_baseline_phase_cycle_passes():
    result = assess_observations(phase_obs(), phase_profile())
    assert result["publishable"] is True
    [obs] = result["observations"]
    assert obs["status"] == "passed" and obs["eligible"] is True


def test_baseline_hip_out_of_range_fails():
    [obs] = assess_observations(phase_obs(hip=1.5), phase_profile())["observations"]
    assert obs["status"] == "failed" and obs["eligible"] is False


# --- 1. Placeholder identities ---------------------------------------------

PLACEHOLDERS = [
    "nan", "NaN", "NAN", " nan", "nan\t", " None ", "none", "NONE",
    "<NA>", "<na>", "NaT", "nat", "null", "NULL", "\nNull\n",
]


@pytest.mark.parametrize("column", ["subject", "source_recording_id", "observation_id"])
@pytest.mark.parametrize("token", PLACEHOLDERS)
def test_placeholder_identity_variants_are_invalid(column, token):
    frame = phase_obs(**{"subject": "P7"})
    frame[column] = token
    contract = inspect_contract(frame)
    assert "invalid_identity" in {issue.code for issue in contract.issues}
    assert contract.publishable is False
    result = assess_observations(frame, phase_profile())
    assert result["coverage"]["eligible_observations"] == 0
    assert all(obs["status"] == "invalid" for obs in result["observations"])


@pytest.mark.parametrize("missing", [np.nan, None, pd.NA, pd.NaT])
def test_true_missing_values_in_object_identity_are_invalid(missing):
    frame = phase_obs()
    frame["observation_id"] = pd.Series([missing] * len(frame), dtype=object)
    assert "invalid_identity" in issue_codes(frame)
    assert assess_observations(frame, phase_profile())["coverage"]["eligible_observations"] == 0


def test_pandas_string_dtype_with_na_is_invalid():
    frame = phase_obs()
    frame["subject"] = pd.array([pd.NA] * len(frame), dtype="string")
    assert "invalid_identity" in issue_codes(frame)


def test_one_placeholder_row_poisons_only_by_failing_closed():
    # A single placeholder row anywhere makes the whole frame non-publishable.
    frame = pd.concat([phase_obs("o1"), phase_obs("o2")], ignore_index=True)
    frame.loc[0, "subject"] = "nan"
    result = assess_observations(frame, phase_profile())
    assert result["publishable"] is False
    assert result["coverage"]["eligible_observations"] == 0


@pytest.mark.parametrize("legit", ["NA01", "nan_trial", "Nancy", "none-left", "S_null_2", "NaT-7", "N"])
def test_identities_resembling_placeholders_stay_valid(legit):
    frame = phase_obs(subject=legit, recording=f"{legit}/rec", obs=legit)
    contract = inspect_contract(frame)
    assert contract.publishable is True, [issue.message for issue in contract.issues]
    [obs] = assess_observations(frame, phase_profile())["observations"]
    assert obs["status"] == "passed"
    assert obs["identity"]["subject"] == legit


def test_side_none_valid_but_stringified_none_side_is_not():
    ok = phase_obs(side="none", otype="transfer")
    assert inspect_contract(ok).schema_passed is True
    bad = phase_obs(side="None", otype="transfer")
    codes = issue_codes(bad)
    assert "unreviewed_reference_side" in codes
    assert inspect_contract(bad).publishable is False
    nan_side = phase_obs(side="nan")
    assert inspect_contract(nan_side).publishable is False


# --- 2. Laterality, mass and timing are not invented -----------------------

def test_cycle_with_side_none_and_limb_columns_is_rejected():
    assert "missing_reference_side" in issue_codes(phase_obs(side="none"))


def test_unknown_side_cycle_is_unreviewed_not_publishable():
    contract = inspect_contract(phase_obs(side="unknown"))
    assert contract.publishable is False


def test_no_mass_or_duration_fields_are_fabricated():
    [obs] = assess_observations(phase_obs(), phase_profile())["observations"]
    lineage = obs["time_lineage"]
    assert lineage["source_start_time_s"] is None and lineage["source_end_time_s"] is None
    assert not any("mass" in key or "duration" in key for key in lineage)
    flat = json.dumps(obs)
    assert "mass" not in flat and "duration" not in flat


# --- 3. Ensemble source bounds ---------------------------------------------

def ensemble(start, end):
    return phase_obs(side="none", otype="ensemble_curve",
                     extra={"source_start_time_s": start, "source_end_time_s": end})


@pytest.mark.parametrize("start,end", [
    (np.nan, 3.0), (2.0, np.nan), (2.0, 3.0), (np.inf, np.nan), (0.0, 0.0),
])
def test_ensemble_with_any_source_clock_fails(start, end):
    frame = ensemble(start, end)
    assert "ensemble_source_bounds" in issue_codes(frame, mode="ensemble")
    assert inspect_contract(frame, mode="ensemble").publishable is False


def test_ensemble_with_partially_filled_clock_fails():
    frame = ensemble(np.nan, np.nan)
    frame.loc[5, "source_end_time_s"] = 1.0
    assert "ensemble_source_bounds" in issue_codes(frame, mode="ensemble")


def test_ensemble_with_both_clocks_unavailable_passes_contract_and_reports_null():
    frame = ensemble(np.nan, np.nan)
    assert inspect_contract(frame, mode="ensemble").publishable is True
    profile = phase_profile(observation_types=["ensemble_curve"])
    [obs] = assess_observations(frame, profile, mode="ensemble")["observations"]
    assert obs["status"] == "passed"
    assert obs["time_lineage"]["source_start_time_s"] is None
    assert obs["time_lineage"]["source_end_time_s"] is None


def test_ensemble_with_only_one_clock_column_is_incomplete():
    frame = phase_obs(side="none", otype="ensemble_curve", extra={"source_start_time_s": np.nan})
    assert "incomplete_source_bounds" in issue_codes(frame, mode="ensemble")


def test_cycle_with_valid_source_clock_still_passes():
    frame = phase_obs(extra={"source_start_time_s": 12.0, "source_end_time_s": 13.1})
    [obs] = assess_observations(frame, phase_profile())["observations"]
    assert obs["status"] == "passed"
    assert obs["time_lineage"]["source_start_time_s"] == 12.0
    assert obs["time_lineage"]["source_end_time_s"] == 13.1


def test_cycle_with_reversed_source_clock_fails():
    frame = phase_obs(extra={"source_start_time_s": 13.0, "source_end_time_s": 12.0})
    assert "invalid_source_bounds" in issue_codes(frame)


# --- 4. Phase grid ----------------------------------------------------------

@pytest.mark.parametrize("n", [149, 151, 101])
def test_phase_sample_count_other_than_150_is_invalid(n):
    assert "invalid_phase_length" in issue_codes(phase_obs(n=n))


def test_phase_grid_without_endpoint_is_invalid():
    frame = phase_obs()
    frame["phase_ipsi"] = np.arange(150) * (100.0 / 150)  # 0 .. 99.33, exclusive
    assert "invalid_phase_grid" in issue_codes(frame)


# --- 5. Time lineage --------------------------------------------------------

def test_time_lineage_with_gaps_reports_recorded_endpoints_only():
    times = [5.0, 5.01, 5.5, 6.25]
    [obs] = assess_observations(time_obs(times), time_profile(), mode="time")["observations"]
    lineage = obs["time_lineage"]
    assert lineage["index_column"] == "time_s"
    assert lineage["index_first"] == 5.0 and lineage["index_last"] == 6.25
    assert obs["row_count"] == 4
    assert lineage["source_start_time_s"] is None


def test_time_lineage_of_unsorted_rows_reports_time_order_endpoints():
    frame = time_obs([7.0, 5.0, 6.0, 5.5])
    [obs] = assess_observations(frame, time_profile(), mode="time")["observations"]
    assert obs["time_lineage"]["index_first"] == 5.0
    assert obs["time_lineage"]["index_last"] == 7.0


def test_time_lineage_with_duplicate_time_marks_observation_invalid():
    frame = time_obs([5.0, 5.0, 5.1])
    [obs] = assess_observations(frame, time_profile(), mode="time")["observations"]
    assert obs["status"] == "invalid"
    assert "invalid_time_order" in obs["reasons"]
    assert obs["time_lineage"]["index_first"] == 5.0


def test_time_lineage_with_nonfinite_time_is_null():
    frame = time_obs([5.0, np.nan, 5.2])
    [obs] = assess_observations(frame, time_profile(), mode="time")["observations"]
    assert obs["status"] == "invalid"
    assert obs["time_lineage"]["index_first"] is None
    assert obs["time_lineage"]["index_last"] is None


def test_time_lineage_nonconstant_source_clock_is_null_and_flagged():
    frame = phase_obs(extra={"source_start_time_s": 1.0, "source_end_time_s": 2.0})
    frame.loc[3, "source_start_time_s"] = 1.5
    [obs] = assess_observations(frame, phase_profile())["observations"]
    assert obs["time_lineage"]["source_start_time_s"] is None
    assert obs["status"] == "invalid"


def test_time_lineage_is_json_serializable_without_nan():
    frame = time_obs([1.0, 1.1, 1.2], extra={"source_start_time_s": np.nan, "source_end_time_s": np.nan})
    result = assess_observations(frame, time_profile(), mode="time")
    json.dumps(result["observations"][0]["time_lineage"], allow_nan=False)


# --- 6. Profile applicability ----------------------------------------------

def with_meta(**subject_meta):
    return phase_obs(extra={"subject_metadata": json.dumps(subject_meta)})


def test_population_mismatch_stays_unchecked():
    frame = with_meta(population="stroke")
    [obs] = assess_observations(frame, phase_profile(applicability={"population": ["healthy"]}))["observations"]
    assert obs["status"] == "unchecked" and obs["eligible"] is False
    assert all(signal["status"] != "passed" for signal in obs["signals"])


def test_absent_applicability_metadata_stays_unchecked():
    frame = with_meta(height_m=1.7)
    [obs] = assess_observations(frame, phase_profile(applicability={"population": ["healthy"]}))["observations"]
    assert obs["status"] == "unchecked" and obs["eligible"] is False


def test_matching_population_passes():
    frame = with_meta(population="healthy")
    [obs] = assess_observations(frame, phase_profile(applicability={"population": ["healthy"]}))["observations"]
    assert obs["status"] == "passed"


def test_protocol_mismatch_via_task_info_stays_unchecked():
    frame = phase_obs()
    frame["task_info"] = json.dumps({"speed_m_s": 1.2, "exo_state": "powered"})
    profile = phase_profile(applicability={"exo_state": ["no_exo"]})
    [obs] = assess_observations(frame, profile)["observations"]
    assert obs["status"] == "unchecked"


def test_reference_side_applicability_mismatch_stays_unchecked():
    profile = phase_profile(applicability={"reference_side": ["left"]})
    [obs] = assess_observations(phase_obs(side="right"), profile)["observations"]
    assert obs["status"] == "unchecked"


def test_task_not_in_profile_stays_unchecked():
    frame = phase_obs()
    frame["task"] = "stair_ascent"
    [obs] = assess_observations(frame, phase_profile())["observations"]
    assert obs["status"] == "unchecked" and obs["eligible"] is False


def test_observation_type_not_opted_in_stays_unchecked():
    frame = ensemble(np.nan, np.nan)
    [obs] = assess_observations(frame, phase_profile(), mode="ensemble")["observations"]
    assert obs["status"] == "unchecked" and obs["eligible"] is False


def test_unit_mismatch_never_passes():
    frame = phase_obs().rename(columns={HIP: "hip_flexion_angle_ipsi_deg"})
    frame["hip_flexion_angle_ipsi_deg"] = 17.0
    [obs] = assess_observations(frame, phase_profile())["observations"]
    assert obs["eligible"] is False
    by_name = {signal["feature"]: signal for signal in obs["signals"]}
    assert by_name["hip_flexion_angle_ipsi_deg"]["status"] == "unchecked"
    assert by_name[HIP]["status"] == "missing"


def test_no_profile_never_passes():
    [obs] = assess_observations(phase_obs())["observations"]
    assert obs["status"] == "unchecked" and obs["eligible"] is False


def test_conflicting_applicability_sources_are_invalid():
    frame = with_meta(population="healthy")
    frame["task_info"] = json.dumps({"speed_m_s": 1.2, "population": "stroke"})
    [obs] = assess_observations(frame, phase_profile(applicability={"population": ["healthy"]}))["observations"]
    assert obs["status"] == "invalid" and obs["eligible"] is False


def test_profile_without_applicability_passes_with_limitation():
    # Documents current behavior that the worker raised as a possible José question.
    result = assess_observations(with_meta(population="stroke"), phase_profile())
    assert result["observations"][0]["status"] == "passed"
    assert any("does not declare population" in item for item in result["limitations"])


# --- 7. States are distinct -------------------------------------------------

def test_five_states_are_distinguishable():
    profile = phase_profile()
    passed = phase_obs("p")
    failed = phase_obs("f", hip=1.5)
    missing = phase_obs("m", hip=np.nan)
    unchecked = phase_obs("u")
    unchecked["task"] = "stair_ascent"
    invalid = phase_obs("i", hip=np.inf)
    frame = pd.concat([passed, failed, missing, unchecked, invalid], ignore_index=True)
    states = {obs["identity"]["observation_id"]: obs["status"]
              for obs in assess_observations(frame, profile)["observations"]}
    assert states == {"p": "passed", "f": "failed", "m": "missing", "u": "unchecked", "i": "invalid"}
