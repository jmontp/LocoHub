"""Checks for the Georgia Tech 2021 problems page against its scope JSON (page text is plain words)."""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPE = json.loads((ROOT / "docs/quality/audits/gt21-problem-scope.json").read_text(encoding="utf-8"))
PAGE = (ROOT / "docs/datasets/gt21/problems.html").read_text(encoding="utf-8")
BODY = PAGE.split('<main id="main"', 1)[1].split("</main>", 1)[0]
TEXT = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<style.*?</style>", "", BODY, flags=re.S)))


def n(x):
    return f"{x:,}"


def test_every_scope_line_and_total_is_on_the_page():
    for p in SCOPE["problems"]:
        assert html.escape(p["total_line"], quote=True) in BODY, p["key"]
        assert html.escape(p["denominator_text"], quote=True) in BODY, p["key"]


def test_headline_totals_equal_json():
    d = SCOPE["denominators"]
    assert d["publisher_participants"] == 22 and d["missing_participants"] == 6 and d["local_recordings"] == 2301
    assert d["rebuilt_recordings"] == 102 and d["rebuilt_steps"] == 1299
    for v in (n(d["local_recordings"]), n(d["rebuilt_recordings"]), n(d["rebuilt_steps"]), n(d["acquired_recordings_of_six"])):
        assert v in TEXT
    miss = next(p for p in SCOPE["problems"] if p["key"] == "missing_participants")
    assert miss["total_numbers"]["recordings_missing"] == sum(int(r[1].replace(",", "")) for r in miss["table"]["rows"])
    assert sum(d["local_recordings_by_task"].values()) == 2301


def test_grid_totals_match_tables():
    for p in SCOPE["problems"]:
        g = p["grid"]
        assert len(g["cells"]) == len(g["rows"]) * len(g["cols"])
        assert (ROOT / f"docs/datasets/gt21/figures/scope-{p['key']}.svg").exists()


def test_every_verdict_has_evidence_or_says_not_checked():
    words = set(SCOPE["verdict_words"])
    for p in SCOPE["problems"]:
        assert p["knock_on"], p["key"]
        for k in p["knock_on"]:
            assert k["verdict"] in words
            if k["verdict"] != "Not checked":
                assert k["evidence"].strip(), (p["key"], k["signal"])
            else:
                assert not k["evidence"].strip()
    assert BODY.count("No evidence yet.") == sum(1 for p in SCOPE["problems"] for k in p["knock_on"] if not k["evidence"])


def test_every_card_has_a_figure_and_status():
    cards = re.findall(r'<article class="fix-card".*?</article>', BODY, flags=re.S)
    assert len(cards) == len(SCOPE["problems"])
    for c in cards:
        assert "<img " in c and 'class="status ' in c
    assert set(p["status"]["label"] for p in SCOPE["problems"]) <= {"Fixed in a checked pilot", "Decided by José, fix not yet run", "Open", "Documented only, kept as published"}
    for img in re.findall(r'src="(figures/[^"]+)"', PAGE):
        assert (ROOT / "docs/datasets/gt21" / img).exists()


def test_no_jargon_hashes_paths_or_ids_in_visible_text():
    low = TEXT.lower()
    for w in ("census", "hook", "gate", "layout", "multiplier", "divisor"):
        assert not re.search(rf"\b{w}\b", low), w
    assert not re.search(r"\b[0-9a-f]{32,}\b", low)
    assert not re.search(r"\b[A-Z]{2,5}\d{0,2}-[A-Z]?\d{2}\b", TEXT.replace("AB", "ab"))  # task ids such as GT21-C01
    assert not re.search(r"D-[A-Z0-9]+-[A-Z0-9]+-\d", TEXT)
    for bad in ("contributor_tools", "docs/", ".json", ".py", ".parquet", ".mat", "converted_datasets", "/mnt/", "GT21"):
        assert bad not in TEXT, bad
