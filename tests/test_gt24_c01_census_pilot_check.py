"""Synthetic checks of the GT24-C01 census-pilot checker (no GT24 data are read).

All documents below are made up; trial names are the probe's fixed CENSUS_PILOT trials, divisors are invented.
"""
import copy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / 'contributor_tools/audit_probes/2026_10_31/check_gt24_c01_census_pilot.py'


@pytest.fixture(scope='module')
def check():
    spec = importlib.util.spec_from_file_location('check_gt24_c01_census_pilot', CHECK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope='module')
def census_pilot(check):
    return check.load_probe().CENSUS_PILOT


def _match(phase, subject, field, source='README', own=True, relation=None):
    h = {'source': source, 'phase': phase, 'subject': subject, 'field': field, 'own_row': own, 'kg': 80.0, 'abs_log': 0.0}
    if relation:
        h['relation'] = relation
    return h


def passing_docs(census_pilot):
    """A synthetic census-pilot output, first-pilot output and receipt that meet every criterion."""
    results, first = [], []
    for i, (ph, subj, rec, why) in enumerate(census_pilot['fixed_trials']):
        t = {'phase': ph, 'subject': subj, 'recording': rec, 'identity': {}, 'identity_divisor_kg': None,
             'identity_class': 'not_exact', 'identity_match_split': {'own_readme_row': [], 'own_statics': [], 'other_candidates': []}}
        if why == 'v1 too_few_samples':
            t['identity'] = {'hip_flexion_l': {'class': 'short_not_exact', 'short_rule_failed': 'power_identity_not_exact'},
                             'knee_angle_l': {'class': 'too_few_samples'}}
        else:
            d = 70.0 + i                                            # invented divisor
            t.update(identity_class='exact', identity_divisor_kg=d)
            first.append({'phase': ph, 'subject': subj, 'recording': rec, 'identity_divisor_kg': d})
            if subj == 'BT09':
                t['identity_match_split'] = {'own_readme_row': [_match(ph, 'BT09', 'model_day1_with_exo_kg')], 'own_statics': [],
                                             'other_candidates': [_match('Phase3', 'BT13', 'participant_day1_kg', own=False, relation='other_folder')]}
            else:
                t['identity_match_split'] = {'own_readme_row': [], 'other_candidates': [],
                                             'own_statics': [_match(ph, subj, 'model ids 7', source='Statics')]}
        results.append(t)
    doc = {'stage': 'census_pilot', 'zips_unchanged': True, 'peak_rss_mib': 240.0, 'seconds_per_trial': 0.5,
           'runtime_seconds': 12.0, 'results': results}
    receipt = {'status': 'completed', 'exit_code': 0, 'clean_success': True, 'checks': {'cleanup_proven': True}}
    return doc, {'results': first}, receipt


def test_all_criteria_pass_on_a_passing_synthetic_run(check, census_pilot):
    doc, first, receipt = passing_docs(census_pilot)
    out = check.evaluate(doc, first, receipt, census_pilot)
    assert [c['criterion'] for c in out] == census_pilot['pass_criteria']
    assert all(c['pass'] for c in out)
    assert out[5]['evidence']['projected_full_census_s'] == pytest.approx(0.5 * 2421)
    assert out[5]['evidence']['split_by_phase'] is False


def test_v1_divisor_change_of_1e9_fails_regression(check, census_pilot):
    doc, first, receipt = passing_docs(census_pilot)
    t = next(t for t in doc['results'] if t['subject'] == 'BT09')
    t['identity_divisor_kg'] *= 1 + 1e-9
    out = check.evaluate(doc, first, receipt, census_pilot)
    assert out[1]['pass'] is False
    assert [c['pass'] for i, c in enumerate(out) if i != 1] == [True] * 5


def test_short_trial_labelled_exact_fails(check, census_pilot):
    doc, first, receipt = passing_docs(census_pilot)
    doc['results'][0]['identity_class'] = 'exact'
    assert check.evaluate(doc, first, receipt, census_pilot)[2]['pass'] is False


def test_short_not_exact_without_reason_fails(check, census_pilot):
    doc, first, receipt = passing_docs(census_pilot)
    del doc['results'][0]['identity']['hip_flexion_l']['short_rule_failed']
    assert check.evaluate(doc, first, receipt, census_pilot)[2]['pass'] is False


def test_bt09_without_flagged_other_candidate_fails(check, census_pilot):
    doc, first, receipt = passing_docs(census_pilot)
    for t in doc['results']:
        if t['subject'] == 'BT09':
            t['identity_match_split']['other_candidates'] = []
    assert check.evaluate(doc, first, receipt, census_pilot)[3]['pass'] is False


def test_bt18_with_an_own_readme_match_fails(check, census_pilot):
    doc, first, receipt = passing_docs(census_pilot)
    t = next(t for t in doc['results'] if t['subject'] == 'BT18')
    t['identity_match_split']['own_readme_row'] = [_match('Phase3', 'BT18', 'model_day1_with_exo_kg')]
    assert check.evaluate(doc, first, receipt, census_pilot)[4]['pass'] is False


def test_slow_pilot_fails_time_and_asks_for_split(check, census_pilot):
    doc, first, receipt = passing_docs(census_pilot)
    doc['seconds_per_trial'] = 0.9                                  # 0.9 x 2421 = 2178.9 s >= 0.6 x 3600 = 2160 s
    t = check.evaluate(doc, first, receipt, census_pilot)[5]
    assert t['pass'] is False and t['evidence']['split_by_phase'] is True


@pytest.mark.parametrize('field, value', [('status', 'timed_out'), ('exit_code', 1)])
def test_failed_run_or_memory_fails_integrity(check, census_pilot, field, value):
    doc, first, receipt = passing_docs(census_pilot)
    bad = copy.deepcopy(receipt)
    bad[field] = value
    assert check.evaluate(doc, first, bad, census_pilot)[0]['pass'] is False
    doc['peak_rss_mib'] = 600.0
    assert check.evaluate(doc, first, receipt, census_pilot)[0]['pass'] is False
