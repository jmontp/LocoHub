"""Independent station-displacement/source-coordinate check, not anatomy approval.

No native launch. Run after both guarded native outputs have completed. Uses no
writer projection helper and reads at most one source/CSV row at a time.
"""
import argparse
import csv
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
from itertools import zip_longest

BODIES = ('pelvis','femur_r','tibia_r','calcn_r','femur_l','tibia_l','calcn_l')
COORDINATES = ('pelvis_tilt','pelvis_list','pelvis_rotation','pelvis_tx','pelvis_ty','pelvis_tz',
 'hip_flexion_r','hip_adduction_r','hip_rotation_r','knee_angle_r','ankle_angle_r','subtalar_angle_r','mtp_angle_r',
 'hip_flexion_l','hip_adduction_l','hip_rotation_l','knee_angle_l','ankle_angle_l','subtalar_angle_l','mtp_angle_l',
 'lumbar_extension','lumbar_bending','lumbar_rotation')
TRANSLATIONS = frozenset(('pelvis_tx','pelvis_ty','pelvis_tz'))
STATION_COLUMNS = ['source_time_s'] + ['coordinate_'+c for c in COORDINATES] + [
 f'{b}_station{p}_{axis}' for b in BODIES for p in range(4) for axis in 'xyz']
POSE_COLUMNS = ['source_time_s','heading_ground_x','heading_ground_y','heading_ground_z'] + [
 b+s for b in BODIES[1:] for s in ('_axis_ground_x','_axis_ground_y','_axis_ground_z','_projected_angle_rad')]


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024**2),b''):h.update(b)
    return h.hexdigest()


def load_json(path):
    with Path(path).open('rb') as f:raw=f.read(4*1024**2+1)
    if len(raw)>4*1024**2:raise ValueError('JSON admission exceeded')
    return json.loads(raw.decode('utf-8-sig'))


def recheck(bindings):
    for p,h in bindings.items():
        if digest(p)!=h:raise ValueError('Changed bound input: '+p)


def lines(path, cap):
    if Path(path).stat().st_size>cap:raise ValueError('Byte admission exceeded')
    total=0
    with Path(path).open() as f:
        while True:
            line=f.readline(65537)
            if not line:break
            total+=len(line.encode())
            if len(line)>65536 or total>cap:raise ValueError('Read admission exceeded')
            yield line


def source_rows(path,start,end):
    stream=iter(lines(path,64*1024**2));flag=None
    for n,line in enumerate(stream):
        if n>100:raise ValueError('Header admission exceeded')
        stripped=line.strip()
        if stripped.startswith('inDegrees'):
            parts=stripped.split('=')
            if flag is not None or len(parts)!=2 or parts[1].strip() not in ('yes','no'):raise ValueError('Ambiguous coordinate units')
            flag=parts[1].strip()
        if stripped.lower()=='endheader':break
    else:raise ValueError('Missing header')
    if flag is None:raise ValueError('Explicit coordinate units required')
    labels=next(stream).split()
    if not labels or labels[0]!='time' or len(set(labels))!=len(labels):raise ValueError('Invalid labels')
    if not set(COORDINATES)<=set(labels):raise ValueError('Missing coordinates')
    indices=[labels.index(c) for c in COORDINATES];previous=-math.inf;selected=0
    for n,line in enumerate(stream):
        if n>=200000:raise ValueError('Source row admission exceeded')
        values=line.split()
        if len(values)!=len(labels):raise ValueError('Source width differs')
        t=float(values[0])
        if not math.isfinite(t) or t<=previous:raise ValueError('Source clock invalid')
        previous=t
        if start<=t<=end:
            selected+=1
            if selected>2500:raise ValueError('Selected row admission exceeded')
            q=[float(values[i]) for i in indices]
            if not all(map(math.isfinite,q)):raise ValueError('Nonfinite source coordinate')
            yield t,[v*math.pi/180 if flag=='yes' and c not in TRANSLATIONS else v for c,v in zip(COORDINATES,q)]
    if selected<2:raise ValueError('Insufficient source rows')


def csv_rows(path,columns):
    reader=csv.DictReader(lines(path,4*1024**2))
    if reader.fieldnames!=columns:raise ValueError('CSV schema differs')
    for n,row in enumerate(reader):
        if n>=2500 or None in row or any(v is None for v in row.values()):raise ValueError('CSV scope malformed')
        yield {k:float(v) for k,v in row.items()}


def close(a,b,label,tol=1e-7):
    if not math.isfinite(a) or not math.isfinite(b) or abs(a-b)>tol:raise ValueError(label+' differs')


def station_basis(row,body):
    points=[[row[f'{body}_station{p}_{a}'] for a in 'xyz'] for p in range(4)]
    if not all(math.isfinite(x) for p in points for x in p):raise ValueError('Nonfinite station')
    axes=[[p[i]-points[0][i] for i in range(3)] for p in points[1:]]
    for i in range(3):
        for j in range(3):close(sum(a*b for a,b in zip(axes[i],axes[j])),float(i==j),'Station rigid basis')
    x,y,z=axes
    cross=(x[1]*y[2]-x[2]*y[1],x[2]*y[0]-x[0]*y[2],x[0]*y[1]-x[1]*y[0])
    close(sum(a*b for a,b in zip(cross,z)),1.,'Station handedness')
    return axes


