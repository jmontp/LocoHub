#!/usr/bin/env python3
"""
Interactive Validation Range Tuner

A GUI tool for interactively adjusting validation ranges by directly manipulating
boxes on the plot. Integrates with existing validation and plotting systems.

Features:
- Direct manipulation of validation range boxes
- Load/save YAML validation ranges
- Load parquet datasets for visualization
- Auto-tuning integration
- Real-time plot updates

Usage:
    python3 contributor_tools/interactive_validation_tuner.py
    
    1. Load a validation ranges YAML file (File -> Load Validation Ranges)
       Example: contributor_tools/validation_ranges/default_ranges.yaml
    
    2. Load a parquet dataset for visualization (File -> Load Dataset)
       Example: converted_datasets/umich_2021_phase.parquet
    
    3. Select task from dropdown and mode (Kinematic/Kinetic/Segment)
    
    4. Interact with validation boxes:
       - Drag top edge to adjust max value
       - Drag bottom edge to adjust min value
       - Drag middle to move entire box
    
    5. Use Auto-Tune button to automatically set ranges using statistical methods
    
    6. Save modified ranges (File -> Save Validation Ranges)

Box Interaction:
    - Red outline: Dragging top edge (max value)
    - Blue outline: Dragging bottom edge (min value)
    - Green outline: Dragging entire box (both values)
    
Requirements:
    - tkinter (GUI framework)
    - matplotlib
    - numpy, pandas, yaml
    
Installation:
    Ubuntu/Debian: sudo apt-get install python3-tk
    Windows/macOS: tkinter included with Python
"""

import sys
import numpy as np
import pandas as pd
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

# Try to import tkinter and set up matplotlib backend
TKINTER_AVAILABLE = False
DISPLAY_AVAILABLE = False

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    TKINTER_AVAILABLE = True
    
    # Test if display is available
    try:
        test_root = tk.Tk()
        test_root.destroy()
        DISPLAY_AVAILABLE = True
    except:
        DISPLAY_AVAILABLE = False
        
    if DISPLAY_AVAILABLE:
        import matplotlib
        matplotlib.use('TkAgg')  # Set backend before importing pyplot
        from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
        import matplotlib.backends.backend_tkagg as tkagg
    
except ImportError as e:
    TKINTER_AVAILABLE = False
    DISPLAY_AVAILABLE = False

# Import matplotlib components (backend-independent)
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.widgets import Button, RadioButtons, TextBox

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import existing modules
from user_libs.python.locomotion_data import LocomotionData
from user_libs.python.feature_constants import get_feature_list
from internal.config_management.config_manager import ValidationConfigManager
from internal.plot_generation.filters_by_phase_plots import get_task_classification
from contributor_tools.automated_fine_tuning import AutomatedFineTuner


