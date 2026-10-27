"""Synthetic Arrow persistence fixtures; run only in the numerical test slot."""
import pytest


def fixture_table():
    import pyarrow as pa
    from contributor_tools.preserve_um21_planar_estimates import FIELDS
    values=[.125,None,float('nan'),-0.]+[.25]*146
    arrays={name:pa.array(values,type=pa.float64()) for name in FIELDS}
    for name,value in {'subject':'SYNTHETIC','source_recording_id':'synthetic/trial','observation_id':'synthetic-cycle','reference_side':'left','observation_type':'individual_cycle','task':'level_walking','task_id':'synthetic','task_info':'{}'}.items():
        arrays[name]=pa.array([value]*150)
    arrays['phase_ipsi']=pa.array([100.*i/149 for i in range(150)])
    arrays['source_ankle_sagittal_angle_ipsi_rad']=pa.array(values)
    arrays['ankle_dorsiflexion_angle_ipsi_rad']=pa.array([None]*150,type=pa.float64())
    table=pa.table(arrays).replace_schema_metadata({b'provenance':b'synthetic source'})
    index=table.schema.get_field_index(FIELDS[0]);field=table.schema.field(index).with_metadata({b'units':b'rad'})
    return table.set_column(index,field,table.column(index))


def test_persisted_exact_values_metadata_and_masks(tmp_path):
    import pyarrow.parquet as pq
    from contributor_tools.preserve_um21_planar_estimates import transform_table,verify_shard
    table=fixture_table();a=tmp_path/'before.parquet';b=tmp_path/'after.parquet'
    pq.write_table(table,a);pq.write_table(transform_table(table),b)
    checked=verify_shard(a,b,set(),lambda:None)
    assert checked['observations']==1 and checked['persisted_exact_preservation']


@pytest.mark.parametrize('fault',['unrelated_value','source_null','canonical','alias_metadata','schema_metadata'])
def test_persisted_corruption_rejected(tmp_path,fault):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from contributor_tools.preserve_um21_planar_estimates import transform_table,verify_shard,FIELDS,MAPPING
    table=fixture_table();changed=transform_table(table)
    name='source_ankle_sagittal_angle_ipsi_rad'
    if fault in ('unrelated_value','source_null'):
        values=changed[name].to_pylist();values[0 if fault=='unrelated_value' else 1]=9.
        i=changed.schema.get_field_index(name);changed=changed.set_column(i,changed.schema.field(i),pa.array(values))
    elif fault=='canonical':
        i=changed.schema.get_field_index(FIELDS[0]);changed=changed.set_column(i,changed.schema.field(i),pa.array([0.]*150))
    elif fault=='alias_metadata':
        i=changed.schema.get_field_index(MAPPING[FIELDS[0]]);changed=changed.set_column(i,changed.schema.field(i).with_metadata({b'bad':b'value'}),changed.column(i))
    else:changed=changed.replace_schema_metadata({b'bad':b'value'})
    a=tmp_path/'before.parquet';b=tmp_path/'after.parquet';pq.write_table(table,a);pq.write_table(changed,b)
    with pytest.raises(ValueError):verify_shard(a,b,set(),lambda:None)
