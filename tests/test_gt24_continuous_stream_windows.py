"""Synthetic scalar fixtures only, no numerical packages or source data."""
import math
import unittest
from contributor_tools.gt24_continuous_stream_windows import aligned_rows,recording_facts,halo_windows

class WindowTests(unittest.TestCase):
    def test_every_row_exactly_once_and_two_neighbor_halos(self):
        for n in (2,3,511,512,513,514,1025):
            covered=[]
            for start,lo,core,window in halo_windows(iter(range(n))):
                self.assertLessEqual(len(window),516)
                self.assertEqual(window,list(range(lo,min(n,start+core+2))))
                covered+=window[start-lo:start-lo+core]
            self.assertEqual(covered,list(range(n)))

    def test_global_fallback_and_reference_not_per_chunk(self):
        rows=[{'angle_filt':{'time':1+i*.005},'velocity':{'v':math.nan if i<512 else 2},'grf':{'fp_r_force_y':21 if i==2 else 0,'fp_l_force_y':21 if i==515 else 0}} for i in range(520)]
        facts=recording_facts(rows,['v','missing'])
        self.assertEqual(facts['gait_reference_leg'],'r')
        self.assertEqual(facts['velocity_fallback_whole_column'],{'v':False,'missing':True})
        self.assertAlmostEqual(facts['sampling_rate_hz'],200)
        self.assertEqual(facts['source_start_time_s'],1)

    def test_gap_rate_unknown_and_tie_left(self):
        rows=[{'angle_filt':{'time':t},'grf':{'fp_l_force_y':22,'fp_r_force_y':22}} for t in (0,.005,.02)]
        facts=recording_facts(rows,[])
        self.assertIsNone(facts['sampling_rate_hz'])
        self.assertEqual(facts['gait_reference_leg'],'l')

    def test_unaligned_sources_rejected(self):
        for source in ({'angle_filt':[{'time':0}],'grf':[]},{'angle_filt':[{'time':0}],'grf':[{'time':1}]}):
            with self.assertRaises(ValueError):list(aligned_rows(source))

if __name__=='__main__':unittest.main()
