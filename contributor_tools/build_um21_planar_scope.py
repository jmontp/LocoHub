"""Bind complete existing UM21 reconstruction evidence for labeling-only work.

Reads small manifests and hashes artifacts; never loads numerical datasets.
Boundary sidecars need additional prior provenance evidence not present in the
current recovery summary, so that producer fails closed until reconciled.
"""
import argparse
import json
import math
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.preserve_um21_planar_estimates import digest,validate_scope



RUN_CHECKER=ROOT/'contributor_tools/audit_probes/2026_10_20/check_um21_running_source.py'
# Audited checker writes its report only after all source/observation assertions.
RUN_CHECKER_SHA='8e99c429cc67b78d37136e9fe8265e9c82589ea7d5de4d30db2a7730bccfd879'


def validate_run_completion(summary,readback):
    status=readback.get('status')
    if status not in (None,'all_running_source_cycles_checked_unreviewed'):
        raise ValueError('Run readback is not terminal')
    if readback.get('source_sha256')!=summary.get('source_sha256') or not summary.get('source_sha256'):
        raise ValueError('Run readback source binding differs')
    if status is None:
        if digest(RUN_CHECKER)!=RUN_CHECKER_SHA or readback.get('probe_sha256')!=RUN_CHECKER_SHA:
            raise ValueError('Legacy final-only Run checker identity differs')
        errors=readback.get('source_component_max_errors')
        if not isinstance(errors,dict) or not errors or any(not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in errors.values()):
            raise ValueError('Missing/invalid complete Run source error evidence')
        if not isinstance(readback.get('finite_source_values_checked'),int) or readback['finite_source_values_checked']<=0:
            raise ValueError('Missing Run source value coverage')
    return 'legacy_final_only_audited_checker' if status is None else 'explicit_terminal_status'


