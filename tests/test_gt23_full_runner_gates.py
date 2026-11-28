"""Adversarial orchestration fixtures, no native or original data execution."""
import json
from pathlib import Path
from types import SimpleNamespace
import time
import pytest
from contributor_tools import rebuild_gt23_full_source as m


def test_binding_merge_canonical_conflict(tmp_path):
    p=tmp_path/'same'
    assert len(m.merge_bindings({str(p):'a'},{str(tmp_path/'x/../same'):'a'}))==1
    with pytest.raises(ValueError,match='Conflicting'):m.merge_bindings({str(p):'a'},{str(tmp_path/'x/../same'):'b'})


def test_absent_or_unreviewed_actual_pilots_rejected():
    with pytest.raises(ValueError):m.reviewed_pilots({'decision':'prepared'})
    with pytest.raises(ValueError):m.reviewed_pilots({'decision':'approved_for_full_source_reconstruction','scientific_approval':False,'pilots':{}})


def test_single_record_disk_admission_not_entire_archive_requirement():
    record={'publisher_files':[{'uncompressed_size':100}]*10}
    assert m.admit_record_disk(record,2000,500)==1520
    with pytest.raises(MemoryError):m.admit_record_disk(record,1519,500)


def test_exact_original_membership_no_missing_hash_fallback():
    names=['Joint_Angle.csv','Joint_Velocities.csv','Joint_Moments.csv','GroundFrame_GRFs.csv']
    e={'csv_files':{n:{'source':'/synthetic/'+n,'source_sha256':'hash'} for n in names}}
    c={'files':[{'source_path':'/synthetic/'+n,'source_sha256':'hash'} for n in names]}
    m.verify_original_membership(e,c);c['files'].pop()
    with pytest.raises(ValueError,match='exact'):m.verify_original_membership(e,c)


def runtime(tmp_path):
    r=m.Runtime.__new__(m.Runtime);r.out=tmp_path;r.plan={'bindings':{},'limits':{'total_deadline_h':1}};r.started=time.monotonic();r.last=0
    r.plan_path=tmp_path/'plan.json';r.plan_path.write_text('{}');r.plan_sha=m.digest(r.plan_path)
    identities={402226:{'start':'24607869','state':'T','cmd':'python contributor_tools/run_gt21_with_memory_wait.py'},402224:{'start':'24607849','state':'T','cmd':'python metadata_serial_queue_20261021/run_queue.py'}}
    r.owned=SimpleNamespace(process=lambda p:identities.get(p),descendants=lambda _: {})
    return r,identities


@pytest.mark.parametrize('damage',['plan','controller_identity','parent_running','STOP','deadline','controller_child'])
def test_continuous_hold_plan_and_stop_gates(tmp_path,damage):
    r,ids=runtime(tmp_path);r.stop_and_ownership()
    if damage=='plan':r.plan_path.write_text('changed')
    elif damage=='controller_identity':ids[402226]['start']='reused'
    elif damage=='parent_running':ids[402224]['state']='R'
    elif damage=='STOP':(tmp_path/'STOP').touch()
    elif damage=='deadline':r.started-=4000
    else:r.owned.descendants=lambda _:{7:{}}
    with pytest.raises((ValueError,RuntimeError,TimeoutError)):r.stop_and_ownership()


def test_stage_cleans_descendants_even_after_leader_success(tmp_path,monkeypatch):
    r,_=runtime(tmp_path);calls=[]
    r.resources=lambda *a,**k:None;r.verify_inputs=lambda:None
    r.owned=SimpleNamespace(process=lambda p:{'pid':p,'start':'owned'},descendants=lambda p:{88:{'pid':88}},cleanup=lambda child,owned:calls.append(('cleanup',child.pid)))
    child=SimpleNamespace(pid=77,returncode=0,poll=lambda:0)
    monkeypatch.setattr(m.subprocess,'Popen',lambda *a,**k:child)
    monkeypatch.setattr(m,'cleanup_linux',lambda child,owned,helper:calls.append(('cleanup',child.pid)))
    r.stage('mock',['synthetic'],tmp_path)
    assert calls==[('cleanup',77)]


