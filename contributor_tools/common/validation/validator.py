#!/usr/bin/env python3
"""
Simplified Validation System for Locomotion Data

Core validation functionality without unnecessary complexity.
Focuses solely on checking if biomechanical data meets specifications.
"""

import os
import numpy as np
import pandas as pd
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any, Set

# Import configuration manager (now in contributor_tools/common/)
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from contributor_tools.common.config_manager import ValidationConfigManager
from locohub import LocomotionData
from locohub.feature_constants import CANONICAL_COLUMN_GROUPS


# Broad structural guardrails for time-domain data. These intentionally catch
# unit/sign explosions and acquisition corruption, not normal biomechanical
# variability; phase-specific quality ranges remain in the YAML configuration.
TIME_STRUCTURAL_ABS_LIMITS = {
    'joint_angles': 2 * np.pi,
    'segment_angles': 2 * np.pi,
    'joint_velocities': 100.0,
    'segment_velocities': 100.0,
    'joint_accelerations': 10_000.0,
    'moments': 5_000.0,
    'moments_normalized': 20.0,
    'assistance_moments': 20.0,
    'biological_moments': 20.0,
    'grf': 10_000.0,
    'grf_normalized': 10.0,
    'cop': 5.0,
    'emg_mvc': 1_000.0,
    'emg_peak': 1_000.0,
}


# ============================================================================
# SIMPLIFIED VALIDATOR
# ============================================================================

