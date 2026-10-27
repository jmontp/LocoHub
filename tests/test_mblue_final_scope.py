"""Synthetic JSON-only acceptance fixtures, not scientific reconstruction."""
import copy
import pytest
from contributor_tools.check_mblue_final_scope import assess, NAMES


@pytest.fixture
def evidence():
    hashes = {name: name + '-hash' for name in NAMES}
    keys = [('SYN', 'bare/level'), ('SYN', 'bare/stairs/ascent/s1')]
    records = []
    for subject, path in keys:
        records.append(dict(subject=subject, source_path=path, observations=2, rows=300,
                            source_sha256='source', subject_info_sha256='mass',
                            outputs={path + '/phase.parquet': 'before'}))
    rebuild = dict(status='all_normalized_blocks_reconstructed_unreviewed',
                   inventory_sha256=hashes['inventory'], planned_blocks=2, records=records)
    prefix = 'mblue:SYN_NormalizedStrides.mat:dataOut/bare/stairs/ascent/s1'
    corrected = []
    for i, row in enumerate(records):
        corrected.append(dict(subject=row['subject'], source_path=row['source_path'],
            observations_before=2, observations_after=1 if i else 2,
            retained_stair_observation_ids=[prefix + ':l:column:1'] if i else [],
            omitted_nonreference_views=[prefix + ':r:column:1'] if i else [],
            outputs={k: 'after' if i else v for k, v in row['outputs'].items()}))
    reports = dict(inventory={'blocks': [dict(subject=s, source_path=p,
                    sides={'l': {'cycles': 1}, 'r': {'cycles': 1}}) for s, p in keys]},
        baseline=copy.deepcopy(rebuild), rebuild=copy.deepcopy(rebuild),
        source_audit=dict(status='all_normalized_blocks_source_checked_unreviewed', start_index=0,
            summary_sha256=hashes['rebuild'], observations=4,
            records=[dict(subject=s, source_path=p, observations=2) for s, p in keys]),
        preservation=dict(status='pelvis_fix_preservation_checked_unreviewed',
            full_baseline_coverage=True, all_other_columns_exactly_preserved=True,
            baseline_summary_sha256=hashes['baseline'], corrected_summary_sha256=hashes['rebuild'],
            records=[dict(subject=s, source_path=p, counts={'left_unchanged': 1, 'right_changed': 1}) for s, p in keys]),
        recovery=dict(status='all_stair_reference_windows_recovered_unreviewed', records=[
            dict(subject='SYN', status='unique_source_matched', candidates=[
                dict(status='all_windows_matched', windows=[dict(source_path=keys[1][1],
                     source_curve_index=1, reference_side='left')])])]),
        correction=dict(status='stair_reference_corrected_unreviewed', scope='full_baseline',
            baseline_summary_sha256=hashes['rebuild'], reference_recovery_sha256=hashes['recovery'],
            observations_before=4, observations_after=3, records=corrected))
    return reports, hashes


def test_complete_synthetic_scope(evidence):
    result = assess(*evidence)
    assert result['observations_before'] == 4 and result['observations_after'] == 3
    assert result['retained_stair_windows'] == result['omitted_nonreference_views'] == 1
    assert result['scientific_approval'] is False


@pytest.mark.parametrize('name', ['baseline', 'rebuild', 'source_audit', 'preservation', 'correction'])
def test_duplicate_cannot_mask_missing_block(evidence, name):
    reports, hashes = evidence
    reports[name]['records'][1] = copy.deepcopy(reports[name]['records'][0])
    with pytest.raises(ValueError, match='duplicate block'):
        assess(reports, hashes)


@pytest.mark.parametrize('kind', ['partial', 'count', 'swapped', 'unused_window', 'hash', 'bytes'])
def test_wrong_scope_identity_or_lineage_refused(evidence, kind):
    reports, hashes = evidence
    c = reports['correction']
    if kind == 'partial': c['scope'] = 'explicit_block'
    elif kind == 'count': c['observations_after'] = 4
    elif kind == 'swapped':
        row = c['records'][1]
        row['retained_stair_observation_ids'], row['omitted_nonreference_views'] = row['omitted_nonreference_views'], row['retained_stair_observation_ids']
    elif kind == 'unused_window':
        windows = reports['recovery']['records'][0]['candidates'][0]['windows']
        windows.append(dict(source_path='bare/stairs/descent/s2', source_curve_index=1, reference_side='right'))
    elif kind == 'hash': reports['source_audit']['summary_sha256'] = 'wrong'
    else: c['records'][0]['outputs']['bare/level/phase.parquet'] = 'changed'
    with pytest.raises(ValueError):
        assess(reports, hashes)
