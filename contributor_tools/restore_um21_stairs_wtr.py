"""Fresh independent UM21 stairs or Wtr conversion/readback pairs; no old queues."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'converted_datasets/reconversion_v2'
SOURCE=ROOT/'contributor_tools/conversion_scripts/Umich_2021/Streaming.mat'


def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def unique(records,kind):
    keys=[(r['subject'],r['condition']) if kind=='stairs' else r['subject'] for r in records]
    if len(set(keys))!=len(keys):raise ValueError('Duplicate recording identity')
    return dict(zip(keys,records))


def prepare(kind,folder):
    queue=BASE/('um21_stair_serial_queue_20261021' if kind=='stairs' else 'um21_wtr_serial_queue_20261021')/'plan.json'
    old=json.loads(queue.read_text());producer,auditor=old['jobs']
    bindings={**producer['code_sha256'],**auditor['code_sha256']}
    for path,sha in bindings.items():
        if digest(path)!=sha:raise ValueError('Original scientific code changed')
    prior=BASE/('um21_stair_annotation_review_v2_20261021' if kind=='stairs' else 'um21_wtr_pilot_20261021')
    summary=prior/'conversion_summary.json';readback=prior/'source_comparison.json';r=json.loads(summary.read_text());a=json.loads(readback.read_text())
    if a['summary_sha256']!=digest(summary) or a['scientific_approval'] is not False:raise ValueError('Prior source scope receipt mismatch')
    if kind=='stairs':
        records=r['recordings'];unique(records,kind)
        if len(records)!=403 or sum(len(x['windows']) for x in records)!=2700 or (a['source_recordings'],a['annotated_observations'],a['explicitly_empty_annotations'])!=(403,2700,16):raise ValueError('Full stair annotation scope changed')
        scope={'recordings':[{k:x[k] for k in ('subject','condition','windows','unannotated')} for x in records],'observations':2700,'source_recordings':403,'empty_annotations':16}
    else:
        subjects=r['source_subjects']
        if subjects!=[f'AB{i:02}' for i in range(1,10)]:raise ValueError('Full nine-subject Wtr scope changed')
        scope={'subjects':subjects,'observation_count':'Derived from all original bilateral source heel-strike pairs, independently checked per subject.'}
    for path in (queue,summary,readback,Path(__file__),ROOT/'contributor_tools/preserve_mblue_planar_estimates.py'):
        bindings[str(path.resolve())]=digest(path)
    baseline=json.loads((BASE/'um21_tread_corrected_20261020/conversion_summary.json').read_text());source=baseline['source']
    if source['sha256']!=r['source_sha256'] or source['path']!=str(SOURCE):raise ValueError('Source identity differs')
    stat=SOURCE.stat()
    if (stat.st_size,stat.st_mtime_ns)!=(source['bytes'],source['mtime_ns']):raise ValueError('Source stat changed')
    output=folder/'outputs';commands=[]
    for job in (producer,auditor):
        cmd=[str(output) if x==job['output'] else x for x in job['command']]
        commands.append(cmd)
    return {'status':'prepared_not_executed','scientific_approval':False,'kind':kind,'bindings':bindings,'source':source,'producer_code_paths':sorted(r['code_sha256']),'scope':scope,'output_root':str(output),'commands':commands,'probe_path':str(ROOT/auditor['command'][1]),'limits':{'address_space_mib':768,'workers':1,'stage_timeout_seconds':21600,'windows_startup_mib':2816,'windows_runtime_mib':2048,'linux_startup_mib':3584,'linux_runtime_mib':2048},'limitations':['Source signals/events only, not anatomical approval; canonical ankle/kinetic frames unresolved.','Wtr canonical task remains missing; no invented walking/running transition timing.','Stair unannotated and explicitly empty annotations remain accounted; partial historical pilots preserved.','Original metadata/serial parent queues remain held and unmodified.']}


def gate(summary,audit,plan,summary_sha):
    kind=plan['kind']
    if summary['scientific_approval'] is not False or audit['scientific_approval'] is not False or summary['source_sha256']!=plan['source']['sha256'] or audit['summary_sha256']!=summary_sha or audit['probe_sha256']!=plan['bindings'][plan['probe_path']]:raise ValueError('Full source/probe provenance differs')
    if sorted(summary['code_sha256'])!=plan['producer_code_paths']:raise ValueError('Producer code coverage incomplete')
    for name,sha in summary['code_sha256'].items():
        if plan['bindings'].get(str(ROOT/name))!=sha:raise ValueError('Actual producer code differs')
    if kind=='stairs':
        if summary['status']!='all_annotated_stair_cycles_exported_unreviewed' or audit['status']!='all_annotated_stair_cycles_source_checked_unreviewed':raise ValueError('Stair pair incomplete')
        actual=unique(summary['recordings'],kind);expected=unique(plan['scope']['recordings'],kind)
        if actual.keys()!=expected.keys():raise ValueError('Stair identity coverage differs')
        for key,r in actual.items():
            if r['windows']!=expected[key]['windows'] or r['unannotated']!=expected[key]['unannotated'] or r['exported_rows']!=150*len(r['windows']):raise ValueError('Stair annotations/exclusions changed')
        if (audit['source_recordings'],audit['annotated_observations'],audit['explicitly_empty_annotations'],audit['exported_observations_checked'])!=(403,2700,16,2700) or audit['source_component_values_checked']<=0 or not math.isfinite(audit['max_component_error']):raise ValueError('Full stair source readback incomplete')
        return 2700,list(actual.values())
    if summary['status']!='all_wtr_source_cycles_preserved_unreviewed' or audit['status']!='all_wtr_source_cycles_checked_unreviewed' or summary['format']!='source_labeled_cycle_companion':raise ValueError('Wtr pair incomplete')
    actual=unique(summary['records'],kind);checked=unique(audit['records'],kind);expected=set(plan['scope']['subjects'])
    if set(summary['source_subjects'])!=expected or len(summary['source_subjects'])!=9 or actual.keys()!=expected or checked.keys()!=expected:raise ValueError('Nine-subject Wtr coverage incomplete')
    for subject,r in actual.items():
        c=checked[subject]
        if c['source_cycles']!=r['observations'] or r['rows']!=150*r['observations'] or sum(r['protocol_counts'].values())!=r['observations'] or c['finite_component_values_checked']<=0 or not math.isfinite(c['maximum_error']):raise ValueError('Wtr cycles/source readback incomplete')
    return sum(r['observations'] for r in actual.values()),list(actual.values())


def verify(plan):
    for path,sha in plan['bindings'].items():
        if digest(path)!=sha:raise ValueError('Bound code/receipt changed')


def run(planpath):
    plan=json.loads(planpath.read_text());sha=digest(planpath);verify(plan);folder=planpath.parent;out=Path(plan['output_root'])
    if out.exists() or (folder/'completion.json').exists():raise FileExistsError('Fresh output required')
    for index,command in enumerate(plan['commands']):
        verify(plan)
        if digest(planpath)!=sha:raise ValueError('Plan changed')
        with (folder/f'{index}.log').open('x') as log:subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=21600)
    summarypath=out/'conversion_summary.json';auditpath=out/'source_comparison.json';summary=json.loads(summarypath.read_text());audit=json.loads(auditpath.read_text())
    observations,records=gate(summary,audit,plan,digest(summarypath));artifacts={str(p):digest(p) for p in (summarypath,auditpath)}
    for record in records:
        prefix=Path(record['subject'])/record['condition'] if plan['kind']=='stairs' else Path(record['subject'])
        expected_names={'phase.parquet','source_columns.json'} if plan['kind']=='stairs' else {'source_cycles.parquet','source_columns.json','cycle_ledger.jsonl'}
        if set(record['outputs'])!={str(prefix/name) for name in expected_names}:raise ValueError('Output field/ledger coverage differs')
        for relative,expected in record['outputs'].items():
            path=(out/relative).resolve()
            if not path.is_relative_to(out) or digest(path)!=expected:raise ValueError('Persisted output identity changed')
            artifacts[str(path)]=expected
    if digest(SOURCE)!=plan['source']['sha256']:raise ValueError('Source changed after complete readback')
    verify(plan)
    result={'status':f'all_{plan["kind"]}_source_scope_checked_unreviewed','scientific_approval':False,'plan_sha256':sha,'source_sha256':plan['source']['sha256'],'recordings':len(records),'observations':observations,'artifacts':artifacts,'bindings':plan['bindings'],'limitations':plan['limitations']}
    with (folder/'completion.json').open('x') as f:json.dump(result,f,indent=2)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--kind',choices=['stairs','wtr'],required=True);p.add_argument('--output-root',type=Path,required=True);p.add_argument('--run',action='store_true');a=p.parse_args();out=a.output_root.resolve()
    if not out.is_relative_to(BASE):raise ValueError('Isolated output required')
    if a.run:run(out/'plan.json');return
    plan=prepare(a.kind,out);out.mkdir(parents=True,exist_ok=False);(out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');print(plan['kind'])
if __name__=='__main__':main()
