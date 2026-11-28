"""CORE-04 GT21 pilot, PROBE step (read-only data access).

Read-only probe (AGENTS.md exception): one recording at a time from the local Camargo 2021 tree
(contributor_tools/conversion_scripts/Gtech_2021/CAMARGO_ET_AL_J_BIOMECH_DATASET), through the
fail-closed numeric MAT reader (contributor_tools/gt21_numeric_source.py, 64 MiB per file);
nothing written under converted_datasets/ or source folders; peak RSS recorded and capped below
300 MiB; nice 19 / ionice idle; one thread. Writes docs/quality/audits/core04-gt21-pilot-probe.json.

Sources per recording (all on the 200 Hz source clock except fp at 1000 Hz, sampled at the
200 Hz Header times): ik (joint angles, deg; ik_offset is not admitted by the reader, so the
model-zero angles are used: same sign, different offset), id (OpenSim generalized forces, N*m,
not mass-normalized), jp (joint powers, W), gcRight/gcLeft (source HeelStrike percent; a reset to 0
is a heel strike), markers (mm -> m) and fp (N, m). Markers and plates share the OpenSim lab frame,
+Y up (GT21-C01). conditions tables are not admitted by the reader, so the source terrain labels
are not used.

Recordings: per subject and mode a seeded permutation, read one at a time until each class has 10
strides with plate-captured stance per leg or the mode cap (treadmill 1, levelground 8, ramp 12,
stair 12) is reached.

Units: strides between consecutive source heel strikes of one leg (source percent reaching >= 50,
0.6-2.5 s). Each stride is projected on its pelvis facing (horizontal ASIS-mid minus PSIS-mid);
geometry is withheld when the foot heel-to-toe axis disagrees by > 90 deg. Strides turning by
> 20 deg (pelvis facing, start vs end) are excluded. Task per stride from the mode and the pelvis
path: treadmill -> level (treadmill); levelground -> level (overground) when |rise/run| < 0.03;
ramp -> incline (rise/run >= 0.06) or decline (<= -0.06); stair -> ascent (>= 0.20) or descent
(<= -0.20); other strides (transitions) excluded and counted. This is a geometric assignment for
the detector's task context, not a source label.

Plates: treadmill uses the named Treadmill_R / Treadmill_L plates. Overground (levelground, ramp,
stair) assigns a plate sample (vy > 100 N, publisher contact rule) to a foot when its CoP is nearer
that foot's heel-toe midpoint than the other foot's and within 0.30 m; a stride keeps GRF/CoP only
if the assigned contact is one block starting in the first 5% of the stride, lasting 45-80% of it
(a second block running to the stride's last sample, the next stance, is allowed),
and no plate carried the other foot in the same stride; otherwise GRF/CoP are withheld (NaN). The
virtual Combined plate is excluded. Hip point = Thigh_Upper marker (there is no trochanter
marker); the detector's vertical-order guard decides whether marker references are used.

Pelvis: the model heading (ik pelvis_rotation) is about +-90 deg, so ik pelvis_tilt is not
sagittal (GT21-C01). Per recording the circular median heading is recorded; pelvis_tilt is passed
only from recordings with |heading| < 20 deg, otherwise the pelvis is unchecked.

Mass: SubjectInfo.Weight literal as recorded in GT21-S01 (units unresolved there; used only by the
detector's GRF-unit plausibility check and ID-light; every sign decision is scale-free).

Ground truth (rule B, target = sign x source; OpenSim gait2392, GT21-C01 model axes): hip +1,
knee angle -1 (range -120..10 deg, flexion negative), ankle +1, hip moment +1, knee moment -1,
ankle moment +1 (generalized forces along the coordinate), powers +1, pelvis_tilt +1 (about +Z,
counterclockwise in the forward-right view) when sagittal. Applies nothing to any dataset.
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
from contributor_tools.gt21_numeric_source import read_numeric_table  # noqa: E402


def _load_detector():
    """The detector needs only numpy. Importing it as contributor_tools.common.sign_offset_detector runs the
    package __init__ (pandas and segmentation helpers, about 85 MiB), which pushed the first full run over the
    probe's RSS cap; load the same file by path instead (its sha256 is recorded in the output)."""
    import importlib.util
    path = ROOT / 'contributor_tools/common/sign_offset_detector.py'
    spec = importlib.util.spec_from_file_location('core04_sign_offset_detector', path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


sod = _load_detector()

SRC = ROOT / 'contributor_tools/conversion_scripts/Gtech_2021/CAMARGO_ET_AL_J_BIOMECH_DATASET'
AUDITS = ROOT / 'docs/quality/audits'
S01 = AUDITS / 'gt21-s01-cohort-crosswalk.json'
PROBE = AUDITS / 'core04-gt21-pilot-probe.json'
SEED = 20261109
N_SUBJECTS = 6
N_SAMPLES = 150
TARGET_STRIDES = 10
MAX_TRIALS = {'treadmill': 1, 'levelground': 8, 'ramp': 12, 'stair': 12}
FORCE_OK = ('named plate', 'nearest-foot plates')
MODES = ['treadmill', 'levelground', 'ramp', 'stair']
CLASSES = {'treadmill': ['level treadmill'], 'levelground': ['level overground'],
           'ramp': ['incline', 'decline'], 'stair': ['stair ascent', 'stair descent']}
DET_TASK = {'level treadmill': 'level_walking', 'level overground': 'level_walking', 'incline': 'incline_walking',
            'decline': 'decline_walking', 'stair ascent': 'stair_ascent', 'stair descent': 'stair_descent'}
SLOPE = {'level': 0.03, 'ramp': 0.06, 'stair': 0.20}
TURN_DEG = 20.0
SAGITTAL_HEADING_DEG = 20.0
STRIDE_S = (0.6, 2.5)
CONTACT_N = 100.0
NEAR_M = 0.30
RSS_CAP_MIB = 280.0
UP = np.array([0.0, 1.0, 0.0])
TRUTH = {'pelvis_tilt': 1, 'hip_angle': 1, 'knee_angle': -1, 'ankle_angle': 1, 'hip_moment': 1, 'knee_moment': -1,
         'ankle_moment': 1, 'hip_power': 1, 'knee_power': 1, 'ankle_power': 1}
JOINT_CHANNELS = [k for k in TRUTH if k != 'pelvis_tilt']
COP_REGISTRATION = ('none: plate CoP and markers are both in the OpenSim lab frame (GT21-C01); no shift applied; '
                    'tested by the detector CoP-within-foot check')


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def peak_rss_mib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def mem_available():
    line = next(s for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:'))
    return int(line.split()[1]) * 1024


def release_memory():
    """Return freed heap to the OS between tables (keeps later peaks from stacking on fragments)."""
    import ctypes
    import gc
    gc.collect()
    try:
        ctypes.CDLL('libc.so.6').malloc_trim(0)
    except OSError:
        pass


class Reader:
    """Bounded reads (reader admission 64 MiB) with size/mtime checked before and after."""
    def __init__(self):
        self.files = []

    def table(self, path):
        st = Path(path).stat()
        out = read_numeric_table(path)
        st2 = Path(path).stat()
        if (st.st_size, st.st_mtime_ns) != (st2.st_size, st2.st_mtime_ns):
            raise ValueError(f'{path} changed during the read')
        self.files.append({'path': str(Path(path).relative_to(ROOT)), 'bytes': st.st_size, 'mtime_ns': st.st_mtime_ns})
        release_memory()
        return out


def masses():
    d = json.loads(S01.read_text())
    out = {}
    for p in d['participants']:
        w = (p.get('metadata') or {}).get('Weight_literal')
        if w is not None:
            out[p['subject']] = float(w)
    return out


def subjects_with_modes():
    out = {}
    for sd in sorted(p for p in SRC.iterdir() if re.fullmatch(r'AB\d+', p.name)):
        dates = [d for d in sd.iterdir() if d.is_dir() and d.name != 'osimxml']
        if len(dates) != 1:
            continue
        if all((dates[0] / m / 'ik').is_dir() for m in MODES):
            out[sd.name] = dates[0]
    return out


def resample(seg):
    seg = np.asarray(seg, float)
    src = np.arange(seg.shape[0])
    grid = np.linspace(0, seg.shape[0] - 1, N_SAMPLES)
    if seg.ndim == 1:
        return np.interp(grid, src, seg)
    return np.stack([np.interp(grid, src, seg[:, k]) for k in range(seg.shape[1])], -1)


def horiz_unit(v):
    v = np.asarray(v, float) - (np.asarray(v, float) @ UP) * UP
    n = np.linalg.norm(v)
    return v / n if np.isfinite(n) and n > 0 else None


def signed_deg(a, b):
    return float(np.degrees(np.arctan2(np.cross(a, b) @ UP, a @ b)))


def circular_median_deg(x_deg):
    x = np.radians(np.asarray(x_deg, float))
    x = x[np.isfinite(x)]
    m = np.arctan2(np.median(np.sin(x)), np.median(np.cos(x)))
    return float(np.degrees(m))


def marker(mk, name):
    cols = [f'{name}_{a}' for a in 'xyz']
    if not all(c in mk for c in cols):
        return None
    p = np.stack([mk[c] for c in cols], -1) / 1000.0
    p[~np.isfinite(p).all(axis=1) | (np.abs(p).sum(axis=1) == 0)] = np.nan  # zeros = gap, not a position
    return p


def plate_names(fp):
    names = sorted({c.rsplit('_', 1)[0] for c in fp if c.endswith('_vy')})
    return [n for n in names if not n.startswith('Combined')]


def read_recording(rd, date_dir, mode, trial):
    """One recording; each table is reduced to the needed columns and released before the next read."""
    get = lambda mod: rd.table(date_dir / mode / mod / trial)

    def same_clock(name, h):
        if len(h) != len(t) or np.max(np.abs(h - t)) > 1e-6:
            raise ValueError(f'{trial}: {name} clock differs from ik')

    ik = get('ik')
    t = ik['Header']
    ang = {s: {'hip_angle': np.radians(ik[f'hip_flexion_{s}']), 'knee_angle': np.radians(ik[f'knee_angle_{s}']),
               'ankle_angle': np.radians(ik[f'ankle_angle_{s}'])} for s in 'rl'}
    pelvis_tilt, heading = np.radians(ik['pelvis_tilt']), ik['pelvis_rotation']
    ik = None
    idt = get('id')
    same_clock('id', idt['Header'])
    mom = {s: {'hip_moment': idt[f'hip_flexion_{s}_moment'], 'knee_moment': idt[f'knee_angle_{s}_moment'],
               'ankle_moment': idt[f'ankle_angle_{s}_moment']} for s in 'rl'}
    idt = None
    jp = get('jp')
    same_clock('jp', jp['Header'])
    pw = {s: {'hip_power': jp[f'hip_flexion_{s}_power'], 'knee_power': jp[f'knee_angle_{s}_power'],
              'ankle_power': jp[f'ankle_angle_{s}_power']} for s in 'rl'}
    jp = None
    hs = {}
    for side, mod in (('right', 'gcRight'), ('left', 'gcLeft')):
        g = get(mod)
        same_clock(mod, g['Header'])
        hs[side] = g['HeelStrike']
        g = None
    mk = get('markers')
    same_clock('markers', mk['Header'])
    pts = {}
    for side, S in (('right', 'R'), ('left', 'L')):
        pts[side] = {'heel': marker(mk, f'{S}_Heel'), 'toe': marker(mk, f'{S}_Toe_Tip'),
                     'ankle': marker(mk, f'{S}_Ankle_Lat'), 'knee': marker(mk, f'{S}_Knee_Lat'),
                     'hip': marker(mk, f'{S}_Thigh_Upper')}
    asis = [marker(mk, 'L_ASIS'), marker(mk, 'R_ASIS')]
    psis = [marker(mk, 'L_PSIS'), marker(mk, 'R_PSIS')]
    mk = None
    front = (asis[0] + asis[1]) / 2 if all(a is not None for a in asis) else None
    rear = (psis[0] + psis[1]) / 2 if all(a is not None for a in psis) else None
    fp = get('fp')
    j = np.clip(np.searchsorted(fp['Header'], t - 1e-7), 0, len(fp['Header']) - 1)
    if np.max(np.abs(fp['Header'][j] - t)) > 1e-6:
        raise ValueError(f'{trial}: fp clock does not contain the 200 Hz samples')
    plates = {}
    for n in plate_names(fp):
        plates[n] = (np.stack([fp[f'{n}_v{a}'][j] for a in 'xyz'], -1),
                     np.stack([fp[f'{n}_p{a}'][j] for a in 'xyz'], -1))
    fp = None
    ch = {side: {**ang[s], **mom[s], **pw[s], 'pelvis_tilt': pelvis_tilt} for side, s in (('right', 'r'), ('left', 'l'))}
    return {'t': t, 'ch': ch, 'pts': pts, 'front': front, 'rear': rear, 'plates': plates, 'hs': hs,
            'heading_deg': {'circular_median': round(circular_median_deg(heading), 1),
                            'q05_q95': [round(float(np.nanpercentile(heading, 5)), 1),
                                        round(float(np.nanpercentile(heading, 95)), 1)]}}


def foot_mid(p):
    if p['heel'] is None or p['toe'] is None:
        return None
    return (p['heel'] + p['toe']) / 2


def ipsi_force(rec, side, mode, a, b):
    """(force, cop, status) for samples a..b of one leg; NaN arrays when withheld."""
    n = b - a + 1
    nan = (np.full((n, 3), np.nan), np.full((n, 3), np.nan))
    other = 'left' if side == 'right' else 'right'
    if mode == 'treadmill':
        name = 'Treadmill_R' if side == 'right' else 'Treadmill_L'
        if name not in rec['plates']:
            return (*nan, 'named treadmill plate missing')
        f, c = rec['plates'][name]
        f, c = f[a:b + 1].copy(), c[a:b + 1].copy()
        on = f[:, 1] > CONTACT_N
        c[~on] = np.nan
        status = 'named plate'
    else:
        mi, mo = foot_mid(rec['pts'][side]), foot_mid(rec['pts'][other])
        if mi is None or mo is None:
            return (*nan, 'foot markers missing')
        mi, mo = mi[a:b + 1], mo[a:b + 1]
        F, M, on = np.zeros((n, 3)), np.zeros((n, 3)), np.zeros(n, bool)
        for name, (f, c) in rec['plates'].items():
            f, c = f[a:b + 1], c[a:b + 1]
            con = f[:, 1] > CONTACT_N
            hd = lambda p: np.linalg.norm((c - p) - np.outer((c - p) @ UP, UP), axis=1)
            di, do = hd(mi), hd(mo)
            mine = con & (di < do) & (di < NEAR_M)
            theirs = con & ~mine
            if mine.any() and theirs.any():
                return (*nan, 'a plate carried both feet in this stride')
            F[mine] += f[mine]
            M[mine] += f[mine][:, [1]] * c[mine]
            on |= mine
        f = F
        c = np.full((n, 3), np.nan)
        c[on] = M[on] / F[on][:, [1]]
        status = 'nearest-foot plates'
    idx = np.flatnonzero(on)
    if not len(idx):
        return (*nan, 'no plate contact')
    # Stance = the first contact block (gaps <= 3 samples). A later block is allowed only if it runs
    # to the stride's last sample: the next stance (on stairs it starts before the source heel strike).
    blocks = np.split(idx, np.flatnonzero(np.diff(idx) > 3) + 1)
    body = blocks[0]
    tail_ok = len(blocks) == 1 or (len(blocks) == 2 and blocks[1][-1] == n - 1)
    if body[0] > 0.05 * n or not tail_ok or not 0.45 <= len(body) / n <= 0.80:
        return (*nan, 'stance not captured as one block (start <= 5%, 45-80% of stride)')
    f = f.copy()
    f[~on] = 0.0
    return f, c, status


def stride_list(rec, side):
    hs = np.asarray(rec['hs'][side], float)
    resets = np.flatnonzero((hs[1:] == 0) & (hs[:-1] > 0)) + 1
    out = []
    for a, b in zip(resets[:-1], resets[1:]):
        dur = float(rec['t'][b] - rec['t'][a])
        if np.nanmax(hs[a:b]) >= 50 and STRIDE_S[0] <= dur <= STRIDE_S[1]:
            out.append((int(a), int(b), dur))
    return out, max(len(resets) - 1, 0)


def classify(rec, mode, a, b):
    if rec['front'] is None or rec['rear'] is None:
        return None, 'pelvis markers missing', None
    pel = (rec['front'] + rec['rear']) / 2
    f0 = horiz_unit(np.nanmedian((rec['front'] - rec['rear'])[a:a + 10], 0))
    f1 = horiz_unit(np.nanmedian((rec['front'] - rec['rear'])[b - 9:b + 1], 0))
    if f0 is None or f1 is None:
        return None, 'pelvis facing missing', None
    turn = signed_deg(f0, f1)
    if abs(turn) > TURN_DEG:
        return None, 'turning', None
    d = np.nanmedian(pel[b - 4:b + 1], 0) - np.nanmedian(pel[a:a + 5], 0)
    run = np.linalg.norm(d - (d @ UP) * UP)
    rise = float(d @ UP)
    if mode == 'treadmill':
        return 'level treadmill', None, None
    if not np.isfinite(run) or run < 0.3:
        return None, 'no progression', None
    slope = rise / run
    if mode == 'levelground':
        return ('level overground', None, slope) if abs(slope) < SLOPE['level'] else (None, 'not level', slope)
    lim = SLOPE[mode]
    if slope >= lim:
        return ('incline' if mode == 'ramp' else 'stair ascent'), None, slope
    if slope <= -lim:
        return ('decline' if mode == 'ramp' else 'stair descent'), None, slope
    return None, 'transition (slope between thresholds)', slope


def process_recording(rec, mode, trial, buckets, tally):
    sag_pelvis = abs(rec['heading_deg']['circular_median']) < SAGITTAL_HEADING_DEG
    for side in ('right', 'left'):
        strides, n_raw = stride_list(rec, side)
        tally[(side, 'source_stride_pairs')] += n_raw
        tally[(side, 'duration_or_percent_excluded')] += n_raw - len(strides)
        for a, b, dur in strides:
            cls, why, slope = classify(rec, mode, a, b)
            if cls is None:
                tally[(side, why)] += 1
                continue
            axis = horiz_unit(np.nanmedian((rec['front'] - rec['rear'])[a:b + 1], 0))
            p = rec['pts'][side]
            agree = None
            if p['heel'] is not None and p['toe'] is not None:
                foot = horiz_unit(np.nanmedian((p['toe'] - p['heel'])[a:b + 1], 0))
                if foot is not None:
                    agree = abs(signed_deg(foot, axis)) < 90.0
            withhold = agree is False
            sag = lambda v: (np.full((b - a + 1, 2), np.nan) if (withhold or v is None)
                             else sod.project_sagittal(v[a:b + 1], axis, UP))
            f, c, fstat = ipsi_force(rec, side, mode, a, b)
            u = {k: resample(rec['ch'][side][k][a:b + 1]) for k in JOINT_CHANNELS}
            u['pelvis_tilt'] = resample(rec['ch'][side]['pelvis_tilt'][a:b + 1]) if sag_pelvis else None
            for k in ('heel', 'toe', 'ankle', 'knee', 'hip'):
                u['pt_' + k] = resample(sag(p[k]))
            u['pt_pelvis_front'] = resample(sag(rec['front']))
            u['pt_pelvis_rear'] = resample(sag(rec['rear']))
            sag_local = lambda v: (np.full((b - a + 1, 2), np.nan) if withhold  # f, c are already a..b
                                   else sod.project_sagittal(v, axis, UP))
            u['grf'] = resample(sag_local(f))
            u['cop'] = resample(sag_local(c))
            u['duration'] = dur
            u['slope'] = slope
            u['force_status'] = fstat if not withhold else 'geometry withheld (foot axis > 90 deg from pelvis facing)'
            u['axis_agree'] = agree
            u['source'] = trial
            buckets[(cls, side)].append(u)
            tally[(side, 'kept_' + cls)] += 1


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


def leg_record(subject, cls, side, units, mass):
    if len(units) < sod.DEFAULTS['min_units']:
        return {'subject': subject, 'condition': cls, 'side': side, 'strides': len(units),
                'skipped': f'fewer than {sod.DEFAULTS["min_units"]} strides'}
    stack = lambda k: np.array([u[k] for u in units])
    chans = {k: stack(k) for k in JOINT_CHANNELS}
    pelvis_units = [u for u in units if u['pelvis_tilt'] is not None]
    pelvis_note = 'unchecked: no recording with |model heading| < 20 deg (ik pelvis_tilt not sagittal)'
    if len(pelvis_units) == len(units):
        chans['pelvis_tilt'] = stack('pelvis_tilt')
        pelvis_note = 'passed: every recording sagittal'
    elif pelvis_units:
        pelvis_note = f'unchecked: only {len(pelvis_units)}/{len(units)} strides from sagittal recordings'
    pts = {k: stack('pt_' + k) for k in ('heel', 'toe', 'ankle', 'knee', 'hip', 'pelvis_front', 'pelvis_rear')}
    rep = sod.detect_leg(f'GT21 {subject} {cls}', side, chans, marker_points=pts, cop=stack('cop'),
                         grf=stack('grf'), task=DET_TASK[cls], grf_unit='N', body_mass_kg=mass,
                         cop_registration=COP_REGISTRATION, unit_durations_s=stack('duration'))
    fs = collections.Counter(u['force_status'] for u in units)
    slopes = [u['slope'] for u in units if u['slope'] is not None]
    return {'subject': subject, 'condition': cls, 'task': DET_TASK[cls], 'side': side, 'strides': len(units),
            'sources': sorted(collections.Counter(u['source'] for u in units).items()),
            'body_mass_literal': mass, 'force_status_strides': dict(fs),
            'axis_agreement_strides': dict(collections.Counter(
                'within_90' if u['axis_agree'] else ('beyond_90' if u['axis_agree'] is False else 'not_checked')
                for u in units)),
            'slope_median_q05_q95': [round(float(np.median(slopes)), 3), round(float(np.percentile(slopes, 5)), 3),
                                     round(float(np.percentile(slopes, 95)), 3)] if slopes else None,
            'pelvis': pelvis_note,
            'marker_checks': rep['marker_checks'], 'plate_frame_check': rep['plate_frame_check'],
            'grf_unit_check': rep['grf_unit_check'], 'leg_assignment_check': rep['leg_assignment_check'],
            'relations': [{x: r[x] for x in ('test', 'channels', 'product', 'reason', 'units_voting', 'units_agreeing')}
                          for r in rep['relations']],
            'channels': summarize(rep)}


def run_probe(n_subjects, out=PROBE):
    resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 ** 2, 1536 * 1024 ** 2))
    if mem_available() < 2 * 1024 ** 3:
        raise MemoryError('Less than 2 GiB available; not started')
    mass = masses()
    avail = subjects_with_modes()
    subjects = sorted(s for s in avail if s in mass)
    rng = np.random.default_rng(SEED)
    order = [subjects[k] for k in rng.permutation(len(subjects))]
    chosen = order[:n_subjects]
    rd, records, recordings = Reader(), [], []
    tallies = {}
    for subj in chosen:
        tally = collections.Counter()
        buckets = collections.defaultdict(list)
        for mode in MODES:
            trials = sorted(p.name for p in (avail[subj] / mode / 'ik').glob('*.mat'))
            trials = [trials[k] for k in rng.permutation(len(trials))]
            used = 0
            for trial in trials:
                if used >= MAX_TRIALS[mode]:
                    break
                if all(sum(u['force_status'] in FORCE_OK for u in buckets[(c, s)]) >= TARGET_STRIDES
                       for c in CLASSES[mode] for s in ('right', 'left')):
                    break
                if mem_available() < 2 * 1024 ** 3:
                    raise MemoryError('Less than 2 GiB available; stopped at a recording boundary')
                rel = f'{subj}/{avail[subj].name}/{mode}/{trial}'
                try:
                    rec = read_recording(rd, avail[subj], mode, trial)
                except (ValueError, MemoryError, KeyError) as e:
                    recordings.append({'recording': rel, 'rejected': f'{type(e).__name__}: {e}'})
                    used += 1
                    continue
                process_recording(rec, mode, trial, buckets, tally)
                recordings.append({'recording': rel, 'model_heading_deg': rec['heading_deg'],
                                   'pelvis_sagittal': abs(rec['heading_deg']['circular_median']) < SAGITTAL_HEADING_DEG,
                                   'peak_rss_mib_after': round(peak_rss_mib(), 1)})
                rec = None
                release_memory()
                used += 1
                print(f'{rel}: peak RSS {peak_rss_mib():.0f} MiB', flush=True)
                if peak_rss_mib() > RSS_CAP_MIB:
                    raise MemoryError(f'peak RSS {peak_rss_mib():.0f} MiB above {RSS_CAP_MIB}; stopped')
        tallies[subj] = {f'{s}: {k}': v for (s, k), v in sorted(tally.items())}
        for mode in MODES:
            for cls in CLASSES[mode]:
                for side in ('right', 'left'):
                    r = leg_record(subj, cls, side, buckets[(cls, side)], mass[subj])
                    records.append(r)
                    print(f'{subj} {cls} {side}: {r.get("strides")} strides {r.get("skipped", "")}', flush=True)
        buckets = None
    data = {'task_id': 'CORE-04', 'pilot': 'GT21', 'scientific_approval': False, 'applies_to_dataset': 'nothing',
            'target_rule': sod.TARGET_CONVENTION['rule_id'], 'seed': SEED,
            'selection': ('numpy default_rng(seed): permutation over local subjects with all four modes and a '
                          'GT21-S01 Weight literal, first N; then per subject and mode a permutation of recordings, '
                          f'read in order until every class has {TARGET_STRIDES} strides with plate-captured stance per leg or the mode cap '
                          f'{MAX_TRIALS} is reached'),
            'subjects': chosen, 'eligible_subjects': subjects, 'classes': CLASSES,
            'body_mass_literal': {s: mass[s] for s in chosen},
            'mass_source': str(S01.relative_to(ROOT)) + ' participants[].metadata.Weight_literal (units unresolved)',
            'truth': TRUTH, 'code_sha256': {str(Path(__file__).relative_to(ROOT)): digest(Path(__file__)),
                                            'contributor_tools/common/sign_offset_detector.py':
                                                digest(ROOT / 'contributor_tools/common/sign_offset_detector.py'),
                                            'contributor_tools/gt21_numeric_source.py':
                                                digest(ROOT / 'contributor_tools/gt21_numeric_source.py')},
            'detector_parameters': {k: list(v) if isinstance(v, tuple) else v for k, v in sod.DEFAULTS.items()},
            'adapter_parameters': {'slope': SLOPE, 'turn_deg': TURN_DEG, 'sagittal_heading_deg': SAGITTAL_HEADING_DEG,
                                   'stride_s': STRIDE_S, 'contact_N': CONTACT_N, 'near_m': NEAR_M,
                                   'target_strides': TARGET_STRIDES, 'max_trials': MAX_TRIALS},
            'recordings': recordings, 'stride_tallies': tallies, 'files_read': rd.files,
            'resources': {'peak_rss_mib': round(peak_rss_mib(), 1), 'cap_mib': 300,
                          'mode': 'read-only probe exception; one recording at a time; nice 19, ionice idle, 1 thread; RLIMIT_AS 1.5 GiB'},
            'records': records}
    out = Path(out)
    out.write_text(json.dumps(data, separators=(',', ':')) + '\n')
    print(json.dumps({'peak_rss_mib': data['resources']['peak_rss_mib'], 'sha256': digest(out), 'subjects': chosen}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--subjects', type=int, default=N_SUBJECTS)
    ap.add_argument('--out', default=str(PROBE), help='pilot runs write outside the repository')
    args = ap.parse_args()
    os.nice(max(0, 19 - os.nice(0)))
    run_probe(args.subjects, args.out)


if __name__ == '__main__':
    main()
