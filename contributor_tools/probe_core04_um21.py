"""CORE-04 UM21 pilot, PROBE step (read-only data access).

Read-only probe (AGENTS.md exception): one recording at a time from Streaming.mat, nothing
written under converted_datasets/ or source folders, peak RSS recorded and capped below
300 MiB, nice 19 / ionice idle, single-threaded. Samples: the UM21-C03 seeds (20261030 and
20261031, 4 recordings each), plus AB01/i0 (level walking) and AB07/i10 (right-ankle branch
episode). For each leg a small adapter passes the untransformed source channels (component
1; power: the first filled slot), stride durations, the participant's ParticipantDetails
Bodymass, and sagittal markers, GRF and CoP in the target frame to
`sign_offset_detector.detect_leg`. Writes docs/quality/audits/core04-um21-pilot-probe-v2.json.

Split from review_core04_um21_pilot.py on 2026-10-31 so that sheet edits never change the
hash recorded in a probe file. The sheet step is contributor_tools/review_core04_um21_pilot.py.
Ground truth (rule B, target = sign x source): pelvis -1, hip +1, knee angle +1, ankle +1,
hip moment +1, knee moment +1, ankle moment +1; power slot 1 (layout 1) -1, slot 3 +1.
Applies nothing to any dataset.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
import collections
import hashlib
import json
from pathlib import Path
import random
import resource
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.common import sign_offset_detector as sod  # noqa: E402

SOURCE = ROOT / 'contributor_tools/conversion_scripts/Umich_2021/Streaming.mat'
C03 = ROOT / 'docs/quality/audits/um21-c03-conventions.json'
AUDITS = ROOT / 'docs/quality/audits'
PROBE_V1 = AUDITS / 'core04-um21-pilot-probe.json'  # rule-C detector run (history; not rewritten)
PROBE = AUDITS / 'core04-um21-pilot-probe-v2.json'  # rule-B detector with phase-3 tests
SEED_A, SEED_B = 20261030, 20261031
EXTRA = [('AB01', 'i0', 'level walking'), ('AB07', 'i10', 'right-ankle branch episode (UM21-C03)')]
N_RANDOM = 4
N_SAMPLES = 150
RATE_HZ = 100.0  # UM21 joint-angle frame rate (UM21-C03)
RSS_CAP_MIB = 280.0  # stop before the 300 MiB exception limit
NOMINAL_SLOPE_DEG = {'d10': 10.0, 'd5': 5.0, 'i0': 0.0, 'i5': 5.0, 'i10': 10.0}  # README p.2 (as UM21-C03)
TASK = {'i0': 'level_walking', 'i5': 'incline_walking', 'i10': 'incline_walking',
        'd5': 'decline_walking', 'd10': 'decline_walking'}
UP = np.array([0.0, 0.0, 1.0])  # marker frame is gravity-aligned, z up (UM21-C03 plate geometry)
TRUTH = {'pelvis_tilt': -1, 'hip_angle': 1, 'knee_angle': 1, 'ankle_angle': 1,
         'hip_moment': 1, 'knee_moment': 1, 'ankle_moment': 1}  # rule B
TRUTH_POWER = {1: -1, 3: 1}  # by source slot: layout 1 stores -(M w) in slot 1; layout 2 +(M w) in slot 3
COP_REGISTRATION = ('midpoint rule (UM21-C03): over stance, mean CoP forward = mean heel-toe marker '
                    'midpoint forward; median CoP height = median lowest foot marker height; one constant '
                    'shift per leg and recording; independent of the moment channels')
CHANNELS = ['pelvis_tilt', 'hip_angle', 'knee_angle', 'ankle_angle', 'hip_moment', 'knee_moment',
            'ankle_moment', 'hip_power', 'knee_power', 'ankle_power']


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def peak_rss_mib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def mem_available():
    line = next(s for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:'))
    return int(line.split()[1]) * 1024


def rot_x(deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def strides(hs, length):  # UM21-C03 rule: 1-based heel strikes, 50-250 frames
    hs = np.asarray(hs).ravel().astype(int)
    return [(int(a), int(b)) for a, b in zip(hs[:-1], hs[1:]) if a >= 1 and b <= length and 50 <= b - a <= 250]


def resample(x, pairs):
    """(n,) or (n, k) frame series -> (units, 150) or (units, 150, k) on each stride a..b (1-based, inclusive)."""
    x = np.asarray(x, float)
    out = []
    for a, b in pairs:
        seg = x[a - 1:b]
        src = np.arange(seg.shape[0])
        grid = np.linspace(0, seg.shape[0] - 1, N_SAMPLES)
        if seg.ndim == 1:
            out.append(np.interp(grid, src, seg))
        else:
            out.append(np.stack([np.interp(grid, src, seg[:, k]) for k in range(seg.shape[1])], -1))
    return np.array(out)


def summarize(rep, truth, power_slots):
    chans = {}
    for k, c in rep['channels'].items():
        t = truth.get(k)
        if k.endswith('_power'):
            t = TRUTH_POWER.get(power_slots.get(k.split('_')[0]))
        if c['verdict'] in ('apply', 'suggest'):
            outcome = f"{'applied' if c['verdict'] == 'apply' else 'suggested'}_{'correct' if c['sign'] == t else 'wrong'}"
        else:
            outcome = c['verdict']
        ev = [{'test': e['test'], 'strength': e['strength'], 'sign': e['sign'],
               'agree': f"{e['units_agreeing']}/{e['units_voting']}", 'reason': e['reason'],
               'stats': {s: v for s, v in (e.get('stats') or {}).items()
                         if s in ('median_abs_slope', 'median_abs_r', 'scale_review', 'median_slope',
                                  'vertical_only', 'median_late_stance_mean', 'half_turn_offset',
                                  'half_cycle', 'half_cycle_ambiguous', 'median_unit_statistic',
                                  'leg_assignment')}}
              for e in c['evidence']]
        off = c['offset']
        chans[k] = {'verdict': c['verdict'], 'sign': c['sign'], 'truth': t, 'outcome': outcome,
                    'confidence': c['confidence'], 'families': c.get('families'), 'reason': c['reason'],
                    'evidence': ev,
                    'offset': {x: off.get(x) for x in ('estimate', 'ci95', 'flag_for_review', 'applied')},
                    'branch_screen': c.get('branch_screen') and {
                        x: c['branch_screen'][x] for x in ('branch_180_frames', 'far_from_median_frames',
                                                           'wrap_360_frames', 'units_touched', 'runs_total',
                                                           'runs_unit_start_stop')}}
    return chans


def participant_mass(handle, subject):
    """Bodymass (kg) from Streaming/<subject>/ParticipantDetails (3 x 11 cell array of
    name, value, unit), as the UM21 converters read it. None if absent or not positive."""
    group = handle[f'Streaming/{subject}']
    if 'ParticipantDetails' not in group:
        return None
    cells = group['ParticipantDetails'][()]

    def val(ref):
        a = handle[ref][()]
        if handle[ref].attrs.get('MATLAB_class', b'') == b'char':
            return ''.join(chr(c) for c in np.asarray(a).ravel())
        return np.asarray(a, float).ravel()
    for r in range(cells.shape[1]):
        name, value, unit = (val(cells[c, r]) for c in range(3))
        if name == 'Bodymass' and unit == 'kg' and np.size(value) == 1 and value[0] > 0:
            return float(value[0])
    return None


def probe_recording(handle, subject, condition):
    trial = handle[f'Streaming/{subject}/Tread/{condition}']
    n = trial['jointAngles']['RPelvisAngles'].shape[1]

    def comp(group, name):
        x = trial[group][name][...].astype(float)
        x[:, (x == 0).all(0)] = np.nan  # exact (0,0,0) triples are zero fill (UM21-C03)
        return x

    def marker(name):
        m = trial['markers'][name][...]
        xyz = m[:3].T.astype(float).copy()
        xyz[m[3] != 1] = np.nan
        return xyz

    # Forward axis from the heel->toe direction of both feet (detector helper); UM21-C03 used PSIS->ASIS.
    heels = np.vstack([marker('RHEE'), marker('LHEE')])
    toes = np.vstack([marker('RTOE'), marker('LTOE')])
    fwd = sod.forward_axis(heels, toes, UP)
    asi = (marker('LASI') + marker('RASI')) / 2
    psi = (marker('LPSI') + marker('RPSI')) / 2
    pel = np.nanmean(asi - psi, 0)
    pel_h = pel - (pel @ UP) * UP
    axis_agreement_deg = float(np.degrees(np.arccos(np.clip(pel_h @ fwd / np.linalg.norm(pel_h), -1, 1))))
    sag = lambda p: sod.project_sagittal(p, fwd, UP)

    # Plates: 10 samples per frame, block mean to 100 Hz; plates tilt with the belt (UM21-C03 geometry).
    plates = {}
    for s in 'RL':
        f = trial['forceplates'][s + 'Force'][...]
        cop = trial['forceplates'][s + 'CoP'][...]
        if f.shape[1] != 10 * n:
            raise ValueError(f'{subject}/{condition}: plate samples {f.shape[1]} != 10 x {n}')
        plates[s] = (np.nanmean(f.reshape(3, n, 10), 2), np.nanmean(cop.reshape(3, n, 10), 2) / 1000.0)
    # Belt-rise sign from the right heel path in mid stance (marker frame), magnitude from the README.
    fz_r = -plates['R'][0][2]
    thr = 0.2 * np.nanpercentile(fz_r, 99)
    on = np.flatnonzero(np.diff((fz_r > thr).astype(int)) == 1) + 1
    hee_r = marker('RHEE')
    slopes = []
    for a in on[:40]:
        b = a + 1
        while b < n and fz_r[b] > thr:
            b += 1
        s0, s1 = a + int(.3 * (b - a)), a + int(.6 * (b - a))
        ok = np.isfinite(hee_r[s0:s1, 1]) & np.isfinite(hee_r[s0:s1, 2])
        if ok.sum() > 5:
            slopes.append(np.degrees(np.arctan(np.polyfit(hee_r[s0:s1, 1][ok], hee_r[s0:s1, 2][ok], 1)[0])))
    belt = float(np.median(slopes))
    alpha = float(np.sign(belt) * NOMINAL_SLOPE_DEG[condition]) if NOMINAL_SLOPE_DEG[condition] else 0.0
    rx = rot_x(alpha)

    angles = {s: {k: comp('jointAngles', f'{s}{c}Angles') for k, c in
                  (('pelvis_tilt', 'Pelvis'), ('hip_angle', 'Hip'), ('knee_angle', 'Knee'), ('ankle_angle', 'Ankle'))}
              for s in 'RL'}
    mass = participant_mass(handle, subject)
    out = {'recording': f'{subject}/{condition}', 'frames': n, 'task': TASK[condition],
           'body_mass_kg': mass, 'body_mass_source': f'Streaming/{subject}/ParticipantDetails Bodymass (kg)',
           'forward_axis_lab': fwd.round(4).tolist(),
           'forward_axis_vs_pelvis_axis_deg': round(axis_agreement_deg, 2),
           'belt_slope_from_heel_path_deg': round(belt, 2), 'plate_tilt_used_deg': alpha, 'legs': {}}
    for side in 'RL':
        pairs = strides(trial['events'][side + 'HS'][...], n)
        pts_lab = {'pelvis_rear': psi, 'pelvis_front': asi, 'hip': marker(side + 'GT'),
                   'knee': (marker(side + 'KNE') + marker(side + 'KNEM')) / 2,
                   'ankle': (marker(side + 'ANK') + marker(side + 'ANKM')) / 2,
                   'heel': marker(side + 'HEE'), 'toe': marker(side + 'TOE')}
        pts = {k: sag(v) for k, v in pts_lab.items()}
        leg_len = float(np.nanmedian(pts['hip'][:, 1] - pts['ankle'][:, 1]))
        if not 0.5 <= leg_len <= 1.2:
            raise ValueError(f'{subject}/{condition} {side}: hip-ankle height {leg_len:.3f} not in metres')
        f, cop = plates[side]
        grf = sag((-(rx @ f)).T)  # GRF on the foot = -(plate force)
        cop_lab = (rx @ np.vstack([cop[0], cop[1], np.zeros(n)])).T
        cop_s = sag(cop_lab)
        # Moment-independent registration (UM21-C03 midpoint rule): over stance, mean CoP forward =
        # mean heel-toe midpoint forward; median CoP height = median lowest foot marker height.
        st = grf[:, 1] > 0.2 * np.nanpercentile(grf[:, 1], 99)
        mid = (pts['heel'] + pts['toe']) / 2
        d_fwd = float(np.nanmean(mid[st, 0]) - np.nanmean(cop_s[st, 0]))
        d_up = float(np.nanmedian(np.fmin(pts['heel'][st, 1], pts['toe'][st, 1])) - np.nanmedian(cop_s[st, 1]))
        cop_s = cop_s + [d_fwd, d_up]

        ch = {k: np.radians(resample(v[0], pairs)) for k, v in angles[side].items()}
        for j, J in (('hip', 'Hip'), ('knee', 'Knee'), ('ankle', 'Ankle')):
            ch[f'{j}_moment'] = resample(comp('jointMoments', f'{side}{J}Moment')[0], pairs)
        slots = {}
        for j, J in (('hip', 'Hip'), ('knee', 'Knee'), ('ankle', 'Ankle')):
            p = comp('jointPowers', f'{side}{J}Power')
            filled = [c + 1 for c in range(3) if np.nanmax(np.abs(np.nan_to_num(p[c]))) > 0]
            if filled:
                slots[j] = filled[0]
                ch[f'{j}_power'] = resample(p[filled[0] - 1], pairs)
        empty = {k: int((np.isfinite(v).sum(1) < sod.DEFAULTS['min_samples_per_unit']).sum())
                 for k, v in ch.items()}  # strides with (almost) only zero fill / missing samples
        branch = {}
        for k in ('pelvis_tilt', 'hip_angle', 'knee_angle', 'ankle_angle'):
            _, mask, _ = sod.screen_branch(ch[k])  # same deterministic screen detect_leg runs
            units = np.flatnonzero(mask.any(1))
            if units.size:
                branch[k] = {'strides_1based_frames': [list(pairs[u]) for u in units],
                             'first_frame': int(pairs[units[0]][0]), 'last_frame': int(pairs[units[-1]][1])}
                if (subject, condition, side, k) == ('AB07', 'i10', 'R', 'ankle_angle'):
                    out['episode_curves'] = {
                        'leg': 'AB07/i10 R ankle_angle, component 1 (deg), each stride resampled to 150 samples',
                        'set_aside': mask.any(1).astype(int).tolist(),
                        'curves_deg': np.round(np.degrees(ch[k]), 2).tolist()}
        rep = sod.detect_leg(f'UM21 {subject}/{condition}', 'right' if side == 'R' else 'left', ch,
                             marker_points={k: resample(v, pairs) for k, v in pts.items()},
                             cop=resample(cop_s, pairs), grf=resample(grf, pairs), task=TASK[condition],
                             grf_unit='N', body_mass_kg=mass, cop_registration=COP_REGISTRATION,
                             unit_durations_s=np.array([(b - a) / RATE_HZ for a, b in pairs]))
        out['legs'][side] = {
            'strides': len(pairs), 'power_slots': slots,
            'units_without_data': empty, 'branch_strides': branch,
            'cop_registration_m': {'forward': round(d_fwd, 4), 'up': round(d_up, 4)},
            'marker_checks': rep['marker_checks'], 'plate_frame_check': rep['plate_frame_check'],
            'grf_unit_check': rep['grf_unit_check'], 'leg_assignment_check': rep['leg_assignment_check'],
            'relations': [{x: r[x] for x in ('test', 'channels', 'product', 'reason', 'units_voting', 'units_agreeing')}
                          for r in rep['relations']],
            'channels': summarize(rep, TRUTH, slots), 'log': rep['log']}
        del ch, rep
    return out


def run_probe():
    import h5py
    resource.setrlimit(resource.RLIMIT_AS, (1024 ** 3, 1024 ** 3))
    if mem_available() < 2 * 1024 ** 3:
        raise MemoryError('Less than 2 GiB available; not started')
    rec = json.loads(C03.read_text())['source']
    st = SOURCE.stat()
    if (st.st_size, st.st_mtime_ns) != (rec['bytes'], rec['mtime_ns']):
        raise ValueError('Streaming.mat size/mtime differ from the UM21-C03 record')
    records = []
    with h5py.File(SOURCE, 'r', rdcc_nbytes=1024 ** 2) as handle:
        group = handle['Streaming']
        trials = sorted((s, c) for s in group for c in group[s]['Tread'])
        sample_a = random.Random(SEED_A).sample(trials, N_RANDOM)
        sample_b = random.Random(SEED_B).sample([t for t in trials if t not in sample_a], N_RANDOM)
        c03 = json.loads(C03.read_text())['method']['samples']
        if [f'{s}/{c}' for s, c in sample_a] != c03['A'] or [f'{s}/{c}' for s, c in sample_b] != c03['B']:
            raise ValueError('Seeded samples differ from UM21-C03')
        plan = [('A', s, c, '') for s, c in sample_a] + [('B', s, c, '') for s, c in sample_b] + \
               [('extra', s, c, why) for s, c, why in EXTRA]
        for label, s, c, why in plan:
            if mem_available() < 2 * 1024 ** 3:
                raise MemoryError('Less than 2 GiB available; stopped at a recording boundary')
            r = probe_recording(handle, s, c)
            r.update(sample=label, why=why or None, peak_rss_mib_after=round(peak_rss_mib(), 1))
            records.append(r)
            print(f'{label} {s}/{c} done, peak RSS {peak_rss_mib():.0f} MiB', flush=True)
            if peak_rss_mib() > RSS_CAP_MIB:
                raise MemoryError(f'peak RSS {peak_rss_mib():.0f} MiB above {RSS_CAP_MIB}; stopped')
    after = SOURCE.stat()
    if (after.st_size, after.st_mtime_ns) != (st.st_size, st.st_mtime_ns):
        raise ValueError('Source changed during the read')
    data = {'task_id': 'CORE-04', 'pilot': 'UM21', 'scientific_approval': False,
            'applies_to_dataset': 'nothing',
            'source': {'path': str(SOURCE.relative_to(ROOT)), 'bytes': st.st_size, 'mtime_ns': st.st_mtime_ns,
                       'sha256_recorded': rec['sha256_recorded'],
                       'note': 'size and mtime checked against the UM21-C03 record before and after; bytes not rehashed'},
            'code_sha256': {str(Path(__file__).relative_to(ROOT)): digest(Path(__file__)),
                            'contributor_tools/common/sign_offset_detector.py':
                                digest(ROOT / 'contributor_tools/common/sign_offset_detector.py')},
            'detector_parameters': {k: list(v) if isinstance(v, tuple) else v for k, v in sod.DEFAULTS.items()},
            'seeds': {'A': SEED_A, 'B': SEED_B,
                      'rule': 'A = random.Random(A).sample(sorted 50 recordings, 4); B = random.Random(B).sample(the 46 others, 4) (UM21-C03).'},
            'samples': {'A': [f'{s}/{c}' for s, c in sample_a], 'B': [f'{s}/{c}' for s, c in sample_b],
                        'extra': [f'{s}/{c}: {why}' for s, c, why in EXTRA]},
            'target_rule': sod.TARGET_CONVENTION['rule_id'],
            'previous_probe': {str(PROBE_V1.relative_to(ROOT)): digest(PROBE_V1)} if PROBE_V1.exists() else None,
            'resources': {'peak_rss_mib': round(peak_rss_mib(), 1), 'cap_mib': 300,
                          'mode': 'read-only probe exception; one recording at a time; nice 19, ionice idle, 1 thread; RLIMIT_AS 1 GiB'},
            'recordings': records}
    PROBE.write_text(json.dumps(data, separators=(',', ':')) + '\n')
    print(json.dumps({'peak_rss_mib': data['resources']['peak_rss_mib'], 'sha256': digest(PROBE)}))


def main():
    os.nice(max(0, 19 - os.nice(0)))
    run_probe()


if __name__ == '__main__':
    main()
