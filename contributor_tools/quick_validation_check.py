#!/usr/bin/env python3
"""
Quick Validation Check - Fast Validation with Optional Plotting

A fast validation tool that shows pass/fail statistics with optional plot generation.
Useful for rapid validation checks during dataset conversion and debugging.

Schema compliance drives the command's exit code; quality gates and pass rates are informational so you can decide what to tighten before documentation.

Usage:
    # Text-only validation (default)
    python quick_validation_check.py converted_datasets/gtech_2021_phase.parquet
    
    # With custom ranges
    python quick_validation_check.py dataset.parquet --ranges custom_ranges.yaml
    
    # Generate plots for all tasks (shows interactively)
    python quick_validation_check.py dataset.parquet --plot
    
    # Generate plot for specific task (shows interactively)
    python quick_validation_check.py dataset.parquet --plot --task level_walking
    
    # Save plots to directory instead of showing
    python quick_validation_check.py dataset.parquet --plot --output-dir ./my_plots

    # Compare against a previous run and save the latest summary
    python quick_validation_check.py dataset.parquet --compare prev_summary.json --save-summary latest_summary.json
"""

import sys
import argparse
import json
import math
from pathlib import Path
from typing import Dict, List, Set, Optional
from datetime import datetime, timezone
import pandas as pd
import threading
import time
import numpy as np

# Ensure repository root and src/ are importable so `import locohub` works
project_root = Path(__file__).parent.parent
src_dir = project_root / "src"
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if src_dir.exists() and str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from internal.validation_engine.validator import Validator
from internal.config_management import task_registry
from locohub import LocomotionData

# Detect if we're in a headless environment (no display available)
import os
DISPLAY_AVAILABLE = bool(os.environ.get('DISPLAY')) or os.name == 'nt'  # Windows always has display

# Tkinter availability checked lazily when needed for interactive display
TKINTER_AVAILABLE = False
_tkinter_checked = False

def _check_tkinter_available():
    """Lazily check if Tkinter is available for interactive display."""
    global TKINTER_AVAILABLE, _tkinter_checked
    if _tkinter_checked:
        return TKINTER_AVAILABLE
    _tkinter_checked = True
    if not DISPLAY_AVAILABLE:
        TKINTER_AVAILABLE = False
        return False
    try:
        import tkinter as tk
        from tkinter import ttk
        import matplotlib
        matplotlib.use('TkAgg')  # Only set TkAgg when we know we need interactive display
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        TKINTER_AVAILABLE = True
    except (ImportError, Exception):
        TKINTER_AVAILABLE = False
    return TKINTER_AVAILABLE


def _setup_headless_backend():
    """Setup matplotlib for headless (file-saving) mode."""
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend for saving files


def animated_loading(stop_event):
    """
    Display animated loading text while plots are being embedded.
    
    Args:
        stop_event: Threading event to signal when to stop the animation
    """
    states = [
        "⏳ Loading plots   ",
        "⏳ Loading plots .  ",
        "⏳ Loading plots .. ",
        "⏳ Loading plots ..."
    ]
    i = 0
    while not stop_event.is_set():
        print(f"\r{states[i]}", end='', flush=True)
        i = (i + 1) % len(states)
        time.sleep(0.3)
    # Clear the loading line
    print("\r" + " " * 25 + "\r", end='', flush=True)


