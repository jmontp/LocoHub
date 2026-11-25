import json,collections
R='/mnt/s/workspace/locomotion-data-standardization/converted_datasets/reconversion_v2/'
cover=json.load(open(R+'gt21_event_eligibility_review_20261021/source_coverage.json'))['recordings']
old={(c['record']['subject'],c['record']['mode'],c['record']['recording'].replace('.mat','')):c['source_pairs'] for c in cover}
print(len(old),collections.Counter(k[1] for k in old))
tab=collections.Counter(); oldr=collections.Counter(); dis=[]
by_sub=collections.defaultdict(list)
for k in old: by_sub[k[0]].append(k)
tot={'steps':0}
for sub,keys in by_sub.items():
    ks=set(keys)
    for l in open(R+f'gt21_rb_segment_batch_{sub}_20261125/steps.jsonl'):
        s=json.loads(l); k=(sub,s['mode'],s['recording'])
        if k not in ks or s['mode']!='treadmill': continue
        pairs={(p['side'],round(p['start_s'],3),round(p['end_s'],3)):p['reason'] for p in old[k]}
        r=pairs.get((s['leg'],round(s['start_s'],3),round(s['end_s'],3)))
        oi = r!='outside_complete_eligible_task_window'
        tab[(k[1:], s['disposition'],'old_in' if oi else 'old_out')]+=1
        oldr[r]+=1
for k,v in sorted(tab.items(),key=str): print(k,v)
print(oldr)
