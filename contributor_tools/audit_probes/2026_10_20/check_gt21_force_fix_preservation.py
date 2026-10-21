"""Verify force/COP fixes preserve all other values in matching GT21 records."""
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
import argparse
from collections import Counter
from itertools import zip_longest
import json
from pathlib import Path
import resource
import sys
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest


def compare_frames(before,after):
    import numpy as np
    import pandas as pd
    assert list(before.columns)==list(after.columns),'Output schema changed'
    altered=[c for c in before if c.startswith(('grf_','cop_'))]
    fixed=[c for c in before if c not in altered]
    pd.testing.assert_frame_equal(before[fixed],after[fixed],check_exact=True)
    counts={}
    for col in altered:
        a=before[col].to_numpy();b=after[col].to_numpy()
        different=~((a==b)|(np.isnan(a)&np.isnan(b)))
        if different.any():counts[col]={'changed':int(different.sum()),
            'missing_to_finite':int((np.isnan(a)&np.isfinite(b)).sum()),
            'finite_to_missing':int((np.isfinite(a)&np.isnan(b)).sum())}
    return counts


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--before',type=Path,required=True)
    p.add_argument('--after',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True);a=p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    a.output_root.mkdir(parents=True,exist_ok=False)
    before_state=json.loads((a.before/'batch_status.json').read_text());after_state=json.loads((a.after/'batch_status.json').read_text())
    before_plan=json.loads((a.before/'inventory.json').read_text())['recordings'][:before_state['completed']]
    completed=json.loads((a.after/'inventory.json').read_text())['recordings'][:after_state['completed']]
    report={'scientific_approval':False,'status':'checking','records':[],'not_yet_rebuilt':[],
        'probe_sha256':digest(Path(__file__)),'before_snapshot':before_state,'after_snapshot':after_state,
        'limitations':['Preservation comparison is limited to records completed in both batches','Changed force/COP values need independent source and physical-frame checks','Unchanged values are not evidence of correct anatomical conventions']}
    try:
        for record in before_plan:
            if record not in completed:report['not_yet_rebuilt'].append(record);continue
            relative=Path(record['subject'])/record['date']/record['mode']/Path(record['recording']).stem
            old=a.before/relative;new=a.after/relative
            manifests=[json.loads((folder/'conversion_manifest.json').read_text()) for folder in [old,new]]
            assert manifests[0]['sources']==manifests[1]['sources'],'Source input identity changed'
            assert all(m['status']=='converted_unreviewed' for m in manifests)
            for folder,manifest in zip([old,new],manifests):
                expected=next(x['sha256'] for x in manifest['outputs'] if x['name']=='phase.parquet')
                assert digest(folder/'phase.parquet')==expected
            for item in manifests[1]['sources']:assert digest(Path(item['path']))==item['sha256']
            streams=[pq.ParquetFile(folder/'phase.parquet').iter_batches(batch_size=150,use_threads=False) for folder in [old,new]]
            rows=0;changes={}
            for before,after in zip_longest(*streams):
                assert before is not None and after is not None,'Observation count changed'
                bf=before.to_pandas(use_threads=False);af=after.to_pandas(use_threads=False)
                assert len(bf)==150 and bf.observation_id.nunique()==1 and af.observation_id.nunique()==1
                for col,counts in compare_frames(bf,af).items():changes.setdefault(col,Counter()).update(counts)
                rows+=len(bf)
            report['records'].append({'recording':record,'rows':rows,'non_force_columns_identical':True,
                'changed_columns':{c:dict(v) for c,v in changes.items()},
                'before_manifest_sha256':digest(old/'conversion_manifest.json'),'after_manifest_sha256':digest(new/'conversion_manifest.json')})
        assert report['records'],'No overlapping completed recordings'
        report['status']='non_force_values_preserved_in_all_compared_records'
    except Exception as error:report.update(status='failed',reason=str(error));raise
    finally:(a.output_root/'preservation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'recordings':len(report['records']),'rows':sum(r['rows'] for r in report['records']),'not_yet_rebuilt':len(report['not_yet_rebuilt'])}))


if __name__=='__main__':main()
