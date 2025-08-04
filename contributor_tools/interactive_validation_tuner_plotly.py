#!/usr/bin/env python3
"""
Interactive Validation Range Tuner - Plotly/Dash Version

A fast, web-based GUI tool for interactively adjusting validation ranges using
Plotly and Dash for improved performance with large datasets.

Features:
- WebGL-accelerated rendering for smooth interaction
- Built-in draggable shapes for validation ranges
- Real-time updates without full redraws
- Efficient handling of thousands of data points

Usage:
    python3 contributor_tools/interactive_validation_tuner_plotly.py
    
    Then open http://localhost:8050 in your web browser
    
Requirements:
    pip install plotly dash pandas pyyaml numpy
"""

import sys
import numpy as np
import pandas as pd
import yaml
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

# Plotly and Dash imports
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

try:
    import dash
    from dash import dcc, html, Input, Output, State, callback_context, ALL, MATCH, no_update, Patch
    from dash.exceptions import PreventUpdate
    DASH_AVAILABLE = True
except ImportError:
    DASH_AVAILABLE = False
    print("Error: dash is not installed. Please install it using:")
    print("  pip install dash")
    sys.exit(1)

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import existing modules
from user_libs.python.locomotion_data import LocomotionData
from user_libs.python.feature_constants import get_feature_list
from internal.config_management.config_manager import ValidationConfigManager
from internal.plot_generation.filters_by_phase_plots import get_task_classification
from contributor_tools.automated_fine_tuning import AutomatedFineTuner


