"""Analytic synthetic CSV fixtures; never reads research datasets."""
import csv
import json
import math
from pathlib import Path
import pytest
from contributor_tools import audit_gt24_corrected_raw_source as a


def fixture(tmp_path,participant=50.,model=60.):
    record={'subject':'BT01','recording':'synthetic_on','phase':'Phase3','folder':str(tmp_path),'files':{},'is_gait':True,'task':'level_walking','task_id':'synthetic','exo_state':'powered','participant_mass':{'value_kg':participant,'status':'source_participant_mass_bound' if participant else 'unresolved','calendar_day':None},'model_mass':{'source_model_mass_kg':model},'mass_evidence_sha256':'synthetic','verified_source_denominator':None}
    for kind in sorted(a.TABLES):
        path=tmp_path/f'BT01_synthetic_on_{kind}.csv';headers=['time',*sorted(a.projected_columns(kind))]
        with path.open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=headers);writer.writeheader()
            for i in range(7):
                row={'time':i*.1}
                for column in headers[1:]:
                    if kind=='angle_filt':value=(i*.1)**2*180/math.pi
                    elif kind=='velocity':value='nan'
                    elif kind=='grf':value=98.1 if '_r_' in column else (49.05 if i>=2 else 0.)
                    else:value=2. if '_r' in column else 3.
                    row[column]=value
                writer.writerow(row)
        record['files'][kind]={'path':str(path)}
    return record


def test_analytic_reference_sign_derivatives_and_masses(tmp_path):
    r=fixture(tmp_path);facts=a.scan(r)
    assert facts['reference']=='r'
    source=list(a.windows(a.source_rows(r)));values,withheld=a.expected_row(r,facts,*source[3])
    assert values['hip_flexion_angle_ipsi_rad']==pytest.approx(.09)
    assert values['knee_flexion_angle_ipsi_rad']==pytest.approx(-.09)
    assert values['ankle_dorsiflexion_velocity_ipsi_rad_s']==pytest.approx(-.6)
    assert values['hip_flexion_acceleration_ipsi_rad_s2']==pytest.approx(2.)
    assert values['grf_vertical_ipsi_BW']==pytest.approx(.2)
    assert values['derived_source_model_weight_grf_vertical_ipsi']==pytest.approx(1/6)
    assert values['source_normalized_knee_extension_net_moment_ipsi_Nm_kg']==2.
    assert 'knee_flexion_moment_ipsi_Nm_kg' in withheld


def test_unknown_masses_withhold_without_borrowing(tmp_path):
    r=fixture(tmp_path,None,None);f=a.scan(r);v,w=a.expected_row(r,f,*next(a.windows(a.source_rows(r))))
    assert math.isnan(v['grf_vertical_ipsi_BW']) and math.isnan(v['derived_source_model_weight_grf_vertical_ipsi'])
    assert v['source_grf_vertical_ipsi_N']==98.1
    with pytest.raises(ValueError,match='fabricated'):a.check_value(.2,v['grf_vertical_ipsi_BW'],'BW')


@pytest.mark.parametrize('actual,expected',[(1.,-1.),(.2,.3),('left','right'),(0.,math.nan)])
def test_sign_normalization_side_and_missing_corruption(actual,expected):
    with pytest.raises(ValueError):a.check_value(actual,expected,'synthetic')


def test_wrong_source_identity(tmp_path):
    r=fixture(tmp_path);r['recording']='another'
    with pytest.raises(ValueError,match='identity'):list(a.source_rows(r))


def test_mismatched_stream_clock(tmp_path):
    r=fixture(tmp_path);p=Path(r['files']['grf']['path']);text=p.read_text();p.write_text(text.replace('0.1,','0.11,'))
    with pytest.raises(ValueError,match='clocks differ'):a.scan(r)


def test_missing_required_header_rejected(tmp_path):
    r=fixture(tmp_path);p=Path(r['files']['moment_filt']['path']);p.write_text(p.read_text().replace('knee_angle_r_moment','wrong_units_or_column'))
    with pytest.raises(ValueError,match='columns missing'):a.scan(r)


def test_five_row_storage_bound_and_endpoints(tmp_path):
    r=fixture(tmp_path);f=a.scan(r);windows=list(a.windows(a.source_rows(r)))
    assert max(len(w) for _,_,w in windows)<=5
    first,_=a.expected_row(r,f,*windows[0]);last,_=a.expected_row(r,f,*windows[-1])
    assert first['hip_flexion_velocity_ipsi_rad_s']==pytest.approx(.1)
    assert last['hip_flexion_velocity_ipsi_rad_s']==pytest.approx(1.1)