def show_scrollable_plot():
    """
    Display matplotlib plots in a scrollable Tkinter window.
    This is needed for large plots that exceed screen height.
    """
    if not _check_tkinter_available():
        # Fallback to standard matplotlib display if Tkinter is not available
        import matplotlib.pyplot as plt
        plt.show()
        return

    # Import Tkinter components (available since _check_tkinter_available passed)
    import tkinter as tk
    from tkinter import ttk
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.pyplot as plt

    # Get all current figures
    figures = [plt.figure(num) for num in plt.get_fignums()]
    if not figures:
        return

    # Start loading animation before the slow embedding process
    print("")  # New line before animation
    stop_loading = threading.Event()
    loading_thread = threading.Thread(target=animated_loading, args=(stop_loading,))
    loading_thread.daemon = True
    loading_thread.start()

    # Create Tkinter window
    root = tk.Tk()
    root.title("Validation Plots - Quick Check")
    
    # Define close handler
    def on_closing():
        """Properly close the window and terminate the program."""
        try:
            root.quit()  # Quit the mainloop
            root.destroy()  # Destroy the window
        except:
            pass  # Ignore any errors during cleanup
    
    # Bind the close event
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Get screen dimensions
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # Set window size based on plot dimensions
    # Plots are typically 14 inches wide at 80-100 DPI = ~1120-1400 pixels
    # Add some padding for scrollbars and window chrome
    window_width = min(1450, int(screen_width * 0.8))  # Cap at 1450px or 80% of screen
    window_height = int(screen_height * 0.9)  # Keep height at 90% for scrolling
    
    # Center the window
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    # Create notebook for multiple figures if needed
    if len(figures) > 1:
        notebook = ttk.Notebook(root)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        for i, fig in enumerate(figures):
            # Create frame for this figure
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=f"Task {i+1}")
            
            # Create scrollable canvas for the figure
            create_scrollable_figure(frame, fig)
    else:
        # Single figure - create scrollable canvas directly
        create_scrollable_figure(root, figures[0])
    
    # Stop the loading animation after embedding is complete
    stop_loading.set()
    loading_thread.join(timeout=0.5)  # Wait for animation to finish
    print("✅ Plots loaded successfully!")
    
    try:
        # Start the Tkinter event loop
        root.mainloop()
    except:
        pass  # Ignore any errors during mainloop
    finally:
        # Ensure cleanup happens
        try:
            root.destroy()
        except:
            pass
        # Close all figures after window is closed
        plt.close('all')


def create_scrollable_figure(parent, fig):
    """
    Create a scrollable canvas with the matplotlib figure embedded.
    
    Args:
        parent: The parent Tkinter widget
        fig: The matplotlib figure to embed
    """
    # Create frame to hold canvas and scrollbars
    frame = ttk.Frame(parent)
    frame.pack(fill=tk.BOTH, expand=True)
    
    # Create canvas for the plot
    canvas_frame = tk.Canvas(frame, highlightthickness=0)
    canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    # Create scrollbars
    v_scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=canvas_frame.yview)
    v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    h_scrollbar = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=canvas_frame.xview)
    h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
    
    # Configure canvas scrolling
    canvas_frame.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
    
    # Create frame inside canvas to hold the matplotlib figure
    plot_frame = ttk.Frame(canvas_frame)
    
    # Embed the matplotlib figure
    figure_canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    figure_canvas.draw()
    figure_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    # Add the plot frame to the canvas
    canvas_frame.create_window((0, 0), window=plot_frame, anchor='nw')
    
    # Update scroll region after the frame is drawn
    def configure_scroll_region(event=None):
        canvas_frame.configure(scrollregion=canvas_frame.bbox('all'))
    
    plot_frame.bind('<Configure>', configure_scroll_region)
    
    # Initial configuration
    canvas_frame.after(100, configure_scroll_region)


