"""Acquire one pinned official ZIP member with bounded streaming inflation.

Default preparation only. No archive-wide download or native B3D imports.
HTTP ETag+CRC transport binding is NOT a publisher cryptographic signature.
"""
import argparse,hashlib,json,os,resource,shutil,struct,sys,time,urllib.request,zlib
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
CHUNK=256*1024


def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for block in iter(lambda:stream.read(CHUNK),b''):h.update(block)
 return h.hexdigest()


def verify_persisted(compressed,expanded,result,guard=lambda:None):
 """Reopen both outputs; hashes computed while writing alone are insufficient."""
 for path,size_key,hash_key in [(compressed,'compressed_bytes','compressed_sha256'),(expanded,'expanded_bytes','source_b3d_sha256')]:
  h=hashlib.sha256();size=0
  with Path(path).open('rb') as stream:
   while True:
    guard();block=stream.read(CHUNK)
    if not block:break
    size+=len(block)
    if size>result[size_key]:raise ValueError('Persisted source exceeds expected size')
    h.update(block)
  if size!=result[size_key] or h.hexdigest()!=result[hash_key]:raise ValueError('Persisted source readback differs')


def validate_response(response,start,length,archive):
 if response.status!=206 or response.headers.get('Content-Range')!=f'bytes {start}-{start+length-1}/{archive["archive_bytes"]}':raise ValueError('Exact206 Content-Range required')
 if response.headers.get('ETag')!=archive['etag'] or response.headers.get('Last-Modified')!=archive['last_modified']:raise ValueError('Archive version changed')
 if response.headers.get('Content-Encoding','identity')!='identity':raise ValueError('Encoded transfer forbidden')
 if response.headers.get('Content-Length')!=str(length):raise ValueError('Range byte length differs')


def request_range(start,length,archive):
 req=urllib.request.Request(archive['url'],headers={'Range':f'bytes={start}-{start+length-1}','If-Match':archive['etag'],'Accept-Encoding':'identity'})
 response=urllib.request.urlopen(req,timeout=30)
 try:validate_response(response,start,length,archive)
 except BaseException:response.close();raise
 return response


def header_identity(data,member):
 if len(data)<30:raise ValueError('Truncated localheader')
 f=struct.unpack_from('<4s5H3L2H',data)
 if f[0]!=b'PK\x03\x04' or f[2]!=member['flags'] or f[3]!=member['compression_method'] or f[2]&9:raise ValueError('Unsupported/encrypted/data-descriptor ZIP member')
 n,e=f[-2:]
 if len(data)!=30+n+e or data[30:30+n].decode('utf-8')!=member['name']:raise ValueError('Local member name differs')
 crc,compressed,expanded=f[6:9];extra=data[30+n:];offset=0;zip64=None
 while offset<len(extra):
  if offset+4>len(extra):raise ValueError('Invalid extra header')
  kind,size=struct.unpack_from('<HH',extra,offset);offset+=4
  if offset+size>len(extra):raise ValueError('Invalid extra size')
  if kind==1:
   if zip64 is not None:raise ValueError('DuplicateZIP64')
   zip64=extra[offset:offset+size]
  offset+=size
 cursor=0
 for key,value in [('expanded_bytes',expanded),('compressed_bytes',compressed)]:
  if value==0xffffffff:
   if zip64 is None or cursor+8>len(zip64):raise ValueError('MissingZIP64size')
   value=struct.unpack_from('<Q',zip64,cursor)[0];cursor+=8
  if value!=member[key]:raise ValueError('Local/central size mismatch')
 if crc!=member['crc32']:raise ValueError('Local/central CRC mismatch')


