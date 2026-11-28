"""Independent scalar interpolation and source-field readback for UM24K S1."""
import hashlib
import json
import math
from pathlib import Path

TASK_NAMES={'LL':'squat','LW':'level_walking','SA':'stair_ascent','SD':'stair_descent','RA':'incline_walking','RD':'decline_walking'}
MUSCLES=('quads','VMO','VL','RF','hams','ST','BF')
MEASURES=[('torque','source_exo_knee_extension_torque_Nm'),('thighAngle','source_thigh_anterior_to_vertical_angle_deg'),('shankAngle','source_shank_anterior_to_vertical_angle_deg'),('kneeAngle','source_knee_flexion_angle_deg'),('grf','source_foot_sensor_force_BW')]
IDENTITY=['subject','condition','task','source_task','source_subject_column','source_recording_id','observation_id','observation_type','reference_side','source_sample_count','phase_percent','task_info']

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def nested(data,*path):
    for name in path:data=data[name] if isinstance(data,dict) else getattr(data,name)
    return data

def raw_columns(data,condition,task,column):
    result={}
    for native,target in MEASURES:result[target]=[float(v) for v in nested(data,'exo',native,task)[:,column]] if condition=='exo' else [math.nan]*101
    for muscle in MUSCLES:
        result[f'source_emg_{muscle}_percent_MVC']=[float(v) for v in nested(data,'emg',muscle,condition,task,'ensemble')[:,column]]
        result[f'source_emg_{muscle}_cycle_mean_percent_MVC']=[float(nested(data,'emg',muscle,condition,task,'means')[column])]*101
    return result

def interpolate(values,index,samples):
    if samples==101:return values[index]
    numerator=index*100;left,remainder=divmod(numerator,149)
    if remainder==0:return values[left]
    a,b=values[left],values[left+1]
    if math.isnan(a) or math.isnan(b):return math.nan
    return a+(b-a)*(remainder/149)

def verify_observation(table,data,condition,task,column,samples):
    if samples not in (101,150) or table.num_rows!=samples:raise ValueError('Exact complete source grid required')
    source=raw_columns(data,condition,task,column)
    if table.column_names!=IDENTITY+list(source):raise ValueError('Unexpected columns; no invented timing, side, variability or signals')
    identity=f'um24k:dataset_S1.mat:{condition}:{task}:column:{column+1}'
    expected={'subject':f'UM24_COLUMN_{column+1:02d}','condition':condition,'task':TASK_NAMES[task],'source_task':task,'source_subject_column':column+1,'source_recording_id':identity,'observation_id':identity+':ensemble','observation_type':'ensemble_curve','reference_side':'unknown','source_sample_count':101}
    for name,value in expected.items():
        if table[name].to_pylist()!=[value]*samples:raise ValueError('Observation identity differs: '+name)
    for i,v in enumerate(table['phase_percent'].to_pylist()):
        if v is None or not math.isclose(v,i*100/(samples-1),rel_tol=0,abs_tol=1e-12):raise ValueError('Phase grid differs')
    infos=table['task_info'].to_pylist()
    if len(set(infos))!=1:raise ValueError('Per-row provenance differs')
    info=json.loads(infos[0])
    for name,value in {'source_file':'dataset_S1.mat','source_doi':'10.5061/dryad.z34tmpgks','source_version':314890,'source_task':task,'condition':condition,'observation_type':'ensemble_curve','source_samples':101,'output_samples':samples,'table_kind':'original_source_samples' if samples==101 else 'interpolated_source_ensemble','scientific_approval':False}.items():
        if info.get(name)!=value:raise ValueError('Source provenance differs')
    for name,text in [('reference_side','Not specified'),('timing','unavailable'),('force_reference','unresolved'),('torque_reference','extension positive'),('segment_reference','Anterior to vertical positive')]:
        if text not in info.get(name,''):raise ValueError('Source limitation missing')
    if task in ('RA','RD') and info.get('incline_deg')!=(15 if task=='RA' else -15):raise ValueError('Incline differs')
    if task in ('SA','SD') and info.get('step_height_m')!=0.1778:raise ValueError('Step height differs')
    counts={}
    for name,values in source.items():
        if len(values)!=101 or any(math.isinf(v) for v in values):raise ValueError('Invalid original source signal')
        actual=table[name].to_pylist();finite=missing=0
        for i,v in enumerate(actual):
            expected=interpolate(values,i,samples)
            if v is None or math.isinf(v) or math.isnan(v)!=math.isnan(expected):raise ValueError('Source missingness differs: '+name)
            if math.isnan(expected):missing+=1;continue
            finite+=1
            if samples==101:
                import struct
                if struct.pack('d',v)!=struct.pack('d',expected):raise ValueError('Original source bits differ: '+name)
            elif not math.isclose(v,expected,rel_tol=1e-12,abs_tol=1e-12):raise ValueError('Independent source value differs: '+name)
        counts[name]={'finite_checked':finite,'missing_unassessed':missing,'assessment':'source_values_checked_not_anatomical_approval' if finite else 'unavailable_not_passed'}
    return counts

