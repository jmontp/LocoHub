"""SYNTHETIC fixtures only (fake baseline with tiny files); no research data, no launcher, no producer run."""
import hashlib
import json
import sys
import pytest
from contributor_tools import run_um21_t02_pilot as tool


def sha(b):
    return hashlib.sha256(b).hexdigest()


def make_baseline(tmp, names=(('S1', 'a'), ('S1', 'b'), ('S2', 'a'))):
    base = tmp / 'base'
    recs, checked = [], []
    for s, c in names:
        d = base / s / c
        d.mkdir(parents=True)
        phase, ledger = f'phase-{s}{c}'.encode(), f'ledger-{s}{c}'.encode()
        (d / 'phase.parquet').write_bytes(phase)
        (d / 'candidate_ledger.jsonl').write_bytes(ledger)
        recs.append({'subject': s, 'condition': c, 'path': f'{s}/{c}/phase.parquet', 'sha256': sha(phase), 'observations': 1})
        checked.append({'subject': s, 'condition': c, 'output_sha256': sha(phase), 'ledger_sha256': sha(ledger)})
    summary = {'source': {'sha256': 'src'}, 'recordings': recs, 'planned_recordings': 3, 'available_recordings': 3}
    (base / 'conversion_summary.json').write_text(json.dumps(summary))
    rb = tmp / 'rb.json'
    rb.write_text(json.dumps({'status': 'all_tread_sagittal_exports_checked_unreviewed', 'source_sha256': 'src',
                              'summary_sha256': tool.digest(base / 'conversion_summary.json'), 'records': checked}))
    return base, rb


def test_stage_keeps_one_record_bit_identical(tmp_path):
    base, rb = make_baseline(tmp_path)
    st = tool.stage_base(base, rb, tmp_path / 'stage', 'S1', 'b')
    summary = json.loads(st['summary'].read_text())
    readback = json.loads(st['readback'].read_text())
    assert [(r['subject'], r['condition']) for r in summary['recordings']] == [('S1', 'b')]
    assert [(r['subject'], r['condition']) for r in readback['records']] == [('S1', 'b')]
    assert summary['planned_recordings'] == 1
    assert readback['summary_sha256'] == tool.digest(st['summary'])
    assert (tmp_path / 'stage/S1/b/phase.parquet').read_bytes() == b'phase-S1b'
    assert not (tmp_path / 'stage/S1/a').exists()
    assert sorted(p.name for p in (tmp_path / 'stage').iterdir()) == ['S1', 'conversion_summary.json', 'source_comparison.json']


def test_stage_refuses_unknown_changed_or_existing(tmp_path):
    base, rb = make_baseline(tmp_path)
    with pytest.raises(tool.PilotError):
        tool.stage_base(base, rb, tmp_path / 's1', 'S9', 'z')
    tool.stage_base(base, rb, tmp_path / 's2', 'S1', 'a')
    with pytest.raises(FileExistsError):
        tool.stage_base(base, rb, tmp_path / 's2', 'S1', 'a')
    (base / 'S1/a/phase.parquet').write_bytes(b'tampered')
    with pytest.raises(tool.PilotError):
        tool.stage_base(base, rb, tmp_path / 's3', 'S1', 'a')


def test_stage_refuses_stale_readback(tmp_path):
    base, rb = make_baseline(tmp_path)
    d = json.loads(rb.read_text())
    d['summary_sha256'] = '0' * 64
    rb.write_text(json.dumps(d))
    with pytest.raises(tool.PilotError):
        tool.stage_base(base, rb, tmp_path / 's', 'S1', 'a')


def test_commands_use_staged_base_and_new_outputs(tmp_path):
    staged = {'stage_root': tmp_path / 'st', 'readback': tmp_path / 'st/source_comparison.json'}
    p, a = tool.commands(tmp_path / 'out', staged, 'S1', 'a', '/src.mat', 'f' * 64)
    assert p[1].endswith('extend_umich_tread_source.py') and '--max-recordings' not in p
    assert a[a.index('--base-root') + 1] == str(tmp_path / 'st')
    assert a[a.index('--pilot-root') + 1] == p[p.index('--output-root') + 1]
    assert a[a.index('--expected-source-sha256') + 1] == 'f' * 64


def test_run_step_logs_and_never_overwrites(tmp_path):
    assert tool.run_step([sys.executable, '-c', 'print(1)'], tmp_path / 'l.log', 30, cwd=tmp_path) == 0
    assert tool.run_step([sys.executable, '-c', 'raise SystemExit(3)'], tmp_path / 'm.log', 30, cwd=tmp_path) == 3
    with pytest.raises(FileExistsError):
        tool.run_step([sys.executable, '-c', 'pass'], tmp_path / 'l.log', 30, cwd=tmp_path)


def _patch(monkeypatch, tmp_path, codes, audit_status='pass'):
    base, rb = make_baseline(tmp_path)
    root = tmp_path / 'reconv'
    root.mkdir()
    monkeypatch.setattr(tool, 'BASE', root)
    monkeypatch.setattr(tool, 'BASELINE', base)
    monkeypatch.setattr(tool, 'READBACK', rb)
    calls = []

    def fake(command, log, timeout, cwd=None):  # synthetic stand-in for producer and audit
        calls.append(command[1])
        name = 'producer' if len(calls) == 1 else 'audit'
        if name == 'audit' and codes[1] == 0:
            out = log.parent / 'audit'
            out.mkdir()
            (out / 'audit_report.json').write_text(json.dumps({'status': audit_status}))
        return codes[0 if name == 'producer' else 1]
    monkeypatch.setattr(tool, 'run_step', fake)
    out = root / 'pilot'
    args = ['run', '--output-root', str(out), '--record', 'S1/a', '--source', '/x.mat', '--source-sha256', 'f' * 64]
    return out, args, calls


def test_run_passes_and_summarises(tmp_path, monkeypatch):
    out, args, calls = _patch(monkeypatch, tmp_path, (0, 0))
    assert tool.main(args) == 0
    s = json.loads((out / 'run_summary.json').read_text())
    assert s['status'] == 'pilot_passed_unreviewed' and s['audit_status'] == 'pass' and len(calls) == 2


def test_run_stops_after_producer_failure_and_audit_not_passed(tmp_path, monkeypatch):
    out, args, calls = _patch(monkeypatch, tmp_path, (3, 0))
    assert tool.main(args) == 1 and len(calls) == 1
    assert json.loads((out / 'run_summary.json').read_text())['status'] == 'producer_failed'


def test_run_refuses_nonempty_root_and_foreign_root(tmp_path, monkeypatch):
    out, args, _ = _patch(monkeypatch, tmp_path, (0, 0))
    out.mkdir()
    (out / 'x').write_text('x')
    with pytest.raises(tool.PilotError):
        tool.main(args)
    args[2] = str(tmp_path / 'elsewhere')
    with pytest.raises(tool.PilotError):
        tool.main(args)
