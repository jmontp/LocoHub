"""Small Arrow fixtures; coordinator runs in an available numerical slot."""
import json
from contributor_tools.adopt_gt24_phase_ankle_sign import FIELDS,transform,task_metadata


def test_arrow_exact_source_masks_metadata_and_single_negation():
    import pyarrow as pa
    import pyarrow.parquet as pq
    import tempfile
    from pathlib import Path
    from contributor_tools.preserve_um21_planar_estimates import exact_value
    info={'exo_state':'no_exo','moment_semantics':'source_filtered_total_joint_moment_Nm_per_source_model_kg','biological_moment_semantics':'source_total_minus_exo_interaction_when_available','assistance_semantics':'known_absent_no_exo'}
    fields=[pa.field(k,pa.float64(),metadata={b'unit':k.rsplit('_',1)[-1].encode()}) for k in FIELDS]+[pa.field('task_info',pa.string()),pa.field('unrelated',pa.float64())]
    schema=pa.schema(fields,metadata={b'synthetic':b'exact metadata fixture'})
    raw=[-0.,1.5,None,float('nan')]
    table=pa.Table.from_arrays([pa.array(raw) for k in FIELDS]+[pa.array([json.dumps(info)]*4),pa.array([1.,None,-0.,float('nan')])],schema=schema)
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)/'corrected.parquet';pq.write_table(transform(table),path);after=pq.read_table(path)
    assert after.schema.metadata==table.schema.metadata
    for name,alias in FIELDS.items():
        assert exact_value(table[name].to_pylist(),after[alias].to_pylist())
        assert exact_value([None if v is None else -v for v in raw],after[name].to_pylist())
        assert table[name].is_null().equals(after[name].is_null())
        assert table.schema.field(name).with_name(alias).equals(after.schema.field(alias),check_metadata=True)
    assert exact_value(table['unrelated'].to_pylist(),after['unrelated'].to_pylist())
    assert after['task_info'].to_pylist()==[task_metadata(json.dumps(info))]*4
