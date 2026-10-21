"""Synthetic metadata accounting only; no source arrays or numerical jobs."""
import copy
import pytest
from contributor_tools.plan_gt24_full_reconstruction import classify


def fixture():
    parsed={'subject':'BT01','recording':'task_on','disposition':'source_only_unmapped_task','files':{'angle_filt':{'path':'synthetic.csv','bytes':10}}}
    inventory={'phases':[{'phase':'Phase3','parsed_recordings':[parsed],'dynamic_complete_recordings':[{'subject':'BT01','recording':'task'}]}]}
    matrix={'parsed_recordings':[{'phase':'Phase3','subject':'BT01','recording':'task_on','task_disposition':parsed['disposition'],'participant_mass':{'value_kg':None},'mass_status':'unresolved'}]}
    membership={'jobs':[{'phase':'Phase3','subject':'BT01','parsed_recording':'task_on','native_recording':'task'}]}
    return inventory,matrix,membership


def test_unknown_mass_and_missing_streams_never_pass():
    result=classify(*fixture());row=result['parsed'][0]
    assert result['counts']['participant_mass_unresolved']==1
    assert row['missing_required_streams']==['grf','insole_sim','moment_filt','velocity']
    assert row['ready_for_scientific_adoption'] is False
    assert row['next_action'].startswith('lossless_source_companion')


def test_duplicate_inventory_rejected():
    i,m,p=fixture();i['phases'][0]['parsed_recordings']*=2
    with pytest.raises(ValueError,match='Duplicate'):classify(i,m,p)


def test_extra_mass_identity_rejected():
    i,m,p=fixture();m['parsed_recordings'].append({**m['parsed_recordings'][0],'recording':'extra'})
    with pytest.raises(ValueError,match='exactly'):classify(i,m,p)


def test_duplicate_or_foreign_membership_rejected():
    i,m,p=fixture();p['jobs']*=2
    with pytest.raises(ValueError,match='Duplicate'):classify(i,m,p)
    p['jobs']=p['jobs'][:1];p['jobs'][0]['native_recording']='missing'
    with pytest.raises(ValueError,match='unknown'):classify(i,m,p)


def test_no_candidate_explicit_not_silently_dropped():
    i,m,p=fixture();p['jobs']=[];result=classify(i,m,p)
    assert result['counts']['without_candidate_membership']==1
    assert result['parsed'][0]['membership_status']=='no_candidate_requires_source_lineage_resolution'
