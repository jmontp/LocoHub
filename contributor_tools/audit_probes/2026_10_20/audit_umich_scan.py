# Archived read-only investigation probe, 2026-10-20.
# Run from repository root with OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
# and nice -n 19 ionice -c 3. Local source paths and file versions are required.
# Results are scoped samples, not release approval.
import resource,json,collections
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
import pyarrow.parquet as pq
out={}
for name in ['clean','raw']:
 f=pq.ParquetFile(f'converted_datasets/umich_2021_phase_{name}.parquet');counts=collections.Counter();ids=collections.Counter();prev=None;n=0;starts=[];bad=[];index=0;lastphase=None
 for batch in f.iter_batches(batch_size=4096,columns=['subject','task','step','phase_ipsi'],use_threads=False):
  d=batch.to_pydict()
  for s,t,step,p in zip(d['subject'],d['task'],d['step'],d['phase_ipsi']):
   key=(s,t,step);counts[t]+=1
   if prev is None or key!=prev or p<=lastphase:
    if prev is not None and (n!=150 or abs(lastphase-100)>1e-5 or abs(startphase)>1e-5):bad.append({'row':start,'id':prev,'n':n,'startphase':startphase,'endphase':lastphase})
    ids[key]+=1;n=0;start=index;startphase=p
    if t not in [x['task'] for x in starts]:starts.append({'task':t,'row':index,'row_group':next(i for i in range(f.metadata.num_row_groups) if index<sum(f.metadata.row_group(j).num_rows for j in range(i+1)))})
   n+=1;prev=key;lastphase=p;index+=1
 if n!=150 or abs(lastphase-100)>1e-5 or abs(startphase)>1e-5:bad.append({'row':start,'id':prev,'n':n,'startphase':startphase,'endphase':lastphase})
 out[name]={'rows_by_task':dict(counts),'curves':sum(ids.values()),'distinct_ids':len(ids),'reused_id_count':sum(v>1 for v in ids.values()),'reused_examples':[(k,v) for k,v in ids.items() if v>1][:5],'bad_phase_count':len(bad),'bad_phase_examples':bad[:8],'task_start_rows':starts}
print(json.dumps(out,indent=2))
