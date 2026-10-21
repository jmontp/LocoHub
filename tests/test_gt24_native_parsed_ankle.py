"""Synthetic in-memory CSV/source relationships; stdlib only."""
import io
import math
import unittest
from contributor_tools.audit_gt24_native_parsed_ankle import read_prefix,compare_rows,check_relations


class NativeParsedTests(unittest.TestCase):
    def test_exact_time_alignment_not_first_row_alignment(self):
        native=[{'time':i*.005,'ankle':float(i)} for i in range(5)]
        self.assertEqual(compare_rows(native,native[2:],['time','ankle']),{'ankle':3})
        with self.assertRaisesRegex(ValueError,'alignment_deferred'):compare_rows(native,[{'time':9.,'ankle':0.}],['time','ankle'])
        with self.assertRaisesRegex(ValueError,'values differ'):compare_rows(native,[{'time':.01,'ankle':-2.}],['time','ankle'])

    def test_missingness_is_preserved_and_unassessed(self):
        nan=float('nan');rows=[{'time':0.,'ankle':nan}]
        self.assertEqual(compare_rows(rows,rows,['time','ankle']),{'ankle':0})
        with self.assertRaisesRegex(ValueError,'missingness'):compare_rows(rows,[{'time':0.,'ankle':0.}],['time','ankle'])

    def test_csv_limits_header_clock_and_prefix_evidence(self):
        data=b'time,ankle\n0,1\n0.005,2\n0.01,3\n0.015,4\n'
        rows,proof=read_prefix(io.BytesIO(data),['time','ankle'],3,lambda:None)
        self.assertEqual(len(rows),3);self.assertEqual(proof['consumed_bytes'],len(data)-8)
        for invalid in [data.replace(b'0.005',b'0'),data.replace(b'time,ankle',b'time,time'),data.replace(b'0.005',b'nan')]:
            with self.assertRaises(ValueError):read_prefix(io.BytesIO(invalid),['time','ankle'],3,lambda:None)

    def test_known_linear_angle_velocity_and_power(self):
        tables={k:[] for k in ['angle_filt','moment_filt','moment_filt_bio','velocity','power','power_bio']}
        for i in range(4):
            for kind in tables:
                row={'time':i*.005}
                for side in ('l','r'):
                    field='ankle_angle_'+side
                    if kind=='angle_filt':value=i*.5
                    elif kind=='velocity':field+='_velocity';value=100.
                    elif kind in ('moment_filt','moment_filt_bio'):field+='_moment';value=2.
                    else:field+='_power';value=2*100*math.pi/180
                    row[field]=value
                tables[kind].append(row)
        result=check_relations(tables);self.assertEqual(result['l']['interior_derivatives_checked'],2)
        tables['power'][1]['ankle_angle_l_power']*=-1
        with self.assertRaisesRegex(ValueError,'power product'):check_relations(tables)
