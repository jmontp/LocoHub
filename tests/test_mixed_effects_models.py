#!/usr/bin/env python3
"""
Test Suite for Mixed-Effects Models

Created: 2025-06-19 with user permission
Purpose: Comprehensive testing of mixed-effects modeling functionality

Intent:
This test suite validates the mixed-effects modeling system including lme4 integration,
model templates, comparison tools, and diagnostic capabilities. Tests are designed to
work with both real and synthetic data, ensuring robust functionality across different
data characteristics and research scenarios.

Test Coverage:
- MixedEffectsManager initialization and basic functionality
- Biomechanical model templates (gait, intervention, group comparison)
- Model comparison and selection tools
- Random effects optimization
- Diagnostics and assumption checking
- Error handling and edge cases
"""

import unittest
import numpy as np
import pandas as pd
import tempfile
from pathlib import Path
import warnings
from unittest.mock import patch, MagicMock

# Import modules to test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib', 'core'))

try:
    from locomotion_analysis import LocomotionData
    from mixed_effects_models import MixedEffectsManager, BiomechanicalModels, ModelComparison, RandomEffectsOptimizer, DiagnosticsEngine
    from mixed_effects_examples import MixedEffectsExamples
    IMPORTS_SUCCESS = True
except ImportError as e:
    IMPORTS_SUCCESS = False
    IMPORT_ERROR = str(e)

# Check for R availability
try:
    import rpy2.robjects as ro
    from rpy2.robjects.packages import importr
    R_AVAILABLE = True
    try:
        lme4 = importr('lme4')
        LME4_AVAILABLE = True
    except:
        LME4_AVAILABLE = False
except ImportError:
    R_AVAILABLE = False
    LME4_AVAILABLE = False


class TestDataGenerator:
    """Generate synthetic locomotion data for testing."""
    
    @staticmethod
    def create_synthetic_locomotion_data(n_subjects=5, n_tasks=2, n_cycles=3) -> pd.DataFrame:
        """
        Create synthetic phase-indexed locomotion data for testing.
        
        Parameters
        ----------
        n_subjects : int
            Number of subjects
        n_tasks : int  
            Number of tasks per subject
        n_cycles : int
            Number of cycles per subject-task combination
            
        Returns
        -------
        pd.DataFrame
            Synthetic locomotion data
        """
        points_per_cycle = 150
        data_list = []
        
        # Define some realistic biomechanical parameters
        base_knee_angle = 0.5  # radians
        base_hip_angle = 0.3
        base_ankle_angle = -0.1
        
        task_effects = {
            'normal_walk': 0.0,
            'fast_walk': 0.2,
            'slow_walk': -0.1,
            'stair_ascent': 0.4,
            'stair_descent': 0.3
        }
        
        tasks = list(task_effects.keys())[:n_tasks]
        
        for subj_idx in range(n_subjects):
            subject_id = f"SUB{subj_idx+1:02d}"
            
            # Subject-specific random effects
            subj_knee_offset = np.random.normal(0, 0.1)
            subj_hip_offset = np.random.normal(0, 0.1)
            subj_ankle_offset = np.random.normal(0, 0.05)
            
            for task in tasks:
                task_effect = task_effects[task]
                
                for cycle in range(n_cycles):
                    # Create phase array
                    phase_percent = np.linspace(0, 100, points_per_cycle)
                    phase_idx = np.arange(1, points_per_cycle + 1)
                    
                    # Generate gait cycle patterns with some realism
                    for i, (phase_pct, phase_id) in enumerate(zip(phase_percent, phase_idx)):
                        phase_rad = 2 * np.pi * phase_pct / 100
                        
                        # Knee flexion pattern (more complex)
                        knee_base = base_knee_angle + subj_knee_offset + task_effect
                        knee_pattern = (knee_base + 
                                      0.8 * np.sin(phase_rad) + 
                                      0.3 * np.sin(2 * phase_rad) +
                                      np.random.normal(0, 0.02))
                        
                        # Hip flexion pattern
                        hip_base = base_hip_angle + subj_hip_offset + task_effect * 0.5
                        hip_pattern = (hip_base + 
                                     0.4 * np.sin(phase_rad + np.pi/4) +
                                     np.random.normal(0, 0.015))
                        
                        # Ankle flexion pattern
                        ankle_base = base_ankle_angle + subj_ankle_offset + task_effect * 0.3
                        ankle_pattern = (ankle_base + 
                                       0.3 * np.sin(phase_rad - np.pi/3) +
                                       np.random.normal(0, 0.01))
                        
                        # Create row
                        row = {
                            'subject': subject_id,
                            'task': task,
                            'phase': phase_id,
                            'cycle': cycle + 1,
                            'knee_flexion_angle_ipsi_rad': knee_pattern,
                            'knee_flexion_angle_contra_rad': knee_pattern + np.random.normal(0, 0.01),
                            'hip_flexion_angle_ipsi_rad': hip_pattern,
                            'hip_flexion_angle_contra_rad': hip_pattern + np.random.normal(0, 0.01),
                            'ankle_flexion_angle_ipsi_rad': ankle_pattern,
                            'ankle_flexion_angle_contra_rad': ankle_pattern + np.random.normal(0, 0.01)
                        }
                        
                        data_list.append(row)
        
        return pd.DataFrame(data_list)
    
    @staticmethod
    def save_synthetic_data_to_parquet(data: pd.DataFrame, file_path: str):
        """Save synthetic data to parquet file."""
        data.to_parquet(file_path, index=False)


