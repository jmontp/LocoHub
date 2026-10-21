"""Explain source event-pair coverage in completed GT21 overground/treadmill recordings.

This is independent accounting, not approval of the single-reference-leg policy.
"""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import resource
resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
import numpy as np
import pandas as pd
import pyarrow.parquet as pq


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('batch',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    state=json.loads((args.batch/'batch_status.json').read_text());plan=json.loads((args.batch/'inventory.json').read_text())['recordings'][:state['completed']]
    args.output.mkdir(parents=True,exist_ok=False);reports=[];totals=Counter()
    for record in plan:
        if record['mode'] not in ('levelground','treadmill'):continue
        folder=args.batch/record['subject']/record['date']/record['mode']/Path(record['recording']).stem
        manifest=json.loads((folder/'conversion_manifest.json').read_text())
        for item in manifest['outputs']:assert digest(folder/item['name'])==item['sha256']
        field='Speed' if record['mode']=='treadmill' else 'Label'
        conditions=pd.read_csv(next(folder.glob('source_conditions_*.csv.gz')),usecols=['Header',field])
        segments=[]
        values=[i/20 for i in range(10,41)] if field=='Speed' else ['walk','turnccw','turncw','stand-walk','walk-stand']
        for label in values:
            mask=(conditions.Speed.sub(label).abs().le(.025) if field=='Speed' else conditions.Label.eq(label)).to_numpy()
            if field=='Label' and mask.sum()<50:continue
            edges=np.diff(np.r_[False,mask,False].astype(int));starts=np.flatnonzero(edges==1);ends=np.flatnonzero(edges==-1)-1
            for a,b in zip(starts,ends):
                if field=='Speed' and b-a+1<5000:continue
                start,end=float(conditions.Header.iloc[a]),float(conditions.Header.iloc[b])
                if end-start>0.05:segments.append({'label':label,'start':start,'end':end,'exported_sides':set()})
        clocks={name:pd.read_csv(next(folder.glob(f'source_{name}_*.csv.gz')),usecols=['Header']).Header.to_numpy() for name in ('ik_offset','id')}
        exported=set()
        for batch in pq.ParquetFile(folder/'phase.parquet').iter_batches(batch_size=150,columns=['reference_side','source_start_time_s','source_end_time_s'],use_threads=False):
            frame=batch.to_pandas(use_threads=False);row=frame.iloc[0];key=(row.reference_side,float(row.source_start_time_s),float(row.source_end_time_s))
            assert key not in exported;exported.add(key)
            matched=[s for s in segments if s['start']<=key[1]+1e-9 and key[2]<=s['end']+1e-9]
            assert len(matched)==1;matched[0]['exported_sides'].add(key[0])
        ledger=[];seen=set();counts=Counter()
        for side in ['left','right']:
            events=pd.read_csv(folder/f'source_gc{side.capitalize()}_data.csv.gz',usecols=['Header','HeelStrike'])
            reset=events.HeelStrike.eq(0)&events.HeelStrike.shift().gt(0);indices=np.flatnonzero(reset)
            for ai,bi in zip(indices[:-1],indices[1:]):
                a,b=float(events.Header.iloc[ai]),float(events.Header.iloc[bi]);key=(side,a,b)
                matched=[s for s in segments if s['start']<=a+1e-9 and b<=s['end']+1e-9]
                if key in exported:reason='exported';seen.add(key)
                elif not matched:reason='outside_complete_eligible_task_window'
                elif len(matched)>1:reason='ambiguous_task_windows'
                elif matched[0]['exported_sides'] and side not in matched[0]['exported_sides']:reason='opposite_reference_leg_not_exported'
                elif bi-ai+1<10 or events.HeelStrike.iloc[ai:bi+1].max()<50:reason='source_cycle_fails_converter_sample_or_phase_rule'
                elif any(np.count_nonzero((t>=a)&(t<=b))<10 for t in clocks.values()):reason='insufficient_source_ik_or_id_samples'
                else:reason='requires_further_reconciliation'
                counts[reason]+=1;ledger.append({'side':side,'start_s':a,'end_s':b,'reason':reason})
        assert seen==exported,'Output has no matching source event pair'
        totals.update(counts);reports.append({'record':record,'counts':dict(counts),'source_pairs':ledger,'manifest_sha256':digest(folder/'conversion_manifest.json')})
    report={'recordings':reports,'totals':dict(totals),'batch_snapshot':state,'probe_sha256':digest(Path(__file__)),'scientific_approval':False,
        'limitations':['Completed overground/treadmill subset only; ramps, stairs and unfinished records remain open',
            'Explains current converter policy, not approval of excluded opposite-leg observations',
            'Task-window eligibility uses current label/speed windows and sample thresholds; scientific validity remains unverified']}
    (args.output/'source_coverage.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'recordings':len(reports),'totals':dict(totals)}))


if __name__=='__main__':main()
