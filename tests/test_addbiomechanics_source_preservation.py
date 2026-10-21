"""Source API mocks only; no nimble import or B3D scientific data loaded."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from enum import Enum
import sys
import numpy as np
import pandas as pd
import pytest

path=Path(__file__).parents[1]/'contributor_tools/conversion_scripts/AddBiomechanics/convert_addbiomechanics_to_parquet.py'
spec=importlib.util.spec_from_file_location('adb_preserve',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class PassType(Enum):
    kinematics=0
    lowPassFilter=1
    dynamics=2


def frame(i,trial=0,passes=1):
    return SimpleNamespace(t=i,trial=trial,missingGRFReason=PassType.kinematics,markerObservations=[('pelvis',np.array([-0.,1.,np.nan]))],rawForcePlateForces=[np.array([10.,20.,30.])],processingPasses=[SimpleNamespace(type=PassType(p%3),pos=np.array([100+p,200.,-0.]),vel=np.array([1.,2.,3.]),tau=np.array([4.,5.,6.]),groundContactForceInRootFrame=np.array([3.,2.,1.]),contact=np.array([1,0]),custom_source_property=np.array([i,p])) for p in range(passes)])

class Subject:
    def __init__(self,lengths=(65,3),mass=0.):self.lengths=lengths;self.mass=mass;self.calls=[]
    def getMassKg(self):return self.mass
    def getTrialLength(self,t):return self.lengths[t]
    def getNumTrials(self):return len(self.lengths)
    def getTrialTimestep(self,t):return .01 if t==0 else .02
    def getTrialOriginalName(self,t):return 'same_original_task'
    def getTrialName(self,t):return 'same_task_split_'+str(t)
    def getTrialSplitIndex(self,t):return t
    def getTrialNumProcessingPasses(self,t):return 1 if t==0 else 3
    def getNumProcessingPasses(self):return 3
    def getProcessingPassType(self,p):return PassType(p)
    def getOpensimFileText(self,p):return '<OpenSimDocument><Coordinate name="unusual_dof_first"/></OpenSimDocument>'
    def getContactBodies(self):return ['unexpected_left_body','unexpected_right_body']
    def readFrames(self,t,start,count,**kwargs):
        assert kwargs=={'includeSensorData':True,'includeProcessingPasses':True}
        self.calls.append((t,start,count));return [frame(i,t,1 if t==0 else 3) for i in range(start,start+count)]


def test_all_passes_arrays_flags_and_unknown_dofs_preserved():
    rows=m.extract_frame_data(frame(12,3,3),.02,0.)
    assert len(rows)==4 and {r['source_pass_index'] for r in rows}=={-1,0,1,2}
    assert all(r['time_s']==.24 and r['source_mass_kg']==0 and not r['mass_available'] for r in rows)
    raw=json.loads(rows[0]['source_fields_json']);assert raw['markerObservations'][0]['values'][1]['values'][2]=={'source_nonfinite':'NaN'}
    dynamics=json.loads(rows[3]['source_fields_json']);assert dynamics['pos']['values']==[102,200.,-0.]
    assert dynamics['type']['name']=='dynamics' and dynamics['custom_source_property']['values']==[12,2]
    assert not any('knee' in key or 'grf_vertical' in key for r in rows for key in r)


def test_exact_trial_frame_accounting_and_bounded_reads():
    subject=Subject();batches=list(m.iter_trial_records(subject,0,'Falisse2016','id','file','sha'))
    assert subject.calls==[(0,0,32),(0,32,32),(0,64,1)]
    raw=[r for batch in batches for r in batch if r['source_pass_index']==-1]
    assert len(raw)==65 and raw[-1]['time_s']==.64 and raw[-1]['task'] is None
    other=[r for b in m.iter_trial_records(subject,1,'Falisse2016','id','file','sha') for r in b]
    assert len(other)==12 and other[0]['time_s']==0
    assert raw[0]['source_recording_id']!=other[0]['source_recording_id']


@pytest.mark.parametrize('failure',['short','wrong_frame','unserializable'])
def test_failed_frames_stop_instead_of_shrinking_clock(failure):
    s=Subject((3,));original=s.readFrames
    def bad(*args,**kwargs):
        frames=original(*args,**kwargs)
        if failure=='short':return frames[:-1]
        if failure=='wrong_frame':frames[1].t=2
        else:frames[1].unsupported=object()
        return frames
    s.readFrames=bad
    with pytest.raises((ValueError,TypeError)):list(m.iter_trial_records(s,0,'Falisse2016','id','file','sha'))


def test_phase_requires_review_and_uses_physical_clock_without_contra_invention():
    df=pd.DataFrame({'source_recording_id':['one']*4,'time_s':[0.,.5,1.5,2.],'angle':[0.,1.,np.nan,4.]})
    with pytest.raises(ValueError,match='review'):m.segment_to_strides(df)
    out=m.interpolate_stride(df);assert len(out)==150 and out['phase_ipsi_dot'].eq(50.).all() and out['phase_contra'].isna().all()
    assert out['phase_ipsi'].iloc[-1]==100 and out['angle'].isna().any()
    df.loc[3,'source_recording_id']='other'
    with pytest.raises(ValueError,match='merge'):m.interpolate_stride(df)


def test_inclusive_events_not_task_grouped():
    df=pd.DataFrame({'source_recording_id':['one']*7,'time_s':np.arange(7)*.1,'grf_vertical_ipsi_N':[0.,60.,60.,0.,60.,60.,0.]})
    rows=m.segment_to_strides(df,reviewed_force_mapping=True)
    assert len(rows)==1 and len(rows[0])==4 and rows[0]['time_s'].iloc[-1]==.4


def test_streaming_file_manifest_preserves_models_all_frames_and_original(tmp_path,monkeypatch):
    monkeypatch.setattr(m,'make_guard',lambda output:lambda **kwargs:None)
    source=tmp_path/'input';source.mkdir();file=source/'synthetic.b3d';file.write_bytes(b'Artificial fixture only, no B3D payload')
    subject=Subject((3,2));monkeypatch.setitem(sys.modules,'nimblephysics',SimpleNamespace(biomechanics=SimpleNamespace(SubjectOnDisk=lambda p:subject)))
    sha=m.digest(file);output=tmp_path/'output';m.process_dataset('Falisse2016',source,output)
    manifest=json.loads((output/'manifest.json').read_text());assert manifest['canonical_dataset_complete'] is False
    assert manifest['status']=='all_source_files_preserved_unreviewed' and len(manifest['files'][0]['trials'])==2
    assert [t['frames_written'] for t in manifest['files'][0]['trials']]==[3,2]
    import pyarrow.parquet as pq
    table=pq.ParquetFile(output/'source_0000/source_frames.parquet').read(use_threads=False)
    assert table.num_rows==14 and m.digest(file)==sha
    metadata=json.loads((output/'source_0000/source_metadata.json').read_text());assert len(metadata['models'])==3
    assert (output/'source_0000/model_pass_0.osim').read_text()==subject.getOpensimFileText(0)
    with pytest.raises(FileExistsError):m.process_dataset('Falisse2016',source,output)


def test_failed_source_retains_explicit_full_file_ledger(tmp_path,monkeypatch):
    monkeypatch.setattr(m,'make_guard',lambda output:lambda **kwargs:None)
    source=tmp_path/'input';source.mkdir()
    for name in ('a.b3d','b.b3d'):(source/name).write_bytes(b'synthetic')
    subject=Subject((3,));subject.readFrames=lambda *a,**k:[]
    monkeypatch.setitem(sys.modules,'nimblephysics',SimpleNamespace(biomechanics=SimpleNamespace(SubjectOnDisk=lambda p:subject)))
    output=tmp_path/'output'
    with pytest.raises(ValueError,match='Short'):m.process_dataset('Falisse2016',source,output)
    manifest=json.loads((output/'manifest.json').read_text());assert manifest['status']=='stopped_incomplete'
    assert len(manifest['files'])==2 and manifest['files'][1]['status']=='not_started'


def test_variable_frame_pass_counts_are_accounted_not_assumed(tmp_path,monkeypatch):
    monkeypatch.setattr(m,'make_guard',lambda output:lambda **kwargs:None)
    source=tmp_path/'input';source.mkdir();(source/'a.b3d').write_bytes(b'synthetic')
    subject=Subject((3,));subject.readFrames=lambda t,start,count,**kwargs:[frame(i,t,i) for i in range(start,start+count)]
    monkeypatch.setitem(sys.modules,'nimblephysics',SimpleNamespace(biomechanics=SimpleNamespace(SubjectOnDisk=lambda p:subject)))
    output=tmp_path/'output';m.process_dataset('Falisse2016',source,output)
    trial=json.loads((output/'manifest.json').read_text())['files'][0]['trials'][0]
    assert trial['frames_written']==3 and trial['pass_rows_written']==3
    assert trial['actual_frame_pass_count_histogram']=={'0':1,'1':1,'2':1}
    assert trial['pass_count_assessment']=='frame_pass_count_differs_from_trial_header_unassessed'


def test_guard_startup_wsl_disk_and_periodic_checks(tmp_path,monkeypatch):
    guard=object.__new__(m.ResourceGuard);guard.output=tmp_path;guard.last=0;calls=[]
    guard.check=lambda **kwargs:calls.append(kwargs) or {'linux_available_mib':3000}
    monkeypatch.setattr(m.os,'statvfs',lambda p:SimpleNamespace(f_bavail=6*1024**3,f_frsize=1))
    with pytest.raises(MemoryError,match='3584'):guard(startup=True)
    guard.check=lambda **kwargs:calls.append(kwargs) or {'linux_available_mib':4000}
    guard(startup=True);guard();assert len(calls)==2
    guard(force=True);assert len(calls)==3
    monkeypatch.setattr(m.os,'statvfs',lambda p:SimpleNamespace(f_bavail=4*1024**3,f_frsize=1))
    with pytest.raises(MemoryError,match='5 GiB'):guard(force=True)


def test_runtime_guard_failure_keeps_unprocessed_inventory(tmp_path,monkeypatch):
    source=tmp_path/'input';source.mkdir();(source/'a.b3d').write_bytes(b'synthetic')
    calls=[]
    def guard(**kwargs):
        calls.append(kwargs)
        if len(calls)>1:raise MemoryError('synthetic host pressure')
    monkeypatch.setattr(m,'make_guard',lambda output:guard)
    monkeypatch.setitem(sys.modules,'nimblephysics',SimpleNamespace(biomechanics=SimpleNamespace(SubjectOnDisk=lambda p:Subject())))
    output=tmp_path/'output'
    with pytest.raises(MemoryError,match='host pressure'):m.process_dataset('Falisse2016',source,output)
    manifest=json.loads((output/'manifest.json').read_text());assert manifest['status']=='stopped_incomplete'
    assert manifest['files'][0]['status']=='not_started'


def test_historical_task_guess_is_not_canonical_source_task():
    subject=Subject((1,))
    row=next(m.iter_trial_records(subject,0,'Hamner2013','id','file','sha'))[0]
    assert row['task'] is None
    assert row['task_id']=='same_original_task'
    info=json.loads(row['task_info'])
    assert info['historical_task']=='run'
    assert info['assessment']=='historical_mapping_unreviewed'
