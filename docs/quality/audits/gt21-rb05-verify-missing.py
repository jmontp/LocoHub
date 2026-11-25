import os,json,glob,resource,sys
import numpy as np,pyarrow.parquet as pq
REPO='/mnt/s/workspace/locomotion-data-standardization/'; R=REPO+'converted_datasets/reconversion_v2/'
cols=['observation_id','source_recording_id','reference_side','source_start_time_s','source_end_time_s']+[f'grf_{c}_{p}_BW' for c in('vertical','anterior','lateral') for p in('ipsi','contra')]
tot={}; per_mode={}
def add(k,n,mode):
    tot[k]=tot.get(k,0)+n; per_mode.setdefault(mode,{}); per_mode[mode][k]=per_mode[mode].get(k,0)+n
cache={}
def rec_arrays(sub,rid,mode):
    if cache.get('k')==rid: return cache['v']
    pas=pq.read_table(R+f'gt21_rb_pass_batch_{sub}_20261124/'+f"{rid}.parquet",columns=['time_s'],use_threads=False)
    t=pas['time_s'].to_numpy()
    mk=pq.read_table(R+f'gt21_rb_segment_batch_{sub}_20261125/force_mask/{rid}.parquet',use_threads=False)
    assert np.array_equal(mk['time_s'].to_numpy(),t)
    pz=pq.read_table(R+f'gt21_rb_pass_batch_{sub}_20261124/'+f"{rid}.parquet",columns=['pelvis_forward_lab_x','pelvis_forward_lab_z','plate_loaded_left','plate_loaded_right'],use_threads=False)
    hx=pz['pelvis_forward_lab_x'].to_numpy(); hz=pz['pelvis_forward_lab_z'].to_numpy()
    st_={}
    for leg in('left','right'):
        ld=pz[f'plate_loaded_{leg}'].to_numpy(zero_copy_only=False).astype(bool); n=len(t); stat=np.zeros(n,np.int8)  # 0 unloaded,1 ok,2 gate failed,3 heading nan
        k=0
        while k<n:
            if ld[k]:
                a=k
                while k<n and ld[k]: k+=1
                ok=np.isfinite(hx[a:k])&np.isfinite(hz[a:k])
                if not ok.any(): stat[a:k]=3
                else:
                    m=np.array([hx[a:k][ok].mean(),hz[a:k][ok].mean()]); m/=np.linalg.norm(m)
                    stat[a:k]=1 if abs(m[1])>=np.cos(np.radians(45)) else 2
            else: k+=1
        st_[leg]=stat
    v={'stat':st_,'t':t,'left':mk['force_missing_left'].to_numpy(zero_copy_only=False).astype(bool),'right':mk['force_missing_right'].to_numpy(zero_copy_only=False).astype(bool)}
    cache['k']=rid; cache['v']=v; return v
def maskph(m,t,tq):
    n=len(t); j=np.clip(np.searchsorted(t,tq,side='right')-1,0,n-2); j1=j+1
    on=np.abs(t[j]-tq)<1e-9; on2=np.abs(t[j1]-tq)<1e-9
    return np.where(on,m[j],np.where(on2,m[j1],m[j]|m[j1]))
for s in sorted(glob.glob(R+'gt21_rb05_export_*_r1')):
    sub=s.split('export_')[1].split('_r1')[0]
    pf=pq.ParquetFile(s+'/phase.parquet')
    for g in range(pf.num_row_groups):
        tb=pf.read_row_group(g,columns=cols,use_threads=False)
        oid=tb['observation_id'].to_numpy(zero_copy_only=False); rids=tb['source_recording_id'].to_numpy(zero_copy_only=False); side=tb['reference_side'].to_numpy(zero_copy_only=False)
        st=tb['source_start_time_s'].to_numpy(); en=tb['source_end_time_s'].to_numpy()
        F={c:tb[c].to_numpy(zero_copy_only=False) for c in cols[5:]}
        # obs boundaries
        b=np.flatnonzero(np.r_[True,oid[1:]!=oid[:-1],True])
        for a,e in zip(b[:-1],b[1:]):
            assert e-a==150
            rid=rids[a]; mode=rid.split('/')[1]
            ra=rec_arrays(sub,rid,mode); tq=np.linspace(st[a],en[a],150)
            for tag,leg in (('ipsi',side[a]),('contra','right' if side[a]=='left' else 'left')):
                mp=maskph(ra[leg],ra['t'],tq)
                V=F[f'grf_vertical_{tag}_BW'][a:e]; A=F[f'grf_anterior_{tag}_BW'][a:e]; L=F[f'grf_lateral_{tag}_BW'][a:e]
                anyn=np.isnan(V)|np.isnan(A)|np.isnan(L)
                um=anyn&~mp
                add('samples_total',150,mode)
                add('masked_samples',int(mp.sum()),mode)
                add('unmasked_missing_any_channel',int(um.sum()),mode)
                add('unmasked_missing_vertical',int((np.isnan(V)&~mp).sum()),mode)
                add('unmasked_missing_anterior',int((np.isnan(A)&~mp).sum()),mode)
                add('unmasked_missing_lateral',int((np.isnan(L)&~mp).sum()),mode)
                add('A_vertical_finite_shear_missing_(sign_or_heading_gate)',int((um&np.isfinite(V)).sum()),mode)
                add('B_vertical_missing_not_masked_(all_plates_missing)',int((um&np.isnan(V)).sum()),mode)
                add('masked_but_finite_force(should be 0)',int((mp&~np.isnan(V)).sum()),mode)
                add('masked_but_finite_anterior(should be 0)',int((mp&~np.isnan(A)).sum()),mode)
                add('V_missing_AND_A_finite_unmasked',int((um&np.isnan(V)&np.isfinite(A)).sum()),mode)
                if um.any():
                    t_=ra['t']; n_=len(t_); j=np.clip(np.searchsorted(t_,tq,side='right')-1,0,n_-2)
                    on=np.abs(t_[j]-tq)<1e-9; on2=np.abs(t_[j+1]-tq)<1e-9; jj=np.where(on,j,np.where(on2,j+1,j))
                    sj=ra['stat'][leg][jj]; sj1=ra['stat'][leg][np.minimum(jj+1,n_-1)]
                    z=np.where(sj>0,sj,sj1)   # status the sign function uses: own/earlier neighbour, else later
                    for code,name in ((2,'gate_failed_45deg'),(3,'heading_nan'),(0,'no_loaded_run_at_either_neighbour_(loaded_between_samples)'),(1,'sign_defined_(unexpected)')):
                        add('A_cause_'+name,int((um&(z==code)).sum()),mode)
    print(sub,flush=True)
json.dump({'total':tot,'by_mode':per_mode,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024},open('/tmp/vrb05/missing2.json','w'),indent=1)
print(json.dumps(tot,indent=1)); print(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
