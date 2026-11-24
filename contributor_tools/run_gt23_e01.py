"""GT23-E01 export runner (Python only, no MATLAB).

Subcommands
  run      One participant (or named recordings). Reads, one recording at a time, the C06 batch3 output (angles, speeds,
           foot-frame pressure point, force in N), the M01 output (moments, powers, force in body weights) and the S01
           segments; every input file is hash-checked against its ledger. Writes a NEW root:
             phase.parquet           150-sample observations of every accepted S01 stride (individual_cycle) and span (transfer)
             time.parquet            one continuous_recording observation per recording (the only table for the 64
                                     recordings with no defensible cycle)
             observations.jsonl      one line per exported observation with lineage
             exclusions.jsonl        every S01 interval left out, with its reason
             authors_windows.jsonl   every authors' window with its fate
             recordings.jsonl        every recording with its disposition and counts
             README.md, run_summary.json
  spec     Writes the guarded-launcher job spec.
  summary  Adds participant roots into counts by kind and exclusions by reason.

Rules and column mapping are in gt23_export.py. Memory: one recording resident, Parquet rows written in groups of at most
4096 rows (3000 for phase), pyarrow system pool, no threads.
"""
import argparse
import json
import os
from pathlib import Path
import resource
import sys

os.environ.setdefault('ARROW_DEFAULT_MEMORY_POOL', 'system')
for _k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_k, '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
from contributor_tools import gt23_export as ex  # noqa: E402
from contributor_tools import gt23_mass as ms  # noqa: E402
from contributor_tools import gt23_source_reader as rd  # noqa: E402

SUBJECTS = ('AB01', 'AB02', 'AB03', 'AB05', 'AB06', 'AB07', 'AB08', 'AB09', 'AB10', 'AB11', 'AB12', 'AB13')
BASE = 'converted_datasets/reconversion_v2'
README = 'docs/quality/audits/source_evidence/gt23/publisher-readme.txt'
CODE = ('contributor_tools/gt23_export.py', 'contributor_tools/run_gt23_e01.py', 'contributor_tools/gt23_mass.py',
        'contributor_tools/gt23_source_reader.py', 'contributor_tools/guarded_launcher.py')
PHASE_ROWS_PER_GROUP = 3000
TIME_ROWS_PER_GROUP = 4096
READ_BATCH = 4096
SCHEMA_ID = 'locohub.gt23_e01/1'
STR_COLUMNS = ('subject', 'source_recording_id', 'observation_id', 'reference_side', 'observation_type', 'task', 'task_id',
               'task_info', 'subject_metadata', 'held_signals')


class ExportError(RuntimeError):
    pass


def roots_for(subject, base=BASE):
    return {'c06': f'{base}/gt23_c06_batch3_{subject}', 'm01': f'{base}/gt23_m01_batch_{subject}',
            's01': f'{base}/gt23_s01_batch_{subject}'}


def peak_rss_mib():
    return round(max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) / 1024, 1)


def read_all(path):
    pf = pq.ParquetFile(str(path), buffer_size=0)
    names = list(pf.schema_arrow.names)
    parts = {n: [] for n in names}
    for batch in pf.iter_batches(batch_size=READ_BATCH, use_threads=False):
        for n in names:
            parts[n].append(batch.column(n).to_numpy(zero_copy_only=False))
    return {n: np.concatenate(v).astype(np.float64, copy=False) for n, v in parts.items()}


def jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def same(a, b):
    return bool(np.array_equal(a, b, equal_nan=True))


def phase_names():
    return ex.role_columns(('ipsi', 'contra'))


def time_names():
    return ex.role_columns(('left', 'right'))


def make_schema(index_name, signal_names):
    fields = [pa.field(n, pa.string()) for n in ex.IDENTITY]
    fields += [pa.field(index_name, pa.float64())] + [pa.field(n, pa.float64()) for n in ex.CLOCKS]
    fields += [pa.field('held_signals', pa.string())]
    fields += [pa.field(n, pa.float64()) for n in signal_names]
    return pa.schema(fields, metadata={b'schema': SCHEMA_ID.encode()})


