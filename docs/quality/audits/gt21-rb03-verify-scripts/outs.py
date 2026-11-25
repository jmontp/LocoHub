import json,glob,hashlib,os,datetime
os.chdir('/mnt/s/workspace/locomotion-data-standardization')
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()
bad=0;n=0;times=[]
for f in sorted(glob.glob('docs/quality/audits/gt21-rb03-ruleA-batch-AB*-launcher-receipt.json')):
    r=json.load(open(f)); root=r['spec']['output_root']
    times.append((r['checked_at_utc'],f[-35:-27]))
    for o in r['outputs']:
        p=os.path.join(root,o['path']); n+=1
        if not os.path.exists(p) or sha(p)!=o['sha256']: bad+=1; print('BAD',p)
p=json.load(open('docs/quality/audits/gt21-rb03-pilot-ruleA-launcher-receipt.json'))
print('files',n,'bad',bad,'pilot',p['checked_at_utc'],p['finished_at_utc'],'exit',p['exit_code'],'first batch',min(times),'last',max(times))
print('peaks MiB',max(json.load(open(f))['peak_rss_kib_largest_process'] for f in glob.glob('docs/quality/audits/gt21-rb03-ruleA-batch-AB*-launcher-receipt.json'))/1024)
