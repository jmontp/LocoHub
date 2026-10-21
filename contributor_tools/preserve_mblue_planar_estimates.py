"""Preserve MBLUE planar estimates while withholding unsupported orientations.

Explicit serial-worker execution only. Processes one 150-row cycle at a time,
reopens each written shard for exact preservation checks, and never overwrites.
This corrects labeling, not the outstanding physical orientation reconstruction.
"""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import resource
import shutil
import sys
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CANONICAL = tuple(f'{segment}_sagittal_{kind}_{side}_{unit}'
                  for segment in ('thigh', 'shank', 'foot')
                  for side in ('ipsi', 'contra')
                  for kind, unit in (('angle', 'rad'), ('velocity', 'rad_s')))
MAPPING = {name: 'derived_planar_' + name for name in CANONICAL}


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            value.update(block)
    return value.hexdigest()


def transform(frame):
    import pandas as pd
    if not frame.columns.is_unique or not set(CANONICAL) <= set(frame):
        raise ValueError('All twelve unique canonical segment columns required')
    if any(name.startswith('derived_planar_') for name in frame.columns):
        raise ValueError('Existing planar columns require explicit reconciliation')
    if any(not pd.api.types.is_numeric_dtype(frame[name])
           or pd.api.types.is_bool_dtype(frame[name]) for name in CANONICAL):
        raise ValueError('Canonical segment values must be numeric')
    result = frame.copy()
    for source, target in MAPPING.items():
        result[target] = frame[source].copy()
        result[source] = float('nan')
    return result


def transform_table(table):
    """Preserve Arrow null masks and metadata without a pandas write round-trip."""
    import pyarrow as pa
    if len(set(table.column_names)) != len(table.column_names) or not set(CANONICAL) <= set(table.column_names):
        raise ValueError('All twelve unique canonical segment columns required')
    if any(name.startswith('derived_planar_') for name in table.column_names):
        raise ValueError('Existing planar columns require explicit reconciliation')
    for source, target in MAPPING.items():
        field = table.schema.field(source)
        if not (pa.types.is_floating(field.type) or pa.types.is_integer(field.type)):
            raise ValueError('Canonical segment values must be numeric')
        values = table[source]
        metadata = dict(field.metadata or {})
        metadata[b'interpretation'] = b'planar estimate; not verified spatial orientation'
        table = table.append_column(pa.field(target, field.type, nullable=True,
            metadata=metadata), values)
        table = table.set_column(table.schema.get_field_index(source), field.with_nullable(True),
                                 pa.nulls(table.num_rows, type=field.type))
    return table


def verify_frame(before, after):
    import pandas as pd
    if list(after.columns) != list(before.columns) + list(MAPPING.values()):
        raise ValueError('Unexpected output columns or order')
    unchanged = [name for name in before if name not in MAPPING]
    pd.testing.assert_frame_equal(before[unchanged], after[unchanged], check_exact=True)
    for source, target in MAPPING.items():
        pd.testing.assert_series_equal(before[source], after[target], check_exact=True, check_names=False)
        if not after[source].isna().all():
            raise ValueError('Unsupported canonical orientation remained populated')


