"""Synthetic checks of the GT24-C01 divisor probe estimators (no GT24 data are read).

All signals here are made up; known divisors and masses are planted and must be recovered.
"""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

PATH = Path(__file__).resolve().parents[1] / 'contributor_tools/audit_probes/2026_10_31/probe_gt24_c01_divisors.py'


@pytest.fixture(scope='module')
def probe():
    spec = importlib.util.spec_from_file_location('probe_gt24_c01_divisors', PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def synthetic_moment(n=4000, seed=1):
    t = np.arange(n) / 200.0
    rng = np.random.default_rng(seed)
    return np.sin(2 * np.pi * 0.9 * t) + 0.3 * np.sin(2 * np.pi * 2.7 * t + 0.4) + 0.01 * rng.standard_normal(n)


def test_exact_identity_recovers_planted_divisor_and_sign(probe):
    d = synthetic_moment()                      # synthetic (net - bio), N*m/kg
    x = -85.14 * d                              # synthetic interaction torque, N*m, opposite sign convention
    x[:50] = np.nan
    r = probe.ratio_estimate(x, d)
    assert r['class'] == 'exact'
    assert r['sign'] == -1
    assert r['divisor_kg'] == pytest.approx(85.14, rel=1e-9)


def test_noisy_proportion_is_not_called_exact(probe):
    d = synthetic_moment()
    rng = np.random.default_rng(2)
    x = 70.0 * d + 0.5 * rng.standard_normal(d.size)
    r = probe.ratio_estimate(x, d)
    assert r['class'] == 'proportional_not_exact'
    assert r['divisor_kg'] == pytest.approx(70.0, rel=0.01)


def test_unrelated_signals_have_no_identity(probe):
    rng = np.random.default_rng(3)
    r = probe.ratio_estimate(rng.standard_normal(4000), synthetic_moment())
    assert r['class'] == 'no_identity'


def test_mass_match_separates_day_one_and_day_two(probe):
    cands = [{'source': 'README', 'phase': 'Phase1And2', 'subject': 'BT06', 'field': 'model_day1_with_exo_kg', 'kg': 85.78},
             {'source': 'README', 'phase': 'Phase1And2', 'subject': 'BT06', 'field': 'model_day2_with_exo_kg', 'kg': 85.14}]
    hits = probe.match(85.1400004, cands, probe.RULES['mass_match_max_abs_log'])
    assert [h['field'] for h in hits] == ['model_day2_with_exo_kg']


def test_statics_prefix_does_not_confuse_trial_1_and_10(probe):
    statics = {'stairs_3_1': {}, 'stairs_3_10': {}, 'normal_walk_1_1': {}}
    assert probe.statics_trial(statics, 'stairs_3_10_down_on') == 'stairs_3_10'
    assert probe.statics_trial(statics, 'stairs_3_1_up_on') == 'stairs_3_1'
    assert probe.statics_trial(statics, 'jump_1_1_hop_on') is None


def test_plate_mass_recovers_planted_worn_mass(probe):
    m, g, n_stride = 84.84, probe.G, 220          # synthetic 1.1 s strides at 200 Hz
    phase = (np.arange(30 * n_stride) % n_stride) / n_stride
    right = np.where(phase < 0.6, np.sin(np.pi * phase / 0.6), 0.0)
    left = np.where(((phase + 0.5) % 1) < 0.6, np.sin(np.pi * ((phase + 0.5) % 1) / 0.6), 0.0)
    scale = m * g / np.mean(right + left)
    p = probe.plate_mass(left * scale, right * scale)
    assert p['class'] == 'estimated'
    assert p['mass_kg'] == pytest.approx(m, rel=2e-3)


def test_lever_divisor_recovers_planted_divisor(probe):
    n_st, n_sw, D = 120, 100, 74.96               # synthetic stances of 0.6 s
    fy, fx, copx = [], [], []
    for _ in range(12):
        s = np.linspace(0, 1, n_st)
        fy += list(800 * np.sin(np.pi * s)) + [0.0] * n_sw
        fx += list(-100 * np.cos(np.pi * s)) + [0.0] * n_sw
        copx += list(-0.05 + 0.25 * s) + [0.0] * n_sw
    fy, fx, copx = np.array(fy), np.array(fx), np.array(copx)
    pred = -((copx - 0.04877) * fy + 0.04195 * fx)
    lv = probe.lever_divisor(fx, fy, copx, pred / D)
    assert lv['class'] == 'estimated'
    assert lv['implied_divisor_kg_uncorrected'] == pytest.approx(D, rel=1e-6)


@pytest.mark.parametrize('d_net, d_x, bias, shares', [
    (84.84, 84.84, 0.9942, True),    # same divisor, GT23 lever bias
    (77.79, 84.84, 0.9942, False),   # net moments divided by body mass, interaction by worn mass
    (84.84, 84.84, 0.89, False),     # same divisor, but the lever bias does not transfer (0.89)
    (84.84, 84.84, 1.0, True),       # same divisor, bias 1.0
])
def test_e3_classification_against_external_bias(probe, d_net, d_x, bias, shares):
    implied = d_net / bias           # lever implied divisor = D_net / b (synthetic)
    result = {'phase': 'Phase3', 'subject': 'BTxx', 'identity_divisor_kg': d_x, 'identity_matches': [],
              'lever': {'l': {'implied_divisor_kg_uncorrected': implied,
                              'log_ratio_to_identity': float(np.log(implied / d_x))}}}
    probe.summarize([result])
    assert result['lever']['l']['shares_identity_divisor_if_bias_transfers'] is shares


# ---------------------------------------------------------------- rule v2 (short trials) and census reporting
# All signals and trial names below are synthetic. The two masses in the BT09/BT13 case (88.97 and 88.99 kg)
# are README-printed values quoted by the GT24-C01 verifier; the divisor 88.97209 is the pilot's BT09 value.

def short_trial(probe, n, d_moment=85.14, d_power=85.14, seed=1, noise=0.0):
    """Synthetic (identity, power_identity) column results for one joint; n_used is about n / 4."""
    d = synthetic_moment(n=n, seed=seed)                           # synthetic (net - bio), N*m/kg
    rng = np.random.default_rng(seed + 100)
    x = -d_moment * d * (1 + noise * rng.standard_normal(n))       # synthetic interaction torque, N*m
    vel = 300.0 * synthetic_moment(n=n, seed=seed + 7)              # synthetic joint velocity, deg/s
    p = x * np.deg2rad(vel) / d_power                              # synthetic power_exo, W/kg
    return probe.ratio_estimate(x, d), probe.ratio_estimate(x * np.deg2rad(vel), p)


def test_rule_v2_is_versioned_and_v1_entries_unchanged(probe):
    assert probe.RULES['identity_min_samples'] == 200
    assert probe.RULES['identity_exact_max_rel_spread'] == 1e-3
    v2 = probe.RULES['identity_short_rule_v2']
    assert v2['version'] == 2 and v2['min_samples'] == 50 and v2['applies_below'] == 200
    assert v2['max_rel_spread'] == 1e-9 and v2['require_power_identity'] and v2['label'] == 'exact_short'
    assert 'reason' in v2 and 'after' in v2['added']


def test_long_column_with_1e6_noise_is_still_v1_exact(probe):
    m, _ = short_trial(probe, 4000, noise=1e-6)                           # n_used ~1000 >= 200: v1 rule
    assert m['n_used'] >= 200
    assert m['class'] == 'exact'
    assert m['divisor_kg'] == pytest.approx(85.14, rel=1e-5)


def test_short_column_with_1e6_noise_is_not_exact_short(probe):
    m, p = short_trial(probe, 600, noise=1e-6)                            # n_used ~150: same noise fails the 1e-9 gate
    assert 50 <= m['n_used'] < 200
    assert m['class'] == 'short_not_exact'
    ident, power = {'hip_flexion_l': m}, {'hip_flexion_l': p}
    probe.promote_short(ident, power)
    assert probe.trial_identity(ident)['identity_class'] == 'not_exact'


def test_short_exact_identity_with_exact_power_is_exact_short(probe):
    m, p = short_trial(probe, 600)
    assert m['class'] == 'short_candidate' and p['class'] == 'short_candidate'
    ident, power = {'hip_flexion_l': m}, {'hip_flexion_l': p}
    probe.promote_short(ident, power)
    assert ident['hip_flexion_l']['class'] == 'exact_short'
    assert power['hip_flexion_l']['class'] == 'exact_short'
    t = probe.trial_identity(ident)
    assert t['identity_class'] == 'exact_short'                    # never counted as v1 'exact'
    assert t['identity_divisor_kg'] == pytest.approx(85.14, rel=1e-12)


def test_short_column_below_50_samples_stays_too_few(probe):
    m, _ = short_trial(probe, 150)                                        # n_used ~38
    assert m['n_used'] < 50
    assert m['class'] == 'too_few_samples'


def test_short_without_power_identity_is_not_promoted(probe):
    m, _ = short_trial(probe, 600)
    ident, power = {'knee_angle_r': m}, {'knee_angle_r': {'class': 'column_absent'}}
    probe.promote_short(ident, power)
    assert ident['knee_angle_r']['class'] == 'short_not_exact'
    assert ident['knee_angle_r']['short_rule_failed'] == 'power_identity_not_exact'


def test_short_with_power_divisor_off_by_1e6_is_not_promoted(probe):
    m, p = short_trial(probe, 600, d_power=85.14 * (1 + 1e-6))
    ident, power = {'knee_angle_r': m}, {'knee_angle_r': p}
    probe.promote_short(ident, power)
    assert ident['knee_angle_r']['short_rule_failed'] == 'power_divisor_disagrees'
    assert power['knee_angle_r']['class'] == 'short_not_exact'


def test_short_joints_that_disagree_are_not_promoted(probe):
    m1, p1 = short_trial(probe, 600, d_moment=85.14, d_power=85.14, seed=1)
    m2, p2 = short_trial(probe, 600, d_moment=85.78, d_power=85.78, seed=2)   # day-1 vs day-2 style mismatch
    ident, power = {'hip_flexion_l': m1, 'knee_angle_l': m2}, {'hip_flexion_l': p1, 'knee_angle_l': p2}
    probe.promote_short(ident, power)
    assert {v['short_rule_failed'] for v in ident.values()} == {'joints_disagree'}
    assert probe.trial_identity(ident)['identity_class'] == 'not_exact'


def test_v1_exact_trial_is_not_reclassified_by_a_short_column(probe):
    long_m, long_p = short_trial(probe, 4000, seed=3)                     # v1 exact, 85.14
    short_m, short_p = short_trial(probe, 600, d_moment=85.15, d_power=85.15, seed=4)
    ident = {'hip_flexion_l': long_m, 'knee_angle_l': short_m}
    power = {'hip_flexion_l': long_p, 'knee_angle_l': short_p}
    before = dict(long_m)
    probe.promote_short(ident, power)
    assert ident['hip_flexion_l'] == before                        # v1 column untouched
    assert ident['knee_angle_l']['short_rule_failed'] == 'joints_disagree'
    t = probe.trial_identity(ident)
    assert t['identity_class'] == 'exact'
    assert t['identity_divisor_kg'] == pytest.approx(85.14, rel=1e-12)


def synthetic_meta():
    """Synthetic README table with two real printed values (BT09 worn day 1, BT13 Phase3 body day 1)."""
    return {'readme': {'phase_masses': {
        'Phase1And2': {'BT09': {'participant_day1_kg': 82.50, 'model_day1_with_exo_kg': 88.97}},   # 82.50: made up
        'Phase3': {'BT13': {'participant_day1_kg': 88.99, 'model_day1_with_exo_kg': 96.00}}}},     # 96.00: made up
        'phase3_static_models': {}}


def test_own_row_match_is_reported_apart_from_other_folder_match(probe):
    cands = probe.candidates(synthetic_meta(), 'Phase1And2', 'BT09')
    hits = probe.match(88.97209, cands, probe.RULES['mass_match_max_abs_log'])
    assert len(hits) == 2                                          # 88.99 is inside 0.05 % of 88.97209
    s = probe.split_matches(hits, 'BT09')
    assert [(h['subject'], h['field']) for h in s['own_readme_row']] == [('BT09', 'model_day1_with_exo_kg')]
    assert [(h['subject'], h['field'], h['relation']) for h in s['other_candidates']] == \
        [('BT13', 'participant_day1_kg', 'other_folder')]
    assert s['own_statics'] == []


def test_census_summary_flags_other_candidates_and_missing_own_rows(probe):
    cands = probe.candidates(synthetic_meta(), 'Phase1And2', 'BT09')
    hits = probe.match(88.97209, cands, probe.RULES['mass_match_max_abs_log'])
    bt09 = {'phase': 'Phase1And2', 'subject': 'BT09', 'recording': 'synthetic_walk', 'identity': {},
            'identity_class': 'exact', 'identity_divisor_kg': 88.97209, 'identity_divisor_spread_rel': 0.0,
            'identity_match_split': probe.split_matches(hits, 'BT09')}
    statics_only = {'phase': 'Phase3', 'subject': 'BTzz', 'recording': 'synthetic_stairs', 'identity': {},
                    'identity_class': 'exact_short', 'identity_divisor_kg': 84.8435, 'identity_divisor_spread_rel': 0.0,
                    'identity_match_split': {'own_readme_row': [], 'other_candidates': [],
                                             'own_statics': [{'source': 'Statics', 'phase': 'Phase3', 'subject': 'BTzz',
                                                              'field': 'model ids 7', 'own_row': True, 'kg': 84.8435}]}}
    s = probe.census_summary([bt09, statics_only])
    assert s['by_identity_class'] == {'exact': 1, 'exact_short': 1}
    assert s['trials_matching_own_body_mass'] == []
    assert [x['trial'] for x in s['trials_without_own_readme_match']] == ['Phase3/BTzz/synthetic_stairs']
    assert s['trials_without_any_own_match'] == []
    flagged = s['trials_with_other_candidates_in_tolerance']
    assert [x['trial'] for x in flagged] == ['Phase1And2/BT09/synthetic_walk']
    assert flagged[0]['own'] == ['README Phase1And2 BT09 model_day1_with_exo_kg']
    assert flagged[0]['other_candidates_not_binding'][0]['label'] == 'README Phase3 BT13 participant_day1_kg'


class SyntheticReader:
    """Stands in for the zip reader: serves synthetic tables, honours usecols, records what was asked."""

    def __init__(self, tables):
        self.tables, self.asked = tables, []

    def table(self, phase, member, usecols=None):
        import pandas as pd
        self.asked.append(member)
        if member not in self.tables:
            raise KeyError(member)
        df = pd.DataFrame(self.tables[member])
        return df[[c for c in df.columns if usecols(c)]] if usecols else df


def test_census_trial_restricts_columns_and_reports_absent_power(probe):
    n, D = 600, 79.09                                              # synthetic short stairs trial
    base = 'Parsed/BTyy/synthetic_stairs/BTyy_synthetic_stairs_'
    exo_joint = {'hip_flexion': 'hip', 'knee_angle': 'knee'}
    sign = {'hip_flexion': -1.0, 'knee_angle': 1.0}               # interaction sign per joint, as in GT24
    keys = [(c, s) for s in 'lr' for c in ('hip_flexion', 'knee_angle')]
    d = {k: synthetic_moment(n=n, seed=i) for i, k in enumerate(keys)}            # synthetic net - bio
    vel = {k: 300.0 * synthetic_moment(n=n, seed=10 + i) for i, k in enumerate(keys)}
    x = {k: sign[k[0]] * D * d[k] for k in keys}                                    # synthetic interaction, N*m
    exo = {f'{exo_joint[c]}_angle_{s}_torque_interaction': x[(c, s)] for c, s in keys}
    net = {f'{c}_{s}_moment': d[(c, s)] + 1.0 for c, s in keys}
    bio = {f'{c}_{s}_moment': np.ones(n) for c, s in keys}
    pex = {f'{c}_{s}_power': x[(c, s)] * np.deg2rad(vel[(c, s)]) / D for c, s in keys}
    extra = {'unrelated_column': np.zeros(n)}
    tables = {base + 'exo.csv': {**exo, **extra}, base + 'moment_filt.csv': {**net, **extra},
              base + 'moment_filt_bio.csv': bio, base + 'power_exo.csv': pex,
              base + 'velocity.csv': {f'{c}_{s}_velocity': vel[(c, s)] for c, s in keys}}
    meta = {'readme': {'phase_masses': {'Phase1And2': {'BTyy': {'model_day1_with_exo_kg': 79.09}}}}, 'phase3_static_models': {}}
    item = {'phase': 'Phase1And2', 'subject': 'BTyy', 'recording': 'synthetic_stairs', 'stage': 'census',
            'estimators': ['E1'], 'missing_kinds': []}
    out = probe.census_trial(SyntheticReader(tables), meta, item)
    assert out['identity_class'] == 'exact_short'
    assert out['identity_divisor_kg'] == pytest.approx(D, rel=1e-12)
    assert [h['field'] for h in out['identity_match_split']['own_readme_row']] == ['model_day1_with_exo_kg']
    # The same trial without its power file is not promoted (power identity required for short trials).
    item2 = dict(item, missing_kinds=['power_exo'])
    out2 = probe.census_trial(SyntheticReader(tables), meta, item2)
    assert out2['kinds_not_read'] == ['power_exo']
    assert out2['identity_class'] == 'not_exact'
    assert {v['short_rule_failed'] for v in out2['identity'].values()} == {'power_identity_not_exact'}
