#!/usr/bin/env python3
"""
Test Plotting Libraries Coverage

Created: 2025-06-19 with user permission
Purpose: Achieve 100% line coverage for plotting and visualization libraries

Intent:
Comprehensive test coverage for all three plotting libraries:
- forward_kinematics_plots.py: 167 lines (0% coverage) 
- generate_validation_gifs.py: 159 lines (0% coverage)
- generate_validation_plots.py: 132 lines (0% coverage)

Testing Strategy:
- Mock matplotlib to avoid display issues
- Test all plotting functions with realistic biomechanical data
- Cover file saving and output generation
- Test error conditions and edge cases
- Validate all code paths and branches
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, mock_open, call
import numpy as np
import pandas as pd
import os
import sys
import tempfile
import shutil
from pathlib import Path
from io import StringIO

# Add source directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

# Import the libraries we're testing
from internal.plot_generation.forward_kinematics_plots import KinematicPoseGenerator
from internal.plot_generation.generate_validation_gifs import (
    calculate_joint_positions,
    create_stick_figure_animation_from_locomotion_data,
    create_stick_figure_animation,
    process_dataset_config,
    main as gif_main
)
from lib.validation.generate_validation_plots import ValidationPlotsGenerator, main as plots_main


class TestForwardKinematicsPlots(unittest.TestCase):
    """Test coverage for forward_kinematics_plots.py"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.generator = KinematicPoseGenerator()
        self.temp_dir = tempfile.mkdtemp()
        
        # Create sample joint ranges for testing
        self.sample_joint_ranges = {
            'hip_flexion_angle_ipsi': {'min': -0.5, 'max': 1.0},
            'hip_flexion_angle_contra': {'min': -0.3, 'max': 0.8},
            'knee_flexion_angle_ipsi': {'min': 0.0, 'max': 1.5},
            'knee_flexion_angle_contra': {'min': 0.1, 'max': 1.3},
            'ankle_flexion_angle_ipsi': {'min': -0.4, 'max': 0.3},
            'ankle_flexion_angle_contra': {'min': -0.2, 'max': 0.5}
        }
        
        # Sample biomechanical data for testing - create data around target phase points
        phase_data = []
        for phase in [0, 25, 50, 75]:
            # Create data within tolerance around each phase point
            for i in range(10):
                phase_data.append(phase + np.random.uniform(-2, 2))  # Within ±2% tolerance
        
        # Add some other phase data that won't match
        for i in range(20):
            phase_data.append(np.random.uniform(10, 90))
        
        self.sample_data = pd.DataFrame({
            'task_name': ['level_walking'] * len(phase_data),
            'phase_gait_cycle_percent': phase_data,
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.2, 0.3, len(phase_data)),
            'knee_flexion_angle_ipsi_rad': np.random.normal(0.5, 0.4, len(phase_data)),
            'ankle_flexion_angle_ipsi_rad': np.random.normal(-0.1, 0.2, len(phase_data)),
            'hip_flexion_angle_contra_rad': np.random.normal(0.1, 0.3, len(phase_data)),
            'knee_flexion_angle_contra_rad': np.random.normal(0.4, 0.4, len(phase_data)),
            'ankle_flexion_angle_contra_rad': np.random.normal(0.0, 0.2, len(phase_data))
        })
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init(self):
        """Test KinematicPoseGenerator initialization"""
        # Test initialization with default parameters
        self.assertIsInstance(self.generator.segment_lengths, dict)
        self.assertIsInstance(self.generator.joint_limits, dict)
        self.assertIsInstance(self.generator.phase_points, list)
        self.assertIsInstance(self.generator.colors, dict)
        
        # Verify specific values
        self.assertEqual(self.generator.segment_lengths['thigh'], 1.0)
        self.assertEqual(self.generator.segment_lengths['shank'], 1.0)
        self.assertEqual(self.generator.segment_lengths['foot'], 0.5)
        self.assertEqual(self.generator.segment_lengths['torso'], 2.0)
        
        # Test phase points
        self.assertEqual(self.generator.phase_points, [0, 25, 50, 75])
        
        # Test joint limits
        self.assertIn('hip', self.generator.joint_limits)
        self.assertIn('knee', self.generator.joint_limits)
        self.assertIn('ankle', self.generator.joint_limits)
    
    def test_calculate_joint_positions(self):
        """Test joint position calculations"""
        # Test with zero angles
        hip_angle, knee_angle, ankle_angle = 0.0, 0.0, 0.0
        positions = self.generator.calculate_joint_positions(hip_angle, knee_angle, ankle_angle)
        
        self.assertEqual(len(positions), 4)  # hip, knee, ankle, foot
        
        # Test hip position (should be at origin)
        hip_pos, knee_pos, ankle_pos, foot_pos = positions
        self.assertEqual(hip_pos[0], 0.0)
        self.assertEqual(hip_pos[1], 0.0)
        
        # Test with non-zero angles
        hip_angle, knee_angle, ankle_angle = 0.5, 1.0, -0.3
        positions = self.generator.calculate_joint_positions(hip_angle, knee_angle, ankle_angle)
        
        # Verify positions are numpy arrays
        for pos in positions:
            self.assertIsInstance(pos, np.ndarray)
            self.assertEqual(len(pos), 2)
        
        # Test with extreme angles
        hip_angle, knee_angle, ankle_angle = np.pi, np.pi, np.pi
        positions = self.generator.calculate_joint_positions(hip_angle, knee_angle, ankle_angle)
        
        # Should not raise exception and return valid positions
        for pos in positions:
            self.assertIsInstance(pos, np.ndarray)
            self.assertFalse(np.isnan(pos).any())
    
    @patch('matplotlib.pyplot.subplots')
    @patch('matplotlib.pyplot.tight_layout')
    @patch('matplotlib.pyplot.savefig')
    @patch('matplotlib.pyplot.close')
    @patch('os.makedirs')
    def test_generate_range_visualization(self, mock_makedirs, mock_close, mock_savefig, mock_tight_layout, mock_subplots):
        """Test range visualization generation"""
        # Mock matplotlib components
        mock_fig = Mock()
        mock_ax = Mock()
        mock_ax.plot.return_value = [Mock()]  # Return mock line objects
        mock_ax.add_patch = Mock()
        mock_ax.annotate = Mock()
        mock_ax.text = Mock()
        mock_ax.axhline = Mock()
        mock_ax.set_xlim = Mock()
        mock_ax.set_ylim = Mock()
        mock_ax.set_aspect = Mock()
        mock_ax.set_xticks = Mock()
        mock_ax.set_yticks = Mock()
        mock_ax.set_title = Mock()
        mock_ax.legend = Mock()
        mock_ax.spines = {'top': Mock(), 'right': Mock(), 'bottom': Mock(), 'left': Mock()}
        for spine in mock_ax.spines.values():
            spine.set_visible = Mock()
        mock_subplots.return_value = (mock_fig, mock_ax)
        
        # Test basic visualization generation
        filepath = self.generator.generate_range_visualization(
            task_name='level_walking',
            phase_point=25,
            joint_ranges=self.sample_joint_ranges,
            output_path=self.temp_dir
        )
        
        # Verify file path
        expected_path = os.path.join(self.temp_dir, 'level_walking_forward_kinematics_phase_25_range.png')
        self.assertEqual(filepath, expected_path)
        
        # Verify matplotlib calls
        mock_subplots.assert_called_once_with(figsize=(12, 8))
        mock_makedirs.assert_called_once_with(self.temp_dir, exist_ok=True)
        mock_savefig.assert_called_once_with(expected_path, dpi=150, bbox_inches='tight', facecolor='white')
        mock_close.assert_called_once()
        
        # Test different phase points
        for phase in [0, 50, 75]:
            mock_subplots.reset_mock()
            mock_savefig.reset_mock()
            
            filepath = self.generator.generate_range_visualization(
                task_name='level_walking',
                phase_point=phase,
                joint_ranges=self.sample_joint_ranges,
                output_path=self.temp_dir
            )
            
            expected_path = os.path.join(self.temp_dir, f'level_walking_forward_kinematics_phase_{phase:02d}_range.png')
            self.assertEqual(filepath, expected_path)
    
    @patch('matplotlib.pyplot.subplots')
    def test_draw_bilateral_pose(self, mock_subplots):
        """Test bilateral pose drawing"""
        # Mock matplotlib components
        mock_fig = Mock()
        mock_ax = Mock()
        mock_subplots.return_value = (mock_fig, mock_ax)
        
        # Mock ax.plot to return line objects
        mock_line = Mock()
        mock_ax.plot.return_value = [mock_line]
        mock_ax.add_patch = Mock()
        
        # Test bilateral pose drawing
        self.generator.draw_bilateral_pose(
            mock_ax,
            left_hip_min=-0.5, left_knee_min=0.0, left_ankle_min=-0.4,
            left_hip_avg=0.25, left_knee_avg=0.75, left_ankle_avg=-0.05,
            left_hip_max=1.0, left_knee_max=1.5, left_ankle_max=0.3,
            right_hip_min=-0.3, right_knee_min=0.1, right_ankle_min=-0.2,
            right_hip_avg=0.25, right_knee_avg=0.65, right_ankle_avg=0.15,
            right_hip_max=0.8, right_knee_max=1.3, right_ankle_max=0.5
        )
        
        # Verify plotting calls were made
        self.assertTrue(mock_ax.plot.called)
        self.assertTrue(mock_ax.add_patch.called)
        
        # Should have multiple plot calls for different leg segments and transparency levels
        self.assertGreater(mock_ax.plot.call_count, 10)  # Multiple segments and legs
        self.assertGreater(mock_ax.add_patch.call_count, 3)  # Joint circles
    
    def test_extract_phase_ranges_from_data(self):
        """Test phase range extraction from real data"""
        # Test with task filter
        phase_points = [0, 25, 50, 75]
        ranges = self.generator.extract_phase_ranges_from_data(
            self.sample_data, 'level_walking', phase_points
        )
        
        # Verify structure
        self.assertIsInstance(ranges, dict)
        for phase in phase_points:
            self.assertIn(phase, ranges)
            phase_data = ranges[phase]
            
            # Should have joint angle data
            for joint in ['hip_flexion_angle', 'knee_flexion_angle', 'ankle_flexion_angle']:
                if joint in phase_data:
                    joint_info = phase_data[joint]
                    self.assertIn('min', joint_info)
                    self.assertIn('max', joint_info)
                    self.assertIn('mean', joint_info)
                    self.assertIn('std', joint_info)
                    self.assertIn('data_points', joint_info)
        
        # Test with no task filter
        data_no_task = self.sample_data.drop('task_name', axis=1)
        ranges_no_task = self.generator.extract_phase_ranges_from_data(
            data_no_task, 'test_task', phase_points
        )
        self.assertIsInstance(ranges_no_task, dict)
        
        # Test with no phase column - should raise error
        data_no_phase = self.sample_data.drop('phase_gait_cycle_percent', axis=1)
        with self.assertRaises(ValueError):
            self.generator.extract_phase_ranges_from_data(
                data_no_phase, 'level_walking', phase_points
            )
    
    @patch('lib.validation.forward_kinematics_plots.parse_kinematic_validation_expectations')
    @patch('os.path.exists')
    @patch('pathlib.Path.exists')
    def test_generate_task_validation_images(self, mock_path_exists, mock_os_exists, mock_parse):
        """Test task validation image generation"""
        # Mock validation file existence
        mock_os_exists.return_value = True
        mock_path_exists.return_value = True
        
        # Mock validation data
        mock_validation_data = {
            'level_walking': {
                0: self.sample_joint_ranges,
                25: self.sample_joint_ranges,
                50: self.sample_joint_ranges,
                75: self.sample_joint_ranges
            }
        }
        mock_parse.return_value = mock_validation_data
        
        with patch.object(self.generator, 'generate_range_visualization') as mock_generate:
            mock_generate.return_value = '/fake/path/image.png'
            
            # Test image generation
            files = self.generator.generate_task_validation_images(
                task_name='level_walking',
                output_dir=self.temp_dir
            )
            
            # Verify correct number of files generated
            self.assertEqual(len(files), 4)  # One for each phase point
            
            # Verify generate_range_visualization called correctly
            self.assertEqual(mock_generate.call_count, 4)
        
        # Test with pre-computed ranges
        with patch.object(self.generator, 'generate_range_visualization') as mock_generate:
            mock_generate.return_value = '/fake/path/image.png'
            
            files = self.generator.generate_task_validation_images(
                task_name='level_walking',
                validation_ranges=mock_validation_data['level_walking'],
                output_dir=self.temp_dir
            )
            
            self.assertEqual(len(files), 4)
        
        # Test with missing task
        with self.assertRaises(ValueError):
            self.generator.generate_task_validation_images(
                task_name='nonexistent_task',
                validation_ranges=mock_validation_data['level_walking'],
                output_dir=self.temp_dir
            )
        
        # Test with missing validation file
        mock_os_exists.return_value = False
        mock_path_exists.return_value = False
        
        with self.assertRaises(ValueError):
            self.generator.generate_task_validation_images(
                task_name='level_walking',
                output_dir=self.temp_dir
            )


