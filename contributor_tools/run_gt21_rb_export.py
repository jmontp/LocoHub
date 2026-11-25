"""GT21-RB05 export runner (Python only).

Subcommands
  run   One participant (--subject) or named recordings (--record SUBJECT/MODE/RECORDING, repeatable). Reads, one recording at a
        time: the merged-pass continuous table and its ledger entry (RB02/RB04), the RB03 steps, dispositions and force-mask layer,
        the RB01/RB03 authors' fields and subject info, and (for phase forces) the 1 kHz plate source table. Writes a NEW root:
          phase.parquet         150-sample observations of every rule-A eligible step (one leg per observation)
          time.parquet          one continuous_recording observation per converted recording
          observations.jsonl    one line per observation with lineage
          exclusions.jsonl      every step or recording left out, with its stage and reason
          recordings.jsonl      every recording with its disposition and counts
          README.md, run_summary.json
  spec  Writes the guarded-launcher job spec.

Rules, column mapping and the phase-force decision are in gt21_rb_export.py. Run only through
``python3 -m contributor_tools.guarded_launcher run SPEC.json``. Memory: one recording resident; Parquet row groups of at most
3000 (phase) or 4096 (time) rows; one Arrow thread. No scientific approval is claimed.
"""
import argparse
import gc as pygc
import json
import os
from pathlib import Path
import random
import sys
from collections import Counter

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
os.environ.setdefault('ARROW_DEFAULT_MEMORY_POOL', 'system')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
from contributor_tools import gt21_numeric_source as src  # noqa: E402
from contributor_tools import gt21_rb_export as ex  # noqa: E402
from contributor_tools import gt21_rb_pass as rb  # noqa: E402
from contributor_tools.run_gt21_rb_pass import (INVENTORY, ROOTS, _json_default, load_inventory, peak_rss_mib,  # noqa: E402
                                                sha256_file)

pa.set_cpu_count(1)


def _malloc_setup():
    """Large arrays go to mmap and are returned to the system when freed (the 768 MiB address-space cap otherwise runs out
    after several treadmill recordings in one process through heap fragmentation)."""
    try:
        import ctypes
        libc = ctypes.CDLL('libc.so.6')
        libc.mallopt(-3, 1 << 16)       # M_MMAP_THRESHOLD
        return libc
    except OSError:
        return None


LIBC = _malloc_setup()
pa.set_io_thread_count(1)
BASE = 'converted_datasets/reconversion_v2'
AUTHORS = f'{BASE}/gt21_rb03_authors_fields_20261125'
PASS_ROOT = f'{BASE}/gt21_rb_pass_batch_{{subject}}_20261124'
SEG_ROOT = f'{BASE}/gt21_rb_segment_batch_{{subject}}_20261125'
CODE = ('contributor_tools/gt21_rb_export.py', 'contributor_tools/run_gt21_rb_export.py', 'contributor_tools/gt21_rb_pass.py',
        'contributor_tools/run_gt21_rb_pass.py', 'contributor_tools/gt21_numeric_source.py')
SCHEMA_ID = 'locohub.gt21_rb05/1'
PHASE_ROWS_PER_GROUP = 3000
TIME_ROWS_PER_GROUP = 4096
LEGS = ('left', 'right')
PASS_EXTRA = ('time_s', 'pelvis_forward_lab_x', 'pelvis_forward_lab_z', 'geometry_hold_left', 'geometry_hold_right')
FORCE_RECON_TOL = 1e-9
SUBJECTS = ('AB06', 'AB07', 'AB08', 'AB09', 'AB10', 'AB11', 'AB12', 'AB13', 'AB14', 'AB15', 'AB16', 'AB17', 'AB18', 'AB19', 'AB20',
            'AB21', 'AB23', 'AB24', 'AB25', 'AB27', 'AB28', 'AB30')


class ExportError(RuntimeError):
    pass


def jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def phase_names():
    return ex.role_columns(('ipsi', 'contra'))


def time_names():
    return ex.role_columns(('left', 'right'))


def make_schema(index_name, names):
    fields = [pa.field(n, pa.string()) for n in ex.IDENTITY] + [pa.field(index_name, pa.float64())]
    fields += [pa.field(n, pa.float64()) for n in ex.CLOCKS] + [pa.field('held_signals', pa.string())]
    fields += [pa.field(n, pa.float64()) for n in names]
    return pa.schema(fields, metadata={b'schema': SCHEMA_ID.encode()})


