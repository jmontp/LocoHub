"""Explicit GT24 participant/model normalization policy, independent of converters.

Source-normalized moments are always preserved. Canonical participant-normalized
moments require a verified source denominator chain, never a second division of
already normalized values. No model or calendar-day identity is invented.
"""
import math


def participant_mass(metadata,phase,subject,*,day=None,day_evidence=None):
    if phase not in ('Phase1And2','Phase3'):raise ValueError('Explicit source phase required')
    entry=metadata['readme']['phase_masses'][phase].get(subject)
    if entry is None:raise ValueError('Unknown phase/subject')
    if day is not None and (type(day) is not int or day not in (1,2) or not day_evidence):raise ValueError('Explicit day needs source evidence')
    repeated='model_day2_with_exo_kg' in entry or 'participant_day2_kg' in entry
    if repeated and day is None:return {'value_kg':None,'status':'recording_day_unresolved','calendar_day':None}
    key='participant_day2_kg' if day==2 else 'participant_day1_kg'
    if key not in entry:return {'value_kg':None,'status':'participant_mass_not_reported_for_day','calendar_day':day}
    return {'value_kg':float(entry[key]),'status':'source_participant_mass_bound','calendar_day':day,'readme_line':entry['line'],'readme_sha256':metadata['readme']['sha256'],'basis':'participant_without_exoskeleton','day_evidence':day_evidence}


def validated_mass(evidence,key='value_kg'):
    if evidence is None or evidence.get(key) is None:return None
    value=evidence[key]
    if type(value) not in (int,float) or not math.isfinite(value) or value<=0:raise ValueError('Invalid normalization mass')
    return float(value)


def source_denominator(evidence):
    if evidence is None:return None
    value=validated_mass(evidence)
    if value is None:return None
    if evidence.get('status')!='independently_verified_source_normalization_denominator' or not evidence.get('evidence_sha256') or len(evidence['evidence_sha256'])!=64:raise ValueError('Unverified source denominator chain')
    if evidence.get('evidence_kind') not in ('source_producer_code','independent_net_bio_interaction_identity'):raise ValueError('Unsupported denominator evidence')
    return value


def finite_or_missing(value):
    if value is None:return math.nan
    value=float(value)
    if math.isinf(value):raise ValueError('Infinite source measurement')
    return value


def normalize_sample(*,source_force_vertical_N,source_interaction_torque_units_unknown,source_net_moment_Nm_kg,source_biological_moment_Nm_kg,joint,exo_state,participant,reported_model=None,verified_source_denominator=None):
    if joint not in ('hip_flexion','knee_flexion','ankle_dorsiflexion'):raise ValueError('Unknown canonical joint')
    if exo_state not in ('powered','worn_unpowered','no_exo'):raise ValueError('Unknown source actuator state')
    participant_kg=validated_mass(participant)
    if participant_kg is not None and participant.get('status')!='source_participant_mass_bound':raise ValueError('Unbound participant mass')
    model_kg=validated_mass(reported_model)
    denominator=source_denominator(verified_source_denominator)
    force=finite_or_missing(source_force_vertical_N);interaction=finite_or_missing(source_interaction_torque_units_unknown)
    net=finite_or_missing(source_net_moment_Nm_kg);bio=finite_or_missing(source_biological_moment_Nm_kg)
    sign=1. if joint=='hip_flexion' else -1.
    canonical_net=sign*net*denominator/participant_kg if participant_kg is not None and denominator is not None else math.nan
    canonical_bio=sign*bio*denominator/participant_kg if participant_kg is not None and denominator is not None else math.nan
    if exo_state=='no_exo':assistance=0.
    else:assistance=math.nan  # README does not define actual torque_interaction units.
    return {'source_force_vertical_N':force,'source_interaction_torque_units_unknown':interaction,'source_net_moment_Nm_kg':net,'source_biological_moment_Nm_kg':bio,
            'derived_source_reported_model_weight_force':force/(model_kg*9.81) if model_kg is not None else math.nan,
            'canonical_force_vertical_BW':force/(participant_kg*9.81) if participant_kg is not None else math.nan,
            'canonical_assistance_moment_Nm_kg':assistance,'canonical_net_moment_Nm_kg':canonical_net,'canonical_biological_moment_Nm_kg':canonical_bio,
            'normalization_policy':'canonical participant-without-exoskeleton mass; source normalized moments retained separately; no double division',
            'withheld_reasons':(['participant_mass_unresolved'] if participant_kg is None else [])+(['source_joint_moment_denominator_unverified'] if denominator is None else [])+(['source_interaction_units_unverified'] if exo_state!='no_exo' else [])}
