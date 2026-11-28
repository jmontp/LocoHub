import json,sys,os,collections
sys.path.insert(0,'/tmp/vrb'); import rulea
R='/mnt/s/workspace/locomotion-data-standardization/converted_datasets/reconversion_v2/'
EPS=1e-6
def seq(w,t0,t1): return [x for x in w if x['end_header']>=t0-EPS and x['start_header']<=t1+EPS]
def mine(mode,m,t0,t1):
    if mode=='treadmill': return 'discard' if len({x['value'] for x in seq(m['speed_runs'],t0,t1)})>2 else 'treadmill'
    L=[x['label'] for x in seq(m['label_windows'],t0,t1)]
    if not L: return 'NOLABELS'
    return rulea.classify(mode,L,m['leading_leg_start'],m['leading_leg_stop'],m['trans_leg_ascent'],m['trans_leg_descent'],''.join(m['turn']))
tab=collections.Counter(); mism=[]; other=collections.Counter(); notconv=collections.Counter()
for sub in sorted(os.listdir(R+'gt21_rb03_authors_fields_20261125')):
    meta={}
    for l in open(R+f'gt21_rb03_authors_fields_20261125/{sub}/labels_{sub}.jsonl'):
        d=json.loads(l); meta[(d['mode'],d['recording'])]=d
    for l in open(R+f'gt21_rb_segment_batch_{sub}_20261125/authors_intervals.jsonl'):
        a=json.loads(l)
        other[(a['mode'],a['kind'],a['status'])]+=1
        if a['kind']!='interior' or a['status']!='matched': continue
        c=mine(a['mode'],meta[(a['mode'],a['recording'])],a['start_s'],a['end_s'])
        kept=c not in('discard','NOTFOUND','NOLABELS')
        if c in('NOTFOUND','NOLABELS'): mism.append(('nf',a['our_step_id'],c))
        ours=a['our_disposition']
        tab[(a['mode'],'authors_kept' if kept else 'authors_dropped',ours,a.get('our_reason') if ours!='eligible' else '')]+=1
        if kept != (a['authors_class'] not in ('discard',None)) and a['mode']!='treadmill': mism.append(('cls',a['our_step_id'],c,a['authors_class']))
        if a['mode']!='treadmill' and c!=a['authors_class'] and kept: mism.append(('name',a['our_step_id'],c,a['authors_class']))
for k,v in sorted(tab.items(),key=str): print(k,v)
print('mism',len(mism),mism[:10])
print(sorted(other.items()))
print('--- partial/extra intervals by authors class kept/dropped (mine)')
pt=collections.Counter(); rec124=collections.Counter()
for sub in sorted(os.listdir(R+'gt21_rb03_authors_fields_20261125')):
    meta={}
    for l in open(R+f'gt21_rb03_authors_fields_20261125/{sub}/labels_{sub}.jsonl'):
        d=json.loads(l); meta[(d['mode'],d['recording'])]=d
    for l in open(R+f'gt21_rb_segment_batch_{sub}_20261125/authors_intervals.jsonl'):
        a=json.loads(l)
        if a['kind']=='interior' and a['our_disposition']=='excluded' and a.get('our_reason','').startswith('recording_not_conv'): rec124[(sub,a['recording'])]+=1
        if a['kind']=='interior': continue
        c=mine(a['mode'],meta[(a['mode'],a['recording'])],a['start_s'],a['end_s'])
        pt[(a['mode'],a['kind'],a['status'],'kept' if c not in('discard','NOTFOUND','NOLABELS') else c)]+=1
for k,v in sorted(pt.items()): print(k,v)
print(rec124)
