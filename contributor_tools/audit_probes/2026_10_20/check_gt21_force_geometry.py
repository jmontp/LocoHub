"""Compare native GT21 plate locations with measured foot markers.

Uses the original Osim.correlateForcePlates convention: marker millimetres to
metres, mean heel/toe position, and source positive-y force above 100 N.
Reports evidence only; does not fit force signs or approve anatomical axes.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
import hashlib
import json
from pathlib import Path
import resource
resource.setrlimit(resource.RLIMIT_AS, (768 * 1024**2, 768 * 1024**2))
import numpy as np
import pyarrow.parquet as pq


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--converted', type=Path, help='Optional matching phase export to audit')
    args = parser.parse_args()
    manifest = json.loads((args.probe / 'source_comparison.json').read_text())
    assert manifest['native_status']['status'] == 'completed'
    assert manifest['native_status']['exit_code'] == 0
    for table in manifest['tables']:
        assert digest(args.probe / table['file']) == table['sha256']
    fp = pq.ParquetFile(args.probe / 'source_fp_data.parquet').read(use_threads=False).to_pandas(use_threads=False)
    names = ['Header'] + [f'{side}_{marker}_{axis}' for side in ('L', 'R')
                         for marker in ('Heel', 'Toe_Tip', 'ASIS', 'PSIS') for axis in 'xyz']
    markers = pq.ParquetFile(args.probe / 'source_markers_data.parquet').read(columns=names,
                            use_threads=False).to_pandas(use_threads=False)
    ft, mt = fp.Header.to_numpy(), markers.Header.to_numpy()
    assert np.isfinite(ft).all() and np.isfinite(mt).all()
    assert (np.diff(ft) > 0).all() and (np.diff(mt) > 0).all()
    inside = (mt >= ft[0]) & (mt <= ft[-1])
    feet = {side: sum(markers[[f'{side}_{marker}_{axis}' for axis in 'xyz']].to_numpy()
                      for marker in ('Heel', 'Toe_Tip')) / 2000 for side in ('L', 'R')}
    # Anterior/posterior and left/right marker labels supply independent
    # orientation evidence without comparing forces against joint moments.
    pelvis = {f'{side}_{landmark}': markers[[f'{side}_{landmark}_{axis}' for axis in 'xyz']].to_numpy()
              for side in ('L', 'R') for landmark in ('ASIS', 'PSIS')}
    forward = (pelvis['L_ASIS'] + pelvis['R_ASIS'] - pelvis['L_PSIS'] - pelvis['R_PSIS']) / 2
    right = pelvis['R_ASIS'] - pelvis['L_ASIS']
    headings = {}
    for label, vector in [('posterior_to_anterior_pelvis', forward), ('left_to_right_pelvis', right)]:
        length = np.linalg.norm(vector, axis=1)
        usable = np.isfinite(vector).all(axis=1) & (length > 0)
        direction = vector[usable] / length[usable, None]
        headings[label] = {'usable_samples': int(usable.sum()), 'unusable_samples': int((~usable).sum()),
                           'xyz_unit_vector_quantiles_05_50_95': np.quantile(direction, [.05, .5, .95], axis=0).tolist()
                           if usable.any() else None}
    plates = []
    for prefix in [name[:-3] for name in fp.columns if name.endswith('_vy')]:
        force = np.interp(mt, ft, fp[prefix + '_vy'])
        cop = np.column_stack([np.interp(mt, ft, fp[f'{prefix}_p{axis}']) for axis in 'xyz'])
        contact = inside & (force > 100)
        valid = contact & np.isfinite(cop).all(axis=1)
        valid &= np.isfinite(feet['L']).all(axis=1) & np.isfinite(feet['R']).all(axis=1)
        distances = {side: np.linalg.norm(cop[valid] - feet[side][valid], axis=1) for side in feet}
        n = int(valid.sum())
        fractions = {side: float(np.mean(distances[side] < distances['R' if side == 'L' else 'L']))
                     if n else None for side in feet}
        plates.append({'plate': prefix, 'contact_samples': int(contact.sum()), 'usable_samples': n,
                       'missing_geometry_samples': int((contact & ~valid).sum()),
                       'nearer_foot_fraction': fractions,
                       'distance_m_quantiles_05_50_95': {side: np.quantile(value, [.05,.5,.95]).tolist()
                                                       if n else None for side,value in distances.items()},
                       'unambiguous_majority_side': ('L' if fractions['L'] >= 2/3 else
                                                    'R' if fractions['R'] >= 2/3 else None) if n else None})
    exported_comparison = None
    if args.converted:
        comparisons = []
        columns = ['observation_id', 'source_recording_id', 'reference_side', 'subject_metadata',
                   'source_start_time_s', 'source_end_time_s']
        columns += [f'grf_{axis}_{side}_BW' for side in ('ipsi', 'contra') for axis in ('anterior', 'vertical')]
        for batch in pq.ParquetFile(args.converted).iter_batches(batch_size=150, columns=columns, use_threads=False):
            frame = batch.to_pandas(use_threads=False)
            assert len(frame) == 150 and frame.observation_id.nunique() == 1
            row = frame.iloc[0]
            # The probe manifest identifies the actual source recording.
            source_paths = list(manifest['inputs']['sources'])
            suffix = str(row.source_recording_id).split(':', 1)[1]
            pieces = suffix.split('/')
            assert any('/'.join(pieces[:-1] + ['fp', pieces[-1]]) in path for path in source_paths)
            times = np.linspace(row.source_start_time_s, row.source_end_time_s, 150)
            assert times[0] >= ft[0] and times[-1] <= ft[-1]
            mass = json.loads(row.subject_metadata)['weight_kg']
            assert np.isfinite(mass) and mass > 0
            for side in ('ipsi', 'contra'):
                anatomical = row.reference_side if side == 'ipsi' else ('left' if row.reference_side == 'right' else 'right')
                prefix = 'Treadmill_' + anatomical[0].upper()
                record = {'observation_id': row.observation_id, 'side': side, 'anatomical_leg': anatomical}
                for axis, suffix in [('anterior', 'vz'), ('vertical', 'vy')]:
                    raw = np.interp(times, ft, fp[prefix + '_' + suffix]) / (mass * 9.81)
                    output = frame[f'grf_{axis}_{side}_BW'].to_numpy()
                    finite = np.isfinite(raw) & np.isfinite(output)
                    errors = {label: float(np.max(np.abs(output[finite] - sign * raw[finite]))) if finite.any() else None
                              for label, sign in [('source_positive', 1), ('source_negative', -1)]}
                    record[axis] = {'finite_values': int(finite.sum()), 'max_abs_errors_BW': errors,
                                    'matching_signs_at_1e_minus_7': [label for label,error in errors.items()
                                                                  if finite.all() and error is not None and error <= 1e-7]}
                comparisons.append(record)
        exported_comparison = {'path': str(args.converted), 'sha256': digest(args.converted), 'cycles': len(comparisons)//2,
                               'leg_comparisons': comparisons,
                               'note': 'Sign matching describes existing outputs; it does not choose a sign by optimization.'}
    source_code = Path('contributor_tools/conversion_scripts/Gtech_2021/CAMARGO_ET_AL_J_BIOMECH_DATASET/scripts (1)/MoCapTools/+Osim/correlateForcePlates.m')
    result = {'status': 'source_geometry_diagnostic', 'scientific_approval': False,
              'source_readback_sha256': digest(args.probe / 'source_comparison.json'),
              'original_geometry_code_sha256': digest(source_code), 'probe_sha256': digest(Path(__file__)),
              'force_rows': len(fp), 'marker_rows': len(markers), 'plates': plates,
              'pelvis_marker_orientation': headings, 'converted_force_comparison': exported_comparison,
              'limitations': ['One recording only; no generalization to stairs, ramps or other recordings',
                              'Nearest foot is supporting geometric evidence, not a measurement of contact identity',
                              'Anterior/lateral anatomical directions and force/COP sign mapping remain unresolved',
                              'Missing geometry and absent contact never default to a right-side assignment']}
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'source_geometry.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'plates': plates, 'pelvis_marker_orientation': headings,
                      'converted_cycles': exported_comparison['cycles'] if exported_comparison else None}))


if __name__ == '__main__':
    main()
