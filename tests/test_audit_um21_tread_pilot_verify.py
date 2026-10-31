"""Reviewer mutation tests for contributor_tools/audit_um21_tread_pilot.py (UM21-T02 verify).

SYNTHETIC fixtures only. The fixture writer (a tiny 700-frame HDF5 shaped like one
UM21 Streaming/Tread record, with signals linear in the frame index) is reused from
the worker's tests/test_audit_um21_tread_pilot.py; every mutation and every expected
outcome below is the reviewer's own. Expected values are known in closed form
(linear signals), never computed with the audit's code. No research data is read.
"""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip('h5py')
pytest.importorskip('pyarrow')

_SPEC = importlib.util.spec_from_file_location(
    'um21_t02_worker_fixture', Path(__file__).resolve().parent / 'test_audit_um21_tread_pilot.py')
w = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(w)

PRIOR_SIDE_STEMS = ('hip_flexion_angle', 'knee_flexion_angle', 'thigh_sagittal_angle', 'shank_sagittal_angle',
                    'source_ankle_sagittal_angle', 'hip_flexion_velocity', 'knee_flexion_velocity')
DEG = np.pi / 180


def run_failed(tmp_path, out_name='audit_out', extra=(), **build_kwargs):
    src, base, pilot = w.build(tmp_path, **build_kwargs)
    proc, report = w.run(tmp_path, src, base, pilot, *extra, out_name=out_name)
    assert report is not None, (proc.stdout, proc.stderr)
    return proc, report, w.failed(report)


def swap_ipsi_contra(prior):
    for stem in PRIOR_SIDE_STEMS:
        unit = '_rad_s' if 'velocity' in stem else '_rad'
        i, c = f'{stem}_ipsi{unit}', f'{stem}_contra{unit}'
        prior[i], prior[c] = prior[c], prior[i]


# ---------------------------------------------------------------- side by identity
def test_symmetric_legs_make_side_check_non_discriminating_and_fail(tmp_path, monkeypatch):
    """Left and right source channels identical: value checks cannot see a side swap,
    so the audit must refuse to call the side check passed."""
    original = w.coefficients

    def symmetric(group, var, comp):
        return original(group, 'L' + var[1:] if var.startswith('R') else var, comp)
    monkeypatch.setattr(w, 'coefficients', symmetric)

    def mutate(oid, prior, comps, which):  # swap on both base and pilot: invisible to value checks
        if oid.endswith('right:frames:310:430'):
            swap_ipsi_contra(prior)
    proc, report, failed = run_failed(tmp_path, mutate_obs=mutate)
    assert proc.returncode == 1
    assert 'side_discriminating_data_present' in failed
    assert report['counts']['side_discriminating_observations'] < report['counts']['observations']


def test_ledger_side_label_swapped_for_one_pair_fails(tmp_path):
    def edit(lines):
        out = []
        for line in lines:
            entry = json.loads(line)
            if 'excluded' in entry and entry['side'] == 'right':
                entry['side'] = 'left'  # an RHS pair claimed as left
            out.append(json.dumps(entry))
        return out
    proc, report, failed = run_failed(tmp_path, mutate_ledger=edit)
    assert proc.returncode == 1 and 'ledger_accounts_for_every_source_pair' in failed


# ---------------------------------------------------------------- phase and window endpoints
def test_phase_endpoint_off_by_one_sample_fails(tmp_path):
    def mutate(oid, prior, comps, which):
        prior['phase_ipsi'] = (np.arange(150) + 1) * 100.0 / 150  # 0.67 .. 100: starts one step late
    proc, report, failed = run_failed(tmp_path, mutate_obs=mutate)
    assert proc.returncode == 1 and 'phase_inclusive_0_to_100' in failed


def test_end_exclusive_window_fails_components(tmp_path):
    """Pilot resampled frames start..end-1 (exclusive end) instead of start..end."""
    def mutate(oid, prior, comps, which):
        if which != 'pilot':
            return
        start, end = (int(x) for x in oid.rsplit(':', 2)[-2:])
        k = np.arange(150)
        x_wrong = (start - 1) + k * (end - 1 - start) / 149.0
        name = 'source_joint_force_rhipforce_component_2_N_kg'
        comps[name] = w.source_value('jointForces', 'RHipForce', 2, x_wrong)
    proc, report, failed = run_failed(tmp_path, mutate_obs=mutate)
    assert proc.returncode == 1 and failed == ['source_component_values_and_mask']


