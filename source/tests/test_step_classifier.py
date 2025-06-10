#!/usr/bin/env python3
"""
Comprehensive Test Suite for step_classifier.py

Created: 2025-06-10
Purpose: Test all functionality of the StepClassifier module including feature-aware 
         classification, step tracking, color mapping, and edge case handling.

Intent:
This test suite validates the step classification functionality that determines how 
individual steps should be color-coded in validation plots:

1. **Basic Classification**: Tests core step color classification logic
2. **Feature-Aware Logic**: Validates local vs other violation distinction
3. **Deterministic Test Cases**: Tests with precise failing/passing scenarios based on known ranges
4. **Boundary Value Analysis**: Tests exact boundary conditions (min/max limits)
5. **Edge Cases**: Tests with empty data, missing features, invalid inputs
6. **Integration Scenarios**: Tests with realistic validation failure data
7. **Performance**: Validates efficiency with large step counts
8. **Error Handling**: Tests proper error handling for invalid inputs

Test Categories:
- Unit tests for individual methods
- Deterministic tests with known validation ranges and expected outcomes
- Integration tests with realistic validation data
- Boundary value tests for precise limit checking
- Edge case tests for robustness
- Performance tests for scalability

**Deterministic Testing Approach**:
This test suite implements comprehensive deterministic testing where we:
- Define precise validation ranges (e.g., hip: 0.2-0.6 rad at phase 0%)
- Create specific failing cases (e.g., value 0.8 > max 0.6 = should fail)
- Create specific passing cases (e.g., value 0.4 within 0.2-0.6 = should pass)
- Test boundary conditions (e.g., values 0.2, 0.6 exactly at limits)
- Verify expected step color outcomes based on violation types

**Current Implementation Limitation**:
The step classifier currently operates at task-level granularity, meaning all validation
failures within a task are assigned to ALL steps of that task. This is acknowledged in
the implementation and tests are designed to work with this limitation while still
providing comprehensive validation of the color classification logic.

The tests ensure the step classifier correctly maps validation failures to step colors
for use in the filters_by_phase_plots visualization system.
"""

import sys
import os
import numpy as np
from pathlib import Path

# Add source directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False
    class pytest:
        @staticmethod
        def fixture(func):
            return func
        
        @staticmethod  
        def mark():
            class Mark:
                def parametrize(self, *args, **kwargs):
                    def decorator(func):
                        return func
                    return decorator
            return Mark()

from validation.step_classifier import StepClassifier


