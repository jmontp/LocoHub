"""Tiny headless tests of draft persistence and edits; no display or source data."""

import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest
import yaml


FEATURE = "knee_flexion_angle_ipsi_rad"


@pytest.fixture
def tuner_module(monkeypatch):
    monkeypatch.setenv("LOCOHUB_HEADLESS", "1")
    monkeypatch.setenv("MPLBACKEND", "Agg")
    return importlib.import_module("contributor_tools.interactive_validation_tuner")


@pytest.fixture
def tuner(tuner_module, tmp_path):
    profile = {
        "version": "2.0",
        "review_status": "reviewed",
        "review": {"reviewer": "fixture-reviewer"},
        "provenance": {"source": "fixture-study", "coordinate_frame": "source_frame"},
        "time_structural_abs_limits": {FEATURE: 6.0},
        "tasks": {"level_walking": {
            "metadata": {"population": "fixture", "protocol": {"surface": "treadmill"}},
            "citation": {"doi": "fixture-doi"},
            "phases": {0: {FEATURE: {"min": 0.0, "max": 1.0}}},
        }},
    }
    path = tmp_path / "source.yaml"
    path.write_text(yaml.safe_dump(profile))
    app = tuner_module.InteractiveValidationTuner(headless=True)
    app._load_profile(path)
    app.current_task = "level_walking"
    return app


