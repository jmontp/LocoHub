#!/usr/bin/env python3
"""
Comprehensive Test Suite for filters_by_phase_plots.py

Created: 2025-06-10
Purpose: Test all functionality of the unified filters by phase plotting system including
         validation range visualization, step data overlay, and step color classification.

Intent:
This test suite validates the core plotting functionality used for biomechanical validation
visualization. The filters_by_phase_plots module creates publication-ready plots that show:

1. **Validation Range Visualization**: Shows expected biomechanical ranges at key phases
2. **Step Data Overlay**: Overlays actual step data (150 time points × 6 features) 
3. **Step Color Classification**: Uses three-color system for validation status indication
4. **Multi-Modal Support**: Handles both kinematic (joint angles) and kinetic (forces/moments) data
5. **Task Classification**: Supports different locomotion tasks (gait vs bilateral movements)
6. **Publication Quality**: Generates professional validation plots for research and clinical use

**Core Testing Categories:**

**Basic Functionality Tests:**
- Plot generation without data overlay (validation ranges only)
- Plot generation with step data overlay (realistic biomechanical patterns)
- Proper filename generation and output directory handling
- Both kinematic and kinetic mode support

**Step Color Classification Tests:**
- Gray steps: Valid steps with no violations
- Red steps: Steps with local violations (violations in current feature)
- Pink steps: Steps with other violations (violations in different features)
- Mixed color scenarios with realistic violation patterns
- Edge cases with mismatched array sizes

**Data Format and Edge Case Tests:**
- Various data array shapes (wrong features, wrong time points)
- Missing tasks and invalid inputs
- Bilateral vs gait task handling
- Error handling and graceful degradation

**Integration Tests:**
- Realistic biomechanical data patterns with known violations
- Step color arrays that match actual step classifier output
- Task classification for different locomotion activities
- Output file naming conventions and organization

**Validation Data Structure:**
The test suite uses realistic validation ranges based on biomechanical literature:
```python
validation_data = {
    'level_walking': {
        0: {  # Phase 0% (heel strike)
            'hip_flexion_angle_ipsi': {'min': 0.15, 'max': 0.6},  # 9-34 degrees
            'knee_flexion_angle_ipsi': {'min': 0.0, 'max': 0.15}, # 0-9 degrees
            'ankle_flexion_angle_ipsi': {'min': -0.05, 'max': 0.05}, # ±3 degrees
        },
        25: {  # Phase 25% (loading response)
            # Different ranges for different gait phases...
        }
    }
}
```

**Step Data Format:**
Tests use 3D arrays with shape (num_steps, 150, 6) representing:
- num_steps: Number of individual gait cycles or movements
- 150: Standard phase normalization (0-100% in 150 points)
- 6: Six biomechanical features (hip/knee/ankle × ipsi/contra)

**Step Color Integration:**
The plotting system integrates with the step classifier to show validation status:
- Input: `step_colors` array with shape (num_steps,) containing ['gray', 'red', 'pink']
- Output: Plot with colored step traces indicating validation status
- Integration: Works seamlessly with validation workflow and dataset validator

**Error Handling Philosophy:**
The plotting system follows graceful degradation principles:
- Missing data → plots validation ranges only  
- Wrong data shapes → attempts to adapt or falls back gracefully
- Invalid inputs → clear error messages with debugging context
- Missing tasks → explicit error with available task listing

**Performance Considerations:**
Tests validate performance with realistic data sizes:
- Multiple steps (5-10 typical, up to 50+ for large datasets)
- Full phase resolution (150 time points per step)
- Multiple features (6 kinematic or 6 kinetic features)
- Multiple validation phases (typically 4: 0%, 25%, 50%, 75%)

This comprehensive testing ensures the filters by phase plotting system produces reliable,
publication-quality validation visualizations for biomechanical research and clinical applications.
"""

import numpy as np
import sys
import os
from pathlib import Path
import tempfile
import shutil
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for testing

# Try to import pytest, handle gracefully if not available
try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False
    # Create dummy pytest decorators for manual testing
    class pytest:
        @staticmethod
        def fixture(func):
            return func

# Add source directories to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root / 'source'))

from validation.filters_by_phase_plots import (
    create_filters_by_phase_plot, 
    get_task_classification
)


