"""GT23-M01 mass step runner (Python only, no MATLAB).

Subcommands
  run      One participant (or named recordings). Per recording, reads X01 companions (Joint_Moments, Joint_Powers,
           GroundFrame_GRFs; hash-checked against the X01 ledger) and the C06 batch3 output (speeds and force in N;
           hash-checked against the C06 ledger). Writes NEW output root: <recording>.parquet, ledger.jsonl, run_summary.json.
  spec     Writes the guarded-launcher job spec.
  summary  Adds participant roots into counts, factor range, power consistency and the N*m checks.

Output columns: time_s; <joint>_moment_Nm_kg style names for all 12 moment columns and 12 power columns (rescaled in the
52 recordings, identical otherwise); force columns of C06 renamed _N -> _BW, divided by README mass x g.
"""
import argparse
import json
import os
from pathlib import Path
import resource
import sys

os.environ.setdefault('ARROW_DEFAULT_MEMORY_POOL', 'system')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
from contributor_tools import gt23_mass as ms  # noqa: E402
from contributor_tools import gt23_source_reader as rd  # noqa: E402

SOURCE = Path('/mnt/s/locomotion_data/Gtech_2023')
SUBJECTS = ('AB01', 'AB02', 'AB03', 'AB05', 'AB06', 'AB07', 'AB08', 'AB09', 'AB10', 'AB11', 'AB12', 'AB13')
X01_ROOTS = {s: f'converted_datasets/reconversion_v2/gt23_x01_batch_{s}' + ('_r2' if s == 'AB01' else '') for s in SUBJECTS}
C06_ROOTS = {s: f'converted_datasets/reconversion_v2/gt23_c06_batch3_{s}' for s in SUBJECTS}
AUDIT = 'docs/quality/audits/gt23-c05-rescale-error.json'
README = 'docs/quality/audits/source_evidence/gt23/publisher-readme.txt'
CODE = ('contributor_tools/gt23_mass.py', 'contributor_tools/run_gt23_m01.py', 'contributor_tools/gt23_source_reader.py',
        'contributor_tools/guarded_launcher.py')
WORD = {'L': 'left', 'R': 'right'}
# power = moment x (sign x our speed): the published knee coordinate is the negative of knee flexion (C06)
JOINTS = (('hip', 'hip_flexion_{s}_moment', 'hip_flexion_power_{s}', 'hip_flexion_velocity_{w}_rad_s', 1.0),
          ('knee', 'knee_angle_{s}_moment', 'knee_power_{s}', 'knee_flexion_velocity_{w}_rad_s', -1.0),
          ('ankle', 'ankle_angle_{s}_moment', 'ankle_power_{s}', 'ankle_dorsiflexion_velocity_{w}_rad_s', 1.0))
GRF_SRC = {'grf_lab_x_{w}_N': '{S}ForceX', 'grf_lab_y_{w}_N': '{S}ForceY_Vertical', 'grf_lab_z_{w}_N': '{S}ForceZ'}
ID_TOLERANCE_NM = 1e-3


class RunError(RuntimeError):
    pass


def peak_rss_mib():
    return round(max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) / 1024, 1)


def read_all(path, columns=None):
    pf = pq.ParquetFile(str(path), buffer_size=0)
    names = columns or list(pf.schema_arrow.names)
    parts = [b.to_pandas() for b in pf.iter_batches(batch_size=4096, columns=list(names), use_threads=False)]
    df = pd.concat(parts, ignore_index=True)
    return {c: df[c].to_numpy(np.float64) for c in names}


def write_parquet(path, cols, metadata):
    schema = pa.schema([(k, pa.float64()) for k in cols], metadata=metadata)
    table = pa.Table.from_arrays([pa.array(np.ascontiguousarray(v), type=pa.float64(), from_pandas=False) for v in cols.values()], schema=schema)
    with pq.ParquetWriter(str(path), schema, compression='zstd') as w:
        w.write_table(table, row_group_size=4096)


def same(a, b):
    return bool(np.array_equal(a, b, equal_nan=True))


