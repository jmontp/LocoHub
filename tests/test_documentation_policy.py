"""Documentation policy: only refutations whose task is done in the backlog withhold a statement,
matched by exact citation key (no data read; synthetic tables except the real-table tests)."""
import json

import pytest

from contributor_tools.common.documentation_policy import (BACKLOG_PATH, INSTRUCTION_QUOTE, INSTRUCTION_TASKS,
                                                            REFUTED_PATH, split_documentation)

README = 'README lines 90-91: "Hip flexion, knee extension, and ankle plantarflexion is positive"'
RID = 'gt24-readme:L90-91'
ITEMS = [('hip_angle', 1, README, RID), ('knee_angle', -1, README, RID), ('ankle_angle', -1, README, RID),
         ('ankle_moment', -1, README + ' (read as the DOF generalized-force sign)', RID)]
KEY = 'x-readme:L1'


def _world(tmp_path, entry, status='done', task='T-1', extra_tasks=()):
    table = tmp_path / 'refuted.json'
    entries = entry if isinstance(entry, list) else [entry]
    table.write_text(json.dumps({'datasets': {'X': entries}}))
    backlog = tmp_path / 'backlog.json'
    backlog.write_text(json.dumps({'tasks': [{'id': t, 'status': s} for t, s in [(task, status), *extra_tasks]]}))
    return dict(path=table, backlog_path=backlog)


ENTRY = {'id': 'x', 'statement': 'README says PF+', 'citation_ids': [KEY],
         'channels': ['ankle_angle'], 'refuted_sign': -1, 'refuted_by_task': 'T-1'}


def _item(sign=-1, cid=KEY, channel='ankle_angle'):
    return [(channel, sign, 'README line 1: PF+', cid)]


def test_real_table_withholds_only_the_gt24_readme_ankle_statement():
    kept, log = split_documentation('GT24', ITEMS)
    assert [k[0] for k in kept] == ['hip_angle', 'knee_angle']
    assert all(len(k) == 3 for k in kept)  # detector triples
    withheld = [e for e in log if e['action'] == 'withheld']
    assert {e['channel'] for e in withheld} == {'ankle_angle', 'ankle_moment'}
    assert all(e['refuted_by_task'] == 'GT24-C02' for e in withheld)


def test_instruction_quote_is_recorded_under_both_tasks_in_the_backlog():
    # The provenance cites the quote plus tasks, and the quote is in backlog.json under both.
    policy = json.loads(REFUTED_PATH.read_text())['policy']
    assert INSTRUCTION_QUOTE in policy['provenance']['quote']
    assert tuple(policy['provenance']['tasks']) == INSTRUCTION_TASKS
    tasks = {t['id']: t for t in json.loads(BACKLOG_PATH.read_text())['tasks']}
    for task in INSTRUCTION_TASKS:
        checks = tasks[task]['handoff']['checks']
        assert any(f'"{INSTRUCTION_QUOTE}"' in str(c) and 'José instruction in chat, 2026-10-30' in str(c)
                   for c in checks), task


@pytest.mark.parametrize('status', ['review', 'in_progress', 'ready', 'blocked'])
def test_backlog_status_not_done_keeps_the_statement(tmp_path, status):
    w = _world(tmp_path, ENTRY, status=status)
    kept, log = split_documentation('X', _item(), **w)
    assert len(kept) == 1 and log[0]['action'] == 'kept' and 'not done' in log[0]['summary']


def test_backlog_status_done_withholds_the_statement(tmp_path):
    w = _world(tmp_path, ENTRY, status='done')
    kept, log = split_documentation('X', _item(), **w)
    assert kept == [] and log[0]['action'] == 'withheld'


def test_refutation_naming_a_non_task_keeps_the_statement(tmp_path):
    w = _world(tmp_path, dict(ENTRY, refuted_by_task='a blog post'))
    kept, log = split_documentation('X', _item(), **w)
    assert len(kept) == 1 and 'not a backlog task' in log[0]['summary']


@pytest.mark.parametrize('near_miss', ['x-readme:L1-2', 'x-readme:L10', 'y-readme:L1', 'x-readme-v2:L1'])
def test_near_miss_citation_key_does_not_match(tmp_path, near_miss):
    # Exact keys: a key that merely shares a prefix or substring with the refuted key is not refuted.
    w = _world(tmp_path, ENTRY)
    kept, log = split_documentation('X', _item(cid=near_miss), **w)
    assert len(kept) == 1 and log == []


