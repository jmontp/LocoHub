import numpy as np,pyarrow.parquet as pq,json
R='/mnt/s/workspace/locomotion-data-standardization/converted_datasets/reconversion_v2/'
s,m,r='AB27','treadmill','Treadmill_03_01'
t=pq.read_table(R+f'gt21_rb_pass_batch_{s}_20261124/{s}/{m}/{r}.parquet',columns=['time_s','stance_right','plate_loaded_right','grf_vertical_right_BW','grf_anterior_right_BW'])
L=pq.read_table(R+f'gt21_rb_segment_batch_{s}_20261125/force_mask/{s}/{m}/{r}.parquet')['force_missing_right'].to_numpy(zero_copy_only=False).astype(bool)
st=t['stance_right'].to_numpy(zero_copy_only=False).astype(bool); v=t['grf_vertical_right_BW'].to_numpy(); tt=t['time_s'].to_numpy(); pl=t['plate_loaded_right'].to_numpy(zero_copy_only=False).astype(bool)
d=np.diff(np.concatenate([[0],st.astype(int),[0]])); S=np.where(d==1)[0]; E=np.where(d==-1)[0]
for a,b in zip(S,E):
    mk=L[a:b]
    if mk.any():
        idx=np.where(mk)[0]; print('stance',a,b,'len',b-a,'t',tt[a],tt[b-1],'masked idx range',idx.min(),idx.max(),'n',len(idx),'contiguous',idx.max()-idx.min()+1==len(idx))
        print(' v at stance start..',np.round(v[a:a+4],3),' around masked',np.round(v[a+idx.min()-3:a+idx.min()+3],3),'last',np.round(v[b-4:b],3))
        print(' plate_loaded in stance',pl[a:b].mean(), 'any v<=20/BW unmasked', ((v[a:b]*667.47<20)&~mk).sum())
        print(' stance max v',v[a:b].max(), 'vertical during masked (min,max)',v[a:b][mk].min(),v[a:b][mk].max())
