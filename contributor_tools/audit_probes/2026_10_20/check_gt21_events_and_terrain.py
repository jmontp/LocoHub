"""Audit raw gait phases and source terrain metadata without inventing defaults."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,json,resource,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest
from contributor_tools.gt21_numeric_source import read_numeric_table


def phase_issues(phase,start,end):
    import numpy as np
    issues=[];interior=phase[start:end]
    if start<1 or end<=start or end>=len(phase):return ['invalid_event_indices']
    if not (phase[start]==0 and phase[end]==0 and phase[start-1]>0 and phase[end-1]>0):issues.append('endpoints_not_source_resets')
    if not np.isfinite(phase[start:end+1]).all():issues.append('nonfinite_source_phase')
    if np.any(np.diff(interior)<-1e-8):issues.append('source_phase_reversal')
    if np.count_nonzero(interior==0)!=1:issues.append('extra_zero_phase_samples')
    if np.any((interior<0)|(interior>100)):issues.append('source_phase_outside_0_100')
    return issues


def terrain_task(label):
    base={'rampascent':'incline_walking','rampdescent':'decline_walking','stairascent':'stair_ascent','stairdescent':'stair_descent'}
    if label in base:return base[label]
    if label.startswith('walk-') and label[5:] in base:return 'transition'
    if label.endswith('-walk') and label[:-5] in base:return 'transition'
    raise ValueError('Unmapped terrain source label: '+label)


def review_status(report):
    if any(not item['present_and_positive'] for item in report['terrain_metadata']):
        return 'source_terrain_metadata_incomplete'
    if any(item['phase_issues'] for item in report['completed_records']):
        return 'source_phase_issues_found'
    if not report['completed_records']:
        return 'no_completed_outputs_checked'
    return 'source_events_and_terrain_checked_unreviewed'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--batch-root',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True);a=p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
    import numpy as np,pandas as pd,scipy.io,pyarrow as pa,pyarrow.parquet as pq
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    plan=json.loads((a.batch_root/'inventory.json').read_text())['recordings'];state=json.loads((a.batch_root/'batch_status.json').read_text())
    source=ROOT/'contributor_tools/conversion_scripts/Gtech_2021/CAMARGO_ET_AL_J_BIOMECH_DATASET'
    a.output_root.mkdir(parents=True,exist_ok=False)
    report={'scientific_approval':False,'status':'checking','batch_snapshot':state,'terrain_metadata':[],'completed_records':[],
        'probe_sha256':digest(Path(__file__)),'reader_sha256':digest(ROOT/'contributor_tools/gt21_numeric_source.py'),
        'limitations':['Source gait-phase monotonicity does not prove physical heel contact timing','Terrain values are source annotations, not independently measured geometry','Task-label and phase checks cover completed outputs only; metadata presence covers all local ramp/stair source recordings']}
    nominal={}
    try:
        for rec in plan:
            if rec['mode'] not in ['ramp','stair']:continue
            field='rampIncline' if rec['mode']=='ramp' else 'stairHeight'
            path=source/rec['subject']/rec['date']/rec['mode']/'conditions'/rec['recording']
            value=scipy.io.loadmat(path,variable_names=[field]).get(field)
            valid=value is not None and value.size==1 and np.isfinite(value.item()) and value.item()>0
            number=float(value.item()) if valid else None
            key=(rec['subject'],rec['date'],rec['mode'],rec['recording']);nominal[key]=number
            report['terrain_metadata'].append({'recording':rec,'source_field':field,'source_value':number,'present_and_positive':bool(valid),'source_sha256':digest(path)})
        for rec in plan[:state['completed']]:
            folder=a.batch_root/rec['subject']/rec['date']/rec['mode']/Path(rec['recording']).stem
            manifest=json.loads((folder/'conversion_manifest.json').read_text())
            assert manifest['status']=='converted_unreviewed'
            assert digest(folder/'phase.parquet')==next(x['sha256'] for x in manifest['outputs'] if x['name']=='phase.parquet')
            for item in manifest['outputs']:
                if item['name'].startswith(('source_gc','source_conditions_')):
                    assert digest(folder/item['name'])==item['sha256'],'Native source comparison table changed'
            events={}
            for side in ['left','right']:
                channel='gc'+side.capitalize();item=next(x for x in manifest['sources'] if Path(x['path']).parent.name==channel)
                assert digest(Path(item['path']))==item['sha256'];events[side]=read_numeric_table(item['path'])
                native=pd.read_csv(folder/('source_'+channel+'_data.csv.gz'))
                assert native.columns.tolist()==list(events[side])
                for col,values in events[side].items():np.testing.assert_allclose(native[col],values,atol=1e-10,rtol=1e-12,equal_nan=True)
            labels=None
            if rec['mode'] in ['ramp','stair']:
                labels=pd.read_csv(folder/'source_conditions_labels.csv.gz')
            observations=0;issues=[];terrain_checked=0
            for batch in pq.ParquetFile(folder/'phase.parquet').iter_batches(batch_size=150,use_threads=False):
                frame=batch.to_pandas(use_threads=False);row=frame.iloc[0];assert len(frame)==150 and frame.observation_id.nunique()==1
                event=events[row.reference_side];clock=event['Header'];start=np.flatnonzero(np.isclose(clock,row.source_start_time_s,rtol=0,atol=1e-9));end=np.flatnonzero(np.isclose(clock,row.source_end_time_s,rtol=0,atol=1e-9));assert len(start)==len(end)==1
                found=phase_issues(event['HeelStrike'],int(start[0]),int(end[0]))
                if found:issues.append({'observation_id':row.observation_id,'issues':found})
                if labels is not None:
                    selected=labels.loc[labels.Header.between(row.source_start_time_s,row.source_end_time_s),'Label']
                    assert len(selected)>0 and selected.nunique()==1,'Output crosses or lacks source task labels'
                    label=selected.iloc[0];assert frame.task.eq(terrain_task(label)).all()
                    info=json.loads(row.task_info);assert not info.get('fallback',False),'Fallback task requires separate review'
                    number=nominal[(rec['subject'],rec['date'],rec['mode'],rec['recording'])];assert number is not None
                    if rec['mode']=='ramp':
                        expected=round(number,1)*(-1 if 'descent' in label else 1)
                        assert abs(info['incline_deg']-expected)<1e-10
                    else:assert abs(info['step_height_m']-round(number*.0254,3))<1e-10
                    terrain_checked+=1
                observations+=1
            report['completed_records'].append({'recording':rec,'observations':observations,'phase_issues':issues,'terrain_labels_and_values_checked':terrain_checked,'manifest_sha256':digest(folder/'conversion_manifest.json')})
        report['status']=review_status(report)
    except Exception as error:report.update(status='failed',reason=str(error));raise
    finally:(a.output_root/'event_terrain_review.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'terrain_source_records':len(report['terrain_metadata']),'missing_terrain_values':sum(not x['present_and_positive'] for x in report['terrain_metadata']),'completed_recordings':len(report['completed_records']),'observations':sum(x['observations'] for x in report['completed_records']),'source_phase_issues':sum(len(x['phase_issues']) for x in report['completed_records']),'terrain_observations_checked':sum(x['terrain_labels_and_values_checked'] for x in report['completed_records'])}))
    if report['status']!='source_events_and_terrain_checked_unreviewed':
        raise SystemExit(1)


if __name__=='__main__':main()