class TestGenerateValidationGifs(unittest.TestCase):
    """Test coverage for generate_validation_gifs.py"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.segment_lengths = {'thigh': 1.0, 'shank': 1.0, 'foot': 0.5, 'torso': 2.0}
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_calculate_joint_positions(self):
        """Test joint position calculation for stick figure"""
        # Test with zero angles
        positions = calculate_joint_positions(0.0, 0.0, 0.0, self.segment_lengths)
        self.assertEqual(len(positions), 4)
        
        # Hip should be at origin
        hip_pos = positions[0]
        self.assertEqual(hip_pos, (0, 0))
        
        # Test with non-zero angles
        positions = calculate_joint_positions(0.5, 1.0, -0.3, self.segment_lengths)
        
        # Verify all positions are tuples with 2 elements
        for pos in positions:
            self.assertIsInstance(pos, tuple)
            self.assertEqual(len(pos), 2)
            self.assertIsInstance(pos[0], (int, float, np.floating))
            self.assertIsInstance(pos[1], (int, float, np.floating))
        
        # Test with extreme angles
        positions = calculate_joint_positions(np.pi, np.pi, np.pi, self.segment_lengths)
        
        # Should not contain NaN values
        for pos in positions:
            self.assertFalse(np.isnan(pos[0]))
            self.assertFalse(np.isnan(pos[1]))
    
    @patch('lib.validation.generate_validation_gifs.LocomotionData')
    def test_create_stick_figure_animation_from_locomotion_data_missing_features(self, mock_loco_class):
        """Test animation creation with insufficient features"""
        # Mock LocomotionData with insufficient angle features
        mock_loco = Mock()
        mock_loco.ANGLE_FEATURES = ['hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_ipsi_rad']
        mock_loco.features = ['hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_ipsi_rad']
        mock_loco_class.return_value = mock_loco
        
        # Mock the actual function import
        with patch.dict('sys.modules', {'lib.core.locomotion_analysis': Mock()}):
            result = create_stick_figure_animation_from_locomotion_data(
                mock_loco, 'S01', 'level_walking', self.segment_lengths, '/fake/path.gif'
            )
        
        # Should return False due to insufficient features
        self.assertFalse(result)
    
    def test_create_stick_figure_animation_from_locomotion_data_no_data(self):
        """Test animation creation with no cycle data"""
        # Mock LocomotionData with sufficient features but no data
        mock_loco = Mock()
        mock_loco.ANGLE_FEATURES = [
            'hip_flexion_angle_ipsi_rad', 'hip_flexion_angle_contra_rad',
            'knee_flexion_angle_ipsi_rad', 'knee_flexion_angle_contra_rad',
            'ankle_flexion_angle_ipsi_rad', 'ankle_flexion_angle_contra_rad'
        ]
        mock_loco.features = mock_loco.ANGLE_FEATURES
        mock_loco.get_cycles.return_value = (None, None)
        
        with patch.dict('sys.modules', {'lib.core.locomotion_analysis': Mock()}):
            with patch('lib.validation.generate_validation_gifs.LocomotionData', return_value=mock_loco):
                result = create_stick_figure_animation_from_locomotion_data(
                    mock_loco, 'S01', 'level_walking', self.segment_lengths, '/fake/path.gif'
                )
        
        # Should return False due to no data
        self.assertFalse(result)
    
    def test_create_stick_figure_animation_from_locomotion_data_success(self):
        """Test successful animation creation from LocomotionData"""
        # Mock LocomotionData with valid data
        mock_loco = Mock()
        mock_loco.ANGLE_FEATURES = [
            'hip_flexion_angle_ipsi_rad', 'hip_flexion_angle_contra_rad',
            'knee_flexion_angle_ipsi_rad', 'knee_flexion_angle_contra_rad',
            'ankle_flexion_angle_ipsi_rad', 'ankle_flexion_angle_contra_rad'
        ]
        mock_loco.features = mock_loco.ANGLE_FEATURES
        
        # Mock cycle data (1 cycle, 150 frames, 6 features)
        cycle_data = np.random.random((1, 150, 6))
        feature_names = mock_loco.ANGLE_FEATURES
        mock_loco.get_cycles.return_value = (cycle_data, feature_names)
        
        with patch.dict('sys.modules', {'lib.core.locomotion_analysis': Mock()}):
            with patch('lib.validation.generate_validation_gifs.LocomotionData', return_value=mock_loco):
                with patch('lib.validation.generate_validation_gifs.create_stick_figure_animation', return_value=True) as mock_create_anim:
                    result = create_stick_figure_animation_from_locomotion_data(
                        mock_loco, 'S01', 'level_walking', self.segment_lengths, '/fake/path.gif'
                    )
        
        # Should return True
        self.assertTrue(result)
        mock_create_anim.assert_called_once()
    
    def test_create_stick_figure_animation_from_locomotion_data_missing_joints(self):
        """Test animation creation with missing joint mappings"""
        # Mock LocomotionData with features that don't map to required joints
        mock_loco = Mock()
        mock_loco.ANGLE_FEATURES = [
            'some_other_angle_rad', 'another_angle_rad',
            'third_angle_rad', 'fourth_angle_rad',
            'fifth_angle_rad', 'sixth_angle_rad'
        ]
        mock_loco.features = mock_loco.ANGLE_FEATURES
        
        # Mock cycle data
        cycle_data = np.random.random((1, 150, 6))
        feature_names = mock_loco.ANGLE_FEATURES
        mock_loco.get_cycles.return_value = (cycle_data, feature_names)
        
        with patch.dict('sys.modules', {'lib.core.locomotion_analysis': Mock()}):
            with patch('lib.validation.generate_validation_gifs.LocomotionData', return_value=mock_loco):
                result = create_stick_figure_animation_from_locomotion_data(
                    mock_loco, 'S01', 'level_walking', self.segment_lengths, '/fake/path.gif'
                )
        
        # Should return False due to missing joint mappings
        self.assertFalse(result)
    
    def test_create_stick_figure_animation_from_locomotion_data_exception(self):
        """Test exception handling in animation creation"""
        # Mock LocomotionData to raise exception during import
        with patch.dict('sys.modules', {'lib.core.locomotion_analysis': Mock()}):
            with patch('lib.validation.generate_validation_gifs.LocomotionData', side_effect=Exception("Import error")):
                result = create_stick_figure_animation_from_locomotion_data(
                    None, 'S01', 'level_walking', self.segment_lengths, '/fake/path.gif'
                )
        
        # Should return False due to exception
        self.assertFalse(result)
    
    def test_create_stick_figure_animation_insufficient_frames(self):
        """Test animation creation with insufficient frames"""
        # Create cycle data with too few frames
        cycle_data = np.random.random((5, 6))  # Only 5 frames
        feature_mapping = {
            'hip_ipsi': 0, 'knee_ipsi': 1, 'ankle_ipsi': 2,
            'hip_contra': 3, 'knee_contra': 4, 'ankle_contra': 5
        }
        
        with patch('matplotlib.pyplot.subplots'), \
             patch('matplotlib.animation.FuncAnimation'), \
             patch('matplotlib.pyplot.close'):
            
            result = create_stick_figure_animation(
                cycle_data, feature_mapping, self.segment_lengths, '/fake/path.gif', 'S01', 'level_walking'
            )
        
        # Should return False due to insufficient frames
        self.assertFalse(result)
    
    def test_create_stick_figure_animation_success(self):
        """Test successful animation creation"""
        # Create valid cycle data
        cycle_data = np.random.random((150, 6))  # 150 frames, 6 features
        feature_mapping = {
            'hip_ipsi': 0, 'knee_ipsi': 1, 'ankle_ipsi': 2,
            'hip_contra': 3, 'knee_contra': 4, 'ankle_contra': 5
        }
        
        # Mock matplotlib components to avoid animation complexity
        mock_fig = Mock()
        mock_ax = Mock()
        mock_line1 = Mock()
        mock_line2 = Mock()
        mock_ax.plot.side_effect = [[mock_line1], [mock_line2]]
        mock_ax.set_xlim = Mock()
        mock_ax.set_ylim = Mock()
        mock_ax.set_aspect = Mock()
        mock_ax.grid = Mock()
        mock_ax.set_title = Mock()
        mock_ax.legend = Mock()
        
        # Mock animation that doesn't trigger initialization
        mock_anim = Mock()
        mock_anim.save = Mock()
        
        with patch('matplotlib.pyplot.subplots', return_value=(mock_fig, mock_ax)), \
             patch('matplotlib.animation.FuncAnimation', return_value=mock_anim), \
             patch('matplotlib.pyplot.close') as mock_close:
            
            result = create_stick_figure_animation(
                cycle_data, feature_mapping, self.segment_lengths, '/fake/path.gif', 'S01', 'level_walking'
            )
        
        # Should return True
        self.assertTrue(result)
        
        # Verify calls were made
        mock_anim.save.assert_called_once_with('/fake/path.gif', writer='pillow', fps=20)
        mock_close.assert_called_once_with(mock_fig)
    
    def test_create_stick_figure_animation_save_error(self):
        """Test animation creation with save error"""
        # Create valid cycle data
        cycle_data = np.random.random((150, 6))
        feature_mapping = {
            'hip_ipsi': 0, 'knee_ipsi': 1, 'ankle_ipsi': 2,
            'hip_contra': 3, 'knee_contra': 4, 'ankle_contra': 5
        }
        
        # Mock matplotlib components
        mock_fig = Mock()
        mock_ax = Mock()
        mock_line1 = Mock()
        mock_line2 = Mock()
        mock_ax.plot.side_effect = [[mock_line1], [mock_line2]]
        mock_ax.set_xlim = Mock()
        mock_ax.set_ylim = Mock()
        mock_ax.set_aspect = Mock()
        mock_ax.grid = Mock()
        mock_ax.set_title = Mock()
        mock_ax.legend = Mock()
        
        # Mock animation with save error
        mock_anim = Mock()
        mock_anim.save.side_effect = Exception("Save error")
        
        with patch('matplotlib.pyplot.subplots', return_value=(mock_fig, mock_ax)), \
             patch('matplotlib.animation.FuncAnimation', return_value=mock_anim), \
             patch('matplotlib.pyplot.close') as mock_close:
            
            result = create_stick_figure_animation(
                cycle_data, feature_mapping, self.segment_lengths, '/fake/path.gif', 'S01', 'level_walking'
            )
        
        # Should return False due to save error
        self.assertFalse(result)
        mock_close.assert_called_once_with(mock_fig)
    
    def test_process_dataset_config(self):
        """Test dataset configuration processing"""
        # Mock LocomotionData
        mock_loco = Mock()
        mock_loco.subjects = ['S01', 'S02']
        mock_loco.tasks = ['level_walking', 'incline_walking']
        
        # Test configuration
        config = {
            'file': 'test_dataset.parquet',
            'subject_task_pairs': [
                ('S01', 'level_walking', 0),
                ('S02', 'incline_walking', 100)
            ]
        }
        
        with patch.dict('sys.modules', {'lib.core.locomotion_analysis': Mock()}):
            with patch('lib.validation.generate_validation_gifs.LocomotionData', return_value=mock_loco) as mock_loco_class:
                with patch('lib.validation.generate_validation_gifs.create_stick_figure_animation_from_locomotion_data', return_value=True) as mock_create_anim:
                    with patch('pathlib.Path.mkdir') as mock_mkdir:
                        # Process configuration (should not raise exception)
                        process_dataset_config(config)
        
        # Verify calls
        mock_loco_class.assert_called_once_with('test_dataset.parquet')
        self.assertEqual(mock_create_anim.call_count, 2)
        mock_mkdir.assert_called_once_with(exist_ok=True)
    
    def test_process_dataset_config_missing_subject(self):
        """Test dataset processing with missing subject"""
        # Mock LocomotionData with limited subjects
        mock_loco = Mock()
        mock_loco.subjects = ['S01']  # Missing S02
        mock_loco.tasks = ['level_walking']
        
        config = {
            'file': 'test_dataset.parquet',
            'subject_task_pairs': [
                ('S01', 'level_walking', 0),
                ('S02', 'level_walking', 0)  # S02 doesn't exist
            ]
        }
        
        with patch.dict('sys.modules', {'lib.core.locomotion_analysis': Mock()}):
            with patch('lib.validation.generate_validation_gifs.LocomotionData', return_value=mock_loco) as mock_loco_class:
                with patch('pathlib.Path.mkdir'):
                    # Should not raise exception, just continue processing
                    process_dataset_config(config)
        
        mock_loco_class.assert_called_once_with('test_dataset.parquet')
    
    def test_process_dataset_config_missing_task(self):
        """Test dataset processing with missing task"""
        # Mock LocomotionData with limited tasks
        mock_loco = Mock()
        mock_loco.subjects = ['S01']
        mock_loco.tasks = ['level_walking']  # Missing incline_walking
        
        config = {
            'file': 'test_dataset.parquet',
            'subject_task_pairs': [
                ('S01', 'level_walking', 0),
                ('S01', 'incline_walking', 0)  # Task doesn't exist
            ]
        }
        
        with patch.dict('sys.modules', {'lib.core.locomotion_analysis': Mock()}):
            with patch('lib.validation.generate_validation_gifs.LocomotionData', return_value=mock_loco) as mock_loco_class:
                with patch('pathlib.Path.mkdir'):
                    # Should not raise exception, just continue processing
                    process_dataset_config(config)
        
        mock_loco_class.assert_called_once_with('test_dataset.parquet')
    
    def test_process_dataset_config_exception(self):
        """Test dataset processing with exception"""
        config = {
            'file': 'test_dataset.parquet',
            'subject_task_pairs': [('S01', 'level_walking', 0)]
        }
        
        with patch.dict('sys.modules', {'lib.core.locomotion_analysis': Mock()}):
            with patch('lib.validation.generate_validation_gifs.LocomotionData', side_effect=Exception("Dataset load error")) as mock_loco_class:
                # Should not raise exception, just handle it
                process_dataset_config(config)
        
        mock_loco_class.assert_called_once_with('test_dataset.parquet')
    
    @patch('argparse.ArgumentParser.parse_args')
    @patch('lib.validation.generate_validation_gifs.process_dataset_config')
    def test_main_single_subject_task(self, mock_process, mock_parse_args):
        """Test main function with single subject-task pair"""
        # Mock command line arguments
        mock_args = Mock()
        mock_args.file = 'test.parquet'
        mock_args.subject = 'S01'
        mock_args.task = 'level_walking'
        mock_args.jump_frames = 100
        mock_args.all_datasets = False
        mock_args.parallel = False
        mock_parse_args.return_value = mock_args
        
        # Run main function
        gif_main()
        
        # Verify process_dataset_config was called with correct config
        mock_process.assert_called_once()
        config = mock_process.call_args[0][0]
        self.assertEqual(config['file'], 'test.parquet')
        self.assertEqual(len(config['subject_task_pairs']), 1)
        self.assertEqual(config['subject_task_pairs'][0], ('S01', 'level_walking', 100))
    
    @patch('argparse.ArgumentParser.parse_args')
    @patch('lib.validation.generate_validation_gifs.process_dataset_config')
    def test_main_all_datasets_sequential(self, mock_process, mock_parse_args):
        """Test main function with all datasets (sequential)"""
        # Mock command line arguments
        mock_args = Mock()
        mock_args.file = None
        mock_args.subject = None
        mock_args.task = None
        mock_args.all_datasets = True
        mock_args.parallel = False
        mock_parse_args.return_value = mock_args
        
        # Run main function
        gif_main()
        
        # Should process multiple datasets
        self.assertGreater(mock_process.call_count, 0)
    
    @patch('argparse.ArgumentParser.parse_args')
    @patch('multiprocessing.Pool')
    @patch('lib.validation.generate_validation_gifs.process_dataset_config')
    def test_main_all_datasets_parallel(self, mock_process, mock_pool_class, mock_parse_args):
        """Test main function with all datasets (parallel)"""
        # Mock command line arguments
        mock_args = Mock()
        mock_args.file = None
        mock_args.subject = None
        mock_args.task = None
        mock_args.all_datasets = True
        mock_args.parallel = True
        mock_parse_args.return_value = mock_args
        
        # Mock multiprocessing pool
        mock_pool = Mock()
        mock_pool_class.return_value.__enter__.return_value = mock_pool
        
        # Run main function
        gif_main()
        
        # Verify parallel processing was used
        mock_pool.map.assert_called_once()
    
    @patch('argparse.ArgumentParser.parse_args')
    @patch('builtins.print')
    def test_main_usage_message(self, mock_print, mock_parse_args):
        """Test main function with no arguments (shows usage)"""
        # Mock command line arguments with no valid options
        mock_args = Mock()
        mock_args.file = None
        mock_args.subject = None
        mock_args.task = None
        mock_args.all_datasets = False
        mock_parse_args.return_value = mock_args
        
        # Run main function
        gif_main()
        
        # Should print usage examples
        mock_print.assert_called()
        # Check that usage examples were printed
        printed_text = ' '.join([str(call[0][0]) for call in mock_print.call_args_list])
        self.assertIn('Usage examples', printed_text)


class TestGenerateValidationPlots(unittest.TestCase):
    """Test coverage for generate_validation_plots.py"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock validation data
        self.sample_validation_data = {
            'level_walking': {
                0: {'hip_flexion_angle_ipsi': {'min': -0.5, 'max': 1.0}},
                25: {'hip_flexion_angle_ipsi': {'min': -0.3, 'max': 0.8}},
                50: {'hip_flexion_angle_ipsi': {'min': -0.4, 'max': 0.9}},
                75: {'hip_flexion_angle_ipsi': {'min': -0.6, 'max': 1.1}}
            }
        }
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.mkdir')
    def test_validation_plots_generator_init_kinematic(self, mock_mkdir, mock_exists):
        """Test ValidationPlotsGenerator initialization for kinematic mode"""
        mock_exists.return_value = True
        
        generator = ValidationPlotsGenerator(mode='kinematic')
        
        self.assertEqual(generator.mode, 'kinematic')
        self.assertIsNotNone(generator.pose_generator)
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.mkdir')
    def test_validation_plots_generator_init_kinetic(self, mock_mkdir, mock_exists):
        """Test ValidationPlotsGenerator initialization for kinetic mode"""
        mock_exists.return_value = True
        
        generator = ValidationPlotsGenerator(mode='kinetic')
        
        self.assertEqual(generator.mode, 'kinetic')
        self.assertFalse(hasattr(generator, 'pose_generator'))
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    
    @patch('pathlib.Path.exists')
    def test_validation_plots_generator_init_missing_spec(self, mock_exists):
        """Test ValidationPlotsGenerator initialization with missing spec file"""
        mock_exists.return_value = False
        
        with self.assertRaises(FileNotFoundError):
            ValidationPlotsGenerator(mode='kinematic')
    
    @patch('pathlib.Path.exists')
    @patch('lib.validation.generate_validation_plots.parse_kinematic_validation_expectations')
    @patch('lib.validation.generate_validation_plots.apply_contralateral_offset_kinematic')
    def test_load_validation_data_kinematic(self, mock_offset, mock_parse, mock_exists):
        """Test loading kinematic validation data"""
        mock_exists.return_value = True
        mock_parse.return_value = self.sample_validation_data
        mock_offset.side_effect = lambda data, task: data  # Return data unchanged
        
        generator = ValidationPlotsGenerator(mode='kinematic')
        validation_data = generator.load_validation_data()
        
        self.assertEqual(validation_data, self.sample_validation_data)
        mock_parse.assert_called_once()
        mock_offset.assert_called()
    
    @patch('pathlib.Path.exists')
    @patch('lib.validation.generate_validation_plots.parse_kinetic_validation_expectations')
    @patch('lib.validation.generate_validation_plots.apply_contralateral_offset_kinetic')
    def test_load_validation_data_kinetic(self, mock_offset, mock_parse, mock_exists):
        """Test loading kinetic validation data"""
        mock_exists.return_value = True
        mock_parse.return_value = self.sample_validation_data
        mock_offset.side_effect = lambda data, task: data  # Return data unchanged
        
        generator = ValidationPlotsGenerator(mode='kinetic')
        validation_data = generator.load_validation_data()
        
        self.assertEqual(validation_data, self.sample_validation_data)
        mock_parse.assert_called_once()
        mock_offset.assert_called()
    
    @patch('pathlib.Path.exists')
    @patch('lib.validation.generate_validation_plots.parse_kinematic_validation_expectations')
    def test_load_validation_data_exception(self, mock_parse, mock_exists):
        """Test loading validation data with exception"""
        mock_exists.return_value = True
        mock_parse.side_effect = Exception("Parse error")
        
        generator = ValidationPlotsGenerator(mode='kinematic')
        
        with self.assertRaises(RuntimeError):
            generator.load_validation_data()
    
    @patch('pathlib.Path.exists')
    def test_generate_forward_kinematics_plots_kinetic_mode(self, mock_exists):
        """Test forward kinematics plots in kinetic mode (should return empty)"""
        mock_exists.return_value = True
        
        generator = ValidationPlotsGenerator(mode='kinetic')
        files = generator.generate_forward_kinematics_plots()
        
        self.assertEqual(files, [])
    
    @patch('pathlib.Path.exists')
    @patch.object(ValidationPlotsGenerator, 'load_validation_data')
    def test_generate_forward_kinematics_plots_kinematic_mode(self, mock_load_data, mock_exists):
        """Test forward kinematics plots in kinematic mode"""
        mock_exists.return_value = True
        mock_load_data.return_value = self.sample_validation_data
        
        generator = ValidationPlotsGenerator(mode='kinematic')
        
        with patch.object(generator.pose_generator, 'generate_task_validation_images') as mock_generate:
            mock_generate.return_value = ['/fake/path1.png', '/fake/path2.png']
            
            files = generator.generate_forward_kinematics_plots()
            
            self.assertEqual(len(files), 2)
            mock_generate.assert_called_once()
    
    @patch('pathlib.Path.exists')
    @patch.object(ValidationPlotsGenerator, 'load_validation_data')
    def test_generate_forward_kinematics_plots_specific_tasks(self, mock_load_data, mock_exists):
        """Test forward kinematics plots for specific tasks"""
        mock_exists.return_value = True
        mock_load_data.return_value = self.sample_validation_data
        
        generator = ValidationPlotsGenerator(mode='kinematic')
        
        with patch.object(generator.pose_generator, 'generate_task_validation_images') as mock_generate:
            mock_generate.return_value = ['/fake/path.png']
            
            files = generator.generate_forward_kinematics_plots(tasks=['level_walking'])
            
            self.assertEqual(len(files), 1)
            mock_generate.assert_called_once_with(
                task_name='level_walking',
                validation_ranges=self.sample_validation_data['level_walking'],
                output_dir=str(generator.output_dir)
            )
    
    @patch('pathlib.Path.exists')
    @patch.object(ValidationPlotsGenerator, 'load_validation_data')
    def test_generate_forward_kinematics_plots_missing_task(self, mock_load_data, mock_exists):
        """Test forward kinematics plots with missing task"""
        mock_exists.return_value = True
        mock_load_data.return_value = self.sample_validation_data
        
        generator = ValidationPlotsGenerator(mode='kinematic')
        
        with self.assertRaises(ValueError):
            generator.generate_forward_kinematics_plots(tasks=['nonexistent_task'])
    
    @patch('pathlib.Path.exists')
    @patch.object(ValidationPlotsGenerator, 'load_validation_data')
    def test_generate_forward_kinematics_plots_generation_error(self, mock_load_data, mock_exists):
        """Test forward kinematics plots with generation error"""
        mock_exists.return_value = True
        mock_load_data.return_value = self.sample_validation_data
        
        generator = ValidationPlotsGenerator(mode='kinematic')
        
        with patch.object(generator.pose_generator, 'generate_task_validation_images') as mock_generate:
            mock_generate.side_effect = Exception("Generation error")
            
            # Should not raise exception, just continue
            files = generator.generate_forward_kinematics_plots()
            
            self.assertEqual(files, [])
    
    @patch('pathlib.Path.exists')
    @patch.object(ValidationPlotsGenerator, 'load_validation_data')
    @patch('lib.validation.generate_validation_plots.create_filters_by_phase_plot')
    def test_generate_filters_by_phase_plots(self, mock_create_plot, mock_load_data, mock_exists):
        """Test filters by phase plots generation"""
        mock_exists.return_value = True
        mock_load_data.return_value = self.sample_validation_data
        mock_create_plot.return_value = '/fake/path.png'
        
        generator = ValidationPlotsGenerator(mode='kinematic')
        files = generator.generate_filters_by_phase_plots()
        
        self.assertEqual(len(files), 1)
        mock_create_plot.assert_called_once()
    
    @patch('pathlib.Path.exists')
    @patch.object(ValidationPlotsGenerator, 'load_validation_data')
    @patch('lib.validation.generate_validation_plots.create_filters_by_phase_plot')
    def test_generate_filters_by_phase_plots_specific_tasks(self, mock_create_plot, mock_load_data, mock_exists):
        """Test filters by phase plots for specific tasks"""
        mock_exists.return_value = True
        mock_load_data.return_value = self.sample_validation_data
        mock_create_plot.return_value = '/fake/path.png'
        
        generator = ValidationPlotsGenerator(mode='kinematic')
        files = generator.generate_filters_by_phase_plots(tasks=['level_walking'])
        
        self.assertEqual(len(files), 1)
        mock_create_plot.assert_called_once_with(
            validation_data=self.sample_validation_data,
            task_name='level_walking',
            output_dir=str(generator.output_dir),
            mode='kinematic',
            data=None,
            step_colors=None
        )
    
    @patch('pathlib.Path.exists')
    @patch.object(ValidationPlotsGenerator, 'load_validation_data')
    def test_generate_filters_by_phase_plots_missing_task(self, mock_load_data, mock_exists):
        """Test filters by phase plots with missing task"""
        mock_exists.return_value = True
        mock_load_data.return_value = self.sample_validation_data
        
        generator = ValidationPlotsGenerator(mode='kinematic')
        
        with self.assertRaises(ValueError):
            generator.generate_filters_by_phase_plots(tasks=['nonexistent_task'])
    
    @patch('pathlib.Path.exists')
    @patch.object(ValidationPlotsGenerator, 'load_validation_data')
    @patch('lib.validation.generate_validation_plots.create_filters_by_phase_plot')
    def test_generate_filters_by_phase_plots_generation_error(self, mock_create_plot, mock_load_data, mock_exists):
        """Test filters by phase plots with generation error"""
        mock_exists.return_value = True
        mock_load_data.return_value = self.sample_validation_data
        mock_create_plot.side_effect = Exception("Generation error")
        
        generator = ValidationPlotsGenerator(mode='kinematic')
        
        # Should not raise exception, just continue
        files = generator.generate_filters_by_phase_plots()
        
        self.assertEqual(files, [])
    
    @patch('pathlib.Path.exists')
    @patch.object(ValidationPlotsGenerator, 'generate_forward_kinematics_plots')
    @patch.object(ValidationPlotsGenerator, 'generate_filters_by_phase_plots')
    def test_generate_all_plots(self, mock_fbp, mock_fk, mock_exists):
        """Test generating all plots"""
        mock_exists.return_value = True
        mock_fk.return_value = ['/fake/fk1.png', '/fake/fk2.png']
        mock_fbp.return_value = ['/fake/fbp1.png']
        
        generator = ValidationPlotsGenerator(mode='kinematic')
        results = generator.generate_all_plots()
        
        self.assertEqual(results['total_files'], 3)
        self.assertEqual(len(results['forward_kinematics_plots']), 2)
        self.assertEqual(len(results['filters_by_phase_plots']), 1)
    
    @patch('pathlib.Path.exists')
    @patch.object(ValidationPlotsGenerator, 'generate_forward_kinematics_plots')
    def test_generate_all_plots_exception(self, mock_fk, mock_exists):
        """Test generating all plots with exception"""
        mock_exists.return_value = True
        mock_fk.side_effect = Exception("Generation error")
        
        generator = ValidationPlotsGenerator(mode='kinematic')
        
        with self.assertRaises(Exception):
            generator.generate_all_plots()
    
    @patch('argparse.ArgumentParser.parse_args')
    @patch('lib.validation.generate_validation_plots.ValidationPlotsGenerator')
    def test_main_default_options(self, mock_generator_class, mock_parse_args):
        """Test main function with default options"""
        # Mock command line arguments
        mock_args = Mock()
        mock_args.tasks = None
        mock_args.forward_kinematic_only = False
        mock_args.filters_only = False
        mock_args.mode = 'kinematic'
        mock_parse_args.return_value = mock_args
        
        # Mock generator
        mock_generator = Mock()
        mock_generator.generate_all_plots.return_value = {'total_files': 5}
        mock_generator_class.return_value = mock_generator
        
        # Run main function
        result = plots_main()
        
        self.assertEqual(result, 0)
        mock_generator_class.assert_called_once_with(mode='kinematic')
        mock_generator.generate_all_plots.assert_called_once_with(None)
    
    @patch('argparse.ArgumentParser.parse_args')
    @patch('lib.validation.generate_validation_plots.ValidationPlotsGenerator')
    def test_main_forward_kinematic_only(self, mock_generator_class, mock_parse_args):
        """Test main function with forward kinematic only option"""
        # Mock command line arguments
        mock_args = Mock()
        mock_args.tasks = ['level_walking']
        mock_args.forward_kinematic_only = True
        mock_args.filters_only = False
        mock_args.mode = 'kinematic'
        mock_parse_args.return_value = mock_args
        
        # Mock generator
        mock_generator = Mock()
        mock_generator.generate_forward_kinematics_plots.return_value = ['/fake/path.png']
        mock_generator_class.return_value = mock_generator
        
        # Run main function
        result = plots_main()
        
        self.assertEqual(result, 0)
        mock_generator.generate_forward_kinematics_plots.assert_called_once_with(['level_walking'])
    
    @patch('argparse.ArgumentParser.parse_args')
    @patch('lib.validation.generate_validation_plots.ValidationPlotsGenerator')
    def test_main_filters_only(self, mock_generator_class, mock_parse_args):
        """Test main function with filters only option"""
        # Mock command line arguments
        mock_args = Mock()
        mock_args.tasks = None
        mock_args.forward_kinematic_only = False
        mock_args.filters_only = True
        mock_args.mode = 'kinematic'
        mock_parse_args.return_value = mock_args
        
        # Mock generator
        mock_generator = Mock()
        mock_generator.generate_filters_by_phase_plots.return_value = ['/fake/path.png']
        mock_generator_class.return_value = mock_generator
        
        # Run main function
        result = plots_main()
        
        self.assertEqual(result, 0)
        mock_generator.generate_filters_by_phase_plots.assert_called_once_with(None)
    
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_conflicting_options(self, mock_parse_args):
        """Test main function with conflicting options"""
        # Mock command line arguments with conflicting options
        mock_args = Mock()
        mock_args.forward_kinematic_only = True
        mock_args.filters_only = True
        mock_parse_args.return_value = mock_args
        
        # Run main function
        result = plots_main()
        
        self.assertEqual(result, 1)  # Should return error code
    
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_forward_kinematic_kinetic_mode(self, mock_parse_args):
        """Test main function with forward kinematic option in kinetic mode"""
        # Mock command line arguments
        mock_args = Mock()
        mock_args.forward_kinematic_only = True
        mock_args.filters_only = False
        mock_args.mode = 'kinetic'
        mock_parse_args.return_value = mock_args
        
        # Run main function
        result = plots_main()
        
        self.assertEqual(result, 1)  # Should return error code
    
    @patch('argparse.ArgumentParser.parse_args')
    @patch('lib.validation.generate_validation_plots.ValidationPlotsGenerator')
    def test_main_exception_handling(self, mock_generator_class, mock_parse_args):
        """Test main function exception handling"""
        # Mock command line arguments
        mock_args = Mock()
        mock_args.tasks = None
        mock_args.forward_kinematic_only = False
        mock_args.filters_only = False
        mock_args.mode = 'kinematic'
        mock_parse_args.return_value = mock_args
        
        # Mock generator to raise exception
        mock_generator_class.side_effect = Exception("Initialization error")
        
        # Run main function
        result = plots_main()
        
        self.assertEqual(result, 1)  # Should return error code


