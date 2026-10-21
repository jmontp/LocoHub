"""Stdlib manifest fixtures; no numerical imports or research data."""
import copy
import unittest
from contributor_tools.build_um21_planar_scope import records_from_evidence
from contributor_tools.preserve_um21_planar_estimates import validate_scope,exact_value


class ScopeTests(unittest.TestCase):
    def run_evidence(self):
        r={'subject':'SYN','condition':'run','observations':2,'rows':300,'outputs':{'SYN/run/phase.parquet':'a'*64,'SYN/run/source_columns.json':'b'*64}}
        return {'status':'complete_running_source_channels_unreviewed','source_sha256':'source','available_recordings':1,'recordings':[r]}, {'status':'all_running_source_cycles_checked_unreviewed','source_sha256':'source','summary_sha256':'s','recordings':[dict(subject='SYN',condition='run',observations=2,rows=300)],'total_observations':2,'total_rows':300}

    def test_complete_run_scope_bound_to_independent_readback(self):
        summary,readback=self.run_evidence()
        records=records_from_evidence('run',summary,'s',readback)
        scope={'status':'complete_um21_planar_scope_checked_unreviewed','producer':'run','baseline_summary_sha256':'s','evidence_bindings':{'manifest':'s'},'records':records,'expected_records':1,'expected_observations':2}
        self.assertEqual(len(validate_scope(scope)),1)
        for fault in ['hash','missing','count']:
            bad=copy.deepcopy(readback)
            if fault=='hash':bad['summary_sha256']='changed'
            elif fault=='missing':bad['recordings']=[]
            else:bad['recordings'][0]['observations']=1
            with self.assertRaises(ValueError):records_from_evidence('run',summary,'s',bad)

    def test_partial_run_and_unbound_boundary_sidecars_rejected(self):
        summary,readback=self.run_evidence();summary['available_recordings']=2
        with self.assertRaises(ValueError):records_from_evidence('run',summary,'s',readback)
        with self.assertRaisesRegex(ValueError,'sidecars'):records_from_evidence('boundaries',{},'s')

    def test_exact_values_distinguish_null_nan_and_signed_zero(self):
        self.assertTrue(exact_value([None,float('nan'),-0.],[None,float('nan'),-0.]))
        self.assertFalse(exact_value([None],[float('nan')]))
        self.assertFalse(exact_value([-0.],[0.]))
        self.assertFalse(exact_value([True],[1]))

    def test_legacy_final_only_checker_identity_and_source_required(self):
        from contributor_tools.build_um21_planar_scope import RUN_CHECKER_SHA
        summary,readback=self.run_evidence();del readback['status']
        with self.assertRaises(ValueError):records_from_evidence('run',summary,'s',readback)
        summary['source_sha256']='source'
        readback.update(probe_sha256=RUN_CHECKER_SHA,source_sha256='source',finite_source_values_checked=1,source_component_max_errors={'source_joint_angle':0.})
        self.assertEqual(len(records_from_evidence('run',summary,'s',readback)),1)
        for key,value in [('status','running'),('source_sha256','other'),('probe_sha256','other'),('source_component_max_errors',{'angle':float('nan')})]:
            bad=copy.deepcopy(readback);bad[key]=value
            with self.assertRaises(ValueError):records_from_evidence('run',summary,'s',bad)

    def test_duplicate_identity_and_record_directory_rejected(self):
        summary,readback=self.run_evidence()
        summary['recordings']*=2;summary['available_recordings']=2
        with self.assertRaisesRegex(ValueError,'Duplicate'):records_from_evidence('run',summary,'s',readback)
        summary,readback=self.run_evidence();records=records_from_evidence('run',summary,'s',readback)
        empty={'phase_path':None,'record_path':'SYN/run','disposition':'no_annotated_observations','observations':0,'rows':0,'outputs':{'SYN/run/disposition.json':'c'*64}}
        scope={'status':'complete_um21_planar_scope_checked_unreviewed','producer':'stairs','baseline_summary_sha256':'s','evidence_bindings':{'manifest':'s'},'records':records+[empty],'expected_records':2,'expected_observations':2}
        for ordering in [records+[empty],[empty]+records]:
            scope['records']=ordering
            with self.assertRaises(ValueError):validate_scope(scope)

    def test_empty_stair_requires_explicit_bound_disposition(self):
        record={'subject':'SYN','condition':'stairs','windows':[],'exported_rows':0,'disposition':'no_annotated_observations','outputs':{'SYN/stairs/disposition.json':'d'*64}}
        summary={'status':'all_annotated_stair_cycles_exported_unreviewed','recordings':[record]}
        readback={'status':'all_annotated_stair_cycles_source_checked_unreviewed','summary_sha256':'s','source_recordings':1,'annotated_observations':0,'exported_observations_checked':0}
        records=records_from_evidence('stairs',summary,'s',readback)
        scope={'status':'complete_um21_planar_scope_checked_unreviewed','producer':'stairs','baseline_summary_sha256':'s','evidence_bindings':{'manifest':'s'},'records':records,'expected_records':1,'expected_observations':0}
        self.assertEqual(validate_scope(scope)[0]['disposition'],'no_annotated_observations')
        del record['disposition']
        with self.assertRaisesRegex(ValueError,'disposition'):records_from_evidence('stairs',summary,'s',readback)
