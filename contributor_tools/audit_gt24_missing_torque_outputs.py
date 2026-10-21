"""Check reconstructed GT24 files against documented invalid source torques."""
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[name]='1'
import argparse
import json
from pathlib import Path
import resource
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest,ensure_storage_headroom


def check_missing(frame, invalid_side):
    if invalid_side not in ('left','right'):raise ValueError('Unknown invalid anatomical side')
    if not frame.reference_side.isin(['left','right']).all():raise ValueError('Unknown reference side')
    values=0
    for role in ['ipsi','contra']:
        mask=frame.reference_side.eq(invalid_side)
        if role=='contra':mask=~mask
        for joint in ['hip_flexion','knee_flexion','ankle_dorsiflexion']:
            for kind in ['moment','biological_moment']:
                column=f'{joint}_{kind}_{role}_Nm_kg'
                if column not in frame:raise ValueError('Missing expected torque column: '+column)
                if not frame.loc[mask,column].isna().all():
                    raise ValueError('Documented invalid torque became a value: '+column)
                values+=int(mask.sum())
    return values


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--batch-root',type=Path,required=True)
    p.add_argument('--source-review',type=Path,default=ROOT/'converted_datasets/reconversion_v2/gt24_invalid_torque_review_20261021/source_review.json')
    p.add_argument('--census',type=Path,default=ROOT/'converted_datasets/reconversion_v2/gt24_task_coverage_review_20261020/source_coverage.json')
    p.add_argument('--output-root',type=Path,required=True);a=p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    ensure_storage_headroom(a.output_root);a.output_root.mkdir(parents=True,exist_ok=False)
    review=json.loads(a.source_review.read_text());assert review['missing_variants']==0
    assert review['files_with_finite_or_infinite_invalid_torques']==0
    census=json.loads(a.census.read_text())
    mapping={(r['subject'],r['recording']):r for r in census['records'] if r['phase']=='Phase1And2'}
    report={'status':'checking','scientific_approval':False,'source_review_sha256':digest(a.source_review),
        'census_sha256':digest(a.census),'probe_sha256':digest(Path(__file__)),
        'checked_recordings':0,'checked_rows':0,'verified_missing_values':0,'records':[],
        'limitations':['Only documented failed-load-cell torque channels are checked','Omitted source recordings remain coverage gaps','Other signals, anatomical conventions and scientific suitability are not approved']}
    def save():
        path=a.output_root/'output_review.json';temp=path.with_suffix('.tmp');temp.write_text(json.dumps(report,indent=2)+'\n');temp.replace(path)
    save()
    try:
        for record in review['records']:
            for recording in record['matched_recordings']:
                key=(record['subject'],recording);expected=mapping[key]
                folder=a.batch_root/'gt24/Phase1And2'/record['subject']/recording
                path=folder/'phase.parquet';manifest_path=folder/'conversion_manifest.json'
                item={'subject':key[0],'recording':key[1],'invalid_side':record['side'],'source_mapping_status':expected['mapping_status']}
                if not manifest_path.is_file():
                    if expected['mapping_status']=='mapped_task':raise FileNotFoundError('Missing mapped recording: '+str(folder))
                    item['status']='omitted_source_recording_not_checked';report['records'].append(item);continue
                manifest=json.loads(manifest_path.read_text())
                assert manifest['status']=='converted_unreviewed' and manifest['schema_passed']
                output=next(x for x in manifest['outputs'] if x['name']=='phase.parquet')
                assert digest(path)==output['sha256']
                assert manifest['source']=='Phase1And2' and (manifest['subject'],manifest['recording'])==key
                sources={str(Path(x['path']).resolve()):x['sha256'] for x in manifest['sources']}
                for source in record['files']:
                    source_path=Path(source['path'])
                    if source_path.parent.name!=recording:continue
                    assert source['documented_invalid_values_are_all_nan']
                    assert digest(source_path)==source['sha256']
                    if source_path.name.endswith(('_moment_filt.csv','_moment_filt_bio.csv')):
                        assert sources[str(source_path.resolve())]==source['sha256'],'Output used different torque source'
                assert any(x['sha256']==review['readme_sha256'] for x in manifest['sources']),'Source documentation mismatch'
                rows=values=0
                for batch in pq.ParquetFile(path).iter_batches(batch_size=150,use_threads=False):
                    frame=batch.to_pandas(use_threads=False)
                    assert len(frame)==150 and frame.observation_id.nunique()==1
                    values+=check_missing(frame,record['side']);rows+=len(frame)
                assert rows>0
                item.update(status='documented_missing_torques_preserved',rows=rows,verified_missing_values=values,
                    output_sha256=output['sha256'],manifest_sha256=digest(manifest_path))
                report['records'].append(item);report['checked_recordings']+=1;report['checked_rows']+=rows;report['verified_missing_values']+=values;save()
        assert report['checked_recordings']>0,'No corrected recordings were checked'
        report['status']='available_outputs_checked_with_explicit_coverage_gaps' if any(r['status']=='omitted_source_recording_not_checked' for r in report['records']) else 'all_documented_invalid_torques_preserved'
    except Exception as error:report.update(status='failed',reason=str(error));raise
    finally:save()
    print(json.dumps({k:v for k,v in report.items() if k!='records'}))


if __name__=='__main__':main()
