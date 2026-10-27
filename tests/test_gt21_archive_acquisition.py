"""Synthetic byte streams only; no network or research archive loads."""
import hashlib
import io
import pytest
from contributor_tools.acquire_gt21_missing_participant import copy_verified


def test_exact_archive_bytes_and_hash():
    data=b'synthetic publisher archive';out=io.BytesIO();remaining=[]
    assert copy_verified(io.BytesIO(data),out,len(data),hashlib.sha256(data).hexdigest(),remaining.append,rate=0)==len(data)
    assert out.getvalue()==data
    assert remaining[-1]==0


@pytest.mark.parametrize('data,size,sha',[(b'abc',2,hashlib.sha256(b'ab').hexdigest()),(b'ab',3,hashlib.sha256(b'abc').hexdigest()),(b'abc',3,'0'*64)])
def test_size_or_hash_mismatch_refused(data,size,sha):
    with pytest.raises(ValueError):copy_verified(io.BytesIO(data),io.BytesIO(),size,sha,lambda _:None,rate=0)


def test_guard_prevents_first_write():
    output=io.BytesIO()
    def guard(_):raise MemoryError('reserve')
    with pytest.raises(MemoryError):copy_verified(io.BytesIO(b'abc'),output,3,'0'*64,guard,rate=0)
    assert output.getvalue()==b''


def test_rate_limit_waits_for_each_buffer(monkeypatch):
    from contributor_tools import acquire_gt21_missing_participant as tool
    clock=[0.0];sleeps=[]
    monkeypatch.setattr(tool,'BUFFER',8)
    monkeypatch.setattr(tool.time,'monotonic',lambda:clock[0])
    def sleep(seconds):
        sleeps.append(seconds);clock[0]+=seconds
    monkeypatch.setattr(tool.time,'sleep',sleep)
    data=b'x'*24
    assert tool.copy_verified(io.BytesIO(data),io.BytesIO(),24,hashlib.sha256(data).hexdigest(),lambda _:None,rate=8)==24
    assert sleeps==[1,1,1]
    assert clock[0]==3


def test_elapsed_deadline_stops_before_read(monkeypatch):
    from contributor_tools import acquire_gt21_missing_participant as tool
    ticks=iter([0.0,2701.0])
    monkeypatch.setattr(tool.time,'monotonic',lambda:next(ticks))
    stream=io.BytesIO(b'abc');out=io.BytesIO()
    with pytest.raises(TimeoutError):tool.copy_verified(stream,out,3,'0'*64,lambda _:None)
    assert stream.tell()==0 and out.getvalue()==b''


def test_prepare_binds_exact_ledger_and_tool_without_network(tmp_path,monkeypatch):
    import json
    from pathlib import Path
    from contributor_tools import acquire_gt21_missing_participant as tool
    ledger=tmp_path/'synthetic.json'
    archive={'status':'COMPLETED','doi':'10.synthetic/fixture.1','sha256_hash':'a'*64,'size':3}
    record={'subject':'AB17','available_individual_archive':archive}
    report={'missing_participants':['AB17'],'missing_participant_ledger':[record]}
    ledger.write_text(json.dumps(report))
    def forbidden(*args,**kwargs):pytest.fail('Preparation attempted network access')
    monkeypatch.setattr(tool.urllib.request,'urlopen',forbidden)
    plan=tool.prepare(ledger,'AB17')
    assert plan['archive']==archive
    assert plan['bindings'][str(ledger.resolve())]==hashlib.sha256(ledger.read_bytes()).hexdigest()
    assert plan['bindings'][str(Path(tool.__file__).resolve())]==hashlib.sha256(Path(tool.__file__).read_bytes()).hexdigest()
    assert plan['destination']=='/mnt/s/locomotion_data/gt21_missing_participants_v1/AB17'
    assert plan['expanded_size_bytes'] is None
    with pytest.raises(ValueError,match='Exactly one'):tool.prepare(ledger,'AB12')
    report['missing_participant_ledger'].append(record)
    ledger.write_text(json.dumps(report))
    with pytest.raises(ValueError,match='Exactly one'):tool.prepare(ledger,'AB17')
