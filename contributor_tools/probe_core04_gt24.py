"""CORE-04 GT24 pilot, PROBE step (read-only data access).

Read-only probe (AGENTS.md exception): one trial (condition folder) at a time from the
GaTech 2024 TaskAgnostic Parsed zips, one zip member at a time; nothing written under
converted_datasets/ or source folders; peak RSS recorded and capped below 300 MiB; nice 19 /
ionice idle; single-threaded. Writes docs/quality/audits/core04-gt24-pilot-probe.json.

Sample: numpy default_rng(SEED).permutation over the (phase, subject) units of the README
mass table; the first 3 units in that order that have exo-off level walking, plus the first
3 other units. Conditions per unit: level 1.2 m/s exo on, level 1.2 m/s exo off (if
present), incline 5 deg exo on, decline 5 deg exo on; both legs.

Adapter (no sign changes):
- Channels: angle_filt hip_flexion / knee_angle / ankle_angle (deg -> rad); moment_filt
  (net ID moment, N*m/kg; the normalizing mass is unresolved, so magnitudes are not
  interpreted and every decision used here is scale-free); power (net, W/kg).
- Units: heel strike to heel strike of each leg, from insole_sim vertical force above 10 %
  body weight (0.4-2.5 s per stride), resampled to 150 samples; durations from the samples
  at 200 Hz.
- Geometry: the Parsed zips hold no markers, so there is no marker reference and no pelvis
  facing. The lab force file is not used (its walking direction is +-z per trial). Ankle
  plate geometry is taken in each foot's calcn frame from insole_sim (x along the foot, y
  foot-up, z = x cross y lifts the toes; GT24-C02): CoP = (cop_x, 0), force = (force_x,
  force_y), ankle = generic talus position (0.04877, 0.04195) m. A 2-D moment is invariant to
  this in-plane rotation. Knee and hip positions are unavailable, so their lever arms abstain.
- Mass: README "w/ exo" mass for exo-on trials and "w/o exo" mass for exo-off trials (first
  day), declared for the GRF-unit check.
- Documentation: README lines 90-91 ("Hip flexion, knee extension, and ankle plantarflexion
  is positive") supplied as documentation evidence for the angles and, read as the sign of
  each DOF's generalized force, for the moments. Each leg is run twice: with that
  documentation (primary) and without it (data only).

Ground truth (rule B, target = sign x source; GT24-C02 and the survey): hip +1, knee angle -1
(source extension positive), ankle +1 (data dorsiflexion positive despite the README), hip
moment +1, knee moment -1, ankle moment +1 (internal, plantarflexor negative), powers +1.
Applies nothing to any dataset.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import collections
import hashlib
import io
import json
from pathlib import Path
import re
import resource
import sys
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.common import sign_offset_detector as sod  # noqa: E402
from contributor_tools.common.documentation_policy import split_documentation  # noqa: E402

SRC = Path('/mnt/s/locomotion_data/GaTech_2024_TaskAgnostic')
README = SRC / 'readme.txt'
ZIPS = {'Phase1And2': SRC / 'Phase1And2_Parsed.zip', 'Phase3': SRC / 'Phase3_Parsed.zip'}
AUDITS = ROOT / 'docs/quality/audits'
PROBE = AUDITS / 'core04-gt24-pilot-probe.json'
SEED = 20261104
N_WITH_OFF, N_OTHER = 3, 3
G = 9.81
RATE_HZ = 200.0
N_SAMPLES = 150
STANCE_BW = 0.10
ANKLE_CALCN = (0.04877, 0.04195)  # generic gait2392/2354 talus position in calcn (m), as GT24-C02
RSS_CAP_MIB = 280.0
# README lines 52-82, first-day masses: (w/o exo, w/ exo)
MASS = {'Phase1And2': {'BT01': (80.59, 87.02), 'BT02': (72.24, 79.09), 'BT03': (95.29, 101.52), 'BT04': (98.23, 106.04),
                       'BT06': (79.33, 85.78), 'BT07': (64.49, 70.61), 'BT08': (69.13, 75.67), 'BT09': (82.31, 88.97),
                       'BT10': (93.45, 100.11), 'BT11': (50.39, 56.98), 'BT12': (78.15, 84.62), 'BT13': (89.85, 96.74),
                       'BT14': (67.30, 74.35), 'BT15': (58.40, 65.87), 'BT16': (64.33, 72.03), 'BT17': (60.03, 67.36)},
        'Phase3': {'BT01': (77.29, 84.28), 'BT02': (72.33, 79.10), 'BT13': (88.99, 96.03), 'BT18': (67.96, 74.96),
                   'BT19': (69.95, 76.84), 'BT20': (55.44, 62.50), 'BT21': (58.85, 65.86), 'BT22': (76.79, 84.27),
                   'BT23': (67.23, 74.24), 'BT24': (77.79, 84.84)}}
CONDITIONS = [('level 1.2 m/s, exo on', r'^normal_walk_\d+_\d+_1-2_on$', 'level_walking'),
              ('level 1.2 m/s, exo off', r'^normal_walk_\d+_\d+_1-2_off$', 'level_walking'),
              ('incline 5 deg, exo on', r'^incline_walk_\d+_\d+_up5_on$', 'incline_walking'),
              ('decline 5 deg, exo on', r'^incline_walk_\d+_\d+_down5_on$', 'decline_walking')]
TRUTH = {'hip_angle': 1, 'knee_angle': -1, 'ankle_angle': 1, 'hip_moment': 1, 'knee_moment': -1,
         'ankle_moment': 1, 'hip_power': 1, 'knee_power': 1, 'ankle_power': 1}
CHANNELS = list(TRUTH)
README_DOC = 'README lines 90-91: "Hip flexion, knee extension, and ankle plantarflexion is positive"'
README_ID = 'gt24-readme:L90-91'
DOCUMENTATION = [('hip_angle', 1, README_DOC, README_ID), ('knee_angle', -1, README_DOC, README_ID),
                 ('ankle_angle', -1, README_DOC, README_ID),
                 ('hip_moment', 1, README_DOC + ' (read as the DOF generalized-force sign)', README_ID),
                 ('knee_moment', -1, README_DOC + ' (read as the DOF generalized-force sign)', README_ID),
                 ('ankle_moment', -1, README_DOC + ' (read as the DOF generalized-force sign)', README_ID)]
# Documentation policy (Jose, 2026-10-30, "fix both readmes based on the evidence"): only
# statements no verified audit has refuted are passed; refuted ones are logged.
DOCUMENTATION_PASSED, DOCUMENTATION_REFUTED = split_documentation('GT24', DOCUMENTATION)
COP_REGISTRATION = ('calcn frame: CoP and force from insole_sim (publisher plate data rotated into calcn); ankle at the '
                    'generic talus position (0.04877, 0.04195) m in calcn; no markers in the Parsed zips')


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def peak_rss_mib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def mem_available():
    line = next(s for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:'))
    return int(line.split()[1]) * 1024


class Reader:
    """One zip member at a time; records each member's decompressed size and sha256."""

    def __init__(self):
        self.zips, self.members, self.listing = {}, [], {}

    def zip(self, phase):
        return self.zips.setdefault(phase, zipfile.ZipFile(ZIPS[phase]))

    def conditions(self, phase, subject):
        key = (phase, subject)
        if key not in self.listing:
            out = set()
            for name in self.zip(phase).namelist():
                p = name.split('/')
                if len(p) >= 4 and p[1] == subject and p[3]:
                    out.add(p[2])
            self.listing[key] = sorted(out)
        return self.listing[key]

    def table(self, phase, member, usecols=None):
        import pandas as pd
        raw = self.zip(phase).read(member)
        self.members.append({'zip': ZIPS[phase].name, 'member': member, 'bytes': len(raw),
                             'sha256': hashlib.sha256(raw).hexdigest()})
        df = pd.read_csv(io.BytesIO(raw), usecols=usecols)
        del raw
        return df


