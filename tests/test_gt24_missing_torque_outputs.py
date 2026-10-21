import numpy as np
import pandas as pd
import pytest
from contributor_tools.audit_gt24_missing_torque_outputs import check_missing


def frame():
    result=pd.DataFrame({'reference_side':['left','right']})
    for role in ['ipsi','contra']:
        for joint in ['hip_flexion','knee_flexion','ankle_dorsiflexion']:
            for kind in ['moment','biological_moment']:
                result[f'{joint}_{kind}_{role}_Nm_kg']=[1,np.nan] if role=='ipsi' else [np.nan,1]
    return result


def test_invalid_right_side_follows_reference_leg():
    assert check_missing(frame(),'right')==12


@pytest.mark.parametrize('value',[0,1,np.inf])
def test_plausible_values_and_infinity_are_rejected(value):
    data=frame();data.loc[0,'hip_flexion_moment_contra_Nm_kg']=value
    with pytest.raises(ValueError,match='became a value'):check_missing(data,'right')


def test_missing_columns_and_unknown_sides_do_not_pass():
    with pytest.raises(ValueError,match='Missing expected'):check_missing(frame().drop(columns='knee_flexion_moment_ipsi_Nm_kg'),'right')
    data=frame();data.loc[0,'reference_side']='unknown'
    with pytest.raises(ValueError,match='Unknown reference'):check_missing(data,'right')
