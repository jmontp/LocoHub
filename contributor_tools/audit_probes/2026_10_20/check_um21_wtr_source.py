"""Independently compare Wtr companion cycles against source events and signals."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse
import hashlib
import json
from pathlib import Path
import resource
resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
import h5py
import numpy as np
import pyarrow.parquet as pq
from scipy.interpolate import interp1d
ROOT=Path(__file__).resolve().parents[3]


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output_root',type=Path);args=parser.parse_args()
    out=args.output_root;summary=json.loads((out/'conversion_summary.json').read_text())
    source=ROOT/'contributor_tools/conversion_scripts/Umich_2021/Streaming.mat'
    assert digest(source)==summary['source_sha256'];results=[]
    with h5py.File(source,'r',rdcc_nbytes=1024**2) as f:
        for record in summary['records']:
            for path,sha in record['outputs'].items():assert digest(out/path)==sha
            folder=out/record['subject'];trial=f['Streaming/'+record['subject']+'/Wtr'];events=trial['events']
            pairs=set()
            for side,key in [('left','LHS'),('right','RHS')]:
                hs=events[key][...].reshape(-1)
                pairs.update((side,int(a),int(b)) for a,b in zip(hs[:-1],hs[1:]))
            mapping=json.loads((folder/'source_columns.json').read_text());cuts=events['cutPoints'][...].T
            labels=[''.join(chr(int(c)) for c in f[ref][...].flat) for ref in events['tasks'][...].flat]
            seen=set();finite=0;maximum=0.
            for batch in pq.ParquetFile(folder/'source_cycles.parquet').iter_batches(batch_size=150,use_threads=False):
                frame=batch.to_pandas(use_threads=False);assert len(frame)==150 and frame.observation_id.nunique()==1 and frame.task.isna().all()
                side=frame.reference_side.iloc[0];a=int(frame.source_start_frame.iloc[0]);b=int(frame.source_end_frame.iloc[0]);key=(side,a,b)
                assert key in pairs and key not in seen;seen.add(key)
                np.testing.assert_allclose(frame.time_s,np.linspace(0,(b-a)/100,150))
                np.testing.assert_allclose(frame.phase_ipsi,np.linspace(0,100,150))
                np.testing.assert_allclose(frame.source_start_time_s,(a-1)/100);np.testing.assert_allclose(frame.source_end_time_s,(b-1)/100)
                overlaps=[{'index':i,'label':labels[i],'start_frame':int(start),'end_frame':int(end)} for i,(start,end) in enumerate(cuts) if start<b and a<end]
                assert all(json.loads(v)==overlaps for v in frame.source_protocol_intervals)
                for col,item in mapping.items():
                    raw=trial[item['group']+'/'+item['variable']][item['matlab_component_1based']-1,a-1:b]
                    expected=interp1d(np.arange(a,b+1),raw)(np.linspace(a,b,150))
                    actual=frame[col].to_numpy();np.testing.assert_allclose(actual,expected,rtol=1e-10,atol=1e-10,equal_nan=True)
                    valid=np.isfinite(expected);finite+=int(valid.sum())
                    if valid.any():maximum=max(maximum,float(np.max(abs(actual[valid]-expected[valid]))))
            assert seen==pairs,'Missing source cycles'
            results.append({'subject':record['subject'],'source_cycles':len(pairs),'finite_component_values_checked':finite,'maximum_error':maximum})
    full=len(results)==len(summary['source_subjects'])
    result={'status':'all_wtr_source_cycles_checked_unreviewed' if full else 'pilot_source_cycles_checked_unreviewed',
        'records':results,'scientific_approval':False,'summary_sha256':digest(out/'conversion_summary.json'),'probe_sha256':digest(Path(__file__)),
        'limitations':['Source components and cycle coverage checked; canonical gait labels remain unassigned',
            'Forceplates, markers, velocity profiles and physical conventions require separate verification']}
    with (out/'source_comparison.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(result))


if __name__=='__main__':main()