def resample(x, pairs):
    out = []
    for a, b in pairs:
        seg = np.asarray(x[a:b + 1], float)
        src = np.arange(seg.shape[0])
        grid = np.linspace(0, seg.shape[0] - 1, N_SAMPLES)
        if seg.ndim == 1:
            out.append(np.interp(grid, src, seg))
        else:
            out.append(np.stack([np.interp(grid, src, seg[:, k]) for k in range(seg.shape[1])], -1))
    return np.array(out)


def strides_from_force(fy, bw):
    on = np.nan_to_num(fy) > STANCE_BW * bw
    hs = np.flatnonzero(np.diff(on.astype(int)) == 1) + 1
    return [(int(a), int(b)) for a, b in zip(hs[:-1], hs[1:]) if 0.4 * RATE_HZ <= b - a <= 2.5 * RATE_HZ]


def summarize(rep):
    keep = ('median_abs_slope', 'median_abs_r', 'median_slope', 'vertical_only', 'median_late_stance_mean',
            'half_cycle', 'half_cycle_ambiguous', 'median_unit_statistic', 'leg_assignment', 'citation')
    out = {}
    for k, c in rep['channels'].items():
        t = TRUTH.get(k)
        if c['verdict'] in ('apply', 'suggest'):
            outcome = f"{'applied' if c['verdict'] == 'apply' else 'suggested'}_{'correct' if c['sign'] == t else 'wrong'}"
        else:
            outcome = c['verdict']
        out[k] = {'verdict': c['verdict'], 'sign': c['sign'], 'truth': t, 'outcome': outcome,
                  'confidence': c['confidence'], 'families': c.get('families'), 'reason': c['reason'],
                  'evidence': [{'test': e['test'], 'strength': e['strength'], 'sign': e['sign'],
                                'agree': f"{e['units_agreeing']}/{e['units_voting']}", 'reason': e['reason'],
                                'stats': {s: v for s, v in (e.get('stats') or {}).items() if s in keep}}
                               for e in c['evidence']]}
    return out


