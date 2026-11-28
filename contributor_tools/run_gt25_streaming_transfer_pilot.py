"""Plan-only by default; explicitly run one isolated projected GT25 transfer.

Never calls the full-table worker or mutates the active source/converter snapshot.
"""
import argparse
import csv
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from contributor_tools import gt25_projected_row_store as spool
from contributor_tools import gt25_streaming_transfers as segmentation
from contributor_tools.preserve_mblue_planar_estimates import headroom,windows_available_mib

FAMILY=Path('contributor_tools/conversion_scripts/GaTech_2025_DomainAdaptation')
KINDS=('angle_filt','moment_filt','grf','velocity','insole_sim','moment_filt_bio','power','power_bio','exo','exo_sim','imu_sim')
REQUIRED=set(KINDS[:5])


def load_converter(path):
    spec=importlib.util.spec_from_file_location('isolated_gt25_transfer_converter',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def convert_windows(stores, boundaries, converter, subject, recording, *, guard=lambda:None):
    import pandas as pd
    task,_,info=converter.map_task_name(recording)
    if task not in ('sit_to_stand','stand_to_sit'):raise ValueError('Transfer-only pilot')
    model=converter.get_model_variant(recording) or 'unknown';mass=converter.get_subject_mass(subject)
    imu=stores.get('imu_sim');dt=1/converter.SAMPLING_RATE
    if imu:
        # Full source interval mean, never per-window/chunk clock initialization.
        dt=(imu.window(imu.rows-1,imu.rows-1)[0][0]-imu.window(0,0)[0][0])/(imu.rows-1)
    for number,bound in enumerate(boundaries):
        guard();start,end=bound['start_idx'],bound['end_idx']
        windows=spool.aligned_windows(stores,start,end)
        frames={kind:pd.DataFrame(rows,columns=stores[kind].columns) for kind,rows in windows.items()}
        imu_frame=frames.pop('imu_sim',None)
        result=converter.process_stride(data=frames,start_idx=0,end_idx=end-start,subject_id=subject,subject_mass=mass,
            task=bound['segment_type'],task_id=bound['segment_type'],task_info=info,step_num=number,leg_side='l',
            model_variant=model,imu_df=imu_frame,imu_dt=dt,use_accel_init=True,
            source_recording_id=f'gt25:Parsed/{subject}/{recording}')
        if result is None:raise ValueError('Accepted source transfer produced no output')
        result['source_start_sample']=start;result['source_end_sample']=end
        result['observation_id']=f'gt25:Parsed/{subject}/{recording}:samples:{start}:{end}:left'
        result['step']=result['observation_id']
        yield result


def prepare(prepared,source_root,subject,recording,out):
    for component in (subject,recording):
        if Path(component).name!=component or component in ('.','..'):raise ValueError('Invalid source component')
    if not recording.startswith('sit_to_stand_'):raise ValueError('Only source sit_to_stand recordings admitted')
    prepared=Path(prepared).resolve();source_root=Path(source_root).resolve();out=Path(out).resolve()
    if not out.is_relative_to(ROOT/'converted_datasets/reconversion_v2'):raise ValueError('Isolated staging output required')
    manifest_path=prepared/'preparation_manifest.json';manifest=json.loads(manifest_path.read_text());snapshot=prepared/'isolated_repo'
    bindings={str(manifest_path):spool.digest(manifest_path)}
    for name,sha in manifest['snapshot_code'].items():
        path=(snapshot/name).resolve()
        if not path.is_relative_to(snapshot) or spool.digest(path)!=sha:raise ValueError('Snapshot binding mismatch')
        bindings[str(path)]=sha
    for path in [Path(__file__).resolve(),Path(spool.__file__).resolve(),Path(segmentation.__file__).resolve(),ROOT/'contributor_tools/preserve_mblue_planar_estimates.py',*sorted((ROOT/'contributor_tools/common').rglob('*.py'))]:bindings[str(path)]=spool.digest(path)
    readme=source_root.parent/'readme.txt'
    if spool.digest(readme)!=manifest['readme']['sha256']:raise ValueError('Reviewed source README changed')
    bindings[str(readme)]=spool.digest(readme)
    inputs=[];trial=source_root/subject/recording
    for kind in KINDS:
        path=trial/f'{subject}_{recording}_{kind}.csv'
        if not path.exists():
            if kind in REQUIRED:raise ValueError('Missing required source '+kind)
            continue
        with path.open('rb') as stream:line=stream.readline(spool.MAX_LINE_BYTES+1)
        if len(line)>spool.MAX_LINE_BYTES:raise ValueError('Header admission exceeded')
        header=next(csv.reader([line.decode('utf-8-sig')]))
        columns=spool.projection(kind,transfer=True)
        if not set(columns)<=set(header) or len(header)!=len(set(header)):raise ValueError('Missing/duplicate projected source columns: '+kind)
        st=path.stat();inputs.append({'kind':kind,'path':str(path),'bytes':st.st_size,'mtime_ns':st.st_mtime_ns,'columns':columns})
    return {'status':'prepared_not_executed','scientific_approval':False,'subject':subject,'recording':recording,
        'snapshot':str(snapshot),'bindings':bindings,'sources':inputs,'output':str(out),'limits':{'address_space_mib':768,'windows_startup_mib':2816,'windows_runtime_mib':2048,'chunk_rows':4096,'window_rows':4096},
        'source_sha256_status':'Acquired during bounded serial projection; original files rehashed before success.',
        'scientific_limits':['Projection/segmentation equivalence is not anatomical convention approval.','Whole-trial IMU mean dt uses endpoint telescoping; bounded floating tolerance required against prior numpy mean(diff).']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared',type=Path,required=True);parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--subject',required=True);parser.add_argument('--recording',required=True)
    parser.add_argument('--output-root',type=Path,required=True);parser.add_argument('--run',action='store_true')
    args=parser.parse_args();plan=prepare(args.prepared,args.source_root,args.subject,args.recording,args.output_root)
    out=Path(plan['output']);planpath=out/'plan.json'
    if out.exists():
        if not planpath.is_file() or list(out.iterdir())!=[planpath] or json.loads(planpath.read_text())!=plan:raise FileExistsError('Preserve existing attempt')
    else:out.mkdir(parents=True);planpath.write_text(json.dumps(plan,indent=2)+'\n')
    if not args.run:print(json.dumps({'status':plan['status'],'plan':str(planpath)}));return
    for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[name]='1'
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
    started=time.monotonic();last=0.
    def guard():
        nonlocal last
        if (out/'STOP_AFTER_CURRENT').exists():raise RuntimeError('Requested stop')
        if time.monotonic()-started>3600:raise TimeoutError('One-hour pilot limit')
        if time.monotonic()-last>=15:
            headroom(out)
            if windows_available_mib()<2048:raise MemoryError('Windows runtime reserve below2GiB')
            last=time.monotonic()
    headroom(out)
    if windows_available_mib()<2816:raise MemoryError('Windows startup reserve insufficient')
    import pyarrow as pa
    import pyarrow.parquet as pq
    from contributor_tools.common.data_contract import assess_observations
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    summary={'status':'running','scientific_approval':False,'plan_sha256':spool.digest(planpath),'observations':0,'sources':[]}
    def save():
        p=out/'conversion_summary.tmp';p.write_text(json.dumps(summary,indent=2)+'\n');p.replace(out/'conversion_summary.json')
    save();writer=None
    try:
        stores={}
        for source in plan['sources']:
            guard();path=Path(source['path']);st=path.stat()
            if (st.st_size,st.st_mtime_ns)!=(source['bytes'],source['mtime_ns']):raise ValueError('Prepared source changed')
            meta=spool.build(path,out/'projected'/source['kind'],source['columns'],guard=guard)
            summary['sources'].append(meta);stores[source['kind']]=spool.Store(out/'projected'/source['kind']);save()
        converter=load_converter(Path(plan['snapshot'])/FAMILY/'convert_gtech_2025_da_to_parquet.py')
        config=converter.SitStandConfig(grf_vertical_ipsi_col='grf_vertical_ipsi_N',grf_vertical_contra_col='grf_vertical_contra_N',velocity_cols=('hip_flexion_velocity_ipsi_rad_s','hip_flexion_velocity_contra_rad_s','knee_flexion_velocity_ipsi_rad_s','knee_flexion_velocity_contra_rad_s'),sitting_grf_threshold_N=400.,standing_grf_threshold_N=600.,velocity_threshold_rad_s=.436,use_iqr_filtering=True,iqr_multiplier=1.5)
        events=segmentation.segment(stores,out/'segmentation.sqlite',config,guard=guard)
        with (out/'observation_assessments.jsonl').open('x') as assessments:
            for frame in convert_windows(stores,segmentation.accepted(events),converter,args.subject,args.recording,guard=guard):
                report=assess_observations(frame,None)
                if not report['schema_passed']:raise ValueError('Observation schema failed')
                table=pa.Table.from_pandas(frame,preserve_index=False)
                if writer is None:writer=pq.ParquetWriter(out/'phase.parquet.partial',table.schema)
                writer.write_table(table,row_group_size=150);assessments.write(json.dumps(report,allow_nan=False)+'\n')
                summary['observations']+=1;save()
        if writer:writer.close();writer=None
        if not summary['observations']:raise ValueError('No accepted source transfers')
        for source in summary['sources']:
            guard()
            if spool.digest(source['source_path'])!=source['source_sha256']:raise ValueError('Source changed after projection')
        for path,sha in plan['bindings'].items():
            if spool.digest(path)!=sha:raise ValueError('Bound implementation changed')
        if spool.digest(planpath)!=summary['plan_sha256']:raise ValueError('Plan changed')
        (out/'phase.parquet.partial').rename(out/'phase.parquet')
        summary.update(status='streaming_transfer_converted_unreviewed',rows=150*summary['observations'],phase_sha256=spool.digest(out/'phase.parquet'),segmentation_sha256=spool.digest(events),peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except Exception as error:summary.update(status='failed_incomplete',reason=str(error));raise
    finally:
        if writer:writer.close()
        save()
    print(json.dumps(summary))


if __name__=='__main__':main()
