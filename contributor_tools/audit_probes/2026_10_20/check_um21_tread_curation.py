"""Account for every UM21 treadmill cycle against original normalized selection.

Membership is provenance, not scientific approval or a reason to rotate angles.
Uses small event tables and previously independently verified cycle ledgers.
"""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import argparse,hashlib,json,resource
from collections import Counter
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
import h5py
import numpy as np
ROOT=Path(__file__).resolve().parents[3]


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-root',type=Path,required=True);a=p.parse_args()
    base=ROOT/'converted_datasets/reconversion_v2/um21_tread_corrected_20261020'
    summary_path=base/'conversion_summary.json';summary=json.loads(summary_path.read_text())
    checked_path=ROOT/'converted_datasets/reconversion_v2/um21_tread_full_readback_20261021/source_comparison.json'
    checked=json.loads(checked_path.read_text());assert checked['summary_sha256']==digest(summary_path)
    checked_records={(r['subject'],r['condition']):r for r in checked['records']}
    source=ROOT/'contributor_tools/conversion_scripts/Umich_2021/Normalized.mat';source_sha=digest(source)
    streaming=Path(summary['source']['path']);assert digest(streaming)==summary['source']['sha256']
    a.output_root.mkdir(parents=True,exist_ok=False);reports=[];totals=Counter();by_task={}
    with h5py.File(source,'r',rdcc_nbytes=1024**2) as h, h5py.File(streaming,'r',rdcc_nbytes=1024**2) as raw, (a.output_root/'cycle_membership.jsonl').open('x') as membership:
        for record in summary['recordings']:
            subject,condition=record['subject'],record['condition'];folder=base/subject/condition;ledger_path=folder/'candidate_ledger.jsonl'
            assert digest(ledger_path)==checked_records[(subject,condition)]['ledger_sha256']
            assert digest(folder/'phase.parquet')==record['sha256']
            curated={}
            normalized_condition={'d5':'in5','d10':'in10'}.get(condition,condition)
            source_angles={side:raw[f'Streaming/{subject}/Tread/{condition}/jointAngles/{prefix}AnkleAngles'][0,:] for side,prefix in [('left','L'),('right','R')]}
            matched_first_values=0;max_first_error=0.;condition_groups=0
            for task,group in h[f'Normalized/{subject}/Walk'].items():
                if normalized_condition not in group or not isinstance(group[normalized_condition],h5py.Group):continue
                condition_groups+=1
                block=group[normalized_condition];details=block['events/StrideDetails'][...].T
                assert details.ndim==2 and details.shape[1]==4
                for index,(start,end,duration,leg) in enumerate(details):
                    assert np.isfinite([start,end,duration,leg]).all()
                    assert start==int(start) and end==int(end) and end-start==duration and leg in (1,2)
                    key=('left' if leg==1 else 'right',int(start),int(end));assert key not in curated
                    curated[key]=task
                    angles=block['jointAngles/AnkleAngles'];first=float(angles[index,0,0] if angles.ndim==3 else angles[0,0])
                    original=float(source_angles[key[0]][key[1]-1])
                    assert np.isfinite(first) and np.isfinite(original)
                    error=abs(first-original);assert error<1e-8,(subject,condition,key,error)
                    matched_first_values+=1;max_first_error=max(max_first_error,error)
            assert condition_groups>0,(subject,condition,normalized_condition)
            ledger=[json.loads(line) for line in ledger_path.read_text().splitlines()];seen=set();counts=Counter();task_counts={};unmatched=[]
            for item in ledger:
                key=(item['side'],item['start'],item['end']);assert key not in seen;seen.add(key)
                written=item.get('status')=='written_unreviewed';present=key in curated
                status=('exported' if written else 'excluded')+('_in_original_curation' if present else '_not_in_original_curation')
                counts[status]+=1
                if written:
                    task=item['task'];task_counts.setdefault(task,Counter())[status]+=1;by_task.setdefault(task,Counter())[status]+=1
                membership.write(json.dumps({'subject':subject,'condition':condition,'reference_side':key[0],'start_frame':key[1],'end_frame':key[2],'observation_id':item.get('observation_id'),'streaming_status':status,'streaming_task':item.get('task'),'original_normalized_task':curated.get(key),'exclusion_reason':item.get('excluded')})+'\n')
            for key in sorted(set(curated)-seen):
                unmatched.append({'side':key[0],'start':key[1],'end':key[2],'original_task':curated[key]})
            counts['original_curated_cycles_absent_from_streaming_ledger']=len(unmatched)
            assert counts['exported_in_original_curation']+counts['exported_not_in_original_curation']==record['observations']
            totals.update(counts);reports.append({'subject':subject,'condition':condition,'normalized_condition':normalized_condition,'curated_first_ankle_samples_checked':matched_first_values,'maximum_first_sample_error_deg':max_first_error,'original_curated_cycles':len(curated),'counts':dict(counts),'exported_by_task':{k:dict(v) for k,v in task_counts.items()},'unmatched_original_cycles':unmatched,'ledger_sha256':digest(ledger_path)})
    assert digest(source)==source_sha
    result={'status':'full_treadmill_curation_membership_accounted','scientific_approval':False,'records':reports,'totals':dict(totals),'exported_by_task':{k:dict(v) for k,v in by_task.items()},'source_normalized_sha256':source_sha,'source_streaming_sha256':summary['source']['sha256'],'condition_aliases':{'d5':'in5','d10':'in10'},'base_summary_sha256':digest(summary_path),'base_source_readback_sha256':digest(checked_path),'membership_sha256':digest(a.output_root/'cycle_membership.jsonl'),'probe_sha256':digest(Path(__file__)),'limitations':['Original normalized selection and streaming task windows differ; absence alone does not establish a bad cycle','Original curation membership does not approve the opposite-leg signal during the same window','No observations removed or source values changed by this audit','Unmatched original cycles require reconciliation before claiming full curated coverage']}
    (a.output_root/'curation_coverage.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'recordings':len(reports),'totals':dict(totals),'by_task':result['exported_by_task']}))


if __name__=='__main__':main()
