"""Independent scalar unit fixtures, no real signal data or numerical libraries."""
import json
import math
from pathlib import Path
import pytest
from contributor_tools.gt24_mass_field_policy import normalize_sample,participant_mass

METADATA=json.loads((Path(__file__).parent/'fixtures/gt24_mass_source_excerpt.json').read_text())


def inputs():
    return dict(source_force_vertical_N=981.,source_interaction_torque_units_unknown=-40.,source_net_moment_Nm_kg=3.,source_biological_moment_Nm_kg=2.5,joint='hip_flexion',exo_state='powered',participant={'value_kg':80.,'status':'source_participant_mass_bound'},reported_model={'value_kg':100.})


def test_true_participant_bodyweight_separate_from_model_weight_and_raw_torque():
    result=normalize_sample(**inputs())
    assert result['canonical_force_vertical_BW']==1.25
    assert result['derived_source_reported_model_weight_force']==1.
    assert math.isnan(result['canonical_assistance_moment_Nm_kg'])
    assert result['source_interaction_torque_units_unknown']==-40.
    assert 'source_interaction_units_unverified' in result['withheld_reasons']
    assert math.isnan(result['canonical_net_moment_Nm_kg'])
    assert result['source_net_moment_Nm_kg']==3. and result['source_biological_moment_Nm_kg']==2.5


def test_verified_denominator_chain_reexpresses_not_double_divides():
    result=normalize_sample(**inputs(),verified_source_denominator={'value_kg':100.,'status':'independently_verified_source_normalization_denominator','evidence_kind':'source_producer_code','evidence_sha256':'a'*64})
    assert result['canonical_net_moment_Nm_kg']==3.75
    assert result['canonical_biological_moment_Nm_kg']==3.125
    assert result['source_net_moment_Nm_kg']==3.
    assert result['canonical_net_moment_Nm_kg']!=3./80.


def test_unknown_bodymass_does_not_inherit_model_mass():
    arguments=inputs();arguments['participant']={'value_kg':None,'status':'recording_day_unresolved'}
    result=normalize_sample(**arguments)
    assert math.isnan(result['canonical_force_vertical_BW'])
    assert math.isnan(result['canonical_assistance_moment_Nm_kg'])
    assert result['derived_source_reported_model_weight_force']==1.


def test_ankle_assistance_unknown_unless_known_absent_and_sign_applied_once():
    arguments=inputs();arguments['joint']='ankle_dorsiflexion'
    result=normalize_sample(**arguments)
    assert math.isnan(result['canonical_assistance_moment_Nm_kg'])
    arguments['exo_state']='no_exo';assert normalize_sample(**arguments)['canonical_assistance_moment_Nm_kg']==0.
    arguments['joint']='knee_flexion'
    result=normalize_sample(**arguments,verified_source_denominator={'value_kg':100.,'status':'independently_verified_source_normalization_denominator','evidence_kind':'source_producer_code','evidence_sha256':'a'*64})
    assert result['canonical_net_moment_Nm_kg']==-3.75


def test_participant_mass_phase_day_binding_is_not_worn_model_mass():
    assert participant_mass(METADATA,'Phase1And2','BT01')['value_kg']==80.59
    assert participant_mass(METADATA,'Phase3','BT01')['value_kg']==77.29
    assert participant_mass(METADATA,'Phase1And2','BT06')['value_kg'] is None
    assert participant_mass(METADATA,'Phase1And2','BT06',day=2,day_evidence='synthetic fixture')['value_kg'] is None
    assert participant_mass(METADATA,'Phase3','BT02')['value_kg'] is None
    assert participant_mass(METADATA,'Phase3','BT02',day=2,day_evidence='synthetic fixture')['value_kg']==69.83


def test_mass_number_alone_is_not_a_verified_source_denominator():
    with pytest.raises(ValueError):normalize_sample(**inputs(),verified_source_denominator={'value_kg':100.})
