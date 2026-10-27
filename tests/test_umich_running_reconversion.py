"""Source frames, components and units stay distinct in UM21 running exports."""
import h5py
import numpy as np
import pytest
from contributor_tools.reconvert_umich_running import running_windows,source_components


def test_running_events_use_all_pairs_and_verify_reported_durations(tmp_path):
    with h5py.File(tmp_path/'events.h5','w') as f:
        for prefix,hs in [('L',[1,101,201]),('R',[51,151])]:
            f[prefix+'HS']=np.array(hs)
            f[prefix+'StrideTime']=np.diff(hs)
        windows=list(running_windows(f,'s1x8'))
        assert [(w['side'],w['start'],w['end']) for w in windows]==[('left',1,101),('left',101,201),('right',51,151)]
        assert windows[0]['task']=='run'
        assert windows[0]['info']['protocol_max_speed_m_s']==1.8
        f['LStrideTime'][0]=99
        with pytest.raises(ValueError,match='durations disagree'):list(running_windows(f,'s1x8'))


def test_source_components_keep_all_planes_units_and_missing_values(tmp_path):
    with h5py.File(tmp_path/'source.h5','w') as f:
        values=np.vstack([np.arange(150.),1000+np.arange(150.),-20-np.arange(150.)])
        values[1,40:45]=np.nan
        f.create_group('jointMoments')['LHipMoment']=values
        f.create_group('jointAngles')['RHipAngles']=values+10
        fields,mapping=source_components(f,1,150)
        assert len(fields)==6
        for index in range(3):
            col=f'source_joint_moment_lhipmoment_component_{index}_Nm_kg'
            np.testing.assert_array_equal(fields[col],values[index])
            assert mapping[col]['matlab_component_1based']==index+1
            assert mapping[col]['unit']=='Nm_kg'
        assert np.isnan(fields['source_joint_moment_lhipmoment_component_1_Nm_kg'][42])
        np.testing.assert_array_equal(fields['source_joint_angle_rhipangles_component_0_deg'],values[0]+10)
