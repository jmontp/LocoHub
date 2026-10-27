#!/usr/bin/env python3
"""Validate the maintained task backlog and render its static HTML page.

This tool never changes task states or launches work. JSON is the source of truth.
"""
import argparse
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
STATUSES = {'ready', 'working', 'review', 'blocked', 'done'}
STAGES = {'source_inventory', 'conventions', 'conversion', 'pilot', 'source_readback',
          'quality', 'release', 'operations', 'documentation'}
RESOURCES = {'read_only', 'fixture', 'numerical', 'native'}
PRIORITIES = {'P0', 'P1', 'P2'}
GATE_STATES = {'unreviewed', 'partial', 'verified', 'not_applicable'}
ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]*$')


class BacklogError(ValueError):
    """A task or dependency cannot be interpreted safely."""


def _text(value, context):
    if not isinstance(value, str) or not value.strip():
        raise BacklogError(f'{context}: expected nonempty text')


def _strings(value, context, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        raise BacklogError(f'{context}: expected a list' + (' with at least one item' if nonempty else ''))
    for item in value:
        _text(item, context)


def _utc(value, context):
    _text(value, context)
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if stamp.tzinfo is None or stamp.utcoffset() != timezone.utc.utcoffset(stamp):
            raise ValueError('UTC offset required')
    except ValueError as error:
        raise BacklogError(f'{context}: expected an ISO8601 UTC timestamp') from error


def validate_backlog(data):
    """Raise BacklogError for invalid v2 data; return the unchanged data otherwise."""
    if not isinstance(data, dict) or type(data.get('schema_version')) is not int or data['schema_version'] != 2:
        raise BacklogError('schema_version must be 2')
    _utc(data.get('updated_at_utc'), 'updated_at_utc')
    _text(data.get('snapshot_notice'), 'snapshot_notice')
    if 'next_task_id' not in data:
        raise BacklogError('next_task_id: required (null when no tasks are ready)')
    if data['next_task_id'] is not None:
        _text(data['next_task_id'], 'next_task_id')
    if 'previous_snapshot' in data:
        _text(data['previous_snapshot'], 'previous_snapshot')
    workflow = data.get('workflow')
    if not isinstance(workflow, dict):
        raise BacklogError('workflow: expected definitions and handoff rules')
    for key, required in [('statuses', STATUSES), ('stages', STAGES)]:
        definitions = workflow.get(key)
        if not isinstance(definitions, dict) or set(definitions) != required:
            raise BacklogError(f'workflow.{key}: expected definitions for {", ".join(sorted(required))}')
        for value in definitions.values():
            _text(value, f'workflow.{key}')
    for key in ('handoff_rules', 'selection_policy'):
        _strings(workflow.get(key), f'workflow.{key}', nonempty=True)
    gates = data.get('release_gates', [])
    if not isinstance(gates, list):
        raise BacklogError('release_gates: expected a list')
    gate_ids = set()
    for gate in gates:
        if not isinstance(gate, dict):
            raise BacklogError('release gate: expected an object')
        for key in ('id', 'title', 'question'):
            _text(gate.get(key), f'release_gate.{key}')
        if not ID.fullmatch(gate['id']) or gate['id'] in gate_ids:
            raise BacklogError(f'Duplicate or invalid release gate id: {gate["id"]}')
        gate_ids.add(gate['id'])
        _strings(gate.get('evidence_required'), f'release_gate.{gate["id"]}.evidence_required', True)
    datasets = data.get('datasets')
    if not isinstance(datasets, list):
        raise BacklogError('datasets: expected a list')
    dataset_ids = set()
    for dataset in datasets:
        if not isinstance(dataset, dict):
            raise BacklogError('dataset: expected an object')
        for key in ('id', 'name', 'state', 'remaining'):
            _text(dataset.get(key), f'dataset.{key}')
        if dataset['id'] in dataset_ids:
            raise BacklogError(f'Duplicate dataset id: {dataset["id"]}')
        dataset_ids.add(dataset['id'])
        gate_status = dataset.get('gate_status', {})
        if not isinstance(gate_status, dict):
            raise BacklogError('dataset.gate_status: expected a mapping')
        for key, value in gate_status.items():
            if key not in gate_ids or not isinstance(value, str) or value not in GATE_STATES:
                raise BacklogError(f'{dataset["id"]}.gate_status: unknown gate or status {key!r}: {value!r}')
    tasks = data.get('tasks')
    if not isinstance(tasks, list) or not tasks:
        raise BacklogError('tasks: expected at least one task')
    by_id = {}
    anchors = {'main', 'next-task', 'tasks', 'datasets', 'workflow', 'task-details'}
    aliases = set()
    for task in tasks:
        if not isinstance(task, dict):
            raise BacklogError('task: expected an object')
        for key in ('id', 'priority', 'dataset', 'title', 'status', 'stage', 'question', 'scope', 'next_action', 'resource_class'):
            _text(task.get(key), f'task.{key}')
        task_id = task['id']
        if not ID.fullmatch(task_id):
            raise BacklogError(f'Invalid task id: {task_id}')
        if task_id in by_id:
            raise BacklogError(f'Duplicate task id: {task_id}')
        for key, choices in [('priority', PRIORITIES), ('status', STATUSES), ('stage', STAGES), ('resource_class', RESOURCES)]:
            if task[key] not in choices:
                raise BacklogError(f'{task_id}.{key}: unsupported value {task[key]!r}')
        for key in ('depends_on', 'inputs', 'deliverables', 'acceptance', 'evidence_paths'):
            _strings(task.get(key), f'{task_id}.{key}', key in ('deliverables', 'acceptance'))
        if len(set(task['depends_on'])) != len(task['depends_on']):
            raise BacklogError(f'{task_id}: duplicate dependency')
        legacy = task.get('legacy_ids', [])
        _strings(legacy, f'{task_id}.legacy_ids')
        if task_id in anchors or task_id in aliases:
            raise BacklogError(f'Duplicate or invalid task anchor: {task_id}')
        anchors.add(task_id)
        for anchor in legacy:
            if not ID.fullmatch(anchor) or anchor in anchors:
                raise BacklogError(f'Duplicate or invalid task anchor: {anchor}')
            aliases.add(anchor)
        handoff = task.get('handoff')
        if not isinstance(handoff, dict):
            raise BacklogError(f'{task_id}.handoff: required')
        _utc(handoff.get('last_checked_at_utc'), f'{task_id}.handoff.last_checked_at_utc')
        _text(handoff.get('summary'), f'{task_id}.handoff.summary')
        for key in ('checks', 'remaining'):
            _strings(handoff.get(key), f'{task_id}.handoff.{key}')
        if 'changed_files' in handoff:
            _strings(handoff['changed_files'], f'{task_id}.handoff.changed_files')
        if task['status'] == 'working':
            _text(task.get('owner'), f'{task_id}.owner')
            _utc(task.get('started_at_utc'), f'{task_id}.started_at_utc')
        if task['status'] == 'blocked':
            _text(task.get('blocked_reason'), f'{task_id}.blocked_reason')
        if task['status'] == 'done' and (not task['evidence_paths'] or not handoff['checks']):
            raise BacklogError(f'{task_id}: done requires evidence_paths and handoff checks')
        by_id[task_id] = task
    for dataset in datasets:
        for field in ('gate_tasks', 'gate_evidence'):
            mapping = dataset.get(field, {})
            if not isinstance(mapping, dict):
                raise BacklogError(f'{dataset["id"]}.{field}: expected a mapping')
            for gate_id, values in mapping.items():
                if gate_id not in gate_ids:
                    raise BacklogError(f'{dataset["id"]}.{field}: unknown gate {gate_id}')
                _strings(values, f'{dataset["id"]}.{field}.{gate_id}')
                if field == 'gate_tasks':
                    if len(set(values)) != len(values):
                        raise BacklogError(f'{dataset["id"]}.{field}.{gate_id}: duplicate task link')
                    for task_id in values:
                        if task_id not in by_id:
                            raise BacklogError(f'{dataset["id"]}.{field}.{gate_id}: unknown task {task_id}')
        for gate_id, status in dataset.get('gate_status', {}).items():
            if status != 'verified':
                continue
            evidence = dataset.get('gate_evidence', {}).get(gate_id, [])
            linked = dataset.get('gate_tasks', {}).get(gate_id, [])
            if not evidence or not linked:
                raise BacklogError(f'{dataset["id"]}.{gate_id}: verified gate requires evidence and linked tasks')
            pending = [task_id for task_id in linked if by_id[task_id]['status'] != 'done']
            if pending:
                raise BacklogError(f'{dataset["id"]}.{gate_id}: verified gate has unfinished tasks: {", ".join(pending)}')
    for task in tasks:
        for dep in task['depends_on']:
            if dep == task['id']:
                raise BacklogError(f'{task["id"]}: self dependency')
            if dep not in by_id:
                raise BacklogError(f'{task["id"]}: unknown dependency {dep}')
    # Iterative traversal also handles large queues without a recursion limit.
    indegree = {key: len(task['depends_on']) for key, task in by_id.items()}
    children = {key: [] for key in by_id}
    for task in tasks:
        for dep in task['depends_on']:
            children[dep].append(task['id'])
    available = [key for key, count in indegree.items() if count == 0]
    visited = 0
    while available:
        key = available.pop()
        visited += 1
        for child in children[key]:
            indegree[child] -= 1
            if indegree[child] == 0:
                available.append(child)
    if visited != len(tasks):
        raise BacklogError('Cyclic dependencies: ' + ', '.join(sorted(key for key, count in indegree.items() if count)))
    for task in tasks:
        pending = [dep for dep in task['depends_on'] if by_id[dep]['status'] != 'done']
        if task['status'] in {'ready', 'working', 'review', 'done'} and pending:
            raise BacklogError(f'{task["id"]}: {task["status"]} task has unfinished dependencies: {", ".join(pending)}')
    ready = [task for task in tasks if task['status'] == 'ready']
    if data['next_task_id'] is None:
        if ready:
            raise BacklogError('next_task_id cannot be null while ready tasks exist')
    else:
        selected = by_id.get(data['next_task_id'])
        if selected is None or selected['status'] != 'ready':
            raise BacklogError('next_task_id must identify an existing ready task')
    return data


def next_task(data):
    """Return the explicitly selected, validated task; never pick or mutate a task."""
    validate_backlog(data)
    return next((task for task in data['tasks'] if task['id'] == data['next_task_id']), None)


def _label(value):
    return value.replace('_', ' ').capitalize()


def _reference(value, docs_root):
    """Only HTTP(S) evidence and actual files inside docs receive hyperlinks."""
    safe = escape(value, quote=True)
    try:
        parsed = urlsplit(value)
    except ValueError:
        return f'<code>{safe}</code>'
    if parsed.scheme in ('https', 'http') and parsed.netloc:
        return f'<a href="{safe}">{safe}</a>'
    if not parsed.scheme and not parsed.query and value.startswith('docs/'):
        target = (docs_root.parent / parsed.path).resolve()
        if target.is_relative_to(docs_root.resolve()) and target.is_file():
            href = os.path.relpath(target, docs_root / 'maintainers').replace(os.sep, '/')
            if parsed.fragment:
                href += '#' + parsed.fragment
            return f'<a href="{escape(href, quote=True)}"><code>{safe}</code></a>'
    return f'<code>{safe}</code>'


def render_backlog(data, docs_root=None):
    """Return deterministic HTML. No filesystem writes or task-state transitions."""
    validate_backlog(data)
    docs_root = Path(docs_root) if docs_root is not None else ROOT / 'docs'
    esc = lambda value: escape(value, quote=True)
    def items(values, references=False):
        if not values:
            return '<p>None recorded.</p>'
        return '<ul>' + ''.join('<li>' + (_reference(v, docs_root) if references else esc(v)) + '</li>' for v in values) + '</ul>'
    def detail(task):
        deps = ', '.join(f'<a href="#{esc(dep)}">{esc(dep)}</a>' for dep in task['depends_on']) or 'None'
        handoff = task['handoff']
        content = [f'<p><strong>Question:</strong> {esc(task["question"])}</p>',
                   f'<p><strong>Scope:</strong> {esc(task["scope"])}</p>',
                   f'<p><strong>Next action:</strong> {esc(task["next_action"])}</p>',
                   f'<p><strong>Depends on:</strong> {deps} · <strong>Resources:</strong> {esc(_label(task["resource_class"]))}</p>']
        if task['status'] == 'working':
            content.append(f'<p><strong>Owner:</strong> {esc(task["owner"])} · <strong>Started:</strong> <time datetime="{esc(task["started_at_utc"])}">{esc(task["started_at_utc"])}</time></p>')
        if task['status'] == 'blocked':
            content.append(f'<p><strong>Blocked:</strong> {esc(task["blocked_reason"])}</p>')
        for title, key, ref in [('Inputs', 'inputs', True), ('Deliverables', 'deliverables', False), ('Acceptance checks', 'acceptance', False), ('Evidence', 'evidence_paths', True)]:
            content.append(f'<h4>{title}</h4>' + items(task[key], ref))
        content.extend([f'<h4>Latest handoff</h4><p>{esc(handoff["summary"])}</p>',
                        f'<p>Checked <time datetime="{esc(handoff["last_checked_at_utc"])}">{esc(handoff["last_checked_at_utc"])}</time>.</p>',
                        '<p><strong>Checks completed</strong></p>' + items(handoff['checks']),
                        '<p><strong>Still needed</strong></p>' + items(handoff['remaining'])])
        if 'changed_files' in handoff:
            content.append('<p><strong>Changed files</strong></p>' + items(handoff['changed_files'], True))
        return '\n'.join(content)
    selected = next_task(data)
    counts = {status: sum(task['status'] == status for task in data['tasks']) for status in STATUSES}
    count_labels = {'ready': 'ready', 'working': 'in progress', 'blocked': 'blocked', 'review': 'awaiting review', 'done': 'done'}
    task_summary = (f'View all {len(data["tasks"])} tasks — ' +
                    ', '.join(f'{counts[status]} {count_labels[status]}' for status in ('ready', 'working', 'blocked', 'review', 'done')))
    if selected is None:
        next_card = '<p>No task is ready to start. Read the active handoffs and blocked reasons below; do not bypass unfinished prerequisites.</p>'
    else:
        next_card = (f'<h3><a href="#{esc(selected["id"])}">{esc(selected["id"])} — {esc(selected["title"])}</a></h3>'
                     f'<p>{esc(selected["dataset"])} · {esc(selected["priority"])} · {esc(_label(selected["stage"]))}</p>'
                     f'<p>{esc(selected["question"])}</p><p><strong>Start here:</strong> {esc(selected["next_action"])}</p>')
    out = ['<!doctype html>', '<html lang="en">', '<head>', '<meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width, initial-scale=1">',
           '<title>Work backlog · LocoHub</title>', '<link rel="stylesheet" href="../stylesheets/site.css">',
           '<script src="../javascripts/extra.js" defer></script>', '</head>', '<body>',
           '<a class="skip-link" href="#main">Skip to content</a>',
           '<header class="site-header"><div class="header-inner"><a class="wordmark" href="../index.html">LocoHub</a>',
           '<nav class="primary-nav" aria-label="Main navigation"><a href="../index.html">Data</a><a href="../tutorials/index.html">Tutorials</a><a href="../reference/index.html">File format</a><a href="../quality/index.html">Testing &amp; data quality</a></nav>',
           '<a class="repository-link" href="https://github.com/jmontp/LocoHub">GitHub</a></div></header>',
           '<div class="page-layout"><main id="main" class="page-content" tabindex="-1">',
           '<h1>Work backlog</h1>', f'<p>{esc(data["snapshot_notice"])}</p>',
           f'<p>Updated <time datetime="{esc(data["updated_at_utc"])}">{esc(data["updated_at_utc"])}</time>. <a href="backlog.json">Task list (JSON)</a></p>',
           '<nav aria-label="Backlog sections"><a href="#next-task">Next task</a> · <a href="#tasks">All tasks</a> · <a href="#datasets">Datasets</a> · <a href="#workflow">Working rules</a></nav>',
           '<section id="next-task"><h2>Next task</h2>',
           next_card,
           '<p>Read the task’s inputs and handoff before starting. This page does not start jobs or change task states.</p></section>',
           '<h2 id="tasks">All tasks</h2>',
           f'<details><summary>{esc(task_summary)}</summary>',
           '<div class="table-scroll"><table><caption>Maintained task states, not live process monitoring</caption><thead><tr><th>Task</th><th>Dataset</th><th>Priority</th><th>Status</th><th>Stage</th><th>Depends on</th></tr></thead><tbody>']
    for task in data['tasks']:
        deps = ', '.join(f'<a href="#{esc(dep)}">{esc(dep)}</a>' for dep in task['depends_on']) or '—'
        out.append(f'<tr><th scope="row"><a href="#{esc(task["id"])}">{esc(task["id"])}: {esc(task["title"])}</a></th><td>{esc(task["dataset"])}</td><td>{esc(task["priority"])}</td><td>{esc(_label(task["status"]))}</td><td>{esc(_label(task["stage"]))}</td><td>{deps}</td></tr>')
    out.extend(['</tbody></table></div></details>', '<h2 id="datasets">Dataset status</h2>', '<div class="table-scroll"><table><thead><tr><th>Dataset</th><th>Current state</th><th>Still needed</th></tr></thead><tbody>'])
    for dataset in data['datasets']:
        out.append(f'<tr><th scope="row">{esc(dataset["name"])}</th><td>{esc(dataset["state"])}</td><td>{esc(dataset["remaining"])}</td></tr>')
    out.append('</tbody></table></div>')
    if data.get('release_gates'):
        out.extend(['<h3>Release checks</h3>', '<p>These checks describe the data, separately from task progress. Unreviewed: evidence not checked. Partial: some evidence exists, but the check remains open. Verified: the recorded check is satisfied. Not applicable: the check does not apply. An omitted status is shown as unreviewed.</p>', '<div class="table-scroll"><table><thead><tr><th>Dataset</th>'])
        for gate in data['release_gates']:
            out.append(f'<th>{esc(gate["title"])}</th>')
        out.append('</tr></thead><tbody>')
        for dataset in data['datasets']:
            out.append(f'<tr><th scope="row">{esc(dataset["name"])}</th>')
            for gate in data['release_gates']:
                status = dataset.get('gate_status', {}).get(gate['id'], 'unreviewed')
                cell = esc(_label(status))
                links = dataset.get('gate_tasks', {}).get(gate['id'], [])
                if links:
                    cell += '<br><small>Tasks: ' + ', '.join(f'<a href="#{esc(task_id)}">{esc(task_id)}</a>' for task_id in links) + '</small>'
                evidence = dataset.get('gate_evidence', {}).get(gate['id'], [])
                if evidence:
                    cell += '<details><summary>Evidence</summary>' + items(evidence, True) + '</details>'
                out.append('<td>' + cell + '</td>')
            out.append('</tr>')
        out.append('</tbody></table></div><details><summary>Evidence needed for each release check</summary>')
        for gate in data['release_gates']:
            out.extend([f'<h4>{esc(gate["title"])}</h4><p>{esc(gate["question"])}</p>', items(gate['evidence_required'])])
        out.append('</details>')
    out.append('<h2 id="task-details">Task handoffs</h2>')
    rendered_aliases = set()
    for task in data['tasks']:
        for alias in task.get('legacy_ids', []):
            if alias not in rendered_aliases:
                out.append(f'<span id="{esc(alias)}"></span>')
                rendered_aliases.add(alias)
        out.append(f'<details id="{esc(task["id"])}"' + (' open' if selected and task['id'] == selected['id'] else '') + f'><summary>{esc(task["id"])} — {esc(task["title"])} · {esc(_label(task["status"]))}</summary>')
        out.append(detail(task))
        out.append('</details>')
    out.extend(['<section id="workflow"><h2>Working rules</h2>', '<h3>Choosing work</h3>', items(data['workflow']['selection_policy']), '<h3>Leaving a handoff</h3>', items(data['workflow']['handoff_rules'])])
    for title, key in [('Task states', 'statuses'), ('Stages', 'stages')]:
        out.append(f'<h3>{title}</h3><dl>')
        for name, description in data['workflow'][key].items():
            out.append(f'<dt>{esc(_label(name))}</dt><dd>{esc(description)}</dd>')
        out.append('</dl>')
    out.append('</section>')
    if 'previous_snapshot' in data:
        out.append('<p>Previous snapshot: ' + _reference(data['previous_snapshot'], docs_root) + '</p>')
    if 'historical_scope' in data:
        out.append('<details><summary>Historical scope record</summary><pre>' + esc(json.dumps(data['historical_scope'], indent=2, ensure_ascii=False)) + '</pre></details>')
    out.extend(['</main></div>', '</body>', '</html>', ''])
    return '\n'.join(out)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise BacklogError(f'Duplicate JSON field: {key}')
        result[key] = value
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'docs/maintainers/backlog.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/maintainers/backlog.html')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='Validate JSON and require current generated HTML')
    mode.add_argument('--next', action='store_true', help='Print the selected ready task as JSON without writing')
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.source.read_text(encoding='utf-8'), object_pairs_hook=_unique_object)
        validate_backlog(data)
        if args.next:
            selected = next_task(data)
            print(json.dumps(selected if selected is not None else {'status': 'no_ready_tasks', 'next_task': None, 'message': 'No task is ready; review active handoffs and blocked prerequisites.'}, indent=2, ensure_ascii=False))
            return 0
        html = render_backlog(data)
        if args.check:
            if not args.output.is_file() or args.output.read_text(encoding='utf-8') != html:
                raise BacklogError(f'{args.output}: HTML is missing or stale; run the renderer')
            print(f'Backlog valid; HTML current ({len(data["tasks"])} tasks).')
            return 0
        # Validate and render fully before replacing the generated page.
        temp = args.output.with_name(args.output.name + '.tmp')
        temp.write_text(html, encoding='utf-8')
        temp.replace(args.output)
        print(f'Rendered {args.output} ({len(data["tasks"])} tasks).')
        return 0
    except (BacklogError, OSError, json.JSONDecodeError) as error:
        print(f'Backlog error: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