def records_from_evidence(producer,summary,summary_hash,readback=None):
    records=[]
    inventory=summary.get('recordings',summary.get('records',[]))
    keys=[(r['subject'],r['condition']) for r in inventory]
    if len(set(keys))!=len(keys):raise ValueError('Duplicate source recording identity')
    if producer=='run':
        if summary['status']!='complete_running_source_channels_unreviewed' or len(summary['recordings'])!=summary['available_recordings']:raise ValueError('Run reconstruction incomplete')
        if not readback or readback['summary_sha256']!=summary_hash:raise ValueError('Independent Run readback not bound to summary')
        validate_run_completion(summary,readback)
        rows=summary['recordings'];checked={(r['subject'],r['condition']):r for r in readback['recordings']}
        if len(checked)!=len(rows) or len(readback['recordings'])!=len(rows):raise ValueError('Run source readback scope mismatch')
        for r in rows:
            key=(r['subject'],r['condition']);c=checked.get(key)
            if not c or c['observations']!=r['observations'] or c['rows']!=r['rows']:raise ValueError('Run readback count mismatch')
            phase=f"{r['subject']}/{r['condition']}/phase.parquet"
            records.append({'phase_path':phase,'phase_sha256':r['outputs'][phase],'observations':r['observations'],'rows':r['rows'],'outputs':r['outputs']})
        if sum(r['observations'] for r in records)!=readback['total_observations'] or sum(r['rows'] for r in records)!=readback['total_rows']:raise ValueError('Run aggregate mismatch')
    elif producer=='tread_components':
        if summary['status']!='all_tread_joint_components_readback_unreviewed' or len(summary['records'])!=summary['planned_recordings']:raise ValueError('Full treadmill component reconstruction required')
        for r in summary['records']:
            if not r['existing_columns_exactly_preserved'] or r['source_columns']!=84:raise ValueError('Source extension preservation not established')
            parent=f"{r['subject']}/{r['condition']}";phase=parent+'/phase.parquet'
            outputs={phase:r['output_sha256'],parent+'/source_columns.json':r['source_columns_sha256'],parent+'/candidate_ledger.jsonl':r['ledger_sha256']}
            records.append({'phase_path':phase,'phase_sha256':r['output_sha256'],'observations':r['observations_checked'],'rows':150*r['observations_checked'],'outputs':outputs})
    elif producer=='stairs':
        if summary['status']!='all_annotated_stair_cycles_exported_unreviewed':raise ValueError('Full stair reconstruction required')
        if not readback or readback['status']!='all_annotated_stair_cycles_source_checked_unreviewed' or readback['summary_sha256']!=summary_hash:raise ValueError('Full independent stair readback required')
        if len(summary['recordings'])!=readback['source_recordings']:raise ValueError('Stair recording census mismatch')
        for r in summary['recordings']:
            count=len(r['windows']);phase=f"{r['subject']}/{r['condition']}/phase.parquet"
            if not count:
                if r.get('disposition')!='no_annotated_observations' or r.get('exported_rows')!=0 or not r.get('outputs') or not any('ledger' in Path(p).name or 'disposition' in Path(p).name for p in r['outputs']):
                    raise ValueError('Empty stair recording lacks explicit hash-bound disposition ledger')
                records.append({'phase_path':None,'record_path':f"{r['subject']}/{r['condition']}",'disposition':r['disposition'],'observations':0,'rows':0,'outputs':r['outputs']})
                continue
            if r.get('exported_rows')!=count*150:raise ValueError('Missing stair output needs reconciliation')
            records.append({'phase_path':phase,'phase_sha256':r['outputs'][phase],'observations':count,'rows':count*150,'outputs':r['outputs']})
        if sum(r['observations'] for r in records)!=readback['annotated_observations'] or readback['exported_observations_checked']!=readback['annotated_observations']:raise ValueError('Stair annotation coverage mismatch')
    elif producer=='boundaries':
        raise ValueError('Boundary summary binds phase hashes but not source_columns/recovered_cycles sidecars; independent source-membership and sidecar scope proof required')
    else:raise ValueError('Unsupported producer')
    paths=[p for r in records for p in r['outputs']]
    if len(set(paths))!=len(paths):raise ValueError('Output path reused across records')
    return records


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True);p.add_argument('--producer',choices=['run','tread_components','stairs','boundaries'],required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    summary_path=args.baseline/'conversion_summary.json';summary_hash=digest(summary_path);summary=json.loads(summary_path.read_text())
    evidence={str(summary_path.resolve()):summary_hash};readback=None
    if args.producer in ('run','stairs'):
        rp=args.baseline/'source_comparison.json';readback=json.loads(rp.read_text());evidence[str(rp.resolve())]=digest(rp)
    records=records_from_evidence(args.producer,summary,summary_hash,readback)
    if args.producer=='run' and readback.get('status') is None:evidence[str(RUN_CHECKER)]=RUN_CHECKER_SHA
    evidence[str(Path(__file__).resolve())]=digest(Path(__file__))
    expected_paths=set()
    for r in records:
        for relative,sha in r['outputs'].items():
            path=Path(relative)
            if path.is_absolute() or '..' in path.parts:raise ValueError('Unsafe output evidence')
            if digest(args.baseline/path)!=sha:raise ValueError('Baseline artifact hash differs: '+relative)
            expected_paths.add(relative)
        parent=Path(r['phase_path']).parent if r['phase_path'] else Path(r['record_path'])
        actual_sidecars={str(p.relative_to(args.baseline)) for p in (args.baseline/parent).iterdir() if p.is_file()}
        if actual_sidecars!=set(r['outputs']):raise ValueError('Incomplete per-record artifact inventory')
    actual={str(x.relative_to(args.baseline)) for x in args.baseline.rglob('phase.parquet')}
    if actual!={r['phase_path'] for r in records if r['phase_path']}:raise ValueError('Actual phase shard inventory differs from complete manifest')
    report={'status':'complete_um21_planar_scope_checked_unreviewed','producer':args.producer,'scientific_approval':False,
        'baseline_root':str(args.baseline.resolve()),'baseline_summary_sha256':summary_hash,'evidence_bindings':evidence,
        'expected_records':len(records),'expected_observations':sum(r['observations'] for r in records),'records':records,
        'completion_evidence':validate_run_completion(summary,readback) if args.producer=='run' else 'explicit_terminal_status',
        'builder_sha256':digest(Path(__file__)),'source_sha256':summary['source_sha256'],
        'limitations':['Complete scope refers to this declared reconstruction producer, not all UM21 source modes','Source numerical readback does not validate3D segment conventions','Boundary sidecar lineage is not admitted by this builder']}
    validate_scope(report)
    if any(digest(path)!=sha for path,sha in evidence.items()):raise ValueError('Evidence changed during scope check')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as f:json.dump(report,f,indent=2);f.write('\n')


if __name__=='__main__':main()
