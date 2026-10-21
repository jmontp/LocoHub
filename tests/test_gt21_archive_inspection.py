"""Synthetic ZIP directories and tiny README only; no real archive reads."""
import hashlib
import json
import stat
import zipfile
import pytest
from contributor_tools import inspect_gt21_recovered_archive as tool


def member(name,size=10,compressed=5,mode=stat.S_IFREG|0o644):
    m=zipfile.ZipInfo(name);m.file_size=size;m.compress_size=compressed;m.external_attr=mode<<16
    return m


@pytest.mark.parametrize('name',['../AB17/x','/AB17/x','AB17/../x','AB17\\x','AB17//x','AB17/./x','AB17/C:evil','AB17/NUL.mat','AB17/foo.','AB17/foo '])
def test_unsafe_paths_rejected(name):
    with pytest.raises(ValueError):tool.inspect_members([member(name)],'AB17',10**12)


def test_foreign_subject_and_symlink_refused():
    with pytest.raises(ValueError,match='subject set'):tool.inspect_members([member('AB12/a')],'AB17',10**12)
    with pytest.raises(ValueError,match='Nonregular'):tool.inspect_members([member('AB17/a',mode=stat.S_IFLNK|0o777)],'AB17',10**12)


@pytest.mark.parametrize('names',[['AB17/a','AB17/A'],['AB17/a','AB17/a/x'],['AB17/a','AB17/a/']])
def test_windows_collisions_refused(names):
    with pytest.raises(ValueError):tool.inspect_members([member(n) for n in names],'AB17',10**12)


def test_expanded_size_reserve_and_ratio_admission():
    entries=[member('AB17/date/ik/a.mat',100,20),member('AB17/date/gcLeft/a.mat',50,10)]
    result=tool.inspect_members(entries,'AB17',tool.RESERVE+150)
    assert result['extraction_admitted'] and result['expanded_bytes']==150
    assert result['source_channel_directories']==['gcLeft','ik']
    assert not tool.inspect_members(entries,'AB17',tool.RESERVE+149)['extraction_admitted']
    assert not tool.inspect_members([member('AB17/a',2000,1)],'AB17',10**12)['extraction_admitted']


def test_real_synthetic_zip_receipt_and_readme(tmp_path):
    archive=tmp_path/'synthetic.zip'
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('AB17/README.txt','Synthetic version1 fixture')
        z.writestr('AB17/date/ik/example.mat',b'synthetic, not MAT')
    sha=hashlib.sha256(archive.read_bytes()).hexdigest()
    plan={'subject':'AB17','archive':{'doi':'10.synthetic/example.1','size':archive.stat().st_size,'sha256_hash':sha}}
    planpath=tmp_path/'acquisition_plan.json';planpath.write_text(json.dumps(plan))
    receipt=tmp_path/'acquisition_result.json';receipt.write_text(json.dumps({'status':'publisher_archive_sha256_verified_not_extracted','archive_path':str(archive),'sha256':sha,'plan_sha256':tool.digest(planpath)}))
    report=tool.inspect(archive,receipt,tmp_path/'inspection.json')
    assert report['readme_metadata'][0]['text']=='Synthetic version1 fixture'
    assert not report['version_reconciliation']['archive_ik_offset_directory_present']
    assert report['scientific_approval'] is False
    assert not (tmp_path/'AB17').exists()
    with pytest.raises(FileExistsError):tool.inspect(archive,receipt,tmp_path/'inspection.json')
    archive.write_bytes(archive.read_bytes()+b'changed')
    with pytest.raises(ValueError,match='size/hash'):tool.inspect(archive,receipt,tmp_path/'another.json')
