import json
from pathlib import Path
import pytest
from contributor_tools import reconcile_mblue_fileinfo_handoff as tool


def write(path,value):path.write_text(json.dumps(value))


def fixture(tmp_path,monkeypatch):
    monkeypatch.setattr(tool,'windows',lambda p:str(p))
    old=tmp_path/'old';old.mkdir();native=tmp_path/'native';native.mkdir()
    source=tmp_path/'AB01_FileInfo.mat';source.write_text('synthetic metadata')
    sources=[{'subject':'AB01','path':str(source),'sha256':tool.digest(source),'tasks':[['bare','STS']]}]
    write(old/'plan.json',{'sources':sources,'rebuild_sha256':'synthetic-rebuild'})
    upstream=tmp_path/'upstream.json';write(upstream,{'status':'finished_unreviewed'})
    queue=tmp_path/'old_queue_plan.json';write(queue,{'prerequisite_summary':str(upstream),'prerequisite_status':'finished_unreviewed','jobs':[{'name':'mblue_fileinfo_metadata','output':str(old),'code_sha256':{str(old/'plan.json'):tool.digest(old/'plan.json')}}]})
    state=tmp_path/'old_queue_status.json';write(state,{'pid':999999,'status':'stopped_incomplete','scientific_approval':False,'reason':'MCOS decode failure'})
    plan=native/'plan.json';bindings={str(source):tool.digest(source)}
    write(plan,{'sources':sources,'rebuild_sha256':'synthetic-rebuild','bindings':bindings})
    raw=native/'native_metadata.json';payload={'subjects':{'AB01':{'subject':'AB01','date':'08162024','bare':{'STS':{'vicon_filename':'trial'}}}}};write(raw,payload)
    status=native/'native_status.json';write(status,{'status':'completed','exit_code':0,'options':str(native/'options.json')})
    write(native/'fileinfo_metadata.json',{'status':'fileinfo_metadata_exported_unreviewed','scientific_approval':False,'plan_sha256':tool.digest(plan),'rebuild_sha256':'synthetic-rebuild','bindings':{**bindings,str(plan):tool.digest(plan)},'native_evidence':{str(raw):tool.digest(raw),str(status):tool.digest(status)},'subjects':tool.validate_payload(payload,sources)})
    return [queue,state,plan,tmp_path/'handoff']


def test_success_preserves_failure_and_metadata(tmp_path,monkeypatch):
    args=fixture(tmp_path,monkeypatch);before=args[1].read_bytes()
    result=tool.reconcile(*args,alive=lambda pid:False)
    assert result['status']=='finished_unreviewed' and result['scientific_approval'] is False
    assert result['superseded_queue_status']['status']=='stopped_incomplete'
    assert args[1].read_bytes()==before
    assert result['jobs'][0]['summary_sha256']==tool.digest(args[2].parent/'fileinfo_metadata.json')
    with pytest.raises(FileExistsError):tool.reconcile(*args,alive=lambda pid:False)


def test_live_predecessor_refused(tmp_path,monkeypatch):
    args=fixture(tmp_path,monkeypatch)
    with pytest.raises(ValueError,match='PID'):tool.reconcile(*args,alive=lambda pid:True)


@pytest.mark.parametrize('change',['upstream','native_status','source','scope','subjects','approval'])
def test_bad_evidence_refused(tmp_path,monkeypatch,change):
    args=fixture(tmp_path,monkeypatch);native=args[2].parent
    if change=='upstream':write(tmp_path/'upstream.json',{'status':'stopped_incomplete'})
    elif change=='native_status':write(native/'native_status.json',{'status':'failed'})
    elif change=='source':(tmp_path/'AB01_FileInfo.mat').write_text('changed')
    elif change=='scope':
        p=json.loads(args[2].read_text());p['sources'][0]['tasks']=[['bare','crouch']];write(args[2],p)
    else:
        p=native/'fileinfo_metadata.json';r=json.loads(p.read_text())
        if change=='subjects':r['subjects']['AB01']['date']='01012000'
        else:r['scientific_approval']=True
        write(p,r)
    with pytest.raises(ValueError):tool.reconcile(*args,alive=lambda pid:False)
    assert not args[3].exists()


def test_retained_dead_worker_provenance_allowed(tmp_path,monkeypatch):
    args=fixture(tmp_path,monkeypatch);state=json.loads(args[1].read_text());state['worker_pid']=999998;write(args[1],state)
    result=tool.reconcile(*args,alive=lambda pid:False)
    assert result['superseded_queue_status']['worker_pid']==999998


def test_retained_live_worker_refused(tmp_path,monkeypatch):
    args=fixture(tmp_path,monkeypatch);state=json.loads(args[1].read_text());state['worker_pid']=999998;write(args[1],state)
    with pytest.raises(ValueError,match='worker'):tool.reconcile(*args,alive=lambda pid:pid==999998)