def test_persisted_readback_and_late_corruption(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    r=fixture(tmp_path);facts=a.scan(r);rows=[]
    for window in a.windows(a.source_rows(r)):
        values,_=a.expected_row(r,facts,*window)
        # Expected mapping already checked against analytic values above; this
        # fixture additionally exercises persisted batches/identity/late errors.
        values['subject_metadata']=json.dumps({'weight_kg':50.,'participant_mass_kg':50.,'source_model_mass_kg':60.,'weight_basis':'participant_without_exoskeleton','day':None,'source_mass_evidence_sha256':'synthetic'})
        values['task_info']=json.dumps({'reference_leg':'r','exo_state':'powered','normalization_policy':'gt24_participant_mass_missingness_v2','source_joint_moment_denominator_status':'unverified'})
        rows.append(values)
    output=tmp_path/'corrected.parquet';pq.write_table(pa.Table.from_pylist(rows),output,row_group_size=2)
    result=a.audit(r,output)
    assert result['rows']==7
    assert result['status']=='corrected_raw_source_partial_unassessed' # supplied velocity aliases all NaN
    assert result['coverage']['grf_vertical_ipsi_BW']=={'finite':7,'missing':0,'withheld':0}
    assert result['coverage']['hip_flexion_moment_ipsi_Nm_kg']['withheld']==7
    rows[-1]['grf_vertical_ipsi_BW']=999.
    pq.write_table(pa.Table.from_pylist(rows),output,row_group_size=2)
    with pytest.raises(ValueError,match='normalization differs'):a.audit(r,output)


def test_literal_unit_evidence_requires_every_unit():
    text='\n'.join(['<task name>_angle_filt.csv: kinematics (deg)','<task name>_velocity.csv: velocity (deg/s)','<task name>_moment_filt.csv: moments (Nm/kg)','<task name>_moment_filt_bio.csv: moments (Nm/kg)','<task name>_grf.csv: Force in N; y-axis is vertical','Virtual_Insoles.csv: COP in m in calcn_l and calcn_r'])
    assert a.unit_evidence(text)['interaction_torque'].startswith('unknown')
    with pytest.raises(ValueError,match='unit evidence'):a.unit_evidence(text.replace('(Nm/kg)','(Nm)'))


def declared_added_schema(filename):
    """Read the actual frozen producer declaration without scientific imports."""
    import ast
    path=Path(__file__).resolve().parents[1]/'contributor_tools'/filename
    tree=ast.parse(path.read_text())
    nodes=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='JOINTS' for t in n.targets) or isinstance(n,ast.FunctionDef) and n.name=='added_fields']
    namespace={};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),namespace)
    return namespace['added_fields']()


@pytest.mark.parametrize('policy,filename',[('gt24_participant_mass_v1','apply_gt24_participant_normalization.py'),('gt24_participant_mass_missingness_v2','apply_gt24_participant_normalization_v2.py')])
def test_actual_producer_schema_aliases_are_required_not_optional(tmp_path,policy,filename):
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    r=fixture(tmp_path);facts=a.scan(r);rows=[]
    v2_added=declared_added_schema('apply_gt24_participant_normalization_v2.py')
    declared=declared_added_schema(filename)
    for window in a.windows(a.source_rows(r)):
        values,_=a.expected_row(r,facts,*window)
        base={k:v for k,v in values.items() if k not in v2_added}
        actual={**base,**{k:values[k] for k in declared}}
        actual['subject_metadata']=json.dumps({'weight_kg':50.,'participant_mass_kg':50.,'source_model_mass_kg':60.,'weight_basis':'participant_without_exoskeleton','day':None,'source_mass_evidence_sha256':'synthetic'})
        actual['task_info']=json.dumps({'reference_leg':'r','exo_state':'powered','normalization_policy':policy,'source_joint_moment_denominator_status':'unverified'})
        rows.append(actual)
    output=tmp_path/'schema.parquet';pq.write_table(pa.Table.from_pylist(rows),output)
    assert a.audit(r,output,producer_policy=policy)['rows']==7
    other='gt24_participant_mass_v1' if policy.endswith('v2') else 'gt24_participant_mass_missingness_v2'
    with pytest.raises(ValueError,match='columns'):a.audit(r,output,producer_policy=other)


def test_no_contact_reference_is_unassessed_fallback(tmp_path):
    r=fixture(tmp_path);path=Path(r['files']['grf']['path']);rows=list(csv.DictReader(path.open()))
    for row in rows:
        row['fp_l_force_y']='0';row['fp_r_force_y']='0'
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
    facts=a.scan(r)
    assert facts['reference']=='l'
    assert facts['reference_evidence']=='no_contact_left_fallback_unassessed'
