"""Explicit bounded pilot for source participant-condition ensembles, not strides.

Run only in the coordinator's serial numerical slot. No source downloads occur.
"""
import argparse
import bisect
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
RIGHT_SIGN_MAP = {
    'RHipAngleZ': ('hip_flexion_angle_ipsi_rad', math.pi/180),
    'RKneeAngleZ': ('knee_flexion_angle_ipsi_rad', math.pi/180),
    'RAnkleAngleZ': ('ankle_dorsiflexion_angle_ipsi_rad', math.pi/180),
    'RHipMomentZ': ('hip_flexion_moment_ipsi_Nm_kg', 1),
    'RKneeMomentZ': ('knee_flexion_moment_ipsi_Nm_kg', -1),
    'RAnkleMomentZ': ('ankle_dorsiflexion_moment_ipsi_Nm_kg', -1),
}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def read_curve(path):
    if path.stat().st_size > 1024**2:
        raise ValueError('Ensemble table exceeds 1 MiB pilot admission')
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        columns = reader.fieldnames
        if not columns or len(set(columns)) != len(columns) or columns[0] != 'Time':
            raise ValueError('Unexpected or duplicate source header')
        rows = list(reader)
    if len(rows) != 101:
        raise ValueError('Reviewed pilot requires exactly 101 source samples')
    values = {name: [float(row[name]) for row in rows] for name in columns}
    if any(not math.isfinite(x) or abs(x-i) > 1e-8 for i, x in enumerate(values['Time'])):
        raise ValueError('Expected source normalized grid 0..100, not elapsed time')
    if any(math.isinf(x) for v in values.values() for x in v):
        raise ValueError('Infinite source values')
    return values


def interpolate(values, phase):
    """Linear interpolation on integer source phase; never bridge missing data."""
    out = []
    for x in phase:
        lo = int(math.floor(x)); hi = min(lo+1, 100)
        if x == lo:
            out.append(values[lo])
        elif not math.isfinite(values[lo]) or not math.isfinite(values[hi]):
            out.append(float('nan'))
        else:
            out.append(values[lo] + (values[hi]-values[lo])*(x-lo))
    return out


