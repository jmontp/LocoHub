#!/usr/bin/env python3
"""
⚠️  OUTDATED FILE - DO NOT USE WITHOUT THOROUGH REVIEW ⚠️

This file appears to be misnamed and contains specification compliance testing code
rather than dataset validation functionality. The filename suggests it should be a
time-based dataset validator, but the content does not match this expectation.

**CRITICAL WARNING**: This file has NOT been thoroughly vetted and may contain:
- Outdated validation logic
- Incorrect variable mappings  
- Incompatible data structures
- Security vulnerabilities

**ACTION REQUIRED**: Before using this file:
1. Review all validation logic against current specification
2. Verify variable naming conventions are up-to-date
3. Test thoroughly with known good datasets
4. Update imports and dependencies
5. Rename file to match actual functionality

**RECOMMENDED**: Use the current dataset_validator.py instead, which has been
thoroughly tested and validated for phase-based datasets.

Original Description (may be outdated):
Specification Compliance Test Suite

Tests the intuitive validation system against the standard specification requirements:
1. Variable naming convention compliance
2. Phase calculation expectations (0-100%, 150 points/cycle) 
3. Sign convention adherence
4. Markdown-based validation expectations

This ensures the intuitive validation system correctly implements the project standards.
"""

# CRITICAL: Prevent usage of this outdated file
import sys

def _prevent_usage():
    """Prevent usage of this outdated file until it's thoroughly reviewed."""
    error_msg = """
    ⚠️  CRITICAL ERROR: Attempting to use outdated validation file ⚠️
    
    This file (dataset_validator_time.py) is OUTDATED and has not been thoroughly vetted.
    
    Using this file may result in:
    - Incorrect validation results
    - Data corruption or loss
    - Security vulnerabilities
    - Compatibility issues
    
    **SOLUTION**: Use the current dataset_validator.py instead:
    
    from validation.dataset_validator import DatasetValidator
    
    If you specifically need time-based validation functionality,
    please review and update this file thoroughly before use.
    
    To override this safety check (NOT RECOMMENDED), set environment variable:
    ALLOW_OUTDATED_VALIDATOR=true
    """
    
    import os
    if os.environ.get('ALLOW_OUTDATED_VALIDATOR', '').lower() != 'true':
        print(error_msg, file=sys.stderr)
        sys.exit(1)
    else:
        print("⚠️  WARNING: Using outdated validator despite safety warnings!", file=sys.stderr)

# Check for usage attempt
_prevent_usage()

import pandas as pd
import numpy as np
import re
from typing import List, Dict, Tuple, Optional
import unittest
from pathlib import Path
import tempfile
import os
from validation_markdown_parser import ValidationMarkdownParser

