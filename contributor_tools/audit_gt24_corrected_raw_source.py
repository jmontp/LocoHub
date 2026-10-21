"""Independent bounded GT24 corrected continuous readback, without adapter imports.

Checks exported fields against literal CSV columns. Canonical orientation and
source event/condition annotations are not scientifically approved by this audit.
"""
import argparse
from collections import deque
from contextlib import ExitStack
import csv
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import resource
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

JOINTS=(('hip_flexion','hip_flexion','hip_flexion',1),('knee_angle','knee_flexion','knee_extension',-1),('ankle_angle','ankle_dorsiflexion','ankle_plantarflexion',-1))
REQUIRED={'angle_filt','moment_filt','grf','velocity','insole_sim'}
TABLES=REQUIRED|{'moment_filt_bio','exo'}


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def number(token):
    if token is None:raise ValueError('Truncated CSV row')
    if token.strip().lower() in ('','na','nan','n/a','null'):return math.nan
    value=float(token)
    if math.isinf(value):raise ValueError('Infinite source value requires explicit investigation')
    return value


def projected_columns(kind):
    if kind in ('angle_filt','velocity','moment_filt','moment_filt_bio'):
        suffix={'angle_filt':'','velocity':'_velocity','moment_filt':'_moment','moment_filt_bio':'_moment'}[kind]
        return {f'{native}_{leg}{suffix}' for native,_,_,_ in JOINTS for leg in ('l','r')}
    if kind=='grf':return {f'fp_{leg}_force_{axis}' for leg in ('l','r') for axis in ('x','y','z')}
    if kind=='insole_sim':return {f'insole_{leg}_cop_{axis}' for leg in ('l','r') for axis in ('x','z')}
    return {f'{joint}_angle_{leg}_torque_interaction' for joint in ('hip','knee') for leg in ('l','r')}


def source_rows(record,guard=lambda:None):
    files=record['files']
    if not REQUIRED<=set(files):raise ValueError('Required source stream missing')
    with ExitStack() as stack:
        readers={}
        for kind in sorted(TABLES&set(files)):
            path=Path(files[kind]['path'])
            expected_name=f"{record['subject']}_{record['recording']}_{kind}.csv"
            if path.name!=expected_name or path.parent.resolve()!=Path(record['folder']).resolve():raise ValueError('Source stream identity/path differs')
            stream=stack.enter_context(path.open(encoding='utf-8-sig',newline=''))
            def bounded_lines(handle):
                for line in handle:
                    if len(line)>1024*1024:raise MemoryError('CSV line exceeds1MiB')
                    yield line
            reader=csv.DictReader(bounded_lines(stream));headers=reader.fieldnames or []
            if len(set(headers))!=len(headers) or 'time' not in headers:raise ValueError('Duplicate/missing source header')
            # Missing optional streams are reported unassessed. Present mapped
            # streams must contain the literal columns used by their aliases.
            if not projected_columns(kind)<=set(headers):raise ValueError('Required literal source columns missing: '+kind)
            readers[kind]=reader
        previous=None
        for index,values in enumerate(itertools.zip_longest(*readers.values())):
            if index%512==0:guard()
            if any(row is None for row in values):raise ValueError('Source stream row counts differ')
            raw={kind:{name:number(row[name]) for name in projected_columns(kind)|{'time'}} for kind,row in zip(readers,values)}
            clock=raw['angle_filt']['time']
            if not math.isfinite(clock) or previous is not None and clock<=previous:raise ValueError('Invalid source clock')
            if any(not math.isclose(value['time'],clock,rel_tol=0,abs_tol=1e-9) for value in raw.values()):raise ValueError('Source stream clocks differ')
            previous=clock
            yield raw


