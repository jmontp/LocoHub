"""GT23-E02 tests. All fixtures are SYNTHETIC (tiny made-up angle series with known values); they do not regenerate any
scientific dataset. They check the unwrap rule, the step-up hold and the runner against independently known values."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from contributor_tools import gt23_fixes as fx
from contributor_tools import run_gt23_e02 as rn2
from contributor_tools import run_gt23_e01 as rn1
from tests import test_gt23_e01 as t1

D = np.radians


def wrapped(x):
    return fx.wrap(x)


def make_leg(n=400, foot_true_deg=None, shank_deg=-135.0):
    """Published (wrapped) segment and joint columns for one leg of a made-up recording."""
    pelvis = np.zeros(n)
    thigh = D(15.0) + 0.0 * pelvis
    shank = D(shank_deg) + 0.0 * pelvis
    foot_true = D(foot_true_deg)
    foot = wrapped(foot_true)                       # what C06 writes: wrapped to (-180, 180]
    return {'pelvis_sagittal_angle_rad': pelvis, 'thigh_sagittal_angle_left_rad': thigh, 'shank_sagittal_angle_left_rad': shank,
            'foot_sagittal_angle_left_rad': foot, 'hip_flexion_angle_left_rad': thigh - pelvis,
            'knee_flexion_angle_left_rad': thigh - shank, 'ankle_dorsiflexion_angle_left_rad': foot - shank}


def test_wrap_case_known_values():
    # the foot goes from -170 to -190 degrees (true, continuous) while the shank sits at -135: the ankle is -35 .. -55
    n = 400
    foot_true = np.linspace(-170.0, -190.0, n)
    cols = make_leg(n, foot_true)
    assert np.degrees(cols['ankle_dorsiflexion_angle_left_rad']).max() > 300       # published: the wrap jump is there
    new, report = fx.fix_angles(cols)
    ankle = np.degrees(new['ankle_dorsiflexion_angle_left_rad'])
    expected = foot_true + 135.0                                                  # independent: true foot minus shank
    assert np.allclose(ankle, expected, atol=1e-9)
    foot = np.degrees(new['foot_sagittal_angle_left_rad'])
    assert np.allclose(foot, foot_true, atol=1e-9)
    # only the samples past -180 changed, each by exactly -360 degrees; nothing else changed
    changed = report['foot_sagittal_angle_left_rad']['indices']
    assert np.array_equal(changed, np.flatnonzero(foot_true < -180.0))
    assert np.allclose(report['foot_sagittal_angle_left_rad']['new'] - report['foot_sagittal_angle_left_rad']['old'], -2 * np.pi)
    assert set(report) == {'foot_sagittal_angle_left_rad', 'ankle_dorsiflexion_angle_left_rad'}
    assert 'hip_flexion_angle_left_rad' not in new and 'knee_flexion_angle_left_rad' not in new


def test_no_wrap_nothing_changes_and_bits_kept():
    cols = make_leg(300, np.linspace(-20.0, 40.0, 300), shank_deg=-10.0)
    new, report = fx.fix_angles(cols)
    assert new == {} and report == {}


def test_nan_gap_is_not_bridged_and_stays_missing():
    n = 300
    foot_true = np.linspace(-170.0, -200.0, n)
    cols = make_leg(n, foot_true)
    cols['foot_sagittal_angle_left_rad'][100:120] = np.nan
    cols['ankle_dorsiflexion_angle_left_rad'][100:120] = np.nan
    new, _ = fx.fix_angles(cols)
    a = new['ankle_dorsiflexion_angle_left_rad']
    assert np.isnan(a[100:120]).all() and np.isfinite(a[:100]).all() and np.isfinite(a[120:]).all()
    assert np.allclose(np.degrees(a[120:]), foot_true[120:] + 135.0)


def test_a_real_jump_is_not_a_wrap():
    n = 200
    foot_true = np.concatenate([np.full(100, 10.0), np.full(100, 70.0)])           # a 60 degree step: no wrap involved
    cols = make_leg(n, foot_true, shank_deg=-10.0)
    new, report = fx.fix_angles(cols)
    assert report == {}
    wrap_idx, remains = fx.classify_jumps(cols['foot_sagittal_angle_left_rad'], cols['foot_sagittal_angle_left_rad'])
    assert len(wrap_idx) == 0 and list(remains) == [100]


def test_classify_wrap_jump_is_removed_by_unwrap():
    foot_true = np.concatenate([np.linspace(-170.0, -179.0, 50), np.linspace(-181.0, -190.0, 50)])
    cols = make_leg(100, foot_true)
    new, _ = fx.fix_angles(cols)
    old = cols['ankle_dorsiflexion_angle_left_rad']
    wrap_idx, remains = fx.classify_jumps(old, new['ankle_dorsiflexion_angle_left_rad'])
    assert list(wrap_idx) == [50] and len(remains) == 0


def test_change_that_is_not_a_whole_turn_is_refused():
    with pytest.raises(ValueError):
        fx.check_whole_turns(np.array([0.0, 1.0]), np.array([0.0, 1.0 + 3.0]))
    assert list(fx.check_whole_turns(np.array([0.0, 1.0]), np.array([0.0, 1.0 + 2 * np.pi]))) == [1]


def test_speed_is_rederived_and_kept_when_equal():
    n = 400
    foot_true = np.linspace(-170.0, -190.0, n)
    cols = make_leg(n, foot_true)
    cols['ankle_dorsiflexion_velocity_left_rad_s'] = fx.central_derivative(cols['ankle_dorsiflexion_angle_left_rad'])
    new, report = fx.fix_angles(cols)
    assert 'ankle_dorsiflexion_velocity_left_rad_s' not in report       # the published speed already wrapped the difference


def test_step_up_hold_rule_and_columns():
    assert fx.step_up_hold('step_ups') and not fx.step_up_hold('curb_up') and not fx.step_up_hold('normal_walk')
    cols = {f'cop_{k}_{s}_m': np.ones(5) for s in fx.SIDES for k in fx.COP_KEYS}
    cols['cop_lab_y_left_m'] = np.full(5, 0.009)
    cols['grf_lab_y_left_N'] = np.full(5, 500.0)
    new, held = fx.hold_step_up_cop(cols, {})
    assert set(new) == {f'cop_{k}_{s}_m' for s in fx.SIDES for k in fx.COP_KEYS}
    assert all(np.isnan(v).all() for v in new.values())
    assert set(held) == set(new) and all(r == fx.STEP_UP_REASON for r in held.values())
    assert np.all(cols['cop_anterior_left_m'] == 1.0)                     # inputs untouched; force and plate point never touched


def test_heel_evidence_is_evidence_only():
    heel = np.array([0.55, 0.56, 0.05, 0.06])
    plate = np.full(4, 0.009)
    force = np.array([400.0, 400.0, 400.0, 5.0])
    ev = fx.heel_gap_evidence(heel, plate, force)
    assert ev['loaded_samples'] == 3 and abs(ev['median_m'] - (0.55 - 0.009)) < 1e-12
    assert abs(ev['share_above_reference_line'] - 2 / 3) < 1e-12


# ------------------------------------------------------------------ the runner on a synthetic participant
def smooth_angles(n, wrap_in_left_foot):
    t = np.arange(n) / 200.0
    pelvis = D(5.0) * np.sin(2 * np.pi * 0.5 * t)
    out = {'pelvis_sagittal_angle_rad': pelvis}
    for side in ('left', 'right'):
        thigh = D(20.0) * np.sin(2 * np.pi * t)
        shank = D(-135.0 if (wrap_in_left_foot and side == 'left') else -10.0) + D(10.0) * np.sin(2 * np.pi * t + 0.3)
        if wrap_in_left_foot and side == 'left':
            foot_true = np.linspace(-170.0, -190.0, n)          # crosses -180: C06 writes the wrapped value
            foot = fx.wrap(D(foot_true))
        else:
            foot = D(10.0) * np.sin(2 * np.pi * t + 0.6)
        out[f'thigh_sagittal_angle_{side}_rad'] = thigh
        out[f'shank_sagittal_angle_{side}_rad'] = shank
        out[f'foot_sagittal_angle_{side}_rad'] = foot
        joints = {'hip': thigh - pelvis, 'knee': thigh - shank, 'ankle': foot - shank}
        for j, word in fx.JOINTS:
            out[f'{word}_angle_{side}_rad'] = joints[j]
            out[f'{word}_velocity_{side}_rad_s'] = fx.central_derivative(joints[j])
    return out


@pytest.fixture(scope='module')
def e02_inputs(tmp_path_factory):
    base = tmp_path_factory.mktemp('gt23e02') / 'inputs'
    roots = t1.build_inputs(base)
    c06_root = Path(roots['c06'])
    ledger = [json.loads(line) for line in (c06_root / 'ledger.jsonl').read_text().splitlines()]
    for entry in ledger:
        rec = entry['recording']
        path = c06_root / f'{rec}.parquet'
        table = pq.read_table(str(path)).to_pandas()
        new_cols = smooth_angles(len(table), wrap_in_left_foot=(rec == 'jump_1'))
        for k, v in new_cols.items():
            table[k] = v
        t1.write_parquet(path, {c: table[c].to_numpy() for c in table.columns})
        entry['output']['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    (c06_root / 'ledger.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in ledger))
    return base


@pytest.fixture(scope='module')
def e02_out(e02_inputs, tmp_path_factory, monkeypatch_module):
    out = e02_inputs.parent / 'out_e02'
    monkeypatch_module.setattr(fx, 'STEP_UP_TASK', 'poses')        # the rule's task name; poses_1 plays the step-up recording here
    monkeypatch_module.setattr(rn2, 'heel_evidence', lambda subject, rec, cols: {'left': {'loaded_samples': 1}, 'right': {'loaded_samples': 1}})
    args = argparse.Namespace(subject=t1.SUBJECT, output_root=str(out), records=None, base=str(e02_inputs))
    assert rn2.run(args) == 0
    return out


@pytest.fixture(scope='module')
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


def jl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def test_runner_exports_only_changed_and_held_recordings(e02_out):
    s = json.loads((e02_out / 'e02_summary.json').read_text())
    assert sorted(s['recordings_exported']) == ['jump_1', 'poses_1']
    assert s['recordings_unchanged_not_exported'] == ['normal_walk_1']
    assert s['superseded_e01_recordings'] == s['recordings_exported']
    recs = {r['recording'] for r in jl(e02_out / 'recordings.jsonl')}
    assert recs == {'jump_1', 'poses_1'}


def test_runner_change_log_is_whole_turns_and_known_values(e02_out):
    ch = jl(e02_out / 'changes.jsonl')
    assert ch and {c['column'].split('_left_')[0].split('_ipsi_')[0].split('_contra_')[0] for c in ch} <= {
        'foot_sagittal_angle', 'ankle_dorsiflexion_angle'} | {'foot_sagittal_angle_ipsi'}
    assert all(abs(c['new_rad'] - c['old_rad'] - 2 * np.pi * c['whole_turns']) < 1e-9 for c in ch if c['kind'] == 'whole_turns')
    assert all(c['whole_turns'] == -1 for c in ch if c['kind'] == 'whole_turns')
    time_foot = [c for c in ch if c['table'] == 'time' and c['column'] == 'foot_sagittal_angle_left_rad']
    n = 1200
    expected = np.flatnonzero(np.linspace(-170.0, -190.0, n) < -180.0)
    assert [c['sample_index'] for c in time_foot] == expected.tolist()
    assert {c['source_recording_id'] for c in ch} == {f'{t1.SUBJECT}/jump_1'}


def test_runner_time_table_has_the_continuous_ankle(e02_out):
    df = pq.read_table(str(e02_out / 'time.parquet'), columns=['source_recording_id', 'ankle_dorsiflexion_angle_left_rad']).to_pandas()
    a = np.degrees(df[df['source_recording_id'] == f'{t1.SUBJECT}/jump_1']['ankle_dorsiflexion_angle_left_rad'].to_numpy())
    shank = np.degrees(smooth_angles(1200, True)['shank_sagittal_angle_left_rad'])
    assert np.allclose(a, np.linspace(-170.0, -190.0, 1200) - shank, atol=1e-9)          # true foot minus shank, no 360 jump


def test_runner_hold_marks_cop_missing_with_reason_and_keeps_force(e02_out):
    df = pq.read_table(str(e02_out / 'time.parquet')).to_pandas()
    held = df[df['source_recording_id'] == f'{t1.SUBJECT}/poses_1']
    for s in ('left', 'right'):
        for k in fx.COP_KEYS:
            assert held[f'cop_{k}_{s}_m'].isna().all()
    assert held['cop_lab_y_left_m'].notna().all() and held['grf_vertical_left_N'].notna().all()
    reasons = json.loads(held['held_signals'].iloc[0])
    assert reasons['cop_anterior_left_m'] == fx.STEP_UP_REASON
    assert fx.STEP_UP_NOTE in held['task_info'].iloc[0]
    other = df[df['source_recording_id'] == f'{t1.SUBJECT}/jump_1']
    assert other['cop_anterior_left_m'].notna().all()


def test_runner_refuses_non_empty_root(e02_inputs, e02_out):
    args = argparse.Namespace(subject=t1.SUBJECT, output_root=str(e02_out), records=None, base=str(e02_inputs))
    with pytest.raises(rn2.FixError):
        rn2.run(args)


def test_phase_sample_straddling_a_wrap_pair_is_logged_with_its_changed_source_sample(monkeypatch):
    """Independent value: source samples 10 (+179 deg, wrapped) and 11 (-179.. true +181 deg). The old phase value interpolated
    between +179 and -179; the corrected one between +179 and +181."""
    col = 'foot_sagittal_angle_left_rad'
    old_src = np.zeros(30)
    old_src[10], old_src[11] = D(179.0), D(-179.0)
    new_src = old_src.copy()
    new_src[11] = D(181.0)
    a, b = 0, 29
    from contributor_tools import gt23_export as ex
    old = ex.phase_samples(old_src, a, b)
    new = ex.phase_samples(new_src, a, b)
    monkeypatch.setattr(rn2.STATE, 'changes', [], raising=False)
    monkeypatch.setattr(rn2.STATE, 'changed_idx', {col: {11}}, raising=False)
    w = rn2.LoggingWriters.__new__(rn2.LoggingWriters)
    w._log_phase({'observation_id': 'x', 'reference_side': 'left', 'source_recording_id': 's'}, col, col, old, new, a, b)
    kinds = {c['kind'] for c in rn2.STATE.changes}
    assert kinds == {'interpolated_across_a_wrap'} or kinds == {'interpolated_across_a_wrap', 'whole_turns'}
    assert all(c['source_index_lo'] == 10 or c['source_index_hi'] == 11 or c['source_index_lo'] == 11 for c in rn2.STATE.changes)
    # a change with no changed source neighbour is refused
    monkeypatch.setattr(rn2.STATE, 'changed_idx', {col: {25}}, raising=False)
    with pytest.raises(rn2.FixError):
        w._log_phase({'observation_id': 'x', 'reference_side': 'left', 'source_recording_id': 's'}, col, col, old, new, a, b)


# ------------------------------------------------------------------ the readback
from contributor_tools import audit_gt23_e02 as au2  # noqa: E402


@pytest.fixture(scope='module')
def e01_out(e02_inputs):
    out = e02_inputs.parent / 'out_e01'
    args = argparse.Namespace(subject=t1.SUBJECT, output_root=str(out), records=None, base=str(e02_inputs))
    assert rn1.run(args) == 0
    return out


def audit(e01_out, e02_out, name):
    args = argparse.Namespace(subject=t1.SUBJECT, e02_root=str(e02_out), e01_root=str(e01_out), output_root=str(e02_out.parent / name))
    rc = au2.run(args)
    return rc, json.loads((e02_out.parent / name / 'audit_report.json').read_text())


def test_readback_passes_on_the_correct_export(e01_out, e02_out):
    rc, rep = audit(e01_out, e02_out, 'audit_ok')
    assert rc == 0 and rep['status'] == 'pass', rep['problems']
    assert rep['checks']['changed_cells_equal_log'] and rep['checks']['observation_sets_equal']
    assert rep['changed_cells'] == len(jl(e02_out / 'changes.jsonl'))
    assert rep['held_cop_cells'] > 0


def test_readback_fails_when_a_logged_change_is_missing(e01_out, e02_out, tmp_path):
    import shutil
    copy = tmp_path / 'e02copy'
    shutil.copytree(e02_out, copy)
    lines = (copy / 'changes.jsonl').read_text().splitlines()
    (copy / 'changes.jsonl').write_text('\n'.join(lines[1:]) + '\n')
    args = argparse.Namespace(subject=t1.SUBJECT, e02_root=str(copy), e01_root=str(e01_out), output_root=str(tmp_path / 'aud'))
    assert au2.run(args) == 1


def test_readback_fails_when_a_cell_changes_that_should_not(e01_out, e02_out, tmp_path):
    import shutil
    copy = tmp_path / 'e02copy2'
    shutil.copytree(e02_out, copy)
    t = pq.read_table(str(copy / 'time.parquet'))
    col = t.column('hip_flexion_angle_left_rad').to_numpy().copy()
    col[5] += 0.1
    t = t.set_column(t.schema.get_field_index('hip_flexion_angle_left_rad'), 'hip_flexion_angle_left_rad', pa.array(col))
    pq.write_table(t, str(copy / 'time.parquet'), row_group_size=500)
    args = argparse.Namespace(subject=t1.SUBJECT, e02_root=str(copy), e01_root=str(e01_out), output_root=str(tmp_path / 'aud2'))
    assert au2.run(args) == 1
