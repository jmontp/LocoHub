"""Isolated, serial UM21 labeling-only correction; no scientific approval.

Default prepares a hash-bound plan. --run processes150-row batches, preserving
all unrelated values/metadata and original planar estimates exactly. Requires a
complete explicitly bound scope report; does not redo source conversion.
"""
import argparse
import itertools
import json
import math
import os
from pathlib import Path
import resource
import shutil
import struct
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.um21_planar_field_policy import field_policy
from contributor_tools.preserve_mblue_planar_estimates import digest,headroom,windows_available_mib
FIELDS=tuple(f'{s}_sagittal_angle_{r}_rad' for s in ('thigh','shank') for r in ('ipsi','contra'))
MAPPING=field_policy('streaming_python',FIELDS)['preserve_exactly']


def validate_scope(scope):
    if scope.get('status')!='complete_um21_planar_scope_checked_unreviewed':raise ValueError('Complete scope evidence required')
    if scope.get('producer') not in ('run','tread_components','stairs','boundaries'):raise ValueError('Unsupported producer')
    if not scope.get('baseline_summary_sha256') or not scope.get('evidence_bindings'):raise ValueError('Missing baseline evidence')
    records=scope.get('records',[])
    if not records or len(records)!=scope.get('expected_records'):raise ValueError('Record coverage mismatch')
    seen=set();total=0
    for record in records:
        rel=record['phase_path']
        if rel is None:
            parent=Path(record['record_path'])
            if parent.is_absolute() or '..' in parent.parts or str(parent) in seen:raise ValueError('Invalid empty-record identity')
            seen.add(str(parent))
            if record.get('disposition')!='no_annotated_observations' or record['observations']!=0 or record['rows']!=0 or not record['outputs']:raise ValueError('Missing empty-record disposition')
            for name,sha in record['outputs'].items():
                q=Path(name)
                if q.is_absolute() or '..' in q.parts or q.parent!=parent or q.suffix=='.parquet' or len(sha)!=64:raise ValueError('Invalid empty-record artifact')
            continue
        p=Path(rel)
        if p.is_absolute() or '..' in p.parts or p.name!='phase.parquet' or str(p.parent) in seen:raise ValueError('Unsafe/duplicate phase path')
        seen.add(str(p.parent))
        if not isinstance(record['observations'],int) or record['observations']<=0:raise ValueError('Invalid observation count')
        if record['rows']!=150*record['observations']:raise ValueError('Incomplete phase rows')
        if record['outputs'].get(rel)!=record['phase_sha256']:raise ValueError('Missing phase binding')
        for name,sha in record['outputs'].items():
            q=Path(name)
            if q.is_absolute() or '..' in q.parts or q.parent!=p.parent or not isinstance(sha,str) or len(sha)!=64:raise ValueError('Invalid sidecar binding')
        total+=record['observations']
    if total!=scope.get('expected_observations'):raise ValueError('Observation scope mismatch')
    return records


def transform_table(table):
    import pyarrow as pa
    field_policy('streaming_python',table.column_names)
    if len(set(table.column_names))!=len(table.column_names):raise ValueError('Duplicate columns')
    for name,alias in MAPPING.items():
        field=table.schema.field(name)
        if not pa.types.is_floating(field.type):raise ValueError('UM21 angle fields must be floating')
        metadata=dict(field.metadata or {});metadata[b'interpretation']=b'planar estimate; spatial orientation unverified'
        table=table.append_column(pa.field(alias,field.type,nullable=True,metadata=metadata),table[name])
        table=table.set_column(table.schema.get_field_index(name),field.with_nullable(True),pa.nulls(table.num_rows,type=field.type))
    return table


def exact_value(a,b):
    if type(a) is not type(b):return False
    if isinstance(a,float):return struct.pack('>d',a)==struct.pack('>d',b)
    if isinstance(a,list):return len(a)==len(b) and all(exact_value(x,y) for x,y in zip(a,b))
    if isinstance(a,dict):return a.keys()==b.keys() and all(exact_value(a[k],b[k]) for k in a)
    return a==b


