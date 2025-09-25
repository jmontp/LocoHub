#!/usr/bin/env python3
"""
Interactive Validation Range Tuner

A GUI tool for interactively adjusting validation ranges by directly manipulating
boxes on the plot. Integrates with existing validation and plotting systems.

Features:
- Direct manipulation of validation range boxes
- Load/save YAML validation ranges
- Load parquet datasets for visualization
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
    
    5. Adjust validation ranges by dragging the colored boxes on the plot
    
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
import copy
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
from matplotlib.collections import LineCollection
import matplotlib.animation as animation

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import existing modules
from user_libs.python.locomotion_data import LocomotionData
from user_libs.python.feature_constants import get_feature_list
from internal.config_management.config_manager import ValidationConfigManager
from internal.plot_generation.filters_by_phase_plots import get_task_classification


class DraggableBox:
    """
    A draggable validation range box that can be interactively adjusted.
    Optimized with blitting for fast dragging performance.
    """
    
    def __init__(self, ax, phase: int, var_name: str, min_val: float, max_val: float, 
                 callback=None, color='lightgreen', edgecolor='black', allow_x_drag=True, parent=None):
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
            parent: Reference to InteractiveValidationTuner for unit conversion
        """
        # Validate input values to prevent None arithmetic errors
        if min_val is None or max_val is None:
            raise ValueError(f"DraggableBox cannot be created with None values: min_val={min_val}, max_val={max_val}")
        
        self.ax = ax
        self.phase = phase
        self.original_phase = phase  # Store original phase
        self.var_name = var_name
        self.callback = callback
        self.color = color
        self.edgecolor = edgecolor
        self.box_width = 8
        self.allow_x_drag = allow_x_drag
        self.parent = parent  # Store parent reference for unit conversion
        
        # Current values
        self.min_val = min_val
        self.max_val = max_val
        
        # Performance optimization: Cache expensive pixel-to-data conversion factors
        self._pixels_per_data_unit = None
        self._hover_extend_data = None
        self._last_ylim = None
        self._last_figure_size = None
        self._last_axes_position = None
        
        # Initialize conversion cache before using it
        self._update_conversion_cache()
        
        # PERFORMANCE: Smart background caching to avoid expensive redraws on click
        self.background_invalid = True
        
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
        
        # Define handle dimensions and offsets first
        handle_width = 3  # Fixed width in data units (narrow rectangle)
        handle_height = 0.15  # Fixed height in data units (vertically long)
        handle_offset = 0.03  # Small gap between handle and box for visual separation
        label_buffer = 0.02  # Additional buffer for readability
        
        # Add text labels positioned outside grab handle areas
        # Convert to display units if needed
        display_min = self._get_display_value(min_val)
        display_max = self._get_display_value(max_val)
        
        self.min_text = self.ax.text(phase, min_val - handle_height - handle_offset - label_buffer, f'{display_min:.3f}',
                                     ha='center', va='top', fontsize=7, 
                                     fontweight='bold', zorder=11)
        self.max_text = self.ax.text(phase, max_val + handle_offset + handle_height + label_buffer, f'{display_max:.3f}',
                                     ha='center', va='bottom', fontsize=7,
                                     fontweight='bold', zorder=11)
        
        # Add phase label
        self.phase_text = self.ax.text(phase, self.ax.get_ylim()[1], f'{phase}%',
                                       ha='center', va='bottom', fontsize=8,
                                       fontweight='bold', color='blue', zorder=11)
        
        # Create phase indicator for dragging (initially hidden)
        self.drag_phase_text = self.ax.text(phase, (min_val + max_val) / 2, '',
                                           ha='center', va='center', fontsize=10,
                                           fontweight='bold', color='black', 
                                           bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.8),
                                           visible=False, zorder=20)
        
        # Create vertical rectangular resize handles with slight offset from box edges (ALWAYS VISIBLE for better performance)
        self.top_handle = patches.Rectangle(
            (phase - handle_width/2, max_val + handle_offset), handle_width, handle_height,
            facecolor='lightgrey', edgecolor='black', linewidth=2,
            visible=True, zorder=20  # Always visible for performance
        )
        self.bottom_handle = patches.Rectangle(
            (phase - handle_width/2, min_val - handle_height - handle_offset), handle_width, handle_height,
            facecolor='lightgrey', edgecolor='black', linewidth=2,
            visible=True, zorder=20  # Always visible for performance
        )
        self.ax.add_patch(self.top_handle)
        self.ax.add_patch(self.bottom_handle)
        
        # Create transparent hover zone for better UX
        self.hover_zone = patches.Rectangle(
            (phase - self.box_width/2, min_val - self._hover_extend_data),
            self.box_width,
            (max_val - min_val) + 2 * self._hover_extend_data,
            facecolor='none', edgecolor='none', alpha=0,
            visible=True, zorder=1
        )
        self.ax.add_patch(self.hover_zone)
        
        # Dragging state
        self.dragging = None  # None, 'top', 'bottom', or 'middle'
        self.drag_start_x = None
        self.drag_start_y = None
        self.drag_start_phase = None
        self.drag_start_min = None
        self.drag_start_max = None
        
        # Blitting background storage
        self.background = None
        
        # Connect events (PERFORMANCE: Remove separate hover handler)
        self.cidpress = self.ax.figure.canvas.mpl_connect('button_press_event', self.on_press)
        self.cidrelease = self.ax.figure.canvas.mpl_connect('button_release_event', self.on_release)
        self.cidmotion = self.ax.figure.canvas.mpl_connect('motion_notify_event', self.on_motion)
        # NOTE: on_hover removed for performance - circles now always visible
        
        # Track if this box is selected
        self.selected = False
    
    def _get_display_value(self, value):
        """Convert value to display units if parent has conversion method."""
        if self.parent and hasattr(self.parent, 'convert_to_display_units'):
            return self.parent.convert_to_display_units(value, self.var_name)
        return value
    
    def _update_conversion_cache(self):
        """
        Update cached pixel-to-data conversion factors only when needed.
        PERFORMANCE OPTIMIZATION: Avoids recalculating on every mouse move.
        """
        current_ylim = self.ax.get_ylim()
        current_size = self.ax.figure.get_size_inches()
        current_position = self.ax.get_position()
        
        # Only recalculate if something changed
        if (self._pixels_per_data_unit is None or 
            current_ylim != self._last_ylim or 
            not np.array_equal(current_size, self._last_figure_size) or
            current_position.bounds != (self._last_axes_position.bounds if self._last_axes_position else None)):
            
            # Expensive calculations done only when needed
            fig_height_inches = current_size[1]
            axes_height_inches = current_position.height * fig_height_inches
            dpi = self.ax.figure.dpi
            data_range = current_ylim[1] - current_ylim[0]
            
            self._pixels_per_data_unit = (axes_height_inches * dpi) / data_range
            self._hover_extend_data = 35 / self._pixels_per_data_unit   # 35 pixels extension
            
            # Cache current state
            self._last_ylim = current_ylim
            self._last_figure_size = current_size.copy()
            self._last_axes_position = current_position
            
            # Background becomes invalid when plot geometry changes
            self.background_invalid = True
    
    def on_press(self, event):
        """Handle mouse press event with generous Y-range resize zones."""
        if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            return
        
        # Only handle left-clicks (button 1) for dragging - allow right-clicks to pass through
        if event.button != 1:
            print(f"DEBUG: DraggableBox {self.var_name} at phase {self.phase} ignoring button {event.button}")
            return
        
        # Check if click is within the box x-range (hover zone)
        if abs(event.xdata - self.phase) > self.box_width/2:
            return
        
        # Simple Y-coordinate based interaction zones
        if event.ydata > self.max_val:
            # Above box - resize top edge
            self.dragging = 'top'
            self.rect.set_edgecolor('red')
        elif event.ydata < self.min_val:
            # Below box - resize bottom edge
            self.dragging = 'bottom'
            self.rect.set_edgecolor('blue')
        elif self.min_val <= event.ydata <= self.max_val:
            # Inside box - drag both X and Y
            self.dragging = 'middle'
            self.rect.set_edgecolor('green')
        else:
            # Should not reach here
            return
        
        # Initialize drag
        self.drag_start_x = event.xdata
        self.drag_start_y = event.ydata
        self.drag_start_phase = self.phase
        self.drag_start_min = self.min_val
        self.drag_start_max = self.max_val
        
        # PERFORMANCE: Background is pre-cached by _cache_trace_backgrounds()
        # No expensive operations needed here - drag/resize initiation is instant!
        canvas = self.ax.figure.canvas
        
        # Background should be ready from 4-step algorithm
        # NO FALLBACK CACHING - this would capture boxes and cause trails!
        
        # Show phase indicator if dragging horizontally
        if self.dragging == 'middle' and self.allow_x_drag:
            self.drag_phase_text.set_visible(True)
            self.drag_phase_text.set_position((self.phase, (self.min_val + self.max_val) / 2))
            self.drag_phase_text.set_text(f'Phase: {self.phase}%')
    
    def invalidate_background(self):
        """Mark background cache as invalid, forcing redraw on next use."""
        self.background_invalid = True
        
    # PERFORMANCE OPTIMIZATION: on_hover method completely removed
    # Circles are now always visible for better performance
    # This eliminates expensive pixel-to-data conversions and draw calls on every mouse move
    
    def on_motion(self, event):
        """Handle mouse motion event with performance optimizations."""
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
                    # Update drag indicator
                    self.drag_phase_text.set_position((self.phase, (self.min_val + self.max_val) / 2))
                    self.drag_phase_text.set_text(f'Phase: {self.phase}%')
        
        # Update rectangle y position and height
        self.rect.set_y(self.min_val)
        self.rect.set_height(self.max_val - self.min_val)
        
        # Update text labels positioned outside grab handle areas
        handle_width = 3  # Same width as used in initialization
        handle_height = 0.15  # Same height as used in initialization
        handle_offset = 0.03  # Match handle offset
        label_buffer = 0.02  # Additional buffer for readability
        
        self.min_text.set_text(f'{self.min_val:.3f}')
        self.min_text.set_position((self.phase, self.min_val - handle_height - handle_offset - label_buffer))
        self.max_text.set_text(f'{self.max_val:.3f}')
        self.max_text.set_position((self.phase, self.max_val + handle_offset + handle_height + label_buffer))
        
        # Update handle positions with slight offset from box edges
        # Top handle: positioned above the validation box with offset
        self.top_handle.set_x(self.phase - handle_width/2)
        self.top_handle.set_y(self.max_val + handle_offset)
        
        # Bottom handle: positioned below the validation box with offset
        self.bottom_handle.set_x(self.phase - handle_width/2) 
        self.bottom_handle.set_y(self.min_val - handle_height - handle_offset)
        
        # Update hover zone position (using cached values)
        self.hover_zone.set_x(self.phase - self.box_width/2)
        self.hover_zone.set_y(self.min_val - self._hover_extend_data)
        self.hover_zone.set_height((self.max_val - self.min_val) + 2 * self._hover_extend_data)
        
        # Use blitting for fast updates only if background is valid
        if self.background is not None and not self.background_invalid:
            canvas = self.ax.figure.canvas
            # Restore the background
            canvas.restore_region(self.background)
            # Redraw the animated artists
            self.ax.draw_artist(self.rect)
            self.ax.draw_artist(self.min_text)
            self.ax.draw_artist(self.max_text)
            self.ax.draw_artist(self.phase_text)
            # PERFORMANCE: Always draw handles since they're always visible
            self.ax.draw_artist(self.top_handle)
            self.ax.draw_artist(self.bottom_handle)
            if self.drag_phase_text.get_visible():
                self.ax.draw_artist(self.drag_phase_text)
            # Blit the changes
            canvas.blit(self.ax.bbox)
        else:
            self.ax.figure.canvas.draw_idle()
    
    def on_release(self, event):
        """Handle mouse release event."""
        if self.dragging is not None:
            self.dragging = None
            self.rect.set_edgecolor(self.edgecolor)
            # Hide phase indicator
            self.drag_phase_text.set_visible(False)
            # PERFORMANCE: Handles remain visible (no more hide/show)
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
        
        # Update text labels positioned outside grab handle areas
        handle_width = 3  # Same width as used in initialization
        handle_height = 0.15  # Same height as used in initialization
        handle_offset = 0.03  # Match handle offset
        label_buffer = 0.02  # Additional buffer for readability
        
        # Convert to display units if needed
        display_min = self._get_display_value(self.min_val)
        display_max = self._get_display_value(self.max_val)
        
        self.min_text.set_text(f'{display_min:.3f}')
        self.min_text.set_position((self.phase, self.min_val - handle_height - handle_offset - label_buffer))
        self.max_text.set_text(f'{display_max:.3f}')
        self.max_text.set_position((self.phase, self.max_val + handle_offset + handle_height + label_buffer))
        
        # Update rectangular handle positions with slight offset from box edges
        # Top handle: positioned above the validation box with offset
        self.top_handle.set_x(self.phase - handle_width/2)
        self.top_handle.set_y(self.max_val + handle_offset)
        
        # Bottom handle: positioned below the validation box with offset
        self.bottom_handle.set_x(self.phase - handle_width/2) 
        self.bottom_handle.set_y(self.min_val - handle_height - handle_offset)
        
        # Update hover zone position
        self._update_conversion_cache()  # Ensure cache is current
        hover_extend_data = self._hover_extend_data
        self.hover_zone.set_y(self.min_val - hover_extend_data)
        self.hover_zone.set_height((self.max_val - self.min_val) + 2 * hover_extend_data)
    
    def remove(self):
        """Remove the box from the plot."""
        try:
            # Properly unregister all artists from matplotlib
            # Note: ax.patches and ax.texts don't have a remove() method,
            # but calling artist.remove() handles everything properly
            self.rect.remove()
            self.min_text.remove()
            self.max_text.remove()
            self.phase_text.remove()
            
            if hasattr(self, 'drag_phase_text'):
                self.drag_phase_text.remove()
            
            # Remove resize handles and hover zone
            self.top_handle.remove()
            self.bottom_handle.remove()
            self.hover_zone.remove()
        except:
            pass  # Ignore if already removed
        
        # Disconnect events
        try:
            self.ax.figure.canvas.mpl_disconnect(self.cidpress)
            self.ax.figure.canvas.mpl_disconnect(self.cidrelease)
            self.ax.figure.canvas.mpl_disconnect(self.cidmotion)
            # NOTE: cidhover removed for performance optimization
        except:
            pass


