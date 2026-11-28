"""GT21-RB05 independent verification: seeded phase + continuous recompute. Own maths; only repo import is the source table reader."""
import sys, json, math, random, glob, os, resource
os.environ['OMP_NUM_THREADS']='1'
import numpy as np, pyarrow.parquet as pq
REPO='/mnt/s/workspace/locomotion-data-standardization/'
sys.path.insert(0,REPO)
from contributor_tools import gt21_numeric_source as reader   # data access only
R=REPO+'converted_datasets/reconversion_v2/'
BASES={'local_2024_copy_bundle':REPO+'contributor_tools/conversion_scripts/Gtech_2021/CAMARGO_ET_AL_J_BIOMECH_DATASET/','extracted_2024_copy_zip':'/mnt/s/locomotion_data/gt21_author_mirror_2024_extracted/'}
SEED=20261211
def draw():
    rnd=random.Random(SEED); subs=sorted(glob.glob(R+'gt21_rb05_export_*_r1'))
    byms={}
    for s in subs:
        sub=s.split('export_')[1].split('_r1')[0]
        for l in open(s+'/observations.jsonl'):
            o=json.loads(l)
            if o['table']=='phase': byms.setdefault((o['mode'],sub),[]).append(o)
    modes=['levelground','ramp','stair','treadmill']; picks=[]
    allsubs=sorted({k[1] for k in byms})
    for m in modes:
        for _ in range(3):
            sub=rnd.choice([s for s in allsubs if (m,s) in byms]); picks.append(rnd.choice(byms[(m,sub)]))
    cont=[]
    c=[]
    for s in subs:
        sub=s.split('export_')[1].split('_r1')[0]
        for l in open(s+'/recordings.jsonl'):
            r=json.loads(l)
            if r['status']=='exported': c.append(r)
    cont=rnd.sample(c,2)
    return picks,cont
def ledger(sub,rec_id):
    for l in open(R+f'gt21_rb_pass_batch_{sub}_20261124/ledger.jsonl'):
        d=json.loads(l)
        if f"{d['subject']}/{d['mode']}/{d['recording']}"==rec_id: return d
def rd(base,session,mode,ch,rec): return reader.read_numeric_table(f'{base}{session}/{mode}/{ch}/{rec}.mat')
def forces_1k(led,pas,tq,leg,mode,fp_t,fp,names,BW):
    """vertical,anterior,lateral BW at times tq from the 1kHz plate for leg."""
    t=pas['time_s'].to_numpy(); n=len(t)
    own=np.zeros((len(tq),len(names)),bool)
    if mode=='treadmill':
        pn='Treadmill_L' if leg=='left' else 'Treadmill_R'; own[:,names.index(pn)]=True
        own200=np.zeros((n,len(names)),bool); own200[:,names.index(pn)]=True
    else:
        own200=np.zeros((n,len(names)),bool)
        for c in led['plates']['contacts']:
            if c['owner']==leg:
                j=names.index(c['plate']); own[(tq>=t[c['a']]-1e-9)&(tq<=t[c['b']-1]+1e-9),j]=True; own200[c['a']:c['b'],j]=True
    def at(x):
        out=np.full(len(tq),np.nan); ok=(tq>=fp_t[0])&(tq<=fp_t[-1]); out[ok]=np.interp(tq[ok],fp_t,x); return out
    vy=np.stack([at(fp[p+'_vy']) for p in names],1); vx=np.stack([at(fp[p+'_vx']) for p in names],1); vz=np.stack([at(fp[p+'_vz']) for p in names],1)
    # lab-Z sign from the loaded run (loaded = pass 200 Hz owned vertical > 1 N), heading from pass table
    loaded=pas[f'plate_loaded_{leg}'].to_numpy().astype(bool)
    hx=pas['pelvis_forward_lab_x'].to_numpy(); hz=pas['pelvis_forward_lab_z'].to_numpy()
    zs=np.full(n,np.nan); k=0
    while k<n:
        if loaded[k]:
            a=k
            while k<n and loaded[k]: k+=1
            ok=np.isfinite(hx[a:k])&np.isfinite(hz[a:k])
            if ok.any():
                m=np.array([hx[a:k][ok].mean(),hz[a:k][ok].mean()]); m/=np.linalg.norm(m)
                if abs(m[1])>=math.cos(math.radians(45)): zs[a:k]=np.sign(m[1])
        else: k+=1
    # sign at phase time: sample itself if on clock, else earlier neighbour, else later
    j=np.clip(np.searchsorted(t,tq,side='right')-1,0,n-2)
    on=np.abs(t[j]-tq)<1e-9; on2=np.abs(t[np.minimum(j+1,n-1)]-tq)<1e-9
    jj=np.where(on,j,np.where(on2,j+1,j)); z=zs[jj]; z=np.where(np.isfinite(z),z,zs[np.minimum(jj+1,n-1)])
    ownf=own.astype(float)
    V=(vy*ownf).sum(1)/BW; Z=(vz*ownf).sum(1); X=(vx*ownf).sum(1)
    allnan=np.isnan(vy[:,:]).all(1); V[allnan]=np.nan
    ant=Z*z/BW; lat=X*(-z)*(1 if leg=='right' else -1)/BW
    unl=(~((vy*ownf).sum(1)>1.0))&np.isnan(z)&~allnan   # unloaded foot, no sign: no force = 0 (rule in pass docstring)
    ant[unl]=0.0; lat[unl]=0.0; ant[allnan]=np.nan; lat[allnan]=np.nan
    global LAST_GATE; LAST_GATE=int((np.isnan(ant)&~allnan).sum())
    # RB03 mask recomputed: stance and owned 200 Hz vertical < 20 N
    ownv=np.zeros(n)
    t1=fp_t
    vyc=np.stack([np.interp(t,fp_t,fp[p+'_vy']) for p in names],1)
    vyc[(t<fp_t[0])|(t>fp_t[-1])]=np.nan
    v200=np.where(own200,vyc,0).sum(1); v200[np.isnan(vyc).all(1)]=np.nan
    stance=pas[f'stance_{leg}'].to_numpy().astype(bool)
    m200=stance&~(np.nan_to_num(v200,nan=0.0)>=20.0)
    # phase-time mask: sample itself if on clock else true if either neighbour masked
    mp=np.where(on,m200[j],np.where(on2,m200[np.minimum(j+1,n-1)],m200[j]|m200[np.minimum(j+1,n-1)]))
    for a in (V,ant,lat): a[mp]=np.nan
    return V,ant,lat,mp
