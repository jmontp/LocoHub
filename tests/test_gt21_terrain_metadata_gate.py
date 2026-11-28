"""Synthetic independently specified source-label metadata expectations."""
import copy
import unittest
from contributor_tools.gt21_terrain_metadata_gate import check_curve_metadata, expected_metadata


class TerrainMetadataTests(unittest.TestCase):
    def test_all_source_labels_and_transition_directions(self):
        cases=[
            ('rampascent','incline_walking','incline_5.2deg',None,None),
            ('rampdescent','decline_walking','decline_-5.2deg',None,None),
            ('walk-rampascent','transition','walk_to_ramp_ascent','level_walking','incline_walking'),
            ('rampascent-walk','transition','ramp_ascent_to_walk','incline_walking','level_walking'),
            ('walk-rampdescent','transition','walk_to_ramp_descent','level_walking','decline_walking'),
            ('rampdescent-walk','transition','ramp_descent_to_walk','decline_walking','level_walking'),
            ('stairascent','stair_ascent','stair_ascent',None,None),
            ('stairdescent','stair_descent','stair_descent',None,None),
            ('walk-stairascent','transition','walk_to_stair_ascent','level_walking','stair_ascent'),
            ('stairascent-walk','transition','stair_ascent_to_walk','stair_ascent','level_walking'),
            ('walk-stairdescent','transition','walk_to_stair_descent','level_walking','stair_descent'),
            ('stairdescent-walk','transition','stair_descent_to_walk','stair_descent','level_walking'),
        ]
        for label,task,identity,origin,destination in cases:
            with self.subTest(label=label):
                mode='ramp' if 'ramp' in label else 'stair'
                actual=expected_metadata(mode,label,5.2 if mode=='ramp' else 4)
                self.assertEqual((actual['task'],actual['task_id']),(task,identity))
                self.assertEqual(actual['task_info'].get('transition_from'),origin)
                self.assertEqual(actual['task_info'].get('transition_to'),destination)
                if mode=='stair':self.assertEqual(actual['task_info']['step_height_m'],.102)

    def test_every_row_checked_and_class_only_match_is_insufficient(self):
        original={'task':'transition','task_id':'walk_to_stair_ascent',
            'task_info':{'step_height_m':.102,'surface':'stairs','gait_transition':True,
                'transition_from':'level_walking','transition_to':'stair_ascent'}}
        rows=[copy.deepcopy(original) for _ in range(150)]
        result=check_curve_metadata(rows,mode='stair',source_labels=['walk-stairascent']*3,raw_terrain=4)
        self.assertFalse(result['event_coverage_checked'])
        for field,value in [('task_id','stair_ascent_to_walk'),('transition_to','stair_descent'),('step_height_m',4.),('gait_transition',1)]:
            changed=copy.deepcopy(rows)
            if field=='task_id':changed[149][field]=value
            else:changed[149]['task_info'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                check_curve_metadata(changed,mode='stair',source_labels=['walk-stairascent'],raw_terrain=4)

    def test_missing_and_mixed_source_labels_rejected(self):
        for labels in [[],['stairascent','stairascent-walk']]:
            with self.assertRaises(ValueError):check_curve_metadata([],mode='stair',source_labels=labels,raw_terrain=4)

    def test_fallback_metadata_rejected(self):
        row={'task':'stair_ascent','task_id':'stair_ascent','task_info':{'step_height_m':.102,'surface':'stairs','fallback':True}}
        with self.assertRaises(ValueError):check_curve_metadata([row]*150,mode='stair',source_labels=['stairascent'],raw_terrain=4)

    def test_bad_source_geometry_and_mode_rejected(self):
        for value in [None,True,0,-4,float('nan'),float('inf')]:
            with self.subTest(value=value),self.assertRaises(ValueError):expected_metadata('stair','stairascent',value)
        with self.assertRaises(ValueError):expected_metadata('ramp','stairascent',4)
