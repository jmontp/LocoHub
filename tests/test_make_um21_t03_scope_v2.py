"""SYNTHETIC scope fixture only."""
import pytest
from contributor_tools.make_um21_t03_scope_v2 import repartition

V1 = {'schema': 's', 'batches': [['A1/x', 'A1/y'], ['A2/x', 'A3/x'], ['A3/y', 'A4/x', 'A4/y'], ['A5/x', 'A6/x']]}


def test_head_kept_tail_split_by_subject_membership_order_preserved():
    v2 = repartition(V1, 1, 'h', 'n')
    assert v2['batches'] == [['A1/x', 'A1/y'], ['A2/x'], ['A3/x', 'A3/y'], ['A4/x', 'A4/y'], ['A5/x'], ['A6/x']]
    assert v2['supersedes_scope_sha256'] == 'h' and V1['batches'][1] == ['A2/x', 'A3/x']  # input untouched


def test_keep_two_leaves_first_two_exactly():
    assert repartition(V1, 2, 'h', 'n')['batches'][:2] == V1['batches'][:2]