def load_plan():
    masses = ms.parse_readme_masses((ROOT / README).read_text())
    audit = json.loads((ROOT / AUDIT).read_text())
    return masses, ms.build_plan(audit['trials'], masses)


def read_inverse_dynamics(subject, part, columns):
    path = SOURCE / 'RawData' / subject / 'MotionFile_EH' / 'inverse_dynamics.sto'
    if not path.exists():
        return None, 'no inverse_dynamics.sto for this participant'
    if rd.sha256_file(path) != part['motion_files']['inverse_dynamics.sto']['sha256']:
        raise RunError(f'{subject}: inverse_dynamics.sto hash differs from the X01 participant file')
    parts = []
    for chunk in pd.read_csv(path, sep='\t', skiprows=6, usecols=lambda c: c.strip() in set(columns) | {'time'}, chunksize=20000):
        chunk.columns = [c.strip() for c in chunk.columns]
        parts.append(chunk)
    df = pd.concat(parts, ignore_index=True)
    return df, None


def process_recording(subject, rec, entry, mass_bw, x01, c06, x01_root, c06_root, part, id_cache):
    comp = ROOT / x01_root / rec
    for ch in ('Joint_Moments', 'Joint_Powers', 'GroundFrame_GRFs'):
        if rd.sha256_file(comp / f'{ch}.parquet') != x01['channels'][ch]['parquet_sha256']:
            raise RunError(f'{rec}: {ch} companion hash differs from the X01 ledger')
    c06_path = ROOT / c06_root / f'{rec}.parquet'
    if rd.sha256_file(c06_path) != c06['output']['sha256']:
        raise RunError(f'{rec}: C06 output hash differs from the C06 ledger')
    mom = read_all(comp / 'Joint_Moments.parquet')
    pwr = read_all(comp / 'Joint_Powers.parquet')
    grf = read_all(comp / 'GroundFrame_GRFs.parquet')
    c = read_all(c06_path)
    n = len(mom['time'])
    if not (len(pwr['time']) == len(grf['time']) == len(c['time_s']) == n):
        raise RunError(f'{rec}: row counts differ across moments, powers, force and C06 output')
    if not same(c['time_s'], mom['time']):
        raise RunError(f'{rec}: C06 clock differs from the source clock')
    factor = entry['factor']
    out = {'time_s': mom['time']}
    out_units = {}
    mcols = [k for k in mom if k != 'time']
    pcols = [k for k in pwr if k != 'time']
    for k in mcols:
        out[f'{k}_{ms.UNITS["moment"]}'] = ms.scale(mom[k], factor)
        out_units[f'{k}_{ms.UNITS["moment"]}'] = 'N*m/kg'
    for k in pcols:
        out[f'{k}_{ms.UNITS["power"]}'] = ms.scale(pwr[k], factor)
        out_units[f'{k}_{ms.UNITS["power"]}'] = 'W/kg'
    # forces: only the body-weight columns depend on a mass. The N columns of C06 are checked equal to the plate columns.
    force_cols, n_equal = [], {}
    for k in c:
        if not k.endswith('_N'):
            continue
        force_cols.append(k)
        out[k[:-2] + '_BW'] = ms.to_body_weights(c[k], mass_bw)
        out_units[k[:-2] + '_BW'] = 'body weights'
    for S in 'LR':
        for pat, src in GRF_SRC.items():
            name = pat.format(w=WORD[S])
            n_equal[name] = same(c[name], grf[src.format(S=S)])
    # same-factor proof: scaled / source for every column
    proof = {}
    if factor is not None:
        ratios = []
        for src, dst in [(mom, 'moment'), (pwr, 'power')]:
            for k in src:
                if k == 'time':
                    continue
                o = out[f'{k}_{ms.UNITS[dst]}']
                ok = np.isfinite(src[k]) & (src[k] != 0)
                ratios.append(float(np.max(np.abs(o[ok] / src[k][ok] - factor))) if ok.any() else 0.0)
                if not same(np.isfinite(o), np.isfinite(src[k])):
                    raise RunError(f'{rec}: rescale changed which samples are finite')
        proof['max_abs_ratio_minus_factor'] = max(ratios)
    else:
        for src, dst in [(mom, 'moment'), (pwr, 'power')]:
            for k in src:
                if k != 'time' and not same(out[f'{k}_{ms.UNITS[dst]}'], src[k]):
                    raise RunError(f'{rec}: kept recording changed in {k}')
        proof['kept_identical_to_source'] = True
    # power = moment x speed, before and after
    consistency = {}
    for S in 'LR':
        s, w = S.lower(), WORD[S]
        for jn, mname, pname, vname, sign in JOINTS:
            mn, pn, vn = mname.format(s=s), pname.format(s=s), vname.format(w=w)
            before = ms.power_consistency(mom[mn], pwr[pn], c[vn], sign)
            after = ms.power_consistency(out[f'{mn}_{ms.UNITS["moment"]}'], out[f'{pn}_{ms.UNITS["power"]}'], c[vn], sign)
            consistency[f'{jn}_{s}'] = {'before': before, 'after': after}
    # N*m inverse dynamics (exact-tier recordings only; local file covers normal walking)
    id_check = None
    if entry.get('audit_provenance', {}).get('tier') == 'exact' or entry.get('audit_class') == 'own_mass_only' and rec == 'normal_walk_1':
        mass_for_nm = entry['mass_used_kg'] if factor is not None else entry['own_mass_kg']
        if subject not in id_cache:
            id_cache[subject] = read_inverse_dynamics(subject, part, mcols)
        df, why = id_cache[subject]
        if df is None:
            id_check = {'available': False, 'reason': why}
        elif len(df) != n:
            id_check = {'available': False, 'reason': f'inverse_dynamics.sto has {len(df)} rows, recording has {n}'}
        else:
            per = {}
            for k in mcols:
                col = out[f'{k}_{ms.UNITS["moment"]}']
                per[k] = ms.nm_check(col, df[k].to_numpy(np.float64), entry['own_mass_kg'])
            mx = max(v.get('max_abs_nm', 0.0) for v in per.values())
            peak = max(v.get('peak_inverse_dynamics_nm', 0.0) for v in per.values())
            id_check = {'available': True, 'mass_multiplied_kg': entry['own_mass_kg'], 'published_mass_kg_expected': mass_for_nm,
                        'time_max_abs_s': float(np.max(np.abs(df['time'].to_numpy(np.float64) - mom['time']))),
                        'max_abs_nm_all_columns': mx, 'peak_abs_inverse_dynamics_nm': peak, 'max_abs_over_peak': mx / peak if peak else None, 'within_tolerance': bool(mx <= ID_TOLERANCE_NM),
                        'tolerance_nm': ID_TOLERANCE_NM, 'per_column': per}
    # standing check helper: total vertical force in body weights
    vz = c['grf_lab_y_left_N'] + c['grf_lab_y_right_N']
    loaded = np.isfinite(vz) & (vz > 0.5 * mass_bw * ms.G)
    stand = {'loaded_samples': int(loaded.sum()),
             'median_total_vertical_BW': float(np.median(vz[loaded]) / (mass_bw * ms.G)) if loaded.any() else None,
             'median_implied_mass_kg': float(np.median(vz[loaded]) / ms.G) if loaded.any() else None}
    report = {'subject': subject, 'recording': rec, 'rows': n, 'action': entry['action'], 'own_mass_kg': entry['own_mass_kg'],
              'mass_used_kg': entry['mass_used_kg'], 'factor': factor, 'how_known': entry['how'],
              'note': entry['note'], 'note_key': entry.get('note_key', 'rescaled'), 'audit_class': entry['audit_class'],
              'audit_provenance': entry.get('audit_provenance'), 'body_weight_mass_kg': mass_bw, 'g_m_s2': ms.G,
              'force_columns_in_N_equal_plate_columns': n_equal, 'force_columns_converted_to_BW': force_cols,
              'rescale_proof': proof, 'power_consistency': consistency, 'inverse_dynamics_check': id_check,
              'loaded_vertical_force': stand, 'units': out_units, 'units_note': ms.README_NOTE}
    return out, report, out_units


