"""Tiny workflow fixtures; no scientific data or process work."""
import copy
from html.parser import HTMLParser
import json
from pathlib import Path
import pytest
from contributor_tools import build_backlog_page as b


def task(task_id='NEXT', status='ready', dependencies=None):
    row = {'id': task_id, 'priority': 'P0', 'dataset': 'project', 'title': 'Check the source',
            'status': status, 'stage': 'source_inventory', 'question': 'Do source identities agree?',
            'scope': 'One metadata record', 'depends_on': dependencies or [], 'inputs': ['A documented source record'],
            'deliverables': ['A checked record'], 'acceptance': ['Exact identity agrees'],
            'next_action': 'Read the source record.', 'resource_class': 'read_only',
            'evidence_paths': ['docs/quality/audit.json'] if status == 'done' else [],
            'handoff': {'last_checked_at_utc': '2026-10-27T10:00:00Z', 'summary': 'Prepared for review.',
                        'checks': ['Identity checked'] if status == 'done' else [], 'remaining': ['Review source']}}
    if status == 'working':
        row.update(owner='fixture-agent', started_at_utc='2026-10-27T10:01:00Z')
    return row


def backlog():
    return {'schema_version': 2, 'updated_at_utc': '2026-10-27T10:00:00Z',
            'snapshot_notice': 'Maintained snapshot; no scientific approval.', 'next_task_id': 'NEXT',
            'workflow': {'statuses': {v: 'Definition of ' + v for v in sorted(b.STATUSES)},
                         'stages': {v: 'Definition of ' + v for v in sorted(b.STAGES)},
                         'handoff_rules': ['Record evidence.'], 'selection_policy': ['Read the next ready task.']},
            'datasets': [{'id': 'example', 'name': 'Example study', 'state': 'Unreviewed', 'remaining': 'Source review'}],
            'tasks': [task()]}


def test_valid_dependency_chain_and_no_mutation():
    data = backlog(); data['tasks'] = [task('SOURCE', 'done'), task(dependencies=['SOURCE'])]
    original = copy.deepcopy(data)
    assert b.validate_backlog(data) is data
    assert b.next_task(data)['id'] == 'NEXT'
    assert data == original


@pytest.mark.parametrize('fault,match', [
    ('duplicate', 'Duplicate task'), ('unknown', 'unknown dependency'), ('self', 'self dependency'),
    ('cycle', 'Cyclic'), ('unfinished', 'unfinished dependencies'), ('next_unknown', 'next_task_id'),
    ('next_blocked', 'next_task_id'), ('done_no_evidence', 'done requires'), ('done_no_checks', 'done requires'),
    ('blocked_no_reason', 'blocked_reason'), ('missing_scope', 'scope'), ('invalid_status', 'unsupported'),
    ('invalid_stage', 'unsupported'), ('invalid_resource', 'unsupported'), ('invalid_priority', 'unsupported'),
    ('timestamp', 'UTC timestamp'), ('acceptance', 'at least one'), ('dependency_twice', 'duplicate dependency')])
def test_invalid_workflows(fault, match):
    data = backlog(); t = data['tasks'][0]
    if fault == 'duplicate': data['tasks'].append(copy.deepcopy(t))
    if fault == 'unknown': t['depends_on'] = ['absent']
    if fault == 'self': t['depends_on'] = ['NEXT']
    if fault == 'cycle':
        t['depends_on'] = ['SECOND']; data['tasks'].append(task('SECOND', 'review', ['NEXT']))
    if fault == 'unfinished':
        t['depends_on'] = ['SECOND']; data['tasks'].append(task('SECOND', 'review'))
    if fault == 'next_unknown': data['next_task_id'] = 'absent'
    if fault == 'next_blocked': t.update(status='blocked', blocked_reason='Source unavailable')
    if fault == 'done_no_evidence': t.update(status='done'); t['handoff']['checks'] = ['Checked']
    if fault == 'done_no_checks': t.update(status='done', evidence_paths=['evidence'])
    if fault == 'blocked_no_reason': t['status'] = 'blocked'
    if fault == 'missing_scope': del t['scope']
    if fault.startswith('invalid_'): t[{'resource': 'resource_class'}.get(fault[8:], fault[8:])] = 'unknown'
    if fault == 'timestamp': t['handoff']['last_checked_at_utc'] = '2026-10-27'
    if fault == 'acceptance': t['acceptance'] = []
    if fault == 'dependency_twice': t['depends_on'] = ['SOURCE', 'SOURCE']
    with pytest.raises(b.BacklogError, match=match): b.validate_backlog(data)


class Document(HTMLParser):
    def __init__(self):
        super().__init__(); self.ids = []; self.links = []
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if 'id' in values: self.ids.append(values['id'])
        if tag == 'a': self.links.append(values.get('href'))


