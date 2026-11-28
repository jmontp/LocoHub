"""Independent analytic synthetic fixtures; no Gait120 scientific data."""
import json
import math
import pytest
from contributor_tools import audit_gait120_extended_sources as a
from contributor_tools import withhold_gait120_planar_segments as c


def test_exact_uniform_linear_derivative_and_duration():
    assert a.derivative([1.,2.,3.,4.],3.)==[1.]*4
    assert a.derivative([1.,2.,3.,4.],6.)==[.5]*4
    assert a.derivative([1.,1.,1.],2.)==[0.]*3


def test_unshifted_source_jump_can_trigger_frozen_repair():
    values=[i*.01+(2 if i>=75 else 0) for i in range(150)]
    assert a.repair_would_trigger(values)
    assert not a.repair_would_trigger([i*.01 for i in range(150)])


def test_anthropometry_units_identity_and_duplicates():
    rows=[{'Subject':'S120','Bodymass(Kg)':72.5,'Height(mm)':1820},{'Subject':'S001','Bodymass(Kg)':61.,'Height(mm)':1630}]
    assert a.expected_anthropometry(rows,'S120')=={'weight_kg':72.5,'height_m':1.82}
    with pytest.raises(ValueError,match='Exactly one'):a.expected_anthropometry(rows+rows,'S120')
    with pytest.raises(ValueError):a.expected_anthropometry(rows,'S999')


def synthetic():
    angles={(joint,side):[float(i)/149 for i in range(150)] for joint in ('hip_flexion','knee_flexion','ankle_dorsiflexion') for side in ('ipsi','contra')};pelvis=[0.]*150
    fields={'subject_metadata':[json.dumps({'weight_kg':80.,'height_m':1.7})]*150,'pelvis_sagittal_angle_rad':[0.]*150,'pelvis_sagittal_velocity_rad_s':[0.]*150}
    for side in ('ipsi','contra'):
        for joint in ('hip_flexion','knee_flexion','ankle_dorsiflexion'):
            fields[f'{joint}_velocity_{side}_rad_s']=[1.]*150;fields[f'{joint}_acceleration_{side}_rad_s2']=[0.]*150
        for segment,values,vel in [('thigh',angles[('hip_flexion',side)],1.),('shank',[0.]*150,0.),('foot',angles[('ankle_dorsiflexion',side)],1.)]:
            fields[f'{segment}_sagittal_angle_{side}_rad']=values;fields[f'{segment}_sagittal_velocity_{side}_rad_s']=[vel]*150
    return fields,angles,pelvis


def test_all_independent_derivatives_and_planar_values():
    fields,angles,pelvis=synthetic();r=a.review_arrays(fields,angles,pelvis,1.,{'weight_kg':80.,'height_m':1.7})
    assert len(r['feature_checks'])==26 and not r['unassessed_features'];assert r['scientific_approval'] is False
    fields['ankle_dorsiflexion_acceleration_contra_rad_s2'][75]=1.
    with pytest.raises(ValueError,match='Independent value'):a.review_arrays(fields,angles,pelvis,1.,{'weight_kg':80.,'height_m':1.7})


def test_planar_alias_bits_nulls_and_unrelated_preserved():
    import pyarrow as pa
    columns={'subject':['G120_S001']*4,'task_info':['{}']*4,'unrelated':[-0.,None,float('nan'),3.]}
    for name in c.ALIASES:columns[name]=pa.array([-0.,None,float('nan'),.2],type=pa.float64())
    before=pa.table(columns);after=c.transform_table(before);c.verify_tables(before,after)
    assert all(after[name].null_count==4 for name in c.ALIASES)
    assert all(after[name].null_count==1 for name in c.ALIASES.values())
    field=after.schema.field('unrelated');bad=after.set_column(after.schema.get_field_index('unrelated'),field,pa.array([0.,None,float('nan'),3.]))
    with pytest.raises(ValueError,match='bits'):c.verify_tables(before,bad)


def test_actual_frozen_helper_modifies_unshifted_synthetic_jump():
    import numpy as np
    from contributor_tools.common.derivatives import compute_velocity_from_shifted_angle
    values=np.arange(150,dtype=float)*.01;values[75:]+=2.
    plain=a.derivative(values.tolist(),1.)
    existing=compute_velocity_from_shifted_angle(values,1.,discontinuity_idx=None)
    assert not np.allclose(existing,plain)
    explicit=compute_velocity_from_shifted_angle(values,1.,discontinuity_idx=None,detect_discontinuity=False)
    np.testing.assert_allclose(explicit,plain,rtol=1e-12,atol=1e-12)


def test_independent_spreadsheet_reader(tmp_path):
    import openpyxl
    path=tmp_path/'synthetic.xlsx';book=openpyxl.Workbook();sheet=book.active
    sheet.append(['Subject','Bodymass(Kg)','Height(mm)']);sheet.append(['S003',67.2,1740]);book.save(path);book.close()
    assert a.expected_anthropometry(a.spreadsheet_rows(path),'S003')=={'weight_kg':67.2,'height_m':1.74}


def test_isolated_patch_only_changes_reviewed_calls_and_metadata():
    from contributor_tools.prepare_gait120_unshifted_derivatives import SOURCE,patch
    original=SOURCE.read_text();changed=patch(original)
    assert changed.count('detect_discontinuity=False')==19
    assert 'automatic_discontinuity_repair' in changed
    with pytest.raises(ValueError):patch(changed)
