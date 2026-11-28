"""Metadata-only successor for independently checked GT25 streaming transfers.

Never changes numerical values or asserts a global/anatomical segment frame.
"""
import argparse
import itertools
import json
from pathlib import Path
import resource
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.run_gt25_normalization_pilot_v4 import digest
from contributor_tools.preserve_um21_planar_estimates import exact_value


def metadata(old,task):
    if task not in ('sit_to_stand','stand_to_sit'):raise ValueError('Streaming transfer scope only')
    value=json.loads(old)
    if value.get('segment_angle_method')!='virtual_IMU_integration_with_converter_initialization':raise ValueError('Unknown original segment method')
    value.update(segment_angle_reference='independently standing-zeroed per segment and accepted transfer',segment_zero_reference_samples='last20' if task=='sit_to_stand' else 'first20',segment_integrated_axis='local_body_gyro_z',segment_source_gyro_units='deg/s converted to rad/s before integration',segment_integration_dt='whole-record mean supplied IMU time difference',segment_global_anatomical_orientation='unverified; not established global sagittal orientation',segment_method_availability='method description only; missing IMU remains missing')
    return json.dumps(value,sort_keys=True)


def apply(source,output):
    import pyarrow as pa
    import pyarrow.parquet as pq
    source,output=Path(source),Path(output);before_sha=digest(source)
    if output.exists():raise FileExistsError('Preserve existing output')
    old=pq.ParquetFile(source);writer=None;rows=0
    try:
        for batch in old.iter_batches(batch_size=150,use_threads=False):
            table=pa.Table.from_batches([batch]);values=table.to_pylist()
            if any(r['observation_type']!='transfer' or r['reference_side']!='left' or not r['source_recording_id'].startswith('gt25:Parsed/') for r in values):raise ValueError('Wrong recording scope')
            updated=[metadata(r['task_info'],r['task']) for r in values]
            table=table.set_column(table.schema.get_field_index('task_info'),table.schema.field('task_info'),pa.array(updated,type=pa.string()))
            if writer is None:writer=pq.ParquetWriter(output,old.schema_arrow,compression='zstd')
            writer.write_table(table,row_group_size=150);rows+=batch.num_rows
    finally:
        if writer:writer.close()
    if rows==0 or rows%150:raise ValueError('Incomplete phase observations')
    new=pq.ParquetFile(output)
    if not old.schema_arrow.equals(new.schema_arrow,check_metadata=True):raise ValueError('Schema metadata changed')
    for before,after in itertools.zip_longest(old.iter_batches(batch_size=150,use_threads=False),new.iter_batches(batch_size=150,use_threads=False)):
        if before is None or after is None or before.num_rows!=after.num_rows:raise ValueError('Row coverage changed')
        for name in before.schema.names:
            a=before.column(before.schema.get_field_index(name));b=after.column(after.schema.get_field_index(name))
            if name=='task_info':
                tasks=before.column(before.schema.get_field_index('task')).to_pylist()
                if b.to_pylist()!=[metadata(v,t) for v,t in zip(a.to_pylist(),tasks)]:raise ValueError('Disclosure differs')
            elif not a.is_null().equals(b.is_null()) or not exact_value(a.to_pylist(),b.to_pylist()):raise ValueError('Unrelated values or masks changed: '+name)
    if digest(source)!=before_sha:raise ValueError('Historical source changed')
    report={'status':'transfer_segment_reference_disclosed_exact_preservation_unreviewed','scientific_approval':False,'source':str(source),'source_sha256':before_sha,'output':str(output),'output_sha256':digest(output),'rows':rows,'changed_fields':['task_info'],'all_other_fields_masks_metadata_exact':True,'anatomical_frame_verified':False}
    with Path(str(output)+'.review.json').open('x') as handle:json.dump(report,handle,indent=2)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));print(json.dumps(apply(a.source,a.output)))
if __name__=='__main__':main()
