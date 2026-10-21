"""Fresh, bounded GT25 source companions; never canonical gait observations.

Plan-only by default. Original CSV bytes are retained losslessly compressed;
raw aliases retain original units, signs, clock and row order per stream.
"""
import argparse,csv,gzip,hashlib,json,math,os,resource,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024**2),b''):h.update(b)
 return h.hexdigest()


def numeric(token):
 value=token.strip()
 if value.lower() in ('','na','n/a','null'):return None
 if value.lower()=='true':return 1.
 if value.lower()=='false':return 0.
 return float(value)


def prepare(classification,subject,recording,output):
 classification=Path(classification).resolve();output=Path(output).resolve();data=json.loads(classification.read_text())
 if data.get('status')!='all192_source_recording_dispositions_prepared_not_converted' or data['counts']['records']!=192:raise ValueError('Exact192 source disposition required')
 selected=[r for r in data['records'] if (r['subject'],r['recording'])==(subject,recording)]
 if len(selected)!=1:raise ValueError('Ambiguous source recording')
 if not output.is_relative_to(ROOT/'converted_datasets/reconversion_v2') or output.exists():raise FileExistsError('Fresh local output required')
 files=[Path(__file__).resolve(),ROOT/'contributor_tools/audit_gt25_source_companion.py',ROOT/'contributor_tools/preserve_mblue_planar_estimates.py',classification]
 bindings={**data['bindings'],**{str(p):digest(p) for p in files}}
 for p,h in bindings.items():
  if digest(p)!=h:raise ValueError('Classification dependency changed')
 record=selected[0]
 for f in record['files']:
  st=Path(f['path']).stat()
  if (st.st_size,st.st_mtime_ns)!=(f['bytes'],f['mtime_ns']):raise ValueError('Source stat changed since header inventory')
 profiles={f['header_profile']:data['header_profiles'][f['header_profile']] for f in record['files']}
 plan={'status':'prepared_not_run','scientific_approval':False,'bindings':bindings,'record':record,'profiles':profiles,'readme':next(p for p in data['bindings'] if p.endswith('/readme.txt')),'memory_admission_mib':256,'output':str(output)}
 output.mkdir(parents=True);(output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');return {'plan':str(output/'plan.json'),'plan_sha256':digest(output/'plan.json')}


def preserve_stream(file,profile,output,metadata,guard):
 import pyarrow as pa
 import pyarrow.parquet as pq
 path=Path(file['path']);st=path.stat();before=(st.st_size,st.st_mtime_ns)
 if before!=(file['bytes'],file['mtime_ns']):raise ValueError('Source changed before run')
 compressed=output/(file['kind']+'.csv.gz.partial');parquet=output/(file['kind']+'.parquet.partial');h=hashlib.sha256()
 with path.open('rb') as source,compressed.open('xb') as raw:
  with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as archive:
   for block in iter(lambda:source.read(1024**2),b''):guard();h.update(block);archive.write(block)
 columns=profile['columns'];fields=[pa.field('source_row_index',pa.int64())]
 for c in columns:
  fields.append(pa.field(c['proposed_alias'],pa.float64(),metadata={b'original_name':c['source_name'].encode(),b'source_unit':json.dumps(c['source_unit']).encode(),b'unit_status':c['status'].encode()}))
 schema=pa.schema(fields,metadata={b'observation_scope':b'continuous_parsed_source_stream',b'scientific_approval':b'false',b'source_identity':json.dumps(metadata,sort_keys=True).encode(),b'kind':file['kind'].encode(),b'interpretation':b'Original source signs/units; no canonical mapping, interpolation, filtering, mass normalization or reference limb.'})
 count=0;batch=[];batch_bytes=0
 with pq.ParquetWriter(parquet,schema,compression='zstd') as writer,path.open('rb') as source:
  header=source.readline(65537)
  if hashlib.sha256(header).hexdigest()!=profile['header_sha256']:raise ValueError('Original header changed')
  names=next(csv.reader([header.decode('utf-8-sig').rstrip('\r\n')]))
  if names!=[c['source_name'] for c in columns]:raise ValueError('Header mapping differs')
  def flush():
   nonlocal batch,batch_bytes
   if not batch:return
   arrays=[pa.array([r[0] for r in batch],type=pa.int64())]+[pa.array([r[i+1] for r in batch],type=pa.float64()) for i in range(len(columns))]
   table=pa.Table.from_arrays(arrays,schema=schema)
   if table.nbytes>8*1024**2:raise MemoryError('Arrow batch exceeds8MiB')
   guard();writer.write_table(table,row_group_size=1024);batch=[];batch_bytes=0
  while True:
   line=source.readline(1024**2+1)
   if not line:break
   if len(line)>1024**2:raise MemoryError('Source row exceeds1MiB')
   values=next(csv.reader([line.decode('utf-8').rstrip('\r\n')],strict=True))
   if len(values)!=len(columns):raise ValueError('Source row width mismatch')
   if batch and (len(batch)>=1024 or batch_bytes+len(line)>2*1024**2):flush()
   batch.append([count,*[numeric(v) for v in values]]);batch_bytes+=len(line);count+=1
  flush()
 if count==0:raise ValueError('Empty source stream')
 if digest(path)!=h.hexdigest() or (path.stat().st_size,path.stat().st_mtime_ns)!=before:raise ValueError('Source changed during preservation')
 final_csv=compressed.with_suffix('');final_parquet=parquet.with_suffix('');compressed.replace(final_csv);parquet.replace(final_parquet)
 return {'kind':file['kind'],'source_path':str(path),'source_sha256':h.hexdigest(),'source_bytes':before[0],'rows':count,'compressed':final_csv.name,'compressed_sha256':digest(final_csv),'parquet':final_parquet.name,'parquet_sha256':digest(final_parquet),'source_header_sha256':profile['header_sha256']}


def run(plan_path,expected):
 for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[name]='1'
 resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
 plan_path=Path(plan_path).resolve();out=plan_path.parent
 if digest(plan_path)!=expected or {p.name for p in out.iterdir()}!={'plan.json'}:raise ValueError('Fresh bound plan only required')
 plan=json.loads(plan_path.read_text())
 for p,h in plan['bindings'].items():
  if digest(p)!=h:raise ValueError('Bound source companion dependency changed')
 import sys,shutil
 sys.path.insert(0,str(ROOT))
 from contributor_tools.preserve_mblue_planar_estimates import headroom,windows_available_mib
 headroom(out)
 if windows_available_mib()<2816 or shutil.disk_usage(out).free<5*1024**3+4*plan['record']['all_csv_bytes']:raise MemoryError('Conservative perrecord memory/disk admission refused')
 import pyarrow as pa
 pa.set_cpu_count(1);pa.set_io_thread_count(1)
 last=0.
 def guard():
  nonlocal last
  if shutil.disk_usage(out).free<5*1024**3+8*1024**2:raise OSError('Retain5GiB disk reserve')
  if time.monotonic()-last>15:
   headroom(out)
   if windows_available_mib()<2048:raise MemoryError('Host reserve below2GiB')
   last=time.monotonic()
 record=plan['record'];report={'status':'running','scientific_approval':False,'subject':record['subject'],'recording':record['recording'],'source_metadata':record['source_metadata'],'bindings':plan['bindings'],'plan_sha256':expected,'streams':[]}
 def save():
  p=out/'preservation.tmp';p.write_text(json.dumps(report,indent=2)+'\n');p.replace(out/'preservation.json')
 save()
 try:
  for file in record['files']:
   if (out/'STOP_AFTER_CURRENT').exists():raise RuntimeError('Coordinator stopped source companion')
   metadata={k:record[k] for k in ('subject','recording','source_recording_id')}
   report['streams'].append(preserve_stream(file,plan['profiles'][file['header_profile']],out,metadata,guard));save()
  for p,h in plan['bindings'].items():
   if digest(p)!=h:raise ValueError('Dependency changed during preservation')
  if digest(plan_path)!=expected:raise ValueError('Plan changed')
  report['status']='all_source_streams_preserved_pending_independent_readback'
 except Exception as e:report.update(status='failed_preserved_partial',reason=str(e));raise
 finally:save()


def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='mode',required=True);q=sub.add_parser('prepare')
 for n in ['classification','output']:q.add_argument('--'+n,type=Path,required=True)
 for n in ['subject','recording']:q.add_argument('--'+n,required=True)
 q=sub.add_parser('run');q.add_argument('--plan',type=Path,required=True);q.add_argument('--plan-sha256',required=True);a=p.parse_args()
 if a.mode=='prepare':print(json.dumps(prepare(a.classification,a.subject,a.recording,a.output)))
 else:run(a.plan,a.plan_sha256)
if __name__=='__main__':main()
