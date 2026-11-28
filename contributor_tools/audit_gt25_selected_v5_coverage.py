"""Independent identity/status/receipt accounting; stdlib only, no numerical reads."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def key(r):return r['subject'],r['recording']


def check(folder):
    folder=Path(folder);planpath=folder/'plan.json';plan=json.loads(planpath.read_text());state=json.loads((folder/'batch_status.json').read_text())
    if state['plan_sha256']!=digest(planpath) or state['scientific_approval'] is not False:raise ValueError('Plan/approval mismatch')
    expected={key(r):r for r in plan['records']};actual={key(r):r for r in state['records']}
    if len(expected)!=len(plan['records']) or len(actual)!=len(state['records']) or expected.keys()!=actual.keys():raise ValueError('Recording identity coverage differs')
    counts={'regular':0,'streaming':0,'unresolved':0};rows=0
    for identity,r in actual.items():
        if r['route']!=expected[identity]['route'] or r['output']!=expected[identity]['output']:raise ValueError('Admission changed')
        if r['route']=='excluded_unresolved_observation_semantics':
            if r['status']!='excluded_unresolved_observation_semantics' or r['canonical_task'] is not None:raise ValueError('Invalid unresolved disposition')
            counts['unresolved']+=1;continue
        if r['status']!='source_readback_checked_unreviewed':raise ValueError('Missing source audit')
        for path,sha in r['receipts'].items():
            if digest(path)!=sha:raise ValueError('Changed receipt')
        audits=[Path(p) for p in r['receipts'] if Path(p).name=='source_comparison.json']
        if len(audits)!=1:raise ValueError('Exactly one independent audit required')
        a=json.loads(audits[0].read_text())
        if a['rows_checked']!=r['rows'] or a['observations_checked']*150!=r['rows']:raise ValueError('Incomplete observation coverage')
        regular=r['route']=='regular_selected_worker';counts['regular' if regular else 'streaming']+=1
        status='regular_raw_source_events_and_92_features_checked_unreviewed' if regular else 'independent_raw_transfer_events_and_values_checked_unreviewed'
        if a['status']!=status or a['numeric_features_checked']!=(92 if r['rows'] else 0):raise ValueError('Wrong independent audit scope')
        if regular and (not a['whole_selected_source_clocks_checked'] or a['scientific_blockers'] or (not r['rows'] and not a['no_accepted_observations_independently_checked'])):raise ValueError('Source clock/event gate incomplete')
        for p,sha in a['bindings'].items():
            if digest(p)!=sha:raise ValueError('Source/output audit binding changed')
        rows+=r['rows']
    if plan['kind']=='full':
        inventory=[p for p in plan['bindings'] if p.endswith('/gt25_full_20261021/inventory.json')]
        if len(inventory)!=1 or {key(r) for r in json.loads(Path(inventory[0]).read_text())}!=expected.keys():raise ValueError('Original full inventory omitted')
        if counts!={'regular':450,'streaming':34,'unresolved':192} or state['status']!='all_676_accounted_484_source_checked_192_unresolved':raise ValueError('Full disposition counts incomplete')
    elif counts!={'regular':3,'streaming':1,'unresolved':0} or state['status']!='four_family_v5_pilot_source_checked_unreviewed':raise ValueError('Pilot disposition incomplete')
    for p,sha in plan['bindings'].items():
        if digest(p)!=sha:raise ValueError('Plan code/input binding changed')
    return {'status':'independent_identity_and_source_receipt_coverage_checked_unreviewed','scientific_approval':False,'plan_sha256':digest(planpath),'recordings':len(actual),'counts':counts,'rows_source_checked':rows,'scientific_full_scope_complete':False,'limitations':plan['limitations']}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',type=Path,required=True);a=p.parse_args();r=check(a.folder)
    with (a.folder/'independent_coverage.json').open('x') as f:json.dump(r,f,indent=2)
if __name__=='__main__':main()