class Recording:
    """Arrays of one recording from C06 and M01 with the leg mapping applied once."""

    def __init__(self, subject, name, c06, m01, c06_entry):
        self.subject, self.name = subject, name
        self.c06, self.m01 = c06, m01
        self.time = c06['time_s']
        self.n = len(self.time)
        self.held = dict(c06_entry['held_columns'])
        self.cache = {}
        self.finite_rec = {}

    def array(self, family, source, sign):
        key = (family, source, sign)
        if key not in self.cache:
            table = self.c06 if family == 'c06' else self.m01
            if source not in table:
                raise ExportError(f'{self.subject}/{self.name}: source column {source} missing from {family}')
            x = table[source]
            self.cache[key] = x if sign == 1.0 else np.negative(x)
        return self.cache[key]

    def columns(self, tokens_sides):
        """[(export name, family, array, held key, side word)] for pelvis and the listed (token, side) legs."""
        out = []
        pname, pfam, psrc, psign, phold = ex.PELVIS_SPEC
        out.append((pname, pfam, self.array(pfam, psrc, psign), phold, None))
        for template_index in range(len(ex.LEG_SPECS)):
            for token, side in tokens_sides:
                name, fam, src, sign, hold = ex.column_sources(token, side)[template_index]
                out.append((name, fam, self.array(fam, src, sign), hold, side))
        return out


def finite_any(x):
    return bool(np.isfinite(x).any())


def build_held(columns, rows_slice, rec, plate_missing, finite_rec_cache):
    """{export column: reason} for columns with no finite value in the slice."""
    held = {}
    for name, fam, arr, hold, side in columns:
        key = name
        if key not in finite_rec_cache:
            finite_rec_cache[key] = finite_any(arr)
        seg = arr if rows_slice is None else arr[rows_slice]
        in_obs = finite_any(seg)
        reason = ex.held_reason(name, hold, rec.held, in_obs, finite_rec_cache[key],
                                bool(side and plate_missing.get(side)), fam)
        if reason is not None:
            held[name] = reason
    return held


class Writers:
    def __init__(self, out_root, subject):
        self.root = out_root
        self.pnames, self.tnames = phase_names(), time_names()
        self.pschema = make_schema('phase_ipsi', self.pnames)
        self.tschema = make_schema('time_s', self.tnames)
        self.phase = pq.ParquetWriter(str(out_root / 'phase.parquet'), self.pschema, compression='zstd')
        self.time = pq.ParquetWriter(str(out_root / 'time.parquet'), self.tschema, compression='zstd')
        self.phase_rows = self.time_rows = 0
        self.buf = []

    def close(self):
        self.flush()
        self.phase.close()
        self.time.close()

    def flush(self):
        if not self.buf:
            return
        table = self.table_from_obs(self.buf)
        self.phase.write_table(table, row_group_size=PHASE_ROWS_PER_GROUP)
        self.phase_rows += table.num_rows
        self.buf = []

    def add_phase(self, obs):
        self.buf.append(obs)
        if len(self.buf) * ex.N_PHASE >= PHASE_ROWS_PER_GROUP:
            self.flush()

    def table_from_obs(self, obs_list):
        n = ex.N_PHASE
        grid = np.linspace(0.0, 100.0, n)
        arrays = []
        for name in ex.IDENTITY + ('phase_ipsi',) + ex.CLOCKS + ('held_signals',) + tuple(self.pnames):
            if name in ex.IDENTITY or name == 'held_signals':
                values = [o['meta'][name] if name != 'held_signals' else o['held_json'] for o in obs_list for _ in range(1)]
                arrays.append(pa.array([v for v in values for _ in range(n)], type=pa.string()))
            elif name == 'phase_ipsi':
                arrays.append(pa.array(np.tile(grid, len(obs_list)), type=pa.float64()))
            elif name in ex.CLOCKS:
                arrays.append(pa.array(np.repeat([o['meta'][name] for o in obs_list], n), type=pa.float64()))
            else:
                arrays.append(pa.array(np.concatenate([o['values'][name] for o in obs_list]), type=pa.float64()))
        return pa.Table.from_arrays(arrays, schema=self.pschema)

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
        self.time_rows += n