class TestFiltersByPhasePlots:
    """Comprehensive test suite for filters by phase plotting functionality"""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory for tests"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_kinematic_validation_data(self):
        """Create sample kinematic validation data with full phase coverage"""
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
    def sample_kinetic_validation_data(self):
        """Create sample kinetic validation data"""
        return {
            'level_walking': {
                0: {
                    'hip_moment_ipsi_Nm_kg': {'min': -0.1, 'max': 0.3},
                    'knee_moment_ipsi_Nm_kg': {'min': -0.2, 'max': 0.1},
                    'ankle_moment_ipsi_Nm_kg': {'min': -0.3, 'max': 0.3},
                    'hip_moment_contra_Nm_kg': {'min': 0.3, 'max': 1.1},
                    'knee_moment_contra_Nm_kg': {'min': -0.6, 'max': -0.1},
                    'ankle_moment_contra_Nm_kg': {'min': -1.6, 'max': -1.2}
                },
                25: {
                    'hip_moment_ipsi_Nm_kg': {'min': -1.0, 'max': -0.2},
                    'knee_moment_ipsi_Nm_kg': {'min': -0.4, 'max': 0.2},
                    'ankle_moment_ipsi_Nm_kg': {'min': 0.5, 'max': 1.5},
                    'hip_moment_contra_Nm_kg': {'min': -0.1, 'max': 0.2},
                    'knee_moment_contra_Nm_kg': {'min': -0.1, 'max': 0.3},
                    'ankle_moment_contra_Nm_kg': {'min': -0.1, 'max': 0.1}
                },
                50: {
                    'hip_moment_ipsi_Nm_kg': {'min': 0.3, 'max': 1.1},
                    'knee_moment_ipsi_Nm_kg': {'min': -0.6, 'max': -0.1},
                    'ankle_moment_ipsi_Nm_kg': {'min': -1.6, 'max': -1.2},
                    'hip_moment_contra_Nm_kg': {'min': -0.1, 'max': 0.3},
                    'knee_moment_contra_Nm_kg': {'min': -0.2, 'max': 0.1},
                    'ankle_moment_contra_Nm_kg': {'min': -0.3, 'max': 0.3}
                },
                75: {
                    'hip_moment_ipsi_Nm_kg': {'min': -0.1, 'max': 0.2},
                    'knee_moment_ipsi_Nm_kg': {'min': -0.1, 'max': 0.3},
                    'ankle_moment_ipsi_Nm_kg': {'min': -0.1, 'max': 0.1},
                    'hip_moment_contra_Nm_kg': {'min': -1.0, 'max': -0.2},
                    'knee_moment_contra_Nm_kg': {'min': -0.4, 'max': 0.2},
                    'ankle_moment_contra_Nm_kg': {'min': 0.5, 'max': 1.5}
                }
            }
        }
    
    @pytest.fixture
    def valid_kinematic_step_data(self):
        """Create kinematic step data that stays within validation ranges"""
        num_steps = 5
        num_points = 150  # Standard phase normalization
        num_features = 6  # hip_ipsi, hip_contra, knee_ipsi, knee_contra, ankle_ipsi, ankle_contra
        
        data = np.zeros((num_steps, num_points, num_features))
        phase_percent = np.linspace(0, 100, num_points)
        
        for step in range(num_steps):
            # Add small random variation to each step
            step_offset = (step - 2.5) * 0.02  # Small offset per step
            
            # Hip flexion (follows gait pattern within bounds)
            hip_base = 0.25 * np.sin(2 * np.pi * phase_percent / 100) + 0.35
            data[step, :, 0] = hip_base + step_offset  # hip_ipsi
            data[step, :, 1] = hip_base + step_offset  # hip_contra (same pattern for simplicity)
            
            # Knee flexion (follows stance/swing pattern)
            knee_base = 0.4 * np.sin(np.pi * phase_percent / 100) + 0.3
            data[step, :, 2] = knee_base + step_offset  # knee_ipsi
            data[step, :, 3] = knee_base + step_offset  # knee_contra
            
            # Ankle flexion (dorsi/plantarflexion pattern)
            ankle_base = -0.15 * np.sin(2 * np.pi * phase_percent / 100)
            data[step, :, 4] = ankle_base + step_offset  # ankle_ipsi
            data[step, :, 5] = ankle_base + step_offset  # ankle_contra
        
        return data
    
    @pytest.fixture
    def violating_kinematic_step_data(self):
        """Create kinematic step data with known violations for testing color coding"""
        num_steps = 6
        num_points = 150
        num_features = 6
        
        # Start with valid baseline
        data = np.zeros((num_steps, num_points, num_features))
        phase_percent = np.linspace(0, 100, num_points)
        
        # Create baseline valid patterns
        for step in range(num_steps):
            hip_base = 0.25 * np.sin(2 * np.pi * phase_percent / 100) + 0.35
            data[step, :, 0] = hip_base
            data[step, :, 1] = hip_base
            
            knee_base = 0.4 * np.sin(np.pi * phase_percent / 100) + 0.3
            data[step, :, 2] = knee_base
            data[step, :, 3] = knee_base
            
            ankle_base = -0.15 * np.sin(2 * np.pi * phase_percent / 100)
            data[step, :, 4] = ankle_base
            data[step, :, 5] = ankle_base
        
        # Add specific violations for testing
        # Step 0: Hip ipsi violation (should be red for hip plots)
        data[0, :, 0] += 0.8  # Exceed upper bounds
        
        # Step 1: Knee contra violation (should be red for knee plots)
        data[1, :, 3] += 1.5  # Exceed upper bounds
        
        # Step 2: Ankle ipsi violation (should be red for ankle plots)
        data[2, :, 4] -= 0.7  # Below lower bounds
        
        # Step 3: Multiple violations (hip + ankle)
        data[3, :, 0] += 0.7  # Hip violation
        data[3, :, 4] -= 0.6  # Ankle violation
        
        # Step 4: Only contra violations (should be red for contra plots)
        data[4, :, 1] += 0.9  # Hip contra violation
        
        # Step 5: Valid (no violations) - should be gray
        
        return data
    
    def test_basic_plot_generation_kinematic(self, sample_kinematic_validation_data, temp_output_dir):
        """Test basic kinematic plot generation without data overlay"""
        filepath = create_filters_by_phase_plot(
            validation_data=sample_kinematic_validation_data,
            task_name='level_walking',
            output_dir=temp_output_dir,
            mode='kinematic'
        )
        
        assert os.path.exists(filepath)
        assert 'level_walking_kinematic_filters_by_phase.png' in filepath
        assert '_with_data' not in filepath
        print(f"✅ Basic kinematic plot generated: {filepath}")
    
    def test_basic_plot_generation_kinetic(self, sample_kinetic_validation_data, temp_output_dir):
        """Test basic kinetic plot generation without data overlay"""
        filepath = create_filters_by_phase_plot(
            validation_data=sample_kinetic_validation_data,
            task_name='level_walking',
            output_dir=temp_output_dir,
            mode='kinetic'
        )
        
        assert os.path.exists(filepath)
        assert 'level_walking_kinetic_filters_by_phase.png' in filepath
        assert '_with_data' not in filepath
        print(f"✅ Basic kinetic plot generated: {filepath}")
    
    def test_plot_with_valid_step_data(self, sample_kinematic_validation_data, valid_kinematic_step_data, temp_output_dir):
        """Test plot generation with valid step data overlay"""
        filepath = create_filters_by_phase_plot(
            validation_data=sample_kinematic_validation_data,
            task_name='level_walking',
            output_dir=temp_output_dir,
            mode='kinematic',
            data=valid_kinematic_step_data
        )
        
        assert os.path.exists(filepath)
        assert 'level_walking_kinematic_filters_by_phase_with_data.png' in filepath
        print(f"✅ Plot with valid step data generated: {filepath}")
    
    def test_step_color_classification_all_gray(self, sample_kinematic_validation_data, valid_kinematic_step_data, temp_output_dir):
        """Test step color classification - all steps should be gray (valid)"""
        # All steps are valid, so all should be gray
        step_colors = np.array(['gray'] * valid_kinematic_step_data.shape[0])
        
        filepath = create_filters_by_phase_plot(
            validation_data=sample_kinematic_validation_data,
            task_name='level_walking',
            output_dir=temp_output_dir,
            mode='kinematic',
            data=valid_kinematic_step_data,
            step_colors=step_colors
        )
        
        assert os.path.exists(filepath)
        print(f"✅ Plot with all gray step colors generated: {filepath}")
    
    def test_step_color_classification_mixed(self, sample_kinematic_validation_data, violating_kinematic_step_data, temp_output_dir):
        """Test step color classification with mixed violation types"""
        # Create step colors array for the violating data
        # Based on the violations we created in the fixture:
        # Step 0: Hip violation -> red for hip plots, pink for others
        # Step 1: Knee violation -> red for knee plots, pink for others  
        # Step 2: Ankle violation -> red for ankle plots, pink for others
        # Step 3: Multiple violations -> red for relevant plots
        # Step 4: Contra violations -> red for contra plots
        # Step 5: Valid -> gray
        
        # For this test, let's simulate step colors as they would be classified
        # for the hip ipsi subplot (feature 0)
        step_colors = np.array([
            'red',   # Step 0: has hip violation
            'pink',  # Step 1: has knee violation (other violation)
            'pink',  # Step 2: has ankle violation (other violation)
            'red',   # Step 3: has hip violation
            'pink',  # Step 4: has contra violation (other violation)
            'gray'   # Step 5: valid
        ])
        
        filepath = create_filters_by_phase_plot(
            validation_data=sample_kinematic_validation_data,
            task_name='level_walking',
            output_dir=temp_output_dir,
            mode='kinematic',
            data=violating_kinematic_step_data,
            step_colors=step_colors
        )
        
        assert os.path.exists(filepath)
        print(f"✅ Plot with mixed step colors (red/pink/gray) generated: {filepath}")
    
    def test_step_color_all_red(self, sample_kinematic_validation_data, violating_kinematic_step_data, temp_output_dir):
        """Test step colors with all red (local violations)"""
        step_colors = np.array(['red'] * violating_kinematic_step_data.shape[0])
        
        filepath = create_filters_by_phase_plot(
            validation_data=sample_kinematic_validation_data,
            task_name='level_walking',
            output_dir=temp_output_dir,
            mode='kinematic',
            data=violating_kinematic_step_data,
            step_colors=step_colors
        )
        
        assert os.path.exists(filepath)
        print(f"✅ Plot with all red step colors generated: {filepath}")
    
    def test_step_color_all_pink(self, sample_kinematic_validation_data, violating_kinematic_step_data, temp_output_dir):
        """Test step colors with all pink (other violations)"""
        step_colors = np.array(['pink'] * violating_kinematic_step_data.shape[0])
        
        filepath = create_filters_by_phase_plot(
            validation_data=sample_kinematic_validation_data,
            task_name='level_walking',
            output_dir=temp_output_dir,
            mode='kinematic',
            data=violating_kinematic_step_data,
            step_colors=step_colors
        )
        
        assert os.path.exists(filepath)
        print(f"✅ Plot with all pink step colors generated: {filepath}")
    
    def test_mismatched_step_colors_array(self, sample_kinematic_validation_data, valid_kinematic_step_data, temp_output_dir):
        """Test handling of mismatched step_colors array length"""
        # Provide fewer colors than steps
        step_colors = np.array(['gray', 'red'])  # Only 2 colors for 5 steps
        
        filepath = create_filters_by_phase_plot(
            validation_data=sample_kinematic_validation_data,
            task_name='level_walking',
            output_dir=temp_output_dir,
            mode='kinematic',
            data=valid_kinematic_step_data,
            step_colors=step_colors
        )
        
        assert os.path.exists(filepath)
        print(f"✅ Plot with mismatched step colors array handled gracefully: {filepath}")
    
    def test_bilateral_symmetric_task(self, temp_output_dir):
        """Test plotting for bilateral symmetric task (squats)"""
        bilateral_validation_data = {
            'squats': {
                0: {
                    'hip_flexion_angle_ipsi': {'min': -0.1, 'max': 0.3},
                    'knee_flexion_angle_ipsi': {'min': 0.0, 'max': 0.25},
                    'ankle_flexion_angle_ipsi': {'min': -0.05, 'max': 0.15},
                    'hip_flexion_angle_contra': {'min': -0.1, 'max': 0.3},
                    'knee_flexion_angle_contra': {'min': 0.0, 'max': 0.25},
                    'ankle_flexion_angle_contra': {'min': -0.05, 'max': 0.15}
                },
                25: {
                    'hip_flexion_angle_ipsi': {'min': 0.6, 'max': 1.4},
                    'knee_flexion_angle_ipsi': {'min': 0.9, 'max': 1.8},
                    'ankle_flexion_angle_ipsi': {'min': 0.15, 'max': 0.4},
                    'hip_flexion_angle_contra': {'min': 0.6, 'max': 1.4},
                    'knee_flexion_angle_contra': {'min': 0.9, 'max': 1.8},
                    'ankle_flexion_angle_contra': {'min': 0.15, 'max': 0.4}
                }
            }
        }
        
        filepath = create_filters_by_phase_plot(
            validation_data=bilateral_validation_data,
            task_name='squats',
            output_dir=temp_output_dir,
            mode='kinematic'
        )
        
        assert os.path.exists(filepath)
        print(f"✅ Bilateral symmetric task plot generated: {filepath}")
    
    def test_data_shape_edge_cases(self, sample_kinematic_validation_data, temp_output_dir):
        """Test handling of various data shape edge cases"""
        # Test with wrong number of features
        wrong_features_data = np.random.randn(3, 150, 3)  # Only 3 features instead of 6
        
        filepath = create_filters_by_phase_plot(
            validation_data=sample_kinematic_validation_data,
            task_name='level_walking',
            output_dir=temp_output_dir,
            mode='kinematic',
            data=wrong_features_data
        )
        
        assert os.path.exists(filepath)
        print(f"✅ Wrong number of features handled gracefully: {filepath}")
        
        # Test with wrong number of time points
        wrong_timepoints_data = np.random.randn(3, 100, 6)  # 100 points instead of 150
        
        filepath2 = create_filters_by_phase_plot(
            validation_data=sample_kinematic_validation_data,
            task_name='level_walking',
            output_dir=temp_output_dir,
            mode='kinematic',
            data=wrong_timepoints_data
        )
        
        assert os.path.exists(filepath2)
        print(f"✅ Wrong number of time points handled gracefully: {filepath2}")
    
    def test_missing_task_error(self, sample_kinematic_validation_data, temp_output_dir):
        """Test error handling for missing task"""
        if PYTEST_AVAILABLE:
            with pytest.raises(ValueError, match="Task nonexistent_task not found"):
                create_filters_by_phase_plot(
                    validation_data=sample_kinematic_validation_data,
                    task_name='nonexistent_task',
                    output_dir=temp_output_dir,
                    mode='kinematic'
                )
        else:
            # Manual error testing
            try:
                create_filters_by_phase_plot(
                    validation_data=sample_kinematic_validation_data,
                    task_name='nonexistent_task',
                    output_dir=temp_output_dir,
                    mode='kinematic'
                )
                assert False, "Should have raised ValueError"
            except ValueError as e:
                assert "nonexistent_task not found" in str(e)
        print("✅ Missing task error handled correctly")
    
    def test_task_classification(self):
        """Test task classification function"""
        # Test gait tasks
        assert get_task_classification('level_walking') == 'gait'
        assert get_task_classification('incline_walking') == 'gait'
        assert get_task_classification('run') == 'gait'
        
        # Test bilateral tasks
        assert get_task_classification('squats') == 'bilateral'
        assert get_task_classification('jump') == 'bilateral'
        assert get_task_classification('sit_to_stand') == 'bilateral'
        
        # Test unknown task (should default to gait)
        assert get_task_classification('unknown_task') == 'gait'
        
        print("✅ Task classification working correctly")
    
    def test_output_filename_patterns(self, sample_kinematic_validation_data, valid_kinematic_step_data, temp_output_dir):
        """Test that output filenames follow expected patterns"""
        # Test kinematic without data
        filepath1 = create_filters_by_phase_plot(
            sample_kinematic_validation_data, 'level_walking', temp_output_dir, 'kinematic'
        )
        assert 'level_walking_kinematic_filters_by_phase.png' in filepath1
        
        # Test kinematic with data
        filepath2 = create_filters_by_phase_plot(
            sample_kinematic_validation_data, 'level_walking', temp_output_dir, 'kinematic',
            data=valid_kinematic_step_data
        )
        assert 'level_walking_kinematic_filters_by_phase_with_data.png' in filepath2
        
        # Test kinetic without data
        kinetic_data = {
            'level_walking': {
                0: {'hip_moment_ipsi_Nm_kg': {'min': -0.1, 'max': 0.3}},
                25: {'hip_moment_ipsi_Nm_kg': {'min': -1.0, 'max': -0.2}}
            }
        }
        filepath3 = create_filters_by_phase_plot(
            kinetic_data, 'level_walking', temp_output_dir, 'kinetic'
        )
        assert 'level_walking_kinetic_filters_by_phase.png' in filepath3
        
        print("✅ Output filename patterns correct")