def build_rows(angles, kinetics, stem):
    match = re.fullmatch(r'WBDS(\d{2})walkO([SCF])', stem)
    if not match:
        raise ValueError('Initial pilot only covers documented overground condition codes')
    subject, condition = match.groups()
    phase = [100*i/149 for i in range(150)]
    combined = {k: v for k, v in angles.items() if k != 'Time'}
    for name, values in kinetics.items():
        if name == 'Time':
            continue
        if name in combined:
            raise ValueError('Duplicate signal across source tables')
        combined[name] = values
    if not combined or any(not re.fullmatch(r'[RL](?:PelvisAngle|HipAngle|KneeAngle|AnkleAngle|FootAngle|HipMoment|KneeMoment|AnkleMoment|GRF)[XYZ]', c) for c in combined):
        raise ValueError('Unreviewed source signal header')
    rows = []
    source_id = 'fu18:v6:participant_condition_ensemble:'+stem
    for prefix, side in [('R', 'right'), ('L', 'left')]:
        columns = {k: v for k, v in combined.items() if k.startswith(prefix)}
        if not columns:
            raise ValueError('Missing anatomical leg columns')
        signals = {}
        for name, value in columns.items():
            unit = 'deg' if 'Angle' in name else 'Nm_kg' if 'Moment' in name else 'N_kg'
            signals['source_'+name+'_'+unit] = interpolate(value, phase)
            if side == 'right' and name in RIGHT_SIGN_MAP:
                target, scale = RIGHT_SIGN_MAP[name]
                signals[target] = [x*scale for x in interpolate(value, phase)]
        info = {'environment': 'overground', 'source_condition': condition,
                'speed_category': {'S': 'slow', 'C': 'comfortable', 'F': 'fast'}[condition],
                'source_grid_samples': 101, 'export_grid_samples': 150,
                'resampling': 'linear interpolation of source ensemble, not recovery of individual strides',
                'timing': 'normalized phase only; original cycle durations unavailable',
                'aggregation': 'source participant-condition mean; cycle membership/count/SD unavailable',
                'canonical_sign_scope': 'right sagittal angles/moments from author script labels; left stays source-only',
                'source_doi': '10.6084/m9.figshare.5722711.v6'}
        for i, x in enumerate(phase):
            row = {'subject': 'FU18_'+subject, 'task': 'level_walking', 'task_id': 'overground_'+condition,
                   'source_recording_id': source_id, 'observation_id': source_id+':'+side,
                   'reference_side': side, 'observation_kind': 'ensemble', 'observation_type': 'ensemble_curve',
                   'phase_ipsi': x, 'task_info': json.dumps(info, sort_keys=True),
                   'source_start_time_s': float('nan'), 'source_end_time_s': float('nan')}
            row.update({name: value[i] for name, value in signals.items()})
            rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-pilot', type=Path, required=True)
    parser.add_argument('--stem', default='WBDS01walkOC')
    parser.add_argument('--output-root', type=Path, required=True)
    args = parser.parse_args()
    for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'ARROW_NUM_THREADS'):
        os.environ[name] = '1'
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (768*1024**2, 768*1024**2))
    os.nice(max(0, 19-os.nice(0)))
    sys.path.insert(0, str(ROOT))
    from contributor_tools.reconvert_recording import ensure_storage_headroom
    ensure_storage_headroom(args.output_root)
    if not re.fullmatch(r'WBDS\d{2}walkO[SCF]', args.stem):
        raise ValueError('Invalid source stem')
    review = json.loads((args.source_pilot/'range_acquisition.json').read_text())
    paths = [args.source_pilot/(args.stem+suffix+'.txt') for suffix in ('ang', 'knt')]
    expected = {x['local_file']: x['sha256'] for x in review['members']}
    if any(digest(p) != expected.get(p.name) for p in paths):
        raise ValueError('Acquired source member hash mismatch')
    script = Path(__file__).parent/'source_evidence/wbdsExploratoryDA.m'
    candidate = json.loads((Path(__file__).parent/'candidate.json').read_text())
    script_evidence = next(e for e in candidate['evidence_files'] if e['path'].endswith('/wbdsExploratoryDA.m'))
    if digest(script) != script_evidence['sha256']:
        raise ValueError('Sign convention source script changed')
    rows = build_rows(*(read_curve(p) for p in paths), args.stem)
    import pandas as pd
    import pyarrow as pa
    from contributor_tools.common.data_contract import inspect_contract
    pa.set_cpu_count(1); pa.set_io_thread_count(1)
    frame = pd.DataFrame(rows)
    assessment = inspect_contract(frame, mode='ensemble')
    if not assessment.schema_passed:
        raise ValueError('Ensemble contract failure: '+str(assessment.issues))
    args.output_root.mkdir(parents=True, exist_ok=False)
    target = args.output_root/'ensemble.parquet'
    frame.to_parquet(target, index=False, row_group_size=150)
    manifest = {'status': 'converted_ensemble_unreviewed', 'scientific_approval': False,
                'source_files': {str(p): digest(p) for p in paths},
                'acquisition_sha256': digest(args.source_pilot/'range_acquisition.json'),
                'sign_evidence_sha256': digest(script), 'converter_sha256': digest(Path(__file__)),
                'output_sha256': digest(target), 'rows': len(frame), 'ensembles': 2,
                'individual_cycles': 0, 'interpolated_grid': '101 to150 samples, explicitly labeled',
                'limitations': ['No source cycle durations/counts/SD', 'No simultaneous bilateral timing',
                                'Left canonical signs unapproved; source components retained',
                                'Source preservation is not biomechanical approval']}
    (args.output_root/'conversion_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')


if __name__ == '__main__':
    main()