def condition_legs(rd, phase, subject, label, cond, task):
    base = f'Parsed/{subject}/{cond}/{subject}_{cond}_'
    exo_on = cond.endswith('_on')
    mass = MASS[phase][subject][1 if exo_on else 0]
    ang = rd.table(phase, base + 'angle_filt.csv')
    mom = rd.table(phase, base + 'moment_filt.csv')
    pw = rd.table(phase, base + 'power.csv')
    ins = rd.table(phase, base + 'insole_sim.csv')
    n = len(ang)
    for name, df in (('moment_filt', mom), ('power', pw), ('insole_sim', ins)):
        if len(df) != n or np.nanmax(np.abs(df['time'].to_numpy(float) - ang['time'].to_numpy(float))) > 1e-3:
            raise ValueError(f'{phase}/{subject}/{cond}: {name} time base differs from angle_filt')
    legs = []
    for s in 'lr':
        fy = ins[f'insole_{s}_force_y'].to_numpy(float)
        pairs = [(a, b) for a, b in strides_from_force(fy, mass * G) if b < n]
        rec = {'phase': phase, 'subject': subject, 'condition': label, 'source_condition': cond, 'task': task,
               'side': 'left' if s == 'l' else 'right', 'exo': 'on' if exo_on else 'off', 'body_mass_kg': mass,
               'strides': len(pairs)}
        if len(pairs) < sod.DEFAULTS['min_units']:
            rec['skipped'] = f'{len(pairs)} strides (< 5)'
            legs.append(rec)
            continue
        ch = {'hip_angle': np.radians(ang[f'hip_flexion_{s}'].to_numpy(float)),
              'knee_angle': np.radians(ang[f'knee_angle_{s}'].to_numpy(float)),
              'ankle_angle': np.radians(ang[f'ankle_angle_{s}'].to_numpy(float)),
              'hip_moment': mom[f'hip_flexion_{s}_moment'].to_numpy(float),
              'knee_moment': mom[f'knee_angle_{s}_moment'].to_numpy(float),
              'ankle_moment': mom[f'ankle_angle_{s}_moment'].to_numpy(float),
              'hip_power': pw[f'hip_flexion_{s}_power'].to_numpy(float),
              'knee_power': pw[f'knee_angle_{s}_power'].to_numpy(float),
              'ankle_power': pw[f'ankle_angle_{s}_power'].to_numpy(float)}
        chans = {k: resample(v, pairs) for k, v in ch.items()}
        grf = resample(np.stack([ins[f'insole_{s}_force_x'], fy], -1).astype(float), pairs)
        cop = resample(np.stack([ins[f'insole_{s}_cop_x'].to_numpy(float), np.zeros(n)], -1), pairs)
        ankle = np.broadcast_to(np.array(ANKLE_CALCN), cop.shape).copy()
        durations = np.array([(b - a) / RATE_HZ for a, b in pairs])
        kw = dict(joint_positions={'ankle': ankle}, cop=cop, grf=grf, task=task, grf_unit='N',
                  body_mass_kg=mass, cop_registration=COP_REGISTRATION, unit_durations_s=durations)
        rep = sod.detect_leg(f'GT24 {phase}/{subject} {label}', rec['side'], chans,
                             documentation=DOCUMENTATION_PASSED, **kw)
        data_only = sod.detect_leg(f'GT24 {phase}/{subject} {label} (data only)', rec['side'], chans, **kw)
        rec.update({'plate_frame_check': rep['plate_frame_check'], 'grf_unit_check': rep['grf_unit_check'],
                    'leg_assignment_check': rep['leg_assignment_check'],
                    'relations': [{x: r[x] for x in ('test', 'channels', 'product', 'reason', 'units_voting', 'units_agreeing')}
                                  for r in rep['relations']],
                    'channels': summarize(rep), 'data_only': summarize(data_only)})
        legs.append(rec)
    return legs