class Writers:
    def __init__(self, out_root):
        self.pnames, self.tnames = phase_names(), time_names()
        self.pschema = make_schema('phase_ipsi', self.pnames)
        self.tschema = make_schema('time_s', self.tnames)
        self.phase = pq.ParquetWriter(str(out_root / 'phase.parquet'), self.pschema, compression='zstd')
        self.time = pq.ParquetWriter(str(out_root / 'time.parquet'), self.tschema, compression='zstd')
        self.buf = []

    def close(self):
        self.flush()
        self.phase.close()
        self.time.close()

    def flush(self):
        if not self.buf:
            return
        n = ex.N_PHASE
        grid = np.linspace(0.0, 100.0, n)
        arrays = []
        for name in ex.IDENTITY + ('phase_ipsi',) + ex.CLOCKS + ('held_signals',) + tuple(self.pnames):
            if name in ex.IDENTITY or name == 'held_signals':
                vals = [o['meta'][name] if name != 'held_signals' else o['held_json'] for o in self.buf]
                arrays.append(pa.array([v for v in vals for _ in range(n)], type=pa.string()))
            elif name == 'phase_ipsi':
                arrays.append(pa.array(np.tile(grid, len(self.buf)), type=pa.float64()))
            elif name in ex.CLOCKS:
                arrays.append(pa.array(np.repeat([o['meta'][name] for o in self.buf], n), type=pa.float64()))
            else:
                arrays.append(pa.array(np.concatenate([o['values'][name] for o in self.buf]), type=pa.float64()))
        self.phase.write_table(pa.Table.from_arrays(arrays, schema=self.pschema), row_group_size=PHASE_ROWS_PER_GROUP)
        self.buf = []

    def add_phase(self, obs):
        self.buf.append(obs)
        if len(self.buf) * ex.N_PHASE >= PHASE_ROWS_PER_GROUP:
            self.flush()

    def write_time(self, meta, held_json, time_s, signals):
        n = len(time_s)
        for lo in range(0, n, TIME_ROWS_PER_GROUP):
            hi = min(lo + TIME_ROWS_PER_GROUP, n)
            m = hi - lo
            arrays = []
            for name in ex.IDENTITY + ('time_s',) + ex.CLOCKS + ('held_signals',) + tuple(self.tnames):
                if name in ex.IDENTITY:
                    arrays.append(pa.repeat(pa.scalar(meta[name], pa.string()), m))
                elif name == 'held_signals':
                    arrays.append(pa.repeat(pa.scalar(held_json, pa.string()), m))
                elif name == 'time_s':
                    arrays.append(pa.array(time_s[lo:hi], type=pa.float64()))
                elif name in ex.CLOCKS:
                    arrays.append(pa.repeat(pa.scalar(meta[name], pa.float64()), m))
                else:
                    arrays.append(pa.array(signals[name][lo:hi], type=pa.float64()))
            self.time.write_table(pa.Table.from_arrays(arrays, schema=self.tschema), row_group_size=TIME_ROWS_PER_GROUP)


# ------------------------------------------------------------------------------------------------ one recording
def pass_columns_needed():
    names = set(PASS_EXTRA) | {ex.PELVIS}
    for leg in LEGS:
        for _n, _k, s, _l in ex.source_columns(leg, leg):
            if s:
                names.add(s)
    return sorted(names)


def read_pass(root, entry, extra=()):
    want = pass_columns_needed() + list(extra)
    t = pq.read_table(root / entry['parquet'], columns=want, use_threads=False)
    return {c: t.column(c).to_numpy(zero_copy_only=False) for c in want}


def read_mask(seg_root, entry):
    t = pq.read_table(seg_root / entry['force_mask_layer'], use_threads=False)
    return {c: t.column(c).to_numpy(zero_copy_only=False) for c in t.column_names}