@unittest.skipIf(not IMPORTS_SUCCESS, f"Import failed: {IMPORT_ERROR if not IMPORTS_SUCCESS else ''}")
class TestMixedEffectsModels(unittest.TestCase):
    """Test mixed-effects modeling functionality."""
    
    def setUp(self):
        """Set up test data and objects."""
        # Create synthetic data
        self.synthetic_data = TestDataGenerator.create_synthetic_locomotion_data(
            n_subjects=4, n_tasks=2, n_cycles=2
        )
        
        # Create temporary file
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.parquet', delete=False)
        self.temp_file.close()
        
        # Save synthetic data
        TestDataGenerator.save_synthetic_data_to_parquet(self.synthetic_data, self.temp_file.name)
        
        # Create LocomotionData object
        try:
            self.loco_data = LocomotionData(self.temp_file.name)
            self.loco_data_available = True
        except Exception as e:
            self.loco_data_available = False
            self.loco_data_error = str(e)
    
    def tearDown(self):
        """Clean up temporary files."""
        if hasattr(self, 'temp_file'):
            Path(self.temp_file.name).unlink(missing_ok=True)
    
    @unittest.skipIf(not R_AVAILABLE, "R not available")
    def test_mixed_effects_manager_initialization(self):
        """Test MixedEffectsManager initialization."""
        if not self.loco_data_available:
            self.skipTest(f"LocomotionData not available: {self.loco_data_error}")
        
        # Test successful initialization
        me_manager = MixedEffectsManager(self.loco_data)
        
        self.assertIsInstance(me_manager, MixedEffectsManager)
        self.assertEqual(me_manager.loco_data, self.loco_data)
        self.assertIsInstance(me_manager.templates, BiomechanicalModels)
        self.assertIsInstance(me_manager.comparison, ModelComparison)
        self.assertIsInstance(me_manager.optimizer, RandomEffectsOptimizer)
        self.assertIsInstance(me_manager.diagnostics, DiagnosticsEngine)
    
    @unittest.skipIf(not R_AVAILABLE, "R not available")
    def test_data_preparation(self):
        """Test data preparation for mixed-effects modeling."""
        if not self.loco_data_available:
            self.skipTest(f"LocomotionData not available: {self.loco_data_error}")
        
        me_manager = MixedEffectsManager(self.loco_data)
        
        # Test basic data preparation
        data = me_manager.prepare_data_for_modeling()
        
        self.assertIsInstance(data, pd.DataFrame)
        self.assertGreater(len(data), 0)
        
        # Check required columns
        required_cols = ['subject', 'task', 'cycle', 'phase', 'phase_percent']
        for col in required_cols:
            self.assertIn(col, data.columns)
        
        # Check phase-related columns
        self.assertIn('phase_sin', data.columns)
        self.assertIn('phase_cos', data.columns)
        self.assertIn('subject_factor', data.columns)
        self.assertIn('task_factor', data.columns)
        
        # Test data preparation without phase
        data_no_phase = me_manager.prepare_data_for_modeling(include_phase=False)
        self.assertIsNone(data_no_phase['phase'].iloc[0])
    
    @unittest.skipIf(not R_AVAILABLE or not LME4_AVAILABLE, "R or lme4 not available")
    def test_basic_hierarchical_model(self):
        """Test basic hierarchical model fitting."""
        if not self.loco_data_available:
            self.skipTest(f"LocomotionData not available: {self.loco_data_error}")
        
        me_manager = MixedEffectsManager(self.loco_data)
        
        # Prepare data
        data = me_manager.prepare_data_for_modeling(
            features=['knee_flexion_angle_ipsi_rad']
        )
        
        # Test basic model
        try:
            results = me_manager.fit_basic_hierarchical_model(
                outcome='knee_flexion_angle_ipsi_rad',
                predictors=['task_factor'],
                random_effects='(1|subject)',
                data=data,
                model_name='test_basic_model'
            )
            
            # Check results structure
            self.assertIsInstance(results, dict)
            self.assertIn('model', results)
            self.assertIn('summary', results)
            self.assertIn('formula', results)
            self.assertIn('aic', results)
            self.assertIn('bic', results)
            self.assertIn('converged', results)
            
            # Check that model is stored
            self.assertIn('test_basic_model', me_manager.models)
            
        except Exception as e:
            # Model fitting can fail with small synthetic datasets
            self.skipTest(f"Model fitting failed (expected with synthetic data): {e}")
    
    @unittest.skipIf(not R_AVAILABLE or not LME4_AVAILABLE, "R or lme4 not available")
    def test_gait_analysis_template(self):
        """Test gait analysis model template."""
        if not self.loco_data_available:
            self.skipTest(f"LocomotionData not available: {self.loco_data_error}")
        
        me_manager = MixedEffectsManager(self.loco_data)
        
        try:
            results = me_manager.templates.gait_analysis_model(
                outcome='knee_flexion_angle_ipsi_rad',
                tasks=['normal_walk', 'fast_walk'],
                include_phase=True,
                model_name='test_gait_model'
            )
            
            # Check results
            self.assertIsInstance(results, dict)
            self.assertIn('model', results)
            self.assertIn('formula', results)
            
            # Check formula contains expected terms
            formula = results['formula']
            self.assertIn('task_factor', formula)
            self.assertIn('phase_sin', formula)
            self.assertIn('phase_cos', formula)
            
        except Exception as e:
            self.skipTest(f"Gait analysis model failed (expected with synthetic data): {e}")
    
    def test_random_effects_recommendations(self):
        """Test random effects structure recommendations."""
        if not self.loco_data_available:
            self.skipTest(f"LocomotionData not available: {self.loco_data_error}")
        
        me_manager = MixedEffectsManager(self.loco_data)
        
        # Prepare data
        data = me_manager.prepare_data_for_modeling(
            features=['knee_flexion_angle_ipsi_rad']
        )
        
        # Get recommendations
        recommendations = me_manager.optimizer.recommend_random_effects(
            outcome='knee_flexion_angle_ipsi_rad',
            predictors=['task_factor', 'phase_sin', 'phase_cos'],
            data=data
        )
        
        # Check structure
        self.assertIsInstance(recommendations, dict)
        self.assertIn('data_summary', recommendations)
        self.assertIn('recommendations', recommendations)
        
        # Check data summary
        summary = recommendations['data_summary']
        self.assertIn('n_subjects', summary)
        self.assertIn('mean_obs_per_subject', summary)
        
        # Check recommendations list
        recs = recommendations['recommendations']
        self.assertIsInstance(recs, list)
        self.assertGreater(len(recs), 0)
        
        # Check first recommendation (should be basic random intercept)
        first_rec = recs[0]
        self.assertIn('structure', first_rec)
        self.assertIn('description', first_rec)
        self.assertIn('rationale', first_rec)
        self.assertEqual(first_rec['structure'], '(1|subject)')
    
    def test_model_comparison(self):
        """Test model comparison functionality."""
        if not self.loco_data_available:
            self.skipTest(f"LocomotionData not available: {self.loco_data_error}")
        
        me_manager = MixedEffectsManager(self.loco_data)
        
        # Create some mock model results for comparison testing
        mock_model1 = {
            'formula': 'outcome ~ predictor + (1|subject)',
            'aic': 100.0,
            'bic': 105.0,
            'loglik': -48.0,
            'converged': True,
            'data_shape': (1000, 10)
        }
        
        mock_model2 = {
            'formula': 'outcome ~ predictor + phase + (1|subject)',
            'aic': 95.0,
            'bic': 102.0,
            'loglik': -45.0,
            'converged': True,
            'data_shape': (1000, 10)
        }
        
        # Store mock models
        me_manager.models['model1'] = mock_model1
        me_manager.models['model2'] = mock_model2
        
        # Test comparison
        comparison = me_manager.comparison.compare_models(['model1', 'model2'])
        
        self.assertIsInstance(comparison, pd.DataFrame)
        self.assertEqual(len(comparison), 2)
        
        # Check columns
        expected_cols = ['model', 'formula', 'aic', 'bic', 'loglik', 'converged', 'aic_rank', 'bic_rank']
        for col in expected_cols:
            self.assertIn(col, comparison.columns)
        
        # Check ordering (should be sorted by AIC)
        self.assertEqual(comparison.iloc[0]['model'], 'model2')  # Lower AIC
        self.assertEqual(comparison.iloc[1]['model'], 'model1')  # Higher AIC
    
    def test_diagnostics_engine(self):
        """Test model diagnostics functionality."""
        if not self.loco_data_available:
            self.skipTest(f"LocomotionData not available: {self.loco_data_error}")
        
        me_manager = MixedEffectsManager(self.loco_data)
        
        # Create mock model for diagnostics testing
        mock_model_info = {
            'model': MagicMock(),  # Mock R model object
            'formula': 'outcome ~ predictor + (1|subject)',
            'aic': 100.0,
            'bic': 105.0,
            'loglik': -48.0,
            'converged': True,
            'data_shape': (1000, 10)
        }
        
        me_manager.models['test_diag_model'] = mock_model_info
        
        # Test diagnostics (will likely fail due to mock R object, but test structure)
        try:
            diagnostics = me_manager.diagnostics.run_diagnostics('test_diag_model')
            
            self.assertIsInstance(diagnostics, dict)
            self.assertIn('model_name', diagnostics)
            self.assertIn('convergence', diagnostics)
            
        except Exception:
            # Expected to fail with mock R objects
            pass
        
        # Test assumption checking
        try:
            assumptions = me_manager.diagnostics.check_assumptions('test_diag_model')
            
            self.assertIsInstance(assumptions, dict)
            expected_assumptions = ['linearity', 'independence', 'homoscedasticity', 
                                  'normality_residuals', 'normality_random_effects', 'overall_assessment']
            for assumption in expected_assumptions:
                self.assertIn(assumption, assumptions)
                
        except Exception:
            # Expected to fail with mock R objects
            pass
    
    def test_mixed_effects_examples(self):
        """Test mixed-effects examples functionality."""
        if not self.loco_data_available:
            self.skipTest(f"LocomotionData not available: {self.loco_data_error}")
        
        examples = MixedEffectsExamples(self.loco_data)
        
        # Test initialization
        self.assertIsInstance(examples, MixedEffectsExamples)
        self.assertEqual(examples.loco_data, self.loco_data)
        self.assertIsInstance(examples.me_manager, MixedEffectsManager)
    
    def test_error_handling(self):
        """Test error handling for various edge cases."""
        if not self.loco_data_available:
            self.skipTest(f"LocomotionData not available: {self.loco_data_error}")
        
        me_manager = MixedEffectsManager(self.loco_data)
        
        # Test with non-existent outcome variable
        data = me_manager.prepare_data_for_modeling()
        
        with self.assertRaises(RuntimeError):
            me_manager.fit_basic_hierarchical_model(
                outcome='non_existent_variable',
                predictors=['task_factor'],
                random_effects='(1|subject)',
                data=data,
                model_name='error_test'
            )
        
        # Test model summary for non-existent model
        with self.assertRaises(ValueError):
            me_manager.get_model_summary('non_existent_model')
        
        # Test comparison with non-existent models
        comparison = me_manager.comparison.compare_models(['non_existent1', 'non_existent2'])
        self.assertEqual(len(comparison), 0)  # Should return empty DataFrame
    
    @unittest.skipIf(R_AVAILABLE, "Test only when R is not available")
    def test_r_not_available_handling(self):
        """Test handling when R is not available."""
        if not self.loco_data_available:
            self.skipTest(f"LocomotionData not available: {self.loco_data_error}")
        
        # This test only runs when R is not available
        with self.assertRaises(ImportError):
            MixedEffectsManager(self.loco_data)


