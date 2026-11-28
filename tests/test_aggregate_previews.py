"""Independent checks of grouping, missingness, and subject weighting."""

import json
import math

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from contributor_tools.build_aggregate_previews import (
    CycleIndexer, Moments, aggregate_file, projected_groups, signal_definitions,
    split_existing_exports,
)


ANGLE = "knee_flexion_angle_ipsi_rad"
MOMENT = "hip_flexion_moment_contra_Nm_kg"


def curve(subject, step, angle=0.0, moment=1.0, task="level_walking"):
    return {
        "subject": [subject] * 150, "task": [task] * 150, "step": [step] * 150,
        "phase_ipsi": np.linspace(0, 100, 150).tolist(),
        ANGLE: [angle] * 150, MOMENT: [moment] * 150,
    }


def combined(curves):
    return {name: [value for item in curves for value in item[name]] for name in curves[0]}


def test_reused_step_and_batch_boundaries_do_not_merge_cycles():
    accepted = []
    indexer = CycleIndexer(lambda *values: accepted.append(values))
    phase = np.tile(np.linspace(0, 100, 150), 3)
    keys = [("A", "walking", "reused-step")] * 450
    for left, right in ((0, 149), (149, 151), (151, 307), (307, 450)):
        indexer.feed(keys[left:right], phase[left:right])
    counts, _ = indexer.finish()
    assert [item[:2] for item in accepted] == [(0, 150), (150, 300), (300, 450)]
    assert counts["complete_observations"] == 3
    assert counts["complete_rows"] == counts["source_rows"] == 450


def test_149_plus_151_rows_are_excluded_without_reshaping():
    accepted = []
    indexer = CycleIndexer(lambda *values: accepted.append(values))
    indexer.feed([("A", "walk", 1)] * 149, np.linspace(0, 100, 149))
    indexer.feed([("A", "walk", 2)] * 151, np.linspace(0, 100, 151))
    counts, _ = indexer.finish()
    assert accepted == []
    assert counts["incomplete_or_oversized_observations"] == 2
    assert counts["incomplete_or_oversized_rows"] == 300


@pytest.mark.parametrize("mutation", ["nonuniform", "duplicate", "missing"])
def test_only_exact_monotonic_phase_grid_is_accepted(mutation):
    accepted = []
    phase = np.linspace(0, 100, 150)
    if mutation == "nonuniform":
        phase[70] += 0.05
    elif mutation == "duplicate":
        phase[70] = phase[69]
    else:
        phase[70] = np.nan
    indexer = CycleIndexer(lambda *values: accepted.append(values))
    indexer.feed([("A", "walk", 1)] * 150, phase)
    counts, _ = indexer.finish()
    assert accepted == []
    assert counts["malformed_phase_observations"] == 1


def test_missing_identity_never_becomes_a_complete_observation():
    accepted = []
    indexer = CycleIndexer(lambda *values: accepted.append(values))
    indexer.feed([("A", "walk", None)] * 150, np.linspace(0, 100, 150))
    counts, _ = indexer.finish()
    assert not accepted
    assert counts["invalid_identity_rows"] == 150


def test_welford_uses_finite_counts_and_sample_sd():
    moments = Moments((3,))
    moments.update(np.array([1.0, np.nan, np.nan]))
    moments.update(np.array([3.0, 4.0, np.inf]))
    mean, sd, n = moments.arrays()
    np.testing.assert_equal(n, [2, 1, 0])
    np.testing.assert_allclose(mean[:2], [2, 4])
    assert math.isclose(sd[0], math.sqrt(2))
    assert np.isnan(sd[1:]).all()
    assert np.isnan(mean[2])


def test_signal_selection_includes_units_and_sides_but_excludes_metadata():
    schema = pa.schema([
        (ANGLE, pa.float64()), (MOMENT, pa.float64()),
        ("joint_power_ipsi_W", pa.float64()), ("marker_position_contra_m", pa.float64()),
        ("grf_vertical_ipsi_N", pa.float64()), ("thigh_velocity_ipsi_rad_s", pa.float64()),
        ("knee_acceleration_ipsi_rad_s2", pa.float64()), ("assistance_active", pa.bool_()),
        ("phase_ipsi", pa.float64()), ("phase_ipsi_dot", pa.float64()),
        ("time_s", pa.float64()), ("height_m", pa.float64()), ("task_incline_deg", pa.float64()),
    ])
    signals = signal_definitions(schema)
    assert len(signals) == 7
    assert next(item for item in signals if item["column"] == ANGLE)["label"].endswith("(ipsilateral)")
    assert next(item for item in signals if item["column"] == MOMENT)["unit"] == "Nm_kg"


