"""Small real-data preview exports and their static-site inclusion."""

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("previews", ROOT / "contributor_tools/build_data_previews.py")
PREVIEWS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREVIEWS)


def source_file(tmp_path, reverse=False):
    values = np.linspace(-0.2, 0.8, 150)
    values[24] = np.nan
    values[25] = np.inf
    phase = np.linspace(0, 100, 150)
    path = tmp_path / "tiny.parquet"
    pq.write_table(pa.table({
        "subject": ["example"] * 150, "task": ["level_walking"] * 150,
        "step": [4] * 150, "phase_ipsi": phase[::-1] if reverse else phase,
        "knee_flexion_angle_ipsi_rad": values,
        "unused_large_column": ["not exported"] * 150,
    }), path)
    return path


def test_preview_preserves_actual_rows_and_missing_values(tmp_path):
    result = PREVIEWS.read_preview(source_file(tmp_path))
    assert len(result["rows"]) == 150
    assert result["rows"][0]["knee_flexion_angle_ipsi_rad"] == pytest.approx(-0.2)
    assert result["rows"][-1]["knee_flexion_angle_ipsi_rad"] == pytest.approx(0.8)
    assert result["rows"][24]["knee_flexion_angle_ipsi_rad"] is None
    assert result["rows"][25]["knee_flexion_angle_ipsi_rad"] is None
    assert "unused_large_column" not in result["columns"]
    assert result["source"]["file_columns"] == 6
    assert result["source"]["source_sha256"] is None
    assert result["phase_display"] == "Movement (%)"


def test_preview_refuses_large_projected_row_group(tmp_path):
    result = PREVIEWS.read_preview(source_file(tmp_path), max_column_bytes=1)
    assert result["available"] is False
    assert "rows" not in result


def test_preview_does_not_sort_or_repair_bad_phase_order(tmp_path):
    result = PREVIEWS.read_preview(source_file(tmp_path, reverse=True))
    assert result["chart_available"] is False
    assert result["rows"][0]["phase_ipsi"] == 100


def test_published_previews_have_exact_sample_checksums_and_honest_sources():
    payload = json.loads((ROOT / "docs/datasets/preview_data.json").read_text())
    catalog = json.loads((ROOT / "docs/datasets/comparison_data.json").read_text())
    assert set(payload["datasets"]) == {entry["slug"] for entry in catalog["datasets"]}
    for sample in payload["datasets"].values():
        if not sample["available"]:
            assert sample["reason"]
            assert "rows" not in sample
            continue
        assert len(sample["rows"]) <= 150
        assert sample["source"]["filename"] != "locohub_example_data.parquet"
        assert "Not verified against the linked download" in sample["source"]["note"]
        encoded = json.dumps(sample["rows"], sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        assert hashlib.sha256(encoded).hexdigest() == sample["source"]["sample_sha256"]
        assert len(encoded) < 50 * 1024


def test_data_preview_javascript_parses():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is unavailable")
    subprocess.run([node, "--check", str(ROOT / "docs/javascripts/data-preview.js")], check=True)
