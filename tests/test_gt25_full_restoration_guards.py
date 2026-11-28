"""Coordinator mocks only; no full preparations or source data."""
import ast,json
from pathlib import Path
from types import SimpleNamespace
import pytest
from contributor_tools import run_gt25_full_restoration_v5 as m


def test_imported_prerequisites_and_closure_are_worker_only():
 tree=ast.parse(Path(m.__file__).read_text());run=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run')
 calls=[n for n in ast.walk(run) if isinstance(n,ast.Call)]
 assert not any(isinstance(n.func,ast.Name) and n.func.id in ('prerequisites','final_closure','verify') for n in calls)
 text=ast.unparse(run)
 assert 'verify-inputs' in text and 'final-closure' in text


def test_closure_worker_requires_actual_inputs_and_binds_summary(tmp_path,monkeypatch):
 plan=tmp_path/'plan.json';plan.write_text('{}');sha=m.digest(plan);calls=[]
 monkeypatch.setattr(m,'check_inputs_worker',lambda p,h:calls.append((p,h)))
 monkeypatch.setattr(m,'final_closure',lambda p:{'plan_sha256':sha,'scientific_approval':False})
 m.closure_worker(tmp_path,sha)
 assert calls==[(tmp_path,sha)] and json.loads((tmp_path/'coverage.json').read_text())['scientific_approval'] is False
 with pytest.raises(FileExistsError):m.closure_worker(tmp_path,sha)


@pytest.mark.parametrize('condition',['stop','headroom','timeout'])
def test_actual_prerequisite_worker_monitored_and_cleaned(tmp_path,monkeypatch,condition):
 from contributor_tools import preserve_mblue_planar_estimates as memory
 out=tmp_path/'run';out.mkdir();(out/'companions').mkdir();(out/'companions/plan.json').write_text('{}')
 (out/'plan.json').write_text(json.dumps({'bindings':{},'timeout_s':60}))
 clock=[0.];monkeypatch.setattr(m.time,'monotonic',lambda:clock[0]);monkeypatch.setattr(memory,'headroom',lambda p:None)
 monkeypatch.setattr(memory,'windows_available_mib',lambda:0 if condition=='headroom' and clock[0] else 100000)
 p={'pid':101,'start':'owned','state':'S','pgid':101,'ppid':1};monkeypatch.setattr(m,'process',lambda pid:p);monkeypatch.setattr(m,'descendants',lambda pid:{})
 calls=[];cleaned=[]
 def poll():
  clock[0]=61. if condition=='timeout' else 16.
  if condition=='stop':(out/'STOP').touch()
  return None
 child=SimpleNamespace(pid=101,poll=poll,returncode=None)
 def launch(args,**kwargs):calls.append(args);return child
 monkeypatch.setattr(m.subprocess,'Popen',launch);monkeypatch.setattr(m,'cleanup',lambda child,owned:cleaned.append(owned))
 with pytest.raises(RuntimeError):m.run(out)
 assert len(calls)==1 and 'verify-inputs' in calls[0] and cleaned
 state=json.loads((out/'restoration_status.json').read_text())
 assert state['status']=='stopped_incomplete' and state['owned_workers_cleaned'] is True


def test_reused_parent_does_not_adopt_unrelated_descendant():
 owned={101:{'start':'old'}};rows={101:{'start':'new'},102:{'start':'newchild'}}
 m.capture_owned(SimpleNamespace(pid=101),owned,rows)
 assert owned=={101:{'start':'old'}}
