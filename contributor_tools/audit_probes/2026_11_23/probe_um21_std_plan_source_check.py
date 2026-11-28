# UM21-STD-plan read-only probe (one recording per run, one channel at a time, RLIMIT_AS 1 GiB, writes nothing). Run: flock /tmp/locohub-probe.lock nice -n 19 ionice -c 3 /usr/bin/time -v python3 THIS.py AB06 i5
import h5py, resource, numpy as np, json, sys
resource.setrlimit(resource.RLIMIT_AS,(1<<30,1<<30))
S='/mnt/s/workspace/locomotion-data-standardization/contributor_tools/conversion_scripts/Umich_2021/Streaming.mat'
SUB,COND=sys.argv[1],sys.argv[2]
def P(**k): print(json.dumps(k,default=lambda o: np.asarray(o).tolist()))
with h5py.File(S,'r',rdcc_nbytes=1<<20) as h:
    t=h[f'Streaming/{SUB}/Tread/{COND}']
    def mk(n):
        m=t['markers'][n][...]; x=m[:3].copy(); ok=m[3]==1; x[:,~ok]=np.nan; return x,float(ok.mean())
    M={};cov={}
    for n in ['LASI','RASI','LPSI','RPSI','RGT','LGT','RKNE','RKNEM','LKNE','LKNEM','RANK','RANKM','LANK','LANKM','RHEE','RTOE','LHEE','LTOE']:
        M[n],cov[n]=mk(n)
    P(marker_valid_fraction={k:round(v,4) for k,v in cov.items()})
    asi=(M['LASI']+M['RASI'])/2; psi=(M['LPSI']+M['RPSI'])/2; d=asi-psi
    ant=np.nanmean(d[:2],1); ant/=np.linalg.norm(ant)
    fwd=lambda v: v[0]*ant[0]+v[1]*ant[1]
    deg=np.degrees
    pelvis_m=deg(np.arctan2(asi[2]-psi[2],fwd(d)))
    angs=lambda n: t['jointAngles'][n][...][0]
    P(anterior_axis=ant, pelvis_marker_median_deg=np.nanmedian(pelvis_m),
      pelvis_published_plus_marker_med=np.nanmedian(angs('RPelvisAngles')+pelvis_m))
    res={}
    for s in 'RL':
        kn=(M[s+'KNE']+M[s+'KNEM'])/2; an=(M[s+'ANK']+M[s+'ANKM'])/2
        thigh=deg(np.arctan2(fwd(kn-M[s+'GT']),-(kn-M[s+'GT'])[2]))
        shank=deg(np.arctan2(fwd(an-kn),-(an-kn)[2]))
        ft=M[s+'TOE']-M[s+'HEE']
        foot=deg(np.arctan2(ft[2],fwd(ft)))
        hip_m=thigh-pelvis_m; knee_m=thigh-shank; ank_m=foot-shank
        r={}
        for nm,mv,pub in (('hip',hip_m,angs(s+'HipAngles')),('knee',knee_m,angs(s+'KneeAngles')),('ankle',ank_m,angs(s+'AnkleAngles'))):
            dd=pub-mv; ok=np.isfinite(dd)
            r[nm]={'pub_minus_marker_median':np.nanmedian(dd),'p5_p95':np.nanpercentile(dd,[5,95]).round(2).tolist(),'corr':float(np.corrcoef(pub[ok],mv[ok])[0,1])}
        r['foot_marker_p5_p95']=np.nanpercentile(foot,[5,95]).round(1).tolist()
        r['foot_progress_pub_comp1_p5_p95']=np.nanpercentile(t['jointAngles'][s+'FootProgressAngles'][...][0],[5,95]).round(1).tolist()
        r['heel_toe_len_m_median']=float(np.nanmedian(np.linalg.norm(ft,axis=0)))
        r['ankle_to_heel_fwd_m_median']=float(np.nanmedian(fwd(M[s+'HEE']-an)))
        r['ankle_to_toe_fwd_m_median']=float(np.nanmedian(fwd(M[s+'TOE']-an)))
        r['ankle_malleolar_width_m']=float(np.nanmedian(np.linalg.norm(M[s+'ANK']-M[s+'ANKM'],axis=0)))
        F=t['forceplates'][s+'Force'][...]; C=t['forceplates'][s+'CoP'][...]
        fz=-F[2]; loaded=fz>0.1*np.nanpercentile(fz,99)
        r['plate']={'force_p1_p99':[np.nanpercentile(c,[1,99]).round(2).tolist() for c in F],
                    'cop_loaded_p1_p99':[np.nanpercentile(c[loaded],[1,99]).round(4).tolist() for c in C],
                    'cop_nonfinite_or_zero_when_unloaded':[float(np.mean(~np.isfinite(c[~loaded])|(c[~loaded]==0))) for c in C],
                    'samples_per_frame':F.shape[1]/an.shape[1]}
        fa=fwd(an); n=an.shape[1]; tt=np.arange(F.shape[1])/10.0
        faI=np.interp(tt,np.arange(n),fa)
        idx=np.flatnonzero(loaded); segs=np.split(idx,np.flatnonzero(np.diff(idx)>1)+1)
        segs=[g for g in segs if len(g)>300]
        out=[]
        for g in segs[2:-2][:30]:
            g=g[len(g)//4:3*len(g)//4]
            row={}
            for k in (0,1):
                ok=np.isfinite(faI[g])&np.isfinite(C[k][g])
                if ok.sum()>50: row[k]=np.polyfit(C[k][g][ok],faI[g][ok],1)
            out.append(row)
        for k in (0,1):
            sl=[o[k][0] for o in out if k in o]
            r['plate'][f'axis{k}_slope_ankleFwd_vs_cop_median_q25_q75']=[float(np.median(sl)),*np.percentile(sl,[25,75]).round(5).tolist()] if sl else None
        r['n_stance_segments']=len(segs)
        res[s]=r
    P(sides=res)
