#!/usr/bin/env python3
"""
Simplified Validation System for Locomotion Data

Core validation functionality without unnecessary complexity.
Focuses solely on checking if biomechanical data meets specifications.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

# Import configuration manager
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from internal.config_management.config_manager import ValidationConfigManager
from user_libs.python.locomotion_data import LocomotionData


# ============================================================================
# VALIDATION UTILITIES
# ============================================================================

def apply_contralateral_offset_kinematic(
    phase_data: Dict[int, Dict[str, Dict[str, float]]], 
    task_name: str = None,
    offset_percent: int = 50
) -> Dict[int, Dict[str, Dict[str, float]]]:
    """
    Apply contralateral offset for gait tasks with configurable offset.
    
    For gait tasks, the contralateral limb is offset by a percentage of the cycle
    (typically 50% for symmetric gait). This function dynamically calculates
    the offset for any phase points defined in the configuration.
    
    Args:
        phase_data: Validation ranges organized by phase
        task_name: Name of the task being validated
        offset_percent: Phase offset for contralateral limb (default 50%)
        
    Returns:
        Updated phase data with contralateral values
    """
    gait_tasks = ['level_walking', 'incline_walking', 'decline_walking',
                  'up_stairs', 'down_stairs', 'run']
    
    if not task_name or task_name not in gait_tasks:
        return phase_data
    
    result = {}
    available_phases = sorted(phase_data.keys())
    
    for phase in available_phases:
        result[phase] = phase_data[phase].copy()
        
        # Calculate contralateral phase dynamically
        contra_phase = (phase + offset_percent) % 100
        
        # Find closest available phase if exact match not found
        if contra_phase not in phase_data:
            # Find nearest phase in available data
            if available_phases:
                contra_phase = min(available_phases, 
                                 key=lambda x: abs(x - contra_phase))
        
        # Apply contralateral data if source phase exists
        if contra_phase in phase_data:
            for var_name, var_range in phase_data[contra_phase].items():
                if '_ipsi' in var_name:
                    contra_name = var_name.replace('_ipsi', '_contra')
                    result[phase][contra_name] = var_range
    
    return result


def apply_contralateral_offset_kinetic(
    phase_data: Dict[int, Dict[str, Dict[str, float]]], 
    task_name: str = None,
    offset_percent: int = 50
) -> Dict[int, Dict[str, Dict[str, float]]]:
    """Apply contralateral offset for kinetic variables in gait tasks."""
    return apply_contralateral_offset_kinematic(phase_data, task_name, offset_percent)


# ============================================================================
# SIMPLIFIED VALIDATOR
# ============================================================================

class Validator:
    """
    Simplified validator for locomotion datasets.
    
    Core functionality:
    1. Load dataset
    2. Check phase structure (150 points per cycle)
    3. Validate against YAML specifications
    4. Return simple pass/fail with details
    
    Supports arbitrary phase points defined in YAML configuration.
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize validator with configuration.
        
        Args:
            config_dir: Optional path to config directory with YAML files
        """
        self.config_manager = ValidationConfigManager(config_dir)
        # Phase points will be determined dynamically from configuration
        self.default_phases = {0: 0, 25: 37, 50: 75, 75: 112}
        
    def validate(self, dataset_path: str) -> Dict[str, Any]:
        """
        Validate a dataset against specifications.
        
        Args:
            dataset_path: Path to phase-indexed parquet file
            
        Returns:
            Dictionary with validation results:
            - passed: Overall pass/fail status
            - phase_valid: Whether phase structure is correct
            - violations: Dict of violations by task and variable
            - stats: Summary statistics
        """
        # Load dataset
        locomotion_data = LocomotionData(dataset_path)
        data = locomotion_data.get_expanded_data()
        
        # Validate phase structure
        phase_valid, phase_msg = self._validate_phase_structure(data)
        
        # Get task information
        tasks = locomotion_data.get_tasks()
        
        # Validate against specifications
        violations = {}
        total_checks = 0
        total_violations = 0
        
        for task in tasks:
            task_data = locomotion_data.get_task_data(task)
            task_violations = self._validate_task(task_data, task)
            
            if task_violations:
                violations[task] = task_violations
                total_violations += sum(len(v) for v in task_violations.values())
            
            total_checks += len(task_data) * 6 * 4  # steps * variables * phases
        
        # Calculate pass rate
        pass_rate = 1.0 - (total_violations / total_checks if total_checks > 0 else 0)
        
        return {
            'passed': phase_valid and pass_rate >= 0.9,
            'phase_valid': phase_valid,
            'phase_message': phase_msg,
            'violations': violations,
            'stats': {
                'total_checks': total_checks,
                'total_violations': total_violations,
                'pass_rate': pass_rate,
                'num_tasks': len(tasks),
                'dataset': Path(dataset_path).stem
            }
        }
    
    def _validate_phase_structure(self, data: np.ndarray) -> Tuple[bool, str]:
        """Check if all cycles have exactly 150 points."""
        if data.shape[1] != 150:
            return False, f"Invalid phase length: {data.shape[1]} (expected 150)"
        return True, "Phase structure valid (150 points per cycle)"
    
    def _get_phase_indices(self, task_ranges: Dict) -> Dict[int, int]:
        """
        Dynamically calculate phase indices from configuration.
        
        Assumes 150 points per cycle (0-149 indices).
        Maps phase percentages to array indices.
        
        Args:
            task_ranges: Dictionary with phase percentages as keys
            
        Returns:
            Dictionary mapping phase percentage to array index
        """
        # Extract phase percentages from config
        phases = sorted([int(p) for p in task_ranges.keys()])
        
        phase_indices = {}
        for phase in phases:
            # Map phase percentage to index (0-149)
            # Phase 0% = index 0, Phase 100% = index 149
            # Use 149 as max index since array is 0-indexed
            index = int(round((phase / 100.0) * 149))
            phase_indices[phase] = index
        
        return phase_indices
    
    def _validate_task(self, task_data: np.ndarray, task_name: str) -> Dict[str, List[int]]:
        """
        Validate task data against specifications.
        
        Returns dict of violations: {variable_name: [step_indices]}
        """
        violations = {}
        
        # Load validation ranges for both modes
        for mode in ['kinematic', 'kinetic']:
            ranges = self.config_manager.load_validation_ranges(mode)
            
            if task_name not in ranges:
                continue
                
            task_ranges = ranges[task_name]
            
            # Get phase indices dynamically from configuration
            phase_indices = self._get_phase_indices(task_ranges)
            
            # Apply contralateral offset
            if mode == 'kinematic':
                task_ranges = apply_contralateral_offset_kinematic(task_ranges, task_name)
            else:
                task_ranges = apply_contralateral_offset_kinetic(task_ranges, task_name)
            
            # Check each phase from configuration
            for phase_pct, phase_idx in phase_indices.items():
                if phase_pct not in task_ranges:
                    continue
                    
                phase_ranges = task_ranges[phase_pct]
                
                # Check each variable
                for var_name, var_range in phase_ranges.items():
                    var_violations = self._check_variable(
                        task_data, phase_idx, var_name, var_range
                    )
                    
                    if var_violations:
                        if var_name not in violations:
                            violations[var_name] = []
                        violations[var_name].extend(var_violations)
        
        return violations
    
    def _check_variable(self, data: np.ndarray, phase_idx: int, 
                       var_name: str, var_range: Dict) -> List[int]:
        """Check if variable values are within range at given phase."""
        violations = []
        
        # Map variable name to data column index
        var_idx = self._get_variable_index(var_name)
        if var_idx is None:
            return violations
        
        min_val = var_range.get('min', -float('inf'))
        max_val = var_range.get('max', float('inf'))
        
        # Check each step
        for step_idx in range(data.shape[0]):
            value = data[step_idx, phase_idx, var_idx]
            
            if value < min_val or value > max_val:
                violations.append(step_idx)
        
        return violations
    
    def _get_variable_index(self, var_name: str) -> Optional[int]:
        """Map variable name to data array index."""
        # Standard ordering in LocomotionData expanded format
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
        
        return variable_map.get(var_name)


# ============================================================================
# VALIDATION RESULT FORMATTER
# ============================================================================

def format_validation_result(result: Dict[str, Any]) -> str:
    """Format validation result for display."""
    lines = []
    lines.append("=" * 60)
    lines.append("VALIDATION REPORT")
    lines.append("=" * 60)
    
    # Overall status
    status = "✅ PASSED" if result['passed'] else "❌ FAILED"
    lines.append(f"Status: {status}")
    lines.append(f"Dataset: {result['stats']['dataset']}")
    lines.append(f"Pass Rate: {result['stats']['pass_rate']:.1%}")
    
    # Phase structure
    phase_status = "✅" if result['phase_valid'] else "❌"
    lines.append(f"\nPhase Structure: {phase_status} {result['phase_message']}")
    
    # Violations summary
    if result['violations']:
        lines.append(f"\nViolations by Task:")
        for task, task_violations in result['violations'].items():
            lines.append(f"  {task}:")
            for var, steps in task_violations.items():
                lines.append(f"    - {var}: {len(steps)} violations")
    else:
        lines.append("\nNo violations found!")
    
    # Statistics
    lines.append(f"\nStatistics:")
    lines.append(f"  Total Checks: {result['stats']['total_checks']:,}")
    lines.append(f"  Total Violations: {result['stats']['total_violations']:,}")
    lines.append(f"  Tasks Validated: {result['stats']['num_tasks']}")
    
    lines.append("=" * 60)
    
    return "\n".join(lines)


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """Command-line interface for validation."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validate locomotion datasets against specifications"
    )
    parser.add_argument("dataset", help="Path to phase-indexed parquet file")
    parser.add_argument("--config-dir", help="Optional config directory path")
    
    args = parser.parse_args()
    
    # Initialize validator
    config_dir = Path(args.config_dir) if args.config_dir else None
    validator = Validator(config_dir)
    
    # Run validation
    print(f"Validating: {args.dataset}")
    result = validator.validate(args.dataset)
    
    # Display results
    print(format_validation_result(result))
    
    # Exit with appropriate code
    sys.exit(0 if result['passed'] else 1)


# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================

# Provide DatasetValidator and StepClassifier for backward compatibility
# These are imported dynamically to avoid circular imports

def __getattr__(name):
    """Dynamic import for backward compatibility."""
    if name == 'DatasetValidator':
        from internal.validation_engine.report_generator import DatasetValidator
        return DatasetValidator
    elif name == 'StepClassifier':
        from internal.plot_generation.step_classifier import StepClassifier
        return StepClassifier
    elif name == 'ValidationReportGenerator':
        from internal.validation_engine.report_generator import ValidationReportGenerator
        return ValidationReportGenerator
    raise AttributeError(f"module {__name__} has no attribute {name}")

# Utility function for compatibility
def validate_task_completeness(task_data: Dict, task_name: str, mode: str):
    """
    Check if task data is complete for validation.
    
    For dynamic phase support, this now validates that at least some phases
    exist rather than requiring specific hardcoded phases.
    """
    # Extract numeric phases from task data
    phases = [int(p) for p in task_data.keys() if str(p).isdigit()]
    
    if not phases:
        raise ValueError(f"No valid phase data found for task {task_name}")
    
    # Ensure we have at least 2 phases for meaningful validation
    if len(phases) < 2:
        raise ValueError(f"Task {task_name} has only {len(phases)} phase(s). At least 2 required for validation.")


if __name__ == "__main__":
    main()