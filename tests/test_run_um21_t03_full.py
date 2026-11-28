"""SYNTHETIC fixtures only (fake baseline with tiny files); no research data, no launcher, no producer or audit run."""
import hashlib
import json
import pytest
from contributor_tools import run_um21_t03_full as tool

NAMES = [('S1', 'a'), ('S1', 'b'), ('S2', 'a'), ('S2', 'b'), ('S3', 'a')]
OBS = {n: i + 1 for i, n in enumerate(NAMES)}  # S1a=1 ... S3a=5 observations
DROP = [('S1', 'b'), ('S3', 'a')]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def make(tmp):
    base = tmp / 'base'
    recs, checked, cens = [], [], []
    for s, c in NAMES:
        d = base / s / c
        d.mkdir(parents=True)
        phase, ledger = f'phase-{s}{c}'.encode(), f'ledger-{s}{c}'.encode()
        (d / 'phase.parquet').write_bytes(phase)
        (d / 'candidate_ledger.jsonl').write_bytes(ledger)
        recs.append({'subject': s, 'condition': c, 'path': f'{s}/{c}/phase.parquet', 'sha256': sha(phase), 'observations': OBS[(s, c)]})
        checked.append({'subject': s, 'condition': c, 'output_sha256': sha(phase), 'ledger_sha256': sha(ledger), 'excluded_pairs': 7})
        bad = (s, c) in DROP
        cens.append({'subject': s, 'condition': c, 'alignment': {'passed': not bad, 'best_lag': 169 if bad else 0,
                                                                  'reason': 'not evaluable: synthetic' if (s, c) == ('S3', 'a') else None}})
    (base / 'conversion_summary.json').write_text(json.dumps({'source': {'sha256': 'src'}, 'recordings': recs}))
    rb = tmp / 'rb.json'
    rb.write_text(json.dumps({'status': 'all_tread_sagittal_exports_checked_unreviewed', 'source_sha256': 'src',
                              'summary_sha256': tool.digest(base / 'conversion_summary.json'), 'records': checked}))
    kept_obs = sum(v for k, v in OBS.items() if k not in DROP)
    census = tmp / 'census.json'
    census.write_text(json.dumps({'misaligned': [{'record': f'{s}/{c}'} for s, c in DROP], 'records': cens,
                                  'totals': {'misaligned': 2, 'aligned': 3, 'strides_as_published_aligned_only': kept_obs}}))
    return base, rb, census


def test_scope_keeps_baseline_order_accounts_for_every_record(tmp_path):
    base, rb, census = make(tmp_path)
    scope = tool.build_scope(base, rb, census, batch_size=2)
    assert [k['record'] for k in scope['kept']] == ['S1/a', 'S2/a', 'S2/b']
    assert scope['batches'] == [['S1/a', 'S2/a'], ['S2/b']]
    assert {(d['subject'], d['condition']): d['observations_not_converted'] for d in scope['dropped']} == {('S1', 'b'): 2, ('S3', 'a'): 5}
    assert scope['kept_observations'] == 1 + 3 + 4 and scope['baseline_observations'] == 15
    reasons = {d['subject'] + d['condition']: d['reason'] for d in scope['dropped']}
    assert reasons['S3a'].startswith('not evaluable') and 'misaligned by 169' in reasons['S1b']


def test_scope_refuses_census_total_mismatch_and_stale_readback(tmp_path):
    base, rb, census = make(tmp_path)
    c = json.loads(census.read_text())
    c['totals']['strides_as_published_aligned_only'] += 1
    census.write_text(json.dumps(c))
    with pytest.raises(tool.FullError):
        tool.build_scope(base, rb, census)
    base2, rb2, census2 = make(tmp_path / 'two') if (tmp_path / 'two').mkdir() is None else None
    r = json.loads(rb2.read_text())
    r['summary_sha256'] = '0' * 64
    rb2.write_text(json.dumps(r))
    with pytest.raises(tool.FullError):
        tool.build_scope(base2, rb2, census2)


def test_stage_records_bit_identical_in_baseline_order(tmp_path):
    base, rb, _ = make(tmp_path)
    st = tool.stage_records(base, rb, tmp_path / 'stage', ['S2/b', 'S1/a'])  # request out of order
    assert st['order'] == [('S1', 'a'), ('S2', 'b')]
    summary = json.loads(st['summary'].read_text())
    readback = json.loads(st['readback'].read_text())
    assert [(r['subject'], r['condition']) for r in summary['recordings']] == st['order']
    assert [(r['subject'], r['condition']) for r in readback['records']] == st['order']
    assert summary['planned_recordings'] == 2 and readback['summary_sha256'] == tool.digest(st['summary'])
    assert (tmp_path / 'stage/S2/b/phase.parquet').read_bytes() == b'phase-S2b'
    assert not (tmp_path / 'stage/S1/b').exists() and not (tmp_path / 'stage/S3').exists()


