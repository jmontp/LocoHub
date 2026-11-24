# Verifier-written second implementation for UM21-S02 v7 (does not import the runner). run1: recompute + gate verdicts on a sample; run3 <index>: per-recording leg-plane glitch census. Run under prlimit --as=629145600, nice 19, one recording per process for run3.
import sys; sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from um21_s02_v7_verify_ver import *
import random
S=json.load(open(OUT+'s02_summary.json'))
recs=S['recordings']; fixed=['AB03/i10','AB08/i5']
pool=[r for r in recs if r not in fixed]
samp=random.Random(20261205).sample(pool,6)
todo=samp+fixed
H=h5py.File(SRC,'r')
print('sample',samp,flush=True)
gm=group_map(todo)
byrec={r['recording']:r for r in S['records']}
report={}
for rec in todo:
    s,c=rec.split('/'); t=H[f'Streaming/{s}/Tread/{c}']
    summ=byrec[rec]; mass=summ['meta']['body_mass_kg']
    v2=v2rows(rec,gm); R=derive(rec,t,v2,mass,summ)
    pub=pq.read_table(OUT+f'components/{s}/{c}/s02.parquet').to_pandas()
    unh=pq.read_table(OUT+f'components/{s}/{c}/cop_unheld.parquet').to_pandas()
    idx={o:i for i,o in enumerate(R['ids'])}
    # published arrays in id order
    pubo=pub.sort_values(['observation_id','sample']); 
    rep={}
    for leg,L in R['legs'].items():
        rows=L['rows']; ids=[R['ids'][i] for i in rows]
        cmp={}
        for col,arr in L['out'].items():
            P=np.stack([pub.loc[pub.observation_id==o].sort_values('sample')[col].values for o in ids])
            nanmatch=bool(np.array_equal(np.isnan(P),np.isnan(arr)))
            both=np.isfinite(P)&np.isfinite(arr)
            cmp[col]={'nan_pattern_equal':nanmatch,'n_nan_mismatch':int((np.isnan(P)!=np.isnan(arr)).sum()),'max_abs_diff':float(np.max(np.abs(P-arr)[both])) if both.any() else None}
        if 'cop' in L:
            for k,name in enumerate(('cop_anterior','cop_vertical','cop_lateral')):
                P=np.stack([unh.loc[unh.observation_id==o].sort_values('sample')[name].values for o in ids])
                a=L['cop'][k]; both=np.isfinite(P)&np.isfinite(a)
                cmp[name+'_unheld']={'n_nan_mismatch':int((np.isnan(P)!=np.isnan(a)).sum()),'finite_published':int(np.isfinite(P).sum()),'max_abs_diff_m':float(np.max(np.abs(P-a)[both])) if both.any() else None}
                Ph=np.stack([pub.loc[pub.observation_id==o].sort_values('sample')[name].values for o in ids])
                cmp[name+'_released']={'finite':int(np.isfinite(Ph).sum())}
        # gate verdict
        sg=summ['legs'][leg]['cop_gate']; rg=L['reg']
        mine={}
        if 'holdout_r' in L:
            ep=L['endpoint']['frac4']
            mine={'holdout_r':L['holdout_r'],'toe_frac4':ep,'toe_n':L['endpoint']['n'],'assign':L['assign'],'refit_dx':L['refit_dx'],'dx_summary':L['dx_summary']}
            v=(L['holdout_r']>=0.95) and ep is not None and ep>=0.95 and (L['assign'] or 0)>=0.95
            if rec=='AB04/d10': v=False
            mine['verdict']='pass' if v else 'held'
        else: mine['verdict']='held'
        rep[leg]={'compare':cmp,'gate_mine':mine,'gate_runner':{'verdict':sg['verdict'],'reasons':sg['reasons'],
            'r':(rg.get('ankle_holdout') or {}).get('r'),'toe_frac':(rg.get('endpoint_check_0p2bw') or {}).get('fraction_within_4cm_toe')}}
    report[rec]=rep
    print(rec,'rss',round(rss()),flush=True)
json.dump(report,open('/tmp/report1.json','w'),indent=1,default=float)
print('PEAK',rss())
