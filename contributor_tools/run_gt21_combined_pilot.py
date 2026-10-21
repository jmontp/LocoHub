"""Stage and explicitly run a combined GT21 pilot with separate adoption gates.

One bounded recording only. This does not replace a production converter or
approve anatomical conventions. Native execution belongs in the serial queue.
"""
import argparse
import json
import os
from pathlib import Path
import resource
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.reconvert_recording import digest, ensure_storage_headroom


def require_complete_ledger(report):
    if report.get('status') != 'complete_eligible_pairs_checked_unreviewed':
        raise ValueError('Complete source-pair coverage has not passed')


def require_unused_summary(output_root):
    """Preserve every previous attempt, including interrupted and failed runs."""
    summary = Path(output_root) / 'pilot_summary.json'
    if summary.exists() or summary.is_symlink():
        raise FileExistsError(f'Existing pilot attempt must be preserved; use a new root: {summary}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    require_unused_summary(args.output_root)
    for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[key] = '1'
    os.nice(max(0, 19-os.nice(0)))
    resource.setrlimit(resource.RLIMIT_AS, (768*1024**2, 768*1024**2))
    from contributor_tools import run_gt21_native_batch as native
    from contributor_tools.prepare_gt21_combined_adoption import combined_source
    from contributor_tools.audit_gt21_added_cycle_forces import DEPENDENCIES as force_dependencies
    baseline_path = args.baseline.resolve()
    baseline = json.loads(baseline_path.read_text())
    if baseline['status'] != 'converted_unreviewed':
        raise ValueError('Completed baseline required')
    record = baseline['recording']
    if record['mode'] not in ('levelground', 'treadmill'):
        raise ValueError('Terrain eligibility ledger is not yet implemented; cannot approve that pilot')
    for item in baseline['sources']:
        if digest(Path(item['path'])) != item['sha256']:
            raise ValueError('Baseline source changed')
    for item in baseline['outputs']:
        if digest(baseline_path.parent/item['name']) != item['sha256']:
            raise ValueError('Baseline output changed')
    source_root = next(Path(x['path']).parent for x in baseline['sources']
                       if Path(x['path']).name == 'SubjectInfo.mat')
    out = args.output_root.resolve()
    ensure_storage_headroom(out)
    plan_path = out/'pilot_plan.json'
    if not plan_path.exists():
        # Refuse pre-existing partial staging, preserving evidence of interruption.
        out.mkdir(parents=True, exist_ok=False)
        code = out/'isolated_code/Gtech_2021'
        code.mkdir(parents=True)
        original = native.CODE/'convert_gtech_2021_phase_to_parquet.m'
        (code/original.name).write_text(combined_source(original.read_text()))
        shutil.copytree(native.CODE/'utilities', code/'utilities', ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(native.CODE.parent/'matlab_common', code.parent/'matlab_common')
        dependencies = [Path(__file__), original, Path(native.__file__), native.GUARD]
        dependencies += [ROOT/'contributor_tools'/name for name in (
            'prepare_gt21_combined_adoption.py', 'prepare_gt21_bilateral_recovery.py',
            'prepare_gt21_terrain_fix.py', 'audit_gt21_native_batch.py',
            'audit_gt21_adoption_ledger.py', 'audit_gt21_treadmill_metadata.py', 'gt21_adoption_coverage.py',
            'gt21_numeric_source.py', 'reconvert_recording.py')]
        dependencies += force_dependencies
        dependencies += sorted((ROOT/'contributor_tools/common').rglob('*.py'))
        dependencies = list(dict.fromkeys(dependencies))
        dependencies += sorted((out/'isolated_code').rglob('*.m'))
        plan = {'status':'prepared_unreviewed', 'baseline_path':str(baseline_path),
                'baseline_sha256':digest(baseline_path), 'recording':record,
                'code':native.evidence(dependencies), 'scientific_approval':False,
                'limitations':['Levelground/treadmill pilot only; terrain pipeline remains unverified',
                               'Overlapping leg cycles are not independent trials',
                               'Source convention reproduction does not approve physical/anatomical accuracy']}
        native.save(plan_path, plan)
    plan = json.loads(plan_path.read_text())
    if plan['baseline_sha256'] != digest(baseline_path):
        raise ValueError('Baseline changed; use a new pilot root')
    if any(digest(Path(x['path'])) != x['sha256'] for x in plan['code']):
        raise ValueError('Pilot code changed; use a new pilot root')
    if not args.run:
        print(json.dumps({'status':plan['status']}))
        return
    # The Windows launcher independently checks host memory, disk and timeout.
    from contributor_tools.prepare_gt21_bilateral_recovery import verify_preserved
    from contributor_tools.audit_gt21_native_batch import check_record
    from contributor_tools.audit_gt21_adoption_ledger import check_record as check_ledger
    from contributor_tools.audit_gt21_added_cycle_forces import audit_record as check_forces
    import pandas as pd
    summary = {'status':'running', 'scientific_approval':False}
    summary_path = out/'pilot_summary.json'
    native.save(summary_path, summary)
    try:
        native.CODE = out/'isolated_code/Gtech_2021'
        native.run_record(source_root, record, out/'converted', plan['code'])
        folder = out/'converted'/record['subject']/record['date']/record['mode']/Path(record['recording']).stem
        summary['preservation'] = verify_preserved(baseline_path.parent/'phase.parquet', folder/'phase.parquet')
        ledger = check_ledger(folder)
        native.save(out/'eligibility_readback.json', ledger)
        require_complete_ledger(ledger)
        if record['mode'] == 'treadmill':
            from contributor_tools.audit_gt21_treadmill_metadata import check_record as check_metadata
            metadata = check_metadata(folder, ledger)
            native.save(out/'treadmill_metadata_readback.json', metadata)
            if metadata.get('status') != 'all_treadmill_metadata_source_checked_unreviewed':
                raise ValueError('Source treadmill metadata gate has not passed')
            summary['treadmill_metadata_sha256'] = digest(out/'treadmill_metadata_readback.json')
        mass_root = ROOT/'converted_datasets/reconversion_v2/gt21_subject_mass_review_20261021'
        evidence = json.loads((mass_root/'source_comparison.json').read_text())
        if not evidence['native_exact_mass_readback'] or digest(mass_root/'subject_masses.csv') != evidence['csv_sha256']:
            raise ValueError('Verified source masses required')
        masses = pd.read_csv(mass_root/'subject_masses.csv')
        readback = check_record(folder, dict(zip(masses.Subject, masses.Weight)), evidence)
        native.save(out/'source_readback.json', readback)
        forces = check_forces(folder, baseline_path.parent, out/'added_cycle_force_audit')
        if forces.get('status') != 'all_pilot_cycles_force_checked_unreviewed':
            raise ValueError('Complete added-cycle force/COP gate has not passed')
        if any(digest(Path(x['path'])) != x['sha256'] for x in plan['code']):
            raise ValueError('Pilot code changed during execution')
        summary.update(status='combined_pilot_source_checked_unreviewed',
                       output_sha256=digest(folder/'phase.parquet'),
                       eligibility_sha256=digest(out/'eligibility_readback.json'),
                       source_readback_sha256=digest(out/'source_readback.json'),
                       force_readback_sha256=digest(out/'added_cycle_force_audit/added_cycle_force_summary.json'),
                       limitations=plan['limitations'])
    except Exception as error:
        summary.update(status='failed_incomplete', reason=str(error))
        raise
    finally:
        native.save(summary_path, summary)


if __name__ == '__main__':
    main()
