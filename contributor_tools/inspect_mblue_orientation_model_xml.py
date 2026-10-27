"""Bounded XML-only evidence for MBLUE body-axis proposals; no pose evaluation."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

BODIES=('pelvis','femur_r','tibia_r','calcn_r','femur_l','tibia_l','calcn_l')

def bounded_bytes(path, limit):
    with Path(path).open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise MemoryError("Source exceeds bounded admission")
    return raw

def read_model(path):
    path=Path(path)
    if path.stat().st_size>2*1024**2:raise MemoryError('Model XML exceeds 2 MiB admission')
    raw=bounded_bytes(path,2*1024**2);tree=ET.fromstring(raw);model=tree.find('Model')
    if model is None:raise ValueError('Missing OpenSim Model')
    body_names=[b.get('name') for b in model.findall('./BodySet/objects/Body')]
    if len(body_names)!=len(set(body_names)) or not set(BODIES)<=set(body_names):raise ValueError('Missing or duplicate model bodies')
    coordinates={}
    for node in model.findall('.//Coordinate'):
        name=node.get('name')
        if name in coordinates:raise ValueError('Duplicate model coordinate')
        coordinates[name]={k:node.findtext(k) for k in ('default_value','default_speed_value','range','locked','prescribed','clamped')}
    joints={}
    for node in model.findall('./JointSet/objects/*'):
        name=node.get('name')
        if name in joints:raise ValueError('Duplicate model joint')
        frames=[{'name':f.get('name'),'parent':f.findtext('socket_parent'),'translation':f.findtext('translation'),'orientation':f.findtext('orientation')} for f in node.findall('./frames/PhysicalOffsetFrame')]
        axes=[]
        for axis in node.findall('./SpatialTransform/TransformAxis'):
            functions=[f for f in axis if f.tag not in ('coordinates','axis')]
            axes.append({'name':axis.get('name'),'coordinates':axis.findtext('coordinates'),'axis':axis.findtext('axis'),'function_types':[f.tag for f in functions],'function_xml_sha256':hashlib.sha256(b''.join(ET.tostring(f) for f in functions)).hexdigest(),'contains_spline':any(f.find('.//SimmSpline') is not None or f.tag=='SimmSpline' for f in functions)})
        joints[name]={'type':node.tag,'socket_parent_frame':node.findtext('socket_parent_frame'),'socket_child_frame':node.findtext('socket_child_frame'),'frames':frames,'transform_axes':axes}
    markers={}
    for marker in model.findall('./MarkerSet/objects/Marker'):
        name=marker.get('name')
        if name in markers:raise ValueError('Duplicate model marker')
        if name and any(s in name for s in ('HEEL','MET1','MET3','MET5','ANKLAT','ANKMED','KNEELAT','KNEEMED')):
            markers[name]={'parent':marker.findtext('socket_parent_frame'),'location':marker.findtext('location')}
    return {'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'length_units':model.findtext('length_units'),'force_units':model.findtext('force_units'),'gravity':model.findtext('gravity'),'bodies':body_names,'coordinates':coordinates,'joints':joints,'landmarks':markers,'interpretation':'Literal XML evidence only. No anatomical axis, coordinate sign, joint-center line or neutral offset inferred.'}


def census(availability):
    result=[];seen=set()
    for record in availability['records']:
        for model in record['models']:
            if model['path'] in seen:raise ValueError('Duplicate inventoried model path')
            seen.add(model['path']);evidence=read_model(model['path'])
            if evidence['sha256']!=model['sha256']:raise ValueError('Model changed since original source census')
            evidence.update(subject=record['subject'],date=record['date']);result.append(evidence)
    return {'status':'literal_model_XML_evidence_not_pose_or_anatomical_validation','scientific_approval':False,'model_count':len(result),'subjects':sorted({r['subject'] for r in result}),'records':result}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--availability',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError('Preserve prior evidence')
    data=bounded_bytes(a.availability,4*1024**2)
    if len(data)>4*1024**2:raise MemoryError('Inventory admission exceeded')
    result=census(json.loads(data));result['inventory_sha256']=hashlib.sha256(data).hexdigest()
    with a.output.open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps({k:result[k] for k in ('status','model_count','subjects')}))