class SpecComplianceTestSuite:
    """Test suite to verify specification compliance of validation systems"""
    
    def __init__(self):
        self.test_results = []
        self.errors = []
        self.markdown_parser = ValidationMarkdownParser()
        
    def test_variable_naming_convention(self, columns: List[str]) -> Dict[str, any]:
        """
        Test variable naming convention compliance.
        
        Expected pattern: <joint>_<motion>_<measurement>_<side>_<unit>
        Examples: knee_flexion_angle_right_rad, hip_moment_left_Nm
        
        Args:
            columns: List of column names to test
            
        Returns:
            Dict with test results
        """
        print("Testing Variable Naming Convention Compliance...")
        
        # Define the expected pattern components
        valid_joints = {
            'hip', 'knee', 'ankle', 'torso', 'thigh', 'shank', 'foot',
            'lumbar', 'thorax', 'pelvis', 'spine'
        }
        
        valid_motions = {
            'flexion', 'extension', 'adduction', 'abduction', 'rotation',
            'tilt', 'obliquity', 'list', 'moment', 'power', 'force',
            'translation', 'position', 'velocity', 'acceleration'
        }
        
        valid_measurements = {
            'angle', 'moment', 'power', 'force', 'position', 'velocity',
            'acceleration', 'translation'
        }
        
        valid_sides = {'left', 'right', 'l', 'r'}
        
        valid_units = {
            'rad', 'deg', 'N', 'Nm', 'm', 's', 'kg', 'rad_s', 'm_s', 'm_s2',
            'W', 'J', 'Pa'
        }
        
        # Core required columns that don't follow the pattern
        core_columns = {
            'time_s', 'phase_l', 'phase_r', 'phase_%', 'subject_id', 'task_id',
            'task_name', 'step_number', 'cycle_number', 'is_outlier',
            'vertical_grf_N', 'ap_grf_N', 'ml_grf_N', 'cop_x_m', 'cop_y_m', 'cop_z_m'
        }
        
        # Metadata columns that don't follow the pattern
        metadata_columns = {
            'age', 'gender', 'height', 'body_mass', 'walking_speed_m_s',
            'ground_inclination_deg', 'sampling_frequency_hz'
        }
        
        results = {
            'total_columns': len(columns),
            'compliant_columns': [],
            'non_compliant_columns': [],
            'core_columns_found': [],
            'metadata_columns_found': [],
            'errors': [],
            'compliance_rate': 0.0
        }
        
        # Define the main naming pattern
        # Pattern: <joint>_<motion>_<measurement>_<side>_<unit>
        biomech_pattern = re.compile(
            r'^([a-z]+)_([a-z]+)_([a-z]+)_([a-z]+)_([a-z_0-9]+)$'
        )
        
        # Alternative patterns for some variables
        grf_pattern = re.compile(r'^(vertical|ap|ml)_grf_N$')
        cop_pattern = re.compile(r'^cop_[xyz]_m$')
        phase_pattern = re.compile(r'^phase_[lr%]$')
        
        for col in columns:
            if col in core_columns:
                results['core_columns_found'].append(col)
                results['compliant_columns'].append(col)
            elif col in metadata_columns:
                results['metadata_columns_found'].append(col)
                results['compliant_columns'].append(col)
            elif grf_pattern.match(col) or cop_pattern.match(col) or phase_pattern.match(col):
                results['compliant_columns'].append(col)
            else:
                # Test against main biomechanical pattern
                match = biomech_pattern.match(col)
                if match:
                    joint, motion, measurement, side, unit = match.groups()
                    
                    # Validate each component
                    issues = []
                    if joint not in valid_joints:
                        issues.append(f"Unknown joint: {joint}")
                    if motion not in valid_motions:
                        issues.append(f"Unknown motion: {motion}")
                    if measurement not in valid_measurements:
                        issues.append(f"Unknown measurement: {measurement}")
                    if side not in valid_sides:
                        issues.append(f"Unknown side: {side}")
                    if unit not in valid_units:
                        issues.append(f"Unknown unit: {unit}")
                    
                    if issues:
                        results['non_compliant_columns'].append({
                            'column': col,
                            'issues': issues
                        })
                        results['errors'].extend([f"{col}: {issue}" for issue in issues])
                    else:
                        results['compliant_columns'].append(col)
                else:
                    results['non_compliant_columns'].append({
                        'column': col,
                        'issues': ['Does not match expected naming pattern']
                    })
                    results['errors'].append(f"{col}: Does not match expected naming pattern")
        
        results['compliance_rate'] = len(results['compliant_columns']) / len(columns) if columns else 0.0
        
        print(f"  ✓ Total columns tested: {results['total_columns']}")
        print(f"  ✓ Compliant columns: {len(results['compliant_columns'])}")
        print(f"  ✗ Non-compliant columns: {len(results['non_compliant_columns'])}")
        print(f"  📊 Compliance rate: {results['compliance_rate']:.1%}")
        
        return results
    
    def test_phase_calculation_expectations(self, data: pd.DataFrame) -> Dict[str, any]:
        """
        Test phase calculation expectations.
        
        Expected:
        - Phase values in range [0.0, 100.0)
        - 150 points per cycle (default)
        - Phase columns: phase_l, phase_r, or phase_%
        
        Args:
            data: DataFrame with phase data
            
        Returns:
            Dict with test results
        """
        print("Testing Phase Calculation Expectations...")
        
        results = {
            'phase_columns_found': [],
            'valid_phase_ranges': {},
            'points_per_cycle_analysis': {},
            'phase_continuity_check': {},
            'errors': [],
            'compliance_issues': []
        }
        
        # Check for phase columns
        phase_columns = [col for col in data.columns if col.startswith('phase_')]
        results['phase_columns_found'] = phase_columns
        
        if not phase_columns:
            results['errors'].append("No phase columns found (expected: phase_l, phase_r, or phase_%)")
            return results
        
        for phase_col in phase_columns:
            if phase_col not in data.columns:
                continue
                
            phase_data = data[phase_col].dropna()
            
            # Test 1: Phase range [0.0, 100.0)
            min_phase = phase_data.min()
            max_phase = phase_data.max()
            
            range_valid = (min_phase >= 0.0) and (max_phase < 100.0)
            results['valid_phase_ranges'][phase_col] = {
                'min': min_phase,
                'max': max_phase,
                'valid': range_valid
            }
            
            if not range_valid:
                results['compliance_issues'].append(
                    f"{phase_col}: Phase values outside expected range [0.0, 100.0). "
                    f"Found [{min_phase:.2f}, {max_phase:.2f}]"
                )
            
            # Test 2: Points per cycle analysis
            if len(phase_data) > 0:
                # Look for cycle boundaries (where phase resets to 0 or near 0)
                phase_diff = np.diff(phase_data)
                cycle_resets = np.where(phase_diff < -50)[0]  # Large negative jump indicates cycle reset
                
                if len(cycle_resets) > 0:
                    # Calculate points per cycle
                    cycle_lengths = []
                    start_idx = 0
                    
                    for reset_idx in cycle_resets:
                        cycle_length = reset_idx - start_idx + 1
                        cycle_lengths.append(cycle_length)
                        start_idx = reset_idx + 1
                    
                    # Add final cycle if data continues
                    if start_idx < len(phase_data):
                        cycle_lengths.append(len(phase_data) - start_idx)
                    
                    if cycle_lengths:
                        avg_points = np.mean(cycle_lengths)
                        std_points = np.std(cycle_lengths)
                        
                        results['points_per_cycle_analysis'][phase_col] = {
                            'cycles_found': len(cycle_lengths),
                            'avg_points_per_cycle': avg_points,
                            'std_points_per_cycle': std_points,
                            'expected_150_compliance': abs(avg_points - 150) < 10  # Allow ±10 tolerance
                        }
                        
                        if abs(avg_points - 150) >= 10:
                            results['compliance_issues'].append(
                                f"{phase_col}: Average points per cycle ({avg_points:.1f}) "
                                f"differs significantly from expected 150"
                            )
            
            # Test 3: Phase continuity (should be mostly monotonic within cycles)
            if len(phase_data) > 1:
                # Check for reasonable continuity (allowing for cycle resets)
                phase_jumps = np.abs(np.diff(phase_data))
                large_jumps = phase_jumps > 50  # Large jumps could indicate issues
                reset_jumps = phase_diff < -50   # Expected cycle resets
                
                unexpected_jumps = large_jumps & ~reset_jumps
                
                results['phase_continuity_check'][phase_col] = {
                    'total_points': len(phase_data),
                    'large_jumps': np.sum(large_jumps),
                    'expected_resets': np.sum(reset_jumps),
                    'unexpected_jumps': np.sum(unexpected_jumps),
                    'continuity_ok': np.sum(unexpected_jumps) < len(phase_data) * 0.01  # <1% unexpected jumps
                }
                
                if np.sum(unexpected_jumps) >= len(phase_data) * 0.01:
                    results['compliance_issues'].append(
                        f"{phase_col}: Too many unexpected phase discontinuities "
                        f"({np.sum(unexpected_jumps)} out of {len(phase_data)} points)"
                    )
        
        print(f"  ✓ Phase columns found: {len(phase_columns)}")
        print(f"  ✓ Range compliance issues: {len([r for r in results['valid_phase_ranges'].values() if not r['valid']])}")
        print(f"  ✗ Total compliance issues: {len(results['compliance_issues'])}")
        
        return results
    
    def test_sign_convention_adherence(self, data: pd.DataFrame) -> Dict[str, any]:
        """
        Test sign convention adherence.
        
        Expected sign conventions (from OpenSim):
        - Hip extension: positive
        - Knee extension: positive  
        - Ankle dorsiflexion: positive
        - GRF vertical: positive upward
        - GRF AP: positive forward
        - GRF ML: positive rightward
        
        Args:
            data: DataFrame with biomechanical data
            
        Returns:
            Dict with test results
        """
        print("Testing Sign Convention Adherence...")
        
        results = {
            'joint_angle_checks': {},
            'grf_checks': {},
            'cop_checks': {},
            'sign_convention_issues': [],
            'anatomical_plausibility': {}
        }
        
        # Define expected sign conventions and plausible ranges
        expected_ranges = {
            # Joint angles (in radians) - typical ranges during walking
            'hip_flexion_angle': {'min': -0.5, 'max': 1.2},  # ~-30° to +70°
            'knee_flexion_angle': {'min': -0.1, 'max': 1.4}, # ~-5° to +80°
            'ankle_flexion_angle': {'min': -0.6, 'max': 0.4}, # ~-35° to +25°
            
            # GRF (in Newtons) - typical ranges for walking
            'vertical_grf_N': {'min': 0, 'max': 2000},     # 0 to ~2x body weight
            'ap_grf_N': {'min': -500, 'max': 500},         # ±0.5x body weight
            'ml_grf_N': {'min': -200, 'max': 200},         # ±0.2x body weight
            
            # COP (in meters) - typical foot dimensions
            'cop_x_m': {'min': -0.15, 'max': 0.15},        # ±15cm
            'cop_y_m': {'min': -0.1, 'max': 0.1},          # ±10cm
            'cop_z_m': {'min': -0.05, 'max': 0.05}         # ±5cm
        }
        
        # Test joint angles
        for joint in ['hip', 'knee', 'ankle']:
            for side in ['left', 'right', 'l', 'r']:
                col_name = f"{joint}_flexion_angle_{side}_rad"
                if col_name in data.columns:
                    angle_data = data[col_name].dropna()
                    
                    if len(angle_data) > 0:
                        min_val = angle_data.min()
                        max_val = angle_data.max()
                        mean_val = angle_data.mean()
                        
                        expected_range = expected_ranges.get(f"{joint}_flexion_angle", {'min': -3.14, 'max': 3.14})
                        
                        range_ok = (min_val >= expected_range['min'] - 0.5 and 
                                   max_val <= expected_range['max'] + 0.5)
                        
                        results['joint_angle_checks'][col_name] = {
                            'min': min_val,
                            'max': max_val,
                            'mean': mean_val,
                            'range_plausible': range_ok,
                            'expected_range': expected_range
                        }
                        
                        if not range_ok:
                            results['sign_convention_issues'].append(
                                f"{col_name}: Values outside plausible range. "
                                f"Found [{min_val:.2f}, {max_val:.2f}], "
                                f"expected ~[{expected_range['min']:.2f}, {expected_range['max']:.2f}]"
                            )
                        
                        # Check for sign convention issues (e.g., all negative hip flexion during walking)
                        if joint == 'hip' and max_val < 0:
                            results['sign_convention_issues'].append(
                                f"{col_name}: All negative values suggest possible sign convention error "
                                f"(hip should show positive flexion during walking)"
                            )
        
        # Test GRF sign conventions
        grf_columns = ['vertical_grf_N', 'ap_grf_N', 'ml_grf_N']
        for grf_col in grf_columns:
            if grf_col in data.columns:
                grf_data = data[grf_col].dropna()
                
                if len(grf_data) > 0:
                    min_val = grf_data.min()
                    max_val = grf_data.max()
                    mean_val = grf_data.mean()
                    
                    expected_range = expected_ranges.get(grf_col, {'min': -1000, 'max': 1000})
                    
                    range_ok = (min_val >= expected_range['min'] - 100 and 
                               max_val <= expected_range['max'] + 100)
                    
                    results['grf_checks'][grf_col] = {
                        'min': min_val,
                        'max': max_val,
                        'mean': mean_val,
                        'range_plausible': range_ok,
                        'expected_range': expected_range
                    }
                    
                    if not range_ok:
                        results['sign_convention_issues'].append(
                            f"{grf_col}: Values outside plausible range. "
                            f"Found [{min_val:.1f}, {max_val:.1f}], "
                            f"expected ~[{expected_range['min']}, {expected_range['max']}]"
                        )
                    
                    # Specific sign convention checks
                    if grf_col == 'vertical_grf_N' and mean_val < 0:
                        results['sign_convention_issues'].append(
                            f"{grf_col}: Negative mean value suggests possible sign error "
                            f"(vertical GRF should be positive upward)"
                        )
        
        # Test COP sign conventions
        cop_columns = ['cop_x_m', 'cop_y_m', 'cop_z_m']
        for cop_col in cop_columns:
            if cop_col in data.columns:
                cop_data = data[cop_col].dropna()
                
                if len(cop_data) > 0:
                    min_val = cop_data.min()
                    max_val = cop_data.max()
                    mean_val = cop_data.mean()
                    
                    expected_range = expected_ranges.get(cop_col, {'min': -1, 'max': 1})
                    
                    range_ok = (min_val >= expected_range['min'] - 0.05 and 
                               max_val <= expected_range['max'] + 0.05)
                    
                    results['cop_checks'][cop_col] = {
                        'min': min_val,
                        'max': max_val,
                        'mean': mean_val,
                        'range_plausible': range_ok,
                        'expected_range': expected_range
                    }
                    
                    if not range_ok:
                        results['sign_convention_issues'].append(
                            f"{cop_col}: Values outside plausible range. "
                            f"Found [{min_val:.3f}, {max_val:.3f}], "
                            f"expected ~[{expected_range['min']:.2f}, {expected_range['max']:.2f}]"
                        )
        
        print(f"  ✓ Joint angles checked: {len(results['joint_angle_checks'])}")
        print(f"  ✓ GRF variables checked: {len(results['grf_checks'])}")
        print(f"  ✓ COP variables checked: {len(results['cop_checks'])}")
        print(f"  ✗ Sign convention issues: {len(results['sign_convention_issues'])}")
        
        return results
    
    def test_markdown_validation_compliance(self, data: pd.DataFrame) -> Dict[str, any]:
        """
        Test compliance with markdown-based validation expectations.
        
        Args:
            data: DataFrame with biomechanical data
            
        Returns:
            Dict with test results
        """
        print("Testing Markdown Validation Compliance...")
        
        results = {
            'validation_rules_loaded': False,
            'task_validations': {},
            'overall_compliance': {},
            'errors': []
        }
        
        # Load validation expectations
        spec_file = Path("docs/standard_spec/validation_expectations.md")
        if not spec_file.exists():
            results['errors'].append(f"Validation expectations file not found: {spec_file}")
            return results
        
        try:
            validation_rules = self.markdown_parser.parse_file(str(spec_file))
            results['validation_rules_loaded'] = True
            print(f"  ✓ Loaded validation rules for {len(validation_rules)} tasks")
        except Exception as e:
            results['errors'].append(f"Error loading validation rules: {e}")
            return results
        
        # Determine which tasks are present in the data
        if 'task_name' in data.columns:
            unique_tasks = data['task_name'].unique()
            print(f"  ✓ Found {len(unique_tasks)} unique tasks in data")
        else:
            results['errors'].append("No task_name column found in data")
            return results
        
        # Validate each task
        total_task_rules = 0
        total_passed = 0
        total_failed = 0
        
        for task in unique_tasks:
            if task in validation_rules:
                task_data = data[data['task_name'] == task]
                task_result = self.markdown_parser.validate_data(task_data, task)
                
                results['task_validations'][task] = task_result
                total_task_rules += task_result['total_rules']
                total_passed += task_result['passed_rules']
                total_failed += task_result['failed_rules']
                
                print(f"    - {task}: {task_result['passed_rules']}/{task_result['total_rules']} rules passed ({task_result['success_rate']:.1%})")
            else:
                results['errors'].append(f"No validation rules found for task: {task}")
        
        # Overall compliance metrics
        overall_success_rate = total_passed / total_task_rules if total_task_rules > 0 else 0
        results['overall_compliance'] = {
            'total_rules_tested': total_task_rules,
            'total_passed': total_passed,
            'total_failed': total_failed,
            'success_rate': overall_success_rate,
            'tasks_tested': len(results['task_validations'])
        }
        
        print(f"  📊 Overall markdown compliance: {overall_success_rate:.1%} ({total_passed}/{total_task_rules} rules)")
        
        return results
    
    def create_test_dataset(self) -> pd.DataFrame:
        """Create a test dataset that should pass all compliance tests"""
        
        np.random.seed(42)  # For reproducible tests
        n_samples = 300  # 2 cycles × 150 points each
        
        # Create phase data (2 complete cycles)
        phase_l = np.concatenate([
            np.linspace(0, 99.9, 150),  # Cycle 1
            np.linspace(0, 99.9, 150)   # Cycle 2
        ])
        
        # Create compliant biomechanical data
        data = {
            'time_s': np.linspace(0, 3.0, n_samples),
            'phase_l': phase_l,
            'subject_id': ['S01'] * n_samples,
            'task_id': ['T001'] * n_samples,
            'task_name': ['level_walking'] * n_samples,
            
            # Joint angles (in radians, following OpenSim conventions)
            'hip_flexion_angle_left_rad': 0.3 + 0.5 * np.sin(2 * np.pi * phase_l / 100),
            'hip_flexion_angle_right_rad': 0.3 + 0.5 * np.sin(2 * np.pi * (phase_l + 50) / 100),
            # Knee flexion with motion capture error tolerance (allows -10° to +120° range)
            # Base pattern: mostly positive but some values near heel strike can be slightly negative
            'knee_flexion_angle_left_rad': 0.3 + 0.6 * np.maximum(0, np.sin(2 * np.pi * phase_l / 100)) + 0.02 * np.random.randn(n_samples),
            'knee_flexion_angle_right_rad': 0.3 + 0.6 * np.maximum(0, np.sin(2 * np.pi * (phase_l + 50) / 100)) + 0.02 * np.random.randn(n_samples),
            'ankle_flexion_angle_left_rad': 0.1 * np.sin(2 * np.pi * phase_l / 100),
            'ankle_flexion_angle_right_rad': 0.1 * np.sin(2 * np.pi * (phase_l + 50) / 100),
            
            # GRF data (in Newtons)
            'vertical_grf_N': 800 + 400 * np.sin(2 * np.pi * phase_l / 100)**2,
            'ap_grf_N': 100 * np.sin(4 * np.pi * phase_l / 100),
            'ml_grf_N': 20 * np.random.randn(n_samples),
            
            # COP data (in meters)
            'cop_x_m': 0.05 * np.sin(2 * np.pi * phase_l / 100),
            'cop_y_m': 0.02 * np.random.randn(n_samples),
            'cop_z_m': 0.01 * np.random.randn(n_samples),
            
            # Metadata (monolithic format example)
            'age': [25] * n_samples,
            'gender': ['male'] * n_samples,
            'height': [1.75] * n_samples,
            'body_mass': [70.0] * n_samples,
            'walking_speed_m_s': [1.3] * n_samples,
            
            # Quality flags
            'is_outlier': [False] * n_samples
        }
        
        return pd.DataFrame(data)
    
    def run_full_compliance_test(self, data: Optional[pd.DataFrame] = None) -> Dict[str, any]:
        """
        Run the complete specification compliance test suite.
        
        Args:
            data: Optional DataFrame to test. If None, uses generated test data.
            
        Returns:
            Dict with comprehensive test results
        """
        if data is None:
            print("Creating compliant test dataset...")
            data = self.create_test_dataset()
        
        print(f"\nRunning Specification Compliance Test Suite on {len(data)} samples...")
        print("=" * 60)
        
        # Test 1: Variable naming convention
        naming_results = self.test_variable_naming_convention(data.columns.tolist())
        
        # Test 2: Phase calculation expectations
        phase_results = self.test_phase_calculation_expectations(data)
        
        # Test 3: Sign convention adherence
        sign_results = self.test_sign_convention_adherence(data)
        
        # Test 4: Markdown validation compliance
        markdown_results = self.test_markdown_validation_compliance(data)
        
        # Compile overall results
        overall_results = {
            'test_timestamp': pd.Timestamp.now().isoformat(),
            'dataset_info': {
                'total_rows': len(data),
                'total_columns': len(data.columns),
                'subjects': data['subject_id'].nunique() if 'subject_id' in data.columns else 0,
                'tasks': data['task_id'].nunique() if 'task_id' in data.columns else 0
            },
            'naming_convention': naming_results,
            'phase_calculation': phase_results,
            'sign_conventions': sign_results,
            'markdown_validation': markdown_results,
            'overall_compliance': {}
        }
        
        # Calculate overall compliance metrics
        total_issues = (
            len(naming_results['non_compliant_columns']) +
            len(phase_results['compliance_issues']) +
            len(sign_results['sign_convention_issues']) +
            len(markdown_results['errors'])
        )
        
        overall_results['overall_compliance'] = {
            'total_tests_run': 4,
            'total_issues_found': total_issues,
            'naming_compliance_rate': naming_results['compliance_rate'],
            'phase_issues_count': len(phase_results['compliance_issues']),
            'sign_issues_count': len(sign_results['sign_convention_issues']),
            'markdown_issues_count': len(markdown_results['errors']),
            'markdown_success_rate': markdown_results.get('overall_compliance', {}).get('success_rate', 0),
            'overall_pass': total_issues == 0
        }
        
        print("\n" + "=" * 60)
        print("SPECIFICATION COMPLIANCE TEST SUMMARY")
        print("=" * 60)
        print(f"📊 Overall compliance: {'✅ PASS' if total_issues == 0 else '❌ FAIL'}")
        print(f"📝 Total issues found: {total_issues}")
        print(f"📏 Naming compliance: {naming_results['compliance_rate']:.1%}")
        print(f"⏱️  Phase issues: {len(phase_results['compliance_issues'])}")
        print(f"📐 Sign convention issues: {len(sign_results['sign_convention_issues'])}")
        print(f"📋 Markdown validation: {markdown_results.get('overall_compliance', {}).get('success_rate', 0):.1%}")
        
        return overall_results
    
    def save_compliance_report(self, results: Dict, output_path: str):
        """Save compliance test results to files"""
        
        # Create summary report
        with open(output_path, 'w') as f:
            f.write("SPECIFICATION COMPLIANCE TEST REPORT\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Test timestamp: {results['test_timestamp']}\n")
            f.write(f"Dataset: {results['dataset_info']['total_rows']} rows, {results['dataset_info']['total_columns']} columns\n\n")
            
            # Overall compliance
            f.write("OVERALL COMPLIANCE\n")
            f.write("-" * 20 + "\n")
            overall = results['overall_compliance']
            f.write(f"Result: {'PASS' if overall['overall_pass'] else 'FAIL'}\n")
            f.write(f"Total issues: {overall['total_issues_found']}\n")
            f.write(f"Naming compliance: {overall['naming_compliance_rate']:.1%}\n\n")
            
            # Detailed issues
            if overall['total_issues_found'] > 0:
                f.write("DETAILED ISSUES\n")
                f.write("-" * 15 + "\n")
                
                # Naming issues
                naming = results['naming_convention']
                if naming['non_compliant_columns']:
                    f.write("Naming Convention Issues:\n")
                    for issue in naming['non_compliant_columns']:
                        f.write(f"  - {issue['column']}: {', '.join(issue['issues'])}\n")
                    f.write("\n")
                
                # Phase issues
                phase = results['phase_calculation']
                if phase['compliance_issues']:
                    f.write("Phase Calculation Issues:\n")
                    for issue in phase['compliance_issues']:
                        f.write(f"  - {issue}\n")
                    f.write("\n")
                
                # Sign convention issues
                sign = results['sign_conventions']
                if sign['sign_convention_issues']:
                    f.write("Sign Convention Issues:\n")
                    for issue in sign['sign_convention_issues']:
                        f.write(f"  - {issue}\n")
        
        print(f"\n📄 Compliance report saved to: {output_path}")


