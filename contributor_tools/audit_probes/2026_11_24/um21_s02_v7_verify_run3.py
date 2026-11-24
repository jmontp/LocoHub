# Verifier-written second implementation for UM21-S02 v7 (does not import the runner). run1: recompute + gate verdicts on a sample; run3 <index>: per-recording leg-plane glitch census. Run under prlimit --as=629145600, nice 19, one recording per process for run3.
import sys; sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from um21_s02_v7_verify_ver import *
S=json.load(open(OUT+'s02_summary.json')); H=h5py.File(SRC,'r',rdcc_nbytes=1024**2)
tot={}
per=[]
cols=['thigh_angle','shank_angle','foot_angle','knee_angle','ankle_angle','hip_angle']
B=int(sys.argv[1])
for rec in S["recordings"][B:B+1]:
    import gc; gc.collect()
    s,c=rec.split('/'); t=H[f'Streaming/{s}/Tread/{c}']; n=t['markers']['RASI'].shape[1]
    M=markers(t,n)
    am,pm=(M['LASI']+M['RASI'])/2,(M['LPSI']+M['RPSI'])/2
    d=np.nanmean(am-pm,0); d-=(d@UP)*UP; fwd=d/np.linalg.norm(d)
    tp=pq.read_table(OUT+f'components/{s}/{c}/s02.parquet'); tu=pq.read_table(OUT+f'components/{s}/{c}/cop_unheld.parquet')
    oidall=np.array(tp.column('observation_id').to_pylist()[::150]); assert tp.num_rows==150*len(oidall)
    smp=tp.column('sample').to_numpy(); assert (smp.reshape(-1,150)==np.arange(150)).all()
    PUB={k:tp.column(k).to_numpy(zero_copy_only=False).reshape(-1,150) for k in cols+['cop_anterior','cop_vertical','cop_lateral']}
    UNH={k+'_unheld':tu.column(k).to_numpy(zero_copy_only=False).reshape(-1,150) for k in ('cop_anterior','cop_vertical','cop_lateral')}
    assert list(tu.column('observation_id').to_pylist()[::150])==list(oidall)
    del tp,tu
    for side,leg in (('R','right'),('L','left')):
        lat,med=M[side+'KNEM'],M[side+'KNE']
        axr=(lat-med) if side=='R' else (med-lat)
        h=axr-(axr@UP)[:,None]*UP; fl=rows_unit(np.cross(UP,h))
        ang=np.degrees(np.arccos(np.clip(np.sum(fl*fwd,1),-1,1)))
        fin=np.isfinite(ang)
        g100=fin&(ang>100); g90=fin&(ang>90); g60=fin&(ang>60)
        # stride windows from published ids
        sel=np.array([o.split(':')[2]==leg for o in oidall]); ids=list(oidall[sel])
        strides=[(o,int(o.split(':')[4]),int(o.split(':')[5])) for o in ids]
        flagged=[o for o,a,b in strides if g100[a-1:b].any()]
        mx=np.array([np.nanmax(ang[a_-1:b_]) if np.isfinite(ang[a_-1:b_]).any() else np.nan for o,a_,b_ in strides])
        J=np.nanmax(np.abs(np.diff(PUB['thigh_angle'][sel],axis=1)),axis=1) if sel.any() else None
        allnan=np.array([not np.isfinite(PUB['thigh_angle'][sel][i]).any() for i in range(len(ids))])
        rr={'rec':rec,'leg':leg,'strides':len(ids),'max_plane':[None if not np.isfinite(x) else float(x) for x in mx],'thigh_jump':[None if not np.isfinite(x) else float(x) for x in J],'thigh_range':[None if not np.isfinite(x) else float(x) for x in np.nanmax(np.abs(PUB['thigh_angle'][sel]),axis=1)],'allnan':allnan.tolist(),'ids':ids,'win':[(a_,b_) for o,a_,b_ in strides],'g100_frames':np.flatnonzero(g100).tolist()[:5000]}
        per.append(rr)
    print(rec,round(rss()),flush=True)
json.dump(per,open(f'/tmp/report3_{B}.json','w'),default=float)
print('PEAK',rss())
