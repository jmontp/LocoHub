"""Retain the source-event reference view of each MBLUE stair window.

Both anatomical legs remain in every retained observation. The omitted view is
the same time window expressed relative to the non-event leg, not another cycle.
Existing files remain immutable; outputs and selection evidence use a new root.
"""
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[name]='1'
import argparse
import json
from pathlib import Path
import resource
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest,ensure_storage_headroom


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True);p.add_argument('--recovery',type=Path,required=True)
    p.add_argument('--output-root',type=Path,required=True)
    p.add_argument('--subject');p.add_argument('--source-path');a=p.parse_args()
    if bool(a.subject)!=bool(a.source_path):p.error('Pilot requires both subject and source-path')
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    summary_path=a.baseline/'conversion_summary.json';baseline=json.loads(summary_path.read_text())
    assert baseline['status']=='all_normalized_blocks_reconstructed_unreviewed'
    recovery=json.loads(a.recovery.read_text());assert recovery['status']=='all_stair_reference_windows_recovered_unreviewed'
    mapping={};source_hashes={}
    for record in recovery['records']:
        assert record['status']=='unique_source_matched'
        candidates=[c for c in record['candidates'] if c['status']=='all_windows_matched'];assert len(candidates)==1
        candidate=candidates[0]
        for kind in ('force','ik'):
            assert digest(Path(candidate[kind+'_path']))==candidate[kind+'_sha256']
        source_hashes[record['subject']]=record['normalized_sha256']
        for window in candidate['windows']:
            key=(record['subject'],window['source_path'],window['source_curve_index'])
            assert key not in mapping;mapping[key]=window
    for path,sha in recovery['source_code_sha256'].items():assert digest(Path(path))==sha
    records=[r for r in baseline['records'] if not a.subject or (r['subject']==a.subject and r['source_path']==a.source_path)]
    assert records,'No matching source blocks'
    ensure_storage_headroom(a.output_root);a.output_root.mkdir(parents=True,exist_ok=False)
    state={'status':'running','scientific_approval':False,'scope':'explicit_block' if a.subject else 'full_baseline',
           'probe_sha256':digest(Path(__file__)),'baseline_summary_sha256':digest(summary_path),
           'reference_recovery_sha256':digest(a.recovery),'records':[],
           'limitations':['Retains the original normalized time grid; reconstructed event timestamps are separate metadata',
               'Reference side follows the original source event convention, not independent physical contact validation',
               'Anatomical conventions and other existing dataset limitations remain unreviewed']}
    try:
        for record in records:
            if (a.output_root/'STOP_AFTER_CURRENT').exists():raise RuntimeError('Explicit stop request')
            ensure_storage_headroom(a.output_root)
            stair='/stairs/' in record['source_path'];seen=set();kept=[];removed=[];outputs={}
            if stair:assert record['source_sha256']==source_hashes[record['subject']]
            for relative,sha in record['outputs'].items():
                source=a.baseline/relative;assert digest(source)==sha
                target=a.output_root/relative;target.parent.mkdir(parents=True,exist_ok=True)
                if not stair:
                    shutil.copyfile(source,target);assert digest(target)==sha;outputs[relative]=sha
                    continue
                partial=target.with_suffix('.parquet.partial');writer=None
                try:
                    for batch in pq.ParquetFile(source).iter_batches(batch_size=150,use_threads=False):
                        frame=batch.to_pandas(use_threads=False)
                        assert len(frame)==150 and frame.observation_id.nunique()==1
                        index=int(frame.source_curve_index.iloc[0]);side=frame.reference_side.iloc[0]
                        key=(record['subject'],record['source_path'],index);window=mapping[key]
                        assert (index,side) not in seen;seen.add((index,side))
                        if side!=window['reference_side']:
                            removed.append(str(frame.observation_id.iloc[0]));continue
                        original=frame.copy()
                        end_force=window['end_matches_same_side_force_event']
                        marker_step='s2' if record['subject']=='AB02' else 's4'
                        if not end_force:assert record['source_path'].endswith('/descent/'+marker_step)
                        frame['source_event_start_time_s']=window['source_event_start_s']
                        frame['source_event_end_time_s']=window['source_event_end_s']
                        frame['source_event_start_basis']='force_threshold_pre_crossing_sample'
                        frame['source_event_end_basis']='force_threshold_pre_crossing_sample' if end_force else 'source_marker_based_endpoint'
                        pd.testing.assert_frame_equal(frame[original.columns],original,check_exact=True)
                        table=pa.Table.from_pandas(frame,preserve_index=False)
                        if writer is None:writer=pq.ParquetWriter(partial,table.schema,compression='zstd')
                        writer.write_table(table);kept.append(str(frame.observation_id.iloc[0]))
                finally:
                    if writer is not None:writer.close()
                expected={k[2] for k in mapping if k[:2]==(record['subject'],record['source_path'])}
                assert seen=={(index,side) for index in expected for side in ('left','right')}
                assert len(kept)==len(removed)==len(expected)
                assert pq.ParquetFile(partial).metadata.num_rows==150*len(kept)
                # Reopen persisted output and compare every retained source
                # column, rather than relying only on the in-memory frame.
                exported=iter(pq.ParquetFile(partial).iter_batches(batch_size=150,use_threads=False))
                for batch in pq.ParquetFile(source).iter_batches(batch_size=150,use_threads=False):
                    original=batch.to_pandas(use_threads=False)
                    index=int(original.source_curve_index.iloc[0])
                    window=mapping[(record['subject'],record['source_path'],index)]
                    if original.reference_side.iloc[0]!=window['reference_side']:continue
                    actual=next(exported).to_pandas(use_threads=False)
                    pd.testing.assert_frame_equal(actual[original.columns],original,check_exact=True)
                    assert actual.source_event_start_time_s.eq(window['source_event_start_s']).all()
                    assert actual.source_event_end_time_s.eq(window['source_event_end_s']).all()
                    assert actual.source_event_start_basis.eq('force_threshold_pre_crossing_sample').all()
                    basis='force_threshold_pre_crossing_sample' if window['end_matches_same_side_force_event'] else 'source_marker_based_endpoint'
                    assert actual.source_event_end_basis.eq(basis).all()
                assert next(exported,None) is None,'Unexpected extra output observations'
                partial.replace(target);outputs[relative]=digest(target)
            state['records'].append({'subject':record['subject'],'source_path':record['source_path'],
                'observations_before':record['observations'],'observations_after':len(kept) if stair else record['observations'],
                'retained_stair_observation_ids':kept,'omitted_nonreference_views':removed,'outputs':outputs})
        state.update(status='stair_reference_corrected_unreviewed',
            observations_before=sum(r['observations_before'] for r in state['records']),
            observations_after=sum(r['observations_after'] for r in state['records']))
    except Exception as error:state.update(status='failed',reason=str(error));raise
    finally:(a.output_root/'correction_summary.json').write_text(json.dumps(state,indent=2)+'\n')
    print(json.dumps({k:state[k] for k in ('status','scope','observations_before','observations_after')}))


if __name__=='__main__':main()
