import json,random,glob
R='/mnt/s/workspace/locomotion-data-standardization/converted_datasets/reconversion_v2/'
rows=[]
for f in sorted(glob.glob(R+'gt21_rb_segment_batch_AB*_20261125/ledger.jsonl')):
    for l in open(f):
        d=json.loads(l)
        if d['status']=='segmented': rows.append((d['subject'],d['mode'],d['recording']))
rows.sort()
print(len(rows))
rng=random.Random(20261209)
pick=[]
for m in ['levelground','ramp','stair','treadmill']:
    pool=[r for r in rows if r[1]==m]; pick.append(rng.choice(pool))
rest=[r for r in rows if r not in pick]
pick+=rng.sample(rest,2)
for p in pick: print(p)
json.dump(pick,open('/tmp/vrb/sample.json','w'))
