# Archived read-only investigation probe, 2026-10-20.
# Run from repository root with OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
# and nice -n 19 ionice -c 3. Local source paths and file versions are required.
# Results are scoped samples, not release approval.
import resource
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
import json,pathlib,collections,pyarrow.parquet as pq,math
results=[]
for a in json.loads(pathlib.Path('docs/quality/audits/remaining.json').read_text())['artifacts']:
 p=pathlib.Path(a['path']);f=pq.ParquetFile(p); names=f.schema_arrow.names
 cols=[x for x in ['subject','subject_metadata','task','task_id','task_info','step','phase_ipsi'] if x in names]
 estimate=max(sum(f.metadata.row_group(i).column(names.index(c)).total_uncompressed_size for c in cols) for i in range(f.metadata.num_row_groups))
 if estimate>64*1024**2: raise RuntimeError(f'projection exceeds limit {p} {estimate}')
 keys={}; subjects=collections.defaultdict(set); tasks=collections.Counter(); badphase=0; rows=0
 for b in f.iter_batches(batch_size=600,columns=cols,use_threads=False):
  for r in b.to_pylist():
   rows+=1; key=(r['subject'],r['task'],r['step']); v=keys.setdefault(key,[0,0,set(),set()]);v[0]+=1
   phase=r['phase_ipsi'];idx=round(phase*149/100) if phase is not None and math.isfinite(phase) else -1
   if 0<=idx<150 and abs(phase-idx*100/149)<1e-6:v[1]|=1<<idx
   else:badphase+=1
   v[2].add(r.get('task_id'));v[3].add(r.get('task_info'));subjects[r['subject']].add(r.get('subject_metadata'));tasks[r['task']]+=1
 result={'file':str(p),'rows_scanned':rows,'projected_max_group_bytes':estimate,'observation_key':['subject','task','step'],'keys':len(keys),'bad_count_keys':sum(v[0]!=150 for v in keys.values()),'bad_grid_keys':sum(v[1]!=(1<<150)-1 for v in keys.values()),'bad_phase_rows':badphase,'mixed_taskid_keys':sum(len(v[2])>1 for v in keys.values()),'mixed_taskinfo_keys':sum(len(v[3])>1 for v in keys.values()),'subject_count':len(subjects),'subjects':{s:sorted(v) for s,v in subjects.items()},'tasks_rows':dict(tasks)}
 results.append(result);print(json.dumps({k:v for k,v in result.items() if k!='subjects'}),flush=True)
 pathlib.Path('/tmp/remaining-scan.json').write_text(json.dumps(results,indent=2))
print('peak_rss_kib',resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