class InteractiveValidationTuner:
    """
    Main GUI application for interactive validation range tuning.
    """
    
    def __init__(self):
        """Initialize the interactive validation tuner."""
        self.validation_data = {}  # For GUI display (ipsi only)
        self.full_validation_data = {}  # For validation (ipsi + contra)
        self.original_validation_data = {}  # Immutable copy of loaded YAML (ipsi only)
        self.original_full_validation_data = {}  # Immutable copy including contra values
        self.config_manager = None  # Will be initialized when loading ranges
        self.dataset_path = None
        self.locomotion_data = None
        self.current_task = None
        self.draggable_boxes = []
        self.data_cache = {}
        self.modified = False
        
        # PERFORMANCE: Shared background cache for all draggable boxes
        self._shared_background = None
        self._shared_background_invalid = True
        
        # Setup the GUI
        self.setup_gui()
        
        # Auto-load default files
        self.auto_load_defaults()
    
    def invalidate_all_backgrounds(self):
        """Invalidate background cache for all draggable boxes when plot changes."""
        self._shared_background_invalid = True
        self._shared_background = None
        for box in self.draggable_boxes:
            box.invalidate_background()
    
    def prepare_all_backgrounds(self):
        """PERFORMANCE: Eagerly prepare all draggable box backgrounds after plot updates.
        
        This moves the expensive canvas.draw() operation from click time (jarring)
        to plot update time (expected). Eliminates 500ms drag/resize initiation delay.
        """
        if not self.draggable_boxes:
            return
        
        # Update status to show we're preparing
        if hasattr(self, 'status_bar'):
            self.status_bar.config(text="Preparing interactive elements...")
        
        # Get canvas from any draggable box (they share the same figure)
        canvas = self.draggable_boxes[0].ax.figure.canvas
        
        # One expensive draw operation for all boxes
        canvas.draw()
        
        # Prepare background for each draggable box
        for box in self.draggable_boxes:
            box.background = canvas.copy_from_bbox(box.ax.bbox)
            box.background_invalid = False
        
        # Update status to show we're ready
        if hasattr(self, 'status_bar'):
            self.status_bar.config(text="Ready for interaction - all drags/resizes are now instant")
        
        print(f"Prepared backgrounds for {len(self.draggable_boxes)} interactive elements")
        
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
        
        # Bind window resize with debouncing
        self.resize_timer = None
        self.last_window_size = None
        self.root.bind('<Configure>', self.on_window_configure)
        
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
        
        # Display info label
        self.info_label = ttk.Label(toolbar_frame, text="Displaying all features (kinematic + kinetic + segment angles)")
        self.info_label.pack(side=tk.LEFT, padx=20)
        
        # Buttons
        
        # Validate button (disabled by default)
        self.validate_button = ttk.Button(toolbar_frame, text="Validate", command=self.run_validation_update, state='disabled')
        self.validate_button.pack(side=tk.LEFT, padx=5)

        # Reset all button with warning prompt
        self.reset_all_button = ttk.Button(
            toolbar_frame,
            text="Reset All",
            command=self.on_reset_all_clicked
        )
        self.reset_all_button.pack(side=tk.LEFT, padx=5)

        # Checkbox to show locally passing strides
        self.show_local_passing_var = tk.BooleanVar(value=False)
        self.show_local_checkbox = ttk.Checkbutton(
            toolbar_frame, 
            text="Show Locally Passing (Yellow)",
            variable=self.show_local_passing_var,
            command=self.on_show_local_toggle
        )
        self.show_local_checkbox.pack(side=tk.LEFT, padx=10)
        
        # Checkbox to toggle between radians and degrees
        self.show_degrees_var = tk.BooleanVar(value=False)
        self.show_degrees_checkbox = ttk.Checkbutton(
            toolbar_frame,
            text="Show in Degrees",
            variable=self.show_degrees_var,
            command=self.on_degrees_toggle
        )
        self.show_degrees_checkbox.pack(side=tk.LEFT, padx=10)
        
        # Create scrollable matplotlib figure frame
        self.create_scrollable_plot_area()
        
        # Status bar
        self.status_bar = ttk.Label(self.root, text="Ready. Load validation ranges and dataset to begin.", 
                                   relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Initialize empty plot
        self.create_empty_plot()
    
    def auto_load_defaults(self):
        """Auto-load default validation ranges only. No dataset auto-loading."""
        # Load default validation ranges
        default_ranges_path = project_root / "contributor_tools" / "validation_ranges" / "default_ranges.yaml"
        if default_ranges_path.exists():
            try:
                # Use ValidationConfigManager for consistency
                self.config_manager = ValidationConfigManager(default_ranges_path)
                
                # Extract validation data
                self.validation_data = {}  # For display (ipsi only)
                self.full_validation_data = {}  # For validation (ipsi + contra)
                self.original_validation_data = {}
                self.original_full_validation_data = {}
                
                for task_name in self.config_manager.get_tasks():
                    # Get full data with generated contra features
                    full_task_data = self.config_manager.get_task_data(task_name)
                    self.full_validation_data[task_name] = full_task_data
                    
                    # Filter to ipsi-only for GUI display
                    self.validation_data[task_name] = {}
                    for phase, variables in full_task_data.items():
                        ipsi_vars = {k: v for k, v in variables.items() if '_contra' not in k}
                        if ipsi_vars:  # Only add phase if it has ipsi variables
                            self.validation_data[task_name][phase] = ipsi_vars

                    # Capture immutable originals for future resets
                    self.original_full_validation_data[task_name] = copy.deepcopy(full_task_data)
                    self.original_validation_data[task_name] = copy.deepcopy(self.validation_data[task_name])
                
                # Update task dropdown
                tasks = list(self.validation_data.keys())
                self.task_dropdown['values'] = tasks
                if tasks:
                    self.task_dropdown.set(tasks[0])
                    self.current_task = tasks[0]
                
                self.status_bar.config(text=f"Loaded default validation ranges. Load dataset via File menu.")
                self.modified = False
            except Exception as e:
                print(f"Could not load default ranges: {e}")
                self.status_bar.config(text="Ready. Load validation ranges and dataset to begin.")
        else:
            self.status_bar.config(text="Ready. Load validation ranges and dataset to begin.")
    
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
    
    def on_window_configure(self, event):
        """Handle window configuration changes (resize, move, etc.)."""
        if event.widget == self.root:
            current_size = (self.root.winfo_width(), self.root.winfo_height())
            
            # Check if size actually changed (not just a move)
            if current_size != self.last_window_size:
                self.last_window_size = current_size
                
                # Cancel any active drags
                if hasattr(self, 'draggable_boxes'):
                    for box in self.draggable_boxes:
                        if box.dragging is not None:
                            box.dragging = None
                            box.rect.set_edgecolor(box.edgecolor)
                            box.drag_phase_text.set_visible(False)
                            # Mark background as invalid
                            box.background_invalid = True
                
                # Cancel previous timer if exists
                if self.resize_timer:
                    self.root.after_cancel(self.resize_timer)
                
                # Set new timer - cache backgrounds 500ms after resize stops
                self.resize_timer = self.root.after(500, self.on_resize_complete)
    
    def on_resize_complete(self):
        """Called after window resize has completed (debounced)."""
        self.resize_timer = None
        
        # Only re-cache if we have draggable boxes
        if not hasattr(self, 'draggable_boxes') or not self.draggable_boxes:
            return
        
        # Re-cache backgrounds for all boxes
        self._recache_backgrounds_after_resize()
    
    def _recache_backgrounds_after_resize(self):
        """Re-cache clean backgrounds after window resize."""
        if not hasattr(self, 'canvas'):
            return
        
        print("Re-caching backgrounds after window resize...")
        
        # Hide all boxes temporarily
        for box in self.draggable_boxes:
            box.rect.set_visible(False)
            box.top_handle.set_visible(False)
            box.bottom_handle.set_visible(False)
            box.min_text.set_visible(False)
            box.max_text.set_visible(False)
            box.phase_text.set_visible(False)
        
        # Draw canvas with boxes hidden to get clean backgrounds
        self.canvas.draw()
        
        # Cache background for each box
        for box in self.draggable_boxes:
            box.background = self.canvas.copy_from_bbox(box.ax.bbox)
            box.background_invalid = False
        
        # Restore visibility
        for box in self.draggable_boxes:
            box.rect.set_visible(True)
            box.top_handle.set_visible(True)
            box.bottom_handle.set_visible(True)
            box.min_text.set_visible(True)
            box.max_text.set_visible(True)
            box.phase_text.set_visible(True)
        
        # Final draw to show boxes again
        self.canvas.draw_idle()
        
        print(f"Re-cached backgrounds for {len(self.draggable_boxes)} boxes")
    
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
        
        self.fig = Figure(figsize=(fig_width, fig_height), dpi=dpi)
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
    
    def _convert_numpy_to_python(self, obj):
        """Recursively convert numpy types to Python native types."""
        import numpy as np
        
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.integer, np.signedinteger, np.unsignedinteger)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.complexfloating)):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, dict):
            return {key: self._convert_numpy_to_python(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_to_python(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(self._convert_numpy_to_python(item) for item in obj)
        else:
            return obj
    
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
            # Use ValidationConfigManager for consistency
            self.config_manager = ValidationConfigManager(Path(file_path))

            # Extract validation data
            self.validation_data = {}  # For display (ipsi only)
            self.full_validation_data = {}  # For validation (ipsi + contra)
            self.original_validation_data = {}
            self.original_full_validation_data = {}
            
            for task_name in self.config_manager.get_tasks():
                # Get full data with generated contra features
                full_task_data = self.config_manager.get_task_data(task_name)
                self.full_validation_data[task_name] = full_task_data
                
                # Filter to ipsi-only for GUI display
                self.validation_data[task_name] = {}
                for phase, variables in full_task_data.items():
                    ipsi_vars = {k: v for k, v in variables.items() if '_contra' not in k}
                    if ipsi_vars:  # Only add phase if it has ipsi variables
                        self.validation_data[task_name][phase] = ipsi_vars

                # Capture immutable originals for future resets
                self.original_full_validation_data[task_name] = copy.deepcopy(full_task_data)
                self.original_validation_data[task_name] = copy.deepcopy(self.validation_data[task_name])
            
            # Update task dropdown
            tasks = list(self.validation_data.keys())
            self.task_dropdown['values'] = tasks
            if tasks:
                self.task_dropdown.set(tasks[0])
                self.current_task = tasks[0]
            
            self.status_bar.config(text=f"Loaded validation ranges from: {Path(file_path).name}")
            self.modified = False
            
            # Update plot if dataset is loaded
            if self.locomotion_data is not None and self.current_task:
                # Use the 4-step validation process to ensure proper display
                self.run_validation_update()
            
        except Exception as e:
            import traceback
            error_msg = f"Failed to load validation ranges: {str(e)}"
            print(f"ERROR: {error_msg}")
            print("Full traceback:")
            traceback.print_exc()
            messagebox.showerror("Error", f"{error_msg}\n\nCheck terminal for full traceback.")
    
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
                    # Try with 'phase_ipsi' column
                    self.locomotion_data = LocomotionData(
                        str(self.dataset_path),
                        phase_col='phase_ipsi'
                    )
                else:
                    raise e
            
            # Clear data cache
            self.data_cache = {}
            
            # Update task dropdown to include all dataset tasks
            self.update_task_dropdown_from_dataset()
            
            self.status_bar.config(text=f"Loaded dataset: {self.dataset_path.name}")
            
            # Update plot if we have a current task (even without validation ranges)
            if self.current_task:
                # Run validation with 4-step process for proper display
                self.run_validation_update()
            
        except Exception as e:
            print(f"ERROR: Failed to load dataset: {str(e)}")
            messagebox.showerror("Error", f"Failed to load dataset:\n{str(e)}")
    
    def update_task_dropdown_from_dataset(self):
        """Update task dropdown based on tasks available in the dataset."""
        if not self.locomotion_data:
            return
        
        try:
            # Get tasks from dataset
            dataset_tasks = self.locomotion_data.get_tasks()
            
            # Combine with tasks from validation data (if any)
            # This allows users to see both dataset tasks and any pre-defined validation tasks
            all_tasks = list(set(dataset_tasks) | set(self.validation_data.keys()))
            all_tasks.sort()
            
            # Update dropdown
            self.task_dropdown['values'] = all_tasks
            
            # Set selection
            if self.current_task in all_tasks:
                self.task_dropdown.set(self.current_task)
            elif all_tasks:
                self.task_dropdown.set(all_tasks[0])
                self.current_task = all_tasks[0]
            
            # Update status
            dataset_only_tasks = set(dataset_tasks) - set(self.validation_data.keys())
            if dataset_only_tasks:
                print(f"Found {len(dataset_only_tasks)} tasks in dataset without validation ranges: {', '.join(sorted(dataset_only_tasks))}")
            
        except Exception as e:
            print(f"Warning: Could not get tasks from dataset: {e}")
    
    def on_task_changed(self, event=None):
        """Handle task selection change."""
        self.current_task = self.task_var.get()
        if self.current_task and self.locomotion_data:
            # Use the 4-step validation process to ensure proper background caching
            self.run_validation_update()
    
    def on_show_local_toggle(self):
        """Handle toggling of show locally passing checkbox."""
        if self.locomotion_data and self.current_task:
            # Need to redraw traces and recache backgrounds for blitting
            # Use the 4-step algorithm to ensure proper background caching
            self.run_validation_update()
    
    def on_degrees_toggle(self):
        """Handle toggling between radians and degrees display."""
        if self.locomotion_data and self.current_task:
            # Need to redraw everything with new units
            self.run_validation_update()

    def on_reset_all_clicked(self):
        """Prompt user and reset the current task to YAML defaults."""
        if not self.current_task:
            messagebox.showinfo("Reset All", "Select a task before resetting validation ranges.")
            return

        if self.current_task not in self.original_validation_data:
            messagebox.showwarning(
                "Reset All",
                "No YAML defaults are available for the selected task."
            )
            return

        warning_text = (
            "This will discard all unsaved edits for the current task and "
            "restore the validation ranges from the loaded YAML file.\n\n"
            "Do you want to continue?"
        )

        confirm = messagebox.askyesno(
            title="Reset All Validation Ranges",
            message=warning_text,
            icon='warning'
        )

        if not confirm:
            return

        self.reset_current_task_to_original()
    
    def convert_to_display_units(self, value, var_name):
        """Convert value to display units based on checkbox state."""
        if value is None or var_name is None:
            return value
        
        # Only convert radians to degrees if checkbox is checked and variable is in radians
        if self.show_degrees_var.get() and var_name.endswith('_rad'):
            return value * 180 / np.pi
        return value
    
    def convert_from_display_units(self, value, var_name):
        """Convert value from display units back to storage units."""
        if value is None or var_name is None:
            return value
        
        # Only convert degrees to radians if checkbox is checked and variable is in radians
        if self.show_degrees_var.get() and var_name.endswith('_rad'):
            return value * np.pi / 180
        return value
    
    def get_variable_unit(self, var_name):
        """Determine the unit of a variable from its name suffix."""
        if var_name is None:
            return ""
        
        # Check suffixes
        if var_name.endswith('_rad'):
            return 'deg' if self.show_degrees_var.get() else 'rad'
        elif var_name.endswith('_Nm_kg'):
            return 'Nm/kg'
        elif var_name.endswith('_BW'):
            return 'BW'
        elif var_name.endswith('_BW'):
            return 'N/kg'
        elif var_name.endswith('_Nm'):
            return 'Nm'
        elif var_name.endswith('_N'):
            return 'N'
        elif var_name.endswith('_m'):
            return 'm'
        elif var_name.endswith('_deg'):
            return 'deg'
        elif 'moment' in var_name.lower():
            return 'Nm/kg'  # Fallback for moments (now weight-normalized)
        elif 'grf' in var_name.lower():
            return 'N/kg'  # Fallback for GRF (now weight-normalized)
        elif 'angle' in var_name.lower():
            return 'rad'  # Fallback for angles
        else:
            return ''  # No unit or unknown
    
    def get_all_features(self):
        """Get all features to display (kinematic + kinetic + segment) from standard spec - ipsilateral only."""
        # Primary joint angles (sagittal plane) - from standard_spec.md - IPSI ONLY
        kinematic_vars = [
            'hip_flexion_angle_ipsi_rad',
            'knee_flexion_angle_ipsi_rad',
            'ankle_dorsiflexion_angle_ipsi_rad'
        ]
        kinematic_labels = [
            'Hip Flexion Angle (Ipsi)',
            'Knee Flexion Angle (Ipsi)',
            'Ankle Dorsiflexion Angle (Ipsi)'
        ]
        
        # Joint moments (sagittal plane) - from standard_spec.md - IPSI ONLY - Weight normalized
        kinetic_vars = [
            'hip_flexion_moment_ipsi_Nm_kg',
            'knee_flexion_moment_ipsi_Nm_kg',
            'ankle_dorsiflexion_moment_ipsi_Nm_kg'
        ]
        kinetic_labels = [
            'Hip Flexion Moment (Ipsi)',
            'Knee Flexion Moment (Ipsi)',
            'Ankle Dorsiflexion Moment (Ipsi)'
        ]
        
        # Ground Reaction Forces - from standard_spec.md - IPSI ONLY - Weight normalized
        grf_vars = [
            'vertical_grf_ipsi_BW',
            'anterior_grf_ipsi_BW', 
            'lateral_grf_ipsi_BW'
        ]
        grf_labels = [
            'Vertical GRF (BW, Ipsi)',
            'Anterior GRF (BW, Ipsi)', 
            'Lateral GRF (BW, Ipsi)'
        ]
        
        # Center of Pressure - from standard_spec.md - IPSI ONLY
        cop_vars = [
            'cop_anterior_ipsi_m',
            'cop_lateral_ipsi_m',
            'cop_vertical_ipsi_m'
        ]
        cop_labels = [
            'COP Anterior (Ipsi)',
            'COP Lateral (Ipsi)',
            'COP Vertical (Ipsi)'
        ]
        
        # Segment angles (sagittal plane) - from standard_spec.md - IPSI ONLY (plus bilateral segments)
        segment_vars = [
            'pelvis_sagittal_angle_rad',
            'trunk_sagittal_angle_rad',
            'thigh_sagittal_angle_ipsi_rad',
            'shank_sagittal_angle_ipsi_rad',
            'foot_sagittal_angle_ipsi_rad'
        ]
        segment_labels = [
            'Pelvis Sagittal Angle',
            'Trunk Sagittal Angle',
            'Thigh Sagittal Angle (Ipsi)',
            'Shank Sagittal Angle (Ipsi)',
            'Foot Sagittal Angle (Ipsi)'
        ]
        
        # Additional kinematic features (frontal and transverse planes) - optional
        additional_kinematic_vars = [
            'hip_adduction_angle_ipsi_rad',
            'hip_rotation_angle_ipsi_rad',
            'knee_adduction_angle_ipsi_rad',
            'ankle_eversion_angle_ipsi_rad',
            'pelvis_frontal_angle_rad',
            'pelvis_transverse_angle_rad',
            'trunk_frontal_angle_rad',
            'trunk_transverse_angle_rad'
        ]
        additional_kinematic_labels = [
            'Hip Adduction Angle (Ipsi)',
            'Hip Rotation Angle (Ipsi)',
            'Knee Adduction Angle (Ipsi)',
            'Ankle Eversion Angle (Ipsi)',
            'Pelvis Frontal Angle',
            'Pelvis Transverse Angle',
            'Trunk Frontal Angle',
            'Trunk Transverse Angle'
        ]
        
        # Joint angular velocities - from standard_spec.md - IPSI ONLY
        velocity_vars = [
            'hip_flexion_velocity_ipsi_rad_s',
            'knee_flexion_velocity_ipsi_rad_s',
            'ankle_dorsiflexion_velocity_ipsi_rad_s'
        ]
        velocity_labels = [
            'Hip Flexion Velocity (Ipsi)',
            'Knee Flexion Velocity (Ipsi)',
            'Ankle Dorsiflexion Velocity (Ipsi)'
        ]
        
        # Combine primary features (most commonly available)
        # Start with sagittal plane kinematics, kinetics, GRF, COP, and segments
        all_vars = kinematic_vars + kinetic_vars + grf_vars + cop_vars + segment_vars
        all_labels = kinematic_labels + kinetic_labels + grf_labels + cop_labels + segment_labels
        
        # Optionally add velocities and additional planes if needed
        # Uncomment to include:
        # all_vars += velocity_vars + additional_kinematic_vars
        # all_labels += velocity_labels + additional_kinematic_labels
        
        return all_vars, all_labels
    
    def update_plot(self, force_redraw=False):
        """Update the plot with current task and mode using two-column layout."""
        if not self.current_task or self.current_task not in self.validation_data:
            return
        
        # Check if we need a full redraw or can reuse existing plot
        needs_redraw = force_redraw or not hasattr(self, 'axes_pass') or not self.axes_pass
        
        if needs_redraw:
            # Clear existing plot
            self.fig.clear()
            # PERFORMANCE: Invalidate shared background cache when plot is redrawn
            self._shared_background_invalid = True
            self._shared_background = None
            
            # Remove existing draggable boxes
            for box in self.draggable_boxes:
                box.remove()
            self.draggable_boxes = []
        else:
            # Just clear the line collections from existing axes
            for ax_pass, ax_fail in zip(self.axes_pass, self.axes_fail):
                # Remove old line collections
                for coll in ax_pass.collections[:]:
                    coll.remove()
                for coll in ax_fail.collections[:]:
                    coll.remove()
                # Remove old lines
                for line in ax_pass.lines[:]:
                    line.remove()
                for line in ax_fail.lines[:]:
                    line.remove()
        
        # Get all features to display
        variables, variable_labels = self.get_all_features()
        n_vars = len(variables)
        
        # Store current variables for later validation
        self.current_variables = variables
        
        # Use cached validation results if available, otherwise run validation
        if not hasattr(self, 'cached_failing_strides') or force_redraw:
            self.cached_failing_strides = self.run_validation(variables)
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
        
        # Create subplots with 2 columns (pass/fail) only if needed
        if needs_redraw:
            self.axes_pass = []
            self.axes_fail = []
            
            for i in range(n_vars):
                # Create pass and fail axes side by side
                ax_pass = self.fig.add_subplot(n_vars, 2, i*2 + 1)
                ax_fail = self.fig.add_subplot(n_vars, 2, i*2 + 2)
                self.axes_pass.append(ax_pass)
                self.axes_fail.append(ax_fail)
        
        # Process each variable
        for i in range(n_vars):
            ax_pass = self.axes_pass[i]
            ax_fail = self.axes_fail[i]
            
            var_name = variables[i] if i < len(variables) else None
            var_label = variable_labels[i] if i < len(variable_labels) else f"Variable {i}"
            
            # Get y-axis range with expanded margins (30% instead of 10%)
            y_min, y_max = self.get_expanded_y_range(var_name) if var_name else (-1, 1)
            
            # Plot data for PASS column
            passed_count = 0
            local_count = 0
            if self.locomotion_data and var_name:
                result = self.plot_variable_data_pass_fail(
                    ax_pass, var_name, failing_strides.get(var_name, set()), 
                    show_pass=True,
                    show_local_passing=self.show_local_passing_var.get()
                )
                # Handle return value based on whether local passing is shown
                if self.show_local_passing_var.get():
                    passed_count, local_count = result
                else:
                    passed_count = result
            
            # Plot data for FAIL column  
            failed_count = 0
            if self.locomotion_data and var_name:
                failed_count = self.plot_variable_data_pass_fail(
                    ax_fail, var_name, failing_strides.get(var_name, set()),
                    show_pass=False
                )
            
            # Add draggable boxes for validation ranges on BOTH axes (only if redrawing)
            if needs_redraw and var_name and self.current_task in self.validation_data:
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
                                color='lightgreen',  # Light green fill for pass column
                                edgecolor='black',  # Black outline
                                allow_x_drag=True,
                                parent=self
                            )
                            self.draggable_boxes.append(box_pass)
                            
                            # Create draggable box on fail axis (also interactive)
                            box_fail = DraggableBox(
                                ax_fail, phase, var_name, min_val, max_val,
                                callback=self.on_box_changed,  # Add callback for fail side too
                                color='lightcoral',  # Light red fill for fail column
                                edgecolor='black',  # Black outline
                                allow_x_drag=True,  # Allow dragging on fail side as well
                                parent=self
                            )
                            self.draggable_boxes.append(box_fail)
                            
                            # Store bidirectional references for synchronization
                            box_pass.paired_box = box_fail
                            box_fail.paired_box = box_pass  # Bidirectional pairing
            
            # Setup axes
            if self.show_local_passing_var.get() and local_count > 0:
                ax_pass.set_title(f'{var_label} - ✓ Pass ({passed_count} green, {local_count} yellow)', fontsize=9, fontweight='bold')
            else:
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
                
                # Set y-label only on left column with correct units
                if ax == ax_pass:
                    unit = self.get_variable_unit(var_name)
                    if unit:
                        ax.set_ylabel(unit, fontsize=8)
        
        # Add title
        self.fig.suptitle(f'{self.current_task.replace("_", " ").title()} - All Validation Ranges',
                         fontsize=12, fontweight='bold', y=0.99)
        
        # Create/update canvas
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        if hasattr(self, 'canvas'):
            self.canvas.get_tk_widget().destroy()
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas.draw()
        
        # Connect right-click event for context menu
        self.fig.canvas.mpl_connect('button_press_event', self.on_plot_click)
        
        # Update scroll region
        self.plot_frame.update_idletasks()
        self.on_plot_frame_configure()
    
    def run_validation(self, variables):
        """Run validation to determine which strides fail for each variable.
        
        Only validates features that:
        1. Are in the displayed variables list
        2. Actually exist in the dataset
        3. Have validation ranges defined
        
        Returns failing_strides dict and sets self.global_passing_strides
        """
        failing_strides = {}
        all_stride_indices = set()
        features_validated = set()
        
        if not self.locomotion_data or not self.current_task:
            return failing_strides
        
        # Use full validation data (with contra) for validation
        task_data = self.full_validation_data.get(self.current_task, {})
        if not task_data:
            # Fallback to display data if full data not available (shouldn't happen)
            task_data = self.validation_data.get(self.current_task, {})
            if not task_data:
                return failing_strides
        
        # Get all data for this task
        try:
            subjects = self.locomotion_data.get_subjects()
            
            # Get dataset features once
            sample_features = None
            for subject in subjects:
                try:
                    _, sample_features = self.locomotion_data.get_cycles(
                        subject=subject,
                        task=self.current_task,
                        features=None
                    )
                    if sample_features:
                        break
                except:
                    continue
            
            if not sample_features:
                return failing_strides
            
            # Only validate displayed features that exist in dataset
            validated_features = []
            for var_name in variables:
                if var_name in sample_features:
                    # Check if this feature has any validation ranges
                    has_ranges = False
                    for phase_data in task_data.values():
                        if isinstance(phase_data, dict) and var_name in phase_data:
                            has_ranges = True
                            break
                    if has_ranges:
                        validated_features.append(var_name)
                        features_validated.add(var_name)
            
            print(f"\nValidation Summary:")
            print(f"  Total displayed features: {len(variables)}")
            print(f"  Features in dataset: {len([v for v in variables if v in sample_features])}")
            print(f"  Features being validated: {len(validated_features)}")
            if len(validated_features) < len(variables):
                missing = [v for v in variables if v not in sample_features]
                if missing:
                    print(f"  Missing from dataset: {', '.join(missing[:3])}{'...' if len(missing) > 3 else ''}")
            
            # Track stride index globally across subjects
            global_stride_idx = 0
            
            for subject in subjects:
                try:
                    cycles_data, feature_names = self.locomotion_data.get_cycles(
                        subject=subject,
                        task=self.current_task,
                        features=None
                    )
                    
                    if cycles_data.size == 0:
                        continue
                    
                    # Check each stride
                    for stride in range(cycles_data.shape[0]):
                        all_stride_indices.add(global_stride_idx)
                        
                        # Only check features we're actually validating
                        for var_name in validated_features:
                            if var_name not in feature_names:
                                continue
                                
                            if var_name not in failing_strides:
                                failing_strides[var_name] = set()
                            
                            var_idx = feature_names.index(var_name)
                            stride_data = cycles_data[stride, :, var_idx]
                            
                            # Check each phase
                            for phase_str in task_data.keys():
                                if not str(phase_str).isdigit():
                                    continue
                                phase = int(phase_str)
                                
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
                                            failing_strides[var_name].add(global_stride_idx)
                                            break  # This stride fails for this variable
                        
                        global_stride_idx += 1
                        
                except:
                    continue
        except:
            pass
        
        # Calculate global passing strides (those that pass ALL validated features)
        global_failing_strides = set()
        for var_failures in failing_strides.values():
            global_failing_strides.update(var_failures)
        
        # Store the global passing strides
        self.global_passing_strides = all_stride_indices - global_failing_strides
        
        # Store validation stats
        self.validation_stats = {
            'total_strides': len(all_stride_indices),
            'passing_strides': len(self.global_passing_strides),
            'features_validated': len(features_validated),
            'features_displayed': len(variables)
        }
        
        # Print summary
        print(f"  Total strides: {len(all_stride_indices)}")
        if len(all_stride_indices) > 0:
            print(f"  Passing all features: {len(self.global_passing_strides)} ({len(self.global_passing_strides)/len(all_stride_indices)*100:.1f}%)")
        else:
            print(f"  Passing all features: 0 (0.0%)")
        
        return failing_strides
    
    def get_expanded_y_range(self, var_name):
        """Get y-axis range with expanded margins for more dragging space."""
        y_min, y_max = -1, 1  # Default
        
        if not self.current_task or var_name is None:
            return y_min, y_max
        
        # First, try to get actual data range
        cache_key = f"{self.current_task}_{var_name}"
        data_min, data_max = None, None
        
        if cache_key in self.data_cache and len(self.data_cache[cache_key]) > 0:
            data = self.data_cache[cache_key]
            data_min = np.min(data)
            data_max = np.max(data)
        else:
            # Try to load the data if not in cache
            self.load_variable_data(var_name)
            if cache_key in self.data_cache and len(self.data_cache[cache_key]) > 0:
                data = self.data_cache[cache_key]
                data_min = np.min(data)
                data_max = np.max(data)
        
        # If we have actual data, use it as the primary range
        if data_min is not None and data_max is not None and not np.isnan(data_min) and not np.isnan(data_max):
            # Expand range by 50% for more dragging space
            margin = (data_max - data_min) * 0.5
            y_min = data_min - margin
            y_max = data_max + margin
        else:
            # Fall back to validation ranges if no data available
            task_data = self.validation_data.get(self.current_task, {})
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
            
            if all_mins and all_maxs:
                val_min = min(all_mins)
                val_max = max(all_maxs)
                # Expand range by 30% for validation ranges
                margin = (val_max - val_min) * 0.3
                y_min = val_min - margin
                y_max = val_max + margin
        
        # Ensure minimum range for usability
        if (y_max - y_min) < 0.1:
            center = (y_max + y_min) / 2
            y_min = center - 0.5
            y_max = center + 0.5
        
        # Final safety check - never return NaN or Inf
        if np.isnan(y_min) or np.isnan(y_max) or np.isinf(y_min) or np.isinf(y_max):
            y_min, y_max = -1, 1  # Safe fallback
        
        # Convert to display units if showing degrees
        if self.show_degrees_var.get() and var_name.endswith('_rad'):
            y_min = self.convert_to_display_units(y_min, var_name)
            y_max = self.convert_to_display_units(y_max, var_name)
        
        return y_min, y_max
    
    def load_variable_data(self, var_name):
        """Load data for a specific variable into the cache."""
        if not self.locomotion_data or not self.current_task:
            return
        
        cache_key = f"{self.current_task}_{var_name}"
        if cache_key in self.data_cache:
            return  # Already cached
        
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
                    
                    if cycles_data.size > 0 and var_name in feature_names:
                        var_idx = feature_names.index(var_name)
                        all_data.append(cycles_data[:, :, var_idx])
                except:
                    continue
            
            if all_data:
                all_data = np.vstack(all_data)
                self.data_cache[cache_key] = all_data
        except:
            pass
    
    def plot_variable_data_pass_fail(self, ax, var_name, failed_stride_indices, show_pass=True, show_local_passing=False):
        """Plot data for a variable using LineCollection for fast rendering.
        
        For pass column: Shows only strides that pass ALL features (global intersection)
                        Optionally shows locally passing strides in yellow
        For fail column: Shows strides that fail this specific feature
        """
        count = 0
        local_count = 0
        
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
        
        # Plot data if available using LineCollection for speed
        if len(all_data) > 0:
            phase_ipsi = np.linspace(0, 100, 150)
            
            # Get global passing strides if available
            global_passing = getattr(self, 'global_passing_strides', set())
            
            # Collect lines for batch plotting
            if show_pass:
                # For pass column: separate globally passing and locally passing
                global_lines = []
                local_lines = []
                
                for stride_idx, stride in enumerate(all_data):
                    # Convert to display units if needed
                    display_stride = self.convert_to_display_units(stride, var_name)
                    
                    if stride_idx in global_passing:
                        # Globally passing (green)
                        global_lines.append(list(zip(phase_ipsi, display_stride)))
                        count += 1
                    elif show_local_passing and stride_idx not in failed_stride_indices:
                        # Locally passing but not globally (yellow)
                        local_lines.append(list(zip(phase_ipsi, display_stride)))
                        local_count += 1
                
                # Plot globally passing strides in green
                if global_lines:
                    lc = LineCollection(global_lines, colors='green', alpha=0.2, linewidths=0.5, zorder=1)
                    ax.add_collection(lc)
                
                # Plot locally passing strides in yellow (if enabled)
                if local_lines:
                    lc = LineCollection(local_lines, colors='gold', alpha=0.3, linewidths=0.5, zorder=2)
                    ax.add_collection(lc)
                
                # Plot means
                if global_lines:
                    global_pass_strides = [all_data[i] for i in range(len(all_data)) if i in global_passing]
                    mean_pattern = np.mean(global_pass_strides, axis=0)
                    display_mean = self.convert_to_display_units(mean_pattern, var_name)
                    ax.plot(phase_ipsi, display_mean, color='darkgreen', linewidth=2, zorder=5)
                
                if local_lines:
                    local_pass_indices = [i for i in range(len(all_data)) 
                                         if i not in global_passing and i not in failed_stride_indices]
                    local_pass_strides = [all_data[i] for i in local_pass_indices]
                    mean_pattern = np.mean(local_pass_strides, axis=0)
                    display_mean = self.convert_to_display_units(mean_pattern, var_name)
                    ax.plot(phase_ipsi, display_mean, color='darkorange', linewidth=2, zorder=6)
            else:
                # For fail column: show strides that fail this specific feature
                lines = []
                for stride_idx, stride in enumerate(all_data):
                    if stride_idx in failed_stride_indices:
                        # Convert to display units if needed
                        display_stride = self.convert_to_display_units(stride, var_name)
                        lines.append(list(zip(phase_ipsi, display_stride)))
                        count += 1
                
                # Use LineCollection for fast batch plotting
                if lines:
                    lc = LineCollection(lines, colors='red', alpha=0.3, linewidths=0.5, zorder=1)
                    ax.add_collection(lc)
                
                # Plot mean of the displayed strides
                if count > 0:
                    fail_strides = [all_data[i] for i in range(len(all_data)) if i in failed_stride_indices]
                    if fail_strides:
                        mean_pattern = np.mean(fail_strides, axis=0)
                        display_mean = self.convert_to_display_units(mean_pattern, var_name)
                        ax.plot(phase_ipsi, display_mean, color='darkred', linewidth=2, zorder=5)
        
        # Return both counts for title updates
        if show_pass and show_local_passing:
            return count, local_count
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
            phase_ipsi = np.linspace(0, 100, 150)
            for stride in all_data:
                ax.plot(phase_ipsi, stride, color='gray', alpha=0.1, linewidth=0.5, zorder=1)
            
            # Plot mean
            mean_pattern = np.mean(all_data, axis=0)
            ax.plot(phase_ipsi, mean_pattern, color='black', linewidth=2, zorder=5)
    
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
            
            # Also update full validation data (for validation consistency)
            if self.current_task in self.full_validation_data:
                if box.phase not in self.full_validation_data[self.current_task]:
                    self.full_validation_data[self.current_task][box.phase] = {}
                self.full_validation_data[self.current_task][box.phase][box.var_name] = {
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
                # Don't call draw_idle() here - paired box updates happen through blitting
            
            self.modified = True
            self.status_bar.config(text=f"Modified: {box.var_name} at phase {box.phase}% - Press Validate to update")
            
            # Enable validate button
            if hasattr(self, 'validate_button'):
                self.validate_button.config(state='normal')
    
    
    
    def on_plot_click(self, event):
        """Handle right-click events for adding/deleting boxes."""
        print(f"DEBUG: on_plot_click called - button={event.button}, inaxes={event.inaxes is not None}")
        if event.button == 3 and event.inaxes:  # Right-click
            print(f"DEBUG: Processing right-click at ({event.xdata:.1f}, {event.ydata:.1f})")
            # Check if we clicked on a box
            clicked_box = None
            for box in self.draggable_boxes:
                if box.ax == event.inaxes:
                    # Use matplotlib's contains method for more reliable hit detection
                    contains, _ = box.rect.contains(event)
                    if contains:
                        clicked_box = box
                        break
            
            # Create context menu
            menu = tk.Menu(self.root, tearoff=0)
            
            target_var = None

            if clicked_box:
                # Right-clicked on a box - show delete option
                target_var = clicked_box.var_name
                menu.add_command(
                    label=f"Delete box at {clicked_box.phase}%",
                    command=lambda: self.delete_box(clicked_box)
                )
            else:
                # Right-clicked on empty space - show add option
                phase = int(round(event.xdata))
                phase = max(0, min(100, phase))  # Constrain to 0-100

                # Find which variable this axis corresponds to
                var_idx = None
                for i, (ax_pass, ax_fail) in enumerate(zip(self.axes_pass, self.axes_fail)):
                    if event.inaxes == ax_pass or event.inaxes == ax_fail:
                        var_idx = i
                        break

                if var_idx is not None and var_idx < len(self.current_variables):
                    var_name = self.current_variables[var_idx]
                    target_var = var_name
                    click_value = event.ydata
                    menu.add_command(
                        label=f"Add box at {phase}% for {var_name}",
                        command=lambda p=phase, v=var_name, y=click_value: self.add_box(p, v, y)
                    )

            if target_var and self._has_yaml_defaults(target_var):
                if menu.index('end') is not None:
                    menu.add_separator()
                menu.add_command(
                    label=f"Reset {target_var} to YAML defaults",
                    command=lambda var=target_var: self.reset_variable_to_original(var)
                )
            
            # Show menu at cursor position
            try:
                # Convert matplotlib coordinates to tkinter coordinates
                x = self.root.winfo_pointerx()
                y = self.root.winfo_pointery()
                menu.tk_popup(x, y)
            finally:
                menu.grab_release()
    
    def delete_box(self, box):
        """Delete a validation box and its paired box."""
        print(f"Deleting box at phase {box.phase} for {box.var_name}")

        # Remove from validation data
        if (self.current_task in self.validation_data and 
            box.phase in self.validation_data[self.current_task] and
            box.var_name in self.validation_data[self.current_task][box.phase]):
            del self.validation_data[self.current_task][box.phase][box.var_name]
            
            # Clean up empty phase
            if not self.validation_data[self.current_task][box.phase]:
                del self.validation_data[self.current_task][box.phase]
        
        # Step 1: Remove BOTH boxes from the list first
        paired_box = box.paired_box if hasattr(box, 'paired_box') else None
        
        # Disconnect callbacks to prevent re-adding to validation_data
        box.callback = None
        if paired_box:
            paired_box.callback = None
        
        # Clear paired_box references to prevent ghost boxes
        box.paired_box = None
        if paired_box:
            paired_box.paired_box = None
        
        if box in self.draggable_boxes:
            self.draggable_boxes.remove(box)
        
        if paired_box and paired_box in self.draggable_boxes:
            self.draggable_boxes.remove(paired_box)
        
        # Step 2: Call remove() on both to disconnect events and remove from plot
        box.remove()
        if paired_box:
            paired_box.remove()
        
        # Step 3: Now redraw the affected axes with remaining boxes
        if hasattr(self, 'trace_backgrounds') and hasattr(self, 'current_variables'):
            try:
                var_idx = self.current_variables.index(box.var_name)
                
                # Collect axes that need updating
                axes_to_update = []
                
                # Determine which axes need updating and their background keys
                if hasattr(self, 'axes_pass') and box.ax in self.axes_pass:
                    axes_to_update.append((box.ax, f'pass_{var_idx}'))
                elif hasattr(self, 'axes_fail') and box.ax in self.axes_fail:
                    axes_to_update.append((box.ax, f'fail_{var_idx}'))
                
                if paired_box:
                    if hasattr(self, 'axes_pass') and paired_box.ax in self.axes_pass:
                        axes_to_update.append((paired_box.ax, f'pass_{var_idx}'))
                    elif hasattr(self, 'axes_fail') and paired_box.ax in self.axes_fail:
                        axes_to_update.append((paired_box.ax, f'fail_{var_idx}'))
                
                # Update each affected axis
                for ax, bg_key in axes_to_update:
                    bg = self.trace_backgrounds.get(bg_key)
                    if bg:
                        # Restore the clean trace background
                        self.canvas.restore_region(bg)
                        
                        # Redraw ALL remaining boxes on this axis
                        for other_box in self.draggable_boxes:
                            if other_box.ax == ax:
                                ax.draw_artist(other_box.rect)
                                ax.draw_artist(other_box.min_text)
                                ax.draw_artist(other_box.max_text)
                                ax.draw_artist(other_box.phase_text)
                                ax.draw_artist(other_box.top_handle)
                                ax.draw_artist(other_box.bottom_handle)
                        
                        # Blit the changes
                        self.canvas.blit(ax.bbox)
                        
            except (ValueError, IndexError):
                pass  # Variable not found in current_variables
        
        # Update cached backgrounds for all remaining boxes on affected axes
        # They should all use the same trace-only background from self.trace_backgrounds
        if hasattr(self, 'trace_backgrounds') and hasattr(self, 'axes_pass') and hasattr(self, 'axes_fail'):
            affected_axes = set()
            affected_axes.add(box.ax)
            if paired_box:
                affected_axes.add(paired_box.ax)
            
            for ax in affected_axes:
                # Determine which trace background to use
                bg = None
                if ax in self.axes_pass:
                    idx = self.axes_pass.index(ax)
                    bg = self.trace_backgrounds.get(f'pass_{idx}')
                elif ax in self.axes_fail:
                    idx = self.axes_fail.index(ax)
                    bg = self.trace_backgrounds.get(f'fail_{idx}')
                
                # Assign the same trace background to all boxes on this axis
                if bg:
                    for b in self.draggable_boxes:
                        if b.ax == ax:
                            b.background = bg
                            b.background_invalid = False
        
        # Mark as modified
        self.modified = True
        self.validate_button.config(state='normal')
        self.status_bar.config(text=f"Deleted validation box at {box.phase}% for {box.var_name}")

    def _has_yaml_defaults(self, var_name: str) -> bool:
        """Return True if the original YAML contains ranges for the variable."""
        if not self.current_task or not var_name:
            return False

        task_data = self.original_validation_data.get(self.current_task, {})
        for variables in task_data.values():
            if not isinstance(variables, dict):
                continue
            if var_name in variables and isinstance(variables[var_name], dict):
                range_spec = variables[var_name]
                if range_spec.get('min') is not None and range_spec.get('max') is not None:
                    return True
        return False

    def reset_current_task_to_original(self):
        """Reset every variable in the current task to the YAML defaults."""
        if not self.current_task:
            return

        original_task_data = self.original_validation_data.get(self.current_task)
        if not original_task_data:
            if hasattr(self, 'status_bar'):
                self.status_bar.config(text="No YAML defaults available to reset this task.")
            return

        # Restore GUI-facing validation data
        self.validation_data[self.current_task] = copy.deepcopy(original_task_data)

        # Restore full validation data if available, otherwise remove custom overrides
        if self.current_task in self.original_full_validation_data:
            self.full_validation_data[self.current_task] = copy.deepcopy(
                self.original_full_validation_data[self.current_task]
            )
        elif self.current_task in self.full_validation_data:
            del self.full_validation_data[self.current_task]

        # Clear existing draggable boxes to prevent stale visuals when dataset is absent
        for box in self.draggable_boxes:
            try:
                box.remove()
            except Exception:
                pass
        self.draggable_boxes = []

        # Refresh plots if dataset is loaded; otherwise, trigger a light redraw
        if self.locomotion_data:
            self.run_validation_update()
        elif hasattr(self, 'canvas'):
            self.canvas.draw_idle()

        # Mark state and notify user
        self.modified = True
        if hasattr(self, 'validate_button'):
            self.validate_button.config(state='disabled')
        if hasattr(self, 'status_bar'):
            self.status_bar.config(
                text=f"Reset all validation ranges for {self.current_task} to YAML defaults."
            )

    def reset_variable_to_original(self, var_name: str):
        """Reset all validation ranges for a variable to the loaded YAML defaults."""
        if not self.current_task or not var_name:
            return

        original_task_data = self.original_validation_data.get(self.current_task, {})
        if not original_task_data:
            if hasattr(self, 'status_bar'):
                self.status_bar.config(text="No original YAML ranges available for reset.")
            return

        # Collect the original ranges for this variable across all phases
        original_entries = []
        for phase, variables in original_task_data.items():
            if not isinstance(variables, dict):
                continue
            if var_name in variables and isinstance(variables[var_name], dict):
                min_val = variables[var_name].get('min')
                max_val = variables[var_name].get('max')
                if min_val is None or max_val is None:
                    continue
                original_entries.append((phase, copy.deepcopy(variables[var_name])))

        if not original_entries:
            if hasattr(self, 'status_bar'):
                self.status_bar.config(text=f"No YAML defaults found for {var_name}.")
            return

        def _normalize_phase_value(value):
            """Convert phase keys to numeric values for plotting."""
            if isinstance(value, (int, float)):
                return int(round(value)) if isinstance(value, float) else value
            if isinstance(value, str):
                try:
                    return int(value)
                except ValueError:
                    try:
                        return int(float(value))
                    except ValueError:
                        return None
            return None

        # Reset GUI-facing validation data
        task_data = self.validation_data.setdefault(self.current_task, {})
        for phase in list(task_data.keys()):
            if isinstance(task_data[phase], dict) and var_name in task_data[phase]:
                del task_data[phase][var_name]
                if not task_data[phase]:
                    del task_data[phase]

        for phase, range_spec in original_entries:
            if phase not in task_data:
                task_data[phase] = {}
            task_data[phase][var_name] = copy.deepcopy(range_spec)

        # Reset full validation data if available
        full_original = self.original_full_validation_data.get(self.current_task, {})
        full_task_data = self.full_validation_data.setdefault(self.current_task, {})
        for phase in list(full_task_data.keys()):
            if isinstance(full_task_data[phase], dict) and var_name in full_task_data[phase]:
                del full_task_data[phase][var_name]
                if not full_task_data[phase]:
                    del full_task_data[phase]

        for phase, variables in full_original.items():
            if not isinstance(variables, dict):
                continue
            if var_name in variables and isinstance(variables[var_name], dict):
                if phase not in full_task_data:
                    full_task_data[phase] = {}
                full_task_data[phase][var_name] = copy.deepcopy(variables[var_name])

        # Remove existing draggable boxes for this variable
        boxes_to_remove = [box for box in self.draggable_boxes if box.var_name == var_name]
        for box in boxes_to_remove:
            paired_box = getattr(box, 'paired_box', None)
            if paired_box is not None:
                paired_box.paired_box = None
            box.paired_box = None
            box.remove()
            if box in self.draggable_boxes:
                self.draggable_boxes.remove(box)

        # Recreate draggable boxes if the variable is currently displayed
        if hasattr(self, 'current_variables') and var_name in getattr(self, 'current_variables', []):
            try:
                var_idx = self.current_variables.index(var_name)
                ax_pass = self.axes_pass[var_idx]
                ax_fail = self.axes_fail[var_idx]

                for phase, range_spec in original_entries:
                    min_val = range_spec.get('min')
                    max_val = range_spec.get('max')
                    if min_val is None or max_val is None:
                        continue

                    normalized_phase = _normalize_phase_value(phase)
                    if normalized_phase is None:
                        continue

                    box_pass = DraggableBox(
                        ax_pass, normalized_phase,
                        var_name, min_val, max_val,
                        callback=self.on_box_changed,
                        color='lightgreen',
                        edgecolor='black',
                        allow_x_drag=True,
                        parent=self
                    )
                    box_fail = DraggableBox(
                        ax_fail, normalized_phase,
                        var_name, min_val, max_val,
                        callback=self.on_box_changed,
                        color='lightcoral',
                        edgecolor='black',
                        allow_x_drag=True,
                        parent=self
                    )

                    box_pass.paired_box = box_fail
                    box_fail.paired_box = box_pass

                    if hasattr(self, 'trace_backgrounds'):
                        pass_bg = self.trace_backgrounds.get(f'pass_{var_idx}')
                        fail_bg = self.trace_backgrounds.get(f'fail_{var_idx}')
                        if pass_bg is not None and fail_bg is not None:
                            box_pass.background = pass_bg
                            box_pass.background_invalid = False
                            box_fail.background = fail_bg
                            box_fail.background_invalid = False

                    self.draggable_boxes.extend([box_pass, box_fail])

                if hasattr(self, 'canvas'):
                    self.canvas.draw_idle()
            except (ValueError, IndexError):
                # Variable not currently plotted; data already reset
                pass

        self.modified = True
        if hasattr(self, 'validate_button'):
            self.validate_button.config(state='normal')
        if hasattr(self, 'status_bar'):
            self.status_bar.config(text=f"Reset {var_name} to YAML defaults for {self.current_task}.")

    def add_box(self, phase, var_name, click_value):
        """Add a new validation box at the specified phase."""
        # Create default range around click position
        range_size = 0.4  # Default range size - larger for easier manipulation
        min_val = click_value - range_size/2
        max_val = click_value + range_size/2
        
        # Add to validation data
        if self.current_task not in self.validation_data:
            self.validation_data[self.current_task] = {}
        if phase not in self.validation_data[self.current_task]:
            self.validation_data[self.current_task][phase] = {}
        
        self.validation_data[self.current_task][phase][var_name] = {
            'min': min_val,
            'max': max_val
        }
        
        # Find the axes for this variable
        var_idx = self.current_variables.index(var_name)
        ax_pass = self.axes_pass[var_idx]
        ax_fail = self.axes_fail[var_idx]
        
        # Create draggable boxes on both axes directly for immediate responsiveness
        box_pass = DraggableBox(
            ax_pass, phase, var_name, min_val, max_val,
            callback=self.on_box_changed,
            color='lightgreen',  # Light green fill for pass column
            edgecolor='black',  # Black outline
            allow_x_drag=True,
            parent=self
        )
        self.draggable_boxes.append(box_pass)
        
        box_fail = DraggableBox(
            ax_fail, phase, var_name, min_val, max_val,
            callback=self.on_box_changed,
            color='lightcoral',  # Light red fill for fail column
            edgecolor='black',  # Black outline
            allow_x_drag=True,
            parent=self
        )
        self.draggable_boxes.append(box_fail)
        
        # Pair the boxes
        box_pass.paired_box = box_fail
        box_fail.paired_box = box_pass
        
        # Assign cached trace backgrounds to new boxes for proper blitting
        if hasattr(self, 'trace_backgrounds'):
            pass_bg = self.trace_backgrounds.get(f'pass_{var_idx}')
            fail_bg = self.trace_backgrounds.get(f'fail_{var_idx}')
            
            if pass_bg is not None and fail_bg is not None:
                box_pass.background = pass_bg
                box_fail.background = fail_bg
                box_pass.background_invalid = False
                box_fail.background_invalid = False
                print(f"Assigned cached backgrounds to new boxes for {var_name}")
            else:
                print(f"WARNING: Missing cached backgrounds for {var_name}")
        
        # Update canvas without destroying cached backgrounds
        self.canvas.draw_idle()
        
        # Mark as modified
        self.modified = True
        self.validate_button.config(state='normal')
        self.status_bar.config(text=f"Added validation box at {phase}% for {var_name}")
    
    def _get_summary_title(self):
        """Generate comprehensive summary title with validation stats."""
        # Main title components
        task_title = self.current_task.replace("_", " ").title() if self.current_task else "No Task"
        dataset_name = self.dataset_path.name if hasattr(self, 'dataset_path') else "No Dataset"
        
        # Stats line (if validation has been run)
        if hasattr(self, 'validation_stats'):
            stats = self.validation_stats
            pass_pct = stats['passing_strides']/stats['total_strides']*100 if stats['total_strides'] > 0 else 0
            stats_line = (f"\n{stats['total_strides']} strides | "
                         f"{stats['features_validated']}/{stats['features_displayed']} features validated | "
                         f"{stats['passing_strides']} passing ({pass_pct:.1f}%)")
        else:
            stats_line = "\nNo validation run yet - click Validate to analyze"
        
        return f"{task_title} - {dataset_name}{stats_line}"
    
    def run_validation_update(self):
        """Run validation using the 4-step algorithm for optimal performance.
        
        Steps:
        1. Run validation
        2. Draw traces without boxes
        3. Cache clean trace backgrounds
        4. Add boxes back for interaction
        """
        if not self.locomotion_data:
            return
        
        # Ensure current_variables is set for validation (fix validate button issue)
        if not hasattr(self, 'current_variables') or not self.current_variables:
            variables, variable_labels = self.get_all_features()
            self.current_variables = variables
            print(f"Set current_variables for validation: {len(variables)} features")
        
        self.status_bar.config(text="Step 1/4: Running validation...")
        self.root.update()
        
        # Step 1: Run validation
        self.cached_failing_strides = self.run_validation(self.current_variables)
        
        self.status_bar.config(text="Step 2/4: Drawing traces...")
        self.root.update()
        
        # Step 2: Draw traces without boxes
        self._draw_traces_only()
        
        self.status_bar.config(text="Step 3/4: Caching backgrounds...")
        self.root.update()
        
        # Step 3: Cache clean trace backgrounds
        self._cache_trace_backgrounds()
        
        self.status_bar.config(text="Step 4/4: Adding interactive elements...")
        self.root.update()
        
        # Step 4: Add boxes back for interaction
        self._add_boxes_for_interaction()
        
        # Force final canvas refresh to ensure display updates
        self.status_bar.config(text="Refreshing display...")
        self.root.update()
        self.canvas.draw_idle()  # Use draw_idle for better performance
        self.canvas.flush_events()  # Ensure all events are processed
        
        # Debug: Verify figure/canvas connection
        print(f"Figure has {len(self.fig.axes)} axes, Canvas figure ID: {id(self.canvas.figure)}, Self figure ID: {id(self.fig)}")
        if id(self.canvas.figure) != id(self.fig):
            print("WARNING: Canvas and self.fig are different objects - display may be blank!")
        
        # Disable validate button
        self.validate_button.config(state='disabled')
        
        # Update status bar with validation stats
        if hasattr(self, 'validation_stats'):
            stats = self.validation_stats
            if stats['total_strides'] > 0:
                pass_pct = stats['passing_strides']/stats['total_strides']*100
            else:
                pass_pct = 0.0
            status_text = (f"Validation complete | {stats['total_strides']} strides | "
                          f"Validating {stats['features_validated']}/{stats['features_displayed']} features | "
                          f"{stats['passing_strides']} pass all ({pass_pct:.1f}%)")
            self.status_bar.config(text=status_text)
        else:
            self.status_bar.config(text="Validation complete.")
        
        # Update scroll region to match new figure size
        self.plot_frame.update_idletasks()
        self.on_plot_frame_configure()
    
    def _draw_traces_only(self):
        """Step 2: Draw traces without draggable boxes."""
        if not self.current_task or self.current_task not in self.validation_data:
            return
        
        # Clear existing plot and remove any existing boxes
        self.fig.clear()
        for box in self.draggable_boxes:
            box.remove()
        self.draggable_boxes = []
        
        # Get all features to display
        variables, variable_labels = self.get_all_features()
        n_vars = len(variables)
        
        # Store current variables for later use
        self.current_variables = variables
        
        # Calculate dynamic figure size
        window_width = self.root.winfo_width() if self.root.winfo_width() > 1 else 1400
        dpi = 100
        fig_width = (window_width - 100) / dpi
        row_height = 2.5
        fig_height = n_vars * row_height + 1
        
        # Reuse existing figure to maintain canvas connection, just resize and clear
        self.fig.set_size_inches(fig_width, fig_height)
        self.fig.clear()  # Clear all existing content but keep figure connected to canvas
        # Ensure constrained_layout is off so subplots_adjust works properly
        self.fig.set_constrained_layout(False)
        self.fig.subplots_adjust(left=0.06, right=0.98, top=0.94, bottom=0.02, hspace=0.25, wspace=0.15)
        
        # Recreate canvas to match new figure size
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        if hasattr(self, 'canvas'):
            self.canvas.get_tk_widget().destroy()
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Create subplots (pass/fail columns)
        self.axes_pass = []
        self.axes_fail = []
        
        for i in range(n_vars):
            ax_pass = self.fig.add_subplot(n_vars, 2, i*2 + 1)
            ax_fail = self.fig.add_subplot(n_vars, 2, i*2 + 2)
            self.axes_pass.append(ax_pass)
            self.axes_fail.append(ax_fail)
        
        # Get failing strides from cached results
        failing_strides = self.cached_failing_strides
        
        # Process each variable - draw traces but NO boxes
        for i in range(n_vars):
            ax_pass = self.axes_pass[i]
            ax_fail = self.axes_fail[i]
            
            var_name = variables[i] if i < len(variables) else None
            var_label = variable_labels[i] if i < len(variable_labels) else f"Variable {i}"
            
            # Get y-axis range
            y_min, y_max = self.get_expanded_y_range(var_name) if var_name else (-1, 1)
            
            # Plot data for PASS column
            passed_count = 0
            local_count = 0
            if self.locomotion_data and var_name:
                result = self.plot_variable_data_pass_fail(
                    ax_pass, var_name, failing_strides.get(var_name, set()), 
                    show_pass=True,
                    show_local_passing=self.show_local_passing_var.get()
                )
                # Handle return value based on whether local passing is shown
                if self.show_local_passing_var.get():
                    passed_count, local_count = result
                else:
                    passed_count = result
            
            # Plot data for FAIL column
            failed_count = 0
            if self.locomotion_data and var_name:
                failed_count = self.plot_variable_data_pass_fail(
                    ax_fail, var_name, failing_strides.get(var_name, set()),
                    show_pass=False
                )
            
            # Setup axes (but NO draggable boxes!)
            if self.show_local_passing_var.get() and local_count > 0:
                ax_pass.set_title(f'{var_label} - ✓ Pass ({passed_count} green, {local_count} yellow)', fontsize=9, fontweight='bold')
            else:
                ax_pass.set_title(f'{var_label} - ✓ Pass ({passed_count})', fontsize=9, fontweight='bold')
            ax_fail.set_title(f'{var_label} - ✗ Fail ({failed_count})', fontsize=9, fontweight='bold')
            
            for ax in [ax_pass, ax_fail]:
                ax.set_xlim(-5, 105)
                ax.set_ylim(y_min, y_max)
                ax.set_xticks([0, 25, 50, 75, 100])
                ax.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
                ax.grid(True, alpha=0.3)
                ax.set_xlabel('Phase (%)' if i == n_vars - 1 else '')
                
                # Set y-label only on left column with correct units
                if ax == ax_pass:
                    unit = self.get_variable_unit(var_name)
                    if unit:
                        ax.set_ylabel(unit, fontsize=8)
        
        # Add comprehensive title with stats
        self.fig.suptitle(self._get_summary_title(), 
                          fontsize=11, fontweight='bold', y=0.99)
        
        # Update canvas to show traces
        self.canvas.draw()
    
    def _cache_trace_backgrounds(self):
        """Step 3: Cache clean trace backgrounds for each axis."""
        if not hasattr(self, 'axes_pass') or not hasattr(self, 'axes_fail'):
            return
        
        # Ensure canvas is fully drawn with just traces
        self.canvas.draw()
        
        # Cache background for each axis pair
        self.trace_backgrounds = {}
        
        for i, (ax_pass, ax_fail) in enumerate(zip(self.axes_pass, self.axes_fail)):
            # Cache background for pass axis
            self.trace_backgrounds[f'pass_{i}'] = self.canvas.copy_from_bbox(ax_pass.bbox)
            
            # Cache background for fail axis  
            self.trace_backgrounds[f'fail_{i}'] = self.canvas.copy_from_bbox(ax_fail.bbox)
        
        print(f"Cached trace backgrounds for {len(self.axes_pass)} axis pairs")
    
    def _add_boxes_for_interaction(self):
        """Step 4: Add draggable boxes back over the cached trace backgrounds."""
        if not hasattr(self, 'axes_pass') or not hasattr(self, 'axes_fail'):
            return
        
        if not hasattr(self, 'current_variables') or not self.current_variables:
            return
        
        # Clear any existing boxes
        for box in self.draggable_boxes:
            box.remove()
        self.draggable_boxes = []
        
        # Add draggable boxes for each variable
        variables = self.current_variables
        
        for i in range(len(variables)):
            var_name = variables[i]
            ax_pass = self.axes_pass[i]
            ax_fail = self.axes_fail[i]
            
            # Create boxes only if validation data exists for this variable
            if self.current_task in self.validation_data:
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
                            
                            # Create draggable box on pass axis (thin black rectangle)
                            box_pass = DraggableBox(
                                ax_pass, phase, var_name, min_val, max_val,
                                callback=self.on_box_changed,
                                color='lightgreen',  # Light green fill for pass column
                                edgecolor='black',  # Black outline
                                allow_x_drag=True,
                                parent=self
                            )
                            self.draggable_boxes.append(box_pass)
                            
                            # Create draggable box on fail axis (light red rectangle)
                            box_fail = DraggableBox(
                                ax_fail, phase, var_name, min_val, max_val,
                                callback=self.on_box_changed,
                                color='lightcoral',  # Light red fill for fail column
                                edgecolor='black',  # Black outline
                                allow_x_drag=True,
                                parent=self
                            )
                            self.draggable_boxes.append(box_fail)
                            
                            # Store bidirectional references for synchronization
                            box_pass.paired_box = box_fail
                            box_fail.paired_box = box_pass
                            
                            # Use cached trace backgrounds for instant blitting
                            if hasattr(self, 'trace_backgrounds'):
                                pass_bg = self.trace_backgrounds.get(f'pass_{i}')
                                fail_bg = self.trace_backgrounds.get(f'fail_{i}')
                                
                                if pass_bg is not None and fail_bg is not None:
                                    box_pass.background = pass_bg
                                    box_fail.background = fail_bg
                                    box_pass.background_invalid = False
                                    box_fail.background_invalid = False
                                    print(f"Assigned cached backgrounds to boxes for axis {i}")
                                else:
                                    print(f"WARNING: Missing cached backgrounds for axis {i} (pass={pass_bg is not None}, fail={fail_bg is not None})")
                            else:
                                print("WARNING: No trace_backgrounds attribute found")
        
        # Update canvas to show boxes
        self.canvas.draw()
        
        # Reconnect right-click handler AFTER draggable boxes to ensure it processes events last
        if hasattr(self, 'cid_plot_click'):
            self.fig.canvas.mpl_disconnect(self.cid_plot_click)
        self.cid_plot_click = self.fig.canvas.mpl_connect('button_press_event', self.on_plot_click)
        print(f"DEBUG: Reconnected right-click handler after creating {len(self.draggable_boxes)} boxes")
        
        # Verify that boxes are using clean trace backgrounds (no re-caching needed!)
        print(f"Added {len(self.draggable_boxes)} interactive boxes using clean trace backgrounds")
    
    def setup_plot_infrastructure(self):
        """Setup GUI infrastructure (figure sizing, canvas integration, subplots) without data plotting."""
        if not self.current_task or self.current_task not in self.validation_data:
            return
        
        # Get variables to determine plot structure
        variables, variable_labels = self.get_all_features()
        n_vars = len(variables)
        
        # Store current variables for later use
        self.current_variables = variables
        
        # Remove existing draggable boxes
        if hasattr(self, 'draggable_boxes'):
            for box in self.draggable_boxes:
                box.remove()
            self.draggable_boxes = []
        
        # Calculate dynamic figure height based on number of variables
        window_width = self.root.winfo_width() if self.root.winfo_width() > 1 else 1400
        dpi = 100
        fig_width = (window_width - 100) / dpi
        
        # Height per subplot row (in inches)
        row_height = 2.5  # Increased for better dragging space
        fig_height = n_vars * row_height + 1  # Add space for title
        
        # Create new figure with dynamic size (like original update_plot())
        from matplotlib.figure import Figure
        self.fig = Figure(figsize=(fig_width, fig_height), dpi=dpi)
        self.fig.subplots_adjust(left=0.06, right=0.98, top=0.94, bottom=0.02, hspace=0.25, wspace=0.15)
        
        # Create subplots (pass/fail columns)
        self.axes_pass = []
        self.axes_fail = []
        
        for i in range(n_vars):
            ax_pass = self.fig.add_subplot(n_vars, 2, i*2 + 1)
            ax_fail = self.fig.add_subplot(n_vars, 2, i*2 + 2)
            self.axes_pass.append(ax_pass)
            self.axes_fail.append(ax_fail)
        
        # CRITICAL: Canvas widget recreation (missing from original implementation)
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        if hasattr(self, 'canvas'):
            self.canvas.get_tk_widget().destroy()
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Add initial title (will be updated with stats after validation)
        self.fig.suptitle(self._get_summary_title(),
                          fontsize=11, fontweight='bold', y=0.99)
        
        # Connect right-click event for context menu
        self.cid_plot_click = self.fig.canvas.mpl_connect('button_press_event', self.on_plot_click)
        
        # Update scroll region (essential for proper scrolling)
        self.plot_frame.update_idletasks()
        self.on_plot_frame_configure()
        
        print(f"Setup plot infrastructure: {n_vars} variables, {len(self.axes_pass)} axis pairs")
    
    def initialize_validation_display(self):
        """Complete startup initialization: GUI setup + 4-step validation algorithm."""
        if not self.validation_data or not self.current_task:
            return
        
        self.status_bar.config(text="Initializing validation display...")
        self.root.update()
        
        # Step 1: Setup GUI infrastructure (figure sizing, subplots, scrolling)
        self.setup_plot_infrastructure()
        
        # Step 2: Run the proven 4-step validation algorithm
        self.run_validation_update()
        
        # Update final status
        self.status_bar.config(text="Validation display initialized and ready")
    
    def update_stride_colors(self):
        """Update stride colors by forcing a complete redraw."""
        # The incremental update approach doesn't work well with blitting optimizations
        # Force a complete redraw instead
        self.update_plot(force_redraw=True)
    
    
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
            # Create config manager and set data
            config_manager = ValidationConfigManager()
            
            # Convert numpy types to Python native types and ensure integer phases
            clean_data = {}
            for task_name, task_data in self.validation_data.items():
                clean_data[task_name] = {}
                for phase, variables in task_data.items():
                    # Ensure phase is an integer
                    phase = int(phase) if not isinstance(phase, int) else phase
                    clean_data[task_name][phase] = self._convert_numpy_to_python(variables)
            
            # Set data and metadata
            config_manager.set_data(clean_data)
            config_manager.set_metadata('source', 'Interactive Validation Tuner')
            config_manager.set_metadata('description', 'Interactively tuned validation ranges for all features')
            
            # Save to file
            config_manager.save(Path(file_path))
            
            self.modified = False
            self.status_bar.config(text=f"Saved validation ranges to: {Path(file_path).name}")
            messagebox.showinfo("Success", f"Validation ranges saved to:\n{Path(file_path).name}")
            
        except Exception as e:
            print(f"ERROR: Failed to save validation ranges: {str(e)}")
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
        print("\nAlternatively, you can use the command-line tool:")
        print("  - create_validation_range_plots.py for static plots")
        return 1
    
    app = InteractiveValidationTuner()
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
