"""Known boundary labels and linear synthetic signals for recovered cycles."""
import json
import h5py
import numpy as np
import pandas as pd
import pytest
from contributor_tools.recover_umich_curated_boundaries import recovered_window, verify_cycle
from contributor_tools.reconvert_umich_streaming import cycle_frame
from contributor_tools.reconvert_umich_running import source_components


def item():
    return {'subject':'AB01','condition':'i0','reference_side':'right','start_frame':2,'end_frame':12,
            'original_normalized_task':'s0x8','boundary_reason':'curated_label_contains_start_but_not_end',
            'overlapping_streaming_windows':[{'label':'s0x8','start_frame':1,'end_frame':7,'contains_start':True,'contains_end':False}]}


def test_cycle_start_label_does_not_claim_full_cycle_speed():
    window=recovered_window(item())
    assert window['task']=='level_walking'
    assert window['info']['source_task_window_duration_fraction']==.5
    assert window['info']['source_nominal_speed_m_s']==.8
    assert 'speed_m_s' not in window['info']
    assert window['info']['cycle_crosses_source_task_window']


def test_ambiguous_label_window_is_rejected():
    record=item();record['overlapping_streaming_windows']*=2
    with pytest.raises(ValueError,match='Ambiguous'):recovered_window(record)


def test_false_boundary_geometry_is_rejected():
    record=item();record['overlapping_streaming_windows'][0]['end_frame']=12
    with pytest.raises(ValueError,match='geometry'):recovered_window(record)


@pytest.mark.parametrize('corrupt',[False,True])
def test_independent_source_readback(tmp_path,corrupt):
    with h5py.File(tmp_path/'synthetic.mat','w') as h:
        trial=h.create_group('trial');angles=trial.create_group('jointAngles')
        for name in ['RPelvisAngles','RHipAngles','LHipAngles','RKneeAngles','LKneeAngles','RAnkleAngles','LAnkleAngles']:
            values=np.zeros((3,20));values[0]=np.arange(20)*10
            angles.create_dataset(name,data=values)
        record=item();frame=cycle_frame(trial,'AB01','i0',recovered_window(record))
        values,_=source_components(trial,2,12);frame=pd.concat([frame,pd.DataFrame(values)],axis=1)
        # Ten degrees per .01 s gives 1000 deg/s, independent of phase indexing.
        np.testing.assert_allclose(frame.hip_flexion_velocity_ipsi_rad_s,1000*np.pi/180)
        if corrupt:
            frame.loc[70,'source_joint_angle_rhipangles_component_0_deg']+=1
            with pytest.raises(AssertionError):verify_cycle(frame,trial,record)
        else:
            result=verify_cycle(frame,trial,record)
            assert result['finite_source_values_checked']==7*3*150