def test_html_escaping_legacy_aliases_and_existing_docs_only(tmp_path):
    docs = tmp_path / 'docs'; (docs / 'quality').mkdir(parents=True)
    (docs / 'quality/audit.json').write_text('{}')
    data = backlog(); t = data['tasks'][0]
    t['title'] = '<script>bad & worse</script>'; t['legacy_ids'] = ['NEW-01']
    t['inputs'] = ['converted_datasets/no-file.json', 'docs/quality/audit.json', 'docs/missing.json', 'javascript:alert(1)']
    data['tasks'].append(task('SECOND', 'review')); data['tasks'][-1]['legacy_ids'] = ['NEW-01']
    data['previous_snapshot'] = 'docs/quality/audit.json'
    html = b.render_backlog(data, docs)
    assert '<script>bad' not in html and '&lt;script&gt;' in html
    doc = Document(); doc.feed(html)
    assert len(doc.ids) == len(set(doc.ids)) and doc.ids.count('NEW-01') == 1
    assert '../quality/audit.json' in doc.links
    assert 'docs/missing.json' not in doc.links and 'converted_datasets/no-file.json' not in doc.links
    assert 'javascript:alert(1)' not in doc.links
    assert html.index('id="next-task"') < html.index('id="tasks"')
    assert '<h2 id="tasks">All tasks</h2>\n<details><summary>View all 2 tasks — 1 ready, 0 in progress, 0 blocked, 1 awaiting review, 0 done</summary>' in html
    assert '<details id="NEXT" open>' in html
    for href in doc.links:
        if href and href.startswith('#'): assert href[1:] in doc.ids


def gates(data):
    data['release_gates'] = [{'id': 'source', 'title': 'Source identity', 'question': 'Is the original identified?', 'evidence_required': ['Pinned original bytes']}]
    data['datasets'][0]['gate_status'] = {'source': 'partial'}
    return data


def test_release_gates_are_separate_and_missing_is_unreviewed():
    data = gates(backlog()); html = b.render_backlog(data)
    assert 'Release checks' in html and '<td>Partial</td>' in html
    del data['datasets'][0]['gate_status']['source']
    assert '<td>Unreviewed</td>' in b.render_backlog(data)


@pytest.mark.parametrize('fault', ['unknown', 'bad_status', 'duplicate_gate'])
def test_bad_gate_mappings(fault):
    data = gates(backlog())
    if fault == 'unknown': data['datasets'][0]['gate_status'] = {'absent': 'partial'}
    if fault == 'bad_status': data['datasets'][0]['gate_status']['source'] = 'ready'
    if fault == 'duplicate_gate': data['release_gates'] *= 2
    with pytest.raises(b.BacklogError): b.validate_backlog(data)


def test_cli_render_check_and_next_are_read_only_when_requested(tmp_path, capsys):
    source = tmp_path / 'backlog.json'; output = tmp_path / 'backlog.html'
    source.write_text(json.dumps(backlog())); original = source.read_bytes()
    args = ['--source', str(source), '--output', str(output)]
    assert b.main(args + ['--check']) == 1 and not output.exists()
    assert b.main(args + ['--next']) == 0 and not output.exists()
    assert '"id": "NEXT"' in capsys.readouterr().out
    assert b.main(args) == 0
    html = output.read_bytes(); assert b.main(args + ['--check']) == 0
    assert source.read_bytes() == original and output.read_bytes() == html
    output.write_text('stale')
    assert b.main(args + ['--check']) == 1 and output.read_text() == 'stale'


def test_invalid_source_preserves_html_and_duplicate_json_rejected(tmp_path):
    source = tmp_path / 'backlog.json'; output = tmp_path / 'backlog.html'; output.write_text('keep')
    source.write_text('{"schema_version":2,"schema_version":2}')
    assert b.main(['--source', str(source), '--output', str(output)]) == 1
    assert output.read_text() == 'keep'


def test_checked_in_backlog_and_generated_page_are_current():
    """CI checks the actual maintained backlog as well as synthetic graphs."""
    assert b.main(['--check']) == 0

@pytest.mark.parametrize('status', ['blocked', 'working', 'review', 'done'])
def test_no_ready_task_is_valid_without_state_mutation(status):
    data = backlog(); data['next_task_id'] = None; data['tasks'] = [task('ONLY', status)]
    if status == 'blocked': data['tasks'][0]['blocked_reason'] = 'Awaiting original source'
    original = copy.deepcopy(data)
    assert b.validate_backlog(data) is data and b.next_task(data) is None
    assert 'No task is ready to start.' in b.render_backlog(data)
    assert data == original


