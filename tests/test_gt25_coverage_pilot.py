"""Small status/provenance fixtures; these do not assert scientific validity."""
import json
from pathlib import Path
import pytest
import contributor_tools.run_gt25_coverage_pilot as pilot


def test_shuffle_and_recovered_admission_gates():
    pilot.validate_pilot_kind('shuffle', 'normal_walk_1_baseline_shuffle_on', 100, 200, None)
    pilot.validate_pilot_kind('recovered_admission', 'sit_to_stand_1_baseline_short-arm_on', 63*1024**2, 70*1024**2, None)
    with pytest.raises(ValueError, match='64 MiB'):
        pilot.validate_pilot_kind('recovered_admission', 'sit_to_stand_1_baseline_short-arm_on', 65*1024**2, 70*1024**2, None)
    with pytest.raises(ValueError, match='original all-CSV rejection'):
        pilot.validate_pilot_kind('recovered_admission', 'sit_to_stand_1_baseline_short-arm_on', 100, 200, None)


def test_unchanged_gate_requires_ordinary_baseline():
    with pytest.raises(ValueError):
        pilot.validate_pilot_kind('unchanged', 'normal_walk_1_1-2_on', 100, 200, None)
    with pytest.raises(ValueError):
        pilot.validate_pilot_kind('unchanged', 'normal_walk_1_shuffle_on', 100, 200, Path('baseline'))


def test_snapshot_rejects_changed_or_added_code(tmp_path, monkeypatch):
    monkeypatch.setattr(pilot, 'ROOT', tmp_path)
    source = tmp_path/'source/Parsed'
    source.mkdir(parents=True)
    monkeypatch.setattr(pilot, 'SOURCE', source)
    readme = source.parent/'readme.txt'
    readme.write_text('source evidence')
    prepared = tmp_path/'converted_datasets/reconversion_v2/prepared'
    code = prepared/'isolated_repo/contributor_tools/worker.py'
    code.parent.mkdir(parents=True)
    code.write_text('x = 1\n')
    plan = {'status': 'prepared_unreviewed_not_run', 'snapshot_code': {'contributor_tools/worker.py': pilot.digest(code)},
            'readme': {'sha256': pilot.digest(readme)}}
    (prepared/'preparation_manifest.json').write_text(json.dumps(plan))
    pilot.verify_snapshot(prepared)
    code.write_text('x = 2\n')
    with pytest.raises(ValueError, match='Snapshot changed'):
        pilot.verify_snapshot(prepared)
    code.write_text('x = 1\n')
    (code.parent/'extra.py').write_text('pass\n')
    with pytest.raises(ValueError, match='dependency set changed'):
        pilot.verify_snapshot(prepared)


def test_snapshot_outside_authorized_root_rejected(tmp_path):
    with pytest.raises(ValueError, match='authorized'):
        pilot.verify_snapshot(tmp_path/'outside')


def test_manifest_rejects_changed_source_inventory_and_output(tmp_path):
    raw, code, output = (tmp_path/n for n in ['source.csv', 'worker.py', 'phase.parquet'])
    raw.write_bytes(b'synthetic source')
    code.write_text('pass\n')
    output.write_bytes(b'synthetic opaque output; not real parquet')
    sources = pilot.evidence([raw])
    d = {'status': 'converted_unreviewed', 'schema_passed': True, 'rows': 150,
         'sources': sources, 'converter_code': pilot.evidence([code]),
         'outputs': [{'name': output.name, 'sha256': pilot.digest(output)}]}
    manifest = tmp_path/'conversion_manifest.json'
    manifest.write_text(json.dumps(d))
    pilot.verify_manifest(manifest, sources)
    with pytest.raises(ValueError, match='different source inventory'):
        pilot.verify_manifest(manifest, [])
    output.write_bytes(b'changed')
    with pytest.raises(ValueError, match='output changed'):
        pilot.verify_manifest(manifest, sources)


def test_no_observations_is_not_a_passing_pilot(tmp_path):
    manifest = tmp_path/'conversion_manifest.json'
    manifest.write_text(json.dumps({'status': 'no_accepted_observations', 'rows': 0}))
    with pytest.raises(ValueError, match='nonempty'):
        pilot.verify_manifest(manifest)
