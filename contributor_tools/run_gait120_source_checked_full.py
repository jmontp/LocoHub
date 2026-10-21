"""Full Gait120 successor: unchanged frozen producer plus independent source readback.

Default prepares metadata only. --run is coordinator-only serial scientific work.
No inverse dynamics or anatomical plate mapping is enabled.
"""
import argparse
import csv
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'converted_datasets/reconversion_v2';sys.path.insert(0,str(ROOT))
from contributor_tools.preserve_mblue_planar_estimates import digest
from contributor_tools.run_gt24_ankle_converter_pilot import verify
ORIGINAL=ROOT/'contributor_tools/run_gait120_batch.py'
INVENTORY=BASE/'gait120_full_batch_20261020/source_inventory.json'
PILOT=BASE/'gait120_force_pilot_20261020/source_comparison.json'

REVIEW_TASKS={'LevelWalking':'level_walking','StairAscent':'stair_ascent','StairDescent':'stair_descent','SlopeAscent':'incline_walking','SlopeDescent':'decline_walking','SitToStand':'sit_to_stand','StandToSit':'stand_to_sit'}


def load_original():
 s=importlib.util.spec_from_file_location('g120_frozen_batch',ORIGINAL);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def scope(inventory):
    from collections import Counter
    paths=inventory['recordings']
    if len(paths)!=6882 or len(set(paths))!=6882 or len(inventory['subjects'])!=120 or inventory['unsupported_source_paths']:raise ValueError('Full source inventory differs')
    for value in paths:
        p=Path(value)
        if p.is_absolute() or '..' in p.parts or len(p.parts)!=5 or p.parts[1]!='JointAngle' or p.suffix.lower()!='.mot':raise ValueError('Unsafe source recording')
    tasks=dict(Counter(Path(p).parts[2] for p in paths))
    if set(tasks)!={'LevelWalking','SitToStand','StandToSit','StairAscent','StairDescent','SlopeAscent','SlopeDescent'}:raise ValueError('Seven-task coverage differs')
    if {Path(p).parts[0] for p in paths}!=set(inventory['subjects']):raise ValueError('Participant scope differs')
    return {'records':6882,'subjects':120,'tasks':tasks,'expected_rows':6882*150}


