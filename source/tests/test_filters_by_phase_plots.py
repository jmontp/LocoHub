#!/usr/bin/env python3
"""
Test suite for filters_by_phase_plots.py functionality

Tests the updated filters by phase plotting function with:
1. Basic functionality (no data)
2. Data overlay functionality
3. Violation detection and highlighting
4. Both kinematic and kinetic modes
"""

import numpy as np
import pytest
import sys
import os
from pathlib import Path
import tempfile
import shutil

# Add source directories to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root / 'source' / 'visualization'))
sys.path.append(str(project_root / 'source'))

from filters_by_phase_plots import (
    create_filters_by_phase_plot, 
    classify_step_violations,
    detect_filter_violations
)


class TestFiltersByPhasePlots:
    """Test suite for filters by phase plotting functionality"""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory for tests"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_kinematic_validation_data(self):
        """Create sample kinematic validation data for testing"""
        return {
            'level_walking': {
                0: {
                    'hip_flexion_angle_ipsi': {'min': 0.15, 'max': 0.6},
                    'knee_flexion_angle_ipsi': {'min': 0.0, 'max': 0.15},
                    'ankle_flexion_angle_ipsi': {'min': -0.05, 'max': 0.05},
                    'hip_flexion_angle_contra': {'min': -0.35, 'max': 0.0},
                    'knee_flexion_angle_contra': {'min': 0.5, 'max': 0.8},
                    'ankle_flexion_angle_contra': {'min': -0.4, 'max': -0.2}
                },
                25: {
                    'hip_flexion_angle_ipsi': {'min': -0.05, 'max': 0.35},
                    'knee_flexion_angle_ipsi': {'min': 0.05, 'max': 0.25},
                    'ankle_flexion_angle_ipsi': {'min': 0.05, 'max': 0.25},
                    'hip_flexion_angle_contra': {'min': 0.3, 'max': 0.9},
                    'knee_flexion_angle_contra': {'min': 0.8, 'max': 1.3},
                    'ankle_flexion_angle_contra': {'min': -0.1, 'max': 0.2}
                },
                50: {
                    'hip_flexion_angle_ipsi': {'min': -0.35, 'max': 0.0},
                    'knee_flexion_angle_ipsi': {'min': 0.5, 'max': 0.8},
                    'ankle_flexion_angle_ipsi': {'min': -0.4, 'max': -0.2},
                    'hip_flexion_angle_contra': {'min': 0.15, 'max': 0.6},
                    'knee_flexion_angle_contra': {'min': 0.0, 'max': 0.15},
                    'ankle_flexion_angle_contra': {'min': -0.05, 'max': 0.05}
                },
                75: {
                    'hip_flexion_angle_ipsi': {'min': 0.3, 'max': 0.9},
                    'knee_flexion_angle_ipsi': {'min': 0.8, 'max': 1.3},
                    'ankle_flexion_angle_ipsi': {'min': -0.1, 'max': 0.2},
                    'hip_flexion_angle_contra': {'min': -0.05, 'max': 0.35},
                    'knee_flexion_angle_contra': {'min': 0.05, 'max': 0.25},
                    'ankle_flexion_angle_contra': {'min': 0.05, 'max': 0.25}
                }
            }
        }
    
    @pytest.fixture
    def valid_kinematic_data(self):
        """Create valid kinematic data that should pass all filters"""
        num_steps = 5
        num_points = 150
        num_features = 6
        
        data = np.zeros((num_steps, num_points, num_features))
        phase_percent = np.linspace(0, 100, num_points)
        
        for step in range(num_steps):
            # Create realistic patterns within validation ranges
            # Hip flexion
            hip_pattern = 0.25 * np.sin(2 * np.pi * phase_percent / 100) + 0.3
            data[step, :, 0] = hip_pattern  # hip_ipsi
            data[step, :, 1] = hip_pattern  # hip_contra
            
            # Knee flexion
            knee_pattern = 0.4 * np.sin(np.pi * phase_percent / 100) + 0.3
            data[step, :, 2] = knee_pattern  # knee_ipsi
            data[step, :, 3] = knee_pattern  # knee_contra
            
            # Ankle flexion
            ankle_pattern = -0.15 * np.sin(2 * np.pi * phase_percent / 100) + 0.1
            data[step, :, 4] = ankle_pattern  # ankle_ipsi
            data[step, :, 5] = ankle_pattern  # ankle_contra
        
        return data
    
    @pytest.fixture
    def violating_kinematic_data(self):
        """Create kinematic data with known violations"""
        num_steps = 6
        num_points = 150
        num_features = 6
        
        data = np.zeros((num_steps, num_points, num_features))
        phase_percent = np.linspace(0, 100, num_points)
        
        # Start with valid baseline patterns
        for step in range(num_steps):
            hip_pattern = 0.25 * np.sin(2 * np.pi * phase_percent / 100) + 0.3
            data[step, :, 0] = hip_pattern
            data[step, :, 1] = hip_pattern
            
            knee_pattern = 0.4 * np.sin(np.pi * phase_percent / 100) + 0.3
            data[step, :, 2] = knee_pattern
            data[step, :, 3] = knee_pattern
            
            ankle_pattern = -0.15 * np.sin(2 * np.pi * phase_percent / 100) + 0.1
            data[step, :, 4] = ankle_pattern
            data[step, :, 5] = ankle_pattern
        
        # Add specific violations
        # Step 0: Hip ipsi violation (too high)
        data[0, :, 0] += 0.8
        
        # Step 1: Knee ipsi violation (too high)
        data[1, :, 2] += 1.2
        
        # Step 2: Ankle ipsi violation (too low)
        data[2, :, 4] -= 0.8
        
        # Step 3: Multiple violations (hip and knee)
        data[3, :, 0] += 0.7
        data[3, :, 2] += 1.0
        
        # Step 4: Contralateral violation
        data[4, :, 1] += 0.9
        
        # Step 5: Valid (no violations)
        
        return data
    
    def test_basic_plot_generation_no_data(self, sample_kinematic_validation_data, temp_output_dir):
        """Test basic plot generation without data overlay"""
        filepath = create_filters_by_phase_plot(
            validation_data=sample_kinematic_validation_data,
            task_name='level_walking',
            output_dir=temp_output_dir,
            mode='kinematic'
        )
        
        assert os.path.exists(filepath)
        assert 'level_walking_kinematic_filters_by_phase.png' in filepath
        assert '_with_data' not in filepath
    
    def test_plot_generation_with_valid_data(self, sample_kinematic_validation_data, valid_kinematic_data, temp_output_dir):
        """Test plot generation with valid data overlay"""
        filepath = create_filters_by_phase_plot(
            validation_data=sample_kinematic_validation_data,
            task_name='level_walking',
            output_dir=temp_output_dir,
            mode='kinematic',
            data=valid_kinematic_data
        )
        
        assert os.path.exists(filepath)
        assert 'level_walking_kinematic_filters_by_phase_with_data.png' in filepath
    
    def test_plot_generation_with_violating_data(self, sample_kinematic_validation_data, violating_kinematic_data, temp_output_dir):
        """Test plot generation with violating data overlay"""
        filepath = create_filters_by_phase_plot(
            validation_data=sample_kinematic_validation_data,
            task_name='level_walking',
            output_dir=temp_output_dir,
            mode='kinematic',
            data=violating_kinematic_data
        )
        
        assert os.path.exists(filepath)
        assert 'level_walking_kinematic_filters_by_phase_with_data.png' in filepath
    
    def test_violation_detection_valid_data(self, sample_kinematic_validation_data, valid_kinematic_data):
        """Test violation detection with valid data"""
        task_data = sample_kinematic_validation_data['level_walking']
        feature_map = {
            ('hip_flexion_angle', 'ipsi'): 0,
            ('hip_flexion_angle', 'contra'): 1,
            ('knee_flexion_angle', 'ipsi'): 2,
            ('knee_flexion_angle', 'contra'): 3,
            ('ankle_flexion_angle', 'ipsi'): 4,
            ('ankle_flexion_angle', 'contra'): 5
        }
        
        global_violations, local_violations = detect_filter_violations(
            valid_kinematic_data, task_data, feature_map, 'kinematic', 0
        )
        
        # Valid data should have no violations
        assert len(global_violations) == 0
        assert len(local_violations) == 0
    
    def test_violation_detection_violating_data(self, sample_kinematic_validation_data, violating_kinematic_data):
        """Test violation detection with violating data"""
        task_data = sample_kinematic_validation_data['level_walking']
        feature_map = {
            ('hip_flexion_angle', 'ipsi'): 0,
            ('hip_flexion_angle', 'contra'): 1,
            ('knee_flexion_angle', 'ipsi'): 2,
            ('knee_flexion_angle', 'contra'): 3,
            ('ankle_flexion_angle', 'ipsi'): 4,
            ('ankle_flexion_angle', 'contra'): 5
        }
        
        # Test hip ipsi violations (feature 0)
        global_violations, local_violations = detect_filter_violations(
            violating_kinematic_data, task_data, feature_map, 'kinematic', 0
        )
        
        # Should detect global violations
        assert len(global_violations) > 0
        # Should detect local violations for hip ipsi (steps 0 and 3)
        assert len(local_violations) > 0
        
        # Test knee ipsi violations (feature 2)
        global_violations, local_violations = detect_filter_violations(
            violating_kinematic_data, task_data, feature_map, 'kinematic', 2
        )
        
        # Should detect local violations for knee ipsi (steps 1 and 3)
        assert len(local_violations) > 0
    
    def test_data_shape_validation(self, sample_kinematic_validation_data, temp_output_dir):
        """Test that function handles different data shapes correctly"""
        # Test with wrong number of features
        wrong_shape_data = np.random.randn(5, 150, 3)  # Only 3 features instead of 6
        
        # Should not crash, but should skip plotting for missing features
        filepath = create_filters_by_phase_plot(
            validation_data=sample_kinematic_validation_data,
            task_name='level_walking',
            output_dir=temp_output_dir,
            mode='kinematic',
            data=wrong_shape_data
        )
        
        assert os.path.exists(filepath)
    
    def test_missing_task_error(self, sample_kinematic_validation_data, temp_output_dir):
        """Test error handling for missing task"""
        with pytest.raises(ValueError, match="Task nonexistent_task not found"):
            create_filters_by_phase_plot(
                validation_data=sample_kinematic_validation_data,
                task_name='nonexistent_task',
                output_dir=temp_output_dir,
                mode='kinematic'
            )
    
    def test_kinetic_mode_placeholder(self, temp_output_dir):
        """Test kinetic mode with minimal data"""
        # Create minimal kinetic validation data
        kinetic_validation_data = {
            'level_walking': {
                0: {
                    'hip_moment_ipsi_Nm_kg': {'min': -0.1, 'max': 0.3},
                    'knee_moment_ipsi_Nm_kg': {'min': -0.2, 'max': 0.1},
                    'ankle_moment_ipsi_Nm_kg': {'min': -0.3, 'max': 0.3}
                }
            }
        }
        
        # Should work without crashing
        filepath = create_filters_by_phase_plot(
            validation_data=kinetic_validation_data,
            task_name='level_walking',
            output_dir=temp_output_dir,
            mode='kinetic'
        )
        
        assert os.path.exists(filepath)
        assert 'kinetic' in filepath


