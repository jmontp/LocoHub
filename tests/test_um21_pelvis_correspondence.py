"""Synthetic same-stride tests; no original UM21 source is loaded."""
import copy,math
import pytest
from contributor_tools.audit_um21_pelvis_correspondence import stride_key,find_stride,normalize,compare,compare_components,audit

def test_explicit_side_identity_and_duplicate_rejection():
 assert stride_key([11,21,10,1])==('left',11,21)
 details=[[11,21,10,2],[11,21,10,1]]
 assert find_stride(details,('left',11,21))==1
 with pytest.raises(ValueError):find_stride(details,('left',12,21))
 with pytest.raises(ValueError):find_stride(details+details[:1],('left',11,21))

@pytest.mark.parametrize('row',[[0,10,10,1],[1,10,8,1],[1,10,9,3],[1,float('nan'),9,1]])
def test_bad_source_identity(row):
 with pytest.raises(ValueError):stride_key(row)

def test_nonzero_pelvis_distinguishes_author_minus_from_legacy_plus():
 p=[[10.]*150,[2.]*150,[3.]*150];h=[[40.]*150,[5.]*150,[6.]*150]
 r=compare_components(p,h,h,{'RPelvisAngles':p,'LPelvisAngles':None})
 assert r['pelvis_candidates']['RPelvisAngles']['author_minus_vs_stream_minus']['status']=='matched_all150'
 assert r['pelvis_candidates']['RPelvisAngles']['author_minus_vs_legacy_stream_plus']['maximum_error_deg']==20
 assert r['pelvis_candidates']['LPelvisAngles']['status']=='unassessed_missing_source_channel'

def test_interpolation_and_missingness_do_not_bridge_gaps():
 assert normalize([3.,5.])[75]==pytest.approx(3+2*75/149)
 assert math.isnan(normalize([0.,math.nan,2.])[50])
 r=compare([math.nan]*150,[math.nan]*150);assert r['status']=='unassessed_all_missing'
 r=compare([0.]*150,[0.]*149+[1.]);assert r['status']=='mismatch_or_incomplete'

def fixture(tmp_path):
 import h5py
 norm=tmp_path/'normalized.h5';raw=tmp_path/'stream.h5'
 records=[];details=[];hips=[];pelves=[]
 with h5py.File(raw,'w') as f:
  b=f.create_group('Streaming/AB04/Tread/d10');b.create_dataset('events/LHS',data=[[1,11,21]]);b.create_dataset('events/RHS',data=[[2,12,22]])
  for name,offset in [('LHipAngles',100),('RHipAngles',200),('RPelvisAngles',10),('LPelvisAngles',-10)]:
   b.create_dataset('jointAngles/'+name,data=[[offset+c*10+i for i in range(30)] for c in range(3)])
 for side,starts,offset,leg in [('right',[2,12],200,2),('left',[1,11],100,1)]:
  for a in starts:
   b=a+10;details.append([a,b,10,leg]);hips.append([normalize([offset+c*10+i for i in range(a-1,b)]) for c in range(3)]);pelves.append([normalize([10+c*10+i for i in range(a-1,b)]) for c in range(3)])
   records.append({'subject':'AB04','condition':'d10','reference_side':side,'start_frame':a,'end_frame':b,'original_normalized_task':'s1','observation_id':f'um21:Streaming/AB04/Tread/d10:{side}:frames:{a}:{b}'})
 with h5py.File(norm,'w') as f:
  b=f.create_group('Normalized/AB04/Walk/s1/in10');b.create_dataset('events/StrideDetails',data=list(zip(*details)));b.create_dataset('jointAngles/HipAngles',data=hips);b.create_dataset('jointAngles/PelvisAngles',data=pelves)
 return {'normalized':str(norm),'streaming':str(raw),'records':records,'expected_record_count':4}

def test_persisted_bilateral_components_and_candidate_evidence(tmp_path):
 r=audit(fixture(tmp_path),lambda:None)
 assert r['nonzero_pelvis_by_side']=={'left':True,'right':True}
 assert len(r['records'])==4 and not r['streaming_author_recipe_approved']
 for x in r['records']:
  assert all(c['status']=='matched_all150' for c in x['hip_components'])
  assert all(c['status']=='matched_all150' for c in x['pelvis_candidates']['RPelvisAngles']['components'])
  assert x['pelvis_candidates']['LPelvisAngles']['components'][0]['status']=='mismatch_or_incomplete'