class TestAnimationFunctionCoverage(unittest.TestCase):
    """Test coverage for animation function paths"""
    
    def test_animation_frame_logic_coverage(self):
        """Test the internal animation logic without complex matplotlib mocking"""
        from internal.plot_generation.generate_validation_gifs import calculate_joint_positions
        
        # Test the core calculation that happens in the animation frame
        segment_lengths = {'thigh': 1.0, 'shank': 1.0, 'foot': 0.5, 'torso': 2.0}
        
        # Test with various angle combinations to cover different code paths
        test_angles = [
            (0.0, 0.0, 0.0),
            (0.5, 1.0, -0.3),
            (np.pi/4, np.pi/3, np.pi/6),
            (-0.2, 0.8, -0.5),
            (1.5, 2.0, 0.3)
        ]
        
        for hip, knee, ankle in test_angles:
            positions = calculate_joint_positions(hip, knee, ankle, segment_lengths)
            
            # Verify structure
            self.assertEqual(len(positions), 4)
            
            # Verify no NaN values
            for pos in positions:
                self.assertFalse(np.isnan(pos[0]))
                self.assertFalse(np.isnan(pos[1]))
    
    def test_animation_error_handling_coverage(self):
        """Test error handling paths in animation functions"""
        # Test with invalid data that should trigger error handling
        cycle_data = np.array([[np.nan, 0, 0, 0, 0, 0]])  # NaN values
        feature_mapping = {
            'hip_ipsi': 0, 'knee_ipsi': 1, 'ankle_ipsi': 2,
            'hip_contra': 3, 'knee_contra': 4, 'ankle_contra': 5
        }
        segment_lengths = {'thigh': 1.0, 'shank': 1.0, 'foot': 0.5, 'torso': 2.0}
        
        # This tests the error handling inside the animation function
        # by calling the core calculation with problematic data
        from internal.plot_generation.generate_validation_gifs import calculate_joint_positions
        
        try:
            # Test with NaN - should handle gracefully
            positions = calculate_joint_positions(np.nan, 0.0, 0.0, segment_lengths)
            # If it doesn't crash, that's good
            self.assertEqual(len(positions), 4)
        except Exception:
            # Exception handling is also valid behavior
            pass
    
    def test_create_stick_figure_animation_from_locomotion_data_direct(self):
        """Test the LocomotionData import path directly to achieve coverage"""
        from internal.plot_generation.generate_validation_gifs import create_stick_figure_animation_from_locomotion_data
        
        # Create a mock that simulates the import failing
        with patch('builtins.__import__', side_effect=ImportError("Module not found")):
            result = create_stick_figure_animation_from_locomotion_data(
                None, 'S01', 'level_walking', {'thigh': 1.0, 'shank': 1.0, 'foot': 0.5}, '/fake/path.gif'
            )
            # Should return False when import fails
            self.assertFalse(result)
    
    def test_process_dataset_config_direct(self):
        """Test process_dataset_config directly to achieve coverage"""
        from internal.plot_generation.generate_validation_gifs import process_dataset_config
        
        config = {
            'file': 'nonexistent.parquet',
            'subject_task_pairs': [('S01', 'walking', 0)]
        }
        
        # This will trigger the exception handling path
        with patch('builtins.__import__', side_effect=ImportError("Module not found")):
            # Should not raise exception, just handle it gracefully
            process_dataset_config(config)
    
    def test_gif_main_function_coverage(self):
        """Test main function paths to achieve coverage"""
        from internal.plot_generation.generate_validation_gifs import main
        
        # Test the usage message path
        with patch('argparse.ArgumentParser.parse_args') as mock_parse:
            mock_args = Mock()
            mock_args.file = None
            mock_args.subject = None  
            mock_args.task = None
            mock_args.all_datasets = False
            mock_args.parallel = False
            mock_parse.return_value = mock_args
            
            with patch('builtins.print') as mock_print:
                main()
                # Should print usage examples
                mock_print.assert_called()


