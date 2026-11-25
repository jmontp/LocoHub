"""GT21-RB05 independent readback (separate code path).

Imports nothing from the export code (gt21_rb_export, run_gt21_rb_export) or from the pass code (gt21_rb_pass). Only data
access is shared: the fail-closed MAT table reader gt21_numeric_source (to read the 1 kHz plate source table).

For each participant export root (phase.parquet, time.parquet, observations.jsonl, exclusions.jsonl, recordings.jsonl,
run_summary.json) it checks, against the inputs on disk (merged-pass tables and ledgers, RB03 steps, ledger and force-mask
layers, authors' fields):

  structure   every phase observation has exactly 150 rows on the bitwise np.linspace(0, 100, 150) grid, constant metadata,
              one reference side; rows = observations x 150; no duplicate identity; time rows equal the pass rows.
  values      every phase value except force against the pass table by an independent interpolation (np.interp with a
              missing-neighbour indicator); every continuous value against the pass table with the force mask applied; forces
              at the two on-clock samples (first and last phase sample) against the pass table; masked phase samples are
              missing; and, for seeded recordings (one per mode per participant), every force value of every observation
              re-derived from the 1 kHz plate source with scalar-free but separately written ownership, sign and mask code.
  power       power == moment x joint speed in every row of both tables (missing iff either factor is missing).
  counts      per recording and in total: RB03 eligible steps = exported phase observations (+ export exclusions), every other
              RB03 step is in exclusions.jsonl once with the RB03 reason, RB03 ledger step count = observations + exclusions,
              inventory recordings = exported + excluded recordings (3,147 over 22 participants), one continuous observation
              per converted recording, held_signals = the columns with no finite value, flags and labels = RB03 fields.
  lineage     output file hashes equal run_summary; pass parquet and mask layer hashes equal recordings.jsonl.

Only through the guarded launcher. Writes one new JSON file. Memory: one recording at a time, Parquet row groups.
"""
import argparse
import gc as pygc
import hashlib
import json
import os
from pathlib import Path
import random
import resource
import sys
from collections import Counter, defaultdict

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('ARROW_DEFAULT_MEMORY_POOL', 'system')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.compute as pc  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
from contributor_tools import gt21_numeric_source as src  # noqa: E402

pa.set_cpu_count(1)
pa.set_io_thread_count(1)
try:
    import ctypes
    _libc = ctypes.CDLL('libc.so.6')
    _libc.mallopt(-3, 1 << 16)
except OSError:
    _libc = None

BASE = ROOT / 'converted_datasets/reconversion_v2'
INVENTORY = BASE / 'gt21_rb01_inventory_20261123/recording_ledger.jsonl'
SOURCE_ROOTS = {'local_2024_copy_bundle': ROOT / 'contributor_tools/conversion_scripts/Gtech_2021/CAMARGO_ET_AL_J_BIOMECH_DATASET',
                'extracted_2024_copy_zip': Path('/mnt/s/locomotion_data/gt21_author_mirror_2024_extracted')}
N = 150
GRID = np.linspace(0.0, 100.0, N)
TOL = 1e-12
FTOL = 1e-9
STR_COLS = ('subject', 'source_recording_id', 'observation_id', 'reference_side', 'observation_type', 'task', 'task_id',
            'task_info', 'subject_metadata', 'held_signals')
LEGS = ('left', 'right')
OTHER = {'left': 'right', 'right': 'left'}
JOINTS = ('hip_flexion', 'knee_flexion', 'ankle_dorsiflexion')
MAX_EXAMPLES = 12


def peak_rss_mib():
    return round(max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) / 1024, 1)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


class Fails:
    def __init__(self):
        self.count = Counter()
        self.examples = defaultdict(list)

    def add(self, kind, detail):
        self.count[kind] += 1
        if len(self.examples[kind]) < MAX_EXAMPLES:
            self.examples[kind].append(detail)

    def out(self):
        return {'counts': dict(self.count), 'examples': dict(self.examples)}


# ------------------------------------------------------------------------------------------------ independent maths
def interp_missing(t, y, tq):
    """Linear interpolation; on a source sample (within 1e-9) the sample itself; missing where a bracketing sample is missing
    or the query is outside the clock."""
    t, y, tq = np.asarray(t, float), np.asarray(y, float), np.asarray(tq, float)
    fin = np.isfinite(y)
    v = np.interp(tq, t, np.where(fin, y, 0.0), left=np.nan, right=np.nan)
    bad = np.interp(tq, t, (~fin).astype(float), left=1.0, right=1.0) > 0
    out = np.where(bad, np.nan, v)
    k = np.clip(np.searchsorted(t, tq - 1e-9), 0, len(t) - 1)
    near = np.abs(t[k] - tq) <= 1e-9
    out[near] = y[k[near]]
    return out


