import json,collections,glob
R='/mnt/s/workspace/locomotion-data-standardization/converted_datasets/reconversion_v2/'
EPS=1e-6
sub,rec='AB27','Treadmill_03_01'
for l in open(R+f'gt21_rb03_authors_fields_20261125/{sub}/labels_{sub}.jsonl'):
    d=json.loads(l)
    if d['recording']==rec: m=d;break
runs=m['speed_runs']; print('runs',len(runs),'values',sorted({r['value'] for r in runs})[-5:],'trial',m['trial_start'],m['trial_end'])
dist=collections.Counter();bad=0;ex=[]
for l in open(R+f'gt21_rb_segment_batch_{sub}_20261125/steps.jsonl'):
    s=json.loads(l)
    if s['recording']!=rec: continue
    vals={r['value'] for r in runs if r['end_header']>=s['start_s']-EPS and r['start_header']<=s['end_s']+EPS}
    n=len(vals); dist[n]+=1
    exp='excluded' if n>2 else 'eligible'
    if exp!=s['disposition']: bad+=1
    if n>2 and len(ex)<3: ex.append((s['step_id'],n,s['start_s'],s['reason']))
    if n==2 and len(ex)<6: ex.append(('n2',s['step_id'],sorted(vals),s['disposition']))
print('distinct-count histogram',dict(dist),'bad',bad); print(ex)
# global: rule_origin by leg
c=collections.Counter()
for f in glob.glob(R+'gt21_rb_segment_batch_AB*_20261125/steps.jsonl'):
    for l in open(f):
        s=json.loads(l); c[(s['leg'],s['rule_origin'])]+=1
print(c)
