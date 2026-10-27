# Archived read-only investigation probe, 2026-10-20.
# Run from repository root with OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
# and nice -n 19 ionice -c 3. Local source paths and file versions are required.
# Results are scoped samples, not release approval.
import resource,json
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
import pyarrow.parquet as pq
from pathlib import Path
for p in Path('converted_datasets').glob('umich*.parquet'):
 f=pq.ParquetFile(p);m=f.metadata
 print(json.dumps({'file':str(p),'bytes':p.stat().st_size,'rows':m.num_rows,'groups':m.num_row_groups,'columns':f.schema_arrow.names,'created_by':m.created_by,'metadata_keys':list((m.metadata or {}).keys())},default=str))
 print('groups',[(i,m.row_group(i).num_rows,m.row_group(i).total_byte_size) for i in range(min(5,m.num_row_groups))])
 cols=[c for c in ['subject','task','task_info','step','phase_ipsi','time_s'] if c in f.schema_arrow.names]
 b=next(f.iter_batches(batch_size=150,columns=cols,use_threads=False));d=b.to_pydict();print('first', {k:[v[0],v[-1]] for k,v in d.items()})
