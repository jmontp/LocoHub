#!/usr/bin/env python3
"""
Simplified Validation System for Locomotion Data

Core validation functionality without unnecessary complexity.
Focuses solely on checking if biomechanical data meets specifications.
"""

import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

# Import configuration manager
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from internal.config_management.config_manager import ValidationConfigManager
from user_libs.python.locomotion_data import LocomotionData


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
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize validator with configuration.
        
        Args:
            config_path: Optional path to config file or directory. 
                        If file, loads that specific config.
                        If directory or None, uses default config.
        """
        if config_path and Path(config_path).is_file():
            # If it's a file, load it directly
            self.config_manager = ValidationConfigManager(config_path)
        else:
            # If it's a directory or None, use default behavior
            self.config_manager = ValidationConfigManager()
        
    def validate(self, dataset_path: str, ignore_features: List[str] = None) -> Dict[str, Any]:
        """
        Validate a dataset against specifications.
        
        Args:
            dataset_path: Path to phase-indexed parquet file
            ignore_features: Optional list of feature names to ignore during validation
            
        Returns:
            Dictionary with validation results:
            - passed: Overall pass/fail status
            - phase_valid: Whether phase structure is correct
            - violations: Dict of violations by task and variable
            - stats: Summary statistics
        """
        # Load dataset with proper phase column name
        locomotion_data = LocomotionData(dataset_path, phase_col='phase_ipsi')
        
        # Validate phase structure
        phase_valid, phase_msg = self._validate_phase_structure(locomotion_data)
        
        # Get task information
        tasks = locomotion_data.get_tasks()
        
        # Validate against specifications
        violations = {}
        total_checks = 0
        total_violations = 0
        total_strides = 0
        total_failing_strides = 0
        
        for task in tasks:
            task_violations = self._validate_task(locomotion_data, task, ignore_features)
            
            if task_violations:
                violations[task] = task_violations
                total_violations += sum(len(v) for v in task_violations.values())
            
            # Count number of cycles for this task
            task_data = locomotion_data.df[locomotion_data.df['task'] == task]
            n_cycles = len(task_data) // 150  # Each cycle is 150 points
            total_strides += n_cycles
            
            # Count failing strides for this task (stride-level pass rate)
            failing_features = self._validate_task_with_failing_features(locomotion_data, task, ignore_features)
            total_failing_strides += len(failing_features)
            
            # Get number of variables and phases being checked from config
            n_variables = 12  # 6 kinematic + 6 kinetic variables
            n_phases = 4  # Default 4 phases (0%, 25%, 50%, 75%)
            total_checks += n_cycles * n_variables * n_phases
        
        # Calculate stride-level pass rate (green strides / total strides)
        stride_pass_rate = 1.0 - (total_failing_strides / total_strides if total_strides > 0 else 0)
        
        # Keep old variable-level calculation for detailed statistics
        variable_pass_rate = 1.0 - (total_violations / total_checks if total_checks > 0 else 0)
        
        return {
            'passed': phase_valid and stride_pass_rate >= 0.9,
            'phase_valid': phase_valid,
            'phase_message': phase_msg,
            'violations': violations,
            'stats': {
                'total_checks': total_checks,
                'total_violations': total_violations,
                'total_strides': total_strides,
                'total_failing_strides': total_failing_strides,
                'pass_rate': stride_pass_rate,  # Now stride-level pass rate (main metric)
                'variable_pass_rate': variable_pass_rate,  # Old variable-level for reference
                'num_tasks': len(tasks),
                'dataset': Path(dataset_path).stem
            }
        }
    
    def _validate_phase_structure(self, locomotion_data: LocomotionData) -> Tuple[bool, str]:
        """Check if all cycles have exactly 150 points."""
        # Check each task to ensure proper phase structure
        tasks = locomotion_data.get_tasks()
        
        for task in tasks:
            task_data = locomotion_data.df[locomotion_data.df['task'] == task]
            n_points = len(task_data)
            
            # Check if divisible by 150
            if n_points % 150 != 0:
                return False, f"Task '{task}' has {n_points} points, not divisible by 150"
            
            # Verify phase values if present
            if 'phase' in task_data.columns:
                # Group by cycle and check each has 150 points
                n_cycles = n_points // 150
                for cycle_idx in range(n_cycles):
                    cycle_start = cycle_idx * 150
                    cycle_end = (cycle_idx + 1) * 150
                    cycle_data = task_data.iloc[cycle_start:cycle_end]
                    
                    if len(cycle_data) != 150:
                        return False, f"Cycle {cycle_idx} in task '{task}' has {len(cycle_data)} points"
        
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
    
    def _validate_task(self, locomotion_data: LocomotionData, task_name: str, ignore_features: List[str] = None) -> Dict[str, List[int]]:
        """
        Validate task data against specifications.
        
        Returns dict of violations: {variable_name: [stride_indices]}
        """
        # Get failing features per stride
        failing_features = self._validate_task_with_failing_features(locomotion_data, task_name, ignore_features)
        
        # Convert to variable-centric format
        violations = {}
        for stride_idx, failed_vars in failing_features.items():
            for var_name in failed_vars:
                if var_name not in violations:
                    violations[var_name] = []
                violations[var_name].append(stride_idx)
        
        return violations
    
    def _validate_task_with_failing_features(self, locomotion_data: LocomotionData, task_name: str, ignore_features: List[str] = None) -> Dict[int, List[str]]:
        """
        Validate task data and return failing features per stride.
        
        Args:
            locomotion_data: The locomotion data object
            task_name: Name of the task to validate
            ignore_features: Optional list of feature names to ignore during validation
            
        Returns dict: {stride_idx: [list_of_failed_variable_names]}
        Strides not in the dict passed all checks.
        """
        failing_features = {}
        
        # Check if task exists in configuration
        if not self.config_manager.has_task(task_name):
            return failing_features
            
        # Get validation ranges for this specific task (includes generated contra features)
        task_ranges = self.config_manager.get_task_data(task_name)
        
        # Get phase indices dynamically from configuration
        phase_indices = self._get_phase_indices(task_ranges)
        
        # Collect all variables we need to check
        all_variables_to_check = set()
        for phase_ranges in task_ranges.values():
            all_variables_to_check.update(phase_ranges.keys())
        
        # Filter out ignored features if specified
        if ignore_features:
            all_variables_to_check = all_variables_to_check - set(ignore_features)
        
        # Filter to only variables that exist in the dataset
        all_features = locomotion_data.features
        valid_variables = [v for v in all_variables_to_check if v in all_features]
        
        if not valid_variables:
            return failing_features
        
        # Get 3D array for this task with all subjects (single unified load)
        data_3d, feature_names = locomotion_data.get_cycles(None, task_name, list(valid_variables))
        
        if data_3d is None:
            return failing_features
        
        # Check each stride
        n_strides = data_3d.shape[0]
        for stride_idx in range(n_strides):
            stride_failures = []
            
            # Check each phase
            for phase_pct, phase_idx in phase_indices.items():
                if phase_pct not in task_ranges:
                    continue
                
                phase_ranges = task_ranges[phase_pct]
                
                # Check each variable
                for var_name, var_range in phase_ranges.items():
                    if var_name not in feature_names:
                        continue
                    
                    # Get variable index in the feature array
                    var_idx = feature_names.index(var_name)
                    
                    # Get value at this stride, phase, and variable
                    value = data_3d[stride_idx, phase_idx, var_idx]
                    
                    # Check if within range
                    min_val = var_range.get('min')
                    max_val = var_range.get('max')
                    
                    # Skip if ranges are None (missing data placeholders)
                    if min_val is None or max_val is None:
                        continue
                    
                    if value < min_val or value > max_val:
                        if var_name not in stride_failures:
                            stride_failures.append(var_name)
            
            # Only add to failing_features if this stride had failures
            if stride_failures:
                failing_features[stride_idx] = stride_failures
        
        return failing_features
    
    def _check_variable_3d(self, data_3d: np.ndarray, phase_idx: int, 
                          var_idx: int, var_range: Dict) -> List[int]:
        """
        Check if variable values are within range at given phase using 3D array.
        
        Args:
            data_3d: 3D array of shape (n_cycles, 150, n_features)
            phase_idx: Index into the 150-point cycle (0-149)
            var_idx: Index of the variable in the features dimension
            var_range: Dict with 'min' and 'max' keys
            
        Returns:
            List of cycle indices that violate the range
        """
        violations = []
        
        min_val = var_range.get('min', -float('inf'))
        max_val = var_range.get('max', float('inf'))
        
        # Check each cycle at the specified phase
        n_cycles = data_3d.shape[0]
        for cycle_idx in range(n_cycles):
            # Direct indexing: get value at this cycle, phase, and variable
            value = data_3d[cycle_idx, phase_idx, var_idx]
            
            # Check if value is within range
            if value < min_val or value > max_val:
                violations.append(cycle_idx)
        
        return violations
    


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

