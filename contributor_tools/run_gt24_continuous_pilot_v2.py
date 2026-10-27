"""Memory-bounded recovery of the failed GT24 continuous pilot; no cap increase.

Preserves executed v1 evidence. Explicitly hash-bound record0 exports may be
reused, but neither record is accepted until the new 512-row audit passes.
"""
import argparse
import itertools
import json
import os
from pathlib import Path
import resource
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.run_gt24_continuous_pilot import worker as convert_worker,manual_derivative
from contributor_tools.run_gt24_ankle_converter_pilot import digest,verify,guarded
from contributor_tools.prepare_gt24_continuous_correction import README_SHA
from contributor_tools.preserve_um21_planar_estimates import exact_value


def allowed_changes():
    changed={'subject_metadata','task_info','step','time_s','sampling_rate_hz'}
    for role in ('ipsi','contra'):
        for kind,unit in [('angle','rad'),('velocity','rad_s'),('acceleration','rad_s2'),('moment','Nm_kg'),('biological_moment','Nm_kg')]:changed.add(f'ankle_dorsiflexion_{kind}_{role}_{unit}')
        for joint in ('hip_flexion','knee_flexion'):
            for kind,unit in [('velocity','rad_s'),('acceleration','rad_s2')]:changed.add(f'{joint}_{kind}_{role}_{unit}')
        for joint in ('hip_flexion','knee_flexion','ankle_dorsiflexion'):changed.add(f'{joint}_assistance_moment_{role}_Nm_kg')
        for axis in ('anterior','lateral'):changed.add(f'grf_{axis}_{role}_BW')
        changed.add(f'cop_vertical_{role}_m')
    return changed


def added_fields():
    added={'source_recording_id','observation_id','observation_type','reference_side','source_start_time_s','source_end_time_s','source_time_s'}
    for role in ('ipsi','contra'):
        for axis in ('x','y','z'):added.add(f'source_grf_global_{axis}_{role}_N')
        for kind,unit in [('angle','rad'),('velocity','rad_s'),('moment','Nm_kg'),('biological_moment','Nm_kg')]:added.add(f'source_ankle_coordinate_{kind}_{role}_{unit}')
    return added


def check_unmodified(before,after):
    if set(after.schema.names)!=set(before.schema.names)|added_fields():raise ValueError('Unexpected continuous output field set')
    for name in before.schema.names:
        if name in allowed_changes():continue
        a=before.column(before.schema.get_field_index(name));b=after.column(after.schema.get_field_index(name))
        if not before.schema.field(name).equals(after.schema.field(name),check_metadata=True) or not a.is_null().equals(b.is_null()) or not exact_value(a.to_pylist(),b.to_pylist()):raise ValueError('Unmodified persisted field changed: '+name)


def source_columns():
    columns={name:{'time'} for name in ('angle_filt','velocity','moment_filt','moment_filt_bio','grf','insole_sim','exo')}
    for leg in ('l','r'):
        for joint in ('hip_flexion','knee_angle','ankle_angle'):
            columns['angle_filt'].add(joint+'_'+leg);columns['velocity'].add(joint+'_'+leg+'_velocity')
            for table in ('moment_filt','moment_filt_bio'):columns[table].add(joint+'_'+leg+'_moment')
        for axis in ('x','y','z'):columns['grf'].add(f'fp_{leg}_force_{axis}')
        for axis in ('x','z'):columns['insole_sim'].add(f'insole_{leg}_cop_{axis}')
        for joint in ('hip','knee'):columns['exo'].add(f'{joint}_angle_{leg}_torque_interaction')
    return columns


