"""Verify complete MBLUE scope across existing hash-bound audit summaries.

This is a summary/evidence gate, not another numerical or scientific validation.
It reads JSON only and never opens source MAT or output Parquet files.
"""
import argparse
import hashlib
import json
from pathlib import Path

NAMES = ('inventory', 'baseline', 'rebuild', 'source_audit', 'preservation', 'recovery', 'correction')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def index(rows, name):
    result = {}
    for row in rows:
        key = (row['subject'], row['source_path'])
        require(key not in result, f'{name}: duplicate block {key}')
        result[key] = row
    require(bool(result), f'{name}: empty scope')
    return result


def count(value):
    require(type(value) is int and value >= 0, 'Invalid observation count')
    return value


def assess(reports, hashes):
    inventory, baseline, rebuilt, source, preserved, recovery, corrected = (reports[n] for n in NAMES)
    for report in (baseline, rebuilt):
        require(report['status'] == 'all_normalized_blocks_reconstructed_unreviewed', 'Rebuild incomplete')
        require(report['inventory_sha256'] == hashes['inventory'], 'Inventory binding mismatch')
    require(source['status'] == 'all_normalized_blocks_source_checked_unreviewed'
            and source['start_index'] == 0, 'Source audit is partial')
    require(source['summary_sha256'] == hashes['rebuild'], 'Source audit binding mismatch')
    require(preserved['status'] == 'pelvis_fix_preservation_checked_unreviewed'
            and preserved['full_baseline_coverage'] is True
            and preserved['all_other_columns_exactly_preserved'] is True, 'Preservation incomplete')
    require(preserved['baseline_summary_sha256'] == hashes['baseline']
            and preserved['corrected_summary_sha256'] == hashes['rebuild'], 'Preservation binding mismatch')
    require(recovery['status'] == 'all_stair_reference_windows_recovered_unreviewed', 'Recovery incomplete')
    require(corrected['status'] == 'stair_reference_corrected_unreviewed'
            and corrected['scope'] == 'full_baseline', 'Correction is partial')
    require(corrected['baseline_summary_sha256'] == hashes['rebuild']
            and corrected['reference_recovery_sha256'] == hashes['recovery'], 'Correction binding mismatch')
    indexes = {'inventory': index(inventory['blocks'], 'inventory')}
    for name in ('baseline', 'rebuild', 'source_audit', 'preservation', 'correction'):
        indexes[name] = index(reports[name]['records'], name)
        require(indexes[name].keys() == indexes['inventory'].keys(), f'{name}: block set differs from inventory')
    total_blocks = len(indexes['inventory'])
    require(baseline['planned_blocks'] == rebuilt['planned_blocks'] == total_blocks, 'Planned block count mismatch')
    mapping = {}
    for record in recovery['records']:
        require(record['status'] == 'unique_source_matched', 'Ambiguous source recovery')
        candidates = [c for c in record['candidates'] if c['status'] == 'all_windows_matched']
        require(len(candidates) == 1, 'Recovery candidate ambiguity')
        for window in candidates[0]['windows']:
            key = (record['subject'], window['source_path'], window['source_curve_index'])
            require(key not in mapping, 'Duplicate recovered window')
            require(window['reference_side'] in ('left', 'right'), 'Unknown recovered side')
            require(type(key[2]) is int and key[2] > 0, 'Invalid source curve index')
            mapping[key] = window['reference_side']
    retained_all, omitted_all, consumed = set(), set(), set()
    before_total = after_total = 0
    for key, inv in indexes['inventory'].items():
        path = key[1]
        bilateral = '/STS/' in path or path.endswith('/crouch')
        expected_before = count(inv['sides']['l']['cycles']) if bilateral else sum(count(v['cycles']) for v in inv['sides'].values())
        old, new, audited, preservation, correction = (indexes[n][key] for n in
            ('baseline', 'rebuild', 'source_audit', 'preservation', 'correction'))
        require(old['observations'] == new['observations'] == audited['observations']
                == correction['observations_before'] == expected_before, f'Observation count mismatch: {key}')
        require(old['rows'] == new['rows'] == expected_before * 150, 'Row count mismatch')
        require(old['source_sha256'] == new['source_sha256']
                and old['subject_info_sha256'] == new['subject_info_sha256'], 'Source binding mismatch')
        require(sum(count(v) for v in preservation['counts'].values()) == expected_before, 'Preservation count mismatch')
        require(set(correction['outputs']) == set(new['outputs']) == set(old['outputs']), 'Output path scope mismatch')
        kept, omitted = correction['retained_stair_observation_ids'], correction['omitted_nonreference_views']
        require(len(set(kept)) == len(kept) and len(set(omitted)) == len(omitted), 'Duplicate retained/omitted identity')
        require(not set(kept) & set(omitted), 'Retained and omitted overlap')
        if '/stairs/' in path:
            windows = {k: side for k, side in mapping.items() if k[:2] == key}
            require(bool(windows), 'Stair block has no recovered windows')
            expected_kept, expected_omitted = set(), set()
            for k, side in windows.items():
                prefix = f'mblue:{key[0]}_NormalizedStrides.mat:dataOut/{path}'
                expected_kept.add(f'{prefix}:{side[0]}:column:{k[2]}')
                expected_omitted.add(f'{prefix}:{"r" if side == "left" else "l"}:column:{k[2]}')
            require(set(kept) == expected_kept and set(omitted) == expected_omitted, 'Recovered identity mapping mismatch')
            require(expected_before == 2 * len(windows), 'Stair view count mismatch')
            consumed.update(windows)
            expected_after = len(windows)
        else:
            require(not kept and not omitted, 'Nonstair identities changed')
            require(correction['outputs'] == new['outputs'], 'Nonstair output bytes changed')
            expected_after = expected_before
        require(correction['observations_after'] == expected_after, 'Final observation count mismatch')
        require(not retained_all & set(kept) and not omitted_all & set(omitted), 'Cross-block duplicate identity')
        retained_all.update(kept); omitted_all.update(omitted)
        before_total += expected_before; after_total += expected_after
    require(consumed == mapping.keys(), 'Recovered windows omitted from correction scope')
    require(not retained_all & omitted_all, 'Global retained/omitted identity overlap')
    require(source['observations'] == corrected['observations_before'] == before_total
            and corrected['observations_after'] == after_total, 'Global count mismatch')
    return {'status': 'complete_mblue_scope_evidence_checked_unreviewed', 'scientific_approval': False,
            'blocks': total_blocks, 'observations_before': before_total, 'observations_after': after_total,
            'retained_stair_windows': len(retained_all), 'omitted_nonreference_views': len(omitted_all),
            'input_sha256': hashes, 'limitations': [
                'Summary consistency and existing audit coverage only; this gate does not reread numerical values or output files',
                'Anatomical conventions and scientific approval remain separate requirements']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in NAMES:
        parser.add_argument('--' + name.replace('_', '-'), type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'Output already exists; preserve previous evidence')
    raw = {name: getattr(args, name).read_bytes() for name in NAMES}
    hashes = {name: hashlib.sha256(value).hexdigest() for name, value in raw.items()}
    result = assess({name: json.loads(value) for name, value in raw.items()}, hashes)
    for name in NAMES:
        require(hashlib.sha256(getattr(args, name).read_bytes()).hexdigest() == hashes[name], 'Summary changed during gate')
    result['inputs'] = {name: str(getattr(args, name).resolve()) for name in NAMES}
    result['probe_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
