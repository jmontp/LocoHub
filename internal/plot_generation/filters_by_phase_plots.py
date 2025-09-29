"""
Filters by phase plotting for validation reports - Version 3.
This version implements single-feature plots with pass/fail columns,
matching the style from interactive_validation_tuner.py.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.collections import LineCollection
from pathlib import Path
import warnings
import sys

# Import for memory monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Add parent directories to path for imports
current_dir = Path(__file__).parent
repo_root = current_dir.parent.parent
sys.path.insert(0, str(repo_root))

# Import feature definitions from user library
from user_libs.python.feature_constants import get_sagittal_features, get_task_classification

# Removed: validate_task_completeness (no longer needed in unified system)


def _get_memory_aware_plot_params(n_features: int, base_width: float = 14.0, base_height_per_feature: float = 2.0) -> Tuple[Tuple[float, float], float, float]:
    """
    Get memory-aware plot parameters based on current memory usage.
    
    Adjusts figure size, DPI, and line parameters to reduce memory consumption
    when approaching the 95% memory circuit breaker limit.
    
    Args:
        n_features: Number of features to plot (affects base figure height)
        base_width: Base figure width in inches
        base_height_per_feature: Base height per feature in inches
        
    Returns:
        Tuple of (figsize, dpi, linewidth) where:
        - figsize: (width, height) in inches
        - dpi: Dots per inch for matplotlib
        - linewidth: Line thickness for plot lines
    """
    # Default high-quality parameters
    default_dpi = 100
    default_linewidth = 0.5
    base_figsize = (base_width, max(6, n_features * base_height_per_feature))
    
    if not PSUTIL_AVAILABLE:
        return base_figsize, default_dpi, default_linewidth
    
    try:
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Aggressive memory reduction as we approach circuit breaker
        if memory_percent > 90:
            # Critical memory pressure - use minimal quality settings
            scale_factor = 0.6
            dpi = 60
            linewidth = 0.3
        elif memory_percent > 85:
            # High memory pressure - reduce quality moderately  
            scale_factor = 0.7
            dpi = 70
            linewidth = 0.35
        elif memory_percent > 80:
            # Moderate memory pressure - slight reduction
            scale_factor = 0.85
            dpi = 85
            linewidth = 0.4
        else:
            # Normal memory usage - full quality
            scale_factor = 1.0
            dpi = default_dpi
            linewidth = default_linewidth
            
        # Scale figure size
        scaled_figsize = (base_figsize[0] * scale_factor, base_figsize[1] * scale_factor)
        
        return scaled_figsize, dpi, linewidth
        
    except Exception:
        # Fall back to defaults if memory monitoring fails
        return base_figsize, default_dpi, default_linewidth


def _create_line_collection(phase_data, stride_data, color, alpha, linewidth, rasterized=True):
    """
    Create a LineCollection from stride data for memory-efficient plotting.
    
    Args:
        phase_data: Array of phase values (x-axis)
        stride_data: 2D array where each row is a stride (shape: n_strides x n_points)
        color: Line color
        alpha: Line transparency
        linewidth: Line width
        rasterized: Whether to rasterize the collection
        
    Returns:
        LineCollection object ready to be added to an axis
    """
    segments = []
    for stride in stride_data:
        points = np.column_stack([phase_data, stride])
        segments.append(points)
    
    lc = LineCollection(segments, colors=color, alpha=alpha, linewidths=linewidth, rasterized=rasterized)
    return lc


def create_single_feature_plot(
    validation_data: Dict,
    task_name: str,
    var_name: str,
    var_label: str,
    output_dir: str,
    data: Optional[np.ndarray] = None,
    failing_features: Optional[Dict[int, List[str]]] = None,
    dataset_name: Optional[str] = None,
    timestamp: Optional[str] = None
) -> str:
    """
    Create a single-feature validation plot with pass/fail columns.
    
    Args:
        validation_data: Parsed validation data with ranges
        task_name: Name of the task
        var_name: Variable name to plot
        var_label: Display label for the variable
        output_dir: Directory to save the plot
        data: Optional numpy array with shape (num_strides, 150, num_features)
        failing_features: Dict mapping stride indices to lists of failed variable names
        dataset_name: Optional dataset name to display
        timestamp: Optional timestamp to display
        
    Returns:
        Path to the generated plot
    """
    if task_name not in validation_data:
        raise ValueError(f"Task {task_name} not found in validation data")
    
    task_data = validation_data[task_name]
    
    # Extract phases dynamically from the validation data
    phases = sorted([int(p) for p in task_data.keys() if str(p).isdigit()])
    
    # Add 100% for cyclical completion if not present
    if 100 not in phases and 0 in task_data:
        phases.append(100)
        task_data[100] = task_data[0].copy()
    
    task_type = get_task_classification(task_name)
    
    # Create figure with 1 row, 2 columns (pass/fail) - with memory-aware parameters
    figsize, dpi, linewidth = _get_memory_aware_plot_params(1, base_width=14.0, base_height_per_feature=3.0)
    fig, (ax_pass, ax_fail) = plt.subplots(1, 2, figsize=figsize, dpi=dpi)
    
    # Build title
    task_type_label = "Gait-Based Task" if task_type == 'gait' else "Bilateral Symmetric Task"
    title = f'{task_name.replace("_", " ").title()} - {var_label}\n{task_type_label}'
    if dataset_name:
        title += f'\nDataset: {dataset_name}'
    if timestamp:
        title += f' | Generated: {timestamp}'
    
    fig.suptitle(title, fontsize=12, fontweight='bold')
    
    # Handle failing features
    if failing_features is None:
        failing_features = {}
    
    # Since we're receiving single-feature data with shape (n_strides, 150, 1),
    # the feature is always at index 0
    var_idx = 0 if data is not None and data.size > 0 and data.shape[2] > 0 else None
    
    # Build global set of failed stride indices for ANY variable
    global_failed_strides = set()
    for stride_idx, failed_vars in failing_features.items():
        # Check if any variable failed for this stride
        if failed_vars:  # If any variable failed
            global_failed_strides.add(stride_idx)
    
    # Build variable-specific failed strides
    variable_failed_strides = set()
    for stride_idx, failed_vars in failing_features.items():
        if var_name in failed_vars:
            variable_failed_strides.add(stride_idx)
    
    # Get validation ranges for this variable
    var_ranges = {}
    for phase in phases:
        if phase in task_data and var_name in task_data[phase]:
            var_ranges[phase] = task_data[phase][var_name]
    
    # Determine y-axis range
    all_mins = []
    all_maxs = []
    
    # Include validation ranges
    for phase, ranges in var_ranges.items():
        if 'min' in ranges and 'max' in ranges:
            min_val = ranges['min']
            max_val = ranges['max']
            if min_val is not None and max_val is not None:
                if not (np.isinf(min_val) or np.isinf(max_val) or np.isnan(min_val) or np.isnan(max_val)):
                    all_mins.append(min_val)
                    all_maxs.append(max_val)
    
    # Include actual data range if available
    if data is not None and data.size > 0 and var_idx is not None:
        data_values = data[:, :, var_idx]
        # Check if data slice is not all NaN before computing min/max
        if not np.isnan(data_values).all():
            data_min = np.nanmin(data_values)
            data_max = np.nanmax(data_values)
            if not (np.isinf(data_min) or np.isinf(data_max) or np.isnan(data_min) or np.isnan(data_max)):
                all_mins.append(data_min)
                all_maxs.append(data_max)
    
    if all_mins and all_maxs:
        y_min = min(all_mins) - 0.1 * (max(all_maxs) - min(all_mins))
        y_max = max(all_maxs) + 0.1 * (max(all_maxs) - min(all_mins))
    else:
        y_min, y_max = -1, 1
    
    # Determine unit and conversion
    if var_name.endswith('_rad_s'):
        units = 'rad/s'
        value_conversion = np.degrees  # Convert rad/s to deg/s
        unit_suffix = '°/s'
    elif var_name.endswith('_rad'):
        units = 'rad'
        value_conversion = np.degrees
        unit_suffix = '°'
    elif var_name.endswith('_Nm'):
        units = 'Nm'
        value_conversion = lambda x: x
        unit_suffix = ''
    else:
        units = ''
        value_conversion = lambda x: x
        unit_suffix = ''
    
    # Plot PASSED strides (left column)
    passed_count = 0
    if data is not None and data.size > 0 and var_idx is not None:
        phase_ipsi = np.linspace(0, 100, 150)
        
        # Collect all passing strides
        passing_strides = []
        for stride_idx in range(data.shape[0]):
            if stride_idx not in global_failed_strides:
                passing_strides.append(data[stride_idx, :, var_idx])
                passed_count += 1
        
        # Plot all passing strides at once using LineCollection
        if passing_strides:
            passing_array = np.array(passing_strides)
            lc = _create_line_collection(phase_ipsi, passing_array, 'green', 0.3, linewidth, rasterized=True)
            ax_pass.add_collection(lc)
    
    # Plot validation ranges on pass axis
    _plot_validation_ranges(ax_pass, var_ranges, phases, 'lightgreen', value_conversion, unit_suffix)
    
    if data is None or data.size == 0:
        ax_pass.text(50, (y_min + y_max) / 2, 'Data Not Available', 
                    ha='center', va='center', fontsize=12, color='gray', alpha=0.7)
    
    ax_pass.set_title(f'{var_label} - ✓ Passed ({passed_count} strides)', fontsize=10, fontweight='bold')
    ax_pass.set_xlim(-5, 105)
    ax_pass.set_ylim(y_min, y_max)
    ax_pass.set_xticks([0, 25, 50, 75, 100])
    ax_pass.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
    ax_pass.set_ylabel(units, fontsize=9)
    ax_pass.grid(True, alpha=0.3)
    x_label = 'Gait Phase' if task_type == 'gait' else 'Movement Phase'
    ax_pass.set_xlabel(x_label, fontsize=10)
    
    # Plot FAILED strides (right column)
    failed_count = 0
    if data is not None and data.size > 0 and var_idx is not None:
        # Collect all failed strides
        failed_strides = []
        for stride_idx in range(data.shape[0]):
            if stride_idx in variable_failed_strides:
                failed_strides.append(data[stride_idx, :, var_idx])
                failed_count += 1
        
        # Plot all failed strides at once using LineCollection
        if failed_strides:
            failed_array = np.array(failed_strides)
            lc = _create_line_collection(phase_ipsi, failed_array, 'red', 0.4, linewidth, rasterized=True)
            ax_fail.add_collection(lc)
    
    # Plot validation ranges on fail axis
    _plot_validation_ranges(ax_fail, var_ranges, phases, 'lightcoral', value_conversion, unit_suffix)
    
    if data is None or data.size == 0:
        ax_fail.text(50, (y_min + y_max) / 2, 'Data Not Available', 
                    ha='center', va='center', fontsize=12, color='gray', alpha=0.7)
    
    ax_fail.set_title(f'{var_label} - ✗ Failed ({failed_count} strides)', fontsize=10, fontweight='bold')
    ax_fail.set_xlim(-5, 105)
    ax_fail.set_ylim(y_min, y_max)
    ax_fail.set_xticks([0, 25, 50, 75, 100])
    ax_fail.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
    ax_fail.grid(True, alpha=0.3)
    ax_fail.set_xlabel(x_label, fontsize=10)
    
    # Add degree conversion on right y-axis for angular variables
    if var_name.endswith('_rad_s'):
        ax2_pass = ax_pass.twinx()
        ax2_pass.set_ylim(value_conversion(y_min), value_conversion(y_max))
        ax2_pass.set_ylabel('deg/s', fontsize=9)
        
        ax2_fail = ax_fail.twinx()
        ax2_fail.set_ylim(value_conversion(y_min), value_conversion(y_max))
        ax2_fail.set_ylabel('deg/s', fontsize=9)
    elif var_name.endswith('_rad'):
        ax2_pass = ax_pass.twinx()
        ax2_pass.set_ylim(value_conversion(y_min), value_conversion(y_max))
        ax2_pass.set_ylabel('degrees', fontsize=9)
        
        ax2_fail = ax_fail.twinx()
        ax2_fail.set_ylim(value_conversion(y_min), value_conversion(y_max))
        ax2_fail.set_ylabel('degrees', fontsize=9)
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.93])
    
    # Save the plot with variable name in filename
    safe_var_name = var_name.replace('/', '_')
    if dataset_name:
        output_path = Path(output_dir) / f"{dataset_name}_{task_name}_{safe_var_name}.png"
    else:
        output_path = Path(output_dir) / f"{task_name}_{safe_var_name}.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return str(output_path)


def create_task_combined_plot(
    validation_data: Dict,
    task_name: str,
    output_dir: str,
    data_3d: Optional[np.ndarray] = None,
    feature_names: Optional[List[str]] = None,
    failing_features: Optional[Dict] = None,  # Can be legacy or merged format
    dataset_name: Optional[str] = None,
    timestamp: Optional[str] = None,
    comparison_mode: bool = False,
    show_interactive: bool = False,
    show_local_passing: bool = False,
    use_column_names: bool = False
) -> str:
    """
    Create a combined validation plot with all features for a single task.
    
    Args:
        validation_data: Parsed validation data with ranges for this task
        task_name: Name of the task
        output_dir: Directory to save the plot
        data_3d: Optional numpy array with shape (num_strides, 150, num_features)
        feature_names: List of feature names corresponding to data_3d columns
        failing_features: Dict mapping stride indices to lists of failed variable names
        dataset_name: Optional dataset name to display
        timestamp: Optional timestamp to display
        comparison_mode: If True, generate single-column comparison plot (passing strides only)
        show_interactive: If True, show plot interactively instead of saving to file
        show_local_passing: If True, show locally passing strides in yellow/gold (pass current feature but fail others)
        use_column_names: If True, use actual column names instead of pretty labels
        
    Returns:
        Path to the generated plot (or empty string if shown interactively)
    """
    # ALWAYS use all sagittal features for consistent layout
    sagittal_features = get_sagittal_features()
    feature_labels = {f[0]: f[1] for f in sagittal_features}
    
    # Track which features have data available
    available_feature_names = set(feature_names) if feature_names else set()
    
    # Always use all 17 features for consistent plot height
    n_features = len(sagittal_features)
    
    # Memory-aware dimensions for consistency across all plots
    row_height = 2.0  # inches per feature row (base value)
    
    if comparison_mode:
        # Single column layout for comparison plots
        figsize, dpi, linewidth = _get_memory_aware_plot_params(n_features, base_width=7.0, base_height_per_feature=row_height)
        fig, axes = plt.subplots(n_features, 1, figsize=figsize, dpi=dpi)
        # Ensure axes is always 2D for consistent indexing
        if n_features == 1:
            axes = axes.reshape(1, 1)
        else:
            axes = axes.reshape(n_features, 1)
    else:
        # Original 2-column layout for validation plots
        if show_interactive:
            # For interactive display, ensure each row gets proper height
            # Don't limit the height - let matplotlib handle scrolling
            height_per_row = 2.5  # inches per feature row for good visibility
            total_height = n_features * height_per_row
            figsize = (14.0, total_height)  # Full height, no limiting
            dpi = 80  # Screen DPI
            linewidth = 0.5
        else:
            figsize, dpi, linewidth = _get_memory_aware_plot_params(n_features, base_width=14.0, base_height_per_feature=row_height)
        fig, axes = plt.subplots(n_features, 2, figsize=figsize, dpi=dpi)
        # Ensure axes is always 2D
        if n_features == 1:
            axes = axes.reshape(1, -1)
    
    # Calculate statistics for enhanced title
    total_strides = data_3d.shape[0] if data_3d is not None and data_3d.size > 0 else 0
    n_features_validated = len(available_feature_names)
    n_features_total = len(sagittal_features)
    
    # Count passing strides
    passing_strides = 0
    if total_strides > 0:
        for stride_idx in range(total_strides):
            if stride_idx not in failing_features:
                passing_strides += 1
    
    pass_rate = (passing_strides / total_strides * 100) if total_strides > 0 else 0
    
    # Build enhanced title with statistics
    task_type = get_task_classification(task_name)
    task_type_label = "Gait-Based Task" if task_type == 'gait' else "Bilateral Symmetric Task"
    
    if comparison_mode:
        title = f'{task_name.replace("_", " ").title()} - Clean Data Comparison\n{task_type_label}'
    else:
        title = f'{task_name.replace("_", " ").title()} - All Features Validation\n{task_type_label}'
    
    if dataset_name:
        title += f'\nDataset: {dataset_name}'
    if timestamp:
        title += f' | Generated: {timestamp}'
    
    # Handle failing features and detect format first
    if failing_features is None:
        failing_features = {}
    
    # Detect format: merged or legacy
    is_merged_format = False
    if failing_features:
        sample_value = next(iter(failing_features.values()))
        if isinstance(sample_value, dict) and 'biomechanical' in sample_value and 'velocity' in sample_value:
            is_merged_format = True
    
    # Build stride classification sets for three-color system
    if is_merged_format:
        # New three-color system
        biomechanical_failed_strides = set()
        velocity_only_failed_strides = set()
        global_failed_strides = set()
        
        for stride_idx, failure_types in failing_features.items():
            biomech_failures = failure_types.get('biomechanical', [])
            velocity_failures = failure_types.get('velocity', [])
            
            if biomech_failures:
                biomechanical_failed_strides.add(stride_idx)
                global_failed_strides.add(stride_idx)
            elif velocity_failures:
                velocity_only_failed_strides.add(stride_idx)
                global_failed_strides.add(stride_idx)
    else:
        # Legacy format - all failures are red
        global_failed_strides = set()
        biomechanical_failed_strides = set()
        velocity_only_failed_strides = set()
        
        for stride_idx, failed_vars in failing_features.items():
            if failed_vars:  # If any variable failed
                global_failed_strides.add(stride_idx)
                biomechanical_failed_strides.add(stride_idx)  # Treat all as biomechanical in legacy mode
    
    # Add statistics line
    if not comparison_mode:
        title += f'\n{total_strides} strides | {n_features_validated}/{n_features_total} features validated | {passing_strides} passing ({pass_rate:.1f}%)'
        
        # Add three-color legend in merged format
        if is_merged_format and (len(biomechanical_failed_strides) > 0 or len(velocity_only_failed_strides) > 0):
            legend_parts = ['Green: Pass']
            if len(biomechanical_failed_strides) > 0:
                legend_parts.append(f'Red: Biomech Fail ({len(biomechanical_failed_strides)})')
            if len(velocity_only_failed_strides) > 0:
                legend_parts.append(f'Blue: Velocity Fail ({len(velocity_only_failed_strides)})')
            title += f'\nLegend: {" | ".join(legend_parts)}'
    
    fig.suptitle(title, fontsize=12, fontweight='bold')
    
    # Extract phases from validation data
    phases = sorted([int(p) for p in validation_data.keys() if str(p).isdigit()])
    
    # Add 100% for cyclical completion if not present
    if 100 not in phases and 0 in validation_data:
        phases.append(100)
        validation_data[100] = validation_data[0].copy()
    
    # Process ALL sagittal features (always 17 rows)
    for feat_idx, (var_name, var_label) in enumerate(sagittal_features):
        # Choose which label to display based on use_column_names flag
        display_label = var_name if use_column_names else var_label
        
        if comparison_mode:
            # Single column - only pass axis
            ax_pass = axes[feat_idx, 0]
            ax_fail = None
        else:
            # Two columns - pass and fail axes
            ax_pass = axes[feat_idx, 0]
            ax_fail = axes[feat_idx, 1]
        
        # Check if this feature has data available
        has_data = var_name in available_feature_names
        
        # Get the index of this feature in the data array
        if has_data and feature_names and var_name in feature_names:
            var_idx = feature_names.index(var_name)
        else:
            var_idx = None
        
        # Build variable-specific failed strides for three-color system
        if is_merged_format:
            variable_biomech_failed_strides = set()
            variable_velocity_failed_strides = set()
            
            for stride_idx, failure_types in failing_features.items():
                biomech_failures = failure_types.get('biomechanical', [])
                velocity_failures = failure_types.get('velocity', [])
                
                if var_name in biomech_failures:
                    variable_biomech_failed_strides.add(stride_idx)
                elif var_name in velocity_failures:
                    variable_velocity_failed_strides.add(stride_idx)
            
            # For backward compatibility, also create combined set
            variable_failed_strides = variable_biomech_failed_strides | variable_velocity_failed_strides
        else:
            # Legacy format
            variable_failed_strides = set()
            variable_biomech_failed_strides = set()
            variable_velocity_failed_strides = set()
            
            for stride_idx, failed_vars in failing_features.items():
                if var_name in failed_vars:
                    variable_failed_strides.add(stride_idx)
                    variable_biomech_failed_strides.add(stride_idx)  # Treat all as biomechanical
        
        # Get validation ranges for this variable
        var_ranges = {}
        for phase in phases:
            if phase in validation_data and var_name in validation_data[phase]:
                var_ranges[phase] = validation_data[phase][var_name]
        
        # Determine y-axis range
        all_mins = []
        all_maxs = []
        
        # Include validation ranges
        for phase, ranges in var_ranges.items():
            if 'min' in ranges and 'max' in ranges:
                min_val = ranges['min']
                max_val = ranges['max']
                if min_val is not None and max_val is not None:
                    if not (np.isinf(min_val) or np.isinf(max_val) or np.isnan(min_val) or np.isnan(max_val)):
                        all_mins.append(min_val)
                        all_maxs.append(max_val)
        
        # Include actual data range if available
        if data_3d is not None and data_3d.size > 0 and var_idx is not None:
            data_values = data_3d[:, :, var_idx]
            # Check if data slice is not all NaN before computing min/max
            if not np.isnan(data_values).all():
                data_min = np.nanmin(data_values)
                data_max = np.nanmax(data_values)
                if not (np.isinf(data_min) or np.isinf(data_max) or np.isnan(data_min) or np.isnan(data_max)):
                    all_mins.append(data_min)
                    all_maxs.append(data_max)
        
        if all_mins and all_maxs:
            y_min = min(all_mins) - 0.1 * (max(all_maxs) - min(all_mins))
            y_max = max(all_maxs) + 0.1 * (max(all_maxs) - min(all_mins))
        else:
            y_min, y_max = -1, 1
        
        # Determine unit and conversion
        if var_name.endswith('_rad_s'):
            units = 'rad/s'
            value_conversion = np.degrees  # Convert rad/s to deg/s
            unit_suffix = '°/s'
        elif var_name.endswith('_rad'):
            units = 'rad'
            value_conversion = np.degrees
            unit_suffix = '°'
        elif var_name.endswith('_Nm'):
            units = 'Nm'
            value_conversion = lambda x: x
            unit_suffix = ''
        else:
            units = ''
            value_conversion = lambda x: x
            unit_suffix = ''
        
        # Plot PASSED strides (left column) - OPTIMIZED BATCH PLOTTING
        passed_count = 0
        local_passed_count = 0
        if has_data and data_3d is not None and data_3d.size > 0 and var_idx is not None:
            phase_ipsi = np.linspace(0, 100, 150)
            
            if show_local_passing:
                # Build variable-specific failed strides
                variable_failed_strides = set()
                if is_merged_format:
                    for stride_idx, failure_types in failing_features.items():
                        biomech_failures = failure_types.get('biomechanical', [])
                        velocity_failures = failure_types.get('velocity', [])
                        if var_name in biomech_failures or var_name in velocity_failures:
                            variable_failed_strides.add(stride_idx)
                else:
                    for stride_idx, failed_vars in failing_features.items():
                        if var_name in failed_vars:
                            variable_failed_strides.add(stride_idx)
                
                # Separate globally passing from locally passing
                global_passing_indices = [stride_idx for stride_idx in range(data_3d.shape[0]) 
                                        if stride_idx not in global_failed_strides]
                local_passing_indices = [stride_idx for stride_idx in range(data_3d.shape[0])
                                       if stride_idx not in variable_failed_strides and stride_idx in global_failed_strides]
                
                # Plot globally passing strides in green
                if global_passing_indices:
                    global_passing_data = data_3d[global_passing_indices, :, var_idx]
                    passed_count = len(global_passing_indices)
                    lc = _create_line_collection(phase_ipsi, global_passing_data, 'green', 0.3, linewidth, rasterized=True)
                    ax_pass.add_collection(lc)
                
                # Plot locally passing strides in gold/yellow
                if local_passing_indices:
                    local_passing_data = data_3d[local_passing_indices, :, var_idx]
                    local_passed_count = len(local_passing_indices)
                    lc = _create_line_collection(phase_ipsi, local_passing_data, 'gold', 0.3, linewidth, rasterized=True)
                    lc.set_zorder(2)
                    ax_pass.add_collection(lc)
            else:
                # Original logic - all non-globally-failed strides in green
                passing_indices = [stride_idx for stride_idx in range(data_3d.shape[0]) 
                                 if stride_idx not in global_failed_strides]
                
                if passing_indices:
                    # Extract all passing stride data at once - shape: (n_passing, 150)
                    passing_data = data_3d[passing_indices, :, var_idx]
                    passed_count = len(passing_indices)
                    
                    # Use LineCollection for all passing strides (memory efficient)
                    lc = _create_line_collection(phase_ipsi, passing_data, 'green', 0.3, linewidth, rasterized=True)
                    ax_pass.add_collection(lc)
        
        # Plot validation ranges on pass axis
        _plot_validation_ranges(ax_pass, var_ranges, phases, 'lightgreen', value_conversion, unit_suffix)
        
        if not has_data or data_3d is None or data_3d.size == 0 or var_idx is None:
            ax_pass.text(50, (y_min + y_max) / 2, 'Data Not Available', 
                        ha='center', va='center', fontsize=10, color='gray', alpha=0.7)
        
        # Compact title for subplot
        if show_local_passing and local_passed_count > 0:
            ax_pass.set_title(f'{display_label} ✓ ({passed_count} green, {local_passed_count} yellow)', fontsize=8, fontweight='bold')
        else:
            ax_pass.set_title(f'{display_label} ✓ ({passed_count})', fontsize=8, fontweight='bold')
        ax_pass.set_xlim(-5, 105)
        ax_pass.set_ylim(y_min, y_max)
        ax_pass.set_xticks([0, 25, 50, 75, 100])
        ax_pass.set_xticklabels(['0%', '25%', '50%', '75%', '100%'], fontsize=7)
        ax_pass.set_ylabel(units, fontsize=7)
        ax_pass.grid(True, alpha=0.3)
        ax_pass.tick_params(axis='y', labelsize=7)
        
        # Only add x-label to bottom row (always row 16, since we have 17 features)
        if feat_idx == len(sagittal_features) - 1:
            x_label = 'Gait Phase' if task_type == 'gait' else 'Movement Phase'
            ax_pass.set_xlabel(x_label, fontsize=8)
        
        # Plot FAILED strides (right column) - only in validation mode
        if not comparison_mode and ax_fail is not None:
            failed_count = 0
            biomech_failed_count = 0
            velocity_failed_count = 0
            
            if has_data and data_3d is not None and data_3d.size > 0 and var_idx is not None:
                # OPTIMIZED BATCH PLOTTING for failed strides
                
                # Collect indices for each failure type
                biomech_indices = [idx for idx in variable_biomech_failed_strides]
                velocity_indices = [idx for idx in variable_velocity_failed_strides]
                
                # Plot biomechanical failures in red (batch)
                if biomech_indices:
                    biomech_data = data_3d[biomech_indices, :, var_idx]
                    biomech_failed_count = len(biomech_indices)
                    lc = _create_line_collection(phase_ipsi, biomech_data, 'red', 0.4, linewidth, rasterized=True)
                    ax_fail.add_collection(lc)
                
                # Plot velocity failures in blue (batch)
                if velocity_indices:
                    velocity_data = data_3d[velocity_indices, :, var_idx]
                    velocity_failed_count = len(velocity_indices)
                    lc = _create_line_collection(phase_ipsi, velocity_data, 'blue', 0.4, linewidth, rasterized=True)
                    ax_fail.add_collection(lc)
                
                failed_count = biomech_failed_count + velocity_failed_count
            
            # Plot validation ranges on fail axis
            _plot_validation_ranges(ax_fail, var_ranges, phases, 'lightcoral', value_conversion, unit_suffix)
            
            if not has_data or data_3d is None or data_3d.size == 0 or var_idx is None:
                ax_fail.text(50, (y_min + y_max) / 2, 'Data Not Available', 
                            ha='center', va='center', fontsize=10, color='gray', alpha=0.7)
            
            # Enhanced title showing breakdown in three-color mode
            if is_merged_format and (biomech_failed_count > 0 or velocity_failed_count > 0):
                title_parts = []
                if biomech_failed_count > 0:
                    title_parts.append(f'R{biomech_failed_count}')
                if velocity_failed_count > 0:
                    title_parts.append(f'B{velocity_failed_count}')
                breakdown = ' '.join(title_parts)
                ax_fail.set_title(f'{display_label} ✗ ({breakdown})', fontsize=8, fontweight='bold')
            else:
                ax_fail.set_title(f'{display_label} ✗ ({failed_count})', fontsize=8, fontweight='bold')
            ax_fail.set_xlim(-5, 105)
            ax_fail.set_ylim(y_min, y_max)
            ax_fail.set_xticks([0, 25, 50, 75, 100])
            ax_fail.set_xticklabels(['0%', '25%', '50%', '75%', '100%'], fontsize=7)
            ax_fail.grid(True, alpha=0.3)
            ax_fail.tick_params(axis='y', labelsize=7)
            
            # Only add x-label to bottom row (always row 16)
            if feat_idx == len(sagittal_features) - 1:
                ax_fail.set_xlabel(x_label, fontsize=8)
        
        # Add degree conversion on right y-axis for angular variables
        if var_name.endswith('_rad_s'):
            ax2_pass = ax_pass.twinx()
            ax2_pass.set_ylim(value_conversion(y_min), value_conversion(y_max))
            ax2_pass.set_ylabel('deg/s', fontsize=7)
            ax2_pass.tick_params(axis='y', labelsize=7)
            
            # Only add fail axis degree conversion in validation mode
            if not comparison_mode and ax_fail is not None:
                ax2_fail = ax_fail.twinx()
                ax2_fail.set_ylim(value_conversion(y_min), value_conversion(y_max))
                ax2_fail.set_ylabel('deg/s', fontsize=7)
                ax2_fail.tick_params(axis='y', labelsize=7)
        elif var_name.endswith('_rad'):
            ax2_pass = ax_pass.twinx()
            ax2_pass.set_ylim(value_conversion(y_min), value_conversion(y_max))
            ax2_pass.set_ylabel('deg', fontsize=7)
            ax2_pass.tick_params(axis='y', labelsize=7)
            
            # Only add fail axis degree conversion in validation mode
            if not comparison_mode and ax_fail is not None:
                ax2_fail = ax_fail.twinx()
                ax2_fail.set_ylim(value_conversion(y_min), value_conversion(y_max))
                ax2_fail.set_ylabel('deg', fontsize=7)
                ax2_fail.tick_params(axis='y', labelsize=7)
        
        # AGGRESSIVE CLEANUP after each feature to prevent memory accumulation
        import gc
        # Clean up temporary data arrays that may have been created
        locals_to_delete = ['passing_data', 'biomech_data', 'velocity_data', 'passing_indices', 
                          'biomech_indices', 'velocity_indices', 'stride_data']
        for var_name_to_del in locals_to_delete:
            if var_name_to_del in locals():
                del locals()[var_name_to_del]
        
        # Force garbage collection after every few features to prevent accumulation
        if feat_idx % 5 == 0:  # Every 5 features
            gc.collect()
    
    # Only apply tight_layout for file saving, not interactive display
    if not show_interactive:
        plt.tight_layout(rect=[0, 0.02, 1, 0.985])
    
    # Save the plot (only if output_dir is provided)
    if show_interactive:
        # Skip path creation for interactive mode
        output_path = None
    elif comparison_mode:
        # Comparison plots use simpler naming: dataset_task.png
        if dataset_name:
            output_path = Path(output_dir) / f"{dataset_name}_{task_name}.png"
        else:
            output_path = Path(output_dir) / f"{task_name}_comparison.png"
    else:
        # Validation plots keep original naming
        if dataset_name:
            output_path = Path(output_dir) / f"{dataset_name}_{task_name}_all_features_validation.png"
        else:
            output_path = Path(output_dir) / f"{task_name}_all_features_validation.png"
    
    if show_interactive:
        # Configure for interactive display
        fig = plt.gcf()
        
        # The figure is already sized properly with each row having 2.5 inches
        # Just adjust the layout for better spacing
        plt.subplots_adjust(left=0.08, right=0.95, top=0.97, bottom=0.03, hspace=0.3, wspace=0.15)
        
        # Note: Don't call plt.show() here - let the caller handle it
        # This allows multiple plots to be accumulated before showing
        return ""  # No file path when showing interactively
    else:
        # Save to file as usual
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        return str(output_path)


def create_subject_failure_histogram(
    locomotion_data,
    task_name: str,
    failing_features: Dict[int, List[str]],
    output_dir: str,
    dataset_name: Optional[str] = None,
    timestamp: Optional[str] = None
) -> str:
    """
    Create a histogram showing the distribution of failed strides per subject.
    
    Args:
        locomotion_data: LocomotionData object with the dataset
        task_name: Name of the task being analyzed
        failing_features: Dict mapping stride indices to lists of failed variable names
        output_dir: Directory to save the plot
        dataset_name: Optional dataset name for the filename
        timestamp: Optional timestamp to display
        
    Returns:
        Path to the generated histogram
    """
    import matplotlib.pyplot as plt
    import numpy as np
    from collections import defaultdict
    
    # Get all subjects for this task
    subjects = locomotion_data.get_subjects()
    
    # Build mapping of stride indices to subjects
    stride_to_subject = {}
    current_stride_idx = 0
    
    for subject in subjects:
        # Get data for this subject and task
        subject_data = locomotion_data.df[
            (locomotion_data.df['subject'] == subject) & 
            (locomotion_data.df['task'] == task_name)
        ]
        
        if len(subject_data) == 0:
            continue
            
        # Count unique steps (strides) for this subject
        n_strides = len(subject_data['step'].unique())
        
        # Map stride indices to this subject
        for i in range(n_strides):
            stride_to_subject[current_stride_idx] = subject
            current_stride_idx += 1
    
    # Count failures per subject
    subject_failures = defaultdict(int)
    subject_totals = defaultdict(int)
    
    # Count total strides per subject
    for stride_idx, subject in stride_to_subject.items():
        subject_totals[subject] += 1
        # Check if this stride failed
        if stride_idx in failing_features and failing_features[stride_idx]:
            subject_failures[subject] += 1
    
    # Sort subjects for consistent ordering
    sorted_subjects = sorted(subject_totals.keys())
    
    # Prepare data for plotting
    subjects_list = []
    failures_list = []
    totals_list = []
    colors_list = []
    
    for subject in sorted_subjects:
        subjects_list.append(subject)
        failures = subject_failures[subject]
        total = subject_totals[subject]
        failures_list.append(failures)
        totals_list.append(total)
        
        # Color based on failure rate
        fail_rate = failures / total if total > 0 else 0
        if fail_rate < 0.1:
            colors_list.append('green')
        elif fail_rate < 0.3:
            colors_list.append('orange')
        else:
            colors_list.append('red')
    
    # Create the histogram with memory-aware parameters
    figsize, dpi, linewidth = _get_memory_aware_plot_params(1, base_width=10.0, base_height_per_feature=6.0)
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    
    # Create bars
    x_pos = np.arange(len(subjects_list))
    bars = ax.bar(x_pos, failures_list, color=colors_list, alpha=0.7)
    
    # Add value labels on top of bars
    for i, (failures, total) in enumerate(zip(failures_list, totals_list)):
        if total > 0:
            ax.text(i, failures + 0.5, f'{failures}/{total}', 
                   ha='center', va='bottom', fontsize=8)
    
    # Customize the plot
    ax.set_xlabel('Subject', fontsize=10)
    ax.set_ylabel('Number of Failed Strides', fontsize=10)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(subjects_list, rotation=45, ha='right')
    ax.grid(True, alpha=0.3, axis='y')
    
    # Build title
    title = f'{task_name.replace("_", " ").title()} - Failed Strides by Subject'
    if dataset_name:
        title += f'\nDataset: {dataset_name}'
    if timestamp:
        title += f' | Generated: {timestamp}'
    
    # Add summary statistics
    total_failures = sum(failures_list)
    total_strides = sum(totals_list)
    overall_rate = (total_failures / total_strides * 100) if total_strides > 0 else 0
    title += f'\nTotal: {total_failures}/{total_strides} failed ({overall_rate:.1f}%)'
    
    ax.set_title(title, fontsize=11, fontweight='bold')
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='green', alpha=0.7, label='<10% failure'),
        Patch(facecolor='orange', alpha=0.7, label='10-30% failure'),
        Patch(facecolor='red', alpha=0.7, label='>30% failure')
    ]
    ax.legend(handles=legend_elements, loc='upper right')
    
    plt.tight_layout()
    
    # Save the plot
    if dataset_name:
        output_path = Path(output_dir) / f"{dataset_name}_{task_name}_subject_failures.png"
    else:
        output_path = Path(output_dir) / f"{task_name}_subject_failures.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return str(output_path)


# Keep the old function for backward compatibility but mark as deprecated
def create_filters_by_phase_plot(
    validation_data: Dict, 
    task_name: str, 
    output_dir: str, 
    mode: str = 'kinematic',
    data: Optional[np.ndarray] = None, 
    violations: Optional[Dict[str, List[int]]] = None,
    failing_features: Optional[Dict[int, List[str]]] = None,
    dataset_name: Optional[str] = None, 
    timestamp: Optional[str] = None
) -> str:
    """
    Create a filters by phase plot with pass/fail separation.
    
    Args:
        validation_data: Parsed validation data with ranges
        task_name: Name of the task
        output_dir: Directory to save the plot
        mode: 'kinematic' or 'kinetic'
        data: Optional numpy array with shape (num_strides, 150, num_features)
        violations: DEPRECATED - Optional dict mapping variable names to lists of failed stride indices
        failing_features: NEW - Dict mapping stride indices to lists of failed variable names
        dataset_name: Optional dataset name to display
        timestamp: Optional timestamp to display
        
    Returns:
        Path to the generated plot
    """
    if task_name not in validation_data:
        raise ValueError(f"Task {task_name} not found in validation data")
    
    task_data = validation_data[task_name]
    
    # Task data validation removed (handled by unified validation system)
    
    # Extract phases dynamically from the validation data
    phases = sorted([int(p) for p in task_data.keys() if str(p).isdigit()])
    
    # Add 100% for cyclical completion if not present
    if 100 not in phases and 0 in task_data:
        phases.append(100)
        task_data[100] = task_data[0].copy()
    
    task_type = get_task_classification(task_name)
    
    # Define variables based on mode
    if mode == 'kinematic':
        variables = [
            'hip_flexion_angle_ipsi_rad', 'hip_flexion_angle_contra_rad',
            'knee_flexion_angle_ipsi_rad', 'knee_flexion_angle_contra_rad',
            'ankle_dorsiflexion_angle_ipsi_rad', 'ankle_dorsiflexion_angle_contra_rad'
        ]
        variable_labels = [
            'Hip Flexion Angle (Ipsi)', 'Hip Flexion Angle (Contra)',
            'Knee Flexion Angle (Ipsi)', 'Knee Flexion Angle (Contra)',
            'Ankle Dorsiflexion Angle (Ipsi)', 'Ankle Dorsiflexion Angle (Contra)'
        ]
        units = 'rad'
        value_conversion = np.degrees
        unit_suffix = '°'
    elif mode == 'kinetic':
        variables = [
            'hip_flexion_moment_ipsi_Nm', 'hip_flexion_moment_contra_Nm',
            'knee_flexion_moment_ipsi_Nm', 'knee_flexion_moment_contra_Nm',
            'ankle_dorsiflexion_moment_ipsi_Nm', 'ankle_dorsiflexion_moment_contra_Nm'
        ]
        variable_labels = [
            'Hip Flexion Moment (Ipsi)', 'Hip Flexion Moment (Contra)',
            'Knee Flexion Moment (Ipsi)', 'Knee Flexion Moment (Contra)',
            'Ankle Dorsiflexion Moment (Ipsi)', 'Ankle Dorsiflexion Moment (Contra)'
        ]
        units = 'Nm'
        value_conversion = lambda x: x
        unit_suffix = ''
    elif mode == 'segment':  # Link/segment angles
        variables = [
            'pelvis_sagittal_angle_rad', 'pelvis_frontal_angle_rad', 'pelvis_transverse_angle_rad',
            'trunk_sagittal_angle_rad', 'trunk_frontal_angle_rad', 'trunk_transverse_angle_rad',
            'thigh_sagittal_angle_ipsi_rad', 'thigh_sagittal_angle_contra_rad',
            'shank_sagittal_angle_ipsi_rad', 'shank_sagittal_angle_contra_rad',
            'foot_angle_ipsi_rad', 'foot_angle_contra_rad'
        ]
        variable_labels = [
            'Pelvis Sagittal Angle', 'Pelvis Frontal Angle', 'Pelvis Transverse Angle',
            'Trunk Sagittal Angle', 'Trunk Frontal Angle', 'Trunk Transverse Angle',
            'Thigh Sagittal Angle (Ipsi)', 'Thigh Sagittal Angle (Contra)',
            'Shank Sagittal Angle (Ipsi)', 'Shank Sagittal Angle (Contra)',
            'Foot Angle (Ipsi)', 'Foot Angle (Contra)'
        ]
        units = 'rad'
        value_conversion = np.degrees
        unit_suffix = '°'
    else:
        raise ValueError(f"Unknown mode: {mode}")
    
    # Create figure with appropriate layout based on number of variables - memory-aware
    n_vars = len(variables)
    if mode == 'segment':
        # For segment angles, use 12x2 layout (12 variables x pass/fail)
        figsize, dpi, linewidth = _get_memory_aware_plot_params(12, base_width=14.0, base_height_per_feature=2.0)
        fig, axes = plt.subplots(12, 2, figsize=figsize, dpi=dpi)
    else:
        # For kinematic/kinetic, use 6x2 layout (6 variables x pass/fail)
        figsize, dpi, linewidth = _get_memory_aware_plot_params(6, base_width=14.0, base_height_per_feature=3.33)
        fig, axes = plt.subplots(6, 2, figsize=figsize, dpi=dpi)
    
    # Build title
    if mode == 'kinematic':
        mode_label = "Kinematic"
    elif mode == 'kinetic':
        mode_label = "Kinetic"
    elif mode == 'segment':
        mode_label = "Segment Angles"
    else:
        mode_label = mode.capitalize()
    task_type_label = "Gait-Based Task" if task_type == 'gait' else "Bilateral Symmetric Task"
    
    title = f'{task_name.replace("_", " ").title()} - {mode_label} Validation\n{task_type_label}'
    if dataset_name:
        title += f'\nDataset: {dataset_name}'
    if timestamp:
        title += f' | Generated: {timestamp}'
    
    fig.suptitle(title, fontsize=14, fontweight='bold')
    
    # Handle both old and new formats
    if failing_features is None and violations is not None:
        # Convert old format to new format for backward compatibility
        failing_features = {}
        for var_name, stride_list in violations.items():
            for stride_idx in stride_list:
                if stride_idx not in failing_features:
                    failing_features[stride_idx] = []
                if var_name not in failing_features[stride_idx]:
                    failing_features[stride_idx].append(var_name)
    elif failing_features is None:
        failing_features = {}
    
    # Build global set of failed stride indices for ANY variable being plotted
    # A stride is only "clean" if it passes validation for ALL variables
    global_failed_strides = set()
    for stride_idx, failed_vars in failing_features.items():
        # Check if this stride failed validation for any of the variables being plotted
        for var_name in variables:
            if var_name in failed_vars:
                global_failed_strides.add(stride_idx)
                break  # Once we know this stride failed, no need to check other variables
    
    # Process each variable
    for var_idx, (var_name, var_label) in enumerate(zip(variables, variable_labels)):
        # Build variable-specific failed strides (for red plot)
        variable_failed_strides = set()
        for stride_idx, failed_vars in failing_features.items():
            if var_name in failed_vars:
                variable_failed_strides.add(stride_idx)
        
        # Get validation ranges for this variable
        var_ranges = {}
        for phase in phases:
            if phase in task_data and var_name in task_data[phase]:
                var_ranges[phase] = task_data[phase][var_name]
        
        # Determine y-axis range from both validation ranges and actual data
        all_mins = []
        all_maxs = []
        
        # Include validation ranges
        for phase, ranges in var_ranges.items():
            if 'min' in ranges and 'max' in ranges:
                min_val = ranges['min']
                max_val = ranges['max']
                # Skip None values (missing data placeholders)
                if min_val is None or max_val is None:
                    continue
                # Check for inf/nan after None check
                if not (np.isinf(min_val) or np.isinf(max_val) or np.isnan(min_val) or np.isnan(max_val)):
                    all_mins.append(min_val)
                    all_maxs.append(max_val)
        
        # Include actual data range if available
        if data is not None and data.size > 0 and var_idx < data.shape[2]:
            data_values = data[:, :, var_idx]
            # Check if data slice is not all NaN before computing min/max
            if not np.isnan(data_values).all():
                data_min = np.nanmin(data_values)
                data_max = np.nanmax(data_values)
                if not (np.isinf(data_min) or np.isinf(data_max) or np.isnan(data_min) or np.isnan(data_max)):
                    all_mins.append(data_min)
                    all_maxs.append(data_max)
        
        if all_mins and all_maxs:
            y_min = min(all_mins) - 0.1 * (max(all_maxs) - min(all_mins))
            y_max = max(all_maxs) + 0.1 * (max(all_maxs) - min(all_mins))
        else:
            y_min, y_max = -1, 1  # Default range if no valid ranges found
        
        # Plot PASSED strides (left column)
        ax_pass = axes[var_idx, 0]
        passed_count = 0
        
        # Plot data FIRST (behind validation ranges)
        if data is not None and data.size > 0 and var_idx < data.shape[2]:
            phase_ipsi = np.linspace(0, 100, 150)
            
            # Collect all passing strides
            passing_strides = []
            for stride_idx in range(data.shape[0]):
                if stride_idx not in global_failed_strides:
                    passing_strides.append(data[stride_idx, :, var_idx])
                    passed_count += 1
            
            # Plot all passing strides at once using LineCollection
            if passing_strides:
                passing_array = np.array(passing_strides)
                lc = _create_line_collection(phase_ipsi, passing_array, 'green', 0.3, linewidth, rasterized=True)
                ax_pass.add_collection(lc)
        
        # Plot validation ranges on TOP of data (higher z-order)
        _plot_validation_ranges(ax_pass, var_ranges, phases, 'lightgreen', value_conversion, unit_suffix)
        
        # Add message if no data available
        if data is None or data.size == 0:
            ax_pass.text(50, (y_min + y_max) / 2, 'Data Not Available', 
                        ha='center', va='center', fontsize=12, color='gray', alpha=0.7)
        
        ax_pass.set_title(f'{var_label} - ✓ Passed ({passed_count} strides)', fontsize=10, fontweight='bold')
        ax_pass.set_xlim(-5, 105)
        ax_pass.set_ylim(y_min, y_max)
        ax_pass.set_xticks([0, 25, 50, 75, 100])
        ax_pass.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
        ax_pass.set_ylabel(f'{units}', fontsize=9)
        ax_pass.grid(True, alpha=0.3)
        
        # Only add x-label to bottom row
        last_row_idx = 11 if mode == 'segment' else 5  # 12th variable is at index 11
        if var_idx == last_row_idx:
            x_label = 'Gait Phase' if task_type == 'gait' else 'Movement Phase'
            ax_pass.set_xlabel(x_label, fontsize=10)
        
        # Plot FAILED strides (right column)
        ax_fail = axes[var_idx, 1]
        failed_count = 0
        
        # Plot data FIRST (behind validation ranges)
        if data is not None and data.size > 0 and var_idx < data.shape[2]:
            # Collect all failed strides
            failed_strides = []
            for stride_idx in range(data.shape[0]):
                if stride_idx in variable_failed_strides:
                    failed_strides.append(data[stride_idx, :, var_idx])
                    failed_count += 1
            
            # Plot all failed strides at once using LineCollection
            if failed_strides:
                failed_array = np.array(failed_strides)
                lc = _create_line_collection(phase_ipsi, failed_array, 'red', 0.4, linewidth, rasterized=True)
                ax_fail.add_collection(lc)
        
        # Plot validation ranges on TOP of data (higher z-order)
        _plot_validation_ranges(ax_fail, var_ranges, phases, 'lightcoral', value_conversion, unit_suffix)
        
        # Add message if no data available
        if data is None or data.size == 0:
            ax_fail.text(50, (y_min + y_max) / 2, 'Data Not Available', 
                        ha='center', va='center', fontsize=12, color='gray', alpha=0.7)
        
        ax_fail.set_title(f'{var_label} - ✗ Failed ({failed_count} strides)', fontsize=10, fontweight='bold')
        ax_fail.set_xlim(-5, 105)
        ax_fail.set_ylim(y_min, y_max)
        ax_fail.set_xticks([0, 25, 50, 75, 100])
        ax_fail.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
        ax_fail.grid(True, alpha=0.3)
        
        # Only add x-label to bottom row
        if var_idx == last_row_idx:
            ax_fail.set_xlabel(x_label, fontsize=10)
        
        # Add degree conversion on right y-axis for kinematic and segment plots
        if mode in ['kinematic', 'segment']:
            ax2_pass = ax_pass.twinx()
            ax2_pass.set_ylim(value_conversion(y_min), value_conversion(y_max))
            ax2_pass.set_ylabel('degrees', fontsize=9)
            
            ax2_fail = ax_fail.twinx()
            ax2_fail.set_ylim(value_conversion(y_min), value_conversion(y_max))
            ax2_fail.set_ylabel('degrees', fontsize=9)
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.96])
    
    # Save the plot
    if dataset_name:
        output_path = Path(output_dir) / f"{dataset_name}_{task_name}_{mode}_filters_by_phase_with_data.png"
    else:
        output_path = Path(output_dir) / f"{task_name}_{mode}_filters_by_phase_with_data.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return str(output_path)


def _plot_validation_ranges(ax, var_ranges, phases, color, value_conversion, unit_suffix):
    """Helper function to plot validation range boxes."""
    box_width = 8
    
    # Collect min/max values for each phase (excluding 100% which duplicates 0%)
    phase_mins = []
    phase_maxs = []
    valid_phases = []
    
    for phase in phases:
        if phase not in var_ranges or phase == 100:  # Skip 100% as it duplicates 0%
            continue
            
        ranges = var_ranges[phase]
        if 'min' not in ranges or 'max' not in ranges:
            continue
            
        min_val = ranges['min']
        max_val = ranges['max']
        
        # Skip None values (missing data placeholders)
        if min_val is None or max_val is None:
            continue
        
        if np.isinf(min_val) or np.isinf(max_val) or np.isnan(min_val) or np.isnan(max_val):
            continue
        
        phase_mins.append(min_val)
        phase_maxs.append(max_val)
        valid_phases.append(phase)
        
        # Create rectangle for this phase range with higher z-order
        height = max_val - min_val
        rect = patches.Rectangle(
            (phase - box_width/2, min_val), box_width, height,
            linewidth=1.5, edgecolor='black', 
            facecolor=color, alpha=0.4, zorder=10
        )
        ax.add_patch(rect)
        
        # Add value labels with higher z-order
        if unit_suffix:  # Kinematic - convert to degrees
            min_label = f'{value_conversion(min_val):.0f}{unit_suffix}'
            max_label = f'{value_conversion(max_val):.0f}{unit_suffix}'
        else:  # Kinetic
            min_label = f'{min_val:.1f}'
            max_label = f'{max_val:.1f}'
        
        ax.text(phase, min_val - 0.02, min_label, 
               ha='center', va='top', fontsize=7, fontweight='bold', zorder=11)
        ax.text(phase, max_val + 0.02, max_label, 
               ha='center', va='bottom', fontsize=7, fontweight='bold', zorder=11)
    
    # NO connecting lines between boxes - removed the line plotting code