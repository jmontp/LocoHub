"""Synthetic metadata, ZIP ranges and scalar interpolation; no real data reads."""
import importlib.util
import json
from pathlib import Path
import struct
import zlib
import pytest

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
PLAN=load('fu18_full_plan','contributor_tools/plan_fukuchi_ensembles.py')
PAIR=load('fu18_full_pair','contributor_tools/convert_fukuchi_ensemble_pair.py')
RUN=load('fu18_full_run','contributor_tools/run_fukuchi_ensembles.py')
BASE=load('fu18_frozen_base','contributor_tools/conversion_scripts/Fukuchi_2018_Walking/convert_ensemble_pilot.py')


def sample_inventory(stems):
    directory=[];metadata=[]
    for stem in stems:
        for suffix in ['ang','knt']:
            name=stem+suffix+'.txt'
            directory.append({'name':'51subjs/'+name,'method':8,'flags':8,'crc32':123,'compressed_size':40,'uncompressed_size':100,'offset':1000*len(directory)})
            metadata.append({'FileName':name,'Subject':str(int(stem[4:6])),'AgeGroup':'Young' if int(stem[4:6])<=24 else 'Older'})
    return directory,metadata


def test_exact_pair_coverage_and_absence_ledger():
    result=PLAN.inventory(*sample_inventory(['WBDS01walkOC','WBDS51walkT06']))
    assert result['summary']['pairs']==2 and result['summary']['subjects']==2
    assert result['summary']['cohort_subjects']=={'Young':1,'Older':1}
    assert 'OC' in result['summary']['absent_condition_pairs']['FU18_51']
    assert result['summary']['planned_side_observations_upper_bound']==4


def test_missing_pair_is_not_silently_dropped():
    directory,metadata=sample_inventory(['WBDS01walkOC']);directory.pop();metadata.pop()
    with pytest.raises(ValueError,match='Unpaired'):PLAN.inventory(directory,metadata)


def test_metadata_and_archive_must_match():
    directory,metadata=sample_inventory(['WBDS01walkOC']);metadata[0]['Subject']='2'
    with pytest.raises(ValueError,match='identity'):PLAN.inventory(directory,metadata)


@pytest.mark.parametrize('stem,environment,condition', [('WBDS01walkOS','overground','OS'),('WBDS51walkT06','treadmill','T06'),('WBDS24walkT08','treadmill','T08')])
def test_full_adapter_keeps_condition_and_leg_identity(stem,environment,condition):
    angles={'Time':list(range(101)),'RHipAngleZ':[30.]*101,'LHipAngleZ':[40.]*101}
    moments={'Time':list(range(101)),'RKneeMomentZ':[2.]*101,'LKneeMomentZ':[3.]*101}
    rows=PAIR.expanded_rows(angles,moments,stem,BASE)
    assert len(rows)==300 and len({r['observation_id'] for r in rows})==2
    assert rows[0]['subject']=='FU18_'+stem[4:6]
    assert rows[0]['task_id']==environment+'_'+condition
    assert rows[0]['source_recording_id'].endswith(stem)
    assert rows[0]['knee_flexion_moment_ipsi_Nm_kg']==-2
    assert rows[150]['source_LHipAngleZ_deg']==40 and 'hip_flexion_angle_ipsi_rad' not in rows[150]
    for row in rows:
        info=json.loads(row['task_info']);assert info['source_condition']==condition and info['environment']==environment
        assert 'speed_m_s' not in info
        if environment=='treadmill':assert 'speed_category' not in info


def zip_fixture():
    raw=b'synthetic source text\n';name=b'51subjs/WBDS01walkOCang.txt'
    compressor=zlib.compressobj(wbits=-15);compressed=compressor.compress(raw)+compressor.flush();extra=b'EXTRA'
    crc=zlib.crc32(raw)&0xffffffff
    header=struct.pack('<I5H3I2H',0x04034b50,20,0,8,0,0,crc,len(compressed),len(raw),len(name),len(extra))
    data=header+name+extra+compressed
    member={'name':name.decode(),'offset':0,'method':8,'flags':0,'crc32':crc,'compressed_size':len(compressed),'uncompressed_size':len(raw)}
    return data,member,raw


def test_range_reader_skips_zip_extra_without_full_archive():
    data,member,expected=zip_fixture();requests=[]
    def fetch(start,size):requests.append((start,size));return data[start:start+size]
    assert RUN.member_bytes(member,fetch)==expected
    assert len(requests)==3 and requests[-1][0]==30+len(member['name'])+5
    assert sum(size for _,size in requests)==len(data)-5


def test_crc_mismatch_rejected():
    data,member,_=zip_fixture();member['crc32']^=1
    with pytest.raises(ValueError,match='CRC'):RUN.member_bytes(member,lambda start,size:data[start:start+size])


def test_zip_name_mismatch_rejected():
    data,member,_=zip_fixture();member['name']='51subjs/WBDS02walkOCang.txt'
    with pytest.raises(ValueError,match='name mismatch'):RUN.member_bytes(member,lambda start,size:data[start:start+size])


def test_unknown_condition_and_subject_rejected():
    for stem in ['WBDS52walkT01','WBDS01walkT09','WBDS01walkO01C']:
        with pytest.raises(ValueError):PAIR.protocol(stem)


@pytest.mark.parametrize('changed', [None,'source_readback.json','ensemble.parquet'])
def test_resume_binds_previous_completion_receipts(tmp_path,changed):
    stem='WBDS01walkOC';pair=tmp_path/stem;pair.mkdir()
    (pair/'source_readback.json').write_text('{"status":"synthetic"}')
    (pair/'ensemble.parquet').write_bytes(b'synthetic placeholder, not Parquet')
    previous={'pairs':[{'stem':stem,'readback_sha256':RUN.digest(pair/'source_readback.json'),
                        'output_sha256':RUN.digest(pair/'ensemble.parquet')}]}
    if changed:
        (pair/changed).write_bytes(b'changed evidence')
        with pytest.raises(ValueError,match='receipt changed'):
            RUN.verify_previous_receipts(previous,tmp_path,{stem})
    else:
        RUN.verify_previous_receipts(previous,tmp_path,{stem})
        with pytest.raises(ValueError,match='identity'):
            RUN.verify_previous_receipts(previous,tmp_path,set())
        previous['pairs']*=2
        with pytest.raises(ValueError,match='duplicate'):
            RUN.verify_previous_receipts(previous,tmp_path,{stem})