@pytest.mark.parametrize('bad', [':L90-91', 'L90-91', 'gt24-readme:L90-91\n', 'gt24-readme:L\u0669\u0660',
                                 'gt24-readme:L90-91 ', 'gt24-readme', 'gt24-readme:', 'gt24-readme:lines 90-91',
                                 'README lines 90-91', 'x-readme:L', 'X-README:L1', '', None])
def test_citation_id_without_document_or_locator_is_rejected(tmp_path, bad):
    w = _world(tmp_path, dict(ENTRY, citation_ids=[bad]))
    with pytest.raises(ValueError, match='citation_id'):
        split_documentation('X', _item(), **w)
    (tmp_path / 'item').mkdir()
    w = _world(tmp_path / 'item', ENTRY)
    with pytest.raises(ValueError, match='citation_id'):
        split_documentation('X', _item(cid=bad), **w)


@pytest.mark.parametrize('good', ['gt24-readme:L90-91', 'gt23-readme:L12', 'gt24-paper:S2.3', 'opensim-model:S-units'])
def test_well_formed_citation_ids_are_accepted(tmp_path, good):
    w = _world(tmp_path, dict(ENTRY, citation_ids=[good]))
    kept, log = split_documentation('X', _item(cid=good), **w)
    assert kept == [] and log[0]['action'] == 'withheld'


def test_agreeing_sign_is_kept(tmp_path):
    w = _world(tmp_path, ENTRY)
    kept, log = split_documentation('X', _item(sign=1), **w)
    assert len(kept) == 1 and log[0]['action'] == 'kept' and 'agrees' in log[0]['summary']


@pytest.mark.parametrize('sign', [True, False, None, '1', '-1', 2, 0, -1.0])
def test_statement_sign_must_be_integer_plus_or_minus_one(tmp_path, sign):
    w = _world(tmp_path, ENTRY)
    with pytest.raises(ValueError, match='documentation sign'):
        split_documentation('X', _item(sign=sign), **w)


@pytest.mark.parametrize('refuted_sign', [True, False, None, '-1', -1.0, 0])
def test_refuted_sign_must_be_integer_plus_or_minus_one(tmp_path, refuted_sign):
    # JSON true must not pass as +1.
    w = _world(tmp_path, dict(ENTRY, refuted_sign=refuted_sign))
    with pytest.raises(ValueError, match='refuted_sign'):
        split_documentation('X', _item(sign=1), **w)


@pytest.mark.parametrize('order', [0, 1])
def test_every_matching_entry_is_evaluated_in_any_order(tmp_path, order):
    # An earlier unverified entry must not hide a later verified refutation.
    unverified = dict(ENTRY, id='u', refuted_by_task='T-2')
    verified = dict(ENTRY, id='v', refuted_by_task='T-1')
    w = _world(tmp_path, [unverified, verified] if order == 0 else [verified, unverified],
               extra_tasks=[('T-2', 'review')])
    kept, log = split_documentation('X', _item(), **w)
    assert kept == [] and log[0]['action'] == 'withheld' and log[0]['ids'] == ['v']
    assert any('T-2' in r for r in log[0]['other_entries'])


def test_duplicate_backlog_task_ids_are_refused(tmp_path):
    # A second record with the same id could carry a different status; refuse rather than pick one.
    w = _world(tmp_path, ENTRY, status='done', extra_tasks=[('T-1', 'review')])
    with pytest.raises(ValueError, match='duplicate task ids'):
        split_documentation('X', _item(), **w)


def test_each_refutation_task_record_names_its_citation_or_entry():
    # Each real table entry's refuting task record in backlog.json must mention one of its
    # citation_ids or its entry id, binding the backlog record to the refuted statement.
    table = json.loads(REFUTED_PATH.read_text())
    tasks = {t['id']: json.dumps(t, ensure_ascii=False) for t in json.loads(BACKLOG_PATH.read_text())['tasks']}
    for dataset, entries in table['datasets'].items():
        for e in entries:
            record = tasks[e['refuted_by_task']]
            assert any(k in record for k in [e['id'], *e['citation_ids']]), (dataset, e['id'], e['refuted_by_task'])
