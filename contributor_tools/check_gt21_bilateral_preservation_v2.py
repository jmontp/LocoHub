"""Isolated strict GT21 adoption-preservation gate; not wired to frozen pilots.

Use explicit errors even under Python optimization. The original gate rejects
duplicate baseline IDs in default Python, but relies on an assert after dict().
Read one150row observation at a time. A pass does not verify events, terrain,
force/COP, source conventions, or completion of the2301record inventory.
"""
import hashlib,json,math,struct
from pathlib import Path


def encoded(value):
 if value is None:return ['null']
 if isinstance(value,bool):return ['bool',value]
 if isinstance(value,int):return ['int',str(value)]
 if isinstance(value,float):return ['float64',struct.pack('>d',value).hex()]
 if isinstance(value,str):return ['str',value]
 raise ValueError('Unsupported scalar in exact preservation gate')


def fingerprint(columns,rows):
 if len(rows)!=150 or len(set(columns))!=len(columns) or not {'observation_id','reference_side','source_start_time_s','source_end_time_s'}<=set(columns):raise ValueError('Complete150row observation and unique columns required')
 if any(set(row)!=set(columns) for row in rows):raise ValueError('Observation row schema differs')
 identities={r['observation_id'] for r in rows};sides={r['reference_side'] for r in rows}
 if len(identities)!=1 or len(sides)!=1:raise ValueError('Mixed observation identity/side')
 identity=rows[0]['observation_id'];side=rows[0]['reference_side']
 if not isinstance(identity,str) or not identity or side not in ('left','right'):raise ValueError('Invalid observation identity/side')
 start,end=rows[0]['source_start_time_s'],rows[0]['source_end_time_s']
 if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in (start,end)) or end<=start:raise ValueError('Invalid source cycle interval')
 if any(r['source_start_time_s']!=start or r['source_end_time_s']!=end for r in rows):raise ValueError('Mixed source cycle interval')
 h=hashlib.sha256();h.update(json.dumps(columns).encode())
 for row in rows:h.update(json.dumps([encoded(row[c]) for c in columns],ensure_ascii=True,separators=(',',':')).encode());h.update(b'\n')
 return identity,side,h.hexdigest()


def check_observations(baseline,candidate,max_observations=25000):
 """Iterators yield (ordered column names,150row dict list); memory stores hashes only."""
 originals={};seen=set();added=[]
 for columns,rows in baseline:
  identity,side,sha=fingerprint(columns,rows)
  if identity in originals:raise ValueError('Duplicate baseline observation identity')
  if len(originals)>=max_observations:raise MemoryError('Bounded baseline observation admission exceeded')
  originals[identity]=(side,sha)
 if not originals:raise ValueError('Empty baseline cannot prove adoption preservation')
 for columns,rows in candidate:
  identity,side,sha=fingerprint(columns,rows)
  if identity in seen:raise ValueError('Duplicate candidate observation identity')
  if len(seen)>=max_observations:raise MemoryError('Bounded candidate observation admission exceeded')
  seen.add(identity)
  if identity in originals:
   if originals[identity]!=(side,sha):raise ValueError('Original observation values/schema/missingness changed')
  else:added.append({'observation_id':identity,'reference_side':side,'start_s':float(rows[0]['source_start_time_s']),'end_s':float(rows[0]['source_end_time_s'])})
 if set(originals)-seen:raise ValueError('Original observations disappeared')
 if not added:raise ValueError('No bilateral additions; recovery remains unproved')
 return {'status':'exact_baseline_preservation_checked_unreviewed','preserved_observations':len(originals),'added_observations':len(added),'added_cycles':added,'scientific_approval':False,'source_pair_coverage_checked':False,'force_cop_checked':False,'full2301scope_checked':False}


def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
 return h.hexdigest()


def verify_preserved(baseline,recovered):
 """Future pilot integration only; caller owns guarded exclusive numerical slot."""
 import pyarrow.parquet as pq
 before={str(p):digest(p) for p in (baseline,recovered)}
 old=pq.ParquetFile(baseline);new=pq.ParquetFile(recovered)
 if not old.schema_arrow.equals(new.schema_arrow,check_metadata=True):raise ValueError('Exact output field/schema metadata changed')
 def curves(parquet):
  for batch in parquet.iter_batches(batch_size=150,use_threads=False):
   if batch.nbytes>8*1024**2:raise MemoryError('Observation exceeds8MiB')
   yield batch.schema.names,batch.to_pylist()
 report=check_observations(curves(old),curves(new))
 if any(digest(path)!=sha for path,sha in before.items()):raise ValueError('Preservation inputs changed during check')
 report['input_sha256']=before;report['exact_schema_metadata_checked']=True
 return report
