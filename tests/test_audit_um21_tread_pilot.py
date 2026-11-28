"""Tests for contributor_tools/audit_um21_tread_pilot.py on SYNTHETIC fixtures.

Every fixture here is synthetic: a tiny HDF5 file shaped like one UM21
Streaming/Tread record (700 frames, made-up linear signals) and a made-up pilot
and base output. No research data is read. Expected values are known in closed
form: every source channel is linear in the frame index, so linear resampling
reproduces it exactly, and the NaN positions below were derived by hand from
the window lengths, not computed with the audit's code.
"""
import ast
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

h5py = pytest.importorskip('h5py')
pa = pytest.importorskip('pyarrow')
pq = pytest.importorskip('pyarrow.parquet')

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'contributor_tools' / 'audit_um21_tread_pilot.py'
ENV = {**os.environ, 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'}

N = 700
LHS = [10, 130, 255, 370, 500]
RHS = [70, 190, 310, 430, 560, 650, 690]
CUTS = [(5, 300), (250, 690), (640, 700)]
LABELS = ['s1x2', 'd0x5', 's0x8']
GROUP_VARS = {
    'jointAngles': ['LAnkleAngles', 'LFootProgressAngles', 'LHipAngles', 'LKneeAngles', 'LPelvisAngles',
                    'RAnkleAngles', 'RFootProgressAngles', 'RHipAngles', 'RKneeAngles', 'RPelvisAngles'],
    'jointForces': ['LAnkleForce', 'LHipForce', 'LKneeForce', 'RAnkleForce', 'RHipForce', 'RKneeForce'],
    'jointMoments': ['LAnkleMoment', 'LHipMoment', 'LKneeMoment', 'RAnkleMoment', 'RHipMoment', 'RKneeMoment'],
    'jointPowers': ['LAnklePower', 'LHipPower', 'LKneePower', 'RAnklePower', 'RHipPower', 'RKneePower'],
}
KIND = {'jointAngles': ('joint_angle', 'deg'), 'jointForces': ('joint_force', 'N_kg'),
        'jointMoments': ('joint_moment', 'Nm_kg'), 'jointPowers': ('joint_power', 'W_kg')}
NAN_FRAME = 140  # LKneeAngles component 1 (1-based) is NaN at this 1-based frame.
# Hand-derived: window (130, 255) has 125 frame steps; frame 140 is index 10;
# k*125/149 lies in (9, 11) for k = 11, 12, 13. Window (70, 190): 120 steps,
# index 70; k*120/149 in (69, 71) for k = 86, 87, 88. Central differences then
# touch one more sample on each side.
NAN_K = {('left', 130, 255): [11, 12, 13], ('right', 70, 190): [86, 87, 88]}
EXPECTED_WRITTEN = 8
EXPECTED_EXCLUDED = 2


def belt_speed(frame):
    """Synthetic commanded belt speed (m/s) at a 1-based frame: a slow linear ramp."""
    return 0.5 + 0.001 * frame


def foot_ap_position(frame):
    """Heel/toe AP position (m) whose exact derivative is -belt_speed(frame) at 100 Hz:
    d/df of -(0.5 f + 0.0005 f^2)/100 is -(0.5 + 0.001 f)/100 m per frame. Central
    differences are exact for a quadratic, so the marker belt speed equals cvel at lag 0."""
    return -(0.5 * frame + 0.0005 * frame ** 2) / 100.0


def write_belt(trial, cvel_shift=0):
    """cvel sample j (0-based) holds the speed of joint frame j + 1 - cvel_shift."""
    if 'events/VelProf/cvel' in trial:
        del trial['events/VelProf/cvel']
    j = np.arange(N + 2)
    trial['events/VelProf/cvel'] = belt_speed(j + 1 - cvel_shift).reshape(-1, 1)


def coefficients(group, var, comp):
    gi = list(GROUP_VARS).index(group)
    vi = GROUP_VARS[group].index(var)
    a = vi + 0.1 * comp + 0.3 * gi
    b = 0.001 * (1 + vi + 0.5 * gi) * (1 if (comp + vi) % 2 == 0 else -1)
    return a, b


def source_value(group, var, comp, index0):
    a, b = coefficients(group, var, comp)
    return a + b * index0


def classify(start, end):
    hits = [i for i, (a, b) in enumerate(CUTS) if a <= start and end <= b]
    if len(hits) != 1:
        return None
    label = LABELS[hits[0]]
    if label.startswith('s'):
        return 'decline_walking', label, {'incline_deg': -10, 'speed_m_s': float(label[1:].replace('x', '.')),
                                          'surface': 'treadmill'}
    sign = 1 if label[0] == 'a' else -1
    return 'transition', label, {'incline_deg': -10, 'surface': 'treadmill',
                                 'transition_phase': 'acceleration' if sign > 0 else 'deceleration',
                                 'acceleration_m_s2': sign * float(label[1:].replace('x', '.'))}


def write_source(path, mutate=None):
    with h5py.File(path, 'w') as f:
        trial = f.create_group('Streaming/AB01/Tread/d10')
        ev = trial.create_group('events')
        ev['LHS'] = np.array(LHS, float).reshape(-1, 1)
        ev['RHS'] = np.array(RHS, float).reshape(-1, 1)
        ev['LStrideTime'] = np.diff(LHS).astype(float).reshape(-1, 1)
        ev['RStrideTime'] = np.diff(RHS).astype(float).reshape(-1, 1)
        ev['cutPoints'] = np.array(CUTS, float).T
        refs = []
        for i, label in enumerate(LABELS):
            ds = f.create_dataset(f'#refs#/t{i}', data=np.array([ord(c) for c in label], np.uint16).reshape(-1, 1))
            refs.append(ds.ref)
        ev.create_dataset('tasks', data=np.array(refs, dtype=h5py.ref_dtype).reshape(-1, 1))
        write_belt(trial)
        frames = np.arange(1, N + 1, dtype=float)
        for side in 'LR':
            for name, offset in (('HEE', 0.0), ('TOE', 0.2)):
                trial[f'markers/{side}{name}'] = np.stack([foot_ap_position(frames) + offset,
                                                           np.full(N, 0.1), np.full(N, 0.05), np.ones(N)])
        index0 = np.arange(N, dtype=float)
        for group, names in GROUP_VARS.items():
            for var in names:
                data = np.stack([source_value(group, var, c, index0) for c in range(3)])
                if (group, var) == ('jointAngles', 'LKneeAngles'):
                    data[0, NAN_FRAME - 1] = np.nan
                trial[f'{group}/{var}'] = data
        for name in ('LForce', 'RForce'):
            trial[f'forceplates/{name}'] = np.zeros((3, 10 * N))
        if mutate:
            mutate(f, trial)


def windows():
    out = []
    for side, hs in (('left', LHS), ('right', RHS)):
        for a, b in zip(hs[:-1], hs[1:]):
            out.append((side, a, b, classify(a, b)))
    return out


def observation(side, start, end, task):
    k = np.arange(150)
    x = (start - 1) + k * (end - start) / 149.0      # 0-based fractional source index
    deg = math.pi / 180
    rec = 'um21:Streaming/AB01/Tread/d10'
    oid = f'{rec}:{side}:frames:{start}:{end}'
    nan_k = NAN_K.get((side, start, end), [])
    task_name, label, info = task
    prior = {'subject': ['UM21_AB01'] * 150, 'source_recording_id': [rec] * 150, 'observation_id': [oid] * 150,
             'reference_side': [side] * 150, 'observation_type': ['individual_cycle'] * 150,
             'task': [task_name] * 150, 'task_id': [label] * 150,
             'task_info': [json.dumps(info, sort_keys=True)] * 150,
             'source_start_time_s': np.full(150, (start - 1) / 100), 'source_end_time_s': np.full(150, (end - 1) / 100),
             'phase_ipsi': k * 100.0 / 149, 'time_s': k * (end - start) / (149 * 100.0), 'step': [oid] * 150}
    ang = lambda var: source_value('jointAngles', var, 0, x) * deg  # noqa: E731
    pelvis = ang('RPelvisAngles')
    prior['pelvis_sagittal_angle_rad'] = pelvis
    for role, leg in (('ipsi', 'R' if side == 'right' else 'L'), ('contra', 'L' if side == 'right' else 'R')):
        hip, knee = ang(leg + 'HipAngles'), ang(leg + 'KneeAngles')
        hip_rate = coefficients('jointAngles', leg + 'HipAngles', 0)[1] * 100 * deg
        knee_rate = np.full(150, coefficients('jointAngles', leg + 'KneeAngles', 0)[1] * 100 * deg)
        if leg == 'L' and nan_k:
            knee[nan_k] = np.nan
            knee_rate[list(range(nan_k[0] - 1, nan_k[-1] + 2))] = np.nan
        prior.update({f'hip_flexion_angle_{role}_rad': hip, f'knee_flexion_angle_{role}_rad': knee,
                      f'thigh_sagittal_angle_{role}_rad': pelvis + hip,
                      f'shank_sagittal_angle_{role}_rad': pelvis + hip - knee,
                      f'source_ankle_sagittal_angle_{role}_rad': ang(leg + 'AnkleAngles'),
                      f'ankle_dorsiflexion_angle_{role}_rad': np.full(150, np.nan),
                      f'hip_flexion_velocity_{role}_rad_s': np.full(150, hip_rate),
                      f'knee_flexion_velocity_{role}_rad_s': knee_rate})
    comps = {}
    for group, names in GROUP_VARS.items():
        kind, unit = KIND[group]
        for var in names:
            for c in range(3):
                values = source_value(group, var, c, x)
                if (group, var, c) == ('jointAngles', 'LKneeAngles', 0) and nan_k:
                    values[nan_k] = np.nan
                comps[f'source_{kind}_{var.lower()}_component_{c}_{unit}'] = values
    return oid, prior, comps


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(tmp, mutate_source=None, mutate_obs=None, mutate_ledger=None, mutate_mapping=None):
    """Write synthetic source, base and pilot; mutate_obs(oid, prior, comps, which) edits a copy."""
    src = tmp / 'Streaming.mat'
    write_source(src, mutate_source)
    base_root, pilot_root = tmp / 'base', tmp / 'pilot'
    base_dir, pilot_dir = base_root / 'AB01' / 'd10', pilot_root / 'AB01' / 'd10'
    base_dir.mkdir(parents=True)
    pilot_dir.mkdir(parents=True)
    ledger, base_tables, pilot_tables, mapping = [], [], [], {}
    for side, a, b, task in reversed(windows()):  # file order deliberately not source order
        if task is None:
            ledger.append({'side': side, 'start': a, 'end': b, 'excluded': 'outside or ambiguous task interval'})
            continue
        oid, prior, comps = observation(side, a, b, task)
        ledger.append({'side': side, 'start': a, 'end': b, 'task': task[0], 'label': task[1], 'info': task[2],
                       'observation_id': oid, 'status': 'written_unreviewed'})
        base_prior = {k: (v.copy() if isinstance(v, np.ndarray) else list(v)) for k, v in prior.items()}
        if mutate_obs:
            mutate_obs(oid, base_prior, None, 'base')
            mutate_obs(oid, prior, comps, 'pilot')
        base_tables.append(pa.table(base_prior))
        pilot_tables.append(pa.table({**prior, **comps}))
    for group, names in GROUP_VARS.items():
        kind, unit = KIND[group]
        for var in names:
            for c in range(3):
                mapping[f'source_{kind}_{var.lower()}_component_{c}_{unit}'] = {
                    'group': group, 'variable': var, 'matlab_component_1based': c + 1, 'unit': unit,
                    'canonical_frame_verified': False}
    if mutate_mapping:
        mutate_mapping(mapping)
    for path, tables in ((base_dir / 'phase.parquet', base_tables), (pilot_dir / 'phase.parquet', pilot_tables)):
        writer = pq.ParquetWriter(path, tables[0].schema)
        for t in tables:
            writer.write_table(t)
        writer.close()
    lines = [json.dumps(x) for x in ledger]
    (base_dir / 'candidate_ledger.jsonl').write_text('\n'.join(lines) + '\n')
    if mutate_ledger:
        lines = mutate_ledger(lines)
    (pilot_dir / 'candidate_ledger.jsonl').write_text('\n'.join(lines) + '\n')
    (pilot_dir / 'source_columns.json').write_text(json.dumps(mapping, indent=2) + '\n')
    code = pilot_root / 'code' / 'contributor_tools' / 'fake_producer.py'
    code.parent.mkdir(parents=True)
    code.write_text('# synthetic producer snapshot\n')
    source_sha = sha(src)
    (base_root / 'conversion_summary.json').write_text(json.dumps({
        'source': {'sha256': source_sha},
        'recordings': [{'subject': 'AB01', 'condition': 'd10', 'sha256': sha(base_dir / 'phase.parquet')}]}))
    (pilot_root / 'conversion_summary.json').write_text(json.dumps({
        'source_sha256': source_sha, 'base_summary_sha256': sha(base_root / 'conversion_summary.json'),
        'code_sha256': {'/elsewhere/contributor_tools/fake_producer.py': sha(code)},
        'records': [{'subject': 'AB01', 'condition': 'd10', 'observations_checked': EXPECTED_WRITTEN,
                     'source_columns': len(mapping), 'output_sha256': sha(pilot_dir / 'phase.parquet'),
                     'base_output_sha256': sha(base_dir / 'phase.parquet'),
                     'ledger_sha256': sha(pilot_dir / 'candidate_ledger.jsonl'),
                     'source_columns_sha256': sha(pilot_dir / 'source_columns.json')}]}))
    return src, base_root, pilot_root


def run(tmp, src, base_root, pilot_root, *extra, hash_mode=('--skip-source-hash',), out_name='audit_out'):
    out = tmp / out_name
    cmd = [sys.executable, str(SCRIPT), '--source', str(src), '--pilot-root', str(pilot_root),
           '--base-root', str(base_root), '--subject', 'AB01', '--condition', 'd10', '--output-dir', str(out),
           *hash_mode, *extra]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=ENV, timeout=300)
    report_path = out / 'audit_report.json'
    report = json.loads(report_path.read_text()) if report_path.exists() else None
    return proc, report


