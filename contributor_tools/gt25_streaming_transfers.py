"""Disk-backed whole-trial transfer segmentation; isolated unreviewed proposal."""
import math
import sqlite3
from pathlib import Path
from itertools import zip_longest

from contributor_tools.gt25_projected_row_store import CHUNK_ROWS


def percentile(db, table, column, fraction):
    count=db.execute(f'SELECT count({column}) FROM {table}').fetchone()[0]
    if not count:raise ValueError('No finite percentile values')
    position=(count-1)*fraction;lower=int(position);weight=position-lower
    values=[x[0] for x in db.execute(f'SELECT {column} FROM {table} WHERE {column} IS NOT NULL ORDER BY {column} LIMIT 2 OFFSET ?', (lower,))]
    return values[0] if not weight else values[0]+(values[1]-values[0])*weight


def segment(stores, output, config, *, chunk_rows=CHUNK_ROWS, guard=lambda:None):
    """Return SQLite evidence path; accepted rows remain on disk, never a list."""
    import numpy as np
    if not 1<=chunk_rows<=CHUNK_ROWS:raise ValueError('Chunk admission exceeded')
    output=Path(output)
    if output.exists():raise FileExistsError('Preserve segmentation attempt')
    required=('angle_filt','grf','velocity')
    if any(k not in stores for k in required):raise ValueError('Missing segmentation source')
    n=stores['angle_filt'].rows
    if any(stores[k].rows!=n for k in required):raise ValueError('Segmentation row counts differ')
    db=sqlite3.connect(output)
    db.execute('PRAGMA cache_size=-2048');db.execute('PRAGMA temp_store=FILE')
    db.execute('CREATE TABLE raw(i INTEGER PRIMARY KEY,t REAL,g REAL,v REAL,dt REAL)')
    db.execute('CREATE TABLE smooth(i INTEGER PRIMARY KEY,t REAL,g REAL,v REAL)')
    db.execute('CREATE TABLE transitions(i INTEGER PRIMARY KEY,crossing INTEGER,t REAL,kind TEXT)')
    db.execute('CREATE TABLE candidates(i INTEGER PRIMARY KEY,start INTEGER,end INTEGER,start_time REAL,end_time REAL,duration REAL,kind TEXT,crossing INTEGER,crossing_time REAL,accepted INTEGER)')
    db.execute('CREATE TABLE facts(key TEXT PRIMARY KEY,value REAL)')
    previous=None;max_grf=-math.inf;finite_grf=0
    gc=stores['grf'].columns;vc=stores['velocity'].columns
    gi=[gc.index(f'fp_{side}_force_y') for side in ('l','r')]
    vi=[vc.index(f'{joint}_{side}_velocity') for joint in ('hip_flexion','knee_angle') for side in ('l','r')]
    try:
        readers=[stores[k].iter_rows(chunk_rows) for k in required]
        for entries in zip_longest(*readers):
            if any(e is None for e in entries):raise ValueError('Truncated source')
            i=entries[0][0];a,g,v=[e[1] for e in entries]
            if any(e[0]!=i for e in entries) or any(abs(x[0]-a[0])>1e-9 for x in (g,v)):raise ValueError('Segmentation clocks differ')
            total=g[gi[0]]+g[gi[1]]
            velocity=float(np.max(np.abs(np.asarray([v[k] for k in vi])* (np.pi/180.))))
            if math.isfinite(total):finite_grf+=1
            if not math.isnan(total):max_grf=max(max_grf,total)
            db.execute('INSERT INTO raw VALUES(?,?,?,?,?)',(i,a[0],total,velocity,None if previous is None else a[0]-previous));previous=a[0]
            if i%chunk_rows==0:guard()
        rate=1/percentile(db,'raw','dt',.5)
        window=max(1,int(config.smooth_window_s*rate))
        if window>4096:raise ValueError('Smoothing halo exceeds bounded admission')
        left=window//2;right=window-1-left;kernel=np.ones(window)/window
        for start in range(0,n,chunk_rows):
            guard();end=min(n,start+chunk_rows)
            lo=max(0,start-left);hi=min(n,end+right)
            rows=db.execute('SELECT t,g,v FROM raw WHERE i>=? AND i<? ORDER BY i',(lo,hi)).fetchall()
            a=np.asarray([[float('nan') if x is None else x for x in row] for row in rows])
            pads=(max(0,left-start),max(0,end+right-n))
            grf=np.convolve(np.pad(a[:,1],pads,mode='edge'),kernel,mode='valid')
            vel=np.convolve(np.pad(a[:,2],pads,mode='edge'),kernel,mode='valid') if window>1 and n>window else a[start-lo:end-lo,2]
            for offset in range(end-start):db.execute('INSERT INTO smooth VALUES(?,?,?,?)',(start+offset,float(a[start-lo+offset,0]),float(grf[offset]),float(vel[offset])))
        sitting=config.sitting_grf_threshold_BW if max_grf<10 else config.sitting_grf_threshold_N
        standing=config.standing_grf_threshold_BW if max_grf<10 else config.standing_grf_threshold_N
        current='unknown';count=0
        for i,t,g in db.execute('SELECT i,t,g FROM smooth ORDER BY i'):
            g=float('nan') if g is None else g
            state='standing' if g>standing else 'sitting' if g<sitting else current if current!='unknown' else 'transition'
            if (current,state) in (('sitting','standing'),('standing','sitting')):
                kind='sit_to_stand' if state=='standing' else 'stand_to_sit'
                db.execute('INSERT INTO transitions VALUES(?,?,?,?)',(count,i,t,kind));count+=1
            current=state
            if i%chunk_rows==0:guard()
        stable=int(config.min_stable_duration_s*rate);before=int(config.margin_before_s*rate);after=int(config.margin_after_s*rate)
        cached_start=-1;cache=[]
        def value(index):
            nonlocal cached_start,cache
            start=(index//chunk_rows)*chunk_rows
            if start!=cached_start:
                guard();cache=db.execute('SELECT t,v FROM smooth WHERE i>=? AND i<? ORDER BY i',(start,start+chunk_rows)).fetchall();cached_start=start
            t,v=cache[index-start];return t,float('nan') if v is None else v
        accepted_candidates=0
        query='SELECT crossing,t,kind,lag(crossing,1,0) OVER(ORDER BY i),lead(crossing,1,?) OVER(ORDER BY i) FROM transitions ORDER BY i'
        for cross,t,kind,lower,upper in db.execute(query,(n,)):
            guard();motion_start=motion_end=cross
            for j in range(cross,max(0,lower)-1,-1):
                if value(j)[1]<config.velocity_threshold_rad_s:
                    run=0
                    for k in range(j,max(0,j-stable),-1):
                        if value(k)[1]<config.velocity_threshold_rad_s:run+=1
                        else:break
                    if run>=stable//2:motion_start=j;break
            for j in range(cross,min(n,upper)):
                if value(j)[1]<config.velocity_threshold_rad_s:
                    run=0
                    for k in range(j,min(n,j+stable)):
                        if value(k)[1]<config.velocity_threshold_rad_s:run+=1
                        else:break
                    if run>=stable//2:motion_end=j;break
            start=max(max(0,motion_start-before),lower);end=min(min(n-1,motion_end+after),upper)
            ts=value(start)[0];te=value(end)[0];duration=te-ts
            if config.min_segment_duration_s<=duration<=config.max_segment_duration_s:
                db.execute('INSERT INTO candidates VALUES(?,?,?,?,?,?,?,?,?,1)',(accepted_candidates,start,end,ts,te,duration,kind,cross,t));accepted_candidates+=1
        low=config.min_segment_duration_s;high=config.max_segment_duration_s
        if config.use_iqr_filtering and accepted_candidates>=4:
            q1=percentile(db,'candidates','duration',.25);q3=percentile(db,'candidates','duration',.75)
            low=max(low,q1-config.iqr_multiplier*(q3-q1));high=min(high,q3+config.iqr_multiplier*(q3-q1))
            db.execute('UPDATE candidates SET accepted=0 WHERE duration<? OR duration>?',(low,high))
        db.executemany('INSERT INTO facts VALUES(?,?)',[('sample_rate',rate),('samples',n),('smooth_samples',window),('maximum_total_grf',None if max_grf==-math.inf else max_grf),('finite_total_grf_samples',finite_grf),('transitions',count),('iqr_lower',low),('iqr_upper',high)])
        db.commit()
    finally:db.close()
    return output


def accepted(path):
    db=sqlite3.connect(f'file:{Path(path).resolve()}?mode=ro',uri=True)
    try:
        for row in db.execute('SELECT start,end,start_time,end_time,duration,kind,crossing,crossing_time FROM candidates WHERE accepted=1 ORDER BY i'):
            yield dict(zip(('start_idx','end_idx','start_time_s','end_time_s','duration_s','segment_type','crossing','crossing_time_s'),row))
    finally:db.close()
