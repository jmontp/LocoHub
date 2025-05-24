"""
Enhanced BiomechanicsValidator Module

This module provides a comprehensive data validator for locomotion datasets with
support for tracking multiple validation failures per step.

Key Features:
    - Quick mode: Stops at first failure (original behavior)
    - Comprehensive mode: Checks all validation rules and tracks all failures
    - Interpretable error codes with human-readable descriptions
    - Detailed validation reports

Usage:
    validator = BiomechanicsValidator(df, mode='comprehensive')
    annotated_df = validator.validate()
    
    # Get human-readable failure descriptions
    failure_report = validator.get_failure_report()
"""

import re
import numpy as np
import pandas as pd
from typing import Dict, List, Set, Tuple
from collections import defaultdict

class BiomechanicsValidator:
    
    # Error code definitions - each rule gets a unique code
    ERROR_CODES = {
        # Precheck errors (1-9)
        1: "Missing required column",
        2: "Invalid column naming convention", 
        3: "Invalid task name (not in controlled vocabulary)",
        
        # Layer 0: Global sanity (10-29)
        10: "Joint angle outside ±π radians",
        11: "Non-finite angular velocity",
        12: "Joint moment exceeds 4 Nm/kg",
        13: "Vertical GRF negative or exceeds 6×BW",
        14: "AP GRF positive or exceeds 0.6×BW",
        15: "ML GRF negative or exceeds 0.25×BW",
        16: "COP defined during swing phase",
        17: "Time not monotonically increasing",
        18: "Phase percentage outside 0-100%",
        
        # Layer 1/2: Baseline & task-specific (30-49)
        30: "Hip flexion angle outside normal range",
        31: "Hip adduction angle outside normal range",
        32: "Hip rotation angle outside normal range",
        33: "Knee flexion angle outside normal range",
        34: "Ankle flexion angle outside normal range",
        35: "Angular velocity outside normal range",
        36: "Joint moment outside normal range",
        37: "GRF outside normal range",
        38: "COP outside normal range",
        
        # Layer 3: Physics consistency (50-59)
        50: "Power sign inconsistency (moment × velocity)",
        51: "Missing positive power phase",
        52: "Missing negative power phase",
        
        # Layer 4: Subject heuristics (60-69)
        60: "Non-neutral joint angle during quiet stance",
    }
    
    def __init__(self, df: pd.DataFrame,
                 subject_meta: pd.DataFrame = None,
                 task_meta: pd.DataFrame = None,
                 mode: str = 'quick'):
        """
        Initialize validator.
        
        Args:
            df: Biomechanics DataFrame
            subject_meta: Subject metadata (optional)
            task_meta: Task metadata (optional)
            mode: 'quick' (stop on first failure) or 'comprehensive' (check all)
        """
        self.df = df.copy()
        self.mode = mode
        self.subject_meta = subject_meta.set_index('subject_id') if subject_meta is not None else None
        self.task_meta = task_meta.set_index('task_id') if task_meta is not None else None
        
        # Initialize validation columns
        if mode == 'quick':
            self.df['valid_step'] = 0  # Single code (backward compatible)
        else:
            self.df['validation_codes'] = [[] for _ in range(len(df))]  # List of codes
            self.df['is_valid'] = True  # Overall validity flag
        
        # Track detailed failures for reporting
        self.failure_details = defaultdict(list)
        
        # Controlled vocabulary
        self.allowed_tasks = {
            'level_walking','incline_walking','decline_walking','run',
            'up_stairs','down_stairs','sit_to_stand','stand_to_sit','poses',
            'lift_weight','push','jump','lunges','squats',
            'ball_toss_l','ball_toss_m','ball_toss_r','meander','cutting',
            'obstacle_walk','side_shuffle','curb_up','curb_down'
        }
        
        # Layer 0 rules with specific error codes
        self.layer0_rules = {
            (r'.*_angle_rad$', 10): lambda s: ~s.abs().le(np.pi),
            (r'.*_velocity_rad_s$', 11): lambda s: ~np.isfinite(s),
            (r'.*_moment_Nm$', 12): lambda s: ~s.abs().le(4),
            (r'^vertical_grf_N$', 13): lambda s: ~((s >= 0) & s.le(6 * self._get_BW())),
            (r'^ap_grf_N$', 14): lambda s: ~((s <= 0) & s.abs().le(0.6 * self._get_BW())),
            (r'^ml_grf_N$', 15): lambda s: ~((s >= 0) & s.le(0.25 * self._get_BW())),
            (r'^cop_[xy]_m$', 16): lambda s: self.df.loc[~self._in_stance(), s.name].notna(),
            (r'^time_s$', 17): lambda s: ~s.is_monotonic_increasing,
            (r'^phase_%$', 18): lambda s: ~s.between(0,100)
        }
        
        # Baseline envelopes (for level walking)
        self.baseline = {
            'hip_flexion_angle_rad': (0.30, 0.60),
            'hip_adduction_angle_rad': (-0.20, 0.20),
            'hip_rotation_angle_rad': (-0.15, 0.15),
            'knee_flexion_angle_rad': (0.95, 1.20),
            'ankle_flexion_angle_rad': (-0.30, 0.25),
            # ... (rest of baseline values)
        }
        
        # Task-specific overrides
        self.overrides = {
            'incline_walking': {
                'hip_flexion_angle_rad': (0.40, 0.70),
                'ankle_flexion_angle_rad': (-0.40, 0.30),
            },
            'run': {
                'knee_flexion_angle_rad': (1.40, 1.70),
                'vertical_grf_N': (2.0, 3.5),
            },
            # ... (rest of overrides)
        }
    
    def _get_BW(self):
        """Return body weight in Newtons."""
        # TODO: Use actual body mass from metadata if available
        return 70 * 9.81  # Default 70kg
    
    def _in_stance(self):
        """Boolean mask for stance phase."""
        return self.df['vertical_grf_N'] > 0.05 * self._get_BW()
    
    def _add_error(self, mask, error_code: int, details: str = ""):
        """Add error code to affected rows."""
        if self.mode == 'quick':
            # Quick mode: set first error and stop
            if self.df.loc[mask & (self.df['valid_step'] == 0), 'valid_step'].any():
                self.df.loc[mask & (self.df['valid_step'] == 0), 'valid_step'] = error_code
                return True  # Signal to stop
        else:
            # Comprehensive mode: add to list of errors
            for idx in self.df.index[mask]:
                if error_code not in self.df.at[idx, 'validation_codes']:
                    self.df.at[idx, 'validation_codes'].append(error_code)
                    self.df.at[idx, 'is_valid'] = False
                    
                    # Track details for reporting
                    self.failure_details[error_code].append({
                        'index': idx,
                        'subject_id': self.df.at[idx, 'subject_id'],
                        'task_name': self.df.at[idx, 'task_name'],
                        'details': details
                    })
        return False
    
    def validate(self):
        """Run all validation layers."""
        # Run each layer
        if self.layer_prechecks(): return self.df
        if self.layer0(): return self.df
        if self.layer1_and_2(): return self.df
        if self.layer3(): return self.df
        if self.layer4(): return self.df
        
        return self.df
    
    def layer_prechecks(self):
        """Check basic requirements."""
        # Check required columns
        for col in ['subject_id', 'task_id', 'task_name', 'time_s']:
            if col not in self.df.columns:
                if self._add_error(pd.Series([True]*len(self.df)), 1, f"Missing column: {col}"):
                    return True
        
        # Check column naming
        naming_re = re.compile(r'^[a-z0-9_]+(_[a-z0-9]+)?(_rad|_deg|_N|_m|_s|_kg|_Nm|_rad_s)?$')
        for col in self.df.columns:
            if not naming_re.match(col):
                if self._add_error(pd.Series([True]*len(self.df)), 2, f"Invalid column name: {col}"):
                    return True
        
        # Check task vocabulary
        if 'task_name' in self.df.columns:
            invalid_tasks = set(self.df['task_name'].unique()) - self.allowed_tasks
            if invalid_tasks:
                mask = self.df['task_name'].isin(invalid_tasks)
                if self._add_error(mask, 3, f"Invalid tasks: {invalid_tasks}"):
                    return True
        
        return False
    
    def layer0(self):
        """Global sanity checks."""
        for (pattern, code), check_fn in self.layer0_rules.items():
            regex = re.compile(pattern)
            for col in self.df.columns:
                if regex.match(col):
                    mask = check_fn(self.df[col])
                    if mask.any():
                        if self._add_error(mask, code, f"Column {col} failed check"):
                            return True
        return False
    
    def layer1_and_2(self):
        """Baseline and task-specific checks."""
        base_code = 30
        
        for task_name, group in self.df.groupby('task_name'):
            rules = self.baseline.copy()
            if task_name in self.overrides:
                rules.update(self.overrides[task_name])
            
            for i, (feature, (mn, mx)) in enumerate(rules.items()):
                if feature in self.df.columns:
                    data = group[feature]
                    
                    # Normalize if needed
                    if feature.endswith('_N') or feature.endswith('_Nm'):
                        data = data / self._get_BW()
                    
                    mask = ~data.between(mn, mx)
                    if mask.any():
                        error_code = base_code + (i % 10)  # Distribute codes
                        if self._add_error(group.index[mask], error_code, 
                                         f"{feature} outside range [{mn}, {mx}] for {task_name}"):
                            return True
        return False
    
    def layer3(self):
        """Cross-variable physics checks."""
        # Power consistency check
        for m_col in self.df.columns:
            if m_col.endswith('_moment_Nm'):
                v_col = m_col.replace('_moment_Nm', '_velocity_rad_s')
                if v_col in self.df.columns:
                    power = self.df[m_col] * self.df[v_col]
                    
                    # Check for missing power phases
                    if not power.gt(0).any():
                        if self._add_error(pd.Series([True]*len(self.df)), 51, 
                                         f"No positive power phase for {m_col}"):
                            return True
                    
                    if not power.lt(0).any():
                        if self._add_error(pd.Series([True]*len(self.df)), 52,
                                         f"No negative power phase for {m_col}"):
                            return True
        return False
    
    def layer4(self):
        """Subject-level heuristics."""
        # Quiet stance check
        stance_mask = (self.df['vertical_grf_N'] > 0.9 * self._get_BW()) & \
                      (self.df.get('knee_flexion_velocity_rad_s', 0).abs() < 0.1)
        
        for joint in ['hip_flexion_angle_rad', 'knee_flexion_angle_rad', 'ankle_flexion_angle_rad']:
            if joint in self.df.columns and stance_mask.any():
                mean_angle = self.df.loc[stance_mask, joint].mean()
                if abs(mean_angle) > 0.05:
                    if self._add_error(stance_mask, 60,
                                     f"{joint} non-neutral ({mean_angle:.3f} rad) during stance"):
                        return True
        return False
    
    def get_failure_report(self) -> pd.DataFrame:
        """Generate a detailed failure report."""
        if self.mode == 'quick':
            # Simple report for quick mode
            report = self.df.groupby('valid_step').size().reset_index(name='count')
            report['description'] = report['valid_step'].map(
                lambda x: self.ERROR_CODES.get(x, 'Valid') if x > 0 else 'Valid'
            )
            return report
        else:
            # Detailed report for comprehensive mode
            records = []
            for code, failures in self.failure_details.items():
                for failure in failures:
                    records.append({
                        'error_code': code,
                        'description': self.ERROR_CODES[code],
                        'subject_id': failure['subject_id'],
                        'task_name': failure['task_name'],
                        'count': 1,
                        'details': failure['details']
                    })
            
            if records:
                report = pd.DataFrame(records)
                # Aggregate by error type and subject/task
                summary = report.groupby(['error_code', 'description', 'subject_id', 'task_name']).size().reset_index(name='count')
                return summary
            else:
                return pd.DataFrame(columns=['error_code', 'description', 'count'])
    
    def export_validation_report(self, filename: str):
        """Export validation report to CSV."""
        report = self.get_failure_report()
        report.to_csv(filename, index=False)
        print(f"Validation report saved to {filename}")
        
        # Also save the annotated dataframe
        if self.mode == 'comprehensive':
            # Convert lists to strings for CSV export
            df_export = self.df.copy()
            df_export['validation_codes'] = df_export['validation_codes'].apply(
                lambda x: ','.join(map(str, x)) if x else ''
            )
            df_export.to_csv(filename.replace('.csv', '_annotated.csv'), index=False)


