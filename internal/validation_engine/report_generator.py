#!/usr/bin/env python3
"""
Validation Report Generator

Generates markdown reports and coordinates plot generation for validation results.
Separated from core validation logic for better modularity.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

import sys
import numpy as np
import pandas as pd
sys.path.append(str(Path(__file__).parent.parent.parent))

# Avoid circular import - import only what's needed
from internal.plot_generation.filters_by_phase_plots_v2 import create_filters_by_phase_plot
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
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize report generator.
        
        Args:
            output_dir: Output directory for reports and plots
        """
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            # Default to user_guide documentation directory (where MkDocs on port 8001 serves from)
            project_root = Path(__file__).parent.parent.parent
            self.output_dir = project_root / "docs" / "user_guide" / "docs" / "reference" / "datasets_documentation" / "validation_reports"
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.plots_dir = self.output_dir / "plots"
        self.plots_dir.mkdir(exist_ok=True)
        
        # Import here to avoid circular dependency
        from internal.validation_engine.validator import Validator
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
            timestamp
        )
        
        return str(report_path)
    
    def _generate_plots(self, dataset_path: str, validation_result: Dict, 
                       timestamp: str) -> Dict[str, str]:
        """Generate validation plots for the dataset."""
        plot_paths = {}
        
        # Load dataset for plotting
        locomotion_data = LocomotionData(dataset_path)
        data = locomotion_data.df
        tasks = locomotion_data.get_tasks()
        
        # Convert violations to boolean array for step classification
        violations = self._violations_to_array(validation_result['violations'], data.shape)
        
        # Generate plots for each task
        for task in tasks:
            # Define feature ordering for kinematic and kinetic plots
            kinematic_features = [
                'hip_flexion_angle_ipsi_rad', 'hip_flexion_angle_contra_rad',
                'knee_flexion_angle_ipsi_rad', 'knee_flexion_angle_contra_rad',
                'ankle_flexion_angle_ipsi_rad', 'ankle_flexion_angle_contra_rad'
            ]
            
            kinetic_features = [
                'hip_flexion_moment_ipsi_Nm', 'hip_flexion_moment_contra_Nm',
                'knee_flexion_moment_ipsi_Nm', 'knee_flexion_moment_contra_Nm',
                'ankle_flexion_moment_ipsi_Nm', 'ankle_flexion_moment_contra_Nm'
            ]
            
            # Get 3D array data for all subjects for this task
            kinematic_data_3d, _ = locomotion_data.get_cycles(subject=None, task=task, features=kinematic_features)
            kinetic_data_3d, _ = locomotion_data.get_cycles(subject=None, task=task, features=kinetic_features)
            
            # Get failing features for this task (new stride-centric format)
            # This returns {stride_idx: [failed_variable_names]}
            failing_features = self.validator._validate_task_with_failing_features(locomotion_data, task)
            
            # Load and prepare kinematic validation data
            kinematic_ranges = self.validator.config_manager.load_validation_ranges('kinematic')
            if task in kinematic_ranges:
                kinematic_task_data = kinematic_ranges[task]
                # Apply contralateral offset for gait tasks
                from internal.validation_engine.validator import apply_contralateral_offset_kinematic
                kinematic_task_data = apply_contralateral_offset_kinematic(kinematic_task_data, task)
            else:
                kinematic_task_data = {}
            
            # Generate kinematic plot
            kinematic_plot = create_filters_by_phase_plot(
                validation_data={task: kinematic_task_data},
                task_name=task,
                output_dir=str(self.plots_dir),
                mode='kinematic',
                data=kinematic_data_3d,
                failing_features=failing_features,  # Use new format
                dataset_name=Path(dataset_path).stem,
                timestamp=timestamp
            )
            plot_paths[f"{task}_kinematic"] = kinematic_plot
            
            # Load and prepare kinetic validation data
            kinetic_ranges = self.validator.config_manager.load_validation_ranges('kinetic')
            if task in kinetic_ranges:
                kinetic_task_data = kinetic_ranges[task]
                # Apply contralateral offset for gait tasks
                from internal.validation_engine.validator import apply_contralateral_offset_kinetic
                kinetic_task_data = apply_contralateral_offset_kinetic(kinetic_task_data, task)
            else:
                kinetic_task_data = {}
            
            # Generate kinetic plot
            kinetic_plot = create_filters_by_phase_plot(
                validation_data={task: kinetic_task_data},
                task_name=task,
                output_dir=str(self.plots_dir),
                mode='kinetic',
                data=kinetic_data_3d,
                failing_features=failing_features,  # Use new format
                dataset_name=Path(dataset_path).stem,
                timestamp=timestamp
            )
            plot_paths[f"{task}_kinetic"] = kinetic_plot
        
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
                                 plot_paths: Dict, timestamp: str) -> Path:
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
        
        # Violations detail
        if validation_result['violations']:
            lines.append("## Violations Detail")
            lines.append("")
            
            for task, task_violations in validation_result['violations'].items():
                lines.append(f"### {task.replace('_', ' ').title()}")
                for var, steps in task_violations.items():
                    lines.append(f"- **{var}**: {len(steps)} violations")
                lines.append("")
        
        # Write report
        with open(report_path, 'w') as f:
            f.write('\n'.join(lines))
        
        return report_path


# ============================================================================
# STANDALONE VALIDATOR WITH REPORTING
# ============================================================================

class DatasetValidator:
    """
    Compatibility wrapper that combines validation and reporting.
    Maintains the original API for backward compatibility.
    """
    
    def __init__(self, dataset_path: str, output_dir: Optional[str] = None,
                 generate_plots: bool = True):
        """Initialize validator with dataset."""
        self.dataset_path = dataset_path
        self.dataset_name = Path(dataset_path).stem
        self.generate_plots = generate_plots
        self.report_generator = ValidationReportGenerator(output_dir)
        
    def load_dataset(self) -> LocomotionData:
        """Load the dataset."""
        return LocomotionData(self.dataset_path)
    
    def validate_dataset(self, locomotion_data: LocomotionData) -> Dict[str, Any]:
        """Validate the dataset."""
        result = self.report_generator.validator.validate(self.dataset_path)
        
        # Convert to expected format
        return {
            'quality_score': result['stats']['pass_rate'],
            'status': 'PASS' if result['passed'] else 'FAIL',
            'violations': result['violations']
        }
    
    def run_validation(self) -> str:
        """Run complete validation workflow."""
        return self.report_generator.generate_report(
            self.dataset_path, 
            self.generate_plots
        )