"""
BiomechanicsValidator Module

This module provides a comprehensive data validator for locomotion datasets.

Usage:
    1. Run this script directly to launch file dialogs and select your Parquet files.
    2. Import `BiomechanicsValidator` in your code:

        from biomechanics_validator import BiomechanicsValidator, select_file
        import pandas as pd

        # Select files interactively or provide paths directly
        data_path = select_file('Select dataset Parquet file')
        subj_path = select_file('Select subject metadata file (or cancel)')
        task_path = select_file('Select task metadata file (or cancel)')

        df = pd.read_parquet(data_path)
        subj_meta = pd.read_parquet(subj_path) if subj_path else None
        task_meta = pd.read_parquet(task_path) if task_path else None

        validator = BiomechanicsValidator(df, subject_meta=subj_meta, task_meta=task_meta)
        annotated_df = validator.validate()

        # `annotated_df['valid_step']` indicates validation status per row:
        #    0 = valid; 1 = precheck failures; 10 = layer0; 20 = layer1/2; 30 = layer3; 40 = layer4
        print(annotated_df['valid_step'].value_counts())

Methods:
    - validate(): Run all layers and return annotated DataFrame.
    - select_file(prompt): Open a file dialog to pick Parquet files.

"""
import re
import numpy as np
import pandas as pd
import tkinter as tk
from tkinter import filedialog

