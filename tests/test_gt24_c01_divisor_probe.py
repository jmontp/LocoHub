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
