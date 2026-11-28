"""Synthetic rigid poses only; no participant arrays or native engine loaded."""
import copy
import csv
import math
import pytest
from contributor_tools import check_mblue_native_stations as check
from contributor_tools.prepare_mblue_station_check import coordinate_policy


def fixture(tilted=False):
    stations={'source_time_s':0.};q=[0.]*23
    stations.update({'coordinate_'+c:v for c,v in zip(check.COORDINATES,q)})
    pose={'source_time_s':0.,'heading_ground_x':0. if tilted else 1.,'heading_ground_y':0.,'heading_ground_z':-1. if tilted else 0.}
    for index,b in enumerate(check.BODIES):
        s=(.5 if b.endswith('_r') else -.5) if tilted and b!='pelvis' else 0.
        c=math.sqrt(1-s*s)
        axes=[(0.,s,-c),(0.,c,s),(1.,0.,0.)] if tilted else [(1.,0.,0.),(0.,1.,0.),(0.,0.,1.)]
        origin=(index*2.,index*3.,-index*5.)
        for p,offset in enumerate([(0.,0.,0.)]+axes):
            for a,v,o in zip('xyz',offset,origin):stations[f'{b}_station{p}_{a}']=o+v
        if b!='pelvis':
            vector=axes[0] if b.startswith('calcn') else tuple(-v for v in axes[1])
            for a,v in zip('xyz',vector):pose[b+'_axis_ground_'+a]=v
            pose[b+'_projected_angle_rad']=math.pi/6*(1 if b.endswith('_r') else -1) if tilted else 0.
    return stations,pose,(0.,q)


@pytest.mark.parametrize('tilted',[False,True])
def test_known_bilateral_zero_and_yawed_30_degree_poses(tilted):
    # Independent expected +/-30deg, unit axes and arbitrary origins above.
    check.verify_row(*fixture(tilted))


@pytest.mark.parametrize('damage',['side_swap','axis_sign','coordinate','clock','station_scale','reflection','nan_station','wrong_angle'])
def test_adversarial_pose_corruptions(damage):
    s,p,q=fixture(True)
    if damage=='side_swap':
        for a in 'xyz':p['femur_r_axis_ground_'+a]=p['femur_l_axis_ground_'+a]
    elif damage=='axis_sign':p['calcn_l_axis_ground_z']*=-1
    elif damage=='coordinate':s['coordinate_pelvis_tx']=1.
    elif damage=='clock':p['source_time_s']=.01
    elif damage=='station_scale':s['tibia_r_station1_z']+=.1
    elif damage=='reflection':
        for a in 'xyz':s['tibia_l_station3_'+a]=2*s['tibia_l_station0_'+a]-s['tibia_l_station3_'+a]
    elif damage=='nan_station':s['pelvis_station0_x']=float('nan')
    else:p['femur_r_projected_angle_rad']=-math.pi/6
    with pytest.raises(ValueError):check.verify_row(s,p,q)


def test_out_of_plane_axis_missing_projection():
    s,p,q=fixture()
    # Right foot points ground -Z, orthogonal to ground X/Y sagittal plane.
    origin=[s['calcn_r_station0_'+a] for a in 'xyz']
    for point,delta in enumerate(((0,0,0),(0,0,-1),(0,1,0),(1,0,0))):
        for a,o,v in zip('xyz',origin,delta):s[f'calcn_r_station{point}_{a}']=o+v
    for a,v in zip('xyz',(0,0,-1)):p['calcn_r_axis_ground_'+a]=v
    p['calcn_r_projected_angle_rad']=float('nan');check.verify_row(s,p,q)
    p['calcn_r_projected_angle_rad']=0.
    with pytest.raises(ValueError,match='Degenerate'):check.verify_row(s,p,q)


def source_file(tmp_path,degree='yes'):
    path=tmp_path/'synthetic.mot'
    q=[0.]*23;q[0]=180.;q[3]=2.
    path.write_text('inDegrees='+degree+'\nendheader\n'+' '.join(('time',)+check.COORDINATES)+'\n'+'\n'.join(' '.join(map(str,[t]+q)) for t in (0.,.01))+'\n')
    return path


def test_source_degrees_and_translation_not_double_scaled(tmp_path):
    rows=list(check.source_rows(source_file(tmp_path),0.,.01))
    assert len(rows)==2 and rows[0][1][0]==math.pi and rows[0][1][3]==2.
    with pytest.raises(ValueError,match='units'):list(check.source_rows(source_file(tmp_path,'unknown'),0.,.01))


def test_exact_source_output_coverage(tmp_path):
    raw=source_file(tmp_path);rows=list(check.source_rows(raw,0.,.01));station=[];pose=[]
    for t,q in rows:
        s,p,_=fixture();s['source_time_s']=p['source_time_s']=t
        s.update({'coordinate_'+c:v for c,v in zip(check.COORDINATES,q)});station.append(s);pose.append(p)
    def save(name,columns,records):
        path=tmp_path/name
        with path.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(records)
        return path
    sp=save('stations.csv',check.STATION_COLUMNS,station);pp=save('pose.csv',check.POSE_COLUMNS,pose)
    assert check.verify_files(sp,pp,raw,0.,.01)==2
    save('stations.csv',check.STATION_COLUMNS,station[:1])
    with pytest.raises(ValueError,match='coverage'):check.verify_files(sp,pp,raw,0.,.01)


