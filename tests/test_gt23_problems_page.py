"""Checks for the Georgia Tech 2023 known-problems page (built from the scope file only)."""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPE = json.loads((ROOT / "docs/quality/audits/gt23-problem-scope.json").read_text(encoding="utf-8"))
PAGE = (ROOT / "docs/datasets/gt23/problems.html").read_text(encoding="utf-8")
SITE = ROOT / "site/html/datasets/gt23/problems.html"
VERDICTS = set(SCOPE["verdict_words"])


def visible(text):
    text = re.sub(r"<(style|script)\b.*?</\1>", " ", text, flags=re.S)
    attrs = " ".join(re.findall(r'(?:alt|aria-label)="([^"]*)"', text))
    return html.unescape(re.sub(r"<[^>]+>", " ", text) + " " + attrs)


def cards():
    return {m.group(1): m.group(0) for m in re.finditer(r'<article class="fix-card" id="(\w+)">.*?</article>', PAGE, re.S)}


def test_every_card_is_on_the_page_with_a_figure():
    on_page = cards()
    assert set(on_page) == {c["key"] for c in SCOPE["cards"]} and len(on_page) >= 15
    for key, art in on_page.items():
        assert "<img " in art, key
        assert f"figures/scope-{key}.svg" in art
        for src in re.findall(r'<img src="figures/([^"]+)"', art):
            assert (ROOT / "docs/datasets/gt23/figures" / src).exists(), src


def test_totals_equal_the_scope_file():
    for c in SCOPE["cards"]:
        a = sum(v[0] for v in c["grid"]["cells"].values())
        n = sum(v[1] for v in c["grid"]["cells"].values())
        t = c["totals"]
        assert (a, n) == (t["affected"], t["total"]), c["key"]
        assert html.escape(c["total_line"], quote=True) in PAGE
        assert f"{t['affected']:,}" in c["total_line"] and f"{t['total']:,}" in c["total_line"], c["key"]
        for k, v in t.items():
            if isinstance(v, int) and k not in ("affected", "total") and v >= 100:
                assert f"{v:,}" in visible(PAGE), (c["key"], k)
    d = SCOPE["denominators"]
    assert f"{d['recordings']} recordings" in visible(PAGE) and f"{d['event_windows']:,}" in visible(PAGE)
    assert SCOPE["probe"]["peak_rss_mib_self_reported"] < 300


def test_every_verdict_has_evidence_or_says_not_checked():
    for c in SCOPE["cards"]:
        assert c["knock_on"], c["key"]
        for k in c["knock_on"]:
            assert k["verdict"] in VERDICTS
            assert k["evidence"] or k["verdict"] == "Not checked", (c["key"], k["signal"])
            assert k["line"]
    assert PAGE.count('class="verdict ') == sum(len(c["knock_on"]) for c in SCOPE["cards"])


def test_status_and_denominators_are_stated():
    for c in SCOPE["cards"]:
        assert c["status"] in SCOPE["status_words"]
        assert c["denominator_text"].strip() and c["total_line"].strip()
    assert "fixed" not in {c["status"] for c in SCOPE["cards"]}  # no verified pilot receipt exists


def test_no_jargon_paths_hashes_or_ids_in_visible_text():
    text = visible(PAGE)
    banned = [r"\bdivisors?\b", r"\bcensus\b", r"\bhooks?\b", r"\bgates?\b", r"\blayouts?\b", r"\bmultipliers?\b",
              r"/mnt/", r"\.(json|py|parquet|csv|mat|sto|osim)\b", r"\b[0-9a-f]{32,}\b", r"\b[A-Z]{2,4}\d{2}-[A-Z]\d{2}\b",
              r"\bD-[A-Z0-9]+-", r"\bGT23\b", r"\bCORE-\d", r"\bsha\d*\b", r"\bPID\b"]
    for pat in banned:
        assert not re.search(pat, text, flags=re.I if pat.startswith(r"\b") and "[A-Z]" not in pat else 0), pat


def test_site_copy_matches():
    assert SITE.read_text(encoding="utf-8") == PAGE
    assert (SITE.parent / "figures" / "scope-map.svg").exists()