def run(args):
    out_root = ROOT / args.output_root
    if out_root.exists() and any(out_root.iterdir()):
        raise RunError(f'{out_root} is not empty; never overwrite')
    out_root.mkdir(parents=True, exist_ok=True)
    subject = args.subject
    masses, plan = load_plan()
    x01_root, c06_root = X01_ROOTS[subject], C06_ROOTS[subject]
    part = json.loads((ROOT / x01_root / 'participant.json').read_text())
    if part['mass_kg']['readme'] != masses[subject]:
        raise RunError('README mass differs from the X01 participant file')
    x01 = {json.loads(l)['recording']: json.loads(l) for l in (ROOT / x01_root / 'ledger.jsonl').read_text().splitlines()}
    c06 = {json.loads(l)['recording']: json.loads(l) for l in (ROOT / c06_root / 'ledger.jsonl').read_text().splitlines()}
    mine = {r for (s, r) in plan if s == subject}
    if mine != set(x01) or mine != set(c06):
        raise RunError('audit, X01 and C06 do not list the same recordings')
    wanted = args.records or sorted(x01)
    id_cache, receipts = {}, []
    with (out_root / 'ledger.jsonl').open('x') as stream:
        for rec in wanted:
            out, rep, units = process_recording(subject, rec, plan[(subject, rec)], masses[subject], x01[rec], c06[rec],
                                                x01_root, c06_root, part, id_cache)
            path = out_root / f'{rec}.parquet'
            write_parquet(path, out, {'units': json.dumps(units), 'note': rep['note'], 'factor': repr(rep['factor'])})
            back = pq.ParquetFile(str(path), buffer_size=0)
            rep['output'] = {'file': f'{rec}.parquet', 'rows': back.metadata.num_rows, 'columns': back.metadata.num_columns,
                             'sha256': rd.sha256_file(path)}
            rep['peak_rss_mib_so_far'] = peak_rss_mib()
            stream.write(json.dumps(rep, sort_keys=True) + '\n')
            stream.flush()
            receipts.append(rep)
    bad = [r['recording'] for r in receipts if not all(r['force_columns_in_N_equal_plate_columns'].values())]
    summary = {'subject': subject, 'recordings_done': len(receipts), 'rescaled': sum(r['action'] == 'rescale' for r in receipts),
               'kept': sum(r['action'] == 'keep' for r in receipts), 'force_n_not_equal_plate': bad,
               'peak_rss_mib': peak_rss_mib(), 'scientific_approval': False,
               'status': 'participant_done_unreviewed' if not bad else 'force_check_failed'}
    tmp = out_root / 'run_summary.tmp'
    tmp.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    tmp.replace(out_root / 'run_summary.json')
    return 0 if not bad else 1