def generate_plots(dataset_path: str, validator: Validator, task_filter: Optional[str] = None,
                  output_dir: Optional[str] = None, use_column_names: bool = False,
                  show_local_passing: bool = False) -> None:
    """
    Generate validation plots using the same plotting functions as report generator.

    Args:
        dataset_path: Path to dataset
        validator: Initialized validator
        task_filter: Optional single task to plot (if None, plot all)
        output_dir: Where to save plots (if None, show interactively)
        use_column_names: If True, use actual column names instead of pretty labels
        show_local_passing: If True, show locally passing strides in yellow
    """
    # Setup matplotlib backend BEFORE importing pyplot
    # Use Agg (non-interactive) for file saving, TkAgg for interactive display
    if output_dir:
        _setup_headless_backend()
    else:
        # For interactive display, check if Tkinter is available
        if not _check_tkinter_available():
            print("  ⚠️  No display available. Use --output-dir to save plots to files.")
            return

    from internal.plot_generation.filters_by_phase_plots import create_task_combined_plot
    import matplotlib.pyplot as plt

    locomotion_data = LocomotionData(dataset_path, phase_col='phase_ipsi')
    dataset_name = Path(dataset_path).stem
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    
    # Determine which tasks to plot
    all_tasks = locomotion_data.get_tasks()
    if task_filter:
        if task_filter not in all_tasks:
            print(f"❌ Task '{task_filter}' not found in dataset")
            print(f"Available tasks: {', '.join(sorted(all_tasks))}")
            return
        tasks = [task_filter]
    else:
        tasks = all_tasks
    
    # Set output directory only if explicitly specified
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)
        print(f"\n📁 Output directory: {output_dir}")
        show = False  # If output_dir is specified, save files instead of showing
    else:
        show = True  # Default to showing plots if no output_dir specified
    
    # Generate plots for each task
    print(f"\n🎨 Generating plots for {len(tasks)} task(s)...")
    
    for task in sorted(tasks):
        print(f"\n📍 Processing {task}...")
        
        try:
            # Get validation failures for this task
            failures = validator._validate_task_with_failing_features(locomotion_data, task)
            
            # Get task data
            data_3d, features = locomotion_data.get_cycles(subject=None, task=task)
            
            if data_3d.size == 0:
                print(f"  ⚠️  No data available for {task}")
                continue
            
            # Get validation config for this task
            task_config = validator.config_manager.get_task_data(task)
            
            # Generate plot using the same function as report generator
            plot_path = create_task_combined_plot(
                validation_data=task_config,
                task_name=task,
                output_dir=str(output_dir) if output_dir else None,
                data_3d=data_3d,
                feature_names=features,
                failing_features=failures,
                dataset_name=dataset_name,
                timestamp=timestamp,
                show_interactive=show,
                use_column_names=use_column_names,
                show_local_passing=show_local_passing
            )
            
            if plot_path and not show:
                print(f"  ✅ Plot saved: {Path(plot_path).name}")
            elif show:
                print(f"  ✅ Plot displayed")
                
        except Exception as e:
            print(f"  ❌ Error generating plot for {task}: {e}")
            continue
    
    if show:
        # Use scrollable display for better handling of large plots
        show_scrollable_plot()
    elif output_dir:
        print(f"\n✅ All plots saved to: {output_dir}")



