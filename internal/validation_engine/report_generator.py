#!/usr/bin/env python3
"""
Validation Report Generator

Generates markdown reports and coordinates plot generation for validation results.
Separated from core validation logic for better modularity.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

import sys
import numpy as np
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
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize report generator.
        
        Args:
            output_dir: Output directory for reports and plots
        """
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            # Default to documentation directory
            project_root = Path(__file__).parent.parent.parent
            self.output_dir = project_root / "docs" / "reference" / "datasets_documentation" / "validation_reports"
        
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
        data = locomotion_data.get_expanded_data()
        tasks = locomotion_data.get_tasks()
        
        # Convert violations to boolean array for step classification
        violations = self._violations_to_array(validation_result['violations'], data.shape)
        
        # Generate plots for each task
        for task in tasks:
            task_data = locomotion_data.get_task_data(task)
            
            # Classify steps for coloring
            task_violations = violations  # Simplified - would need proper task filtering
            step_colors = self.step_classifier.classify_all_steps(task_violations)
            
            # Generate kinematic plot
            kinematic_plot = create_filters_by_phase_plot(
                validation_data=self.validator.config_manager.load_validation_ranges('kinematic'),
                task_name=task,
                output_dir=str(self.plots_dir),
                mode='kinematic',
                data=task_data,
                step_colors=step_colors,
                dataset_name=Path(dataset_path).stem,
                timestamp=timestamp
            )
            plot_paths[f"{task}_kinematic"] = kinematic_plot
            
            # Generate kinetic plot
            kinetic_plot = create_filters_by_phase_plot(
                validation_data=self.validator.config_manager.load_validation_ranges('kinetic'),
                task_name=task,
                output_dir=str(self.plots_dir),
                mode='kinetic',
                data=task_data,
                step_colors=step_colors,
                dataset_name=Path(dataset_path).stem,
                timestamp=timestamp
            )
            plot_paths[f"{task}_kinetic"] = kinetic_plot
        
        return plot_paths
    
    def _violations_to_array(self, violations: Dict, data_shape: tuple) -> np.ndarray:
        """Convert violations dictionary to boolean array."""
        import numpy as np
        
        # Initialize array
        violation_array = np.zeros((data_shape[0], 12), dtype=bool)  # 12 standard variables
        
        # This is simplified - would need proper mapping
        for task, task_violations in violations.items():
            for var_name, step_indices in task_violations.items():
                var_idx = self.validator._get_variable_index(var_name)
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