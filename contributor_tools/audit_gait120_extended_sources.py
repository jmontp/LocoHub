"""Independent Gait120 derivative/anthropometry review, separate from frozen run.

No execution on import. Scalar checks never call producer derivative or metadata
helpers. Planar segment arithmetic can be reproduced without approving it as
anatomical orientation. Phase-shift repair on unshifted data stays unassessed.
"""
import json
import math
from pathlib import Path
import statistics

SEGMENTS=tuple(f'{segment}_sagittal_{kind}_{side}_{unit}' for segment in ('thigh','shank','foot') for side in ('ipsi','contra') for kind,unit in [('angle','rad'),('velocity','rad_s')])


def derivative(values,duration):
    if len(values)<2 or not math.isfinite(duration) or duration<=0:raise ValueError('Positive actual source duration required')
    dt=duration/(len(values)-1)
    return [(values[1]-values[0])/dt]+[(values[i+1]-values[i-1])/(2*dt) for i in range(1,len(values)-1)]+[(values[-1]-values[-2])/dt]


def repair_would_trigger(values):
    """Independently characterize the frozen producer's documented threshold.

    This detects when plain physical-time differentiation is not the producer's
    operation; it does not bless the subsequent spline/spike repair.
    """
    if len(values)<3 or any(not math.isfinite(v) for v in values):return False
    jumps=[abs(b-a) for a,b in zip(values,values[1:])];median=statistics.median(jumps)
    return median>0 and max(jumps)>3*median


def compare(actual,expected,name):
    if len(actual)!=len(expected):raise ValueError('Different row count: '+name)
    finite=missing=0
    for a,b in zip(actual,expected):
        a=math.nan if a is None else float(a)
        if math.isinf(a) or math.isinf(b):raise ValueError('Infinite scientific value: '+name)
        if math.isnan(a)!=math.isnan(b):raise ValueError('Missingness differs: '+name)
        if math.isnan(b):missing+=1
        elif not math.isclose(a,b,rel_tol=1e-8,abs_tol=1e-8):raise ValueError('Independent value differs: '+name)
        else:finite+=1
    return {'finite_checked':finite,'missing_unassessed':missing,'assessment':'source_computation_checked' if finite else 'all_missing_not_passed'}


def expected_anthropometry(rows,subject):
    required={'Subject','Bodymass(Kg)','Height(mm)'}
    if not rows or not required<=set(rows[0]):raise ValueError('Required spreadsheet headers absent')
    matches=[r for r in rows if str(r['Subject']).strip()==subject]
    if len(matches)!=1:raise ValueError('Exactly one original subject row required')
    r=matches[0]
    def value(name,scale):
        raw=r[name]
        if raw is None:return None
        number=float(raw)
        return number/scale if math.isfinite(number) and number>0 else None
    return {'weight_kg':value('Bodymass(Kg)',1),'height_m':value('Height(mm)',1000)}


def spreadsheet_rows(path):
    """Independent direct spreadsheet cells, no pandas/source adapter metadata helper."""
    import openpyxl
    path=Path(path)
    if path.stat().st_size>4*1024**2:raise MemoryError('Anthropometry spreadsheet exceeds4MiB')
    book=openpyxl.load_workbook(path,read_only=True,data_only=True)
    try:
        sheet=book.worksheets[0];cells=sheet.iter_rows(values_only=True);header=next(cells)
        if len(header)!=len(set(header)):raise ValueError('Duplicate spreadsheet headers')
        rows=[]
        for values in cells:
            if len(rows)>=1000:raise MemoryError('Unexpected anthropometry row count')
            if any(v is not None for v in values):rows.append(dict(zip(header,values)))
        return rows
    finally:book.close()


