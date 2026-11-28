"""GT23-M01 tests. All fixtures are SYNTHETIC with known factors; they do not regenerate any scientific dataset."""
import numpy as np
import pytest

from contributor_tools import gt23_mass as ms

README = '\n'.join(f'AB{i:02d}: {m} kg' for i, m in zip((1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13),
                                                          (78.9, 82.2, 113.5, 71.5, 79.1, 62.3, 87.6, 84.1, 67.5, 65.1, 64.0, 67.6)))


def trial(subject, task, own, cls, used=None, tier='validated_gait'):
    t = {'subject': subject, 'task': task, 'own_mass_kg': own, 'class': cls, 'tier': tier}
    if used:
        t['policy_T'] = {'divisor_kg': used, 'factor': round(used / own, 4)}
    return t


def masses():
    return ms.parse_readme_masses(README)


def test_readme_table_ab03_is_publisher_value():
    assert masses()['AB03'] == 113.5
    with pytest.raises(ms.MassError):
        ms.parse_readme_masses('AB01: 70 kg')


def test_factor_is_ratio_of_listed_masses():
    plan = ms.build_plan([trial('AB05', 'normal_walk_1', 71.5, 'lower_confident', 78.9, 'exact'),
                          trial('AB03', 'dynamic_walk_1', 113.5, 'lower_confident', 84.1)], masses())
    a, b = plan[('AB05', 'normal_walk_1')], plan[('AB03', 'dynamic_walk_1')]
    assert a['factor'] == pytest.approx(78.9 / 71.5) and a['how'] == 'exact'
    assert round(a['factor'], 4) == 1.1035
    assert b['factor'] == pytest.approx(84.1 / 113.5) and b['how'] == 'estimated'
    assert round(b['factor'], 3) == 0.741


def test_only_listed_class_is_rescaled_and_others_get_notes():
    trials = [trial('AB01', 'normal_walk_1', 78.9, 'own_mass_only'), trial('AB02', 'x_1', 82.2, 'mixed'),
              trial('AB06', 'normal_walk_1', 79.1, 'lower_confident', 71.5, 'exact'),
              trial('AB07', 'y_1', 62.3, 'lower_if_recorded_mass', 78.9), trial('AB08', 'z_1', 87.6, 'not_validated')]
    plan = ms.build_plan(trials, masses())
    counts = ms.plan_counts(plan)
    assert counts['rescaled'] == 1 and counts['kept'] == 4
    assert counts['kept_own_mass_confirmed'] == 1 and counts['kept_cannot_be_told'] == 3
    assert all(e['factor'] is None for e in plan.values() if e['action'] == 'keep')


def test_inconsistent_audit_stops():
    bad = trial('AB05', 'a_1', 71.5, 'lower_confident', 78.9, 'exact')
    bad['policy_T']['factor'] = 1.2
    with pytest.raises(ms.MassError):
        ms.build_plan([bad], masses())
    with pytest.raises(ms.MassError):
        ms.build_plan([trial('AB05', 'a_1', 70.0, 'mixed')], masses())          # own mass differs from README
    with pytest.raises(ms.MassError):
        ms.build_plan([trial('AB05', 'a_1', 71.5, 'lower_confident', 80.0)], masses())   # not a table mass


def test_scale_known_values_and_kept_is_identical_object():
    x = np.array([1.0, -2.0, np.nan, 0.0])
    y = ms.scale(x, 1.5)
    np.testing.assert_array_equal(y[[0, 1, 3]], [1.5, -3.0, 0.0])
    assert np.isnan(y[2])
    assert ms.scale(x, None) is x


def test_body_weights_known_values():
    assert ms.to_body_weights(113.5 * ms.G, 113.5) == pytest.approx(1.0)
    f = 113.5 * ms.G
    assert ms.to_body_weights(f, 82.18) == pytest.approx(113.5 / 82.18)   # the old wrong mass gives 1.38 BW
    assert 1.38 < 113.5 / 82.18 < 1.39


def test_power_consistency_invariant_to_common_factor():
    rng = np.random.default_rng(7)
    m, w = rng.normal(size=500), rng.normal(size=500)
    p = m * w * -1.0
    before = ms.power_consistency(m, p, w, -1.0)
    after = ms.power_consistency(m * 1.2345, p * 1.2345, w, -1.0)
    assert before['slope'] == pytest.approx(1.0) and before['r'] == pytest.approx(1.0)
    assert after['slope'] == pytest.approx(before['slope'], abs=1e-12)
    assert after['r'] == pytest.approx(before['r'], abs=1e-12)
    # a power that is half the product gives slope 0.5
    assert ms.power_consistency(m, 0.5 * m * w, w, 1.0)['slope'] == pytest.approx(0.5)


def test_nm_check_recovers_mass():
    rng = np.random.default_rng(3)
    per_kg = rng.normal(size=300)
    nm = per_kg * 78.9
    r = ms.nm_check(per_kg, nm, 78.9)
    assert r['max_abs_nm'] < 1e-9 and r['implied_mass_kg'] == pytest.approx(78.9)
    # rescaled by 78.9/71.5 then times own mass 71.5 equals N*m
    assert ms.nm_check(per_kg * (78.9 / 71.5), nm, 71.5)['max_abs_nm'] < 1e-9


def test_committed_audit_gives_the_decided_counts():
    """Reads the committed audit and README evidence (small files, no data arrays)."""
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    m = ms.parse_readme_masses((root / 'docs/quality/audits/source_evidence/gt23/publisher-readme.txt').read_text())
    trials = json.loads((root / 'docs/quality/audits/gt23-c05-rescale-error.json').read_text())['trials']
    c = ms.plan_counts(ms.build_plan(trials, m))
    assert (c['recordings'], c['rescaled'], c['kept']) == (488, 52, 436)
    assert (c['rescaled_exact'], c['rescaled_estimated']) == (7, 45)
    assert (c['kept_own_mass_confirmed'], c['kept_cannot_be_told']) == (2, 434)