class DraggableBox:
    """
    A draggable validation range box that can be interactively adjusted.
    """
    
    def __init__(self, ax, phase: int, var_name: str, min_val: float, max_val: float, 
                 callback=None, color='lightgreen', edgecolor='black', allow_x_drag=True):
        """
        Initialize a draggable validation range box.
        
        Args:
            ax: Matplotlib axis to draw on
            phase: Phase percentage (0, 25, 50, 75)
            var_name: Variable name this box represents
            min_val: Initial minimum value
            max_val: Initial maximum value
            callback: Function to call when box is modified
            color: Fill color
            edgecolor: Edge color
            allow_x_drag: Whether to allow horizontal dragging
        """
        self.ax = ax
        self.phase = phase
        self.original_phase = phase  # Store original phase
        self.var_name = var_name
        self.callback = callback
        self.color = color
        self.edgecolor = edgecolor
        self.box_width = 8
        self.allow_x_drag = allow_x_drag
        
        # Current values
        self.min_val = min_val
        self.max_val = max_val
        
        # Create rectangle
        self.rect = patches.Rectangle(
            (phase - self.box_width/2, min_val), 
            self.box_width, 
            max_val - min_val,
            linewidth=1.5, 
            edgecolor=edgecolor,
            facecolor=color, 
            alpha=0.4,
            picker=True,  # Make it pickable
            zorder=10
        )
        self.ax.add_patch(self.rect)
        
        # Add text labels
        self.min_text = self.ax.text(phase, min_val - 0.02, f'{min_val:.3f}',
                                     ha='center', va='top', fontsize=7, 
                                     fontweight='bold', zorder=11)
        self.max_text = self.ax.text(phase, max_val + 0.02, f'{max_val:.3f}',
                                     ha='center', va='bottom', fontsize=7,
                                     fontweight='bold', zorder=11)
        
        # Add phase label
        self.phase_text = self.ax.text(phase, self.ax.get_ylim()[1], f'{phase}%',
                                       ha='center', va='bottom', fontsize=8,
                                       fontweight='bold', color='blue', zorder=11)
        
        # Dragging state
        self.dragging = None  # None, 'top', 'bottom', or 'middle'
        self.drag_start_x = None
        self.drag_start_y = None
        self.drag_start_phase = None
        self.drag_start_min = None
        self.drag_start_max = None
        
        # Connect events
        self.cidpress = self.ax.figure.canvas.mpl_connect('button_press_event', self.on_press)
        self.cidrelease = self.ax.figure.canvas.mpl_connect('button_release_event', self.on_release)
        self.cidmotion = self.ax.figure.canvas.mpl_connect('motion_notify_event', self.on_motion)
    
    def on_press(self, event):
        """Handle mouse press event."""
        if event.inaxes != self.ax:
            return
        
        # Check if click is within the box x-range
        if abs(event.xdata - self.phase) > self.box_width/2:
            return
        
        # Determine what part of the box was clicked
        edge_threshold = 0.05 * (self.max_val - self.min_val)  # 5% of box height
        
        if self.min_val <= event.ydata <= self.max_val:
            if abs(event.ydata - self.max_val) < edge_threshold:
                self.dragging = 'top'
                self.rect.set_edgecolor('red')
            elif abs(event.ydata - self.min_val) < edge_threshold:
                self.dragging = 'bottom'
                self.rect.set_edgecolor('blue')
            else:
                self.dragging = 'middle'
                self.rect.set_edgecolor('green')
            
            self.drag_start_x = event.xdata
            self.drag_start_y = event.ydata
            self.drag_start_phase = self.phase
            self.drag_start_min = self.min_val
            self.drag_start_max = self.max_val
            self.ax.figure.canvas.draw_idle()
    
    def on_motion(self, event):
        """Handle mouse motion event."""
        if self.dragging is None or event.inaxes != self.ax:
            return
        
        dy = event.ydata - self.drag_start_y
        dx = event.xdata - self.drag_start_x if self.allow_x_drag else 0
        
        if self.dragging == 'top':
            # Dragging top edge - adjust max value
            new_max = self.drag_start_max + dy
            if new_max > self.min_val + 0.01:  # Minimum box height
                self.max_val = new_max
        elif self.dragging == 'bottom':
            # Dragging bottom edge - adjust min value
            new_min = self.drag_start_min + dy
            if new_min < self.max_val - 0.01:  # Minimum box height
                self.min_val = new_min
        elif self.dragging == 'middle':
            # Dragging whole box - move both values and potentially phase
            self.min_val = self.drag_start_min + dy
            self.max_val = self.drag_start_max + dy
            
            # Handle x-axis movement if enabled
            if self.allow_x_drag:
                new_phase = self.drag_start_phase + dx
                # Constrain to 0-100 range and snap to nearest integer
                new_phase = max(0, min(100, round(new_phase)))
                if new_phase != self.phase:
                    self.phase = new_phase
                    # Update rectangle x position
                    self.rect.set_x(self.phase - self.box_width/2)
                    # Update phase label
                    self.phase_text.set_text(f'{self.phase}%')
                    self.phase_text.set_position((self.phase, self.ax.get_ylim()[1]))
        
        # Update rectangle y position and height
        self.rect.set_y(self.min_val)
        self.rect.set_height(self.max_val - self.min_val)
        
        # Update text labels
        self.min_text.set_text(f'{self.min_val:.3f}')
        self.min_text.set_position((self.phase, self.min_val - 0.02))
        self.max_text.set_text(f'{self.max_val:.3f}')
        self.max_text.set_position((self.phase, self.max_val + 0.02))
        
        self.ax.figure.canvas.draw_idle()
    
    def on_release(self, event):
        """Handle mouse release event."""
        if self.dragging is not None:
            self.dragging = None
            self.rect.set_edgecolor(self.edgecolor)
            self.ax.figure.canvas.draw_idle()
            
            # Call callback if provided
            if self.callback:
                self.callback(self)
    
    def get_range(self) -> Tuple[float, float]:
        """Get current min/max range."""
        return self.min_val, self.max_val
    
    def get_phase(self) -> int:
        """Get current phase value."""
        return self.phase
    
    def set_range(self, min_val: float, max_val: float):
        """Set new min/max range."""
        self.min_val = min_val
        self.max_val = max_val
        
        # Update rectangle
        self.rect.set_y(self.min_val)
        self.rect.set_height(self.max_val - self.min_val)
        
        # Update text labels
        self.min_text.set_text(f'{self.min_val:.3f}')
        self.min_text.set_position((self.phase, self.min_val - 0.02))
        self.max_text.set_text(f'{self.max_val:.3f}')
        self.max_text.set_position((self.phase, self.max_val + 0.02))
    
    def remove(self):
        """Remove the box from the plot."""
        try:
            # Remove from axes instead of calling remove() on artist
            if self.rect in self.ax.patches:
                self.ax.patches.remove(self.rect)
            if self.min_text in self.ax.texts:
                self.ax.texts.remove(self.min_text)
            if self.max_text in self.ax.texts:
                self.ax.texts.remove(self.max_text)
            if self.phase_text in self.ax.texts:
                self.ax.texts.remove(self.phase_text)
        except:
            pass  # Ignore if already removed
        
        # Disconnect events
        try:
            self.ax.figure.canvas.mpl_disconnect(self.cidpress)
            self.ax.figure.canvas.mpl_disconnect(self.cidrelease)
            self.ax.figure.canvas.mpl_disconnect(self.cidmotion)
        except:
            pass


