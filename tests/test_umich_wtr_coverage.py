"""Synthetic protocol boundaries must never discard an observed source cycle."""
import h5py
import numpy as np
from contributor_tools.reconvert_umich_wtr import windows


def test_all_cycles_survive_protocol_boundaries(tmp_path):
    with h5py.File(tmp_path/'source.h5','w') as f:
        e=f.create_group('events')
        for side in ['L','R']:
            e[side+'HS']=[1,11,21,31,41];e[side+'StrideTime']=[10]*4
        e['cutPoints']=np.array([[11,26],[21,36]])
        refs=[]
        for i,label in enumerate(['s2x2','d0x2']):refs.append(f.create_dataset(str(i),data=[ord(c) for c in label]).ref)
        e.create_dataset('tasks',data=np.array(refs,dtype=h5py.ref_dtype))
        result=list(windows(e,f))
    assert len(result)==8
    assert [w['status'] for w in result[:4]]==['outside_annotated_protocol','one_source_interval','crosses_interval_boundary','crosses_interval_boundary']
    assert [(w['start'],w['end']) for w in result[:4]]==[(1,11),(11,21),(21,31),(31,41)]
    assert result[2]['overlapping_intervals']==[{'index':1,'label':'d0x2','start_frame':26,'end_frame':36}]
    assert [w['side'] for w in result]==['left']*4+['right']*4