def prepare(output):
    output=Path(output).resolve()
    if not output.is_relative_to(BASE) or output.exists():raise ValueError('Fresh output root required')
    queue=BASE/'metadata_serial_queue_20261021/plan.json';job=json.loads(queue.read_text())['jobs'][4]
    if job['name']!='gait120':raise ValueError('Wrong original job')
    code=job['code_sha256'];verify(code)
    inventory=json.loads(INVENTORY.read_text());counts=scope(inventory);pilot=json.loads(PILOT.read_text())
    if pilot['recordings_checked']!=14 or pilot['rows_checked']!=2100 or len(pilot['results'])!=14:raise ValueError('Actual seven-task two-subject pilot missing')
    historical_deltas=[]
    for path,h in pilot['code_sha256'].items():
        if str(ROOT/path) in code and code[str(ROOT/path)]!=h:
            if (path,h,code[str(ROOT/path)])!=('contributor_tools/common/stride_segmentation.py','e01434a54aaee082e27455098101b0662e4812b176c05b82aa123664fa984b9b','eecf12b9ff0e643a07de4c6053ba1cf6c3d15eb37c88d6e77905933abb4cfce6'):raise ValueError('Actual pilot producer differs')
            historical_deltas.append({'path':path,'pilot_sha256':h,'current_sha256':code[str(ROOT/path)],'scope':'Not called by presegmented process_step_file; no new stride segmentation or enabled OpenSim pipeline.'})
    bindings={**code,str(INVENTORY):digest(INVENTORY),str(PILOT):digest(PILOT),str(Path(__file__).resolve()):digest(__file__)}
    for result in pilot['results']:
        p=PILOT.parent/result['output'];bindings[str(p)]=result['output_sha256']
    bindings.update(pilot['source_sha256'])
    for name in ['gait120_source_pilot_20261020/anthropometry_comparison.json','gait120_full_batch_20261020/worker_smoke_check.json','gait120_publisher_code_review_20261021/review.json']:
        p=BASE/name;bindings[str(p)]=digest(p)
    guard=ROOT/'contributor_tools/conversion_scripts/Fukuchi_2018_Walking/run_ensemble_pilot.py';bindings[str(guard)]=digest(guard)
    for name in ('preserve_mblue_planar_estimates.py','run_gt24_ankle_converter_pilot.py'):
        dependency=ROOT/'contributor_tools'/name;bindings[str(dependency)]=digest(dependency)
    verify(bindings)
    source_root='/mnt/s/locomotion_data/Gait120'
    plan={'status':'prepared_full_scope_not_run','scientific_approval':False,'source_root':source_root,'output_root':str(output),'inventory':str(INVENTORY),'scope':counts,'producer_code':code,'bindings':bindings,'worker_limit_mib':1024,'worker_timeout_seconds':120,'historical_pilot_code_deltas':historical_deltas,'scope_limitations':['Source preservation checks do not establish full anatomical correctness.','Canonical force/COP and joint moments remain unavailable; plate-frame source aliases retained.','No locally generated OpenSim model/ID replaces publisher precomputed angles.','Protocol dimensions metadata proposal is not applied by this unchanged producer.','Velocity/acceleration/segment fields are unchanged producer outputs, not independently validated by this raw angle and plate-channel checker.','Per-record anthropometric metadata is source-bound but not independently recalculated from spreadsheet by this checker.','Producer does not emit time_s; native start/end time, inclusive phase and phase rate are independently checked instead.'],'resume_policy':'Only receipts with exact source/code/output hashes and independent source readback are reusable; partial directories are preserved and block resume.'}
    output.mkdir(parents=True,exist_ok=False);(output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');(output/'code_hashes.json').write_text(json.dumps(code,indent=2)+'\n');(output/'source_inventory.json').write_text(json.dumps(inventory,indent=2)+'\n');return plan


def mot_columns(path,names):
    """Separate bounded parser, independent of producer load_mot_file."""
    path=Path(path)
    if path.stat().st_size>64*1024**2:raise MemoryError('Source MOT exceeds64MiB')
    with path.open() as f:
        for line in f:
            if line.strip().lower()=='endheader':break
        else:raise ValueError('MOT header absent')
        header=next((s.split() for s in f if s.strip()),None)
        if not header or len(header)!=len(set(header)):raise ValueError('Invalid MOT columns')
        selected={n:header.index(n) for n in names if n in header};result={n:[] for n in selected}
        for line in f:
            if not line.strip():continue
            values=line.split()
            if len(values)!=len(header):raise ValueError('Incomplete MOT row')
            for name,index in selected.items():
                value=float(values[index])
                if math.isinf(value):raise ValueError('Infinite source measurement: '+name)
                result[name].append(value)
    if 'time' not in result or len(result['time'])<2 or any(not math.isfinite(t) for t in result['time']) or any(b<=a for a,b in zip(result['time'],result['time'][1:])):raise ValueError('Source clock invalid')
    return result


def independent_readback(plan,relative):
    import numpy as np
    import pyarrow.parquet as pq
    folder=Path(plan['output_root'])/'recordings'/Path(relative).with_suffix('');target=folder/'phase.parquet';mp=folder/'conversion_manifest.json';manifest=json.loads(mp.read_text())
    if manifest.get('status')!='converted_unreviewed' or manifest.get('scientific_approval') is not False or manifest['code']!=plan['producer_code'] or manifest['output_sha256']!=digest(target):raise ValueError('Producer receipt incomplete')
    verify(manifest['sources']);verify(manifest['code']);table=pq.ParquetFile(target).read(use_threads=False)
    if table.num_rows!=150:raise ValueError('Wrong phase row count')
    fields={n:table[n].to_pylist() for n in table.column_names};source=Path(plan['source_root'])/relative
    if str(source.resolve()) not in manifest['sources']:raise ValueError('Exact source absent from manifest')
    raw=mot_columns(source,['time']+[f'{j}_{l}' for l in ('r','l') for j in ('hip_flexion','knee_angle','ankle_angle')]);clock=raw['time'];target_clock=np.linspace(clock[0],clock[-1],150)
    feature_counts={}
    required=[f'{j}_r' for j in ('hip_flexion','knee_angle','ankle_angle')]
    if not set(required)<=set(raw):raise ValueError('Required right source angle headers absent')
    contra_complete=all(f'{j}_l' in raw for j in ('hip_flexion','knee_angle','ankle_angle'))
    def close(name,expected):
        if name not in fields:raise ValueError('Expected field absent: '+name)
        actual=np.array(fields[name],dtype=float);expected=np.asarray(expected,dtype=float)
        if actual.shape!=expected.shape or not np.array_equal(np.isnan(actual),np.isnan(expected)) or not np.allclose(actual,expected,rtol=1e-10,atol=1e-10,equal_nan=True):raise ValueError('Independent source value mismatch: '+name)
        finite=int(np.isfinite(expected).sum());feature_counts[name]={'finite_values_checked':finite,'missing_values_unassessed':int(np.isnan(expected).sum()),'assessment':'source_values_checked' if finite else 'unavailable_all_missing_not_passed'}
    for role,leg in [('ipsi','r'),('contra','l')]:
        for source_name,canonical,sign in [('hip_flexion','hip_flexion',1),('knee_angle','knee_flexion',-1),('ankle_angle','ankle_dorsiflexion',1)]:
            key=f'{source_name}_{leg}';expected=np.interp(target_clock,clock,raw[key])*sign*math.pi/180 if key in raw and (role=='ipsi' or contra_complete) else np.full(150,np.nan)
            close(f'{canonical}_angle_{role}_rad',expected)
    plate_names=['time']+[f'ground_force{p}_{kind}{a}' for p in (1,2) for kind in ('v','p') for a in 'xyz']+[f'ground_torque{p}_{a}' for p in (1,2) for a in 'xyz']
    force_sources=[Path(p) for p in manifest['sources'] if '/MotionCapture/' in p and '/MOT/' in p and p.endswith('.mot')]
    if len(force_sources)>1:raise ValueError('Ambiguous source force table')
    source_aliases=set()
    if force_sources:
        forces=mot_columns(force_sources[0],plate_names)
        for plate in (1,2):
            for axis in 'xyz':
                for key,name in [(f'ground_force{plate}_v{axis}',f'source_plate{plate}_force_{axis}_N'),(f'ground_force{plate}_p{axis}',f'source_plate{plate}_cop_{axis}_m'),(f'ground_torque{plate}_{axis}',f'source_plate{plate}_torque_{axis}_Nm')]:
                    if key in forces:source_aliases.add(name);close(name,np.interp(target_clock,forces['time'],forces[key],left=np.nan,right=np.nan))
    if {n for n in fields if n.startswith('source_plate')}!=source_aliases:raise ValueError('Unexpected source plate fields')
    for name,values in fields.items():
        if name.startswith(('grf_','cop_')) or '_moment_' in name:
            if any(v is not None and not math.isnan(v) for v in values):raise ValueError('Unsupported anatomical force/COP/ID output: '+name)
            feature_counts[name]={'finite_values_checked':0,'missing_values_unassessed':150,'assessment':'withheld_anatomy_or_ID_not_passed'}
    subject,_,task,_,_=Path(relative).parts;canonical=REVIEW_TASKS[task];identity=f'gait120:G120_{subject}/'+Path(*Path(relative).parts[1:]).as_posix();transfer=task in ('SitToStand','StandToSit')
    for name,value in {'subject':'G120_'+subject,'task':canonical,'task_id':task,'source_recording_id':identity,'observation_id':identity+':right','reference_side':'right','observation_type':'transfer' if transfer else 'individual_cycle','source_start_sample':0,'source_end_sample':len(clock)-1,'source_start_time_s':clock[0],'source_end_time_s':clock[-1]}.items():
        if fields[name]!=[value]*150:raise ValueError('Source identity mismatch: '+name)
    close('phase_ipsi',np.linspace(0,100,150))
    close('phase_ipsi_dot',np.full(150,100/(clock[-1]-clock[0])))
    if 'time_s' in fields:raise ValueError('Frozen producer does not emit time_s; unexpected clock requires explicit review')
    for raw_info in fields['task_info']:
        info=json.loads(raw_info)
        if info.get('source_force_axes')!='original_MOT_axes' or info.get('exo_state')!='no_exo' or info.get('phase_boundary_method')!=('source_pelvis_shoulder_transfer_boundaries' if transfer else 'source_right_heel_strike_boundaries'):raise ValueError('Source policy metadata changed')
    verify(manifest['sources']);verify(manifest['code'])
    return {'status':'gait120_raw_angles_and_plate_aliases_source_checked_unreviewed','scientific_approval':False,'rows':150,'relative':relative,'source_sha256':manifest['sources'],'producer_code':manifest['code'],'manifest_sha256':digest(mp),'output_sha256':digest(target),'reviewer_sha256':digest(__file__),'feature_counts':feature_counts,'scientific_assessment':'partial_source_preservation_not_full_signal_or_metadata_validation','missing_source_angle_columns':[name for name in [f'{j}_{l}' for l in ('r','l') for j in ('hip_flexion','knee_angle','ankle_angle')] if name not in raw],'anthropometry_assessment':'unassessed_per_record; spreadsheet bytes bound but not independently interpreted in this checker','physical_clock_assessment':'source endpoints and phase rate checked; producer has no time_s output','limitations':plan['scope_limitations']}


def completed(plan,relative):
    folder=Path(plan['output_root'])/'recordings'/Path(relative).with_suffix('');rp=folder/'source_readback.json'
    if not folder.exists():return None
    if not rp.exists():raise ValueError('Partial record preserved; explicit recovery required')
    r=json.loads(rp.read_text())
    if r.get('status')!='gait120_raw_angles_and_plate_aliases_source_checked_unreviewed' or r.get('relative')!=relative or r.get('rows')!=150 or r.get('reviewer_sha256')!=digest(__file__) or r.get('producer_code')!=plan['producer_code']:raise ValueError('Resume receipt differs')
    verify(r['source_sha256']);verify(r['producer_code'])
    if digest(folder/'phase.parquet')!=r['output_sha256'] or digest(folder/'conversion_manifest.json')!=r['manifest_sha256']:raise ValueError('Resume artifact changed')
    return {'relative':relative,'output_sha256':r['output_sha256'],'readback_sha256':digest(rp)}


def worker(planpath,index):
    import resource
    resource.setrlimit(resource.RLIMIT_AS,(1024*1024**2,1024*1024**2))
    plan=json.loads(planpath.read_text());sha=digest(planpath);verify(plan['bindings']);inventory=json.loads(Path(plan['inventory']).read_text());relative=inventory['recordings'][index]
    if completed(plan,relative):return
    original=load_original();args=argparse.Namespace(worker=relative,source_root=Path(plan['source_root']),output_root=Path(plan['output_root']))
    original.worker(args);report=independent_readback(plan,relative);verify(plan['bindings'])
    if digest(planpath)!=sha:raise ValueError('Plan changed')
    folder=Path(plan['output_root'])/'recordings'/Path(relative).with_suffix('')
    with (folder/'source_readback.json').open('x') as f:json.dump(report,f,indent=2)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-root',type=Path,required=True);p.add_argument('--run',action='store_true');p.add_argument('--resume',action='store_true');p.add_argument('--worker-index',type=int);a=p.parse_args();out=a.output_root.resolve();planpath=out/'plan.json'
    if not out.is_relative_to(BASE):raise ValueError('Unauthorized output root')
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[key]='1'
    if a.worker_index is not None:worker(planpath,a.worker_index);return
    if not a.run:print(json.dumps(prepare(out)['scope']));return
    plan=json.loads(planpath.read_text());sha=digest(planpath);verify(plan['bindings']);inventory=json.loads(Path(plan['inventory']).read_text());scope(inventory)
    if plan['output_root']!=str(out):raise ValueError('Output root changed')
    summary_path=out/'summary.json';previous={}
    if summary_path.exists():
        if not a.resume:raise FileExistsError('Explicit resume required')
        summary=json.loads(summary_path.read_text())
        if summary['plan_sha256']!=sha:raise ValueError('Resume plan differs')
        previous={r['relative']:r for r in summary['records']}
    elif a.resume:raise ValueError('No prior summary to resume')
    guard=load_guard();records=[];state={'status':'running_full_source_readback','scientific_approval':False,'pid':os.getpid(),'plan_sha256':sha,'full_scope':plan['scope'],'records':records}
    def save():
        p=out/'summary.tmp';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(summary_path)
    try:
        for index,relative in enumerate(inventory['recordings']):
            if (out/'STOP').exists() or (out/'STOP_AFTER_CURRENT').exists():raise RuntimeError('Coordinator stop')
            prior=completed(plan,relative)
            if prior:
                if previous.get(relative)!=prior:raise ValueError('Resume receipt not bound to prior summary')
                records.append(prior);continue
            if relative in previous:raise ValueError('Previous completed record disappeared')
            available=guard.check_resources(prelaunch=True)
            cap_aware_admission(available)
            state['current_record']=relative;save()
            command=['prlimit','--as=1073741824','nice','-n','19','ionice','-c','3',sys.executable,str(Path(__file__).resolve()),'--output-root',str(out),'--worker-index',str(index)]
            # Existing guard owns this sole child group and enforces120s stages.
            stage={'recording':relative};guard.guarded_stage(command,out/f'worker_{index:04d}.log',stage)
            receipt=completed(plan,relative)
            if receipt is None:raise ValueError('Source readback missing')
            records.append(receipt);save()
        state['status']='all6882_gait120_records_source_checked_unreviewed';state.pop('current_record',None)
        verify(plan['bindings'])
        if digest(planpath)!=sha:raise ValueError('Plan changed')
    except BaseException as exc:state.update(status='stopped_incomplete',reason=str(exc));raise
    finally:save()


def cap_aware_admission(resources):
    if resources['windows_available_mib']<3072 or resources['linux_available_mib']<3584:
        raise MemoryError('1GiB Gait120 worker needs Windows3072MiB and Linux3584MiB startup reserves')


def load_guard():
    path=ROOT/'contributor_tools/conversion_scripts/Fukuchi_2018_Walking/run_ensemble_pilot.py';s=importlib.util.spec_from_file_location('g120_full_guard',path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
if __name__=='__main__':main()
