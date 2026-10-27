"""Small synthetic arithmetic fixtures; no scientific data is read."""
import importlib.util
import json
from pathlib import Path
import pytest
import pyarrow as pa

P=Path(__file__).resolve().parents[1]/'contributor_tools/correct_gt23_publisher_normalization.py'
spec=importlib.util.spec_from_file_location('gt23_norm_test',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def fixture():
    c=m.chain_module();force=c.load('force_fixture',c.FORCE_PATH);cop=c.load('cop_fixture',c.COP_PATH)
    info=json.dumps({'gt23_force_frame':force.FRAME_INFO,'gt23_cop_frame':cop.COP_INFO,'task_detail':'synthetic'})
    cols={'subject':['GT23_AB03']*4,'subject_metadata':['weight_kg:82.18']*4,'task_info':[info]*4,'unrelated':pa.array([-0.,None,float('nan'),5.]),'cop_anterior_ipsi_m':[.02]*4}
    for name in force.ALIASES:cols[name]=pa.array([None]*4,type=pa.float64())
    for name in m.FORCES:cols[name]=[2.,None,float('nan'),-0.]
    for name in m.MOMENTS:cols[name]=[227.,None,float('nan'),-0.]
    table=pa.table(cols)
    for alias in force.ALIASES.values():
        i=table.schema.get_field_index(alias);f=table.schema.field(alias).with_metadata({b'coordinate_frame':b'global'});table=table.set_column(i,f,table[alias])
    return table

def test_independent_source_arithmetic_and_preservation():
    t=fixture();out=m.transform_table(t,{'AB03':113.5},{'AB03':82.18})
    # Synthetic source moment 227 Nm / published113.5 kg =2 Nm/kg.
    assert out['hip_flexion_moment_ipsi_Nm_kg'][0].as_py()==2.
    assert out['source_hip_flexion_moment_ipsi_Nm'][0].as_py()==227.
    # Existing knee mapping negates source. Undo only for source-coordinate alias.
    assert out['source_knee_angle_moment_ipsi_Nm'][0].as_py()==-227.
    assert out['knee_flexion_moment_ipsi_Nm_kg'][0].as_py()==2.
    # Original raw vertical force represented by2 old BW: 2*82.18*9.81 N.
    assert out['grf_vertical_ipsi_BW'][0].as_py()==pytest.approx((2*82.18*9.81)/(113.5*9.81))
    assert out['source_grf_global_x_ipsi_BW'][0].as_py()==pytest.approx(164.36/113.5)
    assert out['grf_anterior_ipsi_BW'].null_count==4
    for name in ('unrelated','cop_anterior_ipsi_m'):assert m.exact_equal(t[name],out[name])
    info=json.loads(out['task_info'][0].as_py());original=json.loads(t['task_info'][0].as_py())
    assert info['gt23_force_frame']==original['gt23_force_frame'];assert info['gt23_cop_frame']==original['gt23_cop_frame']
    assert json.loads(out['subject_metadata'][0].as_py())['weight_kg']==113.5
    m.verify_tables(t,out,{'AB03':113.5},{'AB03':82.18})

def test_readback_rejects_corrupted_unrelated_bits():
    t=fixture();out=m.transform_table(t,{'AB03':113.5},{'AB03':82.18});i=out.schema.get_field_index('unrelated')
    out=out.set_column(i,out.schema.field(i),pa.array([0.,None,float('nan'),5.]))
    with pytest.raises(ValueError,match='Readback'):m.verify_tables(t,out,{'AB03':113.5},{'AB03':82.18})

def test_unknown_mass_and_wrong_previous_denominator_rejected():
    with pytest.raises(ValueError,match='Unknown'):m.transform_table(fixture(),{}, {})
    with pytest.raises(ValueError,match='denominator'):m.transform_table(fixture(),{'AB03':113.5},{'AB03':82.2})

def test_cannot_apply_twice():
    out=m.transform_table(fixture(),{'AB03':113.5},{'AB03':82.18})
    with pytest.raises(ValueError):m.transform_table(out,{'AB03':113.5},{'AB03':82.18})

def test_missing_cop_provenance_rejected():
    t=fixture();info=json.loads(t['task_info'][0].as_py());info.pop('gt23_cop_frame');i=t.schema.get_field_index('task_info');t=t.set_column(i,t.schema.field(i),pa.array([json.dumps(info)]*4))
    with pytest.raises(ValueError,match='COP'):m.transform_table(t,{'AB03':113.5},{'AB03':82.18})

def test_unfinished_combined_receipt_rejected(tmp_path):
    p=tmp_path/'receipt.json';p.write_text(json.dumps({'status':'running','scientific_approval':False}))
    with pytest.raises(ValueError,match='Completed'):m.receipt_chain(p,m.chain_module())

def test_persisted_parquet_readback(tmp_path):
    import pyarrow.parquet as pq
    before=fixture();after=m.transform_table(before,{'AB03':113.5},{'AB03':82.18})
    target=tmp_path/'synthetic.parquet';pq.write_table(after,target,row_group_size=2)
    m.verify_tables(before,pq.ParquetFile(target).read(use_threads=False),{'AB03':113.5},{'AB03':82.18})

@pytest.mark.parametrize('bad_mass',[0.,-1.,float('nan'),float('inf')])
def test_invalid_mass_rejected(bad_mass):
    with pytest.raises(ValueError,match='Invalid participant mass'):m.transform_table(fixture(),{'AB03':bad_mass},{'AB03':82.18})
