"""Independent literal-byte and raw-value readback for GT25 source companions.

Does not import the writer/planner or infer gait events, reference sides, mass
normalization, anatomical signs, or canonical task readiness.
"""
import argparse,csv,decimal,gzip,hashlib,json,math,os,re,resource,struct,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1024**2),b''):h.update(block)
 return h.hexdigest()


def expected_unit(text,kind,column):
 if column=='time':return 's'
 if kind=='activity_flag':
  if column not in ('left','right') or 'activity_flag.csv: True if task is actively occurring' not in text:raise ValueError('Undocumented activity flag')
  return 'boolean'
 match=re.search(r'^'+re.escape(kind)+r'\.csv:.*?(?=^[a-z_]+\.csv:|\Z)',text,re.M|re.S)
 if not match:raise ValueError('No source README section: '+kind)
 for line in match.group().splitlines()[1:]:
  m=re.fullmatch(r'\s+([A-Za-z0-9_<>]+) \(([^)]+)\)\s*',line)
  if not m:continue
  pattern=re.escape(m[1]).replace('<side>','[lr]')
  if m[1].startswith('pelvis_imu_<side>_'):pattern=pattern.replace('pelvis_imu_[lr]_','pelvis_imu_(?:[lr]_)?')
  if re.fullmatch(pattern,column):return {'sec':'s','m/s^2':'m/s2'}.get(m[2],m[2])
 return None


def raw_expected(token):
 value=token.strip().lower()
 if value in ('','na','n/a','null'):return None
 if value=='true':return 1.
 if value=='false':return 0.
 return float(decimal.Decimal(value))


def value_equal(a,b):
 if a is None or b is None:return a is None and b is None
 if math.isnan(a) or math.isnan(b):return math.isnan(a) and math.isnan(b)
 return struct.pack('>d',a)==struct.pack('>d',b)


def check_stream(source,compressed,parquet,kind,identity,readme,guard=lambda:None):
 import pyarrow.parquet as pq
 # Independent byte comparison, including literal headers, quoting, newline and missing tokens.
 raw_hash=hashlib.sha256();count_bytes=0
 with Path(source).open('rb') as original,gzip.open(compressed,'rb') as restored:
  while True:
   left=original.read(1024**2);right=restored.read(1024**2);guard()
   if left!=right:raise ValueError('Compressed source is not byte-identical')
   if not left:break
   raw_hash.update(left);count_bytes+=len(left)
 table=pq.ParquetFile(parquet);schema=table.schema_arrow;meta=schema.metadata or {}
 if meta.get(b'observation_scope')!=b'continuous_parsed_source_stream' or meta.get(b'scientific_approval')!=b'false' or json.loads(meta[b'source_identity'])!=identity or meta.get(b'kind')!=kind.encode():raise ValueError('Source scope/identity metadata differs')
 total=0;finite={};missing={};positive_inf={};negative_inf={};clock={'nonfinite':0,'duplicates':0,'decreases':0};previous=None
 with Path(source).open(newline='',encoding='utf-8-sig') as stream:
  reader=csv.DictReader(stream)
  names=reader.fieldnames
  if not names or len(names)!=len(set(names)):raise ValueError('Invalid source header')
  aliases=['source_'+kind+'__'+n for n in names]
  if schema.names!=['source_row_index',*aliases]:raise ValueError('Literal source header mapping differs')
  for name,alias in zip(names,aliases):
   f=schema.field(alias);fm=f.metadata or {};unit=expected_unit(readme,kind,name)
   if fm.get(b'original_name')!=name.encode() or json.loads(fm[b'source_unit'])!=unit or fm.get(b'unit_status')!=(b'unit_unassessed' if unit is None else b'documented_source_unit'):raise ValueError('Source unit evidence mismatch: '+name)
   finite[alias]=0;missing[alias]=0;positive_inf[alias]=0;negative_inf[alias]=0
  for batch in table.iter_batches(batch_size=1024,use_threads=False):
   if batch.nbytes>8*1024**2:raise MemoryError('Readback batch admission exceeded')
   guard()
   for actual in batch.to_pylist():
    row=next(reader,None)
    if row is None or None in row or any(v is None for v in row.values()) or actual['source_row_index']!=total:raise ValueError('Source row membership/order mismatch')
    for name,alias in zip(names,aliases):
     expected=raw_expected(row[name])
     if not value_equal(actual[alias],expected):raise ValueError('Raw value or missing mask differs: '+name)
     if expected is None or math.isnan(expected):missing[alias]+=1
     elif math.isfinite(expected):finite[alias]+=1
     elif expected>0:positive_inf[alias]+=1
     else:negative_inf[alias]+=1
    t=raw_expected(row['time']) if 'time' in row else None
    if t is None or not math.isfinite(t):clock['nonfinite']+=1
    else:
     if previous is not None:
      clock['duplicates']+=int(t==previous);clock['decreases']+=int(t<previous)
     previous=t
    total+=1
  if next(reader,None) is not None or total==0:raise ValueError('Incomplete source row coverage')
 if digest(source)!=raw_hash.hexdigest():raise ValueError('Source changed during independent readback')
 return {'rows':total,'source_bytes':count_bytes,'source_sha256':raw_hash.hexdigest(),'literal_csv_bytes_equal':True,'every_numeric_value_and_missing_mask_checked':True,'source_header_and_units_checked':True,'source_clock_diagnostics':clock,'finite_values_by_column':finite,'missing_values_by_column':missing,'positive_infinity_by_column':positive_inf,'negative_infinity_by_column':negative_inf,'unit_unassessed_columns':[n for n in names if expected_unit(readme,kind,n) is None]}


