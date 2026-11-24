"""The leg-plane chain (GT23-PL01 steps 2-4) reads gt23_planes_* and writes gt23_pl_* roots (names only, no data)."""
from contributor_tools import audit_gt23_e01 as ae01
from contributor_tools import run_gt23_e01 as e01
from contributor_tools import run_gt23_e02 as e02
from contributor_tools import run_gt23_q01_assessment as q1
from contributor_tools import run_gt23_q01v2 as q2


def test_inputs_are_the_plane_roots():
    assert e01.roots_for('AB05')['c06'].endswith('/gt23_planes_batch_AB05')
    assert e01.roots_for('AB05', 'x')['c06'] == 'x/gt23_planes_batch_AB05'
    assert q1.C06_SUMMARY.endswith('/gt23_planes_summary/summary.json')


def test_outputs_are_the_pl_roots_and_never_the_old_ones():
    for path in (q1.root_for('AB05'), q2.e02_root('AB05'), q2.e02_audit('AB05'), q1.E01_SUMMARY, q1.E01_AUDIT_SUMMARY):
        assert '_pl_' in path and 'c06' not in path, path
    assert q1.root_for('AB05').endswith('gt23_pl_e01_batch_AB05')
    assert q2.e02_root('AB05').endswith('gt23_pl_e02_batch_AB05')
    assert 'gt23_e01_' not in e02.EVIDENCE_NOTE


def test_q01v2_spec_names_use_the_pl_prefix():
    import inspect
    src = inspect.getsource(q2.build_spec)
    assert 'gt23-pl-q01v2-' in src and '"gt23-q01v2-' not in src and 'gt23_pl_q01v2_' in src
