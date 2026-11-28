"""Small independent checks for native inventory, admission and immutable resume."""
import json
from pathlib import Path
import pytest
from contributor_tools import run_gt21_native_batch as batch


def test_inventory_includes_all_present_subjects_and_dates(tmp_path):
    for subject,date,mode in [('AB27','01_01_20','ramp'),('AB27','02_01_20','stair'),('AB06','10_09_18','levelground')]:
        folder=tmp_path/subject/date/mode/'conditions';folder.mkdir(parents=True)
        (folder/'recording.mat').write_bytes(b'fixture')
    records=batch.inventory(tmp_path)
    assert len(records)==3
    assert {r['subject'] for r in records}=={'AB06','AB27'}
    assert len({r['date'] for r in records if r['subject']=='AB27'})==2


def test_native_resume_requires_exact_outputs_and_code(tmp_path):
    path=tmp_path/'phase.parquet';path.write_bytes(b'immutable fixture')
    sources=[{'source':'version1'}];code=[{'code':'version1'}]
    manifest={'status':'converted_unreviewed','sources':sources,'code':code,'outputs':[{'name':path.name,'sha256':batch.digest(path)}]}
    assert batch.resume_matches(manifest,sources,code,tmp_path)
    assert not batch.resume_matches(manifest,sources,[{'code':'version2'}],tmp_path)
    path.write_bytes(b'changed')
    assert not batch.resume_matches(manifest,sources,code,tmp_path)
    path.unlink()
    assert not batch.resume_matches(manifest,sources,code,tmp_path)


def test_native_source_admission_requires_both_event_streams(tmp_path):
    record={'subject':'AB06','date':'date','mode':'ramp','recording':'trial.mat'}
    (tmp_path/'SubjectInfo.mat').write_bytes(b'fixture')
    for channel in ['conditions','ik_offset','id','gcRight']:
        folder=tmp_path/'AB06/date/ramp'/channel;folder.mkdir(parents=True)
        (folder/'trial.mat').write_bytes(b'fixture')
    with pytest.raises(ValueError,match='gcLeft'):
        batch.source_files(tmp_path,record)
    folder=tmp_path/'AB06/date/ramp/gcLeft';folder.mkdir()
    (folder/'trial.mat').write_bytes(b'fixture')
    assert len(batch.source_files(tmp_path,record))==6


def test_native_paths_reject_c_backed_outputs():
    with pytest.raises(ValueError,match='must be on S'):
        batch.windows_path('/tmp/output.parquet')
    assert batch.windows_path('/mnt/s/review/data.parquet')=='S:\\review\\data.parquet'


def test_native_source_compression_roundtrips_exactly(tmp_path):
    import gzip
    source=tmp_path/'source_ik_data.csv'
    original=b'time,angle\r\n0,0.123456789012345\r\n1,NaN\r\n'
    source.write_bytes(original)
    checksum=batch.digest(source)
    result=batch.compress_source_tables(tmp_path)
    assert result==[{'name':'source_ik_data.csv.gz','uncompressed_sha256':checksum}]
    assert not source.exists()
    assert gzip.decompress((tmp_path/'source_ik_data.csv.gz').read_bytes())==original