def stream_member(response,compressed_out,expanded_out,member,guard=lambda:None,rate=1024*1024,clock=time.monotonic,sleep=time.sleep):
 if member['compression_method']!=8 or member['expanded_bytes']<=0:raise ValueError('Nonempty DEFLATE member required')
 inflater=zlib.decompressobj(-15);compressed_hash=hashlib.sha256();expanded_hash=hashlib.sha256();crc=0;read=written=0;chunks=[];started=clock()
 while read<member['compressed_bytes']:
  guard();block=response.read(min(CHUNK,member['compressed_bytes']-read))
  if not block:raise ValueError('Truncated compressed member')
  compressed_out.write(block);compressed_hash.update(block);chunks.append(hashlib.sha256(block).hexdigest());read+=len(block);pending=block
  while True:
   value=inflater.decompress(pending,CHUNK);pending=inflater.unconsumed_tail
   if written+len(value)>member['expanded_bytes']:raise ValueError('Expanded member exceeds pinned size')
   expanded_out.write(value);expanded_hash.update(value);crc=zlib.crc32(value,crc);written+=len(value);guard()
   if inflater.unused_data:raise ValueError('Trailing compressed payload')
   if not pending and len(value)<CHUNK:break
  delay=read/rate-(clock()-started)
  if delay>0:sleep(min(delay,1.));guard()
 if response.read(1):raise ValueError('Overlong range body')
 if not inflater.eof or written!=member['expanded_bytes'] or (crc&0xffffffff)!=member['crc32']:raise ValueError('Incomplete/CRC-invalid original B3D')
 return {'compressed_sha256':compressed_hash.hexdigest(),'source_b3d_sha256':expanded_hash.hexdigest(),'compressed_bytes':read,'expanded_bytes':written,'crc32':crc&0xffffffff,'compressed_chunk_sha256':chunks}


def prepare(proposal,central,output):
 proposal=Path(proposal).resolve();central=Path(central).resolve();output=Path(output).resolve();p=json.loads(proposal.read_text());c=json.loads(central.read_text());member=p['member'];name=PurePosixPath(member['name'])
 if name.is_absolute() or any(x in ('..','') for x in name.parts) or '\\' in member['name'] or ':' in member['name'] or not member['name'].endswith('.b3d'):raise ValueError('Unsafe source member path')
 if output.exists() or not output.is_relative_to(ROOT/'converted_datasets/reconversion_v2'):raise ValueError('Fresh isolated output required')
 matches=[r for r in c['members'] if r['name']==member['name']]
 if matches!=[member] or p['archive']!=c['archive_metadata']:raise ValueError('Proposal not exactly bound to centraldirectory')
 local=proposal.parent/'pilot_local_header.bin';header_identity(local.read_bytes(),member)
 if local.stat().st_size!=p['local_header_bytes']:raise ValueError('Local header length mismatch')
 if member['compression_method']!=8 or min(member['compressed_bytes'],member['expanded_bytes'])<=0:raise ValueError('Nonempty DEFLATE member required')
 if p['compressed_range']!=[p['payload_offset'],p['payload_offset']+member['compressed_bytes']-1]:raise ValueError('Payload range mismatch')
 if p['payload_offset']+member['compressed_bytes']>c['archive_metadata']['central_directory_offset']:raise ValueError('Payload overlaps directory')
 binary=proposal.parent/'central_directory.bin'
 if digest(binary)!=c['central_directory_sha256'] or binary.stat().st_size!=c['archive_metadata']['central_directory_bytes']:raise ValueError('Central directory receipt mismatch')
 if p['disk_admission_bytes']<5*1024**3+member['compressed_bytes']+member['expanded_bytes']+16*1024**2:raise ValueError('Insufficient disk admission reserve')
 if digest(local)!=p['local_header_sha256'] or p['payload_offset']!=member['local_header_offset']+p['local_header_bytes']:raise ValueError('Pinned localheader mismatch')
 if not p['archive']['etag'] or p['archive']['etag'].startswith('W/'):raise ValueError('Strong archiveETag required')
 paths=[proposal,central,local,Path(__file__).resolve(),ROOT/'contributor_tools/preserve_mblue_planar_estimates.py',proposal.parent/'official_download.txt',proposal.parent/'web_metadata_receipts.json',proposal.parent/'central_directory.bin']
 plan={'status':'prepared_not_acquired','scientific_approval':False,'proposal':p,'output':str(output),'bindings':{str(path):digest(path) for path in paths},'network_rate_bytes_per_second':1024*1024,'timeout_seconds':7200,'memory_cap_mib':768,'provenance_limit':'Original publisher archive current object; localSHA computed on acquisition, not a publisherSHA. HTTP transport and CRC cannot establish cryptographic authenticity. No equivalence to old localB3Dexport claimed.'}
 output.mkdir();path=output/'plan.json';path.write_text(json.dumps(plan,indent=2)+'\n');return {'plan':str(path),'plan_sha256':digest(path),'compressed_bytes':member['compressed_bytes'],'expanded_bytes':member['expanded_bytes']}