def build_plate_state(row, pe, table, roots):
    """Plate source and ownership for one recording: (state dict or None). Reconstructs the 200 Hz forces of the pass from the
    ledger contacts and the source plates and compares them with the stored table (the integrity check)."""
    channels = list(pe['plates']['channels'])
    if not channels:
        return None
    base = roots[row['source']] / row['subject'] / row['session'] / row['mode']
    fp = src.read_numeric_table(base / 'fp' / f'{row["recording"]}.mat')
    ft = np.asarray(fp['Header'], float)
    t = table['time_s']
    n = len(t)
    idx = {p: i for i, p in enumerate(channels)}
    raw = [{'vx': np.asarray(fp[f'{p}_vx'], float), 'vy': np.asarray(fp[f'{p}_vy'], float), 'vz': np.asarray(fp[f'{p}_vz'], float)}
           for p in channels]
    plates200 = [{'vx': rb.interp_to_clock(t, ft, r['vx']), 'vy': rb.interp_to_clock(t, ft, r['vy']),
                  'vz': rb.interp_to_clock(t, ft, r['vz']), 'cop': np.full((n, 3), np.nan)} for r in raw]
    fwd = np.stack([table['pelvis_forward_lab_x'], np.zeros(n), table['pelvis_forward_lab_z']], axis=1)
    state = {'channels': channels, 'idx': idx, 'ft': ft, 'raw': raw, 'zsign': {}, 'own200': {}, 'contacts': pe['plates'].get('contacts') or [],
             'treadmill': row['mode'] == 'treadmill', 'recon_max_abs_diff': 0.0}
    for leg in LEGS:
        if state['treadmill']:
            own, _ = rb.treadmill_ownership(channels, n)
            own = own[leg]
        else:
            own = ex.own_from_contacts(n, state['contacts'], idx, leg, len(channels))
        state['own200'][leg] = own
        f0 = rb.foot_forces(own, plates200, pe['body_weight_N'], np.full(n, np.nan), leg)
        zs, _rep = rb.contact_zsign(f0['loaded'], fwd)
        f = rb.foot_forces(own, plates200, pe['body_weight_N'], zs, leg)
        state['zsign'][leg] = zs
        for kind, key in (('vertical', 'vertical_BW'), ('anterior', 'anterior_BW'), ('lateral', 'lateral_BW')):
            a, b = f[key], table[f'grf_{kind}_{leg}_BW']
            if not np.array_equal(np.isnan(a), np.isnan(b)):
                state['recon_max_abs_diff'] = float('inf')
            else:
                ok = np.isfinite(a)
                d = float(np.max(np.abs(a[ok] - b[ok]))) if ok.any() else 0.0
                state['recon_max_abs_diff'] = max(state['recon_max_abs_diff'], d)
    del plates200
    if not state['recon_max_abs_diff'] <= FORCE_RECON_TOL:
        raise ExportError(f'200 Hz force reconstruction differs from the pass table by {state["recon_max_abs_diff"]}')
    return state


def phase_forces(state, table, mask, pe, leg, tq, loc):
    """Vertical, anterior, lateral force in BW at the phase times from the 1 kHz plate, mask applied (NaN)."""
    P = len(state['channels'])
    t = table['time_s']
    if state['treadmill']:
        own = np.repeat(state['own200'][leg][:1], len(tq), axis=0)
    else:
        own = ex.own_at(t, state['contacts'], state['idx'], leg, tq, P)
    ft = state['ft']
    plates = [{'vx': rb.interp_to_clock(tq, ft, r['vx']), 'vy': rb.interp_to_clock(tq, ft, r['vy']),
               'vz': rb.interp_to_clock(tq, ft, r['vz']), 'cop': np.full((len(tq), 3), np.nan)} for r in state['raw']]
    zs = ex.zsign_at(state['zsign'][leg], loc)
    f = rb.foot_forces(own, plates, pe['body_weight_N'], zs, leg)
    m = ex.mask_at(mask[f'force_missing_{leg}'], loc)
    out = {}
    for kind, key in (('vertical', 'vertical_BW'), ('anterior', 'anterior_BW'), ('lateral', 'lateral_BW')):
        a = np.array(f[key], float)
        a[m] = np.nan
        out[kind] = a
    return out, m