class BiomechanicsValidator:
    def __init__(self, df: pd.DataFrame,
                 subject_meta: pd.DataFrame = None,
                 task_meta: pd.DataFrame = None):
        """
        df: time- or phase-indexed DataFrame with columns:
            ['subject_id','task_id','task_name','time_s','phase_%', ...features...]
        subject_meta: DataFrame keyed by subject_id (e.g., body_mass)
        task_meta: DataFrame keyed by task_id (e.g., walking_speed_m_s)
        """
        self.df = df.copy()
        # 0 = valid, >0 indicates failure code by layer
        self.df['valid_step'] = 0
        self.subject_meta = subject_meta.set_index('subject_id') if subject_meta is not None else None
        self.task_meta = task_meta.set_index('task_id') if task_meta is not None else None

        # Controlled vocabulary for task_name
        self.allowed_tasks = {
            'level_walking','incline_walking','decline_walking','run',
            'up_stairs','down_stairs','sit_to_stand','stand_to_sit','poses',
            'lift_weight','push','jump','lunges','squats',
            'ball_toss_l','ball_toss_m','ball_toss_r','meander','cutting',
            'obstacle_walk','side_shuffle','curb_up','curb_down'
        }

        # Layer 0 global sanity rules: regex -> mask of invalid rows
        self.layer0_rules = {
            r'.*_angle_rad$':   lambda s: ~s.abs().le(np.pi),
            r'.*_velocity_rad_s$': lambda s: ~np.isfinite(s),
            r'.*_moment_Nm$':   lambda s: ~s.abs().le(4),
            r'^vertical_grf_N$': lambda s: ~((s > 0) & s.le(6 * self._get_BW())),
            r'^ap_grf_N$':      lambda s: ~((s <= 0) & s.abs().le(0.6 * self._get_BW())),
            r'^ml_grf_N$':      lambda s: ~((s >= 0) & s.le(0.25 * self._get_BW())),
            r'^cop_[xy]_m$':    lambda s: self.df.loc[self._in_stance(), s.name].isna(),
            r'^time_s$':        lambda s: ~s.is_monotonic_increasing,
            r'^phase_%$':       lambda s: ~s.between(0,100)
        }

        # Layer 1 baseline envelopes (min, max) for level_walking norms
        self.baseline = {
            # Joint angles
            'hip_flexion_angle_rad':      (0.30, 0.60),
            'hip_adduction_angle_rad':    (-0.20, 0.20),
            'hip_rotation_angle_rad':     (-0.15, 0.15),
            'knee_flexion_angle_rad':     (0.95, 1.20),
            'ankle_flexion_angle_rad':    (-0.30, 0.25),
            'ankle_inversion_angle_rad':  (0.10, 0.25),
            'ankle_rotation_angle_rad':   (-0.20, 0.20),
            # Angular velocities
            'hip_flexion_velocity_rad_s':     (-5.0, 5.0),
            'hip_adduction_velocity_rad_s':   (-5.0, 5.0),
            'hip_rotation_velocity_rad_s':    (-5.0, 5.0),
            'knee_flexion_velocity_rad_s':    (-5.0, 5.0),
            'ankle_flexion_velocity_rad_s':   (-5.0, 5.0),
            'ankle_inversion_velocity_rad_s': (-5.0, 5.0),
            'ankle_rotation_velocity_rad_s':  (-5.0, 5.0),
            # Joint moments (normalized by BW)
            'hip_moment_Nm':      (-2.0, 2.0),
            'knee_moment_Nm':     (-2.0, 2.0),
            'ankle_moment_Nm':     (-2.0, 2.0),
            # Global link angles
            'torso_angle_x_rad':  (-0.30, 0.30), 'torso_angle_y_rad': (-0.20,0.20), 'torso_angle_z_rad': (-0.30,0.30),
            'thigh_angle_x_rad':  (-0.30, 0.30), 'thigh_angle_y_rad': (-0.30,0.30), 'thigh_angle_z_rad': (-0.30,0.30),
            'shank_angle_x_rad':  (-0.30, 0.30), 'shank_angle_y_rad': (-0.30,0.30), 'shank_angle_z_rad': (-0.30,0.30),
            'foot_angle_x_rad':   (-0.30, 0.30), 'foot_angle_y_rad':  (-0.30,0.30), 'foot_angle_z_rad':  (-0.30,0.30),
            # Global link velocities
            'torso_velocity_x_rad_s': (-2.0,2.0), 'torso_velocity_y_rad_s':(-2.0,2.0), 'torso_velocity_z_rad_s':(-2.0,2.0),
            'thigh_velocity_x_rad_s': (-2.0,2.0), 'thigh_velocity_y_rad_s':(-2.0,2.0), 'thigh_velocity_z_rad_s':(-2.0,2.0),
            'shank_velocity_x_rad_s': (-2.0,2.0), 'shank_velocity_y_rad_s':(-2.0,2.0), 'shank_velocity_z_rad_s':(-2.0,2.0),
            'foot_velocity_x_rad_s':  (-2.0,2.0), 'foot_velocity_y_rad_s':(-2.0,2.0), 'foot_velocity_z_rad_s':(-2.0,2.0),
            # GRFs (normalized by BW)
            'vertical_grf_N':    (0.7, 1.3),
            'ap_grf_N':         (-0.25, 0.25),
            'ml_grf_N':         (0.0, 0.10),
            # COP
            'cop_x_m':          (0.75, 0.90),
            'cop_y_m':          (0.0, 0.30)
        }

        # Layer 2 task-specific overrides
        inf = float('inf')
        self.overrides = {
            'incline_walking': {
                'hip_flexion_angle_rad':    (0.35, 0.72),
                'knee_flexion_angle_rad':   (1.00, 1.20),
                'ankle_flexion_angle_rad':  (-0.40, -0.25),
                'knee_moment_Nm':           (0.60, inf),
                'vertical_grf_N':           (0.0, 1.5)
            },
            'decline_walking': {
                'knee_flexion_angle_rad':   (0.35, inf),
                'vertical_grf_N':           (0.0, 1.1),
                'ap_grf_N':                (-0.35, -0.25)
            },
            'run': {
                'vertical_grf_N':           (2.0, 3.0),
                'ap_grf_N':                (-0.40, -0.25),
                'hip_flexion_velocity_rad_s': (5.0, inf)
            },
            'up_stairs': {
                'hip_flexion_angle_rad':    (0.95, 1.25),
                'knee_flexion_angle_rad':   (1.50, 1.80),
                'ankle_moment_Nm':          (1.60, 2.20),
                'knee_moment_Nm':           (0.80, 1.20),
                'vertical_grf_N':           (1.30, 1.60)
            },
            'down_stairs': {
                'ankle_flexion_angle_rad':  (0.35, inf),
                'knee_moment_Nm':           (1.50, 2.30),
                'vertical_grf_N':           (1.40, 1.80)
            },
            'sit_to_stand': {
                'hip_flexion_angle_rad':    (1.20, inf),
                'knee_flexion_velocity_rad_s': (2.0, inf),
                'vertical_grf_N':           (1.40, 1.90)
            },
            'stand_to_sit': {
                'vertical_grf_N':           (0.0, 1.20)
            },
            'lift_weight': {
                'knee_moment_Nm':           (0.80, 1.40),
                'vertical_grf_N':           (1.50, 2.20)
            },
            'jump': {
                'vertical_grf_N':           (3.0, 6.0),
                'knee_flexion_angle_rad':   (0.80, 1.40),
                'ankle_flexion_velocity_rad_s': (6.0, inf),
                'cop_y_m':                 (0.0, 0.30)
            },
            'lunges': {
                'knee_flexion_angle_rad':   (1.80, 2.00),
                'hip_moment_Nm':            (1.00, inf)
            },
            'squats': {
                'knee_flexion_angle_rad':   (2.00, inf),
                'hip_rotation_angle_rad':  (-0.35, 0.35)
            },
            'side_shuffle': {
                'ml_grf_N':                (0.30, inf),
                'ankle_inversion_angle_rad': (-inf, 0.30)
            },
            'cutting': {
                'hip_adduction_angle_rad':  (0.30, inf),
                'knee_moment_Nm':           (-inf, 0.60)
            },
            # Other tasks use baseline
        }

    def _get_BW(self):
        """Return body weight (N) placeholder."""
        return 1 * 9.81

    def _in_stance(self):
        """Boolean mask for stance: vertical_grf_N > 0.05*BW."""
        return self.df['vertical_grf_N'] > 0.05 * self._get_BW()

    def validate(self):
        """Run all validation layers, annotate df['valid_step'], and return annotated df."""
        self.layer_prechecks()
        self.layer0()
        self.layer1_and_2()
        self.layer3()
        self.layer4()
        return self.df

    # -------- Pre-checks: naming & vocabulary --------
    def layer_prechecks(self):
        code = 1
        # Required columns
        for col in ['subject_id', 'task_id', 'task_name', 'time_s']:
            if col not in self.df.columns:
                self.df['valid_step'] = code
        # Column naming convention (snake_case, unit suffix)
        naming_re = re.compile(r'^[a-z0-9_]+(_[a-z0-9]+)?(_rad|_deg|_N|_m|_s|_kg|_Nm|_rad_s)?$')
        for col in self.df.columns:
            if not naming_re.match(col):
                self.df.loc[self.df['valid_step']==0, 'valid_step'] = code + 1
        # Task vocabulary
        if 'task_name' in self.df.columns:
            invalid = set(self.df['task_name'].unique()) - self.allowed_tasks
            if invalid:
                self.df.loc[self.df['valid_step']==0, 'valid_step'] = code + 2

    # -------- Layer 0: Global sanity --------
    def layer0(self):
        code = 10
        for pattern, mask_fn in self.layer0_rules.items():
            regex = re.compile(pattern)
            for col in self.df.columns:
                if regex.match(col):
                    mask = mask_fn(self.df[col])
                    self.df.loc[mask, 'valid_step'] = code

    # -------- Layers 1 & 2: Baseline & overrides --------
    def layer1_and_2(self):
        code = 20
        for task_name, group in self.df.groupby('task_name'):
            rules = self.baseline.copy()
            if task_name in self.overrides:
                rules.update(self.overrides[task_name])
            for feature, (mn, mx) in rules.items():
                if feature in self.df.columns:
                    data = group[feature]
                    # Normalize forces/moments by BW
                    if feature.endswith('_N') or feature.endswith('_Nm'):
                        data = data / self._get_BW()
                    mask = ~data.between(mn, mx)
                    idx = mask[mask].index
                    self.df.loc[idx, 'valid_step'] = code

    # -------- Layer 3: Cross-variable physics --------
    def layer3(self):
        code = 30
        # Moment × angular velocity → power sign consistency
        for m_col in self.df.columns:
            if m_col.endswith('_moment_Nm'):
                v_col = m_col.replace('_moment_Nm', '_velocity_rad_s')
                if v_col in self.df.columns:
                    power = self.df[m_col] * self.df[v_col]
                    # require both positive and negative phases
                    if not (power.gt(0).any() and power.lt(0).any()):
                        self.df.loc[:, 'valid_step'] = code

    # -------- Layer 4: Subject-level heuristics --------
    def layer4(self):
        code = 40
        # Neutral-pose anchoring: quiet stance
        stance = (self.df['vertical_grf_N'] > 0.9 * self._get_BW()) & \
                 (self.df.get('knee_flexion_velocity_rad_s', 0).abs() < 0.1)
        for joint in ['hip_flexion_angle_rad', 'knee_flexion_angle_rad', 'ankle_flexion_angle_rad']:
            if joint in self.df:
                mean_angle = self.df.loc[stance, joint].mean()
                if abs(mean_angle) > 0.05:
                    self.df.loc[stance, 'valid_step'] = code

# ----------------------
# File selection dialog & example usage
# ----------------------

def select_file(prompt: str) -> str:
    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilename(
        title=prompt,
        filetypes=[('Parquet Files', '*.parquet'), ('All Files', '*.*')]
    )

if __name__ == '__main__':
    data_path = select_file('Select dataset Parquet file')
    subj_path = select_file('Select subject metadata Parquet file (or cancel to skip)')
    task_path = select_file('Select task metadata Parquet file (or cancel to skip)')

    df = pd.read_parquet(data_path)
    subj_meta = pd.read_parquet(subj_path) if subj_path else None
    task_meta = pd.read_parquet(task_path) if task_path else None

    validator = BiomechanicsValidator(df, subject_meta=subj_meta, task_meta=task_meta)
    annotated_df = validator.validate()
    # Now annotated_df['valid_step'] shows 0 for valid rows, >0 for failures
    print(annotated_df['valid_step'].value_counts())
