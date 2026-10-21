"""Synthetic stdlib fixtures only; no actual GT24 sources loaded."""
import io
import math
import unittest
from contributor_tools.match_gt24_complete_intervals import ProjectedCSV, compare_membership, require_shared_membership


def reader(text):
    return ProjectedCSV(io.BytesIO(text.encode()), ['time', 'a'])


class MembershipTests(unittest.TestCase):
    def test_removed_transition_is_explicit(self):
        native = reader('time,a\n1,2\n2,4\n3,6\n4,nan\n')
        parsed = reader('time,a\n1,2\n3,6\n4,nan\n')
        result = compare_membership(native, parsed)
        self.assertTrue(result['membership_verified'])
        self.assertEqual(result['native_intervals_not_matched_to_this_candidate'], [{'first_row':1,'last_row':1,'first_time_s':2.,'last_time_s':2.}])
        self.assertEqual(result['missing_equal_values_unassessed'], {'a':1})
        self.assertEqual(require_shared_membership({'angle': result}), result['matched_native_intervals'])

    def test_prefix_name_cannot_override_wrong_clock_or_value(self):
        for parsed in ('time,a\n0,2\n1,9\n5,0\n', 'time,a\n1,nan\n'):
            result = compare_membership(reader('time,a\n1,2\n2,4\n'), reader(parsed))
            self.assertFalse(result['membership_verified'])
            self.assertEqual(len(result['native']['full_csv_sha256']),64)
            with self.assertRaises(ValueError): require_shared_membership({'angle':result})

    def test_clock_errors_and_empty_rejected(self):
        for text in ('time,a\n1,2\n1,3\n','time,a\nnan,2\n','time,a\n'):
            with self.assertRaises(ValueError):compare_membership(reader(text),reader('time,a\n1,2\n'))

    def test_intervals_bounded(self):
        with self.assertRaises(ValueError):compare_membership(reader('time,a\n1,1\n2,2\n3,3\n'),reader('time,a\n1,1\n3,3\n'),max_intervals=1)

    def test_hash_requires_eof(self):
        source=reader('time,a\n1,2\n')
        next(source)
        with self.assertRaises(ValueError):source.evidence()

    def test_different_table_clock_coverage_rejected(self):
        a=compare_membership(reader('time,a\n1,1\n2,2\n'),reader('time,a\n1,1\n'))
        b=compare_membership(reader('time,a\n1,1\n2,2\n'),reader('time,a\n2,2\n'))
        with self.assertRaises(ValueError):require_shared_membership({'angle':a,'moment':b})

if __name__ == '__main__':unittest.main()

class AggregationTests(unittest.TestCase):
    def test_union_keeps_gaps_and_merges_overlap(self):
        from contributor_tools.prepare_gt24_complete_membership import union_ranges
        self.assertEqual(union_ranges([(5,7),(1,3),(3,4),(10,12)]),[[1,7],[10,12]])
        with self.assertRaises(ValueError):union_ranges([(3,2)])

    def test_same_endpoints_different_interior_clocks_fail(self):
        a=compare_membership(reader('time,a\n1,1\n2,2\n4,4\n'),reader('time,a\n1,1\n2,2\n4,4\n'))
        b=compare_membership(reader('time,a\n1,1\n3,2\n4,4\n'),reader('time,a\n1,1\n3,2\n4,4\n'))
        with self.assertRaises(ValueError):require_shared_membership({'angle':a,'moment':b})

class FailClosedReviewTests(unittest.TestCase):
    def test_truncated_unprojected_cell_rejected(self):
        with self.assertRaises(ValueError):
            list(ProjectedCSV(io.BytesIO(b'time,a,unprojected\n1,2\n'),['time','a']))

    def test_timestamp_only_projection_rejected(self):
        from contributor_tools.prepare_gt24_complete_membership import checked_projection
        with self.assertRaises(ValueError):checked_projection({'time'},{'time'},{'time','x'},'grf')
        with self.assertRaises(ValueError):checked_projection({'time','ankle_angle_l'},{'time','ankle_angle_l'},{'time','ankle_angle_l'},'angle_filt')
        self.assertEqual(checked_projection({'time','x'},{'time','x'},{'time','x'},'grf'),['time','x'])

    def test_tampered_top_level_coverage_intervals_rejected(self):
        from contributor_tools.prepare_gt24_complete_membership import checked_report_intervals
        table=compare_membership(reader('time,a\n1,1\n2,2\n'),reader('time,a\n1,1\n'))
        report={'tables':{'angle':table},'matched_intervals':[{**table['matched_native_intervals'][0],'last_row':1}]}
        with self.assertRaises(ValueError):checked_report_intervals(report)
