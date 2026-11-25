import json,glob,sys,collections,os
sys.path.insert(0,'/tmp/vrb')
import rulea
R='/mnt/s/workspace/locomotion-data-standardization/converted_datasets/reconversion_v2/'
EPS=1e-6
HALF=len(sys.argv)>1 and sys.argv[1]=='half'
def seq(wins,t0,t1):
    out=[]
    for w in wins:
        a,b=w['start_header'],w['end_header']
        if HALF:
            if b>=t0-EPS and a<t1-EPS: out.append(w)
        elif b>=t0-EPS and a<=t1+EPS: out.append(w)
    return out
def mine(mode,meta,t0,t1):
    if mode=='treadmill':
        runs=[w for w in seq(meta['speed_runs'],t0,t1)]
        n=len({w['value'] for w in runs})
        return 'discard' if n>2 else 'treadmill'
    L=[w['label'] for w in seq(meta['label_windows'],t0,t1)]
    if not L: return 'NOLABELS'
    return rulea.classify(mode,L,meta['leading_leg_start'],meta['leading_leg_stop'],meta['trans_leg_ascent'],meta['trans_leg_descent'],''.join(meta['turn']) if isinstance(meta['turn'],list) else meta['turn'])
agree=collections.Counter();dis=[];tab=collections.Counter();nf=collections.Counter();ids_out=[]
sample=set(tuple(x) for x in json.load(open('/tmp/vrb/sample.json')))
for sub in sorted(os.listdir(R+'gt21_rb03_authors_fields_20261125')):
    meta={}
    for l in open(R+f'gt21_rb03_authors_fields_20261125/{sub}/labels_{sub}.jsonl'):
        d=json.loads(l); meta[(d['mode'],d['recording'])]=d
    for l in open(R+f'gt21_rb_segment_batch_{sub}_20261125/steps.jsonl'):
        s=json.loads(l); m=meta[(s['mode'],s['recording'])]
        c=mine(s['mode'],m,s['start_s'],s['end_s'])
        elig_mine = c not in ('discard','NOTFOUND','NOLABELS')
        recnc = s['reason'] and 'not_converted' in s['reason']
        ours = s['disposition']=='eligible'
        key=(s['mode'],s['leg'])
        if recnc: tab[(s['mode'],'recording_not_converted_skipped')]+=1; continue
        ok = (elig_mine==ours)
        # reason class check
        if not ok: dis.append((s['step_id'],c,s['authors_class'],s['disposition'],s['reason']))
        else:
            if c=='NOTFOUND': assert s['reason'] and 'case_not_found' in s['reason'],(s['step_id'],s['reason'])
            if s['reason'] and 'case_not_found' in s['reason']: assert c=='NOTFOUND'; nf[(s['mode'],s['leg'],s['rule_origin'])]+=1
            if s['mode']!='treadmill' and ours and s['authors_class']!=c: dis.append(('classname',s['step_id'],c,s['authors_class']))
            if c=='NOLABELS': dis.append(('nolabels',s['step_id']))
        tab[(s['mode'],s['leg'],'eligible' if elig_mine else 'excluded','agree' if ok else 'DISAGREE')]+=1
print('variant','half' if HALF else 'closed')
for k,v in sorted(tab.items()): print(k,v)
print('case_not_found by mode/leg/origin',dict(nf))
print('disagreements',len(dis),dis[:15])
