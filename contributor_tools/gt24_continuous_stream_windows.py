"""Bounded row windows and whole-record facts for future GT24 streaming export.

Pure stdlib. These primitives do not convert data or imply scientific approval.
Global velocity fallback is decided over the entire recording, never per chunk.
"""
from itertools import zip_longest
import math


def aligned_rows(tables):
    if 'angle_filt' not in tables:
        raise ValueError('Angle source clock required')
    names=list(tables)
    for index,values in enumerate(zip_longest(*(iter(tables[name]) for name in names))):
        if any(value is None for value in values):raise ValueError('Source table row counts differ')
        row=dict(zip(names,values));clock=row['angle_filt']['time']
        if any(not math.isclose(value['time'],clock,rel_tol=0,abs_tol=1e-9) for value in values):raise ValueError('Source table clocks differ')
        yield row


def recording_facts(rows, velocity_columns, threshold=20.):
    count=0;first=None;last=None;interval=None;uniform=True
    events={};fallback=dict.fromkeys(velocity_columns,True)
    for row in rows:
        clock=row['angle_filt']['time']
        if not math.isfinite(clock) or (last is not None and clock<=last):raise ValueError('Invalid whole-record clock')
        if first is None:first=clock
        else:
            dt=clock-last
            if interval is None:interval=dt
            elif not math.isclose(dt,interval,rel_tol=0,abs_tol=1e-9):uniform=False
        for leg in ('l','r'):
            force=row.get('grf',{}).get(f'fp_{leg}_force_y',math.nan)
            if leg not in events and force>threshold:events[leg]=count
        for column in velocity_columns:
            if not math.isnan(row.get('velocity',{}).get(column,math.nan)):fallback[column]=False
        count+=1;last=clock
    if count<2:raise ValueError('Two continuous source rows required')
    reference=min(events,key=events.get) if events else 'l'
    return {'rows':count,'source_start_time_s':first,'source_end_time_s':last,'sampling_rate_hz':1/interval if uniform else None,'gait_reference_leg':reference,'first_vertical_force_events':events,'velocity_fallback_whole_column':fallback}


def halo_windows(rows,batch_rows=512,halo=2):
    """Yield (absolute start, window start, core length, bounded source rows)."""
    if batch_rows<1 or halo<1 or halo>batch_rows:raise ValueError('Invalid bounded window parameters')
    iterator=iter(rows);pending=[];start=0;left=0;ended=False
    while True:
        while len(pending)<left+batch_rows+halo and not ended:
            try:pending.append(next(iterator))
            except StopIteration:ended=True
        core=min(batch_rows,len(pending)-left)
        if core<=0:return
        yield start,start-left,core,pending[:left+core+halo]
        retain=min(halo,left+core)
        pending=pending[left+core-retain:]
        start+=core;left=retain
