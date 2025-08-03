#!/usr/bin/env python3
"""
Generate validation documentation from YAML configuration files.

This script reads validation ranges from a YAML config file and generates
comprehensive markdown documentation with embedded visualizations.

Usage:
    python generate_validation_documentation.py --config path/to/validation_ranges.yaml
    python generate_validation_documentation.py  # Uses default config
"""

import argparse
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

class ValidationDocumentationGenerator:
    """Generate markdown documentation from validation YAML configs."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize with config file path.
        
        Args:
            config_path: Path to YAML config file. If None, uses default.
        """
        if config_path is None:
            # Default to the consolidated validation ranges
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "contributor_scripts" / "validation_ranges" / "validation_ranges.yaml"
        
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        # Load config
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Set up paths
        self.project_root = Path(__file__).parent.parent.parent
        self.output_dir = self.project_root / "docs" / "reference" / "standard_spec"
        self.image_dir = self.output_dir / "validation"
    
    def generate_documentation(self, output_file: Optional[Path] = None) -> Path:
        """Generate complete validation documentation.
        
        Args:
            output_file: Output markdown file path. If None, uses default.
            
        Returns:
            Path to generated documentation file.
        """
        if output_file is None:
            output_file = self.output_dir / "validation_ranges.md"
        
        output_file = Path(output_file)
        
        # Generate markdown content
        content = self._generate_markdown()
        
        # Write to file
        output_file.write_text(content)
        
        print(f"✅ Generated validation documentation: {output_file}")
        print(f"   Config: {self.config_path}")
        print(f"   Tasks: {len(self.config['tasks'])}")
        
        return output_file
    
    def _generate_markdown(self) -> str:
        """Generate complete markdown content."""
        lines = []
        
        # Header
        lines.append("# Validation Ranges")
        lines.append("")
        lines.append("**Biomechanically validated ranges for locomotion data quality assessment**")
        lines.append("")
        
        # Metadata
        lines.append("## Configuration Metadata")
        lines.append("")
        lines.append(f"- **Source Config**: `{self.config_path.name}`")
        lines.append(f"- **Generated**: {self.config.get('generated', 'Unknown')}")
        lines.append(f"- **Source Dataset**: {self.config.get('source_dataset', 'Unknown')}")
        lines.append(f"- **Method**: {self.config.get('method', 'Unknown')}")
        lines.append(f"- **Description**: {self.config.get('description', 'Unknown')}")
        lines.append("")
        
        # Feature types
        if 'feature_types' in self.config:
            lines.append("## Feature Categories")
            lines.append("")
            for category, types in self.config['feature_types'].items():
                lines.append(f"- **{category.title()}**: {', '.join(types)}")
            lines.append("")
        
        # Generate sections for each task
        for task_name in sorted(self.config['tasks'].keys()):
            lines.extend(self._generate_task_section(task_name))
        
        # Footer
        lines.append("---")
        lines.append("")
        lines.append(f"*Generated from `{self.config_path.name}` on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        
        return '\n'.join(lines)
    
    def _generate_task_section(self, task_name: str) -> list:
        """Generate documentation section for a specific task."""
        lines = []
        task_data = self.config['tasks'][task_name]
        
        # Task header
        lines.append(f"## Task: {task_name.replace('_', ' ').title()}")
        lines.append("")
        
        # Check for forward kinematics plots (static pose visualizations)
        forward_kinematics_plots = []
        for phase in ['00', '25', '50', '75']:
            plot_path = self.image_dir / f"{task_name}_forward_kinematics_phase_{phase}_range.png"
            if plot_path.exists():
                forward_kinematics_plots.append((phase, plot_path))
        
        # Add forward kinematics visualizations if they exist
        if forward_kinematics_plots:
            lines.append("### Forward Kinematics Visualizations")
            lines.append("")
            lines.append("Joint angle ranges visualized at key gait phases:")
            lines.append("")
            
            # Create table with all phase plots
            phase_headers = []
            phase_images = []
            for phase, plot_path in forward_kinematics_plots:
                phase_int = int(phase)
                phase_headers.append(f"Phase {phase_int}%")
                phase_images.append(f"![Phase {phase_int}%](validation/{plot_path.name})")
            
            lines.append("| " + " | ".join(phase_headers) + " |")
            lines.append("|" + "---|" * len(phase_headers))
            lines.append("| " + " | ".join(phase_images) + " |")
            lines.append("")
        
        # Check for phase-based visualizations
        kinematic_plot = self.image_dir / f"{task_name}_kinematic_filters_by_phase.png"
        kinetic_plot = self.image_dir / f"{task_name}_kinetic_filters_by_phase.png"
        
        # Add phase-based visualizations if they exist
        if kinematic_plot.exists() or kinetic_plot.exists():
            lines.append("### Phase-Based Visualizations")
            lines.append("")
            lines.append("Validation ranges across the full gait cycle (0-100% phase):")
            lines.append("")
            
            if kinematic_plot.exists():
                lines.append("#### Kinematic Variables")
                lines.append(f"![{task_name} Kinematic Validation](validation/{kinematic_plot.name})")
                lines.append("")
            
            if kinetic_plot.exists():
                lines.append("#### Kinetic Variables")
                lines.append(f"![{task_name} Kinetic Validation](validation/{kinetic_plot.name})")
                lines.append("")
        
        # Generate phase tables
        lines.append("### Phase-Specific Validation Ranges")
        lines.append("")
        
        # Group variables by type
        kinematic_vars = []
        kinetic_vars = []
        
        # Scan all phases to get complete variable list
        all_vars = set()
        for phase_data in task_data['phases'].values():
            all_vars.update(phase_data.keys())
        
        for var in sorted(all_vars):
            if any(k in var for k in ['angle', 'velocity']):
                kinematic_vars.append(var)
            else:
                kinetic_vars.append(var)
        
        # Generate kinematic table
        if kinematic_vars:
            lines.append("#### Kinematic Variables (rad, rad/s)")
            lines.extend(self._generate_variable_table(task_data['phases'], kinematic_vars))
            lines.append("")
        
        # Generate kinetic table  
        if kinetic_vars:
            lines.append("#### Kinetic Variables (Nm, N)")
            lines.extend(self._generate_variable_table(task_data['phases'], kinetic_vars))
            lines.append("")
        
        return lines
    
    def _generate_variable_table(self, phases_data: Dict, variables: list) -> list:
        """Generate markdown table for variables."""
        lines = []
        
        # Table header
        phases = sorted(phases_data.keys(), key=lambda x: int(x))
        lines.append("| Variable | " + " | ".join([f"Phase {p}%" for p in phases]) + " |")
        lines.append("|" + "---|" * (len(phases) + 1))
        
        # Table rows
        for var in variables:
            row = [f"`{var}`"]
            for phase in phases:
                if var in phases_data[phase]:
                    ranges = phases_data[phase][var]
                    row.append(f"[{ranges['min']:.2f}, {ranges['max']:.2f}]")
                else:
                    row.append("-")
            lines.append("| " + " | ".join(row) + " |")
        
        return lines

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate validation documentation from YAML config"
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to validation YAML config file (default: validation_ranges.yaml)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output markdown file path (default: docs/reference/standard_spec/validation_ranges.md)"
    )
    
    args = parser.parse_args()
    
    # Generate documentation
    generator = ValidationDocumentationGenerator(args.config)
    generator.generate_documentation(args.output)

if __name__ == "__main__":
    main()