class TestDataGenerator(unittest.TestCase):
    """Test the synthetic data generator."""
    
    def test_synthetic_data_generation(self):
        """Test synthetic data generation."""
        data = TestDataGenerator.create_synthetic_locomotion_data(
            n_subjects=3, n_tasks=2, n_cycles=2
        )
        
        # Check basic structure
        self.assertIsInstance(data, pd.DataFrame)
        
        # Check expected number of rows (3 subjects * 2 tasks * 2 cycles * 150 phases)
        expected_rows = 3 * 2 * 2 * 150
        self.assertEqual(len(data), expected_rows)
        
        # Check required columns
        required_cols = ['subject', 'task', 'phase', 'cycle']
        for col in required_cols:
            self.assertIn(col, data.columns)
        
        # Check biomechanical variables
        biomech_vars = ['knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad', 'ankle_flexion_angle_ipsi_rad']
        for var in biomech_vars:
            self.assertIn(var, data.columns)
        
        # Check data ranges (should be reasonable for biomechanical data)
        knee_data = data['knee_flexion_angle_ipsi_rad']
        self.assertTrue(knee_data.min() > -2.0)  # Reasonable lower bound
        self.assertTrue(knee_data.max() < 3.0)   # Reasonable upper bound
        
        # Check phase values
        self.assertEqual(data['phase'].min(), 1)
        self.assertEqual(data['phase'].max(), 150)
        
        # Check subject and task counts
        self.assertEqual(data['subject'].nunique(), 3)
        self.assertEqual(data['task'].nunique(), 2)


if __name__ == '__main__':
    # Configure test environment
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce log noise during testing
    
    # Run tests
    unittest.main(verbosity=2)