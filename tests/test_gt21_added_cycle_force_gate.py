"""Synthetic wrapper fixtures; no source data, numerical imports or subprocesses."""
import json
from pathlib import Path

import pytest

from contributor_tools import audit_gt21_added_cycle_forces as audit


@pytest.fixture
def pilot(tmp_path, monkeypatch):
    record = {'subject': 'SYNTHETIC', 'date': 'date', 'mode': 'levelground',
              'recording': 'trial.mat'}
    folders = [tmp_path / 'baseline', tmp_path / 'candidate']
    for folder in folders:
        folder.mkdir()
        (folder / 'phase.parquet').write_bytes(b'synthetic placeholder, not parquet')
        manifest = {'status': 'converted_unreviewed', 'recording': record,
                    'sources': [{'path': 'synthetic-source', 'sha256': 'fixture'}],
                    'outputs': [{'name': 'phase.parquet',
                                 'sha256': audit.digest(folder / 'phase.parquet')}]}
        (folder / 'conversion_manifest.json').write_text(json.dumps(manifest))
    baseline, candidate = folders
    code = tmp_path / 'audit_code.py'
    code.write_text('# synthetic frozen dependency\n')
    monkeypatch.setattr(audit, 'DEPENDENCIES', [code])
    monkeypatch.setattr(audit, 'observations', lambda path:
                        {'old': 'right'} if path.parent == baseline else
                        {'old': 'right', 'added': 'left'})
    report = {'status': 'completed_force_sources_checked_unreviewed',
              'records': [{'recording': record.copy(), 'observations': 2,
                           'manifest_sha256': audit.digest(candidate / 'conversion_manifest.json'),
                           'finite_values_checked': 2700, 'missing_values_checked': 900}]}
    mutate = []

    def fake_run(command, *, check, timeout):
        assert check is True and timeout == 600
        batch = Path(command[command.index('--batch-root') + 1])
        state = json.loads((batch / 'batch_status.json').read_text())
        assert state['completed'] == 1 and state['observations'] == 2
        target = batch / 'SYNTHETIC/date/levelground/trial'
        assert target.resolve() == candidate
        output = Path(command[command.index('--output-root') + 1])
        output.mkdir()
        (output / 'force_comparison.json').write_text(json.dumps(report))
        for callback in mutate:
            callback()

    monkeypatch.setattr(audit.subprocess, 'run', fake_run)
    return baseline, candidate, tmp_path / 'audit', report, code, mutate


def test_all_cycles_include_explicit_added_identity(pilot):
    baseline, candidate, output, _, _, _ = pilot
    result = audit.audit_record(candidate, baseline, output)
    assert result['status'] == 'all_pilot_cycles_force_checked_unreviewed'
    assert result['all_observations'] == 2
    assert result['added_observations'] == 1
    assert result['added_cycles'] == [{'observation_id': 'added', 'reference_side': 'left'}]
    assert result['finite_values_checked'] + result['missing_values_checked'] == 3600
    assert result['scientific_approval'] is False


@pytest.mark.parametrize('field,value', [
    ('observations', 1), ('finite_values_checked', 2699),
    ('missing_values_checked', 899), ('manifest_sha256', 'wrong'),
    ('recording', {'subject': 'OTHER'}),
])
def test_reject_incomplete_or_wrong_checker_record(pilot, field, value):
    baseline, candidate, output, report, _, _ = pilot
    report['records'][0][field] = value
    with pytest.raises(ValueError):
        audit.audit_record(candidate, baseline, output)
    assert json.loads((output / 'added_cycle_force_summary.json').read_text())['status'] == 'failed'


@pytest.mark.parametrize('changed', ['code', 'candidate_manifest', 'baseline_manifest',
                                     'candidate_output', 'baseline_output'])
def test_reject_mutation_during_readback(pilot, changed):
    baseline, candidate, output, _, code, mutate = pilot
    path = {'code': code, 'candidate_manifest': candidate / 'conversion_manifest.json',
            'baseline_manifest': baseline / 'conversion_manifest.json',
            'candidate_output': candidate / 'phase.parquet',
            'baseline_output': baseline / 'phase.parquet'}[changed]
    mutate.append(lambda: path.write_bytes(path.read_bytes() + b' '))
    with pytest.raises(ValueError):
        audit.audit_record(candidate, baseline, output)
    assert json.loads((output / 'added_cycle_force_summary.json').read_text())['status'] == 'failed'


def test_reject_empty_checker_records(pilot):
    baseline, candidate, output, report, _, _ = pilot
    report['records'] = []
    with pytest.raises(ValueError):
        audit.audit_record(candidate, baseline, output)