def failed(report):
    return sorted(k for k, v in report['checks'].items() if not v['passed'])


# ------------------------------------------------------------------ clean fixture
def test_synthetic_clean_fixture_passes_with_known_counts(tmp_path):
    src, base, pilot = build(tmp_path)
    proc, report = run(tmp_path, src, base, pilot)
    assert proc.returncode == 0, (proc.stdout, proc.stderr, report and failed(report))
    assert report['status'] == 'pass' and failed(report) == []
    counts = report['counts']
    assert counts['observations'] == EXPECTED_WRITTEN
    assert counts['excluded_pairs'] == EXPECTED_EXCLUDED
    assert counts['source_pairs'] == len(LHS) - 1 + len(RHS) - 1
    assert counts['by_side'] == {'left': 4, 'right': 4}
    assert counts['exclusion_reasons'] == {'outside or ambiguous task interval': 2}
    assert counts['source_component_columns'] == 84
    assert report['flags'] == []
    assert report['binding_complete'] is False
    soft, hard = report['resources']['rlimit_as_bytes']
    assert 0 < soft <= 768 * 1024**2 and 0 < hard <= 768 * 1024**2
    assert report['checks']['no_producer_module_loaded']['passed']
    belt = report['belt_clock_alignment']
    assert belt['passed'] and belt['best_lag'] == 0 and belt['err_lag0_m_s'] < 1e-9
    assert belt['ap_axis_index'] == 0 and belt['comparisons_lag0'] == 11  # 12 HS; RHS 690 runs past the markers
    assert report['inputs']['pilot_phase']['sha256'] == sha(pilot / 'AB01/d10/phase.parquet')
    assert report['audit_script']['sha256'] == sha(SCRIPT)


