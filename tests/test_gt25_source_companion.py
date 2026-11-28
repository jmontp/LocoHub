"""Tiny synthetic byte/value fixtures; never evidence of full scientific release."""
import gzip,hashlib,json,math
from pathlib import Path
import pytest
import pyarrow as pa
pa.set_cpu_count(1)
pa.set_io_thread_count(1)
from contributor_tools import preserve_gt25_source_companion as writer
from contributor_tools import audit_gt25_source_companion as audit


def fixture(tmp_path,bom=False,infinities=False):
 source=tmp_path/'source.csv';source.write_bytes(b'time,hip_flexion_l,ankle_angle_r\r\n10.125,-0,NaN\r\n10.13,1.25,\r\n10.135,-2.5,3.0\r\n')
 if bom:source.write_bytes(b'\xef\xbb\xbf'+source.read_bytes())
 if infinities:source.write_bytes(source.read_bytes().replace(b'1.25',b'Inf').replace(b'-2.5',b'-Inf'))
 header=source.read_bytes().splitlines(keepends=True)[0]
 columns=[{'source_name':n,'proposed_alias':'source_angle__'+n,'source_unit':u,'status':'documented_source_unit'} for n,u in [('time','s'),('hip_flexion_l','deg'),('ankle_angle_r','deg')]]
 profile={'header_sha256':hashlib.sha256(header).hexdigest(),'columns':columns}
 record={'kind':'angle','path':str(source),'bytes':source.stat().st_size,'mtime_ns':source.stat().st_mtime_ns}
 output=tmp_path/'out';output.mkdir();identity={'subject':'SYNTHETIC','recording':'original_unsplit','source_recording_id':'synthetic:original_unsplit'}
 readme='angle.csv: raw angles\n\ttime (sec)\n\thip_flexion_<side> (deg)\n\tankle_angle_<side> (deg)\n'
 report=writer.preserve_stream(record,profile,output,identity,lambda:None)
 return source,output,identity,readme,report


def test_byte_exact_crlf_nan_null_signedzero_and_original_clock(tmp_path):
 source,out,identity,readme,report=fixture(tmp_path)
 assert gzip.decompress((out/report['compressed']).read_bytes())==source.read_bytes()
 result=audit.check_stream(source,out/report['compressed'],out/report['parquet'],'angle',identity,readme)
 assert result['rows']==3 and result['literal_csv_bytes_equal']
 assert result['missing_values_by_column']['source_angle__ankle_angle_r']==2
 assert result['source_clock_diagnostics']=={'nonfinite':0,'duplicates':0,'decreases':0}


@pytest.mark.parametrize('defect',['value','missing_mask','rowindex','identity','units','header'])
def test_independent_readback_rejects_corruption(tmp_path,defect):
 import pyarrow as pa
 import pyarrow.parquet as pq
 source,out,identity,readme,report=fixture(tmp_path);path=out/report['parquet'];table=pq.ParquetFile(path).read(use_threads=False)
 if defect in ('value','missing_mask','rowindex'):
  name={'value':'source_angle__hip_flexion_l','missing_mask':'source_angle__ankle_angle_r','rowindex':'source_row_index'}[defect]
  values=table[name].to_pylist();values[0]=99 if defect!='missing_mask' else None
  table=table.set_column(table.schema.get_field_index(name),table.schema.field(name),pa.array(values,type=table[name].type))
 elif defect=='identity':identity={**identity,'subject':'OTHER'}
 elif defect=='units':readme=readme.replace('(deg)','(rad)')
 else:
  table=table.rename_columns(['source_row_index','source_angle__time','WRONG','source_angle__ankle_angle_r'])
 pq.write_table(table,path)
 with pytest.raises((ValueError,KeyError)):audit.check_stream(source,out/report['compressed'],path,'angle',identity,readme)


def test_literal_byte_corruption_caught_even_when_numeric_values_same(tmp_path):
 source,out,identity,readme,report=fixture(tmp_path)
 (out/report['compressed']).write_bytes(gzip.compress(source.read_bytes().replace(b'1.25',b'1.250')))
 with pytest.raises(ValueError,match='byte-identical'):audit.check_stream(source,out/report['compressed'],out/report['parquet'],'angle',identity,readme)


def test_source_units_independent_readme_unknown_interaction():
 text='exo.csv: source\n\thip_angle_<side>_torque_measured (Nm)\n\tinsole_<side>_cop_x (unitless)\n'
 assert audit.expected_unit(text,'exo','hip_angle_l_torque_measured')=='Nm'
 assert audit.expected_unit(text,'exo','hip_angle_l_torque_interaction') is None
 assert audit.expected_unit(text,'exo','insole_l_cop_x')=='unitless'


def test_each_stream_retains_its_own_clock_and_invalid_clock_diagnostics(tmp_path):
 source,out,identity,readme,report=fixture(tmp_path)
 # A new independent synthetic source has duplicate/decreasing clock samples; preserve, do not repair.
 source2=tmp_path/'other.csv';source2.write_bytes(source.read_bytes().replace(b'10.13,',b'10.125,').replace(b'10.135,',b'9.0,'))
 import pyarrow as pa
 import pyarrow.parquet as pq
 t=pq.ParquetFile(out/report['parquet']).read(use_threads=False);t=t.set_column(1,t.schema.field(1),pa.array([10.125,10.125,9.]));path=out/'other.parquet';pq.write_table(t,path)
 compressed=out/'other.csv.gz';compressed.write_bytes(gzip.compress(source2.read_bytes()))
 result=audit.check_stream(source2,compressed,path,'angle',identity,readme)
 assert result['source_clock_diagnostics']=={'nonfinite':0,'duplicates':1,'decreases':1}


def test_full_batch_receipt_gate_rejects_missing_stream_or_false_flags():
 from contributor_tools.run_gt25_source_companion_batch import receipt_gate
 r={'status':'all15_source_streams_lossless_readback_checked_unreviewed','scientific_approval':False,'canonical_dataset_approval':False,'subject':'SYNTHETIC','recording':'record','streams':[{'kind':str(i),'rows':3,'literal_csv_bytes_equal':True,'every_numeric_value_and_missing_mask_checked':True,'source_header_and_units_checked':True} for i in range(15)]}
 receipt_gate(r,'SYNTHETIC','record')
 r['streams'][0]['literal_csv_bytes_equal']=False
 with pytest.raises(ValueError):receipt_gate(r,'SYNTHETIC','record')
 r['streams']=r['streams'][1:]
 with pytest.raises(ValueError):receipt_gate(r,'SYNTHETIC','record')


@pytest.mark.parametrize('bom',[False,True])
def test_infinities_are_preserved_and_all_source_rows_accounted(tmp_path,bom):
 source,out,identity,readme,report=fixture(tmp_path,bom=bom,infinities=True)
 result=audit.check_stream(source,out/report['compressed'],out/report['parquet'],'angle',identity,readme)
 name='source_angle__hip_flexion_l'
 assert result['positive_infinity_by_column'][name]==1 and result['negative_infinity_by_column'][name]==1
 for column in result['finite_values_by_column']:
  assert sum(result[k][column] for k in ['finite_values_by_column','missing_values_by_column','positive_infinity_by_column','negative_infinity_by_column'])==3
 assert gzip.decompress((out/report['compressed']).read_bytes())==source.read_bytes()
