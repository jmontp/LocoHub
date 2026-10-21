"""Synthetic container prefixes only, not native MATLAB table validation."""
import struct
import zlib
import pytest
from contributor_tools.inspect_gt23_transform_container import inspect


def source(tmp_path,body):
    header=b'MATLAB 5.0 MAT-file'.ljust(124,b' ')+b'\x00\x01IM'
    path=tmp_path/'source.mat';path.write_bytes(header+body);return path


def element(payload):
    compressed=zlib.compress(payload)
    return struct.pack('<II',15,len(compressed))+compressed


def test_unpadded_entries_and_decompression_bound(tmp_path):
    matrix=struct.pack('<IIIIII',14,1000000,6,8,17,0)+b'Transforms MCOS table'+b'x'*1000000
    p=source(tmp_path,element(matrix)+element(matrix))
    r=inspect(p)
    assert len(r['entries'])==2 and all(x['prefix_bytes']==1024 for x in r['entries'])
    assert all(x['matrix_class_id']==17 for x in r['entries'])
    assert r['scientific_arrays_loaded'] is False and r['source_full_hash_checked'] is False
    assert r['read_bytes']<=128+2*(4096+8)


def test_truncated_declared_payload_rejected(tmp_path):
    with pytest.raises(ValueError,match='truncated'):inspect(source(tmp_path,struct.pack('<II',15,100)+b'x'))


def test_wrong_format_no_fallback(tmp_path):
    p=tmp_path/'source.mat';p.write_bytes(b'\x89HDF'+b'\0'*124)
    with pytest.raises(ValueError,match='v5'):inspect(p)
