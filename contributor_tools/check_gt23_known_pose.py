"""Independent model-landmark diagnostic; never grants raw-export anatomy approval.

Consumes a future native probe's thirteen poses. No converter math or source arrays.
Landmark planes are diagnostic definitions, not a claim to ISB joint angles.
"""
import math

COORDINATES = tuple(f'{joint}_{side}' for side in ('r', 'l') for joint in ('hip_flexion', 'knee_angle', 'ankle_angle'))

STATIONS = frozenset(('RASI', 'LASI', 'RPSI', 'LPSI')) | frozenset(
    prefix+name for prefix in ('R', 'L') for name in ('KNE', 'MKNE', 'ANK', 'MANK', 'CAL', 'MT1', 'MT5')
) | frozenset(f'{joint}_{side}' for joint in ('hip', 'knee') for side in ('r', 'l'))

def sub(a, b): return tuple(x-y for x,y in zip(a,b))
def dot(a, b): return sum(x*y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def unit(a):
    n=math.sqrt(dot(a,a))
    if not math.isfinite(n) or n<1e-8: raise ValueError('Degenerate landmark geometry')
    return tuple(x/n for x in a)
def mean(a,b): return tuple((x+y)/2 for x,y in zip(a,b))
def angle(y,x):
    if math.hypot(x,y)<1e-8: raise ValueError('Degenerate sagittal projection')
    return math.atan2(y,x)
def delta(a,b): return math.atan2(math.sin(a-b),math.cos(a-b))

def geometry(points):
    if set(points)!=STATIONS:
        raise ValueError(f'Station identity differs: missing={sorted(STATIONS-set(points))}, extra={sorted(set(points)-STATIONS)}')
    for p in points.values():
        if len(p)!=3 or not all(math.isfinite(v) for v in p): raise ValueError('Invalid station')
    lateral=unit(sub(points['RASI'],points['LASI']))
    front=sub(mean(points['RASI'],points['LASI']),mean(points['RPSI'],points['LPSI']))
    anterior=unit(sub(front,tuple(dot(front,lateral)*x for x in lateral)))
    superior=unit(cross(lateral,anterior))
    result={}
    for side,prefix in [('r','R'),('l','L')]:
        thigh=sub(mean(points[prefix+'KNE'],points[prefix+'MKNE']),points['hip_'+side])
        shank=sub(mean(points[prefix+'ANK'],points[prefix+'MANK']),points['knee_'+side])
        foot=sub(mean(points[prefix+'MT1'],points[prefix+'MT5']),points[prefix+'CAL'])
        thigh_tilt=angle(dot(thigh,anterior),-dot(thigh,superior))
        shank_tilt=angle(dot(shank,anterior),-dot(shank,superior))
        foot_elevation=angle(dot(foot,superior),dot(foot,anterior))
        result['hip_flexion_'+side]=thigh_tilt
        result['knee_angle_'+side]=-delta(shank_tilt,thigh_tilt)
        result['ankle_angle_'+side]=delta(foot_elevation,shank_tilt)
    return result

def check(poses, epsilon=math.pi/180):
    # Local diagnostic only: refuse steps below the coordinate tolerance scale
    # or beyond five degrees, where this neutral-pose direction test is unjustified.
    if not math.isfinite(epsilon) or not math.pi/1800<=epsilon<=math.pi/36:
        raise ValueError('Epsilon must be finite and between 0.1 and 5 degrees')
    expected={'neutral'}|{f'{c}:{s}' for c in COORDINATES for s in ('minus','plus')}
    if len(poses)!=13 or {p['pose'] for p in poses}!=expected: raise ValueError('Exact unique thirteen-pose scope required')
    rows={p['pose']:p for p in poses}
    values={}
    for name,p in rows.items():
        if set(p['coordinates'])!=set(COORDINATES): raise ValueError('Coordinate identity differs')
        for c,v in p['coordinates'].items():
            wanted=(epsilon if name==c+':plus' else -epsilon if name==c+':minus' else 0)
            if not math.isfinite(v) or abs(v-wanted)>1e-9: raise ValueError('Native pose coordinate differs')
        values[name]=geometry(p['stations'])
    checks=[]
    for c in COORDINATES:
        sign=-1 if c.startswith('knee') else 1
        minus=delta(values[c+':minus'][c],values['neutral'][c])
        plus=delta(values[c+':plus'][c],values['neutral'][c])
        if sign*minus>=-epsilon*0.1 or sign*plus<=epsilon*0.1: raise ValueError('Landmark direction disagrees: '+c)
        other='l' if c.endswith('_r') else 'r'
        if any(abs(delta(values[c+':'+direction][k],values['neutral'][k]))>1e-8
               for direction in ('minus', 'plus') for k in COORDINATES if k.endswith('_'+other)):
            raise ValueError('Contralateral pose changed')
        checks.append({'coordinate':c,'producer_sign':sign,'minus_landmark_delta_rad':minus,'plus_landmark_delta_rad':plus,
                       'virtual_work_identity':'(s*Q)*(s*dq) = Q*dq for s in {-1,+1}; conditional on Q being generalized force conjugate to q'})
    return {'status':'model_landmark_coordinate_direction_checked_unreviewed','checks':checks,
            'scientific_approval':False,'raw_csv_coordinate_link_verified':False,
            'published_moment_generalized_force_verified':False,'segment_euler_convention_verified':False}
