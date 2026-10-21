"""Independent persisted B3D readback. Coordinator-scheduled execution only.

No writer encoding or extraction functions are imported. Native source values are
compared recursively against JSON and Parquet, with complete file/trial/frame/pass
accounting. Success preserves source values; canonical anatomy remains unassessed.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import sys
import time
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[name]='1'

MAX_JSON=32*1024**2
HEADER_METHODS=('getAgeYears','getBiologicalSex','getHeightM','getNotes','getSubjectTags','getQuality','getNumDofs','getNumJoints')


def digest(path,guard=None):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024**2),b''):
            if guard:guard()
            h.update(block)
    return h.hexdigest()


def read_json(path):
    with Path(path).open('rb') as f:raw=f.read(MAX_JSON+1)
    if len(raw)>MAX_JSON:raise MemoryError('Metadata admission exceeded')
    return json.loads(raw)


class Guard:
    def __init__(self,output):
        path=Path(__file__).parents[1]/'Fukuchi_2018_Walking/run_ensemble_pilot.py'
        spec=importlib.util.spec_from_file_location('adb_readback_host_guard',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.check=module.check_resources;self.output=Path(output);self.last=0
    def __call__(self,startup=False,force=False):
        if not (startup or force) and time.monotonic()-self.last<15:return
        result=self.check(prelaunch=startup)
        if startup and result['linux_available_mib']<3584:raise MemoryError('WSL startup requires 3584 MiB')
        stat=os.statvfs(self.output)
        if stat.f_bavail*stat.f_frsize<5*1024**3:raise MemoryError('Preserve 5 GiB disk reserve')
        self.last=time.monotonic()


def compare_float(value,source):
    if type(value) not in (float,int) or isinstance(value,bool):raise ValueError('Numeric source type differs')
    if math.isnan(source):
        if not math.isnan(value):raise ValueError('NaN mask differs')
    elif struct.pack('d',float(value))!=struct.pack('d',float(source)):raise ValueError('Source value or signed-zero bits differ')


def compare_encoded(encoded,source):
    """Independent recursive source comparator, not a writer round trip."""
    import numpy as np
    if isinstance(source,np.ndarray):
        if not isinstance(encoded,dict) or set(encoded)!={'source_type','dtype','shape','values'} or encoded['source_type']!='ndarray':raise ValueError('Source array encoding differs')
        if encoded['dtype']!=source.dtype.str or encoded['shape']!=list(source.shape):raise ValueError('Original array dtype/shape differs')
        compare_encoded(encoded['values'],source.tolist());return
    if isinstance(source,np.generic):compare_encoded(encoded,source.item());return
    if isinstance(source,float):
        if not math.isfinite(source):
            token='NaN' if math.isnan(source) else '+Infinity' if source>0 else '-Infinity'
            if encoded!={'source_nonfinite':token}:raise ValueError('Source nonfinite mask/value differs')
        else:compare_float(encoded,source)
        return
    if source is None or isinstance(source,(str,bool,int)):
        if type(encoded)!=type(source) or encoded!=source:raise ValueError('Scalar source type/value differs')
        return
    if isinstance(source,(list,tuple)):
        if isinstance(source,tuple):
            if not isinstance(encoded,dict) or set(encoded)!={'source_type','values'} or encoded['source_type']!='tuple':raise ValueError('Tuple source type differs')
            values=encoded['values']
        else:values=encoded
        if not isinstance(values,list) or len(values)!=len(source):raise ValueError('Source sequence length differs')
        for a,b in zip(values,source):compare_encoded(a,b)
        return
    if isinstance(source,dict):
        if not isinstance(encoded,dict) or set(encoded)!={'source_type','items'} or encoded['source_type']!='mapping' or len(encoded['items'])!=len(source):raise ValueError('Source mapping differs')
        for pair,(key,value) in zip(encoded['items'],source.items()):
            if not isinstance(pair,list) or len(pair)!=2:raise ValueError('Mapping entry differs')
            compare_encoded(pair[0],key);compare_encoded(pair[1],value)
        return
    if hasattr(source,'name') and hasattr(source,'value'):
        if not isinstance(encoded,dict) or set(encoded)!={'source_type','class','name','value'} or encoded['source_type']!='enum' or encoded['class']!=type(source).__name__ or encoded['name']!=str(source.name):raise ValueError('Enum identity differs')
        compare_encoded(encoded['value'],source.value);return
    raise TypeError('Unsupported original property; cannot assert preserved: '+type(source).__name__)


def compare_fields(text,source,exclude=()):
    if len(text.encode())>4*1024**2:raise MemoryError('Frame payload admission exceeded')
    fields=json.loads(text);original={}
    for name in dir(source):
        if name.startswith('_') or name in exclude:continue
        value=getattr(source,name)
        if not callable(value):original[name]=value
    if set(fields)!=set(original):raise ValueError('Dropped or spurious source properties')
    for name,value in original.items():compare_encoded(fields[name],value)
    return len(original)


def expected_schema():
    import pyarrow as pa
    names=['source_trial_index','source_frame_index','time_s','source_timestep_s','source_mass_kg','mass_available','canonical_mapping_status','source_pass_index','source_scope','source_fields_json','source_file','source_sha256','source_recording_id','source_subject_id','source_trial_name','source_original_trial_name','source_trial_split_index','task','task_id','task_info','observation_type','source_row_id']
    integer={'source_trial_index','source_frame_index','source_pass_index','source_trial_split_index'};floating={'time_s','source_timestep_s','source_mass_kg'}
    return pa.schema([(n,pa.int64() if n in integer else pa.float64() if n in floating else pa.bool_() if n=='mass_available' else pa.string()) for n in names])


def rows_from_parquet(path,guard):
    import pyarrow.parquet as pq
    file=pq.ParquetFile(path)
    if not file.schema_arrow.equals(expected_schema(),check_metadata=True):raise ValueError('Persisted schema differs')
    for i in range(file.metadata.num_row_groups):
        if file.metadata.row_group(i).total_byte_size>128*1024**2:raise MemoryError('Row group exceeds admission')
    for batch in file.iter_batches(batch_size=32,use_threads=False):
        guard()
        if batch.nbytes>32*1024**2:raise MemoryError('Readback batch exceeds admission')
        yield from batch.to_pylist()


def safe_path(root,relative):
    path=(root/relative).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('Artifact escapes root')
    return path


def verify_record(record,frame,source_pass,pass_index,trial_info,context):
    trial,frame_index=int(frame.trial),int(frame.t);source_id=context['source_id'];recording=source_id+':trial:'+str(trial)
    expected={'source_trial_index':trial,'source_frame_index':frame_index,'source_pass_index':pass_index,'source_scope':'raw_frame' if pass_index==-1 else 'processing_pass','source_file':context['source_file'],'source_sha256':context['source_sha'],'source_recording_id':recording,'source_subject_id':source_id,'source_trial_name':trial_info['source_trial_name'],'source_original_trial_name':trial_info['source_original_trial_name'],'source_trial_split_index':trial_info['source_trial_split_index'],'task':None,'task_id':trial_info['source_original_trial_name'],'canonical_mapping_status':'unassessed_source_only','observation_type':'continuous_recording','source_row_id':recording+f':frame:{frame_index}:pass:{pass_index}','mass_available':bool(math.isfinite(context['mass']) and context['mass']>0)}
    for key,value in expected.items():
        if record[key]!=value:raise ValueError('Source record identity differs: '+key)
    compare_float(record['source_mass_kg'],context['mass']);compare_float(record['source_timestep_s'],trial_info['source_timestep_s']);compare_float(record['time_s'],frame_index*trial_info['source_timestep_s'])
    info=json.loads(record['task_info'])
    if set(info)!={'historical_mapping','assessment','historical_task','historical_task_id'} or info['assessment']!=trial_info['task_assessment'] or info['historical_task']!=trial_info['task'] or info['historical_task_id']!=trial_info['task_id']:raise ValueError('Task assessment differs')
    compare_encoded(info['historical_mapping'],trial_info['task_info'])
    return compare_fields(record['source_fields_json'],frame if pass_index==-1 else source_pass,('processingPasses',) if pass_index==-1 else ())


def verify_metadata(subject,entry,folder,root,guard):
    path=folder/'source_metadata.json'
    if digest(path)!=entry['metadata_sha256']:raise ValueError('Source metadata hash changed')
    meta=read_json(path)
    if set(meta)!={'models','time_reference','pass_identity','source_mass','contact_bodies','source_identity','canonical_mapping','subject_header'}:raise ValueError('Source metadata coverage differs')
    if meta['time_reference']!='Trial-local elapsed seconds = source Frame.t times original trial timestep; original session offset unavailable.' or meta['source_identity']!='File identity only; no cross-file participant merge inferred' or meta['canonical_mapping']!='Unassessed; all public frame/pass properties retained under source names':raise ValueError('Source metadata interpretation changed')
    if meta['pass_identity']!='source_pass_index is the local Frame.processingPasses slot; source type retained per row. No unsupported local-slot to global model inference.':raise ValueError('Pass-to-model interpretation changed')
    compare_encoded(meta['source_mass'],subject.getMassKg());compare_encoded(meta['contact_bodies'],subject.getContactBodies())
    if set(meta['subject_header'])!=set(HEADER_METHODS):raise ValueError('Subject metadata field coverage differs')
    for name in HEADER_METHODS:
        guard()
        method=getattr(subject,name,None)
        if method is None:
            if meta['subject_header'][name]!={'api_status':'unavailable_in_this_source_reader'}:raise ValueError('Unavailable source API changed')
        else:compare_encoded(meta['subject_header'][name],method())
    models=meta['models']
    if models!=entry['model_files'] or len(models)!=subject.getNumProcessingPasses():raise ValueError('Embedded model coverage differs')
    bindings={str(path):digest(path)}
    for index,model in enumerate(models):
        guard()
        if model['pass_index']!=index or model['pass_type']!=str(subject.getProcessingPassType(index)):raise ValueError('Global source pass identity differs')
        p=safe_path(root,model['model_path'])
        if p.stat().st_size>4*1024**2 or digest(p)!=model['sha256'] or p.read_text()!=subject.getOpensimFileText(index):raise ValueError('Embedded original model XML differs')
        bindings[str(p)]=digest(p)
    return bindings


def audit(input_root,output_root,guard=None):
    input_root=Path(input_root).resolve();root=Path(output_root).resolve();guard=guard or Guard(root);guard(startup=True,force=True)
    import nimblephysics as nimble
    import pyarrow as pa
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    manifest_path=root/'manifest.json';manifest_sha=digest(manifest_path,guard);manifest=read_json(manifest_path)
    if manifest.get('status')!='all_source_files_preserved_unreviewed' or manifest.get('scientific_approval') is not False or manifest.get('canonical_dataset_complete') is not False:raise ValueError('Complete source-preservation manifest required')
    loss=manifest.get('loss_ledger',{})
    if loss.get('silently_dropped_frames')!=0 or loss.get('silently_dropped_public_properties')!=0 or loss.get('unsupported_source_properties')!=[]:raise ValueError('Source loss ledger is incomplete')
    writer=Path(__file__).with_name('convert_addbiomechanics_to_parquet.py');config=Path(__file__).with_name('dataset_configs.py')
    if digest(writer)!=manifest['producer_sha256'] or digest(config)!=manifest['task_config_sha256']:raise ValueError('Producer or historical mapping source changed')
    files=sorted(input_root.rglob('*.b3d'))
    if not files:raise ValueError('No original B3D files; empty scope cannot establish source preservation')
    if [str(p.relative_to(input_root)) for p in files]!=[x['source_file'] for x in manifest['files']]:raise ValueError('Full original file inventory differs')
    bindings={str(manifest_path):manifest_sha,str(writer):digest(writer),str(config):digest(config),str(Path(__file__).resolve()):digest(__file__)};reports=[]
    for path,entry in zip(files,manifest['files']):
        guard(force=True);sha=digest(path,guard)
        if entry.get('status')!='source_preserved_unreviewed' or entry['source_sha256']!=sha:raise ValueError('Original source file status/hash differs')
        target=safe_path(root,entry['output']);output_sha=digest(target,guard)
        if output_sha!=entry['output_sha256']:raise ValueError('Persisted output changed')
        subject=nimble.biomechanics.SubjectOnDisk(str(path));bindings.update(verify_metadata(subject,entry,target.parent,root,guard));bindings[str(path)]=sha;bindings[str(target)]=output_sha
        if len(entry['trials'])!=subject.getNumTrials():raise ValueError('Full original trial coverage differs')
        records=iter(rows_from_parquet(target,guard));total_rows=total_frames=properties=0
        context={'source_id':manifest['dataset']+':'+entry['source_file']+':'+sha,'source_file':entry['source_file'],'source_sha':sha,'mass':float(subject.getMassKg())}
        for trial,info in enumerate(entry['trials']):
            if info.get('task_assessment') not in ('unresolved','historical_mapping_unreviewed'):raise ValueError('Historical task assessment cannot imply canonical approval')
            length=int(subject.getTrialLength(trial));dt=float(subject.getTrialTimestep(trial))
            expected={'source_trial_index':trial,'source_trial_name':subject.getTrialName(trial),'source_original_trial_name':subject.getTrialOriginalName(trial),'source_trial_split_index':subject.getTrialSplitIndex(trial),'source_frames':length,'source_trial_processing_pass_count':subject.getTrialNumProcessingPasses(trial)}
            if not math.isfinite(dt) or dt<=0:raise ValueError('Invalid original clock')
            for key,value in expected.items():
                if info[key]!=value:raise ValueError('Trial metadata differs: '+key)
            compare_float(info['source_timestep_s'],dt);pass_rows=0;hist={}
            for start in range(0,length,32):
                guard();count=min(32,length-start);frames=subject.readFrames(trial,start,count,includeSensorData=True,includeProcessingPasses=True)
                if len(frames)!=count:raise ValueError('Independent original read incomplete')
                for offset,frame in enumerate(frames):
                    guard()
                    if frame.trial!=trial or frame.t!=start+offset:raise ValueError('Original API frame identity inconsistent')
                    passes=list(frame.processingPasses);key=str(len(passes));hist[key]=hist.get(key,0)+1;pass_rows+=len(passes);total_frames+=1
                    for index,source_pass in [(-1,None),*enumerate(passes)]:
                        guard()
                        try:record=next(records)
                        except StopIteration:raise ValueError('Dropped frame or processing pass in persisted output') from None
                        properties+=verify_record(record,frame,source_pass,index,info,context);total_rows+=1
            assessment='matches_trial_header' if set(hist)=={str(subject.getTrialNumProcessingPasses(trial))} else 'frame_pass_count_differs_from_trial_header_unassessed'
            if info['frames_written']!=length or info['raw_rows_written']!=length or info['pass_rows_written']!=pass_rows or info['actual_frame_pass_count_histogram']!=hist or info['pass_count_assessment']!=assessment or info['status']!='all_source_frames_preserved_unreviewed':raise ValueError('Trial completeness disposition differs')
        if next(records,None) is not None or total_rows!=entry['rows']:raise ValueError('Spurious records or manifest row total differs')
        if digest(path,guard)!=sha or digest(target,guard)!=output_sha:raise ValueError('Source/output changed during readback')
        reports.append({'source_file':entry['source_file'],'source_frames':total_frames,'rows':total_rows,'source_properties_checked':properties,'source_sha256':sha,'output_sha256':output_sha})
    for path,h in bindings.items():
        if digest(path,guard)!=h:raise ValueError('Bound evidence changed during audit')
    return {'status':'all_original_B3D_frames_passes_and_properties_source_checked_unreviewed','scientific_approval':False,'canonical_dataset_complete':False,'manifest_sha256':manifest_sha,'bindings':bindings,'files':reports,'limitations':['Original properties and values preserved, not anatomical model/sign approval.','Historical task labels checked for persisted consistency; experiment/task meaning requires independent dataset review.','Frame pass count differences from trial header retained and unassessed.','Source NaN masks preserved; original NaN payload bits remain in B3D.','Unexported array-valued header APIs remain in original B3D and writer loss ledger; not claimed independently exported.']}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    if a.report.exists():raise FileExistsError('Preserve prior source audit')
    import resource,subprocess
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(19);subprocess.run(['ionice','-c','3','-p',str(os.getpid())],check=True)
    result=audit(a.input,a.output_root)
    with a.report.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)

if __name__=='__main__':main()
