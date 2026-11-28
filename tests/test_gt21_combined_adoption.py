"""Synthetic adoption gates; these fixtures do not certify source datasets."""
from pathlib import Path
import pytest
from contributor_tools.prepare_gt21_combined_adoption import combined_source
from contributor_tools.gt21_adoption_coverage import audit_complete_pairs, label_segments


def pair(side, start, end, **changes):
    row=dict(side=side,start_s=start,end_s=end,matching_windows=1,
             source_cycle_samples=101,source_ik_samples=101,source_id_samples=101,
             maximum_source_phase=99.)
    row.update(changes)
    return row


def test_complete_recovery_requires_every_eligible_pair():
    source=[pair('right',0.,1.),pair('left',.5,1.5),pair('left',1.5,2.5)]
    with pytest.raises(ValueError,match='missing='):
        audit_complete_pairs(source,source[:2])
    assert audit_complete_pairs(source,source)['eligible_pairs']==3


def test_excluded_pair_is_explicit_and_must_not_be_exported():
    source=[pair('right',0.,1.),pair('left',.5,1.5,matching_windows=0)]
    report=audit_complete_pairs(source,source[:1])
    assert report['exclusions'][0]['reason']=='outside_complete_eligible_task_window'
    assert report['force_cop_checked'] is False
    with pytest.raises(ValueError,match='unexpected='):
        audit_complete_pairs(source,source)


@pytest.mark.parametrize('fault',['duplicate','ambiguous','nonfinite','empty'])
def test_bad_recovery_evidence_rejected(fault):
    source=[pair('right',0.,1.)];output=list(source)
    if fault=='duplicate':output+=output
    elif fault=='ambiguous':source=[pair('right',0.,1.,matching_windows=2)]
    elif fault=='nonfinite':source=[pair('right',0.,1.,maximum_source_phase=float('nan'))]
    else:source=[]
    with pytest.raises(ValueError):audit_complete_pairs(source,output)


@pytest.mark.parametrize('clock',[[0.,float('nan'),2.],[0.,0.,2.],[0.,2.,1.],['0','1','2']])
def test_proposed_label_clock_rejects_malformed_values(clock):
    with pytest.raises(ValueError):label_segments(clock,['walk']*3,'walk',1)


def test_disjoint_short_regions_do_not_pool_sample_counts():
    labels=['walk']*30+['other']+['walk']*30
    assert label_segments([i*.01 for i in range(61)],labels,'walk')==[]


def test_only_individually_long_region_survives():
    labels=['walk']*60+['other']+['walk']*10
    assert label_segments([i*.01 for i in range(71)],labels,'walk')==[(0.,.59)]


@pytest.mark.parametrize('count,accepted',[(49,False),(50,True)])
def test_per_region_minimum_boundary(count,accepted):
    assert bool(label_segments([i*.01 for i in range(count)],['walk']*count,'walk')) is accepted


def test_combined_patch_retains_both_fixes_and_clock_guard():
    source=Path('contributor_tools/conversion_scripts/Gtech_2021/convert_gtech_2021_phase_to_parquet.m').read_text()
    result=combined_source(source)
    assert "for reference = {'right','left'}" in result
    assert 'stair_height_m = 0.102' not in result
    assert 'Unknown direction, assume ascent by default' not in result
    assert "'LocoHub:TerrainClock'" in result
    assert 'all(diff(clock) > 0)' in result
    anchor='function rows = extract_and_process_strides_single_leg('
    # Actual signal conversion remains byte-identical to the frozen source.
    assert result[result.index(anchor):result.index('\nfunction require_terrain_inputs(')] == source[source.index(anchor):]
