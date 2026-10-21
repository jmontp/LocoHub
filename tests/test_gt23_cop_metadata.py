"""Metadata fixtures plus separately scheduled tiny Arrow serialization tests."""
import importlib.util
import json
from pathlib import Path
import pytest

p=Path(__file__).resolve().parents[1]/'contributor_tools/annotate_gt23_cop_frame.py'
s=importlib.util.spec_from_file_location('gt23_cop_metadata',p)
FIX=importlib.util.module_from_spec(s);s.loader.exec_module(FIX)


def test_metadata_preserves_unrelated_fields_and_documents_no_origin_shift():
    before={'speed_m_s':1.2,'gt23_force_frame':{'source_coordinate_frame':'global'}}
    after=json.loads(FIX.annotate_metadata(json.dumps(before)))
    assert after.pop('gt23_cop_frame')==FIX.COP_INFO
    assert after==before
    assert 'not established as anatomical ankle' in FIX.COP_INFO['origin']


@pytest.mark.parametrize('raw',['[]','{"cop_origin":"ankle"}','{"gt23_cop_frame":{}}','{"frames":{"cop":"ankle"}}'])
def test_existing_cop_metadata_requires_review(raw):
    with pytest.raises(ValueError):FIX.annotate_metadata(raw)


@pytest.mark.parametrize('clock',['time_s','phase_ipsi'])
def test_arrow_roundtrip_preserves_numerical_bits_and_schema(tmp_path,clock):
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    # Include a non-default NaN payload, signed zeros and actual nulls.
    floats=pa.array(([0x8000000000000000,0,0x7ff8000000000001,None,0x3ff0000000000000]*103),type=pa.uint64()).view(pa.float64())
    table=pa.table({'task_info':['{"task":"synthetic"}']*515,clock:list(range(515)),
                    'cop_anterior_ipsi_m':floats,'knee_flexion_angle_ipsi_rad':floats,
                    'subject':pa.array(['A']*514+[None]).dictionary_encode()})
    schema=pa.schema([f.with_metadata({b'preserve':b'field'}) for f in table.schema],metadata={b'preserve':b'table'})
    table=table.cast(schema)
    source=tmp_path/'source.parquet';target=tmp_path/'target.parquet'
    pq.write_table(table,source,row_group_size=150)
    assert FIX.annotate_parquet(source,target)==515
    after=pq.read_table(target,use_threads=False);before=pq.read_table(source,use_threads=False)
    FIX.verify_tables(before,after)
    field=after.schema.field('cop_anterior_ipsi_m')
    changed=after.set_column(after.schema.get_field_index(field.name),field,pa.array([0.]*515))
    with pytest.raises(ValueError):FIX.verify_tables(before,changed)
    with pytest.raises(FileExistsError):FIX.annotate_parquet(source,target)
