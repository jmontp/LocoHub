"""Own equivalent of the RB02 MATLAB comparison against the RB05 AB06 phase export."""
import os,sys,json,glob,resource
import numpy as np,pyarrow.parquet as pq,pandas as pd
REPO='/mnt/s/workspace/locomotion-data-standardization/'; R=REPO+'converted_datasets/reconversion_v2/'
MAT=R+'gt21_force_corrected_full_20261021/AB06'; EXP=R+'gt21_rb05_export_AB06_r1/phase.parquet'; PAS=R+'gt21_rb_pass_batch_AB06_20261124/AB06'
CLS={}
CH=('vertical','anterior','lateral'); TOL=1e-9
cols=['source_recording_id','observation_id','reference_side','source_start_time_s','source_end_time_s']+[f'grf_{c}_{p}_BW' for c in CH for p in('ipsi','contra')]
pf=pq.ParquetFile(EXP); obs={}   # (rec, side, round start, round end) -> dict
for b in pf.iter_batches(batch_size=60000,columns=cols,use_threads=False):
    d=b.to_pandas()
    for oid,g in d.groupby('observation_id',sort=False):
        k=(g.source_recording_id.iloc[0],g.reference_side.iloc[0],round(float(g.source_start_time_s.iloc[0]),6),round(float(g.source_end_time_s.iloc[0]),6))
        if k in obs: obs[k]['parts'].append(g)
        else: obs[k]={'oid':oid,'parts':[g]}
for v in obs.values(): v['df']=pd.concat(v.pop('parts')); 
print('export obs',len(obs),flush=True)
stats={}; classes={'both_finite':0,'matlab_finite_export_missing':0,'matlab_missing_export_finite':0,'both_missing':0}
cyc_total=0; cyc_matched=0; cyc_unmatched=[]; exact={'pairs':0,'max':0.0,'cycles':0}; ends={'pairs':0,'max':0.0}
miss_mask={'matlab_finite_export_missing_vertical_matlab_value_BW_max':0.0}
for f in sorted(glob.glob(MAT+'/*/*/*/phase.parquet')):
    mode,rec=f.split('/')[-3],f.split('/')[-2]
    rid=f'AB06/{mode}/{rec}'
    m=pq.read_table(f,use_threads=False,columns=['observation_id','reference_side','source_start_time_s','source_end_time_s']+[f'grf_{c}_{p}_BW' for c in CH for p in('ipsi','contra')]).to_pandas()
    pp=PAS+f'/{mode}/{rec}.parquet'
    pas=pq.read_table(pp,use_threads=False,columns=['time_s','pelvis_forward_lab_z']).to_pandas() if os.path.exists(pp) else None
    for oid,g in m.groupby('observation_id',sort=False):
        cyc_total+=1; side=g.reference_side.iloc[0]; t0=float(g.source_start_time_s.iloc[0]); t1=float(g.source_end_time_s.iloc[0])
        e=obs.get((rid,side,round(t0,6),round(t1,6)))
        if e is None: cyc_unmatched.append((rid,side,t0,t1)); continue
        cyc_matched+=1; x=e['df']; assert len(x)==150
        t=pas.time_s.to_numpy(); fz=pas.pelvis_forward_lab_z.to_numpy()[(t>=t0)&(t<=t1)]; s=np.sign(np.nanmean(fz))
        tt=np.linspace(t0,t1,150); idx=np.interp(tt,t,np.arange(len(t))); on=np.abs(idx-np.rint(idx))<1e-9*200
        for part,leg in(('ipsi',side),('contra','left' if side=='right' else 'right')):
            for c in CH:
                a=g[f'grf_{c}_{part}_BW'].to_numpy(float); b=x[f'grf_{c}_{part}_BW'].to_numpy(float)
                if c=='lateral': a=a*(-s if leg=='right' else s)
                fin=np.isfinite(a)&np.isfinite(b); d=np.abs(a[fin]-b[fin])
                vm=g[f'grf_vertical_{part}_BW'].to_numpy(float); ve=x[f'grf_vertical_{part}_BW'].to_numpy(float)
                bad=fin&(np.abs(a-b)>TOL)
                for i in np.where(bad)[0]:
                    cl='A_unloaded_le_1N' if vm[i]*734.1804<=1.0 else ('B_export_vertical_zero_matlab_loaded' if ve[i]==0 else 'C_other')
                    k=(mode,c,cl); r_=CLS.setdefault(k,{'n':0,'max':0.0,'vm_max':0.0,'eg':[]}); r_['n']+=1; r_['max']=max(r_['max'],float(abs(a[i]-b[i]))); r_['vm_max']=max(r_['vm_max'],float(abs(vm[i])))
                    if cl.startswith('C') and len(r_['eg'])<5: r_['eg'].append((oid[-60:],leg,c,int(i),float(a[i]),float(b[i]),float(vm[i]),float(ve[i])))
                st=stats.setdefault((mode,c),{'pairs':0,'within':0,'max':0.0}); st['pairs']+=int(fin.sum()); st['within']+=int((d<=TOL).sum()); st['max']=max(st['max'],float(d.max()) if d.size else 0.0)
                classes['both_finite']+=int(fin.sum()); classes['matlab_finite_export_missing']+=int((np.isfinite(a)&~np.isfinite(b)).sum()); classes['matlab_missing_export_finite']+=int((~np.isfinite(a)&np.isfinite(b)).sum()); classes['both_missing']+=int((~np.isfinite(a)&~np.isfinite(b)).sum())
                if c=='vertical':
                    mm=np.isfinite(a)&~np.isfinite(b)
                    if mm.any(): miss_mask['matlab_finite_export_missing_vertical_matlab_value_BW_max']=max(miss_mask['matlab_finite_export_missing_vertical_matlab_value_BW_max'],float(a[mm].max()))
                ef=fin[[0,149]]&on[[0,149]]
                if ef.any(): ends['pairs']+=int(ef.sum()); ends['max']=max(ends['max'],float(np.abs(a[[0,149]]-b[[0,149]])[ef].max()))
                if on.all() and fin.any(): exact['pairs']+=int(fin.sum()); exact['max']=max(exact['max'],float(d.max()))
        if on.all(): exact['cycles']+=1
tot=sum(v['pairs'] for v in stats.values()); within=sum(v['within'] for v in stats.values())
out={'matlab_cycles':cyc_total,'matched_to_export_observation':cyc_matched,'unmatched':len(cyc_unmatched),'unmatched_examples':cyc_unmatched[:5],'finite_pairs':tot,'within_1e-9':within,'share':within/tot if tot else None,
 'by_mode_channel':{'/'.join(k):{'pairs':v['pairs'],'share_within':v['within']/v['pairs'] if v['pairs'] else None,'max_BW':v['max']} for k,v in sorted(stats.items())},
 'classes':classes,'on_grid_cycles':exact,'end_samples_on_grid':ends,'mask_note':miss_mask,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024}
json.dump({'/'.join(k):v for k,v in CLS.items()},open('/tmp/vrb05/cls2.json','w'),indent=1);json.dump(out,open('/tmp/vrb05/matlab_cmp.json','w'),indent=1); print(json.dumps(out,indent=1))
