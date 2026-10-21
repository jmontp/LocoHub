"""Verify repaired GT24 outputs retain all unique observations and measured values."""
import resource
resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
import json
from pathlib import Path
import sys
import pandas as pd
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest
from contributor_tools.common.data_contract import inspect_contract


def main():
    old=ROOT/'converted_datasets/reconversion_v2/gt24_phase3_timing_20261020/gt24/Phase3'
    base=ROOT/'converted_datasets/reconversion_v2/gt24_unique_intervals_pilot_20261020'
    results=[]
    for path in sorted((base/'gt24/Phase3').glob('*/*/phase.parquet')):
        relative=path.relative_to(base/'gt24/Phase3');original=old/relative
        before=pd.read_parquet(original);after=pd.read_parquet(path)
        assert inspect_contract(after,mode='phase').schema_passed
        parts=[];counts={}
        for identity,frame in before.groupby('observation_id',sort=False):
            assert len(frame)%150==0
            counts[identity]=len(frame)//150
            first=frame.iloc[:150].reset_index(drop=True)
            for offset in range(150,len(frame),150):
                pd.testing.assert_frame_equal(first,frame.iloc[offset:offset+150].reset_index(drop=True),check_exact=True)
            parts.append(first)
        unique=pd.concat(parts,ignore_index=True)
        pd.testing.assert_frame_equal(unique.drop(columns='task_info'),after.drop(columns='task_info').reset_index(drop=True),check_exact=True)
        for identity,frame in after.groupby('observation_id',sort=False):
            info=json.loads(frame.task_info.iloc[0]);assert int(info['segmentation_candidate_count'])==counts[identity]
        manifest=json.loads((path.parent/'conversion_manifest.json').read_text())
        assert manifest['status']=='converted_unreviewed' and manifest['schema_passed']
        results.append({'subject':relative.parts[0],'recording':relative.parts[1],
            'old_rows':len(before),'new_rows':len(after),'unique_observations':len(parts),
            'values_unchanged_except_candidate_count_metadata':True,'schema_passed':True,
            'old_sha256':digest(original),'new_sha256':digest(path)})
    assert len(results)==5
    report={'recordings':results,'probe_sha256':digest(Path(__file__)),'scientific_approval':False,
        'limitations':['Verifies duplicate removal and value preservation, not physiological event boundaries','Full affected-dataset reconstruction remains pending']}
    (base/'source_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'recordings':len(results),'new_rows':sum(x['new_rows'] for x in results),'duplicate_rows_removed':sum(x['old_rows']-x['new_rows'] for x in results)}))


if __name__=='__main__':main()
