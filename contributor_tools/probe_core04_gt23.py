"""CORE-04 GT23 pilot, PROBE step (read-only data access).

Read-only probe (AGENTS.md exception): one trial at a time from
/mnt/s/locomotion_data/Gtech_2023/RawData, nothing written under converted_datasets/ or source
folders, peak RSS recorded and capped below 300 MiB, nice 19 / ionice idle, single-threaded.
Seeded subjects; per subject seven conditions (level 1.2 m/s, incline 5 and 10 deg, decline 5
and 10 deg, stair ascent, stair descent). Units are the dataset's own stride segmentation
(Segmentation/<subject>/<task>_parsing.mat, start/end times per leg; only legs with valid plate
data are listed there). Writes docs/quality/audits/core04-gt23-pilot-probe-v2.json.

Adapter (no sign changes): Joint_Angle hip_flexion/knee_angle/ankle_angle (deg -> rad),
Joint_Moments (published N*m/kg; divisor is not always the participant's mass, GT23-C03, so
magnitudes are not interpreted; every detector decision used here is scale-free), Joint_Powers
(W/kg, same divisor). Markers from MarkerData/<task>.trc (mm -> m) and plate forces / CoP from
GroundFrame_GRFs.csv (N, m) share the OpenSim ground frame (Y up); each stride is projected on
its pelvis facing (horizontal ASIS-mid minus PSIS-mid), with the foot heel-to-toe axis as a
fallback. No CoP shift is applied; the detector's CoP-within-foot check tests that
registration. Body mass = README mass of the participant (GRF-unit check and ID-light).

Ground truth (rule B, target = sign x source): OpenSim gait2392 coordinates, so hip +1, knee
angle -1, ankle +1, hip moment +1, knee moment -1, ankle moment +1 (internal, ID); powers +1.
Applies nothing to any dataset.

Split from review_core04_gt23_pilot.py on 2026-10-31 so that sheet edits never change the hash
recorded in a probe file. The sheet step is contributor_tools/review_core04_gt23_pilot.py.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import resource
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.common import sign_offset_detector as sod  # noqa: E402

RAW = Path('/mnt/s/locomotion_data/Gtech_2023/RawData')
SEG = Path('/mnt/s/locomotion_data/Gtech_2023/Segmentation')
AUDITS = ROOT / 'docs/quality/audits'
C03 = AUDITS / 'gt23-c03-normalizing-mass.json'
PROBE_V1 = AUDITS / 'core04-gt23-pilot-probe.json'  # v1: foot heel-to-toe forward axis (history; not rewritten)
PROBE = AUDITS / 'core04-gt23-pilot-probe-v2.json'  # v2: per-stride pelvis facing as the forward axis
SEED = 20261102
N_SUBJECTS = 3
N_SAMPLES = 150
RSS_CAP_MIB = 280.0
UP = np.array([0.0, 1.0, 0.0])  # OpenSim ground frame, Y up
CONDITIONS = [  # (label, trial folder(s) pattern, segmentation name(s), detector task)
    ('level 1.2 m/s', 'normal_walk_1', ['normal_walk_1_1-2'], 'level_walking'),
    ('incline 5 deg', 'incline_walk_1', ['incline_walk_1_up5'], 'incline_walking'),
    ('incline 10 deg', 'incline_walk_2', ['incline_walk_2_up10'], 'incline_walking'),
    ('decline 5 deg', 'incline_walk_1', ['incline_walk_1_down5'], 'decline_walking'),
    ('decline 10 deg', 'incline_walk_2', ['incline_walk_2_down10'], 'decline_walking'),
    ('stair ascent', 'stairs', 'up', 'stair_ascent'),
    ('stair descent', 'stairs', 'down', 'stair_descent'),
]
TRUTH = {'hip_angle': 1, 'knee_angle': -1, 'ankle_angle': 1, 'hip_moment': 1, 'knee_moment': -1,
         'ankle_moment': 1, 'hip_power': 1, 'knee_power': 1, 'ankle_power': 1}
CHANNELS = list(TRUTH)
COP_REGISTRATION = ('none: plate CoP (GroundFrame_GRFs) and markers (.trc) are both in the OpenSim ground '
                    'frame; no shift applied; tested by the detector CoP-within-foot check')


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def peak_rss_mib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def mem_available():
    line = next(s for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:'))
    return int(line.split()[1]) * 1024


class Reader:
    """Bounded reads with size/mtime checked before and after each file."""
    def __init__(self):
        self.files = []

    def _stat(self, p):
        st = Path(p).stat()
        return st.st_size, st.st_mtime_ns

    def csv(self, path, cols):
        import pandas as pd
        before = self._stat(path)
        df = pd.read_csv(path, usecols=cols)
        if self._stat(path) != before:
            raise ValueError(f'{path} changed during the read')
        self.files.append({'path': str(path), 'bytes': before[0], 'mtime_ns': before[1]})
        return df

    def trc(self, path, markers):
        import pandas as pd
        before = self._stat(path)
        with open(path) as f:
            head = [next(f) for _ in range(5)]
        names = head[3].rstrip('\n').split('\t')[2:]
        names = [n for n in names if n]
        cols, idx = {}, [1]
        for m in markers:
            if m in names:
                k = names.index(m)
                cols[m] = list(range(2 + 3 * k, 5 + 3 * k))
                idx += cols[m]
        df = pd.read_csv(path, sep='\t', skiprows=5, header=None, usecols=sorted(set(idx)), engine='c')
        if self._stat(path) != before:
            raise ValueError(f'{path} changed during the read')
        self.files.append({'path': str(path), 'bytes': before[0], 'mtime_ns': before[1]})
        t = df[1].to_numpy(float)
        return t, {m: df[c].to_numpy(float) / 1000.0 for m, c in cols.items()}


def parsing(subject, name):
    import scipy.io as sio
    m = sio.loadmat(SEG / subject / f'{name}_parsing.mat', squeeze_me=True)
    out = {}
    for s in ('left', 'right'):
        a = np.atleast_2d(np.asarray(m[s], float)) if np.size(m[s]) else np.zeros((0, 2))
        out[s] = [tuple(r) for r in a if r.size == 2]
    return out


def resample(x, idx_pairs):
    out = []
    for a, b in idx_pairs:
        seg = np.asarray(x[a:b + 1], float)
        src = np.arange(seg.shape[0])
        grid = np.linspace(0, seg.shape[0] - 1, N_SAMPLES)
        if seg.ndim == 1:
            out.append(np.interp(grid, src, seg))
        else:
            out.append(np.stack([np.interp(grid, src, seg[:, k]) for k in range(seg.shape[1])], -1))
    return np.array(out)


def stride_axis_angle(heel, toe, axis):
    """Signed angle (deg, about +Y) from one stride's foot heel-to-toe axis to the pelvis-facing
    axis; None when the foot markers are missing for the whole stride."""
    d = np.asarray(toe, float) - np.asarray(heel, float)
    d = d[np.isfinite(d).all(axis=1)]
    if not len(d):
        return None
    h = d - np.outer(d @ UP, UP)
    f = np.median(h, axis=0)
    if not np.isfinite(f).all() or np.linalg.norm(f) == 0:
        return None
    f = f / np.linalg.norm(f)
    return float(np.degrees(np.arctan2(np.cross(f, axis) @ UP, f @ axis)))


def load_trial(rd, subject, trial, side):
    s, S = side[0], side[0].upper()
    d = RAW / subject / 'CSV_Data' / trial
    ang = rd.csv(d / 'Joint_Angle.csv', ['time', f'hip_flexion_{s}', f'knee_angle_{s}', f'ankle_angle_{s}'])
    mom = rd.csv(d / 'Joint_Moments.csv', ['time', f'hip_flexion_{s}_moment', f'knee_angle_{s}_moment', f'ankle_angle_{s}_moment'])
    pw = rd.csv(d / 'Joint_Powers.csv', ['time', f'hip_flexion_power_{s}', f'knee_power_{s}', f'ankle_power_{s}'])
    grf = rd.csv(d / 'GroundFrame_GRFs.csv', ['time'] + [f'{S}{k}' for k in ('ForceX', 'ForceY_Vertical', 'ForceZ', 'COPX', 'COPY_Vertical', 'COPZ')])
    mk = [f'{S}CAL', f'{S}MT1', f'{S}MT5', f'{S}ANK', f'{S}MANK', f'{S}KNE', f'{S}MKNE', f'{S}GTR', 'LASI', 'RASI', 'LPSI', 'RPSI']
    tm, markers = rd.trc(RAW / subject / 'MarkerData' / f'{trial}.trc', mk)
    t = ang['time'].to_numpy(float)
    for name, df in (('moments', mom), ('powers', pw), ('grf', grf)):
        if len(df) != len(t) or np.nanmax(np.abs(df['time'].to_numpy(float) - t)) > 1e-3:
            raise ValueError(f'{subject}/{trial}: {name} time base differs from Joint_Angle')
    j = np.clip(np.searchsorted(tm, t), 0, len(tm) - 1)  # marker frame per CSV sample (both 200 Hz)
    mid = lambda a, b: (markers[a] + markers[b]) / 2 if a in markers and b in markers else None
    pts3 = {'heel': markers.get(f'{S}CAL'), 'toe': mid(f'{S}MT1', f'{S}MT5'),
            'ankle': mid(f'{S}ANK', f'{S}MANK'), 'knee': mid(f'{S}KNE', f'{S}MKNE'),
            'hip': markers.get(f'{S}GTR'), 'pelvis_front': mid('LASI', 'RASI'), 'pelvis_rear': mid('LPSI', 'RPSI')}
    pts3 = {k: v[j] for k, v in pts3.items() if v is not None}
    ch = {'hip_angle': np.radians(ang[f'hip_flexion_{s}'].to_numpy(float)),
          'knee_angle': np.radians(ang[f'knee_angle_{s}'].to_numpy(float)),
          'ankle_angle': np.radians(ang[f'ankle_angle_{s}'].to_numpy(float)),
          'hip_moment': mom[f'hip_flexion_{s}_moment'].to_numpy(float),
          'knee_moment': mom[f'knee_angle_{s}_moment'].to_numpy(float),
          'ankle_moment': mom[f'ankle_angle_{s}_moment'].to_numpy(float),
          'hip_power': pw[f'hip_flexion_power_{s}'].to_numpy(float),
          'knee_power': pw[f'knee_power_{s}'].to_numpy(float),
          'ankle_power': pw[f'ankle_power_{s}'].to_numpy(float)}
    force = np.stack([grf[f'{S}ForceX'], grf[f'{S}ForceY_Vertical'], grf[f'{S}ForceZ']], -1).astype(float)
    cop = np.stack([grf[f'{S}COPX'], grf[f'{S}COPY_Vertical'], grf[f'{S}COPZ']], -1).astype(float)
    return t, ch, pts3, force, cop


def condition_record(rd, subject, label, trial, seg, task, mass):
    """All strides of one leg for one condition (stairs: pooled over passes, per leg)."""
    if trial == 'stairs':
        names = sorted((p.name.replace('_parsing.mat', '') for p in (SEG / subject).glob(f'stairs_1_*_{seg}_parsing.mat')),
                       key=lambda n: int(re.search(r'stairs_1_(\d+)', n).group(1)))
        plan = [(re.match(r'(stairs_1_\d+)', n).group(1), n) for n in names]
    else:
        plan = [(trial, seg[0])]
    counts = collections.Counter()
    for _, n in plan:
        for s, v in parsing(subject, n).items():
            counts[s] += len(v)
    if not counts or max(counts.values()) < sod.DEFAULTS['min_units']:
        return {'subject': subject, 'condition': label, 'skipped': f'fewer than 5 parsed strides per leg ({dict(counts)})'}
    side = max(('left', 'right'), key=lambda s: counts[s])
    acc = collections.defaultdict(list)
    fwd_list, heading, durations, sources = [], [], [], []
    axis_used = collections.Counter()
    axis_agreement, axis_angles = collections.Counter(), []
    for tr, n in plan:
        strides = parsing(subject, n)[side]
        if not strides:
            continue
        t, ch, pts3, force, cop = load_trial(rd, subject, tr, side)
        pairs = []
        for t0, t1 in strides:
            a, b = int(np.searchsorted(t, t0)), int(np.searchsorted(t, t1))
            if 0 <= a < b < len(t):
                pairs.append((a, b))
                durations.append(float(t[b] - t[a]))
        if not pairs:
            continue
        win = np.concatenate([np.arange(a, b + 1) for a, b in pairs])
        fwd = sod.forward_axis(pts3['heel'][win], pts3['toe'][win], UP)
        fwd_list.append(fwd.round(4).tolist())
        if 'pelvis_front' in pts3 and 'pelvis_rear' in pts3:
            pv = np.nanmedian(pts3['pelvis_front'][win] - pts3['pelvis_rear'][win], 0)
            pv = pv - (pv @ UP) * UP
            ang = np.degrees(np.arctan2(np.cross(fwd, pv) @ UP, fwd @ pv))
            heading.append(round(float(ang), 1))
        for k, v in ch.items():
            acc[k].append(resample(v, pairs))
        # Forward axis per stride = pelvis facing (horizontal ASIS-mid minus PSIS-mid, median over
        # the stride). The foot heel-to-toe axis carries toe-out (5-28 deg here) and leaked frontal
        # forces into v1; it is kept only as a fallback when pelvis markers are missing.
        for a, b in pairs:
            axis, used = fwd, 'foot (fallback)'
            if 'pelvis_front' in pts3 and 'pelvis_rear' in pts3:
                pv = np.nanmedian(pts3['pelvis_front'][a:b + 1] - pts3['pelvis_rear'][a:b + 1], 0)
                pv = pv - (pv @ UP) * UP
                if np.isfinite(pv).all() and np.linalg.norm(pv) > 0:
                    axis, used = pv / np.linalg.norm(pv), 'pelvis'
            axis_used[used] += 1
            # Per-stride agreement of the pelvis facing and this stride's foot heel-to-toe axis.
            # More than 90 deg apart means one of them points backwards (swapped markers or a
            # mislabelled pass): the stride's geometry (markers, GRF, CoP) is withheld, not guessed.
            agree = None
            if used == 'pelvis' and 'heel' in pts3 and 'toe' in pts3:
                ang = stride_axis_angle(pts3['heel'][a:b + 1], pts3['toe'][a:b + 1], axis)
                if ang is not None:
                    agree = abs(ang) < 90.0
                    axis_angles.append(round(ang, 1))
            axis_agreement['within_90' if agree else ('beyond_90' if agree is False else 'not_checked')] += 1
            withhold = agree is False
            sag = lambda v: (np.full((b - a + 1, 2), np.nan) if withhold
                             else sod.project_sagittal(v[a:b + 1], axis, UP))
            one = [(0, b - a)]
            for k in ('heel', 'toe', 'ankle', 'knee', 'hip', 'pelvis_front', 'pelvis_rear'):
                if k in pts3:
                    acc['pt_' + k].append(resample(sag(pts3[k]), one))
                else:  # marker absent in this pass: missing, not invented
                    acc['pt_' + k].append(np.full((1, N_SAMPLES, 2), np.nan))
            acc['grf'].append(resample(sag(force), one))
            acc['cop'].append(resample(sag(cop), one))
        sources.append(f'{tr} ({n}): {len(pairs)} strides')
        del ch, pts3, force, cop
    cat = {k: np.concatenate(v) for k, v in acc.items()}
    chans = {k: cat[k] for k in CHANNELS}
    pts = {k[3:]: cat[k] for k in cat if k.startswith('pt_')}
    rep = sod.detect_leg(f'GT23 {subject} {label}', side, chans, marker_points=pts, cop=cat['cop'],
                         grf=cat['grf'], task=task, grf_unit='N', body_mass_kg=mass,
                         cop_registration=COP_REGISTRATION, unit_durations_s=np.array(durations))
    return {'subject': subject, 'condition': label, 'task': task, 'side': side, 'strides': int(len(durations)),
            'sources': sources, 'body_mass_kg': mass, 'forward_axes_lab': fwd_list,
            'pelvis_heading_vs_forward_deg': heading,
            'forward_axis': 'per-stride pelvis facing', 'forward_axis_strides': dict(axis_used),
            'axis_agreement_strides': dict(axis_agreement),
            'pelvis_minus_foot_axis_deg_per_stride': axis_angles,
            'marker_checks': rep['marker_checks'], 'plate_frame_check': rep['plate_frame_check'],
            'grf_unit_check': rep['grf_unit_check'], 'leg_assignment_check': rep['leg_assignment_check'],
            'relations': [{x: r[x] for x in ('test', 'channels', 'product', 'reason', 'units_voting', 'units_agreeing')}
                          for r in rep['relations']],
            'channels': summarize(rep)}


def summarize(rep):
    keep = ('median_abs_slope', 'median_abs_r', 'scale_review', 'median_slope', 'vertical_only',
            'median_late_stance_mean', 'half_turn_offset', 'half_cycle', 'half_cycle_ambiguous',
            'median_unit_statistic', 'leg_assignment')
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
                               for e in c['evidence']],
                  'offset': {x: c['offset'].get(x) for x in ('estimate', 'ci95', 'flag_for_review', 'applied')},
                  'branch_screen': c.get('branch_screen') and {x: c['branch_screen'][x] for x in
                                                               ('branch_180_frames', 'far_from_median_frames', 'wrap_360_frames')}}
    return out


def run_probe():
    resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 ** 2, 1536 * 1024 ** 2))
    if mem_available() < 2 * 1024 ** 3:
        raise MemoryError('Less than 2 GiB available; not started')
    masses = json.loads(C03.read_text())['readme_masses_kg']
    subjects = sorted(masses)
    order = np.random.default_rng(SEED).permutation(len(subjects))
    rd, records, chosen = Reader(), [], []
    for k in order:
        if len(chosen) == N_SUBJECTS:
            break
        subj = subjects[k]
        needed = [SEG / subj / f'{n}_parsing.mat' for _, tr, segs, _ in CONDITIONS if tr != 'stairs' for n in segs]
        if not all(p.exists() for p in needed) or not list((SEG / subj).glob('stairs_1_*_up_parsing.mat')):
            records.append({'subject': subj, 'skipped': 'segmentation for a condition missing'})
            continue
        chosen.append(subj)
        for label, trial, seg, task in CONDITIONS:
            if mem_available() < 2 * 1024 ** 3:
                raise MemoryError('Less than 2 GiB available; stopped at a condition boundary')
            rec = condition_record(rd, subj, label, trial, seg, task, masses[subj])
            rec['peak_rss_mib_after'] = round(peak_rss_mib(), 1)
            records.append(rec)
            print(f'{subj} {label}: {rec.get("strides", rec.get("skipped"))}, peak RSS {peak_rss_mib():.0f} MiB', flush=True)
            if peak_rss_mib() > RSS_CAP_MIB:
                raise MemoryError(f'peak RSS {peak_rss_mib():.0f} MiB above {RSS_CAP_MIB}; stopped')
    data = {'task_id': 'CORE-04', 'pilot': 'GT23', 'scientific_approval': False, 'applies_to_dataset': 'nothing',
            'target_rule': sod.TARGET_CONVENTION['rule_id'],
            'seed': SEED, 'selection': 'numpy default_rng(seed).permutation over the 12 README subjects; first 3 with '
                                       'segmentation for every condition; all seven conditions each.',
            'subjects': chosen, 'conditions': [c[0] for c in CONDITIONS],
            'readme_masses_kg': {s: masses[s] for s in chosen},
            'mass_source': str(C03.relative_to(ROOT)) + ' readme_masses_kg (publisher README table)',
            'code_sha256': {str(Path(__file__).relative_to(ROOT)): digest(Path(__file__)),
                            'contributor_tools/common/sign_offset_detector.py':
                                digest(ROOT / 'contributor_tools/common/sign_offset_detector.py')},
            'detector_parameters': {k: list(v) if isinstance(v, tuple) else v for k, v in sod.DEFAULTS.items()},
            'files_read': rd.files,
            'resources': {'peak_rss_mib': round(peak_rss_mib(), 1), 'cap_mib': 300,
                          'mode': 'read-only probe exception; one trial at a time; nice 19, ionice idle, 1 thread; RLIMIT_AS 1.5 GiB'},
            'records': records,
            'forward_axis': 'per-stride pelvis facing (horizontal ASIS-mid minus PSIS-mid), foot axis as fallback',
            'previous_probe': {str(PROBE_V1.relative_to(ROOT)): digest(PROBE_V1)} if PROBE_V1.exists() else None}
    PROBE.write_text(json.dumps(data, separators=(',', ':')) + '\n')
    print(json.dumps({'peak_rss_mib': data['resources']['peak_rss_mib'], 'sha256': digest(PROBE), 'subjects': chosen}))


def main():
    os.nice(max(0, 19 - os.nice(0)))
    run_probe()


if __name__ == '__main__':
    main()
