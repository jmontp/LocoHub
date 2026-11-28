"""Text/stdlib fixtures only; no source datasets or numerical packages loaded."""
import unittest
from pathlib import Path
from contributor_tools.audit_gt21_terrain_adoption import terrain_windows, require_unambiguous_rounding
from contributor_tools.prepare_gt21_terrain_pilot_runner import adapt_runner


class TerrainAdoptionTests(unittest.TestCase):
    def test_whole_source_regions_not_one_supplied_label(self):
        labels=['rampascent']*60+['rampascent-walk']*60
        windows=terrain_windows([i*.01 for i in range(120)],labels,'ramp')
        self.assertEqual([(w['start_s'],w['end_s'],w['label']) for w in windows],
                         [(0.,.59,'rampascent'),(.6,1.19,'rampascent-walk')])
        self.assertFalse(any(w['start_s']<=.5 and .7<=w['end_s'] for w in windows))

    def test_existing_aggregate_threshold_preserved(self):
        labels=['stairascent']*30+['walk']+['stairascent']*30
        self.assertEqual(len(terrain_windows([i*.01 for i in range(61)],labels,'stair')),2)

    def test_wrong_mode_or_unknown_labels_do_not_create_windows(self):
        self.assertEqual(terrain_windows([i*.01 for i in range(100)],['stairascent']*100,'ramp'),[])

    def test_invalid_clock_rejected(self):
        with self.assertRaises(ValueError):terrain_windows([0.,float('nan'),2.],['stairascent']*3,'stair')
        with self.assertRaises(ValueError):terrain_windows([0.,0.,2.],['stairascent']*3,'stair')

    def test_rounding_boundaries_require_native_reconciliation(self):
        require_unambiguous_rounding('ramp',5.2)
        require_unambiguous_rounding('stair',4.)
        for mode,value in [('ramp',5.25),('stair',.1025/.0254)]:
            with self.assertRaises(ValueError):require_unambiguous_rounding(mode,value)

    def test_real_runner_adaptation_keeps_all_other_gates(self):
        source=Path('contributor_tools/run_gt21_combined_pilot.py').read_text()
        result=adapt_runner(source)
        self.assertIn('audit_gt21_terrain_adoption import check_record',result)
        self.assertIn("record['mode'] not in ('ramp', 'stair')",result)
        for gate in ['require_complete_ledger(ledger)','verify_preserved(','check_forces(',"digest(Path(x['path']))"]:
            self.assertIn(gate,result)
        self.assertIn('Terrain rounding fixtures: 4 cases passed',result)
        with self.assertRaises(ValueError):adapt_runner(source.replace("('levelground', 'treadmill')","('levelground',)"))