def scan(record,guard=lambda:None):
    first=None;previous=None;step=None;count=0;contacts={};finite_velocity=set()
    for row in source_rows(record,guard):
        clock=row['angle_filt']['time']
        if first is None:first=clock
        if previous is not None:
            delta=clock-previous
            if step is None:step=delta
            elif not math.isclose(delta,step,rel_tol=0,abs_tol=1e-9):raise ValueError('Nonuniform clock requires interval-specific derivatives')
        for leg in ('l','r'):
            if leg not in contacts and row['grf'][f'fp_{leg}_force_y']>20:contacts[leg]=count
        for column,value in row['velocity'].items():
            if column!='time' and math.isfinite(value):finite_velocity.add(column)
        previous=clock;count+=1
    if count<2:raise ValueError('At least two source samples required')
    gait=record.get('is_gait')
    if type(gait) is not bool:raise ValueError('Bound task archetype required, not inferred from output')
    reference=min(contacts,key=lambda leg:(contacts[leg],leg)) if gait and contacts else 'l'
    return {'rows':count,'start':first,'end':previous,'sampling_rate':1/step,'reference':reference,'finite_velocity_columns':finite_velocity,'reference_evidence':('first_raw_vertical_force_above20N_with_left_tie' if contacts else 'no_contact_left_fallback_unassessed') if gait else 'documented_non_gait_left_reference'}


def windows(rows):
    """Five-row rolling source neighborhood; never retains the trial."""
    iterator=iter(rows);buffer=deque();base=0;index=0;ended=False
    while True:
        while not ended and base+len(buffer)<=index+2:
            try:buffer.append(next(iterator))
            except StopIteration:ended=True
        if index>=base+len(buffer):return
        yield index,base,list(buffer)
        index+=1
        while base<index-2:buffer.popleft();base+=1


def derivative(index,count,get,time):
    if index==0:return (get(1)-get(0))/(time(1)-time(0))
    if index==count-1:return (get(index)-get(index-1))/(time(index)-time(index-1))
    a=time(index)-time(index-1);b=time(index+1)-time(index)
    return -b/(a*(a+b))*get(index-1)+(b-a)/(a*b)*get(index)+a/(b*(a+b))*get(index+1)


def mass_values(record):
    participant=record['participant_mass']['value_kg'];model=record['model_mass']['source_model_mass_kg']
    for value in (participant,model):
        if value is not None and (type(value) not in (int,float) or not math.isfinite(value) or value<=0):raise ValueError('Invalid bound mass')
    if participant is not None and record['participant_mass'].get('status')!='source_participant_mass_bound':raise ValueError('Participant mass is not source bound')
    if record.get('verified_source_denominator') is not None:raise ValueError('Unsupported source-normalized moment denominator')
    if record['exo_state'] not in ('no_exo','powered','worn_unpowered'):raise ValueError('Unknown assistance state')
    return participant,model


