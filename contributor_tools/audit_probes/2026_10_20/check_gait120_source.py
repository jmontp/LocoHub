"""Regenerate a bounded Gait120 pilot and compare every angle to raw MOT samples.

One recording per task for S001 (without forces) and S011 (with forces).
Run with one BLAS thread and low process/I/O priority. Outputs are immutable.
This checks source preservation, not the clinical validity of model/force results.
"""
import resource
resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024**2, 1024 * 1024**2))
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'contributor_tools/conversion_scripts/Gait120'))
import numpy as np
import pandas as pd
from contributor_tools.conversion_scripts.Gait120 import convert_gait120_to_parquet as converter
from contributor_tools.common.data_contract import inspect_contract

SOURCE = Path('/mnt/s/locomotion_data/Gait120')
OUTPUT = ROOT / 'converted_datasets/reconversion_v2/gait120_source_pilot_20261020'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    OUTPUT.mkdir(exist_ok=False)
    code_files = sorted((ROOT / 'contributor_tools/conversion_scripts/Gait120').glob('*.py'))
    code_files += sorted((ROOT / 'contributor_tools/common').rglob('*.py'))
    code_files.append(Path(__file__).resolve())
    code_hashes = {}
    for path in code_files:
        relative = path.relative_to(ROOT)
        destination = OUTPUT / 'code' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        code_hashes[str(relative)] = digest(path)
    results = []
    source_hashes = {}
    for subject in ['S001', 'S011']:
        anthropometry = converter.get_subject_anthropometrics(subject, SOURCE)
        for folder, (task, task_id) in converter.TASK_MAPPING.items():
            candidates = sorted((SOURCE / subject / 'JointAngle' / folder).glob('*/*.mot'))
            assert candidates, (subject, folder)
            source = candidates[0]
            raw = pd.read_csv(io.StringIO(source.read_text().split('endheader', 1)[1].strip()), sep=r'\s+')
            frame = converter.process_step_file(source, f'G120_{subject}', task, task_id, 0,
                subject_mass_kg=anthropometry['mass_kg'], subject_height_m=anthropometry['height_m'])
            assert frame is not None and len(frame) == 150
            assert inspect_contract(frame, mode='phase').schema_passed
            target = np.linspace(raw.time.iloc[0], raw.time.iloc[-1], 150)
            errors = {}
            for role, leg in [('ipsi', 'r'), ('contra', 'l')]:
                for src, dst, sign in [('hip_flexion', 'hip_flexion', 1), ('knee_angle', 'knee_flexion', -1), ('ankle_angle', 'ankle_dorsiflexion', 1)]:
                    expected = np.interp(target, raw.time, raw[f'{src}_{leg}']) * sign * np.pi / 180
                    col = f'{dst}_angle_{role}_rad'
                    np.testing.assert_allclose(frame[col], expected, rtol=1e-10, atol=1e-10, equal_nan=True)
                    errors[col] = float(np.nanmax(abs(frame[col] - expected)))
            destination = OUTPUT / subject / folder / source.parent.name / source.name.replace('.mot', '.parquet')
            destination.parent.mkdir(parents=True, exist_ok=True)
            frame.to_parquet(destination, index=False)
            pd.testing.assert_frame_equal(frame.reset_index(drop=True), pd.read_parquet(destination))
            sources = [source, converter.get_grf_mot_path(source), converter.get_trc_path(source)]
            for path in sources:
                if path is not None:
                    source_hashes[str(path)] = digest(path)
            results.append({'source': str(source), 'output': str(destination.relative_to(OUTPUT)),
                            'output_sha256': digest(destination), 'rows': len(frame),
                            'max_angle_errors_rad': errors, 'status': 'converted_unreviewed'})
    spreadsheet = SOURCE / 'Anthropometric_Data_Participants.xlsx'
    if not spreadsheet.exists():
        spreadsheet = ROOT / 'contributor_tools/conversion_scripts/Gait120/Anthropometric_Data_Participants.xlsx'
    source_hashes[str(spreadsheet)] = digest(spreadsheet)
    report = {'recordings_checked': len(results), 'rows_checked': sum(x['rows'] for x in results),
              'results': results, 'source_sha256': source_hashes, 'code_sha256': code_hashes,
              'limitations': ['Pilot only: full source coverage pending', 'Original source model/sign conventions require further checks', 'Force/COP and inverse dynamics not independently validated']}
    (OUTPUT / 'source_comparison.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'recordings_checked': len(results), 'rows_checked': report['rows_checked']}))


if __name__ == '__main__':
    main()
