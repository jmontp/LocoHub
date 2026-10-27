"""Retain unverified GT23 producer interpretations under explicit derived aliases.

This does not reinterpret coordinates. Original full source CSV companions carry
source signals. The aliases here are the previous interpolated producer values,
including its signs/offsets, not a claim that they are raw anatomical measures.
"""
import json
import re
from pathlib import Path
PREFIX='derived_unverified_producer_'
ANNOTATION={'canonical_status':'unavailable','preserved_as':PREFIX+'<original_column>',
 'meaning':'Prior producer interpolation/sign/offset interpretation; not approved anatomical orientation or moment direction.',
 'source_signals':'Use original continuous source CSV companions for source coordinate fields.'}
PATTERN=re.compile(r'^(hip_|knee_|ankle_|pelvis_|trunk_|thigh_|shank_|foot_)')


def mapping(names):
    return {n:PREFIX+n for n in names if PATTERN.match(n) and any(k in n for k in ('_angle_','_velocity_','_acceleration_','_moment_'))}


def transform(table):
    import pyarrow as pa
    pairs=mapping(table.column_names)
    if not pairs or set(pairs.values()) & set(table.column_names):raise ValueError('Missing or conflicting anatomical fields')
    result=table
    for name,alias in pairs.items():
        f=table.schema.field(name)
        if not pa.types.is_floating(f.type):raise ValueError('Expected floating anatomical feature')
        result=result.append_column(pa.field(alias,f.type,metadata=f.metadata),table[name])
        result=result.set_column(result.schema.get_field_index(name),f,pa.nulls(len(table),type=f.type))
    info=[]
    for raw in table['task_info'].to_pylist():
        d=json.loads(raw)
        if 'gt23_unverified_anatomy' in d:raise ValueError('Conflicting anatomy disposition')
        d['gt23_unverified_anatomy']=ANNOTATION.copy()
        info.append(json.dumps(d,sort_keys=True,allow_nan=False))
    f=table.schema.field('task_info');return result.set_column(result.schema.get_field_index('task_info'),f,pa.array(info,type=f.type))


def identical(a,b):
    # Arrow equality does not treat NaNs as equal; compare all scalar bits/nulls.
    import struct
    if a.type!=b.type or len(a)!=len(b):return False
    for x,y in zip(a.to_pylist(),b.to_pylist()):
        if x is None or y is None:
            if x is not y:return False
        elif isinstance(x,float) and isinstance(y,float):
            if struct.pack('>d',x)!=struct.pack('>d',y):return False
        elif x!=y:return False
    return True


def verify(before,after):
    if len(before)!=len(after):raise ValueError('Row count differs')
    pairs=mapping(before.column_names)
    if after.column_names!=before.column_names+list(pairs.values()) or before.schema.metadata!=after.schema.metadata:raise ValueError('Schema/order metadata differs')
    for name in before.column_names:
        if not before.schema.field(name).equals(after.schema.field(name),check_metadata=True):raise ValueError('Source field metadata differs')
        if name in pairs:
            alias=after.schema.field(pairs[name]);original=before.schema.field(name)
            if alias.type!=original.type or alias.metadata!=original.metadata:raise ValueError('Alias field metadata differs')
            if after[name].null_count!=len(after) or not identical(before[name],after[pairs[name]]):raise ValueError('Anatomical preservation differs')
        elif name=='task_info':
            for old,new in zip(before[name].to_pylist(),after[name].to_pylist()):
                expected=json.loads(old);observed=json.loads(new);annotation=observed.pop('gt23_unverified_anatomy',None)
                if observed!=expected or annotation!=ANNOTATION:raise ValueError('Task/force/COP provenance changed')
        elif not identical(before[name],after[name]):raise ValueError('Unrelated values or null masks changed')


def run(source,target,check_resources=lambda:None):
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    source=Path(source);target=Path(target)
    if target.exists():raise FileExistsError('Fresh anatomy disposition output required')
    writer=None;count=0
    try:
        for batch in pq.ParquetFile(source).iter_batches(batch_size=150,use_threads=False):
            check_resources()
            if batch.nbytes>8*1024**2:raise MemoryError('Bounded anatomical preservation batch exceeded')
            table=pa.Table.from_batches([batch]);changed=transform(table);verify(table,changed)
            if writer is None:writer=pq.ParquetWriter(target,changed.schema,compression='zstd')
            writer.write_table(changed,row_group_size=150);count+=len(table)
    finally:
        if writer:writer.close()
    if not count:raise ValueError('Empty corrected source table')
    from itertools import zip_longest
    for a,b in zip_longest(pq.ParquetFile(source).iter_batches(batch_size=150,use_threads=False),pq.ParquetFile(target).iter_batches(batch_size=150,use_threads=False)):
        check_resources()
        if a is None or b is None:raise ValueError('Persisted row count differs')
        verify(pa.Table.from_batches([a]),pa.Table.from_batches([b]))
    return {'status':'source_interpretations_preserved_canonical_anatomy_unavailable','scientific_approval':False,'rows':count}
