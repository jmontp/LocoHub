"""Independent bounded boundary-sidecar/source gate; default prepares a plan.

--run --pilot-cycles 5 checks a finite prefix and cannot emit a complete scope.
--run (without a limit) requires a complete baseline and emits a scope accepted
by the frozen planar postprocessor. Original data and summaries are untouched.
"""
import argparse
from collections import defaultdict
import json
import hashlib
import math
import os
from pathlib import Path
import resource
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.preserve_um21_planar_estimates import digest,validate_scope
from contributor_tools.preserve_mblue_planar_estimates import headroom,windows_available_mib
KEYS=('subject','condition','reference_side','start_frame','end_frame','original_normalized_task')
GROUPS={'jointAngles':('joint_angle','deg'),'jointForces':('joint_force','N_kg'),'jointMoments':('joint_moment','Nm_kg'),'jointPowers':('joint_power','W_kg')}


def identity(item):
    key=tuple(item[k] for k in KEYS)
    if any(not isinstance(v,str) or not v or '/' in v or v in ('.','..') for v in key[:2]):raise ValueError('Unsafe recording identity')
    if key[2] not in ('left','right') or any(type(x) is not int for x in key[3:5]) or not 1<=key[3]<key[4] or key[4]-key[3]+1>4096:raise ValueError('Invalid source interval')
    return key


def reconcile(summary,review,coverage,membership,sidecars,full):
    """Pure manifest reconciliation; raw-source and numerical checks are separate."""
    if review['status']!='curated_window_exclusions_explained' or coverage['status']!='full_treadmill_curation_membership_accounted':raise ValueError('Incomplete admission evidence')
    items=review['records'];keys=[identity(x) for x in items]
    if len(set(k[:5] for k in keys))!=len(keys) or len(keys)!=review['cycles'] or summary['planned_cycles']!=len(keys):raise ValueError('Ambiguous/incomplete reviewed scope')
    members=[identity(x) for x in membership if x['streaming_status']=='excluded_in_original_curation']
    if len(members)!=len(set(members)) or set(members)!=set(keys):raise ValueError('Original curated membership differs')
    allowed=('all_curated_boundary_cycles_recovered_unreviewed',) if full else ('all_curated_boundary_cycles_recovered_unreviewed','partial_requested_limit')
    if summary['status'] not in allowed:raise ValueError('Recovery baseline not terminal')
    count=summary['recovered_cycles']
    if type(count) is not int or not 0<count<=len(items) or (full and count!=len(items)):raise ValueError('Incomplete recovered coverage')
    expected=defaultdict(list)
    for item in items[:count]:expected[(item['subject'],item['condition'])].append(item)
    records=summary['records'];ids=[(r['subject'],r['condition']) for r in records]
    if len(ids)!=len(set(ids)) or set(ids)!=set(expected) or set(sidecars)!=set(expected):raise ValueError('Recording inventory differs')
    for r in records:
        key=(r['subject'],r['condition'])
        if r['cycles']!=len(expected[key]) or sidecars[key]!=expected[key]:raise ValueError('Recovered sidecar differs from admitted source membership/order')
    return expected


def expected_mapping(trial):
    mapping={}
    for group,(kind,unit) in GROUPS.items():
        if group not in trial:continue
        for name,ds in trial[group].items():
            if ds.ndim!=2 or not 1<=ds.shape[0]<=3:raise ValueError('Unexpected source component shape')
            for n in range(ds.shape[0]):
                col=f'source_{kind}_{name.lower()}_component_{n}_{unit}'
                if col in mapping:raise ValueError('Source component name collision')
                mapping[col]={'group':group,'variable':name,'matlab_component_1based':n+1,'unit':unit,'canonical_frame_verified':False}
    if not mapping:raise ValueError('No source components')
    return mapping


def bounded(ds):
    if ds.size>65536 or ds.size*ds.dtype.itemsize>1024**2:raise ValueError('Event/annotation exceeds bounded admission')
    return ds[...]


