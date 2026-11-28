"""Synthetic tests for GT21-RB05 export rules (made-up arrays with known answers; not source data)."""
import numpy as np
import pytest

from contributor_tools import gt21_rb_export as ex
from contributor_tools import run_gt21_rb_export as rn


def test_locate_on_grid_and_between():
    t = np.arange(11) * 0.005
    y = np.arange(11, dtype=float) ** 2
    loc = ex.locate(t, np.array([0.0, 0.0125, 0.05, 0.03]))
    v = ex.sample_at(y, loc)
    assert v[0] == 0.0 and v[2] == 100.0 and v[3] == 36.0
    assert v[1] == pytest.approx(0.5 * (4.0 + 9.0))             # halfway between samples 2 and 3


def test_locate_exact_sample_ignores_missing_neighbour_but_between_is_missing():
    t = np.arange(5) * 0.005
    y = np.array([1.0, np.nan, 3.0, 4.0, 5.0])
    v = ex.sample_at(y, ex.locate(t, np.array([0.0, 0.005, 0.0025, 0.01])))
    assert v[0] == 1.0 and np.isnan(v[1]) and np.isnan(v[2]) and v[3] == 3.0


def test_locate_outside_clock_raises():
    with pytest.raises(ValueError):
        ex.locate(np.arange(5) * 0.005, np.array([0.03]))


def test_mask_at_neighbour_rule():
    t = np.arange(5) * 0.005
    m = np.array([0, 1, 0, 0, 0], bool)
    out = ex.mask_at(m, ex.locate(t, np.array([0.0, 0.005, 0.0075, 0.0125, 0.02])))
    assert out.tolist() == [False, True, True, False, False]


def test_zsign_at():
    t = np.arange(4) * 0.005
    z = np.array([np.nan, 1.0, 1.0, np.nan])
    out = ex.zsign_at(z, ex.locate(t, np.array([0.0, 0.0025, 0.0075, 0.015])))
    assert np.isnan(out[0]) and out[1] == 1.0 and out[2] == 1.0 and np.isnan(out[3])


def test_power_is_product_and_missing_never_zero():
    p = ex.power_from(np.array([2.0, np.nan, 3.0, 0.5]), np.array([-1.5, 4.0, np.nan, 2.0]))
    assert p[0] == -3.0 and np.isnan(p[1]) and np.isnan(p[2]) and p[3] == 1.0
    assert ex.power_inputs('knee_flexion_power_ipsi_W_kg') == ('knee_flexion_moment_ipsi_Nm_kg', 'knee_flexion_velocity_ipsi_rad_s')


def test_columns_and_kinds():
    names = ex.role_columns(('ipsi', 'contra'))
    assert names[0] == ex.PELVIS and len(names) == 1 + 2 * len(ex.LEG_SPECS) == len(set(names))
    assert ex.kind_of('grf_lateral_contra_BW') == 'force' and ex.kind_of('ankle_dorsiflexion_power_left_W_kg') == 'power'
    assert ex.kind_of('cop_vertical_ipsi_m') == 'cop' and ex.kind_of(ex.PELVIS) == 'pelvis'


def test_own_at_interval_uses_contact_sample_times():
    t = np.arange(20) * 0.005
    contacts = [{'plate': 'A', 'a': 4, 'b': 10, 'owner': 'right'}, {'plate': 'B', 'a': 12, 'b': 15, 'owner': 'left'}]
    tq = np.array([0.015, 0.02, 0.045, 0.0451, 0.06])
    own = ex.own_at(t, contacts, {'A': 0, 'B': 1}, 'right', tq, 2)
    assert own[:, 0].tolist() == [False, True, True, False, False] and not own[:, 1].any()


def step(**kw):
    s = {'step_id': 'AB00/x/y/left/0001', 'recording': 'levelground_ccw_fast_01_01', 'mode': 'levelground', 'label': 'walk',
         'authors_class': 'walk', 'incline_deg': None, 'stair_height_m': None, 'direction': None}
    s.update(kw)
    return s