def process_recording(row, step_rows, pe, seg_entry, pass_root, seg_root, info, meta, roots, writers, report):
    subject, mode, rec = row['subject'], row['mode'], row['recording']
    sid = f'{subject}/{mode}/{rec}'
    weight_kg, bw = float(pe['weight_kg']), float(pe['body_weight_N'])
    table = read_pass(pass_root, pe)
    mask = read_mask(seg_root, seg_entry)
    t = table['time_s']
    if not np.array_equal(mask['time_s'], t):
        raise ExportError(f'{sid}: force-mask clock differs from the pass clock')
    n = len(t)
    eligible = [s for s in step_rows if s['disposition'] == 'eligible']
    state = build_plate_state(row, pe, table, roots) if eligible else None
    plate_channels = bool(pe['plates']['channels'])
    stats = Counter()
    recon = state['recon_max_abs_diff'] if state else None
    # whole-recording finite flags and power
    full_pass = {}
    for leg in LEGS:
        for _n, kind, s, _l in ex.source_columns(leg, leg):
            if s:
                full_pass[s] = table[s]
    power_full = {}
    for leg in LEGS:
        for joint in ex.JOINTS:
            power_full[f'{joint}_power_{leg}_W_kg'] = ex.power_from(table[f'{joint}_moment_{leg}_Nm_kg'], table[f'{joint}_velocity_{leg}_rad_s'])
    smeta = ex.dumps(ex.subject_meta(info, weight_kg, bw))
    limits = ex.step_limits(subject)
    finite_rec = {}

    def rec_finite(key, arr):
        if key not in finite_rec:
            finite_rec[key] = bool(np.isfinite(arr).any())
        return finite_rec[key]

    # ------------------------------------------------------------ phase observations
    obs_lines = []
    for s in step_rows:
        base_line = {'step_id': s['step_id'], 'subject': subject, 'mode': mode, 'recording': rec, 'leg': s['leg'],
                     'start_s': s['start_s'], 'end_s': s['end_s'], 'rule_origin': s.get('rule_origin')}
        if s['disposition'] != 'eligible':
            report['exclusions'].append({**base_line, 'source_recording_id': sid, 'stage': 'RB03 segmentation', 'reason': s['reason'],
                                         'disposition': s['disposition']})
            stats['excluded_rb03'] += 1
            continue
        t0, t1 = float(s['start_s']), float(s['end_s'])
        if t0 < t[0] - ex.TOL_S or t1 > t[-1] + ex.TOL_S:
            report['exclusions'].append({**base_line, 'source_recording_id': sid, 'stage': 'RB05 export',
                                         'reason': 'step_outside_pass_clock', 'disposition': 'excluded'})
            stats['excluded_export'] += 1
            continue
        tq = np.linspace(t0, t1, ex.N_PHASE)
        loc = ex.locate(t, tq)
        i0, i1 = int(np.searchsorted(t, t0 - ex.TOL_S)), int(np.searchsorted(t, t1 + ex.TOL_S, side='right'))
        task, tid, tinfo = ex.classify(s)
        flag_inc, frac = ex.stance_flags(s)
        flags = []
        if s.get('rule_origin') == ex.FLAG_LEFT_EXT:
            flags.append(ex.FLAG_LEFT_EXT)
        if flag_inc:
            flags.append(flag_inc)
        side = s['leg']
        values, held, kinds, fin_map = {}, {}, {}, {}
        hold_frac = {}
        force_by_leg = {}
        mask_all = {}
        for token, leg in (('ipsi', side), ('contra', ex.OTHER[side])):
            hold_win = table[f'geometry_hold_{leg}'][i0:i1] > 0
            hold_frac[token] = float(hold_win.mean()) if len(hold_win) else None
            hold_all = bool(hold_win.all()) if len(hold_win) else False
            if state is not None:
                force_by_leg[leg], mk = phase_forces(state, table, mask, pe, leg, tq, loc)
                mask_all[leg] = bool(mk.all())
            else:
                mk = ex.mask_at(mask[f'force_missing_{leg}'], loc)
                mask_all[leg] = bool(mk.all())
            for name, kind, scol, _l in ex.source_columns(token, leg):
                if kind == 'power':
                    continue
                if kind == 'force':
                    k = name.split('_')[1]
                    if state is not None:
                        arr = force_by_leg[leg][k]
                    else:
                        arr = ex.sample_at(table[scol], loc)
                        arr[mk] = np.nan
                else:
                    arr = ex.sample_at(table[scol], loc)
                values[name] = arr
                kinds[name] = (kind, leg, hold_all)
                fin_map[name] = rec_finite(scol, full_pass[scol])
            for name, kind, scol, _l in ex.source_columns(token, leg):
                if kind == 'power':
                    mname, vname = ex.power_inputs(name)
                    values[name] = ex.power_from(values[mname], values[vname])
                    kinds[name] = (kind, leg, hold_all)
                    fin_map[name] = rec_finite('power|' + name.replace(token, 'X', 1) + leg,
                                               power_full[name.split('_power_')[0] + f'_power_{leg}_W_kg'])
        values[ex.PELVIS] = ex.sample_at(table[ex.PELVIS], loc)
        kinds[ex.PELVIS] = ('pelvis', None, False)
        fin_map[ex.PELVIS] = rec_finite(ex.PELVIS, table[ex.PELVIS])
        order = phase_names()
        values = {k: values[k] for k in order}
        for name in order:
            kind, leg, hold_all = kinds[name]
            arr = values[name]
            fin_rec = fin_map[name]
            reason = ex.held_reason(name, kind, leg, bool(np.isfinite(arr).any()), fin_rec, hold_all,
                                    mask_all.get(leg, False), plate_channels)
            if reason is not None:
                held[name] = reason
        tinfo.update({'source_recording': sid, 'step_id': s['step_id'], 'rb03_label_windows': s.get('labels_overlapped'),
                      'rule_origin': s.get('rule_origin'), 'flags': flags, 'limits': limits,
                      'stance_samples': s.get('stance_samples'), 'force_missing_stance_samples': s.get('force_missing_stance_samples'),
                      'force_missing_stance_fraction': frac, 'geometry_held_fraction_ipsi': hold_frac['ipsi'],
                      'geometry_held_fraction_contra': hold_frac['contra'], 'pass_rows_in_step': i1 - i0,
                      'phase_force_source': ('1 kHz plate at the phase times' if state is not None else 'no plate channel: pass table (missing)'),
                      'contralateral_timing': 'contra columns cover the same absolute time span as the ipsi leg; no 50 percent shift is assumed',
                      'step_start_s': t0, 'step_end_s': t1, 'source_gc_start_index': s.get('gc_start_index'),
                      'source_gc_end_index': s.get('gc_end_index')})
        if flag_inc:
            tinfo['incomplete_note'] = ('at least half of the stance samples have no force (no plate under the foot carrying 20 N); '
                                        'the force profile of this step is incomplete')
        obs_meta = {'subject': subject, 'source_recording_id': sid, 'observation_id': s['step_id'], 'reference_side': side,
                    'observation_type': 'individual_cycle', 'task': task, 'task_id': tid, 'task_info': ex.dumps(tinfo),
                    'subject_metadata': smeta, 'source_start_time_s': t0, 'source_end_time_s': t1}
        writers.add_phase({'meta': obs_meta, 'values': values, 'held_json': ex.dumps(held)})
        stats['phase'] += 1
        stats['flag_' + (flag_inc or 'none')] += 1
        if ex.FLAG_LEFT_EXT in flags:
            stats['left_extension'] += 1
        obs_lines.append({'subject': subject, 'source_recording_id': sid, 'observation_id': s['step_id'], 'reference_side': side,
                          'observation_type': 'individual_cycle', 'table': 'phase', 'rows': ex.N_PHASE, 'mode': mode, 'task': task,
                          'task_id': tid, 'flags': flags, 'held_signals': sorted(held), 'start_s': t0, 'end_s': t1,
                          'force_missing_stance_fraction': frac})
    # ------------------------------------------------------------ continuous time observation
    values, held = {}, {}
    for token in LEGS:
        leg = token
        hold = table[f'geometry_hold_{leg}'] > 0
        for name, kind, scol, _l in ex.source_columns(token, leg):
            if kind == 'power':
                continue
            arr = np.array(table[scol], float)
            if kind == 'force':
                arr[mask[f'force_missing_{leg}']] = np.nan
            values[name] = arr
        for name, kind, scol, _l in ex.source_columns(token, leg):
            if kind == 'power':
                mname, vname = ex.power_inputs(name)
                values[name] = ex.power_from(values[mname], values[vname])
    values[ex.PELVIS] = np.array(table[ex.PELVIS], float)
    order = time_names()
    for name in order:
        arr = values[name]
        if np.isfinite(arr).any():
            continue
        kind = ex.kind_of(name)
        leg = 'left' if '_left_' in name else ('right' if '_right_' in name else None)
        hold_all = bool((table[f'geometry_hold_{leg}'] > 0).all()) if leg else False
        reason = ex.held_reason(name, kind, leg, False, False, hold_all, bool(mask[f'force_missing_{leg}'].any()) if leg else False,
                                plate_channels)
        held[name] = reason
    tfam, tid, tinfo = ('level_walking' if mode == 'treadmill' else 'continuous_recording'), f'{mode}_recording', {}
    tinfo.update({'source_mode': mode, 'source_recording': sid, 'export_scope': 'continuous_and_steps' if stats['phase'] else 'continuous_only',
                  'steps_exported': stats['phase'], 'limits': limits, 'surface': mode, 'time_scope': 'continuous_trial',
                  'sampling_rate_hz': round(1.0 / float(pe['median_dt_s']), 3),
                  'force_note': 'forces are the pass values with the stance force mask applied (missing, never 0)',
                  'label_note': 'continuous recording: the task family states only what the recording mode determines'})
    oid = f'{sid}/continuous'
    tmeta = {'subject': subject, 'source_recording_id': sid, 'observation_id': oid, 'reference_side': 'none',
             'observation_type': 'continuous_recording', 'task': 'continuous_recording', 'task_id': f'{mode}_recording',
             'task_info': ex.dumps(tinfo), 'subject_metadata': smeta, 'source_start_time_s': float(t[0]),
             'source_end_time_s': float(t[-1])}
    writers.write_time(tmeta, ex.dumps(held), t, values)
    obs_lines.append({'subject': subject, 'source_recording_id': sid, 'observation_id': oid, 'reference_side': 'none',
                      'observation_type': 'continuous_recording', 'table': 'time', 'rows': int(n), 'mode': mode,
                      'held_signals': sorted(held), 'start_s': float(t[0]), 'end_s': float(t[-1])})
    report['observations'].extend(obs_lines)
    pass_sha = sha256_file(pass_root / pe['parquet'])
    mask_sha = sha256_file(seg_root / seg_entry['force_mask_layer'])
    report['recordings'].append({'subject': subject, 'mode': mode, 'recording': rec, 'source_recording_id': sid, 'status': 'exported',
                                 'rows': int(n), 'steps_rb03': len(step_rows), 'eligible_steps': len(eligible),
                                 'phase_observations': stats['phase'], 'excluded_rb03': stats['excluded_rb03'],
                                 'excluded_export': stats['excluded_export'], 'continuous_observations': 1,
                                 'plate_channels': pe['plates']['channels'], 'force_reconstruction_max_abs_diff_BW': recon,
                                 'incomplete_stance_force': stats['flag_' + ex.FLAG_INCOMPLETE],
                                 'left_leg_extension': stats['left_extension'], 'pass_parquet': pe['parquet'], 'pass_sha256': pass_sha,
                                 'force_mask_sha256': mask_sha})
    return stats


