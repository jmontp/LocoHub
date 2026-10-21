"""Inventory completeness and immutable resume for the Gait120 worker."""
import json
from contributor_tools import run_gait120_batch as batch


def test_inventory_keeps_all_trials_and_accounts_for_unsupported_sources(tmp_path):
    for name in ['S001/JointAngle/LevelWalking/Trial01/step01.mot',
                 'S120/JointAngle/StandToSit/Trial02/step01.MOT',
                 'S120/JointAngle/Unknown/Trial01/step01.mot',
                 'S120/JointAngle/LevelWalking/unexpected.mot']:
        path=tmp_path/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text('fixture')
    plan=batch.inventory(tmp_path)
    assert len(plan['recordings'])==2
    assert len(plan['unsupported_source_paths'])==2
    assert plan['subjects']==['S001','S120']


def test_resume_rejects_changed_sources_code_and_output(tmp_path):
    output=tmp_path/'phase.parquet';output.write_bytes(b'original')
    sources={'source':'hash1'};code={'code':'hash2'}
    (tmp_path/'conversion_manifest.json').write_text(json.dumps({
        'status':'converted_unreviewed','sources':sources,'code':code,
        'output_sha256':batch.digest(output)}))
    assert batch.resume_matches(tmp_path,sources,code)
    assert not batch.resume_matches(tmp_path,{'source':'changed'},code)
    assert not batch.resume_matches(tmp_path,sources,{'code':'changed'})
    output.write_bytes(b'changed')
    assert not batch.resume_matches(tmp_path,sources,code)


def test_sources_include_actual_fallback_sheet_and_optional_measurements(tmp_path,monkeypatch):
    code=tmp_path/'code';code.mkdir()
    sheet=code/'Anthropometric_Data_Participants.xlsx';sheet.write_bytes(b'sheet')
    monkeypatch.setattr(batch,'CODE',code)
    relative='S001/JointAngle/LevelWalking/Trial01/step01.mot'
    angle=tmp_path/relative;angle.parent.mkdir(parents=True);angle.write_bytes(b'angle')
    force=tmp_path/'S001/MotionCapture/LevelWalking/MOT/Trial01/step01.mot'
    force.parent.mkdir(parents=True);force.write_bytes(b'force')
    assert batch.source_files(tmp_path,relative)==[angle,sheet,force]
