#!/usr/bin/env python3
"""
Validation Plots Generator

Generates validation visualization plots from YAML configuration:
1. Forward kinematics range visualization plots (phase 0%, 25%, 50%, 75%)
2. Filters by phase validation plots

Usage:
    python generate_validation_plots.py [--tasks task1 task2 ...] [--config path/to/config.yaml]
    
Examples:
    python generate_validation_plots.py                    # Generate all plots
    python generate_validation_plots.py --tasks level_walking incline_walking
    python generate_validation_plots.py --config custom_ranges.yaml
"""

import os
from pathlib import Path
from typing import List, Optional
import argparse

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import validation modules
from lib.validation.config_manager import ValidationConfigManager
from lib.validation.validation_offset_utils import (
    apply_contralateral_offset_kinematic,
    apply_contralateral_offset_kinetic
)
from lib.validation.forward_kinematics_plots import KinematicPoseGenerator
from lib.validation.filters_by_phase_plots import create_filters_by_phase_plot

class ValidationPlotsGenerator:
    """
    Unified generator for all validation plots referenced in the kinematic and kinetic specifications.
    Hardcoded paths for simplicity and reliability.
    """
    
    def __init__(self, mode: str = 'kinematic', config_path: Optional[Path] = None):
        """Initialize with config manager.
        
        Args:
            mode: 'kinematic', 'kinetic', or 'all' to determine which plots to generate
            config_path: Optional path to custom config file
        """
        self.mode = mode
        
        # Project root 
        self.project_root = Path(__file__).parent.parent
        
        # Initialize config manager
        if config_path:
            # Use custom config directory
            self.config_manager = ValidationConfigManager(config_path.parent)
        else:
            self.config_manager = ValidationConfigManager()
        
        # Output directory where markdown files expect the images
        self.output_dir = self.project_root / "docs" / "reference" / "standard_spec" / "validation"
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize generators (only for kinematic mode)
        if mode == 'kinematic':
            self.pose_generator = KinematicPoseGenerator()
        
        print(f"✅ Initialized ValidationPlotsGenerator ({mode} mode)")
        print(f"   📁 Config dir: {self.config_manager.config_dir}")
        print(f"   📁 Output dir: {self.output_dir}")
    
    def load_validation_data(self) -> dict:
        """Load validation expectations from YAML config."""
        print(f"📊 Loading validation data from config")
        
        try:
            # Load from config manager
            validation_data = self.config_manager.load_validation_ranges(self.mode)
            
            # Apply contralateral offset for all gait-based tasks
            processed_data = {}
            for task_name, task_data in validation_data.items():
                if self.mode == 'kinematic':
                    processed_data[task_name] = apply_contralateral_offset_kinematic(task_data, task_name)
                else:  # kinetic
                    processed_data[task_name] = apply_contralateral_offset_kinetic(task_data, task_name)
            
            print(f"✅ Successfully loaded validation data for {len(processed_data)} tasks: {list(processed_data.keys())}")
            return processed_data
        except Exception as e:
            raise RuntimeError(f"Failed to load validation data: {e}")
    
    def generate_forward_kinematics_plots(self, tasks: Optional[List[str]] = None) -> List[str]:
        """
        Generate forward kinematics range visualization plots.
        Only available for kinematic mode.
        
        Creates: {task_name}_forward_kinematics_phase_{00,25,50,75}_range.png
        
        Args:
            tasks: Optional list of specific tasks. If None, generates for all tasks.
            
        Returns:
            List of generated file paths
        """
        if self.mode != 'kinematic':
            print("⚠️  Forward kinematics plots are only available for kinematic mode")
            return []
            
        print("\n🎨 Generating Forward Kinematics Range Visualization Plots...")
        
        validation_data = self.load_validation_data()
        
        # Determine tasks to process
        if tasks:
            # Validate requested tasks exist
            missing_tasks = [task for task in tasks if task not in validation_data]
            if missing_tasks:
                raise ValueError(f"Requested tasks not found in validation data: {missing_tasks}")
            tasks_to_process = tasks
        else:
            tasks_to_process = list(validation_data.keys())
        
        generated_files = []
        
        for task_name in tasks_to_process:
            print(f"  📐 Generating forward kinematics plots for: {task_name}")
            
            try:
                # Strip units from variable names for forward kinematics generator
                # The forward kinematics code expects variables without _rad suffix
                cleaned_ranges = {}
                for phase, variables in validation_data[task_name].items():
                    cleaned_ranges[phase] = {}
                    for var_name, var_range in variables.items():
                        # Only include angle variables and strip _rad suffix
                        if 'angle' in var_name:
                            clean_name = var_name.replace('_rad', '')
                            cleaned_ranges[phase][clean_name] = var_range
                
                # Generate plots for this task using the cleaned validation data
                task_files = self.pose_generator.generate_task_validation_images(
                    task_name=task_name,
                    validation_ranges=cleaned_ranges,
                    output_dir=str(self.output_dir)
                )
                
                generated_files.extend(task_files)
                print(f"    ✅ Generated {len(task_files)} phase plots")
                
            except Exception as e:
                print(f"    ❌ Failed to generate plots for {task_name}: {e}")
                continue
        
        print(f"✅ Forward kinematics plots complete: {len(generated_files)} files generated")
        return generated_files
    
    def generate_filters_by_phase_plots(self, tasks: Optional[List[str]] = None) -> List[str]:
        """
        Generate filters by phase validation plots.
        
        Creates: {task_name}_{kinematic|kinetic}_filters_by_phase.png
        
        Args:
            tasks: Optional list of specific tasks. If None, generates for all tasks.
            
        Returns:
            List of generated file paths
        """
        print(f"\n📊 Generating Filters by Phase Validation Plots ({self.mode} mode)...")
        
        validation_data = self.load_validation_data()
        
        # Determine tasks to process
        if tasks:
            # Validate requested tasks exist
            missing_tasks = [task for task in tasks if task not in validation_data]
            if missing_tasks:
                raise ValueError(f"Requested tasks not found in validation data: {missing_tasks}")
            tasks_to_process = tasks
        else:
            tasks_to_process = list(validation_data.keys())
        
        generated_files = []
        
        for task_name in tasks_to_process:
            print(f"  📈 Generating filters by phase plot for: {task_name}")
            
            try:
                # Create the plot (no actual data overlay, just the validation ranges)
                plot_path = create_filters_by_phase_plot(
                    validation_data=validation_data,
                    task_name=task_name,
                    output_dir=str(self.output_dir),
                    mode=self.mode,
                    data=None,  # No actual data overlay
                    step_colors=None  # No step coloring
                )
                
                generated_files.append(plot_path)
                print(f"    ✅ Generated: {Path(plot_path).name}")
                
            except Exception as e:
                print(f"    ❌ Failed to generate plot for {task_name}: {e}")
                continue
        
        print(f"✅ Filters by phase plots complete: {len(generated_files)} files generated")
        return generated_files
    
    def generate_all_plots(self, tasks: Optional[List[str]] = None) -> dict:
        """
        Generate all validation plots referenced in the kinematic specification.
        
        Args:
            tasks: Optional list of specific tasks. If None, generates for all tasks.
            
        Returns:
            Dictionary with generated file counts and paths
        """
        print(f"\n🎯 Generating ALL validation plots for kinematic specification")
        
        if tasks:
            print(f"   🎯 Target tasks: {tasks}")
        else:
            print(f"   🎯 Target: ALL tasks")
        
        results = {
            'forward_kinematics_plots': [],
            'filters_by_phase_plots': [],
            'total_files': 0
        }
        
        try:
            # Generate forward kinematics plots
            fk_files = self.generate_forward_kinematics_plots(tasks)
            results['forward_kinematics_plots'] = fk_files
            
            # Generate filters by phase plots  
            fbp_files = self.generate_filters_by_phase_plots(tasks)
            results['filters_by_phase_plots'] = fbp_files
            
            # Calculate totals
            results['total_files'] = len(fk_files) + len(fbp_files)
            
            print(f"\n🎉 ALL VALIDATION PLOTS GENERATED SUCCESSFULLY!")
            print(f"   📐 Forward Kinematics: {len(fk_files)} files")
            print(f"   📊 Filters by Phase: {len(fbp_files)} files")
            print(f"   📁 Total: {results['total_files']} files")
            print(f"   💾 Output directory: {self.output_dir}")
            
            return results
            
        except Exception as e:
            print(f"\n❌ ERROR: Failed to generate validation plots: {e}")
            raise


