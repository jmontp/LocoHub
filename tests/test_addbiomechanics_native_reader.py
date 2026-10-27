"""Dependency policy only; never import the real native extension or Torch."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import pytest
p=Path(__file__).parents[1]/'contributor_tools/conversion_scripts/AddBiomechanics/native_reader.py'
spec=importlib.util.spec_from_file_location('adb_loader_fixture',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

@pytest.fixture
def env(monkeypatch):
 monkeypatch.setattr(m,'sys',SimpleNamespace(modules={}))
 cls=type('Subject',(),{n:lambda self:None for n in m.REQUIRED_METHODS})
 native=SimpleNamespace(biomechanics=SimpleNamespace(SubjectOnDisk=cls))
 calls=[]
 monkeypatch.setattr(m.importlib,'import_module',lambda name:(calls.append(name),native)[1])
 monkeypatch.setattr(m.importlib.metadata,'version',lambda name:'0.10.52.1')
 return native,calls

def test_direct_extension_and_distribution_version(env):
 native,calls=env;assert m.load_reader()==(native,'0.10.52.1');assert calls==['nimblephysics_libs._nimblephysics']

@pytest.mark.parametrize('name',['torch','torch.cuda'])
def test_preexisting_torch_rejected(env,name):
 m.sys.modules[name]=object()
 with pytest.raises(RuntimeError,match='Torch'):m.load_reader()
 assert env[1]==[]

def test_import_side_effect_torch_rejected(env,monkeypatch):
 def load(name):m.sys.modules['torch']=object();return env[0]
 monkeypatch.setattr(m.importlib,'import_module',load)
 with pytest.raises(RuntimeError,match='Torch'):m.load_reader()

@pytest.mark.parametrize('missing',['readFrames','getTrialOriginalName','getMassKg'])
def test_missing_required_api(env,missing):
 delattr(env[0].biomechanics.SubjectOnDisk,missing)
 with pytest.raises(RuntimeError,match='lacks required'):m.load_reader()

def test_missing_version_fail_closed(env,monkeypatch):
 monkeypatch.setattr(m.importlib.metadata,'version',lambda name:'')
 with pytest.raises(RuntimeError,match='version'):m.load_reader()