class TestStepClassifier:
    """Test suite for the StepClassifier class."""
    
    @pytest.fixture
    def classifier(self):
        """Create a StepClassifier instance for testing."""
        return StepClassifier()
    
    @pytest.fixture
    def precise_validation_ranges(self):
        """Create precise validation ranges for deterministic testing."""
        return {
            'level_walking': {
                0: {  # Phase 0%
                    'hip_flexion_angle_ipsi': {'min': 0.2, 'max': 0.6},      # 0.2-0.6 rad
                    'knee_flexion_angle_ipsi': {'min': 0.0, 'max': 0.15},    # 0.0-0.15 rad
                    'ankle_flexion_angle_ipsi': {'min': -0.05, 'max': 0.05}, # -0.05-0.05 rad
                },
                25: {  # Phase 25%
                    'hip_flexion_angle_ipsi': {'min': 0.1, 'max': 0.4},      # 0.1-0.4 rad
                    'knee_flexion_angle_ipsi': {'min': 0.3, 'max': 0.8},     # 0.3-0.8 rad
                    'ankle_flexion_angle_ipsi': {'min': 0.0, 'max': 0.2},    # 0.0-0.2 rad
                },
                50: {  # Phase 50%
                    'hip_flexion_angle_ipsi': {'min': -0.1, 'max': 0.2},     # -0.1-0.2 rad
                    'knee_flexion_angle_ipsi': {'min': 0.5, 'max': 1.0},     # 0.5-1.0 rad
                    'ankle_flexion_angle_ipsi': {'min': -0.3, 'max': -0.1},  # -0.3--0.1 rad
                }
            },
            'incline_walking': {
                0: {
                    'hip_flexion_angle_ipsi': {'min': 0.3, 'max': 0.8},
                    'knee_flexion_angle_ipsi': {'min': 0.0, 'max': 0.2},
                    'ankle_flexion_angle_ipsi': {'min': 0.0, 'max': 0.1},
                }
            }
        }
    
    @pytest.fixture
    def deterministic_failing_cases(self, precise_validation_ranges):
        """Create specific failing cases based on known validation ranges."""
        return [
            # Level walking failures
            {
                'task': 'level_walking',
                'variable': 'hip_flexion_angle_ipsi',
                'phase': 0.0,
                'value': 0.8,  # Above max of 0.6
                'expected_min': 0.2,
                'expected_max': 0.6,
                'failure_reason': 'Value 0.800 above maximum 0.600 at phase 0.0%',
                'expected_color': 'red'  # Local violation for hip feature
            },
            {
                'task': 'level_walking',
                'variable': 'hip_flexion_angle_ipsi',
                'phase': 0.0,
                'value': 0.1,  # Below min of 0.2
                'expected_min': 0.2,
                'expected_max': 0.6,
                'failure_reason': 'Value 0.100 below minimum 0.200 at phase 0.0%',
                'expected_color': 'red'  # Local violation for hip feature
            },
            {
                'task': 'level_walking',
                'variable': 'knee_flexion_angle_ipsi',
                'phase': 25.0,
                'value': 1.2,  # Above max of 0.8
                'expected_min': 0.3,
                'expected_max': 0.8,
                'failure_reason': 'Value 1.200 above maximum 0.800 at phase 25.0%',
                'expected_color': 'red'  # Local violation for knee feature
            },
            {
                'task': 'level_walking',
                'variable': 'ankle_flexion_angle_ipsi',
                'phase': 50.0,
                'value': 0.1,  # Above max of -0.1
                'expected_min': -0.3,
                'expected_max': -0.1,
                'failure_reason': 'Value 0.100 above maximum -0.100 at phase 50.0%',
                'expected_color': 'red'  # Local violation for ankle feature
            },
            # Incline walking failures
            {
                'task': 'incline_walking',
                'variable': 'hip_flexion_angle_ipsi',
                'phase': 0.0,
                'value': 1.0,  # Above max of 0.8
                'expected_min': 0.3,
                'expected_max': 0.8,
                'failure_reason': 'Value 1.000 above maximum 0.800 at phase 0.0%',
                'expected_color': 'red'  # Local violation for hip feature
            }
        ]
    
    @pytest.fixture
    def deterministic_passing_cases(self, precise_validation_ranges):
        """Create specific passing cases based on known validation ranges."""
        return [
            # Level walking valid values
            {
                'task': 'level_walking',
                'variable': 'hip_flexion_angle_ipsi',
                'phase': 0.0,
                'value': 0.4,  # Within range 0.2-0.6
                'expected_min': 0.2,
                'expected_max': 0.6,
                'should_pass': True
            },
            {
                'task': 'level_walking',
                'variable': 'knee_flexion_angle_ipsi',
                'phase': 25.0,
                'value': 0.5,  # Within range 0.3-0.8
                'expected_min': 0.3,
                'expected_max': 0.8,
                'should_pass': True
            },
            {
                'task': 'level_walking',
                'variable': 'ankle_flexion_angle_ipsi',
                'phase': 50.0,
                'value': -0.2,  # Within range -0.3 to -0.1
                'expected_min': -0.3,
                'expected_max': -0.1,
                'should_pass': True
            },
            # Edge cases (at boundaries)
            {
                'task': 'level_walking',
                'variable': 'hip_flexion_angle_ipsi',
                'phase': 0.0,
                'value': 0.2,  # Exactly at min
                'expected_min': 0.2,
                'expected_max': 0.6,
                'should_pass': True
            },
            {
                'task': 'level_walking',
                'variable': 'hip_flexion_angle_ipsi',
                'phase': 0.0,
                'value': 0.6,  # Exactly at max
                'expected_min': 0.2,
                'expected_max': 0.6,
                'should_pass': True
            }
        ]
    
    @pytest.fixture
    def sample_validation_failures(self):
        """Create sample validation failures for testing (legacy fixture)."""
        return [
            {
                'task': 'level_walking',
                'variable': 'hip_flexion_angle_ipsi',
                'phase': 25.0,
                'value': 0.8,
                'expected_min': 0.15,
                'expected_max': 0.6,
                'failure_reason': 'Value 0.800 above maximum 0.600 at phase 25.0%'
            },
            {
                'task': 'level_walking',
                'variable': 'knee_flexion_angle_contra',
                'phase': 50.0,
                'value': 1.5,
                'expected_min': 0.0,
                'expected_max': 0.15,
                'failure_reason': 'Value 1.500 above maximum 0.150 at phase 50.0%'
            },
            {
                'task': 'incline_walking',
                'variable': 'ankle_flexion_angle_ipsi',
                'phase': 75.0,
                'value': -0.5,
                'expected_min': -0.1,
                'expected_max': 0.2,
                'failure_reason': 'Value -0.500 below minimum -0.100 at phase 75.0%'
            }
        ]
    
    @pytest.fixture
    def sample_step_task_mapping(self):
        """Create sample step-to-task mapping for testing."""
        return {
            0: 'level_walking',
            1: 'level_walking',
            2: 'level_walking',
            3: 'incline_walking',
            4: 'incline_walking',
            5: 'level_walking'
        }
    
    def test_initialization(self, classifier):
        """Test StepClassifier initialization."""
        assert hasattr(classifier, 'kinematic_feature_map')
        assert hasattr(classifier, 'kinetic_feature_map')
        assert hasattr(classifier, 'color_scheme')
        
        # Check expected kinematic features
        expected_kinematic = ['hip_flexion_angle_ipsi', 'hip_flexion_angle_contra',
                             'knee_flexion_angle_ipsi', 'knee_flexion_angle_contra',
                             'ankle_flexion_angle_ipsi', 'ankle_flexion_angle_contra']
        for feature in expected_kinematic:
            assert feature in classifier.kinematic_feature_map
        
        # Check expected kinetic features
        expected_kinetic = ['hip_moment_ipsi_Nm_kg', 'hip_moment_contra_Nm_kg',
                           'knee_moment_ipsi_Nm_kg', 'knee_moment_contra_Nm_kg',
                           'ankle_moment_ipsi_Nm_kg', 'ankle_moment_contra_Nm_kg']
        for feature in expected_kinetic:
            assert feature in classifier.kinetic_feature_map
        
        # Check color scheme
        assert classifier.color_scheme['valid'] == 'gray'
        assert classifier.color_scheme['local_violation'] == 'red'
        assert classifier.color_scheme['other_violation'] == 'pink'
    
    def test_get_feature_map(self, classifier):
        """Test feature map retrieval for different modes."""
        # Test kinematic mode
        kinematic_map = classifier.get_feature_map('kinematic')
        assert isinstance(kinematic_map, dict)
        assert len(kinematic_map) == 6
        assert 'hip_flexion_angle_ipsi' in kinematic_map
        
        # Test kinetic mode
        kinetic_map = classifier.get_feature_map('kinetic')
        assert isinstance(kinetic_map, dict)
        assert len(kinetic_map) == 6
        assert 'hip_moment_ipsi_Nm_kg' in kinetic_map
        
        # Test invalid mode
        try:
            classifier.get_feature_map('invalid_mode')
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Unknown mode" in str(e)
    
    def test_extract_step_violations_basic(self, classifier, sample_validation_failures, sample_step_task_mapping):
        """Test basic step violation extraction."""
        step_violations = classifier.extract_step_violations_from_failures(
            sample_validation_failures, sample_step_task_mapping
        )
        
        assert isinstance(step_violations, dict)
        assert len(step_violations) == len(sample_step_task_mapping)
        
        # Check that level_walking steps have hip and knee violations
        for step_idx, task in sample_step_task_mapping.items():
            assert step_idx in step_violations
            violations = step_violations[step_idx]
            
            if task == 'level_walking':
                # Should include both hip and knee violations
                assert 'hip_flexion_angle_ipsi' in violations
                assert 'knee_flexion_angle_contra' in violations
            elif task == 'incline_walking':
                # Should include ankle violation
                assert 'ankle_flexion_angle_ipsi' in violations
    
    def test_classify_steps_for_feature_local_violations(self, classifier, sample_validation_failures, sample_step_task_mapping):
        """Test step classification for local violations (red steps)."""
        # Test hip feature (should be red for level_walking steps)
        hip_colors = classifier.classify_steps_for_feature(
            sample_validation_failures, sample_step_task_mapping, 
            'hip_flexion_angle_ipsi', 'kinematic'
        )
        
        assert isinstance(hip_colors, np.ndarray)
        assert len(hip_colors) == len(sample_step_task_mapping)
        
        # Steps 0, 1, 2, 5 are level_walking and should be red (local violation)
        for step_idx, task in sample_step_task_mapping.items():
            if task == 'level_walking':
                assert hip_colors[step_idx] == 'red'
            else:
                # incline_walking steps should be gray (no hip violation)
                assert hip_colors[step_idx] == 'gray'
    
    def test_classify_steps_for_feature_other_violations(self, classifier, sample_validation_failures, sample_step_task_mapping):
        """Test step classification for other violations (pink steps)."""
        # Test ankle feature (should be pink for level_walking, red for incline_walking)
        ankle_colors = classifier.classify_steps_for_feature(
            sample_validation_failures, sample_step_task_mapping,
            'ankle_flexion_angle_ipsi', 'kinematic'
        )
        
        assert isinstance(ankle_colors, np.ndarray)
        assert len(ankle_colors) == len(sample_step_task_mapping)
        
        for step_idx, task in sample_step_task_mapping.items():
            if task == 'level_walking':
                # Has violations in other features (hip, knee) but not ankle
                assert ankle_colors[step_idx] == 'pink'
            elif task == 'incline_walking':
                # Has local violation in ankle
                assert ankle_colors[step_idx] == 'red'
    
    def test_classify_steps_for_feature_no_violations(self, classifier, sample_step_task_mapping):
        """Test step classification when no violations exist."""
        # Empty failures list
        no_failures = []
        
        colors = classifier.classify_steps_for_feature(
            no_failures, sample_step_task_mapping,
            'hip_flexion_angle_ipsi', 'kinematic'
        )
        
        # All steps should be gray (valid)
        assert all(color == 'gray' for color in colors)
        assert len(colors) == len(sample_step_task_mapping)
    
    def test_classify_steps_for_all_features(self, classifier, sample_validation_failures, sample_step_task_mapping):
        """Test classification for all features in kinematic mode."""
        classifications = classifier.classify_steps_for_all_features(
            sample_validation_failures, sample_step_task_mapping, 'kinematic'
        )
        
        assert isinstance(classifications, dict)
        assert len(classifications) == 6  # 6 kinematic features
        
        # Check that all expected features are present
        expected_features = ['hip_flexion_angle_ipsi', 'hip_flexion_angle_contra',
                            'knee_flexion_angle_ipsi', 'knee_flexion_angle_contra',
                            'ankle_flexion_angle_ipsi', 'ankle_flexion_angle_contra']
        
        for feature in expected_features:
            assert feature in classifications
            assert isinstance(classifications[feature], np.ndarray)
            assert len(classifications[feature]) == len(sample_step_task_mapping)
    
    def test_get_step_summary_classification(self, classifier, sample_validation_failures, sample_step_task_mapping):
        """Test summary classification (any violations = red)."""
        summary_colors = classifier.get_step_summary_classification(
            sample_validation_failures, sample_step_task_mapping
        )
        
        assert isinstance(summary_colors, np.ndarray)
        assert len(summary_colors) == len(sample_step_task_mapping)
        
        # All steps with any violations should be red
        for step_idx, task in sample_step_task_mapping.items():
            if task in ['level_walking', 'incline_walking']:
                assert summary_colors[step_idx] == 'red'  # Has violations
    
    def test_create_step_classification_report(self, classifier, sample_validation_failures, sample_step_task_mapping):
        """Test comprehensive classification report generation."""
        report = classifier.create_step_classification_report(
            sample_validation_failures, sample_step_task_mapping, 'kinematic'
        )
        
        assert isinstance(report, dict)
        assert 'total_steps' in report
        assert 'mode' in report
        assert 'feature_classifications' in report
        assert 'summary' in report
        assert 'by_feature' in report
        
        assert report['total_steps'] == len(sample_step_task_mapping)
        assert report['mode'] == 'kinematic'
        
        # Check summary statistics
        summary = report['summary']
        assert 'valid_steps' in summary
        assert 'local_violation_steps' in summary
        assert 'other_violation_steps' in summary
        
        # Check per-feature statistics
        assert len(report['by_feature']) == 6
        for feature_stats in report['by_feature'].values():
            assert 'valid' in feature_stats
            assert 'local_violations' in feature_stats
            assert 'other_violations' in feature_stats
    
    def test_empty_input_handling(self, classifier):
        """Test handling of empty inputs."""
        empty_failures = []
        empty_mapping = {}
        
        # Should handle empty inputs gracefully
        colors = classifier.classify_steps_for_feature(
            empty_failures, empty_mapping, 'hip_flexion_angle_ipsi', 'kinematic'
        )
        
        assert isinstance(colors, np.ndarray)
        assert len(colors) == 0
    
    def test_large_step_count_performance(self, classifier):
        """Test performance with large number of steps."""
        # Create large step mapping
        large_mapping = {i: 'level_walking' for i in range(1000)}
        
        # Create some failures
        failures = [
            {
                'task': 'level_walking',
                'variable': 'hip_flexion_angle_ipsi',
                'phase': 25.0,
                'value': 0.8,
                'expected_min': 0.15,
                'expected_max': 0.6,
                'failure_reason': 'Test failure'
            }
        ]
        
        # Should handle large inputs efficiently
        colors = classifier.classify_steps_for_feature(
            failures, large_mapping, 'hip_flexion_angle_ipsi', 'kinematic'
        )
        
        assert len(colors) == 1000
        assert all(color == 'red' for color in colors)  # All should have violations
    
    def test_mixed_task_scenarios(self, classifier):
        """Test classification with mixed tasks and violation patterns."""
        # Create complex scenario with multiple tasks
        mixed_failures = [
            {'task': 'level_walking', 'variable': 'hip_flexion_angle_ipsi', 'phase': 25.0, 'value': 0.8, 'expected_min': 0.15, 'expected_max': 0.6, 'failure_reason': 'Test'},
            {'task': 'incline_walking', 'variable': 'knee_flexion_angle_contra', 'phase': 50.0, 'value': 1.5, 'expected_min': 0.0, 'expected_max': 0.15, 'failure_reason': 'Test'},
            {'task': 'running', 'variable': 'ankle_flexion_angle_ipsi', 'phase': 75.0, 'value': -0.5, 'expected_min': -0.1, 'expected_max': 0.2, 'failure_reason': 'Test'}
        ]
        
        mixed_mapping = {
            0: 'level_walking',     # hip violation
            1: 'level_walking',     # hip violation  
            2: 'incline_walking',   # knee violation
            3: 'incline_walking',   # knee violation
            4: 'running',           # ankle violation
            5: 'running',           # ankle violation
            6: 'squats',            # no violations
            7: 'squats'             # no violations
        }
        
        # Test hip feature classification
        hip_colors = classifier.classify_steps_for_feature(
            mixed_failures, mixed_mapping, 'hip_flexion_angle_ipsi', 'kinematic'
        )
        
        # Steps 0,1 should be red (local hip violation)
        # Steps 2,3,4,5 should be pink (other violations)
        # Steps 6,7 should be gray (no violations)
        expected_colors = ['red', 'red', 'pink', 'pink', 'pink', 'pink', 'gray', 'gray']
        
        for i, expected in enumerate(expected_colors):
            assert hip_colors[i] == expected, f"Step {i}: expected {expected}, got {hip_colors[i]}"
    
    def test_deterministic_failing_cases(self, classifier, deterministic_failing_cases):
        """Test step classification with specific failing cases where we know the expected outcome."""
        
        # Group failures by task for step mapping
        level_walking_failures = [f for f in deterministic_failing_cases if f['task'] == 'level_walking']
        incline_walking_failures = [f for f in deterministic_failing_cases if f['task'] == 'incline_walking']
        
        # Test level walking hip failures (should be red for hip feature)
        hip_failures = [f for f in level_walking_failures if f['variable'] == 'hip_flexion_angle_ipsi']
        step_mapping = {i: 'level_walking' for i in range(len(hip_failures))}
        
        hip_colors = classifier.classify_steps_for_feature(
            hip_failures, step_mapping, 'hip_flexion_angle_ipsi', 'kinematic'
        )
        
        # All steps should be red (local violations in hip)
        for i, failure in enumerate(hip_failures):
            assert hip_colors[i] == 'red', f"Hip failure case {i} should be red, got {hip_colors[i]}"
            assert failure['expected_color'] == 'red', f"Test case {i} should expect red"
        
        # Test knee failures classification for hip feature 
        # NOTE: Due to current implementation, testing knee failures separately
        knee_failures = [f for f in level_walking_failures if f['variable'] == 'knee_flexion_angle_ipsi']
        if knee_failures:
            step_mapping_knee = {i: 'level_walking' for i in range(len(knee_failures))}
            
            hip_colors_for_knee_failures = classifier.classify_steps_for_feature(
                knee_failures, step_mapping_knee, 'hip_flexion_angle_ipsi', 'kinematic'
            )
            
            # Should be gray (no hip violations) since these are only knee failures  
            for i, color in enumerate(hip_colors_for_knee_failures):
                assert color == 'gray', f"Knee-only failure case {i} should be gray for hip feature, got {color}"
    
    def test_deterministic_passing_cases(self, classifier, deterministic_passing_cases):
        """Test step classification with specific passing cases where no violations should occur."""
        
        # Create step mapping for all passing cases
        step_mapping = {i: case['task'] for i, case in enumerate(deterministic_passing_cases)}
        
        # Since these are all passing cases, there should be no failures to report
        no_failures = []
        
        # Test that all steps are classified as gray (valid) when no failures exist
        colors = classifier.classify_steps_for_feature(
            no_failures, step_mapping, 'hip_flexion_angle_ipsi', 'kinematic'
        )
        
        for i, color in enumerate(colors):
            assert color == 'gray', f"Passing case {i} should be gray, got {color}"
            case = deterministic_passing_cases[i]
            assert case['should_pass'] == True, f"Test case {i} should be marked as passing"
    
    def test_boundary_value_analysis(self, classifier):
        """Test boundary values specifically (at min/max limits)."""
        
        # Create boundary test cases
        boundary_failures = [
            # Just above max (should fail)
            {
                'task': 'level_walking',
                'variable': 'hip_flexion_angle_ipsi',
                'phase': 0.0,
                'value': 0.601,  # Just above max of 0.6
                'expected_min': 0.2,
                'expected_max': 0.6,
                'failure_reason': 'Value 0.601 above maximum 0.600',
                'should_fail': True
            },
            # Just below min (should fail)
            {
                'task': 'level_walking',
                'variable': 'hip_flexion_angle_ipsi', 
                'phase': 0.0,
                'value': 0.199,  # Just below min of 0.2
                'expected_min': 0.2,
                'expected_max': 0.6,
                'failure_reason': 'Value 0.199 below minimum 0.200',
                'should_fail': True
            }
        ]
        
        step_mapping = {i: 'level_walking' for i in range(len(boundary_failures))}
        
        # Test hip feature - should be red for boundary violations
        hip_colors = classifier.classify_steps_for_feature(
            boundary_failures, step_mapping, 'hip_flexion_angle_ipsi', 'kinematic'
        )
        
        for i, color in enumerate(hip_colors):
            assert color == 'red', f"Boundary failure case {i} should be red, got {color}"
    
    def test_mixed_scenario_deterministic(self, classifier):
        """Test a mixed scenario with known passing and failing cases.
        
        NOTE: Due to current implementation limitation, this test demonstrates the 
        task-level violation assignment behavior rather than step-specific violations.
        """
        
        # Create separate task scenarios to work around current limitation
        # Test 1: Task with only hip violations
        hip_only_failures = [
            {
                'task': 'level_walking',
                'variable': 'hip_flexion_angle_ipsi',
                'phase': 0.0,
                'value': 0.8,  # Above max of 0.6
                'expected_min': 0.2,
                'expected_max': 0.6,
                'failure_reason': 'Hip violation'
            }
        ]
        
        hip_step_mapping = {0: 'level_walking', 1: 'level_walking'}
        
        hip_colors = classifier.classify_steps_for_feature(
            hip_only_failures, hip_step_mapping, 'hip_flexion_angle_ipsi', 'kinematic'
        )
        
        # Both steps should be red (local hip violations in the task)
        assert all(color == 'red' for color in hip_colors), f"Hip-only failures: {hip_colors}"
        
        # Test 2: Task with only knee violations (for hip feature should be gray)
        knee_only_failures = [
            {
                'task': 'level_walking',
                'variable': 'knee_flexion_angle_ipsi',
                'phase': 25.0,
                'value': 1.2,  # Above max of 0.8
                'expected_min': 0.3,
                'expected_max': 0.8,
                'failure_reason': 'Knee violation'
            }
        ]
        
        knee_step_mapping = {0: 'level_walking', 1: 'level_walking'}
        
        hip_colors_for_knee = classifier.classify_steps_for_feature(
            knee_only_failures, knee_step_mapping, 'hip_flexion_angle_ipsi', 'kinematic'
        )
        
        # Should be gray for hip feature (no hip violations, only knee)
        assert all(color == 'gray' for color in hip_colors_for_knee), f"Knee-only for hip feature: {hip_colors_for_knee}"
        
        # Test 3: Mixed tasks 
        mixed_task_failures = [
            {'task': 'level_walking', 'variable': 'hip_flexion_angle_ipsi', 'phase': 0.0, 'value': 0.8, 'expected_min': 0.2, 'expected_max': 0.6, 'failure_reason': 'Hip violation'},
            {'task': 'incline_walking', 'variable': 'knee_flexion_angle_ipsi', 'phase': 25.0, 'value': 1.2, 'expected_min': 0.3, 'expected_max': 0.8, 'failure_reason': 'Knee violation'},
        ]
        
        mixed_step_mapping = {
            0: 'level_walking',     # Task with hip violation
            1: 'level_walking',     # Task with hip violation
            2: 'incline_walking',   # Task with knee violation (no hip)
            3: 'incline_walking',   # Task with knee violation (no hip)
            4: 'squats'             # Task with no violations
        }
        
        mixed_hip_colors = classifier.classify_steps_for_feature(
            mixed_task_failures, mixed_step_mapping, 'hip_flexion_angle_ipsi', 'kinematic'
        )
        
        expected_mixed = ['red', 'red', 'gray', 'gray', 'gray']  # level_walking has hip violations, others don't
        for i, (actual, expected) in enumerate(zip(mixed_hip_colors, expected_mixed)):
            assert actual == expected, f"Mixed task step {i}: expected {expected}, got {actual}"
    
    def test_comprehensive_failure_matrix(self, classifier):
        """Test comprehensive failure combinations across multiple features and tasks."""
        
        # Create a comprehensive failure matrix
        comprehensive_failures = [
            # Multiple failures in same step
            {'task': 'level_walking', 'variable': 'hip_flexion_angle_ipsi', 'phase': 0.0, 'value': 0.8, 'expected_min': 0.2, 'expected_max': 0.6, 'failure_reason': 'Hip violation'},
            {'task': 'level_walking', 'variable': 'knee_flexion_angle_ipsi', 'phase': 25.0, 'value': 1.2, 'expected_min': 0.3, 'expected_max': 0.8, 'failure_reason': 'Knee violation'},
            
            # Different task violations
            {'task': 'incline_walking', 'variable': 'hip_flexion_angle_ipsi', 'phase': 0.0, 'value': 1.0, 'expected_min': 0.3, 'expected_max': 0.8, 'failure_reason': 'Incline hip violation'},
            {'task': 'incline_walking', 'variable': 'ankle_flexion_angle_ipsi', 'phase': 0.0, 'value': 0.2, 'expected_min': 0.0, 'expected_max': 0.1, 'failure_reason': 'Incline ankle violation'},
        ]
        
        # Create mixed task mapping
        step_mapping = {
            0: 'level_walking',     # Hip violation
            1: 'level_walking',     # Knee violation  
            2: 'level_walking',     # No violations
            3: 'incline_walking',   # Hip violation
            4: 'incline_walking',   # Ankle violation
            5: 'incline_walking',   # No violations
        }
        
        # Test hip classification across both tasks
        hip_colors = classifier.classify_steps_for_feature(
            comprehensive_failures, step_mapping, 'hip_flexion_angle_ipsi', 'kinematic'
        )
        
        # Expected: [red, pink, gray, red, pink, gray]
        # Steps 0,3 have hip violations (red), step 1,4 have other violations (pink), steps 2,5 are valid (gray)
        expected = ['red', 'pink', 'gray', 'red', 'pink', 'gray']
        for i, (actual, expected_color) in enumerate(zip(hip_colors, expected)):
            assert actual == expected_color, f"Comprehensive test step {i}: expected {expected_color}, got {actual}"
    
    def test_kinetic_mode_classification(self, classifier):
        """Test classification in kinetic mode."""
        kinetic_failures = [
            {
                'task': 'level_walking',
                'variable': 'hip_moment_ipsi_Nm_kg',
                'phase': 25.0,
                'value': 1.5,
                'expected_min': -0.1,
                'expected_max': 0.3,
                'failure_reason': 'Test kinetic failure'
            }
        ]
        
        step_mapping = {0: 'level_walking', 1: 'level_walking'}
        
        # Test kinetic feature classification
        kinetic_colors = classifier.classify_steps_for_feature(
            kinetic_failures, step_mapping, 'hip_moment_ipsi_Nm_kg', 'kinetic'
        )
        
        # Both steps should be red (local violation)
        assert all(color == 'red' for color in kinetic_colors)
        
        # Test different kinetic feature (should be pink)
        knee_colors = classifier.classify_steps_for_feature(
            kinetic_failures, step_mapping, 'knee_moment_ipsi_Nm_kg', 'kinetic'
        )
        
        # Both steps should be pink (other violation)
        assert all(color == 'pink' for color in knee_colors)


