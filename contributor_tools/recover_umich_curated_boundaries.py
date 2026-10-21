"""Recover source-curated UM21 cycles excluded by whole-cycle task windows.

Writes a separate supplement. Labels follow original curation at cycle start;
nominal protocol settings do not assert constant speed across the entire cycle.
"""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,json,resource,sys,shutil
from itertools import groupby,zip_longest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest,ensure_storage_headroom
from contributor_tools.reconvert_umich_streaming import cycle_frame,INCLINES
from contributor_tools.reconvert_umich_running import source_components


def recovered_window(item):
    if item['boundary_reason']!='curated_label_contains_start_but_not_end':
        raise ValueError('Recovery requires a source-curated cycle starting inside its label window')
    start,end=item['start_frame'],item['end_frame'];label=item['original_normalized_task']
    candidates=[w for w in item['overlapping_streaming_windows'] if w['label']==label and w['contains_start'] and not w['contains_end']]
    if len(candidates)!=1:raise ValueError('Ambiguous original task window')
    window=candidates[0]
    if not window['start_frame']<=start<=window['end_frame']<end:raise ValueError('Invalid boundary geometry')
    incline=INCLINES[item['condition']]
    info={'incline_deg':incline,'surface':'treadmill','source_task_label_scope':'cycle_start',
          'original_normalized_task':label,'original_curation_member':True,
          'cycle_crosses_source_task_window':True,'source_task_window_start_frame':window['start_frame'],
          'source_task_window_end_frame':window['end_frame'],
          'source_task_window_duration_fraction':(window['end_frame']-start)/(end-start)}
    if label.startswith('s'):
        task='incline_walking' if incline>0 else 'decline_walking' if incline<0 else 'level_walking'
        info['source_nominal_speed_m_s']=float(label[1:].replace('x','.'))
    elif label in {'a0x2','a0x5','d0x2','d0x5'}:
        task='transition';info['transition_phase']='acceleration' if label[0]=='a' else 'deceleration'
        info['source_nominal_acceleration_m_s2']=float(label[1:].replace('x','.'))*(1 if label[0]=='a' else -1)
    else:raise ValueError('Unsupported original source task label')
    return {'side':item['reference_side'],'start':start,'end':end,'task':task,'label':label,'info':info}


