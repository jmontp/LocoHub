"""Independent JSON/hash accounting of every GT25 planned recording.

This checks recording coverage and receipts, not numerical or anatomical validity.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def digest(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda:handle.read(1024**2),b''):value.update(chunk)
    return value.hexdigest()


def reconcile(plan,status):
    def indexed(records):
        result={}
        for record in records:
            key=(record['subject'],record['recording'])
            if key in result:raise ValueError('Duplicate coverage identity')
            result[key]=record
        return result
    expected,actual=indexed(plan['records']),indexed(status['records'])
    if set(expected)!=set(actual):raise ValueError('Missing/extra recording identity')
    for key,record in actual.items():
        origin=expected[key]
        for field in ('route','source_files','canonical_task','output'):
            if record[field]!=origin[field]:raise ValueError('Changed planned disposition/source identity')
        allowed={'excluded_unresolved_observation_semantics':{'excluded_unresolved_observation_semantics'},'regular_selected_worker':{'converted_unreviewed','no_accepted_observations'},'streaming_transfer_worker':{'transfer_source_readback_unreviewed'}}[record['route']]
        if record['status'] not in allowed:raise ValueError('Nonterminal or wrong route disposition')
    return actual


def check(folder):
    folder=Path(folder);planpath=folder/'plan.json';plan=json.loads(planpath.read_text());status=json.loads((folder/'batch_status.json').read_text())
    if status['plan_sha256']!=digest(planpath) or status['status']!='conversions_accounted_pending_regular_source_audit':raise ValueError('Batch is not terminal complete accounting')
    records=reconcile(plan,status);rows=0
    required={(r['subject'],r['recording']) for r in records.values() if r['route']=='regular_selected_worker'}
    backlog=status.get('regular_independent_audit_backlog',[])
    if len(backlog)!=len(required) or {(r['subject'],r['recording']) for r in backlog}!=required:raise ValueError('Regular independent audit backlog incomplete')
    for record in records.values():
        if record['route'].startswith('excluded'):continue
        if digest(record['manifest'])!=record['manifest_sha256']:raise ValueError('Manifest changed')
        manifest=json.loads(Path(record['manifest']).read_text())
        if manifest['rows']!=record['rows'] or record['rows']%150:raise ValueError('Row counts differ')
        if record['route']=='streaming_transfer_worker':
            if digest(record['audit'])!=record['audit_sha256']:raise ValueError('Source readback changed')
            if digest(record['segment_disclosure'])!=record['segment_disclosure_sha256']:raise ValueError('Segment disclosure changed')
            disclosure=json.loads(Path(record['segment_disclosure']).read_text())
            if disclosure['status']!='transfer_segment_reference_disclosed_exact_preservation_unreviewed' or disclosure['rows']!=record['rows'] or digest(disclosure['source'])!=disclosure['source_sha256'] or digest(disclosure['output'])!=disclosure['output_sha256']:raise ValueError('Segment metadata preservation failed')
        else:
            for output in manifest['outputs']:
                if Path(output['name']).name!=output['name'] or digest(Path(record['manifest']).parent/output['name'])!=output['sha256']:raise ValueError('Output changed')
        rows+=record['rows']
    return {'status':'all_selected_recording_identities_accounted_unreviewed','scientific_approval':False,'records':len(records),'counts':dict(Counter(r['status'] for r in records.values())),'rows':rows,'plan_sha256':digest(planpath),'batch_status_sha256':digest(folder/'batch_status.json'),'limitations':plan['limitations'],'numerical_source_audit_for_regular_records':{'status':'pending','recordings':len(required)},'scientific_full_scope_complete':False}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();report=check(a.output_root)
    with (a.output_root/'independent_coverage.json').open('x') as handle:json.dump(report,handle,indent=2)
if __name__=='__main__':main()
