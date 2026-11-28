"""Prepare/run isolated sequential GT24 ankle correction and persisted readback.

Two complete short recordings preserve trial-wide IMU initialization. Numerical
stages are separate 768 MiB processes, monitored only in their own process groups.
Default prepares a plan; --run requires the coordinator's exclusive worker slot.
"""
import argparse
import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.prepare_gt24_ankle_fix import ADAPTER,README_SHA256
from contributor_tools.preserve_mblue_planar_estimates import headroom,windows_available_mib
from contributor_tools.run_gt25_coverage_pilot import linux_available_mib
KINDS=('angle_filt','moment_filt','grf','velocity','insole_sim','moment_filt_bio','power','power_bio','exo','exo_sim','imu_sim')
META={'ankle_source_positive_direction','ankle_canonical_transform','ankle_convention_evidence','ankle_convention_readme_sha256','ankle_source_alias_method'}
FIELDS={f'ankle_dorsiflexion_{kind}_{side}_{unit}':f'source_ankle_coordinate_{alias}_{side}_{unit}' for side in ('ipsi','contra') for kind,alias,unit in [('angle','angle','rad'),('velocity','derived_velocity','rad_s'),('acceleration','derived_acceleration','rad_s2'),('moment','moment','Nm_kg'),('biological_moment','biological_moment','Nm_kg')]}


def digest(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024**2),b''):value.update(block)
    return value.hexdigest()


def admission_estimate(size):
    estimate=size*30+64*1024**2
    if size<0 or size>24*1024**2 or estimate>768*1024**2:raise MemoryError("Complete short-recording admission exceeds explicit 768 MiB budget")
    return estimate


def verify(bindings):
    for name,sha in bindings.items():
        if digest(name)!=sha:raise ValueError('Bound evidence changed: '+name)


