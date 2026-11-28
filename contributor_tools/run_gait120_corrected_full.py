"""Full6882 Gait120 derivative correction after actual baseline completion.

Preparation is metadata-only. --run requires actual complete source receipts;
no automatic launch, output overwrite, or anatomy approval.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'converted_datasets/reconversion_v2';sys.path.insert(0,str(ROOT))
from contributor_tools.preserve_mblue_planar_estimates import digest
from contributor_tools.run_gt24_ankle_converter_pilot import verify
from contributor_tools import run_gait120_source_checked_full as baseline


def prepare(original_plan_path,output):
    original_plan_path=Path(original_plan_path).resolve();output=Path(output).resolve()
    if not output.is_relative_to(BASE) or output.exists():raise ValueError('Fresh authorized output required')
    original=json.loads(original_plan_path.read_text());verify(original['bindings']);inventory=json.loads(Path(original['inventory']).read_text());scope=baseline.scope(inventory)
    bindings={**original['bindings'],str(original_plan_path):digest(original_plan_path)}
    for name in ['run_gait120_corrected_full.py','correct_gait120_unshifted_derivatives.py','audit_gait120_corrected_derivatives.py','audit_gait120_extended_sources.py','withhold_gait120_planar_segments.py']:
        path=ROOT/'contributor_tools'/name;bindings[str(path)]=digest(path)
    plan={'status':'prepared_waiting_actual_full_baseline','scientific_approval':False,'original_plan':str(original_plan_path),'original_plan_sha256':digest(original_plan_path),'output_root':str(output),'bindings':bindings,'scope':scope,'recordings':inventory['recordings'],'worker_mib':1024,'worker_seconds':120,'startup_windows_mib':3072,'startup_linux_mib':3584,'policy':'19 unshifted finite differences on original150-point source-duration grid; previous19 derivatives preserved,12planar canonical fields withheld with corrected derived aliases.','uncertainty':['Anatomical segment orientation not established.','Source anomalies preserved; no physiological smoothness approval.','Joint signs retain reviewed source mapping and existing anatomical limitations.','Canonical force/COP and moments remain withheld.'],'endpoint_policy':'Forward first sample, centered interior, backward final sample; dt=(source_end-source_start)/149. No circular derivative or phase-discontinuity repair.'}
    output.mkdir(parents=True,exist_ok=False);(output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');return plan


def admit(plan,plan_sha):
    verify(plan['bindings']);original=json.loads(Path(plan['original_plan']).read_text());summary_path=Path(original['output_root'])/'summary.json'
    if not summary_path.exists():raise ValueError('Actual full baseline completion required before correction')
    if summary_path.stat().st_size>8*1024**2:raise MemoryError('Baseline summary exceeds8MiB')
    summary=json.loads(summary_path.read_text())
    if summary.get('status')!='all6882_gait120_records_source_checked_unreviewed' or summary.get('scientific_approval') is not False or summary.get('plan_sha256')!=plan['original_plan_sha256']:raise ValueError('Completed baseline status/plan mismatch')
    if summary.get('full_scope')!=plan['scope'] or len(summary['records'])!=6882 or [r['relative'] for r in summary['records']]!=plan['recordings']:raise ValueError('All6882 original records required; partial baseline rejected')
    return {'status':'actual_full_baseline_admitted_unreviewed','scientific_approval':False,'plan_sha256':plan_sha,'summary_path':str(summary_path),'summary_sha256':digest(summary_path),'records':summary['records']}


def check_admission(plan,sha,path):
    saved=json.loads(Path(path).read_text());current=admit(plan,sha)
    if saved!=current:raise ValueError('Admitted baseline changed')
    return saved


def completed(plan,relative,admitted):
    folder=Path(plan['output_root'])/'recordings'/Path(relative).with_suffix('');report_path=folder/'source_readback.json'
    if not folder.exists():return None
    if not report_path.exists():raise ValueError('Partial corrected output retained; explicit recovery required')
    report=json.loads(report_path.read_text());manifest_path=folder/'correction_manifest.json';manifest=json.loads(manifest_path.read_text())
    plan_path=Path(plan['output_root'])/'plan.json'
    if json.loads(plan_path.read_text())!=plan:raise ValueError('Active plan differs')
    expected_sha=digest(plan_path)
    if report.get('plan_sha256')!=expected_sha or manifest.get('plan_sha256')!=expected_sha:raise ValueError('Receipt plan binding differs')
    if manifest.get('status')!='corrected_unshifted_derivatives_export_unreviewed' or manifest.get('scientific_approval') is not False or manifest.get('relative')!=relative or manifest.get('original_receipt')!=admitted:raise ValueError('Manifest source identity differs')
    if report.get('status')!='unshifted_derivatives_and_planar_source_aliases_checked_unreviewed' or report.get('scientific_approval') is not False or report.get('relative')!=relative or report.get('rows')!=150 or report.get('original_receipt')!=admitted:raise ValueError('Corrected receipt scope differs')
    auditor=ROOT/'contributor_tools/audit_gait120_corrected_derivatives.py'
    if report.get('auditor_sha256')!=digest(auditor) or manifest['code_sha256']!=plan['bindings']:raise ValueError('Correction producer/reviewer changed')
    if report.get('manifest_sha256')!=digest(manifest_path) or report['output_sha256']!=digest(folder/'phase.parquet') or manifest['output_sha256']!=report['output_sha256']:raise ValueError('Corrected artifacts changed')
    verify(report['source_sha256'])
    return {'relative':relative,'output_sha256':report['output_sha256'],'readback_sha256':digest(report_path),'manifest_sha256':digest(manifest_path)}


def worker(plan_path,index):
    import resource
    resource.setrlimit(resource.RLIMIT_AS,(1024*1024**2,1024*1024**2))
    import pyarrow as pa
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    from contributor_tools.correct_gait120_unshifted_derivatives import write_corrected
    from contributor_tools.audit_gait120_corrected_derivatives import audit_record
    plan=json.loads(plan_path.read_text());sha=digest(plan_path);verify(plan['bindings']);admission=check_admission(plan,sha,plan_path.parent/'admission.json')
    if not 0<=index<6882:raise ValueError('Invalid complete-source index')
    relative=plan['recordings'][index];admitted=admission['records'][index];original=json.loads(Path(plan['original_plan']).read_text())
    if baseline.completed(original,relative)!=admitted:raise ValueError('Original source receipt changed')
    if completed(plan,relative,admitted):return
    folder=Path(plan['output_root'])/'recordings'/Path(relative).with_suffix('');folder.mkdir(parents=True,exist_ok=False);target=folder/'phase.parquet'
    source=Path(original['output_root'])/'recordings'/Path(relative).with_suffix('')/'phase.parquet';write_corrected(source,target)
    manifest={'status':'corrected_unshifted_derivatives_export_unreviewed','scientific_approval':False,'relative':relative,'original_receipt':admitted,'code_sha256':plan['bindings'],'output_sha256':digest(target),'plan_sha256':sha};mp=folder/'correction_manifest.json';mp.write_text(json.dumps(manifest,indent=2)+'\n')
    report=audit_record(original,relative,target);report['manifest_sha256']=digest(mp);report['plan_sha256']=sha
    verify(plan['bindings']);check_admission(plan,sha,plan_path.parent/'admission.json')
    if digest(plan_path)!=sha or baseline.completed(original,relative)!=admitted:raise ValueError('Correction inputs changed')
    with (folder/'source_readback.json').open('x') as f:json.dump(report,f,indent=2,allow_nan=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-root',type=Path,required=True);p.add_argument('--original-plan',type=Path);p.add_argument('--run',action='store_true');p.add_argument('--resume',action='store_true');p.add_argument('--worker-index',type=int);a=p.parse_args();out=a.output_root.resolve();plan_path=out/'plan.json'
    if not out.is_relative_to(BASE):raise ValueError('Authorized output root required')
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[k]='1'
    if a.worker_index is not None:worker(plan_path,a.worker_index);return
    if not a.run:
        if not a.original_plan:p.error('--original-plan required for preparation')
        print(json.dumps(prepare(a.original_plan,out)['scope']));return
    plan=json.loads(plan_path.read_text());sha=digest(plan_path);verify(plan['bindings']);admission_path=out/'admission.json'
    if plan['output_root']!=str(out):raise ValueError('Output root differs')
    if admission_path.exists():
        if not a.resume:raise FileExistsError('Explicit resume required')
        admission=check_admission(plan,sha,admission_path)
    else:
        if a.resume:raise ValueError('No admitted prior run')
        admission=admit(plan,sha)
        with admission_path.open('x') as f:json.dump(admission,f,indent=2)
    summary_path=out/'summary.json';previous={}
    if summary_path.exists():
        if not a.resume:raise FileExistsError('Existing summary requires explicit resume')
        old=json.loads(summary_path.read_text())
        if old['plan_sha256']!=sha:raise ValueError('Prior summary plan differs')
        previous={r['relative']:r for r in old['records']}
    records=[];state={'status':'running_full_derivative_correction','scientific_approval':False,'plan_sha256':sha,'scope':plan['scope'],'records':records};guard=baseline.load_guard()
    def save():
        tmp=out/'summary.tmp';tmp.write_text(json.dumps(state,indent=2)+'\n');tmp.replace(summary_path)
    try:
        for index,relative in enumerate(plan['recordings']):
            if (out/'STOP').exists() or (out/'STOP_AFTER_CURRENT').exists():raise RuntimeError('Coordinator stop')
            receipt=completed(plan,relative,admission['records'][index])
            if receipt:
                if previous.get(relative)!=receipt:raise ValueError('Resume receipt not pinned by prior summary')
                records.append(receipt);continue
            if relative in previous:raise ValueError('Prior corrected output missing')
            baseline.cap_aware_admission(guard.check_resources(prelaunch=True));state['current_record']=relative;save()
            command=['prlimit','--as=1073741824','nice','-n','19','ionice','-c','3',sys.executable,str(Path(__file__).resolve()),'--output-root',str(out),'--worker-index',str(index)]
            guard.guarded_stage(command,out/f'worker_{index:04d}.log',{'recording':relative})
            result=completed(plan,relative,admission['records'][index])
            if result is None:raise ValueError('Independent corrected readback missing')
            records.append(result);save()
        if len(records)!=6882:raise ValueError('Full source scope omitted')
        state['status']='all6882_unshifted_derivatives_source_checked_unreviewed';state.pop('current_record',None)
        verify(plan['bindings']);check_admission(plan,sha,admission_path)
        original=json.loads(Path(plan['original_plan']).read_text())
        for relative,admitted,corrected in zip(plan['recordings'],admission['records'],records):
            if baseline.completed(original,relative)!=admitted or completed(plan,relative,admitted)!=corrected:raise ValueError('Final source or corrected receipt changed')
    except BaseException as exc:state.update(status='stopped_incomplete',reason=str(exc));raise
    finally:save()

if __name__=='__main__':main()
