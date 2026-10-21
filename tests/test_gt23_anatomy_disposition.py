import json
import pytest


def test_anatomical_aliases_preserve_signed_zero_nan_null_and_other_evidence():
    import pyarrow as pa
    from contributor_tools.withhold_gt23_unverified_anatomy import transform,verify
    original=pa.table({'hip_flexion_angle_ipsi_rad':[-0.,float('nan'),None],
         'grf_vertical_ipsi_BW':[1.,2.,3.], 'source_grf_global_x_ipsi_BW':[.1,.2,.3],
         'task_info':[json.dumps({'gt23_force_frame':{'source_coordinate_frame':'global'},'gt23_cop_frame':{'origin':'calcn'}})]*3})
    changed=transform(original);verify(original,changed)
    assert changed['hip_flexion_angle_ipsi_rad'].null_count==3
    bad=changed.set_column(1,changed.schema.field(1),pa.array([1.,2.,4.]))
    with pytest.raises(ValueError,match='Unrelated'):verify(original,bad)
    alias='derived_unverified_producer_hip_flexion_angle_ipsi_rad'
    bad=changed.set_column(changed.schema.get_field_index(alias),changed.schema.field(alias),pa.array([0.,float('nan'),None]))
    with pytest.raises(ValueError,match='preservation'):verify(original,bad)


def test_truncated_rows_annotation_and_alias_metadata_fail():
    import pyarrow as pa
    from contributor_tools.withhold_gt23_unverified_anatomy import transform,verify
    schema=pa.schema([pa.field('knee_flexion_angle_ipsi_rad',pa.float64(),metadata={b'unit':b'rad'}),pa.field('task_info',pa.string())])
    original=pa.Table.from_pylist([{'knee_flexion_angle_ipsi_rad':1.,'task_info':'{}'},{'knee_flexion_angle_ipsi_rad':2.,'task_info':'{}'}],schema=schema)
    changed=transform(original)
    with pytest.raises(ValueError,match='Row count'):verify(original,changed.slice(0,1))
    bad=changed.set_column(1,changed.schema.field(1),pa.array(['{"gt23_unverified_anatomy":{"canonical_status":"unavailable"}}']*2))
    with pytest.raises(ValueError,match='provenance'):verify(original,bad)
    f=changed.schema.field(2);bad=changed.set_column(2,pa.field(f.name,f.type,metadata={b'unit':b'deg'}),changed.column(2))
    with pytest.raises(ValueError,match='metadata'):verify(original,bad)