def verify_row(stations,pose,source):
    t,q=source
    close(stations['source_time_s'],t,'Station clock',1e-10)
    close(pose['source_time_s'],t,'Pilot clock',1e-10)
    for c,v in zip(COORDINATES,q):close(stations['coordinate_'+c],v,'Source coordinate '+c,1e-10)
    bases={b:station_basis(stations,b) for b in BODIES}
    x=bases['pelvis'][0];norm=math.hypot(x[0],x[2])
    if norm<1e-8:raise ValueError('Undefined pelvis heading')
    h=(x[0]/norm,0.,x[2]/norm)
    for a,v in zip('xyz',h):close(pose['heading_ground_'+a],v,'Pelvis station heading')
    for b in BODIES[1:]:
        axis=bases[b][0] if b.startswith('calcn') else [-v for v in bases[b][1]]
        for a,v in zip('xyz',axis):close(pose[b+'_axis_ground_'+a],v,'Native station axis '+b)
        f=sum(a*v for a,v in zip(axis,h));up=axis[1];angle=pose[b+'_projected_angle_rad']
        if math.hypot(f,up)<1e-8:
            if not math.isnan(angle):raise ValueError('Degenerate projection must be missing')
        else:
            expected=math.atan2(up,f) if b.startswith('calcn') else math.atan2(f,-up)
            if not math.isfinite(angle) or abs(math.remainder(angle-expected,2*math.pi))>1e-7:raise ValueError('Native station projection differs')


def verify_files(station_path,pose_path,source_path,start,end):
    count=0
    for s,p,q in zip_longest(csv_rows(station_path,STATION_COLUMNS),csv_rows(pose_path,POSE_COLUMNS),source_rows(source_path,start,end)):
        if s is None or p is None or q is None:raise ValueError('Source/native row coverage differs')
        verify_row(s,p,q);count+=1
    return count


def completed_status(status):
    if status.get('status')!='completed' or type(status.get('exit_code')) is not int or status['exit_code']!=0:
        raise ValueError('Native completion missing')
    if type(status.get('pid')) is not int or status['pid']<=0 or status.get('memory_limit_mib')!=2048 or status.get('timeout_seconds')!=300:
        raise ValueError('Guard identity or resource limits differ')
    try:
        start=datetime.fromisoformat(status['started_utc'].replace('Z','+00:00'))
        end=datetime.fromisoformat(status['finished_utc'].replace('Z','+00:00'))
        if start.tzinfo is None or end.tzinfo is None or end<start:raise ValueError('Invalid terminal time')
    except (KeyError,TypeError,AttributeError) as e:raise ValueError('Missing guard completion time') from e


def audit(plan_path):
    plan_path=Path(plan_path).resolve();p=load_json(plan_path);root=plan_path.parent
    if p['status']!='prepared_not_executed' or p['scientific_approval'] is not False:raise ValueError('Invalid preparation')
    bindings=dict(p['inputs_sha256']);bindings[str(plan_path)]=digest(plan_path)
    if str(Path(__file__).resolve()) not in bindings:raise ValueError('Unbound reviewer')
    required=[Path(__file__).resolve(),Path(__file__).with_name('audit_mblue_orientation_pose_pilot.py').resolve(),
              Path(__file__).with_name('prepare_mblue_orientation_pose_pilot.py').resolve(),
              Path(p['pilot_plan']),Path(p['pilot_options']),root/'options.json',Path(p['source_ik'])]
    if any(str(path) not in bindings for path in required):raise ValueError('Missing dependency binding')
    recheck(bindings)
    original=load_json(p['pilot_plan'])
    if any(bindings.get(path)!=sha for path,sha in original['inputs_sha256'].items()):raise ValueError('Original pilot bindings differ')
    old=Path(p['pilot_plan']).parent
    if Path(p['pilot_options'])!=old/'options.json' or Path(p['pilot_output'])!=old/'body_axes.csv' or Path(p['pilot_status'])!=old/'native_status.json':raise ValueError('Original pilot paths differ')
    original_options=load_json(p['pilot_options'])
    evidence={}
    for status_path,options_path in ((p['pilot_status'],p['pilot_options']),(str(root/'native_status.json'),str(root/'options.json'))):
        status=load_json(status_path)
        expected=load_json(options_path)
        # Exact guarded options identity and completed native process are required.
        from contributor_tools.audit_mblue_orientation_pose_pilot import linux
        completed_status(status)
        if expected.get('model_path')!=original_options.get('model_path'):raise ValueError('Native model identity differs')
        if linux(status.get('options','')).resolve()!=Path(options_path).resolve():raise ValueError('Native options identity differs')
        if linux(expected['ik_path']).resolve()!=Path(p['source_ik']) or expected['start_s']!=p['start_s'] or expected['end_s']!=p['end_s']:raise ValueError('Native source/window identity differs')
        evidence[status_path]=digest(status_path)
        output=linux(expected['output_path']).resolve()
        if output!=Path(p['pilot_output'] if status_path==p['pilot_status'] else root/'stations.csv').resolve():raise ValueError('Output identity differs')
    for path in (p['pilot_output'],str(root/'stations.csv')):evidence[path]=digest(path)
    count=verify_files(root/'stations.csv',p['pilot_output'],p['source_ik'],p['start_s'],p['end_s'])
    recheck(bindings);recheck(evidence)
    report={'status':'independent_source_reader_and_native_station_comparison_passed_unreviewed','scientific_approval':False,
            'rows':count,'inputs_sha256':bindings,'outputs_sha256':evidence,
            'scope':'Six model body-axis directions, pelvis heading, original coordinates and clocks. No canonical anatomical fields restored.',
            'limitations':['Station and vector APIs share the native OpenSim engine; this is not an independent dynamics engine or validation of scaled anatomical landmarks.',
                           'Real source check covers only the prepared source window, not all 335 blocks or 15061 observations.']}
    with (root/'station_audit.json').open('x') as f:json.dump(report,f,indent=2)
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plan',type=Path,required=True)
    print(json.dumps(audit(parser.parse_args().plan)))
