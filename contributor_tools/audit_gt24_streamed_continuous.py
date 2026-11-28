"""Independent bounded source readback for prepared GT24 continuous streaming.

No execution on import. Needs caller-supplied, provenance-bound expected mass
metadata, reference rule, and schema. Does not certify unsupported anatomy.
"""
import json
import math
from pathlib import Path
from contributor_tools.run_gt24_continuous_pilot import manual_derivative
from contributor_tools.stream_gt24_continuous_record import source_rows,scan
from contributor_tools.gt24_continuous_stream_windows import halo_windows
from contributor_tools.preserve_mblue_planar_estimates import digest


def checked_scalar(actual,expected,name):
    missing=actual is None or (isinstance(actual,float) and math.isnan(actual))
    expected_missing=isinstance(expected,float) and math.isnan(expected)
    if missing!=expected_missing:raise ValueError('Source missingness differs: '+name)
    if expected_missing:return False
    if isinstance(expected,(int,float)) and not isinstance(expected,bool):
        if not math.isfinite(actual) or not math.isclose(actual,expected,rel_tol=1e-8,abs_tol=1e-7):raise ValueError('Source value differs: '+name)
    elif actual!=expected:raise ValueError('Source identity/value differs: '+name)
    return True


def audit_record(record,output,expected_metadata,expected_schema,is_gait,guard):
    import pyarrow.parquet as pq
    facts,source_evidence=scan(record,guard)
    mass=expected_metadata['weight_kg']
    if not isinstance(mass,(int,float)) or not math.isfinite(mass) or mass<=0:raise ValueError('Verified positive source model mass required')
    reference=facts['gait_reference_leg'] if is_gait else 'l'
    side='left' if reference=='l' else 'right'
    recording=f"gt24:{record['phase']}/{record['subject']}/{record['recording']}"
    identity=recording+':continuous:'+side
    parquet=pq.ParquetFile(output)
    if parquet.metadata.num_rows!=facts['rows'] or not parquet.schema_arrow.equals(expected_schema,check_metadata=True):raise ValueError('Row/schema preservation differs')
    batches=iter(parquet.iter_batches(batch_size=512,use_threads=False))
    finite={};missing={};checked=set();metadata_text=None;total=0
    with source_rows(record,guard) as (rows,readers):
        for start,lo,core,window in halo_windows(rows):
            guard();batch=next(batches,None)
            if batch is None or batch.num_rows!=core:raise ValueError('Incomplete bounded readback')
            actual=batch.to_pylist();offset=start-lo;clock=[row['angle_filt']['time'] for row in window]
            expected={}
            def raw(kind,column):return [row.get(kind,{}).get(column,math.nan) for row in window]
            for role,leg in [('ipsi',reference),('contra','r' if reference=='l' else 'l')]:
                for native,canonical,sign in [('hip_flexion','hip_flexion',1),('knee_angle','knee_flexion',-1),('ankle_angle','ankle_dorsiflexion',-1)]:
                    angle=[sign*v*math.pi/180 for v in raw('angle_filt',native+'_'+leg)]
                    column=native+'_'+leg+'_velocity'
                    velocity=manual_derivative(angle,clock) if facts['velocity_fallback_whole_column'][column] else [sign*v*math.pi/180 for v in raw('velocity',column)]
                    expected[f'{canonical}_angle_{role}_rad']=angle
                    expected[f'{canonical}_velocity_{role}_rad_s']=velocity
                    expected[f'{canonical}_acceleration_{role}_rad_s2']=manual_derivative(velocity,clock)
                    for kind,table in [('moment','moment_filt'),('biological_moment','moment_filt_bio')]:expected[f'{canonical}_{kind}_{role}_Nm_kg']=[sign*v for v in raw(table,native+'_'+leg+'_moment')]
                    if record['exo_state']=='no_exo':assist=[0.]*len(window)
                    elif native=='ankle_angle':assist=[math.nan]*len(window)
                    else:assist=[-v/mass for v in raw('exo',native.replace('_flexion','_angle')+'_'+leg+'_torque_interaction')]
                    expected[f'{canonical}_assistance_moment_{role}_Nm_kg']=assist
                for kind,table,suffix,unit,scale in [('angle','angle_filt','','rad',math.pi/180),('velocity','velocity','_velocity','rad_s',math.pi/180),('moment','moment_filt','_moment','Nm_kg',1.),('biological_moment','moment_filt_bio','_moment','Nm_kg',1.)]:expected[f'source_ankle_coordinate_{kind}_{role}_{unit}']=[v*scale for v in raw(table,'ankle_angle_'+leg+suffix)]
                for axis in ('x','y','z'):expected[f'source_grf_global_{axis}_{role}_N']=raw('grf',f'fp_{leg}_force_{axis}')
                expected[f'grf_vertical_{role}_BW']=[v/(mass*9.81) for v in raw('grf',f'fp_{leg}_force_y')]
                for axis in ('anterior','lateral'):expected[f'grf_{axis}_{role}_BW']=[math.nan]*len(window)
                for canonical,native in [('anterior','x'),('lateral','z')]:expected[f'cop_{canonical}_{role}_m']=raw('insole_sim',f'insole_{leg}_cop_{native}')
                expected[f'cop_vertical_{role}_m']=[math.nan]*len(window)
                for segment in ('thigh','shank','foot'):
                    for kind,unit in [('angle','rad'),('velocity','rad_s')]:expected[f'{segment}_sagittal_{kind}_{role}_{unit}']=[math.nan]*len(window)
            constants={'subject':'GT24_'+record['subject'],'task':record['task'],'task_id':record['task_id'],'step':identity,'source_recording_id':recording,'observation_id':identity,'observation_type':'continuous_recording','reference_side':side,'source_start_time_s':facts['source_start_time_s'],'source_end_time_s':facts['source_end_time_s'],'sampling_rate_hz':facts['sampling_rate_hz'],'assistance_active':record['exo_state']=='powered'}
            expected['source_time_s']=clock;expected['time_s']=[t-facts['source_start_time_s'] for t in clock]
            for index,row in enumerate(actual):
                if json.loads(row['subject_metadata'])!=expected_metadata:raise ValueError('Bound source mass/day metadata differs')
                info=json.loads(row['task_info'])
                if metadata_text is not None and row['task_info']!=metadata_text:raise ValueError('Task provenance changes across chunks')
                metadata_text=row['task_info']
                if not math.isclose(info['sampling_rate_hz'],facts['sampling_rate_hz'],rel_tol=1e-8,abs_tol=1e-7) or info['reference_leg']!=reference or info['exo_state']!=record['exo_state']:raise ValueError('Global provenance differs')
                for role,leg in [('ipsi',reference),('contra','r' if reference=='l' else 'l')]:
                    if info['ankle_velocity_fallback'][role]!=facts['velocity_fallback_whole_column'][f'ankle_angle_{leg}_velocity']:raise ValueError('Local fallback leaked into global provenance')
                values={**constants,**{name:series[offset+index] for name,series in expected.items()}}
                checked.update(values);checked.update(('subject_metadata','task_info'))
                if set(values)|{'subject_metadata','task_info'}!=set(row):raise ValueError('Unexpected unaudited output field')
                for name,value in values.items():
                    counts=finite if checked_scalar(row[name],value,name) else missing
                    counts[name]=counts.get(name,0)+1
            total+=core
        if next(batches,None) is not None or total!=facts['rows']:raise ValueError('Extra or missing persisted source rows')
        if {name:reader.evidence() for name,reader in readers.items()}!=source_evidence:raise ValueError('Source changed across audit passes')
    return {'status':'streamed_continuous_source_checked_unreviewed','scientific_approval':False,'rows':total,'output_sha256':digest(output),'source_evidence':source_evidence,'every_output_field_checked':sorted(checked),'finite_checked_values':finite,'missing_source_values_unassessed':missing,'limitations':['Expected source mass/day metadata and task/reference policy require external hash-bound provenance','Unverified physical segment orientations and horizontal anatomical forces remain missing','Uniform source recordings only; gaps require a separate interval policy']}
