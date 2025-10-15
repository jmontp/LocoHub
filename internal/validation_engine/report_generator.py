#!/usr/bin/env python3
"""
Validation Report Generator

Generates markdown reports and coordinates plot generation for validation results.
Separated from core validation logic for better modularity.
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Tuple
import hashlib
import shutil

import sys
import numpy as np
import pandas as pd
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️  psutil not available - memory monitoring disabled")

# Avoid circular import - import only what's needed
from internal.plot_generation.filters_by_phase_plots import (
    create_single_feature_plot, 
    create_task_combined_plot,
    create_subject_failure_histogram,
    get_sagittal_features,
    get_task_classification,
    create_filters_by_phase_plot  # Keep for backward compatibility
)
from internal.plot_generation.step_classifier import StepClassifier
from locohub import LocomotionData


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
        self.docs_dir = project_root / "docs" / "reference" / "datasets_documentation"
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        
        # Validation plots go in a subdirectory
        self.plots_dir = self.docs_dir / "validation_plots"
        self.plots_dir.mkdir(exist_ok=True)
        
        # Validation archives for ranges files
        self.archives_dir = self.docs_dir / "validation_archives"
        self.archives_dir.mkdir(exist_ok=True)
        
        # Keep old output_dir for backwards compatibility
        self.output_dir = project_root / "docs" / "reference" / "datasets_documentation" / "validation_reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Import here to avoid circular dependency
        from internal.validation_engine.validator import Validator
        
        # Store which ranges file is being used
        if ranges_file:
            self.ranges_file_path = Path(ranges_file)
            # Create validator with empty config manager
            self.validator = Validator()
            # Load the specific ranges file
            self.validator.config_manager.load(self.ranges_file_path)
        else:
            # Use default ranges file
            self.ranges_file_path = project_root / "contributor_tools" / "validation_ranges" / "default_ranges.yaml"
            self.validator = Validator()
        
        self.step_classifier = StepClassifier()
        
        # Memory monitoring setup
        self.memory_log_file = None
        self.peak_memory_usage = 0
        self._setup_memory_monitoring()
        
        # Cache for required columns to avoid repeated column introspection
        self._required_columns_cache = None
        
        # Will store archive info after archiving
        self.ranges_archive_path = None
        self.ranges_hash = None
        
    def _setup_memory_monitoring(self):
        """Setup memory monitoring and logging."""
        if PSUTIL_AVAILABLE:
            # Create memory log file with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.memory_log_file = self.docs_dir / f"memory_usage_report_{timestamp}.log"
            
            # Initialize log file
            with open(self.memory_log_file, 'w') as f:
                f.write(f"# Memory Usage Report - {datetime.now()}\n")
                f.write(f"# Format: timestamp, operation, memory_used_mb, memory_percent, available_mb\n")
            
            # Log initial memory state
            self._log_memory("initialization", "ValidationReportGenerator created")
            
            print(f"📊 Memory monitoring enabled - logging to: {self.memory_log_file.name}")
        else:
            print("📊 Memory monitoring disabled (psutil not available)")
    
    def _log_memory(self, operation: str, details: str = ""):
        """Log current memory usage to file and check circuit breaker."""
        if not PSUTIL_AVAILABLE or not self.memory_log_file:
            return
            
        try:
            # Get memory info
            memory = psutil.virtual_memory()
            process = psutil.Process()
            process_memory = process.memory_info()
            
            # Convert to MB
            used_mb = memory.used / 1024 / 1024
            available_mb = memory.available / 1024 / 1024
            process_mb = process_memory.rss / 1024 / 1024
            
            # Track peak usage
            if process_mb > self.peak_memory_usage:
                self.peak_memory_usage = process_mb
            
            # Format timestamp
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Log to file
            with open(self.memory_log_file, 'a') as f:
                f.write(f"{timestamp},{operation},{used_mb:.1f},{memory.percent:.1f},{available_mb:.1f},{process_mb:.1f},{details}\n")
            
            # Memory circuit breaker - abort if memory exceeds 95%
            if memory.percent > 95:
                error_msg = f"💥 MEMORY CIRCUIT BREAKER TRIGGERED: {memory.percent:.1f}% memory usage exceeded 95% limit"
                print(error_msg)
                with open(self.memory_log_file, 'a') as f:
                    f.write(f"{timestamp},CIRCUIT_BREAKER,{used_mb:.1f},{memory.percent:.1f},{available_mb:.1f},{process_mb:.1f},CRITICAL: Processing aborted to prevent crash\n")
                raise MemoryError(error_msg)
            
            # Print warning if memory usage is high
            elif memory.percent > 80:
                print(f"⚠️  High memory usage: {memory.percent:.1f}% ({used_mb:.0f} MB used)")
                
        except MemoryError:
            # Re-raise MemoryError from circuit breaker
            raise
        except Exception as e:
            print(f"⚠️  Memory logging error: {e}")
    
    def _check_memory_threshold(self, operation: str = "operation") -> bool:
        """
        Check if memory usage is safe to continue processing.
        
        Args:
            operation: Name of operation being checked
            
        Returns:
            True if safe to continue, False if should abort
            
        Raises:
            MemoryError: If memory usage exceeds 95%
        """
        if not PSUTIL_AVAILABLE:
            return True  # Can't check, assume safe
            
        try:
            memory = psutil.virtual_memory()
            if memory.percent > 95:
                error_msg = f"💥 MEMORY THRESHOLD EXCEEDED: {memory.percent:.1f}% during {operation}"
                print(error_msg)
                raise MemoryError(error_msg)
            
            return memory.percent < 90  # Return False if approaching limit (90%+)
            
        except MemoryError:
            raise
        except Exception:
            return True  # Error checking, assume safe
    
    def _get_memory_summary(self) -> str:
        """Get current memory usage summary string."""
        if not PSUTIL_AVAILABLE:
            return "Memory monitoring disabled"
            
        try:
            memory = psutil.virtual_memory()
            process = psutil.Process()
            process_mb = process.memory_info().rss / 1024 / 1024
            
            return f"System: {memory.percent:.1f}% ({memory.used/1024/1024:.0f}MB), Process: {process_mb:.1f}MB, Peak: {self.peak_memory_usage:.1f}MB"
        except:
            return "Memory info unavailable"
    
    def _get_required_columns(self, dataset_path: str) -> List[str]:
        """
        Get list of columns required for validation to minimize memory usage.
        Only includes columns that actually exist in the dataset.
        
        Args:
            dataset_path: Path to dataset parquet file
            
        Returns:
            List of column names needed for validation (only existing columns)
        """
        if self._required_columns_cache is not None:
            return self._required_columns_cache
            
        print("📊 Analyzing dataset columns for optimal loading...")
        
        try:
            # Get all available columns from the dataset (read schema only)
            import pyarrow.parquet as pq
            parquet_file = pq.ParquetFile(dataset_path)
            available_columns = set(parquet_file.schema.names)
            total_columns = len(available_columns)
            
            # Always required columns (must exist)
            required_cols = []
            for col in ['subject', 'task', 'step', 'phase_ipsi']:
                if col in available_columns:
                    required_cols.append(col)
                else:
                    print(f"⚠️  Required column '{col}' not found in dataset")
            
            # Optional phase_ipsi_dot for velocity validation
            if 'phase_ipsi_dot' in available_columns:
                required_cols.append('phase_ipsi_dot')
            
            # Add sagittal features that exist
            from internal.plot_generation.filters_by_phase_plots import get_sagittal_features
            sagittal_features = get_sagittal_features()
            feature_names = [f[0] for f in sagittal_features]
            
            sagittal_found = 0
            for feature in feature_names:
                if feature in available_columns:
                    required_cols.append(feature)
                    sagittal_found += 1
            
            print(f"📊 Found {sagittal_found}/{len(feature_names)} sagittal features in dataset")
            
            # Add velocity features for velocity validation (only if they exist)
            from locohub.feature_constants import (
                ANGLE_FEATURES, VELOCITY_FEATURES, 
                SEGMENT_ANGLE_FEATURES, SEGMENT_VELOCITY_FEATURES
            )
            
            # Build angle-velocity pairs and check existence
            angle_velocity_pairs = []
            for angle in ANGLE_FEATURES:
                velocity = angle.replace('_angle_', '_velocity_').replace('_rad', '_rad_s')
                if velocity in VELOCITY_FEATURES:
                    angle_velocity_pairs.append((angle, velocity))
            
            for angle in SEGMENT_ANGLE_FEATURES:
                velocity = angle.replace('_angle_', '_velocity_').replace('_rad', '_rad_s')
                if velocity in SEGMENT_VELOCITY_FEATURES:
                    angle_velocity_pairs.append((angle, velocity))
            
            velocity_found = 0
            for angle, velocity in angle_velocity_pairs:
                if angle in available_columns:
                    required_cols.append(angle)
                if velocity in available_columns:
                    required_cols.append(velocity)
                    velocity_found += 1
            
            print(f"📊 Found {velocity_found}/{len(angle_velocity_pairs)} velocity pairs in dataset")
            
            # Remove duplicates and cache result
            self._required_columns_cache = list(set(required_cols))
            
            reduction_percent = (1 - len(self._required_columns_cache) / total_columns) * 100
            print(f"📊 Optimized loading: {len(self._required_columns_cache)}/{total_columns} columns ({reduction_percent:.1f}% reduction)")
            
            return self._required_columns_cache
            
        except Exception as e:
            print(f"⚠️  Column analysis failed: {e}")
            print("📊 Falling back to full dataset loading")
            # Return None to trigger full dataset loading
            return None
    
    def _load_dataset_optimized(self, dataset_path: str, phase_col: str = 'phase_ipsi') -> 'LocomotionData':
        """
        Load dataset with memory optimization by selecting only required columns.
        
        Args:
            dataset_path: Path to dataset file
            phase_col: Phase column name
            
        Returns:
            LocomotionData instance with minimal memory footprint
        """
        self._log_memory("optimized_load_start", "Starting optimized dataset loading")
        
        # Get required columns (returns None if analysis fails)
        required_cols = self._get_required_columns(dataset_path)
        
        # Load data - use column optimization if available
        if required_cols is not None:
            try:
                df_subset = pd.read_parquet(dataset_path, columns=required_cols)
                self._log_memory("optimized_load_columns", f"Loaded {len(required_cols)} columns, shape: {df_subset.shape}")
                print(f"✅ Column optimization successful")
            except Exception as e:
                print(f"⚠️  Column loading failed ({e}), falling back to full load")
                self._log_memory("optimized_load_fallback", f"Column loading failed: {e}")
                df_subset = pd.read_parquet(dataset_path)
        else:
            print("📊 Loading full dataset (column optimization unavailable)")
            self._log_memory("full_load", "Loading full dataset")
            df_subset = pd.read_parquet(dataset_path)
        
        # Create a minimal LocomotionData instance by temporarily replacing the DataFrame
        from locohub import LocomotionData
        
        # Create instance with minimal loading
        loco_data = LocomotionData.__new__(LocomotionData)
        loco_data.data_path = Path(dataset_path)
        loco_data.subject_col = 'subject'
        loco_data.task_col = 'task'
        loco_data.phase_col = phase_col
        loco_data.df = df_subset
        loco_data._cache = {}
        
        # Initialize features list
        loco_data.features = [col for col in df_subset.columns 
                             if col not in ['subject', 'task', 'step', 'phase_ipsi', 'phase_ipsi_dot']]
        
        # Add required methods
        def get_tasks():
            return sorted(df_subset['task'].unique())
        
        def get_cycles(subject=None, task=None, features=None):
            # Enhanced version that handles concatenated cycles
            data_filtered = df_subset.copy()
            if subject:
                data_filtered = data_filtered[data_filtered['subject'] == subject]
            if task:
                data_filtered = data_filtered[data_filtered['task'] == task]
                
            if features is None:
                features = loco_data.features
            
            # Group by subject/task/step and reshape to 3D array
            groups = data_filtered.groupby(['subject', 'task', 'step'])
            cycles_list = []
            total_groups = len(groups)
            valid_groups = 0
            total_cycles_extracted = 0
            
            for (subj, tsk, step), group in groups:
                group_len = len(group)
                if group_len % 150 == 0 and group_len >= 150:  # Valid cycle(s)
                    valid_groups += 1
                    n_cycles = group_len // 150
                    
                    # Extract feature data and reshape to cycles
                    group_data = group[features].values
                    try:
                        # Reshape to separate individual cycles
                        cycles_data = group_data.reshape(n_cycles, 150, len(features))
                        
                        # Add each cycle individually
                        for cycle_idx in range(n_cycles):
                            cycles_list.append(cycles_data[cycle_idx])
                            total_cycles_extracted += 1
                            
                    except ValueError as e:
                        # Log reshape errors for debugging
                        print(f"⚠️  Reshape error for {subj}-{tsk}-{step}: {group_len} points, {len(features)} features - {e}")
            
            # Log extraction statistics
            print(f"    Cycle extraction: {valid_groups}/{total_groups} valid groups, {total_cycles_extracted} total cycles")
            
            if cycles_list:
                cycles_3d = np.stack(cycles_list, axis=0)
                return cycles_3d, features
            else:
                return np.array([]).reshape(0, 150, len(features)), features
        
        loco_data.get_tasks = get_tasks
        loco_data.get_cycles = get_cycles
        
        self._log_memory("optimized_load_complete", f"Optimized LocomotionData created")
        
        return loco_data
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA256 hash of file contents.
        
        Args:
            file_path: Path to file to hash
            
        Returns:
            Hexadecimal string of SHA256 hash
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _archive_ranges_file(self, dataset_name: str, timestamp_str: str) -> Tuple[Path, str]:
        """
        Archive the validation ranges file with timestamp.
        
        Args:
            dataset_name: Name of dataset being validated
            timestamp_str: Timestamp string for archive naming
            
        Returns:
            Tuple of (archive_path, hash_string)
        """
        # Calculate hash of original file
        file_hash = self._calculate_file_hash(self.ranges_file_path)
        
        # Create archive filename
        timestamp_clean = timestamp_str.replace(" ", "_").replace(":", "")
        archive_name = f"{dataset_name}_{timestamp_clean}_ranges.yaml"
        archive_path = self.archives_dir / archive_name
        
        # Copy ranges file to archive
        shutil.copy2(self.ranges_file_path, archive_path)
        
        # Save hash to companion file
        hash_file = self.archives_dir / f"{dataset_name}_{timestamp_clean}_ranges.sha256"
        with open(hash_file, 'w') as f:
            f.write(f"{file_hash}  {archive_name}\n")
        
        return archive_path, file_hash
    
    def generate_report(self, dataset_path: str, generate_plots: bool = True) -> str:
        """
        Generate complete validation report with optional plots and memory protection.
        
        Args:
            dataset_path: Path to dataset to validate
            generate_plots: Whether to generate validation plots
            
        Returns:
            Path to generated report
            
        Raises:
            MemoryError: If memory usage exceeds safe limits during processing
        """
        dataset_name = Path(dataset_path).stem
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            self._log_memory("report_start", f"Starting report generation for {dataset_name}")
            print(f"📊 Initial memory: {self._get_memory_summary()}")
            
            # Archive the ranges file
            self.ranges_archive_path, self.ranges_hash = self._archive_ranges_file(dataset_name, timestamp)
            self._log_memory("archive_complete", "Validation ranges archived")
            
            # Run validation
            validation_result = self.validator.validate(dataset_path)
            self._log_memory("validation_complete", f"Dataset validation completed")
            print(f"📊 Post-validation memory: {self._get_memory_summary()}")
            
            # Generate plots if requested (this also runs velocity validation)
            plot_paths = {}
            velocity_results = {}
            if generate_plots:
                try:
                    plot_paths, velocity_results = self._generate_plots(dataset_path, validation_result, timestamp)
                    self._log_memory("plots_complete", f"Generated {len(plot_paths)} plots")
                    print(f"📊 Post-plots memory: {self._get_memory_summary()}")
                except MemoryError as e:
                    print(f"⚠️  Plot generation aborted due to memory limits: {e}")
                    print("🔄 Continuing with report generation without plots...")
                    # Continue with empty plots and velocity results
            
            # Generate markdown report (reuse velocity results instead of re-running validation)
            report_path = self._generate_markdown_report(
                dataset_name, 
                validation_result, 
                plot_paths, 
                timestamp,
                dataset_path,
                velocity_results  # Pass velocity results to avoid duplicate validation
            )
            
            self._log_memory("report_complete", f"Report generation finished")
            print(f"📊 Final memory: {self._get_memory_summary()}")
            
            return str(report_path)
            
        except MemoryError as e:
            # Log the memory error and re-raise with context
            self._log_memory("memory_error", f"Report generation failed: {str(e)}")
            print(f"💥 Report generation failed due to memory constraints")
            print(f"📊 Memory state at failure: {self._get_memory_summary()}")
            raise MemoryError(f"Report generation for {dataset_name} exceeded memory limits: {str(e)}")
    
    def _generate_plots(self, dataset_path: str, validation_result: Dict, 
                       timestamp: str, show_interactive: bool = False, show_local_passing: bool = False) -> Tuple[Dict[str, str], Dict[str, Dict]]:
        """Generate validation plots for the dataset with memory optimization."""
        import gc
        import matplotlib.pyplot as plt
        
        plot_paths = {}
        
        # Load dataset with optimized column selection (minimal memory footprint)
        print(f"Loading dataset with memory optimization...")
        locomotion_data = self._load_dataset_optimized(dataset_path, phase_col='phase_ipsi')
        tasks = locomotion_data.get_tasks() if hasattr(locomotion_data, 'get_tasks') else sorted(locomotion_data.df['task'].unique())
        print(f"Found {len(tasks)} tasks: {', '.join(tasks)}")
        self._log_memory("metadata_loaded", f"Loaded {len(tasks)} tasks")
        
        # Run velocity validation once but release data immediately after
        print("Running velocity validation...")
        data = locomotion_data.df
        self._log_memory("velocity_start", f"Starting velocity validation on {data.shape}")
        velocity_results = self.validate_velocity_consistency(data)
        
        # Explicit memory cleanup
        del data
        gc.collect()
        self._log_memory("velocity_complete", f"Velocity validation complete, data released")
        
        # Get sagittal plane features only
        sagittal_features = get_sagittal_features()
        feature_names = [f[0] for f in sagittal_features]
        
        # Process one task at a time to minimize memory usage
        for i, task in enumerate(tasks, 1):
            print(f"Processing task {i}/{len(tasks)}: {task}")
            
            # Check memory before processing each task
            try:
                self._log_memory("task_start", f"Starting task {task}")
            except MemoryError as e:
                print(f"💥 Task processing aborted due to memory limit: {e}")
                break
            
            try:
                # Reload dataset with optimized loading for this task only
                task_locomotion_data = self._load_dataset_optimized(dataset_path, phase_col='phase_ipsi')
                
                # Filter to only features that exist in the dataset
                available_features = [f for f in feature_names if f in task_locomotion_data.features]
                
                if available_features:
                    # Process features in smaller batches to minimize memory usage
                    plot_path = self._generate_task_plot_memory_optimized(
                        task_locomotion_data=task_locomotion_data,
                        task=task,
                        available_features=available_features,
                        velocity_results=velocity_results,
                        dataset_path=dataset_path,
                        timestamp=timestamp,
                        show_interactive=show_interactive,
                        show_local_passing=show_local_passing
                    )
                    
                    if plot_path:
                        plot_paths[task] = plot_path
                        print(f"  ✅ Validation plot saved: {Path(plot_path).name}")
                    
                    # Generate subject failure histogram (uses minimal memory)
                    biomechanical_failing_features = self.validator._validate_task_with_failing_features(task_locomotion_data, task)
                    velocity_failing_features = self._get_velocity_failures_for_task(task_locomotion_data, task, velocity_results)
                    merged_failures = self._merge_failure_types(biomechanical_failing_features, velocity_failing_features)
                    
                    if merged_failures:
                        print(f"  Generating failure histogram...")
                        legacy_failures = self._convert_merged_failures_to_legacy_format(merged_failures)
                        histogram_path = create_subject_failure_histogram(
                            locomotion_data=task_locomotion_data,
                            task_name=task,
                            failing_features=legacy_failures,
                            output_dir=str(self.plots_dir),
                            dataset_name=Path(dataset_path).stem,
                            timestamp=timestamp
                        )
                        plot_paths[f"{task}_histogram"] = histogram_path
                        print(f"  ✅ Histogram saved: {Path(histogram_path).name}")
                    
                    # Explicit memory cleanup after each task
                    del task_locomotion_data, biomechanical_failing_features
                    del velocity_failing_features, merged_failures
                    plt.close('all')  # Close any matplotlib figures
                    gc.collect()
                    self._log_memory("task_cleanup", f"Task {task} memory cleaned up")
                    print(f"  Memory cleaned up")
                else:
                    print(f"  ⚠️  No available features for task {task}")
                    
            except Exception as e:
                print(f"  ❌ Error processing task {task}: {e}")
                # Clean up on error
                plt.close('all')
                gc.collect()
                self._log_memory("task_error", f"Task {task} failed, memory cleaned up")
                continue
        
        # Final cleanup - but keep velocity_results for return
        velocity_results_copy = velocity_results.copy()  # Make a copy before deletion
        del velocity_results
        gc.collect()
        self._log_memory("plots_final_cleanup", "Final plot generation cleanup")
        print(f"Plot generation completed: {len(plot_paths)} plots generated")
        
        return plot_paths, velocity_results_copy
    
    def _generate_task_plot_memory_optimized(self, task_locomotion_data, task: str, available_features: List[str], 
                                           velocity_results: Dict, dataset_path: str, timestamp: str, show_interactive: bool = False, show_local_passing: bool = False) -> Optional[str]:
        """
        Generate task plot with memory optimization by processing features in smaller batches.
        
        Args:
            task_locomotion_data: LocomotionData instance for this task
            task: Task name
            available_features: List of available feature names
            velocity_results: Velocity validation results
            dataset_path: Path to dataset
            timestamp: Timestamp for plot
            
        Returns:
            Path to generated plot or None if failed
        """
        import gc
        import matplotlib.pyplot as plt
        
        try:
            # Process features in batches of 8 to minimize memory usage
            batch_size = 8
            feature_batches = [available_features[i:i + batch_size] 
                             for i in range(0, len(available_features), batch_size)]
            
            print(f"    Processing {len(available_features)} features in {len(feature_batches)} batches")
            self._log_memory("plot_batch_start", f"Starting {len(feature_batches)} feature batches")
            
            # Load all batches and combine (still more memory efficient than before)
            all_data_batches = []
            all_feature_names = []
            
            for batch_idx, feature_batch in enumerate(feature_batches, 1):
                print(f"    Loading batch {batch_idx}/{len(feature_batches)}: {len(feature_batch)} features")
                
                # Check memory before each batch
                try:
                    self._log_memory("plot_batch_load", f"Loading feature batch {batch_idx}")
                except MemoryError as e:
                    print(f"💥 Plot generation aborted at batch {batch_idx} due to memory limit: {e}")
                    return None
                
                # Load data for this feature batch only
                batch_data_3d, batch_feature_names = task_locomotion_data.get_cycles(
                    subject=None, task=task, features=feature_batch
                )
                
                all_data_batches.append(batch_data_3d)
                all_feature_names.extend(batch_feature_names)
                
                self._log_memory("plot_batch_loaded", f"Batch {batch_idx} loaded: {batch_data_3d.shape}")
                
                # Quick memory cleanup
                gc.collect()
            
            # Combine all batches into final array
            print(f"    Combining {len(all_data_batches)} batches...")
            self._log_memory("plot_combine_start", "Combining feature batches")
            
            if all_data_batches:
                # Concatenate along the feature axis (axis=2)
                all_data_3d = np.concatenate(all_data_batches, axis=2)
                self._log_memory("plot_combine_complete", f"Combined data shape: {all_data_3d.shape}")
                
                # Clean up intermediate batches
                del all_data_batches
                gc.collect()
                self._log_memory("plot_batches_cleanup", "Intermediate batches cleaned up")
                
                # Get validation information
                biomechanical_failing_features = self.validator._validate_task_with_failing_features(task_locomotion_data, task)
                velocity_failing_features = self._get_velocity_failures_for_task(task_locomotion_data, task, velocity_results)
                merged_failures = self._merge_failure_types(biomechanical_failing_features, velocity_failing_features)
                
                print(f"    Found {len(merged_failures)} failing strides")
                
                # Get task validation data
                task_validation_data = self.validator.config_manager.get_task_data(task) if self.validator.config_manager.has_task(task) else {}
                
                # Generate the plot with lower DPI for memory efficiency
                print(f"    Generating validation plot...")
                self._log_memory("plot_generation_start", "Starting plot generation")
                
                plot_path = create_task_combined_plot(
                    validation_data=task_validation_data,
                    task_name=task,
                    output_dir=str(self.plots_dir),
                    data_3d=all_data_3d,
                    feature_names=all_feature_names,
                    failing_features=merged_failures,
                    dataset_name=Path(dataset_path).stem,
                    timestamp=timestamp,
                    show_interactive=show_interactive,
                    show_local_passing=show_local_passing
                )
                
                self._log_memory("plot_generation_complete", "Plot generation complete")
                
                # Immediate cleanup of large arrays
                del all_data_3d, biomechanical_failing_features, velocity_failing_features
                del merged_failures, task_validation_data
                plt.close('all')
                gc.collect()
                self._log_memory("plot_arrays_cleanup", "Large arrays cleaned up")
                
                return plot_path
            else:
                print(f"    ⚠️  No data loaded for task {task}")
                return None
                
        except Exception as e:
            print(f"    ❌ Memory-optimized plot generation failed: {e}")
            self._log_memory("plot_error", f"Plot generation failed: {e}")
            plt.close('all')
            gc.collect()
            return None
    
    def _get_velocity_failures_for_task(self, locomotion_data: LocomotionData, task: str, velocity_results: Dict) -> Dict[int, List[str]]:
        """
        Extract velocity failing features for a specific task.
        
        Args:
            locomotion_data: LocomotionData instance
            task: Task name to filter for
            velocity_results: Results from validate_velocity_consistency
            
        Returns:
            Dictionary mapping stride indices to list of failed velocity variables
        """
        velocity_failing_features = {}
        
        # Filter for task data to build stride mapping
        task_data = locomotion_data.df[locomotion_data.df['task'] == task]
        
        # Build mapping from global stride index to task-local stride index
        stride_idx = 0
        for subject in sorted(task_data['subject'].unique()):
            subject_data = task_data[task_data['subject'] == subject]
            for step in sorted(subject_data['step'].unique()):
                step_data = subject_data[subject_data['step'] == step]
                n_cycles = len(step_data) // 150  # 150 points per cycle
                
                # Each step can have multiple cycles
                for cycle in range(n_cycles):
                    # Check if this stride failed any velocity variables
                    failed_velocities = []
                    
                    for vel_var, result in velocity_results.items():
                        if 'failing_strides' in result:
                            if stride_idx in result['failing_strides']:
                                failed_velocities.append(vel_var)
                    
                    if failed_velocities:
                        velocity_failing_features[stride_idx] = failed_velocities
                    
                    stride_idx += 1
        
        return velocity_failing_features
    
    def _merge_failure_types(self, biomechanical_failures: Dict[int, List[str]], 
                           velocity_failures: Dict[int, List[str]]) -> Dict[int, Dict[str, List[str]]]:
        """
        Merge biomechanical and velocity failures while preserving failure type information.
        
        Args:
            biomechanical_failures: Dict mapping stride indices to failed biomechanical variables
            velocity_failures: Dict mapping stride indices to failed velocity variables
            
        Returns:
            Dictionary with structure: {stride_idx: {'biomechanical': [...], 'velocity': [...]}}
        """
        merged_failures = {}
        
        # Get all stride indices that failed either type of validation
        all_failed_strides = set(biomechanical_failures.keys()) | set(velocity_failures.keys())
        
        for stride_idx in all_failed_strides:
            merged_failures[stride_idx] = {
                'biomechanical': biomechanical_failures.get(stride_idx, []),
                'velocity': velocity_failures.get(stride_idx, [])
            }
        
        return merged_failures
    
    def _convert_merged_failures_to_legacy_format(self, merged_failures: Dict[int, Dict[str, List[str]]]) -> Dict[int, List[str]]:
        """
        Convert merged failure structure back to legacy format for backward compatibility.
        
        Args:
            merged_failures: Dict with structure {stride_idx: {'biomechanical': [...], 'velocity': [...]}}
            
        Returns:
            Dict with structure {stride_idx: [all_failed_variables]} (legacy format)
        """
        legacy_failures = {}
        
        for stride_idx, failure_types in merged_failures.items():
            all_failed_variables = []
            
            # Combine biomechanical and velocity failures
            all_failed_variables.extend(failure_types.get('biomechanical', []))
            all_failed_variables.extend(failure_types.get('velocity', []))
            
            if all_failed_variables:
                legacy_failures[stride_idx] = all_failed_variables
        
        return legacy_failures
    
    def _generate_comparison_plots(self, dataset_path: str, timestamp: str) -> None:
        """
        Generate comparison plots (single-column, passing strides only).
        
        Args:
            dataset_path: Path to the dataset
            timestamp: Timestamp for the plots
        """
        # Create comparison plots directory
        comparison_plots_dir = self.docs_dir / "comparison_plots"
        comparison_plots_dir.mkdir(exist_ok=True)
        
        # Load dataset
        locomotion_data = LocomotionData(dataset_path, phase_col='phase_ipsi')
        data = locomotion_data.df
        tasks = locomotion_data.get_tasks()
        dataset_name = Path(dataset_path).stem.replace('_phase', '').replace('_time', '')
        
        # Run velocity validation once for all tasks
        velocity_results = self.validate_velocity_consistency(data)
        
        # Get sagittal features
        sagittal_features = get_sagittal_features()
        feature_names = [f[0] for f in sagittal_features]
        
        # Generate comparison plot for each task
        for task in tasks:
            # Filter to available features
            available_features = [f for f in feature_names if f in locomotion_data.features]
            
            if available_features:
                # Load data for all features
                all_data_3d, all_feature_names = locomotion_data.get_cycles(
                    subject=None, task=task, features=available_features
                )
                
                # Get failing features for filtering (integrated validation)
                biomechanical_failing_features = self.validator._validate_task_with_failing_features(locomotion_data, task)
                velocity_failing_features = self._get_velocity_failures_for_task(locomotion_data, task, velocity_results)
                merged_failures = self._merge_failure_types(biomechanical_failing_features, velocity_failing_features)
                
                # Get task validation data
                task_validation_data = self.validator.config_manager.get_task_data(task) \
                    if self.validator.config_manager.has_task(task) else {}
                
                # Generate comparison plot (single column, passing strides only)
                create_task_combined_plot(
                    validation_data=task_validation_data,
                    task_name=task,
                    output_dir=str(comparison_plots_dir),
                    data_3d=all_data_3d,
                    feature_names=all_feature_names,
                    failing_features=merged_failures,  # Pass merged structure for three-color support
                    dataset_name=dataset_name,
                    timestamp=timestamp,
                    comparison_mode=True,  # KEY: Single column layout
                    show_local_passing=False  # Comparison plots don't show local passing
                )
    
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
    
    def validate_velocity_consistency(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """
        Validate that velocities match angles using chain rule: dθ/dt = (dθ/dφ) × (dφ/dt)
        Memory optimized version that processes velocity variables one at a time.
        
        Args:
            df: DataFrame with phase-indexed data including phase_ipsi_dot
            
        Returns:
            Dictionary with consistency results for each velocity variable
        """
        import numpy as np
        import gc
        from locohub.feature_constants import (
            ANGLE_FEATURES, VELOCITY_FEATURES,
            SEGMENT_ANGLE_FEATURES, SEGMENT_VELOCITY_FEATURES
        )
        
        results = {}
        
        # Check if phase_ipsi_dot exists
        if 'phase_ipsi_dot' not in df.columns:
            return {'error': 'phase_ipsi_dot column not found - velocity validation requires phase rate information'}
        
        # Map angles to velocities
        angle_velocity_pairs = []
        
        # Map joint angles to joint velocities
        for angle in ANGLE_FEATURES:
            # Convert angle name to velocity name
            velocity = angle.replace('_angle_', '_velocity_').replace('_rad', '_rad_s')
            if velocity in VELOCITY_FEATURES:
                angle_velocity_pairs.append((angle, velocity))
        
        # Map segment angles to segment velocities
        for angle in SEGMENT_ANGLE_FEATURES:
            # Convert angle name to velocity name
            velocity = angle.replace('_angle_', '_velocity_').replace('_rad', '_rad_s')
            if velocity in SEGMENT_VELOCITY_FEATURES:
                angle_velocity_pairs.append((angle, velocity))
        
        print(f"Validating {len(angle_velocity_pairs)} velocity variables...")
        
        # Process each velocity variable with progress tracking
        for i, (angle_col, velocity_col) in enumerate(angle_velocity_pairs, 1):
            print(f"  Processing {i}/{len(angle_velocity_pairs)}: {velocity_col}")
            
            # Check memory before processing each variable
            try:
                self._log_memory("velocity_variable", f"Processing {velocity_col}")
            except MemoryError as e:
                print(f"💥 Velocity validation aborted due to memory limit: {e}")
                results[velocity_col] = {'status': 'memory_limit_exceeded', 'message': str(e)}
                break
                
            if angle_col not in df.columns:
                results[velocity_col] = {'status': 'angle_missing', 'message': f'Angle column {angle_col} not found'}
                continue
            
            errors = []
            stride_count = 0
            failing_stride_indices = []  # Track which strides failed velocity validation
            
            # Process each stride
            for stride_idx, ((subject, task, step), stride_df) in enumerate(df.groupby(['subject', 'task', 'step'])):
                if len(stride_df) != 150:
                    continue
                
                stride_count += 1
                phase_dot = stride_df['phase_ipsi_dot'].iloc[0]  # Constant for stride
                
                # Calculate expected velocity from angle using chain rule
                angle_data = stride_df[angle_col].values
                
                # Skip if all NaN
                if np.all(np.isnan(angle_data)):
                    continue
                
                # Calculate gradient with respect to index
                dangle_dindex = np.gradient(angle_data)
                
                # Convert to per-phase-percent (150 points = 100%)
                dangle_dphase = dangle_dindex * (100 / 150)
                
                # Apply chain rule: dθ/dt = (dθ/dφ) × (dφ/dt)
                expected_velocity = dangle_dphase * phase_dot
                
                # Check if stored velocity exists
                if velocity_col in stride_df.columns:
                    stored_velocity = stride_df[velocity_col].values
                    
                    # Skip if stored velocity is all NaN
                    if not np.all(np.isnan(stored_velocity)):
                        # Calculate mean absolute error
                        valid_mask = ~(np.isnan(expected_velocity) | np.isnan(stored_velocity))
                        if np.any(valid_mask):
                            mae = np.mean(np.abs(expected_velocity[valid_mask] - stored_velocity[valid_mask]))
                            errors.append(mae)
                            
                            # Check if this stride fails velocity validation
                            if mae >= 0.5:  # Using same threshold as before
                                failing_stride_indices.append(stride_idx)
            
            # Determine pass/fail (threshold: 0.5 rad/s mean error)
            if errors:
                mean_error = np.mean(errors)
                max_error = np.max(errors)
                std_error = np.std(errors)
                var_error = np.var(errors)  # Add variance calculation
                
                results[velocity_col] = {
                    'status': 'pass' if mean_error < 0.5 else 'fail',
                    'mean_error': mean_error,
                    'max_error': max_error,
                    'std_error': std_error,
                    'var_error': var_error,  # Include variance
                    'num_strides': len(errors),
                    'total_strides': stride_count,
                    'failing_strides': failing_stride_indices  # Track failing stride indices
                }
                status_symbol = "✅" if mean_error < 0.5 else "❌"
                print(f"    {status_symbol} {results[velocity_col]['status'].upper()}: {len(failing_stride_indices)} failing strides")
            else:
                results[velocity_col] = {
                    'status': 'calculated_only',
                    'message': 'No stored velocities to compare',
                    'total_strides': stride_count,
                    'failing_strides': []  # Empty list for consistency
                }
                print(f"    ⚠️  CALCULATED_ONLY: No stored velocities to compare")
            
            # Memory cleanup after each variable
            gc.collect()
        
        print(f"Velocity validation completed: {len(results)} variables processed")
        return results
    
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
                                 plot_paths: Dict, timestamp: str, dataset_path: str, 
                                 velocity_results: Optional[Dict[str, Dict]] = None) -> Path:
        """Generate markdown validation report."""
        report_name = f"{dataset_name}_validation_report.md"
        report_path = self.output_dir / report_name
        
        # Build report content
        lines = []
        lines.append(f"# Validation Report: {dataset_name}")
        lines.append(f"")
        lines.append(f"**Generated**: {timestamp}  ")
        
        # Status summary
        schema_status = "✅ Schema compliant" if validation_result.get('schema_passed', validation_result['passed']) else "❌ Schema issues"
        lines.append(f"**Schema**: {schema_status}  ")

        quality_gate = validation_result.get('quality_gate_passed')
        threshold = validation_result.get('quality_gate_threshold')
        if quality_gate is not None:
            icon = "✅" if quality_gate else "⚠️"
            threshold_pct = f"{threshold * 100:.0f}%" if isinstance(threshold, (int, float)) and threshold else "n/a"
            lines.append(f"**Quality Gate ({threshold_pct} stride pass)**: {icon} {validation_result['stats']['pass_rate']:.1%}  ")
        else:
            lines.append(f"**Pass Rate**: {validation_result['stats']['pass_rate']:.1%}  ")

        lines.append("")
        
        # Validation summary
        lines.append("## Summary")
        lines.append(f"- **Phase Structure**: {'✅ Valid' if validation_result['phase_valid'] else '❌ Invalid'}")
        lines.append(f"- **Tasks Validated**: {validation_result['stats']['num_tasks']}")
        lines.append(f"- **Total Checks**: {validation_result['stats']['total_checks']:,}")
        lines.append(f"- **Violations**: {validation_result['stats']['total_violations']:,}")
        lines.append("")
        
        # Velocity validation summary
        if velocity_results:
            lines.append("## Velocity Validation")
            lines.append("")
            
            # Count velocity validation results
            velocity_passed = 0
            velocity_failed = 0
            velocity_calculated_only = 0
            velocity_errors = 0
            
            for var_name, result in velocity_results.items():
                status = result.get('status', 'unknown')
                if status == 'passed':
                    velocity_passed += 1
                elif status == 'failed':
                    velocity_failed += 1
                elif status == 'calculated_only':
                    velocity_calculated_only += 1
                else:
                    velocity_errors += 1
            
            total_velocity_vars = len(velocity_results)
            
            lines.append(f"- **Variables Tested**: {total_velocity_vars}")
            lines.append(f"- **✅ Passed**: {velocity_passed}")
            lines.append(f"- **❌ Failed**: {velocity_failed}")
            lines.append(f"- **⚠️ Calculated Only**: {velocity_calculated_only}")
            if velocity_errors > 0:
                lines.append(f"- **🚫 Errors**: {velocity_errors}")
            lines.append("")
            
            # Add detailed results for failed variables
            if velocity_failed > 0:
                lines.append("### Failed Velocity Variables")
                lines.append("")
                lines.append("Variables where calculated velocities (dθ/dt = dθ/dφ × dφ/dt) significantly differ from stored velocities:")
                lines.append("")
                
                for var_name, result in velocity_results.items():
                    if result.get('status') == 'failed':
                        failed_strides = result.get('failing_stride_count', 0)
                        mean_error = result.get('mean_error', 0)
                        var_error = result.get('variance_error', 0)
                        max_error = result.get('max_error', 0)
                        
                        lines.append(f"**{var_name}**:")
                        lines.append(f"- Failed strides: {failed_strides}")
                        lines.append(f"- Mean error: {mean_error:.4f} rad/s")
                        lines.append(f"- Variance: {var_error:.6f} (rad/s)²")
                        lines.append(f"- Max error: {max_error:.4f} rad/s")
                        lines.append("")
            
            # Add note about calculated-only variables
            if velocity_calculated_only > 0:
                lines.append("### Calculated-Only Variables")
                lines.append("")
                lines.append("Variables without stored velocity data (validation shows calculated velocities only):")
                lines.append("")
                
                calc_only_vars = [var for var, result in velocity_results.items() 
                                if result.get('status') == 'calculated_only']
                for var in calc_only_vars:
                    lines.append(f"- `{var}`")
                lines.append("")
        
        # Plots section
        if plot_paths:
            lines.append("## Validation Plots")
            lines.append("")
            lines.append("**Legend**: 🟢 Green = Passing strides, 🔴 Red = Biomechanical failures, 🔵 Blue = Velocity-only failures")
            lines.append("")
            
            # Get sagittal features to count validated features
            sagittal_features = get_sagittal_features()
            
            # Process each task with its combined plot
            tasks_processed = set()
            for key in sorted(plot_paths.keys()):
                # Skip histogram keys for now
                if key.endswith('_histogram'):
                    continue
                    
                task = key
                tasks_processed.add(task)
                
                # Task header
                lines.append(f"### {task.replace('_', ' ').title()}")
                lines.append("")
                
                # Add summary
                lines.append(f"*All {len(sagittal_features)} sagittal plane features validated*")
                lines.append("")
                
                # Add the combined plot
                # Calculate relative path from validation_reports to validation_plots
                plot_file = Path(plot_paths[task]).name
                rel_path = f"../validation_plots/{plot_file}"
                lines.append(f"![{task.replace('_', ' ').title()} Validation]({rel_path})")
                lines.append("")
                
                # Add histogram if it exists
                histogram_key = f"{task}_histogram"
                if histogram_key in plot_paths:
                    lines.append("#### Subject Failure Distribution")
                    lines.append("")
                    histogram_file = Path(plot_paths[histogram_key]).name
                    histogram_rel_path = f"../validation_plots/{histogram_file}"
                    lines.append(f"![{task.replace('_', ' ').title()} Subject Failures]({histogram_rel_path})")
                    lines.append("")
        
        
        # Write report
        with open(report_path, 'w') as f:
            f.write('\n'.join(lines))
        
        return report_path
    
    def update_dataset_documentation(self, dataset_path: str, generate_plots: bool = True, generate_comparison: bool = True, short_code: Optional[str] = None) -> str:
        """
        Update dataset documentation with validation results.
        
        Args:
            dataset_path: Path to dataset to validate
            generate_plots: Whether to generate validation plots
            generate_comparison: Whether to generate comparison plots
            short_code: Optional short code for the dataset (e.g., 'UM21', 'GT23')
            
        Returns:
            Path to updated documentation file
        """
        dataset_name = Path(dataset_path).stem
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Archive the ranges file
        self.ranges_archive_path, self.ranges_hash = self._archive_ranges_file(dataset_name, timestamp)
        
        # Run validation
        validation_result = self.validator.validate(dataset_path)
        
        # Generate plots if requested
        plot_paths = {}
        velocity_results = None
        if generate_plots:
            plot_paths, velocity_results = self._generate_plots(dataset_path, validation_result, timestamp)
        
        # Generate comparison plots if requested
        if generate_comparison:
            self._generate_comparison_plots(dataset_path, timestamp)
        
        # Find the corresponding dataset documentation file
        doc_name = dataset_name.replace('_phase', '').replace('_time', '')
        doc_path = self.docs_dir / f"dataset_{doc_name}.md"
        
        if not doc_path.exists():
            print(f"Warning: Dataset documentation not found at {doc_path}")
            print(f"Creating new documentation file...")
            self._create_new_documentation(doc_path, doc_name, dataset_path, short_code)
        
        # Get velocity results for documentation
        if velocity_results is None:
            # Load and validate velocity consistency if not done yet
            import pandas as pd
            dataset = pd.read_parquet(dataset_path)
            velocity_results = self.validate_velocity_consistency(dataset)
        
        # Generate validation section content
        validation_section = self._generate_validation_section(
            dataset_name, 
            validation_result, 
            plot_paths, 
            timestamp,
            dataset_path,
            velocity_results
        )
        
        # Read existing documentation
        with open(doc_path, 'r') as f:
            content = f.read()
        
        # Remove ALL existing validation sections (there might be duplicates)
        validation_marker = "## Data Validation"
        if validation_marker in content:
            import re
            
            # Split content at first validation section and keep everything before it
            validation_start = content.find(validation_marker)
            if validation_start != -1:
                # Keep everything before the first validation section
                content_before = content[:validation_start].rstrip()
                
                # Look for the footer (--- separator) after validation sections
                footer_pattern = r'\n---\n\*Last Updated:.*'
                footer_match = re.search(footer_pattern, content, re.DOTALL)
                
                if footer_match:
                    # Keep the footer
                    footer_content = footer_match.group(0)
                    new_content = content_before + '\n\n' + validation_section + '\n' + footer_content
                else:
                    # No footer found, just append validation section
                    new_content = content_before + '\n\n' + validation_section
            else:
                # Validation marker not found (shouldn't happen), just append
                new_content = content.rstrip() + '\n\n' + validation_section
        else:
            # Append before the final separator or at the end
            if '\n---\n*Last Updated:' in content:
                # Insert before the footer
                parts = content.rsplit('\n---\n*Last Updated:', 1)
                new_content = parts[0] + '\n\n' + validation_section + '\n---\n*Last Updated:' + parts[1]
            else:
                # Just append at the end
                new_content = content.rstrip() + '\n\n' + validation_section
        
        # Write updated documentation
        with open(doc_path, 'w') as f:
            f.write(new_content)
        
        return str(doc_path)
    
    def _generate_validation_section(self, dataset_name: str, validation_result: Dict,
                                    plot_paths: Dict, timestamp: str, dataset_path: str, 
                                    velocity_results: Optional[Dict[str, Dict]] = None) -> str:
        """Generate validation section for dataset documentation."""
        lines = []
        lines.append("## Data Validation")
        lines.append("")
        lines.append('<div class="validation-summary" markdown>')
        lines.append("")
        lines.append("### 📊 Validation Status")
        lines.append("")
        lines.append("**Validation Configuration:**")
        lines.append(f"- **Ranges File**: `{self.ranges_file_path.name}`")
        if self.ranges_hash:
            lines.append(f"- **SHA256**: `{self.ranges_hash[:8]}...` (first 8 chars)")
        if self.ranges_archive_path:
            archive_rel_path = f"validation_archives/{self.ranges_archive_path.name}"
            lines.append(f"- **Archived Copy**: [`{self.ranges_archive_path.name}`]({archive_rel_path})")
        lines.append("")
        
        # Create status table
        lines.append("| Metric | Value | Status |")
        lines.append("|--------|-------|--------|")
        
        # Overall status
        pass_rate = validation_result['stats']['pass_rate']
        if pass_rate >= 0.95:
            status_icon = "✅"
            status_text = "PASSED"
        elif pass_rate >= 0.80:
            status_icon = "⚠️"
            status_text = "PARTIAL"
        else:
            status_icon = "❌"
            status_text = "FAILED"
        
        lines.append(f"| **Overall Status** | {pass_rate:.1%} Valid | {status_icon} {status_text} |")
        
        # Phase structure
        phase_status = "✅ Valid" if validation_result['phase_valid'] else "❌ Invalid"
        lines.append(f"| **Phase Structure** | 150 points/cycle | {phase_status} |")
        
        # Tasks validated
        num_tasks = validation_result['stats']['num_tasks']
        lines.append(f"| **Tasks Validated** | {num_tasks} tasks | ✅ Complete |")
        
        # Total checks
        lines.append(f"| **Total Checks** | {validation_result['stats']['total_checks']:,} | - |")
        
        # Violations
        violations = validation_result['stats']['total_violations']
        if violations == 0:
            viol_status = "✅ None"
        elif violations < 1000:
            viol_status = "⚠️ Minor"
        else:
            viol_status = "⚠️ Present"
        lines.append(f"| **Violations** | {violations:,} | {viol_status} |")
        
        lines.append("")
        
        # Velocity consistency validation
        lines.append("### 🔄 Velocity Consistency Validation")
        lines.append("")
        
        # Use velocity results from plot generation (avoid duplicate validation)
        if velocity_results is None or len(velocity_results) == 0:
            # Fallback: load dataset and run velocity validation if not provided
            print("⚠️  Running fallback velocity validation (should not happen)")
            import pandas as pd
            df = pd.read_parquet(dataset_path)
            velocity_results = self.validate_velocity_consistency(df)
            self._log_memory("velocity_fallback", "Fallback velocity validation completed")
        
        # Handle case where velocity_results might be empty due to memory limits
        if not velocity_results or 'error' in velocity_results:
            lines.append(f"⚠️ **Velocity validation skipped**: {velocity_results['error']}")
            lines.append("")
        else:
            lines.append("Validates that velocities match angles using the chain rule: `dθ/dt = (dθ/dφ) × (dφ/dt)`")
            lines.append("")
            lines.append("| Velocity Variable | Status | Mean Error (rad/s) | Max Error (rad/s) | Strides Checked |")
            lines.append("|-------------------|--------|-------------------|-------------------|-----------------|")
            
            # Sort results by variable name
            for vel_var in sorted(velocity_results.keys()):
                result = velocity_results[vel_var]
                
                # Determine status icon and text
                if result['status'] == 'pass':
                    status = "✅ Pass"
                elif result['status'] == 'fail':
                    status = "❌ Fail"
                elif result['status'] == 'calculated_only':
                    status = "🔄 Calculated"
                elif result['status'] == 'angle_missing':
                    status = "⚠️ N/A"
                else:
                    status = "❓ Unknown"
                
                # Format error values
                if 'mean_error' in result:
                    mean_err = f"{result['mean_error']:.3f}"
                    max_err = f"{result['max_error']:.3f}"
                    num_strides = f"{result['num_strides']}/{result['total_strides']}"
                else:
                    mean_err = "-"
                    max_err = "-"
                    num_strides = result.get('message', '-')
                
                # Format variable name for display
                vel_var_display = vel_var.replace('_', ' ').replace(' rad s', ' (rad/s)')
                
                lines.append(f"| {vel_var_display} | {status} | {mean_err} | {max_err} | {num_strides} |")
            
            lines.append("")
            lines.append("**Legend**:")
            lines.append("- ✅ **Pass**: Mean error < 0.5 rad/s between stored and calculated velocities")
            lines.append("- ❌ **Fail**: Mean error ≥ 0.5 rad/s (velocities inconsistent with angles)")
            lines.append("- 🔄 **Calculated**: No stored velocities; values computed from angles")
            lines.append("- ⚠️ **N/A**: Corresponding angle data not available")
            lines.append("")
        
        # Task-specific validation plots
        if plot_paths:
            lines.append("### 📈 Task-Specific Validation")
            lines.append("")
            
            # Get sagittal features to count validated features
            sagittal_features = get_sagittal_features()
            num_features = len(sagittal_features)
            
            # Process tasks (skip histogram keys)
            tasks_processed = set()
            for key in sorted(plot_paths.keys()):
                # Skip histogram keys for now
                if key.endswith('_histogram'):
                    continue
                    
                task = key
                tasks_processed.add(task)
                
                # Format task name
                task_display = task.replace('_', ' ').title()
                
                lines.append(f"#### {task_display}")
                
                # Add validation plot
                plot_file = Path(plot_paths[task]).name
                rel_path = f"validation_plots/{plot_file}"
                lines.append(f"![{task_display}]({rel_path})")
                
                # Add task-specific pass rate if available
                if 'task_stats' in validation_result and task in validation_result['task_stats']:
                    task_pass_rate = validation_result['task_stats'][task]['pass_rate']
                    lines.append(f"*{num_features} sagittal features validated • {task_pass_rate:.1%} pass rate*")
                else:
                    lines.append(f"*{num_features} sagittal features validated*")
                lines.append("")
                
                # Add histogram if it exists
                histogram_key = f"{task}_histogram"
                if histogram_key in plot_paths:
                    lines.append(f"**Subject Failure Distribution:**")
                    histogram_file = Path(plot_paths[histogram_key]).name
                    histogram_rel_path = f"validation_plots/{histogram_file}"
                    lines.append(f"![{task_display} Subject Failures]({histogram_rel_path})")
                    lines.append("")
        
        lines.append("</div>")
        lines.append("")
        lines.append(f"**Last Validated**: {timestamp}")
        
        return '\n'.join(lines)
    
    def _create_new_documentation(self, doc_path: Path, doc_name: str, dataset_path: str, short_code: Optional[str] = None):
        """
        Create a comprehensive documentation template with auto-filled data.
        
        Args:
            doc_path: Path where documentation will be created
            doc_name: Name of the dataset (extracted from filename)
            dataset_path: Path to the actual dataset file
            short_code: Optional short code for the dataset
        """
        # Load dataset to extract information
        try:
            import pandas as pd
            df = pd.read_parquet(dataset_path)
            
            # Extract subject information
            subjects = sorted(df['subject'].unique())
            num_subjects = len(subjects)
            
            # Determine population type from subject IDs
            population_codes = set()
            for subject in subjects:
                # Extract population code (AB, TF, TT, etc.)
                parts = subject.split('_')
                if len(parts) >= 3:
                    pop_code = parts[-1][:2]  # First 2 chars of last part (e.g., 'AB' from 'AB01')
                    population_codes.add(pop_code)
            
            # Map population codes to descriptions
            pop_map = {
                'AB': 'Able-bodied',
                'TF': 'Transfemoral amputee',
                'TT': 'Transtibial amputee'
            }
            populations = [pop_map.get(code, code) for code in sorted(population_codes)]
            population_str = ', '.join(populations)
            
            # Extract tasks
            tasks = sorted(df['task'].unique())
            
            # Get data shape info
            num_rows = len(df)
            num_cols = len(df.columns)
            
            # Determine subject ID format
            if short_code:
                # Use the population code from actual data
                pop_code = sorted(population_codes)[0] if population_codes else "XX"
                subject_id_format = f"`{short_code}_{pop_code}##`"
                subject_list_str = f"{short_code}_{pop_code}01 - {short_code}_{pop_code}{num_subjects:02d}"
            else:
                # Extract pattern from first subject
                first_subject = subjects[0] if subjects else "Unknown"
                # Try to extract the base pattern
                subject_base = '_'.join(first_subject.split('_')[:-1]) if '_' in first_subject else first_subject
                subject_id_format = f"`{subject_base}_XX##`"
                subject_list_str = ', '.join(subjects[:3]) + (f' ... ({num_subjects} total)' if num_subjects > 3 else '')
            
        except Exception as e:
            print(f"Warning: Could not extract all information from dataset: {e}")
            # Fallback values
            num_subjects = "[TODO: Count subjects]"
            subject_list_str = "[TODO: List subject IDs]"
            subject_id_format = f"`{short_code or '[TODO: Add short code]'}_XX##`"
            population_str = "[TODO: Specify population type]"
            tasks = []
            num_rows = "[TODO: Add row count]"
            num_cols = "[TODO: Add column count]"
        
        # Generate content
        content = f"""# {doc_name.replace('_', ' ').title()} Dataset