def expected_row(record,facts,index,base,window,producer_policy='gt24_participant_mass_missingness_v2'):
    participant,model=mass_values(record);values={};withheld=set()
    if producer_policy not in ('gt24_participant_mass_v1','gt24_participant_mass_missingness_v2'):raise ValueError('Unknown bound producer policy')
    if producer_policy=='gt24_participant_mass_v1' and (participant is None or model is None):raise ValueError('V1 requires known masses')
    def raw(i,kind,column):return window[i-base].get(kind,{}).get(column,math.nan)
    time=lambda i:raw(i,'angle_filt','time')-facts['start']
    reference=facts['reference'];side='left' if reference=='l' else 'right'
    recording=f"gt24:{record['phase']}/{record['subject']}/{record['recording']}";identity=recording+':continuous:'+side
    values.update(subject='GT24_'+record['subject'],task=record['task'],task_id=record['task_id'],step=identity,source_recording_id=recording,observation_id=identity,observation_type='continuous_recording',reference_side=side,source_start_time_s=facts['start'],source_end_time_s=facts['end'],sampling_rate_hz=facts['sampling_rate'],assistance_active=record['exo_state']=='powered',source_time_s=raw(index,'angle_filt','time'),time_s=time(index))
    def put(name,value,reason=False):
        values[name]=value
        if reason:withheld.add(name)
    for role,leg in [('ipsi',reference),('contra','r' if reference=='l' else 'l')]:
        force=raw(index,'grf',f'fp_{leg}_force_y')
        put(f'grf_vertical_{role}_BW',force/(participant*9.81) if participant is not None else math.nan,participant is None)
        put(f'derived_source_model_weight_grf_vertical_{role}',force/(model*9.81) if model is not None else math.nan,model is None)
        if producer_policy=='gt24_participant_mass_missingness_v2':put(f'source_grf_vertical_{role}_N',force)
        for axis in ('x','y','z'):put(f'source_grf_global_{axis}_{role}_N',raw(index,'grf',f'fp_{leg}_force_{axis}'))
        for axis in ('anterior','lateral'):put(f'grf_{axis}_{role}_BW',math.nan,True)
        for axis,native in [('anterior','x'),('lateral','z')]:put(f'cop_{axis}_{role}_m',raw(index,'insole_sim',f'insole_{leg}_cop_{native}'))
        put(f'cop_vertical_{role}_m',math.nan,True)
        for native,canonical,coordinate,sign in JOINTS:
            angle=lambda i:sign*raw(i,'angle_filt',native+'_'+leg)*math.pi/180
            column=native+'_'+leg+'_velocity'
            velocity=(lambda i:sign*raw(i,'velocity',column)*math.pi/180) if column in facts['finite_velocity_columns'] else (lambda i:derivative(i,facts['rows'],angle,time))
            put(f'{canonical}_angle_{role}_rad',angle(index))
            put(f'{canonical}_velocity_{role}_rad_s',velocity(index))
            put(f'{canonical}_acceleration_{role}_rad_s2',derivative(index,facts['rows'],velocity,time))
            for kind,table in [('net','moment_filt'),('biological','moment_filt_bio')]:put(f'source_normalized_{coordinate}_{kind}_moment_{role}_Nm_kg',raw(index,table,native+'_'+leg+'_moment'))
            for kind in ('moment','biological_moment'):put(f'{canonical}_{kind}_{role}_Nm_kg',math.nan,True)
            put(f'{canonical}_assistance_moment_{role}_Nm_kg',0. if record['exo_state']=='no_exo' else math.nan,record['exo_state']!='no_exo')
            if canonical!='ankle_dorsiflexion':put(f'source_exo_{canonical}_interaction_torque_{role}_units_unknown',raw(index,'exo',native.replace('_flexion','_angle')+'_'+leg+'_torque_interaction'))
        for kind,table,suffix,unit,scale in [('angle','angle_filt','','rad',math.pi/180),('velocity','velocity','_velocity','rad_s',math.pi/180),('moment','moment_filt','_moment','Nm_kg',1.),('biological_moment','moment_filt_bio','_moment','Nm_kg',1.)]:put(f'source_ankle_coordinate_{kind}_{role}_{unit}',raw(index,table,'ankle_angle_'+leg+suffix)*scale)
        for segment in ('thigh','shank','foot'):
            for kind,unit in [('angle','rad'),('velocity','rad_s')]:put(f'{segment}_sagittal_{kind}_{role}_{unit}',math.nan,True)
    return values,withheld


def check_value(actual,expected,name):
    missing=lambda value:value is None or isinstance(value,float) and math.isnan(value)
    if missing(expected):
        if not missing(actual):raise ValueError('Missing/withheld value fabricated: '+name)
        return 'missing'
    if missing(actual):raise ValueError('Available source value lost: '+name)
    if isinstance(expected,(int,float)) and not isinstance(expected,bool):
        if not math.isfinite(actual) or not math.isclose(actual,expected,rel_tol=1e-7,abs_tol=1e-7):raise ValueError('Raw source value/sign/normalization differs: '+name)
    elif actual!=expected:raise ValueError('Source identity differs: '+name)
    return 'finite'


def metadata_gate(row,record,facts,producer_policy='gt24_participant_mass_missingness_v2'):
    subject=json.loads(row['subject_metadata']);info=json.loads(row['task_info']);participant,model=mass_values(record)
    for name,value in {'weight_kg':participant,'participant_mass_kg':participant,'source_model_mass_kg':model,'weight_basis':'participant_without_exoskeleton','day':record['participant_mass']['calendar_day'],'source_mass_evidence_sha256':record['mass_evidence_sha256']}.items():
        if name not in subject or subject[name]!=value:raise ValueError('Mass metadata differs: '+name)
    if info.get('normalization_policy')!=producer_policy:raise ValueError('Normalization policy differs from bound producer')
    for name,value in {'reference_leg':facts['reference'],'exo_state':record['exo_state'],'source_joint_moment_denominator_status':'unverified'}.items():
        if info.get(name)!=value:raise ValueError('Task/source provenance differs: '+name)


