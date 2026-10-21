"""Synthetic persisted rows only: no scientific dataset files are opened."""
import contextlib
import json
import math
import pytest
from contributor_tools import apply_gt24_participant_normalization as tool


def fixture():
    record={'participant_mass':{'value_kg':80.,'status':'source_participant_mass_bound','calendar_day':None},'model_mass':{'source_model_mass_kg':100.,'mass_basis':'synthetic model','model_id':1},'mass_evidence_sha256':'a'*64,'exo_state':'powered'}
    raw={'angle_filt':{'time':0.},'grf':{'fp_l_force_y':981.,'fp_r_force_y':490.5},'exo':{'hip_angle_l_torque_interaction':-40.,'knee_angle_l_torque_interaction':20.},'moment_filt':{'hip_flexion_l_moment':3.,'ankle_angle_l_moment':-2.},'moment_filt_bio':{'hip_flexion_l_moment':2.5}}
    row={'reference_side':'left','source_time_s':0.,'subject_metadata':json.dumps({'weight_kg':100.,'untouched':'value'}),'task_info':'{}','preserved':1.25,'nullable':None}
    for name in tool.changed_fields()-{'subject_metadata','task_info'}:row[name]=123.
    return record,raw,row


def test_known_force_unknown_interaction_units_and_moment_denominator():
    record,source,row=fixture();actual=tool.corrected_row(row,source,record)
    assert actual['grf_vertical_ipsi_BW']==1.25
    assert actual['derived_source_model_weight_grf_vertical_ipsi']==1.
    assert actual['source_exo_hip_flexion_interaction_torque_ipsi_units_unknown']==-40.
    assert actual['source_normalized_hip_flexion_net_moment_ipsi_Nm_kg']==3.
    assert math.isnan(actual['hip_flexion_assistance_moment_ipsi_Nm_kg'])
    assert math.isnan(actual['hip_flexion_moment_ipsi_Nm_kg'])
    assert actual['preserved']==row['preserved'] and actual['nullable'] is None
    record['verified_source_denominator']={'value_kg':100.,'evidence_sha256':'a'*64}
    with pytest.raises(ValueError,match='not evidence'):tool.corrected_row(row,source,record)


def test_persisted_chunk_boundary_and_independent_audit(tmp_path,monkeypatch):
    import pyarrow as pa
    import pyarrow.parquet as pq
    record,source,row=fixture();rows=[];raws=[]
    for i in range(1027):
        rows.append({**row,'source_time_s':float(i),'preserved':float(i) if i%3 else None})
        raws.append({**source,'angle_filt':{'time':float(i)},'grf':{'fp_l_force_y':981.+i,'fp_r_force_y':490.5}})
    class Reader:
        def evidence(self):return {'synthetic':True}
    @contextlib.contextmanager
    def numerical(*args):yield iter(raws)
    @contextlib.contextmanager
    def independent(*args):yield iter(raws),{'synthetic':Reader()}
    monkeypatch.setattr(tool,'numerical_source_rows',numerical);monkeypatch.setattr(tool,'source_rows',independent)
    old=tmp_path/'old.parquet';new=tmp_path/'new.parquet'
    pq.write_table(pa.Table.from_pylist(rows).replace_schema_metadata({b'synthetic':b'fixture'}),old)
    assert tool.apply_record(record,old,new)['rows']==1027
    result=tool.audit_record(record,old,new)
    assert result['rows']==1027 and result['all_unrelated_values_field_metadata_null_masks_exact']
    table=pq.ParquetFile(new).read(use_threads=False)
    values=table['preserved'].to_pylist();values[512]=99999.
    table=table.set_column(table.schema.get_field_index('preserved'),'preserved',pa.array(values,type=pa.float64()))
    pq.write_table(table,new)
    with pytest.raises(ValueError,match='Unrelated persisted'):tool.audit_record(record,old,new)
