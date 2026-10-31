"""Documentation policy for sign-detector adapters (CORE-04).

Provenance: 'José instruction in chat, 2026-10-30: "we should just fix both readmes based on
the evidence"', recorded verbatim by the coordinator in docs/maintainers/backlog.json in the
handoff checks of tasks GT24-C02 and GT23-C02 (confirmed authoritative). A verified audit
overrides a publisher README. Adapters pass to the detector only documentation statements that
no verified audit has refuted, and log each refuted statement with its refutation. This is a
policy implementation, not a new scientific decision.

Verification source: backlog status only. A refutation counts only if its `refuted_by_task` has
status `done` in docs/maintainers/backlog.json. Only the coordinator sets `done`, and only after
the independent verifier's `done` verdict, so the backlog status is the single authoritative
record. Verify files are not parsed: their round structure and timestamps are free-form and were
gameable.

Citation keys: every documentation item carries an exact `citation_id` such as
"gt24-readme:L90-91" (document name, colon, line or section locator; see CITATION_ID_RE).
Table entries list the refuted `citation_ids`; matching is exact string equality, never
substring.

An item (channel, sign, citation, citation_id) is withheld only when, for at least one entry of
its dataset (every matching entry is evaluated, so table order does not matter), the entry lists
the channel and the citation_id, its `refuted_sign` equals the item's sign (a statement agreeing
with the finding is kept), and its task is done. Otherwise the statement is kept and the reason
logged. Malformed input raises ValueError: a citation_id that fails CITATION_ID_RE, a statement
or refuted sign that is not the integer +1 or -1 (bools, None, strings and floats are rejected),
a missing task or channel list, or a backlog with duplicate task ids.
"""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
REFUTED_PATH = Path(__file__).with_name('refuted_documentation.json')
BACKLOG_PATH = ROOT / 'docs/maintainers/backlog.json'
INSTRUCTION_QUOTE = 'we should just fix both readmes based on the evidence'
INSTRUCTION_TASKS = ('GT24-C02', 'GT23-C02')
# <document>:<locator>; document is lower-case words joined by - _ or .; locator is a line or
# line range (L90, L90-91) or a section (S3, S3.2, S-units).
# fullmatch + ASCII: no trailing newline (as `$` would allow) and no non-ASCII digits.
CITATION_ID_RE = re.compile(r'[a-z0-9]+(?:[-_.][a-z0-9]+)*:(?:L[0-9]+(?:-[0-9]+)?|S-?[0-9A-Za-z]+(?:[-.][0-9A-Za-z]+)*)',
                            re.ASCII)


def _is_sign(x):
    return type(x) is int and x in (1, -1)  # bool is a subclass of int: excluded by the exact type check


def _check_citation_id(cid, where):
    if not isinstance(cid, str) or not CITATION_ID_RE.fullmatch(cid):
        raise ValueError(f'{where}: citation_id {cid!r} must be <document>:<locator>, e.g. "gt24-readme:L90-91"')


def load_refuted(path=REFUTED_PATH):
    table = json.loads(Path(path).read_text())
    for dataset, entries in table.get('datasets', {}).items():
        for e in entries:
            where = f'{dataset} {e.get("id")}'
            ids = e.get('citation_ids')
            if not isinstance(ids, list) or not ids:
                raise ValueError(f'{where}: citation_ids must be a non-empty list')
            for cid in ids:
                _check_citation_id(cid, where)
            if not _is_sign(e.get('refuted_sign')):
                raise ValueError(f'{where}: refuted_sign must be the integer +1 or -1')
            if not isinstance(e.get('refuted_by_task'), str) or not e['refuted_by_task'].strip():
                raise ValueError(f'{where}: refuted_by_task must name a backlog task')
            if not isinstance(e.get('channels'), list) or not e['channels']:
                raise ValueError(f'{where}: channels must be a non-empty list')
    return table


def task_done(task, backlog_path=BACKLOG_PATH):
    """(True, '') if `task` has status done in the backlog (the single authoritative record)."""
    records = json.loads(Path(backlog_path).read_text()).get('tasks', [])
    ids = [t.get('id') for t in records]
    duplicates = sorted({i for i in ids if ids.count(i) > 1}, key=str)
    if duplicates:
        raise ValueError(f'backlog has duplicate task ids {duplicates}; the status record is ambiguous')
    tasks = {t['id']: t for t in records}
    if task not in tasks:
        return False, f'{task} is not a backlog task'
    if tasks[task].get('status') != 'done':
        return False, f'{task} status is {tasks[task].get("status")!r}, not done'
    return True, ''


def split_documentation(dataset, items, path=REFUTED_PATH, backlog_path=BACKLOG_PATH):
    """items: (channel, sign, citation, citation_id). Return (kept, log); kept items are
    (channel, sign, citation) triples for detect_leg(documentation=...). One log entry per
    matched statement: action 'withheld' (a verified refutation of that sign) or 'kept'."""
    entries = load_refuted(path).get('datasets', {}).get(dataset, [])
    kept, log = [], []
    for channel, sign, citation, cid in items:
        if not _is_sign(sign):
            raise ValueError(f'{dataset} {channel}: documentation sign must be the integer +1 or -1, got {sign!r}')
        _check_citation_id(cid, f'{dataset} {channel}')
        hits = [e for e in entries if channel in e['channels'] and cid in e['citation_ids']]
        if not hits:
            kept.append((channel, sign, citation))
            continue
        withheld_by, reasons = [], []
        for e in hits:
            if e['refuted_sign'] != sign:
                reasons.append(f"{e['id']}: sign {sign:+d} agrees with the verified finding "
                               f"({e['refuted_by_task']} refutes only {e['refuted_sign']:+d})")
                continue
            ok, why = task_done(e['refuted_by_task'], backlog_path)
            if ok:
                withheld_by.append(e)
            else:
                reasons.append(f"{e['id']}: refutation by {e['refuted_by_task']} not verified ({why})")
        if withheld_by:
            by = ', '.join(sorted({x['refuted_by_task'] for x in withheld_by}))
            log.append({'channel': channel, 'sign': sign, 'citation_id': cid, 'action': 'withheld',
                        'ids': sorted(x['id'] for x in withheld_by), 'statement': withheld_by[0]['statement'],
                        'refuted_by_task': by,
                        'summary': f"{withheld_by[0]['statement']}: refuted by {by} (done); not passed as evidence",
                        'other_entries': reasons})
        else:
            kept.append((channel, sign, citation))
            log.append({'channel': channel, 'sign': sign, 'citation_id': cid, 'action': 'kept',
                        'ids': sorted(x['id'] for x in hits), 'summary': 'kept: ' + '; '.join(reasons)})
    return kept, log