def acquire(path,sha):
 path=Path(path).resolve();out=path.parent
 if digest(path)!=sha or {p.name for p in out.iterdir()}!={'plan.json'}:raise ValueError('Fresh bound acquisitionplan required')
 plan=json.loads(path.read_text())
 if Path(plan['output'])!=out:raise ValueError('Output root differs from bound plan')
 proposal=plan['proposal'];archive=proposal['archive'];member=proposal['member'];resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
 from contributor_tools.preserve_mblue_planar_estimates import headroom,windows_available_mib
 def verify():
  if digest(path)!=sha:raise ValueError('Plan changed')
  for p,h in plan['bindings'].items():
   if digest(p)!=h:raise ValueError('Bound source metadata/tool changed')
 verify();headroom(out)
 if windows_available_mib()<2816 or shutil.disk_usage(out).free<proposal['disk_admission_bytes']:raise MemoryError('Acquisition admission refused')
 started=time.monotonic();last=[0.]
 def guard():
  if (out/'STOP').exists():raise RuntimeError('Coordinator STOP')
  if time.monotonic()-started>plan['timeout_seconds']:raise TimeoutError('Finite acquisition timeout')
  if shutil.disk_usage(out).free<5*1024**3+2*CHUNK:raise MemoryError('Preserve5GiB diskreserve')
  if time.monotonic()-last[0]>15:
   headroom(out)
   if windows_available_mib()<2048:raise MemoryError('Windows runtime reserve')
   last[0]=time.monotonic()
 with (out/'attempt.json').open('x') as stream:json.dump({'plan_sha256':sha,'status':'acquiring'},stream)
 try:
  with request_range(member['local_header_offset'],proposal['local_header_bytes'],archive) as response:header=response.read(proposal['local_header_bytes']+1)
  if hashlib.sha256(header).hexdigest()!=proposal['local_header_sha256']:raise ValueError('Remote localheader changed')
  header_identity(header,member);target=out/'source'/member['name'];target.parent.mkdir(parents=True);partial=target.with_name(target.name+'.partial');compressed=out/'source_member.deflate.partial'
  with request_range(proposal['payload_offset'],member['compressed_bytes'],archive) as response,compressed.open('xb') as c,partial.open('xb') as b:
   result=stream_member(response,c,b,member,guard,plan['network_rate_bytes_per_second'])
  verify_persisted(compressed,partial,result,guard)
  verify();guard();partial.rename(target);compressed.rename(out/'source_member.deflate')
  result['persisted_outputs_readback_verified']=True
  result.update(status='official_member_crc_and_local_sha_verified_not_scientifically_reviewed',scientific_approval=False,plan_sha256=sha,source_path=str(target),member_name=member['name'],archive=archive,provenance_limit=plan['provenance_limit'])
  with (out/'acquisition.json').open('x') as stream:json.dump(result,stream,indent=2)
 except BaseException as error:
  with (out/'failure.json').open('x') as stream:json.dump({'status':'failed_partial_preserved','reason':str(error),'scientific_approval':False},stream)
  raise

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True);q=s.add_parser('prepare');q.add_argument('--proposal',type=Path,required=True);q.add_argument('--central-directory',type=Path,required=True);q.add_argument('--output',type=Path,required=True);q=s.add_parser('acquire');q.add_argument('--plan',type=Path,required=True);q.add_argument('--plan-sha256',required=True);a=p.parse_args()
 if a.mode=='prepare':print(json.dumps(prepare(a.proposal,a.central_directory,a.output)))
 else:acquire(a.plan,a.plan_sha256)