def check_inputs(subject, rec_name, s01_row, c06_entry, m01_entry, c06_root, m01_root, readme_mass):
    if s01_row['status'] != 'ok':
        raise ExportError(f'{subject}/{rec_name}: S01 status {s01_row["status"]}')
    if c06_entry['rows'] != s01_row['rows'] or m01_entry['rows'] != s01_row['rows']:
        raise ExportError(f'{subject}/{rec_name}: row counts differ between S01, C06 and M01')
    if rd.sha256_file(ROOT / c06_root / c06_entry['output']['file']) != c06_entry['output']['sha256']:
        raise ExportError(f'{subject}/{rec_name}: C06 output hash differs from its ledger')
    if rd.sha256_file(ROOT / m01_root / m01_entry['output']['file']) != m01_entry['output']['sha256']:
        raise ExportError(f'{subject}/{rec_name}: M01 output hash differs from its ledger')
    if m01_entry['body_weight_mass_kg'] != readme_mass:
        raise ExportError(f'{subject}/{rec_name}: body-weight mass differs from the README table')


def process_recording(subject, rec_name, s01_row, segs, authors, c06_entry, m01_entry, roots, readme_mass, writers, report):
    check_inputs(subject, rec_name, s01_row, c06_entry, m01_entry, roots['c06'], roots['m01'], readme_mass)
    c06 = read_all(ROOT / roots['c06'] / c06_entry['output']['file'])
    m01 = read_all(ROOT / roots['m01'] / m01_entry['output']['file'])
    if not same(c06['time_s'], m01['time_s']) or len(c06['time_s']) != s01_row['rows']:
        raise ExportError(f'{subject}/{rec_name}: C06 and M01 clocks differ')
    rec = Recording(subject, rec_name, c06, m01, c06_entry)
    task, tclass = s01_row['task'], s01_row['task_class']
    mkey, mnote = ex.mass_note(m01_entry)
    limits = ex.recording_limits(subject, m01_entry, task)
    plate_missing = {side: rec.held.get(f'grf_lab_y_{side}_N') == ex.PLATE_MISSING for side in ('left', 'right')}
    smeta = ex.dumps(ex.subject_meta(readme_mass))
    sid = f'{subject}/{rec_name}'
    finite_rec = {}
    time = rec.time
    t_start, t_end = float(time[0]), float(time[-1])
    stats = {'exported_observations': 0, 'cycles': 0, 'transfers': 0, 'excluded': 0, 'accepted_segments': 0}
    # ------------------------------------------------------------------ phase observations
    obs_lines = []
    seg_obs = {}
    for seg in segs:
        if seg['status'] == 'excluded':
            report['exclusions'].append({'subject': subject, 'recording': rec_name, 'segment_id': seg['segment_id'], 'side': seg['side'],
                                         'task': task, 'start_s': seg['start_s'], 'end_s': seg['end_s'], 'stage': 'S01 segmentation',
                                         'reason': seg['reason'], 'disposition': seg['disposition']})
            stats['excluded'] += 1
            continue
        if seg['status'] != 'accepted' or tclass == 'continuous':
            raise ExportError(f'{sid}: unexpected S01 status {seg["status"]} for {tclass}')
        stats['accepted_segments'] += 1
        a, b = seg['start_index'], seg['end_index']
        if not (abs(time[a] - seg['start_s']) < 1e-9 and abs(time[b] - seg['end_s']) < 1e-9):
            raise ExportError(f'{sid}: S01 clock differs from the recording clock at {seg["segment_id"]}')
        label = ex.authors_label(rec_name, seg['authors_file']) if seg['label_source'] == 'authors_window' else None
        if (seg['label_source'] == 'authors_window') != bool(seg['authors_match']):
            raise ExportError(f'{sid}: label source and authors match disagree at {seg["segment_id"]}')
        fam, tid, info = ex.classify(task, rec_name, label)
        info.update({'label_source': seg['label_source'], 'authors_file': seg['authors_file'],
                     'authors_match': seg['authors_match'], 's01_segment_id': seg['segment_id'],
                     's01_disposition': seg['disposition'], 'segment_rule': seg['rule'], 'segment_start_index': a,
                     'segment_end_index': b, 'segment_duration_s': seg['duration_s'], 'mass_note_key': mkey,
                     'mass_note': mnote, 'mass_factor': m01_entry.get('factor'), 'limits': limits,
                     'contralateral_timing': 'contra columns cover the same absolute time span as the reference leg; no 50 percent shift is assumed'})
        if label is None:
            info['label_note'] = 'unknown: no authors window matched this span'
        task_info = ex.dumps(info)
        otype = ex.obs_type(tclass)
        for side in ex.observation_sides(seg['side']):
            cols = rec.columns((('ipsi', side), ('contra', ex.OTHER[side])))
            held = build_held(cols, slice(a, b + 1), rec, plate_missing, finite_rec)
            values = {name: ex.phase_samples(arr, a, b) for name, _f, arr, _h, _s in cols}
            meta = {'subject': subject, 'source_recording_id': sid, 'observation_id': seg['segment_id'], 'reference_side': side,
                    'observation_type': otype, 'task': fam, 'task_id': tid, 'task_info': task_info, 'subject_metadata': smeta,
                    'source_start_time_s': float(time[a]), 'source_end_time_s': float(time[b])}
            writers.add_phase({'meta': meta, 'values': values, 'held_json': ex.dumps(held)})
            stats['exported_observations'] += 1
            stats['cycles' if otype == 'individual_cycle' else 'transfers'] += 1
            seg_obs.setdefault(seg['index'], []).append(f'{seg["segment_id"]}|{side}')
            obs_lines.append({'subject': subject, 'source_recording_id': sid, 'observation_id': seg['segment_id'],
                              'reference_side': side, 'observation_type': otype, 'table': 'phase', 'rows': ex.N_PHASE,
                              'task': fam, 'task_id': tid, 'label_source': seg['label_source'], 'authors_label': label,
                              'authors_file': seg['authors_file'], 'start_index': a, 'end_index': b,
                              'source_start_time_s': float(time[a]), 'source_end_time_s': float(time[b]),
                              'held_signals': sorted(held), 'mass_note_key': mkey, 's01_disposition': seg['disposition'],
                              'c06_sha256': c06_entry['output']['sha256'], 'm01_sha256': m01_entry['output']['sha256']})
    # ------------------------------------------------------------------ authors' windows
    for w in authors:
        row = {k: w[k] for k in ('subject', 'recording', 'task', 'file', 'key', 'row', 'side', 'start', 'end', 'status', 'reason', 'segment_index')}
        if w['status'] == 'matched':
            ids = seg_obs.get(w['segment_index'])
            if not ids:
                raise ExportError(f'{sid}: authors window {w["file"]}:{w["key"]}:{w["row"]} matched but its span was not exported')
            row.update({'fate': 'exported', 'observations': sorted(ids)})
        else:
            row.update({'fate': 'not_exported', 'observations': []})
        report['authors_windows'].append(row)
    # ------------------------------------------------------------------ continuous time observation
    cols = rec.columns((('left', 'left'), ('right', 'right')))
    held = build_held(cols, None, rec, plate_missing, finite_rec)
    fam, tid, info = ex.classify(task, rec_name, None)
    scope = 'continuous_only' if tclass == 'continuous' else 'continuous_and_segments'
    info.update({'export_scope': scope, 's01_disposition': s01_row['disposition'], 'segment_rule': s01_row['rule'],
                 'segments_exported': stats['exported_observations'], 'mass_note_key': mkey, 'mass_note': mnote,
                 'mass_factor': m01_entry.get('factor'), 'limits': limits, 'label_source': 'unknown',
                 'label_note': 'continuous recording: the task family holds only what the recording name determines'})
    oid = f'{sid}/continuous'
    meta = {'subject': subject, 'source_recording_id': sid, 'observation_id': oid, 'reference_side': 'none',
            'observation_type': 'continuous_recording', 'task': fam, 'task_id': tid, 'task_info': ex.dumps(info),
            'subject_metadata': smeta, 'source_start_time_s': t_start, 'source_end_time_s': t_end}
    signals = {name: arr for name, _f, arr, _h, _s in cols}
    writers.write_time(meta, ex.dumps(held), time, signals)
    obs_lines.append({'subject': subject, 'source_recording_id': sid, 'observation_id': oid, 'reference_side': 'none',
                      'observation_type': 'continuous_recording', 'table': 'time', 'rows': int(rec.n), 'task': fam, 'task_id': tid,
                      'export_scope': scope, 'source_start_time_s': t_start, 'source_end_time_s': t_end, 'held_signals': sorted(held),
                      'mass_note_key': mkey, 'c06_sha256': c06_entry['output']['sha256'], 'm01_sha256': m01_entry['output']['sha256']})
    report['observations'].extend(obs_lines)
    report['recordings'].append({'subject': subject, 'recording': rec_name, 'task': task, 'task_class': tclass,
                                 'disposition': s01_row['disposition'], 'rows': int(rec.n), 'export_scope': scope,
                                 'accepted_segments': stats['accepted_segments'], 'excluded_segments': stats['excluded'],
                                 'authors_windows': len(authors), 'phase_observations': stats['exported_observations'],
                                 'cycles': stats['cycles'], 'transfers': stats['transfers'], 'mass_note_key': mkey,
                                 'limits': limits, 'held_signal_count_continuous': len(held), 'plate_missing': plate_missing,
                                 'c06_sha256': c06_entry['output']['sha256'], 'm01_sha256': m01_entry['output']['sha256']})
    return stats


