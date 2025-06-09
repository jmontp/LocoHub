#!/usr/bin/env python3
"""
Kinematic Pose Generator

Extends walking_animator.py functionality to generate static pose visualizations
for validation purposes. Creates min/max position images at specific phase points
to embed in validation documentation.

Based on walking_animator.py forward kinematics calculations.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse

class KinematicPoseGenerator:
    """Generator for static kinematic poses for validation visualization"""
    
    def __init__(self):
        """Initialize the pose generator with segment parameters"""
        
        # Define segment lengths (same as walking_animator.py)
        self.segment_lengths = {
            'thigh': 1.0, 
            'shank': 1.0, 
            'foot': 0.5, 
            'torso': 2.0
        }
        
        # Define joint angle limits for visualization
        self.joint_limits = {
            'hip': {'min': -0.7, 'max': 2.1},      # -40° to +120°
            'knee': {'min': -0.2, 'max': 2.4},     # -10° to +140°
            'ankle': {'min': -0.9, 'max': 0.7}     # -50° to +40°
        }
        
        # Phase points for validation - Updated to v5.0 system
        self.phase_points = [0, 25, 50, 75]
        
        # Colors for different elements
        self.colors = {
            'ipsi_leg': 'blue',
            'contra_leg': 'red',
            'joints': 'black',
            'ground': 'gray',
            'torso': 'darkgreen'
        }
    
    def calculate_joint_positions(self, hip_angle: float, knee_angle: float, ankle_angle: float) -> Tuple[np.ndarray, ...]:
        """
        Calculate joint positions based on angles.
        
        Args:
            hip_angle: Hip flexion angle in radians
            knee_angle: Knee flexion angle in radians  
            ankle_angle: Ankle flexion angle in radians
            
        Returns:
            Tuple of position arrays: (hip, knee, ankle, foot)
        """
        # Convert angles to match animation coordinate system
        hip_angle_rad = hip_angle
        knee_angle_rad = knee_angle
        ankle_angle_rad = ankle_angle + np.pi / 2
        
        # Calculate positions (same logic as walking_animator.py)
        hip_position = np.array([0, 0])
        
        knee_position = hip_position + np.array([
            self.segment_lengths['thigh'] * np.sin(hip_angle_rad),
            -self.segment_lengths['thigh'] * np.cos(hip_angle_rad)
        ])
        
        total_knee_angle_rad = hip_angle_rad + knee_angle_rad
        ankle_position = knee_position + np.array([
            self.segment_lengths['shank'] * np.sin(total_knee_angle_rad),
            -self.segment_lengths['shank'] * np.cos(total_knee_angle_rad)
        ])
        
        total_ankle_angle_rad = total_knee_angle_rad + ankle_angle_rad
        foot_position = ankle_position + np.array([
            self.segment_lengths['foot'] * np.sin(total_ankle_angle_rad),
            -self.segment_lengths['foot'] * np.cos(total_ankle_angle_rad)
        ])
        
        return hip_position, knee_position, ankle_position, foot_position
    
    def draw_bilateral_pose(self, ax: plt.Axes, 
                           ipsi_hip_min: float, ipsi_knee_min: float, ipsi_ankle_min: float,
                           ipsi_hip_max: float, ipsi_knee_max: float, ipsi_ankle_max: float,
                           contra_hip_min: float, contra_knee_min: float, contra_ankle_min: float,
                           contra_hip_max: float, contra_knee_max: float, contra_ankle_max: float):
        """
        Draw bilateral min/max poses on the given axes.
        
        Args:
            ax: Matplotlib axes to draw on
            ipsi_hip_min/max, ipsi_knee_min/max, ipsi_ankle_min/max: Ipsilateral leg joint angle ranges
            contra_hip_min/max, contra_knee_min/max, contra_ankle_min/max: Contralateral leg joint angle ranges
        """
        # Hip position at origin
        hip_pos = np.array([0, 0])
        
        # Draw torso (vertical line from hip)
        torso_top = hip_pos + np.array([0, self.segment_lengths['torso']])
        ax.plot([hip_pos[0], torso_top[0]], [hip_pos[1], torso_top[1]], 
                color=self.colors['torso'], linewidth=4, alpha=0.8)
        
        # Calculate positions for min poses (dashed lines)
        ipsi_hip_min_corrected = -ipsi_hip_min
        left_min_hip_pos, left_min_knee_pos, left_min_ankle_pos, left_min_foot_pos = self.calculate_joint_positions(
            ipsi_hip_min_corrected, ipsi_knee_min, ipsi_ankle_min
        )
        
        contra_hip_min_corrected = -contra_hip_min
        right_min_hip_pos, right_min_knee_pos, right_min_ankle_pos, right_min_foot_pos = self.calculate_joint_positions(
            contra_hip_min_corrected, contra_knee_min, contra_ankle_min
        )
        
        # Calculate positions for max poses (solid lines)
        ipsi_hip_max_corrected = -ipsi_hip_max
        left_max_hip_pos, left_max_knee_pos, left_max_ankle_pos, left_max_foot_pos = self.calculate_joint_positions(
            ipsi_hip_max_corrected, ipsi_knee_max, ipsi_ankle_max
        )
        
        contra_hip_max_corrected = -contra_hip_max
        right_max_hip_pos, right_max_knee_pos, right_max_ankle_pos, right_max_foot_pos = self.calculate_joint_positions(
            contra_hip_max_corrected, contra_knee_max, contra_ankle_max
        )
        
        # Draw left leg (blue) - min pose (dashed)
        ax.plot([hip_pos[0], left_min_knee_pos[0]], [hip_pos[1], left_min_knee_pos[1]], 
                color=self.colors['ipsi_leg'], linewidth=3, alpha=0.7, linestyle='--')
        ax.plot([left_min_knee_pos[0], left_min_ankle_pos[0]], [left_min_knee_pos[1], left_min_ankle_pos[1]], 
                color=self.colors['ipsi_leg'], linewidth=3, alpha=0.7, linestyle='--')
        ax.plot([left_min_ankle_pos[0], left_min_foot_pos[0]], [left_min_ankle_pos[1], left_min_foot_pos[1]], 
                color=self.colors['ipsi_leg'], linewidth=3, alpha=0.7, linestyle='--')
        
        # Draw left leg (blue) - max pose (solid)
        ax.plot([hip_pos[0], left_max_knee_pos[0]], [hip_pos[1], left_max_knee_pos[1]], 
                color=self.colors['ipsi_leg'], linewidth=3, alpha=0.9, linestyle='-')
        ax.plot([left_max_knee_pos[0], left_max_ankle_pos[0]], [left_max_knee_pos[1], left_max_ankle_pos[1]], 
                color=self.colors['ipsi_leg'], linewidth=3, alpha=0.9, linestyle='-')
        ax.plot([left_max_ankle_pos[0], left_max_foot_pos[0]], [left_max_ankle_pos[1], left_max_foot_pos[1]], 
                color=self.colors['ipsi_leg'], linewidth=3, alpha=0.9, linestyle='-')
        
        # Draw right leg (red) - min pose (dashed)
        ax.plot([hip_pos[0], right_min_knee_pos[0]], [hip_pos[1], right_min_knee_pos[1]], 
                color=self.colors['contra_leg'], linewidth=3, alpha=0.7, linestyle='--')
        ax.plot([right_min_knee_pos[0], right_min_ankle_pos[0]], [right_min_knee_pos[1], right_min_ankle_pos[1]], 
                color=self.colors['contra_leg'], linewidth=3, alpha=0.7, linestyle='--')
        ax.plot([right_min_ankle_pos[0], right_min_foot_pos[0]], [right_min_ankle_pos[1], right_min_foot_pos[1]], 
                color=self.colors['contra_leg'], linewidth=3, alpha=0.7, linestyle='--')
        
        # Draw right leg (red) - max pose (solid)
        ax.plot([hip_pos[0], right_max_knee_pos[0]], [hip_pos[1], right_max_knee_pos[1]], 
                color=self.colors['contra_leg'], linewidth=3, alpha=0.9, linestyle='-')
        ax.plot([right_max_knee_pos[0], right_max_ankle_pos[0]], [right_max_knee_pos[1], right_max_ankle_pos[1]], 
                color=self.colors['contra_leg'], linewidth=3, alpha=0.9, linestyle='-')
        ax.plot([right_max_ankle_pos[0], right_max_foot_pos[0]], [right_max_ankle_pos[1], right_max_foot_pos[1]], 
                color=self.colors['contra_leg'], linewidth=3, alpha=0.9, linestyle='-')
        
        # Draw joints as circles
        joint_radius = 0.04
        # Left leg joints
        for pos in [left_min_knee_pos, left_min_ankle_pos]:
            circle = Circle(pos, joint_radius, facecolor=self.colors['ipsi_leg'], edgecolor='black',
                           alpha=0.7, zorder=10)
            ax.add_patch(circle)
        for pos in [left_max_knee_pos, left_max_ankle_pos]:
            circle = Circle(pos, joint_radius, facecolor=self.colors['ipsi_leg'], edgecolor='black',
                           alpha=0.9, zorder=10)
            ax.add_patch(circle)
        
        # Right leg joints
        for pos in [right_min_knee_pos, right_min_ankle_pos]:
            circle = Circle(pos, joint_radius, facecolor=self.colors['contra_leg'], edgecolor='black',
                           alpha=0.7, zorder=10)
            ax.add_patch(circle)
        for pos in [right_max_knee_pos, right_max_ankle_pos]:
            circle = Circle(pos, joint_radius, facecolor=self.colors['contra_leg'], edgecolor='black',
                           alpha=0.9, zorder=10)
            ax.add_patch(circle)
        
        # Hip joint (shared)
        hip_circle = Circle(hip_pos, joint_radius*1.2, facecolor=self.colors['joints'], 
                           edgecolor='black', alpha=1.0, zorder=15)
        ax.add_patch(hip_circle)
    
    def generate_range_visualization(self, task_name: str, phase_point: float, 
                                   joint_ranges: Dict[str, Dict[str, float]], 
                                   output_path: str) -> str:
        """
        Generate a visualization showing min and max poses at a specific phase point.
        
        Args:
            task_name: Name of the locomotion task
            phase_point: Phase percentage (0, 33, 50, 66)
            joint_ranges: Dictionary with min/max values for each joint
            output_path: Directory to save the image
            
        Returns:
            Path to the generated image file
        """
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Extract bilateral joint angles for min and max poses
        # Left leg angles
        ipsi_hip_min = joint_ranges.get('hip_flexion_angle_left', {}).get('min', 0)
        ipsi_hip_max = joint_ranges.get('hip_flexion_angle_left', {}).get('max', 0.5)
        ipsi_knee_min = joint_ranges.get('knee_flexion_angle_left', {}).get('min', 0)
        ipsi_knee_max = joint_ranges.get('knee_flexion_angle_left', {}).get('max', 1.0)
        ipsi_ankle_min = joint_ranges.get('ankle_flexion_angle_left', {}).get('min', -0.2)
        ipsi_ankle_max = joint_ranges.get('ankle_flexion_angle_left', {}).get('max', 0.2)
        
        # Right leg angles
        contra_hip_min = joint_ranges.get('hip_flexion_angle_right', {}).get('min', -0.2)
        contra_hip_max = joint_ranges.get('hip_flexion_angle_right', {}).get('max', 0.3)
        contra_knee_min = joint_ranges.get('knee_flexion_angle_right', {}).get('min', 0)
        contra_knee_max = joint_ranges.get('knee_flexion_angle_right', {}).get('max', 1.0)
        contra_ankle_min = joint_ranges.get('ankle_flexion_angle_right', {}).get('min', -0.2)
        contra_ankle_max = joint_ranges.get('ankle_flexion_angle_right', {}).get('max', 0.2)
        
        # Draw bilateral poses (min=dashed, max=solid)
        self.draw_bilateral_pose(ax, 
                               ipsi_hip_min, ipsi_knee_min, ipsi_ankle_min,
                               ipsi_hip_max, ipsi_knee_max, ipsi_ankle_max,
                               contra_hip_min, contra_knee_min, contra_ankle_min,
                               contra_hip_max, contra_knee_max, contra_ankle_max)
        
        # Draw ground line
        ground_level = -(self.segment_lengths['thigh'] + self.segment_lengths['shank'])
        ax.axhline(y=ground_level, color=self.colors['ground'], 
                  linestyle='-', linewidth=2, alpha=0.5, label='Ground')
        
        # Set axis properties
        ax.set_xlim(-2.5, 2.5)
        ax.set_ylim(ground_level - 0.5, self.segment_lengths['torso'] + 0.5)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        
        # Add labels and title
        ax.set_title(f'{task_name.replace("_", " ").title()}\nPhase {phase_point}% - Bilateral Joint Range Validation', 
                    fontsize=14, fontweight='bold')
        ax.set_xlabel('Anterior-Posterior (m)', fontsize=12)
        ax.set_ylabel('Vertical (m)', fontsize=12)
        
        # Add legend
        legend_elements = [
            plt.Line2D([0], [0], color=self.colors['ipsi_leg'], linewidth=3, linestyle='-', label='Ipsilateral Leg (Max)'),
            plt.Line2D([0], [0], color=self.colors['ipsi_leg'], linewidth=3, linestyle='--', label='Ipsilateral Leg (Min)'),
            plt.Line2D([0], [0], color=self.colors['contra_leg'], linewidth=3, linestyle='-', label='Contralateral Leg (Max)'),
            plt.Line2D([0], [0], color=self.colors['contra_leg'], linewidth=3, linestyle='--', label='Contralateral Leg (Min)'),
            plt.Line2D([0], [0], color=self.colors['torso'], linewidth=4, label='Torso'),
            plt.Line2D([0], [0], color=self.colors['ground'], linewidth=2, label='Ground')
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=9)
        
        # Add bilateral angle annotations (fixed newline characters)
        annotation_text = (
            f"LEFT LEG RANGES:\n"
            f"Hip: {np.degrees(ipsi_hip_min):.1f}° to {np.degrees(ipsi_hip_max):.1f}°\n"
            f"Knee: {np.degrees(ipsi_knee_min):.1f}° to {np.degrees(ipsi_knee_max):.1f}°\n"
            f"Ankle: {np.degrees(ipsi_ankle_min):.1f}° to {np.degrees(ipsi_ankle_max):.1f}°\n\n"
            f"RIGHT LEG RANGES:\n"
            f"Hip: {np.degrees(contra_hip_min):.1f}° to {np.degrees(contra_hip_max):.1f}°\n"
            f"Knee: {np.degrees(contra_knee_min):.1f}° to {np.degrees(contra_knee_max):.1f}°\n"
            f"Ankle: {np.degrees(contra_ankle_min):.1f}° to {np.degrees(contra_ankle_max):.1f}°"
        )
        ax.text(0.02, 0.98, annotation_text, transform=ax.transAxes, 
               fontsize=9, verticalalignment='top', 
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # Save the figure
        os.makedirs(output_path, exist_ok=True)
        filename = f"{task_name}_phase_{phase_point:02d}_range.png"
        filepath = os.path.join(output_path, filename)
        
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def extract_phase_ranges_from_data(self, data: pd.DataFrame, task_name: str, 
                                     phase_points: List[float]) -> Dict[float, Dict[str, Dict[str, float]]]:
        """
        Extract min/max ranges for each joint at specific phase points from real data.
        
        Args:
            data: DataFrame with biomechanical data
            task_name: Name of the task
            phase_points: List of phase percentages to analyze
            
        Returns:
            Dictionary with ranges for each phase point
        """
        results = {}
        
        # Filter data for the specific task
        if 'task_name' in data.columns:
            task_data = data[data['task_name'] == task_name].copy()
        else:
            task_data = data.copy()
        
        # Find phase column
        phase_columns = [col for col in data.columns if col.startswith('phase_')]
        if not phase_columns:
            raise ValueError("No phase column found in data")
        
        phase_column = phase_columns[0]
        
        # Define joint angle columns to analyze
        joint_columns = {
            'hip_flexion_angle': [col for col in data.columns if 'hip_flexion_angle' in col and '_rad' in col],
            'knee_flexion_angle': [col for col in data.columns if 'knee_flexion_angle' in col and '_rad' in col],
            'ankle_flexion_angle': [col for col in data.columns if 'ankle_flexion_angle' in col and '_rad' in col]
        }
        
        for phase_point in phase_points:
            phase_ranges = {}
            
            # Find data near this phase point
            tolerance = 5.0  # ±5% phase tolerance
            phase_mask = (np.abs(task_data[phase_column] - phase_point) <= tolerance)
            phase_data = task_data[phase_mask]
            
            if len(phase_data) > 0:
                for joint_type, columns in joint_columns.items():
                    if columns:
                        # Use first available column for this joint
                        col = columns[0]
                        if col in phase_data.columns:
                            joint_data = phase_data[col].dropna()
                            if len(joint_data) > 0:
                                phase_ranges[joint_type] = {
                                    'min': float(joint_data.min()),
                                    'max': float(joint_data.max()),
                                    'mean': float(joint_data.mean()),
                                    'std': float(joint_data.std()),
                                    'data_points': len(joint_data)
                                }
            
            results[phase_point] = phase_ranges
        
        return results
    
    def generate_task_validation_images(self, task_name: str, 
                                      validation_ranges: Optional[Dict] = None,
                                      output_dir: str = "validation_images") -> List[str]:
        """
        Generate validation images for all phase points of a task.
        
        Args:
            task_name: Name of the locomotion task
            validation_ranges: Optional pre-computed ranges, otherwise uses defaults
            output_dir: Directory to save images
            
        Returns:
            List of generated image file paths
        """
        generated_files = []
        
        # Use default ranges if none provided
        if validation_ranges is None:
            validation_ranges = self._get_default_task_ranges(task_name)
        
        # Generate image for each phase point
        for phase_point in self.phase_points:
            phase_ranges = validation_ranges.get(phase_point, {})
            
            # Ensure we have some default ranges if data is missing
            if not phase_ranges:
                phase_ranges = self._get_default_phase_ranges(task_name, phase_point)
            
            filepath = self.generate_range_visualization(
                task_name, phase_point, phase_ranges, output_dir
            )
            generated_files.append(filepath)
            print(f"Generated: {filepath}")
        
        return generated_files
    
    def _get_default_task_ranges(self, task_name: str) -> Dict[float, Dict[str, Dict[str, float]]]:
        """Get default ranges for a task if no data is available"""
        
        # Define task-specific default ranges based on typical biomechanics
        task_defaults = {
            'level_walking': {
                0: {    # Heel strike
                    'hip_flexion_angle': {'min': 0.1, 'max': 0.6},
                    'knee_flexion_angle': {'min': 0.0, 'max': 0.3},
                    'ankle_flexion_angle': {'min': -0.1, 'max': 0.1}
                },
                33: {   # Mid-stance
                    'hip_flexion_angle': {'min': -0.1, 'max': 0.3},
                    'knee_flexion_angle': {'min': 0.0, 'max': 0.4},
                    'ankle_flexion_angle': {'min': -0.2, 'max': 0.1}
                },
                50: {   # Push-off
                    'hip_flexion_angle': {'min': -0.3, 'max': 0.2},
                    'knee_flexion_angle': {'min': 0.1, 'max': 0.5},
                    'ankle_flexion_angle': {'min': -0.3, 'max': 0.0}
                },
                66: {   # Mid-swing
                    'hip_flexion_angle': {'min': 0.2, 'max': 0.8},
                    'knee_flexion_angle': {'min': 0.3, 'max': 1.2},
                    'ankle_flexion_angle': {'min': -0.1, 'max': 0.3}
                }
            },
            'incline_walking': {
                0: {'hip_flexion_angle': {'min': 0.2, 'max': 0.8}, 'knee_flexion_angle': {'min': 0.0, 'max': 0.4}, 'ankle_flexion_angle': {'min': 0.0, 'max': 0.2}},
                33: {'hip_flexion_angle': {'min': 0.0, 'max': 0.5}, 'knee_flexion_angle': {'min': 0.1, 'max': 0.6}, 'ankle_flexion_angle': {'min': -0.1, 'max': 0.2}},
                50: {'hip_flexion_angle': {'min': -0.2, 'max': 0.3}, 'knee_flexion_angle': {'min': 0.2, 'max': 0.7}, 'ankle_flexion_angle': {'min': -0.2, 'max': 0.1}},
                66: {'hip_flexion_angle': {'min': 0.3, 'max': 1.0}, 'knee_flexion_angle': {'min': 0.4, 'max': 1.4}, 'ankle_flexion_angle': {'min': 0.0, 'max': 0.4}}
            },
            'up_stairs': {
                0: {'hip_flexion_angle': {'min': 0.3, 'max': 1.0}, 'knee_flexion_angle': {'min': 0.1, 'max': 0.6}, 'ankle_flexion_angle': {'min': 0.0, 'max': 0.3}},
                33: {'hip_flexion_angle': {'min': 0.5, 'max': 1.2}, 'knee_flexion_angle': {'min': 0.3, 'max': 1.0}, 'ankle_flexion_angle': {'min': 0.1, 'max': 0.4}},
                50: {'hip_flexion_angle': {'min': 0.6, 'max': 1.4}, 'knee_flexion_angle': {'min': 0.5, 'max': 1.4}, 'ankle_flexion_angle': {'min': 0.2, 'max': 0.5}},
                66: {'hip_flexion_angle': {'min': 0.4, 'max': 1.1}, 'knee_flexion_angle': {'min': 0.7, 'max': 1.6}, 'ankle_flexion_angle': {'min': 0.3, 'max': 0.5}}
            }
        }
        
        return task_defaults.get(task_name, task_defaults['level_walking'])
    
    def _get_default_phase_ranges(self, task_name: str, phase_point: float) -> Dict[str, Dict[str, float]]:
        """Get default ranges for a specific phase point"""
        defaults = self._get_default_task_ranges(task_name)
        return defaults.get(phase_point, {
            'hip_flexion_angle': {'min': 0.0, 'max': 0.5},
            'knee_flexion_angle': {'min': 0.0, 'max': 1.0},
            'ankle_flexion_angle': {'min': -0.2, 'max': 0.2}
        })


def main():
    """Main function for testing the kinematic pose generator"""
    
    parser = argparse.ArgumentParser(description='Generate kinematic validation poses')
    parser.add_argument('--task', type=str, default='level_walking', 
                       help='Task name for pose generation')
    parser.add_argument('--output-dir', type=str, default='validation_images',
                       help='Output directory for images')
    parser.add_argument('--data-file', type=str, 
                       help='Optional data file to extract real ranges')
    
    args = parser.parse_args()
    
    # Create pose generator
    generator = KinematicPoseGenerator()
    
    # Load data if provided
    validation_ranges = None
    if args.data_file:
        try:
            data = pd.read_parquet(args.data_file)
            print(f"Loaded data from {args.data_file}")
            validation_ranges = generator.extract_phase_ranges_from_data(
                data, args.task, generator.phase_points
            )
            print(f"Extracted ranges for {len(validation_ranges)} phase points")
        except Exception as e:
            print(f"Error loading data: {e}")
            print("Using default ranges instead")
    
    # Generate validation images
    print(f"Generating validation images for task: {args.task}")
    generated_files = generator.generate_task_validation_images(
        args.task, validation_ranges, args.output_dir
    )
    
    print(f"\\nGenerated {len(generated_files)} validation images:")
    for filepath in generated_files:
        print(f"  - {filepath}")
    
    return generated_files


if __name__ == "__main__":
    main()