def test_native_false_cleanup_proof_cannot_succeed(tmp_path,monkeypatch):
    r,_=runtime(tmp_path);r.resources=lambda *a,**k:None;r.verify_inputs=lambda:None
    r.owned=SimpleNamespace(process=lambda p:{'pid':p,'start':'owned'},descendants=lambda p:{},cleanup=lambda *a:None)
    r.cleanup=SimpleNamespace(await_cleanup=lambda *a,**k:{'safe_to_release':False})
    child=SimpleNamespace(pid=77,returncode=0,poll=lambda:0)
    monkeypatch.setattr(m.subprocess,'Popen',lambda *a,**k:child)
    monkeypatch.setattr(m,'cleanup_linux',lambda *a:None)
    with pytest.raises(RuntimeError,match='unresolved'):r.stage('native_mock',['synthetic'],tmp_path,intent={'synthetic':'ownership'})


def test_stage_signal_exception_still_cleans_owned_group(tmp_path,monkeypatch):
    r,_=runtime(tmp_path);calls=[];checks=0
    def resources(*a,**k):
        nonlocal checks
        checks+=1
        if checks>1:raise RuntimeError('Synthetic termination request')
    r.resources=resources;r.verify_inputs=lambda:None
    r.owned=SimpleNamespace(process=lambda p:{'pid':p,'start':'owned'},descendants=lambda p:{88:{'pid':88}},cleanup=lambda *a:calls.append('cleaned'))
    child=SimpleNamespace(pid=77,returncode=None,poll=lambda:None)
    monkeypatch.setattr(m.subprocess,'Popen',lambda *a,**k:child)
    monkeypatch.setattr(m,'cleanup_linux',lambda *a:calls.append('cleaned'))
    with pytest.raises(RuntimeError,match='termination'):r.stage('mock',['synthetic'],tmp_path)
    assert calls==['cleaned']


def test_final_ledger_rejects_pending_source_and_omitted_parsing(tmp_path):
    runtime=SimpleNamespace(guarded_digest=m.digest)
    scope={'records':[{'subject':'AB99','recording':'raw'}],'parsing_entries':[{'subject':'AB99','parsing':'task.mat'}]}
    ledger={'source_recordings':{'AB99/raw':{'status':'pending'}},'parsing_entries':{'AB99/task.mat':{'status':'pending'}}}
    with pytest.raises(ValueError,match='Incomplete'):m.verify_final_ledger(runtime,scope,ledger)
    ledger['parsing_entries']={}
    with pytest.raises(ValueError,match='scope'):m.verify_final_ledger(runtime,scope,ledger)


def test_false_pilot_scientific_approval_not_accepted():
    with pytest.raises(ValueError):m.reviewed_pilots({'decision':'approved_for_full_source_reconstruction','scientific_approval':True})


def test_capture_refuses_reused_leader_and_preserves_old_descendant_identity():
    child=SimpleNamespace(pid=1);owned={1:{'start':'old'},2:{'start':'old-child'}}
    rows={1:{'start':'reused'},2:{'start':'reused-child'},3:{'start':'new-child'}}
    helper=SimpleNamespace(process=lambda p:rows.get(p),descendants=lambda p:{k:v for k,v in rows.items() if k!=1})
    m.capture_owned(child,owned,helper);assert set(owned)=={1,2}
    rows[1]['start']='old';m.capture_owned(child,owned,helper)
    assert owned[2]['start']=='old-child' and owned[3]['start']=='new-child'


def test_windows_cleanup_attempted_even_when_linux_cleanup_raises(tmp_path,monkeypatch):
    r,_=runtime(tmp_path);r.resources=lambda *a,**k:None;r.verify_inputs=lambda:None;calls=[]
    r.owned=SimpleNamespace(process=lambda p:{'pid':p,'start':'owned'},descendants=lambda p:{})
    r.cleanup=SimpleNamespace(await_cleanup=lambda *a,**k:calls.append('Windows checked') or {'safe_to_release':True})
    child=SimpleNamespace(pid=77,returncode=0,poll=lambda:0)
    monkeypatch.setattr(m.subprocess,'Popen',lambda *a,**k:child)
    def bad_linux(*a):raise RuntimeError('synthetic Linux cleanup failure')
    monkeypatch.setattr(m,'cleanup_linux',bad_linux)
    with pytest.raises(RuntimeError,match='Linux'):r.stage('native_mock',['synthetic'],tmp_path,intent={'synthetic':'ownership'})
    assert calls==['Windows checked']


