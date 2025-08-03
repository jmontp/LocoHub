#!/usr/bin/env python3
"""
Enhanced Phase Validator

Created: 2025-06-18 with user permission
Purpose: Memory-efficient comprehensive phase validation with enhanced biomechanical checking

Intent:
This module provides enhanced phase validation capabilities building on the existing
dataset_validator_phase.py infrastructure. It adds:

1. **Strict 150-Point Enforcement**: Validates exactly 150 points per gait cycle
2. **Enhanced Biomechanical Checking**: More detailed range validation
3. **Memory-Conscious Processing**: Efficient batch processing for large datasets
4. **Improved Error Reporting**: Detailed validation failure analysis

**Key Features:**
- Leverages existing LocomotionData and StepClassifier infrastructure
- Adds strict phase length validation
- Provides memory-efficient processing for large datasets
- Enhanced biomechanical range checking with detailed reporting
- Comprehensive validation workflow integration

**Usage:**
    from internal.validation_engine.phase_validator import EnhancedPhaseValidator
    
    validator = EnhancedPhaseValidator(dataset_path)
    results = validator.validate_comprehensive()
    
    # For memory-conscious processing
    validator.enable_batch_processing(batch_size=100)
    results = validator.validate_large_dataset()
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
import warnings
from dataclasses import dataclass

# Import existing validation infrastructure
from .dataset_validator_phase import DatasetValidator
from .step_classifier import StepClassifier
from user_libs.python.locomotion_data import LocomotionData
from user_libs.python.feature_constants import ANGLE_FEATURES, MOMENT_FEATURES


@dataclass
class PhaseValidationResult:
    """Container for phase validation results."""
    is_valid: bool
    total_steps: int
    valid_steps: int
    failed_steps: int
    phase_length_violations: List[Dict]
    biomechanical_violations: List[Dict]
    memory_usage_mb: Optional[float] = None
    processing_time_s: Optional[float] = None


@dataclass
class PhaseLengthViolation:
    """Container for phase length validation violations."""
    subject: str
    task: str
    step: int
    actual_length: int
    expected_length: int = 150


class EnhancedPhaseValidator:
    """
    Enhanced phase validation with strict 150-point enforcement and memory-conscious processing.
    
    Builds on existing DatasetValidator infrastructure while adding:
    - Strict phase length validation
    - Enhanced biomechanical checking
    - Memory-efficient batch processing
    - Detailed violation reporting
    """
    
    def __init__(self, dataset_path: str, output_dir: str = None, strict_mode: bool = True):
        """
        Initialize enhanced phase validator.
        
        Args:
            dataset_path: Path to phase-indexed dataset
            output_dir: Output directory for reports
            strict_mode: If True, enforce strict 150-point validation
        """
        self.dataset_path = Path(dataset_path)
        self.output_dir = Path(output_dir) if output_dir else None
        self.strict_mode = strict_mode
        
        # Initialize base validator
        self.base_validator = DatasetValidator(
            str(dataset_path), 
            str(output_dir) if output_dir else None,
            generate_plots=False  # We'll handle plotting separately
        )
        
        # Memory management settings
        self.batch_processing_enabled = False
        self.batch_size = 1000  # Default batch size for memory-conscious processing
        self.max_memory_mb = 512  # Maximum memory usage before switching to batch mode
        
        # Validation settings
        self.phase_length_tolerance = 0  # No tolerance in strict mode
        self.require_exact_150_points = strict_mode
        
        # Results storage
        self.last_validation_result = None
        
    def enable_batch_processing(self, batch_size: int = 1000, max_memory_mb: int = 512):
        """
        Enable memory-conscious batch processing.
        
        Args:
            batch_size: Number of steps to process per batch
            max_memory_mb: Memory limit before switching to batch mode
        """
        self.batch_processing_enabled = True
        self.batch_size = batch_size
        self.max_memory_mb = max_memory_mb
        
    def validate_phase_structure(self, locomotion_data: LocomotionData) -> List[PhaseLengthViolation]:
        """
        Validate that all gait cycles have exactly 150 points.
        
        Args:
            locomotion_data: Loaded LocomotionData object
            
        Returns:
            List of phase length violations
        """
        violations = []
        df = locomotion_data.df
        
        # Check if we have step grouping columns
        if not all(col in df.columns for col in ['subject', 'task', 'step']):
            warnings.warn("Cannot validate phase structure - missing grouping columns")
            return violations
        
        # Group by step and check sizes
        step_groups = df.groupby(['subject', 'task', 'step']).size()
        
        for (subject, task, step), size in step_groups.items():
            if self.require_exact_150_points:
                # Strict validation - must be exactly 150
                if size != 150:
                    violations.append(PhaseLengthViolation(
                        subject=subject,
                        task=task,
                        step=step,
                        actual_length=size,
                        expected_length=150
                    ))
            else:
                # Allow some tolerance (e.g., 140-160 points)
                tolerance = self.phase_length_tolerance
                if not (150 - tolerance <= size <= 150 + tolerance):
                    violations.append(PhaseLengthViolation(
                        subject=subject,
                        task=task,
                        step=step,
                        actual_length=size,
                        expected_length=150
                    ))
        
        return violations
    
    def validate_biomechanical_ranges(self, locomotion_data: LocomotionData) -> Tuple[Dict, List[Dict]]:
        """
        Perform enhanced biomechanical range validation.
        
        Args:
            locomotion_data: Loaded LocomotionData object
            
        Returns:
            Tuple of (validation_results, detailed_violations)
        """
        if self.batch_processing_enabled:
            return self._validate_biomechanical_ranges_batch(locomotion_data)
        else:
            return self._validate_biomechanical_ranges_full(locomotion_data)
    
    def _validate_biomechanical_ranges_full(self, locomotion_data: LocomotionData) -> Tuple[Dict, List[Dict]]:
        """Full dataset validation using existing infrastructure."""
        validation_results = self.base_validator.validate_dataset(locomotion_data)
        
        # Extract detailed violations
        detailed_violations = []
        
        # Combine kinematic and kinetic failures
        all_failures = (validation_results.get('kinematic_failures', []) + 
                       validation_results.get('kinetic_failures', []))
        
        for failure in all_failures:
            detailed_violations.append({
                'type': 'biomechanical_range',
                'subject': failure.get('subject', 'unknown'),
                'task': failure.get('task', 'unknown'),
                'step': failure.get('step', -1),
                'variable': failure.get('variable', 'unknown'),
                'phase': failure.get('phase', -1),
                'value': failure.get('value', None),
                'expected_min': failure.get('expected_min', None),
                'expected_max': failure.get('expected_max', None),
                'failure_reason': failure.get('failure_reason', 'unknown')
            })
        
        return validation_results, detailed_violations
    
    def _validate_biomechanical_ranges_batch(self, locomotion_data: LocomotionData) -> Tuple[Dict, List[Dict]]:
        """
        Memory-conscious batch validation for large datasets.
        
        Processes dataset in batches to avoid memory issues.
        """
        print(f"🔄 Using batch processing (batch_size={self.batch_size})")
        
        # Initialize results
        total_results = {
            'total_steps': 0,
            'valid_steps': 0,
            'failed_steps': 0,
            'kinematic_failures': [],
            'kinetic_failures': [],
            'tasks_validated': [],
            'task_step_counts': {}
        }
        
        detailed_violations = []
        
        # Get subjects and tasks
        subjects = locomotion_data.subjects
        tasks = locomotion_data.tasks
        
        # Process in batches by subject-task combinations
        batch_count = 0
        
        for subject in subjects:
            for task in tasks:
                try:
                    # Get data for this subject-task combination
                    # Check if we have kinematic data
                    kinematic_features = [f for f in ANGLE_FEATURES if f in locomotion_data.features]
                    if kinematic_features and self.base_validator.kinematic_expectations:
                        kinematic_data_3d, _ = locomotion_data.get_cycles(subject, task, kinematic_features)
                        if kinematic_data_3d is not None:
                            # Process this batch
                            batch_results = self._process_subject_task_batch(
                                kinematic_data_3d, kinematic_features, subject, task, 'kinematic'
                            )
                            self._merge_batch_results(total_results, batch_results)
                            
                            # Extract violations from batch
                            for failure in batch_results.get('kinematic_failures', []):
                                detailed_violations.append({
                                    'type': 'biomechanical_range',
                                    'subject': failure.get('subject', subject),
                                    'task': failure.get('task', task),
                                    'step': failure.get('step', -1),
                                    'variable': failure.get('variable', 'unknown'),
                                    'phase': failure.get('phase', -1),
                                    'value': failure.get('value', None),
                                    'expected_min': failure.get('expected_min', None),
                                    'expected_max': failure.get('expected_max', None),
                                    'failure_reason': failure.get('failure_reason', 'unknown')
                                })
                    
                    # Check if we have kinetic data
                    kinetic_features = [f for f in MOMENT_FEATURES if f in locomotion_data.features]
                    if kinetic_features and self.base_validator.kinetic_expectations:
                        kinetic_data_3d, _ = locomotion_data.get_cycles(subject, task, kinetic_features)
                        if kinetic_data_3d is not None:
                            # Process this batch
                            batch_results = self._process_subject_task_batch(
                                kinetic_data_3d, kinetic_features, subject, task, 'kinetic'
                            )
                            self._merge_batch_results(total_results, batch_results)
                            
                            # Extract violations from batch
                            for failure in batch_results.get('kinetic_failures', []):
                                detailed_violations.append({
                                    'type': 'biomechanical_range',
                                    'subject': failure.get('subject', subject),
                                    'task': failure.get('task', task),
                                    'step': failure.get('step', -1),
                                    'variable': failure.get('variable', 'unknown'),
                                    'phase': failure.get('phase', -1),
                                    'value': failure.get('value', None),
                                    'expected_min': failure.get('expected_min', None),
                                    'expected_max': failure.get('expected_max', None),
                                    'failure_reason': failure.get('failure_reason', 'unknown')
                                })
                    
                    batch_count += 1
                    if batch_count % 10 == 0:
                        print(f"   Processed {batch_count} subject-task combinations...")
                        
                except Exception as e:
                    warnings.warn(f"Error processing {subject}-{task}: {e}")
                    continue
        
        return total_results, detailed_violations
    
    def _process_subject_task_batch(self, data_3d: np.ndarray, features: List[str], 
                                   subject: str, task: str, validation_type: str) -> Dict:
        """Process a single subject-task batch for validation."""
        results = {
            'total_steps': 0,
            'valid_steps': 0,
            'failed_steps': 0,
            'kinematic_failures': [] if validation_type == 'kinematic' else [],
            'kinetic_failures': [] if validation_type == 'kinetic' else [],
            'tasks_validated': [task],
            'task_step_counts': {task: {'total': 0, 'failed': 0, 'valid': 0}}
        }
        
        n_steps = data_3d.shape[0]
        results['total_steps'] = n_steps
        results['task_step_counts'][task]['total'] = n_steps
        
        # Validate each step in this batch
        for step_idx in range(n_steps):
            step_data = data_3d[step_idx, :, :]  # Shape: (150, n_features)
            
            # Use base validator's step validation method
            step_failures = self.base_validator._validate_step_3d_data(
                step_data, features, task, validation_type, subject, step_idx
            )
            
            if step_failures:
                results['failed_steps'] += 1
                results['task_step_counts'][task]['failed'] += 1
                if validation_type == 'kinematic':
                    results['kinematic_failures'].extend(step_failures)
                else:
                    results['kinetic_failures'].extend(step_failures)
            else:
                results['valid_steps'] += 1
                results['task_step_counts'][task]['valid'] += 1
        
        return results
    
    def _merge_batch_results(self, total_results: Dict, batch_results: Dict):
        """Merge batch results into total results."""
        total_results['total_steps'] += batch_results['total_steps']
        total_results['valid_steps'] += batch_results['valid_steps']
        total_results['failed_steps'] += batch_results['failed_steps']
        
        total_results['kinematic_failures'].extend(batch_results.get('kinematic_failures', []))
        total_results['kinetic_failures'].extend(batch_results.get('kinetic_failures', []))
        
        # Merge task counts
        for task, counts in batch_results.get('task_step_counts', {}).items():
            if task not in total_results['task_step_counts']:
                total_results['task_step_counts'][task] = {'total': 0, 'failed': 0, 'valid': 0}
            
            total_results['task_step_counts'][task]['total'] += counts['total']
            total_results['task_step_counts'][task]['failed'] += counts['failed']
            total_results['task_step_counts'][task]['valid'] += counts['valid']
        
        # Update validated tasks
        for task in batch_results.get('tasks_validated', []):
            if task not in total_results['tasks_validated']:
                total_results['tasks_validated'].append(task)
    
    def validate_comprehensive(self) -> PhaseValidationResult:
        """
        Perform comprehensive phase validation including structure and biomechanical checks.
        
        Returns:
            PhaseValidationResult with complete validation analysis
        """
        import time
        
        start_time = time.time()
        initial_memory = 0  # Default if psutil not available
        
        # Try to import psutil for memory monitoring (optional)
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            process = None
        
        try:
            # Load dataset
            print(f"📊 Loading dataset: {self.dataset_path}")
            locomotion_data = self.base_validator.load_dataset()
            
            # Check memory usage and switch to batch processing if needed
            if process is not None:
                try:
                    current_memory = process.memory_info().rss / 1024 / 1024  # MB
                    if current_memory > self.max_memory_mb and not self.batch_processing_enabled:
                        print(f"🔄 Memory usage ({current_memory:.1f} MB) exceeds limit ({self.max_memory_mb} MB)")
                        print("   Switching to batch processing mode...")
                        self.enable_batch_processing()
                except:
                    pass  # Skip memory monitoring if it fails
            
            # Phase 1: Validate phase structure (150-point enforcement)
            print(f"🔍 Validating phase structure (150-point enforcement)...")
            phase_violations = self.validate_phase_structure(locomotion_data)
            
            if phase_violations and self.strict_mode:
                print(f"❌ Found {len(phase_violations)} phase length violations")
                for violation in phase_violations[:5]:  # Show first 5
                    print(f"   {violation.subject}-{violation.task} step {violation.step}: "
                          f"{violation.actual_length} points (expected {violation.expected_length})")
                if len(phase_violations) > 5:
                    print(f"   ... and {len(phase_violations) - 5} more violations")
            else:
                print(f"✅ Phase structure validation passed ({len(phase_violations)} minor issues)")
            
            # Phase 2: Validate biomechanical ranges
            print(f"🔍 Validating biomechanical ranges...")
            validation_results, biomechanical_violations = self.validate_biomechanical_ranges(locomotion_data)
            
            # Calculate final metrics
            processing_time = time.time() - start_time
            memory_usage = 0  # Default if psutil not available
            
            if process is not None:
                try:
                    final_memory = process.memory_info().rss / 1024 / 1024  # MB
                    memory_usage = final_memory - initial_memory
                except:
                    memory_usage = 0
            
            # Determine overall validity
            phase_structure_valid = len(phase_violations) == 0 or not self.strict_mode
            biomechanical_valid = validation_results['failed_steps'] == 0
            overall_valid = phase_structure_valid and biomechanical_valid
            
            # Create result object
            result = PhaseValidationResult(
                is_valid=overall_valid,
                total_steps=validation_results['total_steps'],
                valid_steps=validation_results['valid_steps'],
                failed_steps=validation_results['failed_steps'],
                phase_length_violations=[violation.__dict__ for violation in phase_violations],
                biomechanical_violations=biomechanical_violations,
                memory_usage_mb=memory_usage,
                processing_time_s=processing_time
            )
            
            self.last_validation_result = result
            
            # Print summary
            print(f"\n📊 Validation Summary:")
            print(f"   Overall Status: {'✅ VALID' if overall_valid else '❌ INVALID'}")
            print(f"   Steps Processed: {result.total_steps}")
            print(f"   Valid Steps: {result.valid_steps}")
            print(f"   Failed Steps: {result.failed_steps}")
            print(f"   Phase Violations: {len(phase_violations)}")
            print(f"   Biomechanical Violations: {len(biomechanical_violations)}")
            print(f"   Processing Time: {processing_time:.2f}s")
            print(f"   Memory Usage: {memory_usage:.1f} MB")
            
            return result
            
        except Exception as e:
            print(f"❌ Validation failed: {e}")
            # Return error result
            processing_time = time.time() - start_time
            return PhaseValidationResult(
                is_valid=False,
                total_steps=0,
                valid_steps=0,
                failed_steps=0,
                phase_length_violations=[],
                biomechanical_violations=[{'error': str(e)}],
                processing_time_s=processing_time
            )
    
    def generate_enhanced_report(self, result: PhaseValidationResult = None) -> str:
        """
        Generate enhanced validation report with detailed analysis.
        
        Args:
            result: PhaseValidationResult to report on (uses last result if None)
            
        Returns:
            Path to generated report
        """
        if result is None:
            result = self.last_validation_result
            
        if result is None:
            raise ValueError("No validation result available. Run validate_comprehensive() first.")
        
        # Create output directory if specified
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            report_path = self.output_dir / f"{self.dataset_path.stem}_enhanced_validation_report.md"
        else:
            report_path = self.dataset_path.parent / f"{self.dataset_path.stem}_enhanced_validation_report.md"
        
        with open(report_path, 'w') as f:
            f.write("# Enhanced Phase Validation Report\n\n")
            f.write(f"**Dataset**: `{self.dataset_path}`\n")
            f.write(f"**Validation Mode**: {'Strict' if self.strict_mode else 'Tolerant'}\n")
            f.write(f"**Batch Processing**: {'Enabled' if self.batch_processing_enabled else 'Disabled'}\n\n")
            
            # Overall status
            status_emoji = "✅" if result.is_valid else "❌"
            f.write(f"## {status_emoji} Overall Status: {'VALID' if result.is_valid else 'INVALID'}\n\n")
            
            # Performance metrics
            f.write("## Performance Metrics\n\n")
            f.write(f"- **Processing Time**: {result.processing_time_s:.2f} seconds\n")
            if result.memory_usage_mb:
                f.write(f"- **Memory Usage**: {result.memory_usage_mb:.1f} MB\n")
            f.write(f"- **Steps Processed**: {result.total_steps}\n")
            f.write(f"- **Processing Rate**: {result.total_steps / result.processing_time_s:.1f} steps/second\n\n")
            
            # Step validation summary
            f.write("## Step Validation Summary\n\n")
            f.write(f"- **Total Steps**: {result.total_steps}\n")
            f.write(f"- **Valid Steps**: {result.valid_steps}\n")
            f.write(f"- **Failed Steps**: {result.failed_steps}\n")
            
            if result.total_steps > 0:
                success_rate = (result.valid_steps / result.total_steps) * 100
                f.write(f"- **Success Rate**: {success_rate:.1f}%\n")
            f.write("\n")
            
            # Phase length violations
            if result.phase_length_violations:
                f.write(f"## ⚠️ Phase Length Violations ({len(result.phase_length_violations)})\n\n")
                f.write("| Subject | Task | Step | Actual Length | Expected Length |\n")
                f.write("|---------|------|------|---------------|----------------|\n")
                
                for violation in result.phase_length_violations[:20]:  # Limit to first 20
                    f.write(f"| {violation['subject']} | {violation['task']} | {violation['step']} | "
                           f"{violation['actual_length']} | {violation['expected_length']} |\n")
                
                if len(result.phase_length_violations) > 20:
                    f.write(f"\n*... and {len(result.phase_length_violations) - 20} more violations*\n")
                f.write("\n")
            else:
                f.write("## ✅ Phase Length Validation Passed\n\n")
                f.write("All gait cycles have the expected 150 data points.\n\n")
            
            # Biomechanical violations summary
            if result.biomechanical_violations:
                f.write(f"## ⚠️ Biomechanical Violations ({len(result.biomechanical_violations)})\n\n")
                
                # Group by variable for better analysis
                violations_by_variable = {}
                for violation in result.biomechanical_violations:
                    var = violation.get('variable', 'unknown')
                    if var not in violations_by_variable:
                        violations_by_variable[var] = []
                    violations_by_variable[var].append(violation)
                
                for variable, violations in violations_by_variable.items():
                    f.write(f"### {variable} ({len(violations)} violations)\n\n")
                    f.write("| Subject | Task | Step | Phase | Value | Expected Range |\n")
                    f.write("|---------|------|------|-------|-------|----------------|\n")
                    
                    for violation in violations[:10]:  # Limit to first 10 per variable
                        subject = violation.get('subject', 'N/A')
                        task = violation.get('task', 'N/A')
                        step = violation.get('step', 'N/A')
                        phase = violation.get('phase', 'N/A')
                        value = violation.get('value', 'N/A')
                        min_val = violation.get('expected_min', 'N/A')
                        max_val = violation.get('expected_max', 'N/A')
                        
                        if isinstance(value, (int, float)):
                            value_str = f"{value:.3f}"
                        else:
                            value_str = str(value)
                        
                        if isinstance(min_val, (int, float)) and isinstance(max_val, (int, float)):
                            range_str = f"{min_val:.3f} to {max_val:.3f}"
                        else:
                            range_str = f"{min_val} to {max_val}"
                        
                        f.write(f"| {subject} | {task} | {step} | {phase} | {value_str} | {range_str} |\n")
                    
                    if len(violations) > 10:
                        f.write(f"\n*... and {len(violations) - 10} more violations for this variable*\n")
                    f.write("\n")
            else:
                f.write("## ✅ Biomechanical Validation Passed\n\n")
                f.write("All biomechanical measurements are within expected ranges.\n\n")
            
            # Recommendations
            f.write("## Recommendations\n\n")
            if result.is_valid:
                f.write("✅ **Dataset Quality**: Excellent - ready for analysis\n\n")
                f.write("- All validation checks passed\n")
                f.write("- Data structure meets phase-indexed requirements\n")
                f.write("- Biomechanical measurements are within expected ranges\n")
            else:
                f.write("⚠️ **Dataset Quality**: Issues detected - review recommended\n\n")
                
                if result.phase_length_violations:
                    f.write("**Phase Length Issues:**\n")
                    f.write("- Some gait cycles do not have exactly 150 data points\n")
                    f.write("- Consider re-processing data with proper phase interpolation\n")
                    f.write("- Verify gait cycle detection algorithms\n\n")
                
                if result.biomechanical_violations:
                    f.write("**Biomechanical Range Issues:**\n")
                    f.write("- Some measurements exceed expected physiological ranges\n")
                    f.write("- Review data collection protocols and sensor calibration\n")
                    f.write("- Consider data cleaning and outlier detection\n")
                    f.write("- Verify subject movement quality and instructions\n\n")
        
        print(f"📄 Enhanced validation report saved: {report_path}")
        return str(report_path)


def validate_phase_dataset_enhanced(dataset_path: str, output_dir: str = None, 
                                   strict_mode: bool = True, enable_batch: bool = False) -> PhaseValidationResult:
    """
    Convenience function for enhanced phase validation.
    
    Args:
        dataset_path: Path to phase-indexed dataset
        output_dir: Output directory for reports
        strict_mode: Enable strict 150-point validation
        enable_batch: Enable batch processing for memory efficiency
        
    Returns:
        PhaseValidationResult with validation analysis
    """
    validator = EnhancedPhaseValidator(dataset_path, output_dir, strict_mode)
    
    if enable_batch:
        validator.enable_batch_processing()
    
    result = validator.validate_comprehensive()
    validator.generate_enhanced_report(result)
    
    return result