def run(plan_path,expected):
 for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[name]='1'
 resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
 plan_path=Path(plan_path).resolve();out=plan_path.parent
 if digest(plan_path)!=expected:raise ValueError('Plan changed')
 plan=json.loads(plan_path.read_text());receipt_path=out/'preservation.json';receipt_sha=digest(receipt_path);receipt=json.loads(receipt_path.read_text())
 if receipt.get('status')!='all_source_streams_preserved_pending_independent_readback' or receipt.get('scientific_approval') is not False or receipt.get('plan_sha256')!=expected or receipt.get('bindings')!=plan['bindings']:raise ValueError('Completed source preservation prerequisite missing')
 for p,h in plan['bindings'].items():
  if digest(p)!=h:raise ValueError('Frozen dependency changed')
 attempt=out/'source_audit_attempt.json'
 with attempt.open('x') as f:json.dump({'scientific_approval':False,'status':'started','preservation_sha256':receipt_sha},f)
 import sys,shutil
 sys.path.insert(0,str(ROOT))
 from contributor_tools.preserve_mblue_planar_estimates import headroom,windows_available_mib
 headroom(out)
 if windows_available_mib()<2816:raise MemoryError('Source audit startup headroom insufficient')
 import pyarrow as pa
 pa.set_cpu_count(1);pa.set_io_thread_count(1)
 last=0.
 def guard():
  nonlocal last
  if time.monotonic()-last>15:
   headroom(out)
   if windows_available_mib()<2048:raise MemoryError('Source audit runtime reserve insufficient')
   last=time.monotonic()
 files={f['kind']:f for f in plan['record']['files']};streams=receipt['streams']
 if len(files)!=15 or len(streams)!=15 or {s['kind'] for s in streams}!=set(files):raise ValueError('All15 unique source streams required')
 identity={k:plan['record'][k] for k in ('subject','recording','source_recording_id')};readme=Path(plan['readme']).read_text();results=[]
 for stream in streams:
  file=files[stream['kind']]
  if stream['source_path']!=file['path'] or stream['source_bytes']!=file['bytes']:raise ValueError('Source manifest identity differs')
  for field,hashfield in [('compressed','compressed_sha256'),('parquet','parquet_sha256')]:
   if Path(stream[field]).name!=stream[field] or digest(out/stream[field])!=stream[hashfield]:raise ValueError('Output artifact changed')
  result=check_stream(file['path'],out/stream['compressed'],out/stream['parquet'],stream['kind'],identity,readme,guard)
  if result['rows']!=stream['rows'] or result['source_sha256']!=stream['source_sha256']:raise ValueError('Preservation receipt count/hash differs')
  results.append({'kind':stream['kind'],**result})
 for p,h in plan['bindings'].items():
  if digest(p)!=h:raise ValueError('Frozen source evidence changed')
 if digest(plan_path)!=expected or digest(receipt_path)!=receipt_sha:raise ValueError('Plan or receipt changed')
 report={'status':'all15_source_streams_lossless_readback_checked_unreviewed','scientific_approval':False,'canonical_dataset_approval':False,'subject':identity['subject'],'recording':identity['recording'],'plan_sha256':expected,'preservation_sha256':receipt_sha,'bindings':plan['bindings'],'streams':results,'limitations':['Source preservation only. No canonical task/cycle/anatomical/mass-normalization approval.','Clocks and missingness are reported without repair, filtering, interpolation, or invented time.','Parsed source is already condition-split; original acquisition transitions are not recovered.']}
 with (out/'source_readback.json').open('x') as f:json.dump(report,f,indent=2)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--plan-sha256',required=True);a=p.parse_args();run(a.plan,a.plan_sha256)
if __name__=='__main__':main()
