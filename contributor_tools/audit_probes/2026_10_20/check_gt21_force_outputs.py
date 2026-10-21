"""Check completed GT21 GRF/COP outputs against original tables and declared mapping."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,gc,json,resource,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest
from contributor_tools.gt21_numeric_source import read_numeric_table


def select_plate(fp,markers,start,end,side,mode):
    """Evaluate source contact geometry, without waveform or torque sign fitting."""
    import numpy as np
    if side not in ('left','right'):raise ValueError('Unknown anatomical side')
    if mode=='treadmill':
        name='Treadmill_'+side[0].upper()
        complete=all(name+'_'+c in fp for c in ['vx','vy','vz','px','py','pz'])
        return (name,[name]) if complete else (None,[])
    ft,mt=fp['Header'],markers['Header']
    required=[f'{leg}_{point}_{axis}' for leg in ['L','R'] for point in ['Heel','Toe_Tip'] for axis in 'xyz']
    if not all(c in markers for c in required):return None,[]
    included=(mt>=start)&(mt<=end)&(mt>=ft[0])&(mt<=ft[-1])
    if included.sum()<2:return None,[]
    time=mt[included]
    feet={leg:np.column_stack([(markers[f'{leg}_Heel_{axis}'][included]+markers[f'{leg}_Toe_Tip_{axis}'][included])/2000 for axis in 'xyz']) for leg in ['L','R']}
    candidates=[]
    for column in fp:
        if not column.endswith('_vy'):continue
        name=column[:-3]
        if not all(name+'_'+c in fp for c in ['vx','vy','vz','px','py','pz']):continue
        force=np.interp(time,ft,fp[column],left=np.nan,right=np.nan)
        contact=force>100
        if not contact.any():continue
        cop=np.column_stack([np.interp(time,ft,fp[name+'_p'+axis],left=np.nan,right=np.nan) for axis in 'xyz'])
        valid=np.isfinite(cop).all(axis=1)&np.isfinite(feet['L']).all(axis=1)&np.isfinite(feet['R']).all(axis=1)
        if not valid[contact].all():continue
        squared={leg:np.sum((cop[contact]-feet[leg][contact])**2,axis=1) for leg in ['L','R']}
        wanted=side[0].upper();other='R' if wanted=='L' else 'L'
        if np.count_nonzero(squared[wanted]<squared[other])*3>2*int(contact.sum()):candidates.append(name)
    return (candidates[0] if len(candidates)==1 else None),candidates


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--batch-root',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True);a=p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    state=json.loads((a.batch_root/'batch_status.json').read_text());plan=json.loads((a.batch_root/'inventory.json').read_text())['recordings'][:state['completed']]
    mass_root=ROOT/'converted_datasets/reconversion_v2/gt21_subject_mass_review_20261021'
    mass_evidence=json.loads((mass_root/'source_comparison.json').read_text());assert digest(mass_root/'subject_masses.csv')==mass_evidence['csv_sha256']
    assert mass_evidence['native_exact_mass_readback']
    masses=pd.read_csv(mass_root/'subject_masses.csv').set_index('Subject').Weight.to_dict()
    a.output_root.mkdir(parents=True,exist_ok=False)
    report={'status':'checking','scientific_approval':False,'records':[],'batch_snapshot':state,
        'reader_sha256':digest(ROOT/'contributor_tools/gt21_numeric_source.py'),'probe_sha256':digest(Path(__file__)),
        'limitations':['Completed local recordings only; unconverted recordings remain unchecked','Checks declared laboratory-axis mapping, not a fully rotated anatomical frame','Plate assignment is checked against source-marker proximity rules, not independent contact labels','Missing direction, ambiguous plates and off-contact COP remain unavailable; range suitability is not established']}
    try:
        for record in plan:
            folder=a.batch_root/record['subject']/record['date']/record['mode']/Path(record['recording']).stem
            manifest=json.loads((folder/'conversion_manifest.json').read_text());assert manifest['status']=='converted_unreviewed'
            assert next(x['sha256'] for x in manifest['sources'] if Path(x['path']).name=='SubjectInfo.mat')==mass_evidence['source_sha256']
            assert digest(folder/'phase.parquet')==next(x['sha256'] for x in manifest['outputs'] if x['name']=='phase.parquet')
            tables={}
            for channel in ['fp','markers']:
                source=next(x for x in manifest['sources'] if Path(x['path']).parent.name==channel)
                assert digest(Path(source['path']))==source['sha256'];tables[channel]=read_numeric_table(source['path']);gc.collect()
            fp,markers=tables['fp'],tables['markers'];ft,mt=fp['Header'],markers['Header'];mass=masses[record['subject']]
            observations=finite=missing=0;errors={};selection_counts={'assigned':0,'multiple_candidates':0,'no_supported_plate':0}
            for batch in pq.ParquetFile(folder/'phase.parquet').iter_batches(batch_size=150,use_threads=False):
                frame=batch.to_pandas(use_threads=False);assert len(frame)==150 and frame.observation_id.nunique()==1
                row=frame.iloc[0];start,end=float(row.source_start_time_s),float(row.source_end_time_s);target=np.linspace(start,end,150)
                assert json.loads(row.subject_metadata)['weight_kg']==mass
                selected=(mt>=start)&(mt<=end);assert selected.sum()>=2
                direction=np.nan
                if mt[0]<=start<end<=mt[-1]:
                    pelvis={axis:(markers['L_ASIS_'+axis][selected]+markers['R_ASIS_'+axis][selected]-markers['L_PSIS_'+axis][selected]-markers['R_PSIS_'+axis][selected])/2 for axis in ['x','z']}
                    if np.isfinite(pelvis['x']).all() and np.isfinite(pelvis['z']).all() and (abs(pelvis['z'])>abs(pelvis['x'])).all():
                        if (pelvis['z']>0).all():direction=1
                        elif (pelvis['z']<0).all():direction=-1
                for role,side in [('ipsi',row.reference_side),('contra','left' if row.reference_side=='right' else 'right')]:
                    assert side in ['left','right'];leg=side[0].upper()
                    plate,candidates=select_plate(fp,markers,start,end,side,record['mode'])
                    selection_counts['assigned' if plate else 'multiple_candidates' if len(candidates)>1 else 'no_supported_plate']+=1
                    expected={}
                    for axis,component,sign in [('vertical','y',1),('lateral','x',1),('anterior','z',direction)]:
                        force=np.interp(target,ft,fp[plate+'_v'+component],left=np.nan,right=np.nan)*sign/(mass*9.81) if plate else np.full(150,np.nan)
                        expected[f'grf_{axis}_{role}_BW']=force
                        cop=np.interp(target,ft,fp[plate+'_p'+component],left=np.nan,right=np.nan) if plate else np.full(150,np.nan)
                        ankle=np.interp(target,mt[selected],markers[leg+'_Ankle_Lat_'+component][selected],left=np.nan,right=np.nan)/1000
                        expected[f'cop_{axis}_{role}_m']=(cop-ankle)*sign
                    contact=expected[f'grf_vertical_{role}_BW'];off=~np.isfinite(contact)|(contact<.2)
                    for feature,values in expected.items():
                        if feature.startswith('cop_'):values[off]=np.nan
                        np.testing.assert_allclose(frame[feature],values,rtol=1e-8,atol=1e-8,equal_nan=True,err_msg=str(folder)+' '+str(row.observation_id)+' '+feature)
                        good=np.isfinite(values);finite+=int(good.sum());missing+=int(np.isnan(values).sum())
                        if good.any():errors[feature]=max(errors.get(feature,0),float(np.max(abs(frame[feature].to_numpy()[good]-values[good]))))
                observations+=1
            report['records'].append({'recording':record,'observations':observations,'plate_selection_counts':selection_counts,'finite_values_checked':finite,'missing_values_checked':missing,'max_errors':errors,'manifest_sha256':digest(folder/'conversion_manifest.json')})
            del tables,fp,markers;gc.collect()
        assert report['records'];report['status']='completed_force_sources_checked_unreviewed'
    except Exception as error:report.update(status='failed',reason=str(error));raise
    finally:
        report['peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        (a.output_root/'force_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'recordings':len(report['records']),'observations':sum(x['observations'] for x in report['records']),'finite_values':sum(x['finite_values_checked'] for x in report['records']),'missing_values':sum(x['missing_values_checked'] for x in report['records']),'peak_rss_kib':report['peak_rss_kib']}))


if __name__=='__main__':main()