def test_xml_units_policy_rejects_unreviewed_coordinate(tmp_path):
    from xml.etree.ElementTree import Element,SubElement,tostring
    root=Element('OpenSimDocument');objects=SubElement(SubElement(SubElement(root,'Model'),'JointSet'),'objects')
    joint=SubElement(objects,'CustomJoint');cs=SubElement(joint,'coordinates')
    for c in check.COORDINATES:SubElement(cs,'Coordinate',name=c)
    st=SubElement(joint,'SpatialTransform')
    for i in range(6):
        a=SubElement(st,'TransformAxis');SubElement(a,'coordinates').text=' '.join(c for c in check.COORDINATES if (c in check.TRANSLATIONS)==(i>=3))
    path=tmp_path/'synthetic.osim';path.write_bytes(tostring(root))
    policy=coordinate_policy(path);assert policy[3:6]==[False]*3 and sum(policy)==20
    cs[0].set('name','unknown');path.write_bytes(tostring(root))
    with pytest.raises(ValueError,match='coordinate'):coordinate_policy(path)


def audit_fixture(tmp_path,monkeypatch):
    import json
    from pathlib import Path
    from contributor_tools import audit_mblue_orientation_pose_pilot as prior
    # Mock only Windows-to-WSL path conversion for temporary synthetic files.
    monkeypatch.setattr(prior,'linux',Path)
    old=tmp_path/'pilot';old.mkdir();new=tmp_path/'station';new.mkdir()
    raw=source_file(tmp_path);records=[];poses=[]
    for t,q in check.source_rows(raw,0.,.01):
        s,p,_=fixture();s['source_time_s']=p['source_time_s']=t
        s.update({'coordinate_'+c:v for c,v in zip(check.COORDINATES,q)});records.append(s);poses.append(p)
    for path,columns,rows in ((old/'body_axes.csv',check.POSE_COLUMNS,poses),(new/'stations.csv',check.STATION_COLUMNS,records)):
        with path.open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader();writer.writerows(rows)
    def write(path,value):path.write_text(json.dumps(value));return path
    for root,name in ((old,'body_axes.csv'),(new,'stations.csv')):
        write(root/'options.json',{'output_path':str(root/name),'ik_path':str(raw),'start_s':0.,'end_s':.01})
        write(root/'native_status.json',{'status':'completed','exit_code':0,'options':str(root/'options.json'),
              'pid':123,'memory_limit_mib':2048,'timeout_seconds':300,'started_utc':'2026-10-21T00:00:00Z','finished_utc':'2026-10-21T00:00:01Z'})
    original=write(old/'plan.json',{'inputs_sha256':{str(old/'options.json'):check.digest(old/'options.json')}})
    paths=[raw,original,old/'options.json',new/'options.json',Path(check.__file__).resolve(),Path(prior.__file__).resolve(),Path(prior.__file__).with_name('prepare_mblue_orientation_pose_pilot.py').resolve()]
    plan=write(new/'plan.json',{'status':'prepared_not_executed','scientific_approval':False,'inputs_sha256':{str(p):check.digest(p) for p in paths},
      'pilot_plan':str(original),'pilot_options':str(old/'options.json'),'pilot_status':str(old/'native_status.json'),'pilot_output':str(old/'body_axes.csv'),
      'source_ik':str(raw),'start_s':0.,'end_s':.01})
    return plan,old,new,raw


def test_complete_metadata_receipt_and_immutable_audit(tmp_path,monkeypatch):
    plan,old,new,raw=audit_fixture(tmp_path,monkeypatch)
    result=check.audit(plan)
    assert result['rows']==2 and result['scientific_approval'] is False
    assert check.digest(raw)==result['inputs_sha256'][str(raw)]
    assert len(result['outputs_sha256'])==4
    with pytest.raises(FileExistsError):check.audit(plan)


@pytest.mark.parametrize('damage',['unfinished','no_finish','wrong_options','source_changed','missing_helper','pilot_binding','wrong_output_path'])
def test_end_to_end_provenance_rejections(tmp_path,monkeypatch,damage):
    import json
    plan,old,new,raw=audit_fixture(tmp_path,monkeypatch)
    if damage=='source_changed':raw.write_text(raw.read_text()+'0.02 0\n')
    elif damage in ('unfinished','no_finish','wrong_options'):
        path=new/'native_status.json';s=json.loads(path.read_text())
        if damage=='unfinished':s['status']='running'
        elif damage=='no_finish':del s['finished_utc']
        else:s['options']=str(old/'options.json')
        path.write_text(json.dumps(s))
    else:
        p=json.loads(plan.read_text())
        if damage=='missing_helper':
            key=next(k for k in p['inputs_sha256'] if k.endswith('prepare_mblue_orientation_pose_pilot.py'));del p['inputs_sha256'][key]
        elif damage=='pilot_binding':
            path=old/'plan.json';source=json.loads(path.read_text());source['inputs_sha256'][str(old/'options.json')]='0'*64
            path.write_text(json.dumps(source));p['inputs_sha256'][str(path)]=check.digest(path)
        else:p['pilot_output']=str(new/'stations.csv')
        plan.write_text(json.dumps(p))
    with pytest.raises(ValueError):check.audit(plan)


def test_isolated_guard_enforces_two_gib_reserve():
    from contributor_tools.prepare_mblue_station_check import isolated_guard,ROOT
    original=(ROOT/'contributor_tools/run_matlab_recording_guarded.ps1').read_text()
    changed=isolated_guard(original)
    assert '-lt 2048MB' in changed and '-lt 1536MB' not in changed
    assert 'mblue_station_pose_check(options)' in changed
    with pytest.raises(ValueError):isolated_guard(changed)