def test_real_parquet_equal_subject_weighting_missingness_and_cross_row_groups(tmp_path):
    curves = [curve("A", "reused", 0, value) for value in (1, 3, 5)] + [curve("B", "reused", 10, 7)]
    for item in curves[:3]:
        item[ANGLE][5] = None
    curves[3][ANGLE][6] = None
    curves.append(curve("C", "one", None, None, "all_missing"))
    malformed = curve("D", "bad", 99, 99, "bad_phase")
    malformed["phase_ipsi"][60] += 0.05
    curves.append(malformed)
    path = tmp_path / "fixture.parquet"
    pq.write_table(pa.table(combined(curves)), path, row_group_size=97)
    output = tmp_path / "out" / "fixture"
    result = aggregate_file(path, output, batch_rows=31)
    assert result["excluded_counts"]["complete_observations"] == 5
    assert result["excluded_counts"]["malformed_phase_observations"] == 1
    tasks = {task["id"]: task for task in result["tasks"]}
    payload = json.loads((output.parent / tasks["level_walking"]["url"]).read_text())
    subjects = {
        subject: json.loads((output / reference["url"]).read_text())
        for subject, reference in payload["subjects"].items()
    }
    assert payload["subjects"]["A"]["observations"] == 3
    assert payload["subjects"]["B"]["observations"] == 1
    assert "signals" not in payload["subjects"]["A"]
    assert subjects["A"]["signals"][ANGLE]["mean"][0] == 0
    assert subjects["B"]["signals"][ANGLE]["sd"][0] is None
    # The grand mean is 5, not the observation-weighted mean 2.5.
    assert payload["all"]["signals"][ANGLE]["mean"][0] == 5
    assert payload["all"]["signals"][ANGLE]["sd"][0] == pytest.approx(math.sqrt(50), rel=1e-6)
    assert subjects["A"]["signals"][MOMENT]["mean"][0] == 3
    assert subjects["A"]["signals"][MOMENT]["sd"][0] == 2
    assert payload["all"]["signals"][ANGLE]["n"][5] == 1
    assert payload["all"]["signals"][ANGLE]["mean"][5] == 10
    assert payload["all"]["signals"][ANGLE]["sd"][5] is None
    assert subjects["A"]["signals"][ANGLE]["n"][5] == 0
    assert subjects["A"]["signals"][ANGLE]["mean"][5] is None
    assert payload["all"]["signals"][ANGLE]["n"][6] == 1
    assert tasks["all_missing"]["signals"] == []
    assert tasks["bad_phase"]["observations"] == 0
    assert tasks["bad_phase"]["subjects"] == ["D"]
    assert result["source"]["source_sha256"] is None
    assert "not verified" in result["source"]["note"].lower()
    assert list(tmp_path.joinpath("out").glob(".aggregate-*")) == []


def test_split_existing_preserves_statistics_and_uses_relative_subject_urls(tmp_path):
    output = tmp_path / "exports"
    dataset = output / "fixture"
    dataset.mkdir(parents=True)
    subject = {"observations": 1, "signals": {ANGLE: {"mean": [1, None], "sd": [None, None], "n": [1, 0]}}}
    task_payload = {"phase": [0, 100], "subjects": {"A / B": subject}, "all": {"signals": {ANGLE: subject["signals"][ANGLE]}}}
    task_path = dataset / "walking.json"
    task_path.write_text(json.dumps(task_payload))
    manifest = {"version": 1, "datasets": {"fixture": {
        "source": {"filename": "must_not_read.parquet"},
        "tasks": [{"id": "walking", "url": "fixture/walking.json"}],
    }}}
    (output / "manifest.json").write_text(json.dumps(manifest))
    result = split_existing_exports(output)
    rewritten = json.loads(task_path.read_text())
    reference = rewritten["subjects"]["A / B"]
    assert set(reference) == {"observations", "url"}
    assert not reference["url"].startswith("/")
    assert json.loads((task_path.parent / reference["url"]).read_text()) == subject
    assert rewritten["all"] == task_payload["all"]
    assert rewritten["phase"] == task_payload["phase"]
    assert result["version"] == 2
    assert result["datasets"]["fixture"]["tasks"][0]["max_subject_file_bytes"] > 0
    assert split_existing_exports(output) == result


def test_projected_row_group_budget_is_enforced(tmp_path):
    path = tmp_path / "budget.parquet"
    pq.write_table(pa.table(curve("A", 1)), path)
    with pq.ParquetFile(path) as parquet:
        with pytest.raises(MemoryError, match="Column"):
            projected_groups(parquet, [ANGLE], limit=1)
