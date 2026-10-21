"""Synthetic source annotations with independently specified expected semantics."""
import h5py
import numpy as np
import pytest
from contributor_tools.reconvert_umich_stairs import stair_windows


def fixture(path, side='L', identifier='i20', bounds=(10,30)):
    f=h5py.File(path,'w');trial=f.create_group('trial');events=trial.create_group('events')
    events['newID']=np.array([ord(c) for c in identifier],dtype='uint16')
    for prefix,hs in [('L',[10,30,50]),('R',[20,40])]:
        events[prefix+'HS']=hs;events[prefix+'StrideTime']=np.diff(hs)
    refs=[]
    for index,value in enumerate(['w2s',side,bounds]):
        ds=f.create_dataset(str(index),data=[ord(c) for c in value] if isinstance(value,str) else value)
        refs.append(ds.ref)
    events.create_dataset('cutPoints',data=np.array(refs,dtype=h5py.ref_dtype).reshape(3,1))
    return f,trial


def test_source_side_and_transition_are_preserved(tmp_path):
    f,trial=fixture(tmp_path/'source.h5')
    with f:
        windows,omitted=stair_windows(trial,f,'s20dg_01')
    assert [(w['side'],w['start'],w['end'],w['task']) for w in windows]==[('left',10,30,'transition')]
    assert windows[0]['info']['transition_from']=='level_walking'
    assert windows[0]['info']['transition_to']=='stair_ascent'
    assert omitted==[{'side':'left','start':30,'end':50,'reason':'no_source_task_annotation'},
                     {'side':'right','start':20,'end':40,'reason':'no_source_task_annotation'}]


@pytest.mark.parametrize('options,condition,error',[
    ({'side':'R'},'s20dg_01','sided consecutive'),
    ({'bounds':(10,40)},'s20dg_01','sided consecutive'),
    ({'identifier':'in20'},'s20dg_01','incline/direction'),
])
def test_inconsistent_annotations_are_rejected(tmp_path,options,condition,error):
    f,trial=fixture(tmp_path/'source.h5',**options)
    with f,pytest.raises(ValueError,match=error):stair_windows(trial,f,condition)


def test_matlab_empty_is_recorded_without_inventing_a_cycle(tmp_path):
    f,trial=fixture(tmp_path/'source.h5')
    with f:
        # MATLAB HDF5 stores empty dimensions, not two actual zero samples.
        for name in ['1','2']:
            f[name].attrs['MATLAB_empty']=np.uint8(1)
        windows,omitted=stair_windows(trial,f,'s20dg_01')
    assert windows==[]
    assert len(omitted)==4
    assert omitted[-1]=={'label':'w2s','reason':'source_annotation_explicitly_empty'}
