"""Synthetic stdlib AST/scalar checks only; not scientific regeneration."""
import ast
import importlib.util
import math
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('gt24_prepare', ROOT/'contributor_tools/prepare_gt24_ankle_fix.py')
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


def patched_tree():
    return ast.parse(TOOL.patch_converter((ROOT/TOOL.ADAPTER).read_text()))


def assignment_value(tree, name, namespace):
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
    return eval(compile(ast.Expression(node.value), '<synthetic scalar fixture>', 'eval'), namespace)


@pytest.mark.parametrize('side', ['ipsi', 'contra'])
def test_known_positive_plantarflexion_becomes_negative_dorsiflexion(side):
    value = assignment_value(patched_tree(), f'ankle_{side}_rad',
                             {'resample': lambda x: x, f'ankle_{side}_deg': 30., 'deg2rad': math.pi/180})
    assert value == pytest.approx(-math.pi/6)


@pytest.mark.parametrize('side', ['ipsi', 'contra'])
@pytest.mark.parametrize('biological', [False, True])
def test_known_source_moment_changes_sign(side, biological):
    class Values:
        def __getitem__(self, key):
            return 2.5
    frame = {'ankle_angle_l_moment': SimpleNamespace(values=Values())}
    variable = f'ankle_bio_mom_{side}' if biological else f'ankle_mom_{side}'
    value = assignment_value(patched_tree(), variable,
        {'resample': lambda x: x, side: 'l', 'start_idx': 0, 'end_idx': 1,
         'moment_df': frame, 'bio_moment_df': frame})
    assert value == -2.5


def test_only_stride_function_changes_and_imu_dependency_stays_independent():
    original = ast.parse((ROOT/TOOL.ADAPTER).read_text())
    updated = patched_tree()
    funcs = lambda tree: {n.name: ast.dump(n) for n in tree.body if isinstance(n, ast.FunctionDef)}
    before, after = funcs(original), funcs(updated)
    assert {name for name in before if before[name] != after[name]} == {'process_stride'}
    for name in ['compute_segment_angles_from_imu', 'compute_segment_angles_from_imu_with_accel_init', 'calculate_foot_angle_offset']:
        node = next(n for n in original.body if isinstance(n, ast.FunctionDef) and n.name == name)
        references = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
        assert not references & {'ankle_ipsi_rad', 'ankle_contra_rad', 'angle_df'}


def test_source_alias_restores_original_sign_and_missingness():
    tree = patched_tree()
    aliases = {k.value: value for node in ast.walk(tree) if isinstance(node, ast.Dict)
               for k, value in zip(node.keys, node.values)
               if isinstance(k, ast.Constant) and isinstance(k.value, str) and k.value.startswith('source_ankle_coordinate_')}
    assert len(aliases) == 10
    for expression in aliases.values():
        assert isinstance(expression, ast.UnaryOp) and isinstance(expression.op, ast.USub)
        for value in [-3., float('nan')]:
            actual = eval(compile(ast.Expression(expression), '<synthetic alias>', 'eval'), {expression.operand.id: value})
            assert math.isnan(actual) if math.isnan(value) else actual == 3.


def test_assistance_assignments_are_unchanged():
    old = ast.parse((ROOT/TOOL.ADAPTER).read_text())
    new = patched_tree()
    extract = lambda tree: [ast.dump(n) for n in ast.walk(tree) if isinstance(n, ast.Assign)
                            and any(isinstance(t, ast.Name) and t.id.startswith('ankle_assist') for t in n.targets)]
    assert extract(old) == extract(new)


def test_unreviewed_code_shape_rejected():
    source = (ROOT/TOOL.ADAPTER).read_text().replace('ankle_ipsi_rad = resample(ankle_ipsi_deg * deg2rad)', 'ankle_ipsi_rad = changed()')
    with pytest.raises(ValueError, match='source shape changed'):
        TOOL.patch_converter(source)
