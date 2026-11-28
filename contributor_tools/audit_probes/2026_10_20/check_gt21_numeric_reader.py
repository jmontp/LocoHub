"""Compare the restricted Python MAT reader with eight exact native exports."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,json,resource,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest
from contributor_tools.gt21_numeric_source import read_numeric_table,SUPPORTED_LAYOUT_SHA256


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-root',type=Path,required=True);a=p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
    import numpy as np
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    a.output_root.mkdir(parents=True,exist_ok=False);records=[]
    for name in ['gt21_force_source_probe_1536_20261021','gt21_ramp_force_probe_20261021','gt21_stair_force_probe_20261021','gt21_levelground_force_probe_20261021']:
        folder=ROOT/'converted_datasets/reconversion_v2'/name
        plan=json.loads((folder/'probe_plan.json').read_text())
        status=json.loads((folder/'native_status.json').read_text(encoding='utf-8-sig'))
        assert status['status']=='completed' and status['exit_code']==0
        native=json.loads((folder/'native_source_manifest.json').read_text())
        assert native['status']=='native_source_tables_readback'
        for source,wanted in plan['sources'].items():
            path=Path(source);assert digest(path)==wanted
            values=read_numeric_table(path);target=folder/('source_'+path.parent.name+'_data.parquet')
            metadata=next(t for t in native['tables'] if t['channel']==path.parent.name)
            assert list(values)==metadata['variable_names']
            rows=metadata['rows'];assert all(len(v)==rows for v in values.values())
            offset=finite=nan=0
            for batch in pq.ParquetFile(target).iter_batches(batch_size=4096,use_threads=False):
                assert batch.schema.names==list(values)
                for col in batch.schema.names:
                    expected=batch.column(col).to_numpy(zero_copy_only=False);actual=values[col][offset:offset+len(batch)]
                    np.testing.assert_array_equal(actual,expected)
                    finite+=int(np.isfinite(actual).sum());nan+=int(np.isnan(actual).sum())
                offset+=len(batch)
            assert offset==rows
            records.append({'source':source,'source_sha256':wanted,'native_export_sha256':digest(target),
                'rows':rows,'columns':len(values),'finite_values_compared':finite,'nan_values_compared':nan,'exact_match':True})
            del values
    report={'status':'exact_native_comparison_passed','scientific_approval':False,'records':records,
        'supported_layout_sha256':SUPPORTED_LAYOUT_SHA256,'reader_sha256':digest(ROOT/'contributor_tools/gt21_numeric_source.py'),
        'probe_sha256':digest(Path(__file__)),'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'limitations':['Four source recordings, both force and marker tables; not every GT21 file','Unknown layouts and nonnumeric tables are rejected','Exact source decoding does not verify force plate assignment or physical conventions']}
    (a.output_root/'reader_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'tables':len(records),'finite_values':sum(r['finite_values_compared'] for r in records),'nan_values':sum(r['nan_values_compared'] for r in records),'peak_rss_kib':report['peak_rss_kib']}))


if __name__=='__main__':main()