def test_stage_records_refuses_unknown_tampered_duplicate_existing(tmp_path):
    base, rb, _ = make(tmp_path)
    with pytest.raises(tool.FullError):
        tool.stage_records(base, rb, tmp_path / 's1', ['S9/z'])
    with pytest.raises(tool.FullError):
        tool.stage_records(base, rb, tmp_path / 's2', ['S1/a', 'S1/a'])
    tool.stage_records(base, rb, tmp_path / 's3', ['S1/a'])
    with pytest.raises(FileExistsError):
        tool.stage_records(base, rb, tmp_path / 's3', ['S1/a'])
    (base / 'S1/a/candidate_ledger.jsonl').write_bytes(b'tampered')
    with pytest.raises(tool.FullError):
        tool.stage_records(base, rb, tmp_path / 's4', ['S1/a'])


def test_commands_audit_one_record_into_its_own_new_dir(tmp_path):
    staged = {'stage_root': tmp_path / 'st', 'readback': tmp_path / 'st/rb.json'}
    p = tool.producer_command(tmp_path / 'o', staged)
    a = tool.audit_command(tmp_path / 'o', staged, 'S1', 'a', '/src.mat', 'f' * 64)
    assert '--max-recordings' not in p and p[p.index('--output-root') + 1] == str(tmp_path / 'o/components')
    assert a[a.index('--output-dir') + 1] == str(tmp_path / 'o/audit/S1_a')
    assert a[a.index('--base-root') + 1] == str(tmp_path / 'st') and a[a.index('--expected-source-sha256') + 1] == 'f' * 64


def test_producer_gate_requires_exact_membership_counts_and_status():
    scope = {'S1/a': {'observations': 2}, 'S1/b': {'observations': 3}}
    rec = lambda s, c, n, keep=True: {'subject': s, 'condition': c, 'observations_checked': n, 'existing_columns_exactly_preserved': keep}
    good = {'status': 'all_tread_joint_components_readback_unreviewed', 'records': [rec('S1', 'a', 2), rec('S1', 'b', 3)]}
    assert len(tool.producer_gate(good, [('S1', 'a'), ('S1', 'b')], scope)) == 2
    for bad in ({**good, 'status': 'partial_requested_limit'}, {**good, 'records': good['records'][:1]},
                {**good, 'records': [rec('S1', 'a', 2), rec('S1', 'b', 4)]}, {**good, 'records': [rec('S1', 'a', 2), rec('S1', 'b', 3, False)]}):
        with pytest.raises(tool.FullError):
            tool.producer_gate(bad, [('S1', 'a'), ('S1', 'b')], scope)


def test_run_with_stubbed_steps_writes_per_record_audit_status(tmp_path, monkeypatch):
    base, rb, census = make(tmp_path)
    out_base = tmp_path / 'reconv'
    out_base.mkdir()
    monkeypatch.setattr(tool, 'BASELINE', base)
    monkeypatch.setattr(tool, 'READBACK', rb)
    monkeypatch.setattr(tool, 'BASE', out_base)
    scope = tool.build_scope(base, rb, census, batch_size=2)
    scope_path = tmp_path / 'scope.json'
    scope_path.write_text(json.dumps(scope))
    fail = {'S2/a'}

    def fake_step(command, log, timeout, cwd=None):
        if 'extend' in command[1]:
            root = out_base / 'o1/components'
            root.mkdir(parents=True)
            recs = [{'subject': s, 'condition': c, 'observations_checked': OBS[(s, c)], 'existing_columns_exactly_preserved': True,
                     'source_columns': 84, 'maximum_error': 0.0, 'output_sha256': 'x', 'ledger_sha256': 'y'}
                    for s, c in [('S1', 'a'), ('S2', 'a')]]
            (root / 'conversion_summary.json').write_text(json.dumps({'status': 'all_tread_joint_components_readback_unreviewed', 'records': recs}))
            return 0
        d = command[command.index('--output-dir') + 1]
        name = f"{command[command.index('--subject') + 1]}/{command[command.index('--condition') + 1]}"
        import os
        os.makedirs(d)
        ok = name not in fail
        with open(os.path.join(d, 'audit_report.json'), 'w') as f:
            json.dump({'status': 'pass' if ok else 'fail', 'checks': {'a': {'passed': True}, 'b': {'passed': ok}}}, f)
        return 0 if ok else 1
    monkeypatch.setattr(tool.pilot, 'run_step', fake_step)

    class A:
        output_root, scope, scope_sha256, batch = out_base / 'o1', scope_path, tool.digest(scope_path), 0
        source, source_sha256 = '/src.mat', 'f' * 64
    assert tool.run(A) == 1
    s = json.loads((out_base / 'o1/run_summary.json').read_text())
    assert s['status'] == 'audit_not_passed' and s['scientific_approval'] is False
    assert s['audits']['S1/a']['status'] == 'pass' and s['audits']['S2/a']['checks_failed'] == ['b']
    assert [r['observations'] for r in s['producer_records']] == [1, 3]
    with pytest.raises(tool.FullError):  # non-empty root refused
        A.output_root = out_base / 'o1'
        tool.run(A)
    A.output_root, A.scope_sha256 = out_base / 'o2', '0' * 64
    with pytest.raises(tool.FullError):  # scope hash mismatch
        tool.run(A)
