"""Scalar synthetic fixtures only; no numerical imports or dataset reads."""
import importlib.util
import json
from pathlib import Path
import pytest

path=Path(__file__).resolve().parents[1]/'contributor_tools/correct_gt23_global_force_frame.py'
spec=importlib.util.spec_from_file_location('gt23_frame_fix',path)
FIX=importlib.util.module_from_spec(spec);spec.loader.exec_module(FIX)


def fixture():
    columns={name:[-0.0,None,float('nan'),-2.5] for name in FIX.ALIASES}
    columns.update(task_info=['{"speed_m_s":1.0}']*4,subject=['GT23_A']*4,
                   phase_percent=[0.,25.,50.,100.],knee_flexion_angle_ipsi_rad=[-1.,None,2.,3.],
                   grf_vertical_ipsi_BW=[1.,0.,None,2.],cop_anterior_ipsi_m=[0.1,None,0.2,0.3])
    return columns


def test_global_axes_preserved_without_rotation_or_other_changes():
    original=fixture();corrected=FIX.corrected_columns(original)
    FIX.verify_columns(original,corrected)
    for name,alias in FIX.ALIASES.items():
        assert corrected[alias] is original[name]
        assert corrected[name]==[None]*4
    for name in ['subject','phase_percent','knee_flexion_angle_ipsi_rad','grf_vertical_ipsi_BW','cop_anterior_ipsi_m']:
        assert corrected[name] is original[name]
    assert json.loads(corrected['task_info'][0])['speed_m_s']==1.


@pytest.mark.parametrize('column', ['source_grf_global_x_ipsi_BW','knee_flexion_angle_ipsi_rad','cop_anterior_ipsi_m'])
def test_readback_rejects_unrelated_or_source_change(column):
    original=fixture();corrected=FIX.corrected_columns(original)
    corrected[column]=list(corrected[column]);corrected[column][1]=0.
    with pytest.raises(ValueError):FIX.verify_columns(original,corrected)


def test_cannot_apply_twice_or_admit_nonobject_metadata():
    with pytest.raises(ValueError):FIX.corrected_columns(FIX.corrected_columns(fixture()))
    with pytest.raises(ValueError):FIX.frame_metadata('[]')


def test_zero_sign_and_missing_masks_are_preserved():
    assert not FIX.same_values([-0.0],[0.0])
    assert not FIX.same_values([None],[float('nan')])
    assert FIX.same_values([float('nan')],[float('nan')])


@pytest.mark.parametrize('index_column',['time_s','phase_ipsi'])
def test_persisted_parquet_preserves_arrays_masks_and_metadata(tmp_path,index_column):
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    original=fixture()
    original={key:(values*129)[:515] for key,values in original.items()}
    original[index_column]=[float(i) for i in range(515)]
    table=pa.Table.from_pydict(original)
    fields=[field.with_metadata({b'units':b'BW',b'original':b'preserve'}) if field.name in FIX.ALIASES else field.with_metadata({b'original':b'unchanged'}) for field in table.schema]
    table=table.cast(pa.schema(fields,metadata={b'source':b'synthetic fixture'}))
    category=pa.array(['walking']*514+[None]).dictionary_encode()
    table=table.append_column(pa.field('category',category.type,metadata={b'categorical':b'preserve'}),category)
    source=tmp_path/'source.parquet';target=tmp_path/'corrected.parquet'
    pq.write_table(table,source,row_group_size=150)
    assert FIX.correct_parquet(source,target)==515
    after=pq.ParquetFile(target).read(use_threads=False)
    FIX.verify_tables(table,after)
    persisted=pq.ParquetFile(target)
    assert persisted.num_row_groups>1
    assert all(persisted.metadata.row_group(i).num_rows<=512 for i in range(persisted.num_row_groups))
    for name,alias in FIX.ALIASES.items():
        assert after[name].null_count==515
        assert after[alias].is_null().equals(table[name].is_null())
        assert after.schema.field(alias).metadata[b'units']==b'BW'
    field=after.schema.field('category')
    corrupted=after.set_column(after.schema.get_field_index('category'),field.with_metadata({b'changed':b'bad'}),after['category'])
    with pytest.raises(ValueError,match='metadata'):FIX.verify_tables(table,corrupted)
