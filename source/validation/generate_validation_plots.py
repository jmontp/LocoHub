#!/usr/bin/env python3
"""
Validation Plots Generator

Single script to generate all validation plots referenced in validation_expectations_kinematic.md:
1. Forward kinematics range visualization plots (phase 0%, 25%, 50%, 75%)
2. Filters by phase validation plots

All paths are hardcoded for simplicity. Just run this script to update all validation plots.

Usage:
    python generate_validation_plots.py [--tasks task1 task2 ...]
    
Examples:
    python generate_validation_plots.py                    # Generate all plots
    python generate_validation_plots.py --tasks level_walking incline_walking
"""

import os
import sys
from pathlib import Path
from typing import List, Optional
import argparse

# Add source directory to Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Import validation modules
from validation.validation_expectations_parser import (
    parse_kinematic_validation_expectations, 
    parse_kinetic_validation_expectations,
    apply_contralateral_offset_kinematic,
    apply_contralateral_offset_kinetic
)
from validation.forward_kinematics_plots import KinematicPoseGenerator
from validation.filters_by_phase_plots import create_filters_by_phase_plot

class ValidationPlotsGenerator:
    """
    Unified generator for all validation plots referenced in the kinematic and kinetic specifications.
    Hardcoded paths for simplicity and reliability.
    """
    
    def __init__(self, mode: str = 'kinematic'):
        """Initialize with hardcoded paths.
        
        Args:
            mode: 'kinematic' or 'kinetic' to determine which plots to generate
        """
        self.mode = mode
        
        # Project root (assumes script is in source/validation/)
        self.project_root = Path(__file__).parent.parent.parent
        
        # Hardcoded paths
        if mode == 'kinematic':
            self.spec_file = self.project_root / "docs" / "standard_spec" / "validation_expectations_kinematic.md"
        else:  # kinetic
            self.spec_file = self.project_root / "docs" / "standard_spec" / "validation_expectations_kinetic.md"
            
        self.output_dir = self.project_root / "docs" / "standard_spec" / "validation"
        
        # Validate paths exist
        if not self.spec_file.exists():
            raise FileNotFoundError(f"{mode.title()} specification file not found: {self.spec_file}")
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize generators (only for kinematic mode)
        if mode == 'kinematic':
            self.pose_generator = KinematicPoseGenerator()
        
        print(f"✅ Initialized ValidationPlotsGenerator ({mode} mode)")
        print(f"   📄 Spec file: {self.spec_file}")
        print(f"   📁 Output dir: {self.output_dir}")
    
    def load_validation_data(self) -> dict:
        """Load validation expectations from specification file."""
        print(f"📊 Loading validation data from: {self.spec_file}")
        
        try:
            if self.mode == 'kinematic':
                validation_data = parse_kinematic_validation_expectations(str(self.spec_file))
                # Apply contralateral offset for all gait-based tasks
                for task_name, task_data in validation_data.items():
                    validation_data[task_name] = apply_contralateral_offset_kinematic(task_data, task_name)
            else:  # kinetic
                validation_data = parse_kinetic_validation_expectations(str(self.spec_file))
                # Apply contralateral offset for all gait-based tasks
                for task_name, task_data in validation_data.items():
                    validation_data[task_name] = apply_contralateral_offset_kinetic(task_data, task_name)
            
            print(f"✅ Successfully loaded validation data for {len(validation_data)} tasks: {list(validation_data.keys())}")
            return validation_data
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
                # Generate plots for this task using the validation data
                task_files = self.pose_generator.generate_task_validation_images(
                    task_name=task_name,
                    validation_ranges=validation_data[task_name],
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
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(
        description='Generate all validation plots for kinematic specification',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_validation_plots.py                    # Generate all plots
  python generate_validation_plots.py --tasks level_walking incline_walking
  python generate_validation_plots.py --forward-kinematic-only     # Only forward kinematics
  python generate_validation_plots.py --filters-only     # Only filters by phase
        """
    )
    
    parser.add_argument(
        '--tasks',
        nargs='*',
        help='Specific tasks to generate plots for (default: all tasks)'
    )
    
    parser.add_argument(
        '--forward-kinematic-only',
        action='store_true',
        help='Generate only forward kinematics plots'
    )
    
    parser.add_argument(
        '--filters-only', 
        action='store_true',
        help='Generate only filters by phase plots'
    )
    
    parser.add_argument(
        '--mode',
        choices=['kinematic', 'kinetic'],
        default='kinematic',
        help='Validation mode: kinematic (joint angles) or kinetic (forces/moments)'
    )
    
    args = parser.parse_args()
    
    # Validate mutually exclusive options
    if args.forward_kinematic_only and args.filters_only:
        print("❌ ERROR: Cannot specify both --forward-kinematic-only and --filters-only")
        return 1
    
    try:
        # Initialize generator with specified mode
        generator = ValidationPlotsGenerator(mode=args.mode)
        
        # Generate plots based on options
        if args.forward_kinematic_only:
            if args.mode == 'kinetic':
                print("⚠️  Forward kinematics plots are only available for kinematic mode")
                return 1
            generator.generate_forward_kinematics_plots(args.tasks)
        elif args.filters_only:
            generator.generate_filters_by_phase_plots(args.tasks)
        else:
            generator.generate_all_plots(args.tasks)
        
        print(f"\n✅ Validation plots generation completed successfully!")
        return 0
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())