def test_source_hash_binding_and_mismatch(tmp_path):
    src, base, pilot = build(tmp_path)
    proc, report = run(tmp_path, src, base, pilot, hash_mode=('--expected-source-sha256', sha(src)))
    assert proc.returncode == 0 and report['binding_complete'] is True
    assert report['inputs']['source']['sha256'] == sha(src)
    proc, report = run(tmp_path, src, base, pilot, hash_mode=('--expected-source-sha256', '0' * 64), out_name='o2')
    assert proc.returncode == 1 and 'source_sha256_matches_expected' in failed(report)


# ------------------------------------------------------------------ mutations that must fail
def test_value_where_hand_derived_mask_is_nan_fails(tmp_path):
    col = 'source_joint_angle_lkneeangles_component_0_deg'

    def mutate(oid, prior, comps, which):
        if which == 'pilot' and oid.endswith('left:frames:130:255'):
            comps[col][12] = 0.0
    proc, report = run(tmp_path, *build(tmp_path, mutate_obs=mutate))
    assert proc.returncode == 1 and failed(report) == ['source_component_values_and_mask']


def test_component_one_frame_shift_fails(tmp_path):
    def mutate(oid, prior, comps, which):
        if which == 'pilot':
            for c in range(3):  # value at the next frame: add one frame step of the linear signal
                name = f'source_joint_moment_lhipmoment_component_{c}_Nm_kg'
                comps[name] = comps[name] + coefficients('jointMoments', 'LHipMoment', c)[1]
    proc, report = run(tmp_path, *build(tmp_path, mutate_obs=mutate))
    assert proc.returncode == 1 and failed(report) == ['source_component_values_and_mask']


