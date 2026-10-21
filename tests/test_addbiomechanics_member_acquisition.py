"""Synthetic ZIP transport fixtures; no public archive payloads or B3D imports."""
import hashlib
import io
import json
import struct
import zlib
from pathlib import Path
import pytest
from contributor_tools import acquire_addbiomechanics_zip_member as tool


def fixture(payload=b'original bytes'*100):
 encoder=zlib.compressobj(wbits=-15);compressed=encoder.compress(payload)+encoder.flush()
 return payload,compressed,dict(name='train/study/subject.b3d',flags=0,compression_method=8,crc32=zlib.crc32(payload),compressed_bytes=len(compressed),expanded_bytes=len(payload),local_header_offset=10)


def header(member,zip64=False):
 name=member['name'].encode();extra=struct.pack('<HHQQ',1,16,member['expanded_bytes'],member['compressed_bytes']) if zip64 else b''
 return struct.pack('<4s5H3L2H',b'PK\x03\x04',45,0,8,0,0,member['crc32'],0xffffffff if zip64 else member['compressed_bytes'],0xffffffff if zip64 else member['expanded_bytes'],len(name),len(extra))+name+extra


@pytest.mark.parametrize('zip64',[False,True])
def test_exact_local_identity(zip64):
 _,_,m=fixture();tool.header_identity(header(m,zip64),m)
 with pytest.raises(ValueError):tool.header_identity(header(m,zip64),dict(m,crc32=0))


def test_missing_zip64_rejected():
 _,_,m=fixture();h=bytearray(header(m));struct.pack_into('<L',h,18,0xffffffff)
 with pytest.raises(ValueError,match='ZIP64'):tool.header_identity(h,m)


@pytest.mark.parametrize('payload',[b'x'*3_000_000,bytes(range(256))*5000])
def test_stream_bounded_inflate_and_exact_original(payload):
 raw,c,m=fixture(payload);a=io.BytesIO();b=io.BytesIO();guards=[]
 r=tool.stream_member(io.BytesIO(c),a,b,m,guard=lambda:guards.append(1),sleep=lambda _:None)
 assert a.getvalue()==c and b.getvalue()==raw
 assert r['source_b3d_sha256']==hashlib.sha256(raw).hexdigest() and len(guards)>2


@pytest.mark.parametrize('fault',['truncated','overlong','crc','expanded_limit','trailing_deflate'])
def test_bad_payload_rejected(fault):
 raw,c,m=fixture()
 if fault=='truncated':c=c[:-1]
 if fault=='overlong':c+=b'x'
 if fault=='crc':m['crc32']=0
 if fault=='expanded_limit':m['expanded_bytes']-=1
 if fault=='trailing_deflate':c+=b'x';m['compressed_bytes']+=1
 with pytest.raises(ValueError):tool.stream_member(io.BytesIO(c),io.BytesIO(),io.BytesIO(),m,sleep=lambda _:None)


def test_guard_and_rate_used():
 _,c,m=fixture();sleeps=[]
 tool.stream_member(io.BytesIO(c),io.BytesIO(),io.BytesIO(),m,rate=100,clock=lambda:0,sleep=sleeps.append)
 assert sleeps and 0<sleeps[0]<=1
 def stop():raise MemoryError('reserve')
 with pytest.raises(MemoryError):tool.stream_member(io.BytesIO(c),io.BytesIO(),io.BytesIO(),m,guard=stop)


@pytest.mark.parametrize('fault',[None,'compressed','expanded','truncated','overlong'])
def test_persisted_output_readback(tmp_path,fault):
 raw,c,m=fixture();compressed=tmp_path/'compressed';expanded=tmp_path/'expanded'
 with compressed.open('wb') as a,expanded.open('wb') as b:
  result=tool.stream_member(io.BytesIO(c),a,b,m,sleep=lambda _:None)
 if fault=='compressed':compressed.write_bytes(b'x'+c[1:])
 if fault=='expanded':expanded.write_bytes(b'x'+raw[1:])
 if fault=='truncated':expanded.write_bytes(raw[:-1])
 if fault=='overlong':expanded.write_bytes(raw+b'x')
 if fault is None:tool.verify_persisted(compressed,expanded,result)
 else:
  with pytest.raises(ValueError,match='Persisted source'):tool.verify_persisted(compressed,expanded,result)


@pytest.mark.parametrize('key,value',[('status',200),('ETag','other'),('Last-Modified','other'),('Content-Range','bytes 1-2/99'),('Content-Length','99'),('Content-Encoding','gzip')])
def test_range_version_strict(key,value):
 archive={'archive_bytes':100,'etag':'"version"','last_modified':'today'}
 class Response:status=206;headers={'Content-Range':'bytes 10-19/100','Content-Length':'10','ETag':'"version"','Last-Modified':'today'}
 r=Response();r.headers=dict(r.headers)
 tool.validate_response(r,10,10,archive)
 if key=='status':r.status=value
 else:r.headers[key]=value
 with pytest.raises(ValueError):tool.validate_response(r,10,10,archive)


def test_prepare_binds_metadata_and_refuses_changed_directory(tmp_path,monkeypatch):
 monkeypatch.setattr(tool,'ROOT',tmp_path)
 root=tmp_path/'converted_datasets/reconversion_v2';root.mkdir(parents=True)
 (tmp_path/'contributor_tools').mkdir();(tmp_path/'contributor_tools/preserve_mblue_planar_estimates.py').write_text('# guard fixture')
 raw,c,m=fixture();h=header(m);(tmp_path/'pilot_local_header.bin').write_bytes(h)
 for f in ['official_download.txt','web_metadata_receipts.json']:(tmp_path/f).write_text('synthetic metadata')
 binary=tmp_path/'central_directory.bin';binary.write_bytes(b'synthetic central directory')
 archive={'etag':'"version"','central_directory_offset':100000,'central_directory_bytes':binary.stat().st_size}
 p={'archive':archive,'member':m,'local_header_sha256':hashlib.sha256(h).hexdigest(),'local_header_bytes':len(h),'payload_offset':10+len(h),'compressed_range':[10+len(h),10+len(h)+len(c)-1],'disk_admission_bytes':5*1024**3+len(c)+len(raw)+16*1024**2}
 proposal=tmp_path/'proposal.json';proposal.write_text(json.dumps(p));central=tmp_path/'central.json';central.write_text(json.dumps({'members':[m],'archive_metadata':archive,'central_directory_sha256':tool.digest(binary)}))
 result=tool.prepare(proposal,central,root/'fresh');plan=json.loads(Path(result['plan']).read_text());assert plan['scientific_approval'] is False and len(plan['bindings'])==8
 binary.write_bytes(b'changed')
 with pytest.raises(ValueError,match='directory receipt'):tool.prepare(proposal,central,root/'second')
