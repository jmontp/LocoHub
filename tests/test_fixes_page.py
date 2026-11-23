"""The broken-vs-fixed page shows only verified findings and never claims a release.

Reads only the committed page, backlog and verification handoffs (no data).

Inclusion rule: a card's backlog task is done and its <task>-verify.json says done.
Exception (approved 2026-10-31): exactly the two UM21-T02 cards below may
appear while UM21-T02 is not done, each marked data-rule="approved-exception",
stating the approval date, and backed by independently verified evidence.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs/quality/fixes.html"
HANDOFFS = ROOT / "docs/maintainers/handoffs"
APPROVED_EXCEPTIONS = {"um21-belt-clock": "UM21-T02", "um21-ab01-copy": "UM21-T02"}


def cards():
    text = PAGE.read_text(encoding="utf-8")
    return re.findall(r'<article class="fix-card" id="([^"]+)" data-task="([^"]+)"([^>]*)>(.*?)</article>', text, re.S)


def verify(name):
    return json.loads((HANDOFFS / f"{name}.json").read_text(encoding="utf-8"))


def round_item(record, round_key, prefix):
    found = [c for c in record[round_key]["checks"] if c["item"].startswith(prefix)]
    assert len(found) == 1, prefix
    return found[0]["result"]


def test_every_card_cites_a_done_and_independently_verified_task_and_an_audit():
    tasks = {t["id"]: t for t in json.loads((ROOT / "docs/maintainers/backlog.json").read_text())["tasks"]}
    found = cards()
    assert found
    for card_id, task, attrs, body in found:
        audits = re.findall(r'href="(audits/[^"]+\.json)"', body)
        assert audits and all((PAGE.parent / a).is_file() for a in audits), card_id
        if 'data-rule="approved-exception"' in attrs:
            continue  # checked in the exception test below
        assert tasks[task]["status"] == "done", task
        record = verify(f"{task}-verify")
        assert record.get("verdict", record.get("status")) == "done", task


def test_approved_exceptions_are_only_the_two_um21_t02_cards_with_verified_evidence():
    excepted = {card_id: (task, body) for card_id, task, attrs, body in cards() if 'data-rule="approved-exception"' in attrs}
    assert set(excepted) <= set(APPROVED_EXCEPTIONS)
    audit_verify = verify("UM21-T02-audit-verify")
    for card_id, (task, body) in excepted.items():
        assert task == APPROVED_EXCEPTIONS[card_id]
        assert "shown anyway, approved 2026-10-31" in body and f"Task {task} is not done" in body
        assert audit_verify["verdict"] == "done_for_audit_script"
    if "um21-belt-clock" in excepted:
        assert round_item(audit_verify, "round_2", "3. Independent lag spot-check") == "pass"
        assert "audits/um21-t02-clock-census.json" in excepted["um21-belt-clock"][1]
    if "um21-ab01-copy" in excepted:
        assert verify("UM21-SLOPE-verify")["verdict"] == "done"
        assert round_item(audit_verify, "round_2", "4. Duplicate claim").startswith("pass")
        assert "audits/um21-midstance-slope.json" in excepted["um21-ab01-copy"][1]
        backlog = json.loads((ROOT / "docs/maintainers/backlog.json").read_text())
        remaining = [t for t in backlog["tasks"] if t["id"] == "UM21-T02"][0]["handoff"]["remaining"]
        assert any("Coordinator resolution (2026-10-31): D-UM21-T02-2 withdrawn" in r
                   and "AB01 i10 passes the clock and slope checks and stays" in r for r in remaining)
        assert "coordinator resolution under D-UM21-T02-1 = A" in excepted["um21-ab01-copy"][1]


def test_no_card_claims_corrected_files_are_released():
    for card_id, _, _, body in cards():
        label = re.search(r'<span class="fix-label"[^>]*>(.*?)</span>', body).group(1).lower()
        assert "not yet" in label or "no new" in label, card_id
        assert "fixed in released" not in body.lower(), card_id


def test_each_card_has_figures_with_alt_text_that_exist():
    for card_id, _, _, body in cards():
        images = re.findall(r'<img src="([^"]+)"[^>]*alt="([^"]+)"', body)
        assert images, card_id
        for src, alt in images:
            assert (PAGE.parent / src).is_file() and alt.strip(), (card_id, src)
