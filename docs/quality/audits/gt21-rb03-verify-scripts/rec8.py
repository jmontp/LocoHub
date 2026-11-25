import json,sys,random,collections
sys.path.insert(0,'/tmp/vrb'); import rulea
R='/mnt/s/workspace/locomotion-data-standardization/converted_datasets/reconversion_v2/'
EPS=1e-6
def seq(w,t0,t1): return [x for x in w if x['end_header']>=t0-EPS and x['start_header']<=t1+EPS]
def mine(mode,m,t0,t1):
    if mode=='treadmill':
        vals={x['value'] for x in seq(m['speed_runs'],t0,t1)}; return ('discard' if len(vals)>2 else 'treadmill'),len(vals)
    L=[x['label'] for x in seq(m['label_windows'],t0,t1)]
    return rulea.classify(mode,L,m['leading_leg_start'],m['leading_leg_stop'],m['trans_leg_ascent'],m['trans_leg_descent'],''.join(m['turn'])),L
sample=[tuple(x) for x in json.load(open('/tmp/vrb/sample.json'))]
rng=random.Random(20261209+17)
ab17=[json.loads(l) for l in open(R+'gt21_rb_segment_batch_AB17_20261125/ledger.jsonl')]
ab17=[(d['subject'],d['mode'],d['recording']) for d in ab17 if d['status']=='segmented' and d['mode'] in('stair','ramp','levelground')]
sample+= [('AB06','stair','stair_1_l_01_02'), rng.choice(ab17)]
print(sample[-1])
for sub,mode,rec in sample:
    meta=None
    for l in open(R+f'gt21_rb03_authors_fields_20261125/{sub}/labels_{sub}.jsonl'):
        d=json.loads(l)
        if d['mode']==mode and d['recording']==rec: meta=d;break
    n=collections.Counter();bad=0
    for l in open(R+f'gt21_rb_segment_batch_{sub}_20261125/steps.jsonl'):
        s=json.loads(l)
        if s['mode']!=mode or s['recording']!=rec: continue
        c,x=mine(mode,meta,s['start_s'],s['end_s'])
        el=c not in('discard','NOTFOUND')
        if el!=(s['disposition']=='eligible'): bad+=1
        if mode!='treadmill' and el and c!=s['authors_class']: bad+=1
        if c=='NOTFOUND' and not (s['leg']=='left' and 'case_not_found' in s['reason'] and s['rule_origin']=='authors_rule_extended_to_left_leg'): bad+=1
        n[(s['leg'],'eligible' if el else ('notfound' if c=='NOTFOUND' else 'discard'),s['rule_origin'][-8:])]+=1
    print(sub,mode,rec,'steps',sum(n.values()),'mismatches',bad,dict(n))
