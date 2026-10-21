"""Fresh Gait120 derivatives and source-only planar estimates; no automatic jobs.

Recompute19 derivatives on150 inclusive samples using actual recording duration.
Original derivatives remain in explicitly named prior-policy aliases. The full
baseline remains immutable, including source anomalies and unrelated values.
"""
import json
import math
from pathlib import Path
from contributor_tools.withhold_gait120_planar_segments import ALIASES as PLANAR, INFO as ORIGINAL_PLANAR_INFO, transform_table as withhold_planar

VELOCITIES={f'{joint}_velocity_{side}_rad_s':f'{joint}_angle_{side}_rad' for side in ('ipsi','contra') for joint in ('hip_flexion','knee_flexion','ankle_dorsiflexion')}
VELOCITIES.update({f'{segment}_sagittal_velocity_{side}_rad_s':f'{segment}_sagittal_angle_{side}_rad' for segment in ('thigh','shank','foot') for side in ('ipsi','contra')})
VELOCITIES['pelvis_sagittal_velocity_rad_s']='pelvis_sagittal_angle_rad'
ACCELERATIONS={f'{joint}_acceleration_{side}_rad_s2':f'{joint}_velocity_{side}_rad_s' for side in ('ipsi','contra') for joint in ('hip_flexion','knee_flexion','ankle_dorsiflexion')}
PREVIOUS={name:'derived_previous_discontinuity_policy_'+name for name in [*VELOCITIES,*ACCELERATIONS]}
POLICY={'method':'uniform_physical_time_finite_differences','sample_grid':'150 inclusive samples from verified original source start to end','endpoints':'first-order forward/backward difference','interior':'centered second-order difference','automatic_discontinuity_repair':False,'source_anomalies':'Retained; no phase-shift repair applied to unshifted source curves','previous_derivatives':'Preserved under derived_previous_discontinuity_policy aliases','planar_segments':'Corrected derivatives remain derived planar estimates, not anatomical orientations'}

CORRECTED_PLANAR_INFO={**ORIGINAL_PLANAR_INFO,'velocity':'Corrected physical-duration finite differences of planar estimates; prior-policy derivatives retained separately and neither is a measured anatomical orientation.'}

def transform_table(before):
    import numpy as np
    import pyarrow as pa
    required=set(VELOCITIES)|set(VELOCITIES.values())|set(ACCELERATIONS)|set(PLANAR)
    if before.num_rows!=150 or not required<=set(before.column_names) or set(PREVIOUS.values())&set(before.column_names):raise ValueError('Complete fresh150-row source observation required')
    if len(before['observation_id'].unique())!=1:raise ValueError('Single source observation required')
    starts=before['source_start_time_s'].to_pylist();ends=before['source_end_time_s'].to_pylist()
    if len(set(starts))!=1 or len(set(ends))!=1:raise ValueError('Inconsistent source clock bounds')
    duration=ends[0]-starts[0]
    if not math.isfinite(duration) or duration<=0:raise ValueError('Positive source duration required')
    table=before
    for name,alias in PREVIOUS.items():
        field=before.schema.field(name)
        if not pa.types.is_floating(field.type):raise ValueError('Floating derivative required')
        table=table.append_column(pa.field(alias,field.type,nullable=field.nullable,metadata={**(field.metadata or {}),b'derivative_policy':b'previous frozen automatic discontinuity repair; preserved unassessed'}),before[name])
    values={}
    for derivative,angle in VELOCITIES.items():
        source=np.asarray(before[angle].to_pylist(),dtype=float)
        if np.isinf(source).any():raise ValueError('Infinite source-derived angle')
        values[derivative]=np.gradient(source,duration/149)
    for acceleration,velocity in ACCELERATIONS.items():values[acceleration]=np.gradient(values[velocity],duration/149)
    for name,array in values.items():
        field=before.schema.field(name);table=table.set_column(table.schema.get_field_index(name),field,pa.array(array,type=field.type))
    metadata=[]
    for raw in table['task_info'].to_pylist():
        info=json.loads(raw)
        if 'gait120_unshifted_derivatives' in info:raise ValueError('Already corrected derivative policy')
        info['gait120_unshifted_derivatives']=POLICY;metadata.append(json.dumps(info,sort_keys=True,allow_nan=False))
    field=table.schema.field('task_info');table=table.set_column(table.schema.get_field_index('task_info'),field,pa.array(metadata,type=field.type))
    # Existing source-only transform preserves corrected planar derivative arrays.
    result=withhold_planar(table)
    infos=[]
    for raw in result['task_info'].to_pylist():
        info=json.loads(raw);info['gait120_planar_segments']=CORRECTED_PLANAR_INFO;infos.append(json.dumps(info,sort_keys=True,allow_nan=False))
    return result.set_column(result.schema.get_field_index('task_info'),field,pa.array(infos,type=field.type))


def read_observation(path):
    """Reject oversized compressed or decoded observations before array reads."""
    import pyarrow.parquet as pq
    path=Path(path)
    if path.stat().st_size>8*1024**2:raise MemoryError("Observation file exceeds 8 MiB")
    file=pq.ParquetFile(path)
    if file.metadata.num_rows!=150:raise ValueError("Exactly one complete phase observation required")
    decoded=sum(file.metadata.row_group(i).total_byte_size for i in range(file.metadata.num_row_groups))
    if decoded>8*1024**2:raise MemoryError("Decoded observation exceeds 8 MiB")
    table=file.read(use_threads=False)
    if table.nbytes>8*1024**2:raise MemoryError("Observation exceeds 8 MiB")
    return table


def write_corrected(before_path,target):
    import pyarrow.parquet as pq
    target=Path(target)
    if target.exists():raise FileExistsError('Preserve prior scientific output')
    before=read_observation(before_path)
    after=transform_table(before);pq.write_table(after,target,compression='zstd',row_group_size=150)
