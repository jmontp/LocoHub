import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

path=Path(__file__).resolve().parents[1]/'contributor_tools/audit_probes/2026_10_20/check_gt21_force_fix_preservation.py'
spec=importlib.util.spec_from_file_location('gt21_preservation',path)
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)


def frame():
    return pd.DataFrame({'observation_id':['a','a'],'reference_side':['right','right'],
        'source_start_time_s':[1.,1.],'hip_flexion_angle_ipsi_rad':[.1,.2],
        'hip_flexion_moment_ipsi_Nm_kg':[.5,.6],'grf_vertical_ipsi_BW':[np.nan,1.],
        'cop_anterior_ipsi_m':[0.,np.nan]})


def test_force_changes_report_missing_and_restored_values():
    old=frame();new=old.copy();new.loc[0,'grf_vertical_ipsi_BW']=.5;new.loc[0,'cop_anterior_ipsi_m']=np.nan
    changes=probe.compare_frames(old,new)
    assert changes['grf_vertical_ipsi_BW']=={'changed':1,'missing_to_finite':1,'finite_to_missing':0}
    assert changes['cop_anterior_ipsi_m']=={'changed':1,'missing_to_finite':0,'finite_to_missing':1}


@pytest.mark.parametrize('column,value',[
    ('reference_side','left'),('source_start_time_s',1.1),
    ('hip_flexion_angle_ipsi_rad',.11),('hip_flexion_moment_ipsi_Nm_kg',.51),
])
def test_unrelated_changes_are_rejected(column,value):
    old=frame();new=old.copy();new.loc[0,column]=value
    with pytest.raises(AssertionError):probe.compare_frames(old,new)


def test_schema_changes_are_rejected():
    with pytest.raises(AssertionError,match='schema'):probe.compare_frames(frame(),frame().drop(columns='cop_anterior_ipsi_m'))