def test_concatenation_order_side_swap_fails_even_when_base_agrees(tmp_path):
    def mutate(oid, prior, comps, which):
        if oid.endswith('right:frames:310:430'):
            for stem in ('hip_flexion_angle', 'knee_flexion_angle', 'thigh_sagittal_angle', 'shank_sagittal_angle',
                         'source_ankle_sagittal_angle', 'hip_flexion_velocity', 'knee_flexion_velocity'):
                unit = '_rad_s' if 'velocity' in stem else '_rad'
                i, c = f'{stem}_ipsi{unit}', f'{stem}_contra{unit}'
                prior[i], prior[c] = prior[c], prior[i]
    proc, report = run(tmp_path, *build(tmp_path, mutate_obs=mutate))
    assert proc.returncode == 1
    assert failed(report) == ['prior_angle_values_and_mask', 'prior_velocity_values_and_mask']


def test_wrong_reference_side_label_fails(tmp_path):
    def mutate(oid, prior, comps, which):
        if oid.endswith('right:frames:310:430'):
            prior['reference_side'] = ['left'] * 150
    proc, report = run(tmp_path, *build(tmp_path, mutate_obs=mutate))
    assert proc.returncode == 1 and failed(report) == ['identity_reference_side']


def test_rule_c_knee_sign_already_applied_fails(tmp_path):
    def mutate(oid, prior, comps, which):
        for role in ('ipsi', 'contra'):
            prior[f'knee_flexion_angle_{role}_rad'] = -prior[f'knee_flexion_angle_{role}_rad']
    proc, report = run(tmp_path, *build(tmp_path, mutate_obs=mutate))
    assert proc.returncode == 1 and failed(report) == ['prior_angle_values_and_mask']