def interp200(t,y,tq):
    j=np.clip(np.searchsorted(t,tq,side='right')-1,0,len(t)-2)
    on=np.abs(t[j]-tq)<1e-9; on2=np.abs(t[np.minimum(j+1,len(t)-1)]-tq)<1e-9
    w=(tq-t[j])/(t[j+1]-t[j]); v=y[j]+w*(y[j+1]-y[j]); v=np.where(on,y[j],np.where(on2,y[np.minimum(j+1,len(t)-1)],v)); return v
res={'seed':SEED,'phase':[],'continuous':[]}
picks,cont=draw()
tolmax=0
def cmp(a,b):
    both=np.isfinite(a)&np.isfinite(b)
    return dict(n_both=int(both.sum()),max_diff=float(np.abs(a[both]-b[both]).max()) if both.any() else 0.0,finite_mismatch=int((np.isfinite(a)!=np.isfinite(b)).sum()))
for o in picks:
    sub=o['subject']; rid=o['source_recording_id']; mode=o['mode']; led=ledger(sub,rid)
    pas=pq.read_table(R+f'gt21_rb_pass_batch_{sub}_20261124/'+led['parquet']).to_pandas(); t=pas['time_s'].to_numpy()
    ph=pq.read_table(R+f'gt21_rb05_export_{sub}_r1/phase.parquet',filters=[('observation_id','=',o['observation_id'])],use_threads=False).to_pandas()
    r={'observation_id':o['observation_id'],'mode':mode,'rows':len(ph),'phase_grid_max_err':float(np.abs(ph['phase_ipsi'].to_numpy()-np.linspace(0,100,150)).max()),
       'const_meta':{c:int(ph[c].nunique(dropna=False)) for c in ('subject','source_recording_id','reference_side','task','task_id','observation_type','subject_metadata','held_signals')}}
    leg=o['reference_side']; other='right' if leg=='left' else 'left'
    tq=np.linspace(ph['source_start_time_s'].iloc[0],ph['source_end_time_s'].iloc[0],150)
    r['time_span_vs_obs']=[float(ph['source_start_time_s'].iloc[0]-o['start_s']),float(ph['source_end_time_s'].iloc[0]-o['end_s'])]
    base=BASES[led['source']]+sub+'/'
    fp=rd(base,led['session'],mode,'fp',rid.split('/')[-1]); names=led['plates']['channels']
    BW=led['body_weight_N']; fpt=np.asarray(fp['Header'])
    d={}
    for tag,lg in (('ipsi',leg),('contra',other)):
        for base_name in ('thigh_sagittal_angle','shank_sagittal_angle','foot_sagittal_angle','hip_flexion_angle','knee_flexion_angle','ankle_dorsiflexion_angle','hip_flexion_velocity','knee_flexion_velocity','ankle_dorsiflexion_velocity','hip_flexion_moment','knee_flexion_moment','ankle_dorsiflexion_moment'):
            unit='rad' if 'angle' in base_name else ('rad_s' if 'velocity' in base_name else 'Nm_kg')
            ex=f'{base_name}_{tag}_{unit}'; pc=f'{base_name}_{lg}_{unit}'
            mine=interp200(t,pas[pc].to_numpy(),tq); d[ex]=cmp(ph[ex].to_numpy(),mine)
        for j_ in ('hip_flexion','knee_flexion','ankle_dorsiflexion'):
            p=ph[f'{j_}_moment_{tag}_Nm_kg'].to_numpy()*ph[f'{j_}_velocity_{tag}_rad_s'].to_numpy()
            d[f'{j_}_power_{tag}']=cmp(ph[f'{j_}_power_{tag}_W_kg'].to_numpy(),p)
        V,A,L,mp=forces_1k(led,pas,tq,lg,mode,fpt,fp,names,BW)
        for nm,v in (('vertical',V),('anterior',A),('lateral',L)): d[f'grf_{nm}_{tag}']=cmp(ph[f'grf_{nm}_{tag}_BW'].to_numpy(),v)
        d[f'force_masked_samples_{tag}']=int(mp.sum())
        d[f'force_nan_unmasked_stored_{tag}']=int((np.isnan(ph[f'grf_anterior_{tag}_BW'].to_numpy())&~mp).sum())
    # held columns: held_signals text vs all-missing columns
    hs=json.loads(ph['held_signals'].iloc[0])
    allmiss=sorted(c for c in ph.columns if ph[c].dtype==float and ph[c].isna().all() and c!='phase_ipsi')
    r['held_signals_field']=json.dumps(hs) if isinstance(hs,dict) else str(hs); r['all_missing_columns']=allmiss
    r['checks']=d
    r['worst_non_force']=max(v['max_diff'] for k,v in d.items() if isinstance(v,dict) and not k.startswith('grf'))
    r['worst_force']=max(v['max_diff'] for k,v in d.items() if isinstance(v,dict) and k.startswith('grf'))
    r['finite_mismatch_total']=sum(v['finite_mismatch'] for v in d.values() if isinstance(v,dict))
    res['phase'].append(r); del fp
    print(o['observation_id'],r['worst_non_force'],r['worst_force'],r['finite_mismatch_total'],flush=True)