def verify_shard(original, corrected, global_identities=None, resource_guard=None):
    import pyarrow.parquet as pq
    from contributor_tools.common.data_contract import inspect_contract
    left, right = pq.ParquetFile(original), pq.ParquetFile(corrected)
    if left.schema_arrow.metadata != right.schema_arrow.metadata:
        raise ValueError('Original schema metadata changed')
    if left.metadata.num_rows != right.metadata.num_rows:
        raise ValueError('Shard row count changed')
    seen = set(); rows = 0
    for a, b in itertools.zip_longest(left.iter_batches(batch_size=150, use_threads=False),
                                     right.iter_batches(batch_size=150, use_threads=False)):
        if resource_guard is not None:
            resource_guard()
        if a is None or b is None:
            raise ValueError('Shard batch coverage mismatch')
        before, after = a.to_pandas(use_threads=False), b.to_pandas(use_threads=False)
        for name in a.schema.names:
            target = MAPPING.get(name, name)
            if a.column(a.schema.get_field_index(name)).is_null().to_pylist() != b.column(b.schema.get_field_index(target)).is_null().to_pylist():
                raise ValueError('Original null bitmap changed')
            if name not in MAPPING and not a.schema.field(name).equals(b.schema.field(name), check_metadata=True):
                raise ValueError('Unrelated field schema changed')
            if name in MAPPING:
                original_field = a.schema.field(name)
                expected_metadata = dict(original_field.metadata or {})
                expected_metadata[b'interpretation'] = b'planar estimate; not verified spatial orientation'
                if (b.schema.field(target).metadata != expected_metadata
                        or b.schema.field(target).type != original_field.type
                        or not original_field.with_nullable(True).equals(b.schema.field(name), check_metadata=True)):
                    raise ValueError('Canonical or preserved estimate field metadata changed')
        if len(before) != 150 or before.observation_id.nunique() != 1:
            raise ValueError('Partial or mixed observation')
        identity = before.observation_id.iloc[0]
        if identity in seen or (global_identities is not None and identity in global_identities):
            raise ValueError('Duplicate observation')
        seen.add(identity)
        if global_identities is not None:
            global_identities.add(identity)
        verify_frame(before, after)
        if not inspect_contract(after, mode='phase').schema_passed:
            raise ValueError('Corrected output fails structural checks')
        rows += len(after)
    return {'observations': len(seen), 'rows': rows,
            'all_other_columns_exactly_preserved': True,
            'all_planar_estimates_exactly_preserved': True,
            'unsupported_canonical_values_missing': True}


def headroom(path, source_bytes=0):
    if shutil.disk_usage(path).free < 5 * 1024**3 + source_bytes:
        raise OSError('Less than 5 GiB plus one shard of output space')
    if Path('/mnt/c').exists() and shutil.disk_usage('/mnt/c').free < 1024**3:
        raise OSError('Less than 1 GiB Windows drive reserve')
    available = next(int(line.split()[1]) * 1024 for line in Path('/proc/meminfo').read_text().splitlines()
                     if line.startswith('MemAvailable:'))
    if available < 2 * 1024**3:
        raise MemoryError('Less than 2 GiB WSL available memory')


