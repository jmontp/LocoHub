"""Paper-backed metadata and AST-only preservation fixtures."""
import ast
from pathlib import Path
import pytest
from contributor_tools.gait120_protocol_metadata import protocol_metadata, metadata_patch_proposal, DOI


@pytest.mark.parametrize('task,field,value,page', [
    ('stair_ascent', 'step_height_m', .10, 8),
    ('stair_descent', 'step_height_m', .10, 8),
    ('incline_walking', 'incline_deg', 10.1, 8),
    ('decline_walking', 'incline_deg', -10.1, 8),
    ('sit_to_stand', 'seat_height_m', .490, 2),
    ('stand_to_sit', 'seat_height_m', .490, 2),
])
def test_paper_dimensions_and_explicit_provenance(task, field, value, page):
    result = protocol_metadata(task)
    assert result[field] == value
    assert set(result) == {field, 'protocol_metadata_evidence'}
    assert result['protocol_metadata_evidence'] == {
        'doi': DOI, 'pdf_page': page, 'scope': 'reported_experimental_apparatus', 'fields': [field]}
    assert not any('speed' in key for key in result)


def test_unknown_and_level_walk_do_not_invent_measurements():
    assert protocol_metadata('level_walking') == {}
    assert protocol_metadata('unknown') == {}
    a = protocol_metadata('stair_ascent')
    a['protocol_metadata_evidence']['fields'].append('invented')
    assert protocol_metadata('stair_ascent')['protocol_metadata_evidence']['fields'] == ['step_height_m']


def test_only_metadata_expansion_changes_existing_function_asts():
    root = Path(__file__).resolve().parents[1]
    original = (root/'contributor_tools/conversion_scripts/Gait120/convert_gait120_to_parquet.py').read_text()
    patched = ast.parse(metadata_patch_proposal(original))
    removed = 0
    for node in ast.walk(patched):
        if isinstance(node, ast.Dict):
            for i in range(len(node.keys)-1, -1, -1):
                value = node.values[i]
                if node.keys[i] is None and isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == 'protocol_metadata':
                    assert len(value.args) == 1 and isinstance(value.args[0], ast.Name) and value.args[0].id == 'task'
                    del node.keys[i]
                    del node.values[i]
                    removed += 1
    assert removed == 1
    before = [ast.dump(n) for n in ast.parse(original).body if isinstance(n, ast.FunctionDef)]
    after = [ast.dump(n) for n in patched.body if isinstance(n, ast.FunctionDef)]
    assert before == after


def test_patch_refuses_changed_source():
    with pytest.raises(ValueError, match='source shape changed'):
        metadata_patch_proposal('import json\n')
