"""The site shows only the datasets listed in docs/site_datasets.json; the others are hidden, not deleted.

Reads the committed docs (small HTML and JSON). Synthetic dictionaries test the JSON filter.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
spec = importlib.util.spec_from_file_location("static_docs_hidden", DOCS / "build.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)

LISTING = json.loads((DOCS / "site_datasets.json").read_text(encoding="utf-8"))
SHOWN = set(LISTING["shown"])


def test_the_list_is_the_three_datasets_being_rebuilt():
    assert SHOWN == {"um21", "gt21", "gt23"}
    assert not SHOWN & {d["slug"] for d in LISTING["later"]}


def test_hidden_pages_stay_on_disk_but_are_not_built_pages_or_assets():
    hidden = B.hidden_datasets(DOCS)
    assert {"gt24", "ga26", "mb24", "sp50", "gt25d", "fu18"} <= hidden and not hidden & SHOWN
    for slug in hidden:
        assert (DOCS / "datasets" / slug / "index.html").is_file(), f"{slug} must stay on disk"
    pages, assets = B.check_site(DOCS)  # also fails on any link to a hidden page or file
    for path in pages:
        parts = path.relative_to(DOCS.resolve()).parts
        assert not (parts[0] == "datasets" and len(parts) > 2 and parts[1] in hidden), path
    for asset in assets:
        assert B.hidden_reference(asset.relative_to(DOCS.resolve()).as_posix(), hidden) is None, asset


def test_a_link_to_a_hidden_page_is_an_error(tmp_path):
    (tmp_path / "datasets" / "aa01").mkdir(parents=True)
    (tmp_path / "datasets" / "aa01" / "index.html").write_text(
        '<!doctype html><html><head><title>A</title></head><body><main id="main"><h1>A</h1></main></body></html>')
    (tmp_path / "datasets" / "bb02").mkdir()
    (tmp_path / "datasets" / "bb02" / "index.html").write_text(
        '<!doctype html><html><head><title>B</title></head><body><main id="main"><h1>B</h1></main></body></html>')
    (tmp_path / "site_datasets.json").write_text(json.dumps({"shown": ["aa01"]}))
    (tmp_path / "index.html").write_text(
        '<!doctype html><html><head><title>T</title></head><body><main id="main"><a href="datasets/aa01/index.html">a</a>'
        '<a href="datasets/bb02/index.html">b</a></main></body></html>')
    try:
        B.check_site(tmp_path)
    except ValueError as error:
        assert "datasets/bb02/index.html" in str(error) and "datasets/aa01/index.html" not in str(error)
    else:
        raise AssertionError("a link to a hidden dataset page must fail the check")


def test_published_json_lists_drop_hidden_datasets():
    hidden = {"gt24"}
    listing = B.filter_hidden_json({"datasets": [{"slug": "um21"}, {"slug": "gt24"}]}, hidden)
    assert listing == {"datasets": [{"slug": "um21"}]}
    keyed = B.filter_hidden_json({"version": 2, "datasets": {"um21": {}, "gt24": {}}}, hidden)
    assert keyed == {"version": 2, "datasets": {"um21": {}}}


def test_publish_writes_a_filtered_copy_and_never_changes_the_source(tmp_path):
    source = tmp_path / "comparison_data.json"
    source.write_text(json.dumps({"datasets": [{"slug": "um21"}, {"slug": "gt24"}]}))
    out = tmp_path / "out.json"
    B.publish_file(source, out, {"gt24"}, "datasets/comparison_data.json")
    assert json.loads(out.read_text()) == {"datasets": [{"slug": "um21"}]}
    assert len(json.loads(source.read_text())["datasets"]) == 2


def catalog(path):
    return (DOCS / path).read_text(encoding="utf-8")


def test_catalog_copies_list_only_the_shown_datasets_and_a_closed_plain_text_later_section():
    for name in ("index.html", "datasets/index.html"):
        text = catalog(name)
        assert set(re.findall(r'<tr id="(\w+)" data-dataset', text)) == SHOWN, name
        assert ">3 datasets<" in text
        later = re.search(r"<!-- FUTURE_START -->(.*?)<!-- FUTURE_END -->", text, re.S)
        assert later, name
        block = later.group(1)
        assert block.startswith("<details") and " open" not in block.split(">", 1)[0]
        assert "<a " not in block and "href" not in block  # plain text: those pages are not built
        for entry in LISTING["later"]:
            assert entry["name"] in block
        for group_name in LISTING["later_group"]["names"]:
            assert group_name in block
        every_other = {d["slug"] for d in LISTING["later"]} | set(LISTING["later_group"]["slugs"])
        assert not every_other & SHOWN and len(every_other) == 19
        assert f"Coming later ({len(every_other)} datasets)" in block


def test_fixes_page_has_cards_only_for_shown_datasets():
    text = catalog("quality/fixes.html")
    ids = re.findall(r'<article class="fix-card" id="([^"]+)"', text)
    assert ids and all(i.split("-")[0] in SHOWN for i in ids)
    compare = catalog("datasets/comparison/index.html")
    assert all(i.split("-")[0] in SHOWN for i in re.findall(r'class="ovf-item" id="ovf-([^"]+)"', compare))


def test_quality_page_status_cards_only_for_shown_datasets():
    cards = re.findall(r'<article class="status-card" id="status-(\w+)"', catalog("quality/index.html"))
    assert set(cards) == SHOWN
    assert set(re.findall(r'data-audit-dataset="(\w+)"', catalog("quality/index.html"))) <= SHOWN


def test_status_script_only_touches_shown_dataset_pages():
    import sys
    sys.path.insert(0, str(ROOT / "contributor_tools"))
    import dataset_status as S
    touched = {p.relative_to(DOCS).parts[1] for p, _ in S.targets(S.load_backlog()) if p.parent.parent.name == "datasets"}
    assert touched == SHOWN