def make_spec(args):
    from contributor_tools import guarded_launcher as gl
    command = ['python3', 'contributor_tools/run_gt23_m01.py', args.kind, '--output-root', args.output_root]
    bindings = {c: gl.sha256_file(ROOT / c) for c in CODE}
    bindings[AUDIT] = gl.sha256_file(ROOT / AUDIT)
    bindings[README] = gl.sha256_file(ROOT / README)
    if args.kind == 'run':
        command += ['--subject', args.subject]
        for r in args.records or []:
            command += ['--records', r]
        for p in (f'{X01_ROOTS[args.subject]}/ledger.jsonl', f'{X01_ROOTS[args.subject]}/participant.json',
                  f'{C06_ROOTS[args.subject]}/ledger.jsonl'):
            bindings[p] = rd.sha256_file(ROOT / p)
        names = ['run_summary.json']
    else:
        command += ['--roots'] + list(args.roots)
        for r in args.roots:
            bindings[f'{r}/run_summary.json'] = rd.sha256_file(ROOT / r / 'run_summary.json')
        names = ['summary.json']
    spec = {'job_id': args.job_id, 'command': command, 'cwd': str(ROOT), 'output_root': args.output_root,
            'receipt_path': args.receipt, 'bindings': bindings, 'timeout_seconds': 3600, 'kill_after_seconds': 30,
            'poll_seconds': 15, 'startup_memory_mib': {'linux': 3584, 'windows': 2816},
            'runtime_memory_mib': {'linux': 2048, 'windows': 2048}, 'expected_output_names': names, 'address_space_mib': 768}
    with Path(args.spec_out).open('x') as stream:
        json.dump(spec, stream, indent=2)
        stream.write('\n')
    return 0