def test_classify_labels_and_terrain():
    assert ex.classify(step(label='turnccw'))[:2] == ('transition', 'turn_left')
    assert ex.classify(step())[:2] == ('level_walking', 'level')
    task, tid, info = ex.classify(step(mode='ramp', label='rampdescent', incline_deg=-7.8, direction='descent'))
    assert (task, tid, info['incline_deg']) == ('decline_walking', 'decline_7.8deg', -7.8)
    task, tid, info = ex.classify(step(mode='stair', label='walk-stairascent', stair_height_m=0.102, direction='ascent'))
    assert (task, tid, info['step_height_m']) == ('transition', 'walk_to_stair_ascent', 0.102)
    _, _, info = ex.classify(step(mode='treadmill', label='treadmill', speed_values_m_s=[0.8]))
    assert info['speed_m_s'] == 0.8
    _, _, info = ex.classify(step(mode='treadmill', label='treadmill', speed_values_m_s=[0.5, 0.8]))
    assert 'speed_m_s' not in info and info['speed_values_m_s'] == [0.5, 0.8]


@pytest.mark.parametrize('bad', [dict(mode='ramp', label='rampascent', incline_deg=None, direction='ascent'),
                                 dict(mode='ramp', label='rampascent', incline_deg=5.0, direction='descent'),
                                 dict(mode='ramp', label='rampdescent', incline_deg=5.0, direction='descent'),
                                 dict(mode='stair', label='stairascent', stair_height_m=0.0, direction='ascent'),
                                 dict(mode='levelground', label='stand'), dict(mode='treadmill', label='treadmill')])
def test_classify_refuses_defaults(bad):
    with pytest.raises(ex.LabelError):
        ex.classify(step(**bad))


def test_incomplete_flag_threshold_is_half_of_stance():
    assert ex.stance_flags({'stance_samples': 84, 'force_missing_stance_samples': 42})[0] == ex.FLAG_INCOMPLETE
    assert ex.stance_flags({'stance_samples': 84, 'force_missing_stance_samples': 41})[0] is None
    assert ex.stance_flags({'stance_samples': 0, 'force_missing_stance_samples': 0}) == (None, None)


def test_held_reason_texts():
    assert ex.held_reason('x', 'angle', 'left', True, True, True, False, True) is None
    assert 'bad-fit' in ex.held_reason('x', 'angle', 'left', False, True, True, False, True)
    assert 'not a measured zero' in ex.held_reason('x', 'force', 'left', False, True, False, True, True)
    assert 'no force plate' in ex.held_reason('x', 'force', 'left', False, False, False, False, False)
    assert 'bad-fit' in ex.held_reason('x', 'power', 'left', False, True, True, False, True)


def test_limits_per_subject():
    assert len(ex.step_limits('AB28')) == 1 and 'pelvis' in ex.step_limits('AB28')[0]
    assert 'R_Thigh_Upper' in ex.step_limits('AB27')[0] and ex.step_limits('AB06') == []


def test_phase_force_comes_from_the_1khz_plate_not_the_200hz_table():
    """A one-sample 700 N spike at t = 0.012 s (1 kHz) between the 200 Hz samples 0.010 and 0.015: the phase force at 0.012 s
    is 1.0 BW from the plate; the 200 Hz route would give 0.4 BW."""
    from contributor_tools import gt21_rb_pass as rb
    ft = np.arange(0, 41) * 0.001
    vy = np.zeros(41)
    vy[12] = 700.0
    zero = np.zeros(41)
    t = np.arange(9) * 0.005
    state = {'channels': ['P'], 'idx': {'P': 0}, 'ft': ft, 'raw': [{'vx': zero, 'vy': vy, 'vz': zero}], 'treadmill': False,
             'contacts': [{'plate': 'P', 'a': 0, 'b': 9, 'owner': 'right'}], 'own200': {}, 'zsign': {'right': np.ones(9)}}
    table = {'time_s': t}
    mask = {'force_missing_right': np.zeros(9, bool)}
    tq = np.array([0.012, 0.02])
    out, m = rn.phase_forces(state, table, mask, {'body_weight_N': 700.0}, 'right', tq, ex.locate(t, tq))
    assert out['vertical'][0] == pytest.approx(1.0) and out['vertical'][1] == 0.0 and not m.any()
    assert rb.interp_to_clock(t, ft, vy)[2] == pytest.approx(0.0 + 0.0)   # the 200 Hz table never sees the spike at all
    mask['force_missing_right'][2] = True                                    # sample 0.010 masked: 0.012 falls between 2 and 3
    out, m = rn.phase_forces(state, table, mask, {'body_weight_N': 700.0}, 'right', tq, ex.locate(t, tq))
    assert np.isnan(out['vertical'][0]) and np.isnan(out['anterior'][0]) and out['vertical'][1] == 0.0