def readme_text(subject):
    lines = [f'# GT23 export, participant {subject} (GT23-E01, unreviewed)', '',
             'Tables: `phase.parquet` (150 samples, 0 to 100 percent inclusive, one observation per stride or span and reference leg) and '
             '`time.parquet` (one continuous recording per source recording, left and right columns). Identity: subject, '
             'source_recording_id, observation_id, reference_side. Lineage lines are in `observations.jsonl`.', '',
             '## Units and signs',
             '- Angles rad, speeds rad/s, moments N*m/kg, powers W/kg, forces N and body weights (BW), pressure point m, per the data contract.',
             f'- {ex.README_UNITS_NOTE}',
             '- Knee flexion and knee flexor moment are positive (knee moment = minus the published knee_angle moment). Frontal and '
             'transverse columns (hip adduction and rotation, subtalar) keep the source sign; the standard has not adopted a rule.',
             '- Foot-frame pressure point: origin 100 mm forward of the ankle-marker midpoint, forward along heel to toe. Lab-axis force and '
             'plate pressure point are named `_lab_`. Forward and sideways force exist only in the 11 forward-walking tasks.',
             '- Body-weight columns use the publisher README masses (AB03 113.5 kg).', '',
             '## Labels',
             'The authors\' file label is carried only where an S01 span matched an authors\' window; every other observation says unknown '
             '(`label_source`, `authors_label` in task_info). A speed or incline appears only when the label or the README states it. '
             'Stair rise 0.152 m cites the paper; no curb or step-up height exists in any source.', '',
             '## Notes per recording',
             'Each observation carries `mass_note_key` (rescaled_exact, rescaled_estimated, own_mass_confirmed, cannot_be_told) and '
             '`mass_note` in task_info, `limits` where one applies, and `held_signals` naming every column with no finite value and why.',
             f'- {ex.CURB_UP_NOTE}', f'- {ex.AB09_LIMIT}', f'- {ex.AB07_LIMIT}', '',
             'Window-rule spans have no single leg: each accepted span is exported for the left and the right reference leg with the same '
             'observation_id. Contralateral columns cover the same absolute time span; no 50 percent shift is assumed.']
    return '\n'.join(lines) + '\n'