## Overview

**Brief Description**: [TODO: Add comprehensive description of dataset purpose and scope]

**Collection Year**: [TODO: Add year(s) of data collection]

**Institution**: [TODO: Add institution name and department]

**Principal Investigators**: [TODO: Add PI names and labs]

## Citation Information

### Primary Citation
```
[TODO: Add primary citation in standard format]
```

### Associated Publications
[TODO: Add related publications if any]

### Acknowledgments
[TODO: Add funding sources and acknowledgments]

## Dataset Contents

### Subjects
- **Total Subjects**: {num_subjects} ({subject_list_str})
- **Subject ID Format**: {subject_id_format} (Dataset: {doc_name.replace('_', ' ').title()}, Population: {population_str})
- **Demographics**:
  - Age Range: [TODO: Add age range]
  - Sex Distribution: [TODO: Add M/F distribution]
  - Height Range: [TODO: Add height range in mm]
  - Weight Range: [TODO: Add weight range in kg]
  - Mean Age: [TODO: Add mean age]
  - Mean Weight: [TODO: Add mean weight]
  - Mean Height: [TODO: Add mean height]
- **Population**: {population_str}

### Tasks Included
| Task ID | Task Description | Duration/Cycles | Conditions | Notes |
|---------|------------------|-----------------|------------|-------|"""
        
        # Add tasks if available
        if tasks:
            for task in tasks:
                task_display = task.replace('_', ' ').title()
                content += f"\n| {task} | {task_display} | Continuous | [TODO: Add conditions] | [TODO: Add notes] |"
        else:
            content += "\n| [TODO: Add tasks] | [TODO: Add descriptions] | [TODO: Add duration] | [TODO: Add conditions] | [TODO: Add notes] |"
        
        content += f"""

### Data Columns (Standardized Format)
- **Variables**: {num_cols} columns including biomechanical features
- **Format**: Phase-indexed (150 points per gait cycle)
- **File**: `converted_datasets/{doc_name}_phase.parquet`
- **Units**: All angles in radians, moments normalized by body weight (Nm/kg)

## Contact Information
- **Dataset Curator**: [TODO: Add curator name and title]
- **Lab Website**: [TODO: Add lab website URL]
- **Lab Email**: [TODO: Add contact email]
- **Technical Support**: [TODO: Add support contact]

## Usage

```python
from locohub import LocomotionData

# Load the dataset
data = LocomotionData('converted_datasets/{doc_name}_phase.parquet')

# Get data for analysis
cycles_3d, features = data.get_cycles('SUB01', 'level_walking')
```

---
*Last Updated: {datetime.now().strftime("%B %Y")}*
"""
        
        with open(doc_path, 'w') as f:
            f.write(content)
        
        # Count TODOs
        todo_count = content.count('[TODO:')
        if todo_count > 0:
            print(f"📝 Created documentation template with {todo_count} items to complete")
            print(f"   Use your preferred editor or Claude Code to fill in the [TODO:] sections")


