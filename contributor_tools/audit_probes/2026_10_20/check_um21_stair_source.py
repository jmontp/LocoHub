"""Independent raw-cell and signal readback for UM21 stair staging outputs."""
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
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
    assert digest(source)==summary['source_sha256']
    checked=0;finite=0;maximum=0.;annotations=0;empty=0
    with h5py.File(source,'r',rdcc_nbytes=1024**2) as f:
        def text(ref):return ''.join(map(chr,f[ref][...].reshape(-1).astype(int)))
        source_plan={(s,c) for s in f['Streaming'] if 'Stair' in f['Streaming'][s] for c in f['Streaming'][s]['Stair']}
        assert source_plan=={(r['subject'],r['condition']) for r in summary['recordings']}
        for record in summary['recordings']:
            trial=f['Streaming/'+record['subject']+'/Stair/'+record['condition']];expected=[]
            for refs in trial['events/cutPoints'][...].T:
                if f[refs[1]].attrs.get('MATLAB_empty',False):
                    assert f[refs[2]].attrs.get('MATLAB_empty',False);empty+=1;continue
                label,leg=text(refs[0]),text(refs[1]);a,b=f[refs[2]][...].reshape(-1).astype(int)
                expected.append((label,'left' if leg=='L' else 'right',a,b));annotations+=1
            assert expected==[(w['label'],w['side'],w['start'],w['end']) for w in record['windows']]
            if 'exported_rows' not in record:continue
            for path,sha in record['outputs'].items():assert digest(out/path)==sha
            folder=out/record['subject']/record['condition'];mapping=json.loads((folder/'source_columns.json').read_text())
            batches=list(pq.ParquetFile(folder/'phase.parquet').iter_batches(batch_size=150,use_threads=False))
            assert len(batches)==len(expected)
            for batch,(label,side,a,b) in zip(batches,expected):
                frame=batch.to_pandas(use_threads=False);assert len(frame)==150
                assert frame.reference_side.eq(side).all() and frame.task_id.eq(label).all()
                np.testing.assert_allclose(frame.source_start_time_s,(a-1)/100)
                np.testing.assert_allclose(frame.source_end_time_s,(b-1)/100)
                np.testing.assert_allclose(frame.time_s,np.linspace(0,(b-a)/100,150))
                for col,item in mapping.items():
                    values=trial[item['group']+'/'+item['variable']][item['matlab_component_1based']-1,a-1:b]
                    target=interp1d(np.arange(a,b+1),values)(np.linspace(a,b,150))
                    np.testing.assert_allclose(frame[col],target,rtol=1e-10,atol=1e-10,equal_nan=True)
                    valid=np.isfinite(target);finite+=int(valid.sum())
                    if valid.any():maximum=max(maximum,float(np.max(abs(frame[col].to_numpy()[valid]-target[valid]))))
                for role,leg in [('ipsi',side[0].upper()),('contra','R' if side=='left' else 'L')]:
                    for joint in ['Hip','Knee']:
                        raw=trial['jointAngles/'+leg+joint+'Angles'][0,a-1:b]
                        expected_angle=interp1d(np.arange(a,b+1),raw)(np.linspace(a,b,150))*np.pi/180
                        np.testing.assert_allclose(frame[f'{joint.lower()}_flexion_angle_{role}_rad'],expected_angle,atol=1e-10,rtol=1e-10)
                checked+=1
    result={'status':'all_annotated_stair_cycles_source_checked_unreviewed' if checked==annotations else 'source_checked_partial_export_unreviewed','source_recordings':len(source_plan),
        'annotated_observations':annotations,'explicitly_empty_annotations':empty,'exported_observations_checked':checked,
        'source_component_values_checked':finite,'max_component_error':maximum,'scientific_approval':False,
        'summary_sha256':digest(out/'conversion_summary.json'),'probe_sha256':digest(Path(__file__)),
        'limitations':['Full source annotation inventory checked; signals checked only for exported pilot',
            'Physical ankle and segment conventions, marker coverage and unannotated pairs remain unresolved']}
    with (out/'source_comparison.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(result))


if __name__=='__main__':main()
