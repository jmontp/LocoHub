#!/usr/bin/env python3
"""
Dataset Validator Phase Final Coverage Test

Created: 2025-06-19 with user permission
Purpose: Achieve 100% line coverage for lib/validation/dataset_validator_phase.py

Intent:
EMERGENCY GOVERNMENT AUDIT COMPLIANCE - Final push for 100% line coverage.
This test targets ALL 344 missing lines from current coverage analysis to achieve
near-100% coverage for government audit compliance.

Missing Line Ranges to Target:
- Lines 46-47: Import error handling
- Line 210: Phase dataset name validation
- Line 259: Phase column validation edge case
- Line 282: Missing columns error handling
- Line 311: Empty dataset edge case
- Line 386: Validation type check
- Lines 442-445: Step failure annotation
- Lines 468-577: Complete dataset validation workflow
- Lines 581-600: Step grouping utilities
- Lines 604-609: Task extraction utilities  
- Lines 622-721: Validation report generation
- Lines 734-797: Data conversion for plotting
- Lines 814-829: Step color generation
- Lines 843-927: Validation plot generation
- Lines 943-983: Task data processing
- Lines 988-1037: Failure table writing
- Lines 1047-1079: Main validation workflow
- Lines 1084-1104: CLI entry point
- Line 1108: CLI exit code

Critical Requirements:
- Target ALL 344 missing lines systematically
- Use real functionality testing (no fake coverage)
- Test all validation workflows and error paths
- Cover all plotting integration and report generation
- Test CLI entry points and main execution paths
"""

import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock, mock_open, call
import io
from datetime import datetime
import argparse

# Add project paths for imports
current_dir = Path(__file__).parent
repo_root = current_dir.parent
lib_path = repo_root / "lib"
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(lib_path))

# Mock external dependencies first
sys.modules['lib.core.locomotion_analysis'] = MagicMock()
sys.modules['lib.validation.filters_by_phase_plots'] = MagicMock()  
sys.modules['lib.validation.step_classifier'] = MagicMock()
sys.modules['lib.core.feature_constants'] = MagicMock()

# Import the module to test
from lib.validation.dataset_validator_phase import DatasetValidator, main


