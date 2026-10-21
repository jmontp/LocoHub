"""Small synthetic ZIPs only; no publisher archive reads."""
import io
import json
from pathlib import Path
import shutil
import stat
import zipfile
import zlib

import pytest
from contributor_tools import extract_gt21_recovered_archive as tool


def fixture(tmp_path, monkeypatch, names=None):
    monkeypatch.setattr(shutil, 'disk_usage', lambda p: shutil._ntuple_diskusage(100*1024**3, 0, 100*1024**3))
    archive=tmp_path/'source.zip'
    with zipfile.ZipFile(archive,'w') as z:
        for name in names or ['AB17/ik/trial.mat','AB17/fp/trial.mat']:
            z.writestr(name,b'synthetic fixture\x00'*50)
    h=tool.inspector.digest(archive)
    acquisition={'subject':'AB17','archive':{'size':archive.stat().st_size,'sha256_hash':h,'doi':'synthetic.1'}}
    tool.write_json(tmp_path/'acquisition_plan.json',acquisition)
    receipt={'status':'publisher_archive_sha256_verified_not_extracted','plan_sha256':tool.inspector.digest(tmp_path/'acquisition_plan.json'),'bytes':archive.stat().st_size,'archive_path':str(archive),'sha256':h}
    tool.write_json(tmp_path/'acquisition_result.json',receipt)
    tool.inspector.inspect(archive,tmp_path/'acquisition_result.json',tmp_path/'archive_inspection.json')
    return tool.prepare(tmp_path/'acquisition_result.json',tmp_path/'archive_inspection.json',tmp_path/'extracted_v1_test')


def test_success_and_no_overwrite(tmp_path,monkeypatch):
    plan=fixture(tmp_path,monkeypatch)
    result=tool.extract(plan)
    assert result['files']==2 and result['expanded_bytes']==1800
    assert result['scientific_approval'] is False
    root=Path(plan['output_root'])
    rows=[json.loads(x) for x in (root/'member_manifest.jsonl').read_text().splitlines()]
    for row in rows:
        data=(root/'files'/row['member']).read_bytes()
        assert row['sha256']==tool.inspector.digest(root/'files'/row['member'])
        assert row['crc32']==f'{zlib.crc32(data):08x}'
    with pytest.raises(FileExistsError):tool.extract(plan)


@pytest.mark.parametrize('size,crc',[(2,zlib.crc32(b'abc')),(4,zlib.crc32(b'abc')),(3,0)])
def test_copy_bad_size_crc_preserves_partial(tmp_path,size,crc):
    target=tmp_path/'partial'
    with pytest.raises(ValueError):tool.copy_member(io.BytesIO(b'abc'),target,size,crc)
    assert target.exists()
    with pytest.raises(FileExistsError):tool.copy_member(io.BytesIO(b'abc'),target,3,zlib.crc32(b'abc'))


@pytest.mark.parametrize('bad',['../AB17/x','AB17/../x','AB17\\x','AB17/CON','/AB17/x'])
def test_unsafe_paths_refused(tmp_path,monkeypatch,bad):
    with pytest.raises(ValueError):fixture(tmp_path,monkeypatch,[bad])


def test_changed_receipt_and_archive(tmp_path,monkeypatch):
    plan=fixture(tmp_path,monkeypatch)
    receipt=tmp_path/'acquisition_result.json'
    receipt.write_text(receipt.read_text()+' ')
    with pytest.raises(ValueError,match='Bound evidence'):tool.extract(plan)
    assert not Path(plan['output_root']).exists()
    receipt.write_text(receipt.read_text()[:-1])
    with Path(plan['archive']).open('ab') as stream:stream.write(b'changed')
    with pytest.raises(ValueError,match='archive hash'):tool.extract(plan)


def test_renewed_disk_admission(tmp_path,monkeypatch):
    plan=fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(shutil,'disk_usage',lambda p:shutil._ntuple_diskusage(1,0,tool.inspector.RESERVE))
    with pytest.raises(ValueError,match='admission'):tool.extract(plan)
    assert not Path(plan['output_root']).exists()


def test_timeout_failure_preserved(tmp_path,monkeypatch):
    plan=fixture(tmp_path,monkeypatch)
    with pytest.raises(RuntimeError,match='timeout'):tool.extract(plan,timeout_seconds=-1)
    root=Path(plan['output_root'])
    assert json.loads((root/'extraction_failure.json').read_text())['status']=='failed_preserved'
    with pytest.raises(FileExistsError):tool.extract(plan)


def test_output_location_and_symlink(tmp_path,monkeypatch):
    fixture(tmp_path,monkeypatch)
    args=(tmp_path/'acquisition_result.json',tmp_path/'archive_inspection.json')
    with pytest.raises(ValueError):tool.prepare(*args,tmp_path/'active')
    (tmp_path/'extracted_v1_link').symlink_to(tmp_path/'missing')
    with pytest.raises(FileExistsError):tool.prepare(*args,tmp_path/'extracted_v1_link')


def test_collisions_and_symlinks():
    for names in [['AB17/x','AB17/X'],['AB17/x','AB17/x/y']]:
        with pytest.raises(ValueError):tool.inspector.inspect_members([zipfile.ZipInfo(x) for x in names],'AB17',100*1024**3)
    link=zipfile.ZipInfo('AB17/link');link.external_attr=(stat.S_IFLNK|0o777)<<16
    with pytest.raises(ValueError):tool.inspector.inspect_members([link],'AB17',100*1024**3)


def test_safe_directory_refuses_substituted_parent(tmp_path):
    root=tmp_path/'root';root.mkdir()
    outside=tmp_path/'outside';outside.mkdir()
    (root/'files').symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError,match='Symlink'):tool.safe_directories(root,'files/AB17/ik')
    assert not (outside/'AB17').exists()