def test_gtech_datasets():
    """Test GTech 2023 datasets for specification compliance"""
    
    test_suite = SpecComplianceTestSuite()
    
    # Find all GTech parquet files
    converted_dir = Path("converted_datasets")
    gtech_files = list(converted_dir.glob("gtech_2023_time*.parquet"))
    
    if not gtech_files:
        print("❌ No GTech 2023 datasets found in converted_datasets/")
        return None
    
    print(f"Found {len(gtech_files)} GTech 2023 datasets to test")
    
    all_results = {}
    output_dir = Path("validation_reports")
    output_dir.mkdir(exist_ok=True)
    
    for parquet_file in gtech_files:
        print(f"\n{'='*60}")
        print(f"Testing: {parquet_file.name}")
        print(f"{'='*60}")
        
        try:
            # Load the dataset
            data = pd.read_parquet(parquet_file)
            print(f"Loaded {len(data)} rows, {len(data.columns)} columns")
            
            # Run compliance tests
            results = test_suite.run_full_compliance_test(data)
            results['dataset_file'] = str(parquet_file.name)
            
            # Save individual report
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            report_name = parquet_file.stem + f"_compliance_{timestamp}.txt"
            report_path = output_dir / report_name
            
            test_suite.save_compliance_report(results, str(report_path))
            
            all_results[parquet_file.name] = results
            
        except Exception as e:
            print(f"❌ Error testing {parquet_file.name}: {e}")
            all_results[parquet_file.name] = {"error": str(e)}
    
    # Create summary report
    create_gtech_summary_report(all_results, output_dir)
    
    return all_results