def test_time_at_wrong_clock_and_exclusive_phase_fail(tmp_path):
    def mutate(oid, prior, comps, which):
        prior['time_s'] = prior['time_s'] * 10            # as if frames were 10 Hz
        prior['phase_ipsi'] = np.arange(150) * 100.0 / 150  # 0..99.33, end-exclusive
    proc, report = run(tmp_path, *build(tmp_path, mutate_obs=mutate))
    assert proc.returncode == 1
    assert {'clock_time_s_elapsed_frames_at_100hz', 'phase_inclusive_0_to_100'} <= set(failed(report))


def test_prior_column_one_ulp_change_against_base_fails(tmp_path):
    def mutate(oid, prior, comps, which):
        if which == 'pilot' and oid.endswith('left:frames:10:130'):
            prior['pelvis_sagittal_angle_rad'] = np.nextafter(prior['pelvis_sagittal_angle_rad'], np.inf)
    proc, report = run(tmp_path, *build(tmp_path, mutate_obs=mutate))
    assert proc.returncode == 1
    assert 'prior_column_bitwise_equal_to_base' in failed(report)
    assert 'prior_angle_values_and_mask' not in failed(report)  # 1 ulp is inside the source tolerance


@pytest.mark.parametrize('edit, expected', [
    (lambda lines: [l for l in lines if '"excluded"' not in l] + [l for l in lines if '"excluded"' in l][1:],
     'ledger_accounts_for_every_source_pair'),
    (lambda lines: [l.replace('outside or ambiguous task interval', 'manual') for l in lines],
     'exclusion_reason_matches_independent_rule'),
    (lambda lines: [l.replace('outside or ambiguous task interval', ' ') for l in lines],
     'exclusion_has_explicit_reason'),
])
def test_ledger_exclusion_accounting_fails(tmp_path, edit, expected):
    proc, report = run(tmp_path, *build(tmp_path, mutate_ledger=edit))
    assert proc.returncode == 1 and expected in failed(report)