# Example usage
if __name__ == '__main__':
    import tkinter as tk
    from tkinter import filedialog
    
    def select_file(prompt: str) -> str:
        root = tk.Tk()
        root.withdraw()
        return filedialog.askopenfilename(
            title=prompt,
            filetypes=[('Parquet Files', '*.parquet'), ('All Files', '*.*')]
        )
    
    # Get mode from user
    mode = input("Select validation mode (quick/comprehensive) [comprehensive]: ").strip() or 'comprehensive'
    
    # Select files
    data_path = select_file('Select dataset Parquet file')
    if not data_path:
        print("No file selected.")
        exit()
    
    subj_path = select_file('Select subject metadata file (or cancel to skip)')
    task_path = select_file('Select task metadata file (or cancel to skip)')
    
    # Load data
    df = pd.read_parquet(data_path)
    subj_meta = pd.read_parquet(subj_path) if subj_path else None
    task_meta = pd.read_parquet(task_path) if task_path else None
    
    # Run validation
    print(f"\nRunning validation in {mode} mode...")
    validator = BiomechanicsValidator(df, subject_meta=subj_meta, task_meta=task_meta, mode=mode)
    annotated_df = validator.validate()
    
    # Show results
    if mode == 'quick':
        print("\nValidation results (quick mode):")
        print(annotated_df['valid_step'].value_counts().sort_index())
    else:
        print("\nValidation results (comprehensive mode):")
        print(f"Total rows: {len(annotated_df)}")
        print(f"Valid rows: {annotated_df['is_valid'].sum()}")
        print(f"Invalid rows: {(~annotated_df['is_valid']).sum()}")
        
        # Show failure report
        print("\nFailure summary:")
        report = validator.get_failure_report()
        print(report.head(20))
    
    # Export report
    export_path = input("\nEnter filename to export report (or press Enter to skip): ").strip()
    if export_path:
        validator.export_validation_report(export_path)