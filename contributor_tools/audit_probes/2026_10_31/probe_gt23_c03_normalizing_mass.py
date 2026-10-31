"""GT23-C03: which mass did the GT23 authors divide each subject's joint moments by?

Read-only probe (AGENTS.md probe exception): one trial at a time, nothing written under
converted_datasets/ or the source folder, single-threaded, nice 19 / ionice idle (set by the caller),
peak RSS recorded and required below 300 MiB.

Steps, run one at a time and in this order:
  reference  Inventory every subject's OpenSim models (mass, joint geometry, publisher CRC), draw the
             seeded trial sample for all 12 subjects, analyse only the REFERENCE subjects, and fix the
             tolerance from them. Writes docs/quality/audits/gt23-c03-normalizing-mass.json (stage
             "reference"). The test subjects' data are not read in this step.
  test       Reads the fixed tolerance from that JSON (it is not recomputed), analyses the TEST subjects
             (AB03, AB05, AB08, AB10: the four named by GT23-C02 findings) plus targeted trials, and flags
             trials and subjects against the tolerance. Updates the JSON (stage "final").
  sheet      Builds review_sheets/D-GT23-C03-1/ from the JSON only.

Method (no mass enters any N*m estimate):
  Publisher Virtual_Insoles.csv give the measured GRF and CoP in each calcn frame (C02: force norm equals
  GroundFrame_GRFs). For each sample the joint centres and axes are placed in that calcn frame from the
  trial's own scaled model (Statics.csv -> <subj>-Scaled<n>.osim):
      ankle centre  p_a = R_sub^T (0 - s)                 s = subtalar location_in_parent (talus frame)
      knee centre   p_k = R_sub^T (R_ank^T (0 - L) - s)   L = ankle location_in_parent (tibia frame)
      ankle axis    n_a = R_sub^T a_ank;  knee axis n_k = R_sub^T R_ank^T z
  with R_ank, R_sub rotations about the model's ankle and subtalar axes by the trial's Joint_Angle values.
  The CoP is placed at calcn y = 0 (sensitivity: y = -0.03 m). Quasi-static internal moment (N*m):
      est_j = -n_j . ((CoP - p_j) x F)       (ignores foot/shank weight and inertia, knee spline translation)
  Source column (N*m/kg) is regressed on est_j through the origin in a stance window
  (ankle 40-90 %, knee 20-90 % of stance); implied normalizing mass = 1 / slope.
  Stance: insole vertical force > 100 N for 0.25-2.5 s, not at a file edge, all inputs finite.

Tolerance (rule fixed in code before any test-subject data are read):
  reference subjects = the 8 subjects not named in GT23-C02 findings; per-trial log ratio
  q = log(implied / README mass) over their seeded trials (ankle); centre c = median(q);
  robust s = 1.4826 * median|q - c|; band |q - c| <= max(3 s, log 1.10).
  A trial is flagged when its ankle ratio is outside the band; a subject when the median of its
  trial ratios is. The same rule is applied separately to the knee and to the local N*m re-run.

Local N*m re-run: RawData/<subj>/MotionFile_EH/inverse_dynamics.sto is NOT in the publisher archive
(raw_zip_directory.json); its provenance is unknown. It is used only as corroboration: its sagittal
moments (N*m) regressed on the matching trial's published moments give a second divisor estimate.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import re
import resource
import sys
import xml.etree.ElementTree as ET
import zlib

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

RAW = Path('/mnt/s/locomotion_data/Gtech_2023/RawData')
PUB = ROOT / 'converted_datasets/reconversion_v2/swarm_backlog_20261021/gt23_publisher_source_review_20261021'
PUB_MASSES = PUB / 'verified_members/Subject_masses.csv'
ZIP_DIR = PUB / 'raw_zip_directory.json'
AUDIT = ROOT / 'docs/quality/audits/gt23-c03-normalizing-mass.json'
SHEET = ROOT / 'review_sheets/D-GT23-C03-1'
SEED = 20261031
K_PER_SUBJECT = 4
REFERENCE = ['AB01', 'AB02', 'AB06', 'AB07', 'AB09', 'AB11', 'AB12', 'AB13']
TEST = ['AB03', 'AB05', 'AB08', 'AB10']
# Targeted (not random): the trials named in GT23-C02 / its verification, plus the other incline
# trial of AB05 so a per-trial anomaly can be told from a per-subject one.
TARGETED = [('AB05', 'incline_walk_2'), ('AB05', 'incline_walk_1'), ('AB03', 'weighted_walk_1'),
            ('AB10', 'incline_walk_1'), ('AB08', 'weighted_walk_1')]
FAMILIES = ['normal_walk', 'incline_walk', 'weighted_walk', 'dynamic_walk', 'obstacle_walk', 'walk_backward',
            'stairs', 'curb_up', 'curb_down', 'meander', 'turn_and_step', 'side_shuffle', 'cutting', 'tire_run']
PLATE_MASS_FAMILIES = {'normal_walk', 'incline_walk', 'weighted_walk', 'walk_backward', 'dynamic_walk'}
VEST_KG = 25 * 0.45359237      # weighted_walk_1_25lbs
G = 9.81
RATE_HZ = 200.0
STANCE_N = 100.0
MIN_STANCES = 4
WINDOWS = {'ankle': (0.40, 0.90), 'knee': (0.20, 0.90)}
COP_Y = 0.0
COP_Y_SENS = -0.03
BAND_FLOOR = float(np.log(1.10))
RSS_LIMIT_MIB = 300
COLS = {'ankle': 'ankle_angle_{s}_moment', 'knee': 'knee_angle_{s}_moment'}


def utc():
    return dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def peak_rss_mib():
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)


def family(task):
    return re.sub(r'(_\d+)+$', '', task)


def masses(path):
    out = {}
    for line in Path(path).read_text().splitlines():
        parts = line.strip().split(',')
        if len(parts) == 2 and parts[0].startswith('AB'):
            out[parts[0]] = float(parts[1])
    return out


class Reader:
    """Reads whole source files (a few MB), hashes them and checks size+CRC32 against the publisher zip directory."""

    def __init__(self, zipdir):
        self.zipdir = zipdir
        self.files = []

    def raw(self, path):
        b = Path(path).read_bytes()
        name = str(Path(path).relative_to(RAW))
        e = self.zipdir.get(name)
        self.files.append({'path': str(path), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(),
                           'publisher_crc32_match': (e is not None and zlib.crc32(b) == e['crc32'] and len(b) == e['uncompressed_size'])
                           if e else None})
        return b

    def table(self, path, **kw):
        import pandas as pd
        b = self.raw(path)
        df = pd.read_csv(io.BytesIO(b), **kw)
        del b
        return df


# ---------------------------------------------------------------- models

def vec(e):
    return np.array([float(v) for v in e.text.split()])


def parse_model(path, reader):
    root = ET.fromstring(reader.raw(path))
    bodies = {b.get('name'): b for b in root.find('Model/BodySet/objects').findall('Body')}
    out = {'file': path.name, 'mass_kg': round(sum(float(b.find('mass').text) for b in bodies.values()), 3)}
    for s in 'rl':
        geo = {}
        for body, jn in [('tibia_' + s, 'knee_' + s), ('talus_' + s, 'ankle_' + s), ('calcn_' + s, 'subtalar_' + s)]:
            jset = bodies[body].find('Joint')
            j = [x for x in (jset if jset is not None else []) if x.get('name') == jn]
            if not j:
                return None
            j = j[0]
            for tag in ('orientation_in_parent', 'orientation', 'location'):
                if np.any(vec(j.find(tag)) != 0):
                    raise ValueError(f'{path} {jn} {tag} non-zero; frame algebra assumes zero')
            ax = [t for t in j.find('SpatialTransform').findall('TransformAxis') if t.get('name') == 'rotation1'][0]
            geo[jn.split('_')[0]] = {'location_in_parent': vec(j.find('location_in_parent')).tolist(),
                                     'rotation1_axis': vec(ax.find('axis')).tolist(),
                                     'rotation1_coordinate': (ax.find('coordinates').text or '').strip()}
        out[s] = geo
    return out


def inventory(reader):
    inv = {}
    for subj_dir in sorted(RAW.glob('AB*')):
        subj = subj_dir.name
        models = {}
        for p in sorted((subj_dir / 'Models').glob('*.osim')):
            m = parse_model(p, reader)
            models[p.name] = m if m else {'file': p.name, 'parse': 'no CustomJoint chain (2-D variant), not used'}
        statics = {}
        for line in reader.raw(subj_dir / 'Models/Statics.csv').decode().splitlines()[1:]:
            t, n = line.strip().split(',')
            statics[t] = int(n)
        inv[subj] = {'models': models, 'statics': statics}
    return inv


def model_for(inv, subj, task):
    n = inv[subj]['statics'].get(task)
    if n is None:
        return None, 'task not in Statics.csv'
    name = f'{subj}-Scaled{n}.osim'
    if name in inv[subj]['models']:
        return name, 'Statics.csv'
    alt = f'{subj}-Scaled{n}_original.osim'     # AB01: local copy renamed; its CRC equals publisher AB01-Scaled1.osim
    if alt in inv[subj]['models']:
        return alt, 'Statics.csv; local file renamed _original, bytes equal the publisher model by CRC32'
    return None, f'{name} missing'


# ---------------------------------------------------------------- geometry

def rot(axis, ang):
    """Rodrigues rotation matrices, shape (n, 3, 3), axis (3,), ang (n,) rad."""
    a = np.asarray(axis, float) / np.linalg.norm(axis)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    ang = np.asarray(ang, float)[:, None, None]
    return np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * (K @ K)


def joint_frames(geo, q_ank_deg, q_sub_deg):
    """Ankle/knee centres and axes in the calcn frame for each sample."""
    L = np.array(geo['ankle']['location_in_parent'])
    s = np.array(geo['subtalar']['location_in_parent'])
    Ra = rot(geo['ankle']['rotation1_axis'], np.deg2rad(q_ank_deg))
    Rs = rot(geo['subtalar']['rotation1_axis'], np.deg2rad(q_sub_deg))
    RsT, RaT = np.transpose(Rs, (0, 2, 1)), np.transpose(Ra, (0, 2, 1))
    p_a = RsT @ (-s)
    p_k = np.einsum('nij,nj->ni', RsT, np.einsum('nij,j->ni', RaT, -L) - s)
    n_a = RsT @ np.asarray(geo['ankle']['rotation1_axis'], float)
    n_k = np.einsum('nij,nj->ni', RsT, RaT @ np.array([0.0, 0.0, 1.0]))
    return {'ankle': (p_a, n_a / np.linalg.norm(n_a, axis=1, keepdims=True)),
            'knee': (p_k, n_k / np.linalg.norm(n_k, axis=1, keepdims=True))}


def estimate(p, n, cop_ap, fv, fap, cop_y):
    """-n . ((CoP - p) x F) with sagittal loads only: the insole ML force and CoP are not used (their
    sign convention is not established), so r and F lie in the calcn x-y plane and only n_z contributes."""
    rx, ry = cop_ap - p[:, 0], cop_y - p[:, 1]
    return -n[:, 2] * (rx * fv - ry * fap)


# ---------------------------------------------------------------- trial analysis

def stances(fv, n):
    on = np.nan_to_num(fv) > STANCE_N
    edges = np.flatnonzero(np.diff(on.astype(int)))
    return [(a + 1, b + 1) for a, b in zip(edges[:-1], edges[1:])
            if on[a + 1] and 0.25 * RATE_HZ <= b - a <= 2.5 * RATE_HZ and a > 0 and b < n - 2]


def fit(src, est):
    slope = float(src @ est / (est @ est))
    return slope, float(np.corrcoef(src, est)[0, 1])


def analyse_trial(reader, inv, pub, subj, task, origin):
    d = RAW / subj / 'CSV_Data' / task
    names = ('Joint_Moments.csv', 'Virtual_Insoles.csv', 'Joint_Angle.csv', 'GroundFrame_GRFs.csv')
    st = {p: (d / p).stat().st_mtime_ns for p in names}
    mom, ins, ang, grf = (reader.table(d / p) for p in names)
    if any((d / p).stat().st_mtime_ns != st[p] for p in names):
        raise ValueError('Source changed during the read')
    dt_max = max(float(np.max(np.abs(mom.time.to_numpy() - x.time.to_numpy()))) for x in (ins, ang, grf)) \
        if len(mom) == len(ins) == len(ang) == len(grf) else None
    if dt_max is None or dt_max > 1e-6:
        return {'subject': subj, 'task': task, 'origin': origin, 'usable': False, 'reason': f'time bases differ (rows/dt {dt_max})'}
    mname, msrc = model_for(inv, subj, task)
    if mname is None:
        return {'subject': subj, 'task': task, 'origin': origin, 'usable': False, 'reason': msrc}
    model = inv[subj]['models'][mname]
    out = {'subject': subj, 'task': task, 'family': family(task), 'origin': origin, 'model': mname, 'model_source': msrc,
           'model_mass_kg': model['mass_kg'], 'readme_mass_kg': pub[subj], 'sides': []}
    pooled = {j: ([], [], []) for j in WINDOWS}      # src, est, est_sens
    for s in 'rl':
        S = s.upper()
        fv, fap, cop = (ins[f'{S}{k}'].to_numpy(float) for k in ('VerticalF', 'ShearF_AP', 'COP_AP'))
        qa, qs = ang[f'ankle_angle_{s}'].to_numpy(float), ang[f'subtalar_angle_{s}'].to_numpy(float)
        srcs = {j: mom[COLS[j].format(s=s)].to_numpy(float) for j in WINDOWS}
        ok = np.isfinite(fv) & np.isfinite(fap) & np.isfinite(cop) & np.isfinite(qa) & np.isfinite(qs) \
            & np.isfinite(srcs['ankle']) & np.isfinite(srcs['knee'])
        runs = [r for r in stances(fv, len(fv)) if ok[r[0]:r[1]].all()]
        side = {'side': s, 'stances': len(runs)}
        if family(task) in PLATE_MASS_FAMILIES and len(runs) >= MIN_STANCES:
            fvp = np.nan_to_num(grf[f'{S}ForceY_Vertical'].to_numpy(float))
            hs = [a for a, _ in runs]
            per = [2 * float(np.mean(fvp[a:b])) / G for a, b in zip(hs[:-1], hs[1:]) if b - a < 3 * RATE_HZ]
            if per:
                side['force_plate_mass_kg'] = round(float(np.median(per)) - (VEST_KG if family(task) == 'weighted_walk' else 0), 2)
        for j, (lo, hi) in WINDOWS.items():
            per_stance = []
            for a, b in runs:
                i = np.arange(a + int(round(lo * (b - a))), a + int(round(hi * (b - a))))
                fr = joint_frames(model[s], qa[i], qs[i])
                p, n = fr[j]
                e = estimate(p, n, cop[i], fv[i], fap[i], COP_Y)
                e2 = estimate(p, n, cop[i], fv[i], fap[i], COP_Y_SENS)
                pooled[j][0].append(srcs[j][i]); pooled[j][1].append(e); pooled[j][2].append(e2)
                sl, _ = fit(srcs[j][i], e)
                per_stance.append(1 / sl if sl > 0 else np.nan)
            if per_stance:
                v = np.array(per_stance)
                side[j] = {'per_stance_implied_kg_median': round(float(np.nanmedian(v)), 2),
                           'per_stance_implied_kg_iqr': [round(float(np.nanpercentile(v, 25)), 2), round(float(np.nanpercentile(v, 75)), 2)],
                           'negative_slope_stances': int(np.sum(~np.isfinite(v)))}
        if runs:
            fr = joint_frames(model[s], qa[runs[0][0]:runs[0][0] + 1], qs[runs[0][0]:runs[0][0] + 1])
            side['first_stance_ankle_centre_calcn_m'] = np.round(fr['ankle'][0][0], 4).tolist()
            side['first_stance_knee_centre_calcn_m'] = np.round(fr['knee'][0][0], 4).tolist()
        out['sides'].append(side)
    n_st = sum(x['stances'] for x in out['sides'])
    out['stances_total'] = n_st
    out['usable'] = n_st >= MIN_STANCES
    if not out['usable']:
        out['reason'] = f'fewer than {MIN_STANCES} valid stances'
        return out
    for j in WINDOWS:
        src, est, est2 = (np.concatenate(x) for x in pooled[j])
        sl, r = fit(src, est)
        sl2, _ = fit(src, est2)
        out[j] = {'implied_mass_kg': round(1 / sl, 2) if sl > 0 else None, 'slope': round(sl, 6), 'corr': round(r, 4),
                  'implied_mass_kg_cop_y_minus_3cm': round(1 / sl2, 2) if sl2 > 0 else None,
                  'ratio_to_readme': round((1 / sl) / pub[subj], 4) if sl > 0 else None,
                  'ratio_to_model': round((1 / sl) / model['mass_kg'], 4) if sl > 0 else None,
                  'samples': int(src.size)}
    fpm = [x['force_plate_mass_kg'] for x in out['sides'] if 'force_plate_mass_kg' in x]
    out['force_plate_body_mass_kg'] = round(float(np.mean(fpm)), 2) if fpm else None
    return out


def draw_sample():
    """Seeded draw for all 12 subjects at once (independent of which stage runs)."""
    pub = masses(PUB_MASSES)
    rng = np.random.default_rng(SEED)
    plan = {}
    for subj in sorted(pub):
        tasks = sorted(p.name for p in (RAW / subj / 'CSV_Data').iterdir() if p.is_dir())
        fams = sorted({family(t) for t in tasks} & set(FAMILIES))
        order = [fams[i] for i in rng.permutation(len(fams))]
        plan[subj] = []
        for f in order:
            members = sorted(t for t in tasks if family(t) == f)
            plan[subj].append(members[int(rng.integers(len(members)))])
    return plan


def eh_check(reader, subj):
    """Local N*m re-run (unknown provenance) vs the matching published trial."""
    import pandas as pd
    p = RAW / subj / 'MotionFile_EH' / 'inverse_dynamics.sto'
    if not p.exists():
        return {'subject': subj, 'present': False}
    b = reader.raw(p)
    lines = b[:4000].decode(errors='replace').splitlines()
    skip = next(i for i, l in enumerate(lines) if l.strip() == 'endheader') + 1
    eh = pd.read_csv(io.BytesIO(b), sep=r'\s+', skiprows=skip)
    del b
    t_end = float(eh.time.iloc[-1])
    match = []
    for d in sorted((RAW / subj / 'CSV_Data').iterdir()):
        with (d / 'Joint_Moments.csv').open('rb') as f:
            f.seek(-300, 2)
            last = f.read().splitlines()[-1]
        if abs(float(last.split(b',')[0]) - t_end) < 0.01:
            match.append(d.name)
    out = {'subject': subj, 'present': True, 'in_publisher_archive': False, 'rows': len(eh), 't_end_s': t_end,
           'matching_trials_by_end_time': match}
    if len(match) != 1:
        out['note'] = 'no unique matching trial'
        return out
    jm = reader.table(RAW / subj / 'CSV_Data' / match[0] / 'Joint_Moments.csv')
    cols = {}
    for c in ['ankle_angle_r_moment', 'ankle_angle_l_moment', 'knee_angle_r_moment', 'knee_angle_l_moment',
              'hip_flexion_r_moment', 'hip_flexion_l_moment']:
        m = pd.merge_asof(jm[['time', c]].rename(columns={c: 'pub'}), eh[['time', c]].rename(columns={c: 'eh'}),
                          on='time', tolerance=1e-4, direction='nearest')
        f = np.isfinite(m.pub.to_numpy()) & np.isfinite(m.eh.to_numpy())
        if f.sum() < 1000:
            continue
        a, e = m.pub.to_numpy()[f], m.eh.to_numpy()[f]
        k = float(a @ e / (a @ a))
        cols[c] = {'n': int(f.sum()), 'eh_over_published_slope': round(k, 3),
                   'corr': round(float(np.corrcoef(a, e)[0, 1]), 5),
                   'max_abs_residual_Nm': round(float(np.max(np.abs(e - k * a))), 4),
                   'p99_abs_Nm': round(float(np.percentile(np.abs(e), 99)), 2)}
    out['trial'] = match[0]
    out['columns'] = cols
    sag = [v['eh_over_published_slope'] for k, v in cols.items() if not k.startswith('hip')]
    out['divisor_kg_median_ankle_knee'] = round(float(np.median(sag)), 2) if sag else None
    return out


def band(values):
    q = np.log(np.asarray(values, float))
    c = float(np.median(q))
    s = 1.4826 * float(np.median(np.abs(q - c)))
    half = max(3 * s, BAND_FLOOR)
    return {'n': int(q.size), 'centre_ratio': round(float(np.exp(c)), 4), 'robust_sd_log': round(s, 4),
            'half_width_log': round(half, 4), 'band_ratio': [round(float(np.exp(c - half)), 4), round(float(np.exp(c + half)), 4)]}


def run_subjects(reader, inv, pub, plan, subjects, extra=()):
    trials, redraws = [], []
    for subj in subjects:
        got = 0
        for task in plan[subj]:
            if got == K_PER_SUBJECT:
                break
            r = analyse_trial(reader, inv, pub, subj, task, 'seeded')
            if r['usable']:
                trials.append(r); got += 1
            else:
                redraws.append({'subject': subj, 'task': task, 'reason': r.get('reason')})
            print(f'{subj} {task}: usable={r["usable"]} ankle={r.get("ankle", {}).get("implied_mass_kg")} rss={peak_rss_mib()}', flush=True)
            if peak_rss_mib() > RSS_LIMIT_MIB:
                raise MemoryError('peak RSS above limit')
    for subj, task in extra:
        r = analyse_trial(reader, inv, pub, subj, task, 'targeted')
        trials.append(r)
        print(f'{subj} {task} (targeted): ankle={r.get("ankle", {}).get("implied_mass_kg")} rss={peak_rss_mib()}', flush=True)
    return trials, redraws


def stage_reference():
    import pandas  # noqa: F401
    resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 ** 2, 1536 * 1024 ** 2))
    pub = masses(PUB_MASSES)
    zipdir = {e['name']: e for e in json.loads(ZIP_DIR.read_text())}
    reader = Reader(zipdir)
    inv = inventory(reader)
    plan = draw_sample()
    trials, redraws = run_subjects(reader, inv, pub, plan, REFERENCE)
    seeded = [t for t in trials if t['usable']]
    tol = {j: band([t[j]['ratio_to_readme'] for t in seeded if t[j]['ratio_to_readme']]) for j in WINDOWS}
    eh = [eh_check(reader, s) for s in REFERENCE]
    eh_ratios = [e['divisor_kg_median_ankle_knee'] / pub[e['subject']] for e in eh if e.get('divisor_kg_median_ankle_knee')]
    tol['local_nm_rerun'] = band(eh_ratios)
    data = {'task_id': 'GT23-C03', 'stage': 'reference', 'scientific_approval': False,
            'question': 'Which mass did the GT23 authors divide each subject\'s joint moments by, and are any subjects or trials mis-scaled?',
            'seed': SEED, 'k_per_subject': K_PER_SUBJECT, 'families': FAMILIES, 'sample_plan': plan,
            'reference_subjects': REFERENCE, 'test_subjects': TEST, 'targeted_trials': [list(x) for x in TARGETED],
            'tolerance_rule': 'per-trial log(implied / README mass) over reference seeded trials; centre = median; robust sd = 1.4826 MAD; '
                              'band = centre +/- max(3 sd, log 1.10). Trial flagged outside band; subject flagged when the median of its trial ratios is outside.',
            'tolerance': tol, 'tolerance_fixed_at_utc': utc(),
            'readme_masses_kg': pub, 'mass_tables': {'readme_publisher': {'path': str(PUB_MASSES.relative_to(ROOT)), 'sha256': digest(PUB_MASSES)},
                                                     'local_model_derived': {'path': str(RAW / 'Subject_masses.csv'), 'sha256': digest(RAW / 'Subject_masses.csv'),
                                                                             'kg': masses(RAW / 'Subject_masses.csv')}},
            'model_inventory': inv, 'trials': trials, 'redraws': redraws, 'local_nm_rerun': eh,
            'files_read': reader.files, 'peak_rss_mib': {'reference': peak_rss_mib()}}
    AUDIT.write_text(json.dumps(data, indent=1) + '\n')
    print(json.dumps({'tolerance': tol, 'peak_rss_mib': peak_rss_mib()}, indent=1))


EXACT_CORR = 0.9999       # local N*m re-run counts as the published run only if every ankle/knee column correlates this well
SUBJECT_FLOOR = float(np.log(1.05))


def exact_divisor(e):
    cols = {k: v for k, v in e.get('columns', {}).items() if not k.startswith('hip')}
    if cols and all(v['corr'] >= EXACT_CORR for v in cols.values()):
        return round(float(np.median([v['eh_over_published_slope'] for v in cols.values()])), 2)
    return None


def calibration_trial(reader, inv, pub, data, subj):
    """Lever-arm analysis of the trial that the local N*m re-run covers (normal_walk_1 when no re-run)."""
    e = next((x for x in data['local_nm_rerun'] if x['subject'] == subj), {})
    task = e.get('trial') or 'normal_walk_1'
    have = next((t for t in data['trials'] if t['subject'] == subj and t['task'] == task and t.get('usable')), None)
    if have:
        return have
    r = analyse_trial(reader, inv, pub, subj, task, 'calibration')
    data['trials'].append(r)
    print(f'{subj} {task} (calibration): ankle={r.get("ankle", {}).get("implied_mass_kg")} rss={peak_rss_mib()}', flush=True)
    return r


def stage_calibrate():
    """Second, stricter tolerance, fixed before any test-subject data are read.

    Added after the reference stage showed that the local N*m re-run reproduces the published moments
    exactly (correlation 1.0) for several reference subjects, but with a divisor that is not always the
    subject's README mass. Agreement with the README mass is therefore not a valid reference; the
    lever-arm method is instead calibrated against those exactly known divisors on the same trial."""
    import pandas  # noqa: F401
    resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 ** 2, 1536 * 1024 ** 2))
    data = json.loads(AUDIT.read_text())
    if data.get('stage') != 'reference':
        raise ValueError('Calibrate runs once, after the reference stage and before the test stage')
    pub = masses(PUB_MASSES)
    zipdir = {e['name']: e for e in json.loads(ZIP_DIR.read_text())}
    reader = Reader(zipdir)
    inv = data['model_inventory']
    cal = {}
    for subj in REFERENCE:
        e = next((x for x in data['local_nm_rerun'] if x['subject'] == subj), {})
        t = calibration_trial(reader, inv, pub, data, subj)
        cal[subj] = {'trial': t['task'], 'exact_divisor_kg': exact_divisor(e),
                     'lever_ankle_kg': t['ankle']['implied_mass_kg'], 'lever_knee_kg': t['knee']['implied_mass_kg']}
    exact = {k: v for k, v in cal.items() if v['exact_divisor_kg']}
    tol2 = {}
    for j in WINDOWS:
        q = np.log([v[f'lever_{j}_kg'] / v['exact_divisor_kg'] for v in exact.values()])
        c = float(np.median(q)); sd = 1.4826 * float(np.median(np.abs(q - c)))
        half = max(3 * sd, SUBJECT_FLOOR)
        tol2[f'{j}_bias'] = {'n_subjects': int(q.size), 'subjects': sorted(exact), 'centre_ratio': round(float(np.exp(c)), 4),
                             'robust_sd_log': round(sd, 4), 'half_width_log': round(half, 4),
                             'per_subject_ratio': {k: round(v[f'lever_{j}_kg'] / v['exact_divisor_kg'], 4) for k, v in exact.items()}}
        dev = []
        for subj in REFERENCE:
            base = cal[subj][f'lever_{j}_kg']
            dev += [float(np.log(t[j]['implied_mass_kg'] / base)) for t in data['trials']
                    if t['subject'] == subj and t.get('origin') == 'seeded' and t.get('usable') and t[j]['implied_mass_kg']
                    and t['task'] != cal[subj]['trial']]
        dev = np.array(dev); sd = 1.4826 * float(np.median(np.abs(dev - np.median(dev))))
        tol2[f'{j}_trial_within_subject'] = {'n_trials': int(dev.size), 'median_log': round(float(np.median(dev)), 4),
                                             'robust_sd_log': round(sd, 4), 'half_width_log': round(max(3 * sd, BAND_FLOOR), 4)}
    data['calibration'] = cal
    data['tolerance_v2'] = tol2
    data['tolerance_v2_rule'] = ('Subject divisor from the lever arm = lever implied mass on the re-run trial / ankle_bias centre; a candidate mass is '
                                 'consistent when |log(divisor / candidate)| <= ankle_bias half width (max(3 robust sd, log 1.05)). Exact re-run divisors '
                                 '(every ankle/knee column correlation >= 0.9999) override the lever arm. A trial is flagged when its lever implied mass deviates '
                                 'from the same subject\'s re-run-trial lever implied mass by more than the trial half width (max(3 robust sd, log 1.10)).')
    data['tolerance_v2_fixed_at_utc'] = utc()
    data['stage'] = 'calibrated'
    data['files_read'] += reader.files
    data['peak_rss_mib']['calibrate'] = peak_rss_mib()
    AUDIT.write_text(json.dumps(data, indent=1) + '\n')
    print(json.dumps({'calibration': cal, 'tolerance_v2': tol2, 'peak_rss_mib': peak_rss_mib()}, indent=1))


def stage_test():
    import pandas  # noqa: F401
    resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 ** 2, 1536 * 1024 ** 2))
    data = json.loads(AUDIT.read_text())
    if data.get('stage') != 'calibrated' or 'tolerance' not in data or 'tolerance_v2' not in data:
        raise ValueError('Run reference and calibrate first; tolerances must be fixed before test data are read')
    pub = masses(PUB_MASSES)
    zipdir = {e['name']: e for e in json.loads(ZIP_DIR.read_text())}
    reader = Reader(zipdir)
    inv = data['model_inventory']
    plan = data['sample_plan']
    if plan != draw_sample():
        raise ValueError('Sample plan changed between stages')
    trials, redraws = run_subjects(reader, inv, pub, plan, TEST, TARGETED)
    data['trials'] += trials
    data['redraws'] += redraws
    data['local_nm_rerun'] += [eh_check(reader, s) for s in TEST]
    for subj in TEST:
        e = next((x for x in data['local_nm_rerun'] if x['subject'] == subj), {})
        t = calibration_trial(reader, inv, pub, data, subj)
        data['calibration'][subj] = {'trial': t['task'], 'exact_divisor_kg': exact_divisor(e),
                                     'lever_ankle_kg': t['ankle']['implied_mass_kg'], 'lever_knee_kg': t['knee']['implied_mass_kg']}
    data['files_read'] += reader.files
    data['peak_rss_mib']['test'] = peak_rss_mib()
    if peak_rss_mib() > RSS_LIMIT_MIB:
        raise MemoryError('peak RSS above limit')
    tol, tol2, cal = data['tolerance'], data['tolerance_v2'], data['calibration']
    order = sorted(pub)
    prev = {s: pub[order[i - 1]] for i, s in enumerate(order) if i > 0}
    cands = {f'README {k}': v for k, v in pub.items()}
    for subj, x in inv.items():
        for name, m in x['models'].items():
            if 'mass_kg' in m:
                cands[f'model {subj}/{name}'] = m['mass_kg']
    flags_v1, flags_trial = [], []
    for t in data['trials']:
        if not t.get('usable'):
            continue
        subj = t['subject']
        for j in WINDOWS:
            r = t[j]['ratio_to_readme']
            t[j]['inside_tolerance_v1'] = bool(r and abs(np.log(r / tol[j]['centre_ratio'])) <= tol[j]['half_width_log'])
            base = cal[subj][f'lever_{j}_kg']
            dev = float(np.log(t[j]['implied_mass_kg'] / base)) if t[j]['implied_mass_kg'] else None
            t[j]['log_dev_from_subject_calibration_trial'] = round(dev, 4) if dev is not None else None
            t[j]['inside_trial_band_v2'] = dev is not None and abs(dev - tol2[f'{j}_trial_within_subject']['median_log']) <= tol2[f'{j}_trial_within_subject']['half_width_log']
        div = t['ankle']['implied_mass_kg'] / tol2['ankle_bias']['centre_ratio']
        t['ankle']['bias_corrected_divisor_kg'] = round(div, 2)
        t['ankle']['nearest_candidate_masses'] = [[k, v] for k, v in sorted(cands.items(), key=lambda kv: abs(np.log(kv[1] / div)))[:4]]
        if not t['ankle']['inside_tolerance_v1']:
            flags_v1.append({'subject': subj, 'task': t['task'], 'origin': t['origin'], 'ankle_ratio_to_readme': t['ankle']['ratio_to_readme']})
        if not t['ankle']['inside_trial_band_v2']:
            flags_trial.append({'subject': subj, 'task': t['task'], 'origin': t['origin'],
                                'ankle_log_dev': t['ankle']['log_dev_from_subject_calibration_trial'],
                                'knee_log_dev': t['knee']['log_dev_from_subject_calibration_trial'],
                                'knee_inside_trial_band': t['knee']['inside_trial_band_v2'],
                                'ankle_factor_vs_calibration_trial': round(float(np.exp(t['ankle']['log_dev_from_subject_calibration_trial'])), 3),
                                'bias_corrected_divisor_kg': round(div, 2)})
    subjects = {}
    hb = tol2['ankle_bias']['half_width_log']
    for subj in order:
        ts = [t for t in data['trials'] if t['subject'] == subj and t.get('usable') and t['origin'] == 'seeded']
        c = cal[subj]
        lever_div = c['lever_ankle_kg'] / tol2['ankle_bias']['centre_ratio']
        knee_div = c['lever_knee_kg'] / tol2['knee_bias']['centre_ratio']
        seeded_div = float(np.median([t['ankle']['implied_mass_kg'] for t in ts])) / tol2['ankle_bias']['centre_ratio'] if ts else None
        best = c['exact_divisor_kg'] or lever_div
        fp = [t['force_plate_body_mass_kg'] for t in data['trials'] if t['subject'] == subj and t.get('usable') and t.get('force_plate_body_mass_kg')]
        subjects[subj] = {
            'readme_mass_kg': pub[subj], 'previous_subject_readme_mass_kg': prev.get(subj),
            'models_used': sorted({t['model'] for t in data['trials'] if t['subject'] == subj and t.get('model')}),
            'model_masses_kg': sorted({t['model_mass_kg'] for t in data['trials'] if t['subject'] == subj and t.get('model_mass_kg')}),
            'force_plate_body_mass_kg_median': round(float(np.median(fp)), 1) if fp else None,
            'calibration_trial': c['trial'],
            'exact_divisor_kg_from_local_nm_rerun': c['exact_divisor_kg'],
            'lever_divisor_kg_calibration_trial_ankle': round(lever_div, 2),
            'lever_divisor_kg_calibration_trial_knee': round(knee_div, 2),
            'lever_divisor_kg_seeded_median_ankle': round(seeded_div, 2) if seeded_div else None,
            'seeded_trials': [t['task'] for t in ts],
            'divisor_kg_best': round(best, 2), 'divisor_basis': 'local N*m re-run (exact)' if c['exact_divisor_kg'] else 'lever arm (calibrated)',
            'readme_consistent': bool(abs(np.log(best / pub[subj])) <= (0.01 if c['exact_divisor_kg'] else hb)),
            'previous_subject_consistent': (bool(abs(np.log(best / prev[subj])) <= (0.01 if c['exact_divisor_kg'] else hb)) if subj in prev else None),
            'lever_log_err_own_readme': round(float(np.log(lever_div / pub[subj])), 4),
            'lever_log_err_previous_readme': round(float(np.log(lever_div / prev[subj])), 4) if subj in prev else None,
            'scale_factor_published_vs_readme_normalized': round(pub[subj] / best, 3),
            'trials_outside_trial_band': [t['task'] for t in ts if not t['ankle']['inside_trial_band_v2']],
            'nearest_candidate_masses': [[k, v] for k, v in sorted(cands.items(), key=lambda kv: abs(np.log(kv[1] / best)))[:3]]}
    data['subjects'] = subjects
    data['flags_v1_readme_band'] = flags_v1
    data['flags_trial_v2'] = flags_trial
    data['candidate_masses_kg'] = cands
    data['stage'] = 'final'
    data['finished_at_utc'] = utc()
    AUDIT.write_text(json.dumps(data, indent=1) + '\n')
    print(json.dumps({'subjects': subjects, 'flags_trial_v2': flags_trial, 'peak_rss_mib': data['peak_rss_mib']}, indent=1))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('step', choices=['reference', 'calibrate', 'test', 'sheet'])
    args = parser.parse_args()
    os.nice(max(0, 19 - os.nice(0)))
    if args.step == 'sheet':
        build_sheet()
    else:
        {'reference': stage_reference, 'calibrate': stage_calibrate, 'test': stage_test}[args.step]()


INK, MUTED, BLUE, ORANGE, GREY = '#20252B', '#5b6672', '#2a78d6', '#eb6834', '#9aa3ad'
SHORT = {'normal_walk_1': 'level walk', 'incline_walk_1': 'incline 1', 'incline_walk_2': 'incline 2',
         'turn_and_step_1': 'turn', 'dynamic_walk_1': 'dynamic', 'curb_up_1': 'curb up', 'curb_down_1': 'curb down',
         'weighted_walk_1': 'weighted', 'obstacle_walk_1': 'obstacle', 'side_shuffle_1': 'shuffle', 'cutting_1': 'cutting',
         'meander_1': 'meander', 'tire_run_1': 'tire run', 'walk_backward_1': 'backward', 'stairs_1_10': 'stairs',
         'stairs_1_5': 'stairs'}


def style():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 10.5, 'axes.titlesize': 11, 'axes.spines.top': False, 'axes.spines.right': False,
                         'text.color': INK, 'axes.labelcolor': INK, 'axes.edgecolor': INK, 'xtick.color': INK,
                         'ytick.color': INK, 'axes.linewidth': 0.6, 'legend.frameon': False, 'legend.fontsize': 10})
    return plt


def save(fig, path, dpi=170):
    """Fixed 4.5 in canvas (no tight bbox), so the saved PNG is never wider than 4.5 in."""
    import struct
    fig.savefig(path, dpi=dpi)
    with open(path, 'rb') as f:
        width = struct.unpack('>I', f.read(24)[16:20])[0]
    if width / dpi > 4.5 + 1e-6:
        raise ValueError(f'{path} is {width / dpi:.2f} in wide; limit 4.5 in')


def fig_subjects(plt, data, path):
    subs = data['subjects']
    names = sorted(subs)
    fig, ax = plt.subplots(figsize=(4.5, 4.9), layout='constrained')
    hb = data['tolerance_v2']['ankle_bias']['half_width_log']
    for y, sname in enumerate(names):
        v = subs[sname]
        if v['previous_subject_readme_mass_kg']:
            ax.plot(v['previous_subject_readme_mass_kg'], y, 'D', mfc='none', mec=ORANGE, ms=8, mew=1.6)
        ax.plot(v['readme_mass_kg'], y, 'o', mfc='none', mec=MUTED, ms=11, mew=1.6)
        lev = v['lever_divisor_kg_calibration_trial_ankle']
        ax.plot([lev * np.exp(-hb), lev * np.exp(hb)], [y, y], color=BLUE, lw=2.2, alpha=.55)
        if v['exact_divisor_kg_from_local_nm_rerun']:
            ax.plot(v['exact_divisor_kg_from_local_nm_rerun'], y, 's', color=INK, ms=5.5)
        else:
            # force-plate only: every recorded mass inside the band fits, so the estimate is not unique
            for m in data['readme_masses_kg'].values():
                if abs(np.log(m / lev)) <= hb:
                    ax.plot(m, y, '|', color=INK, ms=11, mew=1.6)
            ax.plot(lev, y, 'o', mfc='white', mec=INK, ms=5, mew=1.3)
    ax.set_yticks(range(len(names)), names)
    ax.invert_yaxis()
    ax.set_xscale('log')
    ax.set_xticks([60, 70, 80, 90, 100, 115], ['60', '70', '80', '90', '100', '115'])
    ax.minorticks_off()
    ax.set_xlabel('mass (kg, log scale), level walking trial')
    ax.plot([], [], 'o', mfc='none', mec=MUTED, ms=9, mew=1.6, label='own body mass')
    ax.plot([], [], 'D', mfc='none', mec=ORANGE, ms=7, mew=1.6, label='previous subject\'s mass')
    ax.plot([], [], color=BLUE, lw=2.2, alpha=.55, label='force-plate estimate ±5 %')
    ax.plot([], [], 's', color=INK, ms=5, label='exact divisor (N·m re-run)')
    ax.plot([], [], '|', color=INK, ms=9, mew=1.6, label='masses that also fit')
    fig.legend(loc='outside lower center', ncol=2, fontsize=10, handletextpad=.3, columnspacing=.8)
    save(fig, path); plt.close(fig)


def fig_trials(plt, data, path, contrast):
    b = data['tolerance_v2']['ankle_bias']['centre_ratio']
    hb = data['tolerance_v2']['ankle_bias']['half_width_log']
    fig, ax = plt.subplots(figsize=(4.5, 3.9), layout='constrained')
    x0 = 0
    ticks, labels = [], []
    for subj, col in (('AB05', ORANGE), (contrast, BLUE)):
        seen, rows = set(), []
        for t in data['trials']:
            if t['subject'] == subj and t.get('usable') and t['task'] not in seen:
                seen.add(t['task']); rows.append(t)
        rows.sort(key=lambda t: t['ankle']['implied_mass_kg'])
        own = data['readme_masses_kg'][subj]
        ax.plot([x0 - .5, x0 + len(rows) - .5], [own, own], color=MUTED, lw=1.2, ls='--')
        ax.text(x0 - .4, own - 6.5, f'{subj} own mass', color=MUTED, fontsize=10)
        for i, t in enumerate(rows):
            d = t['ankle']['implied_mass_kg'] / b
            ax.errorbar(x0 + i, d, yerr=[[d - d * np.exp(-hb)], [d * np.exp(hb) - d]], fmt='o', color=col, ms=5, capsize=0, lw=1.6)
            ticks.append(x0 + i); labels.append(SHORT.get(t['task'], t['task']))
        ex = data['subjects'][subj]['exact_divisor_kg_from_local_nm_rerun']
        if ex:
            i = [k for k, t in enumerate(rows) if t['task'] == data['subjects'][subj]['calibration_trial']][0]
            ax.plot(x0 + i, ex, 's', color=INK, ms=5.5, zorder=5)
        x0 += len(rows) + 1
    ax.set_xticks(ticks, labels, rotation=55, ha='right')
    ax.set_ylabel('mass divided by (kg)')
    ax.set_ylim(55, 135)
    save(fig, path); plt.close(fig)


def fig_method(plt, data, path):
    subs = {k: v for k, v in data['subjects'].items() if v['exact_divisor_kg_from_local_nm_rerun']}
    hb = data['tolerance_v2']['ankle_bias']['half_width_log']
    fig, ax = plt.subplots(figsize=(4.5, 3.9), layout='constrained')
    xs = np.linspace(55, 120, 50)
    ax.fill_between(xs, xs * np.exp(-hb), xs * np.exp(hb), color=BLUE, alpha=.12, lw=0)
    ax.plot(xs, xs, color=BLUE, lw=1)
    for k, v in subs.items():
        lev = v['lever_divisor_kg_calibration_trial_ankle']
        ax.plot(v['readme_mass_kg'], lev, 'o', mfc='none', mec=MUTED, ms=8, mew=1.4)
        ax.plot(v['exact_divisor_kg_from_local_nm_rerun'], lev, 's', color=INK, ms=5.5)
    ax.plot([], [], 's', color=INK, ms=5, label='vs exact divisor')
    ax.plot([], [], 'o', mfc='none', mec=MUTED, ms=7, mew=1.4, label='vs own body mass')
    ax.legend(loc='upper left', fontsize=10)
    ax.set_xlim(55, 120); ax.set_ylim(55, 120)
    ax.set_xlabel('mass (kg)')
    ax.set_ylabel('force-plate estimate (kg)')
    save(fig, path); plt.close(fig)


def build_sheet():
    from contributor_tools.common.review_sheet import page
    data = json.loads(AUDIT.read_text())
    if data.get('stage') != 'final':
        raise ValueError('Run the probe stages first')
    subs = data['subjects']
    agreeing = sorted(k for k, v in subs.items() if v['readme_consistent'])
    contrast = agreeing[int(np.random.default_rng(SEED + 1).integers(len(agreeing)))]
    plt = style()
    SHEET.mkdir(parents=True, exist_ok=True)
    for old in SHEET.glob('*.png'):
        old.unlink()
    fig_subjects(plt, data, SHEET / 'fig1_subjects.png')
    fig_trials(plt, data, SHEET / 'fig2_trials.png', contrast)
    fig_method(plt, data, SHEET / 'fig3_method.png')
    wrong = sorted(k for k, v in subs.items() if not v['readme_consistent'])
    exact = {k: v for k, v in subs.items() if v['exact_divisor_kg_from_local_nm_rerun']}
    method_err = [abs(np.log(v['lever_divisor_kg_calibration_trial_ankle'] / v['exact_divisor_kg_from_local_nm_rerun'])) for v in exact.values()]
    cal_subj = data['tolerance_v2']['ankle_bias']['subjects']
    oos_err = [abs(np.log(v['lever_divisor_kg_calibration_trial_ankle'] / v['exact_divisor_kg_from_local_nm_rerun']))
               for k, v in exact.items() if k not in cal_subj]
    exact_wrong = sorted(k for k, v in exact.items() if abs(np.log(v['exact_divisor_kg_from_local_nm_rerun'] / v['readme_mass_kg'])) > 0.01)
    prev_exact = sorted(k for k in exact_wrong if subs[k]['previous_subject_readme_mass_kg']
                        and abs(np.log(subs[k]['exact_divisor_kg_from_local_nm_rerun'] / subs[k]['previous_subject_readme_mass_kg'])) < 0.001)
    hb = data['tolerance_v2']['ankle_bias']['half_width_log']
    lever_fits = {k: [m for m in data['readme_masses_kg'].values() if abs(np.log(m / v['lever_divisor_kg_calibration_trial_ankle'])) <= hb]
                  for k, v in subs.items() if k in wrong and not v['exact_divisor_kg_from_local_nm_rerun']}
    fp_err = [abs(v['force_plate_body_mass_kg_median'] / v['readme_mass_kg'] - 1) for v in subs.values() if v['force_plate_body_mass_kg_median']]
    def divisor(t):
        v = subs[t['subject']]
        if t['task'] == v['calibration_trial'] and v['exact_divisor_kg_from_local_nm_rerun']:
            return v['exact_divisor_kg_from_local_nm_rerun']
        return t['ankle']['bias_corrected_divisor_kg']
    clean = list({(t['subject'], t['task']): t for t in data['trials'] if t.get('usable') and t['ankle']['corr'] >= 0.98}.values())
    factors = [data['readme_masses_kg'][t['subject']] / divisor(t) for t in clean]
    ab05 = [t for t in clean if t['subject'] == 'AB05']
    ab05_walk = [divisor(t) for t in ab05 if t['task'] == subs['AB05']['calibration_trial']]
    ab05_other = [divisor(t) for t in ab05 if t['task'] != subs['AB05']['calibration_trial']]
    other_flags = sorted({f"{f['subject']} {SHORT.get(f['task'], f['task'])}" for f in data['flags_trial_v2']
                          if f['subject'] != 'AB05' and f['knee_inside_trial_band'] is False and 'curb' not in f['task']})
    curb = sorted({f"{t['subject']} {SHORT.get(t['task'], t['task'])}" for t in data['trials']
                   if t.get('usable') and 'curb' in t['task'] and t['ankle']['corr'] < 0.98})
    chips = [
        ('pass', f'README masses are body masses: force plates agree within {100 * max(fp_err):.0f} % in {len(fp_err)} of 12'),
        ('pass', f'Force-plate estimate within {100 * (np.exp(max(oos_err)) - 1):.1f} % of the exact divisor out of sample ({len(oos_err)} of {len(oos_err)}; bias set on {len(cal_subj)} of {len(exact)})'),
        ('fail', f'Not own mass in {len(wrong)} of 12 subjects; another subject\'s mass by re-run in {len(exact_wrong)}, the previous subject\'s in {len(prev_exact)}'),
        ('fail', f'Published values {min(factors):.2f} to {max(factors):.2f} times the per-kg value ({len(clean)} trials)'),
        ('fail', f'AB05 divisor changes between trials: {ab05_walk[0]:.0f} kg level walking, {min(ab05_other):.0f}-{max(ab05_other):.0f} kg in {len(set(t["task"] for t in ab05)) - 1} others'),
        ('unchecked', 'Other trial jumps, knee agrees: ' + ', '.join(other_flags)),
        ('unchecked', f'Curb trials: estimate unreliable in {len(curb)} of {sum(1 for t in data["trials"] if t.get("usable") and "curb" in t["task"])}'),
        ('unchecked', 'Origin of the local N·m re-run files (not in the publisher archive)'),
    ]
    options = [
        (0, 'Withhold GT23 moments and powers', 'All GT23 joint moments and powers',
         'Kinematics and forces still released; no GT23 joint kinetics until the authors confirm the masses or a full check is reviewed. Nothing is estimated. Reversible.'),
        (1, 'Rescale each trial to its participant\'s own mass', 'Trials whose divisor cannot be matched',
         'Needs a full per-trial check first: each trial\'s divisor is measured (exact where an N·m re-run matches the published values by a constant, else force plates within 5 %) and '
         'matched to a recorded mass; unmatched trials are left out. Adds a derived step that needs its own review. Reversible.'),
        (2, 'Release as published with an erratum', 'Nothing',
         f'All values kept with a per-subject warning table; users get moments and powers {min(factors):.2f} to {max(factors):.2f} times '
         'the per-kg value and must correct them. Reversible.'),
    ]
    options.sort(key=lambda o: o[0])   # neutral order: GT23 moment trials released (none, matched only, all)
    keys = 'ABC'
    rows = [(f'{k} · {o[1]}', [o[2], o[3]]) for k, o in zip(keys, options)]
    rows.append(('Defer', ['—', 'GT23 kinetics stay unreleased; drafts keep the published (mis-scaled) values; kinematics unaffected.']))
    why = (f'An N·m re-run fixes the divisor in {len(exact)} level-walking trials; in {len(exact_wrong)} it is another participant\'s mass, '
           'and the divisor changes between trials of one subject, so a correction needs a divisor for every trial. Withholding invents '
           'nothing and is reversed once a full check or the authors confirm the masses.')
    decision = {'question': 'How should LocoHub release GT23 joint moments and powers?',
                'columns': ['Left out', 'Consequence'], 'rows': rows,
                'recommendation': f'A. {why} Confidence: medium.',
                'footnote': 'Ordered by moment trials released.'}
    details = [f'Seed {SEED} ({K_PER_SUBJECT} trials per subject from {len(FAMILIES)} locomotion task families); comparison subject drawn with seed {SEED + 1} from {", ".join(agreeing)}: {contrast}.',
               'Divisor = force-plate lever-arm moment (N·m, subject model joint centres, calcn frame) / published moment (N·m/kg); '
               f'bias {data["tolerance_v2"]["ankle_bias"]["centre_ratio"]} calibrated on {len(cal_subj)} of the {len(exact)} trials whose local N·m re-run equals the published values times a constant '
               f'({", ".join(cal_subj)}); out of sample it held in {len(oos_err)} of {len(oos_err)} (worst {100 * (np.exp(max(oos_err)) - 1):.1f} %). '
               f'Force-plate-only subjects fit more than one recorded mass within the band: ' + '; '.join(f'{k} ' + ' or '.join(f'{m}' for m in sorted(v)) for k, v in lever_fits.items()) + '.',
               'Per subject (README, divisor, basis): ' + '; '.join(f'{k} {v["readme_mass_kg"]}, {v["divisor_kg_best"]} ({"exact" if v["exact_divisor_kg_from_local_nm_rerun"] else "force plate"})' for k, v in subs.items()),
               'Local N·m re-run: RawData/<subject>/MotionFile_EH/inverse_dynamics.sto, absent from the publisher archive directory; provenance unknown.',
               f'Evidence: {AUDIT.relative_to(ROOT)}; builder {Path(__file__).relative_to(ROOT)}. Peak memory {max(data["peak_rss_mib"].values())} MiB.']
    page(SHEET / 'index.html', title='GT23 moment masses',
         ask='Choose how GT23 moments and powers are released.',
         headline=f'GT23 moments not divided by the subject\'s own mass in {len(wrong)} of 12 subjects',
         chips=chips,
         figures=[('fig1_subjects.png', 'Was each subject\'s walking trial divided by its own mass?',
                   'Squares exact; open dots not unique.', 'Divisor per subject against own and previous subject mass'),
                  ('fig2_trials.png', 'Does the divisor change between one subject\'s trials?',
                   f'AB05 (orange) against {contrast} (blue, seeded).', 'Per-trial divisor for AB05 and a comparison subject'),
                  ('fig3_method.png', 'Can the force-plate estimate tell masses apart?',
                   'Squares on the line; circles off it.', 'Force-plate estimate against exact divisor and own mass')],
         not_shown=['Every trial (4 to 6 per subject)', 'Hip moments', 'Why the masses shifted'],
         reply='D-GT23-C03-1: A, B, C or defer', details=details, decision=decision)
    backlog = {'id': 'D-GT23-C03-1', 'task_id': 'GT23-C03',
               'question': 'GT23 joint moments and powers were divided by another participant\'s body mass in most subjects, and the mass '
                           'can change between trials of one participant. How should LocoHub release GT23 moments and powers?',
               'options': [{'key': k, 'label': o[1], 'consequence': o[3]} for k, o in zip(keys, options)],
               'options_order': 'By GT23 moment trials released: none, only those with a matched divisor, all.',
               'recommended': 'A', 'confidence': 'medium', 'why': why,
               'check': f'Sheet, first figure: the black square for AB06 sits on the orange diamond (71.5 kg, the previous subject), not on its own grey circle (79.1 kg).',
               'cost_of_waiting': 'GT23 joint kinetics stay out of any release and drafts keep the published mis-scaled values; GT23 kinematics and other datasets are unaffected.',
               'decide_before_recommendation': True, 'status': 'open'}
    (SHEET / 'decision.json').write_text(json.dumps(backlog, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'contrast': contrast, 'chips': chips, 'decision': backlog}, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