def guarded(command,out,log):
    if windows_available_mib()<2816 or linux_available_mib()<3584:raise MemoryError('Worker startup reserve insufficient')
    headroom(out);process=subprocess.Popen(['nice','-n','19','ionice','-c','3',*command],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    start=time.monotonic();last=0.
    try:
        while process.poll() is None:
            now=time.monotonic()
            if now-start>180:raise TimeoutError('Numerical stage exceeded 180 seconds')
            if linux_available_mib()<2048:raise MemoryError('WSL reserve below 2 GiB')
            if now-last>=15:
                headroom(out)
                if windows_available_mib()<2048:raise MemoryError('Host reserve below 2 GiB')
                last=now
            time.sleep(.5)
        if process.returncode:raise RuntimeError('Numerical stage failed; inspect stage log')
    finally:
        if process.poll() is None:
            os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()


def worker(planpath,index,stage):
    for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[name]='1'
    os.environ['MPLBACKEND']='Agg';os.environ['LOCOHUB_HEADLESS']='1'
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    plan=json.loads(planpath.read_text());verify(plan['bindings']);record=plan['records'][index];out=planpath.parent/f'record_{index}';out.mkdir(exist_ok=True)
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    if stage in ('reference','corrected'):
        path=Path(plan['reference_adapter'] if stage=='reference' else plan['corrected_adapter'])
        sys.path.insert(0,str(path.parent));spec=importlib.util.spec_from_file_location('pilot_adapter',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        read_csv=pd.read_csv
        def bounded_csv(path,*args,**kwargs):
            if str(Path(path).resolve()) not in record['source_bindings']:raise ValueError('Converter requested unbound source')
            if kwargs.get('nrows') is not None:raise ValueError('Unexpected converter row override')
            data=read_csv(path,*args,nrows=20001,**kwargs)
            if len(data)>20000:raise ValueError('Short-recording 20000-row admission exceeded')
            return data
        pd.read_csv=bounded_csv
        frames=module.process_trial(Path(record['folder']),record['subject'],record['phase'],'all')
        if not frames:raise ValueError('No accepted observations')
        # Full-recording execution is required for unchanged global IMU offsets.
        frame=pd.concat(frames,ignore_index=True);del frames
        if len(frame)>150*300:raise ValueError('Short-recording 300-observation admission exceeded')
        frame.to_parquet(out/(stage+'.parquet'),index=False,row_group_size=150)
        verify(plan['bindings']);return
    from scipy.interpolate import interp1d
    from contributor_tools.common.data_contract import inspect_contract
    before=pq.ParquetFile(out/'reference.parquet');after=pq.ParquetFile(out/'corrected.parquet')
    if before.metadata.num_rows!=after.metadata.num_rows:raise ValueError('Observation count changed')
    source={}
    for kind in ('angle_filt','moment_filt','moment_filt_bio'):
        path=Path(record['folder'])/f"{record['subject']}_{record['condition']}_{kind}.csv"
        if path.exists():
            frame=pd.read_csv(path,nrows=20001)
            if len(frame)>20000:raise ValueError('Readback admission exceeded')
            source[kind]=frame
    historical=pq.ParquetFile(record['historical_phase']) if record.get('historical_phase') else None
    if historical and historical.metadata.num_rows!=before.metadata.num_rows:raise ValueError('Historical baseline scope differs')
    old_batches=historical.iter_batches(batch_size=150,use_threads=False) if historical else None
    count=0;identities=set();finite={k:0 for k in FIELDS};missing={k:0 for k in FIELDS}
    for a,b in itertools.zip_longest(before.iter_batches(batch_size=150,use_threads=False),after.iter_batches(batch_size=150,use_threads=False)):
        if a is None or b is None or a.num_rows!=150 or b.num_rows!=150:raise ValueError('Incomplete persisted cycle')
        old,new=a.to_pandas(use_threads=False),b.to_pandas(use_threads=False)
        if historical:
            hb=next(old_batches,None)
            if hb is None:raise ValueError('Historical baseline missing cycle')
            pd.testing.assert_frame_equal(hb.to_pandas(use_threads=False),old,check_exact=True)
        if set(new.columns)!=set(old.columns)|set(FIELDS.values()):raise ValueError('Unexpected output fields')
        if old.observation_id.nunique()!=1 or old.observation_id.iloc[0] in identities:raise ValueError('Repeated source identity')
        identities.add(old.observation_id.iloc[0])
        for col in old:
            if not a.schema.field(col).equals(b.schema.field(col),check_metadata=True):raise ValueError('Persisted original field schema changed')
            if not a.column(a.schema.get_field_index(col)).is_null().equals(b.column(b.schema.get_field_index(col)).is_null()):raise ValueError('Persisted original null mask changed')
            if col in FIELDS:
                np.testing.assert_allclose(new[col],-old[col],rtol=0,atol=0,equal_nan=True)
                pd.testing.assert_series_equal(new[FIELDS[col]],old[col],check_names=False,check_exact=True)
                if not a.column(a.schema.get_field_index(col)).is_null().equals(b.column(b.schema.get_field_index(FIELDS[col])).is_null()):raise ValueError('Source alias persisted null mask changed')
                finite[col]+=int(np.isfinite(new[col]).sum());missing[col]+=int(new[col].isna().sum())
            elif col=='task_info':
                for left,right in zip(old[col],new[col]):
                    info=json.loads(right)
                    if {k:v for k,v in info.items() if k not in META}!=json.loads(left) or not META<=set(info) or info['ankle_convention_readme_sha256']!=README_SHA256:raise ValueError('Unrelated task metadata changed')
            else:pd.testing.assert_series_equal(old[col],new[col],check_exact=True)
        start=int(old.source_start_sample.iloc[0]);end=int(old.source_end_sample.iloc[0]);times=source['angle_filt'].time.iloc[start:end+1].to_numpy()
        if len(times)!=end-start+1 or not np.isfinite(times).all() or not (np.diff(times)>0).all():raise ValueError('Invalid source clock')
        target=np.linspace(times[0],times[-1],150)
        for role,side in [('ipsi','l' if old.reference_side.iloc[0]=='left' else 'r'),('contra','r' if old.reference_side.iloc[0]=='left' else 'l')]:
            for kind,table,suffix,scale in [('angle','angle_filt','',np.pi/180),('moment','moment_filt','_moment',1.),('biological_moment','moment_filt_bio','_moment',1.)]:
                if table not in source:expected=np.full(150,np.nan)
                else:
                    tabledata=source[table];np.testing.assert_allclose(tabledata.time.iloc[start:end+1],times,rtol=0,atol=1e-9)
                    raw=tabledata[f'ankle_angle_{side}{suffix}'].iloc[start:end+1].to_numpy()*scale
                    expected=interp1d(times,-raw,bounds_error=True)(target)
                unit='rad' if kind=='angle' else 'Nm_kg';np.testing.assert_allclose(new[f'ankle_dorsiflexion_{kind}_{role}_{unit}'],expected,rtol=1e-10,atol=1e-10,equal_nan=True)
        if not inspect_contract(new,mode='phase').schema_passed:raise ValueError('Corrected observation structural failure')
        count+=1
    if historical and next(old_batches,None) is not None:raise ValueError('Unconsumed historical baseline cycle')
    verify(plan['bindings'])
    report={'status':'persisted_ankle_correction_checked_unreviewed','scientific_approval':False,'observations':count,'finite_values':finite,'missing_values_unassessed':missing,'exact_unrelated_values_and_metadata':True,'source_aliases_exact_with_null_masks':True,'historical_baseline_exact':bool(historical),'reference_sha256':digest(out/'reference.parquet'),'corrected_sha256':digest(out/'corrected.parquet'),'limitations':['Reference replay uses complete trial initialization; segmentation unchanged by proposal','Phase1And2 uses a newly executed frozen-original reference, not a pre-existing historical export','True anatomical posture is not independently measured by this test']}
    (out/'readback.json').write_text(json.dumps(report,indent=2)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__);base=ROOT/'converted_datasets/reconversion_v2'
    p.add_argument('--output-root',type=Path,required=True);p.add_argument('--proposal',type=Path,default=base/'swarm_backlog_20261021/gt24_ankle_negation_proposal')
    p.add_argument('--run',action='store_true');p.add_argument('--worker',choices=['reference','corrected','audit']);p.add_argument('--record-index',type=int);a=p.parse_args()
    out=a.output_root.resolve();planpath=out/'plan.json'
    if a.worker:worker(planpath,a.record_index,a.worker);return
    if not out.is_relative_to(base):raise ValueError('Isolated output root required')
    proposal=json.loads((a.proposal/'preparation_manifest.json').read_text());native=base/'gt24_native_parsed_ankle_pilot_20261021/source_comparison.json';native_report=json.loads(native.read_text())
    if native_report['status']!='bounded_native_parsed_ankle_correspondence_checked_unreviewed' or len(native_report['records'])!=2:raise ValueError('Successful two-phase native pilot required')
    bindings={str(a.proposal/'preparation_manifest.json'):digest(a.proposal/'preparation_manifest.json'),str(native):digest(native),str(Path(__file__).resolve()):digest(__file__)}
    native_plan=native.parent/'plan.json'
    if digest(native_plan)!=native_report['plan_sha256']:raise ValueError('Native pilot plan binding differs')
    bindings[str(native_plan)]=digest(native_plan)
    for evidence in [a.proposal/'source_readme.txt',Path('/mnt/s/locomotion_data/GaTech_2024_TaskAgnostic/readme.txt')]:
        if digest(evidence)!=README_SHA256:raise ValueError('Released README evidence changed')
        bindings[str(evidence.resolve())]=README_SHA256
    bindings.update(proposal['original_code'])
    for name,sha in proposal['snapshot_code'].items():bindings[str((a.proposal/'isolated_repo'/name).resolve())]=sha
    for name in ['prepare_gt24_ankle_fix.py','preserve_mblue_planar_estimates.py','run_gt25_coverage_pilot.py']:
        path=ROOT/'contributor_tools'/name;bindings[str(path)]=digest(path)
    records=[];source_root=Path('/mnt/s/locomotion_data/GaTech_2024_TaskAgnostic')
    for phase,subject,condition in [('Phase1And2','BT01','normal_walk_1_0-6_on'),('Phase3','BT20','normal_walk_1_1_0-6_on')]:
        folder=source_root/(phase+'_Parsed')/'Parsed'/subject/condition
        paths=[folder/f'{subject}_{condition}_{kind}.csv' for kind in KINDS];paths=[x for x in paths if x.exists()]
        size=sum(x.stat().st_size for x in paths);estimate=admission_estimate(size)
        source_bindings={str(x):digest(x) for x in paths};bindings.update(source_bindings)
        record={'phase':phase,'subject':subject,'condition':condition,'folder':str(folder),'source_bytes':size,'admission_estimate_bytes':estimate,'source_bindings':source_bindings}
        if phase=='Phase3':
            hist=base/'gt24_phase3_timing_20261020/gt24/Phase3'/subject/condition/'conversion_manifest.json';h=json.loads(hist.read_text())
            if h['status']!='converted_unreviewed':raise ValueError('Historical baseline not complete')
            bindings[str(hist)]=digest(hist)
            for entry in h['outputs']:bindings[str(hist.parent/entry['name'])]=entry['sha256']
            for entry in h['sources']:
                if digest(entry['path'])!=entry['sha256']:raise ValueError('Historical source differs')
            record['historical_phase']=str(hist.parent/'phase.parquet')
        records.append(record)
    verify(bindings)
    plan={'status':'prepared_not_executed','scientific_approval':False,'bindings':bindings,'records':records,'reference_adapter':str(ROOT/ADAPTER),'corrected_adapter':str((a.proposal/'isolated_repo'/ADAPTER).resolve()),'stage_order':['reference','corrected','audit'],'worker_address_space_mib':768,'windows_startup_mib':2816,'windows_runtime_mib':2048,'linux_startup_mib':3584,'maximum_csv_rows':20000,'maximum_observations':300}
    if out.exists():
        if not planpath.is_file() or list(out.iterdir())!=[planpath] or json.loads(planpath.read_text())!=plan:raise FileExistsError('Preserve existing pilot attempt')
    else:out.mkdir(parents=True);planpath.write_text(json.dumps(plan,indent=2)+'\n')
    if not a.run:print(json.dumps({'plan':str(planpath),'records':len(records)}));return
    reports=[]
    for index,record in enumerate(records):
        for stage in plan['stage_order']:
            verify(bindings)
            with (out/f'{index}_{stage}.log').open('x') as log:guarded([sys.executable,str(Path(__file__).resolve()),'--output-root',str(out),'--worker',stage,'--record-index',str(index)],out,log)
        reports.append(json.loads((out/f'record_{index}/readback.json').read_text()))
    verify(bindings)
    result={'status':'two_phase_ankle_converter_pilot_checked_unreviewed','scientific_approval':False,'plan_sha256':digest(planpath),'records':reports}
    (out/'pilot_summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status']}))


if __name__=='__main__':main()
