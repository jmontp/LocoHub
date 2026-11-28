import json,glob
R='/mnt/s/workspace/locomotion-data-standardization/converted_datasets/reconversion_v2/'
n=0;ne=0;aff=[];tot=0
from collections import Counter
for f in sorted(glob.glob(R+'gt21_rb_segment_batch_AB*_20261125/steps.jsonl')):
    for l in open(f):
        d=json.loads(l)
        if d['mode']!='treadmill': continue
        n+=1
        if d['disposition']=='eligible':
            ne+=1
            if d['force_missing_stance_samples']>0: aff.append((d['step_id'],d['force_missing_stance_samples'],d['stance_samples']))
print(n,ne,len(aff)); 
frac=sorted(((m/s) for _,m,s in aff),reverse=True)[:10]; print(frac)
print(Counter(a[0].split('/')[0] for a in aff if a[1]/a[2]>0.2))
print([a for a in aff if a[1]/a[2]>0.2][:20])