def readme_text(subject):
    return '\n'.join([
        f'# GT21 export, {subject} (GT21-RB05, unreviewed)', '',
        '`phase.parquet`: one 150-sample observation (0 to 100 percent inclusive) for every rule-A eligible step of either leg; '
        '`time.parquet`: one continuous 200 Hz observation per converted recording (left and right columns). Identity is '
        '(subject, source_recording_id, observation_id, reference_side); observation_id is the RB03 step id.', '',
        '## Values',
        '- Angles, speeds, moments and foot-frame pressure point are the merged-pass values (RB02/RB04), linearly interpolated '
        'on the 200 Hz clock to the phase times; a value is missing where either neighbouring sample is missing.',
        '- Phase forces are re-derived from the 1 kHz plate at the phase times (same plate ownership, sign and body-weight rules '
        'as the pass), not from the 200 Hz table. The stance force mask (stance with no plate carrying 20 N under the foot) '
        'makes force missing, never 0.',
        '- Power is moment x joint speed row by row (D-REF-5), missing where either factor is missing.',
        '- Body-weight columns use the declared Weight in kg x 9.81 (subject_metadata).', '',
        '## Labels',
        'Rule A labels (the authors\' STRIDES.m rule), ramp incline, stair height and treadmill speed come from the authors\' '
        'exports only. Left-leg steps use the same rule (flag authors_rule_extended_to_left_leg).', '',
        '## Flags and limits (task_info)',
        '- incomplete_stance_force: at least half of the step\'s stance samples have no force.',
        f'- {ex.LIMIT_AB28}', f'- {ex.LIMIT_AB27}', '',
        '`held_signals` lists every column with no finite value in the observation and why. Held (bad-fit) frames are missing '
        'inside observations; `geometry_held_fraction_*` in task_info gives the share.'
    ]) + '\n'