def flag_at(t, mask, tq):
    mask = np.asarray(mask, float)
    v = np.interp(tq, t, mask) > 0
    k = np.clip(np.searchsorted(t, tq - 1e-9), 0, len(t) - 1)
    near = np.abs(t[k] - tq) <= 1e-9
    v[near] = mask[k[near]] > 0
    return v


def same_values(a, b, tol):
    """(nan pattern equal, max abs difference over finite pairs)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    pat = bool(np.array_equal(np.isnan(a), np.isnan(b)))
    ok = np.isfinite(a) & np.isfinite(b)
    d = float(np.max(np.abs(a[ok] - b[ok]))) if ok.any() else 0.0
    return pat and d <= tol, d


def runs_true(x):
    e = np.diff(np.r_[0, np.asarray(x, np.int8), 0])
    return list(zip(np.flatnonzero(e == 1), np.flatnonzero(e == -1)))


def rederive_forces(pe, row, table_t, fwd_x, fwd_z, mask, tq_list):
    """Forces (vertical, anterior, lateral in BW, mask applied) per leg at each observation's phase times from the 1 kHz plate
    source. ``tq_list`` = [(leg, tq)] -> list of dict(kind -> array). Separately written ownership, sign and mask rules."""
    channels = list(pe['plates']['channels'])
    bw = float(pe['body_weight_N'])
    base = SOURCE_ROOTS[row['source']] / row['subject'] / row['session'] / row['mode']
    fp = src.read_numeric_table(base / 'fp' / f'{row["recording"]}.mat')
    ft = np.asarray(fp['Header'], float)
    raw = {p: {k: np.asarray(fp[f'{p}_v{k}'], float) for k in 'xyz'} for p in channels}
    n = len(table_t)
    contacts = pe['plates'].get('contacts') or []
    treadmill = row['mode'] == 'treadmill'
    plate_names_owned = {'right': 'Treadmill_R', 'left': 'Treadmill_L'}

    def owned_plates_at(leg, times):
        """bool (len(times), P)."""
        out = np.zeros((len(times), len(channels)), bool)
        if treadmill:
            if plate_names_owned[leg] in channels:
                out[:, channels.index(plate_names_owned[leg])] = True
            return out
        for c in contacts:
            if c['owner'] == leg:
                lo, hi = table_t[c['a']], table_t[c['b'] - 1]
                out[(times >= lo - 1e-9) & (times <= hi + 1e-9), channels.index(c['plate'])] = True
        return out

    def owned_plates_samples(leg):
        out = np.zeros((n, len(channels)), bool)
        if treadmill:
            if plate_names_owned[leg] in channels:
                out[:, channels.index(plate_names_owned[leg])] = True
            return out
        for c in contacts:
            if c['owner'] == leg:
                out[c['a']:c['b'], channels.index(c['plate'])] = True
        return out

    def vert_sum(own, times):
        tot = np.zeros(len(times))
        for i, p in enumerate(channels):
            v = interp_missing(ft, raw[p]['y'], times)
            tot += np.where(own[:, i], np.nan_to_num(v), 0.0)
        return tot

    zsign = {}
    for leg in LEGS:
        own = owned_plates_samples(leg)
        loaded = vert_sum(own, table_t) > 1.0
        z = np.full(n, np.nan)
        for a, b in runs_true(loaded):
            xs, zs = fwd_x[a:b], fwd_z[a:b]
            ok = np.isfinite(xs) & np.isfinite(zs)
            if not ok.any():
                continue
            mx, mz = xs[ok].mean(), zs[ok].mean()
            h = np.hypot(mx, mz)
            if h > 0 and abs(mz / h) >= np.cos(np.radians(45.0)):
                z[a:b] = 1.0 if mz > 0 else -1.0
        zsign[leg] = z
    results = []
    for leg, tq in tq_list:
        own = owned_plates_at(leg, tq)
        vert = vert_sum(own, tq)
        fz = np.zeros(len(tq))
        fx = np.zeros(len(tq))
        all_nan = np.ones(len(tq), bool)
        for i, p in enumerate(channels):
            vz, vx = interp_missing(ft, raw[p]['z'], tq), interp_missing(ft, raw[p]['x'], tq)
            vy = interp_missing(ft, raw[p]['y'], tq)
            all_nan &= np.isnan(vy)
            fz += np.where(own[:, i], np.nan_to_num(vz), 0.0)
            fx += np.where(own[:, i], np.nan_to_num(vx), 0.0)
        # sign of the lab Z axis at the query times
        z = zsign[leg]
        k = np.clip(np.searchsorted(table_t, tq - 1e-9), 0, n - 1)
        near = np.abs(table_t[k] - tq) <= 1e-9
        j = np.clip(np.searchsorted(table_t, tq, side='right') - 1, 0, n - 2)
        zs = np.where(np.isnan(z[j]), z[j + 1], z[j])
        zs[near] = z[k[near]]
        loaded = vert > 1.0
        sgn = 1.0 if leg == 'left' else -1.0
        ant = zs * fz / bw
        lat = sgn * zs * fx / bw
        unl = (~loaded) & np.isnan(zs)
        ant[unl], lat[unl] = 0.0, 0.0
        vgrf = vert / bw
        vgrf[all_nan], ant[all_nan], lat[all_nan] = np.nan, np.nan, np.nan
        m = flag_at(table_t, mask[leg], tq)
        for arr in (vgrf, ant, lat):
            arr[m] = np.nan
        results.append({'vertical': vgrf, 'anterior': ant, 'lateral': lat, 'masked': m})
    return results


# ------------------------------------------------------------------------------------------------ helpers
def pass_col(name, side_ipsi, token):
    """Pass column name for an export column: '<base>_<token>_<unit>' with token ipsi/contra/left/right."""
    for tok in ('ipsi', 'contra', 'left', 'right'):
        mark = f'_{tok}_'
        if mark in name:
            leg = {'ipsi': side_ipsi, 'contra': OTHER.get(side_ipsi), 'left': 'left', 'right': 'right'}[tok]
            return name.replace(mark, f'_{leg}_', 1), leg
    return name, None


def kind(name):
    if name.startswith('grf_'):
        return 'force'
    if '_power_' in name:
        return 'power'
    return 'other'


def load_pass(pass_root, pe, columns):
    t = pq.read_table(pass_root / pe['parquet'], columns=columns, use_threads=False)
    return {c: t.column(c).to_numpy(zero_copy_only=False) for c in columns}


def read_groups(path):
    pf = pq.ParquetFile(str(path), buffer_size=0)
    for i in range(pf.metadata.num_row_groups):
        yield pf.read_row_group(i, use_threads=False)


def const_and_first(t, name, per):
    """(first value per block of ``per`` rows, all-constant bool per block) for a string column via dictionary encoding."""
    enc = pc.dictionary_encode(t.column(name).combine_chunks())
    idx = enc.indices.to_numpy(zero_copy_only=False).reshape(-1, per)
    dic = enc.dictionary.to_pylist()
    return [dic[i] for i in idx[:, 0]], (idx == idx[:, :1]).all(axis=1)


# ------------------------------------------------------------------------------------------------ one participant
def readback_subject(subject, export_root, seeds, fails, inv, partial=False):
    export_root = Path(export_root)
    proot = BASE / f'gt21_rb_pass_batch_{subject}_20261124'
    sroot = BASE / f'gt21_rb_segment_batch_{subject}_20261125'
    prows = {(r['mode'], r['recording']): r for r in jsonl(proot / 'ledger.jsonl')}
    srows = {(r['mode'], r['recording']): r for r in jsonl(sroot / 'ledger.jsonl')}
    steps_by_rec = defaultdict(list)
    for s in jsonl(sroot / 'steps.jsonl'):
        steps_by_rec[(s['mode'], s['recording'])].append(s)
    step_by_id = {s['step_id']: s for v in steps_by_rec.values() for s in v}
    mine = lambda rows: [r for r in rows if r['subject'] == subject]       # noqa: E731  (a pilot root can hold several subjects)
    obs_lines = mine(jsonl(export_root / 'observations.jsonl'))
    exclusions = mine(jsonl(export_root / 'exclusions.jsonl'))
    recs = mine(jsonl(export_root / 'recordings.jsonl'))
    summary = json.loads((export_root / 'run_summary.json').read_text())
    res = Counter()
    # ---- lineage hashes of the export files
    for name, h in summary['sha256'].items():
        if sha256(export_root / name) != h:
            fails.add('export_file_hash_differs_from_run_summary', f'{subject}/{name}')
    # ---- inventory and recordings
    inv_keys = {(m, r) for (s, m, r) in inv if s == subject}
    rec_keys = {(r['mode'], r['recording']) for r in recs}
    if (not rec_keys <= inv_keys if partial else inv_keys != rec_keys) or len(recs) != len(rec_keys):
        fails.add('recordings_differ_from_inventory', f'{subject}: inventory {len(inv_keys)} export {len(rec_keys)}')
    res['inventory_recordings'] = len(inv_keys)
    rec_by = {(r['mode'], r['recording']): r for r in recs}
    exp_by_step = defaultdict(list)
    exp_rec_excl = {}
    for e in exclusions:
        if e['step_id'] is None:
            exp_rec_excl[(e['mode'], e['recording'])] = e
        else:
            exp_by_step[e['step_id']].append(e)
    obs_phase = [o for o in obs_lines if o['table'] == 'phase']
    obs_time = [o for o in obs_lines if o['table'] == 'time']
    ids = [o['observation_id'] for o in obs_lines]
    if len(ids) != len(set(ids)):
        fails.add('duplicate_observation_id', subject)
    obs_by_rec = defaultdict(list)
    for o in obs_phase:
        obs_by_rec[o['source_recording_id']].append(o)
    time_by_rec = {o['source_recording_id']: o for o in obs_time}
    # ---- counts per recording against RB03
    for (mode, rec), r in sorted(rec_by.items()):
        sid = f'{subject}/{mode}/{rec}'
        st = steps_by_rec.get((mode, rec), [])
        se = srows.get((mode, rec))
        if se is None or se.get('steps', len(st)) != len(st):
            fails.add('rb03_ledger_steps_differ_from_steps_file', sid)
        elig = {s['step_id'] for s in st if s['disposition'] == 'eligible'}
        expo = {o['observation_id'] for o in obs_by_rec.get(sid, [])}
        export_excl = {e['step_id'] for v in exp_by_step.values() for e in v
                       if e['source_recording_id'] == sid and e['stage'] == 'RB05 export'}
        if r['status'] == 'exported':
            if expo | export_excl != elig or expo & export_excl:
                fails.add('eligible_steps_not_equal_observations_plus_export_exclusions', sid)
            pe = prows[(mode, rec)]
            if pe.get('status') != 'converted':
                fails.add('exported_recording_not_converted_in_pass', sid)
            if sid not in time_by_rec:
                fails.add('no_continuous_observation', sid)
            elif time_by_rec[sid]['rows'] != pe['n_samples']:
                fails.add('continuous_rows_differ_from_pass', sid)
        else:
            if expo or sid in time_by_rec:
                fails.add('excluded_recording_has_observations', sid)
            if (mode, rec) not in exp_rec_excl:
                fails.add('excluded_recording_not_listed', sid)
            elif prows[(mode, rec)].get('status') == 'converted':
                fails.add('recording_excluded_but_converted_in_pass', sid)
        listed = 0
        for s in st:
            es = exp_by_step.get(s['step_id'], [])
            if s['disposition'] == 'eligible' and r['status'] == 'exported':
                if s['step_id'] in expo:
                    if es:
                        fails.add('exported_step_also_excluded', s['step_id'])
                else:
                    listed += len(es) == 1
                    if len(es) != 1:
                        fails.add('step_neither_exported_nor_excluded_once', s['step_id'])
            else:
                if len(es) != 1:
                    fails.add('step_excluded_not_listed_once', s['step_id'])
                else:
                    listed += 1
                    if es[0]['reason'] != s['reason']:
                        fails.add('exclusion_reason_differs_from_rb03', s['step_id'])
        if len(expo) + listed != len(st):
            fails.add('observations_plus_exclusions_differ_from_source_steps', sid)
        res['steps_rb03'] += len(st)
        res['phase_observations'] += len(expo)
        res['exclusions_listed'] += listed
        res['eligible_steps'] += len(elig)
        if r['status'] == 'exported':
            res['recordings_exported'] += 1
        else:
            res['recordings_excluded'] += 1
    stray = set(exp_by_step) - set(step_by_id)
    if stray:
        fails.add('exclusion_for_unknown_step', f'{subject}: {len(stray)}')
    # ---- hashes of the inputs
    for r in recs:
        if r['status'] != 'exported':
            continue
        pe = prows[(r['mode'], r['recording'])]
        if sha256(proot / pe['parquet']) != r['pass_sha256']:
            fails.add('pass_parquet_hash_differs', r['source_recording_id'])
        if sha256(sroot / srows[(r['mode'], r['recording'])]['force_mask_layer']) != r['force_mask_sha256']:
            fails.add('mask_layer_hash_differs', r['source_recording_id'])
    # ---- seeded recordings for the plate-rate force re-derivation: one per mode
    rng = random.Random(seeds + int(subject[2:]))
    seeded = set()
    for mode in ('levelground', 'ramp', 'stair', 'treadmill'):
        pool = sorted(k for k, r in rec_by.items() if k[0] == mode and r['status'] == 'exported' and r['phase_observations'] > 0)
        if pool:
            seeded.add(rng.choice(pool))
    res['seeded_recordings'] = len(seeded)
    # ---- phase table
    names_cache = {}
    cur = None
    chunks = []
    seen_obs = 0
    phase_rows = 0

    def finalize(sid, chunks):
        mode, rec = sid.split('/')[1:3]
        compare_phase_recording(subject, sid, mode, rec, chunks, prows[(mode, rec)], srows[(mode, rec)], proot, sroot, step_by_id,
                                (mode, rec) in seeded, fails, res, inv.get((subject, mode, rec)))
        pygc.collect()
        if _libc is not None:
            _libc.malloc_trim(0)

    for t in read_groups(export_root / 'phase.parquet'):
        m = t.num_rows
        if m % N:
            fails.add('row_group_not_whole_observations', f'{subject}: {m}')
            continue
        ids_first, c_id = const_and_first(t, 'observation_id', N)
        meta = {}
        for c in STR_COLS:
            meta[c], ok = const_and_first(t, c, N)
            if not ok.all():
                fails.add(f'nonconstant_{c}', f'{subject}: {int((~ok).sum())} observations')
        grid = t.column('phase_ipsi').to_numpy(zero_copy_only=False).reshape(-1, N)
        if not (grid == GRID[None, :]).all():
            fails.add('phase_grid_not_linspace_0_100_150', subject)
        cs, ce = (t.column(c).to_numpy(zero_copy_only=False).reshape(-1, N) for c in ('source_start_time_s', 'source_end_time_s'))
        if not ((cs == cs[:, :1]).all() and (ce == ce[:, :1]).all()):
            fails.add('nonconstant_source_clock', subject)
        cols = {c: t.column(c).to_numpy(zero_copy_only=False).reshape(-1, N) for c in t.column_names
                if c not in STR_COLS and c not in ('phase_ipsi',) + ('source_start_time_s', 'source_end_time_s')}
        for i in range(m // N):
            sid = meta['source_recording_id'][i]
            if not sid.startswith(subject + '/'):
                continue
            phase_rows += N
            if sid != cur:
                if cur is not None:
                    finalize(cur, chunks)
                cur, chunks = sid, []
            chunks.append({'meta': {c: meta[c][i] for c in STR_COLS}, 't0': float(cs[i, 0]), 't1': float(ce[i, 0]),
                           'vals': {c: cols[c][i] for c in cols}})
            seen_obs += 1
        del cols
    if cur is not None:
        finalize(cur, chunks)
    res['phase_rows'] = phase_rows
    if phase_rows != seen_obs * N or seen_obs != len(obs_phase):
        fails.add('phase_rows_not_150_per_observation', f'{subject}: rows {phase_rows}, observations in file {seen_obs}, listed {len(obs_phase)}')
    # ---- time table
    cur, chunk = None, []
    time_rows = 0
    tcount = 0

    def fin_time(sid, parts):
        mode, rec = sid.split('/')[1:3]
        compare_time_recording(subject, sid, parts, prows[(mode, rec)], srows[(mode, rec)], proot, sroot, fails, res)
        pygc.collect()
        if _libc is not None:
            _libc.malloc_trim(0)

    for t in read_groups(export_root / 'time.parquet'):
        sids = pc.unique(t.column('source_recording_id')).to_pylist()
        if len(sids) == 1 and not sids[0].startswith(subject + '/'):
            continue
        if len(sids) == 1 and sids[0] == cur:
            time_rows += t.num_rows
            chunk.append(t)
            continue
        # split the group at recording changes
        col = t.column('source_recording_id').combine_chunks()
        enc = pc.dictionary_encode(col)
        idx = enc.indices.to_numpy(zero_copy_only=False)
        dic = enc.dictionary.to_pylist()
        starts = np.r_[0, np.flatnonzero(np.diff(idx)) + 1, len(idx)]
        for a, b in zip(starts[:-1], starts[1:]):
            sid = dic[idx[a]]
            if not sid.startswith(subject + '/'):
                continue
            time_rows += int(b - a)
            if sid != cur:
                if cur is not None:
                    fin_time(cur, chunk)
                    tcount += 1
                cur, chunk = sid, []
            chunk.append(t.slice(int(a), int(b - a)))
    if cur is not None:
        fin_time(cur, chunk)
        tcount += 1
    res['time_rows'] = time_rows
    res['continuous_observations'] = tcount
    if tcount != len(obs_time) or tcount != res['recordings_exported']:
        fails.add('continuous_observation_count', f'{subject}: file {tcount}, listed {len(obs_time)}, exported recordings {res["recordings_exported"]}')
    return dict(res)


def needed_pass_columns(token_cols):
    return sorted(set(token_cols))


def compare_phase_recording(subject, sid, mode, rec, chunks, pe, se, proot, sroot, step_by_id, seeded, fails, res, invrow):
    tab_cols = {'time_s', 'pelvis_forward_lab_x', 'pelvis_forward_lab_z', 'geometry_hold_left', 'geometry_hold_right'}
    ex_cols = list(chunks[0]['vals'])
    for c in ex_cols:
        for leg in LEGS:
            pc_, _ = pass_col(c, leg, 'x')
            if kind(c) != 'power':
                tab_cols.add(pc_)
    tab_cols |= {c for c in tab_cols if c != 'time_s'}
    for leg in LEGS:
        for j in JOINTS:
            tab_cols |= {f'{j}_moment_{leg}_Nm_kg', f'{j}_velocity_{leg}_rad_s'}
    tab = load_pass(proot, pe, sorted(c for c in tab_cols if c in pq.ParquetFile(str(proot / pe['parquet'])).schema_arrow.names))
    t = tab['time_s']
    mt = pq.read_table(sroot / se['force_mask_layer'], use_threads=False)
    mask = {leg: mt.column(f'force_missing_{leg}').to_numpy(zero_copy_only=False) for leg in LEGS}
    if not np.array_equal(mt.column('time_s').to_numpy(zero_copy_only=False), t):
        fails.add('mask_clock_differs', sid)
    tq_list, entries = [], []
    for ch in chunks:
        meta = ch['meta']
        step = step_by_id.get(meta['observation_id'])
        if step is None:
            fails.add('observation_without_rb03_step', meta['observation_id'])
            continue
        side = meta['reference_side']
        info = json.loads(meta['task_info'])
        # identity and labels
        if step['disposition'] != 'eligible' or side != step['leg'] or meta['source_recording_id'] != sid:
            fails.add('observation_identity_differs_from_step', meta['observation_id'])
        if ch['t0'] != step['start_s'] or ch['t1'] != step['end_s']:
            fails.add('source_clock_differs_from_step', meta['observation_id'])
        if info.get('authors_label') != step['label'] or info.get('step_id') != step['step_id']:
            fails.add('label_differs_from_rb03', meta['observation_id'])
        if mode == 'ramp' and info.get('incline_deg') != step['incline_deg']:
            fails.add('incline_differs_from_rb03', meta['observation_id'])
        if mode == 'stair' and info.get('step_height_m') != step['stair_height_m']:
            fails.add('stair_height_differs_from_rb03', meta['observation_id'])
        if mode == 'treadmill' and info.get('speed_values_m_s') != sorted(step['speed_values_m_s']):
            fails.add('treadmill_speed_differs_from_rb03', meta['observation_id'])
        if (('authors_rule_extended_to_left_leg' in info['flags']) != (step['rule_origin'] == 'authors_rule_extended_to_left_leg')):
            fails.add('left_extension_flag_wrong', meta['observation_id'])
        frac = step['force_missing_stance_samples'] / step['stance_samples'] if step['stance_samples'] else None
        if ('incomplete_stance_force' in info['flags']) != (frac is not None and frac >= 0.5):
            fails.add('incomplete_flag_wrong', meta['observation_id'])
        if subject == 'AB28' and not any('pelvis' in x for x in info['limits']):
            fails.add('ab28_limit_missing', meta['observation_id'])
        if subject == 'AB27' and not any('R_Thigh_Upper' in x for x in info['limits']):
            fails.add('ab27_limit_missing', meta['observation_id'])
        res['flag_left_extension'] += 'authors_rule_extended_to_left_leg' in info['flags']
        if 'incomplete_stance_force' in info['flags']:
            res['flag_incomplete_' + mode] += 1
            if mode == 'treadmill' and side == 'left':
                res['flag_incomplete_treadmill_left'] += 1
        # values
        tq = np.linspace(step['start_s'], step['end_s'], N)
        for c, v in ch['vals'].items():
            k = kind(c)
            if k == 'force':
                continue
            if k == 'power':
                continue
            pcn, _leg = pass_col(c, side, 'x')
            exp = interp_missing(t, tab[pcn], tq)
            ok, d = same_values(v, exp, TOL)
            res['value_columns_compared'] += 1
            res['max_abs_diff_interpolated'] = max(res.get('max_abs_diff_interpolated', 0.0), d if np.isfinite(d) else 1e9)
            if not ok:
                fails.add('value_differs_from_pass', f'{meta["observation_id"]} {c} max diff {d}')
        for token, leg in (('ipsi', side), ('contra', OTHER[side])):
            for j in JOINTS:
                mom = ch['vals'][f'{j}_moment_{token}_Nm_kg']
                vel = ch['vals'][f'{j}_velocity_{token}_rad_s']
                pw = ch['vals'][f'{j}_power_{token}_W_kg']
                expp = np.where(np.isfinite(mom) & np.isfinite(vel), mom * vel, np.nan)
                same = np.array_equal(np.isnan(pw), np.isnan(expp)) and np.array_equal(pw[np.isfinite(pw)], expp[np.isfinite(expp)])
                res['power_rows_checked'] += N
                if not same:
                    fails.add('phase_power_not_moment_times_speed', f'{meta["observation_id"]} {j} {token}')
            # forces: masked samples missing, ends equal the pass table
            m = flag_at(t, mask[leg], tq)
            for kk in ('vertical', 'anterior', 'lateral'):
                f = ch['vals'][f'grf_{kk}_{token}_BW']
                if not np.isnan(f[m]).all():
                    fails.add('masked_force_not_missing', f'{meta["observation_id"]} {kk} {token}')
                if np.any(np.isnan(f) & ~m) and pe['plates']['channels']:
                    res['force_missing_not_from_mask'] += int((np.isnan(f) & ~m).sum())
                for idx in (0, N - 1):
                    tab_v = tab[f'grf_{kk}_{leg}_BW'][np.searchsorted(t, tq[idx] - 1e-9)] if abs(t[np.clip(np.searchsorted(t, tq[idx] - 1e-9), 0, len(t) - 1)] - tq[idx]) <= 1e-9 else None
                    if tab_v is None:
                        continue
                    i_t = np.searchsorted(t, tq[idx] - 1e-9)
                    exp_v = np.nan if mask[leg][i_t] else tab_v
                    got = f[idx]
                    res['force_end_samples_compared'] += 1
                    if not ((np.isnan(exp_v) and np.isnan(got)) or (np.isfinite(exp_v) and np.isfinite(got) and abs(exp_v - got) <= FTOL)):
                        fails.add('force_end_sample_differs_from_pass', f'{meta["observation_id"]} {kk} {token} idx {idx}: {got} vs {exp_v}')
            tq_list.append((leg, tq))
            entries.append((meta['observation_id'], token, leg))
        # held signals
        held = json.loads(meta['held_signals'])
        none_finite = {c for c, v in ch['vals'].items() if not np.isfinite(v).any()}
        if set(held) != none_finite or any(not isinstance(x, str) or not x for x in held.values()):
            fails.add('held_signals_differ_from_missing_columns', meta['observation_id'])
        res['phase_observations_checked'] += 1
    # independent plate-rate force re-derivation for seeded recordings
    if seeded and pe['plates']['channels'] and invrow is not None:
        got = rederive_forces(pe, invrow, t, tab['pelvis_forward_lab_x'], tab['pelvis_forward_lab_z'], mask, tq_list)
        by_obs = {ch['meta']['observation_id']: ch for ch in chunks}
        for (oid, token, leg), exp in zip(entries, got):
            ch = by_obs[oid]
            for kk in ('vertical', 'anterior', 'lateral'):
                ok, d = same_values(ch['vals'][f'grf_{kk}_{token}_BW'], exp[kk], FTOL)
                res['seeded_force_columns_compared'] += 1
                res['max_abs_diff_seeded_force_BW'] = max(res.get('max_abs_diff_seeded_force_BW', 0.0), d if np.isfinite(d) else 1e9)
                if not ok:
                    fails.add('plate_rate_force_differs_from_independent_rederivation', f'{oid} {kk} {token} max diff {d}')
        res['seeded_recordings_rederived'] += 1
    elif seeded:
        res['seeded_recordings_without_plates'] += 1
    del tab, mask
    chunks.clear()


def compare_time_recording(subject, sid, parts, pe, se, proot, sroot, fails, res):
    mode, rec = sid.split('/')[1:3]
    tt = pa.concat_tables(parts)
    n = tt.num_rows
    if n != pe['n_samples']:
        fails.add('time_rows_differ_from_pass', sid)
    meta_ok = all(len(pc.unique(tt.column(c))) == 1 for c in STR_COLS)
    if not meta_ok:
        fails.add('time_metadata_not_constant', sid)
    if tt.column('reference_side')[0].as_py() != 'none' or tt.column('observation_type')[0].as_py() != 'continuous_recording':
        fails.add('time_identity_wrong', sid)
    got = {c: tt.column(c).to_numpy(zero_copy_only=False) for c in tt.column_names if c not in STR_COLS}
    pschema = pq.ParquetFile(str(proot / pe['parquet'])).schema_arrow.names
    want = set()
    for c in got:
        if c in ('time_s', 'source_start_time_s', 'source_end_time_s'):
            continue
        if kind(c) != 'power':
            want.add(pass_col(c, 'left', 'x')[0])
    want |= {'time_s'}
    tab = load_pass(proot, pe, sorted(c for c in want if c in pschema))
    mt = pq.read_table(sroot / se['force_mask_layer'], use_threads=False)
    if not np.array_equal(got['time_s'], tab['time_s']):
        fails.add('time_clock_differs_from_pass', sid)
    held = json.loads(tt.column('held_signals')[0].as_py())
    none_finite = set()
    for c, v in got.items():
        if c in ('time_s', 'source_start_time_s', 'source_end_time_s'):
            continue
        if not np.isfinite(v).any():
            none_finite.add(c)
        if kind(c) == 'power':
            continue
        pcn, leg = pass_col(c, 'left', 'x')
        exp = np.array(tab[pcn], float)
        if kind(c) == 'force':
            exp[mt.column(f'force_missing_{leg}').to_numpy(zero_copy_only=False)] = np.nan
        ok, d = same_values(v, exp, 0.0)
        res['time_columns_compared'] += 1
        if not ok:
            fails.add('time_value_differs_from_pass', f'{sid} {c} max diff {d}')
    for leg in LEGS:
        for j in JOINTS:
            mom, vel, pw = got[f'{j}_moment_{leg}_Nm_kg'], got[f'{j}_velocity_{leg}_rad_s'], got[f'{j}_power_{leg}_W_kg']
            expp = np.where(np.isfinite(mom) & np.isfinite(vel), mom * vel, np.nan)
            res['power_rows_checked'] += n
            if not (np.array_equal(np.isnan(pw), np.isnan(expp)) and np.array_equal(pw[np.isfinite(pw)], expp[np.isfinite(expp)])):
                fails.add('time_power_not_moment_times_speed', f'{sid} {j} {leg}')
    if set(held) != none_finite or any(not isinstance(x, str) or not x for x in held.values()):
        fails.add('time_held_signals_differ_from_missing_columns', sid)
    res['time_recordings_checked'] += 1
    del tt, got, tab


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--export-root-template', default='converted_datasets/reconversion_v2/gt21_rb05_export_{subject}_r1')
    p.add_argument('--subjects', nargs='+', required=True)
    p.add_argument('--seed', type=int, default=20261201)
    p.add_argument('--out', required=True)
    p.add_argument('--export-root', help='one explicit root (pilot); the subjects are taken from observations')
    args = p.parse_args(argv)
    out = Path(args.out)
    inv = {}
    for line in INVENTORY.read_text().splitlines():
        r = json.loads(line)
        inv[(r['subject'], r['mode'], r['recording'])] = r
    fails = Fails()
    per = {}
    for subject in args.subjects:
        root = args.export_root or args.export_root_template.format(subject=subject)
        per[subject] = readback_subject(subject, ROOT / root, args.seed, fails, inv, partial=bool(args.export_root))
        print(f'{subject} readback done failures={sum(fails.count.values())} peak_rss_mib={peak_rss_mib()}', file=sys.stderr, flush=True)
    total = Counter()
    for v in per.values():
        for k, x in v.items():
            if k.startswith('max_abs'):
                total[k] = max(total.get(k, 0.0), x)
            else:
                total[k] += x
    result = {'status': 'passed' if not fails.count else 'failed', 'scientific_approval': False, 'subjects': args.subjects,
              'failures': fails.out(), 'totals': dict(total), 'per_subject': per, 'seed': args.seed, 'peak_rss_mib': peak_rss_mib(),
              'tolerances': {'interpolated_values_abs': TOL, 'plate_rate_forces_BW': FTOL, 'continuous_values': 'bit equal'},
              'code_sha256': {'contributor_tools/run_gt21_rb_export_readback.py': sha256(Path(__file__)),
                              'contributor_tools/gt21_numeric_source.py': sha256(ROOT / 'contributor_tools/gt21_numeric_source.py')}}
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
        f.write('\n')
    return 0 if not fails.count else 2


if __name__ == '__main__':
    raise SystemExit(main())