def test_whole_stride_shifted_one_frame_in_base_and_pilot_fails(tmp_path):
    """Every value column sampled from frames start+1..end+1; base agrees, so only the
    source comparison can catch it."""
    def mutate(oid, prior, comps, which):
        start, end = (int(x) for x in oid.rsplit(':', 2)[-2:])
        side = oid.split(':')[-4]
        task = next(t for s, a, b, t in w.windows() if (s, a, b) == (side, start, end))
        _, shifted_prior, shifted_comps = w.observation(side, start + 1, end + 1, task)
        for key in prior:
            if key.endswith(('_rad', '_rad_s')):
                prior[key] = shifted_prior[key]
        if comps is not None:
            comps.update(shifted_comps)
    proc, report, failed = run_failed(tmp_path, mutate_obs=mutate)
    assert proc.returncode == 1
    assert {'source_component_values_and_mask', 'prior_angle_values_and_mask'} <= set(failed)
    assert 'prior_column_bitwise_equal_to_base' not in failed


def test_rows_reversed_within_one_observation_fails(tmp_path):
    def mutate(oid, prior, comps, which):
        if oid.endswith('left:frames:10:130'):
            for key, value in list(prior.items()):
                prior[key] = value[::-1].copy() if isinstance(value, np.ndarray) else list(value)[::-1]
            if comps is not None:
                for key in comps:
                    comps[key] = comps[key][::-1].copy()
    proc, report, failed = run_failed(tmp_path, mutate_obs=mutate)
    assert proc.returncode == 1
    assert {'phase_inclusive_0_to_100', 'clock_time_s_elapsed_frames_at_100hz'} <= set(failed)


# ---------------------------------------------------------------- clock units
def test_source_start_time_at_wrong_clock_fails(tmp_path):
    def mutate(oid, prior, comps, which):
        prior['source_start_time_s'] = prior['source_start_time_s'] * 10  # 10 Hz frames
        prior['source_end_time_s'] = prior['source_end_time_s'] * 10
    proc, report, failed = run_failed(tmp_path, mutate_obs=mutate)
    assert proc.returncode == 1 and failed == ['clock_source_start_end_time_s']


def test_time_at_1000hz_fails_and_velocity_follows(tmp_path):
    def mutate(oid, prior, comps, which):
        prior['time_s'] = prior['time_s'] / 10  # as if frames were 1000 Hz
    proc, report, failed = run_failed(tmp_path, mutate_obs=mutate)
    assert proc.returncode == 1
    assert {'clock_time_s_elapsed_frames_at_100hz', 'clock_source_start_end_time_s'} <= set(failed)


def test_forceplate_not_ten_times_joint_frames_fails(tmp_path):
    def mutate(f, trial):
        del trial['forceplates/LForce']
        trial['forceplates/LForce'] = np.zeros((3, w.N))  # 100 Hz forceplate
    proc, report, failed = run_failed(tmp_path, mutate_source=mutate)
    assert proc.returncode == 1 and failed == ['clock_forceplate_frames_equal_10x_joint_frames']


def test_cut_points_past_joint_frames_are_flagged(tmp_path):
    def mutate(f, trial):
        cuts = np.array(w.CUTS, float).T
        cuts[1, -1] = w.N + 5
        del trial['events/cutPoints']
        trial['events/cutPoints'] = cuts
    proc, report, failed = run_failed(tmp_path, mutate_source=mutate)
    assert 'cut_points_exceed_joint_frames' in {f['flag'] for f in report['flags']}


# ---------------------------------------------------------------- NaN masks
def test_source_nan_dropped_in_prior_columns_of_base_and_pilot_fails(tmp_path):
    """Base and pilot both bridge the source gap (knee interpolated across the NaN frame)."""
    def mutate(oid, prior, comps, which):
        if oid.endswith('left:frames:130:255'):
            start, end = 130, 255
            x = (start - 1) + np.arange(150) * (end - start) / 149.0
            knee = w.source_value('jointAngles', 'LKneeAngles', 0, x) * DEG  # bridged: no NaN
            prior['knee_flexion_angle_ipsi_rad'] = knee
    proc, report, failed = run_failed(tmp_path, mutate_obs=mutate)
    assert proc.returncode == 1 and 'prior_angle_values_and_mask' in failed
    assert 'prior_column_bitwise_equal_to_base' not in failed


def test_extra_nan_in_pilot_component_fails(tmp_path):
    def mutate(oid, prior, comps, which):
        if which == 'pilot' and oid.endswith('right:frames:310:430'):
            comps['source_joint_power_rkneepower_component_0_W_kg'][75] = np.nan
    proc, report, failed = run_failed(tmp_path, mutate_obs=mutate)
    assert proc.returncode == 1 and failed == ['source_component_values_and_mask']