def test_source_stride_time_not_in_frames_fails(tmp_path):
    def mutate(f, trial):
        del trial['events/LStrideTime']
        trial['events/LStrideTime'] = (np.diff(LHS) / 100.0).reshape(-1, 1)  # seconds, not frames
    proc, report = run(tmp_path, *build(tmp_path, mutate_source=mutate))
    assert proc.returncode == 1 and failed(report) == ['clock_stride_time_equals_hs_difference_frames']


def test_missing_component_in_mapping_fails(tmp_path):
    proc, report = run(tmp_path, *build(tmp_path, mutate_mapping=lambda m: m.pop(next(iter(m)))))
    assert proc.returncode == 1
    assert {'component_mapping_covers_every_source_component', 'component_count_as_expected'} <= set(failed(report))


# ------------------------------------------------------------------ flags, guards, CLI
def test_ankle_alternate_branch_is_flagged_not_failed(tmp_path):
    def mutate(f, trial):
        data = trial['jointAngles/RAnkleAngles'][...]
        data[1, :] = 100.0  # constant, so resampled values stay exact
        del trial['jointAngles/RAnkleAngles']
        trial['jointAngles/RAnkleAngles'] = data

    def mutate_obs(oid, prior, comps, which):
        if comps is not None:
            comps['source_joint_angle_rankleangles_component_1_deg'] = np.full(150, 100.0)
    proc, report = run(tmp_path, *build(tmp_path, mutate_source=mutate, mutate_obs=mutate_obs))
    assert proc.returncode == 0, failed(report)
    flags = {f['flag']: f['detail'] for f in report['flags']}
    assert flags['ankle_alternate_branch_frames_in_exported_windows']['RAnkleAngles']['observations'] == 8


def test_rss_guard_stops_with_exit_4(tmp_path):
    proc, report = run(tmp_path, *build(tmp_path), '--max-rss-mib', '1')
    assert proc.returncode == 4 and report['status'] == 'stopped_rss_guard'


