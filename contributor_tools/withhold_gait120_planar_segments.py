"""Isolated source-only proposal for Gait120 planar segment estimates.

No automatic scientific execution. Keep all twelve original arrays under derived
aliases; withhold unsupported anatomical orientations. Joint fields unchanged.
"""
import json
from contributor_tools.audit_gait120_extended_sources import SEGMENTS
ALIASES={name:'derived_planar_'+name for name in SEGMENTS}
INFO={'status':'source_planar_estimates_preserved_anatomical_orientation_unassessed','formula':'thigh=pelvis_tilt+hip_flexion; shank=thigh-knee_flexion; foot=shank+ankle_dorsiflexion','limitation':'Scalar sagittal sums do not establish three-dimensional segment orientation or anatomical zero.','velocity':'Original estimate derivative retained, including any frozen heuristic phase-discontinuity repair; not relabeled as measured angular velocity.'}


def transform_table(table):
    import pyarrow as pa
    if len(table.column_names)!=len(set(table.column_names)) or not set(ALIASES)<=set(table.column_names) or set(ALIASES.values())&set(table.column_names):raise ValueError('Missing/duplicate/already preserved segment fields')
    if any(not isinstance(s,str) or not s.startswith('G120_') for s in table['subject'].to_pylist()):raise ValueError('Gait120 observations required')
    result=table
    for name,alias in ALIASES.items():
        field=table.schema.field(name)
        if not pa.types.is_floating(field.type):raise ValueError('Floating segment estimate required')
        metadata={**(field.metadata or {}),b'derivation':b'Gait120 sagittal planar estimate; anatomical orientation unassessed'}
        result=result.append_column(pa.field(alias,field.type,nullable=field.nullable,metadata=metadata),table[name])
        result=result.set_column(result.schema.get_field_index(name),field.with_nullable(True),pa.nulls(table.num_rows,type=field.type))
    infos=[]
    for raw in table['task_info'].to_pylist():
        info=json.loads(raw)
        if 'gait120_planar_segments' in info:raise ValueError('Conflicting existing segment policy')
        info['gait120_planar_segments']=INFO;infos.append(json.dumps(info,sort_keys=True,allow_nan=False))
    field=table.schema.field('task_info');result=result.set_column(result.schema.get_field_index('task_info'),field,pa.array(infos,type=field.type))
    return result


def verify_tables(before,after):
    import pyarrow as pa
    expected=transform_table(before)
    if not expected.schema.equals(after.schema,check_metadata=True) or len(before)!=len(after):raise ValueError('Schema or rows changed')
    for name in expected.column_names:
        a=expected[name].combine_chunks();b=after[name].combine_chunks()
        if not a.is_null().equals(b.is_null()):raise ValueError('Null mask changed: '+name)
        if pa.types.is_floating(a.type):
            t={32:pa.uint32(),64:pa.uint64()}.get(a.type.bit_width)
            if t is None or not a.view(t).equals(b.view(t)):raise ValueError('Numerical bits changed: '+name)
        elif not a.equals(b):raise ValueError('Unrelated field changed: '+name)
