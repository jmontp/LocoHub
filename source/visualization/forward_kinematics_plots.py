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
import re
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
        
        total_knee_angle_rad = hip_angle_rad - knee_angle_rad
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
                           left_hip_min: float, left_knee_min: float, left_ankle_min: float,
                           left_hip_avg: float, left_knee_avg: float, left_ankle_avg: float,
                           left_hip_max: float, left_knee_max: float, left_ankle_max: float,
                           right_hip_min: float, right_knee_min: float, right_ankle_min: float,
                           right_hip_avg: float, right_knee_avg: float, right_ankle_avg: float,
                           right_hip_max: float, right_knee_max: float, right_ankle_max: float):
        """
        Draw bilateral min/avg/max poses matching original style.
        
        Args:
            ax: Matplotlib axes to draw on
            left/right joint angle ranges with min, avg, max values
        """
        # Hip position at origin (shared by both legs)
        hip_pos = np.array([0, 0])
        
        # Draw torso (vertical line from hip)
        torso_top = hip_pos + np.array([0, self.segment_lengths['torso']])
        ax.plot([hip_pos[0], torso_top[0]], [hip_pos[1], torso_top[1]], 
                color='black', linewidth=4)
        
        # Draw pelvis as horizontal line
        pelvis_width = 0.3
        ax.plot([hip_pos[0] - pelvis_width/2, hip_pos[0] + pelvis_width/2], 
                [hip_pos[1], hip_pos[1]], 
                color='black', linewidth=6, solid_capstyle='round')
        
        # Calculate positions for all poses
        # Left leg positions
        left_avg_hip, left_avg_knee, left_avg_ankle, left_avg_foot = self.calculate_joint_positions(
            left_hip_avg, left_knee_avg, left_ankle_avg)
        left_min_hip, left_min_knee, left_min_ankle, left_min_foot = self.calculate_joint_positions(
            left_hip_min, left_knee_min, left_ankle_min)
        left_max_hip, left_max_knee, left_max_ankle, left_max_foot = self.calculate_joint_positions(
            left_hip_max, left_knee_max, left_ankle_max)
        
        # Right leg positions (offset from shared hip)
        right_avg_hip, right_avg_knee, right_avg_ankle, right_avg_foot = self.calculate_joint_positions(
            right_hip_avg, right_knee_avg, right_ankle_avg)
        right_min_hip, right_min_knee, right_min_ankle, right_min_foot = self.calculate_joint_positions(
            right_hip_min, right_knee_min, right_ankle_min)
        right_max_hip, right_max_knee, right_max_ankle, right_max_foot = self.calculate_joint_positions(
            right_hip_max, right_knee_max, right_ankle_max)
        
        # Draw left leg (blue) - min pose with 10% alpha
        ax.plot([hip_pos[0], left_min_knee[0]], [hip_pos[1], left_min_knee[1]], 
                color='blue', linewidth=3, alpha=0.1, linestyle='--')
        ax.plot([left_min_knee[0], left_min_ankle[0]], [left_min_knee[1], left_min_ankle[1]], 
                color='blue', linewidth=3, alpha=0.1, linestyle='--')
        ax.plot([left_min_ankle[0], left_min_foot[0]], [left_min_ankle[1], left_min_foot[1]], 
                color='blue', linewidth=3, alpha=0.1, linestyle='--')
        
        # Draw left leg (blue) - max pose with 10% alpha
        ax.plot([hip_pos[0], left_max_knee[0]], [hip_pos[1], left_max_knee[1]], 
                color='blue', linewidth=3, alpha=0.1, linestyle='-')
        ax.plot([left_max_knee[0], left_max_ankle[0]], [left_max_knee[1], left_max_ankle[1]], 
                color='blue', linewidth=3, alpha=0.1, linestyle='-')
        ax.plot([left_max_ankle[0], left_max_foot[0]], [left_max_ankle[1], left_max_foot[1]], 
                color='blue', linewidth=3, alpha=0.1, linestyle='-')
        
        # Draw left leg (blue) - average pose (solid)
        ax.plot([hip_pos[0], left_avg_knee[0]], [hip_pos[1], left_avg_knee[1]], 
                color='blue', linewidth=3, alpha=1.0, linestyle='-')
        ax.plot([left_avg_knee[0], left_avg_ankle[0]], [left_avg_knee[1], left_avg_ankle[1]], 
                color='blue', linewidth=3, alpha=1.0, linestyle='-')
        ax.plot([left_avg_ankle[0], left_avg_foot[0]], [left_avg_ankle[1], left_avg_foot[1]], 
                color='blue', linewidth=3, alpha=1.0, linestyle='-')
        
        # Draw right leg (red) - min pose with 10% alpha
        ax.plot([hip_pos[0], right_min_knee[0]], [hip_pos[1], right_min_knee[1]], 
                color='red', linewidth=3, alpha=0.1, linestyle='--')
        ax.plot([right_min_knee[0], right_min_ankle[0]], [right_min_knee[1], right_min_ankle[1]], 
                color='red', linewidth=3, alpha=0.1, linestyle='--')
        ax.plot([right_min_ankle[0], right_min_foot[0]], [right_min_ankle[1], right_min_foot[1]], 
                color='red', linewidth=3, alpha=0.1, linestyle='--')
        
        # Draw right leg (red) - max pose with 10% alpha
        ax.plot([hip_pos[0], right_max_knee[0]], [hip_pos[1], right_max_knee[1]], 
                color='red', linewidth=3, alpha=0.1, linestyle='-')
        ax.plot([right_max_knee[0], right_max_ankle[0]], [right_max_knee[1], right_max_ankle[1]], 
                color='red', linewidth=3, alpha=0.1, linestyle='-')
        ax.plot([right_max_ankle[0], right_max_foot[0]], [right_max_ankle[1], right_max_foot[1]], 
                color='red', linewidth=3, alpha=0.1, linestyle='-')
        
        # Draw right leg (red) - average pose (solid)
        ax.plot([hip_pos[0], right_avg_knee[0]], [hip_pos[1], right_avg_knee[1]], 
                color='red', linewidth=3, alpha=1.0, linestyle='-')
        ax.plot([right_avg_knee[0], right_avg_ankle[0]], [right_avg_knee[1], right_avg_ankle[1]], 
                color='red', linewidth=3, alpha=1.0, linestyle='-')
        ax.plot([right_avg_ankle[0], right_avg_foot[0]], [right_avg_ankle[1], right_avg_foot[1]], 
                color='red', linewidth=3, alpha=1.0, linestyle='-')
        
        # Draw joints as circles for average pose only
        joint_radius = 0.04
        for pos in [left_avg_knee, left_avg_ankle]:
            circle = Circle(pos, joint_radius, facecolor='blue', edgecolor='black', zorder=10)
            ax.add_patch(circle)
        for pos in [right_avg_knee, right_avg_ankle]:
            circle = Circle(pos, joint_radius, facecolor='red', edgecolor='black', zorder=10)
            ax.add_patch(circle)
        
        # Hip joint (shared)
        hip_circle = Circle(hip_pos, joint_radius*1.2, facecolor='black', 
                           edgecolor='black', alpha=1.0, zorder=15)
        ax.add_patch(hip_circle)
    
    def generate_range_visualization(self, task_name: str, phase_point: float, 
                                   joint_ranges: Dict[str, Dict[str, float]], 
                                   output_path: str) -> str:
        """
        Generate a visualization showing min and max poses at a specific phase point.
        
        Args:
            task_name: Name of the locomotion task
            phase_point: Phase percentage (0, 25, 50, 75)
            joint_ranges: Dictionary with min/max values for each joint
            output_path: Directory to save the image
            
        Returns:
            Path to the generated image file
        """
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Extract bilateral joint angles for min and max poses - Updated for ipsi/contra naming
        # Ipsilateral leg angles
        ipsi_hip_min = joint_ranges.get('hip_flexion_angle_ipsi', {}).get('min', 0)
        ipsi_hip_max = joint_ranges.get('hip_flexion_angle_ipsi', {}).get('max', 0.5)
        ipsi_knee_min = joint_ranges.get('knee_flexion_angle_ipsi', {}).get('min', 0)
        ipsi_knee_max = joint_ranges.get('knee_flexion_angle_ipsi', {}).get('max', 1.0)
        ipsi_ankle_min = joint_ranges.get('ankle_flexion_angle_ipsi', {}).get('min', -0.2)
        ipsi_ankle_max = joint_ranges.get('ankle_flexion_angle_ipsi', {}).get('max', 0.2)
        
        # Contralateral leg angles
        contra_hip_min = joint_ranges.get('hip_flexion_angle_contra', {}).get('min', -0.2)
        contra_hip_max = joint_ranges.get('hip_flexion_angle_contra', {}).get('max', 0.3)
        contra_knee_min = joint_ranges.get('knee_flexion_angle_contra', {}).get('min', 0)
        contra_knee_max = joint_ranges.get('knee_flexion_angle_contra', {}).get('max', 1.0)
        contra_ankle_min = joint_ranges.get('ankle_flexion_angle_contra', {}).get('min', -0.2)
        contra_ankle_max = joint_ranges.get('ankle_flexion_angle_contra', {}).get('max', 0.2)
        
        # Calculate average values for main pose
        ipsi_hip_avg = (ipsi_hip_min + ipsi_hip_max) / 2
        ipsi_knee_avg = (ipsi_knee_min + ipsi_knee_max) / 2
        ipsi_ankle_avg = (ipsi_ankle_min + ipsi_ankle_max) / 2
        contra_hip_avg = (contra_hip_min + contra_hip_max) / 2
        contra_knee_avg = (contra_knee_min + contra_knee_max) / 2
        contra_ankle_avg = (contra_ankle_min + contra_ankle_max) / 2
        
        # Draw min/avg/max poses with correct transparency
        self.draw_bilateral_pose(ax, 
                               ipsi_hip_min, ipsi_knee_min, ipsi_ankle_min,
                               ipsi_hip_avg, ipsi_knee_avg, ipsi_ankle_avg,
                               ipsi_hip_max, ipsi_knee_max, ipsi_ankle_max,
                               contra_hip_min, contra_knee_min, contra_ankle_min,
                               contra_hip_avg, contra_knee_avg, contra_ankle_avg,
                               contra_hip_max, contra_knee_max, contra_ankle_max)
        
        # Draw walking direction arrow - lowered to avoid legend conflict
        ax.annotate('', xy=(1.5, 1.3), xytext=(0.5, 1.3),
                   arrowprops=dict(arrowstyle='->', lw=3, color='green'))
        ax.text(1.0, 1.5, 'Walking Direction', ha='center', va='bottom', 
               fontsize=12, color='green', fontweight='bold')
        
        # Draw ground line
        ground_level = -2.0
        ax.axhline(y=ground_level, color='gray', linestyle='-', linewidth=2)
        
        # Set axis properties - remove axis text as requested
        ax.set_xlim(-2, 2)
        ax.set_ylim(-2.5, 2.5)
        ax.set_aspect('equal')
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        
        # Title in original style
        if phase_point == 25:
            phase_name = "Mid Phase"
        elif phase_point == 50:
            phase_name = "Mid Phase" 
        elif phase_point == 75:
            phase_name = "Mid Phase"
        else:
            phase_name = f"Phase {phase_point}%"
            
        ax.set_title(f'{task_name.replace("_", " ").title()} - {phase_name}\n' +
                    'Joint Angle Range Visualization\n(Frontal Plane View)', 
                    fontsize=14, fontweight='bold')
        
        # Simple legend with correct ipsi/contra terminology
        legend_elements = [
            plt.Line2D([0], [0], color='blue', linewidth=3, label='Ipsilateral Leg'),
            plt.Line2D([0], [0], color='red', linewidth=3, label='Contralateral Leg'),
            plt.Line2D([0], [0], color='black', linewidth=3, label='Pelvis'),
            plt.Line2D([0], [0], color='gray', linewidth=2, label='Ground')
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
        
        # Simple angle annotations in original min/avg/max format
        ax.text(-1.8, 1.5, 
               f"Hip: {np.degrees(ipsi_hip_min):.0f}° / {np.degrees(ipsi_hip_avg):.0f}° / {np.degrees(ipsi_hip_max):.0f}°\n\n"
               f"Knee: {np.degrees(ipsi_knee_min):.0f}° / {np.degrees(ipsi_knee_avg):.0f}° / {np.degrees(ipsi_knee_max):.0f}°\n\n"
               f"Ankle: {np.degrees(ipsi_ankle_min):.0f}° / {np.degrees(ipsi_ankle_avg):.0f}° / {np.degrees(ipsi_ankle_max):.0f}°",
               fontsize=11, verticalalignment='top')
        
        # Range explanation box
        ax.text(-1.8, 0.8,
               "Range: Min / Avg / Max\n"
               "Avg: solid line\n"
               "Min: dashed (10% alpha)\n"
               "Max: solid (10% alpha)",
               fontsize=9, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='white', edgecolor='black', alpha=0.8))
        
        # Save the figure
        os.makedirs(output_path, exist_ok=True)
        filename = f"{task_name}_forward_kinematics_phase_{phase_point:02d}_range.png"
        filepath = os.path.join(output_path, filename)
        
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
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
                                      output_dir: str = "docs/standard_spec/validation",
                                      validation_file: str = "docs/standard_spec/validation_expectations_kinematic.md") -> List[str]:
        """
        Generate validation images for all phase points of a task.
        
        Args:
            task_name: Name of the locomotion task
            validation_ranges: Optional pre-computed ranges, otherwise parses from validation file
            output_dir: Directory to save images
            validation_file: Path to validation expectations markdown file
            
        Returns:
            List of generated image file paths
        """
        generated_files = []
        
        # Parse validation expectations if no ranges provided
        if validation_ranges is None:
            try:
                # Find the validation file
                if os.path.exists(validation_file):
                    validation_path = validation_file
                else:
                    # Try from project root
                    project_root = Path(__file__).parent.parent.parent
                    validation_path = project_root / validation_file
                    if not validation_path.exists():
                        print(f"Warning: Could not find validation file at {validation_file}, using defaults")
                        validation_ranges = self._get_default_task_ranges(task_name)
                    else:
                        validation_path = str(validation_path)
                
                if validation_ranges is None:
                    print(f"Parsing validation expectations from: {validation_path}")
                    all_validation_data = self.parse_validation_expectations(validation_path)
                    validation_ranges = all_validation_data.get(task_name, {})
                    
                    if not validation_ranges:
                        print(f"Warning: No validation data found for task {task_name}, using defaults")
                        validation_ranges = self._get_default_task_ranges(task_name)
                    else:
                        print(f"Successfully loaded validation data for {task_name}")
                        
            except Exception as e:
                print(f"Error parsing validation file: {e}, using defaults")
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
    
    def parse_validation_expectations(self, file_path: str) -> Dict[str, Dict[int, Dict[str, Dict[str, float]]]]:
        """
        Parse the validation_expectations_kinematic.md file to extract joint angle ranges.
        
        Args:
            file_path: Path to the validation_expectations_kinematic.md file
            
        Returns:
            Dictionary structured as: {task_name: {phase: {joint: {min, max}}}}
        """
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Dictionary to store parsed data
        validation_data = {}
        
        # Find all task sections
        task_pattern = r'### Task: ([\w_]+)\n'
        tasks = re.findall(task_pattern, content)
        
        for task in tasks:
            validation_data[task] = {}
            
            # Find the task section
            task_section_pattern = rf'### Task: {re.escape(task)}\n(.*?)(?=### Task:|## ✅ \*\*MAJOR UPDATE COMPLETED\*\*|## Joint Validation Range Summary|## Pattern Definitions|$)'
            task_match = re.search(task_section_pattern, content, re.DOTALL)
            
            if task_match:
                task_content = task_match.group(1)
                
                # Find all phase sections within this task
                phase_pattern = r'#### Phase (\d+)%.*?\n\| Variable \| Min_Value \| Max_Value \| Units \| Notes \|(.*?)(?=####|\*\*Contralateral|\*\*Note:|\*\*Kinematic|$)'
                phase_matches = re.findall(phase_pattern, task_content, re.DOTALL)
                
                for phase_str, table_content in phase_matches:
                    phase = int(phase_str)
                    validation_data[task][phase] = {}
                    
                    # Parse table rows for joint angles
                    row_pattern = r'\| ([\w_]+) \| ([-\d.]+) \([^)]+\) \| ([-\d.]+) \([^)]+\) \| (\w+) \|'
                    rows = re.findall(row_pattern, table_content)
                    
                    for variable, min_val, max_val, unit in rows:
                        # Extract bilateral joint angles (both left and right legs)
                        if ('_ipsi_rad' in variable) and unit == 'rad':
                            # Determine joint type and side
                            if 'hip_flexion_angle' in variable:
                                joint_name = 'hip_flexion_angle_ipsi'
                            elif 'knee_flexion_angle' in variable:
                                joint_name = 'knee_flexion_angle_ipsi'
                            elif 'ankle_flexion_angle' in variable:
                                joint_name = 'ankle_flexion_angle_ipsi'
                            else:
                                continue
                            
                            validation_data[task][phase][joint_name] = {
                                'min': float(min_val),
                                'max': float(max_val)
                            }
        
        return validation_data
    
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
    parser.add_argument('--output-dir', type=str, default='docs/standard_spec/validation',
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