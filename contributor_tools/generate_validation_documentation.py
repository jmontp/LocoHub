#!/usr/bin/env python3
"""
Unified Validation Documentation Generator

Generates both validation plots and markdown documentation from YAML configuration:
1. Forward kinematics range visualization plots
2. Filters by phase validation plots  
3. Validation ranges markdown documentation
4. Dataset overview pages

Usage:
    python generate_validation_documentation.py               # Generate everything
    python generate_validation_documentation.py --plots-only  # Only generate plots
    python generate_validation_documentation.py --docs-only   # Only generate docs
    python generate_validation_documentation.py --config custom_ranges.yaml
"""

import os
from pathlib import Path
from typing import List, Optional, Dict
import argparse
from datetime import datetime
import sys

# Add parent directory to path for imports
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

# Import validation modules
from internal.config_management.config_manager import ValidationConfigManager
from internal.plot_generation.forward_kinematics_plots import KinematicPoseGenerator
from internal.plot_generation.filters_by_phase_plots import create_filters_by_phase_plot


class UnifiedValidationGenerator:
    """
    Unified generator for all validation documentation and plots.
    Combines functionality from create_validation_range_plots.py and generate_validation_docs.py.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize with config path."""
        self.project_root = Path(__file__).parent.parent
        
        # Configuration
        if config_path:
            self.config_path = config_path
            self.config_manager = ValidationConfigManager(config_path.parent)
        else:
            self.config_path = self.project_root / "contributor_tools" / "validation_ranges" / "default_ranges.yaml"
            self.config_manager = ValidationConfigManager()
        
        # Output directories
        self.docs_dir = self.project_root / "docs" / "reference" / "datasets_documentation"
        self.plots_dir = self.docs_dir / "validation_ranges"
        self.validation_md = self.docs_dir / "validation_ranges.md"
        
        # Create directories if needed
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.plots_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize pose generator for forward kinematics
        self.pose_generator = KinematicPoseGenerator()
        
        print(f"✅ Initialized Unified Validation Generator")
        print(f"   📁 Config file: {self.config_path.name}")
        print(f"   📁 Output dir: {self.docs_dir}")
        print(f"   📁 Plots dir: {self.plots_dir}")
    
    def load_validation_data(self) -> dict:
        """Load validation expectations from YAML config."""
        print(f"📊 Loading validation data from {self.config_path.name}")
        
        try:
            # Load from config manager (contralateral features are generated automatically)
            self.config_manager.load()
            processed_data = {}
            for task_name in self.config_manager.get_tasks():
                # get_task_data returns data with generated contra features
                processed_data[task_name] = self.config_manager.get_task_data(task_name)
            
            print(f"✅ Loaded validation data for {len(processed_data)} tasks: {list(processed_data.keys())}")
            return processed_data
        except Exception as e:
            raise RuntimeError(f"Failed to load validation data: {e}")
    
    def generate_forward_kinematics_plots(self, tasks: Optional[List[str]] = None) -> List[str]:
        """
        Generate forward kinematics range visualization plots.
        Creates: {task_name}_forward_kinematics_phase_{00,25,50,75}_range.png
        """
        print("\n🎨 Generating Forward Kinematics Range Visualization Plots...")
        
        validation_data = self.load_validation_data()
        
        # Get current timestamp
        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Determine tasks to process
        if tasks:
            missing_tasks = [task for task in tasks if task not in validation_data]
            if missing_tasks:
                raise ValueError(f"Requested tasks not found: {missing_tasks}")
            tasks_to_process = tasks
        else:
            tasks_to_process = list(validation_data.keys())
        
        generated_files = []
        
        for task_name in tasks_to_process:
            print(f"  📐 Generating forward kinematics plots for: {task_name}")
            
            try:
                # Build ranges for forward kinematics with proper phase handling
                # Forward kinematics needs both ipsi and contra data at the SAME phase for bilateral pose
                cleaned_ranges = {}
                
                # Get all available phases (they are already integers from config manager)
                all_phases = sorted(validation_data[task_name].keys())
                
                for phase in all_phases:
                    # For forward kinematics, we need ipsi data at this phase
                    # and contra data from the offset phase (phase + 50) % 100
                    contra_phase = (phase + 50) % 100
                    
                    # Check if we have data for both phases needed
                    if phase not in validation_data[task_name]:
                        continue
                    if contra_phase not in validation_data[task_name]:
                        print(f"    ⚠️ Skipping phase {phase}: no data at contra phase {contra_phase}")
                        continue
                    
                    phase_ranges = {}
                    
                    # Get ipsi angles from current phase
                    for var_name, var_range in validation_data[task_name][phase].items():
                        if 'angle' in var_name and 'ipsi' in var_name:
                            clean_name = var_name.replace('_rad', '')
                            # Map ankle_dorsiflexion to ankle_flexion for forward kinematics
                            clean_name = clean_name.replace('ankle_dorsiflexion_angle', 'ankle_flexion_angle')
                            phase_ranges[clean_name] = var_range
                    
                    # Get contra angles from offset phase
                    for var_name, var_range in validation_data[task_name][contra_phase].items():
                        if 'angle' in var_name and 'ipsi' in var_name:
                            # Convert ipsi variable from offset phase to contra variable at current phase
                            clean_name = var_name.replace('_ipsi', '_contra').replace('_rad', '')
                            clean_name = clean_name.replace('ankle_dorsiflexion_angle', 'ankle_flexion_angle')
                            phase_ranges[clean_name] = var_range
                    
                    # Check if we have all required angles for forward kinematics
                    required_angles = [
                        'hip_flexion_angle_ipsi', 'knee_flexion_angle_ipsi', 'ankle_flexion_angle_ipsi',
                        'hip_flexion_angle_contra', 'knee_flexion_angle_contra', 'ankle_flexion_angle_contra'
                    ]
                    if all(angle in phase_ranges for angle in required_angles):
                        cleaned_ranges[phase] = phase_ranges
                    else:
                        missing = [a for a in required_angles if a not in phase_ranges]
                        print(f"    ⚠️ Skipping phase {phase}: missing {missing[:2]}...")
                
                if not cleaned_ranges:
                    print(f"    ⚠️ No valid phase combinations found for {task_name}")
                    continue
                
                print(f"    📊 Processing phases: {sorted(cleaned_ranges.keys())}")
                
                # Generate plots for this task with timestamp
                task_files = self.pose_generator.generate_task_validation_images(
                    task_name=task_name,
                    validation_ranges=cleaned_ranges,
                    output_dir=str(self.plots_dir),
                    timestamp=current_timestamp
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
        Creates: {task_name}_{kinematic|kinetic|segment}_filters_by_phase.png
        """
        print("\n📊 Generating Filters by Phase Validation Plots...")
        
        validation_data = self.load_validation_data()
        
        # Get metadata from config manager
        metadata = self.config_manager.get_metadata()
        dataset_name = metadata.get('source_dataset', 'Unknown')
        
        # Use current timestamp for all plots
        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Determine tasks to process
        if tasks:
            missing_tasks = [task for task in tasks if task not in validation_data]
            if missing_tasks:
                raise ValueError(f"Requested tasks not found: {missing_tasks}")
            tasks_to_process = tasks
        else:
            tasks_to_process = list(validation_data.keys())
        
        generated_files = []
        
        # Generate plots for all three modes: kinematic, kinetic, and segment
        for mode in ['kinematic', 'kinetic', 'segment']:
            print(f"  📈 Generating {mode} plots...")
            
            for task_name in tasks_to_process:
                try:
                    # Create the plot with current timestamp
                    plot_path = create_filters_by_phase_plot(
                        validation_data=validation_data,
                        task_name=task_name,
                        output_dir=str(self.plots_dir),
                        mode=mode,
                        data=None,  # No actual data overlay
                        dataset_name=f"Config: {self.config_path.name}",
                        timestamp=current_timestamp
                    )
                    
                    generated_files.append(plot_path)
                    print(f"    ✅ Generated: {Path(plot_path).name}")
                    
                except Exception as e:
                    print(f"    ❌ Failed to generate {mode} plot for {task_name}: {e}")
                    continue
        
        print(f"✅ Filters by phase plots complete: {len(generated_files)} files generated")
        return generated_files
    
    def generate_validation_ranges_md(self):
        """Generate clean validation_ranges.md with only plots."""
        # Get metadata from config manager
        metadata = self.config_manager.get_metadata()
        tasks = self.config_manager.get_tasks()
        
        lines = []
        lines.append("# Validation Ranges")
        lines.append("")
        lines.append("**Biomechanically validated ranges for locomotion data quality assessment**")
        lines.append("")
        
        # Configuration metadata
        lines.append("## Configuration Metadata")
        lines.append("")
        lines.append(f"- **Config File**: `{self.config_path.name}`")
        lines.append(f"- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if 'source_dataset' in metadata:
            lines.append(f"- **Source Dataset**: {metadata['source_dataset']}")
        if 'method' in metadata:
            lines.append(f"- **Method**: {metadata['method']}")
        if 'description' in metadata:
            lines.append(f"- **Description**: {metadata['description']}")
        lines.append("")
        
        # Process each task
        for task_name in sorted(tasks.keys()):
            lines.append(f"## Task: {task_name.replace('_', ' ').title()}")
            lines.append("")
            
            # Forward kinematics visualizations
            lines.append("### Forward Kinematics Visualizations")
            lines.append("")
            lines.append("Joint angle ranges visualized at key gait phases:")
            lines.append("")
            
            # Check which forward kinematics plots actually exist
            # Look for any phase files, not just standard ones
            import os
            from pathlib import Path
            existing_phases = []
            
            # Find all forward kinematics files for this task
            pattern = f"{task_name}_forward_kinematics_phase_*_range.png"
            for img_file in sorted(self.plots_dir.glob(pattern)):
                # Extract phase number from filename
                filename = img_file.name
                phase_str = filename.split('_phase_')[1].split('_range')[0]
                existing_phases.append(phase_str)
            
            if existing_phases:
                # Image table for forward kinematics (only existing plots)
                headers = [f"Phase {int(p)}%" for p in existing_phases]
                lines.append("| " + " | ".join(headers) + " |")
                lines.append("|" + "---|" * len(existing_phases))
                fk_images = []
                for phase in existing_phases:
                    img_path = f"validation_ranges/{task_name}_forward_kinematics_phase_{phase}_range.png"
                    fk_images.append(f"![Phase {int(phase)}%]({img_path})")
                lines.append("| " + " | ".join(fk_images) + " |")
                lines.append("")
            else:
                lines.append("*No forward kinematics visualizations available for this task.*")
                lines.append("")
            
            # Phase-based visualizations
            lines.append("### Phase-Based Visualizations")
            lines.append("")
            lines.append("Validation ranges across the full gait cycle (0-100% phase):")
            lines.append("")
            
            # Kinematic variables plot
            lines.append("#### Kinematic Variables (Joint Angles)")
            lines.append(f"![{task_name.replace('_', ' ').title()} Kinematic Validation](validation_ranges/{task_name}_kinematic_filters_by_phase_with_data.png)")
            lines.append("")
            
            # Kinetic variables plot
            lines.append("#### Kinetic Variables (Joint Moments)")
            lines.append(f"![{task_name.replace('_', ' ').title()} Kinetic Validation](validation_ranges/{task_name}_kinetic_filters_by_phase_with_data.png)")
            lines.append("")
            
            # Segment angle plot
            lines.append("#### Segment Angles")
            lines.append(f"![{task_name.replace('_', ' ').title()} Segment Validation](validation_ranges/{task_name}_segment_filters_by_phase_with_data.png)")
            lines.append("")
        
        lines.append("---")
        lines.append("")
        lines.append(f"*Generated from `{self.config_path.name}` on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        
        # Write the file
        with open(self.validation_md, 'w') as f:
            f.write('\n'.join(lines))
        
        print(f"✅ Generated: {self.validation_md}")
    
    def generate_dataset_overview(self):
        """Generate dataset overview README."""
        overview_path = self.docs_dir / "README.md"
        
        lines = []
        lines.append("# Dataset Documentation")
        lines.append("")
        lines.append("## Overview")
        lines.append("")
        lines.append("This section contains documentation for all standardized biomechanical datasets in the repository.")
        lines.append("")
        lines.append("## Available Datasets")
        lines.append("")
        lines.append("### UMich 2021")
        lines.append("- **Full Documentation**: [dataset_umich_2021.md](dataset_umich_2021.md)")
        lines.append("- **Validation Report**: [validation_reports/umich_2021_phase_validation_report.md](validation_reports/umich_2021_phase_validation_report.md)")
        lines.append("- **Tasks**: Level walking, incline walking, decline walking")
        lines.append("- **Subjects**: 10")
        lines.append("- **Format**: Phase-indexed (150 points per cycle)")
        lines.append("")
        lines.append("### GTech 2023")
        lines.append("- **Full Documentation**: [dataset_gtech_2023.md](dataset_gtech_2023.md)")
        lines.append("- **Status**: In development")
        lines.append("")
        lines.append("### AddBiomechanics")
        lines.append("- **Full Documentation**: [dataset_addbiomechanics.md](dataset_addbiomechanics.md)")
        lines.append("- **Status**: In development")
        lines.append("")
        lines.append("## Dataset Standards")
        lines.append("")
        lines.append("All datasets follow the standardized format defined in:")
        lines.append("- [Data Standard Specification](../standard_spec/standard_spec.md)")
        lines.append("- [Units and Conventions](../standard_spec/units_and_conventions.md)")
        lines.append("- [Validation Ranges](validation_ranges.md)")
        lines.append("")
        
        with open(overview_path, 'w') as f:
            f.write('\n'.join(lines))
        
        print(f"✅ Generated: {overview_path}")
    
    def generate_dataset_page(self, dataset_name: str, tasks: List[str]):
        """Generate individual dataset documentation page."""
        dataset_file = f"dataset_{dataset_name.lower().replace(' ', '_')}.md"
        dataset_path = self.docs_dir / dataset_file
        
        lines = []
        lines.append(f"# {dataset_name} Dataset")
        lines.append("")
        lines.append("## Overview")
        lines.append("")
        
        if dataset_name == "UMich 2021":
            lines.append("The University of Michigan 2021 dataset contains standardized biomechanical data from 10 healthy subjects performing various locomotion tasks.")
            lines.append("")
            lines.append("## Dataset Details")
            lines.append("")
            lines.append("- **Subjects**: 10 healthy adults")
            lines.append("- **Tasks**: Level walking, incline walking, decline walking")
            lines.append("- **Variables**: 45 biomechanical features (kinematics, kinetics, segment angles)")
            lines.append("- **Format**: Phase-indexed (150 points per gait cycle)")
            lines.append("- **File**: `converted_datasets/umich_2021_phase.parquet`")
            lines.append("")
            lines.append("## Validation Ranges")
            lines.append("")
            lines.append("The following plots show the expected biomechanical ranges used for data validation:")
            lines.append("")
            
            # Add validation range plots for each task
            for task in tasks:
                lines.append(f"### {task.replace('_', ' ').title()}")
                lines.append("")
                
                # Forward kinematics
                lines.append("#### Forward Kinematics")
                lines.append("| Phase 0% | Phase 25% | Phase 50% | Phase 75% |")
                lines.append("|---|---|---|---|")
                fk_images = []
                for phase in ['00', '25', '50', '75']:
                    img_path = f"validation_ranges/{task}_forward_kinematics_phase_{phase}_range.png"
                    fk_images.append(f"![{phase}%]({img_path})")
                lines.append("| " + " | ".join(fk_images) + " |")
                lines.append("")
                
                # Filters by phase
                lines.append("#### Validation Ranges by Phase")
                lines.append(f"![Kinematic](validation_ranges/{task}_kinematic_filters_by_phase.png)")
                lines.append(f"![Kinetic](validation_ranges/{task}_kinetic_filters_by_phase.png)")
                lines.append(f"![Segment](validation_ranges/{task}_segment_filters_by_phase.png)")
                lines.append("")
            
            lines.append("## Data Validation")
            lines.append("")
            lines.append("For detailed validation results with actual data:")
            lines.append("- [Full Validation Report](validation_reports/umich_2021_phase_validation_report.md)")
            lines.append("")
            
        elif dataset_name == "GTech 2023":
            lines.append("The Georgia Tech 2023 dataset is currently being processed for standardization.")
            lines.append("")
            lines.append("## Status")
            lines.append("- **Current Phase**: Data conversion and validation")
            lines.append("- **Expected Completion**: TBD")
            lines.append("")
            
        elif dataset_name == "AddBiomechanics":
            lines.append("The AddBiomechanics dataset provides comprehensive biomechanical data from multiple sources.")
            lines.append("")
            lines.append("## Status")
            lines.append("- **Current Phase**: Initial integration")
            lines.append("- **Expected Completion**: TBD")
            lines.append("")
        
        lines.append("## Usage")
        lines.append("")
        lines.append("```python")
        lines.append("from user_libs.python.locomotion_data import LocomotionData")
        lines.append("")
        lines.append(f"# Load the dataset")
        lines.append(f"data = LocomotionData('converted_datasets/{dataset_name.lower().replace(' ', '_')}_phase.parquet')")
        lines.append("")
        lines.append("# Get data for analysis")
        lines.append("cycles_3d, features = data.get_cycles('SUB01', 'level_walking')")
        lines.append("```")
        lines.append("")
        
        with open(dataset_path, 'w') as f:
            f.write('\n'.join(lines))
        
        print(f"✅ Generated: {dataset_path}")
    
    def generate_all_plots(self, tasks: Optional[List[str]] = None) -> dict:
        """Generate all validation plots."""
        print("\n🎯 Generating ALL validation plots")
        
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
            
            print(f"\n🎉 ALL PLOTS GENERATED SUCCESSFULLY!")
            print(f"   📐 Forward Kinematics: {len(fk_files)} files")
            print(f"   📊 Filters by Phase: {len(fbp_files)} files")
            print(f"   📁 Total: {results['total_files']} files")
            
            return results
            
        except Exception as e:
            print(f"\n❌ ERROR: Failed to generate validation plots: {e}")
            raise
    
    def generate_all_docs(self):
        """Generate all documentation files."""
        print("\n📝 Generating all documentation...")
        
        # Generate validation_ranges.md
        self.generate_validation_ranges_md()
        
        # Generate dataset overview
        self.generate_dataset_overview()
        
        # Generate individual dataset pages
        tasks = self.config_manager.get_tasks()
        
        self.generate_dataset_page("UMich 2021", tasks)
        self.generate_dataset_page("GTech 2023", [])
        self.generate_dataset_page("AddBiomechanics", [])
        
        print("\n✅ All documentation generated successfully!")
    
    def generate_all(self, tasks: Optional[List[str]] = None):
        """Generate everything - plots and documentation."""
        print("\n🚀 Generating complete validation documentation...")
        print(f"   📁 Using config: {self.config_path.name}")
        
        # Generate all plots
        self.generate_all_plots(tasks)
        
        # Generate all documentation
        self.generate_all_docs()
        
        print("\n✅ COMPLETE! All validation documentation generated successfully!")
        print(f"   📁 Documentation: {self.docs_dir}")
        print(f"   📁 Plots: {self.plots_dir}")


def main():
    """Main entry point with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Generate validation documentation and plots from YAML configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python generate_validation_documentation.py               # Generate everything
    python generate_validation_documentation.py --plots-only  # Only generate plots
    python generate_validation_documentation.py --docs-only   # Only generate docs
    python generate_validation_documentation.py --config custom_ranges.yaml
        """
    )
    
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to validation config YAML (default: default_ranges.yaml)"
    )
    
    parser.add_argument(
        "--tasks",
        nargs="+",
        help="Specific tasks to generate plots for (default: all tasks)"
    )
    
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--plots-only",
        action="store_true",
        help="Only generate plots (skip documentation)"
    )
    mode_group.add_argument(
        "--docs-only",
        action="store_true",
        help="Only generate documentation (skip plots)"
    )
    
    args = parser.parse_args()
    
    # Initialize generator
    try:
        generator = UnifiedValidationGenerator(args.config)
        
        if args.plots_only:
            print("\n📊 Generating plots only...")
            generator.generate_all_plots(args.tasks)
        elif args.docs_only:
            print("\n📝 Generating documentation only...")
            generator.generate_all_docs()
        else:
            # Default: generate everything
            generator.generate_all(args.tasks)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())