#!/usr/bin/env python3
"""
Enhanced Image Generator with Embedded Config

Generates validation plots with embedded configuration data visible in the image.
Each image becomes self-documenting by displaying the exact ranges used.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml
from datetime import datetime


class ValidationImageGenerator:
    """
    Generates validation images with embedded configuration data.
    
    Each generated image includes:
    - The validation plot itself
    - A config panel showing the ranges used
    - Metadata about generation (date, dataset, method)
    """
    
    def __init__(self, config_manager):
        """
        Initialize the image generator.
        
        Args:
            config_manager: ValidationConfigManager instance
        """
        self.config_manager = config_manager
    
    def create_filters_by_phase_with_config(self, 
                                           task_name: str,
                                           mode: str,
                                           output_dir: str,
                                           data: Optional[np.ndarray] = None) -> str:
        """
        Create filters by phase plot with embedded config panel.
        
        Args:
            task_name: Name of the task (e.g., 'level_walking')
            mode: 'kinematic' or 'kinetic'
            output_dir: Directory to save the plot
            data: Optional actual data to overlay
            
        Returns:
            Path to the saved image
        """
        # Load validation ranges and metadata
        validation_ranges = self.config_manager.get_task_ranges(mode, task_name)
        metadata = self.config_manager.get_metadata(mode)
        
        # Create figure with custom layout
        fig = plt.figure(figsize=(20, 12))
        
        # Use GridSpec for custom layout
        # Left 75%: Main plot, Right 25%: Config panel
        gs = GridSpec(1, 2, figure=fig, width_ratios=[3, 1])
        
        # Main plot area
        ax_main = fig.add_subplot(gs[0, 0])
        
        # Config panel area
        ax_config = fig.add_subplot(gs[0, 1])
        ax_config.axis('off')
        
        # Draw the main validation plot
        self._draw_validation_plot(ax_main, task_name, mode, validation_ranges, data)
        
        # Draw the config panel
        self._draw_config_panel(ax_config, task_name, mode, validation_ranges, metadata)
        
        # Overall title
        fig.suptitle(f'{task_name.replace("_", " ").title()} - {mode.title()} Validation',
                    fontsize=16, fontweight='bold')
        
        # Save the figure
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        filename = f"{task_name}_{mode}_filters_by_phase_with_config.png"
        filepath = output_path / filename
        
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight', 
                   metadata={'Software': 'Locomotion Data Standardization',
                            'Generated': datetime.now().isoformat(),
                            'Task': task_name,
                            'Mode': mode})
        plt.close()
        
        return str(filepath)
    
    def _draw_validation_plot(self, ax, task_name: str, mode: str, 
                             validation_ranges: Dict, data: Optional[np.ndarray]):
        """
        Draw the main validation plot (simplified version).
        
        This is a placeholder - in practice, you'd call the existing
        filters_by_phase_plots functions here.
        """
        phases = [0, 25, 50, 75]
        
        # Example: Plot one variable's ranges
        if validation_ranges and phases[0] in validation_ranges:
            phase_0_data = validation_ranges[phases[0]]
            if phase_0_data:
                # Get first variable for demonstration
                first_var = list(phase_0_data.keys())[0]
                
                # Collect min/max values across phases
                mins = []
                maxs = []
                for phase in phases:
                    if phase in validation_ranges and first_var in validation_ranges[phase]:
                        mins.append(validation_ranges[phase][first_var].get('min', 0))
                        maxs.append(validation_ranges[phase][first_var].get('max', 0))
                    else:
                        mins.append(0)
                        maxs.append(0)
                
                # Plot the ranges
                ax.fill_between(phases, mins, maxs, alpha=0.3, color='blue', 
                              label=f'{first_var} range')
                ax.plot(phases, mins, 'b-', marker='o', label='Min')
                ax.plot(phases, maxs, 'r-', marker='o', label='Max')
                
                ax.set_xlabel('Gait Phase (%)')
                ax.set_ylabel('Value (rad or Nm)')
                ax.set_title(f'Validation Ranges - {first_var}')
                ax.legend()
                ax.grid(True, alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'No validation data available', 
                   ha='center', va='center', transform=ax.transAxes)
    
    def _draw_config_panel(self, ax, task_name: str, mode: str,
                          validation_ranges: Dict, metadata: Dict):
        """
        Draw the configuration panel showing the ranges and metadata.
        """
        # Title for config panel
        y_pos = 0.95
        ax.text(0.5, y_pos, 'Configuration', fontsize=14, fontweight='bold',
               ha='center', transform=ax.transAxes)
        
        y_pos -= 0.05
        ax.text(0.5, y_pos, '─' * 30, fontsize=10, ha='center',
               transform=ax.transAxes, family='monospace')
        
        # Metadata section
        y_pos -= 0.04
        ax.text(0.1, y_pos, 'Metadata:', fontsize=11, fontweight='bold',
               transform=ax.transAxes)
        
        y_pos -= 0.03
        if metadata:
            for key, value in metadata.items():
                if key not in ['tasks', 'version']:  # Skip these for display
                    display_key = key.replace('_', ' ').title()
                    # Truncate long values
                    display_value = str(value)[:25] + '...' if len(str(value)) > 25 else str(value)
                    ax.text(0.1, y_pos, f'• {display_key}:', fontsize=9,
                           transform=ax.transAxes)
                    y_pos -= 0.025
                    ax.text(0.15, y_pos, f'{display_value}', fontsize=8,
                           transform=ax.transAxes, style='italic')
                    y_pos -= 0.03
        
        # Validation Ranges section
        y_pos -= 0.02
        ax.text(0.1, y_pos, f'Ranges ({task_name}):', fontsize=11, fontweight='bold',
               transform=ax.transAxes)
        
        y_pos -= 0.03
        
        # Display sample ranges for each phase
        phases = [0, 25, 50, 75]
        for phase in phases:
            if phase in validation_ranges:
                ax.text(0.1, y_pos, f'Phase {phase}%:', fontsize=10,
                       transform=ax.transAxes, color='darkblue')
                y_pos -= 0.025
                
                # Show first few variables as examples
                phase_data = validation_ranges[phase]
                var_count = 0
                for var_name, var_range in phase_data.items():
                    if var_count >= 2:  # Only show first 2 variables to save space
                        remaining = len(phase_data) - 2
                        if remaining > 0:
                            ax.text(0.15, y_pos, f'... +{remaining} more', 
                                   fontsize=8, transform=ax.transAxes,
                                   style='italic', color='gray')
                            y_pos -= 0.025
                        break
                    
                    # Shorten variable name
                    short_name = var_name.replace('_ipsi', '').replace('_contra', 'c')
                    if len(short_name) > 20:
                        short_name = short_name[:17] + '...'
                    
                    min_val = var_range.get('min', 'N/A')
                    max_val = var_range.get('max', 'N/A')
                    
                    # Format numbers
                    if isinstance(min_val, (int, float)) and not np.isnan(min_val):
                        min_str = f'{min_val:.2f}'
                    else:
                        min_str = 'N/A'
                    
                    if isinstance(max_val, (int, float)) and not np.isnan(max_val):
                        max_str = f'{max_val:.2f}'
                    else:
                        max_str = 'N/A'
                    
                    ax.text(0.15, y_pos, f'{short_name}:', fontsize=8,
                           transform=ax.transAxes)
                    y_pos -= 0.02
                    ax.text(0.2, y_pos, f'[{min_str}, {max_str}]', fontsize=8,
                           transform=ax.transAxes, family='monospace',
                           color='darkgreen')
                    y_pos -= 0.025
                    var_count += 1
                
                y_pos -= 0.01
        
        # Add a note at the bottom
        ax.text(0.5, 0.02, 'Config embedded in image', fontsize=8,
               ha='center', transform=ax.transAxes, style='italic',
               color='gray')
    
    def create_config_summary_image(self, mode: str, output_dir: str) -> str:
        """
        Create a summary image showing all config data for a mode.
        
        This creates a purely textual image that displays all the
        configuration data in a readable format.
        
        Args:
            mode: 'kinematic' or 'kinetic'
            output_dir: Directory to save the image
            
        Returns:
            Path to the saved image
        """
        # Load all validation ranges
        all_ranges = self.config_manager.load_validation_ranges(mode)
        metadata = self.config_manager.get_metadata(mode)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 16))
        ax.axis('off')
        
        # Title
        y_pos = 0.98
        ax.text(0.5, y_pos, f'{mode.title()} Validation Configuration',
               fontsize=16, fontweight='bold', ha='center',
               transform=ax.transAxes)
        
        y_pos -= 0.03
        ax.text(0.5, y_pos, '═' * 60, fontsize=10, ha='center',
               transform=ax.transAxes, family='monospace')
        
        # Metadata
        y_pos -= 0.03
        ax.text(0.05, y_pos, 'Configuration Metadata:', fontsize=12,
               fontweight='bold', transform=ax.transAxes)
        
        y_pos -= 0.02
        for key, value in metadata.items():
            if key != 'tasks':
                ax.text(0.07, y_pos, f'{key}: {value}', fontsize=10,
                       transform=ax.transAxes, family='monospace')
                y_pos -= 0.015
        
        # Tasks
        y_pos -= 0.02
        ax.text(0.05, y_pos, 'Task Configurations:', fontsize=12,
               fontweight='bold', transform=ax.transAxes)
        
        y_pos -= 0.02
        for task_name in sorted(all_ranges.keys()):
            ax.text(0.07, y_pos, f'▶ {task_name}', fontsize=11,
                   fontweight='bold', transform=ax.transAxes,
                   color='darkblue')
            y_pos -= 0.015
            
            # Show summary statistics for this task
            task_data = all_ranges[task_name]
            num_phases = len(task_data)
            num_vars = len(next(iter(task_data.values()))) if task_data else 0
            
            ax.text(0.1, y_pos, f'Phases: {num_phases}, Variables: {num_vars}',
                   fontsize=9, transform=ax.transAxes, style='italic')
            y_pos -= 0.02
        
        # Save
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        filename = f"{mode}_config_summary.png"
        filepath = output_path / filename
        
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return str(filepath)