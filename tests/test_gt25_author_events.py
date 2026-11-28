"""Synthetic MAT/CSV fixtures only; no publisher arrays are read."""
import array
import json
from pathlib import Path
import numpy as np
import pytest
from scipy.io import savemat
from contributor_tools import audit_gt25_author_events as audit


def test_synthetic_mat_preserves_legs_optional_types_and_invalids(tmp_path):
 path=tmp_path/'synthetic.mat'
 left=np.array([[0.,1.],[2.,2.],[np.nan,3.]])
 types=np.array([[2,7,11]],dtype=np.int16)
 savemat(path,{'left':left,'right':np.empty((0,2)),'types':types})
 report=audit.inspect_mat(path)
 assert report['legs']['left']['valid_rows']==1
 assert report['legs']['left']['invalid_rows']==2
 assert report['legs']['right']['status']=='empty_author_event_matrix'
 assert report['decoded_fields_exact']['types']['c_order_bytes_hex']==types.tobytes().hex()
 assert report['decoded_fields_exact']['types']['shape']==[1,3]
 assert report['optional_type_to_event_membership'].startswith('unassessed')
 json.dumps(report,allow_nan=False)


def test_unsupported_leg_schema_does_not_invent_events(tmp_path):
 path=tmp_path/'synthetic.mat';savemat(path,{'left':np.array([[1,2,3]])})
 report=audit.inspect_mat(path)
 assert report['legs']['left']['status']=='unsupported_event_matrix_schema'
 assert report['legs']['right']['status']=='missing_author_leg_field'


def clock(tmp_path,text):
 path=tmp_path/'clock.csv';path.write_text(text);return audit.scan_clock(path)


def test_literal_and_numeric_clocks_distinguished(tmp_path):
 a,_=clock(tmp_path,'time,signal\n0,1\n1,2\n')
 b,_=clock(tmp_path,'time,signal\n0.0,1\n1.0,2\n')
 assert a['literal_time_sha256']!=b['literal_time_sha256']
 assert a['float64_time_sha256']==b['float64_time_sha256']


@pytest.mark.parametrize('values',['0\nnan\n1','0\n0\n1','1\n0\n2','0\nbad\n1'])
def test_bad_clock_blocks_hypotheses(tmp_path,values):
 report,times=clock(tmp_path,'time\n'+values+'\n')
 result=audit.hypotheses(audit.interval_rows(np.array([[0.,1.]])),report,times)
 assert result['candidates']==[] and result['chosen_offset_s'] is None


def test_offsets_remain_hypotheses_never_selected(tmp_path):
 report,times=clock(tmp_path,'time\n10\n11\n12\n')
 result=audit.hypotheses(audit.interval_rows(np.array([[0.,2.]])),report,times)
 assert [x['offset_s'] for x in result['candidates']]==[0,10,10]
 assert not result['candidates'][0]['all_valid_events_contained']
 assert result['candidates'][1]['all_valid_events_contained']
 assert result['chosen_offset_s'] is None and result['canonical_cycles_approved'] is False
 assert all(x['offset_applied_to_export'] is False for x in result['candidates'])


def test_full_row_width_checked(tmp_path):
 with pytest.raises(ValueError,match='row width'):clock(tmp_path,'time,signal\n0\n')


def test_row_bound_and_periodic_stop(tmp_path,monkeypatch):
 monkeypatch.setattr(audit,'MAX_ROWS',2)
 with pytest.raises(MemoryError):clock(tmp_path,'time\n0\n1\n2\n')
 monkeypatch.setattr(audit,'MAX_ROWS',1000)
 path=tmp_path/'many.csv';path.write_text('time\n'+''.join(f'{i}\n' for i in range(513)))
 def stop():raise RuntimeError('stop fixture')
 with pytest.raises(RuntimeError,match='stop fixture'):audit.scan_clock(path,stop)


def test_conflicting_bindings_rejected(tmp_path):
 path=tmp_path/'evidence'
 with pytest.raises(ValueError,match='Conflicting'):audit.merge_bindings({str(path):'a'},{str(path):'b'})


def test_decoded_field_bound():
 with pytest.raises(MemoryError):audit.exact_array(np.zeros(100001),[0])


def run_plan(tmp_path):
 records=[{'subject':'synthetic','recording':str(i),'source_task':'synthetic'} for i in range(3)]
 plan={'bindings':{},'records':records,'memory_cap_mib':768,'timeout_s':180,'max_clock_rows':audit.MAX_ROWS,'external_exclusive_slot_required':True}
 path=tmp_path/'plan.json';path.write_text(json.dumps(plan))
 return path,plan


@pytest.mark.parametrize('failure',['headroom','timeout','stop'])
def test_run_delegates_guards_and_preserves_failure(tmp_path,monkeypatch,failure):
 from contributor_tools import run_gt25_coverage_pilot as guard
 path,plan=run_plan(tmp_path)
 def stage(command,**kw):
  assert command[:3]==['nice','-n','19']
  assert kw['timeout']==180
  if failure=='stop':
   (tmp_path/'STOP').touch();kw['storage_check'](tmp_path)
  if failure=='headroom':raise MemoryError('synthetic headroom refusal')
  raise TimeoutError('synthetic timeout')
 monkeypatch.setattr(guard,'guarded_stage',stage)
 with pytest.raises((MemoryError,TimeoutError,RuntimeError)):audit.run(path,audit.digest(path))
 assert (tmp_path/'attempt.json').exists()
 assert not (tmp_path/'event_clock_review.json').exists()


def test_run_rejects_swapped_receipt_identity(tmp_path,monkeypatch):
 from contributor_tools import run_gt25_coverage_pilot as guard
 from types import SimpleNamespace
 path,plan=run_plan(tmp_path);sha=audit.digest(path)
 def stage(*args,**kwargs):
  rows=list(reversed(plan['records']))
  (tmp_path/'event_clock_review.json').write_text(json.dumps({'status':'author_event_schema_and_clock_hypotheses_reported_unreviewed','plan_sha256':sha,'scientific_approval':False,'canonical_cycles_approved':False,'records':rows}))
  return SimpleNamespace(returncode=0)
 monkeypatch.setattr(guard,'guarded_stage',stage)
 with pytest.raises(ValueError,match='identity'):audit.run(path,sha)


def test_order_and_overlap_diagnostic_keeps_original_rows():
 result=audit.interval_rows(np.array([[3.,5.],[0.,4.],[5.,6.]]))
 assert result['ordering_and_overlap']['valid_start_order_nondecreasing'] is False
 assert result['ordering_and_overlap']['overlap_pairs']==1
 assert [r['start_s'] for r in result['rows']]==[3,0,5]
 assert result['valid_rows']==3


def test_exact_three_selected_identities():
 members=[{'subject':'synthetic','recording':t,'source_task':t,'member':{'name':t}} for t in ('ball_toss','cutting','start_stop')]
 review={'next_bounded_verification':{'selected_records':[dict(r,author_event_member=r['member']) for r in members]}}
 audit.validate_selection(members,review)
 with pytest.raises(ValueError,match='distinct'):audit.validate_selection([members[0],members[0],members[2]],review)
 changed=[dict(r) for r in members];changed[0]['member']={'name':'wrong'}
 with pytest.raises(ValueError,match='ZIP'):audit.validate_selection(changed,review)
