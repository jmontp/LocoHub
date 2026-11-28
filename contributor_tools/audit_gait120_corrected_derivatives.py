"""Independent raw-clock readback of corrected Gait120 derivative outputs."""
import json
import math
from pathlib import Path
from contributor_tools.audit_gait120_extended_sources import derivative, compare, expected_anthropometry, spreadsheet_rows
from contributor_tools.withhold_gait120_planar_segments import ALIASES as PLANAR, INFO as PLANAR_INFO
from contributor_tools.correct_gait120_unshifted_derivatives import PREVIOUS, POLICY, CORRECTED_PLANAR_INFO, read_observation


def bit_equal(a,b):
    import pyarrow as pa
    a=a.combine_chunks();b=b.combine_chunks()
    if not a.is_null().equals(b.is_null()):return False
    if pa.types.is_floating(a.type):
        dtype={32:pa.uint32(),64:pa.uint64()}.get(a.type.bit_width)
        return dtype is not None and a.view(dtype).equals(b.view(dtype))
    return a.equals(b)


def expected_from_raw(raw,start,end):
    """Interpolate source radians, then independent scalar finite differences."""
    import numpy as np
    time=raw['time']
    if len(time)<10 or time[0]!=start or time[-1]!=end or end<=start:raise ValueError('Complete original source clock required')
    if any(not math.isfinite(t) for t in time) or any(b<=a for a,b in zip(time,time[1:])):raise ValueError('Finite strictly increasing source clock required')
    if any(len(v)!=len(time) or any(math.isinf(x) for x in v) for v in raw.values()):raise ValueError('Complete finite-or-missing source arrays required')
    required=[f'{j}_r' for j in ('hip_flexion','knee_angle','ankle_angle')]
    if not set(required)<=set(raw):raise ValueError('Required right source components absent')
    contra=all(f'{j}_l' in raw for j in ('hip_flexion','knee_angle','ankle_angle'));grid=np.linspace(start,end,150);duration=end-start
    def sample(name,sign=1):
        if name not in raw:return [math.nan]*150
        return np.interp(grid,time,[v*sign*math.pi/180 for v in raw[name]]).tolist()
    pelvis=sample('pelvis_tilt');expected={'pelvis_sagittal_velocity_rad_s':derivative(pelvis,duration)};segments={}
    for role,leg in [('ipsi','r'),('contra','l')]:
        angles={}
        for native,canonical,sign in [('hip_flexion','hip_flexion',1),('knee_angle','knee_flexion',-1),('ankle_angle','ankle_dorsiflexion',1)]:
            angle=sample(f'{native}_{leg}',sign) if role=='ipsi' or contra else [math.nan]*150;angles[canonical]=angle
            velocity=derivative(angle,duration)
            expected[f'{canonical}_velocity_{role}_rad_s']=velocity
            expected[f'{canonical}_acceleration_{role}_rad_s2']=derivative(velocity,duration)
        thigh=[p+h for p,h in zip(pelvis,angles['hip_flexion'])];shank=[t-k for t,k in zip(thigh,angles['knee_flexion'])];foot=[s+a for s,a in zip(shank,angles['ankle_dorsiflexion'])]
        for segment,angle in [('thigh',thigh),('shank',shank),('foot',foot)]:
            segments[f'derived_planar_{segment}_sagittal_angle_{role}_rad']=angle
            segments[f'derived_planar_{segment}_sagittal_velocity_{role}_rad_s']=derivative(angle,duration)
    return expected,segments


