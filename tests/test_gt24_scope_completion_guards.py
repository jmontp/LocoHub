"""Mocked runtime and receipt checks; no GT24 source processing."""
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from contributor_tools import run_gt24_scope_completion as m


def test_hash_closure_worker_binds_plan_and_remains_unapproved(tmp_path,monkeypatch):
 path=tmp_path/'plan.json';path.write_text(json.dumps({'bindings':{}}));sha=m.digest(path);calls=[]
 monkeypatch.setattr(m,'closure',lambda plan:calls.append(plan) or {'status':'all_original_scope_accounted_with_explicit_scientific_gaps','scientific_approval':False,'canonical_dataset_approval':False})
 m.closure_worker(path,sha)
 receipt=m.load(tmp_path/'summary.json')
 assert receipt['coordinator_plan_sha256']==sha and receipt['scientific_approval'] is False and calls==[{'bindings':{}}]
 with pytest.raises(FileExistsError):m.closure_worker(path,sha)


@pytest.mark.parametrize('condition',['stop','headroom','overall','stage'])
def test_runtime_gate_refuses_during_closure_or_hash_stage(tmp_path,monkeypatch,condition):
 now=16.;monkeypatch.setattr(m.time,'monotonic',lambda:now)
 if condition=='stop':(tmp_path/'STOP').touch()
 if condition=='overall':now=90*24*3600+1
 def headroom(*args):
  if condition=='headroom':raise MemoryError('Runtime memory reserve')
 monkeypatch.setattr(m,'headroom',headroom)
 with pytest.raises((RuntimeError,MemoryError,TimeoutError)):
  m.runtime_gate(tmp_path,0,begin=0,timeout=1 if condition=='stage' else 100000000,check_headroom=True)


@pytest.mark.parametrize('condition',['stop','headroom','overall'])
def test_actual_stage_monitor_kills_hash_worker_on_guard_refusal(tmp_path,monkeypatch,condition):
 path=tmp_path/'plan.json';path.write_text(json.dumps({'output':str(tmp_path),'bindings':{},'mapped_plan':str(tmp_path/'mapped.json'),'companion_plan':str(tmp_path/'companions.json')}))
 (tmp_path/'mapped.json').write_text('{}');(tmp_path/'companions.json').write_text('{}')
 clock=[0.];monkeypatch.setattr(m.time,'monotonic',lambda:clock[0]);calls=[];cleaned=[]
 def headroom(root,startup):
  if condition=='headroom' and not startup:raise MemoryError('Runtime reserve')
 monkeypatch.setattr(m,'headroom',headroom)
 monkeypatch.setattr(m,'processes',lambda:{101:{'start':'original','ppid':1,'pgid':101,'state':'S'}})
 def poll():
  clock[0]=90*24*3600+1 if condition=='overall' else 16.
  if condition=='stop':(tmp_path/'STOP').touch()
  return None
 child=SimpleNamespace(pid=101,poll=poll,returncode=None)
 def launch(args,**kwargs):calls.append((args,kwargs));return child
 monkeypatch.setattr(m.subprocess,'Popen',launch);monkeypatch.setattr(m,'cleanup',lambda child,owned:cleaned.append(owned))
 with pytest.raises((RuntimeError,TimeoutError,MemoryError)):m.run(path,m.digest(path))
 assert len(calls)==1 and 'verify-bindings' in calls[0][0]
 assert callable(calls[0][1]['preexec_fn']) and calls[0][1]['start_new_session'] is True
 assert cleaned and cleaned[0][101]['start']=='original'
 assert m.load(tmp_path/'status.json')['status']=='stopped_incomplete'


def test_final_closure_is_monitored_subprocess_not_inline():
 import ast
 tree=ast.parse(Path(m.__file__).read_text());run=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run')
 calls=[n for n in ast.walk(run) if isinstance(n,ast.Call)]
 assert not any(isinstance(n.func,ast.Name) and n.func.id=='closure' for n in calls)
 final=next(n for n in calls if isinstance(n.func,ast.Name) and n.func.id=='stage' and n.args and isinstance(n.args[0],ast.Constant) and n.args[0].value=='final_closure')
 assert 'final-closure' in ast.unparse(final) and '7 * 24 * 3600' in ast.unparse(final)


def test_reused_parent_cannot_adopt_new_session_descendants():
 owned={101:{'start':'original','pgid':101}}
 rows={101:{'start':'reused','pgid':101,'ppid':1},102:{'start':'unrelated','pgid':102,'ppid':101}}
 m.capture_owned(SimpleNamespace(pid=101),owned,rows)
 assert owned=={101:{'start':'original','pgid':101}}


def test_reused_child_identity_never_overwrites_owned_identity():
 owned={101:{'start':'parent','pgid':101},102:{'start':'oldchild','pgid':102}}
 rows={101:{'start':'parent','pgid':101,'ppid':1},102:{'start':'newchild','pgid':102,'ppid':101}}
 m.capture_owned(SimpleNamespace(pid=101),owned,rows)
 assert owned[102]['start']=='oldchild'


def test_cleanup_uses_current_owned_session_not_stale_group(monkeypatch):
 owned={101:{'start':'same','pgid':101}};live={101:{'start':'same','pgid':999,'ppid':1,'state':'S'}};calls=[]
 monkeypatch.setattr(m,'processes',lambda:dict(live))
 def kill(pid,sig):
  calls.append((pid,sig))
  if sig==m.signal.SIGKILL:live.pop(pid,None)
 monkeypatch.setattr(m.os,'kill',kill);monkeypatch.setattr(m.os,'killpg',lambda *args:pytest.fail('Stale process group signaled'))
 m.cleanup(SimpleNamespace(pid=101,wait=lambda timeout:0),owned)
 assert calls[-1]==(101,m.signal.SIGKILL)
