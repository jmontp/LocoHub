"""Known-value checks for bounded reconstruction, independent of historic outputs."""
import h5py
import numpy as np
from contributor_tools.reconvert_umich_streaming import cycle_frame, windows
from contributor_tools.common.data_contract import inspect_contract


def test_inclusive_derivative_simultaneous_limbs_and_chain(tmp_path):
    path=tmp_path/'source.h5'
    with h5py.File(path,'w') as f:
        trial=f.create_group('trial');angles=trial.create_group('jointAngles')
        t=np.arange(201)/100
        for leg,offset in [('R',10),('L',30)]:
            for name,values in [('HipAngles',offset+20*t),('KneeAngles',5+10*t),('AnkleAngles',90+3*t),('PelvisAngles',np.full(201,2.))]:
                angles[leg+name]=np.vstack([values,np.zeros(201),np.zeros(201)])
        window={'start':1,'end':201,'side':'right','task':'level_walking','label':'s1','info':{'speed_m_s':1}}
        df=cycle_frame(trial,'AB01','i0',window)
        assert inspect_contract(df,mode='phase').schema_passed
        assert df.time_s.iloc[-1]==2
        np.testing.assert_allclose(df.hip_flexion_velocity_ipsi_rad_s,20*np.pi/180,rtol=1e-12)
        np.testing.assert_allclose(df.hip_flexion_angle_contra_rad-df.hip_flexion_angle_ipsi_rad,20*np.pi/180)
        np.testing.assert_allclose(df.thigh_sagittal_angle_ipsi_rad-df.pelvis_sagittal_angle_rad,df.hip_flexion_angle_ipsi_rad)
        assert df.ankle_dorsiflexion_angle_ipsi_rad.isna().all()
        np.testing.assert_allclose(df.source_ankle_sagittal_angle_ipsi_rad.iloc[[0,-1]],[np.pi/2,96*np.pi/180])
        other=cycle_frame(trial,'AB01','i5',window)
        assert other.observation_id.iloc[0]!=df.observation_id.iloc[0]
        left=cycle_frame(trial,'AB01','i0',{**window,'side':'left'})
        np.testing.assert_allclose(left.hip_flexion_angle_ipsi_rad,df.hip_flexion_angle_contra_rad)
        assert left.observation_id.iloc[0]!=df.observation_id.iloc[0]


def test_boundary_cycles_are_accounted_for_not_relabelled(tmp_path):
    with h5py.File(tmp_path/'source.h5','w') as f:
        label=f.create_dataset('label',data=np.array([ord(c) for c in 's1']))
        e=f.create_group('events');e['cutPoints']=np.array([[101],[301]])
        e.create_dataset('tasks',data=np.array([[label.ref]],dtype=h5py.ref_dtype))
        e['RHS']=np.array([[1,101,201,301,401]]);e['LHS']=np.array([[51,151,251,351]])
        result=list(windows(e,f,0))
        assert len(result)==7
        assert sum('excluded' in r for r in result)==4
        assert [(r['start'],r['end']) for r in result if 'excluded' not in r]==[(101,201),(201,301),(151,251)]
