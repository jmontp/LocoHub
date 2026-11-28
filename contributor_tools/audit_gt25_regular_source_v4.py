"""Independent bounded GT25 regular-record source/event audit, plan-only default.

Imports a hash-checked v4 *audit* oracle, never converter/event implementations.
Raw selected CSVs are independently streamed to SQLite; outputs are read150rows.
"""
import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import resource
import sqlite3
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.run_gt25_normalization_pilot_v4 import digest,verify
from contributor_tools.preserve_mblue_planar_estimates import headroom,windows_available_mib
AUDIT_SHA='800dcf9af5f99269da9ac461ae40f564b2193b1f52459d860654637310379138'


def oracle(snapshot):
    path=Path(snapshot)/'contributor_tools/audit_gt25_streaming_transfer_normalization_v4.py'
    if digest(path)!=AUDIT_SHA:raise ValueError('Independent v4 oracle hash differs')
    spec=importlib.util.spec_from_file_location('gt25_independent_v4_oracle',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def quantile(values,p):
    values=sorted(values)
    if not values:raise ValueError('Empty quantile')
    position=(len(values)-1)*p;low=int(position);weight=position-low
    return values[low] if not weight else values[low]*(1-weight)+values[low+1]*weight


def task_identity(recording):
    if recording.startswith('sit_to_stand_'):return 'sit_to_stand','sit_to_stand'
    if recording.startswith('stairs_'):
        if '_up_' in recording:return 'stair_ascent','stair_ascent'
        if '_down_' in recording:return 'stair_descent','stair_descent'
    if recording.startswith('normal_walk_'):
        if '_shuffle_' in recording:return 'level_walking','level_0.4ms'
        for token,speed in [('0-6','0.6'),('1-2','1.2'),('1-8','1.8')]:
            if '_'+token+'_' in recording:return 'level_walking','level_'+speed+'ms'
    if recording.startswith('walk_backward_'):
        for token,speed in [('0-6','0.6'),('0-8','0.8'),('1-0','1.0')]:
            if '_'+token+'_' in recording:return 'walk_backward','backward_'+speed+'ms'
    raise ValueError('Unresolved source task; cannot audit canonical coverage')


def expected_task_metadata(recording,reference,transfer):
    task,task_id=task_identity(recording)
    variants=[v for v in ('baseline','4t4s','0task') if '_'+v+'_' in recording]
    if len(variants)!=1 or not recording.endswith('_on'):raise ValueError('Unresolved source model or powered state')
    result={'leg':reference,'model':variants[0],'exo_state':'powered','exo_joints':'hip_knee','incline_deg':0.,'source_grf_frame':'OpenSim_global_y_vertical','horizontal_grf_alignment':'unresolved_trial_forward_and_anatomical_lateral_axes','cop_frame':'OpenSim_calcn_foot_frame','cop_vertical_status':'unavailable_in_source','segment_angle_method':'virtual_IMU_integration_with_converter_initialization','grf_normalization_basis':'participant_mass_without_exoskeleton_times_9.81','moment_semantics':'canonical_withheld_source_Nm_per_kg_denominator_unverified','assistance_moment_semantics':'canonical_withheld_source_interaction_units_unverified','phase_boundary_method':'inferred_transfer_from_grf_and_joint_velocity' if transfer else 'vertical_force_upward_20N_crossing'}
    if task in ('level_walking','walk_backward'):result['speed_m_s']=float(task_id.split('_',1)[1][:-2])
    if '_shuffle_' in recording:result['source_variant']='shuffle'
    return result


def check_clocks(db,meta):
    if 'angle_filt' not in meta or meta['angle_filt']['rows']<2:raise ValueError('Incomplete source clock')
    count=meta['angle_filt']['rows']
    for kind,info in meta.items():
        if info['rows']!=count:raise ValueError('Source row counts differ')
        if db.execute(f'SELECT 1 FROM (SELECT c0,lag(c0) OVER(ORDER BY i) AS prior FROM {kind}) WHERE c0 IS NULL OR c0<=prior LIMIT 1').fetchone():raise ValueError('Source clock invalid')
        if db.execute(f'SELECT 1 FROM angle_filt a JOIN {kind} b ON a.i=b.i WHERE abs(a.c0-b.c0)>1e-9 LIMIT 1').fetchone():raise ValueError('Source clocks differ')
    return count


def gait_events(db,column,leg,guard=lambda:None):
    """Independent SQL five-point edge-smoothed contacts, full exclusion ledger."""
    count=db.execute('SELECT count(*) FROM angle_filt').fetchone()[0]
    if count<2:raise ValueError('Source clock needs at least two samples')
    maximum=db.execute(f'SELECT max({column}) FROM grf').fetchone()[0]
    if maximum is None:raise ValueError('No assessed source force; cannot validate no-events')
    # This legacy converter heuristic is exposed, not endorsed as a unit proof.
    threshold=.05 if maximum<10 else 20.
    db.execute('CREATE TEMP TABLE IF NOT EXISTS clock_deltas(d REAL)');db.execute('DELETE FROM clock_deltas')
    db.execute('INSERT INTO clock_deltas SELECT c0-lag(c0) OVER(ORDER BY i) FROM angle_filt')
    total=db.execute('SELECT count(*) FROM clock_deltas WHERE d IS NOT NULL').fetchone()[0]
    middle=[v[0] for v in db.execute('SELECT d FROM clock_deltas WHERE d IS NOT NULL ORDER BY d LIMIT 2 OFFSET ?',((total-1)//2,))]
    median=middle[0] if total%2 else sum(middle)/2
    minimum=int(.3/median)
    edge_first=db.execute(f'SELECT {column} FROM grf ORDER BY i LIMIT 1').fetchone()[0];edge_last=db.execute(f'SELECT {column} FROM grf ORDER BY i DESC LIMIT 1').fetchone()[0]
    query=f'SELECT g.i,a.c0,sum(g.{column}) OVER w,count(g.{column}) OVER w FROM grf g JOIN angle_filt a ON a.i=g.i WINDOW w AS(ORDER BY g.i ROWS BETWEEN 2 PRECEDING AND 2 FOLLOWING) ORDER BY g.i'
    contacts=[];ledger=[];prior=False
    for index,t,total,valid in db.execute(query):
        if index%4096==0:guard()
        left=max(0,2-index);right=max(0,index+2-count+1);expected=5-left-right
        smoothed=None if valid!=expected or (left and edge_first is None) or (right and edge_last is None) else (total+left*(edge_first or 0)+right*(edge_last or 0))/5
        if smoothed is not None and abs(smoothed-threshold)<1e-10:raise ValueError('Ambiguous contact threshold rounding boundary')
        above=smoothed is not None and smoothed>threshold
        if above and not prior and index:
            admitted=not contacts or index-contacts[-1][0]>=minimum
            ledger.append({'kind':'contact','leg':leg,'sample':index,'time':t,'accepted':admitted,'reason':'contact_retained' if admitted else 'minimum_contact_interval'})
            if admitted:contacts.append((index,t))
        prior=above
    if len(contacts)>100000:raise ValueError('Contact ledger bound exceeded')
    candidates=[]
    for (start,t0),(end,t1) in zip(contacts,contacts[1:]):
        duration=t1-t0;valid=.5<=duration<=3.
        candidates.append({'kind':'stride','leg':leg,'start':start,'end':end,'t0':t0,'t1':t1,'duration':duration,'accepted':valid,'reason':'accepted' if valid else 'absolute_duration'})
    valid=[x['duration'] for x in candidates if x['accepted']]
    if len(valid)>=4:
        q1,q3=quantile(valid,.25),quantile(valid,.75);lo=max(.5,q1-1.5*(q3-q1));hi=min(3.,q3+1.5*(q3-q1))
        for item in candidates:
            if item['accepted'] and not lo<=item['duration']<=hi:item.update(accepted=False,reason='duration_iqr')
    return [x for x in candidates if x['accepted']],ledger+candidates,{'threshold':threshold,'raw_units':'README N','legacy_low_amplitude_BW_heuristic_triggered':maximum<10,'minimum_contact_samples':minimum,'transition_trimming':0}


def gait_segment_values(read,times,imu_dt,offsets):
    import numpy as np
    target=np.linspace(times[0],times[-1],150);dt=(times[-1]-times[0])/149;result={}
    for role,leg in [('ipsi','l'),('contra','r')]:
        gyros=[read('imu_sim',f'{body}_imu_{leg}_gyro_z',optional=True) for body in ('foot','shank','thigh')]
        if gyros[0] is None:angles=[np.full(150,np.nan)]*3
        else:
            foot,shank,thigh=[value*np.pi/180 for value in gyros]
            f=np.cumsum(foot)*imu_dt+offsets[leg];s=f+np.cumsum(shank-foot)*imu_dt;t=s+np.cumsum(thigh-shank)*imu_dt
            angles=[np.interp(target,times,np.where(np.isfinite(v),v,np.nan)) for v in (f,s,t)]
        for body,angle in zip(('foot','shank','thigh'),angles):
            result[f'{body}_sagittal_angle_{role}_rad']=angle;result[f'{body}_sagittal_velocity_{role}_rad_s']=np.gradient(angle)/dt
    return result


def audit(manifest_path,snapshot,output):
    import numpy as np
    import pyarrow.parquet as pq
    source=oracle(snapshot);manifest_path=Path(manifest_path).resolve();output=Path(output).resolve()
    if output.exists():raise FileExistsError('Preserve existing audit')
    manifest=json.loads(manifest_path.read_text());subject=manifest['subject'];recording=manifest['recording'];transfer=recording.startswith('sit_to_stand_')
    if manifest['dataset']!='gt25' or manifest['source']!='Parsed' or manifest['status'] not in ('converted_unreviewed','no_accepted_observations'):raise ValueError('Wrong manifest scope/status')
    task,task_id=task_identity(recording)
    bindings={str(manifest_path):digest(manifest_path),str(Path(__file__).resolve()):digest(__file__)}
    bindings.update({s['path']:s['sha256'] for s in manifest['sources']});bindings.update({str(manifest_path.parent/x['name']):x['sha256'] for x in manifest['outputs']})
    expected_converter='3325b621e1758f18f9b61037b96fa710df48eba3cab9f590a7e35f09fd81b8f4'
    matches=[x for x in manifest['converter_code'] if Path(x['path']).name=='convert_gtech_2025_da_to_parquet.py']
    if len(matches)!=1 or matches[0]['sha256']!=expected_converter:raise ValueError('Manifest does not bind reviewed v4 converter')
    bindings.update({x['path']:x['sha256'] for x in manifest['converter_code']})
    bindings[str(Path(snapshot)/'contributor_tools/audit_gt25_streaming_transfer_normalization_v4.py')]=AUDIT_SHA
    for helper in ('run_gt25_normalization_pilot_v4.py','preserve_mblue_planar_estimates.py'):
        path=ROOT/'contributor_tools'/helper;bindings[str(path)]=digest(path)
    verify(bindings);headroom(output.parent)
    available=next(int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
    if available<3584*1024:raise MemoryError('Linux startup reserve')
    if windows_available_mib()<2816:raise MemoryError('Host startup reserve')
    output.mkdir();db=sqlite3.connect(output/'source.sqlite');db.execute('PRAGMA cache_size=-8192');db.execute('PRAGMA temp_store=FILE');started=time.monotonic();last=0
    def guard():
        nonlocal last
        now=time.monotonic()
        if now-started>3600:raise TimeoutError('Audit time limit')
        if now-last>15:
            headroom(output)
            if windows_available_mib()<2048:raise MemoryError('Host reserve')
            last=now
    try:
        prefix=f'{subject}_{recording}_';meta={};readme=None
        for item in manifest['sources']:
            path=Path(item['path'])
            if path.name=='readme.txt':readme=path;continue
            if not path.name.startswith(prefix) or path.suffix!='.csv':raise ValueError('Unexpected selected source identity')
            kind=path.stem[len(prefix):]
            if kind in meta or kind not in ('angle_filt','moment_filt','grf','velocity','insole_sim','moment_filt_bio','power','power_bio','exo','exo_sim','imu_sim'):raise ValueError('Source duplicate/unknown')
            meta[kind]=source.ingest(db,kind,path,source.columns_for(kind),guard)
        if not {'angle_filt','moment_filt','grf','velocity','insole_sim'}<=set(meta) or readme is None:raise ValueError('Missing required source evidence')
        n=check_clocks(db,meta)
        col=lambda kind,name:'c'+str(meta[kind]['header'].index(name))
        evidence=[];events=[];rules={}
        if transfer:
            force=[col('grf','fp_'+leg+'_force_y') for leg in ('l','r')];vel=[col('velocity',joint+'_'+leg+'_velocity') for joint in ('hip_flexion','knee_angle') for leg in ('l','r')]
            db.execute('CREATE TABLE raw_event AS SELECT a.i,a.c0 AS t,g.'+force[0]+'+g.'+force[1]+' AS g,CASE WHEN '+' AND '.join('v.'+c+' IS NOT NULL' for c in vel)+' THEN max('+','.join('abs(v.'+c+')' for c in vel)+')*? ELSE NULL END AS v FROM angle_filt a JOIN grf g ON a.i=g.i JOIN velocity v ON a.i=v.i',(math.pi/180,))
            source.independent_events(db,n,guard)
            for a,b,t0,t1,d,kind,cross,accepted in db.execute('SELECT * FROM expected ORDER BY start'):
                item={'start':a,'end':b,'t0':t0,'t1':t1,'duration':d,'kind':kind,'leg':'l','crossing':cross,'accepted':bool(accepted),'reason':'accepted' if accepted else 'duration_iqr'};evidence.append(item)
                if accepted:events.append(item)
            known={r['crossing'] for r in evidence}
            evidence.extend({'kind':'transfer_crossing','crossing':i,'accepted':False,'reason':'absolute_duration_or_no_bounded_interval'} for (i,) in db.execute('SELECT i FROM crossings') if i not in known)
        else:
            for leg in ('l','r'):
                accepted,ledger,rule=gait_events(db,col('grf',f'fp_{leg}_force_y'),leg,guard);events+=accepted;evidence+=ledger;rules[leg]=rule
        with (output/'event_ledger.json').open('x') as handle:json.dump({'events':evidence,'rules':rules,'source_rows':n},handle,indent=2)
        if manifest['rows']!=len(events)*150:raise ValueError('Independent complete source event coverage differs')
        if not events:
            if manifest['status']!='no_accepted_observations' or (manifest_path.parent/'phase.parquet').exists():raise ValueError('Empty source ledger differs from output')
        match=re.search(r'^'+re.escape(subject)+r':\s*([\d.]+) kg\s*\|\s*([\d.]+) kg',readme.read_text(),re.M)
        if not match:raise ValueError('Documented participant mass unavailable')
        mass=float(match[1]);readme_sha=digest(readme);imu_dt=None
        if 'imu_sim' in meta:
            lo,hi=db.execute('SELECT min(c0),max(c0) FROM imu_sim').fetchone();imu_dt=(hi-lo)/(n-1)
        def raw(kind,column,start,end,optional=False):
            if kind not in meta:
                if optional:return None
                raise ValueError('Required raw source missing')
            return source.raw_window(db,meta,kind,start,end,[column])[:,0]
        offsets={}
        if not transfer:
            for reference in ('l','r'):
                for side in ('l','r'):
                    mids=[]
                    if 'imu_sim' in meta:
                        for event in events:
                            if event['leg']!=reference:continue
                            value=np.cumsum(raw('imu_sim',f'foot_imu_{side}_gyro_z',event['start'],event['end'])*np.pi/180)*imu_dt
                            mids.append(np.mean(value[int(.15*len(value)):int(.35*len(value))]))
                    offsets[reference,side]=-float(np.mean(mids)) if mids else 0.
        errors={};checked=0
        if events:
            parquet=pq.ParquetFile(manifest_path.parent/'phase.parquet')
            if parquet.metadata.num_rows!=len(events)*150:raise ValueError('Persisted row count differs')
            batches=parquet.iter_batches(batch_size=150,use_threads=False)
            for event in events:
                guard();batch=next(batches,None)
                if batch is None or batch.num_rows!=150:raise ValueError('Incomplete phase observation')
                frame=batch.to_pandas();start,end=event['start'],event['end'];reference=event['leg'];physical='left' if reference=='l' else 'right';sid=f'gt25:Parsed/{subject}/{recording}';identity=f'{sid}:samples:{start}:{end}:{physical}'
                facts={'subject':'GT25D_'+subject,'source_recording_id':sid,'observation_id':identity,'step':identity,'source_start_sample':start,'source_end_sample':end,'reference_side':physical,'observation_type':'transfer' if transfer else 'individual_cycle'}
                for name,value in facts.items():
                    if not frame[name].eq(value).all():raise ValueError('Source identity differs: '+name)
                expected_task=event['kind'] if transfer else task;expected_id=event['kind'] if transfer else task_id
                if not frame.task.eq(expected_task).all() or not frame.task_id.eq(expected_id).all():raise ValueError('Source task/direction differs')
                required=expected_task_metadata(recording,reference,transfer)
                for text in frame.task_info:
                    info=json.loads(text)
                    if any(info.get(k)!=v for k,v in required.items()):raise ValueError('Source normalization/task metadata differs')
                if not frame.assistance_active.eq(True).all():raise ValueError('Source powered state differs')
                for unavailable in ('phase_contra','phase_contra_dot'):
                    if unavailable in frame and frame[unavailable].notna().any():raise ValueError('Unsupported contralateral phase supplied')
                for name,expected in [('source_start_time_s',event['t0']),('source_end_time_s',event['t1']),('phase_ipsi',np.linspace(0,100,150)),('time_s',np.linspace(0,event['duration'],150)),('phase_ipsi_dot',100/event['duration'])]:np.testing.assert_allclose(frame[name],expected,rtol=1e-12,atol=1e-10)
                def read(kind,column,optional=False):
                    if reference=='r':column=re.sub(r'_(l|r)(?=_|$)',lambda m:'_r' if m[1]=='l' else '_l',column)
                    return raw(kind,column,start,end,optional)
                times=raw('angle_filt','time',start,end);expected=source.expected_values(read,times,mass,event['kind'],imu_dt)
                if not transfer:expected.update(gait_segment_values(read,times,imu_dt,{leg:offsets[reference,reference if leg=='l' else ('l' if reference=='r' else 'r')] for leg in ('l','r')}))
                if len(expected)!=92:raise ValueError('Numeric source scope differs')
                current=source.compare_values(frame,expected)
                for name,error in current.items():
                    if error is not None:errors[name]=max(errors.get(name,0.),error)
                for text in frame.subject_metadata:
                    metadata=json.loads(text)
                    if metadata!={'weight_kg':mass,'weight_basis':'participant_without_exoskeleton','mass_with_worn_exo_kg':float(match[2]),'mass_source_readme_sha256':readme_sha}:raise ValueError('Participant normalization metadata differs')
                checked+=1
            if next(batches,None) is not None:raise ValueError('Extra output observations')
        verify(bindings)
        report={'status':'regular_raw_source_events_and_92_features_checked_unreviewed','scientific_approval':False,'subject':subject,'recording':recording,'observations_checked':checked,'rows_checked':checked*150,'numeric_features_checked':92 if checked else 0,'no_accepted_observations_independently_checked':not events,'whole_selected_source_clocks_checked':True,'contralateral_phase':'not supplied by source converter; reject invented finite values','scientific_blockers':(['known_conversion_error_raw_N_reinterpreted_as_BW'] if any(r.get('legacy_low_amplitude_BW_heuristic_triggered') for r in rules.values()) else []),'bindings':bindings,'event_ledger_sha256':digest(output/'event_ledger.json'),'max_error_by_feature':errors,'limitations':['Source event/transformation fidelity only; no anatomical reference approval.','Participant normalization documented; source moments denominator and interaction units unresolved, canonical values withheld.','Legacy low-amplitude GRF unit heuristic exposed in event ledger; not validated as correct unit inference.']}
        with (output/'source_comparison.json').open('x') as handle:json.dump(report,handle,indent=2)
        return report
    finally:db.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True);p.add_argument('--run',action='store_true');a=p.parse_args()
    if not a.run:print(json.dumps({'status':'audit_prepared_not_executed','manifest':str(a.manifest)}));return
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[key]='1'
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)));print(json.dumps(audit(a.manifest,a.snapshot,a.output_root)))
if __name__=='__main__':main()