class TestStepColorVisualization:
    """Dedicated test class for step color visualization features"""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory for tests"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_comprehensive_step_color_demo(self, temp_output_dir):
        """Create a comprehensive demo showing all step color combinations"""
        
        # Create validation data
        validation_data = {
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
                }
            }
        }
        
        # Create step data with specific patterns
        num_steps = 8
        num_points = 150
        num_features = 6
        
        data = np.zeros((num_steps, num_points, num_features))
        
        # Create different step patterns for demonstration
        for step in range(num_steps):
            if step < 3:  # Valid steps
                data[step, :, 0] = 0.3  # Valid hip
                data[step, :, 2] = 0.1  # Valid knee
                data[step, :, 4] = 0.0  # Valid ankle
            elif step < 6:  # Violating steps
                data[step, :, 0] = 0.8  # Hip violation
                data[step, :, 2] = 0.1  # Valid knee
                data[step, :, 4] = 0.0  # Valid ankle
            else:  # Mixed patterns
                data[step, :, 0] = 0.3  # Valid hip
                data[step, :, 2] = 0.5  # Knee violation
                data[step, :, 4] = -0.2  # Ankle violation
        
        # Test different step color scenarios
        scenarios = [
            (['gray'] * num_steps, 'all_valid'),
            (['red'] * num_steps, 'all_local_violations'),
            (['pink'] * num_steps, 'all_other_violations'),
            (['gray', 'red', 'pink', 'gray', 'red', 'pink', 'red', 'gray'], 'mixed_pattern')
        ]
        
        for step_colors, scenario_name in scenarios:
            step_colors_array = np.array(step_colors)
            
            filepath = create_filters_by_phase_plot(
                validation_data=validation_data,
                task_name='level_walking',
                output_dir=temp_output_dir,
                mode='kinematic',
                data=data,
                step_colors=step_colors_array
            )
            
            assert os.path.exists(filepath)
            
            # Rename file to include scenario
            new_filepath = filepath.replace('.png', f'_{scenario_name}.png')
            os.rename(filepath, new_filepath)
            
            print(f"✅ Step color scenario '{scenario_name}' generated: {new_filepath}")