def _stats(values):
    v = [x for x in values if x is not None and np.isfinite(x)]
    return {'n': len(v), 'min': min(v), 'median': float(np.median(v)), 'max': max(v)} if v else {'n': 0}


def summarize(args):
    out_root = ROOT / args.output_root
    out_root.mkdir(parents=True, exist_ok=False)
    masses, plan = load_plan()
    rows = []
    for r in args.roots:
        rows += [json.loads(l) for l in (ROOT / r / 'ledger.jsonl').read_text().splitlines()]
    recs = {(r['subject'], r['recording']) for r in rows}
    if len(rows) != len(recs):
        raise RunError('a recording appears twice')
    resc = [r for r in rows if r['action'] == 'rescale']
    kept = [r for r in rows if r['action'] == 'keep']
    ab03 = [r for r in rows if r['subject'] == 'AB03']
    expected = {k for k, e in plan.items() if e['action'] == 'rescale'}
    counts = {'recordings': len(rows), 'rescaled': len(resc), 'kept': len(kept),
              'rescaled_equal_audit_list': {(r['subject'], r['recording']) for r in resc} == expected,
              'rescaled_exact': sum(r['how_known'] == 'exact' for r in resc), 'rescaled_estimated': sum(r['how_known'] == 'estimated' for r in resc),
              'kept_own_mass_confirmed': sum(r['note_key'] == 'own_mass_confirmed' for r in kept),
              'kept_cannot_be_told': sum(r['note_key'] == 'cannot_be_told' for r in kept),
              'ab03_recordings': len(ab03), 'ab03_body_weight_mass_113_5': sum(r['body_weight_mass_kg'] == 113.5 for r in ab03),
              'every_other_body_weight_mass_is_readme': all(r['body_weight_mass_kg'] == masses[r['subject']] for r in rows)}
    pc = {}
    for label, sel in (('rescaled', resc), ('kept', kept)):
        for phase in ('before', 'after'):
            for key in ('slope', 'r'):
                vals = [j[phase].get(key) for r in sel for j in r['power_consistency'].values()]
                pc[f'{label}_{phase}_{key}'] = _stats(vals)
    pc['max_after_minus_before_slope'] = max(abs((j['after'].get('slope') or 0) - (j['before'].get('slope') or 0))
                                             for r in rows for j in r['power_consistency'].values())
    pc['max_after_minus_before_r'] = max(abs((j['after'].get('r') or 0) - (j['before'].get('r') or 0))
                                         for r in rows for j in r['power_consistency'].values())
    ids = [r for r in rows if r['inverse_dynamics_check']]
    summary = {'counts': counts, 'factor': _stats([r['factor'] for r in resc]),
               'factor_exact': _stats([r['factor'] for r in resc if r['how_known'] == 'exact']),
               'factor_estimated': _stats([r['factor'] for r in resc if r['how_known'] == 'estimated']),
               'power_consistency': pc,
               'inverse_dynamics': [{'subject': r['subject'], 'recording': r['recording'], 'how_known': r['how_known'],
                                     'mass_used_kg': r['mass_used_kg'], 'check': {k: v for k, v in r['inverse_dynamics_check'].items() if k != 'per_column'},
                                     'implied_mass_kg_by_column': {k: v.get('implied_mass_kg') for k, v in (r['inverse_dynamics_check'].get('per_column') or {}).items()}}
                                    for r in ids],
               'force_n_equal_plate_everywhere': all(all(r['force_columns_in_N_equal_plate_columns'].values()) for r in rows),
               'ab03_loaded_vertical_force': {r['recording']: r['loaded_vertical_force'] for r in ab03},
               'scientific_approval': False, 'peak_rss_mib': peak_rss_mib()}
    (out_root / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('run')
    s.add_argument('--output-root', required=True)
    s.add_argument('--subject', required=True, choices=SUBJECTS)
    s.add_argument('--records', action='append')
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
