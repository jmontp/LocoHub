"""Stage a native bilateral GT21 pilot without modifying an active converter.

The isolated converter changes only reference-leg selection. Existing strides
must remain identical; added strides receive their own source event identities.
Use --run only in the serial reconstruction queue.
"""
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[name]='1'
import argparse
import json
from pathlib import Path
import resource
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest,ensure_storage_headroom


def bilateral_source(source):
    start=source.index('function rows = extract_and_process_strides(')
    end=source.index('function rows = extract_and_process_strides_single_leg(',start)
    old=source[start:end]
    if old.count('gtech_determine_first_heel_strike(')!=1 or old.count('extract_and_process_strides_single_leg(')!=1:
        raise ValueError('Reference-leg selection changed; review the patch again')
    replacement='''function rows = extract_and_process_strides(trial_data, time_start, time_end, ...
    subject_str, subject_metadata, task, task_id, task_info, subject_mass, mode)
    % Separate source heel-strike cycles for each reference leg.
    % These observations overlap in time; they are not independent trials.
    rows = table();
    for reference = {'right','left'}
        selected = extract_and_process_strides_single_leg(trial_data, time_start, time_end, ...
            subject_str, subject_metadata, task, task_id, task_info, subject_mass, reference{1}, mode);
        if ~isempty(selected), rows = [rows; selected]; end
    end
end

'''
    return source[:start]+replacement+source[end:]


def verify_preserved(baseline, recovered):
    """Compare all columns for every previously exported observation."""
    import pandas as pd
    import pyarrow.parquet as pq
    def curves(path):
        for batch in pq.ParquetFile(path).iter_batches(batch_size=150,use_threads=False):
            frame=batch.to_pandas(use_threads=False)
            assert len(frame)==150 and frame.observation_id.nunique()==1
            yield frame.observation_id.iloc[0],frame
    # One bounded native recording only; never concatenate a full dataset.
    originals=dict(curves(baseline));seen=set();added=[]
    assert len(originals)*150==pq.ParquetFile(baseline).metadata.num_rows
    for identity,frame in curves(recovered):
        assert identity not in seen;seen.add(identity)
        if identity in originals:
            pd.testing.assert_frame_equal(originals[identity],frame,check_exact=True)
        else:
            added.append({'observation_id':identity,'reference_side':frame.reference_side.iloc[0],
                'start_s':float(frame.source_start_time_s.iloc[0]),'end_s':float(frame.source_end_time_s.iloc[0])})
    assert set(originals)<=seen,'Previously exported cycles disappeared'
    assert added,'Pilot recovered no cycles'
    return {'preserved_observations':len(originals),'added_observations':len(added),'added_cycles':added}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True,help='Completed per-record conversion_manifest.json')
    p.add_argument('--output-root',type=Path,required=True)
    p.add_argument('--run',action='store_true');a=p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
    from contributor_tools import run_gt21_native_batch as native
    from contributor_tools.audit_gt21_native_batch import check_record
    import pandas as pd
    baseline=json.loads(a.baseline.read_text());assert baseline['status']=='converted_unreviewed'
    for item in baseline['outputs']:assert digest(a.baseline.parent/item['name'])==item['sha256']
    for item in baseline['sources']:assert digest(Path(item['path']))==item['sha256']
    source_root=next(Path(x['path']).parent for x in baseline['sources'] if Path(x['path']).name=='SubjectInfo.mat')
    out=a.output_root.resolve();ensure_storage_headroom(out)
    plan_path=out/'pilot_plan.json'
    if not plan_path.exists():
        out.mkdir(parents=True,exist_ok=False)
        code=out/'isolated_code/Gtech_2021';code.mkdir(parents=True)
        original=native.CODE/'convert_gtech_2021_phase_to_parquet.m'
        (code/original.name).write_text(bilateral_source(original.read_text()))
        shutil.copytree(native.CODE/'utilities',code/'utilities',ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(native.CODE.parent/'matlab_common',code.parent/'matlab_common')
        dependencies=[Path(__file__),Path(native.__file__),native.GUARD,
            ROOT/'contributor_tools/audit_gt21_native_batch.py',ROOT/'contributor_tools/reconvert_recording.py',
            *sorted((ROOT/'contributor_tools/common').rglob('*.py')),
            *sorted((out/'isolated_code').rglob('*.m'))]
        plan={'status':'prepared_unreviewed','baseline_sha256':digest(a.baseline),
            'original_converter_sha256':digest(original),'code':native.evidence(dependencies),
            'recording':baseline['recording'],'scientific_approval':False,
            'limitations':['Overlapping leg cycles are not independent trials','Source readback does not approve anatomical conventions','Native pilot must finish before adopting this selection change']}
        plan_path.write_text(json.dumps(plan,indent=2)+'\n')
    plan=json.loads(plan_path.read_text());assert plan['baseline_sha256']==digest(a.baseline)
    assert all(digest(Path(x['path']))==x['sha256'] for x in plan['code'])
    if not a.run:print(json.dumps({'status':plan['status']}));return
    if shutil.disk_usage('/mnt/c').free<1024**3:raise OSError('C free space below 1 GiB')
    native.CODE=out/'isolated_code/Gtech_2021'
    summary={'status':'running','scientific_approval':False}
    summary_path=out/'pilot_summary.json'
    native.save(summary_path,summary)
    try:
        manifest=native.run_record(source_root,baseline['recording'],out/'converted',plan['code'])
        record=baseline['recording'];folder=out/'converted'/record['subject']/record['date']/record['mode']/Path(record['recording']).stem
        summary.update(verify_preserved(a.baseline.parent/'phase.parquet',folder/'phase.parquet'))
        mass_root=ROOT/'converted_datasets/reconversion_v2/gt21_subject_mass_review_20261021'
        evidence=json.loads((mass_root/'source_comparison.json').read_text())
        assert evidence['native_exact_mass_readback'] and digest(mass_root/'subject_masses.csv')==evidence['csv_sha256']
        masses=pd.read_csv(mass_root/'subject_masses.csv')
        readback=check_record(folder,dict(zip(masses.Subject,masses.Weight)),evidence)
        native.save(out/'source_readback.json',readback)
        assert all(digest(Path(x['path']))==x['sha256'] for x in plan['code'])
        summary.update(status='bilateral_pilot_source_checked_unreviewed',source_readback_sha256=digest(out/'source_readback.json'),
            output_sha256=digest(folder/'phase.parquet'))
    except Exception as error:summary.update(status='failed',reason=str(error));raise
    finally:native.save(summary_path,summary)


if __name__=='__main__':main()
