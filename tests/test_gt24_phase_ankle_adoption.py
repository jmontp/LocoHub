"""Stdlib provenance fixtures; numerical transform fixture is separately marked."""
import copy
import json
import unittest
from contributor_tools.adopt_gt24_phase_ankle_sign import META,README_SHA256,task_metadata,validate_manifest


class AdoptionPolicyTests(unittest.TestCase):
    def info(self,state='powered'):
        return {'exo_state':state,'moment_semantics':'source_filtered_total_joint_moment_Nm_per_source_model_kg','biological_moment_semantics':'source_total_minus_exo_interaction_when_available','assistance_semantics':'known_absent_no_exo' if state=='no_exo' else 'source_interaction_torque_when_available','source_note':'preserve me'}

    def test_documented_metadata_addition_keeps_original_information(self):
        for state in ['powered','worn_unpowered','no_exo']:
            original=self.info(state);result=json.loads(task_metadata(json.dumps(original)))
            self.assertEqual(result,{**original,**META})

    def test_unknown_units_states_or_double_transform_rejected(self):
        for key,value in [('moment_semantics','unknown'),('exo_state','unknown'),('assistance_semantics','inferred_zero'),('ankle_canonical_transform','previous')]:
            info=self.info();info[key]=value
            with self.assertRaises(ValueError):task_metadata(json.dumps(info))

    def manifest(self):
        return dict(dataset='gt24',source='Phase3',subject='SYN',recording='trial',status='converted_unreviewed',rows=150,schema_passed=True,decision_counts={'unchecked':1},converter_code=[{'path':'convert_gtech_2024_phase_to_parquet.py','sha256':'known'}],sources=[{'path':'readme.txt','sha256':README_SHA256}],outputs=[{'name':'phase.parquet','sha256':'phase'}])

    def test_known_original_convention_and_complete_count(self):
        data=self.manifest();self.assertEqual(validate_manifest(data,'Phase3','SYN','trial','known'),150)
        for key,value in [('status','quarantined_schema_failure'),('rows',149),('source','Phase1And2'),('schema_passed',False),('decision_counts',{})]:
            bad=copy.deepcopy(data);bad[key]=value
            with self.assertRaises(ValueError):validate_manifest(bad,'Phase3','SYN','trial','known')
        with self.assertRaises(ValueError):validate_manifest(data,'Phase3','SYN','trial','other')

    def test_zero_observations_explicit_disposition(self):
        data=self.manifest();data.update(status='no_accepted_observations',rows=0,decision_counts={},outputs=[{'name':'quality_unreviewed.json'}],schema_passed=False)
        self.assertEqual(validate_manifest(data,'Phase3','SYN','trial','known'),0)
        data['outputs'].append({'name':'phase.parquet'})
        with self.assertRaises(ValueError):validate_manifest(data,'Phase3','SYN','trial','known')