def audit(planpath,index):
    for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[name]='1'
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    from contributor_tools.common.data_contract import inspect_contract
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    plan=json.loads(planpath.read_text());verify(plan['bindings']);record=plan['records'][index];out=planpath.parent/f'record_{index}'
    before=pq.ParquetFile(out/'reference.parquet');after=pq.ParquetFile(out/'corrected.parquet')
    n=after.metadata.num_rows
    if not 2<=n<=20000 or before.metadata.num_rows!=n:raise ValueError('Continuous row admission/count differs')
    source={}
    for kind,columns in source_columns().items():
        path=Path(record['folder'])/f"{record['subject']}_{record['condition']}_{kind}.csv"
        if path.exists():
            table=pd.read_csv(path,usecols=lambda name:name in columns,nrows=20001)
            if len(table)!=n or 'time' not in table:raise ValueError('Source row/clock mismatch')
            source[kind]={name:table[name].to_numpy() for name in table.columns}
    clock=source['angle_filt']['time']
    if not np.isfinite(clock).all() or not (np.diff(clock)>0).all():raise ValueError('Invalid source clock')
    for table in source.values():np.testing.assert_allclose(table['time'],clock,rtol=0,atol=1e-9)
    phase=pq.ParquetFile(record['phase_pilot_output']);phase_metadata=json.loads(next(phase.iter_batches(batch_size=1,use_threads=False)).column(phase.schema_arrow.get_field_index('subject_metadata')).to_pylist()[0])
    finite={};missing={};start=0;identity=None;metadata_text=None;segment_fields=set()
    def raw(table,column,lo,hi):
        values=source.get(table,{}).get(column)
        return np.full(hi-lo,np.nan) if values is None else values[lo:hi]
    for old_batch,new_batch in itertools.zip_longest(before.iter_batches(batch_size=512,use_threads=False),after.iter_batches(batch_size=512,use_threads=False)):
        if old_batch is None or new_batch is None or old_batch.num_rows!=new_batch.num_rows:raise ValueError('Incomplete readback coverage')
        check_unmodified(old_batch,new_batch)
        segment_fields.update(name for name in old_batch.schema.names if name.startswith(('thigh_','shank_','foot_')) and any(token in name for token in ('_angle_','_velocity_','_acceleration_')))
        frame=new_batch.to_pandas(use_threads=False);stop=start+len(frame)
        np.testing.assert_array_equal(frame.source_time_s,clock[start:stop]);np.testing.assert_array_equal(frame.time_s,clock[start:stop]-clock[0])
        side=frame.reference_side.iloc[0]
        if side not in ('left','right'):raise ValueError('Unknown physical reference side')
        recording=f"gt24:{record['phase']}/{record['subject']}/{record['condition']}";expected_id=recording+':continuous:'+side
        if identity is not None and identity!=expected_id:raise ValueError('Continuous role changed')
        identity=expected_id
        for col,value in [('source_recording_id',recording),('observation_id',identity),('step',identity),('observation_type','continuous_recording'),('reference_side',side),('source_start_time_s',clock[0]),('source_end_time_s',clock[-1])]:
            if not frame[col].eq(value).all():raise ValueError('Source identity/bounds differ: '+col)
        if not frame.task_info.eq(frame.task_info.iloc[0]).all() or (metadata_text is not None and metadata_text!=frame.task_info.iloc[0]):raise ValueError('Recording task provenance changed')
        metadata_text=frame.task_info.iloc[0];info=json.loads(metadata_text)
        if info['ankle_convention_readme_sha256']!=README_SHA or not frame.subject_metadata.map(lambda x:json.loads(x)==phase_metadata).all():raise ValueError('README/mass provenance differs')
        mass=phase_metadata['weight_kg']
        def check(column,expected):
            expected=np.asarray(expected,dtype=float);actual=frame[column].to_numpy()
            np.testing.assert_allclose(actual,expected,rtol=1e-8,atol=1e-7,equal_nan=True)
            if not np.array_equal(np.isnan(actual),np.isnan(expected)):raise ValueError('Source missingness differs: '+column)
            finite[column]=finite.get(column,0)+int(np.isfinite(actual).sum());missing[column]=missing.get(column,0)+int(np.isnan(actual).sum())
        lo=max(0,start-2);hi=min(n,stop+2);window=slice(start-lo,stop-lo)
        for role,leg in [('ipsi','l' if side=='left' else 'r'),('contra','r' if side=='left' else 'l')]:
            for native,canonical,sign in [('hip_flexion','hip_flexion',1),('knee_angle','knee_flexion',-1),('ankle_angle','ankle_dorsiflexion',-1)]:
                angle=sign*raw('angle_filt',native+'_'+leg,lo,hi)*np.pi/180;native_velocity=source.get('velocity',{}).get(native+'_'+leg+'_velocity')
                fallback=native_velocity is None or np.isnan(native_velocity).all()
                velocity=np.asarray(manual_derivative(angle,clock[lo:hi])) if fallback else sign*native_velocity[lo:hi]*np.pi/180
                check(f'{canonical}_angle_{role}_rad',angle[window]);check(f'{canonical}_velocity_{role}_rad_s',velocity[window]);check(f'{canonical}_acceleration_{role}_rad_s2',np.asarray(manual_derivative(velocity,clock[lo:hi]))[window])
                check(f'{canonical}_moment_{role}_Nm_kg',sign*raw('moment_filt',native+'_'+leg+'_moment',start,stop));check(f'{canonical}_biological_moment_{role}_Nm_kg',sign*raw('moment_filt_bio',native+'_'+leg+'_moment',start,stop))
                assistance=np.zeros(stop-start) if info['exo_state']=='no_exo' else np.full(stop-start,np.nan) if native=='ankle_angle' else -raw('exo',native.replace('_flexion','_angle')+'_'+leg+'_torque_interaction',start,stop)/mass
                check(f'{canonical}_assistance_moment_{role}_Nm_kg',assistance)
                if native=='ankle_angle' and info['ankle_velocity_fallback'][role]!=fallback:raise ValueError('Fallback provenance differs')
            for kind,table,suffix,unit,scale in [('angle','angle_filt','','rad',np.pi/180),('velocity','velocity','_velocity','rad_s',np.pi/180),('moment','moment_filt','_moment','Nm_kg',1.),('biological_moment','moment_filt_bio','_moment','Nm_kg',1.)]:check(f'source_ankle_coordinate_{kind}_{role}_{unit}',raw(table,'ankle_angle_'+leg+suffix,start,stop)*scale)
            for axis in ('x','y','z'):check(f'source_grf_global_{axis}_{role}_N',raw('grf',f'fp_{leg}_force_{axis}',start,stop))
            check(f'grf_vertical_{role}_BW',raw('grf',f'fp_{leg}_force_y',start,stop)/(mass*9.81))
            for name in ('grf_anterior','grf_lateral'):check(f'{name}_{role}_BW',np.full(stop-start,np.nan))
            check(f'cop_vertical_{role}_m',np.full(stop-start,np.nan));check(f'cop_anterior_{role}_m',raw('insole_sim',f'insole_{leg}_cop_x',start,stop));check(f'cop_lateral_{role}_m',raw('insole_sim',f'insole_{leg}_cop_z',start,stop))
        if not inspect_contract(frame,mode='time').schema_passed:raise ValueError('Continuous batch contract failed')
        start=stop
    if start!=n:raise ValueError('Continuous row coverage incomplete')
    verify(plan['bindings'])
    report={'status':'continuous_source_streaming_checked_unreviewed','scientific_approval':False,'rows':n,'observation_id':identity,'finite_source_values':finite,'missing_source_values_unassessed':missing,'exact_all_unmodified_values_metadata_masks':True,'exact_segment_fields':sorted(segment_fields),'explicit_changed_fields':sorted(allowed_changes()),'audit_batch_rows':512,'derivative_halo_rows':2,'reference_sha256':digest(out/'reference.parquet'),'corrected_sha256':digest(out/'corrected.parquet'),'reused_exports':record.get('reused_exports'),'limitations':['Source-documented coordinates; physical posture not independently measured','Unverified anatomical horizontal forces and unavailable measurements remain unassessed','The earlier failed audit is not counted as successful evidence']}
    (out/'readback.json').write_text(json.dumps(report,indent=2)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__);base=ROOT/'converted_datasets/reconversion_v2'
    p.add_argument('--output-root',type=Path,required=True);p.add_argument('--run',action='store_true');p.add_argument('--worker',choices=['reference','corrected','audit']);p.add_argument('--record-index',type=int);a=p.parse_args();out=a.output_root.resolve();planpath=out/'plan.json'
    if a.worker:
        if a.worker=='audit':audit(planpath,a.record_index)
        else:convert_worker(planpath,a.record_index,a.worker)
        return
    if not out.is_relative_to(base):raise ValueError('Isolated output required')
    oldplan=base/'gt24_continuous_pilot_20261021/plan.json';plan=json.loads(oldplan.read_text());bindings=plan['bindings'];bindings[str(oldplan)]=digest(oldplan)
    failure=oldplan.parent/'0_audit.log'
    if 'ArrowMemoryError' not in failure.read_text():raise ValueError('Expected failed audit evidence differs')
    bindings[str(failure)]=digest(failure)
    for path in [Path(__file__),ROOT/'contributor_tools/preserve_um21_planar_estimates.py',ROOT/'contributor_tools/um21_planar_field_policy.py']:bindings[str(path.resolve())]=digest(path)
    for kind in ('reference','corrected'):
        path=oldplan.parent/'record_0'/(kind+'.parquet')
        if not path.is_file():raise ValueError('Reusable completed export absent')
        bindings[str(path)]=digest(path)
    plan['records'][0]['reused_exports']={kind:{'path':str(oldplan.parent/'record_0'/(kind+'.parquet')),'sha256':digest(oldplan.parent/'record_0'/(kind+'.parquet'))} for kind in ('reference','corrected')}
    plan.update(status='prepared_not_executed',replaces_failed_attempt=str(oldplan.parent),audit_batch_rows=512,derivative_halo_rows=2,bindings=bindings)
    verify(bindings)
    snapshots={'executed_v1_runner.py':ROOT/'contributor_tools/run_gt24_continuous_pilot.py','executed_v1_plan.json':oldplan}
    if out.exists():
        if not planpath.is_file() or {x.name for x in out.iterdir()}!={'plan.json','executed_v1_runner.py','executed_v1_plan.json'} or json.loads(planpath.read_text())!=plan:raise FileExistsError('Preserve existing v2 attempt')
        for name,path in snapshots.items():
            if digest(out/name)!=digest(path):raise ValueError('Executed-v1 snapshot changed')
    else:
        out.mkdir(parents=True)
        for name,path in snapshots.items():shutil.copyfile(path,out/name)
        planpath.write_text(json.dumps(plan,indent=2)+'\n')
    if not a.run:print(json.dumps({'status':'prepared_not_executed','plan':str(planpath)}));return
    reports=[]
    for index,record in enumerate(plan['records']):
        if 'reused_exports' in record:
            folder=out/f'record_{index}';folder.mkdir()
            for kind,evidence in record['reused_exports'].items():
                verify(bindings);target=folder/(kind+'.parquet');shutil.copyfile(evidence['path'],target)
                if digest(target)!=evidence['sha256']:raise ValueError('Reused export copy changed')
            stages=['audit']
        else:stages=['reference','corrected','audit']
        for stage in stages:
            verify(bindings)
            with (out/f'{index}_{stage}.log').open('x') as log:guarded([sys.executable,str(Path(__file__).resolve()),'--output-root',str(out),'--worker',stage,'--record-index',str(index)],out,log)
        reports.append(json.loads((out/f'record_{index}/readback.json').read_text()))
    verify(bindings);result={'status':'two_phase_continuous_streaming_pilot_checked_unreviewed','scientific_approval':False,'plan_sha256':digest(planpath),'records':reports,'failed_predecessor_preserved':str(oldplan.parent)}
    (out/'pilot_summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status']}))


if __name__=='__main__':main()