def run(args):
    subject = args.subject
    out_root = ROOT / args.output_root
    if out_root.exists() and any(out_root.iterdir()):
        raise ExportError(f'{out_root} is not empty; never overwrite')
    out_root.mkdir(parents=True, exist_ok=True)
    roots = roots_for(subject, args.base)
    masses = ms.parse_readme_masses((ROOT / README).read_text())
    s01_ledger = {r['recording']: r for r in jsonl(ROOT / roots['s01'] / 'ledger.jsonl')}
    segments, authors = {}, {}
    for s in jsonl(ROOT / roots['s01'] / 'segments.jsonl'):
        segments.setdefault(s['recording'], []).append(s)
    for w in jsonl(ROOT / roots['s01'] / 'authors_windows.jsonl'):
        authors.setdefault(w['recording'], []).append(w)
    c06 = {r['recording']: r for r in jsonl(ROOT / roots['c06'] / 'ledger.jsonl')}
    m01 = {r['recording']: r for r in jsonl(ROOT / roots['m01'] / 'ledger.jsonl')}
    if not (set(s01_ledger) == set(c06) == set(m01)):
        raise ExportError('S01, C06 and M01 do not list the same recordings')
    wanted = args.records or sorted(s01_ledger)
    report = {'exclusions': [], 'authors_windows': [], 'observations': [], 'recordings': []}
    writers = Writers(out_root, subject)
    totals = {'cycles': 0, 'transfers': 0, 'continuous': 0}
    try:
        for rec_name in wanted:
            stats = process_recording(subject, rec_name, s01_ledger[rec_name], segments.get(rec_name, []), authors.get(rec_name, []),
                                      c06[rec_name], m01[rec_name], roots, masses[subject], writers, report)
            totals['cycles'] += stats['cycles']
            totals['transfers'] += stats['transfers']
            totals['continuous'] += 1
    finally:
        writers.close()
    for name, rows in (('observations', report['observations']), ('exclusions', report['exclusions']),
                       ('authors_windows', report['authors_windows']), ('recordings', report['recordings'])):
        with (out_root / f'{name}.jsonl').open('x') as stream:
            for row in rows:
                stream.write(json.dumps(row, sort_keys=True) + '\n')
    (out_root / 'README.md').write_text(readme_text(subject))
    back = {name: pq.ParquetFile(str(out_root / f'{name}.parquet'), buffer_size=0) for name in ('phase', 'time')}
    by_reason = {}
    for e in report['exclusions']:
        by_reason[e['reason']] = by_reason.get(e['reason'], 0) + 1
    summary = {'schema': SCHEMA_ID, 'subject': subject, 'recordings_done': len(wanted), 'records_arg': bool(args.records),
               'observations': {'individual_cycle': totals['cycles'], 'transfer': totals['transfers'],
                                'continuous_recording': totals['continuous']},
               'phase_rows': back['phase'].metadata.num_rows, 'time_rows': back['time'].metadata.num_rows,
               'phase_row_groups': back['phase'].metadata.num_row_groups, 'time_row_groups': back['time'].metadata.num_row_groups,
               'exclusions': len(report['exclusions']), 'exclusions_by_reason': by_reason,
               'authors_windows': len(report['authors_windows']),
               'authors_windows_exported': sum(w['fate'] == 'exported' for w in report['authors_windows']),
               'continuous_only_recordings': sum(r['export_scope'] == 'continuous_only' for r in report['recordings']),
               'mass_note_counts': {k: sum(r['mass_note_key'] == k for r in report['recordings']) for k in ex.MASS_NOTES},
               'peak_rss_mib': peak_rss_mib(), 'scientific_approval': False,
               'sha256': {n: rd.sha256_file(out_root / n) for n in ('phase.parquet', 'time.parquet', 'observations.jsonl',
                                                                   'exclusions.jsonl', 'authors_windows.jsonl', 'recordings.jsonl')},
               'status': 'participant_done_unreviewed'}
    tmp = out_root / 'run_summary.tmp'
    tmp.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    tmp.replace(out_root / 'run_summary.json')
    return 0