@pytest.mark.parametrize('fault',['wrong_side','late_value','heel_strike','wrong_recording','wrong_task','zero_pelvis'])
def test_persisted_adversarial(tmp_path,fault):
 import h5py
 p=fixture(tmp_path)
 if fault=='wrong_recording':p['records'][0]['observation_id']='borrowed'
 if fault=='wrong_task':p['records'][0]['original_normalized_task']='other'
 if fault in ('wrong_side','late_value','heel_strike'):
  with h5py.File(p['streaming'],'r+') as f:
   root=f['Streaming/AB04/Tread/d10']
   if fault=='wrong_side':root['jointAngles/RHipAngles'][...]=root['jointAngles/LHipAngles'][...]
   if fault=='late_value':root['jointAngles/RHipAngles'][0,11]=999
   if fault=='heel_strike':root['events/RHS'][0,1]=13
 if fault=='zero_pelvis':
  with h5py.File(p['normalized'],'r+') as f:f['Normalized/AB04/Walk/s1/in10/jointAngles/PelvisAngles'][...]=0
 if fault in ('heel_strike','wrong_recording','wrong_task'):
  with pytest.raises((ValueError,KeyError)):audit(p,lambda:None)
 else:
  r=audit(p,lambda:None)
  if fault=='zero_pelvis':assert r['status']=='partial_unassessed_missing_bilateral_nonzero_pelvis'
  else:assert r['records'][0]['hip_components'][0]['status']=='mismatch_or_incomplete'


def test_exact_four_stride_scope(tmp_path):
 p=fixture(tmp_path);p['records'].pop()
 with pytest.raises(ValueError,match='Exact four-stride'):audit(p,lambda:None)

def test_immediate_final_plan_digest_recheck(monkeypatch,tmp_path):
 import json,types
 from contributor_tools import audit_um21_pelvis_correspondence as m
 from pathlib import Path
 path=tmp_path/'plan.json';output=tmp_path/'result.json'
 n=tmp_path/'normalized';n.write_text('synthetic');s=tmp_path/'streaming';s.write_text('synthetic')
 paths=[n,s,Path(m.__file__)]
 path.write_text(json.dumps({'output':str(output),'normalized':str(n),'streaming':str(s),'bindings':{str(x):m.digest(x) for x in paths}}));expected=m.digest(path)
 monkeypatch.setattr(m.subprocess,'run',lambda *a,**k:types.SimpleNamespace(stdout='999999999'))
 monkeypatch.setattr(m.shutil,'disk_usage',lambda p:types.SimpleNamespace(free=10*1024**3))
 from pathlib import Path
 original=Path.read_text
 def text(p,*a,**k):
  return 'MemAvailable: 99999999 kB' if str(p)=='/proc/meminfo' else original(p,*a,**k)
 from pathlib import Path
 monkeypatch.setattr(Path,'read_text',text)
 def changed(plan,guard):path.write_text('{}');return {'status':'synthetic'}
 monkeypatch.setattr(m,'audit',changed)
 with pytest.raises(ValueError,match='before output publication'):m.run(path,expected,True)
 assert not output.exists()


@pytest.mark.parametrize('missing',['normalized','streaming','auditor'])
def test_mandatory_binding_missing(tmp_path,missing):
 from contributor_tools import audit_um21_pelvis_correspondence as m
 paths={'normalized':str(tmp_path/'n'),'streaming':str(tmp_path/'s'),'auditor':m.__file__}
 plan={**paths,'bindings':{v:'a'*64 for k,v in paths.items() if k!=missing}}
 with pytest.raises(ValueError,match='mandatory'):m.bound_inputs(plan)

def test_canonical_binding_conflict(tmp_path):
 from contributor_tools import audit_um21_pelvis_correspondence as m
 plan={'normalized':str(tmp_path/'n'),'streaming':str(tmp_path/'s'),'bindings':{str(tmp_path/'n'):'a'*64,str(tmp_path/'x/../n'):'b'*64}}
 with pytest.raises(ValueError,match='Conflicting'):m.bound_inputs(plan)

@pytest.mark.parametrize('chunk,size,whole',[(16*1024**2//8+1,1,False),(None,256*1024//8+1,True)])
def test_resource_admission_without_allocation(chunk,size,whole):
 from types import SimpleNamespace
 from contributor_tools.audit_um21_pelvis_correspondence import admit
 ds=SimpleNamespace(dtype=SimpleNamespace(kind='f',itemsize=8),chunks=(chunk,) if chunk else None,size=size)
 with pytest.raises(ValueError,match='exceeds'):admit(ds,whole)
