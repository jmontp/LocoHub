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
3. **Edge Cases**: Tests with empty data, missing features, invalid inputs
4. **Integration Scenarios**: Tests with realistic validation failure data
5. **Performance**: Validates efficiency with large step counts
6. **Error Handling**: Tests proper error handling for invalid inputs

Test Categories:
- Unit tests for individual methods
- Integration tests with realistic validation data
- Edge case tests for robustness
- Performance tests for scalability

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
    def sample_validation_failures(self):
        """Create sample validation failures for testing."""
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
    
    print("\n🎉 All manual tests passed!")


if __name__ == "__main__":
    if PYTEST_AVAILABLE:
        print("🧪 Running pytest test suite...")
        # Run with pytest if available
        import pytest
        pytest.main([__file__, "-v"])
    else:
        print("⚠️  pytest not available, running manual tests...")
        run_manual_tests()