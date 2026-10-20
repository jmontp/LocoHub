"""Exercise the public data journey using only the small synthetic fixture."""

from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import urljoin, urlparse

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs/tutorials/assets"
IDENTITY = ["subject", "source_recording_id", "observation_id", "reference_side"]
SPEC = importlib.util.spec_from_file_location("static_docs", ROOT / "docs/build.py")
STATIC_DOCS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STATIC_DOCS)


def test_tutorial_files_are_equivalent_complete_v2_observations():
    from contributor_tools.common.data_contract import inspect_contract

    csv = pd.read_csv(ASSETS / "locohub_example_data.csv")
    parquet = pd.read_parquet(ASSETS / "locohub_example_data.parquet")
    pd.testing.assert_frame_equal(csv, parquet, check_dtype=False, rtol=1e-12, atol=1e-12)
    assert len(csv) == 600
    assert csv["subject"].nunique() == 2
    assert csv.groupby(IDENTITY).size().tolist() == [150] * 4
    assert csv["subject"].str.startswith("EXAMPLE_").all()
    assert csv["subject_metadata"].map(json.loads).map(lambda value: value["synthetic"]).all()
    assert csv["observation_type"].eq("individual_cycle").all()
    for _, observation in csv.groupby(IDENTITY):
        np.testing.assert_allclose(observation["phase_ipsi"], np.linspace(0, 100, 150))
    result = inspect_contract(parquet, mode="phase")
    assert result.schema_passed, result.to_dict()


def test_published_python_walkthrough_executes(monkeypatch):
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    tutorial = STATIC_DOCS.Page(ROOT / "docs/tutorials/index.html")
    tutorial.feed(tutorial.path.read_text())
    blocks = [text for language, text in tutorial.code_blocks if language == "python"]
    assert len(blocks) == 3
    monkeypatch.chdir(ASSETS)
    namespace = {}
    try:
        for index, block in enumerate(blocks, start=1):
            exec(compile(block, f"tutorial-python-{index}", "exec"), namespace)
        assert len(namespace["selected"]) == 300
        assert len(namespace["ax"].lines) == 2
        assert namespace["ax"].get_ylabel() == "Knee flexion (degrees)"
    finally:
        plt.close("all")


def test_readme_python_example_executes(monkeypatch):
    monkeypatch.chdir(ROOT)
    readme = (ROOT / "README.md").read_text()
    blocks = re.findall(r"^```python\n(.*?)^```", readme, flags=re.MULTILINE | re.DOTALL)
    assert blocks
    for block in blocks:
        namespace = {}
        exec(compile(block, "README-python", "exec"), namespace)
        assert len(namespace["df"]) == 600


def test_catalog_records_link_to_local_dataset_pages():
    records = json.loads((ROOT / "docs/datasets/comparison_data.json").read_text())["datasets"]
    assert records
    for record in records:
        assert (ROOT / f"docs/datasets/{record['slug']}/index.html").is_file()
        for key in ("clean_url", "dirty_url"):
            if record.get(key):
                assert urlparse(record[key]).scheme == "https"


def test_comparison_assets_resolve_under_project_base_path():
    page = (ROOT / "docs/datasets/comparison/index.html").read_text()
    source = re.search(r'data-source="([^"]+)"', page).group(1)
    source_url = urljoin("https://example.org/LocoHub/datasets/comparison/", source)
    assert source_url == "https://example.org/LocoHub/datasets/comparison_data.json"
    records = json.loads((ROOT / "docs/datasets/comparison_data.json").read_text())["datasets"]
    for record in records:
        for task in record.get("tasks", []):
            for plot in task.get("plots", []):
                resolved = urljoin(source_url, plot)
                assert urlparse(resolved).path.startswith("/LocoHub/datasets/")


def test_documentation_javascript_parses():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is not installed; CI checks JavaScript syntax")
    subprocess.run([node, "--check", str(ROOT / "docs/javascripts/extra.js")], check=True)


def test_authored_html_links_and_native_examples_are_complete():
    pages, assets = STATIC_DOCS.check_site()
    assert len(pages) >= 29
    tutorial = pages[(ROOT / "docs/tutorials/index.html").resolve()]
    assert tutorial.language_panels == {"python": 3, "matlab": 3}
    assert len([code for language, code in tutorial.code_blocks if language == "matlab"]) == 3
    for page in pages.values():
        assert page.example_panels >= page.example_groups
        assert page.main_count == 1
        assert "mkdocs" not in page.path.read_text().lower()
    dataset = pages[(ROOT / "docs/datasets/um21/index.html").resolve()]
    assert "Human locomotion" in " ".join(dataset.main_text)
    assert "validation" in dataset.ids
    assert any("umich_2021" in str(asset) for asset in assets)


def test_static_publisher_does_not_need_markdown_or_copy_unreferenced_files(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "index.html").write_text('<!doctype html><html><head><title>Example</title></head><body><main id="main"><h1>Example</h1><a href="sample.csv">Sample</a></main></body></html>')
    (source / "sample.csv").write_text("value\n1\n")
    (source / "private-notes.md").write_text("Do not publish")
    output = tmp_path / "output"
    pages, assets = STATIC_DOCS.build(output, source)
    assert (pages, assets) == (1, 1)
    assert (output / "index.html").read_bytes() == (source / "index.html").read_bytes()
    assert (output / "sample.csv").read_bytes() == (source / "sample.csv").read_bytes()
    assert not (output / "private-notes.md").exists()
    assert (output / ".nojekyll").exists()
    assert json.loads((output / "search_index.json").read_text())[0]["title"] == "Example"
