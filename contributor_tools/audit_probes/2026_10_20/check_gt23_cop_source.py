"""Bounded evidence that GT23 measured vertical COP must not be replaced by zero.

This is a source audit, not execution of the corrected MATLAB converters.
"""
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path('/mnt/s/locomotion_data/Gtech_2023/RawData/AB01/CSV_Data')
OUTPUT = ROOT / 'converted_datasets/reconversion_v2/gt23_cop_source_review_20261020'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    results = []
    for task in ['ball_toss_1', 'normal_walk_1', 'sit_to_stand_1']:
        path = BASE / task / 'GroundFrame_GRFs.csv'
        values = {key: [] for key in ['RCOPY_Vertical', 'LCOPY_Vertical']}
        with path.open() as stream:
            for index, row in enumerate(csv.DictReader(stream)):
                for key in values:
                    values[key].append(float(row[key]))
                if index == 4095:
                    break
        summaries = {}
        for key, samples in values.items():
            finite = [x for x in samples if math.isfinite(x)]
            summaries[key] = {'rows': len(samples), 'finite': len(finite),
                              'nonzero_finite': sum(x != 0 for x in finite),
                              'min': min(finite) if finite else None,
                              'max': max(finite) if finite else None}
        results.append({'source': str(path), 'sha256': digest(path), 'channels': summaries})
    assert any(v['nonzero_finite'] for result in results for v in result['channels'].values())
    OUTPUT.mkdir(exist_ok=False)
    report = {'source_samples': results, 'probe_sha256': digest(Path(__file__)),
              'finding': 'Measured global vertical COP is nonzero in original source rows.',
              'limitations': ['4096 rows per recording only', 'Corrected native MATLAB converters not executed',
                              'Ankle-frame convention, full reconstruction and release validation pending']}
    (OUTPUT / 'source_comparison.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
