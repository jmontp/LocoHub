"""Source metadata fixtures only; synthetic day assignments are not dataset proof."""
import json
from pathlib import Path
import pytest
from contributor_tools.gt24_source_mass import resolve_mass,parse_statics,readme_masses

FIXTURE=Path(__file__).parent/'fixtures/gt24_mass_source_excerpt.json'

@pytest.fixture
def metadata():return json.loads(FIXTURE.read_text())

@pytest.mark.parametrize('subject,expected',[('BT01',87.02),('BT02',79.09),('BT13',96.74)])
def test_overlapping_subjects_resolve_explicit_phase12_not_phase3(metadata,subject,expected):
    kwargs={'day':1,'day_evidence':'SYNTHETIC assignment for unit fixture only'} if subject=='BT13' else {}
    result=resolve_mass(metadata,'Phase1And2',subject,'powered',**kwargs)
    assert result['source_model_mass_kg']==expected
    assert result['mass_basis']=='source_reported_worn_system_mass'

@pytest.mark.parametrize('subject,expected',[('BT06',85.14),('BT07',71.19),('BT13',96.50)])
def test_repeat_day_unknown_rejected_then_explicit_day2(metadata,subject,expected):
    with pytest.raises(ValueError,match='source-backed recording day'):resolve_mass(metadata,'Phase1And2',subject,'powered')
    result=resolve_mass(metadata,'Phase1And2',subject,'powered',day=2,day_evidence='SYNTHETIC assignment for unit fixture only')
    assert result['source_model_mass_kg']==expected
    assert result['participant_mass_kg'] is None


def test_phase3_uses_trial_model_exact_value_without_invented_calendar_day(metadata):
    result=resolve_mass(metadata,'Phase3','BT02','powered',native_trial='stairs_3_1')
    assert result['source_model_mass_kg_decimal']=='76.7386574562227'
    assert result['model_id']=='9' and result['calendar_day'] is None
    assert result['participant_mass_kg'] is None
    assert result['source_model_mass_kg']!=79.10
    with pytest.raises(ValueError,match='conflicts'):resolve_mass(metadata,'Phase3','BT02','powered',native_trial='stairs_3_1',day=1,day_evidence='synthetic contradiction')

@pytest.mark.parametrize('subject',['BT18','BT24'])
def test_conflicting_source_subject_model_identity_never_auto_swapped(metadata,subject):
    with pytest.raises(ValueError,match='Source conflict'):resolve_mass(metadata,'Phase3',subject,'powered',native_trial='normal_walk_1_1')


def test_unknown_phase_subject_native_model_and_noexo_refused(metadata):
    for phase,subject,state,extra in [('Parsed','BT01','powered',{}),('Phase1And2','UNKNOWN','powered',{}),('Phase1And2','BT01','no_exo',{}),('Phase3','BT20','powered',{}),('Phase3','BT20','powered',{'native_trial':'invented'})]:
        with pytest.raises(ValueError):resolve_mass(metadata,phase,subject,state,**extra)


def test_model_metadata_must_have_unique_valid_identity():
    with pytest.raises(ValueError):parse_statics(b'trial,static,mass\nx,1,70\nx,2,71\n')
    with pytest.raises(ValueError):parse_statics(b'trial,static,mass\nx,1,nan\n')
    with pytest.raises(ValueError):parse_statics(b'trial,static,mass\nx,1\n')