def persisted_ledger(tmp_path):
    """Tiny persisted byte companions; no scientific data or native APIs."""
    import gzip
    files=[];members=[]
    import zlib
    for i in range(10):
        target=tmp_path/f'channel{i}.csv.gz'
        target.write_bytes(gzip.compress(b'time,value\r\n0,-0\r\n',mtime=0))
        original=tmp_path/'RawData/AB99/CSV_Data/raw'/f'channel{i}.csv';original.parent.mkdir(parents=True,exist_ok=True);original.write_bytes(b'time,value\r\n0,-0\r\n')
        crc=zlib.crc32(original.read_bytes());size=original.stat().st_size
        members.append({'name':f'AB99/CSV_Data/raw/channel{i}.csv','crc32':crc,'uncompressed_size':size})
        files.append({'source_path':str(original),'source_sha256':m.digest(original),'lossless_readback_sha256':m.digest(original),'source_bytes':size,'publisher_crc32':crc,
                      'output_path':str(target),'output_sha256':m.digest(target)})
    source={'subject':'AB99','recording':'raw','files':files,
            'status':'all_ten_source_channels_losslessly_preserved_unreviewed','scientific_approval':False}
    record={'subject':'AB99','parsing':'task.mat','recording':'raw','has_intervals':False}
    parsed={'record':record.copy(),'status':'no_source_intervals_source_channels_preserved','scientific_approval':False}
    source_path=tmp_path/'source_readback.json';parsed_path=tmp_path/'record_readback.json'
    source_path.write_text(json.dumps(source));parsed_path.write_text(json.dumps(parsed))
    scope={'records':[{'subject':'AB99','recording':'raw','publisher_files':members}],'parsing_entries':[record]}
    ledger={'source_recordings':{'AB99/raw':{'status':source['status'],'receipt':str(source_path),'sha256':m.digest(source_path)}},
            'parsing_entries':{'AB99/task.mat':{'status':parsed['status'],'receipt':str(parsed_path),'sha256':m.digest(parsed_path)}}}
    return SimpleNamespace(guarded_digest=m.digest,plan={'source_root':str(tmp_path)}),scope,ledger,source,parsed


def test_persisted_final_ledger_counts_without_scientific_approval(tmp_path):
    runtime,scope,ledger,_,_=persisted_ledger(tmp_path)
    result=m.verify_final_ledger(runtime,scope,ledger)
    assert result['source_recordings_preserved']==1
    assert result['parsing_entries_accounted']==1
    assert result['scientific_gaps'] and result['deferred_or_empty_entries']


@pytest.mark.parametrize('damage',['source_receipt_bytes','source_identity','source_status','duplicate_channel',
                                   'companion_bytes','parsing_receipt_bytes','parsing_identity','recording_identity',
                                   'false_approval','missing_mode','output_bytes','foreign_channel','original_changed','wrong_crc','wrong_size'])
def test_persisted_final_ledger_tamper_and_swapped_identity(tmp_path,damage):
    runtime,scope,ledger,source,parsed=persisted_ledger(tmp_path)
    si=ledger['source_recordings']['AB99/raw'];pi=ledger['parsing_entries']['AB99/task.mat']
    if damage=='source_receipt_bytes':Path(si['receipt']).write_text('{}')
    elif damage=='companion_bytes':Path(source['files'][0]['output_path']).write_bytes(b'corrupt')
    elif damage=='original_changed':Path(source['files'][0]['source_path']).write_bytes(b'new source')
    elif damage=='parsing_receipt_bytes':Path(pi['receipt']).write_text('{}')
    else:
        if damage=='foreign_channel':source['files'][0]['source_path']=str(tmp_path/'foreign.csv')
        elif damage=='wrong_crc':source['files'][0]['publisher_crc32']+=1
        elif damage=='wrong_size':source['files'][0]['source_bytes']+=1
        elif damage=='source_identity':source['recording']='different'
        elif damage=='source_status':source['status']='pending'
        elif damage=='duplicate_channel':source['files'][-1]=source['files'][0].copy()
        elif damage=='parsing_identity':parsed['record']['parsing']='different.mat'
        elif damage=='recording_identity':parsed['record']['recording']='different'
        elif damage=='false_approval':parsed['scientific_approval']=True
        elif damage in ('missing_mode','output_bytes'):
            output=tmp_path/'synthetic_output';output.write_bytes(b'original')
            row={'output':str(output),'sha256':m.digest(output),
                 'source_readback':{'status':'publisher_normalization_raw_source_checked_unreviewed'}}
            parsed['status']='both_modes_source_checked_canonical_anatomy_unavailable'
            parsed['modes']={'time':row,'phase':row.copy()};pi['status']=parsed['status']
            if damage=='missing_mode':del parsed['modes']['phase']
            else:output.write_bytes(b'changed')
        # Even self-consistent rewritten hashes cannot legitimize a swapped identity.
        Path(si['receipt']).write_text(json.dumps(source));si['sha256']=m.digest(si['receipt'])
        Path(pi['receipt']).write_text(json.dumps(parsed));pi['sha256']=m.digest(pi['receipt'])
    with pytest.raises(ValueError):m.verify_final_ledger(runtime,scope,ledger)