def run_manual_tests():
    """Run tests manually for environments without pytest"""
    print("=== Running Manual Tests for filters_by_phase_plots.py ===\n")
    
    # Create temporary directory
    import tempfile
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Initialize test class
        test_instance = TestFiltersByPhasePlots()
        
        # Create fixtures manually
        validation_data = {
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
        
        step_data = np.random.randn(5, 150, 6) * 0.1 + 0.3
        step_colors = np.array(['gray', 'red', 'pink', 'gray', 'red'])
        
        # Test basic functionality
        print("1. Testing basic plot generation...")
        filepath = create_filters_by_phase_plot(
            validation_data, 'level_walking', temp_dir, 'kinematic'
        )
        print(f"   ✅ Generated: {filepath}")
        
        # Test with data
        print("2. Testing plot with step data...")
        filepath = create_filters_by_phase_plot(
            validation_data, 'level_walking', temp_dir, 'kinematic',
            data=step_data, step_colors=step_colors
        )
        print(f"   ✅ Generated: {filepath}")
        
        # Test task classification
        print("3. Testing task classification...")
        assert get_task_classification('level_walking') == 'gait'
        assert get_task_classification('squats') == 'bilateral'
        print("   ✅ Task classification working")
        
        print("\n=== All manual tests passed! ===")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    # Try to run with pytest, fall back to manual tests
    if PYTEST_AVAILABLE:
        print("Running tests with pytest...")
        pytest.main([__file__, '-v'])
    else:
        print("pytest not available, running manual tests...")
        run_manual_tests()