def test_existing_output_dir_and_missing_hash_choice_are_refused(tmp_path):
    src, base, pilot = build(tmp_path)
    (tmp_path / 'audit_out').mkdir()
    proc, report = run(tmp_path, src, base, pilot)
    assert proc.returncode == 2 and report is None
    proc, _ = run(tmp_path, src, base, pilot, hash_mode=(), out_name='o3')
    assert proc.returncode == 2
    proc, _ = run(tmp_path, src, base, pilot, '--address-space-mib', '1024', out_name='o4')
    assert proc.returncode == 2


def test_script_imports_no_producer_code():
    tree = ast.parse(SCRIPT.read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split('.')[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or '').split('.')[0])
    allowed = {'os', 'argparse', 'hashlib', 'json', 'math', 're', 'pathlib', 'resource', 'sys', 'time',
               'numpy', 'h5py', 'pyarrow'}
    assert imported <= allowed, imported - allowed
    text = SCRIPT.read_text()
    assert 'source_components(' not in text and 'np.interp' not in text and 'interp1d' not in text


# ------------------------------------------------------------------ task-interval clock (review R1)
def test_cvel_clock_shifted_150_frames_fails_alignment(tmp_path):
    """cvel (and so the cutPoints clock) runs 150 frames behind the markers: the
    synthetic belt reaches each speed 150 cvel samples later than the feet show it."""
    proc, report = run(tmp_path, *build(tmp_path, mutate_source=lambda f, trial: write_belt(trial, cvel_shift=150)))
    assert proc.returncode == 1 and failed(report) == ['clock_cut_points_aligned_with_joint_frames']
    belt = report['belt_clock_alignment']
    assert belt['best_lag'] == 150 and belt['err_best_m_s'] < 1e-9
    assert abs(belt['err_lag0_m_s'] - 0.150) < 1e-9  # ramp slope 0.001 m/s per frame x 150 frames


def test_cvel_shift_of_40_frames_fails_on_the_error_criterion(tmp_path):
    """40 frames is inside +-50, but on this ramp (0.001 m/s per frame) the lag-0 error
    exceeds the best by 0.040 m/s, above the stated 0.02 m/s."""
    proc, report = run(tmp_path, *build(tmp_path, mutate_source=lambda f, trial: write_belt(trial, cvel_shift=40)))
    belt = report['belt_clock_alignment']
    assert belt['best_lag'] == 40 and abs(belt['err_lag0_m_s'] - 0.040) < 1e-9
    assert proc.returncode == 1 and failed(report) == ['clock_cut_points_aligned_with_joint_frames']


def test_cvel_shift_of_10_frames_passes(tmp_path):
    """10 frames: inside +-50 and 0.010 m/s excess error, inside 0.02 m/s."""
    proc, report = run(tmp_path, *build(tmp_path, mutate_source=lambda f, trial: write_belt(trial, cvel_shift=10)))
    belt = report['belt_clock_alignment']
    assert belt['best_lag'] == 10 and abs(belt['err_lag0_m_s'] - 0.010) < 1e-9
    assert proc.returncode == 0, failed(report)


def test_missing_markers_make_alignment_fail_not_pass(tmp_path):
    def mutate(f, trial):
        del trial['markers/LTOE']
    proc, report = run(tmp_path, *build(tmp_path, mutate_source=mutate))
    assert proc.returncode == 1 and failed(report) == ['clock_cut_points_aligned_with_joint_frames']
    assert report['belt_clock_alignment']['reason'].startswith('not evaluable')


def test_non_finite_report_value_exits_2_without_writing_a_file(tmp_path):
    def mutate(f, trial):
        cuts = np.array(CUTS, float).T
        cuts[0, 0] = np.nan  # reaches clock.cut_points_max
        del trial['events/cutPoints']
        trial['events/cutPoints'] = cuts
    src, base, pilot = build(tmp_path, mutate_source=mutate)
    proc, report = run(tmp_path, src, base, pilot)
    assert proc.returncode == 2 and report is None
    assert not (tmp_path / 'audit_out' / 'audit_report.json').exists()
