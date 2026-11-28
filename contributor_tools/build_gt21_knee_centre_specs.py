"""Write the guarded-launcher spec for the GT21 knee-centre analysis (A5; plan only; nothing is launched). Standard library only.

usage:
  build_gt21_knee_centre_specs.py [pilot [-r2]]   the Python analysis job (all people, or the two pilot people AB06 and AB12)
The spec goes to docs/quality/audits/gt21-knee-centre-analysis[-pilot]-spec.json and refuses to overwrite. It binds the code it
runs and the small inputs it reads (A3 outputs, RB01 inventory). Follows build_gt21_static_specs.py. Admission numbers are copied
from that reviewed spec with the PM-01 runtime reserve (2048 MiB); the launcher dry run decides whether they are accepted.
Run order: pilot spec, dry run, pilot run, check, then the full spec (same bound code).
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ('AB06', 'AB12')
OUT = 'converted_datasets/reconversion_v2/gt21_knee_centre_v1'
BIND_CODE = ('contributor_tools/analyze_gt21_knee_centre.py', 'contributor_tools/analyze_gt21_static_pose.py',
             'contributor_tools/gt21_rb_pass.py', 'contributor_tools/gt21_numeric_source.py',
             'contributor_tools/common/review_sheet.py', 'contributor_tools/guarded_launcher.py')
BIND_INPUTS = ('converted_datasets/reconversion_v2/gt21_static_analysis_v1/per_participant.csv',
               'converted_datasets/reconversion_v2/gt21_static_analysis_v1/comparison.json',
               'converted_datasets/reconversion_v2/gt21_rb01_inventory_20261123/recording_ledger.jsonl')
SEED = '20261127'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def analysis_spec(pilot=False, attempt=''):
    out = OUT + ('_pilot' if pilot else '') + attempt
    command = ['python3', 'contributor_tools/analyze_gt21_knee_centre.py', 'compute', '--out-root', out, '--seed', SEED]
    if pilot:
        for s in PILOT:
            command += ['--subject', s]
    tag = ('-pilot' if pilot else '') + attempt
    return {'job_id': 'gt21-knee-centre-analysis' + tag, 'command': command, 'cwd': str(ROOT), 'output_root': out,
            'receipt_path': f'docs/quality/audits/gt21-knee-centre-analysis{tag}-launcher-receipt.json',
            'bindings': {k: sha(ROOT / k) for k in BIND_CODE + BIND_INPUTS}, 'timeout_seconds': 3600, 'kill_after_seconds': 30,
            'poll_seconds': 15, 'startup_memory_mib': {'linux': 3584, 'windows': 2816},
            'runtime_memory_mib': {'linux': 2048, 'windows': 2048},
            'expected_output_names': ['run_summary.json', 'per_participant.csv', 'comparison.json', 'model_inspection.json'],
            'address_space_mib': 768, 'disk_admission': [{'path': str(ROOT / 'converted_datasets'), 'min_free_mib': 2048}]}


def write(pilot, attempt=''):
    target = ROOT / 'docs/quality/audits' / f'gt21-knee-centre-analysis{"-pilot" if pilot else ""}{attempt}-spec.json'
    with target.open('x') as stream:
        json.dump(analysis_spec(pilot, attempt), stream, indent=2)
        stream.write('\n')
    return target


if __name__ == '__main__':
    if len(sys.argv) > 3 or (len(sys.argv) >= 2 and sys.argv[1] != 'pilot'):
        raise SystemExit(__doc__)
    # `pilot [-r2]`: a re-run after a code change goes to a new root and spec (never overwrites)
    print(write(len(sys.argv) >= 2, sys.argv[2] if len(sys.argv) == 3 else ''))
