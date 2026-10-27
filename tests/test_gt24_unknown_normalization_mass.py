"""Synthetic source rows only; no actual source or converted datasets opened."""
import contextlib
import json
import math
import pytest
from contributor_tools import apply_gt24_participant_normalization_v2 as tool


def fixture(participant=80.,model=None):
    record={'participant_mass':{'value_kg':participant,'status':'source_participant_mass_bound' if participant is not None else 'recording_day_unresolved','calendar_day':None},'model_mass':{'source_model_mass_kg':model,'mass_basis':'synthetic unresolved' if model is None else 'synthetic model','model_id':None},'mass_evidence_sha256':'a'*64,'exo_state':'powered'}
    raw={'angle_filt':{'time':0.},'grf':{'fp_l_force_y':981.,'fp_r_force_y':490.5},'exo':{'hip_angle_l_torque_interaction':-40.},'moment_filt':{'hip_flexion_l_moment':3.},'moment_filt_bio':{'hip_flexion_l_moment':2.5}}
    row={'reference_side':'left','source_time_s':0.,'subject_metadata':'{}','task_info':'{}','unrelated':-0.}
    for name in tool.changed_fields()-{'subject_metadata','task_info'}:row[name]=123.
    return record,raw,row


@pytest.mark.parametrize('participant,model,expected_BW,expected_model',[(80.,None,1.25,None),(None,100.,None,1.),(None,None,None,None),(80.,100.,1.25,1.)])
def test_independent_denominators(participant,model,expected_BW,expected_model):
    record,raw,row=fixture(participant,model);new=tool.corrected_row(row,raw,record)
    assert new['source_grf_vertical_ipsi_N']==981.
    for name,expected in [('grf_vertical_ipsi_BW',expected_BW),('derived_source_model_weight_grf_vertical_ipsi',expected_model)]:
        if expected is None:assert math.isnan(new[name])
        else:assert new[name]==expected
    assert new['source_normalized_hip_flexion_net_moment_ipsi_Nm_kg']==3.
    assert new['source_exo_hip_flexion_interaction_torque_ipsi_units_unknown']==-40.
    assert math.isnan(new['hip_flexion_moment_ipsi_Nm_kg'])
    assert math.isnan(new['hip_flexion_assistance_moment_ipsi_Nm_kg'])
    assert math.copysign(1,new['unrelated'])==-1.
    info=json.loads(new['task_info'])['normalization_availability']
    assert ('withheld' in info['derived_model_weight_force'])==(model is None)


@pytest.mark.parametrize('participant,model',[(80.,None),(None,100.),(None,None)])
def test_persisted_unknown_mass_readback_and_false_finite_rejection(tmp_path,monkeypatch,participant,model):
    import pyarrow as pa
    import pyarrow.parquet as pq
    record,raw,row=fixture(participant,model)
    rows=[{**row,'source_time_s':float(i)} for i in range(513)]
    source=[{**raw,'angle_filt':{'time':float(i)}} for i in range(513)]
    class Reader:
        def evidence(self):return {'synthetic':True}
    @contextlib.contextmanager
    def numerical(*args):yield iter(source)
    @contextlib.contextmanager
    def independent(*args):yield iter(source),{'fixture':Reader()}
    monkeypatch.setattr(tool,'numerical_source_rows',numerical);monkeypatch.setattr(tool,'source_rows',independent)
    old=tmp_path/'before.parquet';new=tmp_path/'after.parquet'
    pq.write_table(pa.Table.from_pylist(rows),old)
    tool.apply_record(record,old,new);report=tool.audit_record(record,old,new)
    assert report['rows']==513 and report['scientific_approval'] is False
    name='derived_source_model_weight_grf_vertical_ipsi' if model is None else 'grf_vertical_ipsi_BW'
    table=pq.ParquetFile(new).read(use_threads=False);values=table[name].to_pylist();values[512]=1.
    table=table.set_column(table.schema.get_field_index(name),table.schema.field(name),pa.array(values,type=pa.float64()));pq.write_table(table,new)
    with pytest.raises(ValueError,match='missingness'):tool.audit_record(record,old,new)


@pytest.mark.parametrize('bad',[0.,-1.,float('nan'),float('inf')])
def test_invalid_mass_is_not_silently_unknown(bad):
    record,raw,row=fixture(model=bad)
    with pytest.raises(ValueError,match='Invalid normalization mass'):tool.corrected_row(row,raw,record)
