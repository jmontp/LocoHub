import pyarrow as pa; pa.set_cpu_count(1); pa.set_io_thread_count(1)
import numpy as np,pyarrow.parquet as pq,json,glob,os,gc
R='/mnt/s/workspace/locomotion-data-standardization/converted_datasets/reconversion_v2/'
res=[];nrec=0;tot_masked=0;edge_only_masked=0;interior=[]
for f in sorted(glob.glob(R+'gt21_rb_segment_batch_AB*_20261125/force_mask/AB*/treadmill/*.parquet')):
    s=f.split('/force_mask/')[1].split('/')[0]; rec=os.path.basename(f)[:-8]
    L=pq.read_table(f,use_threads=False); 
    t=pq.read_table(R+f'gt21_rb_pass_batch_{s}_20261124/{s}/treadmill/{rec}.parquet',columns=["stance_left","stance_right"],use_threads=False)
    nrec+=1
    for x in('left','right'):
        lay=L[f'force_missing_{x}'].to_numpy(zero_copy_only=False).astype(bool)
        if not lay.any(): continue
        st=t[f'stance_{x}'].to_numpy(zero_copy_only=False).astype(bool)
        d=np.diff(np.concatenate([[0],st.astype(int),[0]])); S=np.where(d==1)[0]; E=np.where(d==-1)[0]
        for a,b in zip(S,E):
            mk=lay[a:b]
            if not mk.any(): continue
            tot_masked+=int(mk.sum())
            un=np.where(~mk)[0]
            if len(un)==0: interior.append((s,rec,x,a,b-a,'fully',int(mk.sum()))); continue
            idx=np.where(mk)[0]; inter=int(((idx>un.min())&(idx<un.max())).sum())
            if inter==0: edge_only_masked+=int(mk.sum())
            else: interior.append((s,rec,x,int(a),int(b-a),inter,int(mk.sum())))
    del L,t; gc.collect()
print('recs',nrec,'masked in stances',tot_masked,'edge-only masked',edge_only_masked)
print('stances with interior masked samples',len(interior))
for i in interior[:40]: print(i)
json.dump(interior,open('/tmp/vrb/tm_interior.json','w'))
