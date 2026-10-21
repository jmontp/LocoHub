"""Small identity/receipt fixtures; no GT24 scientific source reads."""
import pytest
from contributor_tools import run_gt24_scope_completion as m


def scope():
 parsed=[{'phase':'P','subject':'S','recording':str(i),'disposition':'source_only_unmapped_task' if i<869 else 'canonical_parsed_candidate_requires_source_audit'} for i in range(2421)]
 native=[{'phase':'P','subject':'S','recording':str(i)} for i in range(1358)]
 inventory={'phases':[{'phase':'P','parsed_recordings':parsed,'dynamic_complete_recordings':native}]}
 return {'full_scope':{'parsed':list(parsed),'native':list(native)}},{'records':list(parsed[:869])},inventory


def test_exact_complete_scope():
 a,b,c=scope();p,n=m.scope_gate(a,b,c);assert (len(p),len(n))==(2421,1358)

@pytest.mark.parametrize('kind',['missing','duplicate','wrong_identity','native_missing'])
def test_reject_identity_drift(kind):
 a,b,c=scope()
 if kind=='missing':b['records'].pop()
 if kind=='duplicate':b['records'][-1]=b['records'][0]
 if kind=='wrong_identity':b['records'][-1]={**b['records'][-1],'subject':'WRONG'}
 if kind=='native_missing':a['full_scope']['native'].pop()
 with pytest.raises(ValueError):m.scope_gate(a,b,c)

@pytest.mark.parametrize('status',['prepared_not_run','corrected_raw_source_partial_unassessed','stopped_incomplete'])
def test_actual_pilot_required(status):
 with pytest.raises(ValueError):m.pilot_gate({'status':status,'scientific_approval':False,'full_adoption_allowed':False,'records':[]})


def test_two_companion_pilots_require_actual_receipts():
 with pytest.raises(ValueError):m.companion_pilot_gate({'status':'prepared_not_run'}, {})


def test_descendant_sessions_remain_owned():
 rows={1:{'ppid':0},2:{'ppid':1},3:{'ppid':2},4:{'ppid':9}}
 assert set(m.descendants(1,rows))=={1,2,3}
