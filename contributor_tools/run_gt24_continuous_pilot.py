"""Prepare guarded two-phase continuous-export replay/readback; never auto-run."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.run_gt24_ankle_converter_pilot import digest,verify,guarded
from contributor_tools.prepare_gt24_continuous_correction import TIME,README_SHA


def manual_derivative(values,times):
    """Independent three-point finite difference with first-order endpoints."""
    result=[(values[1]-values[0])/(times[1]-times[0])]
    for i in range(1,len(values)-1):
        left=times[i]-times[i-1];right=times[i+1]-times[i]
        result.append(-right/(left*(left+right))*values[i-1]+(right-left)/(left*right)*values[i]+left/(right*(left+right))*values[i+1])
    result.append((values[-1]-values[-2])/(times[-1]-times[-2]));return result


def worker(planpath,index,stage):
    for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[name]='1'
    os.environ['MPLBACKEND']='Agg';os.environ['LOCOHUB_HEADLESS']='1';resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    plan=json.loads(planpath.read_text());verify(plan['bindings']);record=plan['records'][index];out=planpath.parent/f'record_{index}';out.mkdir(exist_ok=True)
    if stage in ('reference','corrected'):
        adapter=Path(plan[stage+'_adapter']);sys.path.insert(0,str(adapter.parent));spec=importlib.util.spec_from_file_location('continuous_pilot_adapter',adapter);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        original=pd.read_csv
        def bounded(path,*args,**kwargs):
            if str(Path(path).resolve()) not in record['source_bindings']:raise ValueError('Unbound source read')
            frame=original(path,*args,nrows=20001,**kwargs)
            if len(frame)>20000:raise ValueError('Continuous source row admission exceeded')
            return frame
        pd.read_csv=bounded
        frame=module.process_trial_time(Path(record['folder']),record['subject'],record['phase'],'all')
        if frame.empty or len(frame)>20000:raise ValueError('Missing/oversized continuous output')
        frame.to_parquet(out/(stage+'.parquet'),index=False,row_group_size=512);verify(plan['bindings']);return
    from contributor_tools.common.data_contract import inspect_contract
    old=pq.read_table(out/'reference.parquet').to_pandas(use_threads=False);new=pq.read_table(out/'corrected.parquet').to_pandas(use_threads=False)
    if len(new)>20000 or len(new)!=len(old):raise ValueError('Continuous output coverage differs')
    source={}
    for kind in ('angle_filt','moment_filt','moment_filt_bio','velocity','grf','insole_sim','exo'):
        path=Path(record['folder'])/f"{record['subject']}_{record['condition']}_{kind}.csv"
        if path.exists():source[kind]=pd.read_csv(path,nrows=20001)
    clock=source['angle_filt'].time.to_numpy();n=len(clock)
    if n!=len(new) or any(len(frame)!=n for frame in source.values()):raise ValueError('Source rows differ')
    for table in source.values():np.testing.assert_allclose(table.time,clock,rtol=0,atol=1e-9)
    np.testing.assert_array_equal(new.source_time_s,clock);np.testing.assert_array_equal(new.time_s,clock-clock[0])
    if not np.isfinite(clock).all() or not (np.diff(clock)>0).all():raise ValueError('Source clock invalid')
    recording=f"gt24:{record['phase']}/{record['subject']}/{record['condition']}";side=new.reference_side.iloc[0]
    identity=recording+':continuous:'+side
    for col,value in [('source_recording_id',recording),('observation_id',identity),('step',identity),('observation_type','continuous_recording'),('reference_side',side)]:
        if not new[col].eq(value).all():raise ValueError('Continuous identity differs')
    if side not in ('left','right') or not new.source_start_time_s.eq(clock[0]).all() or not new.source_end_time_s.eq(clock[-1]).all():raise ValueError('Reference side/source boundaries invalid')
    info=json.loads(new.task_info.iloc[0]);mass=json.loads(new.subject_metadata.iloc[0])['weight_kg']
    if not new.task_info.eq(new.task_info.iloc[0]).all() or not new.subject_metadata.eq(new.subject_metadata.iloc[0]).all() or info['ankle_convention_readme_sha256']!=README_SHA:raise ValueError('Structured provenance metadata differs')
    phase=pq.ParquetFile(record['phase_pilot_output']);phase_metadata=json.loads(next(phase.iter_batches(batch_size=1,use_threads=False)).to_pandas().subject_metadata.iloc[0])
    if json.loads(new.subject_metadata.iloc[0])!=phase_metadata:raise ValueError('Source mass/day/model basis differs from source-checked phase pilot')
    finite={};missing={}
    def check(column,expected):
        expected=np.asarray(expected,dtype=float);actual=new[column].to_numpy()
        np.testing.assert_allclose(actual,expected,rtol=1e-8,atol=1e-7,equal_nan=True)
        if not np.array_equal(np.isnan(actual),np.isnan(expected)):raise ValueError('Source missingness differs: '+column)
        finite[column]=int(np.isfinite(actual).sum());missing[column]=int(np.isnan(actual).sum())
    def raw(table,column):
        if table not in source or column not in source[table]:return np.full(n,np.nan)
        return source[table][column].to_numpy()
    for role,leg in [('ipsi','l' if side=='left' else 'r'),('contra','r' if side=='left' else 'l')]:
        for native,canonical,sign in [('hip_flexion','hip_flexion',1),('knee_angle','knee_flexion',-1),('ankle_angle','ankle_dorsiflexion',-1)]:
            angle=sign*raw('angle_filt',native+'_'+leg)*np.pi/180
            velocity=sign*raw('velocity',native+'_'+leg+'_velocity')*np.pi/180
            if np.isnan(velocity).all():velocity=np.asarray(manual_derivative(angle,clock))
            check(f'{canonical}_angle_{role}_rad',angle);check(f'{canonical}_velocity_{role}_rad_s',velocity)
            check(f'{canonical}_acceleration_{role}_rad_s2',manual_derivative(velocity,clock))
            check(f'{canonical}_moment_{role}_Nm_kg',sign*raw('moment_filt',native+'_'+leg+'_moment'))
            check(f'{canonical}_biological_moment_{role}_Nm_kg',sign*raw('moment_filt_bio',native+'_'+leg+'_moment'))
            assistance=np.zeros(n) if info['exo_state']=='no_exo' else (np.full(n,np.nan) if native=='ankle_angle' else -raw('exo',native.replace('_flexion','_angle')+'_'+leg+'_torque_interaction')/mass)
            check(f'{canonical}_assistance_moment_{role}_Nm_kg',assistance)
        for kind,table,suffix,unit,scale in [('angle','angle_filt','','rad',np.pi/180),('velocity','velocity','_velocity','rad_s',np.pi/180),('moment','moment_filt','_moment','Nm_kg',1.),('biological_moment','moment_filt_bio','_moment','Nm_kg',1.)]:
            check(f'source_ankle_coordinate_{kind}_{role}_{unit}',raw(table,'ankle_angle_'+leg+suffix)*scale)
        for axis in ('x','y','z'):check(f'source_grf_global_{axis}_{role}_N',raw('grf',f'fp_{leg}_force_{axis}'))
        check(f'grf_vertical_{role}_BW',raw('grf',f'fp_{leg}_force_y')/(mass*9.81))
        for feature in ('grf_anterior','grf_lateral'):check(f'{feature}_{role}_BW',np.full(n,np.nan))
        check(f'cop_vertical_{role}_m',np.full(n,np.nan))
        check(f'cop_anterior_{role}_m',raw('insole_sim',f'insole_{leg}_cop_x'));check(f'cop_lateral_{role}_m',raw('insole_sim',f'insole_{leg}_cop_z'))
    allowed={'subject_metadata','task_info','step','time_s','sampling_rate_hz'}
    for col in old:
        if col in allowed or 'ankle_dorsiflexion_' in col or '_velocity_' in col or '_acceleration_' in col or '_assistance_moment_' in col or col.startswith(('grf_anterior_','grf_lateral_','cop_vertical_')):continue
        pd.testing.assert_series_equal(old[col],new[col],check_exact=True)
    contract=inspect_contract(new,mode='time')
    if not contract.schema_passed:raise ValueError('Continuous contract failed: '+str(contract.issues))
    verify(plan['bindings'])
    result={'status':'continuous_source_checked_unreviewed','scientific_approval':False,'rows':n,'observation_id':identity,'finite_source_values':finite,'missing_source_values_unassessed':missing,'unchanged_unaffected_fields_exact':True,'reference_sha256':digest(out/'reference.parquet'),'corrected_sha256':digest(out/'corrected.parquet'),'limitations':['Full-source clocks retained, source roles explicit; anatomical posture not independently measured','Horizontal anatomical GRF and unavailable COP/actuator fields remain unassessed','Continuous reference export was structurally legacy and is not approved by preserving unaffected columns']}
    (out/'readback.json').write_text(json.dumps(result,indent=2)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__);base=ROOT/'converted_datasets/reconversion_v2'
    p.add_argument('--output-root',type=Path,required=True);p.add_argument('--proposal',type=Path,default=base/'gt24_continuous_correction_proposal_20261021');p.add_argument('--run',action='store_true');p.add_argument('--worker',choices=['reference','corrected','audit']);p.add_argument('--record-index',type=int);a=p.parse_args();out=a.output_root.resolve();planpath=out/'plan.json'
    if a.worker:worker(planpath,a.record_index,a.worker);return
    if not out.is_relative_to(base):raise ValueError('Isolated output required')
    phaseplan=base/'gt24_ankle_converter_pilot_v2_20261021/plan.json';phase_summary=phaseplan.parent/'pilot_summary.json';summary=json.loads(phase_summary.read_text())
    if summary['status']!='two_phase_ankle_converter_pilot_checked_unreviewed' or summary['plan_sha256']!=digest(phaseplan):raise ValueError('Successful phase pilot required')
    phase=json.loads(phaseplan.read_text());manifestpath=a.proposal/'preparation_manifest.json';proposal=json.loads(manifestpath.read_text());records=phase['records'];bindings=dict(phase['bindings'])
    for i,record in enumerate(records):
        path=phaseplan.parent/f'record_{i}/corrected.parquet';record['phase_pilot_output']=str(path);bindings[str(path)]=summary['records'][i]['corrected_sha256']
    for name,sha in proposal['snapshot_code'].items():bindings[str((a.proposal/'isolated_repo'/name).resolve())]=sha
    for path in [phaseplan,phase_summary,manifestpath,Path(__file__),ROOT/'contributor_tools/prepare_gt24_continuous_correction.py']:bindings[str(path.resolve())]=digest(path)
    verify(bindings);plan={'status':'prepared_not_executed','scientific_approval':False,'bindings':bindings,'records':records,'reference_adapter':str(ROOT/TIME),'corrected_adapter':str((a.proposal/'isolated_repo'/TIME).resolve()),'worker_memory_mib':768,'stage_order':['reference','corrected','audit']}
    if out.exists():
        if not planpath.is_file() or list(out.iterdir())!=[planpath] or json.loads(planpath.read_text())!=plan:raise FileExistsError('Existing attempt preserved')
    else:out.mkdir(parents=True);planpath.write_text(json.dumps(plan,indent=2)+'\n')
    if not a.run:print(json.dumps({'status':'prepared_not_executed','plan':str(planpath)}));return
    reports=[]
    for index in range(len(records)):
        for stage in plan['stage_order']:
            verify(bindings)
            with (out/f'{index}_{stage}.log').open('x') as log:guarded([sys.executable,str(Path(__file__).resolve()),'--output-root',str(out),'--worker',stage,'--record-index',str(index)],out,log)
        reports.append(json.loads((out/f'record_{index}/readback.json').read_text()))
    verify(bindings);report={'status':'two_phase_continuous_source_pilot_checked_unreviewed','scientific_approval':False,'plan_sha256':digest(planpath),'records':reports}
    (out/'pilot_summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status']}))


if __name__=='__main__':main()
