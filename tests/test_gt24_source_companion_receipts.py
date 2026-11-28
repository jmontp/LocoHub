"""Synthetic tiny receipts/Arrow files only; no scientific source data."""
import gzip,hashlib,json
from pathlib import Path
import pytest
from contributor_tools import audit_gt24_source_companion as audit
from contributor_tools import run_gt24_source_companion_batch as batch


def fixture(tmp_path):
 import pyarrow as pa
 import pyarrow.parquet as pq
 pa.set_cpu_count(1);pa.set_io_thread_count(1)
 source=tmp_path/'source.csv';source.write_text('time,value\n0,1\n1,2\n')
 compressed=tmp_path/'source.csv.gz';compressed.write_bytes(gzip.compress(source.read_bytes(),mtime=0))
 identity={'phase':'synthetic','subject':'synthetic','recording':'synthetic','source_recording_id':'synthetic:only'}
 fields=[pa.field('source_row_index',pa.int64())]
 for name,unit in [('time','s'),('value',None)]:
  fields.append(pa.field('source_raw__'+name,pa.float64(),metadata={b'original_name':name.encode(),b'source_unit':json.dumps(unit).encode(),b'unit_status':b'unit_unassessed' if unit is None else b'documented_source_unit'}))
 schema=pa.schema(fields,metadata={b'observation_scope':b'continuous_parsed_source_stream',b'scientific_approval':b'false',b'source_identity':json.dumps(identity).encode(),b'kind':b'raw'})
 output=tmp_path/'source.parquet';pq.write_table(pa.Table.from_arrays([pa.array([0,1],type=pa.int64()),pa.array([0.,1.]),pa.array([1.,2.])],schema=schema),output)
 return source,compressed,output,identity


def test_actual_output_hashes_recorded(tmp_path):
 source,compressed,output,identity=fixture(tmp_path)
 result=audit.check_stream(source,compressed,output,'raw',identity,'raw.csv: test\n')
 assert result['compressed_sha256']==audit.digest(compressed)
 assert result['parquet_sha256']==audit.digest(output)
 assert result['compressed']==compressed.name and result['parquet']==output.name


@pytest.mark.parametrize('column,type_name',[('source_row_index','int32'),('source_raw__value','float32')])
def test_equal_values_wrong_types_rejected(tmp_path,column,type_name):
 import pyarrow as pa
 import pyarrow.parquet as pq
 source,compressed,output,identity=fixture(tmp_path);table=pq.ParquetFile(output).read(use_threads=False)
 i=table.schema.get_field_index(column);old=table.schema.field(i);dtype={'int32':pa.int32(),'float32':pa.float32()}[type_name]
 table=table.set_column(i,pa.field(column,dtype,metadata=old.metadata),table[column].cast(dtype));pq.write_table(table,output)
 with pytest.raises(ValueError,match='schema must use'):audit.check_stream(source,compressed,output,'raw',identity,'raw.csv: test\n')


def test_output_changed_during_readback_rejected_even_same_restored_bytes(tmp_path,monkeypatch):
 source,compressed,output,identity=fixture(tmp_path);equal=audit.value_equal;changed=[False]
 def mutate(a,b):
  if not changed[0]:compressed.write_bytes(gzip.compress(source.read_bytes(),mtime=1234));changed[0]=True
  return equal(a,b)
 monkeypatch.setattr(audit,'value_equal',mutate)
 with pytest.raises(ValueError,match='Output changed during'):audit.check_stream(source,compressed,output,'raw',identity,'raw.csv: test\n')


def closure_fixture(tmp_path):
 source,compressed,output,identity=fixture(tmp_path)
 result=audit.check_stream(source,compressed,output,'raw',identity,'raw.csv: test\n')
 row={**identity,'files':[{'kind':'raw','path':str(source),'bytes':source.stat().st_size}]}
 plan=tmp_path/'plan.json';plan.write_text('{}');preservation=tmp_path/'preservation.json';preservation.write_text('{}')
 receipt={**identity,'status':'all_inventoried_source_streams_lossless_readback_checked_unreviewed','scientific_approval':False,'canonical_dataset_approval':False,'plan_sha256':batch.digest(plan),'preservation_sha256':batch.digest(preservation),'streams':[{'kind':'raw',**result}]}
 (tmp_path/'source_readback.json').write_text(json.dumps(receipt));return row,output


@pytest.mark.parametrize('target',['source.parquet','source.csv.gz','source.csv','plan.json','preservation.json','source_readback.json'])
def test_closure_detects_prior_artifact_mutation(tmp_path,target):
 row,output=closure_fixture(tmp_path);bindings=batch.receipt_closure(tmp_path,row)
 with (tmp_path/target).open('ab') as stream:stream.write(b'changed')
 with pytest.raises(ValueError):batch.verify(bindings)


def test_different_source_recording_id_not_accepted(tmp_path):
 row,output=closure_fixture(tmp_path);row['source_recording_id']='other'
 with pytest.raises(ValueError,match='recording ID'):batch.receipt_closure(tmp_path,row)


def test_cleanup_kills_owned_group_after_leader_exit(monkeypatch):
 calls=[]
 class Child:
  pid=123
  def poll(self):return 0
  def wait(self,timeout):calls.append(('wait',timeout))
 monkeypatch.setattr(batch.os,'killpg',lambda pid,sig:calls.append(('kill',pid,sig)))
 batch.cleanup_owned(Child());assert calls==[('kill',123,batch.signal.SIGKILL),('wait',10)]


def test_sigterm_enters_cleanup_path_and_restores_handler(monkeypatch,tmp_path):
 handlers={sig:object() for sig in (batch.signal.SIGTERM,batch.signal.SIGINT)};original=handlers.copy()
 monkeypatch.setattr(batch.signal,'getsignal',handlers.__getitem__)
 monkeypatch.setattr(batch.signal,'signal',lambda sig,fn:handlers.__setitem__(sig,fn))
 monkeypatch.setattr(batch,'_run',lambda *args:handlers[batch.signal.SIGTERM](batch.signal.SIGTERM,None))
 with pytest.raises(RuntimeError,match='interrupted'):batch.run(tmp_path/'plan.json','sha')
 assert handlers==original
