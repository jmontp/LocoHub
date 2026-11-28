"""Audit all local GT23 named transfer intervals against recorded knee motion.

Reads one recording at a time. This establishes source-label evidence, not native
execution of the updated transfer-label branch or approval of full exports.
"""
import resource
resource.setrlimit(resource.RLIMIT_AS, (768 * 1024**2, 768 * 1024**2))
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path('/mnt/s/locomotion_data/Gtech_2023')
OUTPUT = ROOT / 'converted_datasets/reconversion_v2/gt23_transfer_source_review_20261020'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    grouped = defaultdict(list)
    for path in sorted((SOURCE / 'Segmentation').glob('AB*/sit_to_stand*_parsing.mat')):
        name = path.stem.removesuffix('_parsing')
        folders = (SOURCE/'RawData'/path.parent.name/'CSV_Data').iterdir()
        candidates = [folder.name for folder in folders if folder.is_dir() and (name == folder.name or name.startswith(folder.name+'_'))]
        assert candidates, path
        recording = max(candidates, key=len)
        grouped[(path.parent.name, recording)].append(path)
    results = []; source_hashes = {}; problems = []
    for (subject, recording), annotations in grouped.items():
        source = SOURCE / 'RawData' / subject / 'CSV_Data' / recording / 'Joint_Angle.csv'
        angles = pd.read_csv(source, usecols=['time', 'knee_angle_l', 'knee_angle_r'])
        source_hashes[str(source)] = digest(source)
        clock = angles.time.to_numpy()
        assert np.isfinite(clock).all() and (np.diff(clock) > 0).all()
        for path in annotations:
            parsed = loadmat(path)
            source_hashes[str(path)] = digest(path)
            for condition, task, sign in [('sitting', 'stand_to_sit', 1), ('standing', 'sit_to_stand', -1)]:
                intervals = parsed['left_' + condition]
                np.testing.assert_array_equal(intervals, parsed['right_' + condition])
                assert intervals.ndim == 2 and intervals.shape[1] == 2
                for index, (start, end) in enumerate(intervals):
                    assert np.isfinite([start, end]).all() and end > start
                    changes = {}
                    for leg in ['l', 'r']:
                        endpoints = np.interp([start, end], clock, -angles[f'knee_angle_{leg}'], left=np.nan, right=np.nan)
                        delta = float(endpoints[1] - endpoints[0])
                        changes[leg] = delta if np.isfinite(delta) else None
                    result = {'source': str(path), 'condition': condition, 'task': task,
                              'source_interval_index': index, 'start_s': float(start), 'end_s': float(end),
                              'knee_flexion_change_deg': changes}
                    if any(value is None or value*sign <= 0 for value in changes.values()):
                        problems.append(result)
                    results.append(result)
    OUTPUT.mkdir(exist_ok=False)
    report = {'subjects': len({subject for subject, _ in grouped}), 'recordings': len(grouped),
              'intervals': len(results), 'direction_disagreements_or_missing': len(problems),
              'problems': problems, 'source_sha256': source_hashes, 'results': results,
              'probe_sha256': digest(Path(__file__)),
              'limitations': ['Endpoint direction check does not prove boundary precision',
                              'Native transfer branch and full regeneration still pending']}
    (OUTPUT / 'source_comparison.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps({key: value for key, value in report.items() if key not in {'results', 'source_sha256', 'problems'}}))


if __name__ == '__main__':
    main()
