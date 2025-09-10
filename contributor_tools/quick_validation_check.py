#!/usr/bin/env python3
"""
Quick Validation Check - Fast Validation with Optional Plotting

A fast validation tool that shows pass/fail statistics with optional plot generation.
Useful for rapid validation checks during dataset conversion and debugging.

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
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, List, Set, Optional
from datetime import datetime
import pandas as pd
import threading
import time

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from internal.validation_engine.validator import Validator
from user_libs.python.locomotion_data import LocomotionData

# Import Tkinter components for scrollable display
try:
    import tkinter as tk
    from tkinter import ttk
    import matplotlib
    matplotlib.use('TkAgg')  # Ensure TkAgg backend for embedding
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False


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
    if not TKINTER_AVAILABLE:
        # Fallback to standard matplotlib display if Tkinter is not available
        import matplotlib.pyplot as plt
        plt.show()
        return
    
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



def print_validation_summary(result: Dict) -> None:
    """
    Print a concise validation summary.
    
    Args:
        result: Validation result dictionary from Validator
    """
    stats = result['stats']
    
    # Header
    print("\n" + "="*70)
    print("QUICK VALIDATION CHECK")
    print("="*70)
    
    # Overall status
    status = "✅ PASSED" if result['passed'] else "❌ FAILED"
    print(f"\nDataset: {stats['dataset']}")
    print(f"Status: {status}")
    print(f"Overall Pass Rate: {stats['pass_rate']:.1%} ({stats['total_strides'] - stats['total_failing_strides']}/{stats['total_strides']} strides)")
    
    # Phase structure
    phase_icon = "✅" if result['phase_valid'] else "❌"
    print(f"Phase Structure: {phase_icon} {result['phase_message']}")
    
    # Task summary
    print(f"\nTasks Validated: {stats['num_tasks']}")
    
    if result['violations']:
        print("\n" + "-"*70)
        print("TASK SUMMARY")
        print("-"*70)
        
        for task, violations in sorted(result['violations'].items()):
            # Count total failures for this task
            total_failures = sum(len(v) for v in violations.values())
            
            if total_failures > 0:
                # Count unique features that failed
                failed_features = len(violations)
                print(f"\n📍 {task}: {total_failures} stride failures across {failed_features} features")
            else:
                print(f"\n📍 {task}: ✅ All features passed")
    else:
        print("\n✅ All validations passed!")
    
    # Summary statistics
    print("\n" + "-"*70)
    print("SUMMARY")
    print("-"*70)
    print(f"Total Strides: {stats['total_strides']:,}")
    print(f"Pass Rate: {stats['pass_rate']:.1%}")
    print(f"Variable Pass Rate: {stats['variable_pass_rate']:.1%}")
    
    print("\n" + "="*70)




def main():
    """Main entry point for quick validation check."""
    parser = argparse.ArgumentParser(
        description="Quick validation check - text-only, no plots",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "dataset",
        help="Path to phase-indexed dataset parquet file"
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
        # Initialize validator
        validator = Validator(config_path=ranges_file)
        
        # Run validation
        result = validator.validate(str(dataset_path))
        
        # Always print summary
        print_validation_summary(result)
        
        # Optional plot generation
        if args.plot:
            # Check for conflicting options
            if args.task and not args.plot:
                print("\n⚠️  Warning: --task requires --plot to be specified")
            
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
        return 0 if result['passed'] else 1
        
    except Exception as e:
        print(f"\n❌ Error during validation: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())