def print_validation_summary(result: Dict, task_details: Optional[Dict[str, Dict[str, object]]] = None) -> None:
    """
    Print a concise validation summary.

    Args:
        result: Validation result dictionary from Validator
        task_details: Optional per-task statistics for additional reporting
    """
    stats = result['stats']
    mode = result.get('mode', 'phase')

    print("\n" + "="*70)
    print("QUICK VALIDATION CHECK")
    print("="*70)

    schema_passed = result.get('schema_passed', result['passed'])
    schema_icon = "✅" if schema_passed else "❌"
    schema_text = "Schema compliant" if schema_passed else "Schema issues detected"

    print(f"\nDataset: {stats['dataset']}")
    print(f"Schema Status: {schema_icon} {schema_text}")
    print(f"Mode: {'Time-Indexed' if mode == 'time' else 'Phase-Indexed'}")

    if mode == 'phase':
        total_strides = stats['total_strides']
        passing_strides = total_strides - stats['total_failing_strides']
        print(f"Overall Pass Rate: {stats['pass_rate']:.1%} ({passing_strides}/{total_strides} strides)")
    else:
        print(f"Overall Pass Rate: {stats['pass_rate']:.1%} (structural checks)")

    quality_gate = result.get('quality_gate_passed')
    threshold = result.get('quality_gate_threshold')
    if quality_gate is not None:
        icon = "✅" if quality_gate else "⚠️"
        if isinstance(threshold, (int, float)) and threshold:
            threshold_pct = f"{threshold * 100:.0f}%"
        else:
            threshold_pct = "n/a"
        print(f"Quality Gate ({threshold_pct} threshold): {icon}")

    phase_icon = "✅" if result['phase_valid'] else "❌"
    print(f"Phase Structure: {phase_icon} {result['phase_message']}")

    print(f"\nTasks Evaluated: {stats.get('num_tasks', 0)}")

    task_details_available = task_details is not None
    task_summary_needed = bool(result.get('violations')) or (task_details_available and mode == 'phase')
    if task_summary_needed:
        print("\n" + "-"*70)
        print("TASK SUMMARY")
        print("-"*70)

        if mode == 'phase' and task_details_available:
            for task in sorted(task_details.keys()):
                details = task_details[task]
                total = details.get('total_strides', 0) or 0
                failing = details.get('failing_strides', 0) or 0
                passing = total - failing if total else 0

                if total:
                    pass_pct = details.get('pass_rate', 1.0) * 100
                    print(f"\n📍 {task}: {pass_pct:.1f}% pass ({passing}/{total} strides)")
                else:
                    print(f"\n📍 {task}: ⚠️ No strides found")

                feature_failures = details.get('feature_failures', [])
                if feature_failures:
                    print("    Failing features:")
                    for feature_info in feature_failures:
                        feature = feature_info['feature']
                        failed_count = feature_info['failed_strides']
                        failed_pct = feature_info['failed_percentage'] * 100
                        print(f"      - {feature}: {failed_count} strides ({failed_pct:.1f}%)")
                        phase_breakdown = feature_info.get('phase_breakdown', [])
                        for phase_info in phase_breakdown:
                            total_phase_failures = phase_info['below'] + phase_info['above']
                            if total_phase_failures == 0:
                                continue
                            parts = []
                            if phase_info['below']:
                                parts.append(f"{phase_info['below']} below")
                            if phase_info['above']:
                                parts.append(f"{phase_info['above']} above")
                            phase_desc = ', '.join(parts) if parts else 'out of range'
                            print(f"        • phase {phase_info['phase']}%: {total_phase_failures} strides ({phase_desc})")
                else:
                    print("    ✅ All features within range")
        else:
            for task, violations in sorted(result.get('violations', {}).items()):
                total_failures = sum(len(v) for v in violations.values())
                if total_failures > 0:
                    failed_features = len(violations)
                    summary_label = "issues" if mode == 'time' else "stride failures"
                    print(f"\n📍 {task}: {total_failures} {summary_label} across {failed_features} checks")
                    if mode == 'time':
                        for check_name, records in violations.items():
                            print(f"    - {check_name}: {len(records)} flagged segments")
                else:
                    print(f"\n📍 {task}: ✅ All checks passed")
    else:
        print("\n✅ All validations passed!")

    print("\n" + "-"*70)
    print("SUMMARY")
    print("-"*70)
    if mode == 'phase':
        print(f"Total Strides: {stats['total_strides']:,}")
        print(f"Pass Rate: {stats['pass_rate']:.1%}")
        print(f"Variable Pass Rate: {stats['variable_pass_rate']:.1%}")
    else:
        print(f"Total Checks: {stats['total_checks']:,}")
        print(f"Violations: {stats['total_violations']:,}")
        print(f"Episodes: {stats.get('num_episodes', 0)}")

    print("\n" + "="*70)


