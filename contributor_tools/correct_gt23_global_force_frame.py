"""Explicitly scheduled, streaming correction of legacy GT23 force-frame labels.

Accepts time or phase Parquet from the reviewed converter lineage. Never rotates
forces, changes joint signs, or treats source preservation as anatomical approval.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import struct

ROOT=Path(__file__).resolve().parents[1]
CONVERTER=ROOT/'contributor_tools/conversion_scripts/Gtech_2023/convert_gtech_2023_time_to_parquet.m'
CONVERTER_SHA256='8de9c1ae8938423be9f918720a3b0dfaab396f99bc6950fa47c18557d69fd69e'
PAPER_SHA256='5c30a9035c70bc7a1d1041373623cc2e69d4d2caba3a71d1a0ee16f0d1f72baa'
ALIASES={f'grf_{direction}_{side}_BW':f'source_grf_global_{axis}_{side}_BW'
         for side in ('ipsi','contra') for direction,axis in [('anterior','x'),('lateral','z')]}
FRAME_INFO={
    'source':'GroundFrame_GRFs.csv',
    'source_coordinate_frame':'global',
    'source_horizontal_axes':['X','Z'],
    'source_vertical_axis':'Y',
    'unit':'BW; existing normalization retained, not independently revalidated',
    'anatomical_horizontal_status':'unavailable; no orientation rotation established',
    'evidence_doi':'10.1038/s41597-023-02840-6',
    'evidence_location':'Table 3, _grf.csv row',
    'paper_xml_sha256':PAPER_SHA256,
}


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def frame_metadata(raw):
    info=json.loads(raw)
    if not isinstance(info,dict) or 'gt23_force_frame' in info:
        raise ValueError('Missing task metadata object or existing correction')
    info['gt23_force_frame']=FRAME_INFO
    return json.dumps(info,sort_keys=True,allow_nan=False)


def corrected_columns(columns):
    """Pure small-fixture transformation; source arrays remain identical objects."""
    if not set(ALIASES)<=set(columns) or set(ALIASES.values())&set(columns):
        raise ValueError('Missing source fields or existing source aliases')
    result=dict(columns)
    for original,alias in ALIASES.items():
        result[alias]=columns[original]
        result[original]=[None]*len(columns[original])
    result['task_info']=[frame_metadata(raw) for raw in columns['task_info']]
    return result


def same_values(left,right):
    if len(left)!=len(right):return False
    for a,b in zip(left,right):
        if isinstance(a,float) and isinstance(b,float):
            if math.isnan(a) and math.isnan(b):continue
            if struct.pack('!d',a)!=struct.pack('!d',b):return False
        elif a!=b:return False
    return True


def verify_columns(original,corrected):
    if set(corrected)!=set(original)|set(ALIASES.values()):
        raise ValueError('Unexpected output columns')
    count=len(original['task_info'])
    if any(len(values)!=count for values in original.values()) or any(len(values)!=count for values in corrected.values()):
        raise ValueError('Readback row count mismatch')
    for name,values in original.items():
        if name in ALIASES:
            if any(v is not None for v in corrected[name]):raise ValueError('Unsupported anatomical force remains')
            if not same_values(values,corrected[ALIASES[name]]):raise ValueError('Source values or missing mask changed')
        elif name=='task_info':
            for before,after in zip(values,corrected[name]):
                info=json.loads(after)
                if info.pop('gt23_force_frame',None)!=FRAME_INFO or info!=json.loads(before):
                    raise ValueError('Unrelated task metadata changed')
        elif not same_values(values,corrected[name]):raise ValueError('Unrelated column changed: '+name)


def transform_table(table):
    """Keep unchanged Arrow arrays and field metadata intact."""
    import pyarrow as pa
    if not set(ALIASES)<=set(table.column_names) or set(ALIASES.values())&set(table.column_names):
        raise ValueError('Unsupported schema')
    for name,alias in ALIASES.items():
        field=table.schema.field(name)
        if not pa.types.is_floating(field.type):raise ValueError('Force columns must be floating point')
        metadata=dict(field.metadata or {})
        metadata[b'coordinate_frame']=b'global'
        table=table.append_column(pa.field(alias,field.type,nullable=field.nullable,metadata=metadata),table[name])
        table=table.set_column(table.schema.get_field_index(name),field.with_nullable(True),pa.nulls(table.num_rows,type=field.type))
    field=table.schema.field('task_info')
    values=pa.array([frame_metadata(raw) for raw in table['task_info'].to_pylist()],type=field.type)
    return table.set_column(table.schema.get_field_index('task_info'),field,values)


def verify_tables(before,after):
    if after.schema.names!=before.schema.names+list(ALIASES.values()) or before.schema.metadata!=after.schema.metadata:
        raise ValueError('Schema order or metadata changed')
    for field in before.schema:
        expected=field.with_nullable(True) if field.name in ALIASES else field
        if not expected.equals(after.schema.field(field.name),check_metadata=True):raise ValueError('Field metadata changed')
        if field.name in ALIASES:
            metadata=dict(field.metadata or {});metadata[b'coordinate_frame']=b'global'
            alias=after.schema.field(ALIASES[field.name])
            if alias.type!=field.type or alias.metadata!=metadata or alias.nullable!=field.nullable:
                raise ValueError('Source alias metadata changed')
    verify_columns(before.to_pydict(),after.to_pydict())


def correct_parquet(source_path,target):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from itertools import zip_longest
    source=pq.ParquetFile(source_path);writer=None;rows=0
    try:
        for batch in source.iter_batches(batch_size=512,use_threads=False):
            if batch.nbytes>8*1024**2:raise MemoryError('Batch exceeds 8 MiB admission')
            table=transform_table(pa.Table.from_batches([batch]))
            if writer is None:writer=pq.ParquetWriter(target,table.schema,compression='zstd')
            writer.write_table(table,row_group_size=512);rows+=len(batch)
    finally:
        if writer is not None:writer.close()
    if not rows:raise ValueError('Empty input is not a successful correction')
    checked=0
    for before,after in zip_longest(source.iter_batches(batch_size=512,use_threads=False),
                                   pq.ParquetFile(target).iter_batches(batch_size=512,use_threads=False)):
        if before is None or after is None:raise ValueError('Readback length mismatch')
        verify_tables(before,after);checked+=len(before)
    return checked


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--input-sha256',required=True)
    parser.add_argument('--lineage',type=Path,required=True,
                        help='Reviewed JSON binding input_sha256 and converter_sha256')
    parser.add_argument('--lineage-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True,help='Fresh local correction directory')
    args=parser.parse_args()
    for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[name]='1'
    import resource
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
    out=args.output.resolve()
    if not out.is_relative_to(ROOT/'converted_datasets/reconversion_v2'):raise ValueError('Output outside local review root')
    bindings={str(args.input):args.input_sha256,str(args.lineage):args.lineage_sha256,
              str(CONVERTER):CONVERTER_SHA256,str(Path(__file__).resolve()):digest(__file__)}
    def verify_bindings():
        for path,expected in bindings.items():
            if digest(path)!=expected:raise ValueError('Changed bound input: '+path)
    verify_bindings()
    lineage=json.loads(args.lineage.read_text())
    if lineage['input_sha256']!=args.input_sha256 or lineage['converter_sha256']!=CONVERTER_SHA256:
        raise ValueError('Unreviewed converter lineage')
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    source=pq.ParquetFile(args.input)
    if not set(ALIASES)<=set(source.schema_arrow.names) or set(ALIASES.values())&set(source.schema_arrow.names):
        raise ValueError('Unsupported schema')
    if any(not pa.types.is_floating(source.schema_arrow.field(name).type) for name in ALIASES):
        raise ValueError('Force columns must be floating point')
    out.mkdir(parents=True,exist_ok=False)
    target=out/'corrected.parquet'
    checked=correct_parquet(args.input,target)
    verify_bindings()
    report={'status':'global_force_labels_corrected_source_preserved_unreviewed','scientific_approval':False,
            'rows_checked':checked,'input_sha256':bindings,'output_sha256':digest(target),
            'aliases':ALIASES,'frame':FRAME_INFO,
            'unchanged_scope':'Joint signs, vertical force, COP, timing, identities and existing missing masks outside the four withheld anatomical horizontal columns.',
            'limitations':'Input lineage is explicitly reviewer supplied. No raw source, body-weight normalization, COP origin, joint sign or anatomical rotation validation is claimed.'}
    (out/'correction_readback.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
