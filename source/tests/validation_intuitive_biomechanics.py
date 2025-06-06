"""
Intuitive Biomechanics Validator

This module provides phase-based validation using biomechanically intuitive expected ranges
for joint angles at key gait phases. This complements the existing validation system by
providing more interpretable test cases based on clinical gait analysis knowledge.

Key Features:
- Expected joint angle ranges at heel strike (0-10% phase) and mid-stance (45-55% phase)
- Task-specific adjustments for different activities
- Velocity validation through phase derivatives
- Easy-to-read tabular format for clinical interpretation

Usage:
    validator = IntuitiveValidator(df)
    results = validator.validate()
    report = validator.get_clinical_report()
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class PhaseRange:
    """Expected angle range at a specific phase window"""
    min_angle: float  # radians
    max_angle: float  # radians
    phase_start: float  # % (0-100)
    phase_end: float   # % (0-100)
    description: str

class IntuitiveValidator:
    """
    Biomechanically intuitive validator based on expected joint angles
    during key phases of movement cycles.
    """
    
    def __init__(self, df: pd.DataFrame):
        """
        Initialize validator with phase-indexed data.
        
        Args:
            df: DataFrame with columns including 'phase_%', joint angles in radians
        """
        self.df = df.copy()
        self.df['validation_intuitive'] = True
        self.df['intuitive_errors'] = [[] for _ in range(len(df))]
        
        # Track validation results
        self.validation_results = defaultdict(list)
        
        # Track step-level errors for detailed debugging
        self.step_errors = []  # List of detailed error records for each failing step
        
        # Define biomechanical expectations table
        self._build_expectations_table()
    
    def _deg_to_rad(self, degrees: float) -> float:
        """Convert degrees to radians"""
        return degrees * np.pi / 180
    
    def _build_expectations_table(self):
        """
        Build comprehensive table of expected joint angles for different tasks and phases.
        
        Based on clinical gait analysis literature and biomechanical research.
        All angles stored in radians, with positive values following the sign convention:
        - Hip: Extension positive
        - Knee: Extension positive  
        - Ankle: Dorsiflexion positive
        """
        
        # INDEPENDENT TASK EXPECTATIONS - No inheritance or baselines
        self.expectations = {
            # LEVEL WALKING - Normal pace on flat ground
            'level_walking': {
                'heel_strike': {
                    'hip_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(15), self._deg_to_rad(25), 0, 10,
                        "Hip flexed 15-25° for limb advancement during level walking heel strike"
                    ),
                    'knee_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(-5), self._deg_to_rad(5), 0, 10,
                        "Knee near neutral (-5 to 5°) for stable initial contact during level walking"
                    ),
                    'ankle_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(-5), self._deg_to_rad(5), 0, 10,
                        "Ankle near neutral (-5 to 5°) for heel-first contact during level walking"
                    ),
                    'hip_adduction_angle_rad': PhaseRange(
                        self._deg_to_rad(-10), self._deg_to_rad(10), 0, 10,
                        "Hip adduction controlled (-10 to 10°) for pelvic stability during level walking heel strike"
                    ),
                },
                'mid_stance': {
                    'hip_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(-5), self._deg_to_rad(5), 45, 55,
                        "Hip near neutral (-5 to 5°) during single-limb support in level walking"
                    ),
                    'knee_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(10), self._deg_to_rad(25), 45, 55,
                        "Knee flexed 10-25° for shock absorption during level walking mid-stance"
                    ),
                    'ankle_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(5), self._deg_to_rad(15), 45, 55,
                        "Ankle dorsiflexed 5-15° for forward progression during level walking mid-stance"
                    ),
                    'hip_adduction_angle_rad': PhaseRange(
                        self._deg_to_rad(-8), self._deg_to_rad(8), 45, 55,
                        "Hip adduction minimal (-8 to 8°) for efficient weight transfer during level walking"
                    ),
                }
            },
            
            # INCLINE WALKING - Walking uphill on slopes (5-15° inclines)
            'incline_walking': {
                'heel_strike': {
                    'hip_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(20), self._deg_to_rad(35), 0, 10,
                        "Hip flexed 20-35° for toe clearance and stride length on incline walking heel strike"
                    ),
                    'knee_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(0), self._deg_to_rad(10), 0, 10,
                        "Knee slightly flexed 0-10° for controlled impact on incline walking initial contact"
                    ),
                    'ankle_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(-10), self._deg_to_rad(5), 0, 10,
                        "Ankle plantarflexed to neutral (-10 to 5°) for incline surface contact"
                    ),
                    'hip_adduction_angle_rad': PhaseRange(
                        self._deg_to_rad(-12), self._deg_to_rad(12), 0, 10,
                        "Hip adduction controlled (-12 to 12°) for lateral stability on inclined terrain"
                    ),
                },
                'mid_stance': {
                    'hip_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(5), self._deg_to_rad(20), 45, 55,
                        "Hip maintained in flexion 5-20° for incline propulsion during mid-stance"
                    ),
                    'knee_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(15), self._deg_to_rad(30), 45, 55,
                        "Knee flexed 15-30° for enhanced shock absorption on incline walking"
                    ),
                    'ankle_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(10), self._deg_to_rad(25), 45, 55,
                        "Ankle dorsiflexed 10-25° for forward progression against gravity on inclines"
                    ),
                    'hip_adduction_angle_rad': PhaseRange(
                        self._deg_to_rad(-10), self._deg_to_rad(10), 45, 55,
                        "Hip adduction controlled (-10 to 10°) for stability during incline weight acceptance"
                    ),
                }
            },
            
            # DECLINE WALKING - Walking downhill on slopes (5-15° declines)
            'decline_walking': {
                'heel_strike': {
                    'hip_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(10), self._deg_to_rad(20), 0, 10,
                        "Hip flexed 10-20° for controlled descent positioning during decline walking heel strike"
                    ),
                    'knee_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(5), self._deg_to_rad(15), 0, 10,
                        "Knee slightly flexed 5-15° for impact preparation during decline walking initial contact"
                    ),
                    'ankle_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(-15), self._deg_to_rad(0), 0, 10,
                        "Ankle plantarflexed (-15 to 0°) for safe decline surface contact"
                    ),
                    'hip_adduction_angle_rad': PhaseRange(
                        self._deg_to_rad(-12), self._deg_to_rad(12), 0, 10,
                        "Hip adduction controlled (-12 to 12°) for lateral stability during decline walking"
                    ),
                },
                'mid_stance': {
                    'hip_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(-10), self._deg_to_rad(5), 45, 55,
                        "Hip extended (-10 to 5°) for controlled descent and braking during decline walking"
                    ),
                    'knee_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(20), self._deg_to_rad(40), 45, 55,
                        "Knee flexed 20-40° for eccentric control and shock absorption during decline walking"
                    ),
                    'ankle_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(0), self._deg_to_rad(10), 45, 55,
                        "Ankle dorsiflexed 0-10° for stability and forward control during decline stance"
                    ),
                    'hip_adduction_angle_rad': PhaseRange(
                        self._deg_to_rad(-10), self._deg_to_rad(10), 45, 55,
                        "Hip adduction controlled (-10 to 10°) for balance during decline weight bearing"
                    ),
                }
            },
            
            # STAIR ASCENT
            'up_stairs': {
                'heel_strike': {
                    'hip_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(35), self._deg_to_rad(50), 0, 10,
                        "High hip flexion for stair clearance"
                    ),
                    'knee_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(60), self._deg_to_rad(80), 0, 10,
                        "High knee flexion for step clearance"
                    ),
                    'ankle_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(5), self._deg_to_rad(15), 0, 10,
                        "Ankle dorsiflexed for step contact"
                    ),
                },
                'mid_stance': {
                    'hip_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(20), self._deg_to_rad(35), 45, 55,
                        "Hip flexed during stair loading"
                    ),
                    'knee_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(40), self._deg_to_rad(70), 45, 55,
                        "Knee highly flexed during stair push-off"
                    ),
                    'ankle_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(10), self._deg_to_rad(25), 45, 55,
                        "Ankle dorsiflexed for stair propulsion"
                    ),
                }
            },
            
            # STAIR DESCENT
            'down_stairs': {
                'heel_strike': {
                    'hip_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(15), self._deg_to_rad(30), 0, 10,
                        "Moderate hip flexion for stair descent"
                    ),
                    'knee_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(10), self._deg_to_rad(25), 0, 10,
                        "Knee prepared for impact control"
                    ),
                    'ankle_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(-10), self._deg_to_rad(5), 0, 10,
                        "Ankle positioned for step contact"
                    ),
                },
                'mid_stance': {
                    'hip_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(0), self._deg_to_rad(15), 45, 55,
                        "Hip control during stair descent"
                    ),
                    'knee_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(30), self._deg_to_rad(60), 45, 55,
                        "High knee flexion for controlled descent"
                    ),
                    'ankle_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(-5), self._deg_to_rad(10), 45, 55,
                        "Ankle control for stair stability"
                    ),
                }
            },
            
            # RUNNING - Higher velocities and forces
            'run': {
                'heel_strike': {
                    'hip_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(25), self._deg_to_rad(40), 0, 10,
                        "Increased hip flexion for running stride"
                    ),
                    'knee_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(5), self._deg_to_rad(20), 0, 10,
                        "Knee slightly flexed for running impact"
                    ),
                    'ankle_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(-5), self._deg_to_rad(10), 0, 10,
                        "Ankle prepared for running contact"
                    ),
                },
                'mid_stance': {
                    'hip_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(10), self._deg_to_rad(25), 45, 55,
                        "Hip extended for running propulsion"
                    ),
                    'knee_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(20), self._deg_to_rad(45), 45, 55,
                        "Knee flexion for running shock absorption"
                    ),
                    'ankle_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(10), self._deg_to_rad(25), 45, 55,
                        "Ankle dorsiflexion during running stance"
                    ),
                }
            },
            
            # SIT TO STAND
            'sit_to_stand': {
                'heel_strike': {  # Initial position
                    'hip_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(80), self._deg_to_rad(110), 0, 10,
                        "Hip highly flexed in sitting position"
                    ),
                    'knee_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(80), self._deg_to_rad(110), 0, 10,
                        "Knee highly flexed in sitting position"
                    ),
                    'ankle_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(-10), self._deg_to_rad(10), 0, 10,
                        "Ankle near neutral when seated"
                    ),
                },
                'mid_stance': {  # Standing position
                    'hip_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(-5), self._deg_to_rad(15), 45, 55,
                        "Hip approaching neutral when standing"
                    ),
                    'knee_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(-5), self._deg_to_rad(15), 45, 55,
                        "Knee extending toward neutral"
                    ),
                    'ankle_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(-5), self._deg_to_rad(10), 45, 55,
                        "Ankle stable during standing transition"
                    ),
                }
            },
            
            # SQUATS
            'squats': {
                'heel_strike': {  # Starting position
                    'hip_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(-5), self._deg_to_rad(10), 0, 10,
                        "Hip near neutral at squat start"
                    ),
                    'knee_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(-5), self._deg_to_rad(10), 0, 10,
                        "Knee near neutral at squat start"
                    ),
                    'ankle_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(-5), self._deg_to_rad(10), 0, 10,
                        "Ankle stable at squat start"
                    ),
                },
                'mid_stance': {  # Deep squat position
                    'hip_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(60), self._deg_to_rad(90), 45, 55,
                        "Hip highly flexed in deep squat"
                    ),
                    'knee_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(90), self._deg_to_rad(130), 45, 55,
                        "Knee highly flexed in deep squat"
                    ),
                    'ankle_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(15), self._deg_to_rad(35), 45, 55,
                        "Ankle dorsiflexed for squat depth"
                    ),
                }
            },
            
            # JUMP
            'jump': {
                'heel_strike': {  # Preparation phase
                    'hip_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(20), self._deg_to_rad(40), 0, 10,
                        "Hip flexed for jump preparation"
                    ),
                    'knee_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(30), self._deg_to_rad(60), 0, 10,
                        "Knee flexed for jump loading"
                    ),
                    'ankle_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(5), self._deg_to_rad(20), 0, 10,
                        "Ankle dorsiflexed for jump preparation"
                    ),
                },
                'mid_stance': {  # Take-off phase
                    'hip_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(-10), self._deg_to_rad(10), 45, 55,
                        "Hip extending for jump propulsion"
                    ),
                    'knee_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(-10), self._deg_to_rad(15), 45, 55,
                        "Knee extending for jump take-off"
                    ),
                    'ankle_flexion_angle_rad': PhaseRange(
                        self._deg_to_rad(-20), self._deg_to_rad(0), 45, 55,
                        "Ankle plantarflexing for jump propulsion"
                    ),
                }
            }
        }
        
        # Define which tasks are cyclic (have meaningful phase-based analysis)
        self.cyclic_tasks = {
            'level_walking', 'incline_walking', 'decline_walking', 'run',
            'up_stairs', 'down_stairs', 'sit_to_stand', 'squats', 'jump'
        }
        
        # Initialize error tracking table
        self.error_table = pd.DataFrame(columns=[
            'task_name', 'joint', 'phase', 'error_type', 'count', 'severity_avg'
        ])
    
    def validate(self) -> pd.DataFrame:
        """
        Run intuitive biomechanical validation only on cyclic tasks.
        
        Returns:
            DataFrame with added validation columns
        """
        if 'phase_%' not in self.df.columns:
            raise ValueError("DataFrame must contain 'phase_%' column for phase-based validation")
        
        if 'task_name' not in self.df.columns:
            raise ValueError("DataFrame must contain 'task_name' column")
        
        # Only validate cyclic tasks that have meaningful phase relationships
        for task_name, group in self.df.groupby('task_name'):
            if task_name in self.cyclic_tasks:
                self._validate_task_group(task_name, group)
            else:
                print(f"Skipping non-cyclic task: {task_name}")
        
        # Validate velocities using phase derivatives (only for cyclic tasks)
        self._validate_velocities()
        
        # Generate error table summary
        self._generate_error_table()
        
        return self.df
    
    def _validate_task_group(self, task_name: str, group: pd.DataFrame):
        """Validate a specific task group"""
        if task_name not in self.expectations:
            # Skip validation for unknown tasks
            return
        
        task_expectations = self.expectations[task_name]
        
        # Validate heel strike phase (0-10%)
        if 'heel_strike' in task_expectations:
            self._validate_phase_window(group, task_expectations['heel_strike'], 'heel_strike')
        
        # Validate mid-stance phase (45-55%)
        if 'mid_stance' in task_expectations:
            self._validate_phase_window(group, task_expectations['mid_stance'], 'mid_stance')
    
    def _validate_phase_window(self, group: pd.DataFrame, expectations: Dict, phase_name: str):
        """Validate joint angles within a specific phase window"""
        for joint, expected_range in expectations.items():
            if joint in group.columns:
                # Find data points in the phase window
                phase_mask = (
                    (group['phase_%'] >= expected_range.phase_start) & 
                    (group['phase_%'] <= expected_range.phase_end)
                )
                
                if phase_mask.any():
                    joint_data = group.loc[phase_mask, joint]
                    
                    # Check if any values are outside expected range
                    out_of_range = (
                        (joint_data < expected_range.min_angle) | 
                        (joint_data > expected_range.max_angle)
                    )
                    
                    if out_of_range.any():
                        # Mark rows as invalid and record error
                        invalid_indices = group.index[phase_mask][out_of_range]
                        
                        for idx in invalid_indices:
                            self.df.at[idx, 'validation_intuitive'] = False
                            actual_value = joint_data.loc[out_of_range].iloc[0]
                            
                            error_msg = (
                                f"{joint} out of expected range during {phase_name}: "
                                f"{actual_value:.3f} rad "
                                f"(expected {expected_range.min_angle:.3f} to {expected_range.max_angle:.3f})"
                            )
                            self.df.at[idx, 'intuitive_errors'].append(error_msg)
                            
                            # Store for aggregate reporting
                            self.validation_results[f"{joint}_{phase_name}"].append({
                                'task': group.at[idx, 'task_name'],
                                'subject': group.at[idx, 'subject_id'] if 'subject_id' in group.columns else 'Unknown',
                                'phase': group.at[idx, 'phase_%'],
                                'actual_value': actual_value,
                                'expected_min': expected_range.min_angle,
                                'expected_max': expected_range.max_angle,
                                'description': expected_range.description
                            })
                            
                            # Store detailed step-level error for debugging
                            step_id = f"{group.at[idx, 'subject_id'] if 'subject_id' in group.columns else 'Unknown'}_{group.at[idx, 'task_name']}_{group.at[idx, 'phase_%']:.1f}"
                            
                            self.step_errors.append({
                                'step_id': step_id,
                                'subject_id': group.at[idx, 'subject_id'] if 'subject_id' in group.columns else 'Unknown',
                                'task_name': group.at[idx, 'task_name'],
                                'phase_percent': group.at[idx, 'phase_%'],
                                'joint': joint,
                                'phase_window': phase_name,
                                'actual_value_rad': actual_value,
                                'actual_value_deg': np.degrees(actual_value),
                                'expected_min_rad': expected_range.min_angle,
                                'expected_max_rad': expected_range.max_angle,
                                'expected_min_deg': np.degrees(expected_range.min_angle),
                                'expected_max_deg': np.degrees(expected_range.max_angle),
                                'deviation_deg': min(abs(np.degrees(actual_value) - np.degrees(expected_range.min_angle)),
                                                   abs(np.degrees(actual_value) - np.degrees(expected_range.max_angle))),
                                'severity': self._assess_severity({'actual_value': actual_value, 
                                                                'expected_min': expected_range.min_angle,
                                                                'expected_max': expected_range.max_angle}),
                                'clinical_description': expected_range.description,
                                'error_type': 'angle_out_of_range',
                                'fix_suggestion': self._generate_fix_suggestion(joint, phase_name, actual_value, expected_range)
                            })
    
    def _validate_velocities(self):
        """
        Validate angular velocities by computing d(angle)/d(phase)
        and checking for appropriate sign changes during movement cycles.
        Only validates cyclic tasks.
        """
        velocity_cols = [col for col in self.df.columns if col.endswith('_velocity_rad_s')]
        
        for vel_col in velocity_cols:
            # Find corresponding angle column
            angle_col = vel_col.replace('_velocity_rad_s', '_angle_rad')
            
            if angle_col in self.df.columns:
                # Group by subject and task for continuous phase progression
                for (subject, task), group in self.df.groupby(['subject_id', 'task_name']):
                    # Only validate cyclic tasks
                    if task not in self.cyclic_tasks:
                        continue
                        
                    if len(group) < 3:  # Need at least 3 points for derivative
                        continue
                    
                    # Sort by phase for proper derivative calculation
                    group_sorted = group.sort_values('phase_%')
                    
                    # Calculate phase derivative (d_angle/d_phase)
                    phase_diff = np.diff(group_sorted['phase_%'])
                    angle_diff = np.diff(group_sorted[angle_col])
                    
                    # Avoid division by zero
                    valid_diff = phase_diff != 0
                    if not valid_diff.any():
                        continue
                    
                    phase_velocity = np.zeros_like(angle_diff)
                    phase_velocity[valid_diff] = angle_diff[valid_diff] / phase_diff[valid_diff]
                    
                    # Check if phase velocity and measured velocity have consistent signs
                    measured_vel = group_sorted[vel_col].iloc[1:].values  # Skip first point
                    
                    # Allow for some tolerance in sign comparison
                    sign_inconsistency = (
                        (phase_velocity > 0.01) & (measured_vel < -0.01) |
                        (phase_velocity < -0.01) & (measured_vel > 0.01)
                    )
                    
                    if sign_inconsistency.any():
                        # Mark inconsistent velocities
                        inconsistent_indices = group_sorted.index[1:][sign_inconsistency]
                        
                        for idx in inconsistent_indices:
                            self.df.at[idx, 'validation_intuitive'] = False
                            error_msg = (
                                f"Velocity sign inconsistency for {vel_col}: "
                                f"measured={measured_vel[sign_inconsistency][0]:.3f}, "
                                f"phase_derivative={phase_velocity[sign_inconsistency][0]:.3f}"
                            )
                            self.df.at[idx, 'intuitive_errors'].append(error_msg)
    
    def _generate_error_table(self):
        """
        Generate comprehensive error tracking table showing which task and 
        measurement combinations have validation failures.
        """
        error_records = []
        
        # Process validation results to create error summary
        for error_type, failures in self.validation_results.items():
            # Parse error type to extract joint and phase
            if '_' in error_type:
                joint, phase = error_type.rsplit('_', 1)
            else:
                joint, phase = error_type, 'unknown'
            
            # Group failures by task
            task_failures = defaultdict(list)
            for failure in failures:
                task_failures[failure['task']].append(failure)
            
            # Create error record for each task
            for task, task_failures_list in task_failures.items():
                count = len(task_failures_list)
                severities = [self._assess_severity(f) for f in task_failures_list]
                severity_scores = {'Mild': 1, 'Moderate': 2, 'Severe': 3}
                avg_severity = np.mean([severity_scores[s] for s in severities])
                
                error_records.append({
                    'task_name': task,
                    'joint': joint,
                    'phase': phase,
                    'error_type': 'angle_out_of_range',
                    'count': count,
                    'severity_avg': avg_severity,
                    'severity_distribution': f"Mild:{severities.count('Mild')}, "
                                           f"Moderate:{severities.count('Moderate')}, "
                                           f"Severe:{severities.count('Severe')}"
                })
        
        # Add velocity validation errors
        velocity_errors = defaultdict(lambda: defaultdict(int))
        for idx, errors in enumerate(self.df['intuitive_errors']):
            if errors:  # Has validation errors
                task = self.df.iloc[idx]['task_name']
                for error in errors:
                    if 'Velocity sign inconsistency' in error:
                        joint = error.split(' for ')[1].split(':')[0].replace('_velocity_rad_s', '')
                        velocity_errors[task][joint] += 1
        
        # Add velocity errors to error records
        for task, joints in velocity_errors.items():
            for joint, count in joints.items():
                error_records.append({
                    'task_name': task,
                    'joint': joint,
                    'phase': 'all_phases',
                    'error_type': 'velocity_sign_inconsistency',
                    'count': count,
                    'severity_avg': 2.0,  # Moderate severity for velocity issues
                    'severity_distribution': f"Moderate:{count}"
                })
        
        if error_records:
            self.error_table = pd.DataFrame(error_records)
            # Sort by task, then by count (descending)
            self.error_table = self.error_table.sort_values(['task_name', 'count'], ascending=[True, False])
        else:
            self.error_table = pd.DataFrame(columns=[
                'task_name', 'joint', 'phase', 'error_type', 'count', 'severity_avg', 'severity_distribution'
            ])
    
    def get_error_table(self) -> pd.DataFrame:
        """
        Get the comprehensive error table showing failures by task and measurement.
        
        Returns:
            DataFrame with columns: task_name, joint, phase, error_type, count, severity_avg
        """
        return self.error_table.copy()
    
    def get_clinical_report(self) -> pd.DataFrame:
        """
        Generate a clinical interpretation report of validation results.
        
        Returns:
            DataFrame with human-readable validation summary
        """
        records = []
        
        for error_type, failures in self.validation_results.items():
            for failure in failures:
                records.append({
                    'joint_phase': error_type,
                    'task': failure['task'],
                    'subject': failure['subject'],
                    'phase_percent': failure['phase'],
                    'actual_angle_deg': np.degrees(failure['actual_value']),
                    'expected_min_deg': np.degrees(failure['expected_min']),
                    'expected_max_deg': np.degrees(failure['expected_max']),
                    'clinical_interpretation': failure['description'],
                    'severity': self._assess_severity(failure)
                })
        
        if records:
            report = pd.DataFrame(records)
            return report.sort_values(['joint_phase', 'task', 'subject'])
        else:
            return pd.DataFrame()
    
    def _assess_severity(self, failure: Dict) -> str:
        """Assess the clinical severity of a validation failure"""
        actual = failure['actual_value']
        min_expected = failure['expected_min']
        max_expected = failure['expected_max']
        
        # Calculate how far outside the range
        if actual < min_expected:
            deviation = abs(actual - min_expected)
        else:
            deviation = abs(actual - max_expected)
        
        # Convert to degrees for interpretation
        deviation_deg = np.degrees(deviation)
        
        if deviation_deg < 10:
            return "Mild"
        elif deviation_deg < 20:
            return "Moderate"
        else:
            return "Severe"
    
    def _generate_fix_suggestion(self, joint: str, phase_name: str, actual_value: float, expected_range: PhaseRange) -> str:
        """Generate specific fix suggestions for validation failures"""
        actual_deg = np.degrees(actual_value)
        min_deg = np.degrees(expected_range.min_angle)
        max_deg = np.degrees(expected_range.max_angle)
        
        if actual_value < expected_range.min_angle:
            # Too low (e.g., not enough flexion)
            if 'hip_flexion' in joint:
                return f"Increase hip flexion from {actual_deg:.1f}° to {min_deg:.1f}°+ during {phase_name}. Check hip flexor activation or measurement calibration."
            elif 'knee_flexion' in joint:
                return f"Increase knee flexion from {actual_deg:.1f}° to {min_deg:.1f}°+ during {phase_name}. Verify knee joint definition or check for hyperextension."
            elif 'ankle_flexion' in joint:
                return f"Increase ankle dorsiflexion from {actual_deg:.1f}° to {min_deg:.1f}°+ during {phase_name}. Check ankle joint calibration or foot contact definition."
            else:
                return f"Increase {joint} from {actual_deg:.1f}° to {min_deg:.1f}°+ during {phase_name}. Verify joint definition and measurement calibration."
        else:
            # Too high (e.g., too much flexion)
            if 'hip_flexion' in joint:
                return f"Reduce hip flexion from {actual_deg:.1f}° to {max_deg:.1f}°- during {phase_name}. Check for excessive forward lean or measurement offset."
            elif 'knee_flexion' in joint:
                return f"Reduce knee flexion from {actual_deg:.1f}° to {max_deg:.1f}°- during {phase_name}. Verify knee joint center or check for crouch pattern."
            elif 'ankle_flexion' in joint:
                return f"Reduce ankle dorsiflexion from {actual_deg:.1f}° to {max_deg:.1f}°- during {phase_name}. Check ankle joint axis or foot-ground contact."
            else:
                return f"Reduce {joint} from {actual_deg:.1f}° to {max_deg:.1f}°- during {phase_name}. Verify joint definition and check for measurement artifacts."
    
    def get_step_level_errors(self) -> pd.DataFrame:
        """
        Get detailed step-level error report for debugging specific data points.
        
        Returns:
            DataFrame with detailed information about each failing step
        """
        if self.step_errors:
            return pd.DataFrame(self.step_errors).sort_values(['subject_id', 'task_name', 'phase_percent'])
        else:
            return pd.DataFrame()
    
    def get_bug_fix_report(self) -> pd.DataFrame:
        """
        Generate a report specifically designed for debugging and fixing data issues.
        
        Returns:
            DataFrame with actionable debugging information
        """
        if not self.step_errors:
            return pd.DataFrame()
        
        df_errors = pd.DataFrame(self.step_errors)
        
        # Create debugging report with actionable information
        bug_report = df_errors.groupby(['subject_id', 'task_name', 'joint', 'phase_window']).agg({
            'step_id': 'count',
            'deviation_deg': ['mean', 'max'],
            'severity': lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else 'Unknown',
            'fix_suggestion': 'first',
            'clinical_description': 'first'
        }).round(2)
        
        # Flatten column names
        bug_report.columns = ['error_count', 'avg_deviation_deg', 'max_deviation_deg', 'typical_severity', 'fix_suggestion', 'clinical_description']
        bug_report = bug_report.reset_index()
        
        # Sort by severity and error count
        severity_order = {'Severe': 3, 'Moderate': 2, 'Mild': 1}
        bug_report['severity_score'] = bug_report['typical_severity'].map(severity_order)
        bug_report = bug_report.sort_values(['severity_score', 'error_count'], ascending=[False, False])
        bug_report = bug_report.drop('severity_score', axis=1)
        
        return bug_report
    
    def export_debugging_reports(self, base_filename: str):
        """
        Export comprehensive debugging reports for data fixing.
        
        Args:
            base_filename: Base name for output files (without extension)
        """
        # Export step-level errors
        step_errors_df = self.get_step_level_errors()
        if len(step_errors_df) > 0:
            step_file = f"{base_filename}_step_errors.csv"
            step_errors_df.to_csv(step_file, index=False)
            print(f"Step-level errors exported to {step_file}")
            
            # Export most problematic steps (top 50)
            top_errors_file = f"{base_filename}_top_errors.csv"
            top_errors = step_errors_df.nlargest(50, 'deviation_deg')
            top_errors.to_csv(top_errors_file, index=False)
            print(f"Top 50 problematic steps exported to {top_errors_file}")
        
        # Export bug fix report
        bug_report = self.get_bug_fix_report()
        if len(bug_report) > 0:
            bug_file = f"{base_filename}_bug_fix_guide.csv"
            bug_report.to_csv(bug_file, index=False)
            print(f"Bug fix guide exported to {bug_file}")
        
        # Export subject-specific summaries
        if len(step_errors_df) > 0:
            subject_summary = step_errors_df.groupby('subject_id').agg({
                'step_id': 'count',
                'task_name': 'nunique',
                'joint': 'nunique',
                'deviation_deg': 'mean',
                'severity': lambda x: (x == 'Severe').sum()
            }).round(2)
            subject_summary.columns = ['total_errors', 'tasks_with_errors', 'joints_with_errors', 'avg_deviation_deg', 'severe_errors']
            
            subject_file = f"{base_filename}_subject_summary.csv"
            subject_summary.to_csv(subject_file)
            print(f"Subject-specific summary exported to {subject_file}")
    
    def export_expectations_table(self, filename: str):
        """
        Export the complete expectations table in a human-readable format.
        
        Args:
            filename: CSV file to save the table
        """
        records = []
        
        for task, phases in self.expectations.items():
            for phase_name, joints in phases.items():
                for joint, expectation in joints.items():
                    records.append({
                        'task': task,
                        'phase': phase_name,
                        'phase_range': f"{expectation.phase_start}-{expectation.phase_end}%",
                        'joint': joint,
                        'min_angle_deg': round(np.degrees(expectation.min_angle), 1),
                        'max_angle_deg': round(np.degrees(expectation.max_angle), 1),
                        'clinical_description': expectation.description
                    })
        
        df_table = pd.DataFrame(records)
        df_table.to_csv(filename, index=False)
        print(f"Expectations table exported to {filename}")
        
        # Also create a summary table grouped by task
        summary_file = filename.replace('.csv', '_summary.csv')
        summary = df_table.groupby(['task', 'phase']).size().reset_index(name='num_joints')
        summary.to_csv(summary_file, index=False)
        print(f"Summary table exported to {summary_file}")


# Example usage and testing
if __name__ == '__main__':
    # Create sample data for testing
    np.random.seed(42)
    n_samples = 1000
    
    sample_data = {
        'subject_id': np.repeat(['S01', 'S02'], n_samples // 2),
        'task_name': np.repeat(['level_walking', 'incline_walking'], n_samples // 2),
        'phase_%': np.tile(np.linspace(0, 100, n_samples // 2), 2),
        'hip_flexion_angle_rad': np.random.normal(0.3, 0.1, n_samples),
        'knee_flexion_angle_rad': np.random.normal(1.0, 0.2, n_samples),
        'ankle_flexion_angle_rad': np.random.normal(0.1, 0.15, n_samples),
        'hip_flexion_velocity_rad_s': np.random.normal(0, 2, n_samples),
    }
    
    df_test = pd.DataFrame(sample_data)
    
    # Run validation
    validator = IntuitiveValidator(df_test)
    validated_df = validator.validate()
    
    # Generate reports
    clinical_report = validator.get_clinical_report()
    
    print("Validation Results:")
    print(f"Total rows: {len(validated_df)}")
    print(f"Valid rows: {validated_df['validation_intuitive'].sum()}")
    print(f"Invalid rows: {(~validated_df['validation_intuitive']).sum()}")
    
    if len(clinical_report) > 0:
        print("\nClinical Report Summary:")
        print(clinical_report.head(10))
    
    # Export expectations table
    validator.export_expectations_table("biomechanical_expectations.csv")