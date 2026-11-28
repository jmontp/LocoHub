"""Synthetic JSON fields only; no MAT files or MATLAB execution."""
import copy
import pytest
from contributor_tools.run_mblue_native_fileinfo import validate_payload,recheck


@pytest.fixture
def metadata():
    sources=[{'subject':'AB01','path':'/synthetic/AB01_FileInfo.mat','sha256':'a'*64,'tasks':[['bare','level_1x0'],['exo','stairs']]}]
    payload={'subjects':{'AB01':{'subject':'AB01','date':'08162024','bare':{'level_1x0':{'vicon_filename':'bare_level_1x0'}},'exo':{'stairs':{'filename_suffix':'stairs'}}}}}
    return payload,sources


def test_native_fields_match_existing_selection_semantics(metadata):
    p,s=metadata;r=validate_payload(p,s)['AB01']
    assert r['date']=='08162024'
    assert r['tasks']=={'bare':{'level_1x0':{'vicon_filename':'bare_level_1x0'}},'exo':{'stairs':{'filename_suffix':'stairs'}}}
    assert r['source_fileinfo_sha256']=='a'*64


@pytest.mark.parametrize('problem',['subject','date','path','extra_subject','extra_task','missing_task','wrong_key','opaque'])
def test_invalid_native_fields_rejected(metadata,problem):
    p,s=metadata;info=p['subjects']['AB01']
    if problem=='subject':info['subject']='AB02'
    if problem=='date':info['date']='2024-08-16'
    if problem=='path':info['exo']['stairs']['filename_suffix']='../stairs'
    if problem=='extra_subject':p['subjects']['AB02']=copy.deepcopy(info)
    if problem=='extra_task':info['bare']['other']={'vicon_filename':'other'}
    if problem=='missing_task':del info['exo']['stairs']
    if problem=='wrong_key':info['exo']['stairs']={'vicon_filename':'stairs'}
    if problem=='opaque':info['date']={'class':'MatlabOpaque'}
    with pytest.raises(ValueError):validate_payload(p,s)


def test_changed_source_binding_rejected(tmp_path):
    from contributor_tools.prepare_mblue_orientation_pose_pilot import digest
    p=tmp_path/'source';p.write_text('original');bindings={str(p):digest(p)}
    recheck(bindings);p.write_text('changed')
    with pytest.raises(ValueError,match='Bound input changed'):recheck(bindings)