def verify_shard(before_path,after_path,seen,guard):
    import pyarrow.parquet as pq
    from contributor_tools.common.data_contract import inspect_contract
    left,right=pq.ParquetFile(before_path),pq.ParquetFile(after_path)
    if left.metadata.num_rows!=right.metadata.num_rows or left.schema_arrow.metadata!=right.schema_arrow.metadata:raise ValueError('Rows/schema metadata changed')
    count=0
    for a,b in itertools.zip_longest(left.iter_batches(batch_size=150,use_threads=False),right.iter_batches(batch_size=150,use_threads=False)):
        guard()
        if a is None or b is None or a.num_rows!=150:raise ValueError('Incomplete batch coverage')
        if b.schema.names!=a.schema.names+list(MAPPING.values()):raise ValueError('Column order changed')
        for name in a.schema.names:
            alias=MAPPING.get(name,name);av=a.column(a.schema.get_field_index(name));bv=b.column(b.schema.get_field_index(alias))
            if av.is_null().to_pylist()!=bv.is_null().to_pylist() or not exact_value(av.to_pylist(),bv.to_pylist()):raise ValueError('Original value/null mask changed: '+name)
            field=a.schema.field(name)
            if name in MAPPING:
                metadata=dict(field.metadata or {});metadata[b'interpretation']=b'planar estimate; spatial orientation unverified'
                target=b.schema.field(alias)
                if target.type!=field.type or target.metadata!=metadata or not target.nullable:raise ValueError('Estimate field metadata changed')
                if not field.with_nullable(True).equals(b.schema.field(name),check_metadata=True):raise ValueError('Canonical metadata changed')
                if b.column(b.schema.get_field_index(name)).null_count!=150:raise ValueError('Canonical orientation remains populated')
            elif not field.equals(b.schema.field(name),check_metadata=True):raise ValueError('Unrelated field metadata changed')
        identities=a.column(a.schema.get_field_index('observation_id')).to_pylist()
        identity=identities[0]
        if not isinstance(identity,str) or len(set(identities))!=1 or identity in seen:raise ValueError('Duplicate/mixed source observation')
        seen.add(identity)
        if not inspect_contract(b.to_pandas(use_threads=False),mode='phase').schema_passed:raise ValueError('Corrected structural check failed')
        count+=1
    return {'observations':count,'rows':count*150,'persisted_exact_preservation':True,'unrelated_metadata_preserved':True,'source_null_masks_preserved':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path,required=True);parser.add_argument('--scope-report',type=Path,required=True)
    parser.add_argument('--output-root',type=Path,required=True);parser.add_argument('--run',action='store_true')
    args=parser.parse_args();baseline=args.baseline.resolve();out=args.output_root.resolve()
    if not out.is_relative_to((ROOT/'converted_datasets/reconversion_v2').resolve()) or out==baseline:raise ValueError('New authorized output root required')
    scope=json.loads(args.scope_report.read_text());records=validate_scope(scope)
    if Path(scope['baseline_root']).resolve()!=baseline:raise ValueError('Scope baseline root differs')
    summary=baseline/'conversion_summary.json'
    if digest(summary)!=scope['baseline_summary_sha256']:raise ValueError('Baseline summary changed')
    bindings={str(args.scope_report.resolve()):digest(args.scope_report),str(summary):digest(summary),**scope['evidence_bindings']}
    for p in [Path(__file__).resolve(),ROOT/'contributor_tools/um21_planar_field_policy.py',ROOT/'contributor_tools/preserve_mblue_planar_estimates.py',*sorted((ROOT/'contributor_tools/common').rglob('*.py'))]:bindings[str(p)]=digest(p)
    if any(digest(p)!=h for p,h in bindings.items()):raise ValueError('Scope evidence changed')
    plan={'status':'prepared_not_executed','scientific_approval':False,'baseline':str(baseline),'scope_sha256':digest(args.scope_report),'bindings':bindings,'field_mapping':MAPPING,'expected_records':len(records),'expected_observations':scope['expected_observations']}
    planpath=out/'plan.json'
    if out.exists():
        if not planpath.is_file() or any(p.name!='plan.json' for p in out.iterdir()) or json.loads(planpath.read_text())!=plan:raise FileExistsError('Existing attempt/dependencies must be preserved')
    else:
        out.mkdir(parents=True,exist_ok=False);planpath.write_text(json.dumps(plan,indent=2)+'\n')
    if not args.run:print(json.dumps(plan));return
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[k]='1'
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    headroom(out)
    if windows_available_mib()<2816:raise MemoryError('Need768MiB plus2GiB host reserve')
    result={'status':'running','scientific_approval':False,'producer':scope['producer'],'scope':'complete_bound_baseline','bindings':bindings,'field_mapping':MAPPING,'records':[],
        'limitations':['Labeling-only correction; true3D segment reconstruction remains open','Canonical missing signals are unassessed, not passing','Ankle/raw source values and identities unchanged']}
    last_host=0.;seen=set()
    def guard():
        nonlocal last_host
        if time.monotonic()-last_host>=15:
            headroom(out)
            if windows_available_mib()<2048:raise MemoryError('Host reserve below2GiB')
            last_host=time.monotonic()
    def save():
        tmp=out/'planar_preservation_summary.tmp';tmp.write_text(json.dumps(result,indent=2)+'\n');tmp.replace(out/'planar_preservation_summary.json')
    save()
    try:
        for record in records:
            guard();relative=record['phase_path']
            if relative is None:
                outputs={}
                for name,sha in record['outputs'].items():
                    if digest(baseline/name)!=sha:raise ValueError('Empty-record evidence changed')
                    target=out/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(baseline/name,target)
                    if digest(target)!=sha or digest(baseline/name)!=sha:raise ValueError('Empty disposition copy changed')
                    outputs[name]={'sha256':sha,'source_sha256':sha}
                result['records'].append({'phase_path':None,'record_path':record['record_path'],'disposition':record['disposition'],'observations':0,'rows':0,'outputs':outputs});save();continue
            source=baseline/relative;target=out/relative
            for name,sha in record['outputs'].items():
                if digest(baseline/name)!=sha:raise ValueError('Bound baseline artifact changed')
            headroom(out,source.stat().st_size);target.parent.mkdir(parents=True)
            partial=target.with_suffix('.parquet.partial');writer=None
            try:
                for batch in pq.ParquetFile(source).iter_batches(batch_size=150,use_threads=False):
                    guard();table=transform_table(pa.Table.from_batches([batch]))
                    if writer is None:writer=pq.ParquetWriter(partial,table.schema,compression='zstd')
                    writer.write_table(table)
            finally:
                if writer is not None:writer.close()
            checked=verify_shard(source,partial,seen,guard)
            if checked['observations']!=record['observations']:raise ValueError('Shard scope changed')
            outputs={}
            for name,sha in record['outputs'].items():
                if digest(baseline/name)!=sha:raise ValueError('Baseline changed during processing')
                if name!=relative:
                    destination=out/name;shutil.copyfile(baseline/name,destination)
                    if digest(destination)!=sha:raise ValueError('Sidecar copy changed')
                    outputs[name]={'sha256':sha,'source_sha256':sha}
            partial.replace(target);outputs[relative]={'sha256':digest(target),'source_sha256':record['phase_sha256']}
            result['records'].append({**checked,'phase_path':relative,'outputs':outputs});save()
        if len(result['records'])!=scope['expected_records'] or len(seen)!=scope['expected_observations']:raise ValueError('Final scope mismatch')
        if any(digest(p)!=h for p,h in bindings.items()):raise ValueError('Bound evidence changed')
        result.update(status='um21_planar_estimates_preserved_canonical_orientations_withheld_unreviewed',observations=len(seen))
    except Exception as error:result.update(status='failed_incomplete',reason=str(error));raise
    finally:save()


if __name__=='__main__':main()
