#!/usr/bin/env python3
"""
Enhanced Two-Tier Validation System

Implements a structured validation approach:
- Tier 1: Generic biomechanical range validation (basic plausibility)
- Tier 2: Task-specific sign convention checks with phase-based validation

This system provides comprehensive validation with intuitive feedback for users.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import re
from pathlib import Path
from validation_markdown_parser import ValidationMarkdownParser

class EnhancedValidationSystem:
    """Two-tier validation system for biomechanical data"""
    
    def __init__(self, validation_spec_path: Optional[str] = None):
        """
        Initialize the enhanced validation system.
        
        Args:
            validation_spec_path: Path to validation_expectations.md file
        """
        self.validation_spec_path = validation_spec_path or "docs/standard_spec/validation_expectations.md"
        self.markdown_parser = ValidationMarkdownParser()
        
        # Load validation rules from markdown
        if Path(self.validation_spec_path).exists():
            self.task_specific_rules = self.markdown_parser.parse_file(self.validation_spec_path)
        else:
            self.task_specific_rules = {}
            
        # Define generic biomechanical ranges (Tier 1)
        self.generic_ranges = self._define_generic_ranges()
        
        # Define phase points for validation
        self.phase_points = [0, 33, 50, 66]  # Four key phase points
        
        self.validation_results = {}
        
    def _define_generic_ranges(self) -> Dict[str, Dict[str, float]]:
        """
        Define generic biomechanical ranges for Tier 1 validation.
        These are broad, anatomically plausible ranges that apply across all tasks.
        """
        return {
            # Joint angles (in radians) - anatomical limits
            'hip_flexion_angle': {'min': -0.7, 'max': 2.1},      # ~-40° to +120°
            'knee_flexion_angle': {'min': -0.2, 'max': 2.4},     # ~-10° to +140°
            'ankle_flexion_angle': {'min': -0.9, 'max': 0.7},    # ~-50° to +40°
            
            # Joint moments (in Nm/kg) - typical human capacity
            'hip_flexion_moment': {'min': -4.0, 'max': 4.0},
            'knee_flexion_moment': {'min': -3.0, 'max': 3.0},
            'ankle_flexion_moment': {'min': -3.0, 'max': 3.0},
            
            # Ground reaction forces (in N) - typical human locomotion
            'vertical_grf_N': {'min': 0, 'max': 5000},           # 0 to ~5x body weight
            'ap_grf_N': {'min': -1000, 'max': 1000},             # ±1x body weight  
            'ml_grf_N': {'min': -500, 'max': 500},               # ±0.5x body weight
            
            # Center of pressure (in meters) - typical foot dimensions
            'cop_x_m': {'min': -0.20, 'max': 0.20},              # ±20cm
            'cop_y_m': {'min': -0.15, 'max': 0.15},              # ±15cm
            'cop_z_m': {'min': -0.10, 'max': 0.10},              # ±10cm
            
            # Joint velocities (in rad/s) - typical human movement
            'hip_velocity': {'min': -10.0, 'max': 10.0},
            'knee_velocity': {'min': -15.0, 'max': 15.0},
            'ankle_velocity': {'min': -10.0, 'max': 10.0},
            
            # Phase values
            'phase': {'min': 0.0, 'max': 100.0}
        }
    
    def tier1_generic_validation(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Tier 1: Generic biomechanical range validation.
        Checks if all values fall within anatomically plausible ranges.
        
        Args:
            data: DataFrame with biomechanical data
            
        Returns:
            Dict with validation results
        """
        results = {
            'tier': 1,
            'description': 'Generic biomechanical range validation',
            'column_results': {},
            'violations': [],
            'summary': {}
        }
        
        for column in data.columns:
            # Extract base variable name (remove side and unit suffixes)
            base_var = self._extract_base_variable(column)
            
            if base_var in self.generic_ranges:
                range_def = self.generic_ranges[base_var]
                col_data = data[column].dropna()
                
                if len(col_data) > 0:
                    min_val = col_data.min()
                    max_val = col_data.max()
                    
                    # Check for violations
                    violations_below = (col_data < range_def['min']).sum()
                    violations_above = (col_data > range_def['max']).sum()
                    total_violations = violations_below + violations_above
                    
                    violation_rate = total_violations / len(col_data)
                    
                    results['column_results'][column] = {
                        'base_variable': base_var,
                        'expected_range': range_def,
                        'actual_range': {'min': min_val, 'max': max_val},
                        'violations_below': int(violations_below),
                        'violations_above': int(violations_above),
                        'total_violations': int(total_violations),
                        'violation_rate': violation_rate,
                        'pass': violation_rate < 0.05  # Allow 5% violation tolerance
                    }
                    
                    if violation_rate >= 0.05:
                        results['violations'].append({
                            'column': column,
                            'issue': f"High violation rate: {violation_rate:.1%}",
                            'expected': f"[{range_def['min']:.2f}, {range_def['max']:.2f}]",
                            'actual': f"[{min_val:.2f}, {max_val:.2f}]"
                        })
        
        # Calculate summary statistics
        total_columns = len(results['column_results'])
        passed_columns = sum(1 for r in results['column_results'].values() if r['pass'])
        
        results['summary'] = {
            'total_columns_tested': total_columns,
            'columns_passed': passed_columns,
            'columns_failed': total_columns - passed_columns,
            'overall_pass_rate': passed_columns / total_columns if total_columns > 0 else 0,
            'tier1_pass': len(results['violations']) == 0
        }
        
        return results
    
    def tier2_task_specific_validation(self, data: pd.DataFrame, task_name: str) -> Dict[str, Any]:
        """
        Tier 2: Task-specific sign convention checks with phase-based validation.
        Uses phase-specific ranges and patterns from markdown specification.
        
        Args:
            data: DataFrame with biomechanical data
            task_name: Name of the locomotion task
            
        Returns:
            Dict with validation results
        """
        results = {
            'tier': 2,
            'description': f'Task-specific validation for {task_name}',
            'task_name': task_name,
            'phase_point_results': {},
            'pattern_violations': [],
            'phase_violations': [],
            'summary': {}
        }
        
        # Get task-specific rules from markdown
        if task_name not in self.task_specific_rules:
            results['error'] = f"No validation rules found for task: {task_name}"
            return results
            
        task_rules = self.task_specific_rules[task_name]
        
        # Check if phase data is available
        phase_columns = [col for col in data.columns if col.startswith('phase_')]
        if not phase_columns:
            results['error'] = "No phase data available for phase-specific validation"
            return results
            
        phase_column = phase_columns[0]  # Use first available phase column
        
        # Validate at each phase point
        for phase_point in self.phase_points:
            phase_results = self._validate_at_phase_point(data, task_rules, phase_column, phase_point)
            results['phase_point_results'][f'{phase_point}%'] = phase_results
        
        # Check for pattern violations across the full cycle
        pattern_results = self._validate_expected_patterns(data, task_rules, phase_column)
        results['pattern_violations'] = pattern_results
        
        # Calculate summary
        total_phase_validations = len(results['phase_point_results'])
        passed_phase_validations = sum(1 for pr in results['phase_point_results'].values() 
                                     if pr.get('overall_pass', False))
        
        results['summary'] = {
            'total_phase_points_tested': total_phase_validations,
            'phase_points_passed': passed_phase_validations,
            'pattern_violations_count': len(results['pattern_violations']),
            'tier2_pass': (passed_phase_validations == total_phase_validations and 
                          len(results['pattern_violations']) == 0)
        }
        
        return results
    
    def _validate_at_phase_point(self, data: pd.DataFrame, task_rules: Dict, 
                                phase_column: str, phase_point: float) -> Dict[str, Any]:
        """
        Validate data at a specific phase point.
        
        Args:
            data: DataFrame with biomechanical data
            task_rules: Task-specific validation rules
            phase_column: Name of phase column
            phase_point: Phase percentage to validate at
            
        Returns:
            Dict with validation results for this phase point
        """
        results = {
            'phase_point': phase_point,
            'variable_results': {},
            'violations': [],
            'data_points_found': 0
        }
        
        # Find data points near this phase
        tolerance = 2.0  # ±2% phase tolerance
        phase_mask = (np.abs(data[phase_column] - phase_point) <= tolerance)
        phase_data = data[phase_mask]
        
        results['data_points_found'] = len(phase_data)
        
        if len(phase_data) == 0:
            results['error'] = f"No data found near phase {phase_point}%"
            return results
        
        # Validate each variable at this phase point
        for rule in task_rules:
            var_name = rule.variable
            if var_name in phase_data.columns:
                var_data = phase_data[var_name].dropna()
                
                if len(var_data) > 0:
                    min_val = var_data.min()
                    max_val = var_data.max()
                    mean_val = var_data.mean()
                    
                    expected_min = rule.min_value
                    expected_max = rule.max_value
                    
                    # Check if values are within expected range
                    range_violation = (min_val < expected_min) or (max_val > expected_max)
                    
                    results['variable_results'][var_name] = {
                        'expected_range': [expected_min, expected_max],
                        'actual_range': [min_val, max_val],
                        'mean_value': mean_val,
                        'range_violation': range_violation,
                        'data_points': len(var_data)
                    }
                    
                    if range_violation:
                        results['violations'].append({
                            'variable': var_name,
                            'phase': f"{phase_point}%",
                            'expected': f"[{expected_min:.2f}, {expected_max:.2f}]",
                            'actual': f"[{min_val:.2f}, {max_val:.2f}]",
                            'units': rule.units
                        })
        
        results['overall_pass'] = len(results['violations']) == 0
        return results
    
    def _validate_expected_patterns(self, data: pd.DataFrame, task_rules: Dict, 
                                  phase_column: str) -> List[Dict[str, Any]]:
        """
        Validate expected patterns across the full gait cycle.
        
        Args:
            data: DataFrame with biomechanical data
            task_rules: Task-specific validation rules
            phase_column: Name of phase column
            
        Returns:
            List of pattern violations
        """
        violations = []
        
        for rule in task_rules:
            var_name = rule.variable
            expected_pattern = rule.expected_pattern
            
            if var_name in data.columns and expected_pattern:
                var_data = data[var_name].dropna()
                phase_data = data[phase_column].dropna()
                
                if len(var_data) > 0 and len(phase_data) > 0:
                    # Check specific patterns
                    pattern_valid = self._check_pattern(var_data, phase_data, expected_pattern)
                    
                    if not pattern_valid:
                        violations.append({
                            'variable': var_name,
                            'expected_pattern': expected_pattern,
                            'issue': f"Pattern {expected_pattern} not detected",
                            'units': rule.units
                        })
        
        return violations
    
    def _check_pattern(self, var_data: pd.Series, phase_data: pd.Series, pattern: str) -> bool:
        """
        Check if data matches expected pattern.
        
        Args:
            var_data: Variable data series
            phase_data: Phase data series
            pattern: Expected pattern string
            
        Returns:
            Boolean indicating if pattern is valid
        """
        # This is a simplified pattern checker - can be enhanced
        if 'peak_at_' in pattern:
            # Extract expected peak phase
            peak_match = re.search(r'peak_at_(\d+)', pattern)
            if peak_match:
                expected_peak_phase = float(peak_match.group(1))
                
                # Find actual peak phase
                max_idx = var_data.idxmax()
                if max_idx in phase_data.index:
                    actual_peak_phase = phase_data.loc[max_idx]
                    
                    # Allow ±15% tolerance for peak timing
                    return abs(actual_peak_phase - expected_peak_phase) <= 15
        
        elif 'valley_at_' in pattern:
            # Extract expected valley phase
            valley_match = re.search(r'valley_at_(\d+)', pattern)
            if valley_match:
                expected_valley_phase = float(valley_match.group(1))
                
                # Find actual valley phase
                min_idx = var_data.idxmin()
                if min_idx in phase_data.index:
                    actual_valley_phase = phase_data.loc[min_idx]
                    
                    # Allow ±15% tolerance for valley timing
                    return abs(actual_valley_phase - expected_valley_phase) <= 15
        
        elif pattern == 'near_zero':
            # Check if values are close to zero
            return np.abs(var_data).mean() < 0.1 * np.abs(var_data).std()
        
        # Default to True for unimplemented patterns
        return True
    
    def _extract_base_variable(self, column_name: str) -> str:
        """
        Extract base variable name from full column name.
        
        Args:
            column_name: Full column name (e.g., 'hip_flexion_angle_left_rad')
            
        Returns:
            Base variable name (e.g., 'hip_flexion_angle')
        """
        # Remove common suffixes
        suffixes = ['_left', '_right', '_l', '_r', '_rad', '_deg', '_N', '_Nm', '_m', '_s']
        
        base_name = column_name
        for suffix in suffixes:
            if base_name.endswith(suffix):
                base_name = base_name[:-len(suffix)]
        
        return base_name
    
    def run_full_validation(self, data: pd.DataFrame, task_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Run complete two-tier validation on dataset.
        
        Args:
            data: DataFrame with biomechanical data
            task_name: Optional task name for Tier 2 validation
            
        Returns:
            Dict with complete validation results
        """
        results = {
            'validation_timestamp': pd.Timestamp.now().isoformat(),
            'dataset_info': {
                'total_rows': len(data),
                'total_columns': len(data.columns),
                'task_name': task_name
            },
            'tier1_results': {},
            'tier2_results': {},
            'overall_summary': {}
        }
        
        # Run Tier 1 validation
        print("Running Tier 1: Generic range validation...")
        results['tier1_results'] = self.tier1_generic_validation(data)
        
        # Run Tier 2 validation if task name is provided
        if task_name:
            print(f"Running Tier 2: Task-specific validation for {task_name}...")
            results['tier2_results'] = self.tier2_task_specific_validation(data, task_name)
        else:
            # Try to infer task name from data
            if 'task_name' in data.columns:
                unique_tasks = data['task_name'].unique()
                if len(unique_tasks) == 1:
                    inferred_task = unique_tasks[0]
                    print(f"Running Tier 2: Inferred task '{inferred_task}'...")
                    results['tier2_results'] = self.tier2_task_specific_validation(data, inferred_task)
                    results['dataset_info']['task_name'] = inferred_task
                else:
                    results['tier2_results'] = {'error': 'Multiple tasks found, specify task_name'}
            else:
                results['tier2_results'] = {'error': 'No task name provided or found in data'}
        
        # Calculate overall summary
        tier1_pass = results['tier1_results'].get('summary', {}).get('tier1_pass', False)
        tier2_pass = results['tier2_results'].get('summary', {}).get('tier2_pass', False)
        
        results['overall_summary'] = {
            'tier1_pass': tier1_pass,
            'tier2_pass': tier2_pass,
            'overall_validation_pass': tier1_pass and tier2_pass,
            'validation_level': 'Two-Tier Enhanced Validation'
        }
        
        return results
    
    def generate_validation_report(self, results: Dict[str, Any], output_path: str):
        """
        Generate a comprehensive validation report.
        
        Args:
            results: Validation results from run_full_validation
            output_path: Path to save the report
        """
        with open(output_path, 'w') as f:
            f.write("ENHANCED TWO-TIER VALIDATION REPORT\n")
            f.write("=" * 50 + "\n\n")
            
            # Header information
            f.write(f"Validation timestamp: {results['validation_timestamp']}\n")
            f.write(f"Dataset: {results['dataset_info']['total_rows']} rows, {results['dataset_info']['total_columns']} columns\n")
            f.write(f"Task: {results['dataset_info'].get('task_name', 'Not specified')}\n\n")
            
            # Overall summary
            overall = results['overall_summary']
            f.write("OVERALL VALIDATION RESULT\n")
            f.write("-" * 30 + "\n")
            f.write(f"Status: {'✅ PASS' if overall['overall_validation_pass'] else '❌ FAIL'}\n")
            f.write(f"Tier 1 (Generic ranges): {'✅ PASS' if overall['tier1_pass'] else '❌ FAIL'}\n")
            f.write(f"Tier 2 (Task-specific): {'✅ PASS' if overall['tier2_pass'] else '❌ FAIL'}\n\n")
            
            # Tier 1 results
            tier1 = results['tier1_results']
            if tier1:
                f.write("TIER 1: GENERIC RANGE VALIDATION\n")
                f.write("-" * 35 + "\n")
                summary = tier1.get('summary', {})
                f.write(f"Columns tested: {summary.get('total_columns_tested', 0)}\n")
                f.write(f"Columns passed: {summary.get('columns_passed', 0)}\n")
                f.write(f"Pass rate: {summary.get('overall_pass_rate', 0):.1%}\n\n")
                
                if tier1.get('violations'):
                    f.write("Generic Range Violations:\n")
                    for violation in tier1['violations']:
                        f.write(f"  - {violation['column']}: {violation['issue']}\n")
                        f.write(f"    Expected: {violation['expected']}, Actual: {violation['actual']}\n")
                    f.write("\n")
            
            # Tier 2 results
            tier2 = results['tier2_results']
            if tier2 and 'error' not in tier2:
                f.write("TIER 2: TASK-SPECIFIC VALIDATION\n")
                f.write("-" * 35 + "\n")
                f.write(f"Task: {tier2['task_name']}\n")
                
                # Phase point results
                phase_results = tier2.get('phase_point_results', {})
                f.write(f"Phase points tested: {len(phase_results)}\n")
                passed_phases = sum(1 for pr in phase_results.values() if pr.get('overall_pass', False))
                f.write(f"Phase points passed: {passed_phases}\n\n")
                
                # Phase violations
                for phase, phase_result in phase_results.items():
                    if phase_result.get('violations'):
                        f.write(f"Phase {phase} violations:\n")
                        for violation in phase_result['violations']:
                            f.write(f"  - {violation['variable']}: Expected {violation['expected']}, "
                                  f"Actual {violation['actual']} {violation.get('units', '')}\n")
                        f.write("\n")
                
                # Pattern violations
                pattern_violations = tier2.get('pattern_violations', [])
                if pattern_violations:
                    f.write("Pattern Violations:\n")
                    for violation in pattern_violations:
                        f.write(f"  - {violation['variable']}: {violation['issue']}\n")
                    f.write("\n")
            
            elif tier2 and 'error' in tier2:
                f.write("TIER 2: TASK-SPECIFIC VALIDATION\n")
                f.write("-" * 35 + "\n")
                f.write(f"Error: {tier2['error']}\n\n")
        
        print(f"📄 Enhanced validation report saved to: {output_path}")


def main():
    """Main function for testing the enhanced validation system"""
    
    # Create enhanced validation system
    validator = EnhancedValidationSystem()
    
    # Create test data
    print("Creating test dataset...")
    np.random.seed(42)
    n_samples = 300
    
    # Create phase data
    phase_l = np.concatenate([
        np.linspace(0, 99.9, 150),  # Cycle 1
        np.linspace(0, 99.9, 150)   # Cycle 2
    ])
    
    test_data = pd.DataFrame({
        'time_s': np.linspace(0, 3.0, n_samples),
        'phase_l': phase_l,
        'task_name': ['level_walking'] * n_samples,
        'subject_id': ['S01'] * n_samples,
        
        # Joint angles with realistic walking patterns
        'hip_flexion_angle_left_rad': 0.2 + 0.4 * np.sin(2 * np.pi * phase_l / 100),
        'knee_flexion_angle_left_rad': 0.2 + 0.5 * np.maximum(0, np.sin(2 * np.pi * phase_l / 100)),
        'ankle_flexion_angle_left_rad': 0.1 * np.sin(2 * np.pi * phase_l / 100),
        
        # GRF data
        'vertical_grf_N': 800 + 400 * np.sin(2 * np.pi * phase_l / 100)**2,
        'ap_grf_N': 100 * np.sin(4 * np.pi * phase_l / 100),
        'ml_grf_N': 20 * np.random.randn(n_samples),
    })
    
    # Run enhanced validation
    results = validator.run_full_validation(test_data, 'level_walking')
    
    # Generate report
    from pathlib import Path
    output_dir = Path("validation_reports")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"enhanced_validation_{timestamp}.txt"
    
    validator.generate_validation_report(results, str(report_path))
    
    return results


if __name__ == "__main__":
    main()