"""Independent bounded raw-CSV transfer audit; never reads converter row stores.

Event decisions use SQL window aggregates and stable-run membership, independently
of the converter's NumPy halos and crossing-centered search implementation.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024**2),b''):h.update(b)
    return h.hexdigest()


def ingest(db, kind, path, columns, guard=lambda:None):
    # Read original CSV directly. SQL uses only generated cN identifiers.
    with Path(path).open(newline='') as stream:
        def lines():
            while True:
                line=stream.readline(1024**2+1)
                if not line:break
                if len(line)>1024**2:raise ValueError('CSV line admission exceeded')
                yield line
        reader=csv.reader(lines());full_header=next(reader);header=columns
        if len(full_header)!=len(set(full_header)) or not set(header)<=set(full_header):raise ValueError('Missing raw audit column')
        selection=[full_header.index(c) for c in header]
        if len(header)>1024 or len(header)!=len(set(header)) or 'time' not in header:raise ValueError('Invalid raw header')
        db.execute(f'CREATE TABLE {kind}(i INTEGER PRIMARY KEY,'+','.join(f'c{k} REAL' for k in range(len(header)))+')')
        previous=-math.inf;timecol=header.index('time');count=0
        for i,row in enumerate(reader):
            if len(row)!=len(full_header):raise ValueError('Raw row width differs')
            values=[float('nan') if v.strip().lower() in ('','nan','na','n/a') else float(v) for v in [row[j] for j in selection]]
            t=values[timecol]
            if not math.isfinite(t) or t<=previous:raise ValueError('Raw clock invalid')
            previous=t;db.execute(f'INSERT INTO {kind} VALUES('+','.join('?' for _ in range(len(values)+1))+')',(i,*values));count+=1
            if i%4096==0:guard()
    return {'header':header,'rows':count}


def quantile(db,table,column,p):
    n=db.execute(f'SELECT count(*) FROM {table} WHERE {column} IS NOT NULL').fetchone()[0]
    if not n:raise ValueError('Empty quantile')
    a=(n-1)*p;k=int(a)
    values=[r[0] for r in db.execute(f'SELECT {column} FROM {table} WHERE {column} IS NOT NULL ORDER BY {column} LIMIT 2 OFFSET ?',(k,))]
    return values[0] if a==k else (1-(a-k))*values[0]+(a-k)*values[1]


def independent_events(db,n,guard=lambda:None):
    """Input raw_event(i,t,g,v), where g is total N and v max abs rad/s."""
    db.execute('CREATE TABLE dt AS SELECT t-lag(t) OVER(ORDER BY i) AS d FROM raw_event')
    rate=1/quantile(db,'dt','d',.5);window=max(1,int(.3*rate))
    if window>4096:raise ValueError('Smoothing window admission exceeded')
    left=window//2;right=window-1-left
    first=db.execute('SELECT g,v FROM raw_event ORDER BY i LIMIT 1').fetchone();last=db.execute('SELECT g,v FROM raw_event ORDER BY i DESC LIMIT 1').fetchone()
    db.execute('CREATE TABLE smoothed(i INTEGER PRIMARY KEY,t REAL,g REAL,v REAL)')
    query=f'SELECT i,t,sum(g) OVER w,count(g) OVER w,sum(v) OVER w,count(v) OVER w,v FROM raw_event WINDOW w AS(ORDER BY i ROWS BETWEEN {left} PRECEDING AND {right} FOLLOWING) ORDER BY i'
    for i,t,gs,gc,vs,vc,vraw in db.execute(query):
        lp=max(0,left-i);rp=max(0,i+right-(n-1));real=window-lp-rp
        def mean(total,count,index):
            if count!=real or (lp and first[index] is None) or (rp and last[index] is None):return None
            return ((total or 0)+lp*(first[index] or 0)+rp*(last[index] or 0))/window
        g=mean(gs,gc,0);v=mean(vs,vc,1) if window>1 and n>window else vraw
        db.execute('INSERT INTO smoothed VALUES(?,?,?,?)',(i,t,g,v))
        if i%4096==0:guard()
    maximum=db.execute('SELECT max(g) FROM raw_event').fetchone()[0]
    lower,upper=(.5,.8) if maximum is not None and maximum<10 else (400.,600.)
    # Exact threshold ties remain as specified; near ties require review because
    # SQL vs NumPy accumulation may differ in the final floating bit.
    for threshold,column in [(lower,'g'),(upper,'g'),(.436,'v')]:
        if db.execute(f'SELECT 1 FROM smoothed WHERE abs({column}-?)<=1e-10 AND abs({column}-?)<=1e-10 LIMIT 1',(threshold,threshold)).fetchone():raise ValueError('Numerically ambiguous event threshold boundary')
    db.execute('CREATE TABLE classified AS SELECT *,CASE WHEN g>? THEN 1 WHEN g<? THEN 0 ELSE NULL END AS state FROM smoothed',(upper,lower))
    db.execute('CREATE TABLE held AS SELECT *,max(CASE WHEN state IS NOT NULL THEN i END) OVER(ORDER BY i) AS last_known FROM classified')
    db.execute('CREATE TABLE states AS SELECT a.i,a.t,b.state FROM held a LEFT JOIN classified b ON a.last_known=b.i')
    db.execute('CREATE TABLE crossings AS SELECT i,t,state FROM (SELECT *,lag(state) OVER(ORDER BY i) AS prior FROM states) WHERE prior IS NOT NULL AND state!=prior')
    db.execute('CREATE TABLE runs AS SELECT *,sum(CASE WHEN v IS NULL OR v>=.436 THEN 1 ELSE 0 END) OVER(ORDER BY i) AS grp FROM smoothed')
    db.execute('CREATE TABLE lowruns AS SELECT grp,min(i) AS a,max(i) AS b FROM runs WHERE v<.436 GROUP BY grp')
    db.execute('CREATE TABLE eligible AS SELECT r.i,r.t,r.v,l.a,l.b FROM runs r JOIN lowruns l ON r.grp=l.grp WHERE r.v<.436')
    db.execute('CREATE INDEX eligible_idx ON eligible(i)')
    stable=int(.3*rate);half=stable//2;margin=int(.1*rate)
    db.execute('CREATE TABLE expected(start INTEGER,end INTEGER,t0 REAL,t1 REAL,duration REAL,kind TEXT,crossing INTEGER,accepted INTEGER)')
    query='SELECT i,t,state,lag(i,1,0) OVER(ORDER BY i),lead(i,1,?) OVER(ORDER BY i) FROM crossings ORDER BY i'
    for cross,t,state,lo,hi in db.execute(query,(n,)):
        guard()
        # Backward oracle excludes index0 from the stability-count range.
        a=db.execute('SELECT max(i) FROM eligible WHERE i>=? AND i<=? AND min(i-a+1,i)>=?',(lo,cross,half)).fetchone()[0]
        b=db.execute('SELECT min(i) FROM eligible WHERE i>=? AND i<? AND b-i+1>=?',(cross,hi,half)).fetchone()[0]
        a=max(0,(cross if a is None else a)-margin,lo);b=min(n-1,(cross if b is None else b)+margin,hi)
        t0=db.execute('SELECT t FROM raw_event WHERE i=?',(a,)).fetchone()[0];t1=db.execute('SELECT t FROM raw_event WHERE i=?',(b,)).fetchone()[0]
        if .3<=t1-t0<=5.:db.execute('INSERT INTO expected VALUES(?,?,?,?,?,?,?,1)',(a,b,t0,t1,t1-t0,'sit_to_stand' if state else 'stand_to_sit',cross))
    count=db.execute('SELECT count(*) FROM expected').fetchone()[0]
    if count>=4:
        q1=quantile(db,'expected','duration',.25);q3=quantile(db,'expected','duration',.75)
        db.execute('UPDATE expected SET accepted=0 WHERE duration<? OR duration>?',(max(.3,q1-1.5*(q3-q1)),min(5.,q3+1.5*(q3-q1))))
    db.commit()


def raw_window(db,meta,kind,start,end,columns):
    import numpy as np
    if end-start+1>4096:raise ValueError('Interval admission exceeded')
    ids=[meta[kind]['header'].index(c) for c in columns]
    rows=db.execute('SELECT '+','.join('c'+str(i) for i in ids)+f' FROM {kind} WHERE i>=? AND i<=? ORDER BY i',(start,end)).fetchall()
    if len(rows)!=end-start+1:raise ValueError('Raw interval incomplete')
    return np.asarray([[math.nan if value is None else value for value in row] for row in rows],dtype=float)


def expected_values(read, times, mass, direction, imu_dt=None):
    """Independent source-column transforms; no converter functions imported."""
    import numpy as np
    target=np.linspace(times[0],times[-1],150);dt=(times[-1]-times[0])/149;result={}
    def resample(v):return np.interp(target,times,np.where(np.isfinite(v),v,np.nan))
    missing=np.full(150,np.nan)
    for role,side in [('ipsi','l'),('contra','r')]:
        for output,source,sign in [('hip_flexion','hip_flexion',1),('knee_flexion','knee_angle',-1),('ankle_dorsiflexion','ankle_angle',1)]:
            angle=resample(read('angle_filt',f'{source}_{side}'))*sign*np.pi/180
            result[f'{output}_angle_{role}_rad']=angle
            velocity=np.gradient(angle)/dt;result[f'{output}_velocity_{role}_rad_s']=velocity
            result[f'{output}_acceleration_{role}_rad_s2']=np.gradient(velocity)/dt
            result[f'{output}_moment_{role}_Nm_kg']=resample(read('moment_filt',f'{source}_{side}_moment'))*sign
            bio=read('moment_filt_bio',f'{source}_{side}_moment',optional=True)
            result[f'{output}_biological_moment_{role}_Nm_kg']=missing if bio is None else resample(bio)*sign
            exo=read('exo',f'{source.replace("flexion","angle")}_{side}_torque_interaction',optional=True) if output!='ankle_dorsiflexion' else None
            result[f'{output}_assistance_moment_{role}_Nm_kg']=missing if exo is None else resample(exo)*(-1/mass)
        result[f'grf_vertical_{role}_BW']=resample(read('grf',f'fp_{side}_force_y'))/(mass*9.81)
        for axis in ('x','z'):result[f'source_grf_global_{axis}_{role}_N']=resample(read('grf',f'fp_{side}_force_{axis}'))
        for plane in ('anterior','lateral'):result[f'grf_{plane}_{role}_BW']=missing
        for plane,axis in [('anterior','x'),('lateral','z')]:result[f'cop_{plane}_{role}_m']=resample(read('insole_sim',f'insole_{side}_cop_{axis}'))
        result[f'cop_vertical_{role}_m']=missing
        for body in ('thigh','shank','foot'):
            gyro=read('imu_sim',f'{body}_imu_{side}_gyro_z',optional=True)
            if gyro is None:angle=missing
            else:
                ax=read('imu_sim',f'{body}_imu_{side}_accel_x');ay=read('imu_sim',f'{body}_imu_{side}_accel_y')
                initial=np.arctan2(np.mean(ax[:20]),np.mean(ay[:20]))
                integrated=initial+np.cumsum(gyro*np.pi/180)*imu_dt
                neutral=np.mean(integrated[-20:] if direction=='sit_to_stand' else integrated[:20])
                angle=resample(integrated-neutral)
            result[f'{body}_sagittal_angle_{role}_rad']=angle
            result[f'{body}_sagittal_velocity_{role}_rad_s']=np.gradient(angle)/dt
    return result


def compare_values(frame,expected):
    import numpy as np
    errors={}
    for column,reference in expected.items():
        actual=frame[column].to_numpy(dtype=float)
        if not np.array_equal(np.isnan(actual),np.isnan(reference)):raise ValueError('Source missingness differs: '+column)
        np.testing.assert_allclose(actual,reference,rtol=1e-9,atol=1e-8,equal_nan=True,err_msg=column)
        finite=np.isfinite(reference);errors[column]=float(np.max(abs(actual[finite]-reference[finite]))) if finite.any() else None
    return errors


def columns_for(kind):
    columns=['time']
    if kind=='angle_filt':columns += [j+'_'+s for j in ('hip_flexion','knee_angle','ankle_angle') for s in ('l','r')]
    if kind in ('moment_filt','moment_filt_bio'):columns += [j+'_'+s+'_moment' for j in ('hip_flexion','knee_angle','ankle_angle') for s in ('l','r')]
    if kind=='grf':columns += ['fp_'+s+'_force_'+a for s in ('l','r') for a in ('x','y','z')]
    if kind=='velocity':columns += [j+'_'+s+'_velocity' for j in ('hip_flexion','knee_angle') for s in ('l','r')]
    if kind=='insole_sim':columns += ['insole_'+s+'_cop_'+a for s in ('l','r') for a in ('x','z')]
    if kind=='exo':columns += [j+'_'+s+'_torque_interaction' for j in ('hip_angle','knee_angle') for s in ('l','r')]
    if kind=='imu_sim':columns += [b+'_imu_'+s+'_'+v for b in ('thigh','shank','foot') for s in ('l','r') for v in ('gyro_z','accel_x','accel_y')]
    return columns


def audit(pilot,output):
    import os
    import resource
    import time
    import numpy as np
    import pyarrow.parquet as pq
    from contributor_tools.preserve_mblue_planar_estimates import headroom,windows_available_mib
    pilot=Path(pilot).resolve();output=Path(output).resolve()
    if output.exists():raise FileExistsError('Preserve existing independent audit')
    summary_path=pilot/'conversion_summary.json';summary=json.loads(summary_path.read_text())
    plan_path=pilot/'plan.json';plan=json.loads(plan_path.read_text());parquet_path=pilot/'phase.parquet'
    if summary['status']!='streaming_transfer_converted_unreviewed' or digest(plan_path)!=summary['plan_sha256'] or digest(parquet_path)!=summary['phase_sha256']:raise ValueError('Terminal pilot hash binding differs')
    if summary['rows']!=150*summary['observations']:raise ValueError('Output count differs')
    bindings={str(summary_path):digest(summary_path),str(plan_path):digest(plan_path),str(parquet_path):digest(parquet_path),str(Path(__file__).resolve()):digest(__file__),**plan['bindings']}
    expected_sources={s['path']:s['kind'] for s in plan['sources']}
    if {s['source_path'] for s in summary['sources']}!=set(expected_sources) or len(summary['sources'])!=len(expected_sources):raise ValueError('Source scope differs')
    for source in summary['sources']:bindings[source['source_path']]=source['source_sha256']
    started=time.monotonic();last=0.
    def guard():
        nonlocal last
        if (output/'STOP').exists():raise RuntimeError('Requested stop')
        if time.monotonic()-started>3600:raise TimeoutError('Independent audit timeout')
        if time.monotonic()-last>=15:
            headroom(output.parent)
            if windows_available_mib()<2048:raise MemoryError('Windows runtime reserve below2GiB')
            last=time.monotonic()
    # The immutable audit directory is created only after input verification.
    headroom(output.parent)
    if windows_available_mib()<2816:raise MemoryError('Windows startup reserve below2816MiB')
    def recheck():
        for path,sha in bindings.items():
            value=hashlib.sha256()
            with Path(path).open('rb') as stream:
                for b in iter(lambda:stream.read(1024**2),b''):guard();value.update(b)
            if value.hexdigest()!=sha:raise ValueError('Bound audit input changed: '+path)
    recheck();output.mkdir(parents=True,exist_ok=False)
    db=sqlite3.connect(output/'independent_raw.sqlite');db.execute('PRAGMA cache_size=-2048');db.execute('PRAGMA temp_store=FILE')
    try:
        meta={}
        for source in summary['sources']:
            kind=expected_sources[source['source_path']]
            if kind not in ('angle_filt','moment_filt','grf','velocity','insole_sim','moment_filt_bio','power','power_bio','exo','exo_sim','imu_sim'):raise ValueError('Unknown source kind')
            meta[kind]=ingest(db,kind,source['source_path'],columns_for(kind),guard)
        n=meta['angle_filt']['rows']
        for kind,info in meta.items():
            if info['rows']!=n or db.execute(f'SELECT 1 FROM angle_filt a JOIN {kind} b ON a.i=b.i WHERE abs(a.c0-b.c0)>1e-9 LIMIT 1').fetchone():raise ValueError('Whole-trial raw clocks differ')
        def col(kind,name):return 'c'+str(meta[kind]['header'].index(name))
        g=[col('grf','fp_'+s+'_force_y') for s in ('l','r')]
        v=[col('velocity',j+'_'+s+'_velocity') for j in ('hip_flexion','knee_angle') for s in ('l','r')]
        db.execute('CREATE TABLE raw_event AS SELECT a.i,a.c0 AS t,g.'+g[0]+'+g.'+g[1]+' AS g,CASE WHEN '+ ' AND '.join('v.'+c+' IS NOT NULL' for c in v)+' THEN max('+','.join('abs(v.'+c+')' for c in v)+')*? ELSE NULL END AS v FROM angle_filt a JOIN grf g ON a.i=g.i JOIN velocity v ON a.i=v.i',(math.pi/180,))
        db.execute('CREATE UNIQUE INDEX raw_event_idx ON raw_event(i)')
        independent_events(db,n,guard)
        expected_count=db.execute('SELECT count(*) FROM expected WHERE accepted=1').fetchone()[0]
        if expected_count!=summary['observations']:raise ValueError('Independent source event count differs')
        subject=plan['subject'];recording=plan['recording'];source_id=f'gt25:Parsed/{subject}/{recording}'
        readmes=[Path(p) for p in plan['bindings'] if Path(p).name=='readme.txt']
        if len(readmes)!=1:raise ValueError('Measured mass README binding missing')
        match=re.search(r'^'+re.escape(subject)+r':\s*[\d.]+ kg\s*\|\s*([\d.]+) kg',readmes[0].read_text(),re.M)
        if not match or not float(match[1])>0:raise ValueError('Source with-exo mass unavailable')
        mass=float(match[1]);imu_dt=None
        if 'imu_sim' in meta:
            lo,hi=db.execute('SELECT min(c0),max(c0) FROM imu_sim').fetchone();imu_dt=(hi-lo)/(n-1)
        parquet=pq.ParquetFile(parquet_path)
        if parquet.num_row_groups!=expected_count or parquet.metadata.num_rows!=expected_count*150 or parquet.metadata.num_columns>128:raise ValueError('Expected bounded row groups per observation')
        if any(parquet.metadata.row_group(i).num_rows!=150 for i in range(expected_count)):raise ValueError('Oversized or incomplete row group')
        errors={};checked=0
        for group,event in enumerate(db.execute('SELECT start,end,t0,t1,kind FROM expected WHERE accepted=1 ORDER BY start')):
            guard();start,end,t0,t1,kind=event;frame=parquet.read_row_group(group).to_pandas(use_threads=False)
            if len(frame)!=150:raise ValueError('Incomplete150sample observation')
            identity=f'{source_id}:samples:{start}:{end}:left'
            facts={'subject':'GT25D_'+subject,'observation_id':identity,'step':identity,'source_recording_id':source_id,'reference_side':'left','observation_type':'transfer','source_start_sample':start,'source_end_sample':end,'task':kind,'task_id':kind,'assistance_active':True}
            for column,value in facts.items():
                if not frame[column].eq(value).all():raise ValueError('Observation identity/metadata differs: '+column)
            for column,value in [('source_start_time_s',t0),('source_end_time_s',t1)]:np.testing.assert_allclose(frame[column],value,rtol=0,atol=1e-10)
            np.testing.assert_allclose(frame.phase_ipsi,np.linspace(0,100,150),rtol=0,atol=1e-12)
            np.testing.assert_allclose(frame.time_s,np.linspace(0,t1-t0,150),rtol=0,atol=1e-10)
            np.testing.assert_allclose(frame.phase_ipsi_dot,100/(t1-t0),rtol=1e-12)
            if any(json.loads(x)!={'weight_kg':mass,'weight_basis':'source_model_including_worn_exo'} for x in frame.subject_metadata):raise ValueError('Measured mass metadata differs')
            variants=[v for v in ('baseline','4t4s','0task') if '_'+v+'_' in recording]
            if len(variants)!=1:raise ValueError('Ambiguous source model variant')
            required_info={'model':variants[0],'leg':'l','exo_state':'powered','exo_joints':'hip_knee','incline_deg':0.0,'phase_boundary_method':'inferred_transfer_from_grf_and_joint_velocity','source_grf_frame':'OpenSim_global_y_vertical','horizontal_grf_alignment':'unresolved_trial_forward_and_anatomical_lateral_axes','cop_frame':'OpenSim_calcn_foot_frame','cop_vertical_status':'unavailable_in_source','moment_semantics':'source_filtered_total_joint_moment_Nm_per_source_model_kg','biological_moment_semantics':'source_total_minus_exo_interaction_when_available','segment_angle_method':'virtual_IMU_integration_with_converter_initialization'}
            if any(json.loads(x)!=required_info for x in frame.task_info):raise ValueError('Task/source semantics metadata differs')
            times=raw_window(db,meta,'angle_filt',start,end,['time'])[:,0]
            def read(kind,column,optional=False):
                if kind not in meta:
                    if optional:return None
                    raise ValueError('Missing required audit source')
                return raw_window(db,meta,kind,start,end,[column])[:,0]
            values=expected_values(read,times,mass,kind,imu_dt);current=compare_values(frame,values)
            for column,error in current.items():
                if error is not None:errors[column]=max(errors.get(column,0.),error)
            checked+=1
        recheck()
        report={'status':'independent_raw_transfer_events_and_values_checked_unreviewed','scientific_approval':False,'observations_checked':checked,'rows_checked':checked*150,'numeric_features_checked':len(values),'max_error_by_feature':errors,'bindings':bindings,'source_mass_with_exo_kg':mass,'event_method':'Independent SQL smoothing windows, last classified-state carry, stable-run membership and disk quantiles; no converter event or projected stores read.','limitations':['Source heuristic events and virtual IMU orientations remain model-derived; matching raw transformations is not anatomical validation.','Threshold accumulation differences within1e-10 fail closed for review.']}
        (output/'source_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
        return report
    finally:db.close()


def main():
    import os,resource
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pilot',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True);p.add_argument('--run',action='store_true');a=p.parse_args()
    if not a.run:print(json.dumps({'status':'audit_not_executed','pilot':str(a.pilot),'output':str(a.output_root)}));return
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[key]='1'
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
    r=audit(a.pilot,a.output_root);print(json.dumps({'status':r['status'],'observations_checked':r['observations_checked']}))
if __name__=='__main__':main()