# ---------------------------------------------------------------- observation order and identity
def test_observations_reordered_in_pilot_only_fails(tmp_path):
    src, base, pilot = w.build(tmp_path)
    import pyarrow.parquet as pq
    import pyarrow as pa
    path = pilot / 'AB01' / 'd10' / 'phase.parquet'
    table = pq.read_table(path)
    swapped = pa.concat_tables([table.slice(150, 150), table.slice(0, 150), table.slice(300)])
    pq.write_table(swapped, path)
    summary_path = pilot / 'conversion_summary.json'
    summary = json.loads(summary_path.read_text())
    summary['records'][0]['output_sha256'] = w.sha(path)  # receipt consistent; only the order differs
    summary_path.write_text(json.dumps(summary))
    proc, report = w.run(tmp_path, src, base, pilot)
    failed = w.failed(report)
    assert proc.returncode == 1 and failed == ['prior_column_bitwise_equal_to_base']


def test_observations_reordered_in_base_and_pilot_still_pass_by_identity(tmp_path):
    """Order is not identity: the same permutation in both files must still pass."""
    src, base, pilot = w.build(tmp_path)
    import pyarrow.parquet as pq
    import pyarrow as pa
    for root, key, summary_key in ((pilot, 'records', 'output_sha256'), (base, 'recordings', 'sha256')):
        path = root / 'AB01' / 'd10' / 'phase.parquet'
        table = pq.read_table(path)
        pq.write_table(pa.concat_tables([table.slice(150, 150), table.slice(0, 150), table.slice(300)]), path)
    summary_b = json.loads((base / 'conversion_summary.json').read_text())
    summary_b['recordings'][0]['sha256'] = w.sha(base / 'AB01/d10/phase.parquet')
    (base / 'conversion_summary.json').write_text(json.dumps(summary_b))
    summary_p = json.loads((pilot / 'conversion_summary.json').read_text())
    summary_p['records'][0]['output_sha256'] = w.sha(pilot / 'AB01/d10/phase.parquet')
    summary_p['records'][0]['base_output_sha256'] = w.sha(base / 'AB01/d10/phase.parquet')
    summary_p['base_summary_sha256'] = w.sha(base / 'conversion_summary.json')
    (pilot / 'conversion_summary.json').write_text(json.dumps(summary_p))
    proc, report = w.run(tmp_path, src, base, pilot)
    assert proc.returncode == 0, w.failed(report)


def test_written_pair_relabelled_to_other_task_fails(tmp_path):
    def edit(lines):
        out = []
        for line in lines:
            entry = json.loads(line)
            if entry.get('label') == 's1x2':
                entry['label'] = 'd0x5'
            out.append(json.dumps(entry))
        return out
    proc, report, failed = run_failed(tmp_path, mutate_ledger=edit)
    assert proc.returncode == 1 and 'written_entry_matches_independent_rule' in failed


# ---------------------------------------------------------------- signs (rule C must not be pre-applied)
def test_pelvis_sign_flipped_in_base_and_pilot_fails(tmp_path):
    def mutate(oid, prior, comps, which):
        prior['pelvis_sagittal_angle_rad'] = -prior['pelvis_sagittal_angle_rad']
    proc, report, failed = run_failed(tmp_path, mutate_obs=mutate)
    assert proc.returncode == 1 and failed == ['prior_angle_values_and_mask']


def test_knee_moment_component_sign_flipped_fails(tmp_path):
    def mutate(oid, prior, comps, which):
        if comps is not None:
            name = 'source_joint_moment_lkneemoment_component_0_Nm_kg'
            comps[name] = -comps[name]
    proc, report, failed = run_failed(tmp_path, mutate_obs=mutate)
    assert proc.returncode == 1 and failed == ['source_component_values_and_mask']


# ---------------------------------------------------------------- receipts and CLI
def test_pilot_phase_hash_in_summary_stale_fails(tmp_path):
    src, base, pilot = w.build(tmp_path)
    summary_path = pilot / 'conversion_summary.json'
    summary = json.loads(summary_path.read_text())
    summary['records'][0]['output_sha256'] = '0' * 64
    summary_path.write_text(json.dumps(summary))
    proc, report = w.run(tmp_path, src, base, pilot)
    assert proc.returncode == 1 and w.failed(report) == ['receipt_pilot_phase_sha256']


def test_code_snapshot_tampered_fails(tmp_path):
    src, base, pilot = w.build(tmp_path)
    (pilot / 'code' / 'contributor_tools' / 'fake_producer.py').write_text('# edited after the run\n')
    proc, report = w.run(tmp_path, src, base, pilot)
    assert proc.returncode == 1 and w.failed(report) == ['receipt_code_snapshot_matches_summary']


def test_uppercase_expected_hash_and_missing_parent_are_usage_errors(tmp_path):
    src, base, pilot = w.build(tmp_path)
    proc, report = w.run(tmp_path, src, base, pilot, hash_mode=('--expected-source-sha256', 'A' * 64))
    assert proc.returncode == 2 and report is None
    proc, report = w.run(tmp_path, src, base, pilot, out_name='missing_parent/out')
    assert proc.returncode == 2 and report is None