def test_save_draft_preserves_provenance_and_emits_diff(tuner, tmp_path):
    parent_hash = hashlib.sha256(tuner.profile_path.read_bytes()).hexdigest()
    tuner.set_numeric_range("level_walking", FEATURE, 0, 10, -0.2, 1.2)
    output = tmp_path / "draft.yaml"
    audit_path = tuner.save_profile(output, "Reviewed source units; widening this draft for testing.")
    profile = yaml.safe_load(output.read_text())
    audit = json.loads(audit_path.read_text())
    assert profile["review_status"] == audit["review_status"] == "draft"
    assert profile["review"]["parent_profile_sha256"] == parent_hash
    assert profile["review_history"] == [{"reviewer": "fixture-reviewer"}]
    assert "reviewer" not in profile["review"]
    assert profile["provenance"]["coordinate_frame"] == "source_frame"
    assert profile["time_structural_abs_limits"] == {FEATURE: 6.0}
    assert profile["tasks"]["level_walking"]["metadata"]["protocol"] == {"surface": "treadmill"}
    assert profile["tasks"]["level_walking"]["citation"] == {"doi": "fixture-doi"}
    assert len(audit["range_changes"]) == 2  # Old phase removed, new phase added.
    assert audit["before"]["status"] == audit["after"]["status"] == "not_evaluated"
    assert audit["profile_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert tuner.modified is False


def test_save_requires_rationale_and_does_not_write(tuner, tmp_path):
    output = tmp_path / "invalid.yaml"
    with pytest.raises(ValueError, match="rationale"):
        tuner.save_profile(output, "  ")
    assert not output.exists()
    assert not Path(str(output) + ".audit.json").exists()


def test_numeric_edit_undo_redo_and_saved_dirty_state(tuner):
    baseline = tuner._profile_snapshot()
    tuner.set_numeric_range("level_walking", FEATURE, 0, 25, -1.0, 2.0)
    edited = tuner._profile_snapshot()
    assert tuner.modified
    assert tuner.full_validation_data == tuner.validation_data
    tuner.undo()
    assert tuner._profile_snapshot() == baseline
    assert not tuner.modified
    tuner.redo()
    assert tuner._profile_snapshot() == edited
    assert tuner.modified
    tuner.undo()
    tuner.set_numeric_range("level_walking", FEATURE, 0, 0, -0.5, 1.0)
    assert tuner._redo_stack == []


@pytest.mark.parametrize("phase,lower,upper", [
    (101, 0, 1), (0.5, 0, 1), (25, 2, 1), (25, np.nan, 1), (np.inf, 0, 1),
])
def test_invalid_numeric_edit_leaves_ranges_and_history_unchanged(tuner, phase, lower, upper):
    before = tuner._profile_snapshot()
    with pytest.raises(ValueError):
        tuner.set_numeric_range("level_walking", FEATURE, 0, phase, lower, upper)
    assert tuner._profile_snapshot() == before
    assert tuner._undo_stack == []


def test_numeric_phase_collision_is_rejected(tuner):
    tuner.validation_data["level_walking"][50] = {FEATURE: {"min": 0.0, "max": 0.5}}
    before = tuner._profile_snapshot()
    with pytest.raises(ValueError, match="already"):
        tuner.set_numeric_range("level_walking", FEATURE, 0, 50, -1.0, 2.0)
    assert tuner._profile_snapshot() == before


def test_numeric_dialog_converts_display_degrees(tuner, tuner_module, monkeypatch):
    tuner.root = object()
    tuner.update_plot = Mock()
    monkeypatch.setattr(tuner_module.simpledialog, "askinteger", lambda *args, **kwargs: 25)
    answers = iter([-90.0, 90.0])
    monkeypatch.setattr(tuner_module.simpledialog, "askfloat", lambda *args, **kwargs: next(answers))
    tuner.edit_box_numerically(SimpleNamespace(
        phase=0, var_name=FEATURE, min_val=0.0, max_val=1.0,
    ))
    bounds = tuner.validation_data["level_walking"][25][FEATURE]
    np.testing.assert_allclose([bounds["min"], bounds["max"]], [-np.pi / 2, np.pi / 2])
    assert len(tuner._undo_stack) == 1


def test_dataset_derived_ranges_are_unreviewed_and_undoable(tuner, tmp_path):
    tuner.dataset_path = tmp_path / "fixture.parquet"
    tuner.locomotion_data = SimpleNamespace(
        get_subjects=lambda: ["fixture"],
        get_cycles=lambda **kwargs: (np.zeros((1, 150, 1)), [FEATURE]),
    )
    assert tuner._initialize_task_from_dataset("stair_ascent")
    assert "stair_ascent" not in tuner.original_validation_data
    metadata = tuner.task_metadata["stair_ascent"]
    assert metadata["review_status"] == "draft"
    assert metadata["range_origin"] == "dataset_min_max_placeholder"
    assert metadata["review_required"] is True
    tuner.current_task = "stair_ascent"
    assert "DRAFT" in tuner._get_summary_title()
    tuner.undo()
    assert "stair_ascent" not in tuner.validation_data
    assert "stair_ascent" not in tuner.task_metadata


def test_close_and_load_guard_honor_cancel_and_failed_save(tuner, tuner_module, monkeypatch):
    tuner.root = SimpleNamespace(destroy=Mock())
    tuner.modified = True
    monkeypatch.setattr(tuner_module.messagebox, "askyesnocancel", lambda *args, **kwargs: None)
    tuner.on_close()
    tuner.root.destroy.assert_not_called()
    monkeypatch.setattr(tuner_module.messagebox, "askyesnocancel", lambda *args, **kwargs: True)
    tuner.save_validation_ranges = Mock(return_value=False)
    tuner.on_close()
    tuner.root.destroy.assert_not_called()
    chooser = Mock()
    monkeypatch.setattr(tuner_module.filedialog, "askopenfilename", chooser)
    tuner.load_validation_ranges()
    chooser.assert_not_called()
    monkeypatch.setattr(tuner_module.messagebox, "askyesnocancel", lambda *args, **kwargs: False)
    tuner.on_close()
    tuner.root.destroy.assert_called_once()


def test_audit_compares_decisions_on_same_tiny_loaded_table(tuner, tuner_module, tmp_path):
    frame = pd.DataFrame({
        "subject": "fixture", "task": "level_walking", "task_id": "fixture",
        "step": 1, "phase_ipsi": np.linspace(0, 100, 150), FEATURE: 0.5,
    })
    tuner.locomotion_data = tuner_module.DatasetTable.from_frame(frame)
    tuner.set_numeric_range("level_walking", FEATURE, 0, 0, 0.6, 1.0)
    audit_path = tuner.save_profile(tmp_path / "draft.yaml", "Exercise decision change on fixture.")
    audit = json.loads(audit_path.read_text())
    assert audit["before"]["counts"]["total_passing_strides"] == 1
    assert audit["after"]["counts"]["total_failing_strides"] == 1
    assert audit["before"]["dataset_rows"] == audit["after"]["dataset_rows"] == 150


def test_background_preparation_does_not_recreate_gui(tuner):
    canvas = SimpleNamespace(draw=Mock(), copy_from_bbox=Mock(return_value="background"))
    box = SimpleNamespace(ax=SimpleNamespace(figure=SimpleNamespace(canvas=canvas), bbox="bbox"))
    tuner.draggable_boxes = [box]
    tuner.setup_gui = Mock()
    tuner.auto_load_defaults = Mock()
    tuner.prepare_all_backgrounds()
    tuner.setup_gui.assert_not_called()
    tuner.auto_load_defaults.assert_not_called()
    assert box.background == "background"