def audit(record,output,guard=lambda:None,producer_policy='gt24_participant_mass_missingness_v2'):
    import pyarrow.parquet as pq
    before={kind:digest(value['path']) for kind,value in record['files'].items() if kind in TABLES}
    facts=scan(record,guard);parquet=pq.ParquetFile(output)
    if parquet.metadata.num_rows!=facts['rows']:raise ValueError('Source/output row count differs')
    counts={};total=0
    def output_rows():
        for batch in parquet.iter_batches(batch_size=256,use_threads=False):
            guard()
            if batch.nbytes>8*1024**2:raise MemoryError('Readback batch exceeds8MiB')
            yield from batch.to_pylist()
    for source,row in itertools.zip_longest(windows(source_rows(record,guard)),output_rows()):
        if source is None or row is None:raise ValueError('Full row coverage differs')
        index,base,window=source;values,withheld=expected_row(record,facts,index,base,window,producer_policy)
        if set(row)!=set(values)|{'subject_metadata','task_info'}:raise ValueError('Unexpected or missing unaudited output columns')
        metadata_gate(row,record,facts,producer_policy)
        for name,expected in values.items():
            category=check_value(row[name],expected,name)
            if category=='missing' and name in withheld:category='withheld'
            counts.setdefault(name,{'finite':0,'missing':0,'withheld':0})[category]+=1
        total+=1
    if before!={kind:digest(record['files'][kind]['path']) for kind in before}:raise ValueError('Source changed during readback')
    unassessed=[name for name,count in counts.items() if count['finite']==0 and count['missing']>0]
    return {'status':'corrected_raw_source_partial_unassessed' if unassessed or facts['reference_evidence']=='no_contact_left_fallback_unassessed' else 'corrected_raw_source_fields_checked_unreviewed','scientific_approval':False,'subject':record['subject'],'phase':record['phase'],'recording':record['recording'],'rows':total,'output_sha256':digest(output),'source_sha256':before,'coverage':counts,'entirely_unassessed_features':unassessed,'reference_evidence':facts['reference_evidence'],'bound_producer_policy':producer_policy,'missing_optional_streams':sorted((TABLES-REQUIRED)-set(record['files'])),'limitations':['Task/archetype/assistance metadata requires separately bound source annotation evidence.','First20N crossing reproduces documented exporter reference convention, not independent gait-event validity.','COP calcn-frame source alias and anatomical signs follow reviewed conversion convention; anatomical validity remains unapproved.','Complete native transition residuals and unexported source columns outside this corrected Parsed output remain separate scope.']}


def unit_evidence(readme):
    import re
    checks={'angle_filt':r'<task name>_angle_filt\.csv:.*?\(deg\)',
            'velocity':r'<task name>_velocity\.csv:.*?\(deg/s\)',
            'moment_filt':r'<task name>_moment_filt\.csv:.*?\(Nm/kg\)',
            'moment_filt_bio':r'<task name>_moment_filt_bio\.csv:.*?\(Nm/kg\)',
            'grf':r'<task name>_grf\.csv:.*?Force in N.*?y-axis is vertical',
            'insole_sim':r'Virtual_Insoles\.csv:.*?COP in m.*?calcn_l and calcn_r'}
    for name,pattern in checks.items():
        if not re.search(pattern,readme):raise ValueError('Publisher unit evidence absent: '+name)
    return {'angle':'deg','velocity':'deg/s','source_moments':'Nm/kg, denominator unresolved','force':'N, global y vertical','cop':'m, calcn frames','interaction_torque':'unknown; no canonical normalization'}