def run_probe():
    import pandas  # noqa: F401  (import before the address-space limit)
    resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 ** 2, 1536 * 1024 ** 2))
    if mem_available() < 2 * 1024 ** 3:
        raise MemoryError('Less than 2 GiB available; not started')
    before = {p: (z.stat().st_size, z.stat().st_mtime_ns) for p, z in ZIPS.items()}
    units = sorted((p, s) for p, d in MASS.items() for s in d)
    order = np.random.default_rng(SEED).permutation(len(units))
    rd = Reader()
    with_off, other = [], []
    for k in order:
        p, s = units[k]
        conds = rd.conditions(p, s)
        if not any(re.match(CONDITIONS[0][1], c) for c in conds):
            continue
        has_off = any(re.match(CONDITIONS[1][1], c) for c in conds)
        if has_off and len(with_off) < N_WITH_OFF:
            with_off.append((p, s))
        elif not has_off and len(other) < N_OTHER:
            other.append((p, s))
        if len(with_off) == N_WITH_OFF and len(other) == N_OTHER:
            break
    chosen = [u for u in units if u in with_off + other]
    records = []
    for p, s in [units[k] for k in order if units[k] in chosen]:
        conds = rd.conditions(p, s)
        for label, pattern, task in CONDITIONS:
            match = sorted(c for c in conds if re.match(pattern, c))
            if not match:
                records.append({'phase': p, 'subject': s, 'condition': label, 'skipped': 'condition not present'})
                continue
            if mem_available() < 2 * 1024 ** 3:
                raise MemoryError('Less than 2 GiB available; stopped at a trial boundary')
            for leg in condition_legs(rd, p, s, label, match[0], task):
                leg['peak_rss_mib_after'] = round(peak_rss_mib(), 1)
                records.append(leg)
            print(f'{p}/{s} {label} ({match[0]}): peak RSS {peak_rss_mib():.0f} MiB', flush=True)
            if peak_rss_mib() > RSS_CAP_MIB:
                raise MemoryError(f'peak RSS {peak_rss_mib():.0f} MiB above {RSS_CAP_MIB}; stopped')
    after = {p: (z.stat().st_size, z.stat().st_mtime_ns) for p, z in ZIPS.items()}
    if after != before:
        raise ValueError('A source zip changed during the read')
    lines = README.read_text(errors='replace').splitlines()
    data = {'task_id': 'CORE-04', 'pilot': 'GT24', 'run': 'v1', 'scientific_approval': False, 'applies_to_dataset': 'nothing',
            'target_rule': sod.TARGET_CONVENTION['rule_id'], 'seed': SEED,
            'selection': f'default_rng({SEED}).permutation over sorted (phase, subject) README-mass units; first '
                         f'{N_WITH_OFF} with exo-off level walking, first {N_OTHER} without; level 1.2 exo on is required.',
            'subjects': [f'{p}/{s}' for p, s in chosen], 'subjects_with_exo_off': [f'{p}/{s}' for p, s in with_off],
            'conditions': [c[0] for c in CONDITIONS],
            'readme': {'path': str(README), 'sha256': digest(README), 'lines_90_91': lines[89:91]},
            'documentation_supplied': DOCUMENTATION_PASSED,
            'documentation_refuted': DOCUMENTATION_REFUTED,
            'zips': {p: {'path': str(z), 'bytes': before[p][0], 'mtime_ns': before[p][1],
                         'note': 'multi-GB, not hashed; size and mtime equal before and after; each member hashed'}
                     for p, z in ZIPS.items()},
            'members_read': rd.members,
            'code_sha256': {str(Path(__file__).relative_to(ROOT)): digest(Path(__file__)),
                            'contributor_tools/common/sign_offset_detector.py':
                                digest(ROOT / 'contributor_tools/common/sign_offset_detector.py')},
            'detector_parameters': {k: list(v) if isinstance(v, tuple) else v for k, v in sod.DEFAULTS.items()},
            'resources': {'peak_rss_mib': round(peak_rss_mib(), 1), 'cap_mib': 300,
                          'mode': 'read-only probe exception; one trial at a time, one zip member at a time; nice 19, '
                                  'ionice idle, 1 thread; RLIMIT_AS 1.5 GiB'},
            'records': records}
    PROBE.write_text(json.dumps(data, separators=(',', ':')) + '\n')
    print(json.dumps({'peak_rss_mib': data['resources']['peak_rss_mib'], 'sha256': digest(PROBE),
                      'subjects': data['subjects']}))


def main():
    os.nice(max(0, 19 - os.nice(0)))
    run_probe()


if __name__ == '__main__':
    main()
