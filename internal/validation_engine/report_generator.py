#!/usr/bin/env python3
"""
Validation Report Generator

Generates markdown reports and coordinates plot generation for validation results.
Separated from core validation logic for better modularity.
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List

import sys
import numpy as np
import pandas as pd
sys.path.append(str(Path(__file__).parent.parent.parent))

# Avoid circular import - import only what's needed
from internal.plot_generation.filters_by_phase_plots import create_filters_by_phase_plot
from internal.plot_generation.step_classifier import StepClassifier
from user_libs.python.locomotion_data import LocomotionData


class ValidationReportGenerator:
    """
    Generates comprehensive validation reports with plots.
    
    Handles:
    - Markdown report generation
    - Plot coordination
    - Output directory management
    """
    
    def __init__(self, ranges_file: Optional[str] = None):
        """
        Initialize report generator.
        
        Args:
            ranges_file: Optional path to specific validation ranges YAML file
        """
        # Use fixed output directory
        project_root = Path(__file__).parent.parent.parent
        self.output_dir = project_root / "docs" / "reference" / "datasets_documentation" / "validation_reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.plots_dir = self.output_dir / "plots" 
        self.plots_dir.mkdir(exist_ok=True)
        
        # Import here to avoid circular dependency
        from internal.validation_engine.validator import Validator
        
        # Initialize validator with specific ranges file if provided
        if ranges_file:
            config_dir = Path(ranges_file).parent
            self.validator = Validator(config_dir)
            # Override the default config file
            self.validator.config_manager.consolidated_config = Path(ranges_file)
        else:
            self.validator = Validator()
        
        self.step_classifier = StepClassifier()
        
    def generate_report(self, dataset_path: str, generate_plots: bool = True) -> str:
        """
        Generate complete validation report with optional plots.
        
        Args:
            dataset_path: Path to dataset to validate
            generate_plots: Whether to generate validation plots
            
        Returns:
            Path to generated report
        """
        dataset_name = Path(dataset_path).stem
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Run validation
        validation_result = self.validator.validate(dataset_path)
        
        # Generate plots if requested
        plot_paths = {}
        if generate_plots:
            plot_paths = self._generate_plots(dataset_path, validation_result, timestamp)
        
        # Generate markdown report
        report_path = self._generate_markdown_report(
            dataset_name, 
            validation_result, 
            plot_paths, 
            timestamp,
            dataset_path
        )
        
        return str(report_path)
    
    def _generate_plots(self, dataset_path: str, validation_result: Dict, 
                       timestamp: str) -> Dict[str, str]:
        """Generate validation plots for the dataset."""
        plot_paths = {}
        
        # Load dataset for plotting with proper phase column name
        locomotion_data = LocomotionData(dataset_path, phase_col='phase_percent')
        data = locomotion_data.df
        tasks = locomotion_data.get_tasks()
        
        # Note: violations conversion removed as we now use failing_features directly
        
        # Generate plots for each task
        for task in tasks:
            # Define feature groupings for plotting
            kinematic_features = [
                'hip_flexion_angle_ipsi_rad', 'hip_flexion_angle_contra_rad',
                'knee_flexion_angle_ipsi_rad', 'knee_flexion_angle_contra_rad',
                'ankle_dorsiflexion_angle_ipsi_rad', 'ankle_dorsiflexion_angle_contra_rad'
            ]
            
            kinetic_features = [
                'hip_flexion_moment_ipsi_Nm', 'hip_flexion_moment_contra_Nm',
                'knee_flexion_moment_ipsi_Nm', 'knee_flexion_moment_contra_Nm',
                'ankle_dorsiflexion_moment_ipsi_Nm', 'ankle_dorsiflexion_moment_contra_Nm'
            ]
            
            segment_features = [
                'pelvis_sagittal_angle_rad', 'pelvis_frontal_angle_rad', 'pelvis_transverse_angle_rad',
                'trunk_sagittal_angle_rad', 'trunk_frontal_angle_rad', 'trunk_transverse_angle_rad',
                'thigh_sagittal_angle_ipsi_rad', 'thigh_sagittal_angle_contra_rad',
                'shank_sagittal_angle_ipsi_rad', 'shank_sagittal_angle_contra_rad',
                'foot_sagittal_angle_ipsi_rad', 'foot_sagittal_angle_contra_rad'
            ]
            
            # Collect all features we might need
            all_features = kinematic_features + kinetic_features + segment_features
            
            # Filter to only features that exist in the dataset
            available_features = [f for f in all_features if f in locomotion_data.features]
            
            # Single unified data load for all features
            all_data_3d, all_feature_names = locomotion_data.get_cycles(subject=None, task=task, features=available_features)
            
            # Get failing features for this task (unified validation)
            failing_features = self.validator._validate_task_with_failing_features(locomotion_data, task)
            
            # Get task data with generated contra features
            task_validation_data = self.validator.config_manager.get_task_data(task) if self.validator.config_manager.has_task(task) else {}
            
            # Generate plots for each feature type using consistent data
            
            # Filter kinematic features and data
            kinematic_available = [f for f in kinematic_features if f in all_feature_names]
            if kinematic_available and all_data_3d is not None:
                kinematic_indices = [all_feature_names.index(f) for f in kinematic_available]
                kinematic_data_3d = all_data_3d[:, :, kinematic_indices]
                
                kinematic_plot = create_filters_by_phase_plot(
                    validation_data={task: task_validation_data},
                    task_name=task,
                    output_dir=str(self.plots_dir),
                    mode='kinematic',
                    data=kinematic_data_3d,
                    failing_features=failing_features,
                    dataset_name=Path(dataset_path).stem,
                    timestamp=timestamp
                )
                plot_paths[f"{task}_kinematic"] = kinematic_plot
            
            # Filter kinetic features and data
            kinetic_available = [f for f in kinetic_features if f in all_feature_names]
            if kinetic_available and all_data_3d is not None:
                kinetic_indices = [all_feature_names.index(f) for f in kinetic_available]
                kinetic_data_3d = all_data_3d[:, :, kinetic_indices]
                
                kinetic_plot = create_filters_by_phase_plot(
                    validation_data={task: task_validation_data},
                    task_name=task,
                    output_dir=str(self.plots_dir),
                    mode='kinetic',
                    data=kinetic_data_3d,
                    failing_features=failing_features,
                    dataset_name=Path(dataset_path).stem,
                    timestamp=timestamp
                )
                plot_paths[f"{task}_kinetic"] = kinetic_plot
            
            # Filter segment features and data
            segment_available = [f for f in segment_features if f in all_feature_names]
            if segment_available and all_data_3d is not None:
                segment_indices = [all_feature_names.index(f) for f in segment_available]
                segment_data_3d = all_data_3d[:, :, segment_indices]
                
                segment_plot = create_filters_by_phase_plot(
                    validation_data={task: task_validation_data},
                    task_name=task,
                    output_dir=str(self.plots_dir),
                    mode='segment',
                    data=segment_data_3d,
                    failing_features=failing_features,
                    dataset_name=Path(dataset_path).stem,
                    timestamp=timestamp
                )
                plot_paths[f"{task}_segment"] = segment_plot
            else:
                # Generate empty segment plot if no data available
                segment_plot = create_filters_by_phase_plot(
                    validation_data={task: task_validation_data},
                    task_name=task,
                    output_dir=str(self.plots_dir),
                    mode='segment',
                    data=None,  # No data available
                    failing_features=failing_features,
                    dataset_name=Path(dataset_path).stem,
                    timestamp=timestamp
                )
                plot_paths[f"{task}_segment"] = segment_plot
        
        return plot_paths
    
    def _get_task_violations_by_variable(self, violations: Dict, task: str) -> Dict[str, List[int]]:
        """
        Extract violations for a specific task, organized by variable name.
        
        Args:
            violations: Full violations dictionary from validator
            task: Task name to filter for
            
        Returns:
            Dictionary mapping variable names to lists of step indices with violations
        """
        if task not in violations:
            return {}
        
        return violations[task]
    
    def _map_step_violations_to_cycles(self, step_violations: Dict[str, List[int]], 
                                      data: pd.DataFrame, task: str) -> Dict[str, List[int]]:
        """
        Map step numbers (trial IDs) to cycle indices in the 3D data array.
        
        Args:
            step_violations: Dict mapping variable names to lists of violated step numbers
            data: Full DataFrame with all data
            task: Task name to filter for
            
        Returns:
            Dictionary mapping variable names to lists of cycle indices with violations
        """
        cycle_violations = {}
        
        # Get task data
        task_data = data[data['task'] == task]
        
        # Build mapping of step numbers to cycle indices
        # First, get all unique combinations of subject and step
        step_cycle_map = {}
        cycle_idx = 0
        
        for subject in sorted(task_data['subject'].unique()):
            subject_data = task_data[task_data['subject'] == subject]
            for step in sorted(subject_data['step'].unique()):
                step_data = subject_data[subject_data['step'] == step]
                n_cycles = len(step_data) // 150  # 150 points per cycle
                
                if step not in step_cycle_map:
                    step_cycle_map[step] = []
                
                # Add all cycle indices for this step
                for i in range(n_cycles):
                    step_cycle_map[step].append(cycle_idx)
                    cycle_idx += 1
        
        # Now map violations from steps to cycles
        for var_name, violated_steps in step_violations.items():
            cycle_violations[var_name] = []
            for step in violated_steps:
                if step in step_cycle_map:
                    cycle_violations[var_name].extend(step_cycle_map[step])
        
        return cycle_violations
    
    def _violations_to_array(self, violations: Dict, data_shape: tuple) -> np.ndarray:
        """Convert violations dictionary to boolean array."""
        import numpy as np
        
        # Initialize array
        violation_array = np.zeros((data_shape[0], 12), dtype=bool)  # 12 standard variables
        
        # Map variable names to indices (standard ordering)
        variable_map = {
            'hip_flexion_angle_ipsi_rad': 0,
            'hip_flexion_angle_contra_rad': 1,
            'knee_flexion_angle_ipsi_rad': 2,
            'knee_flexion_angle_contra_rad': 3,
            'ankle_flexion_angle_ipsi_rad': 4,
            'ankle_flexion_angle_contra_rad': 5,
            'hip_flexion_moment_ipsi_Nm': 6,
            'hip_flexion_moment_contra_Nm': 7,
            'knee_flexion_moment_ipsi_Nm': 8,
            'knee_flexion_moment_contra_Nm': 9,
            'ankle_flexion_moment_ipsi_Nm': 10,
            'ankle_flexion_moment_contra_Nm': 11
        }
        
        # This is simplified - would need proper mapping
        for task, task_violations in violations.items():
            for var_name, step_indices in task_violations.items():
                var_idx = variable_map.get(var_name)
                if var_idx is not None:
                    for step_idx in step_indices:
                        if step_idx < violation_array.shape[0]:
                            violation_array[step_idx, var_idx] = True
        
        return violation_array
    
    def _generate_markdown_report(self, dataset_name: str, validation_result: Dict,
                                 plot_paths: Dict, timestamp: str, dataset_path: str) -> Path:
        """Generate markdown validation report."""
        report_name = f"{dataset_name}_validation_report.md"
        report_path = self.output_dir / report_name
        
        # Build report content
        lines = []
        lines.append(f"# Validation Report: {dataset_name}")
        lines.append(f"")
        lines.append(f"**Generated**: {timestamp}  ")
        
        # Status summary
        status = "✅ PASSED" if validation_result['passed'] else "❌ FAILED"
        lines.append(f"**Status**: {status} ({validation_result['stats']['pass_rate']:.1%} valid)  ")
        lines.append(f"")
        
        # Validation summary
        lines.append("## Summary")
        lines.append(f"- **Phase Structure**: {'✅ Valid' if validation_result['phase_valid'] else '❌ Invalid'}")
        lines.append(f"- **Tasks Validated**: {validation_result['stats']['num_tasks']}")
        lines.append(f"- **Total Checks**: {validation_result['stats']['total_checks']:,}")
        lines.append(f"- **Violations**: {validation_result['stats']['total_violations']:,}")
        lines.append("")
        
        # Plots section
        if plot_paths:
            lines.append("## Validation Plots")
            lines.append("")
            
            # Group plots by task
            tasks = set(key.rsplit('_', 1)[0] for key in plot_paths.keys())
            
            for task in sorted(tasks):
                lines.append(f"### {task.replace('_', ' ').title()}")
                lines.append("")
                
                # Kinematic plot
                kinematic_key = f"{task}_kinematic"
                if kinematic_key in plot_paths:
                    rel_path = Path(plot_paths[kinematic_key]).relative_to(self.output_dir)
                    lines.append(f"#### Kinematic Validation")
                    lines.append(f"![{task} Kinematic]({rel_path})")
                    lines.append("")
                
                # Kinetic plot  
                kinetic_key = f"{task}_kinetic"
                if kinetic_key in plot_paths:
                    rel_path = Path(plot_paths[kinetic_key]).relative_to(self.output_dir)
                    lines.append(f"#### Kinetic Validation")
                    lines.append(f"![{task} Kinetic]({rel_path})")
                    lines.append("")
                
                # Segment angle plot
                segment_key = f"{task}_segment"
                if segment_key in plot_paths:
                    rel_path = Path(plot_paths[segment_key]).relative_to(self.output_dir)
                    lines.append(f"#### Segment Angles Validation")
                    lines.append(f"![{task} Segment Angles]({rel_path})")
                    
                    # Check if segment angle data is actually available - define segment features here
                    segment_features = [
                        'pelvis_sagittal_angle_rad', 'pelvis_frontal_angle_rad', 'pelvis_transverse_angle_rad',
                        'trunk_sagittal_angle_rad', 'trunk_frontal_angle_rad', 'trunk_transverse_angle_rad',
                        'thigh_sagittal_angle_ipsi_rad', 'thigh_sagittal_angle_contra_rad',
                        'shank_sagittal_angle_ipsi_rad', 'shank_sagittal_angle_contra_rad',
                        'foot_sagittal_angle_ipsi_rad', 'foot_sagittal_angle_contra_rad'
                    ]
                    
                    # Get available features from the data
                    from user_libs.python.locomotion_data import LocomotionData
                    temp_loco = LocomotionData(dataset_path, phase_col='phase_percent')
                    segment_available = any(f in temp_loco.features for f in segment_features)
                    if not segment_available:
                        lines.append("*Note: Segment angle data not available in this dataset*")
                    lines.append("")
        
        
        # Write report
        with open(report_path, 'w') as f:
            f.write('\n'.join(lines))
        
        return report_path


