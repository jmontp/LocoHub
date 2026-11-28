"""Text/schema tests only; no research data or numerical imports."""
import ast
from pathlib import Path
import unittest
from contributor_tools.um21_planar_field_policy import field_policy,patch_streaming_source


class PlanarFieldPolicyTests(unittest.TestCase):
    def test_python_exact_four_fields_and_no_invented_foot_or_velocity(self):
        fields={f'{s}_sagittal_angle_{r}_rad' for s in ['thigh','shank'] for r in ['ipsi','contra']}
        result=field_policy('streaming_python',fields|{'source_ankle_sagittal_angle_ipsi_rad','observation_id'})
        self.assertEqual(set(result['preserve_exactly']),fields)
        self.assertTrue(all(alias=='derived_planar_'+name for name,alias in result['preserve_exactly'].items()))
        self.assertFalse(result['scientific_approval'])

    def test_historical_matlab_includes_all_twelve_derived_fields(self):
        fields={f'{s}_sagittal_{k}_{r}_{u}' for s in ['thigh','shank','foot']
                for k,u in [('angle','rad'),('velocity','rad_s')] for r in ['ipsi','contra']}
        for producer in ['legacy_matlab_phase','legacy_matlab_time']:
            self.assertEqual(len(field_policy(producer,fields)['preserve_exactly']),12)

    def test_missing_schema_and_alias_collision_rejected(self):
        with self.assertRaises(ValueError):field_policy('streaming_python',[])
        fields={f'{s}_sagittal_angle_{r}_rad' for s in ['thigh','shank'] for r in ['ipsi','contra']}
        with self.assertRaises(ValueError):field_policy('streaming_python',fields|{'derived_planar_thigh_sagittal_angle_ipsi_rad'})
        with self.assertRaises(ValueError):field_policy('Wtr',fields)

    def test_patch_preserves_raw_ankle_and_all_unrelated_source(self):
        original=Path('contributor_tools/reconvert_umich_streaming.py').read_text()
        patched=patch_streaming_source(original);ast.parse(patched)
        restored=patched
        for segment,expr in [('thigh','pelvis+hip'),('shank','pelvis+hip-knee')]:
            new=(f"        fields[f'derived_planar_{segment}_sagittal_angle_{{role}}_rad']={expr}\n"
                 f"        fields[f'{segment}_sagittal_angle_{{role}}_rad']=np.full(150,np.nan)")
            restored=restored.replace(new,f"        fields[f'{segment}_sagittal_angle_{{role}}_rad']={expr}")
        self.assertEqual(restored,original)
        self.assertIn("fields[f'ankle_dorsiflexion_angle_{role}_rad']=np.full(150,np.nan)",patched)
        with self.assertRaises(ValueError):patch_streaming_source(patched)
