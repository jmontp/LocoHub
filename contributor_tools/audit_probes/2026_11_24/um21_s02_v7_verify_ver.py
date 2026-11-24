"""Independent recompute of UM21-S02 v7 (written by the verifier; does not import the worker's runner)."""
import os
os.environ.setdefault('ARROW_DEFAULT_MEMORY_POOL','system')
import h5py, json, re, sys, resource, numpy as np, pyarrow.parquet as pq
ROOT='/mnt/s/workspace/locomotion-data-standardization/'
SRC=ROOT+'contributor_tools/conversion_scripts/Umich_2021/Streaming.mat'
V2=ROOT+'converted_datasets/reconversion_v2/um21_r01_review_v2/full.parquet'
OUT=ROOT+'converted_datasets/reconversion_v2/um21_s02_frame_full_v7/'
UP=np.array([0,0,1.0]); N=150; G=9.81
ID=re.compile(r"^um21:Streaming/(AB\d{2})/Tread/([di]\d+):(right|left):frames:(\d+):(\d+)$")
SLOPE={"d10":10.0,"d5":5.0,"i0":0.0,"i5":5.0,"i10":10.0}
MK=["LASI","RASI","LPSI","RPSI","RGT","LGT","RKNE","RKNEM","LKNE","LKNEM","RANK","RANKM","LANK","LANKM","RHEE","RTOE","LHEE","LTOE"]
def rss(): return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
def rows_unit(v):
    n=np.linalg.norm(v,axis=-1,keepdims=True)
    with np.errstate(invalid='ignore',divide='ignore'): o=v/n
    o[n[...,0]==0]=np.nan; return o
def markers(t,n):
    o={}
    for k in MK:
        m=t['markers'][k][...]; x=m[:3].T.astype(float); ok=(m[3]==1)&np.isfinite(x).all(1); x[~ok]=np.nan; o[k]=x
    return o
def resample(x,pairs):
    out=[]
    for a,b in pairs:
        seg=x[a-1:b]; g=np.linspace(0,len(seg)-1,N); s=np.arange(len(seg))
        out.append(np.stack([np.interp(g,s,seg[:,k]) for k in range(seg.shape[1])],-1) if seg.ndim>1 else np.interp(g,s,seg))
    return np.array(out)
def v2rows(rec,groups):
    s,c=rec.split('/'); mk=f"um21:Streaming/{s}/Tread/{c}:"
    cols=['pelvis_sagittal_angle_rad','hip_flexion_moment_ipsi_Nm_kg','knee_flexion_moment_ipsi_Nm_kg','ankle_dorsiflexion_moment_ipsi_Nm_kg']
    rows={}
    pf=pq.ParquetFile(V2)
    for g in groups[rec]:
        tab=pf.read_row_group(g,columns=['observation_id']+cols)
        ids=tab.column(0).to_pylist(); arr={c_:tab.column(c_).to_numpy(zero_copy_only=False) for c_ in cols}
        for i,o in enumerate(ids):
            if o.startswith(mk):
                r=rows.setdefault(o,{c_:[] for c_ in cols})
                for c_ in cols: r[c_].append(arr[c_][i])
    return {o:{c_:np.array(v) for c_,v in r.items()} for o,r in rows.items()}
def group_map(recs):
    pf=pq.ParquetFile(V2); m={r:[] for r in recs}
    for g in range(pf.metadata.num_row_groups):
        ids=pf.read_row_group(g,columns=['observation_id']).column(0).to_pylist()
        for r in recs:
            s,c=r.split('/'); mk=f"um21:Streaming/{s}/Tread/{c}:"
            if ids[0].startswith(mk) or ids[-1].startswith(mk): m[r].append(g)
    return m
