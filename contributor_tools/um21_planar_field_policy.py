"""Isolated UM21 field-disclosure proposal; not adopted by frozen converters.

Preserve algebraic estimates under explicit derived_planar names. Canonical
orientations remain unavailable until independently verified 3D reconstruction.
This is an interim labeling correction, not completion of segment reconstruction.
"""


def field_policy(producer, columns):
    if producer == 'streaming_python':
        expected={f'{segment}_sagittal_angle_{side}_rad' for segment in ('thigh','shank') for side in ('ipsi','contra')}
    elif producer in ('legacy_matlab_time','legacy_matlab_phase'):
        expected={f'{segment}_sagittal_{kind}_{side}_{unit}' for segment in ('thigh','shank','foot')
                  for kind,unit in [('angle','rad'),('velocity','rad_s')] for side in ('ipsi','contra')}
    else:raise ValueError('Producer has no reviewed planar mapping')
    columns=set(columns)
    if not expected<=columns:raise ValueError('Expected planar fields missing; review producer schema')
    aliases={name:'derived_planar_'+name for name in sorted(expected)}
    if set(aliases.values()) & columns:raise ValueError('Preserved estimate fields already exist; refuse overwrite')
    return {'preserve_exactly':aliases,'withhold_canonical':sorted(expected),
        'canonical_fill':'missing, never zero','scientific_approval':False,
        'unaffected':'All raw source components, ankle missingness, joints, timing, identities and other columns remain unchanged',
        'completion_requires':'Source-frame/rotation-order validated 3D segment reconstruction and independent marker/model readback'}


def patch_streaming_source(source):
    """Prepare only; do not mutate an active converter or a previous artifact."""
    for segment,expression in [('thigh','pelvis+hip'),('shank','pelvis+hip-knee')]:
        old=f"        fields[f'{segment}_sagittal_angle_{{role}}_rad']={expression}"
        new=(f"        fields[f'derived_planar_{segment}_sagittal_angle_{{role}}_rad']={expression}\n"
             f"        fields[f'{segment}_sagittal_angle_{{role}}_rad']=np.full(150,np.nan)")
        if source.count(old)!=1:raise ValueError('Reviewed UM21 producer changed')
        source=source.replace(old,new,1)
    return source
