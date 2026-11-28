"""Synthetic low-force unit regressions; no scientific data or frozen edits."""
import ast
from dataclasses import replace
from pathlib import Path
import sys
import types
import numpy as np
import pandas as pd
import pytest
from contributor_tools.prepare_gt25_newton_v5 import patch_common,patch_stream,patch_transfer_audit,patch_regular_audit,functions
from contributor_tools.common import stride_segmentation as original


def corrected():
    text=patch_common(Path(original.__file__).read_text());name='contributor_tools.common._gt25_v5_synthetic';module=types.ModuleType(name);module.__package__='contributor_tools.common';sys.modules[name]=module;exec(compile(text,name,'exec'),module.__dict__);return module


def gait(amplitude):
    n=601;force=np.zeros(n)
    for start in (50,200,350,500):force[start:start+60]=amplitude
    return pd.DataFrame({'time_s':np.arange(n)*.005,'grf_vertical_ipsi_N':force})


def config(module):return module.GaitSegmentationConfig(grf_vertical_col='grf_vertical_ipsi_N',grf_threshold_N=20.,min_stride_duration_s=.5,max_stride_duration_s=3.,skip_first_segments=0,skip_last_segments=0,use_iqr_filtering=True)


def test_five_newton_false_cycles_removed():
    new=corrected();frame=gait(5.)
    assert len(original.segment_gait_cycles(frame,config(original)))==3
    assert new.segment_gait_cycles(frame,config(new))==[]


def test_normal_load_gait_exact_boundaries_preserved_and_jump_unchanged():
    new=corrected();frame=gait(800.)
    old=original.segment_gait_cycles(frame,config(original));actual=new.segment_gait_cycles(frame,config(new))
    assert [(s.start_idx,s.end_idx,s.duration_s) for s in actual]==[(s.start_idx,s.end_idx,s.duration_s) for s in old]
    before=functions(Path(original.__file__).read_text());after=functions(patch_common(Path(original.__file__).read_text()))
    assert {name for name in before if before[name]!=after[name]}=={'segment_gait_cycles','segment_sit_stand_transfers'}


def transfer(low):
    n=1200;t=np.arange(n)*.05;force=np.full(n,.2 if low else 200.);velocity=np.zeros(n)
    for i,cross in enumerate((150,350,550,750,950)):
        force[cross:]=(5. if low else 800.) if i%2==0 else (.2 if low else 200.)
        velocity[cross-10:cross+10]=1.2
    return pd.DataFrame({'time_s':t,'grf_vertical_ipsi_N':force/2,'grf_vertical_contra_N':force/2,'velocity':velocity})


def transfer_config(module):return module.SitStandConfig(grf_vertical_ipsi_col='grf_vertical_ipsi_N',grf_vertical_contra_col='grf_vertical_contra_N',velocity_cols=('velocity',))


def test_low_force_transfer_states_not_bodyweight_scaled():
    new=corrected();frame=transfer(True)
    assert len(original.segment_sit_stand_transfers(frame,transfer_config(original)))>0
    assert new.segment_sit_stand_transfers(frame,transfer_config(new))==[]


def test_normal_load_transfer_boundaries_unchanged():
    new=corrected();frame=transfer(False)
    old=original.segment_sit_stand_transfers(frame,transfer_config(original));actual=new.segment_sit_stand_transfers(frame,transfer_config(new))
    assert len(old)>0
    assert [(s.start_idx,s.end_idx,s.segment_type) for s in actual]==[(s.start_idx,s.end_idx,s.segment_type) for s in old]


def test_explicit_source_unit_guard_rejects_bw_column():
    new=corrected();frame=gait(800.).rename(columns={'grf_vertical_ipsi_N':'grf_vertical_ipsi_BW'})
    c=replace(config(new),grf_vertical_col='grf_vertical_ipsi_BW')
    with pytest.raises(ValueError,match='explicit N'):new.segment_gait_cycles(frame,c)


def test_stream_and_independent_oracles_fixed_newtons():
    root=Path(__file__).resolve().parents[1]
    stream=patch_stream((root/'contributor_tools/gt25_streaming_transfers.py').read_text())
    assert 'sitting=config.sitting_grf_threshold_N' in stream and 'if max_grf<10' not in stream
    source='lower,upper=(.5,.8) if maximum is not None and maximum<10 else (400.,600.)'
    assert patch_transfer_audit(source).startswith('lower,upper=400.,600.')
    regular=patch_regular_audit((root/'contributor_tools/audit_gt25_regular_source_v4.py').read_text(),'a'*64,'b'*64)
    assert 'threshold=20.' in regular and 'threshold=.05' not in regular
    assert 'b'*64 in regular and 'a'*64 in regular
    ast.parse(regular)


@pytest.mark.parametrize('low',[True,False])
def test_streaming_and_independent_transfer_detector_use_same_explicit_N(tmp_path,low):
    import sqlite3
    from contributor_tools import gt25_projected_row_store as spool
    from contributor_tools import gt25_streaming_transfers as original_stream
    root=Path(__file__).resolve().parents[1]
    module=types.ModuleType('synthetic_newton_stream');exec(patch_stream((root/'contributor_tools/gt25_streaming_transfers.py').read_text()),module.__dict__)
    audit=types.ModuleType('synthetic_independent_newton');exec(patch_transfer_audit((root/'contributor_tools/audit_gt25_streaming_transfer.py').read_text()),audit.__dict__)
    frame=transfer(low);times=frame.time_s.to_numpy();velocity=frame.velocity.to_numpy()*180/np.pi
    data={'angle_filt':pd.DataFrame({'time':times}),'grf':pd.DataFrame({'time':times,'fp_l_force_y':frame.grf_vertical_ipsi_N,'fp_r_force_y':frame.grf_vertical_contra_N}),'velocity':pd.DataFrame({'time':times,**{f'{joint}_{leg}_velocity':velocity for joint in ('hip_flexion','knee_angle') for leg in ('l','r')}})}
    stores={}
    for kind,values in data.items():
        path=tmp_path/(kind+'.csv');values.to_csv(path,index=False);spool.build(path,tmp_path/kind,list(values),chunk_rows=17);stores[kind]=spool.Store(tmp_path/kind)
    cfg=transfer_config(original)
    module.segment(stores,tmp_path/'new.sqlite',cfg,chunk_rows=17);observed=list(module.accepted(tmp_path/'new.sqlite'))
    original_stream.segment(stores,tmp_path/'old.sqlite',cfg,chunk_rows=17);before=list(original_stream.accepted(tmp_path/'old.sqlite'))
    db=sqlite3.connect(':memory:');db.execute('CREATE TABLE raw_event(i INTEGER,t REAL,g REAL,v REAL)')
    db.executemany('INSERT INTO raw_event VALUES(?,?,?,?)',[(i,float(t),float(frame.grf_vertical_ipsi_N.iloc[i]*2),float(frame.velocity.iloc[i])) for i,t in enumerate(times)])
    audit.independent_events(db,len(frame));expected=list(db.execute('SELECT start,end,kind FROM expected WHERE accepted=1 ORDER BY start'))
    assert [(r['start_idx'],r['end_idx'],r['segment_type']) for r in observed]==expected
    if low:assert observed==[] and len(before)>0
    else:assert [(r['start_idx'],r['end_idx']) for r in observed]==[(r['start_idx'],r['end_idx']) for r in before]
