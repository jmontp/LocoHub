"""Build a static source-availability table from the pinned walking inventory.

Metadata only. No scientific arrays, downloads, conversion or readiness promotion.
"""
import argparse
from collections import Counter
import hashlib
import html
import json
from pathlib import Path

PLAN_SHA='ee8776499bb5cd0d66c21eedcb3cce2f24545a2757ee13edebabcde8c0ae599a'
CONDITIONS=('OS','OC','OF','T01','T02','T03','T04','T05','T06','T07','T08')
COUNTS={'OS':42,'OC':42,'OF':42,**{f'T0{i}':51 for i in range(1,7)},'T07':40,'T08':36}

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def inventory(plan):
    rows={};seen=set();counts=Counter()
    for pair in plan['pairs']:
        subject,condition=pair['subject'],pair['condition']
        if subject not in {f'FU18_{i:02d}' for i in range(1,52)} or condition not in CONDITIONS or (subject,condition) in seen:raise ValueError('Duplicate or invalid source pair')
        seen.add((subject,condition));counts[condition]+=1
        stem='WBDS'+subject[-2:]+'walk'+condition
        if pair['stem']!=stem or pair['environment']!=('overground' if condition.startswith('O') else 'treadmill') or pair['age_group'] not in ('Young','Older'):raise ValueError('Source identity differs')
        if set(pair['members'])!={'ang','knt'}:raise ValueError('Incomplete source pair')
        for kind,member in pair['members'].items():
            if Path(member['name']).name!=stem+kind+'.txt':raise ValueError('Source member identity differs')
        row=rows.setdefault(subject,{'subject':subject,'age_group':pair['age_group'],'conditions':[]})
        if row['age_group']!=pair['age_group']:raise ValueError('Participant age group differs')
        row['conditions'].append(condition)
    if len(seen)!=508 or len(rows)!=51 or dict(counts)!=COUNTS or Counter(r['age_group'] for r in rows.values())!={'Young':24,'Older':27}:raise ValueError('Published full cohort differs')
    return [rows[key] for key in sorted(rows)]

def render(rows):
    body=[]
    for row in rows:
        cells=''.join('<td title="Published angle and kinetic tables">Yes</td>' if c in row['conditions'] else '<td class="absent" title="Not present in this source version">—</td>' for c in CONDITIONS)
        body.append('<tr><th scope="row">'+html.escape(row['subject'])+'</th><td>'+html.escape(row['age_group'])+'</td>'+cells+'</tr>')
    headers=''.join('<th scope="col">'+c+'</th>' for c in CONDITIONS)
    return '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fukuchi walking: available conditions</title><link rel="stylesheet" href="../../stylesheets/site.css"><style>.coverage-wrap{overflow:auto;max-height:70vh;border:1px solid #cbd5e1}.coverage{border-collapse:collapse;width:100%;font-size:.9rem}.coverage th,.coverage td{padding:.45rem .7rem;border-bottom:1px solid #e2e8f0;text-align:center;white-space:nowrap}.coverage th:first-child{text-align:left}.coverage thead th{position:sticky;top:0;background:#f1f5f9;color:#334155}.coverage .absent{color:#64748b;background:#f8fafc}.filters{display:flex;flex-wrap:wrap;gap:1rem;margin:1rem 0}.filters label{display:grid;gap:.25rem}input,select{padding:.4rem;font:inherit}caption{text-align:left;padding:.7rem}#visible{margin:.5rem 0}</style></head><body><header class="site-header"><div class="header-inner"><a class="wordmark" href="../../index.html">LocoHub</a></div></header><main id="main" class="page-content"><nav><a href="index.html">Fukuchi walking</a> · <a href="pilot-review.html">Pilot results</a> · <a href="full-admission.html">Remaining checks</a></nav><h1>Which walking conditions are in the source?</h1><p>51 participants · 508 participant-condition averages · source version 6</p><p><strong>This table shows published source files, not completed conversions.</strong> “Yes” means both angle and kinetic tables exist. A dash means that condition is absent. The full conversion is still pending review.</p><div class="filters"><label>Participant<input id="participant" type="search" placeholder="For example, FU18_43"></label><label>Age group<select id="group"><option value="">All participants</option><option>Young</option><option>Older</option></select></label><label>Coverage<select id="missing"><option value="">All participants</option><option value="missing">Has an absent condition</option></select></label></div><p id="visible" aria-live="polite">51 participants shown</p><div class="coverage-wrap" tabindex="0" aria-label="Source condition availability, scroll horizontally for all conditions"><table class="coverage"><caption>OS, OC and OF are overground conditions. T01–T08 are treadmill condition codes; individual speeds come from source metadata.</caption><thead><tr><th scope="col">Participant</th><th scope="col">Age group</th>'''+headers+'''</tr></thead><tbody>'''+''.join(body)+'''</tbody></table></div><p>Each file pair contains participant averages, with separate leg references. It does not provide individual strides, cycle durations or within-person standard deviations. Left-leg anatomical directions remain unverified; original source components are retained.</p><p>The paper describes 42 participants; the later source version includes 51. Nine later participants have treadmill-only files. Published T07 and T08 coverage is also incomplete. Missing conditions will not be filled in.</p><p><a href="https://doi.org/10.7717/peerj.4640">Fukuchi, Fukuchi and Duarte (2018)</a> · <a href="https://doi.org/10.6084/m9.figshare.5722711.v6">Version 6 source data</a> · <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a></p><script>
const controls=['participant','group','missing'].map(id=>document.getElementById(id));const rows=[...document.querySelectorAll('tbody tr')];
function filter(){const [search,group,missing]=controls.map(el=>el.value);let count=0;for(const row of rows){const cells=row.cells;const match=cells[0].textContent.toLowerCase().includes(search.toLowerCase())&&(!group||cells[1].textContent===group)&&(!missing||row.querySelector('.absent'));row.hidden=!match;if(match)count++;}document.getElementById('visible').textContent=count+' participants shown';}
controls.forEach(el=>el.addEventListener('input',filter));
</script></main></body></html>'''

def build(plan_path,output):
    plan_path=Path(plan_path);output=Path(output)
    if output.exists():raise FileExistsError('Preserve existing coverage document')
    if plan_path.stat().st_size>1024**2 or digest(plan_path)!=PLAN_SHA:raise ValueError('Pinned source plan differs')
    plan=json.loads(plan_path.read_text())
    for path,h in {**plan['input_sha256'],**plan['code_sha256']}.items():
        if digest(path)!=h:raise ValueError('Bound source inventory/code differs')
    rows=inventory(plan);page=render(rows)
    with output.open('x') as f:f.write(page)
    return {'status':'source_inventory_only_not_conversion_completion','participants':len(rows),'pairs':sum(len(r['conditions']) for r in rows),'plan_sha256':PLAN_SHA,'output_sha256':digest(output)}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.plan,a.output)))
