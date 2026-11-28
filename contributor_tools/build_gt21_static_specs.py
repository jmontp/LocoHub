"""Write guarded-launcher specs for the GT21 static-pose check (plan only; nothing is launched). Standard library only.

usage:
  build_gt21_static_specs.py export AB06 [attempt]     one native MATLAB export job (static ik, ik_offset, markers) for one person
  build_gt21_static_specs.py analysis [pilot]          the Python analysis job (all people, or the two pilot people)
Specs go to docs/quality/audits/gt21-static-<job>-spec[-rN].json and refuse to overwrite. Each binds the code it runs.
Pilot people: AB06 (local copy) and AB12 (extracted zip). The native launcher runs one person per job.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ('AB06', 'AB07', 'AB08', 'AB09', 'AB10', 'AB11', 'AB13', 'AB14', 'AB16', 'AB18', 'AB20', 'AB21', 'AB24', 'AB25', 'AB27', 'AB30')
SIX = ('AB12', 'AB15', 'AB17', 'AB19', 'AB23', 'AB28')
PILOT = ('AB06', 'AB12')
LOCAL_ROOT = ROOT / 'contributor_tools/conversion_scripts/Gtech_2021/CAMARGO_ET_AL_J_BIOMECH_DATASET'
EXTRACT_ROOT = Path('/mnt/s/locomotion_data/gt21_author_mirror_2024_extracted')
EXPORT_ROOT = 'converted_datasets/reconversion_v2/gt21_static_export_v1'
ANALYSIS_ROOT = 'converted_datasets/reconversion_v2/gt21_static_analysis_v1'
AUDITS = ROOT / 'docs/quality/audits'
EXPORT_BIND = ('contributor_tools/conversion_scripts/Gtech_2021/gt21_static_export.m',
               'contributor_tools/guarded_launcher_native.py', 'contributor_tools/guarded_launcher.py')
ANALYSIS_BIND = ('contributor_tools/analyze_gt21_static_pose.py', 'contributor_tools/gt21_rb_pass.py',
                 'contributor_tools/build_review_sheet_cross_dataset.py', 'contributor_tools/common/review_sheet.py',
                 'contributor_tools/guarded_launcher.py')
PHASE_TABLES = ('gt21_r01_package_v1', 'gt23_r01_review_v11', 'um21_r01_package_v5')


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def export_spec(subject, attempt=1):
    assert subject in LOCAL or subject in SIX
    suffix = '' if attempt == 1 else f'-r{attempt}'
    source = LOCAL_ROOT if subject in LOCAL else EXTRACT_ROOT
    return {'job_id': f'gt21-static-export-{subject}{suffix}', 'job': 'static', 'subject': subject, 'source_root': str(source),
            'output_root': str(ROOT / EXPORT_ROOT / f'{subject}{suffix}'),
            'receipt_path': str(ROOT / f'docs/quality/audits/gt21-static-export-{subject}-launcher-receipt{suffix}.json'),
            'bindings': {k: sha(ROOT / k) for k in EXPORT_BIND}, 'timeout_seconds': 900, 'expected_output_names': []}


def analysis_spec(pilot=False):
    bindings = {k: sha(ROOT / k) for k in ANALYSIS_BIND}
    for t in PHASE_TABLES:
        bindings[f'converted_datasets/reconversion_v2/{t}/filtered_phase.parquet'] = sha(ROOT / f'converted_datasets/reconversion_v2/{t}/filtered_phase.parquet')
    out = ANALYSIS_ROOT + ('_pilot' if pilot else '')
    command = ['python3', 'contributor_tools/analyze_gt21_static_pose.py', 'compute', '--out-root', out]
    if pilot:
        for s in PILOT:
            command += ['--subject', s]
    return {'job_id': 'gt21-static-analysis' + ('-pilot' if pilot else ''), 'command': command, 'cwd': str(ROOT), 'output_root': out,
            'receipt_path': f'docs/quality/audits/gt21-static-analysis{"-pilot" if pilot else ""}-launcher-receipt.json',
            'bindings': bindings, 'timeout_seconds': 3600, 'kill_after_seconds': 30, 'poll_seconds': 15,
            'startup_memory_mib': {'linux': 3584, 'windows': 2816}, 'runtime_memory_mib': {'linux': 2048, 'windows': 2048},
            'expected_output_names': ['run_summary.json', 'per_participant.csv', 'comparison.json', 'static_trials.csv'],
            'address_space_mib': 768, 'disk_admission': [{'path': str(ROOT / 'converted_datasets'), 'min_free_mib': 5120}]}


def write(name, spec):
    target = AUDITS / f'gt21-static-{name}-spec.json'
    with target.open('x') as stream:
        json.dump(spec, stream, indent=2)
        stream.write('\n')
    return target


if __name__ == '__main__':
    kind = sys.argv[1]
    if kind == 'export':
        subject = sys.argv[2]
        attempt = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        print(write(f'export-{subject}' + ('' if attempt == 1 else f'-r{attempt}'), export_spec(subject, attempt)))
    elif kind == 'analysis':
        pilot = len(sys.argv) > 2 and sys.argv[2] == 'pilot'
        print(write('analysis-pilot' if pilot else 'analysis', analysis_spec(pilot)))
    else:
        raise SystemExit(__doc__)