def make_spec(args):
    from contributor_tools import guarded_launcher as gl
    command = ['python3', 'contributor_tools/run_gt23_e01.py', args.kind, '--output-root', args.output_root]
    bindings = {c: gl.sha256_file(ROOT / c) for c in CODE}
    bindings[README] = gl.sha256_file(ROOT / README)
    if args.kind == 'run':
        command += ['--subject', args.subject]
        for r in args.records or []:
            command += ['--records', r]
        roots = roots_for(args.subject)
        for p in (f"{roots['c06']}/ledger.jsonl", f"{roots['m01']}/ledger.jsonl", f"{roots['s01']}/ledger.jsonl",
                  f"{roots['s01']}/segments.jsonl", f"{roots['s01']}/authors_windows.jsonl"):
            bindings[p] = gl.sha256_file(ROOT / p)
        names = ['run_summary.json']
    else:
        command += ['--roots'] + list(args.roots)
        for r in args.roots:
            bindings[f'{r}/run_summary.json'] = gl.sha256_file(ROOT / r / 'run_summary.json')
        names = ['summary.json']
    spec = {'job_id': args.job_id, 'command': command, 'cwd': str(ROOT), 'output_root': args.output_root,
            'receipt_path': args.receipt, 'bindings': bindings, 'timeout_seconds': 3600, 'kill_after_seconds': 30,
            'poll_seconds': 15, 'startup_memory_mib': {'linux': 3584, 'windows': 2816},
            'runtime_memory_mib': {'linux': 2048, 'windows': 2048}, 'expected_output_names': names, 'address_space_mib': 768}
    with Path(args.spec_out).open('x') as stream:
        json.dump(spec, stream, indent=2)
        stream.write('\n')
    return 0