def audit_output(plan_path):
    from scipy.io import loadmat
    import pyarrow.parquet as pq
    plan_path=Path(plan_path);plan_sha=digest(plan_path);plan=json.loads(plan_path.read_text());root=Path(plan['output_root']);source=Path(plan['source_root'])/'dataset_S1.mat'
    for p,h in plan['bindings'].items():
        if digest(p)!=h:raise ValueError('Bound source or code changed')
    if source.stat().st_size>1024**2:raise MemoryError('MAT source exceeds bounded admission')
    # Separate source reader representation; no producer extraction/interpolation API.
    raw=loadmat(source,struct_as_record=False,squeeze_me=True)
    expected=[{'condition':c,'task':t,'column':i+1} for c in ('bare','exo') for t in ('LL','LW','SA','SD','RA','RD') for i in range(10)]
    if plan['observations']!=expected:raise ValueError('Full participant-condition ledger differs')
    reports={};output_hashes={}
    for samples,name in ((101,'source_101.parquet'),(150,'phase_150.parquet')):
        path=root/name
        if path.stat().st_size>16*1024**2:raise MemoryError('Output exceeds bounded admission')
        before=digest(path);file=pq.ParquetFile(path)
        if file.metadata.num_rows!=120*samples or file.metadata.num_row_groups!=120:raise ValueError('Incomplete ensemble scope')
        counts=[]
        for index,item in enumerate(expected):
            meta=file.metadata.row_group(index)
            if meta.num_rows!=samples or meta.total_byte_size>1024**2:raise ValueError('Invalid bounded observation group')
            table=file.read_row_group(index,use_threads=False)
            counts.append({'observation':item,'signals':verify_observation(table,raw,item['condition'],item['task'],item['column']-1,samples)})
        if digest(path)!=before:raise ValueError('Output changed during independent readback')
        reports[name]=counts;output_hashes[name]=before
    for p,h in plan['bindings'].items():
        if digest(p)!=h:raise ValueError('Source or code changed during readback')
    if digest(plan_path)!=plan_sha:raise ValueError('Plan changed during readback')
    return {'status':'120_participant_condition_ensembles_source_checked_unreviewed','scientific_approval':False,'plan_sha256':plan_sha,'bindings':plan['bindings'],'output_sha256':output_hashes,'scope':{'participants':10,'conditions':2,'tasks':6,'ensembles':120},'checks':reports,'source_file_dispositions':plan['source_file_dispositions'],'limits':['No individual cycles, durations, stride counts or within-participant variability available.','Source knee flexion and segment/torque directions documented; source anatomical side and foot-force direction unresolved.','Original 101-point values and EMG cycle means retained; 150-point curves explicitly interpolated.','S2 fatigue summaries remain preserved original source, not converted or silently excluded.']}