class TestViolationScenarios:
    """Test specific violation scenarios"""
    
    @pytest.fixture
    def violation_test_data(self):
        """Create data with specific violation patterns for detailed testing"""
        num_steps = 4
        num_points = 150
        num_features = 6
        
        data = np.zeros((num_steps, num_points, num_features))
        
        # Step 0: Only hip ipsi violation
        data[0, :, 0] = 1.0  # Hip ipsi - violates upper bound
        data[0, :, 1] = 0.3  # Hip contra - valid
        data[0, :, 2] = 0.1  # Knee ipsi - valid
        data[0, :, 3] = 0.1  # Knee contra - valid
        data[0, :, 4] = 0.0  # Ankle ipsi - valid
        data[0, :, 5] = 0.0  # Ankle contra - valid
        
        # Step 1: Only knee contra violation
        data[1, :, 0] = 0.3  # Hip ipsi - valid
        data[1, :, 1] = 0.3  # Hip contra - valid
        data[1, :, 2] = 0.1  # Knee ipsi - valid
        data[1, :, 3] = 2.0  # Knee contra - violates upper bound
        data[1, :, 4] = 0.0  # Ankle ipsi - valid
        data[1, :, 5] = 0.0  # Ankle contra - valid
        
        # Step 2: Multiple violations (hip + ankle)
        data[2, :, 0] = 1.0  # Hip ipsi - violates upper bound
        data[2, :, 1] = 0.3  # Hip contra - valid
        data[2, :, 2] = 0.1  # Knee ipsi - valid
        data[2, :, 3] = 0.1  # Knee contra - valid
        data[2, :, 4] = -1.0  # Ankle ipsi - violates lower bound
        data[2, :, 5] = 0.0  # Ankle contra - valid
        
        # Step 3: No violations (all valid)
        data[3, :, 0] = 0.3  # Hip ipsi - valid
        data[3, :, 1] = 0.3  # Hip contra - valid
        data[3, :, 2] = 0.1  # Knee ipsi - valid
        data[3, :, 3] = 0.1  # Knee contra - valid
        data[3, :, 4] = 0.0  # Ankle ipsi - valid
        data[3, :, 5] = 0.0  # Ankle contra - valid
        
        return data
    
    def test_local_vs_global_violations(self, violation_test_data):
        """Test distinction between local and global violations"""
        task_data = {
            0: {
                'hip_flexion_angle_ipsi': {'min': 0.15, 'max': 0.6},
                'hip_flexion_angle_contra': {'min': 0.15, 'max': 0.6},
                'knee_flexion_angle_ipsi': {'min': 0.0, 'max': 0.15},
                'knee_flexion_angle_contra': {'min': 0.0, 'max': 0.15},
                'ankle_flexion_angle_ipsi': {'min': -0.05, 'max': 0.05},
                'ankle_flexion_angle_contra': {'min': -0.05, 'max': 0.05}
            }
        }
        
        feature_map = {
            ('hip_flexion_angle', 'ipsi'): 0,
            ('hip_flexion_angle', 'contra'): 1,
            ('knee_flexion_angle', 'ipsi'): 2,
            ('knee_flexion_angle', 'contra'): 3,
            ('ankle_flexion_angle', 'ipsi'): 4,
            ('ankle_flexion_angle', 'contra'): 5
        }
        
        # Test hip ipsi violations (feature 0)
        global_violations, local_violations = detect_filter_violations(
            violation_test_data, task_data, feature_map, 'kinematic', 0
        )
        
        # Steps 0 and 2 have hip ipsi violations (local)
        # Step 1 has knee contra violation (global but not local)
        # Step 3 has no violations
        
        assert 0 in local_violations  # Step 0 has local hip violation
        assert 2 in local_violations  # Step 2 has local hip violation
        assert 1 not in local_violations  # Step 1 has no hip violation
        
        assert 0 in global_violations  # Step 0 has violations
        assert 1 in global_violations  # Step 1 has violations
        assert 2 in global_violations  # Step 2 has violations
        assert 3 not in global_violations  # Step 3 has no violations


def run_tests():
    """Run all tests manually (for environments without pytest)"""
    print("Running filters_by_phase_plots tests...")
    
    # This would need to be implemented as a simple test runner
    # For now, use pytest if available
    try:
        import pytest
        pytest.main([__file__, '-v'])
    except ImportError:
        print("pytest not available. Install pytest to run full test suite.")
        print("Manual testing can be done by running the individual test methods.")


if __name__ == "__main__":
    run_tests()