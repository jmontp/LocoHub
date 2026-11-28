import json,glob,hashlib,os,sys
os.chdir('/mnt/s/workspace/locomotion-data-standardization')
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()
groups={'authors':sorted(glob.glob('docs/quality/audits/gt21-rb03-authors-fields-AB*-launcher-receipt.json')),
 'pilot':['docs/quality/audits/gt21-rb03-pilot-ruleA-launcher-receipt.json'],
 'batch':sorted(glob.glob('docs/quality/audits/gt21-rb03-ruleA-batch-AB*-launcher-receipt.json'))}
cur={}
for g,fs in groups.items():
    print(g,len(fs))
    bad=[]; binds={}
    for f in fs:
        r=json.load(open(f))
        probs=[]
        if r.get('status')!='completed' or r.get('exit_code')!=0 or not r.get('clean_success'): probs.append(('status',r.get('status'),r.get('exit_code'),r.get('clean_success')))
        if r.get('launcher_errors') or r.get('finalisation_errors') or r.get('orphans_at_leader_exit') or r.get('expected_outputs_missing'): probs.append('errs')
        if not all(r['checks'].values()): probs.append({k:v for k,v in r['checks'].items() if not v})
        for ph in ('bindings_before','bindings_after'):
            for p,b in r[ph].items():
                if not b['matches'] or b['expected']!=b['actual']: probs.append((ph,p))
        for p,h in r['spec']['bindings'].items():
            binds.setdefault(p,set()).add(h)
            if p not in cur: cur[p]=sha(p)
        if probs: bad.append((f,probs))
        else: pass
    print(' problems:',bad)
    for p,hs in binds.items():
        print('  ',p[-60:],len(hs),'distinct;', 'current==bound' if hs=={cur[p]} else 'DIFF cur=%s'%cur[p][:8], [h[:8] for h in hs])
