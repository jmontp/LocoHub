"""Synthetic metadata-only lineage planning, without numerical source access."""
import pytest
from contributor_tools import plan_mblue_orientation_lineage as planner


@pytest.fixture
def inputs(monkeypatch):
    monkeypatch.setattr(planner, 'model_evidence', lambda *args: {'status': 'execution_binding_missing'})
    inventory = {'blocks': [{'subject': 'SYN', 'source_path': path}
                            for path in ('bare/stairs/ascent/s1', 'bare/level_1x0')]}
    rebuild = {'records': [dict(**b, subject_info_sha256='info', source_sha256='normalized')
                           for b in inventory['blocks']]}
    recovery = {'records': [{'subject': 'SYN', 'status': 'unique_source_matched',
        'subject_info_sha256': 'info', 'normalized_sha256': 'normalized',
        'candidates': [{'status': 'all_windows_matched',
            'ik_path': '/synthetic/SYN/older/bare_stairs_corrected_IK_Results.mot',
            'ik_sha256': 'ik', 'windows': [{'source_path': 'bare/stairs/ascent/s1',
                'source_curve_index': 1, 'reference_side': 'right',
                'source_event_start_s': 1.0, 'source_event_end_s': 2.0}]}]}]}
    return inventory, rebuild, recovery, {'records': []}


def test_source_matched_older_date_kept_and_unmapped_explicit(inputs):
    result = planner.plan(*inputs)
    assert result['blocks_with_ik_path'] == 1
    assert result['stair_windows_mapped'] == 1
    assert '/older/' in result['records'][0]['ik_path']
    assert result['records'][0]['retained_windows'][0]['observation_id'].endswith(':r:column:1')
    assert result['records'][1]['status'] == 'needs_hash_bound_fileinfo_metadata_receipt'
    assert result['scientific_approval'] is False


@pytest.mark.parametrize('field', ['subject_info_sha256', 'source_sha256'])
def test_wrong_recovery_source_binding_rejected(inputs, field):
    inputs[1]['records'][0][field] = 'wrong'
    with pytest.raises(ValueError, match='lineage differ'):
        planner.plan(*inputs)


def test_ambiguous_recovery_does_not_choose_latest(inputs):
    candidates = inputs[2]['records'][0]['candidates']
    candidates.append(candidates[0].copy())
    with pytest.raises(ValueError, match='Unique source'):
        planner.plan(*inputs)


@pytest.mark.parametrize('problem', ['duplicate_inventory', 'extra_rebuild', 'unknown_condition'])
def test_scope_or_condition_mismatch_refused(inputs, problem):
    if problem == 'duplicate_inventory':
        inputs[0]['blocks'].append(inputs[0]['blocks'][0].copy())
    elif problem == 'extra_rebuild':
        inputs[1]['records'].append(dict(inputs[1]['records'][0], source_path='bare/extra'))
    else:
        inputs[0]['blocks'][1]['source_path'] = 'unknown/level_1x0'
        inputs[1]['records'][1]['source_path'] = 'unknown/level_1x0'
    with pytest.raises(ValueError):
        planner.plan(*inputs)
