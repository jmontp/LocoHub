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
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd
import yaml

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
from matplotlib.ticker import FuncFormatter, FixedLocator
from matplotlib.collections import LineCollection
import matplotlib.animation as animation

# Ensure repository root and src/ are importable so `import locohub` works
project_root = Path(__file__).parent.parent
src_dir = project_root / "src"
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if src_dir.exists() and str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Import existing modules
from locohub import LocomotionData
from locohub.feature_constants import get_feature_list
from internal.config_management.config_manager import ValidationConfigManager
from internal.validation_engine.validator import Validator
from internal.config_management import task_registry
from internal.plot_generation.filters_by_phase_plots import get_task_classification


class DraggableBox:
    """
    A draggable validation range box that can be interactively adjusted.
    Optimized with blitting for fast dragging performance.
    """
    HANDLE_WIDTH_DATA = 3  # Width stays in phase space units
    HANDLE_HEIGHT_PIXELS = 18  # Consistent on-screen handle height
    HANDLE_OFFSET_PIXELS = 6   # Gap between box edge and handle
    LABEL_BUFFER_PIXELS = 4    # Space for numeric labels

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
        self.handle_width = self.HANDLE_WIDTH_DATA
        self.allow_x_drag = allow_x_drag
        self.parent = parent  # Store parent reference for unit conversion
        self.display_unit = ''
        if self.parent is not None:
            self.display_unit = self.parent.get_display_unit(var_name)

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

        # Pixel->data conversions for handle geometry
        self._handle_height = 0.0
        self._handle_offset = 0.0
        self._label_buffer = 0.0
        self._update_handle_metrics()

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

        # Add text labels positioned outside grab handle areas
        # Convert to display units if needed
        display_min = self._get_display_value(min_val)
        display_max = self._get_display_value(max_val)

        self.min_text = self.ax.text(phase, min_val - self._handle_height - self._handle_offset - self._label_buffer,
                                     self._format_display_value(display_min),
                                     ha='center', va='top', fontsize=7, 
                                     fontweight='bold', zorder=11)
        self.max_text = self.ax.text(phase, max_val + self._handle_offset + self._handle_height + self._label_buffer,
                                     self._format_display_value(display_max),
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
            (phase - self.handle_width/2, max_val + self._handle_offset),
            self.handle_width,
            self._handle_height,
            facecolor='lightgrey', edgecolor='black', linewidth=2,
            visible=True, zorder=20  # Always visible for performance
        )
        self.bottom_handle = patches.Rectangle(
            (phase - self.handle_width/2, min_val - self._handle_height - self._handle_offset),
            self.handle_width,
            self._handle_height,
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

        # Track if this box is selected
        self.selected = False
    
    def _get_display_value(self, value):
        """Return value ready for labeling; values stored internally in base units."""
        if self.parent is None:
            return value
        return self.parent.convert_value_for_display(self.var_name, value)

    def _format_display_value(self, value):
        """Format display value with an appropriate unit suffix."""
        if value is None:
            formatted = 'N/A'
        else:
            try:
                numeric_value = float(value)
                if np.isnan(numeric_value):
                    formatted = 'N/A'
                else:
                    formatted = f'{numeric_value:.3f}'
            except (TypeError, ValueError):
                formatted = str(value)

        if self.display_unit:
            return f"{formatted} {self.display_unit}"
        return formatted

    def _pixels_to_data(self, pixels: float) -> float:
        """Convert a fixed pixel distance to data units for consistent handle sizing."""
        self._update_conversion_cache()
        if not self._pixels_per_data_unit:
            return 0.0
        return pixels / self._pixels_per_data_unit

    def _update_handle_metrics(self):
        """Refresh cached handle offsets based on the latest axis scaling."""
        self._handle_height = self._pixels_to_data(self.HANDLE_HEIGHT_PIXELS)
        self._handle_offset = self._pixels_to_data(self.HANDLE_OFFSET_PIXELS)
        self._label_buffer = self._pixels_to_data(self.LABEL_BUFFER_PIXELS)

    def _update_handle_artists(self):
        """Update handle sizes, positions, and label locations using cached metrics."""
        self._update_handle_metrics()

        display_min = self._get_display_value(self.min_val)
        display_max = self._get_display_value(self.max_val)

        min_y = self.min_val - self._handle_height - self._handle_offset - self._label_buffer
        max_y = self.max_val + self._handle_offset + self._handle_height + self._label_buffer

        self.min_text.set_text(self._format_display_value(display_min))
        self.min_text.set_position((self.phase, min_y))

        self.max_text.set_text(self._format_display_value(display_max))
        self.max_text.set_position((self.phase, max_y))

        handle_x = self.phase - self.handle_width / 2

        self.top_handle.set_x(handle_x)
        self.top_handle.set_y(self.max_val + self._handle_offset)
        self.top_handle.set_width(self.handle_width)
        self.top_handle.set_height(self._handle_height)

        self.bottom_handle.set_x(handle_x)
        self.bottom_handle.set_y(self.min_val - self._handle_height - self._handle_offset)
        self.bottom_handle.set_width(self.handle_width)
        self.bottom_handle.set_height(self._handle_height)

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
        if event.xdata is None or event.ydata is None:
            return

        if self.parent is not None:
            if self.parent._normalize_axis(event.inaxes) != self.parent._normalize_axis(self.ax):
                return
        elif event.inaxes != self.ax:
            return

        # Only handle left-clicks (button 1) for dragging - allow right-clicks to pass through
        if event.button != 1:
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

    def contains_event(self, event) -> bool:
        """Return True when the pointer event targets this box."""
        if event.x is None or event.y is None:
            return False

        if self.rect.contains_point((event.x, event.y)):
            return True

        # Allow clicks on resize handles
        if (self.top_handle.contains_point((event.x, event.y)) or
                self.bottom_handle.contains_point((event.x, event.y))):
            return True

        return self.hover_zone.contains_point((event.x, event.y))

    def _draw_self(self):
        """Draw this box and associated UI elements."""
        self.ax.draw_artist(self.rect)
        self.ax.draw_artist(self.min_text)
        self.ax.draw_artist(self.max_text)
        self.ax.draw_artist(self.phase_text)
        self.ax.draw_artist(self.top_handle)
        self.ax.draw_artist(self.bottom_handle)
        if self.drag_phase_text.get_visible():
            self.ax.draw_artist(self.drag_phase_text)

    def _draw_box(self):
        """Redraw this axis using the cached background if available."""
        if self.background is not None and not self.background_invalid:
            canvas = self.ax.figure.canvas
            canvas.restore_region(self.background)

            boxes_to_draw = [self]
            if self.parent is not None:
                axis_key = self.parent._normalize_axis(self.ax)
                boxes_to_draw = self.parent._boxes_by_axis.get(axis_key, [self])

            for box in boxes_to_draw:
                box._draw_self()

            canvas.blit(self.ax.bbox)
        else:
            self.ax.figure.canvas.draw_idle()

    def redraw(self):
        """Public helper to trigger a redraw from the parent application."""
        self._draw_box()

    # PERFORMANCE OPTIMIZATION: on_hover method completely removed
    # Circles are now always visible for better performance
    # This eliminates expensive pixel-to-data conversions and draw calls on every mouse move
    
    def on_motion(self, event):
        """Handle mouse motion event with performance optimizations."""
        if self.dragging is None:
            return

        if self.parent is not None:
            if self.parent._normalize_axis(event.inaxes) != self.parent._normalize_axis(self.ax):
                return
        elif event.inaxes != self.ax:
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

        # Update handle sizing and label positions using pixel-consistent metrics
        self._update_handle_artists()

        # Update hover zone position (using cached values)
        self.hover_zone.set_x(self.phase - self.box_width/2)
        self.hover_zone.set_y(self.min_val - self._hover_extend_data)
        self.hover_zone.set_height((self.max_val - self.min_val) + 2 * self._hover_extend_data)

        # Redraw using cached background (falls back to full draw if needed)
        self.redraw()
    
    def on_release(self, event):
        """Handle mouse release event."""
        if self.dragging is not None:
            self.dragging = None
            self.rect.set_edgecolor(self.edgecolor)
            # Hide phase indicator
            self.drag_phase_text.set_visible(False)
            # PERFORMANCE: Redraw only the affected axes using cached background
            self.redraw()
            
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

        # Update handle sizing and label positions using pixel-consistent metrics
        self._update_handle_artists()

        # Update hover zone position
        self._update_conversion_cache()  # Ensure cache is current
        hover_extend_data = self._hover_extend_data
        self.hover_zone.set_y(self.min_val - hover_extend_data)
        self.hover_zone.set_height((self.max_val - self.min_val) + 2 * hover_extend_data)

        # Redraw with updated values
        self.redraw()
    
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
        
        # Event callbacks are centrally managed; nothing to disconnect here


class InteractiveValidationTuner:
    """
    Main GUI application for interactive validation range tuning.
    """
    
    def __init__(self):
        """Initialize the interactive validation tuner."""
        self.validation_data = {}  # Active validation ranges (ipsi + contra)
        self.full_validation_data = {}  # Mirror of validation_data for validation routines
        self.original_validation_data = {}  # Immutable copy of loaded YAML
        self.original_full_validation_data = {}  # Immutable copy for backward compatibility
        self.config_manager = None  # Will be initialized when loading ranges
        self.dataset_path = None
        self.locomotion_data = None
        self.current_task = None
        self.draggable_boxes = []
        self._boxes_by_axis = defaultdict(list)
        self._axis_aliases = {}
        self.validator = Validator()
        self.data_cache = {}
        self.phase_template = np.linspace(0, 100, 150)
        self.max_traces_per_axis = 350
        self.modified = False
        self.unknown_tasks = set()
        self.dataset_tasks = set()  # Track which tasks exist in the loaded dataset
        self._missing_task_notice = None  # Message shown when YAML task lacks dataset support
        self.available_tasks = []  # Cached list of tasks displayed in the dropdown

        # PERFORMANCE: Shared background cache for all draggable boxes
        self._shared_background = None
        self._shared_background_invalid = True

        # Centralized canvas event state
        self._canvas_event_cids = []
        self._active_box = None
        self.debug = False
        
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

    def _set_status(self, message: str):
        """Safely update the status bar if it exists."""
        if hasattr(self, 'status_bar'):
            self.status_bar.config(text=message)

    def _dataset_has_task(self, task: Optional[str]) -> bool:
        """Return True when the loaded dataset contains the requested task."""
        return bool(self.locomotion_data) and bool(task) and task in self.dataset_tasks

    def _compute_available_tasks(self) -> List[str]:
        """Determine which tasks should appear in the dropdown."""
        if self.dataset_tasks:
            return sorted(self.dataset_tasks)
        return sorted(self.validation_data.keys())

    def _refresh_task_dropdown(self, preserve_selection: bool = True):
        """Populate the dropdown with the appropriate task list and select a default."""
        tasks = self._compute_available_tasks()
        self.available_tasks = tasks

        previous = self.current_task if preserve_selection else None
        if previous not in tasks:
            previous = None

        selected = previous if previous else (tasks[0] if tasks else None)

        self.task_dropdown['values'] = tasks

        if selected:
            self.task_dropdown.set(selected)
            self.task_var.set(selected)
            self.current_task = selected
        else:
            self.task_dropdown.set('')
            self.task_var.set('')
            self.current_task = None

        if self.dataset_tasks:
            hidden_yaml_tasks = sorted(set(self.validation_data.keys()) - self.dataset_tasks)
            if hidden_yaml_tasks:
                preview = ', '.join(hidden_yaml_tasks[:4])
                if len(hidden_yaml_tasks) > 4:
                    preview += ', ...'
                print(f"INFO: Hiding YAML-only tasks not present in dataset: {preview}")

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

        # Help button to show quick usage instructions
        self.help_button = ttk.Button(
            toolbar_frame,
            text="Help",
            command=self.show_help_dialog
        )
        self.help_button.pack(side=tk.LEFT, padx=5)

        # Checkbox to show locally passing strides
        self.show_local_passing_var = tk.BooleanVar(value=False)
        self.show_local_checkbox = ttk.Checkbutton(
            toolbar_frame, 
            text="Show Locally Passing (Yellow)",
            variable=self.show_local_passing_var,
            command=self.on_show_local_toggle
        )
        self.show_local_checkbox.pack(side=tk.LEFT, padx=10)
        
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
                
                # Extract validation data (explicit ipsi + contra)
                self.validation_data = {}
                self.full_validation_data = {}
                self.original_validation_data = {}
                self.original_full_validation_data = {}
                
                for task_name in self.config_manager.get_tasks():
                    full_task_data = self.config_manager.get_task_data(task_name)
                    self.validation_data[task_name] = copy.deepcopy(full_task_data)
                    self.full_validation_data[task_name] = copy.deepcopy(full_task_data)
                    self.original_validation_data[task_name] = copy.deepcopy(full_task_data)
                    self.original_full_validation_data[task_name] = copy.deepcopy(full_task_data)

                yaml_tasks = list(self.validation_data.keys())
                self._note_unknown_tasks(yaml_tasks, source="validation ranges")
                self._refresh_task_dropdown(preserve_selection=False)

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
            box._update_handle_artists()

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

    def _get_usage_sections(self) -> Dict[str, str]:
        """Return structured usage information sections."""
        return {
            "goal": (
                "Fine-tune validation ranges so the exported YAML captures your trusted data "
                "before you submit the dataset."
            ),
            "steps": (
                "1. Load validation ranges via File → Load Validation Ranges.\n"
                "2. Load a dataset via File → Load Dataset.\n"
                "3. Pick a task from the toolbar dropdown.\n"
                "4. Drag the green/red boxes so acceptable strides stay inside the ranges.\n"
                "5. Press Validate to check pass/fail plots and iterate.\n"
                "6. Export the YAML once ranges are dialed in and include it with your submission."
            ),
            "tips": [
                "Click the Help button anytime to bring these instructions back.",
                "Use right-click menus or Reset All whenever you need to revert ranges.",
                "Work feature-by-feature to isolate issues and spot trends.",
                "Keep a backup of the original YAML so you can compare changes."
            ],
        }

    def _get_usage_instructions_text(self) -> str:
        """Return formatted usage instructions for display in dialogs."""
        sections = self._get_usage_sections()
        tips_text = "\n".join(f"• {tip}" for tip in sections['tips'])
        return (
            "Interactive Validation Range Tuner\n\n"
            f"Goal: {sections['goal']}\n\n"
            f"Steps:\n{sections['steps']}\n\n"
            f"Tips:\n{tips_text}"
        )

    def _add_secondary_angle_axis(self, ax, y_min, y_max):
        """Add a degree-scaled twin axis for angular variables."""
        twin_ax = ax.twinx()
        twin_ax.set_ylim(y_min, y_max)
        twin_ax.grid(False)
        twin_ax.set_ylabel('deg', fontsize=8, color='gray')
        twin_ax.tick_params(axis='y', labelcolor='gray', labelsize=7)

        formatter = FuncFormatter(lambda val, _: f"{np.rad2deg(val):.1f}")
        twin_ax.yaxis.set_major_formatter(formatter)

        def _sync_ticks():
            ticks = ax.get_yticks()
            twin_ax.set_ylim(ax.get_ylim())
            twin_ax.yaxis.set_major_locator(FixedLocator(ticks))

        _sync_ticks()

        canvas = ax.figure.canvas

        def _on_draw(event):
            if event.canvas is canvas:
                _sync_ticks()

        canvas.mpl_connect('draw_event', _on_draw)

        # Subtle styling to distinguish the secondary spine
        if 'right' in twin_ax.spines:
            twin_ax.spines['right'].set_color('gray')

        # Map the secondary axis back to its primary axis for event handling
        self._axis_aliases[twin_ax] = ax
        return twin_ax

    @staticmethod
    def _base_task_name(task_name: str) -> str:
        """Strip population suffixes before registry lookup."""

        if not task_name:
            return ''

        task_lower = task_name.lower()
        population_suffixes = [
            '_stroke', '_amputee', '_tfa', '_tta', '_pd', '_sci', '_cp',
            '_ms', '_oa', '_cva', '_parkinsons'
        ]
        for suffix in population_suffixes:
            if task_lower.endswith(suffix):
                return task_lower[:-len(suffix)]
        return task_lower

    def _note_unknown_tasks(self, tasks, source: str):
        """Track and warn about tasks missing from the canonical registry."""

        unknown = sorted({
            task for task in tasks
            if task and not task_registry.is_valid_task(self._base_task_name(task))
        })

        if not unknown:
            return

        self.unknown_tasks.update(unknown)
        warning = (
            f"Warning: {source} contains tasks not in task_registry: "
            f"{', '.join(unknown)}"
        )
        print(f"WARNING: {warning}")
        if hasattr(self, 'status_bar'):
            self.status_bar.config(text=warning)

    def _initialize_task_from_dataset(self, task_name: str) -> bool:
        """Generate placeholder validation ranges for a dataset-only task."""

        if not self.locomotion_data or not task_name:
            return False

        if task_name in self.validation_data:
            return False

        try:
            subjects = self.locomotion_data.get_subjects()
        except Exception:
            return False

        all_data = []
        feature_names = None

        for subject in subjects:
            try:
                cycles_data, feature_names = self.locomotion_data.get_cycles(
                    subject=subject,
                    task=task_name,
                    features=None
                )
            except Exception:
                continue

            if cycles_data.size == 0:
                continue

            all_data.append(cycles_data)

        if not all_data or feature_names is None:
            return False

        combined = np.concatenate(all_data, axis=0)
        if combined.size == 0:
            return False

        num_samples = combined.shape[1]
        if num_samples <= 1:
            return False

        phases = [0, 25, 50, 75]
        phase_ranges = {}
        for phase in phases:
            phase_idx = int(round(phase / 100 * (num_samples - 1)))
            phase_idx = max(0, min(num_samples - 1, phase_idx))
            feature_ranges = {}
            for feat_idx, feature in enumerate(feature_names):
                values = combined[:, phase_idx, feat_idx]
                values = values[np.isfinite(values)]
                if values.size == 0:
                    continue
                lower = float(np.min(values))
                upper = float(np.max(values))
                if not np.isfinite(lower) or not np.isfinite(upper):
                    continue
                if lower == upper:
                    epsilon = max(1e-4, abs(lower) * 0.05)
                    lower -= epsilon
                    upper += epsilon
                feature_ranges[feature] = {
                    'min': lower,
                    'max': upper
                }
            if feature_ranges:
                phase_ranges[phase] = feature_ranges

        if not phase_ranges:
            return False

        if not phase_ranges:
            return False

        self.validation_data[task_name] = {
            phase: {var: copy.deepcopy(rng) for var, rng in variables.items()}
            for phase, variables in phase_ranges.items()
        }
        self.full_validation_data[task_name] = copy.deepcopy(self.validation_data[task_name])
        self.original_validation_data[task_name] = copy.deepcopy(self.validation_data[task_name])
        self.original_full_validation_data[task_name] = copy.deepcopy(self.validation_data[task_name])

        if self.config_manager is not None:
            config_snapshot = copy.deepcopy(self.config_manager.get_data())
            config_snapshot[task_name] = {
                'metadata': {},
                'phases': copy.deepcopy(self.validation_data[task_name])
            }
            self.config_manager.set_data(config_snapshot)

        self.modified = True
        print(f"Initialized placeholder validation ranges for task '{task_name}' using full data range.")
        return True

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
        
        # Create initial empty axes with usage instructions
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)
        self.ax.axis('off')

        self.ax.text(
            0.5,
            0.5,
            self._get_usage_instructions_text(),
            ha='center',
            va='center',
            fontsize=11,
            color='dimgray',
            wrap=True
        )
        self.canvas.draw()

        # Ensure canvas events are connected once the widget exists
        self._bind_canvas_events()

        # Update scroll region
        self.plot_frame.update_idletasks()
        self.on_plot_frame_configure()

    def _bind_canvas_events(self):
        """Attach centralized press/move/release handlers to the canvas."""
        if not hasattr(self, 'canvas') or self.canvas is None:
            return

        # Detach any existing bindings before wiring new ones
        if self._canvas_event_cids:
            for bound_canvas, cid in self._canvas_event_cids:
                try:
                    bound_canvas.mpl_disconnect(cid)
                except Exception:
                    pass
            self._canvas_event_cids = []

        canvas = self.canvas
        self._canvas_event_cids = [
            (canvas, canvas.mpl_connect('button_press_event', self._on_canvas_press)),
            (canvas, canvas.mpl_connect('motion_notify_event', self._on_canvas_motion)),
            (canvas, canvas.mpl_connect('button_release_event', self._on_canvas_release)),
            (canvas, canvas.mpl_connect('scroll_event', self._on_canvas_scroll)),
        ]

    def _normalize_axis(self, axis):
        """Map twinned axes back to their primary axis for hit-testing."""
        return self._axis_aliases.get(axis, axis)

    @staticmethod
    def _downsample_indices(indices, max_samples):
        indices = np.asarray(indices, dtype=int)
        if not indices.size or len(indices) <= max_samples:
            return indices
        positions = np.linspace(0, len(indices) - 1, max_samples).astype(int)
        return indices[positions]

    def _build_segments(self, stride_array):
        if stride_array.size == 0:
            return None
        phase = self.phase_template
        if stride_array.shape[1] != phase.shape[0]:
            phase = np.linspace(0, 100, stride_array.shape[1])
        phase_tiles = np.tile(phase, (stride_array.shape[0], 1))
        segments = np.stack((phase_tiles, stride_array), axis=2)
        return segments

    def _register_box(self, box: DraggableBox):
        """Track a draggable box for hit-testing and redraw management."""
        self.draggable_boxes.append(box)
        axis_key = self._normalize_axis(box.ax)
        self._boxes_by_axis[axis_key].append(box)

    def _unregister_box(self, box: DraggableBox):
        """Remove a draggable box from tracking structures."""
        if box in self.draggable_boxes:
            self.draggable_boxes.remove(box)

        axis_key = self._normalize_axis(box.ax)
        axis_boxes = self._boxes_by_axis.get(axis_key)
        if axis_boxes and box in axis_boxes:
                axis_boxes.remove(box)
                if not axis_boxes:
                    del self._boxes_by_axis[axis_key]

    def _refresh_variable_boxes(self, var_name: str):
        """Rebuild draggable boxes for a specific variable without full redraw."""
        if not self.current_task or not hasattr(self, 'current_variables'):
            return
        if var_name not in self.current_variables:
            return

        var_idx = self.current_variables.index(var_name)

        axes = []
        if hasattr(self, 'axes_pass') and var_idx < len(self.axes_pass):
            axes.append(self.axes_pass[var_idx])
        if hasattr(self, 'axes_fail') and var_idx < len(self.axes_fail):
            axes.append(self.axes_fail[var_idx])

        if not axes:
            return

        # Remove existing boxes tied to this variable
        for ax in axes:
            axis_key = self._normalize_axis(ax)
            boxes = list(self._boxes_by_axis.get(axis_key, []))
            for box in boxes:
                if box.var_name == var_name:
                    self._unregister_box(box)
                    box.remove()

        task_data = self.validation_data.get(self.current_task, {})
        if not task_data:
            self.canvas.draw_idle()
            return

        # Prepare phase entries sorted numerically while retaining original keys
        phase_entries = []
        for phase_key, variables in task_data.items():
            if not isinstance(variables, dict) or var_name not in variables:
                continue
            try:
                phase_val = float(phase_key)
            except (TypeError, ValueError):
                try:
                    phase_val = float(int(phase_key))
                except (TypeError, ValueError):
                    continue
            phase_entries.append((phase_val, phase_key))

        phase_entries.sort(key=lambda x: x[0])

        for phase_val, phase_key in phase_entries:
            range_data = task_data[phase_key][var_name]
            min_val = range_data.get('min')
            max_val = range_data.get('max')
            if min_val is None or max_val is None:
                continue

            display_phase = int(round(phase_val))

            ax_pass = self.axes_pass[var_idx] if var_idx < len(self.axes_pass) else None
            ax_fail = self.axes_fail[var_idx] if var_idx < len(self.axes_fail) else None

            if ax_pass:
                box_pass = DraggableBox(
                    ax_pass, display_phase, var_name, min_val, max_val,
                    callback=self.on_box_changed,
                    color='lightgreen',
                    edgecolor='black',
                    allow_x_drag=True,
                    parent=self
                )
                self._register_box(box_pass)
            else:
                box_pass = None

            if ax_fail:
                box_fail = DraggableBox(
                    ax_fail, display_phase, var_name, min_val, max_val,
                    callback=self.on_box_changed,
                    color='lightcoral',
                    edgecolor='black',
                    allow_x_drag=True,
                    parent=self
                )
                self._register_box(box_fail)
            else:
                box_fail = None

            if box_pass and box_fail:
                box_pass.paired_box = box_fail
                box_fail.paired_box = box_pass

            # Attach cached backgrounds if available for instant blitting
            if hasattr(self, 'trace_backgrounds'):
                pass_bg = self.trace_backgrounds.get(f'pass_{var_idx}') if ax_pass else None
                fail_bg = self.trace_backgrounds.get(f'fail_{var_idx}') if ax_fail else None

                if box_pass and pass_bg is not None:
                    box_pass.background = pass_bg
                    box_pass.background_invalid = False
                if box_fail and fail_bg is not None:
                    box_fail.background = fail_bg
                    box_fail.background_invalid = False

            if box_pass:
                box_pass.redraw()
            if box_fail:
                box_fail.redraw()

        self.canvas.draw_idle()

    def _find_box_for_event(self, event) -> Optional[DraggableBox]:
        """Return the top-most draggable box that should respond to the event."""
        if not event:
            return None

        axis_key = self._normalize_axis(event.inaxes)
        axis_boxes = self._boxes_by_axis.get(axis_key)
        if not axis_boxes:
            return None

        for box in reversed(axis_boxes):
            if box.contains_event(event):
                return box
        return None

    def _on_canvas_press(self, event):
        """Route mouse press events to the active draggable box or context menu."""
        self._active_box = None

        if event is None:
            return

        if event.button == 3:
            # Delegate right-clicks to the context menu handler
            self.on_plot_click(event)
            return

        if event.button != 1:
            return

        box = self._find_box_for_event(event)
        if box:
            self._active_box = box
            box.on_press(event)

    def _on_canvas_motion(self, event):
        """Forward motion events to the currently active box."""
        if self._active_box is not None:
            self._active_box.on_motion(event)

    def _on_canvas_release(self, event):
        """Release the active box and finalize edits."""
        if self._active_box is not None:
            self._active_box.on_release(event)
            self._active_box = None

    def _on_canvas_scroll(self, event):
        """
        Handle scroll wheel events to zoom the y-axis for a single row.

        When the user scrolls while hovering over either the Pass or Fail
        column for a variable, this zooms the y-limits for that variable's
        row only (both axes in the pair). Other rows remain unchanged.
        """
        if event is None or event.inaxes is None:
            return

        # Ensure we have a full validation display with axis pairs
        if not hasattr(self, 'axes_pass') or not hasattr(self, 'axes_fail'):
            return

        # Map twinned axes back to their primary axis for hit-testing
        axis_key = self._normalize_axis(event.inaxes)
        if axis_key is None:
            return

        # Identify the row index for this axis
        row_index = None
        if axis_key in getattr(self, 'axes_pass', []):
            row_index = self.axes_pass.index(axis_key)
        elif axis_key in getattr(self, 'axes_fail', []):
            row_index = self.axes_fail.index(axis_key)

        if row_index is None:
            return

        # Obtain the axis pair for this row
        try:
            ax_pass = self.axes_pass[row_index]
            ax_fail = self.axes_fail[row_index]
        except (AttributeError, IndexError):
            return

        # Current limits and zoom center
        y_min, y_max = ax_pass.get_ylim()
        if not np.isfinite(y_min) or not np.isfinite(y_max):
            return

        span = y_max - y_min
        if span <= 0:
            return

        # Use cursor position as zoom center when available
        center = event.ydata if event.ydata is not None else (y_min + y_max) / 2.0

        # Scroll up to zoom in, down to zoom out
        # event.step is typically +1 for up, -1 for down
        step = getattr(event, 'step', 0) or 0
        if step == 0:
            # Fallback based on button label if step is unavailable
            if getattr(event, 'button', None) == 'up':
                step = 1
            elif getattr(event, 'button', None) == 'down':
                step = -1
            else:
                return

        # Choose a gentle zoom factor per scroll notch
        zoom_in_factor = 0.8
        zoom_out_factor = 1.25
        factor = zoom_in_factor if step > 0 else zoom_out_factor

        new_half_span = (span * factor) / 2.0

        # Prevent over-zooming to a nearly flat line
        min_span = 1e-3
        if new_half_span * 2.0 < min_span:
            new_half_span = min_span / 2.0

        new_y_min = center - new_half_span
        new_y_max = center + new_half_span

        # Apply the same limits to both axes in this row
        ax_pass.set_ylim(new_y_min, new_y_max)
        ax_fail.set_ylim(new_y_min, new_y_max)

        # Invalidate cached backgrounds so draggable boxes update correctly
        self.invalidate_all_backgrounds()

        # Redraw the canvas with updated limits
        if hasattr(self, 'canvas'):
            self.canvas.draw_idle()

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

            # Extract validation data (ipsi + contra stored explicitly)
            self.validation_data = {}
            self.full_validation_data = {}
            self.original_validation_data = {}
            self.original_full_validation_data = {}
            
            for task_name in self.config_manager.get_tasks():
                full_task_data = self.config_manager.get_task_data(task_name)
                self.validation_data[task_name] = copy.deepcopy(full_task_data)
                self.full_validation_data[task_name] = copy.deepcopy(full_task_data)
                self.original_validation_data[task_name] = copy.deepcopy(full_task_data)
                self.original_full_validation_data[task_name] = copy.deepcopy(full_task_data)
            
            yaml_tasks = list(self.validation_data.keys())
            self._note_unknown_tasks(yaml_tasks, source="validation ranges")
            self._refresh_task_dropdown()

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
            self._missing_task_notice = None
            
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
            dataset_tasks = list(self.locomotion_data.get_tasks())
            self.dataset_tasks = set(dataset_tasks)

            added_any = False
            for task in dataset_tasks:
                if task not in self.validation_data:
                    added_any = self._initialize_task_from_dataset(task) or added_any

            if added_any:
                print("Generated placeholder validation ranges for dataset-only tasks.")

            self._note_unknown_tasks(dataset_tasks, source="dataset")

            dataset_only_tasks = self.dataset_tasks - set(self.validation_data.keys())
            if dataset_only_tasks:
                friendly_list = ', '.join(sorted(dataset_only_tasks))
                print(f"INFO: Dataset tasks without YAML ranges will use placeholders: {friendly_list}")

            self._refresh_task_dropdown()

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

    def show_help_dialog(self):
        """Display usage instructions in a dialog window."""
        messagebox.showinfo(
            title="Interactive Validation Range Tuner Help",
            message=self._get_usage_instructions_text()
        )

    def get_variable_unit(self, var_name):
        """Determine the base unit of a variable from its name suffix."""
        if var_name is None:
            return ""

        # Check suffixes
        if var_name.endswith('_rad'):
            return 'rad'
        elif var_name.endswith('_Nm_kg'):
            return 'Nm/kg'
        elif var_name.endswith('_BW'):
            return 'BW'
        elif var_name.endswith('_rad_s'):
            return 'rad/s'
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

    def get_display_unit(self, var_name):
        """Return the unit shown to the user for the given variable."""
        base_unit = self.get_variable_unit(var_name)

        if not var_name:
            return base_unit

        if var_name.endswith('_rad_s'):
            return 'deg/s'
        if var_name.endswith('_rad'):
            return 'deg'

        return base_unit

    def convert_value_for_display(self, var_name, value):
        """Convert stored values to the unit presented to the user."""
        if value is None or var_name is None:
            return value

        try:
            arr = np.asarray(value, dtype=float)
        except Exception:
            return value

        if var_name.endswith('_rad_s') or var_name.endswith('_rad'):
            arr = np.rad2deg(arr)

        if arr.shape == ():
            return float(arr)
        return arr
    
    def get_all_features(self):
        """Get all features to display (spec-driven, with dataset-aware ordering)."""
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
            'ankle_dorsiflexion_velocity_ipsi_rad_s',
            'thigh_sagittal_velocity_ipsi_rad_s',
            'shank_sagittal_velocity_ipsi_rad_s',
            'foot_sagittal_velocity_ipsi_rad_s'
        ]
        velocity_labels = [
            'Hip Flexion Velocity (Ipsi)',
            'Knee Flexion Velocity (Ipsi)',
            'Ankle Dorsiflexion Velocity (Ipsi)',
            'Thigh Sagittal Velocity (Ipsi)',
            'Shank Sagittal Velocity (Ipsi)',
            'Foot Sagittal Velocity (Ipsi)'
        ]
        
        # Combine primary features (most commonly available)
        # Start with sagittal plane kinematics, velocities, kinetics, GRF, COP, and segments
        all_vars = (
            kinematic_vars
            + velocity_vars
            + kinetic_vars
            + grf_vars
            + cop_vars
            + segment_vars
        )
        all_labels = (
            kinematic_labels
            + velocity_labels
            + kinetic_labels
            + grf_labels
            + cop_labels
            + segment_labels
        )

        dataset_mode = self.locomotion_data is not None

        ordered_vars = []
        ordered_labels = []

        def _add_feature(var_name, label):
            if var_name not in ordered_vars:
                ordered_vars.append(var_name)
                ordered_labels.append(label)

        # Always start from the spec-driven ordering so rows appear even when
        # the dataset is missing some variables.
        for var_name, label in zip(all_vars, all_labels):
            _add_feature(var_name, label)

            # In spec-only mode, also expose contralateral counterparts to aid tuning.
            if (not dataset_mode) and '_ipsi' in var_name:
                contra_var = var_name.replace('_ipsi', '_contra')
                if '(Ipsi)' in label:
                    contra_label = label.replace('(Ipsi)', '(Contra)')
                else:
                    contra_label = f"{label} (Contra)"
                _add_feature(contra_var, contra_label)

        # When a dataset is loaded, also surface any additional dataset features
        # (e.g., non-standard variables) after the canonical list.
        if dataset_mode:
            dataset_features = list(self.locomotion_data.features)
            ordered_dataset_features = self._order_dataset_features(dataset_features)
            for var in ordered_dataset_features:
                if var not in ordered_vars:
                    _add_feature(var, self._format_feature_label(var))

        return ordered_vars, ordered_labels

    @staticmethod
    def _format_feature_label(var_name: str) -> str:
        """Create a readable label from a dataset feature name."""
        if not var_name:
            return ''

        parts = var_name.split('_')
        # Highlight unit separately if present
        if len(parts) > 1 and parts[-1] in {'rad', 'deg', 'Nm', 'BW', 'm', 'N'}:
            core = ' '.join(parts[:-1]).title()
            return f"{core} ({parts[-1]})"
        elif len(parts) > 2 and f"{parts[-2]}_{parts[-1]}" in {'rad_s', 'deg_s', 'Nm_kg', 'W_kg'}:
            core = ' '.join(parts[:-2]).title()
            return f"{core} ({parts[-2]}_{parts[-1]})"

        return var_name.replace('_', ' ').title()

    @staticmethod
    def _order_dataset_features(features):
        """Ensure ipsi variants precede contra variants while preserving base order."""
        base_order = []
        grouped = {}

        for feature in features:
            side = None
            if '_ipsi_' in feature:
                side = 'ipsi'
            elif '_contra_' in feature:
                side = 'contra'

            if side:
                base = re.sub(r'_(ipsi|contra)(?=_)', '', feature)
            else:
                base = feature

            if base not in grouped:
                grouped[base] = {'ipsi': None, 'contra': None, 'other': []}
                base_order.append(base)

            if side == 'ipsi':
                grouped[base]['ipsi'] = feature
            elif side == 'contra':
                grouped[base]['contra'] = feature
            else:
                grouped[base]['other'].append(feature)

        ordered = []
        for base in base_order:
            entry = grouped[base]
            if entry['ipsi']:
                ordered.append(entry['ipsi'])
            if entry['contra']:
                ordered.append(entry['contra'])
            ordered.extend(entry['other'])

        return ordered
    
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
            self._axis_aliases.clear()

            # Remove existing draggable boxes
            for box in self.draggable_boxes:
                box.remove()
            self.draggable_boxes = []
            self._boxes_by_axis.clear()
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
        row_height = 2.3  # Provide extra vertical space for axis labels
        fig_height = max(n_vars * row_height + 0.8, 4.6)

        # Create new figure with dynamic size
        from matplotlib.figure import Figure
        self.fig = Figure(figsize=(fig_width, fig_height), dpi=dpi)
        
        # Balanced spacing: minimal top whitespace, room for x-labels
        self.fig.subplots_adjust(left=0.07, right=0.985, top=0.96, bottom=0.08, hspace=0.22, wspace=0.12)
        
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
                            self._register_box(box_pass)
                            
                            # Create draggable box on fail axis (also interactive)
                            box_fail = DraggableBox(
                                ax_fail, phase, var_name, min_val, max_val,
                                callback=self.on_box_changed,  # Add callback for fail side too
                                color='lightcoral',  # Light red fill for fail column
                                edgecolor='black',  # Black outline
                                allow_x_drag=True,  # Allow dragging on fail side as well
                                parent=self
                            )
                            self._register_box(box_fail)
                            
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
                         fontsize=12, fontweight='bold', y=0.97)
        
        # Create/update canvas
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        if hasattr(self, 'canvas'):
            self.canvas.get_tk_widget().destroy()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas.draw()

        # Ensure the centralized event handlers stay attached when the canvas is rebuilt
        self._bind_canvas_events()
        
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
        failing_strides = {var: set() for var in variables}
        self._missing_task_notice = None

        if not self.locomotion_data or not self.current_task:
            self.validation_stats = {
                'total_strides': 0,
                'passing_strides': 0,
                'features_validated': 0,
                'features_displayed': len(variables)
            }
            self.global_passing_strides = set()
            return failing_strides

        if not self._dataset_has_task(self.current_task):
            dataset_label = self.dataset_path.name if self.dataset_path else 'loaded dataset'
            message = (f"Dataset '{dataset_label}' does not contain task '{self.current_task}'. "
                       "Showing YAML ranges without stride data.")
            print(f"INFO: {message}")
            self._missing_task_notice = message
            self.validation_stats = {
                'total_strides': 0,
                'passing_strides': 0,
                'features_validated': 0,
                'features_displayed': len(variables)
            }
            self.global_passing_strides = set()
            self._set_status(message)
            return failing_strides

        # Sync validator config with current in-memory ranges
        self.validator.config_manager.set_data(copy.deepcopy(self.full_validation_data))

        validation_result = self.validator.validate_dataset(
            locomotion_data=self.locomotion_data,
            task_filter=[self.current_task]
        )

        task_info = validation_result['tasks'].get(self.current_task, {})

        failing_map = task_info.get('failing_strides_by_variable', {})
        for var_name, stride_set in failing_map.items():
            failing_strides[var_name] = set(stride_set)

        self.global_passing_strides = set(task_info.get('global_passing_strides', set()))

        self.validation_stats = {
            'total_strides': task_info.get('total_strides', 0),
            'passing_strides': len(self.global_passing_strides),
            'features_validated': len(task_info.get('validated_variables', [])),
            'features_displayed': len(variables)
        }

        print("\nValidation Summary:")
        print(f"  Total displayed features: {len(variables)}")
        validated_vars = task_info.get('validated_variables', [])
        in_dataset_count = len([v for v in variables if v in validated_vars])
        print(f"  Features in dataset: {in_dataset_count}")
        print(f"  Features being validated: {len(validated_vars)}")
        missing_vars = [v for v in variables if v not in validated_vars]
        if missing_vars:
            preview = ', '.join(missing_vars[:3])
            if len(missing_vars) > 3:
                preview += ', ...'
            print(f"  Missing from dataset or ranges: {preview}")
        print(f"  Total strides: {self.validation_stats['total_strides']}")
        if self.validation_stats['total_strides'] > 0:
            pass_pct = (
                self.validation_stats['passing_strides'] /
                self.validation_stats['total_strides'] * 100
            )
            print(f"  Passing all features: {self.validation_stats['passing_strides']} ({pass_pct:.1f}%)")
        else:
            print("  Passing all features: 0 (0.0%)")

        return failing_strides
    
    def get_expanded_y_range(self, var_name):
        """Get y-axis range with expanded margins for more dragging space."""
        y_min, y_max = -1, 1  # Default
        
        if not self.current_task or var_name is None:
            return y_min, y_max
        
        # Collect display ranges driven by both data and validation boxes
        ranges: List[Tuple[float, float]] = []

        cache_key = f"{self.current_task}_{var_name}"
        dataset_has_task = self._dataset_has_task(self.current_task)

        # Include data-driven range when available
        if dataset_has_task:
            data = None
            if cache_key in self.data_cache and len(self.data_cache[cache_key]) > 0:
                data = self.data_cache[cache_key]
            else:
                self.load_variable_data(var_name)
                if cache_key in self.data_cache and len(self.data_cache[cache_key]) > 0:
                    data = self.data_cache[cache_key]

            if data is not None:
                data_min = np.nanmin(data)
                data_max = np.nanmax(data)
                if np.isfinite(data_min) and np.isfinite(data_max):
                    span = max(data_max - data_min, 1e-6)
                    margin = max(span * 0.5, 0.5)
                    ranges.append((data_min - margin, data_max + margin))

        # Always include the validation box envelope so handles remain visible
        task_data = self.validation_data.get(self.current_task, {})
        all_mins = []
        all_maxs = []

        for phase in task_data.keys():
            if not str(phase).isdigit():
                continue
            phase = int(phase)

            if var_name in task_data[phase]:
                range_data = task_data[phase][var_name]
                min_val = range_data.get('min') if isinstance(range_data, dict) else None
                max_val = range_data.get('max') if isinstance(range_data, dict) else None

                if min_val is not None and max_val is not None:
                    all_mins.append(min_val)
                    all_maxs.append(max_val)

        if all_mins and all_maxs:
            val_min = min(all_mins)
            val_max = max(all_maxs)
            span = max(val_max - val_min, 1e-6)
            margin = max(span * 0.3, 0.5)
            ranges.append((val_min - margin, val_max + margin))

        if ranges:
            y_min = min(r[0] for r in ranges)
            y_max = max(r[1] for r in ranges)
        
        # Ensure minimum range for usability
        if (y_max - y_min) < 0.1:
            center = (y_max + y_min) / 2
            y_min = center - 0.5
            y_max = center + 0.5
        
        # Final safety check - never return NaN or Inf
        if np.isnan(y_min) or np.isnan(y_max) or np.isinf(y_min) or np.isinf(y_max):
            y_min, y_max = -1, 1  # Safe fallback
        
        return y_min, y_max
    
    def load_variable_data(self, var_name):
        """Load data for a specific variable into the cache."""
        if not self.locomotion_data or not self.current_task:
            return
        
        cache_key = f"{self.current_task}_{var_name}"
        if cache_key in self.data_cache:
            return  # Already cached

        if not self._dataset_has_task(self.current_task):
            if cache_key not in self.data_cache:
                self.data_cache[cache_key] = np.empty((0, self.phase_template.size))
            return

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
        if not self._dataset_has_task(self.current_task):
            self.data_cache.setdefault(cache_key, np.empty((0, self.phase_template.size)))
            if show_pass and show_local_passing:
                return (0, 0)
            return 0

        if cache_key in self.data_cache:
            all_data = self.data_cache[cache_key]
        else:
            collected = []
            try:
                subjects = self.locomotion_data.get_subjects()
                for subject in subjects:
                    try:
                        cycles_data, feature_names = self.locomotion_data.get_cycles(
                            subject=subject,
                            task=self.current_task,
                            features=None
                        )

                        if not hasattr(cycles_data, 'size') or cycles_data.size == 0:
                            continue

                        if var_name in feature_names:
                            var_idx = feature_names.index(var_name)
                            collected.append(cycles_data[:, :, var_idx])
                    except Exception:
                        continue

                if collected:
                    all_data = np.vstack(collected)
                else:
                    all_data = np.empty((0, self.phase_template.size))
                self.data_cache[cache_key] = all_data
            except Exception:
                all_data = np.empty((0, self.phase_template.size))

        if all_data.size == 0:
            return (0, 0) if show_pass and show_local_passing else 0

        total_strides = all_data.shape[0]
        global_passing = np.array(sorted(i for i in getattr(self, 'global_passing_strides', set())
                                         if 0 <= i < total_strides), dtype=int)
        failed_stride_indices = np.array(sorted(i for i in failed_stride_indices if 0 <= i < total_strides), dtype=int)

        if show_pass:
            count = len(global_passing)

            if show_local_passing:
                fail_mask = np.zeros(total_strides, dtype=bool)
                fail_mask[failed_stride_indices] = True
                global_mask = np.zeros(total_strides, dtype=bool)
                global_mask[global_passing] = True
                local_indices = np.where(~global_mask & ~fail_mask)[0]
            else:
                local_indices = np.array([], dtype=int)

            local_count = len(local_indices)

            # Draw globally passing strides
            if count:
                draw_indices = self._downsample_indices(global_passing, self.max_traces_per_axis)
                segments = self._build_segments(all_data[draw_indices])
                if segments is not None:
                    lc = LineCollection(segments, colors='green', alpha=0.2, linewidths=0.5, zorder=1)
                    ax.add_collection(lc)
                mean_pattern = np.mean(all_data[global_passing], axis=0)
                ax.plot(self.phase_template[:mean_pattern.size], mean_pattern, color='darkgreen', linewidth=2, zorder=5)

            # Draw locally passing strides if requested
            if show_local_passing and local_count:
                draw_local = self._downsample_indices(local_indices, self.max_traces_per_axis)
                segments = self._build_segments(all_data[draw_local])
                if segments is not None:
                    lc = LineCollection(segments, colors='gold', alpha=0.3, linewidths=0.5, zorder=2)
                    ax.add_collection(lc)
                mean_pattern = np.mean(all_data[local_indices], axis=0)
                ax.plot(self.phase_template[:mean_pattern.size], mean_pattern, color='darkorange', linewidth=2, zorder=6)

            if show_pass and show_local_passing:
                return count, local_count
            return count

        # Fail column rendering
        count = len(failed_stride_indices)
        if count:
            draw_fail = self._downsample_indices(failed_stride_indices, self.max_traces_per_axis)
            segments = self._build_segments(all_data[draw_fail])
            if segments is not None:
                lc = LineCollection(segments, colors='red', alpha=0.3, linewidths=0.5, zorder=1)
                ax.add_collection(lc)
            mean_pattern = np.mean(all_data[failed_stride_indices], axis=0)
            ax.plot(self.phase_template[:mean_pattern.size], mean_pattern, color='darkred', linewidth=2, zorder=5)

        return count
    
    def plot_variable_data(self, ax, var_name):
        """Plot actual data for a variable if available."""
        # Check cache first
        cache_key = f"{self.current_task}_{var_name}"
        if not self._dataset_has_task(self.current_task):
            self.data_cache.setdefault(cache_key, np.empty((0, self.phase_template.size)))
            return

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

            # Redraw the updated boxes without triggering a full canvas refresh
            box.redraw()
            if hasattr(box, 'paired_box') and box.paired_box:
                box.paired_box.redraw()

            self.modified = True
            self.status_bar.config(text=f"Modified: {box.var_name} at phase {box.phase}% - Press Validate to update")
            
            # Enable validate button
            if hasattr(self, 'validate_button'):
                self.validate_button.config(state='normal')
    
    
    
    def on_plot_click(self, event):
        """Handle right-click events for adding/deleting boxes."""
        if event.button == 3 and event.inaxes:  # Right-click
            # Check if we clicked on a box
            clicked_box = None
            axis_key = self._normalize_axis(event.inaxes)
            axis_boxes = self._boxes_by_axis.get(axis_key, [])
            for box in axis_boxes:
                if box.contains_event(event):
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
                axis_key = self._normalize_axis(event.inaxes)
                for i, (ax_pass, ax_fail) in enumerate(zip(self.axes_pass, self.axes_fail)):
                    if axis_key in (self._normalize_axis(ax_pass), self._normalize_axis(ax_fail)):
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

            if target_var:
                if menu.index('end') is not None:
                    menu.add_separator()
                has_reset_option = self._has_yaml_defaults(target_var)
                copy_commands_added = False

                if '_ipsi' in target_var:
                    other_side = 'contralateral'
                    menu.add_command(
                        label=f"Overwrite {other_side} with 50% phase offset",
                        command=lambda var=target_var: self.copy_variable_to_counterpart(var, to_contra=True, phase_offset=50)
                    )
                    menu.add_command(
                        label=f"Overwrite {other_side} with no offset",
                        command=lambda var=target_var: self.copy_variable_to_counterpart(var, to_contra=True, phase_offset=0)
                    )
                    copy_commands_added = True
                elif '_contra' in target_var:
                    other_side = 'ipsilateral'
                    menu.add_command(
                        label=f"Overwrite {other_side} with 50% phase offset",
                        command=lambda var=target_var: self.copy_variable_to_counterpart(var, to_contra=False, phase_offset=50)
                    )
                    menu.add_command(
                        label=f"Overwrite {other_side} with no offset",
                        command=lambda var=target_var: self.copy_variable_to_counterpart(var, to_contra=False, phase_offset=0)
                    )
                    copy_commands_added = True

                if has_reset_option:
                    if copy_commands_added:
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
        
        self._unregister_box(box)

        if paired_box:
            self._unregister_box(paired_box)
        
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

        # Keep validation structures synchronized
        self.full_validation_data[self.current_task] = copy.deepcopy(
            self.validation_data.get(self.current_task, {})
        )

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
        self._boxes_by_axis.clear()
        self._axis_aliases.clear()

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
                        if pass_bg is not None:
                            box_pass.background = pass_bg
                            box_pass.background_invalid = False
                        if fail_bg is not None:
                            box_fail.background = fail_bg
                            box_fail.background_invalid = False

                    self._register_box(box_pass)
                    self._register_box(box_fail)
                    box_pass.redraw()
                    box_fail.redraw()

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

    def copy_variable_to_counterpart(self, var_name: str, to_contra: bool, phase_offset: int = 0) -> None:
        """Copy validation ranges between ipsilateral and contralateral versions of a variable.

        Args:
            var_name: Source variable to copy from (ipsi or contra).
            to_contra: When True copy to contralateral; otherwise copy to ipsilateral side.
            phase_offset: Phase shift to apply (mod 100) when copying ranges.
        """
        if not self.current_task or not var_name:
            return

        task_data = self.validation_data.setdefault(self.current_task, {})
        full_task_data = self.full_validation_data.setdefault(self.current_task, {})

        if to_contra:
            source_name = var_name if '_ipsi' in var_name else var_name.replace('_contra', '_ipsi')
            target_name = source_name.replace('_ipsi', '_contra')
            target_side = 'contralateral'
        else:
            source_name = var_name if '_contra' in var_name else var_name.replace('_ipsi', '_contra')
            target_name = source_name.replace('_contra', '_ipsi')
            target_side = 'ipsilateral'

        if source_name == target_name:
            return

        offset = phase_offset % 100

        def _phase_key_to_int(phase_key):
            try:
                return int(phase_key)
            except (TypeError, ValueError):
                try:
                    return int(float(phase_key))
                except (TypeError, ValueError):
                    return 0

        # Collect source ranges from display data, fall back to full data if needed
        source_entries = []
        for phase_key, variables in task_data.items():
            if source_name in variables:
                phase_int = _phase_key_to_int(phase_key)
                source_entries.append((phase_int, copy.deepcopy(variables[source_name])))

        if not source_entries:
            for phase_key, variables in full_task_data.items():
                if source_name in variables:
                    phase_int = _phase_key_to_int(phase_key)
                    source_entries.append((phase_int, copy.deepcopy(variables[source_name])))

        if not source_entries:
            if hasattr(self, 'status_bar'):
                self.status_bar.config(text=f"No source ranges found for {source_name}; copy skipped.")
            return

        # Remove existing target entries before copying
        for data_dict in (task_data, full_task_data):
            phases_to_remove = []
            for phase_key, variables in data_dict.items():
                if target_name in variables:
                    del variables[target_name]
                if not variables:
                    phases_to_remove.append(phase_key)
            for phase_key in phases_to_remove:
                del data_dict[phase_key]

        # Apply copied ranges with optional phase offset
        for phase_int, range_spec in source_entries:
            new_phase = (phase_int + offset) % 100
            task_data.setdefault(new_phase, {})[target_name] = copy.deepcopy(range_spec)
            full_task_data.setdefault(new_phase, {})[target_name] = copy.deepcopy(range_spec)

        self.modified = True

        if hasattr(self, 'validate_button'):
            self.validate_button.config(state='normal')

        if hasattr(self, 'status_bar'):
            pretty_source = source_name.replace('_ipsi', ' (ipsi)').replace('_contra', ' (contra)')
            if offset:
                self.status_bar.config(
                    text=(f"Copied {pretty_source} ranges to {target_side} side with "
                          f"{offset}% phase offset for {self.current_task}.")
                )
            else:
                self.status_bar.config(
                    text=f"Copied {pretty_source} ranges to {target_side} side for {self.current_task}."
                )

        # Refresh visible boxes for the updated counterpart without a full validation pass.
        self._refresh_variable_boxes(target_name)

        # Defer full validation until the user explicitly requests it.

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
        self._register_box(box_pass)
        
        box_fail = DraggableBox(
            ax_fail, phase, var_name, min_val, max_val,
            callback=self.on_box_changed,
            color='lightcoral',  # Light red fill for fail column
            edgecolor='black',  # Black outline
            allow_x_drag=True,
            parent=self
        )
        self._register_box(box_fail)
        
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
        if self._missing_task_notice:
            stats_line = f"\n{self._missing_task_notice}"
        elif hasattr(self, 'validation_stats'):
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
        if self._missing_task_notice:
            self._set_status(self._missing_task_notice)
        elif hasattr(self, 'validation_stats'):
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
        self._boxes_by_axis.clear()
        self._axis_aliases.clear()

        # Get all features to display
        variables, variable_labels = self.get_all_features()
        n_vars = len(variables)
        
        # Store current variables for later use
        self.current_variables = variables
        
        # Calculate dynamic figure size
        window_width = self.root.winfo_width() if self.root.winfo_width() > 1 else 1400
        dpi = 100
        fig_width = (window_width - 100) / dpi
        row_height = 2.3
        fig_height = max(n_vars * row_height + 0.8, 4.6)
        
        # Reuse existing figure to maintain canvas connection, just resize and clear
        self.fig.set_size_inches(fig_width, fig_height)
        self.fig.clear()  # Clear all existing content but keep figure connected to canvas
        # Ensure constrained_layout is off so subplots_adjust works properly
        self.fig.set_constrained_layout(False)
        self.fig.subplots_adjust(left=0.07, right=0.985, top=0.96, bottom=0.08, hspace=0.22, wspace=0.12)
        
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

            if var_name and 'angle' in var_name.lower():
                self._add_secondary_angle_axis(ax_pass, y_min, y_max)
                self._add_secondary_angle_axis(ax_fail, y_min, y_max)

        # Add comprehensive title with stats
        self.fig.suptitle(self._get_summary_title(), 
                          fontsize=11, fontweight='bold', y=0.982)
        
        # Update canvas to show traces
        self.canvas.draw()

        # Ensure centralized event hooks are refreshed with the new canvas
        self._bind_canvas_events()
    
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
        self._boxes_by_axis.clear()
        self._active_box = None

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
                            self._register_box(box_pass)
                            
                            # Create draggable box on fail axis (light red rectangle)
                            box_fail = DraggableBox(
                                ax_fail, phase, var_name, min_val, max_val,
                                callback=self.on_box_changed,
                                color='lightcoral',  # Light red fill for fail column
                                edgecolor='black',  # Black outline
                                allow_x_drag=True,
                                parent=self
                            )
                            self._register_box(box_fail)
                            
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
        
        # Update canvas to show boxes and refresh event bindings
        self.canvas.draw()
        self._bind_canvas_events()

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
            self._boxes_by_axis.clear()
        self._axis_aliases.clear()

        # Calculate dynamic figure height based on number of variables
        window_width = self.root.winfo_width() if self.root.winfo_width() > 1 else 1400
        dpi = 100
        fig_width = (window_width - 100) / dpi
        
        # Height per subplot row (in inches)
        row_height = 2.3
        fig_height = max(n_vars * row_height + 0.8, 4.6)

        # Create new figure with dynamic size (like original update_plot())
        from matplotlib.figure import Figure
        self.fig = Figure(figsize=(fig_width, fig_height), dpi=dpi)
        self.fig.subplots_adjust(left=0.07, right=0.985, top=0.96, bottom=0.08, hspace=0.22, wspace=0.12)
        
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
                          fontsize=11, fontweight='bold', y=0.97)

        # Ensure centralized canvas event handlers are connected
        self._bind_canvas_events()

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
