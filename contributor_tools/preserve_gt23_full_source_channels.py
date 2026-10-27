"""Lossless GT23 source CSV companions; explicit serial execution only.

Preserves all ten publisher channels with original clocks/strings and units in
source documentation. Compression creates ordinary .csv.gz files, not cycles
or canonical anatomical measurements. No dataframe or native import.
"""
import gzip
import hashlib
import json
import re
from pathlib import Path
import zlib
from contributor_tools.plan_gt23_full_source_restoration import CHANNELS,digest,read


def guarded_digest(path,check_resources):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024**2),b''):
            check_resources();h.update(block)
    return h.hexdigest()


def validate_record(record):
    subject=record['subject'];recording=record['recording'];members=record['publisher_files']
    if not isinstance(subject,str) or not re.fullmatch(r'AB[0-9]{2}',subject):raise ValueError('Unsafe subject identity')
    if not isinstance(recording,str) or recording in ('.','..','') or '/' in recording or '\\' in recording:raise ValueError('Unsafe recording identity')
    names=[]
    for member in members:
        name=member['name'];parts=name.split('/')
        if len(parts)!=4 or any(p in ('','.','..') for p in parts) or '\\' in name or parts[:3]!=[subject,'CSV_Data',recording]:raise ValueError('Unsafe publisher source path')
        names.append(parts[3])
    if len(names)!=10 or len(set(names))!=10 or set(names)!=set(CHANNELS):raise ValueError('Exact ten unique publisher channels required')


def preserve_file(source,target,expected,check_resources=lambda:None):
    source=Path(source);target=Path(target)
    if target.exists():raise FileExistsError('Never overwrite a source companion')
    before=source.stat()
    if before.st_size!=expected['uncompressed_size']:raise ValueError('Publisher member size differs')
    check_resources();h=hashlib.sha256();crc=0;size=0
    with source.open('rb') as src,target.open('xb') as dst:
        with gzip.GzipFile(filename='',mode='wb',fileobj=dst,compresslevel=1,mtime=0) as gz:
            for chunk in iter(lambda:src.read(1024**2),b''):
                check_resources();h.update(chunk);crc=zlib.crc32(chunk,crc);size+=len(chunk);gz.write(chunk)
    after=source.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns) or size!=expected['uncompressed_size'] or crc!=expected['crc32']:raise ValueError('Actual source differs from publisher member or changed')
    restored=hashlib.sha256();restored_size=0
    with gzip.open(target,'rb') as f:
        for chunk in iter(lambda:f.read(1024**2),b''):
            check_resources();restored.update(chunk);restored_size+=len(chunk)
    if restored.hexdigest()!=h.hexdigest() or restored_size!=size:raise ValueError('Lossless persisted companion readback differs')
    compressed_hash=guarded_digest(target,check_resources)
    final=source.stat()
    if (before.st_size,before.st_mtime_ns)!=(final.st_size,final.st_mtime_ns):raise ValueError('Source changed during persisted readback')
    return {'source_path':str(source),'source_sha256':h.hexdigest(),'source_bytes':size,'publisher_crc32':crc,
            'output_path':str(target),'output_sha256':compressed_hash,'lossless_readback_sha256':restored.hexdigest()}


def preserve_record(source_root,record,output,check_resources=lambda:None):
    output=Path(output)
    if output.exists():raise FileExistsError('Fresh record preservation root required')
    validate_record(record)
    output.mkdir(parents=True);files=[]
    for member in record['publisher_files']:
        path=Path(member['name'])
        if path.parts[:3]!=(record['subject'],'CSV_Data',record['recording']) or len(path.parts)!=4:raise ValueError('Source recording path mismatch')
        files.append(preserve_file(Path(source_root)/'RawData'/path,output/(path.name+'.gz'),member,check_resources))
    result={'status':'all_ten_source_channels_losslessly_preserved_unreviewed','scientific_approval':False,
            'subject':record['subject'],'recording':record['recording'],'files':files,
            'scope':'Original continuous CSV clocks and source strings retained. No gait cycles, normalized timing, anatomical signs or units invented.'}
    with (output/'source_readback.json').open('x') as f:json.dump(result,f,indent=2)
    return result
