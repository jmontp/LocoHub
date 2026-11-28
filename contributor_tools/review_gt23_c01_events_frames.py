"""GT23-C01: GaTech 2023 event definitions and physical frames, per activity.

Steps (run one at a time):
  report  Metadata only. Builds docs/quality/audits/gt23-c01-events-and-frames.json from the
          publisher README copy, the paper XML, the publisher Code.zip, the converters, the existing
          parsing-field inventory (gt23_task_coverage_review_20261020/source_coverage.json, interval
          counts per field, no times) and prior audits. Reads no source arrays.
  sheet   Builds review_sheets/GT23-C01/ and review_sheets/D-GT23-C01-1/ from that JSON only.
  plan    Prints the seeded probe selection (inventory metadata only).
  probe   Bounded source probe (parsing interval values, GroundFrame_GRFs vertical columns and
          Activity_Flag for a seeded sample). NOT run by GT23-C01: it needs the serial numerical
          slot and must go through contributor_tools/guarded_launcher.py.

Publisher task grouping is computed by porting Code.zip/GroupTasks.m (regexprep, in order).
Activity = publisher base task name (README "TASK DESCRIPTIONS"); 19 of the 26 base tasks have
Segmentation/<subject>/*_parsing.mat files, 7 have none (README line 278).
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.common.review_sheet import page  # noqa: E402

TASK_ID = 'GT23-C01'
DECISION_ID = 'D-GT23-C01-1'
SEED = 20261031
REPORT = ROOT / 'docs/quality/audits/gt23-c01-events-and-frames.json'
SHEETS = ROOT / 'review_sheets'
SOURCE = Path('/mnt/s/locomotion_data/Gtech_2023')
REVIEW = ROOT / 'converted_datasets/reconversion_v2/swarm_backlog_20261021'
INPUTS = {
    'readme': ROOT / 'docs/quality/audits/source_evidence/gt23/publisher-readme.txt',
    'paper_xml': REVIEW / 'gt23_paper_fulltext.xml',
    'code_zip': REVIEW / 'gt23_publisher_source_review_20261021/Code.zip',
    'parsing_fields': ROOT / 'converted_datasets/reconversion_v2/gt23_task_coverage_review_20261020/source_coverage.json',
    'inventory': ROOT / 'converted_datasets/reconversion_v2/gt23_full_native_batch_20261020/inventory.json',
    'time_converter': ROOT / 'contributor_tools/conversion_scripts/Gtech_2023/convert_gtech_2023_time_to_parquet.m',
    'phase_converter': ROOT / 'contributor_tools/conversion_scripts/Gtech_2023/convert_gtech_phase_to_parquet.m',
    'task_parser': ROOT / 'contributor_tools/conversion_scripts/Gtech_2023/parse_gtech_activity_matlab.m',
    'sit_stand_fallback': ROOT / 'contributor_tools/conversion_scripts/Gtech_2023/utilities/segment_sit_stand_transitions.m',
    'jump_fallback': ROOT / 'contributor_tools/conversion_scripts/Gtech_2023/utilities/segment_jump_cycles.m',
    'core04_gt23_pilot': ROOT / 'docs/quality/audits/core04-gt23-pilot.json',
    'sign_survey': ROOT / 'docs/quality/audits/sign-conventions-source-survey.json',
    'joint_sign_audit': ROOT / 'docs/quality/audits/gt23-joint-sign-and-segment-evidence.json',
    'known_pose_audit': ROOT / 'docs/quality/audits/gt23-known-pose-preparation.json',
    'source_frame_audit': ROOT / 'docs/quality/audits/gt23-source-frame-review.json',
    'force_frame_audit': ROOT / 'docs/quality/audits/gt23-global-force-frame-correction.json',
    'cop_joint_audit': ROOT / 'docs/quality/audits/gt23-cop-and-joint-coordinate-review.json',
    'transform_container_audit': ROOT / 'docs/quality/audits/gt23-oversized-transform-container-review.json',
    'full_scope_audit': ROOT / 'docs/quality/audits/gt23-full-source-scope.json',
    'c02_units': ROOT / 'docs/quality/audits/gt23-c02-moment-units.json',
    'c03_mass': ROOT / 'docs/quality/audits/gt23-c03-normalizing-mass.json',
    'c04_divisors': ROOT / 'docs/quality/audits/gt23-c04-trial-divisors.json',
    'data_reference': ROOT / 'docs/reference/index.md',
}

# GroupTasks.m lines 22-30, verbatim order (Code.zip).
GROUPS = ['walk', 'incline', 'decline', 'stair_ascent', 'stair_descent', 'walk_backwards',
          'calisthenics', 'cutting', 'meander', 'ball_toss', 'jump_across', 'jump_in_place', 'lift_weight', 'lunge',
          'misc', 'push_pull', 'run', 'sit_stand', 'stand', 'start_stop', 'step_over', 'curb', 'step_ups', 'squats',
          'tug_of_war', 'turn', 'twister', 'weighted_walk']
EXPRESSIONS = ['normal.*([0-1]-[0-9]|shuffle)', 'incline.*up', 'incline.*down',
               'stairs.*up', 'stairs.*down', 'walk_backward', '(normal.*skip)|(.+?butt-kicks)|(.+?high-knees)|(tire_run)',
               'cutting', 'meander', 'ball_toss', '(jump.*fb)|(jump.*lateral)|(side_shuffle)', 'jump.*(hop|vertical|90|180)',
               'lift_weight', 'lunges', '(.+?heel-walk)|(.+?toe-walk)', 'push', 'normal.*2-[0-5]', 'sit_to_stand', 'poses',
               'start_stop', 'obstacle_walk', 'curb_(up|down)', 'step_up', 'squat', 'tug_of_war', 'turn_and_step', 'twister',
               'weighted_walk']


def publisher_group(name):
    """Port of GroupTasks.m: regexprep(name, [expr '.*'], group) applied in order."""
    for expression, group in zip(EXPRESSIONS, GROUPS):
        name = re.sub(expression + '.*', group, name)
    return name


# README "SEGMENTATION DETAILS" (lines 271-278) and paper Methods, Ground reaction forces.
SEGMENTATION = {
    'heel_strike': {'readme_line': 272, 'definition': 'Consecutive heel strikes of one leg; heel strike = 20 N rising '
                    'threshold on the force plates (paper: 50 N for treadmill running). Interval = one stride of that leg.',
                    'observation_type': 'individual_cycle', 'event_source': 'force plate'},
    'skip': {'readme_line': 273, 'definition': 'Heel strike to heel strike, ignoring the brief mid-stride heel strike of '
             'skipping.', 'observation_type': 'individual_cycle', 'event_source': 'force plate'},
    'hop': {'readme_line': 274, 'definition': '20 N foot-contact threshold (hop cycle).',
            'observation_type': 'individual_cycle', 'event_source': 'force plate'},
    'trunk_velocity': {'readme_line': 275, 'definition': 'Trunk velocity crossing 0.5 m/s, debounced and manually '
                       'verified. Task window, not a leg event.', 'observation_type': 'transfer', 'event_source': 'markers'},
    'plate_pass': {'readme_line': 276, 'definition': 'Toe-off of the step before the force plates to heel strike of the '
                   'first step off them; automatic marker-velocity check, then manual adjustment. Phase 0 is a toe-off, '
                   'not a heel strike.', 'observation_type': 'transfer', 'event_source': 'markers, manual'},
    'pelvis_velocity': {'readme_line': 277, 'definition': 'Pelvis velocity crossing 0.5 m/s, debounced and manually '
                        'verified. Task window, not a leg event.', 'observation_type': 'transfer', 'event_source': 'markers'},
    'none': {'readme_line': 278, 'definition': 'Not segmented by the publisher.', 'observation_type': 'continuous_recording',
             'event_source': 'none'},
}

# Forward-axis classes. 'treadmill_forward' and 'overground_forward' need only the measured heading;
# every other class needs D-GT23-C01-1 (what +x means when the person is not walking forward).
FORWARD = {
    'treadmill_forward': 'Fixed heading on the treadmill; facing equals travel. +x derivable from markers '
                         '(CORE-04 v2 pelvis facing: braking/propulsion and CoP progression pass on level, incline '
                         'and decline in AB01/AB06/AB13). Not stated by the publisher.',
    'overground_forward': 'Facing equals travel while walking forward; heading measured per stride from markers. '
                          'CORE-04 stair strides: CoP progression and braking/propulsion checks were "unknown".',
    'backward_travel': 'Facing is opposite to travel; the data reference defines +x as "the walking direction" while '
                       'viewing the person "facing right". Needs D-GT23-C01-1.',
    'heading_changes': 'The pelvis heading turns within the window; one forward axis per window is undefined. '
                       'Needs D-GT23-C01-1.',
    'no_forward_travel': 'No forward walking direction (in place, sideways or transfer). Needs D-GT23-C01-1.',
}

# Base task -> (README description line, setting stated by README, segmentation key, forward class, notes).
ACTIVITIES = {
    'ball_toss': (152, 'not stated', 'pelvis_velocity', 'no_forward_travel', []),
    'curb_down': (157, 'not stated', 'pelvis_velocity', 'overground_forward',
                  ['AB02 has split files: curb_down_1_left_parsing.mat holds <leg>_right fields and _right holds '
                   '<leg>_left fields (filename suffix and field type disagree; unresolved).']),
    'curb_up': (159, 'not stated', 'pelvis_velocity', 'overground_forward', ['AB02 split files as for curb_down.']),
    'cutting': (161, 'not stated (jog/run into a sharp turn)', 'plate_pass', 'heading_changes', []),
    'dynamic_walk': (167, 'treadmill', 'heel_strike', 'treadmill_forward',
                     ['Heel walk and toe walk are publisher group "misc"; butt kicks and high knees "calisthenics".']),
    'incline_walk': (173, 'treadmill', 'heel_strike', 'treadmill_forward',
                     ['Inclines carry left-leg intervals only, declines right-leg only (field inventory). README line 93 '
                      'says the right plate is missing except for declines; that the left plate is missing in declines is '
                      'inferred, not stated.']),
    'jump': (179, 'not stated', 'pelvis_velocity', 'no_forward_travel',
             ['jump_1_hop uses the 20 N contact rule (README 274); all other jumps pelvis velocity.',
              '90 and 180 deg jumps turn within the window (heading_changes).']),
    'lift_weight': (188, 'not stated', 'trunk_velocity', 'no_forward_travel', []),
    'lunges': (198, 'not stated', 'pelvis_velocity', 'no_forward_travel', []),
    'meander': (207, 'overground', 'none', 'heading_changes', []),
    'normal_walk': (209, 'treadmill', 'heel_strike', 'treadmill_forward',
                    ['2-0 and 2-5 are running: GroupTasks "run", plotting script titles "Running 2.0/2.5 m/s", paper '
                     'Table 1 run 2.0-2.5 m/s, 50 N threshold. LocoHub labels them level_walking.',
                     'skip uses the skip rule (README 273), publisher group "calisthenics"; LocoHub labels it level_walking.',
                     'README line 272 lists "shuffling" among heel-strike tasks without saying which: read here as '
                     'normal_walk_1_shuffle (0.4 m/s, GroupTasks "walk", left-leg intervals only), not side_shuffle.',
                     'AB05 and AB10 2-0/2-5 parsing files are empty; README lines 108 and 139: no valid running trials.',
                     'Running files carry both legs (24-27 intervals each) although README line 93 says the right '
                     'treadmill plate is missing; the right-leg event source is unchecked.']),
    'obstacle_walk': (218, 'treadmill', 'none', 'treadmill_forward', []),
    'poses': (220, 'not stated', 'none', 'no_forward_travel', []),
    'push': (222, 'not stated', 'none', 'no_forward_travel', []),
    'side_shuffle': (224, 'not stated', 'pelvis_velocity', 'no_forward_travel',
                     ['Travel is sideways.', 'README line 272 "shuffling" (heel-strike rule) is read as normal_walk '
                      'shuffle; side_shuffle files hold identical left/right typed window counts (150/150), consistent '
                      'with pelvis-velocity windows (README 277). Ambiguity unresolved until probe P1.']),
    'sit_to_stand': (226, 'not stated', 'pelvis_velocity', 'no_forward_travel',
                     ['Fields <leg>_sitting / <leg>_standing name the destination posture (types per README line 51).']),
    'squats': (231, 'not stated', 'pelvis_velocity', 'no_forward_travel', []),
    'stairs': (235, 'not stated', 'heel_strike', 'overground_forward',
               ['One interval per leg per pass (plate-captured strides only).',
                'AB01 stair-descent parsing files (5) are empty; no README explanation.',
                'Paper Table 1: stair rise 152 mm. LocoHub writes height_m 0.15 and calls the pass index step_number.']),
    'start_stop': (247, 'overground force plates', 'none', 'overground_forward', ['Only AB10-AB13 (README line 91).']),
    'step_ups': (249, 'not stated', 'pelvis_velocity', 'overground_forward',
                 ['AB02 step_ups deleted (README line 99). LocoHub writes height_m 0.20 (not found in local sources).']),
    'tire_run': (253, 'overground', 'plate_pass', 'overground_forward', []),
    'tug_of_war': (255, 'not stated', 'none', 'no_forward_travel', []),
    'turn_and_step': (257, 'not stated', 'pelvis_velocity', 'heading_changes',
                      ['Conflict: README line 277 implies pelvis-velocity windows; publisher plotting script lines 113-114 '
                       'title the curves "segmented by toe off". Left/right interval counts differ within files (see counts), '
                       'which whole-body pelvis windows would not produce. Event definition unresolved.']),
    'twister': (261, 'not stated', 'none', 'no_forward_travel', []),
    'walk_backward': (263, 'treadmill', 'heel_strike', 'backward_travel', []),
    'weighted_walk': (268, 'treadmill', 'heel_strike', 'treadmill_forward',
                      ['README line 268: 1.0 m/s; publisher plotting script line 8 titles it "1.25 m/s". Speed unresolved.']),
}

# Sign rule B (docs/reference/index.md, Signs and frames; D-UM21-C03-1 = B) applied to GT23 source columns.
JOINT_SIGNS = {
    'hip_flexion_r/l (angle, velocity, moment)': {'multiplier': 1, 'canonical': 'hip_flexion_*'},
    'knee_angle_r/l (angle, velocity, moment)': {'multiplier': -1, 'canonical': 'knee_flexion_*'},
    'ankle_angle_r/l (angle, velocity, moment)': {'multiplier': 1, 'canonical': 'ankle_dorsiflexion_*'},
    'Joint_Powers hip/knee/ankle': {'multiplier': 1, 'canonical': 'power (moment x velocity, unchanged by the knee negation)'},
}

CORE04_CONDITIONS = {'normal_walk': 'level 1.2 m/s', 'incline_walk': 'incline 5/10 deg, decline 5/10 deg',
                     'stairs': 'stair ascent, stair descent'}


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def base_task(parsing):
    return re.split(r'_\d+(?:_|$)', parsing.replace('_parsing.mat', ''))[0]


def condition_counts(fields):
    """Interval counts per (condition, leg), following expand_parsing_conditions (phase converter)."""
    out = defaultdict(dict)
    for name, info in fields.items():
        leg, _, condition = name.partition('_')
        out[condition][leg] = info['intervals']
    return out


def field_summary(records):
    tasks = defaultdict(lambda: {'files': 0, 'empty_files': [], 'subjects': set(), 'fields': Counter(),
                                 'intervals_left': 0, 'intervals_right': 0, 'phase_kept': 0, 'phase_dropped': 0,
                                 'files_left_ne_right': 0, 'files_one_leg_only': 0, 'time_windows': 0})
    for record in records:
        task = tasks[record['task']]
        task['files'] += 1
        task['subjects'].add(record['subject'])
        fields = record['interval_fields']
        if not fields:
            task['empty_files'].append(f"{record['subject']}/{record['parsing']}")
            continue
        task['time_windows'] += 1  # time export: one envelope per parsing file
        task['fields'].update(list(fields))
        differs = one_leg = False
        for legs in condition_counts(fields).values():
            left, right = legs.get('left', 0), legs.get('right', 0)
            task['intervals_left'] += left
            task['intervals_right'] += right
            # Phase converter (lines 452-490) keeps the leg with more rows (tie: earlier first start).
            task['phase_kept'] += max(left, right)
            task['phase_dropped'] += min(left, right)
            differs |= left != right
            one_leg |= (left == 0) != (right == 0)
        task['files_left_ne_right'] += differs
        task['files_one_leg_only'] += one_leg
    return tasks


def report():
    for path in INPUTS.values():
        if not path.exists():
            raise SystemExit(f'Missing input: {path}')
    coverage = json.loads(INPUTS['parsing_fields'].read_text())
    inventory = json.loads(INPUTS['inventory'].read_text())['records']
    if coverage['parsing_windows'] != 787 or len(inventory) != 787:
        raise SystemExit('Parsing inventory changed; re-derive before reporting')
    readme = INPUTS['readme'].read_text(encoding='utf-8').splitlines()
    with zipfile.ZipFile(INPUTS['code_zip']) as archive:
        plotting = archive.read('example_script_plotting.m').decode('utf-8').splitlines()
    fields = field_summary(coverage['records'])
    raw_dirs = sorted(p for p in (SOURCE / 'RawData').glob('AB*/CSV_Data/*') if p.is_dir())  # directory names only
    raw_by_task = defaultdict(set)
    recordings_by_task = Counter()
    for path in raw_dirs:
        task = re.split(r'_\d+(?:_|$)', path.name)[0]
        raw_by_task[task].add(path.parts[-3])
        recordings_by_task[task] += 1
    event_recordings = defaultdict(set)  # recordings with at least one non-empty parsing file
    for r in inventory:
        if r['has_intervals']:
            event_recordings[base_task(r['parsing'])].add((r['subject'], r['recording']))
    segmented_recordings = Counter({task: len(recs) for task, recs in event_recordings.items()})
    groups = defaultdict(Counter)
    for record in coverage['records']:
        groups[record['task']][publisher_group(record['parsing'].replace('_parsing.mat', ''))] += 1
    for task in ('meander', 'obstacle_walk', 'poses', 'push', 'start_stop', 'tug_of_war', 'twister'):
        groups[task][publisher_group(task + '_1')] += 1

    rows = []
    for task, (readme_line, setting, seg_key, forward_key, notes) in sorted(ACTIVITIES.items()):
        if not readme[readme_line - 1].startswith(task + ':'):
            raise SystemExit(f'README line {readme_line} does not describe {task}')
        seg = SEGMENTATION[seg_key]
        f = fields.get(task)
        segmented = f is not None
        rows.append({
            'activity': task,
            'readme_description': {'line': readme_line, 'text': readme[readme_line - 1].strip()},
            'setting_stated': setting,
            'recordings': recordings_by_task[task], 'subjects_with_recordings': len(raw_by_task[task]),
            'recordings_with_parsing': segmented_recordings.get(task, 0),
            'publisher_groups': dict(groups[task]),
            'events': {
                'segmented_by_publisher': segmented,
                'definition': seg['definition'], 'readme_line': seg['readme_line'], 'event_source': seg['event_source'],
                'parsing_files': f['files'] if f else 0,
                'parsing_subjects': len(f['subjects']) if f else 0,
                'empty_parsing_files': f['empty_files'] if f else [],
                'interval_fields': dict(sorted(f['fields'].items())) if f else {},
                'intervals_left': f['intervals_left'] if f else 0,
                'intervals_right': f['intervals_right'] if f else 0,
                'files_with_unequal_left_right_counts': f['files_left_ne_right'] if f else 0,
                'files_with_one_leg_only': f['files_one_leg_only'] if f else 0,
                'toe_off_in_source_files': 'no (parsing intervals hold start/end only); derivable from the 20 N plate '
                                           'threshold only where that leg has plate data (probe P2)',
                'proposed_observation_type': seg['observation_type'],
                'valid_status': ('no_source_events' if not segmented else
                                 'conflicting_definition' if task == 'turn_and_step' else
                                 'source_defined_unverified'),
            },
            'phase_converter_interval_use': {'kept': f['phase_kept'], 'dropped_other_leg': f['phase_dropped']} if f else None,
            'time_converter_windows': f['time_windows'] if f else 0,
            'frames': {
                'vertical_grf': 'supported: GroundFrame_GRFs Y up (README line 30); positive support (GT23-C02 force-plate '
                                'body mass matches README in 5/5 subjects)',
                'horizontal_grf_and_cop': {'class': forward_key, 'status': FORWARD[forward_key]},
                'virtual_insoles': 'calcn_l/calcn_r body frames (README line 38; paper Methods, Virtual insoles); +x toward '
                                   'the toe supported in walking only (GT23-C02: CoP moves forward in 253/254 stances)',
                'joint_sagittal': ('source-supported for all activities (same OpenSim coordinates: author Plot_3x3_plots.m '
                                   '155-160 with paper Fig. 5 caption; model +Z axes); data-reproduced only in CORE-04 '
                                   + (f'conditions: {CORE04_CONDITIONS[task]}' if task in CORE04_CONDITIONS else
                                      'gait conditions, not in this activity')),
                'joint_non_sagittal': 'not adopted by the data reference; keep source sign (hip adduction/rotation, subtalar)',
                'segment_angles': 'unsupported: no publisher pelvis/segment angle; Link_Angle.csv is locally generated',
                'kinetics': 'N*m/kg and W/kg as published (GT23-C02); divisor not the own mass in 9 of 12 subjects '
                            '(GT23-C03); per-trial rescale only for matched trials, D-GT23-C04-1 open',
            },
            'notes': notes,
        })

    totals = {
        'activities': len(rows),
        'segmented_activities': sum(r['events']['segmented_by_publisher'] for r in rows),
        'recordings': sum(r['recordings'] for r in rows),
        'recordings_with_parsing': sum(r['recordings_with_parsing'] for r in rows),
        'parsing_files': sum(r['events']['parsing_files'] for r in rows),
        'empty_parsing_files': sum(len(r['events']['empty_parsing_files']) for r in rows),
        'intervals_left': sum(r['events']['intervals_left'] for r in rows),
        'intervals_right': sum(r['events']['intervals_right'] for r in rows),
        'phase_kept': sum((r['phase_converter_interval_use'] or {}).get('kept', 0) for r in rows),
        'phase_dropped': sum((r['phase_converter_interval_use'] or {}).get('dropped_other_leg', 0) for r in rows),
        'phase_dropped_cycles': sum(r['phase_converter_interval_use']['dropped_other_leg'] for r in rows
                                    if r['events']['proposed_observation_type'] == 'individual_cycle'),
        'phase_dropped_hop_contacts': sum(min(legs.get('left', 0), legs.get('right', 0))
                                          for rec in coverage['records'] if '_hop' in rec['parsing']
                                          for legs in condition_counts(rec['interval_fields']).values()),
    }
    totals['recordings_without_parsing_files'] = totals['recordings'] - len({(r['subject'], r['recording']) for r in inventory})
    totals['recordings_without_source_intervals'] = totals['recordings'] - totals['recordings_with_parsing']
    by_forward = defaultdict(list)
    for r in rows:
        by_forward[r['frames']['horizontal_grf_and_cop']['class']].append(r['activity'])

    out = {
        'task_id': TASK_ID,
        'status': 'review',
        'scientific_approval': False,
        'scope': 'All 26 GaTech 2023 publisher base tasks ("activities"): the 19 with publisher segmentation files '
                 '(the backlog question\'s 19) plus 7 the publisher did not segment. Metadata, documentation and code '
                 'only; no source arrays were read.',
        'generated_by': 'contributor_tools/review_gt23_c01_events_frames.py report',
        'inputs_sha256': {str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p): digest(p)
                          for p in INPUTS.values() if p.is_file()},
        'code_sha256': {'contributor_tools/review_gt23_c01_events_frames.py': digest(Path(__file__))},
        'reads': 'Publisher README copy, paper XML, Code.zip members, converter sources, prior audits, the parsing-field '
                 'inventory (interval counts per field; produced 2026-10-20 by contributor_tools/audit_probes/2026_10_20/'
                 'check_gt23_task_coverage.py), inventory.json and RawData directory names. During exploration the first '
                 '400 bytes of one AB01 normal_walk_1 GroundFrame_GRFs.csv and Activity_Flag.csv were printed to read '
                 'column headers; no values are used as evidence.',
        'totals': totals,
        'forward_axis_classes': {k: {'activities': v, 'status': FORWARD[k]} for k, v in sorted(by_forward.items())},
        'activities': rows,
        'established': [
            'Activity definitions and segmentation rules: README lines 144-278; paper Methods (Ground reaction forces: 20 N '
            'steps, 50 N for treadmill running, feet assigned by marker/CoP matching; inverse dynamics NaN off plates).',
            'Parsing file layout: README line 51 (rows = cycles, columns start/end time; optional types -> right_<type>, '
            'left_<type>). Field inventory confirms <leg>[_<type>] fields in all 778 non-empty files; 9 files are empty '
            '(AB05/AB10 running: README 108, 139; AB01 five stair descents: unexplained).',
            'Activity_Flag.csv: per-sample on/off for left and right (paper Table 3; README line 29). Neither converter reads it.',
            'Vertical GRF: Y up, positive support (README line 30; GT23-C02).',
            'Horizontal GRF and global CoP: OpenSim global X/Z, which turn with the person (paper Table 3; '
            'gt23-source-frame-review). Converters assign ForceX/ForceZ directly to anterior/lateral (time converter '
            'lines 501-506; phase converter 794-835): unsupported.',
            'Sideways sign: outward per leg (data reference, Signs and frames; D-GT21-C01-1 = B), once +x is known.',
            'Converter CoP: calcn body frame with calcn origin (gt23-cop-and-joint-coordinate-review). The data reference '
            'defines CoP in the ground frame (+x forward, +y up); a foot-fixed frame rotates with the foot, so the '
            'current cop_* mapping is a frame mismatch, not only an origin note.',
            'Joint sagittal signs under rule B: hip +1, knee -1, ankle +1 for angle, velocity and moment; powers +1 '
            '(sign survey; gt23-joint-sign-and-segment-evidence; CORE-04 GT23 pilot 0 wrong of 141 applied/suggested, '
            'independent rerun AB10/AB11 0 wrong).',
            'Units and mass: GT23-C02, GT23-C03, GT23-C04 (kinetics blocked by D-GT23-C04-1).',
        ],
        'converter_findings': [
            {'id': 'F1', 'where': 'convert_gtech_phase_to_parquet.m lines 452-490',
             'finding': f"Keeps only the leg with more intervals per condition (tie: earlier start) and drops the other "
                        f"leg: {totals['phase_dropped']} of {totals['intervals_left'] + totals['intervals_right']} intervals, "
                        f"of which {totals['phase_dropped_cycles']} are per-leg gait cycles (running, stairs) and "
                        f"{totals['phase_dropped_hop_contacts']} are hop contact intervals (README 274, 20 N contact; jump "
                        "is classed as task windows, so these are not in the gait-cycle count). The rest are task-window "
                        "activities whose left/right windows may be identical (probe P1); there ipsi is arbitrary.",
             'fix': 'Emit each leg\'s source intervals with its reference_side; for whole-body windows identical on '
                    'both legs (probe P1) emit reference_side none (contract: ipsi/contra name roles).'},
            {'id': 'F2', 'where': 'convert_gtech_2023_time_to_parquet.m lines 320-357',
             'finding': 'One window per parsing file = envelope [min start, max end] over every interval field, so '
                        'conditions in one file (sitting/standing, forward/backward, left/right-lead) are merged into one '
                        f"window; reference leg = first start. {totals['recordings_without_source_intervals']} recordings "
                        f"carry no source intervals ({totals['recordings_without_parsing_files']} without parsing files, "
                        f"{totals['recordings_without_source_intervals'] - totals['recordings_without_parsing_files']} with "
                        "only empty ones) and are never exported.",
             'fix': 'One observation per source interval (or per contiguous cycle chain), labelled by its field; '
                    'continuous_recording for recordings without source intervals (after exclusion review).'},
            {'id': 'F3', 'where': 'convert_gtech_phase_to_parquet.m lines 217-233, 498-579; utilities/segment_*',
             'finding': 'Fallback sit/stand and jump segmentation with LocoHub thresholds (600/400 N absolute, 25 deg/s) '
                        'replaces source events when a file lacks left/right fields. Every sit_to_stand and jump file '
                        'has source fields, so it should never fire; any output it produced is not source-defined.',
             'fix': 'Remove the fallback; fail closed.'},
            {'id': 'F4', 'where': 'parse_gtech_activity_matlab.m lines 22-39',
             'finding': 'normal_walk 2-0/2-5 (running per GroupTasks, plotting script and paper) and skip are labelled '
                        'level_walking.', 'fix': 'Label from the publisher grouping (run; skip as its own variant family).'},
            {'id': 'F5', 'where': 'parse_gtech_activity_matlab.m lines 96-105, 240, 245, 250',
             'finding': 'Invented task_info: stairs height_m 0.15 (paper Table 1: 152 mm), step_number is the pass '
                        'index, curb 0.15 m and step-up 0.20 m not found in local sources.',
             'fix': 'Stair rise 0.152 m citing paper Table 1; rename pass index; drop curb/step-up heights unless '
                    'Supplementary Table 1 states them.'},
            {'id': 'F6', 'where': 'time converter 501-506; phase converter 794-835',
             'finding': 'Global ForceX/ForceZ written as anterior/lateral (known; correction prepared, not run).',
             'fix': 'Heading-projected +x per forward class; other classes per D-GT23-C01-1.'},
        ],
        'unsupported_mappings_left_explicit': [
            'Horizontal GRF and CoP for backward_travel, heading_changes and no_forward_travel activities (D-GT23-C01-1).',
            'Horizontal GRF and CoP for forward classes until heading is measured per stride/window and checked (probe P2 '
            'covers contact only; heading reuse of the CORE-04 adapter is planned).',
            'cop_* in the converter\'s calcn body frame (frame mismatch with the data reference).',
            'Segment and pelvis angles (no publisher channel; local Link_Angle Euler YZX with a +pi/2 pelvis offset; seven '
            'AB02 normal_walk windows have oversized Transforms).',
            'Non-sagittal joint coordinates (no adopted rule).',
            'Moments and powers until D-GT23-C04-1 is answered and rescaling is reviewed.',
            'turn_and_step event definition (README vs plotting script).',
            'AB02 curb filename vs field type; weighted_walk speed (README 1.0 vs plotting 1.25 m/s).',
            'AB07 treadmill recordings (dynamic_walk, incline_walk, normal_walk, walk_backward, weighted_walk, '
            'obstacle_walk) exist in RawData without parsing files; README lines 115-136 say these trials were removed '
            '(zero A/P force). Exclusion disposition needed before any continuous export.',
        ],
        'probe_plan': probe_plan(inventory),
        'native_pilot': {
            'prepared': 'gt23-known-pose-preparation.json: 13 AB01 model poses (neutral, +/-1 deg hip/knee/ankle each side), '
                        'OpenSim marker/body stations; checker contributor_tools/check_gt23_known_pose.py.',
            'status': 'not executed. The reviewed guarded launcher refuses MATLAB/native jobs until a reviewed native '
                      'extension exists (guarded_launcher.py docstring).',
            'what_it_adds': 'Model-level direction of hip/knee/ankle coordinates independent of the author plot code. '
                            'CORE-04 marker tests already reproduced the signs from data in 7 gait conditions, so the '
                            'native pilot is corroborating, not blocking for sagittal signs.',
        },
        'verification_plan': [
            'Contact missingness: per activity and leg, fraction of NaN vertical GRF inside parsing envelopes (P2); '
            'treadmill one-plate rule (README 93) incl. the running both-leg intervals and the decline left plate.',
            'Non-gait activities: whether left/right windows are identical (P1) and whether Activity_Flag on-periods '
            'bound the parsing windows (P3) for squats, sit_to_stand, lift_weight, ball_toss, jumps, lunges, cutting, tire_run.',
            'Heel-strike intervals: interval start equals a 20 N (50 N running) rising crossing on that leg within 1 '
            'sample, and a falling crossing (toe-off) exists inside each interval (P2).',
            'Second agent re-derives the activity table from README lines 144-278, GroupTasks.m and source_coverage.json '
            'without importing this builder.',
        ],
        'limitations': [
            'No source arrays read: event validity is "source_defined_unverified" until probes P1-P3 run.',
            'Paper Supplementary Table 1 (task protocol) is not available locally.',
            'Prior CORE-04 pilot covered 3 subjects and gait conditions only.',
        ],
    }
    REPORT.write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(totals, indent=1))


# ---------------------------------------------------------------- probe (not run by GT23-C01)
PROBE_OUT = ROOT / 'docs/quality/audits/gt23-c01-probe.json'
PER_ACTIVITY = 2
MAX_CSV_BYTES = 64 * 1024 ** 2


def probe_plan(inventory):
    import numpy as np
    eligible = defaultdict(list)
    for record in sorted(inventory, key=lambda r: (r['subject'], r['parsing'])):
        if record['has_intervals']:
            eligible[base_task(record['parsing'])].append(record)
    rng = np.random.default_rng(SEED)
    selection = []
    for task in sorted(eligible):
        picks = rng.permutation(len(eligible[task]))[:PER_ACTIVITY]
        selection += [{'activity': task, 'subject': eligible[task][i]['subject'], 'parsing': eligible[task][i]['parsing'],
                       'recording': eligible[task][i]['recording']} for i in sorted(picks)]
    # Extra seeded picks so P2 always covers the hop contact rule and treadmill running (README 93 vs right-leg events).
    for label, pattern in (('hop', r'_hop_parsing'), ('running', r'normal_walk_1_2-[05]_parsing')):
        pool = [r for r in eligible['jump' if label == 'hop' else 'normal_walk'] if re.search(pattern, r['parsing'])
                and not any(r['parsing'] == x['parsing'] and r['subject'] == x['subject'] for x in selection)]
        pick = pool[int(rng.integers(len(pool)))]
        selection.append({'activity': base_task(pick['parsing']), 'subject': pick['subject'],
                          'parsing': pick['parsing'], 'recording': pick['recording'], 'extra': label})
    return {
        'seed': SEED, 'per_activity': PER_ACTIVITY, 'selection': selection,
        'P1': 'All 787 parsing files (708 KiB total): per condition, left vs right windows identical (max |diff| <= '
              '0.0025 s), consecutive-interval contiguity, duration median; types cell contents.',
        'P2': 'Selected recordings, GroundFrame_GRFs.csv columns time, LForceY_Vertical, RForceY_Vertical only: NaN '
              'fraction per leg inside the parsing envelope; for heel_strike and skip activities and every jump hop file, '
              'rising 20 N (50 N for normal_walk 2-0/2-5) crossing within 1 sample of each interval start, and a falling '
              'crossing inside it. One extra seeded hop file and one extra running file are always included.',
        'P3': 'Selected recordings, Activity_Flag.csv: fraction of flag-on samples inside vs outside the parsing envelope, per leg.',
        'bounds': 'One process, one thread, RLIMIT_AS 768 MiB, CSV files > 64 MiB refused (recorded not_checked), '
                  'csv module, each file read whole into memory under the 64 MiB cap (not streamed), no writes outside '
                  'docs/quality/audits/gt23-c01-probe.json.',
        'launch': 'OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 MPLBACKEND=Agg nice -n 19 ionice -c 3 '
                  'python3 -m contributor_tools.guarded_launcher run <spec running this file with "probe">; '
                  'needs the serial numerical slot.',
        'executed': False,
    }


def _intervals(parsed):
    import numpy as np
    out = {}
    for key, value in parsed.items():
        if key.startswith('_') or not isinstance(value, np.ndarray) or not np.issubdtype(value.dtype, np.number):
            continue
        if value.ndim == 2 and value.shape[1] == 2 and value.size:
            out[key] = np.asarray(value, float)
    return out


def _read_columns(path, wanted):
    import csv
    import numpy as np
    if path.stat().st_size > MAX_CSV_BYTES:
        return None
    with open(path, newline='') as handle:
        reader = csv.reader(handle)
        header = next(reader)
        index = [header.index(w) for w in wanted]
        rows = [[float(row[i]) if row[i] not in ('', 'NaN', 'nan') else np.nan for i in index] for row in reader]
    return np.asarray(rows, float)


def probe():
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 ** 2, 768 * 1024 ** 2))
    import numpy as np
    from scipy.io import loadmat
    if PROBE_OUT.exists():
        raise SystemExit(f'{PROBE_OUT} exists; refusing to overwrite')
    inventory = json.loads(INPUTS['inventory'].read_text())['records']
    plan = probe_plan(inventory)
    p1 = defaultdict(lambda: Counter())
    for record in inventory:
        path = SOURCE / 'Segmentation' / record['subject'] / record['parsing']
        if digest(path) != record['parsing_sha256']:
            raise SystemExit(f'Parsing file changed: {path}')
        parsed = loadmat(path)
        fields = _intervals(parsed)
        counts = p1[base_task(record['parsing'])]
        counts['files'] += 1
        if any(not k.startswith(('left', 'right')) for k in parsed if not k.startswith('_')):
            counts['files_with_non_interval_variables'] += 1
        by_condition = defaultdict(dict)
        for name, values in fields.items():
            leg, _, condition = name.partition('_')
            by_condition[condition][leg] = values
            gaps = values[1:, 0] - values[:-1, 1]
            counts['intervals'] += len(values)
            counts['contiguous_pairs'] += int(np.sum(np.abs(gaps) <= 0.0025))
            counts['pairs'] += max(len(values) - 1, 0)
        for legs in by_condition.values():
            if 'left' in legs and 'right' in legs:
                counts['conditions_both_legs'] += 1
                if legs['left'].shape == legs['right'].shape and np.max(np.abs(legs['left'] - legs['right'])) <= 0.0025:
                    counts['conditions_identical_windows'] += 1
    p23 = []
    for pick in plan['selection']:
        parsed = _intervals(loadmat(SOURCE / 'Segmentation' / pick['subject'] / pick['parsing']))
        folder = SOURCE / 'RawData' / pick['subject'] / 'CSV_Data' / pick['recording']
        entry = dict(pick)
        starts = np.concatenate([v[:, 0] for v in parsed.values()])
        ends = np.concatenate([v[:, 1] for v in parsed.values()])
        t0, t1 = float(starts.min()), float(ends.max())
        grf = _read_columns(folder / 'GroundFrame_GRFs.csv', ['time', 'LForceY_Vertical', 'RForceY_Vertical'])
        flag = _read_columns(folder / 'Activity_Flag.csv', ['time', 'left', 'right'])
        if grf is None or flag is None:
            entry['status'] = 'not_checked_file_too_large'
            p23.append(entry)
            continue
        inside = (grf[:, 0] >= t0) & (grf[:, 0] <= t1)
        entry['nan_fraction'] = {leg: float(np.mean(np.isnan(grf[inside, i]))) for leg, i in (('left', 1), ('right', 2))}
        segment = SEGMENTATION[ACTIVITIES[pick['activity']][2]]
        if segment['observation_type'] == 'individual_cycle' or '_hop' in pick['parsing']:
            threshold = 50.0 if re.search(r'normal_walk_1_2-[05]', pick['parsing']) else 20.0
            dt = float(np.median(np.diff(grf[:, 0])))
            hits = Counter()
            for name, values in parsed.items():
                leg = name.split('_')[0]
                force = np.nan_to_num(grf[:, 1 if leg == 'left' else 2], nan=0.0)
                above = force >= threshold
                rises = grf[1:, 0][above[1:] & ~above[:-1]]
                falls = grf[1:, 0][~above[1:] & above[:-1]]
                for start, end in values:
                    hits['intervals'] += 1
                    hits['start_at_rise'] += bool(rises.size and np.min(np.abs(rises - start)) <= 1.01 * dt)
                    hits['toe_off_inside'] += bool(np.any((falls > start) & (falls < end)))
            entry['heel_strike_check'] = dict(hits, threshold_N=threshold)
        flag_inside = (flag[:, 0] >= t0) & (flag[:, 0] <= t1)
        entry['activity_flag_on_fraction'] = {
            leg: {'inside': float(np.mean(flag[flag_inside, i] > 0)) if flag_inside.any() else None,
                  'outside': float(np.mean(flag[~flag_inside, i] > 0)) if (~flag_inside).any() else None}
            for leg, i in (('left', 1), ('right', 2))}
        entry['status'] = 'checked'
        p23.append(entry)
    out = {'task_id': TASK_ID, 'plan': plan, 'P1': {k: dict(v) for k, v in sorted(p1.items())}, 'P2_P3': p23,
           'code_sha256': digest(Path(__file__)),
           'peak_rss_mib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 'scientific_approval': False}
    PROBE_OUT.write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'P1': out['P1'], 'checked': sum(e['status'] == 'checked' for e in p23)}, indent=1))


# ---------------------------------------------------------------- sheets
def _plt():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 10.5, 'axes.titlesize': 11, 'axes.spines.top': False, 'axes.spines.right': False,
                         'savefig.facecolor': 'white'})
    return plt


def _save(fig, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    fig.clf()


def fig_kept(data, path):
    plt = _plt()
    rows = [r for r in data['activities'] if r['events']['proposed_observation_type'] == 'individual_cycle']
    rows.sort(key=lambda r: r['events']['intervals_left'] + r['events']['intervals_right'])
    names = [r['activity'] for r in rows]
    total = [r['events']['intervals_left'] + r['events']['intervals_right'] for r in rows]
    kept = [r['phase_converter_interval_use']['kept'] for r in rows]
    fig, ax = plt.subplots(figsize=(4.5, 3.2), layout='constrained')
    y = range(len(rows))
    ax.barh(y, total, color='#c9d3dc', label='source, both legs')
    ax.barh(y, kept, color='#24506F', height=0.5, label='kept by phase export')
    ax.set_yticks(list(y), names)
    ax.set_xlabel('cycles in parsing files')
    ax.legend(loc='lower right', frameon=False, fontsize=10)
    _save(fig, path)


def fig_coverage(data, path):
    plt = _plt()
    rows = sorted(data['activities'], key=lambda r: (r['recordings_with_parsing'] > 0, r['recordings']))
    names = [r['activity'] for r in rows]
    with_events = [r['recordings_with_parsing'] for r in rows]
    without = [r['recordings'] - r['recordings_with_parsing'] for r in rows]
    fig, ax = plt.subplots(figsize=(4.5, 7.6), layout='constrained')
    y = range(len(rows))
    ax.barh(y, with_events, color='#24506F', label='with source events')
    ax.barh(y, without, left=with_events, color='#d08a2e', label='no source events')
    ax.set_yticks(list(y), names)
    ax.set_xlabel('recordings')
    ax.legend(loc='lower right', frameon=False, fontsize=10)
    _save(fig, path)


def fig_forward(path):
    """Made-up top view: facing (person) vs travel (arrow) in three activities."""
    plt = _plt()
    from matplotlib.patches import Ellipse, FancyArrow
    fig, ax = plt.subplots(figsize=(4.5, 2.2), layout='constrained')
    cases = [(0.0, 'walking\nforward', (1, 0)), (3.0, 'walking\nbackward', (-1, 0)), (6.0, 'side\nshuffle', (0, 1))]
    for x, label, (dx, dy) in cases:
        ax.add_patch(Ellipse((x, 0), 0.5, 1.0, color='#c9d3dc'))
        ax.add_patch(FancyArrow(x, 0, 0.9, 0, width=0.06, color='#24506F', length_includes_head=True))
        if dy:  # sideways travel, drawn beside the person
            ax.add_patch(FancyArrow(x - 0.6, -0.45, 0, 0.9, width=0.06, color='#d08a2e', length_includes_head=True))
        else:
            ax.add_patch(FancyArrow(x - 0.45 * dx, -0.85, 0.9 * dx, 0, width=0.06, color='#d08a2e',
                                    length_includes_head=True))
        ax.text(x, 0.6, label, ha='center', va='bottom', fontsize=12)
    ax.text(3.3, -1.25, 'blue: facing   orange: travel', ha='center', fontsize=12)
    ax.set_xlim(-0.8, 7.2)
    ax.set_ylim(-1.45, 1.45)
    ax.set_aspect('equal')
    ax.axis('off')
    _save(fig, path)


def sheet():
    data = json.loads(REPORT.read_text())
    t = data['totals']
    out = SHEETS / TASK_ID
    fig_kept(data, out / 'fig1_kept.png')
    fig_coverage(data, out / 'fig2_coverage.png')
    labels = {r['activity']: r['events']['valid_status'] for r in data['activities']}
    chips = [('pass', f"{t['parsing_files']} event files mapped to {t['segmented_activities']} activities"),
             ('pass', 'joint signs from author code, reproduced in 7 walking conditions'),
             ('fail', f"phase export drops {t['phase_dropped_cycles']} gait cycles of the second leg"),
             ('fail', 'time export merges sitting and standing into one window'),
             ('fail', 'running labelled as level walking'),
             ('fail', 'invented curb and step heights'),
             ('unchecked', 'event times against force plates (probe not run)'),
             ('unchecked', 'turn-and-step event definition conflicts' if labels['turn_and_step'] == 'conflicting_definition'
              else 'turn-and-step events')]
    page(out / 'index.html', title='GaTech 2023 events check',
         ask='Look at 2 figures. Reply ok, or say what looks wrong.',
         headline='GaTech 2023 events are source-defined for 19 of 26 activities; converters drop or merge them',
         chips=chips,
         figures=[('fig1_kept.png', 'How many gait cycles does the phase export keep?',
                   'Grey: source cycles, both legs. Blue: kept.', 'Bars per gait activity of source cycles and cycles kept'),
                  ('fig2_coverage.png', 'Which recordings have no source events?',
                   'Orange: never exported.', 'Bars per activity of recordings with and without parsing files')],
         not_shown=['Event times against force plates', 'Heading for forward force', 'Model pose check'],
         reply='ok  |  what looks wrong',
         details=[f'{TASK_ID}. Report: docs/quality/audits/gt23-c01-events-and-frames.json',
                  'Builder: contributor_tools/review_gt23_c01_events_frames.py (report, sheet; probe not run)',
                  f"Totals: {json.dumps(t)}",
                  'Interval counts from source_coverage.json (2026-10-20 field inventory); kept = larger leg per condition, '
                  'the phase converter rule.'])

    dout = SHEETS / DECISION_ID
    fig_forward(dout / 'fig1_forward.png')
    decision = decision_record(data)
    n = decision.pop('counts')
    (dout / 'decision.json').write_text(json.dumps(decision, indent=2) + '\n', encoding='utf-8')
    page(dout / 'index.html', title='Forward axis decision',
         ask='Choose what forward means for GaTech 2023 force and pressure when the person is not walking forward.',
         headline=f"Forward is defined as the walking direction; {n['not_forward_walking']} of 26 activities lack "
                  "one steady forward walk",
         chips=[('pass', 'lab forward and sideways axes turn with the person (paper)'),
                ('pass', 'sideways sign is outward per leg (already decided)')],
         figures=[('fig1_forward.png', 'Where do facing and travel disagree?',
                   'Made-up top views.', 'Three top views: facing and travel arrows for forward walking, backward walking and side shuffle')],
         decision={'question': 'What is forward for force and centre of pressure outside forward walking?',
                   'columns': ['Left out', 'What changes', 'Adapter work', 'Reversible'],
                   # Neutral order: most GT23 activities with forward/sideways values first (26, 13, 11, 0).
                   'rows': [('A · facing', ['windows with no steady facing', '+x = pelvis facing in every activity',
                                            'heading per window', 'yes']),
                            ('B · travel', [f"{n['left_out_travel']} in-place or turning activities",
                                            '+x = travel; backward walking and side shuffle filled, their forward force '
                                            'opposite or sideways to facing', 'travel per window', 'yes']),
                            ('C · forward walking', [f"{n['left_out_walking']} activities incl. meander",
                                                     'forward walking incl. obstacle walk, running, stairs, curbs, step-ups, start-stop, tire run',
                                                     'heading per stride', 'yes']),
                            ('defer', ['all GT23 forward and sideways for now', 'vertical force and joint angles unaffected',
                                       '—', '—'])],
                   'footnote': 'Every option keeps measured lab values.',
                   'recommendation': decision['recommended'] + ', ' + decision['confidence'] + ' confidence: '
                                     + decision['why']},
         not_shown=['Measured heading per stride', 'Other datasets with these activities'],
         reply=f'{DECISION_ID}: A, B, C or defer',
         details=[f'{DECISION_ID} (task {TASK_ID}). Report: docs/quality/audits/gt23-c01-events-and-frames.json '
                  '(forward_axis_classes); decision.json equals the handoff decision',
                  'Builder: contributor_tools/review_gt23_c01_events_frames.py'])


STEADY_NON_FORWARD_TRAVEL = ['walk_backward', 'side_shuffle']  # steady travel not along facing


def decision_record(data):
    classes = data['forward_axis_classes']
    walking = sorted(classes['treadmill_forward']['activities'] + classes['overground_forward']['activities'])
    total = len(data['activities'])
    travel = walking + STEADY_NON_FORWARD_TRAVEL
    counts = {'forward_walking': len(walking), 'not_forward_walking': total - len(walking),
              'travel_steady': len(travel), 'left_out_travel': total - len(travel), 'left_out_walking': total - len(walking)}
    return {
        'id': DECISION_ID, 'task_id': TASK_ID,
        'question': (f"Our sign rule defines forward (+x) as the walking direction. In GaTech 2023, "
                     f"{counts['not_forward_walking']} of {total} activities have no single forward walk (backward "
                     "walking, side shuffle, squats, sit-to-stand, lifts, jumps, lunges, turns, cutting, meander and "
                     "others). What should forward mean there for forward and sideways ground force and centre of pressure?"),
        'options': [
            {'key': 'A', 'label': "The person's facing direction in every activity",
             'consequence': 'Forward and sideways force and pressure filled for all 26 activities from pelvis facing '
                            'measured per window; windows without a steady facing left out; the sign-rule wording is '
                            'extended for all datasets. Reversible.'},
            {'key': 'B', 'label': 'The direction of travel (the current rule read literally)',
             'consequence': f"Filled for the {counts['travel_steady']} activities with steady travel: forward walking plus "
                            "backward walking and side shuffle, where forward force is opposite or sideways to the "
                            f"person's facing while joint angles stay in the facing frame. The other "
                            f"{counts['left_out_travel']} (in place or turning) keep lab-axis values only. Reversible."},
            {'key': 'C', 'label': 'Forward walking only',
             'consequence': f"Filled for the {counts['forward_walking']} forward-walking activities ("
                            + ', '.join(walking) + ') from the measured heading; the other '
                            f"{counts['left_out_walking']}, including meander (turning heading), keep lab-axis values "
                            'only. Reversible.'},
        ],
        'options_order': 'By GaTech 2023 activities with forward and sideways values: 26, '
                         f"{counts['travel_steady']}, {counts['forward_walking']}.",
        'recommended': 'C', 'confidence': 'medium',
        'why': 'In forward walking, facing and travel agree, so forward is unambiguous and matches the frame used for '
               'joint angles. Travel splits force from the angle frame in backward walking and side shuffle, and '
               'facing needs a new rule for turning and in-place tasks that would bind every dataset.',
        'check': 'Decision sheet figure: in the backward-walking example the blue facing arrow and the orange travel '
                 'arrow point opposite ways.',
        'cost_of_waiting': 'GaTech 2023 forward and sideways force and pressure stay out of any release (lab values '
                           'kept); vertical force, joint angles and other datasets are unaffected.',
        'decide_before_recommendation': True, 'status': 'open',
        'counts': counts,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('step', choices=['report', 'sheet', 'plan', 'probe'])
    step = parser.parse_args().step
    if step == 'report':
        report()
    elif step == 'sheet':
        sheet()
    elif step == 'plan':
        print(json.dumps(probe_plan(json.loads(INPUTS['inventory'].read_text())['records']), indent=1))
    else:
        probe()


if __name__ == '__main__':
    main()
