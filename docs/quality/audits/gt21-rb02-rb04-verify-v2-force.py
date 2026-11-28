import sys,json,numpy as np,pyarrow.parquet as pq
sys.path.insert(0,'/mnt/s/workspace/locomotion-data-standardization')
from contributor_tools import gt21_numeric_source as rd
R='/mnt/s/workspace/locomotion-data-standardization/'
B=R+'contributor_tools/conversion_scripts/Gtech_2021/CAMARGO_ET_AL_J_BIOMECH_DATASET/AB06/10_09_18/levelground/'
rec='levelground_ccw_fast_01_01'
W=float(json.load(open(R+'converted_datasets/reconversion_v2/gt21_rb01_labels_final_20261124/AB06/subject_info_AB06.json'))['values']['Weight']); BW=W*9.81
f=rd.read_numeric_table(B+'fp/'+rec+'.mat'); ft=np.asarray(f['Header'])
mt=np.asarray(rd.read_numeric_table(B+'markers/'+rec+'.mat')['Header'])
t=pq.read_table(R+'converted_datasets/reconversion_v2/gt21_force_corrected_full_20261021/AB06/10_09_18/levelground/'+rec+'/phase.parquet',columns=['observation_id','reference_side','source_start_time_s','source_end_time_s','grf_vertical_ipsi_BW','grf_vertical_contra_BW']).to_pandas()
plates=[c[:-3] for c in f if c.endswith('_vy')]
print('fp dt',np.median(np.diff(ft)),'marker dt',np.median(np.diff(mt)),'plates',plates)
for oid,g in list(t.groupby('observation_id',sort=False))[:4]:
    g=g.reset_index(drop=True); a,b=g.source_start_time_s[0],g.source_end_time_s[0]; tt=np.linspace(a,b,150)
    for col in ('grf_vertical_ipsi_BW','grf_vertical_contra_BW'):
        y=g[col].values; fin=np.isfinite(y)
        if not fin.any() or np.nanmax(y)<0.3: continue
        best=None
        for p in plates:
            one=np.interp(tt,ft,np.nan_to_num(f[p+'_vy']))/BW
            two=np.interp(tt,mt,np.interp(mt,ft,np.nan_to_num(f[p+'_vy'])))/BW   # 1k -> 200 Hz -> phase
            d1=np.abs(one-y)[fin].max(); d2=np.abs(two-y)[fin].max()
            if best is None or d1<best[1]: best=(p,d1,d2,float((np.abs(two-one)[fin]).max()))
        print(oid[-40:],col[4:-3],'best plate',best[0],'1kHz-direct max diff %.2e'%best[1],'| via 200Hz max diff %.2e'%best[2],'| two routes differ %.3f BW'%best[3])
