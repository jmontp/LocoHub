"""Plan-only fixtures; no scientific CSVs or numerical imports."""
import json
from pathlib import Path
import tempfile
import unittest
from contributor_tools.prepare_gt24_complete_membership import build_plan,digest,TABLES
from contributor_tools.inventory_gt24_continuous_scope import parsed_disposition

class ScopeTests(unittest.TestCase):
    def test_unmapped_or_ambiguous_labels_stay_source_only(self):
        required={'angle_filt','moment_filt','grf','velocity','insole_sim'}
        patterns={'^walk':('walking','walk',{})}
        self.assertEqual(parsed_disposition('novel_on',required,patterns)[0],'source_only_unmapped_task')
        self.assertEqual(parsed_disposition('walk',required,patterns)[0],'source_only_ambiguous_exoskeleton_state')
        self.assertEqual(parsed_disposition('walk_on_off',required,patterns)[0],'source_only_ambiguous_exoskeleton_state')
        self.assertEqual(parsed_disposition('walk_on',required,patterns)[0],'canonical_parsed_candidate_requires_source_audit')

    def test_full_plan_keeps_unmapped_candidates_and_no_candidate_disposition(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);readme=root/'readme.txt';readme.write_text('synthetic')
            native={'subject':'BT01','recording':'native','members':[{'name':name} for name in TABLES.values()]}
            parsed={'subject':'BT01','recording':'native_unknown','native_name_candidates_only':['native'],'files':{key:{'path':'synthetic'} for key in TABLES},'disposition':'source_only_unmapped_task'}
            absent={**parsed,'recording':'other','native_name_candidates_only':[]}
            data={'status':'full_continuous_source_scope_enumerated_unreviewed','code_sha256':{},'readme':{'path':str(readme),'sha256':digest(readme)},'phases':[{'phase':'Phase1And2','dynamic_complete_recordings':[native],'parsed_recordings':[parsed,absent],'archive':{}},{'phase':'Phase3','dynamic_complete_recordings':[],'parsed_recordings':[],'archive':{}}]}
            path=root/'inventory.json';path.write_text(json.dumps(data))
            plan=build_plan(path)
            self.assertEqual(len(plan['jobs']),1)
            self.assertEqual(plan['jobs'][0]['parsed_disposition'],'source_only_unmapped_task')
            self.assertEqual(len(plan['unresolved_source_membership']),1)
            self.assertEqual(len(plan['jobs'][0]['tables']),7)
            data['phases'].pop();path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):build_plan(path)

if __name__=='__main__':unittest.main()
