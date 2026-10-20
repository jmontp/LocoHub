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
