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
    args = parser.parse_args()
    manifest = json.loads((args.probe / 'source_comparison.json').read_text())
    assert manifest['native_status']['status'] == 'completed'
    assert manifest['native_status']['exit_code'] == 0
    for table in manifest['tables']:
        assert digest(args.probe / table['file']) == table['sha256']
    fp = pq.ParquetFile(args.probe / 'source_fp_data.parquet').read(use_threads=False).to_pandas(use_threads=False)
    names = ['Header'] + [f'{side}_{marker}_{axis}' for side in ('L', 'R')
                         for marker in ('Heel', 'Toe_Tip') for axis in 'xyz']
    markers = pq.ParquetFile(args.probe / 'source_markers_data.parquet').read(columns=names,
                            use_threads=False).to_pandas(use_threads=False)
    ft, mt = fp.Header.to_numpy(), markers.Header.to_numpy()
    assert np.isfinite(ft).all() and np.isfinite(mt).all()
    assert (np.diff(ft) > 0).all() and (np.diff(mt) > 0).all()
    inside = (mt >= ft[0]) & (mt <= ft[-1])
    feet = {side: sum(markers[[f'{side}_{marker}_{axis}' for axis in 'xyz']].to_numpy()
                      for marker in ('Heel', 'Toe_Tip')) / 2000 for side in ('L', 'R')}
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
    source_code = Path('contributor_tools/conversion_scripts/Gtech_2021/CAMARGO_ET_AL_J_BIOMECH_DATASET/scripts (1)/MoCapTools/+Osim/correlateForcePlates.m')
    result = {'status': 'source_geometry_diagnostic', 'scientific_approval': False,
              'source_readback_sha256': digest(args.probe / 'source_comparison.json'),
              'original_geometry_code_sha256': digest(source_code), 'probe_sha256': digest(Path(__file__)),
              'force_rows': len(fp), 'marker_rows': len(markers), 'plates': plates,
              'limitations': ['One recording only; no generalization to stairs, ramps or other recordings',
                              'Nearest foot is supporting geometric evidence, not a measurement of contact identity',
                              'Anterior/lateral anatomical directions and force/COP sign mapping remain unresolved',
                              'Missing geometry and absent contact never default to a right-side assignment']}
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'source_geometry.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
