"""Small synthetic manifest fixtures only; no numerical imports or real data."""
import copy
from types import SimpleNamespace
import unittest
from contributor_tools.audit_um21_boundary_scope import reconcile,expected_mapping,identity


class BoundaryScopeTests(unittest.TestCase):
    def fixture(self):
        items=[dict(subject='SYN',condition='d10',reference_side='right',start_frame=a,end_frame=a+100,original_normalized_task='s0x8',streaming_status='excluded_in_original_curation') for a in (10,110)]
        summary=dict(status='all_curated_boundary_cycles_recovered_unreviewed',planned_cycles=2,recovered_cycles=2,records=[dict(subject='SYN',condition='d10',cycles=2)])
        review=dict(status='curated_window_exclusions_explained',records=copy.deepcopy(items),cycles=2)
        coverage=dict(status='full_treadmill_curation_membership_accounted')
        return summary,review,coverage,copy.deepcopy(items),{('SYN','d10'):copy.deepcopy(items)}

    def test_complete_exact_membership(self):
        args=self.fixture()
        self.assertEqual(len(reconcile(*args,True)[('SYN','d10')]),2)

    def test_missing_duplicate_and_extra_membership_rejected(self):
        for kind in ('missing','duplicate','wrong_label'):
            s,r,c,m,side=self.fixture()
            if kind=='missing':m.pop()
            elif kind=='duplicate':m.append(copy.deepcopy(m[0]))
            else:m[0]['original_normalized_task']='s1x2'
            with self.assertRaises(ValueError):reconcile(s,r,c,m,side,True)

    def test_sidecar_order_clock_or_metadata_tampering_rejected(self):
        for kind in ('reverse','clock','metadata'):
            s,r,c,m,side=self.fixture()
            if kind=='reverse':side[('SYN','d10')].reverse()
            elif kind=='clock':side[('SYN','d10')][0]['end_frame']+=1
            else:side[('SYN','d10')][0]['invented']='yes'
            with self.assertRaises(ValueError):reconcile(s,r,c,m,side,True)

    def test_partial_admitted_only_as_exact_prefix_pilot(self):
        s,r,c,m,side=self.fixture();s.update(status='partial_requested_limit',recovered_cycles=1);s['records'][0]['cycles']=1;side[('SYN','d10')]=side[('SYN','d10')][:1]
        self.assertEqual(len(reconcile(s,r,c,m,side,False)[('SYN','d10')]),1)
        with self.assertRaises(ValueError):reconcile(s,r,c,m,side,True)
        side[('SYN','d10')]=[copy.deepcopy(m[1])]
        with self.assertRaises(ValueError):reconcile(s,r,c,m,side,False)

    def test_duplicate_record_and_duplicate_cycle_rejected(self):
        s,r,c,m,side=self.fixture();s['records']*=2
        with self.assertRaises(ValueError):reconcile(s,r,c,m,side,True)
        s,r,c,m,side=self.fixture();r['records'][1]=copy.deepcopy(r['records'][0])
        with self.assertRaises(ValueError):reconcile(s,r,c,m,side,True)

    def test_raw_shape_drives_mapping_with_units_and_unverified_frames(self):
        trial={'jointMoments':{'LHipMoment':SimpleNamespace(ndim=2,shape=(3,500))}}
        mapping=expected_mapping(trial)
        self.assertEqual(len(mapping),3)
        self.assertEqual(mapping['source_joint_moment_lhipmoment_component_2_Nm_kg'],dict(group='jointMoments',variable='LHipMoment',matlab_component_1based=3,unit='Nm_kg',canonical_frame_verified=False))
        trial['jointMoments']['LHipMoment'].shape=(4,500)
        with self.assertRaises(ValueError):expected_mapping(trial)

    def test_invalid_source_intervals_fail_closed(self):
        item=self.fixture()[1]['records'][0]
        for name,value in [('start_frame',0),('end_frame',10),('end_frame',10000),('start_frame',True),('reference_side','unknown'),('subject','../SYN')]:
            bad=dict(item);bad[name]=value
            with self.assertRaises(ValueError):identity(bad)