class PlotlyValidationTuner:
    """Fast interactive validation tuner using Plotly and Dash."""
    
    def __init__(self):
        """Initialize the tuner."""
        self.validation_data = {}
        self.dataset_path = None
        self.locomotion_data = None
        self.data_cache = {}
        self.failing_strides_cache = {}
        
        # Auto-load defaults
        self.load_defaults()
        
        # Create Dash app
        self.app = dash.Dash(__name__)
        self.setup_layout()
        self.setup_callbacks()
    
    def load_defaults(self):
        """Load default validation ranges and dataset."""
        # Load default validation ranges
        default_ranges_path = project_root / "contributor_tools" / "validation_ranges" / "default_ranges.yaml"
        if default_ranges_path.exists():
            try:
                with open(default_ranges_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                self.validation_data = {}
                if 'tasks' in config:
                    for task_name, task_data in config['tasks'].items():
                        self.validation_data[task_name] = {}
                        if 'phases' in task_data:
                            for phase_str, variables in task_data['phases'].items():
                                phase = int(phase_str)
                                self.validation_data[task_name][phase] = variables
                print(f"Loaded default validation ranges from {default_ranges_path.name}")
            except Exception as e:
                print(f"Could not load default ranges: {e}")
        
        # Load default dataset
        default_dataset_path = project_root / "converted_datasets" / "umich_2021_phase.parquet"
        if default_dataset_path.exists():
            try:
                self.dataset_path = default_dataset_path
                
                # Try loading with different phase column names
                try:
                    self.locomotion_data = LocomotionData(str(self.dataset_path))
                except ValueError as e:
                    if "Missing required columns: ['phase']" in str(e):
                        self.locomotion_data = LocomotionData(
                            str(self.dataset_path),
                            phase_col='phase_percent'
                        )
                    else:
                        raise e
                
                print(f"Loaded default dataset from {default_dataset_path.name}")
            except Exception as e:
                print(f"Could not load default dataset: {e}")
    
    def setup_layout(self):
        """Setup the Dash app layout."""
        tasks = list(self.validation_data.keys()) if self.validation_data else []
        
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1("Interactive Validation Range Tuner - Fast Plotly Version", 
                       style={'textAlign': 'center', 'marginBottom': 20}),
            ]),
            
            # Controls
            html.Div([
                # Task selection
                html.Div([
                    html.Label("Task: ", style={'marginRight': 10}),
                    dcc.Dropdown(
                        id='task-dropdown',
                        options=[{'label': task, 'value': task} for task in tasks],
                        value=tasks[0] if tasks else None,
                        style={'width': '300px', 'display': 'inline-block'}
                    ),
                ], style={'display': 'inline-block', 'marginRight': 30}),
                
                # Mode selection
                html.Div([
                    html.Label("Mode: ", style={'marginRight': 10}),
                    dcc.RadioItems(
                        id='mode-radio',
                        options=[
                            {'label': 'Kinematic', 'value': 'kinematic'},
                            {'label': 'Kinetic', 'value': 'kinetic'},
                            {'label': 'Segment', 'value': 'segment'},
                        ],
                        value='kinematic',
                        inline=True,
                        style={'display': 'inline-block'}
                    ),
                ], style={'display': 'inline-block', 'marginRight': 30}),
                
                # Main control buttons
                html.Div([
                    html.Button('Update Validation', id='manual-update-btn', n_clicks=0,
                               disabled=True,
                               style={'marginRight': 10}),  # Style will be set dynamically
                    html.Button('Auto-Tune', id='auto-tune-btn', n_clicks=0,
                               style={'marginRight': 10}),
                    html.Button('Reset Ranges', id='reset-btn', n_clicks=0,
                               style={'marginRight': 10}),
                    html.Button('Save Ranges', id='save-btn', n_clicks=0),
                    dcc.Input(id='save-filename', type='text', placeholder='Enter filename (optional)',
                             style={'marginLeft': 10, 'display': 'none'}),
                    dcc.ConfirmDialog(
                        id='save-confirm-dialog',
                        message='',
                    ),
                ], style={'display': 'inline-block'}),
            ], style={'padding': 20, 'backgroundColor': '#f0f0f0', 'marginBottom': 20}),
            
            # Main plot area with scrollable container
            html.Div([
                dcc.Graph(
                    id='main-plot',
                    style={'width': '100%'},
                    config={
                        'editable': True,  # Enable shape editing
                        'edits': {
                            'shapePosition': False,  # Disable horizontal movement
                            'shapeSize': True,  # ENABLE vertical resizing of shapes
                            'annotationPosition': False,  # Disable annotation movement
                            'annotationTail': False,
                            'annotationText': False,
                            'legendPosition': False,
                            'colorbarPosition': False,
                            'colorbarTitleText': False,
                            'axisTitleText': False,
                            'titleText': False
                        },
                        'scrollZoom': False,  # Disable scroll zoom
                        'doubleClick': False,  # Disable double-click zoom
                        'displayModeBar': True,
                        'displaylogo': False,
                        'modeBarButtonsToRemove': [
                            'pan2d', 'lasso2d', 'select2d', 
                            'zoom2d', 'zoomIn2d', 'zoomOut2d',  # Remove all zoom buttons
                            'autoScale2d', 'resetScale2d'
                        ],
                        'toImageButtonOptions': {
                            'format': 'png',
                            'filename': 'validation_ranges',
                            'height': 1080,
                            'width': 1920,
                            'scale': 1
                        }
                    }
                )
            ], style={
                'height': '80vh',
                'overflowY': 'auto',
                'overflowX': 'hidden',
                'backgroundColor': 'white',
                'border': '1px solid #ddd',
                'padding': '10px'
            }),
            
            # Hidden store for tracking changes
            dcc.Store(id='has-pending-changes', data=False),
            
            # Status bar with help text
            html.Div([
                html.Span(id='status-bar', children="Ready. Loaded default files.", 
                         style={'marginRight': 20}),
                html.Span("💡 Tip: Click and drag the TOP or BOTTOM edges of validation boxes to adjust ranges", 
                         style={'color': '#666', 'fontStyle': 'italic'})
            ], style={'padding': 10, 'backgroundColor': '#e0e0e0', 
                     'position': 'fixed', 'bottom': 0, 'width': '100%'}),
        ])
    
    def get_variables_for_mode(self, mode):
        """Get variables and labels for a given mode."""
        if mode == 'kinematic':
            variables = [
                'hip_flexion_angle_ipsi_rad',
                'knee_flexion_angle_ipsi_rad',
                'ankle_dorsiflexion_angle_ipsi_rad'
            ]
            labels = ['Hip Flexion', 'Knee Flexion', 'Ankle Dorsiflexion']
        elif mode == 'kinetic':
            variables = [
                'hip_flexion_moment_ipsi_Nm',
                'knee_flexion_moment_ipsi_Nm',
                'ankle_dorsiflexion_moment_ipsi_Nm'
            ]
            labels = ['Hip Moment', 'Knee Moment', 'Ankle Moment']
        elif mode == 'segment':
            variables = [
                'pelvis_tilt_angle_rad', 'pelvis_obliquity_angle_rad', 'pelvis_rotation_angle_rad',
                'trunk_flexion_angle_rad', 'trunk_lateral_angle_rad', 'trunk_rotation_angle_rad',
                'thigh_angle_ipsi_rad', 'shank_angle_ipsi_rad', 'foot_angle_ipsi_rad'
            ]
            labels = [
                'Pelvis Tilt', 'Pelvis Obliquity', 'Pelvis Rotation',
                'Trunk Flexion', 'Trunk Lateral', 'Trunk Rotation',
                'Thigh', 'Shank', 'Foot'
            ]
        else:
            variables = []
            labels = []
        
        return variables, labels
    
    def load_data_for_variable(self, task, var_name):
        """Load and cache data for a specific variable."""
        cache_key = f"{task}_{var_name}"
        
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]
        
        if not self.locomotion_data:
            return np.array([])
        
        all_data = []
        try:
            subjects = self.locomotion_data.get_subjects()
            for subject in subjects:
                try:
                    cycles_data, feature_names = self.locomotion_data.get_cycles(
                        subject=subject,
                        task=task,
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
            else:
                all_data = np.array([])
        except:
            all_data = np.array([])
        
        return all_data
    
    def validate_strides(self, task, variables):
        """Validate strides and return failing indices for each variable."""
        if not self.locomotion_data or task not in self.validation_data:
            return {}
        
        # Check cache
        cache_key = f"{task}_{'-'.join(variables)}"
        if cache_key in self.failing_strides_cache:
            # Check if validation data has changed
            if not hasattr(self, '_last_validation_data') or self._last_validation_data != self.validation_data:
                self._last_validation_data = self.validation_data.copy()
            else:
                return self.failing_strides_cache[cache_key]
        
        failing_strides = {}
        task_data = self.validation_data[task]
        
        for var_name in variables:
            failing_strides[var_name] = set()
            data = self.load_data_for_variable(task, var_name)
            
            if len(data) == 0:
                continue
            
            # Check each stride
            for stride_idx in range(len(data)):
                stride_data = data[stride_idx]
                
                # Check each phase
                for phase_str in task_data.keys():
                    if not str(phase_str).isdigit():
                        continue
                    phase = int(phase_str)
                    
                    if var_name in task_data[phase_str]:  # Use string key
                        range_data = task_data[phase_str][var_name]
                        if 'min' in range_data and 'max' in range_data:
                            min_val = range_data['min']
                            max_val = range_data['max']
                            
                            if min_val is None or max_val is None:
                                continue
                            
                            # Map phase to index
                            phase_idx = int(phase * 1.49)  # 0->0, 100->149
                            
                            # Check if value is outside range
                            if stride_data[phase_idx] < min_val or stride_data[phase_idx] > max_val:
                                failing_strides[var_name].add(stride_idx)
                                break  # This stride fails
        
        # Cache the result
        self.failing_strides_cache[cache_key] = failing_strides
        return failing_strides
    
    def create_plot(self, task, mode):
        """Create the main plot with all subplots."""
        if not task or task not in self.validation_data:
            return go.Figure()
        
        variables, labels = self.get_variables_for_mode(mode)
        n_vars = len(variables)
        
        # Fixed height per subplot for consistent sizing
        subplot_height = 400  # pixels per subplot (increased for better visibility)
        total_height = subplot_height * n_vars + 200  # Add space for titles and spacing
        
        # Create subplots with 2 columns (pass/fail)
        fig = make_subplots(
            rows=n_vars, cols=2,
            subplot_titles=[f"{label} - Pass" if i % 2 == 0 else f"{label} - Fail" 
                          for label in labels for i in range(2)],
            vertical_spacing=0.05 if n_vars > 3 else 0.06,  # More vertical spacing
            horizontal_spacing=0.08,  # Slightly more horizontal space
            row_heights=[subplot_height] * n_vars  # Fixed height per row
        )
        
        # Store shape mapping for later updates
        self.shape_mapping = {}  # Maps shape index to (var_name, phase, col)
        
        # Get failing strides
        failing_strides = self.validate_strides(task, variables)
        
        # Plot each variable
        phase_percent = np.linspace(0, 100, 150)
        
        for i, (var_name, label) in enumerate(zip(variables, labels)):
            row = i + 1
            
            # Load data
            data = self.load_data_for_variable(task, var_name)
            if len(data) == 0:
                continue
            
            failed_indices = failing_strides.get(var_name, set())
            
            # Plot passing strides (left column)
            pass_count = 0
            pass_traces = []
            for stride_idx in range(len(data)):
                if stride_idx not in failed_indices:
                    pass_traces.append(data[stride_idx])
                    pass_count += 1
                    
                    # Add trace (sample every 5th for performance)
                    if pass_count % 5 == 0 or pass_count <= 10:
                        fig.add_trace(
                            go.Scattergl(
                                x=phase_percent,
                                y=data[stride_idx],
                                mode='lines',
                                line=dict(color='green', width=0.5),
                                opacity=0.2,
                                showlegend=False,
                                hoverinfo='skip'
                            ),
                            row=row, col=1
                        )
            
            # Add mean of passing strides
            if pass_traces:
                mean_pass = np.mean(pass_traces, axis=0)
                fig.add_trace(
                    go.Scattergl(
                        x=phase_percent,
                        y=mean_pass,
                        mode='lines',
                        line=dict(color='darkgreen', width=2),
                        name=f'Mean Pass ({pass_count})',
                        showlegend=False
                    ),
                    row=row, col=1
                )
            
            # Plot failing strides (right column)
            fail_count = 0
            fail_traces = []
            for stride_idx in range(len(data)):
                if stride_idx in failed_indices:
                    fail_traces.append(data[stride_idx])
                    fail_count += 1
                    
                    # Add trace (sample for performance)
                    if fail_count % 5 == 0 or fail_count <= 10:
                        fig.add_trace(
                            go.Scattergl(
                                x=phase_percent,
                                y=data[stride_idx],
                                mode='lines',
                                line=dict(color='red', width=0.5),
                                opacity=0.3,
                                showlegend=False,
                                hoverinfo='skip'
                            ),
                            row=row, col=2
                        )
            
            # Add mean of failing strides
            if fail_traces:
                mean_fail = np.mean(fail_traces, axis=0)
                fig.add_trace(
                    go.Scattergl(
                        x=phase_percent,
                        y=mean_fail,
                        mode='lines',
                        line=dict(color='darkred', width=2),
                        name=f'Mean Fail ({fail_count})',
                        showlegend=False
                    ),
                    row=row, col=2
                )
            
            # Add validation range boxes as editable shapes
            if task in self.validation_data:
                task_data = self.validation_data[task]
                phases = sorted([int(p) for p in task_data.keys() if str(p).isdigit()])
                
                shape_idx = len(fig.layout.shapes) if hasattr(fig.layout, 'shapes') else 0
                
                for phase in phases:
                    if phase in task_data and var_name in task_data[phase]:
                        range_data = task_data[phase][var_name]
                        if 'min' in range_data and 'max' in range_data:
                            min_val = range_data['min']
                            max_val = range_data['max']
                            
                            if min_val is None or max_val is None:
                                continue
                            
                            # Add rectangles to both columns
                            for col in [1, 2]:
                                color = 'rgba(144, 238, 144, 0.4)' if col == 1 else 'rgba(240, 128, 128, 0.4)'
                                
                                # Store mapping for this shape
                                self.shape_mapping[shape_idx] = {
                                    'var_name': var_name,
                                    'phase': phase,
                                    'col': col,
                                    'row': row
                                }
                                
                                fig.add_shape(
                                    type="rect",
                                    x0=phase - 2.5, x1=phase + 2.5,  # Wider boxes (5 units) for easier edge clicking
                                    y0=min_val, y1=max_val,
                                    line=dict(color="black", width=2),  # Thicker border for visibility
                                    fillcolor=color,
                                    opacity=0.35,
                                    editable=True,
                                    row=row, col=col,
                                    name=f"{var_name}_{phase}_{col}"
                                )
                                
                                shape_idx += 1
                                
                                # Add phase label to the right of box
                                fig.add_annotation(
                                    x=phase + 4,  # Position further right due to wider box
                                    y=(min_val + max_val) / 2,  # Center vertically in box
                                    text=f"<b>{phase}%</b>",
                                    showarrow=False,
                                    font=dict(size=14, color="darkblue"),  # Larger, darker font
                                    bgcolor="rgba(255, 255, 255, 0.8)",  # White background for readability
                                    row=row, col=col,
                                    xref=f"x{(row-1)*2 + col}" if row > 1 or col > 1 else "x",
                                    yref=f"y{(row-1)*2 + col}" if row > 1 or col > 1 else "y"
                                )
                                
                                # Add min/max value labels
                                fig.add_annotation(
                                    x=phase, y=min_val - (max_val - min_val) * 0.05,
                                    text=f"{min_val:.3f}",
                                    showarrow=False,
                                    font=dict(size=8, color="gray"),
                                    row=row, col=col
                                )
                                
                                fig.add_annotation(
                                    x=phase, y=max_val + (max_val - min_val) * 0.02,
                                    text=f"{max_val:.3f}",
                                    showarrow=False,
                                    font=dict(size=8, color="gray"),
                                    row=row, col=col
                                )
            
            # Update subplot titles with counts
            fig.layout.annotations[i*2].text = f"{label} - ✓ Pass ({pass_count})"
            fig.layout.annotations[i*2+1].text = f"{label} - ✗ Fail ({fail_count})"
        
        # Update layout with fixed sizing and clean background
        fig.update_layout(
            title=f"{task.replace('_', ' ').title()} - {mode.capitalize()} Validation Ranges",
            height=total_height,
            showlegend=False,
            hovermode='closest',
            margin=dict(l=60, r=20, t=80, b=40),  # Reduce margins
            autosize=True,
            plot_bgcolor='white',  # Plain white background
            paper_bgcolor='white',  # Plain white paper
            dragmode=False  # Disable drag to zoom (shape editing still works)
        )
        
        # Update axes
        for i in range(n_vars):
            for col in [1, 2]:
                fig.update_xaxes(
                    title_text="Gait Phase (%)" if i == n_vars - 1 else "",
                    range=[-5, 105],
                    row=i+1, col=col,
                    showgrid=False,  # No grid
                    zeroline=False,
                    showline=True,
                    linewidth=1,
                    linecolor='black'
                )
                fig.update_yaxes(
                    title_text="rad" if mode != 'kinetic' else "Nm",
                    row=i+1, col=col,
                    showgrid=False,  # No grid
                    zeroline=False,
                    showline=True,
                    linewidth=1,
                    linecolor='black'
                )
        
        return fig
    
    def setup_callbacks(self):
        """Setup Dash callbacks for interactivity."""
        
        @self.app.callback(
            [Output('main-plot', 'figure'),
             Output('status-bar', 'children'),
             Output('has-pending-changes', 'data'),
             Output('manual-update-btn', 'disabled'),
             Output('manual-update-btn', 'style')],
            [Input('task-dropdown', 'value'),
             Input('mode-radio', 'value'),
             Input('manual-update-btn', 'n_clicks'),
             Input('reset-btn', 'n_clicks'),
             Input('main-plot', 'relayoutData')],
            [State('main-plot', 'figure'),
             State('has-pending-changes', 'data')]
        )
        def update_plot(task, mode, update_clicks, reset_clicks, relayout_data, 
                       current_figure, has_pending_changes):
            """Update the plot based on selections and shape edits."""
            ctx = callback_context
            
            if not ctx.triggered:
                return no_update, no_update, no_update, no_update, no_update
            
            trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
            
            # Define button styles
            enabled_style = {
                'marginRight': 10,
                'backgroundColor': '#4CAF50',
                'color': 'white',
                'fontWeight': 'bold',
                'cursor': 'pointer',
                'border': 'none',
                'padding': '8px 16px',
                'borderRadius': '4px'
            }
            disabled_style = {
                'marginRight': 10,
                'backgroundColor': '#cccccc',
                'color': '#666666',
                'fontWeight': 'bold',
                'cursor': 'not-allowed',
                'border': 'none',
                'padding': '8px 16px',
                'borderRadius': '4px'
            }
            
            # Handle shape edits - update paired box and mark as pending
            if trigger_id == 'main-plot' and relayout_data and any(key.startswith('shapes') for key in relayout_data):
                status, patched_figure = self.handle_shape_edit(relayout_data, task, mode, current_figure)
                if "updated" in status.lower():
                    # Return patched figure to update paired box immediately
                    if patched_figure is not None:
                        return patched_figure, "Changes pending - click 'Update Validation' to apply", True, False, enabled_style
                    return no_update, "Changes pending - click 'Update Validation' to apply", True, False, enabled_style
                return no_update, status, False, True, disabled_style
            
            # Handle manual update button - apply changes and redraw
            if trigger_id == 'manual-update-btn' and has_pending_changes:
                self.failing_strides_cache = {}
                fig = self.create_plot(task, mode)
                return fig, "Validation updated", False, True, disabled_style
            
            # Handle reset - reload original ranges and update
            if trigger_id == 'reset-btn':
                # Reload original validation ranges
                self.load_defaults()
                self.failing_strides_cache = {}
                if task:
                    fig = self.create_plot(task, mode)
                    return fig, "Ranges reset to defaults", False, True, disabled_style
                return go.Figure(), "No task selected", False, True, disabled_style
            
            # Handle task/mode changes - full redraw
            if trigger_id in ['task-dropdown', 'mode-radio']:
                if task:
                    fig = self.create_plot(task, mode)
                    return fig, f"Displaying {task} - {mode}", False, True, disabled_style
                return go.Figure(), "No task selected", False, True, disabled_style
            
            return no_update, no_update, no_update, no_update, no_update
        
        @self.app.callback(
            Output('status-bar', 'children', allow_duplicate=True),
            Input('auto-tune-btn', 'n_clicks'),
            [State('task-dropdown', 'value'),
             State('mode-radio', 'value')],
            prevent_initial_call=True
        )
        def auto_tune(n_clicks, task, mode):
            """Run auto-tuning."""
            if n_clicks and task and self.dataset_path:
                try:
                    tuner = AutomatedFineTuner(str(self.dataset_path), mode=mode)
                    results = tuner.run_statistical_tuning(
                        method='percentile_95',
                        save_ranges=False,
                        save_report=False
                    )
                    
                    if results['success'] and task in results['validation_ranges']:
                        self.validation_data[task] = results['validation_ranges'][task]
                        # Clear cache
                        self.failing_strides_cache = {}
                        self.data_cache = {}
                        return f"Auto-tuning complete for {task} - {mode}"
                    else:
                        return f"Auto-tuning failed: No data for {task}"
                except Exception as e:
                    return f"Auto-tuning error: {str(e)}"
            
            return no_update
        
        @self.app.callback(
            Output('save-confirm-dialog', 'displayed'),
            Output('save-confirm-dialog', 'message'),
            Input('save-btn', 'n_clicks'),
            prevent_initial_call=True
        )
        def show_save_dialog(n_clicks):
            """Show save dialog when save button clicked."""
            if n_clicks:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                default_name = f"tuned_ranges_{timestamp}.yaml"
                return True, f"Save validation ranges as:\n{default_name}\n\n(Click OK to save with this name, or Cancel to abort)"
            return False, ""
        
        @self.app.callback(
            Output('status-bar', 'children', allow_duplicate=True),
            Input('save-confirm-dialog', 'submit_n_clicks'),
            prevent_initial_call=True
        )
        def save_ranges_confirmed(submit_clicks):
            """Save validation ranges after confirmation."""
            if submit_clicks and self.validation_data:
                try:
                    # Generate filename with timestamp
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    output_file = project_root / "contributor_tools" / "validation_ranges" / f"tuned_ranges_{timestamp}.yaml"
                    
                    # Prepare YAML structure
                    config = {
                        'version': '2.0',
                        'generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'source': 'Interactive Validation Tuner (Plotly)',
                        'tasks': {}
                    }
                    
                    for task_name, task_data in self.validation_data.items():
                        config['tasks'][task_name] = {'phases': {}}
                        for phase, variables in task_data.items():
                            config['tasks'][task_name]['phases'][str(phase)] = variables
                    
                    # Save to file
                    with open(output_file, 'w') as f:
                        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
                    
                    return f"✓ Saved validation ranges to {output_file.name}"
                except Exception as e:
                    return f"❌ Save error: {str(e)}"
            
            return no_update
    
    def handle_shape_edit(self, relayout_data, task, mode, current_figure=None):
        """Handle edits to validation range shapes and sync paired boxes."""
        if not task or task not in self.validation_data:
            return "No task selected", None
        
        if not hasattr(self, 'shape_mapping'):
            return "Shape mapping not initialized", None
        
        updated = False
        patched_figure = None
        
        # Parse shape edits from relayout_data
        for key, value in relayout_data.items():
            if key.startswith('shapes['):
                # Extract shape index and property
                # Format: shapes[index].property
                import re
                match = re.match(r'shapes\[(\d+)\]\.(\w+)', key)
                if match:
                    shape_idx = int(match.group(1))
                    property_name = match.group(2)
                    
                    # Get shape info from mapping
                    if shape_idx in self.shape_mapping:
                        shape_info = self.shape_mapping[shape_idx]
                        var_name = shape_info['var_name']
                        phase = shape_info['phase']
                        col = shape_info['col']
                        
                        # Initialize if needed
                        if task not in self.validation_data:
                            self.validation_data[task] = {}
                        if phase not in self.validation_data[task]:
                            self.validation_data[task][phase] = {}
                        if var_name not in self.validation_data[task][phase]:
                            self.validation_data[task][phase][var_name] = {'min': 0, 'max': 1}
                        
                        # Update based on property
                        if property_name in ['x0', 'x1']:
                            # Ignore x-axis changes (width editing disabled)
                            continue
                        
                        elif property_name == 'y0':
                            # Min value changed
                            self.validation_data[task][phase][var_name]['min'] = value
                            updated = True
                            
                            # Find and update paired box
                            if current_figure and 'layout' in current_figure and 'shapes' in current_figure['layout']:
                                # Find the paired shape (opposite column, same variable and phase)
                                paired_col = 2 if col == 1 else 1
                                for idx, mapping in self.shape_mapping.items():
                                    if (mapping['var_name'] == var_name and 
                                        mapping['phase'] == phase and 
                                        mapping['col'] == paired_col):
                                        # Create a patch to update the paired shape
                                        patched_figure = Patch()
                                        patched_figure['layout']['shapes'][idx]['y0'] = value
                                        break
                        
                        elif property_name == 'y1':
                            # Max value changed
                            self.validation_data[task][phase][var_name]['max'] = value
                            updated = True
                            
                            # Find and update paired box
                            if current_figure and 'layout' in current_figure and 'shapes' in current_figure['layout']:
                                # Find the paired shape (opposite column, same variable and phase)
                                paired_col = 2 if col == 1 else 1
                                for idx, mapping in self.shape_mapping.items():
                                    if (mapping['var_name'] == var_name and 
                                        mapping['phase'] == phase and 
                                        mapping['col'] == paired_col):
                                        # Create a patch to update the paired shape
                                        patched_figure = Patch()
                                        patched_figure['layout']['shapes'][idx]['y1'] = value
                                        break
        
        if updated:
            # Clear validation cache
            self.failing_strides_cache = {}
            return f"Validation ranges updated - {task} {mode}", patched_figure
        
        return "No changes detected", None
    
    def run(self, debug=True, port=8050):
        """Run the Dash app."""
        print(f"\n{'='*60}")
        print("Interactive Validation Tuner - Fast Plotly Version")
        print(f"{'='*60}")
        print(f"Starting web server on http://localhost:{port}")
        print("Open this URL in your web browser to use the tool")
        print("Press Ctrl+C to stop the server")
        print(f"{'='*60}\n")
        
        self.app.run(debug=debug, port=port)


def main():
    """Main entry point."""
    if not DASH_AVAILABLE:
        print("Error: Required packages not installed.")
        print("Please install: pip install plotly dash")
        return 1
    
    app = PlotlyValidationTuner()
    app.run(debug=False)  # Set debug=False for production
    return 0


if __name__ == "__main__":
    sys.exit(main())