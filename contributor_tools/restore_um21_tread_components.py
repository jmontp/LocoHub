"""Prepare an independent serial UM21 treadmill component restoration recipe.

Preparation reads small receipts/code only. Execution alone hashes source/output
files and calls the unchanged bounded producer with its independent readback.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'converted_datasets/reconversion_v2'
BASELINE=BASE/'um21_tread_corrected_20261020'
READBACK=BASE/'um21_tread_full_readback_20261021/source_comparison.json'
PROBE=ROOT/'contributor_tools/audit_probes/2026_10_20/check_um21_tread_source.py'


def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def unique(records):
    result={(r['subject'],r['condition']):r for r in records}
    if len(result)!=len(records):raise ValueError('Duplicate recording identity')
    return result


def baseline_gate(base,readback,summary_sha,probe_sha):
    if base['status']!='complete_partial_scope' or base['planned_recordings']!=50 or base['available_recordings']!=50:raise ValueError('Complete 50-record baseline required')
    if readback['status']!='all_tread_sagittal_exports_checked_unreviewed' or readback['scientific_approval'] is not False or readback['summary_sha256']!=summary_sha or readback['probe_sha256']!=probe_sha or readback['source_sha256']!=base['source']['sha256']:raise ValueError('Independent baseline source readback mismatch')
    expected=unique(base['recordings']);checked=unique(readback['records'])
    if len(expected)!=50 or expected.keys()!=checked.keys() or sum(r['observations'] for r in expected.values())!=8626 or sum(r['excluded'] for r in expected.values())!=3674:raise ValueError('Full baseline membership/counts differ')
    for key,r in expected.items():
        c=checked[key]
        if Path(r['path']).parts!=(r['subject'],r['condition'],'phase.parquet') or not r['schema_passed'] or r['rows']!=r['observations']*150:raise ValueError('Invalid baseline observation/path identity')
        if c['observations']!=r['observations'] or c['excluded_pairs']!=r['excluded'] or c['source_pairs']!=r['observations']+r['excluded'] or c['output_sha256']!=r['sha256'] or c['finite_values_checked']<=0 or not math.isfinite(c['maximum_error']) or c['maximum_error']>1e-9:raise ValueError('Baseline readback incomplete')
    return expected,checked


def prepare(folder):
    summary=BASELINE/'conversion_summary.json';base=json.loads(summary.read_text());checked=json.loads(READBACK.read_text())
    baseline_gate(base,checked,digest(summary),digest(PROBE))
    original=json.loads((BASE/'metadata_serial_queue_20261021/plan.json').read_text())['jobs'][1]
    if original['name']!='um21_tread_components':raise ValueError('Original recipe identity changed')
    for path,sha in original['code_sha256'].items():
        if digest(path)!=sha:raise ValueError('Original producer code changed')
    bindings=dict(original['code_sha256'])
    for path in [summary,READBACK,PROBE,Path(__file__),BASE/'metadata_serial_queue_20261021/plan.json',ROOT/'contributor_tools/preserve_mblue_planar_estimates.py']:
        bindings[str(path.resolve())]=digest(path)
    source=Path(base['source']['path']);stat=source.stat()
    if (stat.st_size,stat.st_mtime_ns)!=(base['source']['bytes'],base['source']['mtime_ns']):raise ValueError('Source stat changed')
    output=folder/'components'
    return {'status':'prepared_not_executed','scientific_approval':False,'bindings':bindings,'baseline_root':str(BASELINE),'base_summary':str(summary),'base_readback':str(READBACK),'source':base['source'],'output_root':str(output),'records':base['recordings'],'command':[sys.executable,str(ROOT/'contributor_tools/extend_umich_tread_source.py'),'--base-root',str(BASELINE),'--base-readback',str(READBACK),'--output-root',str(output)],'expected':{'recordings':50,'observations':8626,'rows':1293900,'excluded_preserved':3674},'limitations':['Original component values and units only; no canonical kinetic frames/ankle or global segment orientation approval.','Baseline accepted cycles and exclusion ledger preserved; does not validate source event semantics.','Plan preparation did not hash the 2.2GB source or read numerical outputs; serial worker verifies them.'],'limits':{'address_space_mib':768,'workers':1,'timeout_seconds':21600,'windows_startup_mib':2816,'windows_runtime_mib':2048,'linux_startup_mib':3584,'linux_runtime_mib':2048}}


def verify(plan):
    for path,sha in plan['bindings'].items():
        if digest(path)!=sha:raise ValueError('Changed binding: '+path)


def completion_gate(report,plan,base,readback):
    expected,checked=baseline_gate(base,readback,plan['bindings'][plan['base_summary']],plan['bindings'][str(PROBE)])
    if report['status']!='all_tread_joint_components_readback_unreviewed' or report['scientific_approval'] is not False or report['planned_recordings']!=50 or report['base_summary_sha256']!=plan['bindings'][plan['base_summary']] or report['base_readback_sha256']!=plan['bindings'][plan['base_readback']] or report['source_sha256']!=plan['source']['sha256']:raise ValueError('Full component receipt provenance incomplete')
    actual=unique(report['records'])
    if actual.keys()!=expected.keys():raise ValueError('Component recording membership differs')
    for key,r in actual.items():
        original=expected[key];prior=checked[key]
        if r['observations_checked']!=original['observations'] or not r['existing_columns_exactly_preserved'] or r['finite_source_values_checked']<=0 or r['source_columns']<=0 or not math.isfinite(r['maximum_error']) or r['maximum_error']>1e-9 or r['base_output_sha256']!=original['sha256'] or r['ledger_sha256']!=prior['ledger_sha256']:raise ValueError('Component/source preservation incomplete')
    if sum(r['observations_checked'] for r in actual.values())!=8626:raise ValueError('Full observation scope differs')
    producer={p:sha for p,sha in plan['bindings'].items() if p in report['code_sha256']}
    if len(producer)!=4 or producer!=report['code_sha256']:raise ValueError('Actual producer bindings differ')
    return actual


def run(planpath):
    plan=json.loads(planpath.read_text());plansha=digest(planpath);verify(plan);folder=planpath.parent;output=Path(plan['output_root'])
    if output.exists() or (folder/'completion.json').exists():raise FileExistsError('Fresh restoration required')
    # Executed only under the separately reviewed continuous host guard watcher.
    with (folder/'producer.log').open('x') as log:
        subprocess.run(plan['command'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=21600)
    verify(plan)
    if digest(planpath)!=plansha:raise ValueError('Plan changed')
    summary=output/'conversion_summary.json';report=json.loads(summary.read_text());base=json.loads(Path(plan['base_summary']).read_text());readback=json.loads(Path(plan['base_readback']).read_text())
    records=completion_gate(report,plan,base,readback);artifacts={str(summary):digest(summary)}
    # Final full source hash is intentionally inside the guarded serial slot.
    if digest(plan['source']['path'])!=plan['source']['sha256']:raise ValueError('Source changed during restoration')
    for (subject,condition),r in records.items():
        recordfolder=output/subject/condition
        for name,key in [('phase.parquet','output_sha256'),('candidate_ledger.jsonl','ledger_sha256'),('source_columns.json','source_columns_sha256')]:
            path=recordfolder/name
            if digest(path)!=r[key]:raise ValueError('Persisted component/ledger identity differs')
            artifacts[str(path)]=r[key]
        mapping=json.loads((recordfolder/'source_columns.json').read_text())
        if len(mapping)!=r['source_columns']:raise ValueError('Component sidecar coverage differs')
    verify(plan)
    result={'status':'all50_tread_components_8626_observations_source_checked_unreviewed','scientific_approval':False,'plan_sha256':plansha,'recordings':50,'observations':8626,'excluded_preserved':3674,'source_sha256':plan['source']['sha256'],'bindings':plan['bindings'],'artifacts':artifacts,'limitations':plan['limitations']}
    with (folder/'completion.json').open('x') as f:json.dump(result,f,indent=2)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-root',type=Path,required=True);p.add_argument('--run',action='store_true');a=p.parse_args();out=a.output_root.resolve()
    if not out.is_relative_to(BASE):raise ValueError('Isolated output required')
    if a.run:run(out/'plan.json');return
    plan=prepare(out);out.mkdir(parents=True,exist_ok=False);(out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(plan['expected']))
if __name__=='__main__':main()