def hip_centres(M):
    rasi,lasi,rpsi,lpsi=M['RASI'],M['LASI'],M['RPSI'],M['LPSI']
    am,pm=(rasi+lasi)/2,(rpsi+lpsi)/2
    w=rasi-lasi; width=np.nanmedian(np.linalg.norm(w,axis=1)); er=w/np.linalg.norm(w,axis=1,keepdims=True)
    a=am-pm; depth=np.nanmedian(np.linalg.norm(a,axis=1)); a=a-np.sum(a*er,1,keepdims=True)*er
    ea=a/np.linalg.norm(a,axis=1,keepdims=True); eu=np.cross(er,ea)
    x=-0.24*depth-0.0099; y=-0.30*width-0.0109; z=0.33*width+0.0073
    base=am+x*ea+y*eu
    return {'R':base+z*er,'L':base-z*er}
def plate_at(v,pos):
    i0=np.floor(pos).astype(int); w=pos-i0; i1=np.minimum(i0+1,v.shape[-1]-1)
    return (1-w)*v[...,i0]+w*v[...,i1]
def derive(rec,t,v2,mass,summ):
    n=t['markers']['RASI'].shape[1]; M=markers(t,n)
    am,pm=(M['LASI']+M['RASI'])/2,(M['LPSI']+M['RPSI'])/2
    d=np.nanmean(am-pm,axis=0); d-= (d@UP)*UP; fwd=d/np.linalg.norm(d); rvec=np.cross(fwd,UP); rvec/=np.linalg.norm(rvec)
    pv=am-pm; pv-= (pv@UP)[:,None]*UP; pf_=rows_unit(pv)
    pd_=am-pm; pel=np.arctan2(pd_@UP,np.sum(pd_*pf_,1))
    hjc=hip_centres(M)
    vis={k:np.isfinite(v).all(1) for k,v in M.items()}
    ids=list(v2); P=[ID.fullmatch(o).groups() for o in ids]
    res={'ids':ids,'legs':{}}
    t_frame=np.arange(n)/100.0
    plate={}
    for side,leg in (('R','right'),('L','left')):
        rows=[i for i,p in enumerate(P) if p[2]==leg]
        pairs=[(int(P[i][3]),int(P[i][4])) for i in rows]
        lat,med=M[side+'KNEM'],M[side+'KNE']
        axr=(lat-med) if side=='R' else (med-lat)
        h=axr-(axr@UP)[:,None]*UP; fl=rows_unit(np.cross(UP,h))
        knee=(M[side+'KNE']+M[side+'KNEM'])/2; ank=(M[side+'ANK']+M[side+'ANKM'])/2; hip=hjc[side]
        def comp(v): return np.stack([np.sum(v*fl,-1),v@UP],-1)
        th=comp(knee-hip); sh=comp(ank-knee); ft=comp(M[side+'TOE']-M[side+'HEE'])
        thigh=np.arctan2(th[:,0],-th[:,1]); shank=np.arctan2(sh[:,0],-sh[:,1]); foot=np.arctan2(ft[:,1],ft[:,0])
        g=resample(np.stack([thigh,shank,foot],1),pairs)
        def ok(names): return np.array([all(vis[m][a-1:b].all() for m in names) for a,b in pairs])
        okt=ok(['LASI','RASI','LPSI','RPSI',side+'KNE',side+'KNEM']); oks=ok([side+'KNE',side+'KNEM',side+'ANK',side+'ANKM'])
        okf=ok([side+'HEE',side+'TOE',side+'KNE',side+'KNEM']); oka=ok([side+'ANK',side+'ANKM'])
        thg=np.where(okt[:,None],g[:,:,0],np.nan); shg=np.where(oks[:,None],g[:,:,1],np.nan); ftg=np.where(okf[:,None],g[:,:,2],np.nan)
        v2p=np.stack([v2[ids[i]]['pelvis_sagittal_angle_rad'] for i in rows])
        pm_=np.where(ok(['LASI','RASI','LPSI','RPSI'])[:,None],resample(pel,pairs),np.nan)
        dm=np.array([np.nanmedian(r) if np.isfinite(r).any() else np.nan for r in np.degrees(v2p-pm_)])
        ppass=np.isfinite(dm)&(np.abs(dm)<=1.0)
        pelv=np.where(ppass[:,None],v2p,np.nan)
        out={'pelvis_tilt':pelv,'hip_angle':thg-pelv,'knee_angle':thg-shg,'ankle_angle':ftg-shg,'thigh_angle':thg,'shank_angle':shg,'foot_angle':ftg}
        sp=np.array([(b-a)/100.0 for a,b in pairs])/149
        for k,src in (('pelvis_tilt',pelv),('thigh_angle',thg),('shank_angle',shg),('foot_angle',ftg)):
            out[k+'_velocity']=np.stack([np.gradient(src[u],sp[u],edge_order=1) for u in range(len(rows))])
        L={'rows':rows,'out':out,'okt':okt,'oks':oks,'okf':okf,'oka':oka,'pairs':pairs,'fl_frames':fl,'pel_med':dm}
        # ---- plate
        f=np.asarray(t['forceplates'][side+'Force'][...],float); c=np.asarray(t['forceplates'][side+'CoP'][...],float)/1000.0
        loaded=np.isfinite(f).all(0)&(-f[2]>20.0)&~(c==0).all(0)&np.isfinite(c).all(0)
        f[:,~loaded]=np.nan; c[:,~loaded]=np.nan
        plate[side]=loaded
        reg=summ['legs'][leg]['plate']
        L['reg']=reg
        if 'axis' in reg and reg.get('fit') and 'forward_m' in reg['fit']:
            axis,sign=reg['axis'],reg['sign']; tilt=np.radians(reg['tilt_used_deg'])
            dx,dy,dz=reg['fit']['forward_m'],reg['fit']['up_m'],(reg['fit']['lateral_m'] or 0.0)
            pos=np.array([10*((a-1)+np.arange(N)*(b-a)/149) for a,b in pairs])
            cg=np.stack([plate_at(c[0],pos),plate_at(c[1],pos)])
            fg=np.stack([plate_at(f[k],pos) for k in range(3)])
            lon=sign*(cg[0] if axis==0 else cg[1]); rgt=sign*(-cg[1]) if axis==0 else sign*cg[0]
            cp=np.stack([lon*np.cos(tilt),lon*np.sin(tilt),rgt])  # no shift
            gl=-sign*(fg[0] if axis==0 else fg[1]); gn=-fg[2]; gr=-(sign*(-fg[1])) if axis==0 else -(sign*fg[0])
            Fx=gl*np.cos(tilt)-gn*np.sin(tilt); Fy=gl*np.sin(tilt)+gn*np.cos(tilt)
            sh_=np.array([dx,dy,dz])[:,None,None]; cps=cp+sh_
            lab=cps[0][...,None]*fwd+cps[1][...,None]*UP+cps[2][...,None]*rvec
            geo=resample(np.concatenate([fl,ank,M[side+'HEE'],M[side+'TOE']],1),pairs)
            flg=rows_unit(geo[:,:,0:3].reshape(-1,3)).reshape(geo.shape[:2]+(3,)); a3,h3,t3=geo[:,:,3:6],geo[:,:,6:9],geo[:,:,9:12]
            def frame(pt):
                cc,ss=np.cos(ftg)[...,None],np.sin(ftg)[...,None]
                ef=cc*flg+ss*UP; eu=-ss*flg+cc*UP; er=np.cross(ef,eu); q=pt-a3
                latr=np.sum(q*er,-1)
                return np.stack([np.sum(q*ef,-1)-0.1,np.sum(q*eu,-1),latr if leg=='right' else -latr])
            okc=(okf&oka)[:,None]&np.isfinite(ftg)
            cf=frame(np.where(okc[...,None],lab,np.nan)); hf=frame(h3); tf=frame(t3)
            L.update({'cop':cf,'heel':hf,'toe':tf,'Fx':Fx,'Fy':Fy,'cp_nosh':cp,'cps':cps})
            # hold-out ankle moment
            kk=lambda p: resample(np.stack([p@fwd,p@UP],1),pairs)
            hipf,kneef,ankf=kk(hip),kk(knee),kk(ank)
            mom={j:np.stack([v2[ids[i]][f'{j}_flexion_moment_ipsi_Nm_kg' if j!='ankle' else 'ankle_dorsiflexion_moment_ipsi_Nm_kg'] for i in rows]) for j in ('hip','knee','ankle')}
            geo_ok=(okt&oks)[:,None]
            pk=np.stack([Fx,Fy])/mass
            use=np.isfinite(pk).all(0)&np.isfinite(cps).all(0)&geo_ok&np.isfinite(kneef).all(2)&np.isfinite(hipf).all(2)&np.isfinite(mom['hip'])&np.isfinite(mom['knee'])&(pk[1]>0.3*G)
            use_a=use&np.isfinite(mom['ankle'])&np.isfinite(ankf).all(2)
            tau=lambda cc,F,j: cc[0]-j[...,0] if False else None
            rx=cps[0]-ankf[:,:,0]; ry=cps[1]-ankf[:,:,1]
            tauv=rx*pk[1]-ry*pk[0]; pred=-tauv[use_a]; obs=mom['ankle'][use_a]
            L['holdout_r']=float(np.corrcoef(pred,obs)[0,1]); L['holdout_n']=int(use_a.sum())
            # refit forward shift with the summary's up shift (hip and knee equations)
            c0=cp[:2]
            th0=-(-(((c0[0]-hipf[...,0])*pk[1]-(c0[1]-hipf[...,1])*pk[0])))  # hip internal = -tau ; tau0_h = -joint_moment => tau
            # explicit: tau_hip=rx*Fy-ry*Fx ; m_hip=-tau ; need m_hip=-(tau0 + Fy dx - Fx dy_) => Fy dx = -m_hip - tau0 + Fx dy
            tau_h=((c0[0]-hipf[...,0])*pk[1]-(c0[1]-hipf[...,1])*pk[0]); tau_k=((c0[0]-kneef[...,0])*pk[1]-(c0[1]-kneef[...,1])*pk[0])
            A=np.concatenate([pk[1][use],pk[1][use]]); Tq=np.concatenate([mom['knee'][use]-tau_k[use],-mom['hip'][use]-tau_h[use]])+np.concatenate([pk[0][use],pk[0][use]])*dy
            L['refit_dx']=float(A@Tq/(A@A)); L['dx_summary']=dx
            L['endpoint']=endpoint(cf[0],hf[0],tf[0],(Fy/(mass*G))>0.2)
        res['legs'][leg]=L
    # plate assignment
    for side,leg in (('R','right'),('L','left')):
        L=res['legs'][leg]; other='L' if side=='R' else 'R'
        hs=np.asarray(t['events'][side+'HS'][...]).ravel(); hs=hs[np.isfinite(hs)].astype(int)
        same=tot=0
        for fr in hs:
            if fr<1 or fr+6>n: continue
            sl=slice(10*(fr-1),10*(fr+5)); tot+=1; same+=bool(plate[side][sl].any())
        L['assign']=same/tot if tot else None
    return res
def endpoint(ant,heel,toe,mask):
    et=[];skip=0
    for j in range(ant.shape[0]):
        ok=np.isfinite(ant[j])&np.isfinite(heel[j])&np.isfinite(toe[j])&mask[j]
        idx=np.flatnonzero(ok)
        if idx.size<10: continue
        k0=int(idx[0]);k1=k0
        while k1+1<N and ok[k1+1]: k1+=1
        if k0>8 or k1>=N-1: skip+=1; continue
        et.append(ant[j,k1]-toe[j,k1])
    et=np.array(et)
    return {'n':len(et),'skipped':skip,'frac4':float(np.mean(np.abs(et)<=0.04)) if len(et) else None}