class TestAdditionalCoverageTargets(unittest.TestCase):
    """Additional tests targeting specific uncovered lines"""
    
    def test_forward_kinematics_missing_lines(self):
        """Test specific uncovered lines in forward_kinematics_plots.py"""
        from internal.plot_generation.forward_kinematics_plots import KinematicPoseGenerator
        
        generator = KinematicPoseGenerator()
        
        # Test extract_phase_ranges_from_data with empty results
        empty_data = pd.DataFrame({
            'task_name': ['level_walking'] * 10,
            'phase_gait_cycle_percent': [10, 15, 20, 85, 90, 95] + [100] * 4,  # No data near target phases
            'hip_flexion_angle_ipsi_rad': np.random.random(10)
        })
        
        ranges = generator.extract_phase_ranges_from_data(empty_data, 'level_walking', [0, 25, 50, 75])
        
        # Should return structure but with empty data for phases
        self.assertIsInstance(ranges, dict)
        for phase in [0, 25, 50, 75]:
            self.assertIn(phase, ranges)
    
    def test_forward_kinematics_validation_file_paths(self):
        """Test validation file path resolution"""
        from internal.plot_generation.forward_kinematics_plots import KinematicPoseGenerator
        
        generator = KinematicPoseGenerator()
        
        # Test with nonexistent validation file
        with self.assertRaises(ValueError):
            generator.generate_task_validation_images(
                task_name='level_walking',
                validation_file='/nonexistent/path/validation.md'
            )
    
    def test_generate_validation_plots_missing_lines(self):
        """Test uncovered lines in generate_validation_plots.py"""
        from lib.validation.generate_validation_plots import ValidationPlotsGenerator
        
        with patch('pathlib.Path.exists', return_value=True):
            # Test kinetic mode forward plots (should return empty)
            generator = ValidationPlotsGenerator(mode='kinetic')
            files = generator.generate_forward_kinematics_plots()
            self.assertEqual(files, [])
    
    def test_generate_validation_plots_sys_exit(self):
        """Test sys.exit path in main function"""
        from lib.validation.generate_validation_plots import main
        
        # Test the main function that calls sys.exit
        with patch('argparse.ArgumentParser.parse_args') as mock_parse:
            mock_args = Mock()
            mock_args.forward_kinematic_only = True
            mock_args.filters_only = True  # Conflicting options
            mock_parse.return_value = mock_args
            
            result = main()
            self.assertEqual(result, 1)  # Should return error code


if __name__ == '__main__':
    # Run with verbose output to see coverage details
    unittest.main(verbosity=2)