def test_null_next_is_invalid_if_ready_task_exists():
    data = backlog(); data['next_task_id'] = None
    with pytest.raises(b.BacklogError, match='null while ready'): b.validate_backlog(data)


@pytest.mark.parametrize('status', ['ready', 'working', 'review', 'done'])
def test_execution_states_require_finished_dependencies(status):
    data = backlog(); data['next_task_id'] = 'NEXT' if status == 'ready' else None
    data['tasks'] = [task('PREREQ', 'working'), task('NEXT', status, ['PREREQ'])]
    with pytest.raises(b.BacklogError, match='unfinished dependencies'): b.validate_backlog(data)


def test_next_cli_reports_no_ready_without_rendering(tmp_path, capsys):
    data = backlog(); data['next_task_id'] = None; data['tasks'] = [task('ONLY', 'working')]
    source = tmp_path / 'backlog.json'; source.write_text(json.dumps(data)); output = tmp_path / 'absent.html'
    assert b.main(['--source', str(source), '--output', str(output), '--next']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['status'] == 'no_ready_tasks' and result['next_task'] is None and not output.exists()


@pytest.mark.parametrize('fault', ['owner_missing', 'owner_empty', 'time_missing', 'time_not_utc'])
def test_working_requires_named_owner_and_utc_start(fault):
    data = backlog(); data['next_task_id'] = None; data['tasks'] = [task('ACTIVE', 'working')]
    t = data['tasks'][0]
    if fault == 'owner_missing': del t['owner']
    if fault == 'owner_empty': t['owner'] = ' '
    if fault == 'time_missing': del t['started_at_utc']
    if fault == 'time_not_utc': t['started_at_utc'] = '2026-10-27T10:00:00-04:00'
    with pytest.raises(b.BacklogError): b.validate_backlog(data)


def test_working_owner_and_changed_files_display():
    data = backlog(); data['next_task_id'] = None; data['tasks'] = [task('ACTIVE', 'working')]
    data['tasks'][0]['handoff']['changed_files'] = ['contributor_tools/example.py']
    html = b.render_backlog(data)
    assert 'fixture-agent' in html and '2026-10-27T10:01:00Z' in html
    assert '<code>contributor_tools/example.py</code>' in html and 'Changed files' in html
    assert b.next_task(data) is None


def test_changed_files_requires_list_of_text():
    data = backlog(); data['tasks'][0]['handoff']['changed_files'] = 'not a list'
    with pytest.raises(b.BacklogError, match='changed_files'): b.validate_backlog(data)


def verified_gate():
    data = gates(backlog())
    data['tasks'].insert(0, task('SOURCE-CHECK', 'done'))
    data['datasets'][0].update(gate_status={'source': 'verified'},
                               gate_tasks={'source': ['SOURCE-CHECK']},
                               gate_evidence={'source': ['docs/quality/source-readback.json']})
    return data


def test_verified_gate_requires_explicit_done_tasks_and_evidence():
    data = verified_gate()
    assert b.validate_backlog(data) is data
    html = b.render_backlog(data)
    assert 'Verified<br><small>Tasks: <a href="#SOURCE-CHECK">SOURCE-CHECK</a>' in html
    assert '<code>docs/quality/source-readback.json</code>' in html
    assert data['tasks'][1]['status'] == 'ready'  # no inferred task-state changes


@pytest.mark.parametrize('fault', ['missing_evidence', 'missing_tasks', 'unknown_task',
                                 'unfinished_task', 'unknown_gate', 'bad_evidence_type', 'duplicate_task'])
def test_invalid_gate_task_or_evidence_links(fault):
    data = verified_gate(); dataset = data['datasets'][0]
    if fault == 'missing_evidence': del dataset['gate_evidence']
    if fault == 'missing_tasks': del dataset['gate_tasks']
    if fault == 'unknown_task': dataset['gate_tasks']['source'] = ['absent']
    if fault == 'unfinished_task': dataset['gate_tasks']['source'] = ['NEXT']
    if fault == 'unknown_gate': dataset['gate_tasks']['absent'] = ['NEXT']
    if fault == 'bad_evidence_type': dataset['gate_evidence']['source'] = 'a path'
    if fault == 'duplicate_task': dataset['gate_tasks']['source'] *= 2
    with pytest.raises(b.BacklogError): b.validate_backlog(data)


def test_partial_gate_can_link_unfinished_tasks_without_claiming_verified():
    data = gates(backlog()); data['datasets'][0]['gate_tasks'] = {'source': ['NEXT']}
    b.validate_backlog(data)
    html = b.render_backlog(data)
    assert 'Partial<br><small>Tasks: <a href="#NEXT">NEXT</a>' in html