def review_arrays(fields,source_angles,source_pelvis,duration,anthropometry):
    """Inputs are independent resampled raw angles, not converted angle columns."""
    checks={};unassessed={};expected_segments={}
    checks['pelvis_sagittal_angle_rad']=compare(fields['pelvis_sagittal_angle_rad'],source_pelvis,'pelvis_sagittal_angle_rad')
    if repair_would_trigger(source_pelvis):unassessed['pelvis_sagittal_velocity_rad_s']='Frozen pelvis derivative invokes phase-shift repair on unshifted data.'
    else:checks['pelvis_sagittal_velocity_rad_s']=compare(fields['pelvis_sagittal_velocity_rad_s'],derivative(source_pelvis,duration),'pelvis_sagittal_velocity_rad_s')
    for side in ('ipsi','contra'):
        for joint in ('hip_flexion','knee_flexion','ankle_dorsiflexion'):
            angles=source_angles[(joint,side)];velocity=f'{joint}_velocity_{side}_rad_s';acceleration=f'{joint}_acceleration_{side}_rad_s2'
            if repair_would_trigger(angles):
                for name in (velocity,acceleration):unassessed[name]='Frozen producer invokes phase-shift repair on an unshifted source curve; plain derivative interpretation not approved.'
                continue
            expected_velocity=derivative(angles,duration);checks[velocity]=compare(fields[velocity],expected_velocity,velocity)
            if repair_would_trigger(expected_velocity):unassessed[acceleration]='Frozen acceleration invokes unapproved discontinuity repair of velocity.'
            else:checks[acceleration]=compare(fields[acceleration],derivative(expected_velocity,duration),acceleration)
        hip=source_angles[('hip_flexion',side)];knee=source_angles[('knee_flexion',side)];ankle=source_angles[('ankle_dorsiflexion',side)]
        thigh=[p+h for p,h in zip(source_pelvis,hip)];shank=[t-k for t,k in zip(thigh,knee)];foot=[s+a for s,a in zip(shank,ankle)]
        for segment,angle in [('thigh',thigh),('shank',shank),('foot',foot)]:
            name=f'{segment}_sagittal_angle_{side}_rad';checks[name]=compare(fields[name],angle,name);expected_segments[name]=angle
            velocity=f'{segment}_sagittal_velocity_{side}_rad_s'
            if repair_would_trigger(angle):unassessed[velocity]='Planar estimate derivative uses unapproved phase-shift repair.'
            else:checks[velocity]=compare(fields[velocity],derivative(angle,duration),velocity)
    for raw in fields['subject_metadata']:
        info=json.loads(raw)
        if info!=anthropometry:raise ValueError('Independent subject spreadsheet metadata differs')
    return {'status':'extended_source_computation_review_unreviewed','scientific_approval':False,'feature_checks':checks,'unassessed_features':unassessed,'anthropometry':'original subject-keyed spreadsheet row checked, kg and mm-to-m conversion independently applied','segment_anatomy':'Not approved: sagittal scalar sums reproduce planar estimates, not independently verified three-dimensional segment orientations.','recommended_source_only_segment_fields':list(SEGMENTS),'derivative_policy':'Plain finite differences checked only when frozen automatic repair does not trigger. Triggered values remain unassessed, not counted as passing.'}


def audit_record(full_plan,relative):
    """One bounded scientific worker, scheduled separately after completed full run."""
    import numpy as np
    import pyarrow.parquet as pq
    from contributor_tools import run_gait120_source_checked_full as source_check
    from contributor_tools.preserve_mblue_planar_estimates import digest
    from contributor_tools.run_gt24_ankle_converter_pilot import verify
    receipt=source_check.completed(full_plan,relative)
    if receipt is None:raise ValueError('Completed original source-readback required')
    folder=Path(full_plan['output_root'])/'recordings'/Path(relative).with_suffix('');manifest=json.loads((folder/'conversion_manifest.json').read_text());verify(manifest['sources'])
    source=Path(full_plan['source_root'])/relative
    raw=source_check.mot_columns(source,['time','pelvis_tilt']+[f'{j}_{s}' for s in ('r','l') for j in ('hip_flexion','knee_angle','ankle_angle')]);time=raw['time'];target=np.linspace(time[0],time[-1],150);duration=time[-1]-time[0]
    angles={};contra_complete=all(f'{j}_l' in raw for j in ('hip_flexion','knee_angle','ankle_angle'))
    for role,leg in [('ipsi','r'),('contra','l')]:
        for native,canonical,sign in [('hip_flexion','hip_flexion',1),('knee_angle','knee_flexion',-1),('ankle_angle','ankle_dorsiflexion',1)]:
            key=f'{native}_{leg}';angles[(canonical,role)]=(np.interp(target,time,np.asarray(raw[key])*sign*math.pi/180) if key in raw and (role=='ipsi' or contra_complete) else np.full(150,np.nan)).tolist()
    pelvis=(np.interp(target,time,np.asarray(raw['pelvis_tilt'])*math.pi/180) if 'pelvis_tilt' in raw else np.full(150,np.nan)).tolist()
    sheets=[Path(p) for p in manifest['sources'] if p.endswith('Anthropometric_Data_Participants.xlsx')]
    if len(sheets)!=1:raise ValueError('Unique bound original anthropometry spreadsheet required')
    anthropometry=expected_anthropometry(spreadsheet_rows(sheets[0]),Path(relative).parts[0])
    table=pq.ParquetFile(folder/'phase.parquet').read(use_threads=False);fields={n:table[n].to_pylist() for n in table.column_names}
    report=review_arrays(fields,angles,pelvis,duration,anthropometry);verify(manifest['sources'])
    if source_check.completed(full_plan,relative)!=receipt:raise ValueError('Original completed output changed')
    report.update(relative=relative,rows=150,original_source_receipt=receipt,source_sha256=manifest['sources'],auditor_sha256=digest(__file__))
    return report


