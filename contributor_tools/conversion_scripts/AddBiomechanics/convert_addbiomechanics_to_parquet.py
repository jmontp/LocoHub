#!/usr/bin/env python3
"""Preserve AddBiomechanics B3D source frames and processing passes in Parquet.

This adapter deliberately does not label unknown model DOFs, contact bodies or
root-frame axes as anatomical signals. It writes source arrays and their shapes,
quality flags, exact trial/frame/pass identities, and embedded model XML. No
70 kg replacement, pass-index assumption, missing-frame deletion or automatic
phase reconstruction is allowed. Existing historical files are never overwritten.
"""
import argparse
import hashlib
import json
import math
import os
import time
import importlib.util
from pathlib import Path
import sys
for _name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[_name]='1'
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).parent))
from dataset_configs import get_task_info, get_supported_datasets

FRAME_BATCH=32
MAX_FRAME_PAYLOAD_BYTES=4*1024**2
NUM_PHASE_POINTS=150


def digest(path,guard=None):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024**2),b''):
            if guard:guard()
            h.update(block)
    return h.hexdigest()


class ResourceGuard:
    def __init__(self,output):
        path=Path(__file__).parents[1]/'Fukuchi_2018_Walking/run_ensemble_pilot.py'
        spec=importlib.util.spec_from_file_location('adb_shared_host_guard',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.check=module.check_resources;self.output=Path(output);self.last=0

    def __call__(self,startup=False,force=False):
        if not (startup or force) and time.monotonic()-self.last<15:return
        result=self.check(prelaunch=startup)
        if startup and result['linux_available_mib']<3584:raise MemoryError('WSL startup requires 3584 MiB available')
        target=self.output
        while not target.exists():target=target.parent
        stat=os.statvfs(target)
        if stat.f_bavail*stat.f_frsize<5*1024**3:raise MemoryError('Preserve 5 GiB output disk reserve')
        self.last=time.monotonic()


def make_guard(output):return ResourceGuard(output)


def encode_source(value):
    """JSON-safe source values with array dtype/shape and explicit nonfinites."""
    if isinstance(value,np.ndarray):
        if value.nbytes>MAX_FRAME_PAYLOAD_BYTES:raise MemoryError('Single source array exceeds admission')
        return {'source_type':'ndarray','dtype':value.dtype.str,'shape':list(value.shape),'values':encode_source(value.tolist())}
    if isinstance(value,np.generic):return encode_source(value.item())
    if value is None or isinstance(value,(str,bool,int)):return value
    if isinstance(value,float):
        if math.isnan(value):return {'source_nonfinite':'NaN'}
        if math.isinf(value):return {'source_nonfinite':'+Infinity' if value>0 else '-Infinity'}
        return value
    if isinstance(value,(list,tuple)):return {'source_type':'tuple','values':[encode_source(v) for v in value]} if isinstance(value,tuple) else [encode_source(v) for v in value]
    if isinstance(value,dict):
        # Keys may be DOF indices or sensor labels: preserve type and ordering.
        return {'source_type':'mapping','items':[[encode_source(k),encode_source(v)] for k,v in value.items()]}
    if hasattr(value,'name') and hasattr(value,'value'):
        return {'source_type':'enum','class':type(value).__name__,'name':str(value.name),'value':encode_source(value.value)}
    raise TypeError('Unsupported source property type; do not silently omit: '+type(value).__name__)


def public_fields(obj,exclude=()):
    result={}
    for name in sorted(n for n in dir(obj) if not n.startswith('_') and n not in exclude):
        try:
            value=getattr(obj,name)
            if not callable(value):result[name]=encode_source(value)
        except Exception as error:
            raise TypeError('Cannot preserve source property '+type(obj).__name__+'.'+name+': '+str(error)) from error
    return result


def payload(fields):
    result=json.dumps(fields,sort_keys=True,separators=(',',':'),allow_nan=False)
    if len(result.encode())>MAX_FRAME_PAYLOAD_BYTES:raise MemoryError('Single frame payload exceeds admission')
    return result


def extract_frame_data(frame,timestep,mass_kg):
    """One raw-frame row plus every actual processing-pass row, without mapping."""
    if not math.isfinite(timestep) or timestep<=0:raise ValueError('Finite positive source timestep required')
    frame_index=int(frame.t);trial_index=int(frame.trial)
    if frame_index!=frame.t or trial_index!=frame.trial or frame_index<0 or trial_index<0:raise ValueError('Invalid source frame identity')
    common={'source_trial_index':trial_index,'source_frame_index':frame_index,'time_s':frame_index*timestep,'source_timestep_s':timestep,'source_mass_kg':float(mass_kg),'mass_available':bool(math.isfinite(mass_kg) and mass_kg>0),'canonical_mapping_status':'unassessed_source_only'}
    rows=[{**common,'source_pass_index':-1,'source_scope':'raw_frame','source_fields_json':payload(public_fields(frame,exclude=('processingPasses',)))}]
    for index,source_pass in enumerate(frame.processingPasses):
        rows.append({**common,'source_pass_index':index,'source_scope':'processing_pass','source_fields_json':payload(public_fields(source_pass))})
    return rows


def trial_metadata(subject,trial,dataset):
    original=subject.getTrialOriginalName(trial);task,task_id,task_info=get_task_info(dataset,original)
    step=float(subject.getTrialTimestep(trial));length=int(subject.getTrialLength(trial))
    if not math.isfinite(step) or step<=0 or length<0:raise ValueError('Invalid original trial clock/length')
    return {'source_trial_index':trial,'source_trial_name':subject.getTrialName(trial),'source_original_trial_name':original,'source_trial_split_index':subject.getTrialSplitIndex(trial),'source_frames':length,'source_timestep_s':step,'source_trial_processing_pass_count':subject.getTrialNumProcessingPasses(trial),'task':task,'task_id':task_id,'task_info':task_info,'task_assessment':'unresolved' if task is None else 'historical_mapping_unreviewed'}


def iter_trial_records(subject,trial,dataset,source_id,source_file,source_sha,batch_size=FRAME_BATCH,guard=None):
    if not 1<=batch_size<=FRAME_BATCH:raise ValueError('Frame batch exceeds bounded admission')
    meta=trial_metadata(subject,trial,dataset);mass=float(subject.getMassKg())
    for start in range(0,meta['source_frames'],batch_size):
        if guard:guard()
        count=min(batch_size,meta['source_frames']-start)
        frames=subject.readFrames(trial,start,count,includeSensorData=True,includeProcessingPasses=True)
        if len(frames)!=count:raise ValueError('Short source read; complete trial cannot be claimed')
        rows=[];payload_bytes=0
        for offset,frame in enumerate(frames):
            if guard:guard()
            if int(frame.t)!=start+offset or int(frame.trial)!=trial:raise ValueError('Source frame/trial identity differs')
            for row in extract_frame_data(frame,meta['source_timestep_s'],mass):
                row.update(source_file=source_file,source_sha256=source_sha,source_recording_id=source_id+':trial:'+str(trial),source_subject_id=source_id,source_trial_name=meta['source_trial_name'],source_original_trial_name=meta['source_original_trial_name'],source_trial_split_index=meta['source_trial_split_index'],task=None,task_id=meta['source_original_trial_name'],task_info=payload({'historical_task':meta['task'],'historical_task_id':meta['task_id'],'historical_mapping':encode_source(meta['task_info']),'assessment':meta['task_assessment']}),observation_type='continuous_recording')
                row['source_row_id']=row['source_recording_id']+f":frame:{row['source_frame_index']}:pass:{row['source_pass_index']}"
                payload_bytes+=len(row['source_fields_json'].encode())
                if payload_bytes>32*1024**2:raise MemoryError('Accumulated frame batch exceeds 32 MiB; preserve partial attempt')
                rows.append(row)
        yield rows


def process_b3d_file(b3d_path,dataset,subject_idx=0):
    """Small-review compatibility helper; full CLI uses bounded streaming instead."""
    path=Path(b3d_path);guard=make_guard(path.parent);guard(startup=True,force=True)
    import nimblephysics as nimble
    subject=nimble.biomechanics.SubjectOnDisk(str(path))
    if sum(subject.getTrialLength(i) for i in range(subject.getNumTrials()))>1024:raise MemoryError('Use streaming conversion; in-memory review limited to 1024 frames')
    sha=digest(path,guard);identity=f'{dataset}:{path.name}:{sha}';rows=[]
    for trial in range(subject.getNumTrials()):
        for batch in iter_trial_records(subject,trial,dataset,identity,path.name,sha,guard=guard):
            rows.extend(batch)
            if sum(len(r['source_fields_json']) for r in rows)>32*1024**2:raise MemoryError('Small review payload admission exceeded')
    return pd.DataFrame(rows)


def interpolate_stride(df,num_points=NUM_PHASE_POINTS):
    """Only explicitly reviewed external stride inputs; never auto-used on B3Ds."""
    if num_points!=150:raise ValueError('Inclusive phase exports require 150 samples')
    if len(df)<2 or 'time_s' not in df or 'source_recording_id' not in df:raise ValueError('Complete physical clock and source identity required')
    if df['source_recording_id'].nunique(dropna=False)!=1:raise ValueError('Cannot merge source recordings')
    time=df['time_s'].to_numpy(dtype=float)
    if not np.isfinite(time).all() or not (np.diff(time)>0).all():raise ValueError('Strict source clock required')
    grid=np.linspace(time[0],time[-1],150);phase=np.linspace(0,100,150)
    result={'phase_ipsi':phase,'time_s':grid,'phase_ipsi_dot':np.full(150,100/(time[-1]-time[0])),'phase_contra':np.full(150,np.nan)}
    for name in df:
        if name in result:continue
        if name in ('source_frame_index','frame_number'):continue
        if pd.api.types.is_numeric_dtype(df[name]) and name not in ('source_trial_index','source_trial_split_index'):
            result[name]=np.interp(grid,time,df[name].to_numpy(dtype=float))
        elif df[name].nunique(dropna=False)==1:result[name]=[df[name].iloc[0]]*150
        else:raise ValueError('Changing categorical source values cannot be interpolated: '+name)
    return pd.DataFrame(result)


def segment_to_strides(df,grf_col='grf_vertical_ipsi_N',time_col='time_s',*,reviewed_force_mapping=False):
    """No implicit phase export from unverified root-frame/contact-body signals."""
    if not reviewed_force_mapping:raise ValueError('Independent force frame/side/unit review required before segmentation')
    if df['source_recording_id'].nunique(dropna=False)!=1:raise ValueError('Cannot merge source trials')
    time=df[time_col].to_numpy(dtype=float);force=df[grf_col].to_numpy(dtype=float)
    if not np.isfinite(time).all() or not (np.diff(time)>0).all() or not np.isfinite(force).all():raise ValueError('Complete finite source clocks/forces required')
    strikes=np.flatnonzero((force[:-1]<=50)&(force[1:]>50))+1
    strides=[]
    for start,end in zip(strikes,strikes[1:]):
        stride=df.iloc[start:end+1].copy();identity=str(df['source_recording_id'].iloc[0])+f':frames:{start}-{end}'
        stride['observation_id']=identity;stride['step']=identity;strides.append(stride)
    return strides


def source_schema():
    import pyarrow as pa
    integers={'source_trial_index','source_frame_index','source_pass_index','source_trial_split_index'}
    floats={'time_s','source_timestep_s','source_mass_kg'}
    names=['source_trial_index','source_frame_index','time_s','source_timestep_s','source_mass_kg','mass_available','canonical_mapping_status','source_pass_index','source_scope','source_fields_json','source_file','source_sha256','source_recording_id','source_subject_id','source_trial_name','source_original_trial_name','source_trial_split_index','task','task_id','task_info','observation_type','source_row_id']
    return pa.schema([(n,pa.int64() if n in integers else pa.float64() if n in floats else pa.bool_() if n=='mass_available' else pa.string()) for n in names])


def process_dataset(dataset,input_dir,output_dir):
    """Fresh per-file source tables, embedded models, and full accounting ledger."""
    if dataset not in get_supported_datasets():raise ValueError('Unsupported dataset')
    input_dir=Path(input_dir).resolve();output_dir=Path(output_dir).resolve()
    guard=make_guard(output_dir);guard(startup=True,force=True)
    import nimblephysics as nimble
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    if output_dir.exists():raise FileExistsError('Fresh output directory required; preserve historical artifacts')
    files=sorted(input_dir.rglob('*.b3d'))
    if not files:raise ValueError('No source files')
    output_dir.mkdir(parents=True);schema=source_schema();ledger={'status':'running_source_preservation','scientific_approval':False,'dataset':dataset,'producer_sha256':digest(__file__),'task_config_sha256':digest(Path(__file__).with_name('dataset_configs.py')),'reader_version':str(getattr(nimble,'__version__','not_exposed')),'files':[{'source_file':str(p.relative_to(input_dir)),'status':'not_started'} for p in files],'canonical_dataset_complete':False,'loss_ledger':{'silently_dropped_frames':0,'silently_dropped_public_properties':0,'unsupported_source_properties':[],'unexported_header_methods':'Original B3D retained; only explicitly listed lightweight subject/trial metadata and embedded models exported. Header APIs requiring full arrays are not implicitly loaded.'},'phase_output':'Withheld: original model/DOF signs, contact body identity, force frames and events require independent validation.'}
    def save():
        temp=output_dir/'manifest.tmp';temp.write_text(json.dumps(ledger,indent=2,allow_nan=False)+'\n');temp.replace(output_dir/'manifest.json')
    save()
    try:
        for index,path in enumerate(files):
            guard(force=True)
            entry=ledger['files'][index];entry['status']='running';save();sha=digest(path,guard);subject=nimble.biomechanics.SubjectOnDisk(str(path));folder=output_dir/f'source_{index:04d}';folder.mkdir();entry.update(source_sha256=sha,trials=[])
            source_id=dataset+':'+entry['source_file']+':'+sha
            models=[]
            for p in range(subject.getNumProcessingPasses()):
                guard()
                xml=subject.getOpensimFileText(p)
                if len(xml.encode())>4*1024**2:raise MemoryError('Embedded model exceeds admission')
                model=folder/f'model_pass_{p}.osim';model.write_text(xml);models.append({'pass_index':p,'pass_type':str(subject.getProcessingPassType(p)),'model_path':str(model.relative_to(output_dir)),'sha256':digest(model)})
            metadata={'models':models,'time_reference':'Trial-local elapsed seconds = source Frame.t times original trial timestep; original session offset unavailable.','pass_identity':'source_pass_index is the local Frame.processingPasses slot; source type retained per row. No unsupported local-slot to global model inference.','source_mass':encode_source(subject.getMassKg()),'contact_bodies':encode_source(subject.getContactBodies()),'source_identity':'File identity only; no cross-file participant merge inferred','canonical_mapping':'Unassessed; all public frame/pass properties retained under source names'}
            metadata['subject_header']={}
            for name in ('getAgeYears','getBiologicalSex','getHeightM','getNotes','getSubjectTags','getQuality','getNumDofs','getNumJoints'):
                method=getattr(subject,name,None)
                metadata['subject_header'][name]=encode_source(method()) if method is not None else {'api_status':'unavailable_in_this_source_reader'}
            metadata_path=folder/'source_metadata.json'
            metadata_path.write_text(json.dumps(metadata,indent=2,allow_nan=False)+'\n')
            entry['metadata_sha256']=digest(metadata_path);entry['model_files']=models
            target=folder/'source_frames.parquet';row_count=0
            with pq.ParquetWriter(target,schema,compression='zstd') as writer:
                for trial in range(subject.getNumTrials()):
                    trial_info=trial_metadata(subject,trial,dataset);trial_info.update(frames_written=0,pass_rows_written=0,raw_rows_written=0,actual_frame_pass_count_histogram={},pass_count_assessment='pending',status='running');entry['trials'].append(trial_info);save()
                    for records in iter_trial_records(subject,trial,dataset,source_id,entry['source_file'],sha,guard=guard):
                        table=pa.Table.from_pylist(records,schema=schema)
                        if table.nbytes>128*1024**2:raise MemoryError('Frame batch admission exceeded')
                        guard();writer.write_table(table,row_group_size=512);row_count+=len(records)
                        frame_passes={}
                        for record in records:
                            frame=record['source_frame_index'];frame_passes.setdefault(frame,0)
                            if record['source_pass_index']>=0:frame_passes[frame]+=1
                        for count in frame_passes.values():
                            key=str(count);hist=trial_info['actual_frame_pass_count_histogram'];hist[key]=hist.get(key,0)+1
                        n=sum(r['source_pass_index']==-1 for r in records);trial_info['frames_written']+=n;trial_info['raw_rows_written']+=n;trial_info['pass_rows_written']+=len(records)-n
                    if trial_info['frames_written']!=trial_info['source_frames']:raise ValueError('Incomplete frame accounting')
                    histogram=trial_info['actual_frame_pass_count_histogram']
                    trial_info['pass_count_assessment']='matches_trial_header' if set(histogram)=={str(trial_info['source_trial_processing_pass_count'])} else 'frame_pass_count_differs_from_trial_header_unassessed'
                    trial_info['status']='all_source_frames_preserved_unreviewed';save()
            if digest(path,guard)!=sha:raise ValueError('Source changed during extraction')
            entry.update(status='source_preserved_unreviewed',rows=row_count,output=str(target.relative_to(output_dir)),output_sha256=digest(target,guard));save()
        guard(force=True);ledger['status']='all_source_files_preserved_unreviewed';save()
    except BaseException as error:
        ledger.update(status='stopped_incomplete',reason=str(error))
        if isinstance(error,TypeError):ledger['loss_ledger']['unsupported_source_properties'].append(str(error))
        save();raise
    return output_dir,None


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dataset',required=True,choices=get_supported_datasets());p.add_argument('--input',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    import resource
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
    os.nice(19)
    import subprocess
    subprocess.run(['ionice','-c','3','-p',str(os.getpid())],check=True)
    process_dataset(a.dataset,a.input,a.output_dir)

if __name__=='__main__':main()