class InteractiveValidationTuner:
    """
    Main GUI application for interactive validation range tuning.
    """
    
    def __init__(self):
        """Initialize the interactive validation tuner."""
        self.validation_data = {}
        self.dataset_path = None
        self.locomotion_data = None
        self.current_task = None
        self.current_mode = 'kinematic'
        self.draggable_boxes = []
        self.data_cache = {}
        self.modified = False
        
        # Setup the GUI
        self.setup_gui()
        
        # Auto-load default files
        self.auto_load_defaults()
    
    def setup_gui(self):
        """Setup the main GUI window."""
        # Create main window
        self.root = tk.Tk()
        self.root.title("Interactive Validation Range Tuner")
        
        # Start maximized
        try:
            self.root.state('zoomed')  # Windows
        except:
            # Linux/Mac alternative
            self.root.attributes('-zoomed', True)
        
        # Bind F11 for fullscreen toggle
        self.root.bind('<F11>', self.toggle_fullscreen)
        self.root.bind('<Escape>', self.exit_fullscreen)
        self.fullscreen = False
        
        # Create menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Validation Ranges (YAML)...", command=self.load_validation_ranges)
        file_menu.add_command(label="Load Dataset (Parquet)...", command=self.load_dataset)
        file_menu.add_separator()
        file_menu.add_command(label="Save Validation Ranges...", command=self.save_validation_ranges)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Create toolbar frame
        toolbar_frame = ttk.Frame(self.root)
        toolbar_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Task selection
        ttk.Label(toolbar_frame, text="Task:").pack(side=tk.LEFT, padx=5)
        self.task_var = tk.StringVar()
        self.task_dropdown = ttk.Combobox(toolbar_frame, textvariable=self.task_var, width=20, state='readonly')
        self.task_dropdown.pack(side=tk.LEFT, padx=5)
        self.task_dropdown.bind('<<ComboboxSelected>>', self.on_task_changed)
        
        # Mode selection
        ttk.Label(toolbar_frame, text="Mode:").pack(side=tk.LEFT, padx=20)
        self.mode_var = tk.StringVar(value='kinematic')
        modes = [('Kinematic', 'kinematic'), ('Kinetic', 'kinetic'), ('Segment', 'segment')]
        for text, value in modes:
            ttk.Radiobutton(toolbar_frame, text=text, variable=self.mode_var, 
                          value=value, command=self.on_mode_changed).pack(side=tk.LEFT, padx=5)
        
        # Buttons
        ttk.Button(toolbar_frame, text="Auto-Tune", command=self.auto_tune).pack(side=tk.LEFT, padx=20)
        
        # Validate button (disabled by default)
        self.validate_button = ttk.Button(toolbar_frame, text="Validate", command=self.run_validation_update, state='disabled')
        self.validate_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(toolbar_frame, text="Reset", command=self.reset_ranges).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar_frame, text="Refresh Plot", command=self.refresh_plot).pack(side=tk.LEFT, padx=5)
        
        # Create scrollable matplotlib figure frame
        self.create_scrollable_plot_area()
        
        # Status bar
        self.status_bar = ttk.Label(self.root, text="Ready. Load validation ranges and dataset to begin.", 
                                   relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Initialize empty plot
        self.create_empty_plot()
    
    def auto_load_defaults(self):
        """Auto-load default validation ranges and dataset."""
        # Load default validation ranges
        default_ranges_path = project_root / "contributor_tools" / "validation_ranges" / "default_ranges.yaml"
        if default_ranges_path.exists():
            try:
                # Load YAML directly
                with open(default_ranges_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Extract validation data
                self.validation_data = {}
                if 'tasks' in config:
                    for task_name, task_data in config['tasks'].items():
                        self.validation_data[task_name] = {}
                        if 'phases' in task_data:
                            for phase_str, variables in task_data['phases'].items():
                                phase = int(phase_str)
                                self.validation_data[task_name][phase] = variables
                
                # Update task dropdown
                tasks = list(self.validation_data.keys())
                self.task_dropdown['values'] = tasks
                if tasks:
                    self.task_dropdown.set(tasks[0])
                    self.current_task = tasks[0]
                
                self.status_bar.config(text=f"Loaded default validation ranges")
                self.modified = False
            except Exception as e:
                print(f"Could not load default ranges: {e}")
        
        # Load default dataset
        default_dataset_path = project_root / "converted_datasets" / "umich_2021_phase.parquet"
        if default_dataset_path.exists():
            try:
                self.dataset_path = default_dataset_path
                
                # Try loading with different phase column names
                try:
                    # Try with 'phase' column first
                    self.locomotion_data = LocomotionData(str(self.dataset_path))
                except ValueError as e:
                    if "Missing required columns: ['phase']" in str(e):
                        # Try with 'phase_percent' column
                        self.locomotion_data = LocomotionData(
                            str(self.dataset_path),
                            phase_col='phase_percent'
                        )
                    else:
                        raise e
                
                # Clear data cache
                self.data_cache = {}
                
                self.status_bar.config(text=f"Loaded defaults: {default_ranges_path.name} and {default_dataset_path.name}")
                
                # Update plot if validation ranges are loaded
                if self.validation_data and self.current_task:
                    self.update_plot()
                    # Run initial validation
                    self.run_validation_update()
            except Exception as e:
                print(f"Could not load default dataset: {e}")
    
    def create_scrollable_plot_area(self):
        """Create a scrollable area for the plots."""
        # Create main container
        self.plot_container = ttk.Frame(self.root)
        self.plot_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Create canvas and scrollbar
        self.plot_canvas = tk.Canvas(self.plot_container, bg='white')
        self.v_scrollbar = ttk.Scrollbar(self.plot_container, orient=tk.VERTICAL, command=self.plot_canvas.yview)
        self.h_scrollbar = ttk.Scrollbar(self.plot_container, orient=tk.HORIZONTAL, command=self.plot_canvas.xview)
        
        # Create frame inside canvas
        self.plot_frame = ttk.Frame(self.plot_canvas)
        self.plot_frame_id = self.plot_canvas.create_window(0, 0, anchor='nw', window=self.plot_frame)
        
        # Configure canvas scrolling
        self.plot_canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)
        
        # Pack scrollbars and canvas
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.plot_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind canvas resize
        self.plot_frame.bind('<Configure>', self.on_plot_frame_configure)
        self.plot_canvas.bind('<Configure>', self.on_canvas_configure)
    
    def on_plot_frame_configure(self, event=None):
        """Update scroll region when plot frame changes."""
        self.plot_canvas.configure(scrollregion=self.plot_canvas.bbox('all'))
    
    def on_canvas_configure(self, event=None):
        """Update plot frame width when canvas changes."""
        # Make plot frame fill canvas width
        canvas_width = event.width if event else self.plot_canvas.winfo_width()
        self.plot_canvas.itemconfig(self.plot_frame_id, width=canvas_width)
    
    def toggle_fullscreen(self, event=None):
        """Toggle fullscreen mode."""
        self.fullscreen = not self.fullscreen
        self.root.attributes('-fullscreen', self.fullscreen)
    
    def exit_fullscreen(self, event=None):
        """Exit fullscreen mode."""
        self.fullscreen = False
        self.root.attributes('-fullscreen', False)
    
    def create_empty_plot(self):
        """Create an empty matplotlib figure."""
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        
        # Get window dimensions for dynamic sizing
        window_width = self.root.winfo_width() if self.root.winfo_width() > 1 else 1400
        window_height = self.root.winfo_height() if self.root.winfo_height() > 1 else 900
        
        # Calculate figure size based on window
        dpi = 100
        fig_width = (window_width - 100) / dpi  # Account for scrollbar and padding
        fig_height = 8  # Start with reasonable height
        
        self.fig = Figure(figsize=(fig_width, fig_height), dpi=dpi, constrained_layout=True)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Create initial empty axes
        self.ax = self.fig.add_subplot(111)
        self.ax.text(0.5, 0.5, 'Loading default files...', 
                    ha='center', va='center', fontsize=16, color='gray')
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)
        self.canvas.draw()
        
        # Update scroll region
        self.plot_frame.update_idletasks()
        self.on_plot_frame_configure()
    
    def load_validation_ranges(self):
        """Load validation ranges from YAML file."""
        file_path = filedialog.askopenfilename(
            title="Select Validation Ranges YAML",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")],
            initialdir=str(project_root / "contributor_tools" / "validation_ranges")
        )
        
        if not file_path:
            return
        
        try:
            # Load YAML directly
            with open(file_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Extract validation data
            self.validation_data = {}
            if 'tasks' in config:
                for task_name, task_data in config['tasks'].items():
                    self.validation_data[task_name] = {}
                    if 'phases' in task_data:
                        for phase_str, variables in task_data['phases'].items():
                            phase = int(phase_str)
                            self.validation_data[task_name][phase] = variables
            
            # Update task dropdown
            tasks = list(self.validation_data.keys())
            self.task_dropdown['values'] = tasks
            if tasks:
                self.task_dropdown.set(tasks[0])
                self.current_task = tasks[0]
            
            self.status_bar.config(text=f"Loaded validation ranges from: {Path(file_path).name}")
            self.modified = False
            
            # Update plot if dataset is loaded
            if self.locomotion_data is not None:
                self.update_plot()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load validation ranges:\n{str(e)}")
    
    def load_dataset(self):
        """Load dataset from parquet file."""
        file_path = filedialog.askopenfilename(
            title="Select Dataset Parquet",
            filetypes=[("Parquet files", "*.parquet"), ("All files", "*.*")],
            initialdir=str(project_root / "converted_datasets")
        )
        
        if not file_path:
            return
        
        try:
            self.dataset_path = Path(file_path)
            
            # Try loading with different phase column names
            try:
                # Try with 'phase' column first
                self.locomotion_data = LocomotionData(str(self.dataset_path))
            except ValueError as e:
                if "Missing required columns: ['phase']" in str(e):
                    # Try with 'phase_percent' column
                    self.locomotion_data = LocomotionData(
                        str(self.dataset_path),
                        phase_col='phase_percent'
                    )
                else:
                    raise e
            
            # Clear data cache
            self.data_cache = {}
            
            self.status_bar.config(text=f"Loaded dataset: {self.dataset_path.name}")
            
            # Update plot if validation ranges are loaded
            if self.validation_data and self.current_task:
                self.update_plot()
                # Run initial validation
                self.run_validation_update()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load dataset:\n{str(e)}")
    
    def on_task_changed(self, event=None):
        """Handle task selection change."""
        self.current_task = self.task_var.get()
        if self.current_task:
            self.update_plot()
    
    def on_mode_changed(self):
        """Handle mode selection change."""
        self.current_mode = self.mode_var.get()
        self.update_plot()
    
    def update_plot(self):
        """Update the plot with current task and mode using two-column layout."""
        if not self.current_task or self.current_task not in self.validation_data:
            return
        
        # Clear existing plot
        self.fig.clear()
        
        # Remove existing draggable boxes
        for box in self.draggable_boxes:
            box.remove()
        self.draggable_boxes = []
        
        # Get variables for current mode
        if self.current_mode == 'kinematic':
            variables = [
                'hip_flexion_angle_ipsi_rad',
                'knee_flexion_angle_ipsi_rad',
                'ankle_dorsiflexion_angle_ipsi_rad'
            ]
            variable_labels = [
                'Hip Flexion Angle',
                'Knee Flexion Angle',
                'Ankle Dorsiflexion Angle'
            ]
            n_vars = 3
        elif self.current_mode == 'kinetic':
            variables = [
                'hip_flexion_moment_ipsi_Nm',
                'knee_flexion_moment_ipsi_Nm',
                'ankle_dorsiflexion_moment_ipsi_Nm'
            ]
            variable_labels = [
                'Hip Flexion Moment',
                'Knee Flexion Moment',
                'Ankle Dorsiflexion Moment'
            ]
            n_vars = 3
        elif self.current_mode == 'segment':
            variables = [
                'pelvis_tilt_angle_rad', 'pelvis_obliquity_angle_rad', 'pelvis_rotation_angle_rad',
                'trunk_flexion_angle_rad', 'trunk_lateral_angle_rad', 'trunk_rotation_angle_rad',
                'thigh_angle_ipsi_rad',
                'shank_angle_ipsi_rad',
                'foot_angle_ipsi_rad'
            ]
            variable_labels = [
                'Pelvis Tilt', 'Pelvis Obliquity', 'Pelvis Rotation',
                'Trunk Flexion', 'Trunk Lateral', 'Trunk Rotation',
                'Thigh Angle',
                'Shank Angle',
                'Foot Angle'
            ]
            n_vars = 9
        
        # Store current variables for later validation
        self.current_variables = variables
        
        # Use cached validation results if available, otherwise show all as gray
        if not hasattr(self, 'cached_failing_strides'):
            self.cached_failing_strides = {}
        failing_strides = self.cached_failing_strides
        
        # Calculate dynamic figure height based on number of variables
        window_width = self.root.winfo_width() if self.root.winfo_width() > 1 else 1400
        dpi = 100
        fig_width = (window_width - 100) / dpi
        
        # Height per subplot row (in inches)
        row_height = 2.5  # Increased for better dragging space
        fig_height = n_vars * row_height + 1  # Add space for title
        
        # Create new figure with dynamic size
        from matplotlib.figure import Figure
        self.fig = Figure(figsize=(fig_width, fig_height), dpi=dpi)
        
        # Use tight layout to minimize whitespace
        self.fig.subplots_adjust(left=0.06, right=0.98, top=0.96, bottom=0.02, hspace=0.25, wspace=0.15)
        
        # Create subplots with 2 columns (pass/fail)
        self.axes_pass = []
        self.axes_fail = []
        
        for i in range(n_vars):
            # Create pass and fail axes side by side
            ax_pass = self.fig.add_subplot(n_vars, 2, i*2 + 1)
            ax_fail = self.fig.add_subplot(n_vars, 2, i*2 + 2)
            self.axes_pass.append(ax_pass)
            self.axes_fail.append(ax_fail)
            
            var_name = variables[i] if i < len(variables) else None
            var_label = variable_labels[i] if i < len(variable_labels) else f"Variable {i}"
            
            # Get y-axis range with expanded margins (30% instead of 10%)
            y_min, y_max = self.get_expanded_y_range(var_name) if var_name else (-1, 1)
            
            # Plot data for PASS column
            passed_count = 0
            if self.locomotion_data and var_name:
                passed_count = self.plot_variable_data_pass_fail(
                    ax_pass, var_name, failing_strides.get(var_name, set()), 
                    show_pass=True
                )
            
            # Plot data for FAIL column  
            failed_count = 0
            if self.locomotion_data and var_name:
                failed_count = self.plot_variable_data_pass_fail(
                    ax_fail, var_name, failing_strides.get(var_name, set()),
                    show_pass=False
                )
            
            # Add draggable boxes for validation ranges on BOTH axes
            if var_name and self.current_task in self.validation_data:
                task_data = self.validation_data[self.current_task]
                
                # Get all phases from task data
                phases = sorted([int(p) for p in task_data.keys() if str(p).isdigit()])
                
                for phase in phases:
                    if phase in task_data and var_name in task_data[phase]:
                        range_data = task_data[phase][var_name]
                        if 'min' in range_data and 'max' in range_data:
                            min_val = range_data['min']
                            max_val = range_data['max']
                            
                            # Skip None values
                            if min_val is None or max_val is None:
                                continue
                            
                            # Create draggable box on pass axis
                            box_pass = DraggableBox(
                                ax_pass, phase, var_name, min_val, max_val,
                                callback=self.on_box_changed,
                                color='lightgreen',
                                allow_x_drag=True
                            )
                            self.draggable_boxes.append(box_pass)
                            
                            # Create draggable box on fail axis (also interactive)
                            box_fail = DraggableBox(
                                ax_fail, phase, var_name, min_val, max_val,
                                callback=self.on_box_changed,  # Add callback for fail side too
                                color='lightcoral',
                                allow_x_drag=True  # Allow dragging on fail side as well
                            )
                            self.draggable_boxes.append(box_fail)
                            
                            # Store bidirectional references for synchronization
                            box_pass.paired_box = box_fail
                            box_fail.paired_box = box_pass  # Bidirectional pairing
            
            # Setup axes
            ax_pass.set_title(f'{var_label} - ✓ Pass ({passed_count})', fontsize=9, fontweight='bold')
            ax_fail.set_title(f'{var_label} - ✗ Fail ({failed_count})', fontsize=9, fontweight='bold')
            
            for ax in [ax_pass, ax_fail]:
                ax.set_xlim(-5, 105)
                ax.set_ylim(y_min, y_max)
                ax.set_xticks([0, 25, 50, 75, 100])
                ax.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
                ax.grid(True, alpha=0.3)
                
                # Only add x-label to bottom row
                if i == n_vars - 1:
                    task_type = get_task_classification(self.current_task)
                    x_label = 'Gait Phase' if task_type == 'gait' else 'Movement Phase'
                    ax.set_xlabel(x_label, fontsize=9)
                
                # Set y-label only on left column
                if ax == ax_pass:
                    if self.current_mode == 'kinematic' or self.current_mode == 'segment':
                        ax.set_ylabel('rad', fontsize=8)
                    else:
                        ax.set_ylabel('Nm', fontsize=8)
        
        # Add title
        mode_label = self.current_mode.capitalize()
        self.fig.suptitle(f'{self.current_task.replace("_", " ").title()} - {mode_label} Validation Ranges',
                         fontsize=12, fontweight='bold', y=0.99)
        
        # Create/update canvas
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        if hasattr(self, 'canvas'):
            self.canvas.get_tk_widget().destroy()
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas.draw()
        
        # Update scroll region
        self.plot_frame.update_idletasks()
        self.on_plot_frame_configure()
    
    def run_validation(self, variables):
        """Run validation to determine which strides fail for each variable."""
        failing_strides = {}
        
        if not self.locomotion_data or not self.current_task:
            return failing_strides
        
        task_data = self.validation_data.get(self.current_task, {})
        if not task_data:
            return failing_strides
        
        # Get all data for this task
        try:
            subjects = self.locomotion_data.get_subjects()
            
            for var_name in variables:
                failing_strides[var_name] = set()
                stride_idx = 0
                
                for subject in subjects:
                    try:
                        cycles_data, feature_names = self.locomotion_data.get_cycles(
                            subject=subject,
                            task=self.current_task,
                            features=None
                        )
                        
                        if cycles_data.size == 0 or var_name not in feature_names:
                            continue
                        
                        var_idx = feature_names.index(var_name)
                        
                        # Check each stride against validation ranges
                        for stride in range(cycles_data.shape[0]):
                            stride_data = cycles_data[stride, :, var_idx]
                            
                            # Check each phase
                            for phase in task_data.keys():
                                if not str(phase).isdigit():
                                    continue
                                phase = int(phase)
                                
                                if var_name in task_data[phase]:
                                    range_data = task_data[phase][var_name]
                                    if 'min' in range_data and 'max' in range_data:
                                        min_val = range_data['min']
                                        max_val = range_data['max']
                                        
                                        if min_val is None or max_val is None:
                                            continue
                                        
                                        # Map phase to index (0-149)
                                        phase_idx = int(phase * 1.49)  # 0->0, 100->149
                                        
                                        # Check if value is outside range
                                        if stride_data[phase_idx] < min_val or stride_data[phase_idx] > max_val:
                                            failing_strides[var_name].add(stride_idx)
                                            break  # This stride fails, no need to check other phases
                            
                            stride_idx += 1
                    except:
                        continue
        except:
            pass
        
        return failing_strides
    
    def get_expanded_y_range(self, var_name):
        """Get y-axis range with expanded margins for more dragging space."""
        y_min, y_max = -1, 1  # Default
        
        if not self.current_task or var_name is None:
            return y_min, y_max
        
        task_data = self.validation_data.get(self.current_task, {})
        
        # Get range from validation boxes
        all_mins = []
        all_maxs = []
        
        for phase in task_data.keys():
            if not str(phase).isdigit():
                continue
            phase = int(phase)
            
            if var_name in task_data[phase]:
                range_data = task_data[phase][var_name]
                if 'min' in range_data and 'max' in range_data:
                    min_val = range_data['min']
                    max_val = range_data['max']
                    
                    if min_val is not None and max_val is not None:
                        all_mins.append(min_val)
                        all_maxs.append(max_val)
        
        # Also include data range if available
        cache_key = f"{self.current_task}_{var_name}"
        if cache_key in self.data_cache and len(self.data_cache[cache_key]) > 0:
            data = self.data_cache[cache_key]
            all_mins.append(np.min(data))
            all_maxs.append(np.max(data))
        
        if all_mins and all_maxs:
            data_min = min(all_mins)
            data_max = max(all_maxs)
            # Expand range by 30% for more dragging space
            margin = (data_max - data_min) * 0.3
            y_min = data_min - margin
            y_max = data_max + margin
        
        return y_min, y_max
    
    def plot_variable_data_pass_fail(self, ax, var_name, failed_stride_indices, show_pass=True):
        """Plot data for a variable, showing either passing or failing strides."""
        count = 0
        
        # Check cache first
        cache_key = f"{self.current_task}_{var_name}"
        if cache_key in self.data_cache:
            all_data = self.data_cache[cache_key]
        else:
            # Load data from all subjects
            all_data = []
            try:
                subjects = self.locomotion_data.get_subjects()
                for subject in subjects:
                    try:
                        cycles_data, feature_names = self.locomotion_data.get_cycles(
                            subject=subject,
                            task=self.current_task,
                            features=None
                        )
                        
                        if cycles_data.size == 0:
                            continue
                        
                        # Find variable index
                        if var_name in feature_names:
                            var_idx = feature_names.index(var_name)
                            all_data.append(cycles_data[:, :, var_idx])
                    except:
                        continue
                
                # Cache the data
                if all_data:
                    all_data = np.vstack(all_data)
                    self.data_cache[cache_key] = all_data
            except:
                pass
        
        # Plot data if available
        if len(all_data) > 0:
            phase_percent = np.linspace(0, 100, 150)
            
            for stride_idx, stride in enumerate(all_data):
                if show_pass and stride_idx not in failed_stride_indices:
                    # Plot passing stride in green
                    ax.plot(phase_percent, stride, color='green', alpha=0.2, linewidth=0.5, zorder=1)
                    count += 1
                elif not show_pass and stride_idx in failed_stride_indices:
                    # Plot failing stride in red
                    ax.plot(phase_percent, stride, color='red', alpha=0.3, linewidth=0.5, zorder=1)
                    count += 1
            
            # Plot mean of the displayed strides
            if count > 0:
                if show_pass:
                    pass_strides = [all_data[i] for i in range(len(all_data)) if i not in failed_stride_indices]
                    if pass_strides:
                        mean_pattern = np.mean(pass_strides, axis=0)
                        ax.plot(phase_percent, mean_pattern, color='darkgreen', linewidth=2, zorder=5)
                else:
                    fail_strides = [all_data[i] for i in range(len(all_data)) if i in failed_stride_indices]
                    if fail_strides:
                        mean_pattern = np.mean(fail_strides, axis=0)
                        ax.plot(phase_percent, mean_pattern, color='darkred', linewidth=2, zorder=5)
        
        return count
    
    def plot_variable_data(self, ax, var_name):
        """Plot actual data for a variable if available."""
        # Check cache first
        cache_key = f"{self.current_task}_{var_name}"
        if cache_key in self.data_cache:
            all_data = self.data_cache[cache_key]
        else:
            # Load data from all subjects
            all_data = []
            try:
                subjects = self.locomotion_data.get_subjects()
                for subject in subjects:
                    try:
                        cycles_data, feature_names = self.locomotion_data.get_cycles(
                            subject=subject,
                            task=self.current_task,
                            features=None
                        )
                        
                        if cycles_data.size == 0:
                            continue
                        
                        # Find variable index
                        if var_name in feature_names:
                            var_idx = feature_names.index(var_name)
                            all_data.append(cycles_data[:, :, var_idx])
                    except:
                        continue
                
                # Cache the data
                if all_data:
                    all_data = np.vstack(all_data)
                    self.data_cache[cache_key] = all_data
            except:
                pass
        
        # Plot data if available
        if len(all_data) > 0:
            phase_percent = np.linspace(0, 100, 150)
            for stride in all_data:
                ax.plot(phase_percent, stride, color='gray', alpha=0.1, linewidth=0.5, zorder=1)
            
            # Plot mean
            mean_pattern = np.mean(all_data, axis=0)
            ax.plot(phase_percent, mean_pattern, color='black', linewidth=2, zorder=5)
    
    def on_box_changed(self, box):
        """Handle changes to a draggable box."""
        # First, handle phase changes if the box was moved horizontally
        if hasattr(box, 'original_phase') and box.phase != box.original_phase:
            # Remove data from old phase
            if box.original_phase in self.validation_data[self.current_task]:
                if box.var_name in self.validation_data[self.current_task][box.original_phase]:
                    del self.validation_data[self.current_task][box.original_phase][box.var_name]
                # Clean up empty phase
                if not self.validation_data[self.current_task][box.original_phase]:
                    del self.validation_data[self.current_task][box.original_phase]
            
            # Update original phase for next time
            box.original_phase = box.phase
        
        # Update validation data with new values
        if self.current_task in self.validation_data:
            if box.phase not in self.validation_data[self.current_task]:
                self.validation_data[self.current_task][box.phase] = {}
            
            min_val, max_val = box.get_range()
            self.validation_data[self.current_task][box.phase][box.var_name] = {
                'min': min_val,
                'max': max_val
            }
            
            # Synchronize paired box if it exists
            if hasattr(box, 'paired_box') and box.paired_box:
                box.paired_box.phase = box.phase
                box.paired_box.set_range(min_val, max_val)
                # Update position if phase changed
                box.paired_box.rect.set_x(box.phase - box.paired_box.box_width/2)
                box.paired_box.phase_text.set_text(f'{box.phase}%')
                box.paired_box.phase_text.set_position((box.phase, box.paired_box.ax.get_ylim()[1]))
                box.paired_box.ax.figure.canvas.draw_idle()
            
            self.modified = True
            self.status_bar.config(text=f"Modified: {box.var_name} at phase {box.phase}% - Press Validate to update")
            
            # Enable validate button
            if hasattr(self, 'validate_button'):
                self.validate_button.config(state='normal')
    
    def auto_tune(self):
        """Run auto-tuning for current task and mode."""
        if not self.dataset_path:
            messagebox.showwarning("Warning", "Please load a dataset first.")
            return
        
        if not self.current_task:
            messagebox.showwarning("Warning", "Please select a task.")
            return
        
        try:
            # Create auto-tuner
            tuner = AutomatedFineTuner(str(self.dataset_path), mode=self.current_mode)
            
            # Run tuning (using percentile_95 method by default)
            self.status_bar.config(text="Running auto-tuning...")
            self.root.update()
            
            results = tuner.run_statistical_tuning(
                method='percentile_95',
                save_ranges=False,
                save_report=False
            )
            
            if results['success']:
                # Update validation data with tuned ranges
                tuned_ranges = results['validation_ranges']
                
                if self.current_task in tuned_ranges:
                    # Update our validation data
                    self.validation_data[self.current_task] = tuned_ranges[self.current_task]
                    
                    # Update the plot
                    self.update_plot()
                    
                    # Run validation with new ranges
                    self.run_validation_update()
                    
                    self.modified = True
                    self.status_bar.config(text="Auto-tuning complete. Ranges updated and validated.")
                else:
                    messagebox.showinfo("Info", f"No data available for task: {self.current_task}")
            else:
                messagebox.showerror("Error", f"Auto-tuning failed: {results.get('error', 'Unknown error')}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Auto-tuning failed:\n{str(e)}")
            self.status_bar.config(text="Auto-tuning failed.")
    
    def reset_ranges(self):
        """Reset ranges to original values."""
        if not self.modified:
            messagebox.showinfo("Info", "No changes to reset.")
            return
        
        result = messagebox.askyesno("Confirm Reset", "Reset all changes to original values?")
        if result:
            # Reload validation ranges
            self.load_validation_ranges()
    
    def run_validation_update(self):
        """Run validation and update stride colors based on current ranges."""
        if not self.locomotion_data or not hasattr(self, 'current_variables'):
            return
        
        self.status_bar.config(text="Running validation...")
        self.root.update()
        
        # Run validation with current ranges
        self.cached_failing_strides = self.run_validation(self.current_variables)
        
        # Update the plot to show new pass/fail colors
        self.update_stride_colors()
        
        # Disable validate button
        self.validate_button.config(state='disabled')
        self.status_bar.config(text="Validation complete.")
    
    def update_stride_colors(self):
        """Update only the stride colors without recreating the entire plot."""
        if not hasattr(self, 'axes_pass') or not hasattr(self, 'axes_fail'):
            return
        
        failing_strides = self.cached_failing_strides
        
        # Clear and redraw data on each axis
        for i, (ax_pass, ax_fail) in enumerate(zip(self.axes_pass, self.axes_fail)):
            var_name = self.current_variables[i] if i < len(self.current_variables) else None
            
            if not var_name:
                continue
            
            # Clear only the data lines (keep boxes)
            lines_to_remove = []
            for line in ax_pass.lines + ax_fail.lines:
                # Keep the boxes, remove the data lines
                if line.get_zorder() < 10:  # Data lines have lower z-order than boxes
                    lines_to_remove.append(line)
            
            for line in lines_to_remove:
                line.remove()
            
            # Replot with updated pass/fail status
            if self.locomotion_data and var_name:
                passed_count = self.plot_variable_data_pass_fail(
                    ax_pass, var_name, failing_strides.get(var_name, set()), 
                    show_pass=True
                )
                failed_count = self.plot_variable_data_pass_fail(
                    ax_fail, var_name, failing_strides.get(var_name, set()),
                    show_pass=False
                )
                
                # Update titles with new counts
                var_label = ax_pass.get_title().split(' - ')[0]  # Get original label
                ax_pass.set_title(f'{var_label} - ✓ Pass ({passed_count})', fontsize=9, fontweight='bold')
                ax_fail.set_title(f'{var_label} - ✗ Fail ({failed_count})', fontsize=9, fontweight='bold')
        
        self.canvas.draw_idle()
    
    def refresh_plot(self):
        """Refresh the current plot."""
        self.update_plot()
        self.status_bar.config(text="Plot refreshed.")
    
    def save_validation_ranges(self):
        """Save current validation ranges to YAML file."""
        if not self.validation_data:
            messagebox.showwarning("Warning", "No validation ranges to save.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save Validation Ranges",
            defaultextension=".yaml",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")],
            initialdir=str(project_root / "contributor_tools" / "validation_ranges")
        )
        
        if not file_path:
            return
        
        try:
            # Prepare YAML structure
            config = {
                'version': '2.0',
                'generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'Interactive Validation Tuner',
                'description': f'Interactively tuned validation ranges for {self.current_mode} features',
                'tasks': {}
            }
            
            # Add task data
            for task_name, task_data in self.validation_data.items():
                config['tasks'][task_name] = {'phases': {}}
                for phase, variables in task_data.items():
                    config['tasks'][task_name]['phases'][str(phase)] = variables
            
            # Save to file
            with open(file_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            self.modified = False
            self.status_bar.config(text=f"Saved validation ranges to: {Path(file_path).name}")
            messagebox.showinfo("Success", f"Validation ranges saved to:\n{Path(file_path).name}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save validation ranges:\n{str(e)}")
    
    def run(self):
        """Run the GUI application."""
        self.root.mainloop()


def main():
    """Main entry point."""
    if not TKINTER_AVAILABLE or not DISPLAY_AVAILABLE:
        print("\nInteractive Validation Tuner requires a graphical display.")
        if not TKINTER_AVAILABLE:
            print("\ntkinter is not available. Please install it using:")
            print("  - Ubuntu/Debian: sudo apt-get install python3-tk")
            print("  - Windows: tkinter should be included with Python")
            print("  - macOS: tkinter should be included with Python")
        else:
            print("\nNo display detected. If you're using WSL, you need an X server:")
            print("  1. Install an X server on Windows (e.g., VcXsrv, X410, or WSLg)")
            print("  2. Set DISPLAY environment variable: export DISPLAY=:0")
            print("  3. Or use Windows Terminal with WSLg (Windows 11)")
        print("\nAlternatively, you can use the command-line tools:")
        print("  - automated_fine_tuning.py for statistical auto-tuning")
        print("  - create_validation_range_plots.py for static plots")
        return 1
    
    app = InteractiveValidationTuner()
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())