def verify_cycle(frame,trial,item):
    """Read source arrays independently with SciPy; check frames and metadata."""
    import numpy as np
    from scipy.interpolate import interp1d
    start,end=item['start_frame'],item['end_frame'];clock=np.arange(start-1,end)/100
    target=np.linspace((start-1)/100,(end-1)/100,150)
    assert len(frame)==150 and frame.observation_id.nunique()==1
    assert frame.reference_side.eq(item['reference_side']).all()
    np.testing.assert_allclose(frame.source_start_time_s,(start-1)/100,atol=1e-12,rtol=0)
    np.testing.assert_allclose(frame.source_end_time_s,(end-1)/100,atol=1e-12,rtol=0)
    np.testing.assert_allclose(frame.time_s,target-target[0],atol=1e-12,rtol=0)
    info=json.loads(frame.task_info.iloc[0]);assert info['source_task_label_scope']=='cycle_start'
    assert info['cycle_crosses_source_task_window'] and info['original_normalized_task']==item['original_normalized_task']
    assert 'speed_m_s' not in info and 'acceleration_m_s2' not in info
    finite=0;maximum=0.;expected_columns=set();angles={}
    for group,kind,unit in [('jointAngles','joint_angle','deg'),('jointForces','joint_force','N_kg'),('jointMoments','joint_moment','Nm_kg'),('jointPowers','joint_power','W_kg')]:
        if group not in trial:continue
        for name,ds in trial[group].items():
            expected=interp1d(clock,ds[:,start-1:end],axis=1,bounds_error=True)(target)
            for component,values in enumerate(expected):
                column=f'source_{kind}_{name.lower()}_component_{component}_{unit}';expected_columns.add(column)
                actual=frame[column].to_numpy();np.testing.assert_allclose(actual,values,atol=1e-8,rtol=1e-10,equal_nan=True)
                valid=np.isfinite(values);finite+=int(valid.sum())
                if valid.any():maximum=max(maximum,float(np.max(abs(actual[valid]-values[valid]))))
            if group=='jointAngles':angles[name]=expected[0]*np.pi/180
    assert {c for c in frame if c.startswith(('source_joint_angle_','source_joint_force_','source_joint_moment_','source_joint_power_'))}==expected_columns
    np.testing.assert_allclose(frame.pelvis_sagittal_angle_rad,angles['RPelvisAngles'],atol=1e-8,equal_nan=True)
    for role,leg in [('ipsi','R' if item['reference_side']=='right' else 'L'),('contra','L' if item['reference_side']=='right' else 'R')]:
        for joint,native in [('hip_flexion','HipAngles'),('knee_flexion','KneeAngles')]:
            values=angles[leg+native];np.testing.assert_allclose(frame[f'{joint}_angle_{role}_rad'],values,atol=1e-8,equal_nan=True)
            dt=(end-start)/100/149
            derivative=np.r_[(values[1]-values[0])/dt,(values[2:]-values[:-2])/(2*dt),(values[-1]-values[-2])/dt]
            np.testing.assert_allclose(frame[f'{joint}_velocity_{role}_rad_s'],derivative,atol=1e-8,equal_nan=True)
        np.testing.assert_allclose(frame[f'source_ankle_sagittal_angle_{role}_rad'],angles[leg+'AnkleAngles'],atol=1e-8,equal_nan=True)
        assert frame[f'ankle_dorsiflexion_angle_{role}_rad'].isna().all()
    return {'finite_source_values_checked':finite,'maximum_source_error':maximum,'source_components':len(expected_columns)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--window-review',type=Path,default=ROOT/'converted_datasets/reconversion_v2/um21_curated_window_edges_20261021/window_edges.json')
    p.add_argument('--curation-review',type=Path,default=ROOT/'converted_datasets/reconversion_v2/um21_tread_full_curation_v2_20261021/curation_coverage.json')
    p.add_argument('--source',type=Path,default=ROOT/'contributor_tools/conversion_scripts/Umich_2021/Streaming.mat')
    p.add_argument('--output-root',type=Path,required=True);p.add_argument('--max-cycles',type=int);a=p.parse_args()
    if a.max_cycles is not None and a.max_cycles<1:p.error('max-cycles must be positive')
    os.nice(max(0,19-os.nice(0)));resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
    import h5py,numpy as np,pandas as pd,pyarrow as pa,pyarrow.parquet as pq
    from contributor_tools.common.data_contract import inspect_contract
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    review=json.loads(a.window_review.read_text());assert digest(a.source)==review['streaming_sha256']
    initial_source_stat=a.source.stat()
    assert digest(a.curation_review)==review['curation_coverage_sha256']
    coverage=json.loads(a.curation_review.read_text());membership=a.curation_review.parent/'cycle_membership.jsonl'
    assert digest(membership)==coverage['membership_sha256']
    normalized=ROOT/'contributor_tools/conversion_scripts/Umich_2021/Normalized.mat'
    assert digest(normalized)==coverage['source_normalized_sha256']
    original_members=[json.loads(line) for line in membership.read_text().splitlines()]
    eligible={(x['subject'],x['condition'],x['reference_side'],x['start_frame'],x['end_frame'],x['original_normalized_task']) for x in original_members if x['streaming_status']=='excluded_in_original_curation'}
    assert eligible=={(x['subject'],x['condition'],x['reference_side'],x['start_frame'],x['end_frame'],x['original_normalized_task']) for x in review['records']}
    items=review['records'];assert len(items)==review['cycles']
    ids=[(x['subject'],x['condition'],x['reference_side'],x['start_frame'],x['end_frame']) for x in items];assert len(ids)==len(set(ids))
    ensure_storage_headroom(a.output_root);a.output_root.mkdir(parents=True,exist_ok=False)
    code=[Path(__file__),ROOT/'contributor_tools/reconvert_umich_streaming.py',ROOT/'contributor_tools/reconvert_umich_running.py',ROOT/'contributor_tools/reconvert_recording.py',ROOT/'contributor_tools/common/data_contract.py']
    hashes={str(x):digest(x) for x in code}
    for x in code:
        target=a.output_root/'code'/x.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(x.read_bytes())
    report={'status':'running','pid':os.getpid(),'scientific_approval':False,'source_sha256':review['streaming_sha256'],'normalized_source_sha256':coverage['source_normalized_sha256'],'curation_review_sha256':digest(a.curation_review),'review_sha256':digest(a.window_review),'code_sha256':hashes,'planned_cycles':len(items),'recovered_cycles':0,'records':[],
            'limitations':['Cycle labels follow original curation at start, not a constant task across the full cycle','Nominal protocol settings are not measured instantaneous speed or acceleration','Canonical ankle and kinetic frame mappings remain unverified','Separate supplement; does not overwrite or silently merge the earlier exports']}
    def save():
        path=a.output_root/'conversion_summary.json';temp=path.with_suffix('.tmp');temp.write_text(json.dumps(report,indent=2)+'\n');temp.replace(path)
    save()
    try:
        with h5py.File(a.source,'r',rdcc_nbytes=1024**2) as h:
            for (subject,condition),group in groupby(items[:a.max_cycles],key=lambda x:(x['subject'],x['condition'])):
                if (a.output_root/'STOP_AFTER_CURRENT').exists():report['status']='stopped_by_request';break
                ensure_storage_headroom(a.output_root)
                if shutil.disk_usage('/mnt/c').free<1024**3:raise OSError('C free space below 1 GiB')
                available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
                if available<2*1024**3:raise MemoryError('Available Linux memory below 2 GiB')
                assert all(digest(Path(k))==v for k,v in hashes.items())
                selected=list(group);trial=h[f'Streaming/{subject}/Tread/{condition}'];folder=a.output_root/subject/condition;folder.mkdir(parents=True);path=folder/'phase.parquet';writer=None
                finite=0;maximum=0.;mapping=None
                try:
                    for item in selected:
                        window=recovered_window(item)
                        events=trial['events'];hs=events['RHS' if window['side']=='right' else 'LHS'][...].reshape(-1)
                        assert any(lo==window['start'] and hi==window['end'] for lo,hi in zip(hs[:-1],hs[1:]))
                        labels=[''.join(chr(int(c)) for c in h[ref][...].reshape(-1)) for ref in events['tasks'][...].reshape(-1)]
                        matching=[(lo,hi) for label,(lo,hi) in zip(labels,events['cutPoints'][...].T) if label==window['label'] and lo<=window['start']<=hi<window['end']]
                        assert len(matching)==1 and tuple(matching[0])==(window['info']['source_task_window_start_frame'],window['info']['source_task_window_end_frame'])
                        frame=cycle_frame(trial,subject,condition,window)
                        values,current=source_components(trial,window['start'],window['end']);assert mapping is None or mapping==current;mapping=current
                        frame=pd.concat([frame,pd.DataFrame(values)],axis=1)
                        check=inspect_contract(frame,mode='phase');assert check.schema_passed,check.issues
                        table=pa.Table.from_pandas(frame,preserve_index=False)
                        if writer is None:writer=pq.ParquetWriter(path.with_suffix('.partial'),table.schema,compression='zstd')
                        writer.write_table(table)
                finally:
                    if writer is not None:writer.close()
                batches=pq.ParquetFile(path.with_suffix('.partial')).iter_batches(batch_size=150,use_threads=False)
                for batch,item in zip_longest(batches,selected):
                    assert batch is not None and item is not None,'Recovered cycle count differs from plan'
                    checks=verify_cycle(batch.to_pandas(use_threads=False),trial,item);finite+=checks['finite_source_values_checked'];maximum=max(maximum,checks['maximum_source_error'])
                path.with_suffix('.partial').replace(path)
                (folder/'source_columns.json').write_text(json.dumps(mapping,indent=2)+'\n');(folder/'recovered_cycles.json').write_text(json.dumps(selected,indent=2)+'\n')
                report['recovered_cycles']+=len(selected);report['records'].append({'subject':subject,'condition':condition,'cycles':len(selected),'finite_source_values_checked':finite,'maximum_source_error':maximum,'output_sha256':digest(path)});save()
            else:report['status']='all_curated_boundary_cycles_recovered_unreviewed' if report['recovered_cycles']==len(items) else 'partial_requested_limit'
        assert all(digest(Path(k))==v for k,v in hashes.items())
        assert (a.source.stat().st_size,a.source.stat().st_mtime_ns)==(initial_source_stat.st_size,initial_source_stat.st_mtime_ns)
    except Exception as error:report.update(status='failed',reason=str(error));raise
    finally:save()
    print(json.dumps({'status':report['status'],'cycles':report['recovered_cycles']}))


if __name__=='__main__':main()