@dataclass
class TaskValidationDetails:
    """Rich validation information for a single task."""

    failing_features: Dict[int, List[str]]
    per_variable_failures: Dict[str, List[int]]
    total_strides: int
    validated_variables: List[str]
    global_passing_strides: Set[int]
    phase_indices: Dict[int, int]


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
    
    def __init__(
        self,
        config_path: Optional[Path] = None,
        time_batch_size: Optional[int] = None,
        time_column_chunk_size: Optional[int] = None,
    ):
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

        # Keep large time-domain checks bounded even when a parquet file has one
        # enormous row group. Environment overrides are useful on shared hosts.
        self.time_batch_size = time_batch_size or int(
            os.environ.get('LOCOHUB_VALIDATION_BATCH_ROWS', '16384')
        )
        self.time_column_chunk_size = time_column_chunk_size or int(
            os.environ.get('LOCOHUB_VALIDATION_COLUMN_CHUNK', '8')
        )
        if self.time_batch_size < 1 or self.time_column_chunk_size < 1:
            raise ValueError('Time validation batch and column chunk sizes must be positive')
        
    def validate(
        self,
        dataset_path: str,
        ignore_features: List[str] = None,
        retain_loaded_data: bool = False,
    ) -> Dict[str, Any]:
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
        columns = self._dataset_columns(dataset_path)
        if 'phase_ipsi' not in columns and 'time_s' in columns:
            return self._validate_time_dataset(dataset_path)

        # Load phase-indexed data with the proper phase column name.
        locomotion_data = LocomotionData(dataset_path, phase_col='phase_ipsi')

        result = self.validate_dataset(
            locomotion_data=locomotion_data,
            ignore_features=ignore_features
        )

        # Ensure dataset name is populated for compatibility
        result['stats']['dataset'] = Path(dataset_path).stem
        if retain_loaded_data:
            # Internal handoff used by the CLI to avoid reading a phase dataset
            # twice. The caller must remove this before serialization.
            result['_locomotion_data'] = locomotion_data
        return result

    @staticmethod
    def _dataset_columns(dataset_path: str) -> List[str]:
        """Read only dataset metadata when possible to dispatch by primary index."""
        path = Path(dataset_path)
        if path.suffix.lower() == '.parquet':
            import pyarrow.parquet as pq
            return pq.ParquetFile(path).schema.names
        if path.suffix.lower() in {'.csv', '.txt'}:
            return list(pd.read_csv(path, nrows=0).columns)
        return list(pd.read_parquet(path).columns)

    def _validate_time_dataset(self, dataset_path: str) -> Dict[str, Any]:
        """Validate a time export with bounded Arrow/CSV batches.

        Parquet data stays Arrow-native. Numeric signals are scanned in small
        column groups, preventing a wide, single-row-group dataset from being
        materialized as one large Pandas frame.
        """
        path = Path(dataset_path)
        columns = self._dataset_columns(dataset_path)
        required = ['subject', 'task', 'task_id', 'task_info', 'step', 'time_s']
        missing = [column for column in required if column not in columns]

        violations: Dict[str, Dict[str, List[int]]] = {}
        total_checks = 0
        total_violations = 0
        total_rows = 0
        tasks_in_data: Set[str] = set()

        def add_violation(task: str, check: str, segment: int) -> None:
            nonlocal total_violations
            violations.setdefault(str(task), {}).setdefault(check, []).append(int(segment))
            total_violations += 1

        def add_numeric_violations(
            task_values,
            invalid_mask: np.ndarray,
            check: str,
            row_offset: int,
        ) -> None:
            """Count all bad values while retaining a bounded useful sample."""
            nonlocal total_violations
            invalid_positions = np.flatnonzero(invalid_mask)
            total_violations += len(invalid_positions)
            for position in invalid_positions[:20]:
                task = str(task_values[position] if task_values[position] is not None else 'dataset')
                records = violations.setdefault(task, {}).setdefault(check, [])
                if len(records) < 20:
                    records.append(int(row_offset + position))

        if missing:
            violations['dataset'] = {'missing_required_columns': list(range(len(missing)))}
            total_violations += len(missing)

        configured_limits = (
            self.config_manager.get_metadata('time_structural_abs_limits')
            or TIME_STRUCTURAL_ABS_LIMITS
        )
        numeric_limits = {
            column: float(limit)
            for group_name, limit in configured_limits.items()
            for column in CANONICAL_COLUMN_GROUPS.get(group_name, [])
            if column in columns
        }
        optional_index_columns = [
            column for column in ('collection_id', 'time_reset_per') if column in columns
        ]
        metadata_columns = ['subject', 'task', 'task_id', 'task_info', 'step']
        group_columns = ['subject', 'task', 'task_id', 'step']
        if 'collection_id' in columns:
            group_columns.insert(3, 'collection_id')
        last_time_by_group: Dict[Any, float] = {}
        segment_numbers: Dict[Any, int] = {}

        metadata_scan_columns = list(dict.fromkeys(
            [column for column in required if column in columns] + optional_index_columns
        ))

        def iter_batches(scan_columns):
            if path.suffix.lower() == '.parquet':
                import pyarrow.parquet as pq
                yield from pq.ParquetFile(path).iter_batches(
                    columns=scan_columns,
                    batch_size=self.time_batch_size,
                    use_threads=False,
                )
            else:
                yield from pd.read_csv(
                    path, usecols=scan_columns, chunksize=self.time_batch_size
                )

        def column_values(batch, column):
            """Return a bounded Python list for metadata only."""
            if isinstance(batch, pd.DataFrame):
                return batch[column].tolist()
            return batch.column(batch.schema.get_field_index(column)).to_pylist()

        def numeric_values(batch, column):
            if isinstance(batch, pd.DataFrame):
                return pd.to_numeric(batch[column], errors='coerce').to_numpy(dtype=float)
            import pyarrow as pa
            import pyarrow.compute as pc
            array = batch.column(batch.schema.get_field_index(column))
            try:
                cast = pc.cast(array, pa.float64(), safe=False)
                return np.asarray(cast.to_numpy(zero_copy_only=False), dtype=float)
            except (pa.ArrowInvalid, pa.ArrowNotImplementedError, ValueError):
                # Preserve validation semantics for malformed numeric columns.
                return pd.to_numeric(pd.Series(array.to_pylist()), errors='coerce').to_numpy(dtype=float)

        row_offset = 0
        for batch in iter_batches(metadata_scan_columns):
            batch_length = len(batch)
            total_rows += batch_length
            task_values = (
                column_values(batch, 'task')
                if 'task' in metadata_scan_columns else ['dataset'] * batch_length
            )
            tasks_in_data.update(str(value) for value in task_values if value is not None)

            if not missing:
                for column in metadata_columns:
                    values = column_values(batch, column)
                    invalid = np.fromiter(
                        (value is None or (isinstance(value, str) and not value.strip()) for value in values),
                        dtype=bool,
                        count=batch_length,
                    )
                    total_checks += batch_length
                    add_numeric_violations(task_values, invalid, f'{column}_missing', row_offset)

                time_values = numeric_values(batch, 'time_s')
                invalid_time = ~np.isfinite(time_values) | (time_values < 0)
                total_checks += batch_length
                add_numeric_violations(task_values, invalid_time, 'time_s_invalid', row_offset)

                group_values = [column_values(batch, column) for column in group_columns]
                start = 0
                while start < batch_length:
                    key = tuple(values[start] for values in group_values)
                    end = start + 1
                    while end < batch_length and all(
                        values[end] == key[index] for index, values in enumerate(group_values)
                    ):
                        end += 1
                    segment_number = segment_numbers.setdefault(key, len(segment_numbers) + 1)
                    segment_time = time_values[start:end]
                    total_checks += 1
                    if np.all(np.isfinite(segment_time)):
                        previous = last_time_by_group.get(key)
                        crosses_batch_bad = previous is not None and segment_time[0] <= previous
                        within_batch_bad = len(segment_time) > 1 and np.any(np.diff(segment_time) <= 0)
                        if crosses_batch_bad or within_batch_bad:
                            add_violation(
                                str(task_values[start]),
                                'time_s_not_strictly_increasing',
                                segment_number,
                            )
                        last_time_by_group[key] = float(segment_time[-1])
                    start = end
            row_offset += batch_length

        # Wide numeric data is deliberately read in several narrow passes. This
        # trades modest extra I/O for a predictable memory ceiling.
        numeric_items = list(numeric_limits.items())
        for chunk_start in range(0, len(numeric_items), self.time_column_chunk_size):
            chunk = numeric_items[chunk_start:chunk_start + self.time_column_chunk_size]
            scan_columns = (['task'] if 'task' in columns else []) + [name for name, _ in chunk]
            row_offset = 0
            for batch in iter_batches(scan_columns):
                batch_length = len(batch)
                task_values = (
                    column_values(batch, 'task')
                    if 'task' in scan_columns else ['dataset'] * batch_length
                )
                for column, limit in chunk:
                    values = numeric_values(batch, column)
                    total_checks += values.size
                    add_numeric_violations(
                        task_values, np.isinf(values), f'{column}_infinite', row_offset
                    )
                    add_numeric_violations(
                        task_values,
                        np.isfinite(values) & (np.abs(values) > limit),
                        f'{column}_outside_structural_limit_{limit:g}',
                        row_offset,
                    )
                row_offset += batch_length

        schema_passed = not missing and total_violations == 0 and total_rows > 0
        if total_rows == 0:
            violations.setdefault('dataset', {})['empty_dataset'] = [0]
            total_violations += 1

        message = (
            'Time structure valid (required columns present; time_s is finite, non-negative, and strictly increasing per segment)'
            if schema_passed else
            'Time structure invalid; see violations'
        )
        checks = max(total_checks, 1)
        return {
            'passed': schema_passed,
            'schema_passed': schema_passed,
            'quality_gate_passed': schema_passed,
            'quality_gate_threshold': 1.0,
            # Compatibility keys retained for existing summary/report consumers.
            'phase_valid': schema_passed,
            'phase_message': message,
            'violations': violations,
            'tasks': {},
            'stats': {
                'total_checks': checks,
                'total_violations': total_violations,
                'total_strides': 0,
                'total_failing_strides': 0,
                'pass_rate': max(0.0, 1.0 - total_violations / checks),
                'variable_pass_rate': 1.0,
                'num_tasks': len(tasks_in_data - {'dataset'}),
                'dataset': path.stem,
                'pass_rate_threshold': 1.0,
            },
            'mode': 'time',
        }

    def validate_dataset(
        self,
        locomotion_data: LocomotionData,
        ignore_features: Optional[List[str]] = None,
        task_filter: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Validate a pre-loaded locomotion dataset against current ranges."""

        phase_valid, phase_msg = self._validate_phase_structure(locomotion_data)

        tasks_in_data = locomotion_data.get_tasks()
        config_tasks = set(self.config_manager.get_tasks())
        tasks = [t for t in tasks_in_data if t in config_tasks]
        if task_filter:
            tasks = [t for t in tasks if t in task_filter]

        violations: Dict[str, Dict[str, List[int]]] = {}
        task_results: Dict[str, Dict[str, Any]] = {}

        total_checks = 0
        total_violations = 0
        total_strides = 0
        total_failing_strides = 0

        for task in tasks:
            details = self._validate_task_details(
                locomotion_data,
                task,
                ignore_features=ignore_features
            )

            task_results[task] = {
                'failing_strides_by_variable': {
                    var: set(indices)
                    for var, indices in details.per_variable_failures.items()
                },
                'failing_strides_map': details.failing_features,
                'global_passing_strides': set(details.global_passing_strides),
                'total_strides': details.total_strides,
                'validated_variables': details.validated_variables,
                'phase_indices': details.phase_indices,
            }

            if details.per_variable_failures:
                violations[task] = {
                    var: sorted(indices)
                    for var, indices in details.per_variable_failures.items()
                    if indices
                }

            total_strides += details.total_strides
            total_failing_strides += details.total_strides - len(details.global_passing_strides)
            total_violations += sum(len(indices) for indices in details.per_variable_failures.values())

            # Determine how many variable/phase checks were executed for this task
            task_ranges = self.config_manager.get_task_data(task)
            phase_variable_checks = 0
            if details.validated_variables:
                for phase_ranges in task_ranges.values():
                    for var_name in details.validated_variables:
                        if var_name in phase_ranges:
                            phase_variable_checks += 1
            total_checks += details.total_strides * phase_variable_checks

        stride_pass_rate = (
            1.0 - (total_failing_strides / total_strides)
            if total_strides > 0 else 0.0
        )
        variable_pass_rate = (
            1.0 - (total_violations / total_checks)
            if total_checks > 0 else 0.0
        )

        pass_rate_threshold = 0.9 if total_strides > 0 else 0.0
        quality_gate_passed = stride_pass_rate >= pass_rate_threshold if total_strides > 0 else True

        result = {
            # Schema compliance (phase structure + schema validation) determines overall pass/fail
            'passed': phase_valid,
            'schema_passed': phase_valid,
            # Quality gate keeps legacy pass-rate threshold for visibility but no longer fails the run
            'quality_gate_passed': phase_valid and quality_gate_passed,
            'quality_gate_threshold': pass_rate_threshold,
            'phase_valid': phase_valid,
            'phase_message': phase_msg,
            'violations': violations,
            'tasks': task_results,
            'stats': {
                'total_checks': total_checks,
                'total_violations': total_violations,
                'total_strides': total_strides,
                'total_failing_strides': total_failing_strides,
                'pass_rate': stride_pass_rate,
                'variable_pass_rate': variable_pass_rate,
                'num_tasks': len(tasks),
                'dataset': getattr(locomotion_data, 'data_path', Path('unknown')).stem,
                'pass_rate_threshold': pass_rate_threshold,
            },
            'mode': 'phase'
        }

        return result
    
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
    
    @staticmethod
    def _normalize_phase_key(phase_key: Any) -> Optional[int]:
        """Normalize a phase key from the config to an integer percentage."""
        try:
            return int(round(float(phase_key)))
        except (TypeError, ValueError):
            return None

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
        phases = []
        for raw_phase in task_ranges.keys():
            normalized = self._normalize_phase_key(raw_phase)
            if normalized is not None:
                phases.append(normalized)
        phases.sort()

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
        details = self._validate_task_details(
            locomotion_data,
            task_name,
            ignore_features=ignore_features
        )

        violations = {
            var_name: sorted(indices)
            for var_name, indices in details.per_variable_failures.items()
            if indices
        }

        return violations
    
    def _validate_task_with_failing_features(
        self,
        locomotion_data: LocomotionData,
        task_name: str,
        ignore_features: List[str] = None
    ) -> Dict[int, List[str]]:
        """
        Validate task data and return failing features per stride.
        
        Args:
            locomotion_data: The locomotion data object
            task_name: Name of the task to validate
            ignore_features: Optional list of feature names to ignore during validation
            
        Returns dict: {stride_idx: [list_of_failed_variable_names]}
        Strides not in the dict passed all checks.
        """
        return self._validate_task_details(
            locomotion_data,
            task_name,
            ignore_features=ignore_features
        ).failing_features

    def _validate_task_details(
        self,
        locomotion_data: LocomotionData,
        task_name: str,
        ignore_features: Optional[List[str]] = None
    ) -> TaskValidationDetails:
        """Return rich validation details for a specific task."""

        empty_details = TaskValidationDetails(
            failing_features={},
            per_variable_failures={},
            total_strides=0,
            validated_variables=[],
            global_passing_strides=set(),
            phase_indices={}
        )

        if not self.config_manager.has_task(task_name):
            return empty_details

        task_ranges = self.config_manager.get_task_data(task_name)
        phase_indices = self._get_phase_indices(task_ranges)

        all_variables_to_check = set()
        for phase_ranges in task_ranges.values():
            all_variables_to_check.update(phase_ranges.keys())

        if ignore_features:
            all_variables_to_check -= set(ignore_features)

        dataset_features = set(locomotion_data.features or [])
        validated_variables = [
            var for var in sorted(all_variables_to_check)
            if var in dataset_features
        ]

        if not validated_variables:
            return empty_details

        data_3d, feature_names = locomotion_data.get_cycles(
            subject=None,
            task=task_name,
            features=list(validated_variables)
        )

        if data_3d is None or data_3d.size == 0:
            return empty_details

        feature_index = {name: idx for idx, name in enumerate(feature_names)}
        total_strides = data_3d.shape[0]

        failing_features: Dict[int, List[str]] = {}
        per_variable_failures: Dict[str, List[int]] = {var: [] for var in validated_variables}
        failing_stride_set: Set[int] = set()

        for stride_idx in range(total_strides):
            stride_failures: List[str] = []
            for phase_pct, phase_idx in phase_indices.items():
                phase_ranges = task_ranges.get(phase_pct, {})
                for var_name, var_range in phase_ranges.items():
                    if var_name not in feature_index:
                        continue

                    var_idx = feature_index[var_name]
                    value = data_3d[stride_idx, phase_idx, var_idx]

                    min_val = var_range.get('min')
                    max_val = var_range.get('max')

                    if min_val is None or max_val is None:
                        continue
                    if min_val > max_val:
                        min_val, max_val = max_val, min_val
                    if not np.isfinite(value):
                        continue

                    if value < min_val or value > max_val:
                        if var_name not in stride_failures:
                            stride_failures.append(var_name)
                        failing_stride_set.add(stride_idx)
                        per_variable_failures.setdefault(var_name, []).append(stride_idx)

            if stride_failures:
                failing_features[stride_idx] = stride_failures

        global_passing = set(range(total_strides)) - failing_stride_set

        # Ensure variables with no failures still appear with empty lists
        for var_name in validated_variables:
            per_variable_failures.setdefault(var_name, [])

        return TaskValidationDetails(
            failing_features=failing_features,
            per_variable_failures=per_variable_failures,
            total_strides=total_strides,
            validated_variables=validated_variables,
            global_passing_strides=global_passing,
            phase_indices=phase_indices,
        )
    
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
