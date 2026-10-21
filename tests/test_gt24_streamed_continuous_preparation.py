"""Synthetic stdlib preparation checks. No Arrow/NumPy/data conversion execution."""
import math
from pathlib import Path
import tempfile
import unittest
from contributor_tools.stream_gt24_continuous_record import selected_sources,scan
from contributor_tools.prepare_gt24_complete_membership import stat_identity
from contributor_tools.audit_gt24_streamed_continuous import checked_scalar

class PreparationTests(unittest.TestCase):
    def test_unmapped_sources_cannot_be_canonical(self):
        with self.assertRaises(ValueError):selected_sources({'disposition':'source_only_unmapped_task'})

    def test_global_scan_and_complete_source_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            files={}
            for kind in ('angle_filt','moment_filt','velocity','grf','insole_sim'):
                path=Path(temporary)/(kind+'.csv')
                header={'angle_filt':'hip_flexion_l','moment_filt':'hip_flexion_l_moment','velocity':'ankle_angle_l_velocity','grf':'fp_r_force_y','insole_sim':'insole_l_cop_x'}[kind]
                path.write_text('time,'+header+'\n1,0\n1.005,0\n1.010,30\n')
                files[kind]=stat_identity(path)
            record={'disposition':'canonical_parsed_candidate_requires_source_audit','exo_state':'powered','files':files}
            facts,evidence=scan(record,lambda:None)
            self.assertEqual(facts['rows'],3)
            self.assertEqual(facts['source_end_time_s'],1.01)
            self.assertEqual(facts['gait_reference_leg'],'r')
            self.assertEqual(len(evidence),5)
            self.assertTrue(all(x['rows']==3 and len(x['full_csv_sha256'])==64 for x in evidence.values()))
            # Same source inventory must reject subsequent mutation.
            Path(files['grf']['path']).write_text('time,fp_r_force_y\n1,0\n')
            with self.assertRaises(ValueError):scan(record,lambda:None)

    def test_gap_is_not_silently_differentiated(self):
        with tempfile.TemporaryDirectory() as temporary:
            files={}
            for kind in ('angle_filt','moment_filt','velocity','grf','insole_sim'):
                path=Path(temporary)/(kind+'.csv');path.write_text('time\n1\n1.005\n2\n');files[kind]=stat_identity(path)
            record={'disposition':'canonical_parsed_candidate_requires_source_audit','exo_state':'powered','files':files}
            with self.assertRaisesRegex(ValueError,'gaps/nonuniform'):scan(record,lambda:None)

    def test_independent_scalar_missing_and_sign_checks(self):
        self.assertFalse(checked_scalar(None,math.nan,'missing'))
        self.assertTrue(checked_scalar(-2.,-2.,'ankle'))
        for actual,expected in ((2.,-2.),(None,1.),(1.,math.nan)):
            with self.assertRaises(ValueError):checked_scalar(actual,expected,'source')

if __name__=='__main__':unittest.main()

class LateInfluenceTests(unittest.TestCase):
    def test_far_late_source_facts_affect_every_window(self):
        from contributor_tools.gt24_continuous_stream_windows import recording_facts
        def rows():
            for i in range(12000):
                yield {'angle_filt':{'time':5+i*.005},'grf':{'fp_r_force_y':21 if i==9000 else 0},'velocity':{'ankle_angle_l_velocity':2 if i==11000 else math.nan}}
        facts=recording_facts(rows(),['ankle_angle_l_velocity'])
        self.assertEqual(facts['gait_reference_leg'],'r')
        self.assertEqual(facts['first_vertical_force_events'],{'r':9000})
        self.assertFalse(facts['velocity_fallback_whole_column']['ankle_angle_l_velocity'])
        self.assertEqual(facts['source_end_time_s'],5+11999*.005)
