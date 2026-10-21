"""Keep public quality evidence faithful to the actual rules and test outcomes."""
import hashlib
from pathlib import Path

from contributor_tools.build_quality_page_data import ROOT, export_ranges, read_results
from contributor_tools.common.config_manager import ValidationConfigManager


def test_exported_boxes_use_validator_sample_mapping_and_exact_bounds():
    source = ROOT / 'contributor_tools/validation_ranges/default_ranges.yaml'
    exported = export_ranges(source)
    config = ValidationConfigManager(source)
    assert exported['sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
    for task, features in exported['tasks'].items():
        for feature, ranges in features.items():
            for rule in ranges:
                assert (rule['min'], rule['max']) == config.get_range(task, rule['phase'], feature)
                assert rule['sample_index'] == round(rule['phase'] * 149 / 100)
                assert rule['sample_phase'] == rule['sample_index'] * 100 / 149
    rule = next(r for r in exported['tasks']['level_walking']['knee_flexion_angle_ipsi_rad'] if r['phase'] == 25)
    assert rule['sample_index'] == 37
    assert rule['sample_phase'] != 25  # Report actual sampled phase, not a made-up exact match.


def test_recorded_tests_do_not_turn_skips_or_errors_into_passes(tmp_path):
    path = tmp_path / 'result.xml'
    path.write_text('<testsuites><testsuite><testcase classname="checks" name="ok"/>'
                    '<testcase classname="checks" name="missing"><skipped message="MATLAB unavailable"/></testcase>'
                    '<testcase classname="checks" name="broken"><error message="setup failed"/></testcase>'
                    '</testsuite></testsuites>')
    group = read_results(path)['checks']
    assert (group['passed'], group['failed'], group['skipped']) == (1, 1, 1)
    assert group['cases'][1]['reason'] == 'MATLAB unavailable'


def test_file_audit_never_turns_missing_evidence_or_sample_pass_into_approval():
    from contributor_tools.build_audit_evidence_page import file_status
    assert file_status([])[0] == 'Not cleared'
    assert file_status([{'severity': 'passed', 'title': 'Eight source rows match'}])[0] == 'Not cleared'
    assert file_status([{'severity': 'unknown', 'title': 'No lineage'}])[0] == 'Not cleared'
    assert file_status([{'severity': 'failure', 'title': 'Needs investigation: extreme moment'}])[0] == 'Needs investigation'
    assert file_status([{'severity': 'failure', 'title': 'Different curves share an identity'}])[0] == 'Problem found'


def test_converter_risks_are_not_attributed_to_artifacts(tmp_path):
    import json
    from contributor_tools.build_audit_evidence_page import evidence_html, GROUPS
    artifact = {'path': 'example.parquet', 'rows': 150, 'cols': 4, 'size_bytes': 1000, 'mtime_ns': 1}
    risk = {'scope': 'converter', 'severity': 'failure', 'paths': ['example.parquet'],
            'title': 'Fallback timing', 'evidence': 'Code permits a default',
            'check_scope': 'Code only', 'next_step': 'Check source events'}
    for group, _ in GROUPS:
        (tmp_path / f'{group}.json').write_text(json.dumps({'artifacts': [artifact], 'findings': [risk]}))
    page = evidence_html(tmp_path)
    assert 'audit-problem' not in page
    assert 'Not cleared' in page
    assert 'Converter-code risks' in page
    assert 'Fallback timing' in page


def test_failure_reasons_survive_export(tmp_path):
    path = tmp_path / 'failed.xml'
    path.write_text('<testsuites><testsuite><testcase name="bad" classname="checks">'
                    '<failure message="Wrong phase endpoint">details</failure></testcase></testsuite></testsuites>')
    record = read_results(path)['checks']['cases'][0]
    assert record == {'name': 'bad', 'status': 'failed', 'kind': 'failure', 'reason': 'Wrong phase endpoint'}