def admission(plan,planpath,index,output):
    if plan['bindings'].get(str(Path(__file__).resolve()))!=digest(__file__):raise ValueError('Auditor itself must be bound by a fresh audit plan')
    guard_path=ROOT/'contributor_tools/preserve_mblue_planar_estimates.py'
    if plan['bindings'].get(str(guard_path))!=digest(guard_path):raise ValueError('Runtime guard not bound')
    matrix_path=Path(plan['mass_matrix'])
    if plan['bindings'].get(str(matrix_path))!=digest(matrix_path):raise ValueError('Mass metadata evidence not bound')
    matrix=json.loads(matrix_path.read_text());readme=matrix['source_metadata']['readme'];path=Path(readme['path'])
    expected=readme.get('sha256')
    if expected is None or digest(path)!=expected:raise ValueError('Publisher README hash differs')
    units=unit_evidence(path.read_text())
    # The independent audit plan must reference the actual conversion plan and
    # admission receipt. They bind source membership; output identity alone is
    # never evidence that the source belongs to the producer.
    conversion=Path(plan['conversion_plan']);receipt=Path(plan['conversion_admission'])
    for source in (conversion,receipt):
        if plan['bindings'].get(str(source))!=digest(source):raise ValueError('Actual conversion provenance unbound')
    cp=json.loads(conversion.read_text());admitted=json.loads(receipt.read_text())
    summary=conversion.parent/'pilot_summary.json'
    if plan['bindings'].get(str(summary))!=digest(summary):raise ValueError('Actual producer summary unbound')
    actual=json.loads(summary.read_text())
    policies={'two_phase_participant_force_pilot_checked_unreviewed':('gt24_participant_mass_v1','apply_gt24_participant_normalization.py'),'unknown_mass_representatives_normalization_checked_unreviewed':('gt24_participant_mass_missingness_v2','apply_gt24_participant_normalization_v2.py')}
    if actual.get('status') not in policies or actual.get('plan_sha256')!=digest(conversion):raise ValueError('Actual producer mode unknown')
    policy,filename=policies[actual['status']];producer=ROOT/'contributor_tools'/filename
    if plan.get('producer_policy')!=policy or plan.get('normalization_producer')!=str(producer) or cp['bindings'].get(str(producer))!=digest(producer):raise ValueError('Explicit bound producer/schema differs')

    if admitted.get('plan_sha256')!=digest(conversion) or not admitted.get('membership_hashes'):raise ValueError('Actual membership admission missing')
    for source,sha in admitted['membership_hashes'].items():
        if digest(source)!=sha:raise ValueError('Admitted source membership changed')
    if plan['records'][index]!=cp['records'][index]:raise ValueError('Audit record differs from actual admitted conversion')
    if output.resolve()!=conversion.parent/f'record_{index}'/'continuous.parquet':raise ValueError('Wrong corrected output identity/path')
    return units


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--plan-sha256',required=True);parser.add_argument('--record-index',type=int,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--report',type=Path,required=True);args=parser.parse_args()
    for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[name]='1'
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
    import pyarrow as pa
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    if args.report.exists():raise FileExistsError('Preserve existing audit')
    plan=json.loads(args.plan.read_text())
    def verify():
        if digest(args.plan)!=args.plan_sha256:raise ValueError('Plan changed')
        for path,sha in plan['bindings'].items():
            if digest(path)!=sha:raise ValueError('Bound evidence changed')
    verify();units=admission(plan,args.plan,args.record_index,args.output);record=plan['records'][args.record_index]
    from contributor_tools.preserve_mblue_planar_estimates import headroom,windows_available_mib
    last_check=[0.]
    def guard():
        if time.monotonic()-last_check[0]<15:return
        last_check[0]=time.monotonic()
        headroom(args.output.parent)
        if windows_available_mib()<2048:raise MemoryError('Windows runtime headroom below2048MiB')
    guard();result=audit(record,args.output,guard,plan['producer_policy']);verify();admission(plan,args.plan,args.record_index,args.output);result['plan_sha256']=args.plan_sha256;result['publisher_units']=units
    with args.report.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')

if __name__=='__main__':main()
