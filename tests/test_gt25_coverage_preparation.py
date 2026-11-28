"""Text/AST and tiny synthetic file fixtures; no scientific datasets loaded."""
import ast
from pathlib import Path
import pytest
from contributor_tools.prepare_gt25_coverage_fix import (
    ROOT, FAMILY, patch_converter, patch_mapping, patch_runner, prepare,
)


def assignment(source, name):
    node = next(n for n in ast.parse(source).body
                if isinstance(n, (ast.Assign, ast.AnnAssign))
                and ((isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
                     or (isinstance(n, ast.AnnAssign) and n.target.id == name)))
    return ast.literal_eval(node.value)


def test_shuffle_mapping_matches_readme_without_changing_other_tasks():
    for name, patch, variable in [
        ('convert_gtech_2025_da_to_parquet.py', patch_converter, 'TASK_MAPPING'),
        ('task_mapping.py', patch_mapping, 'FULL_TASK_MAPPING'),
    ]:
        source = (ROOT/FAMILY/name).read_text()
        before, after = assignment(source, variable), assignment(patch(source), variable)
        key = r'normal_walk.*_shuffle'
        changed = after.pop(key)
        before.pop(key)
        assert before == after
        assert changed[0:2] == ('level_walking', 'level_0.4ms')
        assert changed[2]['speed_m_s'] == .4
        assert changed[2]['source_variant'] == 'shuffle'


def test_shuffle_patch_leaves_numerical_functions_identical():
    original = (ROOT/FAMILY/'convert_gtech_2025_da_to_parquet.py').read_text()
    before = [ast.dump(n) for n in ast.parse(original).body if isinstance(n, ast.FunctionDef)]
    after = [ast.dump(n) for n in ast.parse(patch_converter(original)).body if isinstance(n, ast.FunctionDef)]
    assert before == after


def test_patch_refuses_changed_mapping():
    source = (ROOT/FAMILY/'convert_gtech_2025_da_to_parquet.py').read_text()
    with pytest.raises(ValueError):
        patch_converter(source.replace("(None, 'shuffle', {})", "('agility_drill', 'shuffle', {})"))


def test_runner_uses_worker_selection_and_keeps_guard_limits(tmp_path):
    source = patch_runner((ROOT/'contributor_tools/run_gt25_batch.py').read_text())
    tree = ast.parse(source)
    helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'selected_source_bytes')
    # Minimal synthetic adapter obeys the same source discovery interface.
    code = tmp_path/'adapter'
    code.mkdir()
    (code/'reconvert_recording.py').write_text(
        'def source_paths(args):\n'
        '    trial = args.source_root / args.subject / args.recording\n'
        '    return trial, [trial / "used.csv", args.source_root.parent / "readme.txt"], None\n')
    source_root = tmp_path/'Parsed'
    trial = source_root/'BT01'/'recording'
    trial.mkdir(parents=True)
    (trial/'used.csv').write_bytes(b'1234567')
    (trial/'unused.csv').write_bytes(b'x'*100)
    (tmp_path/'readme.txt').write_bytes(b'abcd')
    namespace = {'CODE': code}
    exec(compile(ast.Module(body=[helper], type_ignores=[]), '<isolated-helper>', 'exec'), namespace)
    assert namespace['selected_source_bytes'](source_root, 'BT01', 'recording') == 11
    (trial/'used.csv').unlink()
    with pytest.raises(FileNotFoundError):
        namespace['selected_source_bytes'](source_root, 'BT01', 'recording')
    assert "record['selected_source_bytes']>64*1024**2" in source
    assert "'--memory-mib','1536','--max-source-mib','64'" in source
    assert 'timeout=180' in source


def test_prepare_copies_relative_import_tree_and_refuses_overwrite(tmp_path):
    readme = tmp_path/'readme.txt'
    readme.write_text('normal_walk: ambulating at different speeds on a level treadmill\n_shuffle: walking at 0.4 m/s\n')
    output = tmp_path/'prepared'
    result = prepare(output, readme)
    assert result['status'] == 'prepared_unreviewed_not_run'
    assert result['scientific_approval'] is False
    snapshot = output/'isolated_repo'
    assert (snapshot/FAMILY/'reconvert_recording.py').exists()
    assert (snapshot/'contributor_tools/common/stride_segmentation.py').exists()
    assert (snapshot/'contributor_tools/reconvert_recording.py').exists()
    for relative in result['snapshot_code']:
        ast.parse((snapshot/relative).read_text())
    with pytest.raises(FileExistsError):
        prepare(output, readme)


def test_prepare_rejects_missing_source_evidence(tmp_path):
    readme = tmp_path/'readme.txt'
    readme.write_text('shuffle means something else')
    with pytest.raises(ValueError, match='README evidence'):
        prepare(tmp_path/'output', readme)
    assert not (tmp_path/'output').exists()
