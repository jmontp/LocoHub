"""Synthetic rigid landmark fixtures; not a GT23 native result."""
import copy
import math
import pytest
from contributor_tools.check_gt23_known_pose import check, geometry, COORDINATES

def points():
    p={'RASI':(0,0,1),'LASI':(0,0,-1),'RPSI':(-1,0,1),'LPSI':(-1,0,-1)}
    for side,prefix,z in [('r','R',1),('l','L',-1)]:
        p.update({'hip_'+side:(0,0,z),'knee_'+side:(0,-1,z),prefix+'KNE':(0,-1,z+.1),prefix+'MKNE':(0,-1,z-.1),
                  prefix+'ANK':(0,-2,z+.1),prefix+'MANK':(0,-2,z-.1),prefix+'CAL':(-.2,-2,z),prefix+'MT1':(.5,-2,z+.1),prefix+'MT5':(.5,-2,z-.1)})
    return p

def poses():
    out=[{'pose':'neutral','coordinates':dict.fromkeys(COORDINATES,0),'stations':points()}]
    for c in COORDINATES:
        side=c[-1];prefix=side.upper()
        for label,direction in [('minus',-1),('plus',1)]:
            p=points(); q=direction*math.pi/180
            if c.startswith('hip'):
                pivot=p['hip_'+side]; moving=['knee_'+side]+[prefix+x for x in ['KNE','MKNE','ANK','MANK','CAL','MT1','MT5']]
            elif c.startswith('knee'):
                pivot=p['knee_'+side]; moving=[prefix+x for x in ['ANK','MANK','CAL','MT1','MT5']]
            else:
                pivot=(0,-2,1 if side=='r' else -1);moving=[prefix+x for x in ['CAL','MT1','MT5']]
            for name in moving:
                x,y,z=p[name];x-=pivot[0];y-=pivot[1]
                p[name]=(pivot[0]+math.cos(q)*x-math.sin(q)*y,pivot[1]+math.sin(q)*x+math.cos(q)*y,z)
            out.append({'pose':c+':'+label,'coordinates':dict(dict.fromkeys(COORDINATES,0),**{c:q}),'stations':p})
    return out

def test_known_geometry_and_all_six_directions():
    assert all(abs(x)<1e-12 for x in geometry(points()).values())
    report=check(poses()); assert len(report['checks'])==6
    assert not report['scientific_approval'] and not report['published_moment_generalized_force_verified']
    for row in report['checks']:
        assert row['plus_landmark_delta_rad']==pytest.approx(row['producer_sign']*math.pi/180)

@pytest.mark.parametrize('fault',['missing','duplicate','coordinate','direction','wrong_side','degenerate','nan'])
def test_adversarial(fault):
    p=poses()
    if fault=='missing':p.pop()
    if fault=='duplicate':p[-1]=copy.deepcopy(p[-2])
    if fault=='coordinate':p[1]['coordinates']['hip_flexion_r']=0
    if fault=='direction':p[1]['stations'],p[2]['stations']=p[2]['stations'],p[1]['stations']
    if fault=='wrong_side':p[2]['stations']=copy.deepcopy(p[8]['stations'])
    if fault=='degenerate':p[0]['stations']['RASI']=p[0]['stations']['LASI']
    if fault=='nan':p[0]['stations']['RASI']=(float('nan'),0,0)
    with pytest.raises(ValueError):check(p)

def test_virtual_work_requires_same_sign_on_coordinate_and_force():
    for sign in (-1,1):
        q=.03;force=12
        assert (sign*q)*(sign*force)==pytest.approx(q*force)
        if sign==-1:assert (sign*q)*force!=pytest.approx(q*force)


@pytest.mark.parametrize('epsilon',[float('nan'),float('inf'),-float('inf'),0,-.01,1e-12,math.pi/35])
def test_invalid_epsilon(epsilon):
    with pytest.raises(ValueError,match='Epsilon'):check(poses(),epsilon)

@pytest.mark.parametrize('direction',['minus','plus'])
def test_contralateral_only_corruption(direction):
    p=poses()
    row=next(r for r in p if r['pose']=='hip_flexion_r:'+direction)
    # Preserve correct ipsilateral direction; only change the other leg's foot.
    x,y,z=row['stations']['LMT1'];row['stations']['LMT1']=(x,y+.1,z)
    with pytest.raises(ValueError,match='Contralateral'):check(p)

@pytest.mark.parametrize('fault',['missing','extra'])
def test_exact_station_identity(fault):
    p=points()
    if fault=='missing':del p['RASI']
    else:p['invented_station']=(0,0,0)
    with pytest.raises(ValueError,match='Station identity differs'):geometry(p)
