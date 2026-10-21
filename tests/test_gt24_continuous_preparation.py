"""Stdlib structural/derivative checks, no scientific data or numerical imports."""
import ast
from pathlib import Path
import unittest
from contributor_tools.prepare_gt24_continuous_correction import patch,TIME,ROOT
from contributor_tools.run_gt24_continuous_pilot import manual_derivative


class ContinuousPreparationTests(unittest.TestCase):
    def test_ankle_and_knee_native_velocity_signs_with_no_second_fallback_flip(self):
        tree=ast.parse(patch((ROOT/TIME).read_text()))
        assignments=[x for x in ast.walk(tree) if isinstance(x,ast.Assign)]
        for side in ('ipsi','contra'):
            for name in [f'ankle_{side}',f'ankle_vel_{side}',f'ankle_mom_{side}',f'ankle_bio_{side}',f'knee_vel_{side}']:
                first=next(x for x in assignments if any(isinstance(t,ast.Name) and t.id==name for t in x.targets))
                self.assertTrue(any(isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.USub) for n in ast.walk(first.value)))
            fallback=[x for x in assignments if any(isinstance(t,ast.Name) and t.id==f'ankle_vel_{side}' for t in x.targets)][1]
            self.assertEqual(fallback.value.func.id,'_gradient_over_time')
            self.assertEqual(fallback.value.args[0].id,f'ankle_{side}')

    def test_actual_clock_and_missing_force_policy_present(self):
        source=patch((ROOT/TIME).read_text())
        self.assertNotIn('time_s = np.arange',source)
        self.assertNotIn('n_samples = min(required_lengths)',source)
        self.assertNotIn('if lat_mean > 0',source)
        for key in ['source_time_s','source_recording_id','continuous_recording','source_grf_global_','ankle_velocity_fallback']:
            self.assertIn(key,source)

    def test_independent_derivative_known_irregular_linear_samples(self):
        result=manual_derivative([0.,.2,.6,1.],[0.,.1,.3,.5])
        for value in result:self.assertAlmostEqual(value,2.)

    def test_unknown_source_shape_fails_closed(self):
        source=(ROOT/TIME).read_text().replace('    ankle_ipsi = _series_or_nan','    ankle_ipsi = something_else')
        with self.assertRaises(ValueError):patch(source)
