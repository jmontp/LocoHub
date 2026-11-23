"""Generated dataset documentation must not write repo or local folder paths into visible text.

Synthetic metadata only; output goes to a temporary folder. Fails if manage_dataset_documentation.py
brings a path such as converted_datasets/... or contributor_tools/... back into the generated pages.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

mdd = pytest.importorskip("contributor_tools.manage_dataset_documentation")

BAD = re.compile(r"converted_datasets|contributor_tools|/mnt/|[A-Za-z]:\\|/home/")


def test_public_name_keeps_only_the_file_name():
    assert mdd._public_name("converted_datasets/a_phase.parquet") == "a_phase.parquet"
    assert mdd._public_name(Path("/mnt/s/x/contributor_tools/validation_ranges/default_ranges.yaml")) == "default_ranges.yaml"
    assert mdd._public_name("C:\\data\\b.parquet") == "b.parquet"


def test_generated_pages_show_no_local_paths(tmp_path, monkeypatch):
    docs = tmp_path / "docs" / "datasets"
    monkeypatch.setattr(mdd, "repo_root", tmp_path)
    monkeypatch.setattr(mdd, "DOCS_DATASETS_DIR", docs)
    monkeypatch.setattr(mdd, "DOCS_DATASETS_GENERATED_DIR", docs / ".generated")
    dataset = tmp_path / "converted_datasets" / "syn_phase.parquet"  # synthetic name; the file is never opened
    metadata = {
        "dataset_name": "syn01", "display_name": "Synthetic 1", "short_code": "SY01", "year": 2026, "institution": "Synthetic",
        "subjects": 2, "tasks": ["level_walking"], "feature_task_source": "converted_datasets/syn_phase.parquet",
        "feature_task_groups": [{"title": "Kinematics", "features": [{"name": "knee", "tasks": {"level_walking": {}}}]}],
        "validation_ranges_file": "[Download validation ranges](./syn_validation_ranges.yaml)",
        "validation_ranges_source": "contributor_tools/validation_ranges/default_ranges.yaml",
    }
    _, body = mdd.generate_dataset_page(dataset, metadata, "syn01_validation.md")
    text = body.read_text(encoding="utf-8")
    assert "syn_phase.parquet" in text and not BAD.search(text), BAD.search(text)
    validation = mdd.generate_validation_page(dataset, metadata, "Synthetic summary.", None, {}, docs / "syn01_validation.md",
                                              "syn_validation_ranges.yaml", metadata["validation_ranges_source"])
    vtext = validation.read_text(encoding="utf-8")
    assert "default_ranges.yaml" in vtext and not BAD.search(vtext), BAD.search(vtext)
