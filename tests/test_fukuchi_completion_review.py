"""Synthetic bytes/receipts only: no scientific arrays or conversion workers."""
import json
from pathlib import Path
import zlib
import pytest
from contributor_tools.review_fukuchi_ensemble_completion import digest, review, read_json


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value))


def fixture(tmp_path):
    root=tmp_path/'run';stem='WBDS01walkOC';sources=root/'sources';pairroot=root/'pairs'/stem
    sources.mkdir(parents=True);pairroot.mkdir(parents=True)
    members={};files={};source_hashes={}
    for kind in ('ang','knt'):
        name=stem+kind+'.txt';raw=('synthetic '+kind).encode();path=sources/name;path.write_bytes(raw)
        member={'name':'51subjs/'+name,'uncompressed_size':len(raw),'compressed_size':9,'crc32':zlib.crc32(raw)}
        members[kind]=member;files[name]={'archive_member':member['name'],'bytes':len(raw),'compressed_size':9,'crc32':member['crc32'],'sha256':digest(path)}
        source_hashes[str(path)]=digest(path)
    plan={'run_root':str(root),'source_dir':str(sources),'output_root':str(root/'pairs'),'source_doi':'synthetic DOI','archive':{'download_url':'https://example.invalid/synthetic'},'input_sha256':{},'code_sha256':{},'pairs':[{'stem':stem,'members':members,'subject':'FU18_01','condition':'OC','environment':'overground'}]}
    for filename in ('convert_fukuchi_ensemble_pair.py','check_ensemble_pilot.py'):
        code=tmp_path/filename;code.write_text('# synthetic bound code\n')
        plan['code_sha256'][str(code)]=digest(code)
    pp=tmp_path/'plan.json';write(pp,plan);psha=digest(pp)
    acq=sources/(stem+'.acquisition.json');write(acq,{'stem':stem,'plan_sha256':psha,'source_doi':plan['source_doi'],'archive_url':plan['archive']['download_url'],'whole_archive_md5_verified':False,'files':files})
    parquet=pairroot/'ensemble.parquet';parquet.write_bytes(b'synthetic opaque output; not Parquet')
    bindings={**source_hashes,str(acq):digest(acq),str(pp):psha,**plan['code_sha256']}
    mp=pairroot/'conversion_manifest.json';write(mp,{'status':'converted_ensemble_unreviewed','scientific_approval':False,'source_stem':stem,'plan_sha256':psha,'source_files':source_hashes,'rows':300,'ensembles':2,'individual_cycles':0,'output_sha256':digest(parquet),'verified_input_sha256':bindings})
    rp=pairroot/'source_readback.json';write(rp,{'status':'ensemble_source_values_checked_unreviewed','scientific_approval':False,'ensembles':2,'individual_cycles':0,'manifest_sha256':digest(mp),'verified_input_sha256':{**bindings,str(mp):digest(mp),str(parquet):digest(parquet)}})
    m=read_json(mp);m['converter_sha256']=digest(tmp_path/'convert_fukuchi_ensemble_pair.py');write(mp,m)
    r=read_json(rp);r['reviewer_sha256']=digest(tmp_path/'check_ensemble_pilot.py');r['manifest_sha256']=digest(mp);r['verified_input_sha256'][str(mp)]=digest(mp);write(rp,r)
    sp=root/'summary.json';write(sp,{'status':'explicit_subset_source_checked_unreviewed','scientific_approval':False,'plan_sha256':psha,'full_inventory_pairs':1,'completed_pairs':1,'completed_rows':300,'completed_observations':2,'pairs':[{'stem':stem,'status':'ensemble_source_values_checked_unreviewed','rows':300,'observations':2,'readback_sha256':digest(rp),'output_sha256':digest(parquet)}]})
    return pp,psha,sp,acq,mp,rp


def test_explicit_subset_remains_unapproved(tmp_path):
    pp,h,sp,*_=fixture(tmp_path)
    result=review(pp,h,sp,True)
    assert result['status']=='subset_receipts_reconciled_unreviewed'
    assert result['rows']==300 and result['subjects']==1
    assert result['scientific_approval'] is False and result['catalog_activation'] is False
    with pytest.raises(ValueError,match='completed scope'):review(pp,h,sp)


@pytest.mark.parametrize('kind',['duplicate','count','full','source','output','source_identity','archive_claim','code_binding','producer_identity'])
def test_corrupt_or_overclaimed_evidence_rejected(tmp_path,kind):
    pp,h,sp,acq,mp,rp=fixture(tmp_path);summary=read_json(sp)
    if kind=='duplicate':summary['pairs']*=2;write(sp,summary)
    elif kind=='count':summary['completed_rows']=600;write(sp,summary)
    elif kind=='full':summary['status']='all_published_ensemble_pairs_source_checked_unreviewed';write(sp,summary)
    elif kind=='source':next(acq.parent.glob('*ang.txt')).write_text('wrong source')
    elif kind=='output':(mp.parent/'ensemble.parquet').write_bytes(b'wrong output')
    elif kind=='source_identity':
        m=read_json(mp);m['source_stem']='WBDS02walkOC';write(mp,m)
    elif kind=='archive_claim':
        a=read_json(acq);a['whole_archive_md5_verified']=True;write(acq,a)
    elif kind=='producer_identity':
        m=read_json(mp);m['converter_sha256']='0'*64;write(mp,m)
    else:
        r=read_json(rp);r['verified_input_sha256'].pop(str(acq));write(rp,r)
        summary['pairs'][0]['readback_sha256']=digest(rp);write(sp,summary)
    with pytest.raises(ValueError):review(pp,h,sp,True)


def test_readback_rewrite_rejected_even_when_values_not_loaded(tmp_path):
    pp,h,sp,acq,mp,rp=fixture(tmp_path)
    report=read_json(rp);report['note']='rewritten';write(rp,report)
    with pytest.raises(ValueError,match='Changed bound artifact'):review(pp,h,sp,True)
