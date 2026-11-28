"""Synthetic task-window policy fixtures; no scientific source files loaded."""
import pytest
from contributor_tools.audit_gt21_adoption_ledger import source_windows, unique


def test_existing_global_label_count_policy_is_preserved():
    labels=['walk']*30+['other']+['walk']*30
    windows=source_windows([i*.01 for i in range(61)],labels,'levelground')
    assert len(windows)==2  # Existing MATLAB policy, not proposed per-region 50.
    assert windows[0]['start_s']==0
    assert windows[1]['end_s']==.6


def test_aggregate_label_count_below_50_not_eligible():
    assert source_windows([i*.01 for i in range(49)],['walk']*49,'levelground')==[]


@pytest.mark.parametrize('count,expected',[(4999,0),(5000,1)])
def test_treadmill_5000_sample_threshold(count,expected):
    assert len(source_windows([i*.001 for i in range(count)],[1.]*count,'treadmill'))==expected


def test_treadmill_does_not_add_unimplemented_duration_rule():
    assert len(source_windows([i*.000001 for i in range(5000)],[1.]*5000,'treadmill'))==1


@pytest.mark.parametrize('clock',[[0,float('nan'),2],[0,0,2],[0,2,1]])
def test_malformed_condition_clocks_rejected(clock):
    with pytest.raises(ValueError):source_windows(clock,['walk']*3,'levelground')


def test_rounded_treadmill_tolerance_boundary_is_explicitly_ambiguous():
    with pytest.raises(ValueError,match='boundary'):
        source_windows([i*.001 for i in range(5000)],[1.025]*5000,'treadmill')


def test_unsupported_labels_do_not_create_fallback_window():
    assert source_windows([i*.01 for i in range(100)],['unrecognized']*100,'levelground')==[]


def test_unsupported_mode_rejected():
    with pytest.raises(ValueError,match='Unsupported'):
        source_windows([0.,1.],['stairascent']*2,'stair')


@pytest.mark.parametrize('items',[[],[{'channel':'gcLeft'},{'channel':'gcLeft'}]])
def test_missing_or_ambiguous_source_manifest_rejected(items):
    with pytest.raises(ValueError):unique(items,lambda x:x['channel']=='gcLeft')
