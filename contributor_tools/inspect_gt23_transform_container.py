"""Bounded MAT v5 container metadata inspection; never decodes scientific arrays."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib


def inspect(path):
    path=Path(path);before=path.stat();entries=[];read_bytes=0
    with path.open('rb') as f:
        header=f.read(128);read_bytes+=len(header)
        if len(header)!=128 or not header.startswith(b'MATLAB 5.0 MAT-file') or header[126:128]!=b'IM':
            raise ValueError('Expected little-endian MAT v5 container; no fallback loading')
        offset=128
        while offset<before.st_size:
            if len(entries)>=64:raise ValueError('Container entry limit exceeded')
            f.seek(offset);tag=f.read(8);read_bytes+=len(tag)
            if len(tag)!=8:raise ValueError('Truncated top-level tag')
            kind,size=struct.unpack('<II',tag)
            if kind!=15 or not size or offset+8+size>before.st_size:
                raise ValueError('Unexpected or truncated compressed MAT element')
            payload=f.read(min(size,4096));read_bytes+=len(payload)
            prefix=zlib.decompressobj().decompress(payload,1024)
            if len(prefix)<24 or struct.unpack('<I',prefix[:4])[0]!=14:
                raise ValueError('Missing inner matrix metadata')
            flags=struct.unpack('<I',prefix[16:20])[0]
            entries.append({'offset':offset,'compressed_bytes':size,'prefix_bytes':len(prefix),
                            'prefix_sha256':hashlib.sha256(prefix).hexdigest(),
                            'matrix_payload_bytes':struct.unpack('<I',prefix[4:8])[0],
                            'matrix_class_id':flags&255,'contains_MCOS_label_in_prefix':b'MCOS' in prefix,
                            'contains_Transforms_label_in_prefix':b'Transforms' in prefix,
                            'contains_table_label_in_prefix':b'table' in prefix})
            # MAT compressed elements are not padded to eight bytes.
            offset+=8+size
    after=path.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('Source changed during probe')
    return {'status':'container_metadata_only_not_source_array_validation','scientific_approval':False,
            'source_path':str(path.resolve()),'source_bytes':before.st_size,'source_mtime_ns':before.st_mtime_ns,
            'header_sha256':hashlib.sha256(header).hexdigest(),'format':'MAT v5 compressed little-endian',
            'read_bytes':read_bytes,'maximum_decompressed_prefix_bytes':1024,'entries':entries,
            'source_full_hash_checked':False,'scientific_arrays_loaded':False}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=inspect(a.source)
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
if __name__=='__main__':main()
