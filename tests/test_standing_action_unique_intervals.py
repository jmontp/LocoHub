"""Multiple bursts inside one standing-to-standing interval are one observation."""
import numpy as np
import pandas as pd
from contributor_tools.common.stride_segmentation import StandingActionConfig,segment_standing_action_cycles


def trial(stable_between):
    velocity=np.zeros(301);velocity[100:130]=1;velocity[150:180]=1
    total=np.ones(301);total[80:200]=.7
    if stable_between:total[130:150]=1
    return pd.DataFrame({'time_s':np.arange(301)/100,'grf_vertical_ipsi_BW':total/2,
        'grf_vertical_contra_BW':total/2,'motion':velocity})


def config():
    return StandingActionConfig(velocity_cols=('motion',),smooth_window_s=0,
        margin_before_s=0,margin_after_s=0,min_segment_duration_s=.1,use_iqr_filtering=False)


def test_multiple_motion_bursts_share_one_physical_interval():
    segments=segment_standing_action_cycles(trial(False),config(),'lunge')
    assert len(segments)==1
    assert (segments[0].start_idx,segments[0].end_idx)==(79,200)
    assert segments[0].metadata['candidate_count']==2


def test_distinct_stable_intervals_are_preserved():
    segments=segment_standing_action_cycles(trial(True),config(),'lunge')
    assert len(segments)==2
    assert len({(s.start_idx,s.end_idx) for s in segments})==2
    assert all(s.metadata['candidate_count']==1 for s in segments)
