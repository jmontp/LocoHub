import sys,json,collections,resource
sys.path.insert(0,'/mnt/s/workspace/locomotion-data-standardization')
import pyarrow.parquet as pq
from contributor_tools.common import data_contract as dc
R='/mnt/s/workspace/locomotion-data-standardization/converted_datasets/reconversion_v2/'
out={}
for sub in sys.argv[1:]:
    pf=pq.ParquetFile(R+f'gt21_rb05_export_{sub}_r1/phase.parquet'); n_obs=0; issues=collections.Counter(); sev=collections.Counter(); sp=0; pub=0; ids=set(); partial=0; rows=0
    for g in range(pf.num_row_groups):
        df=pf.read_row_group(g,use_threads=False).to_pandas(); rows+=len(df)
        cnt=df.groupby(['source_recording_id','observation_id','reference_side']).size()
        partial+=int((cnt!=150).sum())
        r=dc.inspect_contract(df,mode='phase'); n_obs+=r.observation_count; sp+=bool(r.schema_passed); pub+=bool(r.publishable)
        for i in r.issues: issues[(i.code,i.severity)]+=1
        for k in cnt.index: 
            assert k not in ids; ids.add(k)
    out[sub]={'rows':rows,'row_groups':pf.num_row_groups,'observations':n_obs,'unique_ids_across_file':len(ids),'chunks_schema_passed':sp,'chunks_publishable':pub,'partial_observations_in_chunk':partial,'issues':{f'{a}/{b}':v for (a,b),v in issues.items()}}
out['peak_rss_mib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
print(json.dumps(out,indent=1)); json.dump(out,open('/tmp/vrb05/contract.json','w'))