for c in cont:
    sub=c['subject']; rid=c['source_recording_id']; mode=c['mode']; led=ledger(sub,rid)
    pas=pq.read_table(R+f'gt21_rb_pass_batch_{sub}_20261124/'+led['parquet']).to_pandas()
    pf=pq.ParquetFile(R+f'gt21_rb05_export_{sub}_r1/time.parquet'); out=[]
    for g in range(pf.num_row_groups):
        tb=pf.read_row_group(g,use_threads=False)
        ids=set(tb.column('source_recording_id').unique().to_pylist())
        if rid in ids: out.append(tb.to_pandas())
    import pandas as pd
    tm=pd.concat(out); tm=tm[tm.source_recording_id==rid].reset_index(drop=True)
    r={'recording':rid,'mode':mode,'rows':len(tm),'pass_rows':len(pas),'time_equal':bool(np.array_equal(tm.time_s.to_numpy(),pas.time_s.to_numpy()))}
    d={}
    for col in tm.columns:
        if col in pas.columns and tm[col].dtype==float and 'grf' not in col:
            d[col]=cmp(tm[col].to_numpy(),pas[col].to_numpy())
    for lg in ('left','right'):
        for j_ in ('hip_flexion','knee_flexion','ankle_dorsiflexion'):
            d[f'{j_}_power_{lg}']=cmp(tm[f'{j_}_power_{lg}_W_kg'].to_numpy(),tm[f'{j_}_moment_{lg}_Nm_kg'].to_numpy()*tm[f'{j_}_velocity_{lg}_rad_s'].to_numpy())
        mask=pq.read_table(R+f'gt21_rb_segment_batch_{sub}_20261125/force_mask/'+led['parquet'].replace(sub+'/','',1) if False else R+f'gt21_rb_segment_batch_{sub}_20261125/force_mask/'+led['parquet']).to_pandas()
        mk=mask[f'force_missing_{lg}'].to_numpy().astype(bool)
        for nm in ('vertical','anterior','lateral'):
            a=tm[f'grf_{nm}_{lg}_BW'].to_numpy(); p=pas[f'grf_{nm}_{lg}_BW'].to_numpy().copy(); p[mk]=np.nan
            d[f'grf_{nm}_{lg}_vs_pass_masked']=cmp(a,p)
    r['checks']=d; r['worst']=max(v['max_diff'] for v in d.values()); r['finite_mismatch']=sum(v['finite_mismatch'] for v in d.values())
    res['continuous'].append(r); print(rid,r['worst'],r['finite_mismatch'],r['time_equal'],flush=True)
res['peak_rss_mib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
json.dump(res,open('/tmp/vrb05/verify_result.json','w'),indent=1,default=str)
print('rss',res['peak_rss_mib'])
