"""Synthetic original bytes; no scientific CSV loaded."""
import gzip
import zlib
import pytest
from contributor_tools.preserve_gt23_full_source_channels import preserve_file


def test_lossless_source_signed_zero_nan_clock_and_exact_csv_bytes(tmp_path):
    raw=b'time,signal\r\n0.01,-0.0\r\n0.03,NaN\r\n0.031,\r\n'
    src=tmp_path/'source.csv';src.write_bytes(raw);dst=tmp_path/'source.csv.gz'
    r=preserve_file(src,dst,{'uncompressed_size':len(raw),'crc32':zlib.crc32(raw)})
    assert gzip.decompress(dst.read_bytes())==raw and src.read_bytes()==raw
    assert r['source_sha256']==r['lossless_readback_sha256']
    with pytest.raises(FileExistsError):preserve_file(src,dst,{'uncompressed_size':len(raw),'crc32':zlib.crc32(raw)})


def test_publisher_crc_mismatch_not_passing(tmp_path):
    src=tmp_path/'source';src.write_bytes(b'a,b\n1,2\n')
    with pytest.raises(ValueError,match='publisher'):preserve_file(src,tmp_path/'out.gz',{'uncompressed_size':8,'crc32':0})


def test_resource_refusal_before_output_creation(tmp_path):
    src=tmp_path/'source';src.write_bytes(b'abc')
    def guard():raise MemoryError('synthetic low headroom')
    with pytest.raises(MemoryError):preserve_file(src,tmp_path/'out.gz',{'uncompressed_size':3,'crc32':zlib.crc32(b'abc')},guard)
    assert not (tmp_path/'out.gz').exists()


def test_record_validation_precedes_directory_creation(tmp_path):
    from contributor_tools.preserve_gt23_full_source_channels import preserve_record
    from contributor_tools.plan_gt23_full_source_restoration import CHANNELS
    r={'subject':'AB01','recording':'one','publisher_files':[{'name':f'AB01/CSV_Data/one/{c}'} for c in CHANNELS]}
    r['publisher_files'].append(r['publisher_files'][0])
    with pytest.raises(ValueError):preserve_record(tmp_path,r,tmp_path/'out')
    assert not (tmp_path/'out').exists()
    r['publisher_files'].pop();r['recording']='..'
    for member in r['publisher_files']:member['name']=member['name'].replace('/one/','/../')
    with pytest.raises(ValueError):preserve_record(tmp_path,r,tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_interrupted_guard_retains_partial_output_but_no_receipt(tmp_path):
    src=tmp_path/'source';src.write_bytes(b'a'*(1024**2+3));target=tmp_path/'partial.gz';calls=0
    def guard():
        nonlocal calls
        calls+=1
        if calls==3:raise MemoryError('Synthetic interrupted scan')
    with pytest.raises(MemoryError):preserve_file(src,target,{'uncompressed_size':src.stat().st_size,'crc32':zlib.crc32(src.read_bytes())},guard)
    assert target.exists() and src.exists()


def test_source_mutation_during_guard_fails(tmp_path):
    src=tmp_path/'source';src.write_bytes(b'abc');calls=0
    def guard():
        nonlocal calls
        calls+=1
        if calls==2:src.write_bytes(b'xyz')
    with pytest.raises(ValueError,match='changed'):preserve_file(src,tmp_path/'out.gz',{'uncompressed_size':3,'crc32':zlib.crc32(b'abc')},guard)


def test_corrupted_persisted_readback_is_rejected(tmp_path,monkeypatch):
    import io
    from contributor_tools import preserve_gt23_full_source_channels as m
    src=tmp_path/'source';src.write_bytes(b'abc')
    monkeypatch.setattr(m.gzip,'open',lambda *a,**k:io.BytesIO(b'wrong bytes'))
    with pytest.raises(ValueError,match='readback'):m.preserve_file(src,tmp_path/'out.gz',{'uncompressed_size':3,'crc32':zlib.crc32(b'abc')})