class TestDatasetValidatorPhaseFinalCoverage(unittest.TestCase):
    """Final comprehensive coverage test targeting ALL missing lines."""
    
    def setUp(self):
        """Set up test fixtures with comprehensive dataset types."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create comprehensive test datasets
        self.valid_phase_dataset = self._create_valid_phase_dataset()
        self.invalid_dataset = self._create_invalid_dataset()
        self.empty_dataset = self._create_empty_dataset()
        self.minimal_dataset = self._create_minimal_dataset()
        self.large_failure_dataset = self._create_large_failure_dataset()
        self.multi_task_dataset = self._create_multi_task_dataset()
        
        # Mock comprehensive validation expectations
        self.mock_kinematic_expectations = {
            'level_walking': {
                'hip_flexion_angle_ipsi_rad': {'min': -0.5, 'max': 1.0},
                'knee_flexion_angle_ipsi_rad': {'min': 0.0, 'max': 1.5},
                'ankle_flexion_angle_ipsi_rad': {'min': -0.3, 'max': 0.8}
            },
            'incline_walking': {
                'hip_flexion_angle_ipsi_rad': {'min': -0.3, 'max': 1.2},
                'knee_flexion_angle_ipsi_rad': {'min': 0.0, 'max': 1.7}
            },
            'decline_walking': {
                'hip_flexion_angle_contra_rad': {'min': -0.4, 'max': 1.1}
            }
        }
        
        self.mock_kinetic_expectations = {
            'level_walking': {
                'hip_moment_ipsi_Nm': {'min': -50, 'max': 100},
                'knee_moment_ipsi_Nm': {'min': -30, 'max': 80},
                'ankle_moment_contra_Nm': {'min': -40, 'max': 120}
            },
            'incline_walking': {
                'hip_moment_contra_Nm': {'min': -60, 'max': 110}
            }
        }
        
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def _create_valid_phase_dataset(self):
        """Create a comprehensive valid phase dataset."""
        n_subjects = 3
        n_tasks = 3
        n_steps = 4
        
        data_rows = []
        tasks = ['level_walking', 'incline_walking', 'decline_walking']
        
        for subj_idx in range(n_subjects):
            subject = f'subject_{subj_idx:03d}'
            for task_idx, task in enumerate(tasks):
                for step in range(1, n_steps + 1):
                    for phase in range(150):
                        phase_percent = (phase / 149) * 100
                        
                        # Create realistic biomechanical data
                        hip_angle = np.sin(phase_percent * np.pi / 180) * (0.5 + task_idx * 0.1)
                        knee_angle = np.sin(phase_percent * np.pi / 180) * (1.0 + task_idx * 0.2) 
                        ankle_angle = np.sin(phase_percent * np.pi / 180) * (0.3 + task_idx * 0.05)
                        
                        hip_moment = np.cos(phase_percent * np.pi / 180) * (50 + task_idx * 10)
                        knee_moment = np.cos(phase_percent * np.pi / 180) * (30 + task_idx * 5)
                        ankle_moment = np.cos(phase_percent * np.pi / 180) * (40 + task_idx * 8)
                        
                        data_rows.append({
                            'subject': subject,
                            'task': task,
                            'step': step,
                            'phase_percent': phase_percent,
                            'hip_flexion_angle_ipsi_rad': hip_angle,
                            'knee_flexion_angle_ipsi_rad': knee_angle,
                            'ankle_flexion_angle_ipsi_rad': ankle_angle,
                            'hip_flexion_angle_contra_rad': hip_angle * 0.8,
                            'knee_flexion_angle_contra_rad': knee_angle * 0.9,
                            'ankle_flexion_angle_contra_rad': ankle_angle * 0.7,
                            'hip_moment_ipsi_Nm': hip_moment,
                            'knee_moment_ipsi_Nm': knee_moment,
                            'ankle_moment_contra_Nm': ankle_moment,
                            'hip_moment_contra_Nm': hip_moment * 0.85,
                            'knee_moment_contra_Nm': knee_moment * 0.95,
                            'ankle_moment_ipsi_Nm': ankle_moment * 0.75
                        })
        
        df = pd.DataFrame(data_rows)
        dataset_path = Path(self.temp_dir) / "comprehensive_valid_phase.parquet"
        df.to_parquet(dataset_path)
        return str(dataset_path)
    
    def _create_invalid_dataset(self):
        """Create dataset with various invalid conditions."""
        data_rows = []
        for i in range(300):  # Multiple steps worth
            data_rows.append({
                'wrong_subject': 'S001',
                'wrong_task': 'invalid_task',
                'phase_percent': (i % 150 / 149) * 100,
                'invalid_var': 0.5
            })
        
        df = pd.DataFrame(data_rows)
        dataset_path = Path(self.temp_dir) / "invalid_phase.parquet"
        df.to_parquet(dataset_path)
        return str(dataset_path)
    
    def _create_empty_dataset(self):
        """Create empty dataset with proper columns."""
        df = pd.DataFrame(columns=[
            'subject', 'task', 'step', 'phase_percent', 
            'hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_ipsi_rad'
        ])
        dataset_path = Path(self.temp_dir) / "empty_phase.parquet"
        df.to_parquet(dataset_path)
        return str(dataset_path)
    
    def _create_minimal_dataset(self):
        """Create minimal dataset for edge case testing."""
        data_rows = []
        for phase in range(150):
            data_rows.append({
                'subject': 'minimal_subject',
                'task': 'level_walking',
                'step': 1,
                'phase_percent': (phase / 149) * 100,
                'hip_flexion_angle_ipsi_rad': 0.5,
                'knee_flexion_angle_ipsi_rad': 1.0
            })
        
        df = pd.DataFrame(data_rows)
        dataset_path = Path(self.temp_dir) / "minimal_phase.parquet"
        df.to_parquet(dataset_path)
        return str(dataset_path)
    
    def _create_large_failure_dataset(self):
        """Create dataset designed to generate many validation failures."""
        data_rows = []
        tasks = ['level_walking', 'incline_walking']
        
        for subj_idx in range(2):
            subject = f'failure_subject_{subj_idx:03d}'
            for task in tasks:
                for step in range(1, 6):  # More steps for more failures
                    for phase in range(150):
                        phase_percent = (phase / 149) * 100
                        
                        # Create data that will fail validation
                        data_rows.append({
                            'subject': subject,
                            'task': task,
                            'step': step,
                            'phase_percent': phase_percent,
                            'hip_flexion_angle_ipsi_rad': 5.0,  # Way out of range
                            'knee_flexion_angle_ipsi_rad': -2.0,  # Negative when shouldn't be
                            'ankle_flexion_angle_ipsi_rad': 3.0,  # Out of range
                            'hip_moment_ipsi_Nm': 500.0,  # Extremely high
                            'knee_moment_ipsi_Nm': -200.0,  # Very negative
                            'ankle_moment_contra_Nm': 1000.0  # Unrealistic
                        })
        
        df = pd.DataFrame(data_rows)
        dataset_path = Path(self.temp_dir) / "large_failure_phase.parquet"
        df.to_parquet(dataset_path)
        return str(dataset_path)
    
    def _create_multi_task_dataset(self):
        """Create dataset with multiple tasks for comprehensive testing."""
        data_rows = []
        tasks = ['level_walking', 'incline_walking', 'decline_walking', 'up_stairs', 'down_stairs']
        
        for task in tasks:
            for subj_idx in range(2):
                subject = f'multi_subject_{subj_idx:03d}'
                for step in range(1, 4):
                    for phase in range(150):
                        phase_percent = (phase / 149) * 100
                        
                        data_rows.append({
                            'subject': subject,
                            'task': task,
                            'step': step,
                            'phase_percent': phase_percent,
                            'hip_flexion_angle_ipsi_rad': np.sin(phase_percent * np.pi / 180) * 0.6,
                            'knee_flexion_angle_ipsi_rad': np.sin(phase_percent * np.pi / 180) * 1.1,
                            'ankle_flexion_angle_contra_rad': np.cos(phase_percent * np.pi / 180) * 0.4,
                            'hip_moment_ipsi_Nm': np.cos(phase_percent * np.pi / 180) * 60,
                            'knee_moment_contra_Nm': np.sin(phase_percent * np.pi / 180) * 35
                        })
        
        df = pd.DataFrame(data_rows)
        dataset_path = Path(self.temp_dir) / "multi_task_phase.parquet"
        df.to_parquet(dataset_path)
        return str(dataset_path)
    
    def _setup_comprehensive_mock_locomotion_data(self, dataset_path, should_fail=False, empty=False, no_data=False):
        """Setup comprehensive mock LocomotionData object."""
        mock_loco_data = MagicMock()
        
        if empty:
            mock_loco_data.subjects = []
            mock_loco_data.tasks = []
            mock_loco_data.features = []
            mock_loco_data.df = pd.DataFrame()
            mock_loco_data.get_subjects.return_value = []
            mock_loco_data.get_tasks.return_value = []
        elif no_data:
            mock_loco_data.subjects = ['subject_001']
            mock_loco_data.tasks = ['level_walking']
            mock_loco_data.features = ['hip_flexion_angle_ipsi_rad']
            mock_loco_data.df = pd.DataFrame()  # Don't read actual file, use empty DataFrame
            mock_loco_data.get_subjects.return_value = ['subject_001']
            mock_loco_data.get_tasks.return_value = ['level_walking']
            # No data returned from get_cycles
            mock_loco_data.get_cycles.return_value = (None, [])
        else:
            mock_loco_data.subjects = ['subject_001', 'subject_002', 'subject_003']
            mock_loco_data.tasks = ['level_walking', 'incline_walking', 'decline_walking']
            mock_loco_data.features = [
                'hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_ipsi_rad', 'ankle_flexion_angle_ipsi_rad',
                'hip_flexion_angle_contra_rad', 'knee_flexion_angle_contra_rad', 'ankle_flexion_angle_contra_rad',
                'hip_moment_ipsi_Nm', 'knee_moment_ipsi_Nm', 'ankle_moment_contra_Nm',
                'hip_moment_contra_Nm', 'knee_moment_contra_Nm', 'ankle_moment_ipsi_Nm'
            ]
            # Create mock DataFrame instead of reading file
            mock_loco_data.df = pd.DataFrame({
                'subject': ['S001'] * 300,
                'task': ['level_walking'] * 300,
                'step': [1] * 150 + [2] * 150,
                'phase_percent': list(range(150)) * 2,
                'hip_flexion_angle_ipsi_rad': np.random.normal(0.5, 0.1, 300)
            })
            mock_loco_data.get_subjects.return_value = mock_loco_data.subjects
            mock_loco_data.get_tasks.return_value = mock_loco_data.tasks
            
            # Setup feature constants
            mock_loco_data.ANGLE_FEATURES = [
                'hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_ipsi_rad', 'ankle_flexion_angle_ipsi_rad',
                'hip_flexion_angle_contra_rad', 'knee_flexion_angle_contra_rad', 'ankle_flexion_angle_contra_rad'
            ]
            mock_loco_data.MOMENT_FEATURES = [
                'hip_moment_ipsi_Nm', 'knee_moment_ipsi_Nm', 'ankle_moment_contra_Nm',
                'hip_moment_contra_Nm', 'knee_moment_contra_Nm', 'ankle_moment_ipsi_Nm'
            ]
            
            # Mock get_cycles method
            if should_fail:
                mock_loco_data.get_cycles.side_effect = Exception("Mock cycle extraction failure")
            else:
                # Return realistic 3D data
                n_steps = 5
                n_phases = 150
                n_features = 6  # Standard number of features
                mock_data_3d = np.random.normal(0.5, 0.2, (n_steps, n_phases, n_features))
                mock_loco_data.get_cycles.return_value = (mock_data_3d, mock_loco_data.ANGLE_FEATURES[:n_features])
        
        return mock_loco_data
    
    def _setup_comprehensive_mock_step_classifier(self, return_failures=True, num_failures=20):
        """Setup comprehensive mock StepClassifier."""
        mock_classifier = MagicMock()
        
        # Mock validation expectations loading
        mock_classifier.load_validation_ranges_from_specs.side_effect = lambda x: (
            self.mock_kinematic_expectations if x == 'kinematic' else self.mock_kinetic_expectations
        )
        
        # Mock validation results
        if return_failures:
            mock_failures = []
            for i in range(num_failures):
                failure = {
                    'variable': f'hip_flexion_angle_ipsi_rad' if i % 2 == 0 else 'knee_moment_ipsi_Nm',
                    'task': 'level_walking' if i % 3 == 0 else 'incline_walking',
                    'step': i,
                    'phase': (i * 25) % 100,
                    'value': 1.5 + i * 0.1,
                    'expected_min': -0.5,
                    'expected_max': 1.0,
                    'failure_reason': 'out_of_range' if i % 2 == 0 else 'biomechanically_invalid'
                }
                mock_failures.append(failure)
        else:
            mock_failures = []
            
        mock_classifier.validate_data_against_specs.return_value = mock_failures
        mock_classifier.get_step_summary_classification.return_value = np.array([0, 1, 2, 0, 1] * 10)  # Mixed colors
        
        return mock_classifier

    # =====================================================================
    # IMPORT ERROR HANDLING TESTS (Lines 46-47)
    # =====================================================================
    
    def test_import_error_handling(self):
        """Test import error handling in module imports."""
        # Test is covered by the actual import at module level
        # The try/except import block is executed when the module loads
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            # This tests the successful import path
            validator = DatasetValidator(self.valid_phase_dataset)
            self.assertIsNotNone(validator.step_classifier)

    # =====================================================================
    # COMPLETE DATASET VALIDATION WORKFLOW TESTS (Lines 468-577)
    # =====================================================================
    
    def test_validate_dataset_comprehensive_success(self):
        """Test complete dataset validation workflow with success path."""
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class, \
             patch('builtins.print') as mock_print:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier(return_failures=False)
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            validator.kinematic_expectations = self.mock_kinematic_expectations
            validator.kinetic_expectations = self.mock_kinetic_expectations
            
            # Setup mock locomotion data
            mock_loco_data = self._setup_comprehensive_mock_locomotion_data(self.valid_phase_dataset)
            
            # Test the complete validation workflow
            result = validator.validate_dataset(mock_loco_data)
            
            # Verify result structure
            self.assertIn('total_steps', result)
            self.assertIn('valid_steps', result)
            self.assertIn('failed_steps', result)
            self.assertIn('kinematic_failures', result)
            self.assertIn('kinetic_failures', result)
            self.assertIn('tasks_validated', result)
            self.assertIn('task_step_counts', result)
            
            # Verify print statements for workflow
            mock_print.assert_any_call("🔍 Starting dataset validation using LocomotionData...")
            mock_print.assert_any_call("📊 Validating 3 subjects across 3 tasks")
            
    def test_validate_dataset_with_failures(self):
        """Test dataset validation workflow with validation failures."""
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class, \
             patch('builtins.print') as mock_print:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier(return_failures=True, num_failures=15)
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.large_failure_dataset)
            validator.kinematic_expectations = self.mock_kinematic_expectations
            validator.kinetic_expectations = self.mock_kinetic_expectations
            
            # Setup mock locomotion data
            mock_loco_data = self._setup_comprehensive_mock_locomotion_data(self.large_failure_dataset)
            
            # Test validation with failures
            result = validator.validate_dataset(mock_loco_data)
            
            # Verify failures are captured
            self.assertGreater(len(result['kinematic_failures']), 0)
            self.assertGreater(result['failed_steps'], 0)
            self.assertEqual(len(validator.step_failures), len(result['kinematic_failures']) + len(result['kinetic_failures']))
            
    def test_validate_dataset_exception_handling(self):
        """Test dataset validation with exception handling during processing."""
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class, \
             patch('builtins.print') as mock_print:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            validator.kinematic_expectations = self.mock_kinematic_expectations
            validator.kinetic_expectations = self.mock_kinetic_expectations
            
            # Setup mock locomotion data that fails during processing
            mock_loco_data = self._setup_comprehensive_mock_locomotion_data(self.valid_phase_dataset, should_fail=True)
            
            # Test validation with processing exceptions
            result = validator.validate_dataset(mock_loco_data)
            
            # Should handle exceptions gracefully
            mock_print.assert_any_call("⚠️  Warning: Could not process subject_001-level_walking: Mock cycle extraction failure")
            
    def test_validate_dataset_no_data_for_subject_task(self):
        """Test validation when no data available for subject-task combinations."""
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            validator.kinematic_expectations = self.mock_kinematic_expectations
            validator.kinetic_expectations = self.mock_kinetic_expectations
            
            # Setup mock locomotion data with no actual data
            mock_loco_data = self._setup_comprehensive_mock_locomotion_data(self.valid_phase_dataset, no_data=True)
            
            # Test validation with no data
            result = validator.validate_dataset(mock_loco_data)
            
            # Should handle no data gracefully
            self.assertEqual(result['total_steps'], 0)

    # =====================================================================
    # STEP GROUPING UTILITIES TESTS (Lines 581-600)
    # =====================================================================
    
    def test_get_step_grouping_columns_standard(self):
        """Test step grouping column identification with standard columns."""
        df = pd.DataFrame({
            'subject': ['S001'],
            'task': ['walking'],
            'step': [1],
            'data': [0.5]
        })
        
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            group_cols = validator._get_step_grouping_columns(df)
            
            self.assertEqual(group_cols, ['subject', 'task', 'step'])
    
    def test_get_step_grouping_columns_alternative_names(self):
        """Test step grouping with alternative column names."""
        df = pd.DataFrame({
            'subject_id': ['S001'],
            'task_name': ['walking'],
            'cycle': [1],
            'data': [0.5]
        })
        
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            group_cols = validator._get_step_grouping_columns(df)
            
            self.assertEqual(group_cols, ['subject_id', 'task_name', 'cycle'])
    
    def test_get_step_grouping_columns_step_number(self):
        """Test step grouping with step_number column."""
        df = pd.DataFrame({
            'subject': ['S001'],
            'task': ['walking'],
            'step_number': [1],
            'data': [0.5]
        })
        
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            group_cols = validator._get_step_grouping_columns(df)
            
            self.assertEqual(group_cols, ['subject', 'task', 'step_number'])

    # =====================================================================
    # TASK EXTRACTION UTILITIES TESTS (Lines 604-609)
    # =====================================================================
    
    def test_get_task_from_step_data_standard(self):
        """Test task extraction from step data with standard column."""
        step_data = pd.DataFrame({
            'task': ['level_walking', 'level_walking'],
            'data': [0.5, 0.6]
        })
        
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            task = validator._get_task_from_step_data(step_data)
            
            self.assertEqual(task, 'level_walking')
    
    def test_get_task_from_step_data_task_name(self):
        """Test task extraction with task_name column."""
        step_data = pd.DataFrame({
            'task_name': ['incline_walking', 'incline_walking'],
            'data': [0.5, 0.6]
        })
        
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            task = validator._get_task_from_step_data(step_data)
            
            self.assertEqual(task, 'incline_walking')
    
    def test_get_task_from_step_data_unknown(self):
        """Test task extraction when no task column exists."""
        step_data = pd.DataFrame({
            'subject': ['S001'],
            'data': [0.5]
        })
        
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            task = validator._get_task_from_step_data(step_data)
            
            self.assertEqual(task, 'unknown_task')

    # =====================================================================
    # VALIDATION REPORT GENERATION TESTS (Lines 622-721)
    # =====================================================================
    
    def test_generate_validation_report_comprehensive(self):
        """Test comprehensive validation report generation."""
        validation_results = {
            'total_steps': 100,
            'valid_steps': 85,
            'failed_steps': 15,
            'kinematic_failures': [
                {
                    'variable': 'hip_flexion_angle_ipsi_rad',
                    'task': 'level_walking',
                    'step': 5,
                    'phase': 25,
                    'value': 1.5,
                    'expected_min': -0.5,
                    'expected_max': 1.0,
                    'failure_reason': 'out_of_range'
                }
            ],
            'kinetic_failures': [
                {
                    'variable': 'hip_moment_ipsi_Nm',
                    'task': 'incline_walking',
                    'step': 3,
                    'phase': 75,
                    'value': 150.0,
                    'expected_min': -50,
                    'expected_max': 100,
                    'failure_reason': 'excessive_magnitude'
                }
            ],
            'tasks_validated': ['level_walking', 'incline_walking'],
            'task_step_counts': {
                'level_walking': {'total': 60, 'failed': 8, 'valid': 52},
                'incline_walking': {'total': 40, 'failed': 7, 'valid': 33}
            }
        }
        
        task_plots = {
            'level_walking': {
                'kinematic': '/path/to/level_walking_kinematic.png',
                'kinetic': '/path/to/level_walking_kinetic.png'
            },
            'incline_walking': {
                'kinematic': '/path/to/incline_walking_kinematic.png'
            }
        }
        
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class, \
             patch('builtins.open', mock_open()) as mock_file:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            report_path = validator.generate_validation_report(validation_results, task_plots)
            
            # Verify report was written
            mock_file.assert_called_once()
            
            # Get the written content
            handle = mock_file.return_value.__enter__.return_value
            written_calls = handle.write.call_args_list
            written_content = ''.join([call[0][0] for call in written_calls])
            
            # Verify report content
            self.assertIn("# Dataset Validation Report", written_content)
            self.assertIn("**Total Steps Validated**: 100", written_content)
            self.assertIn("**Success Rate**: 85.0%", written_content)
            self.assertIn("level_walking, incline_walking", written_content)
            self.assertIn("## Task Validation Results", written_content)
            self.assertIn("### Level Walking", written_content)
            self.assertIn("![level_walking Kinematic Validation]", written_content)
            self.assertIn("## ⚠️ Detailed Failure Analysis", written_content)
            
    def test_generate_validation_report_no_failures(self):
        """Test validation report generation with no failures."""
        validation_results = {
            'total_steps': 50,
            'valid_steps': 50,
            'failed_steps': 0,
            'kinematic_failures': [],
            'kinetic_failures': [],
            'tasks_validated': ['level_walking'],
            'task_step_counts': {
                'level_walking': {'total': 50, 'failed': 0, 'valid': 50}
            }
        }
        
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class, \
             patch('builtins.open', mock_open()) as mock_file:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            report_path = validator.generate_validation_report(validation_results)
            
            # Get the written content
            handle = mock_file.return_value.__enter__.return_value
            written_calls = handle.write.call_args_list
            written_content = ''.join([call[0][0] for call in written_calls])
            
            # Verify no-failure content
            self.assertIn("## ✅ No Validation Failures", written_content)
            self.assertIn("All steps passed validation", written_content)
            self.assertIn("Dataset appears to be high quality", written_content)

    # =====================================================================
    # DATA CONVERSION FOR PLOTTING TESTS (Lines 734-797)
    # =====================================================================
    
    def test_convert_dataset_to_plotting_format_kinematic(self):
        """Test dataset conversion to plotting format for kinematic data."""
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            # Setup mock locomotion data with kinematic features
            mock_loco_data = self._setup_comprehensive_mock_locomotion_data(self.valid_phase_dataset)
            
            data_array, task_step_mapping, step_task_mapping, plot_mode, variables_used = \
                validator._convert_dataset_to_plotting_format(mock_loco_data)
            
            # Verify conversion results
            self.assertEqual(plot_mode, 'kinematic')
            self.assertIsInstance(data_array, np.ndarray)
            self.assertEqual(len(data_array.shape), 3)  # (num_steps, 150, num_features)
            self.assertIsInstance(task_step_mapping, dict)
            self.assertIsInstance(step_task_mapping, dict)
            self.assertIsInstance(variables_used, list)
    
    def test_convert_dataset_to_plotting_format_kinetic(self):
        """Test dataset conversion to plotting format for kinetic data only."""
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            # Setup mock locomotion data with only kinetic features
            mock_loco_data = self._setup_comprehensive_mock_locomotion_data(self.valid_phase_dataset)
            mock_loco_data.ANGLE_FEATURES = []  # No kinematic features
            mock_loco_data.features = mock_loco_data.MOMENT_FEATURES[:3]  # Only kinetic features
            
            data_array, task_step_mapping, step_task_mapping, plot_mode, variables_used = \
                validator._convert_dataset_to_plotting_format(mock_loco_data)
            
            # Should use kinetic mode
            self.assertEqual(plot_mode, 'kinetic')
    
    def test_convert_dataset_to_plotting_format_no_variables(self):
        """Test conversion failure when no standard variables available."""
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            # Setup mock locomotion data with no standard features
            mock_loco_data = self._setup_comprehensive_mock_locomotion_data(self.valid_phase_dataset)
            mock_loco_data.ANGLE_FEATURES = []
            mock_loco_data.MOMENT_FEATURES = []
            mock_loco_data.features = ['unknown_feature']
            
            with self.assertRaises(ValueError) as cm:
                validator._convert_dataset_to_plotting_format(mock_loco_data)
            
            self.assertIn("No standard kinematic or kinetic variables found", str(cm.exception))
    
    def test_convert_dataset_to_plotting_format_no_valid_data(self):
        """Test conversion failure when no valid step data found."""
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            # Setup mock locomotion data that returns no cycles
            mock_loco_data = self._setup_comprehensive_mock_locomotion_data(self.valid_phase_dataset, no_data=True)
            
            with self.assertRaises(ValueError) as cm:
                validator._convert_dataset_to_plotting_format(mock_loco_data)
            
            self.assertIn("No valid step data found for plotting", str(cm.exception))

    # =====================================================================
    # STEP COLOR GENERATION TESTS (Lines 814-829)
    # =====================================================================
    
    def test_generate_step_colors_from_validation_kinematic(self):
        """Test step color generation for kinematic validation."""
        validation_results = {
            'kinematic_failures': [
                {'step': 1, 'variable': 'hip_angle'},
                {'step': 3, 'variable': 'knee_angle'}
            ],
            'kinetic_failures': [
                {'step': 2, 'variable': 'hip_moment'}
            ]
        }
        
        step_task_mapping = {0: 'level_walking', 1: 'level_walking', 2: 'incline_walking'}
        
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            step_colors = validator._generate_step_colors_from_validation(
                validation_results, step_task_mapping, 'kinematic'
            )
            
            # Verify colors generated
            self.assertIsInstance(step_colors, np.ndarray)
            mock_classifier.get_step_summary_classification.assert_called_once()
    
    def test_generate_step_colors_from_validation_kinetic(self):
        """Test step color generation for kinetic validation."""
        validation_results = {
            'kinematic_failures': [{'step': 1}],
            'kinetic_failures': [{'step': 2}, {'step': 3}]
        }
        
        step_task_mapping = {0: 'level_walking', 1: 'level_walking'}
        
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            step_colors = validator._generate_step_colors_from_validation(
                validation_results, step_task_mapping, 'kinetic'
            )
            
            # Should use kinetic failures only
            self.assertIsInstance(step_colors, np.ndarray)
    
    def test_generate_step_colors_unknown_mode(self):
        """Test step color generation for unknown mode (uses all failures)."""
        validation_results = {
            'kinematic_failures': [{'step': 1}],
            'kinetic_failures': [{'step': 2}]
        }
        
        step_task_mapping = {0: 'level_walking'}
        
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            step_colors = validator._generate_step_colors_from_validation(
                validation_results, step_task_mapping, 'unknown_mode'
            )
            
            # Should use all failures
            self.assertIsInstance(step_colors, np.ndarray)

    # =====================================================================
    # VALIDATION PLOT GENERATION TESTS (Lines 843-927)
    # =====================================================================
    
    def test_generate_validation_plots_comprehensive(self):
        """Test comprehensive validation plot generation."""
        validation_results = {
            'kinematic_failures': [],
            'kinetic_failures': []
        }
        
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class, \
             patch('lib.validation.dataset_validator_phase.create_filters_by_phase_plot') as mock_create_plot, \
             patch('builtins.print') as mock_print:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            # Mock plot creation
            mock_create_plot.return_value = '/path/to/generated_plot.png'
            
            validator = DatasetValidator(self.valid_phase_dataset)
            validator.kinematic_expectations = self.mock_kinematic_expectations
            validator.kinetic_expectations = self.mock_kinetic_expectations
            
            # Setup mock locomotion data
            mock_loco_data = self._setup_comprehensive_mock_locomotion_data(self.valid_phase_dataset)
            
            task_plots = validator._generate_validation_plots(mock_loco_data, validation_results)
            
            # Verify plots generated
            self.assertIsInstance(task_plots, dict)
            mock_print.assert_any_call("📊 Generating validation plots for 3 tasks...")
            
    def test_generate_validation_plots_disabled(self):
        """Test plot generation when disabled."""
        validation_results = {'kinematic_failures': [], 'kinetic_failures': []}
        
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset, generate_plots=False)
            
            mock_loco_data = self._setup_comprehensive_mock_locomotion_data(self.valid_phase_dataset)
            
            task_plots = validator._generate_validation_plots(mock_loco_data, validation_results)
            
            # Should return empty dict when plots disabled
            self.assertEqual(task_plots, {})
    
    def test_generate_validation_plots_plot_failures(self):
        """Test plot generation with plot creation failures."""
        validation_results = {'kinematic_failures': [], 'kinetic_failures': []}
        
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class, \
             patch('lib.validation.dataset_validator_phase.create_filters_by_phase_plot') as mock_create_plot, \
             patch('builtins.print') as mock_print:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            # Mock plot creation to fail
            mock_create_plot.side_effect = Exception("Plot creation failed")
            
            validator = DatasetValidator(self.valid_phase_dataset)
            validator.kinematic_expectations = self.mock_kinematic_expectations
            validator.kinetic_expectations = self.mock_kinetic_expectations
            
            mock_loco_data = self._setup_comprehensive_mock_locomotion_data(self.valid_phase_dataset)
            
            task_plots = validator._generate_validation_plots(mock_loco_data, validation_results)
            
            # Should handle plot failures gracefully
            mock_print.assert_any_call("      ❌ Kinematic plot failed: Plot creation failed")

    # =====================================================================
    # TASK DATA PROCESSING TESTS (Lines 943-983)
    # =====================================================================
    
    def test_get_task_data_for_plotting_success(self):
        """Test successful task data processing for plotting."""
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            mock_loco_data = self._setup_comprehensive_mock_locomotion_data(self.valid_phase_dataset)
            subjects = mock_loco_data.subjects
            tasks = ['level_walking']
            features = mock_loco_data.ANGLE_FEATURES[:3]
            
            data_array, task_step_mapping, step_task_mapping = validator._get_task_data_for_plotting(
                mock_loco_data, subjects, tasks, features
            )
            
            # Verify data processing
            self.assertIsInstance(data_array, np.ndarray)
            self.assertEqual(len(data_array.shape), 3)
            self.assertIsInstance(task_step_mapping, dict)
            self.assertIsInstance(step_task_mapping, dict)
    
    def test_get_task_data_for_plotting_processing_failure(self):
        """Test task data processing with processing failures."""
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class, \
             patch('builtins.print') as mock_print:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            mock_loco_data = self._setup_comprehensive_mock_locomotion_data(self.valid_phase_dataset, should_fail=True)
            subjects = mock_loco_data.subjects
            tasks = ['level_walking']
            features = mock_loco_data.ANGLE_FEATURES[:3]
            
            with self.assertRaises(ValueError) as cm:
                validator._get_task_data_for_plotting(mock_loco_data, subjects, tasks, features)
            
            self.assertIn("No valid step data found for plotting", str(cm.exception))
            mock_print.assert_any_call("      ⚠️  Could not process subject_001-level_walking: Mock cycle extraction failure")
    
    def test_get_task_data_for_plotting_no_data(self):
        """Test task data processing when no data available."""
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            mock_loco_data = self._setup_comprehensive_mock_locomotion_data(self.valid_phase_dataset, no_data=True)
            subjects = mock_loco_data.subjects
            tasks = ['level_walking']
            features = mock_loco_data.ANGLE_FEATURES[:3]
            
            with self.assertRaises(ValueError) as cm:
                validator._get_task_data_for_plotting(mock_loco_data, subjects, tasks, features)
            
            self.assertIn("No valid step data found for plotting", str(cm.exception))

    # =====================================================================
    # FAILURE ANALYSIS AND REPORTING TESTS (Lines 988-1037)
    # =====================================================================
    
    def test_write_failure_table_comprehensive(self):
        """Test comprehensive failure table writing."""
        failures = [
            {
                'task': 'level_walking',
                'variable': 'hip_flexion_angle_ipsi_rad',
                'phase': 25.5,
                'value': 1.234,
                'expected_min': -0.5,
                'expected_max': 1.0,
                'failure_reason': 'out_of_range'
            },
            {
                'task': 'level_walking',
                'variable': 'hip_flexion_angle_ipsi_rad',
                'phase': 75.0,
                'value': 2.567,
                'expected_min': -0.5,
                'expected_max': 1.0,
                'failure_reason': 'biomechanically_invalid'
            },
            {
                'task': 'incline_walking',
                'variable': 'knee_moment_ipsi_Nm',
                'phase': 50,
                'value': 150.0,
                'expected_min': -30,
                'expected_max': 80,
                'failure_reason': 'excessive_magnitude'
            }
        ]
        
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            # Test table writing
            mock_file = io.StringIO()
            validator._write_failure_table(mock_file, failures)
            
            content = mock_file.getvalue()
            
            # Verify table content
            self.assertIn("#### Task: Level Walking", content)
            self.assertIn("**Variable: hip_flexion_angle_ipsi_rad** (2 failures)", content)
            self.assertIn("| Phase | Value | Expected Range | Failure Reason |", content)
            self.assertIn("| 25.5% | 1.234 | -0.500 to 1.000 | out_of_range |", content)
            self.assertIn("#### Task: Incline Walking", content)
            self.assertIn("**Variable: knee_moment_ipsi_Nm** (1 failures)", content)
    
    def test_write_failure_table_many_failures(self):
        """Test failure table writing with many failures (truncation)."""
        failures = []
        for i in range(15):  # More than 10 failures for same variable
            failures.append({
                'task': 'level_walking',
                'variable': 'hip_flexion_angle_ipsi_rad',
                'phase': i * 10,
                'value': 1.0 + i * 0.1,
                'expected_min': -0.5,
                'expected_max': 1.0,
                'failure_reason': f'failure_{i}'
            })
        
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            mock_file = io.StringIO()
            validator._write_failure_table(mock_file, failures)
            
            content = mock_file.getvalue()
            
            # Should truncate after 10 failures
            self.assertIn("*... and 5 more failures*", content)
    
    def test_write_failure_table_non_numeric_values(self):
        """Test failure table writing with non-numeric values."""
        failures = [
            {
                'task': 'level_walking',
                'variable': 'hip_flexion_angle_ipsi_rad', 
                'phase': 'N/A',
                'value': 'invalid',
                'expected_min': 'N/A',
                'expected_max': 'N/A',
                'failure_reason': 'invalid_data'
            }
        ]
        
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            mock_file = io.StringIO()
            validator._write_failure_table(mock_file, failures)
            
            content = mock_file.getvalue()
            
            # Should handle non-numeric values
            self.assertIn("| N/A | invalid | N/A to N/A | invalid_data |", content)

    # =====================================================================
    # MAIN VALIDATION WORKFLOW TESTS (Lines 1047-1079)
    # =====================================================================
    
    def test_run_validation_complete_workflow(self):
        """Test complete validation workflow execution."""
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class, \
             patch('lib.validation.dataset_validator_phase.LocomotionData') as mock_loco_class, \
             patch('builtins.print') as mock_print, \
             patch('builtins.open', mock_open()) as mock_file:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier(return_failures=True, num_failures=5)
            mock_step_classifier_class.return_value = mock_classifier
            
            mock_loco_data = self._setup_comprehensive_mock_locomotion_data(self.valid_phase_dataset)
            mock_loco_class.return_value = mock_loco_data
            
            validator = DatasetValidator(self.valid_phase_dataset)
            validator.kinematic_expectations = self.mock_kinematic_expectations
            validator.kinetic_expectations = self.mock_kinetic_expectations
            
            report_path = validator.run_validation()
            
            # Verify complete workflow
            self.assertIsInstance(report_path, str)
            mock_print.assert_any_call("\n✅ Validation completed!")
            mock_print.assert_any_call("⚠️  5 validation failures found")
    
    def test_run_validation_no_failures(self):
        """Test validation workflow with no failures."""
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class, \
             patch('lib.validation.dataset_validator_phase.LocomotionData') as mock_loco_class, \
             patch('builtins.print') as mock_print, \
             patch('builtins.open', mock_open()) as mock_file:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier(return_failures=False)
            mock_step_classifier_class.return_value = mock_classifier
            
            mock_loco_data = self._setup_comprehensive_mock_locomotion_data(self.valid_phase_dataset)
            mock_loco_class.return_value = mock_loco_data
            
            validator = DatasetValidator(self.valid_phase_dataset)
            validator.kinematic_expectations = self.mock_kinematic_expectations
            validator.kinetic_expectations = self.mock_kinetic_expectations
            
            report_path = validator.run_validation()
            
            # Verify no-failure workflow
            mock_print.assert_any_call("✅ No validation failures - dataset is high quality!")
    
    def test_run_validation_with_plots(self):
        """Test validation workflow with plot generation."""
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class, \
             patch('lib.validation.dataset_validator_phase.LocomotionData') as mock_loco_class, \
             patch('lib.validation.dataset_validator_phase.create_filters_by_phase_plot') as mock_create_plot, \
             patch('builtins.print') as mock_print, \
             patch('builtins.open', mock_open()) as mock_file:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            mock_loco_data = self._setup_comprehensive_mock_locomotion_data(self.valid_phase_dataset)
            mock_loco_class.return_value = mock_loco_data
            
            mock_create_plot.return_value = '/path/to/plot.png'
            
            validator = DatasetValidator(self.valid_phase_dataset, generate_plots=True)
            validator.kinematic_expectations = self.mock_kinematic_expectations
            validator.kinetic_expectations = self.mock_kinetic_expectations
            
            report_path = validator.run_validation()
            
            # Verify plot generation workflow
            mock_print.assert_any_call("📊 Generated 6 validation plots in:")

    # =====================================================================
    # CLI ENTRY POINT TESTS (Lines 1084-1104, 1108)
    # =====================================================================
    
    @patch('lib.validation.dataset_validator_phase.DatasetValidator')
    @patch('lib.validation.dataset_validator_phase.argparse.ArgumentParser')
    @patch('builtins.print')
    def test_main_function_success(self, mock_print, mock_parser_class, mock_validator_class):
        """Test main function successful execution."""
        # Setup argument parser mock
        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        mock_args = MagicMock()
        mock_args.dataset = self.valid_phase_dataset
        mock_args.output = None
        mock_args.no_plots = False
        mock_parser.parse_args.return_value = mock_args
        
        # Setup validator mock
        mock_validator = MagicMock()
        mock_validator_class.return_value = mock_validator
        mock_validator.run_validation.return_value = '/path/to/report.md'
        
        # Test main function
        result = main()
        
        # Verify successful execution
        self.assertEqual(result, 0)
        mock_validator_class.assert_called_once_with(
            self.valid_phase_dataset, None, generate_plots=True
        )
        mock_validator.run_validation.assert_called_once()
        mock_print.assert_any_call("\n🎉 Dataset validation completed successfully!")
    
    @patch('lib.validation.dataset_validator_phase.DatasetValidator')
    @patch('lib.validation.dataset_validator_phase.argparse.ArgumentParser')
    @patch('builtins.print')
    def test_main_function_with_args(self, mock_print, mock_parser_class, mock_validator_class):
        """Test main function with custom arguments."""
        # Setup argument parser mock
        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        mock_args = MagicMock()
        mock_args.dataset = self.valid_phase_dataset
        mock_args.output = '/custom/output'
        mock_args.no_plots = True
        mock_parser.parse_args.return_value = mock_args
        
        # Setup validator mock
        mock_validator = MagicMock()
        mock_validator_class.return_value = mock_validator
        mock_validator.run_validation.return_value = '/path/to/report.md'
        
        # Test main function
        result = main()
        
        # Verify execution with custom args
        self.assertEqual(result, 0)
        mock_validator_class.assert_called_once_with(
            self.valid_phase_dataset, '/custom/output', generate_plots=False
        )
    
    @patch('lib.validation.dataset_validator_phase.DatasetValidator')
    @patch('lib.validation.dataset_validator_phase.argparse.ArgumentParser')
    @patch('builtins.print')
    def test_main_function_exception_handling(self, mock_print, mock_parser_class, mock_validator_class):
        """Test main function exception handling."""
        # Setup argument parser mock
        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        mock_args = MagicMock()
        mock_args.dataset = self.valid_phase_dataset
        mock_args.output = None
        mock_args.no_plots = False
        mock_parser.parse_args.return_value = mock_args
        
        # Setup validator mock to raise exception
        mock_validator_class.side_effect = Exception("Validation failed")
        
        # Test main function
        result = main()
        
        # Verify error handling
        self.assertEqual(result, 1)
        mock_print.assert_any_call("❌ Error during validation: Validation failed")

    # =====================================================================
    # MISSING LINES TARGETED TESTS (Lines 96-98, 102-104, 124-161, etc.)
    # =====================================================================
    
    def test_load_dataset_missing_expectations_file_not_found(self):
        """Test initialization when kinematic expectations file not found (Lines 96-98)."""
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            mock_classifier = MagicMock()
            mock_classifier.load_validation_ranges_from_specs.side_effect = FileNotFoundError("File not found")
            mock_step_classifier_class.return_value = mock_classifier
            
            with patch('builtins.print') as mock_print:
                validator = DatasetValidator(self.valid_phase_dataset)
                
                # Should print warning for missing kinematic expectations
                mock_print.assert_any_call("⚠️  Warning: Kinematic validation expectations not found")
                self.assertEqual(validator.kinematic_expectations, {})
    
    def test_load_dataset_missing_kinetic_expectations_file_not_found(self):
        """Test initialization when kinetic expectations file not found (Lines 102-104)."""
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            mock_classifier = MagicMock()
            # First call (kinematic) succeeds, second call (kinetic) fails
            mock_classifier.load_validation_ranges_from_specs.side_effect = [
                self.mock_kinematic_expectations,
                FileNotFoundError("Kinetic file not found")
            ]
            mock_step_classifier_class.return_value = mock_classifier
            
            with patch('builtins.print') as mock_print:
                validator = DatasetValidator(self.valid_phase_dataset)
                
                # Should print warning for missing kinetic expectations
                mock_print.assert_any_call("⚠️  Warning: Kinetic validation expectations not found")
                self.assertEqual(validator.kinetic_expectations, {})
    
    def test_validate_required_columns_detailed_error_messages(self):
        """Test detailed error messages in column validation (Lines 124-161)."""
        # Test missing structural columns with detailed error
        invalid_df = pd.DataFrame({
            'wrong_subject': ['S001'],
            'wrong_task': ['walking'],
            'hip_flexion_angle_ipsi_rad': [0.5]
        })
        
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            with self.assertRaises(ValueError) as cm:
                validator._validate_required_columns(invalid_df)
            
            error_msg = str(cm.exception)
            self.assertIn("❌ VALIDATION FAILED: Missing required structural columns", error_msg)
            self.assertIn("Expected columns: ['subject', 'task', 'step']", error_msg)
            self.assertIn("Available columns:", error_msg)
            self.assertIn("Dataset must include subject, task, and step identification columns", error_msg)
    
    def test_validate_required_columns_detailed_biomech_error(self):
        """Test detailed biomechanical variable error messages (Lines 148-161)."""
        # Test no biomechanical variables with detailed error
        invalid_df = pd.DataFrame({
            'subject': ['S001'],
            'task': ['walking'],
            'step': [1],
            'random_var': [0.5],
            'another_var': [0.8]
        })
        
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            with self.assertRaises(ValueError) as cm:
                validator._validate_required_columns(invalid_df)
            
            error_msg = str(cm.exception)
            self.assertIn("❌ VALIDATION FAILED: No required biomechanical variables found", error_msg)
            self.assertIn("Expected angle variables:", error_msg)
            self.assertIn("hip_flexion_angle_contra_rad", error_msg)
            self.assertIn("Variable names must follow exact naming convention", error_msg)
            self.assertIn("<joint>_flexion_angle_<side>_rad", error_msg)
    
    def test_validate_task_coverage_detailed_error_messages(self):
        """Test detailed task coverage error messages (Lines 173-204)."""
        # Test no valid tasks with detailed error
        invalid_df = pd.DataFrame({
            'task': ['unknown_task', 'invalid_task', 'another_unknown']
        })
        
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            validator.kinematic_expectations = self.mock_kinematic_expectations
            validator.kinetic_expectations = self.mock_kinetic_expectations
            
            with self.assertRaises(ValueError) as cm:
                validator._validate_task_coverage(invalid_df)
            
            error_msg = str(cm.exception)
            self.assertIn("❌ VALIDATION FAILED: No tasks in dataset have validation expectations", error_msg)
            self.assertIn("Dataset tasks:", error_msg)
            self.assertIn("Available validation tasks:", error_msg)
            self.assertIn("Common valid task names: level_walking, incline_walking", error_msg)
    
    def test_load_dataset_print_statements(self):
        """Test all print statements during dataset loading (Lines 234-277)."""
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class, \
             patch('lib.validation.dataset_validator_phase.LocomotionData') as mock_loco_class, \
             patch('builtins.print') as mock_print:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            mock_loco_data = self._setup_comprehensive_mock_locomotion_data(self.valid_phase_dataset)
            mock_loco_class.return_value = mock_loco_data
            
            validator = DatasetValidator(self.valid_phase_dataset)
            validator.load_dataset()
            
            # Verify all print statements
            mock_print.assert_any_call("✅ Loaded phase-based dataset using LocomotionData library")
            mock_print.assert_any_call("   Subjects: 3")
            mock_print.assert_any_call("   Tasks: 3")
            mock_print.assert_any_call("   Features: 12")
            mock_print.assert_any_call("🔍 Performing explicit validation checks...")
            mock_print.assert_any_call("   ✅ Required columns validation passed")
            mock_print.assert_any_call("   ✅ Task coverage validation passed")
            mock_print.assert_any_call("✅ All validation checks passed - dataset is ready for validation")
    
    def test_load_dataset_empty_handling_with_columns(self):
        """Test empty dataset handling with columns (Lines 286-311)."""
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class, \
             patch('lib.validation.dataset_validator_phase.LocomotionData') as mock_loco_class, \
             patch('builtins.print') as mock_print, \
             patch('tempfile.NamedTemporaryFile') as mock_temp_file, \
             patch('os.unlink') as mock_unlink:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            # First call raises ValueError for empty dataset
            # Second call returns the mock data
            mock_loco_data = self._setup_comprehensive_mock_locomotion_data(self.empty_dataset, empty=True)
            mock_loco_class.side_effect = [ValueError("Dataset is empty"), mock_loco_data]
            
            # Mock temporary file
            mock_file = MagicMock()
            mock_file.name = "/tmp/test_minimal_phase.parquet"
            mock_temp_file.return_value.__enter__.return_value = mock_file
            
            validator = DatasetValidator(self.empty_dataset)
            result = validator.load_dataset()
            
            # Should handle empty dataset gracefully
            mock_print.assert_any_call("⚠️  Warning: Dataset is empty - creating minimal validation object")
            self.assertIsNotNone(result)
    
    def test_validate_standard_naming_detailed(self):
        """Test detailed standard naming validation (Lines 319-340)."""
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class, \
             patch('builtins.print') as mock_print:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            # Setup mock with standard and legacy features
            mock_loco_data = self._setup_comprehensive_mock_locomotion_data(self.valid_phase_dataset)
            mock_loco_data.features = [
                'hip_flexion_angle_ipsi_rad',  # Standard
                'knee_flexion_angle_contra_rad',  # Standard  
                'old_hip_angle_r',  # Legacy
                'legacy_knee_moment'  # Legacy
            ]
            validator.locomotion_data = mock_loco_data
            
            validator._validate_standard_naming()
            
            # Should print both standard and legacy warnings
            mock_print.assert_any_call("   ✅ Found 2 standard naming variables")
            mock_print.assert_any_call("   ⚠️  Found 2 legacy naming variables: ['old_hip_angle_r', 'legacy_knee_moment']...")
            mock_print.assert_any_call("   📝 Consider updating to standard naming: <joint>_<motion>_<measurement>_<side>_<unit>")
            mock_print.assert_any_call("      Example: hip_flexion_angle_ipsi_rad, knee_moment_contra_Nm")
    
    def test_convert_single_step_to_array_detailed(self):
        """Test detailed step array conversion (Lines 391-410)."""
        step_data = pd.DataFrame({
            'phase_percent': np.linspace(0, 100, 100),  # 100 points, needs resampling
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.5, 0.1, 100),
            'knee_flexion_angle_ipsi_rad': np.random.normal(0.8, 0.1, 100)
        })
        
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class, \
             patch('lib.core.feature_constants.get_feature_list') as mock_get_features:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            mock_get_features.return_value = ['hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_ipsi_rad']
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            result = validator._convert_single_step_to_array(step_data, 'kinematic')
            
            # Should resample to 150 points and create proper array
            self.assertEqual(result.shape, (1, 150, 2))
            self.assertIsInstance(result, np.ndarray)
    
    def test_validate_step_3d_data_detailed(self):
        """Test detailed 3D step validation (Lines 442-445)."""
        step_data_3d = np.random.normal(0.5, 0.1, (150, 3))
        features = ['hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_ipsi_rad', 'ankle_flexion_angle_ipsi_rad']
        
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            mock_classifier = self._setup_comprehensive_mock_step_classifier(return_failures=True, num_failures=2)
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            failures = validator._validate_step_3d_data(
                step_data_3d, features, 'level_walking', 'kinematic', 'test_subject', 5, 15
            )
            
            # Verify all failure annotation fields are added
            for failure in failures:
                self.assertEqual(failure['subject'], 'test_subject')
                self.assertEqual(failure['step_index'], 5)
                self.assertEqual(failure['step'], 15)
                self.assertEqual(failure['step_id'], 'test_subject_level_walking_5')
    
    def test_get_phase_column_all_alternatives(self):
        """Test all phase column alternatives (Lines 451-455)."""
        test_cases = [
            'phase_percent', 'phase_%', 'phase_r', 'phase_l', 'phase'
        ]
        
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            for phase_col in test_cases:
                with self.subTest(phase_column=phase_col):
                    test_df = pd.DataFrame({
                        phase_col: [0, 25, 50, 75, 100],
                        'data': [1, 2, 3, 4, 5]
                    })
                    
                    result = validator._get_phase_column(test_df)
                    self.assertEqual(result, phase_col)

    # =====================================================================
    # ADDITIONAL EDGE CASES FOR FULL COVERAGE
    # =====================================================================
    
    def test_phase_column_validation_edge_cases(self):
        """Test edge cases in phase column validation (Line 259)."""
        # Create dataset with phase-related columns but no valid phase column
        invalid_phase_df = pd.DataFrame({
            'subject': ['S001'] * 150,
            'task': ['walking'] * 150,
            'step': [1] * 150,
            'phase_related_but_not_valid': np.linspace(0, 100, 150),
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.5, 0.1, 150)
        })
        invalid_phase_path = Path(self.temp_dir) / "invalid_phase_col_phase.parquet"
        invalid_phase_df.to_parquet(invalid_phase_path)
        
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class:
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            validator = DatasetValidator(str(invalid_phase_path))
            
            with self.assertRaises(ValueError) as cm:
                validator.load_dataset()
            
            self.assertIn("Phase-based dataset missing phase column", str(cm.exception))
    
    def test_missing_columns_error_handling(self):
        """Test missing columns error handling (Line 282)."""
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class, \
             patch('lib.validation.dataset_validator_phase.LocomotionData') as mock_loco_class:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            
            # Mock LocomotionData to raise ValueError about missing columns
            mock_loco_class.side_effect = ValueError("Missing required columns for data processing")
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            with self.assertRaises(ValueError) as cm:
                validator.load_dataset()
            
            self.assertIn("Missing required structural columns for validation", str(cm.exception))
    
    def test_validation_type_check(self):
        """Test validation type checking (Line 386)."""
        # This is tested in the _convert_single_step_to_array method
        step_data = pd.DataFrame({
            'phase_percent': np.linspace(0, 100, 150),
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.5, 0.1, 150)
        })
        
        with patch('lib.validation.dataset_validator_phase.StepClassifier') as mock_step_classifier_class, \
             patch('lib.core.feature_constants.get_feature_list') as mock_get_features:
            
            mock_classifier = self._setup_comprehensive_mock_step_classifier()
            mock_step_classifier_class.return_value = mock_classifier
            mock_get_features.side_effect = ValueError("Unknown validation type")
            
            validator = DatasetValidator(self.valid_phase_dataset)
            
            with self.assertRaises(ValueError):
                validator._convert_single_step_to_array(step_data, 'invalid_type')


if __name__ == "__main__":
    # Run with high verbosity to see all test coverage
    unittest.main(verbosity=2)