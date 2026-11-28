"""SYNTHETIC tests for the UM21-C02 pelvis correspondence probe; no UM21 source is read.

Expected values are known by construction (linear ramps, hand-built HDF5 blocks)."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

h5py = pytest.importorskip('h5py')
_p = Path(__file__).resolve().parents[1] / 'contributor_tools/audit_probes/2026_11_02/probe_um21_pelvis_correspondence.py'
_s = importlib.util.spec_from_file_location('probe_c02', _p)
P = importlib.util.module_from_spec(_s)
_s.loader.exec_module(P)


def test_stride_key_explicit_side_and_rejections():
    assert P.stride_key([11, 21, 10, 1]) == ('left', 11, 21)
    assert P.stride_key([11, 21, 10, 2]) == ('right', 11, 21)
    for bad in ([0, 10, 10, 1], [1, 10, 8, 1], [1, 10, 9, 3], [1, float('nan'), 9, 1], [1, 2, 3]):
        with pytest.raises(ValueError):
            P.stride_key(bad)


def test_resample_linear_ramp_is_exact_on_inclusive_grid():
    out = P.resample(np.arange(11.0))          # 0..10 -> 150 points
    assert out[0] == 0 and out[-1] == 10
    assert out[75] == pytest.approx(75 * 10 / 149)


def test_nan_is_not_bridged():
    raw = np.array([0.0, np.nan, 2.0, 3.0])
    out = P.resample(raw)
    assert np.isnan(out[50])                    # x = 1.0 exactly: the missing sample itself
    assert out[0] == 0 and out[-1] == 3


def test_compare_reports_error_and_mask_separately():
    a = np.zeros((3, 150)); b = a.copy()
    b[1, 5] = 0.5
    b[2, 7] = np.nan
    c = P.compare(a, b)
    assert c[0]['max_abs_error_deg'] == 0 and c[1]['max_abs_error_deg'] == 0.5
    assert c[2]['mask_mismatch'] == 1 and c[2]['finite_pairs'] == 149
    assert P.matches(P.compare(a, a)) and not P.matches(c)


def build(tmp_path, swap_pelvis_sides=False):
    """Streaming: left/right pelvis and hip ramps (distinct per side/component); Normalized: 2 strides per side."""
    raw = tmp_path / 's.h5'; norm = tmp_path / 'n.h5'
    def ramp(offset):
        return np.array([[offset + 10 * c + 0.5 * i for i in range(40)] for c in range(3)])
    chans = {'RPelvisAngles': ramp(1), 'LPelvisAngles': ramp(-1), 'RHipAngles': ramp(100), 'LHipAngles': ramp(200)}
    with h5py.File(raw, 'w') as f:
        g = f.create_group('Streaming/AB99/Tread/i0')
        g.create_dataset('events/LHS', data=[[1], [11], [21]])
        g.create_dataset('events/RHS', data=[[2], [12], [22]])
        for k, v in chans.items():
            g.create_dataset('jointAngles/' + k, data=v)
    strides = [('left', 1, 11, 1), ('left', 11, 21, 1), ('right', 2, 12, 2), ('right', 12, 22, 2)]
    det = np.array([[a, b, b - a, leg] for _, a, b, leg in strides], float)
    pel, hip = [], []
    for side, a, b, _ in strides:
        own = 'L' if side == 'left' else 'R'
        po = ('R' if side == 'left' else 'L') if swap_pelvis_sides else own
        pel.append(P.resample(chans[po + 'PelvisAngles'][:, a - 1:b]))
        hip.append(P.resample(chans[own + 'HipAngles'][:, a - 1:b]))
    with h5py.File(norm, 'w') as f:
        g = f.create_group('Normalized/AB99/Walk/s1/i0')
        g.create_dataset('events/StrideDetails', data=det.T)
        g.create_dataset('jointAngles/PelvisAngles', data=np.array(pel))
        g.create_dataset('jointAngles/HipAngles', data=np.array(hip))
    return raw, norm


def run_record(tmp_path, **kw):
    raw, norm = build(tmp_path, **kw)
    with h5py.File(norm, 'r') as n, h5py.File(raw, 'r') as s:
        return P.probe_record('AB99', 'i0', n, s, {('left', 1, 11): {'label': 's1', 'observation_id': 'x'}, ('right', 12, 22): None})


def test_same_side_pelvis_matches_and_other_hypotheses_fail(tmp_path):
    r = run_record(tmp_path)
    assert r['summary'] == {'strides_bound': 4, 'left': 2, 'right': 2} and r['unbound'] == []
    for side in ('left', 'right'):
        s = r['sides'][side]
        assert s['H1_same_side']['matched_all_components'] == 2
        assert s['H2_opposite_side']['matched_all_components'] == 0
        assert s['H1neg_same_side_sign_flipped']['matched_all_components'] == 0
    assert r['hip_control_base1']['matched_all_components'] == 4
    assert r['hip_control_base0']['matched_all_components'] == 0     # frame base is tested, not assumed
    assert r['t03_written_with_normalized_twin'] == 1 and r['t03_written_total'] == 1


def test_swapped_sides_are_reported_not_repaired(tmp_path):
    r = run_record(tmp_path, swap_pelvis_sides=True)
    for side in ('left', 'right'):
        assert r['sides'][side]['H1_same_side']['matched_all_components'] == 0
        assert r['sides'][side]['H2_opposite_side']['matched_all_components'] == 2
    assert len(r['worst_H1_strides']) == 4


def test_unbound_when_not_consecutive_heel_strikes(tmp_path):
    raw, norm = build(tmp_path)
    with h5py.File(norm, 'r+') as f:
        d = f['Normalized/AB99/Walk/s1/i0/events/StrideDetails']
        v = d[...]; v[0, 0] = 2; v[2, 0] = 9    # left 2..11: 2 is a right heel strike, not a left one
        d[...] = v
    with h5py.File(norm, 'r') as n, h5py.File(raw, 'r') as s:
        r = P.probe_record('AB99', 'i0', n, s, {})
    assert r['summary']['strides_bound'] == 3 and len(r['unbound']) == 1
    assert 'consecutive' in r['unbound'][0]['reason']