def _safe_float(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    try:
        candidate = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(candidate) or math.isinf(candidate):
        return None
    return candidate


def _safe_int(value: Optional[float]) -> Optional[int]:
    if value is None:
        return None
    try:
        candidate = int(value)
    except (TypeError, ValueError):
        try:
            candidate = int(float(value))
        except (TypeError, ValueError):
            return None
    return candidate


def _format_percent(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def _build_summary_payload(
    result: Dict,
    task_details: Optional[Dict[str, Dict[str, object]]],
    dataset_path: Path,
    ranges_file: Path,
) -> Dict:
    """Create a JSON-serializable snapshot of validation results."""

    stats = result.get('stats', {})
    mode = result.get('mode', 'phase')

    timestamp = datetime.now(timezone.utc).replace(microsecond=0)

    payload: Dict[str, object] = {
        'generated_at': timestamp.isoformat().replace('+00:00', 'Z'),
        'dataset': str(dataset_path),
        'ranges': str(ranges_file),
        'mode': mode,
        'passed': bool(result.get('passed')),
        'schema_passed': bool(result.get('schema_passed', result.get('passed'))),
        'quality_gate_passed': result.get('quality_gate_passed'),
        'quality_gate_threshold': result.get('quality_gate_threshold'),
        'phase_valid': result.get('phase_valid'),
        'phase_message': result.get('phase_message'),
        'stats': {
            'pass_rate': _safe_float(stats.get('pass_rate')),
            'total_strides': _safe_int(stats.get('total_strides')),
            'total_failing_strides': _safe_int(stats.get('total_failing_strides')),
            'num_tasks': _safe_int(stats.get('num_tasks')),
            'total_checks': _safe_int(stats.get('total_checks')),
            'total_violations': _safe_int(stats.get('total_violations')),
        },
        'tasks': {}
    }

    task_snapshot: Dict[str, Dict[str, object]] = {}
    if task_details:
        for task, details in task_details.items():
            total_strides = _safe_int(details.get('total_strides'))
            failing_strides = _safe_int(details.get('failing_strides'))
            pass_rate = _safe_float(details.get('pass_rate'))

            failing_features: Dict[str, int] = {}
            for feature_info in details.get('feature_failures', []):
                feature_name = feature_info.get('feature')
                failed_count = _safe_int(feature_info.get('failed_strides'))
                if feature_name and failed_count:
                    failing_features[feature_name] = failed_count

            task_snapshot[task] = {
                'total_strides': total_strides,
                'failing_strides': failing_strides,
                'pass_rate': pass_rate,
                'failing_features': failing_features,
            }

    payload['tasks'] = task_snapshot
    return payload


def _write_summary(path: str, payload: Dict) -> None:
    summary_path = Path(path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open('w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write('\n')
    print(f"📝 Summary saved to {summary_path}")


def _load_summary(path: str) -> Optional[Dict]:
    summary_path = Path(path)
    if not summary_path.exists():
        print(f"\n⚠️  Previous summary not found: {summary_path}")
        return None
    try:
        with summary_path.open('r', encoding='utf-8') as handle:
            return json.load(handle)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"\n⚠️  Could not read summary {summary_path}: {exc}")
        return None


PASS_RATE_DELTA_THRESHOLD = 0.005  # 0.5 percentage points


def _compare_summaries(current: Dict, previous: Dict) -> List[str]:
    """Return human-readable notes describing differences between two summaries."""

    notes: List[str] = []

    if current.get('dataset') != previous.get('dataset'):
        notes.append(
            f"ℹ️  Comparing different datasets: now {current.get('dataset')} vs {previous.get('dataset')}"
        )

    current_stats = current.get('stats', {}) or {}
    previous_stats = previous.get('stats', {}) or {}

    current_pass = _safe_float(current_stats.get('pass_rate'))
    previous_pass = _safe_float(previous_stats.get('pass_rate'))
    if current_pass is not None and previous_pass is not None:
        delta = current_pass - previous_pass
        if abs(delta) >= PASS_RATE_DELTA_THRESHOLD:
            arrow = '⬆️' if delta > 0 else '⬇️'
            notes.append(
                f"{arrow} Overall pass rate changed from {_format_percent(previous_pass)} to {_format_percent(current_pass)} ({delta:+.1%})."
            )

    if previous.get('passed') and not current.get('passed'):
        notes.append("⚠️  Overall status regressed: previously passing, now failing.")
    elif current.get('passed') and not previous.get('passed'):
        notes.append("✅ Overall status improved: previously failing, now passing.")

    current_quality = current.get('quality_gate_passed')
    previous_quality = previous.get('quality_gate_passed')
    if current_quality is not None and previous_quality is not None and current_quality != previous_quality:
        if current_quality:
            notes.append("✅ Quality gate now satisfied (previously unmet).")
        else:
            notes.append("⚠️  Quality gate no longer satisfied (previously met).")

    current_tasks = current.get('tasks') or {}
    previous_tasks = previous.get('tasks') or {}
    all_tasks = sorted(set(current_tasks) | set(previous_tasks))

    for task in all_tasks:
        current_task = current_tasks.get(task)
        previous_task = previous_tasks.get(task)

        current_failing = _safe_int((current_task or {}).get('failing_strides')) or 0
        previous_failing = _safe_int((previous_task or {}).get('failing_strides')) or 0
        current_pass_rate = _safe_float((current_task or {}).get('pass_rate'))
        previous_pass_rate = _safe_float((previous_task or {}).get('pass_rate'))

        if current_task and not previous_task:
            if current_failing:
                notes.append(
                    f"⚠️  New task {task} introduced with {current_failing} failing strides ({_format_percent(current_pass_rate)} pass rate)."
                )
            else:
                total = _safe_int(current_task.get('total_strides'))
                notes.append(
                    f"✅ New task {task} added; all {total or 0} strides pass."
                )
            continue

        if previous_task and not current_task:
            notes.append(f"ℹ️  Task {task} no longer present in the dataset.")
            continue

        # Both present
        if current_failing and not previous_failing:
            notes.append(
                f"⚠️  Task {task} now has {current_failing} failing strides ({_format_percent(current_pass_rate)} pass rate)."
            )
        elif previous_failing and not current_failing:
            notes.append(
                f"✅ Task {task} now passes all strides (previously {previous_failing} failures)."
            )
        elif current_failing and previous_failing:
            if current_pass_rate is not None and previous_pass_rate is not None:
                delta = current_pass_rate - previous_pass_rate
                if delta >= PASS_RATE_DELTA_THRESHOLD:
                    notes.append(
                        f"⬆️  Task {task} pass rate improved from {_format_percent(previous_pass_rate)} to {_format_percent(current_pass_rate)}."
                    )
                elif delta <= -PASS_RATE_DELTA_THRESHOLD:
                    notes.append(
                        f"⬇️  Task {task} pass rate dropped from {_format_percent(previous_pass_rate)} to {_format_percent(current_pass_rate)}."
                    )

        current_features = (current_task or {}).get('failing_features') or {}
        previous_features = (previous_task or {}).get('failing_features') or {}

        new_features = sorted(set(current_features) - set(previous_features))
        resolved_features = sorted(set(previous_features) - set(current_features))

        if new_features:
            notes.append(
                f"⚠️  Task {task}: new failing features detected ({', '.join(new_features)})."
            )
        if resolved_features:
            notes.append(
                f"✅ Task {task}: resolved failing features ({', '.join(resolved_features)})."
            )

    return notes


def _print_comparison(current: Dict, previous: Dict) -> None:
    notes = _compare_summaries(current, previous)
    print("\n" + "="*70)
    print("COMPARISON VS PREVIOUS RUN")
    print("="*70)
    if not notes:
        print("\nNo differences detected between the two summaries.")
    else:
        for note in notes:
            print(f"\n{note}")


POPULATION_SUFFIXES = [
    '_stroke', '_amputee', '_tfa', '_tta', '_pd', '_sci', '_cp',
    '_ms', '_oa', '_cva', '_parkinsons'
]


def _base_task_name(task: str) -> str:
    """Remove population suffixes for registry comparisons."""

    if not task:
        return ''

    task_lower = task.lower()
    for suffix in POPULATION_SUFFIXES:
        if task_lower.endswith(suffix):
            return task_lower[:-len(suffix)]
    return task_lower


def _collect_dataset_tasks(dataset_path: Path) -> List[str]:
    """Return unique task names present in the dataset parquet."""

    try:
        df = pd.read_parquet(dataset_path, columns=['task'])
    except Exception:
        df = pd.read_parquet(dataset_path)
    if 'task' not in df.columns:
        return []
    return sorted(x for x in df['task'].dropna().unique())


def _compute_task_statistics(dataset_path: Path, validator: Validator, result: Dict) -> Dict[str, Dict[str, object]]:
    """Collect per-task stride and feature statistics for reporting."""
    task_details: Dict[str, Dict[str, object]] = {}

    if result.get('mode', 'phase') != 'phase':
        return task_details

    locomotion_data = LocomotionData(dataset_path, phase_col='phase_ipsi')
    dataset_tasks = list(locomotion_data.get_tasks())
    violation_tasks = list(result.get('violations', {}).keys())
    all_tasks = sorted(set(dataset_tasks) | set(violation_tasks))

    for task in all_tasks:
        total_strides = 0
        if task in dataset_tasks:
            task_df = locomotion_data.df[locomotion_data.df['task'] == task]
            if locomotion_data.POINTS_PER_CYCLE:
                total_strides = len(task_df) // locomotion_data.POINTS_PER_CYCLE

        violations = result.get('violations', {}).get(task, {})

        failing_stride_indices: Set[int] = set()
        for indices in violations.values():
            failing_stride_indices.update(indices)

        failing_strides = len(failing_stride_indices)
        pass_rate = 1.0
        if total_strides > 0:
            pass_rate = max(0.0, 1.0 - (failing_strides / total_strides))

        # Analyse failures by phase (below / above limits)
        feature_phase_stats: Dict[str, Dict[int, Dict[str, int]]] = {}
        task_config = validator.config_manager.get_task_data(task)

        if task_config and total_strides > 0:
            config_features = sorted({
                feature_name
                for phase_data in task_config.values()
                for feature_name in phase_data.keys()
            })

            if config_features:
                data_3d, feature_names = locomotion_data.get_cycles(
                    subject=None,
                    task=task,
                    features=config_features
                )

                if data_3d is not None and data_3d.size:
                    feature_index = {name: idx for idx, name in enumerate(feature_names)}
                    points_per_cycle = locomotion_data.POINTS_PER_CYCLE or data_3d.shape[1]

                    for phase_pct, phase_variables in task_config.items():
                        phase_idx = int(round((phase_pct / 100.0) * (points_per_cycle - 1)))
                        phase_idx = max(0, min(points_per_cycle - 1, phase_idx))

                        for feature_name, limits in phase_variables.items():
                            idx = feature_index.get(feature_name)
                            if idx is None:
                                continue

                            values = data_3d[:, phase_idx, idx]
                            values = values[np.isfinite(values)]
                            if values.size == 0:
                                continue

                            min_val = limits.get('min')
                            max_val = limits.get('max')
                            if min_val is None and max_val is None:
                                continue

                            below = int(np.sum(values < min_val)) if min_val is not None else 0
                            above = int(np.sum(values > max_val)) if max_val is not None else 0

                            if below or above:
                                phase_stats = feature_phase_stats.setdefault(feature_name, {})
                                stats_entry = phase_stats.setdefault(phase_pct, {'below': 0, 'above': 0})
                                stats_entry['below'] += below
                                stats_entry['above'] += above

        feature_failures = []
        for feature, indices in violations.items():
            unique_indices = len(set(indices))
            failed_percentage = (unique_indices / total_strides) if total_strides else 0.0

            phase_breakdown = []
            for phase_pct, counts in feature_phase_stats.get(feature, {}).items():
                phase_breakdown.append({
                    'phase': phase_pct,
                    'below': counts.get('below', 0),
                    'above': counts.get('above', 0)
                })

            phase_breakdown.sort(key=lambda item: item['below'] + item['above'], reverse=True)

            feature_failures.append({
                'feature': feature,
                'failed_strides': unique_indices,
                'failed_percentage': failed_percentage,
                'phase_breakdown': phase_breakdown
            })

        feature_failures.sort(key=lambda item: item['failed_strides'], reverse=True)

        task_details[task] = {
            'total_strides': total_strides,
            'failing_strides': failing_strides,
            'pass_rate': pass_rate,
            'feature_failures': feature_failures
        }

    return task_details


def _report_task_registry_mismatches(dataset_tasks: List[str], range_tasks: List[str]) -> bool:
    """Warn about tasks missing from the canonical registry or ranges."""

    registry_ok = True

    unknown_dataset = [t for t in dataset_tasks if not task_registry.is_valid_task(_base_task_name(t))]
    unknown_ranges = [t for t in range_tasks if not task_registry.is_valid_task(_base_task_name(t))]

    if unknown_dataset:
        print("\n⚠️  Dataset includes tasks not in task_registry: " + ", ".join(sorted(unknown_dataset)))
        registry_ok = False
    if unknown_ranges:
        print("\n⚠️  Validation ranges include tasks not in task_registry: " + ", ".join(sorted(unknown_ranges)))
        registry_ok = False

    missing_ranges = [t for t in dataset_tasks if t not in range_tasks]
    if missing_ranges:
        print("\n⚠️  Dataset tasks without validation ranges: " + ", ".join(sorted(missing_ranges)))

    if registry_ok:
        print("\n✅ Task registry check passed (all tasks recognised).")
    else:
        print("\n⚠️  Update internal/config_management/task_registry.py if these tasks are expected.")

    return registry_ok




def main():
    """Main entry point for quick validation check."""
    parser = argparse.ArgumentParser(
        description="Quick validation check - schema status plus quality metrics",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "dataset",
        help="Path to standardized dataset parquet file (phase- or time-indexed)"
    )
    
    parser.add_argument(
        "--ranges",
        help="Path to validation ranges YAML file (default: default_ranges.yaml)"
    )
    
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Generate validation plots"
    )
    
    parser.add_argument(
        "--task",
        help="Generate plot for specific task only (e.g., level_walking)"
    )
    
    parser.add_argument(
        "--output-dir",
        help="Directory to save plots (if not specified, plots are shown interactively)"
    )
    
    parser.add_argument(
        "--use-column-names",
        action="store_true",
        help="Use actual column names instead of pretty labels in plots"
    )
    
    parser.add_argument(
        "--show-local-passing",
        action="store_true",
        help="Show locally passing strides in yellow (pass current feature but fail others)"
    )

    parser.add_argument(
        "--save-summary",
        help="Write validation summary JSON to the given path"
    )

    parser.add_argument(
        "--compare",
        help="Compare results to a previous summary JSON file"
    )
    
    args = parser.parse_args()
    
    # Validate input file
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"❌ Error: Dataset file not found: {dataset_path}")
        return 1
    
    # Determine validation ranges file
    if args.ranges:
        ranges_file = Path(args.ranges)
    else:
        ranges_file = Path(__file__).parent / "validation_ranges" / "default_ranges.yaml"
    
    if not ranges_file.exists():
        print(f"❌ Error: Validation ranges file not found: {ranges_file}")
        return 1
    
    print(f"🔍 Validating: {dataset_path.name}")
    print(f"📋 Using ranges: {ranges_file.name}")
    
    try:
        dataset_tasks: List[str] = []
        try:
            dataset_tasks = _collect_dataset_tasks(dataset_path)
        except Exception as exc:
            print(f"\n⚠️  Could not inspect dataset tasks: {exc}")

        # Initialize validator
        validator = Validator(config_path=ranges_file)
        range_tasks = list(validator.config_manager.get_tasks())

        registry_ok = _report_task_registry_mismatches(dataset_tasks, range_tasks)

        # Run validation
        result = validator.validate(str(dataset_path))
        mode = result.get('mode', 'phase')

        task_details = None
        if mode == 'phase':
            try:
                task_details = _compute_task_statistics(dataset_path, validator, result)
            except Exception as exc:
                print(f"\n⚠️  Could not compute per-task statistics: {exc}")

        # Always print summary
        print_validation_summary(result, task_details=task_details)

        summary_payload = _build_summary_payload(
            result=result,
            task_details=task_details,
            dataset_path=dataset_path,
            ranges_file=ranges_file,
        )

        if args.compare:
            previous_summary = _load_summary(args.compare)
            if previous_summary:
                _print_comparison(summary_payload, previous_summary)

        if args.save_summary:
            _write_summary(args.save_summary, summary_payload)

        # Optional plot generation
        if args.plot:
            if mode == 'time':
                print("\n⚠️  Plots are only available for phase-indexed datasets. Skipping plot generation.")
            else:
                generate_plots(
                    dataset_path=str(dataset_path),
                    validator=validator,
                    task_filter=args.task,
                    output_dir=args.output_dir,
                    use_column_names=args.use_column_names,
                    show_local_passing=args.show_local_passing
                )
        elif args.task or args.output_dir:
            print("\n⚠️  Note: --task and --output-dir require --plot to be specified")
        
        # Return exit code based on validation result
        return 0 if (result['passed'] and registry_ok) else 1
        
    except Exception as e:
        print(f"\n❌ Error during validation: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