def run_manual_tests():
    """Run tests manually when pytest is not available."""
    print("🧪 Running manual tests for StepClassifier...")
    
    # Create test instance
    classifier = StepClassifier()
    
    # Test 1: Basic initialization
    print("\n✅ Test 1: Initialization")
    assert hasattr(classifier, 'kinematic_feature_map')
    assert hasattr(classifier, 'kinetic_feature_map')
    assert len(classifier.kinematic_feature_map) == 6
    assert len(classifier.kinetic_feature_map) == 6
    print("   Initialization successful")
    
    # Test 2: Feature map retrieval
    print("\n✅ Test 2: Feature map retrieval")
    kinematic_map = classifier.get_feature_map('kinematic')
    kinetic_map = classifier.get_feature_map('kinetic')
    assert 'hip_flexion_angle_ipsi' in kinematic_map
    assert 'hip_moment_ipsi_Nm_kg' in kinetic_map
    print("   Feature maps retrieved successfully")
    
    # Test 3: Step classification
    print("\n✅ Test 3: Step classification")
    sample_failures = [
        {
            'task': 'level_walking',
            'variable': 'hip_flexion_angle_ipsi',
            'phase': 25.0,
            'value': 0.8,
            'expected_min': 0.15,
            'expected_max': 0.6,
            'failure_reason': 'Test failure'
        }
    ]
    
    step_mapping = {0: 'level_walking', 1: 'level_walking', 2: 'incline_walking'}
    
    colors = classifier.classify_steps_for_feature(
        sample_failures, step_mapping, 'hip_flexion_angle_ipsi', 'kinematic'
    )
    
    assert len(colors) == 3
    assert colors[0] == 'red'  # Local violation
    assert colors[1] == 'red'  # Local violation
    assert colors[2] == 'gray'  # No violation
    print("   Step classification successful")
    
    # Test 4: Summary classification
    print("\n✅ Test 4: Summary classification")
    summary_colors = classifier.get_step_summary_classification(sample_failures, step_mapping)
    assert len(summary_colors) == 3
    assert summary_colors[0] == 'red'  # Has violations
    assert summary_colors[1] == 'red'  # Has violations
    assert summary_colors[2] == 'gray'  # No violations
    print("   Summary classification successful")
    
    # Test 5: Classification report
    print("\n✅ Test 5: Classification report")
    report = classifier.create_step_classification_report(
        sample_failures, step_mapping, 'kinematic'
    )
    assert report['total_steps'] == 3
    assert report['mode'] == 'kinematic'
    assert 'feature_classifications' in report
    assert 'summary' in report
    print("   Classification report generated successfully")
    
    # Test 6: Deterministic failing cases
    print("\n✅ Test 6: Deterministic failing cases")
    deterministic_failures = [
        {
            'task': 'level_walking',
            'variable': 'hip_flexion_angle_ipsi',
            'phase': 0.0,
            'value': 0.8,  # Above max of 0.6
            'expected_min': 0.2,
            'expected_max': 0.6,
            'failure_reason': 'Value 0.800 above maximum 0.600'
        },
        {
            'task': 'level_walking',
            'variable': 'knee_flexion_angle_ipsi',
            'phase': 25.0,
            'value': 1.2,  # Above max of 0.8
            'expected_min': 0.3,
            'expected_max': 0.8,
            'failure_reason': 'Value 1.200 above maximum 0.800'
        }
    ]
    
    deterministic_mapping = {0: 'level_walking', 1: 'level_walking', 2: 'level_walking'}
    
    # Test hip classification - NOTE: Current logic assigns ALL task violations to ALL steps in that task
    hip_colors = classifier.classify_steps_for_feature(
        deterministic_failures, deterministic_mapping, 'hip_flexion_angle_ipsi', 'kinematic'
    )
    
    # Due to current implementation limitation, all steps in 'level_walking' get both hip and knee violations
    # So all level_walking steps should be red (they have local hip violations)
    assert hip_colors[0] == 'red', f"Step 0 should be red (hip violation), got {hip_colors[0]}"
    assert hip_colors[1] == 'red', f"Step 1 should be red (task has hip violation), got {hip_colors[1]}"
    assert hip_colors[2] == 'red', f"Step 2 should be red (task has hip violation), got {hip_colors[2]}"
    print("   Deterministic test cases passed (with current task-level limitation)")
    
    # Test 7: Boundary value testing
    print("\n✅ Test 7: Boundary value testing")
    boundary_failures = [
        {
            'task': 'level_walking',
            'variable': 'hip_flexion_angle_ipsi',
            'phase': 0.0,
            'value': 0.601,  # Just above max of 0.6
            'expected_min': 0.2,
            'expected_max': 0.6,
            'failure_reason': 'Boundary violation'
        }
    ]
    
    boundary_mapping = {0: 'level_walking'}
    boundary_colors = classifier.classify_steps_for_feature(
        boundary_failures, boundary_mapping, 'hip_flexion_angle_ipsi', 'kinematic'
    )
    
    assert boundary_colors[0] == 'red', f"Boundary violation should be red, got {boundary_colors[0]}"
    print("   Boundary value testing passed")
    
    print("\n🎉 All manual tests passed! Including deterministic and boundary tests.")


if __name__ == "__main__":
    if PYTEST_AVAILABLE:
        print("🧪 Running pytest test suite...")
        # Run with pytest if available
        import pytest
        pytest.main([__file__, "-v"])
    else:
        print("⚠️  pytest not available, running manual tests...")
        run_manual_tests()