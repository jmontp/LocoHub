import math
import pytest
from contributor_tools.audit_um21_ankle_full_cycle import physical_key,compare


def test_late_cycle_mismatch_not_hidden_by_first_sample():
    key=('left',1,101);curated={key:{'task':'s1'}};raw=[10.]*150
    values=[math.radians(x) for x in raw];values[-1]+=0.01
    result=compare(values,key,curated,lambda ref:raw)
    assert result['status']=='mismatch' and result['max_abs_error_rad']>0.009


def test_contra_never_uses_reference_leg_curated_curve():
    key=physical_key('left','contra',1,101)
    def forbidden(ref):raise AssertionError('Wrong leg curve was read')
    result=compare([0.]*150,key,{('left',1,101):{'task':'s1'}},forbidden)
    assert key==('right',1,101) and result['status']=='unassessed_no_same_side_frame_counterpart'


def test_exact_same_physical_side_and_frames_only():
    key=physical_key('right','contra',1,101)
    curated={('left',1,102):{'task':'different window'}}
    assert compare([0.]*150,key,curated,lambda r:[0.]*150)['status'].startswith('unassessed')


def test_positive_dorsiflexion_without_offset():
    raw=[-15.,0.,20.]*50;key=('left',1,101);curated={key:{'task':'s1'}}
    assert compare([math.radians(x) for x in raw],key,curated,lambda r:raw)['status']=='matched_all150'
    assert compare([math.radians(x+90) for x in raw],key,curated,lambda r:raw)['status']=='mismatch'
    assert compare([math.radians(-x) for x in raw],key,curated,lambda r:raw)['status']=='mismatch'


def test_missingness_and_all_missing_are_not_passes():
    key=('left',1,101);curated={key:{'task':'s1'}}
    values=[0.]*150;values[149]=math.nan
    assert compare(values,key,curated,lambda r:[0.]*150)['missingness_mismatch']
    assert compare([math.nan]*150,key,curated,lambda r:[math.nan]*150)['status']=='mismatch'


@pytest.mark.parametrize('args',[('bad','ipsi',1,101),('left','bad',1,101),('left','ipsi',1.5,101),('left','ipsi',101,1)])
def test_invalid_identity(args):
    with pytest.raises(ValueError):physical_key(*args)