@pytest.mark.parametrize('damage',[None,'status','approval','participant','rows','disposition','disposition_approval','original_output','binding','audit_receipt','audit_plan','kin_status','kin_approval','kin_recording','kin_plan','kin_report'])
def test_persisted_nested_audit_closure(tmp_path,damage):
    runtime,scope,ledger,source,parsed=persisted_ledger(tmp_path)
    modes={}
    for mode in ('time','phase'):
        folder=tmp_path/mode;folder.mkdir()
        original=folder/'normalized';original.write_bytes(b'synthetic normalized')
        output=folder/'withheld';output.write_bytes(b'synthetic withheld')
        plan={'mode':mode,'expected_rows':150,'parquet':str(original),'bindings':{str(original):m.digest(original)}}
        planpath=folder/'plan.json';planpath.write_text(json.dumps(plan))
        audit={'status':'publisher_normalization_raw_source_checked_unreviewed','scientific_approval':False,'participant':'AB99','rows_checked':150,'plan_sha256':m.digest(planpath),'bindings':plan['bindings']}
        disposition={'status':'source_interpretations_preserved_canonical_anatomy_unavailable','scientific_approval':False,'rows':150}
        if mode=='time':
            if damage=='status':audit['status']='invented_pass'
            elif damage=='approval':audit['scientific_approval']=True
            elif damage=='participant':audit['participant']='AB01'
            elif damage=='rows':disposition['rows']=149
            elif damage=='disposition':disposition['status']='other'
            elif damage=='disposition_approval':disposition['scientific_approval']=True
            elif damage=='original_output':original.write_bytes(b'changed')
            elif damage=='binding':audit['bindings']={}
        ap=folder/'audit.json';ap.write_text(json.dumps(audit))
        modes[mode]={'output':str(output),'sha256':m.digest(output),'source_readback':audit,'source_readback_path':str(ap),'source_readback_sha256':m.digest(ap),'audit_plan':str(planpath),'anatomy_disposition':disposition}
        kp=folder/'kinplan.json';kp.write_text(json.dumps(plan))
        kr={'status':'supplied_raw_kinematics_producer_recipe_checked_unreviewed','scientific_approval':False,'anatomical_approval':False,'physical_source_participant':'AB99','source_recording':'raw','rows_checked':150,'plan_sha256':m.digest(kp),'bindings':plan['bindings'],'output_sha256':m.digest(original)}
        if mode=='time':
            if damage=='kin_status':kr['status']='invented_pass'
            elif damage=='kin_approval':kr['anatomical_approval']=True
            elif damage=='kin_recording':kr['source_recording']='foreign'
        krp=folder/'kinreport.json';krp.write_text(json.dumps(kr))
        modes[mode].update(kinematics_plan=str(kp),kinematics_readback_path=str(krp),kinematics_readback_sha256=m.digest(krp))
        if mode=='time' and damage=='kin_plan':kp.write_text('{}')
        if mode=='time' and damage=='kin_report':krp.write_text('{}')
        if mode=='time' and damage=='audit_receipt':ap.write_text('{}')
        if mode=='time' and damage=='audit_plan':planpath.write_text('{}')
    parsed.update(status='both_modes_source_checked_canonical_anatomy_unavailable',modes=modes)
    item=ledger['parsing_entries']['AB99/task.mat'];item['status']=parsed['status']
    Path(item['receipt']).write_text(json.dumps(parsed));item['sha256']=m.digest(item['receipt'])
    if damage is None:assert m.verify_final_ledger(runtime,scope,ledger)['parsing_entries_accounted']==1
    else:
        with pytest.raises(ValueError):m.verify_final_ledger(runtime,scope,ledger)
