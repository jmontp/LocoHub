"""Synthetic preservation fixtures; no research data used."""
import pandas as pd
import pytest
from contributor_tools.preserve_mblue_planar_estimates import CANONICAL, MAPPING, transform, verify_frame


@pytest.fixture
def original():
    frame = pd.DataFrame({name: [index / 10, float('nan'), -index / 10]
                          for index, name in enumerate(CANONICAL, 1)})
    frame['observation_id'] = ['synthetic'] * 3
    frame['reference_side'] = ['left'] * 3
    frame['source_event_start_time_s'] = [10.0] * 3
    frame['knee_flexion_angle_ipsi_rad'] = [0.1, 0.2, 0.3]
    return frame


def test_exact_planar_values_missingness_and_unrelated_columns(original):
    before = original.copy(deep=True)
    corrected = transform(original)
    verify_frame(original, corrected)
    pd.testing.assert_frame_equal(original, before, check_exact=True)
    assert corrected[list(CANONICAL)].isna().all().all()
    assert corrected[list(MAPPING.values())].iloc[1].isna().all()


@pytest.mark.parametrize('problem', ['missing', 'duplicate', 'derived', 'boolean', 'text'])
def test_refuse_incomplete_or_conflicting_input(original, problem):
    if problem == 'missing': original = original.drop(columns=CANONICAL[0])
    elif problem == 'duplicate': original = pd.concat([original, original[[CANONICAL[0]]]], axis=1)
    elif problem == 'derived': original['derived_planar_unexpected'] = 0.0
    elif problem == 'boolean': original[CANONICAL[0]] = True
    else: original[CANONICAL[0]] = 'unknown'
    with pytest.raises(ValueError):
        transform(original)


@pytest.mark.parametrize('problem', ['identity', 'joint_value', 'estimate', 'missing_mask', 'canonical', 'extra'])
def test_verifier_rejects_corruption(original, problem):
    result = transform(original)
    if problem == 'identity': result.loc[0, 'observation_id'] = 'other'
    elif problem == 'joint_value': result.loc[0, 'knee_flexion_angle_ipsi_rad'] = 9
    elif problem == 'estimate': result.loc[0, MAPPING[CANONICAL[0]]] = 9
    elif problem == 'missing_mask': result.loc[1, MAPPING[CANONICAL[0]]] = 0
    elif problem == 'canonical': result.loc[0, CANONICAL[0]] = 0
    else: result['unexpected'] = 1
    with pytest.raises((ValueError, AssertionError)):
        verify_frame(original, result)


def test_arrow_preserves_null_masks_schema_metadata_and_unrelated_fields():
    import pyarrow as pa
    from contributor_tools.preserve_mblue_planar_estimates import transform_table
    arrays = {name: pa.array([1.0, None, float('nan')]) for name in CANONICAL}
    arrays['observation_id'] = pa.array(['synthetic'] * 3)
    table = pa.table(arrays).replace_schema_metadata({b'provenance': b'synthetic source'})
    result = transform_table(table)
    assert result.schema.metadata == table.schema.metadata
    assert result['observation_id'].equals(table['observation_id'])
    for source, target in MAPPING.items():
        assert result[source].null_count == 3
        assert result[target].is_null().to_pylist() == [False, True, False]
        assert result[target][0].as_py() == 1.0
        assert pd.isna(result[target][2].as_py())
        assert result.schema.field(target).metadata[b'interpretation'].startswith(b'planar estimate')


@pytest.fixture
def persisted_shards(tmp_path):
    """One valid synthetic cycle, retaining Arrow null and NaN separately."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    from contributor_tools.preserve_mblue_planar_estimates import transform_table
    values = [0.125, None, float('nan')] + [0.25] * 147
    arrays = {name: pa.array(values, type=pa.float64()) for name in CANONICAL}
    for name, value in {'subject': 'SYNTHETIC', 'source_recording_id': 'synthetic/trial',
                        'observation_id': 'synthetic-cycle', 'reference_side': 'left',
                        'observation_type': 'individual_cycle', 'task': 'level_walking',
                        'task_id': 'synthetic_level', 'task_info': '{}'}.items():
        arrays[name] = pa.array([value] * 150)
    arrays['phase_ipsi'] = pa.array([100.0 * i / 149 for i in range(150)])
    arrays['knee_flexion_angle_ipsi_rad'] = pa.array(values, type=pa.float64())
    table = pa.table(arrays).replace_schema_metadata({b'provenance': b'synthetic fixture'})
    angle_index = table.schema.get_field_index(CANONICAL[0])
    angle_field = table.schema.field(angle_index).with_metadata({b'units': b'rad', b'source': b'synthetic joint sum'})
    table = table.set_column(angle_index, angle_field, table.column(angle_index))
    index = table.schema.get_field_index('knee_flexion_angle_ipsi_rad')
    field = table.schema.field(index).with_metadata({b'units': b'rad', b'source': b'synthetic'})
    table = table.set_column(index, field, table.column(index))
    source, target = tmp_path / 'source.parquet', tmp_path / 'corrected.parquet'
    pq.write_table(table, source)
    with pq.ParquetWriter(target, transform_table(table).schema, compression='zstd') as writer:
        for batch in pq.ParquetFile(source).iter_batches(batch_size=150, use_threads=False):
            writer.write_table(transform_table(pa.Table.from_batches([batch])))
    return source, target


def test_persisted_roundtrip_verifies_values_nulls_metadata_and_contract(persisted_shards):
    import pyarrow.parquet as pq
    from contributor_tools.preserve_mblue_planar_estimates import verify_shard
    source, target = persisted_shards
    checked = verify_shard(source, target)
    assert checked == {'observations': 1, 'rows': 150,
                       'all_other_columns_exactly_preserved': True,
                       'all_planar_estimates_exactly_preserved': True,
                       'unsupported_canonical_values_missing': True}
    output = pq.ParquetFile(target).read(use_threads=False)
    assert output.schema.metadata == {b'provenance': b'synthetic fixture'}
    assert output.schema.field('knee_flexion_angle_ipsi_rad').metadata[b'units'] == b'rad'
    assert output.schema.field(MAPPING[CANONICAL[0]]).metadata[b'units'] == b'rad'
    assert output.schema.field(MAPPING[CANONICAL[0]]).metadata[b'source'] == b'synthetic joint sum'
    estimate = output[MAPPING[CANONICAL[0]]]
    assert estimate.is_null().to_pylist()[:3] == [False, True, False]
    assert pd.isna(estimate[2].as_py())
    assert output[CANONICAL[0]].null_count == 150


def test_duplicate_observation_across_persisted_shards_rejected(persisted_shards):
    from contributor_tools.preserve_mblue_planar_estimates import verify_shard
    source, target = persisted_shards
    seen = set()
    verify_shard(source, target, seen)
    assert seen == {'synthetic-cycle'}
    with pytest.raises(ValueError, match='Duplicate observation'):
        verify_shard(source, target, seen)
