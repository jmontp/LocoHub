import json,sys,numpy as np,pyarrow.parquet as pq
R='/mnt/s/workspace/locomotion-data-standardization/converted_datasets/reconversion_v2/'
import glob
sample=json.load(open('/tmp/vrb/sample.json'))
# weights from pass ledgers
bw={}
for s,m,r in sample:
    for l in open(R+f'gt21_rb_pass_batch_{s}_20261124/ledger.jsonl'):
        d=json.loads(l)
        if d['recording']==r and d['mode']==m: bw[(s,m,r)]=d['body_weight_N']; break
out=[]
for s,m,r in sample:
    t=pq.read_table(R+f'gt21_rb_pass_batch_{s}_20261124/{s}/{m}/{r}.parquet',columns=['time_s']+[f'{a}_{x}' for x in('left','right') for a in('stance','plate_loaded')]+[f'grf_{c}_{x}_BW' for x in('left','right') for c in('vertical','anterior','lateral')])
    L=pq.read_table(R+f'gt21_rb_segment_batch_{s}_20261125/force_mask/{s}/{m}/{r}.parquet')
    assert np.array_equal(t['time_s'].to_numpy(),L['time_s'].to_numpy())
    res={'rec':f'{s}/{m}/{r}','n':t.num_rows,'BW_N':bw[(s,m,r)]}
    for x in ('left','right'):
        st=t[f'stance_{x}'].to_numpy(zero_copy_only=False).astype(bool)
        pl=t[f'plate_loaded_{x}'].to_numpy(zero_copy_only=False).astype(bool)
        v=t[f'grf_vertical_{x}_BW'].to_numpy()*bw[(s,m,r)]
        mine=st & (v<20)   # NaN<20 False
        lay=L[f'force_missing_{x}'].to_numpy(zero_copy_only=False).astype(bool)
        res[x]={'stance':int(st.sum()),'mine_masked':int(mine.sum()),'layer_masked':int(lay.sum()),'mismatch':int((mine!=lay).sum()),
          'layer_masked_outside_stance':int((lay&~st).sum()),
          'stance_unowned_total':int((st&~pl).sum()),'stance_unowned_zero_left_after_mask':int((st&~pl&~lay&(v==0)).sum()),
          'stance_unowned_unmasked':int((st&~pl&~lay).sum()),
          'stance_unmasked_below20':int((st&~lay&(v<20)).sum()),'masked_at_or_above20':int((lay&(v>=20)).sum()),
          'stance_unmasked_exact_zero_all_three':int((st&~lay&(v==0)&(t[f'grf_anterior_{x}_BW'].to_numpy()==0)&(t[f'grf_lateral_{x}_BW'].to_numpy()==0)).sum())}
        # edge analysis: runs of stance
        d=np.diff(np.concatenate([[0],st.astype(int),[0]])); starts=np.where(d==1)[0]; ends=np.where(d==-1)[0]
        full=0;interior=0;edge_only=0;nst=0;maxrun=0;maxfrac=0
        for a,b in zip(starts,ends):
            nst+=1; mk=lay[a:b]
            if mk.all(): full+=1; continue
            if mk.any():
                idx=np.where(mk)[0]
                # interior masked sample: masked with unmasked samples both before and after it within stance
                un=np.where(~mk)[0]; 
                inter=((idx>un.min())&(idx<un.max())).sum()
                interior+=int(inter>0); edge_only+=int(inter==0)
                maxrun=max(maxrun,int(mk.sum())); maxfrac=max(maxfrac,float(mk.mean()))
        res[x].update(stances=nst,fully_masked=full,partial_edge_only=edge_only,partial_with_interior_masked=interior,max_masked_in_partial=maxrun,max_masked_frac_partial=round(maxfrac,3))
    out.append(res)
    print(json.dumps(res))
json.dump(out,open('/tmp/vrb/mask_result.json','w'),indent=1)
