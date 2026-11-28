"""Tiny synthetic ZIP/member fixtures only."""
import hashlib,json,zipfile,zlib
from pathlib import Path
import pytest
from contributor_tools import prepare_gt21_ab17_restoration as m


def fixture(tmp_path):
 name='AB17/date/levelground/ik/trial.mat';data=b'synthetic bytes'
 info=zipfile.ZipInfo(name);info.file_size=len(data);info.CRC=zlib.crc32(data)
 path=tmp_path/'files'/name;path.parent.mkdir(parents=True);path.write_bytes(data)
 row={'member':name,'bytes':len(data),'crc32':f'{info.CRC:08x}','sha256':hashlib.sha256(data).hexdigest()}
 (tmp_path/'member_manifest.jsonl').write_text(json.dumps(row)+'\n')
 return info,path,row


def test_independent_bytes_readback(tmp_path):
 info,path,row=fixture(tmp_path)
 r=m.persisted_readback(tmp_path,[info]);assert r['files']==1 and r['scientific_approval'] is False
 path.write_bytes(b'changed bytes!!')
 with pytest.raises(ValueError,match='Persisted bytes'):m.persisted_readback(tmp_path,[info])


@pytest.mark.parametrize('fault',['duplicate','missing','extra'])
def test_exact_manifest_scope(tmp_path,fault):
 info,path,row=fixture(tmp_path);manifest=tmp_path/'member_manifest.jsonl'
 if fault=='duplicate':manifest.write_text((json.dumps(row)+'\n')*2)
 elif fault=='missing':manifest.write_text('')
 else:(tmp_path/'files'/'unlisted').write_bytes(b'extra')
 with pytest.raises(ValueError):m.persisted_readback(tmp_path,[info])


def test_readback_obeys_stop(tmp_path):
 info,_,_=fixture(tmp_path)
 def stop():raise RuntimeError('stop')
 with pytest.raises(RuntimeError):m.persisted_readback(tmp_path,[info],stop)


def test_inventory_does_not_invent_offset_or_mass():
 infos=[zipfile.ZipInfo('AB17/date/levelground/'+c+'/trial.mat') for c in ('ik','id','gcLeft','gcRight','conditions','fp')]+[zipfile.ZipInfo('AB17/date/osimxml/AB17.osim')]
 for info in infos:info.CRC=0
 records,other=m.inventory(infos)
 assert len(records)==1 and 'ik_offset' not in records[0]['channels']
 assert other[0]['member'].endswith('AB17.osim')


def test_capture_refuses_reused_owned_pid(monkeypatch):
 owned={2:{'start':'old','fd':9}}
 with pytest.raises(RuntimeError,match='reused'):m.capture_tree(1,owned,{2:{'parent':1,'start':'new'}})
 assert owned[2]['start']=='old'


def test_capture_checks_identity_after_pidfd(monkeypatch):
 closed=[];monkeypatch.setattr(m.os,'pidfd_open',lambda pid:9);monkeypatch.setattr(m.os,'close',closed.append)
 before={1:{'parent':0,'start':'guard'},2:{'parent':1,'start':'old'}}
 after={1:before[1],2:{'parent':1,'start':'new'}}
 snapshots=iter([before,after]);monkeypatch.setattr(m,'process_rows',lambda:next(snapshots))
 with pytest.raises(RuntimeError,match='Ancestry changed'):m.capture_tree(1,{},before)
 assert closed==[9]


def test_subreaper_cleanup_kills_reparented_child(monkeypatch):
 from types import SimpleNamespace
 owned={2:{'start':'a','fd':9}};calls=[]
 def capture(parent,items):items[3]={'start':'b','fd':10}
 monkeypatch.setattr(m,'capture_tree',capture);monkeypatch.setattr(m,'send_owned',lambda i,s:calls.append((i['fd'],s)))
 def reaped(*args):raise ChildProcessError()
 monkeypatch.setattr(m.os,'waitpid',reaped)
 m.cleanup_owned(SimpleNamespace(pid=2,wait=lambda timeout:None),owned)
 assert (10,m.signal.SIGKILL) in calls


def test_archive_mutation_after_persisted_readback_blocks_receipt(tmp_path,monkeypatch):
 import io
 archive=tmp_path/'archive.zip'
 with zipfile.ZipFile(archive,'w') as z:z.writestr('AB17/x',b'fixture')
 expected=m.inspect.digest(archive)
 plan={'bindings':{},'extraction':{'archive':str(archive),'archive_sha256':expected,'output_root':str(tmp_path/'output')}}
 path=tmp_path/'plan.json';path.write_text(json.dumps(plan));sha=m.inspect.digest(path)
 monkeypatch.setattr(m.extract,'extract',lambda *a,**k:{})
 def readback(*args):
  archive.write_bytes(b'changed')
  return {}
 monkeypatch.setattr(m,'persisted_readback',readback)
 with pytest.raises(ValueError,match='Archive changed'):m.worker(path,sha)
 assert not (tmp_path/'independent_extraction_receipt.json').exists()