def main():
    """Main entry point with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Generate validation plots from YAML configuration"
    )
    parser.add_argument(
        "--tasks",
        nargs="+",
        help="Specific tasks to generate plots for (default: all tasks)"
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to custom validation config YAML (default: validation_ranges.yaml)"
    )
    parser.add_argument(
        "--mode",
        choices=['kinematic', 'kinetic', 'all'],
        default='all',
        help="Type of plots to generate (default: all)"
    )
    parser.add_argument(
        "--forward-kinematic-only",
        action="store_true",
        help="Only generate forward kinematic plots"
    )
    parser.add_argument(
        "--filters-only",
        action="store_true",
        help="Only generate filter by phase plots"
    )
    
    args = parser.parse_args()
    
    # Initialize generator with optional custom config
    try:
        if args.mode == 'all':
            # Generate both kinematic and kinetic plots
            modes = ['kinematic', 'kinetic']
        else:
            modes = [args.mode]
        
        for mode in modes:
            print(f"\n{'='*60}")
            print(f"Generating {mode.upper()} validation plots")
            print(f"{'='*60}")
            
            generator = ValidationPlotsGenerator(mode, args.config)
            
            if args.forward_kinematic_only and mode == 'kinematic':
                generator.generate_forward_kinematics_plots(args.tasks)
            elif args.filters_only:
                generator.generate_filters_by_phase_plots(args.tasks)
            else:
                generator.generate_all_plots(args.tasks)
                
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
