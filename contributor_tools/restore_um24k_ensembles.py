"""Isolated UM24K S1 participant-condition ensembles. No automatic execution.

Original 101-point arrays remain in a separate source table. Interpolation never
bridges missing samples; no stride counts, durations, side or vertical GRF invented.
S2 fatigue/progression summaries are outside this ensemble export, never omitted
from the source-file disposition ledger.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'contributor_tools/conversion_scripts/UMich_2024_KneeExo'
EVIDENCE=ROOT/'docs/quality/audits/source_evidence/um24k'
TASKS={'LL':'squat','LW':'level_walking','SA':'stair_ascent','SD':'stair_descent','RA':'incline_walking','RD':'decline_walking'}
MUSCLES=('quads','VMO','VL','RF','hams','ST','BF')
EXO={'torque':'source_exo_knee_extension_torque_Nm','thighAngle':'source_thigh_anterior_to_vertical_angle_deg','shankAngle':'source_shank_anterior_to_vertical_angle_deg','kneeAngle':'source_knee_flexion_angle_deg','grf':'source_foot_sensor_force_BW'}
S1_SHA='efb525cc2166bf6bca1e1a802722f24b08a92fcd2d4e81d127855c188094f77c'
S2_SHA='3f347db39ee86441140695aa94de5ec440fc2f61f61fc0925bf74f5e669b3c8f'

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def fields(obj,expected,where):
    if not isinstance(obj,dict) or set(obj)!=set(expected):raise ValueError('Unexpected source fields: '+where)

def validate_source(data):
    import numpy as np
    data={k:v for k,v in data.items() if not k.startswith('__')}
    fields(data,('exo','emg'),'S1');fields(data['exo'],EXO,'exo');fields(data['emg'],MUSCLES,'emg')
    def array(value,shape,where):
        a=np.asarray(value)
        if a.shape!=shape or a.dtype.kind!='f' or np.isinf(a).any():raise ValueError('Invalid shape/type/infinity: '+where)
    for measure in EXO:
        fields(data['exo'][measure],TASKS,measure)
        for task in TASKS:array(data['exo'][measure][task],(101,10),measure+'.'+task)
    for muscle in MUSCLES:
        fields(data['emg'][muscle],('bare','exo'),muscle)
        for condition in ('bare','exo'):
            fields(data['emg'][muscle][condition],TASKS,muscle+'.'+condition)
            for task in TASKS:
                group=data['emg'][muscle][condition][task];fields(group,('ensemble','means'),muscle+'.'+condition+'.'+task)
                array(group['ensemble'],(101,10),'EMG ensemble');array(group['means'],(10,),'EMG means')
    return data

def info(task,condition,samples):
    result={'source_file':'dataset_S1.mat','source_doi':'10.5061/dryad.z34tmpgks','source_version':314890,'source_task':task,'condition':condition,'observation_type':'ensemble_curve','participant_identity':'Source column ordinal, not a published named participant identifier','source_samples':101,'interpolation':'Piecewise linear 101 to 150 inclusive phase samples; no bridging or extrapolating missing values','timing':'Individual cycle durations unavailable; no physical velocities or accelerations','reference_side':'Not specified by released array documentation','force_reference':'Foot sensor normalized to bodyweight; vertical direction and foot/leg attribution unresolved','torque_reference':'Exoskeleton torque in Nm, extension positive; not biological or net joint moment','segment_reference':'Anterior to vertical positive, in degrees; no inferred anatomical side','emg':'Percent MVC; quads weighted by physiological cross-sectional area, hams unweighted muscle average; source means preserved, no across-participant pooling','scientific_approval':False}
    result['output_samples']=samples
    result['table_kind']='original_source_samples' if samples==101 else 'interpolated_source_ensemble'
    if samples==101:result['interpolation']='None; exact original 101 source phase samples preserved'
    if task in ('SA','SD'):result['step_height_m']=0.1778
    if task in ('RA','RD'):result['incline_deg']=15 if task=='RA' else -15
    return json.dumps(result,sort_keys=True)

def observation(data,condition,task,column,samples):
    import numpy as np
    import pyarrow as pa
    if condition not in ('bare','exo') or task not in TASKS or not 0<=column<10 or samples not in (101,150):raise ValueError('Invalid observation selection')
    phase=np.linspace(0,100,samples);identity=f'um24k:dataset_S1.mat:{condition}:{task}:column:{column+1}'
    output={'subject':[f'UM24_COLUMN_{column+1:02d}']*samples,'condition':[condition]*samples,'task':[TASKS[task]]*samples,'source_task':[task]*samples,'source_subject_column':[column+1]*samples,'source_recording_id':[identity]*samples,'observation_id':[identity+':ensemble']*samples,'observation_type':['ensemble_curve']*samples,'reference_side':['unknown']*samples,'source_sample_count':[101]*samples,'phase_percent':phase,'task_info':[info(task,condition,samples)]*samples}
    def resample(a):return a if samples==101 else np.interp(phase,np.arange(101),a)
    for measure,name in EXO.items():output[name]=resample(data['exo'][measure][task][:,column]) if condition=='exo' else np.full(samples,np.nan)
    for muscle in MUSCLES:
        group=data['emg'][muscle][condition][task]
        output[f'source_emg_{muscle}_percent_MVC']=resample(group['ensemble'][:,column])
        output[f'source_emg_{muscle}_cycle_mean_percent_MVC']=np.full(samples,group['means'][column])
    return pa.table(output)

def prepare(output):
    output=Path(output).resolve()
    if not output.is_relative_to(ROOT/'converted_datasets/reconversion_v2') or output.exists():raise ValueError('Fresh authorized output root required')
    if digest(SOURCE/'dataset_S1.mat')!=S1_SHA or digest(SOURCE/'dataset_S2.mat')!=S2_SHA:raise ValueError('Publisher source binding differs')
    files=[SOURCE/'dataset_S1.mat',SOURCE/'dataset_S2.mat',EVIDENCE/'publisher-version.json',EVIDENCE/'publisher-files.json',EVIDENCE/'publisher-readme.txt',Path(__file__),ROOT/'contributor_tools/audit_um24k_ensembles.py']
    plan={'status':'prepared_not_run','scientific_approval':False,'output_root':str(output),'source_root':str(SOURCE),'bindings':{str(p):digest(p) for p in files},'observations':[{'condition':c,'task':t,'column':i+1} for c in ('bare','exo') for t in TASKS for i in range(10)],'scope':{'participants':10,'conditions':2,'tasks':6,'participant_condition_ensembles':120,'phase_rows':18000,'source_rows':12120},'source_file_dispositions':{'dataset_S1.mat':'All documented EMG ensembles, EMG cycle means and exo measures; strict actual schema check remains execution prerequisite.','dataset_S2.mat':'Retained original fatigue/progression/perceptual summaries; not gait-phase curves. Separate structured restoration required; not claimed converted.'},'resource_policy':'Single coordinator-scheduled worker, 768 MiB cap and external guard required; no automatic launch.'}
    output.mkdir();(output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');return plan

def run(plan_path):
    import resource
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
    import pyarrow as pa
    import pyarrow.parquet as pq
    from scipy.io import loadmat
    from contributor_tools.audit_um24k_ensembles import audit_output
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    plan_path=Path(plan_path);plan=json.loads(plan_path.read_text());output=Path(plan['output_root'])
    if output.resolve()!=plan_path.resolve().parent or not output.resolve().is_relative_to(ROOT/'converted_datasets/reconversion_v2'):raise ValueError('Authorized output scope differs')
    for p,h in plan['bindings'].items():
        if digest(p)!=h:raise ValueError('Bound input changed')
    if any((output/n).exists() for n in ('source_101.parquet','phase_150.parquet','source_readback.json')):raise FileExistsError('Preserve previous attempt')
    source=Path(plan['source_root'])/'dataset_S1.mat'
    if source.stat().st_size>1024**2:raise MemoryError('Source exceeds bounded MAT admission')
    data=validate_source(loadmat(source,simplify_cells=True))
    for samples,name in ((101,'source_101.parquet'),(150,'phase_150.parquet')):
        writer=None
        try:
            for c in ('bare','exo'):
                for t in TASKS:
                    for i in range(10):
                        table=observation(data,c,t,i,samples)
                        if writer is None:writer=pq.ParquetWriter(output/name,table.schema,compression='zstd')
                        writer.write_table(table,row_group_size=samples)
        finally:
            if writer:writer.close()
    del data
    report=audit_output(plan_path)
    for p,h in plan['bindings'].items():
        if digest(p)!=h:raise ValueError('Bound input changed after readback')
    with (output/'source_readback.json').open('x') as f:json.dump(report,f,indent=2,allow_nan=False)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-root',type=Path,required=True);parser.add_argument('--run',action='store_true');args=parser.parse_args()
    if args.run:run(args.output_root/'plan.json')
    else:print(json.dumps(prepare(args.output_root)['scope']))

if __name__=='__main__':
    import sys
    sys.path.insert(0,str(ROOT));main()
