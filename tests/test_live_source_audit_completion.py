"""A terminal converter can publish its final recording during an audit call."""
import json
import sys

import pytest

from contributor_tools import audit_gt21_native_batch as audit


@pytest.mark.parametrize('completed,status,expected_status', [
    (2, 'complete_unreviewed', 'all_recordings_source_checked_unreviewed'),
    (1, 'stopped_incomplete', 'checked_completed_subset_unreviewed'),
])
def test_final_manifest_is_read_after_record_check(tmp_path, monkeypatch, completed, status, expected_status):
    batch = tmp_path / 'batch'
    mass = tmp_path / 'mass'
    out = tmp_path / 'audit'
    batch.mkdir()
    mass.mkdir()
    (mass / 'subject_masses.csv').write_text('Subject,Weight\nAB06,72\n')
    (mass / 'source_comparison.json').write_text(json.dumps({
        'native_exact_mass_readback': True,
        'csv_sha256': audit.digest(mass / 'subject_masses.csv'),
    }))
    plan = [{'subject': 'AB06', 'date': 'test', 'mode': 'treadmill', 'recording': f'trial{i}.mat'}
            for i in range(2)]
    (batch / 'inventory.json').write_text(json.dumps({'recordings': plan}))
    (batch / 'batch_status.json').write_text(json.dumps({'completed': 1, 'status': 'running'}))
    calls = []

    def check(folder, masses, evidence):
        calls.append(folder.name)
        # Simulate the producer's final atomic manifest becoming visible while
        # the checker is still processing its previous snapshot.
        (batch / 'batch_status.json').write_text(json.dumps({'completed': completed, 'status': status}))
        return {'observations': 1, 'rows': 150, 'finite_values_checked': 10,
                'unexported_source_event_pairs': {}}

    monkeypatch.setattr(audit, 'check_record', check)
    monkeypatch.setattr(audit, 'ensure_storage_headroom', lambda _: None)
    monkeypatch.setattr(audit.resource, 'setrlimit', lambda *_: None)
    monkeypatch.setattr(sys, 'argv', ['audit', '--batch-root', str(batch), '--output-root', str(out),
                                     '--mass-evidence', str(mass)])
    audit.main()
    result = json.loads((out / 'audit_status.json').read_text())
    assert len(calls) == result['checked_recordings'] == completed
    assert result['status'] == expected_status
    assert result['batch_summary_sha256'] == audit.digest(batch / 'batch_status.json')
