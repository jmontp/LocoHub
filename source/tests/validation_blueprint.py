import re
import numpy as np
import pandas as pd
import tkinter as tk
from tkinter import filedialog

class ValidationError(Exception):
    """Custom exception for validation failures."""
    pass

class BiomechanicsValidator:
    def __init__(self, df: pd.DataFrame,
                 subject_meta: pd.DataFrame = None,
                 task_meta: pd.DataFrame = None):
        """
        df: time- or phase-indexed dataframe with columns:
            ['subject_id','task_id','task_name','time_s','phase_%', ...features...]
        subject_meta: dataframe keyed by subject_id (e.g., body_mass)
        task_meta: dataframe keyed by task_id (e.g., walking_speed_m_s)
        """
        self.df = df
        self.subject_meta = subject_meta.set_index('subject_id') if subject_meta is not None else None
        self.task_meta = task_meta.set_index('task_id') if task_meta is not None else None
        self.failures = []

        # Controlled vocabulary for task_name
        self.allowed_tasks = {
            'level_walking','incline_walking','decline_walking','run',
            'up_stairs','down_stairs','sit_to_stand','stand_to_sit','poses',
            'lift_weight','push','jump','lunges','squats',
            'ball_toss_l','ball_toss_m','ball_toss_r','meander','cutting',
            'obstacle_walk','side_shuffle','curb_up','curb_down'
        }

        # --- Layer 0 global rules (regex -> lambda series -> bool) ---
        self.layer0_rules = {
            r'.*_angle_rad$': lambda s: s.abs().le(np.pi),
            r'.*_velocity_rad_s$': lambda s: np.isfinite(s),  # plus cycle_integral check if phase available
            r'.*_moment_Nm$': lambda s: s.abs().le(4),
            r'^vertical_grf_N$': lambda s: (s > 0).all() & (s.le(6 * self._get_BW(s.name)).all()),
            r'^ap_grf_N$': lambda s: (s.le(0).all() and s.abs().le(0.6 * self._get_BW(s.name)).all()),
            r'^ml_grf_N$': lambda s: (s.ge(0).all() and s.le(0.25 * self._get_BW(s.name)).all()),
            r'^cop_[xy]_m$': lambda s: s[self._in_stance(s.name)].notna().all(),
            r'^time_s$': lambda s: s.is_monotonic_increasing,
            r'^phase_%$': lambda s: s.between(0,100).all()
        }

        # --- Layer 1 baseline envelopes (feature -> (min, max)) ---
        self.baseline = {
            'hip_flexion_angle_rad': (0.30, 0.60),
            'knee_flexion_angle_rad': (0.95, 1.20),
            'ankle_flexion_angle_rad': (-0.30, 0.25),
            'vertical_grf_N': (0.7, 1.3),   # valley to peak (in BW units)
            'ap_grf_N': (-0.25, 0.25),
            'ml_grf_N': (0.0, 0.10),
            'cop_x_m': (0.75, 0.90),
            'cop_y_m': (0.0, 0.30),
            # … add the rest …
        }

        # --- Layer 2 task‐specific overrides ---
        self.overrides = {
            'incline_walking': {
                'hip_flexion_angle_rad': (0.35, 0.72),  # baseline + [0.05,0.12]
                'vertical_grf_N': (0, 1.5),
                # …
            },
            'run': {
                'vertical_grf_N': (2.0, 3.0),
                # …
            },
            # … all other tasks …
        }

    def _get_BW(self, feature_name):
        """Helper: look up subject body_mass × 9.81 for this feature's series."""
        # Placeholder: returns standard BW for normalization
        return 1 * 9.81

    def _in_stance(self, feature_name):
        """Boolean mask for stance: vertical_grf_N > 0.05*BW"""
        grf = self.df['vertical_grf_N']
        return grf > 0.05 * self._get_BW('vertical_grf_N')

    def validate(self):
        """Run all layers in sequence."""
        self.failures.clear()
        self.layer_prechecks()
        self.layer0()
        self.layer1_and_2()
        self.layer3()
        self.layer4()
        return self.failures

    # -------- Pre-checks: naming & vocabulary --------
    def layer_prechecks(self):
        # Required columns
        required = ['subject_id', 'task_id', 'task_name', 'time_s']
        for col in required:
            if col not in self.df.columns:
                self.failures.append(
                    ('Precheck', 'column_presence', f'Missing required column: {col}')
                )
        # Column naming convention (snake_case + allowed chars)
        naming_re = re.compile(r'^[a-z][a-z0-9_%]*$')
        for col in self.df.columns:
            if not naming_re.match(col):
                self.failures.append(
                    ('Precheck', 'column_naming',
                     f'Invalid column name: "{col}" (must be snake_case, lowercase)')
                )
        # Task vocabulary
        if 'task_name' in self.df.columns:
            invalid = set(self.df['task_name'].unique()) - self.allowed_tasks
            if invalid:
                self.failures.append(
                    ('Precheck', 'task_vocab',
                     f'Invalid task_name(s): {sorted(invalid)}')
                )

    # -------- Layer 0 --------
    def layer0(self):
        df = self.df
        for pattern, check in self.layer0_rules.items():
            regex = re.compile(pattern)
            for col in df.columns:
                if regex.match(col):
                    series = df[col]
                    if not check(series):
                        self.failures.append(
                            ('Layer0', col,
                             f'Global sanity check failed for {col} (pattern: {pattern})')
                        )

    # -------- Layers 1 & 2 --------
    def layer1_and_2(self):
        df = self.df
        for task, task_df in df.groupby('task_name'):
            rules = self.baseline.copy()
            if task in self.overrides:
                rules.update(self.overrides[task])
            for feature, (mn, mx) in rules.items():
                if feature in task_df:
                    data = task_df[feature]
                    # Normalize GRFs to BW units
                    if feature.endswith('_N'):
                        data = data / self._get_BW(feature)
                    if not data.between(mn, mx).all():
                        self.failures.append(
                            ('Layer1/2', feature,
                             f'{task}: {feature} outside [{mn}, {mx}]')
                        )

    # -------- Layer 3 --------
    def layer3(self):
        df = self.df
        # Example check: moment × velocity → power sign consistency
        m_col = 'hip_flexion_moment_Nm'
        v_col = 'hip_flexion_velocity_rad_s'
        if m_col in df and v_col in df:
            power = df[m_col] * df[v_col]
            if power.sign().mean() < 0.1:
                self.failures.append(
                    ('Layer3', 'hip_power_sign',
                     'Inconsistent hip joint power sign')
                )
        # Additional physics-based checks go here...

    # -------- Layer 4 --------
    def layer4(self):
        # Neutral-pose anchoring
        stance = (self.df['vertical_grf_N'] > 0.9 * self._get_BW('vertical_grf_N')) & \
                 (self.df['knee_flexion_velocity_rad_s'].abs() < 0.1)
        for joint in ['hip_flexion_angle_rad', 'knee_flexion_angle_rad', 'ankle_flexion_angle_rad']:
            if joint in self.df:
                mean_angle = self.df.loc[stance, joint].mean()
                if abs(mean_angle) > 0.05:
                    self.failures.append(
                        ('Layer4', joint,
                         f'Neutral-pose mean for {joint} = {mean_angle:.3f} rad (>0.05)')
                    )

# ----------------------
# File selection dialog & example usage:
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
    failures = validator.validate()
    if failures:
        for layer, feature, msg in failures:
            print(f'[{layer}] {feature}: {msg}')
        raise ValidationError(f'Validation failed with {len(failures)} errors')
    else:
        print('✅ All checks passed!')