def create_gtech_summary_report(all_results: Dict, output_dir: Path):
    """Create a summary report for all GTech dataset compliance tests"""
    
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    summary_path = output_dir / f"gtech_2023_compliance_summary_{timestamp}.txt"
    
    with open(summary_path, 'w') as f:
        f.write("GTECH 2023 DATASETS - SPECIFICATION COMPLIANCE SUMMARY\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Test timestamp: {pd.Timestamp.now().isoformat()}\n")
        f.write(f"Total datasets tested: {len(all_results)}\n\n")
        
        # Summary statistics
        total_pass = 0
        total_fail = 0
        
        for dataset_name, results in all_results.items():
            if "error" in results:
                total_fail += 1
            elif results.get('overall_compliance', {}).get('overall_pass', False):
                total_pass += 1
            else:
                total_fail += 1
        
        f.write("SUMMARY STATISTICS\n")
        f.write("-" * 20 + "\n")
        f.write(f"Datasets passed: {total_pass}\n")
        f.write(f"Datasets failed: {total_fail}\n")
        f.write(f"Success rate: {total_pass/(total_pass+total_fail)*100:.1f}%\n\n")
        
        # Individual dataset results
        f.write("INDIVIDUAL DATASET RESULTS\n")
        f.write("-" * 30 + "\n")
        
        for dataset_name, results in all_results.items():
            if "error" in results:
                f.write(f"❌ {dataset_name}: ERROR - {results['error']}\n")
            else:
                overall = results.get('overall_compliance', {})
                status = "✅ PASS" if overall.get('overall_pass', False) else "❌ FAIL"
                total_issues = overall.get('total_issues_found', 'unknown')
                naming_rate = overall.get('naming_compliance_rate', 0) * 100
                
                f.write(f"{status} {dataset_name}:\n")
                f.write(f"  - Issues: {total_issues}\n")
                f.write(f"  - Naming compliance: {naming_rate:.1f}%\n")
                f.write(f"  - Phase issues: {overall.get('phase_issues_count', 0)}\n")
                f.write(f"  - Sign issues: {overall.get('sign_issues_count', 0)}\n\n")
        
        # Common issues analysis
        all_naming_issues = []
        all_phase_issues = []
        all_sign_issues = []
        
        for dataset_name, results in all_results.items():
            if "error" not in results:
                # Collect naming issues
                naming = results.get('naming_convention', {})
                for issue in naming.get('non_compliant_columns', []):
                    all_naming_issues.extend(issue.get('issues', []))
                
                # Collect phase issues
                phase = results.get('phase_calculation', {})
                all_phase_issues.extend(phase.get('compliance_issues', []))
                
                # Collect sign issues
                sign = results.get('sign_conventions', {})
                all_sign_issues.extend(sign.get('sign_convention_issues', []))
        
        if all_naming_issues or all_phase_issues or all_sign_issues:
            f.write("COMMON ISSUES ANALYSIS\n")
            f.write("-" * 25 + "\n")
            
            if all_naming_issues:
                f.write("Most common naming issues:\n")
                from collections import Counter
                issue_counts = Counter(all_naming_issues)
                for issue, count in issue_counts.most_common(5):
                    f.write(f"  - {issue} ({count} occurrences)\n")
                f.write("\n")
            
            if all_phase_issues:
                f.write("Phase calculation issues found:\n")
                for issue in set(all_phase_issues):
                    f.write(f"  - {issue}\n")
                f.write("\n")
            
            if all_sign_issues:
                f.write("Sign convention issues found:\n")
                for issue in set(all_sign_issues):
                    f.write(f"  - {issue}\n")
    
    print(f"\n📊 GTech summary report saved to: {summary_path}")

def main():
    """Main function to run the specification compliance test suite"""
    
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "gtech":
        # Test GTech datasets
        results = test_gtech_datasets()
    else:
        # Create test suite
        test_suite = SpecComplianceTestSuite()
        
        # Run tests with generated compliant data
        print("Testing with generated compliant dataset...")
        results = test_suite.run_full_compliance_test()
        
        # Save results
        output_dir = Path("validation_reports")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        report_path = output_dir / f"spec_compliance_test_{timestamp}.txt"
        
        test_suite.save_compliance_report(results, str(report_path))
    
    # Return results for use by other scripts
    return results


if __name__ == "__main__":
    main()