def run(args):
    out_root = Path(args.out_root)
    if out_root.exists() and any(out_root.iterdir()):
        raise SystemExit(f'{out_root} is not empty; outputs go to a new root')
    out_root.mkdir(parents=True, exist_ok=True)
    inv = load_inventory()
    records = list(args.record or [])
    if args.subject:
        records += [f'{sj}/{m}/{r}' for (sj, m, r) in sorted(inv) if sj == args.subject]
    if not records:
        raise SystemExit('no recordings named')
    report = {'exclusions': [], 'observations': [], 'recordings': []}
    cache = {}
    writers = Writers(out_root)
    totals = Counter()
    errors = []
    try:
        for item in records:
            subject, mode, name = item.split('/')
            row = inv.get((subject, mode, name))
            if row is None:
                raise SystemExit(f'{item} is not in the inventory')
            if subject not in cache:
                proot = ROOT / PASS_ROOT.format(subject=subject)
                sroot = ROOT / SEG_ROOT.format(subject=subject)
                prows = {(r['mode'], r['recording']): r for r in jsonl(proot / 'ledger.jsonl')}
                srows = {(r['mode'], r['recording']): r for r in jsonl(sroot / 'ledger.jsonl')}
                steps = {}
                for s in jsonl(sroot / 'steps.jsonl'):
                    steps.setdefault((s['mode'], s['recording']), []).append(s)
                info = json.loads((ROOT / AUTHORS / subject / f'subject_info_{subject}.json').read_text())
                cache[subject] = (proot, sroot, prows, srows, steps, info)
            proot, sroot, prows, srows, steps, info = cache[subject]
            pe, se, st = prows[(mode, name)], srows[(mode, name)], steps.get((mode, name), [])
            if se.get('steps', len(st)) != len(st):
                raise ExportError(f'{item}: RB03 ledger step count differs from steps.jsonl')
            sid = f'{subject}/{mode}/{name}'
            if pe.get('status') != 'converted':
                for s in st:
                    report['exclusions'].append({'step_id': s['step_id'], 'subject': subject, 'mode': mode, 'recording': name,
                                                 'leg': s['leg'], 'start_s': s['start_s'], 'end_s': s['end_s'],
                                                 'source_recording_id': sid, 'stage': 'RB03 segmentation', 'reason': s['reason'],
                                                 'disposition': s['disposition'], 'rule_origin': s.get('rule_origin')})
                report['exclusions'].append({'step_id': None, 'subject': subject, 'mode': mode, 'recording': name, 'leg': None,
                                             'source_recording_id': sid, 'stage': 'RB02/RB04 pass (recording)',
                                             'reason': pe.get('reason'), 'disposition': 'recording_excluded'})
                report['recordings'].append({'subject': subject, 'mode': mode, 'recording': name, 'source_recording_id': sid,
                                             'status': 'excluded', 'reason': pe.get('reason'), 'steps_rb03': len(st),
                                             'eligible_steps': 0, 'phase_observations': 0, 'excluded_rb03': len(st),
                                             'excluded_export': 0, 'continuous_observations': 0})
                totals['recordings_excluded'] += 1
                continue
            try:
                stats = process_recording(row, st, pe, se, proot, sroot, info, None, ROOTS, writers, report)
                totals['recordings_exported'] += 1
                totals['phase'] += stats['phase']
                totals['continuous'] += 1
            except (ex.LabelError, ExportError) as exc:
                errors.append({'recording': sid, 'error': f'{type(exc).__name__}: {exc}'[:400]})
                raise
            pygc.collect()
            if LIBC is not None:
                LIBC.malloc_trim(0)
            print(f'{sid} done peak_rss_mib={peak_rss_mib()}', file=sys.stderr, flush=True)
    finally:
        writers.close()
    for name, rows in (('observations', report['observations']), ('exclusions', report['exclusions']),
                       ('recordings', report['recordings'])):
        with (out_root / f'{name}.jsonl').open('x') as f:
            for r in rows:
                f.write(json.dumps(r, sort_keys=True, default=_json_default) + '\n')
    (out_root / 'README.md').write_text(readme_text(args.subject or 'pilot'))
    ph, tm = pq.ParquetFile(str(out_root / 'phase.parquet')), pq.ParquetFile(str(out_root / 'time.parquet'))
    kinds = Counter((o['observation_type'], o['mode']) for o in report['observations'])
    recon = [r['force_reconstruction_max_abs_diff_BW'] for r in report['recordings'] if r.get('force_reconstruction_max_abs_diff_BW') is not None]
    summary = {'schema': SCHEMA_ID, 'status': 'run_done_unreviewed', 'scientific_approval': False,
               'subject': args.subject, 'records_arg': bool(args.record), 'recordings': len(report['recordings']),
               'recordings_exported': totals['recordings_exported'], 'recordings_excluded': totals['recordings_excluded'],
               'observations_by_kind_and_mode': {f'{k}|{m}': v for (k, m), v in sorted(kinds.items())},
               'phase_observations': totals['phase'], 'continuous_observations': totals['continuous'],
               'phase_rows': ph.metadata.num_rows, 'time_rows': tm.metadata.num_rows,
               'phase_row_groups': ph.metadata.num_row_groups, 'time_row_groups': tm.metadata.num_row_groups,
               'exclusions': len(report['exclusions']),
               'exclusions_by_reason': dict(Counter(e['reason'] for e in report['exclusions'])),
               'incomplete_stance_force_by_mode': dict(Counter(o['mode'] for o in report['observations'] if 'incomplete_stance_force' in o.get('flags', []))),
               'left_leg_extension_observations': sum(1 for o in report['observations'] if 'authors_rule_extended_to_left_leg' in o.get('flags', [])),
               'force_reconstruction_max_abs_diff_BW': max(recon) if recon else None, 'peak_rss_mib': peak_rss_mib(),
               'code_sha256': {c: sha256_file(ROOT / c) for c in CODE},
               'sha256': {n: sha256_file(out_root / n) for n in ('phase.parquet', 'time.parquet', 'observations.jsonl',
                                                                 'exclusions.jsonl', 'recordings.jsonl')}}
    tmp = out_root / 'run_summary.tmp'
    tmp.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    tmp.replace(out_root / 'run_summary.json')
    return 0