def windows_available_mib():
    powershell = '/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'
    result = subprocess.run([powershell, '-NoProfile', '-NonInteractive', '-Command',
        '[math]::Floor((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1024) | ConvertTo-Json -Compress'],
        capture_output=True, text=True, check=True, timeout=30)
    value = json.loads(result.stdout)
    if type(value) is not int or value < 0:
        raise ValueError('Invalid Windows memory evidence')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True, help='Completed stair-corrected root')
    parser.add_argument('--scope-report', type=Path, required=True)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--run', action='store_true', help='Execute in the coordinated serial worker; default only prepares a plan')
    args = parser.parse_args()
    plan_path = args.output_root / 'plan.json'
    if args.output_root.exists() and (not plan_path.is_file()
            or any(p.name != 'plan.json' for p in args.output_root.iterdir())):
        raise FileExistsError('Preserve existing output attempt; choose a new root')
    baseline_path = args.baseline / 'correction_summary.json'
    bindings = {str(p.resolve()): digest(p) for p in (baseline_path, args.scope_report, args.review, Path(__file__))}
    for path in sorted((ROOT / 'contributor_tools/common').rglob('*.py')):
        bindings[str(path)] = digest(path)
    baseline = json.loads(baseline_path.read_text())
    scope = json.loads(args.scope_report.read_text())
    review = json.loads(args.review.read_text())
    if (baseline['status'] != 'stair_reference_corrected_unreviewed' or baseline['scope'] != 'full_baseline'
            or scope['status'] != 'complete_mblue_scope_evidence_checked_unreviewed'
            or scope['input_sha256']['correction'] != digest(baseline_path)):
        raise ValueError('Complete hash-bound final MBLUE scope evidence required')
    proposed = {item['canonical']: item['preserved_estimate']
                for item in review['isolated_correction_proposal']['field_mapping']}
    if proposed != MAPPING:
        raise ValueError('Reviewed field mapping differs from implementation')
    for evidence in review['evidence']:
        if digest(evidence['path']) != evidence['sha256']:
            raise ValueError('Reviewed source/model evidence changed')
        bindings[evidence['path']] = evidence['sha256']
    plan = {'status': 'prepared_not_executed', 'scientific_approval': False,
            'baseline_root': str(args.baseline.resolve()), 'output_root': str(args.output_root.resolve()),
            'input_sha256': bindings, 'field_mapping': MAPPING,
            'expected_blocks': scope['blocks'], 'expected_observations': scope['observations_after']}
    if plan_path.exists():
        if json.loads(plan_path.read_text()) != plan:
            raise ValueError('Prepared plan dependencies changed; use a new root')
    else:
        args.output_root.mkdir(parents=True, exist_ok=False)
        with plan_path.open('x') as stream:
            json.dump(plan, stream, indent=2); stream.write('\n')
    if not args.run:
        print(json.dumps(plan))
        return
    for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'ARROW_NUM_THREADS'):
        os.environ[key] = '1'
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024**2, 768 * 1024**2))
    os.nice(max(0, 19 - os.nice(0)))
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1); pa.set_io_thread_count(1)
    headroom(args.output_root)
    if windows_available_mib() < 2816:
        raise MemoryError('Need 768 MiB worker allowance plus 2 GiB Windows reserve')
    result = {'status': 'running', 'scientific_approval': False, 'input_sha256': bindings,
              'scope': 'full_baseline', 'field_mapping': MAPPING, 'records': [],
              'withholding_reason': 'Source scalar sums are planar estimates, not verified three-dimensional segment orientations',
              'limitations': ['This preserves estimates and corrects their interpretation; physical orientation reconstruction remains open',
                             'Canonical segment values are missing/unassessed, not evidence of passing',
                             'Pelvis tilt remains the original generalized coordinate with its existing limitations']}
    summary_path = args.output_root / 'planar_preservation_summary.json'
    def save():
        temporary = summary_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(result, indent=2) + '\n'); temporary.replace(summary_path)
    save()
    last_host_check = 0.0
    identities = set()
    def runtime_guard():
        nonlocal last_host_check
        if time.monotonic() - last_host_check >= 15:
            available = windows_available_mib(); last_host_check = time.monotonic()
            result['windows_available_mib'] = available
            if available < 2048:
                raise MemoryError('Windows reserve fell below 2 GiB')
    try:
        total = 0
        for record in baseline['records']:
            outputs = {}; observations = rows = 0
            for relative, expected_hash in record['outputs'].items():
                if Path(relative).is_absolute() or '..' in Path(relative).parts:
                    raise ValueError('Unsafe shard path')
                source = args.baseline / relative
                if digest(source) != expected_hash:
                    raise ValueError('Baseline shard changed')
                headroom(args.output_root, source.stat().st_size)
                target = args.output_root / relative; target.parent.mkdir(parents=True, exist_ok=True)
                partial = target.with_suffix('.parquet.partial'); writer = None
                try:
                    for batch in pq.ParquetFile(source).iter_batches(batch_size=150, use_threads=False):
                        runtime_guard()
                        table = transform_table(pa.Table.from_batches([batch]))
                        if writer is None:
                            writer = pq.ParquetWriter(partial, table.schema, compression='zstd')
                        writer.write_table(table)
                finally:
                    if writer is not None:
                        writer.close()
                checked = verify_shard(source, partial, identities, runtime_guard)
                if digest(source) != expected_hash:
                    raise ValueError('Baseline changed during preservation')
                partial.replace(target)
                outputs[relative] = {'source_sha256': expected_hash, 'sha256': digest(target), **checked}
                observations += checked['observations']; rows += checked['rows']
            if observations != record['observations_after']:
                raise ValueError('Block coverage mismatch')
            result['records'].append({'subject': record['subject'], 'source_path': record['source_path'],
                                      'observations': observations, 'rows': rows, 'outputs': outputs})
            total += observations
            result['observations'] = total
            save()
        if len(result['records']) != scope['blocks'] or total != scope['observations_after']:
            raise ValueError('Final global scope mismatch')
        if any(digest(path) != sha for path, sha in bindings.items()):
            raise ValueError('Bound evidence changed during execution')
        result.update(status='planar_estimates_preserved_canonical_orientations_withheld_unreviewed', observations=total)
    except Exception as error:
        result.update(status='failed_incomplete', reason=str(error)); raise
    finally:
        save()


if __name__ == '__main__':
    main()