def check_cycle(frame,item,trial,streaming,normalized):
    import numpy as np
    from contributor_tools.recover_umich_curated_boundaries import recovered_window,verify_cycle
    from contributor_tools.common.data_contract import inspect_contract
    subject,condition,side,start,end,label=identity(item)
    window=recovered_window(item)
    recording=f'um21:Streaming/{subject}/Tread/{condition}';obs=f'{recording}:{side}:frames:{start}:{end}'
    expected={'subject':'UM21_'+subject,'source_recording_id':recording,'observation_id':obs,'step':obs,'reference_side':side,'observation_type':'individual_cycle','task':window['task'],'task_id':label}
    if len(frame)!=150:raise ValueError('Incomplete phase observation')
    for key,value in expected.items():
        if not frame[key].eq(value).all():raise ValueError('Source identity/task differs: '+key)
    for value in frame.task_info:
        if json.loads(value)!=window['info']:raise ValueError('Boundary metadata differs')
    np.testing.assert_allclose(frame.phase_ipsi,np.linspace(0,100,150),rtol=0,atol=1e-12)
    events=trial['events'];hs=bounded(events['LHS' if side=='left' else 'RHS']).reshape(-1)
    if not np.isfinite(hs).all() or not np.equal(hs,np.floor(hs)).all() or not (np.diff(hs)>0).all():raise ValueError('Invalid source heel-strike clock')
    if sum(a==start and b==end for a,b in zip(hs[:-1],hs[1:]))!=1:raise ValueError('Not an adjacent source heel-strike pair')
    labels=[''.join(chr(int(c)) for c in bounded(streaming[ref]).reshape(-1)) for ref in bounded(events['tasks']).reshape(-1)]
    cuts=bounded(events['cutPoints']).T
    if cuts.shape!=(len(labels),2) or not np.isfinite(cuts).all() or not np.equal(cuts,np.floor(cuts)).all():raise ValueError('Invalid source task windows')
    hits=[(a,b) for name,(a,b) in zip(labels,cuts) if name==label and a<=start<=b<end]
    if hits!=[(window['info']['source_task_window_start_frame'],window['info']['source_task_window_end_frame'])]:raise ValueError('Source task-window membership differs')
    alias={'d5':'in5','d10':'in10'}.get(condition,condition)
    details=bounded(normalized[f'Normalized/{subject}/Walk/{label}/{alias}/events/StrideDetails']).T
    if details.ndim!=2 or details.shape[1]!=4 or not np.isfinite(details).all():raise ValueError('Invalid normalized stride metadata')
    leg=1 if side=='left' else 2
    if sum(a==start and b==end and duration==end-start and native_leg==leg for a,b,duration,native_leg in details)!=1:raise ValueError('Original normalized source membership differs')
    if not inspect_contract(frame,mode='phase').schema_passed:raise ValueError('Phase contract failed')
    return verify_cycle(frame,trial,item)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    base=ROOT/'converted_datasets/reconversion_v2'
    p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True)
    p.add_argument('--window-review',type=Path,default=base/'um21_curated_window_edges_20261021/window_edges.json')
    p.add_argument('--curation-review',type=Path,default=base/'um21_tread_full_curation_v2_20261021/curation_coverage.json')
    p.add_argument('--source',type=Path,default=ROOT/'contributor_tools/conversion_scripts/Umich_2021/Streaming.mat')
    p.add_argument('--normalized',type=Path,default=ROOT/'contributor_tools/conversion_scripts/Umich_2021/Normalized.mat')
    p.add_argument('--pilot-cycles',type=int);p.add_argument('--run',action='store_true');a=p.parse_args()
    if a.pilot_cycles is not None and not 1<=a.pilot_cycles<=10:p.error('Finite pilot must be 1..10 cycles')
    baseline=a.baseline.resolve();out=a.output_root.resolve()
    if not out.is_relative_to(base.resolve()) or out==baseline:raise ValueError('New authorized output root required')
    summary_path=baseline/'conversion_summary.json';summary=json.loads(summary_path.read_text())
    review=json.loads(a.window_review.read_text());coverage=json.loads(a.curation_review.read_text());membership_path=a.curation_review.parent/'cycle_membership.jsonl'
    membership=[json.loads(line) for line in membership_path.read_text().splitlines()]
    binds={str(x.resolve()):digest(x) for x in [summary_path,a.window_review,a.curation_review,membership_path,Path(__file__),ROOT/'contributor_tools/preserve_um21_planar_estimates.py',ROOT/'contributor_tools/preserve_mblue_planar_estimates.py',ROOT/'contributor_tools/um21_planar_field_policy.py',*sorted((ROOT/'contributor_tools/common').rglob('*.py'))]}
    for path,sha in summary['code_sha256'].items():
        if digest(path)!=sha:raise ValueError('Recovery code differs from audited baseline')
        binds[path]=sha
    if summary['review_sha256']!=digest(a.window_review) or summary['curation_review_sha256']!=digest(a.curation_review) or review['curation_coverage_sha256']!=digest(a.curation_review) or coverage['membership_sha256']!=digest(membership_path):raise ValueError('Admission artifact hash differs')
    if not summary['source_sha256']==review['streaming_sha256']==coverage['source_streaming_sha256'] or summary['normalized_source_sha256']!=coverage['source_normalized_sha256']:raise ValueError('Source hash identity differs')
    sidecars={};records=[]
    for r in summary['records']:
        key=(r['subject'],r['condition'])
        if any(not isinstance(v,str) or not v or '/' in v or v in ('.','..') for v in key):raise ValueError('Unsafe recording folder')
        folder=baseline.joinpath(*key)
        if key in sidecars:raise ValueError('Duplicate baseline record')
        sidecars[key]=json.loads((folder/'recovered_cycles.json').read_text())
        expected={'phase.parquet','source_columns.json','recovered_cycles.json'}
        if {x.name for x in folder.iterdir()}!=expected:raise ValueError('Unexpected record artifact inventory')
        outputs={str((folder/name).relative_to(baseline)):(r['output_sha256'] if name=='phase.parquet' else digest(folder/name)) for name in expected}
        rel=str((folder/'phase.parquet').relative_to(baseline))
        records.append({'phase_path':rel,'phase_sha256':r['output_sha256'],'observations':r['cycles'],'rows':150*r['cycles'],'outputs':outputs})
        for name,sha in outputs.items():binds[str(baseline/name)]=sha
    selected=reconcile(summary,review,coverage,membership,sidecars,a.pilot_cycles is None)
    if {str(x.relative_to(baseline)) for x in baseline.rglob('phase.parquet')}!={r['phase_path'] for r in records}:raise ValueError('Extra/missing baseline phase records')
    plan={'status':'prepared_not_executed','baseline':str(baseline),'pilot_cycles':a.pilot_cycles,'bindings':binds,'source_bindings':{str(a.source.resolve()):summary['source_sha256'],str(a.normalized.resolve()):summary['normalized_source_sha256']},'scientific_approval':False}
    planpath=out/'plan.json'
    if out.exists():
        if not planpath.is_file() or list(out.iterdir())!=[planpath] or json.loads(planpath.read_text())!=plan:raise FileExistsError('Existing attempt preserved')
    else:out.mkdir(parents=True);planpath.write_text(json.dumps(plan,indent=2)+'\n')
    if not a.run:print(json.dumps({'plan':str(planpath),'status':plan['status']}));return
    for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[name]='1'
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
    headroom(out)
    if windows_available_mib()<2816:raise MemoryError('Startup host reserve insufficient')
    import h5py
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    last=0.
    def guard():
        nonlocal last
        if time.monotonic()-last>=15:
            headroom(out)
            if windows_available_mib()<2048:raise MemoryError('Runtime host reserve insufficient')
            last=time.monotonic()
    def verify_bindings():
        for path,sha in {**binds,**plan['source_bindings']}.items():
            guard()
            value=hashlib.sha256()
            with Path(path).open('rb') as stream:
                for chunk in iter(lambda:stream.read(1024**2),b''):
                    guard();value.update(chunk)
            if value.hexdigest()!=sha:raise ValueError('Bound artifact changed: '+path)
    verify_bindings();checked=0;finite=0;seen=set()
    with h5py.File(a.source,'r',rdcc_nbytes=1024**2) as raw,h5py.File(a.normalized,'r',rdcc_nbytes=1024**2) as normalized:
        for record in records:
            guard();folder=baseline/Path(record['phase_path']).parent;key=tuple(Path(record['phase_path']).parts[:2]);items=selected[key]
            trial=raw[f'Streaming/{key[0]}/Tread/{key[1]}']
            if json.loads((folder/'source_columns.json').read_text())!=expected_mapping(trial):raise ValueError('Source component sidecar differs from raw source')
            parquet=pq.ParquetFile(folder/'phase.parquet')
            if parquet.metadata.num_rows!=record['rows']:raise ValueError('Persisted row count differs')
            for index,batch in enumerate(parquet.iter_batches(batch_size=150,use_threads=False)):
                guard()
                if a.pilot_cycles is not None and checked>=a.pilot_cycles:break
                if index>=len(items):raise ValueError('Extra persisted observation')
                item=items[index];ident=identity(item)
                if ident[:5] in seen:raise ValueError('Duplicate observed source cycle')
                result=check_cycle(batch.to_pandas(use_threads=False),item,trial,raw,normalized);seen.add(ident[:5]);checked+=1;finite+=result['finite_source_values_checked']
            if a.pilot_cycles is not None and checked>=a.pilot_cycles:break
    expected=min(a.pilot_cycles,summary['recovered_cycles']) if a.pilot_cycles is not None else summary['recovered_cycles']
    if checked!=expected:raise ValueError('Source audit coverage incomplete')
    verify_bindings()
    report={'status':'boundary_source_pilot_checked_unreviewed' if a.pilot_cycles is not None else 'all_boundary_source_sidecars_checked_unreviewed','scientific_approval':False,'observations_checked':checked,'finite_source_values_checked':finite,'bindings':binds,'source_bindings':plan['source_bindings'],'limitations':['Source labels describe cycle start, not a constant task throughout the cycle','Existing numerical verifier reused; membership, identities, task metadata and component mapping checked separately','Canonical segment orientations and kinetic frames remain scientifically unresolved']}
    audit=out/'source_comparison.json';audit.write_text(json.dumps(report,indent=2)+'\n')
    if a.pilot_cycles is None:
        scope={'status':'complete_um21_planar_scope_checked_unreviewed','producer':'boundaries','scientific_approval':False,'baseline_root':str(baseline),'baseline_summary_sha256':digest(summary_path),'evidence_bindings':{**binds,str(audit):digest(audit)},'expected_records':len(records),'expected_observations':checked,'records':records,'source_sha256':summary['source_sha256'],'completion_evidence':'complete_boundary_source_sidecar_readback'}
        validate_scope(scope);(out/'scope.json').write_text(json.dumps(scope,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'observations_checked':checked}))


if __name__=='__main__':main()