def pilot_records(inv, seed=20261127):
    rng = random.Random(seed)
    out = ['AB06/levelground/levelground_ccw_fast_01_01', 'AB06/treadmill/treadmill_01_01', 'AB06/stair/stair_1_l_01_02']
    for subject, mode in (('AB06', 'ramp'), ('AB17', 'levelground'), ('AB17', 'stair')):
        names = sorted(r for (s, m, r) in inv if s == subject and m == mode and f'{s}/{m}/{r}' not in out)
        out.append(f'{subject}/{mode}/{rng.choice(names)}')
    out.append('AB12/treadmill/treadmill_05_01')          # left-leg treadmill steps with large masked stance (flag test)
    return out


def make_spec(args):
    from contributor_tools import guarded_launcher as gl
    inv = load_inventory()
    records = ([f'{sj}/{m}/{r}' for (sj, m, r) in sorted(inv) if sj == args.subject] if args.subject
               else (args.record or pilot_records(inv)))
    subjects = sorted({r.split('/')[0] for r in records})
    bindings = {c: gl.sha256_file(ROOT / c) for c in CODE + ('contributor_tools/guarded_launcher.py',)}
    bindings[INVENTORY] = gl.sha256_file(ROOT / INVENTORY)
    for s in subjects:
        for p in (f'{AUTHORS}/{s}/subject_info_{s}.json', f'{PASS_ROOT.format(subject=s)}/ledger.jsonl',
                  f'{SEG_ROOT.format(subject=s)}/ledger.jsonl', f'{SEG_ROOT.format(subject=s)}/steps.jsonl'):
            bindings[p] = gl.sha256_file(ROOT / p)
    command = ['python3', 'contributor_tools/run_gt21_rb_export.py', 'run', '--out-root', args.out_root]
    if args.subject:
        command += ['--subject', args.subject]
    else:
        for r in records:
            command += ['--record', r]
    spec = {'job_id': args.job_id, 'command': command, 'cwd': str(ROOT), 'output_root': args.out_root,
            'receipt_path': args.receipt, 'bindings': bindings, 'timeout_seconds': 3600, 'kill_after_seconds': 30,
            'poll_seconds': 15, 'startup_memory_mib': {'linux': 3584, 'windows': 2816},
            'runtime_memory_mib': {'linux': 2048, 'windows': 2048},
            'expected_output_names': ['run_summary.json', 'phase.parquet'], 'address_space_mib': 768,
            'disk_admission': [{'path': str(ROOT / 'converted_datasets'), 'min_free_mib': 15360}]}
    with open(args.spec_out, 'x') as f:
        json.dump(spec, f, indent=2)
        f.write('\n')
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('run')
    s.add_argument('--out-root', required=True)
    s.add_argument('--record', action='append')
    s.add_argument('--subject', choices=SUBJECTS)
    s = sub.add_parser('spec')
    s.add_argument('--job-id', required=True)
    s.add_argument('--out-root', required=True)
    s.add_argument('--receipt', required=True)
    s.add_argument('--spec-out', required=True)
    s.add_argument('--record', action='append')
    s.add_argument('--subject', choices=SUBJECTS)
    args = p.parse_args(argv)
    return {'run': run, 'spec': make_spec}[args.cmd](args)


if __name__ == '__main__':
    raise SystemExit(main())