def summarize(args):
    out_root = ROOT / args.output_root
    out_root.mkdir(parents=True, exist_ok=False)
    sums = [json.loads((ROOT / r / 'run_summary.json').read_text()) for r in args.roots]
    kinds = {k: sum(s['observations'][k] for s in sums) for k in ('individual_cycle', 'transfer', 'continuous_recording')}
    reasons = {}
    for s in sums:
        for k, v in s['exclusions_by_reason'].items():
            reasons[k] = reasons.get(k, 0) + v
    summary = {'participants': [s['subject'] for s in sums], 'observations_by_kind': kinds,
               'phase_observations': kinds['individual_cycle'] + kinds['transfer'],
               'phase_rows': sum(s['phase_rows'] for s in sums), 'time_rows': sum(s['time_rows'] for s in sums),
               'exclusions': sum(s['exclusions'] for s in sums), 'exclusions_by_reason': reasons,
               'authors_windows': sum(s['authors_windows'] for s in sums),
               'authors_windows_exported': sum(s['authors_windows_exported'] for s in sums),
               'continuous_only_recordings': sum(s['continuous_only_recordings'] for s in sums),
               'recordings': sum(s['recordings_done'] for s in sums),
               'mass_note_counts': {k: sum(s['mass_note_counts'][k] for s in sums) for k in ex.MASS_NOTES},
               'peak_rss_mib_by_participant': {s['subject']: s['peak_rss_mib'] for s in sums}, 'scientific_approval': False}
    (out_root / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('run')
    s.add_argument('--output-root', required=True)
    s.add_argument('--subject', required=True, choices=SUBJECTS)
    s.add_argument('--records', action='append')
    s.add_argument('--base', default=BASE)
    s = sub.add_parser('spec')
    s.add_argument('--kind', choices=('run', 'summary'), required=True)
    s.add_argument('--job-id', required=True)
    s.add_argument('--output-root', required=True)
    s.add_argument('--receipt', required=True)
    s.add_argument('--spec-out', required=True)
    s.add_argument('--subject', choices=SUBJECTS)
    s.add_argument('--records', action='append')
    s.add_argument('--roots', nargs='*')
    s = sub.add_parser('summary')
    s.add_argument('--output-root', required=True)
    s.add_argument('--roots', nargs='+', required=True)
    args = p.parse_args(argv)
    return {'run': run, 'spec': make_spec, 'summary': summarize}[args.cmd](args)


if __name__ == '__main__':
    raise SystemExit(main())
