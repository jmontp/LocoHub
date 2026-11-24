"""GT23-E01 independent full readback (separate implementation; imports nothing from gt23_export or run_gt23_e01).

Subcommands
  audit    One participant export root. Re-derives what must be there from the C06 and M01 outputs, the S01 segments and the
           publisher README, then reads phase.parquet and time.parquet one row group at a time and compares every observation:
             * identity, metadata, grid, clocks, labels (only where S01 matched an authors' window), README-traceable speeds
             * every signal value against the input arrays (phase: linear interpolation in TIME, a different method from the
               exporter's index arithmetic; time table: bit equality), signs (knee moment = minus the published value),
               body-weight columns against newtons, finite patterns, held_signals against the actual missing columns
             * counts against S01, every exclusion, every authors' window and every recording accounted for
  spec     Writes the guarded-launcher job spec.
  summary  Combines participant audit reports.

Different from the exporter on purpose: names are decoded by regular expression from the standard's own column naming
instead of a template table; phase values are re-sampled by time; label rules come from the README text, not a table.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import sys

os.environ.setdefault('ARROW_DEFAULT_MEMORY_POOL', 'system')
for _k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_k, '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # only for the launcher's sha256 helper when writing a spec
import numpy as np  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

BASE = 'converted_datasets/reconversion_v2'
README = 'docs/quality/audits/source_evidence/gt23/publisher-readme.txt'
SUBJECTS = ('AB01', 'AB02', 'AB03', 'AB05', 'AB06', 'AB07', 'AB08', 'AB09', 'AB10', 'AB11', 'AB12', 'AB13')
CODE = ('contributor_tools/audit_gt23_e01.py', 'contributor_tools/guarded_launcher.py')
G = 9.80665
READ_BATCH = 4096
RTOL, ATOL = 1e-9, 1e-12
SCALE_TOL = 1e-11   # times the largest magnitude of the input signal inside the span: interpolation by time vs by index
ID_COLUMNS = ['subject', 'source_recording_id', 'observation_id', 'reference_side', 'observation_type', 'task', 'task_id',
              'task_info', 'subject_metadata']
CLOCK_COLUMNS = ['source_start_time_s', 'source_end_time_s']
MASS_KEYS = ('rescaled_exact', 'rescaled_estimated', 'own_mass_confirmed', 'cannot_be_told')

# the standard's joint names -> the published joint names used in the M01 columns
JOINT_PUBLISHED = {'hip_flexion': 'hip_flexion', 'hip_adduction': 'hip_adduction', 'hip_rotation': 'hip_rotation',
                   'knee_flexion': 'knee_angle', 'ankle_dorsiflexion': 'ankle_angle', 'subtalar_angle': 'subtalar_angle'}
POWER_PUBLISHED = {'hip_flexion': 'hip_flexion_power', 'hip_adduction': 'hip_adduction_power', 'hip_rotation': 'hip_rotation_power',
                   'knee_flexion': 'knee_power', 'ankle_dorsiflexion': 'ankle_power', 'subtalar_angle': 'subtalar_power'}
FORCE_AXIS = {'vertical': 'lab_y', 'lab_x': 'lab_x', 'lab_z': 'lab_z', 'anterior': 'anterior', 'lateral': 'lateral'}


class AuditError(RuntimeError):
    pass


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def peak_rss_mib():
    return round(max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) / 1024, 1)


def lines(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def load_arrays(path):
    pf = pq.ParquetFile(str(path), buffer_size=0)
    names = pf.schema_arrow.names
    cols = {n: [] for n in names}
    for b in pf.iter_batches(READ_BATCH, use_threads=False):
        for n in names:
            cols[n].append(b.column(n).to_numpy(zero_copy_only=False))
    return {n: np.concatenate(v).astype(np.float64) for n, v in cols.items()}


# ----------------------------------------------------------------------------------------------- decoding of names
ROLE_RE = re.compile(r'_(ipsi|contra|left|right)(?=_|$)')


def decode(name, ref_side, table):
    """Export column name -> (family, source column, sign, held key) using the standard's column naming.
    ``table`` is 'phase' (roles ipsi/contra) or 'time' (left/right)."""
    if name == 'pelvis_sagittal_angle_rad':
        return 'c06', name, 1.0, name
    m = ROLE_RE.search(name)
    if not m:
        raise AuditError(f'cannot decode {name}')
    role = m.group(1)
    if role == 'ipsi':
        side = ref_side
    elif role == 'contra':
        side = {'left': 'right', 'right': 'left'}[ref_side]
    else:
        side = role
    s = side[0]
    stem, tail = name[:m.start()], name[m.end():]
    if re.fullmatch(r'(thigh|shank|foot)_sagittal_angle|(hip_flexion|knee_flexion|ankle_dorsiflexion)_(angle|velocity)', stem):
        src = f'{stem}_{side}{tail}'
        return 'c06', src, 1.0, src
    if stem.startswith('cop_'):
        src = f'{stem}_{side}{tail}'
        return 'c06', src, 1.0, src
    if stem.startswith('heading_'):
        src = f'{name[:m.start()]}_{side}'
        return 'c06', src, 1.0, src
    mm = re.fullmatch(r'grf_(vertical|anterior|lateral|lab_x|lab_z)', stem)
    if mm:
        axis = FORCE_AXIS[mm.group(1)]
        unit = tail.lstrip('_')
        src_n = f'grf_{axis}_{side}_N'
        if unit == 'N':
            return 'c06', src_n, 1.0, src_n
        if unit == 'BW':
            return 'm01', f'grf_{axis}_{side}_BW', 1.0, src_n
    mm = re.fullmatch(r'(\w+)_moment', stem)
    if mm and tail == '_Nm_kg':
        joint = JOINT_PUBLISHED[mm.group(1)]
        return 'm01', f'{joint}_{s}_moment_Nm_kg', (-1.0 if mm.group(1) == 'knee_flexion' else 1.0), None
    mm = re.fullmatch(r'(\w+)_power', stem)
    if mm and tail == '_W_kg':
        pub = POWER_PUBLISHED[mm.group(1)]
        base = pub[:-len('_power')]
        return 'm01', f'{base}_power_{s}_W_kg', 1.0, None
    raise AuditError(f'cannot decode {name}')


def expected_signal_names(table):
    """Independent list of the signal columns: what the standard and the C06/M01 outputs provide per leg."""
    roles = ('ipsi', 'contra') if table == 'phase' else ('left', 'right')
    leg_stems = []
    for seg in ('thigh', 'shank', 'foot'):
        leg_stems.append(f'{seg}_sagittal_angle_{{R}}_rad')
    for j in ('hip_flexion', 'knee_flexion', 'ankle_dorsiflexion'):
        leg_stems.append(f'{j}_angle_{{R}}_rad')
    for j in ('hip_flexion', 'knee_flexion', 'ankle_dorsiflexion'):
        leg_stems.append(f'{j}_velocity_{{R}}_rad_s')
    for j in ('hip_flexion', 'hip_adduction', 'hip_rotation', 'knee_flexion', 'ankle_dorsiflexion', 'subtalar_angle'):
        leg_stems.append(f'{j}_moment_{{R}}_Nm_kg')
    for j in ('hip_flexion', 'hip_adduction', 'hip_rotation', 'knee_flexion', 'ankle_dorsiflexion', 'subtalar_angle'):
        leg_stems.append(f'{j}_power_{{R}}_W_kg')
    for unit in ('N', 'BW'):
        for ax in ('vertical', 'anterior', 'lateral', 'lab_x', 'lab_z'):
            leg_stems.append(f'grf_{ax}_{{R}}_{unit}')
    for c in ('anterior', 'vertical', 'lateral', 'lab_x', 'lab_y', 'lab_z'):
        leg_stems.append(f'cop_{c}_{{R}}_m')
    leg_stems += ['heading_lab_x_{R}', 'heading_lab_z_{R}']
    # exporter order: pelvis, then for each stem both roles
    names = ['pelvis_sagittal_angle_rad']
    for stem in leg_stems:
        for r in roles:
            names.append(stem.format(R=r))
    return names


# ----------------------------------------------------------------------------------------------- README facts
def readme_facts(text):
    """{task: {'header_speed': float|None, 'labels': {label: {'speed': float|None, 'incline': int|None}}}} from the README text."""
    facts, cur = {}, None
    for raw in text.splitlines():
        if not raw.strip():
            continue
        if not raw.startswith(('\t', ' ')) and re.match(r'^[a-z_]+:', raw) and '/////' not in raw:
            task, desc = raw.split(':', 1)
            m = re.search(r'at ([0-9.]+) m/s', desc)
            cur = facts.setdefault(task.strip(), {'header_speed': float(m.group(1)) if m else None, 'labels': {}})
            continue
        m = re.match(r'^\s+_([A-Za-z0-9_-]+):\s*(.*)$', raw)
        if m and cur is not None:
            label, desc = m.group(1), m.group(2)
            sp = re.search(r'at ([0-9.]+) m/s', desc)
            inc = re.search(r'(incline|decline) of (\d+) degrees', desc)
            cur['labels'][label] = {'speed': float(sp.group(1)) if sp else None,
                                    'incline': (int(inc.group(2)) * (1 if inc.group(1) == 'incline' else -1)) if inc else None}
    return facts


def readme_masses(text):
    t = {m.group(1): float(m.group(2)) for m in re.finditer(r'^(AB\d\d):\s*([0-9.]+)\s*kg\s*$', text, re.M)}
    if len(t) != 12:
        raise AuditError('README mass table incomplete')
    return t


def authors_label_of(recording, authors_file):
    """Label by removing the leading recording name (or, for the AB02 'step_ups' folder, 'step_ups_<n>') and the ending."""
    if authors_file is None:
        return None
    body = authors_file[:-len('_parsing.mat')] if authors_file.endswith('_parsing.mat') else None
    if body is None or not (body == recording or body.startswith(recording + '_')):
        raise AuditError(f'{authors_file} does not belong to {recording}')
    rest = body[len(recording):].lstrip('_')
    if not recording[-1].isdigit():
        rest = re.sub(r'^\d+_?', '', rest)
    return rest


# ----------------------------------------------------------------------------------------------- the audit
class Check:
    def __init__(self):
        self.items, self.failures = {}, {}

    def ok(self, name, passed, detail=None):
        if name not in self.items:
            self.items[name] = {'passed': True, 'detail': None}
        if not passed:
            self.items[name]['passed'] = False
            self.failures[name] = self.failures.get(name, 0) + 1
            if self.items[name]['detail'] is None:
                self.items[name]['detail'] = detail
        elif detail is not None and self.items[name]['detail'] is None and self.items[name]['passed']:
            self.items[name]['detail'] = None
        return passed


def interp_time(t, x, a, b):
    """150 values of x between sample a and b by linear interpolation in time; NaN if a neighbour is not finite."""
    tw, xw = t[a:b + 1], x[a:b + 1]
    tq = tw[0] + (tw[-1] - tw[0]) * (np.arange(150) / 149.0)
    finite = np.isfinite(xw)
    y = np.interp(tq, tw, np.where(finite, xw, 0.0))
    valid = np.interp(tq, tw, finite.astype(np.float64))
    y = np.where(valid > 0.999999, y, np.nan)
    return y


def compare(exp, got, check, name, stats, scale=1.0):
    fe, fg = np.isfinite(exp), np.isfinite(got)
    if not check.ok(f'{name}:finite_pattern', bool(np.array_equal(fe, fg)), 'finite pattern differs'):
        return
    if fe.any():
        d = np.abs(exp[fe] - got[fe])
        stats['max_abs_diff'] = max(stats['max_abs_diff'], float(d.max()))
        tol = ATOL + RTOL * np.abs(exp[fe]) + SCALE_TOL * scale
        check.ok(f'{name}:values', bool(np.all(d <= tol)), f'max difference {float(d.max()):.3g}')


def run_audit(args):
    subject = args.subject
    out_root = ROOT / args.output_root
    if out_root.exists() and any(out_root.iterdir()):
        raise AuditError(f'{out_root} is not empty; never overwrite')
    out_root.mkdir(parents=True, exist_ok=True)
    base = args.base
    exp_root = ROOT / args.export_root
    c06_root = ROOT / f'{base}/gt23_c06_batch3_{subject}'
    m01_root = ROOT / f'{base}/gt23_m01_batch_{subject}'
    s01_root = ROOT / f'{base}/gt23_s01_batch_{subject}'
    text = (ROOT / README).read_text()
    masses, facts = readme_masses(text), readme_facts(text)
    mass = masses[subject]
    chk = Check()
    c06_led = {r['recording']: r for r in lines(c06_root / 'ledger.jsonl')}
    m01_led = {r['recording']: r for r in lines(m01_root / 'ledger.jsonl')}
    s01_led = {r['recording']: r for r in lines(s01_root / 'ledger.jsonl')}
    segs = {}
    for s in lines(s01_root / 'segments.jsonl'):
        segs.setdefault(s['recording'], []).append(s)
    aw = {}
    for w in lines(s01_root / 'authors_windows.jsonl'):
        aw.setdefault(w['recording'], []).append(w)
    summary = json.loads((exp_root / 'run_summary.json').read_text())
    scope = sorted(s01_led) if not args.records else list(args.records)
    chk.ok('inputs:same_recordings', set(c06_led) == set(m01_led) == set(s01_led))
    # output file hashes recorded by the exporter equal the files on disk
    for name, digest in summary['sha256'].items():
        chk.ok(f'files:sha256:{name}', sha256(exp_root / name) == digest, 'file differs from run_summary')
    chk.ok('files:readme_present', (exp_root / 'README.md').exists())
    readme_out = (exp_root / 'README.md').read_text()
    for key in ('N*m', 'curb_up', 'AB09 divisor limit', 'AB07 right-foot marker offset limit', 'mass_note_key'):
        chk.ok(f'files:readme_mentions:{key}', key in readme_out)
    # ---------------------------------------------------------------- expected observations from S01
    exp_phase, exp_excl, exp_time = {}, {}, {}
    for rec in scope:
        row = s01_led[rec]
        tclass = row['task_class']
        exp_time[rec] = tclass
        for s in segs.get(rec, []):
            if s['status'] == 'excluded':
                exp_excl[s['segment_id']] = s
                continue
            if tclass == 'continuous':
                chk.ok('s01:continuous_has_no_segments', False, rec)
            sides = {'L': ['left'], 'R': ['right'], 'both': ['left', 'right']}[s['side']]
            for sd in sides:
                exp_phase[(rec, s['segment_id'], sd)] = (s, 'individual_cycle' if tclass == 'gait' else 'transfer')
    # ---------------------------------------------------------------- read the sidecars
    observations = lines(exp_root / 'observations.jsonl')
    exclusions = lines(exp_root / 'exclusions.jsonl')
    windows = lines(exp_root / 'authors_windows.jsonl')
    recordings = lines(exp_root / 'recordings.jsonl')
    chk.ok('accounting:recordings_each_once', sorted(r['recording'] for r in recordings) == sorted(scope))
    chk.ok('accounting:continuous_only_count',
           sum(r['export_scope'] == 'continuous_only' for r in recordings) == sum(v == 'continuous' for v in exp_time.values()))
    chk.ok('accounting:continuous_only_exactly_the_continuous_tasks',
           all((r['export_scope'] == 'continuous_only') == (exp_time[r['recording']] == 'continuous') for r in recordings))
    chk.ok('accounting:exclusions_equal_s01',
           sorted((e['segment_id'], e['reason']) for e in exclusions) == sorted((k, v['reason']) for k, v in exp_excl.items()))
    chk.ok('accounting:every_exclusion_has_reason', all(e.get('reason') for e in exclusions))
    exp_aw = {(w['file'], w['key'], w['row'], w['recording']): w for rec in scope for w in aw.get(rec, [])}
    got_aw = {(w['file'], w['key'], w['row'], w['recording']): w for w in windows}
    chk.ok('accounting:authors_windows_equal_s01', set(exp_aw) == set(got_aw) and len(windows) == len(exp_aw))
    obs_phase_keys = {(o['source_recording_id'].split('/', 1)[1], o['observation_id'], o['reference_side']) for o in observations if o['table'] == 'phase'}
    chk.ok('accounting:observations_jsonl_phase_equals_s01', obs_phase_keys == set(exp_phase) and
           sum(o['table'] == 'phase' for o in observations) == len(exp_phase))
    chk.ok('accounting:observations_jsonl_time_one_per_recording',
           sorted(o['source_recording_id'].split('/', 1)[1] for o in observations if o['table'] == 'time') == sorted(scope))
    for k, w in got_aw.items():
        src = exp_aw.get(k)
        if src is None:
            continue
        if src['status'] == 'matched':
            ids = {(o.split('|')[0], o.split('|')[1]) for o in w['observations']}
            seg = next(s for s in segs[src['recording']] if s['index'] == src['segment_index'])
            want = {(seg['segment_id'], sd) for sd in {'L': ['left'], 'R': ['right'], 'both': ['left', 'right']}[seg['side']]}
            chk.ok('accounting:matched_window_points_at_accepted_span', seg['status'] == 'accepted', f'{k}')
            chk.ok('accounting:matched_window_exported', w['fate'] == 'exported' and ids == want, f'{k}')
        else:
            chk.ok('accounting:missed_window_has_reason_and_no_observation',
                   w['fate'] == 'not_exported' and bool(src['reason']) and not w['observations'], f'{k}')
    # ---------------------------------------------------------------- stream phase.parquet
    sig_phase = expected_signal_names('phase')
    sig_time = expected_signal_names('time')
    stats = {'max_abs_diff': 0.0}
    cache = {'rec': None, 'c06': None, 'm01': None, 'time': None}

    def inputs(rec):
        if cache['rec'] != rec:
            ce, me = c06_led[rec], m01_led[rec]
            cpath, mpath = c06_root / ce['output']['file'], m01_root / me['output']['file']
            chk.ok('inputs:c06_sha_equals_ledger', sha256(cpath) == ce['output']['sha256'], rec)
            chk.ok('inputs:m01_sha_equals_ledger', sha256(mpath) == me['output']['sha256'], rec)
            c, m = load_arrays(cpath), load_arrays(mpath)
            chk.ok('inputs:clock_equal', bool(np.array_equal(c['time_s'], m['time_s'])), rec)
            cache.update(rec=rec, c06=c, m01=m, time=c['time_s'])
        return cache['c06'], cache['m01'], cache['time']

    def source_array(fam, name, sign, c, m):
        table = c if fam == 'c06' else m
        if name not in table:
            raise AuditError(f'source column {name} not found in {fam}')
        return table[name] * sign if sign != 1.0 else table[name]

    seen_phase, n_obs_phase, counts = set(), 0, {'individual_cycle': 0, 'transfer': 0}
    pf = pq.ParquetFile(str(exp_root / 'phase.parquet'), buffer_size=0)
    names = pf.schema_arrow.names
    want_names = ID_COLUMNS + ['phase_ipsi'] + CLOCK_COLUMNS + ['held_signals'] + sig_phase
    chk.ok('schema:phase_columns', names == want_names, 'phase columns differ from the independent list')
    max_group = max(pf.metadata.row_group(i).num_rows for i in range(pf.metadata.num_row_groups)) if pf.metadata.num_row_groups else 0
    chk.ok('streaming:phase_row_group_at_most_3000_rows', max_group <= 3000, str(max_group))
    grid = np.linspace(0.0, 100.0, 150)
    obs_by_key = {(o['source_recording_id'], o['observation_id'], o['reference_side']): o for o in observations if o['table'] == 'phase'}
    for gi in range(pf.metadata.num_row_groups):
        tables = list(pf.iter_batches(READ_BATCH, row_groups=[gi], use_threads=False))
        if len(tables) != 1:
            raise AuditError('row group larger than one batch')
        batch = tables[0]
        n = batch.num_rows
        chk.ok('grid:row_group_is_whole_observations', n % 150 == 0, f'group {gi} has {n} rows')
        cols = {nm: batch.column(nm).to_numpy(zero_copy_only=False) for nm in names}
        for lo in range(0, n - n % 150, 150):
            sl = slice(lo, lo + 150)
            idents = {c: cols[c][sl] for c in ID_COLUMNS}
            const = all(len(set(idents[c].tolist())) == 1 for c in ID_COLUMNS) and \
                len(set(cols['held_signals'][sl].tolist())) == 1 and all(len(set(cols[c][sl].tolist())) == 1 for c in CLOCK_COLUMNS)
            if not chk.ok('metadata:constant_within_observation', const, f'group {gi} offset {lo}'):
                continue
            ident = {c: str(idents[c][0]) for c in ID_COLUMNS}
            rec = ident['source_recording_id'].split('/', 1)[1]
            key = (rec, ident['observation_id'], ident['reference_side'])
            chk.ok('identity:unique_composite', key not in seen_phase, str(key))
            seen_phase.add(key)
            exp = exp_phase.get(key)
            if not chk.ok('identity:observation_expected_from_s01', exp is not None, str(key)):
                continue
            seg, otype = exp
            counts[otype] += 1
            chk.ok('identity:fields',
                   ident['subject'] == subject and ident['source_recording_id'] == f'{subject}/{rec}' and ident['observation_type'] == otype
                   and ident['reference_side'] in ('left', 'right') and all(ident[c].strip() for c in ID_COLUMNS), str(key))
            chk.ok('grid:phase_exact_150', bool(np.array_equal(cols['phase_ipsi'][sl], grid)), str(key))
            c, m, t = inputs(rec)
            a, b = seg['start_index'], seg['end_index']
            chk.ok('clock:source_times_from_recording',
                   float(cols['source_start_time_s'][lo]) == float(t[a]) and float(cols['source_end_time_s'][lo]) == float(t[b])
                   and abs(float(t[a]) - seg['start_s']) < 1e-9 and abs(float(t[b]) - seg['end_s']) < 1e-9, str(key))
            # labels and metadata
            info = json.loads(ident['task_info'])
            label = authors_label_of(rec, seg['authors_file']) if seg['label_source'] == 'authors_window' else None
            chk.ok('labels:authors_label_only_where_s01_matched',
                   (info.get('authors_label') == label) and (info.get('label_source') == seg['label_source']) and
                   ((label is not None) == bool(seg['authors_match'])) and (info.get('authors_file') == seg['authors_file']), str(key))
            task_name = s01_led[rec]['task']
            fact = facts.get(task_name, {'header_speed': None, 'labels': {}})
            if 'speed_m_s' in info:
                allowed = fact['header_speed'] if label is None or label not in fact['labels'] or fact['labels'][label]['speed'] is None \
                    else fact['labels'][label]['speed']
                chk.ok('labels:speed_traceable_to_readme', allowed is not None and abs(info['speed_m_s'] - allowed) < 1e-12, f'{key} {info.get("speed_m_s")}')
            if 'incline_deg' in info:
                want_inc = fact['labels'].get(label, {}).get('incline') if label is not None else None
                chk.ok('labels:incline_only_from_label_text', want_inc is not None and info['incline_deg'] == want_inc, str(key))
            if label is None:
                chk.ok('labels:unknown_has_no_label_dependent_fields',
                       not any(k in info for k in ('incline_deg', 'weight_lb')) and
                       (task_name not in ('normal_walk', 'incline_walk', 'jump') or ident['task'] == 'functional_task'), str(key))
            else:
                chk.ok('labels:run_hop_families_follow_label',
                       (ident['task'] == 'run') == (task_name == 'normal_walk' and label in ('2-0', '2-5')) and
                       (ident['task'] == 'hop') == (task_name == 'jump' and label == 'hop'), str(key))
            if task_name == 'stairs':
                n_pass = int(re.fullmatch(r'stairs_1_(\d+)', rec).group(1))
                chk.ok('labels:stairs_direction_matches_pass_list', ident['task'] == ('stair_ascent' if n_pass % 2 else 'stair_descent')
                       and info.get('stair_rise_m') == 0.152 and 'pass_number' in info and 'step_number' not in info, str(key))
            chk.ok('labels:no_curb_or_step_height', not any(k in info for k in ('curb_height_m', 'step_height_m', 'height_m')), str(key))
            m_entry = m01_led[rec]
            chk.ok('notes:mass_note_matches_m01',
                   info.get('mass_note_key') == (('rescaled_' + m_entry['how_known']) if m_entry['action'] == 'rescale' else m_entry['note_key'])
                   and info.get('mass_note') and info['mass_note_key'] in MASS_KEYS, str(key))
            chk.ok('notes:ab09_limit_exactly_where_audit_lists_no_mass',
                   bool([x for x in info['limits'] if x.startswith('AB09 divisor limit')]) == (
                       subject == 'AB09' and m_entry['action'] == 'rescale' and m_entry['how_known'] == 'estimated' and
                       m_entry['audit_provenance'].get('plausible_divisors_kg') == []), str(key))
            chk.ok('notes:ab07_limit', bool([x for x in info['limits'] if x.startswith('AB07 right-foot')]) == (subject == 'AB07'), str(key))
            chk.ok('notes:curb_up_note', bool([x for x in info['limits'] if x.startswith('curb_up')]) == (task_name == 'curb_up'), str(key))
            sm = json.loads(ident['subject_metadata'])
            chk.ok('mass:body_mass_from_readme', sm.get('body_mass_kg') == mass and m_entry['body_weight_mass_kg'] == mass, str(key))
            # values
            held = json.loads(str(cols['held_signals'][lo]))
            missing = []
            for nm in sig_phase:
                fam, src, sign, hkey = decode(nm, ident['reference_side'], 'phase')
                x = source_array(fam, src, sign, c, m)
                exp_vals = interp_time(t, x, a, b)
                got = cols[nm][sl]
                xs = x[a:b + 1]
                scale = float(np.abs(xs[np.isfinite(xs)]).max()) if np.isfinite(xs).any() else 1.0
                compare(exp_vals, got, chk, 'phase_signal', stats, scale)
                if not np.isfinite(got).any():
                    missing.append(nm)
                if 'knee_flexion_moment' in nm:
                    src_pub = source_array('m01', src, 1.0, c, m)
                    chk.ok('signs:knee_moment_is_minus_published', bool(np.allclose(got, -interp_time(t, src_pub, a, b), rtol=RTOL, atol=ATOL, equal_nan=True)), str(key))
                if nm.endswith('_BW'):
                    n_name = nm[:-3] + '_N'
                    chk.ok('mass:bw_times_mass_g_equals_newtons',
                           bool(np.allclose(got * mass * G, cols[n_name][sl], rtol=1e-9, atol=1e-9, equal_nan=True)), f'{key} {nm}')
                if hkey is not None and hkey in c06_led[rec]['held_columns']:
                    chk.ok('held:c06_held_columns_have_no_values', not np.isfinite(got).any(), f'{key} {nm}')
            chk.ok('held:held_signals_equals_missing_columns', sorted(held) == sorted(missing) and all(isinstance(v, str) and v for v in held.values()), str(key))
            side_ref = ident['reference_side']
            chk.ok('identity:ipsi_is_reference_leg',
                   bool(np.allclose(cols['hip_flexion_angle_ipsi_rad'][sl], interp_time(t, c[f'hip_flexion_angle_{side_ref}_rad'], a, b),
                                    rtol=RTOL, atol=ATOL, equal_nan=True)), str(key))
            o = obs_by_key.get((ident['source_recording_id'], ident['observation_id'], ident['reference_side']))
            chk.ok('lineage:observations_jsonl_line', o is not None and o['task'] == ident['task'] and o['task_id'] == ident['task_id']
                   and o['c06_sha256'] == c06_led[rec]['output']['sha256'] and o['m01_sha256'] == m_entry['output']['sha256'], str(key))
            n_obs_phase += 1
    chk.ok('accounting:phase_observations_equal_s01', seen_phase == set(exp_phase) and n_obs_phase == len(exp_phase), f'{len(seen_phase)} vs {len(exp_phase)}')
    chk.ok('accounting:no_excluded_segment_exported', not (set(k[1] for k in seen_phase) & set(exp_excl)))
    # ---------------------------------------------------------------- stream time.parquet
    pt = pq.ParquetFile(str(exp_root / 'time.parquet'), buffer_size=0)
    tnames = pt.schema_arrow.names
    want_t = ID_COLUMNS + ['time_s'] + CLOCK_COLUMNS + ['held_signals'] + sig_time
    chk.ok('schema:time_columns', tnames == want_t, 'time columns differ from the independent list')
    max_t = max(pt.metadata.row_group(i).num_rows for i in range(pt.metadata.num_row_groups)) if pt.metadata.num_row_groups else 0
    chk.ok('streaming:time_row_group_at_most_4096_rows', max_t <= 4096, str(max_t))
    offsets, seen_time, time_rows = {}, [], 0
    for gi in range(pt.metadata.num_row_groups):
        batches = list(pt.iter_batches(READ_BATCH, row_groups=[gi], use_threads=False))
        batch = batches[0]
        chk.ok('streaming:time_group_single_batch', len(batches) == 1)
        n = batch.num_rows
        cols = {nm: batch.column(nm).to_numpy(zero_copy_only=False) for nm in tnames}
        sid = str(cols['source_recording_id'][0])
        rec = sid.split('/', 1)[1]
        const = all(len(set(cols[c].tolist())) == 1 for c in ID_COLUMNS + ['held_signals']) and all(len(set(cols[c].tolist())) == 1 for c in CLOCK_COLUMNS)
        chk.ok('metadata:time_constant_within_group', const, f'group {gi}')
        if rec not in offsets:
            offsets[rec] = 0
            seen_time.append(rec)
            c, m, t = inputs(rec)
            info = json.loads(str(cols['task_info'][0]))
            held_json = json.loads(str(cols['held_signals'][0]))
            chk.ok('time:identity', str(cols['observation_id'][0]) == f'{sid}/continuous' and str(cols['reference_side'][0]) == 'none'
                   and str(cols['observation_type'][0]) == 'continuous_recording' and str(cols['subject'][0]) == subject, rec)
            chk.ok('time:clock_known', float(cols['source_start_time_s'][0]) == float(t[0]) and float(cols['source_end_time_s'][0]) == float(t[-1]), rec)
            chk.ok('time:export_scope', info['export_scope'] == ('continuous_only' if exp_time[rec] == 'continuous' else 'continuous_and_segments'), rec)
            chk.ok('time:no_label_invented', info.get('label_source') == 'unknown' and info.get('authors_label') is None and 'incline_deg' not in info, rec)
            miss = sorted(nm for nm in sig_time if not np.isfinite(source_array(*decode(nm, 'left', 'time')[:3], c, m)).any())
            o = next(o for o in observations if o['table'] == 'time' and o['source_recording_id'] == sid)
            chk.ok('held:time_held_signals_equal_missing', sorted(o['held_signals']) == miss and sorted(held_json) == miss
                   and all(isinstance(v, str) and v for v in held_json.values()), rec)
        else:
            c, m, t = inputs(rec)
        lo = offsets[rec]
        chk.ok('time:rows_within_recording', lo + n <= len(t), rec)
        chk.ok('time:time_s_equals_source_clock', bool(np.array_equal(cols['time_s'], t[lo:lo + n])), rec)
        for nm in sig_time:
            fam, src, sign, hkey = decode(nm, 'left', 'time')
            x = source_array(fam, src, sign, c, m)
            chk.ok('time_signal:bit_equal', bool(np.array_equal(cols[nm], x[lo:lo + n], equal_nan=True)), f'{rec} {nm}')
            if hkey is not None and hkey in c06_led[rec]['held_columns']:
                chk.ok('held:c06_held_columns_have_no_values', not np.isfinite(x).any(), f'{rec} {nm}')
        offsets[rec] = lo + n
        time_rows += n
    chk.ok('accounting:time_one_continuous_per_recording', sorted(seen_time) == sorted(scope), f'{len(seen_time)} vs {len(scope)}')
    chk.ok('accounting:time_rows_complete', all(offsets.get(r) == s01_led[r]['rows'] for r in scope))
    # ---------------------------------------------------------------- summary
    chk.ok('accounting:counts_in_run_summary',
           summary['observations']['individual_cycle'] == counts['individual_cycle'] and summary['observations']['transfer'] == counts['transfer']
           and summary['observations']['continuous_recording'] == len(seen_time))
    report = {'subject': subject, 'export_root': args.export_root, 'recordings_checked': len(scope),
              'observations': {'individual_cycle': counts['individual_cycle'], 'transfer': counts['transfer'],
                               'continuous_recording': len(seen_time)},
              'phase_rows': pf.metadata.num_rows, 'time_rows': time_rows, 'exclusions': len(exclusions),
              'exclusions_equal_s01': len(exclusions) == len(exp_excl),
              'authors_windows': len(windows), 'authors_windows_exported': sum(w['fate'] == 'exported' for w in windows),
              'max_abs_diff_phase_values': stats['max_abs_diff'], 'tolerance': {'rtol': RTOL, 'atol': ATOL},
              'checks': chk.items, 'failures': chk.failures, 'peak_rss_mib': peak_rss_mib(),
              'status': 'pass' if not chk.failures else 'fail', 'scientific_approval': False}
    (out_root / 'audit_report.tmp').write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + '\n')
    (out_root / 'audit_report.tmp').replace(out_root / 'audit_report.json')
    return 0 if not chk.failures else 1


def make_spec(args):
    from contributor_tools import guarded_launcher as gl
    command = ['python3', 'contributor_tools/audit_gt23_e01.py', args.kind, '--output-root', args.output_root]
    bindings = {c: gl.sha256_file(ROOT / c) for c in CODE}
    bindings[README] = gl.sha256_file(ROOT / README)
    if args.kind == 'audit':
        command += ['--subject', args.subject, '--export-root', args.export_root]
        for r in args.records or []:
            command += ['--records', r]
        bindings[f'{args.export_root}/run_summary.json'] = gl.sha256_file(ROOT / args.export_root / 'run_summary.json')
        for k, p in (('c06', f'{BASE}/gt23_c06_batch3_{args.subject}'), ('m01', f'{BASE}/gt23_m01_batch_{args.subject}'),
                     ('s01', f'{BASE}/gt23_s01_batch_{args.subject}')):
            bindings[f'{p}/ledger.jsonl'] = gl.sha256_file(ROOT / p / 'ledger.jsonl')
        for n in ('segments.jsonl', 'authors_windows.jsonl'):
            bindings[f'{BASE}/gt23_s01_batch_{args.subject}/{n}'] = gl.sha256_file(ROOT / BASE / f'gt23_s01_batch_{args.subject}' / n)
        names = ['audit_report.json']
    else:
        command += ['--roots'] + list(args.roots) + ['--exports'] + list(args.exports)
        for r in list(args.roots) + list(args.exports):
            bindings[f'{r}/audit_report.json' if r in args.roots else f'{r}/run_summary.json'] = gl.sha256_file(
                ROOT / r / ('audit_report.json' if r in args.roots else 'run_summary.json'))
        names = ['audit_summary.json']
    spec = {'job_id': args.job_id, 'command': command, 'cwd': str(ROOT), 'output_root': args.output_root,
            'receipt_path': args.receipt, 'bindings': bindings, 'timeout_seconds': 3600, 'kill_after_seconds': 30,
            'poll_seconds': 15, 'startup_memory_mib': {'linux': 3584, 'windows': 2816},
            'runtime_memory_mib': {'linux': 2048, 'windows': 2048}, 'expected_output_names': names, 'address_space_mib': 768}
    with Path(args.spec_out).open('x') as stream:
        json.dump(spec, stream, indent=2)
        stream.write('\n')
    return 0


def run_summary(args):
    out_root = ROOT / args.output_root
    out_root.mkdir(parents=True, exist_ok=False)
    reports = [json.loads((ROOT / r / 'audit_report.json').read_text()) for r in args.roots]
    exports = [json.loads((ROOT / r / 'run_summary.json').read_text()) for r in args.exports]
    if [r['subject'] for r in reports] != [e['subject'] for e in exports]:
        raise AuditError('audit and export participants differ')
    kinds = {k: sum(r['observations'][k] for r in reports) for k in ('individual_cycle', 'transfer', 'continuous_recording')}
    summary = {'participants': [r['subject'] for r in reports], 'status': 'pass' if all(r['status'] == 'pass' for r in reports) else 'fail',
               'failures': {r['subject']: r['failures'] for r in reports if r['failures']},
               'recordings_checked': sum(r['recordings_checked'] for r in reports), 'observations_read_back': kinds,
               'export_counts_equal_readback': all(e['observations'] == {'individual_cycle': r['observations']['individual_cycle'],
                                                                     'transfer': r['observations']['transfer'],
                                                                     'continuous_recording': r['observations']['continuous_recording']}
                                                   for r, e in zip(reports, exports)),
               'exclusions': sum(r['exclusions'] for r in reports), 'authors_windows': sum(r['authors_windows'] for r in reports),
               'authors_windows_exported': sum(r['authors_windows_exported'] for r in reports),
               'phase_rows': sum(r['phase_rows'] for r in reports), 'time_rows': sum(r['time_rows'] for r in reports),
               'max_abs_diff_phase_values': max(r['max_abs_diff_phase_values'] for r in reports),
               'peak_rss_mib_by_participant': {r['subject']: r['peak_rss_mib'] for r in reports}, 'scientific_approval': False}
    (out_root / 'audit_summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    return 0 if summary['status'] == 'pass' else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('audit')
    s.add_argument('--output-root', required=True)
    s.add_argument('--export-root', required=True)
    s.add_argument('--subject', required=True, choices=SUBJECTS)
    s.add_argument('--records', action='append')
    s.add_argument('--base', default=BASE)
    s = sub.add_parser('spec')
    s.add_argument('--kind', choices=('audit', 'summary'), required=True)
    s.add_argument('--job-id', required=True)
    s.add_argument('--output-root', required=True)
    s.add_argument('--receipt', required=True)
    s.add_argument('--spec-out', required=True)
    s.add_argument('--subject', choices=SUBJECTS)
    s.add_argument('--export-root')
    s.add_argument('--records', action='append')
    s.add_argument('--roots', nargs='*')
    s.add_argument('--exports', nargs='*')
    s = sub.add_parser('summary')
    s.add_argument('--output-root', required=True)
    s.add_argument('--roots', nargs='+', required=True)
    s.add_argument('--exports', nargs='+', required=True)
    args = p.parse_args(argv)
    return {'audit': run_audit, 'spec': make_spec, 'summary': run_summary}[args.cmd](args)


if __name__ == '__main__':
    raise SystemExit(main())
