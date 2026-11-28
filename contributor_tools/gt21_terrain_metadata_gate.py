"""Strict source-label metadata gate for future GT21 combined terrain pilots.

No files or scientific arrays are loaded here. Callers must independently select
one source label over the whole observation and bind raw terrain and output to
source/output hashes. This does not establish event coverage or force/COP validity.
"""
from decimal import Decimal, ROUND_HALF_UP
import json
import math

BASE = {
    'rampascent': ('ramp', 'incline_walking', 'ramp_ascent'),
    'rampdescent': ('ramp', 'decline_walking', 'ramp_descent'),
    'stairascent': ('stair', 'stair_ascent', 'stair_ascent'),
    'stairdescent': ('stair', 'stair_descent', 'stair_descent'),
}


def expected_metadata(mode, source_label, raw_terrain):
    """Raw rampIncline is degrees; raw stairHeight is inches in source MAT."""
    if (not isinstance(raw_terrain,(int,float)) or isinstance(raw_terrain,bool)
            or not math.isfinite(raw_terrain) or raw_terrain <= 0):
        raise ValueError('Positive finite raw source terrain is required')
    transition = None
    if source_label.startswith('walk-'):
        label=source_label[5:];transition='into'
    elif source_label.endswith('-walk'):
        label=source_label[:-5];transition='out'
    else:label=source_label
    if label not in BASE or BASE[label][0] != mode:
        raise ValueError('Unsupported source label for terrain mode')
    _, task, identifier=BASE[label]
    value=Decimal(str(raw_terrain))
    if mode=='ramp':
        value=value.quantize(Decimal('.1'),rounding=ROUND_HALF_UP)
        if label=='rampdescent':value=-value
        metadata={'incline_deg':float(value),'surface':'overground'}
        task_id=('incline_' if label=='rampascent' else 'decline_')+f'{value:.1f}deg'
    else:
        value=(value*Decimal('.0254')).quantize(Decimal('.001'),rounding=ROUND_HALF_UP)
        metadata={'step_height_m':float(value),'surface':'stairs'}
        task_id=task
    if value==0:
        raise ValueError('Terrain rounds to zero at exported precision')
    if transition:
        metadata.update(gait_transition=True,
            transition_from='level_walking' if transition=='into' else task,
            transition_to=task if transition=='into' else 'level_walking')
        task_id='walk_to_'+identifier if transition=='into' else identifier+'_to_walk'
        task='transition'
    return {'task':task,'task_id':task_id,'task_info':metadata}


def check_curve_metadata(rows, *, mode, source_labels, raw_terrain):
    """Check all 150 rows; labels must come from a full-window source selection."""
    if not source_labels or len(set(source_labels))!=1:
        raise ValueError('Missing or mixed source labels')
    expected=expected_metadata(mode,source_labels[0],raw_terrain)
    if len(rows)!=150:raise ValueError('Expected complete inclusive 150-row observation')
    for row in rows:
        if row['task']!=expected['task'] or row['task_id']!=expected['task_id']:
            raise ValueError('Task identity disagrees with source label')
        info=json.loads(row['task_info']) if isinstance(row['task_info'],str) else row['task_info']
        if not isinstance(info,dict):raise ValueError('Task metadata must be an object')
        if info.get('fallback') or info.get('labels_missing'):
            raise ValueError('Source terrain labels cannot be replaced by fallback')
        for key,value in expected['task_info'].items():
            actual=info.get(key)
            if isinstance(value,float):
                if (not isinstance(actual,(float,int)) or isinstance(actual,bool)
                        or not math.isfinite(actual) or abs(actual-value)>1e-10):
                    raise ValueError('Terrain geometry disagrees with raw source')
            elif isinstance(value,bool):
                if actual is not value:raise ValueError('Transition flag must be explicit boolean')
            elif actual!=value:raise ValueError('Terrain transition or surface metadata disagrees')
        if expected['task']!='transition' and any(key in info for key in ('transition_from','transition_to','gait_transition')):
            raise ValueError('Steady terrain mislabeled as transition')
    return {'status':'terrain_task_metadata_checked_unreviewed','rows':150,
        'source_label':source_labels[0],'expected':expected,'scientific_approval':False,
        'source_identity_and_hashes_checked':False,'event_coverage_checked':False,'force_cop_checked':False}
