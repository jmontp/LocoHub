"""Synthetic/import-only execution gates; no scientific source reads."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import pytest
from contributor_tools import run_gt25_newton_worker_v5 as worker
from contributor_tools import run_gt25_selected_v5 as batch


def test_actual_namespace_and_callable_provenance(tmp_path,monkeypatch):
    path=tmp_path/'contributor_tools/common/stride_segmentation.py';path.parent.mkdir(parents=True);path.write_text('# synthetic helper\n')
    gait=lambda:None;transfer=lambda:None
    helper=SimpleNamespace(__file__=str(path),segment_gait_cycles=gait,segment_sit_stand_transfers=transfer)
    converter=SimpleNamespace(segment_gait_cycles=gait,segment_sit_stand_transfers=transfer)
    monkeypatch.setitem(sys.modules,'common.stride_segmentation',helper)
    sha=worker.digest(path)
    assert worker.inspect_helper(converter,tmp_path,sha)['sha256']==sha
    converter.segment_gait_cycles=lambda:None
    with pytest.raises(ValueError,match='callable'):worker.inspect_helper(converter,tmp_path,sha)
    converter.segment_gait_cycles=gait;helper.__file__=str(tmp_path/'other.py')
    with pytest.raises(ValueError,match='Actual'):worker.inspect_helper(converter,tmp_path,sha)


def test_same_named_other_namespace_not_accepted(tmp_path,monkeypatch):
    monkeypatch.delitem(sys.modules,'common.stride_segmentation',raising=False)
    monkeypatch.setitem(sys.modules,'contributor_tools.common.stride_segmentation',SimpleNamespace())
    with pytest.raises(ValueError):worker.inspect_helper(SimpleNamespace(),tmp_path,'0'*64)


def test_storage_override_does_not_change_worker_root():
    scope={'ROOT':Path('/synthetic/snapshot')}
    exec('def ensure_storage_headroom(path): return ROOT, path',scope)
    module=SimpleNamespace(ROOT=scope['ROOT'],ensure_storage_headroom=scope['ensure_storage_headroom'])
    worker.storage_guard(module)
    assert module.ROOT==Path('/synthetic/snapshot')
    assert module.ensure_storage_headroom('output')==(worker.ROOT,'output')
    assert scope['ROOT']==Path('/synthetic/snapshot')


def report(n):
    return dict(status='regular_raw_source_events_and_92_features_checked_unreviewed',scientific_approval=False,whole_selected_source_clocks_checked=True,scientific_blockers=[],observations_checked=n,rows_checked=150*n,numeric_features_checked=92 if n else 0,no_accepted_observations_independently_checked=n==0)


def test_regular_gates_require_actual_nonempty_pilot():
    batch.regular_accept(report(2),{'rows':300},True)
    batch.regular_accept(report(0),{'rows':0},False)
    with pytest.raises(ValueError):batch.regular_accept(report(0),{'rows':0},True)
    r=report(2);r['scientific_blockers']=['bad_units']
    with pytest.raises(ValueError):batch.regular_accept(r,{'rows':300})
    r=report(2);r['whole_selected_source_clocks_checked']=False
    with pytest.raises(ValueError):batch.regular_accept(r,{'rows':300})
    with pytest.raises(ValueError):batch.regular_accept(report(2),{'rows':450})


def test_full_requires_actual_receipts(tmp_path):
    p=tmp_path/'plan.json';p.write_text(json.dumps({'kind':'pilot'}))
    with pytest.raises(FileNotFoundError):batch.prerequisite({'kind':'full','pilot_plan':str(p)})
    (tmp_path/'batch_status.json').write_text(json.dumps({'status':'prepared_not_executed'}))
    with pytest.raises(ValueError):batch.prerequisite({'kind':'full','pilot_plan':str(p)})


def test_four_distinct_family_identities():
    assert set(batch.PILOTS)=={'walking','shuffle','transfer','streaming'}
    assert len(set(batch.PILOTS.values()))==4


def test_independent_coverage_rejects_dropped_identity(tmp_path):
    from contributor_tools.audit_gt25_selected_v5_coverage import check,digest
    p=tmp_path/'plan.json';p.write_text(json.dumps({'records':[{'subject':'synthetic','recording':'one'}]}))
    (tmp_path/'batch_status.json').write_text(json.dumps({'plan_sha256':digest(p),'scientific_approval':False,'records':[]}))
    with pytest.raises(ValueError,match='identity'):check(tmp_path)


def test_cap_aware_windows_admission(monkeypatch,tmp_path):
    calls=[]
    monkeypatch.setattr(batch,'legacy_guarded',lambda *a:calls.append(a))
    monkeypatch.setattr(batch,'windows_available_mib',lambda:3000)
    batch.guarded([],tmp_path,tmp_path/'synthetic.log',768,1)
    with pytest.raises(MemoryError):batch.guarded([],tmp_path,tmp_path/'synthetic.log',1536,1)
    assert len(calls)==1
    monkeypatch.setattr(batch,'windows_available_mib',lambda:3584)
    batch.guarded([],tmp_path,tmp_path/'synthetic.log',1536,1)
    assert len(calls)==2


def test_arbitrary_valid_bindings_do_not_prove_actual_oracle(tmp_path,monkeypatch):
    snapshot=tmp_path/'snapshot';folder=tmp_path/'record';audit=tmp_path/'record_audit';audit.mkdir()
    tool=snapshot/'contributor_tools/audit_gt25_regular_source_newton_v5.py';oracle=snapshot/'contributor_tools/audit_gt25_streaming_transfer_newton_v5.py'
    plan={'snapshot':str(snapshot),'bindings':{str(tool):'a'*64,str(oracle):'b'*64}}
    record={'output':str(folder),'recording':'record','route':'regular_selected_worker'}
    monkeypatch.setattr(batch,'check_runtime',lambda *a:{})
    monkeypatch.setattr(batch,'verify',lambda b:None)
    path=audit/'source_comparison.json'
    path.write_text(json.dumps({'bindings':{},'scientific_approval':False}))
    with pytest.raises(ValueError,match='implementation'):batch.checked_record(record,plan)
    path.write_text(json.dumps({'bindings':plan['bindings'],'scientific_approval':True}))
    with pytest.raises(ValueError,match='approval'):batch.checked_record(record,plan)