def prepare_full_review(original_plan_path,output_root):
    """Prepare all6882 jobs only after actual full predecessor completion.

    No array loading. Immutable summary receipt hashes are rechecked per worker,
    so preparation does not reread all scientific source bytes.
    """
    from contributor_tools.preserve_mblue_planar_estimates import digest
    from contributor_tools.run_gt24_ankle_converter_pilot import verify
    from contributor_tools import run_gait120_source_checked_full as original
    original_plan_path=Path(original_plan_path).resolve();plan=json.loads(original_plan_path.read_text());verify(plan['bindings'])
    summary_path=Path(plan['output_root'])/'summary.json'
    if summary_path.stat().st_size>8*1024**2:raise MemoryError('Full summary exceeds8MiB')
    summary=json.loads(summary_path.read_text());inventory=json.loads(Path(plan['inventory']).read_text());original.scope(inventory)
    if summary.get('status')!='all6882_gait120_records_source_checked_unreviewed' or summary.get('scientific_approval') is not False or summary.get('plan_sha256')!=digest(original_plan_path):raise ValueError('Actual complete source predecessor required')
    if len(summary['records'])!=6882 or [r['relative'] for r in summary['records']]!=inventory['recordings']:raise ValueError('Full record coverage differs')
    output=Path(output_root).resolve();base=original.BASE
    if not output.is_relative_to(base) or output.exists():raise ValueError('Fresh authorized review root required')
    bindings={**plan['bindings'],str(original_plan_path):digest(original_plan_path),str(summary_path):digest(summary_path),str(Path(__file__).resolve()):digest(__file__)}
    proposal=Path(__file__).with_name('withhold_gait120_planar_segments.py');bindings[str(proposal)]=digest(proposal)
    result={'status':'full6882_extended_review_prepared_not_executed','scientific_approval':False,'original_plan':str(original_plan_path),'output_root':str(output),'scope':plan['scope'],'records':summary['records'],'bindings':bindings,'worker_limit_mib':1024,'worker_timeout_seconds':120,'startup_windows_mib':3072,'startup_linux_mib':3584,'single_worker_required':True,'segment_policy':'Audit arithmetic only; separate source-only proposal requires reviewed adoption. No data changed by this auditor.','derivative_policy':'Flag heuristic repair as unassessed, check plain source-duration derivatives where repair is not triggered.'}
    output.mkdir(parents=True,exist_ok=False);(output/'plan.json').write_text(json.dumps(result,indent=2)+'\n');return result


def run_review_worker(plan_path,index):
    import os,resource
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[key]='1'
    resource.setrlimit(resource.RLIMIT_AS,(1024*1024**2,1024*1024**2))
    from contributor_tools.preserve_mblue_planar_estimates import digest
    from contributor_tools.run_gt24_ankle_converter_pilot import verify
    plan_path=Path(plan_path);sha=digest(plan_path);plan=json.loads(plan_path.read_text());verify(plan['bindings'])
    if not 0<=index<6882 or len(plan['records'])!=6882:raise ValueError('Full source inventory index required')
    original=json.loads(Path(plan['original_plan']).read_text());receipt=plan['records'][index];relative=receipt['relative']
    from contributor_tools import run_gait120_source_checked_full as source_check
    if source_check.completed(original,relative)!=receipt:raise ValueError('Actual completed source receipt changed')
    output=Path(plan['output_root'])/'records'/f'{index:06d}.json'
    if not output.resolve().is_relative_to(source_check.BASE):raise ValueError('Unauthorized review output')
    if output.exists():raise FileExistsError('Existing review preserved')
    report=audit_record(original,relative);verify(plan['bindings'])
    if digest(plan_path)!=sha or source_check.completed(original,relative)!=receipt:raise ValueError('Review inputs changed')
    report['plan_sha256']=sha;output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as f:json.dump(report,f,indent=2,allow_nan=False)


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='mode',required=True)
    q=sub.add_parser('prepare');q.add_argument('--original-plan',type=Path,required=True);q.add_argument('--output-root',type=Path,required=True)
    q=sub.add_parser('worker');q.add_argument('--plan',type=Path,required=True);q.add_argument('--index',type=int,required=True)
    a=p.parse_args()
    if a.mode=='prepare':print(json.dumps(prepare_full_review(a.original_plan,a.output_root)['scope']))
    else:run_review_worker(a.plan,a.index)

if __name__=='__main__':main()