def verify_tables(before,after,raw,anthropometry):
    import pyarrow as pa
    if before.num_rows!=150 or after.num_rows!=150:raise ValueError('Complete150-row observation required')
    if after.column_names!=before.column_names+list(PREVIOUS.values())+list(PLANAR.values()) or before.schema.metadata!=after.schema.metadata:raise ValueError('Unexpected column or schema metadata change')
    starts=before['source_start_time_s'].to_pylist();ends=before['source_end_time_s'].to_pylist()
    if len(set(starts))!=1 or len(set(ends))!=1:raise ValueError('Source clock identity inconsistent')
    expected,segments=expected_from_raw(raw,starts[0],ends[0]);checks={}
    changed=set(expected)|set(PLANAR)|{'task_info'}
    for field in before.schema:
        adjusted=field.with_nullable(True) if field.name in PLANAR else field
        if not adjusted.equals(after.schema.field(field.name),check_metadata=True):raise ValueError('Original field metadata changed')
        if field.name not in changed and not bit_equal(before[field.name],after[field.name]):raise ValueError('Unrelated bits/null mask changed: '+field.name)
    for name,alias in PREVIOUS.items():
        f=before.schema.field(name);expected_metadata={**(f.metadata or {}),b'derivative_policy':b'previous frozen automatic discontinuity repair; preserved unassessed'}
        if not pa.field(alias,f.type,nullable=f.nullable,metadata=expected_metadata).equals(after.schema.field(alias),check_metadata=True):raise ValueError('Previous derivative alias metadata changed')
        if not bit_equal(before[name],after[alias]):raise ValueError('Previous derivative not preserved: '+name)
    for name,alias in PLANAR.items():
        f=before.schema.field(name);expected_metadata={**(f.metadata or {}),b'derivation':b'Gait120 sagittal planar estimate; anatomical orientation unassessed'}
        if not pa.field(alias,f.type,nullable=f.nullable,metadata=expected_metadata).equals(after.schema.field(alias),check_metadata=True):raise ValueError('Planar alias metadata changed')
        if after[name].null_count!=150:raise ValueError('Unsupported anatomical segment orientation resurrected')
    for name,values in expected.items():
        target=PLANAR[name] if name in PLANAR else name
        checks[target]=compare(after[target].to_pylist(),values,target)
    for name,values in segments.items():checks[name]=compare(after[name].to_pylist(),values,name)
    for old_info,new_info in zip(before['task_info'].to_pylist(),after['task_info'].to_pylist()):
        expected_info=json.loads(old_info)
        if 'gait120_unshifted_derivatives' in expected_info or 'gait120_planar_segments' in expected_info:raise ValueError('Existing correction metadata conflict')
        expected_info.update(gait120_unshifted_derivatives=POLICY,gait120_planar_segments=CORRECTED_PLANAR_INFO)
        if json.loads(new_info)!=expected_info:raise ValueError('Task provenance changed')
    for text in after['subject_metadata'].to_pylist():
        if json.loads(text)!=anthropometry:raise ValueError('Independent spreadsheet mass/height differs')
    return checks


def audit_record(original_plan,relative,corrected_path):
    import pyarrow.parquet as pq
    from contributor_tools import run_gait120_source_checked_full as source_check
    from contributor_tools.preserve_mblue_planar_estimates import digest
    from contributor_tools.run_gt24_ankle_converter_pilot import verify
    original_receipt=source_check.completed(original_plan,relative)
    if original_receipt is None:raise ValueError('Completed baseline source receipt required')
    folder=Path(original_plan['output_root'])/'recordings'/Path(relative).with_suffix('');manifest=json.loads((folder/'conversion_manifest.json').read_text());verify(manifest['sources'])
    raw=source_check.mot_columns(Path(original_plan['source_root'])/relative,['time','pelvis_tilt']+[f'{joint}_{leg}' for leg in ('r','l') for joint in ('hip_flexion','knee_angle','ankle_angle')])
    spreadsheets=[p for p in manifest['sources'] if p.endswith('Anthropometric_Data_Participants.xlsx')]
    if len(spreadsheets)!=1:raise ValueError('Bound original spreadsheet required')
    anthropometry=expected_anthropometry(spreadsheet_rows(spreadsheets[0]),Path(relative).parts[0])
    before=read_observation(folder/'phase.parquet');after=read_observation(corrected_path)
    checks=verify_tables(before,after,raw,anthropometry);verify(manifest['sources'])
    if source_check.completed(original_plan,relative)!=original_receipt:raise ValueError('Original source receipt changed')
    return {'status':'unshifted_derivatives_and_planar_source_aliases_checked_unreviewed','scientific_approval':False,'relative':relative,'rows':150,'original_receipt':original_receipt,'source_sha256':manifest['sources'],'output_sha256':digest(corrected_path),'auditor_sha256':digest(__file__),'feature_checks':checks,'source_anthropometry':'Independent original spreadsheet row checked','previous_derivatives':'All19 original arrays preserved bitwise under prior-policy aliases','uncertainty':['Planar segment fields remain source-only estimates, not anatomical orientation.','Finite-difference values describe the source-resampled curves, not independent measured angular velocity or validated physiological smoothness.','Source anomalies remain; missing values are unassessed.','Canonical force/COP and moments retain original withheld state.']}
