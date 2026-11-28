"""Check that MBLUE pelvis clock repair preserves every unrelated output column."""
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[name]='1'
import argparse
from collections import Counter
import json
from pathlib import Path
import resource
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline',type=Path);parser.add_argument('corrected',type=Path)
    parser.add_argument('output',type=Path);args=parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
    import pandas as pd
    import pyarrow.parquet as pq
    before=json.loads((args.baseline/'conversion_summary.json').read_text())
    after=json.loads((args.corrected/'conversion_summary.json').read_text())
    assert before['status']==after['status']=='all_normalized_blocks_reconstructed_unreviewed'
    originals={(r['subject'],r['source_path']):r for r in before['records']}
    counts=Counter();records=[]
    args.output.mkdir(parents=True,exist_ok=False)
    result={'status':'checking','scientific_approval':False,'probe_sha256':digest(Path(__file__)),
            'baseline_summary_sha256':digest(args.baseline/'conversion_summary.json'),
            'corrected_summary_sha256':digest(args.corrected/'conversion_summary.json')}
    try:
        for rec in after['records']:
            old=originals[(rec['subject'],rec['source_path'])]
            assert rec['source_sha256']==old['source_sha256']
            assert rec['subject_info_sha256']==old['subject_info_sha256']
            assert rec['observations']==old['observations']
            assert set(rec['outputs'])==set(old['outputs'])
            local=Counter();changed=set()
            for path,sha in rec['outputs'].items():
                a,b=args.baseline/path,args.corrected/path
                assert digest(a)==old['outputs'][path] and digest(b)==sha
                left,right=pq.ParquetFile(a),pq.ParquetFile(b)
                assert left.metadata.num_rows==right.metadata.num_rows
                for aa,bb in zip(left.iter_batches(batch_size=150,use_threads=False),right.iter_batches(batch_size=150,use_threads=False)):
                    x,y=aa.to_pandas(use_threads=False),bb.to_pandas(use_threads=False)
                    allowed=[c for c in x if c.startswith(('pelvis_sagittal_','thigh_sagittal_','shank_sagittal_','foot_sagittal_'))]
                    pd.testing.assert_frame_equal(x.drop(columns=allowed),y.drop(columns=allowed),check_exact=True)
                    differences=[c for c in allowed if not x[c].equals(y[c])]
                    side=x.reference_side.iloc[0]
                    if side=='left':
                        pd.testing.assert_frame_equal(x,y,check_exact=True)
                    local[side+('_changed' if differences else '_unchanged')]+=1
                    changed.update(differences)
            counts.update(local)
            records.append({'subject':rec['subject'],'source_path':rec['source_path'],
                            'counts':dict(local),'changed_columns':sorted(changed)})
        result.update(status='pelvis_fix_preservation_checked_unreviewed',counts=dict(counts),records=records,
                      all_other_columns_exactly_preserved=True,
                      full_baseline_coverage=len(records)==len(before['records']))
    except Exception as error:
        result.update(status='failed',reason=str(error));raise
    finally:
        (args.output/'preservation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'counts':dict(counts),'blocks':len(records)}))


if __name__=='__main__':main()
