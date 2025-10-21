#!/usr/bin/env python3
"""Quick script to show validation plot for a specific task"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from internal.validation_engine.validator import Validator
from internal.validation_engine.report_generator import ValidationReportGenerator
from internal.plot_generation.filters_by_phase_plots import create_task_combined_plot
from locohub import LocomotionData
import matplotlib.pyplot as plt

# Configure matplotlib for better scrolling
plt.rcParams['figure.max_open_warning'] = 0
plt.rcParams['toolbar'] = 'toolbar2'

# Configuration
dataset_path = "converted_datasets/gtech_2021_phase.parquet"
task_to_show = "stair_ascent"
ranges_file = "contributor_tools/validation_ranges/default_ranges.yaml"

print(f"Loading dataset and generating plot for {task_to_show}...")

# Initialize components
validator = Validator(config_path=ranges_file)
locomotion_data = LocomotionData(dataset_path, phase_col='phase_ipsi')

# Get task data
data_3d, feature_names = locomotion_data.get_cycles(None, task_to_show)

# Get validation data
task_validation_data = validator.config_manager.get_task_data(task_to_show) if validator.config_manager.has_task(task_to_show) else {}

# Get failing features
failing_features = validator._validate_task_with_failing_features(locomotion_data, task_to_show)

print(f"Found {len(failing_features)} failing strides for {task_to_show}")
print(f"Data shape: {data_3d.shape} (strides, phases, features)")

# Generate the plot interactively
plot_path = create_task_combined_plot(
    validation_data=task_validation_data,
    task_name=task_to_show,
    output_dir=".",  # Not used when show_interactive=True
    data_3d=data_3d,
    feature_names=feature_names,
    failing_features=failing_features,
    dataset_name="gtech_2021_phase",
    timestamp="interactive",
    show_interactive=True,
    show_local_passing=True  # Enable locally passing strides
)

# Configure the plot window for better navigation  
try:
    fig = plt.gcf()
    fig.canvas.manager.set_window_title(f"Validation Plot: {task_to_show}")
except:
    pass  # Some backends don't support window title setting

print(f"Plot displayed for {task_to_show}")
print("Use the matplotlib toolbar to:")
print("  - 🔍 Zoom: Click zoom tool, then drag to select area")
print("  - 👆 Pan: Click pan tool, then drag to move around")
print("  - 🏠 Home: Reset view to original")
print("  - ↩️ Back/Forward: Navigate zoom history")
