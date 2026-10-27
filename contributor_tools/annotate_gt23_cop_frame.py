"""Streaming metadata-only GT23 COP provenance correction; coordinator scheduled.

No anatomical reorientation, joint sign change, origin offset or source aliases.
Only task_info changes. Input must have reviewed original native-run lineage.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LINEAGE_HELPER=ROOT/'contributor_tools/correct_gt23_global_force_frame.py'
LINEAGE_HELPER_SHA256='5070fbf5a7960a977834065c69d22d822c28cfe0788f78b772f48099db0315bc'
COP_INFO={
    'source':'GroundFrame_GRFs.csv plus Transforms calcn_l/calcn_r',
    'frame':'calcn body frame from the supplied transform table',
    'origin':'calcn transform translation; not established as anatomical ankle',
    'calculation':'R_calcn_transpose * (COP_global - calcn_translation)',
    'axis_mapping':{'anterior':'local X','vertical':'local Y','lateral':'local Z'},
    'units':'m',
    'processing':'Existing time/phase interpolation and contact masks retained without changes',
    'anatomical_status':'Model variant, anatomical axes and ankle-origin correspondence remain unapproved',
    'evidence_doi':'10.1038/s41597-023-02840-6',
    'evidence_location':'Methods/Data Records and Table 3; reviewed native converter expressions',
    'insole_distinction':'These values are not copied from the separate published simulated-insole output',
}


def lineage_helper():
    import hashlib
    if hashlib.sha256(LINEAGE_HELPER.read_bytes()).hexdigest()!=LINEAGE_HELPER_SHA256:
        raise ValueError('Pinned lineage helper changed')
    spec=importlib.util.spec_from_file_location('gt23_frozen_force_lineage',LINEAGE_HELPER)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def annotate_metadata(raw):
    info=json.loads(raw)
    if not isinstance(info,dict):raise ValueError('Task metadata must be an object')
    def has_cop(value):
        if isinstance(value,dict):
            return any(str(k).lower().startswith(('cop','gt23_cop','center_of_pressure')) or has_cop(v) for k,v in value.items())
        if isinstance(value,list):return any(has_cop(v) for v in value)
        return False
    if has_cop(info):raise ValueError('Existing COP metadata requires explicit reconciliation')
    info['gt23_cop_frame']=COP_INFO
    return json.dumps(info,sort_keys=True,allow_nan=False)


def transform_table(table):
    import pyarrow as pa
    if len(table.column_names)!=len(set(table.column_names)):raise ValueError('Duplicate columns')
    field=table.schema.field('task_info')
    if not (pa.types.is_string(field.type) or pa.types.is_large_string(field.type)):
        raise ValueError('Task metadata must be a string column')
    values=pa.array([annotate_metadata(raw) for raw in table['task_info'].to_pylist()],type=field.type)
    return table.set_column(table.schema.get_field_index('task_info'),field,values)


def verify_tables(before,after):
    import pyarrow as pa
    if before.num_rows!=after.num_rows or not before.schema.equals(after.schema,check_metadata=True):
        raise ValueError('Rows or schema metadata changed')
    for field in before.schema:
        left=before[field.name].combine_chunks();right=after[field.name].combine_chunks()
        if not left.is_null().equals(right.is_null()):raise ValueError('Null mask changed: '+field.name)
        if field.name=='task_info':
            expected=[annotate_metadata(raw) for raw in left.to_pylist()]
            if expected!=right.to_pylist():raise ValueError('Unrelated task metadata changed')
        elif pa.types.is_floating(field.type):
            # Integer views retain NaN payloads and signed zeros at valid samples.
            dtype={16:pa.uint16(),32:pa.uint32(),64:pa.uint64()}[field.type.bit_width]
            if not left.view(dtype).equals(right.view(dtype)):
                raise ValueError('Numerical bits changed: '+field.name)
        elif not left.equals(right):raise ValueError('Unrelated values changed: '+field.name)


def annotate_parquet(source_path,target):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from itertools import zip_longest
    if Path(target).exists():raise FileExistsError('Output already exists')
    source=pq.ParquetFile(source_path);writer=None;rows=0
    try:
        for batch in source.iter_batches(batch_size=512,use_threads=False):
            if batch.nbytes>8*1024**2:raise MemoryError('Batch exceeds 8 MiB admission')
            table=transform_table(pa.Table.from_batches([batch]))
            if writer is None:writer=pq.ParquetWriter(target,table.schema,compression='zstd')
            writer.write_table(table,row_group_size=512);rows+=len(batch)
    finally:
        if writer is not None:writer.close()
    if not rows:raise ValueError('Empty input')
    for before,after in zip_longest(source.iter_batches(batch_size=512,use_threads=False),
                                   pq.ParquetFile(target).iter_batches(batch_size=512,use_threads=False)):
        if before is None or after is None:raise ValueError('Output length changed')
        verify_tables(pa.Table.from_batches([before]),pa.Table.from_batches([after]))
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--input-sha256',required=True)
    parser.add_argument('--lineage',type=Path,required=True)
    parser.add_argument('--lineage-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[key]='1'
    import resource
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
    helper=lineage_helper()
    bindings={str(args.input):args.input_sha256,str(args.lineage):args.lineage_sha256,
              str(LINEAGE_HELPER):LINEAGE_HELPER_SHA256,str(Path(__file__).resolve()):helper.digest(__file__)}
    def verify():
        for path,expected in bindings.items():
            if helper.digest(path)!=expected:raise ValueError('Bound evidence changed: '+path)
    verify();lineage=json.loads(args.lineage.read_text())
    if lineage['input_sha256']!=args.input_sha256:raise ValueError('Wrong original native input lineage')
    evidence=lineage['evidence_sha256']
    if lineage['run_manifest'] not in evidence or lineage['run_driver'] not in evidence:
        raise ValueError('Unbound producing-run evidence')
    bindings.update(evidence);verify()
    producer=helper.validate_lineage(lineage,json.loads(Path(lineage['run_manifest']).read_text()),Path(lineage['run_driver']).read_text())
    bindings[str(ROOT/producer['path'])]=producer['sha256'];verify()
    out=args.output.resolve()
    if not out.is_relative_to(ROOT/'converted_datasets/reconversion_v2'):raise ValueError('Unauthorized output root')
    import pyarrow as pa
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    out.mkdir(parents=True,exist_ok=False);target=out/'annotated.parquet'
    rows=annotate_parquet(args.input,target);verify()
    report={'status':'cop_frame_metadata_added_values_unchanged_unreviewed','scientific_approval':False,
            'rows_checked':rows,'verified_input_sha256':bindings,'output_sha256':helper.digest(target),
            'actual_producing_converter':producer,'cop_metadata':COP_INFO,
            'changes':'Only task_info strings; all other Arrow fields, schema metadata, valid numeric bits and null masks verified unchanged.',
            'limitations':'No anatomical axes, source model variant, body-weight normalization, COP origin offset or joint signs are scientifically approved by this correction.'}
    (out/'cop_metadata_readback.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
