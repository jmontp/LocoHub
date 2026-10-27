"""Adapt completed single-record pilots to the existing independent force checker.

This wrapper does not convert data. Call only inside the coordinated numerical
slot after native conversion and exact baseline-preservation checks succeed.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / 'contributor_tools/audit_probes/2026_10_20/check_gt21_force_outputs.py'
DEPENDENCIES = [Path(__file__).resolve(), CHECKER,
                ROOT / 'contributor_tools/gt21_numeric_source.py',
                ROOT / 'contributor_tools/reconvert_recording.py']


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def observations(path):
    """Read only identities, rejecting repeated, partial or mixed cycles."""
    import pyarrow.parquet as pq
    result = {}
    for batch in pq.ParquetFile(path).iter_batches(
            batch_size=150, columns=['observation_id', 'reference_side'], use_threads=False):
        values = batch.to_pydict()
        ids, sides = values['observation_id'], values['reference_side']
        if len(ids) != 150 or len(set(ids)) != 1 or len(set(sides)) != 1:
            raise ValueError('Partial or mixed observation in pilot output')
        identity, side = ids[0], sides[0]
        if not isinstance(identity, str) or not identity or side not in ('left', 'right'):
            raise ValueError('Missing observation identity or anatomical reference')
        if identity in result:
            raise ValueError('Duplicate observation identity')
        result[identity] = side
    return result


def audit_record(folder, baseline_folder, output_root):
    """Return evidence covering ALL pilot cycles, including every added identity.

    Does not prove baseline signal preservation or source-event eligibility;
    the caller must enforce those separate gates. Output root must be new.
    """
    folder, baseline_folder, out = map(lambda p: Path(p).resolve(),
                                      (folder, baseline_folder, output_root))
    manifests = []
    for source in (baseline_folder, folder):
        manifest = json.loads((source / 'conversion_manifest.json').read_text())
        if manifest.get('status') != 'converted_unreviewed':
            raise ValueError('A completed native conversion is required')
        expected = [x['sha256'] for x in manifest['outputs'] if x['name'] == 'phase.parquet']
        if len(expected) != 1 or digest(source / 'phase.parquet') != expected[0]:
            raise ValueError('Pilot output hash mismatch')
        manifests.append(manifest)
    baseline, candidate = manifests
    if baseline['recording'] != candidate['recording'] or baseline['sources'] != candidate['sources']:
        raise ValueError('Baseline and candidate must identify exactly the same original sources')
    before, after = observations(baseline_folder / 'phase.parquet'), observations(folder / 'phase.parquet')
    if not before or not before.keys() <= after.keys():
        raise ValueError('Baseline empty or original observations missing')
    if any(after[key] != side for key, side in before.items()):
        raise ValueError('Original reference side changed')
    added = sorted(after.keys() - before.keys())
    if not added:
        raise ValueError('No added cycles to verify')
    record = candidate['recording']
    for key in ('subject', 'date', 'mode', 'recording'):
        value = record[key]
        if not isinstance(value, str) or Path(value).name != value or value in ('', '.', '..'):
            raise ValueError('Unsafe recording path component')
    bindings = {str(p): digest(p) for p in DEPENDENCIES}
    out.mkdir(parents=True, exist_ok=False)
    batch_root = out / 'single_record_batch'
    target = batch_root / record['subject'] / record['date'] / record['mode'] / Path(record['recording']).stem
    target.parent.mkdir(parents=True)
    target.symlink_to(folder, target_is_directory=True)
    (batch_root / 'inventory.json').write_text(json.dumps({'recordings': [record]}) + '\n')
    (batch_root / 'batch_status.json').write_text(json.dumps({
        'status': 'single_completed_pilot_for_readback', 'completed': 1,
        'observations': len(after), 'scientific_approval': False}) + '\n')
    report = {'status': 'checking', 'scientific_approval': False,
              'baseline_manifest_sha256': digest(baseline_folder / 'conversion_manifest.json'),
              'candidate_manifest_sha256': digest(folder / 'conversion_manifest.json'),
              'code_sha256': bindings, 'all_observations': len(after),
              'added_observations': len(added),
              'added_cycles': [{'observation_id': key, 'reference_side': after[key]} for key in added],
              'limitations': ['Exact baseline signal preservation and event eligibility are separate gates',
                             'Declared source laboratory mapping is checked, not anatomical frame approval']}
    try:
        subprocess.run([sys.executable, str(CHECKER), '--batch-root', str(batch_root),
                        '--output-root', str(out / 'force_readback')], check=True, timeout=600)
        result_path = out / 'force_readback/force_comparison.json'
        checked = json.loads(result_path.read_text())
        if (checked.get('status') != 'completed_force_sources_checked_unreviewed'
                or len(checked['records']) != 1
                or checked['records'][0]['recording'] != record
                or checked['records'][0]['observations'] != len(after)
                or checked['records'][0]['manifest_sha256'] != report['candidate_manifest_sha256']):
            raise ValueError('Force checker did not cover the complete candidate recording')
        values_checked = (checked['records'][0]['finite_values_checked']
                          + checked['records'][0]['missing_values_checked'])
        if values_checked != len(after) * 150 * 12:
            raise ValueError('Incomplete finite/missing coverage across all twelve force/COP columns')
        for source, manifest, bound_hash in zip(
                (baseline_folder, folder), manifests,
                (report['baseline_manifest_sha256'], report['candidate_manifest_sha256'])):
            if digest(source / 'conversion_manifest.json') != bound_hash:
                raise ValueError('Manifest changed during force readback')
            expected = next(x['sha256'] for x in manifest['outputs'] if x['name'] == 'phase.parquet')
            if digest(source / 'phase.parquet') != expected:
                raise ValueError('Output changed during force readback')
        if any(digest(Path(p)) != sha for p, sha in bindings.items()):
            raise ValueError('Audit code changed during readback')
        report.update(status='all_pilot_cycles_force_checked_unreviewed',
                      force_report_sha256=digest(result_path),
                      finite_values_checked=checked['records'][0]['finite_values_checked'],
                      missing_values_checked=checked['records'][0]['missing_values_checked'])
    except Exception as error:
        report.update(status='failed', reason=str(error))
        raise
    finally:
        (out / 'added_cycle_force_summary.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