@pytest.mark.parametrize('mutation',[None,'source','manifest','code'])
def test_schema_units_and_final_closure(tmp_path,monkeypatch,mutation):
 import sys,types
 monkeypatch.setattr(m.resource,'setrlimit',lambda *a:None)
 root=tmp_path/'output';files=root/'files';files.mkdir(parents=True)
 channels={};rows=[]
 for kind in ('ik','id','fp','gcLeft','gcRight'):
  p=files/(kind+'.mat');p.write_bytes(kind.encode());channels[kind]={'member':p.name}
  rows.append({'member':p.name,'sha256':m.inspect.digest(p)})
 manifest=root/'member_manifest.jsonl';manifest.write_text(''.join(json.dumps(r)+'\n' for r in rows))
 code=tmp_path/'bound.py';code.write_text('fixture')
 record={'subject':'AB17','date':'synthetic','mode':'levelground','recording':'fixture','channels':channels}
 plan={'extraction':{'output_root':str(root)},'bindings':{str(code):m.inspect.digest(code)},'schema_pilot_candidates':[record]}
 path=tmp_path/'plan.json';path.write_text(json.dumps(plan));sha=m.inspect.digest(path)
 (tmp_path/'independent_extraction_receipt.json').write_text(json.dumps({'status':'all_extracted_bytes_independently_reread_unreviewed','plan_sha256':sha,'manifest_sha256':m.inspect.digest(manifest)}))
 count=[0]
 def reader(*args,**kwargs):
  count[0]+=1
  if count[0]==5 and mutation:
   target={'source':files/'ik.mat','manifest':manifest,'code':code}[mutation];target.write_bytes(b'changed')
  return {'Header':[1.,2.,3.]}
 monkeypatch.setitem(sys.modules,'contributor_tools.gt21_numeric_source',types.SimpleNamespace(read_numeric_table=reader))
 if mutation:
  with pytest.raises(ValueError):m.schema_worker(path,sha)
  assert not (tmp_path/'schema_pilot.json').exists()
 else:
  m.schema_worker(path,sha);r=json.loads((tmp_path/'schema_pilot.json').read_text());c=r['records'][0]['channels']['ik']
  assert c['source_header_first']==1 and c['clock_units']=='unverified' and 'first_s' not in c


def test_reused_ancestor_never_adopts_unrelated_children(monkeypatch):
 owned={2:{'start':'original','fd':9}};adopted=[]
 monkeypatch.setattr(m.os,'pidfd_open',lambda pid:adopted.append(pid))
 rows={1:{'parent':0,'start':'guard'},2:{'parent':1,'start':'reused'},3:{'parent':2,'start':'unrelated'}}
 with pytest.raises(RuntimeError,match='reused'):m.capture_tree(1,owned,rows)
 assert adopted==[] and set(owned)=={2}


def test_spawn_cancellation_deferred_until_ownership(monkeypatch):
 import ctypes,types
 from contributor_tools import run_gt25_coverage_pilot as limits
 events=[];handlers={};child=types.SimpleNamespace(pid=22)
 monkeypatch.setattr(ctypes,'CDLL',lambda *a,**k:types.SimpleNamespace(prctl=lambda *a:0))
 monkeypatch.setattr(limits,'windows_available_mib',lambda:10000);monkeypatch.setattr(limits,'linux_available_mib',lambda:10000)
 monkeypatch.setattr(m.signal,'signal',lambda sig,handler:handlers.setdefault(sig,handler))
 def mask(mode,signals):
  events.append('block' if mode==m.signal.SIG_BLOCK else 'unblock')
  if mode==m.signal.SIG_SETMASK:raise RuntimeError('pending cancellation')
  return set()
 monkeypatch.setattr(m.signal,'pthread_sigmask',mask)
 def spawn(*a,**k):
  assert events[-1]=='block';events.append('spawn');return child
 monkeypatch.setattr(m.subprocess,'Popen',spawn)
 def capture(parent,owned):events.append('owned');owned[22]={'start':'fixture','fd':9}
 monkeypatch.setattr(m,'capture_tree',capture)
 monkeypatch.setattr(m,'cleanup_owned',lambda c,o:events.append('cleanup') if c is child and 22 in o else pytest.fail('lost ownership'))
 monkeypatch.setattr(m.os,'close',lambda fd:None)
 with pytest.raises(RuntimeError,match='pending cancellation'):m.supervised(['synthetic'],None,lambda:None,1)
 assert events==['block','spawn','owned','unblock','cleanup']
